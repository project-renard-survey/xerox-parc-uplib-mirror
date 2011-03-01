/*
 *  This file is part of the "UpLib 1.7.11" release.
 *  Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
 *  
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *  
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *  
 *  You should have received a copy of the GNU General Public License along
 *  with this program; if not, write to the Free Software Foundation, Inc.,
 *  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

package com.parc.uplib.readup.application;

import com.parc.uplib.util.DataURL;
import com.parc.uplib.util.BrowserLauncher;

import javax.swing.JApplet;
import java.applet.*;
import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.datatransfer.*;
import java.awt.dnd.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.border.*;
import javax.imageio.*;


import com.parc.uplib.readup.uplibbinding.Repository;

class ClusterTransferHandler extends TransferHandler implements Icon {

    private Image dragImage;
    private Transferable transferable;

    public ClusterTransferHandler () {
        super();
    }
        
    public Transferable createTransferable (JComponent comp) {
        System.err.println("createTransferable(" + comp + ")");
        return transferable;
    }

    public void setTransferData (Transferable t, Image i) {
        transferable = t;
        dragImage = i;
    }

    public boolean importData (JComponent comp, Transferable t) {
        boolean status;

        if (comp instanceof Cluster) {
            Cluster c = (Cluster) comp;
            DataFlavor f = c.bestFlavor(t.getTransferDataFlavors());
            try {
                Object o = t.getTransferData(f);
                status = c.doDrop (o);
            } catch (UnsupportedFlavorException x) {
                // shouldn't happen, because we checked the flavor, but...
                x.printStackTrace(System.err);
                status = false;
            } catch (IOException x) {
                x.printStackTrace(System.err);
                status = false;
            }
        } else {
            status = super.importData(comp, t);
        }
        System.err.println("importData => " + status);
        return status;
    }

    public boolean canImport (JComponent comp, DataFlavor[] transferFlavors) {
        boolean status;
        if (comp instanceof Cluster)
            status = (((Cluster)comp).canImport(transferFlavors) != null);
        else
            status = super.canImport(comp, transferFlavors);
        System.err.println("canImport(" + comp + ") => " + status);
        return status;
    }

    public int getSourceActions (JComponent c) {
        if (transferable == null)
            return TransferHandler.NONE;
        else
            return TransferHandler.COPY;
    }

    public int getIconHeight () {
        if (dragImage != null)
            return dragImage.getHeight(null);
        else
            return 0;
    }

    public int getIconWidth () {
        if (dragImage != null)
            return dragImage.getWidth(null);
        else
            return 0;
    }

    public void paintIcon (Component c, Graphics g, int x, int y) {
        if (dragImage != null) {
            g.drawImage(dragImage, x, y, null);
        }
    }

    public Icon getVisualRepresentation (Transferable t) {
        if ((t == transferable) && (dragImage != null))
            return this;
        return null;
    }

    protected void exportDone (JComponent source,
                               Transferable data,
                               int action) {
        super.exportDone(source, data, action);
        if (data == transferable) {
            transferable = null;
            dragImage = null;
        }
        System.err.println("export done.");
    }
}

public class Cluster extends JPanel
    implements MouseListener,
               DropTargetListener, DragSourceListener, DragGestureListener, ActionListener {

    private static BufferedImage right_arrow;
    private static BufferedImage down_arrow;
    private static BufferedImage link_icon;

    static {
        try {
            right_arrow = DataURL.decode("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAALCAYAAABPhbxiAAAAN0lEQVR42mPg4uJigGEg+I/Mx4cZ0DUSqxmrRmI049RISDNejfg0E9SISzNtbKRfqJIVj8SmHACpyjGxX0ae7gAAAABJRU5ErkJggg==");
            down_arrow = DataURL.decode("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAOCAYAAAD5YeaVAAAAHklEQVR42mNgGDTgPwmYaA1E20C0k4j2A9GeHnkAAF4tI93csGXmAAAAAElFTkSuQmCC");
            link_icon = DataURL.decode("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAOCAYAAAD5YeaVAAAAHklEQVR42mNgGDTgPwmYaA1E20C0k4j2A9GeHnkAAF4tI93csGXmAAAAAElFTkSuQmCC");
        } catch (IOException x) {
            x.printStackTrace(System.err);
            System.exit(1);
        }
    }

    final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);
    final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);
    final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);
    final static Color DARK_COLOR = new Color(.439f, .475f, .490f);
    final static Color WHITE = new Color(1.0f, 1.0f, 1.0f);
    final static Color WHITE80 = new Color(1.0f, 1.0f, 1.0f, .8f);
    final static Color BLACK = new Color(0.0f, 0.0f, 0.0f);

    final static Color CATEGORY_BACKGROUND = new Color(0xFFFFCC);
    final static Color COLLECTION_BACKGROUND = new Color(0xFFCCFF);
    final static Color AUTHOR_BACKGROUND = new Color(0xCCFFFF);
    final static Color SEARCH_BACKGROUND = new Color(0xCCCCCC);

    static Cluster drag_source = null;  // if non-null, points to Cluster currently serving as the drag source
    static ClusterTransferHandler transfer_handler = new ClusterTransferHandler();

    private Object document_source;
    private ArrayList nodes;
    private String label;
    private boolean show_label = true;
    private Color label_color = BLACK;
    private Color label_background_color = BACKGROUND_COLOR;
    private Rectangle label_rect = null;
    private int label_width = 0;
    private Rectangle expand_button_rect = null;
    private AffineTransform zoom;
    private Point label_position;
    private int border_width = 0;
    private Color border_color = DARK_COLOR;
    private int node_spacing = 5;
    private boolean expanded = true;
    private boolean rounded = true;
    private int last_width = -1;
    private int last_height = -1;
    private ArrayList node_listeners;
    private Point drop_point = null;
    private Node clicked_node = null;
    private int node_area = 0;
    private boolean drop_pending = false;
    private JPopupMenu context_menu = null;

    private void setGroupNodes (Repository.DocumentGroup g) {
        nodes.clear();
        document_source = g;
        g.loadIcons();
        if (g instanceof Repository.Category) {
            label = "Category \"" + ((Repository.Category) g).getName() + "\"";
            setBackground(CATEGORY_BACKGROUND);
        } else if (g instanceof Repository.Collection) {
            label = "Collection \"" + ((Repository.Collection) g).getName() + "\"";
            setBackground(COLLECTION_BACKGROUND);
        } else if (g instanceof Repository.Author) {
            label = "Author \"" + ((Repository.Author) g).getName() + "\"";
            setBackground(AUTHOR_BACKGROUND);
        }
        for (Iterator i = g.iterator();  i.hasNext();) {
            Repository.Document d = (Repository.Document) (i.next());
            nodes.add(new Node(d, -1f));
        }
        setToolTipText(label);
    }

    public Cluster (Repository.DocumentGroup g) {
        super();
        setBackground(BLACK);
        setBorder(null);
        nodes = new ArrayList();
        node_listeners = new ArrayList();
        Node.setFontMetrics(getFontMetrics(getFont()));
        setPreferredSize(new Dimension(200, 200));
        label = null;
        zoom = new AffineTransform();
        setGroupNodes(g);
        label_color = BLACK;
        setOpaque(false);
        this.addMouseListener(this);
        this.setTransferHandler(transfer_handler);
        DragSource.getDefaultDragSource().createDefaultDragGestureRecognizer(this,
                                                                             DnDConstants.ACTION_COPY,
                                                                             this);
        setDropTarget(new DropTarget(this, DnDConstants.ACTION_COPY_OR_MOVE, this, true));
    }

    private void setQueryNodes (Repository.Search query) {
        document_source = query;
        nodes.clear();
        Repository.Search.Hit[] hits = null;
        try {
        	hits = query.getHits();
        } catch (IOException x) {
        	String msg = "com.parc.uplib.readup.application.Cluster.setQueryNodes got IOException calling query.getHits().  Error = ["+
        	x.toString()+"]";
        	System.err.println(msg);
        	x.printStackTrace(System.err);
        	return;
        }
        label = "Search \"" + query.getQuery() + "\"  (" + hits.length + " hits)";
        float maxscore = Float.MIN_VALUE;
        float minscore = Float.MAX_VALUE;
        for (int i = 0;  i < hits.length;  i++) {
            if (hits[i].score < minscore)
                minscore = hits[i].score;
            if (hits[i].score > maxscore)
                maxscore = hits[i].score;
        }
        if ((maxscore - minscore) > 0.1) {
            float scale = (maxscore - minscore);
            for (int i = 0;  i < hits.length;  i++) {
                nodes.add(new Node(hits[i].doc, (hits[i].score - minscore) / scale));
            }
        } else {
            for (int i = 0;  i < hits.length;  i++) {
                nodes.add(new Node(hits[i].doc, -1f));
            }
        }
        setToolTipText(label);
    }

    public Cluster (Repository.Search query) {
        super();
        setBackground(BLACK);
        setBorder(null);
        setBackground(SEARCH_BACKGROUND);
        zoom = new AffineTransform();
        Node.setFontMetrics(getFontMetrics(getFont()));
        setPreferredSize(new Dimension(200, 200));
        nodes = new ArrayList();
        node_listeners = new ArrayList();
        setQueryNodes(query);
        label_color = BLACK;
        setOpaque(false);
        this.addMouseListener(this);
        this.setTransferHandler(transfer_handler);
        DragSource.getDefaultDragSource().createDefaultDragGestureRecognizer(this,
                                                                             DnDConstants.ACTION_COPY,
                                                                             this);
        setDropTarget(new DropTarget(this, DnDConstants.ACTION_COPY_OR_MOVE, this, true));
    }
    
    public Object getDocumentSource () {
        return document_source;
    }

    private void layoutRow (Vector current_row, int current_row_height, int left, int top) {
        double scaling = zoom.getScaleX();
        int jx = (int) Math.round(left / scaling);
        int spacing = (int) Math.round(node_spacing / scaling);
        int bottom = (int) Math.round((top + current_row_height) / scaling);
        for (int j = 0;  j < current_row.size();  j++) {
            Node n = (Node) (current_row.get(j));
            n.y = bottom - n.height;
            n.x = jx;
            jx += (n.width + spacing);
        }
    }

    protected Dimension doLayout (int constraint, int orientation) {

        System.err.println("doing layout on " + this + " expanded = " + expanded);

        int w = 0;
        int h = 0;
        int x = border_width;
        int y = border_width;
        if ((label != null) && show_label) {
            FontMetrics fm = getFontMetrics(getFont());
            if (label_rect == null)
                label_rect = new Rectangle();
            label_rect.y = y;
            label_rect.height = fm.getHeight() + fm.getLeading();
            label_width = fm.stringWidth(label);
            if (label_position == null)
                label_position = new Point(x, 0);
            label_position.y = y + fm.getLeading() + fm.getAscent();
            y = (label_position.y + fm.getDescent() + fm.getLeading());
        }

        w = x;
        h = y;

        if (expanded) {

            node_area = 0;

            x += node_spacing;
            y += node_spacing;
            w = x;
            h = y;
            int current_row_height = 0;
            int current_row_width = 0;
            Vector current_row = new Vector();
            Object current_node;

            if (orientation == SwingConstants.VERTICAL) {

                for (int i = 0;  i < nodes.size();  i++) {
                    current_node = nodes.get(i);
                    Rectangle r = zoom.createTransformedShape((Shape) current_node).getBounds();
                    if ((current_row.size() > 0) &&
                        ((x + current_row_width + r.width + node_spacing + border_width) > constraint)) {
                        // finished this row
                        layoutRow(current_row, current_row_height, x, y);
                        y += (node_spacing + current_row_height);
                        w = Math.max(x + current_row_width, w);
                        // System.err.println("finished row of " + current_row.size() + " nodes; finished node " + (i - 1) + " of " + nodes.size() + " for width and height of " + w + ", " + y);
                        current_row.clear();
                        current_row_width = 0;
                        current_row_height = 0;
                        i--;        // consider this node again
                        continue;
                    }
                    current_row_width += (r.width + node_spacing);
                    current_row_height = Math.max(r.height, current_row_height);
                    current_row.add(current_node);
                    node_area += (r.width * r.height);
                }
                if (current_row.size() > 0) {
                    layoutRow(current_row, current_row_height, x, y);
                    y += (node_spacing + current_row_height);
                    w = Math.max(x + current_row_width, w);
                }
                h = y;
                
            } else if (orientation == SwingConstants.HORIZONTAL) {
                // TODO
                throw new RuntimeException("Horizontal layout not supported yet.");

            } else
                throw new RuntimeException("Odd orientation for Cluster:  " + orientation);

        }

        w += border_width;
        h += border_width;

        /*
          // this is done in setBounds()
        if ((label_rect != null) && (label != null) && show_label) {
            label_rect.width = Math.min(label_width, w - (2 * expand_button_rect.width));
            label_rect.x = (w - label_rect.width)/2;
            label_position.x = label_rect.x;
        }
        */

        Dimension d = new Dimension(w, h);
        System.err.println("preferred dimensions for " + this + " are " + d);
        setPreferredSize(d);
        return d;
    }

    public int getNodeArea () {
        return node_area;
    }

    public void setBorder (int thickness, Color color) {
        border_width = thickness;
        border_color = color;
        revalidate();
    }

    public void paintComponent (Graphics g) {
        // System.err.println("paintComponent in " + this);
        if ((last_width < 0) || (last_height < 0))
            return;
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g.create();
        if (border_width > 0) {
            g2.setColor(border_color);
            if (rounded)
                g2.fillRoundRect(0, 0, getWidth(), getHeight(), 10, 10);
            else
                g2.fillRect(0, 0, getWidth(), getHeight());
        }
        g2.setColor(getBackground());
        int rw = (border_width > 0) ? 8 : 10;
        if (rounded) {
            g2.fillRoundRect(border_width, border_width, getWidth() - (2 * border_width), getHeight() - (2 * border_width), rw, rw);
        } else
            g2.fillRect(border_width, border_width, getWidth() - (2 * border_width), getHeight() - (2 * border_width));
        if ((label != null) && show_label) {
            if (label_background_color != null) {
                g2.setColor(label_background_color);
                g2.fillRoundRect(border_width, border_width, getWidth() - (2 * border_width), label_rect.height, rw, rw);
            }
            // System.err.println("expanded is " + expanded + ", label_rect is " + label_rect + ", label_position is " + label_position);
            Shape oldclip = g.getClip();
            g2.setColor(label_color);
            g.clipRect(label_rect.x, label_rect.y, label_rect.width, label_rect.height);
            g2.drawString(label, label_position.x, label_position.y);
            g2.setClip(oldclip);
            BufferedImage ei = expanded ? down_arrow : right_arrow;
            g2.drawImage(ei, expand_button_rect.x, expand_button_rect.y, ei.getWidth(null), ei.getHeight(null), null);
        }                          
        if (expanded) {
            // System.err.println("original transform is " + g2.getTransform());
            AffineTransform t2 = (AffineTransform)(g2.getTransform().clone());
            t2.concatenate(zoom);
            g2.setTransform(t2);
            // System.err.println("zoomed tranform is " + g2.getTransform());
            for (int i = 0;  i < nodes.size();  i++) {
                Node n = (Node) (nodes.get(i));
                n.draw(g2, (n == clicked_node));
            }
        }
    }

    public void reLayout () {
        int cwidth = getWidth();
        int cheight = getHeight();
        // System.err.println("setBounds ClusterFrame " + cwidth + "," + cheight + ", insets " + getInsets());
        System.err.println("re-layout of " + this);
        setScale(1.0D);
        Dimension d = doLayout(cwidth, SwingConstants.VERTICAL);
        System.err.println("cluster " + d.width + "x" + d.height + "=" + (d.width * d.height) + " node area is " + getNodeArea() + ", our area is " + cwidth + "x" + cheight + "=" + (cwidth * cheight));
        double nsf = Math.sqrt((double) (cwidth * cheight) / (double) getNodeArea());
        while ((d.height > cheight) || (d.width > cwidth)) {
            System.err.println("cluster size " + d + ", set size " + cwidth + "," + cheight + ", changing current scaling " + getScale() + " to " + nsf);
            setScale(nsf);
            d = doLayout(cwidth, SwingConstants.VERTICAL);
            System.err.println("cluster " + d.width + "x" + d.height + "=" + (d.width * d.height) + " node area is " + getNodeArea());
            nsf = nsf * 0.9D;
        }
    }

    public void setBounds (int x, int y, int width, int height) {
        last_width = getWidth();
        last_height = getHeight();
        super.setBounds(x, y, width, height);
        // System.err.println("Cluster.setBounds(" + width + ", " + height + ") called");
        if ((width < 1) || (height < 1))
            return;
        if (((last_width >= 0) && (width != last_width)) || ((last_height >= 0) && (height != last_height))) {
            if ((label != null) && show_label) {
                label_rect.width = width - (2 * border_width) - 1;
                int erw = (int) Math.max(down_arrow.getWidth(null), right_arrow.getWidth(null));
                int erh = (int) Math.max(down_arrow.getHeight(null), right_arrow.getHeight(null));
                expand_button_rect = new Rectangle(border_width + 2, border_width + 2, erw, erh);
                label_position.x = Math.max(0, (width - label_width - (2 * (border_width + erw)))/2);
                label_rect.x = label_position.x;
                label_rect.width = width - label_position.x - border_width;
            }
            revalidate();
        }
    }

    public int newWidth(int w) {
        Dimension d = doLayout(w, SwingConstants.VERTICAL);
        return d.height;
    }

    public int newHeight(int h) {
        Dimension d = doLayout(h, SwingConstants.HORIZONTAL);
        return d.width;
    }

    public double getScale () {
        return zoom.getScaleX();
    }

    public void setScale (double factor) {
        zoom.setToScale(factor, factor);
    }

    public void scale (double factor) {
        zoom.scale(factor, factor);
    }

    public void showLabel (boolean show) {
        show_label = show;
    }

    public String getLabel () {
        return label;
    }

    public void setExpanded (boolean v) {
        expanded = v;
        revalidate();
        repaint();
    }

    public boolean getExpanded () {
        return expanded;
    }

    public Node onNode (Point p) {
        try {
            Point2D p2 = zoom.inverseTransform((Point2D) p, null);
            for (Iterator i = nodes.iterator();  i.hasNext();) {
                Node n = (Node) i.next();
                if (n.contains(p2))
                    return n;
            }
        } catch (NoninvertibleTransformException x) {
            x.printStackTrace(System.err);
        }            
        return null;
    }

    public Node onNode (MouseEvent e) {
        return onNode(e.getPoint());
    }

    public void mouseEntered (MouseEvent e) {
    }

    public void mouseExited (MouseEvent e) {
        if ((context_menu != null) && context_menu.isVisible()) {
            context_menu.setVisible(false);
            clicked_node = null;
            context_menu = null;
            repaint();
            return;
        }
    }

    public void mousePressed (MouseEvent e) {
        Node n = onNode(e);
        if ((context_menu != null) && context_menu.isVisible()) {
            context_menu.setVisible(false);
            context_menu = null;
        }
        if (clicked_node != n) {
            clicked_node = n;
            repaint();
        }
        if ((n != null) && (e.isPopupTrigger())) {
            Repository.Document doc = n.getDocument();
                
            if (doc != null) {
                context_menu = new JPopupMenu ();

                Repository.Action[] doc_functions = doc.getDocumentFunctions();
                JMenuItem item;

                for (int i = 0;  i < doc_functions.length; i++) {
                    item = new UpLibShowDoc.OurMenuItem(doc_functions[i], doc, doc_functions[i].getLabel(), -1);
                    item.addActionListener(this);
                    context_menu.add(item);
                }
                context_menu.show(this, e.getX(), e.getY());
            }
        }
    }

    public void mouseReleased (MouseEvent e) {
        if ((context_menu != null) && context_menu.isVisible()) {
            context_menu.setVisible(false);
            clicked_node = null;
            context_menu = null;
            repaint();
            return;
        }
        if ((clicked_node != null) && (clicked_node == onNode(e))) {
            Node n = clicked_node;
            clicked_node = null;
            repaint();
            Iterator i = node_listeners.iterator();
            while (i.hasNext()) {
                ((NodeListener) (i.next())).nodeClicked(n);
            }
        }
    }

    public void addNodeListener (NodeListener l) {
        node_listeners.add(l);
    }

    public void mouseClicked (MouseEvent e) {
        if ((expand_button_rect != null) && expand_button_rect.contains(e.getPoint())) {
            System.err.println("clicked on " + (expanded ? "contract" : "expand") + " \"" + label + "\"");
            setExpanded(!getExpanded());
        }
    }

    public String getToolTipText (MouseEvent e) {
        Node n = onNode(e);
        if (n != null)
            return n.getLabel();
        else
            return label;
    }

    public String toString() {
        return "Cluster[\"" + label + "\", " + getWidth() + "x" + getHeight() + "@" + getX() + "," + getY() + ", " + (expanded ? "expanded" : "closed") + "]";
    }


    // drag-and-drop key methods

    public boolean doDrop (Object o, Point drop_location) {
        if (o instanceof Node) {
            Node node = (Node) o;
            if (document_source instanceof Repository.Category) {
                // TODO:  add this category to the dropped document
                Repository.Category c = (Repository.Category) document_source;
                Repository.Document d = node.getDocument();
                System.err.println("Adding " + d + " to " + c);
                c.addDocument(d);
                setGroupNodes(c);
                reLayout();
                repaint();
                return true;
            } else if ((document_source instanceof Repository.PrestoCollection) ||
                       ((document_source instanceof Repository.Collection) &&
                        (!(document_source instanceof Repository.QueryCollection)))) {
                // Add this document to the collection
                Repository.Collection c = (Repository.Collection) document_source;
                Repository.Document d = node.getDocument();
                System.err.println("Adding " + d + " to " + c);
                try {
                    c.addDocument(d);
                } catch (IllegalArgumentException x) {
                    x.printStackTrace(System.err);
                    return false;
                }
                setGroupNodes(c);
                reLayout();
                repaint();
                return true;
            } else if (document_source instanceof Repository.Author) {
                return false;
            }
        }
        return false;
    }

    public boolean doDrop (Object o) {
        return doDrop(o, new Point(0, 0));
    }

    public DataFlavor canImport (DataFlavor[] flavors) {
        if (drag_source == this)
            return null;
        if ((document_source instanceof Repository.Category) ||
            (document_source instanceof Repository.PrestoCollection) ||
            ((document_source instanceof Repository.Collection) &&
             (!(document_source instanceof Repository.QueryCollection)))) {
            for (int i = 0;  i < flavors.length;  i++)
                if (Node.isSelectionFlavor(flavors[i]))
                    return Node.selectionFlavor;
        }
        return null;
    }

    public DataFlavor bestFlavor (DataFlavor[] flavors) {
        return Node.selectionFlavor;
    }

    // DragGestureListener methods

    public void dragGestureRecognized (DragGestureEvent dge) {
        System.err.println("dragGestureRecognized " + dge);
        if ((context_menu != null) && context_menu.isVisible())
            return;
        Point p = dge.getDragOrigin();
        Node drag_hotspot = onNode (p);
        if (drag_hotspot != null) {
            clicked_node = null;
            repaint();
            drag_source = this;
            Rectangle r = zoom.createTransformedShape((Shape) drag_hotspot).getBounds();
            Point drag_point = new Point(r.x - p.x, r.y - p.y);
            Image di = null;
            if (DragSource.isDragImageSupported()) {
                di = drag_hotspot.getIcon(this);
                if (di == null)
                    di = link_icon;
            }
            ((ClusterTransferHandler)(this.getTransferHandler())).setTransferData(drag_hotspot, di);
            DragSource ds = DragSource.getDefaultDragSource();
            if (DragSource.isDragImageSupported()) {
                System.err.println("drag image supported, di is " + ((di == link_icon) ? "link icon" : di.toString()));
                ds.startDrag(dge, null, di, drag_point, drag_hotspot, this);
            } else {
                System.err.println("drag image not supported");
                ds.addDragSourceListener(this);
                ((ClusterTransferHandler)(this.getTransferHandler()))
                    .exportAsDrag(this, dge.getTriggerEvent(), TransferHandler.COPY_OR_MOVE);
            }
        }
    }

    // DragSourceListener methods

    public void dragDropEnd (DragSourceDropEvent e) {
        System.err.println("dragDropEnd " + e);
        drag_source = null;
        ((ClusterTransferHandler)(this.getTransferHandler())).setTransferData(null, null);
        DragSource.getDefaultDragSource().removeDragSourceListener(this);
    }

    public void dragEnter (DragSourceDragEvent e) {
        System.err.println("dragEnter " + e);
    }

    public void dragOver (DragSourceDragEvent e) {
        // System.err.println("dragOver " + e);
    }

    public void dropActionChanged (DragSourceDragEvent e) {
        System.err.println("dropActionChanged " + e);
    }

    public void dragExit (DragSourceEvent e) {
        System.err.println("dragExit " + e);
        drag_source = null;
    }

    // DropTargetListener methods

    public void dragEnter (DropTargetDragEvent dtde) {
        // Called while a drag operation is ongoing, when the mouse pointer enters the operable part of the drop site for the DropTarget registered with this listener.
        boolean old_drop_pending = drop_pending;
        if (canImport(dtde.getCurrentDataFlavors()) != null) {
            drop_pending = true;
            dtde.acceptDrag(DnDConstants.ACTION_COPY);
        } else {
            drop_pending = false;
            dtde.rejectDrag();
        }
        if (old_drop_pending != drop_pending)
            repaint();
    }

    public void dragExit (DropTargetEvent dte) {
        // Called while a drag operation is ongoing, when the mouse pointer has exited the operable part of the drop site for the DropTarget registered with this listener.
        boolean old_drop_pending = drop_pending;
        drop_pending = false;
        if (old_drop_pending != drop_pending)
            repaint();
    }

    public void dragOver (DropTargetDragEvent dtde) {
        // Called when a drag operation is ongoing, while the mouse pointer is still over the operable part of the drop site for the DropTarget registered with this listener.
        // System.err.println("dragOver " + dtde);
    }

    public void drop (DropTargetDropEvent e) {
        // Called when the drag operation has terminated with a drop on the operable part of the drop site for the DropTarget registered with this listener.
        System.err.println("dropping " + e.getTransferable());
        Transferable t = e.getTransferable();
        DataFlavor f = canImport(t.getTransferDataFlavors());
        System.err.println("DataFlavor is " + f);
        if (f != null) {
            System.err.println("importing " + t + " as " + f);
            e.acceptDrop(DnDConstants.ACTION_COPY);
            try {
                Object o = t.getTransferData(f);
                e.dropComplete(doDrop(o, e.getLocation()));
            } catch (UnsupportedFlavorException x) {
                x.printStackTrace(System.err);
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
        } else {
            System.err.println("Can't import " + t);
            e.rejectDrop();
        }
    }

    public void dropActionChanged (DropTargetDragEvent dtde) {
        // Called if the user has modified the current drop gesture.
        System.err.println("dropActionChanged " + dtde);
    }

    // ActionListener methods

    public void actionPerformed (ActionEvent e) {
        if (e.getSource() instanceof UpLibShowDoc.OurMenuItem) {
            UpLibShowDoc.OurMenuItem item = (UpLibShowDoc.OurMenuItem) (e.getSource());
            Repository.Document doc = (Repository.Document) item.reference;
            if (item.action != null) {
                String url = item.action.getURLString();
                if (url != null) {
                    if (doc != null)
                        url = url.replaceAll("%s", doc.getID());
                    // System.err.println("URL is \"" + url + "\"");
                    try {
                        BrowserLauncher.openURL(url);
                    } catch (Exception x) {
                        x.printStackTrace(System.err);
                    }
                }
            }
            if (clicked_node != null) {
                clicked_node = null;
                repaint();
            }
        }
    }

}

