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

import string, re, os, sys, traceback, math, types, base64, hashlib
from urllib import quote_plus, unquote_plus
from StringIO import StringIO

from uplib.plibUtil import note, true, false

_LINK_ICON_CACHE = {}

QUOTED_FIELDS = ("title", )

class LinkIcon:

    # since many links may share the same icon, we "intern" the image bits of the
    # icon in this class, so that multiple links can use the same bits in memory

    DATA_URI_HEADER = "data:image/png;base64,"

    def find_icon (data=None, filename=None):
        import hashlib
        def hash_filename(filename):
            s = hashlib.sha1()
            s.update(filename)
            return s.digest()
        def hash_data_uri(uri):
            s = hashlib.sha1()
            s.update(uri)
            return s.digest()
        if data:
            if not type(data) in types.StringTypes or not data.startswith("data:"):
                raise ValueError("bad 'data' value:  %s" % data)
            h = hash_data_uri(data)
            if h in _LINK_ICON_CACHE:
                return _LINK_ICON_CACHE.get(h)
            icon = LinkIcon(data=data)
            _LINK_ICON_CACHE[h] = icon
            return icon
        elif filename:
            if not os.path.exists(filename):
                raise ValueError("non-existent file specified:  %s" % filename)
            h = hash_filename(os.path.normpath(os.path.realpath(filename)))
            if h in _LINK_ICON_CACHE:
                return _LINK_ICON_CACHE.get(h)
            icon = LinkIcon(filename=filename)
            _LINK_ICON_CACHE[h] = icon
            return icon
        else:
            raise ValueError("either 'data' or 'filename' must be specified; neither was")            
    find_icon = staticmethod(find_icon)

    def __init__(self, data=None, filename=None):
        if filename:
            from PIL import Image
            try:
                d = open(filename, 'rb').read()
                i = Image.open(StringIO(d))
                i.load()
            except:
                msg = string.join(traceback.format_exception(*sys.exc_info()))
                raise ValueError("Invalid image file %s: %s" % (filename, msg))
            if i.format != 'PNG':
                raise ValueError("Icon image files must be in PNG format; %s is not" % filename)
            del i
            self.bits = d
        elif data:
            if not data.startswith("data:"):
                raise ValueError("Invalid 'data' parameter %s" % data)
            if not data.startswith(self.DATA_URI_HEADER):
                raise ValueError("'data' parameters must be base64-encoded PNG images without additional parameters")
            self.bits = base64.decodestring(data[len(self.DATA_URI_HEADER):])
        else:
            raise ValueError("Neither 'data' nor 'filename' was specified")

    def get_writeable_form(self):
        return self.DATA_URI_HEADER + base64.encodestring(self.bits)[:-1]

