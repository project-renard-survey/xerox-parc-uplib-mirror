#!/usr/bin/env python
# -*- Python -*-
#
# This file is part of the "UpLib 1.7.11" release.
# Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# sort incoming mail messages, based on rules in ~/.mailfilter.py
# 
# Like jfiltermail, but also will add specified folders to an UpLib repository.
#

import sys, os, re, types, time, traceback, imaplib, email, socket

from uplib.webutils import HTTPCodes, https_post_multipart
from uplib.plibUtil import read_metadata, getpass, note, set_verbosity

import mailcrawler

class Message(mailcrawler.Message):

    def __init__(self, mboxid, msgtext):
        self.msg = email.message_from_string(msgtext)
        self.size = len(msgtext)
        self.id = mboxid
        self.folders = []
        self.removed = False            # remove from original folder (INBOX)
        self.unseen = False             # mark as unseen

    def __str__(self):
        return '<Message %s (%d bytes) id=%s>' % (self.get_uuid(), self.size, self.id)

    def __repr__(self):
        return str(self)

    def __del__(self):
        del self.msg

    def getheader(self, headername):
        """
        :param headername: the name of the header field to return
        :type headername: string
        :return: the full line, header name and value, of one instance of the specified header field.
        :rtype: string
        """
        v = self.msg.get(headername)
        if v and (type(v) in types.StringTypes):
            return v
        elif v and isinstance(v, (tuple, list)):
            return v[0]
        else:
            return None

    def getallmatchingheaders(self, headerpattern):
        """
        :param headerpattern: a regular expression for the names of the headers to return
        :type headerpattern: string
        :return: the full line, header name and value, of all instances of the matching header fields.
        :rtype: list(string)
        """
        headers = self.msg.keys()
        rval = []
        for header in headers:
            if re.match(headerpattern, header):
                v = self.msg.get(header)
                if isinstance(v, (tuple, list)):
                    for val in v:
                        rval.append(header + ": " + val)
                elif v:
                    rval.append(header + ": " + v)
        return rval

    def in_folder(self, folderpattern):
        """
        :param folderpattern: a regular expression for the names of some set of folders
        :type folderpattern: string
        :return: the folders the message is in the names of which match `folderpattern`
        :rtype: list(string)
        """
        rval = []
        for folder in self.folders:
            if re.match(folderpattern, folder):
                rval.append(folder)
        return rval

    # put a copy of the message into another folder
    def copy (self, foldername, unseen=True):
        """
        :param foldername: the name of the folder to add the message to
        :type foldername: string
        :keyword unseen: boolean whether to mark the message as unseen in that folder, defaulting to `True`
        :type unseen: boolean
        """
        self.folders.append(foldername)
        self.unseen = unseen

    # put the message in a different folder
    def refile (self, foldername, unseen=True):
        """
        :param foldername: the name of the folder to add the message to
        :type foldername: string
        :keyword unseen: boolean whether to mark the message as unseen in that folder, defaulting to `True`
        :type unseen: boolean
        """
        self.folders.append(foldername)
        self.removed = True
        self.unseen = unseen

    # resend the message to the specified names
    def resend(self, *to):
        """
        :param to: email address
        :type to: string
        """
        note("resend not implemented")

    def get_content(self):
        """
        :return: the raw RFC 2822 message
        :rtype: message/rfc822
        """
        return self.msg.as_string()

    def get_mime_content_type(self):
        """
        :return: the MIME content type.
        :rtype: a MIME media type string
        """
        return "message/rfc822"

    # discard message
    def discard(self):
        self.removed = True

    def get_uuid (self):
        """
        Obtain the message ID for the message.

        :return: the Message-ID for the message
        :rtype: RFC 2822 Message-ID value
        """
        return self.getheader("Message-ID") or self.getheader("Resent-Message-Id")


