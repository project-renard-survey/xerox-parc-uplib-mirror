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

package com.parc.uplib.indexing;

import java.io.File;
import java.io.FileReader;
import java.io.FileInputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.util.Date;
import java.util.Vector;
import java.util.StringTokenizer;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.Calendar;
import java.text.SimpleDateFormat;
import java.text.ParsePosition;
import java.text.DecimalFormat;

import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;

import com.parc.uplib.util.Base64;

public class ExtractIndexingInfo {

    private final static DecimalFormat RANGE_DATE_FORMAT = new DecimalFormat("########");

    private static Matcher content_type = Pattern.compile("Content-Type:\\s*text/plain\\s*;\\s*charset=(.*)\\s*$").matcher("");
    private static Matcher content_language = Pattern.compile("Content-Language:\\s*(.*)\\s*$").matcher("");

    private static Matcher header_encoding = Pattern.compile("^=\\?([^\\?]+)\\?([BQbq])\\?(.*)\\?=$").matcher("");

    private static HeaderField[] standard_headers = {
        new HeaderField("title", true, true, false, false, null),
        new HeaderField("authors", true, true, false, false, "\\sand\\s"),
        new HeaderField("source", true, true, false, false, null),
        new HeaderField("date", true, false, false, true, null),
        new HeaderField("comment", true, true, false, false, null),
        new HeaderField("abstract", true, true, false, false, null),
        new HeaderField("citation", true, false, false, false, null),
        new HeaderField("categories", true, false, false, false, ","),
        new HeaderField("keywords", true, false, false, false, ","),
    };

    private static HeaderField[] headers = standard_headers;

    public static String convert_date (String slashed_date) {
        int year, month, day;
        try {
            String[] parts = slashed_date.split("/");
            int current_year = Calendar.getInstance().get(Calendar.YEAR);
            int current_century = (current_year - (current_year % 100));
            if (parts.length == 3) {
                month = Integer.parseInt(parts[0]);
                day = Integer.parseInt(parts[1]);
                year = Integer.parseInt(parts[2]);
            } else if (parts.length == 2) {
                day = 0;
                month = Integer.parseInt(parts[0]);
                year = Integer.parseInt(parts[1]);
            } else {
                day = 0;
                month = 0;
                year = Integer.parseInt(parts[0]);
                if (year > 3000)
                    return null;
            }
            if (year < (current_year % 100))
                year += current_century;
            else if (year < 100)
                year += (current_century - 100);
            return RANGE_DATE_FORMAT.format(year * 10000 + month * 100 + day);
        } catch (Exception e) {
            return null;
        }
    }

    private static String id_to_date (String id) {
        SimpleDateFormat o = new SimpleDateFormat("yyyyMMdd");
        StringTokenizer t = new StringTokenizer(id, "-");
        long time = Integer.parseInt(t.nextToken());
        time = time * 100 + Integer.parseInt(t.nextToken());
        time = time * 10000 + Integer.parseInt(t.nextToken());
        time = time * 1000 + Integer.parseInt(t.nextToken());
        return o.format(new Date(time));
    }

    // fromHex()

    private static int fromHex (int input)
        throws java.io.UnsupportedEncodingException {
        if (input >= 48 && input <= 59)
            return (input - 48);
        else if (input >= 65 && input <= 70)
            return (input - 55);
        else if (input >= 97 && input <= 102)
            return (input - 87);
        else {
            System.err.println("Invalid hex code " + input + " passed.");
            throw new java.io.UnsupportedEncodingException("Invalid hex code " + input + " passed.");
        }
    }

    // Decode Quoted-Printable

    private static ByteBuffer decode_quoted_printable (String inputString)
        throws java.io.UnsupportedEncodingException {

        final byte EQUAL_SIGN = 61;
        final byte NEWLINE = 10;
        final byte CARRIAGE_RETURN = 13;

        byte[] input = inputString.getBytes("US-ASCII");
        ByteBuffer output = ByteBuffer.allocate(input.length);

        for (int i = 0;  i < input.length;) {
            if (input[i] == EQUAL_SIGN) {
                if (input[i+1] == NEWLINE) {
                    // an escaped newline
                    i = i + 2;
                    continue;
                } else {
                    // an escaped binary byte
                    output.put((byte) (fromHex(input[i+1]) * 16 + fromHex(input[i+2])));
                    i = i + 3;
                }
            } else {
                output.put(input[i]);
                i++;
            }
        }
        output.flip();
        return output;
    }

    // Decode Base64

    private static ByteBuffer decode_base64 (String input)
        throws java.io.UnsupportedEncodingException {
        
        return ByteBuffer.wrap(Base64.decode(input.getBytes("US-ASCII")));
    }


    // Convert "encoded-word" values to UTF-8

