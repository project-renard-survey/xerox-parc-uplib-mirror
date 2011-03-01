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
import com.parc.uplib.util.CertificateHandler;
import com.parc.uplib.util.ClientKeyManager;
import com.parc.uplib.util.FileBox;

import javax.swing.JApplet;
import java.applet.*;
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
import java.net.*;
import javax.net.ssl.*;
import javax.security.cert.*;

import javax.jnlp.ServiceManager;
import javax.jnlp.SingleInstanceService;
import javax.jnlp.SingleInstanceListener;
import javax.jnlp.BasicService;
import javax.jnlp.ClipboardService;

import com.parc.uplib.readup.widget.*;
import com.parc.uplib.readup.uplibbinding.*;

class Closer extends WindowAdapter {

    private HashMap wins;
    private HashMap docs;

    public Closer() {
        super();
        wins = new HashMap();
        docs = new HashMap();
    };

    public void add (Window value, DocViewer dv) {
        value.addWindowListener(this);
        wins.put(value, dv);
    }

    public void add (Window value, DocViewer dv, Repository.Document doc) {
        value.addWindowListener(this);
        wins.put(value, dv);
        docs.put(doc, dv);
    }

    public DocViewer get(Repository.Document doc) {
        return (DocViewer) docs.get(doc);
    }

    public Iterator iterator() {
        return wins.entrySet().iterator();
    }

    public boolean hasWindows () {
        return (!wins.isEmpty());
    }

    public void windowClosing (WindowEvent e) {
        Window w = e.getWindow();
        if (wins.containsKey(w)) {
            DocViewer dv = (DocViewer) (wins.get(w));
            if (dv != null)
                try {
                    for (Iterator i = docs.entrySet().iterator();  i.hasNext(); ) {
                        Map.Entry entry = (Map.Entry) i.next();
                        DocViewer dv2 = (DocViewer) entry.getValue();
                        if (dv2 == dv) {
                            Object doc = entry.getKey();
                            docs.remove(doc);                            
                        }
                    }
                    dv.finalize();
                } catch (Throwable t) {
                    t.printStackTrace(System.err);
                }
            wins.put(w, null);
        }
        w.dispose();
        System.err.println("Window closing event " + e + " on " + w);
    }

    public void windowClosed (WindowEvent e) {
        Window w = e.getWindow();
        if (wins.containsKey(w)) {
            wins.remove(w);
        }
    }

    public void finalizeAll () {
        Iterator i = wins.values().iterator();
        while (i.hasNext()) {
            DocViewer dv = (DocViewer) (i.next());
            if (dv != null)
                try {
                    for (Iterator i2 = docs.entrySet().iterator();  i.hasNext(); ) {
                        Map.Entry entry = (Map.Entry) i2.next();
                        DocViewer dv2 = (DocViewer) entry.getValue();
                        if (dv2 == dv) {
                            Object doc = entry.getKey();
                            docs.remove(doc);                            
                        }
                    }
                    dv.finalize();
                } catch (Throwable t) {
                    t.printStackTrace(System.err);
                }
        }
    }

    public void closeAll () {
        Iterator i = wins.keySet().iterator();
        while (i.hasNext()) {
            Window w = (Window)(i.next());
            this.windowClosing(new WindowEvent(w, WindowEvent.WINDOW_CLOSING));
        }
    }
}

class FileBoxHolder {
    private Repository repo;
    private FileBox box;
    public JFrame frame;
    private final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    public FileBoxHolder (FileBox b, Repository r) {
        this.box = b;
        this.repo = r;
        this.frame = null;
    }
    public JFrame getFrame(String title) {
        if (this.frame == null) {
            this.frame = new JFrame(title);
            JScrollPane jsp = new JScrollPane(box,
                                              JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED,
                                              JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
            jsp.getViewport().setScrollMode(JViewport.BLIT_SCROLL_MODE);
            jsp.getViewport().setBackground(BACKGROUND_COLOR);
            this.frame.getContentPane().add(jsp);
            this.frame.setDefaultCloseOperation(WindowConstants.HIDE_ON_CLOSE);
            this.frame.pack();
        }
        return this.frame;
    }
    public boolean match(Repository r) {
        return (this.repo == r);
    }
    public void setBox (FileBox b) {
        this.box = b;
    }
    public FileBox getBox() {
        return this.box;
    }
    public Repository getRepository() {
        return repo;
    }
    public void discard () {
        if (this.frame != null)
            this.frame.dispose();
        frame = null;
        box = null;
        repo = null;
    }
}

class MessagePane extends JDialog implements ActionListener {
    final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);
    final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);
    final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);
    final static Color DARK_COLOR = new Color(.439f, .475f, .490f);
    final static Color WHITE = new Color(1.0f, 1.0f, 1.0f);
    final static Color BLACK = new Color(0.0f, 0.0f, 0.0f);

    private String      mymessage;
    private Icon        myicon;
    private String      uplib_version = null;
    private String      mytitle;

    MessagePane (String title, String message) {
        super ((Frame) null, true);
        setBackground(TOOLS_COLOR);
        setDefaultCloseOperation(JDialog.DISPOSE_ON_CLOSE);
        mymessage = message;
        myicon = UpLibShowDoc.getIcon();
        uplib_version = UpLibShowDoc.getUpLibVersion();
        mytitle = title;
        // System.err.println("URL is " + repoURL + ", password is " + repoPassword);
        initComponents();
        pack();
        setLocationRelativeTo(null);
    }

    public void initComponents() {
        Box s;
        JLabel f;
        Font namefont = new Font("Serif", Font.BOLD, 14);
        Font boldfont = new Font("Serif", Font.BOLD, 12);
        Font smallfont = new Font("Serif", Font.PLAIN, 10);

        setTitle(mytitle);
	getContentPane().setBackground(TOOLS_COLOR);

        Box main = Box.createHorizontalBox();

        Box branding = Box.createVerticalBox();
        f = new JLabel(myicon);
        f.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalGlue());
        s.add(f);
        s.add(Box.createHorizontalGlue());
        branding.add(s);
//         f = new JLabel("ReadUp");
//         f.setHorizontalAlignment(SwingConstants.CENTER);
//         f.setBackground(TOOLS_COLOR);
//         f.setForeground(BLACK);
//         f.setFont(namefont);
//         s = Box.createHorizontalBox();
//         s.add(Box.createHorizontalGlue());
//         s.add(f);
//         s.add(Box.createHorizontalGlue());
//         branding.add(s);
//         branding.add(Box.createVerticalStrut(3));
        f = new JLabel("<html><center><b>UpLib " + uplib_version + "</b><p><small>PARC / ISL</small></center></html>");
        f.setHorizontalAlignment(SwingConstants.CENTER);
        f.setBackground(TOOLS_COLOR);
        f.setForeground(WHITE);
        f.setFont(new Font("Serif", Font.PLAIN, 14));
        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalGlue());
        s.add(f);
        s.add(Box.createHorizontalGlue());
        branding.add(s);
        branding.add(Box.createVerticalStrut(5));
        main.add(branding);
        main.add(Box.createHorizontalStrut(5));

        Box b = Box.createVerticalBox();
        b.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        JPanel b2 = new JPanel();
        b2.setLayout(new BoxLayout(b2, BoxLayout.Y_AXIS));
        // Box b2 = Box.createVerticalBox();
        b2.setBackground(BACKGROUND_COLOR);
        b2.setBorder(BorderFactory.createCompoundBorder(BorderFactory.createBevelBorder(BevelBorder.LOWERED),
                                                        BorderFactory.createEmptyBorder(8,8,8,8)));

        f = new JLabel("<html><center>" + mymessage + "</center></body></html>");

        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalGlue());
        s.add(f);
        s.add(Box.createHorizontalGlue());
        b2.add(Box.createVerticalGlue());
        b2.add(s);

        b2.add(Box.createVerticalGlue());
        b.add(b2);
        b.add(Box.createVerticalStrut(5));
        JButton cancel_button = new JButton("OK");
        cancel_button.setActionCommand("OK");
        cancel_button.addActionListener(this);
        cancel_button.setSelected(true);
        getRootPane().setDefaultButton(cancel_button);
        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalGlue());
        s.add(cancel_button);
        s.add(Box.createHorizontalGlue());
        b.add(s);

        main.add(b);

        getContentPane().add(main);
    }

    public void actionPerformed (ActionEvent e) {
        this.dispose();
    }
}

class GetQueryDialog extends JDialog implements ActionListener {

    final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);
    final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);
    final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);
    final static Color DARK_COLOR = new Color(.439f, .475f, .490f);
    final static Color WHITE = new Color(1.0f, 1.0f, 1.0f);
    final static Color BLACK = new Color(0.0f, 0.0f, 0.0f);

    public boolean submitted = false;
    public boolean cancelled = false;

    JTextField      repository_widget;
    JPasswordField  password_widget;
    JTextField      query_widget;
    JSlider         minscore_widget;
    JCheckBox       pickall_widget;

    JButton         submit_button;
    JButton         cancel_button;

    private String  mytitle = "";
    private Icon    myicon;
    private String  uplib_version = null;

    public String   myquery;
    public String   myrepository;
    public String   mypassword;
    public float    mycutoff;
    public boolean  myshowall;

    GetQueryDialog (String title, String query, String repoURL, String repoPassword, float cutoff, boolean showall) {
        super ((Frame) null, true);
        setBackground(TOOLS_COLOR);
        // setDefaultCloseOperation(JDialog.DISPOSE_ON_CLOSE);
        myquery = query;
        mytitle = title;
        myrepository = repoURL;
        mypassword = repoPassword;
        mycutoff = cutoff;
        myicon = UpLibShowDoc.getIcon();
        myshowall = showall;
        this.uplib_version = UpLibShowDoc.getUpLibVersion();
        // System.err.println("URL is " + repoURL + ", password is " + repoPassword);
        initComponents();
        pack();
        setLocationRelativeTo(null);
    }

    public void initComponents() {
        Box s;
        JLabel f;
        Font namefont = new Font("Serif", Font.BOLD, 14);
        Font boldfont = new Font("Serif", Font.BOLD, 12);
        Font smallfont = new Font("Serif", Font.PLAIN, 10);

        setTitle(mytitle);
	setBackground(TOOLS_COLOR);

        Box main = Box.createHorizontalBox();

        Box branding = Box.createVerticalBox();
        f = new JLabel(myicon);
        f.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalGlue());
        s.add(f);
        s.add(Box.createHorizontalGlue());
        branding.add(s);