class ClusterFrame extends JInternalFrame implements ComponentListener, ActionListener {

    private Cluster cluster = null;
    private boolean shrink_wrap = false;
    JTextField query_widget = null;

    public ClusterFrame (Cluster c, boolean shrink_wrap) {
        super("", true, true, true, true);
        cluster = c;
        this.shrink_wrap = shrink_wrap;
        setTitle(cluster.getLabel());
        cluster.showLabel(false);
        cluster.setScale(1.0D);
        Container cp = getContentPane();
        cluster.addComponentListener(this);
        Object dsrc = c.getDocumentSource();
        System.err.println("document_source is " + dsrc);
        cp.setLayout(new BoxLayout(cp, BoxLayout.Y_AXIS));
        Dimension d2 = new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE);
        cluster.setMaximumSize(d2);
        if (dsrc instanceof Repository.Search) {
            query_widget = new JTextField(((Repository.Search)dsrc).getQuery());
            Dimension d = query_widget.getPreferredSize();
            d.width = Integer.MAX_VALUE;
            query_widget.setMaximumSize(d);
            query_widget.addActionListener(this);
            query_widget.setActionCommand("modify_query");
            cp.add(query_widget);
            cp.add(cluster);
        } else {
            cp.add(cluster);
        }
        setBackground(c.getBackground());
        setOpaque(true);
        Dimension d = getSize();
        if ((d.width > 0) && (d.height > 0))
            cluster.setBounds(0, 0, d.width, d.height);
    }

    // ComponentListener methods

    public void componentHidden(ComponentEvent e) {
        // Invoked when the component has been made invisible.
    }

    public void componentMoved(ComponentEvent e) {
        // Invoked when the component's position changes.
    }

    public void componentResized(ComponentEvent e) {
        // Invoked when the component's size changes.
        Component c = e.getComponent();
        if (c == cluster) {
            ((Cluster)c).reLayout();
            repaint();
        }
    }

    public void componentShown(ComponentEvent e) {
        // Invoked when the component has been made visible.
    }

    // ActionListener method

    public void actionPerformed (ActionEvent e) {
        if (e.getActionCommand().equals("modify_query")) {
            Container cp = getContentPane();
            Rectangle cluster_bounds = cluster.getBounds();
            Dimension d = cluster.getMaximumSize();
            cp.remove(cluster);
            Repository r = ((Repository.Search) cluster.getDocumentSource()).getRepository();
            cluster = new Cluster(r.search(query_widget.getText(), 0.0f, true));
            setTitle(cluster.getLabel());
            cluster.showLabel(false);
            cluster.setScale(1.0D);
            cluster.setMaximumSize(d);
            cluster.addComponentListener(this);
            cluster.setBounds(cluster_bounds);
            cp.add(cluster);
            repaint();
        }
    }
}

