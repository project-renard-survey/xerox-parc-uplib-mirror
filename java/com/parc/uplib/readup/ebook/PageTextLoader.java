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

package com.parc.uplib.readup.ebook;

import javax.swing.JApplet;
import java.applet.*;
import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.*;
import java.awt.datatransfer.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.border.*;
import javax.imageio.*;
import java.text.*;
import java.net.*;
import java.util.zip.*;

import com.parc.uplib.readup.widget.CachingLoader;
import com.parc.uplib.readup.widget.ResourceLoader;
import com.parc.uplib.readup.widget.PageText;
import com.parc.uplib.readup.widget.ImageHolder;
import com.parc.uplib.readup.uplibbinding.MXCIFTree;

public class PageTextLoader extends CachingLoader {

    private URL repo_url;
    private String repo_password;

    public PageTextLoader () {
        super(null, "page text");
    }

    public void setCookie (String cookie) {
    }

    public Object getResource(String document_id, int pageno, int selector)
        throws IOException {
        
        String the_url = null;

        if (pageno < 0)
            throw new ResourceLoader.ResourceNotFound("invalid page number " + pageno + " specified.");

        Object o = super.getResource(document_id, pageno, selector);
        if (o != null) {
            // System.err.println("loaded page text " + document_id + "/" + pageno + "/" + selector + " from cache");
            return o;
        }

        the_url = "/thumbnails/" + Integer.toString(pageno+1) + ".bboxes";
        InputStream inps = PageTextLoader.class.getResourceAsStream(the_url);
        if (inps != null) {
            try {
                try {
                    UpLibPageText pt = UpLibPageText.read(pageno, inps);
                    if (pt==null){
                        System.err.println("fetched page text " + document_id + "/" + pageno +
                                           " but the data is NULL");
                    } else {
                        System.err.println("fetched page text " + document_id + "/" + pageno);
                    }
                    super.cacheResource(document_id, pageno, selector, pt);
                    return pt;
                } finally {
                    inps.close();
                }
            } catch (java.io.IOException ioe) {
        	String msg = "Couldn't read PageText " + document_id + "/" + pageno + " from " + the_url + ": " + ioe;
                System.err.println(msg);
                //throw ioe;
                byte[] nullData = new byte[0];
        	int nullPageStart = 0;
        	UpLibPageText pt = new UpLibPageText(nullData, nullPageStart, pageno);
                return pt;
            } catch (java.util.zip.DataFormatException dfe) {
        	String msg = "Pagetext data for " + document_id + "/" + pageno + " not in valid zip compression format:  " + dfe;
                System.err.println(msg);
                //throw new ResourceLoader.CommunicationFailure(msg);
                byte[] nullData = new byte[0];
        	int nullPageStart = 0;
        	UpLibPageText pt = new UpLibPageText(nullData, nullPageStart, pageno);
                return pt;
            } catch (Exception e) {
        	String msg = "UpLibPageTextLoader.getResource got unexpected Exception.";
        	msg += "\nException = ["+e.toString()+"] on page "+document_id+"/"+pageno+"";
        	System.err.println(msg);
                e.printStackTrace(System.err);
        	//throw new IOException(msg);
        	byte[] nullData = new byte[0];
        	int nullPageStart = 0;
        	UpLibPageText pt = new UpLibPageText(nullData, nullPageStart, pageno);
            }
        }
        return null;
    }

    public static class UpLibPageText extends PageText implements Serializable {

        private byte[] pagetext;
        private int pagestart;
        public int current_word_count;
        private int our_page;

        private int maxwidth;
        private int maxheight;

        // this index maps word positions to word bboxes
        private TreeSet text_position_index;

        // and a comparator...
        private class TextPositionComparator implements Comparator, Serializable {
            public TextPositionComparator () {
            }

            // we compare the ends of the text span, so that we can use tailSet() to
            // get the subtree which begins with the first bbox after any point

            public int compare (Object o1, Object o2) {
                UpLibWordBox b1 = (UpLibWordBox) o1;
                UpLibWordBox b2 = (UpLibWordBox) o2;
                return ((b1.content_position + b1.textlen - 1) - (b2.content_position + b2.textlen - 1));
            }
            public boolean equal (Object o1, Object o2) {
                UpLibWordBox b1 = (UpLibWordBox) o1;
                UpLibWordBox b2 = (UpLibWordBox) o2;
                return ((b1.content_position + b1.textlen - 1) == (b2.content_position + b2.textlen - 1));
            }
        }


