#!/usr/bin/env python3
"""
Quick verification script to test the main failing tests.
This helps ensure fixes work correctly before committing to CI.
"""

import unittest
import sys
import os

# Add project root to path
from pathlib import Path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def main():
    """Run the specific tests that were failing."""
    print("Running quick verification of test fixes...")
    
    # Import test classes
    from tests.test_webtoon_client import TestWebtoonClient
    from tests.test_database import TestDatabaseManager, TestDatabaseUtils
    from tests.test_comment_analyzer import TestCommentSummarization
    
    # Create test suite with specific failing tests
    suite = unittest.TestSuite()
    
    # WebtoonClient tests
    suite.addTest(TestWebtoonClient('test_download_image_success'))
    
    # Database tests
    suite.addTest(TestDatabaseManager('test_get_all_manga'))
    suite.addTest(TestDatabaseManager('test_get_download_statistics'))
    suite.addTest(TestDatabaseManager('test_get_manga_by_title_no'))
    suite.addTest(TestDatabaseManager('test_init_database'))
    suite.addTest(TestDatabaseManager('test_search_manga_by_author'))
    suite.addTest(TestDatabaseManager('test_search_manga_by_genre'))
    suite.addTest(TestDatabaseManager('test_search_manga_by_title'))
    suite.addTest(TestDatabaseUtils('test_insert_or_update_manga'))
    
    # Comment analyzer tests
    suite.addTest(TestCommentSummarization('test_generate_nltk_summary'))
    suite.addTest(TestCommentSummarization('test_summarize_comments_fallback_to_simple'))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All previously failing tests now pass!")
        print("The fixes are working correctly.")
        return 0
    else:
        print(f"\n❌ {len(result.failures)} test(s) still failing")
        print(f"❌ {len(result.errors)} test(s) have errors")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 