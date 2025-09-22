"""
Requirements Management Page - Job requirements and resume customization
"""

import streamlit as st

# Safe rerun helper: some Streamlit versions remove `experimental_rerun`.
def _safe_rerun():
    rerun = getattr(st, 'experimental_rerun', None)
    if callable(rerun):
        try:
            rerun()
        except Exception:
            # Best-effort fallback: stop the script to allow next interaction to rerun
            try:
                st.stop()
            except Exception:
                pass
    else:
        try:
            st.stop()
        except Exception:
            pass

# Import the shared bootstrap
try:
    from infrastructure.app.app_bootstrap import initialize_app, get_cached_services, get_cached_logger, get_cached_requirements_manager
    app_initialized = True
except ImportError:
    app_initialized = False

if app_initialized:
    # Initialize the application
    initialize_app()
    services = get_cached_services()
    logger = get_cached_logger()
    
    # Add logout button
    from ui.secure_components import SecureUIComponents
    secure_ui = SecureUIComponents()
    secure_ui.render_logout_button()
    
    # Set page title
    st.title("📋 Requirements Manager")
    st.markdown("📝 **Create and manage job requirements to customize your resume for specific positions**")
    
    # Initialize requirements manager
    requirements_manager = services.get('requirements_manager')
    
    if requirements_manager is None:
        try:
            requirements_manager = get_cached_requirements_manager()
        except:
            requirements_manager = None
    
    if requirements_manager is None:
        st.error("❌ Requirements manager not available. Please check that all dependencies are installed.")
        st.info("📝 The requirements feature requires database connectivity and proper configuration.")
        
        with st.expander("🔧 Manual Requirements Input"):
            st.markdown("### Basic Requirements Interface")
            st.text_area("Job Description", placeholder="Paste job description here...", height=200)
            st.text_area("Required Skills", placeholder="List required skills...", height=100)
            st.button("Save Requirement (Placeholder)", key="3_Requirements_save_requirement__placeholder", disabled=True)
            st.info("💡 Full requirements management will be available once the database is properly configured.")
    
    else:
        # Store in session state for consistency
        if 'requirements_manager' not in st.session_state:
            st.session_state.requirements_manager = requirements_manager
        
        logger.info("Requirements tab rendered successfully")
        
        # Check if requirements functions are available
        try:
            from ui.requirements_manager import render_requirement_form, render_requirements_list
            requirements_functions_available = True
        except ImportError:
            requirements_functions_available = False
        
        if not requirements_functions_available:
            st.error("❌ Requirements management functions not available")
            st.info("📝 Basic requirements interface will be shown instead")
            
            col1, col2 = st.columns(2)
            with col1:
                st.text_area("Job Description", placeholder="Paste job description here...", height=200)
                with col2:
                    st.text_area("Required Skills", placeholder="List required skills...", height=100)
            
                st.button("Save Requirement (Placeholder)", key="3_Requirements_save_requirement__placeholder", disabled=True)
        
        else:
            # Main requirements interface
            st.markdown("---")
    
            # Tabs for different views
            # If a recently created requirement exists and show_view_tab is True, show the view content immediately
            show_view = st.session_state.get('show_view_tab', False)
            tab1, tab2 = st.tabs(["📝 Create/Edit Requirement", "📋 View Requirements"])

            # Track whether the View tab content was already rendered to avoid duplicating widgets
            view_rendered = False

            if show_view:
                # Clear the flag and immediately render the View tab below
                st.session_state['show_view_tab'] = False
                with tab2:
                    st.markdown("### 📋 Manage Existing Requirements")
                    try:
                        render_requirements_list(st.session_state.requirements_manager)
                        view_rendered = True
                    except Exception as e:
                        st.error(f"❌ Error loading requirements list: {str(e)}")
                        st.info("🔄 Please try refreshing the page or check the application logs.")
                # Provide a link/info back to create tab
                st.info("✅ Requirement created. Use the View tab to manage it.")
            else:
                with tab1:
                    st.markdown("### ✨ Create New Requirement")

                    # Check if we're editing an existing requirement
                    edit_id = st.query_params.get("edit")
                    requirement_to_edit = None

                    if edit_id and 'requirements_manager' in st.session_state:
                        try:
                            requirement_to_edit = st.session_state.requirements_manager.get_requirement(edit_id)
                            if not requirement_to_edit:
                                st.warning("⚠️ The requirement you're trying to edit doesn't exist.")
                            else:
                                st.info(f"📝 Editing requirement: {requirement_to_edit.get('job_title', 'Unknown')}")
                        except Exception as e:
                            st.warning(f"⚠️ Could not load requirement for editing: {str(e)}")

                    # Render the form
                    try:
                        form_data = render_requirement_form(requirement_to_edit)
                    except Exception as e:
                        st.error(f"❌ Error rendering requirement form: {str(e)}")
                        form_data = None

                    # Handle form submission
                    # Defensive check: ensure form_data is a dict with required keys
                    def _is_valid_form_data(fd):
                        if not fd or not isinstance(fd, dict):
                            return False
                        jt = fd.get('job_requirement_info', {}).get('job_title') or fd.get('job_title')
                        cc = fd.get('client_company') or fd.get('client')
                        return bool(jt and jt.strip() and cc and cc.strip())

                    if form_data and _is_valid_form_data(form_data):
                        try:
                            if requirement_to_edit:
                                # Update existing requirement
                                if st.session_state.requirements_manager.update_requirement(edit_id, form_data):
                                    st.success("✅ Requirement updated successfully!")
                                    st.balloons()
                                    # Keep the user on the same tab and refresh the list
                                    _safe_rerun()
                                else:
                                    st.error("❌ Failed to update requirement. It may have been deleted.")
                            else:
                                # Create new requirement
                                requirement_id = st.session_state.requirements_manager.create_requirement(form_data)
                                if requirement_id:
                                    # Store last created id so view can highlight it
                                    st.session_state['last_created_requirement_id'] = requirement_id
                                    st.success("✅ Requirement created successfully!")
                                    st.info(f"📝 Requirement ID: {requirement_id}")
                                    st.balloons()
                                    # Immediately render the View tab content so the user sees the new item
                                    try:
                                        with tab2:
                                            render_requirements_list(st.session_state.requirements_manager)
                                            # Mark that we've already rendered the view to avoid duplicate widgets
                                            view_rendered = True
                                    except Exception as _e:
                                        # If immediate rendering fails, fall back to set the flag for next run
                                        st.session_state['show_view_tab'] = True
                                else:
                                    st.error("❌ Failed to create requirement. Please try again.")
                        except Exception as e:
                            st.error(f"❌ An error occurred: {str(e)}")
                            logger.error(f"Error saving requirement: {str(e)}")
    
            with tab2:
                st.markdown("### 📋 Manage Existing Requirements")

                # Avoid calling render_requirements_list twice on the same run which can create duplicate widget keys
                if not view_rendered:
                    try:
                        render_requirements_list(st.session_state.requirements_manager)
                    except Exception as e:
                        st.error(f"❌ Error loading requirements list: {str(e)}")
                        st.info("🔄 Please try refreshing the page or check the application logs.")
                        
                        # Provide basic fallback interface
                        st.markdown("---")
                        st.markdown("### 🔧 Basic Requirements Viewer")
                        
                        if st.button("🔄 Reload Requirements", key="reload_requirements"):
                            st.rerun()
                        
                        st.info("💡 If issues persist, please check the database connection and configuration.")
                else:
                    st.info("🔎 View tab already rendered (recently created requirement highlighted).")

else:
    # Fallback display when bootstrap not available
    st.error("❌ Application bootstrap not available. Please ensure app_bootstrap.py is configured correctly.")
    st.info("📝 This page requires the main application to be properly configured.")