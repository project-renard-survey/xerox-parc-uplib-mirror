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

public class FileBox extends JPanel implements MouseInputListener {

    static TexturePaint card_background;
    static TexturePaint divider_background;
    static Color divider_edge = new Color(0xd5, 0xbc, 0xa4);
    static Font divider_font = Font.decode("Times-BOLD-16");
    static Color card_edge = new Color(0xee, 0xea, 0xc9);
    static Color WHITEWASH = new Color(0xFF, 0xFF, 0xFF, 0x60);
    private static Color HALFGRAY = new Color(0.5f, 0.5f, 0.5f);
    private static Color GRAYWASH = new Color(0f, 0f, 0f, 0.1f);
    private static Color CLEAR = new Color(255, 255, 255, 0);

    static {
        try {
            BufferedImage card_background_image = DataURL.decode("data:image/png;base64,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");
            card_background = new TexturePaint (card_background_image, new Rectangle(0,0,card_background_image.getWidth(null), card_background_image.getHeight(null)));
            BufferedImage divider_background_image = new BufferedImage(card_background_image.getWidth(null),
                                                                       card_background_image.getHeight(null),
                                                                       BufferedImage.TYPE_INT_ARGB);
            Graphics g2 = divider_background_image.getGraphics();
            g2.drawImage(card_background_image, 0, 0, card_background_image.getWidth(null), card_background_image.getHeight(null), null);
            g2.setColor(new Color(1.0f, 0.0f, 0.0f, 0.1f));
            g2.fillRect(0, 0, divider_background_image.getWidth(null), divider_background_image.getHeight(null));
            divider_background = new TexturePaint (divider_background_image, new Rectangle(0,0,divider_background_image.getWidth(null), divider_background_image.getHeight(null)));
        } catch (Exception x) {
            x.printStackTrace(System.err);
            System.exit(1);
        }
    }


    public interface CardRun {

        public int size();

        public String label(int index);
        public String body (int index);
        public void open (int index);
    }

    // static Font card_body_font = Font.decode("AmericanTypewriter-PLAIN-12");
    // static Font card_body_font = Font.decode("FeltTipRoman-PLAIN-12");

    public static class StaticCardRun implements CardRun {

        private String[] labels;
        private String[] bodies;

        public StaticCardRun (String[] labels, String[] bodies) {
            this.labels = labels;
            this.bodies = bodies;
        }

        public int size () {
            return labels.length;
        }

        public String label(int index) {
            if ((index >= 0) && (index < labels.length))
                return labels[index];
            else
                return null;
        }

        public String body (int index) {
            if ((index >= 0) && (index < bodies.length))
                return bodies[index];
            else
                return null;
        }

        public void open (int index) {
        }
    }

    public static class DocumentCardRun extends StaticCardRun {

        private URL[] docurls;
        HyperlinkListener listener;

        public DocumentCardRun (String[] labels, String[] bodies, URL[] docurls, HyperlinkListener listener) {
            super(labels, bodies);
            this.docurls = docurls;
            this.listener = listener;
        }

        public void open (int index) {
            listener.hyperlinkUpdate(new HyperlinkEvent("", HyperlinkEvent.EventType.ACTIVATED, docurls[index]));
        }
    }

    static class CardRunViewer extends JPanel implements MouseWheelListener, MouseInputListener, ActionListener, KeyListener, ComponentListener {

        // static Font divider_font = Font.decode("Helvetica-BOLD-16");
        // static Font card_font = Font.decode("1942report-PLAIN-12");
        static Font card_font = Font.decode("Times-PLAIN-16");
        static BufferedImage pushpin = null;
        static BufferedImage pushpin_ghost = null;
        static Color card_background = new Color(0xff, 0xff, 0xff);
        static Color card_edge = new Color(0xee, 0xea, 0xc9);
        static Color card_edge_fill = new Color(0xf6, 0xf4, 0xe4);

        static int zone_size_max = 4;
        static int collapsed_multiplier = 6;

