"""
Enhanced batch processing system for Resume Customizer application.
Provides optimized batch operations, memory management, and parallel processing.
"""

import asyncio
import time
import gc
import threading
from typing import List, Dict, Any, Callable, Optional, AsyncGenerator, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import multiprocessing as mp
from functools import partial
import psutil

from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger
# Removed monitoring imports - monitoring disabled
from .enhanced_error_recovery import RobustResumeProcessor, get_error_recovery_manager
# Removed circuit breaker import - monitoring disabled

logger = get_logger()
structured_logger = get_structured_logger("batch_processor")


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 5
    max_workers: int = None  # Auto-detect
    use_processes: bool = False  # Use threads by default
    memory_threshold_mb: int = 500
    progress_callback: Optional[Callable] = None
    enable_caching: bool = True
    timeout_per_item: float = 30.0
    priority_processing: bool = True
    adaptive_batch_size: bool = True


@dataclass 
class BatchItem:
    """Item in batch processing queue."""
    id: str
    data: Dict[str, Any]
    priority: int = 0
    estimated_time: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue ordering."""
        return self.priority < other.priority


@dataclass
class BatchResult:
    """Result of batch processing operation."""
    success: bool
    item_id: str
    result: Any = None
    error: Optional[str] = None
    processing_time: float = 0.0
    memory_used_mb: float = 0.0
    cache_hit: bool = False
    retry_count: int = 0


class MemoryOptimizedBatchProcessor:
    """Batch processor with advanced memory management and optimization."""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        
        # Auto-detect optimal worker count
        if self.config.max_workers is None:
            cpu_count = mp.cpu_count()
            self.config.max_workers = min(cpu_count * 2, 8)  # Cap at 8
        
        # Disabled cache manager - monitoring removed
        self.cache_manager = None
        self.recovery_manager = get_error_recovery_manager()
        self.robust_processor = RobustResumeProcessor()
        
        # Statistics
        self._stats = {
            'total_processed': 0,
            'successful_items': 0,
            'failed_items': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'avg_processing_time': 0.0,
            'memory_cleanups': 0,
            'adaptive_adjustments': 0
        }
        self._stats_lock = threading.Lock()
        
        # Adaptive batch sizing
        self._performance_history = []
        self._current_batch_size = self.config.batch_size
        
        structured_logger.info(
            "Enhanced batch processor initialized",
            operation="batch_processor_init",
            max_workers=self.config.max_workers,
            batch_size=self.config.batch_size,
            use_processes=self.config.use_processes
        )
    
    async def process_resumes_batch(self, files: List[Any]) -> List[BatchResult]:
        """
        Process multiple resumes with optimized batching and memory management.
        
        Args:
            files: List of file objects to process
            
        Returns:
            List of processing results
        """
        start_time = time.time()
        
        structured_logger.info(
            f"Starting batch processing of {len(files)} files",
            operation="batch_start",
            file_count=len(files),
            batch_size=self._current_batch_size
        )
        
        try:
            # Convert files to batch items
            batch_items = self._prepare_batch_items(files)
            
            # Process in optimized batches
            results = await self._process_batch_items(batch_items)
            
            # Update statistics
            total_time = time.time() - start_time
            self._update_stats(results, total_time)
            
            structured_logger.info(
                f"Batch processing completed",
                operation="batch_complete",
                total_items=len(results),
                successful=sum(1 for r in results if r.success),
                failed=sum(1 for r in results if not r.success),
                total_time=total_time
            )
            
            return results
            
        except Exception as e:
            structured_logger.error(
                f"Batch processing failed: {e}",
                operation="batch_error",
                exception=e
            )
            raise
    
    def _prepare_batch_items(self, files: List[Any]) -> List[BatchItem]:
        """Prepare files for batch processing with priority and estimation."""
        batch_items = []
        
        for i, file_obj in enumerate(files):
            # Extract file information
            file_name = getattr(file_obj, 'name', f'file_{i}')
            file_size = getattr(file_obj, 'size', 0)
            
            # Estimate processing time based on file size
            estimated_time = self._estimate_processing_time(file_size)
            
            # Assign priority (smaller files first for quick wins)
            priority = self._calculate_priority(file_size, i)
            
            batch_items.append(BatchItem(
                id=f"item_{i}",
                data={
                    'file': file_obj,
                    'filename': file_name,
                    'file_size': file_size
                },
                priority=priority,
                estimated_time=estimated_time,
                metadata={'original_index': i}
            ))
        
        # Sort by priority if enabled
        if self.config.priority_processing:
            batch_items.sort()
        
        return batch_items
    
    def _estimate_processing_time(self, file_size: int) -> float:
        """Estimate processing time based on file size and historical data."""
        # Base estimate: 2 seconds + 0.1 seconds per KB
        base_time = 2.0 + (file_size / 1024) * 0.1
        
        # Adjust based on performance history
        if self._performance_history:
            recent_avg = sum(self._performance_history[-10:]) / len(self._performance_history[-10:])
            base_time *= recent_avg / 5.0  # Normalize to 5 second baseline
        
        return max(base_time, 1.0)  # Minimum 1 second
    
    def _calculate_priority(self, file_size: int, index: int) -> int:
        """Calculate processing priority (lower = higher priority)."""
        # Smaller files get higher priority for quick completion
        size_priority = file_size // 1024  # KB as priority component
        
        # Add index to maintain some order
        return size_priority + index
    
    async def _process_batch_items(self, items: List[BatchItem]) -> List[BatchResult]:
        """Process batch items with optimal batching strategy."""
        all_results = []
        
        # Process in adaptive batches
        for batch_start in range(0, len(items), self._current_batch_size):
            batch_end = min(batch_start + self._current_batch_size, len(items))
            batch = items[batch_start:batch_end]
            
            # Check memory before batch
            await self._check_and_manage_memory()
            
            # Process current batch
            batch_results = await self._process_single_batch(batch)
            all_results.extend(batch_results)
            
            # Update progress
            if self.config.progress_callback:
                progress = len(all_results) / len(items)
                self.config.progress_callback(f"Processed {len(all_results)}/{len(items)} files")
            
            # Adaptive batch size adjustment
            if self.config.adaptive_batch_size:
                self._adjust_batch_size(batch_results)
            
            # Brief pause between batches to prevent overwhelming
            if batch_end < len(items):
                await asyncio.sleep(0.1)
        
        return all_results
    
    async def _process_single_batch(self, batch: List[BatchItem]) -> List[BatchResult]:
        """Process a single batch of items."""
        structured_logger.debug(
            f"Processing batch of {len(batch)} items",
            operation="single_batch_start",
            batch_size=len(batch)
        )
        
        start_time = time.time()
        
        if self.config.use_processes:
            results = await self._process_with_multiprocessing(batch)
        else:
            results = await self._process_with_threading(batch)
        
        batch_time = time.time() - start_time
        
        structured_logger.debug(
            f"Batch completed in {batch_time:.2f}s",
            operation="single_batch_complete",
            batch_size=len(batch),
            batch_time=batch_time,
            avg_time_per_item=batch_time / len(batch) if batch else 0
        )
        
        return results
    
    async def _process_with_threading(self, batch: List[BatchItem]) -> List[BatchResult]:
        """Process batch using thread pool."""
        loop = asyncio.get_event_loop()
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                loop.run_in_executor(executor, self._process_single_item, item): item
                for item in batch
            }
            
            # Collect results as they complete
            for future in asyncio.as_completed(future_to_item.keys()):
                try:
                    result = await future
                    results.append(result)
                except Exception as e:
                    item = future_to_item[future]
                    results.append(BatchResult(
                        success=False,
                        item_id=item.id,
                        error=str(e),
                        retry_count=item.retry_count
                    ))
        
        return results
    
    async def _process_with_multiprocessing(self, batch: List[BatchItem]) -> List[BatchResult]:
        """Process batch using process pool."""
        loop = asyncio.get_event_loop()
        results = []
        
        # Prepare data for multiprocessing (must be serializable)
        serializable_batch = [
            {
                'id': item.id,
                'data': item.data,
                'metadata': item.metadata
            }
            for item in batch
        ]
        
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                loop.run_in_executor(executor, self._process_item_in_process, item_data): batch[i]
                for i, item_data in enumerate(serializable_batch)
            }
            
            # Collect results
            for future in asyncio.as_completed(future_to_item.keys()):
                try:
                    result = await future
                    results.append(result)
                except Exception as e:
                    item = future_to_item[future]
                    results.append(BatchResult(
                        success=False,
                        item_id=item.id,
                        error=str(e)
                    ))
        
        return results
    
    # Removed circuit breaker decorator - monitoring disabled
    def _process_single_item(self, item: BatchItem) -> BatchResult:
        """Process a single item with caching and error handling."""
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        # Check cache first
        cache_key = None
        if self.cache_manager and self.config.enable_caching:
            cache_key = self._generate_cache_key(item)
            cached_result = self.cache_manager.get('processing', cache_key)
            if cached_result is not None:
                with self._stats_lock:
                    self._stats['cache_hits'] += 1
                
                return BatchResult(
                    success=True,
                    item_id=item.id,
                    result=cached_result,
                    processing_time=time.time() - start_time,
                    cache_hit=True
                )
        
        try:
            # Process the item
            result = self.robust_processor.process_single_resume(item.data)
            
            # Cache the result
            if self.cache_manager and cache_key and self.config.enable_caching:
                self.cache_manager.set('processing', cache_key, result, ttl=3600)
            
            memory_after = self._get_memory_usage()
            
            return BatchResult(
                success=result.get('success', False),
                item_id=item.id,
                result=result,
                processing_time=time.time() - start_time,
                memory_used_mb=memory_after - memory_before,
                retry_count=item.retry_count
            )
            
        except Exception as e:
            structured_logger.error(
                f"Item processing failed: {e}",
                operation="item_processing_error",
                item_id=item.id,
                error=str(e)
            )
            
            return BatchResult(
                success=False,
                item_id=item.id,
                error=str(e),
                processing_time=time.time() - start_time,
                retry_count=item.retry_count
            )
    
    def _process_item_in_process(self, item_data: Dict[str, Any]) -> BatchResult:
        """Process item in separate process (for multiprocessing)."""
        # This would be called in a separate process
        # Need to recreate necessary objects
        try:
            from enhanced_error_recovery import RobustResumeProcessor
            processor = RobustResumeProcessor()
            
            start_time = time.time()
            result = processor.process_single_resume(item_data['data'])
            
            return BatchResult(
                success=result.get('success', False),
                item_id=item_data['id'],
                result=result,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return BatchResult(
                success=False,
                item_id=item_data['id'],
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _generate_cache_key(self, item: BatchItem) -> str:
        """Generate cache key for item."""
        key_parts = [
            item.data.get('filename', 'unknown'),
            str(item.data.get('file_size', 0)),
            # Add hash of file content if available
        ]
        return '|'.join(key_parts)
    
    async def _check_and_manage_memory(self):
        """Check memory usage and manage if necessary."""
        try:
            memory = psutil.virtual_memory()
            memory_usage_mb = memory.used / (1024 * 1024)
            
            if memory_usage_mb > self.config.memory_threshold_mb:
                structured_logger.info(
                    f"Memory cleanup triggered: {memory_usage_mb:.1f}MB used",
                    operation="memory_cleanup",
                    memory_usage_mb=memory_usage_mb
                )
                
                # Perform cleanup
                if self.cache_manager:
                    # Clear some cache entries
                    stats = self.cache_manager.get_stats()
                    if stats.get('l1_cache', {}).get('size', 0) > 100:
                        # Clear 30% of L1 cache
                        self.cache_manager.local_cache._evict_if_necessary()
                
                # Force garbage collection
                gc.collect()
                
                with self._stats_lock:
                    self._stats['memory_cleanups'] += 1
                
                # Brief pause to let memory settle
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.warning(f"Memory management failed: {e}")
    
    def _adjust_batch_size(self, batch_results: List[BatchResult]):
        """Adjust batch size based on performance metrics."""
        if not self.config.adaptive_batch_size:
            return
        
        try:
            # Calculate average processing time for this batch
            successful_results = [r for r in batch_results if r.success]
            if not successful_results:
                return
            
            avg_time = sum(r.processing_time for r in successful_results) / len(successful_results)
            self._performance_history.append(avg_time)
            
            # Keep only recent history
            if len(self._performance_history) > 20:
                self._performance_history = self._performance_history[-20:]
            
            # Adjust batch size based on performance
            if len(self._performance_history) >= 3:
                recent_avg = sum(self._performance_history[-3:]) / 3
                overall_avg = sum(self._performance_history) / len(self._performance_history)
                
                if recent_avg < overall_avg * 0.8:  # Performance improved
                    self._current_batch_size = min(self._current_batch_size + 1, 10)
                elif recent_avg > overall_avg * 1.2:  # Performance degraded
                    self._current_batch_size = max(self._current_batch_size - 1, 2)
                
                if self._current_batch_size != self.config.batch_size:
                    with self._stats_lock:
                        self._stats['adaptive_adjustments'] += 1
                    
                    structured_logger.debug(
                        f"Adaptive batch size adjusted to {self._current_batch_size}",
                        operation="batch_size_adjustment",
                        new_size=self._current_batch_size,
                        recent_avg=recent_avg,
                        overall_avg=overall_avg
                    )
        
        except Exception as e:
            logger.warning(f"Batch size adjustment failed: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    def _update_stats(self, results: List[BatchResult], total_time: float):
        """Update processing statistics."""
        with self._stats_lock:
            self._stats['total_processed'] += len(results)
            self._stats['successful_items'] += sum(1 for r in results if r.success)
            self._stats['failed_items'] += sum(1 for r in results if not r.success)
            self._stats['total_time'] += total_time
            
            if results:
                avg_processing_time = sum(r.processing_time for r in results) / len(results)
                self._stats['avg_processing_time'] = avg_processing_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        # Calculate derived metrics
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['successful_items'] / stats['total_processed']
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['total_processed']
        else:
            stats['success_rate'] = 0
            stats['cache_hit_rate'] = 0
        
        stats['current_batch_size'] = self._current_batch_size
        stats['performance_history_length'] = len(self._performance_history)
        
        return stats


# Global batch processor instance
_batch_processor = None
_processor_lock = threading.Lock()


def get_batch_processor(config: Optional[BatchConfig] = None) -> MemoryOptimizedBatchProcessor:
    """Get global batch processor instance."""
    global _batch_processor
    
    with _processor_lock:
        if _batch_processor is None:
            _batch_processor = MemoryOptimizedBatchProcessor(config)
        return _batch_processor


async def process_resumes_optimized(files: List[Any], 
                                  config: Optional[BatchConfig] = None,
                                  progress_callback: Optional[Callable] = None) -> List[BatchResult]:
    """
    Optimized batch processing function for resumes.
    
    Args:
        files: List of file objects to process
        config: Batch processing configuration
        progress_callback: Optional progress callback function
        
    Returns:
        List of processing results
    """
    if config is None:
        config = BatchConfig()
    
    if progress_callback:
        config.progress_callback = progress_callback
    
    processor = get_batch_processor(config)
    return await processor.process_resumes_batch(files)



