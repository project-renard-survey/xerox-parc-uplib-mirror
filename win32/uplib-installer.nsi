; Script generated by the HM NIS Edit Script Wizard.
;
; USAGERIGHTS uplib
;
; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "UpLib"
!define PRODUCT_VERSION "${UPLIB_VERSION}"
; !define UPLIB_FOLDER -- this is now defined as a parameter
!define PRODUCT_PUBLISHER "PARC Inc."
!define PRODUCT_WEB_SITE "http://uplib.parc.com/"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\UpLib"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; PDF Converter-related defines
!define ABXPDF_REGKEY "Software\CUSTPDF Writer"
!define PDFCREATOR_REGKEY "Software\PDFCreator\Program"
!define PDFCREATOR_PDF_REGKEY "Software\PDFCreator\Printing\Formats\PDF\General"
!define ABXPDF_DIR "abxpdf"
!define ABXPDF_INSTALLER "abxpdf\Setup.exe"
!define PDFCONVERTER_DIR "pdfconverter"
!define PDFCONVERTER_INSTALL_DIR "$PROGRAMFILES\UpLib PDF Print Server"

# Directories and files we package up
!define PYTHON_INSTALLER "python-2.5.2.msi"
!define PIL_INSTALLER "PIL-1.1.6.win32-py2.5.exe"
!define PYWIN_INSTALLER "pywin32-210.win32-py2.5.exe"
!define MEDUSA_FOLDER "medusa-0.5.4"
!define REPORTLAB_FOLDER "reportlab"
!define MUTAGEN_FOLDER "mutagen-1.12"
!define SSL_FOLDER "ssl-1.13"
!define EMAIL_FOLDER "email-4.0.2"
!define TIFF_FOLDER "GnuWin32"
!define STUNNEL_FOLDER "Stunnel"
!define STUNNEL_CMD "stunnel-4.09.exe"
!define STUNNEL_VERSION "4"
!define LUCENE_FOLDER "Lucene"
!define LUCENE_JAR_FILE "lucene-core-2.3.1.jar"
!define GS_INSTALLER "gs861w32.exe"
!define XPDF_FOLDER "xpdf-3.02-patched"
!define HTML_FOLDER "htmldoc-1.8.27"
!define ENSCRIPT_INSTALLER "enscript-1.6.3-9-bin.exe"
!define OPENSSL_INSTALLER "Win32OpenSSL-0_9_8g.exe"
!define PYLUCENE_FOLDER "PyLucene-2.4.0-i386-win32-py2.5"
!define GRANT_EXE "Grant.exe"
!define UPLIB_ICON "UpLibMultiIcon1.ico"

; Files we expect to exist
!define DIR_USE_INSTALL_EXE "$PROGRAMFILES\Resource Kit\diruse.exe"
!define XPDF_INSTALL_FOLDER "$PROGRAMFILES\xpdf-3.02pl2-uplib"
!define TIFF_INSTALL_FOLDER "$PROGRAMFILES\GnuWin32"
!define LUCENE_INSTALL_JAR "$PROGRAMFILES\Lucene\lucene-core-2.3.1.jar"
!define STUNNEL_INSTALL_EXE "$PROGRAMFILES\Stunnel\stunnel-4.09.exe"

# Helper defines for UpLib
!define UPLIB_HOME "$PROGRAMFILES\UpLib"
!define UPLIB_BIN_FOLDER "${UPLIB_HOME}\bin"
!define UPLIB_SHARE "${UPLIB_HOME}\share"
!define UPLIB_LIB "${UPLIB_HOME}\lib"
!define UPLIB_REMOVE_GUARDIANS_CMD "${UPLIB_BIN_FOLDER}\removeAllUpLibGuardians.py"
!define UPLIB_INSTALL_ICON "${UPLIB_HOME}\share\images\${UPLIB_ICON}"

; MUI 1.67 compatible ------
!include "MUI.nsh"
!include "Library.nsh"
!verbose 3
!include "WinMessages.NSH"
!verbose 4

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON ${UPLIB_ICON}
!define MUI_UNICON ${UPLIB_ICON}

