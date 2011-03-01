/*
 * This file is part of the "UpLib 1.7.11" release.
 * Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

import java.util.Iterator;

import com.parc.uplib.util.CertificateHandler;
import com.parc.uplib.readup.uplibbinding.Repository;
import com.parc.uplib.readup.widget.PageText;
import com.parc.uplib.readup.widget.SoftReferenceCache;

class Tests {

    private static void repoTest (Repository repo, String[] argv) {
        // this tests reading the index file
        Repository.Category[] categories = repo.getCategoriesList();
        if (categories != null) {
            System.out.print("" + categories.length + " categories:");
            for (int i = 0;  i < categories.length;  i++)
                System.out.print(" " + categories[i].getName());
            System.out.println("");
        }
    }

    private static void doctextTest (Repository repo, String[] argv) {
        Repository.Document doc = repo.getDocument(argv[2]);
        int pagecount = doc.getPageCount();
        SoftReferenceCache pagecache = doc.getPageTextLoader();
        for (int i = 0;  i < pagecount;  i++) {
            PageText pt = (PageText) pagecache.get(doc.getID(), i, 0, null);
            while (pt == null) {
                pt = (PageText) pagecache.check(doc.getID(), i, 0);
            }
            String text = pt.getText();
            System.out.println("Page " + i);
            System.out.println(text);
        }
    }

    public static void main (String[] argv) {
        if (argv.length < 2) {
            System.err.println("Usage:  Tests <REPO-URL> <TESTNAME> [<ARGS>...]");
            System.exit(1);
        }
        String password = null;
        try {
            password = System.getenv("UPLIB_PASSWORD");
        } catch (Exception x) {
        };
        try {
            CertificateHandler.ignoreCerts();
            // no password
            Repository repo = new Repository(argv[0], password);
            if (argv[1].equals("repo")) {
                repoTest (repo, argv);
            } else if (argv[1].equals("doctext")) {
                doctextTest(repo, argv);
            } else {
                System.err.println("Unknown test <" + argv[1] + "> specified.");
                System.exit(1);
            }
        } catch (Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }
    }
}
