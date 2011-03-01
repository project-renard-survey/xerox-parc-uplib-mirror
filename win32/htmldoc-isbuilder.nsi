OutFile "Setup.exe"
SilentInstall silent

Section "Htmldoc" SEC01
  SetOutPath "$TEMP"
  SetOverwrite on

  File /r "Media\Internet\Disk Images\disk1"
  ExecWait "$TEMP\disk1\SETUP.EXE"
SectionEnd

