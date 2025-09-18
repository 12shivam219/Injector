"""
Setup environment variables for database configuration
"""
import os

# Set environment variables
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'admin'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'injector'