; Welcome page
!define MUI_WELCOMEPAGE_TEXT "This installs UpLib and all it's dependencies for Windows.\n\rYou will need to click through the installers for all the\n\rdependent software.\n\r\n\r\n\rNOTE: You should not need to reboot, though if you are having problems, rebooting may solve that."
!insertmacro MUI_PAGE_WELCOME
; License page
!insertmacro MUI_PAGE_LICENSE "${UPLIB_FOLDER}\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "The UpLib Repository Manager"
!define MUI_FINISHPAGE_RUN_FUNCTION RunAfter
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\share\doc\index.html"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_COMPONENTS
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language files
!insertmacro MUI_LANGUAGE "English"

; MUI end ------

Var PLEN
Var PYPATH
Var PYHOME
Var JVERSION
Var JAVAHOME
Var GRANT_OUT_FILE
Var WIN_CONFIG_FILE
Var GSHOME
Var GSPATH
Var ENSCRIPTPATH
Var HTMLPATH
Var OPENSSL_HOME
Var USER_DOMAIN
Var FQDN
Var FQDN_OUT_FILE
Var UNINSTALL_CMD
Var PDFCONVERTER_INSTALLED
Var ABXPATH


Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${OUTDIR}\UpLib-${PRODUCT_VERSION}-setup.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Function .onInit
  # Turn install logging on
  LogSet on

  IfFileExists "${DIR_USE_INSTALL_EXE}" DiruseFound 0
    MessageBox MB_OK "No Diruse found.  Expecting it to be here: ${DIR_USE_INSTALL_EXE}"
    Abort
  DiruseFound:

  ReadRegStr $JVERSION HKLM "SOFTWARE\JavaSoft\Java Runtime Environment" "CurrentVersion"
  StrCmp $JVERSION "" 0 HaveJava
    MessageBox MB_OK "Java is not installed.  You must install java first to run this installer."
    Abort
  HaveJava:

  ReadRegStr $JAVAHOME HKLM "SOFTWARE\JavaSoft\Java Runtime Environment\$JVERSION" "JavaHome"
  StrCmp $JAVAHOME "" 0 FoundJavaHome
    MessageBox MB_OK "Java $JVERSION does not exist.  Install Java $JVERSION and then reinstall UpLib."
    Abort
  FoundJavaHome:
  IfFileExists "$JAVAHOME\bin\java.exe" FoundJavaExe
    MessageBox MB_OK "The java command could not be found at: $JAVAHOME\bin\java.exe.  Reinstall Java and then reinstall UpLib."
    Abort
  FoundJavaExe:

  IfFileExists "$JAVAHOME\bin\keytool.exe" FoundKeytoolExe
    MessageBox MB_OK "The java keytool command could not be found at: $JAVAHOME\bin\keytool.exe.  Reinstall Java and then reinstall UpLib."
    Abort
  FoundKeytoolExe:
FunctionEnd

Section "Python" SEC_PYTHON
  SetOutPath "$TEMP"
  SetOverwrite on
  File "${PYTHON_INSTALLER}"
  ExecWait 'msiexec /package "$TEMP\${PYTHON_INSTALLER}" '
SectionEnd

Section -"GetPythonPath"
  ; This is supposed to give us the python executable path
  ReadRegStr $PYPATH HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Python.exe" ""
  StrLen $PLEN "Python.exe"
  ; Specifying a negative number to max len on StrCpy means that it truncates the string
  StrCpy $PYHOME $PYPATH -$PLEN
SectionEnd

SectionGroup "Python Extensions" SEC_PYTHON_EXTENSIONS

Section "PIL" SEC_PIL
  SetOutPath "$TEMP"
  SetOverwrite on
  File "${PIL_INSTALLER}"
  ExecWait "$TEMP\${PIL_INSTALLER}"
SectionEnd

Section "PyWin32" SEC_PYWIN32
  SetOutPath "$TEMP"
  SetOverwrite on
  File "${PYWIN_INSTALLER}"
  ExecWait "$TEMP\${PYWIN_INSTALLER}"
SectionEnd

Section "Report Lab" SEC_REPORTLAB
  SetOutPath "$PYHOME\Lib\site-packages\${REPORTLAB_FOLDER}"
  SetOverwrite on
  File /r "${REPORTLAB_FOLDER}\*"
SectionEnd

Section "Medusa" SEC_MEDUSA
  SetOutPath "$TEMP\${MEDUSA_FOLDER}"
  SetOverwrite on
  File /r "${MEDUSA_FOLDER}\*"
  ExecWait "$\"$PYPATH$\" setup.py install"
SectionEnd

