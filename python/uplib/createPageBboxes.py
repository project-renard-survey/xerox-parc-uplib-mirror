#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import re, os, sys, time, shutil, tempfile, stat, traceback, cgi, socket, codecs, struct, math, StringIO, zlib
from bisect import bisect

from PIL import Image, ImageOps            # python image library (PIL)

from uplib.plibUtil import false, true, Error, note, set_verbosity, subproc, read_metadata, update_metadata, wordboxes_page_iterator
from uplib.ripper import Ripper
from uplib.paragraphs import read_paragraphs_file

# conversion from float to int via "int()" truncates, so define it as "trunc"
trunc = int

NEWLINE_FLAG = 0x04
WORDENDING_FLAG = 0x02

CHARSETPATTERN = re.compile(r"^Content-Type:\s*text/plain;\s*charset=([^)]*)\n", re.IGNORECASE)

UTF8_ALIASES = ('utf8', 'UTF8', 'UTF_8', 'utf_8', 'UTF-8', 'utf-8')

PAGEBREAK_BBOX_VALUE = 0

#
# The contents.ind file contains 8 columns, each preceded by a vertical bar character.
# Each row of the file gives information about some text fragment in the contents.txt file.
# The columns contain, in order, the following information:
# 1.  A decimal integer giving the byte position in the contents.txt file where this piece of text starts
# 2.  A 1 if this fragment begins a new paragraph, 0 otherwise.
# 3.  A 1 if this fragment begins a new sentence, 0 otherwise.
# 4.  A 1 if this fragment begins a new "clause", 0 otherwise.  (should be ignored)
# 5.  A 1 if this fragment begins a new phrase, 0 otherwise.
# 6.  A text string giving a part-of-speech label.
# 7.  A decimal integer giving the length in bytes of the fragment.
# 8.  An ASCII rendition of the text fragment.
#

