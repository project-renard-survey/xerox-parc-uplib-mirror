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

import sys, os, string

# simply installing the email package doesn't override the system-installed one
# So we need to see if it's installed, and if so, hack sys.path to make sure we
# load it.

import sys, os
from uplib.plibUtil import note, configurator
from uplib.webutils import htmlescape, get_content_type, html2unicode

# first make sure the local site-packages comes before the regular lib, in case the
# user has installed a newer version of email
from distutils.sysconfig import get_python_lib
sys.path.insert(0, get_python_lib())

# now make sure our site-packages is first, in case *we* have a newer version of email
installer_site_packages = os.path.join(configurator.default_configurator().get("uplib-home"), "lib", "python" + str(sys.version_info[0]) + "." + str(sys.version_info[1]), "site-packages")
sys.path.insert(0, installer_site_packages)

import email
versions = email.__version__.split(".")
note(4, "email version numbers are " + str(versions) + "\n")
if (not versions) or (int(versions[0]) < 4):
    raise ValueError("Need email package 4.x or higher for emailParser module")

from email.Iterators import _structure as show_message_structure
from email.message import Message

import re, traceback, cgi, types, shutil, urllib, time, pickle, codecs, struct, bisect, hashlib
from StringIO import StringIO

# need PIL for attachment images
from PIL import Image, ImageChops, ImageOps

# need ReportLab to measure size needed for HTML
from reportlab.pdfbase.pdfmetrics import stringWidth as reportLabStringWidth

from uplib.plibUtil import set_verbosity, true, false, subproc, MutexLock, read_metadata, id_to_time, figure_date_string, read_file_handling_charset, URLPATTERN, EMAILPATTERN, SECONDS_PER_WEEK, SECONDS_PER_DAY
from uplib.webutils import HTTPCodes, htmlescape, get_extension_for_type
from uplib.newFolder import AbortDocumentIncorporation
from uplib.addDocument import FakePDFDoc, mktempfile, Error, DocumentParser, mktempdir, MultiPartDocument, newline_expression, whitespace_expression, SUMMARY_LENGTH, alnum_chars
from uplib.collection import Collection
from uplib.ripper import Ripper

from uplib.basicPlugins import __issue_javascript_head_boilerplate as issue_javascript_head_boilerplate
from uplib.basicPlugins import __issue_menu_definition as issue_menu_definition
from uplib.basicPlugins import STANDARD_LEGEND_COLOR, STANDARD_BACKGROUND_COLOR, STANDARD_DARK_COLOR
from uplib.basicPlugins import TEMPORARY_COLLECTIONS, add_user_button, add_group_operation


SUBJ_CRUFT_PATTERN = re.compile(r"^((?P<re>[rR][eE]:)\s+)?\[[^]]+\]\s(?P<subj>.*)$")
HEADER_NEWLINE_PATTERN = re.compile("\n\s+", (re.MULTILINE|re.DOTALL))

DESIRABLE_FORMATS = [ "text/html", "text/plain" ]
ATTACHMENT_FORMATS = [ "text/calendar" ]
NON_NATURAL_SIZE_FORMATS = [ "text/html", "message/rfc822", "text/plain" ]

MAX_TEXT_LINE_LEN = 76


class emailRipper (Ripper):

    def __init__(self, repository):
        Ripper.__init__(self, repository)
        conf = configurator.default_configurator()
        self.suppress_duplicates = conf.get_bool("email-suppress-duplicates", True)

    def rip (self, location, doc_id):
        metadata_path = os.path.join(location, "metadata.txt")
        if os.path.exists(metadata_path):
            md = read_metadata(metadata_path)
            email_guid = md.get("email-guid")
            email_msg_id = md.get("email-message-id") or email_guid
            if self.suppress_duplicates:
                if email_guid:
                    # see if message is already here
                    hits = self.repository().do_query("email-guid:" + email_guid)
                    if hits:
                        doc = hits[0][1]
                        if email_guid:
                            # see if any of its attachments are here...
                            raise AbortDocumentIncorporation(
                                doc_id,
                                "message %s is already in the repository as %s" % (email_msg_id, hits[0][1]))


def clean_dangling_attachments (repo, response, params):

    repo.document_lock.acquire()
    try:

        to_remove = []
        for doc in repo.generate_docs():
            if doc in to_remove:
                continue
            att_id = doc.get_metadata("email-attachment-to")
            if not att_id:
                # not an attachment
                continue

            # first, check to see if the email is present
            hits = repo.do_query("email-guid:" + att_id)
            if not hits:
                # no, there's no containing message
                if doc not in to_remove:
                    to_remove.append(doc)
                continue
            else:
                # next, check to see if it mentions this attachment
                attachments = hits[0][1].get_metadata("email-attachments")
                if not attachments:
                    to_remove.append(doc)
                else:
                    attachment_ids = [x.strip() for x in attachments.split(",")]
                    if not doc.id in attachment_ids:
                        to_remove.append(doc)

        # now, remove the dups
        fp = response.open()
        if len(to_remove) < 1:
            fp.write("No duplicate attachments to remove\n")
        else:
            for doc in to_remove:
                note(2, "removing duplicate email attachment %s", doc)
                repo.delete_document(doc.id)
                fp.write("<p>removed %s\n" % htmlescape(str(doc)))
        fp.close()
    finally:
        repo.document_lock.release()

def initialize (repo, conf):

    def figure_thread (doc):
        if doc.get_metadata("apparent-mime-type") == "message/rfc822":
            note(3, "finding thread for email message %s...", doc)
            t = Thread.find_thread(doc.repo, doc.id, doc.get_metadata())
            note(3, "thread for message %s is %s (%s)", doc, t, t.get_forest())

    rippers = repo.rippers()
    rippers.insert(0, emailRipper(repo))
    if (repo.get_param("email-auto-thread") == "true") or conf.get_bool("email-auto-thread", False):
        repo.register_document_watcher(figure_thread, None, None)
    note("email initialized")

class AddressBook:

    def __init__(self):

        self.dict = {}

        conf = configurator.default_configurator()
        abfile = conf.get("address-book-filename")
        if not abfile:
            abfile = os.path.join("~", ".uplib-address-book")
        abfile = os.path.expanduser(abfile)
        if abfile and os.path.exists(abfile):
            for line in open(abfile, 'r'):
                if not line.strip():
                    continue
                try:
                    email, realname = line.strip().split('|')
                    self.dict[email] = realname
                except:
                    pass

    def email_to_name(self, email):
        return self.dict.get(email)

ADDRESS_BOOK = AddressBook()

def _get_content_type_harder(part):
    t = part.get_content_type()
    if t == "application/octet-stream":
        # see if we can figure out more
        name = part.get_param("name")
        if not name:
            name = part.get_param("filename", None, "Content-Disposition")
        if name:
            return get_content_type(name)
    else:
        return t

class EMail (FakePDFDoc):

    TNEF_PROGRAM = configurator.default_configurator().get("tnef")
    TNEF_COMMAND = configurator.default_configurator().get("tnef-command")
    HTMLDOC = configurator.default_configurator().get("htmldoc")
    WKPDF = configurator.default_configurator().get("wkpdf")
    WKHTMLTOPDF = configurator.default_configurator().get("wkhtmltopdf")

    def __init__(self, doc, options):
        self.pdffile = None
        FakePDFDoc.__init__(self, doc, options)
        self.checkocr = false
        self.__htmlform = None
        self.__options = options.copy()
        self.__msg = options.get("parsed-message")
        self.__htmldir = mktempdir()
        self.__minwidth = 0.0

    format_mimetype = "message/rfc822"

    BEFORE = ("TextDoc", "CardDoc", "SourceCode")
    AFTER = ("ImageDoc", "Video", "Music")               # don't want to try and load/parse these big image files

    def myformat(pathname):
        from email.Parser import Parser
        try:
            msg = Parser().parse(open(pathname, "r"))
        except:
            return False
        note(5, "message-id is %s, sender is %s, date is %s", msg.get("message-id"), (msg.get("from") or msg.get("sender")),msg.get("date"))
        if msg.get("message-id") and (msg.get("from") or msg.get("sender")) and msg.get("date"):
            return { "parsed-message" : msg }
        else:
            return False
    myformat = staticmethod(myformat)

    def find_name_from_address (address):
        return ADDRESS_BOOK.email_to_name(address)
    find_name_from_address=staticmethod(find_name_from_address)

    def figure_name (parsed_addr):
        pname, maddr = parsed_addr
        if pname and (not isinstance(pname, unicode)):
            pname = EMail.unicode_header(pname).strip()
        elif pname:
            pname = pname.strip()
        name = (EMail.find_name_from_address(parsed_addr[1]) or pname or parsed_addr[1])
        return name
    figure_name=staticmethod(figure_name)

    def unicode_header (headerval):
        from email.Header import decode_header
        parts = decode_header(headerval)
        val = u""
        for part in parts:
            try:
                pv = unicode(part[0], part[1] or "ASCII", "replace")
            except LookupError:
                pv = unicode(part[0], "iso-8859-1", "replace")
            val = val + pv
        val = HEADER_NEWLINE_PATTERN.sub(" ", val)
        return val
    unicode_header = staticmethod(unicode_header)

    def reflow_text(t, format, delsp):
        if format and format.lower() == 'flowed':
            lines = re.split('\r?\n', t)
            depth = 0
            flow_seq = []
            paragraphs = []
            for line in lines:
                space_stuffed = False
                flowed = False
                this_depth = 0
                while line and line[0] == '>':
                    this_depth += 1
                    line = line[1:]
                if line and line[0] == ' ':
                    space_stuffed = True
                    line = line[1:]
                if line and line[-1] == ' ':
                    flowed = True
                    if delsp == 'yes':
                        line = line[:-1]
                if (flow_seq and not flowed):
                    flow_seq.append(line)
                    paragraphs.append((depth, flow_seq,))
                    flow_seq = list()
                elif flowed and (this_depth != depth):
                    paragraphs.append((depth, flow_seq,))
                    flow_seq = [line,]
                    depth = this_depth
                elif flowed and line.startswith('-- '):
                    # signature line
                    paragraphs.append((depth, flow_seq,))
                    paragraphs.append((depth, [line,],))
                    flow_seq = []
                elif flowed:
                    flow_seq.append(line)
                else:
                    paragraphs.append((depth, [line,],))
