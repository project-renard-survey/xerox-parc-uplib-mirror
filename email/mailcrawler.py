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
# Like jfiltermail, but also will add specified folders to a repository.
# This module contains base classes; actual crawlers should use them to
# put together a real program
#
"""
This module supplies core classes to build an UpLib-aware mail crawler.
It uses the UpLib `UploadDocument` extension to send email messages to the
repository.

The basic pattern is to create instances of `UpLibRepo`, `MessageSource`, and `MessageSink`,
then use them to create an instance of `MailCrawler`, and call the `run()` method
on that instance of `MailCrawler`.  `UpLibRepo` and `MailCrawler` can be used as-is;
`Message`, `MessageSource` and `MessageSink` are abstract, and must be subclassed appropriately.

If a mail filter function is defined, or a mail filter function file is specified,
that function will be invoked on each message before it is passed to the `UpLibRepo` instance
for addition to an UpLib repository.  The function can use the standard
method on the message to inspect it, and classify it into folders using the
`refile` and `copy` methods.  The `UpLibRepo` will look at this folder classification
in making its determination as to whether it will add the message to the repository.

:Author: Bill Janssen
"""

__docformat__ = "restructuredtext"

import sys, getopt, os, re, types, time, pwd, shutil, traceback, signal, posix, stat, socket, email.utils

from uplib.webutils import HTTPCodes, https_post_multipart, parse_URL_with_scheme, http_post_multipart
from uplib.plibUtil import read_metadata

class NotImplemented(Exception):
    """
    Raised by methods that haven't been properly overridden in a subclass.
    """
    pass

class Message:
    """
    An abstraction of an email message.  Must be subclassed to be used.
    """

    def getheader(self, headername):
        """
        *Abstract*.  Return one of the headers named by `headername`.

        :param headername: the name of the header field to return
        :type headername: string
        :return: the value of one instance of the specified header field.
        :rtype: string
        """
        raise NotImplemented("getheader")

    def getallmatchingheaders(self, headerpattern):
        """
        *Abstract*.  Return all of the headers matched by the given `headerpattern`.

        :param headerpattern: a regular expression for the names of the headers to return
        :type headerpattern: string
        :return: the full line, header name and value, of all instances of the matching header fields.
        :rtype: list(string)
        """
        raise NotImplemented("getallmatchingheaders")

    def in_folder(self, folderpattern):
        """
        *Abstract*. Obtain a list of the "folders" a message is in that match `folderpattern`.

        :param folderpattern: a regular expression for the names of some set of folders
        :type folderpattern: string
        :return: the folders the message is in the names of which match `folderpattern`
        :rtype: list(string)
        """
        raise NotImplemented("in_folder")

    # put a copy of the message into another folder
    def copy (self, foldername, unseen=1):
        """
        *Abstract*. Add the message to the specified folder, and mark it as unseen if `unseen` is set.

        :param foldername: the name of the folder to add the message to
        :type foldername: string
        :keyword unseen: boolean whether to mark the message as unseen in that folder, defaulting to `True`
        :type unseen: boolean
        """
        raise NotImplemented("copy")

    # put the message in a different folder
    def refile (self, foldername, unseen=1):
        """
        *Abstract*.  Move the message to the specified folder, remove it from its "current" folder, and mark it as unseen if `unseen` is set.

        :param foldername: the name of the folder to add the message to
        :type foldername: string
        :keyword unseen: boolean whether to mark the message as unseen in that folder, defaulting to `True`
        :type unseen: boolean
        """
        raise NotImplemented("refile")

    # resend the message to the specified names
    def resend(self, *to):
        """
        *Abstract*.  Resend the message to the specified addresses.

        :param to: email address
        :type to: string
        """
        raise NotImplemented("resend")

    def get_content(self):
        """
        *Abstract*.  Get the raw bits of the document

        :return: the raw RFC 2822 message
        :rtype: message/rfc822
        """
        raise NotImplemented("get_content")

    def get_mime_content_type(self):
        """
        *Abstract*.  Get the MIME content type of the document

        :return: the MIME content type.
        :rtype: a MIME media type string
        """
        return "message/rfc822"

    # discard message
    def discard(self):
        """
        *Abstract*.  Remove the message from its current folder.
        """
        raise NotImplemented("discard")

    def date(self):
        """
        Get the date and time of the message.

        :return: the date and time the message was sent
        :rtype: a float giving seconds past the UNIX epoch
        """
        datestamp = self.getheader("Date")
        if not datestamp:
            raise ValueError("Message has no Date header")
        return time.mktime(email.utils.parsedate(datestamp))

    def get_uuid (self):
        """
        Obtain the message ID for the message.

        :return: the Message-ID for the message
        :rtype: RFC 2822 Message-ID value
        """
        return self.getheader("Message-ID") or self.getheader("Resent-Message-Id")

    # Check to see if any of the specified 'names' are in any of the
    # specified headers
    def matches (self, names, headers):
        """
        Check to see if any of the specified names are in any of the specified headers.

        :param names: a list of strings
        :type names: string or list(string)
        :param headers: a list of header names
        :type headers: string or list(string)
        :return: whether or not any of the names are in any of the headers
        :rtype: boolean
        """
        if type(names) in types.StringTypes:
            names = ( names , )
        if type(headers) in types.StringTypes:
            headers = ( headers , )
        for header in headers:
            headerval = self.getheader(header)
            if not headerval:
                continue
            for name in names:
                testname = name.lower()
                testheader = headerval.lower()
                # print "looking for <%s> in <%s>" % (testname, testheader)
                if (testheader.find(testname) >= 0):
                    # print " *** found it"
                    return True
        return False

    # was the message sent to any of the specified names?
    def sentto (self, *names):
        """
        See if the message was sent to one of the specified names.

        :param names: one or more email addresses
        :type names: email addresses, like `foo@bar.com`
        :return: whether or not it was sent to one of those names
        :rtype: boolean
        """
	for header_name in ("to", "resent-to", "apparently-to", "cc"):
            headers = self.getallmatchingheaders(header_name)
            addresses = [x[1].lower() for x in email.utils.getaddresses(headers)]
	    for name in names:
                name = name.lower()
                for address in addresses:
                    if name in address:
                        return True
	return False



