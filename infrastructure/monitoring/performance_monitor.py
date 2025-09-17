"""
Performance Monitor Module
Provides performance monitoring and metrics collection functionality
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

class PerformanceMonitor:
    """Simple performance monitoring system"""
    
    def __init__(self):
        self._metrics: List[PerformanceMetric] = []
        self._lock = threading.Lock()
        self._start_times: Dict[str, float] = {}
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        if tags is None:
            tags = {}
        
        metric = PerformanceMetric(name=name, value=value, tags=tags)
        with self._lock:
            self._metrics.append(metric)
    
    def start_timer(self, name: str):
        """Start timing an operation"""
        self._start_times[name] = time.time()
    
    def end_timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """End timing an operation and record the duration"""
        if name in self._start_times:
            duration = time.time() - self._start_times[name]
            self.record_metric(f"{name}_duration", duration, tags)
            del self._start_times[name]
            return duration
        return None
    
    @contextmanager
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_metric(f"{name}_duration", duration, tags)
    
    def get_metrics(self, name_filter: Optional[str] = None) -> List[PerformanceMetric]:
        """Get recorded metrics, optionally filtered by name"""
        with self._lock:
            if name_filter:
                return [m for m in self._metrics if name_filter in m.name]
            return self._metrics.copy()
    
    def clear_metrics(self):
        """Clear all recorded metrics"""
        with self._lock:
            self._metrics.clear()
    
    def get_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for a specific metric name"""
        metrics = [m for m in self._metrics if m.name == name]
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'total': sum(values)
        }

# Global performance monitor instance
_global_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    return _global_monitor

def record_performance_metric(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Convenience function to record a metric"""
    _global_monitor.record_metric(name, value, tags)

def time_operation(name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to time function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with _global_monitor.timer(f"function_{name}", tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator