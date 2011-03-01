/*
  This file is part of the "UpLib 1.7.11" release.
  Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
  
  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/

package com.parc.uplib.readup.widget;

/**
 This class provides an interface to the text of a page, including the
 word bounding boxes for each word on the page image.  All bounding
 boxes are scaled to the pixel dimensions of the page thumbnail.
 <p>
 When text is mentioned, it is usually provided in the reading order of the page.
 In UpLib, this reading order is defined by the contents.txt file, and <i>reading order</i>
 is sometimes referred to as <i>contents.txt order</i>.  However, this class interface
 is general enough to support non-UpLib page text.
*/
public abstract class PageText {

    final static int ABBR = 1;
    final static int ABBR_MEAS = 2;
    final static int ADJ = 3;
    final static int ADJ_COMP = 4;
    final static int ADJ_SUP = 5;
    final static int ADV = 6;
    final static int ADV_COMP = 7;
    final static int ADV_INTREL = 8;
    final static int ADV_SUP = 9;
    final static int AUX = 10;
    final static int CONJ_COORD = 11;
    final static int CONJ_SUB = 12;
    final static int DET = 13;
    final static int DET_DEF = 14;
    final static int DET_INDEF = 15;
    final static int DET_INT = 16;
    final static int DET_INTREL = 17;
    final static int DET_REL = 18;
    final static int DET_PL = 19;
    final static int DET_POSS = 20;
    final static int DET_SG = 21;
    final static int INTERJ = 22;
    final static int LETTER = 23;
    final static int MARKUP_SGML = 24;
    final static int NN = 25;
    final static int NN_PL = 26;
    final static int NN_SG = 27;
    final static int NUM = 28;
    final static int NUM_MONEY = 29;
    final static int NUM_PERCENT = 30;
    final static int NUM_ROMAN = 31;
    final static int NUM_DATE = 32;
    final static int ONOM = 33;
    final static int ORD = 34;
    final static int PART_INF = 35;
    final static int PART_NEG = 36;
    final static int PART_POSS = 37;
    final static int PREP = 38;
    final static int PRON = 39;
    final static int PRON_INT = 40;
    final static int PRON_INTREL = 41;
    final static int PRON_REFL = 42;
    final static int PRON_REL = 43;
    final static int PROP = 44;
    final static int PROP_EMAIL = 45;
    final static int PROP_INIT = 46;
    final static int PROP_URL = 47;
    final static int PUNCT = 48;
    final static int PUNCT_CLOSE = 49;
    final static int PUNCT_MONEY = 50;
    final static int PUNCT_OPEN = 51;
    final static int PUNCT_SENT = 52;
    final static int TIME = 53;
    final static int V_INF = 54;
    final static int V_PAPART = 55;
    final static int V_PAST = 56;
    final static int V_PRES = 57;
    final static int V_PRES_3_SG = 58;
    final static int V_PRPART = 59;
    final static int TITLE = 60;

    static String[] POS_TagNames = new String[] {
        "Unknown",
	"Abbr",
	"Abbr-Meas",
	"Adj",
	"Adj-Comp",
	"Adj-Sup",
	"Adv",
	"Adv-Comp",
	"Adv-IntRel",
	"Adv-Sup",
	"Aux",
	"Conj-Coord",
	"Conj-Sub",
	"Det",
	"Det-Def",
	"Det-Indef",
	"Det-Int",
	"Det-IntRel",
	"Det-Rel",
	"Det-Pl",
	"Det-Poss",
	"Det-Sg",
	"Interj",
	"Letter",
	"Markup-SGML",
	"Nn",
	"Nn-Pl",
	"Nn-Sg",
	"Num",
	"Num-Money",
	"Num-Percent",
	"Num-Roman",
	"Num-Date",
	"Onom",
	"Ord",
	"Part-Inf",
	"Part-Neg",
	"Part-Poss",
	"Prep",
	"Pron",
	"Pron-Int",
	"Pron-IntRel",
	"Pron-Refl",
	"Pron-Rel",
	"Prop",
	"Prop-Email",
	"Prop-Init",
	"Prop-URL",
	"Punct",
	"Punct-Close",
	"Punct-Money",
	"Punct-Open",
	"Punct-Sent",
	"Time",
	"V-Inf",
	"V-PaPart",
	"V-Past",
	"V-Pres",
	"V-Pres-3-Sg",
        "V-PrPart",
        "Title",
    };

