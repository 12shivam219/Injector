"""
Post-deployment verification script for Resume Customizer
Checks various aspects of the deployed application
"""
import os
import sys
import logging
import requests
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_connection(database_url):
    """Test connection to the production database"""
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Test basic connectivity
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✅ Connected to database: {version}")
            
            # Check if required tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            logger.info(f"Found tables: {', '.join(tables)}")
            
            # Check connection pool
            pool_size = engine.pool.size()
            logger.info(f"Connection pool size: {pool_size}")
            
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

def check_render_deployment(app_url):
    """Test the Render deployment"""
    try:
        response = requests.get(app_url)
        if response.status_code == 200:
            logger.info(f"✅ Application is accessible at {app_url}")
            return True
        else:
            logger.error(f"❌ Application returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Could not access application: {str(e)}")
        return False

def check_environment_variables():
    """Verify required environment variables are set"""
    required_vars = [
        'DATABASE_URL',
        'DB_ENCRYPTION_KEY',
        'USER_DATA_ENCRYPTION_KEY',
        'ENVIRONMENT'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def main():
    """Run all deployment checks"""
    load_dotenv()  # Load local .env file if it exists
    
    print("\n=== Resume Customizer Deployment Verification ===\n")
    
    # Check environment
    env = os.getenv('ENVIRONMENT', 'development')
    print(f"\nEnvironment: {env}")
    
    # Verify environment variables
    env_ok = check_environment_variables()
    
    # Check database connection
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print("\nChecking database connection...")
        db_ok = check_database_connection(db_url)
    else:
        print("\n❌ DATABASE_URL not set")
        db_ok = False
    
    # Check Render deployment
    app_url = os.getenv('RENDER_EXTERNAL_URL')
    if app_url:
        print("\nChecking Render deployment...")
        render_ok = check_render_deployment(app_url)
    else:
        print("\n❌ RENDER_EXTERNAL_URL not set. Please provide your Render URL.")
        render_ok = False
    
    # Print summary
    print("\n=== Deployment Status Summary ===")
    print(f"Environment Variables: {'✅' if env_ok else '❌'}")
    print(f"Database Connection: {'✅' if db_ok else '❌'}")
    print(f"Render Deployment: {'✅' if render_ok else '❌'}")
    
    if not all([env_ok, db_ok, render_ok]):
        print("\nRecommendations:")
        if not env_ok:
            print("- Set all required environment variables")
        if not db_ok:
            print("- Check database connection string and network access")
        if not render_ok:
            print("- Verify Render deployment and application logs")
            print("- Ensure application is properly built and started")
    else:
        print("\n🎉 Deployment verification completed successfully!")

if __name__ == "__main__":
    main()