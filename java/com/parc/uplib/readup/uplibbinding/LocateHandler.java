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
import java.net.*;

import com.parc.uplib.util.BrowserLauncher;

import com.parc.uplib.readup.widget.*;

public class LocateHandler implements DocViewerCallback {

    private Object          context;
    private String          repo_url;
    private String          doc_id;
    public  ArrayList       stop_list;

    final static String[] DEFAULT_STOP_WORDS = new String[] {
        "a", "and", "any", "are", "as", "at", "be", "but", "by",
        "can", "for", "if", "he", "in", "into", "is", "it", "me",
        "no", "not", "of", "on", "one", "or", "s", "she", "such",
        "t", "that", "the", "their", "them", "then", "there", "these",
        "they", "this", "to", "us", "was", "we", "will", "with" };

    public LocateHandler (Object context, String repo_url, String doc_id) {
        this.context = context;
        this.repo_url = repo_url;
        this.stop_list = new ArrayList();
        this.doc_id = doc_id;
        for (int i = 0;  i < DEFAULT_STOP_WORDS.length;  i++)
            this.stop_list.add(DEFAULT_STOP_WORDS[i]);
    }

    public LocateHandler (Object context) {
        // google handler
        this.context = context;
        this.repo_url = "http://www.google.com/";
        this.stop_list = new ArrayList();
        this.doc_id = null;
        for (int i = 0;  i < DEFAULT_STOP_WORDS.length;  i++)
            this.stop_list.add(DEFAULT_STOP_WORDS[i]);
    }

    private void runQuery (String querystring) {
        System.err.println("querystring is " + querystring);
        try {
            String querypart;
            URL queryURL;
            if (doc_id == null) {
                querypart = new URI(null, null, "search", "q=" + querystring, null).toString();
                queryURL = new URL(repo_url + querypart);
            } else {
                querypart = new URI(null, null, "action/basic/repo_search", "query=" + querystring, null).toString();
                queryURL = new URL(repo_url + querypart);
            }
            System.err.println("URL is " + queryURL);
            try {
                if (context instanceof AppletContext) {
                    ((AppletContext)context).showDocument(queryURL, "_blank");
                } else if (context == null) {
                    BrowserLauncher.openURL(queryURL.toString());
                }
            } catch (Exception x) {
                System.err.println("Error opening URL " + queryURL + ":");
                x.printStackTrace(System.err);
            }
        } catch (URISyntaxException x) {
            System.err.println("Couldn't form URI:");
            x.printStackTrace(System.err);
        } catch (MalformedURLException x) {
            System.err.println("Bad URL:");
            x.printStackTrace(System.err);
        }
    }

    public void call (Object o) {

        if (o instanceof String) {

            String query = null;
            String trimmed = ((String)o).replaceAll("(\\A([^A-Za-z0-9_-]|\\s)+)|(([^A-Za-z0-9_-]|\\s)+\\z)", "");
            String[] words = trimmed.split("[^A-Za-z0-9_-]*\\s+[^A-Za-z0-9_-]*");
            for (int i = 0;  i < words.length;  i++) {
                if ((words[i].length() > 0) && (!stop_list.contains(words[i].toLowerCase()))) {
                    if (query == null)
                        query = words[i];
                    else
                        query = query + " OR " + words[i];
                }
            }

            runQuery(query);

        } else if ((o instanceof java.util.List) && (((java.util.List)o).size() > 0)) {

            java.util.List theboxes = (java.util.List) o;

            if (theboxes.get(0) instanceof PageText.WordBox) {

                PageText.WordBox b = (PageText.WordBox) theboxes.get(0);
                if (b.partOfSpeechCode() != 0) {
                    // we know the parts of speech -- do something with them someday
                    Iterator boxes = theboxes.iterator();
                    String word, phrase = null;
                    String querystring = null;
                    while(boxes.hasNext()) {
                        b = (PageText.WordBox) (boxes.next());
                        // trim off leading/trailing punctuation
                        word = b.getText().replaceAll("(\\A([^A-Za-z0-9_-]|\\s)+)|(([^A-Za-z0-9_-]|\\s)+\\z)", "");
                        if (b.beginsPhrase()) {
                            if (phrase != null) {
                                phrase = phrase + "\"";
                                if (querystring == null)
                                    querystring = phrase;
                                else
                                    querystring = querystring + " OR " + phrase;
                            }
                            if (!stop_list.contains(word.toLowerCase()))
                                phrase = "\"" + word;
                            else
                                phrase = null;
                        } else {
                            if (!stop_list.contains(word.toLowerCase())) {
                                if (phrase == null)
                                    phrase = "\"" + word;
                                else
                                    phrase = phrase + " " + word;
                            }
                        }
                    }
                    if (phrase != null) {
                        phrase = phrase + "\"";
                        if (querystring == null)
                            querystring = phrase;
                        else
                            querystring = querystring + " OR " + phrase;
                    }
                    runQuery(querystring);

                } else {
                    // we don't know the parts of speech, so just form a string
                    Iterator boxes = theboxes.iterator();
                    String querystring = null;
                    while(boxes.hasNext()) {
                        b = (PageText.WordBox) (boxes.next());
                        querystring = (querystring == null) ? b.getText() : " " + b.getText();
                    }
                    call(querystring);
                }
            }
        }
    }

    public void flush () {
    }
}
        

