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
import os
import re
import socket
import signal
import string
import sys
import threading
import time
import traceback
import types
import base64
import quopri
import weakref

from StringIO import StringIO

from bisect import insort

from urllib import unquote, splitquery

# async modules
import asyncore
import asynchat

# medusa modules
from medusa import http_date
from medusa import producers
from medusa import status_handler
from medusa import logger
from medusa.counter import counter

# UpLib modules
from uplib.plibUtil import note
UPLIB_MIN_VERSION = "1.7"

# we know we have the right email package (it's checked in the package
# __init__.py), but just in case...
import email
versions = email.__version__.split(".")
note(4, "email version numbers are " + str(versions) + "\n")
if (not versions) or (int(versions[0]) < 4):
    raise ValueError("Need email package 4.x or higher for IMAPServer package")
import email.Utils
import email.Message
import email.Header
import email.Encoders

import time, base64


QUOTED_LITERALS = '"/\\'

# ===========================================================================
#  states for an imap connection
# ===========================================================================

STATE_NOT_AUTHENTICATED = 0
STATE_AUTHENTICATED = 1
STATE_SELECTED = 2
STATE_LOGOUT = 3

# ===========================================================================
#  message object
# ===========================================================================

def quote(v):
    if not v:
        return None
    else:
        return '"%s"' % email.Utils.quote(v)

BODYPATTERN = re.compile(r'body((?P<peek>\.peek)|(?P<structure>structure))?(?P<hasfields>\[(?P<segment>(?P<partspec>[0-9]+(\.[0-9]+)*)*\.?(?P<fieldspec>[^\]]+)*)\])?(<(?P<firstoctet>[0-9]+)\.(?P<octetcount>[0-9]+)>)?')

