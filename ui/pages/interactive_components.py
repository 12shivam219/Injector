"""
Interactive UI Components Demo

This page showcases enhanced interactive UI elements for the application.
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import altair as alt
from typing import Dict, List, Any
import matplotlib.pyplot as plt
from PIL import Image
import io

def interactive_components_page():
    """Render the interactive components demo page"""
    
    st.title("Enhanced Interactive UI Components")
    st.write("""
    This page demonstrates modern, interactive UI elements that can be used throughout the application.
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

def show_data_visualization():
    """Show interactive data visualization components"""
    st.header("Interactive Data Visualization")
    st.write("""
    Modern data visualization components with interactive features.
    """)
    
    # Sample data
    chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['Resume Quality', 'Interview Success', 'Job Offers']
    )
    
    # Interactive chart selection
    chart_type = st.selectbox(
        "Select Chart Type",
        ["Line Chart", "Bar Chart", "Area Chart", "Scatter Plot", "Heatmap"]
    )
    
    if chart_type == "Line Chart":
        st.line_chart(chart_data)
    elif chart_type == "Bar Chart":
        st.bar_chart(chart_data)
    elif chart_type == "Area Chart":
        st.area_chart(chart_data)
    elif chart_type == "Scatter Plot":
        # Create a scatter plot with Altair
        scatter = alt.Chart(chart_data.reset_index()).transform_fold(
            ['Resume Quality', 'Interview Success', 'Job Offers'],
            as_=['Metric', 'Value']
        ).mark_circle(size=60).encode(
            x='index:Q',
            y='Value:Q',
            color='Metric:N',
            tooltip=['index', 'Value', 'Metric']
        ).interactive()
        st.altair_chart(scatter, use_container_width=True)
    elif chart_type == "Heatmap":
        # Create a correlation heatmap
        corr = chart_data.corr()
        fig, ax = plt.subplots()
        im = ax.imshow(corr, cmap='coolwarm')
        ax.set_xticks(np.arange(len(corr.columns)))
        ax.set_yticks(np.arange(len(corr.columns)))
        ax.set_xticklabels(corr.columns)
        ax.set_yticklabels(corr.columns)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                text = ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", color="black")
        ax.set_title("Correlation Heatmap")
        fig.tight_layout()
        st.pyplot(fig)
    
    # Interactive filtering
    st.subheader("Interactive Filtering")
    
    col1, col2 = st.columns(2)
    with col1:
        min_value = st.slider("Filter Minimum Value", -3.0, 3.0, -2.0, 0.1)
    with col2:
        max_value = st.slider("Filter Maximum Value", -3.0, 3.0, 2.0, 0.1)
    
    filtered_data = chart_data[(chart_data > min_value).all(axis=1) & (chart_data < max_value).all(axis=1)]
    st.write("Filtered Data:")
    st.dataframe(filtered_data.style.highlight_max(axis=0), use_container_width=True)

def show_interactive_forms():
    """Show interactive form components"""
    st.header("Interactive Forms")
    st.write("""
    Enhanced form components with validation and real-time feedback.
    """)
    
    with st.form("enhanced_form"):
        st.subheader("Resume Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", placeholder="John Doe")
            email = st.text_input("Email", placeholder="john.doe@example.com")
            
            # Dropdown with search
            options = ["Software Engineer", "Data Scientist", "Product Manager", 
                      "UX Designer", "DevOps Engineer", "Project Manager"]
            role = st.selectbox("Current Role", options, index=0)
        
        with col2:
            experience = st.slider("Years of Experience", 0, 20, 5)
            
            # Multi-select with chips
            skills = st.multiselect(
                "Select Skills",
                ["Python", "JavaScript", "React", "SQL", "AWS", "Docker", "Kubernetes", 
                 "Machine Learning", "Data Analysis", "UI/UX", "Project Management"]
            )
            
            # Date input
            availability = st.date_input("Available From")
        
        # Text area with character count
        cover_letter = st.text_area("Cover Letter", height=150, 
                                   placeholder="Write a brief cover letter...")
        st.caption(f"Character count: {len(cover_letter)}/500")
        
        # File upload with preview
        uploaded_file = st.file_uploader("Upload Resume", type=["pdf", "docx"])
        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")
            
        # Form submission
        submitted = st.form_submit_button("Submit Application")
        
    if submitted:
        if not name or not email or not skills:
            st.error("Please fill in all required fields")
        else:
            st.success("Form submitted successfully!")
            st.json({
                "name": name,
                "email": email,
                "role": role,
                "experience": experience,
                "skills": skills,
                "availability": str(availability),
                "cover_letter": cover_letter,
                "resume_file": uploaded_file.name if uploaded_file else None
            })

