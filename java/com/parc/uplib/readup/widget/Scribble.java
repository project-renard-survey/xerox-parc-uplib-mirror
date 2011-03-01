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

public class Scribble implements Serializable, Annotation {

    final static BasicStroke ZERO_STROKE = new BasicStroke(0.0f, BasicStroke.CAP_BUTT, BasicStroke.JOIN_ROUND);

    public static class ScribblePoint {
        public float   x;
        public float   y;
        public float   thickness;

        public ScribblePoint (Point end_location, float thickness) {
            this.x = (float) end_location.getX();
            this.y = (float) end_location.getY();
            this.thickness = thickness;
        }

        public ScribblePoint (float x, float y, float thickness) {
            this.x = x;
            this.y = y;
            this.thickness = thickness;
        }
    }

    public Rectangle bbox;
    private String doc_id;
    private int page_index;
    private Annotation.Timestamp time;
    private Annotation.Type typecode;
    public Color color;

    public int npoints;
    public ScribblePoint[] points;

    public ArrayList strokes;
    public float static_thickness;
    private Area drawing_shape;
    protected Point offset;           // offset to the real image page coords

    public Scribble(String doc, int page, Color c, float thickness, Point o) {
        strokes = new ArrayList();
        bbox = null;
        time = new Annotation.Timestamp(Annotation.Timestamp.CREATED);
        doc_id = doc;
        page_index = page;
        color = c;
        npoints = 0;
        points = null;

        offset = o;
        static_thickness = thickness;
        drawing_shape = null;
        typecode = Annotation.Type.SCRIBBLE;
    }

    public Scribble(String doc, int page, Color c, float thickness, Point o, Annotation.Type tc) {
        strokes = new ArrayList();
        bbox = null;
        time = new Annotation.Timestamp(Annotation.Timestamp.CREATED);
        doc_id = doc;
        page_index = page;
        color = c;
        npoints = 0;
        points = null;

        offset = o;
        static_thickness = thickness;
        drawing_shape = null;
        typecode = tc;
    }

    public Scribble(String doc, int page, Color c, float thickness, Point[] points, Annotation.Timestamp timestamp) {
        Point p;
        bbox = null;
        time = timestamp;
        doc_id = doc;
        page_index = page;
        color = c;
        offset = new Point(0, 0);
        npoints = points.length;
        this.points = new ScribblePoint[npoints];
        static_thickness = thickness;
        for (int i = 0;  i < npoints;  i++) {
            p = points[i];
            this.points[i] = new ScribblePoint(points[i], thickness);
            Rectangle addr = new Rectangle((int)(p.x - thickness/2) - 1,
                                           (int)(p.y - thickness/2) - 1,
                                           (int)thickness + 2, (int)thickness + 2);
            if (bbox == null)
                bbox = addr;
            else
                bbox.add(addr);
        }
        drawing_shape = null;
        strokes = null;
        typecode = Annotation.Type.SCRIBBLE;
    }

    public Scribble(String doc, int page, Color c, ScribblePoint[] points, Annotation.Timestamp timestamp,
                    Annotation.Type type) {
        bbox = null;
        time = timestamp;
        doc_id = doc;
        page_index = page;
        color = c;
        offset = new Point(0, 0);
        npoints = points.length;
        this.points = points;
        static_thickness = 0;

        ScribblePoint p;
        for (int i = 0;  i < npoints;  i++) {
            p = points[i];
            Rectangle addr = new Rectangle((int)(p.x - p.thickness/2) - 1,
                                           (int)(p.y - p.thickness/2) - 1,
                                           (int)p.thickness + 2, (int)p.thickness + 2);
            if (bbox == null)
                bbox = addr;
            else
                bbox.add(addr);
        }
        drawing_shape = null;
        strokes = null;
        typecode = type;
    }

    public Annotation.Type getType () {
        return typecode;
    }

    public int pageIndex () {
        return page_index;
    }

    public String docId () {
        return doc_id;
    }

    public Annotation.Timestamp timestamp () {
        return time;
    }

    public boolean within (int kind, Date after, Date before) {

        if ((kind != Annotation.Timestamp.CREATED) &&
            (kind != Annotation.Timestamp.MODIFIED))
            return false;

        if (time == null)
            return (after == null);
        else if ((before != null) && (!time.before(before)))
            return false;
        else if ((after != null) && (!time.after(after)))
            return false;
        else
            return true;
    }

    public String toString () {
        return "<" + typecode.toString() + " color=" + color +
            ", npoints=" + npoints +
            ", bbox=" + bbox +
            ">";
    }

