"""
Adaptive connection pool manager that adjusts pool size based on load
"""

import time
import threading
import logging
from typing import Dict, Any, Optional
from sqlalchemy.engine import Engine

# Configure logger
logger = logging.getLogger(__name__)

class AdaptivePoolManager:
    """
    Manages database connection pool size dynamically based on load metrics
    
    Features:
    - Monitors connection usage and wait times
    - Adjusts pool size based on configurable thresholds
    - Prevents pool size thrashing with cooldown periods
    """
    
    def __init__(
        self, 
        engine: Engine,
        min_pool_size: int = 5,
        max_pool_size: int = 30,
        target_utilization: float = 0.7,
        scale_up_threshold: float = 0.8,
        scale_down_threshold: float = 0.3,
        check_interval_seconds: int = 30,
        cooldown_seconds: int = 60
    ):
        """
        Initialize adaptive pool manager
        
        Args:
            engine: SQLAlchemy engine to manage
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
            target_utilization: Target pool utilization (0.0-1.0)
            scale_up_threshold: Utilization threshold to scale up (0.0-1.0)
            scale_down_threshold: Utilization threshold to scale down (0.0-1.0)
            check_interval_seconds: Seconds between pool size checks
            cooldown_seconds: Seconds to wait after scaling before next adjustment
        """
        self.engine = engine
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.target_utilization = target_utilization
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.check_interval = check_interval_seconds
        self.cooldown_seconds = cooldown_seconds
        
        # Internal state
        self.current_pool_size = min_pool_size
        self.last_scale_time = 0
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        self.stats: Dict[str, Any] = {
            "scale_up_count": 0,
            "scale_down_count": 0,
            "peak_pool_size": min_pool_size,
            "peak_utilization": 0.0,
        }
        
    def start(self):
        """Start adaptive pool monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Adaptive pool monitoring already running")
            return
            
        # Set initial pool size
        self._set_pool_size(self.current_pool_size)
        
        # Start monitoring thread
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitor_pool,
            daemon=True,
            name="AdaptivePoolMonitor"
        )
        self.monitoring_thread.start()
        logger.info(f"Adaptive pool monitoring started (check interval: {self.check_interval}s)")
        
    def stop(self):
        """Stop adaptive pool monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.stop_monitoring.set()
            self.monitoring_thread.join(timeout=5.0)
            logger.info("Adaptive pool monitoring stopped")
        
    def _monitor_pool(self):
        """Monitor pool utilization and adjust size as needed"""
        while not self.stop_monitoring.is_set():
            try:
                # Get current pool metrics
                metrics = self._get_pool_metrics()
                utilization = metrics["utilization"]
                
                # Update stats
                self.stats["peak_utilization"] = max(
                    self.stats["peak_utilization"], 
                    utilization
                )
                
                # Check if we need to scale
                current_time = time.time()
                cooldown_elapsed = (current_time - self.last_scale_time) > self.cooldown_seconds
                
                if cooldown_elapsed:
                    if utilization > self.scale_up_threshold and self.current_pool_size < self.max_pool_size:
                        # Scale up - increase by 25% or at least 2 connections
                        new_size = min(
                            self.max_pool_size,
                            self.current_pool_size + max(2, int(self.current_pool_size * 0.25))
                        )
                        self._set_pool_size(new_size)
                        self.last_scale_time = current_time
                        self.stats["scale_up_count"] += 1
                        logger.info(f"Scaled up connection pool: {self.current_pool_size} → {new_size}")
                        
                    elif utilization < self.scale_down_threshold and self.current_pool_size > self.min_pool_size:
                        # Scale down - decrease by 20% or at least 1 connection
                        new_size = max(
                            self.min_pool_size,
                            self.current_pool_size - max(1, int(self.current_pool_size * 0.2))
                        )
                        self._set_pool_size(new_size)
                        self.last_scale_time = current_time
                        self.stats["scale_down_count"] += 1
                        logger.info(f"Scaled down connection pool: {self.current_pool_size} → {new_size}")
                
                # Log current metrics periodically
                logger.debug(
                    f"Pool metrics: size={self.current_pool_size}, "
                    f"utilization={utilization:.2f}, "
                    f"checkedout={metrics['checkedout']}, "
                    f"available={metrics['available']}"
                )
                
            except Exception as e:
                logger.error(f"Error in adaptive pool monitoring: {e}")
                
            # Wait for next check interval
            self.stop_monitoring.wait(self.check_interval)
    
    def _get_pool_metrics(self) -> Dict[str, Any]:
        """Get current connection pool metrics"""
        # Access SQLAlchemy pool metrics
        pool = self.engine.pool
        checkedout = pool.checkedout()
        available = pool.size()
        total = checkedout + available
        
        # Calculate utilization (avoid division by zero)
        utilization = checkedout / max(1, total)
        
        return {
            "checkedout": checkedout,
            "available": available,
            "total": total,
            "utilization": utilization
        }
    
    def _set_pool_size(self, new_size: int):
        """Set connection pool size"""
        # Try to adjust pool size in a safe manner
        try:
            pool_obj = getattr(self.engine, 'pool', None)
            if pool_obj is None:
                raise RuntimeError('Engine has no pool attribute')

            # Preferred: if the pool implementation exposes a public API, use it
            if hasattr(pool_obj, 'size') and hasattr(pool_obj, 'resize'):
                try:
                    pool_obj.resize(new_size)
                except Exception:
                    # Fallback to private attribute if available
                    if hasattr(pool_obj, '_pool') and hasattr(pool_obj._pool, 'maxsize'):
                        pool_obj._pool.maxsize = new_size
                    else:
                        raise
            else:
                # As a last resort, try the private attribute (fragile)
                if hasattr(pool_obj, '_pool') and hasattr(pool_obj._pool, 'maxsize'):
                    pool_obj._pool.maxsize = new_size
                else:
                    raise RuntimeError('Unable to resize pool; unsupported pool implementation')

        except Exception as e:
            logger.error(f"Failed to set pool size: {e}")
            raise

        self.current_pool_size = new_size

        # Update peak size stat
        self.stats["peak_pool_size"] = max(
            self.stats["peak_pool_size"], 
            new_size
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adaptive pool statistics"""
        stats = self.stats.copy()
        stats.update({
            "current_pool_size": self.current_pool_size,
            "min_pool_size": self.min_pool_size,
            "max_pool_size": self.max_pool_size,
            "target_utilization": self.target_utilization,
        })
        return stats

# Function to set up adaptive connection pooling
def setup_adaptive_pooling(
    engine: Engine,
    min_pool_size: int = 5,
    max_pool_size: int = 30,
    is_neon: bool = False
) -> AdaptivePoolManager:
    """
    Set up adaptive connection pooling for a database engine
    
    Args:
        engine: SQLAlchemy engine to manage
        min_pool_size: Minimum connection pool size
        max_pool_size: Maximum connection pool size
        is_neon: Whether using Neon PostgreSQL (serverless)
        
    Returns:
        AdaptivePoolManager instance
    """
    import os
    
    # Check if we're using Neon PostgreSQL
    if is_neon or os.getenv('NEON_DB_HOST'):
        # Neon serverless PostgreSQL optimization
        # Use smaller pool sizes and more aggressive scaling
        min_pool_size = min(3, min_pool_size)  # Smaller minimum for serverless
        max_pool_size = min(20, max_pool_size)  # Cap maximum for cost efficiency
        
        pool_manager = AdaptivePoolManager(
            engine=engine,
            min_pool_size=min_pool_size,
            max_pool_size=max_pool_size,
            scale_up_threshold=0.6,    # Scale up more aggressively
            scale_down_threshold=0.3,  # Scale down more aggressively
            check_interval_seconds=15  # More frequent monitoring
        )
    else:
        # Standard configuration for non-serverless
        pool_manager = AdaptivePoolManager(
            engine=engine,
            min_pool_size=min_pool_size,
            max_pool_size=max_pool_size
        )
    
    pool_manager.start()
    return pool_manager