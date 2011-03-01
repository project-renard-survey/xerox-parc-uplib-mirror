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
import javax.imageio.stream.*;
import java.net.*;
import java.net.MalformedURLException;
import java.security.MessageDigest;     // for MD5 calculation

import com.parc.uplib.util.Base64;
import com.parc.uplib.util.DataURL;
import com.parc.uplib.readup.widget.*;

/*
 * The class UpLibHotSpot provides an implementation of a HotSpot that
 * is bound to the stored data of an UpLib.
 */

public class UpLibHotSpot extends HotSpot {

    private class Iconic implements HotSpot.Icon {
        private BufferedImage im;
        private Point location;
        public Iconic (BufferedImage im, Point location) {
            this.im = im;
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
            } catch (IOException x) {
                return null;
            }
        }
    }

    private DocViewerCallback callback;
    private URL url;
    private int page;
    private String descr;
    private String docid;
    private String linkid;
    private Annotation.Timestamp timestamp;
    private Annotation.Type type;
    private Iconic icon;
    private boolean intrinsic;
    private Color color = null;

    public UpLibHotSpot (DocViewerCallback c, String docid, boolean intrinsic, int pagep, int xp, int yp, int widthp, int heightp, URL u, String descrp) {
        super(xp, yp, widthp, heightp);
        callback = c;
        url = u;
        page = pagep;
        descr = descrp;
        this.docid = docid;
        this.type = Annotation.Type.LINK;
        timestamp = new Annotation.Timestamp(Annotation.Timestamp.CREATED);
        icon = null;
        this.intrinsic = intrinsic;

        // this.linkid = ???;
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            md.update((docid + ";" + pagep + ";" + xp + ";" + yp + ";" + widthp + ";" + heightp + ";" + descrp).getBytes("UTF-8"));
            this.linkid = Base64.encodeBytes(md.digest(), Base64.DONT_BREAK_LINES);
        } catch (Exception e) {
            System.err.println("Exception trying to MD5-create a linkid");
            e.printStackTrace(System.err);
            this.linkid = null;
        }
    }

    public UpLibHotSpot (DocViewerCallback c, String linkid, String docid, boolean intrinsic, int pagep,
                         int xp, int yp, int widthp, int heightp,
                         URL u, String descrp, BufferedImage im, Point image_location,
                         Color color) {
        super(xp, yp, widthp, heightp);
        callback = c;
        url = u;
        page = pagep;
        descr = descrp;
        this.docid = docid;
        this.linkid = linkid;
        this.type = Annotation.Type.LINK;
        this.intrinsic = intrinsic;
        this.color = color;
        timestamp = new Annotation.Timestamp(Annotation.Timestamp.CREATED);
        if ((im != null) && (image_location != null))
            icon = new Iconic(im, image_location);
        else
            icon = null;
    }

    public UpLibHotSpot (DocViewerCallback c, String linkid, String docid, boolean intrinsic, int pagep,
                         int xp, int yp, int widthp, int heightp, HotSpot h) throws java.net.MalformedURLException {
        super(xp, yp, widthp, heightp);
        callback = c;
        url = new URL(h.getURL());
        page = pagep;
        descr = h.getDescr();
        this.docid = docid;
        this.linkid = linkid;
        this.type = Annotation.Type.LINK;
        this.intrinsic = intrinsic;
        timestamp = new Annotation.Timestamp(Annotation.Timestamp.CREATED);
        HotSpot.Icon ic = h.getIcon();
        if (ic != null)
            icon = new Iconic(ic.getImage(), ic.getLocation());
        else
            icon = null;
    }

    public int pageIndex () {
        return page;
    }

    public String docId() {
        return docid;
    }

    public String linkId() {
        return linkid;
    }

    public boolean isIntrinsic() {
        return intrinsic;
    }

    public Annotation.Timestamp timestamp() {
        return timestamp;
    }

    public Annotation.Type getType() {
        return type;
    }

    public String getDescr() {
        return descr;
    }

    public String getURL() {
        return url.toExternalForm();
    }

    public Color getColor() {
        return color;
    }

    public HotSpot.Icon getIcon () {
        return icon;
    }

    public void call (Object o) {
        // ignore o, and just use our URL
        if (!(url instanceof URL))
            System.err.println("Attempt to invoke Hotspot with bad URL " + url);
        else if (callback != null)
            callback.call(url);
    }

    static public UpLibHotSpot[] decode_string (URL base_url, DocViewerCallback ctxt, String hotspot_data) throws IOException {

        if (hotspot_data.startsWith("1\n")) {
            String[] lines = null;
            Vector retval = null;
            String doc_id = null;
            int pagex = -1;
            int left_x = -1;
            int left_y = -1;
            int width = -1;
            int height = -1;
            URL urlx = null;
            UpLibHotSpot newh = null;

            try {
                lines = hotspot_data.split("\n");
            } catch (Exception e) {
                throw new IOException("Inexplicable exception " + e + " raised while trying to split data into lines.");
            }
            if (lines != null && lines.length < 2)
                throw new IOException("Invalid externalized hotspot data.");
            int count = Integer.parseInt(lines[1]);
            if (count < 1)
                return null;
            retval = new Vector(count);
            int line_index = 2;
            while (line_index < lines.length) {
                if (line_index >= lines.length)
                    throw new IOException("Invalid externalized hotspot data:  lines.length is " + lines.length + ", but line_index is " + line_index + ", and count is " + count);
                // System.err.println("line[line_index=" + line_index + "] is '" + lines[line_index] + "'.");
                String[] header = null;
                try {
                    header = lines[line_index].split(" ");
                } catch (Exception e) {
                    throw new IOException("Inexplicable exception " + e + " raised while trying to split data into lines.");
                }
                if (header == null)
                    throw new IOException("Invalid externalized hotspot data:  Couldn't parse first line of hotspot data:  " + lines[line_index]);
                else if (header.length != 7)
                    throw new IOException("Invalid externalized hotspot data:  " + header.length + " fields in first line of hotspot data, should be 7:  " + lines[line_index]);
                line_index++;
                if (line_index >= lines.length)
                    throw new IOException("Invalid externalized hotspot data.");
                String description = lines[line_index];
                line_index++;
                try {
                    doc_id = header[0];
                    pagex = Integer.parseInt(header[1]);
                    left_x = Integer.parseInt(header[2]);
                    left_y = Integer.parseInt(header[3]);
                    width = Integer.parseInt(header[4]);
                    height = Integer.parseInt(header[5]);
                    urlx = new URL(base_url, header[6]);
                    newh = new UpLibHotSpot(ctxt, doc_id, true, pagex, left_x, left_y, width, height, urlx, lines[line_index]);
                    retval.add(newh);
                } catch (java.net.MalformedURLException x) {
                    System.err.println("Bad URL " + header[6] + " in hotspot at page " + pagex + ", " + width + "x" + height + "@" + left_x + "," + left_y);
                } catch (NumberFormatException x) {
                    System.err.println("Bad integer in hotspot " + lines[line_index]);
                }
            }
            return (UpLibHotSpot[]) retval.toArray(new UpLibHotSpot[retval.size()]);

        } else if (hotspot_data.startsWith("2\n")) {

            String[] lines = null;
            ArrayList retval = new ArrayList();
            String link_id = null;
            String doc_id = null;
            BufferedImage icon_image = null;
            Point icon_loc = null;
            int pagex = -1;
            int left_x = -1;
            int left_y = -1;
            int width = -1;
            int height = -1;
            String intrinsic_marker = null;
            String color_descriptor = null;
            URL urlx = null;
            String descr = null;

            try {
                lines = hotspot_data.split("\n");
            } catch (Exception e) {
                throw new IOException("Inexplicable exception " + e + " raised while trying to split data into lines.");
            }
            if (lines != null && lines.length < 2)
                throw new IOException("Invalid externalized hotspot data.");
            int count = Integer.parseInt(lines[1]);
            if (count < 0)
                return null;
            for (int line_index = 2;  (line_index + 2) < lines.length;  line_index += 3) {

                String[] header = null;

                try {
                    header = lines[line_index].split(" ");
                } catch (Exception e) {
                    throw new IOException("Inexplicable exception " + e + " raised while trying to split header line into tokens.");
                }

                if (header == null)
                    throw new IOException("Invalid externalized hotspot data:  Couldn't parse first line of hotspot data:  " + lines[line_index]);
                else if (header.length != 10)
                    throw new IOException("Invalid externalized hotspot data:  " + header.length + " fields in first line of hotspot data, should be 10:  " + lines[line_index]);

                link_id = header[0];
                doc_id = header[1];
                intrinsic_marker = header[7];
                color_descriptor = header[8];
                try {
                    pagex = Integer.parseInt(header[2]);
                    left_x = Integer.parseInt(header[3]);
                    left_y = Integer.parseInt(header[4]);
                    width = Integer.parseInt(header[5]);
                    height = Integer.parseInt(header[6]);
                } catch (NumberFormatException x) {
                    System.err.println("Bad integer in hotspot " + lines[line_index]);
                    continue;
                }
                try {
                    urlx = new URL(base_url, header[9]);
                } catch (java.net.MalformedURLException x) {
                    System.err.println("Bad URL " + header[9] + " in hotspot at page " + pagex + ", " + width + "x" + height + "@" + left_x + "," + left_y);
                    continue;
                }
                try {
                    descr = new String(Base64.decode(lines[line_index+1].getBytes()), "UTF-8");
                } catch (Exception x) {
                    System.err.println("Bad base64 description " + lines[line_index+1] + " in hotspot at page " + pagex + ", " + width + "x" + height + "@" + left_x + "," + left_y);
                    continue;
                }

                if (!lines[line_index+2].startsWith("noicon")) {
                    String[] parts;
                    try {
                        parts = lines[line_index+2].split(" ");
                        icon_loc = new Point(Integer.parseInt(parts[0]), Integer.parseInt(parts[1]));
                        icon_image = DataURL.decode(parts[2]);
                    } catch (Exception x) {
                        System.err.println("Bad icon line " + lines[line_index+2] + " in in hotspot at page " + pagex + ", " + width + "x" + height + "@" + left_x + "," + left_y);
                        continue;
                    }
                }

                Color color = null;
                if (!color_descriptor.equals("nocolor")) {
                    String[] parts = color_descriptor.split(":");
                    if (parts.length == 3) {
                        float red = Float.parseFloat(parts[0]);
                        float green = Float.parseFloat(parts[1]);
                        float blue = Float.parseFloat(parts[2]);
                        color = new Color(red, green, blue, 0.25f);
                    }
                }

                retval.add(new UpLibHotSpot(ctxt, link_id, doc_id, intrinsic_marker.equals("true"),
                                            pagex, left_x, left_y, width, height,
                                            urlx, descr, icon_image, icon_loc, color));
            }
            UpLibHotSpot[] values = new UpLibHotSpot[retval.size()];
            return (UpLibHotSpot[]) (retval.toArray(values));
        } else {
            throw new IOException("UpLibHotSpot externalized format " +
                                  hotspot_data.substring(0,1) +
                                  " not supported.");
        }
    }

    static public UpLibHotSpot[] decode (URL base_url, DocViewerCallback ctxt, byte[] hotspot_data) throws IOException {
        return decode_string(base_url, ctxt, new String(hotspot_data, "UTF-8"));
    }

    static public UpLibHotSpot[] decode_stream (URL base_url, DocViewerCallback ctxt, InputStream data) throws IOException {
        byte[] buffer = new byte[1<<16];
        int count;
        ByteArrayOutputStream sbuf = new ByteArrayOutputStream();
        while((count = data.read(buffer)) > 0) {
            sbuf.write(buffer, 0, count);
        }
        return UpLibHotSpot.decode_string(base_url, ctxt, sbuf.toString());
    }

    static public HotSpot[] readHotspots (URL uplib_url, String password, String cookie, DocViewerCallback callback) {

        HotSpot[] hotspots = null;

        if (uplib_url != null) {
            System.err.println("Reading hotspots from " + uplib_url);
            try {
                URLConnection c = uplib_url.openConnection();
                c.setUseCaches(false);
                if (password != null)
                    c.setRequestProperty("Password", password);
                if (cookie != null)
                    c.setRequestProperty("Cookie", cookie);
                InputStream s = c.getInputStream();
                System.err.println("Reading hotspots from " + c + ", " + s);
                hotspots = decode_stream(uplib_url, callback, s);
                if (hotspots != null)
                    System.err.println("" + hotspots.length + " hotspots read");
                else
                    System.err.println("no hotspots read");
            } catch (Exception e) {
                System.err.println("Exception reading hotspots:  " + e);
                e.printStackTrace(System.err);
                hotspots = null;
            }
        }
        return hotspots;
    }

    // HotSpot.Factory methods

    static public class Factory implements HotSpot.Factory {
        
        public Factory () {
        }

        public HotSpot create(DocViewerCallback c,
                              String docid,
                              boolean intrinsic,
                              int pagep,
                              int xp, int yp,
                              int widthp, int heightp,
                              URL u,
                              String descrp) {
            return new UpLibHotSpot (c, docid, intrinsic, pagep, xp, yp, widthp, heightp, u, descrp);
        }
        
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
                              Point icon_location) {
            return new UpLibHotSpot (c, linkid, docid, intrinsic, pagep, xp, yp, widthp, heightp, u, descrp, icon, icon_location, null);
        }
        
        public HotSpot create(DocViewerCallback c,
                              String linkid,
                              String docid,
                              boolean intrinsic,
                              int pagep,
                              int xp, int yp,
                              int widthp, int heightp,
                              HotSpot h) throws MalformedURLException {
            return new UpLibHotSpot (c, linkid, docid, intrinsic, pagep, xp, yp, widthp, heightp, h);
        }
    }
}
