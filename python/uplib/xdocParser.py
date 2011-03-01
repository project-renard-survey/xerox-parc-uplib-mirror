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

import string, re, os, sys, traceback, math

from uplib.plibUtil import note, true, false, set_verbosity

#
# To get XDOC from TextBridge, invoke it with the "-f xdoc -wbox" switches.
#
# Note that units for wordboxes are tenths of a millimeter.
#
# Note that each page header has page size and offset (??) (among other things).
#
# More up-to-date manual is at http://elib.cs.berkeley.edu/info/core12xdc.rtf.
#

MARKUP = re.compile(r"\[(([XYRa-z];[^\[\]]+\])|([A-Z]))", re.MULTILINE)
FONT = re.compile(r"\[f;([0-9]+);\"([^\"]+)\";([A-Z]);([a-z]);[0-9]+;(F|V);[0-9]+;[0-9]+;[0-9]+;([0-9]+);[0-9]+\]")
PAGE = re.compile(r"\[p;([0-9]+);(P|L);[0-9]+;[A-Z]+;([-0-9\.]+);([-0-9\.]+);([-0-9]+);([-0-9]+);([-0-9]+);([-0-9]+);[-0-9]+;[-0-9]+\]")
WBOX = re.compile(r"\[b;([0-9]+);([0-9]+);([0-9]+);([0-9]+);([0-9]+);([0-9]+)\]")
REGION = re.compile(r"\[t;([0-9]+);[0-9]+;([0-9]+);([0-9]+);[A-Z];[\"A-Za-z0-9]+;[\"A-Za-z0-9]+;[\"A-Za-z0-9]+;([0-9]+);([0-9]+);([0-9]+);([0-9]+);[0-9]+;[0-9]+\]")
LANGUAGE = re.compile(r"\[O;([0-9]+);([0-9]+)\]")

# found in /project/did/src/system/stackcicp/src/alpaca/alplib/include/icr_char.h
"""
#define L_SINGLE_QUOTE	((CHVAL) '\201')	/* left single quote	*/

#define R_SINGLE_QUOTE	((CHVAL) '\202')	/* right single quote	*/

#define L_DOUBLE_QUOTE	((CHVAL) '\203')	/* left double quote	*/

#define R_DOUBLE_QUOTE	((CHVAL) '\204')	/* right double quote	*/

#define EM_DASH		((CHVAL) '\205')	/* a wide dash		*/

#define BULLET		((CHVAL) '\206')

#define USYMRK     	((CHVAL) '\207')	/* user-defined symbol mark */

#define UNREC		((CHVAL) '\210')	/* unrecognized character */

#define NOISE		((CHVAL) '\211')	/* not a character	*/


/* The following are used in German.					*/

#define SINGLE_LOW_QUOTE ((CHVAL) '\212')	/* single lower quote	*/

#define DOUBLE_LOW_QUOTE ((CHVAL) '\213')	/* double lower quote	*/
"""

XDOC_TO_1252 = string.maketrans('\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b',
                                '\x91\x92\x93\x94\x97\x95\xae\x3f\x3f\x82\x84')

class Word:

    def __init__ (self, s, page, language, font, region, underline, wordbox):
        if language:
            cp = 'windows-' + language.codepage
            self.str = unicode(s, cp, "replace")
        else:
            self.str = unicode(string.translate(s, XDOC_TO_1252, None), 'windows-1252', 'replace')
        self.page = page
        self.font = font
        self.region = region
        self.underlined = underline
        self.wordbox = wordbox
        self.hyphenated = false;
        self.space_follows = true
        self.ends_line = false;

    def wordboxes_line(self, ppi):
        scaling = float(300)/float(ppi)
        points = [(scaling * x) for x in self.wordbox.values]
        fontsize = scaling * self.font.size
        t = ("%11f %11f " % (points[0], points[1]) +
             "%11f %11f  " % (points[2],  points[3]) +
             "%1d %4.1f " % (1, fontsize) +
             "%1d " % ((self.font.fixedwidth and 1) or 0) +
             "%1d " % ((self.font.serif and 1) or 0) +
             "%1d " % 0 +        # symbolic font
             "%1d " % (((self.font.face == 'I') and 1) or 0) +
             "%1d  " % (((self.font.face == 'B') and 1) or 0) +
             "%1d " % ((self.hyphenated and 1) or 0) +
             "%1d " % ((self.space_follows and 1) or 0) +
             "%1d " % ((self.ends_line and 1) or 0) +
             "%4d " % len(self.str))
        for c in self.str:
            t = t + "%6d " % ord(c)
        t = t + "\""
        for c in self.str.encode("US-ASCII", "replace"):
            t = t + c
        t = t + "\""
        return t

    def text(self):
        return self.str + ((self.hyphenated and u"-") or u"") + ((self.space_follows and u" ") or u"") + ((self.ends_line and u"\n") or "")
    def __str__(self):
        return "<Word %s %s>" % (self.str, self.wordbox)
                

