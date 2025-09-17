"""
Query monitoring system for tracking and analyzing database performance
"""

import time
import logging
import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Configure logger
logger = logging.getLogger(__name__)

class QueryMonitor:
    """
    Monitors database queries and tracks performance metrics
    
    Features:
    - Tracks slow queries exceeding threshold
    - Maintains query statistics
    - Provides reporting capabilities
    """
    
    def __init__(self, slow_query_threshold_ms: int = 100):
        """
        Initialize query monitor
        
        Args:
            slow_query_threshold_ms: Threshold in milliseconds to identify slow queries
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.query_stats: Dict[str, Dict[str, Any]] = {}
        self.slow_queries: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._enabled = True
        
    def enable(self):
        """Enable query monitoring"""
        self._enabled = True
        
    def disable(self):
        """Disable query monitoring"""
        self._enabled = False
        
    def register_with_engine(self, engine: Engine):
        """
        Register query monitoring events with SQLAlchemy engine
        
        Args:
            engine: SQLAlchemy engine to monitor
        """
        event.listen(engine, "before_cursor_execute", self._before_cursor_execute)
        event.listen(engine, "after_cursor_execute", self._after_cursor_execute)
        logger.info(f"Query monitoring enabled for engine {engine}")
        
    def _before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Event hook called before query execution"""
        if not self._enabled:
            return
            
        context._query_start_time = time.time()
        
    def _after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Event hook called after query execution"""
        if not self._enabled or not hasattr(context, "_query_start_time"):
            return
            
        # Calculate query execution time
        execution_time = time.time() - context._query_start_time
        execution_time_ms = int(execution_time * 1000)
        
        # Normalize query by removing extra whitespace
        query = " ".join(statement.split())
        
        # Update query statistics
        with self._lock:
            if query not in self.query_stats:
                self.query_stats[query] = {
                    "count": 0,
                    "total_time_ms": 0,
                    "min_time_ms": float("inf"),
                    "max_time_ms": 0,
                    "avg_time_ms": 0
                }
                
            stats = self.query_stats[query]
            stats["count"] += 1
            stats["total_time_ms"] += execution_time_ms
            stats["min_time_ms"] = min(stats["min_time_ms"], execution_time_ms)
            stats["max_time_ms"] = max(stats["max_time_ms"], execution_time_ms)
            stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
            
            # Track slow queries
            if execution_time_ms > self.slow_query_threshold_ms:
                self.slow_queries.append({
                    "query": query,
                    "parameters": str(parameters),
                    "execution_time_ms": execution_time_ms,
                    "timestamp": datetime.now().isoformat()
                })
                logger.warning(f"Slow query detected ({execution_time_ms}ms): {query}")
    
    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """Get list of slow queries"""
        with self._lock:
            return self.slow_queries.copy()
    
    def get_query_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get query statistics"""
        with self._lock:
            return self.query_stats.copy()
    
    def get_top_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top slow queries by execution time
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of slow queries sorted by execution time (descending)
        """
        with self._lock:
            sorted_queries = sorted(
                self.slow_queries, 
                key=lambda q: q["execution_time_ms"], 
                reverse=True
            )
            return sorted_queries[:limit]
    
    def reset_stats(self):
        """Reset all query statistics"""
        with self._lock:
            self.query_stats.clear()
            self.slow_queries.clear()
    
    def export_stats(self, file_path: str):
        """
        Export query statistics to a JSON file
        
        Args:
            file_path: Path to save the JSON file
        """
        with self._lock:
            data = {
                "timestamp": datetime.now().isoformat(),
                "slow_query_threshold_ms": self.slow_query_threshold_ms,
                "query_stats": self.query_stats,
                "slow_queries": self.slow_queries
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Query statistics exported to {file_path}")

# Global query monitor instance
query_monitor = QueryMonitor()

def setup_query_monitoring(engine: Engine, slow_query_threshold_ms: int = 100):
    """
    Set up query monitoring for a database engine
    
    Args:
        engine: SQLAlchemy engine to monitor
        slow_query_threshold_ms: Threshold in milliseconds to identify slow queries
    """
    global query_monitor
    query_monitor = QueryMonitor(slow_query_threshold_ms)
    query_monitor.register_with_engine(engine)
    return query_monitor