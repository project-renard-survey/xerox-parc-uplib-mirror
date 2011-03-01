# A document parser for vCard format
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

import bisect
import cgi
import codecs
import os
import pickle
import quopri
import re
import shutil
import struct
import sys
import tempfile
import time
import traceback
import types
import urllib

from StringIO import StringIO

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch 
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph

from uplib.plibUtil import set_verbosity, true, false, subproc, MutexLock, read_metadata, id_to_time, figure_date_string, read_file_handling_charset, URLPATTERN, EMAILPATTERN, SECONDS_PER_WEEK, SECONDS_PER_DAY, note, configurator
from uplib.webutils import HTTPCodes, htmlescape
from uplib.addDocument import mktempfile, Error, CONTENT_TYPES, DocumentParser, mktempdir, FakePDFDoc, DocumentParser, update_configuration, ensure_assembly_line, calculate_originals_fingerprint
from uplib.newFolder import process_folder, flesh_out_folder
from uplib.ripper import Ripper

sys.path.append(os.path.dirname(__file__))

try:

    import vobject

except ImportError:

    note("can't import vobject, so no vCard parsing")

else:

    _CARDIMAGEFILEPATH = os.path.join(os.path.dirname(__file__), "vcardimage.png")

    def _generate_filename(card):
        data = card.contents
        note("card.contents is %s", data)
        if "fn" in data:
            n = card.fn.value
        elif "org" in data:
            n = ', '.join(card.org.value)
        elif "n" in data:
            n = card.n.value.strip()
            
        else:
            raise ValueError("Pointless vCard passed:  %s" % card.prettyPrint())
        n = n.encode("ASCII", "replace")
        return ''.join([((x.isalpha() and x) or '_') for x in n])

    class vCard (FakePDFDoc):

        _CARDIMAGEASPECT = None
        _CARDIMAGE = None

        def __init__(self, doc, options):
            note("processing card %s", doc.fn.value)
            note(4, "card data is %s", doc.prettyPrint())
            self.pdffile = None
            FakePDFDoc.__init__(self, doc, options)
            self.checkocr = false
            self.__options = options.copy()
            self.__card = doc
            self.__timestamp = None
            rev = doc.contents.get("REV") or []
            if rev:
                timestamps = []
                for x in rev:
                    # v is a timestamp
                    try:
                        timestamp = time.strptime(x.value, "%Y%m%dT%H%M%SZ")
                        timestamps.append(timestamp)
                    except:
                        try:
                            timestamp = time.strptime(x.value, "%Y%m%d")
                            timestamps.append(timestamp)
                        except:
                            pass
                timestamps.sort()
                self.__timestamp = timestamps[-1]
                    

        format_mimetype = "text/x-vcard"

        def myformat(pathname):
            return False
        myformat = staticmethod(myformat)

        def write_to_file (self, fp):
            fp.write(self.doc.serialize())

        def format_name (c, name, organization, x, y): 
            """Draw the person's name"""

            note("name is %s, organization is %s, x,y = %s,%s", name, organization, x, y)

            if name:
                text = name.value
                # define a large font 
                c.setFont("Helvetica-Bold", 14) 
                # choose some colors 
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x, y, text)
                if organization:
                    text = ", ".join(organization.value)
                    c.setFont("Helvetica", 12)
                    c.drawString(x + (0.5 * inch), y - (0.2 * inch), text)
            elif organization:
                text = organization.value
                # define a large font 
                c.setFont("Helvetica-Bold", 14) 
                # choose some colors 
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x, y, text)

        format_name=staticmethod(format_name)

        def format_phone (c, phone, x, y):
            """Draw the person's name"""

            if hasattr(phone, "params"):
                tp = phone.params.get("TYPE")
            text = phone.value

            note("phone is %s, tp is %s", text, tp and [q.lower() for q in tp])

            if text.isdigit():
                if len(text) == 10:
                    text = '(' + text[:3] + ') ' + text[3:6] + '-' + text[6:]
                elif len(text) == 7:
                    text = text[:3] + '-' + text[3:]

            label = "phone:  "
            labelFontName = "Helvetica-Oblique"
            labelFontSize = 12

            textFontName = "Courier-Bold"
            textFontSize = 12

            # choose some colors 
            c.setStrokeColorRGB(0, 0, 0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(labelFontName, labelFontSize)
            c.drawString(x, y, label)
            x += c.stringWidth(label, labelFontName, labelFontSize)
            c.setFont(textFontName, textFontSize)
            c.drawString(x, y, text)
            x += c.stringWidth(text + "  ", textFontName, textFontSize)
            if tp:
                c.setFont(labelFontName, labelFontSize)
                c.drawString(x, y, '(' + ' '.join([q.lower() for q in tp]) + ')')
        format_phone=staticmethod(format_phone)

        def format_email (c, email, x, y):
            """Draw the person's name"""

            if hasattr(email, "params"):
                tp = [q.lower() for q in email.params.get("TYPE") if (q.lower() not in (u"internet",))]
            else:
                tp = None
            text = email.value

            note('email is %s, tp is %s, x is %s, y is %s', text, tp, x, y)

            label = "email:  "
            labelFontName = "Helvetica-Oblique"
            labelFontSize = 12

            textFontName = "Courier-Bold"
            textFontSize = 12

            # choose some colors 
            c.setStrokeColorRGB(0, 0, 0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(labelFontName, labelFontSize)
            c.drawString(x, y, label)
            x += c.stringWidth(label, labelFontName, labelFontSize)
            c.setFont(textFontName, textFontSize)
            c.drawString(x, y, text)
            x += c.stringWidth(text + "  ", textFontName, textFontSize)
            if tp:
                c.setFont(labelFontName, labelFontSize)
                c.drawString(x, y, '(' + ' '.join(tp) + ')')
        format_email=staticmethod(format_email)

        def format_address (c, addr, x, y):

            type = addr.params.get('TYPE')
            if type:
                label = u' '.join([q.lower() for q in type if (q.lower() not in (u"pref",))]) + ' address:'
            else:
                label = 'address:'
            labelFontName = "Helvetica-Oblique"
            labelFontSize = 12

            textFontName = "Helvetica"
            textFontSize = 12

            c.setFont(labelFontName, labelFontSize)
            c.drawString(x, y, label)
            c.setFont(textFontName, textFontSize)

            y -= (0.2 * inch)
            x += (0.3 * inch)

            v = addr.value
            if hasattr(v, "street"):
                l = v.street
                c.drawString(x, y, l)
            city = hasattr(v, "city") and v.city
            state = hasattr(v, "region") and v.region
            zip = hasattr(v, "code") and v.code

            location = ''
            if state:
                location += state
            if zip:
                if location:
                    location += "  "
                location += zip
            if city:
                if location:
                    location = ", " + location
                location = city + location
            if location:
                y -= (0.2 * inch)
                c.drawString(x, y, location)
            return y
        format_address=staticmethod(format_address)

        def format_vcard(self, outputfile, vcard):

            if (self._CARDIMAGEASPECT is None) or (self._CARDIMAGE is None):
                from PIL import Image
                self._CARDIMAGE = im = Image.open(_CARDIMAGEFILEPATH)
                im.load()
                self._CARDIMAGEASPECT = float(im.size[0])/float(im.size[1])
                note(3, "vcard _CARDIMAGEASPECT icon is %s", self._CARDIMAGEASPECT)

            data = vcard.contents

            # new 3x5 card
            c = canvas.Canvas(outputfile,
                              pagesize=(5 * inch, 3 * inch))

            border = 0.3 * inch
            x = border
            y = (3 * inch) - (2 * border)

            iconwidth = 0.5 * inch
            iconheight = iconwidth / self._CARDIMAGEASPECT
            c.drawImage(ImageReader(self._CARDIMAGE),
                        (5 * inch - border - iconwidth), (3 * inch - border - iconheight),
                        iconwidth, iconheight)

            name = data.get("fn")
            if name:
                name = name[0]
            else:
                name = data.get("n")
                if name:
                    name = name[0]
            org = data.get("org")
            if org:
                org = org[0]
            self.format_name(c, name, org, x, y)
            y -= (0.5 * inch)
            for email in (data.get("email") or []):
                self.format_email(c, email, x, y)
                y -= (0.25 * inch)
            for phone in (data.get("tel") or []):
                self.format_phone(c, phone, x, y)
                y -= (0.25 * inch)
            for addr in (data.get("adr") or []):
                y = self.format_address (c, addr, x, y)
                y -= (0.25 * inch)
            c.save()

        def write_metadata(self):
            d = self.doc.contents
            if 'fn' in d:
                self.metadata['title'] = d['fn'][0].value + ' (contact info)'
            elif 'org' in d:
                self.metadata['title'] = ', '.join(d['org'][0].value) + ' (contact info)'
            if self.__timestamp:
                self.metadata['date'] = '%s/%s/%s' % (self.__timestamp[1],
                                                      self.__timestamp[2],
                                                      self.__timestamp[0])
                self.metadata['revision-timestamp'] = time.strftime("%Y%m%dT%H%M%SZ", self.__timestamp)
            FakePDFDoc.write_metadata(self)

        def copy_original(self):

            # store as file

            filename = _generate_filename(self.doc) + ".vcf"
            originals_path = self.originals_path()
            if not os.path.exists(originals_path):
                os.mkdir(originals_path)
                os.chmod(originals_path, 0700)
            fp = open(os.path.join(originals_path, filename), 'wb')
            fp.write(self.doc.serialize())
            fp.close()
            os.chmod(os.path.join(originals_path, filename), 0700)

        def get_pdf_version(self):
            if not (self.pdffile and os.path.exists(self.pdffile)):
                tfile = mktempfile()
                self.format_vcard(tfile, self.__card)
                self.pdffile = tfile
            return self.pdffile


    class vCards (DocumentParser):

        def __init__(self, doc, options):
            DocumentParser.__init__(self, doc, options)
            self.checkocr = false
            self.__options = options.copy()
            self.__cards = options.get("parsed-cards")

        format_mimetype = "text/x-vcard"

        BEFORE = ("TextDoc", "CardDoc")

        def myformat(pathname):
            filename, ext = os.path.splitext(pathname)
            if ext != ".vcf":
                return False
            try:
                cards = [card for card in vobject.readComponents(open(pathname, "r"))]
                # cards = parsefile(open(pathname, "r"))            # with bitpim parser
            except:
                return False
            note(3, "%d cards in vCard file %s", len(cards), pathname)
            return { "parsed-cards" : cards }
        myformat = staticmethod(myformat)

        def process (self):

            resultslist = list()
            for card in self.__cards:
                result = vCard(card, self.__options).process()
                fname = _generate_filename(card)
                identifier = "%s[%s]" % (self.doc, fname)
                resultslist.append((identifier, result))
            return resultslist

    def _add_vcards_file (repo, response, tfile):
        try:
            fp = response.open("text/plain")
            conf = configurator.default_configurator()
            update_configuration(conf)
            tal = ensure_assembly_line(conf.get("assembly-line"))
            cards = []
            try:
                parsed = vCards.myformat(tfile)
                parsed['upload'] = False
                parsed['usepng'] = True
                for card in parsed.get('parsed-cards'):
                    # see if there's already a card for this name
                    query = 'apparent-mime-type:"%s" AND vcard-name:"%s"' % (
                        vCard.format_mimetype, card.fn.value)
                    hits = repo.do_query(query)
                    if hits:
                        if 'metadata' not in parsed:
                            parsed['metadata'] = {}
                        parsed['metadata']['version-of'] = hits[0][1].id
                    p = vCard(card, parsed)
                    # calculate fingerprint
                    fd, filename = tempfile.mkstemp()
                    fp = os.fdopen(fd, "wb")
                    p.write_to_file(fp)
                    fp.close()
                    fingerprint = calculate_originals_fingerprint(filename)
                    # look up fingerprint in repo to see if we already have it
                    hits = repo.do_query('sha-hash:%s' % fingerprint)
                    if hits:
                        # already there, so skip this one
                        note(3, "skipping '%s', already in repo...", card.fn.value)
                        continue
                    # new card, so add it
                    pinst = p.process()
                    if isinstance(pinst, DocumentParser):
                        try:
                            folder = repo.create_document_folder(repo.pending_folder())
                            id = os.path.basename(folder)
                            note("using id %s for %s...", id, card.fn.value)
                            # add the tfolder to the repository
                            process_folder(repo, id, pinst.folder, True)
                            flesh_out_folder(id, None, None, repo, None, None)
                            note("added card for %s\n" % card.fn.value)
                            cards.append((id, card.fn.value))
                        except:
                            msg = "Exception processing vCard; vCard is\n%s\nException was\n%s\n" % (
                                card, ''.join(traceback.format_exception(*sys.exc_info())))
                            note(0, msg)
            finally:
                if tal:
                    from uplib.addDocument import AssemblyLine
                    shutil.rmtree(AssemblyLine)
                if os.path.exists(tfile):
                    os.unlink(tfile)
        except:
            msg = "Exception processing vcards:\n%s\n" % ''.join(traceback.format_exception(*sys.exc_info()))
            note(0, msg)
            response.error(HTTPCodes.INTERNAL_SERVER_ERROR, msg)
        else:
            response.reply('\n'.join(['%20s:  %s' % (x[0], x[1]) for x in cards]))

    def add_vcards_file(repo, response, params):
        """
        Add the cards in a vcards file.  Forks
        a new thread to add each card in the file which is not already in the set
        of vcards this repository knows about.

        :param cards: the bits of the vcards file, not the path
        :type cards: text/x-vcard
        :returns: a text report on the success of the operation
        :rtype: text/plain
        """
        carddata = params.get("cards")
        if not carddata:
            response.error(HTTPCodes.BAD_REQUEST, "No vCard data sent, no 'cards' parameter")
            return
        fd, tfile = tempfile.mkstemp(".vcf")
        fp = os.fdopen(fd, "wb")
        fp.write(carddata)
        fp.close()
        response.fork_request(_add_vcards_file, repo, response, tfile)

