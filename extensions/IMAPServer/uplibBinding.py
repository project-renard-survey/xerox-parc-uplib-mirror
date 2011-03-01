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
import time
import traceback
import weakref
import types
import base64
import quopri

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
from uplib.plibUtil import note, uthread, parse_date, id_to_time, configurator, subproc, get_fqdn, get_note_sink, format_date
from uplib.webutils import htmlescape
from uplib.basicPlugins import __output_document_icon as output_document_icon
from uplib.basicPlugins import STANDARD_BACKGROUND_COLOR, STANDARD_DARK_COLOR
from uplib.collection import PrestoCollection, QueryCollection
from uplib.createIndexEntry import index_folders
import uplib.emailParser as emailParser
from uplib.collection import PrestoCollection, QueryCollection
UPLIB_MIN_VERSION = "1.7"

# we know we have the right email package, but just in case
import email
versions = email.__version__.split(".")
note(4, "email version numbers are " + str(versions) + "\n")
if (not versions) or (int(versions[0]) < 4):
    raise ValueError("Need email package 4.x or higher for imapServer module")
import email.Utils
import email.Message
import email.Header
import email.Encoders
from email import message_from_string

# try for ssl module
try:
    import ssl
except ImportError:
    ssl = None

import time, base64

from IMAPServer.abstractclasses import mailbox, mailcontext, namespace, quote, message
from IMAPServer.abstractclasses import STATE_NOT_AUTHENTICATED
from IMAPServer.medusaHandler import imap_server

# ===========================================================================
#  All the UpLib-specific code
# ===========================================================================

