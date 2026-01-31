@echo off
echo Installing PyInstaller...
pip install pyinstaller

echo Building CacheWarmer...
rmdir /s /q build dist
pyinstaller --noconfirm --onefile --windowed --name "CacheWarmer" --icon="cloud.ico" --hidden-import=PIL._tkinter_finder --hidden-import=pystray --add-data "services;services" ui.py

echo Build complete! Check 'dist' folder.
pause
