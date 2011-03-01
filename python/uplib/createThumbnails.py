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

import re, os, sys, string, time, shutil, tempfile, stat, traceback, gc, types
import math
from math import sqrt, log, exp

from PIL import Image, ImageOps, ImageChops, ImageDraw, ImageFont            # python image library (PIL)

import roman

from uplib.plibUtil import false, true, Error, note, configurator, set_verbosity, subproc, update_metadata, read_metadata
from uplib.ripper import Ripper
from uplib.newFolder import AbortDocumentIncorporation

TIFFSPLIT = None
TIFFCP = None
TIFF_SPLIT_CMD = None
THUMBNAIL_TYPE = None
NUMBERING_FONT = None
LEGEND_FONT = None
PREVIOUS_ICON = None
NEXT_ICON = None
TOP_ICON = None
FONT = None
LETTER_SIZE = None
USE_VIRTUAL_INK = false
AUTO_CROP_BIG_THUMBNAILS = true
DISTORT_VERY_SMALL_THUMBNAILS = false

# PAGEIMAGE_MAXWIDTH and PAGEIMAGE_MAXHEIGHT are used as the bounding box of a rectangle
# to shrink page images inside of.

PAGEIMAGE_MAXWIDTH = None
PAGEIMAGE_MAXHEIGHT = None

# the MAX_SCALING_FACTOR is used to make sure things don't expand too much
# beyond their "normal" size.  If the originals are 300dpi, and the normal presentation
# surface we're thumbnailing for is about 75-100dpi, we should shrink the originals
# to at least 1/3 of their original size.

MAX_SCALING_FACTOR = 0.33

# CONSTANT_AREA_FACTOR is used as a divisor to scale down the constant-area size
CONSTANT_AREA_FACTOR = 4.5

def load_font (fontname):
    if hasattr(ImageFont, "truetype") and fontname.lower().endswith(".ttf"):
        fnt = ImageFont.truetype(fontname, 14)
    else:
        fnt = ImageFont.load(fontname)
    return fnt

def thumbnail_translation_and_scaling (folder, d=None, update=true, recalc=false):
    
    # 'translation' is in units of points
    # 'scaling' is in units of pixels/point

    if d is None:
        d = dict()

    def find_data (key):
        return d.get(key) or doc_metadata.get(key)

    def parse_value (x):
        if x is None:
            return None
        elif type(x) in types.StringTypes:
            return eval('(' + x + ')')
        elif type(x) in types.TupleType:
            return x
        else:
            raise ValueError("argument " + str(x) + " must be string or tuple")

    metadata_file = os.path.join(folder, "metadata.txt")
    doc_metadata = read_metadata(metadata_file)

    if recalc:
        translation = None
        scaling = None
    else:
        translation = parse_value(doc_metadata.get("big-thumbnail-translation-points"))
        scaling = parse_value(doc_metadata.get("big-thumbnail-scaling-factor"))

    if scaling is None or translation is None:

        cropbox_data = find_data("cropping-bounding-box")
        images_size = eval('(%s)' % find_data("images-size"))
        if cropbox_data:
            cropbox = [eval('(%s)' % x) for x in cropbox_data.split(';')]
        else:
            cropbox = [(0,0), images_size]
        big_thumbnail_size = find_data("big-thumbnail-size")
        if big_thumbnail_size:
            big_tn_size = eval('(%s)' % big_thumbnail_size)
        else:
            from PIL import Image
            big_tn_size = Image.open(os.path.join(folder, "thumbnails", "big1.png")).size

        ppi = int(find_data("tiff-dpi") or find_data("images-dpi") or 300)

        # Remember that cropped page images have a 20 pixel border added back after scaling.
        #

        left_crop_border = 0
        right_crop_border = 0
        top_crop_border = 0
        bottom_crop_border = 0

        if cropbox_data:        
            if cropbox[0][0] != 0:
                left_crop_border = 20
            if cropbox[0][1] != 0:
                top_crop_border = 20
            if cropbox[1][0] != images_size[0]:
                right_crop_border = 20
            if cropbox[1][1] != images_size[1]:
                bottom_crop_border = 20

        # calculate a translation quantity in "points"
        translation = (0 - float((cropbox[0][0] - left_crop_border) * 72)/ppi,
                       0 - float((cropbox[0][1] - top_crop_border) * 72)/ppi)

        # calculate a scaling factor that goes from bounding box edges in "points" to
        # scaled thumbnail coordinates in "pixels"
        #
        scaling = (float(ppi * big_tn_size[0])/float(72 * (cropbox[1][0] - cropbox[0][0] + (left_crop_border + right_crop_border))),
                   float(ppi * big_tn_size[1])/float(72 * (cropbox[1][1] - cropbox[0][1] + (top_crop_border + bottom_crop_border))))

        # now read the wordboxes and calculate the thumbnail bounding boxes for them
        note(4, "    for %s:  translation is %f, %f, scaling is %f, %f",
             folder, translation[0], translation[1], scaling[0], scaling[1])

        if update:
            update_metadata(metadata_file,
                            {'big-thumbnail-scaling-factor' : "%f,%f" % scaling,
                             'big-thumbnail-translation-points' : "%f,%f" % translation})

    return translation, scaling