    static String[] POS_Explanations = new String[] {
	null,
	"abbreviation that is not a title",
	"abbreviation of measure",
	"adjective",
	"comparative adjective",
	"superlative adjective",
	"adverb",
	"comparative adverb",
	"wh-adverb",
	"superlative adverb",
	"auxiliary or modal",
	"coordinating conjunction",
	"subordinating conjunction",
	"invariant determiner (singular or plural)",
	"definite determiner",
	"indefinite determiner",
	"interrogative determiner",
	"interrogative or relative determiner",
	"relative determiner",
	"plural determiner",
	"possessive determiner",
	"singular determiner",
	"interjection",
	"letter",
	"SGML markup",
	"invariant noun",
	"plural noun",
	"singular noun",
	"number or numeric expression",
	"monetary amount",
	"percentage",
	"roman numeral",
	"numeric date",
	"onomatopoeia",
	"ordinal number",
	"infinitive marker",
	"negative particle",
	"possessive marker",
	"preposition",
	"pronoun",
	"wh-pronoun",
	"wh-pronoun",
	"reflexive pronoun",
	"relative pronoun",
	"name of a person or thing",
	"email address",
	"initial",
	"web browser URL",
	"other punctuation",
	"closing punctuation",
	"currency punctuation",
	"opening punctuation",
	"sentence-ending punctuation",
	"time expression",
	"infinitive form of verb",
	"verb, past participle",
	"verb, past tense",
	"verb, present tense or infinitive",
	"verb, present tense, 3rd person singular",
        "verb, present participle",
        "title of address",
    };
    static String[] POS_Examples = new String[] {
	null,
	"i.e.",
	"oz.",
	"big",
	"bigger",
	"biggest",
	"quickly",
	"earlier",
	"how, when",
	"fastest",
	"will, could",
	"and",
	"if, that",
	"some, no",
	"the",
	"a",
	"what",
	"whose",
	"whatsoever",
	"these, those",
	"her, his, its",
	"this, that",
	"oh, hello",
	"a, b, c",
	"<TITLE>",
	"sheep",
	"computers",
	"table",
	"40.5",
	"$12.55",
	"12%",
	"XVII, xvii",
	"2004",
	"meow",
	"first, 10th",
	"to",
	"not",
	"'s, '",
	"in, on, to",
	"he",
	"who",
	"who",
	"himself",
	"who, whom, that, which",
	"Graceland, Aesop",
	"lxsupport@inxight.com",
	"J.",
	"http://www.inxight.com",
	"- ; /",
	") ] }",
	"$ £ ´",
	"( [ {",
	". ! ?",
	"9:00",
	"be",
	"understood",
	"ran",
	"walk",
	"runs",
        "walking",
        "Mister",
    };

    /**
       This class provides an abstraction of a word bounding box.
       The dimensions of the box are in pixels, in the space of the
       page thumbnail image.
    */
    public abstract class WordBox extends java.awt.Rectangle {

        public static final int FLAG_FIXEDWIDTH_FONT = 0x80;
        public static final int FLAG_SERIF_FONT = 0x40;
        public static final int FLAG_SYMBOLS_FONT = 0x20;
        public static final int FLAG_ITALIC = 0x10;
        public static final int FLAG_BOLD = 0x8;
        public static final int FLAG_END_OF_LINE = 0x4;
        public static final int FLAG_END_OF_WORD = 0x2;
        public static final int FLAG_ENDING_HYPHEN = 0x1;

        /**
           @return the byte position of the first character of the text of this word relative to
           the beginning of the page's representation (e.g., UTF-8).
        */
        public abstract int contentsPosition();

        /**
           @return the length in bytes (e.g., UTF-8) of the text in this word box, including any trailing punctuation.
        */
        public abstract int contentsLength();
        
        /**
         * @return the character position of the first character of the text of this work relative
         * to the beginning of the Java String representation of the page
         */
        public abstract int stringPosition();
        
        /**
         * @return the length in characters of the text in this word box, including any trailing punctuation.
         */
        public abstract int stringLength();
        
        /**
         * setSentenceNumber()
         * Called by a sentence breaking algorithm to associate this WordBox with a particular sentence
         */
        public abstract void setSentenceNumber(int sentence_number_p);
        
        /**
         * getSentenceNumber()
         * @return the sentence number set in the most recent call to setSentenceNumber() or -1 if
         * no such call has been made
         */
        public abstract int getSentenceNumber();

        /**
           @return the text associated with the word box, including any trailing punctuation.
        */
        public abstract String getText();

        /**
           @return the text associated with the word box, with any trailing punctuation trimmed off.
        */
        public abstract String getTrimmedText ();

        /**
           @return true if last word on line
        */
        public abstract boolean endOfLine();

        /**
           @return true if last word on line
        */
        public abstract boolean isBold();

        /**
           @return true if last word on line
        */
        public abstract boolean isItalic();

        /**
           @return the font size of the word box
        */
        public abstract float fontSize ();

        /**
           @return true if this is the first wordbox in a paragraph, false if not or not known
        */
        public abstract boolean beginsParagraph();

        /**
           @return true if this is the first wordbox in a sentence, false if not or not known
        */
        public abstract boolean beginsSentence();

        /**
           @return true if this is the first wordbox in a phrase, false if not or not known
        */
        public abstract boolean beginsPhrase();

        /**
           @return POS code if known, 0 otherwise.
        */
        public abstract int partOfSpeechCode();

        /**
           @return POS tag-name if known, null otherwise.
        */
        public String partOfSpeechName() {
            int code = partOfSpeechCode();
            if (code < 0 || code > POS_TagNames.length)
                return null;
            else
                return POS_TagNames[code];
        }