class POSTag:

    FRAGMENT_PATTERN = re.compile(r"^\|([0-9]+)\|(0|1)\|(0|1)\|[01]\|(0|1)\|([-A-Za-z0-9]+)\|([0-9]+)\|(.*)$")

    POS_explanations = {
        "Abbr": ("abbreviation that is not a title", "i.e."),
        "Abbr-Meas": ("abbreviation of measure", "oz."),
        "Adj": ("adjective", "big"),
        "Adj-Comp": ("comparative adjective", "bigger"),
        "Adj-Sup": ("superlative adjective", "biggest"),
        "Adv": ("adverb", "quickly"),
        "Adv-Comp": ("comparative adverb", "earlier"),
        "Adv-IntRel": ("wh-adverb", "how, when"),
        "Adv-Sup": ("superlative adverb", "fastest"),
        "Aux": ("auxiliary or modal", "will, could"),
        "Conj-Coord": ("coordinating conjunction", "and"),
        "Conj-Sub": ("subordinating conjunction", "if, that"),
        "Det": ("invariant determiner (singular or plural)", "some, no"),
        "Det-Def": ("definite determiner", "the"),
        "Det-Indef": ("indefinite determiner", "a"),
        "Det-Int": ("interrogative determiner", "what"),
        "Det-IntRel": ("interrogative or relative determiner", "whose"),
        "Det-Rel": ("relative determiner", "whatsoever"),
        "Det-Pl": ("plural determiner", "these, those"),
        "Det-Poss": ("possessive determiner", "her, his, its"),
        "Det-Sg": ("singular determiner", "this, that"),
        "For": ("foreign word", "raison d'etre"),
        "Interj": ("interjection", "oh, hello"),
        "Letter": ("letter", "a, b, c"),
        "Markup-SGML": ("SGML markup", "<TITLE>"),
        "Nn": ("invariant noun", "sheep"),
        "Nn-Pl": ("plural noun", "computers"),
        "Nn-Sg": ("singular noun", "table"),
        "Num": ("number or numeric expression", "40.5"),
        "Num-Money": ("monetary amount", "$12.55"),
        "Num-Percent": ("percentage", "12%"),
        "Num-Roman": ("roman numeral", "XVII, xvii"),
        "Onom": ("onomatopoeia", "meow"),
        "Ord": ("ordinal number", "first, 10th"),
        "Part-Inf": ("infinitive marker", "to"),
        "Part-Neg": ("negative particle", "not"),
        "Part-Poss": ("possessive marker", "'s, '"),
        "Prep": ("preposition", "in, on, to"),
        "Pron": ("pronoun", "he"),
        "Pron-Int": ("wh-pronoun", "who"),
        "Pron-IntRel": ("wh-pronoun", "who"),
        "Pron-Refl": ("reflexive pronoun", "himself"),
        "Pron-Rel": ("relative pronoun", "who, whom, that, which"),
        "Prop": ("name of a person or thing", "Graceland, Aesop"),
        "Prop-Email": ("email address", "lxsupport@inxight.com"),
        "Prop-Init": ("initial", "J."),
        "Prop-URL": ("web browser URL", "http://www.inxight.com"),
        "Punct": ("other punctuation", "- ; /"),
        "Punct-Close": ("closing punctuation", ") ] }"),
        "Punct-Comma": ("comma", ","),
        "Punct-Money": ("currency punctuation", "$"),
        "Punct-Open": ("opening punctuation", "( [ {"),
        "Punct-Percent": ("percent sign", "%"),
        "Punct-Quote": ("quote", "' \" ''"),
        "Punct-Sent": ("sentence-ending punctuation", ". ! ?"),
        "Time": ("time expression", "9:00"),
        "Unknown" : ("unknown part of speech", "??"), 
        "V-Inf-be": ("infinitive of to be", "be"),
        "V-PaPart": ("verb, past participle", "understood"),
        "V-PaPart-be": ("past participle of to be", "been"),
        "V-Past": ("verb, past tense", "ran"),
        "V-Past-Pl-be": ("verb, past tense plural of to be", "were"),
        "V-Past-Sg-be": ("verb, past tense singular of to be", "was"),
        "V-Past-have": ("past tense of have", "had"),
        "V-Pres": ("verb, present tense or infinitive", "walk"),
        "V-Pres-Pl-be": ("verb, present tense plural of to be", "are"),
        "V-Pres-Sg-be": ("verb, present tense singular of to be", "is"),
        "V-Pres-have": ("present tense or infinitive of have", "have"),
        "V-Pres-3-Sg": ("verb, present tense, 3rd person singular", "runs"),
        "V-Pres-3-Sg-have": ("present tense, 3rd person singular of have", "has"),
        # these were added after XLE-machine
        "XY": ("unknown part of speech", "??"), 
        "Title": ("title for addressing a person", "Mister"),
        }

    POS_CODES = {
        "Unknown" : 0,
        "Abbr" : 1,
        "Abbr-Meas" : 2,
        "Adj" : 3,
        "Adj-Comp" : 4,
        "Adj-Sup" : 5,
        "Adv" : 6,
        "Adv-Comp" : 7,
        "Adv-IntRel" : 8,
        "Adv-Sup" : 9,
        "Aux" : 10,
        "Conj-Coord" : 11,
        "Conj" : "Conj-Sub",
        "Conj-Sub" : 12,
        "Coord" : "Conj-Coord",
        "DateP" : "Num-Date",
        "Det" : 13,
        "Det-Def" : 14,
        "Det-Indef" : 15,
        "Det-Int" : 16,
        "Det-Interrog" : "Det-Int",
        "Det-IntRel" : 17,
        "Det-Rel" : 18,
        "Det-Pl" : 19,
        "Det-Poss" : 20,
        "Det-Sg" : 21,
        "For" : "Prep",
        "Init" : "Prop-Init",
        "Interj" : 22,
        "Letter" : 23,
        "Markup-SGML" : 24,
        "Nn" : 25,
        "Nn-Pl" : 26,
        "Nn-Sg" : 27,
        "Num" : 28,
        "Num-Money" : 29,
        "Num-Percent" : 30,
        "Num-Roman" : 31,
        "Num+Roman" : "Num-Roman",              # XLE-machine typo
        "Num-Date" : 32,
        "Onom" : 33,
        "Ord" : 34,
        "Part-Inf" : 35,
        "Part-Neg" : 36,
        "Part-Poss" : 37,
        "Prep" : 38,
        "Prep-at" : "Prep",
        "Prep-of" : "Prep",
        "Pron" : 39,
        "Pron-Sg" : "Pron",
        "Pron-Pl" : "Pron",
        "Pron-Int" : 40,
        "Pron-Interrog" : "Pron-Int",
        "Pron-IntRel" : 41,
        "Pron-Refl" : 42,
        "Pron-Rel" : 43,
        "Prop" : 44,
        "Prop-Email" : 45,
        "Prop-Init" : 46,
        "Prop-URL" : 47,
        "Punct" : 48,
        "Punct-Close" : 49,
        "Punct-Comma" : "Punct",
        "Punct-Money" : 50,
        "Punct-Open" : 51,
        "Punct-Percent" : "Punct",
        "Punct-Quote" : "Punct",
        "Punct-Sent" : 52,
        "Time" : 53,
        "Symbol": "Punct",
        "V-Inf" : 54,
        "V-Inf-be" : "V-Inf",
        "V-PaPart" : 55,
        "V-PaPart-be" : "V-PaPart",
        "V-PaPart-have" : "V-PaPart",
        "V-Past" : 56,
        "V-Past-Pl-be" : "V-Past",
        "V-Past-Sg-be" : "V-Past",
        "V-Past-have" : "V-Past",
        "V-Pres" : 57,
        "V-Pres-Pl-be" : "V-Pres",
        "V-Pres-Sg-be" : "V-Pres",
        "V-Pres-have" : "V-Pres",
        "V-Pres-3-Sg" : 58,
        "V-Pres-3-Sg-have" : "V-Pres-3-Sg",
        "V-PrPart" : 59,
        "XY" : "Unknown",
        "Title" : 60,
        }

    def __init__(self, start, length, pos, text, starts_para, starts_sent, starts_phrase):
        self.start = start
        self.length = length
        self.pos = pos
        self.text = text
        self.starts_paragraph = starts_para
        self.starts_sentence = starts_sent
        self.starts_phrase = starts_phrase

    def from_match (m):
        return POSTag(int(m.group(1)), int(m.group(6)), m.group(5),
                      m.group(7),
                      bool(int(m.group(2))), bool(int(m.group(3))), bool(int(m.group(4))))
    from_match = staticmethod(from_match)

    def get_POS_code (self):
        if self.pos and (self.pos not in self.POS_CODES):
            note(0, "Unknown POS tag:  %s   (word is '%s')\n", self.pos, self.text)
            return 0
        code = POSTag.POS_CODES.get(self.pos, 0)
        while (type(code) == type('')):
            code = POSTag.POS_CODES.get(code, 0)
        return code

    def get_starts_code (self):
        if self.starts_paragraph:
            return 3
        elif self.starts_sentence:
            return 2
        elif self.starts_phrase:
            return 1
        else:
            return 0

    def parse_parseinfo (fp):

        fragments = []
        for line in fp:
            line = line.strip()
            if not line:
                continue
            m = POSTag.FRAGMENT_PATTERN.match(line)
            if m:
                fragments.append(POSTag.from_match(m))
            else:
                note(2, "bad contents.ind line found in %s:  %s", fp.name, line)
        return fragments
    parse_parseinfo=staticmethod(parse_parseinfo)

