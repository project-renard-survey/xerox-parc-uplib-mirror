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

package com.parc.uplib.readup.application;

import com.parc.uplib.util.Configurator;
import com.parc.uplib.util.CertificateHandler;
import com.parc.uplib.util.BrowserLauncher;
import com.parc.uplib.util.EmacsKeymap;
import com.parc.uplib.util.DataURL;
import com.parc.uplib.util.MetadataFile;
import com.parc.uplib.util.FileBox;

import javax.swing.JApplet;
import javax.swing.tree.*;
import java.applet.*;
import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.datatransfer.*;
import java.awt.dnd.*;
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
import javax.net.ssl.*;
import javax.security.cert.*;

import com.parc.uplib.readup.uplibbinding.*;

public class CardCatalog {

    static Font report_font = Font.decode("1942report-PLAIN-16");
    static Font enigma_font = Font.decode("augie-PLAIN-12");
    public static TexturePaint pine_background;

    static {
        try {
            BufferedImage pine_img = DataURL.decode("data:image/png;base64,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");
            pine_background = new TexturePaint (pine_img, new Rectangle(0,0,pine_img.getWidth(null), pine_img.getHeight(null)));
        } catch (Exception x) {
            x.printStackTrace(System.err);
            System.err.println("Can't read pine image");
            System.exit(1);
        }
    }

    private static String listDocument (Repository.Document d, String spacing) {
        String contents;
        contents = "<b>" + d.getTitle() + "</b>";
        Iterator i = d.getAuthors();
        if (i.hasNext())
            contents += "\n" + spacing + ((Repository.Author)(i.next())).getName();
        while (i.hasNext())
            contents += "; " + ((Repository.Author)(i.next())).getName();
        contents += spacing;
        int year = d.getYear();
        if (year >= 0)
            contents += "<i>(" + Integer.toString(year) + ")</i> ";
        contents += "[<a href=\"" + d.getRepository().getURLString() + "action/basic/dv_show?doc_id=" + d.getID() + "\">open</a>]";
        contents += "<br>\n[<a href=\"" + d.getRepository().getURLString() + "action/basic/doc_meta?doc_id=" + d.getID() + "\">edit metadata in browser window</a>]";
        return contents;
    }

    public static FileBox.CardRun AuthorsCardRun (Repository.Author[] authors) {

        String[] titles = new String[authors.length];
        String[] contents = new String[authors.length];

        for (int i = 0;  i < authors.length;  i++) {
            titles[i] = authors[i].getName() + "  [author]";
            String content = "<html><body>\n";
            Iterator i2 = authors[i].iterator();
            while (i2.hasNext()) {
                Repository.Document d = (Repository.Document) (i2.next());
                content += "<p style=\"background-color: #e0f0f8; border-width: 5px;\">" + listDocument(d, "<br>") + "</p>\n";
            }
            content += "</body></html>";
            contents[i] = content;
        }
        return new FileBox.StaticCardRun (titles, contents);
    }

    public static FileBox DateBox (Repository repo, HyperlinkListener hl) throws IOException {
        repo.readIndexFile();
        return DateBox (repo.getDocuments(), hl);
    }

    public static FileBox DateBox (Iterator documents, HyperlinkListener hl) throws IOException {

        HashMap years = new HashMap();
        ArrayList otherslist = new ArrayList();
        while (documents.hasNext()) {
            Repository.Document d = (Repository.Document) documents.next();
            int year = d.getYear();
            // System.out.println(d.getID() + " " + d.getMetadataProperty("date") + " * " + d.getDate() + " => " + year);
            if (year > 0) {
                ArrayList yearlist = (ArrayList)(years.get(new Integer(year)));
                if (yearlist == null) {
                    yearlist = new ArrayList();
                    years.put(new Integer(year), yearlist);
                }
                yearlist.add(d);
            } else {
                otherslist.add(d);
            }
        }
        // System.err.println("Otherslist is " + otherslist.size());
        if (otherslist.size() > 0)
            years.put(new Integer(-1), otherslist);

        String[] titles = new String[years.size()];
        FileBox.CardRun[] runs = new FileBox.CardRun[years.size()];
        Iterator keys = (new TreeSet(years.keySet())).iterator();
        int index = 0;
        while (keys.hasNext()) {
            
            Integer key = (Integer) (keys.next());
            titles[index] = (key.intValue() == -1) ? "???" : key.toString();
            ArrayList al = (ArrayList) (years.get(key));
            // System.err.println("year " + key + " => " + al.size() + " docs");
            runs[index] = documentsCardRun((Repository.Document[]) (al.toArray(new Repository.Document[al.size()])), hl);
            index += 1;
        }

        FileBox cb = FileBox.create(titles, runs, 5, 30, report_font, null, 600, 400);
        cb.addHyperlinkListener(hl);
        return cb;
    }

