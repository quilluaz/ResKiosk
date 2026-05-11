' ResKiosk Hub — Background Launcher
' Script lives in TO RUN; project root = parent of TO RUN.
' Launches python.exe as a hidden process (no console window).
' The hub continues running even after any terminal is closed.

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Working directory = project root (parent of this script's folder)
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strProjectRoot = objFSO.GetParentFolderName(strScriptDir)
objShell.CurrentDirectory = strProjectRoot

' Launch python.exe hidden (0 = hidden window, False = don't wait)
objShell.Run "cmd /c venv\Scripts\python.exe -m hub.launcher > hub.log 2>&1", 0, False