class uplib_email_mailbox (mailbox):

    def __init__(self, name, mailcontextinst, category=None, flags=None, email_folder=True, ip=None, collection=None):

        query = (email_folder and '+apparent-mime-type:"message/rfc822"') or ""
        self.category = category
        self.collection = collection
        self.ip = ip
        self.mailcontext = weakref.ref(mailcontextinst)
        if collection:
            self.folder = collection
        else:
            if category:
                query += (' +categories:"' + category + '"')
            elif category == False:
                query += (' -categories:email')
            self.folder = PrestoCollection(mailcontextinst.repo, None, query)
        mailbox.__init__(self, name, ids=self.folder.docs(), flags=flags, allseen=(not email_folder))

    def __str__(self):
        return '<UpLib mailbox "%s", id=%x, %s messages>' % (self.name, id(self), (self.msglist and len(self.msglist) or 0))

    def __repr__(self):
        return '<UpLib mailbox "%s", id=%x, %s messages>' % (self.name, id(self), (self.msglist and len(self.msglist) or 0))

    def may_have_children(self):
        return not self.collection        

    def get_internaldate(self, msg):
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(msg.mbox_id.add_time()))

    def get_msg_as_email (self, doc):
        try:
            mime_type = doc.get_metadata("apparent-mime-type")
            if mime_type == "message/rfc822":
                f = os.path.join(doc.folder(), "originals")
                filepath = os.path.join(f, os.listdir(f)[0])
                fp = open(filepath, 'r')
                s = fp.read()
                fp.close()
                msg = message_from_string(s)
            else:

                def make_header(name, value):
                    try:
                        v = value.encode("US-ASCII")
                        charset = "US-ASCII"
                    except:
                        v = value.encode("UTF-8")
                        charset = "UTF-8"
                    return name, email.Header.Header(v, charset, 77, name).encode()

                def build_icon(doc):
                    icon = doc.document_icon()
                    img_part = email.Message.Message()
                    img_part.set_type("image/png")
                    cid = "%s.%s.%s.icon" % (self.ip, doc.repo.secure_port(), doc.id)
                    img_part.add_header("Content-ID", cid)
                    img_part.add_header("Content-Transfer-Encoding", "base64")
                    img_part.set_payload(base64.encodestring(icon))
                    return img_part

                def build_description(doc, display):
                    desc_part = email.Message.Message()
                    desc_part.set_type("text/html")
                    desc_part.add_header("Content-Transfer-Encoding", "quoted-printable")
                    desc_part.set_payload(quopri.encodestring('<html><body bgcolor="%s">' % STANDARD_BACKGROUND_COLOR +
                                                              display.encode('UTF-8') + "</body></html>\n"), "UTF-8")
                    return desc_part

                icon_payload = build_icon(doc)
                display, name = self.build_html_abstract_display(doc, icon_payload.get("Content-ID"))
                msg = email.Message.Message()
                msg.set_type("multipart/related;boundary=%s%s%s%s" % (self.ip, doc.repo.secure_port(), doc.id, long(time.time())))
                msg.add_header(*make_header("Message-ID", "%s:%s:%s" % (self.ip, doc.repo.secure_port(), doc.id)))
                d = doc.get_date()
                if d:
                    try:
                        d = email.Utils.formatdate(time.mktime((d[0], (d[1] or 1), (d[2] or 1), 0, 0, 0, 0, 1, -1,)))
                    except:
                        d = email.Utils.formatdate(id_to_time(doc.id))
                else:
                    d = email.Utils.formatdate(id_to_time(doc.id))
                msg.add_header(*make_header("Date", d))
                msg.add_header(*make_header("Subject", name))
                authors = doc.get_metadata("authors")
                if authors:
                    authors = authors.replace(" and ", ", ").replace('"', '\\"').replace('\r', '\\\r').replace('\\', '\\\\')
                    msg.add_header(*make_header("From", '"' + authors + '"'))
                body_payload = build_description(doc, display)
                msg.attach(body_payload)
                msg.attach(icon_payload)
                # note("msg is:\n%s", str(msg))
            return msg
        except:
            note("Exception getting document %s as email:\n%s", doc.id, string.join(traceback.format_exception(*sys.exc_info())))
            return None

    def _read_state(self, doc):
        d = doc.get_metadata("imap-state")
        if d:
            d = eval(d)
            note(5, "imap state for %s is %s", doc.id, d)
        if d and d.has_key(self.name):
            state = d[self.name]
            uid = state.get("uid")
            flags = state.get("flags")
            return uid, []
        return None, []

    def _save_state(self, doc, uid, flags):
        d = doc.get_metadata("imap-state")
        d = eval(d or "{}")
        d[self.name] = { "uid": uid, "flags": flags }
        note("imap state is now %s", repr(d))
        doc.update_metadata({"imap-state": repr(d)}, True)

    def add_message(self, msg):
        uid, flags = self._read_state(msg.mbox_id)
        if uid:
            msg.uid = uid
        else:
            msg.uid = self.next_uid_val
            self.next_uid_val += 1
        msg.flags = flags
        if self.allseen:
            msg.flags.append("\\Seen")
        if msg.mbox_id not in self.folder.docs():
            self.folder.include_doc(msg.mbox_id)
        doc = msg.mbox_id
        if self.category and (self.category not in doc.get_category_strings()):
            doc.add_category(self.category)
            msg.set_needs_saving()
        mailbox.add_message(self, msg)

    def build_html_abstract_display (self, doc, icon_cid):

        fp = StringIO()
        dict = doc.get_metadata()
        pubdate = dict.get("date")
        date = re.sub(" 0|^0", " ",
                      time.strftime("%d %b %Y, %I:%M %p",
                                    time.localtime(id_to_time(doc.id))))
        name = doc.id
        page_count = dict.get('page-count')
        summary = '<i>(No summary available.)</i>'
        if dict:
            if dict.has_key('title'):
                name = dict.get('title')
            elif dict.has_key('name'):
                name = '[' + dict.get('name') + ']'
        fp.write(u'<table border=0><tr><td>')
        fp.write(u'<center>')
        fp.write(u'<a href="https://%s:%d/action/basic/dv_show?doc_id=%s" border=0>' % (self.ip, doc.repo.secure_port(), doc.id))
        fp.write(u'<img src="cid:%s">' % icon_cid)
        fp.write(u'</a><p><small><font color="%s">(%s)</font></small></center></td><td>&nbsp;</td>'
                 % (STANDARD_DARK_COLOR, date))
        fp.write(u'<td valign=top><h3>%s</h3>' % htmlescape(name))
        if dict.has_key(u'authors') or pubdate:
            fp.write(u'<p><small>')
            if dict.has_key('authors'):
                fp.write(u'<b>&nbsp;&nbsp;&nbsp;&nbsp;%s</b>'
                         % (re.sub(' and ', ', ', dict['authors'])))
            if pubdate:
                formatted_date = format_date(pubdate, True)
                fp.write(u'&nbsp;&nbsp;&nbsp;&nbsp;<i><font color="%s">%s</font></i>' % (STANDARD_DARK_COLOR,
                                                                                        formatted_date))
            fp.write(u'</small>\n')
        if dict.has_key('comment'):
            summary = htmlescape(dict.get('comment', ''))
        elif dict.has_key('abstract'):
            summary = "<i>" + htmlescape(dict.get('abstract', '')) + '</i>'
        elif dict.has_key('summary'):
            summary = '<font color="%s">' % STANDARD_DARK_COLOR + htmlescape(dict.get('summary')) + '</font>'
        fp.write(u'<P>%s' % summary)
        if page_count:
            fp.write(u'<small><i><font color="%s"> &middot; (%s page%s)'
                     % (STANDARD_DARK_COLOR, page_count, ((int(page_count) != 1) and "s") or ""))
            fp.write(u'</font></i></small>\n')
        cstrings = doc.get_category_strings()
        fp.write(u'<p>Categories:  ')
        if cstrings:
            fp.write(string.join([htmlescape(s) for s in cstrings], u' &middot; '))
        else:
            fp.write('(none)')
        typ = doc.get_metadata("apparent-mime-type")
        if typ:
            mtype = ' &middot; <small>%s</small>' % typ
        else:
            mtype = ''
        fp.write(u'<p><a href="https://%s:%s/action/externalAPI/fetch_original?doc_id=%s&browser=true"><font color="%s">(Original%s)</font></a>'
                 % (self.ip, doc.repo.secure_port(), doc.id, STANDARD_DARK_COLOR, mtype))
        fp.write(u' &middot; <a href="https://%s:%s/action/basic/doc_pdf?doc_id=%s"><font color="%s">(PDF)</font></a>'
                 % (self.ip, doc.repo.secure_port(), doc.id, STANDARD_DARK_COLOR))
        if not mtype.lower().startswith("text/html"):
            fp.write(u' &middot; <a href="https://%s:%s/action/basic/doc_html?doc_id=%s"><font color="%s">(HTML)</font></a>'
                     % (self.ip, doc.repo.secure_port(), doc.id, STANDARD_DARK_COLOR))
        fp.write(u'</td></tr></table>')
        d = fp.getvalue()
        fp.close()
        return d, name

    def save_message(self, msg):
        doc = msg.mbox_id
        if os.path.isdir(doc.folder()):
            note("   saving flags for message mailbox=%s/uid=%s '%s'", msg.mailbox.name, msg.uid, msg.mbox_id.get_metadata("title"))
            self._save_state(msg.mbox_id, msg.uid, msg.flags)
            msg.saved()

    def remove_message(self, msg, save_state=True):
        mailbox.remove_message(self, msg)
        note("    removed from %s...", self)
        if self.category:
            try:
                msg.mbox_id.remove_category(self.category)
                note("    removed category %s from %s...", self.category, msg.mbox_id)
            except:
                note(2, "%s", ''.join(traceback.format_exception(*sys.exc_info())))
        elif self.collection:
            try:
                if isinstance(self.collection, PrestoCollection):
                    self.collection.exclude_doc(msg.mbox_id)
                    note("    excluded %s from %s...", msg.mbox_id, self.collection)
                elif msg.mbox_id in self.collection:
                    self.collection.exclude_doc(msg.mbox_id)
                    note("    excluded %s from %s...", msg.mbox_id, self.collection)
            except:
                note(2, "%s", ''.join(traceback.format_exception(*sys.exc_info())))
        else:
            # if neither category nor collection, self.folder is a PrestoCollection
            try:
                assert isinstance(self.folder, PrestoCollection)
                self.folder.exclude_doc(msg.mbox_id)
                note("    excluded %s from %s...", msg.mbox_id, self.folder)
            except:
                note(2, "%s", ''.join(traceback.format_exception(*sys.exc_info())))
                raise
        try:
            if save_state and msg.needs_saving():
                self.save_message(msg)
        except:
            note(2, "%s", ''.join(traceback.format_exception(*sys.exc_info())))

    def expunge_message(self, msg):
        note(3, "Expunging %s...", msg.mbox_id)
        self.remove_message(msg, save_state=False)
        remaining_categories = msg.mbox_id.get_category_strings()
        if "email" in remaining_categories:
            remaining_categories = list(remaining_categories)
            remaining_categories.remove("email")
        #note("    remaining categories in %s are %s...", msg.mbox_id, remaining_categories)
        # should we remove any categories not beginning with "email/"?
        repo = self.mailcontext().repo
        if repo.valid_doc_id(msg.mbox_id.id):
            if not remaining_categories:
                # no categories left, candidate for deletion
                if self.mailcontext().expunge_deletes_docs:
                    #note("    deleting document %s...", msg.mbox_id.id)
                    self.mailcontext().repo.delete_document(msg.mbox_id.id)
                elif self.mailcontext().expunge_deletes_inbox_docs and self.name.lower() == "inbox":
                    #note("    deleting document %s...", msg.mbox_id.id)
                    self.mailcontext().repo.delete_document(msg.mbox_id.id)
            else:
                self.save_message(msg)
        self.rescan()

    def rescan (self, clear_recency=False, callback=None):
        if clear_recency:
            self.recent_msgs = []
        self.folder.rescan()
        existing_msgs = [x.mbox_id for x in self.msgs.values()]
        current_docs = self.folder.docs()
        mailbox_uids = self.msgs.keys()[:]
        newmsgs = []
        delmsgs = []
        for uid in mailbox_uids:
            if self.msgs[uid].mbox_id not in current_docs:
                if callback: delmsgs.append(self.msgs[uid])
                self.remove_message(self.msgs[uid])
        for doc in self.folder.docs():
            if doc not in existing_msgs:
                msg = message(self, doc, None, [])
                self.add_message(msg)
                self.next_uid_val += 1
                if callback: newmsgs.append(msg)
        return newmsgs, delmsgs
            
    def checkpoint(self):
        for msg in self.msglist:
            if msg.needs_saving():
                self.save_message(msg)

