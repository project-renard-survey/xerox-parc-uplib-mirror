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
# This extension provides a function which will produce and return
# an ePub version of a document.
#

import sys, os, re, base64, zipfile, time, urllib

from uplib.plibUtil import note, configurator, wordboxes_page_iterator, read_illustrations_metadata, get_fqdn, UPLIB_VERSION, get_machine_id
from uplib.webutils import HTTPCodes, htmlescape, get_extension_for_type
from uplib.paragraphs import _create_textual_HTML_version, _create_image_HTML_version, IMAGE_TYPES, NoWordboxesError

def _form_data_url (image):
    return u'data:image/png;base64,%s' % base64.encodestring(image).strip()

def _get_zip_info (piecename):
    zinfo = zipfile.ZipInfo(filename=piecename,
                            date_time=time.localtime(time.time()))
    zinfo.compress_type = zipfile.ZIP_DEFLATED
    return zinfo

def _get_html_filepath (doc, debug=None, htmltype=None):

    filepath = os.path.join(doc.folder(), "versions", "document.html")
    if (not os.path.exists(filepath)) or (debug and ("rebuild" in debug)):
        t = doc.get_metadata('apparent-mime-type')
        created = False
        if (htmltype =="text") or (not htmltype) and ((not t) or (not IMAGE_TYPES.match(t))):
            # try for a textual version
            try:
                _create_textual_HTML_version(doc, debug=debug)
            except NoWordboxesError:
                pass
            if os.path.exists(filepath):
                created = True
        if (not created) or (htmltype == "image"):
            # make an image version
            try:
                _create_image_HTML_version(doc, debug=debug)
            except:
                note("Exception creating image HTML:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
                return None
        if not os.path.exists(filepath):
            return None
    return filepath

_DATA_URI_PATTERN = re.compile(r'src="data:(?P<maintype>[^/;]+?)/(?P<subtype>[^/;]+?)(?P<params>;[^;]+?)*?(;(?P<encoding>base64))?,(?P<data>[a-zA-Z0-9+-_\r\n]+)"', re.MULTILINE | re.DOTALL)

def _separate_images (html):
    images = {}
    counter = 0
    m = _DATA_URI_PATTERN.search(html)
    while m:
        maintype = m.group("maintype")
        subtype = m.group("subtype")
        encoding = m.group("encoding")
        params = m.group("params")
        data = m.group("data")
        content_type = "%s/%s" % (maintype, subtype)
        if encoding == "base64":
            data = base64.decodestring(data)
        image_name = "image-%s.%s" % (counter, get_extension_for_type(content_type))
        counter += 1
        images[image_name] = (content_type, data)
        html = html[:m.start()] + ('src="images/%s"' % image_name) + html[m.end():]
        m = _DATA_URI_PATTERN.search(html)
    return html, images

_HEAD_PATTERN = re.compile(r'</head>')

def get_epub_version (repo, response, params):

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc specified.\n")
        return
    elif not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc ID %s specified.\n" % doc_id)
        return

    doc = repo.get_document(doc_id)

    bookid = "uplibhash:" + doc.sha_hash()

    page_count = int(doc.get_metadata("page-count") or doc.get_metadata("pagecount") or "0")
    language = doc.text_language() or "en-US"

    package = (u'<?xml version="1.0"?>\n' +
               u'<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">\n')

    metadata = (u'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"\n' +
                u'          xmlns:opf="http://www.idpf.org/2007/opf">\n' +
                u'  <dc:identifier id="BookId">%s</dc:identifier>\n' % htmlescape(bookid) +
                u'  <dc:language>%s</dc:language>\n' % htmlescape(language))

    ncx = u"""<?xml version="1.0"  encoding="UTF-8"?>
              <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" 
              "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
              <ncx version="2005-1" xml:lang="en" xmlns="http://www.daisy.org/z3986/2005/ncx/">
               <head>
                 <meta name="dtb:uid" content="%s"/>
                 <meta name="dtb:depth" content="6"/>
                 <meta name="dtb:generator" content="UpLib %s"/>
                 <meta name="dtb:totalPageCount" content="%s"/>
                 <meta name="dtb:maxPageNumber" content="0"/>
               </head>
               """ % (bookid, UPLIB_VERSION, page_count)

    title = doc.get_metadata("title") or unicode(doc)
    authors = doc.get_metadata("authors")
    ncx += u"<docTitle><text>" + htmlescape(title) + u"</text></docTitle>\n"
    metadata += u'  <dc:title>%s</dc:title>\n' % htmlescape(title)
    if authors:
        authors = authors.split(" and ")
        for author in authors:
            ncx += u"<docAuthor><text>" + htmlescape(author) + u"</text></docAuthor>\n"
            metadata += u'  <dc:creator>%s</dc:creator>\n' % htmlescape(author)
    metadata += u'</metadata>\n'

    ncx += u'<navMap>\n'
    manifest = u'<manifest>\n'
    spine = u'<spine toc="toc.ncx">\n'

    contentpath = _get_html_filepath(doc, debug=("rebuild",))
    content = open(contentpath, "rb").read()
    # remove META tags
    start = content.index("</head>")
    content = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" ' +
               '               "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n' +
               '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="%s">\n<head>\n' % language.encode("UTF-8", "strict") +
               '<title>%s</title>\n</head>\n' % htmlescape(title)) + content[start + len('</head>'):]
    manifest += u'  <item id="contents" href="contents.xhtml" media-type="application/xhtml+xml" />\n'
    spine += u'  <itemref idref="contents" />\n'
    ncx += u'<navPoint id="contents" playOrder="1"><navLabel><text>Content</text></navLabel><content src="contents.xhtml" /></navPoint>\n'

    content, images = _separate_images(content)
    for image in images:
        content_type, bits = images[image]
        manifest += u'  <item id="%s" href="images/%s" media-type="%s" />\n' % (
            image, image, content_type)            