class UpLibRepo:

    """
    Represents an UpLib repository, to file messages into.
    """

    def __init__(self, folders, url=None, host=None, port=None, password=None, certificate=None):
        """
        Create a representative for an UpLib repository at `url`, or on `host` at `port`.  One
        of the two options must be specified; if both are present, the URL is preferred.

        :param url: the URL for the repository
        :type url: an UpLib HTTPS URL
        :param host: the machine on which the repository is running
        :type host: DNS hostname, e.g. `foo.bar.com`
        :param port: the port on which the repository is listening
        :type port: integer
        :param folders: a list of folder name patterns; only messages in those folders will be added to the repository
        :type folders: list(string)
        :keyword password: a password for the repository, defaults to None
        :type password: string
        :keyword certificate: the name of a certificate to use for client authentication, if required
        :type certificate: filename
        """
        if url:
            scheme, host, port, path = parse_URL_with_scheme(url)
            self._host = host
            self._port = port
            if scheme.lower() == "http":
                self._postfn = http_post_multipart
            elif scheme.lower() == "https":
                self._postfn = https_post_multipart
            else:
                raise ValueError("Invalid scheme '%s' for specified URL '%s'" % (scheme, url)) 
        else:
            self._host = host
            self._port = port
            self._postfn = https_post_multipart
        self._folders = folders
        self._password = password
        self._certificate = certificate
        # now see if we can get the name of the repository
        self._name = "%s:%s" % (self._host, self._port)
        keys = {}
        if self._certificate and (self._postfn is https_post_multipart):
            keys["certfile"] = self._certificate
            keys["keyfile"] = self._certificate
        status, statusmsg, headers, result = self._postfn(
            self._host, self._port, self._password, "action/externalAPI/repo_properties",
            [], [], **keys)
        if (status == HTTPCodes.OK):
            for line in result.split('\n'):
                if line.strip().startswith("name:"):
                    self._name = line.strip()[5:].strip()
        else:
            raise RuntimeError("Can't contact specified repository at %s:%s using %s:\n%s\n%s" % (
                self._host, self._port, self._postfn, statusmsg, result))

    def __str__(self):
        return '<UpLib "%s": %s>' % (self._name, ', '.join(self._folders))

    def add (self, msg, verbose=None, error=None):
        """
        Add the specified message to the repository.

        :param msg: the message to add
        :type msg: Message
        :keyword verbose: an outlet to send output to
        :type verbose: a Python file object
        :keyword error: an outlet to send error messages to
        :type error: a Python file object
        """

        trailer = time.strftime("/%Y/%B/%d", time.localtime(msg.date()))
        categories = []
        for folderpattern in self._folders:
            fnames = msg.in_folder(folderpattern)
            for name in fnames:
                foldername = "email/" + name + trailer
                if foldername not in categories:
                    categories.append(foldername)
        if categories:
            if verbose:
                verbose.write("adding %s to UpLib %s, category %s\n" % (
                    msg.get_uuid(), self._name, categories))
            bits = msg.get_content()
            try:
                # send it to UpLib for caching
                params = [('content', msg.get_content()),
                          ('contenttype', msg.get_mime_content_type()),
                          ('md-categories', ','.join(categories)),
                          ('no-redirect', 'true'),
                          ('suppress-duplicates', 'true'),
                          ('bury', 'true'),
                          ]
                keys = {}
                if self._certificate and (self._postfn is https_post_multipart):
                    keys["certfile"] = self._certificate
                    keys["keyfile"] = self._certificate
                status, statusmsg, headers, result = self._postfn(
                    self._host, self._port, self._password, "action/UploadDocument/add",
                    params, [], **keys)
                if (status == HTTPCodes.OK):
                    return
                if error:
                    error.write("Failed to add %s to repo at %s:%s, status code %s:\n%s\n" % (
                        msg.get_uuid(), self._host, self._port, status, result))
            except:
                if error:
                    error.write("Exception trying to add %s to repo_port at %s:%s:\n%s\n" % (
                        msg.get_uuid(), self._host, self._port,
                        ''.join(traceback.format_exception(*sys.exc_info()))))


