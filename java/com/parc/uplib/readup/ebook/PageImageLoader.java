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

package com.parc.uplib.readup.ebook;

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
import java.text.*;
import java.net.*;
import java.util.zip.*;

import com.parc.uplib.readup.widget.CachingLoader;
import com.parc.uplib.readup.widget.ImageHolder;

class PageImageLoader extends CachingLoader {

    private final static DecimalFormat page_image_filename_format = new DecimalFormat("page00000.png");

    int rmargin;
    String resource_type;

    public PageImageLoader (String id_string, int rm) {
        super(null, id_string);
        rmargin = rm;
        resource_type = id_string;
    }
        
    public void setCookie (String cookie) {
    }

    private BufferedImage readImage (InputStream instr)
        throws IOException {
        
        BufferedImage i;
        BufferedInputStream b = new BufferedInputStream(instr);
        i = (BufferedImage) ImageIO.read(b);
        b.close();
        if (rmargin > 0)
            return i.getSubimage(0, 0, i.getWidth(null) - rmargin, i.getHeight(null));
        else
            return i;
    }

    public Object getResource (String document_id, int page_index, int selector)
        throws IOException {
        String the_url = null;

        ImageHolder b = (ImageHolder) super.getResource(document_id, page_index, selector);
        if (b != null) {
            // System.err.println("loaded page image " + document_id + "/" + page_index + "/" + selector + " from cache");
            return b.image();
        }

        if (page_index == -1)
            the_url = "/thumbnails/first.png";
        else if (selector == 0)
            the_url = "/thumbnails/big" + Integer.toString(page_index+1) + ".png";
        else if (selector == 1)
            the_url = "/thumbnails/" + Integer.toString(page_index+1) + ".png";
        else if (selector == 2) {
            String filename = page_image_filename_format.format(page_index+1);
            the_url = "/page-images/" + filename;
        } else
            throw new ResourceNotFound("No page with index " + page_index + " and selector " + selector);

        // System.err.println("page URL is " + the_url);
        try {
            InputStream inps = PageImageLoader.class.getResourceAsStream(the_url);
            try {
                BufferedImage i = readImage(inps);
                if (i != null) {
                    super.cacheResource(document_id, page_index, selector, new ImageHolder(i));
                    System.err.println("fetched " + this.cache_type + " " + document_id + "/" + page_index);
                    return i;
                }
                else
                    return null;
            } finally {
                inps.close();
            }
        } catch (java.io.IOException ioe) {
            System.err.println("Couldn't read " + this.cache_type + " for " + document_id + "/" + page_index + " from buffered bytes " + the_url + ": " + ioe);
            throw ioe;
        }
    }
}

