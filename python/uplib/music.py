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

import sys, os, string
import re, traceback, cgi, types, shutil, urllib, time, pickle, codecs

# need PIL for attachment images
from PIL import Image, ImageChops, ImageOps

from uplib.plibUtil import note, set_verbosity, true, false, subproc, configurator, MutexLock
from uplib.webutils import HTTPCodes
from uplib.addDocument import mktempfile, Error, CONTENT_TYPES, DocumentParser, mktempdir, MultiPartDocument, MissingResource
from uplib.collection import Collection
from uplib.basicPlugins import STANDARD_LEGEND_COLOR, STANDARD_BACKGROUND_COLOR

try:
    from uplib.language import identify_language
except:
    identify_language = None

#
# uses the Mutagen audio tagging library, http://www.sacredchao.net/quodlibet/wiki/Development/Mutagen
#

try:
    import mutagen
except:
    raise MissingResource("\"mutagen\" audio tagging library, from http://www.sacredchao.net/quodlibet/wiki/Development/Mutagen")

CONTENT_TYPES['audio/mp3'] = "mp3"
CONTENT_TYPES['audio/mpeg'] = "mp3"

UPLIB_SHARE = None

class Music (DocumentParser):

    format_mimetype = "audio"

    def myformat(pathname):
        from mutagen import File
        try:
            track = File(pathname)
        except:
            return False
        if (track is not None) and track.mime and (track.mime[0].split("/")[0] == "audio"):
            return { "musictrack" : track }
        else:
            return False
    myformat = staticmethod(myformat)

    def __init__(self, doc, options):
        global UPLIB_SHARE
        DocumentParser.__init__(self, doc, options)
        self.musictrack = options.get("musictrack")
        self.genre = None
        self.artwork = None
        if UPLIB_SHARE is None:
            c = configurator()
            UPLIB_SHARE = c.get("uplib-share")

    def get_page_images(self):

        if not os.path.exists(self.images_path()):
            os.makedirs(self.images_path())
        imagespath = os.path.join(self.images_path(), "page00001.png")

        if self.artwork:
            try:
                from PIL import Image, StringIO
                im = Image.open(StringIO.StringIO(self.artwork[1]))
                if im:
                    im.save(imagespath, "PNG")
                    return
            except:
                note("exception trying to use PIL on MP3 cover art")
                pass

        else:

            # check self.metadata['music-genre'] and pick the right genre icon
            self.metadata['images-dpi'] = '100'
            genre = self.metadata.get('music-genre', 'generic')
            note("music-genre is %s", genre)
            genre_icon_path = os.path.join(UPLIB_SHARE, "images", "music", genre.lower() + ".png")
            if os.path.exists(genre_icon_path):
                shutil.copyfile(genre_icon_path, imagespath)
            else:
                genre_icon_path = os.path.join(UPLIB_SHARE, "images", "music", "generic.png")
                shutil.copyfile(genre_icon_path, imagespath)

    def get_text(self):
        if 'lyrics' in self.metadata:
            textpath = self.text_path()
            text = self.metadata["lyrics"]
            if text.strip():
                if identify_language:
                    lang = identify_language(text)
                else:
                    lang = "en-us"
                fp = codecs.open(self.text_path(), 'wb', 'utf_8')
                fp.write('Content-Type: text/plain;charset=utf-8\nContent-Language: %s\n' % lang)
                fp.write(text)
                fp.close()