//         f = new JLabel("ReadUp");
//         f.setHorizontalAlignment(SwingConstants.CENTER);
//         f.setBackground(TOOLS_COLOR);
//         f.setForeground(BLACK);
//         f.setFont(namefont);
//         s = Box.createHorizontalBox();
//         s.add(Box.createHorizontalGlue());
//         s.add(f);
//         s.add(Box.createHorizontalGlue());
//         branding.add(s);
//         branding.add(Box.createVerticalStrut(3));
        f = new JLabel("<html><center><b>UpLib " + uplib_version + "</b><p><small>PARC / ISL</small></center></html>");
        f.setHorizontalAlignment(SwingConstants.CENTER);
        f.setBackground(TOOLS_COLOR);
        f.setForeground(WHITE);
        f.setFont(new Font("Serif", Font.PLAIN, 14));
        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalGlue());
        s.add(f);
        s.add(Box.createHorizontalGlue());
        branding.add(s);
        main.add(branding);
        main.add(Box.createHorizontalStrut(5));

        Box b = Box.createVerticalBox();
        b.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        Container contents = getContentPane();
	contents.setBackground(TOOLS_COLOR);

        Font bold = new Font(null, Font.BOLD, contents.getFont().getSize());
        Font italic = new Font(null, Font.ITALIC, contents.getFont().getSize());

        s = Box.createHorizontalBox();
        f = new JLabel("Query");
        f.setFont(italic);
        f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
        s.add(f);
        query_widget = new JTextField((myquery == null) ? "" : myquery);
        query_widget.addActionListener(this);
        query_widget.setActionCommand("queried");
        s.add(Box.createHorizontalStrut(5));
        s.add(query_widget);
        s.add(Box.createHorizontalStrut(5));
        Border outer = new LineBorder(UPLIB_ORANGE, 3);
        Border inner = new EmptyBorder(5, 5, 5, 5);
        s.setBorder(new CompoundBorder(outer, inner));
        b.add(s);

        b.add(Box.createVerticalStrut(20));

        s = Box.createHorizontalBox();
        f = new JLabel("Repository");
        f.setFont(italic);
        f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
        s.add(f);
        repository_widget = new JTextField((myrepository == null) ? "(default)" : myrepository);
        s.add(Box.createHorizontalStrut(5));
        s.add(repository_widget);
        s.add(Box.createGlue());
        b.add(s);

        s = Box.createHorizontalBox();
        f = new JLabel("Password");
        f.setFont(italic);
        f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
        s.add(f);
        password_widget = new JPasswordField((mypassword == null) ? "" : mypassword);
        password_widget.addActionListener(this);
        password_widget.setActionCommand("queried");
        s.add(Box.createHorizontalStrut(5));
        s.add(password_widget);
        s.add(Box.createGlue());
        b.add(s);

        b.add(Box.createVerticalStrut(10));

        s = Box.createHorizontalBox();
        f = new JLabel("Min score");
        f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
	f.setBackground(contents.getBackground());
        s.add(f);
        // minscore_widget = new JSpinner(new SpinnerNumberModel(.75d, 0d, 1d, 0.05d));
        minscore_widget = new JSlider(0, 100, Math.round(mycutoff));
	minscore_widget.setBackground(contents.getBackground());
        s.add(minscore_widget);
        s.add(Box.createHorizontalStrut(10));
        pickall_widget = new JCheckBox("Show All", myshowall);
	pickall_widget.setBackground(contents.getBackground());
        s.add(pickall_widget);
        b.add(s);

        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalStrut(10));
        cancel_button = new JButton("Cancel");
        cancel_button.setActionCommand("cancel");
        cancel_button.addActionListener(this);
        s.add(cancel_button);
        s.add(Box.createGlue());
        submit_button = new JButton("Submit");
        submit_button.setActionCommand("submit");
        submit_button.addActionListener(this);
        s.add(submit_button);
        s.add(Box.createHorizontalStrut(10));
        b.add(s);

        main.add(b);

        contents.add(main);
    }

    public void update(Graphics g) {
        super.update(g);
        if (!query_widget.hasFocus())
            query_widget.requestFocusInWindow();
    }
    
    public void setVisible(boolean value) 
    {
        if(value)
        {
            query_widget.requestFocusInWindow();
            super.setVisible(value);
        }
        else
        {
            // hide implementation
        }
    }

    public void actionPerformed(ActionEvent e) {
        if ("submit".equals(e.getActionCommand())) {
            submitted = true;
            mypassword = new String(password_widget.getPassword());
            myquery = query_widget.getText();
            myrepository = repository_widget.getText();
            mycutoff = minscore_widget.getValue();
            dispose();
        }
        else if ("cancel".equals(e.getActionCommand())) {
            cancelled = true;
            dispose();
        }
        else if ("queried".equals(e.getActionCommand())) {
            submitted = true;
            mypassword = new String(password_widget.getPassword());
            myquery = query_widget.getText();
            myrepository = repository_widget.getText();
            mycutoff = minscore_widget.getValue();
            dispose();
        }
        else
            System.err.println("Action " + e);
    }
}

class Trail {

    private static final Color PINK_WASH = new Color(1.0f, 0.0f, 0.0f, .2f);
    private static final Color BLUE_WASH = new Color(0.0f, 0.0f, 1.0f, .2f);
    private final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    protected final static Color DARK_COLOR = new Color(.439f, .475f, .490f);

    private static BufferedImage LinkThumbnail = null;

    static {
        LinkThumbnail = new BufferedImage(8, 100, BufferedImage.TYPE_INT_RGB);
        Graphics g = LinkThumbnail.getGraphics();
        g.setColor(Color.red);
        g.fillRect(0, 0, 8, 100);
        g.dispose();
    }

    private static class Item extends Rectangle {
        private Repository.Document doc;
        private Activity act;

        public Item (Repository.Document d, Activity a) {
            super(0, 0, 0, 0);
            this.doc = d;
            this.act = a;
        }
        public Date getTimestamp () {
            return act.timestamp;
        }
        public Repository.Document getDocument () {
            return doc;
        }
        public int getPage () {
            return act.page_index;
        }
        public BufferedImage getThumbnail () {
            return (BufferedImage) (doc.getPageThumbnailLoader().get(doc.getID(), act.page_index, 1, null));
        }
        public String getTooltip() {
            String fpn = doc.getMetadataProperty("first_page_number");
            int first_page_number = (fpn == null) ? 1 : Integer.parseInt(fpn);
            return doc.getTitle() + ", page " + (act.page_index + first_page_number);
        }

        public void render (Graphics g, TrailView c) {
            BufferedImage img = getThumbnail();
            g.setColor(DARK_COLOR);
            g.drawImage(img, this.x, this.y, this.width, this.height, null);
            g.drawRect(this.x, this.y, this.width-1, this.height-1);
        }

        public void clicked (MouseEvent e, Workspace.DocumentOpener opener) throws IOException {
            opener.open(getDocument(), getPage());
        }
    }

    private static class PageTurn extends Item {
        public PageTurn (Repository.Document d, Activity a) {
            super(d, a);
        }
    }

    private static class OpenDocument extends PageTurn {
        public OpenDocument (Repository.Document d, Activity a) {
            super(d, a);
        }
        public void render (Graphics g, TrailView c) {
            super.render(g, c);
            g.setColor(PINK_WASH);
            g.fillRect(this.x, this.y, this.width, this.height);
        }
    }

    private static class FollowLink extends Item {
        public String url;
        public FollowLink (Repository.Document d, Activity a) throws UnsupportedEncodingException {
            super(d, a);
            int urlstring_length = (a.extension_bytes[0] << 8) + a.extension_bytes[1];
            url = new String(a.extension_bytes, 2, urlstring_length, "UTF-8");
        }
        public String getTooltip() {
            return url;
        }
        public BufferedImage getThumbnail () {
            return LinkThumbnail;
        }
        public void clicked (MouseEvent e, Workspace.DocumentOpener opener) throws IOException {
            try {
                opener.open(url);
            } catch (Exception x) {
                x.printStackTrace(System.err);
            }
        }
    }

    public static class TrailView extends JPanel implements MouseListener, MouseWheelListener {

        public static final int VERTICAL = 0;
        public static final int HORIZONTAL = 1;

        Trail trail;
        public int layout;
        String tool_tip_text;
        Workspace.DocumentOpener opener;
        AffineTransform zoom_level;

        public TrailView (Trail t, int layout) {
            super();
            setLayout(null);
            trail = t;
            this.layout = layout;
            if (trail.size() > 0)
                tool_tip_text = "Trail starting at " + trail.earliest().toString() + ", and going to " + trail.latest().toString();
            else
                tool_tip_text = "Empty trail";
            ToolTipManager.sharedInstance().registerComponent(this);
            zoom_level = new AffineTransform();
            setToolTipText(tool_tip_text);
            addMouseListener(this);
            addMouseWheelListener(this);
            opener = null;
        }

        public void doLayout() {
            // System.err.println("doLayout " + this);
            Dimension d = new Dimension(0, 0);
            Iterator it = trail.iterator();
            while (it.hasNext()) {
                Item i = (Item) (it.next());
                if ((i.height == 0) || (i.width == 0)) {
                    BufferedImage img = i.getThumbnail();
                    if (img != null) {
                        i.width = img.getWidth(null);
                        i.height = img.getHeight(null);
                    }
                }
                if (layout == VERTICAL) {
                    i.x = 0;
                    i.y = (int) Math.round(zoom_level.getScaleY() * d.height);
                    d.width = Math.max(d.width, (int) Math.round(i.width * zoom_level.getScaleX()));
                    d.height = d.height + (int) Math.round(i.height * zoom_level.getScaleY()) + 2;
                } else if (layout == HORIZONTAL) {
                    i.x = (int) Math.round(d.width / zoom_level.getScaleX());
                    i.y = (int) Math.round(getHeight() / zoom_level.getScaleY()) - i.height;
                    d.width = d.width + (int) Math.round(i.width * zoom_level.getScaleX()) + 2;
                    d.height = Math.max(d.height, (int) Math.round(i.height * zoom_level.getScaleY()));
                }
            }
            if (trail.size() > 0) {
                if (layout == VERTICAL)
                    d.height -= 2;
                else if (layout == HORIZONTAL)
                    d.width -= 2;
            }
            
            setPreferredSize(d);
            setMinimumSize(d);
            setMaximumSize(d);
        }

        private Item findItem (Point p) {
            try {
                Point2D p2 = zoom_level.inverseTransform(p, null);
                Iterator it = trail.iterator();
                while (it.hasNext()) {
                    Item i = (Item) (it.next());
                    if (i.contains(p2.getX(), p2.getY())) {
                        return i;
                    }
                }
            } catch (NoninvertibleTransformException x) {
                x.printStackTrace(System.err);
            }
            return null;
        }

        public void paintComponent (Graphics g) {
            // System.err.println("paintComponent " + this);
            Rectangle cliprect = g.getClipBounds();
            g.setColor(BACKGROUND_COLOR);
            g.fillRect(cliprect.x, cliprect.y, cliprect.width, cliprect.height);
            try {
                Rectangle testrect = zoom_level.createInverse().createTransformedShape(cliprect).getBounds();
                AffineTransform old_transform = ((Graphics2D) g).getTransform();
                ((Graphics2D) g).setTransform(zoom_level);
                Iterator it = trail.iterator();
                while (it.hasNext()) {
                    Item i = (Item)(it.next());
                    if (i.intersects(testrect)) {
                        i.render(g, this);
                    }
                }
                ((Graphics2D) g).setTransform(old_transform);
            } catch (NoninvertibleTransformException x) {
                x.printStackTrace(System.err);
                return;
            }
        }

