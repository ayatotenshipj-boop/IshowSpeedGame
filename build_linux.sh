#!/usr/bin/env bash
# Build do executável Linux do SpeedVsLabubu (PyInstaller, arquivo único).
set -e
cd "$(dirname "$0")"

python -m venv .build-venv
./.build-venv/bin/python -m pip install --upgrade pip
./.build-venv/bin/pip install pyinstaller pygame-ce pygame-gui pillow
./.build-venv/bin/pyinstaller --noconfirm SpeedVsLabubu.spec

echo
echo "Pronto. Executável em: dist/SpeedVsLabubu"
