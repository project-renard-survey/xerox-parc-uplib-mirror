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

import java.lang.reflect.*;
import java.awt.*;
import java.awt.image.*;
import java.awt.event.*;
import java.awt.datatransfer.*;
import java.io.*;
import javax.swing.*;
import javax.swing.text.*;
import javax.swing.text.html.*;
import java.util.*;
import javax.swing.event.*;
import javax.imageio.*;

public class EmacsKeymap {

    private static class MultiPaste extends TextAction {

        final private boolean is_mac = System.getProperty("os.name").toLowerCase().startsWith("mac");

        public MultiPaste (String name) {
            super(name);
        }

        public void actionPerformed (ActionEvent e) {
            JTextComponent tc = getTextComponent(e);
            Transferable tf = Toolkit.getDefaultToolkit().getSystemClipboard().getContents(null);
            System.err.println("tc is " + tc + ", tf is " + tf);
            try {
                if (tf != null && tc != null) {
                    if ((tc instanceof JTextPane) && tf.isDataFlavorSupported(DataFlavor.imageFlavor)) {
                        // image
                        System.err.println("pasting image...");
                        DataFlavor[] flavors = tf.getTransferDataFlavors();
                        for (int i = 0;  i < flavors.length;  i++)
                            System.err.println ("" + flavors[i]);
                        Image img = null;
                        if (is_mac)
                            img = getMacImage(tf);
                        else
                            img = (Image) tf.getTransferData(DataFlavor.imageFlavor);
                        if (img != null) {
                            // System.err.println("image is " + img + ", subclass of Image is " + (img instanceof Image));
                            ImageIcon icon = new ImageIcon(img);
                            // System.err.println("icon is " + icon);
                            ((JTextPane)tc).insertIcon(icon);
                            // System.err.println("inserted icon");
                        }
                    } else if (tf.isDataFlavorSupported(DataFlavor.stringFlavor)) {
                        String s = (String) tf.getTransferData(DataFlavor.stringFlavor);
                        Style element_style = null;
                        if (s.startsWith("http:") || s.startsWith("https:") || s.startsWith("ftp:")) {
                            // URL
                            element_style = ((StyledDocument)(tc.getDocument())).getStyle("URL");
                            s = s.trim();       // strip whitespace on ends
                        } else {
                            // String
                        }
                        int offset = tc.getCaretPosition();
                        Document d = tc.getDocument();
                        d.insertString(offset, s, element_style);
                    }
                }
            } catch (UnsupportedFlavorException exc) {
                System.err.println("UnsupportedFlavorException while attempting to paste from the clipboard.");
                exc.printStackTrace(System.err);
            } catch (IOException exc) {
                System.err.println("IOException while attempting to paste from the clipboard.");
                exc.printStackTrace(System.err);
            } catch (BadLocationException exc) {
                System.err.println("BadLocationException while attempting to paste from the clipboard.");
                exc.printStackTrace(System.err);
            }
        }

	// Mac OS X's data transfer handling is horribly broken... we
	// need to use the "image/x-pict" MIME type and then Quicktime
	// for Java in order to obtain image data without problems.
        //
        // This code is from Amrit Aneja and Wayne Rasband, part of
        // the System_Clipboard ImageJ plug-in at NIH.  It's in the
        // public domain, according to
        // http://rsb.info.nih.gov/ij/disclaimer.html: "this software
        // is not subject to copyright protection and is in the public
        // domain."

	private Image getMacImage(Transferable t) {
            if (!isQTJavaInstalled()) {
                System.err.println("QuickTime for Java is not installed");
                return null;
            }
            Image img = null;
            DataFlavor[] d = t.getTransferDataFlavors();
            if (d==null || d.length==0)
                return null;
            try {
                Object is = t.getTransferData(d[0]);
                if (is==null || !(is instanceof InputStream)) {
                    System.err.println("Clipboad does not appear to contain an image");
                    return null;
                }
                img = getImageFromPictStream((InputStream)is);
            } catch (Exception e) {}
            return img;
        }