#                 sys.stderr.write("%3d %s %s %s\n" % (depth, flowed and "F" or " ",
#                                                      space_stuffed and "S" or " ",
#                                                      line))
            if flow_seq:
                paragraphs.append((depth, flow_seq,))
            result = u""

#             result += '<pre>'
#             for depth, lines in paragraphs:
#                 if len(lines) == 1:
#                     # fixed line
#                     result += (lines[0] + '\n')
#                 else:
#                     result += ('>' * depth)
#                     result += ''.join([htmlescape(x) for x in lines]) + '\n'
#             result += '</pre>'

#             for depth, lines in paragraphs:
#                 if len(lines) == 1:
#                     # fixed line
#                     nline = htmlescape(lines[0]) + '<br>\n'
#                     while nline[0] == ' ':
#                         result += '&nbsp;'
#                         nline = nline[1:]
#                     result += nline
#                 else:
#                     result += ('>' * depth)
#                     nline = ''.join([htmlescape(x) for x in lines]) + '<br>\n'
#                     while nline[0] == ' ':
#                         result += '&nbsp;'
#                         nline = nline[1:]
#                     result += nline
            maxlen = 0
            result += "<tt>"
            for depth, lines in paragraphs:
                result += ('>' * depth)
                if len(lines) > 1:
                    nline = ''.join([htmlescape(x) for x in lines])
                elif len(lines) == 1:
                    nline = lines[0]
                else:
                    nline = ''
                if len(nline) > maxlen:
                    maxlen = len(nline)
                result += (nline + '<br/>\n')
            result += "</tt>"
        else:
            # format != flowed
            global MAX_TEXT_LINE_LEN
            lines = re.split(r'\r?\n', t)
            maxlen = max([len(x) for x in lines])
            if maxlen < MAX_TEXT_LINE_LEN:
                result = '<pre>\n' + htmlescape(t) + '</pre>\n'
            else:
                # we're going to re-flow them anyway
                result = "<pre>\r\n"
                for line in lines:
                    qprefix = re.search("^([>\s]+)", line)
                    if qprefix:
                        qprefix = qprefix.group(1)
                    else:
                        qprefix = ""
                    linedata = line[len(qprefix):]
                    while (len(linedata) + len(qprefix)) > MAX_TEXT_LINE_LEN:
                        maxpos = MAX_TEXT_LINE_LEN - len(qprefix)
                        for i in range(maxpos-1, maxpos-20, -1):
                            if linedata[i].isspace():
                                break
                        if i <= (maxpos - 20):
                            i = maxpos                  # no convenient whitespace
                        else:
                            maxpos = i
                        result += qprefix + htmlescape(linedata[:maxpos]) + " \\\r\n"
                        while (maxpos < len(linedata)) and linedata[maxpos].isspace():
                            maxpos += 1
                        linedata = linedata[maxpos:]
                    result += qprefix + htmlescape(linedata) + "\r\n"
                result += "<pre>\r\n"
