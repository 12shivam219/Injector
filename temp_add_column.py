import os
from sqlalchemy import create_engine, text
os.environ['DATABASE_URL']='postgresql://neondb_owner:npg_dQ6JOVN9AGSD@ep-raspy-feather-a8zo9edv-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require'
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_user_sessions_session_id ON user_sessions (session_id);"))
        print('Added session_id column and index (if they were missing)')
    except Exception as e:
        print('Error while altering table:', e)
engine.dispose()
