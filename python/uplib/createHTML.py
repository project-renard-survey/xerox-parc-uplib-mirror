#!/usr/bin/env python
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
#

import re, os, sys, string, time, shutil, tempfile, stat, traceback, cgi, socket, types

from PIL import Image, ImageOps            # python image library (PIL)

from uplib.plibUtil import false, true, Error, note, configurator, read_metadata
from uplib.webutils import htmlescape

from uplib.ripper import Ripper
from uplib.basicPlugins import STANDARD_TOOLS_COLOR, STANDARD_BACKGROUND_COLOR, get_buttons_sorted, FN_DOCUMENT_SCOPE

CONTROLS_TEMPLATE_FILE = None
CONTROLS_TEMPLATE_FILE_MODDATE = 0
CONTROLS_TEMPLATE = None
CONTROLS_HEIGHT = None
THUMBNAIL_COLWIDTH = None
USE_VIRTUAL_INK = false

def _unicodify(s):
    if (type(s) != types.UnicodeType):
        return unicode(s, 'latin_1', 'replace')
    else:
        return s

def do_HTML (dirpath, html_dir, doc_id, port):

    note(3, "  HTMLing in %s...", dirpath)
    html_index = os.path.join(dirpath, "index.html")
    doc_id = os.path.basename(dirpath)
    retval = false
    try:
        if not os.path.exists(html_dir):
            os.mkdir(html_dir)
            os.chmod(html_dir, 0700)

        metadata = read_metadata(os.path.join(dirpath, "metadata.txt"))
        title = metadata.get('name') or metadata.get('title') or doc_id
        pagewidth = None
        pageheight = None
        bts = metadata.get('big-thumbnail-size')
        if bts:
            pagewidth, pageheight = [int(x) for x in string.split(bts, ',')]
            note(3, "    title is %s, pagesize is %sx%s", title, pagewidth, pageheight)

        # start with summary.html

        note(3, "    summary.html")
        summarypath = os.path.join(dirpath, "summary.txt")
        if os.path.exists(summarypath):
            f = open(summarypath, 'r')
            summary_text = f.read()
            f.close()
            html_summary = htmlescape(summary_text, true)
        else:
            html_summary = ""
        html_summary_path = os.path.join(html_dir, "summary.html")
        f = open(html_summary_path, 'w')
        f.write('<html><body>' + html_summary + '</body></html>');
        f.close()
        os.chmod(html_summary_path, 0600)        

        # next thumbs.html

        note(3, "    thumbs.html")
        thumbs_path = os.path.join(html_dir, "thumbs.html")
        f = open(thumbs_path, "w")
        if USE_VIRTUAL_INK:
            bgcolor = "white"
        else:
            bgcolor = STANDARD_TOOLS_COLOR
        f.write('<html><body bgcolor="%s"><center>\n' % bgcolor)
        thumbnail_dir = os.path.join(dirpath, "thumbnails")
        thumbnail_files = os.listdir(thumbnail_dir)
        thumbs = []
        for thumbnail in thumbnail_files:
            m = re.match(r"(\d+).png", thumbnail)
            if m:
                thumbs.append((int(m.group(1)), thumbnail,))
        thumbs.sort()
        for thumbnail in thumbs:
            page_no = int(thumbnail[0])
            f.write('<a href="page%s.html" target=viewarea>' % page_no)
            f.write('<img src="../thumbnails/%s" border=1></a><br>\n' % thumbnail[1])

            # now write the HTML connected to that thumbnail
            page_html = os.path.join(html_dir, "page%s.html" % page_no)
            f2 = open (page_html, 'w')
            # get width of large page
            if not pagewidth or not pageheight:
                im = Image.open(os.path.join(thumbnail_dir, "big%s.png" % page_no))
                pagewidth, pageheight = im.size[0] - 25, im.size[1]
                note(3, "    title is %s, pagesize is %sx%s", title, pagewidth, pageheight)
                del im
            f2.write('<html><body bgcolor="white"><img src="../thumbnails/big%s.png" usemap="#page%smap" border=0>\n' % (page_no, page_no))
            f2.write('<map name="page%smap">\n' % page_no)
            if (page_no < len(thumbs)):
                f2.write('<area href="page%s.html" alt="to Page %s" shape="circle" coords="%s,60,10">\n'
                         % (page_no + 1, page_no + 1, pagewidth + 15))
                f2.write('<area href="page%s.html" alt="to Page %s" shape="rect" coords="%s,0,%s,%s">\n'
                         % (page_no + 1, page_no + 1, pagewidth/2, pagewidth, pageheight))
            if (page_no > 1):
                f2.write('<area href="page%s.html" alt="to Page %s" shape="circle" coords="%s,90,10">\n'
                         % (page_no - 1, page_no - 1, pagewidth + 15))
                f2.write('<area href="page%s.html" alt="to Page %s" shape="rect" coords="0,0,%s,%s">\n'
                         % (page_no - 1, page_no - 1, (pagewidth/2)-1, pageheight))
            f2.write('<area href="/" alt="to repository" target="_top" shape="circle" coords="%s,207,10">\n'
                     % (pagewidth + 15))
            f2.write('</map></body></html>\n')
            f2.close()
            os.chmod(page_html, 0600)
        f.write('</center></body></html>')
        f.close()
        os.chmod (thumbs_path, 0600)

        # next is controls.html

        note(3, "    controls.html")
        controls_path = os.path.join(html_dir, "controls.html")
        f = open(controls_path, "w")
        if CONTROLS_TEMPLATE:
            f.write(CONTROLS_TEMPLATE % { 'doc-id': doc_id })
        else:
            f.write('<html>\n<head>\n')
            f.write('<script type="text/javascript">\n')
            f.write('function newInWindow(did, title, w, h, sidebar, twopage) {\n')
            f.write('  var s = "/action/basic/dv_show?doc_id=" + did + "&no-margin=1";\n')
            f.write('  var c = "width=" + w + ",height=" + h;\n')
            f.write('  if (!sidebar)\n')
            f.write('    s = s + "&no-sidebar=1";\n')
            f.write('  if (twopage)\n')
            f.write('    s = s + "&two-pages=1";\n')
            f.write('  defaultStatus = s;\n')
            f.write('  window.open(s, title, config=c);\n')
            f.write('}\n')
            f.write('</script></head><body bgcolor="%s">\n<center>\n' % STANDARD_TOOLS_COLOR)
            f.write("""<a href="javascript:newInWindow('%s','%s', %d+30, %d+10, false, false); void 0;">Detach</a>""" % (doc_id, htmlescape(title, true), pagewidth, pageheight))
            f.write(""" <a href="javascript:newInWindow('%s','%s', (2 * %d)+30, %d+10, false, true); void 0;">(2)</a>\n""" % (doc_id, htmlescape(title, true), pagewidth, pageheight))
            buttons = get_buttons_sorted(FN_DOCUMENT_SCOPE)
            for button in buttons:
                url = button[1][4]
                target = button[1][3]
                label = button[1][0]
                if url:
                    f.write('<br>\n<a href="%s"' % htmlescape(url % doc_id, true))
                else:
                    f.write('<br>\n<a href="/action/basic/repo_userbutton?uplib_userbutton_key=%s&doc_id=%s"' % (button[0], doc_id))
                if target:
                    f.write(' target="%s"' % target)
                f.write('>%s</a>\n' % label)
            f.write("</center></body></html>")
        f.close()
        os.chmod(controls_path, 0600)

        # then index.html

        note(3, "    index.html")
        f = open(html_index, "w")
        f.write('<head>\n')
        f.write('<title>%s</title>\n</head>\n' % htmlescape(title))
        f.write('<base target="_top">'
                '<frameset cols="%s,*">'
                '<frameset rows="%s,*">'
                '<frame name=controls src="./html/controls.html">'
                '<frame name=thumbs src="./html/thumbs.html">'
                '</frameset>'
                '<frame name="viewarea" src="./html/page1.html">'
                '</frameset>\n' % (THUMBNAIL_COLWIDTH, CONTROLS_HEIGHT))
        f.close()
        os.chmod(html_index, 0600)

        # indicate successful completion
        note(3, "  finished.")
        retval = true

    except:
        info = sys.exc_info()
        note(0, "exception raised in createHTML:\n%s\n", string.join(traceback.format_exception(*info)))
        raise

    else:
        if not retval:
            note("bad retval %s", retval)
            if os.path.exists(html_index): os.unlink(html_index)
            if os.path.exists(html_dir): shutil.rmtree(html_dir)