def figure_doc_size (tiff_file):
    im = Image.open(tiff_file)
    return im.size

def figure_bbox (tiff_file, pageno, existing_bbox, skips):
    if skips and pageno in skips:
        return existing_bbox or None
    im = Image.open(tiff_file)
    im = ImageOps.autocontrast(im.convert('L')) # in case the background is not *quite* white
    im = ImageChops.invert(im)  # we need our white background to be 0, not 255
    bbox = im.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        note(4, "    bbox for page %s is %s", pageno, bbox)
    if existing_bbox and bbox and (left > existing_bbox[0]):
        left = existing_bbox[0]
    if existing_bbox and bbox and (top > existing_bbox[1]):
        top = existing_bbox[1]
    if existing_bbox and bbox and (right < existing_bbox[2]):
        right = existing_bbox[2]
    if existing_bbox and bbox and (bottom < existing_bbox[3]):
        bottom = existing_bbox[3]
    return (bbox and (left, top, right, bottom)) or existing_bbox or (0, 0, im.size[0], im.size[1])
        

def add_page_no (im, location, page_no, boxed_width=None):
    number = ImageDraw.Draw(im)
    fnt = load_font(NUMBERING_FONT)
    if im.mode == "L":
        ink = 0
        boxcolor = 0xC0
    elif im.mode == "1":
        ink = 0
        boxcolor = 255
    elif im.mode == "RGB" or im.mode == "RGBA":
        ink = (0,0,0)
        boxcolor = (0xC0, 0xC0, 0xC0)
    else:
        raise Error("Odd mode detected in image:  %s", im.mode)
    if boxed_width:
        # boxed_right indicates width of area to write in
        width, height = number.textsize(str(page_no), font=fnt)
        lleft, ltop = location
        rect = (min((lleft + boxed_width)-(width + 8),lleft), ltop, lleft + boxed_width - 2, ltop + height + 4)
        number.rectangle (rect, outline=boxcolor)                          
        location = (lleft + boxed_width - (width + 5), ltop + 3)
    number.text(location, str(page_no), font=fnt, fill=ink)
    del number

def add_legend (im, legend):
    l = ImageDraw.Draw(im)
    fnt = load_font(LEGEND_FONT)
    if im.mode == "L" or im.mode == "1":
        ink = 0
    elif im.mode == "RGB" or im.mode == "RGBA":
        ink = (0,0,0)
    else:
        raise Error("Odd mode detected in image:  %s", im.mode)
    parsed_legends = []
    total_height = 0
    if im.mode == 'L' or im.mode == '1' or im.mode == 'P':
        im = im.convert('RGB')
        del l
        l = ImageDraw.Draw(im)
        ink = (0,0,0)
    for s in legend:
        m = re.match('\(([^)]+)\)(.*)$', s)
        if m:
            color = eval(m.group(1))
            s2 = m.group(2)
        else:
            color = ink
            s2 = s
        if im.mode == 'L':
            luminance = float(color) / 255.0
            background_color = ((luminance < 128) and 255) or 0
        elif im.mode == '1':
            background_color = ((color < 128) and 1) or 0
        else:
            luminance = float(color[0]) * 0.299 + float(color[1]) * 0.587 + float(color[2]) * 0.114
            background_color = ((luminance < 128) and (255, 255, 255)) or (0,0,0)
        height = l.textsize(s2, font=fnt)[1]
        parsed_legends.append((s2, color, background_color, height,))
        total_height = (((total_height > 0) and 5) or 0) + total_height + height
    x = 5
    y = im.size[1] - 5 - total_height
    i = 0
    for label, color, background_color, height in parsed_legends:
        note("      label = '%s', mode = %s, color = %s (%s), height = %s, ypos = %s", label, im.mode, color, background_color, height, y)
        l.text((x-1, y-1), label, fill=background_color, font=fnt)
        l.text((x-1, y+1), label, fill=background_color, font=fnt)
        l.text((x+1, y-1), label, fill=background_color, font=fnt)
        l.text((x+1, y+1), label, fill=background_color, font=fnt)
        l.text((x, y), label, fill=color, font=fnt)
        y = y + 5 + height
    del l
    return im

