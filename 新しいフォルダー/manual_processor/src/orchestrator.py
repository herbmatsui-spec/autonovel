"""
Orchestrator Module
Coordinates the document processing workflow with threading and progress reporting
"""

import threading
import queue
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from config.config import Config
from src.processor.processor import DocumentProcessor
from src.logger import get_logger

logger = get_logger("orchestrator")


class ProcessingStatus:
    """Enum-like class for processing status"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingResult:
    """Container for processing results"""
    
    def __init__(self, success: bool, message: str = "", data: Optional[Dict] = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = time.time()


class DocumentOrchestrator:
    """Orchestrates document processing workflow"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.get_instance()
        self.processor = DocumentProcessor(self.config)
        self.logger = get_logger("orchestrator")
        
        # Threading components
        self.process_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        # Status tracking
        self.status = ProcessingStatus.IDLE
        self.current_file = None
        self.processed_files = []
        self.failed_files = []
        
        # Default generation options
        self.compact_layout = False
        self.use_emojis = False
        self.is_business_doc = False
        self.include_tables = False
        self.remove_markdown_bold = True
        
        # Callbacks
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
        
        self.logger.info("DocumentOrchestrator initialized")
    
    def start(self):
        """Start the orchestrator worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            self.logger.warning("Worker thread is already running")
            return
        
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("Orchestrator worker thread started")
    
    def stop(self):
        """Stop the orchestrator worker thread"""
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        self.logger.info("Orchestrator worker thread stopped")
    
    def process_file(self, file_path: Path, callback: Optional[Callable] = None, compact_layout: bool = False, use_emojis: bool = False, is_business_doc: bool = False, include_tables: bool = False, remove_markdown_bold: bool = True) -> ProcessingResult:
        """
        Process a single file synchronously
        
        Args:
            file_path: Path to the file to process
            callback: Optional callback function for progress updates
            compact_layout: If True, generate compact layout with larger text and less whitespace
            use_emojis: If True, insert emojis into generated documents
            is_business_doc: If True, process as a standard business document
            include_tables: If True, include table extraction in summarization
            remove_markdown_bold: If True, remove markdown bold markers (**) from Word output
            
        Returns:
            ProcessingResult object
        """
        try:
            self.logger.info(f"Starting synchronous processing of {file_path}")
            result = self.processor.process_pdf(file_path, compact_layout=compact_layout, use_emojis=use_emojis, is_business_doc=is_business_doc, include_tables=include_tables, remove_markdown_bold=remove_markdown_bold)
            
            if result["success"]:
                self.processed_files.append(file_path)
                return ProcessingResult(
                    success=True,
                    message=f"Successfully processed {file_path.name}",
                    data=result
                )
            else:
                self.failed_files.append((file_path, result["error"]))
                return ProcessingResult(
                    success=False,
                    message=f"Failed to process {file_path.name}: {result['error']}",
                    data=result
                )
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            self.failed_files.append((file_path, str(e)))
            return ProcessingResult(
                success=False,
                message=f"Error processing {file_path.name}: {str(e)}"
            )
    
    def add_file_to_queue(self, file_path: Path):
        """Add a file to the processing queue"""
        self.process_queue.put(file_path)
        self.logger.info(f"Added {file_path} to processing queue")
    
    def get_result(self, timeout: float = 1.0) -> Optional[ProcessingResult]:
        """
        Get a result from the result queue
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            ProcessingResult or None if timeout
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates"""
        self.progress_callback = callback
    
    def set_completion_callback(self, callback: Callable):
        """Set callback for completion notifications"""
        self.completion_callback = callback
    
    def _worker_loop(self):
        """Main worker loop for processing files"""
        self.logger.info("Worker loop started")
        
        while not self.stop_event.is_set():
            try:
                # Get file from queue with timeout
                try:
                    file_path = self.process_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the file
                self.status = ProcessingStatus.PROCESSING
                self.current_file = file_path
                
                self.logger.info(f"Processing {file_path}")
                
                # Notify progress if callback exists
                if self.progress_callback:
                    self.progress_callback({
                        "status": "started",
                        "file": str(file_path),
                        "progress": 0
                    })
                
                # Process the file
                result = self.processor.process_pdf(file_path, compact_layout=self.compact_layout, use_emojis=self.use_emojis, is_business_doc=self.is_business_doc, include_tables=self.include_tables, remove_markdown_bold=self.remove_markdown_bold)
                
                # Update status
                if result["success"]:
                    self.processed_files.append(file_path)
                    status_msg = f"Successfully processed {file_path.name}"
                    if self.progress_callback:
                        self.progress_callback({
                            "status": "completed",
                            "file": str(file_path),
                            "progress": 100,
                            "result": result
                        })
                else:
                    self.failed_files.append((file_path, result.get("error", "Unknown error")))
                    status_msg = f"Failed to process {file_path.name}: {result.get('error', 'Unknown error')}"
                    if self.progress_callback:
                        self.progress_callback({
                            "status": "failed",
                            "file": str(file_path),
                            "progress": 0,
                            "error": result.get("error", "Unknown error")
                        })
                
                # Put result in result queue
                self.result_queue.put(ProcessingResult(
                    success=result["success"],
                    message=status_msg,
                    data=result
                ))
                
                # Mark task as done
                self.process_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                if self.progress_callback:
                    self.progress_callback({
                        "status": "error",
                        "error": str(e)
                    })
            
            # Small sleep to prevent busy waiting
            time.sleep(0.1)
        
        self.logger.info("Worker loop ended")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status information"""
        return {
            "status": self.status,
            "current_file": str(self.current_file) if self.current_file else None,
            "processed_count": len(self.processed_files),
            "failed_count": len(self.failed_files),
            "queue_size": self.process_queue.qsize()
        }