    public ScribblePoint addPoint (Point p, float thickness) {
        Rectangle addr = new Rectangle((int)(p.x - thickness/2) - 1,
                                       (int)(p.y - thickness/2) - 1,
                                       (int)thickness + 2, (int)thickness + 2);
        ScribblePoint sp = new ScribblePoint(p, thickness);
        strokes.add(sp);
        npoints++;
        if (bbox == null)
            bbox = addr;
        else
            bbox.add(addr);
        if (thickness != static_thickness)
          typecode = Annotation.Type.VSCRIBBLE;
        return sp;
    }

    public ScribblePoint addPoint (Point p) {
        return addPoint(p, static_thickness);
    }
    
    public void finish () {
        this.points = (ScribblePoint[]) strokes.toArray(new ScribblePoint[npoints]);
        this.strokes = null;
    }

    public void finish (Area drawingArea) {
        this.points = (ScribblePoint[]) strokes.toArray(new ScribblePoint[npoints]);
        this.strokes = null;
        this.drawing_shape = drawingArea;
    }

    static public boolean calculateStrokeArea (Area area_out, float p1x, float p1y, float p1w, float p2x, float p2y, float p2w) {

        area_out.reset();

        double distance = Math.sqrt((p2x - p1x) * (p2x - p1x) +
                                    (p2y - p1y) * (p2y - p1y));
        if (distance < 0.01)
            return false;

        double sin_alpha = Math.abs(p2y - p1y) / distance;
        double cos_alpha = Math.abs(p2x - p1x) / distance;
        
        int xmult = (p1x > p2x) ? -1 : 1;
        int ymult = (p1y > p2y) ? -1 : 1;

        GeneralPath body = new GeneralPath();
        body.moveTo((float) (p1x - xmult * (sin_alpha * (p1w / 2))),
                    (float) (p1y + ymult * (cos_alpha * (p1w / 2))));
        body.lineTo((float) (p1x + xmult * (sin_alpha * (p1w / 2))),
                    (float) (p1y - ymult * (cos_alpha * (p1w / 2))));
        body.lineTo((float) (p2x + xmult * (sin_alpha * (p2w / 2))),
                    (float) (p2y - ymult * (cos_alpha * (p2w / 2))));
        body.lineTo((float) (p2x - xmult * (sin_alpha * (p2w / 2))),
                    (float) (p2y + ymult * (cos_alpha * (p2w / 2))));
        body.closePath();

        Arc2D.Float p1cap = new Arc2D.Float();
        p1cap.setArc(p1x - (p1w / 2),
                     p1y - (p1w / 2),
                     p1w, p1w,
                     0, 360,
                     Arc2D.CHORD);
                        
        Arc2D.Float p2cap = new Arc2D.Float();
        p2cap.setArc(p2x - (p2w / 2),
                     p2y - (p2w / 2),
                     p2w, p2w,
                     0, 360,
                     Arc2D.CHORD);

        area_out.add(new Area(body));
        area_out.add(new Area(p1cap));
        area_out.add(new Area(p2cap));

        return true;
    }

    private Area calculateArea () {
        Area result = new Area();
        Area temp = new Area();
        ScribblePoint p1, p2;
        for (int j = 0;  j < (npoints - 1);  j++) {
            p1 = points[j];
            p2 = points[j+1];
            if (calculateStrokeArea (temp, p1.x, p1.y, p1.thickness, p2.x, p2.y, p2.thickness))
                result.add(temp);
        }
        return result;
    }

    public void draw (Graphics2D g, int x_offset, int y_offset) {
        // g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setColor(color);
        ScribblePoint p1, p2;
        int npoints;

        if (drawing_shape != null) {

            g.setStroke(ZERO_STROKE);
            g.fill(drawing_shape);

        } else {
            
            if (points == null) {
                p1 = (ScribblePoint) (strokes.get(0));
                npoints = strokes.size();
            } else {
                p1 = points[0];
                npoints = points.length;
            }

            for (int j = 1;  j < npoints;  j++) {
                p2 = (strokes != null) ? ((ScribblePoint) strokes.get(j)) : points[j];
                g.setStroke(new BasicStroke((p2.thickness + p1.thickness)/2,
                                            BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                g.drawLine(Math.round(p1.x - offset.x + x_offset), Math.round(p1.y - offset.y + y_offset),
                           Math.round(p2.x - offset.x + x_offset), Math.round(p2.y - offset.y + y_offset));
                p1 = p2;
            }
        }
    }

    public Rectangle getBounds() {
        if (bbox == null) {
            if (drawing_shape == null) {
                drawing_shape = calculateArea();
            }
            bbox = drawing_shape.getBounds();
        }
        return bbox;
    }
}