        static {
            try {
                pushpin = DataURL.decode("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAdCAYAAADLnm6HAAAEjklEQVR42rWWW0xcVRSG18zAMMyNYabcbGnBKmktIVZ7CYGIbYg0MbEYL4nVVMOLIlV8sTxYRTTGpt5NNBprDMamgAlNfai1vli1VlqV1hojeGsqSqWJpShlgJnZfnvOEIfTMzAT6U7+nHP22Wutf9323iILN0JgI3gb9IPT4GvwBtgA7HKZRgC8DAavd0rsWY/EugIy1p0nI8/nyV+NOXIx1yGK/0fBmoU2HnLa5ERbSP7e5pZYZJEoZYERsM0nKsshE8g0ZWJgMbg6EV6r0fOoX9Tj+aL+KbA2noyPAqJ8Dokit2U+ww02ka9Ks2S63C7KbZcwc9+AuqQ1lS6bRIZCotrTMD6DfUFR6L6A/JJUxpurcyXSj+IIimMInS8UtRfB14rlE1Uny0fXSfmWgHxWmysqzL9n8tInoHGzK14TL1oZX3ttjkyNFV0qNA0Ogru9Ml3ilEm3U1QLhseXiHq6JDMCB3HOa5MnrAh8ejh4qcC3RGI9BtfniHqV/9/j9QYPuQdh/j0ZyIzAJDKFznhKVyQbr6rySixmyucR2K4gZPsotmjSfANz2z1Gih7xZEZA414jDS8kE+ho881edA7jq1k4YOHhfay9y228txZkTqA7P06gP5nAhz2m8HeQ43d81gp2Mb/KaUSgxSvqQoYETgZlCptjyQTOHDN5WuNO3d/H8CCbFj1NlN4iPe9n2Ak/L5JxbKpkAuHBpGoeLxZV606tQHfFlVmiXoL0b7zX58yukTQioDek0RnjLhAZKP5vwXCBEYG5lOjqX8k+P8n77RRiTwbd8F4g7n3fDIEsTeB4/uwIXIVX03MU2Fn2izyi8C7KTrBuMWR+CaVHYLMnTuCp5BSM7DcV4Up2uh/mUbSL3Jdg+CwE2inMCuri18K5Zb6ApN0mk9hclkzgy52mQnoYhTvmSYMOfx3d0EC0wrxvZf0VRIUjWUUtojfA3FLjeO4w74KvN+aaKh0lhXh0fp6wDocMz7ciP877c7RlHt+V7CE7cGIP3108t9Mtfnvc+O5E2meNO/LxJGw6BzbjWUsaxXWG+lmL/I2s/5HvP/XhxfM2SK0j3zUQ2MjzOr+0YstmNu4AjSDWa6qDIb6X6pCmUVy6Dq7BUJFLovfgdSekDiG3F8+bvTJR4JJObOSajesLxweVlZWR0tLSCd375n7uQ8kyl3EkpzJ+CqzG+1VeOXlDgazxOOQW9LaBxxIXkOJU5//R6urqaHt7+0RTU5PeGmOdFiEfwHgNIbwTfA6hUVI1Sqv26a2YuRBReoUirjfa64FMrl07y8rKIrW1tTGfzzfEd6+fKv0uZL376VPxVsK7nEiVEpUKvH6IsA8GjXNB747oqM+EQBDsT1wWXYl66C13GYWVKuS6xaZMc38QlWyHXEzo/F/DB45UEImfitLfXnf7494fWKgrdz44XJxNJQfTuOWAKpfEkNm0kPd+nZI3HXaJNpPzcymI6K5pNW443VY9vhDjJnAqYBP1IAV4ACJDXEaH2fMPUSeb3HHjHwO/XMahi1P3dhf4Xbcr0AfKcXC/1daazvgXLLRIWwSbcMQAAAAASUVORK5CYII=");
                pushpin_ghost = new BufferedImage(pushpin.getWidth(null), pushpin.getHeight(null), BufferedImage.TYPE_INT_ARGB);
                Graphics2D g = (Graphics2D) pushpin_ghost.getGraphics();
                g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, 0.1f));
                g.drawImage(pushpin, 0, 0, pushpin.getWidth(null), pushpin.getHeight(null), null);
            } catch (Exception x) {
                x.printStackTrace(System.err);
                System.err.println("Can't read pushpin image");
                System.exit(1);
            }
        }

        public static int getFocusZoneSize () {
            return zone_size_max;
        }

        public static int getCollapsedSize (int ncards, int zsize) {
            if (ncards > (zsize + 2))
                return (int) Math.max(4, Math.round(Math.log(ncards) * collapsed_multiplier));
            else if (ncards > (zsize + 1))
                return (int) Math.max(2, Math.round(Math.log(ncards) * collapsed_multiplier));
            else
                return 0;
        }

        public static Dimension getNormalSize (int ncards, int tab_height, int zone_size, int card_width, int card_height) {
            int ntabs = Math.min(ncards - 1, zone_size);
            int bwidth = getCollapsedSize(ncards, zone_size);
            return new Dimension(card_width + ntabs * 2 + bwidth,
                                 card_height + ntabs * tab_height + bwidth);            
        }

        private Paint background;
        private CardRun run;
        private int first_top = 0;      /* top edge of first card */
        private int last_top;           /* top edge of last card */
        private int zone_start;
        private int zone_size;
        private int zone_top;
        private int zone_bottom;
        private int border_width;
        private int back_border;
        private int front_border;
        private double front_span;
        private double back_span;
        private int[] front_polygon_x = new int[6];
        private int[] front_polygon_y = new int[6];
        private int[] back_polygon_x = new int[6];
        private int[] back_polygon_y = new int[6];
        private int top = -1;
        private ArrayList action_listeners;
        private JEditorPane editor;
        private JScrollPane content_window;
        private int runsize;
        private int cardwidth;
        private int cardheight;
        private Rectangle pushpin_rect;
        private boolean pinned = false;
        private int tab_height;

        public CardRunViewer (int width, int height, int tab_height, CardRun run) {
            this.background = background;
            this.tab_height = tab_height;
            this.zone_start = 1;
            this.editor = new JEditorPane("text/html", "");
            this.editor.setOpaque(false);
            this.editor.setFont(card_font);
            this.editor.setEditable(false);
            content_window = new JScrollPane(this.editor,
                                             JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED,
                                             JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
            content_window.getViewport().setScrollMode(JViewport.BLIT_SCROLL_MODE);
            content_window.getViewport().setOpaque(false);
            content_window.setBorder(null);
            content_window.setViewportBorder(null);
            content_window.setOpaque(false);
            content_window.setVisible(true);
            add(content_window);
            this.pushpin_rect = new Rectangle(0, 0, pushpin.getWidth(null), pushpin.getHeight(null));
            setLayout(null);
            setOpaque(false);
            setFocusable(true);
            action_listeners = new ArrayList();
            setPreferredSize(new Dimension(width, height));
            setCardRun (run);
            addActionListener(this);
            addMouseListener(this);
            addMouseMotionListener(this);
            addMouseWheelListener(this);
            addKeyListener(this);
            addComponentListener(this);
            setTop(0);
            setZoneStart(1);
        }

        public void setCardRun (CardRun run) {
            this.run = run;
            runsize = run.size();
            zone_size = Math.min(runsize - 1, zone_size_max);
            border_width = getCollapsedSize(runsize, zone_size);
            Dimension d = getPreferredSize();
            cardheight = d.height - border_width - (zone_size * tab_height);
            cardwidth = d.width - (2 * zone_size) - border_width;
            first_top = border_width + (zone_size * tab_height);
            last_top = 0;
            zone_start = -1;
            top = -1;
            setZoneStart(1);
            setTop(0);
        }

        public Dimension figurePreferredSize (int cwidth, int cheight) {
            int zsize = Math.min(runsize - 1, zone_size_max);
            int bwidth = getCollapsedSize(runsize, zsize);
            Dimension d = new Dimension(cwidth + bwidth + (2 * zsize),
                                        cheight + bwidth + (tab_height * zsize));
            setPreferredSize(d);
            setCardRun(run);
            return d;
        }

        public Dimension figurePreferredSize (CardRun newrun) {
            int zsize = Math.min(newrun.size() - 1, zone_size_max);
            int bwidth = getCollapsedSize(newrun.size(), zsize);
            Dimension d = new Dimension(cardwidth + bwidth + (2 * zsize),
                                        cardheight + bwidth + (tab_height * zsize));
            setPreferredSize(d);
            setCardRun(run);
            return d;
        }

        public int count () {
            return run.size();
        }

        private int figureCard (int yval) {
            if ((yval < 0) || (yval > getHeight()))
                return -1;
            if (yval < zone_top) {
                // in back_span
                // return (int) Math.min(runsize - 1, zone_start + zone_size + Math.round(Math.exp(zone_top - yval) * (runsize - (zone_start + zone_size))/back_span));
                return (int) Math.min(runsize - 1, zone_start + zone_size + ((zone_top - yval) * (runsize - (zone_start + zone_size)))/back_border);
            }
            else if (yval >= first_top)
                return 0;
            else if (yval > zone_bottom) {
                // in front_span
                // return (int) Math.max(0, Math.round(Math.exp(first_top - yval) * (zone_start - 1) / front_span));
                return (int) Math.max(0, Math.round((first_top - yval) * (zone_start - 1) / front_border));
            }
            else
                return (zone_start + zone_size - 1) - (yval - zone_top)/tab_height;
        }

        private int figureCardTop (int cardindex) {
            if (cardindex == (runsize - 1))
                return last_top;
            else if (cardindex == 0)
                return first_top;
            else if ((cardindex - zone_start) < zone_size)
                return back_border + tab_height * (zone_size - 1 - (cardindex - zone_start));
            else
                throw new RuntimeException("cardindex " + cardindex + " not in zone " + zone_start + ":" + (zone_start + zone_size - 1) + "  [" + runsize + " cards]");
        }

        private int figureCardLeft (int cardindex) {
            if (cardindex == (runsize - 1))
                return border_width + (2 * zone_size);
            else if (cardindex == 0)
                return 0;
            else if ((cardindex - zone_start) < zone_size)
                return front_border + (2 * (cardindex - zone_start + 1));
            else
                throw new RuntimeException("cardindex " + cardindex + " not in zone " + zone_start + ":" + (zone_start + zone_size - 1) + "  [" + runsize + " cards]");
        }

        public void setTop (int newtop, boolean refigureZone) {
            int oldtop = top;
            top = newtop;
            if (refigureZone) {
                if (newtop >= (zone_start + zone_size))
                    setZoneStart(newtop - zone_size + 1);
                else if (newtop < zone_start)
                    setZoneStart(newtop);
            }
            if (oldtop != newtop) {
                int cardtop = figureCardTop(newtop);
                int cardleft = figureCardLeft(newtop);
                // System.err.println("top changed to " + top + ", \"" + titles[top] + "\"");
                pushpin_rect.x = cardleft + cardwidth - pushpin_rect.width - 5;
                pushpin_rect.y = cardtop + 5;
                int editor_top = Math.max(cardtop + tab_height + 2, pushpin_rect.y + pushpin_rect.height + 5);
                content_window.setBounds(cardleft + 15, editor_top,
                                         cardwidth - 30, cardheight - (editor_top - cardtop + 15));
                editor.setText(run.body(top));
                // System.err.println("text is \"" + run.body(top) + "\"");
                editor.setCaretPosition(0);
                repaint();
            }
        }

        public void setTop (int newtop) {
            setTop (newtop, true);
        }

        private void adjustZone (Point p) {
            if (!pinned) {
                int old_start = zone_start;
                if (p.y > getHeight())
                    setZoneStart(1);
                else if (p.y < 0)
                    setZoneStart(runsize - zone_size);
                else {
                    int card = figureCard(p.y);
                    if ((card >= 0) && (card < zone_start))
                        setZoneStart(card);
                    else if (card >= (zone_start + zone_size)) {
                        // System.err.println("card is " + card + "    (zone " + zone_start + ":" + (zone_start + zone_size - 1) + ")");
                        setZoneStart(card - zone_size + 1);
                    }
                }
                if (zone_start != old_start)
                    repaint();
            }
        }

        public void setZoneStart(int index) {
            if (index == zone_start)
                return;
            if (index < 1)
                zone_start = 1;
            else if (index > (runsize - zone_size))
                zone_start = runsize - zone_size - 1;
            else
                zone_start = index;
            front_border = (zone_start > 1) ? ((zone_start - 1) * border_width) / (runsize - zone_size - 1) : 0;
            back_border = (runsize > (zone_start + zone_size)) ? (border_width - front_border) : 0;
            zone_top = back_border;
            zone_bottom = zone_top + (zone_size * tab_height);
            back_span = Math.exp(back_border);
            front_span = Math.exp(front_border);
            if (zone_bottom < first_top) {
                front_polygon_x[0] = figureCardLeft(zone_start) - 2;
                front_polygon_y[0] = zone_bottom;
                front_polygon_x[1] = front_polygon_x[0] + cardwidth;
                front_polygon_y[1] = front_polygon_y[0];
                front_polygon_x[2] = front_polygon_x[1];
                front_polygon_y[2] = front_polygon_y[1] + cardheight;
                front_polygon_x[3] = front_polygon_x[2] - (first_top - zone_bottom);
                front_polygon_y[3] = front_polygon_y[2] + (first_top - zone_bottom);
                front_polygon_x[4] = front_polygon_x[3];
                front_polygon_y[4] = front_polygon_y[3] - cardheight;
                front_polygon_x[5] = front_polygon_x[4] - cardwidth;
                front_polygon_y[5] = front_polygon_y[4];
            }

            if (last_top < zone_top) {
                back_polygon_x[0] = figureCardLeft(runsize - 1);
                back_polygon_y[0] = last_top;
                back_polygon_x[1] = back_polygon_x[0] + cardwidth;
                back_polygon_y[1] = back_polygon_y[0];
                back_polygon_x[2] = back_polygon_x[1];
                back_polygon_y[2] = back_polygon_y[1] + cardheight;
                back_polygon_x[3] = back_polygon_x[2] - (zone_top - last_top);
                back_polygon_y[3] = back_polygon_y[2] + (zone_top - last_top);
                back_polygon_x[4] = back_polygon_x[3];
                back_polygon_y[4] = back_polygon_y[3] - cardheight;
                back_polygon_x[5] = back_polygon_x[4] - cardwidth;
                back_polygon_y[5] = back_polygon_y[4];
            }
        }

        public void unPin () {
            if (pinned) {
                pinned = false;
                if (isVisible())
                    repaint();
            }
        }

        public void addHyperlinkListener (HyperlinkListener l) {
            editor.addHyperlinkListener(l);
        }

        public void addActionListener(ActionListener l) {
            action_listeners.add(l);
        }

        private void notifyActionListeners (ActionEvent e) {
            for (int i = 0;  i < action_listeners.size();  i++)
                ((ActionListener)(action_listeners.get(i))).actionPerformed(e);
        }

        private void paintCard (Graphics g, int cardindex) {
            int x = figureCardLeft(cardindex);
            int y = figureCardTop(cardindex);
            // System.err.println("paint card " + cardindex + " at " + x + ", " + y);
            g.setColor(card_background);
            g.fillRect(x, y, cardwidth, cardheight);
            g.setColor(card_edge);
            g.drawRect(x, y, cardwidth-1, cardheight-1);
            if (((cardindex == 0) && (!pinned || (top == 0)))||
                ((cardindex >= zone_start) && (cardindex <= (zone_start + zone_size)))) {
                String label = run.label(cardindex);
                if (label != null) {
                    // draw top line (title) of card
                    Shape oldclip = g.getClip();
                    g.setColor(Color.BLACK);
                    g.setFont(card_font);
                    // narrow down the clip rect for the drawString operation
                    g.clipRect(x+15, y+1, cardwidth - 31, tab_height-2);
                    g.drawString(run.label(cardindex), x+15, y + tab_height - 4);
                    g.setClip(oldclip);
                }
            }
            if (cardindex == top) {
                g.drawImage(pinned ? pushpin : pushpin_ghost, pushpin_rect.x, pushpin_rect.y, null);
            }
        }

        public void paintComponent (Graphics g) {
            super.paintComponent(g);
            // draw cards from back to front
            int i;
            // paint cards not visible
            if (last_top < zone_top) {
                g.setColor(card_edge_fill);
                g.fillPolygon(back_polygon_x, back_polygon_y, 6);
            }
            // paint cards in focus zone
            for (i = Math.min(zone_start + zone_size - 1, runsize-1);  i >= zone_start;  i--) {
                if (i != top)
                    paintCard (g, i);
            }
            // paint cards not visible
            if (zone_bottom < first_top) {
                g.setColor(card_edge_fill);
                g.fillPolygon(front_polygon_x, front_polygon_y, 6);
            }
            // always paint card 0
            paintCard(g, 0);
            // always paint top card
            if (top > 0)
                paintCard (g, top);
        }

        public void mouseEntered (MouseEvent e) {
            // System.err.println("" + runsize + " cards");
            adjustZone(e.getPoint());
        }

        public void mouseExited (MouseEvent e) {
            Point p = e.getPoint();
            if (p.y < 0)
                p.y = 0;
            if (p.y > getHeight())
                p.y = getHeight() - 1;
            adjustZone(p);
        }

        public void mouseMoved (MouseEvent e) {
            if (e.getPoint().x <= cardwidth)
                adjustZone(e.getPoint());
        }

        public void mouseDragged (MouseEvent e) {
            adjustZone(e.getPoint());
            if (e.getButton() == MouseEvent.BUTTON1)
                mousePressed(e);
        }

        public void mouseClicked (MouseEvent e) {
        }

        public void mousePressed (MouseEvent e) {
            int tab = figureCard(e.getPoint().y);
            // System.err.println("tab is " + tab);
            if ((e.getButton() == MouseEvent.BUTTON1) && (!pinned && (tab >= 0) && (tab != top))) {
                setTop(tab, true);
                repaint();
            } else if ((e.getButton() == MouseEvent.BUTTON3) && (tab >= 0)) {
                if (!pinned) {
                    if (tab != top)
                        setTop(tab, true);
                    pinned = true;
                    repaint();
                } else if (pinned) {
                    if (tab != top)
                        setTop(tab, false);
                    else
                        pinned = false;
                    repaint();
                }
            } else
                return;
        }

        public void mouseReleased (MouseEvent e) {
            if ((figureCard(e.getPoint().y) == top) && pushpin_rect.contains(e.getPoint())) {
                // System.err.println("flipping pinned to " + !pinned + " for card " + top);
                pinned = !pinned;
                repaint(pushpin_rect);
            }
            if (!pinned) {
                setTop(0, false);
                repaint();
            }
        }

        public void mouseWheelMoved (MouseWheelEvent e) {
            Point p = e.getPoint();
            if ((!pinned) && ((p.x > (figureCardLeft(top) + cardwidth)) || ((p.y >= zone_top) && (p.y < zone_bottom)))) { 
                int rotation = e.getWheelRotation();
                if (((rotation < 0) && ((zone_start + zone_size) < runsize)) ||
                    ((rotation > 0) && (zone_start > 1))) {
                    setZoneStart(zone_start - e.getWheelRotation());
                    repaint();
                }
            }
        }

        public void actionPerformed (ActionEvent e) {
            // System.err.println("Action " + e);
        }

        public void keyPressed (KeyEvent e) {
            // System.err.println("keyPressed " + e);
            if ((top > 0) && (e.getKeyCode() == KeyEvent.VK_SHIFT)) {
                pinned = !pinned;
                repaint();
            } else if ((top >= 0) && (e.getKeyCode() == KeyEvent.VK_CONTROL)) {
                run.open(top);
            }
        }

        public void keyReleased (KeyEvent e) {
        }

        public void keyTyped (KeyEvent e) {
        }

        public void componentHidden(ComponentEvent e) {
        }

        public void componentMoved(ComponentEvent e) {
        }

        public void componentResized(ComponentEvent e) {
        }
        
        public void componentShown(ComponentEvent e) {
            // System.err.println("shown " + e);
            this.requestFocusInWindow();
        }
    }


    public class DividerSelected extends ActionEvent {
        public int tab;
        public DividerSelected (int tabindex) {
            super(FileBox.this, ActionEvent.ACTION_PERFORMED, "tab selected");
            tab = tabindex;
        }
    }

    private CardRunViewer card_viewer;
    private int card_run_viewer_top;
    private int card_run_viewer_bottom;
    private AffineTransform top_transform;
    private AffineTransform bottom_transform;
    private CardRun[] cardruns;
    private int opened = -1;
    protected Paint background;
    protected Font tab_font;
    protected String[] titles;
    protected int selected = -1;
    protected Polygon[] tabs;
    protected Rectangle[] tab_rects;
    protected int tab_height;
    protected float tab_width = 0.0f;
    protected int tabs_per_line;
    protected ArrayList action_listeners;
    protected int[] cards_start;
    protected int tabpressed;
    protected int card_width;
    protected int card_height;
    
    public FileBox (Paint background, Font tab_font, String[] titles, CardRun[] cardruns,
                    int width, int height, int tab_height, int tabs_per_line,
                    int card_width, int card_height, int card_tab_height) {

        this.background = (background == null) ? divider_background : background;
        this.tab_font = (tab_font == null) ? divider_font : tab_font;
        this.titles = titles;
        this.selected = -1;
        this.tabpressed = -1;
        this.tab_height = tab_height;
        this.tabs_per_line = tabs_per_line;
        action_listeners = new ArrayList();
        this.tabs = new Polygon[titles.length];
        this.tab_rects = new Rectangle[titles.length];
        this.cardruns = cardruns;
        this.card_width = card_width;
        this.card_height = card_height;
        this.card_viewer = new CardRunViewer(width, height, card_tab_height, cardruns[0]);
        this.top_transform = new AffineTransform();
        this.bottom_transform = new AffineTransform();
        this.opened = -1;
        setLayout(null);
        setPreferredSize(new Dimension(width, height));
        figureTabs(width, height);
        setOpaque(false);
        setFocusable(true);
        addMouseListener(this);
        addMouseMotionListener(this);
    }

    public void addActionListener(ActionListener l) {
        action_listeners.add(l);
    }

    private void notifyActionListeners (ActionEvent e) {
        for (int i = 0;  i < action_listeners.size();  i++)
            ((ActionListener)(action_listeners.get(i))).actionPerformed(e);
    }

    protected Polygon layoutTab (Rectangle tab_rect,
                                 int card_width, int card_height) {
        Polygon tab = new Polygon();
        tab.addPoint(0, tab_rect.y + tab_height);
        tab.addPoint(tab_rect.x, tab_rect.y + tab_height);
        tab.addPoint(tab_rect.x + 5, tab_rect.y);
        tab.addPoint(tab_rect.x + tab_rect.width - 5, tab_rect.y);
        tab.addPoint(tab_rect.x + tab_rect.width, tab_rect.y + tab_height);
        tab.addPoint(card_width - 1, tab_rect.y + tab_height);
        tab.addPoint(card_width - 1, tab_rect.y + tab_height + card_height);
        tab.addPoint(0, tab_rect.y + tab_height + card_height);
            
        return tab;
    }

    protected void figureTabs (int width, int height) {

        cards_start = new int[titles.length];

        int[] tab_tops = new int[tabs_per_line];
        for (int j = 0;  j < tabs_per_line;  j++)
            tab_tops[j] = -1;

        if (tabs_per_line > 0) {
            // fixed number of tabs per line
            tab_width = (width - 10) / (float) tabs_per_line;
            int tab_y = 0;
            int cstart = 0;
            int cheight;
            for (int i = titles.length - 1;  i >= 0;  i--) {
                int which_tab = i % tabs_per_line;
                cheight = 4 * (int) Math.round(Math.log((double) cardruns[i].size()));
                int tab_x = (int) Math.round((i % tabs_per_line) * tab_width) + 5;
                tab_y += (cheight + 1);
                if ((tab_tops[which_tab] >= 0) && ((tab_y - tab_tops[which_tab]) < tab_height))
                    tab_y += (tab_height - (tab_y - tab_tops[which_tab]));
                // tab_y += Math.max(0, cheight - tab_height + 1);
                cards_start[i] = tab_y + tab_height - cheight;
                // System.err.println("cheight[" + titles[i] + "] is " + cheight + ", cards_start is " + cards_start[i] + ", tab_y is " + tab_y);
                tab_rects[i] = new Rectangle(tab_x, tab_y, (int) Math.round(tab_width), tab_height);
                tabs[i] = layoutTab(tab_rects[i], width, height - tab_y - tab_height);
                tab_tops[which_tab] = tab_y;
            }
            setMinimumSize(new Dimension(0, tab_y + tab_height));
        } else {
            // TODO
        }
    }

    protected int inTab (Point2D p) {
        Point2D p2 = p;
        if (opened >= 0) {
            try {
                double py = p.getY();
                if (py < card_run_viewer_top) {
                    p2 = top_transform.inverseTransform(p, null);
                } else if (py > card_run_viewer_bottom) {
                    p2 = bottom_transform.inverseTransform(p, null);
                }
            } catch (NoninvertibleTransformException x) {
                x.printStackTrace(System.err);
            }
        }
        int py = (int) Math.round(p2.getY());
        for (int i = 0;  i < titles.length;  i++) {
            int y = cards_start[i];
            int limit = 4 * (int) Math.round(Math.log((double) cardruns[i].size()));
            if ((tab_rects[i].contains(p2)) || (py >= y && py < (y + limit)))
                return i;
        }
        return -1;
    }

    public Font getTabFont () {
        return ((tab_font == null) ? divider_font : tab_font);
    }

    public String getSelected() {
        if ((selected >= 0) && (selected < titles.length))
            return titles[selected];
        else
            return null;
    }

    protected Color tabTextColor (int tabindex) {
        if (((opened < 0) && (tabindex == selected)) ||
            ((opened >=0) && (tabindex == opened)))
            return Color.RED;
        else if (cardruns[tabindex].size() == 0)
            return Color.GRAY;
        else
            return Color.BLACK;
    }

    protected void paintTab (Graphics g, int tabindex) {

        AffineTransform saved = null;
        Point2D next_tab_top = null;
        if (opened >= 0) {
            saved = ((Graphics2D)g).getTransform();
            ((Graphics2D)g).setTransform((tabindex > opened) ? top_transform : bottom_transform);
        }

        /*
          if ((tab == 1) || (tab == 10)) {
          System.err.println("g.transform for \"" + titles[tab] + "\" is " + ((Graphics2D)g).getTransform());
          System.err.println("tab top for \"" + titles[tab] + "\" is at " + ((Graphics2D)g).getTransform().transform(new Point(tab_rects[tab].x, tab_rects[tab].y), null));
          }
        */

        if (tabindex != opened) {
            // draw cards behind tab
            int y = cards_start[tabindex];
            int limit = 2 * (int) Math.round(Math.log((double) cardruns[tabindex].size()));
            for (int i = 0;  i < limit;  i++) {
                g.setColor(card_edge);
                g.drawLine(0, y+(2 * i), getWidth(), y+ (2 * i));
                g.setColor(Color.WHITE);
                g.drawLine(0, y+(2 * i)+1, getWidth(), y+(2 * i)+1);
            }
        }
        Object oldaa = ((Graphics2D)g).getRenderingHint(RenderingHints.KEY_ANTIALIASING);
        ((Graphics2D)g).setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        ((Graphics2D)g).setPaint(background);
        ((Graphics2D)g).fill(tabs[tabindex]);
        if (tabindex == selected) {
            g.setColor(WHITEWASH);
            ((Graphics2D)g).fill(tabs[tabindex]);
        }
        g.setColor(divider_edge);
        ((Graphics2D)g).draw(tabs[tabindex]);
        ((Graphics2D)g).setRenderingHint(RenderingHints.KEY_ANTIALIASING, oldaa);

        g.setColor(tabTextColor(tabindex));
        Rectangle2D r = getFont().getStringBounds(titles[tabindex], 0, titles[tabindex].length(), ((Graphics2D)g).getFontRenderContext());
        Rectangle tab = tab_rects[tabindex];
        g.drawString(titles[tabindex], tab.x + (int) (tab.width - r.getWidth())/2,
                     (int) Math.round(tab.y + 4 + r.getHeight()));

        if (opened >= 0) {
            if (tabindex == (opened + 1))
                // just behind it
                next_tab_top = top_transform.transform(new Point(tab_rects[tabindex].x, tab_rects[tabindex].y), null);
            ((Graphics2D)g).setTransform(saved);
            if (next_tab_top != null) {
                Rectangle r2 = card_viewer.getBounds();
                ((Graphics2D)g).setPaint(background);
                g.fillRect(0, r2.y - 2, getWidth(), getHeight() - r2.y + 2);
                if (tabindex == selected) {
                    g.setColor(WHITEWASH);
                    g.fillRect(0, r2.y - 2, getWidth(), getHeight() - r2.y + 2);
                }
                g.setColor(divider_edge);
                g.drawLine(0, r2.y - 2, 0, getHeight() - r2.y + 2);
                g.drawLine(getWidth()-1, r2.y - 2, getWidth()-1, getHeight() - r2.y + 2);
                g.setColor(GRAYWASH);
                g.fillRect(0, r2.y - 2, getWidth(), r2.y + r2.height + 4);
            }
        }
    }

    public void paintComponent (Graphics g) {
        super.paintComponent(g);
        g.setFont(getTabFont());
        // draw cards from back to front
        for (int i = titles.length-1;  i >= 0;  i--)
            paintTab (g, i);
    }

    public void mouseEntered (MouseEvent e) {
        requestFocusInWindow();
        selectTab(inTab(e.getPoint()), false);
    }

    public void mouseExited (MouseEvent e) {
        selected = -1;
        tabpressed = -1;
        repaint();
    }

    public void mouseMoved (MouseEvent e) {
        selectTab(inTab(e.getPoint()), false);
    }

    public void mouseDragged (MouseEvent e) {
        selectTab(inTab(e.getPoint()), false);
    }

    public void selectTab (int tab, boolean clicked) {
        int oldselected = selected;
        if (tab != -1) {
            selected = tab;
            if (clicked)
                notifyActionListeners(new DividerSelected(tab));
            setToolTipText(titles[tab] + ":  " + cardruns[selected].size() + " card" + ((cardruns[selected].size() == 1) ? "" : "s"));
            if (oldselected != tab)
                repaint();
        }
        if (clicked) {
            if ((tab != -1) && (tab != opened)) {
                if (opened >= 0) {
                    card_viewer.setVisible(false);
                    remove(card_viewer);
                    card_viewer.unPin();
                }
                CardRun c = cardruns[tab];
                if (c.size() == 0)
                    return;
                // System.err.println("Run size is " + c.size());
                card_viewer.setCardRun(c);
                Dimension d = card_viewer.figurePreferredSize(card_width, card_height);
                // System.err.println("card_viewer preferred size is " + d);
                int existing_space = tab_rects[tab].y + tab_height - cards_start[tab];
                // int needed_space = d.height - existing_space + tab_height;
                int needed_space = d.height - existing_space + 5;
                if (needed_space > existing_space) {
                    double proportion = cards_start[tab] / (double)(tab_rects[0].y + tab_height);
                    // System.err.println("proportion is " + proportion);
                    card_run_viewer_top = (int) Math.max(tab_height/2, Math.round((getHeight() - (d.height + 5)) * proportion));
                    card_run_viewer_bottom = card_run_viewer_top + d.height + 5;
                    int bottom_height = tab_height/2 - (getHeight() - card_run_viewer_bottom);
                    if (bottom_height > 0) {
                        card_run_viewer_top -= bottom_height;
                        card_run_viewer_bottom -= bottom_height;
                    }
                    /*
                      System.err.println("card_run_viewer_top is " + card_run_viewer_top +
                      ", card_run_viewer_bottom is " + card_run_viewer_bottom +
                      ", bottom is at " + getHeight());
                    */
                    top_transform.setToScale(1.0D, (double) (card_run_viewer_top - 5) / cards_start[tab]);
                    // double y_scaling = (double) (getHeight() - card_run_viewer_bottom) / (double) (getHeight() - tab_rects[tab].y);
                    double y_scaling = Math.min(1.0D, (double) (getHeight() - card_run_viewer_bottom) / (double) (tab_rects[0].y + tab_height - tab_rects[tab].y));
                    bottom_transform.setTransform(1.0D, 0.0D, 0.0D,
                                                  y_scaling, 0.0D,
                                                  tab_rects[tab].y - (y_scaling * tab_rects[tab].y) + (card_run_viewer_bottom - tab_rects[tab].y));
                    // System.err.println("top_transform is " + top_transform + ", bottom_transform is " + bottom_transform);
                        
                } else {
                    card_run_viewer_top = cards_start[tab];
                    card_run_viewer_bottom = card_run_viewer_top + d.height;
                    top_transform.setToIdentity();
                    bottom_transform.setToIdentity();
                }
                int cardviewer_x = (getWidth() - d.width)/2;
                add(card_viewer);
                card_viewer.setBounds(cardviewer_x, card_run_viewer_top, d.width, d.height);
                card_viewer.setVisible(true);
                opened = tab;
                repaint();
            } else {
                card_viewer.setVisible(false);
                remove(card_viewer);
                card_viewer.unPin();
                top_transform.setToIdentity();
                bottom_transform.setToIdentity();
                opened = -1;
                repaint();
            }
        }
    }

    public void mouseClicked (MouseEvent e) {
        if (e.getButton() == MouseEvent.BUTTON3)
            selectTab(-1, true);
    }

    public void mousePressed (MouseEvent e) {
        tabpressed = inTab(e.getPoint());
    }

    public void mouseReleased (MouseEvent e) {
        int tab = inTab(e.getPoint());
        if ((tab != -1) && (tabpressed == tab)) {
            // clicked on this tab
            tabpressed = -1;
            selectTab(tab, true);
        }
    }

    public void setBounds (int x, int y, int width, int height) {
        super.setBounds(x, y, width, height);
        figureTabs(width, height);
    }

    public void addHyperlinkListener (HyperlinkListener l) {
        card_viewer.addHyperlinkListener(l);
    }

    public static FileBox create (String titles[], CardRun[] cardsets, int tabs_per_line, int tab_height, Font tab_font, TexturePaint divider_texture, int cardwidth, int cardheight) {

        int card_tab_height = 20;

        FileBox dividers;
        int[] card_counts = new int[cardsets.length];
        int width = 0;
        int height = 0;
        for (int i = 0;  i < cardsets.length;  i++) {
            // System.err.println("i is " + i + ", titles[i] => " + titles[i] + ", cardsets[i] => " + cardsets[i]);
            card_counts[i] = cardsets[i].size();
            Dimension d = CardRunViewer.getNormalSize(card_counts[i], card_tab_height,
                                                      CardRunViewer.getFocusZoneSize(),
                                                      cardwidth, cardheight);
            // System.err.println("  card_run size for \"" + titles[i] + "\" is " + d);
            width = Math.max(width, d.width);
            height = Math.max(height, d.height);
        }
        dividers = new FileBox(divider_texture, tab_font, titles, cardsets,
                               width, height, tab_height, tabs_per_line, cardwidth, cardheight, card_tab_height);
        Dimension dsize = dividers.getMinimumSize();
        // System.err.println("dividers size is " + dsize);
        height = Math.max(height + 100, dsize.height);
        width = Math.max(width, dsize.width);
        // System.err.println("final size is " + width + ", " + height);
        dsize = new Dimension(width, height);
        dividers.setMinimumSize(dsize);
        dividers.setPreferredSize(dsize);
        dividers.setSize(width, height);
        dividers.setVisible(true);
        dividers.setOpaque(false);
        return dividers;
    }
}
