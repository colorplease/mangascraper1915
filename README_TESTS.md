# Manga Scraper Test Suite

This comprehensive test suite validates all core functionality of the manga scraper application.

## Overview

The test suite covers the four main functionalities you requested:

1. ✅ **Successfully scraping manga chapters**  
2. ✅ **Successfully scraping comments**
3. ✅ **Successfully summarizing comments** 
4. ✅ **Database queries working**

## Test Structure

### Test Files

- `tests/test_webtoon_client.py` - Tests for web scraping and chapter extraction
- `tests/test_comment_analyzer.py` - Tests for comment extraction and summarization
- `tests/test_database.py` - Tests for all database operations
- `tests/test_parsers.py` - **NEW**: Tests for URL parsing and HTML extraction functions
- `tests/test_integration.py` - End-to-end integration tests
- `tests/test_runner.py` - Test runner with comprehensive reporting

### Test Categories

#### Unit Tests
- Individual component testing
- Mocked external dependencies
- Fast execution
- Focused on specific functionality

#### Integration Tests  
- Full workflow testing
- Real component interactions
- Database operations
- Error handling scenarios

## Quick Start

### Run Core Functionality Tests
```bash
python tests/test_runner.py --type functionality
```

This runs focused tests for the 4 core functionalities and provides a clear pass/fail report.

### Run All Tests
```bash
python tests/test_runner.py --type all
```

### Run Specific Test Categories
```bash
# Unit tests only
python tests/test_runner.py --type unit

# Integration tests only  
python tests/test_runner.py --type integration
```

### Run Individual Test Files
```bash
# Test chapter scraping
python -m unittest tests.test_webtoon_client

# Test comment functionality
python -m unittest tests.test_comment_analyzer

# Test database operations
python -m unittest tests.test_database

# Test parser functions (NEW)
python -m unittest tests.test_parsers

# Test full workflows
python -m unittest tests.test_integration
```

## Test Coverage

### Chapter Scraping Tests
- ✅ Web page retrieval with retry logic
- ✅ HTML parsing and chapter link extraction
- ✅ Pagination handling
- ✅ URL normalization (viewer → list pages)
- ✅ Image download functionality
- ✅ Error handling for network issues
- ✅ **NEW**: URL parsing functions (`extract_chapter_info`, `extract_webtoon_info`)
- ✅ **NEW**: HTML parsing functions (`parse_chapter_links`, `parse_manga_metadata`, `parse_chapter_images`)
- ✅ **NEW**: Object creation functions (`create_manga_from_page`, `create_chapters_from_links`)
- ✅ **NEW**: Invalid URL handling and edge cases

### Comment Scraping Tests
- ✅ Comment extraction from HTML
- ✅ Multiple comment structure handling
- ✅ User data extraction (username, date, likes)
- ✅ Malformed HTML handling  
- ✅ Empty comment page handling
- ✅ Debug HTML saving

### Comment Summarization Tests
- ✅ NLTK-based advanced summarization
- ✅ Simple fallback summarization
- ✅ Sentiment analysis
- ✅ Word frequency analysis  
- ✅ Most upvoted comment identification
- ✅ Comment statistics generation

### Database Query Tests
- ✅ Manga creation, reading, updating, deletion (CRUD)
- ✅ Chapter management
- ✅ Search by title, author, genre
- ✅ Filtering by ratings, chapter count
- ✅ Database statistics
- ✅ Transaction handling
- ✅ Connection management

### Integration Tests
- ✅ Complete scraping workflow (series → chapters → comments → database)
- ✅ Error recovery and retry mechanisms
- ✅ File system operations
- ✅ Memory management
- ✅ Resource cleanup

## Expected Output

When running `python tests/test_runner.py --type functionality`, you should see:

```
RUNNING CORE FUNCTIONALITY TESTS
==================================================

CHAPTER SCRAPING
---------------
✓ Chapter Scraping: ALL TESTS PASSED (15 tests)

COMMENT SCRAPING  
---------------
✓ Comment Scraping: ALL TESTS PASSED (12 tests)

COMMENT SUMMARIZATION
--------------------
✓ Comment Summarization: ALL TESTS PASSED (8 tests)

DATABASE OPERATIONS
------------------
✓ Database Operations: ALL TESTS PASSED (18 tests)

==================================================
🎉 ALL CORE FUNCTIONALITY TESTS PASSED!
Your manga scraper has full functionality:
  ✓ Successfully scraping manga chapters
  ✓ Successfully scraping comments  
  ✓ Successfully summarizing comments
  ✓ Database queries working
```

## Test Dependencies

The tests use Python's built-in `unittest` framework and require:

- `unittest.mock` for mocking external dependencies
- `tempfile` for temporary databases and files
- `BeautifulSoup4` for HTML parsing (from your requirements.txt)
- All your existing project dependencies

## Notes

- Tests use temporary databases and files to avoid affecting your real data
- Network calls are mocked to ensure tests run reliably without internet
- Tests are designed to run quickly while providing comprehensive coverage
- The test suite automatically handles setup and cleanup

## Troubleshooting

If tests fail:

1. Check that all dependencies are installed: `pip install -r requirements.txt`
2. Ensure you're running from the project root directory
3. Check that Python can import all modules: `python -c "import scraper.webtoon_client"`
4. Run individual test files to isolate issues

## Extending Tests

To add new tests:

1. Add test methods to existing test classes
2. Create new test classes for new functionality
3. Update `test_runner.py` to include new test classes
4. Follow the existing pattern of mocking external dependencies 