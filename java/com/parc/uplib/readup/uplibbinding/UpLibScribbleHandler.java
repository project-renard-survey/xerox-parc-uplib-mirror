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

import com.parc.uplib.readup.widget.*;

public class UpLibScribbleHandler extends AnnotationStreamHandler {

    static final int BUFSIZE = 1 << 16;

    String uplib_password;
    String uplib_cookie;
    URL uplib_scribble_sink;
    URL uplib_scribble_source;
    String document_id;

    public UpLibScribbleHandler (String doc_id, String password, URL sink, URL source) {
        super(BUFSIZE);
        uplib_password = password;
        uplib_cookie = null;
        uplib_scribble_source = source;
        uplib_scribble_sink = sink;
        document_id = doc_id;
    }

    public void setCookie (String cookie) {
        uplib_cookie = cookie;
    }

    public byte[] encode (String doc_id, int page_no, int selector, Annotation o, int format_version)
        throws IOException {
        return encodeScribble(o, format_version);
    }

    public static byte[] encodeScribble (Annotation an, int format_version) throws IOException {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        DataOutputStream os = new DataOutputStream(b);
        int expected_length = 0;

        if (format_version != 0) {
            throw new IOException("Scribble externalized format " + format_version + " not supported.");
        } else if (! (an instanceof Scribble)) {
            throw new IOException("Not Scribble:  " + an);
        } else {
            Scribble scribble = (Scribble) an;
            Annotation.Type scribble_type = scribble.getType();
            int maxpoints = (scribble_type == Annotation.Type.VSCRIBBLE) ? 65535 : 255;
            if (scribble.points == null)
                scribble.finish();
            int nstrokes = (scribble.points.length / maxpoints) + 1;

            for (int count = 0;  count < nstrokes;  count++) {

                int npoints = (scribble.points.length - (count * maxpoints) < maxpoints) ? (scribble.points.length - (count * maxpoints)) : maxpoints;
                int len = 0;
                
                if ((scribble_type == Annotation.Type.SCRIBBLE) ||
                    (scribble_type == Annotation.Type.ERASURE))
                  len = 20 + (4 * npoints);
                else if (scribble_type == Annotation.Type.VSCRIBBLE)
                  len = 20 + (10 * npoints);

                os.writeShort(len);     /* record length */
                os.writeByte(0);        /* record format version 0 */
                os.writeByte(scribble.getType().getCode());
                os.writeShort(scribble.pageIndex());     /* page index */
                os.writeLong(scribble.timestamp().getTime());
                os.writeByte(scribble.color.getRed());
                os.writeByte(scribble.color.getGreen());
                os.writeByte(scribble.color.getBlue());
                os.writeByte(scribble.color.getAlpha());
                if (scribble_type == Annotation.Type.VSCRIBBLE) {
                    os.writeShort(npoints);
                } else {
                    // SCRIBBLE or ERASURE
                    os.writeByte((byte) Math.round(scribble.static_thickness * 8));
                    os.writeByte((byte) (npoints & 0xFF));
                }
                for (int j = (count * maxpoints);  j < (count + 1) * maxpoints && j < scribble.points.length;  j++) {
                    Scribble.ScribblePoint p = scribble.points[j + (count * maxpoints)];
                    if ((scribble_type == Annotation.Type.SCRIBBLE) ||
                        (scribble_type == Annotation.Type.ERASURE)) {
                        os.writeShort(Math.round(p.x));
                        os.writeShort(Math.round(p.y));
                    } else if (scribble_type == Annotation.Type.VSCRIBBLE) {
                        os.writeFloat(p.x);
                        os.writeFloat(p.y);
                        os.writeShort(Math.round(p.thickness * 256));
                    }
                }
                os.flush();

                expected_length += len;
            }
            byte[] barray = b.toByteArray();
            if (barray.length != expected_length) {
                System.err.println("Encoding scribble " + scribble + " resulted in " + barray.length + " bytes, instead of the expected " + expected_length + ".");
            }
            return barray;
        }
    }

