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

package com.parc.uplib.util;

import java.io.File;
import java.io.FileReader;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.Charset;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.util.Set;
import java.util.Map;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Vector;
import java.util.StringTokenizer;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.nio.charset.Charset;
import java.nio.charset.CharsetEncoder;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.UnmappableCharacterException;
import java.nio.charset.CharacterCodingException;

public class MetadataFile extends java.util.AbstractMap {

    final private static Matcher content_type = Pattern.compile("Content-Type:\\s*text/plain\\s*;\\s*charset=(.*)\\s*$").matcher("");
    final private static Matcher content_language = Pattern.compile("Content-Language:\\s*(.*)\\s*$").matcher("");

    final private static Matcher header_encoding = Pattern.compile("^=\\?([^\\?]+)\\?([BQbq])\\?(.*)\\?=$").matcher("");

    final private static CharsetEncoder US_ASCII = Charset.forName("US-ASCII").newEncoder()
        .onUnmappableCharacter(CodingErrorAction.REPORT)
        .onMalformedInput(CodingErrorAction.REPORT);
        
    final private static CharsetEncoder UTF_8 = Charset.forName("UTF-8").newEncoder()
        .onUnmappableCharacter(CodingErrorAction.REPORT)
        .onMalformedInput(CodingErrorAction.REPORT);

    private static ByteBuffer ASCII_NEWLINE;
    private static ByteBuffer UTF8_HEADER;
    private static ByteBuffer UTF8_TRAILER;

        private static final byte SPACE = 32;
    private static final byte CHAR_A = 65;
    private static final byte CHAR_Z = 90;
    private static final byte CHAR_a = 97;
    private static final byte CHAR_z = 122;
    private static final byte CHAR_0 = 48;
    private static final byte CHAR_9 = 57;
    private static final char[] HEXDIGITS = new char[] {'0', '1', '2', '3', '4', '5', '6', '7',
                                                        '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'};
    private static final char[] ASCII_UPPERCASE = new char[] {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                                                              'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'};
    private static final char[] ASCII_LOWERCASE = new char[] {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                                                              'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'};

