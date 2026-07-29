"""
Manual Processor Main Entry Point
Processes manual PDFs using Google AI APIs and generates multiple output formats
"""

import argparse
import logging
import sys
from pathlib import Path

from ...src.config.config import Config
from ..src.logger import setup_logger, get_logger
from ..src.processor.document_processor import DocumentProcessorFactory

logger = get_logger("main")


def setup_logging():
    """Setup logging configuration"""
    # Configure root logger
    logger = get_logger("manual_processor")
    
    # Prevent duplicate logs from propagations
    logger.propagate = False
    
    # Set level from environment or default to INFO
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
    logger.setLevel(log_level)
    
    # Add file handler if log file is configured
    log_file = getattr(Config.get_instance(), 'log_file', None)
    if log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024, 
            backupCount=5,
            encoding='utf-8'
        )
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def main():
    """Main entry point"""
    # Setup logging first
    setup_logging()
    logger.info("=== Manual Processor Application Started ===")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Manual Processor - converts handwritten manuals to structured digital format"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Path to input PDF file"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in command-line mode"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Run in GUI mode"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory path"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Google API key"
    )
    
    args = parser.parse_args()
    
    # Apply logging configuration
    setup_logging()
    
    logger.debug("Command line arguments parsed")
    for arg, value in vars(args).items():
        logger.debug(f"Argument: {arg} = {value}")
    
    try:
        # Validate configuration
        config = Config.get_instance()
        config_errors = config.validate()
        if config_errors:
            for error in config_errors:
                logger.error(f"Configuration error: {error}")
            raise Exception("\n".join(config_errors))
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Apply API key if provided via CLI
    if args.api_key:
        os.environ["GOOGLE_API_KEY"] = args.api_key
        if "GEMINI_API_KEY" not in os.environ:
            os.environ["GEMINI_API_KEY"] = args.api_key
    
    # Initialize configuration update
    Config.get_instance().output_directory = Path(args.output_dir)
    
    if args.gui:
        logger.info("Starting GUI mode")
        try:
            from ..manual_processor.gui.app import main as gui_main
            gui_main()
        except ImportError:
            logger.error("GUI module not available. Please install required dependencies.")
            sys.exit(1)
    else:
        logger.info("Starting workflow processing")
        if args.input:
            # Process single file mode
            input_path = Path(args.input)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                sys.exit(1)
            
            from ..manual_processor.src.processor.processor import DocumentProcessingOrchestrator
            orchestrator = DocumentProcessingOrchestrator()
            result = orchestrator.process_single_file(input_path)
            
            if result["success"]:
                logger.info("Processing completed successfully")
                for file_path in ["PDF", "DOCX", "Audio"]:
                    if result.get(file_path):
                        logger.info(f"{file_path} generated: {result[file_path]}")
            else:
                logger.error(f"Processing failed: {result['error']}")
                sys.exit(1)
        else:
            logger.info("Starting file monitoring daemon")
            # This would normally start the monitoring daemon
            logger.info("ManualProcessor daemon started - monitoring for PDF files")


if __name__ == "__main__":
    # Set up proper schema for docstring validation if needed
    main()