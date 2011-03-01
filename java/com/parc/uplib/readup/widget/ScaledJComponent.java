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

/*
 * Created on Feb 21, 2004
 */

import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.Container;
import java.awt.Cursor;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Image;
import java.awt.Point;
import java.awt.RenderingHints;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.event.MouseMotionListener;
import java.awt.event.MouseWheelEvent;
import java.awt.event.MouseWheelListener;
import java.awt.geom.Point2D;
import java.awt.image.VolatileImage;
import java.util.Vector;

import javax.swing.JButton;
import javax.swing.JColorChooser;
import javax.swing.JComponent;
import javax.swing.JFrame;
import javax.swing.RepaintManager;
import javax.swing.SwingUtilities;

/**
 * A JComponent that allows you to specify an X and Y scale at which to view the components added to the Content Pane.
 * This class should be used like a JFrame.  All components should be added to the content pane.
 * @author Lance Good
 */
public class ScaledJComponent extends JComponent {

	// Scale to test the component
	final protected static double DEMO_SCALE = 2.0;

	 // A fake mouse event used by setToolTipText to force immediate updates of the ToolTipText
	final MouseEvent FAKE_MOUSE_EVENT = new MouseEvent(this,MouseEvent.MOUSE_ENTERED,0,0,0,0,0,false);

	// A local copy of cursor to restore the original cursor value after any internal changes
	Cursor cursor = getCursor();
	
	// The contents of the content pane rendered as an image
	protected Image backBuffer;

	// Should image rendering be used
	protected boolean imageRenderingEnabled = false;
	
	// Should the contents be revalidated
	protected boolean shouldRevalidate = true;
		
	// The zero pane is necessary so that no other mouse events are passed to the content pane 
	protected ZeroPane zeroPane;
		
	// The container for all the actual components to be scaled.
	protected ContentPane cPane;
	
	// Retargets mouse events to the scaled content
	protected Retargeter retargeter;
		
	// Passes mouse events to the appropriate component based on the event retargeter
	protected ScaledMouseHandler handler;
		
	protected double scaleX = DEMO_SCALE;
	protected double scaleY = DEMO_SCALE;

	// Should safe repaints be enforced - i.e. no repaint calls from the paint method
	protected boolean safeRepaints;
	
	/**
	 * Default constructor
	 */
	public ScaledJComponent() {
		this(false);
	}
	
	public ScaledJComponent(boolean safeRepaints) {
		this.safeRepaints = safeRepaints;

		buildUI();
		
		initEvents();		
	}

	/**
	 * Do any necessary UI construction.  Set layouts, build panes, and set the repaint manager.
	 */
	protected void buildUI() {
		this.setLayout(null);
		zeroPane = createZeroPane();
		cPane = createContentPane();
		zeroPane.add(cPane);
		add(zeroPane);

		if (!(RepaintManager.currentManager(this) instanceof LockingRepaintManager)) {
			RepaintManager.setCurrentManager(new LockingRepaintManager());
		}
	}

	/**
	 * Do any event related setup 
	 */
	protected void initEvents() {
		setFocusable(false);
		zeroPane.setFocusable(false);
		
		retargeter = createRetargeter();
		handler = createScaledMouseHandler();
		addMouseListener(handler);
		addMouseMotionListener(handler);
		addMouseWheelListener(handler);
	}

	/**
	 * This can be overridden by subclasses if necessary
	 */
	protected ZeroPane createZeroPane() {
		ZeroPane comp = new ZeroPane();
		comp.setLayout(null);
		comp.setSize(0,0);
		return comp;
	}

	/**
	 * This can be overridden by subclasses if necessary
	 */
	protected JComponent createMousePane() {
		JComponent comp = new JComponent() {};
		comp.setLayout(null);
		return comp;
	}

	/**
	 * This can be overridden by subclasses if necessary
	 */
	protected ContentPane createContentPane() {
		ContentPane comp = new ContentPane(); 
		comp.setLayout(new BorderLayout());
		//comp.setDoubleBuffered(false);
		return comp;	
	}

