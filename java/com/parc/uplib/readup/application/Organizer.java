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

package com.parc.uplib.readup.application;

import com.parc.uplib.util.Configurator;
import com.parc.uplib.util.BrowserLauncher;
import com.parc.uplib.util.EmacsKeymap;
import com.parc.uplib.util.DataURL;

import javax.swing.JApplet;
import javax.swing.tree.*;
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
import java.awt.datatransfer.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.border.*;
import javax.imageio.*;
import java.net.*;
import javax.net.ssl.*;
import javax.security.cert.*;

import com.parc.uplib.readup.uplibbinding.*;

class DocGroup implements Transferable, Serializable {

    static final String ourFlavorType = DataFlavor.javaSerializedObjectMimeType +
        ";class=com.parc.uplib.readup.application.DocGroup";
    public static DataFlavor selectionFlavor = null;
    public static DataFlavor urlFlavor = null;
    public static DataFlavor[] selection_flavors = null;
    static {
        try {
            selectionFlavor = new DataFlavor(ourFlavorType);
            urlFlavor = new DataFlavor("application/x-java-url;class=java.net.URL", "standard URL");
            selection_flavors = new DataFlavor[] { selectionFlavor, urlFlavor };
        } catch (ClassNotFoundException e) {
            e.printStackTrace(System.err);
        }
    }

    public Repository.DocumentGroup group;

    public DocGroup (Repository.DocumentGroup docgroup) {
        group = docgroup;
    }

    // methods for Transferable

    public static boolean isURLFlavor (DataFlavor f) {
        return (f.getMimeType().startsWith("application/x-java-url;"));
    }

    public static boolean isSelectionFlavor (DataFlavor f) {
        return (selectionFlavor.equals(f));
    }

    public boolean isDataFlavorSupported (DataFlavor flavor) {
        System.err.println("isDataFlavorSupported(" + flavor + ")");
        return (isSelectionFlavor(flavor) || isURLFlavor(flavor));
    }

    public DataFlavor[] getTransferDataFlavors() {
        return selection_flavors;
    }

    public Object getTransferData (DataFlavor flavor) throws UnsupportedFlavorException, IOException {

        // System.err.println("getTransferData(" + flavor + ")");

        if (isSelectionFlavor(flavor)) {

            return this;

        } else if (isURLFlavor(flavor)) {

            return new URL(group.getURLString());

        } else

            throw new UnsupportedFlavorException(flavor);
    }

    // for Serializable
    
    private void writeObject (ObjectOutputStream o) throws IOException {
        System.err.println("URL for " + group + " is " + group.getURLString());
        o.writeObject(new URL(group.getURLString()));
    }

    private void readObject (ObjectInputStream o) throws IOException, ClassNotFoundException {
        URL u = (URL) o.readObject();
        group = (Repository.DocumentGroup) Repository.get(u);
        System.err.println("read group " + group + " from URL " + u);
    }
}

class Workspace extends JPanel implements NodeListener, DropTargetListener {

    static AccessPanel drag_source;
    static Icon closed_node_icon;
    static Icon open_node_icon;
    static Icon leaf_node_icon;

