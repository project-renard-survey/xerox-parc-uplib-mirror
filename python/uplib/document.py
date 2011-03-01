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
#
# Code to implement the repository objects
#

import shelve, os, sys, string, time, traceback, re, math, types, unicodedata, struct, weakref

from uplib.plibUtil import true, false, note, lock_folder, unlock_folder, split_categories_string, subproc, Error, set_threaded, id_to_time, read_metadata, get_note_sink, uthread, parse_date
from uplib.plibUtil import update_metadata as p_update_metadata
from uplib.webutils import parse_URL, http_post_multipart
from uplib.links import read_links_file, Link, write_links_file

CHARSET_PATTERN = re.compile(r"^Content-Type:\s*text/plain;\s*charset=([^)]*)\n", re.IGNORECASE)
LANGUAGE_PATTERN = re.compile(r"^Content-Language:\s*(.*)\n", re.IGNORECASE)
NEWLINE_PATTERN = re.compile(r"([^\r])\n", re.MULTILINE)

def _reindex_document_folder(repo, folder, doc_id, changed_fields):
    try:
        import createIndexEntry, createHTML
        lock_folder(folder)
        try:
            note(3, "re-running some rippers on %s...", doc_id)
            standard_rippers = repo.rippers()
            rerun = []
            for i in range(len(standard_rippers)):
                ripper = standard_rippers[i]
                try:
                    if (ripper.rerun_after_metadata_changes(changed_fields=changed_fields)
                        or any([ripper.rerun_after_other_ripper(x.name()) for x in rerun])):
                        note(4, "    re-running ripper %s on %s", ripper.name(), doc_id)
                        ripper.rip(folder, doc_id)
                        rerun.append(ripper)
                except:
                    note("Exception running %s on %s:\n%s", ripper, doc_id,
                         ''.join(traceback.format_exception(*sys.exc_info())))
        finally:
            unlock_folder(folder)
    except:
        type, value, tb = sys.exc_info()
        note("while in _reindex_document_folder(%s):\n%s", doc_id, ''.join(traceback.format_exception(type, value, tb)))
    
def _newlinify(text):
    return NEWLINE_PATTERN.sub(r"\1\r\n", text)


def read_text_file(filepath):
    if os.path.exists(filepath):
        f = open(filepath, 'r')
        firstline = f.readline()
        if not firstline:
            # empty contents.txt
            f.close();
            return None
        m = CHARSET_PATTERN.match(firstline)
        if m:
            charset = m.group(1)
            f.readline()    # read and discard Content-Language field
        else:
            charset = "latin_1"
            f.seek(0)
        try:
            text = unicodedata.normalize("NFC", unicode(f.read(), charset))
        except UnicodeDecodeError, x:
            note(0, "Can't decode text of %s: %s", filepath, x)
            raise
        f.close()
        return text
    else:
        return None


def get_folder_notes(d):
    ann = {}
    if os.path.exists(d):
        for filename in os.listdir(d):
            if re.match("^[0-9]+$", filename):
                annotations = []
                # an annotations folder for page N
                page_index = int(filename)
                notesdir = os.path.join(d, filename)
                for notename in os.listdir(notesdir):
                    if re.match("^[0-9]+$", notename):
                        notedata = open(os.path.join(notesdir, notename), 'rb').read()
                        if struct.unpack(">B", notedata[:1])[0] != 0xFF:
                            pageindex, notenumber, nsubrecs = struct.unpack('>HHH', notedata[:6])
                            anchor_type, anchor_length = 0, 0
                            ptr = 6
                        else:
                            note_version, anchor_type, pageindex, notenumber, nsubrecs, anchor_length = (
                                struct.unpack(">BBHHHH", notedata[:10]))
                            ptr = 10 + anchor_length
                        annt = []
                        for i in range(nsubrecs):
                            try:
                                reclen,version,rectype = struct.unpack('>IBB', notedata[ptr:ptr+6])
                            except:
                                note("ptr is %d, len(notedata) is %d, notedata is %s",
                                     ptr, len(notedata), repr(notedata))
                                raise
                            if version != 0:
                                note("Unknown note version %s in %s", version, os.path.join(d, filename))
                                continue
                            if rectype == 1:
                                # only handle text annotations
                                t = unicode(notedata[ptr+6:ptr+reclen], 'utf-8', 'replace').strip()
                                annt.append(t)
                            ptr = ptr + reclen
                        annotations.append((notename, annt))
                ann[page_index] = annotations
    return ann


