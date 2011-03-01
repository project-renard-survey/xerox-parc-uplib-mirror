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

package com.parc.uplib.readup.uplibbinding;

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
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.*;

import com.parc.uplib.util.Configurator;
import com.parc.uplib.readup.widget.CachingLoader;
import com.parc.uplib.readup.widget.ResourceLoader;
import com.parc.uplib.readup.widget.PageText;
import com.parc.uplib.readup.widget.PageTextLoader;

public class UpLibPageTextLoader extends CachingLoader {

    private URL repo_url;
    private String repo_password;
    private String repo_cookie;

    static {
        try {
            Configurator c = new Configurator();
            String s = c.get("client-side-cache-location");
            if (s != null) {
                CachingLoader.setCacheDirectory(new File(s));
            }
        } catch (java.security.AccessControlException x) {
            // can't read machine.config, because in an applet
        } catch (Exception x) {
            System.err.println("Exception while initializing CachingLoader static section");
            x.printStackTrace(System.err);
        }
    }
            
    public UpLibPageTextLoader (String resource_type, URL repo_url_p, String pword_p) {
        super(repo_url_p, resource_type);
        repo_url = repo_url_p;
        repo_password = pword_p;
        repo_cookie = null;
    }

    public UpLibPageTextLoader (URL repo_url_p, String pword_p) {
        super(null, "page text");
        repo_url = repo_url_p;
        repo_password = pword_p;
        repo_cookie = null;
    }

    public void setCookie (String cookie) {
        repo_cookie = cookie;
    }

