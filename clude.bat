@echo off
rem clude.bat -- run the clude maintainer CLI (scripts\clude_cli.py) from anywhere.
rem
rem   clude agents                      any command, exactly as clude_cli.py takes it
rem   clude users list                  ...against gs://clude-game-data/llm
rem   clude users list --uri data/llm   override the default with a local store
rem   clude live users add zenbot       "live" first: against the deployed service's
rem   clude live tables list            store, gs://clude-game-data/llm
rem   clude play --help                 every command has --help
rem
rem "live" adds --uri at the end, so use it only with commands that take
rem --uri: users, tables, logbook and store.
rem Those commands default to the live store unless --uri is supplied.

setlocal EnableExtensions

set "CLUDE_DIR=%~dp0"
set "CLUDE_DIR=%CLUDE_DIR:~0,-1%"
set "PYTHON=%CLUDE_DIR%\.venv\Scripts\python.exe"
set "CLI=%CLUDE_DIR%\scripts\clude_cli.py"
set "LIVE_URI=gs://clude-game-data/llm"

if not exist "%PYTHON%" (
    echo clude: no venv interpreter at "%PYTHON%" 1>&2
    exit /b 1
)

rem The CLI's default stores (data, data\llm) are relative paths, so run
rem from the repo whatever folder this was called from.
pushd "%CLUDE_DIR%"

if /i "%~1"=="live" goto live
if /i "%~1"=="users" goto default_store
if /i "%~1"=="tables" goto default_store
if /i "%~1"=="logbook" goto default_store
if /i "%~1"=="store" goto default_store

"%PYTHON%" "%CLI%" %*
set "CODE=%ERRORLEVEL%"
goto done

:default_store
set "ARGS=%*"
:scan_uri
if "%~1"=="" goto run_default_store
set "ARG=%~1"
if /i "%ARG%"=="--uri" goto run_explicit_store
if /i "%ARG:~0,6%"=="--uri=" goto run_explicit_store
shift
goto scan_uri
:run_default_store
"%PYTHON%" "%CLI%" %ARGS% --uri "%LIVE_URI%"
set "CODE=%ERRORLEVEL%"
goto done
:run_explicit_store
"%PYTHON%" "%CLI%" %ARGS%
set "CODE=%ERRORLEVEL%"
goto done

:live
rem Everything after "live", then the bucket's --uri.
set "ARGS="
:collect
shift
if "%~1"=="" goto run_live
set ARGS=%ARGS% %1
goto collect
:run_live
if not defined ARGS (
    echo clude: "live" needs a command, e.g. clude live users list 1>&2
    set "CODE=2"
    goto done
)
"%PYTHON%" "%CLI%"%ARGS% --uri %LIVE_URI%
set "CODE=%ERRORLEVEL%"

:done
popd
exit /b %CODE%