class ClusterList extends JPanel implements Scrollable {

    private int orientation = SwingConstants.VERTICAL;

    public ClusterList (int orientation) {
        super();
        setLayout(null);
        this.orientation = orientation;
        setPreferredSize(new Dimension(200, 200));
        setBackground(Cluster.BLACK);
    }

    public void paintComponent(Graphics g) {
        super.paintComponent(g);
        g.setColor(getBackground());
        g.fillRect(0, 0, getWidth(), getHeight());        
    }

    public Dimension getPreferredScrollableViewportSize() {
        return getPreferredSize();
    }

    public int getScrollableUnitIncrement (Rectangle f, int orientation, int direction) {
        // TODO
        return 200;
    }
            
    public int getScrollableBlockIncrement (Rectangle f, int orientation, int direction) {
        if ((orientation == SwingConstants.VERTICAL) && (this.orientation == SwingConstants.VERTICAL)) {
            if (direction < 0)
                return Math.min(f.y, f.height);
            else
                return Math.min(getHeight() - (f.y + f.height), f.height);
        } else if ((orientation == SwingConstants.HORIZONTAL) && (this.orientation == SwingConstants.HORIZONTAL)) {
            // TODO
            throw new RuntimeException("not implemented");
        }
        return 0;
    }
            
    public boolean getScrollableTracksViewportWidth() {
        return (orientation == SwingConstants.VERTICAL);
    }

