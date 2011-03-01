# -*- Python -*-
#
# Code to support document indexing and search with JCC-Lucene
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

import sys, os, re, time, string, types, traceback, threading, struct, datetime

from uplib import plibUtil
from uplib.plibUtil import id_to_time, note, read_metadata, parse_date, read_file_handling_charset, configurator, uthread
if __name__ == "__main__":
    # for standalone testing
    uthread.initialize()
from uplib.plibUtil import THREADING, HAVE_PYLUCENE
if HAVE_PYLUCENE != "jcc":
    raise ImportError("THREADING is '%s', HAVE_PYLUCENE is '%s'", THREADING, HAVE_PYLUCENE)
from uplib.document import get_folder_notes
from uplib.paragraphs import read_paragraphs

try:
    from uplib.language import identify_language
except ImportError:
    identify_language = None

import lucene
from lucene import Document, Field, initVM, CLASSPATH, JavaError, VERSION
from lucene import PythonMultiFieldQueryParser, Field, MatchAllDocsQuery
from lucene import IndexReader, IndexSearcher, IndexWriter, StandardAnalyzer
from lucene import QueryParser, BooleanQuery, TermQuery, Term, BooleanClause
from lucene import MoreLikeThis, StringReader, SnowballAnalyzer, StopAnalyzer, Analyzer
from lucene import PythonSet, PythonIterator, String, File, FSDirectory

# try to handle both Lucene 2.x and 3.x
try:
    from lucene import TopDocs
except ImportError:
    from lucene import Hit
    _have_topdocs = False
else:
    _have_topdocs = True
try:
    from lucene import TermRangeQuery
except ImportError:
    from lucene import RangeQuery
    _have_trq = False
else:
    _have_trq = True

try:
    from lucene import Version
except ImportError:
    _indexversion = None
else:
    # we'd like to make this the latest Version that this Lucene knows
    # about, because that's what the index will be using, but for some
    # reason Version.LUCENE_CURRENT is deprecated!  So, this
    # complexity:
    def _order(v1, v2):
        if v1.equals(v2):
            return 0
        if v1.onOrAfter(v2):
            return 1
        else:
            return -1
    _values = sorted([getattr(Version, x) for x in Version.__dict__
                      if (x.startswith("LUCENE") and (x != "LUCENE_CURRENT"))],
                     cmp=_order)
    _indexversion = _values[-1]
    del _order, _values

_major_version = int(VERSION.split(".")[0])
if _major_version > 2:
    FIELD_TOKENIZED = Field.Index.ANALYZED
    FIELD_UNTOKENIZED = Field.Index.NOT_ANALYZED
else:
    FIELD_TOKENIZED = Field.Index.TOKENIZED
    FIELD_UNTOKENIZED = Field.Index.UN_TOKENIZED

PAGEBREAK = re.compile('\n\f\\r?\n')

_INITIALIZED = False

INDEXING_HOOKS = None

DEFAULT_LANGUAGE = "en"
_LANGUAGE_ANALYZERS = {}
_LANGUAGE_ANALYZER_CLASS_NAMES = (("el", "GreekAnalyzer"),
                                  ("zh", "CJKAnalyzer"),
                                  ("fa", "PersianAnalyzer"),
                                  ("fr", "FrenchAnalyzer"),
                                  ("th", "ThaiAnalyzer"),
                                  ("pt", "BrazilianAnalyzer"),
                                  ("nl", "DutchAnalyzer"),
                                  ("ru", "RussianAnalyzer"),
                                  ("ar", "ArabicAnalyzer"),
                                  ("de", "GermanAnalyzer"),
                                  ("ja", "CJKAnalyzer"),
                                  ("ko", "CJKAnalyzer"),
                                  ("en", "StandardAnalyzer"),
                                  )

SNOWBALL_ANALYZER_LANGUAGE_NAMES = {
    "it": "Italian",
    "fr": "French",
    "hu": "Hungarian",
    "ru": "Russian",
    "fi": "Finnish",
    "pt": "Portuguese",
    "da": "Danish",
    "tr": "Turkish",
    "nl": "Dutch",
    "sv": "Swedish",
    "de": "German",
    "en": "English",
    "ro": "Romanian",
    "no": "Norwegian",
    "es": "Spanish",
    }

class StringSet(PythonSet):

    # we need this till PyLucene grows it

    def __init__(self, _set):
        super(StringSet, self).__init__()
        self._set = set([x for x in _set])

    def add(self, obj):
        if obj not in self._set:
            self._set.add(obj.toString())
            return True
        return False

    def addAll(self, collection):
        size = len(self._set)
        self._set.update(collection)
        return len(self._set) > size

    def clear(self):
        self._set.clear()

    def contains(self, obj):
        v = obj.toString() in self._set
        # note("%s.contains(%s) => %s", self, repr(obj.toString()), v)
        return v

    def containsAll(self, collection):
        for obj in collection:
            if obj.toString() not in self._set:
                return False
        return True

    def equals(self, collection):
        if type(self) is type(collection):
            return self._set == collection._set
        return False

    def isEmpty(self):
        return len(self._set) == 0

    def iterator(self):
        class _iterator(PythonIterator):
            def __init__(_self):
                super(_iterator, _self).__init__()
                _self._iterator = iter(self._set)
            def hasNext(_self):
                if hasattr(_self, '_next'):
                    return True
                try:
                    _self._next = _self._iterator.next()
                    return True
                except StopIteration:
                    return False
            def next(_self):
                if hasattr(_self, '_next'):
                    next = _self._next
                    del _self._next
                else:
                    next = _self._iterator.next()
                return next
        return _iterator()

    def remove(self, obj):
        try:
            self._set.remove(obj.toString())
            return True
        except KeyError:
            return False

    def removeAll(self, collection):
        result = False
        for obj in collection:
            try:
                self._set.remove(obj.toString())
                result = True
            except KeyError:
                pass
        return result

    def retainAll(self, collection):
        result = False
        for obj in list(self._set):
            if obj.toString() not in c:
                self._set.remove(obj.toString())
                result = True
        return result

    def size(self):
        return len(self._set)

    def toArray(self):
        return list(self._set)