class message:

    def __init__(self, mailbox, id, uid, flags):
        self.mbox_id = id
        self.uid = uid
        self.mailbox = mailbox
        self.flags = flags or ["\Recent"]
        self.__msg = None
        self.__envelope = None
        self.__bodystructure = None
        self.__size = 0
        self.__dirty = False

    def __cmp__(self, other):
        # order by UID
        return cmp(self.uid, other.uid)

    def msg(self):
        m = (self.__msg is not None) and self.__msg()
        if not m:
            # we don't use the size from get_msg_as_email
            m = self.mailbox.get_msg_as_email(self.mbox_id)
            self.__msg = weakref.ref(m)
        return m

    def generate_envelope(self):
        if not self.__envelope:
            self.__envelope = message.get_envelope(self.msg())
        return self.__envelope

    def size(self):
        if not self.__size:
            m = len(self.as_string())
        return self.__size

    def set_flag(self, flag):
        if not flag in self.flags:
            self.flags.append(flag)
            self.__dirty = True

    def clear_flag(self, flag):
        if flag in self.flags:
            self.flags.remove(flag)
            self.__dirty = True

    def set_flags(self, flags):
        self.flags = flags
        self.__dirty = True

    def test_flag(self, flag):
        return flag in self.flags

    def needs_saving(self):
        return self.__dirty

    def set_needs_saving(self):
        self.__dirty = True

    def saved(self):
        self.__dirty = False

    def get_internaldate (self):
        return self.mailbox.get_internaldate(self)

    def get_envelope(m, parenthesize=True):

        """The fields of the envelope structure are in the following
        order: date, subject, from, sender, reply-to, to, cc, bcc,
        in-reply-to, and message-id.  The date, subject, in-reply-to,
        and message-id fields are strings.  The from, sender, reply-to,
        to, cc, and bcc fields are parenthesized lists of address
        structures."""

        def format_addr(a):
            if not a:
                return None
            elif (isinstance(a, tuple) or isinstance(a, list)):
                v = string.join([format_addr(x, False) for x in a])
                return (parenthesize and "(%s)" % v) or v
            else:
                realname, emailaddr = email.Utils.parseaddr(a)
                if emailaddr:
                    mailbox, hostname = ('', '')
                    if ('@' in emailaddr):
                        mailbox, hostname = emailaddr.split('@')
                    elif not realname:
                        realname = a
                v = ("(%s %s %s %s)" % (quote(realname) or 'NIL',
                                        'NIL',                       # we don't handle source routing
                                        quote(mailbox) or 'NIL',
                                        quote(hostname) or 'NIL'))
                return (parenthesize and "(%s)" % v) or v

        return ("(%s %s %s %s %s %s %s %s %s %s)" %
                (quote(m.get('date')) or 'NIL',
                 quote(m.get('subject')) or 'NIL',
                 format_addr(m.get('from')) or 'NIL',
                 format_addr(m.get('sender')) or format_addr(m.get('from')) or 'NIL',
                 format_addr(m.get('reply-to')) or format_addr(m.get('from')) or 'NIL',
                 format_addr(m.get('to')) or 'NIL',
                 format_addr(m.get('cc')) or 'NIL',
                 format_addr(m.get('bcc')) or 'NIL',
                 quote(m.get('in-reply-to')) or 'NIL',
                 quote(m.get('message-id')) or 'NIL'))
    get_envelope=staticmethod(get_envelope)

    def join_multipart(self, mess):
        if not mess.is_multipart():
            raise ValueError("argument to join_multipart must be a multipart")
        b = mess.get_boundary()
        parts = []
        #note("join_multipart(%s):\n", mess)
        for part in mess.get_payload():
            #note("    part is %s, %s", part, part.get_content_type())
            s = self.as_string(ms=part)
            parts.append("--" + b + "\r\n" + s)
        parts.append("--" + b + "--" + "\r\n")
        s = "\r\n".join(parts)
        # s = string.join([("--" + b + "\r\n" + self.as_string(ms=x)) for x in mess.get_payload()], '\r\n') + "--" + b + "--\r\n"
        return s

    def get_body_structure (self, ext_data=False, ms=None):

        m = self.msg()
        if (ms is not None) and (ms is not m):
            m = ms
        elif self.__bodystructure:
            return self.__bodystructure

        # note("getting body_structure for %s %s...", m.get_content_type(), repr(m))

        def get_body_params (m, header=None):
            # note("m.get_params([('', '')], '%s') => %s", header or "content-type", m.get_params([("", "")], header or "content-type"))
            l = []
            charset = False
            mainvalue = None
            for name, value in m.get_params([('', '')], header or "content-type"):
                if (name and value):
                    if isinstance(value, tuple):
                        value = unicode(value[2], value[0] or 'us-ascii')
                    l.append('"%s" "%s"' % (name, value))
                    if name.lower() == 'charset':
                        charset = True
                elif name:
                    mainvalue = name
            if ((header is None) or (header.lower() == 'content-type')) and (m.get_content_maintype() == "text") and (not charset):
                l.append('"CHARSET" "US-ASCII"')
            return mainvalue, string.join(l, ' ')

        t, body_params = get_body_params(m)
        content_id = m.get('content-id')
        content_location = m.get('content-location')
        content_language = m.get('content-language')
        content_md5 = m.get('content-md5')
        content_disp, content_disp_params = get_body_params(m, "content-disposition")
        disp = (content_disp and '("%s" (%s))' % (content_disp, content_disp_params)) or 'NIL'
        if (m.get_content_maintype() == "multipart"):
            basic = '('
            for part in m.get_payload():
                basic += self.get_body_structure(ext_data, ms=part)
            basic += ' "%s"' % m.get_content_subtype()
            if ext_data:
                basic += ' (%s) %s %s %s' % (body_params, disp,
                                             (content_language and '"%s"' % content_language) or 'NIL',
                                             (content_location and '"%s"' % content_location) or 'NIL')
            basic += ')'
        else:
            content_descr = m.get('content-description')
            content_transfer_encoding = m.get('content-transfer-encoding') or '7BIT'
            if m.get_content_maintype() == "message":
                p = m.get_payload()[0]
                s = self.as_string(ms=p)
            else:
                s = m.get_payload()
            basic = ('("%s" "%s" (%s) %s %s %s %d'
                     % (m.get_content_maintype(), m.get_content_subtype(),
                        # body parameters (chartype, etc.)
                        body_params,
                        # body id, usually NIL
                        (content_id and ('"%s"' % content_id)) or 'NIL',
                        # body description
                        (content_descr and ('"%s"' % content_descr)) or 'NIL',
                        # body encoding
                        '"%s"' % content_transfer_encoding,
                        # body size, in octets
                        len(s)))
            if m.get_content_maintype().lower() == 'text':
                basic += " %d" % len(s.split('\n'))
            elif m.get_content_type().lower() == 'message/rfc822':
                basic += " " + message.get_envelope(p) + " " + self.get_body_structure(ext_data,ms=p) + " %d" % len(s.split('\n'))
            if ext_data:
                basic += ' %s %s %s %s' % ((content_md5 and '"%s"' % content_md5) or 'NIL', disp,
                                            (content_language and '"%s"' % content_language) or 'NIL',
                                            (content_location and '"%s"' % content_location) or 'NIL')
            basic += ')'

        #note("   ... is %s", basic)
        if ms is None:
            self.__bodystructure = basic
        return basic

    def find_message_part(self, partspec, ms=None):
        if ms is not None:
            m = ms
        else:
            m = self.msg()
        #note("partspec is '%s'..., m %s", partspec, m)
        if partspec is None:
            return m
        else:
            v = [int(x) for x in partspec.split(".")]
            # note("split partspec is %s", v)
            for i in v:
                # note("finding part %s of %s...", i, repr(m))
                if m.get_content_maintype() == "multipart":
                    m = m.get_payload()[i-1]
                elif m.get_content_type().lower() == "message/rfc822":
                    m = self.find_message_part(str(i), ms=m.get_payload()[0])
                elif (i == 1):
                    # special case for non-multipart; the part is the message itself
                    pass
                else:
                    raise ValueError("bad partspec '%s' given" % partspec)
            #note("part for find_message_part(%s) is %s (%s)", partspec, repr(m), m.get_content_type())
            return m

    def as_string(self, part=None, ms=None):
        m = None
        if ms is not None:
            m = ms
        elif (part is not None):
            m = self.find_message_part(part, ms=ms)
        if m is None:
            m = self.msg()
        #note("as_string(part=%s, ms=%s): self.__msg is %s, m is %s", part, ms, self.__msg, m)
        headers = m.items()
        r = ""
        for header in headers:
            r += "%s: %s\r\n" % header
        r += '\r\n'
        if m.get_content_maintype() == "multipart":
            r += self.join_multipart(m)
        elif m.get_content_maintype() == "message":
            r += self.as_string(ms=m.get_payload()[0])
        else:
            r += m.get_payload()
        return r        

    def get_part(self, part_as_given):

        part = part_as_given.lower()
        # IMAP part names
        if part == "uid":
            return part_as_given + " " + str(self.uid)
        elif part == "flags":
            return part_as_given + " (" + string.join([str(x) for x in self.flags], ' ') + ")"
        elif part == "envelope":
            v = self.generate_envelope()
            note("envelope for %s is %s", self, v)
            return part_as_given + " " + v
        elif part == "internaldate":
            return part_as_given + " " + quote(self.get_internaldate())

        elif part == "rfc822.size":
            return part_as_given + " " + str(len(self.as_string()))

        elif part == "rfc822.header":
            result = ""
            mess = self.msg()
            seen = []
            for h in mess.keys():
                if not h in seen:
                    seen.append(h)
                    v = mess.get_all(h, [])
                    for x in v:
                        result += (h + ": " + str(x) + '\r\n')
            result += '\r\n'
            # note("%s is %s", part, result)
            return "RFC822.HEADER {%d}\r\n" % len(result) + result

        elif part == "rfc822.text":
            mess = self.msg()
            if mess.get_content_maintype() == "multipart":
                s = self.join_multipart(mess)
            elif mess.get_content_maintype() == "message":
                s = self.as_string(ms=mess.get_payload()[0])
            else:
                s = mess.get_payload()
            self.set_flag("\\Seen")
            return 'RFC822.TEXT {%d}\r\n' % len(s) + s

        elif part == "rfc822":
            s = self.as_string()
            self.set_flag("\\Seen")
            return 'RFC822 {%d}\r\n' % len(s) + s

        else:

            m = BODYPATTERN.match(part)
            if m:
                peek = m.group("peek")
                hasfields = m.group("hasfields")
                segment = m.group("segment")
                fields = m.group("fieldspec")
                first_octet = int(m.group("firstoctet") or "-1")
                octet_count = int(m.group("octetcount") or "-1")
                partspec = m.group("partspec")

                mess = self.find_message_part(partspec)
                if mess is None:
                    note("Can't find part %s for %s", partspec, self)
                    return None

                is_message_part = (partspec and (mess.get_content_type().lower() == "message/rfc822"))

                # note("part is '%s', segment is '%s', fields is '%s', message is %s", part_as_given, segment, fields, self.get_body_structure(ms=mess))

                if not hasfields:
                    # simple body
                    return part_as_given + ' ' + self.get_body_structure(ms=mess, ext_data=(m.group("structure") is not None))

                elif (not segment):

                    # whole thing -- body[] or body.peek[]
                    s = self.as_string(ms=mess)
                    if (first_octet >= 0):
                        s = s[min(len(s),first_octet):min(len(s),first_octet+octet_count)]
                    if not peek:
                        self.set_flag("\\Seen")
                    # note("for %s, body is '%s'", part_as_given, repr(s))
                    return 'BODY[]%s {%d}\r\n' % (((first_octet >= 0) and '<%s>' % first_octet) or "", len(s)) + s

                elif (not fields):

                    # body[n] or body.peek[n]
                    # skip the headers for this part
                    if mess.get_content_maintype() == "multipart":
                        s = self.join_multipart(mess)
                    elif mess.get_content_maintype() == "message":
                        s = self.as_string(ms=mess.get_payload()[0])
                    else:
                        s = mess.get_payload()
                    if (first_octet >= 0):
                        s = s[min(len(s),first_octet):min(len(s),first_octet+octet_count)]
                    if not peek:
                        self.set_flag("\\Seen")
                    # note("for %s, body is '%s'", part_as_given, repr(s))
                    return 'BODY[%s]%s {%d}\r\n' % (segment, ((first_octet >= 0) and '<%s>' % first_octet) or "", len(s)) + s

                elif partspec and (fields == "mime"):

                    # BODY[n.MIME] (or peek)
                    result = ""
                    seen = []
                    for h in mess.keys():
                        if not h in seen:
                            seen.append(h)
                            v = mess.get_all(h, [])
                            for x in v:
                                result += (h + ": " + str(x) + '\r\n')
                    result += '\r\n'
                    # note("%s is %s", part, result)
                    if not peek:
                        self.set_flag("\\Seen")
                    return "BODY[%sMIME] {%d}\r\n" % ((partspec and "%s." % partspec) or "", len(result)) + result

                elif fields and fields.startswith("header.fields") and ((not partspec) or is_message_part):
                    inverted = fields.startswith("header.fields.not")
                    p1 = part_as_given.index('(')
                    p2 = part_as_given.index(')')
                    fields_as_given=part_as_given[p1:p2+1]
                    fieldnames = [x.strip() for x in part[p1+1:p2].split(' ')]
                    result = ""
                    if inverted:
                        for h in mess.keys():
                            if h.lower() not in fieldnames:
                                fieldnames.append(h.lower())
                                v = mess.get_all(h, [])
                                for x in v:
                                    result += (h + ": " + str(x) + '\r\n')
                    else:
                        for h in fieldnames:
                            v = mess.get_all(h, [])
                            for x in v:
                                result += (h + ": " + str(x) + '\r\n')
                    result += '\r\n'
                    # note("%s is %s", part, result)
                    if not peek:
                        self.set_flag("\\Seen")
                    fields = fields[:fields.index('(')-1].strip().upper()
                    return "BODY[%s%s %s] {%d}\r\n" % ((partspec and "%s." % partspec) or "", fields, fields_as_given, len(result)) + result

                elif (fields == "header") and ((not partspec) or is_message_part):
                    result = ""
                    keys = mess.keys()
                    seen = []
                    for h in keys:
                        if not h in seen:
                            seen.append(h)
                            v = mess.get_all(h, [])
                            for x in v:
                                result += (h + ": " + str(x) + '\r\n')
                    result += '\r\n'
                    # note("%s is %s", part, result)
                    if not peek:
                        self.set_flag("\\Seen")
                    return "BODY[%sHEADER] {%d}\r\n" % ((partspec and "%s." % partspec) or "", len(result)) + result

                elif (fields == "text") and ((not partspec) or is_message_part):

                    if mess.get_content_maintype() == "multipart":
                        s = self.join_multipart(mess)
                    elif mess.get_content_maintype() == "message":
                        s = self.as_string(ms=mess.get_payload()[0])
                    else:
                        s = mess.get_payload()
                    if (first_octet >= 0):
                        s = s[min(len(s),first_octet):min(len(s),first_octet+octet_count)]
                    if not peek:
                        self.set_flag("\\Seen")
                    # note("for %s, body is '%s'", part_as_given, repr(s))
                    return 'BODY[%sTEXT]%s {%d}\r\n' % ((partspec and "%s" % partspec) or "", ((first_octet >= 0) and '<%s>' % first_octet) or "", len(s)) + s

        raise ValueError("Can't interpret part '%s'" % part)