    private static String convert_header_value (String name, String value)
        throws java.io.UnsupportedEncodingException{

        String decoded_value = value;

        header_encoding.reset(value);
        if (header_encoding.matches()) {
            Charset cs = Charset.forName(header_encoding.group(1));
            String quoting = header_encoding.group(2);
            String encoded_value = header_encoding.group(3);
            ByteBuffer bytes;
            java.nio.CharBuffer chars;

            System.err.println("  header " + name + ":  charset is " + cs + ", quoting is " + quoting + ", encoded_value is " + encoded_value);
            if (quoting.equals("Q") || quoting.equals("q")) {
                bytes = decode_quoted_printable(encoded_value);
                chars = cs.decode(bytes);
            } else if (quoting.equals("B") || quoting.equals("b")) {
                bytes = decode_base64(encoded_value);
                chars = cs.decode(bytes);
            } else
                chars = cs.decode(ByteBuffer.wrap(encoded_value.getBytes()));
            decoded_value = chars.toString();
        };
        return decoded_value;            
    }

    // Set the names of the headers actually indexed for a document

    public static void addIndexingFields (String z) {

        int i = 0;
        Vector standards = new Vector();
        for (i = 0;  i < standard_headers.length;  i++)
            standards.add(standard_headers[i].name);
        HeaderField[] newheaders = HeaderField.parseUserHeaders(z);
        i = 0;
        for (int j = 0;  j < newheaders.length;  j++) {
            if (!standards.contains(newheaders[j].name))
                i++;
        }
        HeaderField[] headers2 = new HeaderField[i + standard_headers.length];
        for (i = 0;  i < standard_headers.length;  i++)
            headers2[i] = standard_headers[i];
        for (int j = 0;  j < newheaders.length;  j++)
            if (!standards.contains(newheaders[j].name)) {
                headers2[i] = newheaders[j];
                i++;
            }
        headers = headers2;
    }

    public static class ContentsIterator implements java.util.Iterator {

        BufferedReader is;
        String line;                    // one-line readahead buffer
        String language = "en";
        File cfile = null;
        CharBuffer cb = null;
        String overflow;

        public ContentsIterator (File contents_file) {

            line = null;
            cfile = contents_file;
            is = getReader();
            cb = CharBuffer.allocate(1 << 15);
            overflow = "";
        }

        public BufferedReader getReader() {

            // read the contents.txt file and add it to the document data
            if (cfile.isFile() && cfile.length() > 0) {
                
                Charset charset = null;

                try {

                    charset = Charset.forName("US-ASCII");
                    is = new BufferedReader(new InputStreamReader(new FileInputStream(cfile), charset));
                    int line_no = 1;

                    is.mark(1 << 12);
                    while (true) {
                        line = is.readLine();
                        if (line == null)
                            break;
                        if (line_no == 1) {
                            content_type.reset(line);
                            if (content_type.matches()) {
                                charset = Charset.forName(content_type.group(1));
                                is.close();
                                is = new BufferedReader(new InputStreamReader(new FileInputStream(cfile), charset));
                                is.readLine();
                                is.mark(1 << 12);   // throw away Content-Type line
                                line_no = line_no + 1;
                                System.err.println("  Using charset " + content_type.group(1) + " for contents.txt");
                                continue;
                            }
                        }
                        if (line_no == 2) {
                            content_language.reset(line);
                            if (content_language.matches()) {
                                language = content_language.group(1);
                                is.mark(1 << 12);   // throw away Content-Language line
                                line_no = line_no + 1;
                                System.err.println("  Using language " + content_language.group(1) + " for contents.txt");
                                continue;
                            }
                        }
                        is.reset();
                        line = is.readLine();
                        break;
                    }
                } catch (java.io.IOException x) {
                    System.err.println("IOException while dealing with contents file " + cfile + ":  " + x);
                    line = null;
                }
                return is;
            } else
                return null;
        }

        public boolean hasNext () {
            return (line != null);
        }

        private boolean isFormfeed (String l) {
            return ((l.length() > 0) && (l.charAt(0) == '\f') && (l.trim().length() == 0));
        }            

        private void addLine (String line) {
            // System.err.println("addLine(" + line.length() + ", " + cb.remaining() + ")");
            if ((overflow.length() > 0) || (cb.position() > 0)) {
                // already text in buffer, must add space before adding line
                if (cb.remaining() < 1) {
                    cb.flip();
                    overflow = overflow + cb.toString();
                    cb.clear();
                }
                cb.put(' ');
            }
            if ((line.length() + 1) >= cb.remaining()) {
                cb.flip();
                overflow = overflow + cb.toString();
                // System.err.println("length of overflow now " + overflow.length());
                cb.clear();
            }
            cb.put(line);
        }

        private void clearBuffer () {
            cb.clear();
            overflow = "";
        }