class IMAPSourceSink (mailcrawler.MessageSource, mailcrawler.MessageSink):

    def __init__ (self, host, port, accountname, accountpassword, mailbox=None, use_ssl=False):
        self.host = host
        self.port = port
        self.accountname = accountname
        self.accountpassword = accountpassword
        self.mailbox = mailbox or "INBOX"
        self.use_ssl = use_ssl
        self.folders = ["INBOX"]

        self.connection = None
        self.partseparator = None

    def _create_folder(self, foldername):
        if not self.connection:
            self._open_connection()
        parts = foldername.split("/")
        newname = self.partseparator.join(parts)
        if newname not in self.folders:
            response, data = self.connection.create(newname)
            self.folders.append(newname)
        return newname

    def _open_connection(self):
        if self.connection is None:
            imaplib.Debug = 0
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self.connection = imaplib.IMAP4(self.host, self.port)
            self.connection.login(self.accountname, self.accountpassword)
            response, data = self.connection.list(self.mailbox)
            if response != "OK":
                raise ValueError("No such mailbox %s:  %s" % (self.mailbox, data))
            self.partseparator = data[0].split()[1].strip('"')
            response, data = self.connection.select(self.mailbox, True)
            if response == "OK":
                count = int(data[0])
                note(3, "%d messages in %s", count, self.mailbox)
            else:
                raise ValueError("Can't select mailbox %s:  %s" % (self.mailbox, data))
            self.connection._cmd_log_len = 1

    def __iter__(self):
        if not self.connection:
            self._open_connection()
        response, data = self.connection.search(None, "(UNKEYWORD $UpLibGathered)")
        if response == "OK":
            msgnums = data[0].split()
        else:
            return
        for msgnum in msgnums:
            response, msgdata = self.connection.fetch(str(msgnum), "(RFC822)")
            for response_part in msgdata:
                if isinstance(response_part, tuple):
                    msg = Message(msgnum, response_part[1])
                    note(3, "%s", msg)
                    yield msg

    # and dispose, for the MessageSink class
    def dispose(self, msg):
        if msg.folders:
            for folder in msg.folders:
                imapfolder = self._create_folder(folder)
                # move it to that folder
                note("moving %s to folder '%s'", msg.get_uuid(), folder)
                response, data = self.connection.copy(msg.id, imapfolder)
                if response != "OK":
                    raise RuntimeError("Can't copy msg %s to folder %s", msg.get_uuid(), folder)
                if msg.unseen:
                    # mark it as unseen
                    note("   marking %s as unseen in '%s'", msg.get_uuid(), folder)
                    try:
                        self.connection.select(imapfolder)
                        query = "(HEADER Message-ID %s)" % msg.getheader("Message-ID")
                        response, data = self.connection.search(None, query)
                        if response == "OK":
                            id = data[0].split()[0]
                            self.connection.store(id, "-FLAGS.SILENT", r"(\Seen)")
                    finally:
                        self.connection.select(self.mailbox)
        if msg.removed:
            # do something to delete it from the mailbox
            note("deleting %s from %s", msg.get_uuid(), self.mailbox)
            self.connection.store(msg.id, "+FLAGS", "($UpLibGathered)")
#           self.connection.store(msg.id, "+FLAGS", r"(\Deleted)")
#        else:
            self.connection.store(msg.id, "+FLAGS", "($UpLibGathered)")
        del msg


def _fix_socket():
    # from http://the.taoofmac.com/space/blog/2006/09/28:
    # Hideous fix to counteract http://python.org/sf/1092502
    # (which should have been fixed ages ago.)
    def _fixed_socket_read(self, size=-1):
        data = self._rbuf
        if size < 0:
            # Read until EOF
            buffers = []
            if data:
                buffers.append(data)
            self._rbuf = ""
            if self._rbufsize <= 1:
                recv_size = self.default_bufsize
            else:
                recv_size = self._rbufsize
            while True:
                data = self._sock.recv(recv_size)
                if not data:
                    break
                buffers.append(data)
            return "".join(buffers)
        else:
            # Read until size bytes or EOF seen, whichever comes first
            buf_len = len(data)
            if buf_len >= size:
                self._rbuf = data[size:]
                return data[:size]
            buffers = []
            if data:
                buffers.append(data)
            self._rbuf = ""
            while True:
                left = size - buf_len
                recv_size = min(self._rbufsize, left)   # this is the fixed line
                data = self._sock.recv(recv_size)
                if not data:
                    break
                buffers.append(data)
                n = len(data)
                if n >= left:
                    self._rbuf = data[left:]
                    buffers[-1] = data[:left]
                    break
                buf_len += n
            return "".join(buffers)

    # patch the method at runtime
    socket._fileobject.read = _fixed_socket_read


