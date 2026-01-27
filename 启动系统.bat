@echo off
REM ============================================================
REM AI股票分析系统启动脚本（Windows）
REM 使用本地虚拟环境优先，等价于执行：python run.py
REM ============================================================

setlocal

set "VENV_PATH=%~dp0venv"
set "PYTHON_EXE=%VENV_PATH%\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" run.py
) else (
    python run.py
)

pause