class MessageSink:
    """
    An abstraction of a message sink, something to dispose of messages after they've been filed.
    """

    def __init__(self):
        raise NotImplemented("MessageSink")

    def dispose(self, msg):
        """
        *Abstract*.  Close or cleanup or actually file the message.

        :param msg: the message to dispose of
        :type msg: Message
        """
        raise NotImplemented("MessageSink.dispose")


class MessageSource:
    """
    An abstraction of a source of email messages, an iterator which produces a sequence of Message objects.
    """
    def __init__(self):
        raise NotImplemented("MessageSource")

    def __iter__(self):
        raise NotImplemented("MessageSource.__iter__")

    def next(self):
        raise NotImplemented("MessageSource.next")


class MailCrawler:
    """
    The actual crawler object.

    Initialized with a `repo`, a `message_source`, and a `message_sink`, it will
    call the mail filter function on each message, then add them to the repository
    if they are in the correct folders for the `repo`.
    """

    def __init__(self, repo, message_source, message_sink, verbose=False, errstream=None, mailfilterfn=None, mailfilterfile=None):
        """
        :param repo: the UpLib repository to use
        :type repo: UpLibRepo
        :param message_source: the source of the new messages
        :type message_source: MessageSource
        :param message_sink: something which finalizes the messages
        :type message_sink: MessageSink
        :keyword verbose: whether or not to produce descriptive output, defaults to None
        :type verbose: Python file object
        :keyword errstream: a stream to write error messages to, defaults to None
        :type errstream: Python file object
        :keyword mailfilterfn: a function to call to process message instances with
        :type mailfilterfn: Python function taking one parameter, the message
        :keyword mailfilterfile: a file containing a mail filter function
        :type mailfilterfile: file name
        """
        self._uplib_repo = repo
        self._message_source = message_source
        self._message_sink = message_sink
        self._mailfilterfn = mailfilterfn
        self._mailfilterfile = mailfilterfile
        if not self._mailfilterfile:
            self._mailfilterfile = os.path.expanduser("~/.mailfilter.py")
        self._filterdeftime = 0
        self._verbose = verbose
        if errstream is None:
            self._error = sys.stderr
        else:
            self._error = errstream

    def _read_filter_fn(self):
        self._filterdeftime = time.time()
        try:
            f = open (self._mailfilterfile, "r")
            code = f.read()
            f.close()
            # print 'code is', code
            execdict = {}
            exec(code) in execdict
            # print 'execdict is', execdict
            if (not execdict.has_key("mailfilterfn")):
                sys.stderr.write("%s does not define 'mailfilterfn'\n" % filename)
                return None
            self._mailfilterfn = execdict["mailfilterfn"]
            return True
        except:
            msg = ''.join(traceback.format_exception(*sys.exc_info()))
            self._error.write("error reading mail filter function in %s:\n%s" % (self._mailfilterfile, msg))
            return False

    def _read_filter_fn_if_necessary(self):
        if (not self._mailfilterfn):
            if self._mailfilterfile and os.path.exists(self._mailfilterfile):
                # not defined, so read the file
                if self._verbose:
                    self._verbose.write("MailCrawler:  reading initial mail filter file %s\n" % self._mailfilterfile)
                self._read_filter_fn()
        else:	# already defined, so re-read only if file has changed
            if os.path.isfile(self._mailfilterfile):
                stats = posix.stat(filename)
                mtime = stats[stat.ST_MTIME]
                if (mtime > self._filterdeftime):
                    if self._verbose:
                        self._verbose.write("MailCrawler:  reading changed mail filter file %s\n" % self._mailfilterfile)
                    self._read_filter_fn()
                else:
                    return True
            else:
                return False

    def run (self, count=0):
        """
        Consume all the messages in the source, calling the filter function on each,
        if it's defined, then giving the message to the repository instance to see if it should
        be added, finally giving the message to the sink.

        :param count: if non-zero, only these many messages will be processed
        :type count: integer
        """

        if self._mailfilterfile and os.path.exists(self._mailfilterfile):
            self._read_filter_fn_if_necessary()
        i = 0
        for msg in self._message_source:
            try:
                if self._mailfilterfn:
                    self._mailfilterfn(msg)
                if self._uplib_repo:
                    self._uplib_repo.add(msg, self._verbose, self._error)
                if self._message_sink:
                    self._message_sink.dispose(msg)
            except:
                self._error.write("Error processing %s:\n%s\n" % (
                    msg, ''.join(traceback.format_exception(*sys.exc_info()))))
            i += 1
            if count > 0 and i >= count:
                return
