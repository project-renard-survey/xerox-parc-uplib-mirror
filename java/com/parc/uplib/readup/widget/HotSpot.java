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

import java.awt.Color;
import java.awt.Point;
import java.awt.Rectangle;
import java.awt.image.BufferedImage;
import java.net.URL;
import java.net.MalformedURLException;
import java.util.Iterator;

/*
 * The HotSpot class provides a rectangular region on a particular page
 * which when clicked on should open, in another window, a particular
 * URL.  You can get a description (the title?) of the page with the
 * getDescr() method.
 *
 * If the width or height of a HotSpot is negative, the HotSpot is assumed
 * to be a span-anchor.  In this case, the "x" value is interpreted as the
 * first byte in the text contents of the document that the span contains,
 * and the "y" value is interpreted as the first byte of the document contents
 * that the span does not contain.  It's meaningless to attempt to use
 * span-anchors without a PageText.
 *
 * The class UpLibHotSpot provides an implementation that is bound to
 * the stored data of an UpLib.
 */
public abstract class HotSpot implements DocViewerCallback, Annotation {

    public static interface Resolver {
        public boolean contains (java.awt.Point p);
        public Rectangle getBounds ();
    }

    public static class RectResolver implements Resolver {

        private Rectangle bbox = null;

        public RectResolver (HotSpot hotspot) {
            bbox = new Rectangle(hotspot.x, hotspot.y, hotspot.width, hotspot.height);
        }

        public boolean contains (java.awt.Point p) {
            return bbox.contains(p);
        }

        public Rectangle getBounds() {
            return bbox;
        }
    }

    public static class SpanResolver implements Resolver {

        private java.util.List boxes = null;
        private Rectangle bbox = null;

        public SpanResolver (HotSpot h, PageText pt) {
            boxes = pt.getWordBoxes (h.x - pt.getTextLocation(), h.y - pt.getTextLocation());
            // now set up bbox
            if (boxes != null) {
                for (Iterator i = boxes.iterator();  i.hasNext();) {
                    PageText.WordBox b = (PageText.WordBox) i.next();
                    if (bbox == null)
                        bbox = b.getBounds();
                    else
                        bbox.add(b);
                }
            }
        }

        public Rectangle getBounds() {
            return bbox;
        }

        public boolean contains (Point p) {
            return ((bbox != null) && bbox.contains(p));
            /*
            if (bbox.contains(p)) {
                if (boxes != null) {
                    for (Iterator i = boxes.iterator();  i.hasNext();) {
                        PageText.WordBox b = (PageText.WordBox) i.next();
                        if (b.contains(p))
                            return true;
                    }
                }
            }
            
            return false;
            */
        }
    }

    public static interface Icon {
        public BufferedImage getImage();
        public Point getLocation();     // location relative to hotspot upper-left corner
        public String getDataURL();     // return data of icon image as a "data:" URL
    }

    public static interface Factory {
        public HotSpot create(DocViewerCallback c,
                              String docid,
                              boolean intrinsic,
                              int pagep,
                              int xp, int yp,
                              int widthp, int heightp,
                              URL u,
                              String descrp);
        public HotSpot create(DocViewerCallback c,
                              String linkid,
                              String docid,
                              boolean intrinsic,
                              int pagep,
                              int xp, int yp,
                              int widthp, int heightp,
                              URL u,
                              String descrp,
                              BufferedImage icon,
                              Point icon_location);
        public HotSpot create(DocViewerCallback c,
                              String linkid,
                              String docid,
                              boolean intrinsic,
                              int pagep,
                              int xp, int yp,
                              int widthp, int heightp,
                              HotSpot h) throws MalformedURLException;
    }        

    private static Factory theFactory = null;

    public static void registerFactory(Factory f) {
        theFactory = f;
    }

    public static HotSpot create(DocViewerCallback c,
                                 String docid,
                                 boolean intrinsic,
                                 int pagep,
                                 int xp, int yp,
                                 int widthp, int heightp,
                                 URL u,
                                 String descrp) {
        if (theFactory != null)
            return theFactory.create(c, docid, intrinsic, pagep, xp, yp, widthp, heightp, u, descrp);
        else
            return null;
    }

    public static HotSpot create(DocViewerCallback c,
                                 String linkid,
                                 String docid,
                                 boolean intrinsic,
                                 int pagep,
                                 int xp, int yp,
                                 int widthp, int heightp,
                                 URL u,
                                 String descrp,
                                 BufferedImage icon,
                                 Point icon_location) {
        if (theFactory != null)
            return theFactory.create(c, linkid, docid, intrinsic, pagep, xp, yp, widthp, heightp, u, descrp, icon, icon_location);
        else
            return null;
    }

    public static HotSpot create(DocViewerCallback c,
                                 String linkid,
                                 String docid,
                                 boolean intrinsic,
                                 int pagep,
                                 int xp, int yp,
                                 int widthp, int heightp,
                                 HotSpot h) throws MalformedURLException {
        if (theFactory != null)
            return theFactory.create(c, linkid, docid, intrinsic, pagep, xp, yp, widthp, heightp, h);
        else
            return null;
    }

    public int x;
    public int y;
    public int width;
    public int height;
    public Resolver resolver;

    public HotSpot(int xp, int yp, int widthp, int heightp) {
        x = xp;
        y = yp;
        width = widthp;
        height = heightp;
        resolver = new RectResolver(this);
    }

    public boolean contains (java.awt.Point p) {
        return resolver.contains(p);
    }

    public Rectangle getBounds() {
        return resolver.getBounds();
    }

    public void setLocation (int xp, int yp) {
        x = xp;
        y = yp;
        resolver = new RectResolver(this);
    }

    public Color getColor() {
        return null;
    }

    abstract public String getDescr();   // returns a (possibly multi-line, possibly HTML) descriptive string about the target

    abstract public String getURL();     // returns the string version of the URL for the hotspot

    abstract public Icon getIcon();     // icon to paint, if any -- often null

    abstract public boolean isIntrinsic();      // link "built-into" document?

    public void flush() {};


}