	// Converts a PICT to an AWT image using QuickTime for Java.
	// This code was contributed by Gord Peters.
	private Image getImageFromPictStream(InputStream is) {
            try {
                ByteArrayOutputStream baos= new ByteArrayOutputStream();
                // We need to strip the header from the data because a PICT file
                // has a 512 byte header and then the data, but in our case we only
                // need the data. --GP
                byte[] header= new byte[512];
                byte[] buf= new byte[4096];
                int retval= 0, size= 0;
                baos.write(header, 0, 512);
                while ( (retval= is.read(buf, 0, 4096)) > 0)
                    baos.write(buf, 0, retval);		
                baos.close();
                size = baos.size();
                if (size<=0)
                    return null;
                byte[] imgBytes= baos.toByteArray();
                // Again with the uglyness.  Here we need to use the Quicktime
                // for Java code in order to create an Image object from
                // the PICT data we received on the clipboard.  However, in
                // order to get this to compile on other platforms, we use
                // the Java reflection API.
                //
                // For reference, here is the equivalent code without
                // reflection:
                //
                //
                // if (QTSession.isInitialized() == false) {
                //     QTSession.open();
                // }
                // QTHandle handle= new QTHandle(imgBytes);
                // GraphicsImporter gi=
                //     new GraphicsImporter(QTUtils.toOSType("PICT"));
                // gi.setDataHandle(handle);
                // QDRect qdRect= gi.getNaturalBounds();
                // GraphicsImporterDrawer gid= new GraphicsImporterDrawer(gi);
                // QTImageProducer qip= new QTImageProducer(gid,
                //                          new Dimension(qdRect.getWidth(),
                //                                        qdRect.getHeight()));
                // return(Toolkit.getDefaultToolkit().createImage(qip));
                //
                // --GP
                Class c = Class.forName("quicktime.QTSession");
                Method m = c.getMethod("isInitialized", (Class[]) null);
                Boolean b= (Boolean)m.invoke(null, (Object[]) null);			
                if (b.booleanValue() == false) {
                    m= c.getMethod("open", (Class[]) null);
                    m.invoke(null, (Object[]) null);
                }
                c= Class.forName("quicktime.util.QTHandle");
                Constructor con = c.getConstructor(new Class[] {imgBytes.getClass() });
                Object handle= con.newInstance(new Object[] { imgBytes });
                String s= new String("PICT");
                c = Class.forName("quicktime.util.QTUtils");
                m = c.getMethod("toOSType", new Class[] { s.getClass() });
                Integer type= (Integer)m.invoke(null, new Object[] { s });
                c = Class.forName("quicktime.std.image.GraphicsImporter");
                con = c.getConstructor(new Class[] { type.TYPE });
                Object importer= con.newInstance(new Object[] { type });
                m = c.getMethod("setDataHandle",
                                new Class[] { Class.forName("quicktime.util." + "QTHandleRef") });
                m.invoke(importer, new Object[] { handle });
                m = c.getMethod("getNaturalBounds", (Class[]) null);
                Object rect= m.invoke(importer, (Object[]) null);
                c = Class.forName("quicktime.app.view.GraphicsImporterDrawer");
                con = c.getConstructor(new Class[] { importer.getClass() });
                Object iDrawer = con.newInstance(new Object[] { importer });
                m = rect.getClass().getMethod("getWidth", (Class[]) null);
                Integer width= (Integer)m.invoke(rect, (Object[]) null);
                m = rect.getClass().getMethod("getHeight", (Class[]) null);
                Integer height= (Integer)m.invoke(rect, (Object[]) null);
                Dimension d= new Dimension(width.intValue(), height.intValue());
                c = Class.forName("quicktime.app.view.QTImageProducer");
                con = c.getConstructor(new Class[] { iDrawer.getClass(), d.getClass() });
                Object producer= con.newInstance(new Object[] { iDrawer, d });
                if (producer instanceof ImageProducer)
                    return(Toolkit.getDefaultToolkit().createImage((ImageProducer)producer));
            } catch (Exception e) {
                System.err.println("QuickTime for java error:  " + e);
            }
            return null;
        }

