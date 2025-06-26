#!/usr/bin/env python3
"""
Demonstration script showing improved error handling with proper logging.

This script shows the before/after comparison of error handling improvements.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from utils.logger import get_logger, log_exception, NetworkError, with_error_handling
from utils.config import Config
import requests
import time

# Set up logging
logger = get_logger(__name__)


def demonstrate_old_error_handling():
    """Example of old error handling with print statements."""
    print("=== OLD ERROR HANDLING (BEFORE) ===")
    
    try:
        # Simulate a network request that might fail
        response = requests.get("https://nonexistent-website-12345.com", timeout=5)
        print("Request succeeded")
    except Exception as e:
        print(f"Error downloading url: {e}")  # Old way - just print
        return False
    
    return True


def demonstrate_new_error_handling():
    """Example of new error handling with proper logging."""
    logger.info("=== NEW ERROR HANDLING (AFTER) ===")
    
    try:
        # Simulate a network request that might fail
        logger.debug("Attempting to fetch URL: https://nonexistent-website-12345.com")
        response = requests.get("https://nonexistent-website-12345.com", timeout=5)
        logger.info("Request succeeded")
        return True
    except requests.RequestException as e:
        # New way - specific exception types with proper logging
        log_exception(logger, e, "Network request failed")
        raise NetworkError(f"Failed to fetch URL: {e}")
    except Exception as e:
        # Catch-all with proper logging
        log_exception(logger, e, "Unexpected error occurred")
        return False


@with_error_handling(logger, "Error in decorated function", reraise=False)
def demonstrate_decorator_error_handling():
    """Example of decorator-based error handling."""
    logger.info("=== DECORATOR ERROR HANDLING ===")
    
    # This will raise an exception but be handled by the decorator
    result = 1 / 0
    return result


def demonstrate_recovery_strategies():
    """Example of error recovery strategies."""
    logger.info("=== ERROR RECOVERY STRATEGIES ===")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1}/{max_retries}")
            
            # Simulate operation that might fail
            if attempt < 2:  # Fail first two attempts
                raise requests.RequestException("Simulated network error")
            
            logger.info("Operation succeeded on retry")
            return True
            
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                retry_delay = 2 ** attempt  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                log_exception(logger, e, f"All {max_retries} attempts failed")
                return False
    
    return False


def demonstrate_context_logging():
    """Example of contextual logging."""
    logger.info("=== CONTEXTUAL ERROR LOGGING ===")
    
    manga_title = "Test Manga"
    chapter_no = "001"
    
    try:
        # Simulate chapter processing
        logger.debug(f"Processing chapter {chapter_no} of {manga_title}")
        
        # Simulate an error with context
        raise ValueError("Invalid chapter data format")
        
    except ValueError as e:
        # Log with rich context information
        logger.error(
            f"Chapter processing failed - Manga: {manga_title}, "
            f"Chapter: {chapter_no}, Error: {e}",
            exc_info=True
        )
        
        # Could implement recovery here
        logger.info(f"Skipping chapter {chapter_no} and continuing...")


def main():
    """Demonstrate the error handling improvements."""
    print(f"Error Handling Improvements Demo")
    print(f"=================================")
    print()
    
    # Validate configuration (this sets up logging)
    if not Config.validate_config():
        print("Configuration validation failed!")
        return 1
    
    logger.info("Starting error handling demonstration")
    
    try:
        # 1. Show old vs new basic error handling
        demonstrate_old_error_handling()
        print()
        
        try:
            demonstrate_new_error_handling()
        except NetworkError as e:
            logger.info(f"Caught custom exception: {e}")
        
        print()
        
        # 2. Show decorator-based error handling
        result = demonstrate_decorator_error_handling()
        logger.info(f"Decorator result: {result}")
        print()
        
        # 3. Show retry logic with proper logging
        success = demonstrate_recovery_strategies()
        logger.info(f"Recovery strategy result: {success}")
        print()
        
        # 4. Show contextual logging
        demonstrate_context_logging()
        print()
        
        logger.info("Error handling demonstration completed successfully")
        
        print("\n" + "="*50)
        print("IMPROVEMENTS SUMMARY:")
        print("✅ Replaced print() with proper logging levels")
        print("✅ Added structured logging with timestamps and context")
        print("✅ Implemented custom exception classes")
        print("✅ Added error recovery strategies with exponential backoff")
        print("✅ Created decorator for automatic error handling")
        print("✅ Added file logging with rotation")
        print("✅ Improved error context and stack traces")
        print("="*50)
        
        return 0
        
    except Exception as e:
        log_exception(logger, e, "Error in demonstration")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 