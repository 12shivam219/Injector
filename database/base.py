"""
Shared SQLAlchemy declarative base for the project.

All models should import `Base` from this module to ensure a single
metadata object is used for schema creation and migrations.
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
