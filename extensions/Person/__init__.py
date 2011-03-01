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
This module provides a new kind of Collection, a Person.

The documents of a Person are those authored by the person.
In addition, the Person object contains pointers to PIM data about that
person, and a subcollection of references to that Person which occur in
other objects.  Person collections are persistent, and registered with
the repository.

Use the `help` function to get a page with help on using this module, or to
look up a particular person.
`list_people` will bring up the Person dossier application for the specified
people; `directory` will display the directory application of all names known in this
repository.

Inside the repository, use `find_person_by_name` to look up the Person
instance for a particular name.

:author: Bill Janssen
"""
__docformat__ = "restructuredtext"
__version__ = "$Revision: 1.17 $"


import sys, os, re, traceback, types, urllib, urllib2, xml.dom.minidom, socket
from bisect import bisect_left
from hashlib import md5
import uplib.plibUtil
from uplib.plibUtil import note, create_new_id, read_file_handling_charset_returning_bytes, configurator
from uplib.plibUtil import URLPATTERN, EMAILPATTERN, GEMAILPATTERN, MONTHABBREVS
from uplib.webutils import htmlescape, HTTPCodes, parse_URL
from uplib.collection import PrestoCollection
from uplib.document import Document
from uplib.basicPlugins import STANDARD_BACKGROUND_COLOR, STANDARD_DARK_COLOR, STANDARD_LEGEND_COLOR, STANDARD_TOOLS_COLOR, output_tools_block

# we stash a couple of indices in plibUtil so they won't be
# overwritten if we reload this module

# maps Unicode normal_form() name string to Person instances
note(4, "_NAME_TO_PERSON in uplib.plibUtil is %s", hasattr(uplib.plibUtil, "_NAME_TO_PERSON"))
if not hasattr(uplib.plibUtil, "_NAME_TO_PERSON"):
    setattr(uplib.plibUtil, "_NAME_TO_PERSON", {})
_NAME_TO_PERSON = getattr(uplib.plibUtil, "_NAME_TO_PERSON")
"""Contains a mapping of Unicode "normal form" name strings to Person instances."""

note(4, "%d listings in _NAME_TO_PERSON", len(_NAME_TO_PERSON))

# maps person ID to Person instances
if not hasattr(uplib.plibUtil, "_ID_TO_PERSON"):
    setattr(uplib.plibUtil, "_ID_TO_PERSON", {})
_ID_TO_PERSON = getattr(uplib.plibUtil, "_ID_TO_PERSON")
"""Contains a mapping of assigned Person IDs to Person instances."""

# Javascript code for display of a Person page
_PERSON_JAVASCRIPT = """
<script type="text/javascript" language="javascript" src="/html/javascripts/prototype.js"></script>
<script type="text/javascript" language="javascript" src="/action/Person/javascript"></script>
"""

_PERSON_CSS = """
<style type="text/css">

td {
    border: solid %(standard-border-color)s 1px;
    color: %(standard-text-color)s;
    background-color: %(standard-background-color)s;
    padding: 10px;
    }

td.photoblock {
    background-color: %(photo-background-color)s;
    }

td.aliasblock {
    background-color: %(alias-background-color)s;
    }

td.documentsblock {
    background-color: %(documents-background-color)s;
    }

td.pictureblock {
    background-color: %(pictures-background-color)s;
    }

td.toolsblock {
    background-color: %(tools-background-color)s;
    }

span.dateclass {
    color: %(legend-color)s;
    font-size: smaller;
    }

#PicturesSearchPanel {
    background-color: %(tools-background-color)s;
    color: %(standard-text-color)s;
    font-family: sans-serif;
    font-size: small;
    display: block;
    text-decoration: none;
    position: absolute;
    }

td.imagesearch {
    background-color: white;
    border: 0px;
    font-family: sans-serif;
    font-size: small;
    text-decoration: none;
    visible: visible;
    }

