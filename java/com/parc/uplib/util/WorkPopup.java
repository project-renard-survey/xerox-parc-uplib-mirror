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

import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.dnd.*;
import java.awt.*;
import java.awt.datatransfer.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.border.*;
import javax.imageio.*;
import java.net.URL;
import java.util.logging.*;

public abstract class WorkPopup extends JDialog {

    protected boolean submitted = false;
    protected boolean cancelled = false;
    protected Component initialfocus;

    // just make this local for convenience
    private final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);

    private class CloseHandler extends WindowAdapter {
        private WorkPopup p;
        CloseHandler(WorkPopup popup) {
            super();
            p = popup;
        }
        public void windowClosing (WindowEvent e) {
            p.cancelled = true;
        }
        public void windowClosed (WindowEvent e) {
            p.cancelled = true;
        }
    }

    public WorkPopup (Frame frame, boolean modal) {
        super (frame, modal);
        setBackground(TOOLS_COLOR);
	getContentPane().setBackground(TOOLS_COLOR);
        addWindowListener(new CloseHandler(this));
        setDefaultCloseOperation(JDialog.HIDE_ON_CLOSE);
        initialfocus = null;
    }

    protected void finish() {
        initValues();
        initComponents();
        pack();
    }

    protected abstract void initValues();

    protected abstract void initComponents();

    public void update (Graphics g) {
        if (initialfocus != null)
            initialfocus.requestFocusInWindow();
        super.update(g);                
    }

    public static Point bestLocation(java.awt.Container c, Rectangle within, Rectangle near) {
        Point retval = null;
        Dimension size = c.getSize();
        Rectangle junction = near.intersection(within);
        if (!junction.isEmpty()) {
            // try right side first
            if ((junction.x + junction.width + size.width + 2) < (within.width + within.x)) {
                // room on right -- try to position top level with top of junction rect
                retval = new Point(junction.x + junction.width + 2,
                                   Math.max(within.y,
                                            Math.min((within.y + within.height) - size.height,
                                                     junction.y + junction.height/2 - size.height/2)));
            } else if ((junction.x - within.x - 2) > size.width) {
                // room on left -- try to position top level with top of junction rect
                retval = new Point(junction.x - size.width - 2,
                                   Math.max(within.y,
                                            Math.min((within.y + within.height) - size.height,
                                                     junction.y + junction.height/2 - size.height/2)));
            } else if ((junction.y - within.y - 2) > size.height) {
                // room on top -- try to center on junction rect
                retval = new Point(Math.max(within.x,
                                            Math.min((within.x + within.width) - size.width,
                                                     junction.x + junction.width/2 + size.width/2)),
                                   junction.y - size.height - 2);
            } else if ((within.y - (junction.y + junction.height + 2)) > size.height) {
                // room below -- try to center on junction rect
                retval = new Point(Math.max(within.x,
                                            Math.min((within.x + within.width) - size.width,
                                                     junction.x + junction.width/2 + size.width/2)),
                                   junction.y + junction.height + 2);
            }
        }
        return retval;
    }
}