def show_realtime_updates():
    """Show components with real-time updates"""
    st.header("Real-time Updates")
    st.write("""
    Components that update in real-time to provide immediate feedback.
    """)
    
    # Progress tracker
    st.subheader("Resume Processing Progress")
    
    if st.button("Start Processing"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simulate a process with multiple steps
        steps = [
            "Parsing document...",
            "Extracting skills...",
            "Analyzing experience...",
            "Formatting content...",
            "Generating recommendations..."
        ]
        
        for i, step in enumerate(steps):
            # Update status text
            status_text.text(step)
            
            # Update progress bar
            progress = (i + 1) / len(steps)
            progress_bar.progress(progress)
            
            # Simulate processing time
            time.sleep(0.5)
        
        status_text.text("Processing complete!")
        st.success("Resume processed successfully!")
    
    # Real-time chart
    st.subheader("Real-time Data Monitoring")
    
    chart_placeholder = st.empty()
    
    if st.button("Start Monitoring"):
        for i in range(1, 101):
            # Simulate real-time data
            data = pd.DataFrame({
                'index': range(i),
                'value': np.random.randn(i).cumsum()
            })
            
            # Update chart
            chart = alt.Chart(data).mark_line().encode(
                x='index',
                y='value'
            ).properties(
                width='container',
                height=300,
                title='Real-time Data Stream'
            )
            
            chart_placeholder.altair_chart(chart, use_container_width=True)
            
            # Slow down the updates
            time.sleep(0.1)
            
            # Stop after 100 iterations
            if i >= 100:
                break

def show_advanced_components():
    """Show advanced UI components"""
    st.header("Advanced Components")
    st.write("""
    Advanced UI components for enhanced user experience.
    """)
    
    # Interactive data editor
    st.subheader("Interactive Data Editor")
    
    sample_data = pd.DataFrame({
        'Name': ['John Doe', 'Jane Smith', 'Robert Johnson'],
        'Role': ['Software Engineer', 'Data Scientist', 'Product Manager'],
        'Experience': [5, 7, 10],
        'Skills': ['Python, JavaScript', 'Python, R, SQL', 'Agile, Jira']
    })
    
    edited_data = st.data_editor(
        sample_data,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("Save Changes"):
        st.success("Data saved successfully!")
        st.write("Updated Data:")
        st.dataframe(edited_data)
    
    # Tabs within tabs (nested tabs)
    st.subheader("Resume Analysis Tools")
    
    inner_tab1, inner_tab2, inner_tab3 = st.tabs([
        "Skill Analysis", "Experience Matcher", "ATS Compatibility"
    ])
    
    with inner_tab1:
        st.write("Analyze and visualize skills from resumes")
        
        # Sample skill data
        skills_data = pd.DataFrame({
            'Skill': ['Python', 'JavaScript', 'SQL', 'AWS', 'React', 'Docker'],
            'Frequency': [85, 65, 72, 48, 55, 42]
        })
        
        # Create horizontal bar chart
        chart = alt.Chart(skills_data).mark_bar().encode(
            x='Frequency',
            y=alt.Y('Skill', sort='-x'),
            color=alt.Color('Frequency', scale=alt.Scale(scheme='viridis')),
            tooltip=['Skill', 'Frequency']
        ).properties(
            width='container',
            height=300,
            title='Skills Frequency Analysis'
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    with inner_tab2:
        st.write("Match resume experience with job requirements")
        
        # Job requirements input
        job_requirements = st.text_area(
            "Enter Job Requirements",
            value="5+ years of Python development\nExperience with cloud platforms (AWS/Azure)\nKnowledge of CI/CD pipelines\nAgile development methodology",
            height=100
        )
        
        # Resume experience input
        resume_experience = st.text_area(
            "Enter Resume Experience",
            value="7 years of Python and JavaScript development\nAWS certified developer\nImplemented CI/CD pipelines using Jenkins\nScrum master certification",
            height=100
        )
        
        if st.button("Analyze Match"):
            # Simulate matching analysis
            st.write("### Match Analysis")
            
            match_results = [
                {"requirement": "Python development", "match": 95, "status": "Excellent"},
                {"requirement": "Cloud platforms", "match": 85, "status": "Good"},
                {"requirement": "CI/CD pipelines", "match": 80, "status": "Good"},
                {"requirement": "Agile methodology", "match": 90, "status": "Excellent"}
            ]
            
            # Display results
            for result in match_results:
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(result["requirement"])
                col2.metric("Match", f"{result['match']}%")
                if result["match"] >= 90:
                    col3.success(result["status"])
                elif result["match"] >= 70:
                    col3.info(result["status"])
                else:
                    col3.warning(result["status"])
            
            # Overall match
            overall_match = sum(r["match"] for r in match_results) / len(match_results)
            st.metric("Overall Match", f"{overall_match:.1f}%")
    
    with inner_tab3:
        st.write("Check resume compatibility with Applicant Tracking Systems")
        
        # File uploader for resume
        uploaded_resume = st.file_uploader("Upload Resume for ATS Check", type=["pdf", "docx"])
        
        if uploaded_resume is not None:
            st.success(f"Uploaded: {uploaded_resume.name}")
            
            # Simulate ATS analysis
            st.write("### ATS Compatibility Analysis")
            
            # Create sample metrics
            ats_metrics = {
                "Keyword Optimization": 85,
                "Format Compatibility": 92,
                "Section Structure": 78,
                "Contact Information": 100,
                "File Format": 95
            }
            
            # Display metrics
            col1, col2 = st.columns(2)
            
            with col1:
                for metric, score in list(ats_metrics.items())[:3]:
                    st.metric(metric, f"{score}%")
            
            with col2:
                for metric, score in list(ats_metrics.items())[3:]:
                    st.metric(metric, f"{score}%")
            
            # Overall score
            overall_score = sum(ats_metrics.values()) / len(ats_metrics)
            
            # Create gauge chart for overall score
            fig, ax = plt.subplots(figsize=(4, 4), subplot_kw={'projection': 'polar'})
            
            # Convert percentage to radians (0-100% -> 0-180 degrees -> 0-π radians)
            theta = np.linspace(0, np.pi, 100)
            r = np.ones_like(theta)
            
            # Plot background (gray)
            ax.fill_between(theta, 0, r, color='lightgray', alpha=0.5)
            
            # Plot score (colored based on value)
            score_theta = np.linspace(0, np.pi * overall_score / 100, 100)
            score_r = np.ones_like(score_theta)
            
            if overall_score >= 90:
                color = 'green'
            elif overall_score >= 70:
                color = 'orange'
            else:
                color = 'red'
                
            ax.fill_between(score_theta, 0, score_r, color=color, alpha=0.7)
            
            # Remove unnecessary elements
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['polar'].set_visible(False)
            
            # Add score text in the middle
            ax.text(0, 0, f"{overall_score:.1f}%", ha='center', va='center', fontsize=20, fontweight='bold')
            
            # Set limits
            ax.set_thetamin(0)
            ax.set_thetamax(180)
            
            st.pyplot(fig)
            
            # Recommendations
            st.subheader("Recommendations")
            recommendations = [
                "Add more industry-specific keywords",
                "Ensure all dates are in consistent format",
                "Add measurable achievements to experience section"
            ]
            
            for rec in recommendations:
                st.write(f"• {rec}")

if __name__ == "__main__":
    interactive_components_page()