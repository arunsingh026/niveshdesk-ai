Set WshShell = CreateObject("WScript.Shell")
desktopPath = WshShell.SpecialFolders("Desktop")
Set shortcut = WshShell.CreateShortcut(desktopPath & "\Arun's Stock Planner.url")
shortcut.TargetPath = "http://localhost:5173"
shortcut.IconLocation = "%SystemRoot%\System32\imageres.dll,93"
shortcut.Save
MsgBox "Desktop shortcut created successfully!", vbInformation, "Stock Planner"
