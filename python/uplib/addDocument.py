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

import re, os, sys, ConfigParser, string, time, shutil, tempfile, stat, traceback, urllib, StringIO, codecs, urllib2, random
import cgi, getopt, urlparse, socket, types, traceback, imp, unicodedata, httplib, math, bisect, struct, pprint

from uplib.plibUtil import false, true, PATH_SEPARATOR, Error, note, configurator, set_verbosity, subproc, update_metadata, create_new_folder, getpass, zipup, read_metadata, unzip, get_note_sink, read_wordboxes_file, read_file_handling_charset, uthread, wordboxes_page_iterator, set_configuration_port, topological_sort

#import uplib.code_timer as code_timer
from uplib.webutils import Fetcher, Cache, get_cookies, get_htmldoc_cookies, htmlescape, parse_URL_with_scheme, parse_URL, https_post_multipart, http_post_multipart, TitleFinder, set_cookies_source, ParsingDone

from uplib.links import pdflinksParser

from HTMLParser import HTMLParser, HTMLParseError
import htmlentitydefs

from PIL import Image

try:
    from uplib.language import identify_language
except ImportError:
    identify_language = None

############################################################
###
###  Global variables
###
############################################################

AssemblyLine = None             # directory where the documents are put

GHOSTSCRIPT = None              # the location of the Ghostscript program
TIFFINFO = None           # the location of the tiffinfo program
TIFFSET = None             # the location of the tiffset program
TIFFCP = None               # the location of the tiffcp program
PDFTOTEXT = None         # the location of the pdftotext program
PDFINFO = None           # command to run to extract the PDF info
WORDBOXES_PDFTOTEXT = None      # the version of pdftotext that knows about wordboxes
PDFTOTEXT_COMMAND = None
WORDBOXES_PDFTOTEXT_COMMAND = None
TIFFSPLIT = None
PDFLINKS = None
PDFLINKS_COMMAND = None
BBOXES_FORMAT_VERSION_TO_CREATE = 2

TIFF_SPLIT_CMD = None
TIFF_COMPRESS_CMD = None

IMAGE_SIZE_LIMIT = (3000 * 3000 * 4)        # 3K x 3K color photo, 36MB

PDFTOTIFF_CMD_MONO = None
PDFTOTIFF_CMD_COLOR = None

PDFTOPNG_CMD_MONO = None
PDFTOPNG_CMD_COLOR = None

OCR_WEB_SERVICE_URL = None
XDOC_OCR_WEB_SERVICE_URL = None
MSOFFICE_OCR_WEB_SERVICE_URL = None
SUMMARY_LENGTH = None

TAR = None
TAR_CMD = None

ASSUME_NO_PASSWORD = None

SCORETEXT = None
SCORETEXT_MODEL = None
SCORETEXT_CMD = None
SCORETEXT_THRESHOLD = None

ENSCRIPT = None
ENSCRIPT_CMD = None
CODE_ENSCRIPT_COMMAND = None
NENSCRIPT = None
NENSCRIPT_CMD = None
CODE_NENSCRIPT_COMMAND = None
PS2PDF = None
PS2PDF_CMD = None
FILE_CMD = None
ASSUME_TEXT_NO_COLOR = false

OPENOFFICE_CONVERT_TO_PDF = None
USE_OPENOFFICE_FOR_WEB = false
USE_OPENOFFICE_FOR_MSOFFICE = false
USE_TOPDF_FOR_MSOFFICE = False
USE_TOPDF_FOR_WEB = False
TOPDF_PORT = 0
TOPDF_HOST = None
PUSH_TO_PDF = False
OOO_CONVERT_TO_PDF = None
OOO_WEB_TO_PDF_CMD = None
OOO_MSWORD_TO_PDF_CMD = None
OOO_POWERPOINT_TO_PDF_CMD = None
OOO_EXCEL_TO_PDF_CMD = None
OOO_MSWORD_XML_TO_PDF_CMD = None
OOO_POWERPOINT_XML_TO_PDF_CMD = None
OOO_EXCEL_XML_TO_PDF_CMD = None
OOO_RTF_TO_PDF_CMD = None

SPLITUP_BINARY = None
SPLITUP_CMD = None

HTMLDOC = None
HTMLDOC_CMD = None

OCR_DEBUG = false

MS_TO_PDF_URL = None

SKEW_DETECT_URL = None
DESKEW_LIMIT_DEGREES = 0.5

DRYCLEAN_SERVICE_URL = None

TRANSFER_FORMAT = 'zipped-folder'

PARSERS = []

CODETIMER_ON = false

UPLIB_VERSION = None
UPLIB_LIBDIR = None

UPLIB_CLIENT_CERT = None

DEFAULT_LANGUAGE = None

############################################################
###
###  Exceptions
###
############################################################

class AuthenticationError(Error):

    def __init__(self, host, port, password):
        Error.__init__(self, "Can't authenticate to https://%s:%s/ with password '%s'." % (host, port, password))
        self.host = host
        self.port = port
        self.password = password

class ConnectionError(Error):

    def __init__(self, host, port):
        Error.__init__(self, "Can't connect to UpLib server at https://%s:%s/." % (host, port))
        self.host = host
        self.port = port

class ProcessError(Error):

    def __init__(self, formatobj, exc):
        Error.__init__(self, "Some processing error occurred")
        self.formatter = formatobj
        self.exception = exc

    def format_exception(self):
        t, v, b = self.exception
        return string.join(traceback.format_exception(t, v, b))

class NoFormat (Error):

    def __init__(self, filename):
        Error.__init__(self, "Can't figure document format for file %s" % filename)
        self.filename = filename

class ParserSortConsistencyException (Error):

    def __init__(self, parsers):
        Error.__init__(self, "Ordering conflicts for parsers %s" % parsers)
        self.parsers = parsers

class MultiPartDocument(Exception):

    # raised to signal control-flow exception in multi-part case

    def __init__(self, parts):
        self.parts = parts

class MissingResource(Error):

    # raised to signal the absence of some resource required for the operation

    def __init__(self, resource):
        Error.__init__(self, "Missing resource, described as \"%s\"." % resource)
        self.resource = resource


def format_exception ():
    import traceback, string
    t, v, b = sys.exc_info()
    return string.join(traceback.format_exception(t, v, b))

def show_exception (x):

    if isinstance(x, AuthenticationError):
        if not x.password:
            sys.stderr.write('Error:  No password supplied for repository at https://%s:%s/.\n' % (x.host, x.port))
        else:
            sys.stderr.write('Error:  Invalid password "%s" supplied for repository at https://%s:%s/.\n' % (x.password, x.host, x.port))
        return 3

    elif isinstance(x, ConnectionError):
        sys.stderr.write('Error:  Can\'t connect to repository angel at https://%s:%s/.\n' % (x.host, x.port))
        return 2

    elif isinstance(x, ProcessError):
        note(2, x.format_exception())
        t, v, b = x.exception
        sys.stderr.write('Error:  Parse of %s failed:\n  %s:  %s.\n' % (x.formatter.doc, t, v))
        x.formatter.delete_folder()
        return 5

    elif isinstance(x, NoFormat):
        sys.stderr.write("Couldn't identify format for file %s.\n" % x.filename)
        return 4

    elif isinstance(x, Error):
        sys.stderr.write("Error:  %s\n" % str(x))
        return 1

############################################################
###
###  Compiled regular expression patterns
###
############################################################

newline_expression = re.compile(r'(\s*\n)+')
whitespace_expression = re.compile(r'\s+')

charset_pattern = re.compile(r"^Content-Type:\s*text/plain;\s*charset=([^)]*)\n", re.IGNORECASE)

alnum_chars = string.digits + string.letters

IMAGE_EXTENSIONS = re.compile(r'((\.gif)|(\.png)|(\.jpeg)|(\.jpg)|(\.tif)|(\.tiff)|(\.pbm)|(\.pnm)|(\.pgm)|(\.ppm)|(\.bmp)|(\.eps)|(\.rast)|(\.xbm)|(\.xpm))$', re.IGNORECASE)
TIFF_EXTENSION = re.compile(r'((\.tiff)|(\.tif))$', re.IGNORECASE)
PDF_EXTENSION = re.compile(r'\.pdf', re.IGNORECASE)
POSTSCRIPT_EXTENSION = re.compile(r'\.ps', re.IGNORECASE)
HTML_EXTENSION = re.compile(r'((\.html)|(\.htm))$', re.IGNORECASE)
MS_EXTENSIONS = re.compile(r'((\.ppt)|(\.pps)|(\.doc)|(\.dot)|(\.xls)|(\.xlt)|(\.docx)|(\.pptx)|(\.ppsx)|(\.xlsx)|(\.rtf))$', re.IGNORECASE)
FILE_TEXT_ENDING = re.compile(r'\stext$', re.IGNORECASE)
URL_PREFIX = re.compile(r'^((http:)|(https:)|(ftp:))')

CONTENT_TYPES = { "application/pdf": "pdf",
                  "text/plain" : "txt",
                  "application/postscript": "ps",
                  "application/vnd.ms-powerpoint": "ppt",
                  "application/msword": "doc",
                  "application/vnd.ms-excel": "xls",
                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
                  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
                  "application/rtf": "rtf",
                  "image/tiff": "tiff",
                  "image/gif": "gif",
                  "image/pbm": "pbm",
                  "image/jpeg": "jpg",
                  "image/png": "png",
                  "image/bmp": "bmp",
                  "text/html": "html",
                  "message/rfc822": "rfc822",
                  }
                  
############################################################
###
###  Utility Functions
###
############################################################

def mktempdir():
    # make a tempdir under the AssemblyLine directory
    global AssemblyLine

    if not AssemblyLine or not os.path.isdir(AssemblyLine):
        return tempfile.mktemp()
    else:
        if hasattr(tempfile, 'mkdtemp'):
            return tempfile.mkdtemp("", "UpLibAdd-", AssemblyLine)
        else:
            tempfile.tempdir = AssemblyLine
            name = tempfile.mktemp()
            os.mkdir(name)
            return name

def mktempfile(extension=None):
    # make a temp filename under the AssemblyLine directory
    global AssemblyLine

    if extension is None:
        extension = ""
    elif not extension.startswith("."):
        extension = "." + extension
    if hasattr(tempfile, "mkdtemp"):
        if not AssemblyLine or not os.path.isdir(AssemblyLine):
            return tempfile.mktemp(extension, "UpLibAdd-")
        else:
            return tempfile.mktemp(extension, "UpLibAdd-", AssemblyLine)
    else:
        # 2.2 or earlier
        if AssemblyLine and os.path.isdir(AssemblyLine):
            tempfile.tempdir = AssemblyLine
        tempfile.template = "UpLibAdd-"
        return tempfile.mktemp(extension)

def quote_spaces(filename):
    return re.sub(" ", "\\ ", filename)

def convert_image_to_tiff (filepath, tiffpath):
    note(3, "trying to convert %s to TIFF", filepath)
    from PIL import Image
    im = Image.open(filepath)
    if not im:
        raise IOError(filepath)
    im.save(tiffpath, 'TIFF')
    return true

def convert_image_to_png (filepath, pngpath):
    note(3, "trying to convert %s to PNG", filepath)
    from PIL import Image
    im = Image.open(filepath)
    if not im:
        raise IOError(filepath)
    im.save(pngpath, 'PNG')
    return true

def black_and_white (color1, color2):
    if (color1 is None or color2 is None):
        return false

    note(5, "       color1 is %s, and color 2 is %s", color1, color2)

    if (((type(color1) == type('s') and type(color2) == type('')) and
             (color1 == '\xff\xff\xff' and color2 == '\x00\x00\x00') or
             (color2 == '\xff\xff\xff' and color1 == '\x00\x00\x00'))): return true

    if (type(color1) == type(3) and type(color2) == type(3)):
        return (color1 == 0 and color2 == 255) or (color1 == 255 and color2 == 0)

    if (type(color1) == type(()) and type(color2) == type(()) and len(color1) == 2 and len(color1) == 2):

        color1 = color1[1]
        color2 = color2[1]

        return (((type(color1) == type(1) and type(color2) == type(1)) and
                 (color1 == 0 and color2 == 255) or
                 (color2 == 0 and color1 == 255)) or
                ((type(color1) == type(()) and type(color2) == type(())) and
                 (color1 == (0, 0, 0) and color2 == (255, 255, 255)) or
                 (color2 == (0, 0, 0) and color1 == (255, 255, 255))))

    return false


def calculate_originals_fingerprint (originals_path):

    # called to create a quick hash of the document's content

    import hashlib

    if os.path.isdir(originals_path):
        dirs = [dir for dir in os.walk(originals_path)]
    else:
        dirpath, filename = os.path.split(originals_path)
        dirs = [(dirpath, [], [filename])]
    s = hashlib.sha1()
    dirs.sort()
    for dirpath, junk, files in dirs:
        files.sort()
        for filename in files:
            fp = open(os.path.join(dirpath, filename), 'rb')
            try:
                data = fp.read(1 << 16)
                while data:
                    s.update(data)
                    data = fp.read(1 << 16)
            finally:
                fp.close()
    return s.hexdigest()


def clean_wordboxes_overlays (folder, debug=False):

    text_path = os.path.join(folder, "contents.txt")
    boxes_path = os.path.join(folder, "wordbboxes")

    if not (os.path.exists(text_path) and os.path.exists(boxes_path)):
        return

    duplicates = []
    for page_index, boxes in wordboxes_page_iterator(folder):
        for b1 in boxes:
            for b2 in boxes:
                if b2 is b1:
                    continue
                if b2.left() >= b1.left():
                    if b2.percentage_overlap(b1) > 0.8:
                        dup = ((b2.contents_offset() > b1.contents_offset()) and b2) or b1
                        duplicates.append(dup)
                        break

        # for debugging, print list of boxes and dups
        if debug:
            for b in boxes:
                dup = b in duplicates
                note("%2d:  %s %5.1fx%5.1f@%5.1f,%5.1f \"%s\"",
                     page_index, (dup and "*") or " ", b.width(), b.height(), b.left(), b.top(), b.text())

    # now remove dups from wordbboxes file
    # we steal this code from the emailParser

    text, charset, language = read_file_handling_charset(text_path, True)
    if identify_language:
        # take this opportunity to update our identification of the actual language in use
        language = identify_language(text)

    # this should be 'replace', but for now let's see the errors
    text = text.encode(charset, 'error')

    dups = [(x.contents_offset(), len(x.text().encode(charset, "replace")), x) for x in duplicates]

    # sort by content-offset
    dups.sort(lambda b1, b2: cmp(b1[0], b2[0]))

    fp = open(boxes_path, 'rb')
    boxes = fp.read()
    fp.close()
    fp = open(boxes_path, 'wb')

    version = ord(boxes[10]) - ord('0')
    if version == 1:
        offset = 20
        boxlen = 24
    elif version == 2:
        offset = 24
        boxlen = 28
    else:
        raise ValueError("Can't understand version # %s in wordbboxes file" % version)

    # header
    fp.write(boxes[:12])
    pointer = 12

    # now the data, adjusting the pointers
    removed = 0
    while dups and (pointer < len(boxes)):
        textoffset = struct.unpack(">I", boxes[pointer+offset:pointer+offset+4])[0]
        pagemarker = (textoffset == 0) and (boxes[pointer:pointer+boxlen] == boxlen*'\0')
        if pagemarker:
            fp.write(boxes[pointer:pointer+boxlen])
        elif textoffset < dups[0][0]:
            # good box, so keep it, but adjust position as necessary
            fp.write(boxes[pointer:pointer+offset])
            fp.write(struct.pack(">I", textoffset - removed))
        else:
            # duplicate box, so remove it
            note(3, "removing duplicate word \"%s\" (%5.1fx%5.1f@%5.1f,%5.1f)",
                 dups[0][2].text(), dups[0][2].width(), dups[0][2].height(), dups[0][2].left(), dups[0][2].top())
            textpos = textoffset - removed
            textlen = dups[0][1]
            text = text[:textpos] + text[textpos+textlen:]
            removed += textlen
            dups = dups[1:]
        pointer += boxlen

    # close the worddboxes file
    fp.close()
    # and re-write the text file
    fp = open(text_path, 'wb')
    fp.write('Content-Type: text/plain; charset=%s\nContent-Language: %s\n' % (charset, language))
    fp.write(text)
    fp.close()

def optimize_tiff_compression (tiff_file_path, save_blank_pages):

    global TIFFSPLIT, TIFFCP, TIFF_SPLIT_CMD, TIFF_COMPRESS_CMD

    tmpdir = mktempdir()
    os.chmod(tmpdir, 0700)
    try:
        tiffmaster = os.path.join(tmpdir, "master.tiff")
        split_command = (TIFF_SPLIT_CMD
                         % (TIFFCP, tiff_file_path, tiffmaster,
                            TIFFSPLIT, tiffmaster, os.path.join(tmpdir, "x")))
        status, output, tsignal = subproc(split_command)
        if status != 0:
            raise Error("Command '%s' failed with output <%s>" % (split_command, output))
        files = os.listdir(tmpdir)
        files.sort()
        newfiles = []
        pageno = 1
        monochrome_pagecount = 0
        paletted_pagecount = 0
        fullcolor_pagecount = 0
        for file in files:
            if file[0] != 'x':
                continue
            path = os.path.join(tmpdir, file)
            im = Image.open(path)
            if im.mode in ('L', 'P'):
                im2 = im
            elif im.mode == '1':
                im2 = im.convert('L')
            else:
                im2 = im.convert('RGB').quantize(256)
            a = im2.histogram()
            b = reduce(lambda x, y: (y and x + [y]) or x, a, [])
            if im2.mode == 'L':
                color1 = b[0]
                color2 = b[1]
            else:
                p = im2.im.getpalette()
                color1 = p[:3]
                color2 = p[3:6]
            compression = 'zip'
            new_filename = path + '2'
            if len(b) == 1:
                if save_blank_pages:
                    compression = 'g4'
                    args['compression'] = 'g4'
                    # store out the file as a monochrome image
                    im = im.convert('1', dither=Image.NONE)
                    im.save(path, 'TIFF')
                    note(3, "   page %d is blank", pageno)
                    monochrome_pagecount = monochrome_pagecount + 1
                else:
                    note(3, "   page %d contains no data.  Eliminating it.", pageno)
                    pageno = pageno + 1
                    continue
            elif (im.mode == '1') or (len(b) == 2) and ((color1 == '\xff\xff\xff' and color2 == '\x00\x00\x00') or
                                                        (color2 == '\xff\xff\xff' and color1 == '\x00\x00\x00')):
                compression = 'g4'
                # store out the file as a monochrome image
                if im.mode != '1':
                    im = im.convert('1', dither=Image.NONE)
                im.save(path, 'TIFF')
                note(3, "   page %d is monochrome", pageno)
                monochrome_pagecount = monochrome_pagecount + 1
            elif (len(b) < 256):
                im = im2.convert('P', dither=Image.NONE)
                im.save(path, 'TIFF')
                note(3, "   page %d is paletted color (buckets = %d)", pageno, len(b))
                paletted_pagecount = paletted_pagecount + 1
            else:
                note(3, "   page %d is full color (buckets = %d)", pageno, len(b))
                fullcolor_pagecount = fullcolor_pagecount + 1
            compress_command = TIFF_COMPRESS_CMD % (TIFFCP, compression, path, new_filename)
            newfiles.append(new_filename)
            status, output, tsignal = subproc(compress_command)
            # we ignore bizarre return codes from tiffcp
            if not os.path.exists(new_filename):
                raise Error("Command '%s' failed with output <%s>" % (compress_command, output))
            pageno = pageno + 1

        rejoin_command = TIFFCP
        if sys.platform.lower().startswith("win"):
            rejoin_command = '"' + rejoin_command + '"'
        for file in newfiles:
            rejoin_command = rejoin_command + ' "' + file + '"'
        rejoin_command = rejoin_command + ' "' + tiff_file_path + '"'
        os.unlink(tiff_file_path)
        status, output, tsignal = subproc(rejoin_command)
        # we ignore the bizarre return codes from tiffcp
        if not os.path.exists(tiff_file_path):
            raise Error("Command '%s' failed to create %s" % (rejoin_command, tiff_file_path))
        return (monochrome_pagecount, paletted_pagecount, fullcolor_pagecount, pageno - 1)
    finally:
        shutil.rmtree(tmpdir)

def _http_post(url, data):
    host, port, path = parse_URL(url)
    h = httplib.HTTPConnection(host, port)
    h.putrequest('POST', path)
    h.putheader('Content-Type', 'application/octet-stream')
    h.putheader('Content-Length', str(len(data)))
    h.endheaders()
    h.send(data)
    response = h.getresponse()
    errcode = response.status
    errmsg = response.reason
    return response.status, response.reason, response.msg, ((response.status == 200) and response.read())

def skew_detect_png_page_images(page_images_dir):

    # create tar of the folder
    if not SKEW_DETECT_URL:
        return None

    tmpfilename = tempfile.mktemp()
    try:
        zipup(page_images_dir, tmpfilename, true)

        # send it to the repository
        errcode, errmsg, headers, result = _http_post(SKEW_DETECT_URL, open(tmpfilename, 'rb').read())

        if (errcode != 200):
            note("skew detection service at %s failed:  %s:  %s", SKEW_DETECT_URL, errcode, errmsg)
            return None

        note(5, "skew results are:\n%s\n", result)

        lines = string.split(result, "\n")
        retvals = []
        pageno = 0
        for line in lines:
            pageno = pageno + 1
            if not string.strip(line):
                continue
            if (string.strip(line) == '*'):
                retvals.append(0.0)
            else:
                try:
                    v = float(line)
                    retvals.append(v * 57.2957795)      # convert to degrees
                except ValueError:
                    note("Bad apparent skew angle floating point value for page %d:  %s", pageno, line)
                    retvals.append(0.0)
        return retvals

    finally:
        if os.path.exists(tmpfilename):
            os.unlink(tmpfilename)


