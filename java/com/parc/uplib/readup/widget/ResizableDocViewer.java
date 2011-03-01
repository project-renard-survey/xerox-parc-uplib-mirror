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
 * Created on Aug 2, 2004
 */
package com.parc.uplib.readup.widget;

import java.awt.Component;
import java.awt.Container;
import java.awt.Dimension;
import java.awt.LayoutManager2;

/**
 * A simple wrapper for DocViewer that scales itself to fit it's given bounds 
 * 
 * @author Lance Good
 */
public class ResizableDocViewer extends ScaledJComponent {

    DocViewer dViewer;

    public ResizableDocViewer(SoftReferenceCache pageLoader,
                              SoftReferenceCache thumbnailLoader,
                              String documentTitle,
                              String documentID,
                              DocViewerCallback logoURL,
                              int pageCount,
                              int firstPageNumber,
                              String pageNumberData,
                              int currentPage,
                              Dimension pageSize,
                              Dimension thumbnailSize,
                              boolean showControls,
                              int topEdge,
                              int bottomEdge,
                              boolean twoPages,
                              Scribble[] scribbles,
                              AnnotationStreamHandler scribbleHandler,
                              HotSpot[] hotspots,
                              DocViewerCallback activityLogger,
                              boolean activitiesOn,
                              boolean annotationsOn,
                              int initialAnnotationInkpot,
                              String bookmarkData,
                              int pageturnAnimationTime,
                              int splashPagePeriod,
                              SoftReferenceCache pagetextLoader,
                              DocViewerCallback urlDisplayer,
                              AnnotationStreamHandler notes_saver,
                              SoftReferenceCache notes_loader) {

        dViewer = new DocViewer(pageLoader,
                                thumbnailLoader,
                                documentTitle,
                                documentID,
                                logoURL,
                                pageCount,
                                firstPageNumber,
                                pageNumberData,
                                currentPage,
                                pageSize,
                                thumbnailSize,
                                showControls,
                                topEdge,
                                bottomEdge,
                                twoPages,
                                scribbles,
                                scribbleHandler,
                                hotspots,
                                activityLogger,
                                activitiesOn,
                                annotationsOn,
                                initialAnnotationInkpot,
                                bookmarkData,
                                pageturnAnimationTime,
                                splashPagePeriod,
                                pagetextLoader,
                                urlDisplayer,
                                notes_saver,
                                notes_loader);
        getContentPane().add(dViewer);
        setXScale(1.0);
        setYScale(1.0);
    }

    public ResizableDocViewer(DocViewer dViewer) {
        this.dViewer = dViewer;
        getContentPane().add(dViewer);
        setXScale(1.0);
        setYScale(1.0);
    }

    public DocViewer getDocViewer() {
        return dViewer;
    }

    /**
     * This provides a layout for the child that sets the child to it's preferred size
     */
    protected ContentPane createContentPane() {
        ContentPane comp = new ContentPane();
		
        comp.setLayout(new LayoutManager2() {
                public void addLayoutComponent(Component comp, Object constraints) {
                }
                public void addLayoutComponent(String name, Component comp) {
                }
                public void removeLayoutComponent(Component comp) {
                }
                public void invalidateLayout(Container target) {
                }
                public float getLayoutAlignmentX(Container target) {
                    return 0;
                }
                public float getLayoutAlignmentY(Container target) {
                    return 0;
                }
                public Dimension maximumLayoutSize(Container target) {
                    return dViewer.getMaximumSize();
                }
                public Dimension minimumLayoutSize(Container parent) {
                    return dViewer.getMinimumSize();
                }
                public Dimension preferredLayoutSize(Container parent) {
                    return dViewer.getPreferredSize();
                }
                public void layoutContainer(Container parent) {
                    dViewer.setLocation(0,0);
                    dViewer.setSize(dViewer.getPreferredSize());
                }
            });
        return comp;	
    }

    public void setBounds(int x, int y, int w, int h) {
        Dimension d = dViewer.getPreferredSize();
        setXScale(d.getWidth()/w);
        setYScale(d.getHeight()/h);
        /*
        double scale = d.getWidth()/w;
        if ((d.getHeight()/h) > scale)
            scale = d.getHeight()/h;
        setXScale(scale);
        setYScale(scale);
        */
        super.setBounds(x,y,w,h);
    }

    public Dimension getPreferredSize() {
        Dimension d = dViewer.getPreferredSize();
        return d;
    }

    public void resizeToUnitTransform () {
        setXScale(1.0);
        setYScale(1.0);
        Dimension d = dViewer.getPreferredSize();
        setSize(d.width, d.height);
        invalidate();
        Container toplevel = getTopLevelAncestor();
        if (toplevel instanceof java.awt.Window) {
            toplevel.setSize(toplevel.getPreferredSize());
            invalidate();
        }
    }
}
