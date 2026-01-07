@echo off
setlocal
echo Warning: this will blindly encode all audio tracks to opus. Do not re-encode lossy audio, this
echo leads to generational-loss which ultimately lowers quality that was already lowered. It's not
echo worth saving a few megabytes. Only encode lossless audio (such a flac/pcm/TrueHD/DTS-HD) to opus.
pause
REM ============================================================
REM Setup Portable Paths
REM We assume this BAT is usually in \extras\
REM We need to find \VapourSynth\python.exe and \tools\opus.py
REM ============================================================

REM Get the directory where this BAT file is *originally* located
REM If you copy this BAT elsewhere, %~dp0 still points to the portable folder
REM ONLY if you run it from there. 

REM If you move the BAT file to your video folder, you must hardcode the root path below.
REM RECOMMENDATION: Leave the BAT in 'extras', and drag your video folder onto this BAT,
REM or copy the BAT and update "PORTABLE_ROOT" below.

REM Attempt to auto-detect root if the BAT is inside 'extras':
SET "PORTABLE_ROOT=%~dp0.."

REM Define Tools
SET "PYTHON_EXE=%PORTABLE_ROOT%\VapourSynth\python.exe"
SET "OPUS_SCRIPT=%PORTABLE_ROOT%\tools\opus.py"

REM Check if tools exist
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Could not find Python at:
    echo %PYTHON_EXE%
    echo.
    echo Please make sure the 'Auto-Boost-Essential' folder structure is intact.
    pause
    exit /b
)

if not exist "%OPUS_SCRIPT%" (
    echo [ERROR] Could not find opus.py at:
    echo %OPUS_SCRIPT%
    pause
    exit /b
)

REM ============================================================
REM Execution
REM ============================================================

echo Starting Opus Audio Workflow...
echo.

"%PYTHON_EXE%" "%OPUS_SCRIPT%"

echo.
echo Workflow finished.
del *.flac
del *.ac3
del *.thd
del *.dtshd
del *.opus
pause