"""
Requirements Management Module for Resume Customizer
Handles CRUD operations for job requirements
"""
import streamlit as st
from typing import Dict, List, Optional, Any
import json
import os
from pathlib import Path
from datetime import datetime
from infrastructure.utilities.logger import get_logger

logger = get_logger()

class RequirementsManager:
    """Manages job requirements CRUD operations with dual backend support."""
    
    def __init__(self, storage_file: str = "requirements.json", use_database: bool = None):
        """Initialize RequirementsManager with storage file or database.
        
        Args:
            storage_file: JSON file path for file-based storage
            use_database: If True, use PostgreSQL; If False, use JSON; If None, auto-detect
        """
        self.storage_file = storage_file
        self.use_database = self._determine_backend(use_database)
        
        if self.use_database:
            try:
                from database import PostgreSQLRequirementsManager, setup_database_environment
                # Setup database environment
                env_result = setup_database_environment()
                if env_result['success']:
                    self.db_manager = PostgreSQLRequirementsManager()
                    logger.info("✅ Using PostgreSQL backend for requirements")
                else:
                    logger.warning("⚠️ PostgreSQL setup failed, falling back to JSON storage")
                    self.use_database = False
                    self.requirements = self._load_requirements()
            except ImportError:
                logger.warning("⚠️ PostgreSQL dependencies not available, using JSON storage")
                self.use_database = False
                self.requirements = self._load_requirements()
        else:
            self.requirements = self._load_requirements()
    
    def _determine_backend(self, use_database: bool = None) -> bool:
        """Determine which backend to use based on configuration and availability"""
        if use_database is not None:
            return use_database
        
        # Auto-detect: check for database environment variables
        import os
        db_vars = ['DATABASE_URL', 'DB_HOST', 'DATABASE_HOST', 'POSTGRES_HOST']
        has_db_config = any(os.getenv(var) for var in db_vars)
        
        if has_db_config:
            try:
                import psycopg2
                import sqlalchemy
                return True  # Database dependencies available and config present
            except ImportError:
                return False  # Database dependencies not available
        
        return False  # No database configuration found
        
    def _get_storage_path(self) -> Path:
        """Get the full path to the requirements storage file."""
        return Path(__file__).parent.parent / self.storage_file
    
    def _load_requirements(self) -> Dict[str, Dict[str, Any]]:
        """Load requirements from JSON file."""
        try:
            path = self._get_storage_path()
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading requirements: {e}")
        return {}
    
    def _save_requirements(self):
        """Save requirements to JSON file."""
        try:
            # Ensure all requirements have created_at field
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for req_id, req in self.requirements.items():
                if 'created_at' not in req:
                    req['created_at'] = current_time
                    logger.info(f"Added missing created_at for requirement {req_id}")
            
            path = self._get_storage_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.requirements, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving requirements: {e}")
            st.error("Failed to save requirements. Please check logs for details.")
    
    def create_requirement(self, requirement_data: Dict[str, Any]) -> str:
        """Create a new requirement with comprehensive data structure."""
        if self.use_database:
            return self.db_manager.create_requirement(requirement_data)
        
        # Original JSON-based implementation
        try:
            requirement_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            # Create a copy to avoid modifying the input dictionary
            requirement_data = requirement_data.copy()
            requirement_data.update({
                'id': requirement_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
            
            # Ensure all new comprehensive fields exist with proper structure
            
            # Basic requirement fields
            if 'req_status' not in requirement_data:
                requirement_data['req_status'] = 'New working'
            if 'applied_for' not in requirement_data:
                requirement_data['applied_for'] = 'Raju'
            if 'tax_type' not in requirement_data:
                requirement_data['tax_type'] = 'C2C'
            
            # Marketing comments
            if 'marketing_comments' not in requirement_data or not isinstance(requirement_data['marketing_comments'], list):
                requirement_data['marketing_comments'] = []
            
            # Vendor details
            if 'vendor_details' not in requirement_data:
                requirement_data['vendor_details'] = {
                    'vendor_company': '',
                    'vendor_person_name': '',
                    'vendor_phone_number': '',
                    'vendor_email': ''
                }
            
            # Job requirement info
            if 'job_requirement_info' not in requirement_data:
                requirement_data['job_requirement_info'] = {
                    'requirement_entered_date': datetime.now().isoformat(),
                    'got_requirement_from': 'Got from online resume',
                    'tech_stack': [],
                    'job_title': '',
                    'job_portal_link': '',
                    'primary_tech_stack': '',
                    'complete_job_description': ''
                }
            
            # Ensure tech_stack is a list
            if not isinstance(requirement_data['job_requirement_info'].get('tech_stack', []), list):
                requirement_data['job_requirement_info']['tech_stack'] = []
            
            # Legacy compatibility fields
            if 'vendor_info' not in requirement_data:
                requirement_data['vendor_info'] = {
                    'name': requirement_data.get('vendor_details', {}).get('vendor_person_name', ''),
                    'company': requirement_data.get('vendor_details', {}).get('vendor_company', ''),
                    'phone': requirement_data.get('vendor_details', {}).get('vendor_phone_number', ''),
                    'email': requirement_data.get('vendor_details', {}).get('vendor_email', '')
                }
            
            # Ensure consultants exists and is a list
            if 'consultants' not in requirement_data or not isinstance(requirement_data['consultants'], list):
                requirement_data['consultants'] = []
                
            self.requirements[requirement_id] = requirement_data
            self._save_requirements()
            logger.info(f"Created requirement {requirement_id} with comprehensive data structure")
            return requirement_id
        except Exception as e:
            logger.error(f"Error creating requirement: {e}")
            st.error("Failed to create requirement. Please check logs for details.")
            raise
    
    def get_requirement(self, requirement_id: str) -> Optional[Dict[str, Any]]:
        """Get a requirement by ID."""
        if self.use_database:
            return self.db_manager.get_requirement(requirement_id)
        return self.requirements.get(requirement_id)
    
    def update_requirement(self, requirement_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing requirement."""
        if self.use_database:
            return self.db_manager.update_requirement(requirement_id, update_data)
        
        # Original JSON-based implementation
        try:
            if requirement_id not in self.requirements:
                logger.error(f"Requirement with ID {requirement_id} not found")
                return False
            
            # Preserve created_at if it exists
            if 'created_at' in self.requirements[requirement_id]:
                update_data['created_at'] = self.requirements[requirement_id]['created_at']
                
            update_data['updated_at'] = datetime.now().isoformat()
            self.requirements[requirement_id].update(update_data)
            self._save_requirements()
            return True
        except Exception as e:
            logger.error(f"Error updating requirement {requirement_id}: {e}")
            st.error("Failed to update requirement. Please check logs for details.")
            return False
    
    def delete_requirement(self, requirement_id: str) -> bool:
        """Delete a requirement."""
        if self.use_database:
            return self.db_manager.delete_requirement(requirement_id)
        
        # Original JSON-based implementation
        if requirement_id in self.requirements:
            del self.requirements[requirement_id]
            self._save_requirements()
            return True
        return False
    
    def list_requirements(self) -> List[Dict[str, Any]]:
        """List all requirements."""
        if self.use_database:
            return self.db_manager.list_requirements()
        return list(self.requirements.values())
    
    def export_requirements(self) -> str:
        """Export all requirements as JSON string."""
        try:
            import json
            export_data = {
                'requirements': self.requirements,
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            return json.dumps(export_data, indent=2)
        except Exception as e:
            logger.error(f"Error exporting requirements: {e}")
            return ""
    
    def import_requirements(self, json_data: str, merge: bool = False) -> bool:
        """Import requirements from JSON string.
        
        Args:
            json_data: JSON string containing requirements data
            merge: If True, merge with existing data; if False, replace all
            
        Returns:
            True if import successful, False otherwise
        """
        try:
            import json
            data = json.loads(json_data)
            
            if 'requirements' not in data:
                logger.error("Invalid import data: missing 'requirements' key")
                return False
            
            imported_requirements = data['requirements']
            
            if not merge:
                # Replace all requirements
                self.requirements = imported_requirements
            else:
                # Merge with existing requirements
                for req_id, req_data in imported_requirements.items():
                    # Update timestamp to show it was imported
                    req_data['updated_at'] = datetime.now().isoformat()
                    req_data['imported'] = True
                    self.requirements[req_id] = req_data
            
            self._save_requirements()
            logger.info(f"Successfully imported {len(imported_requirements)} requirements")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return False
        except Exception as e:
            logger.error(f"Error importing requirements: {e}")
            return False


def render_requirement_form(requirement_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Render the comprehensive requirement form and return form data."""
    is_edit = requirement_data is not None
    
    # Get current time for timestamps
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Initialize form data with defaults or existing values
    form_data = {
        'created_at': requirement_data.get('created_at', current_time) if requirement_data else current_time,
        'updated_at': current_time,
        # Basic requirement info
        'created_at': requirement_data.get('created_at', current_time) if requirement_data else current_time,
        'req_status': 'New working',
        'applied_for': 'Raju',
        'next_step': '',
        'rate': '',
        'tax_type': 'C2C',
        'marketing_comments': [],
        'client_company': '',
        'prime_vendor_company': '',
        
        # Vendor Details
        'vendor_details': {
            'vendor_company': '',
            'vendor_person_name': '',
            'vendor_phone_number': '',
            'vendor_email': ''
        },
        
        # Job Requirement Info
        'job_requirement_info': {
            'requirement_entered_date': datetime.now().isoformat(),
            'got_requirement_from': 'Got from online resume',
            'tech_stack': [],
            'job_title': '',
            'job_portal_link': '',
            'primary_tech_stack': '',
            'complete_job_description': ''
        },
        
        # Legacy fields for backward compatibility
        'job_title': '',
        'client': '',
        'prime_vendor': '',
        'status': 'New working',
        'next_steps': '',
        'consultants': [],
        'vendor_info': {
            'name': '',
            'company': '',
            'phone': '',
            'email': ''
        },
        'interview_id': ''
    }
    
    if is_edit:
        # Update form data with existing requirement data
        form_data.update(requirement_data)
        
        # Ensure nested dictionaries are properly initialized
        if 'vendor_details' not in form_data:
            form_data['vendor_details'] = {
                'vendor_company': '',
                'vendor_person_name': '',
                'vendor_phone_number': '',
                'vendor_email': ''
            }
        if 'job_requirement_info' not in form_data:
            form_data['job_requirement_info'] = {
                'requirement_entered_date': datetime.now().isoformat(),
                'got_requirement_from': 'Got from online resume',
                'tech_stack': [],
                'job_title': '',
                'job_portal_link': '',
                'primary_tech_stack': '',
                'complete_job_description': ''
            }
        if 'marketing_comments' not in form_data:
            form_data['marketing_comments'] = []
        if 'consultants' not in form_data:
            form_data['consultants'] = []
        
        # Backward compatibility for legacy fields
        if 'vendor_info' not in form_data:
            form_data['vendor_info'] = {
                'name': '',
                'company': '',
                'phone': '',
                'email': ''
            }
    
    # Create comprehensive form
    with st.form(key='requirement_form'):
        st.subheader("📝 " + ("Edit" if is_edit else "Create New") + " Requirement")
        
        # Record number (auto-generated)
        if is_edit and 'id' in form_data:
            st.caption(f"Record #: {form_data['id']}")
        
        # Auto-captured date and time
        if is_edit and form_data.get('job_requirement_info', {}).get('requirement_entered_date'):
            st.caption(f"Requirement Entered: {form_data['job_requirement_info']['requirement_entered_date']}")
        else:
            current_time = datetime.now().isoformat()
            form_data['job_requirement_info']['requirement_entered_date'] = current_time
            st.caption(f"Requirement Entered: {current_time}")
        
        # Consolidated form layout - all sections in one form without tabs
        st.markdown("---")
        
        # Section 1: Basic Information
        st.markdown("### 📋 Basic Information")
        col1, col2 = st.columns(2)
        
        with col1:
            # 1. Req Status (Dropdown)
            status_options = ["New working", "Applied", "Cancelled", "Submitted", "Interviewed", "On Hold"]
            form_data['req_status'] = st.selectbox(
                "Req Status*",
                options=status_options,
                index=status_options.index(form_data.get('req_status', 'New working')) if form_data.get('req_status') in status_options else 0
            )
            
            # Update legacy status field for backward compatibility
            form_data['status'] = form_data['req_status']
            
            # 2. Applied For (Dropdown)
            applied_for_options = ["Raju", "Eric"]
            form_data['applied_for'] = st.selectbox(
                "Applied For*",
                options=applied_for_options,
                index=applied_for_options.index(form_data.get('applied_for', 'Raju')) if form_data.get('applied_for') in applied_for_options else 0
            )
            
            # 3. Next Step (Text Input)
            form_data['next_step'] = st.text_input(
                "Next Step",
                value=form_data.get('next_step', ''),
                placeholder="Describe the next step to take"
            )
            
            # Update legacy next_steps field
            form_data['next_steps'] = form_data['next_step']
            
            # 4. Rate (Text Input)
            form_data['rate'] = st.text_input(
                "Rate",
                value=form_data.get('rate', ''),
                placeholder="E.g., $85/hour, $120,000/year"
            )
            
            # 5. Tax Type (Dropdown)
            tax_type_options = ["C2C", "1099", "W2", "Fulltime"]
            form_data['tax_type'] = st.selectbox(
                "Tax Type*",
                options=tax_type_options,
                index=tax_type_options.index(form_data.get('tax_type', 'C2C')) if form_data.get('tax_type') in tax_type_options else 0
            )
        
        with col2:
            # 6. Marketing Person's Comment (Multi-comment functionality)
            st.markdown("**Marketing Person's Comments**")
            
            # Display existing comments
            existing_comments = form_data.get('marketing_comments', [])
            if existing_comments:
                with st.expander(f"📝 View Previous Comments ({len(existing_comments)})"):
                    for i, comment in enumerate(existing_comments):
                        comment_time = comment.get('timestamp', 'Unknown time')
                        comment_text = comment.get('comment', '')
                        st.markdown(f"**{comment_time}:**")
                        st.markdown(f"> {comment_text}")
                        st.markdown("---")
            
            # Add new comment
            new_comment = st.text_area(
                "Add New Comment",
                placeholder="Enter your marketing comment here...",
                height=100,
                key=f"new_comment_{form_data.get('id', 'new')}"
            )
            
            if new_comment.strip():
                if st.form_submit_button("➕ Add Comment", help="Add this comment to the requirement"):
                    new_comment_obj = {
                        'comment': new_comment.strip(),
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    if 'marketing_comments' not in form_data:
                        form_data['marketing_comments'] = []
                    form_data['marketing_comments'].append(new_comment_obj)
                    st.success("Comment added successfully!")
        
        # Section 2: Company Information
        st.markdown("---")
        st.markdown("### 🏢 Company Information")
        col1, col2 = st.columns(2)
        
        with col1:
            # 7. Client Company (Text Input)
            form_data['client_company'] = st.text_input(
                "Client Company*",
                value=form_data.get('client_company', ''),
                placeholder="Name of the client company"
            )
            
            # Update legacy client field
            form_data['client'] = form_data['client_company']
            
            # 8. Prime Vendor Company (Text Input)
            form_data['prime_vendor_company'] = st.text_input(
                "Prime Vendor Company",
                value=form_data.get('prime_vendor_company', ''),
                placeholder="Name of the prime vendor company"
            )
            
            # Update legacy prime_vendor field
            form_data['prime_vendor'] = form_data['prime_vendor_company']
        
        with col2:
            st.markdown("**👤 Vendor Details**")
            
            # 9.1 Vendor Company (Text Input)
            if 'vendor_details' not in form_data:
                form_data['vendor_details'] = {}
            form_data['vendor_details']['vendor_company'] = st.text_input(
                "Vendor Company",
                value=form_data.get('vendor_details', {}).get('vendor_company', ''),
                placeholder="Vendor company name"
            )
            
            # 9.2 Vendor Person Name (Text Input)
            form_data['vendor_details']['vendor_person_name'] = st.text_input(
                "Vendor Person Name",
                value=form_data.get('vendor_details', {}).get('vendor_person_name', ''),
                placeholder="Name of vendor contact person"
            )
            
            # 9.3 Vendor Phone Number (Text Input)
            form_data['vendor_details']['vendor_phone_number'] = st.text_input(
                "Vendor Phone Number",
                value=form_data.get('vendor_details', {}).get('vendor_phone_number', ''),
                placeholder="Vendor phone number"
            )
            
            # 9.4 Vendor Email (Text Input)
            form_data['vendor_details']['vendor_email'] = st.text_input(
                "Vendor Email",
                value=form_data.get('vendor_details', {}).get('vendor_email', ''),
                placeholder="Vendor email address"
            )
            
            # Update legacy vendor_info for backward compatibility
            if 'vendor_info' not in form_data:
                form_data['vendor_info'] = {}
            form_data['vendor_info']['name'] = form_data.get('vendor_details', {}).get('vendor_person_name', '')
            form_data['vendor_info']['company'] = form_data.get('vendor_details', {}).get('vendor_company', '')
            form_data['vendor_info']['phone'] = form_data.get('vendor_details', {}).get('vendor_phone_number', '')
            form_data['vendor_info']['email'] = form_data.get('vendor_details', {}).get('vendor_email', '')
        
        # Section 3: Job Details
        st.markdown("---")
        st.markdown("### 💼 Job Requirement Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 10.2 Got Requirement From (Dropdown)
            if 'job_requirement_info' not in form_data:
                form_data['job_requirement_info'] = {}
            got_requirement_options = ["Got from online resume", "Got through Job Portal"]
            form_data['job_requirement_info']['got_requirement_from'] = st.selectbox(
                "Got Requirement From*",
                options=got_requirement_options,
                index=got_requirement_options.index(form_data.get('job_requirement_info', {}).get('got_requirement_from', 'Got from online resume')) if form_data.get('job_requirement_info', {}).get('got_requirement_from') in got_requirement_options else 0
            )
            
            # 10.3 Tech Stack (Multi-select)
            tech_stack_options = [
                "Java", "Ruby on Rails", "React", "Node", "Angular", "AWS", "Databricks", "Delphi", "SDET", "HCL Commerce", "Python", 
                "Full Stack (Node, React, Angular)", "Full Stack (Java)", "PHP", "ReactNative"
            ]
            form_data['job_requirement_info']['tech_stack'] = st.multiselect(
                "Tech Stack",
                options=tech_stack_options,
                default=form_data.get('job_requirement_info', {}).get('tech_stack', []),
                help="Select all applicable technologies"
            )
            
            # 10.4 Job Title (Text Input)
            form_data['job_requirement_info']['job_title'] = st.text_input(
                "Job Title*",
                value=form_data.get('job_requirement_info', {}).get('job_title', ''),
                placeholder="E.g., Senior Software Engineer"
            )
            
            # Update legacy job_title field
            form_data['job_title'] = form_data['job_requirement_info']['job_title']
            
            # 10.5 Job Portal Link (Text Input / URL Field)
            form_data['job_requirement_info']['job_portal_link'] = st.text_input(
                "Job Portal Link",
                value=form_data.get('job_requirement_info', {}).get('job_portal_link', ''),
                placeholder="https://example.com/job-posting"
            )
        
        with col2:
            # 10.6 Primary Tech Stack (Text Input)
            form_data['job_requirement_info']['primary_tech_stack'] = st.text_input(
                "Primary Tech Stack",
                value=form_data.get('job_requirement_info', {}).get('primary_tech_stack', ''),
                placeholder="Main technology required for this role"
            )
            
            # 10.7 Complete Job Description (Textarea)
            form_data['job_requirement_info']['complete_job_description'] = st.text_area(
                "Complete Job Description",
                value=form_data.get('job_requirement_info', {}).get('complete_job_description', ''),
                height=200,
                placeholder="Paste the complete job description here..."
            )
            
            # Consultants Section (Legacy compatibility)
            st.markdown("**Applied For Consultants**")
            available_consultants = ['Raju', 'Eric']
            selected_consultants = st.multiselect(
                "Select Consultants",
                options=available_consultants,
                default=[form_data.get('applied_for', 'Raju')],  # Default to applied_for selection
                key=f"consultants_select_{form_data.get('id', 'new')}"
            )
            form_data['consultants'] = selected_consultants
        
        # Form submit button
        submitted = st.form_submit_button("💾 Save Requirement", help="Save this requirement with all the provided information")
        
        # Debug information
        if submitted:
            st.info(f"Form submitted! Processing data for: {form_data.get('job_requirement_info', {}).get('job_title', 'Unknown Job')}")
            st.info(f"Form data keys: {list(form_data.keys()) if isinstance(form_data, dict) else 'Not a dict'}")
    
    # Generate Interview ID button (only shown for Submitted status)
    if form_data.get('req_status') == 'Submitted' or form_data.get('status') == 'Submitted':
        if st.button("🎯 Generate Interview ID", key=f"gen_id_{form_data.get('id', 'new')}"):
            job_title = form_data.get('job_requirement_info', {}).get('job_title', '') or form_data.get('job_title', '')
            client = form_data.get('client_company', '') or form_data.get('client', '')
            interview_id = f"INT-{datetime.now().strftime('%Y%m%d')}-{len(job_title.split())}{len(client.split())}"
            interview_id_key = f"interview_id_{form_data.get('id', 'new')}"
            st.session_state[interview_id_key] = interview_id
            form_data['interview_id'] = interview_id
            st.success(f"Interview ID generated: {interview_id}")
            
        # Store the current interview ID in session state
        if 'interview_id' in form_data and form_data['interview_id']:
            interview_id_key = f"interview_id_{form_data.get('id', 'new')}"
            st.session_state[interview_id_key] = form_data['interview_id']
    
    # Process form submission
    if submitted:
        try:
            # Debug: Print form_data keys for debugging
            logger.info(f"Form submitted with keys: {list(form_data.keys()) if form_data else 'None'}")
            
            # Ensure form_data exists and has the required structure
            if not form_data:
                st.error("Form data is empty. Please try again.")
                return None
                
            # Ensure nested dictionaries exist
            if 'job_requirement_info' not in form_data or not isinstance(form_data['job_requirement_info'], dict):
                form_data['job_requirement_info'] = {
                    'job_title': '',
                    'requirement_entered_date': datetime.now().isoformat(),
                    'got_requirement_from': 'Got from online resume',
                    'tech_stack': [],
                    'job_portal_link': '',
                    'primary_tech_stack': '',
                    'complete_job_description': ''
                }
            
            if 'vendor_details' not in form_data or not isinstance(form_data['vendor_details'], dict):
                form_data['vendor_details'] = {
                    'vendor_company': '',
                    'vendor_person_name': '',
                    'vendor_phone_number': '',
                    'vendor_email': ''
                }
            
            # Basic validation
            job_title = form_data.get('job_requirement_info', {}).get('job_title', '') or form_data.get('job_title', '')
            client_company = form_data.get('client_company', '') or form_data.get('client', '')
            
            if not job_title.strip() or not client_company.strip():
                st.error("Please fill in all required fields (marked with *)")
                st.error(f"Job Title: '{job_title}', Client Company: '{client_company}'")
                return None
            
            # Handle new comment if provided
            new_comment_key = f"new_comment_{form_data.get('id', 'new')}"
            if new_comment_key in st.session_state and st.session_state[new_comment_key].strip():
                new_comment_text = st.session_state[new_comment_key].strip()
                new_comment_obj = {
                    'comment': new_comment_text,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                if 'marketing_comments' not in form_data:
                    form_data['marketing_comments'] = []
                form_data['marketing_comments'].append(new_comment_obj)
                # Clear the comment from session state after adding
                st.session_state[new_comment_key] = ""
                
            # Ensure all nested dictionaries exist with proper structure
            if 'vendor_details' not in form_data:
                form_data['vendor_details'] = {
                    'vendor_company': '',
                    'vendor_person_name': '',
                    'vendor_phone_number': '',
                    'vendor_email': ''
                }
                
            if 'job_requirement_info' not in form_data:
                form_data['job_requirement_info'] = {
                    'requirement_entered_date': datetime.now().isoformat(),
                    'got_requirement_from': 'Got from online resume',
                    'tech_stack': [],
                    'job_title': '',
                    'job_portal_link': '',
                    'primary_tech_stack': '',
                    'complete_job_description': ''
                }
            
            # Ensure legacy vendor_info exists for backward compatibility
            if 'vendor_info' not in form_data:
                form_data['vendor_info'] = {}
            
            # Update legacy fields for backward compatibility
            form_data['vendor_info']['name'] = form_data.get('vendor_details', {}).get('vendor_person_name', '')
            form_data['vendor_info']['company'] = form_data.get('vendor_details', {}).get('vendor_company', '')
            form_data['vendor_info']['phone'] = form_data.get('vendor_details', {}).get('vendor_phone_number', '')
            form_data['vendor_info']['email'] = form_data.get('vendor_details', {}).get('vendor_email', '')
            
            # Set timestamps
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not is_edit:
                form_data['created_at'] = current_time
                # Auto-capture requirement entered date if it's a new requirement
                form_data['job_requirement_info']['requirement_entered_date'] = datetime.now().isoformat()
            form_data['updated_at'] = current_time
            
            return form_data
            
        except Exception as e:
            logger.error(f"Error processing form submission: {e}")
            st.error("An error occurred while processing your request. Please try again.")
            return None
    
    return None

def render_requirements_list(requirements_manager: RequirementsManager):
    """Render the list of requirements with actions."""
    st.subheader("📋 Requirements List")
    
    requirements = requirements_manager.list_requirements()
    
    if not requirements:
        st.info("No requirements found. Create one using the form above.")
        return
    
    # Export/Import functionality
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("📄 Export All"):
            export_data = requirements_manager.export_requirements()
            if export_data:
                st.download_button(
                    label="💾 Download Requirements",
                    data=export_data,
                    file_name=f"requirements_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    help="Download all requirements as JSON file"
                )
                st.success("Requirements exported successfully!")
            else:
                st.error("Failed to export requirements")
    
    with col2:
        uploaded_file = st.file_uploader(
            "Import Requirements",
            type=["json"],
            help="Upload a JSON file containing requirements data",
            key="import_requirements"
        )
        
        if uploaded_file:
            import_data = uploaded_file.read().decode('utf-8')
            merge_option = st.checkbox("Merge with existing (otherwise replace all)", value=True, key="merge_requirements_option")
            
            if st.button("📅 Import Requirements"):
                success = requirements_manager.import_requirements(import_data, merge=merge_option)
                if success:
                    st.success("Requirements imported successfully!")
                    st.rerun()
                else:
                    st.error("Failed to import requirements. Please check the file format.")
    
    with col3:
        st.info(f"📊 Total Requirements: {len(requirements)}")
    
    st.markdown("---")
    
    # Sort requirements by creation date (newest first)
    try:
        requirements.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except:
        # If sorting by created_at fails, try to set a default created_at
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for req in requirements:
            if 'created_at' not in req:
                req['created_at'] = current_time
        requirements.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    for req in requirements:
        # Format the title with enhanced status, record number, job title and client
        status_emoji = {
            'New working': '🆕🔄',
            'New': '🆕',  # Keep for backward compatibility
            'Working': '🔄',  # Keep for backward compatibility
            'Applied': '📝',
            'Cancelled': '❌',
            'Submitted': '📤',
            'Interviewed': '✅',
            'On Hold': '⏸️',
            'No Response': '⏳'
        }.get(req.get('req_status', req.get('status', 'New working')), '📌')
        
        record_num = f"#{req.get('id', 'N/A').split('_')[-1]}" if 'id' in req else "#N/A"
        job_title = req.get('job_requirement_info', {}).get('job_title', '') or req.get('job_title', 'Untitled')
        client = req.get('client_company', '') or req.get('client', 'Unknown Client')
        title = f"{status_emoji} {record_num} - {job_title} @ {client}"
        
        with st.expander(title):
            # Create tabs for organized display of information
            info_tab1, info_tab2, info_tab3, comments_tab = st.tabs(["📋 Basic Info", "🏢 Company Details", "💼 Job Details", "💬 Comments"])
            
            with info_tab1:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Basic requirement information
                    st.markdown(f"**Req Status:** {req.get('req_status', req.get('status', 'Not specified'))}")
                    st.markdown(f"**Applied For:** {req.get('applied_for', 'Not specified')}")
                    
                    if req.get('next_step', req.get('next_steps')):
                        st.markdown(f"**Next Step:** {req.get('next_step', req.get('next_steps'))}")
                    
                    if req.get('rate'):
                        st.markdown(f"**Rate:** {req['rate']}")
                    
                    st.markdown(f"**Tax Type:** {req.get('tax_type', 'Not specified')}")
                    
                    # Consultants
                    if req.get('consultants'):
                        consultants_list = ', '.join([c for c in req['consultants'] if c.strip()])
                        st.markdown(f"**Consultants:** {consultants_list}")
                
                with col2:
                    # Timestamps
                    req_entered_date = req.get('job_requirement_info', {}).get('requirement_entered_date')
                    if req_entered_date:
                        st.caption(f"Requirement Entered: {req_entered_date}")
                    
                    if 'created_at' in req:
                        st.caption(f"Created: {req['created_at']}")
                    if 'updated_at' in req and req['updated_at'] != req.get('created_at'):
                        st.caption(f"Last Updated: {req['updated_at']}")
                    
                    # Interview ID (if exists)
                    if req.get('req_status') == 'Submitted' and req.get('interview_id'):
                        st.info(f"Interview ID: `{req['interview_id']}`")
            
            with info_tab2:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Company Information")
                    if req.get('client_company', req.get('client')):
                        st.markdown(f"**Client Company:** {req.get('client_company', req.get('client'))}")
                    
                    if req.get('prime_vendor_company', req.get('prime_vendor')):
                        st.markdown(f"**Prime Vendor Company:** {req.get('prime_vendor_company', req.get('prime_vendor'))}")
                
                with col2:
                    st.markdown("### Vendor Details")
                    vendor_details = req.get('vendor_details', {})
                    if vendor_details or req.get('vendor_info', {}):
                        # Check new vendor_details first, then fallback to legacy vendor_info
                        vendor_company = vendor_details.get('vendor_company', '') or req.get('vendor_info', {}).get('company', '')
                        vendor_name = vendor_details.get('vendor_person_name', '') or req.get('vendor_info', {}).get('name', '')
                        vendor_phone = vendor_details.get('vendor_phone_number', '') or req.get('vendor_info', {}).get('phone', '')
                        vendor_email = vendor_details.get('vendor_email', '') or req.get('vendor_info', {}).get('email', '')
                        
                        if vendor_company:
                            st.markdown(f"**Vendor Company:** {vendor_company}")
                        if vendor_name:
                            st.markdown(f"**Contact Person:** {vendor_name}")
                        if vendor_phone:
                            st.markdown(f"**Phone:** {vendor_phone}")
                        if vendor_email:
                            st.markdown(f"**Email:** {vendor_email}")
                    else:
                        st.info("No vendor details provided")
            
            with info_tab3:
                st.markdown("### Job Requirement Information")
                job_info = req.get('job_requirement_info', {})
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if job_info.get('got_requirement_from'):
                        st.markdown(f"**Got Requirement From:** {job_info['got_requirement_from']}")
                    
                    if job_info.get('tech_stack'):
                        tech_stack_display = ', '.join(job_info['tech_stack'])
                        st.markdown(f"**Tech Stack:** {tech_stack_display}")
                    
                    if job_info.get('primary_tech_stack'):
                        st.markdown(f"**Primary Tech Stack:** {job_info['primary_tech_stack']}")
                    
                    if job_info.get('job_portal_link'):
                        st.markdown(f"**Job Portal Link:** [View Job Posting]({job_info['job_portal_link']})")
                
                with col2:
                    if job_info.get('complete_job_description'):
                        with st.expander("📜 View Complete Job Description"):
                            st.text_area(
                                "Job Description", 
                                value=job_info['complete_job_description'], 
                                height=200, 
                                disabled=True,
                                key=f"job_desc_{req.get('id', 'unknown')}"
                            )
            
            with comments_tab:
                st.markdown("### Marketing Comments Timeline")
                
                marketing_comments = req.get('marketing_comments', [])
                if marketing_comments:
                    st.info(f"Total comments: {len(marketing_comments)}")
                    for i, comment in enumerate(reversed(marketing_comments)):  # Show newest first
                        comment_time = comment.get('timestamp', 'Unknown time')
                        comment_text = comment.get('comment', '')
                        
                        with st.container():
                            st.markdown(f"**{comment_time}**")
                            st.markdown(f"> {comment_text}")
                            if i < len(marketing_comments) - 1:  # Don't show divider after last comment
                                st.markdown("---")
                
                else:
                    st.info("No comments added yet")
                
                # Option to add new comment (this will open edit mode)
                if st.button(f"➕ Add Comment", key=f"add_comment_{req.get('id')}"):
                    st.session_state.editing_requirement = req
                    st.info("Opening requirement for adding comment...")
                    # st.rerun()  # Commented out to prevent tab switching
            
            # Action buttons at the bottom of each requirement
            st.markdown("---")
            action_col1, action_col2, action_col3 = st.columns([1, 1, 2])
            
            with action_col1:
                if st.button("✏️ Edit", key=f"edit_{req['id']}", help="Edit this requirement"):
                    st.session_state.editing_requirement = req
                    st.info("Opening requirement for editing...")
                    # st.rerun()  # Commented out to prevent tab switching
            
            with action_col2:
                if st.button("🗑️ Delete", key=f"delete_{req['id']}", help="Delete this requirement"):
                    # Add confirmation
                    if st.button(f"⚠️ Confirm Delete", key=f"confirm_delete_{req['id']}", help="Click to confirm deletion"):
                        job_title = req.get('job_requirement_info', {}).get('job_title', '') or req.get('job_title', 'Untitled')
                        if requirements_manager.delete_requirement(req['id']):
                            st.success(f"Successfully deleted requirement: {job_title}")
                            # st.rerun()  # Commented out to prevent issues
                        else:
                            st.error("Failed to delete requirement")
            
            with action_col3:
                # Display requirement summary stats
                comment_count = len(req.get('marketing_comments', []))
                tech_count = len(req.get('job_requirement_info', {}).get('tech_stack', []))
                st.caption(f"💬 {comment_count} comments | 🔧 {tech_count} tech stacks")