def get_page_bboxes (dirpath, page_index):

    if (not os.path.isdir(dirpath)):
        return None

    bbox_files = [int(os.path.splitext(x)[0]) for x in os.listdir(dirpath) if x.endswith(".bboxes")]
    bbox_files.sort()
    if ((page_index + 1) in bbox_files):
        return PageBBoxes(os.path.join(dirpath, "%d.bboxes" % (page_index + 1)), page_index)
    return None

def find_page (dirpath, text_pos):

    if (not os.path.isdir(dirpath)):
        return None

    # this could be improved by at the least doing a binary search

    bbox_files = [int(os.path.splitext(x)[0]) for x in os.listdir(dirpath) if x.endswith(".bboxes")]
    bbox_files.sort()
    for pageno in bbox_files:
        fileno = int(pageno)
        boxes = PageBBoxes(os.path.join(dirpath, "%d.bboxes" % fileno), fileno - 1)
        if boxes.contains_text_pos(text_pos):
            return boxes
    return None
            
class PageBBox:

    FIXED_WIDTH =       0x80
    SERIF_FONT =        0x40
    SYMBOLIC_FONT =     0x20
    ITALIC =            0x10
    BOLD =              0x08
    ENDS_LINE =         0x04
    ENDS_WORD =         0x02
    INSERTED_HYPHEN =   0x01

    POS_CODES = dict([[v,k] for k,v in POSTag.POS_CODES.items()])

    def __init__(self, page, nchars, nbytes, font_size, flags, ulx, uly, lrx, lry,
                 pos_tag, begins_para, begins_sentence, begins_phrase, textpos, baseline=0):
        self.page = page
        self.text_len = nbytes
        self.nchars = nchars
        self.font_size = font_size
        self.fixed_width = (flags & PageBBox.FIXED_WIDTH)
        self.serif_font = (flags & PageBBox.SERIF_FONT)
        self.symbolic_font = (flags & PageBBox.SYMBOLIC_FONT)
        self.italic = (flags & PageBBox.ITALIC)
        self.bold = (flags & PageBBox.BOLD)
        self.ends_line = (flags & PageBBox.ENDS_LINE)
        self.ends_word = (flags & PageBBox.ENDS_WORD)
        self.inserted_hyphen = (flags & PageBBox.INSERTED_HYPHEN)
        self.begins_paragraph = begins_para
        self.begins_sentence = begins_sentence
        self.begins_phrase = begins_phrase
        self.part_of_speech = pos_tag
        self.text_position = textpos
        self.baseline = baseline
        self.bbox = (ulx, uly, lrx, lry)

    def string(self):
        return unicode(self.page.text_bytes[self.text_position:self.text_position+self.text_len], 'utf-8', 'replace')

    def page_index(self):
        return self.page.page_index

    def __repr__(self):
        return self.__str__()

    def __str__ (self):
        return "<%s %s %s '%s'>" % (self.__class__.__name__, self.page.page_index, self.bbox,
                                    self.string().encode("ASCII", "replace"))

    def part_of_speech_tag(self):
        if (self.part_of_speech and (self.part_of_speech in self.POS_CODES)):
            return self.POS_CODES[self.part_of_speech]

