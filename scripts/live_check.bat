@echo off
REM Check a deploy of clude by playing a table on the service
REM (docs/web.md, "Checking a deploy with a game"; Phase 8.2d).
REM
REM Usage, from any directory:
REM   scripts\live_check.bat play     a four-seat game with two throwaway
REM                                   accounts to the end, then the replay
REM   scripts\live_check.bat start    a second table left three answers in;
REM                                   prints its TABLE id
REM   scripts\live_check.bat resume TABLE_ID
REM                                   after scripts\deploy.bat: the cold
REM                                   rebuild of that table, timed, then
REM                                   played to the end
REM   scripts\live_check.bat cleanup  remove the two throwaway accounts
REM
REM The accounts t8a and t8b are created on `play` and `start` if missing
REM (a second `users add` is a harmless error) and removed by `cleanup`.
REM Every request kind's timings are printed at the end of each phase;
REM the numbers belong in docs/web.md under "Deploying".

setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
set URL=https://clude-648214345192.us-central1.run.app
set STORE=gs://clude-game-data/llm

if "%~1"=="" goto usage
if /I "%~1"=="play" goto accounts
if /I "%~1"=="start" goto accounts
if /I "%~1"=="resume" goto resume
if /I "%~1"=="cleanup" goto cleanup
goto usage

:accounts
"%PY%" "%ROOT%\scripts\clude_cli.py" users add t8a --uri %STORE%
"%PY%" "%ROOT%\scripts\clude_cli.py" users add t8b --uri %STORE%
"%PY%" "%ROOT%\scripts\clude_live_check.py" %URL% %1 t8a t8b
exit /b %ERRORLEVEL%

:resume
if "%~2"=="" goto usage
"%PY%" "%ROOT%\scripts\clude_live_check.py" %URL% resume t8a t8b %2
exit /b %ERRORLEVEL%

:cleanup
"%PY%" "%ROOT%\scripts\clude_cli.py" users remove t8a --uri %STORE%
"%PY%" "%ROOT%\scripts\clude_cli.py" users remove t8b --uri %STORE%
exit /b 0

:usage
echo usage: live_check.bat play ^| start ^| resume TABLE_ID ^| cleanup
exit /b 2
