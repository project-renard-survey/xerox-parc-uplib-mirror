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

import sys, os, re

from plibUtil import note, configurator
from ripper import Ripper
from addDocument import CardDoc, URLDoc, mktempfile

if sys.platform == "darwin":

    from xattr import getxattr, listxattr

    class MacRipper(Ripper):

        def rip(self, folderpath, id):

            # create a resource fork with the document's first page on it
            try:
                bigfirstpageiconpath = os.path.join(folderpath, "page-images", "page00001.png")
                if os.path.exists(bigfirstpageiconpath):
                    os.system('/usr/bin/sips -i "%s" > /dev/null' % bigfirstpageiconpath)
                    if 'com.apple.ResourceFork' in listxattr(bigfirstpageiconpath):
                        icon = getxattr(bigfirstpageiconpath, 'com.apple.ResourceFork')
                        resourceforkpath = os.path.join(folderpath, "thumbnails", "mac-icon.rsrc")
                        fp = open(resourceforkpath, 'wb')
                        fp.write(icon)
                        fp.close()
            except Exception, x:
                note("MacRipper: exception %s encountered.", repr(x))

    class AppleTextClipping (CardDoc):

        def __init__(self, doc, options):
            CardDoc.__init__(self, doc, options)
            self.__tmpfile = options.get('tempfile')

        BEFORE = ('TextDoc',)

        def get_text_lines(self, path):
            return codecs.open(self.__tmpfile, 'rb', 'utf8', 'replace').readlines()

        def __del__(self):
            if self.__tmpfile and os.path.exists(self.__tmpfile):
                os.unlink(self.__tmpfile)

        def myformat (pathname):
            if (sys.platform == "darwin") and pathname.endswith(".textClipping"):
                try:
                    import MacOS
                    from Carbon import Res
                except:
                    note(3, "can't import MacOS or Res")
                    return False
                text = None
                try:
                    rf = Res.FSpOpenResFile(pathname, 0)
                except MacOS.Error, e:
                    if e.args[0] == -39:
                        # not a resource file
                        note(3, "file %s not a resource file", pathname)
                        return False
                    else:
                        raise
                else:
                    for i in range(1, Res.Count1Types() + 1):
                        typ = Res.Get1IndType(i)
                        for j in range(1, Res.Count1Resources(typ) + 1):
                            res = Res.Get1IndResource(typ, j)
                            id_, typ2, name = res.GetResInfo()
                            if typ == 'utf8':
                                text = unicode(res.data, 'utf8', 'replace')
                                break
                            if typ == 'TEXT':
                                text = unicode(res.data, 'macroman', 'replace')
                                break
                    Res.CloseResFile(rf)
                    if text:
                        tfile = mktempfile()
                        fp = codecs.open(tfile, "wb", "utf8", "replace")
                        fp.write(text)
                        fp.close()
                        return { 'tempfile' : tfile }
            return False
        myformat = staticmethod(myformat)


    class AppleWeblocDoc (URLDoc):

        def __init__(self, doc, options):
            URLDoc.__init__(self, doc, options)
            self.__options = options

        def process (self):
            title = self.__options.get("title")
            if title and not (self.__options.has_key("metadata") and self.__options["metadata"].has_key("title")):
                if self.__options.has_key("metadata"):
                    self.__options["metadata"].update({ "title": title })
                else:
                    self.__options["metadata"] = { "title": title }
            return URLDoc.process(self)

        def myformat (pathname):
            if pathname.endswith(".webloc"):
                try:
                    import MacOS
                    from Carbon import Res
                except:
                    note(3, "can't import MacOS or Res")
                    return False
                url = None
                title = None
                try:
                    rf = Res.FSpOpenResFile(pathname, 0)
                except MacOS.Error, e:
                    if e.args[0] == -39:
                        # not a resource file
                        note(3, "file %s not a resource file", pathname)
                        return False
                    else:
                        raise
                else:
                    for i in range(1, Res.Count1Types() + 1):
                        typ = Res.Get1IndType(i)
                        for j in range(1, Res.Count1Resources(typ) + 1):
                            res = Res.Get1IndResource(typ, j)
                            id_, typ2, name = res.GetResInfo()
                            if typ == 'url ':
                                url = res.data
                            if typ == 'urln':
                                title = res.data
                            if url and title: break
                    Res.CloseResFile(rf)
                if url:
                    result = URLDoc.myformat(url)
                    if type(result) == type({}):
                        result['real-url'] = url
                        if title:
                            result['title'] = title
                    return result
            return False
        myformat = staticmethod(myformat)





            