#        sys.stderr.write('paragraphs are\n' + repr(paragraphs))
        return result, maxlen
    reflow_text = staticmethod(reflow_text)

    def format_message_as_html (msg, mainpart, attachments, base_url):

        from email.Utils import parsedate, getaddresses, parseaddr

        def format_body (parts, maxlen):

            rval = u""

            for part in parts:

                if part.get_content_type() == "text/plain":
                    text = part.get_payload(decode=True)
                    cset = part.get_param("charset")
                    flowed = part.get_param("format")
                    delsp = part.get_param("delsp")
                    if not isinstance(text, unicode):
                        try:
                            text = unicode(text, (cset or "iso-8859-1").lower())
                        except LookupError:
                            # assume we don't have the codec for that charset
                            text = unicode(text, "iso-8859-1")
                    # reflow text if necessary
                    text, ml2 = EMail.reflow_text(text, flowed, delsp)
                    maxlen = max(maxlen, ml2)
                    # find URLs and make them active links
                    start = 0
                    for url in URLPATTERN.finditer(text):
                        note(4, "found url %s, scheme '%s'", url.group("url"), url.group("scheme"))
                        scheme = url.group("scheme")
                        if scheme in ("http", "ftp", "https", "mailto"):
                            v = url.group("url")
                            rval += text[start:url.start("url")]
                            rval += ("<a href=\"" + v + "\">" + v + "</a>")
                            start = url.end("url")
                            note(4, "added url %s", url.group("url"))
                    rval += text[start:]
                    rval += "\n"
                elif part.get_content_type() == "text/html":
                    rval += '<br>\n'
                    # need to do some sub-processing
                    text = part.get_payload(decode=True)
                    cset = part.get_param("charset")
                    text = unicode(text, (cset or "iso-8859-1"))
                    note(4, "text of decoded HTML body is:\n%s", text)
                    # first, get rid of any <head> statement
                    m = re.search("<body.*?>", text, re.IGNORECASE)
                    if m:
                        text = text[m.end():]
                    # now trim off a trailing </html> or </body> statement
                    m = re.search("</html>|</body>", text, re.IGNORECASE)
                    if m:
                        text  = text[:m.start()]
                    rval += text
                    note(4, "rval for decoded trimmed HTML body is:\n%s", rval)
                elif part.get_content_maintype() == "multipart":
                    newval, maxlen = format_body(part.get_payload(), maxlen)
                    rval += newval
                elif part is not None:
                    note(3, "part.get_content_type() is %s", part.get_content_type())
                    rval += part.get_payload(decode=True)

            return rval, maxlen

        if not mainpart:
            mainpart = msg
        parts = ((type(mainpart) == type([])) and mainpart) or (mainpart,)

        note(3, "parts are %s, attachments are %s", [_get_content_type_harder(x) for x in parts], attachments)

        mailto_params = "?"
        subject = msg.get("subject")
        if subject:
            mailto_params += "subject="
            if not subject.lower().startswith("re: "):
                mailto_params += urllib.quote("Re: ")
            mailto_params += urllib.quote(subject)
        if len(mailto_params) > 1:
            mailto_params += "&"
        mailto_params += "In-Reply-To=%s" % urllib.quote(msg.get("message-id"))

        fromaddr = parseaddr(msg.get("from"))
        fromname = EMail.figure_name(fromaddr)

        reply_url = "mailto:%s%s" % (urllib.quote(fromaddr[1]), mailto_params)

        tos = msg.get_all('to', [])
        ccs = msg.get_all('cc', [])
        resent_tos = msg.get_all('resent-to', [])
        resent_ccs = msg.get_all('resent-cc', [])
        all_recipients = getaddresses(tos + ccs + resent_tos + resent_ccs)
        reply_to_all_url = reply_url[:]
        for recipient in all_recipients:
            reply_to_all_url += "&cc=%s" % urllib.quote(recipient[1])

        rval = u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                    "http://www.w3.org/TR/html4/strict.dtd">
                   <html><body>\n<table border=0>\n"""
        if msg.get("subject"):
            # rval += ("<tr><td colspan=2>Subject: <b>" + cgi.escape(EMail.unicode_header(subject)) + "</b></td></tr>\n")
            rval += ("<tr><td>Subject: <b>" + cgi.escape(EMail.unicode_header(subject)) + "</b></td></tr>\n")
        rval += ("<tr><td colspan=2>Date: <i>" + cgi.escape(msg.get("date")) + "</i></td></tr>\n")
        # rval += ("<tr><td>Date: <i>" + cgi.escape(msg.get("date")) + "</i></td></tr>\n")
        # rval += ("<tr><td>From: <a href=\"mailto:" + urllib.quote(fromaddr[1]) + "\" alt=\"reply to sender\"><b>" + cgi.escape(fromname) + "</b></a> <a href=\"%s\"><img border=0 src=\"%s\" align=right></a></td></tr>\n" % (reply_url, EMail.REPLY_TO_ICON_PATH))
        rval += ("<tr><td>From: <a href=\"mailto:" + urllib.quote(fromaddr[1]) + "\" alt=\"reply to sender\"><b>" + cgi.escape(fromname) + "</b></a></td><td align=right><a href=\"%s\"><small><i>[reply]</i></small></a></td></tr>\n" % (reply_url,))

        rval += "<tr><td>To: <i>"
        for recipient in all_recipients:
            name = EMail.figure_name(recipient)
            rval += ('<a href="mailto:%s">' % urllib.quote(recipient[1]) + cgi.escape(name) + "</a>, ")
        # rval = (rval[:-2] + "</i> <a href=\"%s\" alt=\"reply to all\"><img border=0 src=\"%s\" align=right></a></td></tr>\n" % (reply_to_all_url, EMail.REPLY_TO_ALL_ICON_PATH))
        rval = (rval[:-2] + "</i></td><td align=right><a href=\"%s\" alt=\"reply to all\"><small><i>[reply&nbsp;to&nbsp;all]</i></small></a></td></tr>\n" % (reply_to_all_url, ))

        maxlen = 0

        rval += "</table>\n<p>"

        newval, maxlen = format_body(parts, maxlen)
        rval += newval

        if attachments:
            rval += "<p>Attachments:\n"
            for attachment in attachments:
                rval += "<p>"
                id = attachment.get("repository-id")
                name = attachment.get("name") or id
                rval += ('<a href="%s/action/basic/dv_show?doc_id=%s" title="%s">' % (base_url, id, htmlescape(name,true)))
                if attachment.has_key("imagefilename"):
                    rval += ("<img src=\"" + attachment.get("imagefilename") + "\" border=1 bdcolor=gray align=top> &middot; ")
                rval += '%s</a></p>\n' % (attachment.get("name") or id)
            rval += "<br>\n"

        rval += "</body></html>\n"

        return rval, maxlen
    format_message_as_html = staticmethod(format_message_as_html)

    MENTIONED = re.compile(ur"[^,]+ (wrote|writes|schrieb|a \u00E9crit)\s*:")
    ATTRIBUTION_PATTERN = re.compile(ur"(?m)(^([^\n]+,)*(?P<writer>[^\n,]+) (wrote|writes|schrieb|a \u00E9crit)\s*:\s*$(\n)*\.\.\.\s*$)")

    def parse_mail_message (self):

        def code_message_id (id):
            return hashlib.sha1(id.strip()).hexdigest()

        def figure_summary (msg, mainpart, metadata):

            def substitute_name(matchobj):
                from email.Utils import parseaddr
                mstring = matchobj.group("writer").strip()
                fromaddr = parseaddr(matchobj.group("writer"))
                fromname = EMail.figure_name(fromaddr)
                return '[' + fromname + '] ...'

            if type(mainpart) == type([]):
                mainpart = mainpart[0]
            if mainpart.get_content_type() == "text/plain":
                text = mainpart.get_payload(decode=true)
                cset = mainpart.get_param("charset")
                try:
                    text = unicode(text, (cset or "iso-8859-1"))
                except LookupError:
                    text = unicode(text, "iso-8859-1")
                # replace any quoted text with "..."
                text = re.sub(r"(?m)(^>.*?$\n)+", '...\n', text)
                # attributions can take a long time, so check first if they're necessary
                needed = False
                for line in text.split("\n"):
                    needed = needed or (self.MENTIONED.search(line) is not None)
                if needed:
                    text = self.ATTRIBUTION_PATTERN.sub(substitute_name, text)
                text = re.sub(u"^\s*\u00B7\s+", "", re.sub(" /\s+/ ", u" \u00B7 ", re.sub("\s*\n\s*", u" \u00B7 ", text)), re.DOTALL | re.MULTILINE)
                metadata['email-summary'] = text[:min(500, len(text))]

        def parse_tnef (chunk):

            def redo_part(part):
                mtype = get_content_type(part)
                newpart = email.message.Message()
                newpart.set_payload(open(part, "rb").read())
                newpart.set_type(mtype)
                newpart.set_param("name", os.path.basename(part))
                note(4, "found TNEF part %s", newpart)
                os.unlink(part)
                return newpart

            if self.TNEF_PROGRAM:
                tf = mktempfile()
                td = mktempdir()
                fp = open(tf, "wb")
                fp.write(chunk.get_payload(decode=True))
                fp.close()
                parts = []
                cmd = self.TNEF_COMMAND % (self.TNEF_PROGRAM, td, tf)
                status, output, tsig = subproc(cmd)
                if status == 0:
                    os.unlink(tf)
                    files = os.listdir(td)
                    note(4, "tnef files are %s", files)
                    for file in files:
                        if not file.startswith("."):
                            parts.append(os.path.join(td, file))
                else:
                    note("tnef command <<%s>> failed with status %s and this output:\n%s",
                         cmd, status, output)
                parts = [redo_part(part) for part in parts]
                note(4, "tnef parts are %s", parts)
                os.rmdir(td)
                if len(parts) > 1:
                    return parts
                elif len(parts) > 0:
                    return parts
                else:
                    return []
            else:
                return []

        def parse_multipart (chunk):

            note(3, "doing parse_multipart(%s)...", chunk.get_content_type())

            selected_part = None
            attachments = []
            subtype = chunk.get_content_subtype()
            parts = chunk.get_payload()
            params = dict(chunk.get_params())
            note(3, "chunk is %s (%s/%s)\nget_params is %s\nparts are %s", repr(chunk), chunk.get_content_maintype(),
                 subtype, params, [_get_content_type_harder(x) for x in parts])

            if subtype == "mixed":
                selected_part = []
                for part in parts:
                    disposition = part.get("content-disposition")
                    if (_get_content_type_harder(part) in DESIRABLE_FORMATS) and ((len(selected_part) < 1) or (disposition == "inline")):
                        selected_part.append(part)
                    elif (part.get_content_maintype() == "multipart" and
                          part.get_content_subtype() in ("alternative", "signed", "mixed")):
                        sp, a = parse_multipart(part)
                        if type(sp) == type([]):
                            selected_part += sp
                        else:
                            selected_part.append(sp)
                        attachments += a
                    elif (part.get_content_maintype() == "application" and
                          part.get_content_subtype() == "ms-tnef"):
                        note(4, "parsing tnef part %s", part)
                        embedded_files = parse_tnef(part)
                        attachments += embedded_files
                    else:
                        attachments.append(part)

            elif subtype == "related" and params.get("type") == "multipart/alternative":
                for i in range(len(parts)):
                    if (parts[i].get_content_type() == "multipart/alternative"):
                        selected_part, attachments = parse_multipart(parts[i])
                        for part in (parts[:i] + parts[i+1:]):
                            disp = part.get("content-disposition")
                            if (not disp) or (not disp.startswith("inline")):
                                attachments.append(part)
                        note(4, "attachments are %s", [(x, x.get_content_type()) for x in attachments])
                        break

            elif subtype == "related":
                # these parts should all be glued together in order, but we're going
                # to pick one, then list the others as attachments
                selected_part_type_location = len(DESIRABLE_FORMATS)
                note(4, "multipart/related:  picking one of the %d parts...", len(parts))
                for part in parts:
                    note(4, "  looking at part %s with format %s...", repr(part), part.get_content_type())
                    if part.get_content_type() in DESIRABLE_FORMATS:
                        if selected_part:
                            i = DESIRABLE_FORMATS.index(part.get_content_type())
                            if (i < selected_part_type_location):
                                selected_part = part
                        else:
                            selected_part = part
                note(4, "picked %s (%s) for selected_part", repr(selected_part), selected_part.get_content_type())
                for part in parts:
                    if part != selected_part:
                        disp = part.get("content-disposition")
                        if disp:
                            note("content-disposition is %s", disp)
                        if not disp.startswith("inline"):
                            attachments.append(part)
                note(4, "attachments are %s", [(repr(x), x.get_content_type()) for x in attachments])

            elif subtype == "alternative" or subtype == "signed":
                # we can pick one of the parts, depending on what we like
                selected_part_type_location = len(DESIRABLE_FORMATS)
                for part in parts:
                    if part.get_content_type() in DESIRABLE_FORMATS:
                        if selected_part:
                            i = DESIRABLE_FORMATS.index(part.get_content_type())
                            if (i < selected_part_type_location):
                                selected_part = part
                        else:
                            selected_part = part
                    elif part.get_content_type() in ATTACHMENT_FORMATS:
                        # also pick this part as an attachment
                        attachments.append(part)

            elif subtype == "appledouble":
                # discard the "application/applefile" part
                for part in parts:
                    if part.get_content_type() == "application/applefile":
                        continue
                    selected_part = part
                    break

            else:
                note("can't figure out message %s with type %s", repr(msg), msg.get_content_type())

            while isinstance(selected_part, email.message.Message) and selected_part.get_content_maintype() == "multipart":
                selected_part, more_attachments = parse_multipart(selected_part)
                if more_attachments:
                    attachments += more_attachments

            return selected_part, attachments

        from email.Parser import Parser
        from email.Utils import parsedate_tz, parseaddr, mktime_tz, getaddresses

        msg = self.__msg or Parser().parse(open(self.doc, "r"))

        #show_message_structure(msg)

        htmlmsg = None
        metadata = {}

        sender = parseaddr(msg.get("from") or msg.get("sender"))
        metadata["authors"] = EMail.figure_name(sender).strip()
        if sender[0]:
            metadata["email-from-name"] = sender[0]
        if sender[1]:
            metadata["email-from-address"] = sender[1]
        metadata["email-message-id"] = msg.get("message-id")
        metadata["email-guid"] = code_message_id(msg.get("message-id"))

        # IETF standard headers for email threading
        in_reply_to = msg.get("in-reply-to")
        if in_reply_to:
            metadata["email-in-reply-to"] = string.join([code_message_id(x) for x in re.split(r'\s+', in_reply_to)], ", ")
        references = msg.get("references")
        if references:
            metadata["email-references"] = string.join([code_message_id(x) for x in re.split(r'\s+', references)], ", ")

        # some exchange headers, Thread-Topic and Thread-Index
        ttopic = msg.get("thread-topic")
        if ttopic:
            metadata["email-thread-topic"] = ttopic
        tindex = msg.get("thread-index")
        if tindex:
            metadata["email-thread-index"] = tindex

        date = msg.get("date")
        if date:
            parseddate = parsedate_tz(date)
            if parseddate:
                metadata["date"] = "%d/%d/%d" % (parseddate[1], parseddate[2], parseddate[0])
                metadata["email-time"] = str(mktime_tz(parseddate))
        subject = msg.get("subject")
        if subject:
            metadata["title"] = EMail.unicode_header(subject)
            metadata["email-subject"] = EMail.unicode_header(subject)

        mailto_params = "?"
        if subject:
            mailto_params += "subject="
            if not subject.lower().startswith("re: "):
                mailto_params += urllib.quote("Re: ")
            mailto_params += urllib.quote(subject)
        if len(mailto_params) > 1:
            mailto_params += "&"
        mailto_params += "In-Reply-To=%s" % urllib.quote(msg.get("message-id"))
        reply_url = "mailto:%s%s" % (urllib.quote(sender[1]), mailto_params)
        metadata['reply-to-url'] = reply_url

        tos = msg.get_all('to', [])
        ccs = msg.get_all('cc', [])
        resent_tos = msg.get_all('resent-to', [])
        resent_ccs = msg.get_all('resent-cc', [])
        all_recipients = getaddresses(tos + ccs + resent_tos + resent_ccs)
        reply_to_all_url = reply_url[:]
        for recipient in all_recipients:
            reply_to_all_url += "&cc=%s" % urllib.quote(recipient[1])
        metadata['reply-to-all-url'] = reply_to_all_url
        metadata['email-recipients'] = ' / '.join([x[1] for x in all_recipients if x[1].strip()])
        metadata['email-recipient-names'] = ' @ '.join([x[0] for x in all_recipients if (x[0] and x[0].strip())])

        if msg.get_content_maintype() == "multipart":

            selected_part, attachments = parse_multipart(msg)
            patt = []
            for attachment in attachments:
                t = attachment.get_content_maintype()
                if t == "multipart":
                    sp2, att2 = parse_multipart(attachment)
                    patt.append(sp2)
                    if att2: patt += att2
                elif t == "text":
                    # filter out blank parts of a message
                    if len(attachment.get_payload().strip()) > 0:
                        patt.append(attachment)
                else:
                    patt.append(attachment)
            figure_summary (msg, selected_part or msg, metadata)
            return msg, selected_part, patt, metadata

        else:
            # standard single-part message
            figure_summary (msg, msg, metadata)
            if msg.get_content_maintype() == "message":
                # forwarded message with nothing else in it
                # We create a dummy empty text body
                dummytext = Message()
                dummytext.add_header("Content-Type", "text/plain")
                dummytext.set_payload("")
                # and a dummy attachment part
                dummymsg = Message()
                dummymsg.add_header("Content-Type", "message/rfc822")
                dummymsg.set_payload([msg.get_payload()[0]])
                return msg, dummytext, [dummymsg], metadata
            else:
                return msg, None, None, metadata


    REPLY_TO_ICON_PATH = os.path.join(configurator().get("uplib-share"), "images", "tango-mail-reply-sender.png")
    REPLY_TO_ALL_ICON_PATH = os.path.join(configurator().get("uplib-share"), "images", "tango-mail-reply-all.png")

    def figure_pagewidth(self, t):
        # maxlen = self.__minwidth
        # HTMLDOC uses 11pt font for flowed text, 9pt for PRE text
        maxlen = 0
        while t:
            start = re.search('<pre[^>]*>', t)
            if start:
                t = t[start.end():]
                end = re.search('</pre[^>]*>', t)
                if end:
                    lines = t[:end.start()]
                    t = t[end.end():]
                else:
                    lines = t
                    t = None
                for l in lines.strip().split('\n'):
                    # find and strip any HTML
                    while True:
                        m = re.search('(<[^>]+>)', l)
                        if not m: break
                        l = l[:m.start()] + l[m.end():]
                    l = l.rstrip()
                    w2 = reportLabStringWidth(l, "Courier", 9)
                    #note("<%s> => %d", l.strip(), w2)
                    if w2 > maxlen:
                        maxlen = w2
            else:
                t = None
        return maxlen

    def get_pdf_version(self):
        if (not (self.pdffile and os.path.exists(self.pdffile))) and self.__htmlform:
            t = self.__htmlform.encode("ascii", "xmlcharrefreplace")
            margin = 18                 # 1/4 inch, in points
            minwidth = self.figure_pagewidth(html2unicode(self.__htmlform).encode("ascii", "replace"))
            minwidth = max((8.5 * 72) - (2 * margin), minwidth)
            tfile1 = os.path.join(self.__htmldir, "message.html")
            tfile2 = mktempfile()
            fp = open(tfile1, "w")
            fp.write(t)
            fp.close()
            pagesize = (((minwidth + (2 * margin))/72.0), 11.0)
            # note("minwidth is %s, pagesize is %s", minwidth, pagesize)
            try:
                margin /= 72.0          # convert to inches
                if self.HTMLDOC:
                    pagesize = "%.2finx%.2fin" % pagesize
                    cmd = '%s --webpage --links --header \"...\" --footer \"...\" --fontsize 12 --headfootsize 8 --size %s --no-strict --no-embedfonts --format pdf13 --links --linkstyle plain --linkcolor \"#000000\" --bottom %fin --top %fin --left %fin --right %fin -f %s %s' % (self.HTMLDOC, pagesize, margin, margin, margin, margin, tfile2, tfile1)
                elif self.WKHTMLTOPDF:
                    # wkhtmltopdf doesn't deal well with backslashes, so...
                    if sys.platform == "win32":
                        tfile1 = tfile1.replace(os.path.sep, "/")
                        tfile2 = tfile2.replace(os.path.sep, "/")
                    cmd = '%s --quiet --header-left "" --header-right "" --header-center "" --footer-left "" --footer-right "" --footer-center "" --disable-javascript --page-width %.2fin --page-height %.2fin --margin-bottom %fin --margin-top %fin --margin-left %fin --margin-right %fin "%s" "%s"' % (self.WKHTMLTOPDF, pagesize[0], pagesize[1], margin, margin, margin, margin, tfile1, tfile2)
                elif self.WKPDF:
                    cmd = '%s --stylesheet-media print --ignore-http-errors --format Letter --margin %f --source "%s" --output "%s"' % (self.WKPDF, margin, tfile1, tfile2)
                else:
                    note(0, "No converter from HTML to PDF available:  self.WKPDF is %s, self.WKHTMLTOPDF is %s, self.HTMLDOC is %s", self.WKPDF, self.WKHTMLTOPDF, self.HTMLDOC)
                    raise RuntimeError("No converter from HTML to PDF available")
                note(3, "converting mail to PDF with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if status == 0:
                    self.pdffile = tfile2
                else:
                    note(2, "pdf-ication of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile2): os.unlink(tfile2)
                    self.pdffile = None
                    raise Error("pdf-ication of %s failed with status %d:  %s" % (self.doc, status, output))
            finally:
                os.unlink(tfile1)
        return self.pdffile

    def _sensible_fname(fname):
        for char in "'\" \t\n\f:/":
            if char in fname:
                return False
        return True
    _sensible_fname=staticmethod(_sensible_fname)

    def process (self):
        # check for splitup splits
        msg, mainpart, attachments, md = self.parse_mail_message()
        self.__msg = msg
        resultslist = list()
        if attachments:
            note(5, "self.__options are %s", self.__options)
            note(5, "  ...found %d attachments in %s, processing each separately...", len(attachments), self.doc)
            note(4, "     attachments are:\n%s", string.join([("        " + repr(x) + " " + ((isinstance(x, list) and str([y.get_content_type() for y in x])) or x.get_content_type()) + "\n") for x in attachments], ""))
            attachment_results = list()
            for attachment in attachments:
                if isinstance(attachment, list):
                    note("found multipart attachment of type %s; don't know what to do with it",
                         [y.get_content_type() for y in attachment])
                    continue
                attachment_type = _get_content_type_harder(attachment)
                fname = attachment.get_param("filename", None, "content-disposition") or attachment.get_param("name")
                note(4, "fname is %s, attachment headers are %s", fname, attachment.items())
                if fname and EMail._sensible_fname(fname):
                    tdir = mktempdir()
                    tfile = os.path.join(tdir, fname)
                    if not os.path.splitext(fname)[1]:
                        ext = get_extension_for_type(attachment_type)
                        note(4, "adding extension '%s' to specified filename '%s'...", ext, fname)
                        tfile += "." + ext
                else:
                    tdir = None
                    tfile = mktempfile()
                    ext = get_extension_for_type(attachment_type)
                    if ext:
                        tfile += "." + ext
                fp = open(tfile, "wb")
                try:
                    if attachment_type == "message/rfc822":
                        fp.write(attachment.get_payload()[0].as_string())
                    elif attachment.is_multipart():
                        fp.write(attachment.as_string())
                    else:
                        fp.write(attachment.get_payload(decode=true))
                    fp.close()
                    newopts = self.__options.copy()
                    newopts['metadata'] = dict()
                    # not clear to me if using this is a better idea than letting the DocumentParser infrastructure figure it out
                    # newopts['metadata']['apparent-mime-type'] = attachment_type
                    if fname:
                        newopts['metadata']['email-attachment-filename'] = fname
                    newopts['upload'] = false
                    newopts['saveblanks'] = true
                    newopts['next-level-doc'] = self
                    if 'format' in newopts:
                        del newopts['format']
                    DocumentParser.parse_document(tfile, attachment_results, options=newopts)
                finally:
                    os.unlink(tfile)
                    if tdir is not None: os.rmdir(tdir)
            # do something
            note(4, "processed all attachments, results are %s, self.__options is %s", attachment_results, self.__options)
            attachments = list()
            count = 1
            for tfilename, result in attachment_results:
                note(5, "looking at %s...", result)
                if isinstance(result, DocumentParser):
                    note(5, "  building icon for %s...", result)
                    name = result.metadata.get("title")
                    folder = result.folder
                    im = Image.open(os.path.join(folder, "page-images", "page00001.png"))
                    if im.mode == 'L' or im.mode == '1' or im.mode == 'P':
                        im = im.convert('RGB')
                    if result.metadata.get("apparent-mime-type") in NON_NATURAL_SIZE_FORMATS:
                        bbox = ImageChops.invert(ImageOps.autocontrast(im.convert('L'))).getbbox()
                        if bbox:
                            bbox = (max(0, bbox[0]-20), max(0, bbox[1]-20), min(im.size[0], bbox[2]+20), min(im.size[1], bbox[3]+20))
                            im = im.crop(bbox)
                    width, height = im.size
                    if (width > height):
                        scaling_factor = 200.0 / width
                    else:
                        scaling_factor = 200.0 / height
                    newsize = (int(width * scaling_factor), int(height * scaling_factor))
                    im2 = im.resize(newsize, Image.ANTIALIAS)
                    imagefilename = os.path.join(self.__htmldir, "attachment%d.png" % count)
                    fp = open(imagefilename, "wb")
                    im2.save(fp, "PNG")
                    fp.close()
                    upload = False
                    newopts = self.__options.copy()
                    newopts['metadata'] = dict()
                    newopts['metadata']['email-attachment-to'] = md['email-guid']
                    if md.has_key('email-from-name'):
                        newopts['metadata']['email-from-name'] = md['email-from-name']
                    if md.has_key('email-from-address'):
                        newopts['metadata']['email-from-address'] = md['email-from-address']
                    if md.has_key('email-subject'):
                        newopts['metadata']['email-subject'] = md['email-subject']
                    if result.metadata.has_key("email-attachment-filename"):
                        newopts['metadata']['email-attachment-filename'] = result.metadata['email-attachment-filename']
                    if self.metadata.has_key('categories'):
                        newopts['metadata']['categories'] = self.metadata['categories']
                    date = result.metadata.get("date") or md.get('date')
                    if date: newopts['metadata']['date'] = date
                    newopts['metadata']['title'] = (result.metadata.get("title") or
                                                    result.metadata.get("email-attachment-filename") or
                                                    ('(attachment to "' + md.get("title") + '")'))
                    newopts['saveblanks'] = true
                    if 'format' in newopts:
                        del newopts['format']
                    d = result
                    if newopts.has_key('next-level-doc'):
                        d = newopts.get('next-level-doc')
                        while isinstance(d, EMail) and d.__options.has_key('next-level-doc'):
                            d = d.__options['next-level-doc']
                        newopts['upload'] = d.upload
                        if d.metadata.has_key('categories'):
                            newopts['metadata']['categories'] = d.metadata['categories']
                    r = DocumentParser.parse_document(folder, None, options=newopts)
                    id = (type(r[0][1]) in types.StringTypes) and r[0][1] or "foo"
                    note(4, "  adding %s to attachments as %s...", result, id)
                    attachments.append({"repository-id": id, 
                                        "name" : (newopts['metadata'].get('title') or id),
                                        "imagefilename" : os.path.split(imagefilename)[1] })
                count += 1

            resultslist = attachment_results

        note(4, "attachment_results are %s, attachments are %s", resultslist, attachments)

        # base_url = "%s://%s:%s" % (self.repository[2], self.repository[0], self.repository[1])
        base_url = "https://-uplib-"
        self.__htmlform, maxlen = self.format_message_as_html(msg, mainpart, attachments, base_url)
        self.__minwidth = reportLabStringWidth(maxlen * '0', 'Courier', 12)
        msgtime = time.strftime("%I:%M %p", time.localtime(float(md.get("email-time")))).lower()
        if msgtime[0] == '0':
            msgtime = ' ' + msgtime[1:]

        def process_subject (s):
            m = SUBJ_CRUFT_PATTERN.match(s)
            if m:
                p1 = m.group("re")
                if p1:
                    return p1 + " " + m.group("subj")
                else:
                    return m.group("subj")
            else:
                return s

        self.metadata['document-icon-legend'] = u'(20,40,0)%s|(20,80,100)%s %s|(150,50,0)%s' % (md.get("authors"), md.get("date"), msgtime, process_subject(md.get("title")))
        if attachments:
            self.metadata['email-attachments'] = string.join([x['repository-id'] for x in attachments if x.has_key("repository-id")], ", ")
        self.metadata.update(md)
        note(4, "metadata is %s", self.metadata)
        note(5, "HTML is\n%s", self.__htmlform)
        result = (self.doc, FakePDFDoc.process(self))
        resultslist.append(result)
        shutil.rmtree(self.__htmldir)
        return self

    def get_text(self):

        FakePDFDoc.get_text(self)
        # now trim off email header from contents.txt and wordbboxes file
        if os.path.exists(self.text_path()):
            text, charset, language = read_file_handling_charset(self.text_path(), True)
            # find and remove header, which will end with "[reply to all]"
            # this should be 'replace', but for now let's see the errors
            text = text.encode(charset, 'error')
            pos = string.find(text, "[reply to all]")
            if pos >= 0:
                pos += len("[reply to all]")
                while (pos < len(text)) and (text[pos] in string.whitespace) and (text[pos] != '\f'):
                    pos += 1
                text = text[pos:]
                if len(text.strip()) > 0:
                    note(4, "re-writing contents.txt to remove email headers...")
                    fp = open(self.text_path(), 'wb')
                    fp.write('Content-Type: text/plain; charset=%s\nContent-Language: %s\n' % (charset, language))
                    fp.write(text)
                    fp.close()
                    # now re-do wordbboxes
                    if os.path.exists(self.word_boxes_path()):
                        fp = open(self.word_boxes_path(), 'rb')
                        boxes = fp.read()
                        fp.close()
                        version = ord(boxes[10]) - ord('0')
                        if version == 1:
                            offset = 20
                            boxlen = 24
                        elif version == 2:
                            offset = 24
                            boxlen = 28
                        else:
                            raise ValueError("Can't understand version # %s in wordbboxes file" % version)
                        # now re-write it
                        note(4, "re-writing wordbboxes to remove email headers...")
                        fp = open(self.word_boxes_path(), 'wb')
                        # header
                        fp.write(boxes[:12])
                        pointer = 12
                        # now the data, adjusting the pointers
                        while pointer < len(boxes):
                            textoffset = struct.unpack(">I", boxes[pointer+offset:pointer+offset+4])[0]
                            if textoffset > pos:
                                fp.write(boxes[pointer:pointer+offset])
                                fp.write(struct.pack(">I", textoffset - pos))
                            pointer += boxlen
                        fp.close()
                else:
                    note(2, "Re-writing contents.txt would remove all contents!")

    def create_summary (self):

        # called to create a summary of the document.

        summarypath = self.summary_path()
        text = self.metadata.get("email-summary")
        if text:
            if not (type(text) == types.UnicodeType):
                text = unicode(text, "utf_8", "replace")
            text=text[:min(300, len(text))]
            text=re.sub(u" \u00B7 ", " / ", text)
            text=text.encode("ascii", "replace")
            f = open(summarypath, 'wb')
            f.write(text)
            f.close()
            os.chmod(summarypath, 0700)
            self.metadata["summary"] = text
        else:
            textpath = self.text_path()
            summarypath = self.summary_path()

            if os.path.exists(textpath):
                text = read_file_handling_charset(textpath)

                # now change newlines into / and collapse spaces

                text = newline_expression.sub(' / ', text)
                text = whitespace_expression.sub(' ', text)
                while text and not text[0] in alnum_chars:
                    # remove leading punctuation
                    text = text[1:]
                text = text[:min(SUMMARY_LENGTH, len(text))]
                text = text.encode("ascii", "replace")
                f = open(summarypath, 'wb')
                f.write(text)
                f.close()
                os.chmod(summarypath, 0700)
                self.metadata["summary"] = text



from uplib.collection import QueryCollection
from uplib.basicPlugins import STANDARD_BACKGROUND_COLOR, htmlescape, __issue_javascript_head_boilerplate, __issue_title_styles, __issue_menu_definition, _is_sensible_browser
from uplib.basicPlugins import __output_document_title as output_document_title
from uplib.basicPlugins import __output_document_icon as output_document_icon



THREADS = dict()
THREADS_LOCK = MutexLock("EmailThreadsIndex")

class Thread(Collection):

    def __init__(self, repository, id=None, barethread=None):
        self.forest = []
        self.threadtree = barethread
        Collection.__init__(self, repository, id)
        self.scantime = time.time()
        self.first_message_time = 0
        self.latest_message_time = 0
        self.__scanning = False

    def __cmp__(self, other):
        if self is other:
            return 0
        else:
            return cmp(self.first_message_time, other.first_message_time)

    def build_thread_tree (repo, doc_id, doc_metadata):

        added = list()

        def build_subtree(doc_id, doc_metadata):

            note(3, "building subtree for %s...", doc_id)
            if doc_id not in added:
                added.append(doc_id)
            msgid = doc_metadata.get("email-guid")
            if msgid:
                query = "email-references:" + msgid + " OR email-in-reply-to:" + msgid
                v = doc_metadata.get("email-thread-index")
                if v:
                    query += " OR email-thread-index:" + v + "*"
                hits = repo.do_query(query)
                refs = [build_subtree(doc.id, doc.get_metadata()) for score, doc in hits if (doc.id not in added)]
                note(4, "    references for %s...", doc_id)
                for ref in refs:
                    note(4, "       %s", ref[0])
            else:
                refs = []
            v = doc_metadata.get("email-attachments")
            if v:
                atts = [x for x in v.split(", ") if repo.valid_doc_id(x)]
                note(4, "    attachments to %s...", doc_id)
                for att in atts:
                    note(4, "       %s", att)
            else:
                atts = []
            return (doc_id, refs, atts)

        def get_metadata(repo, id):
            mdpath = os.path.join(repo.doc_location(id), "metadata.txt")
            if not os.path.exists(mdpath):
                mdpath = os.path.join(repo.pending_location(id), "metadata.txt")
                if not os.path.exists(mdpath):
                    return {}
            return read_metadata(mdpath)

        def quote_query(s):
            return re.sub(r'"', r'\"', s).replace('*', r'\*')

        # work our way to the top
        roots = [doc_id]
        attachment = doc_metadata.get("email-attachment-to")
        if attachment:
            docs = [doc.id for score, doc in repo.do_query("email-guid:" + attachment)]
            if docs:
                roots = docs
        roots.sort()
        while True:
            note(3, "Finding roots...")
            refs = []
            topics = []
            for root in roots:
                root_metadata = get_metadata(repo, root)
                v1 = root_metadata.get("email-references")
                if v1:
                    for r in [x.strip() for x in re.split(r',?\s+', v1)]:
                        if not r in refs: refs.append(r)
                v2 = root_metadata.get("email-in-reply-to")
                if v2:
                    for r in [x.strip() for x in re.split(r',?\s+', v2)]:
                        if not r in refs: refs.append(r)
                if not (v1 or v2):
                    v3 = root_metadata.get("email-thread-topic")
                    if v3 and v3 not in topics:
                        topics.append(v3)
            if not refs:
                break
            query=""
            for ref in refs:
                if query: query += " OR "
                query += "email-guid:" + ref.strip()
            newroots = [doc.id for score, doc in repo.do_query(query)]
            note(4, "%d hits for search on email-guids...", len(newroots))
            for r in newroots:
                note(4, "    %s", r)
            if topics:
                query = string.join([('email-subject:"' + quote_query(x.strip()) + '"') for x in topics], " OR ")
                topicroots = [doc.id for score, doc in repo.do_query(query)]
                note(4, "%d hits for search on email-guids...", len(topicroots))
                for r in topicroots:
                    note(4, "    %s", r)
                    if r not in newroots:
                        newroots.append(r)
            if not newroots:
                # roots may not be in repository
                break
            newroots.sort()
            if newroots == roots:
                break
            roots = newroots

        note(3, "final roots are %s\n" % [id for id in roots])

        # now work down
        return [build_subtree(id, get_metadata(repo, id)) for id in roots]                
    build_thread_tree=staticmethod(build_thread_tree)

    def lookup_thread (docid):
        THREADS_LOCK.acquire()
        v = THREADS.get(docid)
        THREADS_LOCK.release()
        return v
    lookup_thread = staticmethod(lookup_thread)
        
    def find_thread (repo, doc_id, doc_metadata):
        v = Thread.lookup_thread(doc_id)
        if isinstance(v, Thread) and (doc_id not in v):
            note(3, "Thread %s doesn't contain doc_id %s", v, doc_id)
        if isinstance(v, Thread) and (doc_id in v):
            return v
        else:

            def walk_doc_ids_for_thread(t):
                id, replies, attachments = t
                if THREADS.has_key(id):
                    return THREADS.get(id)
                for reply in replies:
                    v = walk_doc_ids_for_thread(reply)
                    if isinstance(v, Thread):
                        return v
                for att in attachments:
                    if THREADS.has_key(att):
                        return THREADS.get(att)
                return None

            v = None
            tree = Thread.build_thread_tree(repo, doc_id, doc_metadata)

            THREADS_LOCK.acquire()
            try:
                # first we see if an existing thread should contain the doc
                for root in tree:
                    v = walk_doc_ids_for_thread(root)
                    if isinstance(v, Thread):
                        v.set_tree(tree)
                        break

                # if not...
                if not isinstance(v, Thread):
                    note(3, "*****  creating new thread for %s  *********", doc_id)
                    v = Thread(repo, None, tree)
                    # repo.add_collection(None, v)

                THREADS[doc_id] = v
            finally:
                THREADS_LOCK.release()
            return v
    find_thread = staticmethod(find_thread)

    def walk_thread_from_ids (roots, repo):

        def by_time (reply1, reply2):
            try:
                return cmp(float(reply1[0].get_metadata("email-time")), float(reply2[0].get_metadata("email-time")))
            except:
                note("%s\n%s: %s\n%s: %s", string.join(traceback.format_exception(*sys.exc_info())),
                     reply1, reply1[0].get_metadata("email-time"), reply2, reply2[0].get_metadata("email-time"))
            return 0

        def walk_root (t, repo):

            docid, replies, attachments = t
            if not repo.valid_doc_id(docid):
                return None
            else:
                replies = Thread.walk_thread_from_ids(replies, repo)
                attachments = [repo.get_document(did) for did in attachments if repo.valid_doc_id(did)]
                return (repo.get_document(docid), replies, attachments)

        newroots = []
        for root in roots:
            if not repo.valid_doc_id(root[0]):
                note(2, "Invalid email root doc-id %s passed\n", root[0])
                continue
            v = walk_root(root, repo)
            if v is not None:
                doc = v[0]
                if doc.get_metadata("apparent-mime-type") != "message/rfc822":
                    note(2, "Attempt to use non-email document %s as root of email thread\n", doc)
                else:
                    newroots.append(v)
        newroots.sort(by_time)
        return newroots        
    walk_thread_from_ids = staticmethod(walk_thread_from_ids)

    def figure_time_string (doc, referent):

        try:
            s = doc.get_metadata("email-time")
            if not s:
                return doc.get_metadata("date")
            t1 = float(s)
            return figure_date_string(time.localtime(t1), time.localtime(), (referent and float(referent.get_metadata("email-time"))) or None, time.time() - t1)
        except:
            note("oc is %s, referent is %s", doc, referent)
            typ, ex, tb = sys.exc_info()
            raise ex, None, tb

    def figure_dates(self, now=None):

        if now is None:
            now = time.time()
        ptnow = time.localtime(now)
        pt1 = time.localtime(self.first_message_time)
        pt2 = time.localtime(self.latest_message_time)
        return figure_date_string(pt1, ptnow, None, now - self.first_message_time), figure_date_string(pt2, ptnow, pt1, (now - self.latest_message_time))

    def output_thread_block(fp, level, base, referent, with_icon=true, with_attachment_icon=true, sensible_browser=true):

        def figure_time_string (doc, referent):

            try:
                s = doc.get_metadata("email-time")
                if not s:
                    return doc.get_metadata("date")
                if referent:
                    t2 = referent.get_metadata("email-time")
                    pt2 = (t2 and time.localtime(float(t2))) or None
                else:
                    pt2 = None
                t1 = float(s)
                pt1 = time.localtime(t1)
                now = time.time()
                ptnow = time.localtime(now)
                return figure_date_string(pt1, ptnow, pt2, now - t1)
            except:
                note("figure_time_string:  oc is %s, referent is %s", doc, referent)
                typ, ex, tb = sys.exc_info()
                raise ex, None, tb

        doc, replies, attachments = base
        fp.write('<table><tr>')
        if referent:
            fp.write('<td bgcolor="white">&nbsp;</td>')
        doctitle = doc.get_metadata("email-subject")
        if with_icon:
            fp.write('<td rowspan=3 valign=top>')
            iwidth, iheight = [int(x) for x in doc.get_metadata("icon-size").split(",")]
            output_document_icon(doc.id, htmlescape(doctitle, True), fp, sensible_browser, width=iwidth, height=iheight)
            fp.write('</td>')

        fp.write("<td><b>%s</b> &middot; " % htmlescape(doc.get_metadata("authors")))
        # __output_document_title(doc.id, doc.get_metadata("email-subject"), fp, sensible_browser)
        output_document_title(doc.id, figure_time_string(doc, referent), fp, sensible_browser)
        recipients = doc.get_metadata("email-recipients")
        if recipients:
            recipients = recipients.strip(" /").replace(" / ", ", ")
            fp.write('<font size="-1" color="%s"> to </font><font size="-1" color="%s">%s</font>' % (
                STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, htmlescape(recipients)))
        fp.write('\n<br><font size="-1">%s</font>\n' % htmlescape(doc.get_metadata("email-summary") or doc.get_metadata("summary") or "(no summary)"))
        if attachments:
            fp.write('<br><hr><font color="%s"><i>Attachments:</i></font><br><table>\n' % STANDARD_LEGEND_COLOR)
            for attachment in attachments:
                doctitle = attachment.get_metadata("title")
                if attachment.get_metadata("title-is-original-filepath") == "true":
                    doctitle = None
                fp.write('<tr><td>')
                if with_attachment_icon:
                    output_document_icon(attachment.id, doctitle and htmlescape(doctitle, True), fp, sensible_browser)
                    fp.write('</td><td>\n')
                pagecount = int(attachment.get_metadata("page-count"))
                if doctitle:
                    fp.write("<b>%s</b></br>" % htmlescape(doctitle))
                authors = attachment.get_metadata("authors")
                if authors:
                    fp.write("%s</br>" % htmlescape(authors))
                date = attachment.get_metadata("date")
                if date:
                    fp.write("%s, " % date)
                fp.write("%s page%s" % (pagecount, (pagecount != 1) and "s" or ""))
                summary = attachment.get_metadata("abstract") or attachment.get_metadata("comment") or attachment.get_metadata("summary")
                if summary:
                    fp.write("<br><small>%s</small>" % htmlescape(summary))
                fp.write("</td></tr>\n")
            fp.write("</table>\n")

        if replies:
            fp.write('<br><hr><font color="%s"><i>Replies:</i></font><br>' % STANDARD_LEGEND_COLOR)
            for reply in replies:
                Thread.output_thread_block(fp, level, reply, doc, with_icon, with_attachment_icon, sensible_browser)

        fp.write("</tr></table>\n")
    output_thread_block=staticmethod(output_thread_block)

    def collapse_thread (x):
        if x:
            return (x[0].id, [Thread.collapse_thread(y) for y in x[1]], [z.id for z in x[2]])
        else:
            return []
    collapse_thread = staticmethod(collapse_thread)

    def store(self, directory):
        fp = open(os.path.join(directory, self.id), "w")
        pickle.dump([Thread.collapse_thread(x) for x in self.forest], fp)
        fp.close()

    def load(self, fp):
        self.threadtree = pickle.load(fp)
        self.forest = []

    def walk_thread_into_dict (self, t, d=None):

        def by_time (ref1, ref2):
            return cmp(ref1, ref2)

        if d is None: d = dict()
        if not t: return d
        doc, replies, attachments = t
        d[doc.id] = doc
        dtime = float(doc.get_metadata("email-time"))
        if dtime > self.latest_message_time:
            self.latest_message_time = dtime
        for a in attachments:
            d[a.id] = a
        for reply in replies:
            self.walk_thread_into_dict(reply, d)
        return d

    def set_forest(self, t):
        # initializing the forest of the Collection
        if t:
            # bare ids
            self.forest = Thread.walk_thread_from_ids(t, self.repository)
            if self.forest:
                t = self.forest[0][0].get_metadata("email-time")
                if t:
                    self.first_message_time = float(self.forest[0][0].get_metadata("email-time"))                    
                    self.latest_message_time = self.first_message_time
            for subthread in self.forest:
                self.walk_thread_into_dict(subthread, self)
            THREADS_LOCK.acquire()
            for item in self.values():
                THREADS[item.id] = self
            THREADS_LOCK.release()

    def roots(self):
        return [x[0] for x in self.get_forest()]

    def rescan(self):
        def figure_roots (forest):
            newroots = []
            for doc, replies, attachments in forest:
                if self.repository.valid_doc_id(doc.id):
                    newroots += Thread.build_thread_tree(self.repository, doc.id, doc.get_metadata())
                else:
                    del self[doc.id]
                    newroots += figure_roots(replies)
            return newroots
        if not self.__scanning:
            self.__scanning = True
            if self.threadtree and not self.forest:
                self.set_forest(self.threadtree)
                self.threadtree = None
            if self.repository.doc_mod_time() > self.scantime:
                newroots = figure_roots(self.forest)
                self.set_forest(newroots)
                self.scantime = time.time()
            self.__scanning = False

    def set_tree(self, tree):
        self.forest = []
        self.threadtree = tree

    def get_forest(self):
        self.rescan()
        return self.forest


def show_thread (repo, response, params):

    doc_id = params.get("doc_id")
    show_icons = params.get("show_icons")

    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Bad doc_id %s specified." % doc_id)
        return
    doc = repo.get_document(doc_id)

    if not (doc.get_metadata("email-guid") or doc.get_metadata("email-attachment-to")):
        response.error(HTTPCodes.BAD_REQUEST, "Specified document %s is not an email message or attachment." % doc_id)
        return

    # doc might be message or attachment; try attachment first

    another_doc_id = doc.get_metadata("email-attachment-to")
    if another_doc_id and repo.valid_doc_id(another_doc_id):
        doc = repo.get_document(another_doc_id)

    sensible_browser = _is_sensible_browser(response.user_agent)

    thread = Thread.find_thread(repo, doc.id, doc.get_metadata())

    note ("show_thread (%s):  thread is %s (%s)", doc.id, thread, thread.threadtree)

    if thread is None:
        response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "No thread found for %s.\n" % doc)
        return

    else:
        tree = thread.get_forest()
        note(3, "thread is %s, forest is %s", thread, tree)

    fp = response.open("text/html")
    title = tree[0][0].get_metadata("email-subject")
    fp.write("<head><title>\"%s\" email thread</title>\n" % htmlescape(title))
    refresh_period = int(repo.get_param('overview-refresh-period', 0))
    if refresh_period:
        fp.write('<meta http-equiv="Refresh" content="%d">\n' % refresh_period)
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    fp.write('</head>\n')
    fp.write('<body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp);
    fp.write("\"<b>%s</b>\" email thread\n<hr>" % htmlescape(title))
    fp.write('<form action="%s" method="POST" enctype="application/x-www-form-urlencoded">\n' % response.request_path +
             '<input type=hidden name=doc_id value="%s">\n' % doc.id)
    if not show_icons:
        fp.write('<input type=hidden name=show_icons value=true>\n')
    fp.write('<input type=submit value="%s">' % ((show_icons and "Without document icons") or "With document icons") +
             '</form>\n')    
    for root in tree:
        Thread.output_thread_block(fp, 0, root, None, with_icon=show_icons, sensible_browser=sensible_browser)
    fp.write("</body></html>")
    fp.close()

    
#         fp.write('<p><font color="%s">%s\n' % (STANDARD_DARK_COLOR, htmlescape(repr(thread))))
#         fp.write('<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;first message time is %s, latest message time is %s\n'
#                  % (htmlescape(time.ctime(thread.first_message_time)), htmlescape(time.ctime(thread.latest_message_time))))
#         for doc in thread.docs():
#             if doc.get_metadata("apparent-mime-type") == "message/rfc822":
#                 ctime = time.ctime(float(doc.get_metadata("email-time")))
#                 fp.write('<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s  (%s)' % (htmlescape(repr(doc)), htmlescape(ctime)))
#         fp.write('</font>\n')

SHOW_BLOCK = """
<script type="text/javascript" language="javascript" src="/html/javascripts/prototype.js">
</script>
<script type="text/javascript" language="javascript">

    function quote_quotes(s) {
        s = s.replace('"', '\\"');
        s = s.replace("'", "\\'");
        return s;
    }

    function display_block (threadid, open, blockhtml) {
        var d = $(threadid);
        // open/closed indicator ** size ** date ** from ** title
        v = "<table border=0 width=\\"100%\\"><tr width=\\"100%\\">";
        v += "<td width=\\"2%\\"><small><span class=threadlink title=\\"" + (open ? "close" : "open") + "\\" onclick=\\"javascript:thread_click('" + threadid + "', " + (!open) + ")\\">" + (open ? "*" : " ") + "</span></small></td>";
        v += "<td width=\\"5%\\"><small>" + d.getAttribute("msg_count") + "</small></td>";
        v += "<td width=\\"20%\\"><small>" + d.getAttribute("first_date") + "</small></td>";
        v += "<td width=\\"20%\\"><small>" + d.getAttribute("initiator").escapeHTML() + "</small></td>";
        v += '<td width="50%"><span class=threadlink title="' + (open ? "close" : quote_quotes(d.getAttribute("summary").escapeHTML())) + '" onclick="javascript:thread_click(\\'' + threadid + "', " + (!open) + ')"><b>' + d.getAttribute("threadtitle").escapeHTML() + "</b></span></td>";
        v += "</tr>";
        if (open && (blockhtml != null)) {
            v += '<tr width="100%"><td width="2%"> </td><td colspan=4>' + blockhtml + "</td></tr>";
            if (d.getAttribute("content").length == 0) {
                d.setAttribute("content", blockhtml);
            }
        }
        v += "</table>"
        $(threadid).innerHTML = v;
    }

    function thread_click (threadid, open) {
        if (open) {
            var content = $(threadid).getAttribute("content");
            if ((content != null) && (content.length > 0)) {
                display_block(threadid, true, content);
            } else {
                var docid = $(threadid).getAttribute("doc_id");
                var url = "/action/basic/email_thread_content?inner=t&doc_id=" + docid;
                var myAjax = new Ajax.Request(url,
                                              { method: 'get',
                                                onComplete: function (req)
                                                {
                                                    display_block(threadid, true, req.responseText);
                                                },
                                                onFailure: function (req)
                                                {
                                                    alert("Failure to load thread contents:  " + req);
                                                }
                                              });
            }
        } else {
            display_block (threadid, false, null);
        }
        return true;
    }

    function show_all_threads () {
        var elts = document.all || document.getElementsByTagName("div");
        for (var i = 0;  i < elts.length;  i++) {
            if (elts[i].className == "thread") {
                display_block(elts[i].id, false, null);
            }
        }
    }
