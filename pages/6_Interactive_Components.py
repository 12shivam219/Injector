"""
Interactive UI Components

Enhanced interactive UI elements for the Resume Customizer application.
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import altair as alt
from typing import Dict, List, Any
import matplotlib.pyplot as plt

# Import from our UI components
from ui.pages.interactive_components import (
    show_data_visualization,
    show_interactive_forms,
    show_realtime_updates,
    show_advanced_components
)

# Page configuration
st.set_page_config(
    page_title="Interactive Components",
    page_icon="🔄",
    layout="wide"
)

# Main page content
st.title("🔄 Enhanced Interactive UI Components")
st.write("""
This page demonstrates modern, interactive UI elements integrated with the Resume Customizer application.
These components can help improve your resume customization workflow.
""")

# Create tabs for different component categories
tab1, tab2, tab3, tab4 = st.tabs([
    "Data Visualization", 
    "Interactive Forms", 
    "Real-time Updates",
    "Advanced Components"
])

with tab1:
    show_data_visualization()

with tab2:
    show_interactive_forms()

with tab3:
    show_realtime_updates()

with tab4:
    show_advanced_components()

# Footer with integration information
st.markdown("---")
st.markdown("""
### How to Use These Components

These interactive components are fully integrated with the Resume Customizer application and can be used to:

1. **Visualize resume data** - See patterns and trends in your resume customizations
2. **Create enhanced forms** - Use improved input methods for resume information
3. **Track processing in real-time** - Monitor resume processing with live updates
4. **Analyze resume compatibility** - Check how well your resume matches job requirements

To use these components in your workflow, navigate to the appropriate section in the main application.
""")

# Navigation buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("← Back to Resume Customizer"):
        st.switch_page("pages/1_Resume_Customizer.py")
with col2:
    if st.button("Go to Bulk Processor →"):
        st.switch_page("pages/2_Bulk_Processor.py")