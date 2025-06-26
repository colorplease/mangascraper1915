"""
Centralized logging configuration for the webtoon scraper application.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

# Get the logs directory from config
try:
    from utils.config import Config
    LOGS_DIR = Config.LOGS_DIR
except ImportError:
    LOGS_DIR = Path.cwd() / "logs"

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Add color to levelname
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        
        return super().format(record)


def setup_logging(
    name: Optional[str] = None,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up centralized logging configuration.
    
    Args:
        name: Logger name (defaults to the calling module)
        level: Logging level
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or __name__)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler with rotation
    if log_to_file:
        log_file = LOGS_DIR / "manga_scraper.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with standard configuration.
    
    Args:
        name: Logger name (defaults to the calling module)
        
    Returns:
        Logger instance
    """
    if not name:
        # Get the calling module's name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'manga_scraper')
    
    return setup_logging(name)


# Set up root logger for the application
def configure_root_logger():
    """Configure the root logger for the entire application."""
    root_logger = logging.getLogger('manga_scraper')
    
    if not root_logger.handlers:
        setup_logging('manga_scraper', level=logging.INFO)
    
    return root_logger


# Configure on import
configure_root_logger()


# Custom exception classes for better error handling
class ScrapingError(Exception):
    """Base exception for scraping-related errors."""
    pass


class NetworkError(ScrapingError):
    """Exception for network-related errors."""
    pass


class ParsingError(ScrapingError):
    """Exception for HTML parsing errors."""
    pass


class DatabaseError(ScrapingError):
    """Exception for database-related errors."""
    pass


class ValidationError(ScrapingError):
    """Exception for data validation errors."""
    pass


def log_exception(logger: logging.Logger, e: Exception, context: str = "") -> None:
    """
    Log an exception with context information.
    
    Args:
        logger: Logger instance
        e: Exception to log
        context: Additional context information
    """
    if context:
        logger.error(f"{context}: {type(e).__name__}: {e}", exc_info=True)
    else:
        logger.error(f"{type(e).__name__}: {e}", exc_info=True)


def with_error_handling(logger: logging.Logger, context: str = "", reraise: bool = False):
    """
    Decorator for automatic error handling and logging.
    
    Args:
        logger: Logger instance
        context: Context description for the operation
        reraise: Whether to reraise the exception after logging
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_exception(logger, e, context or f"Error in {func.__name__}")
                if reraise:
                    raise
                return None
        return wrapper
    return decorator 