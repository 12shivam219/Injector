import os
import pytest
from database.config import DatabaseConfig, get_connection_string, db_config


def test_parse_database_url(tmp_path, monkeypatch):
    url = 'postgresql://user:pass@localhost:5432/mydb'
    monkeypatch.setenv('DATABASE_URL', url)

    cfg = DatabaseConfig()
    assert cfg.config['host'] == 'localhost'
    assert cfg.config['username'] == 'user'
    assert cfg.config['password'] == 'pass'
    assert cfg.config['database'] == 'mydb'


def test_validate_missing_password(monkeypatch):
    # Ensure no password in env
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('DB_PASSWORD', raising=False)
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_USER', 'postgres')
    monkeypatch.setenv('DB_NAME', 'resume_customizer')
    monkeypatch.delenv('DB_PASSWORD', raising=False)

    cfg = DatabaseConfig()
    valid = cfg.validate_config()
    assert not valid['valid']
    assert any('Missing required field: password' in e for e in valid['errors'])
