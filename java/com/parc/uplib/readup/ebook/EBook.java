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
import java.nio.ByteBuffer;
import java.text.DecimalFormat;

import com.parc.uplib.readup.widget.*;
import com.parc.uplib.util.MetadataFile;
import com.parc.uplib.util.BrowserLauncher;

class EBook {

    private static DocViewer the_viewer = null;

    private static class URLOpener implements DocViewerCallback {

        private DocViewer the_viewer;

        public URLOpener (DocViewer v) {
            the_viewer = v;
        }

        public void setDocViewer (DocViewer v) {
            the_viewer = v;
        }

        public void call (Object o) {
            if (o instanceof URL) {
                try {
                    String exForm = ((URL)o).toExternalForm();
                    System.err.println("invoking URL " + exForm);
                    if (exForm.startsWith("pageindex:")) {
                        // turn to page N
                        int pageindex = Integer.parseInt(exForm.substring("pageindex:".length()));
                        if (the_viewer != null) {
                            the_viewer.setPage(pageindex);
                        }
                    } else {
                        BrowserLauncher.openURL(exForm);
                    }
                } catch (Exception x) {
                    x.printStackTrace(System.err);
                }
            } else if (o instanceof Integer) {
                if (the_viewer != null) {
                    the_viewer.setPage(((Integer)o).intValue());
                }
            } else {
                System.err.println("Bad URL object " + o + " passed to open-URL.");
            }
        }

        public void flush() {};
    }

    private static String getValue(Map m, String key, String dflt) {
        String o = (String) m.get(key);
        if (o == null)
            return dflt;
        else
            return o;
    }

    private static Dimension getDimension (Map m, String key, Dimension dflt) {
        String v = (String) m.get(key);
        if (v == null)
            return dflt;
        else {
            String[] parts = v.split(",");
            return new Dimension(Integer.parseInt(parts[0]), Integer.parseInt(parts[1]));
        }
    }

    private static AffineTransform getThumbnailTransform (Map map) {

        AffineTransform a = null;

        String thumbnail_translation = getValue(map, "big-thumbnail-translation-points", null);
        String thumbnail_scaling = getValue(map, "big-thumbnail-scaling-factor", null);
        if (thumbnail_scaling == null || thumbnail_translation == null)
            return null;

        String[] parts = thumbnail_translation.split(",");
        double translation_x = Double.parseDouble(parts[0]);
        double translation_y = Double.parseDouble(parts[1]);
        parts = thumbnail_scaling.split(",");
        double scaling_x = Double.parseDouble(parts[0]);
        double scaling_y = Double.parseDouble(parts[1]);
        a = AffineTransform.getScaleInstance(scaling_x, scaling_y);
        a.translate(translation_x, translation_y);

        return a;
    }