class Link:

    def __init__(self, doc, fields):
        self.from_doc = doc
        self.filename = fields.get('filename')
        # id is required
        self.id = fields['id']
        if "to-uri" in fields:
            self.typename = "uri"
        elif "to-doc" in fields:
            self.typename = "gotor"
        elif "to-page" in fields:
            self.typename = "goto"
        else:
            raise ValueError("Can't figure type of link with fields %s" % fields)
        self.title = fields.get('title')
        self.user_type = fields.get('type')
        self.from_highlight_color = fields.get('from-highlight-color')
        self.to_uri = fields.get('to-uri')
        v = fields.get('from-page')
        if v is not None:
            self.from_page = int(v)
        else:
            self.from_page = None
        v = fields.get('from-span')
        if v is not None:
            self.from_span = tuple([int(x) for x in v.split(",")])
        else:
            self.from_span = None
        v = fields.get('from-rect')
        if v is not None:
            self.from_rect = tuple([float(x) for x in v.split(",")])
        else:
            self.from_rect = None
        v = fields.get('to-doc')
        if v is not None:
            if not doc.repo.valid_doc_id(v):
                note("Invalid to-doc ID %s specified", v)
                self.to_doc = None
            else:
                self.to_doc = doc.repo.get_document(v)
        else:
            self.to_doc = None
        v = fields.get('to-page')
        if v is not None:
            self.to_page = int(v)
        else:
            self.to_page = None
        v = fields.get('to-rect')
        if v is not None:
            self.to_rect = tuple([float(x) for x in v.split(",")])
        else:
            self.to_rect = None
        v = fields.get('from-icon')
        if v is not None:
            if isinstance(v, LinkIcon):
                self.icon = v
            else:
                self.icon = LinkIcon.find_icon(data=v)
        else:
            self.icon = None
        v = fields.get('from-icon-location')
        if v is not None:
            self.icon_location = tuple([float(x) for x in v.split(",")])
        else:
            self.icon_location = None

    def write(self, fp):
        # write self to open file fp in UpLib links format

        def writeifthere(fp, link, attrname, fieldname):
            if getattr(link, attrname) is not None:
                if attrname in QUOTED_FIELDS:
                    fp.write("%s: %s\n" % (fieldname, quote_plus(getattr(link, attrname))))
                else:
                    fp.write("%s: %s\n" % (fieldname, getattr(link, attrname)))

        def writenumbers(fp, link, attrname, fieldname):
            if getattr(link, attrname) is not None:
                fp.write("%s: %s\n" % (fieldname, string.join([str(x) for x in getattr(link, attrname)], ",")))

        fp.write("id: %s\n" % self.id)
        writeifthere(fp, self, "title", "title")
        writeifthere(fp, self, "user_type", "type")
        writeifthere(fp, self, "from_page", "from-page")
        writenumbers(fp, self, "from_span", "from-span")
        writenumbers(fp, self, "from_rect", "from-rect")
        writeifthere(fp, self, "from_highlight_color", "from-highlight-color")
        writeifthere(fp, self, "to_uri", "to-uri")
        writeifthere(fp, self, "to_page", "to-page")
        writenumbers(fp, self, "to_rect", "to-rect")
        writenumbers(fp, self, "icon_location", "from-icon-location")
        if self.to_doc:
            fp.write("to-doc: %s\n" % self.to_doc.id)
        if self.icon:
            iconbase64 = self.icon.get_writeable_form()
            iconvalue = string.join(iconbase64.split(), "\n  ")
            fp.write("from-icon: %s\n" % iconvalue)

    def permanent (self):
        return (self.filename == "permanent.links" or self.filename == "document.links")

    def get_filename(self):
        return self.filename

    def get_uri(self):
        return self.to_uri

    def is_internal(self):
        return not (self.to_uri or self.to_doc)

    def get_icon(self):
        return self.icon

    def get_highlight_color(self):
        if self.from_highlight_color:
            spec = self.from_highlight_color
            if spec[0] == '#':
                # rgb color spec
                nibbles = (len(spec) - 1) / 3
                divisor = float(16**nibbles)
                red = int(spec[1:1+nibbles], 16)/divisor
                green = int(spec[1+nibbles:1+(2*nibbles)], 16)/divisor
                blue = int(spec[1+(2*nibbles):], 16)/divisor
                return (red, blue, green)
        return None

    def get_title(self):
        return self.title

    def get_bounds(self):
        return (hasattr(self, "from_rect") and getattr(self, "from_rect")) or None

    def set_bounds(self, tpl):
        self.from_rect = tpl

    def off_page(self):
        bounds = self.get_bounds()
        if bounds:
            left, top, width, height = bounds
            pagewidth, pageheight = self.from_doc.page_size_in_points()
            if (((left + width) < 0) or ((top + height) < 0) or (left > pagewidth) or (top > pageheight)):
                return true
        return false


