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

import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.dnd.*;
import java.awt.*;
import java.awt.datatransfer.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.border.*;
import javax.imageio.*;
import java.net.URL;
import java.util.logging.*;

public class ErrorDialog extends JDialog implements ActionListener {

    protected static boolean is_mac;
    protected static boolean is_windows;
    protected static Icon error_icon;

    static {
        is_mac = System.getProperty("os.name").toLowerCase().startsWith("mac");
        is_windows = System.getProperty("os.name").toLowerCase().startsWith("win");
        error_icon = UIManager.getDefaults().getIcon("OptionPane.errorIcon");
    }

    private JButton ok_button;
    private Component icon_area;

    public ErrorDialog (Frame parent, String error_msg, String error_text, boolean modal) {
        super(parent, modal);
        setDefaultCloseOperation(JDialog.DISPOSE_ON_CLOSE);
        initComponents(error_msg, error_text);
    }

    protected void initComponents(String error_msg, String error_text) {
        Box s;
        JLabel f;

        setTitle("Error Message");

        Box b = Box.createVerticalBox();
        b.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        Container contents = getContentPane();
        contents.add(b);

        Font bold = new Font(null, Font.BOLD, contents.getFont().getSize());

        {       // add icon and error message
            s = Box.createHorizontalBox();
            Box s2 = Box.createVerticalBox();
            s2.add(new JLabel(error_icon));
            s2.add(Box.createVerticalGlue());
            s.add(s2);               
        
            s.add(Box.createHorizontalStrut(10));

            JLabel l = new JLabel("<html>" + error_msg + "</html>");
            // l.setFont(bold);
            s.add(l);
            s.add(Box.createHorizontalGlue());
        }
        b.add(s);

        b.add(Box.createVerticalStrut(10));

        if (error_text != null) {
            JScrollPane a = new JScrollPane(new JTextArea(error_text));
            a.setSize(300, 200);
            b.add(a);

            b.add(Box.createVerticalStrut(10));
        }

        s = Box.createHorizontalBox();
        s.add(Box.createHorizontalGlue());
        ok_button = new JButton("OK");
        ok_button.addActionListener(this);
        s.add(ok_button);
        b.add(s);

        pack();
    }

    public void actionPerformed (ActionEvent e) {
        if (e.getActionCommand().equals(ok_button.getActionCommand())) {
            dispose();
        }
    }

    public void toFront () {
        if (is_mac) {
            try {
                this.setAlwaysOnTop(true);
            } catch (Exception e) {
                e.printStackTrace(System.err);
            }
        }
        super.toFront();
    }

    public static void say (String error_msg) {
        say(error_msg, null, null, true);
    }

    public static void say (String error_msg, String error_text) {
        say(error_msg, error_text, null, true);
    }

    public static void say (String error_msg, String error_text, String title) {
        say(error_msg, error_text, title, true);
    }

    public static void say (String error_msg, String error_text, String title, boolean block) {
        ErrorDialog dialog = new ErrorDialog(null, error_msg, error_text, block);
        if (title != null)
            dialog.setTitle(title);
        Dimension d = dialog.getSize();
        if (d.width > 500)
            d.width = 500;
        if (d.height > 400)
            d.height = 400;
        dialog.setSize(d);
        /*
        Dimension d = dialog.getMinimumSize();
        // d.height += 100;
        dialog.setSize(d);
        */
        Rectangle screenbounds = dialog.getOwner().getGraphicsConfiguration().getBounds();
        int x_pos = Math.min(Math.max(screenbounds.x, (screenbounds.width - dialog.getWidth())/2),
                             screenbounds.x + screenbounds.width - dialog.getWidth());
        int y_pos = Math.min(Math.max(screenbounds.y, (screenbounds.height - dialog.getHeight())/2),
                             screenbounds.y + screenbounds.height - dialog.getHeight());
        dialog.setLocation(x_pos, y_pos);
        dialog.requestFocus();
        dialog.toFront();

        dialog.setVisible(true);
    }

    public static void main (String[] argv) {

        try {
            BufferedReader r = new BufferedReader(new FileReader(new File(argv[0])));
            String testmsg = "";
            String line;
            while ((line = r.readLine()) != null)
                testmsg += (line + "\n");
            r.close();
            System.out.println("calling say...");
            say("This is a test message.", testmsg);
            System.out.println("say returned.");
            System.out.println("calling say...");
            say("This is a a very long erorr message with lots of junk in it to see if the thing will be folded or not test message.", testmsg);
            System.out.println("say returned.");
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        System.exit(0);
    }
}
