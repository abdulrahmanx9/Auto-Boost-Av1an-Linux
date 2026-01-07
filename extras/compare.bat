@echo off
setlocal

:: 1. Navigate to the current folder (compare)
cd /d "%~dp0"

:: 2. Set Relative Paths
::    Tools are one level up in the "VapourSynth" folder
set "PYTHON_EXE=..\VapourSynth\python.exe"
set "COMP_SCRIPT=..\VapourSynth\comp.py"

:: 3. Run the Python script
::    (No arguments passed; comp.py will detect MKVs in the current dir)
echo Launching comparison script...
"%PYTHON_EXE%" "%COMP_SCRIPT%"
echo: comp.py done
pause

:: 4. Cleanup steps
echo Cleaning up folder...

:: Execute cleanup commands
if exist "generated*" del "generated*"
if exist "*.lwi" del "*.lwi"
if exist "Comparisons" rmdir /s /q "Comparisons"
if exist "screens" rmdir /s /q "screens"

echo Cleanup finished.