class Markup:

    mtype = "markup"

    def __init__ (self, str):
        self.codes = str

    def __str__ (self):
        return "<%s %s>" % (self.mtype, self.codes)


class Region (Markup):

    mtype = "region"

    def __init__ (self, str):
        Markup.__init__(self, str)
        m = REGION.match(str)
        if not m:
            raise ValueError("bad region string:  %s" % str)
        self.id = m.group(1)
        self.zone_top = int(m.group(2))
        self.zone_height = int(m.group(3))
        self.frame_top = int(m.group(4))
        self.frame_left = int(m.group(5))
        self.frame_right = int(m.group(6))
        self.frame_bottom = int(m.group(7))


class Language (Markup):

    mtype = "language"

    def __init__ (self, str):
        Markup.__init__(self, str)
        m = LANGUAGE.match(str)
        if not m:
            raise ValueError("bad region string:  %s" % str)
        self.language = m.group(3)
        self.codepage = m.group(2)

    def __str__(self):
        return '<language %d; windows code page %d>' % (self.language, self.codepage)

class Font (Markup):

    mtype = "font"

    def __init__ (self, str):
        Markup.__init__(self, str)
        m = FONT.match(str)
        if not m:
            raise ValueError("bad font string:  %s" % str)
        self.id = m.group(1)
        self.family = m.group(2)
        self.face = m.group(3)
        self.serif = (m.group(4) == 's')
        self.fixedwidth = (m.group(5) == 'F')
        self.size = int(m.group(6))

    def __str__(self):
        return "<font %s %s%dpt, %s, %s>" % (self.family, ((self.face == 'B') and "bold ") or ((self.face == 'T') and "italic ") or "", self.size, (self.serif and "serif") or "sans", (self.fixedwidth and "fixed") or "prop.")



def map_tenth_mm_to_points (str):

    v = (float(str) * 72) / 2540

class Wordbox (Markup):

    mtype = "wbox"

    def __init__ (self, str):
        Markup.__init__(self, str)
        m = WBOX.match(str)
        if not m:
            raise ValueError("bad wordbox string:  %s" % str)
        self.values = map(lambda x: (float(x) * 72) / 254, m.groups())

    def __str__ (self):
        return "<wordbox %dx%d+%d+%d>" % ((self.values[2] - self.values[0]), (self.values[3] - self.values[1]), self.values[0], self.values[1])

