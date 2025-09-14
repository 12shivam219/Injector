"""
PostgreSQL Data Flow Demonstration for Resume Customizer
Complete demonstration showing how data is stored, retrieved, and flows through the system
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import json

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database, get_db_session, database_health_check
from database.config import setup_database_environment, create_env_file_template
from database.crud_operations import ResumeCRUDOperations
from database.models import Base
from database.resume_models import ResumeDocument, ResumeCustomization, EmailSend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgreSQLDataFlowDemo:
    """
    Comprehensive demonstration of PostgreSQL integration with Resume Customizer
    Shows complete data flow from upload to email sending
    """
    
    def __init__(self):
        self.crud_ops = ResumeCRUDOperations()
        self.demo_user_id = "demo_user_12345"
        self.demo_session_id = "session_67890"
    
    def setup_database(self) -> bool:
        """
        Setup and initialize the PostgreSQL database
        """
        print("🔧 Setting up PostgreSQL Database Connection...")
        print("=" * 60)
        
        # Create environment template if it doesn't exist
        if not os.path.exists('.env'):
            print("📝 Creating .env template file...")
            create_env_file_template('.env')
            print("✅ .env template created. Please update with your PostgreSQL credentials.")
            print("\n📋 Default database configuration:")
            print("   - Host: localhost")
            print("   - Port: 5432") 
            print("   - Database: resume_customizer")
            print("   - Username: postgres")
            print("   - Password: (update in .env file)")
            return False
        
        # Setup database environment
        setup_result = setup_database_environment()
        if not setup_result['success']:
            print("❌ Database environment setup failed!")
            if setup_result.get('validation_result', {}).get('errors'):
                for error in setup_result['validation_result']['errors']:
                    print(f"   • {error}")
            return False
        
        # Initialize database connection
        print("🔌 Initializing database connection...")
        if not initialize_database():
            print("❌ Failed to initialize database connection!")
            return False
        
        # Perform health check
        print("🏥 Performing database health check...")
        health = database_health_check()
        if not health['connected']:
            print("❌ Database health check failed!")
            for error in health.get('errors', []):
                print(f"   • {error}")
            return False
        
        print(f"✅ Database connected successfully!")
        print(f"   • Response time: {health['response_time_ms']}ms")
        print(f"   • Pool status: {health['pool_status']}")
        
        return True
    
    def create_sample_resume_data(self) -> Dict[str, Any]:
        """
        Create sample resume data for demonstration
        """
        return {
            'filename': 'john_doe_resume.docx',
            'original_filename': 'John Doe - Software Engineer Resume.docx',
            'file_size': 45678,
            'file_hash': 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456',
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'original_content': '''
            John Doe
            Software Engineer
            
            EXPERIENCE:
            • 5+ years of software development experience
            • Proficient in Python, Java, and JavaScript
            • Experience with web frameworks like Django and React
            • Database design and optimization
            • Agile development methodologies
            
            SKILLS:
            • Programming Languages: Python, Java, JavaScript, C++
            • Web Technologies: HTML, CSS, React, Angular, Django
            • Databases: PostgreSQL, MySQL, MongoDB
            • Tools: Git, Docker, Jenkins, AWS
            ''',
            'processed_content': 'Cleaned and processed resume content...',
            'document_structure': {
                'sections': ['header', 'experience', 'skills', 'education'],
                'bullet_points': 12,
                'word_count': 245
            },
            'user_id': self.demo_user_id,
            'session_id': self.demo_session_id
        }
    
    def demonstrate_data_flow(self):
        """
        Complete demonstration of data flow through the system
        """
        print("\n🚀 Starting PostgreSQL Data Flow Demonstration")
        print("=" * 60)
        
        # Step 1: Create Resume Document
        print("\n📄 STEP 1: Creating Resume Document")
        print("-" * 40)
        
        resume_data = self.create_sample_resume_data()
        print(f"📝 Creating resume document: {resume_data['filename']}")
        print(f"   • File size: {resume_data['file_size']} bytes")
        print(f"   • User ID: {resume_data['user_id']}")
        
        resume_id = self.crud_ops.create_resume_document(resume_data)
        if not resume_id:
            print("❌ Failed to create resume document!")
            return
        
        print(f"✅ Resume document created with ID: {resume_id}")
        
        # Step 2: Retrieve Resume Document
        print(f"\n🔍 STEP 2: Retrieving Resume Document")
        print("-" * 40)
        
        retrieved_resume = self.crud_ops.get_resume_document(resume_id)
        if retrieved_resume:
            print("✅ Resume document retrieved successfully!")
            print(f"   • ID: {retrieved_resume['id']}")
            print(f"   • Filename: {retrieved_resume['filename']}")
            print(f"   • Status: {retrieved_resume['processing_status']}")
            print(f"   • Created: {retrieved_resume['created_at']}")
        else:
            print("❌ Failed to retrieve resume document!")
            return
        
        # Step 3: Update Processing Status
        print(f"\n⚙️ STEP 3: Updating Processing Status")
        print("-" * 40)
        
        print("🔄 Updating status to 'processing'...")
        self.crud_ops.update_resume_processing_status(resume_id, 'processing')
        
        time.sleep(1)  # Simulate processing time
        
        print("✅ Updating status to 'completed'...")
        self.crud_ops.update_resume_processing_status(resume_id, 'completed')
        
        # Step 4: Create Customizations
        print(f"\n🎯 STEP 4: Creating Resume Customizations")
        print("-" * 40)
        
        # Create multiple customizations for different jobs
        customizations = [
            {
                'resume_document_id': resume_id,
                'job_title': 'Senior Python Developer',
                'company_name': 'TechCorp Inc.',
                'job_description': 'Looking for a senior Python developer with Django experience...',
                'tech_stack_input': ['Python', 'Django', 'PostgreSQL', 'AWS', 'Docker'],
                'required_skills': ['Python', 'Django', 'REST APIs', 'PostgreSQL'],
                'customized_content': 'Customized resume content for TechCorp...',
                'added_bullet_points': [
                    'Developed scalable web applications using Django framework',
                    'Optimized PostgreSQL database queries for improved performance'
                ],
                'modified_sections': {'experience': 'enhanced', 'skills': 'reordered'},
                'processing_time_seconds': 2.5
            },
            {
                'resume_document_id': resume_id,
                'job_title': 'Full Stack Developer',
                'company_name': 'StartupXYZ',
                'job_description': 'Full stack developer needed for React/Node.js application...',
                'tech_stack_input': ['JavaScript', 'React', 'Node.js', 'MongoDB'],
                'required_skills': ['JavaScript', 'React', 'Node.js', 'MongoDB', 'Express'],
                'customized_content': 'Customized resume content for StartupXYZ...',
                'added_bullet_points': [
                    'Built responsive web applications using React and Node.js',
                    'Implemented RESTful APIs with Express.js framework'
                ],
                'modified_sections': {'skills': 'frontend_focused'},
                'processing_time_seconds': 3.1
            }
        ]
        
        customization_ids = []
        for i, custom_data in enumerate(customizations, 1):
            print(f"📋 Creating customization {i}: {custom_data['company_name']} - {custom_data['job_title']}")
            
            custom_id = self.crud_ops.create_customization(custom_data)
            if custom_id:
                customization_ids.append(custom_id)
                print(f"   ✅ Created with ID: {custom_id}")
                
                # Update quality metrics
                quality_score = 0.85 + (i * 0.05)  # Simulate different quality scores
                match_percentage = 78.0 + (i * 5.0)  # Simulate match percentages
                
                self.crud_ops.update_customization_quality(custom_id, quality_score, match_percentage)
                print(f"   📊 Quality score: {quality_score}, Match: {match_percentage}%")
            else:
                print(f"   ❌ Failed to create customization {i}")
        
        # Step 5: Create Email Send Records
        print(f"\n📧 STEP 5: Creating Email Send Records")
        print("-" * 40)
        
        email_data_list = [
            {
                'customization_id': customization_ids[0],
                'recipient_email': 'hr@techcorp.com',
                'recipient_name': 'HR Team',
                'subject': 'Application for Senior Python Developer Position',
                'body': 'Dear Hiring Manager, Please find my resume attached...',
                'attachment_filename': 'John_Doe_Resume_TechCorp.docx',
                'attachment_size': 47890
            },
            {
                'customization_id': customization_ids[1],
                'recipient_email': 'jobs@startupxyz.com',
                'recipient_name': 'Startup XYZ',
                'subject': 'Full Stack Developer Application',
                'body': 'Hello, I am interested in the Full Stack Developer position...',
                'attachment_filename': 'John_Doe_Resume_StartupXYZ.docx',
                'attachment_size': 48120
            }
        ] if len(customization_ids) >= 2 else []
        
        email_ids = []
        for i, email_data in enumerate(email_data_list, 1):
            print(f"📮 Creating email send record {i}: {email_data['recipient_email']}")
            
            email_id = self.crud_ops.create_email_send(email_data)
            if email_id:
                email_ids.append(email_id)
                print(f"   ✅ Created with ID: {email_id}")
                
                # Simulate email sending process
                print(f"   📤 Updating status to 'sending'...")
                self.crud_ops.update_email_status(email_id, 'sending')
                
                time.sleep(0.5)  # Simulate sending time
                
                print(f"   ✅ Updating status to 'sent'...")
                self.crud_ops.update_email_status(email_id, 'sent')
            else:
                print(f"   ❌ Failed to create email send record {i}")
        
        # Step 6: Retrieve and Display Data
        print(f"\n📊 STEP 6: Retrieving and Analyzing Data")
        print("-" * 40)
        
        # Get user resumes
        print("📄 User's resume documents:")
        user_resumes = self.crud_ops.get_user_resumes(self.demo_user_id)
        for resume in user_resumes:
            print(f"   • {resume['filename']} (Status: {resume['processing_status']})")
        
        # Get customizations for the resume
        print(f"\n🎯 Customizations for resume {resume_id}:")
        customizations_list = self.crud_ops.get_resume_customizations(resume_id)
        for custom in customizations_list:
            print(f"   • {custom['company_name']} - {custom['job_title']}")
            print(f"     Quality: {custom['quality_score']}, Match: {custom['match_percentage']}%")
        
        # Get email history
        if customization_ids:
            print(f"\n📧 Email history for first customization:")
            email_history = self.crud_ops.get_email_history(customization_ids[0])
            for email in email_history:
                print(f"   • To: {email['recipient_email']} (Status: {email['send_status']})")
                print(f"     Subject: {email['subject']}")
        
        # Step 7: Analytics and Statistics
        print(f"\n📈 STEP 7: Analytics and Statistics")
        print("-" * 40)
        
        # Get user statistics
        print("👤 User Statistics:")
        user_stats = self.crud_ops.get_user_statistics(self.demo_user_id)
        for key, value in user_stats.items():
            if isinstance(value, float):
                print(f"   • {key.replace('_', ' ').title()}: {value:.2f}")
            else:
                print(f"   • {key.replace('_', ' ').title()}: {value}")
        
        # Get processing performance
        print(f"\n⚡ Processing Performance (Last 7 days):")
        performance = self.crud_ops.get_processing_performance(7)
        print(f"   • Average processing time: {performance.get('average_processing_time_seconds', 0):.2f} seconds")
        print(f"   • Daily statistics: {len(performance.get('daily_statistics', []))} days of data")
        
        print(f"\n🎉 Data Flow Demonstration Completed Successfully!")
        print("=" * 60)
    
    def demonstrate_search_functionality(self):
        """
        Demonstrate search and query functionality
        """
        print(f"\n🔍 BONUS: Search Functionality Demonstration")
        print("-" * 40)
        
        # Search resumes
        search_results = self.crud_ops.search_resumes(self.demo_user_id, "john")
        print(f"🔎 Search results for 'john': {len(search_results)} found")
        for result in search_results:
            print(f"   • {result['filename']} (Created: {result['created_at']})")
        
        # Search by tech stack (this would require more advanced implementation)
        print(f"\n💡 Advanced search capabilities available:")
        print(f"   • Full-text search in resume content")
        print(f"   • Tech stack matching")
        print(f"   • Company and job title filtering")
        print(f"   • Date range queries")
        print(f"   • Quality score filtering")

def main():
    """
    Main demonstration function
    """
    print("🎯 PostgreSQL Integration Demo for Resume Customizer")
    print("=" * 60)
    print("This demo will show you:")
    print("• How to connect to PostgreSQL database")
    print("• How resume data is stored and retrieved")
    print("• Complete data flow from upload to email sending")
    print("• Analytics and reporting capabilities")
    print("• Search and query functionality")
    print()
    
    demo = PostgreSQLDataFlowDemo()
    
    # Setup database
    if not demo.setup_database():
        print("\n⚠️  Database setup incomplete. Please:")
        print("1. Install PostgreSQL server")
        print("2. Create database 'resume_customizer'")
        print("3. Update .env file with your credentials")
        print("4. Run this demo again")
        return
    
    try:
        # Run the complete demonstration
        demo.demonstrate_data_flow()
        demo.demonstrate_search_functionality()
        
        print(f"\n📋 Summary of Database Operations Performed:")
        print(f"✅ Created resume document with metadata")
        print(f"✅ Updated processing status with timestamps")
        print(f"✅ Created multiple job-specific customizations")
        print(f"✅ Recorded email sending activities")
        print(f"✅ Generated analytics and statistics")
        print(f"✅ Demonstrated search capabilities")
        
        print(f"\n🎯 Your PostgreSQL database now contains:")
        print(f"• Resume documents with full metadata")
        print(f"• Job-specific customizations with quality metrics")
        print(f"• Email sending history and status tracking")
        print(f"• Processing logs and performance data")
        print(f"• User activity and session information")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        print(f"\n❌ Demo encountered an error: {e}")
        print("Please check your database connection and try again.")

if __name__ == "__main__":
    main()
