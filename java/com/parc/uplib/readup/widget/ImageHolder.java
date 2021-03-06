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

import java.io.*;
import java.awt.image.*;
import javax.imageio.ImageIO;

public class ImageHolder implements Serializable {

    private BufferedImage bi;

    public ImageHolder (BufferedImage b) {
        bi = b;
    }

    public BufferedImage image() {
        return bi;
    }

    static public ImageHolder read (InputStream s) throws IOException {
        BufferedImage b = ImageIO.read(s);
        return new ImageHolder(b);
    }

    private void writeObject (ObjectOutputStream o) throws IOException {
        ImageIO.write(bi, "PNG", o);
    }

    private void readObject (ObjectInputStream o) throws IOException {
        bi = ImageIO.read(o);
    }
}