def virtual_ink_pixelify (img1, img2, x, y):

    """convert image to ink layer with alpha channel"""

    red, green, blue = img1.getpixel((x,y,))
    transparency = min(red, green, blue)
    opacity = 255 - transparency
    if (opacity == 0):
        newred = red
        newgreen = green
        newblue = blue
    else:
        newred = min(255, max(0, int(((red - transparency) * 255) / opacity)))
        newgreen = min(255, max(0, int(((green - transparency) * 255) / opacity)))
        newblue = min(255, max(0, int(((blue - transparency) * 255) / opacity)))
    img2.putpixel((x, y,), (newred, newgreen, newblue, opacity))


PAGE_RANGE = re.compile(r"^([0-9]+)(-|--)([0-9]+)$")
PAGE_NUMBERS = re.compile(r"^((b,[0-9]*,[0-9]+(-[0-9]+)*)|(d,[0-9]+,[0-9]+(-[0-9]+)*)|(r,[0-9]+,[0-9]+(-[0-9]+)*))(;"
                          r"((b,[0-9]*,[0-9]+(-[0-9]+)*)|(d,[0-9]+,[0-9]+(-[0-9]+)*)|(r,[0-9]+,[0-9]+(-[0-9]+)*)))*$")
PAGE_NUMBER_TYPES = { 'd': lambda x: str(x),
                      'b': lambda x: '',
                      'r': roman.toRoman,
                      }

def figure_page_numbers (pnstring, id):

    if pnstring is None:
        return None
    numbers = {}

    if PAGE_RANGE.match(pnstring.strip()):

        m = PAGE_RANGE.match(pnstring.strip())
        first_page = int(m.group(1))
        last_page = int(m.group(3))
        for i in range(last_page - first_page + 1):
            numbers[i] = first_page + i

    elif PAGE_NUMBERS.match(pnstring.strip()):

        parts = pnstring.strip().split(";")
        for part in parts:
            try:
                number_type, first_page, range_parts = part.split(",")
                range_parts = range_parts.split("-")
                if len(range_parts) == 2:
                    range_first = int(range_parts[0])
                    range_last = int(range_parts[1])
                else:
                    range_first = int(range_parts[0])
                    range_last = range_first
                number_type_fn = PAGE_NUMBER_TYPES[number_type.lower()]
                first_page = (first_page and int(first_page)) or 0
            except:
                typ, value, tb = sys.exc_info()
                note(2, "Badly formatted page-numbers string \"%s\"for document %s\n%s", pnstring, id,
                     string.join(traceback.format_exception(typ, value, tb)))
                return None
            for i in range(range_first, range_last + 1):
                numbers[i] = number_type_fn(first_page + (i - range_first))

    return numbers