    static {
        try {
            closed_node_icon = new ImageIcon("/sparrow-right-triangle.png");
            open_node_icon = new ImageIcon("/sparrow-down-triangle.png");
            leaf_node_icon = open_node_icon;
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
    }

    public interface DocumentOpener {
        public JComponent open (Repository.Document d, int page_index) throws IOException;
        public void open (String url) throws Exception;
        public void open (URL url) throws Exception;
    }            

    class WorkspaceTransferHandler extends TransferHandler {

        Transferable transferable;

        public WorkspaceTransferHandler () {
            super();
        }

        public void setTransferable (Transferable t) {
            transferable = t;
        }

        public boolean canImport(JComponent comp, DataFlavor[] transferFlavors) {
            // Indicates whether a component would accept an import of the given set of data flavors prior to actually attempting to import it.
            return super.canImport(comp, transferFlavors);
        }

        protected Transferable createTransferable(JComponent c) {
            return transferable;
        }

        protected void exportDone(JComponent source, Transferable data, int action) {
            // Invoked after data has been exported.
            super.exportDone(source, data, action);
            if (data == transferable)
                transferable = null;
        }

        public Icon getVisualRepresentation(Transferable t) {
            // Returns an object that establishes the look of a transfer.
            return super.getVisualRepresentation(t);
        }
    }

    
    private static class DocGroupTreeNode extends DefaultMutableTreeNode {
        public DocGroupTreeNode (Repository.DocumentGroup n) {
            super(n);
        }
        public String toString() {
            Repository.DocumentGroup dg = (Repository.DocumentGroup) getUserObject();
            return dg.getName() + " (" + Integer.toString(dg.size()) + ")";
        }
    }

    class AccessPanel extends Box implements ActionListener, DragSourceListener, DragGestureListener {

        private JTextField query_widget;
        private JTree categories_view;
        private Repository repo;
        
        class CategoryTreeWatcher extends MouseAdapter {

            private void groupSelected (Repository.DocumentGroup group, int num_clicks, int click_modifiers) {
                System.err.println("group " + group + " selected, num_clicks is " + num_clicks + ", click_modifiers is " + click_modifiers);
                if ((click_modifiers & MouseEvent.ALT_DOWN_MASK) == MouseEvent.ALT_DOWN_MASK) {
                    addCluster(new Cluster(group));
                }
            }

            public void mouseClicked(MouseEvent e) {
                int selRow = categories_view.getRowForLocation(e.getX(), e.getY());
                TreePath selPath = categories_view.getPathForLocation(e.getX(), e.getY());
                if (selRow != -1) {
                    Object obj = selPath.getLastPathComponent();
                    System.err.println("obj is " + obj);
                    if (obj instanceof DocGroupTreeNode) {
                        Repository.DocumentGroup group = (Repository.DocumentGroup) ((DocGroupTreeNode) obj).getUserObject();
                        groupSelected(group, e.getClickCount(), e.getModifiersEx());
                    }
                }
            }

        }

        public AccessPanel (Repository repo) {
            super(BoxLayout.Y_AXIS);

            this.repo = repo;
            add(new JLabel(repo.getName()));

            query_widget = new JTextField("");
            Dimension d = query_widget.getPreferredSize();
            d.width = Integer.MAX_VALUE;
            query_widget.setMaximumSize(d);
            query_widget.addActionListener(this);
            query_widget.setActionCommand("search");
            add(query_widget);

            MutableTreeNode root = new DefaultMutableTreeNode(repo.getName());
            DefaultMutableTreeNode group = new DefaultMutableTreeNode("Collections");
            TreePath initially_open = new TreePath (new Object[] { root, group });
            root.insert(group, 0);
            group.setAllowsChildren(true);
            Iterator i = repo.getCollections();
            int counter = 0;
            while (i.hasNext()) {
                Repository.Collection c = (Repository.Collection) (i.next());
                group.insert(new DocGroupTreeNode(c), counter);
                counter++;
            }

            group = new DefaultMutableTreeNode("Categories");
            group.setAllowsChildren(true);
            root.insert(group, 1);
            i = repo.getCategories();
            while (i.hasNext()) {
                Repository.Category c = (Repository.Category) (i.next());
                if (c.getParent() == null)
                    addCategory(c, group);
            }
            group = new DefaultMutableTreeNode("Authors");
            group.setAllowsChildren(true);
            root.insert(group, 2);
            i = repo.getAuthors();
            counter = 0;
            while (i.hasNext()) {
                Repository.Author c = (Repository.Author) (i.next());
                group.insert(new DocGroupTreeNode(c), counter);
                counter++;
            }
            DefaultTreeModel model = new DefaultTreeModel(root);
            DefaultTreeCellRenderer tcr = new DefaultTreeCellRenderer();
            // tcr.setLeafIcon(leaf_node_icon);
            // tcr.setClosedIcon(closed_node_icon);
            // tcr.setOpenIcon(open_node_icon);

            categories_view = new JTree(model);
            categories_view.setRootVisible(false);
            categories_view.setCellRenderer(tcr);
            categories_view.setTransferHandler(new WorkspaceTransferHandler());
            categories_view.setDragEnabled(true);
            // categories_view.expandRow(0);
            categories_view.expandPath(initially_open);            
            DragSource.getDefaultDragSource().createDefaultDragGestureRecognizer(categories_view,
                                                                                 DnDConstants.ACTION_COPY,
                                                                                 this);
            categories_view.addMouseListener(new CategoryTreeWatcher());
            JScrollPane jsp = new JScrollPane(categories_view,
                                              JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED,
                                              JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
            jsp.getViewport().setScrollMode(JViewport.BLIT_SCROLL_MODE);
            jsp.setVisible(true);
            add(jsp);
        }
        
        private void addCategory (Repository.Category c, MutableTreeNode parent) {
            System.err.println("adding " + c.getName());
            DocGroupTreeNode tn = new DocGroupTreeNode(c);
            parent.insert(tn, parent.getChildCount());
            Vector subcategories = c.getSubcategories();
            if (subcategories.size() > 0) {
                for (int i = 0;  i < subcategories.size();  i++)
                    addCategory((Repository.Category)(subcategories.get(i)), tn);
            }
        }

        // ActionListener methods

        public void actionPerformed (ActionEvent e) {
            if (e.getActionCommand().equals("search")) {
                addCluster(new Cluster(repo.search(query_widget.getText(), 0.0f, true)));
            }
        }

        // DragGestureListener methods

        public Repository.DocumentGroup getDocumentGroup (Point p) {
            int selRow = categories_view.getRowForLocation(p.x, p.y);
            TreePath selPath = categories_view.getPathForLocation(p.x, p.y);
            if (selRow != -1) {
                Object obj = selPath.getLastPathComponent();
                System.err.println("obj is " + obj);
                if (obj instanceof DocGroupTreeNode)
                    return (Repository.DocumentGroup) ((DocGroupTreeNode) obj).getUserObject();
            }
            return null;
        }

        public void dragGestureRecognized (DragGestureEvent dge) {
            System.err.println("dragGestureRecognized " + dge);
            Point p = dge.getDragOrigin();
            Repository.DocumentGroup drag_hotspot = getDocumentGroup(p);
            if (drag_hotspot != null) {
                drag_source = this;
                WorkspaceTransferHandler th = (WorkspaceTransferHandler) ((JComponent)(dge.getComponent())).getTransferHandler();
                DocGroup dg = new DocGroup(drag_hotspot);
                th.setTransferable(dg);
                DragSource ds = DragSource.getDefaultDragSource();
                System.err.println("dragging " + drag_hotspot);
                if (true) {
                    ds.startDrag(dge, null, null, p, dg, this);
                } else {
                    ds.addDragSourceListener(this);
                    th.exportAsDrag((JComponent) (dge.getComponent()), dge.getTriggerEvent(), TransferHandler.COPY_OR_MOVE);
                }
            }
        }

        // DragSourceListener methods

        public void dragDropEnd (DragSourceDropEvent e) {
            System.err.println("dragDropEnd " + e);
            drag_source = null;
            ((WorkspaceTransferHandler)(((JComponent)(e.getDragSourceContext().getComponent())).getTransferHandler())).setTransferable(null);
            DragSource.getDefaultDragSource().removeDragSourceListener(this);
        }

        public void dragEnter (DragSourceDragEvent e) {
            System.err.println("dragEnter " + e);
        }

        public void dragOver (DragSourceDragEvent e) {
            System.err.println("dragOver " + e);
        }

        public void dropActionChanged (DragSourceDragEvent e) {
            System.err.println("dropActionChanged " + e);
        }

        public void dragExit (DragSourceEvent e) {
            System.err.println("dragExit " + e);
            drag_source = null;
        }
    }

    private Vector repos;       // vector of Repository instances
    private JDesktopPane desktop;
    private Point next_pos = new Point(0, 0);
    private DocumentOpener doc_opener = null;

    public void setDocumentOpener (DocumentOpener d) {
        doc_opener = d;
    }

    private void addCluster (Cluster c, Point pos) {
        getTopLevelAncestor().setCursor(Cursor.getPredefinedCursor(Cursor.WAIT_CURSOR));
        c.addNodeListener(this);
        ClusterFrame f = new ClusterFrame(c, true);
        f.setSize(desktop.getWidth()/3, desktop.getHeight()/3);
        desktop.add(f);
        f.setLocation(pos);
        f.setVisible(true);
        desktop.setSelectedFrame(f);
        getTopLevelAncestor().setCursor(null);
    }

    private void addCluster (Cluster c) {
        addCluster(c, next_pos);
        next_pos.x += 50;
        next_pos.y += 50;
    }

    public void nodeClicked (Node n) {
        if (doc_opener != null) {
            try {
                JComponent j = doc_opener.open(n.getDocument(), -1);
                if (j.getTopLevelAncestor() == null) {
                    JFrame j2 = new JFrame(n.getDocument().getTitle());
                    j2.getContentPane().add(j);
                    j2.pack();
                    j2.setDefaultCloseOperation(WindowConstants.DISPOSE_ON_CLOSE);
                    j2.setVisible(true);
                }
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }                                               
        }
    }

    // drag-and-drop key methods

    public boolean doDrop (Object dropped, Point p) {
        System.err.println(dropped.toString() + " dropped at " + p);

        if (dropped instanceof DocGroup) {
            Repository.DocumentGroup group = ((DocGroup)dropped).group;
            System.err.println("adding " + group);
            Cluster c = new Cluster(group);
            addCluster(c, p);
            return true;
        } else if (dropped instanceof URL) {
            Object o = Repository.get((URL) dropped);
            if ((o != null) && (o instanceof Repository.DocumentGroup)) {
                Cluster c = new Cluster((Repository.DocumentGroup) o);
                addCluster(c, p);
                return true;
            }
        }
        return false;
    }

    public DataFlavor canImport (DataFlavor[] flavors) {
        DataFlavor[] preferred = DocGroup.selection_flavors;
        for (int j = 0;  j < preferred.length;  j++) {
            for (int i = 0;  i < flavors.length;  i++)
                if (preferred[j].equals(flavors[i]))
                    return preferred[j];
        }
        return null;
    }

    // DropTargetListener methods

    public void dragEnter (DropTargetDragEvent dtde) {
        // Called while a drag operation is ongoing, when the mouse pointer enters the operable part of the drop site for the DropTarget registered with this listener.
        System.err.println("dragEnter " + dtde);
    }

    public void dragExit (DropTargetEvent dte) {
        // Called while a drag operation is ongoing, when the mouse pointer has exited the operable part of the drop site for the DropTarget registered with this listener.
        System.err.println("dragExit " + dte);
    }

    public void dragOver (DropTargetDragEvent dtde) {
        // Called when a drag operation is ongoing, while the mouse pointer is still over the operable part of the drop site for the DropTarget registered with this listener.
        // System.err.println("dragOver " + dtde);
    }

    public void drop (DropTargetDropEvent e) {
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


    private void createGUI () {

        AccessPanel access_panel = new AccessPanel((Repository) (repos.get(0)));

        desktop = new JDesktopPane();
        desktop.setDropTarget(new DropTarget(desktop, DnDConstants.ACTION_COPY, this, true));
        // desktop.setBackground(Cluster.DARK_COLOR);

        setLayout(null);
        add(new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, false, access_panel, desktop));
    }

    public void setBounds (int x, int y, int width, int height) {
        super.setBounds(x, y, width, height);
        Component[] parts = getComponents();
        for (int i = 0;  i < parts.length;  i++)
            parts[i].setBounds(0, 0, width, height);
    }

    public Workspace (Vector repos) {
        this.repos = repos;
        createGUI();
    }
}

class Organizer {
    
    public static void main (String[] argv) {
        try {

            Repository r = new Repository(new URL(argv[0]), (String) argv[1]);
            r.readIndexFile();
            Repository.Search search = r.search(argv[2], 0.1f, true);

            UpLibShowDoc app = new UpLibShowDoc(new Closer(), null,
                                                argv[0], argv[1], null, null,
                                                false, 0.0f, 300, true, false,
                                                new Configurator());

                
            /*
            Cluster c = new Cluster(search);
            c.scale(.5);
            c.setBorder(5, Cluster.UPLIB_ORANGE);
            System.err.println("created cluster...");
            ClusterList cl = new ClusterList(SwingConstants.VERTICAL);
            cl.add(c);
            c = new Cluster(r.search(argv[3], 0.1f, true));
            c.scale(.7);
            c.setBorder(5, Cluster.TOOLS_COLOR);
            cl.add(c);
            c = new Cluster(r.getCategory("paper"));
            c.scale(.3);
            c.setBorder(5, Cluster.DARK_COLOR);
            cl.add(c);
            JScrollPane jsp = new JScrollPane(cl,
                                              JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED,
                                              JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
            jsp.getViewport().setScrollMode(JViewport.BLIT_SCROLL_MODE);
            jsp.setVisible(true);
            */

            System.err.println("making frame...");
            // UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName());

            // Make sure we use the screen-top menu on OS X
            System.setProperty("com.apple.macos.useScreenMenuBar", "true");
            System.setProperty("apple.laf.useScreenMenuBar", "true");

            JFrame f = new JFrame(argv[0]);
            Vector repos = new Vector();
            repos.add(r);
            Workspace w = new Workspace(repos);
            w.setPreferredSize(new Dimension(900, 800));
            w.setDocumentOpener(app);
            f.getContentPane().add(w);
            f.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
            f.pack();
            f.setVisible(true);

        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
    }
}
