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

import java.util.*;
import java.util.regex.*;
import java.net.*;
import javax.net.ssl.*;
import javax.security.cert.*;

public class PARCAwareCertHostnameVerifier implements HostnameVerifier {

    static final Pattern CN_PATTERN = Pattern.compile("^(.*, )*CN=([^,]+)(, .*)*");

    String expected_hostname;
    boolean usePARCHostnameMatching;

    public PARCAwareCertHostnameVerifier (String user_hostname, boolean usePARCHostnameMatching) {
        this.expected_hostname = user_hostname;
        this.usePARCHostnameMatching = usePARCHostnameMatching;
    }

    static private String stringJoin (String[] parts, int start, String separator) {
        String result = "";
        for (int i = 0;  (i + start) < parts.length;  i++) {
            if (i > 0)
                result = result + separator;
            result = result + parts[i+start];
        }
        return result;
    }

    static public boolean PARCHostnameMatch (String url_name, String cert_name) {

        if (cert_name == null || url_name == null)
            return false;

        if (url_name.equals(cert_name))
            return true;

        if (url_name.equals("localhost") || url_name.equals("127.0.0.1")) {
            try {
                String localhost = java.net.InetAddress.getLocalHost().getCanonicalHostName();
                if (localhost.equals("localhost") || localhost.equals("127.0.0.1"))
                    return true;
                else
                    return PARCHostnameMatch(localhost, cert_name);
            } catch (java.net.UnknownHostException e) {
                return false;
            }
        }

        String[] url_parts = url_name.split("\\.");
        String[] cert_parts = cert_name.split("\\.");
        boolean head_match = false;
        if ((cert_parts.length < 2) ||
            (url_parts.length < 1) ||
            ((cert_parts.length == 2) && cert_parts[1].equals("local")))
            return false;

        // allow "http://foo.local/" to match "foo.company.com" in cert
        if ((url_parts.length == 2) &&
            url_parts[1].equals("local") &&
            url_parts[0].equals(cert_parts[0]))
            return true;

        // try to match heads
        String url_head = url_parts[0];
        String cert_head = cert_parts[0];
        if (cert_head.startsWith("vpn-"))
            cert_head = cert_head.substring(4);
        else if (cert_head.endsWith("-wlan"))
            cert_head = cert_head.substring(0, cert_head.length() - 5);
        else if (cert_head.endsWith("-64"))
            cert_head = cert_head.substring(0, cert_head.length() - 3);
        if (!(url_head.equals(cert_head) ||
              url_head.equals(cert_head + "-wlan") ||
              url_head.equals("vpn-" + cert_head) ||
              url_head.equals(cert_head + "-64")))
            // heads don't "match"
            return false;

        String cert_tail = stringJoin(cert_parts, 1, ".");
        // URL is single part, but cert has "parc.com" or some such
        if ((url_parts.length == 1) &&
            (cert_tail.equals("parc.com") ||
             cert_tail.equals("parc.xerox.com") ||
             cert_tail.equals("corp.ad.parc.com")))
            return true;

        // both URL and cert have tails
        String url_tail = stringJoin(url_parts, 1, ".");
        if ((cert_tail.equals("parc.com") ||
             cert_tail.equals("parc.xerox.com") ||
             cert_tail.equals("corp.ad.parc.com")) &&
            (url_tail.equals("parc.com") ||
             url_tail.equals("parc.xerox.com") ||
             url_tail.equals("corp.ad.parc.com")))
            return true;

        // one of the tails wasn't a PARC tail
        return false;
    }

    static private String getHostname (SSLSession session) {
        String hostname = null;
        try {
            X509Certificate[] certs = session.getPeerCertificateChain();
            for (int i = 0;  i < certs.length;  i++) {
                // System.err.println(certs[i].getSubjectDN().getName());
            }
            if (certs.length > 0) {
                String dname = certs[0].getSubjectDN().getName();
                Matcher m = CN_PATTERN.matcher(dname);
                if (m.matches()) {
                    // System.err.println("hostname is " + m.group(2));
                    hostname = m.group(2);
                }
            }
        } catch (Exception e) {
            System.err.println("Exception " + e + " while examining certificates");
        }
        return hostname;
    }

    public boolean verify (String hostname, SSLSession session) {
        String remote_hostname = getHostname(session);
        boolean rval = false;
        if (usePARCHostnameMatching)
            rval = PARCHostnameMatch((expected_hostname == null) ? hostname : expected_hostname, remote_hostname);
        else
            rval = ((expected_hostname == null) ? hostname.equals(remote_hostname) : expected_hostname.equals(remote_hostname));
        // System.err.println("HostnameVerifier:  " + ((expected_hostname == null) ? hostname : expected_hostname) + " and " + remote_hostname + (rval ? " match" : " don't match"));
        return rval;
    }
}

