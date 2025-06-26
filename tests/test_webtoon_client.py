#!/usr/bin/env python3
"""
Tests for WebtoonClient functionality.
Tests chapter scraping, pagination, image downloading, etc.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
import os
import tempfile
from bs4 import BeautifulSoup

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from scraper.webtoon_client import WebtoonClient


class TestWebtoonClient(unittest.TestCase):
    """Test cases for WebtoonClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = WebtoonClient(use_selenium=False)
        
        # Sample HTML for testing
        self.sample_chapter_html = """
        <html>
            <body>
                <div class="paginate">
                    <a href="?page=1"><span>1</span></a>
                    <a href="?page=2"><span>2</span></a>
                    <a href="?page=3"><span>3</span></a>
                </div>
                <ul class="detail_lst">
                    <li>
                        <a href="/en/episode/viewer?title_no=123&episode_no=1">Episode 1</a>
                    </li>
                    <li>
                        <a href="/en/episode/viewer?title_no=123&episode_no=2">Episode 2</a>
                    </li>
                </ul>
            </body>
        </html>
        """
    
    def tearDown(self):
        """Clean up after tests."""
        self.client.close()
    
    @patch('requests.Session.get')
    def test_get_page_success(self, mock_get):
        """Test successful page retrieval."""
        # Mock response
        mock_response = Mock()
        mock_response.text = self.sample_chapter_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test
        soup = self.client.get_page('https://example.com/test')
        
        # Assertions
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertIn('paginate', str(soup))
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_get_page_retry_on_failure(self, mock_get):
        """Test retry logic when page retrieval fails."""
        # Mock failures then success
        mock_get.side_effect = [
            requests.RequestException("Network error"),
            requests.RequestException("Another error"),
            Mock(text=self.sample_chapter_html, raise_for_status=Mock())
        ]
        
        # Test
        soup = self.client.get_page('https://example.com/test')
        
        # Assertions
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(mock_get.call_count, 3)
    
    @patch('requests.Session.get')
    def test_get_page_failure_exhausted_retries(self, mock_get):
        """Test behavior when all retries are exhausted."""
        # Mock continuous failures
        mock_get.side_effect = requests.RequestException("Persistent error")
        
        # Test
        soup = self.client.get_page('https://example.com/test', retry_count=2)
        
        # Assertions
        self.assertIsNone(soup)
        self.assertEqual(mock_get.call_count, 2)
    
    def test_normalize_list_url_viewer_to_list(self):
        """Test conversion of viewer URL to list URL."""
        viewer_url = "https://www.webtoons.com/en/drama/series/viewer?title_no=123&episode_no=1"
        expected = "https://www.webtoons.com/en/drama/series/list?title_no=123"
        
        result = self.client.normalize_list_url(viewer_url)
        self.assertEqual(result, expected)
    
    def test_normalize_list_url_already_list(self):
        """Test that list URLs are returned unchanged."""
        list_url = "https://www.webtoons.com/en/drama/series/list?title_no=123"
        result = self.client.normalize_list_url(list_url)
        self.assertEqual(result, list_url)
    
    @patch('requests.Session.get')
    def test_get_paginated_content(self, mock_get):
        """Test getting content from multiple pages."""
        # Mock first page response
        page1_html = """
        <html>
            <body>
                <div class="paginate">
                    <a href="?page=1"><span>1</span></a>
                    <a href="?page=2"><span>2</span></a>
                </div>
                <div>Page 1 content</div>
            </body>
        </html>
        """
        
        # Mock second page response
        page2_html = """
        <html>
            <body>
                <div>Page 2 content</div>
            </body>
        </html>
        """
        
        mock_responses = [
            Mock(text=page1_html, raise_for_status=Mock()),
            Mock(text=page2_html, raise_for_status=Mock())
        ]
        mock_get.side_effect = mock_responses
        
        # Test
        pages = self.client.get_paginated_content('https://example.com/list', '123')
        
        # Assertions
        self.assertEqual(len(pages), 2)
        self.assertIn('Page 1 content', str(pages[0]))
        self.assertIn('Page 2 content', str(pages[1]))
        self.assertEqual(mock_get.call_count, 2)
    
    def test_get_page_count(self):
        """Test page count extraction from pagination."""
        soup = BeautifulSoup(self.sample_chapter_html, 'html.parser')
        page_count = self.client._get_page_count(soup)
        self.assertEqual(page_count, 3)
    
    def test_get_page_count_no_pagination(self):
        """Test page count when no pagination exists."""
        html = "<html><body><div>No pagination</div></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        page_count = self.client._get_page_count(soup)
        self.assertEqual(page_count, 1)
    
    @patch('requests.Session.get')
    def test_download_image_success(self, mock_get):
        """Test successful image download."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, 'test_image.jpg')
            
            # Mock response with image data - make it large enough to pass size check
            mock_response = Mock()
            mock_response.headers = {'Content-Type': 'image/jpeg'}
            # Create larger fake JPEG data (4000 bytes total)
            mock_response.iter_content.return_value = [b'\xff\xd8\xff\xe0' * 250] * 4  
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Test
            result = self.client.download_image('https://example.com/image.jpg', filepath)
            
            # Assertions - The download should succeed with larger mock data
            self.assertTrue(result)
            self.assertTrue(os.path.exists(filepath))
            self.assertGreater(os.path.getsize(filepath), 1000)  # Should be larger than minimum size
    
    @patch('requests.Session.get')
    def test_download_image_failure(self, mock_get):
        """Test image download failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, 'test_image.jpg')
            
            # Mock network error
            mock_get.side_effect = requests.RequestException("Network error")
            
            # Test
            result = self.client.download_image('https://example.com/image.jpg', filepath)
            
            # Assertions
            self.assertFalse(result)
            self.assertFalse(os.path.exists(filepath))
    
    @patch('requests.Session.get')
    def test_download_image_invalid_content_type(self, mock_get):
        """Test image download with invalid content type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, 'test_image.jpg')
            
            # Mock response with wrong content type
            mock_response = Mock()
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.iter_content.return_value = [b'<html>Error page</html>']
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Test
            result = self.client.download_image('https://example.com/image.jpg', filepath)
            
            # Assertions
            self.assertFalse(result)


class TestWebtoonClientIntegration(unittest.TestCase):
    """Integration tests for WebtoonClient with real-like scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = WebtoonClient(use_selenium=False)
    
    def tearDown(self):
        """Clean up after tests."""
        self.client.close()
    
    @patch('scraper.webtoon_client.WebtoonClient.get_page')
    def test_full_chapter_scraping_workflow(self, mock_get_page):
        """Test complete workflow of scraping chapters from a series."""
        # Mock series page
        series_html = """
        <html>
            <body>
                <div class="paginate">
                    <a href="?page=1"><span>1</span></a>
                </div>
                <ul class="detail_lst">
                    <li>
                        <a href="/en/episode/viewer?title_no=123&episode_no=1">Episode 1: Test Chapter</a>
                    </li>
                    <li>
                        <a href="/en/episode/viewer?title_no=123&episode_no=2">Episode 2: Another Chapter</a>
                    </li>
                </ul>
            </body>
        </html>
        """
        
        mock_get_page.return_value = BeautifulSoup(series_html, 'html.parser')
        
        # Test getting paginated content
        pages = self.client.get_paginated_content('https://example.com/list', '123')
        
        # Assertions
        self.assertEqual(len(pages), 1)
        self.assertIn('Episode 1: Test Chapter', str(pages[0]))
        self.assertIn('Episode 2: Another Chapter', str(pages[0]))
        
        # Verify proper URL construction
        mock_get_page.assert_called_with('https://example.com/list?title_no=123')


if __name__ == '__main__':
    unittest.main() 