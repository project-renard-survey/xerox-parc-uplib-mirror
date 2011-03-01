#!/bin/csh
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

if ($# < 1) then
  echo "Usage:  $0 DISTDIR UPLIB-TARFILE PREREQS-DIRECTORY [NO-SETUP]"
  exit 1
endif

set distdir=$1
set uplibtar=$2
set prereqdir=$3
if ($# == 4) then
  set nosetup=$4
else
  set nosetup=0
endif

set python=/usr/bin/python

set uplibtar=`${python} -c "import os, sys; print os.path.abspath(sys.argv[1])" "${uplibtar}"`

set shorthostname=`/bin/hostname`
set ourhostname=`/usr/bin/host $shorthostname | /usr/bin/awk '{print $1}'`
set osversion=`${python} -c "import platform; print platform.release().split('.')[0]"`

if ( $osversion[1] == '11' ) then
   set macosversion="10.7"
else if ( $osversion[1] == '10' ) then
   set macosversion="10.6"
else if ( $osversion[1] == '9' ) then
   set macosversion="10.5"
else if ( $osversion[1] == '8' ) then
   set macosversion="10.4"
else if ( $osversion[1] == '7' ) then
   set macosversion="10.3"
else
   echo "Can't build installer for Darwin $osversion[1] yet."
   exit 1
endif

set pyversion = `${python} -c "import platform; print '.'.join([str(x) for x in platform.python_version_tuple()[:2]])"`

set processortype=`${python} -c "import platform; print platform.architecture()[0]"`

if (-e ${distdir}) then
  echo "The DISTDIR, ${distdir}, already exists.  To prevent misunderstandings, please remove it first."
  exit 1
endif

echo "Mac OS X version is ${macosversion}, processor type is ${processortype}."

set my_identity=`id -un`

if ( ! $?BUILD_LOCATION ) then
  setenv BUILD_LOCATION /tmp/build-mac-uplib-$$
endif

rm -rf ${distdir}
rm -f /tmp/build-mac-uplib-tmp-$$
mkdir -p ${distdir}
chown -R ${my_identity} ${distdir}
chmod -R 777 ${distdir}
mkdir -p ${distdir}/bin
mkdir -p ${distdir}/man/man1
mkdir -p ${distdir}/share/ghostscript/fonts
rm -rf ${BUILD_LOCATION}
mkdir -p ${BUILD_LOCATION}

pushd ${BUILD_LOCATION}

if ( -x /project/uplib/splitup/dist/macosx-${macosversion}/splitup ) then
    install -m 555 /project/uplib/splitup/dist/macosx-${macosversion}/splitup ${distdir}/bin
endif

foreach file ( ${prereqdir}/*.tar.gz ${prereqdir}/*.tgz )
  tar xvfz $file
end
foreach file ( ${prereqdir}/*.tar.bz2 )
  bunzip2 < $file | tar xvf -
end
tar xvfz ${uplibtar}

set uplibversion=`cat ${BUILD_LOCATION}/uplib-*/VERSION`
set uplibmajorversion=`${python} -c "print '${uplibversion}'.split('.')[0]"`
set uplibminorversion=`${python} -c "print '${uplibversion}'.split('.')[1]"`

# We assume that simple-*.zip and jodconverter-*.zip are present in prereqs for ToPDF
set simpledist=${prereqdir}/simple-*.zip
set jodconverterdist=${prereqdir}/jodconverter-*dist.zip

cd libpng-*
./configure --prefix=${distdir}
make
make install

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

cd ../jbig2dec*
./configure --prefix=${distdir}
make
make install

cd ../ghostscript-8*
ln -s ../jpeg-6b ./jpeg
# Macs may not have X11, so make sure not to link it in by accident
./configure --without-x --prefix=${distdir}
make
make install

# now install the jasper tool included in the Ghostscript build
cd jasper
./configure --prefix=${distdir}
make
install -m 555 src/appl/jasper ${distdir}/bin/jasper
cd ..

cd ../fonts
install -m 444 * ${distdir}/share/ghostscript/fonts

cd ../tiff-*
./configure --prefix=${distdir} --without-x
make
make install

cd ../freetype-2.*
# first, get rid of erroneous mac flag
cp include/freetype/config/ftconfig.h /tmp/build-mac-uplib-tmp-$$
rm -f include/freetype/config/ftconfig.h
sed -e 's/#define FT_MACINTOSH 1/#undef FT_MACINTOSH/' < /tmp/build-mac-uplib-tmp-$$ > include/freetype/config/ftconfig.h
# next, enable the bytecode interpreter
rm -f /tmp/build-mac-uplib-tmp-$$
cp include/freetype/config/ftoption.h /tmp/build-mac-uplib-tmp-$$
rm -f include/freetype/config/ftoption.h
sed -e 's;/\* #define  TT_CONFIG_OPTION_BYTECODE_INTERPRETER \*/;#define TT_CONFIG_OPTION_BYTECODE_INTERPRETER;' < /tmp/build-mac-uplib-tmp-$$ > include/freetype/config/ftoption.h
# now build
./configure --prefix=${distdir}
make
make install
cp ${distdir}/include/ft2build.h ${distdir}/include/freetype2/                # for xpdf

cd ../t1lib-5.*
./configure --without-x --without-athena --prefix=${distdir}
make without_doc
make install

cd ../tnef-*
./configure --prefix=${distdir}
make
make install

# requires Leptonica 1.62 or better
cd ../leptonlib-*
./configure --prefix=${distdir}
make DEBUG=no
make install DEBUG=no

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

# install xpdf support for Chinese, Korean, etc.
cd ..
cd xpdf-character-set-support
mkdir -p ${distdir}/share/xpdf
(cd xpdf-char-info; cp -r * ${distdir}/share/xpdf/ )
sed -e "s;SHAREDIR;${distdir}/share;g" < xpdfrc-patch >> ${distdir}/etc/xpdfrc

cd ..
set htmldoc=`ls -d htmldoc-1.*`
cd $htmldoc
if ( $htmldoc == "htmldoc-1.8.24" ) then
   patch -p0 < ../uplib-*/HTMLDOC-1.8.24-PATCH
endif
./configure --without-gui --prefix=${distdir}
make
make install

cd ../checkocr-*
./configure --prefix=${distdir}
make
make install
install -m 444 ${prereqdir}/langmodel_brown_5_05 ${distdir}/lib

cd ../enscript-*
./configure --without-x --prefix=${distdir} --with-media=usletter --with-ps-level=3
make
make install

cd ../stunnel-4.*
./configure --prefix=${distdir}
make
make install << EOF
US
California
Palo Alto
PARC
UpLib
$ourhostname
EOF

set sitepackages="${distdir}/lib/python${pyversion}/site-packages"

cd ../medusa-0.5.4
patch -p0 < ../uplib-*/patches/MEDUSA-PATCH-2
patch -p0 < ../uplib-*/patches/medusa-0.5.4-PATCH
${python} setup.py build
${python} setup.py install --prefix=${distdir}

cd ../mutagen-*
${python} setup.py build
${python} setup.py install --prefix=${distdir}

cd ../Imaging-1.1.*
rm -f /tmp/build-mac-uplib-tmp-$$
cp setup.py /tmp/build-mac-uplib-tmp-$$
sed -e "s;/sw;${distdir};" < /tmp/build-mac-uplib-tmp-$$ > setup.py
${python} setup.py build
${python} setup.py install --prefix=${distdir}
echo "${sitepackages}/PIL" > "${sitepackages}/PIL.pth"

cd ../email-4*
${python} setup.py build
${python} setup.py install --prefix=${distdir}

# for vobject and JCC
setenv PYTHONPATH ${distdir}/lib/python${pyversion}/site-packages
cd ../setuptools-*
${python} setup.py build
${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}

# for vobject, we need this
cd ../python-dateutil*
${python} setup.py build
${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}

cd ../tornado-*
${python} setup.py build
${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}

cd ../vobject-*
${python} setup.py build
${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}

# we need to know where java is, to build PyLucene
if ( -x /usr/libexec/java_home ) then
   set javahome=`/usr/libexec/java_home -v 1.5+`
else
   set javahome=/Library/Java/Home
endif
# we need to know whether to use 32-bit or 64-bit libraries
set arch=`${python} -c "import platform; print platform.uname()[4]"`
# we need to know whether Python supports the -m commandline flag
set moduleflag=`${python} -c "import sys; print (sys.version_info >= (2, 5)) and '1' or '0'"`

setenv PYTHONPATH "${sitepackages}"

cd ../pylucene-*/jcc
${python} setup.py install --single-version-externally-managed --root=/ --prefix=${distdir}
cd ..

setenv JAVA_HOME "$javahome"
set jccpath=./jcc/build/lib.*/jcc
setenv PYTHONPATH ${jccpath}:${PYTHONPATH}
set pythonhome=`dirname ${python}`
set pythonhome=`dirname ${pythonhome}`
if ( "${pyversion}" == "2.5" ) then
   set JCCCOMMAND="${python} -m jcc --shared"
else if ( "${pyversion}" == "2.3" ) then
   set JCCCOMMAND="${distdir}/lib/python${pyversion}/site-packages/jcc/__init__.py --shared"
else
   set JCCCOMMAND="${python} -m jcc.__main__ --shared"
endif
make PREFIX_PYTHON=${pythonhome} ANT=ant PYTHON=${python} JCC="${JCCCOMMAND}" NUM_FILES=1
make PREFIX_PYTHON=${pythonhome} ANT=ant PYTHON=${python} JCC="${JCCCOMMAND}" NUM_FILES=1 install INSTALL_OPT="--root / --prefix '${distdir}'"
unsetenv PYTHONPATH
install -m 444 build/lucene/lucene-core-*.jar ${distdir}/lib
set lucenejar=${distdir}/lib/lucene-core-*.jar

echo "installing ReportLab..."
cd ../ReportLab_2_*
${python} setup.py build
${python} setup.py install --prefix=${distdir}

echo "installing epydoc..."
cd ../epydoc*
${python} setup.py build
${python} setup.py install --prefix=${distdir}

echo "installing feedparser..."
cd ../feedparser*
${python} setup.py build
${python} setup.py install --prefix=${distdir}

echo "installing guess_language..."
cd ../guess-language-*
${python} setup.py build
${python} setup.py install --prefix=${distdir}

echo "installing BeautifulSoup..."
cd ../BeautifulSoup*
${python} setup.py build
${python} setup.py install --prefix=${distdir}

# install the video support
if ( -f ${prereqdir}/../darwin/libavbin.5.dylib ) then

  mkdir -p ${distdir}/lib
  echo "copying ${prereqdir}/../darwin/libavbin.5.dylib -> ${distdir}/lib/"
  cp ${prereqdir}/../darwin/libavbin.5.dylib ${distdir}/lib/
  ln -sf ${distdir}/lib/libavbin.5.dylib ${distdir}/lib/libavbin.dylib
  chmod a+rx ${distdir}/lib/libavbin.5.dylib

  cd ../pyglet-*
  sed -e "s;darwin='/usr/local/lib/libavbin.dylib';darwin='${distdir}/lib/libavbin.dylib';" < pyglet/media/avbin.py > ../avbin.py.$$
  rm -f pyglet/media/avbin.py
  cp ../avbin.py.$$ pyglet/media/avbin.py
  ${python} setup.py build
  ${python} setup.py install --prefix=${distdir}

  cd ../hachoir-core*
  ${python} setup.py build
  ${python} setup.py install --prefix=${distdir}

  cd ../hachoir-parser*
  ${python} setup.py build
  ${python} setup.py install --prefix=${distdir}

  cd ../hachoir-metadata*
  ${python} setup.py build
  ${python} setup.py install --prefix=${distdir}

endif

# install wkpdf for Web page rendering
if ( -f ${prereqdir}/../darwin/wkpdf ) then
  install -m 555 ${prereqdir}/../darwin/wkpdf ${distdir}/bin
endif

set needs_ssl=`${python} -c "import platform; ((platform.python_version_tuple() > (2, 6, 1)) and 'no') or 'yes'"`

if ( $needs_ssl == "yes") then
    echo "installing Python SSL module..."
    cd ../ssl-*
    ${python} setup.py build
    ${python} setup.py install --prefix=${distdir}
endif

cd ${BUILD_LOCATION}

#set sitedir=${distdir}/lib/python${pyversion}

#rm -f ${sitedir}/site-packages/uplib-${uplibversion}.pth
#echo "${distdir}/lib/python${pyversion}/site-packages" > ${sitedir}/site-packages/uplib-${uplibversion}.pth
#echo "${distdir}/lib/python${pyversion}/site-packages/PIL" >> ${sitedir}/site-packages/uplib-${uplibversion}.pth
#chmod 444 ${sitedir}/site-packages/uplib-${uplibversion}.pth

echo "Now doing UpLib..."
cd uplib-*
set path = ( ${distdir}/bin ${distdir}/sbin /usr/bin /bin /usr/sbin /sbin )
setenv PYTHONPATH ${distdir}/lib/python${pyversion}/site-packages
./configure --prefix=${distdir} --with-lucene=${lucenejar} --without-scoretext --with-macosappdir=${distdir}/bin --with-jodconverter-dist=${jodconverterdist} --with-simple-dist=${simpledist}
touch doc/manual.pdf
# tweak the site.config file to put the location of xpdfrc in it
/bin/ed site.config <<EOF
/wordboxes-pdftotext-command = /
s;-q -raw -wordboxes;-cfg ${distdir}/etc/xpdfrc -q -raw -wordboxes;
1
/pdftotext-command = /
s;-q;-cfg ${distdir}/etc/xpdfrc -q;
w
q
EOF
make
make install

if ( $nosetup != "noinstaller" ) then
   
   echo "Building installer..."
   
   # install -m 444 /u/macosx/stunnel.cnf.in ${distdir}/lib/UpLib-${uplibversion}
   
   set parts=`python -c "import string, os, sys; parts = string.split('${distdir}', os.sep); parts = (parts[0] and parts) or parts[1:]; print os.sep + parts[0], apply(os.path.join, parts[1:])"`
   set topdir=$parts[1]
   set restdirs=$parts[2]
   
   rm -rf ${BUILD_LOCATION}/copy
   /usr/bin/ditto --rsrc ${distdir} ${BUILD_LOCATION}/copy/${restdirs}
   
   rm -f ./unix/macosx/package-properties.plist
   /usr/bin/sed -e "s;FULLVERSION;${uplibversion};g" -e "s;MAJORVERSION;${uplibmajorversion};g" -e "s;MINORVERSION;${uplibminorversion};g" < ./unix/macosx/package-properties.plist.in > ./unix/macosx/package-properties.plist
   chmod 555 ./unix/macosx/package-properties.plist
   
   rm -f ./unix/macosx/package-description.plist
   /usr/bin/sed -e "s;FULLVERSION;${uplibversion};g" -e "s;MAJORVERSION;${uplibmajorversion};g" -e "s;MINORVERSION;${uplibminorversion};g" < ./unix/macosx/package-description.plist.in > ./unix/macosx/package-description.plist
   chmod 555 ./unix/macosx/package-description.plist
   
   rm -f ./unix/macosx/package-resources/postinstall
   /usr/bin/sed -e "s;RESTPATH;${restdirs};g" -e "s;VERSION;${uplibversion};g" -e "s;NOSETUP;${nosetup};g" < ./unix/macosx/postinstall.in > ./unix/macosx/package-resources/postinstall
   chmod 555 ./unix/macosx/package-resources/postinstall
   
   rm -f ./unix/macosx/package-resources/postupgrade
   /usr/bin/sed -e "s;RESTPATH;${restdirs};g" -e "s;VERSION;${uplibversion};g" -e "s;NOSETUP;${nosetup};g" < ./unix/macosx/postinstall.in > ./unix/macosx/package-resources/postupgrade
   chmod 555 ./unix/macosx/package-resources/postupgrade
   
   rm -rf /tmp/UpLib-${uplibversion}.pkg
   
   echo "Creating package..."
   
   #packagemaker -build -ds -p /tmp/UpLib-${uplibversion}.pkg \
   #    -f ${distdir} \
   #    -r ./unix/macosx/package-resources \
   #    -d ./unix/macosx/package-description.plist \
   #    -i ./unix/macosx/package-properties.plist
   
   ${python} ./unix/macosx/buildpkg.py --Title="UpLib" --Version="${uplibversion}" --Description="The UpLib Personal Digital Library System, version ${uplibversion}" --BackgroundAlignment="center" --BackgroundScaling="proportional" --DefaultLocation="${topdir}" --BundleIdentifier="com.parc.uplib" --NeedsAuthorization=YES --OutputDir=${BUILD_LOCATION} --Relocatable=NO ${BUILD_LOCATION}/copy ./unix/macosx/package-resources
   
   echo "Building disk image..."
   
   # /usr/libexec/StartupItemContext /usr/bin/hdiutil create -srcfolder ${BUILD_LOCATION}/UpLib-${uplibversion}.pkg -volname "UpLib ${uplibversion} Mac OS X ${macosversion} Installer" -ov ${BUILD_LOCATION}/UpLib-${uplibversion}-MacOSX-${macosversion}-${processortype}-Installer.dmg 
   /usr/bin/hdiutil create -srcfolder ${BUILD_LOCATION}/UpLib-${uplibversion}.pkg -volname "UpLib ${uplibversion} Mac OS X ${macosversion} Installer" -ov ${BUILD_LOCATION}/UpLib-${uplibversion}-MacOSX-${macosversion}-${processortype}-Installer.dmg 
   
endif

echo "Done."

popd