class Page (Markup):

    current_page = None
    mtype = "page"

    def __init__ (self, str):
        Markup.__init__(self, str)
        m = PAGE.match(str)
        if not m:
            raise ValueError("bad page string:  %s" % str)
        self.language = None
        self.pageno = int(m.group(1))
        self.orientation = m.group(2)   # P or L
        self.skew = float(m.group(3))
        self.untilt = float(m.group(4))
        self.ul_corner = (int(m.group(5)), int(m.group(6)),)
        self.width = (float(m.group(7)) / 254)
        self.height = (float(m.group(8)) / 254)
        self.fonts = {}
        self.regions = {}
        self.words = []
        self.underline = false
        self.current_font = None
        self.current_region = None
        self.wordbox = None

    def __str__ (self):
        return "<page %d:  %fx%f+%d+%d, skew %f, untilt %f>" % (self.pageno, self.width, self.height, self.ul_corner[0], self.ul_corner[1], self.skew, self.untilt)

    def setWbox(self, b):
        self.wordbox = b

    def addFont (self, f):
        self.fonts[f.id] = f
        return f

    def addRegion (self, r):
        self.regions[r.id] = r
        return r

    def setLanguage (self, l):
        self.language = l

    def addWord (self, w):
        if self.wordbox == None:
            note(3, "addWord('%s') called with null wordbox", w)
        else:
            note(5, "addWord('%s') at %s", w, self.wordbox)
            self.words.append(Word(w, self, self.language, self.current_font, self.current_region, self.underline, self.wordbox))

    def addMarkup(self, m):
        self.words.append(m)
        if m.codes.startswith("[c;"):
            font = self.fonts.get(m.codes[3:-1])
            if font:
                self.current_font = font
            else:
                print "bad font selector:  %s" % m.codes
        elif m.codes.startswith("[e;"):
            region = self.regions.get(m.codes[3:-1])
            if region:
                self.current_region = region
            else:
                print "bad region selector:  %s" % m.codes
        elif m.codes == '[U':
            self.underline = not self.underline

    def endLine (self):
        i = len(self.words)
        while (i > 0):
            if isinstance(self.words[i-1], Word):
                self.words[i-1].ends_line = true
                break
            i = i - 1

    def addText (w):
        Page.current_page.addWord(w)
    addText = staticmethod(addText)

    def newRegion(str):
        return Page.current_page.addRegion(Region(str))
    newRegion = staticmethod(newRegion)

    def newLanguage(str):
        return Page.current_page.setLanguage(Language(str))
    newLanguage = staticmethod(newLanguage)

    def newPage (str):
        Page.current_page = Page(str)
        return Page.current_page
    newPage = staticmethod(newPage)

    def newFont (str):
        return Page.current_page.addFont(Font(str))
    newFont = staticmethod(newFont)

    def newWbox (str):
        return Page.current_page.setWbox(Wordbox(str))
    newWbox = staticmethod(newWbox)

    def show (self, words_only):
        if not words_only:
            fkeys = self.fonts.keys()
            fkeys.sort()
            for key in fkeys:
                font = self.fonts[key]
                print "%s:  %s" % (font.id, font)
        for word in self.words:
            if isinstance(word, Word):
                print '%s %s %s' % (repr(word.str), word.font, word.wordbox)
            elif not words_only:
                if isinstance(word, Markup):
                    print '*** %s' % repr(word)
                else:
                    print '??? %s' % repr(word)

    def text(self):
        r = u""
        for word in self.words:
            if isinstance(word, Word):
                r += word.text()
        return r

    def wordbox_lines(self, fp, ppi):
        for word in self.words:
            if isinstance(word, Word):
                try:
                    fp.write(word.wordboxes_line(ppi) + "\n")
                except:
                    typ, value, tb = sys.exc_info()
                    msg = string.join(traceback.format_exception(typ, value, tb))
                    note("word %s raised exception:\n%s", word, msg)

def add_markup (str):
    if str.startswith("[p;"):
        return Page.newPage(str)
    elif str.startswith("[f;"):
        return Page.newFont(str)
    elif str.startswith("[b;"):
        return Page.newWbox(str)
    elif str.startswith("[t;"):
        return Page.newRegion(str)
    elif str.startswith("[O;"):
        return Page.newLanguage(str)
    elif str.startswith("[y;"):
        Page.current_page.endLine()
        m = Markup(str)
        Page.current_page.addMarkup(m)
        note(5, "markup is %s", m)
        return m
    elif Page.current_page:
        m = Markup(str)
        Page.current_page.addMarkup(m)
        note(5, "markup is %s", m)
        return m    
    else:
        note(4, "markup '%s' dropped", str)

def parse_XDOC_input (inp):

    ptr = inp
    outp = list()

    m = MARKUP.search(ptr)
    while m:
        if m.start() > 0:
            if ptr[:m.start()].strip():
                Page.addText(ptr[:m.start()].strip())
        mrk = add_markup(m.group())
        if isinstance(mrk, Page):
            outp.append(mrk)
        ptr = ptr[m.end():]
        m = MARKUP.search(ptr)
    if ptr and ptr.strip():
        Page.addText(ptr.strip())
        
    return outp


def parse_XDOC_file (input_file, output_file, ppi=300):

    pagetext = ""
    pageno = 1
    lineno = 1
    line = input_file.readline()
    while line:
        while line and (line != '\f\n'):
            pagetext += line
            line = input_file.readline()
            lineno += 1
        pages = parse_XDOC_input(pagetext)
        for page in pages:
            page.wordbox_lines(output_file, ppi)
            output_file.write("\f\n")
        note(3, "page %d finished at line %d", pageno, lineno)
        pagetext = ""
        pageno += 1
        line = input_file.readline()
        lineno += 1


if __name__ == "__main__":
    set_verbosity(5)
    input_file = open(sys.argv[1], 'r')
    parse_XDOC_file(input_file, sys.stdout)

#     pages = parse_XDOC_input(open(sys.argv[1], 'r').read())
#     for page in pages:
#         page.wordbox_lines(sys.stdout)
#         sys.stdout.write("\f\n")

      
        