        public String getToolTipText () {
            // System.err.println("getToolTipText() => " + tool_tip_text);
            return tool_tip_text;
        }

        public String getToolTipText (MouseEvent e) {
            Point p = e.getPoint();
            Item i = findItem(p);
            return (i != null) ? i.getTooltip() : tool_tip_text;
        }


        public void setDocumentOpener (Workspace.DocumentOpener d) {
            opener = d;
        }

        // MouseWheelListener methods

        public void mouseWheelMoved (MouseWheelEvent e) {
            double scalefactor = Math.pow(0.9D, (double) e.getWheelRotation());
            if (scalefactor != 0) {
                zoom_level.scale(scalefactor, scalefactor);
                // System.err.println("scalefactor is " + zoom_level.getScaleY());
                doLayout();
                repaint();
            }
        }

        // MouseListener methods

        public void mouseClicked(MouseEvent e) {
            // Invoked when the mouse button has been clicked (pressed and released) on a component.
            if (e.getButton() == MouseEvent.BUTTON1) {
                System.err.println("mouseClicked " + e);
                Item i = findItem(e.getPoint());
                if (i != null)
                    try {
                        i.clicked(e, opener);
                    } catch (IOException x) {
                        x.printStackTrace(System.err);
                    }
            } else if (e.getButton() == MouseEvent.BUTTON2) {
                zoom_level.setToIdentity();
                repaint();
            }
        }

        public void mouseEntered(MouseEvent e) {
            // Invoked when the mouse enters a component.
        }

        public void mouseExited(MouseEvent e) {
            // Invoked when the mouse exits a component.
        }

        public void mousePressed(MouseEvent e) {
            // Invoked when a mouse button has been pressed on a component.
        }

        public void mouseReleased(MouseEvent e) {
            // Invoked when a mouse button has been released on a c
        }
    }

    private ArrayList items;
    private Vector open_docs;

    public Trail () {
        super();
        items = new ArrayList();
        open_docs = new Vector();
    }

    public Iterator iterator() {
        return items.iterator();
    }

    public int size () {
        return items.size();
    }

    public Date earliest () {
        return ((Item)(items.get(0))).getTimestamp();
    }

    public Date latest () {
        return ((Item)(items.get(items.size() - 1))).getTimestamp();
    }

    public void add (Repository.Document d, Activity a) {
        if (a.activity_code == Activity.AC_OPENED_DOC) {
            open_docs.add(d);
            items.add(new OpenDocument(d, a));
        } else if (a.activity_code == Activity.AC_CLOSED_DOC) {
            open_docs.remove(d);
        } else if (!open_docs.contains(d)) {
            // document must be open for events to be recorded in the trail
            return;
        } else if (a.activity_code == Activity.AC_PAGE_TURNED) {
            items.add(new PageTurn(d, a));
        } else if (a.activity_code == Activity.AC_HOTSPOT_CLICKED) {
            try {
                items.add(new FollowLink(d, a));
            } catch (Exception x) {
                x.printStackTrace(System.err);
            }
        }
    }

    public TrailView getView (int orientation) {
        return new TrailView(this, orientation);
    }
}
    
