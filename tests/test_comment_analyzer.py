#!/usr/bin/env python3
"""
Tests for CommentAnalyzer functionality.
Tests comment extraction, summarization, and analysis.
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

from scraper.comment_analyzer import (
    CommentAnalyzer, 
    extract_comments, 
    summarize_comments,
    save_comments_to_file,
    _generate_simple_summary,
    _generate_nltk_summary
)


class TestCommentExtraction(unittest.TestCase):
    """Test cases for comment extraction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = CommentAnalyzer()
        
        # Sample HTML with comments
        self.sample_comments_html = """
        <html>
            <body>
                <ul class="wcc_CommentList">
                    <li class="wcc_CommentItem__root">
                        <div class="wcc_CommentItem__inside">
                            <div class="wcc_CommentHeader">
                                <span class="wcc_CommentHeader__name">TestUser1</span>
                                <time class="wcc_CommentHeader__createdAt">2024-01-01</time>
                            </div>
                            <div class="wcc_CommentBody">
                                <p class="wcc_TextContent__content">
                                    <span>This is a great chapter! Amazing artwork.</span>
                                </p>
                            </div>
                            <div class="wcc_CommentReaction__root">
                                <button class="wcc_CommentReaction__action">
                                    <span>42</span>
                                </button>
                            </div>
                        </div>
                    </li>
                    <li class="wcc_CommentItem__root">
                        <div class="wcc_CommentItem__inside">
                            <div class="wcc_CommentHeader">
                                <span class="wcc_CommentHeader__name">TestUser2</span>
                                <time class="wcc_CommentHeader__createdAt">2024-01-02</time>
                            </div>
                            <div class="wcc_CommentBody">
                                <p class="wcc_TextContent__content">
                                    <span>I love the character development here.</span>
                                </p>
                            </div>
                            <div class="wcc_CommentReaction__root">
                                <button class="wcc_CommentReaction__action">
                                    <span>15</span>
                                </button>
                            </div>
                        </div>
                    </li>
                </ul>
            </body>
        </html>
        """
        
        # Sample HTML with no comments
        self.no_comments_html = """
        <html>
            <body>
                <div>No comments available</div>
            </body>
        </html>
        """
    
    def test_extract_comments_success(self):
        """Test successful comment extraction."""
        soup = BeautifulSoup(self.sample_comments_html, 'html.parser')
        comments = extract_comments(soup, 'https://example.com/chapter')
        
        # Assertions
        self.assertEqual(len(comments), 2)
        
        # Check first comment
        self.assertEqual(comments[0]['username'], 'TestUser1')
        self.assertEqual(comments[0]['date'], '2024-01-01')
        self.assertIn('great chapter', comments[0]['text'])
        self.assertEqual(comments[0]['likes'], '42')
        
        # Check second comment
        self.assertEqual(comments[1]['username'], 'TestUser2')
        self.assertEqual(comments[1]['date'], '2024-01-02')
        self.assertIn('character development', comments[1]['text'])
        self.assertEqual(comments[1]['likes'], '15')
    
    def test_extract_comments_no_comments(self):
        """Test comment extraction when no comments exist."""
        soup = BeautifulSoup(self.no_comments_html, 'html.parser')
        comments = extract_comments(soup, 'https://example.com/chapter')
        
        # Assertions
        self.assertEqual(len(comments), 0)
    
    def test_extract_comments_malformed_html(self):
        """Test comment extraction with malformed HTML."""
        malformed_html = """
        <html>
            <body>
                <li class="wcc_CommentItem__root">
                    <div class="wcc_CommentItem__inside">
                        <span class="wcc_CommentHeader__name">PartialUser</span>
                        <!-- Missing other elements -->
                    </div>
                </li>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(malformed_html, 'html.parser')
        comments = extract_comments(soup, 'https://example.com/chapter')
        
        # Should handle gracefully and extract what it can
        self.assertIsInstance(comments, list)
    
    def test_comment_analyzer_extract_comments_from_soup(self):
        """Test CommentAnalyzer.extract_comments_from_soup method."""
        soup = BeautifulSoup(self.sample_comments_html, 'html.parser')
        
        with patch('scraper.comment_analyzer.CommentAnalyzer._save_debug_html'):
            comments = self.analyzer.extract_comments_from_soup(soup, 'https://example.com/chapter')
        
        # Assertions
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]['username'], 'TestUser1')
        self.assertEqual(comments[1]['username'], 'TestUser2')
    
    @patch('builtins.open', create=True)
    def test_save_debug_html(self, mock_open):
        """Test debug HTML saving."""
        soup = BeautifulSoup(self.sample_comments_html, 'html.parser')
        
        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        self.analyzer._save_debug_html(soup)
        
        # Assertions
        mock_open.assert_called_once_with('webtoon_page_debug.html', 'w', encoding='utf-8')
        mock_file.write.assert_called_once()


class TestCommentSummarization(unittest.TestCase):
    """Test cases for comment summarization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_comments = [
            {
                'username': 'User1',
                'date': '2024-01-01',
                'text': 'This chapter is amazing! The artwork is beautiful and the story is compelling.',
                'likes': '50'
            },
            {
                'username': 'User2', 
                'date': '2024-01-01',
                'text': 'I love the character development in this series. Great work by the author.',
                'likes': '25'
            },
            {
                'username': 'User3',
                'date': '2024-01-01', 
                'text': 'The plot twist was unexpected! Cannot wait for the next chapter.',
                'likes': '30'
            }
        ]
    
    def test_summarize_comments_empty_list(self):
        """Test summarization with empty comment list."""
        summary = summarize_comments([])
        self.assertEqual(summary, "No comments available for this episode.")
    
    def test_generate_simple_summary(self):
        """Test simple summarization without NLTK."""
        summary = _generate_simple_summary(self.sample_comments)
        
        # Assertions
        self.assertIn('3 comments', summary)
        self.assertIn('50 likes', summary)  # Most upvoted comment
        self.assertIn('amazing', summary)   # Part of most upvoted comment
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 50)
    
    @patch('scraper.comment_analyzer.nltk')
    @patch('scraper.comment_analyzer.word_tokenize')
    @patch('scraper.comment_analyzer.stopwords')
    @patch('scraper.comment_analyzer.SentimentIntensityAnalyzer')
    def test_generate_nltk_summary(self, mock_sia, mock_stopwords, mock_tokenize, mock_nltk):
        """Test NLTK-based summarization."""
        # Mock NLTK components
        mock_tokenize.return_value = ['this', 'chapter', 'is', 'amazing', 'artwork', 'beautiful']
        mock_stopwords.words.return_value = {'is', 'the', 'and', 'of', 'in'}
        
        # Mock sentiment analyzer
        mock_analyzer = Mock()
        mock_analyzer.polarity_scores.return_value = {'compound': 0.8}
        mock_sia.return_value = mock_analyzer
        
        summary = _generate_nltk_summary(self.sample_comments)
        
        # Assertions
        self.assertIn('3 comments', summary)
        self.assertIn('positive', summary)  # Should detect positive sentiment
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 50)
    
    @patch('scraper.comment_analyzer._generate_simple_summary')
    def test_summarize_comments_fallback_to_simple(self, mock_simple):
        """Test fallback to simple summary when NLTK fails."""
        mock_simple.return_value = "Simple summary fallback"
        
        # This should trigger the except block and fall back to simple summary
        with patch('scraper.comment_analyzer.nltk', side_effect=ImportError("NLTK not available")):
            summary = summarize_comments(self.sample_comments)
        
        # Assertions
        mock_simple.assert_called_once_with(self.sample_comments)
        self.assertEqual(summary, "Simple summary fallback")
    
    def test_comment_analyzer_analyze_comments(self):
        """Test CommentAnalyzer.analyze_comments method."""
        analyzer = CommentAnalyzer()
        
        with patch.object(analyzer, '_analyze_simple') as mock_simple:
            mock_simple.return_value = "Analyzed summary"
            analyzer.nltk_available = False
            
            result = analyzer.analyze_comments(self.sample_comments)
            
            mock_simple.assert_called_once_with(self.sample_comments)
            self.assertEqual(result, "Analyzed summary")
    
    def test_save_comments_to_file(self):
        """Test saving comments to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_comments_to_file(self.sample_comments, temp_dir, "001")
            
            # Check if file was created
            expected_file = os.path.join(temp_dir, "comments_episode_001.txt")
            self.assertTrue(os.path.exists(expected_file))
            
            # Check file contents
            with open(expected_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            self.assertIn('Comments for Episode 001', content)
            self.assertIn('Total comments: 3', content)
            self.assertIn('SUMMARY:', content)
            self.assertIn('User1', content)
            self.assertIn('amazing', content)
    
    def test_save_comments_empty_list(self):
        """Test saving empty comment list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_comments_to_file([], temp_dir, "001")
            
            # File should not be created for empty comments
            expected_file = os.path.join(temp_dir, "comments_episode_001.txt")
            self.assertFalse(os.path.exists(expected_file))


