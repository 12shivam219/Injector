# Resume Customizer Pro - Enterprise Multi-User Platform

## Overview

Resume Customizer Pro is a comprehensive, enterprise-grade multi-user platform designed for AI-powered resume customization and optimization. The application specializes in intelligently distributing technology stack points across resume projects and experiences to match specific job requirements. Built with scalability in mind, it supports 50+ concurrent users with advanced features including smart email automation, team collaboration, and high-performance PostgreSQL integration.

The platform transforms traditional resume customization by providing intelligent project detection, automated point distribution, and professional formatting while maintaining original document structure. It serves as both an individual tool for job seekers and an enterprise solution for recruitment teams and career services.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Streamlit Multi-Page Application**: Modern web interface with page-based navigation using Streamlit's native multi-page architecture
- **Component-Based UI Design**: Modular UI components in `/ui/` package with separation of concerns between standard and secure components
- **Progressive Loading**: Implements lazy loading for large file lists and heavy components to maintain responsive performance
- **Bootstrap Integration**: Shared application bootstrap (`app_bootstrap.py`) for consistent initialization across all pages

### Backend Architecture
- **Modular Package Structure**: Well-organized codebase with clear separation between core logic (`core/`), resume processing (`resume_customizer/`), infrastructure (`infrastructure/`), and UI (`ui/`)
- **Service-Oriented Design**: Cached services pattern for shared components including resume processors, requirements managers, and analytics
- **Dual Storage Backend**: Supports both JSON file storage and PostgreSQL database with automatic fallback mechanisms
- **Document Processing Pipeline**: Specialized parsers for different input formats with restriction validation and error recovery

### Data Storage Solutions
- **PostgreSQL Primary Database**: High-performance database with connection pooling (20-connection pool), optimized queries with proper indexing, and materialized views for analytics
- **Database Models**: Comprehensive schema including requirements management, resume documents, customizations, email tracking, processing logs, and audit trails
- **Migration System**: Automated database migrations with Alembic integration and data migration utilities from JSON to PostgreSQL
- **File Storage**: Local file system storage for uploaded documents with secure file validation and hash-based deduplication

### Authentication and Authorization
- **Security Enhancements**: AES-256 encryption for sensitive data, PBKDF2 password hashing, and comprehensive input sanitization
- **Session Management**: Secure session handling with timeout management and rate limiting for API endpoints
- **Access Control**: Role-based permission system with user profiles, subscription tiers (Free, Premium, Enterprise), and team workspace management
- **Audit Logging**: Comprehensive audit trail for security compliance and user activity tracking

### Processing Engine
- **Resume Processor**: Intelligent document processing using python-docx for DOCX files, text extraction, and project detection algorithms
- **Tech Stack Intelligence**: Smart technology mapping and point distribution based on job requirements analysis
- **Batch Processing**: Enhanced batch processor supporting parallel operations, memory optimization, and progress tracking
- **Async Processing**: Optional Celery integration for background task processing with Redis broker support

### Performance Optimization
- **Connection Pooling**: Advanced PostgreSQL connection management with retry logic and health monitoring
- **Caching Strategy**: Multi-level caching including session state management and service-level caching
- **Memory Management**: Optimized memory usage with garbage collection integration and resource monitoring
- **Concurrent Access**: Thread-safe operations designed to support 50+ concurrent users with proper resource isolation

## External Dependencies

### Core Framework Dependencies
- **Streamlit (≥1.28.0)**: Primary web application framework providing the user interface and page navigation system
- **Python-DOCX (≥0.8.11)**: Document processing library for reading and writing Microsoft Word DOCX files
- **Python-Multipart**: File upload handling for Streamlit applications

### Database Dependencies
- **PostgreSQL Integration**: Complete PostgreSQL stack including SQLAlchemy 2.0+ for ORM, psycopg2-binary for database connectivity, and Alembic for migrations
- **SQLAlchemy-Utils**: Additional utilities for database operations and model enhancements

### Document Processing
- **Mammoth (≥1.6.0)**: HTML conversion library for advanced document processing capabilities
- **PyPDF2 (≥3.0.0)**: PDF file processing support for multi-format document handling

### Distributed Processing
- **Celery (≥5.3.0)**: Distributed task queue for background processing and scalability
- **Redis (≥4.0.0)**: Message broker and caching backend for Celery integration

### Security Infrastructure
- **Cryptography (≥41.0.0)**: Encryption and secure password management with AES-256 support
- **Python-Jose (≥3.3.0)**: JWT token handling and secure authentication
- **Passlib (≥1.7.4)**: Password hashing with PBKDF2 and bcrypt support

### Email Automation
- **YagMail (≥0.15.293)**: Simplified email sending with SMTP integration and authentication
- **Email Template System**: Custom template engine with professional formatting and personalization

### Analytics and Monitoring
- **System Performance**: psutil for system resource monitoring and performance tracking
- **Python-Magic**: File type detection and validation for secure file uploads
- **Structured Logging**: Advanced logging with concurrent-log-handler and structlog for enterprise monitoring

### Data Processing
- **Pandas (≥2.0.0) and NumPy (≥1.24.0)**: Data analysis and manipulation for analytics features
- **Python-DateUtil and PyTZ**: Comprehensive date/time handling for scheduling and analytics

### Development Tools
- **Python-Dotenv**: Environment configuration management for secure credential handling
- **TQDM**: Progress bars for long-running operations and batch processing
- **Colorama**: Cross-platform colored terminal output for enhanced development experience