def create_thumbnail (tiff_file, tiff_dpi, output_dir, page_no, first_page, page_count,
                      bbox, bbox_skips, big_thumbnail_size, small_thumbnail_size, icon_size,
                      maxwidth, maxheight, maxscaling,
                      thumbnail_strategy, legend=None, page_no_string=None):

    def fixsizes(size):
        if size[0] > 0:
            if size[1] > 0:
                return size
            else:
                return (size[0], 1)
        elif size[1] > 0:
            return (1, size[1])
        else:
            return (1, 1)

    big_output_file = os.path.join(output_dir, ("big%d" % (page_no + 1)) + ".png")
    small_output_file = os.path.join(output_dir, ("%d" % (page_no + 1)) + ".png")
    first_output_file = os.path.join(output_dir, "first.png")

    note(5, "     first_output_file is %s, big_output_file is %s, small_output_file is %s",
         first_output_file, big_output_file, small_output_file)
    if not maxwidth:
        maxwidth = PAGEIMAGE_MAXWIDTH
    if not maxheight:
        maxheight = PAGEIMAGE_MAXHEIGHT
    if not maxscaling:
        maxscaling = MAX_SCALING_FACTOR
    if not thumbnail_strategy:
        thumbnail_strategy = THUMBNAIL_TYPE
    note(5, "     maxwidth is %s, maxheight is %s, maxscaling is %s, thumbnail_strategy is %s",
         str(maxwidth), str(maxheight), maxscaling, thumbnail_strategy)
    status = false
    try:
        im = Image.open(tiff_file)
        if im.mode == "1":
            # bilevel
            im = ImageOps.grayscale(im.convert("L"))
        elif im.mode == "P":
            # paletted color -- doesn't scale well
            im = im.convert("RGB")
        if bbox and ((not bbox_skips) or (page_no not in bbox_skips)):
            # add a 20-pixel border to the large page images
            left = max(0, bbox[0] - 20)
            top = max(0, bbox[1] - 20)
            right = min(im.size[0], bbox[2] + 20)
            bottom = min(im.size[1], bbox[3] + 20)
        else:
            left = 0
            top = 0
            right = im.size[0]
            bottom = im.size[1]
        big_tn_im = im.crop((left, top, right, bottom,))
        if tiff_dpi:
            max_scaling = 100.0/float(tiff_dpi)
        else:
            max_scaling = MAX_SCALING_FACTOR
        # allow the user to override that limit (for example for a higher-res display)
        max_scaling = max(maxscaling, max_scaling)
        note(5, "     max_scaling is %s, right is %s, left is %s, top is %s, bottom is %s, tiff_dpi is %s",
             max_scaling, right, left, top, bottom, tiff_dpi)
        big_iscale_factor = min(float(max_scaling), min(float(maxwidth) / float(right - left), float(maxheight) / float(bottom - top)))
        newsize = (int(big_iscale_factor * big_tn_im.size[0]), int(big_iscale_factor * big_tn_im.size[1]))
        if (DISTORT_VERY_SMALL_THUMBNAILS):
            newsize = fixsizes(newsize)
        note(5, "     im.size is %s, big_tn_im.size is %s, big_iscale_factor is %s, big_size = %s", im.size, big_tn_im.size, big_iscale_factor, newsize)
        init_color = ((big_tn_im.mode == "L") and 0xFF) or ((big_tn_im.mode == "RGB") and (0xFF, 0xFF, 0xFF))
        big_tn = Image.new(big_tn_im.mode, (newsize[0] + 5 + NEXT_ICON.size[0], newsize[1]), init_color)
        if (big_tn.size[0] == 0 or big_tn.size[1] == 0):
            raise ValueError("big thumbnail has dimensions of %sx%s" % big_tn.size)
        resized_big = big_tn_im.resize(newsize, Image.ANTIALIAS)
        big_tn.paste(resized_big, (0, 0))
        big_thumbnail_size.append(int(newsize[0]))
        big_thumbnail_size.append(int(newsize[1]))
        if page_no_string is not None:
            if page_no_string:
                add_page_no (big_tn, (newsize[0] + 1, 1), page_no_string)
        elif (first_page + page_no) < 0:
            #from roman import toRoman
            #pagestr = toRoman(page_no - first_page + 1)
            #add_page_no (big_tn, (newsize[0] + 1, 1), pagestr, (5 + NEXT_ICON.size[0] - 1))
            pass
        elif first_page == 0 and page_no == 0:
            # no page numbers on 0 pages
            pass
        else:
            #add_page_no (big_tn, (newsize[0] + 1, 1), page_no, (5 + NEXT_ICON.size[0] - 1))
            add_page_no (big_tn, (newsize[0] + 1, 1), page_no + first_page)
        if page_no < (page_count - 1):
            righticon = NEXT_ICON.convert(big_tn.mode, dither=Image.NONE)
            big_tn.paste(righticon, (newsize[0] + 5, 50))
        if page_no > 0:
            lefticon = PREVIOUS_ICON.convert(big_tn.mode, dither=Image.NONE)
            big_tn.paste(lefticon, (newsize[0] + 5, 80))
        topicon = TOP_ICON.convert(big_tn.mode, dither=Image.NONE)
        big_tn.paste(topicon, (newsize[0] + 7, 200))
        if USE_VIRTUAL_INK:
            note(4, "      adding alpha channel to large thumbnail...")
            if big_tn.mode != 'RGBA':
                if big_tn.mode != 'RGB':
                    big_tn = big_tn.convert('RGB')
                new_tn = Image.new('RGBA', big_tn.size)
                tnw, tnh = big_tn.size
                for x in range(tnw):
                    for y in range(tnh):
                        virtual_ink_pixelify(big_tn, new_tn, x, y)
                big_tn = new_tn
            else:
                tnw, tnh = big_tn.size
                for x in range(tnw):
                    for y in range(tnh):
                        virtual_ink_pixelify(big_tn, big_tn, x, y)

        # now do the small page used in the sidebar
        small_iscale_factor = min(float(maxwidth) / float(im.size[0]), float(maxheight) / float(im.size[1])) / float(7)
        newsmallsize = (int(small_iscale_factor * im.size[0]), int(small_iscale_factor * im.size[1]))
        if DISTORT_VERY_SMALL_THUMBNAILS:
            newsmallsize = fixsizes(newsmallsize)
        small_tn = im.resize(newsmallsize, Image.ANTIALIAS)
        if (small_tn.size[0] == 0 or small_tn.size[1] == 0):
            raise ValueError("small thumbnail has dimensions of %sx%s" % small_tn.size)

        small_thumbnail_size.append(int(small_tn.size[0]))
        small_thumbnail_size.append(int(small_tn.size[1]))
        if page_no_string is not None:
            if page_no_string:
                add_page_no (small_tn, (5,5), page_no_string)
        elif (first_page + page_no) < 1:
            from uplib.roman import toRoman
            pagestr = toRoman(page_no + 1)
            add_page_no(small_tn, (5, 5), pagestr)
        elif first_page == 0 and page_no == 0:
            # no page numbers on 0 pages
            pass
        else:
            add_page_no(small_tn, (5, 5), (page_no + first_page))

        if not os.path.exists(output_dir): os.mkdir(output_dir); os.chmod(output_dir, 0700)
        if page_no == 0:
            note(5, "     Big thumbnail size is %sx%s, mode is '%s'", big_tn.size[0], big_tn.size[1], big_tn.mode)
        big_tn.save(big_output_file, "PNG")
        os.chmod(big_output_file, 0600)
        if page_no == 0:
            note(5, "     Small thumbnail size is %sx%s, mode is '%s'", small_tn.size[0], small_tn.size[1], small_tn.mode)
        small_tn.save(small_output_file, "PNG")
        os.chmod(small_output_file, 0600)

        global LETTER_SIZE
        if LETTER_SIZE is None:
            LETTER_SIZE = float((680 * 880) / (CONSTANT_AREA_FACTOR * CONSTANT_AREA_FACTOR))

        if page_no == 0:
            if thumbnail_strategy == "constant-rectangle":
                small_iscale_factor = min(float(maxwidth) / float(im.size[0]), float(maxheight) / float(im.size[1])) / 4.25
                tn = im.resize((small_iscale_factor * im.size[0], small_iscale_factor * im.size[1]),
                                     Image.ANTIALIAS)
            elif thumbnail_strategy == "constant-square":
                side_length = float(maxheight)/4.25
                small_iscale_factor = min(float(side_length) / float(im.size[0]), float(side_length) / float(im.size[1]))
                tn = im.resize((small_iscale_factor * im.size[0], small_iscale_factor * im.size[1]),
                                     Image.ANTIALIAS)
            elif thumbnail_strategy == "constant-area":
                tfactor = sqrt((680.0 * 880.0) / float(im.size[0] * im.size[1])) / CONSTANT_AREA_FACTOR
                newsize = (tfactor * im.size[0], tfactor * im.size[1])
                if DISTORT_VERY_SMALL_THUMBNAILS:
                    newsize = fixsizes(newsize)
                tn = im.resize(newsize, Image.ANTIALIAS)
            elif thumbnail_strategy == "linear":
                dpi = tiff_dpi or 300
                sfactor = ((im.size[0] * im.size[1])/(dpi * dpi))/(8.5 * 11)
                aspect_ratio = float(im.size[0])/float(im.size[1])
                new_width = int(math.sqrt(aspect_ratio * (sfactor * LETTER_SIZE)))
                new_height = int(new_width/aspect_ratio)
                if DISTORT_VERY_SMALL_THUMBNAILS:
                    new_width, new_height = fixsizes((new_width, new_height))
                note("      linear:  dpi is %s, relative_size is %s, new size = %d,%d",
                     dpi, sfactor, sfactor, new_width, new_height)
                tn = im.resize((new_width, new_height), Image.ANTIALIAS)
            elif thumbnail_strategy == "log-area":
                dpi = tiff_dpi or 300
                relative_size = ((float(im.size[0]) * float(im.size[1]))/(dpi * dpi))/(8.5 * 11)
                sfactor = math.sqrt(math.log(((((float(im.size[0]) * float(im.size[1]))/(dpi * dpi))*(math.e - 1))/(8.5 * 11))+1))
                aspect_ratio = float(im.size[0])/float(im.size[1])
                new_width = int(math.sqrt(aspect_ratio * (sfactor * LETTER_SIZE)))
                new_height = int(new_width/aspect_ratio)
                if DISTORT_VERY_SMALL_THUMBNAILS:
                    new_width, new_height = fixsizes((new_width, new_height))
                note("      log-area:  im.size is %s, dpi is %s, relative_size is %s, sfactor is %s, new size = %d,%d",
                     im.size, dpi, relative_size, sfactor, new_width, new_height)
                tn = im.resize((new_width, new_height), Image.ANTIALIAS)
            else:
                raise Error ("Unknown thumbnail strategy '%s'" % thumbnail_strategy)

            note(3, "      size of first.png is %s", tn.size)
            if icon_size is not None:
                icon_size.append(tn.size)

            if (tn.size[0] == 0 or tn.size[1] == 0):
                raise ValueError("document icon has dimensions of %sx%s" % tn.size)

            if legend:
                if hasattr(ImageFont, "truetype") and LEGEND_FONT.lower().endswith(".ttf"):
                    # assume Unicode-capable
                    legends = string.split(legend, "|")
                else:
                    # assume ASCII-only
                    legends = string.split(legend.encode("ascii", "replace"), "|")
                tn = add_legend(tn, legends)

            tn.save(first_output_file, "PNG")
            os.chmod(first_output_file, 0600)

        status = true

    finally:
        if not status:
            if os.path.exists(big_output_file): os.unlink(big_output_file)
            if os.path.exists(small_output_file): os.unlink(small_output_file)
            if os.path.exists(first_output_file): os.unlink(first_output_file)

    return status