# ===========================================================================
#  Mailbox object
# ===========================================================================

class mailbox:

    def __init__(self, name, ids=None, flags=None, allseen=False):
        self.uid_validity_value = int(time.time() * 100)
        self.name = name
        self.next_uid_val = 1
        self.allseen = allseen

        # list of messages in UID val sort order
        self.msglist = []

        # mapping of UID value to message
        self.msgs = {}

        if flags is None:
            self.flags = []
        else:
            self.flags = flags
        self.recent_msgs = []

        # add initial messages
        if ids is not None:
            for id in ids:
                newmsg = message(self, id, None, (self.allseen and ['\\Seen']) or [])
                self.add_message(newmsg)

    def get_by_seq_no(self, msg_seq_no):
        if (0 < msg_seq_no <= len(self.msglist)):
            return self.msglist[msg_seq_no-1]

    def rescan(self, clear_recency=False):
        pass

    def messages(self, clear_recency=False, flag=None):
        self.rescan(clear_recency)
        return self.msglist
        keys = self.msgs.keys()
        # return in sort order of sequence numbers
        keys.sort()
        return [self.msgs[key] for key in keys if ((flag is None) or (self.msgs[key].test_flag(flag)))]

    def get_internaldate(self, msg):
        raise NotImplementedError("get_internal_date not implemented for this mailbox")

    def create_message_generator(self, spec, uses_uids):
        if not self.msgs:
            return
        p = spec.split(',')
        for subseq in p:
            p2 = subseq.split(':')
            if len(p2) == 2:
                if p2[0] == '*':
                    if uses_uids:
                        minval = max(self.msgs.keys())
                    else:
                        minval = len(self.msglist)
                else:
                    minval = int(p2[0].strip())
                if p2[1] == '*':
                    if uses_uids:
                        maxval = max(self.msgs.keys())
                    else:
                        maxval = len(self.msglist)
                else:
                    maxval = int(p2[1].strip())
                if minval > maxval:
                    minval, maxval = maxval, minval
                for v in range(minval, maxval + 1):
                    if uses_uids:
                        if self.msgs.has_key(v):
                            m = self.msgs[v]
                            yield self.msglist.index(m)+1, m
                    elif (1 <= v <= len(self.msglist)):
                        yield v, self.msglist[v-1]
            else:
                v = int(p2[0].strip())
                if uses_uids:
                    if self.msgs.has_key(v):
                        m = self.msgs[v]
                        yield self.msglist.index(m)+1, m
                elif (1 <= v <= len(self.msglist)):
                    yield v, self.msglist[v-1]

    def get_msg_as_email (self, id):
        raise NotImplementedError("get_msg_as_email not implemented for this version of 'mailbox'")

    def min_unseen (self):
        return 1

    def copy_message(self, oldmsg):
        newmsg = message(self, oldmsg.mbox_id, None, (self.allseen and ['\\Seen']) or [])
        self.add_message(newmsg)
        return newmsg.uid

    def add_message(self, newmsg):
        if newmsg.uid is None:
            newmsg.uid = self.next_uid_val
            self.next_uid_val += 1
        # insert sorted into msglist
        insort(self.msglist, newmsg)
        self.msgs[newmsg.uid] = newmsg
        if newmsg not in self.recent_msgs:
            self.recent_msgs.append(newmsg)

    def get_seq_no(self, msg):
        if msg in self.msglist:
            return self.msglist.index(msg)+1
        raise ValueError("msg %s not in mailbox %s" % (msg, self))

    def search (self, charset, args):
        raise NotImplementedError("search not implemented")

    def remove_message(self, m):
        if m in self.msglist:
            self.msglist.remove(m)
        if m.uid in self.msgs:
            del self.msgs[m.uid]
        if m in self.recent_msgs:
            self.recent_msgs.remove(m)

    def recent(self):
        return self.recent_msgs

    def may_have_children(self):
        raise NotImplementedError("may_have_children not implemented")

    def read_only(self, client):
        return True