class HeaderField (object):

    STANDARD_HEADERS = "title:authors$\\sand\\s:source:date@:comment:abstract:notes:citation*:categories$,*:keywords$,*"
    HEADERS = {}

    def __init__(self, name, indexed_p, tokenized_p, stored_p, date_p, splitter=None):

        self.name = name
        self.indexed = indexed_p
        self.tokenized = tokenized_p
        self.stored = stored_p
        self.date = date_p
        self.splitter = splitter

    def get(name):
        return HeaderField.HEADERS.get(name)
    get=staticmethod(get)

    def parse_user_headers (userstring):
        headers = {}
        for part in userstring.split(":"):
            tokenized = True
            date = False
            splitter = None
            name = part
            if name[-1] == '*':
                # non-tokenized
                tokenized = False
                name = name[:-1]
            elif name[-1] == '@':
                # a date
                tokenized = False
                date = True
                name = name[:-1]
            p = name.rfind('$')
            if p >= 0:
                splitter = re.compile(name[p+1:])
                name = name[:p]
            headers[name] = HeaderField(name,
                                        True,
                                        tokenized,
                                        False,
                                        date,
                                        splitter)
        return headers
    parse_user_headers = staticmethod(parse_user_headers)

    def set_headers (userstring=None):
        map = HeaderField.parse_user_headers(HeaderField.STANDARD_HEADERS)
        if userstring:
            map.update(HeaderField.parse_user_headers(userstring))
        HeaderField.HEADERS = map
    set_headers = staticmethod(set_headers)
        
    def add_header(hfield):
        if HeaderField.HEADERS:
            HeaderField.HEADERS.update({ hfield.name: hfield })
            note(3, "added indexing field '%s': %s, %s, %s, %s, %s",
                 hfield.name,
                 hfield.indexed and "indexed" or "not indexec",
                 hfield.tokenized and "tokenized" or "not tokenized",
                 hfield.stored and "stored" or "not stored",
                 hfield.date and "a date" or "not a date",
                 hfield.splitter and ("splitter is %s" % repr(hfield.splitter)) or "no splitter")
    add_header = staticmethod(add_header)
            

DEFAULT_SEARCH_OPERATOR = None
DEFAULT_SEARCH_PROPERTIES = "contents:title:authors:comment:abstract:keywords*"
SEARCH_ABBREVIATIONS = None

class DocumentAnalyzer (object):

    "Extracts the indexable data from a document and returns an iteration \
    of org.apache.lucene.document.Document instances for indexing."

    def id_to_date (id):
        t = time.localtime(id_to_time(id))
        return '%04d%02d%02d' % (t.tm_year, t.tm_mon, t.tm_mday)
    id_to_date = staticmethod(id_to_date)

    def convert_date (d):
        pdate = parse_date(d)
        if pdate is None:
            return None
        return "%04d%02d%02d" % pdate
    convert_date = staticmethod(convert_date)

    def enumerate_categories (cseq):
        # Categories may be hierarchical, but we want to index under all combinations.
        # So we need to form that list of combinations.
        v = []
        for c in cseq:
            parts = c.lower().split('/')
            base = parts[0].strip()
            v.append(base)
            for part in parts[1:]:
                base = base + '/' + part
                v.append(base)
        return v
    enumerate_categories = staticmethod(enumerate_categories)

    def parse_metadata (metadata):
        lucene_metadata = []
        for key in metadata:
            itype = HeaderField.get(key)
            if itype:
                value = metadata[key]
                if not value:
                    note(3, "DocumentAnalyzer.parse_metadata: metadata key '%s' with False value %s",
                         key, value)
                    continue
                if itype.date:
                    value = DocumentAnalyzer.convert_date(value)
                    if value is None:
                        note("uplib.indexing.DocumentAnalyzer:  Date field '%s' has unparsable date value '%s'",
                             key, metadata[key])
                        continue
                if itype.splitter:
                    values = [x.strip() for x in itype.splitter.split(value)]
                elif isinstance(value, (list, set, tuple)):
                    values = value
                else:
                    values = (value,)
                if itype.name == 'categories':
                    values = DocumentAnalyzer.enumerate_categories(values)
                for value in values:
                    store = itype.stored and Field.Store.YES or Field.Store.NO
                    if not itype.indexed:
                        index = Field.Index.NO
                    elif not itype.tokenized:
                        index = FIELD_UNTOKENIZED
                    else:
                        index = FIELD_TOKENIZED
                    lucene_metadata.append(Field(key, value, store, index))
        # add a dummy field so we can identify un-categorized documents
        if 'categories' not in metadata:
            lucene_metadata.append(Field('categories', '_(none)_',
                                         Field.Store.YES, FIELD_UNTOKENIZED))
        # add a dummy category so we can select all documents
        lucene_metadata.append(Field('categories', '_(all)_',
                                     Field.Store.YES, FIELD_UNTOKENIZED))
        return lucene_metadata
    parse_metadata = staticmethod(parse_metadata)
            
    def read_text_annotations(apath):
        ann = get_folder_notes(apath)
        for page in ann:
            t = []
            notes = ann[page]
            for note in notes:
                if note[1]:
                    t.append(' '.join([x for x in note[1] if x]))
            ann[page] = '\n'.join(t)
        return ann
    read_text_annotations = staticmethod(read_text_annotations)

    def __init__(self, folder, docid):

        if not os.path.isdir(folder):
            raise ValueError("non-existent folder '%s' specified" % folder)
        self.id = docid
        self.id_date = self.id_to_date(docid)
        self.folder = folder
        metadata_path = os.path.join(folder, "metadata.txt")
        contents_path = os.path.join(folder, "contents.txt")
        annotations_path = os.path.join(folder, "annotations", "notes")
        if os.path.exists(metadata_path):
            metadata = read_metadata(os.path.join(folder, "metadata.txt"))
            self.metadata = self.parse_metadata(metadata)
            self.language = metadata.get("text-language") or "en"
        else:
            self.metadata = None
            self.language = "en"
        if os.path.exists(annotations_path):
            self.annotations = self.read_text_annotations(annotations_path)
        else:
            self.annotations = None
        paragraphs = read_paragraphs(folder)
        if paragraphs:
            pagetexts = {}
            lang = self.language
            for para in paragraphs:
                if identify_language:
                    lang = identify_language(para.text)
                if para.page in pagetexts:
                    pagetexts[para.page].append((lang, para.text))
                else:
                    pagetexts[para.page] = [(lang, para.text)]
            self.pagetexts = pagetexts
            self.charset = None
        elif os.path.exists(contents_path):
            text, charset, language = read_file_handling_charset(contents_path, True)
            pagetexts = PAGEBREAK.split(text)
            self.pagetexts = dict([(i, pagetexts[i]) for i in range(len(pagetexts))])
            self.charset = charset
            self.language = language
        else:
            self.pagetexts = {}
            self.charset = None

    def pagedoc(self, page_index):
        global INDEXING_HOOKS
        # build and return a Document containing one page
        doc = Document()
        doc.add(Field("id", self.id, Field.Store.YES, FIELD_UNTOKENIZED))
        doc.add(Field("pagenumber", str(page_index), Field.Store.YES, FIELD_UNTOKENIZED))
        doc.add(Field("uplibtype", "page", Field.Store.YES, FIELD_UNTOKENIZED))
        if self.annotations and self.annotations.has_key(page_index):
            doc.add(Field("notes", self.annotations[page_index], Field.Store.NO,
                          FIELD_TOKENIZED))
        if page_index in self.pagetexts:
            texts = self.pagetexts[page_index]
            if isinstance(texts, (str, unicode)):
                doc.add(Field("pagecontents", texts, Field.Store.NO, FIELD_TOKENIZED))
            elif isinstance(texts, (list, tuple)):
                for lang, text in texts:
                    doc.add(Field("pagecontents", text, Field.Store.NO, FIELD_TOKENIZED))
        if INDEXING_HOOKS:
            for hook in INDEXING_HOOKS:
                if hook and callable(hook):
                    for field in hook(self.id, self.folder, page_index):
                        doc.add(field)
        return doc
        
    def fulldoc(self):
        # build and return a Document containing one page
        doc = Document()
        doc.add(Field("id", self.id, Field.Store.YES, FIELD_UNTOKENIZED))
        doc.add(Field("uplibdate", self.id_date, Field.Store.YES, FIELD_UNTOKENIZED))
        doc.add(Field("uplibtype", "whole", Field.Store.YES, FIELD_UNTOKENIZED))
        if self.metadata:
            for field in self.metadata:
                doc.add(field)
        for pagetext in self.pagetexts.values():
            if isinstance(pagetext, (str, unicode)):
                doc.add(Field("contents", pagetext, Field.Store.NO, FIELD_TOKENIZED))
            elif isinstance(pagetext, (list, tuple)):
                for lang, text in pagetext:
                    doc.add(Field("contents", text, Field.Store.NO, FIELD_TOKENIZED))
        if self.annotations:
            for key in self.annotations:
                doc.add(Field("notes", self.annotations[key], Field.Store.NO,
                              FIELD_TOKENIZED))
        if INDEXING_HOOKS:
            for hook in INDEXING_HOOKS:
                if hook and callable(hook):
                    for field in hook(self.id, self.folder, -1):
                        doc.add(field)
        return doc
        
    def __iter__(self):
        return self.produce_versions()

    def doc_language (self):
        return self.language

    def produce_versions (self):
        for i in range(len(self.pagetexts)):
            note(3, "page %d", i)
            yield self.pagedoc(i)
        note(3, "full version")
        yield self.fulldoc()
        note(3, "indexing:  done with %s", self.id)
        raise StopIteration
        
