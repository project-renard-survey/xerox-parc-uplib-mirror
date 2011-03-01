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

public interface FeedbackApp {

    // called to signal the application that it has been "opened"
    public void openApplication (String path);

    // called to signal application that it has been "re-opened"
    public void reOpenApplication (String path);

    // called to signal application that it has been asked to open a document
    public void openDocument(String path);

    // called to ask the application to exit
    public void exitApplication();

    // called to ask the application to open a preferences editor to edit configuration options
    public void editPreferences();

    // called to ask the application to print a document
    public void printDocument (java.lang.String filename);

    // called to ask the application to display a splash screen.
    // return false if not interested.
    public boolean showSplashScreen ();
}