class pdflinksParser:

    def parse_fits (fit, d, lineparts):

        def eat (lineparts, count):
            retval = []
            for i in range(count):
                retval.append(float(lineparts[i]))
            return retval, lineparts[count:]

        if fit == "xyz":

            vals, lineparts = eat(lineparts, 3)
            d['dest-left'] = vals[0]
            d['dest-top'] = vals[1]
            d['dest-zoom'] = vals[2]

        elif fit == "fit" or fit == "fitb":

            pass

        elif fit == "fith" or fit == "fitbh":

            vals, lineparts = eat(lineparts, 1)
            d['dest-top'] = vals[0]

        elif fit == "fitv" or fit == "fitbv":

            vals, lineparts = eat(lineparts, 1)
            d['dest-left'] = vals[0]

        elif fit == "fitr":

            vals, lineparts = eat(lineparts, 4)
            d['dest-left'] = vals[0]
            d['dest-bottom'] = vals[1]
            d['dest-right'] = vals[2]
            d['dest-top'] = vals[3]

        elif fit == "unknown":

            d['unknown-fit-type'] = int(lineparts[0])
            lineparts = lineparts[1:]

        else:
            raise ValueError("bad fit value \"%s\"" % fit)

        return lineparts
    parse_fits = staticmethod(parse_fits)


    def parse_pdflinks_line (line):

        d = dict()
        lineparts = line.strip().split()

        d['pageno'] = int(lineparts[0])
        d['ul_corner'] = (float(lineparts[1]), float(lineparts[2]),)
        d['lr_corner'] = (float(lineparts[3]), float(lineparts[4]),)
        d['border_style'] = lineparts[5]
        action = lineparts[6]
        d['type'] = action

        if (action == "goto"):

            d['dest-page'] = int(lineparts[7])
            fit = lineparts[8]
            d['dest-fit'] = fit
            lineparts = pdflinksParser.parse_fits(fit, d, lineparts[9:])

        elif (action == "gotor"):

            d['dest-page'] = int(lineparts[7])
            fit = lineparts[8]
            d['dest-fit'] = fit
            lineparts = pdflinksParser.parse_fits(fit, d, lineparts[9:])
            d['dest-file'] = lineparts[0]

        elif (action == "uri"):

            desturi = string.join(lineparts[7:], ' ')
            if re.search("[/^]javascript:", desturi.lower()):
                d['type'] = 'action'
                d['action'] = desturi
            else:
                d['dest-uri'] = desturi

        else:
            note(4, "link with action \"%s\" ignored", action)

        return d

    parse_pdflinks_line = staticmethod(parse_pdflinks_line)


    def parse_pdflinks_output(f):

        if type(f) == types.FileType:
            pass
        elif type(f) in types.StringTypes and os.path.exists(f):
            f = open(f, 'r')
        else:
            ValueError("FILE argument to parse_pdflinks_output() must be either open file or filename")

        links = []
        for line in f:
            if not line.strip():
                continue
            try:
                note(5, "  link %s", line.strip())
                l = pdflinksParser.parse_pdflinks_line(line.strip())
            except:
                msg = string.join(traceback.format_exception(*sys.exc_info()))
                note("Exception parsing pdflinks line <%s>:\n%s", line.strip(), msg)
            else:
                if l: links.append(l)
        return links

    parse_pdflinks_output = staticmethod(parse_pdflinks_output)


    def write_links (links, filename):
        
        f = open(filename, 'wb')
        try:
            ignored = 0
            converted = 0

            first = true
        
            for link in links:
                ltype = link.get("type")
                if not ltype in ("goto", "uri"):
                    # only process links which take user to new location
                    ignored += 1
                    note(4, "link with type \"%s\" discarded", ltype)
                    continue
    
                left, top = link.get("ul_corner")
                right, bottom = link.get("lr_corner")
                fpage = link.get("pageno")
    
                idhash = hashlib.md5()
                idhash.update("%s,%d,%f,%f,%f,%f" % (ltype, fpage, left, top, right, bottom))
                id = idhash.hexdigest()
    
                if not first:
                    f.write("\f\n")
    
                f.write("id: %s\n" % id)
                f.write("type: %s\n" % ltype)
                f.write("from-page: %d\n" % (fpage - 1))
                f.write("from-rect: %.3f,%.3f,%.3f,%.3f\n" % (left, top, (right - left), (bottom - top)))
                if ltype == "uri":
                    f.write("to-uri: %s\n" % link.get("dest-uri"))
                elif ltype == "goto":
                    f.write("to-page: %d\n" % (link.get("dest-page") - 1))
                    fit = link.get("dest-fit")
                    if fit == "fitr":
                        dleft = link.get("dest-left")
                        dtop = link.get("dest-top")
                        dright = link.get("dest-right")
                        dbottom = link.get("dest-bottom")
                        f.write("to-rect: %.3f,%.3f,%.3f,%.3f\n" % (left, top, (right - left), (bottom - top)))
                first = false
                converted += 1
                        
            return converted, ignored
        
        finally:
            f.close()

    write_links = staticmethod(write_links)


    def convert_pdflinks_to_uplib_links (infile, outfile, dropped_pages=None):

        def convert_link_page(original_index, dropped_pages):
            if not dropped_pages:
                return original_index
            i = original_index - 1
            for p in dropped_pages:
                if i < p:
                    break
                else:
                    i -= 1
            return i + 1

        linkslist = pdflinksParser.parse_pdflinks_output(infile)
        if dropped_pages:
            for link in linkslist:
                if "pageno" in link:
                    link["pageno"] = convert_link_page(link["pageno"], dropped_pages)
                if "dest-page" in link and not "dest-file" in link:
                    link["dest-page"] = convert_link_page(link["dest-page"], dropped_pages)
        return pdflinksParser.write_links(linkslist, outfile)

    convert_pdflinks_to_uplib_links = staticmethod(convert_pdflinks_to_uplib_links)