        // this maintains a positional layout of wordboxes
        private MXCIFTree xy_position_index;


        // an index which keeps wordboxes sorted by alphabetical order
        private TreeSet alphabetical_index;

        // and the comparator...
        private class AlphabeticalComparator implements Comparator, Serializable {
            public AlphabeticalComparator () {
            }

            public int compare (Object o1, Object o2) {
                UpLibWordBox b1 = (UpLibWordBox) o1;
                UpLibWordBox b2 = (UpLibWordBox) o2;
                int r = b1.trimmed_text.compareToIgnoreCase(b2.trimmed_text);
                if (r != 0)
                    return r;
                else
                    return ((b1.content_position + b1.textlen - 1) - (b2.content_position + b2.textlen - 1));
            }

            public boolean equal (Object o1, Object o2) {
                return (compare(o1, o2) == 0);
            }
        }

        public String toString () {
            return "<PageText " + our_page + " " + pagestart + "-" + (pagestart + pagetext.length) + " " + Integer.toHexString(hashCode()) + ">";
        }

        public class UpLibWordBox extends PageText.WordBox implements Serializable {

            int         char_count = 0;
            int         textlen = 0;    /* in bytes */
            int         font_type = 0;
            float       font_size = 0;
            int         content_position = 0;
            int			string_position = 0;
            boolean     fixed_width = false;
            boolean     serif_font = false;
            boolean     symbolic_font = false;
            boolean     italic = false;
            boolean     bold = false;
            boolean     endsline = false;
            boolean     endsword = false;
            boolean     inserted_hyphen = false;
            boolean     begins_paragraph = false;
            boolean     begins_sentence = false;
            boolean     begins_phrase = false;
            int         part_of_speech_code = 0;
            String      trimmed_text = null;
            int			sentence_number = -1;
            

            public UpLibWordBox (int ulx, int uly, int lrx, int lry,
                                 int chars, float font_size_p,
                                 boolean fixed_width_p, boolean serif_p,
                                 boolean symbolic_p, boolean italic_p, boolean bold_p,
                                 boolean endsline_p, boolean endsword_p, boolean inserted_hyphen_p,
                                 int starts_code, int pos_code,
                                 int textlen_p, int content_position_p, int string_position_p) {

                x = ulx;
                y = uly;
                width = (lrx - ulx);
                height = (lry - uly);
                char_count = chars;
                font_size = font_size_p;
                fixed_width = fixed_width_p;
                serif_font = serif_p;
                symbolic_font = symbolic_p;
                italic = italic_p;
                bold = bold_p;
                endsword = endsword_p;
                endsline = endsline_p;
                inserted_hyphen = inserted_hyphen_p;
                content_position = content_position_p;
                string_position = string_position_p;
                textlen = textlen_p;
                if (starts_code == 3) {
                    begins_paragraph = true;
                    begins_sentence = true;
                    begins_phrase = true;
                } else if (starts_code == 2) {
                    begins_sentence = true;
                    begins_phrase = true;
                } else if (starts_code == 1) {
                    begins_phrase = true;
                }
                part_of_speech_code = pos_code;                    
            }

            public UpLibWordBox (int text_position) {
                content_position = text_position;
                textlen = 1;
            }
            
            public UpLibWordBox (Point p) {
                x = p.x;
                y = p.y;
            }

            public UpLibWordBox (String s) {
                trimmed_text = s;
            }

            public String getText () {

                String s = null;
                try {
                    s = new String(pagetext, content_position, textlen, "UTF-8"); 
                } catch (UnsupportedEncodingException e) {
                    System.err.println("Java doesn't support UTF-8 charset encoding!");
                    return null;
                }
                int chars = (inserted_hyphen ? (char_count - 1) : char_count);
                return s.substring(0, chars);
            }

            public int contentsPosition () {
                return content_position;
            }

            public int contentsLength () {
                return textlen;
            }
            
            public int stringPosition() {
            	// position in the Java String that would result from new String(pagetext, 0, pagetext.length, "UTF-8")
            	return string_position;
            }
            
            public int stringLength() {
            	String wordBoxText = null;
            	try {
            		wordBoxText = new String(pagetext, content_position, textlen, "UTF-8");
            	} catch (UnsupportedEncodingException e) {
            		String msg = "Java does not support the UTF-8 encoding!";
            		throw new RuntimeException(msg);
            	}
            	return wordBoxText.length();
            }
            
            public void setSentenceNumber(int sentence_number_p) {
            	this.sentence_number = sentence_number_p;
            }
            