class PageBBoxes:

    def __init__(self, filepath = None, page_index = None):
        self.start_pos = 0;
        self.end_pos = 0;
        self.text_bytes = None
        self.boxes = None
        self.page_index = page_index
        if filepath is not None:
            self.read_page_bboxes_file_internal(filepath, page_index)

    def read_page_bboxes_file_internal (self, filepath, page_index):
        if not os.path.exists(filepath):
            return None
        fp = open(filepath, 'rb')
        header = fp.read(20)
        if not header or len(header) != 20 or (header[:12] != "UpLib:pbb:1\0"):
            note(3, "invalid page bboxes file (bad header) in " + filepath)
        box_count, text_length, page_start = struct.unpack(">HHI", header[12:20])
        self.page_index = (page_index is not None and page_index) or self.figure_page_index_from_filename(filepath)
        note(4, "page %d, %d boxes, %d text bytes, starting at byte %d in contents.txt", self.page_index, box_count, text_length, page_start)
        boxes = list()
        data = ""
        if (box_count > 0) or (text_length > 0):
            data = zlib.decompress(fp.read())
            if len(data) != (box_count * 16) + text_length:
                note("invalid length for uncompressed box data in %s; expected %s", filepath, (text_length + (box_count * 16)))
                raise ValueError("invalid length for uncompressed box data in %s; expected %s" % (filename, (text_length + (box_count * 16))))
            fp = StringIO.StringIO(data)
            for i in range(box_count):
                data = fp.read(16)
                ulx, uly, lrx, lry, char_count, font_size, flags, text_size, unused, poscode, start = struct.unpack(">HHHHBBBBBBH", data)
                font_size = font_size / 2.0;
                pos_tag = poscode & 0x3F
                start_flags = (poscode & 0xC0) >> 6
                box = PageBBox(self, char_count, text_size, font_size, flags, ulx, uly, lrx, lry, pos_tag,
                               (start_flags > 2), (start_flags > 1), (start_flags > 0), start)
                boxes.append(box)
            data = fp.read(text_length)
        fp.close()
        # text_bytes often has a little extra at the end, since we didn't know how much we'd
        # need when we created the PageBbox file.  So fix that up.
        lastbox = boxes[-1]
        bytes = unicode(data[lastbox.text_position:], "UTF-8", "replace")[:min(lastbox.text_len, lastbox.nchars)].encode("UTF-8", "replace")
        self.text_bytes = data[:lastbox.text_position] + bytes
        # OK, it's fixed
        self.boxes = boxes
        self.starts = map(lambda x: x.text_position, boxes)
        self.start_pos = page_start
        self.end_pos = page_start + text_length
        return self

    def figure_page_index_from_filename (self, filepath):
        try:
            return (int(os.path.splitext(os.path.basename(filepath))[0]) - 1)
        except ValueError:
            return None

    def boxes_for_span (self, start, end):
        if (end < start) or (end < self.start_pos) or (start > (self.end_pos)):
            return []
        start_pos = max(start - self.start_pos, 0)
        end_pos = min(max(0, end - self.start_pos), len(self.text_bytes))
        boxes = []
        index = bisect (self.starts, start_pos)
        while (index < len(self.boxes)) and (self.boxes[index].text_position < end_pos):
            boxes.append(self.boxes[index])
            index = index + 1
        return boxes

    def box_for_pos (self, pos):
        index = bisect (self.starts, pos - self.start_pos)
        return self.boxes[index]

    def __str__(self):
        return "<%s %d %d-%d>" % (self.__class__.__name__, self.page_index, self.start_pos, self.end_pos)

    def contains_text_pos (self, text_pos):
        return (text_pos >= self.start_pos and text_pos < self.end_pos)

        

