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
If the CiteSeerX parsers for citation indexing and header parsing are available,
try using them.  Use the standard CiteSeerX pattern match to see if the document
is a technical paper.

Installing CiteSeerX's ParsCit on OS X Leopard:

1.  Check out the CiteSeerX sources:

% svn co https://citeseerx.svn.sourceforge.net/svnroot/citeseerx citeseerx

2.  Make a place for the parser to reside:

% mkdir /usr/local/ParsCit

3.  Copy the Perl code to that location:

% cp -r ./citeseerx/trunk/src/perl/ParsCit/* /usr/local/ParsCit
% cp -r ./citeseerx/trunk/src/perl/CSXUtil /usr/local/ParsCit/lib

4.  Download CRF++:

% curl -k -L http://downloads.sourceforge.net/project/crfpp/crfpp/0.54/CRF%2B%2B-0.54.tar.gz > /tmp/CRF++-0.54.tar.gz

5.  Configure and build CRF++:

% tar xvf /tmp/CRF++-0.54.tar.gz
% cd CRF++-0.54
% ./configure --disable-static --disable-shared
% make 
% cd ..

6.  Copy crf_learn and crf_test to the ParsCit location:

% rm -rf /usr/local/ParsCit/crfpp/crf_learn /usr/local/ParsCit/crfpp/crf_test
% install -m 555 crf_test crf_learn /usr/local/ParsCit/crfpp/

7.  Now put /usr/local/ParsCit/bin on your path.

8.  Run citeExtract.pl against the text of a paper to extract the citations.

Installing CiteSeerX's HeaderParser on OS X Leopard:

1.  Install the Perl module String::Approx:

% sudo perl -MCPAN -e shell
cpan> install String::Approx
...
cpan> quit
%

2.  Check out the CiteSeerX sources:

% svn co https://citeseerx.svn.sourceforge.net/svnroot/citeseerx citeseerx

3.  Make a place for the parser to reside:

% mkdir /usr/local/CiteSeerHeaderParser

4.  Copy the Perl code to that location:

% cp -r ./citeseerx/trunk/src/perl/HeaderParseService/* /usr/local/CiteSeerHeaderParser
% cp -r ./citeseerx/trunk/src/perl/CSXUtil /usr/local/CiteSeerHeaderParser/lib

5.  Download SVM Light (version 5.00) source tarball from http://svmlight.joachims.org/:

% curl -k -L http://kodiak.cs.cornell.edu/svm_light/v5.00/svm_light.tar.gz >/tmp/svm_light.tar.gz

(This has to be version 5.00 because the pre-built models that ship with CiteSeerX are built
with that version.)

6.  Unpack and build svm_light:

% mkdir svm_light
% cd svm_light
% tar xvf /tmp/svm_light.tar.gz
% make
% cd ..

7.  Replace the svm_light that ships with CiteSeerX:

% rm -f /usr/local/CiteSeerHeaderParser/svm-light/svm_classify /usr/local/CiteSeerHeaderParser/svm-light/svm_learn
% install -m 555 ./svm_light/svm_learn ./svm_light/svm_classify /usr/local/CiteSeerHeaderParser/svm-light/

8.  Now put /usr/local/CiteSeerHeaderParser/bin on your path.

9.  Run extractHeader.pl against the text of a document to extract the header info.

"""

import sys, os, re, tempfile, codecs, pprint
from uplib.plibUtil import note, configurator, read_file_handling_charset, subproc
from uplib.ripper import Ripper, rerip_generic

from BeautifulSoup import BeautifulStoneSoup

CITATION_PARSER = None
"""The program that runs the CiteSeer citation parser."""

HEADER_PARSER = None
"""The program that runs the CiteSeer header parser."""

REFERENCES_PATTERN = re.compile(r"\b(REFERENCES?|References?|BIBLIOGRAPHY|Bibliography|REFERENCES AND NOTES|References and Notes)\:?\s*\n")
"""Pattern to look for to infer that a paper is a technical report.

This pattern from:
"The CiteSeerX Ingestion System"
Isaac G. Councill
TR No. 0021
College of Information Sciences and Technology
The Pennsylvania State University
Sept 18, 2007
"""

ABSTRACT_PREFIX = re.compile(r"^(?P<prefix>\s*abstract[.:]?\s+)\b.*", re.IGNORECASE)
"""Prefix string to trim off CiteSeer's abstract text"""

TRADITIONAL_PAPER_FORMATS = ("application/pdf",
                             "application/postscript",
                             "application/msword",
                             "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             "application/rtf")
"""List of traditional media for papers to appear in."""

class CiteSeerParserRipper(Ripper):

    def __init__(self, repo, citation_parser=None, header_parser=None):
        Ripper.__init__(self, repo)
        self.__citation_parser = citation_parser
        self.__header_parser = header_parser

    def rip (self, location, doc_id):

        global CITATION_PARSER, HEADER_PARSER

        omd = self.get_folder_metadata(location)

        # CiteSeer really only works on traditional publications, so let's stay
        # with PDF and Word docs
        mimetype = omd.get("apparent-mime-type")
        if mimetype not in TRADITIONAL_PAPER_FORMATS:
            return

        text, language = self.get_folder_text(location)
        if not text:
            # no text to look at
            return

        m = REFERENCES_PATTERN.search(text)
        if not m:
            # no REFERENCES_PATTERN in text
            return

        # just a note if we're re-ripping something
        if self.repository().valid_doc_id(doc_id):
            note(3, "%s is a technical report", self.repository().get_document(doc_id))

        cp = self.__citation_parser or CITATION_PARSER
        if cp:
            status, output, tsig = subproc('%s "%s"' % (cp, self.folder_text_path(location)))
            if status == 0:
                parsed = BeautifulStoneSoup(output.strip())
                citations = parsed.findAll("citation")
                note(3, "found %d citations", len(citations))
                fp = open(os.path.join(location, "citeseerx-citations.xml"), "w")
                fp.write(output.strip())

        hp = self.__header_parser or HEADER_PARSER
        if hp:
            tfile = tempfile.mktemp()
            fp = codecs.open(tfile, "w", "UTF-8")
            fp.write(text)
            fp.close()
            try:
                status, output, tsig = subproc('%s "%s"' % (hp, tfile))
                if status == 0:
                    md = dict()
                    parsed = BeautifulStoneSoup(output.strip())
                    title = parsed.find("title")
                    if title:
                        if title.string:
                            md['citeseer-title'] = title.string
                        else:
                            note(3, "Non-string title found: %s", title)
                    authors = set()
                    for author in parsed.findAll("author"):
                        n = author.find("name")
                        if n:
                            authors.add(n.string)
                        else:
                            authors.add(author.string)
                    if authors:
                        md['citeseer-authors'] = " and ".join(list(authors))
                    abstract = parsed.find("abstract")
                    if abstract:
                        if abstract.string:
                            md['citeseer-abstract'] = abstract.string
                        else:
                            note(3, "Non-string abstract found: %s", abstract)
                    note(3, "citeseer metadata is %s", pprint.pformat(md))
                    if "citeseer-title" in md:
                        # use CiteSeer data to fix up document metadata, if necessary
                        if ((not omd.get("title")) or
                            (omd.get("title-is-original-filepath", "false").lower() == "true")):
                            md['title'] = md.get("citeseer-title")
                            md['title-is-original-filepath'] = None
                            md['title-is-citeseer-extracted'] = "true"
                        if ("citeseer-authors" in md) and (not omd.get("authors")):
                            md['authors'] = md.get("citeseer-authors")
                        if ("citeseer-abstract" in md) and (not md.get("abstract")):
                            abs = md.get("citeseer-abstract")
                            prefix = ABSTRACT_PREFIX.match(abs)
                            if prefix:
                                realstart = prefix.end("prefix")
                                note(3, "trimming abstract prefix of %s", repr(abs[:realstart]))
                                abs = abs[realstart:]
                            md['abstract'] = abs                            
                        note(3, "updated missing metadata with CiteSeer versions")
                    self.update_folder_metadata(location, md)
            finally:
                if os.path.exists(tfile):
                    os.unlink(tfile)


def rerip_all (repo, response, params):

    global CITATION_PARSER, HEADER_PARSER

    rerip_generic(repo, response, params, CiteSeerParserRipper(repo, CITATION_PARSER, HEADER_PARSER),
                  (), docs=repo.generate_docs())

def rerip (repo, response, params):

    global CITATION_PARSER, HEADER_PARSER

    rerip_generic(repo, response, params, CiteSeerParserRipper(repo, CITATION_PARSER, HEADER_PARSER),
                  ("LuceneRipper"))


def after_repository_instantiation(repo):

    global CITATION_PARSER, HEADER_PARSER

    conf = configurator.default_configurator()
    CITATION_PARSER = conf.get("citeseer-citation-parser")
    HEADER_PARSER = conf.get("citeseer-header-parser")

    if CITATION_PARSER or HEADER_PARSER:
        rippers = repo.rippers()
        rippers.insert(-3, CiteSeerParserRipper(repo))

    