# ===========================================================================
#  Mail context
# ===========================================================================

class namespace:

    def __init__(self, rootpath, separator):
        self.root = rootpath
        self.separator = separator

    def __str__(self):
        return '("%s" "%s")' % (self.root, self.separator)

class mailcontext:

    def __init__(self, inbox=None, mailboxes=None, subscribed=None):
        self.inbox = inbox
        if mailboxes is None and self.inbox:
            self.mailboxes = [self.inbox]
        else:
            self.mailboxes = mailboxes
        if subscribed is None:
            self.subscribed = []
        else:
            self.subscribed = subscribed

    def capabilities(self, client=None):
        raise NotImplementedError("capabilities() method not implemented for this mailcontext %s" % repr(self))

    def namespaces(self, encrypted_channel=False):
        # by default, no namespaces
        return ((), (), ())

    def __str__(self):
        return "<mailcontext %d mailboxes>" % len(self.mailboxes)

    def check_login (self, username, password, encrypted_channel=False):
        # returns a user-id object if OK, None otherwise
        return None

    def allow_anonymous_login(self, encrypted_channel=False):
        return False

    def remove_mailbox(self, mbox):
        if mbox and (mbox != self.inbox):
            self.mailboxes.remove(mbox)
            self.subscribed.remove(mbox)

    def add_message (self, mbox, flags, internaldate, text):
        raise NotImplementedError("add_message not implemented!")

    def redo_inbox(self, name_for_old_inbox):
        raise NotImplementedError("redo_inbox not implemented!")

    def find_matching_mailboxes(self, regexp, encrypted_channel=False):
        raise NotImplementedError("find_matching_mailboxes not implemented!")

    def create_idlethread(client, callback, flagseq):
        raise NotImplementedError("start_idle_thread not implemented")

    def checkpoint(self):
        pass

    def server_certificate_file(self):
        raise NotImplementedError("server_certificate_file not implemented for %s" % repr(self))

    def note(self, *args):
        """Usage:  note ([MIN_VERBOSITY_LEVEL (defaults to 1), ] FORMAT_STRING [, ARGS...])
        If CurrentVerbosityLevel is greater than or equal to MIN_VERBOSITY_LEVEL, will write
        the message to __note_sink."""
        pass


# ===========================================================================
#  clientchannel -- represents connection to the client
# ===========================================================================

class clientchannel:

    def push(self, thing):
        # push this 'thing' back to the client, serializing as appropriate
        raise NotImplementedError("push() not implemented for %s" % repr(self))

    def close_when_done(self):
        # mark this channel to be closed after the next call to "done"
        raise NotImplementedError("close_when_done() not implemented for %s" % repr(self))

    def done(self):
        # finished with this call; send results to client
        raise NotImplementedError("done() not implemented for %s" % repr(self))

    def can_tls(self):
        # returns None if this channel can support STARTTLS; a string explaining
        # why not if it can't
        raise NotImplementedError("can_tls() not implemented for %s" % repr(self))
        
    def starttls(self):
        # puts the channel in server-side SSL mode
        raise NotImplementedError("starttls() not implemented for %s" % repr(self))

    def start_authentication(self, authtype, client):
        # do an authentication handshake on the channel, and if successful,
        # return user object
        raise NotImplementedError("do_authentication() not implemented for %s" % repr(self))

    def do_idle(self, idlethread):
        # run idle loop
        raise NotImplementedError("do_idle() not implemented for %s" % repr(self))

    def is_secure(self):
        # returns True if connection is secure, False otherwise
        # Note that different implementations might have different ideas about what
        # this means.  UpLib, for instance, considers same-machine connections to
        # be secure even if not encrypted, because of its security model.
        raise NotImplementedError("is_secure() not implemented for %s" % repr(self))

# ===========================================================================
#  mailclient -- represents client state -- complete implementation
# ===========================================================================

class mailclient:

      def __init__ (self, channel, state, user, mailbox):

          self.channel = channel
          self.state = state
          self.user = user              # None for anonymous
          self.mailbox = mailbox

      def push (self, thing):
          self.channel.push(thing)

      def done (self, close=False):
          if close:
              self.channel.close_when_done()
          self.channel.done()
          if close:
              self.channel = None

      def secure (self):
          return self.channel.is_secure()

      def can_tls(self):
          # call this to see if channel can do STARTTLS.  If it returns None,
          # it can.  If it returns a string, it's a reason why it can't.
          return self.channel.can_tls()

      def starttls (self):
          # call this to start the actual TLS handshake on the channel
          self.channel.starttls()

# ===========================================================================
#  Request Object
# ===========================================================================

def by_name_length (v1, v2):
    return cmp(len(v1.name), len(v2.name))

