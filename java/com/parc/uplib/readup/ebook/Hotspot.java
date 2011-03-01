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
import java.util.jar.*;
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
import javax.imageio.stream.*;
import java.net.*;
import java.net.MalformedURLException;
import java.security.MessageDigest;     // for MD5 calculation

import com.parc.uplib.util.Base64;
import com.parc.uplib.util.DataURL;
import com.parc.uplib.util.MetadataFile;
import com.parc.uplib.readup.widget.*;

/*
 * The class UpLibHotSpot provides an implementation of a HotSpot that
 * is bound to the stored data of an UpLib.
 *
 * This class is different from the one found in com.parc.uplib.readup.uplibbinding,
 * because it reads from the stored .link file format, rather than from the wire protocol,
 * which is quite different.
 */

public class Hotspot extends com.parc.uplib.readup.widget.HotSpot {

    private static Hotspot interpretLinkInfo (Map m, AffineTransform t, DocViewerCallback c, String doc_id) {
        String link_id = (String) m.get("id");
        String type = (String) m.get("type");
        String title = (String) m.get("title");
        String from_page = (String) m.get("from-page");
        String from_rect = (String) m.get("from-rect");
        String to_doc = (String) m.get("to-doc");
        String to_page = (String) m.get("to-page");
        String to_uri = (String) m.get("to-uri");
        String from_icon = (String) m.get("from-icon");
        String from_icon_location = (String) m.get("from-icon-location");
        if ((from_rect == null) || (from_page == null) || (link_id == null) ||
            // can't handle links to other "documents"
            (to_doc != null) ||
            // need either a remote URI or a page number in this document
            ((to_uri == null) && (to_page == null)))
            return null;

        if ((to_page != null) && (to_uri == null)) {
            // local intra-document link
        }

        int from_page_number = Integer.parseInt(from_page);
        int to_page_number = (to_page == null) ? 0 : Integer.parseInt(to_page);

        // process from-rect, scaling to thumbnail size
        String[] parts = from_rect.split(",");
        Point2D from_upper_left = t.transform(new Point2D.Double(Double.parseDouble(parts[0]), Double.parseDouble(parts[1])), null);
        Point2D from_dimensions = t.deltaTransform(new Point2D.Double(Double.parseDouble(parts[2]), Double.parseDouble(parts[3])), null);

        // handle icon URL and location, if any
        Point2D icon_location = null;
        if ((from_icon != null) && (from_icon_location != null)) {
            parts = from_icon_location.split(",");
            icon_location = t.transform(new Point2D.Double(Double.parseDouble(parts[0]), Double.parseDouble(parts[0])), null);
        }

        if (to_uri != null) {
            URL u;
            try {
                u = new URL(to_uri);
            } catch (MalformedURLException x) {
                System.err.println("Bad URL:  to-uri is " + to_uri + ", to-doc is " + to_doc + ", to-page is " + to_page + ", title is \"" + title + "\"");
                x.printStackTrace(System.err);
                return null;
            }
            
            return new Hotspot (doc_id, link_id, c,
                                from_page_number,
                                (int) Math.round(from_upper_left.getX()), (int) Math.round(from_upper_left.getY()),
                                (int) Math.round(from_dimensions.getX()), (int) Math.round(from_dimensions.getY()),
                                u, to_page_number, title, from_icon,
                                (icon_location == null) ? null : new Point((int) Math.round(icon_location.getX()),
                                                                           (int) Math.round(icon_location.getY())));
        } else {
            return new Hotspot (doc_id, link_id, c,
                                from_page_number,
                                (int) Math.round(from_upper_left.getX()), (int) Math.round(from_upper_left.getY()),
                                (int) Math.round(from_dimensions.getX()), (int) Math.round(from_dimensions.getY()),
                                null, to_page_number, title, from_icon,
                                (icon_location == null) ? null : new Point((int) Math.round(icon_location.getX()),
                                                                           (int) Math.round(icon_location.getY())));
        }
    }

