#!/usr/bin/env python3
"""
Integration tests for full manga scraper functionality.
Tests complete workflows including scraping, commenting, and database operations.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from bs4 import BeautifulSoup

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from scraper.webtoon_client import WebtoonClient
from scraper.comment_analyzer import CommentAnalyzer
from scraper.downloader import DownloadManager
from utils.db_manager import DatabaseManager
from models.manga import Manga
from models.chapter import Chapter


class TestFullScrapingWorkflow(unittest.TestCase):
    """Test complete manga scraping workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        
        # Sample HTML responses
        self.series_page_html = """
        <html>
            <head><title>Test Series</title></head>
            <body>
                <div class="detail_header">
                    <h1 class="subj">Test Webtoon Series</h1>
                    <h2 class="author">by Test Author</h2>
                    <span class="genre">Drama, Romance</span>
                    <em class="grade_area">9.5</em>
                </div>
                <div class="paginate">
                    <a href="?page=1"><span>1</span></a>
                </div>
                <ul class="detail_lst">
                    <li>
                        <a href="/en/drama/test-series/viewer?title_no=123&episode_no=1">
                            #1 - First Chapter
                        </a>
                    </li>
                    <li>
                        <a href="/en/drama/test-series/viewer?title_no=123&episode_no=2">
                            #2 - Second Chapter  
                        </a>
                    </li>
                </ul>
            </body>
        </html>
        """
        
        self.chapter_page_html = """
        <html>
            <body>
                <div class="_viewerImages">
                    <img data-url="https://example.com/image1.jpg" />
                    <img data-url="https://example.com/image2.jpg" />
                </div>
                <ul class="wcc_CommentList">
                    <li class="wcc_CommentItem__root">
                        <div class="wcc_CommentItem__inside">
                            <span class="wcc_CommentHeader__name">Reader1</span>
                            <time class="wcc_CommentHeader__createdAt">2024-01-01</time>
                            <p class="wcc_TextContent__content">
                                <span>Great chapter! Love the artwork.</span>
                            </p>
                            <div class="wcc_CommentReaction__root">
                                <button class="wcc_CommentReaction__action"><span>25</span></button>
                            </div>
                        </div>
                    </li>
                </ul>
            </body>
        </html>
        """
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    @patch('scraper.webtoon_client.WebtoonClient.get_page')
    @patch('scraper.webtoon_client.WebtoonClient.download_image')
    def test_complete_scraping_workflow(self, mock_download_image, mock_get_page):
        """Test complete workflow: scrape series -> chapters -> comments -> save to DB."""
        
        # Mock web requests
        def mock_get_page_side_effect(url):
            if 'list' in url:
                return BeautifulSoup(self.series_page_html, 'html.parser')
            elif 'viewer' in url:
                return BeautifulSoup(self.chapter_page_html, 'html.parser')
            return None
        
        mock_get_page.side_effect = mock_get_page_side_effect
        mock_download_image.return_value = True
        
        # Initialize components
        client = WebtoonClient(use_selenium=False)
        comment_analyzer = CommentAnalyzer()
        
        try:
            # Step 1: Get series page and extract manga info
            series_url = "https://www.webtoons.com/en/drama/test-series/list?title_no=123"
            series_soup = client.get_page(series_url)
            self.assertIsNotNone(series_soup)
            
            # Step 2: Create manga object (simplified)
            manga = Manga(
                title_no="123",
                series_name="test-series",
                display_title="Test Webtoon Series",
                author="Test Author",
                genre="Drama, Romance",
                grade=9.5,
                url=series_url
            )
            
            # Step 3: Extract chapter links
            chapter_links = series_soup.find_all('a', href=lambda x: x and 'viewer' in x)
            chapters = []
            for i, link in enumerate(chapter_links):
                href = link.get('href')
                if href:
                    full_url = f"https://www.webtoons.com{href}"
                    chapter = Chapter(
                        episode_no=str(i+1),
                        title=link.text.strip(),
                        url=full_url
                    )
                    chapters.append(chapter)
            
            manga.chapters = chapters
            self.assertEqual(len(manga.chapters), 2)
            
            # Step 4: Save manga to database
            manga_id = self.db_manager.save_manga(manga)
            self.assertGreater(manga_id, 0)
            
            # Step 5: Process first chapter - get comments and images
            first_chapter = chapters[0]
            chapter_soup = client.get_page(first_chapter.url)
            self.assertIsNotNone(chapter_soup)
            
            # Extract comments
            comments = comment_analyzer.extract_comments_from_soup(
                chapter_soup, first_chapter.url
            )
            self.assertEqual(len(comments), 1)
            self.assertEqual(comments[0]['username'], 'Reader1')
            self.assertIn('Great chapter', comments[0]['text'])
            
            # Analyze comments
            summary = comment_analyzer.analyze_comments(comments)
            self.assertIsInstance(summary, str)
            self.assertGreater(len(summary), 10)
            
            # Step 6: Verify database operations
            retrieved_manga = self.db_manager.get_manga_by_id(manga_id)
            self.assertIsNotNone(retrieved_manga)
            self.assertEqual(retrieved_manga.title_no, "123")
            self.assertEqual(len(retrieved_manga.chapters), 2)
            
            # Test search functionality
            search_results = self.db_manager.search_manga_by_title("Test Webtoon")
            self.assertEqual(len(search_results), 1)
            
            search_results = self.db_manager.search_manga_by_author("Test Author")
            self.assertEqual(len(search_results), 1)
            
            print("✓ Complete scraping workflow test passed!")
            
        finally:
            client.close()


