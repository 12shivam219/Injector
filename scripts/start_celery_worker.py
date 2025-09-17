#!/usr/bin/env python3
"""
Script to start Celery worker for processing resume tasks.
Run this in a separate terminal/command prompt while your Streamlit app is running.
"""

import os
import sys
import subprocess

def start_celery_worker():
    """Start Celery worker with appropriate configuration."""
    print("🚀 Starting Celery worker for resume processing...")
    
    try:
        # Import to test configuration
from config.celeryconfig import celery_app
        print(f"📡 Using broker: {CELERY_BROKER_URL}")
        
        # Start worker with appropriate settings for Windows
        worker_args = [
            sys.executable, "-m", "celery",
            "--app=celeryconfig:celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=2",  # Limit concurrency for stability
            "--pool=solo" if os.name == 'nt' else "--pool=prefork",  # Use solo pool on Windows
            "--include=tasks",  # Explicitly include tasks module
        ]
        
        print(f"💼 Starting worker with command: {' '.join(worker_args)}")
        print("📋 Worker will process tasks from the filesystem broker.")
        print("🛑 Press Ctrl+C to stop the worker.")
        print("-" * 50)
        
        subprocess.run(worker_args)
        
    except ImportError as e:
        print(f"❌ Error: Could not import Celery configuration: {e}")
        print("Make sure celeryconfig.py and tasks.py are in the current directory.")
    except KeyboardInterrupt:
        print("\n🛑 Stopping Celery worker...")
    except Exception as e:
        print(f"❌ Error starting Celery worker: {e}")

if __name__ == "__main__":
    start_celery_worker()
