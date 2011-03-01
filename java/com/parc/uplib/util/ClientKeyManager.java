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
import java.io.ByteArrayInputStream;
import java.io.File;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLConnection;
import java.net.UnknownHostException;
import java.net.InetAddress;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.security.GeneralSecurityException;
import java.security.Principal;
import java.security.PrivateKey;
import java.security.KeyFactory;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.security.spec.PKCS8EncodedKeySpec;
import javax.crypto.spec.SecretKeySpec;

import java.util.Iterator;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Collection;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLSession;
import javax.net.ssl.X509TrustManager;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.KeyManager;

public class ClientKeyManager extends javax.net.ssl.X509ExtendedKeyManager {

    private static Pattern PEM_CERT_PATTERN =
        Pattern.compile("-----BEGIN CERTIFICATE-----\n(.*)\n-----END CERTIFICATE-----",
                        Pattern.DOTALL | Pattern.MULTILINE);
    private static Pattern PEM_KEY_PATTERN =
        Pattern.compile("-----BEGIN RSA PRIVATE KEY-----\n(.*)\n-----END RSA PRIVATE KEY-----",
                        Pattern.DOTALL | Pattern.MULTILINE);

    private static class CertKeyPair {
        PrivateKey pkey;
        X509Certificate[] cert_chain;
    };

    private HashMap client_certs = null;

    public ClientKeyManager () {
        super();
        client_certs = new HashMap();
    }

    public void addPKCS12Certificate(String alias, File certificate_file, String passwd)
        throws GeneralSecurityException, IOException {

        KeyStore putative_keystore = KeyStore.getInstance("PKCS12");
        FileInputStream keyStoreStream = new FileInputStream(certificate_file);
        char[] password = null;
        if ((passwd != null) && (passwd.length() > 0))
            password = passwd.toCharArray();
        putative_keystore.load(keyStoreStream, password);
        Enumeration aliasesEnum = putative_keystore.aliases();
        if (aliasesEnum.hasMoreElements()) {
            CertKeyPair pair = new CertKeyPair();
            String a = (String)aliasesEnum.nextElement();
            Certificate[] chain = putative_keystore.getCertificateChain(a);
            pair.pkey = (PrivateKey) putative_keystore.getKey(a, (password == null) ? new char[0] : password);
            pair.cert_chain = new X509Certificate[chain.length];
            for (int i = 0;  i < chain.length;  i++) {
                pair.cert_chain[i] = (X509Certificate) chain[i];
            }
            client_certs.put(alias, pair);
        } else {
            throw new IOException("no alias found in certificate file!");
        }
    }

    public void addPEMFile (String alias, File certificate_file, File private_key_file, String password)
        throws GeneralSecurityException, IOException {

        CertKeyPair pair = new CertKeyPair();

        byte[] filebytes = new byte[(int) (certificate_file.length())];
        int n = (new FileInputStream(certificate_file)).read(filebytes);
        String filecontent = new String(filebytes, "US-ASCII");
        System.err.println("read " + n + " bytes from file which contains " + certificate_file.length() + " bytes");
        Matcher m = PEM_CERT_PATTERN.matcher(filecontent);
        if (m.find()) {
            String encodedcert = m.group(1);
            System.err.println("encodedcert is\n" + encodedcert + " (" + encodedcert.length() + " chars)");
            byte[] certbytes = Base64.decode(encodedcert);
            // get the certificate chain
            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            Collection c = cf.generateCertificates(new ByteArrayInputStream(certbytes));
            if (c.size() == 1) {
                // just a single cert, so re-read bytes
                // why do this?  Following lead of
                // http://www.agentbob.info/agentbob/80/version/default/part/AttachmentData/data/ImportKey.java
                X509Certificate[] certs = new X509Certificate[1];
                certs[0] = (X509Certificate) cf.generateCertificate(new ByteArrayInputStream(certbytes));
                pair.cert_chain = certs;
            } else {
                pair.cert_chain = (X509Certificate[]) c.toArray(new X509Certificate[c.size()]);
            }
        } else {
            throw new IOException ("Can't find certificate in PEM file " + certificate_file);
        }

        if ((private_key_file != null) && private_key_file.exists()){
            // what kind of private key file?
            if (private_key_file.getCanonicalPath().toLowerCase().endsWith(".pk8")) {
                // pk8 key
                throw new IOException("Can't handle pk8 keys yet");
            } else {
                throw new IOException("Unrecognized suffix on private key file " + private_key_file);
            }
        } else {
            m = PEM_KEY_PATTERN.matcher(filecontent);
            if (m.find()) {
                String encodedkey = m.group(1);
                System.err.println("encodedkey is\n" + encodedkey + " (" + encodedkey.length() + " chars)");
                byte[] keybytes = Base64.decode(encodedkey);
                // and the private key
                KeyFactory kf = KeyFactory.getInstance("RSA");
                PKCS8EncodedKeySpec keysp = new PKCS8EncodedKeySpec ( keybytes );
                pair.pkey = kf.generatePrivate (keysp);
            } else {
                throw new IOException("Can't find an RSA private key section in specified file " + certificate_file);
            }
        }
        client_certs.put(alias, pair);
    }

