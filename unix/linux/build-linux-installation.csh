#!/bin/tcsh
#
# This file is part of the "UpLib 1.7.11" release.
# Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Script to build UpLib and its prerequisites from source on a Linux system.
#
# It assumes that you have already provided Java and Python.
# Optionally, it will install the various Python packages (Medusa, ReportLab,
# email, mutagen, ssl, and PIL).
#
# Further, it uses the standard distribution jarfile for Lucene, rather than compiling
# it from the Java sources.
#

if ($#argv < 1) then
  echo "Usage:  $0 DISTDIR UPLIB-TARFILE PREREQS-DIR [BUILD-PYTHON-MODULES]"
  exit 1
endif

set distdir=$1
set uplibtar=$2
set prereqdir=$3
if ($#argv < 4) then
  set build_python_modules=0
else
  set build_python_modules=1
endif

echo "$0 $*"

set shorthostname=`/bin/hostname`
set ourhostname=`/usr/bin/host $shorthostname | /usr/bin/awk '{print $1}'`
set python=`which python`
set osversion=`${python} -c "import platform, string; print string.join(platform.release()[0].split('.'), ' ')"`
set pyversion=`${python} -c "import platform; print '.'.join([str(x) for x in platform.python_version_tuple()[:2]])"`
set my_identity=`id -un`

if (-e ${distdir}) then
  echo "The DISTDIR, ${distdir}, already exists.  To prevent misunderstandings, please remove it first."
  exit 1
endif

if ( ! $?BUILD_LOCATION ) then
  setenv BUILD_LOCATION /tmp/build-linux-uplib-$$
endif

mkdir -p ${distdir}
chown -R ${my_identity} ${distdir}
chmod -R 777 ${distdir}
mkdir -p ${distdir}/bin
mkdir -p ${distdir}/man/man1
mkdir -p ${distdir}/share/ghostscript/fonts
rm -rf ${BUILD_LOCATION}
mkdir -p ${BUILD_LOCATION}

if ( ! -e /etc/uplib-machine-id ) then
   if ( -x /usr/bin/uuidgen ) then
     echo "Creating machine UUID..."
     sudo /usr/bin/uuidgen > /etc/uplib-machine-id
   endif
endif

pushd ${BUILD_LOCATION}

if ( -x /project/uplib/splitup/dist/linux/splitup ) then
    install -m 555 /project/uplib/splitup/dist/linux/splitup ${distdir}/bin
endif

foreach file ( ${prereqdir}/*.tar.gz ${prereqdir}/*.tgz )
  echo "unpacking $file..."
  tar xfz $file
end
foreach file ( ${prereqdir}/*.tar.bz2 )
  echo "unpacking $file..."
  bunzip2 < $file | tar xvf -
end
echo "unpacking ${uplibtar}..."
tar xvfz ${uplibtar}

set uplibversion=`cat uplib-*/VERSION`
echo "UpLib version is ${uplibversion}"

# We assume that simple-*.zip and jodconverter-*.zip are present in prereqs for ToPDF
set simpledist=${prereqdir}/simple-*.zip
set jodconverterdist=${prereqdir}/jodconverter-*dist.zip

echo "-- libpng --"
cd libpng-*
./configure --prefix=${distdir}
make
make install

echo "-- libjpeg --"
setenv CPPFLAGS -fPIC
cd ../jpeg*
./configure --prefix=${distdir}
make
make install
make install-lib
make install-headers
ranlib ${distdir}/lib/libjpeg.a

setenv CPPFLAGS "-I${distdir}/include"
setenv LDFLAGS "-L${distdir}/lib"
setenv CXXFLAGS "-I${distdir}/include"

echo "-- jbig2dec --"
cd ../jbig2dec*
./configure --prefix=${distdir}
make
make install

echo "-- ghostscript --"
cd ../ghostscript-8*
ln -s ../jpeg-6b ./jpeg
./configure --without-x --prefix=${distdir}
make
make install

echo "-- jasper --"
# now install the jasper tool included in the Ghostscript build
cd jasper
./configure --prefix=${distdir}
make
install -m 555 src/appl/jasper ${distdir}/bin/jasper
cd ..

echo "-- ghostscript fonts --"
cd ../fonts
install -m 444 * ${distdir}/share/ghostscript/fonts

echo "-- libtiff --"
cd ../tiff-*
./configure --prefix=${distdir} --without-x
make
make install

echo "-- freetype2 --"
cd ../freetype-2.*
# next, enable the bytecode interpreter
rm -f ./foo-mac-uplib
cp include/freetype/config/ftoption.h ./foo-mac-uplib
rm -f include/freetype/config/ftoption.h
sed -e 's;/\* #define  TT_CONFIG_OPTION_BYTECODE_INTERPRETER \*/;#define TT_CONFIG_OPTION_BYTECODE_INTERPRETER;' < ./foo-mac-uplib > include/freetype/config/ftoption.h
# now build
./configure --prefix=${distdir}
make
make install
cp ${distdir}/include/ft2build.h ${distdir}/include/freetype2/                # for xpdf
rm -f ./foo-mac-uplib

echo "-- t1lib --"
cd ../t1lib-5.*
./configure --without-x --without-athena --prefix=${distdir}
make without_doc
make install

echo "-- leptonica --"
# requires leptonica-1.62 or better
cd ../leptonlib-*
./configure --prefix=${distdir}
make DEBUG=no
make install DEBUG=no

echo "-- xpdf --"
cd ..
set xpdf=`ls -d xpdf-3.*`
cd $xpdf
if ( $xpdf == "xpdf-3.00" ) then
   patch -p0 < ../uplib-*/patches/xpdf-3.00-PATCH
else if ( $xpdf == "xpdf-3.01" ) then
   patch -p0 < ../uplib-*/patches/xpdf-3.01-PATCH
else if ( $xpdf == "xpdf-3.02" ) then
   patch -p0 < ../uplib-*/patches/xpdf-3.02-PATCH
endif
./configure --prefix=${distdir} --enable-multithreaded --enable-wordlist --with-t1-library=${distdir}/lib --with-t1-includes=${distdir}/include --with-freetype2-library=${distdir}/lib --with-freetype2-includes=${distdir}/include/freetype2 --without-x
make
make install

echo "-- htmldoc --"
cd ..
set htmldoc=`ls -d htmldoc-1.*`
cd $htmldoc
if ( $htmldoc == "htmldoc-1.8.24" ) then
   patch -p0 < ../uplib-*/HTMLDOC-1.8.24-PATCH
endif
./configure --without-gui --prefix=${distdir}
make
make install

echo "-- ytnef --"
cd ../libytnef-*
./configure --prefix=${distdir}
make
make install

cd ../ytnef-*
# we're using the modified version already, so we don't need to apply the patch
# we do it this way so that we don't have to run autoconf after patching the configure.ac file
./configure --prefix=${distdir}
make
make install

# cd ../checkocr-*
# ./configure --prefix=${distdir}
# make
# make install
# install -m 444 ${prereqdir}/langmodel_brown_5_05 ${distdir}/lib

# cd ../stunnel-4.*
# ./configure --prefix=${distdir}
# make
# make install << EOF
# US
# California
# Palo Alto
# PARC
# UpLib
# $ourhostname
# EOF

if ( ${build_python_modules} ) then

    echo "== Now some Python packages..."

    # figure out site-packages location
    # Note that this code needs to be kept in sync with the code in uplib-check-angel.in,
    # which figures out what directory to put on its path
    set sitedir=`${python} -c "import distutils.sysconfig; print distutils.sysconfig.get_python_lib(plat_specific=True)"`
    set platspot=`${python} -c "import os; import distutils.sysconfig as sc; print sc.get_python_lib(plat_specific=True, prefix='${distdir}')"`
    set pythspot=`${python} -c "import os; import distutils.sysconfig as sc; print sc.get_python_lib(plat_specific=False, prefix='${distdir}')"`
    set py_major=`${python} -c "import sys; print sys.version_info[0]"`
    set py_minor=`${python} -c "import sys; print sys.version_info[1]"`
    echo "platspot is ${platspot}, pythspot is ${pythspot}"
    if (! -d ${platspot}) then
       mkdir -p ${platspot}
    endif
    if (! -d ${pythspot}) then
       mkdir -p ${pythspot}
    endif

    setenv PYTHONPATH "${platspot}:${pythspot}"

    echo "building setuptools..."
    cd ../setuptools-*
    if ( -e ../pylucene-*/jcc/jcc/patches/patch.43.0.6c7 ) then
       echo "patching setuptools with patch.43.0.6c7"
       patch -Nup0 < ../pylucene-*/jcc/jcc/patches/patch.43.0.6c7
    else if ( -e ../pylucene-*/jcc/jcc/patches/patch.43 ) then
       echo "patching setuptools with patch.43"
       patch -Nup0 < ../pylucene-*/jcc/jcc/patches/patch.43
    endif
    # a bit tricky -- we need to first build an egg, then run sh
    # on it, so that we can use the --install-dir option
    ${python} setup.py bdist_egg
    echo "installing setuptools..."
    sh dist/setuptools*.egg --install-dir=${platspot}

    # for vobject, we need this
    echo "-- python-dateutil --"
    cd ../python-dateutil*
    echo "building python-dateutil..."
    ${python} setup.py build
    ${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}

    echo "-- vobject --"
    cd ../vobject-*
    echo "building vobject..."
    ${python} setup.py build
    ${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}

    echo "-- jcc --"
    # we need to know where java is, to build PyLucene
    set javahome=`${python} ../uplib-*/unix/linux/figure-linux-java.py`
    echo "JAVA_HOME is ${javahome}"
    # we need to know whether to use 32-bit or 64-bit libraries
    set arch=`${python} -c "import platform; print platform.uname()[4]"`
    # we need to know whether Python supports the -m commandline flag
    set moduleflag=`${python} -c "import sys; print ((sys.version_info >= (2, 6)) and '2') or ((sys.version_info >= (2, 5)) and '1') or '0'"`

    cd ../pylucene-*/jcc


    setenv JCC_JDK "$javahome"
    ${python} setup.py build
    ${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}
    cd ..
    setenv JAVA_HOME "$javahome"
    if ($moduleflag == "2") then
       set JCCCOMMAND="${python} -m jcc.__main__ --shared"
    else if ($moduleflag == "1") then
       set JCCCOMMAND="${python} -m jcc --shared"
    else
       set jccpath=./jcc/build/lib.*/jcc
       setenv PYTHONPATH ${PYTHONPATH}:${jccpath}
       set JCCCOMMAND="${python} ${jccpath}/__init__.py --shared"
    endif
    echo "-- pylucene --"
    make PREFIX_PYTHON=/usr ANT=ant PYTHON=${python} JCC="${JCCCOMMAND}" NUM_FILES=1
    make PREFIX_PYTHON=/usr ANT=ant PYTHON=${python} JCC="${JCCCOMMAND}" NUM_FILES=1 install INSTALL_OPT="--root / --prefix '${distdir}'"
    set lucenejar=`pwd`/build/lucene/lucene-core-*jar
    echo "lucenejar is $lucenejar"
    setenv PYTHONPATH ${platspot}:${pythspot}

    #
    # None of the modules after this use setuptools
    #

    echo "-- medusa --"
    cd ../medusa-0.5.4
    patch -p0 < ../uplib-*/patches/MEDUSA-PATCH-2
    patch -p0 < ../uplib-*/patches/medusa-0.5.4-PATCH   # fix deprecations
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- mutagen --"
    cd ../mutagen-*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- PIL --"
    cd ../Imaging-1.1.*
    sed -e "s;JPEG_ROOT = None;JPEG_ROOT = libinclude('${distdir}');" < setup.py > setup2.py
    ${python} setup2.py build
    ${python} setup2.py install --prefix=${distdir}

    echo "-- email-4 --"
    cd ../email-4*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

set needs_ssl=`${python} -c "import platform; ((platform.python_version_tuple() > (2, 6, 1)) and 'no') or 'yes'"`

if ( $needs_ssl == "yes") then
    echo "-- ssl module --"
    cd ../ssl-*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}
endif

    echo "-- ReportLab --"
    cd ../ReportLab_2_*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- epydoc --"
    cd ../epydoc-*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- feedparser --"
    cd ../feedparser*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- guess-language --"
    cd ../guess-language*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- BeautifulSoup --"
    cd ../BeautifulSoup*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- pyglet --"
    cd ../pyglet-*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    echo "-- hachoir --"
    cd ../hachoir-core*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    cd ../hachoir-parser*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}

    cd ../hachoir-metadata*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}


#     echo "adding Python packages to ${sitedir}"

#     rm -f ${sitedir}/uplib-${uplibversion}.pth
#     /bin/cat <<EOF >${sitedir}/uplib-${uplibversion}.pth
# ${sitespot}
# ${distdir}/lib/python${py_major}.${py_minor}/site-packages/PIL
# ${distdir}/lib64/python${py_major}.${py_minor}/site-packages/PIL
# EOF
#     chmod 444 ${sitedir}/uplib-${uplibversion}.pth

else

    set lucenejar=${BUILD_LOCATION}/uplib-*/java/lucene-core-*.jar
    echo "lucenejar is $lucenejar"

endif   # build_python_modules

echo "Building UpLib..."

cd ${BUILD_LOCATION}/uplib-*
set path = ( ${distdir}/bin ${distdir}/sbin $path /usr/local/bin /usr/lib/openoffice.org/program )
setenv PYTHONPATH ${platspot}:${pythspot}
./configure --prefix=${distdir} --without-scoretext --with-jodconverter-dist=${jodconverterdist} --with-simple-dist=${simpledist} --with-lucene=${lucenejar}
touch doc/manual.pdf
make
make install

echo "Building a valid SSL certificate..."

set fqdn=`${python} -c "import socket, string, os; hostname = socket.getfqdn(); hostname = ((string.find(hostname, '.') < 0 and hasattr(os, 'uname')) and os.uname()[1]) or hostname; print string.lower(hostname)"`

echo "`/bin/date` UpLib installer:  Building SSL certificate for this machine (${fqdn})"

rm -f ${distdir}/lib/UpLib-${uplibversion}/stunnel.pem
${distdir}/bin/uplib-certificate --hostname=${fqdn} --certificate=${distdir}/lib/UpLib-${uplibversion}/stunnel.pem

echo "Creating machine.config..."
rm -f "${distdir}/lib/UpLib-${uplibversion}/machine.config"
cat > "${distdir}/lib/UpLib-${uplibversion}/machine.config" <<EOF
FQDN: ${fqdn}
OS: Linux
EOF

# echo "`/bin/date` UpLib installer:  installing /usr/local/bin symlinks for UpLib command-line tools"
# rm -f /usr/local/bin/uplib-add-document
# ln -s ${distdir}/bin/uplib-add-document /usr/local/bin
# rm -f /usr/local/bin/uplib-check-angel
# ln -s ${distdir}/bin/uplib-check-angel /usr/local/bin
# rm -f /usr/local/bin/uplib-get-document
# ln -s ${distdir}/bin/uplib-get-document /usr/local/bin
# rm -f /usr/local/bin/uplib-make-repository
# ln -s ${distdir}/bin/uplib-make-repository /usr/local/bin
# rm -f /usr/local/bin/uplib-portal
# ln -s ${distdir}/bin/uplib-portal /usr/local/bin

echo "Done."

popd