    public static HotSpot[] readLinks (AffineTransform t, DocViewerCallback c, String doc_id) {
        HashMap h = new HashMap();
        Vector links = new Vector();

        try {
            // find jar file and read links files from it
            String[] parts = Hotspot.class.getResource("/com/parc/uplib/readup/ebook/Hotspot.class").getFile().split("!");
            if (parts[0].startsWith("file:")) {
                // System.err.println("URL filename is " + parts[0]);
                JarFile j = new JarFile(parts[0].substring(5));
                System.err.println("Jarfile is " + j);
                Enumeration e = j.entries();
                while (e.hasMoreElements()) {
                    JarEntry je = (JarEntry) e.nextElement();
                    // System.err.println ("   jarfile entry " + je.getName());
                    if (je.getName().endsWith(".links")) {
                        BufferedReader is = new BufferedReader(new InputStreamReader(j.getInputStream(je)));
                        // System.err.println("      reading " + je.getName() + " with input stream " + is);
                        h.clear();
                        while (MetadataFile.fillMap(is, h) != null) {
                            Hotspot n;
                            if ((n = interpretLinkInfo(h, t, c, doc_id)) != null) {
                                // System.err.println("         adding link " + n);
                                links.add(n);
                            }
                            h.clear();
                        }
                        is.close();
                    }
                }
                h.clear();
            }
        } catch (java.io.IOException x) {
            x.printStackTrace(System.err);
        }
        HotSpot[] rvalue = new HotSpot[links.size()];
        return (HotSpot[]) links.toArray(rvalue);
    }

    private class Iconic implements HotSpot.Icon {
        private BufferedImage im;
        private Point location;
        public Iconic (String iconurl, Point location) throws java.io.IOException {
            this.im = DataURL.decode(iconurl);
            this.location = location;
        }
        public BufferedImage getImage () {
            return this.im;
        }
        public Point getLocation() {
            return this.location;
        }
        public String getDataURL() {
            try {
                return DataURL.encode(im);
            } catch (Exception e) {
                System.err.println("Exception raised attempting to convert image to data: url");
                e.printStackTrace(System.err);
                return null;
            }
        }
    }

    private URL url;
    private int from_page;
    private int to_page;
    private String descr;
    private String linkid;
    private Annotation.Timestamp timestamp;
    private Annotation.Type type;
    private Iconic icon;
    private boolean intrinsic;
    private DocViewerCallback callback;
    private String docid;

    public Hotspot (String doc_id, String linkid, DocViewerCallback callback,
                    int pagep, int xp, int yp, int widthp, int heightp,
                    URL u, int to_page, String descrp, String im_url, Point image_location) {
        super(xp, yp, widthp, heightp);
        url = u;
        docid = doc_id;
        this.from_page = pagep;
        this.to_page = to_page;
        descr = descrp;
        this.callback = callback;
        this.linkid = linkid;
        this.type = Annotation.Type.LINK;
        this.intrinsic = true;
        this.callback = callback;
        timestamp = new Annotation.Timestamp(Annotation.Timestamp.CREATED);
        icon = null;
        if ((im_url != null) && (image_location != null))
            try {
                icon = new Iconic(im_url, image_location);
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
    }

    /* methods for Annotation */

    public int pageIndex () {
        return from_page;
    }

    public String docId() {
        return docid;
    }

    public String linkId() {
        return linkid;
    }

    public Annotation.Timestamp timestamp() {
        return timestamp;
    }

    public Annotation.Type getType() {
        return type;
    }

    public java.awt.Rectangle getBounds() {
        return super.getBounds();
    }

    /* methods for HotSpot */

    public String getDescr() {
        return descr;
    }

    public String getURL() {
        if (url == null)
            return "pageindex:" + to_page;
        else
            return url.toExternalForm();
    }

    public HotSpot.Icon getIcon () {
        return icon;
    }

    public boolean isIntrinsic() {
        return intrinsic;
    }

    /* methods for DocViewerCallback */

    public void call (Object o) {
        if (callback != null) {
            if (url == null)
                callback.call(new Integer(to_page));
            else
                callback.call(url);
        }
    }

    public void flush () {
        if (callback != null)
            callback.flush();
    }
}