	// Retuns true if QuickTime for Java is installed.
	// This code was contributed by Gord Peters.
	private boolean isQTJavaInstalled() {
            boolean isInstalled = false;
            try {
                Class c= Class.forName("quicktime.QTSession");
                isInstalled = true;
            } catch (Exception e) {}
            return isInstalled;
	}
    }

    private static class MultiAction extends TextAction {

        static Hashtable editor_actions = null;

        Action[] subactions;
        String name;

        public MultiAction (String name, String[] subaction_names) throws NoSuchFieldException {
            super(name);

            Action a;
            this.name = name;
            if (editor_actions == null) {
                Action[] actionsArray = new JTextField().getActions();
                editor_actions = new Hashtable();
                for (int i = 0;  i < actionsArray.length;  i++) {
                    a = actionsArray[i];
                    editor_actions.put(a.getValue(Action.NAME), a);
                }
            }
            this.subactions = new Action[subaction_names.length];
            for (int i = 0;  i < subaction_names.length;  i++) {
                a = (Action) editor_actions.get(subaction_names[i]);
                if (a != null)
                    this.subactions[i] = a;
                else
                    throw new NoSuchFieldException("no action named " + subaction_names[i]);
            }
        }

        public void actionPerformed (ActionEvent e) {
            // System.err.println("actionPerformed:  " + name + " " + e);
            for (int i = 0;  i < subactions.length;  i++)
                subactions[i].actionPerformed(e);
        }
    }

    private static class SetMark extends TextAction {

        public SetMark (String name) {
            super(name);
        }

        public void actionPerformed (ActionEvent e) {
            JTextComponent tc = getTextComponent(e);
            if (tc != null)
                tc.setCaretPosition(tc.getCaretPosition());
        }
    }

    public static BufferedImage convertImageIconToImage (ImageIcon icon) {
        Image img = icon.getImage();
        BufferedImage bi = new BufferedImage(img.getWidth(null), img.getHeight(null), BufferedImage.TYPE_INT_ARGB);
        Graphics g = bi.getGraphics();
        g.setColor(new Color(255, 255, 255, 0));
        g.fillRect(0, 0, bi.getWidth(null), bi.getHeight(null));
        g.drawImage(img, 0, 0, null);
        return bi;
    }

    private static class WriteAction extends TextAction {

        static final char[] hexdigits = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'};

        public WriteAction (String name) {
            super(name);
        }

        private static byte[] convertImageIconToPNGBytes (ImageIcon icon) {
            ByteArrayOutputStream bs = new ByteArrayOutputStream();
            BufferedImage bi = convertImageIconToImage(icon);
            try {
                ImageIO.write(bi, "PNG", bs);
                bs.flush();
            } catch (IOException exc) {
                exc.printStackTrace(System.err);
                return null;
            }
            return bs.toByteArray();
        }

        private static void showContents (Element e, int offset) {
            for (int i = 0;  i < offset;  i++)
                System.err.print("  ");
            System.err.print("Element " + e.toString().trim() + " \"" + e.getName() + "\" :");
            if (e.isLeaf()) {
                System.err.println("");
                String text = null;
                int start = e.getStartOffset();
                int end = e.getEndOffset();
                try {
                    text = e.getDocument().getText(start, end - start);
                } catch (BadLocationException exc) {
                    exc.printStackTrace(System.err);
                }
                AttributeSet attributes = e.getAttributes();
                for (int i = 0;  i < offset;  i++)
                    System.err.print("  ");
                System.err.println("<" + text + ">");
                Enumeration anames = attributes.getAttributeNames();
                while (anames.hasMoreElements()) {
                    Object key = anames.nextElement();
                    Object o = attributes.getAttribute(key);
                    for (int i = 0;  i < (offset + 1);  i++)
                        System.err.print("  ");
                    System.err.println(key.toString() + ": " + o.toString());
                    if ("icon".equals(key.toString()) && (o instanceof ImageIcon)) {
                        try {
                            byte[] pngimage = convertImageIconToPNGBytes((ImageIcon) o);
                            System.err.println("Image has " + pngimage.length + " bytes");
                            FileOutputStream fos = new FileOutputStream("/tmp/foo.png");
                            fos.write(pngimage);
                            fos.close();
                            int i;
                            for (i = 0;  i < pngimage.length;  i++) {
                                if ((i > 0) && ((i % 20) == 0))
                                    System.err.println("");
                                System.err.print(" " + hexdigits[(pngimage[i] >> 4) & 0x0F] + hexdigits[pngimage[i] & 0x0F]);
                            }
                            System.err.println("");
                        } catch (Exception exc) {
                            exc.printStackTrace(System.err);
                        }
                    }
                }
            } else {
                System.err.println("  (non-leaf)");
                for (int limit = e.getElementCount(), i = 0;  i < limit;  i++) {
                    Element el = e.getElement(i);
                    showContents(el, offset + 1);
                }
            }
        }