            public int getSentenceNumber() {
            	return this.sentence_number;
            }

            public String getTrimmedText () {

                if (trimmed_text == null) {

                    int front, back;
                    String s = getText();
                    for (front = 0;  front < s.length();  front++) {
                        if (Character.isLetterOrDigit(s.charAt(front)))
                            break;
                    }
                    for (back = s.length();  back > front;  back--) {
                        if (Character.isLetterOrDigit(s.charAt(back-1)))
                            break;
                    }
                    trimmed_text = s.substring(front, back);
                }
                return trimmed_text;
            }

            public boolean isBold () {
                return bold;
            }

            public boolean isItalic () {
                return italic;
            }

            public boolean endOfLine () {
                return endsline;
            }
            
            public boolean endOfWord () {
            	return this.endsword;   
            }

            public float fontSize () {
                return font_size;
            }

            public int partOfSpeechCode() {
                return part_of_speech_code;
            }

            public boolean beginsParagraph () {
                return begins_paragraph;
            }

            public boolean beginsSentence() {
                return begins_sentence;
            }

            public boolean beginsPhrase() {
                return begins_phrase;
            }
        }


        public UpLibPageText (byte[] pt, int page_start_p, int page_no) {

            pagetext = pt;
            pagestart = page_start_p;
            text_position_index = new TreeSet(new TextPositionComparator());
            xy_position_index = null;
            alphabetical_index = new TreeSet(new AlphabeticalComparator());
            maxwidth = 0;
            maxheight = 0;
            our_page = page_no;
        }

        private void addBox (UpLibWordBox box) {

            String key = box.getTrimmedText();

            text_position_index.add(box);
            alphabetical_index.add(box);
            if ((box.x + box.width) > maxwidth)
                maxwidth = box.x + box.width;
            if ((box.y + box.height) > maxheight)
                maxheight = box.y + box.height;

        }

        private void allBoxesAdded () {
            xy_position_index = new MXCIFTree(new Rectangle(0, 0, maxwidth, maxheight));
            Iterator i = text_position_index.iterator();
            // System.err.println("maxwidth is " + maxwidth + ", maxheight is " + maxheight + ", boxcount is " + text_position_index.size());
            while (i.hasNext()) {
                UpLibWordBox b = (UpLibWordBox) (i.next());
                try {
                    if (b.getHeight() > 0 && b.getWidth() > 0)
                        xy_position_index.insert(b);
                } catch (Exception x) {
                    System.err.println("Exception adding wordbox " + b);
                    x.printStackTrace(System.err);
                }
            }
        }

        public SortedSet getWordBoxes () {
            return (SortedSet) text_position_index;
        }

        public void setText (byte[] t) {
            pagetext = t;
        }

        public String getText (UpLibWordBox box) {
            return box.getText();
        }

        public PageText.WordBox getWordBox (int text_position) {
            UpLibWordBox pobj = new UpLibWordBox (text_position);

            if (text_position_index.isEmpty())
                return null;

            SortedSet ts = text_position_index.tailSet(pobj);

            if (ts.isEmpty())
                return null;
            else
                return ((PageText.WordBox) (ts.first()));
        }

        public PageText.WordBox getNextWordBox (int text_position) {
            return getWordBox(text_position);
        }

        public PageText.WordBox getWordBox (Point position) {
            if (xy_position_index==null) {
            	String msg = "Warning: UpLibPageTextLoader was called at a time when";
            	msg += " xy_position_index did not yet exist.";
            	System.err.println(msg);
            	return null;
            }
            java.util.List rects = xy_position_index.intersect(position);
            if (rects.size() > 0)
                return ((PageText.WordBox) rects.get(0));
            else
                return null;
        }

        public PageText.WordBox getNearestWordBox(Point p) {
            if (xy_position_index==null) {
            	// This can happen if UpLibPageTextLoader finds no word boxes file
            	// for the current page
            	return null;
            }
            return (PageText.WordBox) xy_position_index.nearest(p);
        }


        public java.util.List getWordBoxes (int cpos1, int cpos2) {
            if (!text_position_index.isEmpty()) {
                if (cpos1 > cpos2) {
                    int tmp = cpos1;
                    cpos1 = cpos2;
                    cpos2 = cpos1;
                }
                Vector v = new Vector();
                UpLibWordBox pobj1 = new UpLibWordBox(cpos1);
                UpLibWordBox pobj2 = new UpLibWordBox(cpos2);
                WordBox last = getWordBox(cpos2);
                SortedSet s = text_position_index.subSet(pobj1, pobj2);
                Iterator i = s.iterator();
                while (i.hasNext()) {
                    v.add((WordBox) (i.next()));
                }
                if ((last != null) && (!s.contains(last)))
                    v.add(last);
                return (java.util.List) v;
            };
            return (java.util.List) new ArrayList();
        }

