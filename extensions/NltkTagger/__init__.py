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
# Uses NLTK, if installed, to annotate text with sentence boundaries and part-of-speech tags.
#
# We actually want to use the Hunpos tagger, an interface for which should be available
# eventually in NLTK 2.0, but it's not in 2.0beta8, so for the moment we use the native
# NLTK implementation of TnT, which is slow.  Trained on the Brown corpus.
#

import sys, os, re, traceback, types, pickle

from uplib.plibUtil import note, configurator
from uplib.ripper import Ripper, rerip_generic
from uplib.paragraphs import read_paragraphs_file

from uplib.plibUtil import read_file_handling_charset_returning_bytes, read_wordboxes_file, wordboxes_for_span
from uplib.webutils import HTTPCodes
from uplib.paragraphs import read_paragraphs_file

SENTENCE_BREAKER = None
POS_TAGGER = None

_UPENN_TAGS_TO_UPLIB_TAGS = {
    "-NONE-": "Unknown",
    "PRP$": "Det-Poss",
    "VBG": "V-Pres",
    "FW": "For",
    "VB": "V-Pres",
    "POS": "Part-Poss",
    "VBP": "V-Pres",
    "VBN": "V-PaPart",
    "JJ": "Adj",
    "WP": "Pron-Int",
    "VBZ": "V-Pres-3-Sg",
    "DT": "Det",
    "RP": "Part-Inf",
    "$": "Punct-Money",
    "NN": "Nn",
    ")": "Punct-Close",
    "(": "Punct-Open",
    "RBR": "Adv-Comp",
    "VBD": "V-Past",
    ",": "Punct-Comma",
    ".": "Punct-Sent",
    "TO": "Prep",
    "LS": "Unknown",
    "RB": "Adv",
    ":": "Punct",
    "NNS": "Nn-Pl",
    "NNP": "Prop",
    "``": "Punct-Quote",
    "WRB": "Adv-IntRel",
    "CC": "Conj-Coord",
    "PDT": "Det",
    "RBS": "Adv-Sup",
    "PRP": "Pron-Refl",
    "CD": "Num",
    "EX": "Unknown",
    "IN": "Conj-Sub",
    "WP$": "Pron",
    "MD": "Aux",
    "NNPS": "Nn-Pl",
    "--": "Punct",
    "JJS": "Adj-Sup",
    "JJR": "Adj-Comp",
    "SYM": "Punct",
    "UH": "Interj",
    "WDT": "Det-IntRel",
    }