        public void actionPerformed (ActionEvent e) {
            JTextPane tc = (JTextPane) getTextComponent(e);
            try {
                /*
                Element[] roots = tc.getDocument().getRootElements();
                for (int i = 0;  i < roots.length;  i++)
                    showContents(roots[i], 0);
                */
                showContents(tc.getDocument().getDefaultRootElement(), 0);
            } catch (Exception exc) {
                exc.printStackTrace(System.err);
            }
        }
    }

    public static void setupEmacsKeymap () {

        try {
            final Action[] multiActions =
                {
                    new MultiAction("deleteToEndOfLine",
                                    new String[] {
                                        DefaultEditorKit.selectionEndLineAction,
                                        DefaultEditorKit.cutAction }),
                    new MultiAction("deleteToEndOfWord",
                                    new String[] {
                                        DefaultEditorKit.selectionEndWordAction,
                                        DefaultEditorKit.cutAction }),
                    new MultiPaste ("multiPaste"),
                    new SetMark ("setMark"),
                    new WriteAction ("writeAction"),
                };
            final JTextComponent.KeyBinding[] emacsBindings =
                {
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_B, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.selectionBackwardAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_F, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.selectionForwardAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_P, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.selectionUpAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_N, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.selectionDownAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_D, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.deleteNextCharAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_A, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.selectionBeginLineAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_E, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.selectionEndLineAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_F, InputEvent.META_MASK),
                                                  DefaultEditorKit.selectionNextWordAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_B, InputEvent.META_MASK),
                                                  DefaultEditorKit.selectionPreviousWordAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_W, InputEvent.CTRL_MASK),
                                                  DefaultEditorKit.cutAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_X, InputEvent.META_MASK),
                                                  DefaultEditorKit.cutAction),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_Y, InputEvent.CTRL_MASK),
                                                  //DefaultEditorKit.pasteAction
                                                  "multiPaste"),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_V, InputEvent.META_MASK),
                                                  //DefaultEditorKit.pasteAction
                                                  "multiPaste"),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_I, InputEvent.CTRL_MASK),
                                                  "writeAction"),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_K, InputEvent.CTRL_MASK),
                                                  "deleteToEndOfLine"),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_D, InputEvent.META_MASK),
                                                  "deleteToEndOfWord"),
                    new JTextComponent.KeyBinding(KeyStroke.getKeyStroke(KeyEvent.VK_SPACE, InputEvent.CTRL_MASK),
                                                  "setMark"),
                };
        
            Keymap k = JTextComponent.getKeymap(JTextComponent.DEFAULT_KEYMAP);
            Action[] actionsArray = new JTextField().getActions();
            Hashtable actions = new Hashtable();
            Action a;
            for (int i = 0;  i < actionsArray.length;  i++) {
                a = actionsArray[i];
                actions.put(a.getValue(Action.NAME), a);
            }
            for (int i = 0;  i < multiActions.length;  i++) {
                a = multiActions[i];
                actions.put(a.getValue(Action.NAME), a);
            }
            for (int i = 0;  i < emacsBindings.length;  i++) {
                k.removeKeyStrokeBinding(emacsBindings[i].key);
                a = (Action) actions.get(emacsBindings[i].actionName);
                if (a != null)
                    k.addActionForKeyStroke(emacsBindings[i].key, a);
            }
        } catch (Exception e) {
            e.printStackTrace(System.err);
        }

    }
}    
