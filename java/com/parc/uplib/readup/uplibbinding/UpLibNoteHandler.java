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

public class UpLibNoteHandler extends AnnotationStreamHandler implements ResourceLoader {

    final static private int IMAGE_CHUNK_SIZE = 32000;

    URL uplib_url;
    String uplib_password;
    String uplib_cookie;
    URL put_url;
    URL get_url;

    public UpLibNoteHandler (URL source, String password, int bufsize) {

        super(bufsize);

        uplib_password = password;
        uplib_url = source;
        uplib_cookie = null;
        put_url = null;
        get_url = null;
    }

    public void setCookie (String cookie) {
        uplib_cookie = cookie;
    }

    static private Object decode_note_stream (String document_id, int page_no, int selector, DataInputStream is)
        throws IOException {

        if (selector == 0) {
            // reading layout for all notes
            // discard 6-byte header
            is.skipBytes(6);
            // now read real data
            int format = is.readUnsignedByte();
            if (format != 0)
                throw new IOException("Can't understand format " + format);
            int typeCode = is.readUnsignedByte();
            if (typeCode != 4)
                throw new IOException("Bad type code " + typeCode);
            int noteCount = is.readUnsignedShort();
            NoteFrame[] frames = new NoteFrame[noteCount];
            for (int i = 0;  i < noteCount;  i++) {
                int format2 = is.readUnsignedByte();
                int version2 = is.readUnsignedByte();
                int length = is.readUnsignedShort();
                if ((format2 == 0) && (version2 == 0)) {
                    int note_number = is.readUnsignedShort();
                    int x = is.readUnsignedShort();
                    int y = is.readUnsignedShort();
                    int width = is.readUnsignedShort();
                    int height = is.readUnsignedShort();
                    int position = is.readUnsignedShort();
                    int red = is.readUnsignedByte();
                    int green = is.readUnsignedByte();
                    int blue = is.readUnsignedByte();
                    int alpha = is.readUnsignedByte();
                    frames[i] = new NoteFrame(page_no, note_number, x, y, width, height, position, new Color(red,green,blue,alpha));
                } else {
                    System.err.println("Unrecognized layout element, format " + format2 + ", version " + version2);
                    frames[i] = null;
                    is.skipBytes(length - 4);
                }
            }
            // read newline at the end of the data
            is.readUnsignedByte();
            return frames;
        } else {
            int version;
            int watype;
            int wpageno;
            int wnoteno;
            int walength;
            int count;

            version = is.readUnsignedByte();
            if ((version & 0xFF00) != 0xFF00) {
                // old style
                wpageno = (version << 8) + is.readUnsignedByte();
                if (wpageno != page_no)
                    throw new IOException("bad page number " + wpageno + " in packet; expected " + page_no);
                version = 0;
                wnoteno = is.readUnsignedShort();
                if (wnoteno != selector)
                    throw new IOException("bad note number " + wnoteno + " in packet; expected " + selector);
                count = is.readUnsignedShort();
                watype = 0;
                walength = 0;
            } else {
                watype = is.readUnsignedByte();
                wpageno = is.readUnsignedShort();
                if (wpageno != page_no)
                    throw new IOException("bad page number " + wpageno + " in packet; expected " + page_no);
                wnoteno = is.readUnsignedShort();
                if (wnoteno != selector)
                    throw new IOException("bad note number " + wnoteno + " in packet; expected " + selector);
                count = is.readUnsignedShort();
                walength = is.readUnsignedShort();
            }
            Vector result = new Vector();
            for (int i = 0;  i < count;  i++) {
                int rlength = is.readInt();
                int format = is.readUnsignedByte();
                if (format != 0)
                    throw new IOException("bad format version " + format + " in packet");
                int rtypecode = is.readUnsignedByte();
                Annotation.Type rtype = Annotation.Type.getTypeForCode(rtypecode);
                if ((rtype == Annotation.Type.SCRIBBLE) ||
                    (rtype == Annotation.Type.VSCRIBBLE) ||
                    (rtype == Annotation.Type.ERASURE)) {
                    // scribble
                    int scribble_length = is.readUnsignedShort();
                    int sformat = is.readUnsignedByte();
                    int stype = is.readUnsignedByte();
                    if (stype != rtypecode)
                        throw new IOException("bad scribble type value of " + stype + "; expected " + rtypecode);
                    if (sformat != 0)
                        throw new IOException("bad scribble format value of " + stype + "; expected 0");
                    byte[] t = new byte[rlength - 10];
                    is.readFully(t);
                    result.add(UpLibScribbleHandler.decodeScribble(document_id, t, sformat, rtype));
                } else if (rtype == Annotation.Type.NOTE) {
                    // text
                    byte[] t = new byte[rlength - 6];
                    is.readFully(t);
                    result.add(new String(t));
                } else if (rtype == Annotation.Type.LINK) {
                    // URL
                    byte[] t = new byte[rlength - 6];
                    is.readFully(t);
                    result.add(new URL(new String(t)));
                } else if (rtype == Annotation.Type.IMAGE) {
                    // image
                    byte[] t = new byte[rlength - 6];
                    is.readFully(t);
                    result.add(ImageHolder.read(new ByteArrayInputStream(t)));
                } else if (rtype == Annotation.Type.TIMESTAMP) {
                    // timestamp
                    int kind = is.read();
                    result.add(new Annotation.Timestamp(kind, is.readLong()));
                    if (rlength > 15) {
                        byte[] t = new byte[rlength - 15];
                        is.readFully(t);
                    }
                } else
                    throw new IOException("bad record type " + rtype + " in packet");
            }
            // read newline at end of content
            is.readUnsignedByte();
            return result;
        }
    }