</style>
"""



def _add_name_for_person (namestring, person):

    global _NAME_TO_PERSON

    v = _NAME_TO_PERSON.get(namestring)
    if v:
        already_there = False
        for x in v:
            if isinstance(x, Person) and (x.id == person.id):
                already_there = True
            elif isinstance(x, dict) and (x.get('id') == person.id):
                already_there = True
        if not already_there:
            v.append(person)
    else:
        _NAME_TO_PERSON[namestring] = [person,]


def _remove_name_for_person (namestring, person):

    global _NAME_TO_PERSON

    v = _NAME_TO_PERSON.get(namestring)
    if v:
        for x in v[:]:
            if isinstance(x, Person) and (x.id == person.id):
                v.remove(x)
            elif isinstance(x, dict) and (x.get('id') == person.id):
                v.remove(x)


class Name:
    """
    Representation of a human name.
    """

    def _allcaps(obj):
        if type(obj) in types.StringTypes:
            return (len([x for x in obj if x.islower()]) == 0)
        elif type(obj) in (types.TupleType, types.ListType):
            return (len([x for x in obj if not _allcaps(x)]) == 0)
        else:
            return False
    _allcaps = staticmethod(_allcaps)

    def _isinitial(obj):
        return ((len(obj) == 2) and obj[0].isupper() and (obj[1] == '.'))
    _isinitial=staticmethod(_isinitial)

    PRE_HONORIFICS = ["King",
                      "Pope",
                      "President",
                      "Vice President",
                      "Speaker",
                      "Premier",
                      "Prime Minister",
                      "Chancellor",
                      "Mayor",
                      "Governor",
                      "Senator",
                      "Assemblyman",
                      "Representative",
                      "General",
                      "Admiral",
                      "Rear Admiral",
                      "Vice Admiral",
                      "Commodore",
                      "Commander",
                      "Lieutenant Commander",
                      "Colonel",
                      "Lieutenant Colonel",
                      "Major",
                      "Captain",
                      "Lieutenant",
                      "Lieutenant J.G.",
                      "Ensign",
                      "Sargeant",
                      "Corporal",
                      "Private"]
    """list of honorific strings that may occur before a name"""

    FIRSTNAMES_STOPLIST = ("cedar", "cornell", "programming", "general", "the", "if", "by", "are", "and")
    """list of words not to be considered as first names"""

    LASTNAMES_STOPLIST = (
        "associates",
        "association",
        "boulevard",
        "avenue",
        "association",
        "christmas",
        "inc",
        "university",
        "emergency",
        "rd",
        "st",
        "ave",
        "blvd",
        "area",
        "activity",
        "airport",
        "cathedral",
        "catholic",
        "courthouse",
        "activity",
        "artists",
        "synagogue",
        "corp",
        "department",
        "district",
        "county",
        "dr",
        "football",
        "fund",
        "foundation",
        "medical",
        "panthers",
        "cowboys",
        "packers",
        "steelers",
        "raceway",
        "rm",
        "sgt",
        "airport",
        "broncos",
        "wildcats",
        "tigers",
        "forty-niners",
        "giants",
        "bulldogs",
        "chargers",
        "coliseum",
        "convention",
        "development",
        "express-news",
        "fieldhouse",
        "heights",
        "highway",
        "hwy",
        "island",
        "causeway",
        "extension",
        "introduced",
        "incorporated",
        )
    """list of words not to be considered as last names"""

    NAMES_STOPLIST = (
        ".*\scatholic church$",
        ".*\sbaptist church$",
        "madison square garden",
        "elizabeth arden",
        "national guard",
        ".*general hospital$",
        "(.*\s)*international airport$",
        "major league",
        "urban league",
        "(.*\s)*new orleans$",
        "^new orleans\s.*",
        "state police",
        "lake pontchartrain",
        "baton rouge",
        ".*hyatt\s.*hotel$",
        ".*doubletree\s+hotel$",
        ".*hilton\s+hotel$",
        ".*plaza hotel$",
        ".*comfort inn$",
        ".*quinta inn$",
        ".*marco island",
        "(.*\s)*high school",
        "(.*\s)*middle school",
        "(.*\s)*grade school",
        "(.*\s)*junior high",
        "(.*\s)*medical school",
        "(.*\s)*law school",
        "homeland security",
        "red sox",
        "(.*\s)*state university$",
        "(.*\s)*state college$",
        "(.*\s)*community college$",
        "(.*\s)*yacht harbor$", 
        "louis armstrong\s.*",
        "ann arbor",
        "(.*\s)*school board",
        "(.*\s)*college board",
        ".*\sconvention center$",
        "royal dutch",
        "(.*\s)*, incorporated$",
        "(.*\s)*, inc\.$",
        )
    """list of regular expressions, matches for any of which invalidate a possible name string"""

    def __init__(self, str):
        """Given the string "str", try to figure it out as a name.

        :Parameters:
            str 
                a potential name
        """

        if not isinstance(str, unicode):
            str = unicode(str, "UTF-8", "strict")
        tokens = [x.strip() for x in re.split("[\s,]", str.strip()) if x.strip()]
        self.lastname = tokens[0]
        self.firstnames = tokens
        self.suffixes = None
        count = 1
        try:
            if (tokens[0].lower() == "pope") and (len(tokens) > 1):
                self.lastname = ''.join(tokens[1:])
                self.firstnames = tokens[0:1]
                self.suffixes = None
            else:
                while count < len(tokens):
                    token = tokens[-count]
                    if (not ((token.find('.') >= 0) or
                             (token == "") or
                             (not token[0].isupper()) or
                             (token == "I") or
                             (token == "II") or
                             (token == "III") or
                             (token == "IV") or
                             (token == "V") or
                             (token == "VI") or
                             (token == "VII") or
                             (token == "VIII") or
                             (token == "IX") or
                             (token == "X") or
                             (token == "Jr") or
                             (token == "MD") or
                             (token == "PhD"))):
                        break
                    count = count + 1
                self.lastname = tokens[-count]
                self.firstnames = tokens[:-count]
                if count > 1:
                    self.suffixes = tokens[-(count-1):]
                else:
                    self.suffixes = None
        except:
            note("for '%s', tokens are %s, count is %s:\n%s", str, tokens, count,
                 ''.join(traceback.format_exception(*sys.exc_info())))

    def __cmp__(self, other):
        return cmp(unicode(self), unicode(other))

    def __str__(self):
        return "%s, %s%s" % (self.lastname.encode('UTF-8', 'backslashreplace'),
                             ' '.join(self.firstnames).encode('UTF-8', 'backslashreplace'),
                              ((self.suffixes and (", " + " ".join(self.suffixes))) or "").encode('UTF-8', 'backslashreplace'))

    def __repr__(self):
        return "<%s %s %s>" % (self.__class__.__name__, repr(self.normal_form().encode('UTF-8', 'backslashreplace')), id(self))

    def __unicode__(self):
        try:
            return u"%s, %s%s" % (self.lastname, u' '.join(self.firstnames),
                                  (self.suffixes and (", " + " ".join(self.suffixes))) or "")
        except UnicodeDecodeError:
            note("%s, %s:\n%s", self.lastname, self.firstnames, ''.join(traceback.format_exception(*sys.exc_info())))
            raise


    def normal_form(self):
        """
        :return: standard representation of the Name
        :rtype: Unicode string
        """
        return u"%s %s%s" % (" ".join(self.firstnames),
                             self.lastname,
                             (self.suffixes and (", " + " ".join(self.suffixes))) or "")

    def reasonable(self):
        """
        :return: whether or not this Name instance seems reasonable.  Heavyweight.
        :rtype: boolean
        """
        if not self.firstnames:
            return False
        if (self.firstnames[0].lower() in self.FIRSTNAMES_STOPLIST):
            return False
        if self.lastname.lower() in self.LASTNAMES_STOPLIST:
            return False
        if self._allcaps(self.lastname):
            if not self.firstnames:
                # no first names, probably an acronym
                return False
            if not reduce(lambda oldv, newv: oldv and newv, [self._allcaps(x) for x in self.firstnames], True):
                return False
        if ((not self._allcaps(self.lastname)) and
            (len([x for x in self.firstnames if (self._allcaps(x) and not self._isinitial(x))]) > 0)):
            return False
        if self.lastname[-1] == '-':
            return False
        if (len(self.firstnames) == 1) and self._isinitial(self.firstnames[0]):
            return False
        if (self.lastname.lower() == "war" and (self.firstnames[-1].lower() in ("cold", "world"))):
            return False
        if not self.lastname[0].isupper():
            return False
        fullname = " ".join(self.firstnames + [self.lastname]).lower()
        if '\r' in fullname or '\n' in fullname or '@' in fullname:
            return False
        for pattern in self.NAMES_STOPLIST:
            if re.match(pattern, fullname):
                return False
        # note("%s is reasonable", self)
        return True


class StandardPerson (object):
    """
    Standardized representation of a person.
    """

    def __init__(self, repository, name, picture=None, id=None, vcards=None):

        global _ID_TO_PERSON

        if type(name) in types.StringTypes:
            name = Name(name)
        elif isinstance(name, Name):
            pass
        else:
            raise ValueError("value of name must be a string or an instance of Person.Name")
        self.name = name
        self.id = id or create_new_id()

        # set of Name instances for aliases
        self.aliases = []
        self.picture_id = (isinstance(picture, Document) and picture.id) or None
        self._authored = None
        self._referenced = None
        self._repository = repository
        self._pictures = None
        self._mentions = None
        self._metadata = {}
        self._notes = []
        # mention_regexp is a UTF-8-encoded pattern
        self.mention_regexp = None
        self._form_mentions_re()
        self._info = {}
        _add_name_for_person(self.name.normal_form(), self)
        if vcards is None:
            self._vcards = []
        else:
            self._vcards = vcards
        _ID_TO_PERSON[self.id] = self

    def add_metadata (self, n, v):
        """Adds the metadata specified with key "n" and value "v" to the persistent set of
        metadata about this instance.

        :param n: the name of the metadata field being added.
        :type n: string
        :param v: the metadata value being added, expressed as a string
        :type v: string
        """
        if (type(v) not in types.StringTypes) or (type(n) not in types.StringTypes):
            raise ValueError("metadata name/value pair elements must both be strings")
        if not isinstance(n, unicode):
            n = unicode(n, "UTF-8", "strict")
        if not isinstance(v, unicode):
            v = unicode(v, "UTF-8", "strict")
        l = self._metadata.get(n)
        if isinstance(l, list):
            l.append(v)
        else:
            self._metadata[n] = [v,]
            
    def remove_metadata (self, n, v):
        """If the metadata field with key "n" contains the value "v", removes it.

        :param n: the name of the metadata field being removed
        :type n: string
        :param v: the metadata value being removed, expressed as a string
        :type v: string
        """
        if (type(v) not in types.StringTypes) or (type(n) not in types.StringTypes):
            raise ValueError("metadata name/value pair elements must both be strings")
        if not isinstance(n, unicode):
            n = unicode(n, "UTF-8", "strict")
        if not isinstance(v, unicode):
            v = unicode(v, "UTF-8", "strict")
        l = self._metadata.get(n)
        if l:
            l.remove(v)

    def get_metadata(self, n=None):
        """Get the metadata for this instance.

        :param n: the name of the metadata field to retrieve.  Optional; if not specified, all metadata is returned, as a dict.
        :type n: string
        :return: either a list containing the values for a single metadata field, if "n" is specified, or a dict containing all metdata fields.
        :rtype: list or dict
        """
        if n is not None:
            if (type(n) not in types.StringTypes):
                raise ValueError("metadata names must be strings")
            if not isinstance(n, unicode):
                name = unicode(n, "UTF-8", "strict")
            return self._metadata.get(n)
        else:
            return self._metadata.copy()
            
    def add_email_address(self, email_addr):
        self.add_metadata("email", email_addr)

    def get_email_addresses(self):
        results = []
        s = self._metadata.get("email", [])
        for x in s:
            locs = _find_emails_in_string(x)
            for loc in locs:
                start, end = locs[loc]
                results.append((x, start, end))
        return results

    def get_data(self):
        """
        Get the persistent data for this instance.  Used for pickling this instance.

        :return: a set of name-value pairs containing the data of this instance.
        :rtype: dict
        """
        if self._pictures is not None:
            pics = (self._pictures.includes, self._pictures.excludes, )
        else:
            pics = None

        if self._authored is not None:
            auts = (self._authored.includes, self._authored.excludes, )
        else:
            auts = None

        if self._mentions is not None:
            ment = (self._mentions.includes, self._mentions.excludes, )
        else:
            ment = None

        return { "name": self.name.normal_form(),
                 "id": self.id,
                 "picture": self.picture_id,
                 "aliases": [x.normal_form() for x in self.aliases],
                 "pictures": pics,
                 "authored": auts,
                 "mentions": ment,
                 "info": self._info,
                 "vcards": [x.id for x in self._vcards],
                 "metadata": self._metadata,
                 "notes": self._notes,
                 }

    def set_data(self, data):
        """
        Given a pickle containing saved data for this instance, reset the
        data fields of the instance.

        :param data: a value retrieved from `#get_data`
        :type data: dict
        """
        global _NAME_TO_PERSON, _ID_TO_PERSON

        self.name = Name(data.get('name'))
        self.picture_id = data.get('picture')
        newid = data.get('id')
        if newid and (newid != self.id):
            if self.id in _ID_TO_PERSON:
                del _ID_TO_PERSON[self.id]
            self.id = newid
            _ID_TO_PERSON[self.id] = self
            note("updated id of %s to %s", self, newid)
        _add_name_for_person(self.name.normal_form(), self)
        aliases = [Name(x) for x in data.get('aliases')]
        for alias in aliases:
            self.add_alias(alias)
        info = data.get("info")
        if info:
            note("info is %s  %s", type(info), info)
            self._info.update(info)
        self._metadata = data.get('metadata') or {}
        vcards = data.get('vcards')
        for cardid in vcards:
            if self._repository.valid_doc_id(cardid):
                self._vcards.append(self._repository.get_document(cardid))
        p = data.get('pictures')
        if p:
            self._pictures = PrestoCollection(self._repository, None,
                                              query = self._form_pictured_query(),
                                              includes = p[0],
                                              excludes = p[1])
        p = data.get('authored')
        if p:
            self._authored = PrestoCollection(self._repository, None,
                                              query = self._form_authored_query(),
                                              includes = p[0],
                                              excludes = p[1])
        p = data.get('mentions')
        if p:
            self._mentions = PrestoCollection(self._repository, None,
                                              query = self._form_mentions_query(),
                                              includes = p[0],
                                              excludes = p[1])
        self._form_mentions_re()
        self._notes = data.get("notes") or []

    def get_picture (self):
        return (self.picture_id and
                self._repository.valid_doc_id(self.picture_id) and
                self._repository.get_document(self.picture_id)) or None

    def get_id(self):
        return self.id

    def add_note(self, t):
        self._notes.append(t)

    def notes(self):
        return self._notes[:]

    def add_vcard(self, doc):
        self._vcards.append(doc)

    def vcards(self):
        return self._vcards[:]

    def is_named(self, namestring):
        return (self.mention_regexp.match(namestring) != None)

    def _form_authored_query(self):
        query = 'authors:"' + self.name.normal_form() + '"'
        for alias in self.aliases:
            query += ' OR authors:"' + alias.normal_form() + '"'
        for addr, start, end in self.get_email_addresses():
            query += ' OR email-from-address:"' + addr + '"'
        return query

    def authored(self):
        if self._authored is None:
            self._authored = PrestoCollection(self._repository, None,
                                              self._form_authored_query())
        return self._authored.docs()

    def remove_authorship (self, doc_id):
        if self._authored is None:
            self._authored = PrestoCollection(self._repository, None,
                                              self._form_authored_query(),
                                              excludes=(doc_id,))
        else:
            self._authored.exclude_doc(self._repository.get_document(doc_id))

    def clear_authorship_excludes (self):
        if self._authored:
            includes = self._authored.includes
        else:
            includes = None
        self._authored = PrestoCollection(self._repository, None,
                                          self._form_authored_query(),
                                          includes=includes)

    def _form_mentions_query(self):
        query = 'contents:"' + self.name.normal_form() + '"' + ' OR contents:"' + unicode(self.name) + '"'
        query += 'title:"' + self.name.normal_form() + '"' + ' OR title:"' + unicode(self.name) + '"'
        for alias in self.aliases:
            query += ' OR contents:"' + alias.normal_form() + '"' + ' OR contents:"' + unicode(alias) + '"'
            query += ' OR title:"' + alias.normal_form() + '"' + ' OR title:"' + unicode(alias) + '"'
        for addr, start, end in self.get_email_addresses():
            query += ' OR contents:"' + addr + '"'
        return query

    def _form_mentions_re(self):

        def _add_form(s, name):
            if s:
                s += "|"
            addition = u"(" + name.normal_form() + u")|(" + unicode(name) + ")"
            addition = addition.replace(".", "\.")
            addition = re.sub('\s+', '\\s+', addition, re.DOTALL)
            return s + addition

        s = u""
        s = _add_form(u"", self.name)
        for alias in self.aliases:
            s = _add_form(s, alias)
        try:
            self.mention_regexp = re.compile(s.encode("UTF-8", "strict"), re.DOTALL | re.IGNORECASE)
        except:
            note(0, 'Invalid mention_regexp for "%s":  %s', self, s)

    def mentions(self):
        if self._mentions is None:
            self._mentions = PrestoCollection(self._repository, None,
                                              self._form_mentions_query())
        return self._mentions.docs()

    def remove_mention (self, doc_id):
        if self._mentions is None:
            self._mentions = PrestoCollection(self._repository, None,
                                              self._form_mentions_query(),
                                              excludes=(doc_id,))
        else:
            self._mentions.exclude_doc(self._repository.get_document(doc_id))

    def clear_mentions_excludes (self):
        if self._mentions:
            includes = self._mentions.includes
        else:
            includes = None
        self._mentions = PrestoCollection(self._repository, None,
                                          self._form_mentions_query(),
                                          includes=includes)

    def set_picture (self, doc):
        if isinstance(doc, Document):
            self.picture_id = doc.id
        elif doc is None:
            self.picture_id = None

    def _form_pictured_query(self):
        query = 'apparent-mime-type:image/*'
        query += ' AND -authors:"' + self.name.normal_form() + '"'
        for alias in self.aliases:
            query += ' AND -authors:"' + alias.normal_form() + '"'
        query += ' AND ((%s)' % self.name.normal_form()
        for alias in self.aliases:
            query += ' OR (' + alias.normal_form() + ')'
        query += ")"
        return query

    def pictured (self):
        if self._pictures is None:
            self._pictures = PrestoCollection(self._repository, None,
                                              self._form_pictured_query())
        return [d for d in self._pictures.docs() if (int(d.get_metadata("page-count") or d.get_metadata("pagecount") or 3) == 1)]

    def remove_picture (self, doc_id):
        if self._pictures is None:
            self._pictures = PrestoCollection(self._repository, None,
                                              self._form_pictured_query(),
                                              excludes=(doc_id,))
        else:
            self._pictures.exclude_doc(self._repository.get_document(doc_id))
        
    def clear_pictures_excludes (self):
        if self._pictures is not None:
            includes = self._pictures.includes
        else:
            includes = None
        self._pictures = PrestoCollection(self._repository, None,
                                          self._form_pictured_query(),
                                          includes=includes)


    def add_alias (self, alias):
        if alias == self.name:
            return
        if alias in self.aliases:
            return

        self.aliases.append(alias)
        _add_name_for_person(alias.normal_form(), self)

        # now fix up self.pictures and self.authored
        if self._pictures is not None:
            self._pictures.set_query(self._form_pictured_query())
        if self._authored is not None:
            self._authored.set_query(self._form_authored_query())
        self._form_mentions_re()
        if self._mentions is not None:
            self._mentions.set_query(self._form_mentions_query())

    def remove_alias (self, alias):
        if alias is self.name:
            return

        an_alias = False
        for x in self.aliases:
            if x == alias:
                self.aliases.remove(x)
                an_alias = True

        if an_alias:

            if alias != self.name:
                _remove_name_for_person(alias.normal_form(), self)

            # now fix up self.pictures and self.authored
            if self._pictures is not None:
                self._pictures.set_query(self._form_pictured_query())
            if self._authored is not None:
                self._authored.set_query(self._form_authored_query())
            self._form_mentions_re()
            if self._mentions is not None:
                self._mentions.set_query(self._form_mentions_query())

    def associated_domains(self):
        domains = []
        emails = self._metadata.get("email", [])
        for email in emails:
            locs = _find_emails_in_string(email)
            for start, end in locs.values():
                atsign = email.find('@', start, end)
                if atsign < 0:
                    continue
                domains.append(email[atsign+1:end])
        note("after emails, domains are %s", domains)
        urls = self._metadata.get("url", [])
        for url in urls:
            note("looking at url %s...", url)
            locs = _find_urls_in_string(url)
            note("locs for %s are %s", url, locs)
            for start, end in locs.values():
                host, port, path = parse_URL(url[start:end])
                note("host for %s[%s:%s] is %s", url, start, end, host)
                if host:
                    domains.append(host)
        note("after urls, domains are %s", domains)
        return domains

    def __repr__(self):
        return '<Person: %s; %s>' % (str(self.name), self.id)

    def __unicode__(self):
        return u'<Person: %s; %s>' % (unicode(self.name), self.id)

    def __cmp__(self, other):
        if isinstance(other, self.__class__):
            return cmp(self.name, other.name)
        elif isinstance(other, dict):
            return cmp(self.id, other.get('id'))
        else:
            return -1

    def people():
        k = list()
        for plist in _NAME_TO_PERSON.values():
            for person in plist:
                try:
                    if person not in k:
                        k.append(person)
                except:
                    note("exceptional person %s", repr(person))
        return k
    people = staticmethod(people)


# If we have the EntityFinder extension, I want to make sure that Person is
# also an Entity...

try:
    import EntityFinder as _EF
except ImportError:
    # maybe it's an extension
    try:
        note(4, "Person:  ImportError on 'EntityFinder', trying find_and_load_extension...")
        _EF = find_and_load_extension("EntityFinder")
    except:
        note(3, "Person:  Can't load EntityFinder, skipping Entity class incorporation")
        __have_entity = False
    else:
        __have_entity = (_EF is not None)
else:
    __have_entity = True

class Person(StandardPerson):
    """The class which represents a person in the repository"""
    pass

if __have_entity:
    # add the Entity class to the Person class...
    if not issubclass(Person, _EF.Entity):
        class Person (StandardPerson, _EF.Entity):
            """The class which represents a person in the repository.  A combination of
            `StandardPerson` and `EntityFinder.Entity`. """
            etype = "person"
            def text(self):
                return self.name.normal_form()

def find_person_by_name (repository, name):
    """
    Checks internal tables for `Person` instance with the given "name",
    and returns it if found.  If not found, returns empty list.

    :param name: name string
    :type name: Unicode string
    :return: a list of Person instances with that name
    :rtype: list(`Person`)    
    """
    global _NAME_TO_PERSON, _ID_TO_PERSON

    if not isinstance(name, unicode):
        name = unicode(name, 'UTF-8', 'strict')

    v = _ID_TO_PERSON.get(name)
    if (not v) or (not isinstance(v, Person)):
        v = _NAME_TO_PERSON.get(name)
    else:
        v = [v,]

    v2 = []
    reset = False
    if v:
        for x in v[:]:
            if isinstance(x, Person):
                v2.append(x)
            elif isinstance(x, dict):
                v.remove(x)
                p = Person(repository, name, id=x.get('id'))
                p.set_data(x)
                v2.append(p)
                reset = True
    if reset:
        _NAME_TO_PERSON[name] = v2
    return v2


def directory (repo, response, params):
    """
    :return: an HTML page showing all people known in this repository.
    :rtype: text/html
    """
    def _by_last_name_case_insensitve (n1, n2):
        return cmp(unicode(n1).lower(), unicode(n2).lower())

    compiled_regexp = None
    regexp = params.get('regexp')
    if regexp:
        try:
            compiled_regexp = re.compile(regexp)
        except:
            response.error(HTTPCodes.BAD_REQUEST, "Invalid regexp '%s' supplied." % regexp)
            return

    # get a sorted list of names
    names = [Name(n) for n in _NAME_TO_PERSON.keys() if ((compiled_regexp is None) or compiled_regexp.match(n))]
    names.sort(_by_last_name_case_insensitve)

    fp = response.open()
    page_title = "People in %s" % repo.name()
    fp.write('<head><title>People in %s</title>\n' % htmlescape(page_title))
    fp.write('</head><body bgcolor="%s">' % STANDARD_BACKGROUND_COLOR)
    output_tools_block(repo, fp, page_title, "Title DA", None, None, existing_query="", datekind=None)
    fp.write('<p><a href="#A">A</a>')
    for letter in range(25):
        character = chr(ord('A') + 1 + letter)
        fp.write(' &middot; <a href="#%s">%s</a>' % (character, character))
    for letter in range(26):
        character = chr(ord('A') + letter)
        lcharacter = character.lower()
        fp.write('<p><a name="%s"><H4>%s</H4></a><ul>\n' % (character, character))
        for name in names:
            if unicode(name).lower()[0] == lcharacter:
                fp.write('<li><a href="/action/Person/list_people?who=%s">%s</a></li>\n'
                         % (urllib.quote_plus(name.normal_form().encode('UTF-8', 'strict')), htmlescape(unicode(name))))
        fp.write("</ul>\n")
    fp.write('</body>\n')
    fp.close()


def _format_doc_date(d):
    if not d:
        return "no date"
    x = ""
    if d[1] != 0:
        x += MONTHABBREVS[d[1]-1] + " "
    x += str(d[0])
    return x

def _figure_span(tbytes, anchor_position, margin, charset):
    # figure out a "safe" breakpoint reasonably near (anchor_position + margin),
    # and decode the bytes from there to anchor_position according to charset,
    # returning a Unicode string
    if (margin < 0):
        # looking for a prologue
        while ((anchor_position + margin) > 0) and (not tbytes[anchor_position + margin].isspace()):
            margin -= 1
        # now trim off leading spaces
        while (tbytes[anchor_position + margin].isspace()):
            margin += 1
    elif (margin > 0):
        # looking for an epilogue
        while ((anchor_position + margin) < len(tbytes)) and (not tbytes[anchor_position + margin].isspace()):
            margin += 1;
    if ((anchor_position + margin) < 0):
        return unicode(tbytes[:anchor_position], charset, "strict")
    elif ((anchor_position + margin) > len(tbytes)):
        return unicode(tbytes[anchor_position:], charset, "strict")
    elif (margin < 0):
        return unicode(tbytes[anchor_position + margin:anchor_position], charset, "strict")
    else:
        return unicode(tbytes[anchor_position:anchor_position + margin], charset, "strict")

def _send_javascript(repo, response, params):
    response.return_file("text/javascript", os.path.join(os.path.dirname(__file__), "Person.js"))

def list_people (repo, response, params):
    """Brings up an AJAX application to edit or use the information about a specific person
    or persons.

    :param who: Optional.  Specifies a particular name to look for.  If omitted, all known people are included.
    :type who: string
    :param create: Optional.  Whether to create a "person" for the specified name if not there.  If not specified, defaults to ``False``.
    :type create: either not specified, or the string "true"
    :param excluded-document-categories: Optional.  If supplied, suppresses display of documents which are tagged with a category tag which matches the regular expression given.  The special value ``(standard)`` can be used to mean the value of the configuration parameter "excluded-categories".
    :type excluded-document-categories: string giving a Python regular expression
    :return: a list of people
    :rtype: text/html
    """
    from uplib.basicPlugins import __output_document_title as output_document_title
    from uplib.basicPlugins import __output_document_icon as output_document_icon
    from uplib.basicPlugins import __issue_title_styles as issue_title_styles
    from uplib.basicPlugins import __issue_javascript_head_boilerplate as issue_javascript_head_boilerplate
    from uplib.basicPlugins import __issue_menu_definition as issue_menu_definition
    setattr(uplib.basicPlugins, "WANTS_DOC_ICON_MENUS", True)
    setattr(uplib.basicPlugins, "USING_DOCVIEWER", True)

    who = params.get("who")
    create_if_necessary = (params.get("create") == "true")
    excluded_document_categories = params.get("excluded-document-categories")

    if (not who):
        if not create_if_necessary:
            # everyone
            l = list(Person.people())
            l.sort()
        else:
            response.error(HTTPCodes.BAD_REQUEST, "No name specified, but 'create' specified.")
            return
    elif type(who) in types.StringTypes:
        if not isinstance(who, unicode):
            who = unicode(who, 'UTF-8', 'backslashreplace')
        l = find_person_by_name(repo, who)
        if l:
            pass
        elif create_if_necessary:
            l = [Person(repo, who),]
        else:
            response.error(HTTPCodes.NOT_FOUND, "No person known by the name '%s'" % who)
            return
    else:
        who = [(isinstance(x, unicode) or unicode(x, "UTF-8", "backslashreplace")) for x in who]
        l = [x for x in [find_person_by_name(repo, y) for y in who] if x]
        if l:
            pass
        elif create_if_necessary:
            l = [Person(repo, who) for x in who]
        else:
            response.error(HTTPCodes.NOT_FOUND, "No people known by the names %s" % who)
            return

    fp = response.open()
    fp.write('<head><title>%s</title>\n' % htmlescape(u', '.join([person.name.normal_form() for person in l])))
    fp.write(_PERSON_JAVASCRIPT)
    fp.write(_PERSON_CSS % { 'standard-background-color': STANDARD_BACKGROUND_COLOR,
                             'standard-border-color' : STANDARD_DARK_COLOR,
                             'standard-text-color' : "black",
                             'alias-background-color' : STANDARD_BACKGROUND_COLOR,
                             'photo-background-color' : STANDARD_BACKGROUND_COLOR,
                             'documents-background-color': STANDARD_BACKGROUND_COLOR,
                             'pictures-background-color': STANDARD_BACKGROUND_COLOR,
                             'tools-background-color' : STANDARD_TOOLS_COLOR,
                             'legend-color' : STANDARD_DARK_COLOR,
                             })
    issue_title_styles(fp);
    issue_javascript_head_boilerplate (fp)
    fp.write('</head><body>')
    issue_menu_definition(fp)

    fp.write('<div id="PicturesSearchPanel"></div>\n')

    if excluded_document_categories == "(standard)":
        excl = configurator.default_configurator().get("excluded-categories")
        if excl:
            excl = re.compile(excl)
    elif excluded_document_categories:
        excl = re.compile(excl)
    else:
        excl = None

    first = True
    for person in l:

        if not first:
            fp.write('<hr>\n')
        else:
            first = False
        
        fp.write('<table width="100%" id=topleveltable>\n')
        fp.write('<tr><td width=100%><table width=100%>')

        fp.write('<tr><td class=nameblock><h3 class=name>%s</h3>' % htmlescape(person.name.normal_form()))
        emails = person.get_email_addresses()
        if emails:
            fp.write("<br><i>Email:</i><ul>\n")
            for full, start, end in emails:
                addr = full[start:end]
                fp.write('<li><tt>%s<a class=titlelink href="mailto:%s">%s</a>%s</tt></li>\n'
                         % (htmlescape(full[:start]), addr, htmlescape(addr), htmlescape(full[end:])))
            fp.write('</ul>')
        urls = person.get_metadata('url')
        if urls:
            fp.write("<br><i>Web sites:</i><ul>\n")
            for url in urls:
                locs = _find_urls_in_string(url)
                for key in locs:
                    start, end = locs[key]
                    addr = url[start:end]
                    fp.write('<li><tt>%s<a class=titlelink href="%s">%s</a>%s</tt></li>\n'
                             % (htmlescape(url[:start]), addr, htmlescape(addr), htmlescape(url[end:])))
            fp.write('</ul>')
        fp.write('</td>')
        # now output a picture, if any
        pic = person.get_picture()
        if pic:
            fp.write('<td class=photoblock><center>')
            output_document_icon(pic.id, pic.get_metadata('title') or pic.id, fp, sensible_browser=True)
            fp.write('<br><input type=button value="Remove picture" '
                         'onclick="javascript:remove_canonical_photo(\'%s\', true);">'
                         % (person.id,))
        else:
            fp.write('<td><center>(no picture)')
            fp.write('<br><input type=button value="Look for a picture on Yahoo!" '
                     'onclick="javascript:reveal_picture_search_panel(\'%s\');">' % person.id)

        fp.write('</center></td>')

        fp.write('</tr>')

        pics = person.pictured()
        authored = [x for x in person.authored() if ((not excl) or (not any([excl.match(cat) for cat in x.get_category_strings()])))]
        mentions = [x for x in person.mentions() if ((not excl) or (not any([excl.match(cat) for cat in x.get_category_strings()])))]
        notes = person.notes()[:]
        metadata = person.get_metadata().copy()
        if mentions:
            # first take out docs which have this person as an author
            for doc in authored:
                if doc in mentions:
                    mentions.remove(doc)

        fp.write('<tr><td colspan=2 class="toolsblock"><center>')
        if authored:
            fp.write(' &middot; <a href="#authored">Author of...</a>')
        if mentions:
            fp.write(' &middot; <a href="#mentions">Mentioned by...</a>')
        if pics:
            fp.write(' &middot; <a href="#pictures">Pictures of...</a>')
        fp.write(' &middot; <a href="#pictures">Notes on...</a>')
        fp.write(' &middot; <a href="#pictures">Metadata about...</a>')
        fp.write(' &middot; <a href="#controls">Controls</a>')
        fp.write('</center></td></tr>')
                 

        fp.write('<tr><td colspan=2 class=notesblock>')
        if notes:
            fp.write('<a name="notes"><i>Notes on this person:</i></a>\n')
            for n in notes:
                fp.write('<tt>%s</tt>\n' % htmlescape(n))
        else:
            fp.write('<a name="notes"><i>(No notes on this person)</i></a>\n')
        fp.write('<p><i>Add a note:</i> '
                 '<input type=button align=right value="Submit note" ' +
                 'onclick="javascript:add_note(\'%s\', \'addnotearea\', true);">' % person.id +
                 '<br>\n<textarea id="addnotearea" rows=5 cols=80></textarea>')
        fp.write('</td></tr>\n')

        # output a form for each doc
        if authored:

            # sort by date, most recent first
            def _by_date(d1, d2):
                return cmp(d2.get_date(), d1.get_date())
            authored.sort(_by_date)

            fp.write('<tr><td colspan=2 class=documentsblock><a name="authored"><i>Documents authored by this person:</i></a><ul>')
            for doc in authored:
                authors = doc.get_metadata("authors")
                if authors:
                    authors = [x.strip() for x in authors.split(' and ') if not person.is_named(x.encode("UTF-8", "strict"))]
                fp.write('<li>')
                output_document_title(doc.id, doc.name(), fp, sensible_browser=True)
                fp.write(' <span class="dateclass">(%s)</span>' % htmlescape(_format_doc_date(doc.get_date())))
                if authors:
                    fp.write('<br> <small>with')
                    first = True
                    for author in authors:
                        if not first:
                            fp.write(',')
                        else:
                            first = False
                        fp.write(' <a class=titlelink href="/action/Person/list_people?who=%s">%s</a>'
                                 % (urllib.quote_plus(author.encode("UTF-8", "strict")), htmlescape(author)))
                    fp.write("</small>")
                fp.write(' <input type=button value="Not an author" '
                         'onclick="javascript:remove_author(\'%s\', \'%s\', true);">'
                         % (doc.id, person.id))
                fp.write(' <span id="%s-emailbutton"><input type=button value="Look for email address" ' % doc.id +
                         'onclick="javascript:email_addresses(\'%s\', \'%s\', \'show\');"></span>'
                         % (doc.id, person.id))
                fp.write('<span id="%s-authoredemailaddresses"></span></li>\n' % doc.id)
            fp.write('</td></tr>')
        else:
            fp.write('<tr><td colspan=2 class=documentsblock><a name="authored">'
                     '<i>(no documents authored by this person)</i></td></tr>')

        # snippets
        if mentions:
            # sort by date, most recent first
            def _by_date(d1, d2):
                return cmp(d2.get_date(), d1.get_date())
            mentions.sort(_by_date)

            fp.write('<tr><td colspan=2 class=mentionsblock>'
                     '<a name="mentions"><i>Documents which may mention this person:</i></a><ul>')
            for doc in mentions:
                authors = doc.get_metadata("authors")
                if authors:
                    authors = [x.strip() for x in authors.split(' and ')]

                f, charset, language = read_file_handling_charset_returning_bytes(doc.text_path())
                tbytes = f.read()

                # TODO:  should check for UTF-8 charset, and recode if necessary

                fp.write('<li>')
                output_document_title(doc.id, doc.name(), fp, sensible_browser=True)
                fp.write(' <span class="dateclass">(%s)</span>' % htmlescape(_format_doc_date(doc.get_date())))
                if authors:
                    fp.write('<br> <small>by')
                    first = True
                    for author in authors:
                        if not first:
                            fp.write(', ')
                        else:
                            first = False
                        fp.write(' <a class=titlelink href="/action/Person/list_people?who=%s">%s</a>'
                                 % (urllib.quote_plus(author.encode("UTF-8", "strict")), author))
                    fp.write("</small>")
                fp.write(' <input type=button value="Not a reference" '
                         'onclick="javascript:remove_mention(\'%s\', \'%s\', true);">\n'
                         % (doc.id, person.id))
                pagination = None
                for mention in person.mention_regexp.finditer(tbytes):
                    if pagination is None:
                        pagination = []
                        for pagebreak in re.finditer('\n\f\n', tbytes, re.DOTALL | re.MULTILINE):
                            pagination.append(pagebreak.start())
                    pageno = bisect_left(pagination, mention.start())
                    prologue = _figure_span(tbytes, mention.start(), -40, charset)
                    epilogue = _figure_span(tbytes, mention.end(), 40, charset)
                    linktext = unicode(mention.group(), charset, "strict")
                    fp.write('<br><small>...%s<a class=titlelink href="%s"><b>%s</b></a>%s...</small>'
                             % (htmlescape(prologue),
                                "/action/basic/dv_show?doc_id=%s&page=%s&selection-start=%s&selection-end=%s"
                                % (doc.id, pageno, mention.start(), mention.end()),
                                htmlescape(linktext), htmlescape(epilogue)))
                fp.write("</li>\n")
            fp.write('</td></tr>')

        if pics:
            fp.write('<tr><td colspan=2 class=picturesblock>'
                     '<a name="pictures"><i>Pictures which may contain this person:</i></a>')
            for pic in pics:
                fp.write('<br>')
                output_document_icon(pic.id, pic.get_metadata('title') or pic.id, fp,
                                     sensible_browser=True)
                fp.write(' <input type=button value="Don\'t show this picture" '
                         'onclick="javascript:remove_photo(\'%s\', \'%s\', true);">'
                         % (pic.id, person.id))
                fp.write(' <input type=button value="Use this picture" '
                         'onclick="javascript:make_canonical_photo(\'%s\', \'%s\', true);">'
                         % (pic.id, person.id))
            fp.write('</td></tr>')

        fp.write('<tr><td class=aliasblock><a name="aliases"><i>Aliases:</i></a><ul>\n')
        if person.aliases:
            for alias in person.aliases:
                fp.write('<li>%s' % htmlescape(str(alias.normal_form())))
                fp.write(' <input type=button value="Remove alias" '
                         'onclick="javascript:remove_alias(\'%s\', \'%s\', true);">'
                         % (person.id, alias.normal_form()))
                fp.write(' <input type=button value="Use this as name for person" '
                         'onclick="javascript:use_alias_as_name(\'%s\', \'%s\', \'%s\');"></li>\n'
                         % (person.id, alias.normal_form(),
                            "/action/Person/list_people?who=" + person.id))
            fp.write('</ul>\n')
        fp.write('Add alias: <input type=text name="addalias" '
                 'onkeypress="javascript:add_alias(\'%s\', this, event, true);">' % person.id)

        fp.write('</td><td class=aliasblock><i>Possible aliases:</i><ul>')
        nf = [person.name.normal_form()]
        if person.name.firstnames:
            given_initial = [person.name.firstnames[0][0].lower()]
        else:
            given_initial = []
        for alias in person.aliases:
            nf.append(alias.normal_form())
            note("alias.firstnames for %s is %s", unicode(alias), alias.firstnames)
            if alias.firstnames:
                given_initial.append(alias.firstnames[0][0].lower())
        possibles = [x for x in _NAME_TO_PERSON.keys() if ((x not in nf) and
                                                          x.endswith(person.name.lastname) and
                                                          ((not given_initial) or (x.lower()[0] in given_initial)))]
        for p in possibles:
            fp.write('<li><a class=titlelink href="/action/basic/repo_search?query=%s" target="_blank">%s</a>'
                     % (urllib.quote_plus('authors:"%s"' % p), htmlescape(p)))
            fp.write(' <input type=button value="Add as alias" '
                         'onclick="javascript:add_alias_string(\'%s\', \'%s\', true);"></li>\n'
                         % (person.id, p))
        fp.write('</ul></td></tr>\n')

        fp.write('<tr><td colspan=2 class=metadatablock>'
                 '<a name="metadata"><i>Metadata about this person:</i></a><p>\n')
        for name, value in metadata.items():
            for v in value:
                fp.write('<br><i>%s:</i> <tt>%s</tt>'
                         % (htmlescape(name.encode("UTF-8", "strict")),
                            htmlescape(v.encode("UTF-8", "strict"))))
                fp.write(' <input type=button value="Remove value" '
                         'onclick="javascript:remove_metadata(\'%s\', \'%s\', \'%s\', true);">'
                         % (person.id, htmlescape(name), htmlescape(v)))
        fp.write('<p><i>Add value:</i><br>'
                 '<input type=text name="addmetadata" size=80 '
                 'onkeypress="javascript:add_metadata_from_widget(\'%s\', this, event, true);">' % person.id)
        fp.write('<br><font size="-2"><i>Just type something like "<tt>email: foo@example.com</tt>" and hit "Enter".</i></font>')
        
        fp.write('</td></tr>\n')

        fp.write('<tr><td colspan=2 class=toolsblock>'
                 '<a name="controls"> </a><input type=button value="Show excluded pictures" '
                 'onclick="javascript:show_excluded(\'%s\', \'pictures\');">'
                 % (person.id,) +
                 ' <input type=button value="Show excluded authored documents" '
                 'onclick="javascript:show_excluded(\'%s\', \'authorship\');">'
                 % (person.id,) +
                 ' <input type=button value="Look for a picture on Yahoo!" '
                 'onclick="javascript:reveal_picture_search_panel(\'%s\');">'
                 % (person.id,) +
                 '</td></tr>')

        fp.write('</table>\n')

    fp.close()

def help (repo, response, params):
    """Get help with this module.

    :return: a page with a form to look for people with, and a link to the "directory" function
    :rtype: text/html
    """
    data = ("""<head><title>Help on the Person module</title></head>
            <body bgcolor="%s"><h1>Help on the Person module</h1>""" % STANDARD_BACKGROUND_COLOR +
            """<p>The Person module supports management of information about people
            referred to in the repository.
            <p>Call <a href="/action/Person/directory">directory</a> for a listing of
            all the names in the repository.
            <hr>
            To obtain an "editor" for the information about a particular person,
            type that person's name here, and press the submit button.  Make sure you spell
            the name correctly, including proper capitalization of first and last names.<br>
            <form action="/action/Person/list_people">
            <input type=text name="who" value="" width=100%>
            <input type=submit value="Submit">
            <br>
            <input type=checkbox name="create" value="true">Check this box to "create" the person if they don't already exist
            <br>
            <input type=checkbox name="excluded-document-categories" value="(standard)" checked>Check this box to exclude listing of documents in "<tt>excluded-categories</tt>"
            </form>
            <hr>
            <a href="/html/doc/api/Person-module.html" target=_blank>(Click here to open the API documentation for the 'Person' module in another window.)</a>
            """)

    response.reply(data)

def get_people_in_document (repo, response, params):

    """Returns a list of the people known for this document, with links to click
    on to visit the editor for that person.  _This function can be used as a doc-function._

    :param doc_id: the document to look at
    :type doc_id: UpLib doc ID string
    :return: a list of links to the various people mentioned in the document, if any
    :rtype: text/html
    """

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No document specified.")
        return
    elif type(doc_id) not in types.StringTypes:
        response.error(HTTPCodes.BAD_REQUEST, "Too many doc_id parameters specified:  %s  Use only one." % str(doc_id))
        return
    elif not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id %s specified." % doc_id)
        return

    doc = repo.get_document(doc_id)
    people = []
    authors = doc.get_metadata("authors")
    if authors:
        authors = [x.strip() for x in authors.split(" and ") if x.strip()]
        for author in authors:
            p = find_person_by_name(repo, author)
            if p:
                for x in p:
                    if not x in people:
                        people.append(x)
            else:
                people.append(author)
    if __have_entity:
        entities = _EF.get_entities_as_patterns(doc)
        for entity in entities:
            if isinstance(entity, Person):
                people.append(entity)
            elif (entity.patternname == "person"):
                p = find_person_by_name(repo, entity.text())
                if p:
                    for x in p:
                        if not x in people:
                            people.append(x)
                else:
                    people.append(entity.text())

    fp = response.open()
    fp.write("<head><title>People found in %s</title></head>\n" % htmlescape(unicode(doc)))
    fp.write('<body bgcolor="%s"><h1>People found in %s</h1>' % (STANDARD_BACKGROUND_COLOR,
                                                                 htmlescape(unicode(doc))))
    fp.write('<ul>\n')
    for person in people:
        if type(person) in types.StringTypes:
            #potential person
            fp.write('<li><a href="/action/Person/list_people?who=%s&create=true">%s</a></li>' % (
                urllib.quote_plus(person), htmlescape(person)))
        elif isinstance(person, Person):
            name = person.name.normal_form()
            fp.write('<li><a href="/action/Person/list_people?who=%s&create=false">%s</a></li>' % (
                urllib.quote_plus(name), htmlescape(name)))
    fp.write("</ul></body>\n")
            


_YAHOO_WEB_SEARCH_URL = "http://search.yahooapis.com/WebSearchService/V1/webSearch"
_YAHOO_IMAGE_SEARCH_URL = "http://search.yahooapis.com/ImageSearchService/V1/imageSearch"
_YAHOO_APP_ID = "x8HLC0zV34EKjYNgp2JGtVAHsMFKACBWGFiWLYS0.7WvAYSVI61ac3nHKIgNXcqYRQ--"

def _fetch_result(url, params):

    socket.setdefaulttimeout(10)

    if params:
        querypart = urllib.urlencode(params)
        newurl = url + '?' + querypart
    else:
        newurl = url
    print newurl
    req = urllib2.Request(newurl)
    req.redirect_count = list((0,))
    req.redirect_allowed = True
    host = req.get_host()
    f = urllib2.urlopen(req)
    return f.info(), f.read()

def _doc_to_dict (docnode):
    result = {}
    for subnode in docnode.childNodes:
        if subnode.nodeName:
            if subnode.childNodes:
                if (subnode.nodeType == xml.dom.Node.ELEMENT_NODE) and (len(subnode.childNodes) > 1):
                    result[subnode.nodeName] = _doc_to_dict(subnode)
                elif (subnode.childNodes[0].nodeType == xml.dom.Node.TEXT_NODE):
                    result[subnode.nodeName] = subnode.childNodes[0].data
                else:
                    raise ValueError("Unexpected node %s with %d childnodes %s" %
                                     (subnode, len(subnode.childNodes), subnode.childNodes))
    return result            


def _look_for_pictures (repo, response, params):
    """
    Run a Yahoo! image search for the given person, using all the variants
    of their name (aliases), and any associated domains as clues.

    :param person: the person to search for
    :type person: the person ID, or a dict returned from `Person.get_data`.
    :param headless: whether to add an HTML 'head' section to the page.  If not specified, the 'head' section will be added.
    :type headless: any
    :return: an HTML page displaying search results
    :rtype: text/html
    """

    global _ID_TO_PERSON, _NAME_TO_PERSON

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if (not person):
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    elif isinstance(person, dict):
        d = person
        person = Person(repo, d.get("name"), id=d.get("id"))
        person.set_data(d)
    headless = params.get('headless')

    # put together a query for yahoo!
    query = '"%s" "%s"' % (person.name.normal_form(), unicode(person.name))
    for alias in person.aliases:
        query += ' "%s" "%s"' % (alias.normal_form(), unicode(alias))
    #note("query is %s", query)
    for domain in person.associated_domains():
        query += ' "%s"' % domain

    try:
        headers, result = _fetch_result(_YAHOO_IMAGE_SEARCH_URL,
                                        {'appid': _YAHOO_APP_ID,
                                         'query': query,
                                         'type': 'any',
                                         'results': '10',
                                         'adult_ok': '1',
                                         'output': 'xml'})
    except urllib2.HTTPError:
        response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "error received from Yahoo!")
        return

    # note("headers:\n%s\nresult:\n%s\n", headers, result)

    results = []
    ptree = xml.dom.minidom.parseString(result)
    for doc in [x for x in ptree.documentElement.childNodes if (x.hasChildNodes())]:
        d = _doc_to_dict(doc)
        # note("d is %s", d)
        if "Url" not in d:
            # ignore docs without URLs
            continue
        results.append(d)
    # note("results are %s", results)

    photo_category = configurator.default_configurator().get("person-photo-category") or ""

    fp = response.open()
    if not headless:
        fp.write('<head><title>Search results from Yahoo! for %s</title>\n'
                 % htmlescape(person.name.normal_form()))
        fp.write(PERSON_JAVASCRIPT)
        fp.write('</head><body>')
    fp.write('<h3>Search results from Yahoo! for %s</h3>\n'
             % htmlescape(person.name.normal_form()))
    if not results:
        fp.write('<p>No images found for query %s.' % htmlescape(query))
    for result in results:
        fp.write('<p><table width="100%%"><tr><td width="%s" class=imagesearch><img src="%s"></td>'
                 % (int(result.get("Thumbnail").get("Width")) + 10,
                    result.get("Thumbnail").get("Url")))
        fp.write('<td align="left" class=imagesearch>Size: %s<br>Format: %s<br>'
                 % (result.get("Width") + "x" + result.get("Height"),
                    result.get("FileFormat")))
        fp.write('Page: <a href="%s" target="_blank">%s</a> '
                 % (result.get("RefererUrl") or result.get("Url"),
                    htmlescape(result.get("RefererUrl") or result.get("Url"))))
        fp.write('  <input type=button value="(Add as a URL for %s)" '
                 % htmlescape(person.name.normal_form()) +
                 ' onclick="javascript:add_metadata(\'%s\', \'url\', \'%s\', false);"><br>\n'
                 % (person.id, urllib.quote(result.get("RefererUrl") or result.get("Url"))));
        spanid = md5(result.get("Url")).hexdigest()
        fp.write('<span id=%s-canon> <input type=button value="Add as THE picture of %s" '
                 % (spanid, htmlescape(person.name.normal_form())) +
                 'onclick="javascript:add_as_picture(\'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', true);"></span>'
                 % (person.id, htmlescape(person.name.normal_form()),
                    result.get("Url"), result.get("Thumbnail").get("Url"), htmlescape(photo_category), spanid + "-canon"))
        fp.write('<br><span id=%s-add> <input type=button value="Add as a picture, tagged with %s\'s name" '
                 % (spanid, htmlescape(person.name.normal_form())) +
                 'onclick="javascript:add_as_picture(\'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', false);"></span>'
                 % (person.id, htmlescape(person.name.normal_form()),
                    result.get("Url"), result.get("Thumbnail").get("Url"), htmlescape(photo_category), spanid + "-add"))    
        fp.write('</td></tr>\n')
        fp.write('<tr><td colspan=2 class=imagesearch>%s</td></tr></table>\n' % htmlescape(result.get("Summary") or "(no summary)"))
    fp.write('<tr><td colspan=2>Query was: <tt>%s</tt></td></tr>\n' % htmlescape(query))
    if not headless:
        fp.write('</body>\n')
    fp.close()
# we do this so that Medusa can find the method to call it, but to avoid documenting it as part of the API
globals()["look_for_pictures"] = _look_for_pictures

def add_alias(repo, response, params):

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    alias_name = params.get('alias')
    if not alias_name:
        response.error(HTTPCodes.BAD_REQUEST, "No alias specified.")
        return
    person.add_alias(Name(alias_name))
    response.reply("Alias added.")
    

def remove_alias(repo, response, params):

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    alias_name = params.get('alias')
    if not alias_name:
        response.error(HTTPCodes.BAD_REQUEST, "No alias specified.")
        return
    if not isinstance(alias_name, unicode):
        alias_name = unicode(alias_name, 'UTF-8', 'backslashreplace')
    person.remove_alias(Name(alias_name))
    response.reply("Alias removed.")
    

def use_alias_as_name (repo, response, params):

    global _ID_TO_PERSON

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    alias_name = params.get('alias')
    if not alias_name:
        response.error(HTTPCodes.BAD_REQUEST, "No alias specified.")
        return
    if not isinstance(alias_name, unicode):
        alias_name = unicode(alias_name, 'UTF-8', 'backslashreplace')
    oldname = person.name
    alias = Name(alias_name)
    person.remove_alias(alias)
    person.name = alias
    person.add_alias(oldname)
    response.reply("OK")
    

def add_note(repo, response, params):

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    note_data = params.get('note')
    if not note_data:
        response.error(HTTPCodes.BAD_REQUEST, "No note specified.")
        return
    person.add_note(note_data)
    response.reply("Note added.")
    

def add_metadata(repo, response, params):

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    n = params.get('name')
    if not n:
        response.error(HTTPCodes.BAD_REQUEST, "No name specified.")
        return
    v = params.get('value')
    if not v:
        response.error(HTTPCodes.BAD_REQUEST, "No value specified.")
        return
    note("n is %s (%s), v is %s (%s)", n, type(n), v, type(v))
    person.add_metadata(n, v)
    response.reply("metadata added.")
    

def remove_metadata(repo, response, params):

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    n = params.get('name')
    if not n:
        response.error(HTTPCodes.BAD_REQUEST, "No name specified.")
        return
    v = params.get('value')
    if not v:
        response.error(HTTPCodes.BAD_REQUEST, "No value specified.")
        return
    note("n is %s (%s), v is %s (%s)", n, type(n), v, type(v))
    person.remove_metadata(n, v)
    response.reply("metadata removed")
    

def remove_author(repo, response, params):

    global _ID_TO_PERSON

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No document specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid document specified.")
        return

    person.remove_authorship (doc_id);
    response.reply("Authorship removed.")
    

def remove_photo(repo, response, params):

    global _ID_TO_PERSON

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No photo specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid document specified.")
        return

    person.remove_picture (doc_id);
    response.reply("Photo removed.")
    

def make_canonical_photo (repo, response, params):

    global _ID_TO_PERSON

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No photo specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid document specified.")
        return

    person.set_picture (repo.get_document(doc_id));
    response.reply("Photo selected.")
    
def remove_canonical_photo (repo, response, params):

    global _ID_TO_PERSON

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return

    person.set_picture (None)
    response.reply("Photo selected.")
    

def add_email_address (repo, response, params):

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    addr = params.get('address')
    if not addr:
        response.error(HTTPCodes.BAD_REQUEST, "No address specified.")
        return
    person.add_email_address(addr)
    response.reply("address added")


def _find_urls_in_string (t):
    possibles = {}
    for p in URLPATTERN.finditer(t):
        addr = p.group('url').lower().encode('UTF-8', 'strict')
        if addr not in possibles:
            possibles[addr] = (p.start('url'), p.end('url'))
    return possibles

def _find_emails_in_string (t):
    possibles = {}
    for p in EMAILPATTERN.finditer(t):
        addr = p.group().lower().encode('UTF-8', 'strict')
        if addr not in possibles:
            possibles[addr] = (p.start(), p.end())
    for m in GEMAILPATTERN.finditer(t):
        start, end = m.start('group'), m.end('group')
        domain = m.group('domain')
        mailboxes = []
        current = []
        for i in range(start, end):
            if t[i].isspace() or t[i] == ',':
                if current:
                    mailboxes.append(t[current[0]:current[-1]+1])
                current = []
            elif not t[i].isspace():
                current.append(i)
        if current:
            mailboxes.append(t[current[0]:current[-1]+1])
        #note("domain is %s, mailboxes are %s", domain, mailboxes)
        for mailbox in mailboxes:
            possible = (mailbox + '@' + domain).lower().encode('UTF-8', 'strict')
            if possible not in possibles:
                possibles[possible] = (m.start(), m.end(),)
    return possibles

def look_for_email_address (repo, response, params):

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    doc_id = params.get('doc_id')
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No photo specified.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid document specified.")
        return

    doc = repo.get_document(doc_id)
    t = doc.text()
    possibles = _find_emails_in_string(t)

    if doc.get_metadata("apparent-mime-type") == "message/rfc822":
        # for email messages, look in original message, too
        if os.path.isdir(doc.originals_path()):
            for filename in os.listdir(doc.originals_path()):
                if not filename.startswith("."):
                    t = open(os.path.join(doc.originals_path(), filename), 'rb').read()
                    possibles.update(_find_emails_in_string(t))

    response.reply(htmlescape('\n'.join(possibles.keys())))
    

def show_excluded (repo, response, params):

    global _ID_TO_PERSON

    person_id = params.get('person')
    if not person_id:
        response.error(HTTPCodes.BAD_REQUEST, "No person ID specified.")
        return
    person = _ID_TO_PERSON.get(person_id)
    if not person:
        response.error(HTTPCodes.NOT_FOUND, "No person with ID %s." % person)
        return
    etype = params.get("etype")
        
    if etype == "pictures":
        person.clear_pictures_excludes()
    elif etype == "authorship":
        person.clear_authorship_excludes()
    else:
        response.error(HTTPCodes.BAD_REQUEST, "invalid etype '%s' specified." % etype)
        return
    response.reply("OK")
    

def scan_authors (repo, response, params):
    """
    Look through all the documents in the repository, and make sure that all the authors
    of all the documents are represented by Person instances.

    :return: redirects to `directory` after doing the scan
    :rtype: HTTP redirect
    """
    global _NAME_TO_PERSON
    for doc in repo.generate_docs():
        authors = doc.get_metadata('authors')
        if authors:
            authors = authors.split(' and ')
            for author in authors:
                if not (author.endswith(".com") or
                        author.endswith(".org") or
                        author.endswith(".edu") or
                        author.endswith(".net") or
                        author.endswith(".gov") or
                        author.endswith(".uk") or
                        author.endswith(".ru") or
                        author.endswith(".pdf")):
                    if not find_person_by_name(repo, author.strip()):
                        p = Person(repo, author.strip())
    response.redirect("/action/Person/directory")
        
def scan_person_entities (repo, response, params):

    global _NAME_TO_PERSON
    for doc in repo.generate_docs():
        doctext = None
        entities = doc.get_metadata('entities-found')
        if entities:
            entities = entities.split(';')
            for entity in entities:
                try:
                    if entity.startswith("person:"):
                        starting_position, length, page = map(int, entity[7:].split(","))
                        if doctext is None:
                            f, charset, language = read_file_handling_charset_returning_bytes(doc.text_path())
                            doctext = f.read()
                        person_name = unicode(doctext[starting_position:starting_position+length], charset)
                        if not find_person_by_name(repo, person_name.strip()):
                            p = Person(repo, person_name.strip())
                except:
                    note("exception processing name %s:\n%s", person_name,
                         ''.join(traceback.format_exception(*sys.exc_info())))
    response.redirect("/action/Person/directory")
        
def clear_people (repo, response, params):

    _NAME_TO_PERSON.clear()
    _ID_TO_PERSON.clear()
    response.redirect("/action/Person/directory")

def save_people (repo):

    try:

        saved = []

        people_store = os.path.join(repo.overhead_folder(), "people")

        note("saving people in %s", people_store)

        fp = open(people_store, 'wb')
        fp.write('{\n')

        try:

            # first, save instantiated Person instances
            for id, entry in _ID_TO_PERSON.items():
                try:
                    if id not in saved:
                        fp.write(u'\"%s\" : %s,\n'
                                 % (urllib.quote_plus(entry.name.normal_form().encode('UTF-8', 'ignore')),
                                    entry.get_data()))
                        saved.append(id)
                except:
                    note("save_people:  Can't save data for %s:\n%s", id,
                         ''.join(traceback.format_exception(*sys.exc_info())))

            # then, save dicts not already saved
            for name, v in _NAME_TO_PERSON.items():
                try:
                    for entry in v:
                        try:
                            if isinstance(entry, Person):
                                if entry.id not in saved:
                                    fp.write(u'\"%s\" : %s,\n' % (urllib.quote_plus(name.encode('UTF-8', 'ignore')), entry.get_data()))
                                    saved.append(entry.id)
                            elif isinstance(entry, dict) and entry.get('id'):
                                if entry.get('id') not in saved:
                                    fp.write(u'\"%s\" : %s,\n' % (urllib.quote_plus(name.encode('UTF-8', 'ignore')), entry))
                                    saved.append(entry.get('id'))
                            else:
                                raise ValueError("odd value %s found in entry for %s" % (entry, name))
                        except:
                            note("save_people:  Can't write record for %s:\n%s", entry,
                                 ''.join(traceback.format_exception(*sys.exc_info())))
                except:
                    note("save_people:  Can't save data for %s:\n%s", name,
                         ''.join(traceback.format_exception(*sys.exc_info())))

        finally:
            fp.write('}\n')
            fp.close()

    except:

        note(0, "in save_people:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))


def load_people (repo):

    global _NAME_TO_PERSON

    try:

        people_store = os.path.join(repo.overhead_folder(), "people")
        if os.path.exists(people_store):
            d = eval(open(people_store, 'rb').read())
            note("%d items in restored people", len(d.keys()))
            for name, v in d.items():
                name = unicode(urllib.unquote_plus(name), "UTF-8", 'strict')
                e = _NAME_TO_PERSON.get(name)
                if e:
                    if v not in e:
                        e.append(v)
                else:
                    _NAME_TO_PERSON[name] = [v,]
                    
    except:

        note(0, "in save_people:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))


def test_save(repo, response, params):

    save_people(repo)
    response.reply("saved")

def test_load(repo, response, params):

    global _NAME_TO_PERSON
    _NAME_TO_PERSON.clear()
    load_people(repo)
    fp = response.open("text/plain")
    keys = _NAME_TO_PERSON.keys()
    keys.sort()
    for key in keys:
        fp.write('%40s     %s\n' % (key, [type(x) for x in _NAME_TO_PERSON.get(key)]))
    fp.close()

def list_ids(repo, response, params):

    fp = response.open("text/plain")
    for id in _ID_TO_PERSON:
        fp.write('%40s     %s\n' % (id, _ID_TO_PERSON.get(id)["name"]))
    fp.close()


def after_repository_instantiation (repo):

    load_people(repo)

    repo.add_shutdown_hook(lambda x=repo: save_people(x))

# we do this to avoid documenting this interface
globals()["javascript"] = _send_javascript

# in case the extension is re-loaded...
_ID_TO_PERSON.clear()
for v in _NAME_TO_PERSON.values():
    for i in range(len(v)):
        if v[i] and (not isinstance(v[i], dict)):
            v[i] = v[i].get_data()
        if isinstance(v[i], Person):
            _ID_TO_PERSON[v[i]['id']] = v[i]

