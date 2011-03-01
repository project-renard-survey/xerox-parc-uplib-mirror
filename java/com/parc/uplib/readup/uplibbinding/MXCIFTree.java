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

import java.awt.geom.Point2D;
import java.awt.geom.Rectangle2D;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.io.Serializable;

/**
 * This is an implementation of the MX-CIF Tree from Samet's 
 * "Design and Analysis of Spatial Data Structures".  The code is modified from the pseudocode in the
 * book to allow searching with points instead of rectangles.  It is also modified to allow overlapping rectangles.
 * These overlapping rectangles are stored with an IntervalTree.
 *
 * Of course, this could be made more efficient with something more sophisticated than the MX-CIF.
 *
 * Created on Jul 6, 2004
 *
 * @author Lance Good
 */
public class MXCIFTree implements Serializable {
		
    public static int NW = 0;
    public static int NE = 1;
    public static int SW = 2;
    public static int SE = 3;

    public static int X_AXIS = 0;
    public static int Y_AXIS = 1;
    public static int LEFT = 0;
    public static int RIGHT = 1;
    public static int BOTH = 2;

    protected static double MIN_INTERSECT_RATIO = 0.001;
    protected static double NEAREST_SEARCH_SIZE = 5.0;

    protected Rectangle2D treeBounds;
    protected CNode treeRoot;

    public MXCIFTree(Rectangle2D treeBounds) {
        this.treeBounds = treeBounds;
    }

    public boolean isValidInput(Rectangle2D rect) {
    	Rectangle2D iSect = new Rectangle2D.Double();
    	Rectangle2D.intersect(rect,treeBounds,iSect);
    	return !(iSect.getWidth() < treeBounds.getWidth()*MIN_INTERSECT_RATIO || 
    			iSect.getHeight() < treeBounds.getHeight()*MIN_INTERSECT_RATIO);    	
    }
    
    public void insert(Rectangle2D rect) {
    	if (!isValidInput(rect)) {
    		throw new IllegalArgumentException("Input Rectangle Does Not Intersect Tree Bounds Rectangle Above Required Minimum "+(MIN_INTERSECT_RATIO*100)+"%");
    	}
    	
        treeRoot = cifInsert(rect,treeRoot,treeBounds.getCenterX(),treeBounds.getCenterY(),treeBounds.getWidth()/2.0,treeBounds.getHeight()/2.0);
    }

    public List intersect(Rectangle2D rect) {
        ArrayList results = new ArrayList();
        cifIntersect(rect,treeRoot,treeBounds.getCenterX(),treeBounds.getCenterY(),treeBounds.getWidth()/2.0,treeBounds.getHeight()/2.0,results);
		
        // We need to convert the interval results into rectangles - and make sure they actually intersect the given rectangle
        for(int i=results.size()-1; i>=0; i--) {
            IntervalTree.Interval iVal = (IntervalTree.Interval)results.get(i);
            Rectangle2D iRect = (Rectangle2D)iVal.userObj;
            if (rect.intersects(iRect)) {
                results.set(i,iRect);
            }
            else {
                results.remove(i);
            }
        }
		
        return results;
    }

    public List intersect(Point2D pt) {
        ArrayList results = new ArrayList();
        cifIntersect(pt,treeRoot,treeBounds.getCenterX(),treeBounds.getCenterY(),treeBounds.getWidth()/2.0,treeBounds.getHeight()/2.0,results);
		
        // We need to convert the interval results into rectangles - and make sure they actually intersect the given rectangle
        for(int i=results.size()-1; i>=0; i--) {
            IntervalTree.Interval iVal = (IntervalTree.Interval)results.get(i);
            Rectangle2D iRect = (Rectangle2D)iVal.userObj;
            if (iRect.contains(pt)) {
                results.set(i,iRect);
            }
            else {
                results.remove(i);
            }
        }
		
        return results;
    }

