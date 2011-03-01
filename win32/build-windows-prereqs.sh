#!/bin/bash
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
# We're doing this with sh instead of csh because msys only has sh.
#
# You need to have msys and mingw installed, and this is designed to run in a
# mingw rxvt window.  You'll need msys perl (for OpenSSL), and the msys autoconf tools.
#
# Ghostscript is difficult.  There's a patch for it in the UpLib
# sources, which among other things introduces a dependence on sed,
# which is standard with the msys tools.  You'll also need the sources
# for pthreads-w32 library pthreadGC2.dll, which is built below.
#
# I've tested this with the following set of prereqs:
# BeautifulSoup-3.0.8.tar.gz
# Distutils-1.0.2.tar.gz
# Imaging-1.1.7.tgz
# ReportLab-2.4.tar.gz
# docutils-0.5.tar.gz
# email-4.0.1.tgz
# enscript-1.6.3.tar.gz
# epydoc-3.0.1.tar.gz
# feedparser-4.1.tgz
# freetype-2.3.9.tar.bz2
# ghostscript-8.71.tar.bz2
# grant.exe
# guess-language-0.2.tar.gz
# hachoir-core-1.2.1.tar.gz
# hachoir-metadata-1.2.1.tar.gz
# hachoir-parser-1.2.1.tar.gz
# jasper-1.900.1.tgz
# jbig2dec-0.10.tar.bz2
# jpegsrc.v6b.tar.gz
# leptonlib-1.62.tar.gz
# libpng-1.2.40.tar.gz
# libytnef-1.5.tgz
# medusa-0.5.4.tar.gz
# modified-ytnef.tgz
# mutagen-1.10.1.tar.gz
# openssl-1.0.0.tar.gz
# pyglet-1.1.2.tar.gz
# pylucene-3.0.2-1-src.tar.gz
# python-dateutil-1.4.1.tar.gz
# pywin32-py2.6-214.tar.gz
# pywin32-py2.7-214.tar.gz
# setuptools-0.6c9.tar.gz
# stunnel-4.25.tar.gz
# t1lib-5.1.2.tar.gz
# tiff-3.7.0.tar.gz
# vobject-0.8.1c.tar.gz
# wkhtmltopdf-0.9.5.tar.gz
# xpdf-3.02-pl4.tar.gz
# zlib-1.2.4.tgz