Section "Email" SEC_EMAIL
  SetOutPath "$TEMP\${EMAIL_FOLDER}"
  SetOverwrite on
  File /r "${EMAIL_FOLDER}\*"
  ExecWait "$\"$PYPATH$\" setup.py install"
SectionEnd

Section "Mutagen" SEC_MUTAGEN
  SetOutPath "$TEMP\${MUTAGEN_FOLDER}"
  SetOverwrite on
  File /r "${MUTAGEN_FOLDER}\*"
  ExecWait "$\"$PYPATH$\" setup.py install"
SectionEnd

SectionGroupEnd ; Python Extensions

Section "PyLucene" SEC_PYLUCENE
  SetOutPath "$PYHOME\Lib\site-packages\lucene"
  SetOverwrite on
  File /r "${PYLUCENE_FOLDER}\*"
SectionEnd

Section "SSL" SEC_SSL
  SetOutPath "$PYHOME\Lib\site-packages\ssl"
  SetOverwrite on
  File /r "${SSL_FOLDER}\*"
SectionEnd

Section "Enscript" SEC_ENSCRIPT
  SetOutPath "$TEMP"
  SetOverwrite on
  File "${ENSCRIPT_INSTALLER}"
  ExecWait "$TEMP\${ENSCRIPT_INSTALLER}"
SectionEnd

Section "GhostScript" SEC_GHOSTSCRIPT
  SetOutPath "$TEMP"
  SetOverwrite on
  File "${GS_INSTALLER}"
  ExecWait "$TEMP\${GS_INSTALLER}"
  MessageBox MB_OK "You may optionally want to close the Explorer window with the Ghostscript icons before continuing."
SectionEnd

Section "OpenSSL" SEC_OPENSSL
  SetOutPath "$TEMP"
  SetOverwrite on
  File "${OPENSSL_INSTALLER}"
  ExecWait "$TEMP\${OPENSSL_INSTALLER}"
SectionEnd

Section "Htmldoc" SEC_HTMLDOC
  SetOutPath "$PROGRAMFILES\${HTML_FOLDER}"
  SetOverwrite on

  File /r "${HTML_FOLDER}\*"
  WriteRegExpandStr HKLM "SOFTWARE\Easy Software Products\HTMLDOC" "data" "$PROGRAMFILES\${HTML_FOLDER}"
  WriteRegExpandStr HKLM "SOFTWARE\Easy Software Products\HTMLDOC" "doc" "$PROGRAMFILES\${HTML_FOLDER}\doc"
  WriteRegExpandStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\htmldoc.exe" "" "$PROGRAMFILES\${HTML_FOLDER}\htmldoc.exe"
  WriteRegExpandStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\htmldoc.exe" "Path" "$PROGRAMFILES\${HTML_FOLDER}"
SectionEnd

Section "Libtiff" SEC_LIBTIFF
  SetOutPath "$PROGRAMFILES\${TIFF_FOLDER}"
  SetOverwrite on
  File /r "${TIFF_FOLDER}\*"
SectionEnd

Section "Stunnel" SEC_STUNNEL
  SetOutPath "$PROGRAMFILES\${STUNNEL_FOLDER}"
  SetOverwrite on
  File /r "${STUNNEL_FOLDER}\*"
SectionEnd

Section "Lucene" SEC_LUCENE
  SetOutPath "$PROGRAMFILES\${LUCENE_FOLDER}"
  SetOverwrite on
  File /r "${LUCENE_FOLDER}\*"
SectionEnd

Section "Xpdf" SEC_XPDF
  SetOutPath "${XPDF_INSTALL_FOLDER}"
  SetOverwrite on
  File /r "${XPDF_FOLDER}\*"
SectionEnd