#       ALL
#          All messages in the mailbox; the default initial key for
#          ANDing.

#       ANSWERED
#          Messages with the \Answered flag set.

#       BCC <string>
#          Messages that contain the specified string in the envelope
#          structure's BCC field.

#       BEFORE <date>
#          Messages whose internal date (disregarding time and timezone)
#          is earlier than the specified date.

#       BODY <string>
#          Messages that contain the specified string in the body of the
#          message.

#       CC <string>
#          Messages that contain the specified string in the envelope
#          structure's CC field.

#       DELETED
#          Messages with the \Deleted flag set.

#       DRAFT
#          Messages with the \Draft flag set.

#       FLAGGED
#          Messages with the \Flagged flag set.

#       FROM <string>
#          Messages that contain the specified string in the envelope
#          structure's FROM field.

#       HEADER <field-name> <string>
#          Messages that have a header with the specified field-name (as
#          defined in [RFC-2822]) and that contains the specified string
#          in the text of the header (what comes after the colon).  If the
#          string to search is zero-length, this matches all messages that
#          have a header line with the specified field-name regardless of
#          the contents.

#       KEYWORD <flag>
#          Messages with the specified keyword flag set.

#       LARGER <n>
#          Messages with an [RFC-2822] size larger than the specified
#          number of octets.

