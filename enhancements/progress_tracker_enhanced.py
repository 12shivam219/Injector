"""
Enhanced progress tracking system for Resume Customizer application.
Provides real-time progress updates, ETA calculation, and user-friendly progress display.
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import streamlit as st

from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger

logger = get_logger()
structured_logger = get_structured_logger("progress_tracker")


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressTask:
    """Individual task in progress tracking."""
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_duration: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Get actual duration if task is completed."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed (success or failure)."""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]


@dataclass
class ProgressSession:
    """Progress tracking session for multiple tasks."""
    id: str
    name: str
    tasks: Dict[str, ProgressTask] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_weight: float = 0.0
    progress_callback: Optional[Callable] = None
    
    @property
    def overall_progress(self) -> float:
        """Calculate overall progress across all tasks."""
        if not self.tasks or self.total_weight == 0:
            return 0.0
        
        total_weighted_progress = 0.0
        for task in self.tasks.values():
            weight = task.metadata.get('weight', 1.0)
            total_weighted_progress += task.progress * weight
        
        return min(total_weighted_progress / self.total_weight, 1.0)
    
    @property
    def completed_tasks(self) -> int:
        """Get count of completed tasks."""
        return sum(1 for task in self.tasks.values() if task.is_completed)
    
    @property
    def failed_tasks(self) -> int:
        """Get count of failed tasks."""
        return sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
    
    @property
    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(task.is_completed for task in self.tasks.values())
    
    @property
    def estimated_completion_time(self) -> Optional[datetime]:
        """Estimate when all tasks will complete."""
        if not self.tasks:
            return None
        
        current_progress = self.overall_progress
        if current_progress >= 1.0:
            return datetime.now()
        
        if current_progress <= 0.0:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed <= 0:
            return None
        
        # Calculate rate of progress
        progress_rate = current_progress / elapsed
        if progress_rate <= 0:
            return None
        
        remaining_progress = 1.0 - current_progress
        estimated_remaining_seconds = remaining_progress / progress_rate
        
        return datetime.now() + timedelta(seconds=estimated_remaining_seconds)


