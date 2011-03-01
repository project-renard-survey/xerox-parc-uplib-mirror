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

import java.net.*;
import javax.swing.*;
import java.awt.datatransfer.*;
import java.awt.dnd.*;
import java.awt.Image;
import java.awt.Rectangle;
import java.util.Map;
import java.net.URL;
import java.io.IOException;

public class DraggedSelection implements Transferable {

    static final String ourFlavorType = DataFlavor.javaSerializedObjectMimeType +
        ";class=com.parc.uplib.readup.widget.DraggedSelection";
    public static DataFlavor selectionFlavor = null;
    public static DataFlavor stringFlavor = null;
    public static DataFlavor urlFlavor = null;
    public static DataFlavor[] no_icon_flavors = null;
    public static DataFlavor[] has_icon_flavors = null;
    static {
        try {
            selectionFlavor = new DataFlavor(ourFlavorType);
            stringFlavor = new DataFlavor(Class.forName("java.lang.String"), "text/plain");
            urlFlavor = new DataFlavor("application/x-java-url;class=java.net.URL", "standard URL");
            no_icon_flavors = new DataFlavor[] { selectionFlavor, urlFlavor, stringFlavor };
            has_icon_flavors = new DataFlavor[] { selectionFlavor, urlFlavor, stringFlavor, DataFlavor.imageFlavor };
        } catch (ClassNotFoundException e) {
            e.printStackTrace(System.err);
        }
    }

    URL repo;
    String docid;
    int start;
    int end;
    int page;
    public String text;
    Map metadata;
    String human_page_number;
    public boolean full_page;
    public Rectangle rect;
    Image icon;

    public DraggedSelection (URL repo, String docid, int page_index, String human_page_number, int start, int end,
                             String text, Map metadata, boolean full_page) {
        this.repo = repo;
        this.docid = docid;
        this.start = start;
        this.end = end;
        this.page = page_index;
        this.human_page_number = human_page_number;
        this.text = text;
        this.metadata = metadata;
        this.full_page = full_page;
        this.rect = null;
        this.icon = null;
    }

    public DraggedSelection (URL repo, String docid, int page_index, String human_page_number, int start, int end,
                             String text, Map metadata, boolean full_page, Image icon) {
        this.repo = repo;
        this.docid = docid;
        this.start = start;
        this.end = end;
        this.page = page_index;
        this.human_page_number = human_page_number;
        this.text = text;
        this.metadata = metadata;
        this.full_page = full_page;
        this.rect = null;
        this.icon = icon;
    }

    public DraggedSelection (URL repo, String docid, int page_index, String human_page_number,
                             Rectangle r, Map metadata, boolean full_page, Image icon) {
        this.repo = repo;
        this.docid = docid;
        this.start = -1;
        this.end = -1;
        this.page = page_index;
        this.human_page_number = human_page_number;
        this.text = null;
        this.metadata = metadata;
        this.full_page = full_page;
        this.rect = r;
        // in this case, the icon is the really interesting part
        this.icon = icon;
    }

    public Image getIcon() {
        return this.icon;
    }

    public String toString() {
        return "DraggedSelection[" + getDescription() + "]";
    }

    public URL getURL () {
        try {
            String span_indicator = "";
            if ((start >= 0) && (end >= 0) && (end > start))
                span_indicator = "&selection-start=" + start + "&selection-end=" + end;
            else if (rect != null)
                span_indicator = "&left=" + rect.x + "&top=" + rect.y + "&width=" + rect.width + "&height=" + rect.height;
            URL rval = new URL(repo, "/action/basic/dv_show?doc_id=" + docid + "&page=" + page + span_indicator);
            return rval;
        } catch (java.net.MalformedURLException x) {
            x.printStackTrace(System.err);
            return null;
        }
    }

    public String getDescription (boolean full) {
        String title = (metadata != null) ? ((String) metadata.get("title")) : null;
        String rval = "p. " + human_page_number + ",\n";
        if (repo != null)
            rval = rval + repo.toExternalForm() + ", ";
        rval = rval + docid;
        if (title != null)
            rval = title + ", " + rval;
        return ((full && (text != null)) ? (text + "\n[" + rval + "]\n") : rval);
    }

    public String getDescription () {
        return getDescription(false);
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
        return (isURLFlavor(flavor) ||
                isStringFlavor(flavor) ||
                ((icon != null) && isImageFlavor(flavor)) ||
                isSelectionFlavor(flavor));
    }

    public DataFlavor[] getTransferDataFlavors() {
        return ((icon == null) ? no_icon_flavors : has_icon_flavors);
    }

    public Object getTransferData (DataFlavor flavor) throws UnsupportedFlavorException, IOException {

        // System.err.println("getTransferData(" + flavor + ")");

        if (isURLFlavor(flavor)) {

            URL rval = getURL();
            System.err.println("URL is " + rval);
            return rval;

        } else if (isStringFlavor(flavor)) {

            return getDescription(true);

        } else if (isImageFlavor(flavor) && (icon != null)) {

            return getIcon();

        } else if (isSelectionFlavor(flavor)) {

            return this;

        } else

            throw new UnsupportedFlavorException(flavor);
    }
}