_BROWN_TAGS_TO_UPLIB_TAGS = {
    "-NONE-": "Unknown",
    "(" : "Punct-Open",
    ")" : "Punct-Close",
    "*" : "Punct",
    "," : "Punct-Comma",
    "--" : "Punct",
    "." : "Punct-Sent",
    ":" : "Punct",
    "ABL" : "Det",
    "ABN" : "Det",
    "ABX" : "Det",
    "AP" : "Det",
    "AP$" : "Det-Poss",
    "AP+AP" : "Det",
    "AT" : "Det",
    "BE" : "V-Inf-be",
    "BED" : "V-Past-Pl-be",
    "BED*" : "V-Past-Pl-be",
    "BEDZ" : "V-Past-Sg-be",
    "BEDZ*" : "V-Past-Sg-be",
    "BEG" : "V-Pres",
    "BEM" : "V-Pres",
    "BEM*" : "V-Pres",
    "BEN" : "V-PaPart-be",
    "BER" : "V-Pres-Pl-be",
    "BER*" : "V-Pres-Pl-be",
    "BEZ" : "V-Pres-Sg-be",
    "BEZ*" : "V-Pres-Sg-be",
    "CC" : "Conj-Coord",
    "CD" : "Num",
    "CD$" : "Num",
    "CD-HL" : "Num",
    "CD-TL" : "Num",
    "CS" : "Conj-Sub",
    "DO" : "V-Past",
    "DO*" : "V-Pres",
    "DO+PPSS" : "V-Pres",
    "DOD" : "V-Past",
    "DOD*" : "V-Past",
    "DOZ" : "V-Pres-3-Sg",
    "DOZ*" : "V-Pres-3-Sg",
    "DT" : "Det-Sg",
    "DT$" : "Det-Poss",
    "DT+BEZ" : "Det",
    "DT+MD" : "Det",
    "DTI" : "Det",
    "DTS" : "Det-Pl",
    "DTS+BEZ" : "Det-Pl",
    "DTX" : "Det",
    "EX" : "Pron",
    "EX+BEZ" : "Pron",
    "EX+HVD" : "Pron",
    "EX+HVZ" : "Pron",
    "EX+MD" : "Pron",
    "FW-ABL" : "Det",
    "FW-ABN" : "Det",
    "FW-ABX" : "Det",
    "FW-AP" : "Det",
    "FW-AP$" : "Det-Poss",
    "FW-AP+AP" : "Det",
    "FW-AT" : "Det",
    "FW-BE" : "V-Inf-be",
    "FW-BED" : "V-Past-Pl-be",
    "FW-BED*" : "V-Past-Pl-be",
    "FW-BEDZ" : "V-Past-Sg-be",
    "FW-BEDZ*" : "V-Past-Sg-be",
    "FW-BEG" : "V-Pres",
    "FW-BEM" : "V-Pres",
    "FW-BEM*" : "V-Pres",
    "FW-BEN" : "V-PaPart-be",
    "FW-BER" : "V-Pres-Pl-be",
    "FW-BER*" : "V-Pres-Pl-be",
    "FW-BEZ" : "V-Pres-Sg-be",
    "FW-BEZ*" : "V-Pres-Sg-be",
    "FW-CC" : "Conj-Coord",
    "FW-CD" : "Num",
    "FW-CD$" : "Num",
    "FW-CS" : "Conj-Sub",
    "FW-DO" : "V-Past",
    "FW-DO*" : "V-Pres",
    "FW-DO+PPSS" : "V-Pres",
    "FW-DOD" : "V-Past",
    "FW-DOD*" : "V-Past",
    "FW-DOZ" : "V-Pres-3-Sg",
    "FW-DOZ*" : "V-Pres-3-Sg",
    "FW-DT" : "Det-Sg",
    "FW-DT$" : "Det-Poss",
    "FW-DT+BEZ" : "Det",
    "FW-DT+MD" : "Det",
    "FW-DTI" : "Det",
    "FW-DTS" : "Det-Pl",
    "FW-DTS+BEZ" : "Det-Pl",
    "FW-DTX" : "Det",
    "FW-EX" : "Pron",
    "FW-EX+BEZ" : "Pron",
    "FW-EX+HVD" : "Pron",
    "FW-EX+HVZ" : "Pron",
    "FW-EX+MD" : "Pron",
    "FW-HV" : "V-Pres-have",
    "FW-HV*" : "V-Pres-have",
    "FW-HV+TO" : "V-Pres-have",
    "FW-HVD" : "V-Past-have",
    "FW-HVD*" : "V-Past-have",
    "FW-HVG" : "V-Pres-have",
    "FW-HVN" : "V-Past-have",
    "FW-HVZ" : "V-Pres-3-Sg-have",
    "FW-HVZ*" : "V-Pres-3-Sg-have",
    "FW-IN" : "Prep",
    "FW-IN+IN" : "Prep",
    "FW-IN+PPO" : "Prep",
    "FW-JJ" : "Adj",
    "FW-JJ$" : "Adj",
    "FW-JJ+JJ" : "Adj",
    "FW-JJR" : "Adj-Comp",
    "FW-JJR+CS" : "Adj-Comp",
    "FW-JJS" : "Adj-Sup",
    "FW-JJT" : "Adj-Sup",
    "FW-MD" : "Aux",
    "FW-MD*" : "Aux",
    "FW-MD+HV" : "Aux",
    "FW-MD+PPSS" : "Aux",
    "FW-MD+TO" : "Aux",
    "FW-NN" : "Nn-Sg",
    "FW-NN$" : "Nn-Sg",
    "FW-NN+BEZ" : "Nn-Sg",
    "FW-NN+HVD" : "Nn-Sg",
    "FW-NN+HVZ" : "Nn-Sg",
    "FW-NN+IN" : "Nn-Sg",
    "FW-NN+MD" : "Nn-Sg",
    "FW-NN+NN" : "Nn-Sg",
    "FW-NNS" : "Nn-Pl",
    "FW-NNS$" : "Nn-Pl",
    "FW-NNS+MD" : "Nn-Pl",
    "FW-NP" : "Prop",
    "FW-NP$" : "Prop",
    "FW-NP+BEZ" : "Prop",
    "FW-NP+HVZ" : "Prop",
    "FW-NP+MD" : "Prop",
    "FW-NPS" : "Prop",
    "FW-NPS$" : "Prop",
    "FW-NR" : "Prop",
    "FW-NR$" : "Prop",
    "FW-NR+MD" : "Nn-Sg",
    "FW-NRS" : "Nn-Pl",
    "FW-OD" : "Ord",
    "FW-PN" : "Pron",
    "FW-PN$" : "Pron",
    "FW-PN+BEZ" : "Pron",
    "FW-PN+HVD" : "Pron",
    "FW-PN+HVZ" : "Pron",
    "FW-PN+MD" : "Pron",
    "FW-PP$" : "Det-Poss",
    "FW-PP$$" : "Pron",
    "FW-PPL" : "Pron-Refl",
    "FW-PPLS" : "Pron-Refl",
    "FW-PPO" : "Pron",
    "FW-PPS" : "Pron",
    "FW-PPS+BEZ" : "Pron",
    "FW-PPS+HVD" : "Pron",
    "FW-PPS+HVZ" : "Pron",
    "FW-PPS+MD" : "Pron",
    "FW-PPSS" : "Pron",
    "FW-PPSS+BEM" : "Pron",
    "FW-PPSS+BER" : "Pron",
    "FW-PPSS+BEZ" : "Pron",
    "FW-PPSS+BEZ*" : "Pron",
    "FW-PPSS+HV" : "Pron",
    "FW-PPSS+HVD" : "Pron",
    "FW-PPSS+MD" : "Pron",
    "FW-PPSS+VB" : "Pron",
    "FW-QL" : "Det",
    "FW-QLP" : "Det",
    "FW-RB" : "Adv",
    "FW-RB$" : "Adv",
    "FW-RB+BEZ" : "Adv",
    "FW-RB+CS" : "Adv",
    "FW-RBR" : "Adv-Comp",
    "FW-RBR+CS" : "Adv-Comp",
    "FW-RBT" : "Adv-Sup",
    "FW-RN" : "Adv",
    "FW-RP" : "Adv",
    "FW-RP+IN" : "Adv",
    "FW-TO" : "Part-Inf",
    "FW-TO+VB" : "V-Pres",
    "FW-UH" : "Interj",
    "FW-VB" : "V-Pres",
    "FW-VB+AT" : "V-Pres",
    "FW-VB+IN" : "V-Pres",
    "FW-VB+JJ" : "V-Pres",
    "FW-VB+PPO" : "V-Pres",
    "FW-VB+RP" : "V-Pres",
    "FW-VB+TO" : "V-Pres",
    "FW-VB+VB" : "V-Pres",
    "FW-VBD" : "V-Past",
    "FW-VBG" : "V-PaPart",
    "FW-VBG+TO" : "V-PaPart",
    "FW-VBN" : "V-PaPart",
    "FW-VBN+TO" : "V-PaPart",
    "FW-VBZ" : "V-Pres-3-Sg",
    "FW-WDT" : "Det-Int",
    "FW-WDT+BER" : "Det-Int",
    "FW-WDT+BER+PP" : "Det-Int",
    "FW-WDT+BEZ" : "Det-Int",
    "FW-WDT+DO+PPS" : "Det-Int",
    "FW-WDT+DOD" : "Det-Int",
    "FW-WDT+HVZ" : "Det-Int",
    "FW-WP$" : "Pron-Int",
    "FW-WPO" : "Pron-Int",
    "FW-WPS" : "Pron-Int",
    "FW-WPS+BEZ" : "Pron-Int",
    "FW-WPS+HVD" : "Pron-Int",
    "FW-WPS+HVZ" : "Pron-Int",
    "FW-WPS+MD" : "Pron-Int",
    "FW-WQL" : "Det-Rel",
    "FW-WRB" : "Adv-IntRel",
    "FW-WRB+BER" : "Adv-IntRel",
    "FW-WRB+BEZ" : "Adv-IntRel",
    "FW-WRB+DO" : "Adv-IntRel",
    "FW-WRB+DOD" : "Adv-IntRel",
    "FW-WRB+DOD*" : "Adv-IntRel",
    "FW-WRB+DOZ" : "Adv-IntRel",
    "FW-WRB+IN" : "Adv-IntRel",
    "FW-WRB+MD" : "Adv-IntRel",
    "HV" : "V-Pres-have",
    "HV*" : "V-Pres-have",
    "HV+TO" : "V-Pres-have",
    "HVD" : "V-Past-have",
    "HVD*" : "V-Past-have",
    "HVG" : "V-Pres-have",
    "HVN" : "V-Past-have",
    "HVZ" : "V-Pres-3-Sg-have",
    "HVZ*" : "V-Pres-3-Sg-have",
    "IN" : "Prep",
    "IN+IN" : "Prep",
    "IN+PPO" : "Prep",
    "JJ" : "Adj",
    "JJ$" : "Adj",
    "JJ+JJ" : "Adj",
    "JJ-HL" : "Adj",
    "JJ-TL" : "Adj",
    "JJ-TL-HL" : "Adj",
    "JJR" : "Adj-Comp",
    "JJR+CS" : "Adj-Comp",
    "JJS" : "Adj-Sup",
    "JJT" : "Adj-Sup",
    "MD" : "Aux",
    "MD*" : "Aux",
    "MD+HV" : "Aux",
    "MD+PPSS" : "Aux",
    "MD+TO" : "Aux",
    "NN" : "Nn-Sg",
    "NN$" : "Nn-Sg",
    "NN+BEZ" : "Nn-Sg",
    "NN+HVD" : "Nn-Sg",
    "NN+HVZ" : "Nn-Sg",
    "NN+IN" : "Nn-Sg",
    "NN+MD" : "Nn-Sg",
    "NN+NN" : "Nn-Sg",
    "NN-HL" : "Nn-Sg",
    "NN-TL" : "Nn-Sg",
    "NN-TL-HL" : "Nn-Sg",
    "NNP" : "Prop",
    "NNS" : "Nn-Pl",
    "NNS$" : "Nn-Pl",
    "NNS+MD" : "Nn-Pl",
    "NNS-TL" : "Nn-Pl",
    "NP" : "Prop",
    "NP$" : "Prop",
    "NP+BEZ" : "Prop",
    "NP+HVZ" : "Prop",
    "NP+MD" : "Prop",
    "NPS" : "Prop",
    "NPS$" : "Prop",
    "NR" : "Prop",
    "NR$" : "Prop",
    "NR+MD" : "Nn-Sg",
    "NRS" : "Nn-Pl",
    "OD" : "Ord",
    "PN" : "Pron",
    "PN$" : "Pron",
    "PN+BEZ" : "Pron",
    "PN+HVD" : "Pron",
    "PN+HVZ" : "Pron",
    "PN+MD" : "Pron",
    "PP$" : "Det-Poss",
    "PP$$" : "Pron",
    "PPL" : "Pron-Refl",
    "PPLS" : "Pron-Refl",
    "PPO" : "Pron",
    "PPS" : "Pron",
    "PPS+BEZ" : "Pron",
    "PPS+HVD" : "Pron",
    "PPS+HVZ" : "Pron",
    "PPS+MD" : "Pron",
    "PPSS" : "Pron",
    "PPSS+BEM" : "Pron",
    "PPSS+BER" : "Pron",
    "PPSS+BEZ" : "Pron",
    "PPSS+BEZ*" : "Pron",
    "PPSS+HV" : "Pron",
    "PPSS+HVD" : "Pron",
    "PPSS+MD" : "Pron",
    "PPSS+VB" : "Pron",
    "QL" : "Det",
    "QLP" : "Det",
    "RB" : "Adv",
    "RB$" : "Adv",
    "RB+BEZ" : "Adv",
    "RB+CS" : "Adv",
    "RBR" : "Adv-Comp",
    "RBR+CS" : "Adv-Comp",
    "RBT" : "Adv-Sup",
    "RN" : "Adv",
    "RP" : "Adv",
    "RP+IN" : "Adv",
    "TO" : "Part-Inf",
    "TO+VB" : "V-Pres",
    "UH" : "Interj",
    "VB" : "V-Pres",
    "VB+AT" : "V-Pres",
    "VB+IN" : "V-Pres",
    "VB+JJ" : "V-Pres",
    "VB+PPO" : "V-Pres",
    "VB+RP" : "V-Pres",
    "VB+TO" : "V-Pres",
    "VB+VB" : "V-Pres",
    "VBD" : "V-Past",
    "VBG" : "V-PaPart",
    "VBG+TO" : "V-PaPart",
    "VBN" : "V-PaPart",
    "VBN+TO" : "V-PaPart",
    "VBZ" : "V-Pres-3-Sg",
    "WDT" : "Det-Int",
    "WDT+BER" : "Det-Int",
    "WDT+BER+PP" : "Det-Int",
    "WDT+BEZ" : "Det-Int",
    "WDT+DO+PPS" : "Det-Int",
    "WDT+DOD" : "Det-Int",
    "WDT+HVZ" : "Det-Int",
    "WP$" : "Pron-Int",
    "WPO" : "Pron-Int",
    "WPS" : "Pron-Int",
    "WPS+BEZ" : "Pron-Int",
    "WPS+HVD" : "Pron-Int",
    "WPS+HVZ" : "Pron-Int",
    "WPS+MD" : "Pron-Int",
    "WQL" : "Det-Rel",
    "WRB" : "Adv-IntRel",
    "WRB+BER" : "Adv-IntRel",
    "WRB+BEZ" : "Adv-IntRel",
    "WRB+DO" : "Adv-IntRel",
    "WRB+DOD" : "Adv-IntRel",
    "WRB+DOD*" : "Adv-IntRel",
    "WRB+DOZ" : "Adv-IntRel",
    "WRB+IN" : "Adv-IntRel",
    "WRB+MD" : "Adv-IntRel",
    }