def dryclean_png_page_images(page_images_dir):

    # create tar of the folder
    if not SKEW_DETECT_URL:
        return None

    tmpfilename = tempfile.mktemp()
    try:
        zipup(page_images_dir, tmpfilename, true)

        # send it to the repository
        errcode, errmsg, headers, result = _http_post(DRYCLEAN_SERVICE_URL, open(tmpfilename, 'rb').read())

        if (errcode != 200):
            note("dryclean service at %s failed:  %s:  %s", DRYCLEAN_SERVICE_URL, errcode, errmsg)
            return None

        os.unlink(tmpfilename)
        fp = open(tmpfilename, "w")
        fp.write(result)
        fp.close()
        
        unzip(page_images_dir, tmpfilename)

        return errcode

    finally:
        if os.path.exists(tmpfilename):
            os.unlink(tmpfilename)


def optimize_png_compression (page_images_dir, save_blank_pages, angles):

    def deskew_image (im, angle):
        # should add a white border before deskewing to avoid rotating in black pixels
        # calculate border thickness as "sin(max detectable skew in degrees) * length-of-longest-side pixels"
        # rotate, then crop the border using im.getbbox()?  perhaps not -- just crop back to orig size
        note(4, "     deskewing by %s degrees...", angle)
        return im.rotate(-angle, Image.BICUBIC)

    pages = [x for x in os.listdir(page_images_dir) if (x.startswith("page") and x.endswith(".png"))]
    pages.sort()

    pageno = 1
    monochrome_pagecount = 0
    paletted_pagecount = 0
    fullcolor_pagecount = 0
    blank_pages = []

    out_pageno = 1

    pageinfo = {}

    for page in pages:

        inpath = os.path.join(page_images_dir, page)
        outpath = os.path.join(page_images_dir, "page%05d.png" % out_pageno)
        note(4, "   loading page %s", page)
        im = Image.open(inpath)
        pageinfo[pageno] = { 'size': im.size, 'mode': im.mode, 'outpath' : outpath }
        note(4, "      %sx%s, mode %s", im.size[0], im.size[1], im.mode)
        if im.mode == '1':
            im2 = im.convert('L')
        elif im.mode in ('L', 'P'):
            im2 = im
        else:
            im2 = im.convert('RGB')
            if not hasattr(im2, "getcolors"):
                note(4, "     quantizing page %d..." % pageno)
                im2 = im2.quantize(256)
                note(4, "     ...done.")
        if hasattr(im2, "getcolors"):
            b = im2.getcolors()
            if b is not None:
                color1 = b[0]
                if (len(b) > 1):
                    color2 = b[1]
                else:
                    color2 = None
        else:
            a = im2.histogram()
            b = reduce(lambda x, y: (y and x + [y]) or x, a, [])
            if im2.mode == 'L':
                color1 = b[0]
                color2 = b[1]
            else:
                p = im2.im.getpalette()
                color1 = p[:3]
                color2 = p[3:6]
        note(4, "     %s color%s in page %s", (b and len(b)) or "many", ((not b or len(b) != 1) and "s") or "", pageno)
        if b and len(b) == 1:
            if save_blank_pages:
                # store out the file as a monochrome image
                im = im.convert('1', dither=Image.NONE)
                im.save(outpath, 'PNG')
                note(3, "   page %d is blank", out_pageno)
                monochrome_pagecount = monochrome_pagecount + 1
                pageinfo[pageno]['output-mode'] = im.mode
                pageinfo[pageno]['output-page'] = out_pageno
                out_pageno = out_pageno + 1
            else:
                note(3, "   page %d contains no data.  Eliminating it.", pageno)
                blank_pages.append(pageno)
                pageinfo[pageno]['output-mode'] = None
                pageinfo[pageno]['output-page'] = None
                pageno = pageno + 1
                continue
        elif b and (len(b) == 2) and black_and_white(color1, color2):
            # store out the file as a monochrome image
            im = im.convert('1', dither=Image.NONE)
            if angles and len(angles) >= pageno and math.fabs(angles[pageno-1]) > DESKEW_LIMIT_DEGREES:
                im = deskew_image(im, angles[pageno-1])
            im.save(outpath, 'PNG')
            note(3, "   page %d is monochrome", pageno)
            monochrome_pagecount = monochrome_pagecount + 1
            pageinfo[pageno]['output-mode'] = im.mode
            pageinfo[pageno]['output-page'] = out_pageno
            out_pageno = out_pageno + 1
        elif b and (len(b) < 256):
            im = im.convert('P', dither=Image.NONE)
            if angles and len(angles) >= pageno and math.fabs(angles[pageno-1]) > DESKEW_LIMIT_DEGREES:
                im = deskew_image(im, angles[pageno-1])
            im.save(outpath, 'PNG')
            note(3, "   page %d is paletted color (buckets = %d)", pageno, len(b))
            paletted_pagecount = paletted_pagecount + 1
            pageinfo[pageno]['output-mode'] = im.mode
            pageinfo[pageno]['output-page'] = out_pageno
            out_pageno = out_pageno + 1
        elif hasattr(im2, "getcolors") and b and (len(b) == 256):
            if (im.mode == "P"):
                note(3, "   page %d is paletted color (buckets = 256)", pageno)
            elif (im.mode == "RGB"):
                im = im.convert('P', dither=Image.NONE)
                note(3, "   page %d is paletted color (buckets = 256)", pageno)
            else:
                note(3, "   page %d is 8-bit grayscale", pageno)
            if angles and len(angles) >= pageno and math.fabs(angles[pageno-1]) > DESKEW_LIMIT_DEGREES:
                im = deskew_image(im, angles[pageno-1])
            im.save(outpath, "PNG")
            paletted_pagecount = paletted_pagecount + 1
            pageinfo[pageno]['output-mode'] = im.mode
            pageinfo[pageno]['output-page'] = out_pageno
            out_pageno = out_pageno + 1
        else:
            note(3, "   page %d is full color (buckets = %s)", pageno, (b and len(b)) or "many")
            if angles and len(angles) >= pageno and math.fabs(angles[pageno-1]) > DESKEW_LIMIT_DEGREES:
                im = deskew_image(im, angles[pageno-1])
            im.save(outpath, "PNG")
            fullcolor_pagecount = fullcolor_pagecount + 1
            pageinfo[pageno]['output-mode'] = im.mode
            pageinfo[pageno]['output-page'] = out_pageno
            out_pageno = out_pageno + 1
        pageno = pageno + 1

    note(3, "  %d pages in optimized image directory", out_pageno - 1)

    # if we removed all the pages, better re-think this strategy
    if ((out_pageno == 1) and blank_pages):
        note(2, "all pages were eliminated as blank -- adding them back in")
        pageno = 1
        for page in pages:
            inpath = os.path.join(page_images_dir, page)
            outpath = os.path.join(page_images_dir, "page%05d.png" % out_pageno)
            im = Image.open(inpath)
            pageinfo[pageno] = { 'size': im.size, 'mode': im.mode, 'outpath' : outpath }
            # store out the file as a monochrome image
            im = im.convert('1')
            im.save(outpath, 'PNG')
            note(3, "   page %d is blank", out_pageno)
            monochrome_pagecount = monochrome_pagecount + 1
            pageinfo[pageno]['output-mode'] = im.mode
            pageinfo[pageno]['output-page'] = out_pageno
            out_pageno = out_pageno + 1
            blank_pages = []

    # if we skipped any pages, we have to delete the extra files for those pages
    while (out_pageno <= len(pages)):
        path = os.path.join(page_images_dir, "page%05d.png" % out_pageno)
        if os.path.exists(path):
            os.unlink(path)
        out_pageno = out_pageno + 1

    def figure_canonical_size(pageinfo):
        sizes = {}
        maxsize = [0, 0]
        for page in pageinfo:
            size = pageinfo[page]['size']
            sizes[size] = sizes.get(size, 0) + 1
            maxsize[0] = max(maxsize[0], size[0])
            maxsize[1] = max(maxsize[1], size[1])
        pagesizes = sizes.items()       # sequence of ((width, height), count)

        def sort_by_frequency(item1, item2):
            if item1[1] > item2[1]:
                return -1
            elif item1[1] < item2[1]:
                return 1
            else:
                return 0
        pagesizes.sort(sort_by_frequency)
        
        note(4, "pagesizes are %s", pagesizes)
        # if there's only one size, use it
        if len(pagesizes) == 1:
            note(3, "  all pages are the same size")
            cpagesize = pagesizes[0][0]
        # if some pages are rotated, use the first page size
        elif (len(pagesizes) == 2) and (pagesizes[0][0][0] == pagesizes[1][0][1]) and (pagesizes[0][0][1] == pagesizes[1][0][0]):
            note(3, "  some pages are rotated")
            cpagesize = pageinfo[1]['size']
        # if most pages are one size, use that size
        elif pagesizes[0][1] > (len(pageinfo)/2):
            note(3, "  most pages are of size %s", pagesizes[0][0])
            cpagesize = pagesizes[0][0]
        # else use the maxsize
        else:
            note(3, "  pages are lots of different sizes; using %s", tuple(maxsize))
            cpagesize = tuple(maxsize)

        return cpagesize

    def pad_image(topad, proper_size, outpath):
        background_color = topad.getpixel((0,0,))
        padded = Image.new(topad.mode, proper_size, background_color)
        padded.paste(topad, (0, 0))
        padded.save(outpath)

    modified_pages = {}
    if pageinfo:
        canonical_size = figure_canonical_size(pageinfo)

    for page in pageinfo:
        pi = pageinfo[page]
        pagesize = pi['size']
        # Each page should be examined to see if it is either the
        #canonical size, or a rotation of the canonical size.  If a
        #rotation, the page image should be rotated to the canonical
        #size.  If neither, the page image should first be scaled to
        #fit inside the canonical size, preserving the aspect ratio of
        #the page, then padded with its estimated background color to
        #the canonical page size.  Pages which already fit entirely
        #within the canonical size are not enlarged; they are simply
        #padded.
        if pagesize != canonical_size:
            # fix page:
            pagetrack = os.path.split(pi['outpath'])[1]
            if pagesize[0] == canonical_size[1] and pagesize[1] == canonical_size[0]:
                # rotation
                note(2, "  rotating page %d %s", page, pagesize)
                Image.open(pi['outpath']).rotate(90).save(pi['outpath'])
                modified_pages[pagetrack] = ('rotated', 90)
            elif pagesize[0] <= canonical_size[0] and pagesize[1] <= canonical_size[1]:
                # pad to fit, on right and bottom
                note(2, "  padding page %d %s to %s", page, pagesize, canonical_size)
                pad_image(Image.open(pi['outpath']), canonical_size, pi['outpath'])
                modified_pages[pagetrack] = ('padded', pagesize)
            else:
                # scale to fit
                note(2, "  scaling and padding page %d %s to %s", page, pagesize, canonical_size)
                scale_factor = min(canonical_size[0]/float(pagesize[0]), canonical_size[1]/float(pagesize[1]))
                toscale = Image.open(pi['outpath'])
                scaled = toscale.resize((int(pagesize[0] * scale_factor), int(pagesize[1] * scale_factor),), Image.ANTIALIAS)
                if scaled.size[0] <= canonical_size[0] and scaled.size[1] <= canonical_size[1]:
                    pad_image(scaled, canonical_size, pi['outpath'])
                    modified_pages[pagetrack] = ('padded', scaled.size, 'scaled', scale_factor)
                else:
                    scaled.save(pi['outpath'])
                    modified_pages[pagetrack] = ('scaled', scale_factor)
                                     
    note(3, "modified pages is %s", modified_pages)
                    
    return (monochrome_pagecount, paletted_pagecount, fullcolor_pagecount, pageno - 1, blank_pages, modified_pages)

def old_check_repository (repository):
    note(4, "Calling check_repository in addDocument.py on [%s]", repository)
    try:
        ping_host = 'https://%s:%s/ping' % repository
        note(4, "Attempting to ping %s", ping_host)
        fp = urllib.urlopen(ping_host)
        fp.close()
        note(4, "Ping was successful")
    except IOError, x:
        raise ConnectionError(repository[0], repository[1])
    except socket.sslerror, x:
        raise ConnectionError(repository[0], repository[1])

def submit_to_repository (repository, password, directory, metadata=(), cookie=None):

    # create tar of the folder
    tmpfilename = mktempfile()
    try:
        if TRANSFER_FORMAT == 'zipped-folder':
            zipup(directory, tmpfilename)
        elif TRANSFER_FORMAT == 'tarred-folder':
            cmd = TAR_CMD % (directory, TAR, tmpfilename)
            status, output, signal = subproc(cmd)
            if status != 0:
                raise Error("Command '%s' returned %d; output was\n%s" % (cmd, status, output))
        else:
            raise Error("Invalid transfer format '" + TRANSFER_FORMAT + "' specified.")

        if cookie is not None:
            cookies = (cookie,)
        else:
            cookies = None

        # send it to the repository
        note(2, "About to submit the fully processed document to repository %s %s %s" % (repository[2], repository[0], repository[1]))
        try:
            if repository[2]=="https":
                errcode, errmsg, headers, text = https_post_multipart(
                    repository[0], repository[1], password,
                    "/action/externalAPI/upload_document",
                    (("password", password),
                     ("filetype", TRANSFER_FORMAT)) + metadata,
                    (("newfile", tmpfilename),),
                    cookies=cookies, certfile=UPLIB_CLIENT_CERT)
            else:
                errcode, errmsg, headers, text = http_post_multipart(
                    repository[0], repository[1], password,
                    "/action/externalAPI/upload_document",
                    (("password", password),
                     ("filetype", TRANSFER_FORMAT)) + metadata,
                    (("newfile", tmpfilename),),
                    cookies=cookies)
        except socket.error:
            raise ConnectionError(repository[0], repository[1])

        if errcode == 401:
            raise AuthenticationError(repository[0], repository[1], password)

        elif errcode != 200:
            raise Error("Posting of data to repository %s resulted in error %d (%s).\nReturned text was:\n%s" % (repository, errcode, errmsg, text))

        return text

    finally:
        if os.path.exists(tmpfilename):
            os.unlink(tmpfilename)


def do_ocr_png (png_dir, contents_path, xdoc=false, dpi=None, modified_pages=None):

    rotated_temp_files = []

    def rotate_back(pagefile):
        pfname = os.path.split(pagefile)[1]
        if modified_pages is not None and pfname in modified_pages and modified_pages[pfname][0] == 'rotated':
            tfname = mktempfile() + ".png"
            Image.open(pagefile).rotate(-modified_pages[pfname][1]).save(tfname)
            rotated_temp_files.append(tfname)
            note(3, "  unrotating %s by %s degrees to %s", pfname, -modified_pages[pfname][1], tfname)
            return tfname
        else:
            return pagefile            

    # send it to the OCR service
    msoffice = false
    if MSOFFICE_OCR_WEB_SERVICE_URL:
        msoffice = true
        ocr_host, ocr_port, ocr_path = parse_URL(MSOFFICE_OCR_WEB_SERVICE_URL)
        note(3, "... using MS Office OCR service at %s", MSOFFICE_OCR_WEB_SERVICE_URL)
    elif XDOC_OCR_WEB_SERVICE_URL and xdoc:
        ocr_host, ocr_port, ocr_path = parse_URL(XDOC_OCR_WEB_SERVICE_URL)
        note(3, "... using XDOC-capable OCR service at %s", XDOC_OCR_WEB_SERVICE_URL)
    else:
        ocr_host, ocr_port, ocr_path = parse_URL(OCR_WEB_SERVICE_URL)
        note(3, "... using standard OCR service at %s", OCR_WEB_SERVICE_URL)
    tfilename = mktempfile()
    try:
        zipup(png_dir, tfilename, FILEFUNC=rotate_back)
        opts = (("filetype", "application/x-zipped-png-page-images"),)
        if xdoc and (not msoffice) and XDOC_OCR_WEB_SERVICE_URL:
            opts = opts + (("xdoc", "1"),)
        if dpi:
            opts = opts + (("dpi", str(dpi)),)
        errcode, errmsg, headers, text = http_post_multipart(ocr_host, ocr_port, None, ocr_path,
                                                             opts, (("file", tfilename),))
        if errcode == 200:
            if msoffice:
                tfile2 = mktempfile()
                try:
                    fp = open(tfile2, 'w')
                    fp.write(text)
                    fp.close()
                    PDFToTextWordboxesParser(None, os.path.split(contents_path)[0],
                                             wbb_version=BBOXES_FORMAT_VERSION_TO_CREATE).process_wordboxes(tfile2)
                finally:
                    if os.path.exists(tfile2):
                        if OCR_DEBUG:
                            note("pseudo-pdftotext wordboxes file is in %s", tfile2)
                        else:
                            os.unlink(tfile2)
            elif xdoc and XDOC_OCR_WEB_SERVICE_URL:
                import uplib.xdocParser as xdocParser
                tfile2 = mktempfile()
                fp = open(tfile2, 'w')
                try:
                    if OCR_DEBUG:
                        xdoc_tmpfile = mktempfile()
                        fp2 = open(xdoc_tmpfile, "wb")
                        fp2.write(text)
                        fp2.close()
                        note("XDOC output is in %s", xdoc_tmpfile)
                    if dpi:
                        if (dpi < 200 or dpi > 400):
                            pages = xdocParser.parse_XDOC_file(StringIO.StringIO(text), fp, ppi=300)
                        else:
                            pages = xdocParser.parse_XDOC_file(StringIO.StringIO(text), fp, dpi)
                    else:
                        pages = xdocParser.parse_XDOC_file(StringIO.StringIO(text), fp)
                    fp.close()
                    PDFToTextWordboxesParser(None, os.path.split(contents_path)[0],
                                             wbb_version=BBOXES_FORMAT_VERSION_TO_CREATE).process_wordboxes(tfile2)
                finally:
                    if os.path.exists(tfile2):
                        if OCR_DEBUG:
                            note("pseudo-pdftotext wordboxes file is in %s", tfile2)
                        else:
                            os.unlink(tfile2)
            else:
                f = open(contents_path, "wb")
                f.write(string.replace(text, "\r\n", "\n"));
                f.close()
        else:
            note(3, "OCR failed with error code %s, and error message <%s>", errcode, errmsg)
            raise Error("OCR failed with error message \"" + errmsg + "\"")
    finally:
        if os.path.exists(tfilename):
            if OCR_DEBUG:
                note("zipped page images are in %s", tfilename)
            else:
                os.unlink(tfilename)
        for filename in rotated_temp_files:
            os.unlink(filename)


def do_ocr_tiff (tiff_file, contents_path, xdoc=false):

    # send it to the OCR service
    if XDOC_OCR_WEB_SERVICE_URL and xdoc:
        ocr_host, ocr_port, ocr_path = parse_URL(XDOC_OCR_WEB_SERVICE_URL)
        note(3, "... using XDOC-capable OCR service at %s", XDOC_OCR_WEB_SERVICE_URL)
    else:
        ocr_host, ocr_port, ocr_path = parse_URL(OCR_WEB_SERVICE_URL)
        note(3, "... using standard OCR service at %s", OCR_WEB_SERVICE_URL)
    opts = (("filetype", "image/tiff"),)
    if xdoc and XDOC_OCR_WEB_SERVICE_URL:
        opts = opts + (("xdoc", "1"),)
    errcode, errmsg, headers, text = http_post_multipart(ocr_host, ocr_port, None, ocr_path,
                                                         opts, (("file", tiff_file),))
    if errcode == 200:
        if xdoc and XDOC_OCR_WEB_SERVICE_URL:
            import uplib.xdocParser as xdocParser
            pages = xdocParser.parse_XDOC_input(text)
            tfile2 = mktempfile()
            try:
                fp = open(tfile2, 'w')
                for page in pages:
                    page.wordbox_lines(fp)
                    fp.write("\f\n")
                fp.close()
                PDFToTextWordboxesParser(None, os.path.split(contents_path)[0],
                                         wbb_version=BBOXES_FORMAT_VERSION_TO_CREATE).process_wordboxes(tfile2)
            finally:
                if os.path.exists(tfile2):
                    os.unlink(tfile2)
        else:
            f = open(contents_path, "wb")
            f.write(string.replace(text, "\r\n", "\n"));
            f.close()
    else:
        note(3, "OCR failed with error code %s, and error message <%s>", errcode, errmsg)
        raise Error("OCR failed with error message \"" + errmsg + "\"")


