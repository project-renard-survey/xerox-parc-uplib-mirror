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
 * This code has been derived from Jason Hong's PieMenu widget in Berkeley's Satin
 * system.  See bottom of source code for Berkeley software license.
 */

package com.parc.uplib.readup.widget;

import java.awt.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.io.*;
import java.util.*;
import javax.swing.*;
import javax.swing.event.*;

/**
 * A Pie Menu widget.
 * <P>
 * <IMG SRC="{@docroot}/img/piemenu-1.gif"><BR>
 * <IMG SRC="{@docroot}/img/piemenu-2.gif"><BR>
 *
 * <H2>Introduction</H2>
 * A Pie Menu is a circular menu that lets people choose
 * items by dragging the pointing device in the direction of the menu item.
 * Pie Menus work well with pen devices, and also take advantage of
 * muscle-memory, as it seems that people remember angles better than they
 * remember the position of items in linear lists.
 *
 * <P>
 * See
 * <A HREF="http://www.catalog.com/hopkins/piemenus/PieMenuDescription.html">Don
 * Hopkins' page on Pie Menus</A> for more information.
 *
 * <P>
 * For a short description of how to use this particular Pie Menu
 * implementation, see the
 * <A HREF="http://www.cs.berkeley.edu/~jasonh/download/software/piemenu/">Java PieMenu
 * page</A>.
 *
 * <HR WIDTH=50%>
 *
 * <H2>Application Programming Interface</H2>
 *
 * <P>Here's a short overview of the API. There are a collection of static class
 * methods that let you set global behavior. Some, like
 * {@link #setAllToMouseMode() setAllToMouseMode()} and {@link #setAllDragOpen() setAllDrawOpen()}, deal with the
 * global look and feel of all pie menus.  These kind of class methods are
 * named <CODE>setAllXXX()</CODE>.
 * <P>
 * There are other class methods that let you set the default for all pie menus
 * created <B>after</B> they are set. For example,
 * {@link #setDefaultFillColor(Color) setDefaultFillColor()} lets you set the color of all pie menus
 * created after the method is called. These kind of class methods are named
 * <CODE>setDefaultXXX()</CODE>.
 * <P>
 * There are also instance methods that let you set values for individual
 * instances of pie menus. For example, {@link #setLineColor(Color) setLineColor()} lets you
 * set the color of lines in one instance of a pie menu, without affecting any
 * others.
 * <P>
 * Here's an overview of the <CODE>setAllXXX()</CODE> methods:
 * <UL>
 *    <LI>There are three different pie menu modes that describe how and when
 *        the pie menu will appear. Calling {@link #setAllTapOpen() setAllTapOpen()} makes the
 *        pie menu appear after releasing the activating button, if you haven't
 *        dragged too far since pressing the activating button. Calling
 *        {@link #setAllTapHoldOpen() setAllTapHoldOpen()} makes the pie menu appear after pressing
 *        and holding down the activating button for a set period of time (see
 *        {@link #setAllInitialDelay(long) setAllInitialDelay()} below). Calling
 *        {@link #setAllDragOpen() setAllDragOpen()} makes the pie menu appear by just
 *        pressing the activating button.
 *    <LI>The activating button is the mouse/pen button that opens up the
 *        pie menu. You can specify this in the instance method
 *        {@link #doesActivateMenu(MouseEvent) doesActivateMenu()}. (Technically, this method
 *        should be static, but that would mean you couldn't override it.)
 *    <LI>The method call {@link #setAllAutoOpen(boolean) setAllAutoOpen()} makes pie submenus
 *        automatically open after hovering over one for a set period of time
 *        (see {@link #setAllSubmenuDelay(long) setAllSubmenuDelay()}).
 *    <LI>{@link #setAllRelocateSubmenus(boolean) setAllRelocateSubmenus()} sets whether pie menus will
 *        appear at the current location of the cursor always. By default, this
 *        is true. Turning this off causes the submenus to appear in fixed
 *        locations.
 *    <LI>{@link #setAllInitialDelay(long) setAllInitialDelay()} sets the initial delay before the
 *        pie menu appears.
 *    <LI>{@link #setAllSubmenuDelay(long) setAllSubmenuDelay()} sets the delay for submenus before
 *        they appear.
 *    <LI>{@link #setAllClipping(boolean) setAllClipping()} sets whether pie menus are clipped
 *        correctly. Currently, for performance reasons, this is not done. This
 *        means you can get text crossing from one pie slice to another.
 * </UL>
 *
 * <P>
 * <H2>Code Example</H2>
 * To add items to the PieMenu, just use the various <CODE>add()</CODE>
 * methods. You'll need to add an ActionListener on each of the items you add,
 * which will be called when the menu item is activated. For example:
 * <PRE>
 *    PieMenu pieMain = new PieMenu();
 *    PieMenu pieFile = new PieMenu("File");
 *
 *    pieMain.add(pieFile);       // add a submenu
 *    pieMain.add("Edit").addActionListener(new PieSliceListener());
 *    pieMain.add("View").addActionListener(new PieSliceListener());
 *    pieMain.add("Help").addActionListener(new PieSliceListener());
 *
 *    pieFile.add("Open").addActionListener(new PieSliceListener());
 *    ...
 *
 *    class PieSliceListener
 *       implements ActionListener {
 *
 *       public actionPerformed(ActionEvent evt) {
 *          System.out.println("Activating " + evt.getActionCommand());
 *       } // of actionPerformed
 *
 *    } // of PieSliceListener
 * </PRE>
 * Of course, you'd probably have different ActionListeners instead of just
 * going to one.
 *
 * <P>
 * To add this pie menu to a component, just do:
 * <PRE>
 *    PieMenu pm = new PieMenu();
 *    JComponent c = new JPanel();
 *    pm.addPieMenuTo(c);
 * </PRE>
 * Currently, the PieMenu only works with JComponents.
 *
 * <P>
 * <HR WIDTH=50%>
 * <P>
 * <H2>Other Notes</H2>
 * Pie Menus are a more sophisticated form of {@link javax.swing.JPopupMenu JPopupMenu}.
 * Although most of the interface is implemented, this PieMenu isn't a full
 * JPopupMenu yet (but that's on the list for things to do later on).
 *
 * <P>
 * Please note that this Pie Menu widget does <B>not</B> clip to the circular
 * boundaries of the Pie Menu for performance reasons. It does, however, clip
 * to the rectangular bounds of the Pie Menu. The system response time
 * felt a little sluggish, so I turned it rectangular clipping by default.
 *
 * <P>
 * Lastly, this version of Pie Menu only works with Java Swing. It does not
 * currently work with AWT heavyweight widgets.
 *
 * <P>
 * <HR WIDTH=50%>
 * <P>
 * <H2>Known Problems</H2>
 * Don't do something like this:
 * <PRE>
 * PieMenu   pieMain = new PieMenu();
 * JMenuItem item    = new JMenuItem("File");
 *
 * pieMain.add(item);
 * item.setEnabled(false);
 * </PRE>
 *
 * Although this <EM>should</EM> work, it doesn't, due to a quirk in this
 * implementation. However, you can do the following instead:
 *
 * <PRE>
 * PieMenu   pieMain = new PieMenu();
 * JMenuItem item    = pieMain.add("File");
 * item.setEnabled(false);
 * </PRE>
 *
 * <P>
 * <HR WIDTH=50%>
 * <P>
 * <H2>Sample Code</H2>
 * Here is what some sample code would look like. It creates a hierarchy
 * of pie menus. The parts that have action listeners would actually work. The
 * parts that don't would be displayed but would take no action.
 *
 * <PRE>
 * private void setupPieMenu() {
 *    PieMenu pieMain      = new PieMenu();
 *    PieMenu pieFile      = new PieMenu("File");
 *    PieMenu pieEdit      = new PieMenu("Edit");
 *    PieMenu pieHelp      = new PieMenu("Help");
 *    PieMenu pieTransform = new PieMenu("Rotate /\nZoom");
 *
 *    //// 1. Pie menu layout.
 *    pieMain.add(pieFile);
 *       pieFile.add("Open\nImages").addActionListener(new OpenImageListener());
 *       pieFile.add("Open\nPoster");
 *       pieFile.add("Save\nPoster");
 *    pieMain.add("Undo");
 *    pieMain.add(pieHelp);
 *       pieHelp.add("About");
 *       pieHelp.add("Search");
 *       pieHelp.add(pieDebug);
 *       pieHelp.add(pieTransform);
 *          pieTransform.add("Zoom\nIn");
 *          pieTransform.add("Rotate\nLeft");
 *          pieTransform.add("Zoom\nOut");
 *          pieTransform.add("Rotate\nRight");
 *    pieMain.add("Color").addActionListener(new ColorListener());
 *    pieMain.add("Redo").addActionListener(new RedoListener());
 *    pieMain.add(pieEdit);
 *       pieEdit.add("Cut").addActionListener(new CutListener());
 *       pieEdit.add("Copy").addActionListener(new CopyListener());
 *       pieEdit.add("Paste").addActionListener(new PasteListener());
 *       pieEdit.add("Delete").addActionListener(new DeleteListener());
 *
 *    //// 2. Other pie menu initializations.
 *    pieMain.addPieMenuTo(this);
 *    pieMain.setLineNorth(true);
 *    pieMain.setAllTapHoldOpen();
 * } // of setupPieMenu
 * </PRE>
 *
 *
 * <P>
 * <HR WIDTH=50%>
 *
 * <P>
 * This software is distributed under the
 * <A HREF="http://guir.cs.berkeley.edu/projects/COPYRIGHT.txt">
 * Berkeley Software License</A>.
 *
 * <PRE>
 * Revisions:  - SATIN-v1.0-1.0.0, Mar 16 1999, JH
 *               Created class
 *             - SATIN-v2.1-1.0.1, Aug 11 2000, JH
 *               Touched for SATIN release
 * </PRE>
 *
 * @see     javax.swing.JPopupMenu
 * @author  <A HREF="http://www.cs.berkeley.edu/~jasonh/">Jason Hong</A> (
 *          <A HREF="mailto:jasonh@cs.berkeley.edu">jasonh@cs.berkeley.edu</A> )
 * @since   JDK 1.2
 * @version SATIN-v2.1-1.0.1, Aug 11 2000
 */

// FUNCTIONALITY NOT COMPLETED YET
//    short distance for help, long distances to activate
//    double select - select pie slice, select object
//    implement JMenu / JComponent interface correctly
//    auto-resize / layout based on items within
//    show-me gesture
//    icon draw / layout
//    distance and velocity metrics?
//    pre-select gesture and then gesture
//    darker separation bars to group regions together
//    marking menu options
//    when holding down button, canceling a submenu causes events not to
//       be forwarded to the parent again
//    keyboard input
//    add explicit support for transparent pie menus

