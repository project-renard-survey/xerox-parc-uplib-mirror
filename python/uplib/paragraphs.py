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
# Code to implement paragraph breaking
#


import os, sys, re, string, cgi, StringIO, base64, math, traceback, pprint
from xml.dom.minidom import getDOMImplementation
from unicodedata import category as unitype

try:
    from PIL import Image, ImageChops, ImageOps, ImageDraw, ImageColor
except:
    raise ImportError("Python does not have the Python Imaging Library (PIL) available")

from uplib.plibUtil import wordboxes_page_iterator, true, false, read_metadata, note, update_metadata, Error, lock_folder, unlock_folder, URLPATTERN, EMAILPATTERN, GEMAILPATTERN, wordboxes_for_span, CHARSET_PATTERN, LANGUAGE_PATTERN, read_illustrations_metadata, read_file_handling_charset_returning_bytes, topological_sort, SortError
from uplib.webutils import htmlescape, HTTPCodes
from uplib.ripper import Ripper
from uplib.createIndexEntry import index_folder
from uplib.collection import QueryCollection
from uplib.basicPlugins import show_abstract, show_title, STANDARD_BACKGROUND_COLOR, STANDARD_TOOLS_COLOR
from uplib.basicPlugins import __issue_javascript_head_boilerplate as issue_javascript_head_boilerplate
from uplib.basicPlugins import __issue_menu_definition as issue_menu_definition
from uplib.basicPlugins import __issue_title_styles as issue_title_styles
from uplib.basicPlugins import output_tools_block, output_query_stats, output_footer

COLORTABLE = 128 * (255,) + 128 * (0,)
LEFT_ALIGN = "left"
RIGHT_ALIGN = "right"
CENTER_ALIGN = "center"

IMAGE_HEIGHT = 150

BORDERWIDTH = 0

EMBED_IMAGES = true

REFERENCE_INDICATOR = re.compile('(\[[0-9]+\])|([0-9]+\.)|(\[[A-Za-z0-9]+\])')
BULLET_INDICATOR = re.compile(u'\u2022\s+')

class NoWordboxesError(Error):
    pass

def transform_point (x, y, translation, scaling):

    # int will truncate, so call it trunc
    trunc = int

    return (trunc((x + translation[0]) * scaling[0] + 0.5),
            trunc((y + translation[1]) * scaling[1] + 0.5))

class Box (object):
    def __init__(self, x1, y1, x2, y2):
        self.x0 = x1
        self.y0 = y1
        self.x1 = x2
        self.y1 = y2
    def width (self):
        return abs(self.x1 - self.x0)
    def height (self):
        return abs(self.y1 - self.y0)
    def y_overlaps (self, other):
        return ((self.top() < other.bottom()) and (other.top() < self.bottom()))
    def x_overlaps (self, other):
        return ((self.left() < other.right()) and (other.left() < self.right()))
    def overlaps (self, other):
        return self.y_overlaps(other) and self.x_overlaps(other)
    def percent_y_overlaps (self, other):
        if not self.y_overlaps(other):
            return 0
        elif self.height() == 0:
            return 100
        else:
            return (max(self.top(), other.top()) - min(self.bottom(), other.bottom()) / float(self.height()))
    def percentage_overlap (self, other):
        if not (self.y_overlaps(other) and self.x_overlaps(other)):
            return 0.0
        elif (self.height() == 0) or (self.width() == 0):
            return 1.0
        else:
            h = max(self.top(), other.top()) - min(self.bottom(), other.bottom())
            w = max(self.left(), other.left()) - min(self.right(), other.right())
            return (w * h) / (float(self.height() * self.width()))
    def left(self):
        return self.x0
    def right(self):
        return self.x1
    def top(self):
        return self.y0
    def bottom(self):
        return self.y1
    def expand(self, other):
        self.x0 = min(self.x0, other.left())
        self.x1 = max(self.x1, other.right())
        self.y0 = min(self.y0, other.top())
        self.y1 = max(self.y1, other.bottom())
    def transform(self, translation, scaling):
        self.x0, self.y0 = transform_point(self.x0, self.y0, translation, scaling)
        self.x1, self.y1 = transform_point(self.x1, self.y1, translation, scaling)
    def centricity(self, other):
        """simple measure of how centered one rectangle is inside the other"""
        return ((other.right() - self.left())/self.width() *
                (other.bottom() - self.top())/self.height() *
                (self.right() - other.left())/self.width() *
                (self.bottom() - other.top())/self.height())
    def aspect(self):
        """aspect ratio:  height/width"""
        return self.height()/self.width()
    def __repr__(self):
        return '<%s (%.1f,%.1f),(%.1f,%.1f)>' % (self.__class__.__name__, self.x0, self.y0, self.x1, self.y1)
    def __str__(self):
        return '<%s (%.1f,%.1f),(%.1f,%.1f)>' % (self.__class__.__name__, self.x0, self.y0, self.x1, self.y1)
    def __unicode__(self):
        return u'<%s (%.1f,%.1f),(%.1f,%.1f)>' % (self.__class__.__name__, self.x0, self.y0, self.x1, self.y1)

class WordBox (Box):
    def __init__(self, x1, y1, x2, y2, baseline):
        Box.__init__(self, x1, y1, x2, y2)
        self.base = baseline
    def baseline(self):
        return self.base

class ImageBox (Box):

    def __init__(self, x1, y1, width, height, type, bits):
        Box.__init__(self, x1, y1, x1 + width, y1 + height)
        self.imagetype = type
        self.bits = bits
        self.inserted = False

class URLBox (Box):

    def __init__(self, leftf, topf, widthf, heightf, url, page_index):
        Box.__init__(self, int(leftf), int(topf), int(leftf + widthf), int(topf + heightf))
        self.url = url
        self.page = page_index

class Space (Box):
    pass

class PartBox (WordBox):
    def __init__(self, box):
        WordBox.__init__(self, box.left(), box.top(), box.right(), box.bottom(), box.baseline())
        self.box = box
        self.textstr = box.text()
        self.ENDS_WORD = box.ends_word()
        self.ENDS_LINE = box.ends_line()
        self.HAS_HYPHEN = box.has_hyphen()
        self.FIXED_WIDTH = box.is_fixedwidth()
        self.ITALIC = box.is_italic()
        self.BOLD = box.is_bold()
        self.SERIF = box.is_serif()
        self.SYMBOL = box.is_symbol()
        self.fontsize = box.font_size()
        self.offset = box.contents_offset()

    def is_fixedwidth(self):
        return self.box.is_fixedwidth()

    def is_italic(self):
        return self.box.is_italic()

    def is_bold(self):
        return self.box.is_bold()

    def is_serif(self):
        return self.box.is_serif()

    def is_symbol(self):
        return self.box.is_symbol()

    def font_size(self):
        return self.box.font_size()

    def ends_word(self):
        return self.box.ends_word()

    def ends_line(self):
        return self.box.ends_line()

    def has_hyphen(self):
        return self.box.has_hyphen()

    def rotation(self):
        return self.box.rotation()

    def font_type(self):
        return self.box._font_type

    def baseline(self):
        return self.box.baseline()

    def flags(self):
        return self.box.flags()

    def append(self, box):
        self.expand(box)
        self.textstr = self.textstr + box.text()
        self.ENDS_LINE = box.ends_line()
        self.ENDS_WORD = box.ends_word()
        self.HAS_HYPHEN = box.has_hyphen()
        self.box = box

    def text(self):
        return self.textstr

    def nchars(self):
        return len(self.textstr)

    def avg_char_width(self):
        if self.textstr and len(self.textstr) > 0:
            return self.width() / len(self.textstr)
        else:
            return 0

