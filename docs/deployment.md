# Production Deployment Guide

## Database Setup (Neon)

1. Create a new project on Neon.tech (https://neon.tech)
2. Get your connection string from the Neon dashboard
3. Add it to your production environment variables as `DATABASE_URL`

## Application Deployment (Render)

1. Create a new Web Service on Render.com
2. Connect your GitHub repository
3. Configure the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app.py`
4. Set these environment variables in Render:
   ```
   DATABASE_URL=your-neon-connection-string
   DB_ENCRYPTION_KEY=your-encryption-key
   USER_DATA_ENCRYPTION_KEY=your-user-data-key
   ENVIRONMENT=production
   ```

## Environment Variables

The application supports different environments through these variables:

- `ENVIRONMENT`: Set to 'development' or 'production'
- `DATABASE_URL`: Main database connection string
- `USE_SQLITE_FALLBACK`: Set to 'true' to use SQLite in development
- `DB_ENCRYPTION_KEY`: Database encryption key
- `USER_DATA_ENCRYPTION_KEY`: User data encryption key

## Database Configuration

Production settings (Neon):

```
DB_MIN_CONNECTIONS=2
DB_MAX_CONNECTIONS=10
DB_CONNECTION_TIMEOUT=30
DB_IDLE_TIMEOUT=300
DB_POOL_RECYCLE=300
```

Development settings (local PostgreSQL):

```
DB_MIN_CONNECTIONS=5
DB_MAX_CONNECTIONS=20
DB_CONNECTION_TIMEOUT=10
DB_IDLE_TIMEOUT=600
DB_POOL_RECYCLE=1800
```

## Deployment Checklist

1. Database:

   - [ ] Create Neon project
   - [ ] Get connection string
   - [ ] Test connection
   - [ ] Run migrations

2. Application:

   - [ ] Update requirements.txt
   - [ ] Test locally with production settings
   - [ ] Configure environment variables
   - [ ] Deploy to Render

3. Post-Deployment:
   - [ ] Verify database connection
   - [ ] Test core functionality
   - [ ] Monitor application logs
   - [ ] Check database performance