public class UpLibShowDoc
    implements
        com.parc.uplib.util.FeedbackApp,
        javax.swing.event.AncestorListener,
        NodeListener,
        HyperlinkListener,
        Workspace.DocumentOpener,
        SingleInstanceListener,
        ActionListener {

    private static boolean all_closed = false;
    private static String uplib_version = "(unknown)";
    private static ImageIcon readup_icon;
    private static BufferedImage readup_favicon;

    // maps URL to Repository instance
    private static HashMap repositories = new HashMap();

    // maps Repository.Document to logger instance
    private static HashMap activity_loggers = new HashMap();

    private static Pattern BASENAME_ARG = Pattern.compile("--repository=([^\\s]*)");
    private static Pattern PASSWORD_ARG = Pattern.compile("--password=([^\\s]*)");
    private static Pattern HOSTNAME_ARG = Pattern.compile("--hostname=([^\\s]*)");
    private static Pattern DOCID_ARG = Pattern.compile("--doc-id=([^\\s]*)");
    private static Pattern PAGE_ARG = Pattern.compile("--page=(-?\\d+)");
    private static Pattern COOKIE_ARG = Pattern.compile("--cookie=([^=]+=.+)");
    private static Pattern PSEUDO_FILE = Pattern.compile("/pseudofile/([^/]*)/([0-9]*)/([0-9-]*)(.*)");

    private String      current_url;
    private String      current_query;
    private float       current_cutoff;
    private boolean     current_showall;
    private Closer      closer_map;
    private int         frame_x = 20;
    private int         big_x_incr = 200;
    private int         frame_y = 20;
    private DocViewerCallback url_opener = null;
    private boolean     resizable;
    private int         animation_time;
    private boolean     two_page;
    private SetURLHandler set_url_handler = null;
    private JFrame      results_pane = null;
    private ClusterList cluster_list = null;
    private Trail       current_trail = null;
    private FileBoxHolder       dates_box = null;
    private FileBoxHolder       authors_box = null;
    private FileBoxHolder       collections_box = null;
    private FileBoxHolder       categories_box = null;
    private BasicService        urlopenerservice = null;
    private com.parc.uplib.readup.widget.Clipboard      clipboard = null;
    private ClientKeyManager    client_key_manager = null;

    public Vector       files_to_open = new Vector();

    static class ShutdownHook extends Thread {

        Closer closer;

        public ShutdownHook (Closer closer) {
            super("ShutdownHook for UpLibShowDoc " + Integer.toHexString(closer.hashCode()));
            this.closer = closer;
        }

        public void run () {
            Runtime.getRuntime().runFinalization();
        }
    }

    private static class JNLPClipboard implements com.parc.uplib.readup.widget.Clipboard {
        private javax.jnlp.ClipboardService service;
        public JNLPClipboard (javax.jnlp.ClipboardService s) {
            service = s;
        }
        public void setContents(Transferable t) throws IllegalStateException {
            service.setContents(t);
        }
        public Transferable getContents () throws IllegalStateException {
            return service.getContents();
        }
    }

    private class SetURLHandler implements DocViewerCallback {
        public void call (Object o) {
            System.err.println("called SetURLHandler with " + o);
            Repository repo = getCurrentRepository();
            if ((repo != null) && (o instanceof String)) {
                try {
                    URL r = new URL(repo.getURL(), "/action/basic/dv_show?" + (String)o);
                    java.awt.datatransfer.StringSelection s = new java.awt.datatransfer.StringSelection(r.toExternalForm());
                    clipboard.setContents(s);
                    System.err.println("Clipboard has been set to:  " + r.toExternalForm());
                } catch (Exception x) {
                    System.err.println("Couldn't set clipboard:");
                    x.printStackTrace(System.err);
                }
            }
        }
        public void flush() {
        }
    }

    private class ActivityTracker extends UpLibActivityLogger {

        private Repository.Document doc;

        public ActivityTracker (Repository.Document doc) throws MalformedURLException {
            super(doc.getID(),
                  new URL(doc.getRepository().getURL(), doc.getParameter("activity-sink-url", null)),
                  doc.getRepository().getPassword());
            this.doc = doc;
            setCookie(doc.getRepository().getCookie());
        }

        public void call (Object o) {
            if (o instanceof Activity) {
                registerAction(doc, (Activity) o);
            }
            super.call(o);
        }
    }

    class URLOpener implements DocViewerCallback {

        private String findPattern (String s, String p) {
            Pattern cp = Pattern.compile(".*" + p + ".*");
            Matcher m = cp.matcher(s);
            if (m.matches()) {
                //System.err.println("pattern \"" + p + "\" matches string \"" + s + "\"");
                return m.group(1);
            } else {
                //System.err.println("pattern \"" + p + "\" doesn't match string \"" + s + "\"");
                return null;
            }
        }

        public void call (Object o) {
            if (o instanceof URL) {
                System.err.println("invoking URL " + ((URL)o).toExternalForm());
                try {
                    URL url = (URL) o;
                    String path = url.getPath();
                    String query = url.getQuery();
                    String auth = url.getAuthority();
                    String protocol = url.getProtocol();
                    String repo_url = protocol + "://" + auth + "/";
                    System.err.println("auth is " + auth + ", path is " + path + ", query is " + query);
                    if (auth.equals("-uplib-")) {
                        // re-write the form "-uplib-" to point to the current repository
                        repo_url = current_url;
                        System.err.println("auth is " + auth + ", repo_url is " + repo_url);
                        if (path != null) {
                            repo_url += path;
                        } else {
                            repo_url += "/";
                        }
                        if (query != null) {
                            repo_url += "?" + query;
                        }
                        url = new URL(repo_url);
                    }
                    if (path.startsWith("/action/basic/dv_show")) {
                        // assume it's an UpLib reference
                        query = URLDecoder.decode(query, "UTF-8");
                        String doc_id = findPattern(query, "doc_id=([^&]+)");
                        String page = findPattern(query, "page=([^&]+)");
                        String start = findPattern(query, "selection-start=([^&]+)");
                        String end = findPattern(query, "selection-end=([^&]+)");
                        String rect = findPattern(query, "selection-rect=([^&]+)");
                        String password = findPattern(query, "password=([^&]+)");
                        Repository r = findRepository(repo_url);
                        if (r == null) {
                            r = new Repository (new URL(repo_url), password);
                            repositories.put(r.getURLString(), r);
                        }
                        System.err.println("external form is " + r.getURLString() + "; doc_id is " + doc_id);
                        Repository.Document doc = r.getDocument(doc_id);
                        // do we already have this document open?
                        DocViewer dv = closer_map.get(doc);
                        System.err.println("dv for " + doc + " is " + dv);
                        if (dv == null) {
                            // open a new window
                            dv = showDocument(doc);
                        }
                        if (dv != null) {
                            if (page != null)
                                dv.setPage(Integer.parseInt(page));
                            if ((page != null) && (rect != null)) {
                                String[] parts = rect.split(",");
                                if (parts.length == 4) {
                                    Rectangle selection = new Rectangle();
                                    // we add a bit of padding at left and top
                                    selection.setFrame(Float.parseFloat(parts[0]) - 1,
                                                       Float.parseFloat(parts[1]) - 1,
                                                       Float.parseFloat(parts[2]) + 1,
                                                       Float.parseFloat(parts[3]) + 1);
                                    dv.setSelection(Integer.parseInt(page), selection);
                                }
                            } else if ((page != null) && (start != null) && (end != null))
                                dv.setSelection(Integer.parseInt(page), Integer.parseInt(start), Integer.parseInt(end));
                            dv.setVisible(true);
                            Container topj = dv.getTopLevelAncestor();
                            if (topj instanceof Window) {
                                ((Window) topj).setVisible(true);
                                ((Window) topj).toFront();
                            }
                        }
                    } else if (urlopenerservice != null) {
                        urlopenerservice.showDocument(url);
                    } else {
                        BrowserLauncher.openURL(url.toExternalForm());
                    }
                } catch (Exception x) {
                    System.err.println("Couldn't open " + o);
                    x.printStackTrace(System.err);
                }
            }
        }
        public void flush() {
        }
    }

    static class UserCancelled extends IOException {
    }

    private class RepositoryOpener implements DocViewerCallback {

        Repository repository;

        public RepositoryOpener (URL repository_url, String password) throws MalformedURLException {
            this.repository = new Repository(repository_url, password);
        }

        public RepositoryOpener (Repository repo) {
            this.repository = repo;
        }

        public void call (Object o) {
            try {
                boolean opened = false;
                while (!opened) {
                    opened = queryAndShowDocs(null, repository);
                }
            } catch (ResourceLoader.PrivilegeViolation x) {
                MessagePane p = new MessagePane("ReadUp on " + repository,
                                                "Not allowed:  couldn't get access to repository with given password");
                closer_map.add(p, null);
                p.setVisible(true);
            } catch (ResourceLoader.CommunicationFailure x) {
                MessagePane p = new MessagePane("ReadUp on " + repository,
                                                "Can't connect to repository.");
                closer_map.add(p, null);
                p.setVisible(true);
            } catch (UserCancelled e) {
                return;
            } catch (IOException x) {
                MessagePane p = new MessagePane("ReadUp on " + repository,
                                                "IOException " + x + " attempting to talk to the repository.");
                closer_map.add(p, null);
                p.setVisible(true);
            }
        }

        public void flush() {
        }
    }

    private static void usage () {
        System.err.println("Usage:  java -jar ShowDoc.jar <options> QUERY");
        System.err.println("  Options are:  --twopage -- show two pages side-by-side");
        System.err.println("                --repository=https://HOST:PORT/ -- specify repository");
        System.err.println("                --animate=PERIOD -- specify period, in milliseconds, for page-turn animation");
        System.err.println("                --resizable -- make pages stretchy");
        System.err.println("                --non-resizable -- keep pages fixed-size (default)");
        System.err.println("                --hostname=HOSTNAME -- expected server certificate hostname");
        System.err.println("                --nosplash -- don't display the splash page");
        System.err.println("                --doc-id=ID -- display this document (can be repeated)");
        System.err.println("                --cutoff=FLOAT -- set the query cutoff value for hit scores (0 - 100)");
        System.exit(1);
    }

    private static String joinURLParts (String p1, String p2) {
        String retval;

        if (p1.endsWith("/") && (p2.startsWith("/")))
            retval = p1 + p2.substring(1);
        else
            retval = p1 + p2;
        System.err.println("URL formed is " + retval);
        return retval;
    }

    // methods for ActivityTracker

    public void registerAction (Repository.Document doc, Activity a) {
        System.err.println("Activity: " + a);
        if (current_trail != null)
            current_trail.add(doc, a);
    }

    // methods for Workspace.DocumentOpener

    public JComponent open (Repository.Document doc, int page_index) throws IOException {
        return showDocument(doc, page_index);
    }

    public void open (String url) throws Exception {
        url_opener.call(new URL(url));
    }

    public void open (URL url) throws Exception {
        url_opener.call(url);
    }

    // methods for HyperlinkListener

    public void hyperlinkUpdate (HyperlinkEvent e) {
        if (e.getEventType() == HyperlinkEvent.EventType.ACTIVATED) {
            url_opener.call(e.getURL());
        }
    }

    public DocViewer showDocument (Repository.Document doc) throws IOException {
        return showDocument(doc, -1);
    }

    public DocViewer showDocument (Repository.Document doc, int page_index) throws IOException {

        String image_url_prefix;
        boolean show_controls = true;
        boolean show_edge = true;
        Properties map = null;

        try {
            map = doc.getParameters();
        } catch (java.net.ConnectException x) {
            throw new ResourceLoader.CommunicationFailure("Can't connect to repository:  " + x);
        } catch (ResourceLoader.PrivilegeViolation x) {
            throw x;
        } catch (ResourceLoader.CommunicationFailure x) {
            throw x;
        } catch (Exception e) {
            System.err.println("Exception raised:  " + e);
            e.printStackTrace(System.err);
            return null;
        }

        // map.list(System.err);
        if (!(map.containsKey("title") &&
              map.containsKey("page-count") &&
              map.containsKey("first-page-number") &&
              map.containsKey("page-width") &&
              map.containsKey("page-height") &&
              map.containsKey("thumbnail-width") &&
              map.containsKey("thumbnail-height"))) {
            System.err.println("got bad params for " + doc);
            return null;
        }
        boolean has_text = doc.getBooleanParameter("has-text-boxes", false);
        boolean has_hi_res_images = doc.getBooleanParameter("has-hi-res-images", false);
        int images_dpi = doc.getIntegerParameter("images-dpi", 300);
        Dimension bt_translation = new Dimension((int) doc.getRealParameter("page-translation-x", Double.NaN),
                                                 (int) doc.getRealParameter("page-translation-y", Double.NaN));
        double bt_scaling = doc.getRealParameter("page-scaling", Double.NaN);
        double st_scaling = doc.getRealParameter("thumbnail-scaling", Double.NaN);

        int animate_period = doc.getIntegerParameter("pageturn-animation-millisecs", 0);
        animate_period = (animation_time >= 0) ? animation_time : animate_period;
        int rm = doc.getIntegerParameter("right-margin", 25);

        String title = doc.getParameter("title", "Document " + doc.getID());
        JFrame topj = new JFrame(title);
        topj.setLocation(frame_x, frame_y);
        frame_x += 20;
        frame_y += 20;
        if (((frame_x + 20) >= GraphicsEnvironment.getLocalGraphicsEnvironment().getDefaultScreenDevice().getDisplayMode().getWidth()) ||
            ((frame_y + 20) >= GraphicsEnvironment.getLocalGraphicsEnvironment().getDefaultScreenDevice().getDisplayMode().getHeight())) {
            frame_x = 20 + big_x_incr;
            big_x_incr += 200;
            frame_y = 20;
        }

        DocViewer dv = null;
        try {
            dv = new DocViewer(doc.getPageImageLoader(),
                               doc.getPageThumbnailLoader(),
                               title,
                               doc.getID(),
                               new RepositoryOpener(doc.getRepository()),                     /* logo URL */
                               doc.getIntegerParameter("page-count", 1),
                               doc.getIntegerParameter("first-page-number", 1),
                               doc.getParameter("page-numbers", null),
                               (page_index < 0) ? doc.getIntegerParameter("current-page", 0) : page_index,
                               new Dimension(doc.getIntegerParameter("page-width", 0),        /* page size */
                                             doc.getIntegerParameter("page-height", 0)),
                               new Dimension(doc.getIntegerParameter("thumbnail-width", 0),   /* thumbnail size */
                                             doc.getIntegerParameter("thumbnail-height", 0)),
                               show_controls,                                                 /* show control panel */
                               DocViewer.PAGEEDGE_3D_PROGRESS_BAR_TOP,                        /* top edge display */
                               DocViewer.PAGEEDGE_3D_PROGRESS_BAR_BOTTOM,                     /* bottom edge display */
                               two_page,                                                      /* show two pages */
                               doc.getScribbles(),                                            /* vector of scribbles */
                               doc.getScribbleHandler(),                                      /* handler for new scribbles */
                               doc.getHotspots(url_opener),                                   /* vector of hotspots */
                               getActivityLogger(doc),                                        /* handler for activities */
                               true,                                                          /* watch activities */
                               doc.getBooleanParameter("annotations-state", false),           /* show scribbles */
                               doc.getIntegerParameter("inkpot", 0),                          /* which annotation ink? */
                               doc.getParameter("bookmarks-state", null),                     /* bookmark data */
                               animate_period,                                                /* pageturn animation period */
                               0,
                               (has_text) ? doc.getPageTextLoader() : null,
                               url_opener,
                               doc.getNotesHandler(),
                               doc.getNotesLoader());

            dv.setHotspotSaver(doc.getHotspotHandler());
            if (has_text) {
                dv.setLocateHandler(new LocateHandler(null, doc.getRepository().getURLString(), doc.getID()));
                dv.setGoogleHandler(new LocateHandler(null));
                dv.setURLHandler(set_url_handler);
            }
            dv.setRepositoryURL(doc.getRepository().getURL());
            if ((bt_scaling != Double.NaN) && (st_scaling != Double.NaN) &&
                (bt_translation.width != Double.NaN) && (bt_translation.height != Double.NaN)) {
                dv.setThumbnailSizeFactors(bt_translation, bt_scaling, st_scaling);
                if (has_hi_res_images)
                    dv.setHiResPageImageLoader(doc.getPageHiResLoader(), bt_scaling, bt_translation, images_dpi);
            }
            dv.setClipboard(clipboard);

            dv.setTopLevelWindow(topj);
            // dv.addAncestorListener(this);

            // dv.setLogoImage(readup_favicon);

            if (resizable) {
                ResizableDocViewer rdv = new ResizableDocViewer(dv);
                if (has_text)
                    rdv.getDocViewer().setADHState(400);
                topj.getContentPane().add(rdv);
            } else {
                if (has_text)
                    dv.setADHState(400);
                topj.getContentPane().add(dv);
            }
            topj.setDefaultCloseOperation(WindowConstants.DO_NOTHING_ON_CLOSE);
            topj.pack();
            closer_map.add((Window) topj, dv, doc);
            topj.setJMenuBar(getMenuBar(doc));
            topj.setVisible(true);
        } catch (Throwable t) {
            t.printStackTrace(System.err);
        }
        return dv;
    }

    private Repository findRepository(String url) {
        if (url == null)
            return null;
        // repositories are just host + port, so we should strip off extraneous junk
        try {
            URL u = Repository.getCanonicalRepositoryURL(url);
            return (Repository) (repositories.get(u.toExternalForm()));
        } catch (MalformedURLException x) {
            System.err.println("Attempt to findRepository for malformed URL string " + url);
            return null;
        }
    }

    private Repository addRepository (String url, String password) throws MalformedURLException {
        Repository r = findRepository(url);
        if (r != null) {
            url = r.getURLString();
            // check to see if we have a better password
            if ((password != null) && (password.length() > 0)) {
                if (!password.equals(r.getPassword())) {
                    // we want to delete the old repository, and add a new one
                    try {
                        if (!client_key_manager.addCertificateViaConfigurator(new URL(url)))
                            System.err.println("No certificate found via Configurator for " + url + ".");
                    } catch (Exception x) {
                        System.err.println("Couldn't add certificate for " + url + ":");
                        x.printStackTrace(System.err);
                    }
                    r = new Repository(url, password);
                    repositories.put(url, r);
                }
            }
        } else {
            URL u = Repository.getCanonicalRepositoryURL(url);
            try {
                if (!client_key_manager.addCertificateViaConfigurator(u))
                    System.err.println("No certificate found via Configurator for " + u + ".");
            } catch (Exception x) {
                System.err.println("Couldn't add certificate for " + u + ":");
                x.printStackTrace(System.err);
            }
            r = new Repository(u, password);
            repositories.put(u.toExternalForm(), r);
        }
        return r;
    }

    private Repository setCurrentRepository (String url, String password) throws MalformedURLException {
        current_url = url;
        return addRepository(url, password);
    }

    private Repository getCurrentRepository () {
        return findRepository(current_url);
    }

    private DocViewerCallback getActivityLogger (Repository.Document d) {
        DocViewerCallback logger = (DocViewerCallback) activity_loggers.get(d);
        if (logger == null) {
            try {
                logger = new ActivityTracker(d);
                activity_loggers.put(d, logger);
            } catch (Exception x) {
                x.printStackTrace(System.err);
            }
        }
        return logger;
    }

    private void showSearchResults (Repository.Search s) {
        Cluster c = new Cluster(s);
        c.addNodeListener(this);
        cluster_list.prepend(c);
        results_pane.setJMenuBar(getMenuBar(s.getRepository()));
        results_pane.setVisible(true);
    }

    private Repository.Search promptForQuery (Repository repository)
        throws UserCancelled, IOException {
        
        if ((repository != null) && (findRepository(repository.getURLString()) == null))
            repositories.put(repository.getURLString(), repository);

        Repository r = getCurrentRepository();
        Repository.Search.Hit[] hits = null;
        String repo = (repository == null) ? ((r != null) ? r.getURLString() : "") : repository.getURLString();
        String pword = (repository == null) ? ((r != null) ? r.getURLString() : "") : repository.getPassword();

        System.err.println("promptForQuery:  repository is " + repository);
        System.err.println("promptForQuery:  repo is " + repo + ", pword is " + pword);

        GetQueryDialog theDialog = new GetQueryDialog ("ReadUp on " + repo,
                                                       (current_query == null) ? "" : current_query,
                                                       repo, pword,
                                                       current_cutoff, current_showall);
        closer_map.add(theDialog, null);
        theDialog.setVisible(true);
        
        if (!theDialog.cancelled) {
            current_query = theDialog.query_widget.getText();
            repo = theDialog.repository_widget.getText();
            pword = new String(theDialog.password_widget.getPassword());
            repo = (repo.endsWith("/")) ? repo : repo+"/";
            current_cutoff = theDialog.minscore_widget.getValue();
            current_showall = theDialog.pickall_widget.isSelected();
        } else {
            System.err.println("User cancelled search.");
            throw new UserCancelled();
        }

        if ((current_query != null) && (current_query.trim().length() > 0)) {
            System.err.println("repo is \"" + repo + "\", r is " + r);
            r = setCurrentRepository(repo, pword);
            return r.search(current_query, current_cutoff, current_showall);
        }

        return null;
    }

    public boolean queryAndShowDocs (String query, Repository repository)
        throws UserCancelled, IOException {
        Repository.Search result = null;

        System.err.println("queryAndShowDocs(" + query + ", " + repository);
        Repository r = (repository == null) ? getCurrentRepository() : repository;
        try {
            if (query == null)
                result = promptForQuery (r);
            else 
                result = r.search(query, current_cutoff, current_showall);
            Repository.Search.Hit[] hits = null;

            if (result != null)
                hits = result.getHits();
            if ((hits != null) && (hits.length > 0)) {
                showSearchResults(result);
            } else if (query == null) {
                System.err.println("No documents found matching query \"" + current_query + "\".");
                MessagePane p = new MessagePane("ReadUp on " + repository,
                                                "No documents found matching query<p><b>"
                                                + current_query +
                                                "</b><p>with cutoff " + current_cutoff);
                closer_map.add(p, null);
                p.setVisible(true);
            }
        } catch (ResourceLoader.PrivilegeViolation x) {
            MessagePane p = new MessagePane("ReadUp on " + repository,
                                            "Not allowed.<br>(Couldn't get access to repository with given password.)");
            closer_map.add(p, null);
            p.setVisible(true);
            return false;
        } catch (ResourceLoader.CommunicationFailure x) {
            MessagePane p = new MessagePane("ReadUp on " + repository,
                                            "Can't connect to repository at<br>" + repository +".");
            closer_map.add(p, null);
            p.setVisible(true);
            return false;
        } catch (UserCancelled x) {
            throw x;
        } catch (IOException x) {
            MessagePane p = new MessagePane("ReadUp on " + repository,
                                            "IOException<br><b>" + x + "</b><br>while attempting to talk to the repository at<br>" + repository + ".");
            closer_map.add(p, null);
            p.setVisible(true);
            return false;
        }
        return (result != null);
    }

    public UpLibShowDoc (Closer closer, String[] doc_ids,
                         String repourl, String repopassword, String cookie, String hostname,
                         boolean resizable, float cutoff, int animation_time,
                         boolean nosplash, boolean show_two_pages, Configurator conf) {

        String tmp;
        String certificate_hostname = hostname;

        if (certificate_hostname == null) {
            certificate_hostname = (conf == null) ? null : conf.get("java-default-certificate-hostname");
        }
        if ((conf != null) && (certificate_hostname != null)) {
            tmp = conf.get("use-parc-hostname-matcher", "false");
            com.parc.uplib.util.PARCAwareCertHostnameVerifier hv =
                new com.parc.uplib.util.PARCAwareCertHostnameVerifier(certificate_hostname,
                                                                      (tmp != null) && tmp.toLowerCase().equals("true"));
            HttpsURLConnection.setDefaultHostnameVerifier(hv);
        }

        try {
            String java_trust_store = (conf == null) ? null : conf.get("java-default-trust-store");
            if (java_trust_store != null) {
                if (!(new File(java_trust_store).exists())) {
                    System.err.println("Can't find specified trust-store file:  " + java_trust_store);
                } else {
                    tmp = System.getProperty("javax.net.ssl.trustStore");
                    if (tmp == null)
                        System.setProperty("javax.net.ssl.trustStore", java_trust_store);
                }
            }
            System.err.println("default trustStore is \"" + System.getProperty("javax.net.ssl.trustStore") + "\"");
        } catch (java.security.AccessControlException x) {
            x.printStackTrace(System.err);
        }

        // Now set up the detector that will pop up a dialog box for unknown certs
        try {
            client_key_manager = new ClientKeyManager();
            CertificateHandler.initialize(null, client_key_manager);
            CertificateHandler.ignoreHostnameMismatches();
        } catch (Exception x) {
            System.err.println("Can't install certificate handler code; proceeding without it.\n");
        }

        try {
            urlopenerservice = (BasicService) ServiceManager.lookup("javax.jnlp.BasicService");
        } catch (javax.jnlp.UnavailableServiceException x) {
            // no problem
        }

        // see if we can access the clipboard
        SecurityManager security = System.getSecurityManager();
        if (security != null) {
            try {
                security.checkSystemClipboardAccess();
                // if that succeeded, we can read it
                clipboard = new WrappedSystemClipboard();
            } catch (SecurityException x) {
                clipboard = null;
            } catch (HeadlessException x) {
                clipboard = null;
            }
        } else {
            try {
                clipboard = new WrappedSystemClipboard();
            } catch (HeadlessException x) {
                clipboard = null;
            }
        }
        if (clipboard == null) {
            try {
                ClipboardService service = (ClipboardService) ServiceManager.lookup("javax.jnlp.ClipboardService");
                clipboard = new JNLPClipboard(service);
            } catch (javax.jnlp.UnavailableServiceException x) {
                // no problem
            }
        }

        macOSXRegistration();

        closer_map = closer;
        url_opener = new URLOpener();
        this.two_page = show_two_pages;
        this.resizable = resizable;
        this.animation_time = animation_time;
        this.set_url_handler = new SetURLHandler();
        this.current_showall = true;

        this.current_trail = new Trail();

        if (repourl != null) {
            try {
                Repository r = setCurrentRepository(repourl, repopassword);
                if (cookie != null) {
                    r.setCookie(cookie);
                    System.out.println("Cookie for " + r + " is " + cookie);
                }
            } catch (MalformedURLException x) {
                System.err.println("Bad URL " + repourl + " for repository:");
                x.printStackTrace(System.err);
            }
        }

        results_pane = new JFrame("ReadUp Query Results");
        results_pane.setJMenuBar(getMenuBar(getCurrentRepository()));
        cluster_list = new ClusterList(SwingConstants.VERTICAL);
        JScrollPane jsp = new JScrollPane(cluster_list,
                                          JScrollPane.VERTICAL_SCROLLBAR_ALWAYS,
                                          JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        jsp.getViewport().setScrollMode(JViewport.BLIT_SCROLL_MODE);
        jsp.getViewport().setBackground(new Color(0,0,0));
        results_pane.getContentPane().add(jsp);
        jsp.setPreferredSize(new Dimension(550, 700));
        // results_pane.getContentPane().add(cluster_list);
        results_pane.pack();
        results_pane.setDefaultCloseOperation(WindowConstants.HIDE_ON_CLOSE);
    }

    // Methods for FeedbackApp
    // called to signal the application that it has been "opened"
    public void openApplication (String path) {
        System.err.println("openApplication(" + path + ") called");
        if (path != null) {
            Matcher m = PSEUDO_FILE.matcher(path);
            if (m.matches()) {
                String hostname = m.group(1);
                String port = m.group(2);
                String docid = m.group(3);
                newActivation(new String[] { "--repository=https://" + hostname + ":" + port + "/",
                                             "--doc-id=" + docid });
            }
        }
    }

    // called to signal application that it has been "re-opened"
    public void reOpenApplication (String path) {
        System.err.println("reOpenApplication called");
        if (path != null) {
            Matcher m = PSEUDO_FILE.matcher(path);
            if (m.matches()) {
                String hostname = m.group(1);
                String port = m.group(2);
                String docid = m.group(3);
                newActivation(new String[] { "--repository=https://" + hostname + ":" + port + "/",
                                             "--doc-id=" + docid });
            }
        } else {
            Repository r = getCurrentRepository();
            try {
                queryAndShowDocs(null, r);
            } catch (ResourceLoader.PrivilegeViolation x) {
                MessagePane p = new MessagePane("ReadUp on " + r,
                                                "Not allowed:  couldn't get access to repository with given password");
                closer_map.add(p, null);
                p.setVisible(true);
            } catch (ResourceLoader.CommunicationFailure x) {
                MessagePane p = new MessagePane("ReadUp on " + r,
                                                "Can't connect to repository.");
                closer_map.add(p, null);
                p.setVisible(true);
            } catch (UserCancelled e) {
                return;
            } catch (IOException x) {
                MessagePane p = new MessagePane("ReadUp on " + r,
                                                "IOException " + x + " attempting to talk to the repository.");
                closer_map.add(p, null);
                p.setVisible(true);
            }
        }
    }

    // called to signal application that it has been asked to open a document
    public void openDocument(String path) {
        System.err.println("openDocument(" + path + ") called");
        if (path != null) {
            Matcher m = PSEUDO_FILE.matcher(path);
            if (m.matches()) {
                String hostname = m.group(1);
                String port = m.group(2);
                String docid = m.group(3);
                newActivation(new String[] { "--repository=https://" + hostname + ":" + port + "/",
                                             "--doc-id=" + docid });
                    }
        } else {
            Repository r = getCurrentRepository();
            try {
                queryAndShowDocs(path, null);
            } catch (ResourceLoader.PrivilegeViolation x) {
                MessagePane p = new MessagePane("ReadUp on " + r,
                                                "Not allowed:  couldn't get access to repository with given password");
                closer_map.add(p, null);
                p.setVisible(true);
            } catch (ResourceLoader.CommunicationFailure x) {
                MessagePane p = new MessagePane("ReadUp on " + r,
                                                "Can't connect to repository.");
                closer_map.add(p, null);
                p.setVisible(true);
            } catch (UserCancelled e) {
                return;
            } catch (IOException x) {
                MessagePane p = new MessagePane("ReadUp on " + r,
                                                "IOException " + x + " attempting to talk to the repository.");
                closer_map.add(p, null);
                p.setVisible(true);
            }
        }
    }

    // called to signal application to exit
    public void exitApplication () {
        System.err.println("exitApplication called");
        closer_map.closeAll();
    }

    // called to ask the application to open a preferences editor to edit configuration options
    public void editPreferences() {
        System.err.println("exitApplication called");
    };

    // called to ask the application to print a document
    public void printDocument (java.lang.String filename) {
        System.err.println("Document to print is " + filename);
    }

    // called to ask the application to display a splash screen.
    // return false if not interested.
    public boolean showSplashScreen () {
        return false;
    }


    public static String getUpLibVersion() {
        return uplib_version;
    }

    public static Icon getIcon () {
        return readup_icon;
    }

    public void macOSXRegistration() {

        // after the code at http://developer.apple.com/samplecode/OSXAdapter/listing1.html

        if (System.getProperty("os.name").toLowerCase().equals("mac os x")) {
            try {

                Class osxAdapter = Class.forName("com.parc.uplib.util.MacOSXAppSupport");

                Class[] defArgs = {Class.forName("com.parc.uplib.util.FeedbackApp")};
                java.lang.reflect.Method registerMethod = osxAdapter.getDeclaredMethod("setupEventHandling", defArgs);
                if (registerMethod != null) {
                    Object[] args = { this };
                    registerMethod.invoke(osxAdapter, args);
                }

            } catch (NoClassDefFoundError e) {
                System.err.println("This version of Mac OS X does not support the Apple EAWT. (" + e + ")");
            } catch (ClassNotFoundException e) {
                System.err.println("This version of Mac OS X does not support the Apple EAWT. (" + e + ")");
            } catch (Exception e) {
                System.err.println("Exception while loading the OSXAdapter:");
                e.printStackTrace();
            }
        }
    }
        
    static class OurMenuItem extends JMenuItem {

        public Object reference;
        public Repository.Action action;

        public OurMenuItem (Repository.Action action, Object reference, String label, int key) {
            super(label, key);
            this.action = action;
            this.reference = reference;
        }
    }

    private static class WindowItem extends JMenuItem {

        public Window win;
        Repository.Document doc;

        public WindowItem (String label, Window win, Repository.Document doc) {
            super(label, -1);
            if ((label == null) && (win instanceof Frame))
                setLabel(((Frame)win).getTitle());
            this.win = win;
            this.doc = doc;
        }
    }

    private static String menuRepName (Repository r) {
        String n = r.getName();
        URL u = r.getURL();
        int port = u.getPort();
        if (port < 0)
            port = u.getDefaultPort();
        String host = u.getHost();
        int point = host.indexOf('.');
        if (point >= 0)
            host = host.substring(0, point);
        return n + "  (" + u.getHost() + ":" + port + ")";
    }

    private JMenuBar getMenuBar (Object ref) {

        JMenuBar the_menubar;
        JMenuItem item;

        the_menubar = new JMenuBar();

        JMenu file_menu = new JMenu ("Repository");
        the_menubar.add(file_menu);

        Repository.Document doc = null;
        Repository r = null;

        if ((ref != null) && (ref instanceof Repository.Document)) {
            doc = (Repository.Document) ref;
            r = doc.getRepository();
        } else if ((ref != null) && (ref instanceof Repository)) {
            doc = null;
            r = (Repository) ref;
        }

        if (r != null) {

            Repository.Action[] user_actions = r.getUserActions();

            for (int i = 0;  i < user_actions.length;  i++) {
                item = new OurMenuItem(user_actions[i], null, user_actions[i].getLabel(), -1);
                item.addActionListener(this);
                file_menu.add(item);
            }
        }

        // list known repositories
        boolean has_repositories = false;
        for (Iterator i = repositories.values().iterator();  i.hasNext(); ) {
            Repository tmpr = (Repository) (i.next());
            item = new OurMenuItem(null, r, menuRepName(tmpr), -1);
            item.getAccessibleContext().setAccessibleDescription("Find more documents from the repository");
            item.addActionListener(this);
            file_menu.add(item);
            has_repositories = true;
        }
        if (has_repositories) {
            file_menu.addSeparator();
        }

        item = new OurMenuItem(null, null, "Search...", KeyEvent.VK_S);
        item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_S, ActionEvent.META_MASK));
        item.getAccessibleContext().setAccessibleDescription("Find more documents from the repository");
        item.addActionListener(this);
        file_menu.add(item);
            
        item = new OurMenuItem(null, null, "Trail", KeyEvent.VK_T);
        item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_T, ActionEvent.META_MASK));
        item.getAccessibleContext().setAccessibleDescription("Show the current trail");
        item.addActionListener(this);
        file_menu.add(item);

        item = new OurMenuItem(null, r, "Workspace", KeyEvent.VK_W);
        item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_T, ActionEvent.META_MASK));
        item.getAccessibleContext().setAccessibleDescription("Open the workspace");
        item.addActionListener(this);
        file_menu.add(item);

        if (r != null) {

            file_menu.addSeparator();

            item = new OurMenuItem(null, r, "Collections", KeyEvent.VK_O);
            item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_O, ActionEvent.META_MASK));
            item.getAccessibleContext().setAccessibleDescription("Show collections filebox");
            item.addActionListener(this);
            file_menu.add(item);
            
            item = new OurMenuItem(null, r, "Authors", KeyEvent.VK_A);
            item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_A, ActionEvent.META_MASK));
            item.getAccessibleContext().setAccessibleDescription("Show authors filebox");
            item.addActionListener(this);
            file_menu.add(item);
            
            item = new OurMenuItem(null, r, "Categories", KeyEvent.VK_C);
            item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_C, ActionEvent.META_MASK));
            item.getAccessibleContext().setAccessibleDescription("Show categories filebox");
            item.addActionListener(this);
            file_menu.add(item);
            
            item = new OurMenuItem(null, r, "Dates", KeyEvent.VK_D);
            item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_D, ActionEvent.META_MASK));
            item.getAccessibleContext().setAccessibleDescription("Show documents by date");
            item.addActionListener(this);
            file_menu.add(item);
            
        }

        if (doc != null) {

            JMenu edit_menu = new JMenu ("Document");
            the_menubar.add(edit_menu);

            Repository.Action[] doc_functions = doc.getDocumentFunctions();

            for (int i = 0;  i < doc_functions.length; i++) {
                item = new OurMenuItem(doc_functions[i], doc, doc_functions[i].getLabel(), -1);
                item.addActionListener(this);
                edit_menu.add(item);
            }

            edit_menu.addSeparator();

            item = new OurMenuItem(null, doc, "Close", KeyEvent.VK_C);
            item.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_W, ActionEvent.META_MASK));
            item.getAccessibleContext().setAccessibleDescription("Close the current window");
            item.addActionListener(this);
            edit_menu.add(item);
        }

        {
            JMenu windows_menu = new JMenu ("Windows");
            the_menubar.add(windows_menu);

            item = new WindowItem("Search Results", results_pane, null);
            item.getAccessibleContext().setAccessibleDescription("search results");
            item.addActionListener(this);
            windows_menu.add(item);

            if ((collections_box != null) && (collections_box.frame != null)) {
                item = new WindowItem("Collections Filebox", collections_box.frame, null);
                item.getAccessibleContext().setAccessibleDescription("Repository collections");
                item.addActionListener(this);
                windows_menu.add(item);
            }

            if ((authors_box != null) && (authors_box.frame != null)) {
                item = new WindowItem("Authors Filebox", authors_box.frame, null);
                item.getAccessibleContext().setAccessibleDescription("Repository authors");
                item.addActionListener(this);
                windows_menu.add(item);
            }

            if ((categories_box != null) && (categories_box.frame != null)) {
                item = new WindowItem("Categories Filebox", categories_box.frame, null);
                item.getAccessibleContext().setAccessibleDescription("Repository categories");
                item.addActionListener(this);
                windows_menu.add(item);
            }

            if ((dates_box != null) && (dates_box.frame != null)) {
                item = new WindowItem("Dates Filebox", dates_box.frame, null);
                item.getAccessibleContext().setAccessibleDescription("Repository by date");
                item.addActionListener(this);
                windows_menu.add(item);
            }

            windows_menu.addSeparator();

            Iterator i = closer_map.iterator();
            while (i.hasNext()) {
                Map.Entry e = (Map.Entry) (i.next());
                Window w = (Window) (e.getKey());
                DocViewer dv = (DocViewer) (e.getValue());
                Repository.Document d = null;
                String title = null;
                if (dv != null) {
                    Map p = dv.getDocumentProperties();
                    URL rurl = (URL) (p.get("repository-URL"));
                    Repository repo = (rurl != null) ? findRepository(rurl.toExternalForm()) : null;
                    String did = (String) (p.get("id"));
                    d = ((repo == null) || (did == null)) ? null : repo.getDocument(did);
                    title = (String) (p.get("title"));
                }
                item = new WindowItem(title, w, d);
                item.getAccessibleContext().setAccessibleDescription(item.getLabel());
                item.addActionListener(this);
                windows_menu.add(item);
            }
            
        }

        return the_menubar;
    }

    // methods for AncestorListener

    public void ancestorAdded (AncestorEvent e) {
    }

    public void ancestorRemoved (AncestorEvent e) {
    }

    public void ancestorMoved (AncestorEvent e) {
        /*
        Container c = e.getComponent().getTopLevelAncestor();
        if (c instanceof JFrame) {
            JFrame f = (JFrame) c;
            int x = f.getX();
            int y = f.getY();
            int width = f.getWidth();
            int height = f.getHeight();
            Rectangle r = ((Graphics2D)(f.getGraphics())).getDeviceConfiguration().getBounds();
            // System.err.println("device bounds are " + r + "; window bounds are " + f.getBounds());
            if (f.getContentPane().getComponent(0) instanceof ResizableDocViewer) {
                ResizableDocViewer rdv = (ResizableDocViewer) (f.getContentPane().getComponent(0));
                if (x < 200) {
                    float scaling = x/200.0F;
                    if (scaling < 0.2)
                        scaling = 0.2F;
                    Dimension d = rdv.getPreferredSize();
                    // System.err.println("Scaling is " + scaling + ", preferred size is " + d);
                    f.setSize((int)(d.width * scaling), (int)(d.height * scaling));
                    f.invalidate();
                } else {
                    // System.err.println("XScale is " + rdv.getXScale() + ", yscale is " + rdv.getYScale());
                    if ((rdv.getXScale() > 1.0) || (rdv.getYScale() > 1.0)) {
                        // System.err.println("Resizing to unit transform");
                        rdv.resizeToUnitTransform();
                    }
                }
            }
        }
        */
    }

    // methods for NodeListener

    public void nodeClicked (Node n) {
        try {
            showDocument(n.getDocument());
        } catch (Exception e) {
            e.printStackTrace(System.err);
        }
    }

    // methods for ActionListener

    /*
    private void showResult (HttpURLConnection c) throws Exception {
        String ct = c.getContentType();
        System.err.println("content-type is " + ct);
        String suffix = null;
        if (ct.toLowerCase().startsWith("text/plain"))
            suffix = ".txt";
        else if (ct.toLowerCase().startsWith("text/html"))
            suffix = ".html";
        else if (ct.toLowerCase().startsWith("application/pdf"))
            suffix = ".pdf";
        else
            suffix = ".txt";
        File t = File.createTempFile("ReadUp-", suffix);
        t.deleteOnExit();
        FileOutputStream fp = new FileOutputStream(t);
        InputStream is = (InputStream) c.getContent();
        byte[] buffer = new byte[2 << 16];
        int status;
        while ((status = is.read(buffer, 0, buffer.length)) >= 0) {
            fp.write(buffer, 0, status);
        }
        fp.close();
        is.close();
        BrowserLauncher.openURL("file:" + t.getCanonicalPath());   
    }
    */

    private void showFilebox(FileBoxHolder box, String title) {
        JFrame f = box.getFrame(title);
        f.setJMenuBar(getMenuBar(box.getRepository()));
        f.setVisible(true);
    }

    public void actionPerformed(ActionEvent e) {
        try {
            if (e.getActionCommand().equals("Search...")) {
                reOpenApplication(null);
            } else if (e.getActionCommand().equals("Trail")) {
                if (current_trail != null) {
                    Trail.TrailView view = current_trail.getView(Trail.TrailView.HORIZONTAL);
                    view.setDocumentOpener(this);
                    JScrollPane jsp = new JScrollPane (view, JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED, JScrollPane.HORIZONTAL_SCROLLBAR_ALWAYS);
                    jsp.getViewport().setScrollMode(JViewport.BLIT_SCROLL_MODE);
                    jsp.getViewport().setBackground(new Color(0,0,0));
                    view.doLayout();
                    Dimension d = view.getPreferredSize();
                    jsp.getViewport().setSize(Math.min(800, d.width), d.height);
                    JFrame top = new JFrame();
                    top.getContentPane().add(jsp);
                    top.pack();
                    top.setDefaultCloseOperation(WindowConstants.DISPOSE_ON_CLOSE);
                    top.setVisible(true);
                }
            } else if (e.getActionCommand().equals("Workspace")) {
                JFrame f = new JFrame("ReadUp Workspace");
                Vector repos = Repository.knownRepositories();
                if (repos.size() == 0) {
                    Repository r = (Repository) ((OurMenuItem)(e.getSource())).reference;
                    if (r != null)
                        repos.add(r);
                }
                if (repos.size() > 0) {
                    Workspace w = new Workspace(repos);
                    w.setPreferredSize(new Dimension(900, 800));
                    w.setDocumentOpener(this);
                    f.getContentPane().add(w);
                    f.setDefaultCloseOperation(WindowConstants.DISPOSE_ON_CLOSE);
                    f.pack();
                    f.setVisible(true);
                }
            } else if (e.getActionCommand().equals("Close")) {
                Window win = KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusedWindow();
                System.err.println("win is " + win);
                closer_map.windowClosing(new WindowEvent((Window) win, WindowEvent.WINDOW_CLOSING));
            } else if (e.getActionCommand().equals("Authors")) {
                Repository r = (Repository) ((OurMenuItem)(e.getSource())).reference;
                if ((authors_box == null) || (!authors_box.match(r))) {
                    if (authors_box != null)
                        authors_box.discard();
                    authors_box = new FileBoxHolder(CardCatalog.AuthorsBox(r, this), r);
                }
                showFilebox(authors_box, "Authors");
            } else if (e.getActionCommand().equals("Collections")) {
                Repository r = (Repository) ((OurMenuItem)(e.getSource())).reference;
                if ((collections_box == null) || (!collections_box.match(r))) {
                    if (collections_box != null)
                        collections_box.discard();
                    collections_box = new FileBoxHolder(CardCatalog.CollectionsBox(r, this), r);
                }
                showFilebox(collections_box, "Collections");
            } else if (e.getActionCommand().equals("Categories")) {
                Repository r = (Repository) ((OurMenuItem)(e.getSource())).reference;
                if ((categories_box == null) || (!categories_box.match(r))) {
                    if (categories_box != null)
                        categories_box.discard();
                    categories_box = new FileBoxHolder(CardCatalog.CategoriesBox(r, this), r);
                }
                showFilebox(categories_box, "Categories");
            } else if (e.getActionCommand().equals("Dates")) {
                Repository r = (Repository) ((OurMenuItem)(e.getSource())).reference;
                if ((dates_box == null) || (!dates_box.match(r))) {
                    if (dates_box != null)
                        dates_box.discard();
                    dates_box = new FileBoxHolder(CardCatalog.DateBox(r, this), r);
                }
                showFilebox(dates_box, "Documents by date");
            } else if (e.getSource() instanceof WindowItem) {
                Window w = (Window) ((WindowItem)(e.getSource())).win;
                Repository.Document d = (Repository.Document) ((WindowItem)(e.getSource())).doc;
                if (w instanceof JFrame)
                    ((JFrame)w).setJMenuBar(getMenuBar(d));
                if (!w.isVisible())
                    w.setVisible(true);
                w.toFront();
            } else if (e.getSource() instanceof OurMenuItem) {
                OurMenuItem item = (OurMenuItem) (e.getSource());
                Repository.Document doc = (Repository.Document) item.reference;
                if (item.action != null) {
                    String url = item.action.getURLString();
                    if (url != null) {
                        if (doc != null) {
                            url = url.replaceAll("%s", doc.getID());
                            DocViewer dv = closer_map.get(doc);
                            if ((dv != null) && url.contains("?")) { 
                                // add in info about current page index and selection, if any
                                int page = dv.getSelectionPage();
                                if (page < 0)
                                    page = dv.getPage();
                                if (page >= 0)
                                    url += "&currentpage=" + dv.getPage();
                                Point selectionspan = dv.getSelectionSpan();
                                if (selectionspan != null)
                                    url += "&selectionspan=" + selectionspan.x + ":" + selectionspan.y;
                                else {
                                    Rectangle r = dv.getSelectionRect();
                                    if (r != null)
                                        url += "&selectionrect=" + r.x + ":" + r.y + ":" + r.width + ":" + r.height;
                                }
                            }
                        }
                        // System.err.println("URL is \"" + url + "\"");
                        try {
                            if (urlopenerservice != null)
                                urlopenerservice.showDocument(new URL(url));
                            else
                                BrowserLauncher.openURL(url);
                        } catch (Exception x) {
                            x.printStackTrace(System.err);
                        }
                    }
                }
            }
            /*
              try {
              File f = ((Repository.Document)o).getPDFVersion();
              BrowserLauncher.openURL("file:" + f.getCanonicalPath());
              } catch (Exception x) {
              x.printStackTrace(System.err);
              }
            */

        } catch (IOException x) {
            x.printStackTrace(System.err);
        }
    }

    // methods for SingleInstanceListener

    public void newActivation (String[] args) {

        boolean show_two_pages = this.two_page;
        String password = null;
        String[] doc_ids = null;
        String basename = null;
        String cookie = null;
        int page = -1;

        System.err.println("local args are ");
        for (int i = 0;  i < args.length;  i++) {
            System.err.println("   " + args[i]);
        }

        for (int i = 0;  i < args.length;  i++) {
            if (args[i].equals("--twopage"))
                show_two_pages = true;
            else if (args[i].startsWith("--password")) {
                Matcher m = PASSWORD_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    password = m.group(1);
                }
            }
            else if (args[i].startsWith("--doc-id=")) {
                Matcher m = DOCID_ARG.matcher(args[i]);
                if (!m.matches()) {
                    System.err.println("Bad doc-id arg:  " + args[i]);
                    usage();
                } else {
                    String[] n = new String[((doc_ids == null) ? 1 : (1 + doc_ids.length))];
                    if (doc_ids != null) {
                        int j = 0;
                        for (;  j < doc_ids.length;  j++)
                            n[j] = doc_ids[j];
                        n[j] = m.group(1);
                    } else {
                        n[0] = m.group(1);
                    }
                    doc_ids = n;
                }
            }
            else if (args[i].startsWith("--repository=")) {
                Matcher m = BASENAME_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    basename = m.group(1);
                }
            }
            else if (args[i].startsWith("--page=")) {
                Matcher m = PAGE_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    page = Integer.parseInt(m.group(1));
                }
            }
            else if (args[i].startsWith("--cookie")) {
                Matcher m = COOKIE_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    cookie = m.group(1);
                }
            }
            else if (args[i].startsWith("-")) {
                System.err.println("Invalid argument:  " + args[i]);
                usage();
            }
            else
                break;
        }

        Repository repo;

        if (basename != null) {
            try {
                repo = setCurrentRepository(basename, password);
                if (cookie != null) {
                    System.err.println("cookie is " + cookie);
                    repo.setCookie(cookie);
                }
            } catch (MalformedURLException x) {
                System.err.println("Malformed URL:  " + basename);
                return;
            }
        } else {
            repo = getCurrentRepository();
        }
            
        System.err.println("repo is " + repo);

        if ((repo != null) && (doc_ids != null)) {
            System.err.print("doc_ids are ");
            for (int j = 0;  j < doc_ids.length;  j++)
                System.err.print(" " + doc_ids[j]);
            System.err.println("");

            for (int j = 0;  j < doc_ids.length;  j++) {
                try {
                    showDocument (repo.getDocument(doc_ids[j]), page);
                } catch (Exception x) {
                    System.err.println("Exception " + x + " attempting to open doc " + doc_ids[j] + " at " + basename);
                    x.printStackTrace(System.err);
                }
            }
        }
    }

    // main program

    public static void main(String[] args) {

        String basename = null;
        String hostname = null;
        String password = null;
        String cookie = null;
        String url = null;
        boolean nosplash = false;
        boolean resizable = false;      // drag-and-drop doesn't work with resizing
        boolean keep_running = false;
        java.util.Vector local_args;
        String doc_ids[] = null;
        File output_file = null;
        float cutoff = 0.0F;
        int i;
        boolean opened = false;
        int animation_time = -1;
        boolean debug_output = false;
        boolean show_two_pages = false;
        boolean workspace = false;
        Closer the_closer;
        Pattern ANIMATION_ARG = Pattern.compile("--animate=([0-9]+)");
        Pattern QUERYCUTOFF_ARG = Pattern.compile("--cutoff=([0-9]+)(\\.[0-9]+)*");

        ClassLoader cl = UpLibShowDoc.class.getClassLoader();
        System.err.println("cl is " + cl);
        // Read logo icons
        URL logo = cl.getResource("ReadUp-logo.png");
        System.err.println("logo is " + logo);
        readup_icon = new ImageIcon (logo, "the ReadUp logo");
        try {
            readup_favicon = ImageIO.read(cl.getResourceAsStream("readup-favicon.png"));
        } catch (IOException x) {
            System.err.println("Couldn't read favicon file:");
            x.printStackTrace(System.err);
        }

        System.err.println("args are ");
        for (i = 0;  i < args.length;  i++) {
            System.err.println("   " + args[i]);
        }

        // process the global args
        local_args = new java.util.Vector();
        for (i = 0;  i < args.length;  i++) {
            if (args[i].equals("--debug"))
                debug_output = true;
            else if (args[i].equals("--workspace"))
                workspace = true;
            else if (args[i].equals("--resizable"))
                resizable = true;
            else if (args[i].equals("--non-resizable"))
                resizable = false;
            else if (args[i].startsWith("--animate=")) {
                Matcher m = ANIMATION_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    animation_time = Integer.parseInt(m.group(1));
                }
            }
            else if (args[i].startsWith("--cookie=")) {
                Matcher m = COOKIE_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    cookie = m.group(1);
                }
                local_args.add(args[i]);
            }
            else if (args[i].startsWith("--cutoff=")) {
                Matcher m = QUERYCUTOFF_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    cutoff = Float.parseFloat(m.group(1) + m.group(2));
                }
            }
            else if (args[i].startsWith("--nosplash")) {
                nosplash = true;
            }
            else if (args[i].startsWith("--repository=")) {
                Matcher m = BASENAME_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    basename = m.group(1);
                }
                local_args.add(args[i]);
            }
            else if (args[i].startsWith("--hostname=")) {
                Matcher m = HOSTNAME_ARG.matcher(args[i]);
                if (!m.matches())
                    usage();
                else {
                    hostname = m.group(1);
                }
            } else if (args[i].startsWith("-")) {
                local_args.add(args[i]);
            } else
                break;
        }

        // now do the global actions
        if (!debug_output) {
            try {
                File debug_stream = new File("/dev/null");
                if (!(debug_stream.exists() && debug_stream.canWrite())) {
                    debug_stream = File.createTempFile("ReadUp", ".txt");
                    debug_stream.deleteOnExit();
                }
                System.setErr(new PrintStream(new FileOutputStream(debug_stream)));
            } catch (Exception e) {
                e.printStackTrace(System.err);
            }
        }

        if (workspace) {
            try {
                UIManager.setLookAndFeel("net.sourceforge.napkinlaf.NapkinLookAndFeel");
            } catch (Exception e) {
                // OK if not present
            }
        }

        boolean is_windows = System.getProperty("os.name").toLowerCase().startsWith("win");
        try {
            // on Macs, use Quartz for drawing instead of Sun's slow code
            System.setProperty("apple.awt.graphics.UseQuartz","true");
            // turn off resizing corner on Mac OS X
            System.setProperty("apple.awt.showGrowBox", "false");
            // turn off traversal of applications on OS X
            System.setProperty("JFileChooser.appBundleIsTraversable", "never");
            // Make sure we use the screen-top menu on OS X
            System.setProperty("com.apple.macos.useScreenMenuBar", "true");
            System.setProperty("apple.laf.useScreenMenuBar", "true");

            if (!is_windows)
                EmacsKeymap.setupEmacsKeymap();
        } catch (SecurityException x) {
            // can't do this in JWS
        }

        Configurator conf = null;
        try {
            conf = new Configurator();
            keep_running = conf.getBool("readup-keep-running-with-no-windows", false);
            uplib_version = conf.get("UPLIB_VERSION", "(unknown)");
            System.err.println("version is " + uplib_version);
            if (basename == null)
                url = conf.get("default-repository");
        } catch (IOException x) {
            System.err.println("Couldn't read configuration files:");
            x.printStackTrace(System.err);
        } catch (java.security.AccessControlException x) {
            System.err.println("Couldn't read configuration files:");
            x.printStackTrace(System.err);
        }

        the_closer = new Closer();
        try {
            Runtime.getRuntime().addShutdownHook(new ShutdownHook(the_closer));
        } catch (java.security.AccessControlException x) {
            x.printStackTrace(System.err);
        }

	basename = (url == null) ? null : (url.endsWith("/")) ? url : url+"/";

        UpLibShowDoc app = new UpLibShowDoc(the_closer, doc_ids,
                                            basename, password, cookie, hostname,
                                            resizable, cutoff, animation_time,
                                            nosplash, show_two_pages, conf);

        try { 
            javax.jnlp.SingleInstanceService sis = 
                (SingleInstanceService)javax.jnlp.ServiceManager.lookup("javax.jnlp.SingleInstanceService");
            sis.addSingleInstanceListener(app);
            System.err.println("registered SingleInstanceListener");
        } catch (javax.jnlp.UnavailableServiceException e) {
            System.err.println("can't get an instance of javax.jnlp.SingleInstanceService");
        }

        Repository current_repository = app.getCurrentRepository();

        if (workspace && (current_repository != null)) {
            JFrame f = new JFrame("ReadUp Workspace");
            Vector repos = new Vector();
            repos.add(current_repository);
            Workspace w = new Workspace(repos);
            w.setPreferredSize(new Dimension(900, 800));
            w.setDocumentOpener(app);
            f.getContentPane().add(w);
            f.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
            f.pack();
            f.setVisible(true);
        }

        app.newActivation((String[]) (local_args.toArray(new String[local_args.size()])));

        if (!workspace && (basename != null) && (args.length > i) && (current_repository != null)) {
            if (is_windows && (args.length == (i + 1)) && (new File(args[i])).exists()) {
                // treat this as a file query
                try {
                    if (!app.queryAndShowDocs("localfile:" + args[i], current_repository)) {
                        MessagePane p = new MessagePane("ReadUp on " + args[i],
                                                        "No UpLib documents for file " + args[i] + " found.");
                        the_closer.add(p, null);
                        p.setVisible(true);
                        System.exit(0);
                    }
                } catch (ResourceLoader.PrivilegeViolation x) {
                    MessagePane p = new MessagePane("ReadUp on " + basename,
                                                    "Not allowed:  couldn't get access to repository with given password");
                    the_closer.add(p, null);
                    p.setVisible(true);
                } catch (ResourceLoader.CommunicationFailure x) {
                    MessagePane p = new MessagePane("ReadUp on " + basename,
                                                    "Can't connect to repository.");
                    the_closer.add(p, null);
                    p.setVisible(true);
                } catch (UserCancelled e) {
                    // shouldn't occur
                    e.printStackTrace(System.err);
                } catch (IOException x) {
                    MessagePane p = new MessagePane("ReadUp on " + basename,
                                                    "IOException " + x + " attempting to talk to the repository.");
                    the_closer.add(p, null);
                    p.setVisible(true);
                }
            } else {
                String query = null;
                query = args[i];
                for (int j = i+1;  j < args.length;  j++)
                    query += " " + args[j];
                try {
                    app.current_showall = true;
                    opened = app.queryAndShowDocs (query, null);
                } catch (ResourceLoader.PrivilegeViolation x) {
                    MessagePane p = new MessagePane("ReadUp on " + basename,
                                                    "Not allowed:  couldn't get access to repository with given password");
                    the_closer.add(p, null);
                    p.setVisible(true);
                } catch (ResourceLoader.CommunicationFailure x) {
                    MessagePane p = new MessagePane("ReadUp on " + basename,
                                                    "Can't connect to repository.");
                    the_closer.add(p, null);
                    p.setVisible(true);
                } catch (UserCancelled e) {
                } catch (IOException x) {
                    MessagePane p = new MessagePane("ReadUp on " + basename,
                                                    "IOException " + x + " attempting to talk to the repository.");
                    the_closer.add(p, null);
                    p.setVisible(true);
                }
            }
        }
        
        if ((!workspace) && (!the_closer.hasWindows())) {
            try {
                while (!opened) {
                    opened = app.queryAndShowDocs(null, null);
                }
            } catch (ResourceLoader.PrivilegeViolation x) {
                MessagePane p = new MessagePane("ReadUp on " + current_repository,
                                                "Not allowed:  couldn't get access to repository with given password");
                the_closer.add(p, null);
                p.setVisible(true);
            } catch (ResourceLoader.CommunicationFailure x) {
                x.printStackTrace(System.err);
                MessagePane p = new MessagePane("ReadUp on " + current_repository,
                                                "Can't connect to repository.");
                the_closer.add(p, null);
                p.setVisible(true);
            } catch (UserCancelled e) {
            } catch (IOException x) {
                MessagePane p = new MessagePane("ReadUp on " + current_repository,
                                                "IOException " + x + " attempting to talk to the repository.");
                the_closer.add(p, null);
                p.setVisible(true);
            }
        }


        while (true) {
            while (the_closer.hasWindows() || workspace) {
                try {
                    Thread.sleep(100);  // sleep 100 ms
                } catch (InterruptedException x) {
                    System.err.println("Interrupted!");
                };
            }
            try {
                Thread.sleep(20000);  // sleep 20 seconds
            } catch (InterruptedException x) {
                System.err.println("Interrupted!");
            };
            if ((!keep_running) && (!workspace) && 
                (!the_closer.hasWindows()) &&
                ((app.results_pane == null) || (!app.results_pane.isVisible()))) {
                try { 
                    javax.jnlp.SingleInstanceService sis = 
                        (SingleInstanceService)javax.jnlp.ServiceManager.lookup("javax.jnlp.SingleInstanceService");
                    sis.removeSingleInstanceListener(app);
                    System.err.println("unregistered SingleInstanceListener");
                } catch (javax.jnlp.UnavailableServiceException e) {
                }
                System.exit(0);
            }
        }
    }
}
