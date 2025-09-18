@echo off
SET PYTHONPATH=%PYTHONPATH%;%~dp0..
cd %~dp0..
streamlit run app.py