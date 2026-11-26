@echo off
setlocal
set "K2_SYNC_PYTHON=D:\Build\3D Prints\.venv\Scripts\python.exe"
if not exist "%K2_SYNC_PYTHON%" (
    echo The K2 sync utility could not find its Python interpreter.
    pause
    exit /b 1
)
"%K2_SYNC_PYTHON%" "%~dp0sync_k2_cfs.py" --open %*
if errorlevel 1 (
    pause
    exit /b 1
)
