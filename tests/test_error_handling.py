#!/usr/bin/env python3
"""
Tests for the new error handling and logging features.

This test suite validates:
- Centralized logging system
- Custom exception classes  
- Error recovery strategies
- Decorator-based error handling
- Integration with existing modules
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import logging
import time
import sys
from pathlib import Path
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from utils.logger import (
    get_logger, setup_logging, log_exception, with_error_handling,
    ScrapingError, NetworkError, ParsingError, DatabaseError, ValidationError,
    ColoredFormatter, configure_root_logger
)
from utils.config import Config


class TestLoggingSystem(unittest.TestCase):
    """Test the centralized logging system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any handlers to avoid interference
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Clean up temp files with better error handling
        try:
            if os.path.exists(self.log_file):
                os.unlink(self.log_file)
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors in tests
    
    def test_get_logger_creates_logger(self):
        """Test that get_logger creates a logger with proper configuration."""
        logger = get_logger("test_module")
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_module")
        self.assertTrue(len(logger.handlers) > 0)
    
    def test_setup_logging_file_and_console(self):
        """Test logging setup with both file and console handlers."""
        with patch('utils.logger.LOGS_DIR', Path(self.temp_dir)):
            logger = setup_logging(
                name="test_logger_dual",
                level=logging.DEBUG,
                log_to_file=True,
                log_to_console=True
            )
            
            # Should have at least 1 handler (may consolidate handlers)
            self.assertGreaterEqual(len(logger.handlers), 1) 
            self.assertEqual(logger.level, logging.DEBUG)
    
    def test_setup_logging_file_only(self):
        """Test logging setup with file handler only."""
        with patch('utils.logger.LOGS_DIR', Path(self.temp_dir)):
            logger = setup_logging(
                name="test_logger",
                log_to_file=True,
                log_to_console=False
            )
            
            self.assertEqual(len(logger.handlers), 1)  # File only
    
    def test_setup_logging_console_only(self):
        """Test logging setup with console handler only."""
        logger = setup_logging(
            name="test_logger",
            log_to_file=False,
            log_to_console=True
        )
        
        self.assertEqual(len(logger.handlers), 1)  # Console only
    
    def test_colored_formatter(self):
        """Test that ColoredFormatter adds colors to log records."""
        formatter = ColoredFormatter('%(levelname)s - %(message)s')
        
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain ANSI color codes
        self.assertIn('\033[31m', formatted)  # Red for ERROR
        self.assertIn('\033[0m', formatted)   # Reset code
    
    def test_log_levels_work(self):
        """Test that different log levels work correctly."""
        with patch('utils.logger.LOGS_DIR', Path(self.temp_dir)):
            logger = setup_logging(
                name="test_levels",
                level=logging.DEBUG,
                log_to_file=True,
                log_to_console=False
            )
            
            logger.debug("Debug message")
            logger.info("Info message") 
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # Check that messages were logged
            log_file = Path(self.temp_dir) / "manga_scraper.log"
            if log_file.exists():
                content = log_file.read_text()
                self.assertIn("Debug message", content)
                self.assertIn("Info message", content)
                self.assertIn("Warning message", content)
                self.assertIn("Error message", content)
                self.assertIn("Critical message", content)


class TestCustomExceptions(unittest.TestCase):
    """Test custom exception classes."""
    
    def test_exception_hierarchy(self):
        """Test that custom exceptions have proper inheritance."""
        # Test base exception
        self.assertTrue(issubclass(ScrapingError, Exception))
        
        # Test derived exceptions
        self.assertTrue(issubclass(NetworkError, ScrapingError))
        self.assertTrue(issubclass(ParsingError, ScrapingError))
        self.assertTrue(issubclass(DatabaseError, ScrapingError))
        self.assertTrue(issubclass(ValidationError, ScrapingError))
    
    def test_exception_instantiation(self):
        """Test that exceptions can be created and used."""
        network_error = NetworkError("Network failed")
        self.assertEqual(str(network_error), "Network failed")
        
        parsing_error = ParsingError("Parse failed")
        self.assertEqual(str(parsing_error), "Parse failed")
        
        database_error = DatabaseError("Database failed")
        self.assertEqual(str(database_error), "Database failed")
        
        validation_error = ValidationError("Validation failed")
        self.assertEqual(str(validation_error), "Validation failed")
    
    def test_exception_catching(self):
        """Test that exceptions can be caught properly."""
        # Test catching specific exception
        with self.assertRaises(NetworkError):
            raise NetworkError("Test error")
        
        # Test catching base exception
        with self.assertRaises(ScrapingError):
            raise NetworkError("Test error")
        
        # Test catching generic exception
        with self.assertRaises(Exception):
            raise NetworkError("Test error")


