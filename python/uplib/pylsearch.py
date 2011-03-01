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

import sys, os, string, types, time

from PyLucene import IndexReader, IndexSearcher, StandardAnalyzer, MultiFieldQueryParser, BooleanQuery, TermQuery, Term, BooleanClause, RangeQuery

from uplib.plibUtil import configurator, note, parse_date, true, false

try:
    from PyLucene import QueryParser_Operator
    OPERATOR_AND = QueryParser_Operator.AND
    OPERATOR_OR = QueryParser_Operator.OR
except ImportError:
    from PyLucene import QueryParser
    OPERATOR_AND = QueryParser.Operator.AND
    OPERATOR_OR = QueryParser.Operator.OR

class SearchContext (object):

    STANDARD_PROPERTIES = "contents:title:authors:comment:abstract:keywords*"

    def __init__(self, index_dir):

        self.directorypath = None
        self.current_reader = None
        self.current_searcher = None
        self.index_version = None
        self.analyzer = StandardAnalyzer()
        conf = configurator.default_configurator()
        self.default_operator = OPERATOR_AND
        operator = conf.get("search-default-operator")
        if type(operator) in types.StringTypes and operator.lower() == "or":
            self.default_operator = OPERATOR_OR
        note(5, "default query term combination operator is " + self.default_operator.toString())
        search_terms = conf.get("search-properties")
        fields = self.parse_search_property_string(search_terms or self.STANDARD_PROPERTIES)
        search_abbrevs = conf.get("search-abbreviations", "")
        self.abbrevs = self.parse_user_abbrevs_string(search_abbrevs)
        note(5, "default search properties are %s", fields)    
        self.doc_query_pyparser = UpLibQueryParser(fields, self.abbrevs)
        self.doc_query_parser = None
        self.page_query_pyparser = UpLibPageSearchQueryParser({"pagecontents": (),}, self.abbrevs)
        self.page_query_parser = None
        if index_dir and os.path.exists(index_dir):
            self.directorypath = os.path.normcase(os.path.normpath(index_dir))
            self.reopen()

    def find_search_context(index_dir):
        if os.path.exists(index_dir):
            return SearchContext(index_dir)
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

    def parse_search_property_string(s):
        tdict = {}
        terms = s.split(':')
        for term in terms:
            termname = term
            termprops = ()
            if term[-1] == '@':
                termname = term[:-1]
                termprops = ("date", "untokenized",)
            elif term[-1] == '*':
                termname = term[:-1]
                termprops = ("untokenized",)
            if '$' in termname:
                p = termname.index('$')
                termname = termname[:p]
            tdict[termname] = termprops
        return tdict
    parse_search_property_string=staticmethod(parse_search_property_string)

    def reopen(self):
        note(5, "reopen(%s)", self)
        if self.current_reader is not None:
            self.current_reader.close()
        self.current_reader = IndexReader.open(self.directorypath)
        self.current_searcher = IndexSearcher(self.current_reader)
        self.index_version = IndexReader.getCurrentVersion(self.directorypath)

        self.doc_query_parser = self.analyzer.multiFieldQueryParser(self.doc_query_pyparser, self.doc_query_pyparser.fieldNames())
        self.doc_query_parser.setDefaultOperator(self.default_operator)

        self.page_query_parser = self.analyzer.multiFieldQueryParser(self.page_query_pyparser, self.page_query_pyparser.fieldNames())
        self.page_query_parser.setDefaultOperator(self.default_operator)


    def directory(self):
        return self.directorypath

    def samedir (dir1, dir2):
        return os.path.samefile(os.path.normcase(os.path.normpath(dir1)),
                                os.path.normcase(os.path.normpath(dir2)))
    samedir = staticmethod(samedir)

    def searcher(self, index_dir=None):
        if (self.current_reader is None or
            ((index_dir is not None) and
             not self.samedir(self.directory(), index_dir))):
            if index_dir is None:
                # TODO:  this should default to current repository
                raise ValueError("No index dir specified.")
            else:
                self.directorypath = os.path.normcase(os.path.normpath(index_dir))
                self.reopen()
        elif self.current_searcher is None:
            self.current_searcher = IndexSearcher(self.current_reader)
        elif IndexReader.getCurrentVersion(self.directorypath) != self.index_version:
            note(4, 'current version of Lucene index is %s, previous was %s',
                 IndexReader.getCurrentVersion(self.directorypath), self.index_version)
            self.reopen()
        return self.current_searcher

    def search(self, query):
        s = self.searcher()
        # note(4, "before post-processing, query is " + query)
        if hasattr(MultiFieldQueryParser, "parseQuery"):
            parsed_query = self.doc_query_pyparser.postProcessQuery(self.doc_query_parser.parseQuery(query))
        else:
            parsed_query = self.doc_query_pyparser.postProcessQuery(self.doc_query_parser.parse(query))
        rval = []
        if parsed_query:
            # note(3, "search query is " + parsed_query.toString())
            hits = s.search(parsed_query)
            for i, doc in hits:
                rval.append((doc.get("id"), hits.score(i),))
        return rval

    def pagesearch(self, query, wholedocs=True):
        s = self.searcher()
        # note("pagesearch query is %s", query)
        if hasattr(MultiFieldQueryParser, "parseQuery"):
            q2 = self.page_query_parser.parseQuery(query)
        else:
            q2 = self.page_query_parser.parse(query)
        parsed_query = self.page_query_pyparser.postProcessQuery(q2)
        rval = []
        if parsed_query:
            # note(4, "pagesearch query is " + repr(parsed_query))
            hits = s.search(parsed_query)
            for i, doc in hits:
                doctype = doc.get("uplibtype")
                if doctype == "whole" and wholedocs:
                    rval.append((doc.get("id"), hits.score(i), '*',))
                elif doctype == "page":
                    rval.append((doc.get("id"), hits.score(i), doc.get("pagenumber"),))
        return rval

    def bothsearch(self, query):
        return self.search(query) + self.pagesearch(query, False)

    def interesting_terms (self, candidate_string):
        try:
            from PyLucene import MoreLikeThis, StringReader, VERSION
            if not hasattr(MoreLikeThis, "retrieveInterestingTerms"):
                note("interesting_terms not supported; need PyLucene 2.1 or later; current version is %s", VERSION)
                return []
        except ImportError:
            note("interesting_terms not supported; need PyLucene 2.1 or later; current version is %s", VERSION)
            return []

        mlt = MoreLikeThis(self.current_reader)
        r = StringReader(candidate_string)
        terms = mlt.retrieveInterestingTerms(StringReader(candidate_string))
        r.close()
        return terms

    def like_this (self, candidate_string, fieldnames=None, min_word_len=4, stop_words=None):
        try:
            from PyLucene import MoreLikeThis, StringReader
        except ImportError:
            note("like_this not supported; need PyLucene 2.1 or later")
            return "", []

        if (candidate_string is None) or (len(candidate_string) < 1):
            note("like_this:  candidate_string too short:  '%s'", candidate_string)
            return "", []

        mlt = MoreLikeThis(self.current_reader)
        if fieldnames is not None:
            mlt.setFieldNames(fieldnames)
        if stop_words is not None:
            mlt.setStop(stop_words)
        mlt.setMinWordLen(min_word_len)
        reader = StringReader(candidate_string)
        query = mlt.like(reader)
        reader.close()
        rval = []
        if query:
            qstring = unicode(query)
            if len(qstring.split()) < 1:
                note(3, "like_this:  not enough terms for query")
                return qstring, []
            hits = self.searcher().search(query)
            for i, doc in hits:
                doctype = doc.get("uplibtype")
                if doctype == "whole":
                    rval.append((doc.get("id"), hits.score(i), '*',))
                elif doctype == "page":
                    rval.append((doc.get("id"), hits.score(i), doc.get("pagenumber"),))
        else:
            qstring = unicode("")
        return qstring, rval


