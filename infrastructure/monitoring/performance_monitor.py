"""
Performance Monitor Module
Provides performance monitoring decorators and metrics collection
"""

import time
import psutil
import functools
from typing import Dict, Any, Callable, Optional
from threading import Lock
import logging

# Performance metrics storage
_performance_metrics: Dict[str, Dict[str, Any]] = {}
_metrics_lock = Lock()

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Collects and manages performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = Lock()
    
    def record_execution(self, function_name: str, execution_time: float, 
                        memory_usage: float = 0, cpu_usage: float = 0):
        """Record function execution metrics"""
        with self.lock:
            if function_name not in self.metrics:
                self.metrics[function_name] = {
                    'call_count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0,
                    'total_memory': 0,
                    'avg_memory': 0,
                    'total_cpu': 0,
                    'avg_cpu': 0
                }
            
            metrics = self.metrics[function_name]
            metrics['call_count'] += 1
            metrics['total_time'] += execution_time
            metrics['avg_time'] = metrics['total_time'] / metrics['call_count']
            metrics['min_time'] = min(metrics['min_time'], execution_time)
            metrics['max_time'] = max(metrics['max_time'], execution_time)
            
            if memory_usage > 0:
                metrics['total_memory'] += memory_usage
                metrics['avg_memory'] = metrics['total_memory'] / metrics['call_count']
            
            if cpu_usage > 0:
                metrics['total_cpu'] += cpu_usage
                metrics['avg_cpu'] = metrics['total_cpu'] / metrics['call_count']
    
    def get_metrics(self, function_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics"""
        with self.lock:
            if function_name:
                return self.metrics.get(function_name, {})
            return self.metrics.copy()
    
    def clear_metrics(self):
        """Clear all performance metrics"""
        with self.lock:
            self.metrics.clear()

# Global performance metrics instance
_performance_tracker = PerformanceMetrics()

def get_performance_metrics(function_name: Optional[str] = None) -> Dict[str, Any]:
    """Get performance metrics for functions"""
    return _performance_tracker.get_metrics(function_name)

def clear_performance_metrics():
    """Clear all performance metrics"""
    _performance_tracker.clear_metrics()

def performance_decorator(monitor_memory: bool = True, monitor_cpu: bool = True):
    """
    Decorator to monitor function performance
    
    Args:
        monitor_memory: Whether to monitor memory usage
        monitor_cpu: Whether to monitor CPU usage
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Get initial system metrics
            initial_memory = 0
            initial_cpu = 0
            
            if monitor_memory:
                try:
                    process = psutil.Process()
                    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
                except:
                    pass
            
            if monitor_cpu:
                try:
                    initial_cpu = psutil.cpu_percent()
                except:
                    pass
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Get final system metrics
                final_memory = 0
                final_cpu = 0
                
                if monitor_memory:
                    try:
                        process = psutil.Process()
                        final_memory = process.memory_info().rss / 1024 / 1024  # MB
                    except:
                        pass
                
                if monitor_cpu:
                    try:
                        final_cpu = psutil.cpu_percent()
                    except:
                        pass
                
                # Record metrics
                memory_delta = final_memory - initial_memory if monitor_memory else 0
                cpu_delta = final_cpu - initial_cpu if monitor_cpu else 0
                
                _performance_tracker.record_execution(
                    func.__name__, 
                    execution_time, 
                    memory_delta, 
                    cpu_delta
                )
                
                # Log performance if execution time is significant
                if execution_time > 1.0:  # Log if > 1 second
                    logger.info(f"Performance: {func.__name__} took {execution_time:.2f}s")
                
                return result
                
            except Exception as e:
                # Record failed execution
                execution_time = time.time() - start_time
                _performance_tracker.record_execution(func.__name__, execution_time)
                logger.error(f"Performance: {func.__name__} failed after {execution_time:.2f}s: {e}")
                raise
        
        return wrapper
    return decorator

def monitor_function_performance(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Monitor a single function call and return performance metrics
    """
    start_time = time.time()
    
    try:
        # Get initial metrics
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = psutil.cpu_percent()
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Calculate metrics
        execution_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        final_cpu = psutil.cpu_percent()
        
        return {
            'result': result,
            'execution_time': execution_time,
            'memory_delta': final_memory - initial_memory,
            'cpu_delta': final_cpu - initial_cpu,
            'success': True
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            'result': None,
            'execution_time': execution_time,
            'memory_delta': 0,
            'cpu_delta': 0,
            'success': False,
            'error': str(e)
        }

def get_system_performance() -> Dict[str, Any]:
    """Get current system performance metrics"""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
            'disk_usage_percent': psutil.disk_usage('/').percent if hasattr(psutil.disk_usage('/'), 'percent') else 0,
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get system performance: {e}")
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_available_gb': 0,
            'disk_usage_percent': 0,
            'timestamp': time.time(),
            'error': str(e)
        }

# Convenience function for backward compatibility
def performance_monitor(*args, **kwargs):
    """Alias for performance_decorator"""
    return performance_decorator(*args, **kwargs)