class Paragraph (Box):
    def __init__(self, breaktype):
        Box.__init__(self, 999999, 999999, -1, -1)
        self.lines = []
        self.breaktype = breaktype
        # these units are in PIL coordinates -- upper left corner is 0,0
        self.indent = None
        self.lastleft = 99999
        self._line_spacing_accum = 0
        self._line_height_accum = 0
        self._center_accum = 0
        self._charwidth_accum = 0
        self._font_size_accum = 0
        self.occluded = False
        self.__text = None

    def __unicode__(self):
        t = self.text()
        return u'<Paragraph %dx%d+%d+%d \'%s\' "%s"%d>' % (
            self.width(), self.height(), self.left(), self.top(), self.breaktype, t[:min(len(t), 30)], len(t))

    def __str__(self):
        return self.__unicode__().encode("UTF-8", "strict")

    def __repr__(self):
        return self.__unicode__().encode("ASCII", "backslashreplace")

    def figure_text(words):
        t = u""
        # need to be able to test for last word
        words = [x for x in words]
        lastword = words[-1]
        for w in words:
            if w.ends_line():
                if w.has_hyphen() and (w != lastword):
                    txt = w.text()[:-1]
                else:
                    txt = w.text() + u" "
            elif w.ends_word():
                txt = w.text() + u" "
            else:
                txt = w.text()
            t += txt
        return t.strip()
    figure_text=staticmethod(figure_text)

    def add(self, line):
        if len(self.lines) > 0:
            self._line_spacing_accum += max(0, (line.top - self.lines[-1].bottom))
        self.lastleft = line.left
        if len(self.lines) == 0:
            self.indent = line.left
        self.lines.append(line)
        if self.x0 > line.left:
            self.x0 = line.left
        if self.x1 < line.right:
            self.x1 = line.right
        if self.y0 > line.top:
            self.y0 = line.top
        if self.y1 < line.bottom:
            self.y1 = line.bottom
        self._line_height_accum += line.height
        self._center_accum += (line.left + line.right)/2.0
        self._charwidth_accum += line.avg_char_width()
        self._font_size_accum += line.avg_font_size()
        self.__text = None
        return self

    def avg_char_width(self):
        if len(self.lines) > 0:
            return float(self._charwidth_accum)/len(self.lines)

    def avg_line_spacing(self):
        if len(self.lines) > 1:
            return self._line_spacing_accum/float(len(self.lines)-1)
        else:
            return self.max_line_height() * 0.2

    def avg_line_height (self):
        if len(self.lines) > 0:
            return self._line_height_accum/float(len(self.lines))
        else:
            return 0

    def avg_font_size (self):
        if len(self.lines) > 0:
            return self._font_size_accum/float(len(self.lines))
        else:
            return 0

    def avg_center_position (self):
        if len(self.lines) > 0:
            return self._center_accum/float(len(self.lines))
        else:
            return 0

    def max_line_height (self):
        return max([x.height for x in self.lines])

    def text(self):
        if self.__text is None:
            self.__text = Paragraph.figure_text(self.words())
        return self.__text

    def words(self):
        for line in self.lines:
            for word in line.words:
                yield word

    def first_word(self):
        if self.lines:
            return self.lines[0].words[0]
        else:
            return None

    def last_word(self):
        if self.lines:
            return self.lines[-1].words[-1]
        else:
            return None

    def all_caps(self):
        t = self.text()
        return re.search("[A-Z]", t) and not re.search("[a-z]", t)

    def nwords(self):
        return sum([len(x.words) for x in self.lines])

class Line:

    __avg_adjusted_interword_gap = 0.0
    __avg_interword_gap_count = 0

    def __init__(self):
        self.words = []
        # these units are in PIL coordinates -- upper left corner is 0,0
        self.left = 999999
        self.right = -1
        self.top = 99999
        self.bottom = -1
        self.lastleft = 99999
        self._baseline = None
        self.width = 0
        self.height = 0
        self._word_width_accum = 0
        self._interword_gap_accum = 0
        self._word_count = 0
        self._gutter_classes = set()

    def __unicode__(self):
        t = self.text()
        return u'<%s %dx%d+%d+%d "%s"%d>' % (
            self.__class__.__name__, self.width, self.height, self.left, self.top, t[:min(len(t), 20)], len(t))            

    def __str__(self):
        return self.__unicode__().encode("UTF-8", "strict")

    def __repr__(self):
        return self.__unicode__().encode("ASCII", "backslashreplace")

    def y_overlaps (self, other):
        return ((self.top < other.bottom) and (other.top < self.bottom))

    def amount_y_overlaps (self, other):
        return (min(self.bottom, other.bottom) - max(self.top, other.top))/float(self.bottom - self.top)

    def x_overlaps (self, other):
        return ((self.left < other.right) and (other.left < self.right))

    def overlaps (self, other):
        return self.y_overlaps(other) and self.x_overlaps(other)

    def percentage_overlap (self, other):
        if not (self.y_overlaps(other) and self.x_overlaps(other)):
            return 0.0
        elif (self.height <= 0) or (self.width <= 0):
            return 1.0
        else:
            h = max(self.top, other.top) - min(self.bottom, other.bottom)
            w = max(self.left, other.left) - min(self.right, other.right)
            return (w * h) / (float(self.height * self.width))

    def copy (self):
        newl = self.__class__()
        for w in self.words:
            newl.add(w)
        return newl

    def add(self, wordbox):
        if isinstance(wordbox, Line):
            for w in wordbox.words:
                self.add(w)
        else:
            position = None
            for i in range(len(self.words)):
                if wordbox.left() < self.words[i].left():
                    position = i
                    break
            if position is None:
                self.words.append(wordbox)
            else:
                self.words.insert(position, wordbox)
            if self.left > wordbox.left():
                self.left = wordbox.left()
            if self.right < wordbox.right():
                self.right = wordbox.right()
            if self.top > wordbox.top():
                self.top = wordbox.top()
            if self.bottom < wordbox.bottom():
                self.bottom = wordbox.bottom()
            self._baseline = None
            self.width = self.right - self.left
            self.height = self.bottom - self.top
            self._word_width_accum += wordbox.width()
            if wordbox.ends_word():
                self._word_count += 1
            if len(self.words) > 1:
                gap = self.words[-1].left() - self.words[-2].right()
                self._interword_gap_accum += gap
                Line.__avg_adjusted_interword_gap += (gap/self.height)
                Line.__avg_interword_gap_count += 1

    def avg_interword_gap(self):
        if len(self.words) > 1:
            return self._interword_gap_accum / float(len(self.words)-1)
        else:
            return 0.0

    def avg_adjusted_interword_gap(self):
        if Line.__avg_interword_gap_count > 1:
            return (Line.__avg_adjusted_interword_gap / float(Line.__avg_interword_gap_count)) * self.height
        else:
            return 0.0

    def avg_word_width(self):
        if len(self.words) < 1:
            return 0.0
        else:
            return self._word_width_accum / float(len(self.words))

    def avg_font_size(self):
        if len(self.words) > 0:
            sum = 0.0
            count = 0
            for word in self.words:
                if hasattr(word, "fontsize"):
                    sum += word.fontsize
                count += 1
            return sum/count
        else:
            return 0                    

    def avg_char_width(self):
        if len(self.words) > 0:
            sum = 0.0
            count = 0
            for word in self.words:
                sum += word.width()
                count += len(word.text())
            if count > 0:
                return sum/count
            else:
                return 0
        else:
            return 0

    def is_italic(self):
        return reduce(lambda collector, value: (collector and value), [x.is_italic() for x in self.words], True)

    def is_bold(self):
        return reduce(lambda collector, value: (collector and value), [x.is_bold() for x in self.words], True)

    def avg_line_height (self):
        count = 0.0
        sum = 0.0
        for word in self.words:
            count += word.width()
            sum += (word.height() * word.width())
        return ((count > 0) and (sum/count)) or 0

    def baseline(self):
        if (self._baseline is None) and self.words:
            # figure mode baseline
            blines = {}
            for word in self.words:
                b = word.baseline()
                if b in blines:
                    blines[b] += len(word.text())
                else:
                    blines[b] = len(word.text())
            if blines:
                self._baseline = max(blines.items(), key=lambda x: x[1])[0]
        if self._baseline is not None:
            return self._baseline
        else:
            return self.bottom

    def max_line_height (self):
        return max([word.height() for word in self.words])

    def text(self):
        t = u""
        for w in self.words:
            t += w.text()
            if w.ends_line() and w is not self.words[-1]:
                if (not w.has_hyphen()) or (w.text() == u"-"):
                    t += u" "
            elif w.ends_word():
                t += u" "
        return t