class UpLibQueryParser (object):

    def __init__(self, fields, abbrevs):
        self.fields = fields
        self.abbrevs = abbrevs

    def convertDate(date):
        year, month, day = parse_date(date)
        return "%04d%02d%02d" % (year, month, day)
    convertDate=staticmethod(convertDate)

    def postProcessQuery (self, query):
        # note("postProcessQuery(%s)...", query)
        if query.isBooleanQuery() and (len(query.toBooleanQuery().getClauses()) > 0):
            all_negative = True
            for clause in query.toBooleanQuery().getClauses():
                if not clause.isProhibited():
                    all_negative = False
                    break
            if all_negative:
                q2 = TermQuery(Term("categories", "_(all)_"))
                query.toBooleanQuery().add(q2, BooleanClause.Occur.SHOULD)
        # note("... => %s", query)
        if query.isBooleanQuery() and len(query.toBooleanQuery().getClauses()) == 0:
            return None
        else:
            return query

    def fieldNames(self):
        return self.fields.keys()

    def isTokenizedField(self, fname):
        v = self.fields.get(fname)
        # true if not explicitly non-tokenized
        return not (v and ("untokenized" in v))

    def isDateField(self, fname):
        v = self.fields.get(fname)
        # true only if explicitly specified as a date field
        return ((v is not None) and ("date" in v))

    def addClause(clauses, conjunction, mods, query):
        # note("adding clause %s to %s", query, clauses)
        super.addClause(clauses, conjunction, mods, query)

    def getFieldQuery(self, super, fieldname, text, slop):
        # note("getFieldQuery(%s, %s, %s)" % (fieldname, text, slop))
        orig = None
        if fieldname:
            if fieldname[0] == '$' and fieldname[1:] in self.abbrevs:
                # note(5, "  processing abbrev field %s", fieldname)
                return self.getFieldQuery(super, self.abbrevs[fieldname[1:]], text, slop)
            if fieldname == "categories":
                # note(5, "  processing categories field")
                orig = TermQuery(Term(fieldname, string.join([x.strip() for x in text.lower().split('/')], '/')))
            elif ((fieldname in ("date", "uplibdate")) or self.isDateField(fieldname)) and ('/' in text):
                # note(5, "  processing date field %s", fieldname)
                orig = TermQuery(Term(fieldname, self.convertDate(text)))
            elif (fieldname == "keywords") or (not self.isTokenizedField(fieldname)):
                # note(5, "  processing keyword or non-tokenized field %s", fieldname)
                orig = TermQuery(Term(fieldname, text))
        else:
            if text[0] == '$' and text[1:] in self.abbrevs:
                newparser = super.getAnalyzer().multiFieldQueryParser(self, self.fieldNames())
                newquery = self.abbrevs[text[1:]]
                if hasattr(MultiFieldQueryParser, "parseQuery"):
                    return newparser.parseQuery(newquery)
                else:
                    return newparser.parse(newquery)
        if not orig:
            if slop is None:
                orig = super.getFieldQuery(fieldname, text)
            else:
                orig = super.getFieldQuery(fieldname, text, slop)
            # note(5, "super.getFieldQuery(%s, %s, %s) => %s" % (fieldname, text, slop, orig))
        return orig

    def getRangeQuery(self, super, fieldname, part1, part2, inclusive):
        if fieldname and ((fieldname in ("date", "uplibdate")) or self.isDateField(fieldname)):
            if '/' in part1:
                part1 = self.convertDate(part1)
            if '/' in part2:
                part2 = self.convertDate(part2)
            return RangeQuery(Term(fieldname, part1), Term(fieldname, part2), inclusive)
        else:
            return super.getRangeQuery(fieldname, part1, part2, inclusive)


