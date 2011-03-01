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

import string, re, urllib, sys, os, cgi, socket, time, traceback, StringIO, shutil, tempfile, struct, base64, codecs

from uplib.plibUtil import note, Error, lock_folder, unlock_folder, true, false, get_fqdn, get_note_sink, format_date, id_to_time, configurator
from uplib.webutils import HTTPCodes, htmlescape, parse_URL
from uplib.basicPlugins import STANDARD_BACKGROUND_COLOR, STANDARD_TOOLS_COLOR, STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, UPLIB_ORANGE_COLOR, get_buttons_sorted, FN_DOCUMENT_SCOPE, show_title
from uplib.basicPlugins import __output_document_icon as output_document_icon
from uplib.basicPlugins import __output_document_title as output_document_title
from uplib.basicPlugins import __issue_javascript_head_boilerplate as issue_javascript_head_boilerplate
from uplib.basicPlugins import __issue_menu_definition as issue_menu_definition
from uplib.basicPlugins import __issue_title_styles as issue_title_styles
from uplib.links import Link, LinkIcon
import uplib.related

FORMAT_NAME_MAPPING = {
    "text/plain": "text",
    "text/html": "HTML",
    "application/pdf" : "PDF",
    "application/postscript": "Postscript",
    "application/vnd.ms-powerpoint": "Powerpoint",
    "application/msword": "MS Word",
    "application/vnd.ms-excel": "MS Excel",
    "message/rfc822": "RFC-822 email",
    "image/tiff": "image",
    "image/gif": "image",
    "image/pbm": "image",
    "image/jpeg": "image",
    "image/png": "image",
    "audio/mp3": "MP3",
    }

CONTENT_TYPE = re.compile ('Content-Type: (.+)', re.IGNORECASE)

ANNO_FORMAT_FIRST = 0
ANNO_TYPE_SCRIBBLE = 0
ANNO_TYPE_VSCRIBBLE = 5
ANNO_TYPE_ERASURE = 6

ACTIVITY_CODE_NAMES = { 1 : "PAGE_TURNED",
                        2 : "SCRIBBLED",
                        3 : "HOTSPOT_CLICKED",
                        4 : "THUMBNAILS_OPENED",
                        5 : "THUMBNAILS_CLOSED",
                        6 : "DOC_OPENED",
                        7 : "DOC_CLOSED",
                        }

INKPOT_NAMES = {
    "no-ink" : 0,
    "red-ink" : 1,
    "blue-ink" : 2,
    "pink-hiliter" : 3,
    "green-hiliter" : 4,
    "blue-hiliter" : 5,
    }

ACT_FORMAT_FIRST = 0
ACT_ACTION_CLOSE = 7
ACT_ACTION_PAGETURN = 1

# MODULE_PREFIX = "/action/pageview/"
MODULE_PREFIX = ""

USE_VERSION_2_HOTSPOT_PROTOCOL = false

hostname = get_fqdn()

extended_applet = """
<SCRIPT LANGUAGE="JavaScript"><!--
    var _info = navigator.userAgent; 
    var _ns = false; 
    var _ns6 = false;
    var _ie = (_info.indexOf("MSIE") > 0 && _info.indexOf("Win") > 0 && _info.indexOf("Windows 3.1") < 0);
//--></SCRIPT>
    <COMMENT>
        <SCRIPT LANGUAGE="JavaScript1.1"><!--
        var _ns = (navigator.appName.indexOf("Netscape") >= 0 && ((_info.indexOf("Win") > 0 && _info.indexOf("Win16") < 0 && java.lang.System.getProperty("os.version").indexOf("3.5") < 0) || (_info.indexOf("Sun") > 0) || (_info.indexOf("Linux") > 0) || (_info.indexOf("AIX") > 0) || (_info.indexOf("OS/2") > 0) || (_info.indexOf("IRIX") > 0)));
        var _ns6 = ((_ns == true) && (_info.indexOf("Mozilla/5") >= 0));
//--></SCRIPT>
    </COMMENT>
<SCRIPT LANGUAGE="JavaScript"><!--
    if (_ie == true) document.writeln('<OBJECT classid="clsid:8AD9C840-044E-11D1-B3E9-00805F499D93" WIDTH = %(applet-width)d HEIGHT = %(applet-height)d NAME = "%(applet-name)s"  codebase="http://java.sun.com/products/plugin/autodl/jinstall-1_4-windows-i586.cab#Version=1,4,0,0"><NOEMBED><XMP>');
    else if (_ns == true && _ns6 == false) document.writeln('<EMBED \
	    type="application/x-java-applet;version=1.4" \
            CODE = "%(applet-class)s" \
            JAVA_CODEBASE = "/" \
            ARCHIVE = "%(jar-file)s" \
            NAME = "%(applet-name)s" \
            WIDTH = %(applet-width)d \
            HEIGHT = %(applet-height)d \
            IMAGE_DIR ="/docs/%(doc-id)s/thumbnails" \
            SCRIBBLE_SINK ="%(scribble-sink-url)s" \
            SCRIBBLE_SOURCE ="%(scribble-source-url)s" \
            HOTSPOTS_SINK ="%(hotspots-sink-url)s" \
            HOTSPOTS_SOURCE ="%(hotspots-source-url)s" \
            ACTIVITY_LOGGER ="%(activity-sink-url)s"\
            PAGE_COUNT ="%(page-count)d" \
            FIRST_PAGE_NUMBER = "%(first-page-number)d" \
            CURRENT_PAGE ="%(current-page)d" \
            SELECTION_START ="%(selection-start)s" \
            SELECTION_END ="%(selection-end)s" \
            DOC_TITLE ="%(applet-title)s" \
            IMAGES_DPI ="%(images-dpi)s" \
            PAGE_WIDTH ="%(page-width)d" \
            PAGE_HEIGHT ="%(page-height)d" \
            PAGE_SCALING ="%(page-scaling)s" \
            PAGE_TRANSLATION_X ="%(page-translation-x)s" \
            PAGE_TRANSLATION_Y ="%(page-translation-y)s" \
            PAGETURN_ANIMATION_MS ="%(pageturn-animation-millisecs)d" \
            THUMBNAIL_WIDTH ="%(thumbnail-width)d" \
            THUMBNAIL_HEIGHT ="%(thumbnail-height)d" \
            THUMBNAIL_SCALING ="%(thumbnail-scaling)s" \
            HAS_HI_RES_IMAGES ="%(has-hi-res-images)s" \
            RIGHT_MARGIN = "%(right-margin)d" \
            DOC_ID ="%(doc-id)s" \
            CONTROLS ="%(show-controls-bool)s" \
            HAS_TEXT ="%(has-text-boxes)s" \
            LOGO_URL ="%(logo-url)s" \
            SHOW_TWO_PAGES ="%(show-two-pages-bool)s" \
            SHOW_ADH = "%(adh-mode)s" \
            SHOW_RSVP = "%(rsvp-mode)s" \
            PROGRESSBAR="true" \
            BOXMESSAGE="Loading UpLib Pageview code..." \
            BOXBGCOLOR="%(background-color)s" \
            PROGRESSCOLOR="%(uplib-orange-color)s" \
            SHOW_ANNOTATIONS="%(annotations-state)s" \
            SELECTED_INKPOT="%(inkpot)s" \
            BOOKMARK_DATA="%(bookmarks-state)s" \
            PAGE_NUMBERS="%(page-numbers)s" \
	    scriptable=false \
	    pluginspage="http://java.sun.com/products/plugin/index.html#download"><NOEMBED><XMP>');
//--></SCRIPT>
<APPLET  CODE = "%(applet-class)s" JAVA_CODEBASE = "/" ARCHIVE = "%(jar-file)s" WIDTH = %(applet-width)d HEIGHT = %(applet-height)d NAME = "%(applet-name)s" MAYSCRIPT></XMP>
    <PARAM NAME = CODE VALUE = "%(applet-class)s" >
    <PARAM NAME = CODEBASE VALUE = "/" >
    <PARAM NAME = ARCHIVE VALUE = "%(jar-file)s" >
    <PARAM NAME = NAME VALUE = "%(applet-name)s" >
    <PARAM NAME="type" VALUE="application/x-java-applet;version=1.4">
    <PARAM NAME="scriptable" VALUE="false">
    <PARAM NAME="progressbar" VALUE="true">
    <PARAM NAME="boxmessage" VALUE="Loading UpLib Pageview code...">
    <PARAM NAME="boxbgcolor" VALUE="%(background-color)s">
    <PARAM NAME="progresscolor" VALUE="%(uplib-orange-color)s">
    <PARAM NAME = "IMAGE_DIR" VALUE="/docs/%(doc-id)s/thumbnails">
    <PARAM NAME = "SCRIBBLE_SINK" VALUE="%(scribble-sink-url)s">
    <PARAM NAME = "SCRIBBLE_SOURCE" VALUE="%(scribble-source-url)s">
    <PARAM NAME = "HOTSPOTS_SINK" VALUE="%(hotspots-sink-url)s">
    <PARAM NAME = "HOTSPOTS_SOURCE" VALUE="%(hotspots-source-url)s">
    <PARAM NAME = "ACTIVITY_LOGGER" VALUE="%(activity-sink-url)s">
    <PARAM NAME = "PAGE_COUNT" VALUE="%(page-count)d">
    <PARAM NAME = "FIRST_PAGE_NUMBER" VALUE="%(first-page-number)d">
    <PARAM NAME = "CURRENT_PAGE" VALUE="%(current-page)d">
    <PARAM NAME = "SELECTION_START" VALUE="%(selection-start)s">
    <PARAM NAME = "SELECTION_END" VALUE="%(selection-end)s">
    <PARAM NAME = "DOC_TITLE" VALUE="%(applet-title)s">
    <PARAM NAME = "HAS_HI_RES_IMAGES" VALUE="%(has-hi-res-images)s">
    <PARAM NAME = "IMAGES_DPI" VALUE="%(images-dpi)s">
    <PARAM NAME = "PAGE_WIDTH" VALUE="%(page-width)d">
    <PARAM NAME = "PAGE_HEIGHT" VALUE="%(page-height)d">
    <PARAM NAME = "PAGE_SCALING" VALUE="%(page-scaling)s">
    <PARAM NAME = "PAGE_TRANSLATION_X" VALUE="%(page-translation-x)s">
    <PARAM NAME = "PAGE_TRANSLATION_Y" VALUE="%(page-translation-y)s">
    <PARAM NAME = "PAGETURN_ANIMATION_MS" VALUE="%(pageturn-animation-millisecs)d">
    <PARAM NAME = "THUMBNAIL_WIDTH" VALUE="%(thumbnail-width)d">
    <PARAM NAME = "THUMBNAIL_HEIGHT" VALUE="%(thumbnail-height)d">
    <PARAM NAME = "THUMBNAIL_SCALING" VALUE="%(thumbnail-scaling)s">
    <PARAM NAME = "RIGHT_MARGIN" VALUE="%(right-margin)d">
    <PARAM NAME = "DOC_ID" VALUE="%(doc-id)s">
    <PARAM NAME = "CONTROLS" VALUE="%(show-controls-bool)s">
    <PARAM NAME = "LOGO_URL" VALUE="%(logo-url)s">
    <PARAM NAME = "HAS_TEXT" VALUE="%(has-text-boxes)s">
    <PARAM NAME = "SHOW_ANNOTATIONS" VALUE="%(annotations-state)s">
    <PARAM NAME = "SHOW_ADH" VALUE="%(adh-mode)s">
    <PARAM NAME = "SHOW_RSVP" VALUE="%(rsvp-mode)s">
    <PARAM NAME = "SELECTED_INKPOT" VALUE="%(inkpot)s">
    <PARAM NAME = "BOOKMARK_DATA" VALUE="%(bookmarks-state)s">
    <PARAM NAME = "PAGE_NUMBERS" VALUE="%(page-numbers)s">
    <PARAM NAME = "SHOW_TWO_PAGES" VALUE="%(show-two-pages-bool)s">

There's an applet here that you aren't seeing...
</APPLET>
</NOEMBED>
</EMBED>
</OBJECT>
"""