# TEMPORARY_BACKGROUND = (0x99, 0xAC, 0xB9)
TEMPORARY_BACKGROUND = (0xE0, 0xF0, 0xF8)
LEGEND_COLOR = (0x99, 0xAC, 0xB9)
UNDER_CONSTRUCTION = None

def create_temporary_icons (metadata, dirpath, output_dir, params):
    global TEMPORARY_BACKGROUND, UNDER_CONSTRUCTION
    thumbnails_path = output_dir
    os.mkdir(thumbnails_path)
    note("thumbnails_path is %s", thumbnails_path)
    title = metadata.get("title")
    document_icon = Image.new("RGB", (150, 194), TEMPORARY_BACKGROUND)
    draw = ImageDraw.Draw(document_icon)
    draw.line((0,0) + document_icon.size, LEGEND_COLOR)
    draw.line((0, document_icon.size[1], document_icon.size[0], 0), LEGEND_COLOR)
    draw.rectangle((0, 0, document_icon.size[0]-1, document_icon.size[1] -1), outline=LEGEND_COLOR)
    if title: document_icon = add_legend(document_icon, ("(255, 255, 255)" + title,))
    document_icon.save(os.path.join(thumbnails_path, "first.png"), "PNG")
    page_1_big = Image.new("RGB", (425, 550), TEMPORARY_BACKGROUND)
    legend = []
    legend.append("(255,255,255)[temporary document]")
    if title: legend.append("(0,255,0)%s" % title)
    page_1_big = add_legend(page_1_big, legend)
    page_1_big.save(os.path.join(thumbnails_path, "big1.png"), "PNG")
    page_1_small = Image.new("RGB", (85, 110), TEMPORARY_BACKGROUND)
    add_page_no (page_1_small, (5, 5), "1")
    page_1_small.save(os.path.join(thumbnails_path, "1.png"), "PNG")
    update_metadata(os.path.join(dirpath, "metadata.txt"), {"page-count" : "1",
                                                            "tiff-width" : 2550,
                                                            "images-width" : 2550,
                                                            "images-size" : "2550,3300",
                                                            "cropping-bounding-box" : "0,0;2550,3300",
                                                            "big-thumbnail-size" : "425,550",
                                                            "small-thumbnail-size" : "85,110",
                                                            "small-thumbnail-scaling" : ("%f" % (float(1)/float(30))),
                                                            "images-height" : "3300",
                                                            "tiff-height" : "3300",
                                                            })