        public java.util.List getWordBoxes (Point pos1, Point pos2) {

            Point p1 = pos1;
            Point p2 = pos2;
            UpLibWordBox pobj1 = (UpLibWordBox) getNearestWordBox(pos1);
            UpLibWordBox pobj2 = (UpLibWordBox) getNearestWordBox(pos2);

            if (pobj1 == null && pobj2 == null)
                return null;

            if (pobj1 == null || ((pobj2 != null) && (pobj2.content_position < pobj1.content_position))) {
                UpLibWordBox tmp = pobj1;
                pobj1 = pobj2;
                pobj2 = tmp;
                Point tmpp = p1;
                p1 = p2;
                p2 = tmpp;
            }

            int cpos1 = pobj1.content_position;
            int cpos2 = (pobj2 == null) ? pagetext.length : pobj2.content_position;
            if (pobj2 != null && pobj2.contains(p2))
                cpos2 += pobj2.textlen;

            return getWordBoxes(cpos1, cpos2);
        }

        public java.util.List getMatchingStrings (String to_match) {
            Vector retval = new Vector();
            byte[] search_bytes = null;
            int search_bytes_len = 0;
            try {
                search_bytes = to_match.getBytes("UTF-8");
                search_bytes_len = search_bytes.length;
            } catch (UnsupportedEncodingException uee) {
                System.err.println("Impossible exception occurred!  " + uee);
                return retval;
            }
            int i, j;
            for (i = 0;  i < (pagetext.length - search_bytes.length); i++) {
                for (j = 0;  j < search_bytes.length;  j++) {
                    if (Character.isWhitespace((char) (0x0000 | search_bytes[j])) &&
                        Character.isWhitespace((char) (0x0000 | pagetext[i + j])))
                        continue;
                    if (search_bytes[j] != pagetext[i + j]) {
                        break;
                    }
                }
                if (j >= search_bytes.length) {
                    // we've found a match, so break
                    retval.add(getWordBoxes(i, i + search_bytes.length));
                }
                i = i + j;
            }
            return retval;
        }
        
        public java.util.List getMatchingStringsIgnoreCase (String to_match) {
            Vector retval = new Vector();
            byte[] search_bytes_lower = null;
            byte[] search_bytes_upper = null;
            int search_bytes_len = 0;
            try {
                search_bytes_lower = to_match.toLowerCase().getBytes("UTF-8");
                search_bytes_upper = to_match.toUpperCase().getBytes("UTF-8");
                search_bytes_len = search_bytes_lower.length;
            } catch (UnsupportedEncodingException uee) {
                System.err.println("Impossible exception occurred!  " + uee);
                return retval;
            }
            int i, j;
            for (i = 0;  i < (pagetext.length - search_bytes_lower.length); i++) {
                for (j = 0;  j < search_bytes_lower.length;  j++) {
                    if (Character.isWhitespace((char) (0x0000 | search_bytes_lower[j])) &&
                        Character.isWhitespace((char) (0x0000 | pagetext[i + j])))
                        continue;
                    byte pageTextIPlusJ = pagetext[i+j];
                    if (search_bytes_lower[j] != pageTextIPlusJ && search_bytes_upper[j] != pageTextIPlusJ) {
                        break;
                    }
                }
                if (j >= search_bytes_lower.length) {
                    // we've found a match, so break
                    retval.add(getWordBoxes(i, i + search_bytes_lower.length));
                }
                i = i + j;
            }
            return retval;
        }

