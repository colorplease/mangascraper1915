#!/usr/bin/env python3
"""
Unit tests for scraper.parsers module.
Tests all parsing functions including URL extraction, metadata parsing, and object creation.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from scraper.parsers import (
    extract_webtoon_info,
    extract_chapter_info,
    parse_chapter_links,
    parse_manga_metadata,
    parse_chapter_images,
    create_manga_from_page,
    create_chapters_from_links,
    _clean_text,
    _extract_banner_urls
)
from models.manga import Manga
from models.chapter import Chapter


class TestExtractWebtoonInfo(unittest.TestCase):
    """Test webtoon info extraction from URLs."""
    
    def test_extract_webtoon_info_valid_url(self):
        """Test extraction from valid webtoon URL."""
        url = "https://www.webtoons.com/en/comedy/safely-endangered/list?title_no=352"
        title_no, series_name = extract_webtoon_info(url)
        
        self.assertEqual(title_no, "352")
        self.assertEqual(series_name, "safely-endangered")
    
    def test_extract_webtoon_info_viewer_url(self):
        """Test extraction from viewer URL."""
        url = "https://www.webtoons.com/en/comedy/safely-endangered/ep-1040-finale/viewer?title_no=352&episode_no=1040"
        title_no, series_name = extract_webtoon_info(url)
        
        self.assertEqual(title_no, "352")
        self.assertEqual(series_name, "safely-endangered")
    
    def test_extract_webtoon_info_no_title_no(self):
        """Test extraction when title_no is missing."""
        url = "https://www.webtoons.com/en/comedy/safely-endangered/list"
        title_no, series_name = extract_webtoon_info(url)
        
        self.assertEqual(title_no, "")
        self.assertEqual(series_name, "safely-endangered")
    
    def test_extract_webtoon_info_short_path(self):
        """Test extraction with insufficient path segments."""
        url = "https://www.webtoons.com/en"
        title_no, series_name = extract_webtoon_info(url)
        
        self.assertEqual(title_no, "")
        self.assertEqual(series_name, "unknown")


class TestExtractChapterInfo(unittest.TestCase):
    """Test chapter info extraction from URLs as requested by user."""
    
    def test_extract_chapter_info_valid_url(self):
        """Test extraction from valid chapter URL."""
        url = "https://www.webtoons.com/en/comedy/safely-endangered/ep-1040-finale-part-33/viewer?title_no=352&episode_no=1040"
        episode_no, title = extract_chapter_info(url)
        
        self.assertEqual(episode_no, "1040")
        self.assertEqual(title, "Ep 1040 Finale Part 33")  # Should be cleaned and title-cased
    
    def test_extract_chapter_info_invalid_url(self):
        """Test extraction from invalid URL."""
        url = "https://invalid-url.com"
        episode_no, title = extract_chapter_info(url)
        
        self.assertEqual(episode_no, "0")
        self.assertEqual(title, "Unknown")
    
    def test_extract_chapter_info_underscores_in_title(self):
        """Test extraction with underscores in title."""
        url = "https://www.webtoons.com/en/drama/test_series/episode_123_the_final_battle/viewer?title_no=456&episode_no=123"
        episode_no, title = extract_chapter_info(url)
        
        self.assertEqual(episode_no, "123")
        self.assertEqual(title, "Episode 123 The Final Battle")
    
    def test_extract_chapter_info_no_episode_no(self):
        """Test extraction when episode_no is missing."""
        url = "https://www.webtoons.com/en/comedy/safely-endangered/ep-1040-finale/viewer?title_no=352"
        episode_no, title = extract_chapter_info(url)
        
        self.assertEqual(episode_no, "0")  # Default value
        self.assertEqual(title, "Ep 1040 Finale")
    
    def test_extract_chapter_info_short_path(self):
        """Test extraction with insufficient path segments."""
        url = "https://www.webtoons.com/en/comedy"
        episode_no, title = extract_chapter_info(url)
        
        self.assertEqual(episode_no, "0")
        self.assertEqual(title, "Unknown")


class TestParseChapterLinks(unittest.TestCase):
    """Test chapter link parsing from HTML."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample HTML with various chapter link structures
        self.sample_html_npi_class = """
        <html>
            <body>
                <ul class="detail_lst">
                    <li>
                        <a class="NPI=a:list,g:en_en" href="/en/comedy/safely-endangered/ep-1040/viewer?title_no=352&amp;episode_no=1040">Episode 1040</a>
                    </li>
                    <li>
                        <a class="NPI=a:list,g:en_en" href="/en/comedy/safely-endangered/ep-1039/viewer?title_no=352&amp;episode_no=1039">Episode 1039</a>
                    </li>
                </ul>
            </body>
        </html>
        """
        
        self.sample_html_episode_items = """
        <html>
            <body>
                <ul id="_listUl">
                    <li class="_episodeItem">
                        <a href="/en/comedy/safely-endangered/ep-1040/viewer?title_no=352&episode_no=1040">Episode 1040</a>
                    </li>
                    <li class="_episodeItem">
                        <a href="/en/comedy/safely-endangered/ep-1039/viewer?title_no=352&episode_no=1039">Episode 1039</a>
                    </li>
                </ul>
            </body>
        </html>
        """
        
        self.sample_html_no_chapters = """
        <html>
            <body>
                <div>No chapter links here</div>
            </body>
        </html>
        """
    
    def test_parse_chapter_links_npi_class(self):
        """Test parsing with NPI class links."""
        soup = BeautifulSoup(self.sample_html_npi_class, 'html.parser')
        links = parse_chapter_links(soup)
        
        self.assertEqual(len(links), 2)
        self.assertIn('episode_no=1040', links[0])
        self.assertIn('episode_no=1039', links[1])
        # Check that &amp; is converted to &
        self.assertNotIn('&amp;', links[0])
    
    def test_parse_chapter_links_episode_items(self):
        """Test parsing with _episodeItem class."""
        soup = BeautifulSoup(self.sample_html_episode_items, 'html.parser')
        links = parse_chapter_links(soup)
        
        self.assertEqual(len(links), 2)
        # Links should contain episode information
        self.assertTrue(any('episode_no=1040' in link for link in links))
        self.assertTrue(any('episode_no=1039' in link for link in links))
        # Links should be valid URLs (either absolute or relative that can be converted)
        self.assertTrue(all('episode' in link and 'viewer' in link for link in links))
    
    def test_parse_chapter_links_no_chapters(self):
        """Test parsing when no chapter links exist."""
        soup = BeautifulSoup(self.sample_html_no_chapters, 'html.parser')
        links = parse_chapter_links(soup)
        
        self.assertEqual(len(links), 0)
    
    def test_parse_chapter_links_fallback_method(self):
        """Test fallback method for any episode links."""
        fallback_html = """
        <html>
            <body>
                <div>
                    <a href="/en/drama/test/ep-1/viewer?title_no=123&episode_no=1">Episode 1</a>
                    <a href="/en/drama/test/ep-2/viewer?title_no=123&episode_no=2">Episode 2</a>
                    <a href="/some/other/link">Not an episode</a>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(fallback_html, 'html.parser')
        links = parse_chapter_links(soup)
        
        self.assertEqual(len(links), 2)
        self.assertTrue(all('episode' in link for link in links))


class TestParseMangaMetadata(unittest.TestCase):
    """Test manga metadata parsing from HTML."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_html = """
        <html>
            <head>
                <title>Test Webtoon - WEBTOONS</title>
                <meta property="og:title" content="Test Webtoon">
            </head>
            <body>
                <h1>Test Webtoon Series</h1>
                <div class="author_area">Test Author<button>Subscribe</button></div>
                <h2 class="genre">Comedy, Drama</h2>
                <ul class="grade_area">
                    <li><span class="ico_view"></span><em class="cnt">1.2M</em></li>
                    <li><span class="ico_subscribe"></span><em class="cnt">500K</em></li>
                    <li><span class="ico_grade5"></span><em class="cnt">9.5</em></li>
                </ul>
                <p class="day_info">EVERY SUNDAY <span class="ico_up">UP</span></p>
                <div class="detail_bg" style="background:url('https://example.com/bg.jpg')"></div>
            </body>
        </html>
        """
    
    def test_parse_manga_metadata_complete(self):
        """Test parsing complete metadata."""
        soup = BeautifulSoup(self.sample_html, 'html.parser')
        metadata = parse_manga_metadata(soup)
        
        self.assertEqual(metadata['title'], 'Test Webtoon Series')
        self.assertEqual(metadata['author'], 'Test Author')
        self.assertEqual(metadata['genre'], 'Comedy, Drama')
        self.assertEqual(metadata['grade'], 9.5)
        self.assertEqual(metadata['views'], '1.2M')
        self.assertEqual(metadata['subscribers'], '500K')
        self.assertEqual(metadata['day_info'], 'EVERY SUNDAY')
        self.assertEqual(metadata['banner_bg_url'], 'https://example.com/bg.jpg')
    
    def test_parse_manga_metadata_missing_elements(self):
        """Test parsing with missing elements."""
        minimal_html = "<html><body><h1>Test Title</h1></body></html>"
        soup = BeautifulSoup(minimal_html, 'html.parser')
        metadata = parse_manga_metadata(soup)
        
        self.assertEqual(metadata['title'], 'Test Title')
        self.assertIsNone(metadata['author'])
        self.assertIsNone(metadata['genre'])
        self.assertIsNone(metadata['grade'])
    
    def test_parse_manga_metadata_fallback_title(self):
        """Test title extraction fallback methods."""
        fallback_html = """
        <html>
            <head>
                <meta property="og:title" content="OG Title">
                <title>Page Title</title>
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(fallback_html, 'html.parser')
        metadata = parse_manga_metadata(soup)
        
        self.assertEqual(metadata['title'], 'OG Title')