	/**
	 * This can be overridden by subclasses if necessary
	 */
	protected Retargeter createRetargeter() {
		return new DefaultEventRetargeter();
	}

	/**
	 * This can be overridden by subclasses if necessary
	 */
	protected ScaledMouseHandler createScaledMouseHandler() {
		return new ScaledMouseHandler();
	}

	/**
	 * Accessor method for the content pane to mirror the JFrame content pane method 
	 */
	public JComponent getContentPane() {
		return cPane;
	}

	/**
	 * Scale the passed rectangle and repaint it
	 */
	public void repaintContentPane(int x, int y, int w, int h) {
		repaint((int)(x/getXScale()),(int)(y/getYScale()),(int)(w/getXScale()+2.0),(int)(h/getYScale()+2.0));
	}
	
	/**
	 * This does the proper setup for the scaled paint call.  It paints the backbuffer with the content and locks
	 * the repaint manager.
	 */
	public void paintComponent(Graphics g) {
		LockingRepaintManager manager = (LockingRepaintManager)RepaintManager.currentManager(this);		
		if (safeRepaints) {
			manager.lockRepaint(this);
		}

		safePaintComponent(g);

		if (safeRepaints) {
			manager.unlockRepaint(this);
		}
	}

	/**
	 * A safe paint method in which the repaint manager has been locked
	 */
	protected void safePaintComponent(Graphics g) {
		validateContentPane();

		// Use either the direct rendering or image rendering depending on the flag
		if (!imageRenderingEnabled) {
			Graphics2D g2 = (Graphics2D)g;
			g2.setColor(getBackground());
			g2.fillRect(0,0,getWidth(),getHeight());
			g2.scale(1/getXScale(),1/getYScale());
			cPane.paint(g2);
			g2.scale(getXScale(),getYScale());
		}
		else {
			int returnCode = VolatileImage.IMAGE_OK;
			do {
				paintContentToBuffer();
				paintScaledComponent(g, backBuffer);
			
				if (backBuffer instanceof VolatileImage) {
					returnCode = ((VolatileImage)backBuffer).validate(getGraphicsConfiguration());
				}
			} while (backBuffer instanceof VolatileImage &&
					 ((VolatileImage)backBuffer).contentsLost() && 
					 returnCode != VolatileImage.IMAGE_OK);
		}
	}

	protected void paintContentToBuffer() {
		int sW = (int)(getXScale()*getWidth()+0.5);
		int sH = (int)(getYScale()*getHeight()+0.5);
				
		if (backBuffer instanceof VolatileImage && ((VolatileImage)backBuffer).validate(getGraphicsConfiguration()) == VolatileImage.IMAGE_INCOMPATIBLE) {
			// old buffer doesn't work with new GraphicsConfig; re-create it
			backBuffer = createOffscreenImage(sW, sH);
		}
		
		Graphics2D g2 = (Graphics2D)backBuffer.getGraphics();
		g2.setColor(getBackground());
		g2.fillRect(0,0,backBuffer.getWidth(this),backBuffer.getHeight(this));
		cPane.paint(g2);
		g2.dispose();
	}
	