class MP3 (Music):

    BEFORE = (Music,)

    format_mimetype = "audio/mpeg"

    def myformat(pathname):
        m = Music.myformat(pathname)
        from mutagen.mp3 import MPEGInfo
        if m and (type(m['musictrack'].info) == MPEGInfo):
            return m
        return false
    myformat = staticmethod(myformat)

    def __init__(self, doc, options):
        Music.__init__(self, doc, options)

        # extract the metadata -- see http://www.id3.org/

        if 'COMM' in self.musictrack:
            self.metadata['comment'] = self.musictrack.get('COMM').text[0]
        if 'TALB' in self.musictrack:
            self.metadata['album'] = self.musictrack.get('TALB').text[0]
        if 'TCOM' in self.musictrack:
            self.metadata['composer'] = self.musictrack.get('TCOM').text[0]
        if 'TCON' in self.musictrack:
            self.metadata['music-genre'] = self.musictrack.get('TCON').text[0]
        if 'TIT2' in self.musictrack:
            self.metadata['title'] = self.musictrack.get('TIT2').text[0]
        if 'TLEN' in self.musictrack:
            self.metadata['audio-length'] = self.musictrack.get('TLEN').text[0]
        if 'TPE1' in self.musictrack:
            self.metadata['performer'] = self.musictrack.get('TPE1').text[0]
        if 'TPE2' in self.musictrack:
            self.metadata['accompaniment'] = self.musictrack.get('TPE2').text[0]
        if 'TPE3' in self.musictrack:
            self.metadata['conductor'] = self.musictrack.get('TPE3').text[0]
        if 'TRCK' in self.musictrack:
            self.metadata['track'] = self.musictrack.get('TRCK').text[0]

        day = 0
        year = 0
        month = 0
        if 'TDAT' in self.musictrack:
            tdat = self.musictrack.get('TDAT').text[0]
            day = int(tdat[:2])
            month = int(tdat[2:])
        if 'TYER' in self.musictrack:
            year = int(self.musictrack.get('TYER').text[0])
        if 'TDRC' in self.musictrack:
            tdrc = str(self.musictrack.get('TDRC').text[0])
            # timestamp format -- some prefix (possibly all) of "YYYY-MM-DDTHH:MM:SS"
            if len(tdrc) >= 4:
                year = int(tdrc[:4])
            if len(tdrc) >= 7:
                month = int(tdrc[5:7])
            if len(tdrc) >= 10:
                month = int(tdrc[8:10])
        elif 'TDRL' in self.musictrack:
            tdrl = str(self.musictrack.get('TDRL').text[0])
            # timestamp format -- some prefix (possibly all) of "YYYY-MM-DDTHH:MM:SS"
            if len(tdrl) >= 4:
                year = int(tdrl[:4])
            if len(tdrl) >= 7:
                month = int(tdrl[5:7])
            if len(tdrl) >= 10:
                month = int(tdrl[8:10])
        if year != 0:
            self.metadata['date'] = "%s/%s/%s" % (month, day, year)

        if 'USLT' in self.musictrack:
            self.metadata['lyrics'] = str(self.musictrack.get('USLT'))
        elif 'SYLT' in self.musictrack:
            self.metadata['lyrics'] = str(self.musictrack.get('SYLT'))

        if 'APIC' in self.musictrack:
            pic = self.musictrack.get('APIC')
            self.artwork = (pic.mime, pic.data)

        legend = ""
        authors = ""
        if 'performer' in self.metadata:
            authors += self.metadata.get('performer')
        if 'accompaniment' in self.metadata:
            if authors: authors += " and "
            authors += self.metadata.get('accompaniment')
        if 'conductor' in self.metadata:
            if authors: authors += " and "
            authors += self.metadata.get('conductor')
        if 'composer' in self.metadata:
            if authors: authors += " and "
            authors += self.metadata.get('composer')
        if authors:
            # legend = '(0xA0, 0x18,0x40)' + authors
            legend = '(0xA0, 0x20,0x20)' + authors
            self.metadata['authors'] = authors

        if 'title' in self.metadata:
            if legend: legend += "|"
            legend += ('(0x0,0x60,0x20)' + self.metadata.get('title'))
        if 'album' in self.metadata:
            if legend: legend += "|"
            legend += ('(0x0,0x20,0x60)' + self.metadata.get('album'))

        if legend: self.metadata['document-icon-legend'] = legend