TAGSET = None


def initialize():

    global SENTENCE_BREAKER, POS_TAGGER, TAGSET

    try:
        import nltk, nltk.data
    except ImportError:
        note("No nltk support.")
        return False
    else:
        if SENTENCE_BREAKER is None:
            try:
                SENTENCE_BREAKER = nltk.data.load('tokenizers/punkt/english.pickle')
            except:
                try:
                    nltk.download("punkt")
                    SENTENCE_BREAKER = nltk.data.load('tokenizers/punkt/english.pickle')
                except:
                    note("Can't load nltk punkt tokenizer")
                    return False

        if POS_TAGGER is None:
            good_tagger_path = os.path.join(os.path.dirname(__file__), "TnTBrownTagger.pickle")
            if os.path.exists(good_tagger_path) and (os.path.getsize(good_tagger_path) > 1000):
                try:
                    POS_TAGGER = pickle.load(open(good_tagger_path, "rb"))
                    TAGSET = _BROWN_TAGS_TO_UPLIB_TAGS
                except:
                    note("Can't load TnT Brown tagger from %s", good_tagger_path)
            if POS_TAGGER is None:
                try:
                    POS_TAGGER = nltk.data.load('taggers/maxent_treebank_pos_tagger/english.pickle')
                    TAGSET = _UPENN_TAGS_TO_UPLIB_TAGS
                except:
                    try:
                        nltk.download("maxent_treebank_pos_tagger")
                        POS_TAGGER = nltk.data.load('taggers/maxent_treebank_pos_tagger/english.pickle')
                        TAGSET = _UPENN_TAGS_TO_UPLIB_TAGS
                    except:
                        note("Can't load nltk maxent_treebank_pos_tagger")
                        return False
        return (SENTENCE_BREAKER is not None) and (POS_TAGGER is not None)