	/**
	 * Should be overridden by subclasses instead of paint component
	 */
	protected void paintScaledComponent(Graphics g, Image componentImage) {
		((Graphics2D)g).setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_BICUBIC);
		g.drawImage(componentImage,0,0,getWidth(),getHeight(),0,0,componentImage.getWidth(this),componentImage.getHeight(this),this);
	}
			
	/**
	 * Overridden to update the image size and the content pane size. 
	 */
	public void setBounds(int x, int y, int w, int h) {
		super.setBounds(x,y,w,h);
		invalidateContentPane();
	}

	/**
	 * Validate the content pane and any image buffers if necessary
	 */
	protected void validateContentPane() {
		if (shouldRevalidate) {
			int sW = (int)(getXScale()*getWidth()+0.5);
			int sH = (int)(getYScale()*getHeight()+0.5);

			if (backBuffer != null) {
				backBuffer.flush();
			}
			
			if (imageRenderingEnabled) {
				backBuffer = createOffscreenImage(sW,sH);
			}
			
			if (cPane.getWidth() != sW ||
				cPane.getHeight() != sH) {
				cPane.setBounds(0,0,sW,sH);
				cPane.revalidate();
			}

			shouldRevalidate = false;
		}		
	}

	/**
	 * Notify the component that a new back buffer is needed because the size or one of the scales has changed. 
	 */
	public void invalidateContentPane() {
		shouldRevalidate = true;
	}

	/**
	 * Use a volatile image by default
	 */
	public Image createOffscreenImage(int sW, int sH) {
		//return getGraphicsConfiguration().createCompatibleImage(sW,sH);
		return getGraphicsConfiguration().createCompatibleVolatileImage(sW,sH);
	}

	public double getXScale() {
		return scaleX;
	}
	
	public void setXScale(double scale) {
		this.scaleX = scale;
	}
	
	public double getYScale() {
		return scaleY;
	}
	
	public void setYScale(double scale) {
		this.scaleY = scale;
	}

	/**
	 * Sets the cursor for this ZCanvas
	 * @param c The new cursor
	 */
	public void setCursor(Cursor c) {
		setCursor(c,true);
	}

	/**
	 * Sets the cursor for this component.  If realSet is
	 * true then the cursor that displays when the mouse is over the
	 * component is set as well as the currently displayed cursor.
	 * If realSet is false then only the currently displayed cursor is changed
	 * to indicate that the mouse is over a deeper component within the
	 * component.
	 * @param c The new cursor
	 * @param realSet true - The component cursor and current cursor set
	 *                false - Only the current cursor set
	 */
	public void setCursor(Cursor c, boolean realSet) {
		if (realSet) {
			cursor = c;
		}
		super.setCursor(c);
	}

	/**
	 * Sets the current cursor to the ZCanvas's cursor.
	 */
	public void resetCursor() {
		setCursor(cursor, false);
	}

	/**
	 * Disable double buffering on any components added to the content pane
	 */
	public static void disableDoubleBuffering(Component c) {
		Component[] children = null;
		if (c instanceof Container) {
			children = ((Container)c).getComponents();
		}

		if (children != null) {
			for (int j=0; j<children.length; j++) {
				disableDoubleBuffering(children[j]);
			}
		}

		if (c instanceof JComponent) {
			((JComponent)c).setDoubleBuffered(false);
		}
	}

	//////////////////////////////////////////////////////////////////////////////////
	//
	// Some internal classes needed to make the whole thing work
	//
	//////////////////////////////////////////////////////////////////////////////////

	/**
	 * The zero pane prevents the *actual* mouse events from reaching the content pane 
	 */
	public class ZeroPane extends JComponent {}

	/**
	 * The content pane disables double buffering on any component added 
	 */
	public class ContentPane extends JComponent {
		public Component add(Component comp) {
			disableDoubleBuffering(comp);
			return super.add(comp);
		}
	}

	/**
	 * An event retargeter.  Takes the local mouse position and maps it onto the scaled mouse position 
	 */
	public static interface Retargeter {
		public void localToScaled(Point2D localPt);
	}
	
	/**
	 * The default retargeter that just scales the events appropriately. 
	 */
	public class DefaultEventRetargeter implements Retargeter {
		public void localToScaled(Point2D localPt) {
			localPt.setLocation((int)(localPt.getX()*getXScale()+0.5),
								(int)(localPt.getY()*getYScale()+0.5));
		}		
	}

	/**
	 * Retargets mouse events to the scaled content
	 */
	public class ScaledMouseHandler implements MouseListener, MouseMotionListener, MouseWheelListener {

		// The previous component - used to generate mouseEntered and
		// mouseExited events
		Component prevComponent = null;

		// The components whose cursor is on the screen
		Component cursorComponent = null;

		// Previous points used in generating mouseEntered and mouseExited
		// events
		Point2D prevPoint = null;
		Point2D prevOff = null;

		// The focused component for the left button
		Component focusComponentLeft = null;

		// Offsets for the focused node for the left button
		int focusOffXLeft = 0;
		int focusOffYLeft = 0;

		// The focused component for the middle button
		Component focusComponentMiddle = null;

		// Offsets for the focused node for the middle button
		int focusOffXMiddle = 0;
		int focusOffYMiddle = 0;

		// The focused component for the right button
		Component focusComponentRight = null;

		// Offsets for the focused node for the right button
		int focusOffXRight = 0;
		int focusOffYRight = 0;

		public void mousePressed(MouseEvent e1) {
			dispatchScaledEvent(e1);
		}

		public void mouseReleased(MouseEvent e1) {
			dispatchScaledEvent(e1);
		}

		public void mouseClicked(MouseEvent e1) {
			dispatchScaledEvent(e1);
		}

		public void mouseExited(MouseEvent e1) {
			dispatchScaledEvent(e1);
		}

		public void mouseEntered(MouseEvent e1) {
			dispatchScaledEvent(e1);
		}

		public void mouseMoved(MouseEvent e1) {
			dispatchScaledEvent(e1);
		}

		public void mouseDragged(MouseEvent e1) {
			dispatchScaledEvent(e1);
		}

		public void mouseWheelMoved(MouseWheelEvent e) {
			dispatchWheelEvent(e);			
		}

		// A re-implementation of Container.findComponentAt that ensures
		// that the returned component is *SHOWING* not just visible
		Component findComponentAt(Component c, int x, int y) {
			if (!c.contains(x,y)) {
				return null;
			}

			if (c instanceof Container) {
				Container contain = ((Container)c);
				int ncomponents = contain.getComponentCount();
				Component component[] = contain.getComponents();

				for (int i = 0; i < ncomponents; i++) {
					Component comp = component[i];
					if (comp != null) {
						Point p = comp.getLocation();
						if (comp instanceof Container) {
							comp = findComponentAt(comp, x - (int)p.getX(), y - (int)p.getY());
						}
						else {
							comp = comp.getComponentAt(x - (int)p.getX(), y - (int)p.getY());
						}
						if (comp != null && comp.isShowing()) {
							return comp;
						}
					}
				}
			}
			return c;
		}

		public void dispatchWheelEvent(MouseWheelEvent e1) {
			Point2D pt = e1.getPoint();
			retargeter.localToScaled(pt);
			Component comp = findComponentAt(cPane, (int) pt.getX(), (int) pt.getY());
			if (comp != null) {
				MouseWheelEvent e2 =
					new MouseWheelEvent(
						comp,
						e1.getID(),
						e1.getWhen(),
						e1.getModifiers(),
						(int) pt.getX() - focusOffXLeft,
						(int) pt.getY() - focusOffYLeft,
						e1.getClickCount(),
						e1.isPopupTrigger(),
						e1.getScrollType(),
						e1.getScrollAmount(),
						e1.getWheelRotation());

				comp.dispatchEvent(e2);
				// comp.repaint();

				e1.consume();				
			}
		}
		
		public void dispatchScaledEvent(MouseEvent e1) {
			Component comp = null;
			Point2D pt = e1.getPoint();
			retargeter.localToScaled(pt);

			if (prevPoint == null) {
				prevPoint = pt;
			}
			if (prevOff == null) {
				prevOff = new Point2D.Double(0,0);
			}

			// The offsets to put the event in the correct context
			int offX = 0;
			int offY = 0;

			// This is only partially fixed to find the deepest
			// component at pt.  It needs to do something like
			// package private method:
			// Container.getMouseEventTarget(int,int,boolean)
			comp = findComponentAt(cPane, (int) pt.getX(), (int) pt.getY());

			// We found the right component - but we need to
			// get the offset to put the event in the component's
			// coordinates
			if (comp != null && comp != cPane) {
				for (Component c = comp; c != cPane; c = c.getParent()) {
					offX += c.getLocation().getX();
					offY += c.getLocation().getY();
				}
			}

			// Mouse Pressed gives focus - effects Mouse Drags and
			// Mouse Releases
			if (comp != null && e1.getID() == MouseEvent.MOUSE_PRESSED) {
				if (SwingUtilities.isLeftMouseButton(e1)) {
					focusComponentLeft = comp;
				}
				else if (SwingUtilities.isMiddleMouseButton(e1)) {
					focusComponentMiddle = comp;
				}
				else if (SwingUtilities.isRightMouseButton(e1)) {
					focusComponentRight = comp;
				}
			}
			
			// This first case we don't want to give events to just
			// any Swing component - but to the one that got the
			// original mousePressed
			if (e1.getID() == MouseEvent.MOUSE_DRAGGED || e1.getID() == MouseEvent.MOUSE_RELEASED) {

			    // LEFT MOUSE BUTTON
			    if (SwingUtilities.isLeftMouseButton(e1) && focusComponentLeft != null) {
				focusOffXLeft = 0;
				focusOffYLeft = 0;
				for (Component c = focusComponentLeft; c != cPane; c = c.getParent()) {
				    focusOffXLeft += c.getLocation().getX();
				    focusOffYLeft += c.getLocation().getY();
				}
				    
				MouseEvent e2 =
				    new MouseEvent(
						   focusComponentLeft,
						   e1.getID(),
						   e1.getWhen(),
						   e1.getModifiers(),
						   (int) pt.getX() - focusOffXLeft,
						   (int) pt.getY() - focusOffYLeft,
						   e1.getClickCount(),
						   e1.isPopupTrigger(),
                                                   e1.getButton());

				focusComponentLeft.dispatchEvent(e2);
				// focusComponentLeft.repaint();

				e1.consume();

				if (e1.getID() == MouseEvent.MOUSE_RELEASED) {
				    focusComponentLeft = null;
				}
			    }

			    // MIDDLE MOUSE BUTTON
			    if (SwingUtilities.isMiddleMouseButton(e1) && focusComponentMiddle != null) {
				focusOffXMiddle = 0;
				focusOffYMiddle = 0;
				for (Component c = focusComponentMiddle; c != cPane; c = c.getParent()) {
				    focusOffXMiddle += c.getLocation().getX();
				    focusOffYMiddle += c.getLocation().getY();
				}
				    
				MouseEvent e2 =
				    new MouseEvent(
						   focusComponentMiddle,
						   e1.getID(),
						   e1.getWhen(),
						   e1.getModifiers(),
						   (int) pt.getX() - focusOffXMiddle,
						   (int) pt.getY() - focusOffYMiddle,
						   e1.getClickCount(),
						   e1.isPopupTrigger(),
                                                   e1.getButton());
							
				focusComponentMiddle.dispatchEvent(e2);
				// focusComponentMiddle.repaint();

				e1.consume();

				if (e1.getID() == MouseEvent.MOUSE_RELEASED) {
				    focusComponentMiddle = null;
				}
			    }

			    // RIGHT MOUSE BUTTON
			    if (SwingUtilities.isRightMouseButton(e1) && focusComponentRight != null) {
				focusOffXRight = 0;
				focusOffYRight = 0;
				for (Component c = focusComponentRight; c != cPane; c = c.getParent()) {
				    focusOffXRight += c.getLocation().getX();
				    focusOffYRight += c.getLocation().getY();
				}
				    
				MouseEvent e2 =
				    new MouseEvent(
						   focusComponentRight,
						   e1.getID(),
						   e1.getWhen(),
						   e1.getModifiers(),
						   (int) pt.getX() - focusOffXRight,
						   (int) pt.getY() - focusOffYRight,
						   e1.getClickCount(),
						   e1.isPopupTrigger(),
                                                   e1.getButton());
							
				focusComponentRight.dispatchEvent(e2);
				// focusComponentRight.repaint();

				e1.consume();

				if (e1.getID() == MouseEvent.MOUSE_RELEASED) {
				    focusComponentRight = null;
				}

			    }
			}

			// This case covers the cases mousePressed, mouseClicked,
			// and mouseMoved events
			else if (
				(e1.getID() == MouseEvent.MOUSE_PRESSED || e1.getID() == MouseEvent.MOUSE_CLICKED || e1.getID() == MouseEvent.MOUSE_MOVED)
					&& (comp != null)) {

				MouseEvent e2 =
					new MouseEvent(
						comp,
						e1.getID(),
						e1.getWhen(),
						e1.getModifiers(),
						(int) pt.getX() - offX,
						(int) pt.getY() - offY,
						e1.getClickCount(),
                                                       e1.isPopupTrigger(),
                                                       e1.getButton());

				comp.dispatchEvent(e2);

				e1.consume();
			}

			// Now we need to check if an exit or enter event needs to
			// be dispatched - this code is independent of the mouseButtons.
			// I tested in normal Swing to see the correct behavior.
			if (prevComponent != null) {
				// This means mouseExited

				if (comp == null || e1.getID() == MouseEvent.MOUSE_EXITED) {
					MouseEvent e2 =
						new MouseEvent(
							prevComponent,
							MouseEvent.MOUSE_EXITED,
							e1.getWhen(),
							0,
							(int) prevPoint.getX() - (int) prevOff.getX(),
							(int) prevPoint.getY() - (int) prevOff.getY(),
							e1.getClickCount(),
                                                               e1.isPopupTrigger(),
                                                               e1.getButton());

					prevComponent.dispatchEvent(e2);
					prevComponent = null;

					if (e1.getID() == MouseEvent.MOUSE_EXITED) {
						e1.consume();
					}
				}

				// This means mouseExited prevComponent and mouseEntered comp
				else if (prevComponent != comp) {
					MouseEvent e2 =
						new MouseEvent(
							prevComponent,
							MouseEvent.MOUSE_EXITED,
							e1.getWhen(),
							0,
							(int) prevPoint.getX() - (int) prevOff.getX(),
							(int) prevPoint.getY() - (int) prevOff.getY(),
							e1.getClickCount(),
                                                               e1.isPopupTrigger(),
                                                               e1.getButton());

					prevComponent.dispatchEvent(e2);
					e2 =
						new MouseEvent(
							comp,
							MouseEvent.MOUSE_ENTERED,
							e1.getWhen(),
							0,
							(int) prevPoint.getX() - offX,
							(int) prevPoint.getY() - offY,
							e1.getClickCount(),
                                                               e1.isPopupTrigger(),
                                                               e1.getButton());

					comp.dispatchEvent(e2);
				}
			}
			else {
				// This means mouseEntered
				if (comp != null) {
					MouseEvent e2 =
						new MouseEvent(
							comp,
							MouseEvent.MOUSE_ENTERED,
							e1.getWhen(),
							0,
							(int) prevPoint.getX() - offX,
							(int) prevPoint.getY() - offY,
							e1.getClickCount(),
                                                               e1.isPopupTrigger(),
                                                               e1.getButton());

					comp.dispatchEvent(e2);
				}
			}

			// We have to manager our own Cursors since this is normally
			// done on the native side
			if (comp != cursorComponent) {
				if (comp != null) {
					cursorComponent = comp;
					setCursor(comp.getCursor(), false);
				}
				else {
					cursorComponent = null;
					resetCursor();
				}
			}

			// Set the previous variables for next time
			prevComponent = comp;

			if (comp != null) {
				prevPoint = pt;
				prevOff = new Point2D.Double(offX, offY);
			}
		}
	}
	
	/**
	 * This class should not be instantiated, though all the public
	 * methods of javax.swing.RepaintManager may still be called and
	 * perform in the expected manner.
	 *
	 * LockingRepaintManager is an extension of RepaintManager that traps
	 * those repaints called by the Swing components that have been added
	 * to the content pane and passes these repaints to the
	 * ScaledJComponent rather than up the component hierarchy as
	 * usually happens.
	 *
	 * LockingRepaintManager keeps a list of components that are painting.  This
	 * disables repaint until the component has finished painting.  This is
	 * to address a problem introduced by Swing's CellRendererPane which is
	 * itself a work-around.  The problem is that JTable's, JTree's, and
	 * JList's cell renderers need to be validated before repaint.  Since
	 * we have to repaint the entire Swing component hierarchy (in the case
	 * of a Swing component group used as a Jazz visual component).  This
	 * causes an infinite loop.  So we introduce the restriction that no
	 * repaints can be triggered by a call to paint.
	 */
	protected class LockingRepaintManager extends RepaintManager {
		// The components that are currently painting
		// This needs to be a vector for thread safety
		Vector paintingComponents = new Vector();

            private class ContentPaneRepainter implements java.lang.Runnable {
                private int repaintX, repaintY, w, h;
                private ScaledJComponent comp;
                public ContentPaneRepainter (ScaledJComponent comp, int repaintX, int repaintY, int w, int h) {
                    this.comp = comp;
                    this.repaintX = repaintX;
                    this.repaintY = repaintY;
                    this.w = w;
                    this.h = h;
                }
                    
                public void run() {
                    comp.repaintContentPane(repaintX,repaintY,w,h);
                }
            }


		/**
		 * Locks repaint for a particular (Swing) component 
		 * @param c The component for which the repaint is to be locked
		 */
		public void lockRepaint(JComponent c) {
			paintingComponents.addElement(c);
		}

		/**
		 * Unlocks repaint for a particular (Swing) component 
		 * @param c The component for which the repaint is to be unlocked
		 */
		public void unlockRepaint(JComponent c) {
			synchronized (paintingComponents) {
				paintingComponents.removeElementAt(paintingComponents.lastIndexOf(c));
			}
		}

		/**
		 * Returns true if repaint is currently locked for a component and
		 * false otherwise
		 * @param c The component for which the repaint status is desired
		 * @return Whether the component is currently painting
		 */
		public boolean isPainting(JComponent c) {
			return paintingComponents.contains(c);
		}

		/**
		 * This is the method "repaint" now calls in the Swing components.
		 * Overridden to capture repaint calls from those Swing components
		 * which are children of the content pane.
		 * @param c Component to be repainted
		 * @param x X coordinate of the dirty region in the component
		 * @param y Y coordinate of the dirty region in the component
		 * @param w Width of the dirty region in the component
		 * @param h Height of the dirty region in the component
		 */
		public synchronized void addDirtyRegion(JComponent c, int x, int y, final int w, final int h) {
			boolean captureRepaint = false;
			ScaledJComponent sPanel = null;
			int captureX = x, captureY = y;

			// We have to check to see if a scaled component is
			// in the components ancestry.  If so,
			// we will want to capture that repaint.  However, we also will
			// need to translate the repaint request since the component may
			// be offset inside another component.
			for (Component comp = c; comp != null && comp.isLightweight() && !captureRepaint; comp = comp.getParent()) {

				if (comp.getParent() != null
					&& comp instanceof ContentPane) {
					captureRepaint = true;
					sPanel = (ScaledJComponent)comp.getParent().getParent();
				}
				else {
					// Adds to the offset since the component is nested
					captureX += comp.getLocation().getX();
					captureY += comp.getLocation().getY();
				}

			}

			// Now we check to see if we should capture the repaint and act
			// accordingly
			if (captureRepaint) {
				if (!isPainting(sPanel)) {
                                    SwingUtilities.invokeLater(new ContentPaneRepainter(sPanel,
                                                                                        captureX,captureY,w,h));
				}
			}
			else {
				super.addDirtyRegion(c, x, y, w, h);
			}
		}
	}

	/**
	 * A simple test of the class
	 */
	public static void main(String[] args) {
		final JFrame f = new JFrame();
		f.getContentPane().setLayout(new BorderLayout());
		final ScaledJComponent sComp = new ScaledJComponent();
		final JColorChooser jcc = new JColorChooser();
		final JButton bSwitch = new JButton("Disable scaling");
		bSwitch.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent ae) {
				if (sComp.getParent() != null) {
					f.getContentPane().remove(sComp);
					f.getContentPane().add(jcc);
					bSwitch.setText("Enable scaling");
				}
				else {
					f.getContentPane().add(sComp);
					sComp.getContentPane().add(jcc);
					bSwitch.setText("Disable scaling");					
				}
			}
		});
		
		f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		sComp.getContentPane().add(jcc);
		f.getContentPane().add(sComp);
		f.getContentPane().add(bSwitch,"South");
		f.setSize(300,300);
		f.setVisible(true);
	}
}
