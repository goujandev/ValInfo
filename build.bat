@echo off
cd /d "%~dp0"
echo Building ValInfo.exe...
python -m pip install --quiet pyinstaller
python tools\make_icon.py
python -m PyInstaller --onefile --windowed --clean --noconfirm --name ValInfo --icon assets\valinfo.ico --add-data "assets\valinfo.ico;assets" main.py
echo.
echo Done: dist\ValInfo.exe
pause
