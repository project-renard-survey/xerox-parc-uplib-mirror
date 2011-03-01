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
# The Washington Post embeds metadata about the article.  Use that metadata!
#

import sys, os, re, xml, HTMLParser, htmlentitydefs, urlparse

from uplib.ripper import Ripper
from uplib.plibUtil import note, configurator, read_metadata, update_metadata, set_verbosity
from uplib.webutils import parse_URL
from uplib.addDocument import URLDoc

UPLIB_MIN_VERSION = "1.7"

_TITLEPATTERN = re.compile(r"^\s*\('.*'\) \? '.*' : '(?P<title>.*)'\s*;\s*$")
_URLDATEPATTERN = re.compile(r"^http://www\.washingtonpost\.com/wp-dyn/content/article/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/.*$")

_HEADLINE = "var wp_headline = "
_AUTHORSPATTERN = re.compile(r"^(var wp_authors = )|(var wp_author = )")
_CONTENTID = "var wp_content_id = "
_SECTION = "var wp_section = "

class MetadataGatherer (HTMLParser.HTMLParser):

    def __init__(self):
        self.metadata = {}
        HTMLParser.HTMLParser.__init__(self)

    def parse_starttag(self, i):

        def handle_malformed_starttag(cacher):
            lineno, offset = cacher.getpos()
            endpos = cacher.rawdata.find('>', i)
            cacher.updatepos(i, endpos)
            tagtext = cacher.rawdata[i:endpos+1]
            note(3, "Malformed start tag '%s' at line %s, column %s",
                 tagtext, lineno, offset)
            return ((endpos < 0) and endpos) or (endpos + 1)

        try:
            rval = HTMLParser.HTMLParser.parse_starttag(self, i)
            if rval < 0:
                if self.rawdata.find(">", i) >= 0:
                    return handle_malformed_starttag(self)
            return rval
        except HTMLParser.HTMLParseError, x:
            if x.msg.startswith("malformed start tag"):
                return handle_malformed_starttag(self)
            elif x.msg.startswith("junk characters in start tag:"):
                return handle_malformed_starttag(self)
            else:
                raise

    def handle_starttag (self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            if ("name" in d) and ("content" in d):
                self.metadata[d["name"]] = d["content"]
            if ("http-equiv" in d) and ("content" in d) and (d["http-equiv"] == "refresh"):
                url = d.get("content")
                i = url.find("url=")
                if (i >= 0):
                    self.metadata["refresh-url"] = url[i+4:]

    def handle_endtag(self, tag):
        pass

    def parse(filename):
        _m = MetadataGatherer()
        _m.feed(open(filename, 'r').read())
        return _m.metadata
    parse=staticmethod(parse)

class FindWashPostArticleMetadata (Ripper):

    def rip (self, folder, docid):

        def encodestring(s):
            # WashPost strings have xml char refs, and we want Unicode
            if not s:
                return s

            s = re.sub(r"&#([0-9]+);", lambda x: unichr(int(x.group(1))), s)
            s = re.sub(r"&([a-z]+);", lambda x: htmlentitydefs.name2codepoint(x.group(1)), s)
            return s

        def dequote(s):
            return re.sub(r"\\'", "'", s)

        def catclean(s):
            return re.sub(r"[/,]", "_", s)

        mdpath = os.path.join(folder, "metadata.txt")
        originalspath = os.path.join(folder, "originals", "original.html")
        if not (os.path.exists(mdpath) and os.path.exists(originalspath)):
            return
        md = read_metadata(mdpath)
        url = md.get("original-url")
        if not url:
            return
        host, port, path = parse_URL(url)
        if host != "www.washingtonpost.com":
            return

        # OK, it's from the Post
        new_metadata = MetadataGatherer.parse(originalspath)
        for line in open(originalspath):
            if line.startswith(_HEADLINE):
                line = line[len(_HEADLINE):].strip("\n")
                t = _TITLEPATTERN.match(line)
                if t:
                    new_metadata['hdl'] = dequote(t.group("title"))
            m = _AUTHORSPATTERN.search(line)
            if m:
                new_metadata['authors'] = dequote(line[len(m.group(0)):].strip(" ';\n"))
            if line.startswith(_CONTENTID):
                new_metadata['content-id'] = line[len(_CONTENTID):].strip(" ';\n")
            if line.startswith(_SECTION):
                section = line[len(_SECTION):].strip(" ';\n")
                i = section.index("'")
                new_metadata['section'] = section[:i]

        if "source" not in md:
            md["source"] = "Washington Post"

        # not all articles have metadata...
        if not ('hdl' in new_metadata):
            note(3, "No metadata in article:  %s", new_metadata)
            return

        md["title"] = encodestring(new_metadata.get("hdl") or md.get("title"))

        if "date" not in md:
            # get the date
            d = _URLDATEPATTERN.match(url)
            if d:
                md["date"] = "%s/%s/%s" % (d.group('month'), d.group('day'), d.group('year'))

        if "authors" not in md:
            # get the byline
            d = new_metadata.get("authors")
            if d:
                md["authors"] = encodestring(d)

        d = new_metadata.get("keywords")
        d0 = md.get("keywords")
        if d and d0:
            d0 = [x.strip() for x in d0.split(',')] + [x.strip() for x in d.split(';')]
        elif d:
            d0 = [x.strip() for x in d.split(';')]
        if d0:
            md["keywords"] = encodestring(','.join(d0))
        if new_metadata.get("description"):
            md["summary"] = encodestring(new_metadata.get("description"))
            md["abstract"] = encodestring(new_metadata.get("description"))
        section = new_metadata.get("section")
        if section:
            c = md.get("categories")
            if c:
                c = [x.strip() for x in c.split(",")]
            else:
                c = []
            c = c + ["article", "Washington Post/%s" % catclean(section)]
            md["categories"] = ",".join(c)
        content_id = new_metadata.get("content-id")
        if content_id:
            md["citation"] = "Washington Post article %s" % content_id
        update_metadata(mdpath, md)


def after_repository_instantiation (repo):
    rippers = repo.rippers()
    # add at front so citation is available when indexing is done
    rippers.insert(0, FindWashPostArticleMetadata(repo))


if __name__ == "__main__":
    set_verbosity(4)
    m = FindWashPostArticleMetadata(None)
    m.rip(sys.argv[1], None)
    print open(os.path.join(sys.argv[1], "metadata.txt")).read()