def convert_tiff_to_png (tiff_file, png_directory):

    note(3, "converting TIFF file '%s' to PNG...", tiff_file)
    tmpdir = tempfile.mktemp()
    try:
        from PIL import Image
        os.mkdir(tmpdir)
        tiffmaster = os.path.join(tmpdir, "master.tiff")
        split_command = (TIFF_SPLIT_CMD
                         % (TIFFCP, tiff_file, tiffmaster,
                            TIFFSPLIT, tiffmaster, os.path.join(tmpdir, "x")))
        status, output, tsignal = subproc(split_command)
        if status != 0: raise Error ("'%s' signals non-zero exit status %d in %s => %s" %
                                     (split_command, tiff_file, tmpdir))
        counter = 1
        tiff_files = os.listdir(tmpdir)
        tiff_files.sort()
        for file in tiff_files:
            if file[0] == 'x':
                Image.open(os.path.join(tmpdir, file)).save(os.path.join(png_directory, "page%05d.png" % counter), 'PNG')
                counter = counter + 1
    finally:
        if os.path.isdir(tmpdir): shutil.rmtree(tmpdir)


############################################################
###
###  Mixin for pdftotext wordboxes support
###
###  To complicate things, there are two versions of the output.
###  In version 1, field 6 (parts[5]) is the font-size;
###  while in version 2, field 6 is a string naming the font.
###  So we have to test field 6 to see what we've got.
###
##################################################################

import sys, os, string, re, codecs, struct

class PDFToTextWordboxesLineParser:
    def __init__(self, line):
        parts = string.split(line)
        # sys.stderr.write("parts are " + str(parts) + "\n")
        if '.' in parts[8]:
            self.version = 3
        elif '.' in parts[6]:
            self.version = 2
        else:
            try:
                self.font_size = float(parts[5])
                self.version = 1
            except:
                self.version = 2
        if self.version == 1:
            self.ul = (float(parts[0]), float(parts[1]),)
            self.lr = (float(parts[2]), float(parts[3]),)
            self._baseline = float(parts[3])
            self.rotation = 0
            self.font_type = int(parts[4])
            self.font_name = "*"
            self.font_size = float(parts[5])
            self.fixed_width = (int(parts[6])!=0)
            self.serif = (int(parts[7])!=0)
            self.symbolic = (int(parts[8])!=0)
            self.italic = (int(parts[9])!=0)
            self.bold = (int(parts[10])!=0)
            self.inserted_hyphen = (int(parts[11])!=0)
            self.space_follows = (int(parts[12])!=0)
            self.newline = (int(parts[13])!=0)
            self.char_count = int(parts[14])
            self.chars = []
            for i in range(self.char_count):
                self.chars.append(unichr(int(parts[i+15])))
            word = string.join(self.chars, '')
            # remove ligatures
            self.word = unicodedata.normalize('NFKC', word)
            self.char_count = len(self.word)
        elif self.version == 2:
            self.ul = (float(parts[0]), float(parts[1]),)
            self.lr = (float(parts[2]), float(parts[3]),)
            self._baseline = float(parts[3])
            self.rotation = 0
            self.font_type = int(parts[4])
            self.font_name = parts[5]
            self.font_size = float(parts[6])
            self.fixed_width = (int(parts[7])!=0)
            self.serif = (int(parts[8])!=0)
            self.symbolic = (int(parts[9])!=0)
            self.italic = (int(parts[10])!=0)
            self.bold = (int(parts[11])!=0)
            self.inserted_hyphen = (int(parts[12])!=0)
            self.space_follows = (int(parts[13])!=0)
            self.newline = (int(parts[14])!=0)
            self.char_count = int(parts[15])
            self.chars = []
            for i in range(self.char_count):
                self.chars.append(unichr(int(parts[i+16])))
            word = string.join(self.chars, '')
            # remove ligatures
            self.word = unicodedata.normalize('NFKC', word)
            self.char_count = len(self.word)
        elif self.version == 3:
            self.ul = (float(parts[0]), float(parts[1]),)
            self.lr = (float(parts[2]), float(parts[3]),)
            self._baseline = float(parts[4])
            self.rotation = int(parts[5])
            self.font_type = int(parts[6])
            self.font_name = parts[7]
            self.font_size = float(parts[8])
            self.fixed_width = (int(parts[9])!=0)
            self.serif = (int(parts[10])!=0)
            self.symbolic = (int(parts[11])!=0)
            self.italic = (int(parts[12])!=0)
            self.bold = (int(parts[13])!=0)
            self.inserted_hyphen = (int(parts[14])!=0)
            self.space_follows = (int(parts[15])!=0)
            self.newline = (int(parts[16])!=0)
            self.char_count = int(parts[17])
            self.chars = []
            for i in range(self.char_count):
                self.chars.append(unichr(int(parts[i+18])))
            word = string.join(self.chars, '')
            # remove ligatures
            self.word = unicodedata.normalize('NFKC', word)
            self.char_count = len(self.word)

    def left (self):
        return self.ul[0]

    def top (self):
        return self.ul[1]

    def bottom (self):
        return self.lr[1]

    def right (self):
        return self.lr[0]

    def baseline (self):
        return self._baseline

    def width (self):
        return (self.lr[0] - self.ul[0])

    def height (self):
        return (self.lr[1] - self.ul[1])

    def text (self):
        return self.word

class Line:
    def __init__(self):
        self.words = []
        # these units are in PIL coordinates -- upper left corner is 0,0
        self.left = 999999
        self.right = -1
        self.top = 99999
        self.bottom = -1
        self.lastleft = 99999
        self.baseline = 0
        self.width = 0
        self.height = 0
        self._word_width_accum = 0

    def y_overlaps (self, other):
        return ((self.top < other.bottom) and (other.top < self.bottom))

    def x_overlaps (self, other):
        return ((self.left < other.right) and (other.left < self.right))

    def add(self, wordbox):
        self.words.append(wordbox)
        if self.left > wordbox.left():
            self.left = wordbox.left()
        if self.right < wordbox.right():
            self.right = wordbox.right()
        if self.top > wordbox.top():
            self.top = wordbox.top()
        if self.bottom < wordbox.bottom():
            self.bottom = wordbox.bottom()
        if self.baseline < wordbox.baseline():
            self.baseline = wordbox.baseline()
        self.width = self.right - self.left
        self.height = self.bottom - self.top
        self._word_width_accum += wordbox.width()

def _breuel_sort_lines (p1, p2, alllines):

    # Applying only two ordering criteria turns out to be sufficient to define
    # partial orders suitable for determining reading order in a wide
    # variety of documents:

    # 1. Line segment a comes before line segment b if their ranges of
    # x-coordinates overlap and if line segment a is above line segment b on
    # the page.

    # 2. Line segment a comes before line segment b if a is entirely to the
    # left of b and if there does not exist a line segment c whose
    # y-coordinates are between a and b and whose range of x coordinates
    # overlaps both a and b.

    if (p1.x_overlaps(p2) and (p1.top < p2.top)):
        return True
    if (p1.right < p2.left):
        if (p1.top < p2.top):
            cp1, cp2 = p1, p2
        else:
            cp1, cp2 = p2, p1
            # see if there's a "c" paragraph
        for c in alllines:
            if (c is cp1 or c is cp2):
                continue
            if ((c.top < cp2.top) and (c.bottom > cp1.bottom) and c.x_overlaps(cp1) and c.x_overlaps(cp2)):
                return False
        return True
    return False

class PDFToTextWordboxesParser:

    def __init__(self, pdffile, directory, pages_to_skip=None, wbb_version=None):
        self.pdffile = pdffile
        self.directory = directory
        self.pages_to_skip = pages_to_skip
        self.version = ((wbb_version is None) and 2) or wbb_version
        if self.version == 2:
            self.boxlen = 28
        elif self.version == 1:
            self.boxlen = 24
        else:
            raise ValueError("Invalid wbb format %s specified" % repr(wbb_version))

    def do_wordboxes (self):
        tfilepath = tempfile.mktemp()
        cmd = WORDBOXES_PDFTOTEXT_COMMAND % (WORDBOXES_PDFTOTEXT, self.pdffile, tfilepath)
        note(3, "running '%s' to extract the text (with wordboxes)...", cmd)
        try:
            status, output, signal = subproc(cmd)
            if status == 0:
                self.process_wordboxes (tfilepath)
        finally:
            if os.path.exists(tfilepath):
                os.unlink(tfilepath)

    def flush_page (self, page_no, bboxes, bbox_outfile, contents_outfile, contents_offset):

        def bool_to_int (bool):
            if (bool):
                return 1
            else:
                return 0

        note(4, "    page %d:  %d word bboxes", page_no, len(bboxes))

        if page_no > 0:
            contents_outfile.write(u"\f\n")
            bbox_outfile.write(self.boxlen * struct.pack("B", 0))

        last_written = ''
        for b in bboxes:

            # weed out words which consist solely of control characters
            if not sum([(ord(c) >= 0x20) for c in b.word]):
                continue

            contents_outfile.flush()
            contents_position = contents_outfile.tell() - contents_offset

            if b.inserted_hyphen and b.newline:
                fragment = b.word[:-1]
            elif b.newline:
                # started a new line or column?
                fragment = b.word + u'\n'
            elif b.space_follows:
                fragment = b.word + u' '
            else:
                fragment = b.word

            if len(fragment) > 0:
                # use normalize to re-compose any de-composed accents
                normalized_fragment = unicodedata.normalize("NFC", fragment)
                contents_outfile.write(normalized_fragment)
                last_written = fragment[-1]

            if self.version == 2:
                bbox_outfile.write(struct.pack(">BBBBfffffI",
                                               (b.char_count & 0xFF),
                                               ((b.rotation << 6)  + b.font_type) & 0xFF,
                                               (int(b.font_size * 2) & 0xFF),
                                               ((bool_to_int(b.fixed_width) << 7) |
                                                (bool_to_int(b.serif) << 6) |
                                                (bool_to_int(b.symbolic) << 5) |
                                                (bool_to_int(b.italic) << 4) |
                                                (bool_to_int(b.bold) << 3) |
                                                (bool_to_int(b.newline) << 2) |
                                                (bool_to_int(b.space_follows) << 1) |
                                                bool_to_int(b.inserted_hyphen)),
                                               b.ul[0], b.ul[1],
                                               b.lr[0], b.lr[1],
                                               b.baseline(),
                                               contents_position))
            elif self.version == 1:
                bbox_outfile.write(struct.pack(">BBBBffffI",
                                               (b.char_count & 0xFF),
                                               b.font_type & 0xFF,
                                               (int(b.font_size * 2) & 0xFF),
                                               ((bool_to_int(b.fixed_width) << 7) |
                                                (bool_to_int(b.serif) << 6) |
                                                (bool_to_int(b.symbolic) << 5) |
                                                (bool_to_int(b.italic) << 4) |
                                                (bool_to_int(b.bold) << 3) |
                                                (bool_to_int(b.newline) << 2) |
                                                (bool_to_int(b.space_follows) << 1) |
                                                bool_to_int(b.inserted_hyphen)),
                                               b.ul[0], b.ul[1],
                                               b.lr[0], b.lr[1],
                                               contents_position))

        if last_written != u'\n':
            contents_outfile.write(u'\n')


    def blank_or_comment (self, line):
        l = line.strip()
        return ((not l) or (l[0] == '#'))

    def process_wordboxes (self, infilepath):

        global DEFAULT_LANGUAGE

        note(2, "Extracting wordbboxes and contents.txt, dropped pages are %s...", self.pages_to_skip)
        infile = file(infilepath, "r")
        wordbboxes_filename = os.path.join(self.directory, "wordbboxes")
        note(2, "Creating file %s" % wordbboxes_filename)
        bbox_outfile = file(wordbboxes_filename, "wb")
        bbox_outfile.write("UpLib:wbb:%d\0" % self.version)
        contents_outfile = codecs.open(os.path.join(self.directory, "contents.txt"), 'wb', 'utf_8')
        contents_outfile.write(u'Content-Type: text/plain; charset=utf8\n')
        contents_outfile.write(u'Content-Language: %s\n' % DEFAULT_LANGUAGE)
        contents_outfile.flush()
        contents_offset = contents_outfile.tell()

        note(4, "pages_to_skip is %s", self.pages_to_skip)

        bboxes = []
        in_page = 0
        out_page = 0

        for line in infile:

            if line == u'\f\n':
                # pagebreak
                if (self.pages_to_skip and ((in_page + 1) in self.pages_to_skip)):
                    note(3, "skipping dropped page %s", in_page)
                else:
                    self.flush_page (out_page, bboxes, bbox_outfile, contents_outfile, contents_offset)
                    out_page += 1
                bboxes = []
                in_page += 1
                continue
            elif self.blank_or_comment(line):
                # empty or comment line
                note(3, "empty or comment line %s in %s skipped", repr(line.strip()), infilepath)
                continue
            else:
                bboxes.append(PDFToTextWordboxesLineParser(line))

        if bboxes:
            if not (self.pages_to_skip and (in_page + 1) in self.pages_to_skip):
                self.flush_page (out_page, bboxes, bbox_outfile, contents_outfile, contents_offset)

        contents_outfile.close()
        bbox_outfile.close()
        infile.close()

############################################################
###
###  cache_page_one
###
###  Watch the specified images DIRECTORY for a file called
###  "page00001.png", and when it appears, make a thumbnail
###  of it and put it in ICON_FILE.
###
############################################################

def cache_page_one (directory, icon_file):

    def make_simple_page_thumbnail(big_image_file, thumbnail_image_file, size=None):

        if size is None:
            size = (200, 200)
        im = Image.open(os.path.join(big_image_file))
        if im.mode == 'L' or im.mode == '1' or im.mode == 'P':
            im = im.convert('RGB')
        width, height = im.size
        if (width > height):
            scaling_factor = size[0] / float(width)
        else:
            scaling_factor = size[1] / float(height)
        newsize = (int(width * scaling_factor), int(height * scaling_factor))
        im2 = im.resize(newsize, Image.ANTIALIAS)
        im2.save(thumbnail_image_file, "PNG")

    try:
        imagepath = os.path.join(directory, "page00001.png")
        note(4, "watching %s for page 1...", directory)
        while os.path.exists(directory):
            if os.path.exists(imagepath):
                # do the image processing
                note(4, "...page 1 available, making icon...")
                time.sleep(1)
                make_simple_page_thumbnail(imagepath, icon_file)
                note(4, "...icon finished.")
                break
            else:
                time.sleep(1)
    except:
        note("Exception making page thumbnail:  %s", string.join(traceback.format_exception(*sys.exc_info())))

############################################################
###
###  The master DocumentParser class
###
############################################################