        private String getCurrentPage () {
            String rval = overflow;
            if (cb.position() > 0) {
                cb.flip();
                rval = rval + cb.toString();
            }
            clearBuffer();
            return rval;
        }

        public Object next () {
            clearBuffer();
            try {
                // System.err.println("---:  " + line);
                if (isFormfeed(line)) {
                    line = is.readLine();
                    return null;
                }
                addLine(line);
                while ((line = is.readLine()) != null) {
                    // System.err.println("---:  " + line);
                    if (isFormfeed(line)) {
                        line = is.readLine();
                        break;
                    }
                    addLine(line);
                }
                return getCurrentPage();
            } catch (java.io.IOException x) {
                x.printStackTrace(System.err);
                return null;
            }
        }

        public void remove() {};
    }

    public static class DocumentIterator implements java.util.Iterator {

        public  String id;

        private File folder;
        private File metadata_file;
        private File contents_file;
        private boolean has_categories = false;
        private Document master;
        private ContentsIterator page_iterator;
        private int page_index;
        private Vector metadata_fields;

        public DocumentIterator (File directory, String id) {

            folder = new java.io.File(directory, id);
            metadata_file = new java.io.File(folder, "metadata.txt");
            File contents_file = new java.io.File(folder, "contents.txt");
            has_categories = false;
            this.id = id;

            System.err.println("Working on document " + folder);

            metadata_fields = getMetadataFields();

            // make a new, empty document
            master = new Document();

            master.add(new Field("id", id, Field.Store.YES, Field.Index.UN_TOKENIZED));
            master.add(new Field("uplibdate", id_to_date(id), Field.Store.YES, Field.Index.UN_TOKENIZED));
            master.add(new Field("uplibtype", "whole", Field.Store.YES, Field.Index.UN_TOKENIZED));

            System.err.println("  Created empty doc " + master.toString());

            page_iterator = new ContentsIterator(contents_file);
            page_index = 0;
        }

        private Document nextPage () {
            if (page_iterator.hasNext()) {

                Document doc = new Document();

                doc.add(new Field("id", id, Field.Store.YES, Field.Index.UN_TOKENIZED));
                doc.add(new Field("pagenumber", Integer.toString(page_index), Field.Store.YES, Field.Index.UN_TOKENIZED));
                doc.add(new Field("uplibtype", "page", Field.Store.YES, Field.Index.UN_TOKENIZED));

                String pagecontents = (String) page_iterator.next();
                System.err.println("    page " + page_index + ((pagecontents == null) ? ":  " : " (" + pagecontents.length() + "):  ") + ((pagecontents == null) ? "" : pagecontents.substring(0, Math.min(30, pagecontents.length()))));
                if (pagecontents != null) {
                    doc.add(new Field("pagecontents", pagecontents, Field.Store.NO, Field.Index.TOKENIZED));
                }
                page_index += 1;
                return doc;
            } else {
                return null;
            }
        }

        private void showProperty (String docid, String header, String value, boolean indexed, boolean tokenized, boolean stored) {
            System.err.print("  Adding header '" + header + "' ");
            if (indexed)
                System.err.print("I");
            if (tokenized)
                System.err.print("T");
            if (stored)
                System.err.print("S");
            if (value != null)
                System.err.print(" (" + value + ")");
            System.err.println(" to " + docid);
        }

