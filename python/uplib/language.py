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
# Code to support language determination and handling
#

import os, sys, traceback

from uplib.plibUtil import note, configurator
from uplib.ripper import Ripper

############################################################
###
###  Language-guessing Ripper
###
############################################################

try:
    import guess_language
except:
    _have_guess_language = False
else:
    _have_guess_language = True

if _have_guess_language:

    def identify_language(text):
        return guess_language.guess_language.guessLanguageTag(text)

    class GuessLanguageRipper (Ripper):

        def __init__(self, repository):
            Ripper.__init__(self, repository)

        def provides(self):
            return "GuessLanguage"

        def rip (self, location, doc_id):

            textbytes, charset, language = self.get_folder_text_bytes(location)
            if textbytes and textbytes.strip():
                text = unicode(textbytes, charset, "replace")
                lang = guess_language.guess_language.guessLanguageTag(text)
                if lang:
                    if language != lang:
                        # re-write contents.txt with new language
                        fp = open(self.folder_text_path(location), "wb")
                        fp.write((u"Content-Type: text/plain;charset=%s\n" % charset).encode("ASCII", "strict"))
                        fp.write((u"Content-Language: %s\n" % lang).encode("ASCII", "strict"))
                        fp.write(textbytes)
                        fp.close()
                        note(3, "  re-wrote contents.txt language tag from '%s' to '%s' for %s",
                             language, lang, doc_id)
                    self.update_folder_metadata(location, { "text-language" : lang })
                    