def figure_lineheight_difference (line1, line2):
    height1 = line1.avg_line_height()
    height2 = line2.avg_line_height()
    #height1 = line1.height
    #height2 = line2.height
    divisor = float(min(height1, height2))
    if -0.0000001 < divisor < 0.0000001:
        return 0
    else:
        return (float(max(height1, height2))/divisor - 1.0)

def figure_image_alignment (left_margin, right_margin):
    margin_ratio = float(max(1,left_margin))/float(max(1,right_margin))
    if margin_ratio > 2:
        return RIGHT_ALIGN
    elif margin_ratio < 0.5:
        return LEFT_ALIGN
    else:
        return CENTER_ALIGN

def is_fancy (para, line):
    if len(para.lines) < 1:
        return false
    first = para.lines[0]
    last = para.lines[-1]
    if (first.is_italic() and last.is_italic() and not line.is_italic()):
        return "italic"
    elif (first.is_bold() and last.is_bold() and not line.is_bold()):
        return "bold"
    elif (para.all_caps() and re.search('[a-z]', line.text())):
        return "caps"
    elif ((len(para.lines) > 1) and (figure_lineheight_difference(first, last) < 0.1) and (figure_lineheight_difference(last, line) > 0.3)):
        return "lineheight"
    else:
        return None

def is_fancy_line(line, para):
    newpara = Paragraph('ju')
    newpara.add(line)
    return is_fancy(newpara, para.lines[-1])

def _simple_root_sorter (roots):
    roots.sort(lambda x, y: (x.top() < y.top()) or (x.left() < y.left()))
    return roots