    public static Scribble decodeScribble (String doc_id, byte[] record, int version, Annotation.Type type)
      throws IOException {
        if (version == 0) {
            DataInputStream is = new DataInputStream(new ByteArrayInputStream(record));
            int page = is.readUnsignedShort();
            long ts = is.readLong();
            Annotation.Timestamp timestamp = new Annotation.Timestamp(Annotation.Timestamp.CREATED, ts);
            int red = is.readUnsignedByte();
            int green = is.readUnsignedByte();
            int blue = is.readUnsignedByte();
            int alpha = is.readUnsignedByte();
            float pen_thickness = 0.0F;
            int npoints;
            if ((type == Annotation.Type.SCRIBBLE) || (type == Annotation.Type.ERASURE)) {
                pen_thickness = ((float)is.readUnsignedByte())/8.0F;
                npoints = is.readUnsignedByte();
            } else {
                npoints = is.readUnsignedShort();
            }

            // System.err.println("page " + page + ", timestamp " + timestamp + ", (" + red + "," + green + "," + blue + "," + alpha + ")  " + pen_thickness + "  (" + npoints + " points)");

            int properlen = (type == Annotation.Type.VSCRIBBLE) ? ((10 * npoints) + 16) : ((4 * npoints) + 16);
            if (record.length < properlen)
                throw new IOException("record_length only " + record.length + ", should be " + ((4 * npoints) + 16));
            if (record.length != properlen)
                System.err.println("record_length is " + record.length + ", but should be " + ((4 * npoints) + 16));

            Scribble.ScribblePoint[] points = new Scribble.ScribblePoint[npoints];
            for (int i = 0;  i < npoints;  i++) {
                if (type == Annotation.Type.VSCRIBBLE) {
                    float x = is.readFloat();
                    float y = is.readFloat();
                    pen_thickness = ((float) is.readUnsignedShort())/256.0F;
                    points[i] = new Scribble.ScribblePoint(x, y, pen_thickness);
                } else {
                    int x = is.readUnsignedShort();
                    int y = is.readUnsignedShort();
                    points[i] = new Scribble.ScribblePoint((float) x, (float) y, pen_thickness);
                }
            }
            return new Scribble(doc_id, page, new Color(red, green, blue, alpha), points, timestamp, type);
        } else
            throw new IOException("Only scribble format 0 is supported; can't decode format " + version);
    }

    private Scribble read_scribble (DataInputStream is) throws IOException {
        int record_length;
        try {
            record_length = is.readUnsignedShort();
            int format = is.readUnsignedByte();
            int acode = is.readUnsignedByte();
            // System.err.println("" + record_length + ", " + format + ", " + acode);
            byte[] record = new byte[record_length - 4];
            is.readFully(record);

            /*
            String os = "";
            for (int i = 0;  i < record.length;  i++)
              os = os + " " + Integer.toHexString((record[i] < 0) ? (record[i] + 256) : record[i]);
            System.err.println(os);
            */

            Annotation.Type atype = Annotation.Type.getTypeForCode(acode);
            if ((atype == Annotation.Type.SCRIBBLE) ||
                (atype == Annotation.Type.VSCRIBBLE) ||
                (atype == Annotation.Type.ERASURE)) {
                return decodeScribble (document_id, record, format, atype);
            } else {
                throw new IOException("Can't handle annotation records of type " + atype);
            }
        } catch (EOFException e) {
            // System.err.println("EOF exception decoding pickled scribble:  " + e);
            return null;
        }
    }

    public Scribble[] decode_stream (InputStream data) throws IOException {
        DataInputStream is = new DataInputStream(data);
        byte[] header = new byte[20];
        int count = is.read(header, 0, 20);
        if (count < 20) {
            throw new IOException("Badly formatted header on scribble stream -- not enough bytes");
        }
        if ((header[0] != 0x31) || (header[1] != 0x0a) || (header[19] != 0x0a)) {
            throw new IOException("Badly formatted header on scribble stream:  " + header);
        }
        String doc_id = new String(header, 2, 17);
        if (!doc_id.equals(document_id)) {
            throw new IOException("Annotation is for wrong document (our document " + document_id + ", annotation for " + doc_id + ")");
        }
        ArrayList al = new ArrayList();
        Scribble s;
        while ((s = read_scribble(is)) != null) {
            // System.err.println("Scribble is " + s);
            al.add(s);
        }
        Scribble[] scribbles = new Scribble[al.size()];
        al.toArray(scribbles);
        System.err.println("" + scribbles.length + " scribbles read");
        return scribbles;
    }

    public Scribble[] readScribbles () {
        Scribble[] scribbles = null;
        if (uplib_scribble_source != null) {
            try {
                URLConnection c = uplib_scribble_source.openConnection();
                if (uplib_password != null)
                    c.setRequestProperty("Password", uplib_password);
                if (uplib_cookie != null)
                    c.setRequestProperty("Cookie", uplib_cookie);
                InputStream s = c.getInputStream();
                System.err.println("Reading scribbles from " + c + ", " + s);
                scribbles = decode_stream(s);
                System.err.println("Scribbles successfully read");
            } catch (Exception e) {
                System.err.println("Exception reading scribbles:  " + e);
                e.printStackTrace(System.err);
                scribbles = null;
            }
        }
        return scribbles;
    }

    protected void initializeOutputStream (OutputStream os)
        throws IOException {
        os.write(("1\n" + document_id + "\n").getBytes());
    }

    protected void emptyBuffer (ByteArrayOutputStream b) {
        final byte[] buf = b.toByteArray();
        System.err.println("Emptying scribble buffer (" + buf.length + " bytes) for " + uplib_scribble_sink);

        /*
        try {
            OutputStream f = new FileOutputStream("/tmp/scribbles");
            f.write(buf);
            f.close();
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        */

        UpLibBufferEmptier worker = new UpLibBufferEmptier(buf,
                                                           uplib_scribble_sink,
                                                           "application/x-uplib-annotations",
                                                           uplib_password);
        worker.setCookie(uplib_cookie);
        worker.start(-20);
        b.reset();
    }
}

