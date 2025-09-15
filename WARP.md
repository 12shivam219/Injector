# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Development Commands

### Application Startup
```bash
# Start the main application
streamlit run app.py

# Start with specific configuration
streamlit run app.py --server.port=8501 --server.address=localhost
```

### Database Operations
```bash
# Setup database environment and initialize schema
python scripts/setup_database.py

# Migrate data from JSON to PostgreSQL
python scripts/setup_database.py --migrate

# Run database migration dry run
python scripts/setup_database.py --dry-run
```

### Background Processing
```bash
# Start Celery worker for async processing (Windows)
python scripts/start_celery_worker.py

# Alternative batch script for Windows
scripts/start_celery.bat

# Start Redis server (required for Celery)
redis-server
```

### Testing
```bash
# Run all tests
pytest

# Run tests with configuration
pytest -c config/pytest.ini

# Run specific test file
pytest tests/test_comprehensive.py

# Run performance benchmarks
python tests/performance_benchmark.py
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.template .env
# Edit .env file with your database and email configurations

# Setup database (first time)
python scripts/setup_database.py --setup-env
```

### Development Utilities
```bash
# Run database demo
python run_database_demo.py

# Test database connection
python scripts/setup_database.py --test-connection

# Check application status
python -c "from app_bootstrap import get_cached_services; print(get_cached_services())"
```

## Architecture Overview

### Multi-Page Streamlit Application
The application follows Streamlit's multi-page architecture with:
- **Main App** (`app.py`): Landing page and application bootstrap
- **Pages Directory**: Contains individual page modules (Resume Customizer, Bulk Processor, Requirements Management, etc.)
- **Shared Bootstrap** (`app_bootstrap.py`): Centralized initialization and service caching

### Core Components

#### 1. Resume Processing Engine
- **Location**: `resume_customizer/` and `core/`
- **Purpose**: Intelligent document processing for DOCX files
- **Key Features**: 
  - Project detection algorithms
  - Tech stack point distribution
  - Format preservation during modification
  - Batch processing capabilities

#### 2. Database Layer
- **Location**: `database/`
- **Technology**: PostgreSQL with SQLAlchemy ORM
- **Key Models**: 
  - `Requirement`: Job requirements with comprehensive indexing
  - `RequirementComment`: Timeline-optimized comments
  - `RequirementConsultant`: Many-to-many consultant relationships
- **Performance**: Connection pooling, JSONB fields with GIN indexes, materialized views

#### 3. UI Framework
- **Location**: `ui/`, `pages/`
- **Architecture**: Component-based design with secure and standard components
- **Key Modules**:
  - `UIComponents`: Standard UI elements
  - `secure_components`: Security-enhanced UI elements
  - `bulk_processor.py`: Parallel processing interface
  - `resume_tab_handler.py`: Single resume processing interface

#### 4. Infrastructure Services
- **Location**: `infrastructure/`
- **Services**:
  - **Async Processing**: Celery integration with Redis broker
  - **Monitoring**: Performance tracking and health checks
  - **Logging**: Structured logging with concurrent handlers
  - **Utilities**: Memory optimization, retry handlers, validators

### Data Flow Architecture

#### Single Resume Processing
1. **Upload**: User uploads DOCX file via Streamlit interface
2. **Parsing**: Document processed using `python-docx` library
3. **Analysis**: Project sections detected and analyzed
4. **Enhancement**: Tech stack points distributed across top 3 projects
5. **Output**: Modified DOCX with preserved formatting

#### Bulk Processing
1. **Batch Upload**: Multiple resumes uploaded simultaneously
2. **Queue Processing**: Files queued for parallel processing
3. **Worker Pool**: Multiple workers process files concurrently
4. **Progress Tracking**: Real-time progress updates via session state
5. **Email Integration**: Optional batch email sending with SMTP pooling

#### Requirements Management
1. **Database Storage**: Requirements stored in PostgreSQL with full indexing
2. **JSON Migration**: Legacy JSON data migrated to database with validation
3. **Search & Filter**: Optimized queries using composite indexes
4. **Version Control**: Optimistic locking for concurrent modifications