    public static FileBox CollectionsBox (Repository repo, HyperlinkListener hl) throws IOException {

        repo.readIndexFile();

        HashMap names = new HashMap();
        Iterator collections = repo.getCollections();
        while (collections.hasNext()) {
            Repository.Collection c = (Repository.Collection) (collections.next());
            names.put(c.getName(), documentsCardRun(c.getDocuments(), hl));
        }

        String[] keys = (String[]) (new TreeSet(names.keySet())).toArray(new String[names.size()]);
        FileBox.CardRun[] runs = new FileBox.CardRun[names.size()];
        for (int i = 0;  i < keys.length;  i++)
            runs[i] = (FileBox.CardRun) (names.get(keys[i]));

        FileBox cb = FileBox.create(keys, runs, 3, 30, enigma_font, null, 500, 300);
        cb.addHyperlinkListener(hl);
        return cb;
    }

    public static FileBox CategoriesBox (Repository repo, HyperlinkListener hl) throws IOException {

        repo.readIndexFile();

        HashMap names = new HashMap();
        Iterator categories = repo.getCategories();
        while (categories.hasNext()) {
            Repository.Category c = (Repository.Category) (categories.next());
            names.put(c.getName(), documentsCardRun(c.getDocuments(), hl));
        }

        String[] keys = (String[]) (new TreeSet(names.keySet())).toArray(new String[names.size()]);
        FileBox.CardRun[] runs = new FileBox.CardRun[names.size()];
        for (int i = 0;  i < keys.length;  i++)
            runs[i] = (FileBox.CardRun) (names.get(keys[i]));

        FileBox cb = FileBox.create(keys, runs, 4, 30, null, null, 600, 400);
        cb.addHyperlinkListener(hl);
        return cb;
    }

    public static FileBox AuthorsBox (Repository repo, HyperlinkListener hl) throws IOException {
        repo.readIndexFile();
        return AuthorsBox(repo.getAuthors(), hl);
    }

    public static FileBox AuthorsBox (Iterator authors, HyperlinkListener hl) {

        HashMap c = new HashMap(27);
        for (char ch = 'A';  ch <= 'Z';  ch += 1)
            c.put(new String(new char[] {ch}), new ArrayList());
        c.put("other", new ArrayList());

        while (authors.hasNext()) {
            Repository.Author author = (Repository.Author) (authors.next());
            String name = author.getName();
            String slot = ((name.length() > 0) ? name.substring(0, 1).toUpperCase() : "1");
            if ((slot.charAt(0) < 'A') || (slot.charAt(0) > 'Z'))
                slot = "other";
            ((ArrayList) (c.get(slot))).add(author);
        }

        String[] titles = new String[27];
        FileBox.CardRun[] card_sets = new FileBox.CardRun[27];
        for (char ch = 'A';  ch <= 'Z';  ch += 1) {
            titles[(ch - 'A')] = new String(new char[] {ch});
            ArrayList l = (ArrayList) (c.get(titles[(ch - 'A')]));
            // System.err.println("FileBox.CardRun for " + titles[(ch - 'A')] + " (" + l.size() + ")");
            FileBox.CardRun cr = AuthorsCardRun((Repository.Author[]) (l.toArray(new Repository.Author[l.size()])));
            card_sets[(ch - 'A')] = cr;
        }
        titles[26] = "other";
        ArrayList l = (ArrayList) (c.get(titles[26]));
        FileBox.CardRun cr = AuthorsCardRun((Repository.Author[]) (l.toArray(new Repository.Author[l.size()])));
        card_sets[26] = cr;
        FileBox cb = FileBox.create(titles, card_sets, 8, 35, null, null, 500, 300);
        cb.addHyperlinkListener(hl);
        return cb;
    }

    private static String getAbstract (Repository.Document d) {
        String i = d.getMetadataProperty("abstract");
        if (i == null) {
            i = d.getMetadataProperty("comment");
            if (i == null) {
                i = d.getMetadataProperty("summary");
                if (i == null)
                    return null;
                else
                    return "<small>SUMMARY:</small> " + i;
            } else {
                return "<small>COMMENT:</small> " + i;
            }
        } else {
            return "<small>ABSTRACT:</small> " + i;
        }
    }

