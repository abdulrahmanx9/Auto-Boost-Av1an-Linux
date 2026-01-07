@echo off
setlocal

:: --- CONFIGURATION ---

:: 1. Define the path to the portable Python executable
:: We go up one level (..) from extras\ to find the VapourSynth folder
set "PYTHON_EXE=%~dp0..\VapourSynth\python.exe"

:: 2. Define the path to the Python script
:: We go up one level (..) from extras\ to find the tools folder
set "SCRIPT_PATH=%~dp0..\tools\lossless-intermediary.py"

:: --- CHECKS ---

:: Check if the portable Python exists
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Could not find portable Python.
    echo Expected location: "%PYTHON_EXE%"
    pause
    exit /b 1
)

:: Check if the Python script exists
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] Could not find Python script.
    echo Expected location: "%SCRIPT_PATH%"
    pause
    exit /b 1
)

:: --- EXECUTION ---

echo Launching Python script...
echo Python: "%PYTHON_EXE%"
echo Script: "%SCRIPT_PATH%"
echo.

:: Run the script using the portable python
"%PYTHON_EXE%" "%SCRIPT_PATH%"

echo.
del *.ffindex
del *.vpy
pause