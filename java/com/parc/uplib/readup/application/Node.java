/*
 *  This file is part of the "UpLib 1.7.11" release.
 *  Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
 *  
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *  
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *  
 *  You should have received a copy of the GNU General Public License along
 *  with this program; if not, write to the Free Software Foundation, Inc.,
 *  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

package com.parc.uplib.readup.application;

import javax.swing.JApplet;
import java.applet.*;
import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.datatransfer.*;
import java.awt.event.*;
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
import java.net.URL;

import com.parc.uplib.readup.uplibbinding.Repository;
import com.parc.uplib.readup.widget.DocViewerCallback;


interface NodeListener {
    public void nodeClicked(Node n);
}

public class Node extends java.awt.Rectangle implements Transferable, Serializable, DocViewerCallback {

    private final static Color NOSCORE = new Color(.602f, .676f, .726f);
    private final static Color BACKGROUND_COLOR = new Color(.5f, .5f, .5f);
    private final static Color PRESSED_WASH = new Color(.937f, .157f, .055f, 0.5f);
    private final static Color TRANSPARENT = new Color(0, 0, 0, 0);
    
    static final String ourFlavorType = DataFlavor.javaSerializedObjectMimeType +
        ";class=com.parc.uplib.readup.application.Node";
    public static DataFlavor selectionFlavor = null;
    public static DataFlavor stringFlavor = null;
    public static DataFlavor urlFlavor = null;
    // public static DataFlavor[] no_icon_flavors = null;
    // public static DataFlavor[] has_icon_flavors = null;
    public static DataFlavor[] selection_flavor = null;
    static {
        try {
            selectionFlavor = new DataFlavor(ourFlavorType);
            stringFlavor = new DataFlavor(Class.forName("java.lang.String"), "text/plain");
            urlFlavor = new DataFlavor("application/x-java-url;class=java.net.URL", "standard URL");
            // no_icon_flavors = new DataFlavor[] { selectionFlavor, urlFlavor, stringFlavor };
            // has_icon_flavors = new DataFlavor[] { selectionFlavor, urlFlavor, stringFlavor, DataFlavor.imageFlavor };
            selection_flavor = new DataFlavor[] { selectionFlavor };
        } catch (ClassNotFoundException e) {
            e.printStackTrace(System.err);
        }
    }

    static FontMetrics fm = null;
        
    static public void setFontMetrics(FontMetrics fontmetrics) {
        fm = fontmetrics;
    }

    public static String wrapString (int maxwidth, String label, String interline_string) {
        String result = "";
        String[] parts = label.split(" ");
        String newlabel = parts[0];
        for (int j = 1, k = 0;  j < parts.length;  j++) {
            if (newlabel.endsWith("\n")) {
                result += (newlabel.substring(0, newlabel.length() - 1) + interline_string);
                newlabel = parts[j];
            } else if (fm.stringWidth(newlabel + " " + parts[j]) < maxwidth)
                newlabel += (" " + parts[j]);
            else {
                result += (newlabel + interline_string);
                newlabel = parts[j];
            }
        }
        if (newlabel.length() > 0)
            result += (newlabel + interline_string);
        return result;
    }

    private static String createHTMLTooltipString (int maxwidth, String title, String authors, int year, int pagecount) {
        String ys = "";
        if (pagecount != 0)
            ys += pagecount + " page" + ((pagecount > 1) ? "s" : "");
        if (year >= 0)
            ys += ((pagecount != 0) ? ", " : "") + year;
        if ((year >= 0) || (pagecount != 0))
            ys += "</i>";
        return ("<html><b>" + wrapString(maxwidth, title, "<br>\n") + "</b>" +
                wrapString(maxwidth, authors, "<br>\n") +
                "<i>" + wrapString(maxwidth, ys, "<br>\n") + "</i></html>");
    }

    private Object reference;
    private int border_width;
    private String tooltip = null;
    private Color backgroundColor;
    private BufferedImage icon = null;

    public Node (Repository.Document doc, float score) {
        super();
        this.reference = doc;
        BufferedImage im = doc.getIcon();
        int maxwidth = (im != null) ? (int) Math.round(1.5 * im.getWidth()) : 150;
        String title = doc.getTitle();
        Iterator ait = doc.getAuthors();
        String authors = "";
        while ((ait != null) && ait.hasNext()) {
            if (authors.length() > 0)
                authors += "; ";
            authors += ((Repository.Author) ait.next()).getName();
        }
        tooltip = createHTMLTooltipString(maxwidth, (title == null) ? doc.getID() : title, authors, doc.getYear(), doc.getPageCount());
        border_width = 5;
        backgroundColor = (score < 0) ? BACKGROUND_COLOR : new Color(0f, 1.0f, 0f, score);
        resize(im);
    }

    private void resize (BufferedImage im) {
        width = ((im != null) ? im.getWidth() : 150) + (2 * border_width);
        // height = ((im != null) ? im.getHeight() : 200) + (3 * border_width) + legend.height;
        height = ((im != null) ? im.getHeight() : 200) + (2 * border_width);
    }

    public void draw (Graphics2D g, int at_x, int at_y, boolean pressed) {
        g.setColor(backgroundColor);
        g.fillRoundRect(at_x, at_y, width, height, 8, 8);
        if (reference instanceof Repository.Document) {
            BufferedImage im = ((Repository.Document)reference).getIcon();
            // g.setColor(BLACK);
            // legend.draw(g, x + border_width, y + border_width);
            if (im != null)
                g.drawImage(im, at_x+border_width, at_y + border_width, im.getWidth(), im.getHeight(), null);
        }
        if (pressed) {
            g.setColor(PRESSED_WASH);
            g.fillRoundRect(at_x, at_y, width, height, 8, 8);
        }
    }
        
    public void draw (Graphics2D g, boolean pressed) {
        draw(g, this.x, this.y, pressed);
    }
        
    public BufferedImage getIcon (Component c) {
        if (icon == null) {
            icon = c.getGraphicsConfiguration().createCompatibleImage(this.width, this.height, Transparency.TRANSLUCENT);
            Graphics2D g = (Graphics2D) icon.getGraphics();
            g.setColor(TRANSPARENT);
            g.fillRect(0, 0, this.width, this.height);
            g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC, 0.7f));
            draw(g, 0, 0, false);
        }
        return icon;
    }

    public String getLabel() {
        return tooltip;
    }

    public String getLabel(Point p) {
        return (contains(p) ? getLabel() : null);
    }

    public String toString() {
        return "<" + super.toString() + " " + reference.toString() + ">";
    }

    Repository.Document getDocument() {
        if (reference instanceof Repository.Document)
            return ((Repository.Document)reference);
        else
            return null;
    }

    // methods for Transferable

    public static boolean isURLFlavor (DataFlavor f) {
        return (f.getMimeType().startsWith("application/x-java-url;"));
    }

    public static boolean isStringFlavor (DataFlavor f) {
        return (stringFlavor.equals(f));
    }

    public static boolean isSelectionFlavor (DataFlavor f) {
        return (selectionFlavor.equals(f));
    }

    public static boolean isImageFlavor (DataFlavor f) {
        return (DataFlavor.imageFlavor.equals(f));
    }

    public boolean isDataFlavorSupported (DataFlavor flavor) {
        System.err.println("isDataFlavorSupported(" + flavor + ")");
        // return (isURLFlavor(flavor) || isStringFlavor(flavor) || isSelectionFlavor(flavor));
        return (isSelectionFlavor(flavor));
    }

    public DataFlavor[] getTransferDataFlavors() {
        return selection_flavor;
        // return no_icon_flavors;
    }

    public Object getTransferData (DataFlavor flavor) throws UnsupportedFlavorException, IOException {

        // System.err.println("getTransferData(" + flavor + ")");

        if (isSelectionFlavor(flavor)) {

            return this;

        } else

            throw new UnsupportedFlavorException(flavor);
    }

    // for Serializable
    
    private void writeObject (ObjectOutputStream o) throws IOException {
        if (reference instanceof Repository.Document) {
            o.writeObject(new URL(((Repository.Document)reference).getRepository().getURL(),
                                  "/document/" + ((Repository.Document)reference).getID()));
        } else
            o.writeObject(reference);
        o.writeInt(border_width);
        o.writeObject(tooltip);
        o.writeObject(backgroundColor);
    }

    private void readObject (ObjectInputStream o) throws IOException, ClassNotFoundException {
        reference = o.readObject();
        if (reference instanceof URL)
            reference = Repository.get((URL) reference);
        border_width = o.readInt();
        tooltip = (String) (o.readObject());
        backgroundColor = (Color)(o.readObject());
        icon = null;
    }

    // for DocViewerCallback

    public void call (Object o) {
        if (o instanceof BufferedImage) {
            resize((BufferedImage) o);
        } else if (o instanceof Exception) {
            System.err.println("Exception fetching icon image for " + this);
        }
    }

    public void flush() {};
}