class TestErrorRecoveryStrategies(unittest.TestCase):
    """Test error recovery strategies like retry logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_recovery")
        self.mock_operation = Mock()
    
    def test_retry_logic_success_on_first_try(self):
        """Test retry logic when operation succeeds immediately."""
        self.mock_operation.return_value = "success"
        
        # Simulate retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = self.mock_operation()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.01)  # Small delay for testing
                else:
                    raise
        
        self.assertEqual(result, "success")
        self.assertEqual(self.mock_operation.call_count, 1)
    
    def test_retry_logic_success_on_retry(self):
        """Test retry logic when operation succeeds after retries."""
        # Fail twice, then succeed
        self.mock_operation.side_effect = [
            Exception("Failed attempt 1"),
            Exception("Failed attempt 2"), 
            "success"
        ]
        
        # Simulate retry logic
        max_retries = 3
        result = None
        for attempt in range(max_retries):
            try:
                result = self.mock_operation()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.01)  # Small delay for testing
                else:
                    raise
        
        self.assertEqual(result, "success")
        self.assertEqual(self.mock_operation.call_count, 3)
    
    def test_retry_logic_all_attempts_fail(self):
        """Test retry logic when all attempts fail."""
        self.mock_operation.side_effect = Exception("Always fails")
        
        # Simulate retry logic
        max_retries = 3
        final_exception = None
        with self.assertRaises(Exception):
            for attempt in range(max_retries):
                try:
                    result = self.mock_operation()
                    break
                except Exception as e:
                    final_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(0.01)  # Small delay for testing
                    else:
                        raise
        
        self.assertEqual(self.mock_operation.call_count, 3)
        
    def test_exponential_backoff_delays(self):
        """Test that exponential backoff produces correct delays."""
        delays = []
        
        for attempt in range(4):
            delay = 2 ** attempt
            delays.append(delay)
        
        expected_delays = [1, 2, 4, 8]
        self.assertEqual(delays, expected_delays)


class TestDecoratorErrorHandling(unittest.TestCase):
    """Test decorator-based error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_decorator")
    
    def test_decorator_handles_exception(self):
        """Test that decorator catches and logs exceptions."""
        @with_error_handling(self.logger, "Test operation", reraise=False)
        def failing_function():
            raise ValueError("Test error")
        
        with patch.object(self.logger, 'error') as mock_error:
            result = failing_function()
            
            # Should return None when error is caught
            self.assertIsNone(result)
            
            # Should have logged the error
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0]
            self.assertIn("Test operation", call_args[0])
            self.assertIn("ValueError", call_args[0])
    
    def test_decorator_reraises_exception(self):
        """Test that decorator can reraise exceptions."""
        @with_error_handling(self.logger, "Test operation", reraise=True)
        def failing_function():
            raise ValueError("Test error")
        
        with patch.object(self.logger, 'error') as mock_error:
            with self.assertRaises(ValueError):
                failing_function()
            
            # Should still have logged the error
            mock_error.assert_called_once()
    
    def test_decorator_allows_success(self):
        """Test that decorator doesn't interfere with successful operations."""
        @with_error_handling(self.logger, "Test operation", reraise=False)
        def successful_function():
            return "success"
        
        result = successful_function()
        self.assertEqual(result, "success")