def figure_paragraphs(words, debug=None, linesorter=None, parasorter=None, respect_newlines=True):

    last_word = None
    current_word = None
    lines = []
    current_line = None
    if debug is None:
        debug = ()

    note(4, "figure_paragraphs:  debug is %s", debug)

    for box in words:

        # first, group into lines

        if 'boxdebug' in debug:
            text = box.text().encode("US-ASCII", "replace")
            note("new box:    <box \"%s\" @%.1f,%.1f width=%.1f height=%.1f baseline=%.1f %s%s%s%s%s>" %
                             (text[:min(10,len(text))],
                              box.left(), box.top(), box.width(), box.height(), box.baseline(),
                              ((not last_word) or (not box.y_overlaps(last_word))) and "N" or " ",
                              (box.ends_line() and "L") or (box.ends_word() and "W") or " ",
                              (box.has_hyphen() and "-") or " ",
                              (box.is_italic() and "I") or "n", (box.is_bold() and "B") or "n"))

        if current_word and ((not (box.y_overlaps(current_word))) or
                             (box.left() < current_word.right()) or
                             (box.left() - current_word.right() > (2 * current_word.avg_char_width()))):
            if current_line and (current_word not in current_line.words):
                current_line.add(current_word)
            current_word = None

        if current_word:
            # already working on a word
            current_word.append(box)
        else:
            # start a word
            current_word = PartBox(box)

        if not ((respect_newlines and box.ends_line()) or
                box.ends_word() or
                box.has_hyphen() or
                (current_line and (box.left() < current_line.right))
                ):
            # not at end of a word
            continue

        # OK, we have a new word, see if we need to start a new line
        newline = False

        if last_word and last_word.has_hyphen():
            newline = "hy"

        if isinstance(current_word, ImageBox):
            # image boxes always start a new line -- why?
            newline = "im"

        if (last_word and isinstance(last_word, ImageBox)):
            # first box after an image box starts a new line -- why?
            newline = "pi"

        if ((not last_word) or (not current_word.y_overlaps(last_word))):
            newline = "nw"

        elif (not respect_newlines) and last_word and ((current_word.top() - last_word.top()) >= (0.8 * current_word.height())):
            newline = "vs"

        #elif current_line and (current_word.left() < current_line.right):
        #    newline = "rv"

        elif (last_word and (((current_word.left() - last_word.right()) > 72) or
                             ((last_word.left() - current_word.right()) > 72) or
                             (current_line and (len(current_line.words) == 1) and
                              ((current_word.left() - last_word.right()) > (4 * current_line.avg_char_width()))) or
                             (current_line and (len(current_line.words) > 1) and (
                                 ((current_word.left() - last_word.right()) > (3 * current_line.avg_interword_gap())) or
                                 ((current_word.left() - last_word.right()) > (2 * current_line.avg_char_width())) or
                                 ((current_word.left() - last_word.right()) > (4 * current_line.avg_adjusted_interword_gap()))))
                             )):
            newline = "hs"

        elif (current_line and (sum(len(w.text()) for w in current_line.words) > 5) and
              ((current_line.avg_line_height() > (1.8 * current_word.height())) or
               ((current_line.avg_line_height() * 1.8) < current_word.height())) and
              len(current_line.text()) > 1):
            #abrupt change in font size (note require more than 1 prev character to accommodate ornate initial letter)
            newline = "fs"

        if 'boxdebug' in debug:
            text = current_word.text().encode("US-ASCII", "replace")
            note("          %s <box \"%s\" @%.1f,%.1f width=%.1f height=%.1f baseline=%.1f %s%s%s%s%s>" %
                             ((newline or "  "), text[:min(10,len(text))],
                              current_word.left(), current_word.top(), current_word.width(), current_word.height(), current_word.baseline(),
                              ((not last_word) or (not current_word.y_overlaps(last_word))) and "N" or " ",
                              (current_word.ends_line() and "L") or (current_word.ends_word() and "W") or " ",
                              (current_word.has_hyphen() and "-") or " ",
                              (current_word.is_italic() and "I") or "n", (current_word.is_bold() and "B") or "n"))

        if newline:
            if current_line:
                if 'linedebug' in debug:
                    note("line '%s', text '%s', %d, %.1fx%.1f@%.1f,%.1f, bl %.1f, cw %.3f, iw gap %.3f, avg adj iw gap %.3f",
                         newline,
                         current_line.text(), len(current_line.words),
                         current_line.width, current_line.height, current_line.left, current_line.top,
                         current_line.baseline(),
                         current_line.avg_char_width(), current_line.avg_interword_gap(), 
                         current_line.avg_adjusted_interword_gap())
                if len(current_line.words) > 0:
                    lines.append(current_line)
                else:
                    note("empty line found in linebreaking:  %sx%s@%s,%s", current_line.width, current_line.height, current_line.left, current_line.top)
            current_line = Line()

        if current_word and current_word not in current_line.words:
            current_line.add(current_word)
        last_word = current_word
        current_word = None

    if current_line and len(current_line.words) > 0:
        lines.append(current_line)

    note(4, "%d lines...", len(lines))

    if lines and linesorter:
        note(3, "trying to sort lines with %s...", linesorter)
        try:
            v = linesorter(lines)
        except SortError, x:
            note("SortError attempting to sort lines with %s", linesorter)
        except:
            note("Can't sort lines with %s:\n%s\n", linesorter, ''.join(traceback.format_exception(*sys.exc_info())))
        else:
            lines = v

    # now break into paragraphs

    # first, figure average space between lines, adjusted for line size
    lastline = None
    _linespacing_accum = 0
    _linespacing_count = 0
    for line in lines:
        if lastline and (lastline.bottom < line.top) and ((line.top - lastline.bottom) < lastline.height):
            _linespacing_accum += (line.top - lastline.bottom) * 2 / (line.height + lastline.height)
            _linespacing_count += 1
        lastline = line
    _avg_line_spacing = ((_linespacing_count > 0) and (_linespacing_accum/_linespacing_count)) or 0
    note(4, "_avg_line_spacing is %s", _avg_line_spacing)

    paragraphs = []

    current = Paragraph('bp')

    # first word of a new page
    if "showparabreaks" in debug:
        note("newpara: bp\n")

    lastline = None
    lastpara = None
    column_lines = 0

    for line in lines:

        newparagraph = None

        if isinstance(line.words[0], ImageBox):
            newparagraph = 'im'

        if len(current.lines) > 2:
            # update linespacing now that we've seen two inter-line gaps
            linespacing = current.avg_line_spacing()
        else:
            linespacing = _avg_line_spacing * line.height       # global average

        if len(current.lines) > 0:
            cocenter = math.fabs(current.avg_center_position() - (line.right + line.left)/2.0)
            indent = line.left - current.lastleft
        else:
            cocenter = 0
            indent = 0

        acw = current.avg_char_width()

        if "parabreaking" in debug:
            text = line.text().encode("US-ASCII", "replace")
            note("newline:  <line \"%s\" @%.1f,%.1f width=%.1f height=%.1f %s%s>, (%s, %.1f, %.1f, ls %.1f, %.1f, %.1f, %s, %s, %.2f, %s)\n" %
                             (text[:min(20,len(text))],
                              line.left, line.top, line.width, line.height,
                              (line.is_italic() and "I") or "n", (line.is_bold() and "B") or "n",
                              current.breaktype, indent, cocenter, linespacing,
                              current.left(), current.lastleft, len(current.lines), column_lines,
                              (lastline and figure_lineheight_difference(lastline, line)) or 0.0,
                              is_fancy(current, line)))


        if len(current.lines) == 0:
            # just punt and move on to next line
            pass

        elif (lastline and (line.left > lastline.right) and (line.bottom < lastline.top) and
              (line.words[0].percentage_overlap(current) < 0.001)):
            if "showparabreaks" in debug:
                note("newpara: co -- previous right boundary was %s, current left boundary is %s", lastline.right, line.left)
            newparagraph = 'co'            

        elif ((indent > (1.5*acw)) and
              (column_lines < 2 or len(current.lines) > 1) and
              (current.breaktype not in ('rf', 'bu',)) and
              (math.fabs(current.right() - line.right) < acw) and
              (line.words[0].percentage_overlap(current) < 0.001)):
            # we want to see if this line is indented compared to the last line,
            # but only if the last line was the second or more of a paragraph,
            # and only if this line doesn't overlap the current para
            if "showparabreaks" in debug:
                note("newpara: in -- indent is %s\n" % indent)
            newparagraph = 'in'

        elif (indent > (2*acw)) and is_fancy(current, line):
            # first paragraph after a section header
            if "showparabreaks" in debug:
                note("newpara: if -- section header, indent is %s, is_fancy is %s\n" % (indent, is_fancy(current, line)))
            newparagraph = 'if'

        elif (((current.breaktype == 'co') or (cocenter > current.avg_char_width()) or
               is_fancy_line(line, current)) and
              ((current.lastleft - line.left) > 5) and ((current.left() - line.left) > 5) and
              ((len(current.lines) > 1) or is_fancy_line(line, current))):
            # outdent
            if "showparabreaks" in debug:
                note("newpara: ou -- lastleft is %.1f, newleft is %.1f, current.lines = %d, is_fancy_line = %s\n" % (
                    current.lastleft, line.left, len(current.lines), is_fancy_line(line, current)))
            newparagraph = 'ou'

        elif ((len(current.lines) > 0) and
              REFERENCE_INDICATOR.match(line.text()) and
              (REFERENCE_INDICATOR.match(current.lines[0].words[0].text()) or
               (current.lines[-1].words[-1].text().lower().startswith("reference") and is_fancy(current, line))) and
              (line.left - current.left()) < 1):
            if "showparabreaks" in debug:
                note("newpara: rf -- reference indicator -- previous line was \"%s\", current is \"%s\"\n" % (current.lines[0].words[0].text().encode("US-ASCII", "replace"), line.text().encode("US-ASCII", "replace")))
            newparagraph = 'rf'

        elif ((len(current.lines) > 0) and
              BULLET_INDICATOR.match(line.text()) and
              (line.left - current.left()) < 1):
            if "showparabreaks" in debug:
                note("newpara: bu -- bulleted item -- previous line was \"%s\", current is \"%s\"\n" % (current.lines[0].words[0].text().encode("US-ASCII", "replace"), line.text().encode("US-ASCII", "replace")))
            newparagraph = 'bu'

        elif (lastline and current and (len(current.lines) > 1) and
               (line.top > lastline.bottom) and
               ((line.top - lastline.bottom) > (current.avg_line_spacing() * 1.5))):
            # broad space separating this line from last line
            if "showparabreaks" in debug:
                note("newpara: ls -- current line is \"%s\", len(current.lines) is %s, line.top is %d, lastline.bottom is %d, current.avg_line_spacing is %d\n" % (line.text().encode("US-ASCII", "replace"), len(current.lines), int(line.top), int(lastline.bottom), current.avg_line_spacing()))
            newparagraph = 'ls'

        elif ((figure_lineheight_difference(line, lastline) > 0.3) and
              ((len(line.words) > 1) or ((len(line.words) == 1) and (len(line.words[0].text()) > 1)))):
            # radically different line heights -- may have changed fonts?
            if "showparabreaks" in debug:
                note("newpara: lh -- lineheight difference is %s\n" % figure_lineheight_difference(line, lastline))
            newparagraph = 'lh'

        elif ((current.breaktype != 'in') and (len(current.lines) >= 1) and (len(current.lines) <= 3) and
              # check for single bullet or other such leading char
              ((len(current.lines[0].words) > 1) or (len(current.lines[0].words[0].text()) > 1)) and
              is_fancy(current, line)):
            # previous line was a section header
            if "showparabreaks" in debug:
                note("newpara: sh -- fancy line to non-fancy line (%s)", is_fancy(current, line))
            newparagraph = 'sh'

        elif ((len(current.lines) > 1) and ((line.left - lastline.right) > (5 * acw)) and
              (line.words[0].percentage_overlap(current) < 0.001)):
            if "showparabreaks" in debug:
                note("newpara: co -- previous right boundary was %s, current left boundary is %s", lastline.right, line.left)
            newparagraph = 'co'

        elif (lastline and (lastline.left > line.right)):
            if "showparabreaks" in debug:
                note("newpara: sb -- section break -- previous right boundary was %s, current left boundary is %s", lastline.right, line.left)
            newparagraph = 'sb'

        elif ((len(current.lines) > 1) and lastline and (lastline.top > line.bottom) and
              (line.words[0].percentage_overlap(current) < 0.001)):
            # line is above other lines in paragraph
            if "showparabreaks" in debug:
                note("newpara: vb -- vertical break, line is above previous line")
            newparagraph = 'vb'

        elif (lastline and (line.top - lastline.bottom) > max(lastline.height, line.height)):
            # broad space separating this line from last line
            if "showparabreaks" in debug:
                note("newpara: lb -- current line is \"%s\", line.top is %d, lastline.bottom is %d, max height is %s\n" % (line.text().encode("US-ASCII", "replace"), int(line.top), int(lastline.bottom), max(lastline.height, line.height)))
            newparagraph = 'lb'

        elif (lastline and
              (lastline.words[0].text().lower() == "by") and
              (not [x for x in lastline.words[1:] if unitype(x.text()[0]) != 'Lu']) and
              ((line.width - lastline.width) > (7*acw))):
            # last line was a byline, this line starts the story -- special case for NY Times
            if "showparabreaks" in debug:
                note("newpara: by -- last line was a byline (special case for NY Times web pages)")
            newparagraph = 'by'

        if newparagraph:
            if len(current.lines) > 0:
                paragraphs.append(current)
                if "parabreaking" in debug:
                    note("linespacing for prev para was %.3f, _avg_line_spacing is %.3f",
                         current.avg_line_spacing(), _avg_line_spacing)
            lastpara = current
            current = Paragraph(newparagraph)

        column_lines = column_lines + 1

        current.add(line)
        lastline = line

    if current and len(current.lines) > 0:
        paragraphs.append(current)
    return paragraphs