#       NEW
#          Messages that have the \Recent flag set but not the \Seen flag.
#          This is functionally equivalent to "(RECENT UNSEEN)".

#       NOT <search-key>
#          Messages that do not match the specified search key.

#       OLD
#          Messages that do not have the \Recent flag set.  This is
#          functionally equivalent to "NOT RECENT" (as opposed to "NOT
#          NEW").

#       ON <date>
#          Messages whose internal date (disregarding time and timezone)
#          is within the specified date.

#       OR <search-key1> <search-key2>
#          Messages that match either search key.

#       RECENT
#          Messages that have the \Recent flag set.

#       SEEN
#          Messages that have the \Seen flag set.

#       SENTBEFORE <date>
#          Messages whose [RFC-2822] Date: header (disregarding time and
#          timezone) is earlier than the specified date.

#       SENTON <date>
#          Messages whose [RFC-2822] Date: header (disregarding time and
#          timezone) is within the specified date.

#       SENTSINCE <date>
#          Messages whose [RFC-2822] Date: header (disregarding time and
#          timezone) is within or later than the specified date.

#       SINCE <date>
#          Messages whose internal date (disregarding time and timezone)
#          is within or later than the specified date.

#       SMALLER <n>
#          Messages with an [RFC-2822] size smaller than the specified
#          number of octets.

#       SUBJECT <string>
#          Messages that contain the specified string in the envelope
#          structure's SUBJECT field.

#       TEXT <string>
#          Messages that contain the specified string in the header or
#          body of the message.

#       TO <string>
#          Messages that contain the specified string in the envelope
#          structure's TO field.

#       UID <sequence set>
#          Messages with unique identifiers corresponding to the specified
#          unique identifier set.  Sequence set ranges are permitted.

#       UNANSWERED
#          Messages that do not have the \Answered flag set.

#       UNDELETED
#          Messages that do not have the \Deleted flag set.

#       UNDRAFT
#          Messages that do not have the \Draft flag set.

#       UNFLAGGED
#          Messages that do not have the \Flagged flag set.

#       UNKEYWORD <flag>
#          Messages that do not have the specified keyword flag set.