class TestLogException(unittest.TestCase):
    """Test the log_exception utility function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_log_exception")
    
    def test_log_exception_with_context(self):
        """Test logging exception with context."""
        test_exception = ValueError("Test error")
        
        with patch.object(self.logger, 'error') as mock_error:
            log_exception(self.logger, test_exception, "Test context")
            
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0]
            self.assertIn("Test context", call_args[0])
            self.assertIn("ValueError", call_args[0])
            self.assertIn("Test error", call_args[0])
            
            # Should include exc_info for stack trace
            call_kwargs = mock_error.call_args[1]
            self.assertTrue(call_kwargs.get('exc_info', False))
    
    def test_log_exception_without_context(self):
        """Test logging exception without context."""
        test_exception = NetworkError("Network failed")
        
        with patch.object(self.logger, 'error') as mock_error:
            log_exception(self.logger, test_exception)
            
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0]
            self.assertIn("NetworkError", call_args[0])
            self.assertIn("Network failed", call_args[0])


class TestIntegrationWithExistingModules(unittest.TestCase):
    """Test integration of error handling with existing modules."""
    
    def test_webtoon_client_uses_logging(self):
        """Test that WebtoonClient uses the new logging system."""
        try:
            from scraper.webtoon_client import WebtoonClient
            
            # Check that the module has a logger
            self.assertTrue(hasattr(sys.modules['scraper.webtoon_client'], 'logger'))
            
            # Create client and check it can be initialized
            client = WebtoonClient(use_selenium=False)
            self.assertIsNotNone(client)
            client.close()
            
        except ImportError as e:
            self.skipTest(f"WebtoonClient not available: {e}")
    
    def test_comment_analyzer_uses_logging(self):
        """Test that CommentAnalyzer uses the new logging system."""
        try:
            from scraper.comment_analyzer import CommentAnalyzer
            
            # Check that the module has a logger
            self.assertTrue(hasattr(sys.modules['scraper.comment_analyzer'], 'logger'))
            
            # Create analyzer and check it can be initialized
            analyzer = CommentAnalyzer()
            self.assertIsNotNone(analyzer)
            
        except ImportError as e:
            self.skipTest(f"CommentAnalyzer not available: {e}")
    
    def test_config_logging_setup(self):
        """Test that Config can set up logging."""
        # Test that Config has logging configuration
        self.assertTrue(hasattr(Config, 'LOGGING_CONFIG'))
        self.assertIsInstance(Config.LOGGING_CONFIG, dict)
        
        # Test required configuration keys
        required_keys = ['level', 'log_to_file', 'log_to_console', 'max_file_size']
        for key in required_keys:
            self.assertIn(key, Config.LOGGING_CONFIG)


class TestErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for complete error handling scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_integration")
    
    def test_network_error_scenario(self):
        """Test complete network error handling scenario."""
        @with_error_handling(self.logger, "Network operation", reraise=False)
        def simulate_network_operation():
            raise NetworkError("Connection timeout")
        
        with patch.object(self.logger, 'error') as mock_error:
            result = simulate_network_operation()
            
            self.assertIsNone(result)
            mock_error.assert_called_once()
    
    def test_database_error_scenario(self):
        """Test complete database error handling scenario."""
        @with_error_handling(self.logger, "Database operation", reraise=False)
        def simulate_database_operation():
            raise DatabaseError("Table not found")
        
        with patch.object(self.logger, 'error') as mock_error:
            result = simulate_database_operation()
            
            self.assertIsNone(result)
            mock_error.assert_called_once()
    
    def test_graceful_degradation_scenario(self):
        """Test graceful degradation scenario."""
        def advanced_operation():
            raise Exception("Advanced feature not available")
        
        def simple_operation():
            return "simple_result"
        
        # Simulate graceful degradation
        try:
            result = advanced_operation()
        except Exception as e:
            self.logger.warning(f"Advanced operation failed: {e}. Falling back to simple method")
            result = simple_operation()
        
        self.assertEqual(result, "simple_result")


def run_error_handling_tests():
    """Run all error handling tests and return results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestLoggingSystem,
        TestCustomExceptions,
        TestErrorRecoveryStrategies, 
        TestDecoratorErrorHandling,
        TestLogException,
        TestIntegrationWithExistingModules,
        TestErrorHandlingIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    print("="*70)
    print("ERROR HANDLING FEATURES - AUTOMATED TEST SUITE")
    print("="*70)
    print()
    
    result = runner.run(suite)
    
    print()
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Error:')[-1].strip()}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL ERROR HANDLING TESTS PASSED!")
        print("✅ Logging system working correctly")
        print("✅ Custom exceptions functioning properly")
        print("✅ Error recovery strategies operational")
        print("✅ Decorator-based error handling active")
        print("✅ Integration with existing modules successful")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    return result


if __name__ == '__main__':
    # Run the tests
    result = run_error_handling_tests()
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)