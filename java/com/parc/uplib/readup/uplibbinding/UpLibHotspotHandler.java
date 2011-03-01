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

import com.parc.uplib.util.Base64;
import com.parc.uplib.readup.widget.*;

public class UpLibHotspotHandler extends AnnotationStreamHandler {

    static final int BUFSIZE = 1 << 16;

    public String uplib_password;
    String uplib_cookie;
    URL uplib_hotspot_sink;
    URL uplib_hotspot_source;
    String document_id;
    DocViewerCallback hotspot_context;

    public UpLibHotspotHandler (String doc_id, String password, URL sink, URL source, DocViewerCallback context) {
        super(BUFSIZE);
        uplib_password = password;
        uplib_cookie = null;
        uplib_hotspot_source = source;
        uplib_hotspot_sink = sink;
        document_id = doc_id;
        hotspot_context = context;
        HotSpot.registerFactory(new UpLibHotSpot.Factory());
    }

    public void setCookie (String cookie) {
        this.uplib_cookie = cookie;
    }

    public byte[] encode (String doc_id, int page_no, int selector, Annotation o, int format_version)
        throws IOException {
        if (format_version == 0)
            format_version = 2;
        return encodeHotspot(o, format_version);
    }

    public static byte[] encodeHotspot (Annotation an, int format_version) throws IOException {
        if (format_version != 2) {
            throw new IOException("Hotspot externalized format " + format_version + " not supported.");
        } else if (! (an instanceof UpLibHotSpot)) {
            throw new IOException("Not Hotspot:  " + an);
        } else {
            UpLibHotSpot uhs = (UpLibHotSpot) an;
            HotSpot.Icon icon = uhs.getIcon();
            String descr = Base64.encodeBytes(uhs.getDescr().getBytes("UTF-8"), Base64.DONT_BREAK_LINES);
            System.err.println("encoded icon is " + descr);
            String form = uhs.linkId() + " " + uhs.docId() + " " + uhs.pageIndex() + " " + uhs.x + " " + uhs.y + " " + uhs.width + " " + uhs.height + (uhs.isIntrinsic() ? " true" : " false") + " nocolor " + uhs.getURL() + "\n" + descr + "\n";
            if (icon != null) {
                Point loc = icon.getLocation();
                form = form + loc.getX() + " " + loc.getY() + " " + icon.getDataURL() + "\n";
            } else {
                form = form + "noicon\n";
            }
            return form.getBytes("UTF-8");
        }
    }

    public HotSpot[] readHotspots (DocViewerCallback cb) {
        return UpLibHotSpot.readHotspots (uplib_hotspot_source, uplib_password, uplib_cookie, (cb != null) ? cb : hotspot_context);
    }

    protected void initializeOutputStream (OutputStream os)
        throws IOException {
        os.write("2\n0\n".getBytes("US-ASCII"));
    }

    protected void emptyBuffer (ByteArrayOutputStream b) {
        final byte[] buf = b.toByteArray();
        System.err.println("Emptying links buffer (" + buf.length + " bytes) for " + uplib_hotspot_sink);

        /*
        try {
            OutputStream f = new FileOutputStream("/tmp/hotspots");
            f.write(buf);
            f.close();
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        */

        UpLibBufferEmptier worker = new UpLibBufferEmptier(buf,
                                                           uplib_hotspot_sink,
                                                           "application/x-uplib-hotspots",
                                                           uplib_password);
        worker.setCookie(uplib_cookie);
        worker.start(-20);
        b.reset();
    }
}

