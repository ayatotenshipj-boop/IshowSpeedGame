@echo off
REM Build do SpeedVsLabubu.exe no Windows (PyInstaller, arquivo unico).
REM Requer Python 3.11+ no PATH.

py -m venv .build-venv
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install pyinstaller pygame-ce pygame-gui pillow
pyinstaller --noconfirm SpeedVsLabubu.spec

echo.
echo Pronto. Executavel em: dist\SpeedVsLabubu.exe
pause