    private static DocViewer openDocument (Map map) throws IOException {

        String image_url_prefix;
        boolean show_controls = true;
        boolean show_edge = true;
        URLOpener url_opener = new URLOpener(null);

        // map.list(System.err);
        if (!(map.containsKey("title") &&
              map.containsKey("page-count") &&
              map.containsKey("big-thumbnail-size") &&
              map.containsKey("small-thumbnail-size"))) {
            System.err.println("got bad params for book");
            return null;
        }
        int images_dpi = Integer.parseInt(getValue(map, "images-dpi", "300"));
        int page_count = Integer.parseInt(getValue(map, "page-count", "300"));
        String page_numbers = getValue(map, "page-numbers", null);
        int first_page_number = Integer.parseInt(getValue(map, "first-page-number", "1"));
        Dimension page_size = getDimension(map, "big-thumbnail-size", new Dimension(0, 0));
        Dimension thumbnail_size = getDimension(map, "small-thumbnail-size", new Dimension(0, 0));
        AffineTransform thumbnail_transform = getThumbnailTransform(map);
        int animate_period = 300;
        int rm = 25;
        String title = getValue(map, "title", "(no title)");

        SoftReferenceCache big_thumbnails = new SoftReferenceCache(new PageImageLoader("page image", rm), 20);
        SoftReferenceCache small_thumbnails = new SoftReferenceCache(new PageImageLoader("page thumbnail", 0), 50);
        SoftReferenceCache page_texts = new SoftReferenceCache(new PageTextLoader(), 10);

        HotSpot[] hotspots = null;
        if (thumbnail_transform != null) {
            hotspots = Hotspot.readLinks (thumbnail_transform, url_opener, "thedoc");
        }
        System.err.println("hotspots are " + hotspots +
                           " (" + ((hotspots != null) ? hotspots.length : 0) + ")");

        JFrame topj = new JFrame(title);
        DocViewer dv = null;
        try {
            dv = new DocViewer(big_thumbnails,
                               small_thumbnails,
                               title,
                               "thedoc",
                               null,
                               page_count,
                               first_page_number,
                               page_numbers,
                               0,
                               page_size,
                               thumbnail_size,
                               true,
                               DocViewer.PAGEEDGE_3D_PROGRESS_BAR_TOP,                        /* top edge display */
                               DocViewer.PAGEEDGE_3D_PROGRESS_BAR_BOTTOM,                     /* bottom edge display */
                               false,
                               null,
                               null, 
                               hotspots,
                               null,
                               false,
                               false,
                               0,
                               null,
                               animate_period,                                                /* pageturn animation period */
                               0,
                               page_texts,
                               url_opener,
                               null,
                               null);

            url_opener.setDocViewer(dv);
            dv.setTopLevelWindow(topj);
            topj.getContentPane().add(dv);
            topj.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
            topj.pack();
            topj.setVisible(true);
        } catch (Throwable t) {
            t.printStackTrace(System.err);
        }
        return dv;
    }

    static public void main (String[] argv) {

        boolean debug = false;

        // turn off resizing corner on Mac OS X
        System.setProperty("apple.awt.showGrowBox", "false");
        // Make sure we use the screen-top menu on OS X
        System.setProperty("com.apple.macos.useScreenMenuBar", "true");
        System.setProperty("apple.laf.useScreenMenuBar", "true");

        for (int i = 0;  i < argv.length;  i++) {
            if (argv[i].equals("--debug"))
                debug = true;
            else {
                System.err.println("Invalid option \"" + argv[i] + "\".");
                System.exit(1);
            }
        }

        if (!debug) {
            try {
                File debug_stream = new File("/dev/null");
                if (!(debug_stream.exists() && debug_stream.canWrite())) {
                    debug_stream = File.createTempFile("EBook", ".log");
                    debug_stream.deleteOnExit();
                }
                System.setErr(new PrintStream(new FileOutputStream(debug_stream)));
            } catch (java.security.AccessControlException x) {
                // OK, so we don't redirect stderr
            } catch (Exception e) {
                e.printStackTrace(System.err);
            }
        }
         
        Map map = null;
        try {
            InputStreamReader inps = new InputStreamReader(EBook.class.getResourceAsStream("/metadata.txt"));
            map = new MetadataFile(inps);
            inps.close();
        } catch (java.net.ConnectException x) {
            x.printStackTrace(System.err);
            System.exit(1);
        } catch (ResourceLoader.PrivilegeViolation x) {
            x.printStackTrace(System.err);
            System.exit(1);
        } catch (ResourceLoader.CommunicationFailure x) {
            x.printStackTrace(System.err);
            System.exit(1);
        } catch (Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }

        String title = getValue(map, "title", "Untitled document");
        try {
            System.setProperty("com.apple.mrj.application.apple.menu.about.name", title);
        } catch (java.security.AccessControlException x) {
            // OK, we won't set the property
        }

        try {
            the_viewer = openDocument(map);
        } catch (IOException x) {
            x.printStackTrace(System.err);
            System.exit(1);
        }
    }
}
