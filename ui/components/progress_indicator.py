"""
Progress indicator components for the Resume Customizer application.
Provides UI components for displaying task progress to users.
"""

import streamlit as st
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta

from infrastructure.monitoring.progress import (
    TaskProgress, 
    TaskStatus, 
    get_progress_tracker
)

class ProgressIndicator:
    """Base class for progress indicators."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.progress_tracker = get_progress_tracker()
    
    def render(self):
        """Render the progress indicator."""
        raise NotImplementedError("Subclasses must implement render()")
    
    def get_progress(self) -> Optional[TaskProgress]:
        """Get the current progress of the task."""
        return self.progress_tracker.get_progress(self.task_id)
    
    def get_percentage(self) -> float:
        """Get the progress percentage."""
        progress = self.get_progress()
        if not progress or progress.total == 0:
            return 0.0
        return min(1.0, progress.current / progress.total)
    
    def get_estimated_completion(self) -> Optional[datetime]:
        """Get the estimated completion time."""
        return self.progress_tracker.estimate_completion(self.task_id)
    
    def format_time_remaining(self) -> str:
        """Format the remaining time as a string."""
        estimated = self.get_estimated_completion()
        if not estimated:
            return "Calculating..."
        
        remaining = estimated - datetime.now()
        if remaining.total_seconds() < 0:
            return "Almost done..."
        
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"~{hours}h {minutes}m remaining"
        elif minutes > 0:
            return f"~{minutes}m {seconds}s remaining"
        else:
            return f"~{seconds}s remaining"


class StreamlitProgressBar(ProgressIndicator):
    """Streamlit progress bar implementation."""
    
    def __init__(self, task_id: str, key_prefix: str = "progress"):
        super().__init__(task_id)
        self.key_prefix = key_prefix
        self.bar_key = f"{key_prefix}_{task_id}_bar"
        self.text_key = f"{key_prefix}_{task_id}_text"
        self.status_key = f"{key_prefix}_{task_id}_status"
    
    def render(self):
        """Render a Streamlit progress bar."""
        progress = self.get_progress()
        if not progress:
            st.warning(f"Task {self.task_id} not found")
            return
        
        percentage = self.get_percentage()
        
        # Display the progress bar
        st.progress(percentage, key=self.bar_key)
        
        # Display the description and percentage
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(progress.description, key=self.text_key)
        with col2:
            st.caption(f"{int(percentage * 100)}%")
        
        # Display status information
        if progress.status == TaskStatus.COMPLETED:
            st.success("Completed", icon="✅")
        elif progress.status == TaskStatus.FAILED:
            st.error(f"Failed: {progress.error}", icon="❌")
        elif progress.status == TaskStatus.CANCELLED:
            st.warning("Cancelled", icon="⚠️")
        elif progress.status == TaskStatus.IN_PROGRESS:
            st.info(self.format_time_remaining(), key=self.status_key)


class StreamlitSpinner(ProgressIndicator):
    """Streamlit spinner implementation for indeterminate progress."""
    
    def __init__(self, task_id: str, text: str = "Processing..."):
        super().__init__(task_id)
        self.text = text
    
    def render(self):
        """Render a Streamlit spinner."""
        progress = self.get_progress()
        if not progress:
            return
        
        if progress.status == TaskStatus.IN_PROGRESS:
            with st.spinner(self.text):
                st.caption(progress.description)
                time.sleep(0.1)  # Small delay to allow spinner to render
        elif progress.status == TaskStatus.COMPLETED:
            st.success("Completed", icon="✅")
        elif progress.status == TaskStatus.FAILED:
            st.error(f"Failed: {progress.error}", icon="❌")
        elif progress.status == TaskStatus.CANCELLED:
            st.warning("Cancelled", icon="⚠️")


class ProgressIndicatorFactory:
    """Factory for creating progress indicators."""
    
    @staticmethod
    def create_indicator(
        task_id: str, 
        indicator_type: str = "progress_bar",
        **kwargs
    ) -> ProgressIndicator:
        """Create a progress indicator of the specified type."""
        if indicator_type == "progress_bar":
            return StreamlitProgressBar(task_id, **kwargs)
        elif indicator_type == "spinner":
            return StreamlitSpinner(task_id, **kwargs)
        else:
            raise ValueError(f"Unknown indicator type: {indicator_type}")


def display_task_progress(task_id: str, indicator_type: str = "progress_bar", **kwargs):
    """Display progress for a specific task."""
    indicator = ProgressIndicatorFactory.create_indicator(
        task_id, 
        indicator_type,
        **kwargs
    )
    indicator.render()


def display_active_tasks(indicator_type: str = "progress_bar", **kwargs):
    """Display all active tasks."""
    progress_tracker = get_progress_tracker()
    active_tasks = progress_tracker.get_active_tasks()
    
    if not active_tasks:
        st.info("No active tasks")
        return
    
    for task in active_tasks:
        indicator = ProgressIndicatorFactory.create_indicator(
            task.task_id,
            indicator_type,
            **kwargs
        )
        with st.container():
            indicator.render()
            st.divider()