### Security Architecture
- **Password Encryption**: AES-256 encryption for sensitive data
- **Session Management**: Secure session handling with timeout management
- **Input Validation**: Comprehensive sanitization for all user inputs
- **Access Control**: Role-based permissions with user profiles
- **Audit Logging**: Complete audit trail for compliance

## Development Patterns

### Service Initialization
Services are cached using `@st.cache_resource` in `app_bootstrap.py`. Always use `get_cached_services()` to access services to avoid reinitializing expensive resources.

### Database Operations
- Use the connection manager from `database/connection.py` for all database operations
- Leverage the ORM models in `database/models.py` for type safety
- Always use connection pooling for performance
- Migrations are handled automatically via Alembic

### Error Handling
The application uses structured error handling:
- Core errors defined in `core/errors.py`
- Structured logging via `infrastructure/utilities/structured_logger.py`
- Circuit breaker pattern for external service calls
- Graceful degradation for non-critical features

### Configuration Management
- Environment variables loaded from `.env` file
- Configuration centralized in `config.py`
- Database configuration in `database/config.py`
- Feature flags available in `core/config.py`

### Testing Strategy
- Unit tests focus on core processing logic
- Integration tests for database operations
- Performance benchmarks for optimization validation
- Pytest configuration in `config/pytest.ini`

## Key Files and Their Purposes

### Core Application Files
- `app.py`: Main entry point and landing page
- `app_bootstrap.py`: Shared initialization and service caching
- `config.py`: Root configuration module

### Processing Engine
- `resume_customizer/processors/`: Resume processing algorithms
- `processors/point_distributor.py`: Tech stack point distribution logic
- `detectors/project_detector.py`: Project section detection

### Database Components
- `database/models.py`: SQLAlchemy ORM models with performance optimizations
- `database/connection.py`: Connection pooling and management
- `database/migrations.py`: Database schema migrations
- `database/migrate_from_json.py`: Legacy data migration utilities

### Infrastructure
- `infrastructure/async_processing/`: Celery task definitions and async integration
- `infrastructure/monitoring/`: Performance monitoring and health checks
- `infrastructure/utilities/`: Shared utilities and helpers

### User Interface
- `pages/1_Resume_Customizer.py`: Single resume processing interface
- `pages/2_Bulk_Processor.py`: Bulk processing interface
- `pages/3_Requirements.py`: Requirements management interface
- `ui/components.py`: Reusable UI components
- `ui/bulk_processor.py`: Bulk processing UI logic

## Performance Considerations

### Database Optimization
- Use JSONB fields with GIN indexes for tech stack queries
- Composite indexes on frequently queried field combinations
- Connection pooling with 20-connection limit
- Materialized views for complex analytics queries

### Memory Management
- Lazy loading of heavy components
- Memory cleanup after bulk operations
- Garbage collection integration in long-running processes
- Session state optimization to prevent memory leaks

### Concurrent Processing
- Worker pools for parallel resume processing
- SMTP connection pooling for email operations
- Thread-safe operations for multi-user environments
- Circuit breaker pattern for external service resilience

## Environment Variables and Configuration

Key environment variables in `.env`:
- **Database**: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- **Application**: `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`
- **Performance**: `APP_MAX_WORKERS_DEFAULT`, `CACHE_TTL`, `CONNECTION_POOL_TIMEOUT`
- **Email**: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- **Security**: `SECRET_KEY`, `ENCRYPTION_KEY`

## Troubleshooting Common Issues

### Database Connection Issues
1. Verify PostgreSQL is running
2. Check `.env` configuration
3. Run `python scripts/setup_database.py --test-connection`
4. Ensure database exists and user has proper permissions

### Performance Issues
1. Check worker count configuration in bulk processing
2. Monitor memory usage during large file processing
3. Verify Redis is running for Celery tasks
4. Check connection pool settings

### Import Errors
The application uses graceful degradation - missing dependencies will disable related features but won't crash the application. Check service availability via `get_cached_services()`.

## Development Workflow

1. **Environment Setup**: Copy `.env.template` to `.env` and configure
2. **Database Setup**: Run `python scripts/setup_database.py`
3. **Development**: Start with `streamlit run app.py`
4. **Background Tasks**: Start Celery worker if using async features
5. **Testing**: Run `pytest` for validation before commits