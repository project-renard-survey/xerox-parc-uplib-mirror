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

"""
Contains an UpLib DocumentParser module for JPEG2000 images.
Requires Jasper 1 or better be installed.
"""

__author__ = "Bill Janssen"

__version__ = "$Revision: 1.4 $"

JASPER = None
"""Location of the jasper program"""

import sys, os
from uplib.plibUtil import configurator, note, subproc

conf = configurator.default_configurator()
JASPER = conf.get("jasper")
#note("JASPER is %s, %s", JASPER, os.path.exists(JASPER.strip('"')))
if JASPER and os.path.exists(JASPER.strip('"')):

    from uplib.addDocument import DocumentParser, ImageDoc, mktempfile, convert_image_to_tiff
    from PIL import Image

    class JPEG2000Doc (ImageDoc):

        """DocumentParser subclass for JPEG2000 images.  Uses jasper
        program to convert image for page-image projection.
        """

        format_mimetype = "image/jp2"

        BEFORE = ("TIFFDoc", "ImageDoc")

        @staticmethod
        def myformat (pathname):

            basename, ext = os.path.splitext(pathname)
            if ext in (".jp2", ".JP2", ".JPEG2000"):
                return True
            else:
                return False

        def __init__(self, doc, options):
            DocumentParser.__init__(self, doc, options)

        def write_metadata(self):

            if not self.metadata.has_key("images-dpi"):
                note(3, "   using default DPI of 75")
                self.metadata["images-dpi"] = "75"
            ImageDoc.write_metadata(self)

        def get_page_images (self):

            tf = mktempfile(".pnm")
            cmd = ('"%s" --input-format jp2 --input "%s" --output-format pnm --output "%s"'
                   % (JASPER, self.doc, tf))
            try:
                status, output, tsignal = subproc(cmd)
                if status == 0:
                    # success
                    img = Image.open(tf)
                    imagespath = self.images_path()
                    os.mkdir(imagespath)
                    if self.uses_png:
                        png_file_name = os.path.join(imagespath, "page00001.png")
                        img.save(png_file_name, "PNG")
                    else:
                        if (convert_image_to_tiff(tf, imagespath)):
                            note(3, "created tiff file in %s", imagespath)
                else:
                    note("Can't convert %s.  Output was %s.", self.doc, output)
                    note(4, "cmd was %s", cmd)
                    note(4, "tfile %s %s", tf, (os.path.exists(tf) and "exists") or "does not exist")
                    raise RuntimeError(output)
            finally:
                if os.path.exists(tf):
                    os.unlink(tf)