# parser classes for the search interface

class RequiresQueryLanguage (Exception):

    _EXCEPTION_PATTERN = re.compile(r"RequiresQueryLanguage: Query specifies language '(?P<language>[a-z]+)'")

    def __init__(self, msg):
        Exception.__init__(self, "Query specifies language '%s'" % msg)
        self.language = msg
    def get_language(cls, exception):
        m = cls._EXCEPTION_PATTERN.search(exception.toString())
        if m:
            return m.group("language")
        return None
    get_language=classmethod(get_language)

def _check_analyzer (a, lang):
    # check to see if analyzer a is the correct way to handle language lang
    if isinstance(a, lucene.SnowballAnalyzer):
        # do snowball check
        raise Error("Can't do language-specific queries if Snowball stemming is enabled.")
    elif isinstance(a, lucene.Analyzer):
        reqclass = _LANGUAGE_ANALYZERS.get(lang) or StandardAnalyzer
        #note("reqclass for '%s' is %s, a is %s, subclass match is %s", lang, reqclass, a, reqclass.instance_(a))
        return reqclass.instance_(a)

class UpLibQueryParser (PythonMultiFieldQueryParser):

    def __init__(self, fields, analyzer, abbrevs):
        self.fields = fields
        self.abbrevs = abbrevs
        if _major_version < 3:
            PythonMultiFieldQueryParser.__init__(self, fields.keys(), analyzer)
        else:
            PythonMultiFieldQueryParser.__init__(self, _indexversion, fields.keys(), analyzer)

    def convertDate(date):
        if date.lower() == "today":
            d = datetime.date.today()
            year, month, day = d.year, d.month, d.day
        elif date.lower() == "yesterday":
            oneday = datetime.timedelta(days=1)
            d = datetime.date.today() - oneday
            year, month, day = d.year, d.month, d.day
        elif date.lower() == "now":
            d = datetime.date.today()
            year, month, day = d.year, d.month, d.day
        else:
            year, month, day = parse_date(date)
        return "%04d%02d%02d" % (year, month, day)
    convertDate=staticmethod(convertDate)

    def convertDateRange(date):
        d = datetime.date.today()
        todate = "%04d%02d%02d" % (d.year, d.month, d.day)
        if date.lower() == "pastweek":
            d = datetime.date.today() - datetime.timedelta(days=7)
            fromdate = "%04d%02d%02d" % (d.year, d.month, d.day)
        elif date.lower() == "pastmonth":
            d = datetime.date.today() - datetime.timedelta(days=30)
            fromdate = "%04d%02d%02d" % (d.year, d.month, d.day)
        elif date.lower() == "pastyear":
            d = datetime.date.today() - datetime.timedelta(days=365)
            fromdate = "%04d%02d%02d" % (d.year, d.month, d.day)
        return fromdate, todate
    convertDateRange=staticmethod(convertDateRange)

    def parseQ (self, querystring):
        note(4, "%s.parse(%s)...", self.__class__.__name__, repr(querystring))
        query = QueryParser.parse(self, querystring)
        note(4, "... => %s ...", query)
        if BooleanQuery.instance_(query) and (len(BooleanQuery.cast_(query).getClauses()) > 0):
            all_negative = True
            all_positive = True
            for clause in BooleanQuery.cast_(query).getClauses():
                if not clause.isProhibited():
                    all_negative = False
                q = clause.getQuery()
                if not isinstance(q, MatchAllDocsQuery):
                    all_positive = False                    
            if all_negative:
                q2 = MatchAllDocsQuery()
                BooleanQuery.cast_(query).add(q2, BooleanClause.Occur.SHOULD)
            elif all_positive:
                query = BooleanQuery()
        elif MatchAllDocsQuery.instance_(query):
            query = BooleanQuery()
        note(4, "... => %s", query)
        if BooleanQuery.instance_(query) and (len(BooleanQuery.cast_(query).getClauses()) == 0):
            return None
        else:
            return query

    def fieldNames(self):
        return self.fields.keys()

    def isTokenizedField(self, fname):
        v = HeaderField.get(fname)
        # true if not explicitly non-tokenized
        return (not v) or v.tokenized

    def isDateField(self, fname):
        v = self.fields.get(fname)
        # true only if explicitly specified as a date field
        return v and v.date

    def addClause(clauses, conjunction, mods, query):
        QueryParser.addClause(self, clauses, conjunction, mods, query)

    def getFieldQuery(self, fieldname, text, slop=None):
        orig = None
        if fieldname:
            if fieldname[0] == '$' and fieldname[1:] in self.abbrevs:
                #note(3, "  processing abbrev field %s", fieldname)
                return self.getFieldQuery(self.abbrevs[fieldname[1:]], text, slop)
            if fieldname == "categories":
                #note(3, "  processing categories field")
                orig = TermQuery(Term(fieldname, string.join([x.strip() for x in text.lower().split('/')], '/')))
            elif ((fieldname in ("date", "uplibdate")) or self.isDateField(fieldname)) and (('/' in text) or (text.lower() in ("today", "yesterday", "now"))):
                #note(3, "  processing date field %s", fieldname)
                orig = TermQuery(Term(fieldname, self.convertDate(text)))
            elif ((fieldname in ("date", "uplibdate")) or self.isDateField(fieldname)) and (text.lower() in ("pastweek", "pastmonth", "pastyear")):
                #note(3, "  processing date field %s:%s", fieldname, text)
                fromdate, todate = self.convertDateRange(text)
                if _have_trq:
                    orig = TermRangeQuery(fieldname, fromdate, todate, True, True)
                else:
                    orig = RangeQuery(Term(fieldname, fromdate), Term(fieldname, todate), True)
            elif (fieldname == "keywords") or (not self.isTokenizedField(fieldname)):
                #note(3, "  processing keyword or non-tokenized field %s", fieldname)
                orig = TermQuery(Term(fieldname, text))
            elif (fieldname == "_query_language"):
                if not _check_analyzer(self.getAnalyzer(), text):
                    raise RequiresQueryLanguage(text)
                else:
                    # we want to remove it if the condition is satisfied
                    return None
        else:
            if text[0] == '$' and text[1:] in self.abbrevs:
                # make a new instance to avoid re-initialization problems
                #note(3, "%s: expanding abbrev '%s' to '%s'", self, text, self.abbrevs[text[1:]])
                if isinstance(self, UpLibPageSearchQueryParser):
                    newparser = UpLibPageSearchQueryParser(self.getAnalyzer(), self.abbrevs)
                elif isinstance(self, UpLibQueryParser):
                    newparser = UpLibQueryParser(self.fields, self.getAnalyzer(), self.abbrevs)
                else:
                    raise ValueError(self)
                return newparser.parseQ(self.abbrevs[text[1:]])
        if not orig:
            if slop is None:
                orig = super(UpLibQueryParser, self).getFieldQuery(fieldname, text)
            else:
                orig = super(UpLibQueryParser, self).getFieldQuery(fieldname, text, slop)
            #note(3, "super.getFieldQuery(%s, %s, %s) => %s" % (fieldname, text, slop, orig))
        #note(3, "getFieldQuery(%s, %s) => %s", fieldname, repr(text), orig)
        return orig

    def getRangeQuery(self, fieldname, part1, part2, inclusive):
        if fieldname and ((fieldname in ("date", "uplibdate")) or self.isDateField(fieldname)):
            if ('/' in part1) or (part1.lower() in ("today", "yesterday", "now")):
                part1 = self.convertDate(part1)
            if ('/' in part2) or (part2.lower() in ("today", "yesterday", "now")):
                part2 = self.convertDate(part2)
            if _have_trq:
                return TermRangeQuery(fieldname, part1, part2, inclusive, inclusive)
            else:
                return RangeQuery(Term(fieldname, part1), Term(fieldname, part2), inclusive)
        else:
            return super(UpLibQueryParser, self).getRangeQuery(fieldname, part1, part2, inclusive)