def show_exception():
    import traceback, string, sys
    type, value, tb = sys.exc_info()
    s = string.join(traceback.format_exception(type, value, tb))
    note("Exception:  " + s)


def _get_parameter_dict (doc, conf, params, repo, request_context):

    def bool_test (m):
        if m is None:
            return false
        if (type(m) == type('')):
            if m.lower() == "true" or m.lower() == "t":
                return true
            else:
                return false
        return (m and true) or false


    two_pager = bool_test(params.get("two-pages"))
    pageturn_animation_ms = params.get("animate")
    if pageturn_animation_ms:
        pageturn_animation_ms = int(pageturn_animation_ms)
    else:
        pageturn_animation_ms = conf.get_int('pageturn-animation-milliseconds', 0)
    rsvp_mode = bool_test(params.get("rsvp"))
    adh_mode = bool_test(params.get("adh"))

    global USE_VERSION_2_HOTSPOT_PROTOCOL
    USE_VERSION_2_HOTSPOT_PROTOCOL = conf.get_bool("use-version-2-hotspots-protocol", false)

    images_size = doc.get_metadata("images-size")
    if not images_size:
        images_width = doc.get_metadata("tiff-width")
        images_height = doc.get_metadata("tiff-height")
        if (images_width is None or images_height is None) and doc.uses_png_page_images():
            from PIL import Image
            im = Image.open(StringIO.StringIO(doc.large_page_images(0)))
            images_width, images_height = im.size
        else:
            images_width = None
            images_height = None
    else:
        images_width, images_height = eval("(" + images_size + ")")

    images_dpi = int(doc.get_metadata("tiff-dpi") or doc.get_metadata("images-dpi") or 300)

    big_thumbnail_size = doc.get_metadata('big-thumbnail-size')
    if not big_thumbnail_size:
        # get width of large page
        from PIL import Image
        im = Image.open(os.path.join(doc.folder(), "thumbnails", "big1.png"))
        width, pageheight = im.size
        pagewidth = width - 25
        del im
    else:
        pagewidth, pageheight = eval('(' + big_thumbnail_size + ')')
    thumbnail_translation, thumbnail_scaling = doc.thumbnail_translation_and_scaling()

    small_thumbnail_size = doc.get_metadata('small-thumbnail-size')
    if not small_thumbnail_size:
        # get width of large page
        from PIL import Image
        im = Image.open(os.path.join(doc.folder(), "thumbnails", "1.png"))
        tn_width, tn_height = im.size
        del im
    else:
        tn_width, tn_height = eval('(' + small_thumbnail_size + ')')
    if (images_width is not None) and (images_height is not None):
        st_scaling = (float(tn_width)/images_width + float(tn_height)/images_height) / float(2)
    else:
        st_scaling = None

    pagecount = int(doc.get_metadata('page-count') or doc.get_metadata('pagecount'))

    title = doc.get_metadata('title') or doc.id
    first_page = doc.get_metadata("first-page-number")
    if not first_page:
        first_page = 1
    else:
        first_page = int(first_page)
    page_numbers = doc.get_metadata("page-numbers") or ""

    current_page, annotations_state, inkpot, b = _doc_state(doc)
    if annotations_state is None:
        annotations_state = conf.get_bool("annotations-initially-on", false)
    if inkpot is None:
        inkpot_name = conf.get("annotations-initial-inkpot")
        if inkpot_name:
            inkpot = INKPOT_NAMES.get(inkpot_name, 0)
        else:
            inkpot = 0
    bookmarks = ""
    for i in range(3):
        if i > 0:
            bookmarks = bookmarks + ";"
        bookmark_page, bookmark_height = b.get(i, (None, None))
        if bookmark_page is not None:
            bookmarks = bookmarks + "%d,%f" % (bookmark_page, bookmark_height)
    current_page = params.get("page") or current_page
    note("doc current page determined to be %s; annotations %s, %s; bookmarks are %s", current_page, annotations_state, inkpot, bookmarks)

    selection_start = params.get("selection-start")
    selection_end = params.get("selection-end");

    if not small_thumbnail_size or not big_thumbnail_size:
        data = {}
        if not small_thumbnail_size:
            data['small-thumbnail-size'] = '%d,%d' % (int(tn_width), int(tn_height))
        if not big_thumbnail_size:
            data['big-thumbnail-size'] = '%d,%d' % (int(pagewidth), int(pageheight))
        doc.update_metadata(data)

    has_text_boxes = (os.path.exists(os.path.join(doc.folder(), "thumbnails", "1.bboxes")))

    return { "doc-id": doc.id,
             "bg-color" : STANDARD_BACKGROUND_COLOR,
             "bookmarks-state" : bookmarks,
             "annotations-state" : (annotations_state and "true") or "false",
             "applet-width" : max(pageheight + 30, (2 * pagewidth) + 30),
             "applet-height": max(pagewidth + 10, pageheight + 10),
             "applet-name" : "UpLibReadUpApplet",
             "applet-class" : "com.parc.uplib.readup.applet.UpLibPageview",
             "applet-title" : htmlescape(title),
             "inkpot" : inkpot,
             "jar-file" : "/html/UpLibPageview.jar",
             "page-count" : pagecount,
             "first-page-number" : first_page,
             "current-page" : int(current_page),
             "page-width" : pagewidth,
             "page-height" : pageheight,
             "page-scaling" : ((thumbnail_scaling is None) and "unknown") or thumbnail_scaling[0],
             "page-translation-x" : ((not thumbnail_translation) and "unknown") or thumbnail_translation[0],
             "page-translation-y" : ((not thumbnail_translation) and "unknown") or thumbnail_translation[1],
             "pageturn-animation-millisecs" : pageturn_animation_ms,
             "has-hi-res-images" : (doc.uses_png_page_images() and "true") or "false",
             "images-dpi" : images_dpi,
             "thumbnail-width" : tn_width,
             "thumbnail-height": tn_height,
             "thumbnail-scaling" : (st_scaling and str(st_scaling)) or "unknown",
             "right-margin": 25,
             "show-controls-bool" : "true",
             "show-two-pages-bool" : (two_pager and "true") or "false",
             "has-text-boxes" : (has_text_boxes and "true") or "false",
             "logo-url" : "https://" + hostname + ":" + str(repo.secure_port()) + "/",
             "logo-image-url" : "/html/images/icon16.png",
             "background-color" : "%s" % STANDARD_BACKGROUND_COLOR,
             "uplib-orange-color" : "%s" % UPLIB_ORANGE_COLOR,
             "title" : title,
             "selection-start" : selection_start or "-1",
             "selection-end" : selection_end or "-1",
             "adh-mode" : (bool_test(adh_mode) and "true") or "false",
             "rsvp-mode" : (bool_test(rsvp_mode) and "true") or "false",
             "url-title" : title.replace("'", "\\'"),
             "page-numbers" : page_numbers,
             "categories" : doc.get_metadata("categories") or "",
             "use-text-for-context" : params.get("use-text-for-context"),
             "scribble-sink-url" : MODULE_PREFIX + request_context + "dv_handle_scribble?doc_id=" + doc.id,
             "scribble-source-url" : MODULE_PREFIX + request_context + "dv_get_scribbles?doc_id=" + doc.id,
             "hotspots-sink-url" : MODULE_PREFIX + request_context + "dv_handle_hotspots?doc_id=" + doc.id,
             "hotspots-source-url" : MODULE_PREFIX + request_context + "dv_get_hotspots?doc_id=" + doc.id,
             "activity-sink-url" : MODULE_PREFIX + request_context + "dv_log_activity?doc_id=" + doc.id,
             }


def _java_unicode_escape(exc):
    if (exc.end - exc.start) > 1:
        raise exc
    return (u"\\u%04d" % ord(exc.object[exc.start:exc.end])), exc.end
codecs.register_error('java_unicode_escape', _java_unicode_escape)

