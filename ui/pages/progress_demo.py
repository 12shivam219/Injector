"""
Demo page for progress indicators in the Resume Customizer application.
"""

import streamlit as st
import time
import threading
import uuid
from datetime import datetime

from infrastructure.monitoring.progress import (
    get_progress_tracker,
    TaskStatus
)
from ui.components.progress_indicator import (
    display_task_progress,
    display_active_tasks
)

def run_demo_task(task_id, total_steps=100, step_time=0.1):
    """Run a demo task that updates progress over time."""
    progress_tracker = get_progress_tracker()
    
    try:
        # Start the task
        progress_tracker.start_task(
            task_id=task_id,
            description="Processing resume data...",
            total=total_steps
        )
        
        # Simulate work with progress updates
        for i in range(1, total_steps + 1):
            time.sleep(step_time)
            progress_tracker.update_progress(
                task_id=task_id,
                current=i,
                description=f"Processing step {i} of {total_steps}..."
            )
            
            # Simulate random failure (10% chance at 30% progress)
            if i == int(total_steps * 0.3) and task_id.endswith('fail'):
                progress_tracker.fail_task(task_id, "Simulated error occurred")
                return
                
            # Simulate random cancellation (at 60% progress)
            if i == int(total_steps * 0.6) and task_id.endswith('cancel'):
                progress_tracker.cancel_task(task_id)
                return
        
        # Complete the task
        progress_tracker.complete_task(task_id)
        
    except Exception as e:
        progress_tracker.fail_task(task_id, str(e))


def progress_demo_page():
    """Render the progress demo page."""
    st.title("Progress Indicators Demo")
    st.write("""
    This page demonstrates the progress indicator components for long-running operations.
    You can start different types of tasks and see how the progress is displayed.
    """)
    
    # Demo controls
    st.subheader("Start Demo Tasks")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start Normal Task", key="btn_normal"):
            task_id = f"demo_{uuid.uuid4()}"
            threading.Thread(
                target=run_demo_task,
                args=(task_id, 100, 0.1),
                daemon=True
            ).start()
            st.session_state["last_task_id"] = task_id
            st.rerun()
    
    with col2:
        if st.button("Start Failing Task", key="btn_fail"):
            task_id = f"demo_{uuid.uuid4()}_fail"
            threading.Thread(
                target=run_demo_task,
                args=(task_id, 100, 0.1),
                daemon=True
            ).start()
            st.session_state["last_task_id"] = task_id
            st.rerun()
    
    with col3:
        if st.button("Start Cancelling Task", key="btn_cancel"):
            task_id = f"demo_{uuid.uuid4()}_cancel"
            threading.Thread(
                target=run_demo_task,
                args=(task_id, 100, 0.1),
                daemon=True
            ).start()
            st.session_state["last_task_id"] = task_id
            st.rerun()
    
    # Display progress indicators
    st.subheader("Active Tasks")
    display_active_tasks()
    
    # Display the last started task specifically
    if "last_task_id" in st.session_state:
        st.subheader("Last Started Task")
        display_task_progress(st.session_state["last_task_id"])
    
    # Different indicator types demo
    st.subheader("Indicator Types")
    
    tab1, tab2 = st.tabs(["Progress Bar", "Spinner"])
    
    with tab1:
        if st.button("Start Progress Bar Demo", key="btn_bar"):
            task_id = f"demo_bar_{uuid.uuid4()}"
            threading.Thread(
                target=run_demo_task,
                args=(task_id, 100, 0.1),
                daemon=True
            ).start()
            st.session_state["bar_task_id"] = task_id
            st.rerun()
            
        if "bar_task_id" in st.session_state:
            display_task_progress(
                st.session_state["bar_task_id"],
                indicator_type="progress_bar"
            )
    
    with tab2:
        if st.button("Start Spinner Demo", key="btn_spinner"):
            task_id = f"demo_spinner_{uuid.uuid4()}"
            threading.Thread(
                target=run_demo_task,
                args=(task_id, 100, 0.1),
                daemon=True
            ).start()
            st.session_state["spinner_task_id"] = task_id
            st.rerun()
            
        if "spinner_task_id" in st.session_state:
            display_task_progress(
                st.session_state["spinner_task_id"],
                indicator_type="spinner",
                text="Processing with spinner..."
            )
    
    # Auto-refresh the page to update progress
    if st.checkbox("Auto-refresh", value=True):
        st.empty()
        time.sleep(1)
        st.rerun()


# Run the demo page
progress_demo_page()