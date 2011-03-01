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

import com.apple.eawt.*;

public class MacOSXAppSupport {

    private static class HandleAppleEvents extends ApplicationAdapter {

        private FeedbackApp myapp;

        public HandleAppleEvents (FeedbackApp app) {
            myapp = app;
        }

        public void handleOpenApplication (ApplicationEvent e) {
            System.err.println("openApplication event is " + e + ", filename is " + e.getFilename());
            myapp.openApplication(e.getFilename());
        }

        public void handleReOpenApplication (ApplicationEvent e) {
            System.err.println("reOpenApplication event is " + e + ", filename is " + e.getFilename());
            myapp.reOpenApplication(e.getFilename());
        }

        public void handleOpenFile (ApplicationEvent e) {
            // System.err.println("openDocument event is " + e);
            myapp.openDocument(e.getFilename());
        }

        public void handleQuit (ApplicationEvent e) {
            // System.err.println("Quit event is " + e);
            myapp.exitApplication();
            e.setHandled(true);
        }

        public void handlePreferences (ApplicationEvent e) {
            // System.err.println("handlePreferences event is " + e);
            myapp.editPreferences();
        }

        public void handlePrintFile (ApplicationEvent e) {
            // System.err.println("handlePrintFile event is " + e);
            myapp.printDocument (e.getFilename());
        }

        public void handleAbout (ApplicationEvent e) {
            // System.err.println("handleAbout event is " + e);
            if (myapp.showSplashScreen())
                e.setHandled(true);
        }
    }

    public static void setupEventHandling (FeedbackApp readup) {

        Application app = Application.getApplication();
        // System.err.println("Registering event handler for " + readup);
        app.addApplicationListener(new HandleAppleEvents(readup));
    }
}
        