class DocumentParser (object):

    def __init__(self, doc, options):
        self.folder = create_new_folder(AssemblyLine)
        os.chmod(self.folder, 0700)
        self.doc = doc
        note(1, "Using parser '%s' for %s...", self.__class__.__name__, doc)
        self.uses_png = options.get("usepng", false)
        self.repository = options.get("repository", None)
        self.password = options.get("password", None)
        self.notext = options.get("notext", false)
        self.color = options.get("color", true)
        self.upload = options.get("upload", true)
        self.metadata = {}
        if options.get("metadata"):
            self.metadata.update(options.get("metadata"))
        self.saveblanks = options.get("saveblanks", false)
        self.optimize = options.get("optimize", true)
        self.early_upload = options.get("early_upload", false)
        self.deskew = options.get("deskew", false)
        self.dryclean = options.get("dryclean", false)
        self.checkocr = options.get("checkocr", true)
        self.icon_file = options.get("icon_file", None)
        self.ocr = options.get("ocr", false)
        self.cookie = options.get("cookie", None)
        self.upload_id = None

    def __str__(self):
        return "<%s|%s|%s>" % (self.__class__.__name__, self.doc, self.folder)

    def sort_parsers (parser_list):

        def _sort_fn(p1, p2, allparsers):
            if hasattr(p1, 'BEFORE') and ((p2 in p1.BEFORE) or (p2.__name__ in p1.BEFORE)):
                return True
            if hasattr(p2, 'AFTER') and ((p1 in p2.AFTER) or (p1.__name__ in p2.AFTER)):
                return True
            return False

        return topological_sort (parser_list, _sort_fn)

    sort_parsers=staticmethod(sort_parsers)

    def find_parsers_in_dict (mod_dict):
        items = mod_dict.values()
        mod_name = mod_dict.get("__name__")
        parsers = list()
        for item in items:
            if (type(item) == type(DocumentParser) and
                issubclass(item, DocumentParser) and
                item.__dict__.has_key("myformat")):
                note(4, "  adding parser %s", repr(item))
                parsers.append(item)
        return parsers
    find_parsers_in_dict=staticmethod(find_parsers_in_dict)

    def find_parsers_in_file (file, mname_prefix=None):

        if not os.path.exists(file):
            note("No parsers in non-existent parser file %s", file)
            return []

        f = None
        directory, filepath = os.path.split(file)
        if filepath == "__init__.py":
            # package
            directory, filepath = os.path.split(directory)
            mname, fileext = filepath, ''
        else:
            mname, fileext = os.path.splitext(filepath)
        try:
            try:
                f, pathname, description = imp.find_module(mname, [directory,])
                imp.new_module(mname)
                mod = imp.load_module(mname, f, pathname, description)
                parsers = DocumentParser.find_parsers_in_dict(mod.__dict__)
                return parsers
            except MissingResource, x:
                note("skipping %s; %s", file, x)
                return []
            except Exception, x:
                note("can't load file %s; %s", file, x)
                return []
        finally:
            if f: f.close()
    find_parsers_in_file=staticmethod(find_parsers_in_file)

    def find_parsers(file_list=[]):

        # static method to return a list of all the parser classes that
        # actually process documents

        note(4, "finding the parsers, file list is %s...", file_list)

        def findParserClasses (mod_dict, parsers):
            parsers.extend(DocumentParser.find_parsers_in_dict(mod_dict))
            sorted = DocumentParser.sort_parsers(parsers)
            parsers[:] = []
            parsers.extend(sorted)
            
        global PARSERS
        if not PARSERS:
            note(4, "finding standard parsers from addDocument module globals...")
            findParserClasses(globals(), PARSERS)
            try:
                import uplib.emailParser
                note(4, "finding email parsing classes...")
                findParserClasses(uplib.emailParser.__dict__, PARSERS)
            except ValueError, x:
                note(2, "No email support:  " + str(x))
            except ImportError, x:
                note(2, "No email support:  " + str(x))

            try:
                import uplib.music
                note(4, "finding music parsing classes...")
                findParserClasses(uplib.music.__dict__, PARSERS)
            except ValueError, x:
                note(2, "No music support:  " + str(x))
            except ImportError, x:
                note(2, "No music support:  " + str(x))

            try:
                import uplib.jpeg2000
                note(4, "finding JPEG 2000 parsing classes...")
                findParserClasses(uplib.jpeg2000.__dict__, PARSERS)
            except ValueError, x:
                note(2, "No JPEG 2000 support:  " + str(x))
            except ImportError, x:
                note(2, "No JPEG 2000 support:  " + str(x))

            try:
                import uplib.macstuff
                note(4, "finding Mac parsing classes...")
                findParserClasses(uplib.macstuff.__dict__, PARSERS)
            except ValueError, x:
                note(2, "No Mac support:  " + str(x))
            except ImportError, x:
                note(2, "No Mac support:  " + str(x))

        # now look at site-extensions that may contain parsers
        note(4, "finding parsers in site extensions...")
        edir = os.path.join(UPLIB_LIBDIR, "site-extensions")
        if os.path.exists(edir):
            new_parsers = list()
            for file in os.listdir(edir):
                if file.endswith(".py"):
                    new_parsers.extend(DocumentParser.find_parsers_in_file(os.path.join(edir, file), "_site_extension_"))
                elif os.path.exists(os.path.join(edir, file, "__init__.py")):
                    new_parsers.extend(DocumentParser.find_parsers_in_file(os.path.join(edir, file), "_site_extension_"))
            PARSERS.extend(new_parsers)

        # now look at files that contain user-specified parsers
        note(4, "finding user-specified parsers...")
        new_parsers = list()
        for file in file_list:
            if os.path.exists(file):
                if os.path.isfile(file):
                    new_parsers.extend(DocumentParser.find_parsers_in_file(file, "_user_specified_"))
                elif os.path.isdir(file) and os.path.isfile(os.path.join(file, "__init__.py")):
                    new_parsers.extend(DocumentParser.find_parsers_in_file(os.path.join(file, "__init__.py"), "_user_specified_"))
        PARSERS.extend(new_parsers)
        PARSERS[:] = DocumentParser.sort_parsers(PARSERS)
        note(4, "finished with find_parser")

        #import pprint
        #note(3, "parsers are:\n%s\n", pprint.pformat(PARSERS))

        return PARSERS

    find_parsers = staticmethod(find_parsers)

    def add_parser (p):
        PARSERS.append(p)
        PARSERS[:] = DocumentParser.sort_parsers(PARSERS)
        note(4, "added parser %s", p)
    add_parser = staticmethod(add_parser)        

    def list_formats():

        # static method to return a list of all supported MIME types

        if not PARSERS:
            DocumentParser.find_parsers()
        l = []
        for parser in PARSERS:
            if not parser.format_mimetype:
                note(2, "parser %s doesn't declare mimetype!", parser)
            else:
                l.append(parser)
        return l
    list_formats = staticmethod(list_formats)

    def parse_document (doc, resultslist, **options):

        # core method to parse a document.  Takes a pathname (doc),
        # optionally a list to add the results to, and a number of
        # keyword arguments.

        while (options.has_key("options")):
            options = options.get("options")
        if not PARSERS:
            DocumentParser.find_parsers()
        note(5, 'Sorted parser list is %s', PARSERS)
        parser = None
        pname = options.get("format")
        if pname:
            matches = [x for x in PARSERS if (x.__name__ == pname)]
            if matches:
                parser = matches[0]
        else:
            note(4, "no format specified, looking at all of them...")
        if not parser:
            for x in PARSERS:
                note(4, "trying %s...", x)
                v = x.myformat(doc)
                note(4, "trying %s on %s returns %s", x, doc, v)
                if v:
                    parser = x
                    if (type(v) == types.DictType):
                        options.update(v)
                    break
        if parser:
            try:
                note(4, "Using parser %s on %s", parser, doc)
                result = parser(doc, options).process()
            except Error:
                t, v, b = sys.exc_info()
                note(3, "Parse of %s raises Exception:\n%s", doc, format_exception())
                result = v
            if resultslist is not None:
                if isinstance(result, list):
                    resultslist += result
                elif isinstance(result, DocumentParser):
                    resultslist.append((doc, result))
                return resultslist
            else:
                if isinstance(result, list):
                    return result
                else:
                    return [(doc, result,)]
        elif os.path.isdir(doc):
            # look at the files in the directory, recursively
            if resultslist is not None:
                results = resultslist
            else:
                results = list()
            files = os.listdir(doc)
            for file in files:
                if file[0] == '.' or file[-1] == '~':
                    continue
                filepath = os.path.join(doc, file)
                DocumentParser.parse_document(filepath, results, options=options)
            return results or [(doc, None,)]
        elif resultslist is not None:
            return resultslist
        else:
            return [(doc, None)]
    parse_document = staticmethod(parse_document)

    def text_path (self):

        # returns the pathname to the text file
        
        return os.path.join(self.folder, "contents.txt")

    def links_dir_path (self):

        # returns the pathname to the directory where links are kept
        
        return os.path.join(self.folder, "links")

    def document_links_path (self):

        # returns the pathname to the file of links extracted from the document
        
        return os.path.join(self.links_dir_path(), "document.links")

    def word_boxes_path (self):

        # returns the pathname to the word boxes file
        
        return os.path.join(self.folder, "wordbboxes")

    def images_path (self):

        # returns the pathname to the page-images file

        return os.path.join(self.folder, (self.uses_png and "page-images") or "document.tiff")

    def summary_path (self):

        # returns the pathname to the summary file

        return os.path.join(self.folder, "summary.txt")

    def originals_path (self):

        # returns the pathname to the originals directory

        return os.path.join(self.folder, "originals")

    def metadata_path (self):

        # returns the pathname to the metadata file

        return os.path.join(self.folder, "metadata.txt")

    def update_md (self, data):

        # updates the metadata of the object with the dict "data"
        
        self.metadata.update(data)

    def get_page_images (self):

        # called to create the page images of the document.
        # Subclasses should implement this.

        pass

    def get_text (self):

        # called to get the text of the document.  By default, calls OCR.
        # Subclasses should override this if they care.

        textpath = self.text_path()
        if (not (os.path.exists(textpath) or self.notext)) and self.ocr:
            note(3, "OCR'ing in %s", self.folder)
            try:
                if self.uses_png:
                    ppi = int(self.metadata.get("images-dpi", "300"))
                    do_ocr_png(self.images_path(), textpath, true, dpi=ppi,
                               modified_pages=eval(self.metadata.get('modified-pages', 'None')))
                else:
                    do_ocr_tiff(self.images_path(), textpath, true)
            except:
                t, v, b = sys.exc_info()
                note("OCR raised exception:\n%s", string.join(traceback.format_exception(t, v, b)))
                note("No text added.")
        if not os.path.exists(textpath):
            # create empty file
            f = open(textpath, "wb")
            f.write("Content-Type: text/plain; charset=utf8\n"
                    "Content-Language: %s\n" % DEFAULT_LANGUAGE)
            f.flush()
            f.close()

    def create_summary (self):

        # called to create a summary of the document.

        textpath = self.text_path()
        summarypath = self.summary_path()

        if os.path.exists(textpath):
            text = read_file_handling_charset(textpath)
            text = newline_expression.sub(' / ', text)
            text = whitespace_expression.sub(' ', text)
            while text and not text[0] in alnum_chars:
                # remove leading punctuation
                text = text[1:]
            text = text[:min(SUMMARY_LENGTH, len(text))]

            f = open(summarypath, 'wb')
            f.write(text.encode("latin_1", "replace"))
            f.close()

            self.update_md({"summary" : text})

    def copy_original(self):

        # called to copy the original file to the originals subdirectory

        originals_path = self.originals_path()
        if not os.path.exists(originals_path):
            os.mkdir(originals_path)
            os.chmod(originals_path, 0700)
        if os.path.isdir(self.doc):
            shutil.copytree(self.doc, originals_path)
        else:
            shutil.copy(self.doc, originals_path)

    def optimize_page_images(self):

        # called to optimize the compression of the page images.

        angles = None
        if self.uses_png and self.dryclean and (DRYCLEAN_SERVICE_URL != None):
            note(3, "   sending pages for drycleaning to %s...", DRYCLEAN_SERVICE_URL)
            retval = dryclean_png_page_images(self.images_path())
            note(4, "   ...reval is %s", retval)
        elif self.uses_png and self.deskew and (SKEW_DETECT_URL != None):
            note(3, "   finding page skew angles")
            angles = skew_detect_png_page_images(self.images_path())
            note(4, "   ...angles are %s", angles)
            if angles:
                angles_string = str(angles[0])
                if len(angles) > 1:
                    for angle in angles[1:]:
                        angles_string = angles_string + ":" + str(angle)
                self.update_md({"page-image-skew-angles" : angles_string})
        elif (self.deskew or self.dryclean) and not self.uses_png:
            note("deskew and dryclean services are only available for PNG page images")

        if not self.optimize:
            return

        if self.uses_png:
            note(3, "optimizing PNG page images")
            m, p, f, c, b, x = optimize_png_compression (self.images_path(), self.saveblanks, angles)
            self.metadata['monochrome-pages'] = str(m)
            self.metadata['paletted-pages'] = str(p)
            self.metadata['fullcolor-pages'] = str(f)
            self.metadata['page-count'] = str(c)
            self.metadata['dropped-pages'] = reduce (lambda x, y: x + ((x and (", " + str(y))) or str(y)), b, "")
            if x: self.metadata['modified-pages'] = str(x)
        else:
            note(3, "optimizing tiff compression")
            m, p, f, c = optimize_tiff_compression (self.images_path(), self.saveblanks)
            self.metadata['monochrome-pages'] = str(m)
            self.metadata['paletted-pages'] = str(p)
            self.metadata['fullcolor-pages'] = str(f)
            self.metadata['page-count'] = str(c)


    def extract_links (self):

        # called after get_text, but before write_metadata, to extract any hypertext links
        # the document may have.  By default, there are none.

        pass
    

    def calculate_document_fingerprint (self):

        # called to create a quick hash of the document's content

        key = calculate_originals_fingerprint(os.path.join(self.folder, "originals"))
        self.metadata["sha-hash"] = key
        return key


    def write_metadata(self):

        # called to create the metadata file

        if os.path.exists(self.metadata_path()):
            d = read_metadata(self.metadata_path())
        else:
            d = dict()
        d.update(self.metadata)
        if self.format_mimetype and not d.has_key('apparent-mime-type'):
            d['apparent-mime-type'] = self.format_mimetype
            note(3, "apparent-mime-type set to \"%s\"", self.format_mimetype)
        if not d.has_key("title"):
            if isinstance(self.doc, str):
                if not isinstance(self.doc, unicode):
                    title = unicode(self.doc, sys.getfilesystemencoding(), "strict")
                else:
                    title = self.doc
                d["title"] = title
                d["title-is-original-filepath"] = "true"
        update_metadata(self.metadata_path(), d)

    def delete_folder(self):
        # called to remove storage used by the instance
        try:
            shutil.rmtree(self.folder)
        except OSError, x:
            note(2, "delete_folder failed for %s.  Error=%s" % (self.folder, str(x)))
        if os.path.exists(self.folder):
            note(2, "delete_folder failed for %s.  Error=%s" % (self.folder, str(x)))

    def do_early_upload (self):
        if self.upload:
            temp_folder = create_new_folder(AssemblyLine)
            # originals
            originals_path = os.path.join(temp_folder, "originals");
            os.mkdir(originals_path)
            os.chmod(originals_path, 0700)
            if os.path.isdir(self.doc):
                shutil.copytree(self.doc, originals_path)
            elif os.path.exists(self.doc):
                shutil.copy(self.doc, originals_path)
            elif hasattr(self, "__cached") and os.path.exists(self.__cached):
                shutil.copytree(self.__cached, originals_path)
            else:
                print dir(self)
                raise ValueError("Don't know how to 'early upload' this kind of document:  %s" % self.doc)
            # metadata
            temp_metadata = {}
            temp_metadata.update(self.metadata)
            if self.format_mimetype:
                temp_metadata['apparent-mime-type'] = self.format_mimetype
            temp_metadata["temporary-contents"] = "true"
            update_metadata(os.path.join(temp_folder, "metadata.txt"), temp_metadata)
            # page-images
            images_path = os.path.join(temp_folder, "page-images")
            im = Image.new("1", (2550, 3300))
            os.mkdir(images_path)
            im.save(os.path.join(images_path, "page00001.png"), "PNG")
            # contents.txt
            fp = open(os.path.join(temp_folder, "contents.txt"), "w", 0600)
            fp.flush()
            fp.close()
            # now do the submit
            upload_metadata = []
            if 'id' in self.metadata:
                upload_metadata.append(("id", htmlescape(self.metadata.get('id')),))
            id = submit_to_repository(self.repository, self.password, temp_folder, tuple(upload_metadata),
                                      cookie=self.cookie)
            # on success, remove the temp folder, save the id
            shutil.rmtree(temp_folder)
            self.metadata["replacement-contents-for"] = id
            return id

    def process(self):
        # DocumentParser.process()
        # called to process the document.  Calls the other stages.
#         code_timer.CreateTable("uplib")
#         if CODETIMER_ON:
#             code_timer.CodeTimerOn()
#         else:
#             code_timer.CodeTimerOff()
#         code_timer.StartInt("DocumentParser.process", "uplib")

        note(2, "processing %s with %s parser...", self.doc, self.__class__.__name__)
        try:
            id = None
            #code_timer.StartInt("DocumentParser.process$copy_original", "uplib")
            self.copy_original()
            #code_timer.StopInt("DocumentParser.process$copy_original", "uplib")
            #code_timer.StartInt("DocumentParser.process$calculate_document_fingerprint", "uplib")
            self.calculate_document_fingerprint()
            #code_timer.StopInt("DocumentParser.process$calculate_document_fingerprint", "uplib")
            #code_timer.StartInt("DocumentParser.process$get_page_images", "uplib")
            if self.early_upload:
                id = self.do_early_upload()
            if self.icon_file:
                uthread.start_new_thread(cache_page_one, (self.images_path(), self.icon_file))
            self.get_page_images()
            #code_timer.StopInt("DocumentParser.process$get_page_images", "uplib")
            #code_timer.StartInt("DocumentParser.process$optimize_page_images", "uplib")
            self.optimize_page_images()
            if os.path.exists(self.images_path()): os.chmod(self.images_path(), 0700)
            #code_timer.StopInt("DocumentParser.process$optimize_page_images", "uplib")
            #code_timer.StartInt("DocumentParser.process$get_text", "uplib")
            self.get_text()
            if os.path.exists(self.text_path()): os.chmod(self.text_path(), 0700)
            #code_timer.StopInt("DocumentParser.process$get_text", "uplib")
            #code_timer.StartInt("DocumentParser.process$create_summary", "uplib")
            self.create_summary()
            if os.path.exists(self.summary_path()): os.chmod(self.summary_path(), 0700)
            #code_timer.StopInt("DocumentParser.process$create_summary", "uplib")
            #code_timer.StartInt("DocumentParser.process$extract_links", "uplib")
            self.extract_links()
            #code_timer.StopInt("DocumentParser.process$extract_links", "uplib")
            #code_timer.StartInt("DocumentParser.process$write_metadata", "uplib")
            self.write_metadata()
            # metadata always exists, so no need to check
            os.chmod(self.metadata_path(), 0700)
            #code_timer.StopInt("DocumentParser.process$write_metadata", "uplib")
            #code_timer.StartInt("DocumentParser.process$submit_to_repository", "uplib")
            result = None
            if self.upload:
                upload_metadata = []
                if 'id' in self.metadata:
                    # we use 'htmlescape' here as a convenient way of dealing with Unicode
                    upload_metadata.append(("id", htmlescape(self.metadata.get('id')),))
                id2 = submit_to_repository(self.repository, self.password, self.folder, tuple(upload_metadata),
                                           cookie=self.cookie)
                self.delete_folder()
                if self.early_upload:
                    result = id
                else:
                    result = id2
                self.upload_id = result
            else:
                result = self
#             code_timer.StopInt("DocumentParser.process$submit_to_repository", "uplib")
#             code_timer.StopInt("DocumentParser.process", "uplib")
#             if CODETIMER_ON:
#                 noteOut = StringIO.StringIO()
#                 noteOut.write("\nCode Timer statistics (what took time, in milliseconds):\n")
#                 code_timer.PrintTable(noteOut, "uplib")
#                 noteOut.write("\n")
#                 noteOutString = noteOut.getvalue()
#                 note(3, noteOutString)
            return result
        except MultiPartDocument, x:
            if self.upload:
                self.delete_folder()
            return x.parts
        except ConnectionError:
            raise
        except AuthenticationError:
            raise
        except:
            note(3, "processing %s:\n%s" % (self, ''.join(traceback.format_exception(*sys.exc_info()))))
            raise ProcessError(self, sys.exc_info())


############################################################
###
###  Individual classes for document formats
###
############################################################

class PDFDoc (DocumentParser):

    format_mimetype = "application/pdf"
    
    def myformat(pathname):
        if not os.path.exists(pathname):
            return false
        return (PDF_EXTENSION.search(pathname) != None)
    myformat = staticmethod(myformat)

    def get_text(self):
        contentsfile = self.text_path()
        if os.path.exists(contentsfile):
            return
        if (not self.ocr) and (not self.notext):
            # do we have the version of pdftotext that knows about wordboxes?
            if WORDBOXES_PDFTOTEXT:
                d = self.metadata.get("dropped-pages")
                if d:
                    d = eval("[" + d + "]")
                PDFToTextWordboxesParser(self.doc, self.folder, d).do_wordboxes()
                # check to make sure we don't have a blank file
                if os.path.exists(contentsfile):
                    t = read_file_handling_charset(contentsfile)
                    if not string.strip(t):
                        note(3, "No contents found with PDFToTextWordboxesParser")
                        os.unlink(contentsfile)
                        self.metadata['pdf-contains-no-text'] = 'true'
            else:
                cmd = PDFTOTEXT_COMMAND % (PDFTOTEXT, self.doc)
                note(3, "running '%s' to extract the text...", cmd)
                status, output, signal = subproc(cmd)
                if status == 0:
                    contents = string.strip(output)
                    if contents:
                        f = open(contentsfile, 'wb')
                        f.write(contents)
                        f.close()
                        note(3, "extraction succeeded and contents were found (%s)" % cmd)
                    else:
                        note(3, "extraction succeeded but NO contents were found (%s)" % cmd)
                else:
                    note(3, "extraction failed (%s)" % cmd)

            # use scoretext, if available, to check the text
            if self.checkocr and os.path.exists(contentsfile) and SCORETEXT:
                note(3, "Running scoretext to evaluate generated text...")
                cmd = SCORETEXT_CMD % (SCORETEXT, SCORETEXT_MODEL, contentsfile)
                status, output, signal = subproc(cmd)
                if status == 0:
                    score = int(output)
                    note(3, "scoretext on document text returns %s (threshold is %s)", score, SCORETEXT_THRESHOLD)
                    if score > SCORETEXT_THRESHOLD or score < 0:
                        # text is no good
                        self.metadata['bad-text-from-pdftotext'] = str(score)
                        note(3, "discarding pdftotext-generated text because of high scoretext score of %s", score)
                        os.unlink(contentsfile)
                        if os.path.exists(os.path.join(self.folder, "wordbboxes")):
                            os.unlink(os.path.join(self.folder, "wordbboxes"))
            else:
                if not os.path.exists(contentsfile):
                    note(4, "Not running scoretext because contentsfile %s does not exist." % contentsfile)
                elif not self.checkocr:
                    note(4, "Not running scoretext because parser says not to.")
                elif not SCORETEXT:
                    note(4, "Not running scoretext because it's not available.")

        # finally, try the default, if necessary
        if not os.path.exists(contentsfile):
            note(5, "Unable to extract contents using PDF methods.  Trying default get_text.")
            DocumentParser.get_text(self)
        else:
            note(5, "Successfully extracted contents using PDF methods.")


    def extract_links(self):

        # extract links if we have pdflinks
        if PDFLINKS:
            note(3, "Running pdflinks to extract links...")
            linksdir = self.links_dir_path()
            if not os.path.exists(linksdir):
                os.mkdir(linksdir)
                os.chmod(linksdir, 0700)
            linksfile = self.document_links_path()
            tfile = mktempfile() + ".pdflinks"
            cmd = PDFLINKS_COMMAND % (PDFLINKS, self.doc, tfile)
            status, output, signal = subproc(cmd)
            if status != 0:
                if os.path.exists(tfile): os.unlink(tfile)
                note("Couldn't extract links:  status %s, output <%s>", status, output)
                return
            if os.path.exists(tfile):
                try:
                    d = self.metadata.get("dropped-pages")
                    if d:
                        d = eval("[" + d + "]")
                    converted, ignored = pdflinksParser.convert_pdflinks_to_uplib_links(tfile, linksfile, d)
                    note(4, "   ... %d links converted, %d links ignored", converted, ignored)
                    # os.chmod(linksfile, 0600)
                finally:
                    os.unlink(tfile)


    def write_metadata(self):

        global PDFINFO

        def get_values (text, values):
            d = dict()
            lines = text.split("\n")
            for line in lines:
                for valuename in values:
                    prefix = valuename + ": "
                    if line.startswith(prefix):
                        v = line[len(prefix):].strip()
                        if v:
                            d[valuename] = v
            return d

        if PDFINFO and (not isinstance(self, FakePDFDoc)):
            # look for title in the pdf info
            cmd = '%s "%s"' % (PDFINFO, self.doc)
            status, output, signal = subproc(cmd)
            infodict = dict()
            if status == 0:
                infodict = get_values(output, ["Title", "Author", "PDF version", "CreationDate", "Subject", "Keywords"])
                if "Title" in infodict:
                    # various word processors and converters put in useless or misdirected titles,
                    # so look for those and skip them
                    ltitle = infodict["Title"].lower()
                    if ltitle.startswith("microsoft word - "):
                        infodict["Title"] = infodict["Title"][len("microsoft word - "):]
                        ltitle = ltitle[len("microsoft word - "):]
                    if ((ltitle == "untitled document") or
                        (ltitle == "untitled") or
                        ltitle.endswith(".doc") or
                        ltitle.endswith(".dvi") or
                        ltitle.endswith(".rtf") or
                        ltitle.endswith(".ppt") or
                        ltitle.endswith(".pdf") or
                        ltitle.endswith(".qxd") or
                        ltitle.endswith(".ps")): del infodict["Title"]
                if not ("title" in self.metadata):
                    # figure something out
                    if "Title" in infodict:
                        self.metadata["title"] = infodict["Title"]
                    elif "Subject" in infodict:
                        self.metadata["title"] = infodict["Subject"]
                if (not ("keywords" in self.metadata)) and ("Keywords" in infodict):
                    self.metadata["keywords"] = infodict["Keywords"]
                if (not ("authors" in self.metadata)) and ("Author" in infodict):
                    author = infodict["Author"]
                    if author not in ("anonymous",):
                        self.metadata["authors"] = infodict["Author"]
                if "PDF version" in infodict:
                    self.metadata["pdf-version"] = infodict["PDF version"]
                if (not ("date" in self.metadata)) and ("CreationDate" in infodict):
                    import time
                    try:
                        uplibdate = time.strftime("%m/%d/%Y", time.strptime(infodict["CreationDate"], "%a %b %d %H:%M:%S %Y"))
                        self.metadata["date"] = uplibdate
                    except ValueError, x:
                        # bad date string in PDF
                        note(3, "Apparent bad timestamp in PDF file:  %s", str(x))

        # call super-method
        DocumentParser.write_metadata(self)


    def get_page_images(self):

        dirname = self.folder
        if self.uses_png:
            # create a directory filled with PNG images
            page_images_dirname = self.images_path()
            os.mkdir(page_images_dirname)
            try:
                outputfile = os.path.join(page_images_dirname, "page%05d.png")
                if self.color:
                    cmd = PDFTOPNG_CMD_COLOR % (GHOSTSCRIPT, outputfile, self.doc)
                    note(3, "Ghostscript command is <%s>", cmd)
                    status, output, signal = subproc(cmd)
                    if status != 0:
                        raise Error("can't convert PDF file %s to PNG files in %s with command\n\"%s\"\nError was:\n%s" % (self.doc, page_images_dirname, cmd, output))
                else:
                    cmd = PDFTOPNG_CMD_MONO % (GHOSTSCRIPT, outputfile, self.doc)
                    note(3, "Ghostscript command is <%s>", cmd)
                    status, output, signal = subproc(cmd)
                    if status != 0:
                        raise Error("can't convert PDF file %s to PNG files in %s with command\n\"%s\"\nError was:\n%s" % (self.doc, page_images_dirname, cmd, output))
                note(3, "created PNG files in %s", page_images_dirname)
            except:
                type, value, tb = sys.exc_info()
                if os.path.exists(page_images_dirname):
                    shutil.rmtree(page_images_dirname)
                raise value, None, tb
        else:
            # create a TIFF version
            tiff_file_name = os.path.join(dirname, "document.tiff")
            if self.color:
                cmd = PDFTOTIFF_CMD_COLOR % (GHOSTSCRIPT, tiff_file_name, self.doc)
                note(3, "Ghostscript command is <%s>", cmd)
                status, output, signal = subproc(cmd)
                if not os.path.exists(tiff_file_name):
                    raise Error("can't convert PDF file %s to TIFF file %s with command\n\"%s\"\nError was:\n%s" % (self.doc, tiff_file_name, cmd, output))
            else:
                cmd = PDFTOTIFF_CMD_MONO % (GHOSTSCRIPT, tiff_file_name, self.doc)
                note(3, "Ghostscript command is <%s>", cmd)
                status, output, signal = subproc(cmd)
                if status != 0:
                    raise Error("can't convert PDF file %s to TIFF file %s with command\n\"%s\"\nError was:\n%s" % (self.doc, tiff_file_name, cmd, output))
            note(3, "created tiff file in %s", tiff_file_name)