    public Object getResource (String document_id, int page_no, int selector)
        throws IOException {

        Object note = null;
        URL the_url = null;

        try {
            the_url = new URL(uplib_url, "/action/basic/dv_fetch_note?doc_id=" + document_id + "&page=" + page_no + "&note=" + selector);
        } catch (MalformedURLException x) {
            x.printStackTrace(System.err);
            throw new ResourceLoader.CommunicationFailure(x.toString());
        }

        if (the_url != null) {
            try {
                HttpURLConnection c = (HttpURLConnection) the_url.openConnection();
                if (uplib_password != null)
                    c.setRequestProperty("Password", uplib_password);
                if (uplib_cookie != null)
                    c.setRequestProperty("Cookie", uplib_cookie);
                int rcode = c.getResponseCode();
                if (rcode == 200) {
                    byte[] header = new byte[20];
                    InputStream s = c.getInputStream();
                    try {
                        DataInputStream is = new DataInputStream(s);
                        // System.err.println("Reading note (" + document_id + ", " + page_no + ", " + selector + ") from " + c + ", " + s);
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
                        note = decode_note_stream(document_id, page_no, selector, is);
                    } finally {
                        s.close();
                    }
                } else if (rcode == 404) {
                    throw new ResourceLoader.ResourceNotFound("HTTP code 404 on " + the_url.toExternalForm());
                } else if (rcode == 401) {
                    throw new ResourceLoader.PrivilegeViolation("HTTP code 401 on " + the_url.toExternalForm());
                } else {
                    throw new ResourceLoader.CommunicationFailure("HTTP code " + rcode + " on " + the_url.toExternalForm());
                }
            } catch (IOException e) {
                // System.err.println("Exception reading Note(" + document_id + ", " + page_no + ", " + selector + "):");
                // e.printStackTrace(System.err);
                throw e;
            }
        }
        if (note != null)
            System.err.println("fetched note " + document_id + "/" + page_no + "/" + selector);
        return note;
    }