public class PieMenu
   extends    JPanel
   implements MenuElement {

   //===========================================================================
   //===   CONSTANTS   =========================================================

   static final long serialVersionUID = 9008472948612331581L;

   //===   CONSTANTS   =========================================================
   //===========================================================================



   //===========================================================================
   //===   CONSTANTS   =========================================================

   /** Where the first pie slice is rendered. Currently North.  */
   public static final double DEFAULT_START = Math.PI / 2;

   /** Default radius size for the pie menu, currently 100.  */
   public static final int DEFAULT_BIG_RADIUS = 100;

   /** The radius of the small inner circle, currently 20.  */
   public static final int DEFAULT_SMALL_RADIUS = 20;

   /**
    * The default delay (msec) before pie menus initially pop up, currently
    * 200ms. Don't make this too small, or you'll get strange errors.
    */
   public static final long DEFAULT_INITIAL_DELAY = 200;

   /** The default delay (msec) before pie submenus pop up, currently 500ms.  */
   public static final long DEFAULT_SUBMENU_DELAY = 500;

   /** Default value for auto-open is false.  */
   public static final boolean DEFAULT_AUTO_OPEN = false;

   /** Default value for clipping is false.  */
   public static final boolean DEFAULT_CLIP_FLAG = false;

   /**
    * The default scaling factor for where to draw objects.
    * This scaling factor is multiplied with the radius to determine
    * where to draw things. Currently 0.65.
    */
   public static final double DEFAULT_SCALING_FACTOR = 0.65;

   //-----------------------------------------------------------------

   /** The default color of the pie menu, currently light gray.  */
   public static final Color DEFAULT_FILL_COLOR = new Color(204, 204, 204);;

   /** The default color of the lines in the pie menu, currently black.  */
   public static final Color DEFAULT_LINE_COLOR = new java.awt.Color(0,0,0,0.35f);

   /**
    * The default color of the selected item in the pie menu, currently gray.
    */
   public static final Color DEFAULT_SELECTED_COLOR = new Color(167, 167, 167);

   /** The default color of fonts, currently black.  */
   public static final Color DEFAULT_FONT_COLOR = Color.black;

   /** The default font, currently sans serif plain, 15 point.  */
   public static final Font DEFAULT_FONT = new Font("SansSerif", Font.PLAIN, 15);

   /** Default line width for drawing lines in the Pie Menu, currently 0.7.  */
   public static final float DEFAULT_LINE_WIDTH = 0.7f;

   private final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);

   private final static Color DARK_COLOR = new Color(.439f, .475f, .490f);

   private final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);

   //-----------------------------------------------------------------

   private static final int STATE_TAP_OPEN     = 90;
   private static final int STATE_TAPHOLD_OPEN = 91;
   private static final int STATE_DRAG_OPEN    = 92;
   
   private static final int ORIENT_TOP    = 1;
   private static final int ORIENT_TOPRIGHT  = 2;
   private static final int ORIENT_BOTTOM = 3;
   private static final int ORIENT_TOPLEFT   = 4;
   private static final int ORIENT_BOTRIGHT = 5;
   private static final int ORIENT_BOTLEFT = 6;

   //===   CONSTANTS   =========================================================
   //===========================================================================



   //===========================================================================
   //===   CLASS METHODS FOR PIE MENU DEFAULTS   ===============================

   //// State tracking - turns submenus and select on or off globally.
   static boolean enableSubmenus              = true;
   static boolean enableSelect                = true;

   //// Global behavior of all pie menus
   static boolean defaultAutoOpen             = DEFAULT_AUTO_OPEN;
   static int     defaultOpenState            = STATE_TAP_OPEN;
   static boolean defaultRelocateSubmenusFlag = true;
   static long    defaultInitialDelay         = DEFAULT_INITIAL_DELAY;
   static long    defaultSubmenuDelay         = DEFAULT_SUBMENU_DELAY;
   static boolean defaultFlagPenMode          = false;

   //// Appearance defaults
   static Color   defaultFillColor            = DEFAULT_FILL_COLOR;
   static Color   defaultLineColor            = DEFAULT_LINE_COLOR;
   static Color   defaultSelectedColor        = DEFAULT_SELECTED_COLOR;
   static Color   defaultFontColor            = DEFAULT_FONT_COLOR;
   static Font    defaultFont                 = DEFAULT_FONT;
   static float   defaultLineWidth            = DEFAULT_LINE_WIDTH;
   static int     defaultBigRadius            = DEFAULT_BIG_RADIUS;
   static int     defaultSmallRadius          = DEFAULT_SMALL_RADIUS;
   static double  defaultScalingFactor        = DEFAULT_SCALING_FACTOR;
   static boolean defaultClipFlag             = DEFAULT_CLIP_FLAG;
   static boolean defaultFlagLineNorth        = false;
   static Image   defaultSubmenuIcon          = null;

   //===========================================================================

   /**
    * A simple way of turning submenus on and off temporarily.
    */
   private static synchronized void enableSubmenus() {
      enableSubmenus = true;
   } // of method

   /**
    * A simple way of turning submenus on and off temporarily.
    */
   private static synchronized void disableSubmenus() {
      enableSubmenus = false;
   } // of method

   private static synchronized boolean submenusAreEnabled() {
      return (enableSubmenus);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Allows us to turn selection on and off.
    */
   private static synchronized void enableSelect() {
      enableSelect = true;
   } // of method

   private static synchronized void disableSelect() {
      enableSelect = false;
   } // of method

   //-----------------------------------------------------------------

   private static synchronized boolean selectIsEnabled() {
      return (enableSelect);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set whether we can auto-open pie menus or not.
    */
   public static void setAllAutoOpen(boolean flag) {
      defaultAutoOpen = flag;
   } // of method

   /**
    * Check whether we can auto-open pie menus or not.
    */
   public static boolean getAllAutoOpen() {
      return (defaultAutoOpen);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Check if the sequence {button-down, button-up} opens up the pie menu.
    */
   public static boolean isTapOpen() {
      return (defaultOpenState == STATE_TAP_OPEN);
   } // of method

   /**
    * Check if the sequence {button-down, hold without moving} opens up the
    * pie menu.
    */
   public static boolean isTapHoldOpen() {
      return (defaultOpenState == STATE_TAPHOLD_OPEN);
   } // of method

   /**
    * Check if the sequence {button-down} opens up the pie menu.
    */
   public static boolean isDragOpen() {
      return (defaultOpenState == STATE_DRAG_OPEN);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set that the sequence {button-down, button-up} opens up the pie menu.
    */
   public static void setAllTapOpen() {
      defaultOpenState = STATE_TAP_OPEN;
   } // of method

   /**
    * Set that the sequence {button-down, hold without moving} opens up the
    * pie menu.
    */
   public static void setAllTapHoldOpen() {
      defaultOpenState = STATE_TAPHOLD_OPEN;
      setAllInitialDelay(2*DEFAULT_INITIAL_DELAY);
   } // of method

   /**
    * Set that the sequence {button-down} opens up the pie menu.
    */
   public static void setAllDragOpen() {
      defaultOpenState = STATE_DRAG_OPEN;
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default for whether or not pie menus should appear wherever the
    * cursor happens to be, or if it should appear in a standardized location.
    * This is a global behavior for all pie menus.
    */
   public static void setAllRelocateSubmenus(boolean flag) {
      defaultRelocateSubmenusFlag = flag;
   } // of method

   //-----------------------------------------------------------------

   /**
    * Get the default for whether or not pie menus should appear wherever the
    * cursor happens to be, or if it should appear in a standardized location.
    */
   public static boolean getAllRelocateSubmenus() {
      return (defaultRelocateSubmenusFlag);
   } // of method

   /**
    * Switch the individual pie menu so that it is in the correct mode (pen or
    * mouse) if it is not.
    */
   private static void updatePieMenuToCurrentMode(PieMenu pm) {
      updateToPenMode(pm);
      updateToMouseMode(pm);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Convert an individual pie menu to pen mode.
    */
   private static void updateToPenMode(PieMenu pm) {
      if (isAllPenMode() == true && pm.getPenMode() == false) {
         pm.setPenMode();
         setAllTapOpen();
      }
   } // of method

   /**
    * Convert an individual pie menu to mouse mode.
    */
   private static void updateToMouseMode(PieMenu pm) {
      if (isAllMouseMode() == true && pm.getMouseMode() == false) {
         pm.setMouseMode();
         setAllDragOpen();
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set all of the pie menus to be used with pen mode.
    * This is a global behavior for all pie menus.
    */
   public static void setAllToPenMode() {
      setAllTapOpen();
      defaultFlagPenMode = true;
      setAllSubmenuDelay((int) (1.5 * DEFAULT_SUBMENU_DELAY));
   } // of method

   /**
    * Set all of the pie menus to be used with mouse mode.
    * This is a global behavior for all pie menus.
    */
   public static void setAllToMouseMode() {
      setAllDragOpen();
      defaultFlagPenMode = false;
      setAllSubmenuDelay(DEFAULT_SUBMENU_DELAY);
   } // of method

   //-----------------------------------------------------------------

   /**
    * See if all of the pie menus are in pen mode.
    */
   public static boolean isAllPenMode() {
      return (defaultFlagPenMode);
   } // of method

   /**
    * See if all of the pie menus are in mouse mode.
    */
   public static boolean isAllMouseMode() {
      return (!defaultFlagPenMode);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default appearance delay for the initial pie menu.
    * This is a global behavior for all pie menus.
    */
   public static void setAllInitialDelay(long newDelay) {
      defaultInitialDelay = newDelay;
   } // of method

   /**
    * Get the default appearance delay for the initial pie menu.
    */
   public static long getAllInitialDelay() {
      return (defaultInitialDelay);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default appearance delay all pie submenus.
    * This is a global behavior for all pie menus.
    */
   public static void setAllSubmenuDelay(long newDelay) {
      defaultSubmenuDelay = newDelay;
   } // of method

   /**
    * Get the default appearance delay for all pie submenus.
    */
   public static long getAllSubmenuDelay() {
      return (defaultSubmenuDelay);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default for whether or not pie menus should be clipped to
    * circular bounds for all new pie menus created.
    * Clipping ensures that images and text are drawn entirely within the Pie
    * Menu, but at the cost of performance. The Pie Menu feels a little
    * sluggish when clipping is turned on. By default, it is off.
    */
   public static void setAllClipping(boolean flag) {
      defaultClipFlag = flag;
   } // of method

   /**
    * Get the default for whether or not pie menus should be clipped to
    * circular bounds for all new pie menus created.
    */
   public static boolean getAllClipping() {
      return (defaultClipFlag);
   } // of method

   //-----------------------------------------------------------------




   //-----------------------------------------------------------------

   /**
    * Set what the default image should be for submenus created after this
    * value is set.
    */
   public static void setDefaultSubmenuIcon(Image newImage) {
      defaultSubmenuIcon = newImage;
   } // of method

   /**
    * Get what the default image should be for submenus.
    */
   public static Image getDefaultSubmenuIcon() {
      return (defaultSubmenuIcon);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default fill color for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultFillColor(Color newColor) {
      defaultFillColor = newColor;
   } // of method

   /**
    * Get the default fill color for all new pie menus created.
    */
   public static Color getDefaultFillColor() {
      return (defaultFillColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default line color for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultLineColor(Color newColor) {
      defaultLineColor = newColor;
   } // of method

   /**
    * Get the default line color for all new pie menus created.
    */
   public static Color getDefaultLineColor() {
      return (defaultLineColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default selected color for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultSelectedColor(Color newColor) {
      defaultSelectedColor = newColor;
   } // of method

   /**
    * Get the default selected color for all new pie menus created.
    */
   public static Color getDefaultSelectedColor() {
      return (defaultSelectedColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default font color for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultFontColor(Color newColor) {
      defaultFontColor = newColor;
   } // of method

   /**
    * Get the default font color for all new pie menus created.
    */
   public static Color getDefaultFontColor() {
      return (defaultFontColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default font for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultFont(Font newFont) {
      defaultFont = newFont;
   } // of method

   /**
    * Get the default font for all new pie menus created.
    */
   public static Font getDefaultFont() {
      return (defaultFont);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default line width for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultLineWidth(float newLineWidth) {
      defaultLineWidth = newLineWidth;
   } // of method

   /**
    * Get the default line width for all new pie menus created.
    */
   public static float getDefaultLineWidth() {
      return (defaultLineWidth);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default radius for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultBigRadius(int newRadius) {
      defaultBigRadius = newRadius;
   } // of method

   /**
    * Get the default radius for all new pie menus created.
    */
   public static int getDefaultBigRadius() {
      return (defaultBigRadius);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default radius of the inner circle for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultSmallRadius(int newRadius) {
      defaultSmallRadius = newRadius;
   } // of method

   /**
    * Get the default radius of the inner circle for all new pie menus created.
    */
   public static int getDefaultSmallRadius() {
      return (defaultSmallRadius);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default scaling factor for all new pie menus created
    * after this value is set.
    */
   public static void setDefaultScalingFactor(double newScalingFactor) {
      defaultScalingFactor = newScalingFactor;
   } // of method

   /**
    * Get the default scaling factor for all new pie menus created.
    */
   public static double getDefaultScalingFactor() {
      return (defaultScalingFactor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the default for whether or not the first line drawn should be north
    * or if the first pie slice should be drawn north. Only takes effect
    * for new pie menus created after this value is set.
    */
   public static void setDefaultLineNorth(boolean flag) {
      defaultFlagLineNorth = flag;
   } // of method

   /**
    * Get the default for whether or not the first line drawn should be north
    * or if the first pie slice should be drawn north.
    */
   public static boolean getDefaultLineNorth() {
      return (defaultFlagLineNorth);
   } // of method

   //===   CLASS METHODS FOR PIE MENU DEFAULTS   ===============================
   //===========================================================================



   //===========================================================================
   //===   JMENUITEMWRAPPER INNER CLASS   ======================================

   /**
    * I need a way of calling fireActionPerformed() in JMenuItem, but it's
    * protected. This is really stupid, but it works.
    */
   final class JMenuItemWrapper
      extends JMenuItem {

      //------------------------------------------------------------------

      public JMenuItemWrapper() {
         super();
      } // of constructor

      //------------------------------------------------------------------

      public JMenuItemWrapper(Icon icon) {
         super(icon);
      } // of constructor

      //------------------------------------------------------------------

      public JMenuItemWrapper(String text) {
         super(text);
      } // of constructor

      //------------------------------------------------------------------

      public JMenuItemWrapper(String text, Icon icon) {
         super(text, icon);
      } // of constructor

      //------------------------------------------------------------------

      public JMenuItemWrapper(String text, int mnemonic) {
         super(text, mnemonic);
      } // of constructor

      //------------------------------------------------------------------

      public void fireActionPerformed(ActionEvent evt) {
         super.fireActionPerformed(evt);
      } // of fireActionPerformed

      //------------------------------------------------------------------

   } // of inner class JMenuItemWrapper

   //===   JMENUITEMWRAPPER INNER CLASS   ======================================
   //===========================================================================



   //===========================================================================
   //===   BLINK TIMER AND ACTIONLISTENER INNER CLASS   ========================

   //// Blink-timer shared variables
   Color               tmpFillColor;
   Color               tmpSelectedColor;
   boolean             flagDone      = true;
   int                 count         = 0;
   BlinkActionListener blinkListener = new BlinkActionListener();

   final class BlinkTimer
      extends javax.swing.Timer {

      //------------------------------------------------------------------

      public BlinkTimer() {
         super(20, null);
         addActionListener(blinkListener);
         setInitialDelay(0);
         tmpFillColor     = getFillColor();
         tmpSelectedColor = getSelectedColor();
      } // of constructor

      //------------------------------------------------------------------

      public void start() {
         flagDone = false;
         count = 0;
         disableSelect();
         super.start();
      } // of start

      //------------------------------------------------------------------

      public void stop() {
         selectedColor = tmpSelectedColor;
         PieMenu.this.repaint();
         super.stop();
         flagDone = true;
      } // of stop

      //------------------------------------------------------------------

      public boolean isDone() {
         return (flagDone);
      } // of isDone

   } // of inner class BlinkTimer

   //===========================================================================

   final class BlinkActionListener
      implements ActionListener, Serializable {

      public void actionPerformed(ActionEvent evt) {
         if (count > 2) {
            timer.stop();
            return;
         }

         if (getSelectedColor() == tmpFillColor) {
            selectedColor = tmpSelectedColor;
         }
         else {
            selectedColor = tmpFillColor;
         }
         PieMenu.this.repaint();
         count++;
      } // of actionPerformed

      //------------------------------------------------------------------

   } // of inner class BlinkTimer

   //===   BLINK TIMER AND ACTIONLISTENER INNER CLASS   ========================
   //===========================================================================



   //===========================================================================
   //===   POPUPMENULISTENER INNER CLASS   =====================================

   /**
    * Used to listen to any submenus we have opened.
    */
   final class PopupMenuCallback
      implements PopupMenuListener, Serializable {

      //------------------------------------------------------------------

      public void popupMenuCanceled(PopupMenuEvent evt) {
      } // of popupMenuCanceled

      //------------------------------------------------------------------

      public void popupMenuWillBecomeInvisible(PopupMenuEvent evt) {
         if (submenu != null && submenu.isShowing()) {
            submenu       = null;
            submenuThread = null;
         }
         flagJustClosedSubmenu = true;
      } // of popupMenuWillBecomeInvisible

      //------------------------------------------------------------------

      public void popupMenuWillBecomeVisible(PopupMenuEvent evt) {
         timer.stop();
      } // of popupMenuWillBecomeVisible

      //------------------------------------------------------------------

   } // of PopupMenuCallback

   //===   POPUPMENULISTENER INNER CLASS   =====================================
   //===========================================================================



   //===========================================================================
   //===   DELAYTHREAD INNER CLASS   ===========================================

   /**
    * A thread that waits around for a while before executing an action.
    * Didn't use invokeAndWait() or invokeLater() because I wanted a mechanism
    * for aborting too.
    */
   abstract class DelayThread extends Thread {

      long    ms;                   // how long to sleep before doing something
      boolean flagContinue = true;  // do the command or not?
      boolean flagDone     = false; // done or not?

      //------------------------------------------------------------------

      public DelayThread(long ms) {
         this.ms = ms;
         setPriority(Thread.MIN_PRIORITY);
      } // of constructor

      //------------------------------------------------------------------

      /**
       * Don't execute the command.
       */
      public void abort() {
         flagContinue = false;
      } // of abort

      //------------------------------------------------------------------

      public boolean isDone() {
         return (flagDone);
      } // of isDone

      //------------------------------------------------------------------

      public final void spin(long ms) {
         //// 1. Sleep for a short while.
         try {
            yield();
            sleep(ms);
            yield();
         }
         catch (Exception e) {
            //// ignore
         }
      } // of sleep

      //------------------------------------------------------------------

      public final void run() {
         //// 1. Sleep for a short while.
         spin(ms);

         //// 2. Now do something interesting.
         if (flagContinue == true) {
            doit();
         }
         flagDone = true;
         if (flagContinue == false) {
            undo();
         }
      } // of run

      //------------------------------------------------------------------

      /**
       * Override this method to do something interesting.
       */
      abstract public void doit();

      //------------------------------------------------------------------

      public void undo() {
      } // of undo

      //------------------------------------------------------------------

   } // of DelayThread

   //===========================================================================

   /**
    * A thread that displays a pie menu or submenu after a delay.
    */
   final class ShowThread extends DelayThread {

      Component c;       // component to display pie menu in
      int       x;       // x-coordinate in c's space to display in
      int       y;       // y-coordinate in c's space to display in

      public ShowThread(Component c, int x, int y) {
         this(c, x, y, getAllInitialDelay());
      } // of constructor

      //------------------------------------------------------------------

      public ShowThread(Component c, int x, int y, long ms) {
         super(ms);
         this.c = c;
         this.x = x;
         this.y = y;
      } // of constructor

      //------------------------------------------------------------------

      /**
       * Update where the pie submenu will be displayed.
       */
      public void setShowLocation(int x, int y) {
         this.x = x;
         this.y = y;
      } // of setShowLocation

      //------------------------------------------------------------------

      public void doit() {
         while (!timer.isDone()) {
            spin(50);
         }

         //// 1. First show the pie menu.
         showInternal(c, x, y);

         //// 2. Forward the last event to the pie menu. This lets us do
         ////    actions on the pie menu before it actually appears on screen.
         forwardLastEvent();
      } // of doit

      //------------------------------------------------------------------

   } // of inner class ShowThread

   //===========================================================================

   /**
    * Thread that cancels all pie menus.
    */
   final class CancelPieMenuThread extends DelayThread {

      JMenuItemWrapper item;
      ActionEvent      evt;

      //------------------------------------------------------------------

      public CancelPieMenuThread(long ms) {
         super(ms);
      } // of constructor

      //------------------------------------------------------------------

      public CancelPieMenuThread(long ms, JMenuItemWrapper item,
            ActionEvent evt) {
         super(ms);
         this.item = item;
         this.evt  = evt;
      } // of constructor

      //------------------------------------------------------------------

      public void doit() {
         while (!timer.isDone()) {
            spin(50);
         }
         firePopupMenuWillBecomeInvisible();
         if (item != null && item.isEnabled() == true) {
            hideAll();
         }
         else {
            firePopupMenuCanceled();
         }
         if (item != null && item.isEnabled() == true) {
            item.fireActionPerformed(evt);
         }
      } // of doit

      //------------------------------------------------------------------

   } // of inner class CancelPieMenuThread

   //===========================================================================

   final class ShowSubmenuThread extends DelayThread {

      PieMenu pm;   // the submenu to show
      int     x;    // x-coordinate to show at, in absolute coordinates
      int     y;    // y-coordinate to show at, in absolute coordinates

      //------------------------------------------------------------------

      /**
       * @param pm is the pie menu to show.
       * @param x  is the x-coordinate to show at, in absolute coordinates.
       * @param y  is the y-coordinate to show at, in absolute coordinates.
       * @param ms is the amount of time (msec) to delay.
       */
      public ShowSubmenuThread(PieMenu pm, int x, int y) {
         super(getAllSubmenuDelay());
         this.pm = pm;
         this.x  = x;
         this.y  = y;
      } // of constructor

      //------------------------------------------------------------------

      /**
       * @param pm  is the pie menu to show.
       * @param pos is the pie slice position to show at.
       * @param ms  is the amount of time (msec) to delay.
       */
      public ShowSubmenuThread(PieMenu pm, int pos) {
         super(getAllSubmenuDelay());
         this.pm = pm;

         Point  pt         = new Point();
         Point  ptPie      = getLocation();
         double current    = getStartRadian();
         double stepRadian = 2*Math.PI / getItemCount();
         double angle      = current + (0.5 + pos)*stepRadian;

         polarToCartesian(radius, radius, angle, radius * scalingFactor, pt);
         this.x = ptPie.x + pt.x;
         this.y = ptPie.y + pt.y;

      } // of constructor

      //------------------------------------------------------------------

      public void abort() {
         super.abort();
         this.pm.setVisible(false);
      } // of abort

      //------------------------------------------------------------------

      /**
       * Update where the pie submenu will be displayed.
       */
      public void setShowLocation(int x, int y) {
         this.x = x;
         this.y = y;
      } // of setShowLocation

      //------------------------------------------------------------------

      public void doit() {
         if (submenu == null) {
            return;
         }

         while (!timer.isDone()) {
            spin(50);
         }
         // System.out.println("showing...");

         //// 1.1. Show the pie submenu.
         pm.showInternal(getComponent(), x, y);

         //// 1.2. Cannot hide the parent pie menu, or events will
         ////      not get forwarded correctly.
         // PieMenu.this.hideInternal();

         //// 2. Add a popupmenu listener to the submenu.
         pm.addPopupMenuListener(new PopupMenuCallback());

         //// 3. Forward the last event to the pie menu. This lets us do
         ////    actions on the pie menu before it actually appears on screen.
         // forwardLastEvent();

         //// 4. Since events are forwarded to the submenu, we have
         ////    no longer dragged in the current pie menu.
         flagDraggedInPieMenu = false;
      } // of doit

      //------------------------------------------------------------------

      public void undo() {
         if (flagContinue == false) {
            pm.setVisible(false);
         }
      } // of undo

      //------------------------------------------------------------------

      } // of inner class ShowSubmenuThread

   //===   DELAYTHREAD INNER CLASS   ===========================================
   //===========================================================================



   //===========================================================================
   //===   COMPONENT LISTENER INNER CLASS   ====================================

   /**
    * A mouse listener on one of the top-level panes, allowing us to
    * listen on mouse events and popup the menu when appropriate.
    */
   final class ItemListener
      implements MouseListener,
                 MouseMotionListener,
                 ComponentListener,
                 Serializable {

      //------------------------------------------------------------------

      int  pressedX = 0;    // (x,y) of where we pressed the mouse
      int  pressedY = 0;
      int  distX    = 0;    // (x,y) farthest dragged from pressed (x,y)
      int  distY    = 0;

      //------------------------------------------------------------------

      private boolean hasTravelledTooFar() {
         if (distX*distX + distY*distY > getSmallRadius()*getSmallRadius()) {
            return (true);
         }
         return (false);
      } // of hasTravelledTooFar

      //------------------------------------------------------------------

      /**
       * Calculate the farthest we have been since we pressed the mouse
       * button down. This is done since we don't want to show the pie menu if
       * the right mouse button was dragged around a lot.
       */
      private void updateDistances(MouseEvent evt) {
         int dx = Math.abs(pressedX - evt.getX());
         int dy = Math.abs(pressedY - evt.getY());

         if (dx > distX) {
            distX = dx;
         }

         if (dy > distY) {
            distY = dy;
         }
      } // of updateDistances

      //------------------------------------------------------------------

      /**
       * This is the mouse listener that listens on the attached component
       * to pop up a pie menu after a period of time.
       */
      public void mousePressed(MouseEvent evt) {
         clearLastMouseEvent();
         Dimension dim = Toolkit.getDefaultToolkit().getScreenSize();

         //// 1. If we hit the popup trigger, show the menu.
         if (doesActivateMenu(evt)) {
            pressedX       = evt.getX();
            pressedY       = evt.getY(); /*
            if (defaultBigRadius + pressedX > dim.width) {
                pressedX = dim.width - defaultBigRadius;
            }
            if (pressedX - defaultBigRadius < 0) {
                pressedX = defaultBigRadius;
            }
            if (defaultBigRadius + pressedY > dim.height) {
                pressedY = dim.height - defaultBigRadius;
            } */
            distX          = 0;
            distY          = 0;
            flagJustOpened = false;

            //// 1.1. Show the menu if we can drag-open the pie menu.
            if (isShowing() == false &&
                (isDragOpen() == true || isTapHoldOpen() == true)) {
               show(evt.getComponent(), evt.getX(), evt.getY());
            }
         }
         //// 2. Otherwise set the pie menu to the close option.
         else {
            getActiveMenu().setSelectedItem(-1);
         }
      } // of mousePressed

      //------------------------------------------------------------------

      /**
       * Forward the event to the pie menu listener if we are dragging inside
       * of the circle. This is necessary because all of the mouse events will
       * still be (correctly) dispatched to here instead of to the PieMenu.
       */
      public void mouseDragged(MouseEvent evt) {
         setLastMouseEvent(evt);

         //// 1.1. Basically ignore the event if we are invisible. Just update
         ////      where we will show the piemenu. Since the pie menu is not
         ////      showing, don't add its coordinates to the update location.
         if (submenu == null && isShowing() == false) {
            updateShowLocation(evt.getX(), evt.getY());
            updateDistances(evt);

            //// 1.2. Update the distance, since we only want to open the
            ////      pie menu in tap-mode if we have stayed near where we
            ////      started.
            if (isTapOpen() == true || isTapHoldOpen() == true) {
               if (hasTravelledTooFar() == true) {
                  if (showThread != null) {
                     showThread.abort();
                     showThread = null;
                  }
               }
               else {
                  evt.consume();
               }
            }

            return;
         }

         //// 2. Find the active submenu and dispatch to it.
         PieMenuHandler redispatcher;
         evt          = convertMouseEventSpace(evt);
         redispatcher = getDispatcher();
         redispatcher.handleMouseDragged(evt);

      } // of mouseDragged

      //------------------------------------------------------------------

      /**
       * Forward to the other listener. See documentation above for
       * mouseDragged().
       */
      public void mouseReleased(MouseEvent evt) {
         setLastMouseEvent(evt);

         //// 1. If we are invisible, see if we have the equivalent of a
         ////    mouseClicked() event. The reason I didn't just implement
         ////    mouseClicked() is because when people are using pens,
         ////    sometimes you drag it when trying to click. That's the
         ////    way pens are.
         if (submenu == null && isShowing() == false) {
            if (doesActivateMenu(evt) &&
                (isTapOpen() == true || isTapHoldOpen() == true)) {
               if (isTapOpen() == true && hasTravelledTooFar() == false) {
                  clearLastMouseEvent();
                  show(evt.getComponent(), evt.getX(), evt.getY());
               }
               else if (isTapHoldOpen() == true) {
                  if (showThread != null) {
                     showThread.abort();
                     showThread = null;
                  }
               }
            }
            return;
         }

         //// 2. We don't want pie menus to close immediately if we are
         ////    still holding the button down.
         if (isShowing() == true && isTapHoldOpen() == true && flagJustOpened) {
            evt.consume();
            return;
         }

         //// 3. Find the active submenu and dispatch to it.
         PieMenuHandler redispatcher;
         evt           = convertMouseEventSpace(evt);
         redispatcher  = getDispatcher();
         redispatcher.handleMouseReleased(evt);
      } // of mouseReleased

      //------------------------------------------------------------------

      public void mouseClicked(MouseEvent evt) {
         setLastMouseEvent(evt);
      } // of mouseClicked

      //------------------------------------------------------------------

      public void mouseMoved(MouseEvent evt) {
         //// 1. Just forward the event to drag.
         mouseDragged(evt);
      } // of mouseMoved

      //------------------------------------------------------------------

      public void mouseEntered(MouseEvent evt) { }
      public void mouseExited(MouseEvent evt)  { }

      //------------------------------------------------------------------

      public void componentHidden(ComponentEvent evt) {}
      public void componentMoved(ComponentEvent evt) {}
      public void componentShown(ComponentEvent evt) {}

      //------------------------------------------------------------------

      /**
       * Just so layout will not be messed up on resize.
       */
      public void componentResized(ComponentEvent evt) {
         if (isShowing() == true) {
            hideAll();
         }
      } // of componentResized

   } // of ItemListener

   //===   COMPONENT LISTENER INNER CLASS   ====================================
   //===========================================================================



   //===========================================================================
   //===   PIE MENU LISTENER INNER CLASS   =====================================

   /**
    * Listens to mouse events, forwarding them to the correct submenu's handler.
    */
   final class PieMenuListener
      implements MouseListener, MouseMotionListener, Serializable {

      //------------------------------------------------------------------

      public final void mouseClicked(MouseEvent evt) { }
      public final void mouseExited(MouseEvent evt)  { }

      //------------------------------------------------------------------

      public final void mouseEntered(MouseEvent evt) {
         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();

         //// 1. Since we entered the pie menu, it's okay to forward
         ////    events to the pie slice that just had it's submenu closed.
         ////
         ////    Actually, it's not since you get a mouseEntered() event
         ////    if you closed a pie submenu and the cursor happens to
         ////    be over the pie menu. Just do nothing.

         //      flagJustClosedSubmenu = false;

      } // of mouseEntered

      //------------------------------------------------------------------


      /**
       * This is the mouse listener that listens on the pie menu
       * when it is already popped up.
       */
      public final void mousePressed(MouseEvent evt) {
         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();
         flagJustOpened = false;

         //// 1. Save the last event for redispatching purposes.
         ////    Save here instead of in the mouse listener because
         ////    the mouse listener may be bypassed.
         setLastMouseEvent(evt);

         //// 2. Translate the coordinates and dispatch to the right submenu.
         PieMenuHandler redispatcher;
         evt          = convertMouseEventSpace(evt);
         redispatcher = getDispatcher();
         redispatcher.handleMousePressed(evt);
      } // of mousePressed

      //------------------------------------------------------------------

      public final void mouseReleased(MouseEvent evt) {
         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();

         //// 1. Save the last event for redispatching purposes.
         ////    Save here instead of in the mouse listener because
         ////    the mouse listener may be bypassed.
         setLastMouseEvent(evt);

         //// 2. Translate the coordinates and dispatch to the right submenu.
         PieMenuHandler redispatcher;
         evt          = convertMouseEventSpace(evt);
         redispatcher = getDispatcher();
         redispatcher.handleMouseReleased(evt);
      } // of mouseReleased

      //------------------------------------------------------------------

      public final void mouseDragged(MouseEvent evt) {
         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();

         //// 1. Save the last event for redispatching purposes.
         ////    Save here instead of in the mouse listener because
         ////    the mouse listener may be bypassed.
         setLastMouseEvent(evt);

         //// 2. Translate the coordinates and dispatch to the right submenu.
         PieMenuHandler redispatcher;
         evt          = convertMouseEventSpace(evt);
         redispatcher = getDispatcher();
         redispatcher.handleMouseDragged(evt);
      } // of mouseDragged

      //------------------------------------------------------------------

      public final void mouseMoved(MouseEvent evt) {
         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();

         //// 1. Save the last event for redispatching purposes.
         ////    Save here instead of in the mouse listener because
         ////    the mouse listener may be bypassed.
         setLastMouseEvent(evt);

         //// 2. Translate the coordinates and dispatch to the right submenu.
         PieMenuHandler redispatcher;
         evt          = convertMouseEventSpace(evt);
         redispatcher = getDispatcher();
         redispatcher.handleMouseMoved(evt);

      } // of mouseMoved

   } // of inner class PieMenuListener

   //===   PIE MENU LISTENER INNER CLASS   =====================================
   //===========================================================================



   //===========================================================================
   //===   PIE MENU HANDLER INNER CLASS   ======================================

   /**
    * Responsible for handling the mouse events. The reason that we do not
    * handle the mouse events directly in PieMenuListener above is that
    * PieMenuListener is also responsible for dispatching to the correct
    * Pie submenu.
    */
   final class PieMenuHandler
      implements Serializable {

      //------------------------------------------------------------------

      /**
       * Check whether any button is down.
       */
      private boolean mouseButtonIsDown(MouseEvent evt) {
         return (SwingUtilities.isLeftMouseButton(evt)   ||
                 SwingUtilities.isMiddleMouseButton(evt) ||
                 SwingUtilities.isRightMouseButton(evt));
      } // of mouseButtonIsDown

      //------------------------------------------------------------------

      private void handleMousePressed(MouseEvent evt) {
         // System.out.println("handleMousePressed");

         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();
         flagJustOpened = false;

         //// 1. Highlight the menu item selected.
         setSelectedItem(getSliceNumber(evt.getX(), evt.getY()));
         // System.out.println("Highlight menu item " +
         //                     getSliceNumber(evt.getX(), evt.getY()));

         //// 2. Figure out if we should show a pie submenu or not.
         ////    If we will, then mark this as a submenu that can
         ////    be aborted.
         if (maybeShowPieSubmenu(evt.getX(), evt.getY()) == true) {
            flagCanAbortSubmenu = true;
         }
      } // of mousePressed

      //------------------------------------------------------------------

      private void handleMouseReleased(MouseEvent evt) {
         // System.out.println("handleMouseReleased");

         //// 0.1. Consume the event in case other people check this value. Yum!
         evt.consume();

         //// 0.2.
         if (flagJustOpened == true && isTapHoldOpen() == true) {
            flagJustOpened = false;
            return;
         }
         flagJustOpened = false;

         //// 1. See if the event is in us or not. If the event is in the
         ////    pie menu, then just proceed normally. If it is not, then
         ////    we either activate an item (if it is the popup trigger or
         ////    if it was entirely dragged through) or cancel and close
         ////    just this pie menu (if it is not the popup trigger).
         if (!doesActivateMenu(evt) && !flagDraggedInPieMenu &&
             !bigCircle.contains(evt.getX(), evt.getY())) {
            firePopupMenuCanceled();
            setVisible(false);
            return;
         }

         //// 2. Otherwise activate the menu item selected.
         int pos = getSliceNumber(evt.getX(), evt.getY());

         //// 3.1. Close the menu if we are in the small circle.
         if (pos < 0) {
            firePopupMenuCanceled();
            hideDescendants();
            return;
         }
         //// 3.2. See if we are going to open a popup menu or not.
         ////      Either case, always mark this as a submenu that cannot
         ////      be aborted.
         maybeShowPieSubmenu(evt.getX(), evt.getY());
         flagCanAbortSubmenu = false;

         //// 3. Showing a submenu, cannot activate a command, no need
         ////    to continue.
         if (submenu != null) {
            if (submenu.isEnabled() == false) {
               submenu       = null;
               submenuThread = null;
            }
            else {
               timer.start();
            }
            return;
         }

         //// 3.3. If not, activate the selected pie menu item.
         // System.out.println("Activate menu item " + pos);

         //// 4.1. See if the item is enabled or not.
         JMenuItem item = getItem(pos);
         if (item.isEnabled() == false) {
            return;
         }

         //// 4.2. Hide ourself if we are not going to show a pie submenu.
         ////      Be sure to ignore the next click, since mouseClicked()
         ////      events can come after a mouseReleased() event.
         timer.start();
         ActionEvent      fevt =
            new ActionEvent(this, ActionEvent.ACTION_PERFORMED, item.getText());
         new CancelPieMenuThread(300, (JMenuItemWrapper) item, fevt).start();
      } // of mouseReleased

      //------------------------------------------------------------------

      private void handleMouseDragged(MouseEvent evt) {
         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();

         //// 1.1. Figure out if we are dragging in the pie menu or not.
         ////      This allows the left-mouse button to activate items
         ////      if we drag all the way through.
         if (bigCircle.contains(evt.getX(), evt.getY())) {
            flagDraggedInPieMenu = true;
         }
         //// 1.2. If we aren't in the big circle, then see if we ever
         ////      dragged inside the big circle. If we didn't, then
         ////      highlight the close menu portion.
         else {
            if (flagDraggedInPieMenu == false &&
                mouseButtonIsDown(evt) && !doesActivateMenu(evt)) {
               setSelectedItem(-1);
               return;
            }
         }

         //// 2.1. Figure out which menu item to highlight.
         int selectedItem = getSliceNumber(evt.getX(), evt.getY());

         //// 2.2. If we just closed the submenu, then don't accept events.
         ////      We do this because it's too easy to reactivate the menu
         ////      that was just closed.
         if (flagJustClosedSubmenu == true) {
            if (selectedItem == submenuPos) {
               return;
            }
         }

         //// 2.3. Highlight the selected item.
         setSelectedItem(selectedItem);
         // System.out.println("Highlight menu item " +
         //                    getSliceNumber(evt.getX(), evt.getY()));

         //// 3. Exit out if no item selected. This way, we don't try to open
         ////    up the pie menu by accident, since there isn't one at < 0.
         if (selectedItem < 0) {
            return;
         }
         flagJustOpened = false;

         //// 4. Update where the pie submenu will be displayed.
         if (getAllRelocateSubmenus() == true) {
            Point pt    = PieMenu.this.getLocation();
            int   drawX = evt.getX() + pt.x;
            int   drawY = evt.getY() + pt.y;
            updateShowLocation(drawX, drawY);
         }

         //// 5. Figure out if we should auto-open a piemenu or not.
         ////    If we will, then mark this as a submenu that can be aborted.
         if (getAllAutoOpen() &&
             maybeShowPieSubmenu(evt.getX(), evt.getY()) == true) {
            flagCanAbortSubmenu = true;
         }
      } // of handleMouseDragged

      //------------------------------------------------------------------

      private void handleMouseMoved(MouseEvent evt) {
         // System.out.println("handleMouseMoved");
         // System.out.println("mouseMoved " + evt.getX() + " " + evt.getY());

         //// 0. Consume the event in case other people check this value. Yum!
         evt.consume();

         //// 1. Delegate.
         handleMouseDragged(evt);

         //// 2. This is the only difference between the handleMouseMoved()
         ////    and handleMouseDragged(). Moving doesn't count as dragging in
         ////    this case.
         flagDraggedInPieMenu = false;
      } // of handleMouseMoved

      //------------------------------------------------------------------

      /**
       * Show a pie submenu if we are at the coordinates of one.
       *
       * @param  x is the x-coordinate (where 0 is the left of the PieMenu).
       * @param  y is the x-coordinate (where 0 is the top of the PieMenu).
       * @return true if a pie submenu is to appear, false otherwise.
       */
      private boolean maybeShowPieSubmenu(int x, int y) {
         //// 0. If submenus are not enabled, then don't show any submenus.
         if (!submenusAreEnabled()) {
            return (false);
         }

         //// 1.1. If the selected item is also a pie menu, then show it.
         int pos = getSliceNumber(x, y);

         //// 1.2. No pie menu if we are in the small circle.
         if (pos < 0) {
            return (false);
         }

         //// 1.3. This part of the code is a hack because implementing the
         ////      two hundred methods needed for menus is a real pain.
         ////      First, see if we are already showing a pie menu. If so,
         ////      then don't try to show another one.
         if (submenu != null || submenuThread != null) {
            return (false);
         }

         //// 1.4. Retrieve the menu item where the mouse is at.
         Object obj = list.get(pos);
         if (obj instanceof PieMenu) {
            PieMenu pm = (PieMenu) obj;

            //// 1.5. Create a new thread to show the pie menu after a delay.
            if (!pm.isShowing()) {
               Point pt    = PieMenu.this.getLocation();
               int   drawX = x + pt.x;
               int   drawY = y + pt.y;
               Dimension dim = Toolkit.getDefaultToolkit().getScreenSize();
               // Check to see if the submenu is offscreen. If so, adjust it.
               drawX = fixPieLocationX(drawX);
               drawY = fixPieLocationY(drawY);
               //// 1.6. Be sure to abort any other pie submenus, so we don't
               ////      get multiple pie menus from the same level out.
               submenu    = pm;
               submenu.parentMenu = PieMenu.this;
               submenuPos = pos;
               if (submenuThread != null) {
                  submenuThread.abort();
               }

               //// 1.7. If the submenu is disabled then do nothing.
               if (submenu.isEnabled() == false) {
                  return (false);
               }


               //// 1.8. If we can relocate submenus, then render the submenu
               ////      at the last mouse position.
               if (getAllRelocateSubmenus() == true) {
                  submenuThread = new ShowSubmenuThread(pm, drawX, drawY);
               }
               //// 1.9. Otherwise render the submenu at a fixed location.
               else {
                  submenuThread = new ShowSubmenuThread(pm, pos);
               }

               submenuThread.start();
               return (true);
            }
         }
         return (false);
      } // of maybeShowPieSubmenu
   } // of PieMenuHandler

   //===   PIE MENU HANDLER INNER CLASS   ======================================
   //===========================================================================



   //===========================================================================
   //===   POLAR INNER CLASS   =================================================

   /**
    * Holds a polar coordinate.
    */
   final class PolarCoordinate {

      //------------------------------------------------------------------

      public double radius;
      public double theta;

      //------------------------------------------------------------------

      public PolarCoordinate(double radius, double theta) {
         this.radius = radius;
         this.theta  = theta;
      } // of constructor

      //------------------------------------------------------------------

      public String toString() {
         return ("[r: " + radius + ", theta: " + theta + "]");
      } // of toString

      //------------------------------------------------------------------

   } // of inner class PolarCoordinate

   //===   POLAR INNER CLASS   =================================================
   //===========================================================================



   //===========================================================================
   //===   NONLOCAL VARIABLES   ================================================

   //// PieMenu appearance variables
   Color             fillColor;                   // color of filled background
   Color             lineColor;                   // color of lines
   Color             fontColor;                   // color of font
   Color             selectedColor;               // the color of selected item
   Color             defaultSelectedItemColor;    // translucent selectedColor
   Font              font;                        // the font to use
   boolean           flagLineNorth;               // draw line to north?
   BlinkTimer        timer;                       // timer for blinking

   transient Image       submenuIconImage;        // arrow image for submenus
   transient BasicStroke stroke;                  // stroke characteristics

   //// Event handling variables
   PieMenuListener   lstnr;                       // mouse listener on ourself
   ItemListener      clistener;                   // listens to the parent
   MouseEvent        lastEvent;                   // last mouse event occurring
   PieMenuHandler    handler;                     // actually handles events
   boolean           flagCanAbortSubmenu;         // hack to make it work -
                                                  //   once you click, you
                                                  //   cannot abort. But you
                                                  //   can abort if you didn't
                                                  //   click (ie drag or move)
   boolean           flagDraggedInPieMenu;        // did we drag in the pie
                                                  //   menu? If so, don't
                                                  //   let the left-mouse
                                                  //   button close the pie
                                                  //   menu. Let it activate
                                                  //   an item instead.
   boolean           flagJustClosedSubmenu;       // did we just close a
                                                  //   submenu? If so, don't
                                                  //   forward move or drag
                                                  //   events to the pie slice
                                                  //   that contained the
                                                  //   submenu. Otherwise, the
                                                  //   pie slice could get
                                                  //   reactivated too quickly.
   boolean           flagJustOpened;              // there are problems with
                                                  //   tap-hold, since if you
                                                  //   release the button
                                                  //   immediately after
                                                  //   opening, the pie menu
                                                  //   closes, which is not the
                                                  //   behavior you want.
   private boolean flagAcceptLeft  = false;
   private boolean flagAcceptMid   = false;
   private boolean flagAcceptRight = false;

   //// Graphics and shape variables
   int                 radius;                    // radius of the pie menu
   int                 smallRadius;               // radius of inner circle
   transient Ellipse2D bigCircle;                 // the actual pie menu
   transient Ellipse2D smallCircle;               // small circle within
   transient Ellipse2D clipCircle;                // clipping boundaries
   transient Map       newHints;                  // rendering hints

   //// Pie Menu behavior variables
   boolean           flagPenMode;
   double            scalingFactor;               // how much to scale radius
                                                  //    when rendering text

   //// Pie Menu variables
   String            strText;                     // text name of this menu
   Icon              icon;                        // an icon for this menu
   Container         parent;                      // the component we are on
   java.util.List    list;                        // list of menu items
   int               selected        = -1;        // # of item selected
   int               defaultSelected = -1;        // item to select by default
   ShowThread        showThread;                  // thread to show the menu
   ShowSubmenuThread submenuThread;               // thread to show submenu
   int               submenuPos;                  // menu position of submenu
   PieMenu           submenu;                     // the submenu
                                                  //    null if none open
   PieMenu           parentMenu = null;           // the parent menu
                                                  //   of this submenu
                                                  //   (if it is one)

   //// Listeners
   ArrayList         popupMenuListeners;          // listeners on the popup

   //===   NONLOCAL VARIABLES   ================================================
   //===========================================================================



   //===========================================================================
   //===   CONSTRUCTORS   ======================================================

   /**
    * Create a pie menu on the specified applet.
    */
   public PieMenu() {
      this(DEFAULT_BIG_RADIUS);
   } // of constructor

   //-----------------------------------------------------------------

   public PieMenu(int radius) {
      this("", null, radius);
   } // of constructor

   //-----------------------------------------------------------------

   public PieMenu(String str) {
      this(str, null, DEFAULT_BIG_RADIUS);
   } // of constructor

   //-----------------------------------------------------------------

   public PieMenu(String str, Icon icon) {
      this(str, icon, DEFAULT_BIG_RADIUS);
   } // of constructor

   //-----------------------------------------------------------------

   public PieMenu(String str, int radius) {
      this(str, null, radius);
   } // of constructor

   //-----------------------------------------------------------------

   /**
    * Create a pie menu with the specified parameters.
    *
    * @param str    is the name of this pie menu.
    * @param icon   is the icon for this pie menu.
    * @param radius is the intiial radius of the pie menu.
    */
   public PieMenu(String str, Icon icon, int radius) {
      //// 0.1. Initialize to defaults.
      setFillColor(getDefaultFillColor());
      setLineColor(getDefaultLineColor());
      setFontColor(getDefaultFontColor());
      setSelectedColor(getDefaultSelectedColor());
      setFont(getDefaultFont());
      setLineWidth(getDefaultLineWidth());
      setLineNorth(getDefaultLineNorth());
      setScalingFactor(getDefaultScalingFactor());

      submenuIconImage     = getDefaultSubmenuIcon();

      //// 0.2. Initialize some behaviors.
      bigCircle            = new Ellipse2D.Double();
      smallCircle          = new Ellipse2D.Double();
      clipCircle           = new Ellipse2D.Double();
      list                 = new ArrayList();
      timer                = new BlinkTimer();
      setDoubleBuffered(true);

      //// 0.3. Initialize the listeners.
      popupMenuListeners = new ArrayList();

      //// 0.4. Only draw what we say to draw, don't draw anything else.
      ////      If this is true, then we get some strange repaint problems.
      setOpaque(false);

      //// 1. Setup the listener that we will attach to the parent,
      ////    and the one we will attach to ourself.
      handler   = new PieMenuHandler();
      lstnr     = new PieMenuListener();
      clistener = new ItemListener();

      //// 2. Setup Component stuff, our location, visibility, and font.
      setLocation(0, 0);
      setVisible(true);
      setFont(getDefaultFont());

      //// 3. Set the radius, string, and icon.
      setBigRadius(getDefaultBigRadius());
      setSmallRadius(getDefaultSmallRadius());
      setIcon(icon);
      setText(str);

      //// 4. And now setup a listener on ourself.
      addMouseListener(lstnr);
      addMouseMotionListener(lstnr);

      //// 5. Setup the rendering hints.
      newHints = new HashMap();
      newHints.put(RenderingHints.KEY_ANTIALIASING,
                   RenderingHints.VALUE_ANTIALIAS_ON);
      newHints.put(RenderingHints.KEY_COLOR_RENDERING,
                   RenderingHints.VALUE_COLOR_RENDER_QUALITY);
      newHints.put(RenderingHints.KEY_RENDERING,
                   RenderingHints.VALUE_RENDER_QUALITY);
      newHints.put(RenderingHints.KEY_TEXT_ANTIALIASING,
                   RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

   } // of default constructor

   //===   CONSTRUCTORS   ======================================================
   //===========================================================================



   //===========================================================================
   //===   MENUELEMENT INTERFACE   =============================================

   public MenuElement[] getSubElements() {
      MenuElement[] m = new MenuElement[list.size()];

      for (int i = 0; i < list.size(); i++) {
         m[i] = (MenuElement) list.get(i);
      }

      return (m);
   } // of method

   //-----------------------------------------------------------------

   public void menuSelectionChanged(boolean isIncluded) {
      //// 1. Ignore - I don't believe there is anything we need to do here.
   } // of method

   //-----------------------------------------------------------------

   public void processKeyEvent(KeyEvent evt, MenuElement[] path,
         MenuSelectionManager manager) {
// XXX
      throw new RuntimeException("this method has not been implemented yet");
   } // of method

   //-----------------------------------------------------------------

   public void processMouseEvent(MouseEvent evt, MenuElement[] path,
         MenuSelectionManager manager) {
// XXX
      throw new RuntimeException("this method has not been implemented yet");
   } // of method

   //===   MENUELEMENT INTERFACE   =============================================
   //===========================================================================



   //===========================================================================
   //===   POLAR METHODS   =====================================================

   /**
    * Given an (x,y) coordinate, figure out the angle from the center of this
    * pie menu, assuming that the origin is at (radius, radius). We can assume
    * the origin is there since the coordinate space has (0, 0) at the top-left
    * of this pie menu, meaning that (radius, radius) is the center of this
    * pie menu.
    *
    * <PRE>
    *                     0 radians
    *         ---------    |
    *         |            |
    *        \/            |
    *          ------------|--------------
    *                      |
    *                      |
    *                      |
    *                    pi radians
    * </PRE>
    *
    * @return the angle (in radians) from the positive y-axis,
    *         going counter-clockwise. Ranges from 0 to less than 2*PI.
    */
   private PolarCoordinate getPolarCoordinates(int x, int y) {
      //// 1. First translate such that x and y are relative to (0, 0).
      int xx = x - radius;
      int yy = y - radius;

      //// 2. Figure out the radius. Just the distance from (0, 0).
      double distance = Math.sqrt(xx*xx + yy*yy);

      //// 3. Now figure out the angle.
      double normalizedRadius = ((double) xx) / distance;
      double theta            = Math.acos(normalizedRadius);

      //// 3.1. Have to dress up theta a little. The function acos() only
      ////      returns values from 0.0 to PI. This should mean that
      ////      acos() returns the correct value if y is positive.
      ////      Normally, this would be < and not >, but screen coordinate
      ////      system is backwards.
      if (yy > 0) {
         theta = 2*Math.PI - theta;
      }

      //// 4. Okay, that's it. Return the answer.
      return (new PolarCoordinate(distance, theta));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Convert polar coordinates to cartesian.
    *
    * @param  x       is the x-coordinate of the origin.
    * @param  y       is the y-coordinate of the origin.
    * @param  radians is the number of radians to go through.
    * @param  radius  is the length of the radius.
    * @param  pt      is the point to put the results in.
    * @return an (x,y) point.
    */
   Point
   polarToCartesian(int x, int y, double radian, double radius, Point pt) {

      //// 1. Convert the polar coordinates.
      ////    Normally, the y calculation would be addition instead of
      ////    subtraction, but we are dealing with screen coordinates,
      ////    which has its y-coordinate at the top and not the bottom.
      pt.x = (int) (x + radius*Math.cos(radian));
      pt.y = (int) (y - radius*Math.sin(radian));

      //// 2. Straighten up the data a little.
      if (Math.abs(pt.x - radius) <= 1) {
         pt.x = (int) radius;
      }
      if (Math.abs(pt.y - radius) <= 1) {
         pt.y = (int) radius;
      }

      return (pt);
   } // of method

   //-----------------------------------------------------------------

   /**
    * See if an angle is between the two specified angles.
    *
    * @param  angle is the angle to see if it is between a and b (radians).
    * @param  a     is one bounding angle (radians).
    * @param  b     is the other bounding angle (radians).
    * @return true if the angle is between angles a and b going
    *         counterclockwise. Returns true if a and b are the same.
    */
   static boolean isBetween(double angle, double a, double b) {
      //// 1. Normalize values.
      angle %= 2*Math.PI;
      a     %= 2*Math.PI;
      b     %= 2*Math.PI;

      if (a < b) {
         if ((a <= angle) && (angle <= b)) {
            // System.out.println("true " + a + " <= " + angle + " <= " + b);
            return (true);
         }
         else {
            // System.out.println("false " + a + " <= " + angle + " <= " + b);
            return (false);
         }
      }
      else {
         if ((b >= angle) || (angle >= a)) {
            // System.out.println("true " + a + " <= " + angle + " <= " + b);
            return (true);
         }
         else {
            // System.out.println("false " + a + " <= " + angle + " <= " + b);
            return (false);
         }
      }
   } // of method

   //===   POLAR METHODS   =====================================================
   //===========================================================================



   //===========================================================================
   //===   INTERNAL PIE MENU METHODS   =========================================

   private void setPenMode() {
      flagPenMode = true;
   } // of method

   private boolean getPenMode() {
      return (flagPenMode);
   } // of method

   //-----------------------------------------------------------------

   private void setMouseMode() {
      flagPenMode = false;
   } // of method

   private boolean getMouseMode() {
      return (!flagPenMode);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Get the radian of the first position. We always start at north.
    */
   private double getStartRadian() {
      int    numItems = getItemCount();

      if (getLineNorth() == true || numItems <= 1) {
         return (DEFAULT_START);
      }
      else {
         double offset = 2*Math.PI / numItems;
         return (DEFAULT_START - offset / 2);
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Given a coordinate, get the corresponding slice number of the pie.
    *
    * @return the slice number, zero-based, starting at north, going
    *         counter-clockwise. Returns -1 on error or if the small circle
    *         contains it.
    */
   private int getSliceNumber(int x, int y) {
      PolarCoordinate polar    = getPolarCoordinates(x, y);
      int             numItems = getItemCount();

      //// 0. See if the small circle contains it.
      if (smallCircle.contains(x, y)) {
         return (-1);
      }

      //// 1. Initialize the radian variables.
      double currentRadian = getStartRadian();
      double stepRadian    = 2*Math.PI / numItems;
      double theta         = 2*Math.PI + polar.theta;

      //// 2. Figure out which segment we are in.
      int count = 0;
      for (int i = 0; i < 2*numItems; i++) {
         if ((currentRadian < theta) &&
             (theta <= currentRadian + stepRadian)) {
            return (count % numItems);
         }
         count++;
         theta -= stepRadian;
      }

      //// 3. Return -1 for error.
      return (-1);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Get the deepest-level pie menu that is showing. This is necessary for
    * dispatching events to the correct pie menu in the correct coordinate
    * system.
    */
   PieMenu getActiveMenu() {
      PieMenu pm = getActiveMenuHelper();
      if (pm == null) {
         return (this);
      }
      else {
         return (pm);
      }
   } // of method

   //-----------------------------------------------------------------

   PieMenu getActiveMenuHelper() {
      //// 1.1. Recurse to the deepest-level pie menu.
      if (submenu != null) {
         PieMenu pm = submenu.getActiveMenuHelper();
         if (pm != null) {
            return (pm);
         }
      }

      //// 1.2. Once we are at the deepest level, return the first
      ////      one that is showing.
      if (isShowing() == true) {
         return (this);
      }
      else {
         return (null);
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Convert the coordinate space of this mouse event from the coordinate
    * space of the component it took place in, to the coordinate space of the
    * active menu.
    */
   MouseEvent convertMouseEventSpace(MouseEvent evt) {
      Point   ptComponent = evt.getComponent().getLocationOnScreen();
      PieMenu activeMenu  = getActiveMenu();
      Point   ptPie       = activeMenu.getLocationOnScreen();

      evt.translatePoint(ptComponent.x - ptPie.x, ptComponent.y - ptPie.y);
      return (evt);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Get the listener for either the pie menu or (recursively) one of
    * its submenus, depending on whom we are supposed to dispatch to.
    */
   PieMenuHandler getDispatcher() {
      PieMenu activeMenu = getActiveMenu();
      return (activeMenu.getPieMenuHandler());
   } // of method

   //-----------------------------------------------------------------

   /**
    * A way to get to the listener of the Pie Menu. Necessary for
    * redispatching.
    */
   PieMenuHandler getPieMenuHandler() {
      return (handler);
   } // of method

   //-----------------------------------------------------------------

   //Helper functions that exist only to help adjust where the pie menus
   //are placed relative to screen boundaries

   private int fixPieLocationX(int x) {
      Dimension dim = Toolkit.getDefaultToolkit().getScreenSize();
      int returnvalue = x;
      if (x + defaultBigRadius > dim.width) {
          returnvalue = dim.width - defaultBigRadius;
      }
      if (x - defaultBigRadius < 0) {
          returnvalue = defaultBigRadius;
      }
      return returnvalue;
      
   }
   
   private int fixPieLocationY(int y) {
      Dimension dim = Toolkit.getDefaultToolkit().getScreenSize();
      int returnvalue = y;
      if (y + defaultBigRadius > dim.height) {
          returnvalue = dim.height - defaultBigRadius;
      }
      if (y - defaultBigRadius < 0) {
          returnvalue = defaultBigRadius;
      }
      return returnvalue;
   }
   //Ends here...

   /**
    * Update either where a piemenu or one of its submenu will be displayed.
    * Technically, these should be two methods, but only one of them will have
    * an effect at a time, so it should be okay.
    *
    * @param x is the absolute coordinate to show the submenu at.
    * @param y is the absolute coordinate to show the submenu at.
    */
   void updateShowLocation(int x, int y) {
      
      //// 1. If we are going to show a submenu, then update
      ////    where we will show it.
      if (submenuThread != null) {
         submenuThread.setShowLocation(x, y);
      }
      //// 2. If we are going to show a piemenu, and we are in
      ////    tap mode, then update where we will show it.
      if (showThread != null && (isTapOpen() || isTapHoldOpen() )) {
         showThread.setShowLocation(x, y);
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Clear out the last mouse event we have.
    */
   void clearLastMouseEvent() {
      lastEvent = null;
   } // of method

   /**
    * Set what the latest interesting mouse event we have is.
    */
   void setLastMouseEvent(MouseEvent evt) {
      lastEvent = new MouseEvent(evt.getComponent(), evt.getID(), 0,
         evt.getModifiers(), evt.getX(), evt.getY(), evt.getClickCount(),
         evt.isPopupTrigger());
   } // of method

   //-----------------------------------------------------------------

   /**
    * Forward the last event to the pie menu IF we do not have a default
    * selected item. This lets us do actions on the pie menu before it
    * actually appears on screen.
    */
   void forwardLastEvent() {
      // System.out.println("forwarding last event");
      // System.out.println(lastEvent);

      //// 1. Figure out who we should redispatch to.
      if (lastEvent != null) {
         PieMenuHandler redispatcher = getDispatcher();
         MouseEvent     evt          = convertMouseEventSpace(lastEvent);
         switch (lastEvent.getID()) {
            case MouseEvent.MOUSE_MOVED:
               redispatcher.handleMouseMoved(lastEvent);
               break;
            case MouseEvent.MOUSE_DRAGGED:
               redispatcher.handleMouseDragged(lastEvent);
               break;
            case MouseEvent.MOUSE_RELEASED:
               redispatcher.handleMouseReleased(lastEvent);
               break;
            default:
               //// ignore - do not forward any event
         } // of switch
         clearLastMouseEvent();
      }
   } // of method

   //===   INTERNAL PIE MENU METHODS   =========================================
   //===========================================================================



   //===========================================================================
   //===   PIE MENU LOOK AND FEEL METHODS   ====================================

   /**
    * Set the color of the pie menu items.
    */
   public void setFillColor(Color newColor) {
      fillColor = newColor;
   } // of method

   /**
    * Get the color of the pie menu items.
    */
   public Color getFillColor() {
      return (fillColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the color lines are rendered in.
    */
   public void setLineColor(Color newColor) {
      lineColor = newColor;
   } // of method

   /**
    * Get the color lines are rendered in.
    */
   public Color getLineColor() {
      return (lineColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the color of the selected item.
    */
   public void setSelectedColor(Color newColor) {
      selectedColor = newColor;
      defaultSelectedItemColor = new Color(selectedColor.getRed(),
         selectedColor.getGreen(), selectedColor.getBlue(), 127);
   } // of method

   /**
    * Get the color of the selected item.
    */
   public Color getSelectedColor() {
      return (selectedColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the color text is rendered in.
    */
   public void setFontColor(Color newColor) {
      fontColor = newColor;
   } // of method

   /**
    * Get the color text is rendered in.
    */
   public Color getFontColor() {
      return (fontColor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the font the pie menu will use.
    */
   public void setFont(Font newFont) {
      super.setFont(newFont);
   } // of method

   /**
    * Get the font the pie menu will use.
    */
   public Font getFont() {
      return (super.getFont());
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the line width for the pie menu.
    */
   public void setLineWidth(float newWidth) {
      stroke = new BasicStroke(newWidth);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the radius for the pie menu.
    *
    * @param radius is the radius of the pie menu from the center.
    */
   public void setBigRadius(int radius) {
      if (radius > 0) {
         //// 1. Setup the radius. Actually set our size to be slightly
         ////    larger than the radius.
         this.radius = radius;
         setSize(2*radius + 1, 2*radius + 1);

         //// 2. Update the min, max, and preferred sizes.
         Dimension dim = new Dimension(2*radius, 2*radius);
         setMinimumSize(dim);
         setMaximumSize(dim);
         setPreferredSize(dim);

         //// 3. Now update the bigCircle shape.
         updateShape();
      }
   } // of method

   /**
    * Get the radius for the pie menu.
    */
   public int getBigRadius() {
      return (radius);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the radius of the inner circle for the pie menu.
    */
   public void setSmallRadius(int newRadius) {
      this.smallRadius = newRadius;
      updateShape();
   } // of method

   /**
    * Get the radius of the inner circle for the pie menu.
    */
   public int getSmallRadius() {
      return (smallRadius);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the scaling factor for the pie menu.
    */
   public void setScalingFactor(double newScalingFactor) {
      scalingFactor = newScalingFactor;
   } // of method

   /**
    * Get the scaling factor for the pie menu.
    */
   public double getScalingFactor() {
      return (scalingFactor);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set whether we draw a line to north, or draw the first slice such
    * that it is centered on north.
    *
    * @param flag is true if a line is to be drawn to north, false otherwise.
    */
   public void setLineNorth(boolean flag) {
      flagLineNorth = flag;
   } // of method

   /**
    * Get whether we draw a line to north, or draw the first slice such
    * that it is centered on north.
    */
   public boolean getLineNorth() {
      return (flagLineNorth);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set the left mouse button as a possible input to pop up the pie.
    */
   public void setAcceptLeftButton(boolean bool) {
      flagAcceptLeft = bool;
   } // of method
   
   /**
    * Set the right mouse button as a possible input to pop up the pie.
    */
   public void setAcceptRightButton(boolean bool) {
      flagAcceptRight = bool;
   } // of method

   /**
    * Set the middle mouse button as a possible input to pop up the pie.
    */
   public void setAcceptMidButton(boolean bool) {
      flagAcceptMid = bool;
   } // of method
   
   
   //===   PIE MENU LOOK AND FEEL METHODS   ====================================
   //===========================================================================



   //===========================================================================
   //===   PIE MENU UTILITY METHODS   ==========================================

   /**
    * Don't show the submenu, whether or not it is activated or not.
    * Technically, this is not 100% correct as there may be race conditions.
    */
   private void abortSubmenu() {
      if (submenuThread != null && flagCanAbortSubmenu == true) {
         // System.out.println("aborting...");
         submenuThread.abort();
         if (submenu != null) {
            submenu.setVisible(false);
         }
         submenuThread = null;
         submenu       = null;
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set which menu item is currently selected.
    *
    * @param index is the index of the selected item. It has a value less than
    *              0 to select the center circle.
    */
   public void setSelectedItem(int index) {
      // System.out.println("   setSelectedItem");
      // System.out.println("      old " + selected);
      // System.out.println("      new " + index);

      //// 0. See if select has been turned on or off.
      if (selectIsEnabled() == false) {
         return;
      }

      //// 1. No point in doing anything unless we have something new selected.
      if (index != selected) {
         //// 1.1. Don't change the selected item if we already clicked
         ////      somewhere.
         if (submenuThread != null && flagCanAbortSubmenu == false) {
            return;
         }

         //// 1.2. If we have moved to another item, then do not show
         ////    the delayed pie menu.
         abortSubmenu();

         //// 1.3. Set the selected item.
         this.selected = index;

         //// 1.4. Okay to forward events to the former pie submenu slice again.
         flagJustClosedSubmenu = false;

         //// 1.5. Repaint the PieMenu.
         repaintBounds();
      }

   } // of method

   //-----------------------------------------------------------------

   /**
    * Get the menu item that is currently selected.
    *
    * @return the index of the currently selected item (0 based),
    *         or -1 if the small center circle is selected.
    */
   public int getSelectedItem() {
      return (selected);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Set what the selected item is by default when the pie menu is opened.
    * Be sure to set this <B>AFTER</B> adding items to the pie menu, as it
    * ignores invalid values.
    *
    * @param pos is the index of the menu item to be selected by default.
    *            Pass in a negative value to specify the little circle.
    *            Ignores values that are too large, defaults to the little
    *            circle.
    */
   public void setDefaultSelectedItem(int pos) {
      if (pos >= getItemCount()) {
         pos = -1;
      }
      defaultSelected = pos;
   } // of method

   public int getDefaultSelectedItem() {
      return (defaultSelected);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Specify what triggers the popup of this pie menu.
    * Checks in this order: left, right, middle
    */
   public boolean doesActivateMenu(MouseEvent evt) {
      if (flagAcceptLeft) {
         return (SwingUtilities.isLeftMouseButton(evt));
      }
      else if (flagAcceptRight) {
         return (SwingUtilities.isRightMouseButton(evt));
      }
      else if (flagAcceptMid) {
         return (SwingUtilities.isMiddleMouseButton(evt));
      }
      else {
         return (SwingUtilities.isRightMouseButton(evt));
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * A convenience method to have the pie menu listen on the specified
    * component. By default, this makes the pie menu listen for right mouse
    * clicks. If any are received, then the pie menu will pop open.
    *
    * @param c is the component to attach the pie menu to. Right now,
    *        PieMenu only works with Java Swing components.
    */
   public void addPieMenuTo(Component c) {
      c.addMouseListener(clistener);
      c.addMouseMotionListener(clistener);
      c.addComponentListener(clistener);
   } // of method

   //===   PIE MENU UTILITY METHODS   ==========================================
   //===========================================================================



   //===========================================================================
   //===   SHAPE METHODS   =====================================================

   /**
    * Update the shape of this PieMenu whenever the location or radius is
    * changed.
    */
   protected void updateShape() {
      //// 1. Since our top-left corner is (0, 0), the shape is simply a
      ////    circle from (0, 0) to the width and height, both of which
      ////    should be 2*radius.
      Rectangle bounds = getBounds();
      bigCircle.setFrame(0, 0, 2*radius, 2*radius);
      clipCircle.setFrame(-2, -2, 2*radius + 4, 2*radius + 4);
      smallCircle.setFrame(radius - smallRadius, radius - smallRadius,
                           2*smallRadius, 2*smallRadius);
   } // of method

   //-----------------------------------------------------------------

   public boolean contains(int x, int y) {
      if ( isVisible() == false) {
         return (false);
      }
      return (bigCircle.contains(x, y));
   } // of method

   //-----------------------------------------------------------------

   public boolean contains(Point pt) {
      if ( isVisible() == false) {
         return (false);
      }
      return (contains(pt.x, pt.y));
   } // of method

   //===   SHAPE METHODS   =====================================================
   //===========================================================================



   //===========================================================================
   //===   MENU METHODS   ======================================================

   public void setText(String str) {
      this.strText = str;
   } // of method

   //-----------------------------------------------------------------

   public String getText() {
      return (strText);
   } // of method

   //-----------------------------------------------------------------

   public void setIcon(Icon icon) {
      this.icon = icon;
   } // of method

   //-----------------------------------------------------------------

   public Icon getIcon() {
      return (icon);
   } // of method

   //-----------------------------------------------------------------

   public Component getComponent() {
      return (parent);
   } // of method

   //-----------------------------------------------------------------

   public int getItemCount() {
      return (list.size());
   } // of method

   //-----------------------------------------------------------------

   private JMenuItemWrapper add(JMenuItemWrapper item, int index) {
      if (index == -1) {
         list.add(item);
      }
      else {
         list.add(index, item);
      }
      return (item);
   } // of method

   //-----------------------------------------------------------------

   private JMenuItemWrapper add(JMenuItemWrapper item) {
      list.add(item);
      return (item);
   } // of method

   //-----------------------------------------------------------------

   public JMenuItem add(JMenuItem menuItem, int index) {
      return (add(menuItem.getText(), menuItem.getIcon(), index));
   } // of method

   //-----------------------------------------------------------------

   public JMenuItem add(JMenuItem menuItem) {
      return (add(menuItem.getText(), menuItem.getIcon(), -1));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Add an Icon as a menu element at the given position. If
    * <code>index</code> equals -1, the component will be appended
    * to the end.
    */
   public JMenuItem add(Icon icon, int index) {
      return (add(new JMenuItemWrapper(icon), index));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Add an Icon as a menu element.
    */
   public JMenuItem add(Icon icon) {
      return (add(new JMenuItemWrapper(icon)));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Add a String as a menu element at the given position. If
    * <code>index</code> equals -1, the component will be appended
    * to the end.
    */
   public JMenuItem add(String str, int index) {
      return (add(new JMenuItemWrapper(str), index));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Add a String as a menu element.
    */
   public JMenuItem add(String str) {
      return (add(new JMenuItemWrapper(str)));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Add a String and Icon as a menu element at the given position. If
    * <code>index</code> equals -1, the component will be appended
    * to the end.
    */
   public JMenuItem add(String str, Icon icon, int index) {
      return (add(new JMenuItemWrapper(str, icon), index));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Add a String and Icon as a menu element.
    */
   public JMenuItem add(String str, Icon icon) {
      return (add(new JMenuItemWrapper(str, icon)));
   } // of method

   //-----------------------------------------------------------------

   /**
    * Adds a pie menu as a menu element at the given position. If
    * <code>index</code> equals -1, the component will be appended
    * to the end.
    */
   public void add(PieMenu menu, int index) {
      if (index == -1) {
         add(menu);
      }
      else {
         list.add(index, menu);
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Adds a pie menu as a menu element. This is to allow multi-level
    * pie menus. In later releases, Pie Menus will also be JMenuItems,
    * so everything will be consistent.
    */
   public void add(PieMenu menu) {
      list.add(menu);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Removes the menu item at the specified index from this menu.
    */
   public void remove(int pos) {
      list.remove(pos);
   } // of method

   //-----------------------------------------------------------------

   public JMenuItem getItem(int pos) {
      return ((JMenuItem) list.get(pos));
   } // of method

   //===   MENU METHODS   ======================================================
   //===========================================================================



   //===========================================================================
   //===   POPUP MENU METHODS   ================================================

   public void addPopupMenuListener(PopupMenuListener l) {
      popupMenuListeners.add(l);
   } // of method

   //-----------------------------------------------------------------

   public void removePopupMenuListener(PopupMenuListener l) {
      popupMenuListeners.remove(l);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Called just before the pie menu appears.
    */
   protected void firePopupMenuWillBecomeVisible() {
      //// 1. Clone the list before callbacks, preventing concurrent mod errors.
      java.util.List    lst = (ArrayList) popupMenuListeners.clone();
      PopupMenuListener l;

      //// 2. Iterate and call.
      Iterator it = lst.iterator();
      while (it.hasNext()) {
         l = (PopupMenuListener) it.next();
         l.popupMenuWillBecomeVisible(new PopupMenuEvent(this));
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Called just before the pie menu disappears.
    */
   protected void firePopupMenuWillBecomeInvisible() {
      //// 1. Clone the list before callbacks, preventing concurrent mod errors.
      java.util.List    lst = (ArrayList) popupMenuListeners.clone();
      PopupMenuListener l;

      //// 2. Iterate and call.
      Iterator it = lst.iterator();
      while (it.hasNext()) {
         l = (PopupMenuListener) it.next();
         l.popupMenuWillBecomeInvisible(new PopupMenuEvent(this));
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Called just before the pie menu is cancelled (by clicking on the center).
    * Methods that call this should also call firePopupMenuWillBecomeInvisible.
    */
   protected void firePopupMenuCanceled() {
      //// 1. Clone the list before callbacks, preventing concurrent mod errors.
      java.util.List    lst = (ArrayList) popupMenuListeners.clone();
      PopupMenuListener l;

      //// 2. Iterate and call.
      Iterator it = lst.iterator();
      while (it.hasNext()) {
         l = (PopupMenuListener) it.next();
         l.popupMenuCanceled(new PopupMenuEvent(this));
      }
   } // of method

   //===   POPUP MENU METHODS   ================================================
   //===========================================================================



   //===========================================================================
   //===   AWT METHODS   =======================================================

   /**
    * Hide immediately.
    */
   public void setVisible(boolean flag) {
      if (flag == true) {
         firePopupMenuWillBecomeVisible();
      }
      else {
         firePopupMenuWillBecomeInvisible();
         hideInternal();
      }
      super.setVisible(flag);
   } // of method

   //-----------------------------------------------------------------

   private void hideInternal() {
      enableSelect();
      if (parent != null) {
         //// 1. Hide the pie menu and repaint the area.
         Rectangle rect      = this.getBounds();
         parent.remove(this);

         // parent.repaint();
         parent.repaint(rect.x, rect.y, rect.width, rect.height);
         parent              = null;

         //// 2. Don't show the submenu.
         flagCanAbortSubmenu = true;
         abortSubmenu();

         //// 3. Turn off the blink.
         timer.stop();

         //// 4. Just in case.
         showThread    = null;
         submenuThread = null;
         submenu       = null;
         clearLastMouseEvent();
      }
   } // of method

   //-----------------------------------------------------------------

   /**
    * Hide the pie menu's and all of its submenus.
    */
   private void hideDescendants() {
      if (submenu != null) {
         submenu.hideDescendants();
      }
      setVisible(false);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Hide the pie menu's and all of its ancestor menus.
    */
   private void hideAncestors() {
      if (parentMenu != null) {
         parentMenu.hideAncestors();
      }
      setVisible(false);
   }

   //-----------------------------------------------------------------

   /**
    * Hide the pie menu, all of its submenus, and all of its parent menus.
    */
   private void hideAll() {
      hideDescendants();
      hideAncestors();
   }

   //-----------------------------------------------------------------

   /**
    * Show the pie menu.
    *
    * @param invoker is the Component to show the pie menu in.
    * @param x       is the x-coordinate in the invoker's coordinate space.
    * @param y       is the y-coordinate in the invoker's coordinate space.
    * @param ms      is the delay (msec) before showing the pie menu.
    */
   public void show(Component invoker, int x, int y) {
      //// 1. Just in case we have another show, abort it.
      if (showThread != null) {
         showThread.abort();
      }

      //// 2. Now start the delayed display.
      showThread = new ShowThread(invoker, x, y);
      showThread.start();
   } // of method

   //-----------------------------------------------------------------

   public void showNow(Component invoker, int x, int y) {
      //// 1. Just in case we have another show, abort it.
      if (showThread != null) {
         showThread.abort();
      }

      showInternal(invoker, x, y);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Show the pie menu.
    *
    * @param invoker is the Component to show the pie menu in.
    * @param x       is the x-coordinate in the invoker's coordinate space.
    * @param y       is the y-coordinate in the invoker's coordinate space.
    */
   private void showInternal(Component invoker, int x, int y) {
      enableSelect();
      updatePieMenuToCurrentMode(this);

      //// 0. Set the selected item. Don't use setSelectedItem() because
      ////    that has additional behavior.
      selected = -1;

      //// 1.  First, recurse to the top window so we can attach ourself
      ////     to it.
      Container parent       = null;
      Window    parentWindow = null;

      if (invoker != null) {
         parent = invoker.getParent();
      }

      Point pt    = invoker.getLocation();
      Point ptTmp;

      for (Container p = parent; p != null; p = p.getParent()) {
         //// 2.1. Get to the top of the rootpane.
         if (p instanceof JRootPane) {
            parent = ((JRootPane) p).getLayeredPane();
            p      = parent.getParent();
            while (p != null && !(p instanceof java.awt.Window)) {
               p = p.getParent();
            }
            parentWindow = (Window) p;
            break;
         }
         //// 2.2. Get to the top Java Window.
         else if (p instanceof Window) {
            throw new RuntimeException(
                  "Sorry, Pie Menu does not work with non-Swing widgets yet");
            // parent       = p;
            // parentWindow = (Window) p;
            // break;
         }
         ptTmp = p.getLocation();
         pt.x += ptTmp.x;
         pt.y += ptTmp.y;
      }

      //// 3. Setup our location and layer on the layered pane.
      setLocation(fixPieLocationX(pt.x + x), fixPieLocationY(pt.y + y));
      if (parent instanceof JLayeredPane) {
         ((JLayeredPane) parent).add(this, JLayeredPane.POPUP_LAYER, 0);
      }
      else {
         parent.add(this);
      }

      //// 4.1. Setup stuff on our parent.
      this.parent            = parent;

      //// 4.2. No submenu showing.
      flagCanAbortSubmenu   = true;
      flagJustOpened        = true;
      flagJustClosedSubmenu = false;
      flagDraggedInPieMenu  = false;
      if (showThread != null) {
         showThread.abort();
         showThread = null;
      }
      if (submenuThread != null) {
         submenuThread.abort();
         submenuThread       = null;
         submenu             = null;
      }

      //// 5. Fire off notifications.
      setVisible(true);
   } // of method

   //-----------------------------------------------------------------

   public void setLocation(Point pt) {
      setLocation(pt.x, pt.y);
   } // of method

   //-----------------------------------------------------------------

   public void setLocation(int x, int y) {
      //// 1. Actually set our location to be somewhere else.
      ////    Repaint will be handled when we are set to visible.
      super.setLocation(x - radius, y - radius);
      setBigRadius(radius);

      //// 2. Update the bigCircle shape.
      updateShape();
   } // of method

   //===   AWT METHODS   =======================================================
   //===========================================================================



   //===========================================================================
   //===   DISPLAY METHODS   ===================================================

   /**
    * Calls repaint on the correct bounds of the Pie Menu.
    */
   private void repaintBounds() {
      //// 1. No point in repainting if no parent.
      if (parent == null) {
         return;
      }

      //// 2. Repaint the bounds.
      Point     pt   = getLocation();
      Rectangle rect = getBounds();
      parent.repaint(rect.x, rect.y, rect.width, rect.height);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Render a String at the given angle and maximum radius.
    *
    * @param gg      is the Graphics context to render on.
    * @param xx      is the origin for the angle and radius.
    * @param yy      is the origin for the angle and radius.
    * @param str     is the String to render.
    * @param angle   is the angle to render the String str at.
    * @param radius  is the largest radius to render the String str at.
    *                The pie menu scaling factor will be used.
    * @param enabled specifies whether the menu item is enabled or not.
    */
   protected void renderString(Graphics2D gg, int xx, int yy, String str,
                       double angle, double radius, boolean enabled) {

      //// 1. Compute the width of the string.
      Point       pt      = new Point();               // temporary storage
      FontMetrics fmetric = getFontMetrics(getFont()); // current font metrics
      float       width;                               // width is variable
      float       height  = fmetric.getHeight();       // height is constant

      //// 2. Convert the coordinates from polar to cartesian.
      polarToCartesian(xx, yy, angle, radius * scalingFactor, pt);
      
      //// 2.1. Readjust the point so it's actually in the center of the pie
      ////      menu.
      Point m_pt = new Point();
      polarToCartesian(xx, yy, angle, radius * scalingFactor, m_pt);
      m_pt.x = m_pt.x + DEFAULT_BIG_RADIUS;
      m_pt.y = m_pt.y + DEFAULT_BIG_RADIUS;

      //// 3. Tokenize the String, in case it has newlines and such.
      StringTokenizer strtok = new StringTokenizer(str, "\r\n\t");
      int             offset = 0;
      String          token;
      
      //System.out.println(angle);

      //// 3.1. Draw each token so that it is centered at pt.x and pt.y.
      pt.y = pt.y - (int) (((float) (strtok.countTokens() - 1) / 2) * height);
      
      while (strtok.hasMoreTokens()) {
         token = strtok.nextToken();
         width = fmetric.stringWidth(token);
         //System.out.println(Math.sin(angle));
         
         //// 3.1.1. Figure out the orientation, and use it to scoot the text
         ////        over on the pie menus.
         double orientation = findAngle(angle);
         //System.out.println(orientation);
         
         if (orientation == ORIENT_TOP) {
            m_pt.y = (int)(-1 * DEFAULT_BIG_RADIUS * Math.sin(angle));// - 0.5*height);
         }
         
         //if (orientation == ORIENT_RIGHT) {
         //   if ((pt.x + 0.5*width ) < (DEFAULT_BIG_RADIUS * Math.cos(angle)) &&
         //       (pt.y + 0.5*height) < (DEFAULT_BIG_RADIUS * Math.sin(angle))) {
         //      pt.x = (int)(DEFAULT_BIG_RADIUS * Math.cos(angle));// - 0.5*width);
         //   }
         //}
         //
         //if (orientation == ORIENT_BOTTOM) {
         //   pt.y = -5;//(int)(-0.3*DEFAULT_BIG_RADIUS * Math.sin(angle));// - 0.5*height);
         //   pt.y = 170;
         //}
         //if (orientation == ORIENT_LEFT) {
         //   if ((pt.x - 0.5*width ) < (DEFAULT_BIG_RADIUS * Math.cos(angle)) &&
         //       (pt.y + 0.5*height) < (DEFAULT_BIG_RADIUS * Math.sin(angle))) {
         //      pt.x = (int)(DEFAULT_BIG_RADIUS * Math.cos(angle));// - 0.5*width);
         //   }
         //}
         if (enabled == true) {
            gg.setColor(getFontColor());
            gg.drawString(token, (int) (pt.x - 0.5*width),
                          (int) (pt.y + 0.5*height) + offset);
            
            //// Draw a bounding box around the text for debugging.
            //gg.drawRect((int) (pt.x - 0.5*width), (int) (pt.y - 0.5*height +offset),
            //            (int) width, (int) height);
         }
         else {
            gg.setColor(getFillColor().darker());
            gg.drawString(token, (int) (pt.x - 0.5*width),
                          (int) (pt.y + 0.5*height) + offset);
            //// Draw a bounding box around the text for debugging.
            //gg.drawRect((int) (pt.x - 0.5*width), (int) (pt.y - 0.5*height +offset),
            //            (int) width, (int) height);
         }
         offset += height;
      }
      //gg.setColor(Color.green);
      //gg.drawRect((int)m_pt.x, (int)m_pt.y, 50, 50);
      //System.out.println("X-value: " + m_pt.x + " Y value: " + m_pt.y);

   } // of method

   // Helper function to figure out the orientation
   
   private int findAngle(double angle) {
      double newAngle = angle%(Math.PI*2);
      //System.out.println(newAngle);
      if (newAngle > Math.PI/4 && newAngle < Math.PI * 0.75) {
         return ORIENT_TOP;
      }
      else if (newAngle < Math.PI/4 && newAngle > 0) {//|| newAngle > Math.PI *1.75)
         return ORIENT_TOPRIGHT;
      }
      else if (newAngle > Math.PI * 1.75) {
         return ORIENT_BOTRIGHT;
      }
      else if (newAngle < Math.PI * 1.75 && newAngle > Math.PI * 1.25) {
         return ORIENT_BOTTOM;
      }
      else if (newAngle < Math.PI && newAngle > Math.PI * 0.75) {
         return ORIENT_TOPLEFT;
      }
      else if (newAngle < Math.PI * 1.25 && newAngle > Math.PI) {
         return ORIENT_BOTLEFT;
      }
      else {
         return ORIENT_TOP;
      }
   }

   //-----------------------------------------------------------------

   /**
    * Render a menu icon at the given angle and maximum radius.
    *
    * @param gg      is the Graphics context to render on.
    * @param xx      is the origin for the angle and radius.
    * @param yy      is the origin for the angle and radius.
    * @param icon    is the icon to render.
    * @param angle   is the angle to render the icon at.
    * @param radius  is the largest radius to render the String str at.
    *                The pie menu scaling factor will be used.
    * @param enabled specifies whether the item is enabled or not.
    */
   protected void renderIcon(Graphics2D gg, int xx, int yy, Icon icon,
                             double angle, double radius, boolean enabled) {

      //// 1. Convert the coordinates from polar to cartesian.
      Point pt = new Point();            // temporary storage
      polarToCartesian(xx, yy, angle, radius * scalingFactor, pt);

      //// 2. Prepare to paint into the temporary buffer image.
      BufferedImage img;
      Graphics      img_g;

      img   = new BufferedImage(icon.getIconWidth(), icon.getIconHeight(),
                               BufferedImage.TYPE_3BYTE_BGR);
      img_g = img.getGraphics();

      //// 3. Paint the icon.
      icon.paintIcon(this, img_g, 0, 0);

      //// 4. Now calculate the scaling factor and scale the image.
      double scale = 1.0;
      // img.getScaleInstance()

      //// 5. Cache the scaled instance.

      //// 6. And now draw the scaled image in the real graphics context.
      ////    We want to center it at pt.x and pt.y.
      int drawX = (int) (pt.x - 0.5 * scale * icon.getIconWidth());
      int drawY = (int) (pt.y - 0.5 * scale * icon.getIconHeight());
      gg.drawImage(img, drawX, drawY, null);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Draw the submenu icon.
    */
   protected void renderSubmenuIcon(Graphics2D gg, int xx, int yy, Image img,
                             double angle, double radius) {

      //// 1. Convert the coordinates from polar to cartesian.
      Point pt = new Point();            // temporary storage
      polarToCartesian(xx, yy, angle, radius * 0.9, pt);

      //// 2. Copy the transformations.
      AffineTransform txOld = (AffineTransform) gg.getTransform().clone();
      AffineTransform txNew = (AffineTransform) gg.getTransform().clone();

      //// 3. First relocate the origin, and then rotate around the
      ////    new origin.
      txNew.concatenate(AffineTransform.getTranslateInstance(pt.x, pt.y));
      txNew.concatenate(AffineTransform.getRotateInstance(-angle + Math.PI/2));
      gg.setTransform(txNew);

      //// 4. Draw the image, so that it is centered.
      gg.drawImage(img, (int) (-0.5*img.getWidth(null)),
                        (int) (-0.5*img.getHeight(null)), null);

      //// 5. Restore the old transformation.
      gg.setTransform(txOld);
   } // of method

   //-----------------------------------------------------------------

   /**
    * A temporary measure to retrieve text from both JMenuItems and PieMenus.
    *
    * @param obj is the object from the list of menu items.
    * @param pos is obj's position in that list.
    */
   private String getItemText(Object obj, int pos) {
      int    selectedItem = getSelectedItem();
      String text         = null;

      if (obj instanceof JMenuItem) {
         JMenuItem menuitem = (JMenuItem) obj;
         text = menuitem.getText();
      }
      else {
         PieMenu pie = (PieMenu) obj;
         text = pie.getText();
      }

      return (text);
   } // of method

   //-----------------------------------------------------------------

   /**
    * A temporary measure to retrieve icons from both JMenuItems and PieMenus.
    *
    * @param obj is the object from the list of menu items.
    * @param pos is obj's position in that list.
    */
   private Icon getItemIcon(Object obj, int pos) {
      int    selectedItem = getSelectedItem();
      Icon   icon         = null;

      if (obj instanceof JMenuItem) {
         JMenuItem menuitem = (JMenuItem) obj;
         if (selectedItem == pos) {
            icon = menuitem.getPressedIcon();
         }
         else {
            icon = menuitem.getIcon();
         }
      }
      else {
         PieMenu pie = (PieMenu) obj;
         icon = pie.getIcon();
      }

      return (icon);
   } // of method

   //-----------------------------------------------------------------

   public void paintComponent(Graphics g) {
      //// 0.1. Cast as Graphics2D.
      Graphics2D gg   = (Graphics2D) g;
      Color      oldc = g.getColor();

      //// 0.2. Should we do clipping?
      if (getAllClipping() == true) {
         gg.setClip(clipCircle);
      }

      //// 0.3. Set the rendering quality to make it higher.
      Map oldHints = (Map) gg.getRenderingHints();
      gg.setRenderingHints(newHints);

      //// 0.4. Set the rendering attributes.
      ////      Font is set automatically for us. Stroke is not. Why?
      ////      Who knows? It's certainly a strange design decision.
      gg.setStroke(stroke);
      gg.setPaintMode();

      //// 0.5. Get the selected item number so we can highlight it later.
      int selectedItem        = getSelectedItem();
      int defaultSelectedItem = getDefaultSelectedItem();

      //// 1. Draw the boundary lines. Do nothing if no elements.
      ////    First, calculate the radians required by each element.
      int numItems = getItemCount();
      if (numItems <= 0) {
         gg.setColor(getFillColor());
         gg.fillOval(0, 0, 2*radius, 2*radius);
      }
      else {
         double     stepRadian    = 2*Math.PI / numItems;
         double     currentRadian = getStartRadian();
         Shape      oldClip       = null;
         JComponent item;
         String     text;
         Icon       icon;
         Arc2D      arc;
         //// 1.1. For each element, draw a line from (radius, radius) to
         ////      the endpoint.
         gg.setColor(getLineColor());
         for (int i = 0; i < numItems; i++) {
            //// 1.1.1. Calculate the arc size.
            arc = new Arc2D.Float(0, 0, 2*radius, 2*radius,
                     (float) Math.toDegrees(currentRadian),
                     (float) Math.toDegrees(stepRadian), Arc2D.PIE);

            //// 1.1.2. Color in the selected item.
            if (selectedItem == i) {
               gg.setColor(getSelectedColor());
               gg.fill(arc);
            }
            //// 1.1.3. Otherwise, color in the normal fill color.
            else {
               gg.setColor(getFillColor());
               gg.fill(arc);

               //// 1.1.4. Color in the default selected item.
               if (defaultSelectedItem == i) {
                  gg.setColor(defaultSelectedItemColor);
                  gg.fill(arc);
               }
            }

            gg.setColor(lineColor);

            //// 1.1.5. Retrieve the menu element and subparts.
            ////        This part is hackish, and will be until PieMenu
            ////        implements the full JMenu interface.
            item = (JComponent) list.get(i);
            text = getItemText(item, i);
            icon = getItemIcon(item, i);

            //// 1.1.6. Draw a chevron to represent submenus.
            if (item instanceof PieMenu) {
               renderSubmenuIcon(gg, radius, radius, getSubmenuIcon(),
                             currentRadian + 0.5*stepRadian, radius);
            }

            //// 1.1.7. Render the text and icon. If the clipping flag is
            ////        on, temporarily clip the output so it won't go
            ////        out of bounds.
            if (getAllClipping() == true) {
               oldClip = gg.getClip();
               gg.setClip(arc);
            }
            if (icon == null) {
               renderString(gg, radius, radius, text,
                     currentRadian + 0.5*stepRadian, radius, item.isEnabled());
            }
            else {
               renderIcon(gg, radius, radius, icon,
                     currentRadian + 0.5*stepRadian, radius, item.isEnabled());
            }

            if (getAllClipping() == true) {
               gg.setClip(oldClip);
            }

            //// 1.1.8. Draw the arc lines. Don't draw one if there is
            ////        only one item.
            gg.setColor(getLineColor());
            if (numItems > 1) {
               gg.draw(arc);
            }

            //// 1.1.9. Prepare for the next iteration / pie slice.
            currentRadian += stepRadian;
         } // of for
      } // of if numItems > 0


      //// 2.1. Fill the small circle in the center.
      gg.setColor(getFillColor());
      gg.fill(smallCircle);
      if (selectedItem < 0) {
         gg.setColor(getSelectedColor());
         gg.fill(smallCircle);
      }

      //// 2.2. Draw the line around the small circle in the center.
      gg.setColor(getLineColor());
      gg.draw(smallCircle);

      //// 3. Draw the line around the outer boundary of the PieMenu.
      gg.setColor(getLineColor());
      gg.drawOval(0, 0, 2*radius, 2*radius);

      //// 4. Restore whatever settings we modified.
      gg.setRenderingHints(oldHints);
      gg.setColor(oldc);
   } // of method

   //-----------------------------------------------------------------

   /**
    * Get the image to add for submenus. This image should be drawn such
    * that it is pointing up. We'll do the rotation automatically for you.
    */
   protected Image getSubmenuIcon() {
      if (submenuIconImage == null) {
         int                width  = 10;
         int                height = 10;
         submenuIconImage = new BufferedImage(width, height,
                                              BufferedImage.TYPE_INT_ARGB);
         Graphics g       = submenuIconImage.getGraphics();

         //// Make the background transparent.
         g.setColor(new Color(0, 0, 255, 0));
         g.fillRect(0, 0, width, height);

         g.setColor(LEGEND_COLOR);
         g.fillOval(1, 1, width-2, height-2);

         /*
         Polygon  p       = new Polygon();

         p.addPoint(0, height);
         p.addPoint(width / 2, 0);
         p.addPoint(width, height);

         g.setColor(LEGEND_COLOR);
         g.fillPolygon(p);
         */
      }
      return (submenuIconImage);
   } // of method

   //===   DISPLAY METHODS   ===================================================
   //===========================================================================



   //===========================================================================
   //===   SERIALIZATION METHODS   =============================================

   //// This serialization code always gets unread-bytes errors, although
   //// I can't figure out why.

/*
   private void readObject(ObjectInputStream oistream)
        throws IOException, ClassNotFoundException {

      oistream.defaultReadObject();

      double x;
      double y;
      double w;
      double h;

      x = oistream.readDouble();
      y = oistream.readDouble();
      w = oistream.readDouble();
      h = oistream.readDouble();
      bigCircle.setFrame(x, y, w, h);

      x = oistream.readDouble();
      y = oistream.readDouble();
      w = oistream.readDouble();
      h = oistream.readDouble();
      smallCircle.setFrame(x, y, w, h);

      x = oistream.readDouble();
      y = oistream.readDouble();
      w = oistream.readDouble();
      h = oistream.readDouble();
      clipCircle.setFrame(x, y, w, h);

   } // of readObject

   //-----------------------------------------------------------------

   private void writeObject(ObjectOutputStream oostream)
        throws IOException {

      oostream.defaultWriteObject();

      //// Write out the big circle
      oostream.writeDouble(bigCircle.getX());
      oostream.writeDouble(bigCircle.getY());
      oostream.writeDouble(bigCircle.getWidth());
      oostream.writeDouble(bigCircle.getHeight());

      //// Write out the small circle
      oostream.writeDouble(smallCircle.getX());
      oostream.writeDouble(smallCircle.getY());
      oostream.writeDouble(smallCircle.getWidth());
      oostream.writeDouble(smallCircle.getHeight());

      //// Write out the clip circle
      oostream.writeDouble(clipCircle.getX());
      oostream.writeDouble(clipCircle.getY());
      oostream.writeDouble(clipCircle.getWidth());
      oostream.writeDouble(clipCircle.getHeight());

   } // of writeObject
*/
   //===   SERIALIZATION METHODS   =============================================
   //===========================================================================



   //===========================================================================
   //===   TOSTRING   ==========================================================

   public String toString() {
      return (strText);
   } // of toString

   //===   TOSTRING   ==========================================================
   //===========================================================================

} // of class

//==============================================================================

/*
Copyright (c) 2000 Regents of the University of California.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:

      This product includes software developed by the Group for User
      Interface Research at the University of California at Berkeley.

4. The name of the University may not be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
*/
