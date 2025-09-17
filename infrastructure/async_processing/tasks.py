from ..config.celeryconfig import celery_app
from resume_customizer.processors.resume_processor import ResumeProcessor
from io import BytesIO
import base64

@celery_app.task(bind=True)
def process_resume_task(self, file_data):
    """
    Process resume task with proper file deserialization.
    
    Args:
        file_data: Dictionary containing serialized file data and processing parameters
        
    Returns:
        Dictionary with processing results
    """
    def safe_update_state(state, meta=None):
        """Safely update task state, handling direct calls gracefully."""
        try:
            if hasattr(self, 'request') and self.request and self.request.id:
                self.update_state(state=state, meta=meta)
        except (AttributeError, ValueError):
            # Direct call without Celery context, just print status
            print(f"Task status: {state} - {meta}")
    
    try:
        # Update task status
        safe_update_state(
            state='PROGRESS',
            meta={'status': 'Starting resume processing...', 'progress': 0}
        )
        
        # Deserialize file content from base64
        if 'file_content_b64' in file_data:
            file_content = base64.b64decode(file_data['file_content_b64'])
            file_obj = BytesIO(file_content)
            # Replace the base64 content with actual file object
            file_data['file'] = file_obj
            # Remove the base64 content to save memory
            del file_data['file_content_b64']
        else:
            raise ValueError("No file content found in task data")
        
        # Update task status
        safe_update_state(
            state='PROGRESS',
            meta={'status': 'Processing document...', 'progress': 25}
        )
        
        # Process the resume
        processor = ResumeProcessor()
        
        def progress_callback(msg):
            """Update task progress."""
            safe_update_state(
                state='PROGRESS',
                meta={'status': msg, 'progress': 50}
            )
        
        result = processor.process_single_resume(file_data, progress_callback=progress_callback)
        
        # Update final status
        if result.get('success'):
            safe_update_state(
                state='PROGRESS',
                meta={'status': 'Resume processed successfully!', 'progress': 100}
            )
        
        return result
        
    except Exception as e:
        # Update task with error status
        safe_update_state(
            state='FAILURE',
            meta={'error': str(e), 'status': 'Task failed'}
        )
        raise



