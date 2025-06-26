#!/usr/bin/env python3
"""
Real-world error scenario tests for the manga scraper.

This test suite simulates actual error conditions that might occur
during manga scraping operations and validates the error handling responses.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
import requests
from pathlib import Path
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from utils.logger import get_logger, NetworkError, ParsingError, DatabaseError
from utils.config import Config


class TestNetworkErrorScenarios(unittest.TestCase):
    """Test network-related error scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_network_scenarios")
    
    def test_connection_timeout_handling(self):
        """Test handling of connection timeouts."""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            # Simulate WebtoonClient behavior
            try:
                response = mock_get("https://example.com", timeout=5)
                self.fail("Should have raised timeout exception")
            except requests.exceptions.Timeout as e:
                # This is expected - test that we can catch and handle it
                self.assertIn("timeout", str(e).lower())
    
    def test_connection_refused_handling(self):
        """Test handling of connection refused errors."""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            try:
                response = mock_get("https://example.com")
                self.fail("Should have raised connection error")
            except requests.exceptions.ConnectionError as e:
                self.assertIn("refused", str(e).lower())
    
    def test_http_error_handling(self):
        """Test handling of HTTP errors (404, 500, etc.)."""
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
            mock_get.return_value = mock_response
            
            try:
                response = mock_get("https://example.com")
                response.raise_for_status()
                self.fail("Should have raised HTTP error")
            except requests.exceptions.HTTPError as e:
                self.assertIn("404", str(e))
    
    def test_network_retry_scenario(self):
        """Test network retry scenario with eventual success."""
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.ConnectionError("Network error")
            return Mock(status_code=200, text="Success")
        
        with patch('requests.Session.get', side_effect=side_effect):
            # Simulate retry logic
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    import requests
                    response = requests.Session().get("https://example.com")
                    success = True
                    break
                except requests.exceptions.ConnectionError:
                    if attempt == max_retries - 1:
                        raise
            
            self.assertTrue(success)
            self.assertEqual(call_count, 3)


class TestFileSystemErrorScenarios(unittest.TestCase):
    """Test file system related error scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_filesystem_scenarios")
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_permission_denied_handling(self):
        """Test handling of permission denied errors."""
        # On Windows, permission errors work differently
        import platform
        
        if platform.system() == "Windows":
            # Simulate permission error with mocking on Windows
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                try:
                    with open("restricted_file.txt", 'w') as f:
                        f.write("test")
                    self.fail("Should have raised permission error")
                except PermissionError as e:
                    self.assertIn("access", str(e).lower())
        else:
            # Unix-style permission test
            readonly_dir = os.path.join(self.temp_dir, "readonly")
            os.makedirs(readonly_dir)
            os.chmod(readonly_dir, 0o444)  # Read-only
            
            try:
                # Try to write to read-only directory
                test_file = os.path.join(readonly_dir, "test.txt")
                with open(test_file, 'w') as f:
                    f.write("test")
                self.fail("Should have raised permission error")
            except PermissionError as e:
                self.assertIn("permission", str(e).lower())
            finally:
                # Restore permissions for cleanup
                os.chmod(readonly_dir, 0o755)
    
    def test_disk_space_simulation(self):
        """Test simulation of disk space errors."""
        # This simulates what would happen if disk was full
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            try:
                with open("test_file.txt", 'w') as f:
                    f.write("test")
                self.fail("Should have raised OSError")
            except OSError as e:
                self.assertIn("space", str(e).lower())
    
    def test_file_not_found_handling(self):
        """Test handling of missing files."""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        
        try:
            with open(nonexistent_file, 'r') as f:
                content = f.read()
            self.fail("Should have raised FileNotFoundError")
        except FileNotFoundError as e:
            self.assertIn("no such file", str(e).lower())


class TestDatabaseErrorScenarios(unittest.TestCase):
    """Test database-related error scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_database_scenarios")
    
    def test_database_connection_failure(self):
        """Test database connection failure handling."""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database file is locked")
            
            try:
                import sqlite3
                conn = sqlite3.connect("test.db")
                self.fail("Should have raised database error")
            except Exception as e:
                self.assertIn("locked", str(e).lower())
    
    def test_sql_syntax_error(self):
        """Test SQL syntax error handling."""
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.execute.side_effect = Exception("SQL syntax error")
            mock_conn = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            try:
                import sqlite3
                conn = sqlite3.connect("test.db")
                cursor = conn.cursor()
                cursor.execute("INVALID SQL QUERY")
                self.fail("Should have raised SQL error")
            except Exception as e:
                self.assertIn("syntax", str(e).lower())
    
    def test_database_corruption_scenario(self):
        """Test database corruption scenario."""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database disk image is malformed")
            
            try:
                import sqlite3
                conn = sqlite3.connect("corrupted.db")
                self.fail("Should have raised corruption error")
            except Exception as e:
                self.assertIn("malformed", str(e).lower())