def samepara (lastbox, paragraph, joinpages=True):

    # if the paragraph break is a column change ("co"), or new page ("bp"),
    # the next paragraph may be part of the preceding one.  Let's see if we
    # can find those breaks and glue them back together.

    try:
        v = (lastbox and isinstance(lastbox, Paragraph) and isinstance(paragraph, Paragraph) and
             (((paragraph.breaktype == 'co') and
               # non-indented first line of first para after the column break
               (((unitype(paragraph.first_word().text()[0])[0] == 'L') and (len(paragraph.lines) > 1) and
                 (math.fabs(paragraph.indent - paragraph.lastleft) < paragraph.avg_char_width())) or
                # non-indented non-capitalized first line of first para after the column break
                ((unitype(paragraph.first_word().text()[0]) == 'Ll') and
                 (math.fabs(paragraph.indent - paragraph.lastleft) < paragraph.avg_char_width())) or
                # continuation of a references section
                ((lastbox.breaktype == 'rf') and
                 (unitype(paragraph.first_word().text()[0]) in ('Ll', 'Lu', 'Nd')) and
                 (not REFERENCE_INDICATOR.match(paragraph.first_word().text())))
                )) or
              (((paragraph.breaktype == 'co') or (paragraph.breaktype == 'bp')) and
               # previous multiline paragraph ended with non-sentence ending punctuation
               (len(lastbox.lines) > 1) and (lastbox.last_word().text()[-1] not in u".!?*)}]'\"")
               ) or
              (joinpages and (paragraph.breaktype == 'bp') and
               # continuation of a references section onto the next page
               (((lastbox.breaktype == 'rf') and
                 (unitype(paragraph.first_word().text()[0]) in ('Ll', 'Lu', 'Nd')) and
                 (not REFERENCE_INDICATOR.match(paragraph.first_word().text()))) or
                # non-indented non-capitalized first para on the next page
                ((unitype(paragraph.first_word().text()[0]) == 'Ll') and
                 (math.fabs(paragraph.indent - paragraph.lastleft) < paragraph.avg_char_width())) or
                # last paragraph on previous page ends with a hyphen
                ((unitype(paragraph.first_word().text()[0]) == 'Ll') and
                 (lastbox.last_word().text()[-1] == "-"))))))
        return v
    except:
        note(0, "Can't determine whether para %s and para %s are the same paragraph",
             repr(lastbox.text()), repr(paragraph.text()))


# should this be in plibUtil?
def read_paragraphs_file (filename):

    class PBox:
        def __init__(self, pageno, first_byte, first_byte_not,
                     x, y, width, height, nchars, breaktype, hash):
            self.pageno = int(pageno)
            self.first_byte = int(first_byte)
            self.first_byte_not = int(first_byte_not)
            self.x = int(x)
            self.y = int(y)
            self.width = int(width)
            self.height = int(height)
            self.nchars = int(nchars)
            self.breaktype = breaktype
            self.hash = hash

        def __str__(self):
            return "<PBox %s %s-%s, %s chars>" % (self.pageno, self.first_byte, self.first_byte_not, self.nchars)

        def __cmp__(self, other):
            return cmp(self.first_byte, other.first_byte)

    if os.path.exists(filename):
        return [PBox(*line.strip().split()) for line in open(filename, 'r')]
    else:
        return []