class UpLibPageSearchQueryParser (UpLibQueryParser):

    def __init__(self, fields, abbrevs):
        UpLibQueryParser.__init__(self, fields, abbrevs)

    def getFieldQuery(self, super, fieldName, text, slop):
        if (not fieldName) or (fieldName == "pagecontents"):
            # no particular field, so run it
            return UpLibQueryParser.getFieldQuery(self, super, fieldName, text, slop)
        else:
            return None

    def getFuzzyQuery(self, super, fieldName, termText, minSimilarity=None):
        if (not fieldName) or (fieldName == "pagecontents"):
            # no particular field, so run it
            if minSimilarity is None:
                return super.getFuzzyQuery(fieldName, termText)
            else:
                return super.getFuzzyQuery(fieldName, termText, minSimilarity)
        else:
            return None
            
    def getPrefixQuery(self, super, fieldName, termText):
        if (not fieldName) or (fieldName == "pagecontents"):
            return super.getPrefixQuery(fieldName, termText)
        else:
            return None

    def getRangeQuery(self, super, fieldName, part1, part2, inclusive):
        if (not fieldName) or (fieldName == "pagecontents"):
            return UpLibQueryParser.getRangeQuery(self, super, fieldName, part1, part2, inclusive)
        else:
            return None

    def getWildcardQuery(self, super, fieldName, termText):
        if (not fieldName) or (fieldName == "pagecontents"):
            return super.getWildcardQuery(fieldName, termText)
        else:
            return None
