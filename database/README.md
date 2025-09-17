Database module

Overview

- This folder contains helpers for connecting to PostgreSQL using SQLAlchemy.
- Configuration is driven from environment variables. See the project root `.env.example`.

Usage

- Create a `.env` file from the `.env.example` in the repo root and fill in real credentials.
- Recommended variables: `DATABASE_URL` (full SQLAlchemy connection string). Optionally `DB_READ_CONNECTION_STRING` for a read-replica.

Running setup

- To create tables and indexes locally (developer use only):
  - Activate virtualenv and install dependencies: `pip install -r requirements.txt`.
  - Run: `python database/setup_database.py` (requires `DATABASE_URL` in env).

Security notes

- Do NOT commit `.env` or plaintext credentials.
- If you need to share connection strings among team members, use your organization's secret manager.

Tests

- Unit tests for the database config live in `tests/`.
- To run tests: `pytest tests -q` (ensure env vars are set or tests mock them).
