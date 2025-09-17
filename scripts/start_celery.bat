@echo off
echo 🚀 Starting Celery Worker for Resume Processing...
echo.
echo Make sure this window stays open while using async processing in the Streamlit app.
echo Press Ctrl+C to stop the worker.
echo.
python start_celery_worker.py
pause
