import os
from sqlalchemy import create_engine, text
os.environ['DATABASE_URL']='postgresql://neondb_owner:npg_dQ6JOVN9AGSD@ep-raspy-feather-a8zo9edv-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require'
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='user_sessions' ORDER BY ordinal_position"))
    for r in res:
        print(r)
engine.dispose()