    static {
        try {
            ASCII_NEWLINE = US_ASCII.encode(CharBuffer.wrap("\n"));
            UTF8_HEADER = US_ASCII.encode(CharBuffer.wrap("=?UTF-8?B?"));
            UTF8_TRAILER = US_ASCII.encode(CharBuffer.wrap("?="));
        } catch (UnmappableCharacterException x) {
            // can't ever happen for these string literals
        } catch (CharacterCodingException x) {
            // can't ever happen for these string literals
        }
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

    // Encode Quoted-Printable

    private static CharBuffer encode_quoted_printable (String input)
        throws java.io.UnsupportedEncodingException, java.nio.charset.CharacterCodingException {

        ByteBuffer encoded_input = UTF_8.encode(CharBuffer.wrap(input));
        CharBuffer value = CharBuffer.allocate((3 * encoded_input.limit()) + 20);
        
        value.put("=?UTF-8?Q?");
        for (int i = 0;  i < encoded_input.limit();  i++) {
            byte b = encoded_input.get(i);
            if (b == SPACE)
                value.put("_");
            else if ((b >= CHAR_A) && (b <= CHAR_Z))
                value.put(ASCII_UPPERCASE[b - CHAR_A]);
            else if ((b >= CHAR_a) && (b <= CHAR_z))
                value.put(ASCII_LOWERCASE[b - CHAR_a]);
            else if ((b >= CHAR_0) && (b <= CHAR_9))
                value.put(HEXDIGITS[b - CHAR_0]);
            else {
                value.put("=");
                value.put(HEXDIGITS[(b >> 4) & 0xF]);
                value.put(HEXDIGITS[b & 0xF]);
            }
        }
        value.put("?=");
        value.flip();
        // System.err.println("value for \"" + input + "\" is \"" + value.toString() + "\"");
        return value;
    }

    // Decode Base64

    private static ByteBuffer decode_base64 (String input)
        throws java.io.UnsupportedEncodingException {
        
        return ByteBuffer.wrap(Base64.decode(input.getBytes("ISO-8859-1")));
    }


    // Convert "encoded-word" values to UTF-8

    public static String convert_header_value (String name, String value)
        throws java.io.UnsupportedEncodingException{

        String decoded_value = value;

	synchronized(header_encoding) {
            header_encoding.reset(value);
            if (header_encoding.matches()) {
                Charset cs = Charset.forName(header_encoding.group(1));
                String quoting = header_encoding.group(2);
                String encoded_value = header_encoding.group(3);
                ByteBuffer bytes;
                java.nio.CharBuffer chars;

                // System.err.println("  header " + name + ":  charset is " + cs + ", quoting is " + quoting + ", encoded_value is " + encoded_value);
                if (quoting.equals("Q") || quoting.equals("q")) {
                    bytes = decode_quoted_printable(encoded_value);
                    chars = cs.decode(bytes);
                } else if (quoting.equals("B") || quoting.equals("b")) {
                    bytes = decode_base64(encoded_value);
                    chars = cs.decode(bytes);
                } else
                    chars = cs.decode(ByteBuffer.wrap(encoded_value.getBytes()));
                decoded_value = chars.toString();
            }
	}
        return decoded_value;            
    }

    public static String decode_header_value (String name, String value)
        throws java.io.UnsupportedEncodingException {
        return convert_header_value (name, value);
    }

    public static String encode_header_value (String name, String value, String language)
        throws java.io.UnsupportedEncodingException, java.nio.charset.CharacterCodingException {
        US_ASCII.reset();
        if (!US_ASCII.canEncode(value)) {
            // transcribe to quoted-printable-encoded UTF-8
            return encode_quoted_printable(value).toString();
        } else if (language == null) {
            return value;
        } else {
            // not sure what to do here yet
            return encode_header_value(name, value, null);
        }
    }

    public static String encode_header_value (String name, String value)
        throws java.io.UnsupportedEncodingException, java.nio.charset.CharacterCodingException {
        return encode_header_value(name, value, null);
    }

    public static String fillMap (BufferedReader is, Map data) throws java.io.IOException {

        String current_header = null;
        String current_value = null;
        String current_line = null;
        String value;

        // read the file one line at a time, and dispatch on the header name
        while (((current_line = is.readLine()) != null) &&
               // allow (and ignore) blank lines, unless they start with a formfeed (record separator)
               ((current_line.trim().length() > 0) || (current_line.charAt(0) != '\f'))) {

            // System.err.println("fillMap:  read <" + current_line + ">");

            if (current_line.trim().length() > 0 &&
                java.lang.Character.isWhitespace(current_line.charAt(0)))
                // an extension line; should be added to end of last value
                {
                    if (current_header == null) {
                        // throw some exception??
                        current_line = current_line.trim();
                    } else {
                        current_value = current_value + " " + convert_header_value(current_header, current_line.trim());
                        continue;
                    }
                }

            // new value
            if (current_header != null) {
                // add the current header to the index database
                if (current_value == null) {
                    System.err.println("bad value \"" + current_line.trim() + "\" for header \"" + current_header + "\".");
                    current_header = null;
                    continue;
                }

                data.put((Object) current_header, (Object) current_value);
                // System.err.println("" + current_header + ": " + current_value);
                current_header = null;
                current_value = null;
            }

            if (current_line.trim().length() > 0) {

                // find the new header
                int hpos = current_line.indexOf(':');
                if (hpos < 1) {
                    throw new IOException("Invalid line in metadata file:  <" + current_line + ">");
                } else {
                    current_header = current_line.substring(0, hpos).trim().toLowerCase();
                    current_value = current_line.substring(hpos + 1, current_line.length()).trim();
                    current_value = convert_header_value(current_header, current_value);
                }
                if (current_line != null && current_header == null) {
                    // throw some error here
                }
            }
        }

        if (current_header != null) {
            // add the current header to the index database
            if (current_value == null) {
                System.err.println("bad value \"" + current_line.trim() + "\" for header \"" + current_header + "\".");
            }
            data.put(current_header, current_value);
            // System.err.println("" + current_header + ": " + current_value);
        }

        // System.err.println("fillMap:  returning <" + current_line + ">");
        return current_line;
    }

    private java.util.HashMap data;
    // for two-way I/O, use metadata_file
    private java.io.File metadata_file = null;
    // for one-way I/O (input only), use metadata_reader
    private java.io.Reader metadata_reader = null;
    private boolean dirty;

    public Set entrySet () {
        return data.entrySet();
    }

    private void readMetadata() throws java.io.IOException {

        BufferedReader is;

        if (metadata_file != null)
            is = new BufferedReader(new FileReader(metadata_file));
        else if (metadata_reader != null)
            is = new BufferedReader(metadata_reader);
        else
            throw new java.io.IOException("No file to read!");

        fillMap (is, data);
        is.close();
    }

    private void save () throws IOException {
        ByteBuffer header_bytes;
        ByteBuffer value_bytes;
        FileOutputStream f = new FileOutputStream(metadata_file);
        Iterator it = data.entrySet().iterator();
        // System.err.println("----- saving MetadataFile " + metadata_file);
        while (it.hasNext()) {
            Map.Entry me = (Map.Entry) (it.next());
            String header = (String) me.getKey();
            String value = (String) me.getValue();
            // System.err.println("" + header + ": " + value);
            try {
                ByteBuffer b = US_ASCII.encode(CharBuffer.wrap(header + ": "));
                f.write(b.array(), b.position(), b.limit());
            } catch (Exception x) {
                throw new IOException ("Malformed header value <" + header + ">");
            }
            try {
                US_ASCII.reset();
                if (US_ASCII.canEncode(value))
                    value_bytes = US_ASCII.encode(CharBuffer.wrap(value));
                else
                    value_bytes = US_ASCII.encode(encode_quoted_printable(value));
                f.write(value_bytes.array(), value_bytes.position(), value_bytes.limit());
            } catch (java.nio.charset.CharacterCodingException x) {
                x.printStackTrace(System.err);
            }
        }
        f.close();
        dirty = false;
    }

    public boolean containsKey (Object key) {
        if (key instanceof String)
            return super.containsKey((Object) (((String)key).toLowerCase()));
        else
            return super.containsKey(key);
    }

    public String get (String key) {
        return (String) data.get((Object) key.toLowerCase());
    }

    public Object put (Object key, Object value) {
        Object v = data.get(key);
        data.put((Object) (key.toString()), (Object) (value.toString()));
        dirty = true;
        return v;
    }

    public void clear () {
        data.clear();
        dirty = true;
    }

    public Object remove (Object key) {
        Object v = super.remove(key);
        dirty = true;
        return v;
    }

    public void flush () throws IOException {
        if (dirty)
            save();
    }

    public MetadataFile (File mf) throws java.io.IOException {
        super();
        this.metadata_file = mf;
        this.data = new HashMap();
        readMetadata();
        this.dirty = false;
    }

    public MetadataFile (String pathname) throws java.io.IOException {
        super();
        this.metadata_file = new File(pathname);
        this.data = new HashMap();
        readMetadata();
        this.dirty = false;
    }

    public MetadataFile (Reader r) throws java.io.IOException {
        super();
        this.metadata_file = null;
        this.metadata_reader = r;
        this.data = new HashMap();
        readMetadata();
        this.dirty = false;
    }

    protected void finalize () throws Throwable {
        this.flush();
    }
}
