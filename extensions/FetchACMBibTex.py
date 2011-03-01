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

import sys, os, re, string, StringIO, tempfile, traceback
import urlparse, urllib, urllib2
from uplib.ripper import Ripper
from uplib.plibUtil import note, read_metadata, update_metadata, parse_date

UPLIB_MIN_VERSION = "1.7"

BIBTEX_RE = re.compile(r"('popBibTex.cfm\?(?P<params>[^']+)')")
ENDNOTE_RE = re.compile(r"('popendnotes.cfm\?(?P<params>[^']+)')")
ENDNOTE_CHARREF = re.compile(r'\\&\\#(?P<charcode>[0-9]+);')
# as of March 2008, using this instead of the above RE
ENDNOTE2_RE = re.compile(r"('testpopendnotes.cfm\?(?P<params>[^']+)')")
ABSTRACT_RE = re.compile(r'<A NAME="abstract">.*?<p class="abstract">\s*(?P<abstract>.*?)</p>', re.MULTILINE | re.IGNORECASE | re.DOTALL)

def fetch_bibtex_and_endnote_from_acm_diglib(url):

    bibtex = None
    endnote = None
    abstract = None

    try:

        scheme, location, path, querys, fragment = urlparse.urlsplit(url)
        query = dict([urllib.unquote_plus(x).split('=') for x in querys.split('&')])

        if location == 'portal.acm.org' and query.has_key('id'):
            # fetch the citation page and find the BibTex link
            newurl = "http://%s/citation.cfm?jmp=cit&id=%s" % (location, query.get('id'))
            data = urllib2.urlopen(newurl).read()
            m = BIBTEX_RE.search(data)
            if m:
                # now fetch the bibtex page and pull the actual BibTex out of it
                bibtexpage = urllib2.urlopen('http://%s/popBibTex.cfm?%s' % (location, m.group('params'))).read()
                m = re.search(r'<PRE id="%s">\s*(?P<bibtex>[^<]*)</pre>' % query.get('id'), bibtexpage)
                if m:
                    bibtex = m.group('bibtex').strip()
            m = ENDNOTE_RE.search(data)
            if not m: m = ENDNOTE2_RE.search(data)
            if m:
                # now fetch the endnote page and pull the actual EndNote out of it
                # (we don't need fetch_url here because endnote info is open to all)
                endnotepage = urllib2.urlopen('http://%s/popendnotes.cfm?%s' % (location, m.group('params'))).read()
                m = re.search(r'<PRE id="%s">\s*(?P<endnote>[^<]*)</pre>' % query.get('id'), endnotepage)
                if m:
                    endnote = m.group('endnote').strip()
            # now try for the abstract
            try:
                m = ABSTRACT_RE.search(data)
                if m:
                    abstract = m.group("abstract")
                else:
                    note("no match for abstract")
            except:
                msg = string.join(traceback.format_exception(*sys.exc_info()))
                note("Couldn't get abstract for %s:\n%s", url, msg)
    except:
        msg = string.join(traceback.format_exception(*sys.exc_info()))
        note("Exception fetching ACM citation info for %s:\n%s", url, msg)

    return bibtex, endnote, abstract

def update_document_metadata_from_acm_diglib (location):

    def charref_replace(matchobj):
        return unichr(int(matchobj.group('charcode')))

    def parse_endnote(newdict, md, endnote):
        parts = endnote.strip().split("\n")
        authors = ""
        for part in parts:
            p = ENDNOTE_CHARREF.sub(charref_replace, part.strip())
            if p.startswith("%T "):
                newdict['title'] = p[3:].strip()
                newdict['title-is-original-filepath'] = ''
            elif p.startswith("%P "):
                newdict['page-numbers'] = p[3:].strip()
            elif p.startswith("%D "):
                # we override any existing date, because often the PDF file had
                # a bad date in it -- the date it was scanned to add to the library
                year, month, day = parse_date(p[3:].strip())
                newdict['date'] = "%s/%s/%s" % (month, day, year)
            elif p.startswith("%A "):
                # ignore any author metadata in the PDF file
                if authors:
                    authors += " and "
                authors += p[3:].strip()
        if authors:
            d['authors'] = authors

    mdpath = os.path.join(location, "metadata.txt")
    md = read_metadata(mdpath)
    if md.has_key("original-url") and "portal.acm.org" in md.get("original-url"):
        bibtex, endnote, abstract = fetch_bibtex_and_endnote_from_acm_diglib(md.get("original-url"))
        if bibtex or endnote:
            d = {}
            if bibtex:
                d['bibtex-citation'] = re.sub("\n", " ", bibtex)
            if endnote:
                parse_endnote(d, md, endnote)
                d['endnote-citation'] = re.sub("\n", " / ", endnote)
            if bibtex and not md.has_key("citation"):
                d["citation"] = re.sub("\n", " ", bibtex)
            if abstract and not md.has_key("abstract"):
                d["abstract"] = re.sub("\n|<par>|</par>", " ", abstract)
            update_metadata(mdpath, d)
        else:
            note("Couldn't fetch citation info for URL \"%s\".", md.get("original-url"))

def rerip (repo, response, params):

    ids = params.get('doc_id')
    if not ids:
        response.error(HTTPCodes.BAD_REQUEST, "No document(s) specified.")
        return

    if ids and type(ids) == type(''):
        ids = ( ids, )

    fp = None

    for id in ids:
        if repo.valid_doc_id(id):
            doc = repo.get_document(id)
            try:
                update_document_metadata_from_acm_diglib(doc.folder())
                doc.recache()
                if len(ids) == 1:
                    response.redirect("/action/basic/doc_meta?doc_id=" + doc.id)
                else:
                    if not fp:
                        fp = response.open()
                    fp.write('<p>Updated metadata for document \"%s\".\n' % doc.get_metadata("title"))
            except:
                msg = string.join(traceback.format_exception(*sys.exc_info()))
                note("Exception running ACMBibTexRipper:\n" + msg)
                if not fp:
                    fp = response.open()
                fp.write("<p><pre>Exception running looking for document metadata in the ACM Digital Library:\n" + msg + "</pre>")
        else:
            if not fp:
                fp = response.open()
            fp.write("** Doc ID \"%s\" is not a valid doc ID.\n" % id)


class ACMBibTexRipper (Ripper):

    def __init__(self, repo):
        Ripper.__init__(self, repo)

    def rip (self, location, doc_id):
        try:
            update_document_metadata_from_acm_diglib(location)
        except:
            msg = string.join(traceback.format_exception(*sys.exc_info()))
            note("Exception running ACMBibTexRipper:\n" + msg)

def after_repository_instantiation (repo):
    rippers = repo.rippers()
    # add at front so citation is available when indexing is done
    rippers.insert(0, ACMBibTexRipper(repo))

if __name__ == "__main__":
    print ACMBibTexRipper(None).fetch_bibtex_and_endnote_from_acm_diglib(sys.argv[1])
