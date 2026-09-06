$WshShell = New-Object -ComObject WScript.Shell
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktopPath\Arun's Stock Planner.lnk"

$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "http://localhost:5173"
$shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,93"
$shortcut.Description = "Arun's Personal Stock Investment Planner"
$shortcut.Save()

Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "Location: $shortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "To pin to taskbar:" -ForegroundColor Yellow
Write-Host "  1. Right-click the desktop shortcut" -ForegroundColor White
Write-Host "  2. Click Pin to taskbar" -ForegroundColor White