        public java.util.List getMatchingStringsExactMatchIgnoreCase (String to_match) {
            Vector retval = new Vector();
            byte[] search_bytes_lower = null;
            byte[] search_bytes_upper = null;
     		String punctString = "\n\r\f\t :;,.()[]{}\"\'\\/?!";

    		try {
                search_bytes_lower = to_match.toLowerCase().getBytes("UTF-8");
                search_bytes_upper = to_match.toUpperCase().getBytes("UTF-8");
             } catch (UnsupportedEncodingException uee) {
                System.err.println("Impossible exception occurred!  " + uee);
                return retval;
            }
            int searchByteLen = search_bytes_lower.length;
            int i, j;
            for (i = 0;  i < (pagetext.length - searchByteLen); i++) {
                for (j = 0;  j < searchByteLen;  j++) {
                    byte thisByteLower = search_bytes_lower[j];
                    byte pageTextIPlusJ = pagetext[i+j];
                    if (Character.isWhitespace((char) (0x0000 | thisByteLower)) &&
                        Character.isWhitespace((char) (0x0000 | pageTextIPlusJ)))
                        continue;
                    byte thisByteUpper = search_bytes_upper[j];
                    if (thisByteLower != pageTextIPlusJ && thisByteUpper != pageTextIPlusJ) {
                        break;
                    }
                }
                if (j >= searchByteLen) {
                    // we've possibly found a match
                	String before, after;
                	if (i-1 >= 0) {
	                	byte[] beg = {this.pagetext[i-1]};
	                	before = new String(beg);
                	} else {
                		before = " ";
                	}
                	
                	if (i + searchByteLen + 1 < pagetext.length) {
	                	byte[] end = {this.pagetext[i + searchByteLen]};
	                	after = new String(end);
                	} else {
                		after = " ";
                	}
                	if (punctString.indexOf(before) >= 0 && punctString.indexOf(after) >= 0) {
                		retval.add(getWordBoxes(i, i + searchByteLen));
                	}        
                }
                i = i + j;
            }
            return retval;
        }

        public Iterator getWordBoxes (PageText.WordBox start) {

            if (start == null)
                return text_position_index.iterator();
            else {
                Iterator t = text_position_index.tailSet(start).iterator();
                if (t.hasNext())
                    t.next();
                return t;
            }
        }

        public int getTextLocation () {
            return pagestart;
        }

        public byte[] getTextBytes () {
            return pagetext;
        }

        public String getText () {
            String s = null;
            try {
                s = new String(pagetext, 0, pagetext.length, "UTF-8");
            } catch (UnsupportedEncodingException e) {
                System.err.println("Java doesn't support UTF-8 charset!");
            }
            return s;
        }

        public String getText (int content_position) {
            String s = null;
            if ((content_position >= 0) && (content_position < pagetext.length)) {
                try {
                    s = new String(pagetext, content_position, pagetext.length - content_position, "UTF-8");
                } catch (UnsupportedEncodingException e) {
                    System.err.println("Java VM doesn't support UTF-8 charset!");
                }
            }
            return s;
        }

        public String getText (int content_position1, int content_position2) {
            String s = null;
            if ((content_position2 > content_position1) &&
                (content_position1 < pagetext.length) &&
                (content_position1 >= 0) && (content_position2 >= 0)) {
                try {
                    s = new String(pagetext, content_position1, content_position2 - content_position1, "UTF-8");
                } catch (UnsupportedEncodingException e) {
                    System.err.println("Java VM doesn't support UTF-8 charset!");
                }
            }
            return s;
        }

        public String getWord (Point position) {
            UpLibWordBox b = (UpLibWordBox) getWordBox(position);
            if (b != null)
                return b.getText();
            else
                return null;
        }

        public java.util.List getPrefixWords (String prefix) {
            Vector v = new Vector();
            String prefixLower = prefix.toLowerCase();

            if (alphabetical_index.isEmpty())
                return (java.util.List) v;

            UpLibWordBox pobj = new UpLibWordBox(prefix);
            Iterator i = alphabetical_index.tailSet(pobj).iterator();

            while (i.hasNext()) {
                UpLibWordBox b = (UpLibWordBox) i.next();
                if (b.trimmed_text.toLowerCase().startsWith(prefixLower)) {
                    v.add(b);
                }
            }
            return (java.util.List) v;
        }

        public int getPageIndex () {
            return our_page;
        }

