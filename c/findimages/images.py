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
# extension for UpLib which adds a ripper which finds all the images
# in a document, and adds their bounding boxes to the metadata for
# that document

import sys, os, string, re, traceback, StringIO, base64, tempfile
from uplib.plibUtil import note, configurator, update_metadata, subproc, read_metadata, wordboxes_page_iterator
from uplib.webutils import HTTPCodes, htmlescape
from uplib.ripper import Ripper

FINDIMAGES_PROGRAM = None
PAGE_IMAGE_FILENAME_PATTERN = re.compile("page([0-9]*)\\.png")

def findimages(folder, debug=None):

    images = []

    if not FINDIMAGES_PROGRAM:
        note(3, "FINDIMAGES_PROGRAM not defined")
        return images

    images_dir = os.path.join(folder, "page-images")
    if not os.path.isdir(images_dir):
        note(3, "No page images in %s", images_dir)
        return images

    md = read_metadata(os.path.join(folder, "metadata.txt"))
    dpi = int(md.get("images-dpi") or md.get("dpi") or md.get("tiff-dpi") or 300)
    scaling_factor = float(dpi)/72

    def get_images_for_page (page_index, wordboxes, dpi, images_dir):
        pageimages = []
        filepath = os.path.join(images_dir, "page%05d.png" % (page_index + 1))
        if os.path.exists(filepath):
            wordboxes_file = tempfile.mktemp()
            try:
                boxlist = []
                if wordboxes:
                    # first, write out list of wordboxes, in Leptonica BOXA format
                    for i in range(len(wordboxes)):
                        box = boxes[i]
                        x, y, w, h = (int(box.left() * dpi / 72.0), int(box.top() * dpi / 72.0),
                                      int(box.width() * dpi / 72.0), int(box.height() * dpi / 72.0))
                        if (w > 0) and (h > 0):
                            boxlist.append((x, y, w, h))
                    if len(boxlist) > 0:
                        fp = open(wordboxes_file, "wb")
                        fp.write("\nBoxa Version 2\nNumber of boxes = %d\n" % len(boxlist))
                        for i in range(len(boxlist)):
                            fp.write("  Box[%d]: " % i + "x = %d, y = %d, w = %d, h = %d\n" % boxlist[i])
                        fp.close()
                # now, run the finder on the page image plus the list of wordboxes
                debug_arg = (debug and "--debug") or " "
                cmd = "%s %s %s %s %s" % (FINDIMAGES_PROGRAM, debug_arg, dpi, filepath, (boxlist and wordboxes_file) or "-")
                note(4, "findimages cmd is <<%s>>", cmd)
                status, output, tsignal = subproc(cmd)
                if status == 0:
                    for line in [x.strip() for x in output.split('\n') if x.strip()]:
                        if not line.startswith("halftone "):
                            continue
                        pageimages.append((str(page_index) + " " + line.strip()).split())
                else:
                    note(3, "findimages command <%s> returns bad status %s:\n%s\n" % (cmd, status, output))
            finally:
                # remove the temp file
                if os.path.exists(wordboxes_file):
                    os.unlink(wordboxes_file)
                    # note("%d:  wordboxes file is %s", page_index, wordboxes_file)
        return pageimages

    if os.path.exists(os.path.join(folder, "wordbboxes")):
        for page_index, boxes in wordboxes_page_iterator(folder):
            images += get_images_for_page (page_index, boxes, dpi, images_dir)
    else:
        # handle case where there's no text for the image
        files = os.listdir(images_dir)
        for file in files:
            m = PAGE_IMAGE_FILENAME_PATTERN.match(file)
            if m:
                pageimages = get_images_for_page(int(m.group(1))-1, None, dpi, images_dir)
                images += pageimages

    point_squared = scaling_factor * scaling_factor
    images = [(pageno, imtype, x, y, width, height)
              for (pageno, imtype, x, y, width, height) in images
              if ((int(height) * int(width)) > point_squared)]
    note(3, "images for %s are %s", folder, images)
    return images
        
class ImageFindingRipper (Ripper):

    def provides(self):
        return "ImageFinding"

    def rip (self, location, doc_id, debug=None):

        images = findimages(location, debug)
        val = string.join([string.join(x, ":") for x in images], ',')
        update_metadata(os.path.join(location, "metadata.txt"), { 'illustrations-bounding-boxes' : val })

def show_images (repo, response, params):

    import Image

    id = params.get("doc_id")
    if not id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc ID specified")
        return

    doc = repo.get_document(id)

    images = doc.get_metadata("illustrations-bounding-boxes")
    if not images:
        response.reply("No illustration data found for %s." % doc)
        return
    dpi = int(doc.get_metadata("dpi") or doc.get_metadata("images-dpi") or 300)

    fp = response.open()
    fp.write("<body><h1>Illustrations in %s</h1>" % htmlescape(str(doc)))

    currentpage = None
    im = None
    for image in images.split(","):
        pageno, type, left, top, width, height = image.split(":")
        pageno = int(pageno)
        if pageno != currentpage:
            if currentpage is not None:
                fp.write('<hr>\n')
            fp.write("<p>Page %s" % (pageno + 1))
            currentpage = pageno
            im = None
        left = int(left)
        top = int(top)
        width = int(width)
        height = int(height)
        newwidth, newheight = (width * 75) / dpi, (height * 75)/dpi
        if (newwidth < 1) or (newheight < 1):
            continue
        filepath = os.path.join(doc.folder(), "page-images", "page%05d.png" % (pageno + 1))
        if im is None:
            if not os.path.exists(filepath):
                fp.write('<p>No image file %s for page %s' % (filepath, (pageno + 1)))
            else:
                im = Image.open(filepath)
            if im.mode in ("1", "P", "L"):
                im = im.convert("RGB")
            
        img = im.crop((left, top, left + width + 1, top + height + 1))
        img.load()
        # rescale to 75 dpi
        if dpi != 75:
            img = img.resize((newwidth, newheight), Image.ANTIALIAS)
        # convert to data: URL
        fpi = StringIO.StringIO()
        img.save(fpi, "PNG")
        bits = fpi.getvalue()
        fpi.close()
        fp.write('<p>%s:<br><img src="data:image/png;base64,%s">\n' % (image, base64.encodestring(bits).strip()))

def find_images (repo, response, params):

    id = params.get("doc_id")
    if not id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc ID specified")
        return
    debug = (params.has_key("debug") and "debug") or None

    doc = repo.get_document(id)

    if params.has_key("rerip") or not doc.get_metadata("illustrations-bounding-boxes"):
        ImageFindingRipper(repo).rip(doc.folder(), doc.id, debug)
        doc.recache()

    return show_images (repo, response, params)

def after_repository_instantiation(repo):

    # add the ripper

    if FINDIMAGES_PROGRAM:
        rippers = repo.rippers()
        rippers.insert(1, ImageFindingRipper(repo))
    else:
        note("No findimages program found.")

# finally, find the "findimages" program

FINDIMAGES_PROGRAM = configurator().get("findimages")
try:
    if not FINDIMAGES_PROGRAM:
        FINDIMAGES_PROGRAM = os.popen("which findimages").readline().strip()
        if FINDIMAGES_PROGRAM.startswith("no findimages "):
            FINDIMAGES_PROGRAM=None
except:
    FINDIMAGES_PROGRAM=None

    
if __name__ == "__main__":
    from uplib.plibUtil import set_verbosity
    set_verbosity(4)
    FINDIMAGES_PROGRAM = "./findimages"
    findimages(sys.argv[1], True)
