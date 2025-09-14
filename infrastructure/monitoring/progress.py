"""
Progress tracking functionality for Resume Customizer application.
Provides task progress monitoring and estimation capabilities.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import streamlit as st

from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger
from .metrics import get_metrics_manager, Metric, MetricType

logger = get_logger()
structured_logger = get_structured_logger("progress_tracker")


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """Progress information for a task."""
    task_id: str
    status: TaskStatus
    description: str
    current: int = 0
    total: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressTracker:
    """Tracks progress of tasks and provides estimates."""
    
    def __init__(self):
        self._tasks: Dict[str, TaskProgress] = {}
        self._lock = threading.Lock()
        self._metrics = get_metrics_manager()
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize progress-specific metrics."""
        metrics = [
            Metric(
                "task_duration_seconds",
                MetricType.HISTOGRAM,
                "Task execution duration",
                unit="seconds",
                labels=["task_type", "status"]
            ),
            Metric(
                "task_completion_rate",
                MetricType.GAUGE,
                "Task completion percentage",
                unit="%",
                labels=["task_type"]
            ),
            Metric(
                "active_tasks",
                MetricType.GAUGE,
                "Number of active tasks",
                labels=["status"]
            )
        ]
        
        for metric in metrics:
            self._metrics.register_metric(metric)
    
    def start_task(self, task_id: str, description: str, total: int = 100) -> TaskProgress:
        """Start tracking a new task."""
        progress = TaskProgress(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            description=description,
            total=total,
            start_time=datetime.now()
        )
        
        with self._lock:
            self._tasks[task_id] = progress
            
        self._update_metrics()
        return progress
    
    def update_progress(self, 
                       task_id: str, 
                       current: int,
                       description: Optional[str] = None) -> TaskProgress:
        """Update the progress of a task."""
        with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task {task_id} not found")
                
            progress = self._tasks[task_id]
            progress.current = current
            
            if description:
                progress.description = description
                
            if current >= progress.total:
                progress.status = TaskStatus.COMPLETED
                progress.end_time = datetime.now()
                
        self._update_metrics()
        return progress
    
    def complete_task(self, task_id: str) -> TaskProgress:
        """Mark a task as completed."""
        with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task {task_id} not found")
                
            progress = self._tasks[task_id]
            progress.status = TaskStatus.COMPLETED
            progress.current = progress.total
            progress.end_time = datetime.now()
            
        self._update_metrics()
        return progress
    
    def fail_task(self, task_id: str, error: str) -> TaskProgress:
        """Mark a task as failed."""
        with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task {task_id} not found")
                
            progress = self._tasks[task_id]
            progress.status = TaskStatus.FAILED
            progress.error = error
            progress.end_time = datetime.now()
            
        self._update_metrics()
        return progress
    
    def cancel_task(self, task_id: str) -> TaskProgress:
        """Cancel a task."""
        with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task {task_id} not found")
                
            progress = self._tasks[task_id]
            progress.status = TaskStatus.CANCELLED
            progress.end_time = datetime.now()
            
        self._update_metrics()
        return progress
    
    def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get the current progress of a task."""
        return self._tasks.get(task_id)
    
    def get_active_tasks(self) -> List[TaskProgress]:
        """Get all currently active tasks."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS]
    
    def estimate_completion(self, task_id: str) -> Optional[datetime]:
        """Estimate completion time for a task."""
        progress = self.get_progress(task_id)
        if not progress or not progress.start_time:
            return None
            
        if progress.current == 0:
            return None
            
        elapsed = datetime.now() - progress.start_time
        rate = progress.current / elapsed.total_seconds()
        remaining = (progress.total - progress.current) / rate
        
        return datetime.now() + timedelta(seconds=remaining)
    
    def _update_metrics(self):
        """Update progress-related metrics."""
        status_counts = defaultdict(int)
        for task in self._tasks.values():
            status_counts[task.status.value] += 1
            
            if task.end_time and task.start_time:
                duration = (task.end_time - task.start_time).total_seconds()
                self._metrics.record_value(
                    "task_duration_seconds",
                    duration,
                    labels={"task_type": task.metadata.get("type", "unknown"),
                           "status": task.status.value}
                )
            
            if task.total > 0:
                completion_rate = (task.current / task.total) * 100
                self._metrics.record_value(
                    "task_completion_rate",
                    completion_rate,
                    labels={"task_type": task.metadata.get("type", "unknown")}
                )
        
        for status, count in status_counts.items():
            self._metrics.record_value("active_tasks", count, labels={"status": status})


# Global progress tracker instance
_progress_tracker = ProgressTracker()

def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance."""
    return _progress_tracker