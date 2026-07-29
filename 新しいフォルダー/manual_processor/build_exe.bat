@echo off
echo ===================================================
echo  Manual and Business Document Processor
echo  EXE Build Script
echo ===================================================
echo.

echo 1. Installing requirements and PyInstaller...
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo 2. Building Single-File EXE with PyInstaller...
python -m PyInstaller --noconsole --onefile --name "DocumentProcessor" --collect-all google.genai --collect-all google.cloud.vision --hidden-import PIL --hidden-import fitz --hidden-import docx --hidden-import fpdf --hidden-import gtts --clean main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo  SUCCESS! 
    echo  Single executable file created in 'dist' folder: DocumentProcessor.exe
    echo ===================================================
) else (
    echo.
    echo  ERROR occurred during build. Please check the logs.
)

pause