def _figure_pos_label (position, ppos, tagset):
    pos = ppos[0]
    if (type(pos) == types.TupleType) and pos[1]:
        tag = pos[1]
        if tagset is _BROWN_TAGS_TO_UPLIB_TAGS:
            # remove some Brown features
            if tag.endswith("-HL") or tag.endswith("-TL") or tag.endswith("-NC"):
                tag = tag[:-3]
            if tag.startswith("FW-"):
                tag = tag[3:]
        r = tag and tagset.get(tag)
        if not r:
            note(3, "   unknown POS tag %s for %s @ %s.  Using 'Unknown'.", tag, ppos, position)
            r = "Unknown"
    else:
        note(3, "   odd value %s @ %s passed to _figure_pos_label", repr(ppos), position)
        r = "Unknown"
    return r or "Unknown"

def _clean_word (text):
    # strip off trailing or leading punctuation
    return text.strip(".:;?")

class NLTKPOSTagger (Ripper):

    def __init__(self, repo, tokenizer, tagger, tagset):
        Ripper.__init__(self, repo)
        self.sentence_tokenizer = tokenizer
        self.pos_tagger = tagger
        self.tagset = tagset

    def _sentences_for_doc (self, location, doc_id):
        ppath = os.path.join(location, "paragraphs.txt")
        cpath = os.path.join(location, "contents.txt")
        if (not os.path.exists(ppath)) or (not os.path.exists(cpath)):
            note("missing %s or %s", ppath, cpath)
            return None
        plist = read_paragraphs_file(ppath)
        tfile, charset, language = read_file_handling_charset_returning_bytes(cpath)
        sentences = []
        try:
            textoffset = tfile.tell()
            for i in range(len(plist)):
                para = plist[i]
                tfile.seek(para.first_byte + textoffset)
                if ((i + 1) < len(plist)):
                    ptext = tfile.read(plist[i+1].first_byte - para.first_byte)
                else:
                    ptext = tfile.read()
                if ptext:
                    ptext = re.sub(r'\s', ' ', ptext)
                    rawsentences = self.sentence_tokenizer.tokenize(ptext)
                    sentencestart = 0
                    for sentence in rawsentences:
                        # figure out where the sentence actually begins...
                        # just check the first 20 bytes...  Everybody assumes
                        # this stuff is context-free, but it's not.
                        for j in range(20):
                            if sentence == ptext[sentencestart + j:sentencestart + j + len(sentence)]:
                                sentencestart += j
                                #note("j for <<%s>> is %s (%s)", sentence, j, sentencestart)
                                break
                        if j >= 20:
                            raise ValueError("Can't find sentence <<%s>> in text of %s." % (sentence, doc_id))
                        sentences.append((para.pageno, (sentencestart == 0), para.first_byte + sentencestart, len(sentence.strip())))
                        sentencestart += len(sentence)
            return sentences
        finally:
            tfile.close()

    def rip (self, location, doc_id):

        note(2, "   figuring sentences and POS tags for %s...", doc_id)
        sentences = self._sentences_for_doc(location, doc_id)
        if not sentences:
            note("  No sentences in %s", doc_id)
            return

        wordboxes = dict(read_wordboxes_file(location))
        fp = open(os.path.join(location, "contents.ind"), "w")
        try:
            last_pageno = -1
            for pageno, is_start_of_para, first_byte, sentence_len in sentences:
                if pageno > last_pageno:
                    last_pageno = pageno
                    note(3, "    page %s", pageno)
                boxset = wordboxes[pageno]
                boxes = wordboxes_for_span(boxset, first_byte, first_byte + sentence_len)
                if not boxes:
                    note("   No wordboxes for span(%s, %s)",
                         first_byte, first_byte + sentence_len)
                    continue
                totalbox = None
                sentence_start = True
                for box in boxes:
                    if box.ends_word():
                        if totalbox:
                            totalbox.append(box)
                        else:
                            totalbox = [box]
                        text = ''.join([((x.has_hyphen() and x.text()[:-1]) or x.text()) for x in totalbox])
                        if not text:
                            totalbox = None
                            continue
                        if box is boxes[-1]:
                            cleantext = _clean_word(text)
                            if cleantext:
                                text = cleantext
                        pos = self.pos_tagger.tag([text])
                        pos = _figure_pos_label(totalbox[0].contents_offset(), pos, self.tagset)
                        for fragment in totalbox:
                            ftext = fragment.text()
                            if ftext and fragment.has_hyphen(): ftext = ftext[:-1] + "-"
                            nbytes = len(ftext.encode("UTF-8", "replace"))
                            fp.write("|%s|%s|%s|%s|%s|%s|%s|%s\n" % (
                                fragment.contents_offset(),
                                is_start_of_para and "1" or "0",
                                sentence_start and "1" or "0",
                                "0", "0", pos, nbytes,
                                ftext.encode("ASCII", "backslashreplace")
                                ))
                        totalbox = None
                        is_start_of_para = False
                        sentence_start = False
                    else:
                        if totalbox:
                            totalbox.append(box)
                        else:
                            totalbox = [box]
        finally:
            fp.close()                

    def requires(self):
        return "ParagraphRipper"

