# Builds the single-file Windows program.
# Run from the project root with the virtual environment active:
#   .\scripts\build_windows.ps1

$ErrorActionPreference = "Stop"  # stop at the first error

pyinstaller --noconfirm --onefile --windowed --name chat-exporter-prg `
  --paths src `
  --add-data "src\chat_exporter\assets;chat_exporter\assets" `
  --collect-all playwright `
  run_app.py

Write-Host "Done: dist\chat-exporter-prg.exe"