class TestCommentAnalyzerIntegration(unittest.TestCase):
    """Integration tests for CommentAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = CommentAnalyzer()
    
    @patch('scraper.comment_analyzer.CommentAnalyzer._save_debug_html')
    def test_full_comment_analysis_workflow(self, mock_save_debug):
        """Test complete comment extraction and analysis workflow."""
        # Complex HTML with various comment structures
        complex_html = """
        <html>
            <body>
                <ul class="wcc_CommentList">
                    <li class="wcc_CommentItem__root">
                        <div class="wcc_CommentItem__inside">
                            <span class="wcc_CommentHeader__name">CriticUser</span>
                            <time class="wcc_CommentHeader__createdAt">2024-01-01</time>
                            <p class="wcc_TextContent__content">
                                <span>This chapter was disappointing. The pacing felt rushed.</span>
                            </p>
                            <div class="wcc_CommentReaction__root">
                                <button class="wcc_CommentReaction__action"><span>5</span></button>
                            </div>
                        </div>
                    </li>
                    <li class="wcc_CommentItem__root">
                        <div class="wcc_CommentItem__inside">
                            <span class="wcc_CommentHeader__name">FanUser</span>
                            <time class="wcc_CommentHeader__createdAt">2024-01-01</time>
                            <p class="wcc_TextContent__content">
                                <span>Amazing artwork! The emotional depth is incredible.</span>
                            </p>
                            <div class="wcc_CommentReaction__root">
                                <button class="wcc_CommentReaction__action"><span>100</span></button>
                            </div>
                        </div>
                    </li>
                </ul>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(complex_html, 'html.parser')
        
        # Extract comments
        comments = self.analyzer.extract_comments_from_soup(soup, 'https://example.com/chapter')
        
        # Analyze comments
        summary = self.analyzer.analyze_comments(comments)
        
        # Assertions
        self.assertEqual(len(comments), 2)
        self.assertIn('disappointing', comments[0]['text'])
        self.assertIn('Amazing artwork', comments[1]['text'])
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 20)
        
        # Verify debug HTML was saved
        mock_save_debug.assert_called_once()


if __name__ == '__main__':
    unittest.main() 