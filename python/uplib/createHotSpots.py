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

import sys, string, os, re, unicodedata, traceback

from uplib.ripper import Ripper
from uplib.plibUtil import note, lock_folder, unlock_folder, update_metadata, read_file_handling_charset
from uplib.pageview import Hotspot
from uplib.links import read_links_file
from uplib.createThumbnails import thumbnail_translation_and_scaling

URLPATTERN = re.compile(r'(^|\W)(?P<scheme>http|ftp|https)://(?P<host>[^/\s:]+)(:(?P<port>[0-9]+)){0,1}(?P<path>(/[-+~&$/\w,.?=%#]*[-+~$/\w?=%#])|\s*)')

SCHEME_GROUP = 1
HOST_GROUP = 2
PORT_GROUP = 3
PATH_GROUP = 5

CHARSET_PATTERN = re.compile(r"^Content-Type:\s*text/plain;\s*charset=([^)]*)\n", re.IGNORECASE)

# conversion from float to int via "int()" truncates, so define it as "trunc"
trunc = int


class LinksToHotspotsRipper (Ripper):

    def rip (self, location, doc_id):

        note(2, "  converting links in %s...", location)

        linksfile = os.path.join(location, "links", "document.links")
        if os.path.exists(linksfile):
            translation, scaling = thumbnail_translation_and_scaling(location)
            if translation is None or scaling is None:
                note(2, "    couldn't obtain translation or scaling for %s", location)
                return
            
            def scale_rect (left, top, width, height):
                left = trunc((left + translation[0]) * scaling[0] + 0.5)
                top = trunc((top + translation[1]) * scaling[1] + 0.5)
                width = trunc(width * scaling[0] + 0.5)
                height = trunc(height * scaling[1] + 0.5)
                return left, top, width, height

            links = read_links_file(linksfile)
            if not links:
                note(2, "    no links to convert in %s.", location)
                return

            hotspots_file_path = os.path.join(location, "hotspots.txt")
            hotspots_file = open(hotspots_file_path, "wb")

            try:
                for link in links:

                    from_page = link.get("from-page")
                    from_rect = link.get("from-rect")
                    to_uri = link.get("to-uri")
                    to_page = link.get("to-page")
                    if not from_rect or not from_page or (not to_uri and not to_page):
                        # no hotspot to convert
                        continue
                    if not to_uri and to_page:
                        to_uri = '#uplibpage=%d' % (int(to_page) - 1)
                        description = "turn to page %d" % int(to_page)
                    else:
                        description = to_uri
                    from_page = int(from_page) - 1
                    rect = [float(x) for x in from_rect.split(",")]
                    left, top, width, height = scale_rect(*rect)
                    h = Hotspot(doc_id, from_page, left, top, width, height, to_uri, description)
                    h.write(hotspots_file)
                    hotspots_file.flush()
                    
            finally:
                hotspots_file.close()
                

        else:
            note(2, "    no links to convert in %s.", location)



if __name__ == "__main__":
    r = URLtoHotspotRipper(None)
    r.rip(sys.argv[1], "foo")