    public Rectangle2D nearest(Point2D pt) {
        if (treeRoot == null) {
            return null;	
        }
		
        // Initialize the test rectangle based on our test size
        Rectangle2D testRect = new Rectangle2D.Double(pt.getX()-NEAREST_SEARCH_SIZE/2.0,
                                                      pt.getY()-NEAREST_SEARCH_SIZE/2.0,
                                                      NEAREST_SEARCH_SIZE,
                                                      NEAREST_SEARCH_SIZE);
		
        // Increase the search size until we find an intersecting rectangle
        ArrayList results = new ArrayList();
        while (results.isEmpty()) {
            cifIntersect(testRect,treeRoot,treeBounds.getCenterX(),treeBounds.getCenterY(),treeBounds.getWidth()/2.0,treeBounds.getHeight()/2.0,results);

            // We need to remove any rectangles that don't really intersect the test rectangle 
            for(int i=results.size()-1; i>=0; i--) {
                IntervalTree.Interval iVal = (IntervalTree.Interval)results.get(i);
                Rectangle2D iRect = (Rectangle2D)iVal.userObj;
                if (!testRect.intersects(iRect)) {
                    results.remove(i);
                }
            }
			
            // Double our search size if we don't find anything
            testRect.setRect(testRect.getX()-testRect.getWidth()/2.0,
                             testRect.getY()-testRect.getHeight()/2.0,
                             testRect.getWidth()*2.0,
                             testRect.getHeight()*2.0);	
        }
		
        // Now determine the closest of the available alternatives
        double minDist = Double.MAX_VALUE;
        Rectangle2D minRect = null;
        for(Iterator i=results.iterator(); i.hasNext();) {
            IntervalTree.Interval iVal = (IntervalTree.Interval)i.next();
            Rectangle2D curRect = (Rectangle2D)iVal.userObj;			
            double curDist = distance(curRect,pt);
            if (curDist < minDist) {
                minDist = curDist;
                minRect = curRect;
            } else if (curDist == minDist) {
            	// Prefer smaller rectangles to larger ones in the case of a tie.
            	// This helps work around some bugs where a word will be assigned an inappropriately large word box,
            	// that overlaps the word boxes of other words, making the other words impossible to select.
            	double minRectW = minRect.getWidth();
            	double curRectW = curRect.getWidth();
            	if (curRectW < minRectW) {
            		minRect = curRect;
            	}
            }
        }
		
        return minRect;
    }

    protected int cifCompare(Rectangle2D p, double cx, double cy) {
        if (p.getCenterX() < cx) {
            if (p.getCenterY() < cy) {
                return SW;
            }
            else {
                return NW;	
            }
        }	
        else {
            if (p.getCenterY() < cy) {
                return SE;
            }
            else {
                return NE;	
            }
        }
    }

    protected int binCompare(Rectangle2D p, double cv, int v) {
        if (v == X_AXIS) {
            if (p.getX() <= cv && cv <= p.getX()+p.getWidth()) {
                return BOTH;
            }
            else if (p.getCenterX() < cv) {
                return LEFT;	
            }
            else {
                return RIGHT;	
            }
        }
        else {
            if (p.getY() <= cv && cv <= p.getY()+p.getHeight()) {
                return BOTH;
            }
            else if (p.getCenterY() < cv) {
                return LEFT;	
            }
            else {
                return RIGHT;	
            }			
        }
    }

    protected int binCompare(Point2D p, double cv, int v) {
        if (v == X_AXIS) {
            if (p.getX() < cv) {
                return LEFT;	
            }
            else if (p.getX() == cv) {
                return BOTH;
            }
            else {
                return RIGHT;	
            }
        }
        else {
            if (p.getY() < cv) {
                return LEFT;	
            }
            else if (p.getY() == cv) {
                return BOTH;
            }
            else {
                return RIGHT;	
            }			
        }
    }

    protected CNode cifInsert(Rectangle2D p, CNode r, double cx, double cy, double lx, double ly) {
        double[] xf = new double[]{-1.0,1.0,-1.0,1.0};
        double[] yf = new double[]{1.0,1.0,-1.0,-1.0};
		
        if (r == null) {
            r = new CNode();	
        }	
		
        CNode t = r;
        double dx = binCompare(p,cx,X_AXIS);
        double dy = binCompare(p,cy,Y_AXIS);
        while (dx != BOTH && dy != BOTH) {
            int q = cifCompare(p,cx,cy);
            if (t.getSon(q) == null) {
                t.setSon(q,new CNode());
            }
            t = t.getSon(q);
			
            lx = lx/2.0;
            ly = ly/2.0;
            cx = cx+xf[q]*lx;
            cy = cy+yf[q]*ly;
			
            dx = binCompare(p,cx,X_AXIS);
            dy = binCompare(p,cy,Y_AXIS);
        }
		
        if (dx == BOTH) {
            insertAxis(p,t,cy,ly,Y_AXIS);	
        }
        else {
            insertAxis(p,t,cx,lx,X_AXIS);
        }
		
        return r;
    }