    public byte[] encode (String doc_id, int page_no, int selector, Annotation content, int format_version)
        throws IOException {

        ByteArrayOutputStream b = new ByteArrayOutputStream();
        DataOutputStream os = new DataOutputStream(b);
        int expected_length = 0;

        if (format_version != 0) {
            throw new IOException("Note externalized format " + format_version + " not supported.");
        }
        System.err.println("selector is " + selector + ", content is " + content + " (" + content.getClass().getName() + ")");
        if ((selector == 0) && (content instanceof DocViewer.Notesheets)) {

            // layout info
            Object[] notes = ((ArrayList)content).toArray();
            os.write((doc_id + "\n").getBytes());
            os.writeShort(page_no);
            os.writeShort(selector);
            os.writeShort(notes.length);
            os.writeByte(0);
            os.writeByte(4);
            os.writeShort(notes.length);
            for (int i = 0;  i < notes.length;  i++) {
                System.err.println("      notes[" + i + "] is " + notes[i]);
                NoteFrame f = (NoteFrame) (notes[i]);
                os.writeByte(0);
                os.writeByte(0);
                os.writeShort(20);
                os.writeShort(f.number);
                os.writeShort(f.x);
                os.writeShort(f.y);
                os.writeShort(f.width);
                os.writeShort(f.height);
                os.writeShort(f.stacking_order);
                os.writeByte(f.background.getRed());
                os.writeByte(f.background.getGreen());
                os.writeByte(f.background.getBlue());
                os.writeByte(f.background.getAlpha());
            }
            // add newline to end of packet
            os.writeByte(0x0a);

        } else if (content instanceof DocViewer.Pageview.Note) {
            // info for some specific note
            os.write((doc_id + "\n").getBytes());
            os.writeByte(0xFF);
            os.writeByte(0x00);
            os.writeShort(page_no);
            os.writeShort(selector);
            Vector ct = ((DocViewer.Pageview.Note)content).getContents();
            os.writeShort(ct.size());
            os.writeShort(0);
            Iterator it = ct.iterator();
            while (it.hasNext()) {
                Object o = it.next();
                if (o instanceof String) {  // text
                    byte[] string_bytes = ((String)o).getBytes();
                    os.writeInt(6 + string_bytes.length);
                    os.writeByte(0);
                    os.writeByte(1);
                    os.write(string_bytes);
                    System.err.println("String bytes of note are <" + ((String)o) + ">");
                } else if (o instanceof URL) {
                    byte[] t = ((URL)o).toExternalForm().getBytes();
                    os.writeInt(6 + t.length);
                    os.writeByte(0);
                    os.writeByte(2);
                    os.write(t);
                } else if (o instanceof ImageHolder) {
                    ByteArrayOutputStream bs = new ByteArrayOutputStream();
                    try {
                        ImageIO.write(((ImageHolder)o).image(), "PNG", bs);
                        bs.flush();
                    } catch (IOException exc) {
                        exc.printStackTrace(System.err);
                    }
                    byte[] image_bytes = bs.toByteArray();
                    os.writeInt(6 + image_bytes.length);
                    os.writeByte(0);
                    os.writeByte(3);
                    os.write(image_bytes);
                } else if (o instanceof Scribble) {
                    byte[] scribble_bytes = UpLibScribbleHandler.encodeScribble((Scribble) o, format_version);
                    os.writeInt(scribble_bytes.length + 6);
                    os.writeByte(0);
                    os.writeByte(0);
                    os.write(scribble_bytes, 0, scribble_bytes.length);
                } else if (o instanceof Annotation.Timestamp) {
                    os.writeInt(6 + 9);
                    os.writeByte(0);
                    os.writeByte(4);
                    os.writeByte((byte)(((Annotation.Timestamp)o).getKind()));
                    os.writeLong(((Annotation.Timestamp)o).getTime());
                } else {
                    System.err.println("Unknown note component " + o + " found!");
                    throw new IOException("Unknown note component " + o + " found!");
                }
            }
            // add newline to end of record
            os.writeByte(0x0a);
            os.flush();
        } else {
            throw new IOException("Not valid annotation:  " + content);
        }

        byte[] barray = b.toByteArray();
        String deb = "";
        int j;
        String c = "";
        for (int i = 0;  i < barray.length;  i++) {
            j = barray[i];
            if (j < 0)
                j += 256;
            if ((j > 31) && (j < 127))
                c = "(" + Character.toString((char) j) + ")";
            else
                c = "";
            deb += (Integer.toString(j, 16) + c + " ");
        }
        System.err.println("      encoded length " + barray.length + " bytes:  " + deb);
        return barray;
    }

    protected void initializeOutputStream (OutputStream os)
        throws IOException {
        os.write("1\n".getBytes());
    }

    protected void emptyBuffer (ByteArrayOutputStream b) {
        final byte[] buf = b.toByteArray();
        System.err.println("Emptying notes buffer (" + buf.length + " bytes) for " + uplib_url);

        if (put_url == null) {
            try {
                put_url = new URL(uplib_url, "/action/basic/dv_handle_notes");
            } catch (MalformedURLException x) {
                x.printStackTrace(System.err);
                return;
            }
        }

        /*
          // some debugging output
        try {
            OutputStream f = new FileOutputStream("/tmp/notedata");
            f.write(buf);
            f.close();
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        */

        UpLibBufferEmptier worker = new UpLibBufferEmptier(buf,
                                                           put_url,
                                                           "application/x-uplib-notes",
                                                           uplib_password);
        worker.setCookie(uplib_cookie);
        worker.start(-20);
        b.reset();
    }

    public void addAnnotation (Annotation note, String document_id, int page_no, int note_no) throws IOException {

        /*
        if (contents instanceof Vector) {
            Iterator i = ((Vector)contents).iterator();
            System.err.println("Contents of Note " + document_id + "/" + page_no + "/" + note_no + ":");
            while (i.hasNext()) {
                Object o = i.next();
                System.err.println(">>> (" + o.getClass().getName() + ") " + o.toString().trim());
            }
        }
        */

        super.addAnnotation(note, document_id, page_no, note_no);
    }
}