class TIFFDoc (DocumentParser):

    format_mimetype = "image/tiff"

    BEFORE = ('ImageDoc',)

    DATE_TIME = 0x132
    DATE_TIME_ORIGINAL_EXIF = 0x9003
    CAMERA_MAKE = 0x10F
    CAMERA_MODEL = 0x110
    RESUNIT_INCHES  = 2
    RESUNIT_CENTIMETER = 3
    TAG_RESOLUTION_UNIT = 296
    TAG_X_RESOLUTION = 282
    TAG_Y_RESOLUTION = 283

    def get_tiff_resolution(d):
        if d.has_key(TIFFDoc.TAG_RESOLUTION_UNIT) and d.has_key(TIFFDoc.TAG_X_RESOLUTION) and d.has_key(TIFFDoc.TAG_Y_RESOLUTION):
            units = d[TIFFDoc.TAG_RESOLUTION_UNIT]
            if type(units) == types.TupleType:
                units = units[0]
            if units == TIFFDoc.RESUNIT_CENTIMETER:
                multiplier = 2.54
            elif units == TIFFDoc.RESUNIT_INCHES:
                multiplier = 1
            else:
                multiplier = None
            if multiplier is not None:
                xres = d[TIFFDoc.TAG_X_RESOLUTION]
                while type(xres[0]) == types.TupleType:
                    xres = xres[0]
                xres = xres[0] / (((len(xres) > 1) and xres[1]) or 1)
                yres = d[TIFFDoc.TAG_Y_RESOLUTION]
                while type(yres[0]) == types.TupleType:
                    yres = yres[0]
                yres = yres[0] / (((len(yres) > 1) and yres[1]) or 1)
                if xres == yres:
                    return int(xres * multiplier)
        return None
    get_tiff_resolution = staticmethod(get_tiff_resolution)

    def get_tiff_date(d):
        return d.get(TIFFDoc.DATE_TIME)
    get_tiff_date = staticmethod(get_tiff_date)
        
    def get_tiff_camera_info(d):
        v = d.get(TIFFDoc.CAMERA_MAKE)
        v2 = d.get(TIFFDoc.CAMERA_MODEL)
        if (v or v2):
            return ((v and (v + " - ")) or "") + v2
        else:
            return None
    get_tiff_camera_info = staticmethod(get_tiff_camera_info)

    def check_tags (self):
        # check for TIFF tags
        from PIL import Image
        try:
            im = Image.open(self.doc)
        except:
            pass
        else:
            if hasattr(im, "tag"):
                d = im.tag
                if d:
                    v = TIFFDoc.get_tiff_date(d)
                    if v:
                        self.metadata['original-date-time'] = v
                        if not self.metadata.has_key("date"):
                            date = time.strptime(v, "%Y:%m:%d %H:%M:%S")
                            self.metadata['date'] = time.strftime("%m/%d/%Y", date)
                    v = TIFFDoc.get_tiff_camera_info(d)
                    if v:
                        self.metadata['camera-type'] = v
                    v = TIFFDoc.get_tiff_resolution(d)
                    if (not self.metadata.has_key('images-dpi')) and v:
                        self.metadata['images-dpi'] = str(v)
                        note(3, "   setting DPI to %d based on tags in TIFF file", v)

    def process (self):
        try:
            self.check_tags()
        except:
            note("Exception checking TIFF tags.  Ignored:\n%s",
                 ''.join(traceback.format_exception(*sys.exc_info())))
        return DocumentParser.process(self)

    def myformat(pathname):
        if not os.path.exists(pathname):
            return false
        if not TIFF_EXTENSION.search(pathname):
            return False
        im = Image.open(pathname)
        bytes = im.size[0] * im.size[1]
        if im.mode not in ("1", "L", "P"):
            bytes = bytes * 4  # 32-bit storage
        del im
        if bytes > IMAGE_SIZE_LIMIT:
            note("Image too large: IMAGE_SIZE_LIMIT is %s, image requires %s bytes",
                 IMAGE_SIZE_LIMIT, bytes)
            return False
        return True

    myformat = staticmethod(myformat)

    def countpages(self):
        im = Image.open(self.doc)
        count = 0
        try:
            try:
                while 1:
                    count += 1
                    im.seek(count)
            except EOFError:
                return count
        finally:
            del im
        return 0

    def get_page_images(self):

        imagespath = self.images_path()
        if self.uses_png:
            if not os.path.isdir(imagespath):
                os.mkdir(imagespath)
            # do tiff-to-png conversion
            # first, copy the tiff file and remove compression
            convert_tiff_to_png(self.doc, imagespath)
        else:
            shutil.copyfile(self.doc, imagespath)

    def write_metadata(self):

        if not self.metadata.has_key("images-dpi"):
            note(3, "   using default DPI of 75")
            self.metadata["images-dpi"] = "75"
        DocumentParser.write_metadata(self)


class SplittableTIFFFile (TIFFDoc):

    class Subdocument:

        def __init__(self, folder, original, pagerange, wordboxes):
            self.origin_folder = folder
            self.original = original
            self.startpage = pagerange[0]
            self.finalpage = pagerange[1]
            if wordboxes:
                self.wordboxes = wordboxes[self.startpage:self.finalpage+1]
            else:
                self.wordboxes = []
            self.folder = mktempdir()

        def page_count(self):
            return self.finalpage - self.startpage + 1

        def write_page_images(self):
            our_index = 1
            os.mkdir(os.path.join(self.folder, "page-images"))
            for index in range(self.startpage, self.finalpage + 1):
                shutil.copyfile(os.path.join(self.origin_folder, "page-images", "page%05d.png" % (index+1)),
                                os.path.join(self.folder, "page-images", "page%05d.png" % our_index))
                our_index += 1

        def write_text_and_wordboxes(self):
            bbox_outfile = open(os.path.join(self.folder, "wordbboxes"), "wb")
            bbox_outfile.write("UpLib:wbb:1\0")
            contents_outfile = codecs.open(os.path.join(self.folder, "contents.txt"), 'wb', 'utf_8')
            contents_outfile.write(u'Content-Type: text/plain; charset=utf8\n')
            contents_outfile.write(u'Content-Language: %s\n' % DEFAULT_LANGUAGE)
            contents_outfile.flush()
            contents_offset = contents_outfile.tell()

            page_no = 0
            for page_index, bboxes in self.wordboxes:
                if page_no > 0:
                    contents_outfile.write(u"\f\n")
                    bbox_outfile.write(24 * struct.pack("B", 0))
                for b in bboxes:
                    if b.has_hyphen() and b.ends_line():
                        fragment = b.text()[:-1]
                    elif b.ends_line():
                        fragment = b.text() + u'\n'
                    elif b.ends_word():
                        fragment = b.text() + u' '
                    else:
                        fragment = b.text()
                    contents_outfile.flush()
                    contents_position = contents_outfile.tell() - contents_offset
                    if len(fragment) > 0:
                        contents_outfile.write(unicodedata.normalize("NFC", fragment))
                    bbox_outfile.write(struct.pack(">BBBBffff", *(b.fields[:8])) +
                                       struct.pack(">I", contents_position))
                page_no += 1
            contents_outfile.close()
            bbox_outfile.close()

        def copy_part (startpage, finalpage, inputfile, outputfile):
            input_file = inputfile + "".join([(",%d" % x) for x in range(startpage, finalpage + 1)])
            cmd = TIFF_COMPRESS_CMD % (TIFFCP, "zip", input_file, outputfile)
            status, output, signal = subproc(cmd)
            # tiffcp has bizarre status codes, so ignore them
            return os.path.exists(outputfile)
        copy_part = staticmethod(copy_part)

        def copy_originals(self):
            os.mkdir(os.path.join(self.folder, "originals"))
            if not self.copy_part(self.startpage, self.finalpage, self.original,
                                  os.path.join(self.folder, "originals", "document.tiff")):
                note("Couldn't copy original %s into originals folder of subdocument", self.original)

        def create_new_folder(self):
            self.copy_originals()
            self.write_page_images()
            self.write_text_and_wordboxes()
            return self.folder

        def __del__(self):
            if os.path.exists(self.folder):
                shutil.rmtree(self.folder)

    format_mimetype = TIFFDoc.format_mimetype

    BEFORE = ("ImageDoc", "TIFFDoc", )

    SEPARATOR_PAGE_PATTERN = re.compile('(?:^|\f)([^\f]*UpLib Scan Separator Sheet){4}[^\f]*', re.MULTILINE)
    FORMFEED_PATTERN = re.compile('\f')

    myformat = TIFFDoc.myformat
    myformat = staticmethod(myformat)

    def __init__(self, doc, options):
        TIFFDoc.__init__(self, doc, options)
        self.__options = options

    def figure_subdoc_pageranges(self, separator_pages, pagecount):
        # figure out page ranges for subdocs
        splits = []
        prevpage = 0
        for page_index in separator_pages:
            pagerange = (prevpage, page_index-1)
            prevpage = page_index + 1
            if (pagerange[1] - pagerange[0]) >= 0:
                splits.append(pagerange)
        if (pagecount-1) > page_index:
            splits.append((page_index + 1, pagecount-1,))
        return splits

    def check_for_text_splits(self):
        # now look for separator pages
        separator_pages = []
        wordboxes = None
        text = None

        if os.path.exists(self.text_path()) and os.path.exists(self.word_boxes_path()):
            # look for split pages in OCRed text
            text = open(self.text_path(), 'r').read()
            pagebreaks = []
            for match in self.FORMFEED_PATTERN.finditer(text):
                pagebreaks.append(match.start())
            if pagebreaks:
                if len(text) > pagebreaks[-1]:
                    pagebreaks.append(len(text))
            else:
                pagebreaks.append(len(text))
            # note("   pagebreaks are %s", pagebreaks)
            for match in self.SEPARATOR_PAGE_PATTERN.finditer(text):
                page_index = bisect.bisect(pagebreaks, match.start(1))
                # note("   match %s is page %s", match.start(1), page_index)
                separator_pages.append(page_index)
            wordboxes = read_wordboxes_file(self.folder)
            note(4, "   separator pages are %s", separator_pages)

        if not separator_pages:
            return None

        splits = self.figure_subdoc_pageranges(separator_pages, len(pagebreaks))

        # for each subdocument, create an UpLib folder structure
        resultslist = list()
        if len(splits) > 1:
            note("  ...found %d documents in %s, adding each separately...", len(splits), self.doc)
        for split in splits:
            try:
                s = self.Subdocument(self.folder, self.doc, split, wordboxes)
                f = s.create_new_folder()
                result = UpLibDoc(f, self.hack_opts(split)).process()
                shutil.rmtree(f)
                identifier = "%s[%s-%s]" % (self.doc, split[0], split[1])
                resultslist.append((identifier, result))
            except:
                msg = string.join(traceback.format_exception(*sys.exc_info()))
                note(0, msg)
        return resultslist

    def hack_opts (self, split):
        opts = self.__options.copy()
        md = self.metadata.copy()
        if not self.metadata.has_key('title'):
            if isinstance(self.doc, str):
                if not isinstance(self.doc, unicode):
                    title = unicode(self.doc, sys.getfilesystemencoding(), "strict")
                else:
                    title = self.doc
            md['title'] = "%s[%s-%s]" % (title, split[0], split[1])
            md['title-is-original-filepath'] = "true"
        else:
            md['title'] = "%s[%s-%s]" % (self.metadata['title'], split[0], split[1])
        md['page-count'] = (int(split[1]) - int(split[0])) + 1
        md.pop('monochrome-pages', None)
        md.pop('paletted-pages', None)
        md.pop('fullcolor-pages', None)
        md.pop('summary', None)
        md['apparent-mime-type'] = TIFFDoc.format_mimetype
        opts['metadata'] = md
        return opts

    def process (self):
        # check for splitup splits
        splits = []
        if SPLITUP_BINARY:
            # if we have the "splitup" binary available
            cmd = SPLITUP_CMD % (SPLITUP_BINARY, self.doc)
            status, output, tsig = subproc(cmd)
            if status == 0:
                separator_pages = [int(x) for x in output.split('\n') if (len(x.strip()) > 0)]
                note(4, "separator_pages are %s", separator_pages)
                if separator_pages:
                    splits = self.figure_subdoc_pageranges(separator_pages, self.countpages())
        note(4, "splits are %s", splits)
        if len(splits) > 1:
            note("  ...found %d documents in %s, processing each separately...", len(splits), self.doc)
            resultslist = list()
            self.check_tags()
            for split in splits:
                tfile = mktempfile() + ".tiff"
                try:
                    if self.Subdocument.copy_part(split[0], split[1], self.doc, tfile):
                        result = TIFFDoc(tfile, self.hack_opts(split)).process()
                        identifier = "%s[%s-%s]" % (self.doc, split[0], split[1])
                        resultslist.append((identifier, result))
                finally:
                    if os.path.exists(tfile):
                        os.unlink(tfile)
            note(4, "resultslist is %s", resultslist)
            return resultslist
        else:
            return TIFFDoc.process(self)

    def write_metadata(self):
        sval = self.check_for_text_splits()
        if sval:
            raise MultiPartDocument(sval)
        return TIFFDoc.write_metadata(self)



class ImageDoc (DocumentParser):

    DATE_TIME_ORIGINAL_EXIF = 0x9003

    def __init__(self, doc, options):
        DocumentParser.__init__(self, doc, options)
        ext = os.path.splitext(self.doc)[1]
        if (ext == '.gif' or ext == '.GIF'):
            self.format_mimetype = "image/gif"
        elif (ext == '.png' or ext == '.PNG'):
            self.format_mimetype = "image/png"
        elif (string.lower(ext) == '.jpeg' or string.lower(ext) == '.jpg'):
            self.format_mimetype = "image/jpeg"
        elif (string.lower(ext) == '.tiff' or string.lower(ext) == '.tif'):
            self.format_mimetype = "image/tiff"
        elif (string.lower(ext) == '.bmp'):
            self.format_mimetype = "image/bmp"
        elif (string.lower(ext) == '.xpm'):
            self.format_mimetype = "image/x-pixmap"
        elif (string.lower(ext) == '.xbm'):
            self.format_mimetype = "image/x-bitmap"
        elif (string.lower(ext) == '.rast'):
            self.format_mimetype = "image/x-sun-raster"
        elif (string.lower(ext) == '.eps'):
            self.format_mimetype = "application/postscript"
        elif (string.lower(ext) == '.pbm' or string.lower(ext) == '.pnm' or
              string.lower(ext) == '.pgm' or string.lower(ext) == '.ppm'):
            self.format_mimetype = "image/pbm"
        else:
            self.format_mimetype = "image"
        if self.format_mimetype == "image/jpeg":
            # check for EXIF data
            try:
                im = Image.open(self.doc)
                if hasattr(im, "_getexif"):
                    d = im._getexif()
                    if d:
                        v = d.get(self.DATE_TIME_ORIGINAL_EXIF)
                        if v:
                            self.metadata['original-date-time'] = v
                            if not self.metadata.has_key("date"):
                                date = time.strptime(v, "%Y:%m:%d %H:%M:%S")
                                self.metadata['date'] = time.strftime("%m/%d/%Y", date)
                        v = TIFFDoc.get_tiff_camera_info(d)
                        if v:
                            self.metadata['camera-type'] = v
                        if not self.metadata.has_key("images-dpi"):
                            v = TIFFDoc.get_tiff_resolution(d)
                            if v:
                                note(3, "   setting DPI to %d based on tags in the %s file", v, self.format_mimetype)
                                self.metadata["images-dpi"] = str(v)
            except:
                # OK, ignore (bad) EXIF data :-)
                pass
        elif self.format_mimetype == "image/tiff":
            # check for TIFF tags
            try:
                im = Image.open(self.doc)
                if hasattr(im, "tag"):
                    d = im.tag
                    if d:
                        v = d.get(self.DATE_TIME)
                        if v:
                            self.metadata['original-date-time'] = v
                            if not self.metadata.has_key("date"):
                                date = time.strptime(v, "%Y:%m:%d %H:%M:%S")
                                self.metadata['date'] = time.strftime("%m/%d/%Y", date)
                        v = d.get(self.CAMERA_MAKE)
                        v2 = d.get(self.CAMERA_MODEL)
                        if (v or v2):
                            self.metadata['camera-type'] = ((v and (v + " - ")) or "") + v2
            except:
                # OK, ignore (bad) TIFF tags :-)
                pass
        if not self.metadata.has_key("images-dpi"):
            if options.has_key("dpi"):
                note(3, "   setting DPI to %d based on tags in the %s file", options['dpi'], self.format_mimetype)
                self.metadata["images-dpi"] = str(options["dpi"])
            else:
                note(3, "   using default DPI of 75")
                self.metadata["images-dpi"] = "75"

    format_mimetype = "image"

    def myformat(pathname):
        if not os.path.exists(pathname):
            return false
        if ((IMAGE_EXTENSIONS.search(pathname) == None) or TIFF_EXTENSION.search(pathname)):
            return false
        try:
            from PIL import Image
            im = Image.open(pathname)
            bytes = im.size[0] * im.size[1]
            if im.mode not in ("1", "L", "P"):
                bytes = bytes * 4  # 32-bit storage
            if bytes > IMAGE_SIZE_LIMIT:
                del im
                note("Image too large: IMAGE_SIZE_LIMIT is %s, image requires %s bytes",
                     IMAGE_SIZE_LIMIT, bytes)
                return False
            im.load()
            d = { 'format' : im.format }
            if im.info.has_key('dpi'):
                dpi = im.info.get('dpi')
                if type(dpi) == type(3):
                    d['dpi'] = dpi
                elif type(dpi) == types.TupleType and len(dpi) == 2 and dpi[0] == dpi[1]:
                    d['dpi'] = dpi[0]
            return d
        except:
            typ, val, tb = sys.exc_info()
            note(2, "Apparent image %s cannot be loaded by the Image module: %s.", pathname, val)
            return false
            
    myformat = staticmethod(myformat)

    def get_page_images(self):
        # create a TIFF version
        imagespath = self.images_path()
        if self.uses_png:
            png_file_name = os.path.join(imagespath, "page00001.png")
            os.mkdir(imagespath)
            if (convert_image_to_png(self.doc, png_file_name)):
                note(3, "created PNG file in %s", png_file_name)
                # process the folder
            else:
                note("Can't convert %s to PNG.  Please convert first.", self.doc)
        else:
            if (convert_image_to_tiff(self.doc, imagespath)):
                note(3, "created tiff file in %s", imagespath)
            else:
                note("Can't convert %s to TIFF.  Please convert first.", self.doc)

    def write_metadata(self):

        # called to create the metadata file
        #
        # We look for data inside the image here, notably camera data inside
        # TIFF or JPEG images.
        #

        DocumentParser.write_metadata(self)


class FakePDFDoc (PDFDoc):

    def __init__(self, doc, options):
        PDFDoc.__init__(self, doc, options)
        self.pdffile = None

    def __del__(self):
        if self.pdffile and os.path.exists(self.pdffile):
            os.unlink(self.pdffile)

    format_mimetype = None

    def get_page_images (self):

        pdf = self.get_pdf_version()
        if pdf:
            saved_doc = self.doc
            try:
                self.doc = pdf
                PDFDoc.get_page_images(self)
            finally:
                self.doc = saved_doc

    def get_text (self):

        pdf = self.get_pdf_version()
        if pdf:
            saved_doc = self.doc
            try:
                self.doc = pdf
                PDFDoc.get_text(self)
            finally:
                self.doc = saved_doc

    def extract_links (self):

        pdf = self.get_pdf_version()
        if pdf:
            saved_doc = self.doc
            try:
                self.doc = pdf
                PDFDoc.extract_links(self)
            finally:
                self.doc = saved_doc

    def get_pdf_version(self):
        return None