class UpLibPageSearchQueryParser (UpLibQueryParser):

    __STANDARDFIELDS = HeaderField.parse_user_headers("pagecontents:notes:_query_language")

    def __init__(self, analyzer, abbrevs):
        UpLibQueryParser.__init__(self, self.__STANDARDFIELDS, analyzer, abbrevs)

    def getFieldQuery(self, fieldName, text, slop=None):
        #note("UpLibPageSearchQueryParser.getFieldQuery(%s, %s, %s)", fieldName, text, slop)
        if (not fieldName) or (fieldName in self.__STANDARDFIELDS):
            # no particular field, so run it
            if slop is None:
                q = super(UpLibPageSearchQueryParser, self).getFieldQuery(fieldName, text)
            else:
                q = super(UpLibPageSearchQueryParser, self).getFieldQuery(fieldName, text, slop)
        else:
            q = None
        #note("... => %s", q)
        return q

    def getFuzzyQuery(self, fieldName, termText, minSimilarity=None):
        if (not fieldName) or (fieldName in self.__STANDARDFIELDS):
            # no particular field, so run it
            if minSimilarity is None:
                return super(UpLibPageSearchQueryParser, self).getFuzzyQuery(fieldName, termText)
            else:
                return super(UpLibPageSearchQueryParser, self).getFuzzyQuery(fieldName, termText, minSimilarity)
        else:
            return MatchAllDocsQuery()
            
    def getPrefixQuery(self, fieldName, termText):
        if (not fieldName) or (fieldName in self.__STANDARDFIELDS):
            return super(UpLibPageSearchQueryParser, self).getPrefixQuery(fieldName, termText)
        else:
            return MatchAllDocsQuery()

    def getRangeQuery(self, fieldName, part1, part2, inclusive):
        if (not fieldName) or (fieldName in self.__STANDARDFIELDS):
            return super(UpLibPageSearchQueryParser, self).getRangeQuery(fieldName, part1, part2, inclusive)
        else:
            return MatchAllDocsQuery()

    def getWildcardQuery(self, fieldName, termText):
        if (not fieldName) or (fieldName in self.__STANDARDFIELDS):
            return super(UpLibPageSearchQueryParser, self).getWildcardQuery(fieldName, termText)
        else:
            return MatchAllDocsQuery()