def read_paragraphs(folder):

    class ParaBox (Box):
        def __init__(self, x, y, width, height, breaktype, hash, text, page, span):
            self.x0 = x
            self.y0 = y
            self.x1 = x + width
            self.y1 = y + height
            self.breaktype = breaktype
            self.hash = hash
            self.text = text
            self.page = page
            self.span = span

    ppath = os.path.join(folder, "paragraphs.txt")
    cpath = os.path.join(folder, "contents.txt")
    if (not os.path.exists(ppath)) or (not os.path.exists(cpath)):
        return None
    plist = read_paragraphs_file(ppath)
    tfile, charset, language = read_file_handling_charset_returning_bytes(cpath)
    try:
        start = tfile.tell()
        paras = []
        for i in range(len(plist)):
            p = plist[i]
            tfile.seek(p.first_byte + start)
            if ((i + 1) < len(plist)):
                span = (p.first_byte, plist[i+1].first_byte - p.first_byte)
                ptext = tfile.read(plist[i+1].first_byte - p.first_byte)
            else:
                ptext = tfile.read()
                span = (p.first_byte, p.first_byte + len(ptext))
            ptext = unicode(ptext, charset, "strict").strip()
            if ptext:
                paras.append(ParaBox(p.x, p.y, p.width, p.height, p.breaktype, p.hash, ptext, p.pageno, span))
        return paras
    finally:
        tfile.close()


def gen_fingerprint (paratext):

    text = paratext.lower()
    text = re.sub('\W+', ' ', re.sub(",'-", "", text))
    import hashlib
    s = hashlib.sha1()
    s.update(text)
    return s.hexdigest()    

def process_document (folder):

    def jointext (t1, t2):
        if t1[-1] == '-':
            return t1[-1] + t2
        else:
            return t1 + ' ' + t2

    wbboxes_path = os.path.join(folder, "wordbboxes")
    paragraphs_path = os.path.join(folder, "paragraphs.txt")
    metadata_path = os.path.join(folder, "metadata.txt")
    v = []
    if os.path.exists(wbboxes_path):
        fp = open(paragraphs_path, 'w')
        lastpara = None
        for page_index, bboxes in wordboxes_page_iterator(folder):
            if bboxes:
                paragraphs = figure_paragraphs(bboxes)
                for para in paragraphs:
                    same = samepara(lastpara, para)
                    if same:
                        fingerprint = gen_fingerprint(Paragraph.figure_text(
                            [x for x in lastpara.words()] + [x for x in para.words()]))
                    else:
                        fingerprint = gen_fingerprint(para.text())
                    l = len(para.text())
                    lw = para.last_word()
                    lwl = len(lw.text())
                    if lw.ends_line() and lw.has_hyphen():
                        # contents.txt removes these hyphens
                        lwl -= 1
                    fp.write('%5d %6d %6d %5d %5d %5d %5d %5d %s %s\n'
                             % (page_index, para.first_word().offset,
                                lw.offset + lwl,
                                para.left(), para.top(), para.width(), para.height(), l,
                                para.breaktype, fingerprint))
                    if l > 4:
                        if not same:
                            v.append(fingerprint)
                        else:
                            v[-1] = fingerprint
                        lastpara = para
        fp.close()
    if v:
        update_metadata(metadata_path, { "paragraph-ids" : ", ".join(v) })


def reindex_paragraphs (doc):

    folder = doc.folder()
    lock_folder(folder)
    try:
        # first, refind the paragraphs and hash them
        process_document(folder)
        # next, re-index the document
        index_folder(folder, doc.repo.index_path())
    finally:
        unlock_folder(folder)


class ParagraphRipper (Ripper):

    def rip(self, folder, id):

        process_document(folder)


def _by_repo_add_date(h1, h2):
    return cmp(h1[0].add_time(), h2[0].add_time())

def find_paragraph_related (doc, cutoff=0.0):

    ids = doc.get_metadata("paragraph-ids")

    if ids:
        query = " OR ".join([("paragraph-ids:" + id) for id in ids.split(",")])
    else:
        query = "sha-hash:%s" % doc.get_metadata("sha-hash")
    coll = QueryCollection(doc.repo, None, query, cutoff=cutoff)
    return coll