Section "PDF Converter" SEC_PDFCONVERTER
  IfFileExists "${PDFCONVERTER_INSTALL_DIR}\OLEPDFPrint.exe" 0 PdfConverterExists
    StrCpy $PDFCONVERTER_INSTALLED 1
  PdfConverterExists:

  SetOutPath "$TEMP\${ABXPDF_DIR}"
  SetOverwrite on
  File /r "${ABXPDF_DIR}\*"
  ClearErrors
  ExecWait "$TEMP\${ABXPDF_INSTALLER}"
  IfErrors ABXPDF_INSTALLED
  
  !insertmacro InstallLib REGDLL $PDFCONVERTER_INSTALLED REBOOT_NOTPROTECTED \
    "${PDFCONVERTER_DIR}\msvbvm60.dll" "$SYSDIR\msvbvm60.dll" "$SYSDIR"
  !insertmacro InstallLib REGDLL $PDFCONVERTER_INSTALLED REBOOT_PROTECTED \
    "${PDFCONVERTER_DIR}\oleaut32.dll" "$SYSDIR\oleaut32.dll" "$SYSDIR"
  !insertmacro InstallLib REGDLL $PDFCONVERTER_INSTALLED REBOOT_PROTECTED \
    "${PDFCONVERTER_DIR}\olepro32.dll" "$SYSDIR\olepro32.dll" "$SYSDIR"
  !insertmacro InstallLib REGDLL $PDFCONVERTER_INSTALLED REBOOT_PROTECTED \
    "${PDFCONVERTER_DIR}\comcat.dll"   "$SYSDIR\comcat.dll"   "$SYSDIR"
  !insertmacro InstallLib DLL    $PDFCONVERTER_INSTALLED REBOOT_PROTECTED \
    "${PDFCONVERTER_DIR}\asycfilt.dll" "$SYSDIR\asycfilt.dll" "$SYSDIR"
  !insertmacro InstallLib TLB    $PDFCONVERTER_INSTALLED REBOOT_PROTECTED \
    "${PDFCONVERTER_DIR}\stdole2.tlb"  "$SYSDIR\stdole2.tlb"  "$SYSDIR"

  SetOutPath "${PDFCONVERTER_INSTALL_DIR}"
  File "${PDFCONVERTER_DIR}\*.py"
  File "${PDFCONVERTER_DIR}\*.exe"

  ; This stops the existing PDF server if it exists
  ExpandEnvStrings $1 %COMSPEC%
  ExecWait '"$1" /C ""$PYPATH" "${PDFCONVERTER_INSTALL_DIR}\stopPDFService.py""'

  WriteRegStr HKCU "${ABXPDF_REGKEY}" "DefaultLocation" "${PDFCONVERTER_INSTALL_DIR}\Output"
  WriteRegStr HKCU "${ABXPDF_REGKEY}" "UseDefaultLocation" "1"
  WriteRegStr HKCU "${ABXPDF_REGKEY}" "UseJobName" "1"
  WriteRegStr HKCU "${ABXPDF_REGKEY}" "NoSaveAs" "1"

  ; This registers the ThreadTimer ActiveX component
  ExpandEnvStrings $1 %COMSPEC%
  ExecWait '"$1" /C ""${PDFCONVERTER_INSTALL_DIR}\ThreadTimer.exe" /register"'

  ; This installs the service
  ExecWait '"$1" /C ""$PYPATH" "${PDFCONVERTER_INSTALL_DIR}\PDFServiceInstaller.py""'

  ABXPDF_INSTALLED:
SectionEnd

Section -"UpLibPrereqCheck"
  ReadRegStr $HTMLPATH HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\htmldoc.exe" ""
  StrCmp $HTMLPATH "" 0 HaveHtmldoc
    MessageBox MB_OK "Htmldoc is not installed.  Install htmldoc before running this installer."
    Abort
  HaveHtmldoc:

  ReadRegStr $GSPATH HKLM "SOFTWARE\GPL Ghostscript\8.61" "GS_DLL"
  StrCmp $GSPATH "" 0 HaveGhostscript
    MessageBox MB_OK "Ghostscript is not installed.  Install ghostscript before running this installer."
    Abort
  HaveGhostscript:
  StrLen $PLEN "\bin\gsdll32.dll"
  StrCpy $GSHOME $GSPATH -$PLEN

  ReadRegStr $ENSCRIPTPATH HKLM "SOFTWARE\GnuWin32\Enscript\1.6.3\bin" "InstallPath"
  StrCmp $ENSCRIPTPATH "" 0 HaveEnscript
    MessageBox MB_OK "Enscript is not installed.  Install enscript before running this installer."
    Abort
  HaveEnscript:

  ReadRegStr $OPENSSL_HOME HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\OpenSSL_is1\" "InstallLocation"
  IfFileExists "$OPENSSL_HOME\bin\openssl.exe" HaveOpenSSL
    MessageBox MB_OK "OpenSSL was not installed.  Install OpenSSL before running this installer."
    Abort
  HaveOpenSSL:

  IfFileExists ${XPDF_INSTALL_FOLDER} XpdfFound 0
    MessageBox MB_OK "No xpdf found.  Expecting it to be here: ${XPDF_INSTALL_FOLDER}"
    Abort
  XpdfFound:

  IfFileExists ${TIFF_INSTALL_FOLDER} TiffFound 0
    MessageBox MB_OK "No Tiff found.  Expecting it to be here: ${TIFF_INSTALL_FOLDER}"
    Abort
  TiffFound:

  IfFileExists ${LUCENE_INSTALL_JAR} LuceneFound 0
    MessageBox MB_OK "No Lucene found.  Expecting it to be here: ${LUCENE_INSTALL_JAR}"
    Abort
  LuceneFound:

  IfFileExists ${STUNNEL_INSTALL_EXE} StunnelFound 0
    MessageBox MB_OK "No Stunnel found.  Expecting it to be here: ${STUNNEL_INSTALL_EXE}"
    Abort
  StunnelFound:
  