class TestCommentExtractionAndSummarization(unittest.TestCase):
    """Test complete comment processing workflow."""
    
    @patch('scraper.comment_analyzer.CommentAnalyzer._save_debug_html')
    def test_comment_processing_workflow(self, mock_save_debug):
        """Test complete comment extraction and summarization."""
        
        # Complex comment HTML
        complex_comments_html = """
        <html>
            <body>
                <ul class="wcc_CommentList">
                    <li class="wcc_CommentItem__root">
                        <div class="wcc_CommentItem__inside">
                            <span class="wcc_CommentHeader__name">CriticalReader</span>
                            <time class="wcc_CommentHeader__createdAt">2024-01-01</time>
                            <p class="wcc_TextContent__content">
                                <span>The character development in this chapter is exceptional. The author really knows how to build emotional depth.</span>
                            </p>
                            <div class="wcc_CommentReaction__root">
                                <button class="wcc_CommentReaction__action"><span>78</span></button>
                            </div>
                        </div>
                    </li>
                    <li class="wcc_CommentItem__root">
                        <div class="wcc_CommentItem__inside">
                            <span class="wcc_CommentHeader__name">ArtLover</span>
                            <time class="wcc_CommentHeader__createdAt">2024-01-01</time>
                            <p class="wcc_TextContent__content">
                                <span>The artwork is absolutely stunning! Every panel is like a work of art.</span>
                            </p>
                            <div class="wcc_CommentReaction__root">
                                <button class="wcc_CommentReaction__action"><span>45</span></button>
                            </div>
                        </div>
                    </li>
                </ul>
            </body>
        </html>
        """
        
        analyzer = CommentAnalyzer()
        soup = BeautifulSoup(complex_comments_html, 'html.parser')
        
        # Extract comments
        comments = analyzer.extract_comments_from_soup(soup, 'https://example.com/chapter')
        
        # Verify extraction
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]['username'], 'CriticalReader')
        self.assertEqual(comments[1]['username'], 'ArtLover')
        self.assertIn('character development', comments[0]['text'])
        self.assertIn('artwork', comments[1]['text'])
        
        # Test summarization
        summary = analyzer.analyze_comments(comments)
        
        self.assertIsInstance(summary, str)
        self.assertIn('2 comments', summary)
        self.assertGreater(len(summary), 50)
        
        # Test file saving
        with tempfile.TemporaryDirectory() as temp_dir:
            chapter = Chapter(episode_no="5", title="Test Chapter", url="https://example.com/ch5")
            analyzer.save_comments_to_file(comments, chapter, temp_dir)
            
            expected_file = os.path.join(temp_dir, f"comments_episode_{chapter.episode_no}.txt")
            self.assertTrue(os.path.exists(expected_file))
            
            with open(expected_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            self.assertIn('Comments for Episode 5', content)
            self.assertIn('CriticalReader', content)
            self.assertIn('ArtLover', content)
            self.assertIn('SUMMARY:', content)
        
        print("✓ Comment processing workflow test passed!")


class TestDatabaseQueryOperations(unittest.TestCase):
    """Test database query operations."""
    
    def setUp(self):
        """Set up test database with sample data."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        
        # Create sample manga with various properties
        manga_data = [
            {
                'title_no': '001', 'series_name': 'action-series', 'display_title': 'Epic Action Series',
                'author': 'Action Author', 'genre': 'Action, Adventure', 'grade': 9.2, 'num_chapters': 100
            },
            {
                'title_no': '002', 'series_name': 'romance-series', 'display_title': 'Sweet Romance Story', 
                'author': 'Romance Author', 'genre': 'Romance, Drama', 'grade': 8.8, 'num_chapters': 50
            },
            {
                'title_no': '003', 'series_name': 'comedy-series', 'display_title': 'Hilarious Comedy',
                'author': 'Comedy Master', 'genre': 'Comedy, Slice of Life', 'grade': 9.0, 'num_chapters': 75
            }
        ]
        
        for data in manga_data:
            manga = Manga(**data)
            self.db_manager.save_manga(manga)
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_various_search_operations(self):
        """Test various database search and query operations."""
        
        # Test search by title
        results = self.db_manager.search_manga_by_title('Action')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].display_title, 'Epic Action Series')
        
        # Test search by author
        results = self.db_manager.search_manga_by_author('Romance Author')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].series_name, 'romance-series')
        
        # Test search by genre
        results = self.db_manager.search_manga_by_genre('Comedy')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].genre, 'Comedy, Slice of Life')
        
        # Test minimum chapters search
        results = self.db_manager.search_manga_by_min_chapters(60)
        self.assertEqual(len(results), 2)  # action-series (100) and comedy-series (75)
        
        # Test minimum grade search  
        results = self.db_manager.search_manga_by_grade(9.0)
        self.assertEqual(len(results), 2)  # action-series (9.2) and comedy-series (9.0)
        
        # Test get all manga
        all_manga = self.db_manager.get_all_manga()
        self.assertEqual(len(all_manga), 3)
        
        # Test statistics
        stats = self.db_manager.get_download_statistics()
        self.assertEqual(stats['total_manga'], 3)
        self.assertEqual(stats['total_chapters'], 0)  # No chapters added
        
        print("✓ Database query operations test passed!")


class TestErrorHandlingAndEdgeCases(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def test_invalid_url_handling(self):
        """Test handling of invalid URLs."""
        client = WebtoonClient(use_selenium=False)
        
        try:
            with patch('requests.Session.get') as mock_get:
                mock_get.side_effect = Exception("Network error")
                
                soup = client.get_page('https://invalid-url.com')
                self.assertIsNone(soup)
        finally:
            client.close()
    
    def test_empty_comment_handling(self):
        """Test handling of pages with no comments."""
        analyzer = CommentAnalyzer()
        empty_html = "<html><body><div>No comments here</div></body></html>"
        soup = BeautifulSoup(empty_html, 'html.parser')
        
        with patch('scraper.comment_analyzer.CommentAnalyzer._save_debug_html'):
            comments = analyzer.extract_comments_from_soup(soup, 'https://example.com')
            
        self.assertEqual(len(comments), 0)
        
        summary = analyzer.analyze_comments(comments)
        self.assertIn('No comments', summary)
    
    def test_database_connection_error(self):
        """Test handling of database connection errors."""
        # Try to create DatabaseManager with invalid path
        with self.assertRaises(Exception):
            invalid_db = DatabaseManager('/invalid/path/database.db')
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML."""
        malformed_html = "<html><body><div>Unclosed div<span>Unclosed span</body></html>"
        soup = BeautifulSoup(malformed_html, 'html.parser')
        
        # Should not crash
        analyzer = CommentAnalyzer()
        with patch('scraper.comment_analyzer.CommentAnalyzer._save_debug_html'):
            comments = analyzer.extract_comments_from_soup(soup, 'https://example.com')
        
        self.assertIsInstance(comments, list)
        
        print("✓ Error handling and edge cases test passed!")


if __name__ == '__main__':
    # Run all integration tests
    unittest.main(verbosity=2) 