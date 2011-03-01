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
# Runs the CiteULike metadata rippers for the specified URL
#

import sys, os, re, string, traceback
from uplib.ripper import Ripper
from uplib.plibUtil import note, read_metadata, update_metadata, parse_date, subproc, configurator
from uplib.webutils import HTTPCodes

UPLIB_MIN_VERSION = "1.7"

CITE_U_LIKE_DOCUMENT_TYPES = {
    # maps CiteULike document types to RIS (EndNote) document types
    "BOOK": "BOOK",
    "CHAP": "CHAP",
    "CONF": "CONF",
    "ELEC": "ELEC",
    "GEN": "GEN",
    "INCOL": "CHAP",
    "INCONF": "CONF",
    "INPR": "INPR",
    "JOUR": "JOUR",
    "MANUAL": "BOOK",
    "MTHES": "THES",
    "PAMP": "PAMP",
    "REP": "RPRT",
    "THES": "THES",
    "UNPB": "UNPB",
    }

UPLIB_METADATA_FIELDS = {
    # map RIS field names to UpLib metadata fields
    "TI" : "title",
    "T1" : "title",
    "AU" : "author",
    "A1" : "author",
    "AB" : "abstract",
    "N2" : "abstract",
    "PY" : "date",
    "SP" : "start-page",
    "EP" : "end-page",
    "PB" : "source",
    "SN" : "isbn",
    "JF" : "publication-name",
    "VL" : "publication-volume",
    "IS" : "publication-number",
    "CH" : "chapter",
    }


c = configurator()
TCLSH = c.get('tclsh', '/usr/bin/tclsh')
CITEULIKE_PLUGINS = c.get('citeulike-checkout-directory', '/project/uplib/citeulike')
RIS_PART_START = re.compile(r'(?P<tag>[A-Z0-9]{2})\s+-\s+(?P<value>.*)')
ENDNOTE_CHARREF = re.compile(r'\\&\\#(?P<charcode>[0-9]+);')

def get_metadata_for_url (URL):

    # to do this, we use "tclsh" to run the driver
    cmd = '(cd "%s"; "%s" ./driver.tcl parse \'%s\')' % (os.path.join(CITEULIKE_PLUGINS, "plugins"), TCLSH, URL)
    note(3, "citeulike command is <<%s>>", cmd)
    status, output, tsignal = subproc(cmd)
    if status != 0:
        note(3, "CiteULike can't find or understand metadata for URL %s:\n%s\nStatus is %s.\n", URL, output, status)
        return None
    else:
        values = {}
        # now we have this oddly formatted set of name/value pairs, separated by " -> "
        for line in output.split('\n'):
            if " -> " not in line:
                continue
            name, value = line.split(" -> ")
            values[name.strip()] = value.strip()
        return values

def massage_citeulike_to_ris (DICT):

    # given a dictionary DICT of CiteULike metadata, return an EndNote RIS version

    def parse_authors(authors):
        names = []
        for author in authors.split('}}'):
            if not author.strip():
                continue
            rawname = author.rfind('{')
            if rawname >= 0:
                author = author[:rawname]
            nameparts = author.strip()[1:].split()
            family_name = nameparts[0]
            if nameparts[1] == '{}':
                given_name = string.join(list(nameparts[2]), '. ') + '.'
            else:
                given_name = nameparts[1]
            name = family_name + ', ' + given_name
            names.append(name)
        return names

    def format_date (datedict):
        year = (datedict.has_key('year') and str(datedict.get('year'))) or ''
        month = (datedict.has_key('month') and str(datedict.get('month'))) or ''
        day = (datedict.has_key('day') and str(datedict.get('day'))) or ''
        other = datedict.get('other') or ''
        return '%s/%s/%s/%s' % (year, month, day, other)

    rval = []
    date = {}

    for k in DICT:

        v = DICT[k]

        if k == 'type':
            if v not in CITE_U_LIKE_DOCUMENT_TYPES:
                raise ValueError("Unknown document type %s specified." % v)
            rval.insert(0, "TY  - " + CITE_U_LIKE_DOCUMENT_TYPES.get(v))

        elif k == 'journal':
            rval.append("JF  - " + v)

        elif k == 'title':
            rval.append("TI  - " + v)
        elif k == 'title_secondary':
            rval.append("T2  - " + v)
        elif k == 'title_series':
            rval.append("T3  - " + v)

        elif k == 'abstract':
            rval.append("N2  - " + v)

        elif k == 'date_other':
            date['other'] = v
        elif k == 'day':
            date['day'] = int(v)
        elif k == 'month':
            date['month'] = int(v)
        elif k == 'year':
            date['year'] = int(v)

        elif k == 'chapter':
            rval.append("CH  - " + v)
        elif k == 'volume':
            rval.append("VL  - " + v)
        elif k == 'issue':              # number in BibTex
            rval.append("IS  - " + v)
        elif k == 'edition':
            rval.append("IS  - " + v)

        elif k == 'start_page':
            rval.append("SP  - " + v)
        elif k == 'end_page':
            rval.append("EP  - " + v)

        elif k == 'institution':
            rval.append("PB  - " + v)
        elif k == 'organization':
            rval.append("PB  - " + v)
        elif k == 'publisher':
            rval.append("PB  - " + v)
        elif k == 'school':
            rval.append("PB  - " + v)

        elif k == 'isbn':
            rval.append("SN  - " + v)

        elif k == 'issn':
            rval.append("SN  - " + v)

        elif k == 'authors':
            for x in parse_authors(v):
                rval.append("AU  - " + x)

    # now handle dates

    if date and (date.has_key('other') or (date.has_key('year') and date.get('year') > 0)):
        rval.append("PY  - " + format_date(date))

    rval.append("ER  -")
    return string.join(rval, '\n')