;  IfFileExists "${PDFCONVERTER_INSTALL_DIR}\OLEPDFPrint.exe" 0 PdfConverterExists
;    StrCpy $PDFCONVERTER_INSTALLED 1
;  PdfConverterExists:
  StrCpy $PDFCONVERTER_INSTALLED 1
SectionEnd

Section "Uplib" SEC_UPLIB
  SetOutPath "$TEMP"
  SetOverwrite on

  IfFileExists "$TEMP\${UPLIB_FOLDER}" 0 NoDeleteCached
    RMDir /r "$TEMP\${UPLIB_FOLDER}"
  NoDeleteCached:

  SetOutPath "$TEMP\${UPLIB_FOLDER}"
  File /r "${UPLIB_FOLDER}\*"

  SetOutPath "$TEMP"

  ClearErrors
  ; Check the PDFPrint variable to see if the server is setup
  ; Also get the FQDN from python so we can set the MDF url properly
  ExpandEnvStrings $1 %COMSPEC%
  ; Notice the quoting rules - the double quotes are nested - it must be this way!
  ClearErrors
  ExecWait '"$1" /C ""$PYPATH" -c "import socket; print(socket.getfqdn())" > "$TEMP\uplib-fqdn.out""'
  IfErrors Errfqdn
    ClearErrors
    FileOpen $FQDN_OUT_FILE "$TEMP\uplib-fqdn.out" "r"
    IfErrors Errfqdn
      FileRead $FQDN_OUT_FILE $FQDN
      FileClose $FQDN_OUT_FILE

      Push $FQDN
      Call TrimNewlines
      Pop $FQDN

      Goto Fqdnok
  Errfqdn:
    MessageBox MB_OK 'Could not obtain FQDN for setting up PDF Server.'
  Fqdnok:

  FileOpen $WIN_CONFIG_FILE "$TEMP\${UPLIB_FOLDER}\windows.config" "w"
  FileWrite $WIN_CONFIG_FILE "ENSCRIPT=$ENSCRIPTPATH\bin\enscript.exe$\r$\n"
  FileWrite $WIN_CONFIG_FILE "FILE=$\r$\n"
  FileWrite $WIN_CONFIG_FILE "DIRUSE=${DIR_USE_INSTALL_EXE}$\r$\n"
  FileWrite $WIN_CONFIG_FILE "GHOSTSCRIPTHOME=$GSHOME$\r$\n"
  FileWrite $WIN_CONFIG_FILE "HTMLDOC=$HTMLPATH$\r$\n"
  FileWrite $WIN_CONFIG_FILE "LUCENEJAR=$PROGRAMFILES\${LUCENE_FOLDER}\${LUCENE_JAR_FILE}$\r$\n"
  FileWrite $WIN_CONFIG_FILE "PDFTOTEXT=${XPDF_INSTALL_FOLDER}\pdftotext.exe$\r$\n"
  FileWrite $WIN_CONFIG_FILE "PDFLINKS=${XPDF_INSTALL_FOLDER}\pdflinks.exe$\r$\n"
  FileWrite $WIN_CONFIG_FILE "WORDBOXES_PDFTOTEXT=${XPDF_INSTALL_FOLDER}\pdftotext.exe$\r$\n"
  FileWrite $WIN_CONFIG_FILE "PDFINFO=${XPDF_INSTALL_FOLDER}\pdfinfo.exe$\r$\n"
  FileWrite $WIN_CONFIG_FILE "PYTHON=$PYPATH$\r$\n"
  FileWrite $WIN_CONFIG_FILE "TIFFHOME=$PROGRAMFILES\${TIFF_FOLDER}$\r$\n"
  FileWrite $WIN_CONFIG_FILE "UPLIB_HOME=${UPLIB_HOME}$\r$\n"
  FileWrite $WIN_CONFIG_FILE "SPLITUP=${UPLIB_HOME}\bin\splitup.exe$\r$\n"
  FileWrite $WIN_CONFIG_FILE "STUNNEL=${STUNNEL_INSTALL_EXE}$\r$\n"
  FileWrite $WIN_CONFIG_FILE "STUNNEL_VERSION=4$\r$\n"
  FileWrite $WIN_CONFIG_FILE "OPENSSL=$OPENSSL_HOME\bin\openssl.exe$\r$\n"
  FileWrite $WIN_CONFIG_FILE "USE_PYLUCENE=jcc$\r$\n"
  FileWrite $WIN_CONFIG_FILE "USE_STUNNEL=false$\r$\n"
  FileWrite $WIN_CONFIG_FILE "USE_OPENOFFICE_FOR_WEB=false$\r$\n"
  FileWrite $WIN_CONFIG_FILE "USE_OPENOFFICE_FOR_MSOFFICE=false$\r$\n"

  StrCmp $PDFCONVERTER_INSTALLED "" nopdfconverter
    FileWrite $WIN_CONFIG_FILE "MS_TO_PDF_SERVER_URL=http://$FQDN:10880/pdf$\r$\n"
    FileWrite $WIN_CONFIG_FILE "MS_OCR_URL=http://$FQDN:10880/ocr$\r$\n"
  nopdfconverter:

  FileClose $WIN_CONFIG_FILE

  ; Now configure and install the UpLib files
  ; Setting the output path has the side effect of setting the working directory
  ExpandEnvStrings $1 %COMSPEC%
  SetOutPath "$TEMP\${UPLIB_FOLDER}"
  ExecWait '"$1" /C ""$PYPATH" win32\configure-target.py "${UPLIB_HOME}" ${UPLIB_VERSION}"'

  ; Copy the README to README.txt so it will open correctly
  CopyFiles "$TEMP\${UPLIB_FOLDER}\README" "$INSTDIR\README.txt"

  ; Grant logon as a service right for the current user
  File ${GRANT_EXE}

  ClearErrors
  ExpandEnvStrings $1 %COMSPEC%
  ; Note that we invoke with the command shell like this so Python gets the correct environment
  ; Notice also the quoting rules - the double quotes are nested - it must be this way!
  ExecWait '"$1" /C ""$PYPATH" -c "import win32api; print(win32api.GetUserNameEx(win32api.NameSamCompatible))" > "$TEMP\uplib-grant.out""'
  IfErrors Errread
    FileOpen $GRANT_OUT_FILE "$TEMP\uplib-grant.out" "r"
    IfErrors Errread
      FileRead $GRANT_OUT_FILE $USER_DOMAIN
      FileClose $GRANT_OUT_FILE

      Push $USER_DOMAIN
      Call TrimNewlines
      Pop $USER_DOMAIN

      ClearErrors
      ExecWait '"$TEMP\${UPLIB_FOLDER}\${GRANT_EXE}" add SeServiceLogonRight $USER_DOMAIN'
      Goto Grantok
  Errread:
    ; Get rid of this printout - since it seems to happen sometimes for no good reason
    ; MessageBox MB_OK 'Could not obtain domain\user name for granting "Logon as a Service" right - user is $USER_DOMAIN.'
  Grantok:
SectionEnd

Section -Shortcuts
  # Remove existing shorcuts
  SetShellVarContext all
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"

  # Install new shortcuts
  ; Setting the output path has the side effect of setting the working directory
  ExpandEnvStrings $1 %COMSPEC%
  SetShellVarContext current
  SetOutPath "$TEMP\${UPLIB_FOLDER}\win32"
  ; Notice also the quoting rules - the double quotes are nested - it must be this way!
  ExecWait '"$1" /C ""$PYPATH" createWinShortcuts.py"'

  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
SectionEnd

Section -Post
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\UpLib.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\share\images\UpLibMultiIcon1.ico"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd


#####################
# Uninstaller Section
#####################

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort

  # This is supposed to give us the python executable path
  ReadRegStr $PYPATH HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Python.exe" ""
  StrLen $PLEN "Python.exe"
  # Specifying a negative number to max len on StrCpy means that it truncates the string
  StrCpy $PYHOME $PYPATH -$PLEN
FunctionEnd

Section "un.UpLib" SEC_UN_UPLIB
  # Remove running guardians
  ExecWait "$\"$PYPATH$\" $\"${UPLIB_REMOVE_GUARDIANS_CMD}$\""

  # Remove the UpLib directory
  RMDir /r $INSTDIR

  # Remove Shortcuts from Start Menu
  SetShellVarContext current
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"

  # Remove pointers to repositories
  RMDir /r "$DOCUMENTS\Application Data\UpLib-config"

  # Remove the
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd

