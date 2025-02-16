@echo off
echo Installing dependencies globally...
pip install --upgrade pip
pip install opencv-python PyQt6 ffmpeg-python numpy
echo Installation complete. You can now run the app using run_without_venv.bat.
pause