if [ $# -lt 1 ]; then
  echo "Usage:  $0 DISTDIR UPLIB-TARFILE PREREQS-DIRECTORY"
  exit 1
fi

distdir=$1
uplibtar=$2
prereqdir=$3

export python=`which python`

shorthostname=`hostname`
hostname=$shorthostname
osversion=`${python} -c "import platform; print platform.version().split('.')[0]"`

if [ $osversion = '5' ]; then
   win32version="XP"
elif [ $osversion = '6' ]; then
   win32version="Vista"
elif [ $osversion = '7' ]; then
   win32version="Win7"
else
   echo "Can't build installations for Microsoft Windows version $osversion yet."
   exit 1
fi

pyversion=`${python} -c "import platform; print '.'.join([str(x) for x in platform.python_version_tuple()[:2]])"`

processortype=`${python} -c "import platform; print platform.architecture()[0]"`

echo "Microsoft Windows version is ${win32version}, processor type is ${processortype}."

# this version is for the centrally installed "per-machine" python
sitepackages=`${python} -c "import os; import distutils.sysconfig as sc; print sc.get_python_lib(plat_specific=True, prefix='${distdir}').replace(chr(92), '/')"`

# this version is for the privately installed "just for me" python
#sitepackages=`${python} -c "import os; import distutils.sysconfig as sc; print sc.get_python_lib(plat_specific=True).replace(chr(92), '/')"`

my_identity=`id -un`

export BUILD_LOCATION="${BUILD_LOCATION:-/tmp/build-win-uplib-$$}"

rm -f "${BUILD_LOCATION}"
mkdir -p "${distdir}"/bin
mkdir -p "${distdir}"/man/man1
mkdir -p "${distdir}"/share/ghostscript/fonts
export INCLUDE_PATH="${distdir}/include"
mkdir -p ${INCLUDE_PATH}
export LIBRARY_PATH="${distdir}/lib"
mkdir -p ${LIBRARY_PATH}
rm -rf ${BUILD_LOCATION}
mkdir -p ${BUILD_LOCATION}

pushd ${BUILD_LOCATION}

echo "unpacking ${uplibtar}..."
#tar xvfz ${uplibtar}
tar xfz ${uplibtar}

patchesdir=`cd ./uplib-*/patches ; pwd`
echo "patches directory is ${patchesdir}"

javahome=`${python} uplib-*/win32/find-javahome.py`

if [ ! -d "$javahome" -a -x "${javahome}/bin/jar" ]; then
   echo "Java apparently not installed."
   exit 1
fi

echo "JDK home is ${javahome}, site-packages is ${sitepackages}"

echo "unpacking gzipped tar files..."
for file in ${prereqdir}/*.tar.gz ${prereqdir}/*.tgz ; do
  echo "  `basename $file`" ;
  tar xfz $file
done
echo "unpacking bunzip2ed tar files..."
for file in ${prereqdir}/*.tar.bz2 ; do
  echo "  `basename $file`" ;
  bunzip2 < $file | tar xf -
done

uplibversion=`cat ${BUILD_LOCATION}/uplib-*/VERSION`
uplibmajorversion=`${python} -c "print '${uplibversion}'.split('.')[0]"`
uplibminorversion=`${python} -c "print '${uplibversion}'.split('.')[1]"`

echo "-- diruse, grant, and splitup --"
if test -f "${prereqdir}/diruse.exe" ; then
    # Microsoft tool for figuring disk usage
    install -m 555 "${prereqdir}/diruse.exe" "${distdir}/bin/"
fi
if test -f "${prereqdir}/grant.exe" ; then
    # Microsoft tool for granting permissions
    install -m 555 "${prereqdir}/grant.exe" "${distdir}/bin/"
fi

if test -f "${prereqdir}/splitup.exe" ; then
    # PARC tool for recognizing and splitting separator pages
    install -m 555 "${prereqdir}/splitup.exe" "${distdir}/bin/"
fi

echo "-- zlib --"
cd zlib-*
make -f win32/makefile.gcc
INSTALL=/bin/install make install -f win32/makefile.gcc
cp zlib1.dll "${distdir}/bin"

export CPPFLAGS="-I${distdir}/include"
export LDFLAGS="-L${distdir}/lib"
# we include no-write-strings just for xpdf's benefit
export CXXFLAGS="-Wno-write-strings -I${distdir}/include"

echo "-- jpeg6b --"
cd ../jpeg*
./configure --prefix="${distdir}"
patch -p0 < ${patchesdir}/jpeg-msys-PATCH
make
make install
make install-lib
make install-headers

echo "-- libpng --"
cd ../libpng-*
./configure --prefix="${distdir}"
make
make install

echo "-- jbig2dec --"
cd ../jbig2dec*
./configure --prefix="${distdir}"
make
make install

echo "-- openssl --"
cd ../openssl-1.*
./Configure --prefix="${distdir}" disable-capieng mingw
make depend
make
make install

echo "-- ghostscript --"
cd ../ghostscript-8*
(cd bin; install -m 555 * "${distdir}/bin")
(cd lib; install -m 444 * "${distdir}/lib"; install -m 555 ps2pdf* "${distdir}/bin"; install -m 555 pdf2ps* "${distdir}/bin"; install -m 555 eps2* "${distdir}/bin")

cd ../fonts
install -m 444 * "${distdir}/share/ghostscript/fonts"

# echo "-- jasper --"
# # now install the jasper tool included in the Ghostscript build
# cd ../ghostscript-8*/jasper
# ./configure --prefix="${distdir}"
# make
# install -m 555 src/appl/jasper "${distdir}/bin/jasper"
# cd ..

echo "-- jasper --"
cd ../jasper-*
patch -p0 < ${patchesdir}/jasper-1.900-PATCH
./configure --prefix="${distdir}" --without-x
make
make install

echo "-- libtiff --"
cd ../tiff-*
./configure --prefix="${distdir}" --without-x
make
make install
cp "${distdir}/lib/libtiff-3.exe" "${distdir}/bin/"

echo "-- freetype2 --"
cd ../freetype-2.*
# enable the bytecode interpreter
rm -f /tmp/build-win-uplib-tmp-$$
cp include/freetype/config/ftoption.h /tmp/build-win-uplib-tmp-$$
rm -f include/freetype/config/ftoption.h
sed -e 's;/\* #define  TT_CONFIG_OPTION_BYTECODE_INTERPRETER \*/;#define TT_CONFIG_OPTION_BYTECODE_INTERPRETER;' < /tmp/build-win-uplib-tmp-$$ > include/freetype/config/ftoption.h
# now build
./configure --prefix="${distdir}"
make
make install
cp "${distdir}/include/ft2build.h" "${distdir}/include/freetype2/"                # for xpdf

echo "-- t1lib --"
cd ../t1lib-5.*
./configure --without-x --without-athena --prefix="${distdir}"
make without_doc
make install

echo "-- leptonica --"
# requires Leptonica 1.62 or better
cd ../leptonlib-*
./configure --prefix="${distdir}"
make DEBUG=no
make install DEBUG=no

echo "-- xpdf --"
cd ..
xpdf=`ls -d xpdf-3.*`
cd $xpdf
if [ $xpdf = "xpdf-3.00" ]; then
   patch -p0 < ${patchesdir}/xpdf-3.00-PATCH
elif [ $xpdf = "xpdf-3.01" ]; then
   patch -p0 < ${patchesdir}/xpdf-3.01-PATCH
elif [ $xpdf = "xpdf-3.02" ]; then
   patch -p0 < ${patchesdir}/xpdf-3.02-PATCH
fi
# need to tell xpdf about zlib, and need gdi32 MS library for font scanning
export LIBS="-lz -lgdi32"
./configure --prefix="${distdir}" --enable-multithreaded --enable-wordlist --with-t1-library="${distdir}/lib" --with-t1-includes="${distdir}/include" --with-freetype2-library="${distdir}/lib" --with-freetype2-includes="${distdir}/include/freetype2" --without-x
make
make install
export LIBS=

# We use the pre-compiled enscript from gnuwin32.sourceforge.net
echo "-- enscript --"
cd ../enscript-*
install -m 555 ./bin/* "${distdir}/bin/"
install -m 444 ./etc/* "${distdir}/etc/"
cp -r -p ./lib/* "${distdir}/lib/"
cp -r -p ./share/* "${distdir}/share/"

# Use pre-compiled wkhtmltopdf, as well, from http://code.google.com/p/wkhtmltopdf
echo "-- wkhtmltopdf --"
cd ../wkhtmltopdf-*
cp -p *.dll *.exe "${distdir}/bin/"

# echo "-- htmldoc --"
# cd ../htmldoc-*
# ./configure --without-gui --prefix=${distdir}
# make
# make install

mkdir -p "$sitepackages"
export PYTHONPATH="$sitepackages"
export WINSTYLESITEPKGS=`cmd //c echo "${sitepackages}" | "${python}" -c "import sys; sys.stdout.write(sys.stdin.read().strip().strip('\"').replace('/', 2*chr(92)))"`
export WINSTYLEJAVAHOME=`cmd //c echo "${javahome}" | "${python}" -c "import sys; sys.stdout.write(sys.stdin.read().strip().strip('\"').replace('/', 2*chr(92)))"`
export WINSTYLEDISTDIR=`cmd //c echo "${distdir}" | "${python}" -c "import sys; sys.stdout.write(sys.stdin.read().strip().strip('\"').replace('/', 2*chr(92)))"`
# export WINSTYLEPYHOME=`cmd //c echo "${distdir}/python" | "${python}" -c "import sys; sys.stdout.write(sys.stdin.read().replace('/', 2*chr(92)))"`
echo "WINSTYLESITEPKGS is $WINSTYLESITEPKGS, WINSTYLEJAVAHOME is $WINSTYLEJAVAHOME, WINSTYLEDISTDIR is $WINSTYLEDISTDIR"

echo "-- setuptools --"
# for vobject and JCC
cd ../setuptools-*
${python} setup.py build --compiler=mingw32 install --install-lib="$WINSTYLESITEPKGS"

echo "-- python-dateutil --"
# for vobject, we need this
cd ../python-dateutil*
${python} setup.py build --compiler=mingw32 install --single-version-externally-managed --root /c/ --prefix="${distdir}"

echo "-- vobject --"
cd ../vobject-*
${python} setup.py build --compiler=mingw32 install --single-version-externally-managed --root /c/ --prefix="${distdir}"

echo "-- jcc --"
export PATH="$PATH:${javahome}/jre/bin/client"
echo "PATH is $PATH"
cd ../pylucene-3.0.*/jcc
# note that this patch still works for 3.0.1/3.0.2
patch -p0 < ${patchesdir}/jcc-2.9-mingw-PATCH
export JCC_ARGSEP=";"
export JCC_JDK="$WINSTYLEJAVAHOME"
export JCC_CFLAGS="-fno-strict-aliasing;-Wno-write-strings"
export JCC_LFLAGS="-L${WINSTYLEJAVAHOME}\\lib;-ljvm"
export JCC_INCLUDES="${WINSTYLEJAVAHOME}\\include;${WINSTYLEJAVAHOME}\\include\\win32"
export JCC_JAVAC="${WINSTYLEJAVAHOME}\\bin\\javac.exe"
${python} setup.py build --compiler=mingw32 install --single-version-externally-managed --root /c/ --prefix="${distdir}"
if [ -f jcc/jcc.lib ]; then
  cp -p jcc/jcc.lib "${sitepackages}/jcc/jcc.lib"
fi
# for 3.0.2 compiled with MinGW GCC 4.x and "--shared", we also need two
# GCC libraries
if [ -f /mingw/bin/libstdc++-6.dll ]; then
  install -m 555 /mingw/bin/libstdc++-6.dll "${distdir}/bin/"
  echo "copied libstdc++-6.dll"
fi
if [ -f /mingw/bin/libgcc_s_dw2-1.dll ]; then
  install -m 555 /mingw/bin/libgcc_s_dw2-1.dll "${distdir}/bin/"
  echo "copied libgcc_s_dw2-1.dll"
fi
cd ..

echo "-- pylucene --"
export PATH="${PATH}:${javahome}/bin"
pythonhome=`dirname ${python}`
pythonhome=`dirname ${pythonhome}`
if [ "${pyversion}" == "2.5" ]; then
   JCCCOMMAND="${python} -m jcc --shared --compiler mingw32"
elif [ "${pyversion}" == "2.3" ]; then
   JCCCOMMAND="${sitepackages}/jcc/__init__.py --shared --compiler mingw32"
else
   JCCCOMMAND="${python} -m jcc.__main__ --shared --compiler mingw32"
fi
export JAVA_HOME="${WINSTYLEJAVAHOME}"
make PREFIX_PYTHON=${pythonhome} ANT=ant PYTHON=${python} JCC="${JCCCOMMAND}" NUM_FILES=3
make PREFIX_PYTHON=${pythonhome} ANT=ant PYTHON=${python} JCC="${JCCCOMMAND}" NUM_FILES=3 install INSTALL_OPT="--root /c/ --prefix '${WINSTYLEDISTDIR}'"
install -m 444 build/lucene/lucene-core-*.jar "${distdir}/lib"
set lucenejar=${distdir}/lib/lucene-core-*.jar

#
# None of the modules after this use setuptools
#

echo "-- medusa --"
cd ../medusa-0.5.4
patch -p0 < ${patchesdir}/MEDUSA-PATCH-2
patch -p0 < ${patchesdir}/medusa-0.5.4-PATCH
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- mutagen --"
cd ../mutagen-*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- PIL --"
cd ../Imaging-1.1.*
patch -p0 < ${patchesdir}/PIL-1.1.7-msys-PATCH
# need to tell setup.py where to find image-handling libraries
export PIL_JPEG_ROOT="$WINSTYLEDISTDIR"
export PIL_ZLIB_ROOT="$WINSTYLEDISTDIR"
export PIL_TIFF_ROOT="$WINSTYLEDISTDIR"
export PIL_FREETYPE_ROOT="$WINSTYLEDISTDIR"
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"
echo "${sitepackages}/PIL" > "${sitepackages}/PIL.pth"

echo "-- docutils --"
cd ../docutils-*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- email --"
cd ../email-4*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- ReportLab --"
cd ../ReportLab_2_*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- feedparser --"
cd ../feedparser*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- guess_language --"
cd ../guess-language*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- BeautifulSoup --"
cd ../BeautifulSoup*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

# install the video support
if [ -f "${prereqdir}/avbin.dll" ]; then

  mkdir -p "${distdir}/bin"
  echo "-- copying ${prereqdir}/avbin.dll -> ${distdir}/bin/ --"
  cp "${prereqdir}/avbin.dll" "${distdir}/bin/avbin.dll"

  echo "-- pyglet --"
  cd ../pyglet-*
  ${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

  echo "-- hachoir-core --"
  cd ../hachoir-core*
  ${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

  echo "-- hachoir-parser --"
  cd ../hachoir-parser*
  ${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

  echo "-- hachoir-metadata --"
  cd ../hachoir-metadata*
  ${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

fi

echo "-- epydoc --"
cd ../epydoc*
${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"

echo "-- pywin32 --"
cd ../pywin32-py${pyversion}-*
cp -r -p * ${sitepackages}
rm -f /c/windows/system32/pythoncom*.dll /c/windows/system32/pywintypes*.dll
cp -r -p * pywin32_system32/pythoncom*.dll /c/windows/system32/
cp -r -p * pywin32_system32/pywintypes*.dll /c/windows/system32/

needssslmod=`${python} -c "import sys; print ((sys.version_info < (2, 6, 1)) and 'yes') or 'no'"`

if [ "$needssslmod" = "yes" ]; then
  echo "-- python-ssl --"
  cd ../ssl-* ;
  ${python} setup.py build --compiler=mingw32 install --prefix="${WINSTYLEDISTDIR}"
fi

echo "-- jodconverter and simple --"
cp "${prereqdir}"/simple-*.zip "${prereqdir}"/jodconverter-*.zip "${distdir}/share"

popd
pushd "${distdir}"

cp ./Scripts/* ./bin/
rm -rf Scripts

echo "*** Now building /tmp/uplib-windows-prereqs.tgz..."

tar cvfz /tmp/uplib-windows-prereqs.tgz *

popd

echo "Done."
