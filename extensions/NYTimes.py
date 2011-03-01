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
# The New York Times embeds metadata about the article in all articles published
# since 2001.  Use that metadata!
#

import sys, os, re, xml, HTMLParser, htmlentitydefs, urlparse

from uplib.ripper import Ripper
from uplib.plibUtil import note, configurator, read_metadata, update_metadata, set_verbosity
from uplib.webutils import parse_URL, Cache
from uplib.addDocument import URLDoc

UPLIB_MIN_VERSION = "1.7"


class MetadataGatherer (HTMLParser.HTMLParser):

    def __init__(self):
        self.metadata = {}
        HTMLParser.HTMLParser.__init__(self)

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


class FindNYTimesArticleMetadata (Ripper):

    def rip (self, folder, docid):

        def encodestring(s):
            # nytimes strings have xml char refs, and we want Unicode
            if not s:
                return s

            s = re.sub(r"&#([0-9]+);", lambda x: unichr(int(x.group(1))), s)
            s = re.sub(r"&([a-z]+);", lambda x: htmlentitydefs.name2codepoint(x.group(1)), s)
            return s

        mdpath = os.path.join(folder, "metadata.txt")
        originalspath = os.path.join(folder, "originals", "original.html")
        if not (os.path.exists(mdpath) and os.path.exists(originalspath)):
            return
        md = read_metadata(mdpath)
        url = md.get("original-url")
        if not url:
            return
        host, port, path = parse_URL(url)
        if host != "www.nytimes.com":
            return

        # OK, it's from the NY Times
        new_metadata = MetadataGatherer.parse(originalspath)

        if "source" not in md:
            md["source"] = "New York Times"

        # not all articles have metadata...
        if not ((('title' in new_metadata) or ('hdl' in new_metadata)) and ('pdate' in new_metadata)):
            note(3, "No metadata in article:  %s", new_metadata)
            return

        md["title"] = encodestring(new_metadata.get("hdl") or md.get("title"))
        if "date" not in md:
            # get the date
            d = new_metadata.get("pdate")
            md["date"] = "%s/%s/%s" % (d[4:6], d[6:], d[:4])
        if "authors" not in md:
            # get the byline
            d = new_metadata.get("byl")
            if d:
                if d.startswith("By "):
                    d = d[3:]
                # capitalize properly
                d = d.title()
                # lowercase "And"
                d = d.replace(" And ", " and ")
                md["authors"] = encodestring(d)
        d = new_metadata.get("keywords")
        d0 = md.get("keywords")
        if d0:
            d0 += ("," + d)
        else:
            d0 = d
        if d0:
            md["keywords"] = encodestring(d0)
        if new_metadata.get("description"):
            md["summary"] = encodestring(new_metadata.get("description"))
        update_metadata(mdpath, md)


class NYTimesParser (URLDoc):

    # The NY Time has a nasty habit of handing back ads sometimes.
    # This scans the pulled, cached page, and recaches it until the
    # ad disappears.

    BEFORE = (URLDoc,)

    def myformat (pathname):

        def nytimes_article(url):
            try:
                scheme, location, path, parameters, query, fragment = urlparse.urlparse(url)
            except:
                return False
            host = location.split(':')[0]
            return (host.endswith(".nytimes.com") and path.endswith(".html"))

        def nytimes_blog(url):
            try:
                scheme, location, path, parameters, query, fragment = urlparse.urlparse(url)
            except:
                return False
            host = location.split(':')[0]
            return host.endswith(".blogs.nytimes.com")

        if nytimes_article(pathname) or nytimes_blog(pathname):
            result = URLDoc.myformat(pathname)
            if result and ('cached-copy' in result):
                url = pathname
                # check for ad
                refreshed = 0
                while (refreshed < 3):
                    c = result.get('cached-copy')
                    if c and isinstance(c, Cache):
                        md = MetadataGatherer.parse(c.filename)
                    elif c in types.StringTypes:
                        md = MetadataGatherer.parse(c)
                    if nytimes_article(pathname) and ('pdate' in md) and ('articleid' in md):
                        # OK, real article
                        break
                    if nytimes_blog(pathname) and ('PST' in md) and ('CLMST' in md) and url.endswith("?pagemode=print"):
                        # OK, real blog post
                        break
                    # pull a fresh copy, see if we get it
                    if 'refresh-url' in md:
                        url = urlparse.urljoin(pathname, md.get('refresh-url'))
                    else:
                        url = pathname
                    if nytimes_blog(url):
                        if not url.endswith("?pagemode=print"):
                            url = urlparse.urljoin(url, "?pagemode=print")
                    note(3, "Pulling fresh version of NY Times article from %s...", url)
                    result = URLDoc.cache_local_copy(url)
                    refreshed += 1
            return result
    myformat=staticmethod(myformat)

def after_repository_instantiation (repo):
    rippers = repo.rippers()
    # add at front so citation is available when indexing is done
    rippers.insert(0, FindNYTimesArticleMetadata(repo))


if __name__ == "__main__":
    set_verbosity(4)
    m = FindNYTimesArticleMetadata(None)
    m.rip(sys.argv[1], None)
    print open(os.path.join(sys.argv[1], "metadata.txt")).read()