def massage_ris_to_uplib (CITE):

    def uplib_convert (name, value):

        if name == "author":
            # convert from RIS "lastname firstname suffixes" to UpLib "firstname lastname suffixes"
            v = value.split(', ')
            firstname = v[1]
            lastname = v[0]
            suffixes = (len(v) > 2) and v[2]
            # see if the first name is actually initials
            if re.match('^[A-Z]+$', firstname):
                # expand it
                firstname = string.join(list(firstname), '. ') + '.'
            x = firstname + ' ' + lastname
            if suffixes:
                x += suffixes
            return x

        elif name in "date":
            v = None
            year, month, day, other = value.split('/')
            if year:
                v = year
            if month:
                if day:
                    v = day + '/' + v
                v = month + '/' + v
            return v
                
        else:
            return value


    def charref_replace(matchobj):
        return unichr(int(matchobj.group('charcode')))


    # first, break the cite into fields
    parts = CITE.split('\n')
    l = []
    previouspart = None
    previousvalue = None
    for part in parts:
        if not part.strip():
            continue
        if part.startswith("ER  -"):
            break
        part = ENDNOTE_CHARREF.sub(charref_replace, part)
        m = RIS_PART_START.match(part)
        if m:
            part_type_code = m.group('tag')
            part_value = m.group('value')
            if part_type_code in UPLIB_METADATA_FIELDS:
                previouspart = UPLIB_METADATA_FIELDS.get(part_type_code)
                previousvalue = part_value
                v = uplib_convert(previouspart, previousvalue)
                if v is not None:
                    l.append((previouspart, v,))
            else:
                previouspart = None
        elif previouspart:
            previousvalue += part_value
            v = uplib_convert(previouspart, previousvalue)
            if v is not None:
                l[-1] = ((previouspart, v,))
        else:
            note("Odd line in RIS field:  %s", part)

    # figure the authors and page-numbers
    authors = ''
    start_page = None
    end_page = None
    d = {}
    for name, value in l:
        if name == 'author':
            if not authors:
                authors = value
            else:
                authors = authors + ' and ' + value
        elif name == 'start-page':
            start_page = value
        elif name == 'end-page':
            end_page = value
        else:
            d[name] = value
    if authors:
        d['authors'] = authors
    if start_page is not None:
        if end_page is not None:
            d['page-numbers'] = start_page + '-' + end_page
        else:
            d['first-page'] = start_page

    return d



def test (repo, response, params):

    url = params.get("url")
    if not url:
        response.error(HTTPCodes.BAD_REQUEST, "No URL specified.")
        return

    v = get_metadata_for_url(url)
    if not v:
        response.reply("No data for URL %s." % url)
        return
    else:
        fd = response.open("text/plain")
        for n in v:
            fd.write("%s: %s\n" % (n, v[n]))
        ris = massage_citeulike_to_ris(v)
        fd.write('\n\nRIS format:\n\n' + ris)
        uplib = massage_ris_to_uplib (ris)
        fd.write('\n\nUpLib format:\n\n')
        for k in uplib:
            fd.write('%s: %s\n' % (k, uplib[k]))
        fd.close()
        return
            
            
            
def update_document_metadata_via_citeulike (location):

    mdpath = os.path.join(location, "metadata.txt")
    md = read_metadata(mdpath)

    if not md.has_key("original-url"):
        return None

    v = get_metadata_for_url(md.get("original-url"))
    if v:
        ris = massage_citeulike_to_ris(v)
        ud = massage_ris_to_uplib (ris)
        ris2 = re.sub("\n", " || ", ris)
        ud['ris-citation'] = ris2

        if not md.has_key('citation'):
            md['citation'] = ris2

        md.update(ud)
        update_metadata(mdpath, md)
        return ud

    else:
        return None


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
                update_document_metadata_via_citeulike(doc.folder())
                doc.recache()
                if len(ids) == 1:
                    response.redirect("/action/basic/doc_meta?doc_id=" + doc.id)
                else:
                    if not fp:
                        fp = response.open()
                    fp.write('<p>Updated metadata for document \"%s\".\n' % doc.get_metadata("title"))
            except:
                msg = string.join(traceback.format_exception(*sys.exc_info()))
                note("Exception running CiteULikeMetadataRipper:\n" + msg)
                if not fp:
                    fp = response.open()
                fp.write("<p><pre>Exception running looking for document metadata using the CiteULike plugins:\n" + msg + "</pre>")
        else:
            if not fp:
                fp = response.open()
            fp.write("** Doc ID \"%s\" is not a valid doc ID.\n" % id)


class CiteULikeMetadataRipper (Ripper):

    def __init__(self, repo):
        Ripper.__init__(self, repo)

    def rip (self, location, doc_id):
        try:
            if update_document_metadata_via_citeulike(location):
                note(3, "Updated metadata using CiteULike plugins")
        except:
            msg = string.join(traceback.format_exception(*sys.exc_info()))
            note("Exception running CiteULikeMetadataRipper:\n" + msg)

def after_repository_instantiation (repo):

    if (os.path.isfile(TCLSH) and os.path.isdir(CITEULIKE_PLUGINS) and
        os.path.isdir(os.path.join(CITEULIKE_PLUGINS, "plugins")) and
        os.path.isfile(os.path.join(CITEULIKE_PLUGINS, "README.txt"))):

        rippers = repo.rippers()
        # add at front so citation is available when indexing is done
        rippers.insert(0, CiteULikeMetadataRipper(repo))

    else:
        note('Not adding CiteULike ripper; either "tclsh" is not present, or the CiteULike plugins are not present.')

if __name__ == "__main__":
    v = update_document_metadata_via_citeulike(sys.argv[1])
    if v:
        for x in v:
            print x + ':', v[x]