    public static String[] splitString (int maxwidth, String tosplit, FontMetrics fm) {
            
        ArrayList results = new ArrayList();
        String[] parts = tosplit.split(" ");
        String newlabel = parts[0];
        for (int j = 1, k = 0;  j < parts.length;  j++) {
            if (newlabel.endsWith("\n")) {
                results.add(newlabel.substring(0, newlabel.length() - 1));
                newlabel = parts[j];
            } else if (fm.stringWidth(newlabel + " " + parts[j]) < maxwidth)
                newlabel += (" " + parts[j]);
            else {
                results.add(newlabel);
                newlabel = parts[j];
            }
        }
        if (newlabel.length() > 0)
            results.add(newlabel);
        return (String[]) results.toArray(new String[results.size()]);
    }

    public static String listMetadata(Repository.Document d) {
        MetadataFile mfile = d.getMetadata();
        String rval = "<p><small>METADATA:</small><br><tt><pre>\n";
        if (mfile == null) {
            return "";
        } else {
            Iterator i = mfile.entrySet().iterator();
            while (i.hasNext()) {
                Map.Entry e = (Map.Entry) (i.next());
                String key = (String) e.getKey();
                String value = (String) e.getValue();
                rval += (key + ": " + value + "\n");
            }
        }
        rval += "</pre></tt></p>";
        return rval;
    }

    public static FileBox.StaticCardRun documentsCardRun (Repository.Document[] documents, HyperlinkListener listener) throws IOException {

        String[] titles = new String[documents.length];
        String[] contents = new String[documents.length];
        URL[] urls = new URL[documents.length];

        for (int i = 0;  i < documents.length;  i++) {
            int year = documents[i].getYear();
            titles[i] = documents[i].getTitle() + ((year >= 0) ? ("  [" + Integer.toString(year) + "]") : "");
            urls[i] = new URL(documents[i].getRepository().getURLString() + "action/basic/dv_show?doc_id=" + documents[i].getID());
            String summary = getAbstract(documents[i]);
            String thumbnail_url = documents[i].getRepository().getURLString() + "docs/" + documents[i].getID() + "/thumbnails/first.png";
            contents[i] = "<html><body>" +
                "<table width=\"100%\"><tr>" +
                "<td align=left>" + "<a border=0 href=\"" + urls[i] + "\">" +
                "<img border=1 bdcolor=\"lightgray\" src=\"" + thumbnail_url + "\"></a>" + "</td>" +
                "<td align=left valign=top><p>" + listDocument(documents[i], "<p>") + "</p></td>" +
                "</tr>" +
                "<tr><td colspan=2><p>" + ((summary == null) ? "[no abstract]" : summary) + "</td></tr></table>" +
                listMetadata(documents[i]) +
                "</body></html>";
            // System.err.println("contents are " + contents[i]);
        }
        return new FileBox.DocumentCardRun (titles, contents, urls, listener);
    }

    public static void main (String[] argv) {
        try {

            CertificateHandler.ignoreCerts();

            Repository r = new Repository(new URL(argv[0]), (String) argv[1]);
            r.readIndexFile();

            UpLibShowDoc app = new UpLibShowDoc(new Closer(), null,
                                                argv[0], argv[1], null, null,
                                                false, 0.0f, 300, true, false,
                                                new Configurator());

            // list fonts

            /*
            Font[] fonts = GraphicsEnvironment.getLocalGraphicsEnvironment().getAllFonts();
            for (int i = 0;  i < fonts.length;  i++)
                System.err.println(fonts[i].getName());
            */

            // UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName());

            // Make sure we use the screen-top menu on OS X
            System.setProperty("com.apple.macos.useScreenMenuBar", "true");
            System.setProperty("apple.laf.useScreenMenuBar", "true");
        
            JFrame f;
            JComponent w;

            f = new JFrame("collections in " + argv[0]);
            w = CollectionsBox(r, app);
            f.getContentPane().add(w);
            f.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
            f.pack();
            f.setVisible(true);

            /*
            f = new JFrame("categories in " + argv[0]);
            w = CategoriesBox(r, app);
            f.getContentPane().add(w);
            f.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
            f.pack();
            f.setVisible(true);
            */
            
            JWindow t = new JWindow();
            w = AuthorsBox(r.getAuthors(), app);
            t.setBackground(new Color(255, 255, 255, 0));
            t.setContentPane(w);
            t.pack();
            System.err.println("f.size is " + t.getSize());
            t.setVisible(true);

            /*
            f = new JFrame("documents by date in " + argv[0]);
            w = DateBox(r.getDocuments(), app);
            f.getContentPane().add(w);
            f.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
            f.pack();
            f.setVisible(true);
            */

        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
    }
        
}