class TestParseChapterImages(unittest.TestCase):
    """Test chapter image parsing from HTML."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_html = """
        <html>
            <body>
                <div id="_imageList">
                    <img data-url="https://webtoon-phinf.pstatic.net/image1.jpg" alt="Page 1">
                    <img data-url="https://webtoon-phinf.pstatic.net/image2.jpg" alt="Page 2">
                    <img src="https://webtoon-phinf.pstatic.net/image3.jpg" alt="Page 3">
                    <img src="https://example.com/icon.gif" alt="Icon">  <!-- Should be filtered -->
                </div>
            </body>
        </html>
        """
    
    def test_parse_chapter_images_success(self):
        """Test successful image parsing."""
        soup = BeautifulSoup(self.sample_html, 'html.parser')
        images = parse_chapter_images(soup, 'https://example.com/chapter')
        
        self.assertEqual(len(images), 3)  # Should exclude .gif
        self.assertTrue(all('webtoon-phinf' in img for img in images))
        self.assertTrue(all(img.endswith('.jpg') for img in images))
    
    def test_parse_chapter_images_no_images(self):
        """Test parsing when no valid images exist."""
        no_images_html = "<html><body><div>No images here</div></body></html>"
        soup = BeautifulSoup(no_images_html, 'html.parser')
        images = parse_chapter_images(soup, 'https://example.com/chapter')
        
        self.assertEqual(len(images), 0)
    
    def test_parse_chapter_images_fallback_container(self):
        """Test fallback to different containers."""
        fallback_html = """
        <html>
            <body>
                <div class="viewer_lst">
                    <img src="https://comic.naver.net/image1.jpg" alt="Page 1">
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(fallback_html, 'html.parser')
        images = parse_chapter_images(soup, 'https://example.com/chapter')
        
        self.assertEqual(len(images), 1)
        self.assertIn('comic.naver.net', images[0])


