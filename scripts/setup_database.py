#!/usr/bin/env python3
import sys
from pathlib import Path as _Path
# Ensure repository root is on sys.path when running this script from the scripts/ directory
_ROOT = _Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
"""
Database Setup Script for Resume Customizer
Easy PostgreSQL integration and migration from JSON storage
"""

import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup database environment and configuration"""
    try:
        from database.config import (
            setup_database_environment, 
            create_env_file_template, 
            validate_database_config,
            get_database_config
        )
        
        print("🔧 Setting up database environment...")
        
        # Create .env template if it doesn't exist
        env_file = Path('.env')
        if not env_file.exists():
            print("📝 Creating .env template file...")
            if create_env_file_template():
                print("✅ Created .env.template file")
                print("📋 Please copy .env.template to .env and configure your database settings")
                print("💡 Example: cp .env.template .env")
                return False
            else:
                print("❌ Failed to create .env template")
                return False
        
        # Setup database environment
        result = setup_database_environment()
        
        if result['success']:
            config = get_database_config()
            display_config = config.get_display_config()
            
            print("✅ Database environment setup completed successfully")
            print("📊 Database Configuration:")
            print(f"   Host: {display_config['host']}")
            print(f"   Port: {display_config['port']}")
            print(f"   Database: {display_config['database']}")
            print(f"   Username: {display_config['username']}")
            print(f"   Password: {display_config['password']}")
            print(f"   Pool Size: {display_config['pool_size']}")
            return True
        else:
            print("❌ Database environment setup failed")
            if result.get('validation_result', {}).get('errors'):
                for error in result['validation_result']['errors']:
                    print(f"   ❌ {error}")
            return False
            
    except ImportError as e:
        print(f"❌ Database dependencies not available: {e}")
        print("💡 Please install PostgreSQL dependencies: pip install psycopg2-binary sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def initialize_database():
    """Initialize PostgreSQL database schema"""
    try:
        from database import initialize_database, initialize_database_schema
        
        print("🔄 Initializing database connection...")
        if not initialize_database():
            print("❌ Failed to initialize database connection")
            return False
        
        print("🏗️ Creating database schema...")
        if not initialize_database_schema():
            print("❌ Failed to create database schema")
            return False
        
        print("✅ Database schema initialized successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Database dependencies not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    try:
        from database import get_connection_manager, initialize_database

        print("🔍 Testing database connection...")

        # Ensure the connection manager is initialized before testing
        print("� Initializing database connection for test...")
        if not initialize_database():
            print("❌ Failed to initialize database connection for test")
            return False

        from sqlalchemy import text

        conn_manager = get_connection_manager()
        with conn_manager.get_connection() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                print("✅ Database connection successful")
                return True

        return False
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def migrate_from_json(json_file: str = "requirements.json", backup: bool = True, dry_run: bool = False):
    """Migrate data from JSON to PostgreSQL"""
    try:
        from database.migrate_from_json import run_migration, run_dry_run
        
        json_path = Path(json_file)
        if not json_path.exists():
            print(f"⚠️ JSON file not found: {json_file}")
            print("📝 This is normal for new installations")
            return True
        
        if dry_run:
            print("🔍 Running migration dry run...")
            result = run_dry_run(json_file)
            
            if result['success']:
                analysis = result['analysis']
                print("✅ Dry run completed successfully")
                print(f"📊 Found {analysis['total_requirements']} requirements to migrate")
                print("📈 Data Quality Analysis:")
                quality = analysis['data_quality']
                print(f"   Complete requirements: {quality['complete_requirements']}")
                print(f"   Missing critical fields: {quality['missing_critical_fields']}")
                print(f"   Has comments: {quality['has_comments']}")
                print(f"   Has consultants: {quality['has_consultants']}")
                print(f"   Has vendor info: {quality['has_vendor_info']}")
                
                if analysis['transformation_preview']:
                    print("🔄 Transformation Preview:")
                    for i, preview in enumerate(analysis['transformation_preview'][:2]):
                        if 'error' not in preview:
                            structure = preview['new_structure']
                            print(f"   Sample {i+1}:")
                            print(f"     New structure: {structure['has_req_status']}")
                            print(f"     Comments: {structure['comments_count']}")
                            print(f"     Consultants: {structure['consultants_count']}")
                
                return True
            else:
                print(f"❌ Dry run failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print("🚀 Starting data migration from JSON to PostgreSQL...")
            result = run_migration(json_file, backup)
            
            if result['success']:
                stats = result['stats']
                print("🎉 Migration completed successfully!")
                print(f"📊 Migration Results:")
                print(f"   Total found: {stats['total_found']}")
                print(f"   Successfully migrated: {stats['successfully_migrated']}")
                print(f"   Failed: {stats['failed_migrations']}")
                
                if backup and json_path.exists():
                    print(f"💾 Original JSON file backed up")
                
                # Show verification results
                verification = result.get('verification', {})
                if verification.get('database_health', {}).get('connected'):
                    print("✅ Database verification passed")
                    total_in_db = verification.get('total_requirements_in_db', 0)
                    print(f"📊 Total requirements in database: {total_in_db}")
                
                return True
            else:
                print(f"❌ Migration failed: {result.get('error', 'Unknown error')}")
                if result['stats']['errors']:
                    print("❌ Errors encountered:")
                    for error in result['stats']['errors'][:5]:  # Show first 5 errors
                        print(f"   - {error}")
                return False
                
    except ImportError as e:
        print(f"❌ Migration dependencies not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def show_database_status():
    """Show current database status and statistics"""
    try:
        from database import database_health_check, get_database_information
        from database.requirements_manager_db import PostgreSQLRequirementsManager
        
        print("📊 Database Status Report")
        print("=" * 50)
        
        # Connection health
        health = database_health_check()
        if health['connected']:
            print("✅ Database Status: Connected")
            print(f"📊 Response Time: {health.get('response_time_ms', 'N/A')} ms")
        else:
            print("❌ Database Status: Disconnected")
            return False
        
        # Database information
        info = get_database_information()
        if info.get('tables'):
            print(f"\n📋 Tables ({len(info['tables'])}):")
            for table in info['tables']:
                print(f"   - {table['name']}: {table['row_count']} rows, {table['columns']} columns")
        
        # Requirements statistics
        print("\n📈 Requirements Statistics:")
        manager = PostgreSQLRequirementsManager()
        stats = manager.get_statistics()
        
        if stats:
            print(f"   Total Requirements: {stats.get('total_requirements', 0)}")
            
            status_stats = stats.get('by_status', {})
            if status_stats:
                print("   By Status:")
                for status, count in status_stats.items():
                    if count > 0:
                        print(f"     - {status}: {count}")
            
            consultant_stats = stats.get('by_consultant', {})
            if consultant_stats:
                print("   By Consultant:")
                for consultant, count in consultant_stats.items():
                    if count > 0:
                        print(f"     - {consultant}: {count}")
            
            top_tech = stats.get('top_technologies', {})
            if top_tech:
                print("   Top Technologies:")
                for tech, count in list(top_tech.items())[:5]:
                    print(f"     - {tech}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to get database status: {e}")
        return False

def main():
    """Main setup script entry point"""
    parser = argparse.ArgumentParser(
        description="Resume Customizer Database Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_database.py --setup                    # Setup database environment
  python setup_database.py --init                     # Initialize database schema
  python setup_database.py --migrate                  # Migrate from JSON to PostgreSQL
  python setup_database.py --migrate --dry-run        # Test migration without changes
  python setup_database.py --test                     # Test database connection
  python setup_database.py --status                   # Show database status
  python setup_database.py --all                      # Full setup (setup + init + migrate)
        """
    )
    
    parser.add_argument('--setup', action='store_true', help='Setup database environment')
    parser.add_argument('--init', action='store_true', help='Initialize database schema')
    parser.add_argument('--migrate', action='store_true', help='Migrate data from JSON')
    parser.add_argument('--test', action='store_true', help='Test database connection')
    parser.add_argument('--status', action='store_true', help='Show database status')
    parser.add_argument('--all', action='store_true', help='Run full setup process')
    parser.add_argument('--dry-run', action='store_true', help='Dry run for migration')
    parser.add_argument('--json-file', default='requirements.json', help='JSON file to migrate from')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup during migration')
    
    args = parser.parse_args()
    
    if not any([args.setup, args.init, args.migrate, args.test, args.status, args.all]):
        parser.print_help()
        return 1
    
    success = True
    
    print("🚀 Resume Customizer Database Setup")
    print("=" * 50)
    
    try:
        if args.all or args.setup:
            print("\n1️⃣ Setting up database environment...")
            if not setup_environment():
                success = False
                if not args.all:
                    return 1
        
        if args.all or args.init:
            print("\n2️⃣ Initializing database schema...")
            if not initialize_database():
                success = False
                if not args.all:
                    return 1
        
        if args.all or args.test:
            print("\n3️⃣ Testing database connection...")
            if not test_database_connection():
                success = False
                if not args.all:
                    return 1
        
        if args.all or args.migrate:
            print("\n4️⃣ Migrating data from JSON...")
            if not migrate_from_json(
                json_file=args.json_file,
                backup=not args.no_backup,
                dry_run=args.dry_run
            ):
                success = False
                if not args.all:
                    return 1
        
        if args.status:
            print("\n📊 Database Status...")
            if not show_database_status():
                success = False
                return 1
        
        if success:
            print("\n🎉 Setup completed successfully!")
            print("💡 Your application is now ready to use PostgreSQL database")
            print("🔧 You can now start your application with database support")
        else:
            print("\n⚠️ Setup completed with some issues")
            print("📋 Please review the errors above and try again")
            return 1
    
    except KeyboardInterrupt:
        print("\n⏹️ Setup interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


