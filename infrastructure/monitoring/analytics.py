"""
Analytics functionality for Resume Customizer application.
Provides user activity tracking and system performance analytics.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import json
import hashlib
from collections import defaultdict, Counter

from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger
from .metrics import (
    MetricsManager, 
    Metric, 
    MetricType, 
    MetricValue, 
    get_metrics_manager
)

logger = get_logger()
structured_logger = get_structured_logger("analytics")


@dataclass
class UserActivity:
    """User activity data container."""
    user_id: str
    session_id: str
    timestamp: datetime
    action: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System-level metrics container."""
    cpu_usage: float
    memory_usage: float
    active_users: int
    response_times: List[float]
    error_counts: Dict[str, int]
    timestamp: datetime = field(default_factory=datetime.now)


class AnalyticsManager:
    """Manages analytics collection and analysis."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._metrics = get_metrics_manager()
            self._activities: List[UserActivity] = []
            self._system_metrics: List[SystemMetrics] = []
            self._instance_lock = threading.Lock()
            self._metric_counters = defaultdict(int)
            self._metric_timers = {}
            self._initialized = True
            self._initialize_metrics()
    
    def record_metric(self, category: str, action: str = None, value: Any = 1, 
                     metric_type: MetricType = MetricType.COUNTER, 
                     tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a metric for analytics.
        
        Args:
            category (str): Category of the metric (e.g., 'resume_processing')
            action (str, optional): Specific action being measured
            value (Any): Value to record
            metric_type (MetricType): Type of metric (COUNT, GAUGE, TIMER, etc.)
            tags (Dict[str, str], optional): Additional tags for the metric
        """
        with self._lock:
            metric_id = f"{category}.{action}" if action else category
            
            metric_value = MetricValue(
                value=value,
                timestamp=datetime.now(),
                labels=tags or {}
            )
            
            # Create or get metric definition if it doesn't exist
            if not self._metrics.get_metric(metric_id):
                metric = Metric(
                    name=metric_id,
                    type=metric_type,
                    description=f"Metric for {category}",
                    unit="",
                    labels=list(tags.keys()) if tags else []
                )
                self._metrics.register_metric(metric)
            
            final_value = value
            if metric_type == MetricType.COUNTER:
                self._metric_counters[metric_id] += value
                final_value = self._metric_counters[metric_id]
            elif metric_type == MetricType.TIMER:
                if metric_id not in self._metric_timers:
                    self._metric_timers[metric_id] = value
                    final_value = 0  # Start of timing
                else:
                    duration = value - self._metric_timers[metric_id]
                    final_value = duration
                    del self._metric_timers[metric_id]
            
            self._metrics.record_value(metric_id, final_value, tags)
            
            # Log metric for analysis
            structured_logger.info(
                f"Recorded metric: {metric_id}",
                extra={
                    "metric_id": metric_id,
                    "type": metric_type.value,
                    "value": value,
                    "tags": tags
                }
            )


    def _initialize_metrics(self):
        """Initialize analytics-specific metrics."""
        core_metrics = {
            "user_activity": Metric(
                name="user_activity_count",
                type=MetricType.COUNTER,
                description="Number of user activities",
                labels=["scope", "action"]
            ),
            "system_cpu": Metric(
                name="system_cpu_usage",
                type=MetricType.GAUGE,
                description="System CPU usage percentage",
                unit="%",
                labels=["component"]
            ),
            "system_memory": Metric(
                name="system_memory_usage",
                type=MetricType.GAUGE,
                description="System memory usage percentage",
                unit="%",
                labels=["component"]
            ),
            "active_users": Metric(
                name="active_users_count",
                type=MetricType.GAUGE,
                description="Number of active users",
                labels=["scope"]
            ),
            "response_time": Metric(
                name="response_time_seconds",
                type=MetricType.HISTOGRAM,
                description="API response times",
                unit="seconds",
                labels=["endpoint", "method"]
            )
        }
        
        for metric in core_metrics.values():
            self._metrics.register_metric(metric)


    def record_user_activity(self, activity: UserActivity):
        """Record a user activity."""
        with self._lock:
            self._activities.append(activity)
            
        # Update metrics
        self._metrics.record_value(
            "user_activity_count",
            1,
            labels={"action": activity.action, "user_id": activity.user_id}
        )
    
    def record_system_metrics(self, metrics: SystemMetrics):
        """Record system-level metrics."""
        with self._lock:
            self._system_metrics.append(metrics)
            
        # Update individual metrics
        self._metrics.record_value("system_cpu_usage", metrics.cpu_usage)
        self._metrics.record_value("system_memory_usage", metrics.memory_usage)
        self._metrics.record_value("active_users_count", metrics.active_users)
        
        for rt in metrics.response_times:
            self._metrics.record_value("response_time_seconds", rt)
    
    def get_user_activities(self,
                          user_id: Optional[str] = None,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[UserActivity]:
        """Get user activities with optional filtering."""
        activities = self._activities
        
        if user_id:
            activities = [a for a in activities if a.user_id == user_id]
        if start_time:
            activities = [a for a in activities if a.timestamp >= start_time]
        if end_time:
            activities = [a for a in activities if a.timestamp <= end_time]
            
        return activities
    
    def get_system_metrics_summary(self,
                                 start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get a summary of system metrics."""
        metrics = self._system_metrics
        
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
            
        if not metrics:
            return {}
            
        return {
            "cpu_usage": {
                "current": metrics[-1].cpu_usage,
                "average": sum(m.cpu_usage for m in metrics) / len(metrics)
            },
            "memory_usage": {
                "current": metrics[-1].memory_usage,
                "average": sum(m.memory_usage for m in metrics) / len(metrics)
            },
            "active_users": {
                "current": metrics[-1].active_users,
                "peak": max(m.active_users for m in metrics)
            },
            "response_times": {
                "average": sum(sum(m.response_times) / len(m.response_times) for m in metrics) / len(metrics)
            },
            "error_counts": dict(sum((Counter(m.error_counts) for m in metrics), Counter()))
        }


def get_analytics_manager() -> AnalyticsManager:
    """Get the singleton instance of AnalyticsManager."""
    return AnalyticsManager()