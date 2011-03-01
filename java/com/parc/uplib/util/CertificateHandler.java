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

import java.io.IOException;
import java.io.InputStream;
import java.io.FileInputStream;
import java.io.File;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLConnection;
import java.net.UnknownHostException;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.security.GeneralSecurityException;
import java.security.Principal;
import java.security.PrivateKey;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.Enumeration;
import java.util.HashMap;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLSession;
import javax.net.ssl.X509TrustManager;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.KeyManager;
import javax.swing.JOptionPane;

public class CertificateHandler implements X509TrustManager {

    private static class HostnameIgnorer implements HostnameVerifier {
        public boolean verify (String hostname, SSLSession session) {
            return true;
        }
    }

    /*
      If you want to override this with a subclass that does something different
      for "addUntrustedCertificate", you should call initialize with an instance
      of that subclass as an argument, so that it can be put into the SSLContext.
    */

    private static ArrayList known_certificates = null;
    protected static boolean ignore_cert_details = false;

    private X509TrustManager sunX509TrustManager;

    CertificateHandler() {
        // create sunX509TrustManager
        //
        // for example:
        //     Create/load a keystore
        //     Get instance of a "SunX509" TrustManagerFactory "tmf"
        //     init the TrustManagerFactory with the keystore

        try {
            TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
            tmf.init((java.security.KeyStore) null);
            sunX509TrustManager = (X509TrustManager) tmf.getTrustManagers()[0];
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
    }
    
    /**
       Subclasses should override this to do other things, like updating the keystore.
    */
    public void addUntrustedCertificate (X509Certificate cert) {
        if (known_certificates == null)
            known_certificates = new ArrayList();
        known_certificates.add(cert);
    }

    public void checkClientTrusted(X509Certificate[] chain, String authType)
        throws CertificateException {
        sunX509TrustManager.checkServerTrusted(chain, authType);
    }

    public void checkServerTrusted(X509Certificate[] chain,
                                   String authType)
        throws CertificateException {

        if (ignore_cert_details)
            // we don't really care
            return;

        try {
            sunX509TrustManager.checkServerTrusted(chain, authType);
        } catch (Exception excep) {

            if (known_certificates != null) {
                for (Iterator i = known_certificates.iterator();  i.hasNext();  ) {
                    X509Certificate c = (X509Certificate) (i.next());
                    if (c.equals(chain[0]))
                        return;
                }
            }

            // at this point, throw up a dialog box
            String dname = chain[0].getSubjectDN().getName();
            String iname = chain[0].getIssuerDN().getName();
            String after = chain[0].getNotBefore().toString();
            String before = chain[0].getNotAfter().toString();
            
            String msg = "The repository has a certificate for\n" + dname + ", issued by\n" + iname + ",\ngood after " + after + " and before " + before + ".\n\nDo you want to trust it?";
            int v = JOptionPane.showConfirmDialog(null, msg, "Confirm untrusted certificate", JOptionPane.YES_NO_OPTION);
            if (v != JOptionPane.YES_OPTION)
                if (excep instanceof CertificateException) {
                    throw (CertificateException) excep;
                } else {
                    return;
                }            
            else
                addUntrustedCertificate(chain[0]);
        }
    }
    
    public X509Certificate[] getAcceptedIssuers() {
        return sunX509TrustManager.getAcceptedIssuers();
    }

    public static void initialize (CertificateHandler tm, ClientKeyManager km)
        throws NoSuchAlgorithmException, KeyManagementException {
        
        KeyManager kmArray[] = null;
        if (tm == null)
            tm = new CertificateHandler();
        if (km == null)
            kmArray = new KeyManager[0];
        else
            kmArray = new KeyManager[] { km };
        TrustManager[] myTM = new TrustManager [] { tm };
        SSLContext ctx = SSLContext.getInstance("TLS");
        ctx.init(kmArray, myTM, null);
        HttpsURLConnection.setDefaultSSLSocketFactory(ctx.getSocketFactory());
    }

    public static void initialize() 
        throws NoSuchAlgorithmException, KeyManagementException {
        initialize(null, null);
    }

    public static void ignoreHostnameMismatches() {
        HttpsURLConnection.setDefaultHostnameVerifier(new HostnameIgnorer());
    }

    public static void ignoreCerts(ClientKeyManager km) {
        try {
            ignore_cert_details = true;
            initialize(null, km);
            HttpsURLConnection.setDefaultHostnameVerifier(new HostnameIgnorer());
        } catch (NoSuchAlgorithmException x) {
            x.printStackTrace(System.err);
        } catch (KeyManagementException x) {
            x.printStackTrace(System.err);
        }
    }

    public static void ignoreCerts() {
        try {
            ignore_cert_details = true;
            initialize(null, null);
            HttpsURLConnection.setDefaultHostnameVerifier(new HostnameIgnorer());
        } catch (NoSuchAlgorithmException x) {
            x.printStackTrace(System.err);
        } catch (KeyManagementException x) {
            x.printStackTrace(System.err);
        }
    }

    public static void main (String[] argv) {
        try {                    
            CertificateHandler.initialize();

            for (int i = 0;  i < 3;  i++) {
                try {
                    URLConnection c = new URL(argv[0]).openConnection();
                    InputStream s = c.getInputStream();
                } catch (IOException x) {
                    System.err.println("Error getting the input stream");
                    x.printStackTrace();
                }
                System.err.println("opened url");
            }

        } catch (Exception x) {
            System.err.println("IO Exception!");
            x.printStackTrace(System.err);
        }
    }
}