#     for page_index, bboxes in wordboxes_page_iterator(doc.folder()):
#         page_xhtml = (u'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n' +
#                       u'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="%s">\n' % language +
#                       u'<body>\n')
# #         if pageno in illustrations:
# #             for left, top, width, height, tp, image, junk in illustrations.get(pageno):
# #                 page_xhtml += u'<img width="%s" height="%s" alt="image on page" style="position:absolute; left:%spt; top:%spt;" src="%s" />' % (
# #                     width, height, left, top, _form_data_url(image))
#         for bbox in bboxes:
#             face = (bbox.is_italic() and "Italic") or "Regular"
#             family = (bbox.is_fixedwidth() and "Monospace") or (bbox.is_serif() and "Serif") or "Sans-Serif"
#             weight = (bbox.is_bold() and "Bold") or "Regular"
#             page_xhtml += u'<span style="font-family: %s; font-style: %s; font-weight: %s; font-size: %spt">%s</span>' % (
#                 bbox.left(), bbox.top(), family, face, weight, bbox.font_size() * 0.8, htmlescape(bbox.text()))
#             if bbox.ends_word():
#                 page_xhtml += u"\n"
#         page_xhtml += u"</body></html>\n"
#         pages[page_index] = page_xhtml
#         manifest += u'  <item id="page-%d" href="page-%d.xhtml" media-type="application/xhtml+xml" />\n' % (page_index, page_index)
#         spine += u'  <itemref idref="page-%d" />\n' % page_index
#         ncx += u'<navPoint class="page" id="page-%d" playOrder="%d"><navLabel><text>Page %s</text></navLabel><content src="page-%d.xhtml" /></navPoint>\n' % (
#             page_index, page_index + 1, doc.page_index_to_page_number_string(page_index), page_index)

    # close up the spine elements
    ncx += "</navMap>\n</ncx>"
    manifest += u'  <item id="toc.ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />\n'
    manifest += u'</manifest>\n'
    spine += u'</spine>\n'
    package += metadata + manifest + spine + u'</package>\n'

    # build the zip container
    filepath = os.path.join(doc.folder(), "versions")
    if not os.path.exists(filepath):
        os.mkdir(filepath)
        os.chmod(filepath, 0700)
    filepath = os.path.join(filepath, "document.epub")
    zf = zipfile.ZipFile(filepath, "w", zipfile.ZIP_STORED, True)
    zf.comment = "%s (from UpLib repository '%s', doc ID %s)" % (htmlescape(doc.get_metadata("title")), htmlescape(repo.name()), doc_id)
    zf.writestr("mimetype", "application/epub+zip")
    zf.writestr("META-INF/container.xml",
                """<?xml version="1.0"?>
                <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                <rootfiles>
                <rootfile full-path="packagelayout.opf"
                media-type="application/oebps-package+xml" />     
                </rootfiles>
                </container>
                """)
    zf.writestr(_get_zip_info("packagelayout.opf"), package.encode("UTF-8", "strict"))
    for image in images:
        content_type, bits = images[image]
        zf.writestr("images/%s" % image, bits)
    zf.writestr(_get_zip_info("contents.xhtml"), content)
    zf.writestr(_get_zip_info("toc.ncx"), ncx.encode("UTF-8", "strict"))
    zf.close()

    response.return_file("application/epub", filepath)