    public boolean getScrollableTracksViewportHeight() {
        return (orientation == SwingConstants.HORIZONTAL);
    }

    public Dimension doLayout (int width, int height) {
        Component[] clusters = getComponents();
        int position = 0;
        if (orientation == SwingConstants.VERTICAL) {
            for (int i = 0;  i < clusters.length;  i++) {
                Cluster c = (Cluster) clusters[i];
                int h = c.newWidth(width);
                c.setBounds(0, position, width, h);
                position += h;
            }
            return new Dimension(width, position);
        } else if (orientation == SwingConstants.HORIZONTAL) {
            for (int i = 0;  i < clusters.length;  i++) {
                Cluster c = (Cluster) clusters[i];
                int w = c.newHeight(height);
                c.setBounds(position, 0, w, height);
                position += w;
            }
            return new Dimension(position, height);
        }
        return null;
    }

    public void doLayout() {
        System.err.println("doLayout " + this);
        Dimension d = doLayout(getWidth(), getHeight());
        setPreferredSize(d);
        System.err.println("new preferred size for ClusterList is " + d);
        if ((d.width != getWidth()) || (d.height != getHeight())) {
            Container c = getParent();
            if (c instanceof JViewport)
                setBounds(getX(), getY(), d.width, d.height);
            else
                revalidate();
        }
    }

    public void setBounds (int x, int y, int width, int height) {
        System.err.println("setBounds ClusterList " + width + "," + height);
        int old_width = getWidth();
        int old_height = getHeight();
        super.setBounds(x, y, width, height);
        if (((orientation == SwingConstants.VERTICAL) && (width != old_width)) ||
            ((orientation == SwingConstants.HORIZONTAL) && (height != old_height))) { 
            doLayout();
        }
    }

    public void prepend(Cluster c) {
        add(c, 0);
        doLayout();
    }

    public void addCluster(Cluster c) {
        add(c);
        doLayout();
    }
}