class Document (object):

    def __init__ (self, repo, id):

        self.repo = repo
        self.id = id
        self.__metadata = None
        self.__folder = repo.doc_location(id)
        self.__addtime = id_to_time(id)
        self.__pdforig = None
        self.__category_strings = None
        self.__citation = None
        self.__date = None
        self.__bboxes = {}
        self.__links = {}
        self.__removed_links = {}
        self.__touch_time = None
        self.__pagenumbering = None
        self.__icon_size = None

    def __str__(self):
        return "<document %s \"%s\" in '%s'>" % (self.id, self.name().encode("ASCII", "replace"), self.repo.name().encode("ASCII", "replace"))

    def __unicode__(self):
        return u"<document %s \"%s\" in '%s'>" % (self.id, self.name(), self.repo.name())

    def __repr__(self):
        return self.__str__()

    # pickling methods so that this can be stored on a file

    def __getstate__(self):
        # we just save our ID
        state = [self.id]
        return state

    def __setstate__(self, state):
        # we do this import here so that we can import 'document' without
        # causing a recursive import of 'repository'
        from uplib.repository import TheRepository
        self.id = state[0]
        self.repo = TheRepository
        self.__metadata = None
        self.__folder = self.repo.doc_location(self.id)
        self.__addtime = id_to_time(self.id)
        self.__pdforig = None

    def setfolder(self, d):
        if os.path.isdir(d):
            self.__folder = d

    # methods to access thumbnails and HTML
    #
    # this should probably allow returning either the bits, or a file handle from which they can be read
    #

    def text (self):
        return read_text_file(self.text_path())

    def summary_text (self):
        filename = os.path.join(self.folder(), "summary.txt")
        if os.path.exists(filename):
            f = open(filename, 'r')
            firstline = f.readline()
            if not firstline:
                # empty contents.txt
                f.close();
                return None
            m = CHARSET_PATTERN.match(firstline)
            if m:
                charset = m.group(1)
                f.readline()    # read and discard Content-Language field
            else:
                charset = "latin_1"
                f.seek(0)
            text = unicodedata.normalize("NFC", unicode(f.read(), charset))
            f.close()
            return text
        else:
            return None

    def _figure_charset_and_language(self):
        filename = self.text_path()
        if os.path.exists(filename):
            f = open(filename, 'r')
            firstline = f.readline()
            if firstline:
                m = CHARSET_PATTERN.match(firstline)
                if m:
                    tcs = m.group(1)
                    nextline = f.readline()
                    if nextline:
                        m = LANGUAGE_PATTERN.match(nextline)
                        if m:
                            lang = m.group(1)
                        else:
                            lang = "en"
                    else:
                        lang = "en"
                else:
                    tcs = "ISO-8859-1"
                    lang = "en"
            f.close()
        else:
            tcs = "ISO-8859-1"
            lang = "en"
        self.update_metadata({"text-charset" : tcs, "text-language" : lang})
        return tcs, lang

    def text_charset(self):
        tcs = self.get_metadata("text-charset")
        if not tcs:
            tcs, lang = self._figure_charset_and_language()
        return tcs

    def text_language(self):
        lang = self.get_metadata("text-language")
        if not lang:
            tcs, lang = self._figure_charset_and_language()
        return lang

    def summary_text (self):
        filename = os.path.join(self.folder(), "summary.txt")
        if os.path.exists(filename):
            return open(filename, 'r').read()
        else:
            return None

    def metadata_text (self):
        filename = self.metadata_path()
        if os.path.exists(filename):
            return open(filename, 'r').read()
        else:
            return None

    def html_index (self):
        filename = self.html_index_path()
        if os.path.exists(filename):
            return open(filename, 'r').read()
        else:
            return None

    def tiff_pages(self):
        filename = os.path.join(self.folder(), "document.tiff")
        if os.path.exists(filename):
            return open(filename, 'rb').read()
        else:
            return None

    def document_icon(self):
        filename = os.path.join(self.__folder, "thumbnails", "first.png")
        if os.path.exists(filename):
            return open(filename, 'rb').read()
        else:
            return None

    def small_page_thumbnail (self, pageno):
        filename = os.path.join(self.__folder, "thumbnails", "%d.png" % pageno)
        if os.path.exists(filename):
            return open(filename, 'rb').read()
        else:
            return None

    def large_page_thumbnail (self, pageno):
        filename = os.path.join(self.__folder, "thumbnails", "big%d.png" % pageno)
        if os.path.exists(filename):
            return open(filename, 'rb').read()
        else:
            return None

    def page_bboxes (self, pageno):
        filename = os.path.join(self.__folder, "thumbnails", "%d.bboxes" % pageno)
        note(4, "pagetext for page %s/%d %s exist", self.id, pageno, (os.path.exists(filename) and "does") or "doesn't")
        if os.path.exists(filename):
            return open(filename, 'rb').read()
        else:
            return None

    def large_page_image(self, pageno):
        filename = os.path.join(self.__folder, "page-images", "page%05d.png" % pageno)
        if os.path.exists(filename):
            return open(filename, 'rb').read()
        else:
            return None

    def html_page (self, pageno):
        filename = os.path.join(self.__folder, "html", "page%d.html" % pageno)
        if os.path.exists(filename):
            return open(filename, 'r').read()
        else:
            return None

    def html_controls (self, pageno):
        filename = os.path.join(self.__folder, "html", "controls.html")
        if os.path.exists(filename):
            return open(filename, 'r').read()
        else:
            return None

    def html_thumbs (self, pageno):
        filename = os.path.join(self.__folder, "html", "thumbs.html")
        if os.path.exists(filename):
            return open(filename, 'r').read()
        else:
            return None

    def html_summary (self, pageno):
        filename = os.path.join(self.__folder, "html", "summary.html")
        if os.path.exists(filename):
            return open(filename, 'r').read()
        else:
            return None

    def get_requested_part (self, path, params, query, fragment):

        # we could play games here with the "query" and "fragment", for example to
        # return different resolution thumbnails, or parts of the document

        prefix = "/docs/%s/" % self.id
        if not path.startswith(prefix):
            return None, ""
        suffix = path[len(prefix):]
        if suffix == "index.html":
            return self.html_index(), "text/html"
        elif suffix == "contents.txt":
            t = self.text()
            if t:
                bits = t.encode('utf8', 'replace')
                return _newlinify(bits), "text/plain; charset=utf8"
            else:
                return None, ""
        elif suffix == "summary.txt":
            t = self.summary_text()
            if t:
                bits = t.encode('utf8', 'replace')
                return _newlinify(bits), "text/plain; charset=utf8"
            else:
                return None, ""
        elif suffix == "metadata.txt":
            d = self.get_metadata().items()
            d.sort()
            r = ""
            for n, v in d:
                r += u'%s: %s\n' % (n, v)
            r = r.encode("UTF-8", "strict")
            return _newlinify(r), "text/plain; charset=utf-8"
        elif suffix == "document.tiff":
            return self.tiff_pages(), "image/tiff"
        elif re.match(r"page-images/page\d+.png", suffix):
            pageno = int(re.findall(r'\d+', suffix)[0])
            return self.large_page_image(pageno), "image/png"
        elif suffix.startswith("html/"):
            if suffix.endswith("controls.html"):
                return self.html_controls(), "text/html"
            elif suffix.endswith("thumbs.html"):
                return self.html_thumbs(), "text/html"
            elif suffix.endswith("summary.html"):
                return self.html_summary(), "text/html"
            elif re.match(r"html/page\d+.html", suffix):
                pageno = int(re.findall(r'\d+', suffix)[0])
                return self.html_page(pageno), "text/html"
        elif suffix.startswith("thumbnails/"):
            filename = re.match(r"thumbnails/(big\d+\.png|first\.png|\d+\.png|\d+.bboxes)", suffix).group(1)
            if filename == "first.png":
                return self.document_icon(), "image/png"
            elif filename.endswith(".bboxes"):
                pageno = int(re.findall(r'\d+', filename)[0])
                return self.page_bboxes(pageno), "application/x-page-bounding-boxes"
            elif filename.startswith("big"):
                pageno = int(re.findall(r'\d+', filename)[0])
                return self.large_page_thumbnail(pageno), "image/png"
            elif re.match(r'\d+\.png', filename):
                pageno = int(re.findall(r'\d+', filename)[0])
                return self.small_page_thumbnail(pageno), "image/png"
        return None, ""


    # general methods

    def name(self):
        return self.get_metadata("name") or self.get_metadata("title") or self.id

    def folder(self):
        return self.__folder

    def metadata_path (self):
        return(os.path.join(self.__folder, "metadata.txt"))

    def originals_path (self):
        return(os.path.join(self.__folder, "originals"))

    def icon_path (self):
        return(os.path.join(self.__folder, "thumbnails", "first.png"))

    def small_thumbnail_path (self, page_index):
        return os.path.join(self.__folder, "thumbnails", "%d.png" % (page_index + 1))

    def large_thumbnail_path (self, page_index):
        return os.path.join(self.__folder, "thumbnails", "big%d.png" % (page_index + 1))

    def page_image_path (self, page_index):
        if self.uses_png_page_images():
            return os.path.join(self.__folder, "page-images", "page%05d.png" % (page_index + 1))
        else:
            return None

    def text_path (self):
        return(os.path.join(self.__folder, "contents.txt"))

    def wordboxes_path (self):
        return(os.path.join(self.__folder, "wordbboxes"))

    def html_index_path (self):
        return(os.path.join(self.__folder, "html", "index.html"))

    def annotations_path (self):
        return(os.path.join(self.__folder, "annotations"))

    def notes_path (self):
        return(os.path.join(self.__folder, "annotations", "notes"))

    def paragraphs_path (self):
        return(os.path.join(self.__folder, "paragraphs.txt"))

    def uses_png_page_images(self):
        return os.path.isdir(os.path.join(self.__folder, "page-images"))

    def uses_tiff_page_images(self):
        return os.path.exists(os.path.join(self.__folder, "document.tiff"))

    def update_metadata (self, newdict, reindex=true):
        lock_folder(self.__folder)
        if reindex:
            oldvals = self.get_metadata().copy()
        try:
            self.__metadata = p_update_metadata(self.metadata_path(), newdict)
            self.__date = None
            self.__category_strings = None
            self.__citation = None
        finally:
            unlock_folder(self.__folder)
        if reindex:
            # show_stack(0, "mysterious re-indexing")
            d = newdict.copy()
            for k in d.keys():
                if oldvals.get(k) == d.get(k):
                    del d[k]
            newthread = uthread.start_new_thread(_reindex_document_folder, (self.repo, self.__folder, self.id, d.keys()))
            note(3, "reindexing %s in %s", self.id, str(newthread))

    def get_metadata(self, tag=None):
        if self.__metadata == None:
            mpath = self.metadata_path()
            if os.path.exists(mpath):
                self.__metadata = read_metadata (self.metadata_path())
        if tag:
            return self.__metadata and self.__metadata.get(tag)
        else:
            return self.__metadata or {}

    def get_date (self):
        if self.__date is None:
            d = self.get_metadata('date')
            if d:
                self.__date = parse_date(d)
        return self.__date

    def add_category (self, category_name, reindex=false):

        cats = self.get_category_strings()
        if not category_name in cats:
            self.repo.add_category(category_name)
            self.update_metadata({ 'categories' : string.join(cats + (category_name,), ", ") }, reindex)
            self.repo.touch_doc(self)

    def remove_category (self, category_name, reindex=false):

        cats = self.get_category_strings()
        if category_name in cats:
            newlist = list(cats)
            newlist.remove(category_name)
            self.update_metadata({ 'categories' : string.join(newlist, ", ") }, reindex)
            self.repo.touch_doc(self)

    def get_category_strings(self):
        if self.__category_strings is None:
            cs = self.get_metadata('categories')
            if cs:
                self.__category_strings = tuple([x.strip() for x in cs.strip().split(',')])
            else:
                self.__category_strings = ()
        return self.__category_strings

    def get_bboxes_for_page_index (self, index):
        if not self.__bboxes.has_key(index):
            import createPageBboxes
            self.__bboxes[index] = createPageBboxes.get_page_bboxes(os.path.join(self.folder(), "thumbnails"), index)
        return self.__bboxes[index]

    def get_bboxes_for_text_position (self, position):
        for boxes in self.__bboxes.values():
            if boxes.contains_text_pos(position):
                return boxes
        import createPageBboxes
        boxes = createPageBboxes.find_page (os.path.join(self.folder(), "thumbnails"), position)
        if boxes:
            self.__bboxes[boxes.page_index] = boxes
        return boxes

    def get_page_index_for_text_position (self, position):
        bb = self.get_bboxes_for_text_position(position)
        if bb:
            return bb.page_index
        else:
            return None

    def recache(self):
        self.__bboxes = {}
        self.__metadata = None
        self.__date = None
        self.__category_strings = None
        self.__citation = None
        self.__folder = self.repo.doc_location(self.id)
        self.__pagenumbering = None

    def add_time(self):
        return self.__addtime

    def touch_time(self):
        if self.__touch_time is None:
            # look at folders, and see if we can figure it out
            self.__touch_time = max(os.path.getmtime(self.metadata_path()),
                                    os.path.getmtime(self.folder()))
        return self.__touch_time

    def set_touch_time(self, t):
        self.__touch_time = t

    def touch (self):
        self.__touch_time = time.time()
        return self.__touch_time

    def original_name (self):
        originals_dir = os.path.join(self.__folder, "originals")
        if os.path.isdir(originals_dir):
            files = os.listdir(originals_dir)
            if len(files) == 1:
                fname, ext = os.path.splitext(files[0])
                return fname
        return None

    def pdf_original(self):
        if self.__pdforig == -1:
            return None
        elif self.__pdforig:
            return self.__pdforig
        else:
            originals_dir = os.path.join(self.__folder, "originals")
            if os.path.isdir(originals_dir):
                files = os.listdir(originals_dir)
                if len(files) == 1:
                    fname, ext = os.path.splitext(files[0])
                    if ext == '.pdf' or ext == '.PDF':
                        self.__pdforig = os.path.join(originals_dir, files[0])
                        return self.__pdforig
            self.__pdforig = -1
            return None

    def rerip (self, changed_fields=None, wait=False):

        try:

            import thread

            def rip_it (self):
                reruns = []
                for ripper in self.repo.rippers():
                    try:
                        if (ripper.rerun_after_metadata_changes(changed_fields=changed_fields) or
                            any([ripper.rerun_after_other_ripper(x.name()) for x in reruns])):
                            ripper.rip(self.folder(), self.id)
                            reruns.append(ripper)
                    except:
                        note("Exception running %s on %s:\n%s", ripper, self,
                             ''.join(traceback.format_exception(*sys.exc_info())))
                self.recache()

            newthread = uthread.start_new_thread(rip_it, (self,))
            if wait:
                newthread.join()
            return newthread

        except:
            
            type, value, tb = sys.exc_info()
            note("%s", traceback.format_exception(type, value, tb))


    def figure_file_name (self):
        name = self.get_metadata("title")
        if not name:
            name = self.original_name()
        if not name:
            name = self.id
        name = re.sub("[^-A-Z0-9a-z_]+", "_", name)
        return name


    def do_page_search (self, query_string):

        # we re-load the configuration parameters, in case they've changed

        result = self.repo.pylucene_search("pagesearch", query_string)
        if result is not None:
            return [(float(score), int(pageno),) for id, score, pageno in result if (id == self.id and pageno != '*')]

        command, output = self.repo.javalucene_search("pagesearch", query_string)

        try:
            results = []
            if string.strip(output):
                lines = string.split(output, '\n')
                for line in lines:
                    if line:
                        doc_id_plus_page, scorestring = string.split(line)
                        doc_id, pageno = doc_id_plus_page.split("/")
                        if doc_id == self.id and (pageno != '*'):
                            results.append((float(scorestring), int(pageno)))
            return results
        except:
            raise Error ("Error parsing output of search command.\nCommand was:  %s\nOutput was:\n%s\nException was:\n%s" %
                         (command, output, traceback.format_exception(*sys.exc_info())))


    def thumbnail_translation_and_scaling (self):
        import createThumbnails
        return createThumbnails.thumbnail_translation_and_scaling (self.folder())

    def page_size_in_points (self):
        dpi = int(self.get_metadata("images-dpi") or self.get_metadata("tiff-dpi") or 300)
        return (tuple([math.floor((int(x) * 72.0) / dpi + 0.5) for x in self.get_metadata("images-size").split(",")]))

    def get_page_numbering (self):
        if self.__pagenumbering is None:
            page_numbers = self.get_metadata("page-numbers")
            if page_numbers:
                self.__pagenumbering = []
                for range in page_numbers.split(";"):
                    try:
                        if ',' in range:
                            t, s, r = range.split(",")
                            if not (t in "dbr"):
                                note("document %s:  Invalid page-numbers string (unrecognized numbering-type code '%s'):  %s",
                                     self.id, t, page_numbers)
                                continue
                        elif '--' in range:
                            t = 'd'
                            begin, end = [int(x) for x in range.split('--')]
                            s = begin
                            r = "0-" + str(end - begin)
                        elif '-' in range:
                            t = 'd'
                            begin, end = [int(x) for x in range.split('-')]
                            s = begin
                            r = "0-" + str(end - begin)
                        self.__pagenumbering.append(([int(x) for x in r.split("-")], t, (s and int(s)) or 1,))
                    except:
                        note("exception processing range string '%s' in page_numbers value '%s':\n%s"
                             % (range, page_numbers, string.join(traceback.format_exception(*sys.exc_info()))))
            else:
                first_page = self.get_metadata("first-page-number")
                if first_page:
                    self.__pagenumbering = int(first_page)
                else:
                    self.__pagenumbering = 1
        return self.__pagenumbering

    def page_index_to_page_number_string (self, page_index):
        pn = self.get_page_numbering()
        if (type(pn) == types.IntType):
            return str(pn + page_index)
        elif (type(pn) == types.ListType):
            for pagerange, numbering_type, fpn in pn:
                first_page = pagerange[0]
                if len(pagerange) > 1:
                    last_page = pagerange[1]
                else:
                    last_page = pagerange[0]
                if (page_index >= first_page) and (page_index <= last_page):
                    if numbering_type == 'b':
                        return ""
                    elif numbering_type == 'd':
                        return str(page_index - first_page + fpn)
                    elif numbering_type == 'r':
                        # roman numeral
                        value = page_index - first_page + fpn
                        from roman import toRoman
                        return toRoman(value).lower()
                    else:
                        return ""
            return ""
        else:
            note("document %s:  bad page numbering %s", self.id, pn)
            self.__pagenumbering = 1
            return str(page_index + 1)

    def sha_hash (self):

        from addDocument import calculate_originals_fingerprint

        h = self.get_metadata("sha-hash")
        if h:
            return h

        p = self.originals_path()
        if os.path.isdir(p):
            key = calculate_originals_fingerprint(p)
        elif os.path.isdir(os.path.join(self.folder(), "page-images")):
            key = calculate_originals_fingerprint(os.path.join(self.folder(), "page-images"))
        elif os.path.exists(os.path.join(self.folder(), "document.tiff")):
            key = calculate_originals_fingerprint(os.path.join(self.folder(), "document.tiff"))
        else:
            raise ValueError("No document to take the fingerprint of!")

        self.update_metadata({"sha-hash" : key}, false)
        return key

    def links (self):
        if not self.__links:
            links = {}
            linksdir = os.path.join(self.folder(), "links")
            if os.path.isdir(linksdir):
                for name in os.listdir(linksdir):
                    if os.path.splitext(name)[1] == ".links":
                        links.update(read_links_file(os.path.join(linksdir, name), self))
                self.__links = links
            for linkid in self.__removed_links:
                if linkid in self.__links:
                    del self.__links[linkid]
        return self.__links

    def add_link(self, link):
        if not isinstance(link, Link):
            raise ValueError("Invalid link object %s" % link)
        self.__links[link.id] = link

    def remove_link (self, link):
        lnks = self.links()
        if link.id in lnks:
            l = lnks.get(link.id)
            if l.get_filename() == "permanent.links":
                raise ValueError("Can't remove permanent link %s." % l)
            del self.__links[link.id]
        self.__removed_links[link.id] = link

    def save_links(self):
        filenames = {}
        linksdir = os.path.join(self.folder(), "links")
        if not os.path.exists(linksdir):
            os.makedirs(linksdir, 0700)
        for linkid in self.__links:
            filename = self.__links[linkid].get_filename() or 'added.links'
            d = filenames.get(filename, None)
            if d is None:
                d = dict()
            d[linkid] = self.__links[linkid]
            filenames[filename] = d
        for filename in filenames:
            if filename == 'permanent.links':
                continue
            existing_links = filenames[filename]
            write_links_file(os.path.join(linksdir, filename), existing_links, true, self.__removed_links, self)

    def get_notes(self):
        return get_folder_notes(self.notes_path())

    def icon_size(self):
        if self.__icon_size is None:
            v = self.get_metadata("icon-size")
            if not v:
                from PIL import Image
                im = Image.open(self.icon_path())
                v = im.size
                self.update_metadata({ "icon-size": "%s,%s" % v }, False)
            else:
                v = v.split(',')
                v = (int(v[0].strip()), int(v[1].strip()), )
            self.__icon_size = v
        return self.__icon_size


