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
import java.net.*;

import com.parc.uplib.readup.widget.*;

public class UpLibBufferEmptier extends SwingWorker {
        
    private byte[] buf;
    URL repo;
    String password;
    String cookie;
    String mime_type;

    public UpLibBufferEmptier (byte[] buf, URL repo, String mime_type, String password) {
        this.buf = buf;
        this.repo = repo;
        this.cookie = null;
        this.mime_type = mime_type;
        this.password = password;
    }

    public void setCookie (String cookie) {
        this.cookie = cookie;
    }

    public Object construct() {
        writeToServer(buf);
        return new Integer(1);
    }

    private void writeToServer (byte[] buf) {
        try {
            HttpURLConnection h = (HttpURLConnection) repo.openConnection();
            System.err.println("Got HttpURLConnection obj " + h);
            h.setUseCaches(false);
            h.setDoOutput(true);
            h.setRequestProperty("Content-Type", mime_type);
            h.setRequestProperty("Content-Length", Integer.toString(buf.length));
            if (password != null) {
                h.setRequestProperty("Password", password);
            }
            if (cookie != null) {
                h.setRequestProperty("Cookie", cookie);
            }
            h.setRequestMethod("POST");
            System.err.println("connecting...");
            h.connect();
            System.err.println("connected.");
            OutputStream s = h.getOutputStream();
            System.err.println("output stream is " + s);
            s.write(buf);
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
            System.err.println("Error posting buffer:  " + e);
            e.printStackTrace(System.err);
            System.err.println("Permission is " + e.getPermission());
        } catch (Exception e) {
            System.err.println("Error posting buffer:  " + e);
            e.printStackTrace(System.err);
        }
    }
}