    protected void insertAxis(Rectangle2D p, CNode r, double cv, double lv, int v) {
        double[] vf = new double[]{-1.0,1.0};
		
        if (r.getBin(v) == null) {
            r.setBin(v,new BNode());
        }

        BNode t = r.getBin(v);
        int d = binCompare(p,cv,v);
        while (d != BOTH) {
            if (t.getSon(d) == null) {
                t.setSon(d,new BNode());	
            }
            t = t.getSon(d);
            lv = lv/2.0;
            cv = cv+vf[d]*lv;
            d = binCompare(p,cv,v);
        }
        t.addRectangle(p,v);
    }

    protected void cifIntersect(Rectangle2D p, CNode r, double cx, double cy, double lx, double ly, ArrayList results) {
        double[] xf = new double[]{-1.0,1.0,-1.0,1.0};
        double[] yf = new double[]{1.0,1.0,-1.0,-1.0};

        if (r == null) {
            return;
        }
        else {
            if (!p.intersects(cx-lx,cy-ly,2*lx,2*ly)) {
                return;	
            }
            else {				
                crossAxis(p,r.getBin(Y_AXIS),cy,ly,Y_AXIS,results);
                crossAxis(p,r.getBin(X_AXIS),cx,lx,X_AXIS,results);

                lx = lx/2.0;
                ly = ly/2.0;
                for(int q=0; q<4; q++) {
                    cifIntersect(p,r.getSon(q),cx+xf[q]*lx,cy+yf[q]*ly,lx,ly,results);
                }
            }
        }
    }
	
    protected void crossAxis(Rectangle2D p, BNode r, double cv, double lv, int v, ArrayList results) {
        double[] vf = new double[]{-1.0,1.0};
		
        if (r == null) {
            return;	
        }
        else {
            // Intersect with the given node first
            r.intersect(p,v,results);

            // Now see which other nodes to intersect
            int d = binCompare(p,cv,v);
            lv = lv/2.0;
            if (d == BOTH) {
                crossAxis(p,r.getSon(LEFT),cv-lv,lv,v,results);
                crossAxis(p,r.getSon(RIGHT),cv+lv,lv,v,results); 	
            }
            else {
                crossAxis(p,r.getSon(d),cv+vf[d]*lv,lv,v,results);	
            }
        }
    }

    protected void cifIntersect(Point2D p, CNode r, double cx, double cy, double lx, double ly, ArrayList results) {
        double[] xf = new double[]{-1.0,1.0,-1.0,1.0};
        double[] yf = new double[]{1.0,1.0,-1.0,-1.0};

        if (r == null) {
            return;
        }
        else {
            if (!contains(p,cx-lx,cy-ly,2.0*lx,2.0*ly)) {
                return;	
            }
            else {
                crossAxis(p,r.getBin(Y_AXIS),cy,ly,Y_AXIS,results);
                crossAxis(p,r.getBin(X_AXIS),cx,lx,X_AXIS,results);

                lx = lx/2.0;
                ly = ly/2.0;
                for(int q=0; q<4; q++) {
                    cifIntersect(p,r.getSon(q),cx+xf[q]*lx,cy+yf[q]*ly,lx,ly,results);
                }
            }
        }
    }

    protected void crossAxis(Point2D p, BNode r, double cv, double lv, int v, ArrayList results) {
        double[] vf = new double[]{-1.0,1.0};
		
        if (r == null) {
            return;	
        }
        else {
            r.intersect(p,v,results);
			
            int d = binCompare(p,cv,v);
            lv = lv/2.0;
            if (d == BOTH) {
                crossAxis(p,r.getSon(LEFT),cv-lv,lv,v,results);
                crossAxis(p,r.getSon(RIGHT),cv+lv,lv,v,results); 	
            }
            else {
                crossAxis(p,r.getSon(d),cv+vf[d]*lv,lv,v,results);	
            }
        }
    }

    /**
     * A simple test to see if the given point is contained by the given rectangle
     */
    protected static boolean contains(Point2D p, double x, double y, double w, double h) {
        return (p.getX() >= x && p.getX() <= x+w && p.getY() >= y && p.getY() <= y+h);
    }

