@echo off
setlocal
cd /d "%~dp0.."

:MENU
cls
echo For Windows 10 and 11, this will compress the VapourSynth and Tools folders
echo to save about 60 percent of of space.
echo.
echo Press 1 to continue.
echo Press 2 to exit.
echo.
set /p choice="Enter selection: "

if "%choice%"=="1" goto RUN
if "%choice%"=="2" goto EOF

echo Invalid selection.
pause
goto MENU

:RUN
cls
REM Check if Python exists before trying to run it
if not exist "VapourSynth\python.exe" (
    echo Error: Could not find VapourSynth\python.exe
    pause
    goto EOF
)

if not exist "tools\compress-folders.py" (
    echo Error: Could not find tools\compress-folders.py
    pause
    goto EOF
)

"VapourSynth\python.exe" "tools\compress-folders.py"
pause
goto EOF

:EOF
endlocal