def rerip (repo, response, params):
    """Rerip one or more documents, re-running the sentence breaker and POS tagger, in a background thread.

    :param doc_id: the ID of the document or documents to re-rip.  One of either doc_id or coll must be specified.
    :type doc_id: UpLib document ID
    :param coll:  the ID of the collection to re-rip
    :type coll: UpLib collection ID
    :return: plain text list of docs re-ripped and rippers run on them
    :rtype: text/plain
    """
    global SENTENCE_BREAKER, POS_TAGGER, TAGSET

    if (SENTENCE_BREAKER is None) or (POS_TAGGER is None):
        if not initialize():
            raise Error("Can't initialize SENTENCE_BREAKER or POS_TAGGER")
    note("Re-ripping docs %s with SENTENCE_BREAKER %s, POS_TAGGER %s",
         params.get("coll") or params.get("doc_id"), SENTENCE_BREAKER, POS_TAGGER)
    rerip_generic (repo, response, params, NLTKPOSTagger(repo, SENTENCE_BREAKER, POS_TAGGER, TAGSET),
                   ["BboxesRipper"], background=True)

def rerip_all (repo, response, params):
    """Rerip all documents, re-running the sentence breaker and POS tagger, in a background thread.

    :return: plain text list of docs re-ripped and rippers run on them
    :rtype: text/plain
    """
    global SENTENCE_BREAKER, POS_TAGGER, TAGSET

    if (SENTENCE_BREAKER is None) or (POS_TAGGER is None):
        if not initialize():
            raise Error("Can't initialize SENTENCE_BREAKER or POS_TAGGER")
    note("Re-ripping all documents with SENTENCE_BREAKER %s, POS_TAGGER %s", SENTENCE_BREAKER, POS_TAGGER)
    rerip_generic (repo, response, params, NLTKPOSTagger(repo, SENTENCE_BREAKER, POS_TAGGER, TAGSET),
                   ["BboxesRipper"], docs=repo.generate_docs(), background=True)