def flush_page (dirpath, page_index, bboxes, pagetext, pagestart):

    filepath = os.path.join(dirpath, "thumbnails", "%d.bboxes" % (page_index + 1))
    fp = open(filepath, 'wb')

    count = len(bboxes)
    if (count < 1):
        fp.write("UpLib:pbb:1\0" + struct.pack(">HHI", 0, 0, pagestart))
        fp.flush()
        fp.close()
        note(3, "   0 merged bboxes and 0 bytes of text, 0 compressed, in %d.bboxes", (page_index + 1))
        return

    # merge same word bboxes into one bbox
    i = 0
    realcount = 0
    merged_bboxes = []
    while i < count:
        bbox, tag, ulx, uly, lrx, lry = bboxes[i]
        char_count = bbox.nchars()
        textindex = bbox.contents_offset()
        ends_line = bbox.ends_line()
        ends_word = bbox.ends_word()
        while (not (ends_line or ends_word)) and (i < (count - 1)):
            # fragment of a word.  Unite with other bounding boxes
            i = i + 1
            bbox2, tag2, ulx2, uly2, lrx2, lry2 = bboxes[i]
            char_count = char_count + bbox2.nchars()
            ends_line = bbox2.ends_line()
            ends_word = bbox2.ends_word()
            ulx = min(ulx, ulx2)
            uly = min(uly, uly2)
            lrx = max(lrx, lrx2)
            lry = max(lry, lry2)
        textend = ((i < (count - 1)) and bboxes[i+1][0].contents_offset()) or len(pagetext)
        if isinstance(tag, int):
            poscode = tag
        elif isinstance(tag, POSTag):
            poscode = (tag.get_starts_code() << 6) | tag.get_POS_code()
        else:
            poscode = 0
        try:
            merged_bboxes.append(struct.pack(">HHHHBBBBBBH",
                                             max(0, ulx) & 0xFFFF, max(0, uly) & 0xFFFF,
                                             max(0, lrx) & 0xFFFF, max(0, lry) & 0xFFFF,
                                             char_count & 0xFF, int(bbox.font_size() * 2) & 0xFF,
                                             bbox.flags() & 0xFF, (textend - textindex) & 0xFF, 0, poscode & 0xFF,
                                             max(0, textindex - pagestart) & 0xFFFF))
        except OverflowError, x:
            note("OverflowError(%s) attempting to pack %s", x, (
                ulx, uly, lrx, lry, char_count, bbox.font_size(), bbox.flags(),
                textend - textindex, 0, poscode, textindex - pagestart))
            raise x
            
        realcount = realcount + 1
        i = i + 1

    # compress the data
    compression_buffer = StringIO.StringIO()
    for s in merged_bboxes:
        compression_buffer.write(s)
    compression_buffer.write(pagetext)
    compressed_content = zlib.compress(compression_buffer.getvalue(), 9)
    # compressed_content = compression_buffer.getvalue()
    compression_buffer.close()

    note(3, "   %d merged bboxes and %d bytes of text, %d compressed, in %d.bboxes",
         len(merged_bboxes), len(pagetext), len(compressed_content), (page_index + 1));

    # now write the file
    fp.write("UpLib:pbb:1\0" + struct.pack(">HHI", realcount & 0xFFFF, len(pagetext) & 0xFFFF, pagestart))
    fp.write(compressed_content)
    fp.close()

