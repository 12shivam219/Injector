@echo off
REM Validate encryption keys before starting the app
python scripts\validate_keys.py
IF %ERRORLEVEL% NEQ 0 (
  echo Fix the encryption keys above before starting the app.
  exit /b %ERRORLEVEL%
)

REM Ensure repository root is current directory
cd /d %~dp0..

REM Test database connectivity before starting the app
echo Testing database connectivity...
python scripts\setup_database.py --test
IF %ERRORLEVEL% NEQ 0 (
  echo Database connectivity test failed. If this is a fresh setup, run: python scripts\setup_database.py --all
  exit /b %ERRORLEVEL%
)

REM Start Streamlit
streamlit run app.py