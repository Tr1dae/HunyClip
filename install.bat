@echo off
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install opencv-python PyQt6 ffmpeg-python numpy
@echo Installation complete. Run run.bat to start the app.
