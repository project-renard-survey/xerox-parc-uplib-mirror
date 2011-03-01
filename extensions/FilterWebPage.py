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

import sys, os, re, tempfile, shutil, traceback, htmllib, types, htmlentitydefs, tempfile, formatter, codecs
import xml.dom.minidom

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    note(0, "Can't import BeautifulSoup; FilterWebPage not available")
else:

    from uplib.plibUtil import note, read_metadata
    from uplib.ripper import Ripper, rerip_generic

    class MyBeautifulSoup(BeautifulSoup):

        # if feedparser is imported, it will hack sgmllib.charref in a way which
        # will crash BeautifulSoup.  Mark Pilgrim thinks he's so smart...
        # see http://code.google.com/p/feedparser/issues/detail?id=110

        def handle_charref(self, ref):
            "Handle character references as data."
            if self.convertEntities:
                # hack! this is to work around feedparser's re-definition of
                # of sgmllib.charref
                if ref[0] == 'x':
                    data = unichr(int(ref[1:], 16))
                else:
                    data = unichr(int(ref))
            else:
                data = '&#%s;' % ref
            self.handle_data(data)

    class PageCleaner2 (object):

        # inspired by the Arc90.com "Readability" bookmarklet and the SiteScooper tool

        TRIMPATTERN = re.compile('(comment)|(metal)|(footer)|(footnote)', re.IGNORECASE)
        MAINPATTERN = re.compile('(^|\\s)(post|hentry|entry[-]?(content|text|body|story)?|article[-]?(content|text|body|story)?)(\\s|$)', re.IGNORECASE)
        BYLINE = re.compile(r".*(byline|author).*", re.IGNORECASE)
        PUBDATE = re.compile(r".*(timestamp|date|pubdate).*", re.IGNORECASE)
        DOUBLEBREAK = re.compile(r"<br/?>\s*<br/?>", re.DOTALL | re.IGNORECASE)

        BADTHINGS = ('form', 'object', 'h1', 'h2', 'iframe')

        def __init__(self, rootfile=None, content=None):
            if content is None:
                if isinstance(rootfile, file):
                    content = rootfile.read()
                else:
                    content = open(rootfile, 'rb').read()
            content = self.DOUBLEBREAK.sub('<p></p>', content)
            self.soup = MyBeautifulSoup(
                content, convertEntities=BeautifulSoup.HTML_ENTITIES,
                smartQuotesTo="html")
            title = self.soup.find("title")
            if title:
                self.title = self.textify(title)
            else:
                self.title = None
            self.content = self.figure_content()
            self.authors = self.figure_authors()
            self.date = self.figure_date()

        def textify(self, tag=None):
            if tag is None:
                if not self.top:
                    self.top = self.figure_content()
                texts = [self.textify(p) for p in self.top.contents]
                return '\n'.join([x for x in texts if x.strip()])
            elif tag.string:
                return tag.string
            else:
                return ''.join([self.textify(x) for x in tag.contents])

        def figure_content (self):

            scores = {}

            self.top = None

            # remove font tags
            for f in self.soup.findAll('font'):
                # remove the tag and promote its contents
                parent = f.parent
                for i in range(len(parent)):
                    if parent.contents[i] == f:
                        break
                f.extract()
                for elt in f.contents:
                    parent.contents.insert(i, elt)
                    i += 1

            # score toplevels
            for p in self.soup.findAll('p'):
                parent = p.parent
                if parent not in scores:
                    s = 0
                    # initialize score
                    pid = parent.get('id')
                    if pid:
                        if self.TRIMPATTERN.match(pid):
                            s -= 50
                        elif self.MAINPATTERN.match(pid):
                            s += 25
                    pclass = parent.get('class')
                    if pclass:
                        if self.TRIMPATTERN.match(pclass):
                            s -= 50
                        elif self.MAINPATTERN.match(pclass):
                            s += 25
                else:
                    s = scores.get(parent)
                s += 1                  # for this paragraph
                s += len(self.textify(p).split(','))-1
                scores[parent] = s                

            for p in self.soup.findAll('td'):
                if not p.findAll('p'):
                    parent = p.parent
                    if parent not in scores:
                        s = 0
                        # initialize score
                        pid = parent.get('id')
                        if pid:
                            if self.TRIMPATTERN.match(pid):
                                s -= 50
                            elif self.MAINPATTERN.match(pid):
                                s += 25
                        pclass = parent.get('class')
                        if pclass:
                            if self.TRIMPATTERN.match(pclass):
                                s -= 50
                            elif self.MAINPATTERN.match(pclass):
                                s += 25
                    else:
                        s = scores.get(parent)
                    s += 1                  # for this paragraph
                    s += len(self.textify(p).split(','))-1
                    scores[parent] = s                

            if not scores:
                raise ValueError("Can't score content")

            else:
                best = sorted(scores.items(), key=lambda x: x[1])[-1]
                return best[0]

        def clean_content(self, top):

            # remove all stylesheets
            for x in top.findAll('style'):
                x.extract()

            # and individual styles
            for x in top.findAll(True):
                if x.get('style'):
                    del x['style']
                # and check for bad kinds of things
                if x.name in self.BADTHINGS:
                    x.extract()

            # clean out divs
            baddivs = []
            for div in top.findAll('div'):
                p_count = len(div.findAll('p'))
                a_count = len(div.findAll('a'))
                img_count = len(div.findAll('img'))
                li_count = len(div.findAll('li'))
                embed_count = len(div.findAll('embed'))
                t = self.textify(div)
                comma_count = len(t.split(','))
                word_count = len(t.split())
                if (comma_count < 10 and (
                    (embed_count > 0) or (p_count == 0) or (a_count > p_count) or (img_count > p_count) or (li_count > p_count))
                    ):
                    baddivs.append(div)
            for div in baddivs:
                div.extract()

        def figure_authors(self):
            possibles = []
            for d in self.soup.findAll('div'):
                if self.BYLINE.match(d.get("id") or d.get("class") or ""):
                    if self.textify(d).strip():
                        possibles.append(d)
            # for d in possibles:
            #     print 'byline: ', d.get("id"), d.get("class"), repr(self.textify(d).strip())
            return possibles and possibles[0]

        def clean_authors(self, authors):
            pass

        def figure_date(self):
            possibles = []
            for d in self.soup.findAll('div'):
                if self.PUBDATE.match(d.get("id") or d.get("class") or ""):
                    if self.textify(d).strip():
                        possibles.append(d)
            # for d in possibles:
            #     print 'date: ', d.get("id"), d.get("class"), repr(self.textify(d).strip())
            return possibles and possibles[0]

        def clean_date(self, date):
            pass

        def render (self, fp):
            from uplib.plibUtil import note
            from uplib.webutils import htmlescape

            if not self.content:
                raise ValueError("can't score this document")

            if type(fp) in types.StringTypes:
                fp = open(fp, "ab")

            fp.write(u'<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>\n'.encode("UTF-8", "strict"))
            fp.write((u'<title>%s</title></head>\n' % htmlescape(self.title)).encode("UTF-8", "strict"))
            fp.write((u'<body>\n<h1>%s</h1>\n' % htmlescape(self.title)).encode("UTF-8", "strict"))
            if self.authors:
                self.clean_authors(self.authors)
                fp.write('<p class="uplib-authors">%s</p>\n' % self.authors.renderContents())
            if self.date:
                self.clean_date(self.date)
                fp.write('<p class="uplib-pubdate">%s</p>\n' % self.date.renderContents())
            self.clean_content(self.content)
            fp.write(self.content.prettify())
            fp.write(u'</body>\n'.encode("UTF-8", "strict"))

        def close (self):
            if self.doc:
                self.doc.unlink()

        def clean (rootfile, outputdir=None):
            from uplib.plibUtil import note
            pc = PageCleaner2(rootfile)
            if pc.content:
                pc.clean_content(pc.content)
            if pc.authors:
                pc.clean_authors(pc.authors)
            if pc.date:
                pc.clean_date(pc.date)
            newroot = os.path.join(outputdir, os.path.split(rootfile)[1])
            note("newroot is %s", newroot)
            shutil.copytree(os.path.split(rootfile)[0], outputdir)
            fp = open(newroot, "w")
            pc.render(fp)
            fp.close()
            return newroot
        clean = staticmethod(clean)

        def filter(content):
            pc = PageCleaner2(content=content)
            pc.clean_content(pc.content)
            return pc.content.prettify()
        filter = staticmethod(filter)


    class WebPageContentExtractor (Ripper):

        def rip (self, location, doc_id):

            rootpath = os.path.join(location, "originals", "original.html")
            pagecontentspath = os.path.join(location, "webpagecontents.txt")
            md = read_metadata(os.path.join(location, "metadata.txt"))
            mimetype = md.get("apparent-mime-type")
            #note("location is %s, rootpath is %s, mimetype = %s", location, rootpath, mimetype)
            if (mimetype == "text/html") and os.path.exists(rootpath):
                # clean it
                pc = PageCleaner2(rootpath)
                text = pc.textify().strip()
                if text:
                    fp = codecs.open(pagecontentspath, "w", "UTF-8")
                    fp.write(text)
                    fp.write("\n")
                    fp.close()

    def after_repository_instantiation(repo):

        rippers = repo.rippers()
        rippers.insert(0, WebPageContentExtractor(repo))

    def rerip(repo, response, params):

        rerip_generic (repo, response, params, WebPageContentExtractor(repo))



    if __name__ == "__main__":
        sys.path.append("/u/python")
        from uplib.webutils import Fetcher
        if len(sys.argv) > 1:
            if os.path.exists(sys.argv[1]):
                tfile1 = sys.argv[1]
            else:
                tfile1 = os.path.join(tempfile.mkdtemp(), "original.html")
                Fetcher().fetch_url(sys.argv[1], tfile1)
            folderdir = os.path.dirname(os.path.dirname(tfile1))
            WebPageContentExtractor(None).rip(folderdir, os.path.basename(folderdir))
            sys.stdout.write(open(os.path.join(folderdir, "pagecontents.txt"), "r").read())
            # pc = PageCleaner2(tfile1)
            # pc.clean_content(pc.content)
            # sys.stdout.write(''.join(pc.content(text=True)).strip().encode("ASCII", "backslashreplace"))
