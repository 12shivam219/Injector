"""
Base metrics functionality for Resume Customizer application.
Provides core metric types and collection functionality.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
import time
import threading
import statistics
from datetime import datetime, timedelta

from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger

logger = get_logger()
structured_logger = get_structured_logger("metrics")


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"      # Monotonically increasing counter
    GAUGE = "gauge"         # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"         # Duration measurements


@dataclass
class MetricValue:
    """Value container for metrics with metadata."""
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Definition of a metric."""
    name: str
    type: MetricType
    description: str
    unit: str = ""
    labels: List[str] = field(default_factory=list)


class MetricsManager:
    """Manages metric collection and storage."""
    
    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._values: Dict[str, List[MetricValue]] = {}
        self._lock = threading.Lock()
    
    def register_metric(self, metric: Metric):
        """Register a new metric definition."""
        with self._lock:
            self._metrics[metric.name] = metric
            self._values[metric.name] = []
    
    def record_value(self, 
                    metric_name: str, 
                    value: Union[int, float], 
                    labels: Optional[Dict[str, str]] = None):
        """Record a new value for a metric."""
        if labels is None:
            labels = {}
            
        if metric_name not in self._metrics:
            raise ValueError(f"Metric {metric_name} not registered")
            
        metric_value = MetricValue(value=value, labels=labels)
        
        with self._lock:
            self._values[metric_name].append(metric_value)
    
    def get_metric(self, metric_name: str) -> Optional[Metric]:
        """Get the definition of a metric."""
        return self._metrics.get(metric_name)
    
    def get_values(self, 
                  metric_name: str,
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  labels: Optional[Dict[str, str]] = None) -> List[MetricValue]:
        """Get values for a metric with optional filtering."""
        if metric_name not in self._values:
            return []
            
        values = self._values[metric_name]
        
        if start_time:
            values = [v for v in values if v.timestamp >= start_time]
        if end_time:
            values = [v for v in values if v.timestamp <= end_time]
        if labels:
            values = [v for v in values if all(v.labels.get(k) == labels[k] for k in labels)]
            
        return values
    
    def get_summary(self, metric_name: str) -> Dict[str, Any]:
        """Get a statistical summary of a metric's values."""
        values = [v.value for v in self._values.get(metric_name, [])]
        
        if not values:
            return {}
            
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values)
        }


# Global metrics manager instance
_metrics_manager = MetricsManager()

def get_metrics_manager() -> MetricsManager:
    """Get the global metrics manager instance."""
    return _metrics_manager