def prelated (repo, response, params):

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id %s specified." % doc_id)
        return

    cutoff = float(params.get("cutoff") or 0.05)
    rettype = params.get("rettype")

    doc = repo.get_document(doc_id)
    coll = find_paragraph_related(doc, cutoff)
    scored = coll.scores()
    scored.sort()
    scored.reverse()

    if response.xml_request or (rettype == "xml"):
        retval = getDOMImplementation().createDocument(None, "result", None)
        e = retval.createElement('query')
        e.setAttribute('doc_id', doc_id)
        e.setAttribute('cutoff', str(cutoff))
        e.setAttribute('query', coll.query)
        retval.documentElement.appendChild(e)
        for docid, score in scored:
            doc = coll[docid]
            e = retval.createElement('hit')
            e.setAttribute('doc_id', docid)
            e.setAttribute('score', str(score))
            e.setAttribute('title', doc.get_metadata("title") or "")
            retval.documentElement.appendChild(e)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()

    elif rettype == "plain":
        fp = response.open("text/plain;charset=utf-8")
        for docid, score in scored:
            doc = coll[docid]
            fp.write("%.3f %s %s\n" % (score, docid, (doc.get_metadata("title") or "").encode("UTF-8", "replace")))
        fp.close()

    else:
        fp = response.open()
        title = u"Versions of %s" % repr(doc.get_metadata("title") or doc.id)
        fp.write("<head><title>%s</title>\n" % htmlescape(title))
        fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
        fp.write('<link REL="SHORTCUT ICON" HREF="/favicon.ico">\n')
        fp.write('<link REL="ICON" type="image/ico" HREF="/favicon.ico">\n')
        issue_javascript_head_boilerplate(fp)
        issue_title_styles(fp);
        fp.write('</head><body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
        issue_menu_definition(fp)
        output_tools_block (repo, fp, htmlescape(title), "Abstract MRU", coll, title)

        fp.write('<p><b>The document itself:</b><br>\n')
        show_abstract(repo, doc, fp, True, query=coll.query, showpagesearch=False, showid=True)
        orig_hash = doc.sha_hash()

        fp.write('<p><hr><b>Other versions of that document:</b><br>')
        for docid, score in scored:
            related = coll[docid]
            if related.id == doc.id:
                continue
            related = repo.get_document(docid)
            related_hash = related.sha_hash()
            if related_hash == orig_hash:
                fp.write('<table width=100%% bgcolor="%s"><tr><td>&nbsp;</td><td>' % STANDARD_TOOLS_COLOR)
            show_abstract (repo, related, fp, True, score=score, showpagesearch=False, showid=True)
            if related_hash == orig_hash:
                fp.write('</td></tr></table>')

        output_footer(repo, fp, coll, response.logged_in)
        fp.write('</body>\n')
        fp.close()

def get_urls (doc):

    def get_boxes (doc, start, end, url):
        rboxes = []
        page_index = -1
        boxes = wordboxes_for_span(doc.folder(), start, end)
        currentbox = None
        text = ''
        for b in boxes:
            if page_index < 0:
                page_index = b.page
            if (not currentbox):
                currentbox = PartBox(b)
            elif currentbox.percent_y_overlaps(b) > .5:
                currentbox.append(b)
            else:
                rboxes.append(URLBox(currentbox.left(), currentbox.top(), currentbox.width(), currentbox.height(), url, page_index))
                currentbox = PartBox(b)
        if currentbox:
            rboxes.append(URLBox(currentbox.left(), currentbox.top(), currentbox.width(), currentbox.height(), url, page_index))
        return rboxes

    def get_text (doc):
        f = open(os.path.join(doc.folder(), "contents.txt"), 'rb')
        firstline = f.readline()
        m = CHARSET_PATTERN.match(firstline)
        if m:
            charset = m.group(1)
            l = f.readline()
            m = LANGUAGE_PATTERN.match(l)
            if m:
                language = m.group(1)
            else:
                language = "en-US"
        else:
            charset = "latin_1"
            language = "en-US"
            f.seek(0)
        data = f.read()
        f.close()
        return data

    t = get_text(doc)
    urls = []
    for m in URLPATTERN.finditer(t):
        for box in get_boxes(doc, m.start('url'), m.end('url'), m.group('url')):
            urls.append(box)
    for m in EMAILPATTERN.finditer(t):
        for box in get_boxes(doc, m.start('email'), m.end('email'), 'mailto:' + m.group(0)):
            urls.append(box)
    for m in GEMAILPATTERN.finditer(t):
        start, end = m.start('group'), m.end('group')
        domain = m.group('domain')
        mailboxes = []
        current = []
        for i in range(start, end):
            if t[i] in (',' + string.whitespace):
                if current:
                    mailboxes.append(current)
                current = []
            elif t[i] in string.printable:
                current.append(i)
        if current:
            mailboxes.append(current)
        for mailbox in mailboxes:
            start1, end1 = min(mailbox), max(mailbox)+1
            url = 'mailto:%s@%s' % (t[start1:end1], domain)
            for box in get_boxes(doc, start1, end1, url):
                urls.append(box)
    return urls


IMAGE_TYPES = re.compile('(image/.*)|(application/vnd.ms-powerpoint)')

def HTML (repo, response, params):

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id %s specified." % doc_id)
        return

    debug = params.get("debug")
    if debug:
        if isinstance(debug, str):
            debug = (debug,)

    htmltype = params.get("htmltype")

    doc = repo.get_document(doc_id)

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
                response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Couldn't create HTML version of document, for some reason.")
                return
        if not os.path.exists(filepath):
            response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Couldn't create HTML version of document, for some reason.")
            return
    response.return_file("text/html", filepath)
    return


def _create_textual_HTML_version (doc, debug=None):

    def read_illustrations(doc, page_index):

        from PIL import Image

        images = doc.get_metadata("illustrations-bounding-boxes")
        if not images:
            return []
        dpi = int(doc.get_metadata("dpi") or doc.get_metadata("images-dpi") or 300)

        illustrations = []

        currentpage = None
        im = None
        for image in images.split(","):
            pageno, type, left, top, width, height = image.split(":")
            pageno = int(pageno)
            if pageno != page_index:
                continue
            left = int(left)
            top = int(top)
            width = int(width)
            height = int(height)
            if ((width * height) < 500) and (type == "misc"):
                note("skipping %s", image)
                # too small
                continue
            filepath = os.path.join(doc.folder(), "page-images", "page%05d.png" % (pageno + 1))
            newwidth, newheight = (width * 72) / dpi, (height * 72) / dpi
            if ((newwidth < 1) or (newheight < 1)):
                # too small
                continue
            if im is None:
                if not os.path.exists(filepath):
                    note('No image file %s for page %s' % (filepath, (pageno + 1)))
                else:
                    im = Image.open(filepath)
                if im.mode in ("1", "P", "L"):
                    im = im.convert("RGB")
            img = im.crop((left, top, left + width + 1, top + height + 1))
            # rescale to points (72 dpi)
            width, height = (img.size[0] * 72) / dpi, (img.size[1] * 72) / dpi
            if dpi != 72:
                img = img.resize((newwidth, newheight), Image.ANTIALIAS)
            # convert to data: URL
            fpi = StringIO.StringIO()
            img.save(fpi, "PNG")
            bits = fpi.getvalue()
            fpi.close()
            illustrations.append(ImageBox((left * 72)/ dpi, (top * 72)/dpi, width, height, type, bits))
        if im is not None:
            del im
        return illustrations

    def filter_illustrations (illustrations, page_index):

        def suitable (i):
            # width x height > 30 -- purely arbitrary
            return ((i[2] * i[3]) > 30) or (i[4] != "misc")

        return [ImageBox(i[0], i[1], i[2], i[3], i[4], i[5]) for i in illustrations if ((i[6] == page_index) and suitable(i))]

    def cosort (paras, ills):
        # for each illustration, find the right place in the paragraph structure,
        # and insert it in the list

        for illustration in ills:
            for paragraph in paras:
                overlap = paragraph.percentage_overlap(illustration)
                if overlap > 0.01:
                    note(5, "illustration %s %.2f overlaps paragraph %s", illustration, overlap, paragraph)
                if paragraph.percentage_overlap(illustration) > 0.5:
                    note(4, "illustration %s occludes paragraph %s", illustration, paragraph)
                    paragraph.occluded = True
                if illustration.x_overlaps(paragraph):
                    if (not illustration.inserted) and (illustration.bottom() < paragraph.top()):
                        paras.insert(paras.index(paragraph), illustration)
                        illustration.inserted = True
            if illustration not in paras:
                paras.append(illustration)

        return paras

    def __rerip (doc):

        # do this here to avoid circular imports
        from uplib.createPageBboxes import BboxesRipper

        rippers = doc.repo.rippers()
        for r in rippers:
            if isinstance(r, BboxesRipper):
                r.rip(doc.folder(), doc.id)
                doc.recache()
                return

    folderdir = doc.folder()

    versions_dir = os.path.join(folderdir, "versions")
    if not os.path.exists(versions_dir):
        os.mkdir(versions_dir)
        os.chmod(versions_dir, 0700)

    wordbboxes_path = os.path.join(folderdir, "wordbboxes")
    stats = doc.get_metadata("wordbbox-stats-pagewise")
    if (not os.path.exists(wordbboxes_path)) or (not stats):
        note("re-ripping to get wordboxes or page stats computed...")
        __rerip(doc)

    if (not os.path.exists(wordbboxes_path)):
        raise NoWordboxesError("No wordbboxes file for doc %s" % doc.id)

    doc_links = doc.links().values()

    urls = get_urls(doc)

    doc_illustrations = read_illustrations_metadata(folderdir, include_images=True)

    fp = open(os.path.join(versions_dir, "document.html"), "wb")

    for page_index, bboxes in wordboxes_page_iterator(folderdir):

        paragraphs = figure_paragraphs(bboxes)

        if page_index == 0:
            title = doc.get_metadata("title") or unicode(doc)
            fp.write("<html><head>")
            fp.write('<META http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n')
            fp.write('<META name="viewport" content="initial-scale = 1.0" />\n')
            if title:
                fp.write("<title>%s</title>" % htmlescape(title))
            fp.write("</head><body>\n")

        else:
            fp.write("<hr />\n")

        # see if there are any illustrations for this page
        illustrations = filter_illustrations(doc_illustrations, page_index)

        # sort illustrations into list of paragraphs
        paragraphs = cosort(paragraphs, illustrations)

        # find links for this page
        links = [URLBox(*(x.from_rect + (x.to_uri, x.from_page))) for x in doc_links if ((x.from_page == page_index) and x.to_uri and x.from_rect)]
        links += [x for x in urls if (x.page == page_index)]

        lastbox = None

        for paragraph in paragraphs:

            current_link = None

            if isinstance(paragraph, ImageBox):
                if paragraph.imagetype != "misc":
                    # check for a link around this image
                    for link in links:
                        if link.percentage_overlap(paragraph) > 0.7:
                            current_link = link
                            fp.write('<a href="%s">' % htmlescape(link.url))
                            break
                    if isinstance(lastbox, ImageBox) and (lastbox.percent_y_overlaps(paragraph) > .5):
                        fp.write('<img src="data:image/png;base64,%s" alt="image" />\n' % base64.encodestring(paragraph.bits).strip())
                    else:
                        if lastbox:
                            fp.write('</p>\n')
                        fp.write('<p><img src="data:image/png;base64,%s" alt="image" />\n' % base64.encodestring(paragraph.bits).strip())
                    lastbox = paragraph
                    if current_link:
                        fp.write('</a>')
                        current_link = None
                continue

            elif isinstance(paragraph, Paragraph) and paragraph.occluded:
                # overlaid by an image
                continue

            # if the paragraph break is a column change ("co"), the next paragraph
            # may be part of the preceding one.  Let's see if we can find those
            # breaks and glue them back together.

            if (lastbox and isinstance(lastbox, Paragraph) and isinstance(paragraph, Paragraph) and
                (paragraph.breaktype == 'co') and
                (((unitype(paragraph.first_word().text()[0]) in ('Ll', 'Lu')) and (len(paragraph.lines) > 1) and
                  (math.fabs(paragraph.indent - paragraph.lastleft) < paragraph.avg_char_width())) or
                 ((unitype(paragraph.first_word().text()[0]) == 'Ll') and
                  (math.fabs(paragraph.indent - paragraph.lastleft) < paragraph.avg_char_width())) or
                 ((lastbox.breaktype == 'rf') and
                  (unitype(paragraph.first_word().text()[0]) in ('Ll', 'Lu', 'Nd')) and
                  (not REFERENCE_INDICATOR.match(paragraph.first_word().text())))
                 )):
                # OK, it's the same paragraph
                note(4, "column break removed => %s / %s", lastbox.text(), paragraph.text())
                pass
            else:
                if lastbox:
                    fp.write('</p>\n')
                fp.write('<p style="font-size: %spt">' % paragraph.avg_font_size())

            for box in paragraph.words():

                if current_link and box.percentage_overlap(current_link) < 0.01:
                    fp.write('</a>')
                    current_link = None
                    
                if current_link is None:
                    # check to see if box is in a link
                    for link in links:
                        if box.percentage_overlap(link) > 0.5:
                            current_link = link
                            fp.write('<a href="%s">' % htmlescape(link.url))
                            break

                if isinstance(box, Space):
                    fp.write(' ')
                    continue

                # check box (in PIL units)
                if ((box.right() < box.left()) or (box.top() > box.bottom())):
                    note("bad box:  %s\n" % box)
                    fp.write('\n<!-- bad box: %s -->\n' % box)
                    continue

                # addedbaseline = max(round(paragraph.baseline - box.baseline()), 0)
                addedbaseline = 0
                
                if box.is_fixedwidth():
                    fp.write('<tt>')
                if box.is_bold():
                    fp.write('<b>')
                if box.is_italic():
                    fp.write('<i>')

                t = box.text().encode("UTF-8", "replace")
                if box.has_hyphen():
                    t = t[:-1]
                fp.write(t)

                if box.is_italic():
                    fp.write('</i>')
                if box.is_bold():
                    fp.write('</b>')
                if box.is_fixedwidth():
                    fp.write('</tt>')

                if debug and ("showwords" in debug):
                    fp.write('`')
                if box.ends_word() and not box.has_hyphen():
                    fp.write(' ')

            if current_link:
                fp.write('</a>')
                current_link = None

            if debug and ("parabreaking" in debug):
                fp.write(' <sub><font style="color: red">{%s}</font></sub>' % paragraph.breaktype)

            lastbox = paragraph

        if lastbox:
            fp.write('</p>\n')

    fp.write('</body></html>\n')
    fp.close()

def _create_image_HTML_version (doc, debug=None):

    folderdir = doc.folder()

    versions_dir = os.path.join(folderdir, "versions")
    if not os.path.exists(versions_dir):
        os.mkdir(versions_dir)
        os.chmod(versions_dir, 0700)

    doc_links = doc.links().values()

    urls = get_urls(doc)

    translation, scaling = doc.thumbnail_translation_and_scaling()
    
    def scale_rect (left, top, width, height):
        # convert from points to pixels on the big page thumbnail
        # conversion from float to int via "int()" truncates, so define it as "trunc"
        trunc = int
        left = trunc((left + translation[0]) * scaling[0] + 0.5)
        top = trunc((top + translation[1]) * scaling[1] + 0.5)
        width = trunc(width * scaling[0] + 0.5)
        height = trunc(height * scaling[1] + 0.5)
        return left, top, width, height

    fp = open(os.path.join(versions_dir, "document.html"), "wb")
    pagecount = int(doc.get_metadata('page-count') or doc.get_metadata('pagecount'))

    for page_index in range(pagecount):

        if page_index == 0:
            title = doc.get_metadata("title") or unicode(doc)
            fp.write("<html><head>")
            fp.write('<META http-equiv="Content-Type" content="text/html; charset=UTF-8">')
            if title:
                fp.write("<title>%s</title>" % htmlescape(title))
            fp.write("</head><body>\n")

        else:
            fp.write("<hr>\n")

        # find links for this page
        links = [URLBox(*(x.from_rect + (x.to_uri, x.from_page))) for x in doc_links if ((x.from_page == page_index) and x.to_uri and x.from_rect)]
        links += [x for x in urls if (x.page == page_index)]

        if links:
            # generate a client-side image map
            fp.write('<map name="%s-page-%s">\n' % (doc.id, page_index))
            for link in links:
                left, top, width, height = scale_rect(link.left(), link.top(), link.width(), link.height())
                fp.write('<area href="%s" alt="%s" shape="rect" coords="%d,%d,%d,%d">\n' %
                         (link.url, htmlescape(link.url),
                          left, top, left+width+1, top+height+1))
            fp.write('</map>\n')

        img = Image.open(doc.large_thumbnail_path(page_index))
        img = img.copy().crop((0, 0, img.size[0] - 25, img.size[1]))
        img.load()
        fpi = StringIO.StringIO()
        img.save(fpi, "PNG")
        bits = fpi.getvalue()
        fpi.close()
        if links:
            fp.write('<p><img src="data:image/png;base64,%s" usemap="#%s-page-%s" /></p>\n' %
                     (base64.encodestring(bits).strip(), doc.id, page_index))
        else:
            fp.write('<p><img src="data:image/png;base64,%s" /></p>\n' % base64.encodestring(bits).strip())

    fp.write('</body></html>\n')
    fp.close()