#       UNSEEN
#          Messages that do not have the \Seen flag set.


    def search (self, charset, args):
        # general strategy:  do a search for possible hits on header fields and/or
        # body text, then filter out things like "\Recent"

        def consume_args(charset, args, setset, prohibited_flags, required_flags, query):
            count = 0
            arg = args[count]
            charset = charset or "US-ASCII"
            arg = unicode(arg, charset, "strict").lower()
            if arg[0] in string.digits:
                seqset.append(('seq_nos', arg[0]))
            elif arg == u'uid' and arg[count+1][0] in string.digits:
                seqset.append(('uids', arg[0]))
            elif arg in (u"unanswered", u"undeleted", u"undraft", u"unflagged", u"unseen"):
                prohibited_flags.append(u"\\" + arg[2:].capitalize())
            elif arg in (u"answered", u"deleted", u"draft", u"flagged", u"seen"):
                required_flags.append(u"\\" + arg.capitalize())
            elif arg == u'old':
                prohibited_flags.append(u"\\Recent")
            elif arg == u'new':
                required_flags.append(u"\\Recent")
                prohibited_flags.append(u"\\Seen")
            elif arg == u'text':
                query += u' %s' % quote(unicode(args[count+1], charset, "strict"))
                count += 1
            elif arg == u'body':
                query += u' contents:%s' % quote(unicode(args[count+1], charset, "strict"))
                count += 1
            elif arg == u'subject':
                a = quote(unicode(args[count+1], charset, "strict"))
                query += u' (email-subject:%s OR title:%s)' % (a, a)
                count += 1
            elif arg in (u'to', u'cc', u'bcc'):
                # we don't handle "to" searches yet...
                count += 1
            elif arg in (u'smaller', u'larger'):
                # we don't handle "smaller" searches yet...
                count += 1
            elif arg == u'keyword':
                # we don't handle "keyword" searches yet...
                count += 1
            elif arg == u'since':
                d = email.Utils.parsedate(args[count+1])
                query += u' uplibdate:[%s/%s/%s TO NOW]' % (d[2], d[1], d[0])
            elif arg == u'before':
                d = email.Utils.parsedate(args[count+1])
                query += u' uplibdate:[1/1/1 TO %d/%d/%d]' % (d[2], d[1], d[0])
            elif arg == u'sentbefore':
                d = email.Utils.parsedate(args[count+1])
                query += u' date:[1/1/1 TO %d/%d/%d]' % (d[2], d[1], d[0])
            elif arg == u'sentsince':
                d = email.Utils.parsedate(args[count+1])
                query += u' date:[%s/%s/%s TO NOW]' % (d[2], d[1], d[0])
            elif arg == u'senton':
                d = email.Utils.parsedate(args[count+1])
                query += u' date:[%s/%s/%s TO %s/%s/%s]' % (d[2], d[1], d[0], d[2], d[1], d[0])
            elif arg == u'header':
                # we don't do header yet
                count += 2
            elif arg == u'from':
                query += u' (email-from:%s OR author:%s)' % (quote(args[count+1]), quote(args[count+1]))
                count += 1
            elif arg == u'not':
                args, subquery = consume_args(charset, args[1:], None, [], [], "")
                count = -1
                if subquery:
                    query += u" -( " + subquery + " )"
            elif arg == u'and':
                args, subquery1 = consume_args(charset, args[1:], None, [], [], "")
                args, subquery2 = consume_args(charset, args, None, [], [], "")
                count = -1
                if (subquery1 and subquery2):
                    query += u" ( " + subquery1 + u" AND " + subquery2 + " )"
            elif arg == u'or':
                args, subquery1 = consume_args(charset, args[1:], None, [], [], "")
                args, subquery2 = consume_args(charset, args, None, [], [], "")
                count = -1
                if (subquery1 and subquery2):
                    query += u" ( " + subquery1 + u" OR " + subquery2 + u" )"
            elif arg == u'all':
                pass
            return args[count+1:], query

        def satisfies_flags (msg, required, prohibited):
            for f in required:
                if f not in msg.flags:
                    return False
            for f in prohibited:
                if f in msg.flags:
                    return False
            return True

        query = self.folder.query[:]
        if not isinstance(query, unicode):
            query = unicode(query, "UTF-8", "strict")
        seqset = []
        prohibited_flags = []
        required_flags = []
        while args:
            args, query = consume_args(charset, args, seqset, prohibited_flags, required_flags, query)
        note("query is %s, required_flags are %s, prohibited_flags are %s", repr(query), required_flags, prohibited_flags)
        hits = QueryCollection(self.folder.repository, None, query).docs()
        note("hits are %s", hits)
        count = 0
        while count < len(self.msglist):
            msg = self.msglist[count]
            if (msg.mbox_id in hits) and satisfies_flags(msg, required_flags, prohibited_flags):
                yield msg, count+1
            count += 1

    def read_only (self, client):
        return ((client.state == STATE_NOT_AUTHENTICATED) or (client.user is None))
        

CHECKPOINT_PERIOD = 600

def checkpoint_thread_fn (ctxt_weakref):

    while True:
        time.sleep(CHECKPOINT_PERIOD)
        ctxt = ctxt_weakref()
        # note("Checkpointing context %s...", ctxt)
        if (not ctxt):
            note("exiting checkpoint thread")
            return
        else:
            ctxt.checkpoint()
            ctxt = None

def idle_check_loop_thread_fn (mclient, update_fn, stopflag):

    try:
        while True:
            stopflag.wait(30.0)
            if stopflag.isSet() or not mclient.mailbox:
                # IDLE loop is done
                return
            newmsgs, oldmsgs = mclient.mailbox.rescan(callback=True)
            if newmsgs or oldmsgs:
                update_fn(mclient, newmsgs, oldmsgs)
    finally:
        note(3, "exiting IDLE thread for %s", mclient)

