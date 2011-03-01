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

import java.lang.ref.SoftReference;
import java.awt.Color;

public class NoteFrame implements java.io.Serializable {

    public int page;
    public int number;
    public int x, y, width, height;
    public int stacking_order;
    public Color background;
    transient public SoftReference note_pane;

    public NoteFrame (int page, int note_no, int x, int y, int width, int height, int order, Color background) {
        this.page = page;
        this.number = note_no;
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.stacking_order = order;
        this.background = background;
        this.note_pane = null;
    }

    public String toString () {
        return "<NoteFrame " + page + "/" + number + ": " + width + "x" + height + "+" + x + "+" + y + " (" + stacking_order + ")>";
    }
}
