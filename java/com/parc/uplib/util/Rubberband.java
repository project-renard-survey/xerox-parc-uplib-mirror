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

/*
 * This code is derived from the class com.barbre44.swing.Rubberband,
 * found at http://www.barbre44.com/ on 8 March 2006, with the following
 * copyright information:
 *
 * Rubberband.java
 * Copyright (c) 2003, J. Michael Barbre
 * All rights reserved.
 * 
 * www.barbre44.com
 * 
 * Permission to use, copy, modify, and distribute this software
 * and its documentation for NON-COMMERCIAL or COMMERCIAL purposes
 * and without fee is hereby granted provided that the copyright
 * and messages above appear in all copies. Copyright holder will 
 * not be held responsible for any unwanted effects due to the 
 * usage of this software or any derivative. No warrantees for 
 * usability for any specific application are given or implied.
 */

package com.parc.uplib.util;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Component;
import java.awt.Cursor;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Point;
import java.awt.Rectangle;
import java.awt.Stroke;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.event.MouseMotionAdapter;
import java.awt.event.ActionListener;
import java.awt.event.ActionEvent;
import java.util.ArrayList;
import java.util.List;

import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.event.MouseInputAdapter;

/**
 * Enables rubberbanding effect to select objects.
 *
 * <P><b><font size="-1">Release History</font></b>
 * <TABLE width="60%" border="1" cellspacing="0" cellpadding="1" bordercolor="Black" bgcolor="Aqua">
 * <TR>
 * <TD width="20%" ><b><font size="-1">Developer</font></b></TD>
 * <TD width="20%" ><b><font size="-1">Date</font></b></TD>
 * <TD width="20%" ><b><font size="-1">Notes</font></b></TD>
 * </TR>
 * 
 * <TR><TD>JMB<TD>Nov 8, 2003<TD>Updated javadocs.</TR>
 * 
 * </TABLE>
 * 
 */
public class Rubberband extends MouseInputAdapter {

    public static final String COMPLETED_ACTION_NAME = "rubberbanding-finished";

    private static final Cursor NW_RESIZE_CURSOR = Cursor.getPredefinedCursor(Cursor.NW_RESIZE_CURSOR);
    private static final Cursor NE_RESIZE_CURSOR = Cursor.getPredefinedCursor(Cursor.NE_RESIZE_CURSOR);
    private static final Cursor SW_RESIZE_CURSOR = Cursor.getPredefinedCursor(Cursor.SW_RESIZE_CURSOR);
    private static final Cursor SE_RESIZE_CURSOR = Cursor.getPredefinedCursor(Cursor.SE_RESIZE_CURSOR);

    private static final JPanel DEFAULT_PANE = new JPanel();
    private int x, y, width, height;
    private Rectangle bounds = new Rectangle();
    private Point startPoint = new Point();
    private Point currentPoint = new Point();
    private JComponent theComponent = null;
    private boolean hasBeenDrawn = false;
    private ActionListener toNotify = null;
    private Stroke dashedStroke = new BasicStroke(1.0f, BasicStroke.CAP_SQUARE, BasicStroke.JOIN_MITER, 10.0f, new float[] { 5f, 5f, 5f, 5f }, 5.0f);
    private Point offset = null;

    /**
     * Create a rubberband for the object specified
     * @param component
     */
    public Rubberband(JComponent component) {
        super();
        setComponent(component);
    }

    /**
     * Gets the theComponent.
     * @return Returns a JComponent
     */
    public JComponent getComponent() {
        return theComponent;
    }

    /**
     * Sets the theComponent.
     * @param theComponent The theComponent to set
     */
    public void setComponent(JComponent theComponent) {
        if (theComponent != null) {
            theComponent.removeMouseMotionListener(this);
            theComponent.removeMouseListener(this);
        }
        this.theComponent = theComponent;
    }

    /**
     * Get the components glasspane graphics context.
     * @return Graphics
     */
    private Graphics getGraphics() {
        Component p = DEFAULT_PANE;
        if (getComponent() != null) {
            p = getComponent().getRootPane().getGlassPane();
        }
        return p.getGraphics();
    }

    /**
     * Method draw.
     */
    private void draw() {
        // System.err.println("" + this + " drawing");

        x = Math.min(startPoint.x, currentPoint.x);
        y = Math.min(startPoint.y, currentPoint.y);
        width = Math.abs(startPoint.x - currentPoint.x);
        height = Math.abs(startPoint.y - currentPoint.y);
        Graphics g = getGraphics();
        if (g instanceof Graphics2D) {
            // Do dotted-line in Java2
            ((Graphics2D) g).setStroke(dashedStroke);
        }
        g.setXORMode(getComponent().getBackground());
        g.setColor(Color.red);
        g.drawRect(x, y, width, height);
        hasBeenDrawn = !hasBeenDrawn;
        g = null;
    }