class uplib_mailcontext (mailcontext):

    IDENT = 'UpLib IMAP Server (V4r1)'

    def __init__(self, repo, expunge_deletes_docs=False, use_for_email=False, allow_readers=False, ip=None,
                 server_certificate_file=None):
        self.repo = repo
        self.ip = ip
        if use_for_email:
            email_namespace = (namespace("", "/"),)
        else:
            email_namespace = ()
        doc_namespace = (namespace(repo.name(), "/"),)
        self.__namespaces = (email_namespace, (), doc_namespace)
        self.expunge_deletes_docs = expunge_deletes_docs
        self.expunge_deletes_inbox_docs = use_for_email
        self.allow_readers = allow_readers
        self.__server_certificate_file = server_certificate_file
        self.__dir = os.path.join(repo.overhead_folder(), "imap")
        if not os.path.exists(self.__dir):
            os.mkdir(self.__dir)
        mboxes = []
        inbox = None
        subscribed = []
        subscriptions = []
        if os.path.exists(os.path.join(self.__dir, "subscribed")):
            # read subscriptions
            for line in open(os.path.join(self.__dir, "subscribed"), 'r'):
                subscriptions.append(line.strip())
        categories = repo.categories()
        if use_for_email:
            inbox = uplib_email_mailbox("INBOX", self, category=False, ip=self.ip)
            mboxes.append(inbox)
            for c in categories:
                if c.startswith("email/"):
                    name = string.join([x.strip() for x in c.split('/')][1:], '/')
                    if name:
                        box = uplib_email_mailbox(name, self, category=c, ip=self.ip)
                        note("new mailbox %s", box)
                        mboxes.append(box)
                        subscribed.append(box)
        # build document context
        for c in categories:
            name = repo.name() + '/categories/' + string.join([x.strip() for x in c.split('/')], '/')
            if name:
                box = uplib_email_mailbox(name, self, category=c, email_folder=False, ip=self.ip)
                note("new mailbox %s", box)
                mboxes.append(box)
                if (("category " + c) in subscriptions) and (box not in subscribed):
                    subscribed.append(box)
        for cname, c in repo.list_collections():
            name = repo.name() + '/collections/' + cname
            if name:
                box = uplib_email_mailbox(name, self, category=None, email_folder=False, ip=self.ip, collection=c)
                note("new mailbox %s", box)
                mboxes.append(box)
                if (("collection " + c.name()) in subscriptions) and (box not in subscribed):
                    subscribed.append(box)
        mailcontext.__init__(self, inbox=inbox, mailboxes=mboxes, subscribed=subscribed)
        uthread.start_new_thread(checkpoint_thread_fn, (weakref.ref(self),))

    def __str__(self):
        return '<UpLib mailcontext for repository "%s"; %d mailboxes>' % (self.repo.name(), len(self.mailboxes))

    def capabilities(self, client=None):
        c = "IMAP4rev1"
        if (not client) or (not client.secure()):
            c += " LOGINDISABLED"
            if ssl:
                c += " STARTTLS"
        else:
            c += " LITERAL+"
            if (client.state == STATE_NOT_AUTHENTICATED):
                c += " SASL-IR AUTH=PLAIN"
                if self.allow_anonymous_login(True):
                    c += " AUTH=ANONYMOUS"
            #else:
            #    c += " NAMESPACE UIDPLUS IDLE"
            c += " NAMESPACE UIDPLUS IDLE"
        note("capabilities(%s) => %s", client, c)
        return c

    def namespaces(self, encrypted_channel=False):
        if encrypted_channel:
            return self.__namespaces
        else:
            return ((), (), ())
        
    def create_idle_thread(self, client, send_update, flag):
        # create a thread which will poll the client's selected mailbox
        # periodically while flag[0] is True, and call "send_update" with
        # two lists, of new messages and deleted messages, respectively
        return uthread.create_new_thread("IMAP IDLE for mailbox %s" % repr(client.mailbox),
                                         idle_check_loop_thread_fn, (client, send_update, flag))

    def create_new_mailbox(self, name):
        if not name:
            return None
        mbox = uplib_email_mailbox(name, self, category="email/" + name, ip=self.ip)
        self.mailboxes.append(mbox)
        return mbox

    def add_message (self, mailbox, flags, internaldate, text):
        # should return new message
        raise NotImplementedError("add_message not implemented")

    def redo_inbox(self, name_for_old_inbox):
        if not self.inbox:
            return
        old_inbox = self.inbox
        new_inbox_category_name = "email/" + name_for_old_inbox
        ids = []
        for doc in old_inbox.folder.docs():
            doc.add_category(new_inbox_category_name)
            ids.append(doc.id)
        index_folders(self.repo.docs_folder(), ids, self.repo.index_path())
        old_inbox.name = name_for_old_inbox
        self.inbox = uplib_email_mailbox("INBOX", self, category=False, ip=self.ip)
        self.mailboxes.append(self.inbox)

    def allow_anonymous_login(self, encrypted_channel=False):
        return (encrypted_channel and self.allow_readers)

    def check_login (self, username, password, encrypted_channel=False):
        # no usernames in UpLib
        if (encrypted_channel and (self.repo.check_password(password) or self.repo.check_password(""))):
            return (username or True)
        else:
            return False

    def find_matching_mailboxes(self, mname_re, encrypted_channel=False):
        hits = []
        # we don't disclose our mailboxes in the clear
        if encrypted_channel:
            for mbox in self.mailboxes:
                if re.match(mname_re, mbox.name):
                    hits.append(mbox)
            if not hits and self.inbox and re.match(mname_re, "inbox", re.IGNORECASE):
                hits.append(self.inbox)
        return hits

    def note(self, *args):
        apply(globals().get("note"), args)

    def checkpoint(self):

        note("Checkpointing context %s...", self)
        starttime = time.time()

        mailbox_names = []
        for box in self.mailboxes:
            box.checkpoint()
            mailbox_names.append(box.name)
        for c in self.repo.categories():
            parts = [x.strip() for x in c.split('/')]
            if parts[0] == 'email':
                name = string.join(parts[1:], '/')
                if name and (name not in mailbox_names):
                    box = self.create_new_mailbox(name)
                    note("new mailbox %s", box)
        # remember subscriptions
        if self.subscribed:
            fp = open(os.path.join(self.__dir, "subscribed"), 'w')
            try:
                for mbox in self.subscribed:
                    if mbox.category:
                        fp.write("category %s\n" % mbox.category)
                    elif mbox.collection:
                        fp.write("collection %s\n" % mbox.collection.name())
            finally:
                fp.close()

        duration = time.time() - starttime
        note("...finished checkpoint of %s; %f seconds", self, duration)

    def server_certificate_file(self):
        return self.__server_certificate_file

