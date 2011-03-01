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

public class HeaderField {
    String  name;
    boolean indexed;
    boolean tokenized;
    boolean stored;
    boolean date;
    String splitter;

    public HeaderField (String n, boolean i, boolean t, boolean s, boolean d, String s2) {
        name = n;
        indexed = i;
        tokenized = t;
        stored = s;
        date = d;
        splitter = s2;
    };

    public static HeaderField findField (HeaderField[] fields, String name) {
        for (int i = 0;  i < fields.length;  i++) {
            if (fields[i].name == name)
                return fields[i];
        }
        return null;
    }

    public static HeaderField[] parseUserHeaders (String z) {
        StringTokenizer t = new StringTokenizer(z, ":");
        HeaderField[] userheaders = new HeaderField[t.countTokens()];
        int counter = 0;
        HeaderField h;
        while (t.hasMoreTokens()) {
            String s = t.nextToken();
            h = new HeaderField(null, true, true, false, false, null);
            if (s.charAt(s.length()-1) == '*') {
                // don't tokenize
                h.name = s.substring(0, s.length()-1);
                h.tokenized = false;
            } else if (s.charAt(s.length()-1) == '@') {
                h.name = s.substring(0, s.length()-1);
                h.tokenized = false;
                h.date = true;
            } else {
                h.name = s;
            }
            int splitter = h.name.lastIndexOf('$');
            if (splitter >= 0) {
                h.splitter = h.name.substring(splitter+1);
                h.name = h.name.substring(0, splitter);
            }
            userheaders[counter] = h;
            counter = counter + 1;
        }
        return userheaders;
    }
};