def write_links_file (filename, links, update=true, remove=None, doc=None):
    """
    Write the links file specified by "filename".

    :param filename: the file to write or update
    :type filename: filename string
    :param links: the links to write to the file.  If "update" is True (the default), \
           the links will be added to the file; otherwise the file will \
           be overwritten with the specified "links".
    :type links: dict(string: uplib.links.Link)
    :param update: boolean specifying whether to add "links" to the file (``True``), \
           or overwrite the file with "links" (``False``).
    :type update: boolean
    :param remove: links to remove from the file
    :type remove: sequence(uplib.link.Links)
    """

    if update and os.path.exists(filename):
        existing_links = read_links_file(filename, doc)
        existing_links.update(links)
        if remove:
            for linkid in remove:
                if linkid in existing_links:
                    del existing_links[linkid]
        links = existing_links
    else:
        existing_links = {}
    fp = open(filename, "wb")
    try:
        first = true
        for link in links:
            if not isinstance(links[link], Link):
                note(0, "write_links_file(%s, %s, %s, %s) passed bad link %s" % (
                    filename, str(links), str(update), str(remove), str(links[link])))
                continue
            if not first:
                fp.write('\f\n')
            first = false
            links[link].write(fp)
    finally:
        fp.close()


def read_links_file (filename, doc=None):
    """
    Read a links file.

    :param filename: the file to read
    :type filename: filename string
    """

    if type(filename) == types.FileType:
        fp = filename
    elif type(filename) in types.StringTypes:
        fp = open(filename, 'rb')
    lastpart = os.path.split(fp.name)[1]
    links = {}
    current_link = {}
    lineno = 1
    name = None
    value = None
    for line in fp:
        if line == '\f\n':
            if current_link:
                current_link['filename'] = lastpart
                if doc:
                    links[current_link.get('id')] = Link(doc, current_link)
                else:
                    links[current_link.get('id')] = current_link
                current_link = {}
                name = None
        elif line[0] in string.whitespace:
            if name and current_link:
                current_link[name] = current_link[name] + line.strip()
        else:
            name_end = line.find(':')
            if name_end < 1:
                raise ValueError("Poorly shaped name-value pair \"%s\" in links file %s at line %d" % (line[:-1], filename, lineno))
            name = line[:name_end]
            if name in QUOTED_FIELDS:
                value = unquote_plus(line[name_end+1:].strip())
            else:
                value = line[name_end+1:].strip()
            current_link[name] = value
        lineno += 1
    if current_link:
        current_link['filename'] = lastpart
        if doc:
            links[current_link.get('id')] = Link(doc, current_link)
        else:
            links[current_link.get('id')] = current_link
    return links


def read_folder_links(FOLDER):

    links = []
    linksdir = os.path.join(FOLDER, "links")
    if os.path.isdir(linksdir):
        for name in os.listdir(linksdir):
            if os.path.splitext(name)[1] == ".links":
                newlinks = read_links_file(os.path.join(linksdir, name))
                links += newlinks.values()
    return links


if __name__ == "__main__":
    import uplib
    uplib.plibUtil.set_verbosity(5)
    pdflinksParser.convert_pdflinks_to_uplib_links(sys.argv[1], sys.argv[2])

#     pages = parse_XDOC_input(open(sys.argv[1], 'r').read())
#     for page in pages:
#         page.wordbox_lines(sys.stdout)
#         sys.stdout.write("\f\n")