class PostscriptDoc (FakePDFDoc):

    format_mimetype = "application/postscript"

    def myformat(pathname):
        if not os.path.exists(pathname):
            return false
        return (POSTSCRIPT_EXTENSION.search(pathname) != None)
    myformat = staticmethod(myformat)

    def get_pdf_version(self):
        if not (self.pdffile and os.path.exists(self.pdffile)):
            tfile = mktempfile()
            #cmd = PS2PDF_CMD % (PS2PDF, self.doc, tfile)
            cmd = '%s -q -dSAFER -dNOPAUSE -dBATCH -sDEVICE#pdfwrite -sOutputFile="%s" "%s"' % (
                GHOSTSCRIPT, tfile, self.doc)
            note(2, "converting Postscript to PDF with <<%s>>", cmd)
            status, output, tsig = subproc(cmd)
            if status == 0:
                self.pdffile = tfile
            else:
                note(2, "postscript-to-PDF conversion of %s failed with status %d:  %s", self.doc, status, output)
                if os.path.exists(tfile): os.unlink(tfile)
                self.pdffile = None
                raise Error("postscript-to-PDF conversion of %s failed with status %d:  %s" % (self.doc, status, output))
        return self.pdffile


class TextDoc (PostscriptDoc):

    def __init__(self, doc, options):
        PostscriptDoc.__init__(self, doc, options)
        if ASSUME_TEXT_NO_COLOR:
            self.color = false
        self.checkocr = false

    format_mimetype = "text/plain"

    TEXT_EXTENSION = re.compile(r'((\.txt)|(\.text))$', re.IGNORECASE)

    def type_is_text (pathname):
        if not os.path.exists(pathname) or sys.platform.lower().startswith("win"):
            return false
        # HTML and Postscript can mistakenly be identified as text sometimes,
        # so exclude them
        if HTML_EXTENSION.search(pathname):
            return false
        if POSTSCRIPT_EXTENSION.search(pathname):
            return false
        # There are a couple of Python implementations of "file", but none seems quite
        # read for prime time, so let's just call the real "file"
        cmd = FILE_CMD % pathname
        status, output, tsig = subproc(cmd)
        if status == 0:
            return (FILE_TEXT_ENDING.search(output[:-1]) != None)
        else:
            return false
    type_is_text = staticmethod(type_is_text)

    def myformat(pathname):
        if (ENSCRIPT or NENSCRIPT) and TextDoc.TEXT_EXTENSION.search(pathname):
            return true
        elif (ENSCRIPT or NENSCRIPT) and FILE_CMD and TextDoc.type_is_text(pathname):
            return true
        else:
            return false
    myformat = staticmethod(myformat)

    def get_pdf_version(self):
        if not (self.pdffile and os.path.exists(self.pdffile)):
            tfile = mktempfile()
            if ENSCRIPT:
                cmd = ENSCRIPT_CMD % (ENSCRIPT, tfile, self.doc)
                note(2, "enscripting text file with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                # enscript will exit with non-zero exit status if it wraps lines, so
                # see if the file exists rather than checking the exit status
                if os.path.exists(tfile):
                    prevdoc = self.doc
                    self.doc = tfile
                    try:
                        self.pdffile = PostscriptDoc.get_pdf_version(self)
                    finally:
                        self.doc = prevdoc
                        os.unlink(tfile)
                else:
                    note(2, "enscription of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("enscription of %s failed with status %d:  %s" % (self.doc, status, output))
            elif NENSCRIPT:
                cmd = NENSCRIPT_CMD % (NENSCRIPT, tfile, self.doc)
                note(2, "enscripting text file with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if status == 0:
                    prevdoc = self.doc
                    self.doc = tfile
                    try:
                        self.pdffile = PostscriptDoc.get_pdf_version(self)
                    finally:
                        self.doc = prevdoc
                        os.unlink(tfile)
                else:
                    note(2, "enscription of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("enscription of %s failed with status %d:  %s" % (self.doc, status, output))
        return self.pdffile


class UpLibDoc (DocumentParser):

    format_mimetype = "multipart/x-uplib"

    def myformat(pathname):
        if not os.path.exists(pathname):
            return false
        return (os.path.isdir(pathname) and
                (os.path.isdir(os.path.join(pathname, "page-images")) or
                 os.path.exists(os.path.join(pathname, "document.tiff"))) and
                (os.path.exists(os.path.join(pathname, "metadata.txt")) or
                 os.path.exists(os.path.join(pathname, "contents.txt")) or
                 os.path.exists(os.path.join(pathname, "wordbboxes"))))
    myformat = staticmethod(myformat)

    def copy_original(self):
        if os.path.isdir(os.path.join(self.doc, "images")):
            shutil.copytree(os.path.join(self.doc, "images"), os.path.join(self.folder, "images"))
        if os.path.isdir(os.path.join(self.doc, "originals")):
            shutil.copytree(os.path.join(self.doc, "originals"), self.originals_path())

    def process (self):
        self.optimize = false   # presumably already done
        if os.path.exists(os.path.join(self.doc, "metadata.txt")):
            shutil.copyfile(os.path.join(self.doc, "metadata.txt"), self.metadata_path())
            d = read_metadata(self.metadata_path())
            if not self.metadata.has_key("images-dpi"):
                if d.has_key("images-dpi"):
                    self.metadata["images-dpi"] = d.get("images-dpi")
                elif d.has_key("tiff-dpi"):
                    self.metadata["images-dpi"] = d.get("tiff-dpi")
            if not self.metadata.has_key("title"):
                if d.has_key("title"):
                    self.metadata["title"] = d.get("title")
        if os.path.exists(os.path.join(self.doc, "contents.txt")):
            shutil.copyfile(os.path.join(self.doc, "contents.txt"), self.text_path())
        if os.path.exists(os.path.join(self.doc, "wordbboxes")):
            shutil.copyfile(os.path.join(self.doc, "wordbboxes"), self.word_boxes_path())
        if os.path.exists(os.path.join(self.doc, "summary.txt")):
            shutil.copyfile(os.path.join(self.doc, "summary.txt"), self.summary_path())
        if os.path.exists(os.path.join(self.doc, "links")):
            shutil.copytree(os.path.join(self.doc, "links"), self.links_dir_path())
        if os.path.exists(os.path.join(self.doc, "page-images")):
            # don't know where this comes from, but suspect the GIMP
            if os.path.isdir(os.path.join(self.doc, "page-images", ".xvpics")):
                shutil.rmtree(os.path.join(self.doc, "page-images", ".xvpics"))
            shutil.copytree (os.path.join(self.doc, "page-images"), os.path.join(self.folder, "page-images"))
            self.uses_png = true
        elif os.path.exists(os.path.join(self.doc, "document.tiff")):
            if self.uses_png:
                png_directory = os.path.join(self.folder, "page-images")
                if not os.path.isdir(png_directory):
                    os.mkdir(png_directory)
                convert_tiff_to_png (os.path.join(self.doc, "document.tiff"), png_directory)
            else:
                shutil.copyfile (os.path.join(self.doc, "document.tiff"), os.path.join(self.folder, "document.tiff"))
                self.uses_png = false
        return DocumentParser.process(self)


class URLDoc (DocumentParser):

    REMOTE_WEB_PAGE_PREFIX = "<remoteWebPage>:"

    BEFORE = ('PDFDoc', 'SourceCode', 'TextDoc', 'PostscriptDoc', 'TIFFDoc', 'ImageDoc', 'SplittableTIFFFile', 'MSDoc')

    def __init__(self, doc, options):
        DocumentParser.__init__(self, doc, options)
        if options.has_key('cached-copy'):
            self.__cached = options['cached-copy']
        else:
            self.__cached = None
        self.__real_url = options.get('real-url')
        if options.has_key('content-type'):
            self.format_mimetype = options['content-type']
        self.__options = options

    def process (self):
        # URLDoc.process
        if not self.__cached:
            return None
        url = self.__real_url or self.doc
        if self.__options.has_key("metadata"):
            self.__options["metadata"].update({ "original-url": url })
        else:
            self.__options["metadata"] = { "original-url": url }
        self.__options["real-url"] = url
        if self.__options["content-type"] and self.__options["content-type"].startswith("text/html"):
            # Adding REMOTE_WEB_PAGE_PREFIX will cause the document to be handled by the
            # WebPageRemoteDoc subclass of the FakePDFDoc subclass of PDFDoc:
            v = DocumentParser.parse_document(self.REMOTE_WEB_PAGE_PREFIX + url, None, options=self.__options)
        elif self.__cached and isinstance(self.__cached, Cache):
            v = DocumentParser.parse_document(self.__cached.filename, None, options=self.__options)
        if self.__cached:
            self.__cached.remove()
        return (v and v[0][1]) or None

    format_mimetype = "application/x-url"

    def cache_local_copy (url):
        # try to pull over the document
        note(3, "creating local cache of %s...", url)
        c = Cache(url, "original", use_correct_suffix=True)
        if c.failed:
            note("Can't retrieve URL %s:\n%s", url, c.failed)
            return {}

        is_xhtml = False
        if c.content_type.lower() == "text/html":
            # check for XML
            fp = open(c.filename, 'r')
            try:
                bits = fp.readline()
                if bits.startswith("<?xml "):
                    # really XML, maybe XHTML
                    bits = fp.readline()
                    # deal with blank lines
                    while not bits.strip():
                        bits = fp.readline()
                    if bits.lower().startswith("<!doctype html public"):
                        # yep, XHTML
                        is_xhtml = true
                    else:
                        c.content_type = "text/xml"
            finally:
                fp.close()

        url_ext = os.path.splitext(url)[1]
        if (c.content_type.lower() == "text/plain") and url_ext and (url_ext in SourceCode.suffix_to_language_mapping):
            newname = os.path.splitext(c.filename) + url_ext
            os.rename(c.filename, newname)
            c.filename = newname
            return {'cached-copy': c, 'content-type': c.content_type, 'is_xhtml': false}
        elif CONTENT_TYPES.has_key(c.content_type):
            return {'cached-copy': c, 'content-type': c.content_type, 'is_xhtml': (is_xhtml and true) or false}
        else:
            note("Can't handle content-type %s", c.content_type)
            c.remove()
            return {}
    cache_local_copy=staticmethod(cache_local_copy)

    def myformat (pathname):
        if URL_PREFIX.match(pathname):
            try:
                d = URLDoc.cache_local_copy(pathname)
                if d:
                    return d
                else:
                    return false
            except:
                typ, value, tb = sys.exc_info()
                msg = string.join(traceback.format_exception(typ, value, tb))
                note(4, "exception raised:\n%s", msg)
                return false
        else:
            return false
    myformat = staticmethod(myformat)

    def __del__(self):
        if self.__cached:
            self.__cached.remove()


class WebPageCompleteDoc (FakePDFDoc):

    """This class handles Mozilla-style "web page complete" format"""

    initted = false
    HTMLDOC = None
    HTMLDOC_CMD = None
    WKPDF = None
    WKPDF_CMD = None
    WKHTMLTOPDF = None
    WKHTMLTOPDF_CMD = None

    format_mimetype = "text/html"

    def myformat(pathname):
        if not WebPageCompleteDoc.initted:
            conf = configurator()
            WebPageCompleteDoc.WKPDF = conf.get('wkpdf')
            WebPageCompleteDoc.WKPDF_CMD = conf.get('wkpdf-command')
            WebPageCompleteDoc.HTMLDOC = conf.get('htmldoc')
            WebPageCompleteDoc.HTMLDOC_CMD = conf.get('htmldoc-command')
            WebPageCompleteDoc.WKHTMLTOPDF = conf.get('wkhtmltopdf')
            WebPageCompleteDoc.WKHTMLTOPDF_CMD = conf.get('wkhtmltopdf-command')
            WebPageCompleteDoc.initted = true
        if not (USE_TOPDF_FOR_WEB or USE_OPENOFFICE_FOR_WEB or WebPageCompleteDoc.HTMLDOC or WebPageCompleteDoc.WKPDF or WebPageCompleteDoc.WKHTMLTOPDF):
            note(0, """WebPageCompleteDoc declines to handle URL %s because no htmldoc or wkpdf or OpenOffice or wkhtmltopdf command is
                specified in the configuration""" % pathname)
            return false
        base, ext = os.path.splitext(pathname)
        # Camino on Mac OS X stores page in "foo.html" and "foo Files"
        # Firefox and Mozilla on Mac OS X stores page in "foo.html" and "foo_files"
        if ext.lower() in (".html", ".htm") and (os.path.isdir(base + "_files") or
                                                 os.path.isdir(base + " Files")):
            return true
        # we also need to "trap" and ignore the auxiliary directory of files
        if ((pathname.endswith("_files") or pathname.endswith(" Files"))
            and os.path.isdir(pathname)
            and (os.path.exists(pathname[:-6] + ".html") or os.path.exists(pathname[:-6] + ".htm"))):
            return true
        return false
    myformat = staticmethod(myformat)

    def process(self):
        pathname = self.doc
        if ((pathname.endswith("_files") or pathname.endswith(" Files")) and os.path.isdir(pathname) and
            (os.path.exists(pathname[:-6] + ".html") or os.path.exists(pathname[:-6] + ".htm"))):
            return None
        return FakePDFDoc.process(self)

    def write_metadata (self):
        if not self.metadata.has_key("title"):
            tf = TitleFinder()
            try:
                tf.feed(open(self.doc, 'r').read())
                if tf.title:
                    self.metadata['title'] = tf.clean_title()
            except ParsingDone:
                if tf.title:
                    self.metadata['title'] = tf.clean_title()
            except:
                typ, value, tb = sys.exc_info()
                note(3, "Attempting to parse HTML with TitleFinder raised an exception: %s", str(value))
                note(3, "Ignoring it.")
        FakePDFDoc.write_metadata(self)

    def copy_original(self):

        # called to copy the original file to the originals subdirectory

        originals_path = self.originals_path()
        if not os.path.exists(originals_path):
            os.mkdir(originals_path)
            os.chmod(originals_path, 0700)
        shutil.copyfile(self.doc, os.path.join(originals_path, os.path.basename(self.doc)))
        basepath = os.path.splitext(self.doc)[0] + "_files"
        if not os.path.exists(basepath):
            basepath = os.path.splitext(self.doc)[0] + " Files"
        shutil.copytree(basepath, os.path.join(originals_path, os.path.basename(basepath)))

    def get_pdf_version(self):
        if not (self.pdffile and os.path.exists(self.pdffile)):
            tfile = mktempfile(".pdf")
            if (TOPDF_PORT > 0) and USE_TOPDF_FOR_WEB:
                try:
                    filepath = os.path.realpath(self.doc)
                    if PUSH_TO_PDF:
                        tfile = mktempfile()
                        dir, pathname = os.path.split(filepath)
                        zipup(dir, tfile)
                        try:
                            errcode, errmsg, headers, pdfdata = http_post_multipart(TOPDF_HOST, TOPDF_PORT, None, "/web-to-pdf",
                                                                                    (("filepath", pathname),),
                                                                                    (("zipfile", tfile),))
                        finally:
                            os.unlink(tfile)
                    else:
                        errcode, errmsg, headers, pdfdata = http_post_multipart("127.0.0.1", TOPDF_PORT, None, "/web-to-pdf",
                                                                                (("filepath", filepath),),
                                                                                (),)
                    if errcode == 200:
                        self.metadata['html-to-pdf-formatter'] = "local UpLib ToPDF server"
                        tfile = mktempfile()
                        f = open(tfile, "wb")
                        f.write(pdfdata)
                        f.close()
                        self.pdffile = tfile
                    else:
                        self.pdffile = None
                        note(3, "HTML to PDF conversion via ToPDF on port %s failed with error code %s, and error message <%s>", TOPDF_PORT, errcode, errmsg)
                        raise Error("HTML to PDF conversion via ToPDF on port " + str(TOPDF_PORT) + " failed with error message \"" + errmsg + "\"")
                except socket.error, x:
                    raise Error("Couldn't communicate with UpLib ToPDF service on port %s:  error %s" % (TOPDF_PORT, x))
            elif USE_OPENOFFICE_FOR_WEB:
                cmd = OOO_WEB_TO_PDF_CMD % (OOO_CONVERT_TO_PDF, os.path.abspath(self.doc), tfile)
                note(2, "running OpenOffice to convert saved Web page to PDF with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'openoffice'
                    if status != 0:
                        note("Some errors in processing HTML file:\n%s", output)
                else:
                    note(2, "OpenOffice PDF conversion of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("OpenOffice PDF conversion of %s failed with status %d:  %s" % (self.doc, status, output))
            elif self.WKPDF:
                cmd = self.WKPDF_CMD % (self.WKPDF, self.doc, tfile)
                note(2, "running wkpdf with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'wkpdf'
                    if status != 0:
                        note("Some errors in processing HTML file (exit status %s)", status)
                        if output.strip():
                            note("Output from wkpdf was:\n%s", output)
                else:
                    note(2, "wkpdf of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("wkpdf of %s failed with status %d:  %s" % (self.doc, status, output))
            elif self.WKHTMLTOPDF:
                # wkhtmltopdf mis-handles backslashes in the filename, so convert them to forward slashes
                docpath = self.doc
                if os.path.sep == '\\':
                    docpath = docpath.replace(os.path.sep, '/')
                cmd = self.WKHTMLTOPDF_CMD % (self.WKHTMLTOPDF, docpath, tfile)
                note(2, "running wkhtmltopdf with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'wkhtmltopdf'
                    if status != 0:
                        note("Some errors in processing HTML file (exit status %s)", status)
                        if output.strip():
                            note("Output from wkhtmltopdf was:\n%s", output)
                else:
                    note(2, "wkhtmltopdf of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("wkhtmltopdf of %s failed with status %d:  %s" % (self.doc, status, output))
            else:
                cmd = self.HTMLDOC_CMD % (self.HTMLDOC, "", "", "", tfile, self.doc)
                note(2, "running htmldoc with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'htmldoc'
                    if status != 0:
                        note("Some errors in processing HTML file (exit status %s)", status)
                        if output.strip():
                            note("Output from htmldoc was:\n%s", output)
                else:
                    note(2, "htmldoc of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("htmldoc of %s failed with status %d:  %s" % (self.doc, status, output))
        return self.pdffile


class WebPageRemoteDoc (FakePDFDoc):

    """This class handles URLs that point to HTML documents"""

    initted = false
    HTMLDOC = None
    HTMLDOC_CMD = None
    WKPDF = None
    WKPDF_CMD = None
    WKHTMLTOPDF = None
    WKHTMLTOPDF_CMD = None

    format_mimetype = "text/html"

    BEFORE = ('TextDoc', 'ImageDoc', 'SplittableTIFFFile', 'WebPageCompleteDoc', 'PDFDoc', 'MSDoc', 'PostscriptDoc', 'SourceCode')

    def __init__(self, doc, options):
        FakePDFDoc.__init__(self, doc, options)
        if options.has_key('cached-copy'):
            self.__cached = options['cached-copy']
        else:
            self.__cached = Cache(doc, os.path.join(mktempdir(), "original.html"))
        self.is_xhtml = options.get('is_xhtml')
        self.hard_to_read = (self.__cached and self.__cached.hard_to_read) or options.get('hard_to_read')
        self.real_url = options.get('real-url')
        self.charset = (self.__cached and self.__cached.charset_string) or options.get('charset')
        
    def myformat(pathname):
        if not WebPageRemoteDoc.initted:
            conf = configurator()
            WebPageRemoteDoc.HTMLDOC = conf.get('htmldoc')
            WebPageRemoteDoc.HTMLDOC_CMD = conf.get('htmldoc-command')
            WebPageRemoteDoc.WKPDF = conf.get('wkpdf')
            WebPageRemoteDoc.WKPDF_CMD = conf.get('wkpdf-command')
            WebPageRemoteDoc.WKHTMLTOPDF = conf.get('wkhtmltopdf')
            WebPageRemoteDoc.WKHTMLTOPDF_CMD = conf.get('wkhtmltopdf-command')
            WebPageRemoteDoc.initted = true
        if not pathname.startswith(URLDoc.REMOTE_WEB_PAGE_PREFIX):
            return false;
        if not (USE_OPENOFFICE_FOR_WEB or WebPageRemoteDoc.HTMLDOC or WebPageRemoteDoc.WKPDF or WebPageRemoteDoc.WKHTMLTOPDF):
            note(3, """WebPageRemoteDoc declines to handle URL %s because no htmldoc or wkpdf or OpenOffice or wkhtmltopdf command is
                specified in the configuration""" % pathname)
            return false
        return true
    myformat = staticmethod(myformat)

    def copy_original(self):

        # called to copy the original file to the originals subdirectory

        originals_path = self.originals_path()
        if not os.path.exists(originals_path):
            os.mkdir(originals_path)
            os.chmod(originals_path, 0700)
        pathname = self.doc[len(URLDoc.REMOTE_WEB_PAGE_PREFIX):]
        if not self.__cached:
            self.__cached = Cache(pathname, os.path.join(originals_path, "original.html"))
        else:
            self.__cached.copy_to_dir(originals_path)
        self.hard_to_read = self.__cached.hard_to_read

    def write_metadata (self):
        # WebPageRemoteDoc.write_metadata
        if not self.metadata.has_key("title") and (os.path.exists(os.path.join(self.originals_path(), "original.html")) or self.__cached):
            tf = TitleFinder()
            try:
                fname = os.path.join(self.originals_path(), "original.html")
                if not os.path.exists(fname):
                    fname = self.__cached.filename
                tf.feed(open(fname, 'r').read())
                if tf.title:
                    self.metadata['title'] = tf.clean_title()
            except ParsingDone:
                if tf.title:
                    self.metadata['title'] = tf.clean_title()
            except:
                typ, value, tb = sys.exc_info()
                note(3, "Attempting to parse HTML with TitleFinder raised an exception: %s", str(value))
                note(3, "Ignoring it.")
        if not self.metadata.has_key("title"):
            self.metadata["title"] = self.doc[len(URLDoc.REMOTE_WEB_PAGE_PREFIX):]
        # URLDoc should have set "original-url" field before passing it on to here
        if not self.metadata.get("original-url"):
            self.metadata["original-url"] = self.real_url or self.doc[len(URLDoc.REMOTE_WEB_PAGE_PREFIX):]
        FakePDFDoc.write_metadata(self)

    def get_pdf_version(self):
        if not (self.pdffile and os.path.exists(self.pdffile)):
            tfile = mktempfile(".pdf")
            url = self.doc[len(URLDoc.REMOTE_WEB_PAGE_PREFIX):]
            default_originals_root = os.path.join(self.originals_path(), "original.html")
            if self.__cached:
                originals_root = self.__cached.filename
            elif os.path.exists(default_originals_root):
                originals_root = default_originals_root
            if (TOPDF_PORT > 0) and USE_TOPDF_FOR_WEB:
                try:
                    filepath = os.path.realpath(originals_root)
                    if PUSH_TO_PDF:
                        tfile = mktempfile()
                        dir, pathname = os.path.split(filepath)
                        zipup(dir, tfile)
                        try:
                            note(4, "calling http://%s:%s/web-to-pdf with zipfile=%s, filepath=%s",
                                 TOPDF_HOST, TOPDF_PORT, tfile, pathname)
                            errcode, errmsg, headers, pdfdata = http_post_multipart(TOPDF_HOST, TOPDF_PORT, None, "/web-to-pdf",
                                                                                    (("filepath", pathname),),
                                                                                    (("zipfile", tfile),))
                        finally:
                            os.unlink(tfile)
                    else:
                        errcode, errmsg, headers, pdfdata = http_post_multipart("127.0.0.1", TOPDF_PORT, None, "/web-to-pdf",
                                                                                (("filepath", filepath),),
                                                                                (),)
                    note(4, "returncode was %s", errcode)
                    if errcode == 200:
                        self.metadata['html-to-pdf-formatter'] = "local UpLib ToPDF server"
                        tfile = mktempfile()
                        f = open(tfile, "wb")
                        f.write(pdfdata)
                        f.close()
                        self.pdffile = tfile
                    else:
                        self.pdffile = None
                        note(3, "HTML to PDF conversion via ToPDF on port %s failed with error code %s, and error message <%s>",
                             TOPDF_PORT, errcode, errmsg)
                        raise Error("HTML to PDF conversion via ToPDF on port " + str(TOPDF_PORT) +
                                    " failed with error message \"" + errmsg + "\"")
                except socket.error, x:
                    raise Error("Couldn't communicate with UpLib ToPDF service on port %s:  error %s" % (TOPDF_PORT, x))
            elif USE_OPENOFFICE_FOR_WEB:
                # always use our cached copy to avoid proxy and cookie problems
                cmd = OOO_WEB_TO_PDF_CMD % (OOO_CONVERT_TO_PDF, os.path.abspath(originals_root), tfile)
                note(2, "running OpenOffice to convert Web to PDF with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'openoffice'
                    if status != 0:
                        note("Some errors in processing HTML file:\n%s", output)
                else:
                    note(2, "OpenOffice PDF conversion of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("OpenOffice PDF conversion of %s failed with status %d:  %s" % (self.doc, status, output))
            elif self.WKPDF:
                cmd = self.WKPDF_CMD % (self.WKPDF, originals_root, tfile)
                note(2, "running wkpdf with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'wkpdf'
                    if status != 0:
                        note("Some errors in processing HTML file:\n%s", output)
                else:
                    note(2, "wkpdf of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("wkpdf of %s failed with status %d:  %s" % (self.doc, status, output))
            elif self.WKHTMLTOPDF:
                # wkhtmltopdf mis-handles backslashes in the filename, so convert them to forward slashes
                docpath = originals_root
                if os.path.sep == '\\':
                    docpath = docpath.replace(os.path.sep, '/')
                cmd = self.WKHTMLTOPDF_CMD % (self.WKHTMLTOPDF, docpath, tfile)
                note(2, "running wkhtmltopdf with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'wkhtmltopdf'
                    if status != 0:
                        note("Some errors in processing HTML file, exit status was %s", status)
                        if output.strip():
                            note("Output from wkhtmltopdf was:\n%s", output)
                else:
                    note(2, "wkhtmltopdf of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("wkhtmltopdf of %s failed with status %d:  %s" % (self.doc, status, output))
            else:
                f = Fetcher()
                htmldoc_cookies = get_htmldoc_cookies(url) or ""
                htmldoc_referer = " --referer '%s'" % f.get_self_referer(url)
                proxy = f.get_proxy(url)
                htmldoc_proxy = (proxy and " --proxy '%s'" % proxy) or ""
                # if we've pulled a copy over, and the format is actually XHTML,
                # we've probably got a cached copy that HTMLDOC (which as of 1.8.24
                # doesn't do UTF-8) can deal with better than the remote URL, so use
                # it as the base for making page images
                if os.path.exists(originals_root):
                    pullurl = originals_root
                    htmldoc_cookies = ""
                    htmldoc_referer = ""
                    htmldoc_proxy = ""
                else:
                    pullurl = url
                cmd = self.HTMLDOC_CMD % (self.HTMLDOC, htmldoc_cookies, htmldoc_referer, htmldoc_proxy, tfile, pullurl)
                note(2, "running htmldoc with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if os.path.exists(tfile):
                    self.pdffile = tfile
                    self.metadata['html-to-pdf-formatter'] = 'htmldoc'
                    if status != 0:
                        note("Some errors in processing HTML file:\n%s", output)
                else:
                    note(2, "htmldoc of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("htmldoc of %s failed with status %d:  %s" % (self.doc, status, output))
        return self.pdffile


class MSDoc (FakePDFDoc):

    format_mimetype = "application/x-ms-office"

    def __init__(self, doc, options):
        FakePDFDoc.__init__(self, doc, options)
        ext = string.lower(os.path.splitext(self.doc)[1])
        if (ext == '.ppt' or ext == '.pps'):
            self.format_mimetype = "application/vnd.ms-powerpoint"
        elif (ext == '.doc' or ext == '.dot'):
            self.format_mimetype = "application/msword"
        elif (ext == '.xls' or ext == '.xlt'):
            self.format_mimetype = "application/vnd.ms-excel"
        elif (ext == '.pptx'):
            self.format_mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif (ext == '.ppsx'):
            self.format_mimetype = "application/vnd.openxmlformats-officedocument.presentationml.slideshow"
        elif (ext == '.docx'):
            self.format_mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif (ext == '.xlsx'):
            self.format_mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif (ext == '.rtf'):
            self.format_mimetype = "application/rtf"

    def myformat(pathname):
        if not os.path.exists(pathname):
            return false
        return (MS_EXTENSIONS.search(pathname) != None)
    myformat = staticmethod(myformat)

    def get_text (self):
        FakePDFDoc.get_text(self)
        if self.format_mimetype == "application/vnd.ms-powerpoint":
            # Powerpoint docs converted via OpenOffice can have overlaid duplicate
            # text (where text shadows are in the original document), so clean that
            # up
            clean_wordboxes_overlays(self.folder)

    def get_pdf_version(self):
        if not (self.pdffile and os.path.exists(self.pdffile)):
            if (TOPDF_PORT > 0) and USE_TOPDF_FOR_MSOFFICE:
                try:
                    filepath = os.path.realpath(self.doc)
                    if PUSH_TO_PDF:
                        errcode, errmsg, headers, pdfdata = http_post_multipart(TOPDF_HOST, TOPDF_PORT, None, "/office-to-pdf",
                                                                                (("filetype", self.format_mimetype),
                                                                                 ("filepath", filepath),),
                                                                                (("file", filepath),))
                    else:
                        errcode, errmsg, headers, pdfdata = http_post_multipart("127.0.0.1", TOPDF_PORT, None, "/office-to-pdf",
                                                                                (("filetype", self.format_mimetype),
                                                                                 ("filepath", filepath),), ())
                    if errcode == 200:
                        self.metadata['office-to-pdf-converter'] = "local UpLib ToPDF server"
                        tfile = mktempfile()
                        f = open(tfile, "wb")
                        f.write(pdfdata)
                        f.close()
                        self.pdffile = tfile
                    else:
                        self.pdffile = None
                        note(3, "MS to PDF conversion via ToPDF on port %s failed with error code %s, and error message <%s>",
                             TOPDF_PORT, errcode, errmsg)
                        raise Error("MS to PDF conversion via ToPDF on port " + str(TOPDF_PORT) +
                                    " failed with error message \"" + errmsg + "\"")
                except socket.error, x:
                    raise Error("Couldn't communicate with UpLib ToPDF service on port %s:  error %s" % (TOPDF_PORT, x))
            elif USE_OPENOFFICE_FOR_MSOFFICE:
                if self.format_mimetype == "application/vnd.ms-powerpoint":
                    template = OOO_POWERPOINT_TO_PDF_CMD
                elif self.format_mimetype == "application/msword":
                    template = OOO_MSWORD_TO_PDF_CMD
                elif self.format_mimetype == "application/vnd.ms-excel":
                    template = OOO_EXCEL_TO_PDF_CMD
                elif self.format_mimetype == "application/rtf":
                    template = OOO_RTF_TO_PDF_CMD
                elif self.format_mimetype == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                    template = OOO_POWERPOINT_XML_TO_PDF_CMD
                elif self.format_mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    template = OOO_MSWORD_XML_TO_PDF_CMD
                elif self.format_mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    template = OOO_EXCEL_XML_TO_PDF_CMD
                else:
                    raise ValueError("Invalid MSOffice mimetype %s" % self.format_mimetype)
                tfile = mktempfile(".pdf")
                cmd = template % (OOO_CONVERT_TO_PDF, os.path.abspath(self.doc), tfile)
                note(2, "running OpenOffice to convert saved %s document to PDF with <<%s>>", self.format_mimetype, cmd)
                status, output, tsig = subproc(cmd)
                if (status == 0) and os.path.exists(tfile):
                    self.metadata['office-to-pdf-converter'] = 'openoffice'
                    self.pdffile = tfile
                else:
                    note(2, "OpenOffice PDF conversion of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("OpenOffice PDF conversion of %s failed with status %d:  %s" % (self.doc, status, output))
            elif MS_TO_PDF_URL:
                # send it to the MS to PDF conversion service
                try:
                    ms_host, ms_port, ms_path = parse_URL(MS_TO_PDF_URL)
                except:
                    raise Error("badly formatted URL for MSOffice-to-PDF converter:  %s" % MS_TO_PDF_URL)

                try:
                    ext = string.lower(os.path.splitext(self.doc)[1])
                    errcode, errmsg, headers, pdfdata = http_post_multipart(ms_host, ms_port, None, ms_path,
                                                                            (("fileext", ext),
                                                                             ("filetype", self.format_mimetype),),
                                                                            (("file", self.doc),))
                    if errcode == 200:
                        self.metadata['office-to-pdf-converter'] = MS_TO_PDF_URL
                        tfile = mktempfile()
                        f = open(tfile, "wb")
                        f.write(pdfdata)
                        f.close()
                        self.pdffile = tfile
                    else:
                        self.pdffile = None
                        note(3, "MS to PDF conversion failed with error code %s, and error message <%s>", errcode, errmsg)
                        raise Error("MS to PDF conversion failed with error message \"" + errmsg + "\"")
                except socket.error, x:
                    raise Error("Couldn't communicate with MSOffice-to-PDF conversion service:  error %s" % x)
            else:
                raise Error("No conversion from Office to PDF available.  " +
                            "TOPDF_PORT is %s, " % TOPDF_PORT +
                            "USE_OPENOFFICE_FOR_MSOFFICE is %s, " % USE_OPENOFFICE_FOR_MSOFFICE +
                            "USE_TOPDF_FOR_MSOFFICE is %s, " % USE_TOPDF_FOR_MSOFFICE +
                            "PUSH_TO_PDF is %s, " % PUSH_TO_PDF +
                            "MS_TO_PDF_URL is '%s'" % MS_TO_PDF_URL)
        return self.pdffile


class SourceCode (PostscriptDoc):

    BEFORE = ('TextDoc',)

    filename_to_language_mapping = {
        "Makefile" : "Make",
        }

    suffix_to_language_mapping = {
        ".py": "Python",
        ".emacs" : "Emacs-Lisp",
        ".el" : "Emacs-Lisp",
        ".c" : "C",
        ".java" : "Java",
        ".cpp" : "C++",
        ".cc" : "C++",
        ".c++" : "C++",
        ".h" : "C",
        ".p" : "Perl",
        ".js" : "Javascript",
        ".sh" : "Bourne Shell",
        ".f" : "Fortran",
        ".m" : "Objective-C",
        ".scm" : "Scheme",
        ".tcl" : "Tcl",
        }

    language_to_enscript_code = {
        "Python" : "python",
        "Emacs-Lisp" : "elisp",
        "C" : "c",
        "Java" : "java",
        "C++" : "cpp",
        "Perl" : "perl",
        "Javascript" : "javascript",
        "Bourne Shell" : "sh",
        "Fortran": "fortran",
        "Objective-C" : "objc",
        "Scheme" : "scheme",
        "Tcl" : "tcl",
        "Make" : "makefile",
        }

    format_mimetype = "text/plain"
    BEFORE = ('TextDoc',)

    def __init__(self, doc, options):
        FakePDFDoc.__init__(self, doc, options)
        if ASSUME_TEXT_NO_COLOR:
            self.color = false
        self.checkocr = false
        self.language = (self.suffix_to_language_mapping.get(os.path.splitext(doc)[1]) or
                         self.filename_to_language_mapping.get(os.path.basename(doc)))
        self.format_mimetype = "text/x-%s" % self.language_to_enscript_code.get(self.language)

    def myformat(pathname):
        global CODE_ENSCRIPT_COMMAND, ENSCRIPT, NENSCRIPT, CODE_NENSCRIPT_COMMAND
        return (((ENSCRIPT and CODE_ENSCRIPT_COMMAND) or (NENSCRIPT and CODE_NENSCRIPT_COMMAND)) and
                (SourceCode.suffix_to_language_mapping.has_key(os.path.splitext(pathname)[1]) or
                 SourceCode.filename_to_language_mapping.has_key(os.path.basename(pathname))))
    myformat = staticmethod(myformat)

    def write_metadata (self):
        self.metadata["programming-language"] = self.language
        self.metadata["document-icon-legend"] = "(0,100,0)%s" % os.path.split(self.doc)[1]
        if not self.metadata.has_key("title"):
            self.metadata["title"] = os.path.split(self.doc)[1]
        FakePDFDoc.write_metadata(self)

    def get_pdf_version(self):
        global CODE_ENSCRIPT_COMMAND, ENSCRIPT, PS2PDF, NENSCRIPT, CODE_NENSCRIPT_COMMAND
        if not (self.pdffile and os.path.exists(self.pdffile)):
            tfile = mktempfile(".pdf")
            if ENSCRIPT and CODE_ENSCRIPT_COMMAND:
                tfile = mktempfile(".ps")
                cmd = CODE_ENSCRIPT_COMMAND % (
                    ENSCRIPT, self.language_to_enscript_code.get(self.language), tfile, self.doc)
                note(2, "enscripting code file with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                # enscript will exit with non-zero status if it wraps lines, so check
                # to see if output file exists rather than looking at the exit status
                if os.path.exists(tfile):
                    prevdoc = self.doc
                    try:
                        self.doc = tfile
                        self.pdffile = PostscriptDoc.get_pdf_version(self)
                    finally:
                        self.doc = prevdoc
                        os.unlink(tfile)
                else:
                    note(1, "enscription of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("enscription of %s failed with status %d:  %s" % (self.doc, status, output))
            elif NENSCRIPT and CODE_NENSCRIPT_COMMAND:
                cmd = CODE_NENSCRIPT_COMMAND % (NENSCRIPT, tfile, self.doc)
                note(2, "enscripting code file with <<%s>>", cmd)
                status, output, tsig = subproc(cmd)
                if (status == 0) and os.path.exists(tfile):
                    prevdoc = self.doc
                    try:
                        self.doc = tfile
                        self.pdffile = PostscriptDoc.get_pdf_version(self)
                    finally:
                        self.doc = prevdoc
                        os.unlink(tfile)
                else:
                    note(1, "enscription of %s failed with status %d:  %s", self.doc, status, output)
                    if os.path.exists(tfile): os.unlink(tfile)
                    self.pdffile = None
                    raise Error("enscription of %s failed with status %d:  %s" % (self.doc, status, output))
        return self.pdffile


class CardDoc (FakePDFDoc):

    BEFORE = ('TextDoc', 'SourceCode')

    def __init__(self, doc, options):
        FakePDFDoc.__init__(self, doc, options)
        if ASSUME_TEXT_NO_COLOR:
            self.color = false
            self.optimize = false
        self.checkocr = false
        self.width = options.get('width', 5)
        self.height = options.get('height', 3)

    format_mimetype = "text/plain"

    CARD_SIZE_ENDING = re.compile(r'.*\.([0-9]+)x([0-9]+)$')

    def myformat(pathname):
        m = CardDoc.CARD_SIZE_ENDING.match(pathname)
        if m:
            return { 'width' : int(m.group(2)), 'height' : int(m.group(1)) }
        elif pathname.endswith('.card') or pathname.endswith('.crd'):
            return { 'width' : 5, 'height' : 3 }
        else:
            return false
    myformat = staticmethod(myformat)

    def get_text_lines (self, f):
        if type(f) in types.StringTypes:
            text = open(f, 'r')
        else:
            text = f
        return text.readlines()

    def format_text_card (width, height, text, output_pdf_file, title=None):
        import reportlab
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, Frame, Spacer, SimpleDocTemplate
        from reportlab.lib.styles import ParagraphStyle
        stylesheet = reportlab.lib.styles.getSampleStyleSheet()

        width = width * inch
        height = height * inch
        padding = 0.25 * inch

        para_style = ParagraphStyle('para', stylesheet['Normal'], firstLineIndent=padding, fontSize=12.0,
                                    fontName="Courier")
        head_style = ParagraphStyle('head', stylesheet['Normal'], firstLineIndent=0, fontSize=12.0,
                                    fontName="Courier-Bold", spaceAfter=padding)

        pdf = SimpleDocTemplate(output_pdf_file, pagesize=(width, height),
                                leftMargin=padding, rightMargin=padding,
                                topMargin=padding, bottomMargin=padding,
                                title=title)

        paras = []
        current_para = ""
        if title:
            paras.append(Paragraph(cgi.escape(title), head_style))
        for line in text:
            if not line.strip():
                # blank line, start new paragraph if necessary
                if current_para:
                    paras.append(Paragraph(cgi.escape(current_para), para_style))
                    current_para = ""
            else:
                # line with something on it
                if not current_para:
                    current_para = line.strip()
                else:
                    current_para = current_para + " " + line.strip()
        if current_para:
            paras.append(Paragraph(cgi.escape(current_para), para_style))
        pdf.build(paras)
    format_text_card = staticmethod(format_text_card)

    def write_metadata(self):
        self.metadata['dont-crop-big-thumbnails'] = "true"
        if not self.metadata.get("title"):
            # make the title the first line of text
            self.metadata["title"] = read_file_handling_charset(os.path.join(self.folder, "contents.txt")).split('\n')[0].strip() + "..."
        FakePDFDoc.write_metadata(self)

    def get_pdf_version(self):
        if not (self.pdffile and os.path.exists(self.pdffile)):
            tfile = mktempfile()
            try:
                self.format_text_card(int(self.width), int(self.height), self.get_text_lines(self.doc), tfile,
                                      self.metadata.get("title"))
                self.pdffile = tfile
            except:
                if os.path.exists(tfile):
                    os.unlink(tfile)
                raise
        return self.pdffile


def ensure_assembly_line(confprop=None):
    global AssemblyLine
    if confprop:
        AssemblyLine = confprop
    if not AssemblyLine:
        if hasattr(tempfile, 'mkdtemp'):
            AssemblyLine = tempfile.mkdtemp()
        else:
            AssemblyLine = tempfile.mktemp()
        temp_AssemblyLine = true
    else:
        temp_AssemblyLine = false
    if not os.path.exists(AssemblyLine):
        os.makedirs(AssemblyLine)
    return temp_AssemblyLine

############################################################
###
###  Setup and Initialization code
###
############################################################

def update_configuration(conf=None):
    global AssemblyLine, ENSCRIPT, ENSCRIPT_CMD, PS2PDF, PS2PDF_CMD, FILE_CMD, ASSUME_TEXT_NO_COLOR
    global GHOSTSCRIPT, TIFFINFO, TIFFCP, TIFFSET, PDFTOTEXT_COMMAND, PDFTOTIFF_CMD_MONO, PDFTOTIFF_CMD_COLOR
    global OCR_WEB_SERVICE_URL, SUMMARY_LENGTH, PDFTOTEXT, TAR, TAR_CMD, TIFFSPLIT, SCORETEXT_THRESHOLD
    global ASSUME_NO_PASSWORD, SCORETEXT_CMD, SCORETEXT_MODEL, SCORETEXT, TIFF_SPLIT_CMD, TIFF_COMPRESS_CMD
    global HTMLDOC, HTMLDOC_CMD, TRANSFER_FORMAT, PDFTOPNG_CMD_MONO, PDFTOPNG_CMD_COLOR, PDFINFO
    global WORDBOXES_PDFTOTEXT_COMMAND, WORDBOXES_PDFTOTEXT, XDOC_OCR_WEB_SERVICE_URL, OCR_DEBUG
    global MS_TO_PDF_URL, SKEW_DETECT_URL, DESKEW_LIMIT_DEGREES, DRYCLEAN_SERVICE_URL
    global CODETIMER_ON, MSOFFICE_OCR_WEB_SERVICE_URL, SPLITUP_BINARY, SPLITUP_CMD, PDFLINKS, PDFLINKS_COMMAND
    global OPENOFFICE_CONVERT_TO_PDF, USE_OPENOFFICE_FOR_WEB, USE_OPENOFFICE_FOR_MSOFFICE, OOO_CONVERT_TO_PDF
    global OOO_WEB_TO_PDF_CMD, OOO_MSWORD_TO_PDF_CMD, OOO_POWERPOINT_TO_PDF_CMD, OOO_EXCEL_TO_PDF_CMD
    global OOO_MSWORD_XML_TO_PDF_CMD, OOO_POWERPOINT_XML_TO_PDF_CMD, OOO_EXCEL_XML_TO_PDF_CMD, OOO_RTF_TO_PDF_CMD
    global UPLIB_VERSION, UPLIB_LIBDIR, UPLIB_CLIENT_CERT, CODE_ENSCRIPT_COMMAND, BBOXES_FORMAT_VERSION_TO_CREATE
    global TOPDF_PORT, TOPDF_HOST, USE_TOPDF_FOR_WEB, USE_TOPDF_FOR_MSOFFICE, PUSH_TO_PDF
    global IMAGE_SIZE_LIMIT, DEFAULT_LANGUAGE, NENSCRIPT, NENSCRIPT_CMD, CODE_NENSCRIPT_COMMAND

    def expand_proxies(proxies_string):
        p = {}
        if proxies_string:
            for proxy_string in [s.strip() for s in proxies_string.split(",") if s]:
                host, proxy = tuple([q.strip() for q in proxy_string.split("=")])
                p[host] = proxy
        return p

    if not conf:
        conf = configurator()

    GHOSTSCRIPT = conf.get("ghostscript")
    TIFFINFO = conf.get("tiffinfo")
    TIFFCP = conf.get("tiffcp")
    TIFFSET = conf.get("tiffset")
    TIFFSPLIT = conf.get("tiffsplit")
    TIFF_SPLIT_CMD = conf.get("tiff-split-command")
    TIFF_COMPRESS_CMD = conf.get("tiff-compress-command")
    PDFTOTEXT = conf.get("pdftotext")
    PDFINFO = conf.get("pdfinfo")
    PDFTOTEXT_COMMAND = conf.get("pdftotext-command")
    PDFLINKS = conf.get("pdflinks")
    PDFLINKS_COMMAND = conf.get("pdflinks-command")
    WORDBOXES_PDFTOTEXT = conf.get("wordboxes-pdftotext")
    WORDBOXES_PDFTOTEXT_COMMAND = conf.get("wordboxes-pdftotext-command")
    BBOXES_FORMAT_VERSION_TO_CREATE = conf.get_int("wordbboxes-version-to-use")
    PDFTOTEXT_COMMAND = conf.get("pdftotext-command")
    PDFTOTIFF_CMD_MONO = conf.get("pdf-to-tiff-mono-command")
    PDFTOTIFF_CMD_COLOR = conf.get("pdf-to-tiff-color-command")
    PDFTOPNG_CMD_MONO = conf.get("pdf-to-png-mono-command")
    PDFTOPNG_CMD_COLOR = conf.get("pdf-to-png-color-command")
    OCR_WEB_SERVICE_URL = conf.get("ocr-url")
    XDOC_OCR_WEB_SERVICE_URL = conf.get("xdoc-ocr-url")
    MSOFFICE_OCR_WEB_SERVICE_URL = conf.get("msoffice-ocr-url")
    OPENOFFICE_CONVERT_TO_PDF = conf.get("openoffice-convert-to-pdf")
    USE_OPENOFFICE_FOR_WEB = conf.get_bool("use-openoffice-for-web-page-to-pdf")
    USE_OPENOFFICE_FOR_MSOFFICE = conf.get_bool("use-openoffice-for-msoffice-to-pdf")
    TOPDF_HOST = conf.get("topdf-binding-ip-address", "127.0.0.1")
    TOPDF_PORT = conf.get_int("topdf-port")
    if TOPDF_PORT > 0:
        USE_TOPDF_FOR_MSOFFICE = conf.get_bool("use-topdf-service-for-msoffice-to-pdf")
        USE_TOPDF_FOR_WEB = conf.get_bool("use-topdf-service-for-web-page-to-pdf")
        PUSH_TO_PDF = conf.get_bool("push-documents-to-topdf-service",
                                    TOPDF_HOST != "127.0.0.1")
    else:
        USE_TOPDF_FOR_MSOFFICE = False
        USE_TOPDF_FOR_WEB = False
    OOO_CONVERT_TO_PDF = conf.get("openoffice-convert-to-pdf")
    OOO_WEB_TO_PDF_CMD = conf.get("openoffice-web-to-pdf-command")
    OOO_MSWORD_TO_PDF_CMD = conf.get("openoffice-msword-to-pdf-command")
    OOO_POWERPOINT_TO_PDF_CMD = conf.get("openoffice-powerpoint-to-pdf-command")
    OOO_EXCEL_TO_PDF_CMD = conf.get("openoffice-excel-to-pdf-command")
    OOO_MSWORD_XML_TO_PDF_CMD = conf.get("openoffice-msword-xml-to-pdf-command")
    OOO_POWERPOINT_XML_TO_PDF_CMD = conf.get("openoffice-powerpoint-xml-to-pdf-command")
    OOO_EXCEL_XML_TO_PDF_CMD = conf.get("openoffice-excel-xml-to-pdf-command")
    OOO_RTF_TO_PDF_CMD = conf.get("openoffice-rtf-to-pdf-command")
    SUMMARY_LENGTH = conf.get_int("summary-length")
    TAR = conf.get("tar")
    TAR_CMD = conf.get("tar-command")
    ASSUME_NO_PASSWORD = conf.get_bool("assume-no-password", false)
    SCORETEXT = conf.get("scoretext")
    SCORETEXT_MODEL = conf.get("scoretext-model") 
    SCORETEXT_CMD = conf.get("scoretext-command")
    SCORETEXT_THRESHOLD = conf.get_int("scoretext-threshold")
    ENSCRIPT = conf.get("enscript")
    ENSCRIPT_CMD = conf.get("enscript-command")
    CODE_ENSCRIPT_COMMAND = conf.get("code-enscript-command")
    NENSCRIPT = conf.get("nenscript")
    NENSCRIPT = conf.get("nenscript-command")
    CODE_NENSCRIPT_COMMAND = conf.get("code-nenscript-command")
    PS2PDF = conf.get("ps2pdf")
    PS2PDF_CMD = conf.get("postscript-to-pdf-command")
    FILE_CMD = conf.get("file-command")
    ASSUME_TEXT_NO_COLOR = conf.get("assume-text-no-color")
    HTMLDOC = conf.get('htmldoc')
    HTMLDOC_CMD = conf.get('htmldoc-command')
    MS_TO_PDF_URL = conf.get("ms-to-pdf-url").strip()
    TRANSFER_FORMAT = conf.get('upload-transfer-format', 'zipped-folder')
    SKEW_DETECT_URL = conf.get('skew-detection-url')
    DESKEW_LIMIT_DEGREES = float(conf.get('deskew-limit-in-degrees', '0.5'))
    DRYCLEAN_SERVICE_URL = conf.get('dryclean-service-url')
    OCR_DEBUG = conf.get_bool("ocr-debug", false)
    Fetcher.set_standard_proxies(expand_proxies(conf.get("web-proxies")))
    CODETIMER_ON = conf.get_bool("codetimer-on", false)
    SPLITUP_BINARY = conf.get("splitup")
    SPLITUP_CMD = conf.get("splitup-command")
    UPLIB_VERSION = conf.get("UPLIB_VERSION")
    UPLIB_LIBDIR = conf.get("uplib-lib")
    UPLIB_CLIENT_CERT = conf.get("client-certificate-file")
    IMAGE_SIZE_LIMIT = conf.get("image-size-limit")
    DEFAULT_LANGUAGE = conf.get("default-language")

    return conf

def main (argv):

    global AssemblyLine, SCORETEXT_THRESHOLD, IMAGE_SIZE_LIMIT

    repository = None
    preserve_color = true
    metadata = {}
    notext = false
    comment = None
    upload = true
    verbosity = None
    nopassword = None
    saveblanks = false
    optimize = true
    listformats = false
    parserfiles = None
    metadata_file = None
    threshold = None
    early_upload = false
    icon_filename = None
    deskew = false
    cookies = None
    dryclean = false
    ocr = false
    specified_parser = None
    cookie=None
    image_size_limit = 0

    set_verbosity(0)
    conf = configurator()
    v = conf.get_int("verbosity") or 1
    set_verbosity(v)

    possible_opts = ["repository=", "title=", "dpi=", "list-formats", "scoretext-threshold=",
                     "categories=", "keywords=", "comment=", "authors=", "date=", "url=",
                     "early-upload", "nocolor", "notext", "noupload", "page-numbers=",
                     "nopassword", "nooptimize", "keepblankpages", "ocr",
                     "verbosity=", "first-page=", "tiff-dpi=", "extra-parsers=", "metadata=",
                     "deskew", "cookies=", "dryclean", "source=", "format=", "icon-file=",
                     "image-size-limit=", ]

    note(4, "Starting parameter processing in addDocument.main")
    try:
        optlist, args = getopt.getopt(argv[1:], "", possible_opts)
        for o, a in optlist:
            if o == "--repository":
                repository = a
            elif o == "--title":
                metadata['title'] = a
            elif o == "--extra-parsers":
                parserfiles = [os.path.expanduser(x) for x in string.split(a, PATH_SEPARATOR)]
            elif o == "--categories":
                metadata['categories'] = a
            elif o == "--notext":
                notext = true
            elif o == "--cookies":
                cookies = a
            elif o == "--comment":
                metadata['comment'] = a
            elif o == "--format":
                specified_parser = a
            elif o == "--keywords":
                metadata['keywords'] = a
            elif o == "--authors":
                metadata['authors'] = a
            elif o == "--date":
                metadata['date'] = a
            elif o == "--url":
                metadata['original-url'] = a
            elif o == "--verbosity":
                verbosity = int(a)
            elif o == "--nocolor":
                preserve_color = false
            elif o == "--noupload":
                upload = false
            elif o == "--keepblankpages":
                saveblanks = true
            elif o == "--nopassword":
                nopassword = true
            elif o == "--nooptimize":
                optimize = false
            elif o == "--early-upload":
                early_upload = true
            elif o == "--deskew":
                deskew = true
            elif o == "--dryclean":
                dryclean = true
            elif o == "--first-page":
                metadata['first-page-number'] = a
            elif o == "--page-numbers":
                metadata['page-numbers'] = a
            elif o == "--source":
                metadata['source'] = a
            elif o == "--tiff-dpi":
                metadata['images-dpi'] = a
            elif o == "--scoretext-threshold":
                threshold = int(a)
            elif o == "--image-size-limit":
                image_size_limit = int(a)
            elif o == "--ocr":
                ocr = true
            elif o == "--icon-file":
                icon_filename = a
            elif o == "--dpi":
                metadata['images-dpi'] = a
            elif o == "--list-formats":
                listformats = true
                upload = false
            elif o == "--metadata":
                if not os.path.exists(a):
                    raise IOError("File %s does not exist." % a)
                metadata_file = a

    except getopt.GetoptError, x:
        sys.stderr.write("Error:  %s.\n" % str(x))
        sys.stderr.write("Usage:  %s [options] [file, file, ...]\n" % argv[0])
        sys.stderr.write("Options are:\n"
                         "  --repository=https://HOST:PORT/ -- upload to this repository\n"
                         "  --repository=DIRECTORY -- put docs in the repository in this location\n"
                         "  --title=TITLE-STRING -- specify the document's title\n"
                         "  --categories=COMMA-SEPARATED-CATEGORY-LIST -- specify the document's categories\n"
                         "  --keywords=COMMA-SEPARATED-KEYWORD-LIST -- specify the document's keywords\n"
                         "  --authors=AND-SEPARATED-AUTHORS-LIST -- specify the document's authors\n"
                         "  --comment=COMMENT -- provide a comment about the document\n"
                         "  --date=MM/DD/YY -- specify the document's date\n"
                         "  --url=URL -- the url or filename from which this document originates\n"
                         "  --source=SOURCE -- the source of the document\n"
                         "  --first-page=N -- specify page number of first page\n"
                         "  --scoretext-threshold=N -- specify cutoff threshold for scoretext\n"
                         "  --notext -- the document doesn't contain any text\n"
                         "  --noupload -- just project the document without uploading it\n"
                         "  --rip -- project and rip the document without uploading it\n"
                         "  --disabled-rippers=COMMA-SEPARATED-RIPPER-NAMES -- if '--rip' is specified, skip these rippers\n"
                         "  --nopassword -- the repository doesn't have a password on it\n"
                         "  --nocolor -- there is no color in the document to preserve\n"
                         "  --nooptimize -- don't try to optimize compression of page images\n"
                         "  --ocr -- use OCR instead of trying to get the text from the document\n"
                         "  --deskew -- try to correct skewed images of text\n"
                         "  --dryclean -- try to clean up scanned page images\n"
                         "  --keepblankpages -- include page even if it is blank\n"
                         "  --list-formats -- list the MIME types that can be parsed\n"
                         "  --dpi=N -- specify DPI of an image input file (default is 300dpi)\n"
                         "  --metadata=FILENAME -- specify metadata file to add to documents\n"
                         "  --extra-parsers=FILENAMES -- specify extra parser classes to use\n"
                         "  --early-upload -- upload originals before processing page images\n"
                         "  --icon-file=FILENAME -- put icon in FILENAME as soon as possible\n"
                         "  --format=PARSER -- use parser named PARSER for this document\n"
                         "  --verbosity=LEVEL -- use LEVEL as the verbosity for debugging statements\n")
        sys.exit(1)

    if type(verbosity) == type(3):
        set_verbosity(verbosity)

    note(4, "Done with parameter processing in addDocument.main, figuring repository...")

    # see if we can figure out the repository to tell the configuration files
    if upload and not repository:
        repository = conf.get("default-repository")
    if upload:
        if not repository:
            sys.stderr.write("Error:  No repository specified.\n")
            sys.exit(1)
        else:
            parts = urlparse.urlparse(repository)
            if parts[0] != "https" and parts[0] != "http":
                sys.stderr.write("Error:  Specified repository does not use required HTTPS or HTTP scheme.\n")
                sys.exit(1)
            protocol = parts[0]
            hostport = parts[1]
            parts = string.split(hostport, ':')
            if len(parts) == 1:
                repo = (hostport, 80, protocol)
                port = 80
            else:
                port = string.atoi(parts[1])
                if port == 0:
                    sys.stderr.write("Error:  Bad port specified for repository:  " + repository + ".\n")
                    sys.exit(1)
                else:
                    repo = (parts[0], port, protocol)
                    set_configuration_port(port)
            conf = configurator()
    else:
        repo = ("", 0, "")

    note(4, "repository is %s.  Doing update_configuration in addDocument.main...", repo)

    update_configuration(conf)
    uthread.initialize()

    # check for extra document-format parsers
    note(4, "checking for extra document format parsers")
    p = conf.get("additional-document-parsers")
    if p:
        p = [os.path.expanduser(x) for x in string.split(p, PATH_SEPARATOR)]
        if parserfiles:
            parserfiles = parserfiles + p
        else:
            parserfiles = p
    if parserfiles:
        DocumentParser.find_parsers(parserfiles)

    if listformats:
        l = DocumentParser.list_formats()
        max_width = max([len(x.__name__) for x in l])
        sys.stdout.write("parser name%s: MIME type\n" % ((max_width - len("parser name")) * ' ',))
        sys.stdout.write("%s: ---------------\n" % (max_width * '-'))
        for parser in l:
            sys.stdout.write("%s%s: %s\n" % (parser.__name__, (max_width - len(parser.__name__)) * ' ', parser.format_mimetype))
        return 0

    if not cookies:
        cookies = conf.get("web-cookies-file")

    if cookies:
        set_cookies_source(cookies)

    # incorporate a metadata file, if one was specified
    if metadata_file:
        additional_md = read_metadata(metadata_file)
        metadata.update(additional_md)        

    saveblanks = saveblanks or conf.get_bool("preserve-blank-pages", false)
    use_png_page_images = conf.get_bool("use-png-page-images", false)

    uplib_path = conf.get("uplib-path")
    wait_period = 10

    note(4, "Checking password information")
    # prompt for the repository password unless it is passed in
    if os.environ.has_key("UPLIB_PASSWORD"):
        # valid password was passed in by caller of this module
        password = os.environ["UPLIB_PASSWORD"]
    elif os.environ.has_key("NO_UPLIB_PASSWORD"):
        # no password explicitly specified by caller of this module        
        password = ""
    elif not upload:
        # not going to be uploading anyway
        password = ""
    elif os.environ.has_key("UPLIB_COOKIE"):
        # we're going to be using a cookie instead
        cookie = os.environ["UPLIB_COOKIE"]
        password = ""
    elif not (nopassword or ASSUME_NO_PASSWORD):
        # prompt for the repository password
        note(4, "prompting for a password...")
        password = getpass("Password for repository: ")
    else:
        # there is no password
        password = ""
    note(4, "password is <%s>", password)

    if (threshold is not None):
        SCORETEXT_THRESHOLD = threshold

    if (image_size_limit > 0):
        IMAGE_SIZE_LIMIT = image_size_limit

    # make sure the assembly-line directory exists
    temp_AssemblyLine = ensure_assembly_line(conf.get("assembly-line"))

    try:

        # check to see that the guardian angel is running

#         if upload:
#             note(4, "Calling check_repository in addDocument.main...")
#             check_repository(repo)
#             note(4, "Done with check_repository in addDocument.main")
            
        exceptions = false
        exception_code = 0
        results = ()
        if len(args) > 0:
            for argx in args:
                note(4, "Handling arg [%s] in addDocument.main", argx)
                arg = os.path.expanduser(argx)

                results = DocumentParser.parse_document(arg, None,
                                                        password=password,
                                                        repository=repo,
                                                        saveblanks=saveblanks,
                                                        upload=upload,
                                                        notext=notext,
                                                        color=preserve_color,
                                                        metadata=metadata.copy(),
                                                        usepng=use_png_page_images,
                                                        optimize=optimize,
                                                        deskew=deskew,
                                                        dryclean=dryclean,
                                                        early_upload=early_upload,
                                                        ocr=ocr,
                                                        icon_file=icon_filename,
                                                        format=specified_parser,
                                                        cookie=cookie,
                                                        )
                def show_result(pname, res):

                    if (res is None):
                        sys.stderr.write("Couldn't find parser for %s.  Skipped it.\n" % pname)
                        return (true, 4)
                    elif isinstance(res, Exception):
                        return (true, show_exception(res))
                    elif (upload and type(res) == types.StringType):
                        note(2, "Uploaded %s to repository https://%s:%d/.", pname, repo[0], repo[1])
                        sys.stdout.write(quote_spaces(pname) + " " + res + "\n")
                        return (false, 0)
                    elif (isinstance(res, DocumentParser) and res.upload_id):
                        note(2, "Uploaded %s to repository https://%s:%d/.", pname, repo[0], repo[1])
                        sys.stdout.write(quote_spaces(pname) + " " + res.upload_id + "\n")
                        return (false, 0)
                    elif isinstance(res, DocumentParser):
                        note(2, "Converted %s to UpLib folder in %s", pname, res.folder)
                        #sys.stdout.write(quote_spaces(pname) + " " + res.folder + "\n")
                        return (false, 0)
                    elif type(res) in (types.ListType, types.TupleType):
                        eresult = None
                        for pname2, res2 in res:
                            exc_result, exc_code = show_result(pname2, res2)
                            if exc_result:
                                eresult = exc_code
                        if eresult is not None:
                            return (true, eresult)
                        else:
                            return (false, 0)
                    else:
                        sys.stderr.write("Couldn't identify format of file %s.  Skipping it.\n" % res[0])
                        return (true, 4)

                note(4, "results are %s", results)
                for pathname, result in results:
                    exc_result, exc_code = show_result(pathname, result)
                    if exc_result:
                        exceptions = true
                        exception_code = exc_code

        if temp_AssemblyLine and upload:
            try:
                shutil.rmtree(AssemblyLine)
            except OSError, x:
                note(2, "addDocument failed to delete AssemblyLine %s.  Error=%s" % (AssemblyLine, str(x)))
        if exceptions:
            return exception_code
        elif upload:
            return 0
        else:
            return results

    except Error, x:
        return show_exception(x)
    except:
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    os.environ['UPLIBLIB'] = os.getcwd()
    sys.exit(main(sys.argv))