def do_page_bounding_boxes (dirpath):

    textfilepath = os.path.join(dirpath, "contents.txt")
    wordbox_file = open(os.path.join(dirpath, "wordbboxes"), 'rb')
    pos_filepath = os.path.join(dirpath, "contents.ind")
    para_filepath = os.path.join(dirpath, "paragraphs.txt")

    note ("doing page bboxes for %s...", dirpath)

    if os.path.exists(pos_filepath):
        fp = open(pos_filepath, 'r')
        postags = POSTag.parse_parseinfo(fp)
        fp.close()
    else:
        postags = None

    bbox_iterator = wordboxes_page_iterator(dirpath)

    text_file = open(textfilepath, 'rb')
    firstline = text_file.readline()
    charsetmatch = CHARSETPATTERN.match(firstline)
    if charsetmatch:
        charsetname = charsetmatch.group(1)
        text_file.readline()
        first_byte = text_file.tell()
    else:
        charsetname = "latin_1"
        readlines = false
        first_byte = 0
    if charsetname not in UTF8_ALIASES:
        raise ValueError("Charset in contents.txt must be UTF-8 for page bounding boxes to be created.  Apparently it's %s, instead." % charsetname)
    text_file.seek(first_byte)

    paras = read_paragraphs_file(para_filepath)
    if paras: paras.sort(key=lambda x: x.first_byte)

    from createThumbnails import thumbnail_translation_and_scaling
    translation, scaling = thumbnail_translation_and_scaling (dirpath)
    note(4, "   translation and scaling are %s and %s...", translation, scaling)

    def update_stats (stats, page_stats):
        if stats:
            stats += ", "
        stats += "%d:%.3f:%d:%d:%d:%d:%.3f" % (page_stats[0],
                                               ((page_stats[0] > 0) and float(page_stats[1])/float(page_stats[0]) or 0.0),
                                               page_stats[2], page_stats[3], page_stats[4], page_stats[5],
                                               ((page_stats[0] > 0) and float(page_stats[6])/float(page_stats[0]) or 0.0))
        return stats
        

    page_index = 0
    out_page_index = 0
    last_cindex = 0
    bboxes = []
    postags_index = 0

    stats = ""

    # accumulate stats
    doc_stats = [
        0,              # number of words
        0,              # total length (in characters)
        0,              # number of bold words
        0,              # number of italic words
        0,              # number of bold-italic words
        0,              # number of fixed-width words
        0.0,            # total font sizes
        ]

    for page_index, bboxes in bbox_iterator:

        page_stats = [
            0,              # number of words
            0,              # total length (in characters)
            0,              # number of bold words
            0,              # number of italic words
            0,              # number of bold-italic words
            0,              # number of fixed-width words
            0.0,            # total font sizes
            ]

        adjusted_bboxes = []

        for bbox in bboxes:

            char_count = bbox.nchars()

            doc_stats[0] += 1
            doc_stats[1] += bbox.nchars()
            if bbox.is_bold():
                doc_stats[2] += 1
            if bbox.is_italic():
                doc_stats[3] += 1
            if bbox.is_bold() and bbox.is_italic():
                doc_stats[4] += 1
            if bbox.is_fixedwidth():
                doc_stats[5] += 1
            doc_stats[6] += bbox.font_size()

            page_stats[0] += 1
            page_stats[1] += bbox.nchars()
            if bbox.is_bold():
                page_stats[2] += 1
            if bbox.is_italic():
                page_stats[3] += 1
            if bbox.is_bold() and bbox.is_italic():
                page_stats[4] += 1
            if bbox.is_fixedwidth():
                page_stats[5] += 1
            page_stats[6] += bbox.font_size()

            cindex = bbox.contents_offset()

            tag = None
            if postags:
                # advance to first POS tag which might apply to cindex
                while ((postags_index < len(postags)) and
                       (cindex >= (postags[postags_index].start + postags[postags_index].length))):
                    postags_index = postags_index + 1
                # might be cindex positions for which we have not tags -- check for that
                if ((postags_index < len(postags)) and (cindex >= postags[postags_index].start) and
                    (cindex < (postags[postags_index].start + postags[postags_index].length))):
                    tag = postags[postags_index]

            if paras and (paras[0].first_byte <= (cindex + char_count)) and (paras[0].first_byte_not >= cindex):
                # starts this paragraph
                if tag is None:
                    tag = POSTag(cindex, char_count, None, "",
                                 True, False, False)
                else:
                    tag.starts_paragraph = True
                paras = paras[1:]

            # again, add back in the 20-pixel border on the page
            ulx = trunc((bbox.left() + translation[0]) * scaling[0] + 0.5)
            uly = trunc((bbox.top() + translation[1]) * scaling[1] + 0.5)
            lrx = trunc((bbox.right() + translation[0]) * scaling[0] + 0.5)
            lry = trunc((bbox.bottom() + translation[1]) * scaling[1] + 0.5)

            adjusted_bboxes.append((bbox, tag, ulx, uly, lrx, lry))
            last_cindex = cindex

        if (len(adjusted_bboxes) > 0):

            startpoint = adjusted_bboxes[0][0].contents_offset()
            endpoint = adjusted_bboxes[-1][0].contents_offset() + (adjusted_bboxes[-1][0].nchars() * 4)
            text_file.seek(startpoint + first_byte)
            pagetext = text_file.read(endpoint - startpoint)
            pagestart = startpoint

        else:
            pagetext = ""
            pagestart = last_cindex

        flush_page (dirpath, page_index, adjusted_bboxes, pagetext, pagestart)

        stats = update_stats(stats, page_stats)

    text_file.close()
    wordbox_file.close()

    dstats = update_stats("", doc_stats)

    update_metadata(os.path.join(dirpath, "metadata.txt"), { "wordbbox-stats-pagewise": stats, "wordbbox-stats-docwise": dstats})
            

def calculate_page_bboxes (repo, path, doc_id=None):
    if (os.path.isdir(path) and
        os.path.exists(os.path.join(path, "contents.txt")) and
        (os.path.getsize(os.path.join(path, "contents.txt")) > 0) and
        os.path.isdir(os.path.join(path, "thumbnails")) and
        os.path.exists(os.path.join(path, "wordbboxes"))):
        do_page_bounding_boxes(path)


class BboxesRipper (Ripper):

    def rip (self, location, doc_id):
        try:
            calculate_page_bboxes(self.repository(), location)
        except:
            msg = ''.join(traceback.format_exception(*sys.exc_info()))
            note("Exception processing %s:\n%s\n" % (doc_id, msg))
            note("No page bounding boxes generated.")
            raise

if __name__ == "__main__":
    # little test
    from uplib.plibUtil import set_verbosity
    set_verbosity(4)
    do_page_bounding_boxes(sys.argv[1])
