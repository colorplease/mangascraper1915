#!/usr/bin/env python3
"""
Test runner for manga scraper application.
Runs all tests and provides comprehensive reporting.
"""

import unittest
import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Import all test modules
from tests.test_webtoon_client import TestWebtoonClient, TestWebtoonClientIntegration
from tests.test_comment_analyzer import TestCommentExtraction, TestCommentSummarization, TestCommentAnalyzerIntegration
from tests.test_database import TestDatabaseManager, TestDatabaseUtils, TestDatabaseIntegration
from tests.test_parsers import TestExtractChapterInfo, TestExtractWebtoonInfo, TestParseChapterLinks, TestParseMangaMetadata, TestParseChapterImages, TestCreateObjects
from tests.test_fixes import TestCoreParserFunctionality, TestCoreCommentFunctionality, TestCoreWebClientFunctionality, TestCoreDatabaseFunctionality
from tests.test_integration import (
    TestFullScrapingWorkflow, 
    TestCommentExtractionAndSummarization,
    TestDatabaseQueryOperations,
    TestErrorHandlingAndEdgeCases
)
from tests.test_controllers import (
    TestMangaController,
    TestDownloadController, 
    TestMVCIntegration,
    TestMVCBusinessLogicSeparation
)


def run_test_suite(test_type='all'):
    """Run the test suite and return results."""
    
    # Create test suite
    suite = unittest.TestSuite()
    
    if test_type == 'all' or test_type == 'unit':
        print("Adding unit tests...")
        # Unit tests
        suite.addTest(unittest.makeSuite(TestWebtoonClient))
        suite.addTest(unittest.makeSuite(TestCommentExtraction))
        suite.addTest(unittest.makeSuite(TestCommentSummarization))
        suite.addTest(unittest.makeSuite(TestDatabaseManager))
        suite.addTest(unittest.makeSuite(TestDatabaseUtils))
        # Parser unit tests
        suite.addTest(unittest.makeSuite(TestExtractChapterInfo))
        suite.addTest(unittest.makeSuite(TestExtractWebtoonInfo))
        suite.addTest(unittest.makeSuite(TestParseChapterLinks))
        suite.addTest(unittest.makeSuite(TestParseMangaMetadata))
        suite.addTest(unittest.makeSuite(TestParseChapterImages))
        suite.addTest(unittest.makeSuite(TestCreateObjects))
    
    if test_type == 'all' or test_type == 'core':
        print("Adding core functionality tests...")
        # Core reliable tests
        suite.addTest(unittest.makeSuite(TestCoreParserFunctionality))
        suite.addTest(unittest.makeSuite(TestCoreCommentFunctionality))
        suite.addTest(unittest.makeSuite(TestCoreWebClientFunctionality))
        suite.addTest(unittest.makeSuite(TestCoreDatabaseFunctionality))
        # MVC Controller tests
        suite.addTest(unittest.makeSuite(TestMangaController))
        suite.addTest(unittest.makeSuite(TestDownloadController))
        suite.addTest(unittest.makeSuite(TestMVCIntegration))
        suite.addTest(unittest.makeSuite(TestMVCBusinessLogicSeparation))
    
    if test_type == 'all' or test_type == 'integration':
        print("Adding integration tests...")
        # Integration tests
        suite.addTest(unittest.makeSuite(TestWebtoonClientIntegration))
        suite.addTest(unittest.makeSuite(TestCommentAnalyzerIntegration))
        suite.addTest(unittest.makeSuite(TestDatabaseIntegration))
        suite.addTest(unittest.makeSuite(TestFullScrapingWorkflow))
        suite.addTest(unittest.makeSuite(TestCommentExtractionAndSummarization))
        suite.addTest(unittest.makeSuite(TestDatabaseQueryOperations))
        suite.addTest(unittest.makeSuite(TestErrorHandlingAndEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"Execution time: {end_time - start_time:.2f} seconds")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    print("\n" + "="*60)
    
    return result.wasSuccessful()


def run_functionality_tests():
    """Run tests specifically for the 4 core functionalities mentioned by user."""
    
    print("RUNNING CORE FUNCTIONALITY TESTS")
    print("="*50)
    
    functionality_tests = {
        "Chapter Scraping": [TestWebtoonClient, TestFullScrapingWorkflow, TestExtractChapterInfo, TestExtractWebtoonInfo, TestParseChapterLinks, TestParseMangaMetadata, TestParseChapterImages, TestCreateObjects],
        "Comment Scraping": [TestCommentExtraction, TestCommentExtractionAndSummarization], 
        "Comment Summarization": [TestCommentSummarization, TestCommentAnalyzerIntegration],
        "Database Operations": [TestDatabaseManager, TestDatabaseQueryOperations],
        "MVC Controllers": [TestMangaController, TestDownloadController, TestMVCIntegration, TestMVCBusinessLogicSeparation]
    }
    
    all_passed = True
    
    for functionality, test_classes in functionality_tests.items():
        print(f"\n{functionality.upper()}")
        print("-" * len(functionality))
        
        suite = unittest.TestSuite()
        for test_class in test_classes:
            suite.addTest(unittest.makeSuite(test_class))
        
        runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print(f"✓ {functionality}: ALL TESTS PASSED ({result.testsRun} tests)")
        else:
            print(f"✗ {functionality}: {len(result.failures + result.errors)} FAILURES/ERRORS ({result.testsRun} tests)")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL CORE FUNCTIONALITY TESTS PASSED!")
        print("Your manga scraper has full functionality:")
        print("  ✓ Successfully scraping manga chapters")
        print("  ✓ Successfully scraping comments")
        print("  ✓ Successfully summarizing comments")
        print("  ✓ Database queries working")
    else:
        print("⚠️  Some functionality tests failed. Check the details above.")
    
    return all_passed


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run manga scraper tests')
    parser.add_argument('--type', choices=['all', 'unit', 'integration', 'functionality', 'core'], 
                       default='functionality',
                       help='Type of tests to run (default: functionality)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    print(f"MANGA SCRAPER TEST SUITE")
    print(f"Running {args.type} tests...")
    print("="*50)
    
    if args.type == 'functionality':
        success = run_functionality_tests()
    else:
        success = run_test_suite(args.type)
    
    sys.exit(0 if success else 1) 