class AdvancedProgressTracker:
    """
    Advanced progress tracker with real-time updates and ETA calculation.
    """
    
    def __init__(self):
        self.sessions: Dict[str, ProgressSession] = {}
        self._lock = threading.RLock()
        self._update_callbacks: Dict[str, List[Callable]] = {}
        
        # Performance metrics
        self._metrics = {
            'total_sessions': 0,
            'completed_sessions': 0,
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'avg_task_duration': 0.0
        }
        
        structured_logger.info(
            "Advanced progress tracker initialized",
            operation="progress_tracker_init"
        )
    
    def create_session(self, 
                      session_id: str, 
                      session_name: str,
                      progress_callback: Optional[Callable] = None) -> ProgressSession:
        """
        Create a new progress tracking session.
        
        Args:
            session_id: Unique session identifier
            session_name: Human-readable session name
            progress_callback: Optional callback for progress updates
            
        Returns:
            Created progress session
        """
        with self._lock:
            if session_id in self.sessions:
                logger.warning(f"Session {session_id} already exists, replacing")
            
            session = ProgressSession(
                id=session_id,
                name=session_name,
                progress_callback=progress_callback
            )
            
            self.sessions[session_id] = session
            self._metrics['total_sessions'] += 1
            
            structured_logger.info(
                f"Progress session created: {session_name}",
                operation="session_create",
                session_id=session_id,
                session_name=session_name
            )
            
            return session
    
    def add_task(self, 
                session_id: str,
                task_id: str,
                task_name: str,
                estimated_duration: Optional[float] = None,
                weight: float = 1.0) -> bool:
        """
        Add a task to a progress session.
        
        Args:
            session_id: Session to add task to
            task_id: Unique task identifier
            task_name: Human-readable task name
            estimated_duration: Estimated duration in seconds
            weight: Task weight for progress calculation
            
        Returns:
            True if task was added successfully
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            if task_id in session.tasks:
                logger.warning(f"Task {task_id} already exists in session {session_id}")
                return False
            
            task = ProgressTask(
                id=task_id,
                name=task_name,
                estimated_duration=estimated_duration,
                metadata={'weight': weight}
            )
            
            session.tasks[task_id] = task
            session.total_weight += weight
            
            self._metrics['total_tasks'] += 1
            
            structured_logger.debug(
                f"Task added: {task_name}",
                operation="task_add",
                session_id=session_id,
                task_id=task_id,
                weight=weight,
                estimated_duration=estimated_duration
            )
            
            return True
    
    def start_task(self, session_id: str, task_id: str) -> bool:
        """
        Mark a task as started.
        
        Args:
            session_id: Session containing the task
            task_id: Task to start
            
        Returns:
            True if task was started successfully
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            task = session.tasks.get(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.IN_PROGRESS
            task.start_time = datetime.now()
            task.progress = 0.0
            
            structured_logger.info(
                f"Task started: {task.name}",
                operation="task_start",
                session_id=session_id,
                task_id=task_id
            )
            
            self._notify_progress_update(session)
            return True
    
    def update_task_progress(self, 
                           session_id: str, 
                           task_id: str, 
                           progress: float,
                           message: Optional[str] = None) -> bool:
        """
        Update task progress.
        
        Args:
            session_id: Session containing the task
            task_id: Task to update
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            
        Returns:
            True if progress was updated successfully
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            task = session.tasks.get(task_id)
            if not task:
                return False
            
            # Ensure progress is valid
            progress = max(0.0, min(1.0, progress))
            task.progress = progress
            
            if message:
                task.metadata['current_message'] = message
            
            # Auto-complete task if progress reaches 1.0
            if progress >= 1.0 and task.status != TaskStatus.COMPLETED:
                self.complete_task(session_id, task_id)
            
            structured_logger.debug(
                f"Task progress updated: {task.name} - {progress:.1%}",
                operation="task_progress_update",
                session_id=session_id,
                task_id=task_id,
                progress=progress,
                message=message
            )
            
            self._notify_progress_update(session)
            return True
    
    def complete_task(self, 
                     session_id: str, 
                     task_id: str,
                     success: bool = True,
                     error_message: Optional[str] = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            session_id: Session containing the task
            task_id: Task to complete
            success: Whether task completed successfully
            error_message: Error message if task failed
            
        Returns:
            True if task was completed successfully
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            task = session.tasks.get(task_id)
            if not task:
                return False
            
            task.end_time = datetime.now()
            task.progress = 1.0 if success else task.progress
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            
            if error_message:
                task.error_message = error_message
            
            # Update metrics
            if success:
                self._metrics['completed_tasks'] += 1
            else:
                self._metrics['failed_tasks'] += 1
            
            # Update average duration
            if task.duration:
                current_avg = self._metrics['avg_task_duration']
                total_completed = self._metrics['completed_tasks']
                self._metrics['avg_task_duration'] = (
                    (current_avg * (total_completed - 1) + task.duration) / total_completed
                )
            
            structured_logger.info(
                f"Task completed: {task.name} - {'Success' if success else 'Failed'}",
                operation="task_complete",
                session_id=session_id,
                task_id=task_id,
                success=success,
                duration=task.duration,
                error_message=error_message
            )
            
            # Check if session is complete
            if session.is_complete:
                self._complete_session(session)
            
            self._notify_progress_update(session)
            return True
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive status of a progress session.
        
        Args:
            session_id: Session to get status for
            
        Returns:
            Session status dictionary or None if not found
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            
            # Calculate detailed statistics
            tasks_by_status = {}
            for status in TaskStatus:
                tasks_by_status[status.value] = sum(
                    1 for task in session.tasks.values() if task.status == status
                )
            
            active_tasks = [
                {
                    'id': task.id,
                    'name': task.name,
                    'progress': task.progress,
                    'status': task.status.value,
                    'duration': task.duration,
                    'current_message': task.metadata.get('current_message')
                }
                for task in session.tasks.values()
                if task.status == TaskStatus.IN_PROGRESS
            ]
            
            return {
                'session_id': session.id,
                'session_name': session.name,
                'overall_progress': session.overall_progress,
                'total_tasks': len(session.tasks),
                'completed_tasks': session.completed_tasks,
                'failed_tasks': session.failed_tasks,
                'tasks_by_status': tasks_by_status,
                'active_tasks': active_tasks,
                'start_time': session.start_time.isoformat(),
                'estimated_completion': (
                    session.estimated_completion_time.isoformat()
                    if session.estimated_completion_time else None
                ),
                'is_complete': session.is_complete,
                'duration': (
                    (datetime.now() - session.start_time).total_seconds()
                    if not session.end_time else
                    (session.end_time - session.start_time).total_seconds()
                )
            }
    
    def register_progress_callback(self, session_id: str, callback: Callable):
        """Register a callback for progress updates."""
        with self._lock:
            if session_id not in self._update_callbacks:
                self._update_callbacks[session_id] = []
            self._update_callbacks[session_id].append(callback)
    
    def _notify_progress_update(self, session: ProgressSession):
        """Notify all registered callbacks of progress update."""
        try:
            # Call session's built-in callback
            if session.progress_callback:
                session.progress_callback(session)
            
            # Call registered callbacks
            callbacks = self._update_callbacks.get(session.id, [])
            for callback in callbacks:
                try:
                    callback(session)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
        
        except Exception as e:
            logger.error(f"Progress notification failed: {e}")
    
    def _complete_session(self, session: ProgressSession):
        """Handle session completion."""
        session.end_time = datetime.now()
        self._metrics['completed_sessions'] += 1
        
        structured_logger.info(
            f"Progress session completed: {session.name}",
            operation="session_complete",
            session_id=session.id,
            total_tasks=len(session.tasks),
            successful_tasks=len(session.tasks) - session.failed_tasks,
            failed_tasks=session.failed_tasks,
            duration=(session.end_time - session.start_time).total_seconds()
        )
    
    def cleanup_old_sessions(self, max_age_hours: float = 24):
        """Clean up old completed sessions."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            sessions_to_remove = []
            
            for session_id, session in self.sessions.items():
                if (session.is_complete and 
                    session.end_time and 
                    session.end_time < cutoff_time):
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.sessions[session_id]
                if session_id in self._update_callbacks:
                    del self._update_callbacks[session_id]
            
            if sessions_to_remove:
                structured_logger.info(
                    f"Cleaned up {len(sessions_to_remove)} old progress sessions",
                    operation="session_cleanup",
                    removed_count=len(sessions_to_remove)
                )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get progress tracking metrics."""
        with self._lock:
            active_sessions = sum(1 for s in self.sessions.values() if not s.is_complete)
            
            return {
                **self._metrics,
                'active_sessions': active_sessions,
                'total_active_sessions': len(self.sessions)
            }


# Streamlit-specific progress components
class StreamlitProgressDisplay:
    """Streamlit-specific progress display components."""
    
    @staticmethod
    def create_progress_container(session_name: str) -> Dict[str, Any]:
        """Create Streamlit progress display container."""
        container = st.container()
        
        with container:
            st.subheader(f"🔄 {session_name}")
            
            # Overall progress
            overall_progress = st.progress(0)
            overall_status = st.empty()
            
            # Task details
            task_container = st.expander("📋 Task Details", expanded=False)
            
            # ETA and metrics
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            
            with metrics_col1:
                eta_display = st.empty()
            with metrics_col2:
                speed_display = st.empty()
            with metrics_col3:
                completed_display = st.empty()
        
        return {
            'container': container,
            'overall_progress': overall_progress,
            'overall_status': overall_status,
            'task_container': task_container,
            'eta_display': eta_display,
            'speed_display': speed_display,
            'completed_display': completed_display
        }
    
    @staticmethod
    def update_progress_display(display_components: Dict[str, Any], 
                              session_status: Dict[str, Any]):
        """Update Streamlit progress display."""
        try:
            # Update overall progress
            progress = session_status['overall_progress']
            display_components['overall_progress'].progress(progress)
            
            # Update overall status
            status_text = f"Progress: {progress:.1%} ({session_status['completed_tasks']}/{session_status['total_tasks']} tasks)"
            if session_status['failed_tasks'] > 0:
                status_text += f" ❌ {session_status['failed_tasks']} failed"
            display_components['overall_status'].text(status_text)
            
            # Update ETA
            eta = session_status.get('estimated_completion')
            if eta:
                eta_time = datetime.fromisoformat(eta)
                remaining = eta_time - datetime.now()
                if remaining.total_seconds() > 0:
                    display_components['eta_display'].metric(
                        "⏱️ ETA",
                        f"{remaining.total_seconds():.0f}s"
                    )
                else:
                    display_components['eta_display'].metric("⏱️ ETA", "Complete")
            else:
                display_components['eta_display'].metric("⏱️ ETA", "Calculating...")
            
            # Update speed
            duration = session_status.get('duration', 0)
            if duration > 0:
                speed = session_status['completed_tasks'] / (duration / 60)  # tasks per minute
                display_components['speed_display'].metric(
                    "⚡ Speed",
                    f"{speed:.1f}/min"
                )
            
            # Update completed count
            display_components['completed_display'].metric(
                "✅ Completed",
                f"{session_status['completed_tasks']}/{session_status['total_tasks']}"
            )
            
            # Update task details
            with display_components['task_container']:
                active_tasks = session_status.get('active_tasks', [])
                if active_tasks:
                    for task in active_tasks:
                        task_progress = st.progress(task['progress'])
                        st.text(f"🔄 {task['name']} - {task['progress']:.1%}")
                        if task.get('current_message'):
                            st.caption(task['current_message'])
        
        except Exception as e:
            logger.error(f"Failed to update progress display: {e}")


# Global progress tracker instance
_progress_tracker = None
_tracker_lock = threading.Lock()


def get_progress_tracker() -> AdvancedProgressTracker:
    """Get global progress tracker instance."""
    global _progress_tracker
    
    with _tracker_lock:
        if _progress_tracker is None:
            _progress_tracker = AdvancedProgressTracker()
        return _progress_tracker


# Convenience functions for common usage patterns
def create_progress_session(session_name: str, 
                          tasks: List[Dict[str, Any]],
                          progress_callback: Optional[Callable] = None) -> str:
    """
    Create progress session with predefined tasks.
    
    Args:
        session_name: Name of the session
        tasks: List of task dictionaries with 'name', 'weight', 'estimated_duration'
        progress_callback: Optional progress callback
        
    Returns:
        Session ID
    """
    tracker = get_progress_tracker()
    session_id = f"session_{int(time.time() * 1000)}"
    
    session = tracker.create_session(session_id, session_name, progress_callback)
    
    for i, task_info in enumerate(tasks):
        tracker.add_task(
            session_id,
            f"task_{i}",
            task_info.get('name', f'Task {i+1}'),
            task_info.get('estimated_duration'),
            task_info.get('weight', 1.0)
        )
    
    return session_id