class imap_request:

    def __init__ (self, tag, command, mailclient, mailcontext):
        self.tag = tag
        self.command = command and command.lower()
        self.args = []
        self.client = mailclient
        self.mailcontext = mailcontext

    def __str__(self):
        return '<' + self.__class__.__name__ + ' ' + str(self.tag) + ' ' + str(self.command) + '>'

    def valid(self):
        return (self.tag is not None)

    # --------------------------------------------------
    # user data
    # --------------------------------------------------

    def push (self, thing):
        self.client.channel.push(thing)

    def respond (self, msg):
        #if (type(msg) != types.StringType):
        #    note("attempt to push message not of String type:  <%s>", msg)
        self.push('* ' + msg + '\r\n')

    def finish (self, close=False, tags=None, response="OK", text="completed"):
        self.push("%s %s %s %s%s\r\n" % (self.tag, response, self.command.upper(), (tags and (tags + " ")) or "", text))
        self.client.done(close)

    def error (self, msg, close=False):
        note("IMAP error:  %s %s", self.tag, msg)
        self.push("%s BAD %s\r\n" % (self.tag, msg))
        self.client.done(close)

    def announce(self, msg):
        # send untagged msg
        self.client.push("* " + msg + '\r\n')
        self.client.done()

    def not_implemented(self):
        self.error("%s -- not implemented" % self.command.upper())

    def find_mailbox(self, reference_name, mailbox_name):
        if reference_name:
            mailbox_name = reference_name + mailbox_name
        # turn IMAP mailbox name wildcards into regexps
        mname_re = mailbox_name
        for c in "(.*+[])?{}^":
            mname_re = mname_re.replace(c, "\\" + c)
        mname_re = '^' + mailbox_name.replace("*", ".*").replace("%", "[^/]*") + '$'
        if not mname_re:
            return []
        hits = self.mailcontext.find_matching_mailboxes(mname_re, self.client.channel.is_secure())
        note("mailbox_name is %s, mname_re is %s, hits are %s", repr(mailbox_name), repr(mname_re), hits)
        return hits

    def hierarchy_names(self, reference_name, mailbox_name):
        # if the mailbox name ends with '%', we also need to return levels of
        # the hierarchy -- annoying inconsistency
        added = []
        hits = []
        if mailbox_name.endswith('%'):
            mname_re = '^' + mailbox_name[-1].replace("*", ".*").replace("%", "[^/]*") + '.*$'
            hits2 = self.mailcontext.find_matching_mailboxes(mname_re, self.client.channel.is_secure())
            hits2.sort(by_name_length)
            # now reduce to 'levels of the hierarchy'
            mname_re = '^' + mailbox_name.replace("*", ".*").replace("%", "[^/]*")
            for hit in hits2:
                h = re.match(mname_re, hit.name)
                if h:
                    name = h.group()
                    if name not in added:
                        added.append(name)
                        hits.append((name, not re.match('^[^/]+/categories/.*$', name),))
        return hits

    def show_mailbox_state(self, mbox):
        if mbox.messages():
            self.respond("%d EXISTS" % len(mbox.messages()))
        self.respond("%d RECENT" % len(mbox.recent()))
        self.respond("OK [UIDVALIDITY %d]" % mbox.uid_validity_value)
        self.respond("OK [UIDNEXT %d]" % mbox.next_uid_val)
        self.respond("OK [PERMANENTFLAGS (\Seen \Answered \Flagged \Deleted \Draft \Recent \*)]")
        self.respond("FLAGS (%s)" % string.join(mbox.flags, " "))

    def copy (self, msg_generator, source_uid_validity, mbox):

        # copy message from selected mailbox to target mailbox
        source = [source_uid_validity]
        target = [mbox.uid_validity_value]
        for msgno, msg in msg_generator:
            newuid = mbox.copy_message(msg)
            source.append(str(msg.uid))
            target.append(str(newuid))

        self.finish(tags="[COPYUID %s %s %s %s]" % (source[0], string.join(source[1:], ","), target[0], string.join(target[1:], ",")))

    def search (self, charset, searchargs, by_uid):
        # general strategy:  do a search to identify possible hits, then filter
        # with imap-specific exclusions
        note("search:  charset is %s, args are %s", charset, searchargs)
        return [((by_uid and str(msg.uid)) or str(seq_no)) for msg, seq_no in self.client.mailbox.search(charset, searchargs)]

    def store (self, msg_generator, msg_data_item_name, flags, by_uid=False):

        command = msg_data_item_name.lower()
        norespond = command.endswith(".silent")
        add = command.startswith("+")
        remove = command.startswith("-")

        for msgno, msg in msg_generator:

            if command.startswith("+"):
                for flag in flags:
                    msg.set_flag(flag)
            elif command.startswith("-"):
                for flag in flags:
                    msg.clear_flag(flag)
            else:
                msg.set_flags(flags)
            if not norespond:
                self.respond("%d FETCH (FLAGS (%s))" % ((by_uid and msg.uid) or msgno, string.join(msg.flags, " ")))

        self.finish()
        pass

    def fetch (self, seq_no_generator, fields, uses_uids):

        if type(fields) in types.StringTypes:
            fields = [ fields ]

        # handle macros
        if len(fields) == 1:
            if fields[0].lower() == "all":
                fields = ["FLAGS", "INTERNALDATE", "RFC822.SIZE", "ENVELOPE"]
            elif fields[0].lower() == "full":
                fields = ["FLAGS", "INTERNALDATE", "RFC822.SIZE", "ENVELOPE", "BODY"]
            elif fields[0].lower() == "fast":
                fields = ["FLAGS", "INTERNALDATE", "RFC822.SIZE"]

        if uses_uids and ("uid" not in fields) and ("UID" not in fields): fields.insert(0, 'UID')

        note(5, "fetch %s %s", seq_no_generator, fields)
        for seqno, msg in seq_no_generator:
            note(5, "fetching for msg %d (uid %d)", seqno, msg.uid)
            r = ""
            count = 0
            while count < len(fields):
                part = fields[count]
                if ((type(part) in types.StringTypes) and
                    (part.lower().endswith("[header.fields") or part.lower().endswith("[header.fields.not"))):
                    if ((count+2 < len(fields)) and
                        isinstance(fields[count+1], list) and
                        (fields[count+2].startswith(']'))):
                        part = part + ' (' + string.join(fields[count+1], ' ') + ')' + fields[count+2]
                        count += 2
                    else:
                        raise ValueError("bad part spec")
                partdata = msg.get_part(part)
                # note("partdata for %s is: %s", part, repr(partdata))
                # if (len(r) > 0) and (r[-1] not in string.whitespace):
                if len(r) > 0:
                    r += ' '
                r += partdata
                count += 1
            self.respond(str(seqno) + " FETCH (" + r + ")")
        self.finish()                

    def idle(self):

        # start a new thread, watching selected mailbox for changes

        if not self.client.mailbox:
            self.error("no mailbox selected")
            return
        
        def send_update(client, newmsgs, oldmsgs):
            for msg in oldmsgs:
                client.push('* %s EXPUNGE\r\n' % msg.uid)
            for msg in newmsgs:
                client.push('* %s EXISTS\r\n' % msg.uid)
            client.done()
        
        stopflag = threading.Event()
        t = self.mailcontext.create_idle_thread(self.client, send_update, stopflag)
        if t:
            # start thread in do_idle
            self.client.channel.start_idle(t, stopflag)
        else:
            raise RuntimeError("can't create IDLE thread")

    def start_authentication(self, authtype):
        self.client.channel.start_authentication(authtype, self)

    def finish_authentication(self, user):
        if user:
            self.client.state = STATE_AUTHENTICATED
            self.client.user = user
            self.finish(response="OK [CAPABILITY %s]"
                        % self.mailcontext.capabilities(self.client))
        else:
            self.error("authentication failed")

    def handle_request(self):

        if not self.valid():
            return

        if self.client.state == STATE_LOGOUT:
            return

        note("handle_request:  args are %s", self.args)

        # three commands are valid in any other state

        if self.command == "capability":
            self.respond('CAPABILITY ' + self.mailcontext.capabilities(self.client))
            self.finish()
            return

        elif self.command == "noop":
            if (self.client.state == STATE_SELECTED) and self.client.mailbox:
                # poll for new messages, send state of selected mailbox
                self.client.mailbox.rescan()
                self.show_mailbox_state(self.client.mailbox)
            self.finish()
            return

        elif self.command == "logout":
            self.mailcontext.checkpoint()
            self.respond('BYE IMAP4rev1 Server logging out')
            self.finish(close=True)
            return

        elif self.client.state == STATE_NOT_AUTHENTICATED:
            # only three other commands valid in this state

            if self.command == "starttls":
                if 'STARTTLS' not in self.mailcontext.capabilities(self.client):
                    excuse = "STARTTLS not supported"
                else:
                    excuse = self.client.can_tls()
                if excuse:
                    self.error(excuse)
                else:
                    self.finish()
                    self.client.starttls()
                return

            elif self.command == "login":
                if (len(self.args) == 2):
                    user = self.mailcontext.check_login(self.args[0], self.args[1],
                                                        self.client.channel.is_secure())
                    if user:
                        self.client.state = STATE_AUTHENTICATED
                        self.client.user = user
                        self.finish()
                    else:
                        self.error("Invalid authentication parameters")
                elif ((len(self.args) > 0) and (self.args[0].lower() == 'anonymous')
                      and self.mailcontext.allow_anonymous_login(self.client.channel.is_secure())):
                    self.client.state = STATE_AUTHENTICATED
                    self.client.user = None
                    self.finish()
                else:
                    self.error("Invalid password", True)
                return

            elif self.command == "authenticate":

                if (len(self.args) > 0) and (self.args[0].lower() == "plain"):
                    # implement PLAIN authentication
                    # see http://www.faqs.org/rfcs/rfc2595.html
                    # two possibilities, regular and SASL-IR

                    if len(self.args) == 2:
                        # SASL-IR
                        parts = base64.decodestring(self.args[1].strip()).split('\x00')
                        if len(parts) < 2 or len(parts) > 3:
                            self.error("Invalid authentication parameters")
                            return
                        user = self.mailcontext.check_login(parts[-2], parts[-1],
                                                            self.client.channel.is_secure())
                        if user:
                            self.client.state = STATE_AUTHENTICATED
                            self.client.user = user
                            self.finish(response="OK [CAPABILITY %s]"
                                        % self.mailcontext.capabilities(self.client))
                        else:
                            self.error("Invalid authentication parameters")
                    elif len(self.args) == 1:
                        self.client.channel.start_authentication("plain")
                        return

                    else:
                        self.error("badly-formatted AUTHENTICATE request")
                        
                elif ((len(self.args) > 0) and
                         (self.args[0].lower() == "anonymous") and
                         self.mailcontext.allow_anonymous_login(self.client.secure())):
                    # implement ANONYMOUS authentication
                    # see http://www.faqs.org/rfcs/rfc4505.html
                    # two possibilities, regular and SASL-IR

                    if len(self.args) == 2:
                        # SASL-IR
                        self.client.state = STATE_AUTHENTICATED
                        self.client.user = self.args[1]
                        self.finish(response="OK [CAPABILITY %s]"
                                    % self.mailcontext.capabilities(self.client))

                    elif len(self.args) == 1:
                        self.client.channel.start_authentication("anonymous")
                        return

                    else:
                        self.error("badly-formatted AUTHENTICATE request")

                else:
                    self.not_implemented()
                return

        else:

            if self.command == "select":

                if len(self.args) != 1:
                    self.error("bad arguments")
                else:
                    mboxes = self.find_mailbox("", self.args[0])
                    if not mboxes:
                        self.finish(response="NO")
                        self.client.mailbox = None
                        self.client.state = STATE_AUTHENTICATED
                    else:
                        self.client.mailbox = mboxes[0]
                        self.client.mailbox.rescan()
                        self.show_mailbox_state(self.client.mailbox)
                        self.client.state = STATE_SELECTED
                        if self.client.mailbox.read_only(self.client):
                            tags = "[READ-ONLY]"
                        else:
                            tags = "[READ-WRITE]"
                        self.finish(tags=tags)
                return

            elif self.command == "idle":
                try:
                    self.idle()
                except:
                    note("idle exception:\n%s", string.join(traceback.format_exception(*sys.exc_info())))
                    self.error("idle failed")
                return

            elif self.command == "examine":

                if len(self.args) != 1:
                    self.error("bad arguments")
                else:
                    mboxes = self.find_mailbox("", self.args[0])
                    if not mboxes:
                        self.finish(response="NO")
                        self.client.mailbox = None
                        self.client.state = STATE_AUTHENTICATED
                    else:
                        self.client.mailbox = mboxes[0]
                        self.client.mailbox.rescan()
                        self.show_mailbox_state(self.client.mailbox)
                        self.client.state = STATE_SELECTED
                        if self.client.mailbox.read_only(self.client):
                            tags = "[READ-ONLY]"
                        else:
                            tags = "[READ-WRITE]"
                        self.finish(tags=tags)
                return

            elif self.command == "create":

                if len(self.args) != 1:
                    self.error("bad arguments")
                else:
                    mboxes = self.find_mailbox("", self.args[0])
                    if not mboxes:
                        mbox_path = [x.strip() for x in self.args[0].split('/')]
                        base_path = ""
                        for piece in mbox_path:
                            if not piece:
                                continue
                            if base_path: base_path += '/'
                            base_path += piece
                            if not self.find_mailbox("", base_path):
                                mbox = self.mailcontext.create_new_mailbox(base_path)
                        self.finish()
                    else:
                        self.finish(response="NO", text="Mailbox '%s' already exists!" % self.args[0])
                return

            elif self.command == "delete":

                if len(self.args) != 1:
                    self.error("bad arguments")
                else:
                    mboxes = self.find_mailbox("", self.args[0])
                    if not mboxes:
                        self.finish(response="NO", text="no such mailbox '%s'" % self.args[0])
                    elif len(mboxes) > 1:
                        self.finish(response="NO", text="specification '%s' is ambiguous" % self.args[0])
                    elif mboxes[0] == self.mailcontext.inbox:
                        self.finish(response="NO", text="can't remove INBOX")
                    else:
                        self.mailcontext.remove_mailbox(mboxes[0])
                        self.finish()
                return


            elif self.command == "rename":

                if len(self.args) != 2:
                    self.error("bad arguments")
                    return

                mboxes = self.find_mailbox("", self.args[0])
                newbox = self.find_mailbox("", self.args[1])
                if len(newbox) > 0:
                    self.finish(response="NO", text="mailbox already exists")
                elif (len(mboxes) == 1) and (mboxes[0] == self.mailcontext.inbox):
                    self.mailcontext.redo_inbox(self.args[1])
                    self.finish()
                else:
                    self.finish(response="NO", text="renaming not permitted")
                return

            elif self.command == "subscribe":

                if len(self.args) != 1:
                    self.error("bad arguments")
                else:
                    mboxes = self.find_mailbox("", self.args[0])
                    if not mboxes:
                        self.error("no such mailbox %s" % self.args[0])
                    else:
                        for box in mboxes:
                            if not (box in self.mailcontext.subscribed):
                                self.mailcontext.subscribed.append(box)
                        self.finish()
                return

            elif self.command == "unsubscribe":

                if len(self.args) != 1:
                    self.error("bad arguments")
                else:
                    mboxes = self.find_mailbox("", self.args[0])
                    if not mboxes:
                        self.error("no such mailbox %s" % self.args[0])
                    else:
                        for box in mboxes:
                            self.mailcontext.subscribed.remove(box)
                        self.finish()
                return

            elif self.command == "list":

                if len(self.args) != 2:
                    self.error("bad arguments")
                    return
                elif self.args[1] == '':
                    # return hierarchy delimiter and the root name of the reference name
                    self.respond('LIST (\\Noselect) "/" ""')
                else:
                    boxes = []
                    for box in self.find_mailbox(self.args[0], self.args[1]):
                        # note("responding with %s", box)
                        self.respond('LIST (%s) "/" %s'
                                     % ((((not box.may_have_children()) and "\\Noinferiors") or ""),
                                        quote(box.name)))
                        boxes.append(box.name)
                    # if the mailbox name ends with '%', we also need to return levels of
                    # the hierarchy -- annoying inconsistency
                    if self.args[1].endswith('%'):
                        for name, noselect in self.hierarchy_names(self.args[0], self.args[1]):
                            if not name in boxes:
                                # note("responding with %s %s", name, noselect)
                                self.respond('LIST (%s) "/" %s' % ((noselect and "\\Noselect") or "", quote(name)))
                self.finish()
                return

            elif self.command == "lsub":

                if len(self.args) != 2:
                    self.error("bad arguments")
                else:
                    for box in self.mailcontext.subscribed:
                        self.respond('LSUB () "/" %s' % quote(box.name))
                    self.finish()
                return

            elif self.command == "status":

                if len(self.args) != 2:
                    self.error("bad arguments; should be mailbox name plus parenthesized list of flags")
                else:
                    mboxes = self.find_mailbox("", self.args[0])
                    flags = self.args[1]
                    if not mboxes:
                        self.finish(response="NO")
                    else:
                        for box in mboxes:
                            state = []
                            for flag in flags:
                                if flag == 'MESSAGES':
                                    state.append("MESSAGES %d" % len(box.messages()))
                                elif flag == 'RECENT':
                                    state.append("RECENT %d" % len(box.recent()))
                                elif flag == 'UIDNEXT':
                                    state.append("UIDNEXT %d" % box.next_uid_val)
                                elif flag == 'UIDVALIDITY':
                                    state.append("UIDVALIDITY %d" % box.uid_validity_value)
                                elif flag == 'UNSEEN':
                                    state.append("UNSEEN %d" % box.min_unseen())
                                else:
                                    raise ValueError("Invalid flag specifier '%s' given" % flag)
                            self.respond('STATUS %s (%s)' % (quote(box.name), string.join(state, ' ')))
                    self.finish()
                return

            elif self.command == "append":

                from email.Utils import parsedate

                # add a new message
                # syntax:  append MAILBOX [ FLAGS ] [ DATE ] MESSAGE

                if (len(self.args) < 2):
                    self.error("bad arguments")
                    return

                mbox = self.find_mailbox("", self.args[0])
                if not mbox:
                    self.error("no such mailbox '%s'" % self.args[0])
                    return

                message_text = self.args[-1]
                flags = []
                date = None
                if len(self.args) == 4:
                    flags = self.args[1]
                    date = parsedate(self.args[2])
                elif len(self.args) == 3:
                    if isinstance(self.args[1], list):
                        flags = self.args[1]
                    else:
                        date = parsedate(self.args[1])
                
                msg = self.mailcontext.add_message(mbox, flags, date or time.localtime(), message_text)
                self.finish(tags="[APPENDUID %d %d]" % (msg.mailbox.uid_validity_value, msg.uid))
                return

            elif self.command == "namespace":

                namespaces = self.mailcontext.namespaces(self.client.channel.is_secure())
                note("namespaces are %s", [str(x) for x in namespaces])
                if not namespaces[0]:
                    first = 'NIL'
                else:
                    first = '(' + string.join([str(x) for x in namespaces[0]]) + ')'
                if not namespaces[-1]:
                    last = 'NIL'
                else:
                    last = '(' + string.join([str(x) for x in namespaces[-1]]) + ')'
                self.respond('NAMESPACE ' + first + ' NIL ' + last)
                self.finish()                             
                return

            elif (self.client.state == STATE_SELECTED) and self.client.mailbox:
                
                if self.command == "check":

                    self.mailcontext.checkpoint()
                    self.finish()
                    return

                elif self.command == "close":

                    self.client.state = STATE_AUTHENTICATED
                    self.client.mailbox = None
                    self.finish()
                    return

                elif self.command == "expunge":

                    msgs = self.client.mailbox.messages(flag="\\Deleted")
                    for msg in msgs:
                        msg_seq_no = self.client.mailbox.get_seq_no(msg)
                        self.respond(str(msg_seq_no) + " EXPUNGE")
                        self.client.mailbox.expunge_message(msg)
                    self.finish()
                    return

                elif self.command == "search":

                    if (len(self.args) < 1) or ((self.args[0].lower() == "charset") and (len(self.args) < 3)):
                        self.error("not enough arguments")
                    if self.args[0].lower() == "charset":
                        charset = self.args[1]
                        args = self.args[2:]
                    else:
                        charset = "US-ASCII"
                        args = self.args
                    self.respond('SEARCH ' + string.join(self.search(charset, args, False), ' '))
                    self.finish()
                    return

                elif self.command == "fetch":

                    g = self.client.mailbox.create_message_generator(self.args[0], False)
                    self.fetch(g, self.args[1], False)
                    return

                elif self.command == "store":

                    if len(self.args) != 3:
                        self.error("invalid syntax for STORE")
                    else:
                        g = self.client.mailbox.create_message_generator(self.args[0], False)
                        self.store(g, self.args[1], args[2], False)
                    return

                elif self.command == "copy":

                    if len(self.args) != 2:
                        self.error("invalid args")
                    else:
                        mbox = self.find_mailbox("", self.args[1])
                        if not mbox:
                            self.finish(response="NO", tag="[TRYCREATE]", text="no such mailbox '%s'" % self.args[1])
                            return
                        elif len(mbox) != 1:
                            self.finish(response="NO", text="ambiguous mailbox specification '%s'" % self.args[1])
                            return
                        g = self.client.mailbox.create_message_generator(self.args[0], False)
                        self.copy(g, self.client.mailbox.uid_validity_value, mbox[0])
                    return

                elif self.command == "uid":

                    if len(self.args) < 1:
                        self.error("bad arguments")
                        return
                    subcommand = self.args[0].lower()
                    args = self.args[1:]

                    note ("UID -- subcommand is '%s', args are %s", subcommand, args)

                    self.command = self.command + ' ' + subcommand

                    if subcommand == "fetch":

                        g = self.client.mailbox.create_message_generator(args[0], True)
                        self.fetch(g, args[1], True)
                        return                        

                    elif subcommand == "search":

                        if (len(args) < 1) or ((args[0].lower() == "charset") and (len(args) < 3)):
                            self.error("not enough arguments")
                        if args[0].lower() == "charset":
                            charset = args[1]
                            args = args[2:]
                        else:
                            charset = "US-ASCII"
                        self.respond('SEARCH ' + string.join(self.search(charset, args, True), ' '))
                        self.finish()
                        return

                    elif subcommand == "copy":

                        if len(args) != 2:
                            self.error("invalid args")
                        else:
                            mbox = self.find_mailbox("", args[1])
                            if not mbox:
                                self.finish(response="NO", tag="[TRYCREATE]", text="no such mailbox '%s'" % args[1])
                                return
                            elif len(mbox) != 1:
                                self.finish(response="NO", text="ambiguous mailbox specification '%s'" % args[1])
                                return
                            g = self.client.mailbox.create_message_generator(args[0], True)
                            self.copy(g, self.client.mailbox.uid_validity_value, mbox[0])
                        return

                    elif subcommand == "store":

                        if len(args) != 3:
                            self.error("invalid syntax for UID STORE")
                        else:
                            g = self.client.mailbox.create_message_generator(args[0], True)
                            self.store(g, args[1], args[2], True)
                        return

                    elif subcommand == "expunge":

                        if len(args) != 1:
                            self.error("invalid args")
                            return

                        g = self.client.mailbox.create_message_generator(args[0], True)
                        for msg in msgs:
                            if msg.test_flag("\\Deleted"):
                                msg_seq_no = self.client.mailbox.get_seq_no(msg)
                                self.client.mailbox.expunge_message(msg)
                                self.respond(str(msg_seq_no) + " EXPUNGE")
                        self.finish()
                        return


                    self.not_implemented()
                    return

        # OK, bad command
        self.client.channel.log_info("Bad command -- " + self.command, 'warning')
        self.error("Bad command:  " + self.command)


    def parse_args (self, l):

        # returns the number of additional bytes needed to complete request

        if not l:
            # EOF
            return 0, False
        try:
            args = self.args
            stack = []
            count = 0
            litcount = False
            for i in range(len(l)):
                if l[i] == '"':
                    if stack and (stack[-1][0] == 'qstr'):
                        args.append(intern(l[stack[-1][1]:i]))
                        stack = stack[:-1]
                        #note("end-quote:  self.args is now %s", self.args)
                    elif stack and (stack[-1][0] == 'literal'):
                        stack = stack[:-1]
                    else:
                        stack.append(('qstr', i+1))
                elif l[i] == ')':
                    if stack and (stack[-1][0] == 'qstr'):
                        pass
                    elif (len(stack) > 1) and (stack[-1][0] == 'str') and (stack[-2][0] == 'parens'):
                        args.append(intern(l[stack[-1][1]:i]))
                        stack = stack[:-1]
                        #note("end-string:  self.args is now %s", self.args)
                        args = stack[-1][1]
                        stack = stack[:-1]
                        #note("end-paren:  self.args is now %s", self.args)
                    elif stack and (stack[-1][0] == 'parens'):
                        args = stack[-1][1]
                        stack = stack[:-1]
                        #note("end-paren:  self.args is now %s", self.args)
                    else:
                        raise ValueError("end-paren found not in a quoted string, and not in a parenthesized list:  <%s>" % l)
                elif l[i] == '(':
                    if stack and (stack[-1][0] == 'qstr'):
                        pass
                    else:
                        newlist = list()
                        args.append(newlist)
                        stack.append(('parens', args))
                        args = args[-1]
                elif l[i] == '\\' and stack and (stack[-1][0] == 'qstr') and (len(l) > (i+1)) and (l[i+1] in QUOTED_LITERALS):
                    stack.append(('literal', None))
                elif l[i] == '{':
                    stack.append(('count', i+1))
                    note("start-count at %s", i)
                elif l[i] == '}' and stack and (stack[-1][0] == 'count'):
                    if litcount and l[i-1] == '+':
                        count = int(l[stack[-1][1]:i-1])
                    else:
                        count = int(l[stack[-1][1]:i])
                    stack = stack[:-1]
                    note("end-count:  self.args is now %s", self.args)
                    break
                elif l[i] == '+' and stack and (stack[-1][0] == 'count'):
                    litcount = True
                    note("count is LITERAL+ syntax")
                elif (l[i] in string.digits) and (not litcount) and stack and (stack[-1][0] == 'count'):
                    pass
                elif stack and (stack[-1][0] == 'literal'):
                    stack = stack[:-1]
                elif (l[i] in string.whitespace) and stack and (stack[-1][0] == 'str'):
                    # end of string
                    args.append(intern(l[stack[-1][1]:i]))
                    stack = stack[:-1]
                    #note("end-string:  self.args is now %s", self.args)
                elif (l[i] not in string.whitespace) and ((not stack) or (stack[-1][0] not in ('str', 'qstr'))):
                    stack.append(('str', i))
                    
            if (len(stack) == 1) and (stack[0][0] == 'str'):
                args.append(l[stack[-1][1]:])
                stack = stack[:-1]
            elif stack:
                raise ValueError("End of command reached with non-empty stack!  %s" % stack)
        except:
            note("line was <%s>, stack is %s, exception is %s", l, stack, string.join(traceback.format_exception(*sys.exc_info())))
            raise
        return count, litcount