</script>
<style>
span.threadlink:hover {
    text-decoration: underline;
    }
</style>
"""

def output_thread (thread, fp, forest=None, now=None, json=False):
    f = forest or thread.get_forest()
    if now is None:
        now = time.time()
    lead_doc = f[0][0]
    title = lead_doc.get_metadata("email-subject") or lead_doc.get_metadata("email-summary") or thread.id
    count = len([x for x in thread.docs() if (x.get_metadata("apparent-mime-type") == "message/rfc822")])
    first_date, last_date = thread.figure_dates(now=now)
    if len(thread) > 1:
        dates = "%s to %s" % (first_date, last_date)
    else:
        dates = first_date
    note("thread %s: title is %s, count is %s, dates are %s", thread, title, count, dates)
    if json:
        fp.write(str({ "threadid": thread.id, "docid": lead_doc.id, "count" : count,
                 "firstdate": first_date, "lastdate": last_date, "title": title, }) + "\n")
    else:
        fp.write("<b><a href=\"javascript:void(0)\" onclick=\"javascript:thread_click('%s', '%s', '%s', '%s', '%s', %d, true);\">"
                 % (thread.id, lead_doc.id, urllib.quote(title), urllib.quote(first_date), urllib.quote(last_date), count));
        fp.write('%s</a></b> &middot; <font color="%s">' % (htmlescape(title), STANDARD_DARK_COLOR))
        if count == 1:
            fp.write('%s</font>\n' % htmlescape(first_date))
        else:
            fp.write('%d messages, %s to %s</font>\n' % (count, first_date, last_date))

def figure_thread_elements(thread, forest=None, now=None):
    f = forest or thread.get_forest()
    if now is None:
        now = time.time()
    lead_doc = f[0][0]
    title = lead_doc.get_metadata("email-subject") or lead_doc.get_metadata("email-summary") or thread.id
    count = len([x for x in thread.docs() if (x.get_metadata("apparent-mime-type") == "message/rfc822")])
    first_date, last_date = thread.figure_dates(now=now)
    author = lead_doc.get_metadata("authors") or lead_doc.get_metadata("email-from-address")
    summary = lead_doc.get_metadata("email-summary") or lead_doc.get_metadata("summary") or title
    note(4, "thread %s: title is %s, count is %s, dates are %s, %s, author is %s", thread, repr(title), count, repr(first_date), repr(last_date), repr(author))
    return lead_doc.id, title, count, first_date, last_date, author, summary

def get_thread_content(repo, response, params):

    id = params.get("doc_id")
    if not id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.")
        return

    t = Thread.lookup_thread(id)
    if not t:
        response.error(HTTPCodes.BAD_REQUEST, "No thread for doc_id %s." % id)
        return

    full = params.get("long") is not None
    inner = params.get("inner") is not None
    json = params.get("json") is not None

    fp = response.open()
    f = t.get_forest()
    if json:
        fp.write("[\n")
    if full:
        output_thread(t, fp, f, json=json)
    if full or inner:
        if json:
            outputstream = StringIO()
        else:
            outputstream = fp
        for root in f:
            Thread.output_thread_block(outputstream, 0, root, None, with_icon=False, with_attachment_icon=True, sensible_browser=True)
        if json:
            fp.write(outputstream.getvalue())
    if json:
        fp.write("]\n")
    fp.close()

SORTOPTIONS = (
    ("by-latest-inverted", "Latest changed", lambda t1, t2: cmp(t2.latest_message_time, t1.latest_message_time)),
    ("by-start-inverted", "Latest started", lambda t1, t2: cmp(t2.first_message_time, t1.first_message_time)),
    ("by-latest", "Earliest changed", lambda t1, t2: cmp(t1.latest_message_time, t2.latest_message_time)),
    ("by-start", "Earliest first", lambda t1, t2: cmp(t1.first_message_time, t2.first_message_time)),
    )

def show_threads (repo, response, params):

    def by_start_inverted(t1, t2):
        return cmp(t2.first_message_time, t1.first_message_time)

    def by_latest_inverted(t1, t2):
        return cmp(t2.latest_message_time, t1.latest_message_time)

    docs = None
    coll = None
    category = params.get("category")
    collid = params.get("coll")
    if collid:
        coll = repo.get_collection(collid, True)
        if (coll is None):
            coll = TEMPORARY_COLLECTIONS.get(collid)
    if coll is None:
        existing_query = params.get("query")
        if existing_query:
            coll = QueryCollection(repo, None, existing_query)
            TEMPORARY_COLLECTIONS[coll.id] = coll
    if isinstance(coll, Collection):
        docs = coll.docs()
    else:
        if category:
            coll = QueryCollection(repo, None, '+categories:"' + category.strip() + '"')
            docs = coll.docs()
        if not docs:
            doc_id = params.get("doc_id")
            if doc_id:
                if type(doc_id) in types.StringTypes:
                    doc_id = (doc_id,)
                docs = [repo.get_document(id) for id in doc_id if repo.valid_doc_id(id)]
                coll = Collection(repo, None, docs)
                TEMPORARY_COLLECTIONS[coll.id] = coll
            else:
                docs = []

    sort_order = params.get("sort-order") or "by-latest-inverted"

    threads = []
    for doc in docs:
        v = Thread.find_thread(repo, doc.id, doc.get_metadata())
        if (v not in threads):
            v.rescan()
            if v:
                threads.append(v)
            else:
                note("empty thread for doc %s", doc)

    note(3, "show_threads sort_order is %s", sort_order)
    for sortoption in SORTOPTIONS:
        if (sort_order == sortoption[0]):
            note("sorting by %s", repr(sortoption[1]))
            threads.sort(sortoption[2])
            break

    categories = []
    for thread in threads:
        forest = thread.get_forest()
        if forest and forest[0]:
            for c in forest[0][0].get_category_strings():
                if c not in categories:
                    categories.append(c)

    fp = response.open("text/html")
    title = "Email Threads"
    fp.write("<head><title>%s</title>\n" % htmlescape(title))
    refresh_period = int(repo.get_param('overview-refresh-period', 0))
    if refresh_period:
        fp.write('<meta http-equiv="Refresh" content="%d">\n' % refresh_period)
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    issue_javascript_head_boilerplate(fp)
    fp.write(SHOW_BLOCK);
    fp.write('</head>\n')
    fp.write('<body bgcolor="%s" onload="javascript:show_all_threads();">\n' % STANDARD_BACKGROUND_COLOR)
    issue_menu_definition(fp);

    fp.write('<h2>%s</h2>' % htmlescape(title))
    fp.write('<table border=0 width="100%%"><tr><td width="70%%">')
    fp.write('<form name=search_form method=post action="/action/basic/email_threads" enctype="multipart/form-data">\n')
    q = isinstance(coll, QueryCollection) and coll.query or ""
    fp.write('<font size=-2 style="color: ' + STANDARD_LEGEND_COLOR + '">Search</font> ' +
             '<input type=text name=query size=50 value="%s"></form></td>\n' % htmlescape(q, true))
    fp.write('<td><form name=sort_order method=get action="/action/basic/email_threads">\n')
    if category:
        fp.write('<input type=hidden name="category" value="%s">\n' % htmlescape(category, True))
    note(3, "show_threads:  coll is %s", coll)
    if isinstance(coll, Collection):
        fp.write('<input type=hidden name="coll" value="%s">\n' % coll.id)
    fp.write('<select name="sort-order" size=1 onchange="{document.sort_order.submit();}">\n')
    for sortoption in SORTOPTIONS:
        fp.write('<option %svalue="%s">%s</option>\n'
                 % (((sort_order == sortoption[0]) and "selected ") or "", sortoption[0], sortoption[1]))
    fp.write('</select></form></td>')
    fp.write('<td><form name=category_select method=get action="/action/basic/email_threads">\n')
    if isinstance(coll, Collection):
        fp.write('<input type=hidden name="coll" value="%s">\n' % coll.id)
    fp.write('<input type=hidden name="sort-order" value="%s">\n' % htmlescape(sort_order, True))
    fp.write('<select name="category" size=1 onchange="{document.category_select.submit();}">\n')
    fp.write('<option %svalue="">all categories</option>\n' % (category and " ") or "selected ")
    for c in categories:
        fp.write('<option %svalue="%s">%s</option>\n' % (
            (c == category) and "selected " or "", htmlescape(c, True), htmlescape(c)))
    fp.write('</select></form></td>')
    fp.write('</tr></table>\n')

    now = time.time()
    colors = ("#ffffff", STANDARD_BACKGROUND_COLOR)
    counter = 0
    for thread in threads:
        doc_id, title, count, first_date, last_date, author, summary = figure_thread_elements(thread, now=now)
        note(4, "doc_id is %s, title is %s, count is %s, first_date is %s, last_date %s, author is %s, summary is %s",
             doc_id, title, count, first_date, last_date, author, summary)
        fp.write('<div style="background: %s" id="%s" msg_count="%d" summary="%s" doc_id="%s" threadtitle="%s" first_date="%s" initiator="%s" last_date="%s" content="" class=thread></div>\n'
                 % (colors[counter % 2], thread.id, count, htmlescape(summary, True), doc_id, htmlescape(title, True), htmlescape(first_date, True), htmlescape(author, True), htmlescape(last_date or "", True)))
        counter += 1
    fp.write("</body></html>")
    fp.close()
        
def _all_email_docs(coll, any=False):
    try:
        for doc in coll.docs():
            mimetype = doc.get_metadata("apparent-mime-type")
            attinfo = doc.get_metadata("email-attachment-to")
            if attinfo or ((type(mimetype) in types.StringTypes) and mimetype.startswith("message/")):
                if any:
                    return True
            else:
                if not any:
                    return False
        return (not any)
    except:
        note(3, "_all_email_docs:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
        return False

if __name__ == "__main__":
    import uplib
    from uplib.plibUtil import set_verbosity
    set_verbosity(4)
    uplib.addDocument.update_configuration()
    uplib.addDocument.ensure_assembly_line()
    parser = EMail(sys.argv[1], options={})
    msg, mainpart, attachments, md = parser.parse_mail_message()
    show_message_structure(msg)
    print parser.format_message_as_html(msg, mainpart, attachments, "")
    print md
