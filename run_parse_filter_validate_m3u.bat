@echo off
REM run_parse_filter_validate_m3u.bat
SETLOCAL ENABLEDELAYEDEXPANSION

echo ==============================================
echo  parse_filter_validate_m3u - Windows launcher
echo  Ctrl+C will trigger a graceful save
echo ==============================================
echo.

REM Detect Python
where python >nul 2>&1
IF ERRORLEVEL 1 (
  echo [ERROR] Python not found in PATH.
  echo Install Python 3.9+ and retry.
  pause
  exit /b 1
)

REM Optional interactive filters
set /p LANGS=Enter languages (space-separated, e.g. "fr en") or leave blank: 
set /p COUNTRIES=Enter countries (space-separated, e.g. "CA FR") or leave blank: 
set /p CATEGORIES=Enter categories (space-separated, e.g. "News Sport") or leave blank: 

echo.
echo Processing... (press Ctrl+C to abort)
echo.

python parse_filter_validate_m3u.py --lang %LANGS% --country %COUNTRIES% --category %CATEGORIES%

echo.
echo Finished. Outputs:
echo   filtered_valid_m3u.csv
echo   filtered_out.csv
echo   final_playlist.m3u
echo   log_parse_filter_validate_m3u.txt
echo.
pause
