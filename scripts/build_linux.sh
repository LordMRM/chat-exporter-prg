#!/bin/bash
# Builds the Linux program (one executable file).
# Run from the project root with the virtual environment active:
#   bash scripts/build_linux.sh

set -e  # stop at the first error

pyinstaller --noconfirm --onefile --name chat-exporter-prg \
--paths src \
--add-data "src/chat_exporter/assets:chat_exporter/assets" \
--collect-all playwright \
run_app.py

echo "Done: dist/chat-exporter-prg"