    public String chooseEngineClientAlias (String[] keyTypes,
                                           Principal[] issuers,
                                           SSLEngine engine) {
        // System.err.println("chooseEngineClientAlias " + engine);
        return null;
    }

    public String chooseClientAlias (String[] keyTypes,
                                     Principal[] issuers,
                                     java.net.Socket socket) {
        InetAddress addr = socket.getInetAddress();
        if (addr == null)
            return null;
        String alias = addr.getHostAddress() + ":" + Integer.toString(socket.getPort());
        // System.err.println("chooseClientAlias " + alias);
        return alias;
    }

    public String chooseServerAlias (String keyType,
                                     Principal[] issuers,
                                     java.net.Socket socket) {
        // System.err.println("chooseServerAlias " + socket);
        return null;
    }

    public String[] getClientAliases (String keyType, Principal[] issuers) {
        return (String[]) (client_certs.keySet().toArray(new String[client_certs.size()]));
    }

    public String[] getServerAliases (String keyType, Principal[] issuers) {
        return new String[0];
    }

    public X509Certificate[] getCertificateChain (String thealias) {
        CertKeyPair p = (CertKeyPair) client_certs.get(thealias);
        System.err.println("getCertificateChain(" + thealias + ") => " + p);
        if (p != null)
            return p.cert_chain;
        else
            return null;
    }

    public PrivateKey getPrivateKey (String thealias) {
        CertKeyPair p = (CertKeyPair) client_certs.get(thealias);
        // System.err.println("getPrivateKey(" + thealias + ") => " + p);
        if (p != null)
            return p.pkey;
        else
            return null;
    }

    public boolean addJavaClientCert (Configurator conf, String alias)
        throws java.io.IOException, GeneralSecurityException {

        String pathname = conf.get("java-client-certificate-file");
        System.err.println("conf.get of java-client-certificate-file for " + alias + " returns " + pathname);
        if (pathname != null) {
            File certfile = new File(pathname);

            if (certfile.exists()) {

                // see if there's a password
                String password = conf.get("java-client-private-key-password",
                                           // by default, uplib-certificate uses "server" as a password
                                           "server");

                // check to see if it's a PKCS#12 file
                if (pathname.toLowerCase().endsWith(".p12") ||
                    pathname.toLowerCase().endsWith(".pfx")) {
                    // yes
                    addPKCS12Certificate(alias, certfile, password);
                    return true;

                } else if (pathname.toLowerCase().endsWith(".pem")) {
                    // pem instead, might have separate key file
                    File keyfile = null;
                    String keyfilename = conf.get("java-client-private-key-file");
                    if (keyfilename != null) {
                        keyfile = new File(keyfilename);
                        if (!keyfile.exists()) {
                            throw new IOException("Can't find specified private-key file " + keyfilename);
                        }
                    }
                    addPEMFile(alias, certfile, keyfile, password);
                    return true;
                } else {
                    throw new IOException("Can't figure out type of java-client-certificate-file " + pathname);
                }
            } else {
                throw new IOException("Specified certificate file " + pathname + " doesn't exist!");
            }
        }
        return false;
    }

    public boolean addCertificateViaConfigurator (URL u)
        throws IOException, GeneralSecurityException {

        int port = u.getPort();
        InetAddress addr = InetAddress.getByName(u.getHost());
        InetAddress localhost = InetAddress.getLocalHost();
        String hostname = addr.getCanonicalHostName();
        boolean local = (addr.isAnyLocalAddress() || addr.isLoopbackAddress() || addr.equals(localhost));
        String hostaddr = addr.getHostAddress();
        if (port < 0)
            port = 80;
        String portno = Integer.toString(port);
        String[] sections = new String[3];

        if (local) {
            sections[0] = Configurator.machineID() + ":" + portno;
            sections[1] = hostaddr + ":" + portno;
            sections[2] = "default";
        } else {
            sections[0] = hostaddr + ":" + portno;
            sections[1] = hostname + ":" + portno;
            sections[2] = "default";
        }
        Configurator conf = new Configurator(sections);
        return addJavaClientCert(conf, hostaddr + ":" + portno);
    }
}