def htmlize_folder (repo, path, doc_id):
    update_configuration()
    if (os.path.isdir(path) and os.path.isdir(os.path.join(path, "thumbnails"))):
        try:
            do_HTML(path, os.path.join(path, "html"), doc_id, repo.secure_port())
        except:
                note(0, "exception raised in do_HTML:\n%s\n", ''.join(traceback.format_exception(*sys.exc_info())))

def update_configuration():

    global CONTROLS_TEMPLATE_FILE, CONTROLS_TEMPLATE, CONTROLS_TEMPLATE_FILE_MODDATE, CONTROLS_HEIGHT
    global THUMBNAIL_COLWIDTH, USE_VIRTUAL_INK

    conf = configurator.default_configurator()
    template = conf.get("default-html-controls-template-file")
    if template: template = os.path.expanduser(template)
    if template and os.path.exists(template):
        moddate = os.path.getmtime(template)
    note(3, "default-html-controls-template-file is %s (was %s)", template, CONTROLS_TEMPLATE_FILE)
    if (template and os.path.exists(template) and
        (CONTROLS_TEMPLATE_FILE != template or CONTROLS_TEMPLATE_FILE_MODDATE < moddate)):
        note(3, "re-reading controls template file")
        fp = open(template, 'r')
        CONTROLS_TEMPLATE = fp.read()
        fp.close()
        CONTROLS_TEMPLATE_FILE = template
        CONTROLS_TEMPLATE_FILE_MODDATE = moddate
    CONTROLS_HEIGHT = conf.get_int('html-controls-panel-height') or 200
    THUMBNAIL_COLWIDTH = conf.get_int('html-thumbnails-column-width') or 130
    USE_VIRTUAL_INK = conf.get_bool("use-alpha-channel-thumbnails") or false
    plib_path = conf.get("plib-path")




class HTMLRipper (Ripper):

    def rip (self, location, doc_id):
        htmlize_folder(self.repository(), location, doc_id)

    def rerun_after_metadata_changes(self, changed_fields=None):
        if changed_fields:
            return ("name" in changed_fields or
                    "title" in changed_fields or
                    "images-dpi" in changed_fields)
        else:
            return True