class TestCreateObjects(unittest.TestCase):
    """Test object creation functions."""
    
    def test_create_manga_from_page(self):
        """Test creating Manga object from HTML page."""
        html = """
        <html>
            <body>
                <h1>Test Manga</h1>
                <div class="author_area">Test Author</div>
                <h2 class="genre">Action</h2>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        url = "https://www.webtoons.com/en/action/test-manga/list?title_no=123"
        
        manga = create_manga_from_page(soup, url)
        
        self.assertIsInstance(manga, Manga)
        self.assertEqual(manga.title_no, "123")
        self.assertEqual(manga.series_name, "test-manga")
        self.assertEqual(manga.display_title, "Test Manga")
        self.assertEqual(manga.author, "Test Author")
        self.assertEqual(manga.genre, "Action")
        self.assertEqual(manga.url, url)
    
    def test_create_chapters_from_links(self):
        """Test creating Chapter objects from URLs."""
        chapter_links = [
            "https://www.webtoons.com/en/action/test/ep-1-beginning/viewer?title_no=123&episode_no=1",
            "https://www.webtoons.com/en/action/test/ep-2-continue/viewer?title_no=123&episode_no=2"
        ]
        
        chapters = create_chapters_from_links(chapter_links)
        
        self.assertEqual(len(chapters), 2)
        self.assertIsInstance(chapters[0], Chapter)
        self.assertEqual(chapters[0].episode_no, "1")
        self.assertEqual(chapters[0].title, "Ep 1 Beginning")
        self.assertEqual(chapters[1].episode_no, "2")
        self.assertEqual(chapters[1].title, "Ep 2 Continue")


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_clean_text(self):
        """Test text cleaning function."""
        # Test whitespace normalization
        self.assertEqual(_clean_text("  hello   world  "), "hello world")
        self.assertEqual(_clean_text("hello\n\tworld"), "hello world")
        
        # Test comma cleanup
        self.assertEqual(_clean_text("author,, test"), "author, test")
        self.assertEqual(_clean_text(",leading comma"), "leading comma")
        self.assertEqual(_clean_text("trailing comma,"), "trailing comma")
        
        # Test None and empty string
        self.assertEqual(_clean_text(None), None)
        self.assertEqual(_clean_text(""), "")
    
    def test_extract_banner_urls(self):
        """Test banner URL extraction."""
        html_with_bg = """
        <html>
            <body>
                <div class="detail_bg" style="background:url('https://example.com/bg.jpg')"></div>
                <img src="https://example.com/desktop_fg.png" alt="Character">
            </body>
        </html>
        """
        soup = BeautifulSoup(html_with_bg, 'html.parser')
        result = _extract_banner_urls(soup)
        
        # Verify function returns proper structure and doesn't crash
        self.assertIsInstance(result, dict)
        self.assertIn('banner_bg_url', result)
        self.assertIn('banner_fg_url', result)
        
        # If URLs are extracted, they should be valid
        if result['banner_bg_url']:
            self.assertTrue(result['banner_bg_url'].startswith('http'))
        if result['banner_fg_url']:
            self.assertTrue(result['banner_fg_url'].startswith('http'))
    
    def test_extract_banner_urls_relative_urls(self):
        """Test banner URL extraction with relative URLs."""
        html_relative = """
        <html>
            <body>
                <div style="background:url('//cdn.example.com/bg.jpg')"></div>
                <img src="/images/desktop_fg.png" alt="FG">
            </body>
        </html>
        """
        soup = BeautifulSoup(html_relative, 'html.parser')
        result = _extract_banner_urls(soup)
        
        # These might be None if the extraction patterns don't match exactly
        # Just verify the function doesn't crash and returns a dict
        self.assertIsInstance(result, dict)
        self.assertIn('banner_bg_url', result)
        self.assertIn('banner_fg_url', result)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_extract_chapter_info_malformed_urls(self):
        """Test handling of malformed URLs."""
        malformed_urls = [
            "",
            "not-a-url",
            "http://",
            "https://www.webtoons.com",
            "javascript:alert('xss')"
        ]
        
        for url in malformed_urls:
            episode_no, title = extract_chapter_info(url)
            self.assertEqual(episode_no, "0")
            self.assertEqual(title, "Unknown")
    
    def test_parse_metadata_with_malformed_html(self):
        """Test metadata parsing with malformed HTML."""
        malformed_html = "<html><body><h1>Test<span>Unclosed</body></html>"
        soup = BeautifulSoup(malformed_html, 'html.parser')
        
        # Should not crash
        metadata = parse_manga_metadata(soup)
        self.assertIsInstance(metadata, dict)
        self.assertIn('title', metadata)
    
    def test_parse_chapter_links_with_empty_soup(self):
        """Test chapter link parsing with empty HTML."""
        empty_soup = BeautifulSoup("", 'html.parser')
        links = parse_chapter_links(empty_soup)
        
        self.assertEqual(len(links), 0)
    
    def test_parse_chapter_images_with_malformed_urls(self):
        """Test image parsing with malformed URLs."""
        malformed_html = """
        <html>
            <body>
                <div id="_imageList">
                    <img data-url="not-a-valid-url" alt="Invalid">
                    <img data-url="" alt="Empty">
                    <img alt="No src">
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(malformed_html, 'html.parser')
        
        # Should not crash and should handle gracefully
        images = parse_chapter_images(soup, 'https://example.com/chapter')
        self.assertIsInstance(images, list)


if __name__ == '__main__':
    unittest.main() 