def shutdown_server (repo):
    # we cache the reference to the existing server in another
    # module so that we can reload this one with impunity
    current_server = emailParser.__dict__.get("IMAP_SERVER")
    if current_server:
        note("shutting down imap server %s...", current_server)
        current_server.close()
    imap_dir = os.path.join(repo.overhead_folder(), "imap")
    stunnel_pid_filepath = os.path.join(imap_dir, "stunnel.pid")
    if os.path.exists(stunnel_pid_filepath):
        stunnel_pid = int(open(stunnel_pid_filepath, 'r').read().strip())
    try:
        note("stopping imap stunnel process %d...", stunnel_pid)
        os.kill(stunnel_pid, signal.SIGKILL)
        os.unlink(stunnel_pid_filepath)
    except:
        pass

def manipulate_server_internal (repo, params, response=None, ipaddr=None, lgr=None):

    # regular UpLib action

    conf = params.get("configurator")
    if not conf:
        conf = configurator()
    imap_ssl_port = conf.get_int("imap-server-ssl-port", -1)
    imap_localhost_port = conf.get_int("imap-server-localhost-port", 8143)
    stunnel = conf.get("stunnel")
    expunge_deletes_docs = conf.get_bool("imap-expunge-deletes-documents", False)
    global CHECKPOINT_PERIOD
    CHECKPOINT_PERIOD = conf.get_int("imap-server-checkpoint-interval", 600)
    allow_anonymous_readers = ((not repo.has_password) and
                               conf.get_bool("imap-server-allow-anonymous-readers", True))
    use_for_email = conf.get_bool("imap-server-use-for-email", False)

    imap_dir = os.path.join(repo.overhead_folder(), "imap")
    if not os.path.isdir(imap_dir):
        os.mkdir(imap_dir)

    stunnel_pid_filepath = os.path.join(imap_dir, "stunnel.pid")
    if os.path.exists(stunnel_pid_filepath):
        stunnel_pid = int(open(stunnel_pid_filepath, 'r').read().strip())
    else:
        stunnel_pid = None

    # we cache the reference to the existing server in another
    # module so that we can reload this one with impunity
    current_server = emailParser.__dict__.get("IMAP_SERVER")
    note("current server is %s", current_server)

    action = params.get('action')
    newcontext = params.get('newcontext', False)

    if response:
        fp = response.open()
    else:
        fp = StringIO()

    fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    if current_server:
        s = current_server.status()
        m = s.more()
        while m:
            fp.write(m)
            m = s.more()
        fp.write('\n<hr>\n')
    else:
        fp.write('<h2>UpLib IMAP Server control panel</h2>\n')

    current_context = None
    if current_server and ((action == 'Stop') or (action == 'Restart')):

        if stunnel_pid:
            try:
                os.kill(stunnel_pid, signal.SIGKILL)
                time.sleep(4)
            except:
                pass
            stunnel_pid = None

        current_context = current_server.mailcontext
        current_server.close()
        current_server = None
        del emailParser.__dict__["IMAP_SERVER"]
        fp.write("<p>Closed current server.\n")

    if os.path.exists(stunnel_pid_filepath):
        os.unlink(stunnel_pid_filepath)

    if (action == 'Start') or (action == 'Restart'):

        cert_filepath = os.path.join(repo.overhead_folder(), repo.certfilename())
        
        try:
            port = params.get("port")
            if port:
                port = int(port)
            else:
                port = imap_localhost_port

            if stunnel and ((not ssl) or (imap_ssl_port > 0)):

                # start stunnel
                stunnel_conf_filepath = os.path.join(imap_dir, "stunnel.conf")
                f = open(stunnel_conf_filepath, 'w')
                f.write("debug = 7\n\ncert = %s\noutput = %s\npid = %s\n\n[imapuplib]\naccept = %s\nconnect = 127.0.0.1:%s\n" %
                        (cert_filepath, os.path.join(imap_dir, "stunnel.log"), stunnel_pid_filepath,
                         str(imap_ssl_port), str(port)))
                f.close()
                status, tsignal, output = subproc("%s %s" % (stunnel, stunnel_conf_filepath))
                note("status from '%s %s' (on %s) is %s, output is <%s>", stunnel, stunnel_conf_filepath, imap_ssl_port, status, output)
                if status != 0:
                    raise RuntimeError("Can't start stunnel with '%s %s'; status is %s, output is %s" % (stunnel, stunnel_conf_filepath, status, output))
                stunnel_pid = int(open(stunnel_pid_filepath, 'r').read().strip())
                note("stunnel_pid is %s", stunnel_pid)

            else:
                stunnel_pid = None

            if newcontext or (not current_context):
                current_context = uplib_mailcontext(repo,
                                                    expunge_deletes_docs=expunge_deletes_docs,
                                                    allow_readers=allow_anonymous_readers,
                                                    use_for_email=use_for_email,
                                                    ip=get_fqdn(),
                                                    server_certificate_file=cert_filepath)
            if current_context.inbox:
                current_context.inbox.rescan()
            if stunnel_pid is not None:
                ipaddr = '127.0.0.1'
            else:
                ipaddr = '0.0.0.0'

            if not lgr:
                lgr = logger.rotating_file_logger (os.path.join(imap_dir, "imap.log"), "weekly", None, True)
                lgr = logger.unresolving_logger(lgr)

            imaps = imap_server (current_context, ipaddr, port, logger=lgr, stunnel_pid=stunnel_pid)
            emailParser.__dict__["IMAP_SERVER"] = imaps
            current_server = imaps

            hooked = emailParser.__dict__.get("IMAP_SERVER_SHUTDOWN_HOOK")
            if not hooked:
                repo.add_shutdown_hook(lambda x=repo: shutdown_server(x))
                emailParser.__dict__["IMAP_SERVER_SHUTDOWN_HOOK"] = True

            if stunnel_pid:
                fp.write("<p>Started new IMAP4 server for %s on ports %s/%s."
                         % (repr(repo), str(imap_ssl_port), str(port)))
            else:
                fp.write("<p>Started new IMAP4 server for %s on port %s."
                         % (repr(repo), str(port)))
            if current_context.inbox:
                fp.write("<p>Inbox:  %d messages, %d recent, %d unseen."
                         % (len(current_context.inbox.msgs),
                            len(current_context.inbox.recent()),
                            current_context.inbox.min_unseen()))
        except:
            type, value, tb = sys.exc_info()
            s = string.join(traceback.format_exception(type, value, tb))
            note("Can't establish IMAP server:  exception:  " + s)
            fp.write(s)

    fp.write('<form method=GET action="/action/IMAPServer/manipulate_server">\n')
    fp.write('<input type=submit name=action value="Start" %s>\n' % ((current_server and "disabled") or ""))
    fp.write('<input type=submit name=action value="Stop" %s>\n' % (((current_server == None) and "disabled") or ""))
    fp.write('<input type=submit name=action value="Restart" %s>\n' % (((current_server == None) and "disabled") or ""))
    fp.write('<input type=checkbox name="newcontext" %s> Use fresh mail context\n' % (newcontext and "checked") or "")
    fp.write('</form>\n')
    fp.write('</body>\n')
    