def dv_doc_parameters (repo, response, params):

    """This function is used by ShowDoc.jar"""

    def properties_encode (v):
        if not isinstance(v, unicode):
            v = unicode(v)
        v = v.replace('\\', '\\\\')
        return v.encode('ASCII', 'java_unicode_escape')

    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    parts = string.split(response.request_path, '/')
    if len(parts) > 1:
        request_context = string.join(parts[:-1], '/') + '/'
    else:
        request_context = ""
    note("request_context is %s", request_context)

    doc = repo.get_document(doc_id);
    conf = configurator.default_configurator()

    params_dict = _get_parameter_dict (doc, conf, params, repo, request_context)

    fp = response.open("text/plain;charset=ISO-8859-1");
    fp.write("# This is a list of key-value pairs in the text format accepted by\n")
    fp.write("# the Java 1.4.2 java.util.Properties.load() method.\n")
    fp.write("# See the documentation of that method for that format definition.\n")
    for key in params_dict:
        if not key.startswith("applet-"):
            key = properties_encode(key)
            val = properties_encode(params_dict[key])
            # write out the key value pair
            # we must replace quote backslashes, because strings of the form \uxxxx
            # are treated specially by Properties.java
            fp.write("%s: %s\n" % (key, val))
    fp.close()
    return
             

