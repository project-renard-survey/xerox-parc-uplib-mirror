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

package com.parc.uplib.util;

import java.util.*;
import java.awt.image.*;
import java.io.*;
import javax.imageio.*;
import javax.imageio.stream.*;

import com.parc.uplib.util.Base64;

public class DataURL {

    public static boolean valid (String url) {
        return (url.startsWith("data:image/"));
    }

    public static BufferedImage decode (String url) throws java.io.IOException {
        if (valid(url)) {
            try {
                //  find the image type
                int p1 = url.indexOf(":");
                int p2 = url.indexOf(";");
                int p3 = url.indexOf(",");
                Iterator it = ImageIO.getImageReadersByMIMEType(url.substring(p1+1, p2));
                String imagestring = url.substring(p3+1);
                byte[] imagebytes = Base64.decode(imagestring);
                if (it.hasNext()) {
                    ImageReader ir = (ImageReader) it.next();
                    ir.setInput(new MemoryCacheImageInputStream(new ByteArrayInputStream(imagebytes)));
                    return ir.read(0);
                }
            } catch (UnsupportedEncodingException x) {
                // never happen -- US-ASCII is guaranteed to be there
                x.printStackTrace(System.err);
            }
        }
        return null;
    }

    private static ImageWriter getImageWriter(String format) {
        Iterator it = ImageIO.getImageWritersByFormatName(format);
        if (it.hasNext()) {
            return (ImageWriter) it.next();
        } else
            return null;        
    }

    public static String encode (BufferedImage im) throws java.io.IOException {
        ImageWriter iw = getImageWriter("png");
        if (iw != null) {
            try {
                ByteArrayOutputStream bs = new ByteArrayOutputStream();
                MemoryCacheImageOutputStream os = new MemoryCacheImageOutputStream(bs);
                iw.setOutput(os);
                iw.write(im);
                os.flush();
                return "data:image/png;base64," + Base64.encodeBytes(bs.toByteArray(), Base64.DONT_BREAK_LINES);
            } catch (UnsupportedEncodingException x) {
                // never happen -- US-ASCII is guaranteed to be there
                x.printStackTrace(System.err);
            }
        }
        return null;
    }

    public static void main (String[] argv) throws IOException {
        if ((argv.length == 1) && argv[0].equals("encode")) {
            BufferedImage im = ImageIO.read(System.in);
            String url = encode(im);
            System.out.println(url);
        } else {
            System.err.println("Usage:  encode < STDIN > STDOUT");
            System.exit(1);
        }            
    }
}