        /**
           @return POS description if known, null otherwise.
        */
        public String partOfSpeechDescription() {
            int code = partOfSpeechCode();
            // System.err.println("part-of-speech code for '" + this.getText() + "' is " + code + " (" + POS_TagNames[code] + ")");
            if (code < 1 || code > POS_Explanations.length)
                return null;
            else
                return POS_Explanations[code];
        }

        /**
           @return the PageText this wordbox is from
        */
        public PageText getPageText () { return PageText.this; }
    };

    /**
       Returns the set of word boxes for all the words on this page, sorted according to their
       reading order.
       @return a SortedSet of WordBox instances
    */
    public abstract java.util.SortedSet getWordBoxes ();

    /**
       Given a byte position in the text of the page, return the word at that position or immediately
       after it.  May return null if there is no text at the given position.
       @param text_position the byte position in the page text
       @return the WordBox, or null
    */
    public abstract WordBox getWordBox (int text_position);
    
    /**
       Given a byte position in the text of the page, return the word at that position or the
       next wordbox after it.  May return null if there is no text after the position.
       @param text_position the byte position in the page text
       @return the WordBox, or null
    */
    public abstract WordBox getNextWordBox (int text_position);
    
    /**
       Given a point on the page thumbnail image, return the word around that point, or null if that point is
       not enclosed by a word box.
       @param position the x,y position on the page thumbnail
       @return the WordBox for the enclosing word, or null if none
    */
    public abstract WordBox getWordBox (java.awt.Point position);

    /**
       Given a point on the page thumbnail image, return the word around that point,
       or the nearest wordbox if that point is not enclosed by a word box.
       @param position the x,y position on the page thumbnail
       @return the WordBox for the enclosing word, or null if none
    */
    public abstract WordBox getNearestWordBox (java.awt.Point position);

    /**
       Given two byte positions in the page text, return a list of all the word boxes
       on this page between those positions, in reading order.
       @param   start a byte position page text.  Must be non-negative.
       @param   end a byte position in page text.  Must be non-negative.
       @return a list of WordBox instances.  If <code>start</code> is greater than the length of the
       page text, the list will be empty.
    */
    public abstract java.util.List getWordBoxes (int start, int end);

    /**
       Given a string, return a list of all the word box sequences
       on this page which match that string, in reading order.
       @param   to_match the string to match.  Whitespace characters all match each other.
       @return a list of lists of WordBox instances.  The list may be empty.
    */
    public abstract java.util.List getMatchingStrings (String to_match);
    
    /**
       Given a string, return a list of all the word box sequences
       on this page which match that string, ignoring case, in reading order.
       @param   to_match the string to match.  Whitespace characters all match each other.
       @return a list of lists of WordBox instances.  The list may be empty.
    */
    public abstract java.util.List getMatchingStringsIgnoreCase (String to_match);
    
    /**
     Given a string, return a list of all the word box sequences
     on this page which match that string, ignoring case, in reading order. Matches must
     be surrounded by punctuation or whitespace to be a true match (i.e., a way to avoid substrings)
     @param   to_match the string to match.  Whitespace characters all match each other.
     @return a list of lists of WordBox instances.  The list may be empty.
     */
    public abstract java.util.List getMatchingStringsExactMatchIgnoreCase (String to_match);


    /**
       Given a wordbox to start with, return an iterator for any wordboxes following
       the box in the text of the document.  If wordbox is null, the iterator begins
       at the first wordbox of the pagetext.
       @param   wordbox the first wordbox to exclude, or null if all wordboxes are wanted
       @return  it an iterator over the sequence of wordboxes
    */
    public abstract java.util.Iterator getWordBoxes (WordBox start);       

    /**
       Get the byte position in the document's text where the text of this
       page begins.
       @return the byte position of the first byte of this page
    */
    public abstract int getTextLocation ();
      

    /**
       Returns the raw text bytes for this page, a UTF-8 encoding of a string.
       @return the UTF-8 text
    */
    public abstract byte[] getTextBytes ();

    /**
       Returns the text for this page.
       @return the String for the page.  May be zero-length.
    */
    public abstract String getText ();

    /**
       Given a byte position in the page text, returns the text after that position, if any.
       @param start a byte position in the page text
       @return the text, or null
    */
    public abstract String getText (int start);

    /**
       Given two byte positions in the page text, returns the text between
       those two positions (if any).
       @param start a non-negative byte position in the page text
       @param end a non-negative byte position in the page text
       @return the text, or null
    */
    public abstract String getText (int start, int end);

    /**
       Returns the text of the word at the given position, or null if no word is
       at that position.
       @param position an x,y position on the page thumbnail
       @return the String, or null
    */
    public abstract String getWord (java.awt.Point position);

    /**
       Returns a list of all the WordBox instances on the page the words of which
       begin with the specified prefix.
       @return a List of WordBox lists
    */
    public abstract java.util.List getPrefixWords (String prefix);

    /**
       @return the page index of this page in the document
    */
    public abstract int getPageIndex ();

}