class LuceneContext (object):

    USE_SNOWBALL_STEMMER = False

    MAX_SEARCH_COUNT = 1000

    def samedir (dir1, dir2):
        if isinstance(dir1, FSDirectory) and isinstance(dir2, FSDirectory):
            return (dir1.getFile() == dir2.getFile())
        if (sys.platform != "win32"):
            return os.path.samefile(dir1, dir2)
        else:
            return os.path.realpath(dir1) == os.path.realpath(dir2)
    samedir = staticmethod(samedir)

    def _get_explanation(query, docid, searcher):
        # we don't want to call this by default, as it's expensive to compute
        return searcher.explain(query, docid).toString();
    _get_explanation=staticmethod(_get_explanation)

    def find_search_context(index_dir):
        if os.path.exists(index_dir):
            return LuceneContext(index_dir)
        else:
            return None
    find_search_context=staticmethod(find_search_context)

    def parse_user_abbrevs_string (s):
        tdict = {}
        for abbrev in [x.strip() for x in s.split(";")]:
            if "=" in abbrev:
                tdict[abbrev[:abbrev.index("=")].strip()] = abbrev[abbrev.index("=") + 1:].strip()
        return tdict
    parse_user_abbrevs_string = staticmethod(parse_user_abbrevs_string)

    def __init__(self, index_dir):

        global SEARCH_ABBREVIATIONS, _INITIALIZED, DEFAULT_SEARCH_PROPERTIES, DEFAULT_SEARCH_OPERATOR
        global DEFAULT_LANGUAGE

        note(3, "LuceneContext(%s) in %s", index_dir, threading.currentThread())

        # initialize if necessary
        initialize()

        # directory containing the index
        self.directorypath = None
        self._fsdirectory = None
        # IndexReader open on the directory
        self.current_reader = None
        # IndexSearcher bound to this IndexReader
        self.current_searcher = None
        self._search_count = 0
        # IndexWriter bound to this index
        self.current_writer = None
        # version counter to see if some other thread has updated the index
        self.index_version = None
        # analyzer to use
        self.__analyzers = {}
        self.analyzer = self.analyzer_for_language(DEFAULT_LANGUAGE)
        # operator to use in joining terms
        self.default_operator = DEFAULT_SEARCH_OPERATOR
        # fields to search on, by default
        self.search_fields = HeaderField.parse_user_headers(DEFAULT_SEARCH_PROPERTIES)
        # user-specified abbreviations for various search terms and queries
        if SEARCH_ABBREVIATIONS:
            self.abbrevs = self.parse_user_abbrevs_string(SEARCH_ABBREVIATIONS)
        else:
            self.abbrevs = {}
        note(4, "self.abbrevs are %s, operator is %s, fields are %s",
             self.abbrevs, self.default_operator, self.search_fields.keys())
        if index_dir:
            self.set_index_dir(index_dir)

    def set_index_dir(self, index_dir):
        self.directorypath = os.path.normcase(os.path.normpath(index_dir))
        self._fsdirectory = None
        self.reopen()

    def analyzer_for_language(self, lang):

        global _LANGUAGE_ANALYZERS, SNOWBALL_ANALYZERS, SNOWBALL_ANALYZER_LANGUAGE_NAMES

        if self.__analyzers and lang in self.__analyzers:
            return self.__analyzers.get(lang)
        else:
            analyzer = None
            if _major_version < 3:
                # note that explicit use of the Snowball stemmers is deprecated in 3.x
                if self.USE_SNOWBALL_STEMMER and (lang in SNOWBALL_ANALYZER_LANGUAGE_NAMES):
                    if lang.startswith("en"):
                        # note that in 3.x, this becomes ENGLISH_STOP_WORD_SET
                        stopwords = lucene.StopAnalyzer.ENGLISH_STOP_WORDS
                    else:
                        stopwords = []
                    try:
                        analyzer = SnowballAnalyzer(SNOWBALL_ANALYZER_LANGUAGE_NAMES.get(lang), stopwords)
                        note(3, "For '%s', using SnowballAnalyzer with language %s, stopwords %s", lang,
                             SNOWBALL_ANALYZER_LANGUAGE_NAMES.get(lang), stopwords)
                    except:
                        note(0, "Cannot use SnowballAnalyzer:  %s\n",
                             ''.join(traceback.format_exception(*sys.exc_info())))
            if analyzer is None:
                if lang in _LANGUAGE_ANALYZERS:
                    if _indexversion is not None:
                        analyzer = _LANGUAGE_ANALYZERS[lang](_indexversion)
                    else:
                        analyzer = _LANGUAGE_ANALYZERS[lang]()
                else:
                    note(2, "No specific analyzer class for language '%s', so just using StandardAnalyzer.", lang)
                    if _indexversion is not None:
                        analyzer = StandardAnalyzer(_indexversion)
                    else:
                        analyzer = StandardAnalyzer()
            if analyzer:
                self.__analyzers[lang] = analyzer
            return analyzer

    def reopen(self):
        note(3, "reopen(%s)", self)
        if self.current_writer is not None:
            if _major_version < 3:
                self.current_writer.flush()
            self.current_writer.close()
            self.current_writer = None
        if self.current_searcher is not None:
            self.current_searcher.close()
            self.current_searcher = None
            self._search_count = 0
        if self.current_reader is not None:
            self.current_reader.close()
        if os.path.exists(self.directorypath):
            self.current_reader = IndexReader.open(self.directory())
            self.current_searcher = IndexSearcher(self.current_reader)
            self.index_version = IndexReader.getCurrentVersion(self.directory())
        self.doc_query_parser = UpLibQueryParser(self.search_fields, self.analyzer, self.abbrevs)
        self.doc_query_parser.setDefaultOperator(self.default_operator)
        self.page_query_parser = UpLibPageSearchQueryParser(self.analyzer, self.abbrevs)
        self.page_query_parser.setDefaultOperator(self.default_operator)

    def directory(self):
        if _major_version > 2:
            if not self._fsdirectory:
                self._fsdirectory = FSDirectory.open(File(self.directorypath))
            return self._fsdirectory
        else:
            return self.directorypath

    def reader(self, index_dir=None):
        if (self.current_reader is None or
            ((index_dir is not None) and
             not self.samedir(self.directorypath, index_dir))):
            if index_dir is None:
                # TODO:  this should default to current repository
                raise ValueError("No index dir specified.")
            else:
                self.directorypath = os.path.normcase(os.path.normpath(index_dir))
                self.reopen()
        return self.current_reader

    def searcher(self, index_dir=None):
        self.reader()
        if self.current_searcher is None:
            self.current_searcher = IndexSearcher(self.current_reader)
        elif IndexReader.getCurrentVersion(self.directory()) != self.index_version:
            note(4, 'current version of Lucene index is %s, previous was %s',
                 IndexReader.getCurrentVersion(self.directory()), self.index_version)
            self.reopen()
        elif self._search_count > self.MAX_SEARCH_COUNT:
            self.current_searcher.close()
            self.current_searcher = IndexSearcher(self.current_reader)
            self._search_count = 0
        return self.current_searcher

    def writer(self, index_dir=None):
        if index_dir:
            if self.current_writer:
                # check writer against dir
                wd = self.current_writer.getDirectory().getFile().getCanonicalPath()
                if not self.samedir(index_dir, wd):
                    if _major_version > 2:
                        self.current_writer = IndexWriter(
                            FSDirectory.open(File(index_dir)), self.analyzer, IndexWriter.MaxFieldLength.UNLIMITED)
                    else:
                        self.current_writer = IndexWriter(index_dir, self.analyzer)
            else:
                if _major_version > 2:
                    self.current_writer = IndexWriter(
                        FSDirectory.open(File(index_dir)), self.analyzer, IndexWriter.MaxFieldLength.UNLIMITED)
                else:
                    self.current_writer = IndexWriter(index_dir, self.analyzer)
        elif not self.current_writer:
            if _major_version > 2:
                self.current_writer = IndexWriter(
                    self.directory(), self.analyzer, IndexWriter.MaxFieldLength.UNLIMITED)
            else:
                self.current_writer = IndexWriter(self.directory(), self.analyzer)
        return self.current_writer

    def search(self, query, explain=False, count=None, lang=None):
        s = self.searcher()
        rval = []
        parsed_query = None
        try:
            # apparently query_parser isn't thread-safe
            # parsed_query = self.doc_query_parser.parseQ(query)
            if lang:
                analyzer = self.analyzer_for_language(lang)
            else:
                analyzer = self.analyzer
            query_parser = UpLibQueryParser(self.search_fields, analyzer, self.abbrevs)
            query_parser.setDefaultOperator(self.default_operator)
            try:
                parsed_query = query_parser.parseQ(query)
            except JavaError, x:
                note(3, "Exception received is", repr(x))
                required_language = RequiresQueryLanguage.get_language(x.message)
                if not required_language:
                    raise
                new_analyzer = self.analyzer_for_language(required_language)
                note("retrying query with analyzer %s for language %s", new_analyzer, required_language)
                query_parser = UpLibQueryParser(self.search_fields, new_analyzer, self.abbrevs)
                query_parser.setDefaultOperator(self.default_operator)
                parsed_query = query_parser.parseQ(query)
            except RequiresQueryLanguage, x:
                note(3, "Exception received is", repr(x))
                new_analyzer = self.analyzer_for_language(x.msg)
                note("retrying query with analyzer %s for language %s", new_analyzer, x.msg)
                query_parser = UpLibPageSearchQueryParser(new_analyzer, self.abbrevs)
                query_parser.setDefaultOperator(self.default_operator)
                parsed_query = query_parser.parseQ(query)
        except:
            note(3, "Exception on attempt to parse query string <<%s>>:\n%s",
                 query, ''.join(traceback.format_exception(*sys.exc_info())))
            raise
        if parsed_query:
            note(4, u"search query is " + unicode(parsed_query))
            if _have_topdocs:
                topdocs = s.search(parsed_query, count or 1000000)
                note(4, u"topdocs are %s (%s)", topdocs, topdocs.totalHits)
                for hit in topdocs.scoreDocs:
                    doc = s.doc(hit.doc)
                    score = hit.score
                    note(5, "doc %s is '%s' (%s)", doc.get("id"), doc.get("title") or doc.get("id"), score)
                    if explain:
                        rval.append((doc.get("id"), score,
                                     lambda x=parsed_query, y=hit.doc, z=s: self._get_explanation(x, y, z),))
                    else:
                        rval.append((doc.get("id"), score,))
            else:
                hits = s.search(parsed_query)
                note(4, u"hits are %s (%s)", hits, len(hits))
                for hit in hits:
                    doc = Hit.cast_(hit).getDocument()
                    score = Hit.cast_(hit).getScore()
                    note(5, "doc %s is '%s' (%s)", doc.get("id"), doc.get("title") or doc.get("id"), score)
                    if explain:
                        rval.append((doc.get("id"), score,
                                     lambda x=parsed_query, y=Hit.cast_(hit).getId(), z=s: self._get_explanation(x, y, z),))
                    else:
                        rval.append((doc.get("id"), score,))
            self._search_count += 1
        return rval

    def pagesearch(self, query, wholedocs=True, count=None, lang=None):
        s = self.searcher()
        # note("pagesearch query is %s", query)
        # apparently query_parser isn't thread-safe
        # parsed_query = self.page_query_parser.parseQ(query)
        if lang:
            analyzer = self.analyzer_for_language(lang)
        else:
            analyzer = self.analyzer
        page_query_parser = UpLibPageSearchQueryParser(self.analyzer, self.abbrevs)
        page_query_parser.setDefaultOperator(self.default_operator)
        try:
            try:
                parsed_query = page_query_parser.parseQ(query)
            except RequiresQueryLanguage, x:
                new_analyzer = self.analyzer_for_language(x.msg)
                note("retrying query with analyzer %s for language %s", new_analyzer, x.msg)
                page_query_parser = UpLibPageSearchQueryParser(new_analyzer, self.abbrevs)
                page_query_parser.setDefaultOperator(self.default_operator)
                parsed_query = page_query_parser.parseQ(query)
            except JavaError, x:
                # import jcc
                # print "lucene.VERSION:", lucene.VERSION, ", jcc._jcc.JCC_VERSION", jcc._jcc.JCC_VERSION
                # print "Exception received is", repr(x)
                # print sys.exc_info()
                required_language = RequiresQueryLanguage.get_language(x.message)
                if not required_language:
                    raise
                new_analyzer = self.analyzer_for_language(required_language)
                note("retrying query with analyzer %s for language %s", new_analyzer, required_language)
                page_query_parser = UpLibQueryParser(self.search_fields, new_analyzer, self.abbrevs)
                page_query_parser.setDefaultOperator(self.default_operator)
                parsed_query = page_query_parser.parseQ(query)
        except:
            note(3, "Exception on attempt to parse query string <<%s>>:\n%s",
                 query, ''.join(traceback.format_exception(*sys.exc_info())))
            raise
        rval = []
        if parsed_query:
            note(4, u"pagesearch query is " + unicode(parsed_query))
            if _have_topdocs:
                topdocs = s.search(parsed_query, count or 1000000)
                for hit in topdocs.scoreDocs:
                    doc = s.doc(hit.doc)
                    score = hit.score
                    doctype = doc.get("uplibtype")
                    if doctype == "whole" and wholedocs:
                        rval.append((doc.get("id"), score, '*',))
                    elif doctype == "page":
                        rval.append((doc.get("id"), score, doc.get("pagenumber"),))
            else:
                hits = s.search(parsed_query)
                for hit in hits:
                    doc = Hit.cast_(hit).getDocument()
                    score = Hit.cast_(hit).getScore()
                    doctype = doc.get("uplibtype")
                    if doctype == "whole" and wholedocs:
                        rval.append((doc.get("id"), score, '*',))
                    elif doctype == "page":
                        rval.append((doc.get("id"), score, doc.get("pagenumber"),))
            self._search_count += 1
        return rval

    def bothsearch(self, query, lang=None):
        wholedocs = self.search(query, lang=lang)
        pagedocs = self.pagesearch(query, False, lang=lang)
        # note(5, "pagedocs are %s", pagedocs)
        return wholedocs + pagedocs

    def remove(self, docid):
        w = self.writer()
        if w:
            # remove any existing instances of the document
            w.deleteDocuments(Term("id", docid))
            note(4, "flushing after deletion of %s", docid)
            if _major_version < 3:
                w.flush()
            else:
                w.commit()
            note(4, "finished flush")

    def index(self, folder, id, reopen_afterwards=True):
        d = DocumentAnalyzer(folder, id)
        w = self.writer()
        current_analyzer = w.getAnalyzer()
        req_analyzer_class = _LANGUAGE_ANALYZERS.get(d.doc_language())
        if req_analyzer_class and not isinstance(current_analyzer, req_analyzer_class):
            current_analyzer = self.analyzer_for_language(d.doc_language())
            note(3, "language is '%s'; using custom analyzer %s",
                 d.doc_language(), current_analyzer)
        if w:
            # first, remove any existing instances of the document
            w.deleteDocuments(Term("id", id))
            # now, re-index with the folder contents
            try:
                for x in d:
                    if plibUtil._verbosity > 2:
                        fields = x.getFields().toArray()
                        for field in fields:
                            #name = field.name()
                            name = Field.cast_(field).name()
                            if name in ("paragraph-ids",):
                                # don't show these
                                continue
                            v = field.toString()
                            if name in ("pagecontents", "contents", "abstract", "citation"):
                                newline = v.find('\n')
                                v = v[:min((newline < 0) and len(v) or newline, 50)]
                            note(3, "  %s", v)
                    w.addDocument(x, current_analyzer)
            except:
                note("Indexing of %s (%s) with %s failed:\n%s", folder, id, w,
                     ''.join(traceback.format_exception(*sys.exc_info())))
            # now push the index to the file system, and get a new reader
            if reopen_afterwards:
                self.reopen()
            else:
                note(3, "Note:  not flushing index %s after write, should be done explicitly...", w)
        note(3, "lucene refs are now %s", len(uthread.JAVA_ENV._dumpRefs()))

    def term_frequencies (self, fieldname, terms):
        s = self.searcher()
        t = s.docFreqs([Term(fieldname, term) for term in terms])
        self._search_count += 1
        return [(terms[i], t[i]) for i in range(len(terms))]

    def idf_factors (self, fieldname, terms):
        searcher = self.searcher()
        sim = searcher.getSimilarity()
        self._search_count += 1
        return [(term, sim.idf(Term(fieldname, term), searcher)) for term in terms]

    def interesting_terms (self, candidate_string, fieldnames=None, min_word_len=4, stop_words=None):

        if (candidate_string is None) or (len(candidate_string) < 1):
            note(3, "interesting_terms:  candidate_string too short:  '%s'", candidate_string)
            return []

        mlt = MoreLikeThis(self.reader())
        if fieldnames is not None:
            mlt.setFieldNames(fieldnames)
        if stop_words is not None:
            mlt.setStopWords(StringSet(stop_words))
        mlt.setMinWordLen(min_word_len)
        mlt.setAnalyzer(self.analyzer)
        r = StringReader(candidate_string)
        terms = mlt.retrieveInterestingTerms(r)
        r.close()
        return terms

    def like_this (self, candidate_string, fieldnames=None, min_word_len=4, stop_words=None):

        if (candidate_string is None) or (len(candidate_string) < 1):
            note(3, "like_this:  candidate_string too short:  '%s'", candidate_string)
            return "", []

        mlt = MoreLikeThis(self.reader())
        if fieldnames is not None:
            mlt.setFieldNames(fieldnames)
        if stop_words is not None:
            mlt.setStopWords(StringSet(stop_words))
        mlt.setMinWordLen(min_word_len)
        mlt.setAnalyzer(self.analyzer)
        reader = StringReader(candidate_string)
        query = mlt.like(reader)
        reader.close()
        rval = []
        if query:
            qstring = unicode(query)
            if len(qstring.split()) < 1:
                note(3, "like_this:  not enough terms for query")
                return qstring, []
            searchr = self.searcher()
            if _have_topdocs:
                topdocs = searchr.search(query, 1000)
                for hit in topdocs.scoreDocs:
                    doc = searchr.doc(hit.doc)
                    score = hit.score
                    doctype = doc.get("uplibtype")
                    if doctype == "whole":
                        rval.append((doc.get("id"), score, '*',))
                    elif doctype == "page":
                        rval.append((doc.get("id"), score, doc.get("pagenumber"),))
            else:
                hits = searchr.search(query)
                for hit in hits:
                    doc = Hit.cast_(hit).getDocument()
                    score = Hit.cast_(hit).getScore()
                    doctype = doc.get("uplibtype")
                    if doctype == "whole":
                        rval.append((doc.get("id"), score, '*',))
                    elif doctype == "page":
                        rval.append((doc.get("id"), score, doc.get("pagenumber"),))
            self._search_count += 1
        else:
            qstring = unicode("")
        return qstring, rval

    def __del__(self):
        if self.current_writer:
            self.current_writer.close()
        if self.current_reader:
            self.current_reader.close()
        if self.current_searcher:
            self.current_searcher.close()