    /**
     * Calculate the min distance from a point to a rectangle
     */
    protected static double distance(Rectangle2D rect, Point2D pt) {
        if (rect.contains(pt)) {
            return 0.0;	
        }
        else {
            if (pt.getX() < rect.getMinX()) {
                if (pt.getY() < rect.getMinY()) {
                    return pt.distance(rect.getMinX(),rect.getMinY());	
                }	
                else if (rect.getMinY() <= pt.getY() && pt.getY() <= rect.getMaxY()){
                    return pt.distance(rect.getMinX(),pt.getY());
                }
                else {
                    return pt.distance(rect.getMinX(),rect.getMaxY());	
                }
            }
            else if (rect.getMinX() <= pt.getX() && pt.getX() <= rect.getMaxX()) {
                if (pt.getY() < rect.getMinY()) {
                    return pt.distance(pt.getX(),rect.getMinX());	
                }
                // We know the rect does not contain the point so one case is left out
                else {
                    return pt.distance(pt.getX(),rect.getMaxX());
                }
            }
            else {
                if (pt.getY() < rect.getMinY()) {
                    return pt.distance(rect.getMaxX(),rect.getMinY());	
                }
                else if (rect.getMinY() <= pt.getY() && pt.getY() <= rect.getMaxY()) {
                    return pt.distance(rect.getMaxX(),pt.getY());	
                }
                else {
                    return pt.distance(rect.getMaxX(),rect.getMaxY());	
                }
            }
        }
    }

    /**
     * This is the MX-CIF tree node - it has four children nodes and two binary trees for the x and y axis 
     * @author good
     */
    protected class CNode implements Serializable {
        protected CNode nwChild;
        protected CNode neChild;
        protected CNode swChild;
        protected CNode seChild;
        protected BNode xTree;
        protected BNode yTree;
		
        public CNode getSon(int dir) {
            if (dir == NW) {
                return nwChild;	
            }	
            else if (dir == NE) {
                return neChild;	
            }
            else if (dir == SW) {
                return swChild;	
            }
            else {
                return seChild;	
            }
        }
		
        public void setSon(int dir, CNode aNode) {
            if (dir == NW) {
                nwChild = aNode;	
            }	
            else if (dir == NE) {
                neChild = aNode;	
            }
            else if (dir == SW) {
                swChild = aNode;	
            }
            else {
                seChild = aNode;	
            }
        }
		
        public BNode getBin(int dir) {
            if (dir == X_AXIS) {
                return xTree;	
            }
            else {
                return yTree;	
            }
        }
		
        public void setBin(int dir, BNode aTree) {
            if (dir == LEFT) {
                xTree = aTree;	
            }	
            else {
                yTree = aTree;	
            } 
        }
    } 

    /**
     * This is a Binary tree node.  It has a left and right child and an interval tree payload.
     * @author good
     */
    protected class BNode implements Serializable {
        protected IntervalTree iTree;
        protected BNode left;
        protected BNode right;
		
        public BNode getSon(int dir) {
            if (dir == LEFT) {
                return left;
            }
            else {
                return right;	
            }	
        }
		
        public void setSon(int dir, BNode aNode) {
            if (dir == LEFT) {
                left = aNode;
            }
            else {
                right = aNode;	
            }	
        }
		
        public void addRectangle(Rectangle2D rect, int axis) {
            if (iTree == null) {
                iTree = new IntervalTree();
            }
			
            IntervalTree.Interval interval = new IntervalTree.Interval();
            interval.userObj = rect;
            if (axis == X_AXIS) {
                interval.low = rect.getMinX();
                interval.high = rect.getMaxX();
            }
            else {
                interval.low = rect.getMinY();
                interval.high = rect.getMaxY();
            }
			
            iTree.insert(interval);
        }
		
        public void intersect(Rectangle2D rect, int axis, ArrayList aList) {
            if (iTree != null) {
                IntervalTree.Interval interval = new IntervalTree.Interval();
                if (axis == X_AXIS) {
                    interval.low = rect.getMinX();
                    interval.high = rect.getMaxX(); 
                }
                else {
                    interval.low = rect.getMinY();
                    interval.high = rect.getMaxY(); 				 
                }
			
                iTree.intervalSearch(interval,aList);
            }
        }
		
        public void intersect(Point2D rect, int axis, ArrayList aList) {
            if (iTree != null) {
                IntervalTree.Interval interval = new IntervalTree.Interval();
                if (axis == X_AXIS) {
                    interval.low = rect.getX();
                    interval.high = rect.getX(); 
                }
                else {
                    interval.low = rect.getY();
                    interval.high = rect.getY(); 				 
                }
			
                iTree.intervalSearch(interval,aList);				
            }
        }
    } 

    public static void main(String[] args) {
    	MXCIFTree tree = new MXCIFTree(new Rectangle2D.Double(0,0,1000,1000));
    	tree.insert(new Rectangle2D.Double(50,50,10,10));
    	tree.insert(new Rectangle2D.Double(300,300,5,10));
    	tree.insert(new Rectangle2D.Double(700,600,30,40));
    	List aList = tree.intersect(new Rectangle2D.Double(25,25,300,300));
    	System.out.println(aList);
    	
    	tree.insert(new Rectangle2D.Double(1050,1050,40,40));
    }
}
