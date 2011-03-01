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
import java.awt.image.BufferedImage;
import java.util.Map;
import java.net.URL;
import java.io.IOException;

class DraggedHotspot implements Transferable {

    static final String ourFlavorType = DataFlavor.javaSerializedObjectMimeType +
        ";class=com.parc.uplib.readup.widget.DraggedHotspot";
    public static DataFlavor hotspotFlavor = null;
    public static DataFlavor urlFlavor = null;
    public static DataFlavor stringFlavor = null;
    public static DataFlavor[] no_icon_flavors = null;
    public static DataFlavor[] has_icon_flavors = null;
    static {
        try {
            hotspotFlavor = new DataFlavor(ourFlavorType);
            stringFlavor = new DataFlavor(Class.forName("java.lang.String"), "text/plain");
            urlFlavor = new DataFlavor("application/x-java-url;class=java.net.URL", "standard URL");
            no_icon_flavors = new DataFlavor[] { hotspotFlavor, urlFlavor, stringFlavor };
            has_icon_flavors = new DataFlavor[] { hotspotFlavor, urlFlavor, stringFlavor, DataFlavor.imageFlavor };
        } catch (ClassNotFoundException e) {
            e.printStackTrace(System.err);
        }
    }

    HotSpot hotspot;
    BufferedImage image;

    public DraggedHotspot (HotSpot h) {
        this.hotspot = h;
        HotSpot.Icon i = h.getIcon();
        this.image = (i != null) ? i.getImage() : null;
    }

    public Image getIcon() {
        return this.image;
    }

    public String toString() {
        return "DraggedHotspot[" + this.hotspot.toString() + "]";
    }

    public HotSpot getHotspot() {
        return hotspot;
    }

    // methods for Transferable

    public static boolean isURLFlavor (DataFlavor f) {
        return (f.getMimeType().startsWith("application/x-java-url;"));
    }

    public static boolean isStringFlavor (DataFlavor f) {
        return (stringFlavor.equals(f));
    }

    public static boolean isHotspotFlavor (DataFlavor f) {
        return (hotspotFlavor.equals(f));
    }

    public static boolean isImageFlavor (DataFlavor f) {
        return (DataFlavor.imageFlavor.equals(f));
    }

    public boolean isDataFlavorSupported (DataFlavor flavor) {
        System.err.println("isDataFlavorSupported(" + flavor + ")");
        return (isURLFlavor(flavor) || isStringFlavor(flavor) || isHotspotFlavor(flavor) ||
                (image != null && isImageFlavor(flavor)));
    }

    public DataFlavor[] getTransferDataFlavors() {
        return (image == null) ? no_icon_flavors : has_icon_flavors;
    }

    public Object getTransferData (DataFlavor flavor) throws UnsupportedFlavorException, IOException {

        // System.err.println("getTransferData(" + flavor + ")");

        if (isURLFlavor(flavor)) {

            return this.hotspot.getURL();

        } else if (isStringFlavor(flavor)) {

            return this.hotspot.getDescr() + " <" + this.hotspot.getURL() + ">";

        } else if (isHotspotFlavor(flavor)) {

            return this;

        } else if ((image != null) && isImageFlavor(flavor)) {

            return this.image;

        } else

            throw new UnsupportedFlavorException(flavor);
    }
}