def after_repository_instantiation (repo):

    try:
        import nltk
    except:
        note("Can't import NLTK")
        pass
    else:

        global SENTENCE_BREAKER, POS_TAGGER, TAGSET

        conf = configurator.default_configurator()
        enable_nltk = conf.get_bool("enable-nltk", True)
        if not enable_nltk:
            note("NLTK explicitly disabled")
            lookup_action = lambda fname: None
            return

        if not initialize():
            note("Can't initialize NLTKPOSTagger\n")
            return

        use_bad_tagger = conf.get_bool("use-default-nltk-tagger")
        if use_bad_tagger:
            try:
                POS_TAGGER = nltk.data.load('taggers/maxent_treebank_pos_tagger/english.pickle')
                TAGSET = _UPENN_TAGS_TO_UPLIB_TAGS
            except:
                try:
                    nltk.download("maxent_treebank_pos_tagger")
                    POS_TAGGER = nltk.data.load('taggers/maxent_treebank_pos_tagger/english.pickle')
                    TAGSET = _UPENN_TAGS_TO_UPLIB_TAGS
                except:
                    note("Can't load nltk maxent_treebank_pos_tagger")
                    return
        if (SENTENCE_BREAKER is not None) and (POS_TAGGER is not None):
            note(3, "nltk sentence-breaker is %s, tagger is %s", SENTENCE_BREAKER, POS_TAGGER)
            rippers = repo.rippers()
            for i in range(len(rippers)):
                if rippers[i].name() == "BboxesRipper":
                    rippers.insert(i, NLTKPOSTagger(repo, SENTENCE_BREAKER, POS_TAGGER, TAGSET))
                    break
