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

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

import com.parc.uplib.readup.widget.Activity;
import com.parc.uplib.readup.widget.DocViewerCallback;
import com.parc.uplib.readup.widget.SwingWorker;

public class UpLibActivityLogger
    implements DocViewerCallback {

    static final int BUFSIZE = 1 << 16;

    protected URL uplib_url;
    protected String password;
    private String doc_id;
    private String cookie;

    private DataOutputStream ostream;
    private ByteArrayOutputStream bstream;

    public UpLibActivityLogger (String did, URL sink, String pword) {
        uplib_url = sink;
        password = pword;
        cookie = null;
        bstream = new ByteArrayOutputStream(BUFSIZE);
        ostream = new DataOutputStream(bstream);
        doc_id = did;
    }

    public void setCookie(String cookie) {
        this.cookie = cookie;
    }

    private int figureNeededSize(Activity a) {
        return (14 + ((a.extension_bytes == null) ? 0 : a.extension_bytes.length));
    }

    private void writeToServer (byte[] buf) {
        System.err.println("Writing activity buffer to server " + uplib_url);
        try {
            HttpURLConnection h = (HttpURLConnection) uplib_url.openConnection();
            byte[] header = ("1\n" + doc_id + "\n").getBytes();
            // System.out.println("Got HttpURLConnection obj " + h);
            h.setUseCaches(false);
            h.setDoOutput(true);
            if (password != null)
                h.setRequestProperty("Password", password);
            if (cookie != null)
                h.setRequestProperty("Cookie", cookie);
            h.setRequestProperty("Content-Type", "application/x-uplib-activities");
            h.setRequestProperty("Content-Length", Integer.toString(header.length + buf.length));
            h.setRequestMethod("POST");
            h.connect();
            OutputStream os = h.getOutputStream();
            os.write(header);
            os.write(buf);
            int rcode = h.getResponseCode();
            if (rcode != 200) {
                System.err.println("Response code is " + rcode);
                System.err.println("Content is:");
                InputStream input = (java.io.InputStream) h.getContent();
                while (true) {
                    int c = input.read();
                    if (c < 0)
                        break;
                    System.err.write(c);
                }
                input.close();
            }
        } catch (java.security.AccessControlException e) {
            System.err.println("Error posting activity:  " + e);
            e.printStackTrace(System.err);
            System.err.println("Permission is " + e.getPermission());
        } catch (Exception e) {
            System.err.println("Error posting activity:  " + e);
            e.printStackTrace(System.err);
        }

    }

    private void emptyBuffer (ByteArrayOutputStream b) {
        System.err.println("Emptying Activity buffer for " + doc_id + "; " + b.size() + " bytes");
        final byte[] buf = b.toByteArray();
        b.reset();
        final com.parc.uplib.readup.widget.SwingWorker worker = new com.parc.uplib.readup.widget.SwingWorker() {
                public Object construct() {
                    writeToServer(buf);
                    return new Integer(1);
                }
            };
        worker.start(-20);
    }

    private void encodeActivity (Activity a) {
        try {
            if (a.doc_id != doc_id)
                throw new IOException("Invalid document ID " + a.doc_id + " for this document!");
            int size_needed = figureNeededSize(a);
            synchronized (bstream) {
                if ((bstream.size() + size_needed) >= BUFSIZE)
                    emptyBuffer(bstream);
            }
            ostream.writeByte(0);
            ostream.writeByte((a.extension_bytes == null) ? 0 : a.extension_bytes.length);
            ostream.writeShort(a.page_index);
            ostream.writeLong(a.timestamp.getTime());
            ostream.writeShort(a.activity_code);
            if (a.extension_bytes != null)
                ostream.write(a.extension_bytes, 0, a.extension_bytes.length);
        } catch (IOException e) {
            System.err.println("Error writing activity to output stream:  " + e);
            e.printStackTrace(System.err);
        }
    }

    public void call (Object o) {
        encodeActivity((Activity) o);
    }

    public void flush() {
        synchronized(bstream) {
            if (bstream.size() > 0)
                emptyBuffer(bstream);
        }
    }
}
