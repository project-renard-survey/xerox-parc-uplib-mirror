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

import sys, os, string, datetime, re, traceback, cgi, types, shutil, urllib, time, pickle, codecs

from uplib.plibUtil import note, set_verbosity, true, false, subproc, configurator, MutexLock
from uplib.webutils import HTTPCodes
from uplib.addDocument import mktempfile, HTMLDOC, Error, CONTENT_TYPES, DocumentParser, mktempdir, MultiPartDocument, MissingResource
from uplib.collection import Collection
from uplib.basicPlugins import STANDARD_LEGEND_COLOR, STANDARD_BACKGROUND_COLOR

try:
    import pyglet
except:
    note("No pyglet -- video parser support not provided")
    raise MissingResource("\"pyglet\" video processing library, from http://www.pyglet.org/")

try:
    from PIL import Image
except:
    raise MissingResource("PIL image processing library, from http://www.pythonware.com")

try:
    import hachoir_parser
    import hachoir_metadata
except ImportError:
    note("No hachoir -- limited support for video metadata extraction")
    # no hachoir support
    have_hachoir = False
else:
    have_hachoir = True
    

CONTENT_TYPES['video/mp4'] = "mp4"
CONTENT_TYPES['video/x-ms-wmv'] = "wmv"
CONTENT_TYPES['video/mpeg'] = "mpg"
CONTENT_TYPES['video/quicktime'] = "mov"

UPLIB_SHARE = None

class Video (DocumentParser):

    format_mimetype = "video"

    BEFORE = ("Music",)
    AFTER = ("TIFFDoc", "ImageDoc")

    def myformat(pathname):

        if (os.path.splitext(pathname)[1] not in (".mp4", ".wmv", ".mpg", ".mov", ".qt")):
            return False
        try:
            source = pyglet.media.load(pathname)
        except:
            return False
        if not source.video_format:
            # video track is unreadable
            return False
        return { "video": source }

    myformat = staticmethod(myformat)

    NSAMPLES = None

    def get_video_size(width, height, sample_aspect):
        if sample_aspect > 1.:
            return width * sample_aspect, height
        elif sample_aspect < 1.:
            return width, height / sample_aspect
        else:
            return width, height
    get_video_size = staticmethod(get_video_size)

    def __init__(self, doc, options):
        global UPLIB_SHARE
        DocumentParser.__init__(self, doc, options)
        self.video = options.get("video")
        if not self.video:
            self.video = pyglet.media.load(doc)
            if not self.video.video_format:
                raise ValueError("Unknown video format encountered")
        self.size = self.get_video_size(self.video.video_format.width,
                                        self.video.video_format.height,
                                        self.video.video_format.sample_aspect)
        if (UPLIB_SHARE is None) or (self.NSAMPLES is None):
            c = configurator.default_configurator()
            UPLIB_SHARE = c.get("uplib-share")
            self.NSAMPLES = c.get_int("number-of-video-sample-frames", 5)
        duration = self.video.duration
        if duration:
            self.metadata['duration'] = str(duration)
        if have_hachoir:
            try:
                md = hachoir_metadata.extractMetadata(hachoir_parser.createParser(
                    unicode(doc), doc))
                d = {}
                for v in md:
                    if v.values:
                        d[v.key] = v.values[0].value
                v = d.get("last_modification")
                if v:
                    self.metadata['last-modified'] = v.isoformat('Z')
                    note("last-modified is %s", self.metadata['last-modified'])
                v = d.get("creation_date") or v
                if v:
                    self.metadata['date'] = v.strftime("%m/%d/%Y")
                mime_type = d.get("mime_type")
                if mime_type:
                    self.metadata['apparent-mime-type'] = mime_type
            except:
                pass
        # don't try to optimize away blank frames if we don't have many frames
        self.saveblanks = self.saveblanks or (self.NSAMPLES < 2)

    def pyglet_to_pil_image (pyglet_image):
        image = pyglet_image.get_image_data()
        format = image.format
        if format != 'RGB':
            # Only save in RGB or RGBA formats.
            format = 'RGBA'
        pitch = -(image.width * len(format))

        # Note: Don't try and use frombuffer(..); different versions of
        # PIL will orient the image differently.
        pil_image = Image.fromstring(
            format, (image.width, image.height), image.get_data(format, pitch))
        # need to flip the image to accommodate Pyglet's transform space
        pil_image = pil_image.transpose(Image.FLIP_TOP_BOTTOM)
        return pil_image
    pyglet_to_pil_image=staticmethod(pyglet_to_pil_image)

    def get_page_images(self):

        if not os.path.exists(self.images_path()):
            os.makedirs(self.images_path())
        imagespath = os.path.join(self.images_path(), "page00001.png")

        # try to get the first frame
        try:
            frame = self.video.get_next_video_frame()
            img = self.pyglet_to_pil_image(frame)
            img.save(imagespath, 'PNG')
        except:
            raise

        # get more frames
        duration = self.video.duration
        if duration:
            interval = duration/float(self.NSAMPLES - 1)
            player = pyglet.media.Player()
            player.queue(self.video)
            position = 0
            pagecount = 1
            while position < duration:
                position += interval
                player.seek(position)
                # try to get the first frame
                try:
                    frame = player.source.get_next_video_frame()
                    img = self.pyglet_to_pil_image(frame)
                    pagecount += 1
                    img.save(os.path.join(self.images_path(), "page%05d.png" % pagecount), 'PNG')
                except:
                    raise

            
