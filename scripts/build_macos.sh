#!/bin/bash
# Builds the macOS program.
# Run from the project root with the virtual environment active:
#   bash scripts/build_macos.sh

set -e  # stop at the first error

pyinstaller --noconfirm --windowed --name chat-exporter-prg \
  --paths src \
  --add-data "src/chat_exporter/assets:chat_exporter/assets" \
  --collect-all playwright \
  --icon "src/chat_exporter/assets/icon.icns" \
  run_app.py

echo "Done: dist/chat-exporter-prg.app"