def do_thumbnails (dirpath, output_dir, **params):
    note(2, "  thumbnailing in %s...", dirpath)
    tmpdir = tempfile.mktemp()
    retval = params.get('returnvalue', false)
    doc_metadata_path = os.path.join(dirpath, "metadata.txt")
    try:
        os.mkdir(tmpdir)
        os.chmod(tmpdir, 0700)
        try:

            md = read_metadata(doc_metadata_path)
            is_temporary_doc = md.get("temporary-contents")
            if is_temporary_doc and (is_temporary_doc == "true"):
                # temporary -- don't spend much time on this
                create_temporary_icons (md, dirpath, output_dir, params)
                retval = true
                return

            if os.path.exists(os.path.join(dirpath, "document.tiff")):
                # contains one single-page TIFF file
                tiffmaster = os.path.join(tmpdir, "master.tiff")
                split_command = (TIFF_SPLIT_CMD
                                 % (TIFFCP, os.path.join(dirpath, "document.tiff"), tiffmaster,
                                    TIFFSPLIT, tiffmaster, os.path.join(tmpdir, "x")))
                status, output, tsignal = subproc(split_command)
                if status != 0:
                    raise Error ("'%s' signals non-zero exit status %d in %s => %s"
                                 % (split_command, status, dirpath, tmpdir))
                parts_dir = tmpdir
                filecheck_fn = lambda fn: fn[0] == "x"
            elif (os.path.exists(os.path.join(dirpath, "page-images")) and
                  os.path.isdir(os.path.join(dirpath, "page-images"))):
                # contains directory full of PNG page images
                parts_dir = os.path.join(dirpath, "page-images")
                filecheck_fn = lambda fn: (fn.startswith('page') and fn.endswith('.png'))
            else:
                raise Error("No page images for document in %s" % dirpath)

            tiff_parts = os.listdir(parts_dir)
            if len(tiff_parts) < 1:
                raise Error("No pages in split tiff file directory after split!")
            # either a PNG-images or a TIFF split will sort properly in lexicographic order
            tiff_parts.sort()

            # see if there's a document icon legend and info about the DPI of the tiff file
            legend = md.get('document-icon-legend')
            tiff_dpi = int(md.get('images-dpi') or md.get('tiff-dpi') or params.get('images-dpi') or 0)
            page_numbers_v = md.get('page-numbers')
            page_numbers = (page_numbers_v and figure_page_numbers(page_numbers_v, dirpath))
            first_page = int(md.get('first-page-number', 1))
            skips = md.get('document-bbox-pages-to-skip', '')
            if skips:
                parts = string.split(skips, ':')
                bbox_skips = []
                for part in parts:
                    bbox_skips = bbox_skips + map(int, string.split(part, ','))
            else:
                bbox_skips = None

            # figure bounding box for imaged page
            page_count = 0
            bbox = None
            note(2, "    calculating bounding box for large pages...")
            dont_crop = md.get('dont-crop-big-thumbnails', false)
            if AUTO_CROP_BIG_THUMBNAILS and not dont_crop:
                do_bbox = true
            else:
                do_bbox = false
            for tiff_part in tiff_parts:
                if not filecheck_fn(tiff_part):
                    continue
                if page_count == 0:
                    # find the width and height of the document
                    docwidth, docheight = figure_doc_size(os.path.join(parts_dir, tiff_part))
                    if not do_bbox:
                        bbox = (0, 0, docwidth, docheight)
                if do_bbox:
                    bbox = figure_bbox (os.path.join(parts_dir, tiff_part), page_count, bbox, bbox_skips)
                if (bbox and bbox[0] == 0) and (bbox[1] == 0) and (bbox[2] >= docwidth) and (bbox[3] >= docheight):
                    # don't bother, there's no area to crop already
                    do_bbox = false
                page_count = page_count + 1
            if page_count == 0:
                raise Error("No pages in split tiff file directory after split!")
            note(2, "      final bbox is %s, page_count is %d", bbox, page_count)

            if USE_VIRTUAL_INK:
                note(2, "      alpha channels will be added to large thumbnails...")

            # now make the thumbnails
            big_thumbnail_size = []
            small_thumbnail_size = []
            icon_size = []
            page_index = 0
            for tiff_part in tiff_parts:
                if not filecheck_fn(tiff_part):
                    note(3, "    skipping %s", tiff_part)
                    continue
                tiff_path = os.path.join(parts_dir, tiff_part)
                if page_numbers:
                    page_no_string = page_numbers.get(page_index)
                else:
                    page_no_string = None
                note (2, "    page %d%s", page_index, (page_no_string and "   (%s)" % page_no_string) or "")
                try:
                    if not create_thumbnail(tiff_path, tiff_dpi, output_dir,
                                            page_index, first_page, page_count, bbox, bbox_skips,
                                            big_thumbnail_size, small_thumbnail_size, icon_size,
                                            params.get('maxwidth'), params.get('maxheight'), params.get('maxscaling'),
                                            params.get('thumbnail_strategy'), legend, page_no_string):
                        raise Error ("Can't create thumbnail for page %d in %s (of %s)" % (page_index, tiff_path, dirpath))
                except Exception, x:
                    doc_id = os.path.split(dirpath)[1]
                    note("exception creating thumbnails for page %d of document %s:\n%s", page_index, doc_id,
                         string.join(traceback.format_exception(*sys.exc_info()), ""))
                    raise AbortDocumentIncorporation(doc_id, str(x))

                if page_index == 0:
                    bt_width = big_thumbnail_size[0]
                    bt_height = big_thumbnail_size[1]
                    st_width = small_thumbnail_size[0]
                    st_height = small_thumbnail_size[1]
                else:
                    bt_width = max(bt_width, big_thumbnail_size[0])
                    bt_height = max(bt_height, big_thumbnail_size[1])
                    st_width = max(st_width, small_thumbnail_size[0])
                    st_height = max(st_height, small_thumbnail_size[1])
                st_scaling = (float(st_width)/float(docwidth) + float(st_height)/float(docheight)) / 2.0
                page_index = page_index + 1

            d = {"page-count" : str(page_count),
                 "tiff-width" : str(docwidth),
                 "images-width" : str(docwidth),
                 "images-size" : "%d,%d" % (docwidth, docheight),
                 "cropping-bounding-box" : "%d,%d;%d,%d" % (bbox),
                 "big-thumbnail-size" : "%s,%s" % (bt_width, bt_height),
                 "small-thumbnail-size" : "%s,%s" % (st_width, st_height),
                 "small-thumbnail-scaling" : "%f" % st_scaling,
                 "icon-size" : "%d,%d" % icon_size[0],
                 "images-height" : str(docheight),
                 "tiff-height" : str(docheight) }

            translation, scaling = thumbnail_translation_and_scaling(dirpath, d, false, true)
            d["big-thumbnail-translation-points"] = "%f,%f" % translation
            d["big-thumbnail-scaling-factor"] = "%f,%f" % scaling
            update_metadata(os.path.join(dirpath, "metadata.txt"), d)

        finally:
            shutil.rmtree(tmpdir)

        # indicate successful completion
        note(2, "  finished.")
        retval = true

    finally:
        if not retval:
            if os.path.exists(output_dir): shutil.rmtree(output_dir)