    /**
     * Method erase.
     */
    private void erase() {
        if (hasBeenDrawn)
            draw();
    }

    private void adjustCursor() {
        if (getComponent() != null) {
            Component gp = getComponent().getRootPane().getGlassPane();
            if ((currentPoint.x < startPoint.x) && (currentPoint.y < startPoint.y))
                gp.setCursor(NW_RESIZE_CURSOR);
            else if ((currentPoint.x < startPoint.x) && (currentPoint.y >= startPoint.y))
                gp.setCursor(SW_RESIZE_CURSOR);
            else if ((currentPoint.x >= startPoint.x) && (currentPoint.y < startPoint.y))
                gp.setCursor(NE_RESIZE_CURSOR);
            else if ((currentPoint.x >= startPoint.x) && (currentPoint.y >= startPoint.y))
                gp.setCursor(SE_RESIZE_CURSOR);
        }
    }

    /**
     * @see MouseMotionListener#mouseDragged(MouseEvent)
     */
    public void mouseDragged(MouseEvent e) {
        // System.err.println("" + this + " dragging...");
        erase();
        currentPoint = e.getPoint();
        draw();
        e.consume();
        adjustCursor();
    }

    /**
     * @see MouseListener#mousePressed(MouseEvent)
     */
    public void mousePressed(MouseEvent e) {
        // System.err.println("" + this + " pressed...");
        startPoint = e.getPoint();
    }

    /**
     * @see MouseListener#mouseReleased(MouseEvent)
     */
    public void mouseReleased(MouseEvent e) {
        // System.err.println("" + this + " released...");
        if (startPoint != null) {
            e.consume();
            this.stop();
        }
    }

    /**
     * Method start.
     * @param p
     */
    public void start(Point p) {
        // System.err.println("" + this + " starting rubberband on " + getComponent());
        startPoint = p;
        if (getComponent() != null) {
            Component gp = getComponent().getRootPane().getGlassPane();
            gp.setCursor(NW_RESIZE_CURSOR);
            gp.setVisible(true);
            if (offset == null) {
                Point gp_loc = gp.getLocationOnScreen();
                Point comp_loc = getComponent().getLocationOnScreen();
                offset = new Point((comp_loc.x - gp_loc.x), (comp_loc.y - gp_loc.y));
            }
            gp.addMouseMotionListener(this);
            if (startPoint == null)
                gp.addMouseListener(this);
        }
    }

    /**
     * Method start.
     * @param toNotify
     */
    public void start(ActionListener toNotify) {
        this.start((Point) null);
        this.toNotify = toNotify;
    }

    /**
     * Stop the rubberband and remove it.
     */
    public void stop() {
        if (getComponent() != null) {
            erase();
            Component gp = getComponent().getRootPane().getGlassPane();
            gp.setVisible(false);
            gp.removeMouseListener(this);
            gp.removeMouseMotionListener(this);
        }
        bounds.x = Math.min(startPoint.x, currentPoint.x);
        bounds.y = Math.min(startPoint.y, currentPoint.y);
        bounds.width = Math.max(startPoint.x, currentPoint.x) - bounds.x;
        bounds.height = Math.max(startPoint.y, currentPoint.y) - bounds.y;
        if (offset != null) {
            bounds.x -= offset.x;
            bounds.y -= offset.y;
        }
        if (this.toNotify != null)
            this.toNotify.actionPerformed(new ActionEvent(this, ActionEvent.ACTION_PERFORMED, COMPLETED_ACTION_NAME));
    }

    /**
     * Get the rubberbands selection boundary
     * @return Returns a Rectangle
     */
    public Rectangle getBounds() {
        return bounds;
    }

    /**
     * Get all the components enclosed by the rubberband.
     * @return Component[] enclosed components
     */
    public Component[] getContainedComponents() {
        List list = new ArrayList();
        Component[] allChildren = getComponent().getComponents();
        for (int i = 0; i < allChildren.length; i++) {
            if (getBounds().intersects(allChildren[i].getBounds()))
                list.add(allChildren[i]);
        }
        return (Component[]) list.toArray(new Component[0]);
    }

    /**
     * Method main.
     * @param arguments
     */
    public static void main(String[] arguments) {
        JFrame f = new JFrame();
        f.getContentPane().add(new JButton("hello"));
        f.getContentPane().add(new JLabel("asl;dkfjas;dlfkjs"));
        f.setSize(400, 400);
        final Rubberband rb = new Rubberband((JComponent) f.getContentPane());
        System.out.println(rb.getBounds());
        f.getContentPane().addMouseListener(new MouseAdapter() {
                public void mouseReleased(MouseEvent e) {
                    rb.stop();
                    System.out.println(rb.getBounds());
                }

                public void mousePressed(MouseEvent e) {
                    rb.start(e.getPoint());
                }
            });
        f.setVisible(true);
    }
}