def main():
 
    def usage():
        sys.stderr.write('Usage:  %s [-v] [-repo REPOSITORY] [-folders FOLDERS] [-server HOST[:PORT]] [-account ACCOUNTNAME] [-mailbox MBOXNAME]\n' % sys.argv[0])
        sys.stderr.write('Args were: %s\n' % sys.argv)
        sys.stderr.write('-v causes the program to run in "verbose" mode\n')
        sys.stderr.write('-repo gives the directory of the local repository, or the URL of the remote repository\n')
        sys.stderr.write('-folders gives a comma-separated list of folders to add to the repo\n')
        sys.stderr.write('-server HOST[:PORT] specifies the IMAP server to talk to, and optionally the port\n')
        sys.stderr.write('-account ACCOUNTNAME specifies the account (pass the password as the value of the IMAP_PASSWORD env var)\n')
        sys.stderr.write('-mailbox MBOXNAME specifies the mailbox to read, defaults to INBOX\n')
        sys.stderr.write('-config CONFIGFILE gives the config file to read\n')
        sys.exit(1)

    verbose = False
    repo_port = 0
    repo = None
    folders = None
    accountname = None
    host = None
    mailbox = None

    i = 1
    while (i < len(sys.argv) and sys.argv[i][0] == '-'):
        if (sys.argv[i] == '-v'):
            verbose = True
            set_verbosity(3)
        elif ((sys.argv[i] == '-server') and ((i + 1) < len(sys.argv))):
            i = i + 1
            host = sys.argv[i]
        elif ((sys.argv[i] == '-mailbox') and ((i + 1) < len(sys.argv))):
            i = i + 1
            mailbox = sys.argv[i]
        elif ((sys.argv[i] == '-account') and ((i + 1) < len(sys.argv))):
            i = i + 1
            accountname = sys.argv[i]
        elif ((sys.argv[i] == '-repo') and ((i + 1) < len(sys.argv))):
            i = i + 1
            repo = sys.argv[i]
        elif ((sys.argv[i] == '-folders') and ((i + 1) < len(sys.argv))):
            i = i + 1
            folders = sys.argv[i].split(",")
        else:
            usage()
        i = i + 1

    if ':' in host:
        host, port = host.split(':')
        port = int(port)
    else:
        port = 143
    accountpassword = os.environ.get("IMAP_PASSWORD")
    if not accountpassword:
        accountpassword = getpass("Account password: ")

    if sys.version_info < (2, 5, 4):
        _fix_socket()

    # 1.  Get an UpLibRepo

    if repo and folders:
        if repo.lower().startswith("https:"):
            repo = mailcrawler.UpLibRepo(folder, url=repo)
        elif os.path.isdir(repo):
            portfile = os.path.join(repo, "overhead", "angel.port")
            if not os.path.isfile(portfile):
                raise ValueError("Repository argument '%s' should be the root of an UpLib repository." % repo)
            repo_port = int(open(portfile, "r").read())
            socket.setdefaulttimeout(600)
            repo = mailcrawler.UpLibRepo(folders, host='127.0.0.1', port=repo_port)
        else:
            raise ValueError("Don't understand 'repo' argument '%s'" % repo)
    if repo and verbose:
        sys.stdout.write(str(repo) + "\n")

    # 2.  Get a message source (and sink)

    sourcesink = IMAPSourceSink(host, port, accountname, accountpassword, mailbox, use_ssl=(port == 993))

    # 3.  Create a MailCrawler...

    crawler = mailcrawler.MailCrawler(repo, sourcesink, sourcesink, verbose and sys.stdout, sys.stderr)

    # 4.  And run it.

    crawler.run()

if __name__ == "__main__":
	main()