def update_configuration():

    global TIFFSPLIT, TIFFCP, THUMBNAIL_TYPE, TIFF_SPLIT_CMD, NUMBERING_FONT, LEGEND_FONT, PREVIOUS_ICON, NEXT_ICON, MAX_SCALING_FACTOR
    global PAGEIMAGE_MAXWIDTH, PAGEIMAGE_MAXHEIGHT, TOP_ICON, CONSTANT_AREA_FACTOR, USE_VIRTUAL_INK, UNDER_CONSTRUCTION
    global AUTO_CROP_BIG_THUMBNAILS, DISTORT_VERY_SMALL_THUMBNAILS

    note(3, "in createThumbnails.update_configuration()")

    conf = configurator.default_configurator()

    TIFFSPLIT = conf.get("tiffsplit")
    TIFFCP = conf.get("tiffcp")
    TIFF_SPLIT_CMD = conf.get("tiff-split-command")
    THUMBNAIL_TYPE = conf.get("thumbnail-strategy", "log-area")
    NUMBERING_FONT = conf.get("numbering-font-file")
    LEGEND_FONT = conf.get("legend-font-file")
    previous_page_icon_file = conf.get("previous-page-icon-file")
    if not previous_page_icon_file:
      note(0, "No previous-page-icon-file parameter in site.config nor .uplibrc")
      note(0, "Aborting update_configuration!")
      raise IOError("No previous-page-icon-file parameter in site.config nor .uplibrc")
    try:
      PREVIOUS_ICON = Image.open(previous_page_icon_file)
    except IOError:
      note(0, "Could not load %s as an image." % previous_page_icon_file);
      note(0, "Aborting update_configuration!")
      raise IOError("Could not load %s." % previous_page_icon_file)
    next_page_icon_file = conf.get("next-page-icon-file")
    if not next_page_icon_file:
      note(0, "No next-page-icon-file parameter was found in site.config nor .uplibrc.");
      note(0, "Aborting update_configuration!")
      raise IOError("No next-page-icon-file parameter in config")
    try:
      NEXT_ICON = Image.open(next_page_icon_file)
    except IOError:
      note(0, "Could not load %s as an image." % next_page_icon_file);
      note(0, "Aborting update_configuration!")
      raise IOError("Cound not load %s." % next_page_icon_file)
    temp = Image.open(conf.get("top-icon-file"))
    TOP_ICON = Image.new(temp.mode, temp.size, (255, 255, 255))
    TOP_ICON.paste(temp, (0, 0), temp)
    MAX_SCALING_FACTOR = float(conf.get("page-image-max-scaling-factor") or "0.33")
    PAGEIMAGE_MAXWIDTH = float(conf.get("page-image-max-width-pixels") or "680")
    PAGEIMAGE_MAXHEIGHT = float(conf.get("page-image-max-height-pixels") or "880")
    CONSTANT_AREA_FACTOR = float(conf.get("constant-area-factor") or "4.5")
    USE_VIRTUAL_INK = conf.get_bool("use-alpha-channel-thumbnails", false)
    AUTO_CROP_BIG_THUMBNAILS = conf.get_bool("auto-crop-big-thumbnails", true)
    DISTORT_VERY_SMALL_THUMBNAILS = conf.get_bool("keep-very-small-thumbnails", false)
    images_dir = os.path.join(conf.get("uplib-share"), "images")
    # UNDER_CONSTRUCTION = Image.open(os.path.join(images_dir, "swirl.png"))
                               

def thumbnail_folder(repo, path):
    note("doing thumbnail_folder in %s", path)
    if (os.path.isdir(path) and
        (os.path.exists(os.path.join(path, "document.tiff")) or
         os.path.isdir(os.path.join(path, "page-images")))):
        do_thumbnails(path, os.path.join(path, "thumbnails"))
    else:
        note("Either path %s or document.tiff or page-images is missing!", path)


class ThumbnailRipper (Ripper):

    def rip(self, location, doc_id):

        thumbnail_folder(self.repository(), location)

    def rerun_after_metadata_changes (self, changed_fields=None):
        return (changed_fields and ("images-dpi" in changed_fields or
                                    "page-numbers" in changed_fields or
                                    "first-page-number" in changed_fields or
                                    "document-icon-legend" in changed_fields))
                               

update_configuration()

if __name__ == "__main__":
    if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
        sys.stderr.write("Usage:  python createThumbnails.py FOLDERPATH\n")
        sys.exit(1)
    path = sys.argv[1]
    update_configuration()
    set_verbosity(5)
    do_thumbnails(path, os.path.join(path, "thumbnails"))