        private UpLibWordBox addBoxFromRecord (byte[] record, int byte_count, int last_contents_position, int string_position)
            throws DataFormatException, IOException {
            if (byte_count != 16)
                throw new DataFormatException("bbox record should be exactly 16 bytes");
            DataInputStream ds = new DataInputStream(new ByteArrayInputStream(record, 0, byte_count));
            int upperLeftX = ds.readUnsignedShort();
            int upperLeftY = ds.readUnsignedShort();
            int lowerRightX = ds.readUnsignedShort();
            int lowerRightY = ds.readUnsignedShort();
            int char_count = ds.readUnsignedByte();
            float font_size = (float) (ds.readUnsignedByte() / 2.0);
            int flags = ds.readUnsignedByte();
            int textlen = ds.readUnsignedByte();
            int unused = ds.readUnsignedByte();
            int poscodes = ds.readUnsignedByte();
            int contents_position = ds.readUnsignedShort();
            // System.err.println("" + ulx + "," + uly + " - " + lrx + "," + lry); 
            // System.err.println("char_count " + char_count + ", contents_position is " + contents_position);
            boolean badBox = false;
            if (lowerRightY < upperLeftY) {
                badBox = true;
                int tempY = lowerRightY;
                lowerRightY = upperLeftY;
                upperLeftY = tempY;
            }
            if (lowerRightX < upperLeftX) {
            	badBox = true;
            	int tempX = lowerRightX;
            	lowerRightX = upperLeftX;
            	upperLeftX = tempX;
            }
            if (badBox) {
                System.err.println("Bad wordbox " + (lowerRightX - upperLeftX) + "x" + (lowerRightY - upperLeftY) + "+" +
                		upperLeftX + "+" + upperLeftY + ": " + char_count + "@" + contents_position);
                //return null;
            }
        	if (last_contents_position > contents_position) {
        		String boxText = new String(pagetext, contents_position, textlen, "UTF-8");
        		String msg = "PageTextLoader.UpLibPageText.addBoxFromRecord.  last_contents_position = ["+
        		last_contents_position+"], contents_position = ["+contents_position+"], text = ["+boxText+"]";
        		System.err.println(msg);
        	}

            UpLibWordBox newBox = new UpLibWordBox (upperLeftX, upperLeftY, lowerRightX, lowerRightY, char_count, font_size,
                                     (flags & 0x80) != 0,
                                     (flags & 0x40) != 0,
                                     (flags & 0x20) != 0,
                                     (flags & 0x10) != 0,
                                     (flags & 0x08) != 0,
                                     (flags & 0x04) != 0,
                                     (flags & 0x02) != 0,
                                     (flags & 0x01) != 0,
                                     (poscodes >> 6) & 0x3, (poscodes & 0x3F),
                                     textlen, contents_position, string_position);
            addBox(newBox);
            return newBox;
        }
        
        public static UpLibPageText read (int page_no, InputStream bbox_stream)
            throws IOException, DataFormatException {

            byte[] buffer = new byte[20];
            int page_index = 0;

            // check the headers and find out how many words there are
            bbox_stream.read(buffer, 0, 20);
            String s = new String(buffer, 0, 11);
            if (!s.equals("UpLib:pbb:1"))
                throw new DataFormatException("File " + bbox_stream + " has incorrect header " + s);
            DataInputStream ds = new DataInputStream(new ByteArrayInputStream(buffer, 12, 8));
            int box_count = ds.readUnsignedShort();
            int text_length = ds.readUnsignedShort();
            int page_start_index = ds.readInt();
            // System.err.println("  contains " + box_count + " bboxes and " + text_length + " bytes of text starting at " + page_start_index);

            // uncompress the data
            InflaterInputStream zipstream = new InflaterInputStream(bbox_stream);
            int boxes_length = 16 * box_count;
            int read_so_far = 0;
            byte[] uncompressed_box_data = new byte[boxes_length];
            while (read_so_far < boxes_length) {
                read_so_far = read_so_far + zipstream.read(uncompressed_box_data, read_so_far, (boxes_length - read_so_far));
            }
            read_so_far = 0;
            byte[] uncompressed_text = new byte[text_length];
            while (read_so_far < text_length) {
                read_so_far = read_so_far + zipstream.read(uncompressed_text, read_so_far, (text_length - read_so_far));
            }
            zipstream.close();

            UpLibPageText pb = new UpLibPageText(uncompressed_text, page_start_index, page_no);

            // interpret the data
            ByteArrayInputStream istr = new ByteArrayInputStream(uncompressed_box_data);
            int string_position = 0;
            int last_contents_position = 0;
            for (int i = 0;  i < box_count;  i++) {
                if (istr.available() < 16)
                    throw new DataFormatException("Unexpected end of file in bounding box data");
                istr.read(buffer, 0, 16);
                UpLibWordBox newBox = pb.addBoxFromRecord(buffer, 16, last_contents_position, string_position);
                String boxText = new String(uncompressed_text, newBox.content_position, newBox.textlen, "UTF-8");
                int boxTextLen = boxText.length();
                string_position += boxTextLen;
                last_contents_position = newBox.content_position;
            }
            pb.allBoxesAdded();
            istr.close();

            return pb;
        }
    }
}    