Section "un.PDF Converter" SEC_UN_PDFCONVERTER
  ; This removes the service
  ExpandEnvStrings $1 %COMSPEC%
  ExecWait '"$1" /C ""$PYPATH" "${PDFCONVERTER_INSTALL_DIR}\removePDFService.py""'

  ExecWait '"$1" /C ""$INSTDIR\ThreadTimer.exe" /unregserver"'
  ReadRegStr $ABXPATH HKLM "SOFTWARE\ABXPDF Writer" "Destination Folder"
  ExecWait '"$SYSDIR\uninstpw.exe" $ABXPATH'

  RMDir /r "${PDFCONVERTER_INSTALL_DIR}"
SectionEnd

Section "un.Xpdf" SEC_UN_XPDF
  RMDir /r "$PROGRAMFILES\${XPDF_INSTALL_FOLDER}"
SectionEnd

Section "un.Lucene" SEC_UN_LUCENE
  RMDir /r "$PROGRAMFILES\${LUCENE_FOLDER}"
SectionEnd

Section "un.Stunnel" SEC_UN_STUNNEL
  RMDir /r "$PROGRAMFILES\${STUNNEL_FOLDER}"
SectionEnd

Section "un.Libtiff" SEC_UN_LIBTIFF
  # RMDir /r "$PROGRAMFILES\${TIFF_FOLDER}"
SectionEnd

Section "un.Htmldoc" SEC_UN_HTMLDOC
  RMDir /r "$PROGRAMFILES\${HTML_FOLDER}"
  DeleteRegKey HKLM "SOFTWARE\Easy Software Products\HTMLDOC"
  DeleteRegKey HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\htmldoc.exe"
SectionEnd

Section "un.OpenSSL" SEC_UN_OPENSSL
  ReadRegStr $UNINSTALL_CMD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSSL_is1" "UninstallString"
  ExecWait "$UNINSTALL_CMD"
SectionEnd

Section "un.GhostScript" SEC_UN_GHOSTSCRIPT
  ReadRegStr $UNINSTALL_CMD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GPL Ghostscript 8.61" "UninstallString"
  ExecWait "$UNINSTALL_CMD"
SectionEnd

Section "un.Enscript" SEC_UN_ENSCRIPT
  ReadRegStr $UNINSTALL_CMD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Enscript-1.6.3-bin_is1" "UninstallString"
  ExecWait "$UNINSTALL_CMD"
SectionEnd

Section "un.PyLucene" SEC_UN_PYLUCENE
  RMDir /r "$PYHOME\Lib\site-packages\${PYLUCENE_FOLDER}"
SectionEnd

Section "un.SSL" SEC_UN_SSL
  RMDir /r "$PYHOME\Lib\site-packages\ssl"
SectionEnd

Section "un.Mutagen" SEC_UN_MUTAGEN
  RMDir /r "$PYHOME\Lib\site-packages\mutagen"
SectionEnd

Section "un.Email" SEC_UN_EMAIL
  RMDir /r "$PYHOME\Lib\site-packages\email-4.0.2-py2.5.egg"
SectionEnd

Section "un.Medusa" SEC_UN_MEDUSA
  RMDir /r "$PYHOME\Lib\site-packages\medusa"
SectionEnd

Section "un.Report Lab" SEC_UN_REPORTLAB
  RMDir /r "$PYHOME\Lib\site-packages\${REPORTLAB_FOLDER}"
SectionEnd