def get_svg_version (repo, response, params):

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc specified.\n")
        return
    elif not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc ID %s specified.\n" % doc_id)
        return

    note("doc_id is %s", doc_id)
    doc = repo.get_document(doc_id)
    page = params.get("page")
    if not page:
        response.error(HTTPCodes.BAD_REQUEST, "No page index specified.")
        return
    page = int(page)
    note("page is %s", page)
    page_count = int(doc.get_metadata("page-count") or doc.get_metadata("pagecount") or "0")
    if page >= page_count:
        response.error(HTTPCodes.BAD_REQUEST, "No such page %d." % page)
        return

    language = doc.text_language() or "en-US"
    dpi = int(doc.get_metadata('images-dpi') or doc.get_metadata('tiff-dpi') or doc.get_metadata("dpi") or 300)
    page_image_size = tuple([(float(x.strip())*72/float(dpi))
                             for x in (doc.get_metadata("images-size") or
                                       doc.get_metadata("tiff-size")).split(",")])

    pages = {}
    illustrations = {}
    links = {}

    imd = read_illustrations_metadata(doc.folder(), True)
    for (left, top, width, height, type, bits, pageno) in imd:
        if ((width * height) < 100):
            continue
        if pageno in illustrations:
            illustrations[pageno].append((left, top, width, height, bits, pageno))
        else:
            illustrations[pageno] = [(left, top, width, height, bits, pageno)]
    lmd = doc.links().values()
    for link in lmd:
        if hasattr(link, "from_page") and (link.typename == "uri"):
            pageno = link.from_page
            if pageno in links:
                links[pageno].append(link)
            else:
                links[pageno] = [link]            

    note("links are %s", links)

    for page_index, bboxes in wordboxes_page_iterator(doc.folder()):

        page_svg  = (u'''<?xml version="1.0" standalone="no"?>
                         <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
                                   "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
                            <svg width="%spt" height="%spt" version="1.1"
                                 xmlns="http://www.w3.org/2000/svg"
                                 xmlns:xlink="http://www.w3.org/1999/xlink">
                     ''' % page_image_size)

        if page_index in illustrations:
            for left, top, width, height, image, junk in illustrations.get(page_index):
                page_svg += u'<image x="%spt" y="%spt" width="%spt" height="%spt" xlink:href="%s" />\n' % (
                    left, top, width, height, _form_data_url(image))

        if page_index in links:
            note("links for %s are %s", page_index, links.get(page_index))
            for link in links[page_index]:
                fr = getattr(link, "from_rect")
                if fr:
                    left, top, width, height = fr
                    uri = urllib.quote_plus(link.to_uri)
                    page_svg += (u'<a xlink:href="%s"><rect x="%spt" y="%spt" ' % (uri, left, top) +
                                 u'width="%spt" height="%spt" fill="none" stroke="none" /></a>\n' % (
                                     width, height))

        for bbox in bboxes:
            face = (bbox.is_italic() and "Italic") or "Regular"
            family = (bbox.is_fixedwidth() and "Monospace") or (bbox.is_serif() and "Serif") or "Sans-Serif"
            weight = (bbox.is_bold() and "Bold") or "Regular"
            page_svg += u'<text x="%spt" y="%spt" font-family="%s" font-size="%spt" font-style="%s" font-weight="%s">%s</text>' % (
                bbox.left(), bbox.top(), family, bbox.font_size() * 0.9, face, weight, htmlescape(bbox.text()))
            if bbox.ends_word():
                page_svg += u"\n"
        page_svg += u"</svg>\n"
        pages[page_index] = page_svg

    for pageno in pages:
        note("%s: %s\n", pageno, len(pages.get(pageno)))

    response.reply(pages.get(page), "image/svg+xml")
