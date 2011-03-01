# -*- Python -*-
#
# Code to support related-document analysis
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

import sys, os, re, string, traceback, time, urllib, tempfile, zipfile
from xml.dom.minidom import getDOMImplementation

from uplib.plibUtil import note
from uplib.webutils import htmlescape, HTTPCodes
from uplib.basicPlugins import show_abstract, show_title, STANDARD_BACKGROUND_COLOR
from uplib.basicPlugins import __issue_javascript_head_boilerplate as issue_javascript_head_boilerplate
from uplib.basicPlugins import __issue_menu_definition as issue_menu_definition
from uplib.basicPlugins import __issue_title_styles as issue_title_styles

def find_related (doc, return_all=False, use_history=True, use_authorship=True):

    docs = {}

    likethis = []
    qstring = ""

    try:
        context = doc.repo.search_context()
        if context:
            text = doc.text()
            if doc.get_metadata("apparent-mime-type") == "message/rfc822":
                subject = doc.get_metadata("subject")
                if subject:
                    text += " " + subject
            qstring, hits = context.like_this(text, ["title", "abstract", "contents"])
            if hits:
                for hit in hits[:min(20,len(hits))]:
                    if hit[0] == doc.id:
                        continue
                    if not doc.repo.valid_doc_id(hit[0]):
                        continue
                    related = doc.repo.get_document(hit[0])
                    docs[related] = hit[1]
                    likethis.append((related, hit[1]))
    except:
        note(3, "find_related: skipping 'like this':\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
    
    authored = []

    try:
        from uplib.collection import QueryCollection
        authors = doc.get_metadata("authors")
        if use_authorship and authors:
            note("authors are %s", repr(authors))
            authors = authors.split(" and ")
            note("split authors are %s", repr(authors))
            qc = QueryCollection(doc.repo, None, string.join([('authors:"%s"' % unicode(author)) for author in authors], " OR "))
            for doc_id, score in qc.scores():
                if doc_id == doc.id:
                    continue
                if not doc.repo.valid_doc_id(doc_id):
                    continue
                related = doc.repo.get_document(doc_id)
                score = score/2
                if related in docs:
                    docs[related] += score
                else:
                    docs[related] = score
                authored.append((related, score))
    except:
        note(3, "find_related: skipping 'co-authored':\n%s", ''.join(traceback.format_exception(*sys.exc_info())))

    recent = []

    if use_history:
        try:
            history = doc.repo.history()
            now = time.time()
            for related in history[:min(len(history),20)]:
                if related == doc:
                    continue
                score = (100 - (now - related.touch_time())/60)/100
                if score < 0.01:
                    continue
                if related in docs:
                    docs[related] += score
                else:
                    docs[related] = score
                recent.append((related, score))
        except:
            note(3, "find_related: skipping 'recently used':\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
        
    others = []

    # check for email attachments
    try:
        attachments = doc.get_metadata("email-attachments")
        if attachments:
            # email message, so show any attachments
            for attachment in attachments.split(","):
                attachment = attachment.strip()
                if doc.repo.valid_doc_id(attachment):
                    related = doc.repo.get_document(attachment)
                    if related in docs:
                        docs[related] += 1.0
                    else:
                        docs[related] = 1.0
                    others.append(("email attachment", related, 1.0))
        coverletter = doc.get_metadata("email-attachment-to")
        if coverletter:
            # attached to some email message, so show that message, if it's here
            hits = doc.repo.do_query("email-guid:" + coverletter.strip())
            if hits:
                related = hits[0][1]
                if related in docs:
                    docs[related] += 1.0
                else:
                    docs[related] = 1.0
                others.append(("cover letter this was attached to", related, 1.0))
        if doc.get_metadata("apparent-mime-type") == "message/rfc822":
            # email, so find other documents in the same thread
            from uplib.emailParser import Thread
            t = Thread.find_thread(doc.repo, doc.id, doc.get_metadata())
            if t:
                for related in t.docs():
                    if related == doc:
                        continue
                    if related in docs:
                        docs[related] += 0.25
                    else:
                        docs[related] = 0.25
                    others.append(("another message in this email thread", related, 0.25))
    except:
        note(3, "find_related: skipping 'email related':\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
    
    docs = docs.items()
    docs.sort(lambda x1, x2: cmp(x2[1], x1[1]))
    if return_all:
        return docs, likethis, authored, recent, others, qstring
    else:
        return docs

def google (repo, response, params):
    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id %s specified." % doc_id)
        return
    context = repo.search_context()
    if not context:
        response.error(HTTPCodes.NOT_IMPLEMENTED, "This repository doesn't support this operation")
        return
    doc = repo.get_document(doc_id)
    text = doc.text()
    if doc.get_metadata("apparent-mime-type") == "message/rfc822":
        subject = doc.get_metadata("subject")
        if subject:
            text += " " + subject
    terms = context.interesting_terms(text)
    terms = terms[:min(10, len(terms))]
    q = "http://www.google.com/search?q=%s" % urllib.quote_plus(string.join(terms, " OR "))
    note("query URL is %s", q)
    response.redirect(q)

def _safe_title(doc, default=None):
    t = doc.get_metadata("title")
    if not t:
        if default is None:
            t = doc.id
        else:
            t = default
    if not isinstance(t, unicode):
        t = unicode(t, "ISO-8859-1", "strict")
    t = t.replace("\r", " ")
    return t

def related (repo, response, params):
    """
    Find other documents related to the query document.

    :param doc_id: the query document
    :type doc_id: UpLib doc ID string
    :param use-authorship: whether or not to use co-authorship as a measure of relatedness.  Defaults to "true".
    :type use-authorship: "true" or "false"
    :param use-history: whether or not to to use the use history (most recently used list) as a factor in the calculation.  Defaults to "true".
    :type use-history: "true" or "false"
    :param format: whether to return non-browser format results.  Specifying "xml" will cause an XML document to be returned containing the results.  Specifying "ziplist" will cause a zip file containing extra information about each document to be returned.  If the ``format`` parameter is not specified, an HTML page showing the results broken down by category is returned.
    :type format: "xml" or "ziplist" or none
    :result: list of other documents related to the query document.  See discussion of the ``format`` parameter.
    :rtype: varies
    """

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id %s specified." % doc_id)
        return
    doc = repo.get_document(doc_id)

    use_authorship = (params.get("use-authorship") or "true") == "true"
    use_history = (params.get("use-history") or "true") == "true"    

    docs, likethis, authored, recent, others, qstring = find_related(doc, True, use_history=use_history, use_authorship=use_authorship)

    if response.xml_request or (params.get("format") == "xml"):

        retval = getDOMImplementation().createDocument(None, "result", None)
        e = retval.createElement('paradigm')
        e.setAttribute('id', doc_id)
        e.setAttribute("title", _safe_title(doc))
        e.setAttribute('use-history', use_history and "true" or "false")
        e.setAttribute('use-authorship', use_authorship and "true" or "false")
        retval.documentElement.appendChild(e)
        g = retval.createElement('similar')
        g.setAttribute('query', qstring)
        for doc, score in likethis:
            e = retval.createElement('document')
            e.setAttribute('doc_id', doc.id)
            e.setAttribute('score', str(score))
            title = _safe_title(doc)
            note("title is %s", repr(title))
            e.setAttribute('title', title)
            g.appendChild(e)
        retval.documentElement.appendChild(g)
        g = retval.createElement('co-authored')
        for doc, score in authored:
            e = retval.createElement('document')
            e.setAttribute('doc_id', doc.id)
            e.setAttribute('score', str(score))
            title = _safe_title(doc)
            note("title is %s", repr(title))
            e.setAttribute('title', title)
            g.appendChild(e)
        retval.documentElement.appendChild(g)
        g = retval.createElement('recent')
        for doc, score in recent:
            e = retval.createElement('document')
            e.setAttribute('doc_id', doc.id)
            e.setAttribute('score', str(score))
            title = _safe_title(doc)
            note("title is %s", repr(title))
            e.setAttribute('title', title)
            g.appendChild(e)
        retval.documentElement.appendChild(g)
        g = retval.createElement('linked')
        for doc, score in others:
            e = retval.createElement('document')
            e.setAttribute('doc_id', doc.id)
            e.setAttribute('score', str(score))
            title = _safe_title(doc)
            note("title is %s", repr(title))
            e.setAttribute('title', title)
            g.appendChild(e)
        retval.documentElement.appendChild(g)
        g = retval.createElement('combined')
        for doc, score in docs:
            e = retval.createElement('document')
            e.setAttribute('doc_id', doc.id)
            e.setAttribute('score', str(score))
            title = _safe_title(doc)
            note("title is %s", repr(title))
            e.setAttribute('title', title)
            g.appendChild(e)
        retval.documentElement.appendChild(g)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()

    elif params.get("format") == "ziplist":
        no_icon = (params.get("no-icon") == "true")
        include_doc_functions = params.get("include-doc-functions")
        tpath = tempfile.mktemp()
        zf = zipfile.ZipFile(tpath, "w")
        try:
            try:
                for doc, score in docs:
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/", "")
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/score", str(score))
                    if not no_icon:
                        zf.writestr(doc.id.encode("ASCII", "strict") + "/first.png", doc.document_icon())
                    if include_doc_functions:
                        zf.writestr(doc.id.encode("ASCII", "strict") + "/doc_functions.txt", get_doc_functions(doc))
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/metadata.txt", doc.metadata_text())
            finally:
                zf.close()
            response.return_file("application/x-uplib-searchresults-zipped", tpath, True)
        except:
            msg = string.join(traceback.format_exception(*sys.exc_info()))
            os.remove(tpath)
            note("Exception building zipfile for search results:\n%s", msg)
            response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Can't build zipfile for search results:\n%s\n" % htmlescape(msg))
    else:

        fp = response.open()

        title = "Documents related to %s" % repr(doc.get_metadata("title") or doc.id)

        fp.write("<head><title>%s</title>\n" % htmlescape(title))
        fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
        fp.write('<link REL="SHORTCUT ICON" HREF="/favicon.ico">\n')
        fp.write('<link REL="ICON" type="image/ico" HREF="/favicon.ico">\n')
        issue_javascript_head_boilerplate(fp)
        issue_title_styles(fp)
        fp.write('</head><body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
        issue_menu_definition(fp)
        fp.write('<h2>%s</h2><br>\n' % htmlescape(title))

        show_abstract(repo, doc, fp, True, showpagesearch=False)

        fp.write('<p><hr><b>Context documents:</b><br>')
        for related, score in docs:
            show_title (fp, related, {related.id: score}, True)

        fp.write('<p><hr><b>Like this:</b><br>')
        for related, score in likethis:
            show_title (fp, related, { related.id: score }, True)
        fp.write('<p><i>query was:  %s</i>\n' % htmlescape(qstring))

        fp.write('<p><hr><b>Co-authored:</b><br>')
        for related, score in authored:
            show_title (fp, related, { related.id: score }, True)

        fp.write('<p><hr><b>Recently consulted:</b><br>')
        for related, score in recent:
            show_title (fp, related, { related.id: score }, True)

        fp.write('<p><hr><b>Other considerations:</b><br>')
        for explanation, related, score in others:
            fp.write('<p><i>%s</i><br>\n' % htmlescape(explanation))
            show_title (fp, related, { related.id: score }, True)

        fp.write('</body>\n')
        fp.close()

related_actions = {

    "show_related" : related,
    "google_for_related" : google,
    }

