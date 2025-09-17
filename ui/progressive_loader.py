"""
Progressive Loading Module for Resume Customizer
Implements progressive loading for large file lists and heavy components
"""

import streamlit as st
from typing import List, Any, Dict, Optional
import time
from performance_optimizations import perf_monitor, performance_timer

class ProgressiveLoader:
    """Handles progressive loading of large datasets and components."""
    
    def __init__(self, batch_size: int = 5, delay_ms: int = 50):
        self.batch_size = batch_size
        self.delay_ms = delay_ms / 1000  # Convert to seconds
    
    @performance_timer
    def render_file_list_progressive(self, files: List[Any], render_func, key_prefix: str = "file"):
        """Progressively render a list of files to avoid UI blocking."""
        if not files:
            st.info("📁 No files to display")
            return
        
        # Initialize progressive loading state
        if f"{key_prefix}_loaded_count" not in st.session_state:
            st.session_state[f"{key_prefix}_loaded_count"] = min(self.batch_size, len(files))
        
        loaded_count = st.session_state[f"{key_prefix}_loaded_count"]
        
        # Show progress indicator
        if loaded_count < len(files):
            progress = loaded_count / len(files)
            st.progress(progress, text=f"Loading files... ({loaded_count}/{len(files)})")
        
        # Render loaded files
        for i in range(loaded_count):
            if i < len(files):
                with st.container():
                    render_func(files[i], i)
        
        # Load more button or auto-load
        if loaded_count < len(files):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(f"📄 Load More Files ({len(files) - loaded_count} remaining)", 
                           key=f"{key_prefix}_load_more", 
                           use_container_width=True):
                    # Load next batch instantly
                    remaining_files = len(files) - loaded_count
                    next_batch = min(self.batch_size * 2, remaining_files)  # Load more at once
                    st.session_state[f"{key_prefix}_loaded_count"] += next_batch
                    st.rerun()
        else:
            st.success(f"✅ All {len(files)} files loaded successfully!")
    
    def render_tabs_progressive(self, tab_data: List[Dict], max_initial_tabs: int = 3):
        """Progressively render tabs to avoid initial load delays."""
        if not tab_data:
            return
        
        # Show initial tabs
        initial_tabs = tab_data[:max_initial_tabs]
        remaining_tabs = tab_data[max_initial_tabs:]
        
        # Create initial tab structure
        tab_labels = [item['label'] for item in initial_tabs]
        if remaining_tabs:
            tab_labels.append(f"➕ More ({len(remaining_tabs)})")
        
        tabs = st.tabs(tab_labels)
        
        # Render initial tabs
        for i, tab_info in enumerate(initial_tabs):
            with tabs[i]:
                tab_info['render_func']()
        
        # Handle "More" tab
        if remaining_tabs:
            with tabs[-1]:
                st.markdown("### 📋 Additional Files")
                
                # Progressive loading for remaining tabs
                self.render_file_list_progressive(
                    remaining_tabs,
                    lambda item, idx: self._render_tab_content(item, idx),
                    "additional_tabs"
                )
    
    def _render_tab_content(self, tab_info: Dict, index: int):
        """Render individual tab content."""
        with st.expander(f"📄 {tab_info['label']}", expanded=index == 0):
            tab_info['render_func']()
    
    @performance_timer
    def render_bulk_operations_progressive(self, operations: List[Dict], key: str = "bulk_ops"):
        """Progressively execute and display bulk operations."""
        if f"{key}_status" not in st.session_state:
            st.session_state[f"{key}_status"] = "ready"
        
        status = st.session_state[f"{key}_status"]
        
        if status == "ready":
            st.info(f"📊 Ready to process {len(operations)} operations")
            if st.button("🚀 Start Processing", key=f"{key}_start"):
                st.session_state[f"{key}_status"] = "processing"
                st.session_state[f"{key}_current"] = 0
                st.session_state[f"{key}_results"] = []
                st.rerun()
        
        elif status == "processing":
            current = st.session_state.get(f"{key}_current", 0)
            results = st.session_state.get(f"{key}_results", [])
            
            # Show progress
            progress = current / len(operations) if operations else 0
            st.progress(progress, text=f"Processing operation {current + 1} of {len(operations)}")
            
            # Process current operation
            if current < len(operations):
                operation = operations[current]
                
                # Show current operation
                with st.status(f"Processing: {operation['name']}", expanded=True):
                    try:
                        result = operation['func']()
                        st.success(f"✅ {operation['name']} completed")
                        results.append({"name": operation['name'], "status": "success", "result": result})
                    except Exception as e:
                        st.error(f"❌ {operation['name']} failed: {str(e)}")
                        results.append({"name": operation['name'], "status": "error", "error": str(e)})
                
                # Update state
                st.session_state[f"{key}_current"] = current + 1
                st.session_state[f"{key}_results"] = results
                
                # Auto-continue without delay
                if current + 1 < len(operations):
                    st.rerun()
                else:
                    st.session_state[f"{key}_status"] = "completed"
                    st.rerun()
        
        elif status == "completed":
            results = st.session_state.get(f"{key}_results", [])
            
            # Show summary
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = len(results) - success_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ Successful", success_count)
            with col2:
                st.metric("❌ Failed", error_count)
            with col3:
                st.metric("📊 Total", len(results))
            
            # Show detailed results
            with st.expander("📋 Detailed Results", expanded=error_count > 0):
                for result in results:
                    if result["status"] == "success":
                        st.success(f"✅ {result['name']}")
                    else:
                        st.error(f"❌ {result['name']}: {result['error']}")
            
            # Reset button
            if st.button("🔄 Reset", key=f"{key}_reset"):
                st.session_state[f"{key}_status"] = "ready"
                st.rerun()

# Global progressive loader instance
progressive_loader = ProgressiveLoader()

def render_performance_dashboard():
    """Render performance monitoring dashboard."""
    with st.sidebar.expander("⚡ Performance Monitor", expanded=False):
        perf_monitor.display_metrics()
        
        # Quick performance actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Clear Metrics", key="clear_perf_metrics"):
                perf_monitor.metrics.clear()
                st.success("Metrics cleared!")
        
        with col2:
            if st.button("📊 Refresh", key="refresh_perf_metrics"):
                st.rerun()
