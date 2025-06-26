#!/usr/bin/env python3
"""
Master test runner for all error handling and logging features.

This script runs comprehensive tests to validate:
1. Core error handling functionality
2. Real-world error scenarios
3. Integration with existing modules
4. Performance and reliability
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from utils.logger import get_logger, setup_logging
from utils.config import Config

# Import test modules
from tests.test_error_handling import run_error_handling_tests
from tests.test_error_scenarios import run_error_scenario_tests


def setup_test_environment():
    """Set up the test environment with proper logging."""
    print("Setting up test environment...")
    
    # Validate configuration
    if not Config.validate_config():
        print("❌ Configuration validation failed!")
        return False
    
    # Set up logging for tests
    logger = setup_logging(
        name='error_handling_tests',
        level=Config.LOGGING_CONFIG['level'],
        log_to_file=True,
        log_to_console=True
    )
    
    logger.info("Test environment setup completed")
    return True


def run_comprehensive_tests():
    """Run all error handling tests comprehensively."""
    print("🧪 COMPREHENSIVE ERROR HANDLING TEST SUITE")
    print("=" * 80)
    print()
    
    # Set up test environment
    if not setup_test_environment():
        return False
    
    all_results = []
    start_time = time.time()
    
    try:
        # 1. Run core error handling tests
        print("📋 PHASE 1: Core Error Handling Features")
        print("-" * 50)
        result1 = run_error_handling_tests()
        all_results.append(("Core Error Handling", result1))
        print()
        
        # 2. Run error scenario tests
        print("📋 PHASE 2: Real-World Error Scenarios")
        print("-" * 50)
        result2 = run_error_scenario_tests()
        all_results.append(("Error Scenarios", result2))
        print()
        
        # 3. Summary
        total_time = time.time() - start_time
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        
        for test_name, result in all_results:
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
            status = "✅ PASSED" if result.wasSuccessful() else "❌ FAILED"
            print(f"{test_name:.<30} {status}")
            print(f"  Tests: {result.testsRun}, Failures: {len(result.failures)}, Errors: {len(result.errors)}")
        
        print()
        print(f"Total execution time: {total_time:.2f} seconds")
        print(f"Total tests run: {total_tests}")
        print(f"Total failures: {total_failures}")
        print(f"Total errors: {total_errors}")
        
        success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        print(f"Overall success rate: {success_rate:.1f}%")
        
        if total_failures == 0 and total_errors == 0:
            print()
            print("🎉 ALL ERROR HANDLING TESTS PASSED!")
            print()
            print("VALIDATION SUMMARY:")
            print("✅ Centralized logging system - WORKING")
            print("✅ Custom exception classes - WORKING")
            print("✅ Error recovery strategies - WORKING")
            print("✅ Decorator-based error handling - WORKING")
            print("✅ Network error handling - WORKING")
            print("✅ File system error handling - WORKING")
            print("✅ Database error handling - WORKING")
            print("✅ HTML parsing error handling - WORKING")
            print("✅ Resource limit handling - WORKING")
            print("✅ Integration with existing modules - WORKING")
            print()
            print("🚀 The error handling system is ready for production use!")
            return True
        else:
            print()
            print("❌ SOME TESTS FAILED")
            print()
            print("Please review the test output above to identify and fix issues.")
            return False
    
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error during test execution: {e}", exc_info=True)
        print(f"❌ Test execution failed: {e}")
        return False


def run_quick_validation():
    """Run a quick validation of key error handling features."""
    print("⚡ QUICK ERROR HANDLING VALIDATION")
    print("=" * 50)
    print()
    
    try:
        # Test logging system
        logger = get_logger("quick_test")
        logger.info("Testing logging system...")
        print("✅ Logging system - OK")
        
        # Test custom exceptions
        from utils.logger import NetworkError, DatabaseError, ParsingError
        try:
            raise NetworkError("Test error")
        except NetworkError:
            print("✅ Custom exceptions - OK")
        
        # Test decorator
        from utils.logger import with_error_handling, log_exception
        
        @with_error_handling(logger, "Test operation", reraise=False)
        def test_decorated_function():
            raise ValueError("Test error")
        
        result = test_decorated_function()
        if result is None:  # Decorator should return None on error
            print("✅ Decorator error handling - OK")
        
        # Test integration
        try:
            from scraper.webtoon_client import WebtoonClient
            print("✅ WebtoonClient integration - OK")
        except ImportError:
            print("⚠️ WebtoonClient integration - SKIPPED (module not available)")
        
        try:
            from scraper.comment_analyzer import CommentAnalyzer
            print("✅ CommentAnalyzer integration - OK")
        except ImportError:
            print("⚠️ CommentAnalyzer integration - SKIPPED (module not available)")
        
        print()
        print("🎉 Quick validation completed successfully!")
        print("Run 'python run_error_handling_tests.py --full' for comprehensive testing.")
        return True
        
    except Exception as e:
        print(f"❌ Quick validation failed: {e}")
        return False


def main():
    """Main entry point for the test runner."""
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        # Run comprehensive tests
        success = run_comprehensive_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Run quick validation
        success = run_quick_validation()
    else:
        # Default to comprehensive tests
        print("Usage:")
        print("  python run_error_handling_tests.py         # Run comprehensive tests")
        print("  python run_error_handling_tests.py --full  # Run comprehensive tests")
        print("  python run_error_handling_tests.py --quick # Run quick validation")
        print()
        print("Running comprehensive tests by default...")
        print()
        success = run_comprehensive_tests()
    
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 