def initialize(conf=None):

    global DEFAULT_SEARCH_PROPERTIES, DEFAULT_SEARCH_OPERATOR, SEARCH_ABBREVIATIONS, _INITIALIZED
    global DEFAULT_LANGUAGE, _LANGUAGE_ANALYZERS, _LANGUAGE_ANALYZER_CLASS_NAMES

    if _INITIALIZED:
        return

    if not (hasattr(uthread, "JAVA_ENV") and uthread.JAVA_ENV):
        uthread.JAVA_ENV = initVM(classpath=CLASSPATH)

    conf = conf or configurator.default_configurator()
    DEFAULT_SEARCH_OPERATOR = QueryParser.Operator.AND
    operator = conf.get("search-default-operator")
    if operator:
        if operator.lower() == "or":
            DEFAULT_SEARCH_OPERATOR = QueryParser.Operator.OR
        elif operator.lower() == "and":
            DEFAULT_SEARCH_OPERATOR = QueryParser.Operator.AND

    DEFAULT_SEARCH_PROPERTIES = conf.get("search-properties", DEFAULT_SEARCH_PROPERTIES)
    SEARCH_ABBREVIATIONS = conf.get("search-abbreviations", "")
    HeaderField.set_headers(conf.get("indexing-properties"))
    LuceneContext.USE_SNOWBALL_STEMMER = conf.get_bool("use-snowball-stemmers")

    DEFAULT_LANGUAGE = conf.get("default-language") or "en"
    for tag, classname in _LANGUAGE_ANALYZER_CLASS_NAMES:
        if classname in lucene.__dict__:
            _LANGUAGE_ANALYZERS[tag] = lucene.__dict__.get(classname)
    note(3, "_LANGUAGE_ANALYZERS are %s", _LANGUAGE_ANALYZERS)

    _INITIALIZED = True