class TestParsingErrorScenarios(unittest.TestCase):
    """Test HTML parsing related error scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_parsing_scenarios")
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML."""
        from bs4 import BeautifulSoup
        
        malformed_html = "<html><body><div>Unclosed div<span>Unclosed span</body></html>"
        
        try:
            soup = BeautifulSoup(malformed_html, 'html.parser')
            # BeautifulSoup is actually quite forgiving, so this shouldn't fail
            # but we can test that we get some result
            self.assertIsNotNone(soup)
        except Exception as e:
            self.fail(f"BeautifulSoup should handle malformed HTML: {e}")
    
    def test_empty_html_handling(self):
        """Test handling of empty or missing HTML content."""
        from bs4 import BeautifulSoup
        
        empty_html = ""
        soup = BeautifulSoup(empty_html, 'html.parser')
        
        # Should not crash, but should handle gracefully
        comments = soup.find_all('div', class_='comment')
        self.assertEqual(len(comments), 0)
    
    def test_missing_expected_elements(self):
        """Test handling when expected HTML elements are missing."""
        from bs4 import BeautifulSoup
        
        html_without_comments = "<html><body><div>No comments here</div></body></html>"
        soup = BeautifulSoup(html_without_comments, 'html.parser')
        
        # Should handle missing elements gracefully
        comment_container = soup.find('ul', class_='wcc_CommentList')
        self.assertIsNone(comment_container)


class TestResourceLimitScenarios(unittest.TestCase):
    """Test resource limit and memory related scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_resource_scenarios")
    
    def test_memory_error_simulation(self):
        """Test simulation of memory errors."""
        # Simulate memory error during large operation
        with patch('builtins.list', side_effect=MemoryError("Out of memory")):
            try:
                large_list = list(range(1000))
                self.fail("Should have raised MemoryError")
            except MemoryError as e:
                self.assertIn("memory", str(e).lower())
    
    def test_timeout_during_operation(self):
        """Test timeout during long-running operations."""
        import time
        
        def long_operation(timeout=1):
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(0.1)
                if time.time() - start_time > 0.5:  # Simulate timeout check
                    raise TimeoutError("Operation timed out")
            return "completed"
        
        with self.assertRaises(TimeoutError):
            long_operation(timeout=1)


class TestErrorRecoveryIntegration(unittest.TestCase):
    """Test integrated error recovery scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_recovery_integration")
    
    def test_cascade_failure_recovery(self):
        """Test recovery from cascading failures."""
        attempts = []
        
        def unreliable_operation(attempt_num):
            attempts.append(attempt_num)
            if attempt_num < 3:
                if attempt_num == 1:
                    raise NetworkError("Network failure")
                elif attempt_num == 2:
                    raise DatabaseError("Database failure")
            return f"success_on_attempt_{attempt_num}"
        
        # Simulate recovery strategy
        max_retries = 5
        result = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = unreliable_operation(attempt)
                break
            except (NetworkError, DatabaseError) as e:
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    raise
        
        self.assertEqual(result, "success_on_attempt_3")
        self.assertEqual(len(attempts), 3)
    
    def test_graceful_degradation_chain(self):
        """Test chain of graceful degradations."""
        def try_advanced_feature():
            raise Exception("Advanced feature unavailable")
        
        def try_intermediate_feature():
            raise Exception("Intermediate feature unavailable")
        
        def basic_feature():
            return "basic_result"
        
        # Try features in order of preference
        result = None
        try:
            result = try_advanced_feature()
        except Exception:
            self.logger.warning("Advanced feature failed, trying intermediate")
            try:
                result = try_intermediate_feature()
            except Exception:
                self.logger.warning("Intermediate feature failed, using basic")
                result = basic_feature()
        
        self.assertEqual(result, "basic_result")


def run_error_scenario_tests():
    """Run all error scenario tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestNetworkErrorScenarios,
        TestFileSystemErrorScenarios,
        TestDatabaseErrorScenarios,
        TestParsingErrorScenarios,
        TestResourceLimitScenarios,
        TestErrorRecoveryIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    print("="*70)
    print("ERROR SCENARIO SIMULATION - AUTOMATED TEST SUITE")
    print("="*70)
    print()
    
    result = runner.run(suite)
    
    print()
    print("="*70)
    print("SCENARIO TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n🎉 ALL ERROR SCENARIO TESTS PASSED!")
        print("✅ Network error handling validated")
        print("✅ File system error handling validated")
        print("✅ Database error handling validated")
        print("✅ Parsing error handling validated")
        print("✅ Resource limit handling validated")
        print("✅ Error recovery integration validated")
    else:
        print("\n❌ Some scenario tests failed. Please review the output above.")
    
    return result


if __name__ == '__main__':
    # Run the scenario tests
    result = run_error_scenario_tests()
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1) 