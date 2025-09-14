import streamlit as st
"""
Email handling module for Resume Customizer application.
Handles SMTP connections, email sending, and connection pooling.
"""

import smtplib
import threading
from contextlib import contextmanager
from collections import defaultdict
from typing import List, Dict, Any, Optional
from email.message import EmailMessage

try:
    from config import SMTP_SERVERS, ERROR_MESSAGES
except ImportError:
    # Fallback if SMTP_SERVERS not defined in config
    SMTP_SERVERS = {}
    ERROR_MESSAGES = {}
from infrastructure.utilities.retry_handler import get_retry_handler, with_retry
from infrastructure.utilities.logger import get_logger
from infrastructure.security.security_enhancements import SecurePasswordManager, InputSanitizer, rate_limit
# Removed circuit breaker import - monitoring disabled
from enhancements.metrics_analytics_enhanced import record_email_sent
from enhancements.email_templates_enhanced import get_template_manager


logger = get_logger()

# --- Profiling Decorator ---
import time
def profile_step(step_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            if duration > 1.0:  # Log only slow steps (>1s)
                logger.info(f"[PROFILE] {step_name} took {duration:.2f}s")
            return result
        return wrapper
    return decorator


class SMTPConnectionPool:
    """Thread-safe SMTP connection pool for efficient email sending."""
    
    def __init__(self):
        self._connections = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def get_connection(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str):
        """
        Get or create an SMTP connection from the pool.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            sender_email: Sender email address
            sender_password: Sender email password
            
        Yields:
            SMTP connection object
            
        Raises:
            Exception: If connection creation fails
        """
        connection_key = f"{smtp_server}:{smtp_port}:{sender_email}"
        
        with self._lock:
            if connection_key not in self._connections:
                try:
                    # Support both SSL (port 465) and TLS (port 587)
                    if smtp_port == 465:
                        smtp = smtplib.SMTP_SSL(smtp_server, smtp_port)
                    else:
                        smtp = smtplib.SMTP(smtp_server, smtp_port)
                        smtp.starttls()
                    smtp.login(sender_email, sender_password)
                    self._connections[connection_key] = smtp
                except Exception as e:
                    raise Exception(ERROR_MESSAGES["smtp_connection_failed"].format(error=str(e)))
        
        try:
            yield self._connections[connection_key]
        except Exception as e:
            # If connection fails, remove it from pool
            with self._lock:
                if connection_key in self._connections:
                    try:
                        self._connections[connection_key].quit()
                    except:
                        pass
                    del self._connections[connection_key]
            raise e
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            for smtp in self._connections.values():
                try:
                    smtp.quit()
                except:
                    pass
            self._connections.clear()


class EmailSender:
    """Handles individual email sending operations with security enhancements."""
    
    def __init__(self, connection_pool: SMTPConnectionPool):
        self.connection_pool = connection_pool
        self.password_manager = SecurePasswordManager()
        self.sanitizer = InputSanitizer()
    
    def _decrypt_password_if_needed(self, password: str) -> str:
        """Decrypt password if it's encrypted, otherwise return as-is."""
        try:
            # Check if it's encrypted bytes (base64 encoded)
            if isinstance(password, str) and len(password) > 50 and password.count('=') <= 2:
                # Might be encrypted, try to decrypt
                import base64
                try:
                    encrypted_bytes = base64.b64decode(password)
                    return self.password_manager.decrypt_password(encrypted_bytes)
                except Exception:
                    # Not encrypted, return as-is
                    return password
            return password
        except Exception as e:
            logger.warning(f"Password decryption failed: {e}")
            return password
    
    # Removed circuit breaker decorator - monitoring disabled
    @with_retry(max_attempts=3, base_delay=2.0)
    @rate_limit("email_send", limit=10, window=300)  # 10 emails per 5 minutes
    def send_single_email(
        self, 
        smtp_server: str, 
        smtp_port: int,
        sender_email: str,
        sender_password: str,  # This should be encrypted bytes in production
        recipient_email: str,
        subject: str,
        body: str,
        attachment_data: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Send a single email with attachment.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            sender_email: Sender email address
            sender_password: Sender email password
            recipient_email: Recipient email address
            subject: Email subject
            body: Email body
            attachment_data: File attachment data
            filename: Attachment filename
            
        Returns:
            Result dictionary with success status and details
        """
        # Sanitize inputs for security
        sender_email = self.sanitizer.sanitize_email(sender_email)
        recipient_email = self.sanitizer.sanitize_email(recipient_email)
        filename = self.sanitizer.sanitize_filename(filename)
        subject = self.sanitizer.sanitize_text_input(subject, max_length=200)
        body = self.sanitizer.sanitize_text_input(body, max_length=10000)
        
        if smtp_server == "Custom":
            return {
                'success': False,
                'filename': filename,
                'error': ERROR_MESSAGES["custom_smtp_not_supported"]
            }
        
        try:
            logger.info(f"Sending email for {filename} to {recipient_email}")
            
            # Decrypt password if needed
            decrypted_password = self._decrypt_password_if_needed(sender_password)
            
            with self.connection_pool.get_connection(smtp_server, smtp_port, sender_email, decrypted_password) as smtp:
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = sender_email
                msg['To'] = recipient_email
                msg.set_content(body)
                
                msg.add_attachment(
                    attachment_data,
                    maintype='application',
                    subtype='vnd.openxmlformats-officedocument.wordprocessingml.document',
                    filename=filename
                )
                
                smtp.send_message(msg)
                logger.info(f"Email sent successfully for {filename}")
                
                return {
                    'success': True,
                    'filename': filename,
                    'recipient': recipient_email
                }
                
        except Exception as e:
            logger.error(f"Failed to send email for {filename}", exception=e)
            return {
                'success': False,
                'filename': filename,
                'error': ERROR_MESSAGES["email_send_failed"].format(filename=filename, error=str(e))
            }


class BatchEmailSender:
    """Handles batch email sending with optimization."""
    
    def __init__(self, connection_pool: SMTPConnectionPool):
        self.connection_pool = connection_pool
        self.email_sender = EmailSender(connection_pool)
    
    def send_emails_batch(
        self, 
        email_tasks: List[Dict[str, Any]], 
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Send multiple emails using connection pooling and server grouping.
        
        @profile_step("send_emails_batch")
            results = []
            email_tasks: List of email task dictionaries
            progress_callback: Optional progress callback function
            
        Returns:
            List of result dictionaries
        """
        results = []
        
        # Group emails by SMTP server for efficiency
        server_groups = self._group_by_server(email_tasks)
        
        for server_key, tasks in server_groups.items():
            if not tasks:
                continue
            
            results.extend(self._send_server_group(tasks, progress_callback))
        
        return results
    
    def _group_by_server(self, email_tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group email tasks by SMTP server and sender for efficient connection reuse.
        
        Args:
            email_tasks: List of email task dictionaries
            
        Returns:
            Dictionary with server keys and grouped tasks
        """
        server_groups = defaultdict(list)
        
        for task in email_tasks:
            email_data = task.get('email_data', {})
            if email_data.get('recipient') and email_data.get('sender'):
                key = f"{email_data.get('smtp_server')}:{email_data.get('sender')}"
                server_groups[key].append(task)
        
        return server_groups
    
    def _send_server_group(
        self,
        tasks: List[Dict[str, Any]],
        progress_callback: Optional[callable]
    ) -> List[Dict[str, Any]]:
        """
        Send emails for a specific server group using threads for parallelism.
        """
        import concurrent.futures
        results = []
        if not tasks:
            return results
        first_task = tasks[0]
        email_data = first_task['email_data']
        smtp_server = email_data.get('smtp_server', '')
        smtp_port = email_data.get('smtp_port', 465)
        sender_email = email_data.get('sender', '')
        sender_password = email_data.get('password', '')
        if smtp_server == "Custom":
            for task in tasks:
                results.append({
                    'success': False,
                    'filename': task['filename'],
                    'error': ERROR_MESSAGES["custom_smtp_not_supported"]
                })
            return results
        # Use a single SMTP connection, but send emails in parallel threads
        try:
            with self.connection_pool.get_connection(smtp_server, smtp_port, sender_email, sender_password) as smtp:
                def send_task(task):
                    return self._send_single_email_with_connection(smtp, task, progress_callback)
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(tasks))) as executor:
                    future_to_task = {executor.submit(send_task, task): task for task in tasks}
                    for future in concurrent.futures.as_completed(future_to_task):
                        try:
                            result = future.result()
                        except Exception as e:
                            result = {'success': False, 'filename': future_to_task[future]['filename'], 'error': str(e)}
                        results.append(result)
        except Exception as e:
            for task in tasks:
                results.append({
                    'success': False,
                    'filename': task['filename'],
                    'error': f'SMTP connection failed: {str(e)}'
                })
        return results
    
    def _send_single_email_with_connection(
        self, 
        smtp_connection, 
        task: Dict[str, Any], 
        progress_callback: Optional[callable]
    ) -> Dict[str, Any]:
        """
        Send a single email using an existing SMTP connection.
        
        Args:
            smtp_connection: Existing SMTP connection
            task: Email task dictionary
            progress_callback: Optional progress callback
            
        Returns:
            Result dictionary
        """
        try:
            if progress_callback:
                progress_callback(f"Sending email for {task['filename']}...")
            
            email_data = task['email_data']
            
            msg = EmailMessage()
            msg['Subject'] = email_data.get('subject', '')
            msg['From'] = email_data.get('sender', '')
            msg['To'] = email_data.get('recipient', '')
            msg.set_content(email_data.get('body', ''))
            
            msg.add_attachment(
                task['buffer'],
                maintype='application',
                subtype='vnd.openxmlformats-officedocument.wordprocessingml.document',
                filename=task['filename']
            )
            
            smtp_connection.send_message(msg)
            
            return {
                'success': True,
                'filename': task['filename'],
                'recipient': email_data.get('recipient', '')
            }
            
        except Exception as e:
            return {
                'success': False,
                'filename': task['filename'],
                'error': str(e)
            }


class EmailValidator:
    """Validates email configuration and data."""
    
    @staticmethod
    def validate_email_data(email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate email configuration data.
        
        Args:
            email_data: Email configuration dictionary
            
        Returns:
            Validation result with missing fields and status
        """
        required_fields = {
            'recipient': 'Recipient Email',
            'sender': 'Sender Email', 
            'password': 'Sender Password',
            'subject': 'Email Subject',
            'body': 'Email Body'
        }
        
        missing_fields = []
        for field, display_name in required_fields.items():
            if not email_data.get(field, '').strip():
                missing_fields.append(display_name)
        
        return {
            'valid': len(missing_fields) == 0,
            'missing_fields': missing_fields
        }
    
    @staticmethod
    def get_smtp_config(server_name: str) -> Dict[str, Any]:
        """
        Get SMTP configuration for a given server name.
        
        Args:
            server_name: Name of the SMTP server
            
        Returns:
            SMTP configuration dictionary
        """
        for name, config in SMTP_SERVERS.items():
            if config['server'] == server_name or name.lower() in server_name.lower():
                return config
        
        # Default configuration
        return {'server': server_name, 'port': 587}


class EmailManager:
    """Main email manager that coordinates all email operations."""
    
    def __init__(self):
        self.connection_pool = SMTPConnectionPool()
        self.batch_sender = BatchEmailSender(self.connection_pool)
        self.validator = EmailValidator()
    
    def send_single_email(
        self, 
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
        subject: str,
        body: str,
        attachment_data: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Send a single email.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            sender_email: Sender email address
            sender_password: Sender email password
            recipient_email: Recipient email address
            subject: Email subject
            body: Email body
            attachment_data: File attachment data
            filename: Attachment filename
            
        Returns:
            Result dictionary
        """
        email_sender = EmailSender(self.connection_pool)
        return email_sender.send_single_email(
            smtp_server, smtp_port, sender_email, sender_password,
            recipient_email, subject, body, attachment_data, filename
        )
    
    def send_batch_emails(
        self, 
        email_tasks: List[Dict[str, Any]], 
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Send multiple emails in batch.
        
        Args:
            email_tasks: List of email task dictionaries
            progress_callback: Optional progress callback
            
        Returns:
            List of result dictionaries
        """
        return self.batch_sender.send_emails_batch(email_tasks, progress_callback)
    
    def validate_email_config(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate email configuration.
        
        Args:
            email_data: Email configuration dictionary
            
        Returns:
            Validation result
        """
        return self.validator.validate_email_data(email_data)
    
    def close_all_connections(self) -> None:
        """Close all SMTP connections."""
        self.connection_pool.close_all()


# Global email manager instance
email_manager = EmailManager()


@st.cache_resource
def get_email_manager() -> EmailManager:
    """
    Get the global email manager instance.
    
    Returns:
        EmailManager instance
    """
    return email_manager


def send_emails_batch(
    email_tasks: List[Dict[str, Any]], 
    progress_callback: Optional[callable] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to send batch emails.
    
    Args:
        email_tasks: List of email task dictionaries
        progress_callback: Optional progress callback
        
    Returns:
        List of result dictionaries
    """
    return email_manager.send_batch_emails(email_tasks, progress_callback)