def dv_explain (repo, response, params):

    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    # explain why context is shown
    conf = configurator.default_configurator()
    if conf.get_bool("use-related-for-context-document-set", False):
        # redirect to related
        return uplib.related.related(repo, response, params)

    else:
        # explain MRU scheme
        fp = response.open()

        title = "Most recently used documents" % repr(doc.get_metadata("title") or doc.id)

        fp.write("<head><title>%s</title>\n" % htmlescape(title))
        fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
        fp.write('<link REL="SHORTCUT ICON" HREF="/favicon.ico">\n')
        fp.write('<link REL="ICON" type="image/ico" HREF="/favicon.ico">\n')
        issue_javascript_head_boilerplate(fp)
        issue_title_styles(fp)
        fp.write('</head><body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
        issue_menu_definition(fp)
        fp.write('<h2>These documents are the most recently used</h2><br>\n' % htmlescape(title))

        fp.write('<p><hr><b>Recently consulted:</b><br>')
        for related_doc in repo.history():
            show_title (fp, related_doc, None, True)

        fp.write('</body>\n')
        fp.close()

    

def generate_sidebar_html(doc, fp, conf, params_dict, request_uri, sensible_browser=True):

    CONTROLS_HEIGHT = conf.get_int('html-controls-panel-height') or 130
    THUMBNAIL_COLWIDTH = conf.get_int('html-thumbnails-column-width') or 120
    THUMBNAIL_MAXHEIGHT = conf.get_int('html-thumbnails-max-height') or 80
    viewer = params_dict.get("viewer") or "readup"

    fp.write('<table width=100% height=100%>')
    fp.write('<tr><td width=%spx valign=top>' % THUMBNAIL_COLWIDTH)

    fp.write('<table width=100% height=100% border=0>')

    ### first, write the metadata block

    fp.write('<tr><td bgcolor="white" align=left border=1>')
    fp.write('<p style="font-family: sans-serif; font-size: x-small">')

    started = false

    authors = doc.get_metadata("authors")
    if authors:
        authors = authors.split(" and ")
        fp.write('<span style="color: %s">Authors: </span>' % STANDARD_LEGEND_COLOR)
        notfirst = false
        for author in authors:
            if notfirst: fp.write('<font color="%s">, </font>' % STANDARD_DARK_COLOR)
            fp.write("<a href=\"/action/basic/repo_search?cutoff=0&query=authors:%s\" " %
                     urllib.quote_plus('"%s"~3' % htmlescape(author, true)) +
                     'style="color: %s" title="%s">%s</a>' % (STANDARD_DARK_COLOR,
                                                              htmlescape("All documents by %s" % author, true), htmlescape(author)))
            notfirst = true
        started = true
    date = doc.get_metadata("date")
    if date:
        date = format_date(date)
        if started: fp.write('<br>\n')
        fp.write('<span style="color: %s">Date: </span><span style="color: %s">%s</span>\n'
                 % (STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, date))
        started = true
    categories = doc.get_category_strings()
    if categories:
        if started: fp.write('<br>\n')
        notfirst = false
        fp.write('<span style="color: %s">Tags: </span>' % STANDARD_LEGEND_COLOR)
        for category in categories:
            if notfirst: fp.write('<font color="%s">, </font>' % STANDARD_DARK_COLOR)
            fp.write("<a href=\"/action/basic/repo_search?query=categories:%%22%s%%22&format=Icon+MRU\" " %
                     urllib.quote_plus(category) +
                     'style="color: %s" title="%s">%s</a>' % (STANDARD_DARK_COLOR,
                                                              htmlescape("All documents in category '%s'" % category, true),
                                                              htmlescape(category)))
            notfirst = true
        started = true
    format = doc.get_metadata("apparent-mime-type")
    if (not format) or (not (format.startswith("audio/") or format.startswith("video/"))):
        pages = doc.get_metadata("page-count") or doc.get_metadata("pagecount")
        if pages:
            if started: fp.write('<br>\n')
            fp.write('<span style="color: %s">Pages: </span><span style="color: %s">%s</span>\n'
                     % (STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, pages.strip()))
            started = true
    if format:
        format2 = FORMAT_NAME_MAPPING.get(format) or format
        if started: fp.write('<br>\n')
        fp.write('<span style="color: %s">Format: </span><span style="color: %s">%s</span>\n'
                 % (STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, htmlescape(format2)))
        started = true

        if format.startswith("audio/"):
            album = doc.get_metadata("album")
            if album:
                if started: fp.write('<br>\n')
                fp.write('<span style="color: %s">Album: </span><span style="color: %s">%s</span>\n'
                         % (STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, htmlescape(album)))
                started = true

    fromtag = doc.get_metadata("source")
    website = doc.get_metadata("original-url")
    if website:
        host, port, path = parse_URL(website)
        if host:
            if port and int(port) != 80:
                host = host + ":" + str(port)
            fromtag = host
    if fromtag:
        if started: fp.write('<br>\n')
        if website:
            fp.write('<span style="color: %s">From: </span><span style="color: %s"><a href="%s">%s</a></span>\n'
                     % (STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, website, htmlescape(fromtag)))
        else:
            fp.write('<span style="color: %s">From: </span><span style="color: %s">%s</span>\n'
                     % (STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, htmlescape(fromtag)))
        started = true
    added = time.strftime("%m/%d/%y %I:%M %p", time.localtime(id_to_time(doc.id)))
    if started: fp.write('<br>\n')
    fp.write('<span style="color: %s">Added: </span><span style="color: %s">%s</span>\n'
             % (STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, htmlescape(added)))

    fp.write('</p></td></tr>')

    ### provide access to alternate views

    original_url = params_dict.get("original-url")
    have_cached_copy = params_dict.get("have-cached-copy")
    data_type = params_dict.get("apparent-mime-type")

    # get clean version of uri
    uri = re.sub("&use_readup=[^&]+", "", re.sub("&live_view=[^&]+", "", re.sub("&cached_view=[^&]+", "", request_uri)))
    fp.write('<tr><td align=center border=0>')
    if (viewer != "readup"):
        with_readup = "%s&use_readup=t" % uri
        fp.write('<input type=button value="in ReadUp" onclick="javascript:window.location=\'%s\'">' % with_readup)
    if (viewer[0] != "live") and original_url and data_type in ("text/html", "text/xml", "audio/mp3", "audio/mpeg"):
        live_view = "%s&live_view=t" % uri
        fp.write('<input type=button value="Live" onclick="javascript:window.location=\'%s\'">' % live_view)
    if (viewer[0] != "cached") and have_cached_copy and data_type in ("text/html", "text/xml", "audio/mp3", "audio/mpeg"):
        cached_view = "%s&cached_view=t" % uri
        fp.write('<input type=button value="Cached" onclick="javascript:window.location=\'%s\'">' % cached_view)
    fp.write('</td></tr>')

    ### now, write the actions menu

    buttons = get_buttons_sorted(FN_DOCUMENT_SCOPE)
    show_as_menu = conf.get_bool("show-actions-menu-in-pulldown", False)
    if show_as_menu:

        fp.write('<tr><td align=center border=0>')
        fp.write('<script>\n')
        fp.write("""function perform_document_action() {
                   var selector = $("document_actions");
                   if (selector != null) {
                     var url = selector.options[selector.selectedIndex].value;
                     var target = selector.options[selector.selectedIndex].target;
                     // alert("selector value url is " + value + ", target is " + target)
                     selector.selectedIndex = 0;
                     if ((url == null) || (url.length == 0)) {
                         return;
                     }
                     if ((target == null) || (target == "_top") || (target == window.name)) {
                         window.location = url;
                     } else {
                         window.open(url, target);
                     }
                   } else {
                     alert("No selector found");
                   }
                 }
                 function zero_selector () {
                   var selector = $("document_actions");
                   selector.selectedIndex = 0;
                 }\n""")
        fp.write('</script>')
        fp.write('<select name="document_actions" id="document_actions" size=1 onchange="{perform_document_action();}">\n')
        fp.write('<option value="" selected>[Document Actions]</option>\n')
        for button in buttons:
            if button[1][5] and not button[1][5](doc):
                # don't show this button for this document
                continue
            url = button[1][4]
            target = button[1][3]
            label = button[1][0]
            if url:
                fp.write('<option value="%s"' % htmlescape(url % doc.id, true))
            else:
                fp.write('<option value="/action/basic/repo_userbutton?uplib_userbutton_key=%s&doc_id=%s"' % (button[0], doc.id))
            fp.write(' target="%s">%s</option>\n' % (target, label))
        fp.write('</select></td></tr>')

    else:

        fp.write('<tr><td bgcolor="%(bg-color)s" align=center border=1>' % params_dict)
        fp.write('<p style="font-family: sans-serif; font-size: small">')
        if viewer != "readup":
            fp.write('<a href="%s&use_readup=t">Show in ReadUp</a><br>\n' % request_uri)
        fp.write("""<a href="javascript:newInWindow('%(doc-id)s','%(url-title)s',%(applet-width)d,%(applet-height)d, false, false); void 0;">Detach</a>""" % params_dict)
        fp.write("""<a href="javascript:newInWindow('%(doc-id)s','%(url-title)s',(2 * %(page-width)d)+30,%(applet-height)d, false, true); void 0;">(2)</a>\n""" % params_dict)
        for button in buttons:
            if button[1][5] and not button[1][5](doc):
                # don't show this button for this document
                continue
            url = button[1][4]
            target = button[1][3]
            label = button[1][0]
            if url:
                fp.write('<br>\n<a href="%s"' % htmlescape(url % doc.id, true))
            else:
                fp.write('<br>\n<a href="/action/basic/repo_userbutton?uplib_userbutton_key=%s&doc_id=%s"' % (button[0], doc.id))
            if target:
                fp.write(' target="%s"' % target)
            fp.write('>%s</a>\n' % label)
        fp.write('</p></td></tr>')

    ### now, the search box

    fp.write('<tr><td align=center width="%dpx">' % THUMBNAIL_COLWIDTH +
             '<form target="_blank" action="%sdv_search" method=get name=searchrepo>' % MODULE_PREFIX)
    if show_as_menu:
        fp.write('<small><i><font color="white">Search:</font></i></small></br>')
    fp.write('<input type=text name=query></form></td></tr>\n')

    ### finally, the context documents

    otherdocs = None
    if conf.get_bool("use-related-for-context-document-set"):
        docs = uplib.related.find_related(doc)
        otherdocs = [x[0] for x in docs]

    if not otherdocs:
        otherdocs = doc.repo.history()

    # use icons, or text?
    use_text = params_dict.get("use-text-for-context")
    note("use-text-for-context is %s", params_dict.get("use-text-for-context"))
    if use_text == "true":
        use_text = True
    elif use_text is None:
        use_text = conf.get_bool("use-text-for-sidebar-context-display", False)
    else:
        use_text = False

    fp.write('<tr align=center valign=top><td align=%s>' % ((use_text and "left") or "center"))
    if show_as_menu:
        fp.write('<small><i><font color="white"><center>Context:</center></font></i></small>')
    fp.write('<div style="background-color: %s">' % ((use_text and STANDARD_BACKGROUND_COLOR) or STANDARD_LEGEND_COLOR))
    if use_text:
        fp.write('<font size="-2">')
    notherdocs = int(conf.get("pageview-other-documents-count", (use_text and 15) or 13))
    firstother = True
    for otherdoc in otherdocs[:min(notherdocs,len(otherdocs))]:
        if otherdoc.id == doc.id:
            continue    # don't put the current docs image in this list
        title = otherdoc.get_metadata('title')
        if not title:
            summary = otherdoc.get_metadata('summary')
            if summary:
                title = summary[:min(len(summary), 100)]
        if not title:
            title = otherdoc.id

        if use_text:
            if not firstother:
                fp.write('<br>')
            # output_document_title(otherdoc.id, title, fp, sensible_browser=sensible_browser)
            show_title(fp, otherdoc, None, sensible_browser, short_display=True)
        else:
            title = htmlescape(title, True)
            isize = otherdoc.icon_size()
            if isize and isize[0] and isize[1]:
                hscaling = float(isize[0])/(THUMBNAIL_COLWIDTH - 2)
                vscaling = float(isize[1])/THUMBNAIL_MAXHEIGHT
                if hscaling > vscaling:
                    iconw, iconh = int(float(isize[0])/hscaling), int(float(isize[1])/hscaling)
                else:
                    iconw, iconh = int(float(isize[0])/vscaling), int(float(isize[1])/vscaling)
            else:
                iconw, iconh = (THUMBNAIL_COLWIDTH - 2), THUMBNAIL_MAXHEIGHT
            # fp.write('<a href="dv_show?doc_id=%s" alt="%s" title="%s"><img src="/docs/%s/thumbnails/first.png" width=%s hspace=2 vspace=2 border=1></a><br>\n' % (otherdoc.id, title, title, otherdoc.id, THUMBNAIL_COLWIDTH - 2))
            output_document_icon(otherdoc.id, title, fp, sensible_browser=sensible_browser, width=iconw)
        firstother = False
    fp.write('</div>')
    m = re.search("use-text-for-context=[a-zA-Z]*", request_uri)
    if m:
        request_uri = re.sub("use-text-for-context=[a-zA-Z]*", "use-text-for-context=%s" % ((use_text and "false") or "true"), request_uri)
    else:
        request_uri += "&use-text-for-context=%s" % ((use_text and "false") or "true")
    fp.write('<center><input type=button value="%s" onclick="javascript:window.location=\'%s\';">'
             % ((use_text and "Show as icons") or "Show as text", request_uri))
    fp.write('<input type=button value="Why?" onclick="javascript:window.location=\'dv_explain?doc_id=%s\'"></center>'
             % doc.id)
    fp.write('</td></tr>')
    fp.write('</table></td>')



def dv_show (repo, response, params):

    """Display a document by sending the applet to the browser."""

    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    parts = string.split(response.request_path, '/')
    if len(parts) > 1:
        request_context = string.join(parts[:-1], '/') + '/'
    else:
        request_context = ""
    note("request_context is %s", request_context)

    note("pageview for document " + doc_id);

    doc = repo.get_document(doc_id);
    conf = configurator.default_configurator()

    use_browser_for_html = conf.get_bool("use-browser-for-web-pages", true)
    use_browser_for_audio = conf.get_bool("use-browser-for-audio", true)
    use_browser_for_images = conf.get_bool("use-browser-for-images", true)

    viewer = "readup"
    data_type = doc.get_metadata("apparent-mime-type")
    original_url = doc.get_metadata("original-url")
    pages = int(doc.get_metadata("page-count") or doc.get_metadata("pagecount") or 1)
    if data_type and not params.has_key("use_readup") and os.path.exists(doc.originals_path()):
        # consider using the browser rather than the "readup" applet
        original_files = os.listdir(doc.originals_path())
        if use_browser_for_html and data_type == "text/html":
            # look for original.html and use it if possible
#             if (params.get("live_view") == "t") and original_url:
#                 viewer = ("live", '<object type="text/html" width="100%" height="100%" id="viewtarget"' +
#                           ' style="background-color: white;" ' +
#                           'data="%s"></object>' % original_url)
#             elif os.path.exists(os.path.join(doc.originals_path(), "original.html")):
#                 viewer = ("cached", '<object type="text/html" width="100%" height="100%" id="viewtarget"' +
#                           ' style="background-color: white;" ' +
#                           'data="/action/externalAPI/fetch_original?doc_id=%s&browser=true"></object>' % doc.id)
            if (params.get("live_view") == "t") and original_url:
                viewer = ("live", '<iframe type="text/html" width="100%" height="100%" id="top"' +
                          ' style="background-color: white;" ' +
                          'src="%s"></object>' % original_url)
            elif os.path.exists(os.path.join(doc.originals_path(), "original.html")):
                viewer = ("cached", '<iframe type="text/html" width="100%" height="100%" id="top"' +
                          ' style="background-color: white;" ' +
                          'src="/action/externalAPI/fetch_original?doc_id=%s&browser=true"></object>' % doc.id)
        elif use_browser_for_images and data_type.startswith("image/") and (pages < 2):
            data_uri = "/docs/%s/thumbnails/big1.png" % doc.id
            size = eval('(' + doc.get_metadata("big-thumbnail-size") + ')')
            data_type = "image/png"
            viewer = ("cached",
                      '<object width=%s height=%s type="%s" data="%s" ' % (size[0], size[1], data_type, data_uri) +
                      '<param name="src" value="%s"></object>' % data_uri)
        elif use_browser_for_audio and data_type.startswith("audio/"):
            icon_size = doc.icon_size()
            data_uri = "/action/externalAPI/fetch_original?doc_id=%s&browser=true" % doc.id
            background_uri = "/docs/%s/thumbnails/first.png" % doc.id
            viewer = ("cached",
                      '<object width=%s height=%s type="%s" data="%s" ' % (2*icon_size[0], 2*icon_size[1], data_type, data_uri) +
                      'style="background-image: url(\'%s\');">' % background_uri +
                      '<param name="src" value="%s"></object>' % data_uri)

    jarfile_path = os.path.join(os.path.dirname(repo.docs_folder()), "html", "UpLibPageview.jar")
    if not (os.path.exists(jarfile_path)):
	import filecmp, shutil
        real_jarfile_path = os.path.join(conf.get('uplib-code'), 'UpLibPageview.jar')
        if not os.path.exists(real_jarfile_path):
            response.error(HTTPCodes.SERVICE_UNAVAILABLE, "No UpLibPageview.jar codefile is installed in this UpLib installation.")
            return
	if hasattr(os, 'symlink'):
            if os.path.islink(jarfile_path):
                os.unlink(jarfile_path)
	    os.symlink(real_jarfile_path, jarfile_path)
	elif (not os.path.exists(jarfile_path)) or (not filecmp.cmp(real_jarfile_path, jarfile_path)):
	    shutil.copyfile(real_jarfile_path, jarfile_path)

    params_dict = _get_parameter_dict (doc, conf, params, repo, request_context)
    params_dict["viewer"] = viewer
    params_dict["apparent-mime-type"] = data_type
    params_dict["original-url"] = original_url
    params_dict["have-cached-copy"] = os.path.exists(doc.originals_path())

    centered = params.get('centered', 0)
    new_window = params.get("new-window")
    no_sidebar = params.get("no-sidebar")
    no_margin = params.get("no-margin")
    two_pager = params.get("two-pages")

    fp = response.open();

    fp.write('<html><head><title>%s</title>\n' % params_dict["applet-title"])

    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    issue_javascript_head_boilerplate(fp)
    if no_margin:
        fp.write('<style type="text/css">\nbody {margin:0}\n</style>\n')
    fp.write('<script language="javascript">\n')
    fp.write('function newInWindow(did, title, w, h, sidebar, twopage) {\n')
    fp.write('  var s = "%sdv_show?doc_id=" + did + "&no-margin=1";\n' % MODULE_PREFIX)
    fp.write('  var c = "width=" + w + ",height=" + h;\n')
    fp.write('  if (!sidebar)\n')
    fp.write('    s = s + "&no-sidebar=1";\n')
    fp.write('  if (twopage)\n')
    fp.write('    s = s + "&two-pages=1";\n')
    fp.write('  defaultStatus = s;\n')
    fp.write('  window.open(s, title, config=c);\n')
    fp.write('}\n')
    fp.write('</script></head><body bgcolor="%s">\n' % STANDARD_LEGEND_COLOR)
    issue_menu_definition(fp);
    issue_title_styles(fp)
    if (new_window):
        fp.write('<script language="javascript">(void)newInWindow("%s", "%s", %d + 20, %d + 20, %s, false);</script></body></html>' %
                 (doc_id, params_dict["applet-title"], params_dict["applet-width"], params_dict["applet-height"],
                  (no_sidebar and "true") or "false"))
        return

    if not no_sidebar:
        generate_sidebar_html(doc, fp, conf, params_dict, response.request.uri)
        fp.write('<td align=left valign=top>')

    if centered:
        fp.write('<table width=100% height=100%><tr align=center><td align=center>')

    if viewer == "readup":

        note("sending pageviewer")
        htmlslug = extended_applet % params_dict
        fp.write(htmlslug)

    elif isinstance(viewer, tuple) and viewer[0] == "cached":

        note("sending viewer '%s'..." % viewer[1])
        fp.write(viewer[1])

    elif isinstance(viewer, tuple) and viewer[0] == "live":

        note("sending viewer '%s'..." % viewer[1])
        fp.write(viewer[1])

    if centered:
        fp.write('</td></tr></table>')
    if not no_sidebar:
        fp.write('</td></tr></table>')
    fp.write('</body></html>\n')
    repo.touch_doc(doc)
    return


def dv_search (repo, response, form):

    """Search for a document.  If only one is found, show it.  Otherwise, put up normal display
    of results."""

    from uplib.collection import QueryCollection

    from uplib.basicPlugins import TEMPORARY_COLLECTIONS, SEARCH_RESULTS_FORMAT, _compare_docs_by_score, repo_show_thumbnails, repo_show_titles, repo_show_abstracts
    import traceback

    try:
        query = form.get('query')
        if not query:
            response.reply("No query specified.")
            return

        coll = QueryCollection(repo, None, query)
        TEMPORARY_COLLECTIONS[coll.id] = coll

        name = query
        title = 'Search \'%s\'' % name

        docs = coll.docs()

        if len(docs) == 1:
            dv_show (repo, response, {"doc_id" : docs[0].id})
            return

        scores = coll.xscores
        docs.sort(lambda x, y, z=scores: _compare_docs_by_score(x, y, z))

        if (SEARCH_RESULTS_FORMAT.endswith(' DP') or SEARCH_RESULTS_FORMAT.endswith(' DA')):
            repo_show_timescale(repo, SEARCH_RESULTS_FORMAT, response, None, coll, docs, name, title, scores)
        elif SEARCH_RESULTS_FORMAT.startswith('Thumbnails') or SEARCH_RESULTS_FORMAT.startswith('Icon'):
            repo_show_thumbnails(repo, SEARCH_RESULTS_FORMAT, response, None, coll, docs, name, title, scores)
        elif SEARCH_RESULTS_FORMAT.startswith('Title'):
            repo_show_titles(repo, SEARCH_RESULTS_FORMAT, response, None, coll, docs, name, title, scores)
        else:
            repo_show_abstracts(repo, SEARCH_RESULTS_FORMAT, response, None, coll, docs, name, title, scores)

    except Error, x:
        fp = response.open("text/plain")
        fp.write('The application signalled the following error:\n')
        fp.write(str(x) + '\n')
        fp.close()

    except:
        fp = response.open("text/plain")
        fp.write('The application signalled the following error:\n')
        traceback.print_exc(None, fp)
        fp.close()



class Hotspot:
    def __init__(self, doc_id, page_no, x, y, width, height, url, description, color=None, icon=None, icon_location=None, link_id=None, intrinsic=true, dest_rect=true):
        self.doc_id = doc_id
        self.link_id = link_id
        self.page_no = page_no
        self.x = x;
        self.y = y
        self.width = width;
        self.height = height
        self.url = url
        self.description = description
        self.color = color
        self.icon = icon
        self.icon_location = icon_location
        self.dest_rect = None
        self.intrinsic = intrinsic

    def encode(self, version=1):
        if version == 2:
            base = "%s %s %d %d %d %d %d " % (
                self.link_id, self.doc_id, self.page_no, self.x, self.y, self.width, self.height)
            base += (self.intrinsic and "true ") or "false "
            if self.color:
                base += "%f:%f:%f" % self.color
            else:
                base += "nocolor"
            description = string.join(base64.encodestring(self.description).split(), "")
            if self.url and self.url.startswith("/"):
                url = "https://-uplib-" + self.url
            else:
                url = self.url
            base += " %s\n%s\n" % (re.sub(' ', '+', url), description)
            if not self.icon:
                base += "noicon\n"
            else:
                if self.icon_location:
                    base += "%d %d " % self.icon_location
                else:
                    base += "0 0 "
                iconvalue = string.join(self.icon.get_writeable_form().split(), "")
                base += (iconvalue + "\n")
        elif version == 1:
            base = "%s %d %d %d %d %d %s\n%s\n" % (
                self.doc_id, self.page_no, self.x, self.y, self.width, self.height,
                re.sub(' ', '+', self.url), self.description)
        else:
            raise ValueError("hotspot protocol version \"%s\" specified, only versions 1 and 2 supported" % version)
        # note("encoded hotspot is <%s>", base)
        return base

    def write(self, fp, version=1):
        encoded_form = self.encode(version)
        fp.write(encoded_form)
        # note("wrote %s to %s", encoded_form, fp)

    def decode(data, version=1):
        note(4, "link data is <<%s>>", data)
        try:
            if (version == 1):
                lines = string.split(data, '\n')
                doc_id, page_no, x, y, width, height, url = string.split(lines[0])
                description = string.strip(lines[1])
                return Hotspot(doc_id, int(page_no), int(x), int(y), int(width), int(height), url, description)
            elif (version == 2):
                lines = string.split(data, '\n')
                link_id, doc_id, page_no, x, y, width, height, intrinsic, color, url = string.split(lines[0])
                if color == "nocolor":
                    color = None
                description = base64.decodestring(lines[1])
                if lines[2].startswith('noicon'):
                    icon = None
                    icon_x = 0
                    icon_y = 0
                else:
                    icon_x, icon_y, icon_data = string.split(lines[2])
                    icon = LinkIcon.find_icon(data=icon_data)
                    # note("LinkIcon.find_icon returns %s", icon)
                to_rect = {}
                for key in ("left", "top", "width", "height"):
                    m = re.search("&" + key + "=([-0-9\.]+)", url)
                    if m:
                        to_rect[key] = float(m.groups(1))
                return Hotspot(doc_id, int(page_no), int(x), int(y), int(width), int(height), url, description, color, icon, (icon_x, icon_y), link_id, intrinsic == "true", dest_rect=to_rect)
            else:
                raise Error("unknown hotspot wire format specified:  %s" % version)
        except Exception, x:
            show_exception()
            raise Error("invalid Hotspot format: " + str(x))

    decode = staticmethod(decode)
        
    def from_link(l):

        def scale_point (xlation, scaling, x, y):
            trunc = int
            x = trunc((x + xlation[0]) * scaling[0] + 0.5)
            y = trunc((y + xlation[1]) * scaling[1] + 0.5)
            return x, y

        def scale_size (scaling, width, height):
            # conversion from float to int via "int()" truncates, so define it as "trunc"
            trunc = int
            width = trunc(width * scaling[0] + 0.5)
            height = trunc(height * scaling[1] + 0.5)
            return width, height

        def scale_rect (xlation, scaling, left, top, width, height):
            # conversion from float to int via "int()" truncates, so define it as "trunc"
            left, top = scale_point(xlation, scaling, left, top)
            width, height = scale_size(scaling, width, height)
            return left, top, width, height

        if l.typename not in ("uri", "goto", "gotor"):
            return None

        if l.typename == "goto" and hasattr(l, "to_page"):
            to_uri = '#uplibpage=%d' % int(l.to_page)
            description = l.get_title() or ("turn to page %s" % l.from_doc.page_index_to_page_number_string(int(l.to_page)))
        elif (l.typename == "gotor") and hasattr(l, "to_doc"):
            d2 = getattr(l, "to_doc")
            to_uri = "https://-uplib-/action/basic/dv_show?doc_id=%s" % d2.id
            if hasattr(l, "to_page"):
                to_uri += "&page=%s" % getattr(l, "to_page")
                if hasattr(l, "to_span"):
                    to_uri += "&selection-start=%s&selection-end=%s" % getattr(l, "to_span")
                elif hasattr(l, "to_rect"):
                    translation, scaling = d2.thumbnail_translation_and_scaling()
                    if (translation is not None) and (scaling is not None):
                        left, top, width, height = scale_rect(translation, scaling, *getattr(l, "to_rect"))
                    to_uri += "&selection-rect=%.2f,%.2f,%.2f,%.2f" % (left, top, width, height)
            description = l.get_title() or d2.get_metadata("summary") or d2.get_metadata("title")
        elif hasattr(l, "to_uri"):
            to_uri = l.get_uri()
            description = l.get_title() or to_uri
        else:
            return None
        if not to_uri:
            return None

        translation, scaling = l.from_doc.thumbnail_translation_and_scaling()
        if translation is None or scaling is None:
            note(2, "    couldn't obtain translation or scaling for %s", l.from_doc)
            return None

        def get_attr(obj, aname):
            if hasattr(obj, aname):
                return getattr(obj, aname)
            else:
                return None

        from_page = int(l.from_page)
        if l.from_span:
            # span link
            left, top = l.from_span
            width = height = -1
        else:
            # rect link
            left, top, width, height = scale_rect(translation, scaling, *l.from_rect)

        iloc = get_attr(l, "icon_location")
        if iloc:
            # this is relative to the upper left corner of the link, so it's
            # really a "size" (no translation), not a "point"
            lwidth, lheight = scale_size (scaling, *iloc)
            iloc = (lwidth, lheight)
        return Hotspot(l.from_doc.id, from_page, left, top, width, height, to_uri, description,
                       l.get_highlight_color(), l.get_icon(), iloc, l.id, l.permanent())

    from_link = staticmethod(from_link)

    def to_link(self, doc):

        if doc.id != self.doc_id:
            raise ValueError('invalid doc_id %s for link; expecting %s' % (self.doc_id, doc.id))

        lfields = {}
        lfields['id'] = self.link_id
        lfields['title'] = self.description
        lfields['from-page'] = self.page_no

        translation, scaling = doc.thumbnail_translation_and_scaling()
        if translation is None or scaling is None:
            note(2, "    couldn't obtain translation or scaling for %s", doc)
            return None

        def unscale_dimension (width, height):
            width = (float(width) / scaling[0])
            height = (float(height) / scaling[1])
            return width, height

        def unscale_rect (left, top, width, height):
            left = (float(left) / scaling[0]) - translation[0]
            top = (float(top) / scaling[1]) - translation[1]
            width, height = unscale_dimension(width, height)
            return left, top, width, height

        if (self.width < 0) or (self.height < 0):
            # span anchor
            lfields['from-span'] = '%d,%d' % (self.x, self.y)
        else:
            # rect anchor
            left, top, width, height = unscale_rect(self.x, self.y, self.width, self.height)
            lfields['from-rect'] = "%f,%f,%f,%f" % (left, top, width, height)

        if self.icon_location and self.icon:
            ileft, itop = unscale_dimension(*self.icon_location)
            lfields['from-icon-location'] = "%f,%f" % (ileft, itop)
            lfields['from-icon'] = self.icon

        m = re.match(r'#uplibpage=(\d+)', self.url)
        if m:
            lfields['to-page'] = int(m.group(1)) + 1
        else:
            lfields['to-uri'] = self.url
        if self.dest_rect:
            lfields['to-rect'] = "%f,%f,%f,%f" % (self.dest_rect['left'],
                                                  self.dest_rect['top'],
                                                  self.dest_rect['width'],
                                                  self.dest_rect['height'])
        if self.description != self.url:
            lfields['title'] = self.description

        note(4, "link-fields are %s", lfields)

        return Link(doc, lfields)

    def read(fp):
        # note ("file is %s", fp)
        try:
            line = fp.readline()
            #note("first line is %s", line)
            while len(line) > 0 and (line[0] == '#'):
                line = fp.readline()
            if len(line) < 1:
                return None
            #note("line is %s", line)
            doc_id, page_no, x, y, width, height, url = string.split(line)
            #note("doc_id is %s, page_no is %s, x is %s, y is %s, width is %s, height is %s, url is %s",
            #     doc_id, page_no, x, y, width, height, url)
            description = string.strip(fp.readline())
            return Hotspot(None, doc_id, int(page_no), int(x), int(y), int(width), int(height), url, description)
        except Exception, x:
            show_exception()
            raise Error("invalid Hotspot format:  " + str(x))

    read = staticmethod(read)


def _read_hotspots_file(doc):
    hotspots_path = os.path.join(doc.folder(), "hotspots.txt")
    hotspots = []
    if (os.path.exists(hotspots_path)):
        fp = open(hotspots_path, 'r')
        try:
            while true:
                try:
                    s = Hotspot.read(fp)
                    #note("read hotspot %s", s)
                    if s == None:
                        break
                    hotspots.append(s)
                except:
                    break
        finally:
            fp.close()
    return hotspots

def old_dv_get_hotspots (repo, response, params):

    """Send any hotspots associated with the document to the client."""

    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    doc = repo.get_document(doc_id);
    hotspots = _read_hotspots_file (doc)
    note("%d hotspots read from hotspots file", len(hotspots))
    fp = response.open("application/x-uplib-hotspots")
    fp.write("1\n%d\n" % len(hotspots))
    for s in hotspots:
        s.write(fp)
    fp.close()
    return


def dv_get_hotspots (repo, response, params):

    """Send any hotspots associated with the document to the client."""

    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    doc = repo.get_document(doc_id);
    doclinks = doc.links().values()
    protocol_version = (USE_VERSION_2_HOTSPOT_PROTOCOL and 2) or 1
    note(3, "sending %d hotspots using protocol version %d", len(doclinks), protocol_version)

    fp = response.open("application/x-uplib-hotspots")
    fp.write("%d\n%d\n" % (protocol_version, len(doclinks)))
    for l in doclinks:
        s = Hotspot.from_link(l)
        if s:
            s.write(fp, protocol_version)
        else:
            note(3, "No hotspot for link %s of type %s, to_doc %s", l, repr(l.typename), getattr(l, "to_doc"))
    fp.close()
    return


def dv_handle_hotspots (repo, response, params):

    """Process additional annotations sent back from the client."""

    content_type = response.request.get_header('content-type')
    if content_type != "application/x-uplib-hotspots":
        note("dv_handle_hotspots:  bad content-type %s", content_type)
        response.error(HTTPCodes.BAD_REQUEST, "Invalid content-type " + content_type);
        return

    if not response.content:
        note("dv_handle_hotspots:  empty content")
        response.error(HTTPCodes.BAD_REQUEST, "No data in message")
        return

    if hasattr(response.content, "seek"):
        response.content.seek(0, 0)

    version = int(response.content.readline());
    if version != 2:
        note("handle_hotspots:  invalid protocol version %d" % version)
        if hasattr(response.content, "seek"):
            response.content.seek(0, 0)
        note("handle_hotspots:  whole content is<\n%s>", response.content.read());
        response.error(HTTPCodes.BAD_REQUEST, "Can't understand protocol version " + str(version))
        return

    count = int(response.content.readline())

    if sys.version_info < (2, 6):
        import sets
        docs_mentioned = sets.Set()
    else:
        docs_mentioned = set()

    try:
        lines = response.content.readlines()
        if (len(lines) % 3)!= 0:
            note("dv_handle_hotspots:  read %d lines of data -- not divisible by 3", len(lines))
            note("bad content is <\n%s>", lines)
            response.error(HTTPCodes.BAD_REQUEST, "can't understand data -- wrong number of data lines")
        if (count > 0) and (len(lines) / 3) != count:
            note("dv_handle_hotspots:  data for %d hotspots -- header count says to expect %d", len(lines)/3, count)
            note("bad content is <\n%s>", lines)
            response.error(HTTPCodes.BAD_REQUEST, "can't understand data -- bad header count")
            
        for init_line in range(0,len(lines),3):
            hs = Hotspot.decode(''.join(lines[init_line:init_line+3]), 2)
            if not hs:
                note("Null hotspot decoded from <<%s>>", string.join(lines[init_line:init_line+3], '\n'))
                response.error(HTTPCodes.BAD_REQUEST, "can't understand data")
                return
            doc_id = hs.doc_id
            if not repo.valid_doc_id(doc_id):
                note("Invalid doc_id %s specified in hotspot <<%s>>", doc_id, string.join(lines[init_line:init_line+3], '\n'))
                response.error(HTTPCodes.BAD_REQUEST, "invalid doc_id %s specified" % doc_id)
                return
            doc = repo.get_document(doc_id)
            newlink = hs.to_link(doc)
            plink = doc.links().get(newlink.id)
            if plink:
                # hotspot to link conversion not round-trip, so don't update existing links
                # from hotspots -- though we might update positions, maybe titles, maybe icons
                if newlink.off_page():
                    note(3, "deleting link %s", plink)
                    doc.remove_link(plink)
                else:
                    loc = newlink.get_bounds()
                    note(3, "moving link %s to %s", plink, loc)
                    plink.set_bounds(loc)
            else:
                doc.add_link(newlink)
            docs_mentioned.add(doc)

        for doc in docs_mentioned:
            doc.save_links()

    except:
        note("dv_handle_hotspots:  exception")
        show_exception()


def dv_get_scribbles (repo, response, params):

    """Return the annotations associated with a document."""

    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    doc = repo.get_document(doc_id);
    annotations_filepath = os.path.join(doc.folder(), "annotations");
    data = None
    if (os.path.isdir(annotations_filepath)):
        lock_folder(doc.folder())
        try:
            scribbles_filepath = os.path.join(annotations_filepath, "scribbles")
            if (os.path.exists(scribbles_filepath)):
                fp = open(scribbles_filepath, 'rb')
                data = fp.read()
                fp.close();
        finally:
            unlock_folder(doc.folder());
    elif (os.path.exists(annotations_filepath)):
        lock_folder(doc.folder())
        try:
            fp = open(annotations_filepath, 'rb')
            data = fp.read()
            fp.close();
        finally:
            unlock_folder(doc.folder());
    fp = response.open("application/x-uplib-annotations")
    fp.write("1\n%s\n" % doc_id);
    if data:
        fp.write(data)
    fp.close()
    return

def add_annotations_to_folder (annotations, folder, lockit=True):
    if lockit:
        lock_folder(folder)
    try:
        annotation_file = os.path.join(folder, "annotations")
        scribbles_filepath = os.path.join(annotation_file, "scribbles")
        if (os.path.exists(annotation_file)):
            if os.path.isdir(annotation_file):
                if os.path.exists(scribbles_filepath):
                    fp = open(scribbles_filepath, 'ab')
                else:
                    fp = open(scribbles_filepath, 'wb', 0700)
            else:
                tmpfilename = tempfile.mktemp()
                shutil.move(annotation_file, tmpfilename)
                os.mkdir(annotation_file, 0700)
                shutil.move(tmpfilename, scribbles_filepath)
                fp = open(scribbles_filepath, 'ab')
        else:
            os.mkdir(annotation_file, 0700)
            fp = open(scribbles_filepath, 'wb', 0700)
        fp.write(annotations)
        fp.close()
    finally:
        if lockit:
            unlock_folder(folder)

def _add_annotations (doc, annotations):
    add_annotations_to_folder(annotations, doc.folder())

def dv_fetch_note (repo, response, params):

    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return
    doc = repo.get_document(doc_id);

    pageparam = params.get('page')
    if not pageparam:
        response.error(HTTPCodes.BAD_REQUEST, "No page specified.")
        return
    page = int(pageparam)
    pages = doc.get_metadata("page-count")
    if (pages <= page) or (page < 0):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid page parameter " + pageparam + " specified.")
        return

    noteparam = params.get('note')
    if not noteparam:
        response.error(HTTPCodes.BAD_REQUEST, "No note specified.")
        return
    notenumber = int(noteparam)

    if notenumber == 0:
        filename = os.path.join(doc.folder(), "annotations", "notes", str(page), "layout")
    else:
        filename = os.path.join(doc.folder(), "annotations", "notes", str(page), str(notenumber))

    lock_folder(doc.folder())
    try:
        if os.path.exists(filename):
            data = open(filename, 'rb').read()
            fp = response.open("application/x-uplib-notes")
            fp.write("1\n%s\n" % doc_id);
            if (notenumber == 0):
                format, type, count = struct.unpack(">BBH", data[:4])
                fp.write(struct.pack(">HHH", page & 0xFFFF, notenumber & 0xFFFF, count & 0xFFFF))
                fp.write(data)
            else:
                # check for old note data, and convert it
                if struct.unpack(">B", data[0])[0] != 0xFF:
                    page_no, note_no, record_count = struct.unpack(">HHH", data[:6])
                    header = struct.pack(">BBHHHH", 0xFF, 0, page_no & 0xFFFF, note_no & 0xFFFF, record_count & 0xFFFF, 0)
                    data = header + data[6:]
                fp.write(data)
            fp.write("\n")
            fp.close()
        else:
            response.error(HTTPCodes.NOT_FOUND, "<pre>" + filename + "</pre>")
    finally:
        unlock_folder(doc.folder())


ANCHOR_TYPE_SPAN = 1
ANCHOR_TYPE_RECT = 2
ANCHOR_TYPE_PARAGRAPH = 3

def _read_note_data (input_stream, doc_id):
    note_data = ""
    header = input_stream.read(6)
    note_version = struct.unpack(">B", header[:1])[0]
    note("  header is %s, note_version is %s, note_version < 0xFF is %s",
         repr(header), note_version, note_version < 0xFF)
    if note_version < 0xFF:
        # old style note -- convert it
        note_version = 0
        anchor_type = 0
        anchor_length = 0
        page_no, note_no, record_count = struct.unpack(">HHH", header)
        note("  old style note, version is %s, page %d, note %d, %d subrecords", note_version,
             page_no, note_no, record_count)
        header = struct.pack(">BBHHHH", 0xFF, anchor_type & 0xFF, page_no & 0xFFFF, note_no & 0xFFFF,
                             record_count & 0xFFFF, anchor_length & 0xFFFF)
    else:
        header += input_stream.read(4)
        note_version, anchor_type, page_no, note_no, record_count, anchor_length = struct.unpack(">BBHHHH", header)
        note("  new style note, version is %s, page %d, note %d, %d subrecords, anchor type %d (%d)", note_version,
             page_no, note_no, record_count, anchor_type, anchor_length)
    anchor_data = ""
    if note_no > 0:
        note_data += header
        if anchor_length > 0:
            anchor_data = input_stream.read(anchor_length)
            note_data += anchor_data
        for counter in range(record_count):
            header = input_stream.read(6)
            note("  subrecord header for %d/%d/%d is %s", page_no, note_no, counter, repr(header))
            if len(header) != 6:
                raise ValueError("bad subrecord header %s; note_data so far is %s", repr(header), repr(note_data))
            length, format, type = struct.unpack(">IBB", header)
            note_data += header
            data = input_stream.read(length - 6)
            if len(data) != (length - 6):
                raise ValueError("bad note subrecord data %s, should be %d bytes; note_data so far is %s"
                                 % (repr(data), length - 6, repr(note_data)))
            note_data += data
    else:
        # layout info
        header = input_stream.read(4)
        if len(header) != 4:
            raise ValueError("bad layout record header %s (should be 4 bytes); notedata so far is %s"
                             % (repr(header), repr(notedata)))
        format, type, record_count = struct.unpack(">BBH", header)
        note_data += header
        while (record_count > 0):
            header = input_stream.read(4)
            if len(header) != 4:
                raise ValueError("bad layout subrecord %d/%d header %s; notedata so far is %s"
                                 % (page_no, record_count, repr(header), repr(notedata)))
            rlength = struct.unpack(">H", header[2:])[0]
            data = input_stream.read(rlength - 4)
            note_data += (header + data)
            record_count -= 1

    # read newline at end of data
    input_stream.read(1);

    return (doc_id, page_no, note_no, anchor_type, anchor_data, note_data)


def _store_note_file (filepath, bits):
    if os.path.exists(filepath):
        # move previous version out of the way
        shutil.move(filepath, filepath + "-%.4f" % time.time())
    fp = open(filepath, 'wb', 0600)
    fp.write(bits)
    fp.close()

def store_note_data_for_folder (data, folder):
    doc_id, page_no, note_no, anchor_type, anchor_data, note_bits = data
    lock_folder(folder)
    try:
        annotation_file = os.path.join(folder, "annotations")
        notes_directory = os.path.join(annotation_file, "notes")
        page_directory = os.path.join(notes_directory, str(page_no))
        note_file = os.path.join(page_directory, str(note_no))
        if (os.path.exists(annotation_file)):
            if not os.path.isdir(annotation_file):
                tmpfilename = tempfile.mktemp()
                shutil.move(annotation_file, tmpfilename)
                os.mkdir(annotation_file, 0700)
                shutil.move(tmpfilename, os.path.join(annotation_file, "scribbles"))
        else:
            os.mkdir(annotation_file, 0700)
        if not os.path.exists(notes_directory):
            os.mkdir(notes_directory, 0700)
        if not os.path.exists(page_directory):
            os.mkdir(page_directory, 0700)
        if note_no == 0:
            # information on page layout
            # first, clean up old pages that shouldn't be here anymore
            pointer = 4
            valid_note_records = []
            valid_note_numbers = []
            good_note_bits = note_bits[:2]
            record_count = struct.unpack(">H", note_bits[2:4])[0]
            while (record_count > 0):
                format, rtype, rlength = struct.unpack(">BBH", note_bits[pointer:pointer+4])
                if (format == 0) and (rtype == 0):
                    # standard record
                    record = note_bits[pointer:pointer+rlength]
                    nnumber, nx, ny, nwidth, nheight, nstacking, ncolor = struct.unpack(">HhhHHHI", record[4:])
                    if ((ny + nheight) > 0):
                        valid_note_numbers.append(nnumber)
                        valid_note_records.append(record)
                pointer += rlength
                record_count -= 1
            note_bits = note_bits[:2] + struct.pack(">H", len(valid_note_records) & 0xFFFF) + string.join(valid_note_records, '')
            files = os.listdir(page_directory)
            for file in files:
                if re.match("^[0-9]+$", file):
                    if not int(file) in valid_note_numbers:
                        # move the file out of the way
                        shutil.move(os.path.join(page_directory, file), os.path.join(page_directory, file + "-%.4f" % time.time()))
            note_file = os.path.join(page_directory, "layout")

        _store_note_file (note_file, note_bits)

        # for debugging
        if sys.platform != 'win32':
            if note_no == 0:
                fp = open("/tmp/layout", "wb")
            else:
                fp = open("/tmp/notedata2", "wb")
            fp.write(note_bits)
            fp.close()

    finally:
        unlock_folder(folder)

def _store_note_data (data, doc):
    store_note_data_for_folder(data, doc.folder())


def dv_handle_notes (repo, response, params):

    """Process additional annotations sent back from the client."""

    content_type = response.request.get_header('content-type')
    if content_type != "application/x-uplib-notes":
        note("handle_notes:  bad content-type %s", content_type)
        response.error(HTTPCodes.BAD_REQUEST, "Invalid content-type " + content_type);
        return

    if not response.content:
        note("handle_notes:  empty content")
        response.error(HTTPCodes.BAD_REQUEST, "No scribbles in message")
        return

    if hasattr(response.content, "seek"):
        response.content.seek(0, 0)

    try:
        version = int(response.content.readline());
    except:
        version = 0
        
    if version != 1:
        note("handle_notes:  invalid protocol version %d" % version)
        if hasattr(response.content, "seek"):
            response.content.seek(0, 0)
        note("handle_notes:  whole content is<\n%s>", response.content.read());
        response.error(HTTPCodes.BAD_REQUEST, "Can't understand protocol version " + str(version))
        return

    docs = []
    try:

        while (True):

            doc_id = response.content.readline()
            if not doc_id:
                response.reply("");
                return

            doc_id = doc_id[:-1]

            if not repo.valid_doc_id(doc_id):
                note("handle_notes:  invalid doc_id %s", repr(doc_id))
                response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
                return

            data = _read_note_data(response.content, doc_id)
            if not data:
                note("handle_notes:  no note data for doc ID %s", doc_id)
                response.error(HTTPCodes.BAD_REQUEST, "Invalid note data for " + doc_id + " specified.")
                return
            try:
                doc = repo.get_document(doc_id)
                _store_note_data (data, doc)
                docs.append(doc)
            except:
                type, value, tb = sys.exc_info()
                s = string.join(traceback.format_exception(type, value, tb))
                note("handle_notes:  exception storing data:  " + s)
                response.error(HTTPCodes.BAD_REQUEST, "Can't store note data for " + doc_id);
                return
    finally:
        if docs:
            repo.reindex(docs)

def _show_scribble (s):
    """given the bytes of a scribble, display it to stderr"""

    length, format, anno_type = struct.unpack(">HBB", s[:4])
    if (anno_type == ANNO_TYPE_ERASURE) or (anno_type == ANNO_TYPE_SCRIBBLE):
        pageno, timestamp, red, green, blue, alpha, thickness, npoints = struct.unpack(">HQBBBBBB", s[4:20])
    elif (anno_type == ANNO_TYPE_VSCRIBBLE):
        pageno, timestamp, red, green, blue, alpha, npoints = struct.unpack(">HQBBBBH", s[4:20])
        thickness = 0
    thickness = thickness/8.0
    timestamp = time.localtime(timestamp/1000)
    if (format == 0) and ((anno_type == ANNO_TYPE_SCRIBBLE) or (anno_type == ANNO_TYPE_ERASURE)):
        note("%s %s (%d,%d,%d,%d)  %.1f  (%d points)  (%d bytes)",
             ((anno_type == ANNO_TYPE_ERASURE) and "erasure") or "scribble",
             time.strftime("%m/%d/%y %H:%M:%S", timestamp),
             red, green, blue, alpha, thickness, npoints, length)
        os = ""
        for b in s:
            os += ("%02x " % ord(b))
        note("  %s", os)
        if (npoints * 4) != (len(s) - 20):
            note("  *** above scribble has %d bytes, should have %d bytes", len(s), 20 + (npoints * 4))
        if (len(s) != length):
            note("  *** above scribble has %d bytes, says it has %d bytes", len(s), length)
    elif (format == 0) and (anno_type == ANNO_TYPE_VSCRIBBLE):
        note("%s %s (%d,%d,%d,%d)  (%d points)  (%d bytes)",
             ((anno_type == ANNO_TYPE_ERASURE) and "erasure") or "scribble",
             time.strftime("%m/%d/%y %H:%M:%S", timestamp),
             red, green, blue, alpha, npoints, length)
        os = ""
        for b in s:
            os += ("%02x " % ord(b))
        note("  %s", os)
        if (npoints * 10) != (len(s) - 20):
            note("  *** above scribble has %d bytes, should have %d bytes", len(s), 20 + (npoints * 10))
        if (len(s) != length):
            note("  *** above scribble has %d bytes, says it has %d bytes", len(s), length)


def dv_handle_scribble (repo, response, params):

    """Process additional annotations sent back from the client."""

    content_type = response.request.get_header('content-type')
    if content_type != "application/x-uplib-annotations":
        note("handle_scribble:  bad content-type %s", content_type)
        response.error(HTTPCodes.BAD_REQUEST, "Invalid content-type " + content_type);
        return

    if not response.content:
        note("handle_scribble:  empty content")
        response.error(HTTPCodes.BAD_REQUEST, "No scribbles in message")
        return

    if hasattr(response.content, "seek"):
        response.content.seek(0, 0)

    version = int(response.content.readline());
    if version != 1:
        note("handle_scribble:  invalid protocol version %d" % version)
        if hasattr(response.content, "seek"):
            response.content.seek(0, 0)
        note("handle_scribble:  whole content is<\n%s>", response.content.read());
        response.error(HTTPCodes.BAD_REQUEST, "Can't understand protocol version " + str(version))
        return

    doc_id = response.content.readline()[:-1]

    if not doc_id:
        note("handle_scribble:  no doc_id")
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        note("handle_scribble:  invalid doc_id")
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    try:
        doc = repo.get_document(doc_id);
        annotations = ""
        data = response.content.read()
        i = 0
        while ((i + 4) <= len(data)):
            annotation_length = ((ord(data[i]) << 8) + ord(data[i+1]))
            if (i + annotation_length) > len(data):
                raise Error("Invalid annotation record encountered (length %d)" % annotation_length)
            annotation_format = ord(data[i+2])
            annotation_type = ord(data[i+3])
            if ((annotation_format != ANNO_FORMAT_FIRST) or
                ((annotation_type != ANNO_TYPE_SCRIBBLE) and
                 (annotation_type != ANNO_TYPE_VSCRIBBLE) and
                 (annotation_type != ANNO_TYPE_ERASURE))):
                note(2, "Skipped annotation format = %d, type = %d -- can't handle it",
                     annotation_format, annotation_type)
            else:
                _show_scribble(data[i:i+annotation_length])
                annotations = annotations + data[i:i+annotation_length]
            i = i + annotation_length
        _add_annotations(doc, annotations)
        response.reply("")
    except:
        note("handle_scribble:  exception on attempting to call add_annotations")
        show_exception()


def _add_activity (doc, activities):
    lock_folder(doc.folder())
    try:
        activity_file = os.path.join(doc.folder(), "activity")
        if (os.path.exists(activity_file)):
            fp = open(activity_file, 'ab')
        else:
            fp = open(activity_file, 'wb')
        fp.write(activities)
        fp.close()
    finally:
        unlock_folder(doc.folder())

PREDEFINED_INKPOTS = (
    ("\0\0\0\0\0", 0),
    ("\0xff\0\0\0xff\x0a", 1),
    ("\0\0\0xff\0xff\x0a", 2),
    ("\xb3\0\0\0x33\xa0", 3),
    ("\0\xb3\0\0x33\xa0", 4),
    ("\0\0\xb3\0x33\xa0", 5),
    )

def _doc_state (doc):

    CLOSED_DOC = 7
    PAGE_TURNED = 1
    ANN_ON = 8
    ANN_OFF = 9
    INKPOT = 10
    BOOKMARK_SET = 11
    BOOKMARK_UNSET = 12

    activity_file = os.path.join(doc.folder(), "activity")
    page = 0
    turned_to = None
    annotations = None
    inkpot = None
    bookmarks = {0: (None, None), 1: (None, None), 2: (None, None)}
    if (os.path.exists(activity_file)):
        fp = open(activity_file, 'rb')
        data = fp.read()
        fp.close()
        i = 0
        while (i < len(data)):
            if ord(data[i]) != 0:
                note("bad data byte:  %s", data[i])
                return (page, annotations, inkpot, bookmarks)     # no idea what the format is
            else:
                action = (ord(data[i+12]) << 8) + ord(data[i+13])

#                 note("activity %s, page %d, at %s", ACTIVITY_CODE_NAMES.get(action, str(action)),
#                      (ord(data[i+2]) << 8) + ord(data[i+3]),
#                      time.ctime(((long(ord(data[i+4])) << 56) +
#                                  (long(ord(data[i+5])) << 48) +
#                                  (long(ord(data[i+6])) << 40) +
#                                  (long(ord(data[i+7])) << 32) +
#                                  (long(ord(data[i+8])) << 24) +
#                                  (ord(data[i+9]) << 16) +
#                                  (ord(data[i+10]) << 8) +
#                                  (ord(data[i+11])))/1000))

                if (action == CLOSED_DOC):
                    page = (ord(data[i+2]) << 8) + ord(data[i+3])
                elif (action == PAGE_TURNED):
                    turned_to = (ord(data[i+2]) << 8) + ord(data[i+3])
                elif (action == ANN_ON):
                    annotations = true
                elif (action == ANN_OFF):
                    annotations = false
                elif (action == INKPOT):
                    if ord(data[i+1]) == 1:
                        inkpot = ord(data[i + 14])
                    else:
                        for pot in PREDEFINED_INKPOTS:
                            if data[i+14:i+19] == pot[0]:
                                inkpot = pot[1]
                elif (action == BOOKMARK_SET):
                    index = ord(data[i + 14])
                    pageno = (ord(data[i+2]) << 8) + ord(data[i+3])
                    height = ((ord(data[i+15]) << 8) + ord(data[i+16])) / float(65536)
                    bookmarks[index] = (pageno, height)                              
                elif (action == BOOKMARK_UNSET):
                    index = ord(data[i + 14])
                    height = ((ord(data[i+15]) << 8) + ord(data[i+16])) / float(65536)
                    bookmarks[index] = (-1, height)
                
            i = i + 14 + ord(data[i+1])
    return (page, annotations, inkpot, bookmarks)

def dv_log_activity (repo, response, params):

    """Handle new activity events sent back by the client."""

    content_type = response.request.get_header('content-type')
    if content_type != "application/x-uplib-activities":
        note("log_activity:  bad content-type %s", content_type)
        response.error(HTTPCodes.BAD_REQUEST, "Invalid content-type " + content_type);
        return

    if not response.content:
        note("log_activity:  empty content")
        response.error(HTTPCodes.BAD_REQUEST, "No activities in message")
        return

    if hasattr(response.content, "seek"):
        response.content.seek(0, 0)

    version = int(response.content.readline());
    if version != 1:
        note("log_activity:  invalid protocol version %d" % version)
        if hasattr(response.content, "seek"):
            response.content.seek(0, 0)
        note("log_activity:  whole content is<\n%s>", response.content.read());
        response.error(HTTPCodes.BAD_REQUEST, "can't understand protocol version " + str(version))
        return

    doc_id = response.content.readline()[:-1]

    if not doc_id:
        note("log_activity:  no doc_id")
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return

    if not repo.valid_doc_id(doc_id):
        note("log_activity:  invalid doc_id")
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter " + doc_id + " specified.")
        return

    try:
        doc = repo.get_document(doc_id);
        current_page = None
        activities = ""
        data = response.content.read()
        i = 0
        while ((i + 14) <= len(data)):
            activity_format = ord(data[i])
            activity_extension_length = ord(data[i+1])
            activity_action = ((ord(data[i+12]) << 8) + ord(data[i+13]))
            if (activity_format != ACT_FORMAT_FIRST):
                raise Error("Unknown activity record format:  %d" % activity_format)

            # we keep track of page-change actions here as a cache, so that we
            # don't have to re-read the whole action log again if the document is
            # requested again.
            if (activity_action == ACT_ACTION_CLOSE) or (activity_action == ACT_ACTION_PAGETURN):
                current_page = (ord(data[i+2]) << 8) + ord(data[i+3])

            activities = activities + data[i:(i+14+activity_extension_length)]
            i = i + 14 + activity_extension_length
        _add_activity(doc, activities)
        if (current_page is not None):
            setattr(doc, "current_page", current_page)
        response.reply("")
    except:
        note("log_activity:  exception on attempting to call add_activity")
        show_exception()




pageview_actions = {

    "dv_show" : dv_show,
    "dv_search" : dv_search,
    "dv_explain" : dv_explain,

    "dv_get_hotspots" : dv_get_hotspots,
    "dv_handle_hotspots" : dv_handle_hotspots,

    "dv_get_scribbles" : dv_get_scribbles,
    "dv_handle_scribble" : dv_handle_scribble,

    "dv_log_activity" : dv_log_activity,

    "dv_fetch_note" : dv_fetch_note,
    "dv_handle_notes" : dv_handle_notes,

    "dv_doc_parameters" : dv_doc_parameters,
    }
