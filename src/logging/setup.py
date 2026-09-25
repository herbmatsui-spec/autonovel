import sys
from loguru import logger

def setup_logging():
    """
    Configure logging to output JSON format with rotation.
    Output to stdout for Docker compatibility.
    """
    # Remove default logger
    logger.remove()
    
    # Add stdout sink with JSON format
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        serialize=True,  # This formats the log as JSON
        backtrace=True,
        diagnose=True,
    )
    
    # Optional: file logging with rotation
    logger.add(
        "logs/app.log",
        rotation="100 MB",  # Rotate when file reaches 100 MB
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress rotated logs
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        serialize=True,
        enqueue=True,  # For async safety
    )
    
    return logger