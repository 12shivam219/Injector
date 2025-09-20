# 🎯 Resume Customizer Pro

A comprehensive resume customization platform with advanced multi-user features, smart email automation, team collaboration, and high-performance architecture.

## 🔐 Security Features

- **Password Encryption**: AES-256 encryption for email passwords
- **Secure Authentication**: PBKDF2 password hashing
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Protection against brute force attacks
- **Session Management**: Secure session handling
- **Access Control**: Role-based permissions system

## 🚀 Deployment

### Database (Neon.tech)

1. Create a free account on [Neon.tech](https://neon.tech)
2. Create a new project
3. Get your database connection string
4. Set up the environment variables as described in `.env.example`

### Installation

The project uses a modular requirements structure for different environments:

1. **Basic Installation** (Production):

   ```bash
   pip install -r requirements.txt -r requirements-base.txt
   ```

2. **Development Setup** (includes testing tools):

   ```bash
   pip install -r requirements.txt -r requirements-base.txt -r requirements-dev.txt
   ```

3. **Windows Development** (includes Windows-specific packages):
   ```bash
   pip install -r requirements.txt -r requirements-base.txt -r requirements-windows.txt
   ```

### Application Deployment (Render.com)

1. Fork this repository to your GitHub account
2. Create a new Web Service on [Render.com](https://render.com)
3. Connect your GitHub repository
4. The deployment configuration is already set up in `render.yaml`
5. Set up your environment variables in the Render dashboarder Pro - Enterprise Multi-User Platform

A comprehensive resume customization platform with advanced multi-user features, smart email automation, team collaboration, and high-performance architecture supporting 50+ concur└── 📁 resume_customizer/ # Core resume customization logic
│ ├── **init**.py
│ ├── analyzers/ # Analysis modules
│ ├── parsers/ # Text and document parsing
│ ├── processors/ # Document processing
│ └── formatters/ # Formatting modules
│.

## 🔐 Security Features

- **Password Encryption**: AES-256 encryption for email passwords
- **Secure Authentication**: PBKDF2 password hashing
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Protection against brute force attacks
- **Session Management**: Secure session handling
- **Access Control**: Role-based permissions system

## 📊 Database Features

- **High-Performance PostgreSQL**: Optimized for concurrent access
- **Adaptive Connection Pooling**: Dynamic pool sizing based on load metrics
- **Encrypted Connection Strings**: Secure storage of database credentials
- **Query Monitoring**: Automatic detection and logging of slow queries
- **Read/Write Splitting**: Separate connection pools for read and write operations
- **Repository Pattern**: Standardized data access with error handling
- **Query Builder**: Fluent interface for building complex SQL queries
- **Sharding Strategy**: Horizontal scaling for future data growth
- **Role-Based Access Control**: Fine-grained database permissions
- **Automatic Migrations**: Database versioning and migrations
- **Data Validation**: Schema-level constraints and validation
- **Backup & Recovery**: Automated backup procedures

## ✨ Enhanced Features

### 👤 User Account Management

- **Secure Authentication**: PBKDF2 password hashing, session management
- **User Profiles**: Bio, skills, professional information, profile pictures
- **Subscription Tiers**: Free, Premium, Enterprise with usage limits
- **Analytics Dashboard**: Usage tracking, performance metrics

### 📧 Smart Email Follow-up System

- **Advanced Templates**: Professional, Casual, Creative styles
- **Smart Scheduling**: Business hours optimization, timezone awareness
- **Email Tracking**: Opens, clicks, replies with analytics
- **Campaign Management**: Multi-sequence follow-ups, auto-stop on reply
- **Company Intelligence**: Personalized content based on company research

### 👥 Multi-User Collaboration

- **Team Workspaces**: Create and manage teams with role-based access
- **Resume Sharing**: Share with users, teams, or public links
- **Real-time Comments**: Collaborative feedback system
- **Permission Levels**: View, Comment, Edit access controls
- **Activity Feeds**: Track team activity and notifications

### ⚡ High-Performance Architecture

- **PostgreSQL Database**: Optimized for enterprise scale
- **Database Pooling**: Connection pool for optimal performance
- **Advanced Caching**: Memory cache with TTL, file processing cache
- **Async Operations**: Non-blocking background processing
- **Error Handling**: Comprehensive error recovery and logging

### 📄 Enhanced Resume Processing

- **Batch Processing**: Parallel processing with worker pools
- **Format Preservation**: Maintains original formatting and styles
- **Version Control**: Track resume versions and changes
- **Template System**: Save and reuse resume templates
- **Intelligent Point Distribution**: Sophisticated algorithm for optimal tech stack distribution
- **Customizable Formatting Rules**: Configuration system for bullet points and formatting styles
- **Enhanced Preview Feature**: Multi-view preview with before/after comparison and visual diff

## 🚀 Quick Start

### Option 1: Local Development

```bash
# Clone the repository
git clone https://github.com/12shivam219/Injector.git
cd Injector

# Install core dependencies
pip install -r requirements.txt

# Install Google Drive integration (optional)
pip install -r requirements-gdrive.txt

# Run the application
streamlit run app.py
```

### Option 2: One-Click Deploy

- **Streamlit Cloud**: [![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
- **Railway**: Deploy directly from GitHub
- **Heroku**: One-click deploy with Heroku button

## � Installation & Setup

### Requirements

- Python 3.13+
- PostgreSQL 15+
- Redis (optional, for task queue)

### Installation Options

1. **Basic Installation** (Production):

   ```bash
   pip install -r requirements.txt -r requirements-base.txt
   ```

2. **Development Setup**:

   ```bash
   pip install -r requirements.txt -r requirements-base.txt -r requirements-dev.txt
   ```

3. **Windows Development**:
   ```bash
   pip install -r requirements.txt -r requirements-base.txt -r requirements-windows.txt
   ```

## 🔧 Usage

### 1. Format Management (First Step)

- Go to the **Format Manager** tab first
- Upload sample resume templates that represent different formats
- Name and describe each format for easy reference
- System will analyze and store format patterns
- Test format matching with sample resumes

### 2. Upload Resumes

- Upload one or more DOCX files
- System will automatically match with stored formats
- Each resume should have clear project sections with "Responsibilities:" headings

### 2. Add Tech Stacks

For each resume, provide tech stacks in this format:

```
Python: • Developed web applications using Django and Flask • Implemented RESTful APIs
JavaScript: • Created interactive UI components with React • Utilized Node.js for backend services
AWS: • Deployed applications using EC2 and S3 • Managed databases with RDS
```

### 3. Configure Email (Optional)

- **Recipient Email**: Where to send the resume
- **Sender Email**: Your email address
- **App Password**: Use app-specific passwords for Gmail/Office365
- **SMTP Server**: Pre-configured options available

### 4. Preview Changes

- Click "🔍 Preview Changes" to see exactly what will be modified
- Multiple preview views:
  - Full Preview: Complete resume with highlighted changes
  - New Points Only: View only the additions by project
  - Visual Diff: Color-coded visualization of changes
  - Before/After: Side-by-side comparison
- Detailed distribution statistics showing points per project

### 5. Generate & Send

- **Individual**: Process one resume at a time
- **Bulk Mode**: Process 3+ resumes simultaneously for maximum speed

## 🏗️ Architecture

### Core Components

- **Resume Parser**: Finds projects and responsibilities sections
- **Point Distributor**: Intelligent algorithm for optimal tech stack distribution
- **Format Preserver**: Maintains original document formatting
- **Formatting Configuration**: Customizable bullet points and formatting styles
- **Enhanced Preview**: Multi-view preview with visual diff and comparison
- **Email Manager**: SMTP connection pooling and batch sending
- **Parallel Processor**: Multi-threaded resume processing

### Performance Features

- **Connection Pooling**: Reuses SMTP connections for faster email sending
- **Parallel Processing**: Up to 8x faster with multiple workers
- **Memory Optimization**: Efficient buffer management
- **Real-time Progress**: Live updates during bulk operations

## 📁 Project Structure

## 📁 Project Structure

```
injector/
├── app.py                  # Main Streamlit application
├── config.py              # Configuration module
├── requirements.txt       # Main requirements file
├── requirements-base.txt  # Core dependencies
├── requirements-dev.txt   # Development tools
├── requirements-windows.txt # Windows-specific packages
│
├── 📁 core/              # Core application logic
│   ├── config.py         # Core configuration
│   ├── constants.py      # Global constants
│   ├── errors.py         # Error definitions
│   └── types.py         # Type definitions
│
├── 📁 database/          # Database components
│   ├── adaptive_pool.py  # Connection pooling
│   ├── encryption.py     # Data encryption
│   ├── session.py       # Session management
│   ├── models/          # Database models
│   └── repository/      # Data access layer
│
├── 📁 resume_customizer/ # Core resume logic
│   ├── analyzers/       # Analysis modules
│   ├── parsers/         # Document parsing
│   ├── processors/      # Processing logic
│   └── formatters/      # Output formatting
│
├── 📁 pages/            # Streamlit pages
├── 📁 scripts/          # Utility scripts
├── 📁 tests/            # Test suite
└── 📁 docs/             # Documentation
│   ├── celeryconfig.py             # Celery configuration
│   ├── docker-compose.prod.yml     # Production Docker setup
│   ├── pytest.ini                 # Test configuration
│   └── celery.exchange             # Celery queue configuration
│
├── 📁 core/                        # Core application modules
│   ├── __init__.py
│   ├── resume_processor.py         # Resume processing coordination
│   ├── email_handler.py            # Email operations module
│   ├── document_processor.py       # Document processing module
│   ├── text_parser.py              # Text parsing functionality
│   ├── async_processor.py          # Async processing
│   └── async_integration.py        # Async integration
│
├── 📁 enhancements/                # Enhanced feature modules
│   ├── __init__.py
│   ├── metrics_analytics_enhanced.py
│   ├── health_monitor_enhanced.py
│   ├── email_templates_enhanced.py
│   ├── enhanced_error_recovery.py
│   ├── batch_processor_enhanced.py
│   ├── progress_tracker_enhanced.py
│   └── error_handling_enhanced.py
│
├── 📁 infrastructure/              # Infrastructure components
│   ├── __init__.py
│   ├── app/                        # Application bootstrap
│   ├── monitoring/                 # Monitoring and logging
│   ├── error_handling/            # Error handling
│   ├── security/                  # Security components
│   ├── utilities/                 # Shared utilities
│   └── async_processing/          # Async operations
│
├── 📁 utilities/                   # Helper utilities
│   ├── __init__.py
│   ├── logger.py
│   ├── validators.py
│   ├── memory_optimizer.py
│   ├── structured_logger.py
│   ├── lazy_imports.py
│   └── retry_handler.py
│
├── 📁 config/                       # Configuration files
│   └── formatting_config.json       # Formatting rules configuration
│
├── 📁 database/                    # Database modules
│   ├── __init__.py
│   ├── models.py
│   ├── connection.py
│   ├── migrations.py
│   ├── migrate_from_json.py
│   └── requirements_manager_db.py
│
├── 📁 ui/                          # User interface components
│   ├── __init__.py
│   ├── components.py
│   ├── bulk_processor.py
│   ├── resume_tab_handler.py
│   ├── requirements_manager.py
│   ├── secure_components.py
│   ├── gdrive_picker.py
│   └── utils.py
│
├── 📁 processors/                  # Document processors
│   ├── __init__.py
│   └── point_distributor.py
│
├── 📁 templates/                   # Resume templates
│   ├── software_engineer_template.txt
│   ├── data_science_template.txt
│   ├── product_manager_template.txt
│   ├── executive_template.txt
│   └── general_professional_template.txt
├── 📁 tests/                       # Test files
│   ├── test_comprehensive.py
│   ├── test_bullet_formatting.py
│   ├── test_celery_end_to_end.py
│   ├── test_celery_task.py
│   ├── test_imports.py
│   ├── test_real_task.py
│   ├── test_security_phase1.py
│   └── performance_benchmark.py
│
├── 📁 scripts/                     # Deployment & utility scripts
│   ├── run_worker.bat              # Windows Celery worker script
│   ├── start_celery.bat           # Windows Celery startup
│   ├── start_celery_worker.py     # Python Celery worker
│   └── setup_database.py          # Database setup script
│
├── 📁 docs/                        # Documentation
│   ├── DATABASE_MIGRATION_GUIDE.md
│   ├── ENHANCEMENT_SUMMARY.md
│   ├── PHASE1_USAGE_GUIDE.md
│   ├── README-celery.md
│   ├── README-monitoring.md
│   └── REQUIREMENTS_UPDATE_SUMMARY.md
│
└── 📁 .streamlit/                  # Streamlit configuration
    └── config.toml
```

## � Encryption Keys

- **Generate keys**: Run `python scripts/generate_keys.py` to produce two Fernet keys.
- **Local development**: Copy the generated values into a local `.env` file (this repo now includes an example `.env.example`).
- **Production**: Do NOT commit real keys. Use your deployment platform's secret manager (Streamlit secrets, Vault, environment variables) to set `DB_ENCRYPTION_KEY` and `USER_DATA_ENCRYPTION_KEY`.
- **Streamlit Cloud**: Add keys to Streamlit secrets and they will be loaded by `infrastructure/app/streamlit_config.py`.

## �🔒 Security

- **No Credential Storage**: Email credentials are never stored
- **App-Specific Passwords**: Supports secure authentication methods
- **Input Validation**: Validates file types and content
- **Error Handling**: Graceful handling of failures

## 🚀 Deployment

### Recommended Platforms

1. **Streamlit Cloud** (Free)

   - Best for: Quick deployment, public projects
   - Setup: Connect GitHub → Deploy
   - URL: Auto-generated

2. **Railway** (Modern PaaS)
   - Best for: Modern deployment, generous free tier
   - Setup: Connect GitHub → Auto-deploy
   - Features: Automatic HTTPS, custom domains

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## ⚡ Performance

### Benchmarks

- **Single Resume**: ~2-3 seconds
- **Bulk Processing**: Up to 8x faster with parallel workers
- **Email Sending**: Connection pooling for optimal speed
- **Memory Usage**: Optimized for multiple file processing

### Scaling

- **Concurrent Users**: Supports multiple simultaneous users
- **File Size**: Handles large DOCX files efficiently
- **Batch Size**: Configurable worker count and batch sizes

## 🛠️ Troubleshooting

### Common Issues

1. **Email Not Sending**

   - Use app-specific passwords
   - Check firewall settings
   - Verify SMTP server settings

2. **Resume Not Recognized**

   - Ensure clear "Responsibilities:" sections
   - Check project heading formats
   - Verify DOCX format

3. **Performance Issues**
   - Reduce worker count for lower-spec machines
   - Check memory availability
   - Optimize batch sizes

### Debug Mode

Enable debug output:

```python
import streamlit as st
st.write("Debug info:", st.session_state)
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Deployment Guide](DEPLOYMENT.md)
- 🐛 [Report Issues](https://github.com/12shivam219/Injector/issues)
- 💬 [Discussions](https://github.com/12shivam219/Injector/discussions)

## 🎯 Use Cases

- **Job Seekers**: Customize resumes for different job applications
- **Recruiters**: Bulk process candidate resumes
- **Career Services**: Help students tailor resumes
- **Freelancers**: Quick resume customization for clients

## 🌟 Key Benefits

- ⏱️ **Time Saving**: Bulk process multiple resumes
- 🎯 **Targeted**: Focus on top 3 projects for impact
- 📧 **Automated**: Direct email sending capabilities
- 🔍 **Preview**: See changes before processing
- 🚀 **Fast**: Parallel processing for speed
- 📱 **User-Friendly**: Intuitive Streamlit interface

---

**Made with ❤️ using Streamlit**

_Perfect for job applications, recruitment agencies, and career services!_
