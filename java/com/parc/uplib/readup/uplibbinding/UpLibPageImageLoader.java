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

import javax.swing.JApplet;
import java.applet.*;
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
import java.nio.ByteBuffer;
import java.text.DecimalFormat;

import com.parc.uplib.util.Configurator;
import com.parc.uplib.readup.widget.CachingLoader;
import com.parc.uplib.readup.widget.ResourceLoader;
import com.parc.uplib.readup.widget.ImageHolder;

public class UpLibPageImageLoader extends CachingLoader {

    private final static DecimalFormat page_image_filename_format = new DecimalFormat("page00000.png");
    private static int maxImageSize = 30000000;

    static protected boolean    imageio_fixed = false;
    static {
        try {
            String tmp;
            tmp = System.getProperty("com.parc.uplib.imageIO-fixed");
            if (tmp != null)
                imageio_fixed = Boolean.valueOf(tmp).booleanValue();
            tmp = System.getProperty("com.parc.uplib.readup.maxImageSize");
            if (tmp != null)
                maxImageSize = Integer.parseInt(tmp);
            try {
                Configurator c = new Configurator();
                String s = c.get("client-side-cache-location");
                if (s != null) {
                    CachingLoader.setCacheDirectory(new File(s));
                }
            } catch (java.security.AccessControlException x) {
                // can't read machine.config, because in an applet
            } catch (Exception x) {
                System.err.println("Exception while initializing CachingLoader static section");
                x.printStackTrace(System.err);
            }
        } catch (java.lang.SecurityException x) {
            // don't have privilege to read property
        }
    }

    private URL repo_url;
    private String repo_password;
    private String repo_cookie = null;
    private int rmargin;

    public UpLibPageImageLoader (String resource_type, URL repo, String pword, int right_margin) {
        super(repo, resource_type);
        repo_url = repo;
        repo_password = pword;
        rmargin = right_margin;
    }

    public UpLibPageImageLoader (URL repo, String pword, int right_margin) {
        super(null, "page image");
        repo_url = repo;
        repo_password = pword;
        rmargin = right_margin;
    }

    public void setCookie (String cookie) {
        repo_cookie = cookie;
    }

    public void setPageImageType(String typename) {
        this.cache_type = typename;
    }

    static int max(int v1, int v2) {
        return ((v1 > v2) ? v1 : v2);
    }

    static int min(int v1, int v2) {
        return ((v1 < v2) ? v1 : v2);
    }

    private BufferedImage readImage (InputStream instr)
        throws IOException {
        
        BufferedImage i;
        if (imageio_fixed) {
            BufferedInputStream b = new BufferedInputStream(instr);
            i = (BufferedImage) ImageIO.read(b);
            b.close();
        } else {
                    
            // The code is almost unbearably clunky, but it had to be
            // written in this spread-out way because just doing a
            // straight ImageIO.read(image_url) caused a variety of Zip
            // decoding errors to be signalled by the JRE.
            
            final int READ_CHUNK_SIZE = 20000;
            byte[] buf = new byte[maxImageSize];
            int offset = 0;
            int count = 0;

            while (offset < maxImageSize) {
                count = instr.read(buf, offset, min((maxImageSize - offset), READ_CHUNK_SIZE));
                if (count < 0)
                    break;
                offset = offset + count;
            }
            instr.close();
            //System.err.println("read " + offset + " bytes of image");
            if (offset >= maxImageSize) {
                System.err.println("ResourceTooLarge:  offset is " + offset + ", limit is " + maxImageSize);
                throw new ResourceTooLarge("too many bytes in image; limit is " + maxImageSize, maxImageSize);
            }
            ByteArrayInputStream b = new ByteArrayInputStream(buf, 0, offset);
            i = (BufferedImage) ImageIO.read(b);
            b.close();
        }
        if (rmargin > 0)
            return i.getSubimage(0, 0, i.getWidth(null) - rmargin, i.getHeight(null));
        else
            return i;
    }

    public Object getResource (String document_id, int page_index, int selector)
        throws IOException {
        URL the_url = null;

        ImageHolder b = (ImageHolder) super.getResource(document_id, page_index, selector);
        if (b != null) {
            // System.err.println("loaded page image " + document_id + "/" + page_index + "/" + selector + " from cache");
            return b.image();
        }

        try {
            if (page_index == -1)
                the_url = new URL(repo_url, "/docs/" + document_id + "/thumbnails/first.png");
            else if (selector == 0)
                the_url = new URL(repo_url, "/docs/" + document_id + "/thumbnails/big" + Integer.toString(page_index+1) + ".png");
            else if (selector == 1)
                the_url = new URL(repo_url, "/docs/" + document_id + "/thumbnails/" + Integer.toString(page_index+1) + ".png");
            else if (selector == 2) {
                String filename = page_image_filename_format.format(page_index+1);
                System.err.println("filename is " + filename);
                the_url = new URL(repo_url, "/docs/" + document_id + "/page-images/" + filename);
            }else
                throw new ResourceNotFound("No page with index " + page_index + " and selector " + selector);
        } catch (MalformedURLException x) {
            x.printStackTrace(System.err);
            throw new ResourceLoader.CommunicationFailure(x.toString());
        }

        // System.err.println("page URL is " + the_url);
        try {
            HttpURLConnection c = (HttpURLConnection) the_url.openConnection();
            if ((repo_password != null) && (repo_password.length() > 0))
                c.setRequestProperty("Password", repo_password);
            if (repo_cookie != null)
                c.setRequestProperty("Cookie", repo_cookie);
            int rcode = c.getResponseCode();
            // String msg = "UpLibPageImageLoader.getResource gets return code "+rcode+" for url "+the_url.toString()+".";
            // System.out.println(msg);
            if (rcode == 200) {
                InputStream s = c.getInputStream();
                try {
                    BufferedImage i = readImage(s);
                    if (i != null) {
                        super.cacheResource(document_id, page_index, selector, new ImageHolder(i));
                        System.err.println("fetched " + this.cache_type + " " + document_id + "/" + page_index);
                        return i;
                    }
                    else
                        return null;
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
        } catch (java.io.IOException ioe) {
            System.err.println("Couldn't read " + this.cache_type + " for " + document_id + "/" + page_index + " from buffered bytes " + the_url + ": " + ioe);
            throw ioe;
        }
    }
}
