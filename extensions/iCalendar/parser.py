# A document parser for iCalendar format
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
import hashlib
import shutil
import struct
import sys
import tempfile
import time
import traceback
import types
import urllib

from StringIO import StringIO

from email.utils import parseaddr

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch 
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from uplib.plibUtil import set_verbosity, true, false, subproc, MutexLock, read_metadata, id_to_time, figure_date_string, read_file_handling_charset, URLPATTERN, EMAILPATTERN, SECONDS_PER_WEEK, SECONDS_PER_DAY, note, configurator, format_date
from uplib.webutils import HTTPCodes, htmlescape
from uplib.addDocument import mktempfile, Error, CONTENT_TYPES, DocumentParser, mktempdir, FakePDFDoc, DocumentParser, update_configuration, ensure_assembly_line, calculate_originals_fingerprint
from uplib.newFolder import process_folder, flesh_out_folder
from uplib.ripper import Ripper

try:

    import vobject
    from dateutil import zoneinfo

except ImportError:

    note("can't import vobject, so no iCalendar parsing")

else:

    _CLOCKIMAGEFILEPATH = os.path.join(os.path.dirname(__file__), "clockimage.png")

    def _generate_filename(n):
        note("event.name is %s", n)
        n = n.encode("ASCII", "replace")
        return ''.join([((x.isalnum() and x) or '_') for x in n])

    class iCalendarEventParser (FakePDFDoc):

        _CLOCKIMAGE = None

        def __init__(self, identifier, options):
            note("processing event %s", identifier)
            self.pdffile = None
            self.__event = options.get("icsevent")
            FakePDFDoc.__init__(self, identifier, options)
            if not isinstance(self.__event, vobject.base.Component):
                note("self.__event is not a Component!  %s, %s", repr(self.__event), repr(type(self.__event)))
            if self.__event.behavior != vobject.icalendar.VEvent:
                note("self.__event.behavior is not a VEvent!  %s, %s", repr(self.__event.behavior), repr(type(self.__event.behavior)))
            assert(isinstance(self.__event, vobject.base.Component) and
                   (self.__event.behavior == vobject.icalendar.VEvent))
            self.checkocr = false
            self.__options = options.copy()
            self.__timestamp = None
            self.__uid = options.get("icsuid")
            self.__name = options.get("icsname")
            rev = self.__event.contents.get("REV") or []
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
            contents = self.__event.contents
            self.metadata["event-uid"] = self.__uid
            if self.__name != self.__uid:
                self.metadata["title"] = self.__name
            if self.__timestamp:
                self.metadata['revision-timestamp'] = time.strftime("%Y%m%dT%H%M%SZ", self.__timestamp)
            if 'dtstart' in contents:
                start = self.__event.dtstart.value
                self.metadata["date"] = "%d/%d/%s" % (start.month, start.day, start.year)
                self.metadata["event-start"] = start.isoformat()
                if 'dtend' in contents:
                    end = self.__event.dtend.value
                    duration = end - start
                    duration = (duration.days * SECONDS_PER_DAY) + duration.seconds
                    self.metadata['duration'] = str(duration)
                    self.metadata['event-end'] = end.isoformat()
            elif 'dtend' in contents:
                end = self.__event.dtend.value
                self.metadata["date"] = "%m/%d/%Y" % (end.month, end.day, end.year)
                self.metadata['event-end'] = end.isoformat()
            if 'location' in contents:
                self.metadata["location"] = re.sub("\s", " ", self.__event.location.value)
            if 'description' in contents:
                self.metadata["summary"] = re.sub("\s", " ", self.__event.description.value)

        format_mimetype = "text/calendar"

        def myformat(pathname):
            return (os.path.splitext(pathname)[1] == ".icsevent")
        myformat = staticmethod(myformat)

        def calculate_document_fingerprint(self):
            return self.metadata.get("sha-hash") or FakePDFDoc.calculate_document_fingerprint(self)

        def write_to_file (self, fp, boilerplate=True):
            if boilerplate:
                fp.write("BEGIN:VCALENDAR\r\n")
                fp.write("VERSION:2.0\r\n")
            fp.write(self.__event.serialize())
            if boilerplate:
                fp.write("END:VCALENDAR\r\n")

        def format_name (self, c, x, y, framesize): 
            """Draw the event's name"""
            if self.__name:
                # define a large font 
                c.setFont("Helvetica-Bold", 14) 
                # choose some colors 
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x, y, self.__name)
                return y - (0.5 * inch)
            else:
                return y

        def format_date_and_time(self, c, x, y, framesize):
            if 'date' in self.metadata:
                datestring = format_date(self.metadata["date"], True)
                if 'dtstart' in self.__event.contents:
                    datestring += " @ %s" % time.strftime("%I:%M %p", self.__event.dtstart.value.timetuple()).lstrip("0")
                    if 'dtend' in self.__event.contents:
                        datestring += " (till %s)" % time.strftime("%I:%M %p", self.__event.dtend.value.timetuple()).lstrip("0")
                c.setFont("Helvetica", 12) 
                # choose some colors 
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x, y, datestring)
                y -= (0.3 * inch)
            return y

        def format_location(self, c, x, y, framesize):
            if 'location' in self.__event.contents:
                location = self.__event.location.value.strip()
                c.setFont("Helvetica", 12) 
                # choose some colors 
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x, y, location)
                y -= (0.3 * inch)
            return y

        def format_description_1(self, c, x, y, framesize=None):
            if 'description' in self.__event.contents:
                dstring = self.__event.description.value
                c.setFont("Helvetica", 10) 
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x, y, dstring)
                y -= (0.3 * inch)
            return y

        def format_description(self, c, x, y, framesize):
            if 'description' in self.__event.contents:
                text = '<i>Description:</i> ' + htmlescape(self.__event.description.value.strip())
                text = text.replace('\n', '<br />')
                p = Paragraph(text, ParagraphStyle("normal"))
                w, h = p.wrapOn(c, *framesize)
                y -= h
                p.drawOn(c, x, y)
            return y

        def format_attendees(self, c, x, y, framesize):

            def do_attendee (attendee, annotation, c, x, y, framesize):
                link = attendee.value
                cn = attendee.params.get("CN")
                nameaddr = cn and cn[0]
                if nameaddr:
                    realname, emailaddr = parseaddr(nameaddr.replace(",", "%2C"))
                    if realname:
                        text = realname.replace("%2C", ",")
                    elif emailaddr:
                        text = emailaddr
                    else:
                        text = nameaddr
                elif link:
                    text = link                    
                text = htmlescape(text)
                if link:
                    text = '<link href="' + link + '">' + text + '</link>'
                if annotation:
                    text += ' <i>' + annotation + '</i>'
                p = Paragraph(text, ParagraphStyle("normal"))
                w, h = p.wrapOn(c, *framesize)
                y -= h
                p.drawOn(c, x, y)
                # y -= (0.1 * inch)
                return y

            if 'attendee' in self.__event.contents:
                for attendee in self.__event.contents.get('attendee'):
                    y = do_attendee(attendee, None, c, x, y, framesize)
            if 'organizer' in self.__event.contents:
                for organizer in self.__event.contents.get('organizer'):
                    y = do_attendee(organizer, "(o)", c, x, y, framesize)
            return y                    

        def format_event(self, outputfile, event):

            if (self._CLOCKIMAGE is None):
                from PIL import Image
                self._CLOCKIMAGE = im = Image.open(_CLOCKIMAGEFILEPATH)
                self._CLOCKIMAGE.load()
                note(3, "vcard _CLOCKIMAGE icon is %s", self._CLOCKIMAGE)

            # new 3x5 card
            c = canvas.Canvas(outputfile,
                              pagesize=(5 * inch, 3 * inch))
            border = .3 * inch
            x = 0 + border
            y = (3 * inch) - border
            width = (5 * inch) - (2 * border)
            iconsize = 0.5 * inch
            c.drawImage(ImageReader(self._CLOCKIMAGE),
                        (5 * inch - border - iconsize), (3 * inch - border - iconsize),
                        iconsize, iconsize)                        

            y = self.format_name(c, x, y, framesize=(width, y - border))
            y = self.format_date_and_time(c, x, y, framesize=(width, y - border))
            y = self.format_location(c, x, y, framesize=(width, y - border))
            y = self.format_description(c, x, y, framesize=(width, y - border))
            y = self.format_attendees(c, x, y, framesize=(width, y - border))
            c.save()

        def write_metadata(self):
            FakePDFDoc.write_metadata(self)

        def copy_original(self):

            # store as file

            filename = _generate_filename(self.__name) + ".ics"
            originals_path = self.originals_path()
            if not os.path.exists(originals_path):
                os.mkdir(originals_path)
                os.chmod(originals_path, 0700)
            fp = open(os.path.join(originals_path, filename), 'wb')
            self.write_to_file(fp, True)
            fp.close()
            os.chmod(os.path.join(originals_path, filename), 0700)

        def get_pdf_version(self):
            if not (self.pdffile and os.path.exists(self.pdffile)):
                tfile = mktempfile()
                self.format_event(tfile, self.__event)
                self.pdffile = tfile
            return self.pdffile


    class iCalendar (DocumentParser):

        INITIALIZED = False

        @classmethod
        def _initialize_windows_timezones(cls):

            def _windows_timezones (filename):
                """Returns mapping of Windows timezone names onto Olson names.

                This uses the Unicode Consortium's supplemental data file, available
                at <http://unicode.org/cldr/data/common/supplemental/supplementalData.xml>.

                @param filename the file to read
                @type filename a string filename path
                @return a mapping of Windows timezone names to Olson timezone names
                @rtype dict(string->string)
                """
                import xml.dom.minidom
                mapping = {}
                d = xml.dom.minidom.parse(filename)
                if d:
                    windows_sections = [x for x in d.getElementsByTagName("mapTimezones") if (
                        x.hasAttribute("type") and (x.getAttribute("type") == u"windows"))]
                    for section in windows_sections:
                        # probably only one section
                        for node in section.getElementsByTagName("mapZone"):
                            if (node.hasAttribute("other") and node.hasAttribute("type")):
                                mapping[node.getAttribute("other")] = node.getAttribute("type")
                return mapping

            filepath = os.path.join(os.path.dirname(__file__), "windows-timezones.xml")
            for key, tzname in _windows_timezones(filepath).items():
                tz = zoneinfo.gettz(tzname)
                if tz:
                    vobject.icalendar.registerTzid(key, tz)
                    note(5, "registered %s for '%s'", tz, key)
            cls.INITIALIZED = True

        def __init__(self, doc, options):
            DocumentParser.__init__(self, doc, options)
            self.checkocr = false
            self.__options = options.copy()
            self.__events = options.get("parsed-events")

        format_mimetype = "text/calendar"

        BEFORE = ("TextDoc", "CardDoc")

        def _name_event(e):
            if not hasattr(e, "uid"):
                # build one
                idstring = ""
                if hasattr(e, "summary"):
                    idstring += e.summary.value
                if hasattr(e, "dtstart"):
                    idstring += str(e.dtstart.value)
                if hasattr(e, "dtend"):
                    idstring += str(e.dtstart.value)
                if hasattr(e, "description"):
                    idstring += e.description.value
                uid = hashlib.sha1(idstring).hexdigest()
                e.uid = vobject.base.textLineToContentLine("UID:" + uid)
            else:
                uid = e.uid.value
            if hasattr(e, "summary"):
                summary = re.sub("\s", " ", e.summary.value)
            else:
                summary = ""
            name = summary or uid
            return (e, name, uid)
        _name_event = staticmethod(_name_event)

        def myformat(pathname):
            filename, ext = os.path.splitext(pathname)
            if ext not in (".ics", ".ifb"):
                return False
            if not iCalendar.INITIALIZED:
                iCalendar._initialize_windows_timezones()
            try:
                calendars = list(vobject.readComponents(open(pathname, "r")))
                events = []
                for calendar in calendars:
                    vevents = calendar.contents.get("vevent")
                    if vevents:
                        for event in vevents:
                            events.append(iCalendar._name_event(event))
            except:
                note('%s', ''.join(traceback.format_exception(*sys.exc_info())))
                return False
            note(3, "%d events in iCalendar file %s", len(events), pathname)
            return { "parsed-events" : events }
        myformat = staticmethod(myformat)

        def process (self):
            resultslist = list()
            for event, name, uid in self.__events:
                if event.name == "VEVENT":
                    newoptions = {}
                    newoptions.update(self.__options)
                    newoptions["icsevent"] = event
                    newoptions["icsuid"] = uid
                    newoptions["icsname"] = name
                    newoptions["format"] = "iCalendarEventParser"
                    if hasattr(event, "dtstart"):
                        identifier = "%s[%s @ %s]" % (self.doc, name, event.dtstart.value)
                    else:
                        identifier = "%s[%s]" % (self.doc, name)                    
                    result = DocumentParser.parse_document(identifier, resultslist, options=newoptions)
            note("iCalendar:  resultslist is %s", resultslist)
            return resultslist

    def _add_icalendar_file (repo, response, tfile):
        try:
            conf = configurator.default_configurator()
            update_configuration(conf)
            tal = ensure_assembly_line(conf.get("assembly-line"))
            try:
                parsed = iCalendar.myformat(tfile)
                if not isinstance(parsed, dict):
                    note(0, "Can't parse supposed iCalendar file %s", tfile)
                    response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Can't parse file")
                    return
                resp = response.open("text/plain")
                for event, name, uid in parsed.get('parsed-events'):
                    if hasattr(event, "dtstart"):
                        identifier = "%s @ %s" % (name, event.dtstart.value)
                    else:
                        identifier = name
                    # see if there's already a event for this name
                    query = 'apparent-mime-type:"%s" AND event-uid:"%s"' % (
                        iCalendarEventParser.format_mimetype, uid)
                    hits = repo.do_query(query)
                    if hits:
                        if 'metadata' not in parsed:
                            parsed['metadata'] = {}
                        parsed['metadata']['version-of'] = hits[0][1].id
                    if event.name == "VEVENT":
                        p = iCalendarEventParser(name,
                                                 {"icsname": name,
                                                  "icsuid": uid,
                                                  "icsevent": event,
                                                  "upload": False,
                                                  "usepng": True,
                                                  "metadata": parsed.get("metadata") or {},
                                                  })
                    else:
                        note(3, "No supported iCalendar subtype found in %s", identifier)
                        p = None
                    if p:
                        # calculate fingerprint
                        fd, filename = tempfile.mkstemp(".ics")
                        fp = os.fdopen(fd, "wb")
                        p.write_to_file(fp)
                        fp.close()
                        fingerprint = calculate_originals_fingerprint(filename)
                        # look up fingerprint in repo to see if we already have it
                        hits = repo.do_query('sha-hash:%s' % fingerprint)
                        if hits:
                            # already there, so skip this one
                            note(3, "skipping '%s', already in repo...", identifier)
                            resp.write("skipping '%s', already in repo\n" % identifier)
                            continue
                        # new event, so add it
                        p.metadata["sha-hash"] = fingerprint
                        pinst = p.process()
                        if isinstance(pinst, DocumentParser):
                            try:
                                folder = repo.create_document_folder(repo.pending_folder())
                                id = os.path.basename(folder)
                                # add the tfolder to the repository
                                process_folder(repo, id, pinst.folder, True)
                                flesh_out_folder(id, None, None, repo, None, None)
                                resp.write("added event for %s\n" % identifier)
                            except:
                                msg = "Exception processing event; event is\n%s\nException was\n%s\n" % (
                                    event, ''.join(traceback.format_exception(*sys.exc_info())))
                                note(0, msg)
                                resp.write(msg)
            finally:
                if tal:
                    from uplib.addDocument import AssemblyLine
                    shutil.rmtree(AssemblyLine)
                if os.path.exists(tfile):
                    os.unlink(tfile)
        except:
            msg = "Exception processing iCalendar:\n%s\n" % ''.join(traceback.format_exception(*sys.exc_info()))
            note(0, msg)
            response.error(HTTPCodes.INTERNAL_SERVER_ERROR, msg)

    def add_icalendar_file(repo, response, params):
        """
        Add the events in an iCalendar file.  Forks
        a new thread to add each event in the file which is not already in the set
        of events this repository knows about.

        :param events: the bits of the  file, not the path
        :type events: text/calendar (one or more)
        :returns: a text report on the success of the operation
        :rtype: text/plain
        """
        eventdata = params.get("events")
        if not eventdata:
            response.error(HTTPCodes.BAD_REQUEST, "No iCalendar data sent, no 'events' parameter")
            return
        fd, tfile = tempfile.mkstemp(".ics")
        fp = os.fdopen(fd, "wb")
        fp.write(eventdata)
        fp.close()
        response.fork_request(_add_icalendar_file, repo, response, tfile)

    # make sure the rest of the system knows about this...
    CONTENT_TYPES["text/calendar"] = "ics"