    public Object getResource(String document_id, int pageno, int selector)
        throws IOException {
        
        URL the_url = null;

        if (pageno < 0)
            throw new ResourceLoader.ResourceNotFound("invalid page number " + pageno + " specified.");

        Object o = super.getResource(document_id, pageno, selector);
        if (o != null) {
            // System.err.println("loaded page text " + document_id + "/" + pageno + "/" + selector + " from cache");
            return o;
        }

        try {
            the_url = new URL(repo_url, "/docs/" + document_id + "/thumbnails/" + Integer.toString(pageno+1) + ".bboxes");
        } catch (MalformedURLException x) {
            x.printStackTrace(System.err);
            throw new ResourceLoader.CommunicationFailure(x.toString());
        }

        // System.err.println("page URL is " + path);
        try {
            HttpURLConnection c = (HttpURLConnection) the_url.openConnection();
            if ((repo_password != null) && (repo_password.length() > 0))
                c.setRequestProperty("Password", repo_password);
            if (repo_cookie != null)
                c.setRequestProperty("Cookie", repo_cookie);
            int rcode = c.getResponseCode();
            if (rcode == 200) {
                InputStream s = c.getInputStream();
                try {
                    UpLibPageText pt = UpLibPageText.read(pageno, s);
                    if (pt==null){
                        System.err.println("fetched page text " + document_id + "/" + pageno +
                        		" but the data is NULL");
                    } else {
                    	System.err.println("fetched page text " + document_id + "/" + pageno);
                    }
                    super.cacheResource(document_id, pageno, selector, pt);
                    return pt;
                } finally {
                    s.close();
                }
            } else if (rcode == 404) {
                throw new ResourceLoader.ResourceNotFound("HTTP code 404 on " + the_url.toExternalForm());
            } else if (rcode == 401) {
                throw new ResourceLoader.PrivilegeViolation("HTTP code 401 on " + the_url.toExternalForm());
            } else {
                throw new ResourceLoader.CommunicationFailure("HTTP code " + rcode + " on " + the_url.toExternalForm());
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
            return pt;
        }
    }

    public static class UpLibPageText extends PageText implements Serializable {

        private byte[] pagetext;
        private int pagestart;
        public int current_word_count;
        private int our_page;

        private static CharsetDecoder utf8_decoder_replacing = null;
        private static CharsetDecoder utf8_decoder_erroring = null;
        static {
            utf8_decoder_replacing = Charset.forName("UTF-8").newDecoder();
            utf8_decoder_replacing.onMalformedInput(CodingErrorAction.REPLACE);
            utf8_decoder_erroring = Charset.forName("UTF-8").newDecoder();            
        }

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
            int		sentence_number = -1;
            int         stringPos = -1;

            public UpLibWordBox (int ulx, int uly, int lrx, int lry,
                                 int chars, float font_size_p,
                                 boolean fixed_width_p, boolean serif_p,
                                 boolean symbolic_p, boolean italic_p, boolean bold_p,
                                 boolean endsline_p, boolean endsword_p, boolean inserted_hyphen_p,
                                 int starts_code, int pos_code,
                                 int textlen_p, int content_position_p) {

                x = ulx;
                y = uly;
                width = (lrx - ulx);
                height = (lry - uly);
                char_count = chars; // text characters, not counting trailing white space
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
                textlen = textlen_p; // text bytes (in UTF-8), possibly but not necessarily including trailing white space
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
                } catch (Exception e) {
                    System.err.println("Can't get text for word at content_position " + content_position + " with textlen " + textlen + "; pagetext len is " + pagetext.length);
                    e.printStackTrace(System.err);
                }
                // char_count is only approximate, due to Unicode normalization
                int nchars = Math.min(s.length(), (inserted_hyphen ? (char_count - 1) : char_count));
                return s.substring(0, nchars);
            }

            public int contentsPosition () {
            	// position in the UTF-8 byte sequence, known as pagetext
                return content_position;
            }

            public int contentsLength () {
                return textlen;
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
            
            public int stringPosition () {
                if (stringPos < 0) {
                    try {
                        stringPos = (new String(pagetext, 0, content_position, "UTF-8")).length();
                    } catch (Exception e) {
                        e.printStackTrace(System.err);
                    }
                }
                return stringPos;
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

        private UpLibWordBox addBoxFromRecord (byte[] record, int byte_count, boolean last)
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

                if ((lowerRightY < upperLeftY) || (lowerRightX < upperLeftX)) {
                    // can't just force a fix; need to figure out the right fix
                    String boxText = new String(pagetext, contents_position, textlen, "UTF-8");
                    System.err.println("Bad wordbox " + (lowerRightX - upperLeftX) + "x" + (lowerRightY - upperLeftY) + "+" +
                                       upperLeftX + "+" + upperLeftY + ": " + char_count + "@" + contents_position +
                                       " \"" + boxText + "\"");
                }

                if (last) {
                    // pagetext often has some trailing bytes, because of uncertainty about Unicode normalization
                    // trim those off if this is the last box
                    int old_textlen = textlen;
                    String s = utf8_decoder_replacing.decode
                        (ByteBuffer.wrap(pagetext, contents_position, Math.min(textlen, pagetext.length - contents_position))).toString();
                    if (s.length() > char_count) {
                        // System.err.println("********************************************");
                        // System.err.println("formed string <<" + s + ">> for word @ " + contents_position + " is " + (s.length() - char_count) + " chars too long");
                        s = s.substring(0, char_count);
                        textlen = s.getBytes("UTF-8").length;
                        int extra = pagetext.length - (contents_position + textlen);
                        // System.err.println("that's " + extra + " extra bytes -- " + textlen + " bytes for <<" + s + ">> instead of " + old_textlen);
                        if (extra > 0) {
                            byte[] new_pagetext = new byte[contents_position + textlen];
                            System.arraycopy(pagetext, 0, new_pagetext, 0, new_pagetext.length);
                            pagetext = new_pagetext;
                            // System.err.println("New pagetext length is " + new_pagetext.length);
                        }
                        // System.err.println("********************************************");
                    }
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
        			textlen, contents_position);
                if ((lowerRightY > upperLeftY) && (lowerRightX > upperLeftX)) {
                    // only add box if good; but return it in all cases
                    addBox(newBox);
                }
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
            for (int i = 0;  i < box_count;  i++) {
                if (istr.available() < 16)
                    throw new DataFormatException("Unexpected end of file in bounding box data");
                istr.read(buffer, 0, 16);
                UpLibWordBox newBox = pb.addBoxFromRecord(buffer, 16, (i + 1) == box_count);
            }
            pb.allBoxesAdded();
            istr.close();

            return pb;
        }
    }
    
    public static void main(String[] argv) throws IOException, DataFormatException {
    	// Test that shows off a problem with UpLibPageText.read:
    	String repoHref = "https://greta.parc.xerox.com:9020";
    	String docID = "01126-21-5904-857";
      	String okHref = repoHref + "/docs/"+docID+"/thumbnails/48.bboxes";
    	String problemHref = repoHref + "/docs/"+docID+"/thumbnails/51.bboxes";
    	int okPageno = 47;
    	int problemPageno = 50;
    	URL repoURL = null;
    	try {
    		repoURL = new URL(repoHref);
    	} catch (MalformedURLException e) {
    		String msg = e.toString();
    		System.err.println(msg);
    		return;
    	}
    	String password = "";
    	UpLibPageTextLoader loader = new UpLibPageTextLoader(repoURL, password);
    	UpLibPageText pt = null;
    	String okLocalFilename = "C:\\nimd\\48.bboxes";
    	String problemLocalFilename = "C:\\nimd\\51.bboxes";
    	File okFile = new File(okLocalFilename);
    	File problemFile = new File(problemLocalFilename);
    	InputStream okStream = new FileInputStream(okFile);
    	// This test succeeds:
    	pt = UpLibPageText.read(okPageno, okStream);
    	String thisText = null;
    	thisText = pt.getText();
    	System.out.println("\n\nContents of page 47:");
    	System.out.println(thisText);
    	InputStream problemStream = new FileInputStream(problemFile);
    	// This test fails:
    	pt = UpLibPageText.read(problemPageno, problemStream);
    	thisText = pt.getText();
    	System.out.println("\n\nContents of page 50:");
    	System.out.println(thisText);
    }
}
