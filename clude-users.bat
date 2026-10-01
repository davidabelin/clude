@echo off
setlocal ENABLEEXTENSIONS
setlocal EnableDelayedExpansion

set "%CLUDE_DIR%=C:\Users\David\Documents\Local_Python\clude"
set "%PYTHON%=%CLUDE_DIR%\.venv\Scripts\python.exe"
set "%CLI%=%CLUDE_DIR%\scripts\clude_cli.py"
set "%URI%=gs://clude-game-data/llm"


%PYTHON% %CLI% users %~1% --uri %URI%