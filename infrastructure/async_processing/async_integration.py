"""
Async Integration Module for Resume Customizer
Provides asynchronous processing capabilities for bulk operations
"""

import logging
from typing import List, Dict, Any, Optional
import uuid
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

# Global thread pool for async processing
_thread_pool = None
_active_tasks = {}

def initialize_async_services(max_workers: int = 4) -> bool:
    """
    Initialize async processing capabilities
    
    Args:
        max_workers: Maximum number of worker threads
        
    Returns:
        bool: True if initialization successful
    """
    return initialize_async_processing(max_workers)

def initialize_async_processing(max_workers: int = 4) -> bool:
    """
    Initialize async processing capabilities
    
    Args:
        max_workers: Maximum number of worker threads
        
    Returns:
        bool: True if initialization successful
    """
    global _thread_pool
    try:
        _thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"Async processing initialized with {max_workers} workers")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize async processing: {e}")
        return False

def process_documents_async(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process documents asynchronously
    
    Args:
        documents: List of document data dictionaries
        
    Returns:
        Dict containing success status, message, and task IDs
    """
    try:
        if not _thread_pool:
            logger.warning("Async processing not initialized, falling back to sync")
            return {
                "success": False,
                "message": "Async processing not available",
                "task_ids": []
            }
        
        task_ids = []
        for doc in documents:
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            
            # Store task info
            _active_tasks[task_id] = {
                "status": "submitted",
                "document": doc,
                "result": None,
                "error": None,
                "timestamp": time.time()
            }
            
            # Submit task to thread pool
            future = _thread_pool.submit(_process_single_document, task_id, doc)
            _active_tasks[task_id]["future"] = future
        
        logger.info(f"Submitted {len(task_ids)} documents for async processing")
        return {
            "success": True,
            "message": f"Successfully submitted {len(task_ids)} documents for processing",
            "task_ids": task_ids
        }
        
    except Exception as e:
        logger.error(f"Error submitting async tasks: {e}")
        return {
            "success": False,
            "message": f"Failed to submit tasks: {str(e)}",
            "task_ids": []
        }

def _process_single_document(task_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single document (internal function)
    
    Args:
        task_id: Unique task identifier
        document: Document data
        
    Returns:
        Processing result
    """
    try:
        _active_tasks[task_id]["status"] = "processing"
        
        # Simulate processing (replace with actual document processing logic)
        time.sleep(1)  # Simulate work
        
        result = {
            "filename": document.get("filename", "unknown"),
            "processed": True,
            "tech_stacks": document.get("tech_stacks", {}),
            "timestamp": time.time()
        }
        
        _active_tasks[task_id]["status"] = "completed"
        _active_tasks[task_id]["result"] = result
        
        logger.info(f"Task {task_id} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        _active_tasks[task_id]["status"] = "failed"
        _active_tasks[task_id]["error"] = str(e)
        return {"error": str(e)}

def get_async_results(task_ids: List[str]) -> Dict[str, Any]:
    """
    Get results for async tasks
    
    Args:
        task_ids: List of task IDs to check
        
    Returns:
        Dict containing task statuses and results
    """
    try:
        results = {}
        
        for task_id in task_ids:
            if task_id in _active_tasks:
                task_info = _active_tasks[task_id]
                results[task_id] = {
                    "status": task_info["status"],
                    "result": task_info.get("result"),
                    "error": task_info.get("error"),
                    "timestamp": task_info.get("timestamp")
                }
                
                # Check if future is done
                if "future" in task_info and task_info["future"].done():
                    try:
                        future_result = task_info["future"].result()
                        if task_info["status"] != "failed":
                            results[task_id]["result"] = future_result
                    except Exception as e:
                        results[task_id]["status"] = "failed"
                        results[task_id]["error"] = str(e)
            else:
                results[task_id] = {
                    "status": "not_found",
                    "error": "Task not found"
                }
        
        return {
            "success": True,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error getting async results: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": {}
        }

def cleanup_completed_tasks(max_age_seconds: int = 3600) -> None:
    """
    Clean up old completed tasks
    
    Args:
        max_age_seconds: Maximum age of tasks to keep in seconds
    """
    try:
        current_time = time.time()
        to_remove = []
        
        for task_id, task_info in _active_tasks.items():
            if task_info.get("timestamp", 0) + max_age_seconds < current_time:
                if task_info["status"] in ["completed", "failed"]:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del _active_tasks[task_id]
            
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")
            
    except Exception as e:
        logger.error(f"Error cleaning up tasks: {e}")

def get_async_status() -> Dict[str, Any]:
    """
    Get overall async processing status
    
    Returns:
        Dict containing status information
    """
    try:
        total_tasks = len(_active_tasks)
        status_counts = {}
        
        for task_info in _active_tasks.values():
            status = task_info["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "initialized": _thread_pool is not None,
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "active_tasks": list(_active_tasks.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting async status: {e}")
        return {
            "initialized": False,
            "error": str(e)
        }

def shutdown_async_processing() -> None:
    """Shutdown async processing and cleanup resources"""
    global _thread_pool, _active_tasks
    
    try:
        if _thread_pool:
            _thread_pool.shutdown(wait=True)
            _thread_pool = None
            
        _active_tasks.clear()
        logger.info("Async processing shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during async processing shutdown: {e}")