def add_indexing_hook (fn, fields=None):
    # fn should be a function that takes three args, a document ID,
    # folder, and a page index, with an index of -1 for the whole
    # document.  When called, it returns an iteration of Field
    # instances to add to the index for this document.

    global INDEXING_HOOKS

    if INDEXING_HOOKS is None:
        INDEXING_HOOKS = [fn]
    else:
        INDEXING_HOOKS.append(fn)
    if fields:
        for field in fields:
            HeaderField.add_header(field)

# a hook for module testing

def index (indexd, docfolder):

    c = LuceneContext(indexd)
    c.index(docfolder, os.path.basename(docfolder))

def tindex (indexd, docfolder):

    t = uthread.start_new_thread(index, (indexd, docfolder))
    t.join()

def search (indexd, searchterms):

    c = LuceneContext(indexd)
    print c.search(' '.join(searchterms))

def pagesearch (indexd, searchterms):

    c = LuceneContext(indexd)
    print c.pagesearch(' '.join(searchterms))

def remove (indexd, docid):

    c = LuceneContext(indexd)
    c.remove(docid)

def like (indexd, terms):

    c = LuceneContext(indexd)
    qstring, hits = c.like_this(' '.join(terms))
    print 'terms:', qstring
    for hit in hits:
        print hit

def terms (indexd, terms):
    c = LuceneContext(indexd)
    print c.interesting_terms(' '.join(terms))

initialize()

if __name__ == "__main__":

    def usage():
        sys.stderr.write("Usage:  python %s [index|tindex|search|like|terms] INDEXDIR ARGS...\n")
        sys.exit(1)

    sys.path.insert(0, '/u/python')
    print sys.path
    from uplib.plibUtil import set_verbosity
    set_verbosity(4)
    HeaderField.set_headers(configurator.default_configurator().get("indexing-properties"))

    if len(sys.argv) < 4:
        usage()

    if sys.argv[1] == 'index':
        index(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'tindex':
        tindex(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'search':
        search(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == 'pagesearch':
        pagesearch(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == 'like':
        like(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == 'terms':
        terms(sys.argv[2], sys.argv[3:])
    else:
        sys.stderr.write("unrecognized operation:  %s\n" % sys.argv[1])
        usage()