Section "un.PyWin32" SEC_UN_PYWIN32
  ReadRegStr $UNINSTALL_CMD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pywin32-py2.5" "UninstallString"
  ExecWait "$UNINSTALL_CMD"
SectionEnd

Section "un.PIL" SEC_UN_PIL
  ReadRegStr $UNINSTALL_CMD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PIL-py2.5" "UninstallString"
  ExecWait "$UNINSTALL_CMD"
SectionEnd

Section "un.Python" SEC_UN_PYTHON
  ReadRegStr $UNINSTALL_CMD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\{75E71ADD-042C-4F30-BFAC-A9EC42351313}" "UninstallString"
  ExecWait "$UNINSTALL_CMD"
SectionEnd


######################
# Section descriptions
######################

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  # Install Components
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_PYTHON} "The Python Runtime and Associated Libraries (version 2.5)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_PYTHON_EXTENSIONS} "Python Extensions to handle imaging, windows services, pdfs, servers, email, and song formats"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_PIL} "The Python Imaging Library"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_PYWIN32} "Python for Windows Extensions"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_REPORTLAB} "A tool with automated methods for generating Portable Document Format (PDF) files"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MEDUSA} "An architecture for building long-running, high-performance network servers in Python"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_EMAIL} "A Python package for parsing email"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MUTAGEN} "A Python package for parsing popular song formats"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_PYLUCENE} "A utility for performing Lucene operations in Python"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_SSL} "TLS bindings for Python"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_ENSCRIPT} "Enscript converts ASCII files to PostScript"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_GHOSTSCRIPT} "An interpreter for the PostScript (TM) language"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_OPENSSL} "An open-source implementation of the Secure Sockets Layer protocol"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_HTMLDOC} "The HTMLDOC program for importing html documents"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_LIBTIFF} "The TIFF library for manipulating TIFF files"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_STUNNEL} "The Stunnel program for SSL support"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_LUCENE} "Lucene for full text indexing"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_XPDF} "Xpdf for PDF conversions"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_PDFCONVERTER} "A utility for converting Word/Excel/Powerpoint files to PDF"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UPLIB} "An implementation of a personal document repository system"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

!insertmacro MUI_UNFUNCTION_DESCRIPTION_BEGIN
  # Uninstall components
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_UPLIB} "An implementation of a personal document repository system"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_PDFCONVERTER} "A utility for converting Word/Excel/Powerpoint files to PDF"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_XPDF} "Xpdf for PDF conversions"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_LUCENE} "Lucene for full text indexing"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_STUNNEL} "The Stunnel program for SSL support"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_LIBTIFF} "The TIFF library for manipulating TIFF files"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_HTMLDOC} "The HTMLDOC program for importing html documents"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_OPENSSL} "An open-source implementation of the Secure Sockets Layer protocol"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_GHOSTSCRIPT} "An interpreter for the PostScript (TM) language"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_ENSCRIPT} "Enscript converts ASCII files to PostScript"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_SSL} "TLS bindings for Python"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_MUTAGEN} "A Python package for parsing popular song formats"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_EMAIL} "A Python package for parsing email"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_MEDUSA} "An architecture for building long-running, high-performance network servers in Python"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_REPORTLAB} "A tool with automated methods for generating Portable Document Format (PDF) files"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_PYWIN32} "Python for Windows Extensions"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_PIL} "The Python Imaging Library foo"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_UN_PYTHON} "The Python Runtime and Associated Libraries (version 2.5)"
!insertmacro MUI_UNFUNCTION_DESCRIPTION_END

##################
# Helper functions
##################

; A function that removes newline characters
Function TrimNewlines
  Exch $R0
  Push $R1
  Push $R2
  StrCpy $R1 0

loop:
  IntOp $R1 $R1 - 1
  StrCpy $R2 $R0 1 $R1
  StrCmp $R2 "$\r" loop
  StrCmp $R2 "$\n" loop

  IntOp $R1 $R1 + 1
  IntCmp $R1 0 no_trim_needed
  StrCpy $R0 $R0 $R1

no_trim_needed:
  Pop $R2
  Pop $R1
  Exch $R0
FunctionEnd

Function RunAfter
  Exec "$JAVAHOME/bin/javaw.exe -Dcom.parc.uplib.libdir=$\"${UPLIB_LIB}$\" -jar $\"${UPLIB_SHARE}\code\UpLibJanitor.jar$\""
FunctionEnd