        private Vector getMetadataFields() {

            Vector metadata = new Vector();

            // look for a metadata indexing file, and open it if it exists
            if (metadata_file.isFile() && metadata_file.length() > 0) {

                try {

                    BufferedReader is = new BufferedReader(new FileReader(metadata_file));

                    String current_header = null;
                    String current_value = null;
                    String current_line = null;
                    boolean indexed = false;
                    boolean tokenized = false;
                    boolean stored = false;
                    boolean is_date = false;
                    String split_regex = null;
                    String[] values;
                    String value;

                    // read the file one line at a time, and dispatch on the header name
                    while (true) {

                        // read the next line -- may be null at EOF
                        current_line = is.readLine();

                        if (current_line != null &&
                            current_line.length() > 0 &&
                            java.lang.Character.isWhitespace(current_line.charAt(0)))
                            // an extension line; should be added to end of last value
                            {
                                if (current_header == null) {
                                    // throw some exception
                                    current_line = current_line.trim();
                                } else {
                                    current_value = current_value + " " + convert_header_value(current_header, current_line.trim());
                                    continue;
                                }
                            }

                        if (current_header != null) {
                            // add the current header to the index database
                            if (is_date)
                                // we need to convert dates to the special form Lucene uses
                                current_value = convert_date(current_value);

                            if (current_value == null) {
                                System.err.println("bad value \"" + current_line.trim() + "\" for header \"" + current_header + "\".");
                                current_header = null;
                                continue;
                            }

                            if (split_regex != null)
                                values = current_value.split(split_regex);
                            else {
                                values = new String[1];
                                values[0] = current_value;
                            }
                            if (current_header.equals("categories")) {
                                // Categories may be hierarchical, but we want to index under all combinations.
                                // So we need to form that list of combinations.
                                Vector v = new Vector();
                                for (int idx = 0;  idx < values.length;  idx++) {
                                    String[] parts = values[idx].split("/");
                                    if (parts.length == 1) {
                                        v.add(values[idx].trim());
                                    } else {
                                        String cname = parts[0].trim();
                                        v.add(cname);
                                        for (int jdx = 1;  jdx < parts.length;  jdx++) {
                                            cname = cname + "/" + parts[jdx].trim();
                                            v.add(cname);
                                        }
                                    }
                                }
                                values = (String[]) v.toArray(new String[v.size()]);
                            }
                            for (int valueindex = 0;  valueindex < values.length;  valueindex++) {
                                if (split_regex != null)
                                    value = values[valueindex].trim();
                                else
                                    value = values[valueindex];
                                if (value != null && value.length() > 0) {
                                    if (current_header.equals("categories")) {
                                        has_categories = true;
                                        value = value.toLowerCase();
                                        showProperty(id, current_header, value, indexed, tokenized, stored);
                                    } else if (current_header.equals("keywords")) {
                                        showProperty(id, current_header, value, indexed, tokenized, stored);
                                    } else if (current_header.equals("date")) {
                                        showProperty(id, current_header, current_value, indexed, tokenized, stored);
                                    } else if (current_header.equals("title")) {
                                        // print this out just for informative purposes
                                        showProperty(id, current_header, value, indexed, tokenized, stored);
                                    }
                                    else if (!current_header.equals("paragraph-ids"))
                                        showProperty(id, current_header, null, indexed, tokenized, stored);
                                    if (indexed) {
                                        if (tokenized) {
                                            if (stored)
                                                metadata.add(new Field(current_header, value, Field.Store.YES, Field.Index.TOKENIZED));
                                            else
                                                metadata.add(new Field(current_header, value, Field.Store.NO, Field.Index.TOKENIZED));
                                        } else {
                                            metadata.add(new Field(current_header, value, Field.Store.YES, Field.Index.UN_TOKENIZED));
                                        }
                                    } else {
                                        metadata.add(new Field(current_header, value, Field.Store.YES, Field.Index.NO));
                                    }
                                }
                            }
                            current_header = null;
                            current_value = null;
                        }

                        if (current_line != null) {
                            for (int i = 0;  i < headers.length;  i++) {

                                if (current_line.regionMatches(0, headers[i].name + ":", 0, headers[i].name.length() + 1)) {
                                    current_header = headers[i].name;
                                    current_value = current_line.substring(headers[i].name.length()+ 1, current_line.length()).trim();
                                    // check for non-ASCII encoding
                                    current_value = convert_header_value (current_header, current_value);
                                    indexed = headers[i].indexed;
                                    tokenized = headers[i].tokenized;
                                    stored = headers[i].stored;
                                    is_date = headers[i].date;
                                    split_regex = headers[i].splitter;
                                }
                            }
                        };

                        if (current_line != null && current_header == null) {
                            // throw some error here
                        }

                        if (current_line == null)
                            break;
                    }

                    // close the file
                    try {
                        is.close();
                    } catch (java.io.IOException x) {
                        System.err.println("Error closing input file " + metadata_file + ":  " + x);
                    }
                } catch (java.io.IOException x) {
                    System.err.println("IOException while dealing with input file " + metadata_file + ":  " + x);
                }
            }

            if (!has_categories)
                metadata.add(new Field("categories", "_(none)_", Field.Store.YES, Field.Index.UN_TOKENIZED));
            metadata.add(new Field("categories", "_(any)_", Field.Store.YES, Field.Index.UN_TOKENIZED));

            return metadata;
        }

        private Document finishMaster () {

            Document doc = master;
            master = null;

            BufferedReader is = page_iterator.getReader();
            if (is != null) {
                try {
                    // is is one-line read-ahead, so reset it to get that line back
                    is.reset();
                    // now add the reader to the contents field
                    doc.add(new Field("contents", is));
                } catch (java.io.IOException x) {
                    System.err.println("Error indexing contents field of document " + id);
                    x.printStackTrace(System.err);
                }
            }
            page_iterator = null;
            for (int i = 0;  i < metadata_fields.size();  i++) {
                doc.add((Field)(metadata_fields.get(i)));
            }

            // return the document
            return doc;
        }

        public boolean hasNext() {
            return (((page_iterator != null) && page_iterator.hasNext()) || (master != null));
        }

        public Object next() {
            Object o;
            if ((o = nextPage()) == null) {
                o = finishMaster();
                master = null;
            }
            return o;
        }

        public void remove() {
        }

    }

    private ExtractIndexingInfo() {

    }
}
    
