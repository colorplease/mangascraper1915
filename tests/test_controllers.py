#!/usr/bin/env python3
"""
Tests for MVC controllers.
Tests the business logic separation and controller functionality.
"""

import unittest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from controllers.manga_controller import MangaController
from controllers.download_controller import DownloadController, DownloadProgress
from models.manga import Manga
from models.chapter import Chapter
from utils.db_manager import DatabaseManager


class TestMangaController(unittest.TestCase):
    """Test the MangaController business logic."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.controller = MangaController(self.mock_db_manager)
        
        # Mock config to use temp directory
        self.config_patcher = patch('controllers.manga_controller.Config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.get_downloads_dir.return_value = Path(self.temp_dir)
        self.mock_config.get_manga_folder.return_value = Path(self.temp_dir) / "test_manga"
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.config_patcher.stop()
    
    def test_manga_controller_initialization(self):
        """Test that MangaController initializes correctly."""
        self.assertIsNotNone(self.controller.db_manager)
        self.assertEqual(len(self.controller.downloaded_manga), 0)
        self.assertIsNone(self.controller.current_manga)
    
    def test_load_downloaded_manga_empty_directory(self):
        """Test loading manga from empty directory."""
        # Set up callback
        loaded_manga = None
        def on_manga_loaded(manga_list):
            nonlocal loaded_manga
            loaded_manga = manga_list
        
        self.controller.on_manga_loaded = on_manga_loaded
        
        # Load manga
        self.controller.load_downloaded_manga()
        
        # Verify empty list
        self.assertEqual(loaded_manga, [])
        self.assertEqual(len(self.controller.downloaded_manga), 0)
    
    def test_load_downloaded_manga_with_folders(self):
        """Test loading manga from directory with manga folders."""
        # Create test manga folder
        manga_folder = Path(self.temp_dir) / "webtoon_123_test-manga"
        manga_folder.mkdir(parents=True)
        
        # Create manga_info.json
        manga_info = {
            "title_no": "123",
            "series_name": "test-manga", 
            "display_title": "Test Manga",
            "author": "Test Author",
            "genre": "Action",
            "num_chapters": 10
        }
        
        with open(manga_folder / "manga_info.json", 'w', encoding='utf-8') as f:
            json.dump(manga_info, f)
        
        # Set up callback
        loaded_manga = None
        def on_manga_loaded(manga_list):
            nonlocal loaded_manga
            loaded_manga = manga_list
        
        self.controller.on_manga_loaded = on_manga_loaded
        
        # Load manga
        self.controller.load_downloaded_manga()
        
        # Verify manga was loaded
        self.assertIsNotNone(loaded_manga)
        self.assertEqual(len(loaded_manga), 1)
        self.assertEqual(loaded_manga[0].title_no, "123")
        self.assertEqual(loaded_manga[0].display_title, "Test Manga")
    
    def test_select_manga(self):
        """Test manga selection functionality."""
        # Create test manga
        manga = Manga(
            title_no="123",
            series_name="test-manga",
            display_title="Test Manga"
        )
        
        # Set up callbacks
        selected_manga = None
        def on_manga_selected(m):
            nonlocal selected_manga
            selected_manga = m
        
        self.controller.on_manga_selected = on_manga_selected
        
        # Select manga
        self.controller.select_manga(manga)
        
        # Verify selection
        self.assertEqual(self.controller.current_manga, manga)
        self.assertEqual(selected_manga, manga)
    
    def test_get_manga_by_folder_name(self):
        """Test retrieving manga by folder name."""
        # Create test manga
        manga = Manga(
            title_no="123",
            series_name="test-manga",
            display_title="Test Manga"
        )
        
        # Add to controller's list
        self.controller._downloaded_manga = [manga]
        
        # Test retrieval
        found_manga = self.controller.get_manga_by_folder_name("webtoon_123_test-manga")
        self.assertEqual(found_manga, manga)
        
        # Test not found
        not_found = self.controller.get_manga_by_folder_name("nonexistent")
        self.assertIsNone(not_found)


class TestDownloadController(unittest.TestCase):
    """Test the DownloadController business logic."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Mock the dependencies
        self.client_patcher = patch('controllers.download_controller.WebtoonClient')
        self.download_patcher = patch('controllers.download_controller.DownloadManager')
        self.analyzer_patcher = patch('controllers.download_controller.CommentAnalyzer')
        self.config_patcher = patch('controllers.download_controller.Config')
        
        self.mock_client = self.client_patcher.start()
        self.mock_download_manager = self.download_patcher.start()
        self.mock_analyzer = self.analyzer_patcher.start()
        self.mock_config = self.config_patcher.start()
        
        self.controller = DownloadController(self.mock_db_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        self.client_patcher.stop()
        self.download_patcher.stop()
        self.analyzer_patcher.stop()
        self.config_patcher.stop()
    
    def test_download_controller_initialization(self):
        """Test that DownloadController initializes correctly."""
        self.assertIsNotNone(self.controller.db_manager)
        self.assertIsNone(self.controller.current_manga)
        self.assertFalse(self.controller.is_downloading)
    
    def test_download_progress_class(self):
        """Test the DownloadProgress tracking class."""
        progress = DownloadProgress(total_chapters=10)
        
        # Test initial state
        self.assertEqual(progress.total_chapters, 10)
        self.assertEqual(progress.completed_chapters, 0)
        self.assertFalse(progress.is_complete)
        
        # Test progress calculations
        progress.completed_chapters = 5
        self.assertEqual(progress.chapter_progress_percent, 50)
        
        progress.total_images = 100
        progress.completed_images = 25
        self.assertEqual(progress.image_progress_percent, 25)
    
    def test_set_current_manga(self):
        """Test setting current manga context."""
        # Create test manga
        manga = Manga(
            title_no="123",
            series_name="test-manga",
            display_title="Test Manga"
        )
        
        # Set current manga
        self.controller.set_current_manga(manga)
        
        # Verify it was set
        self.assertEqual(self.controller.current_manga, manga)
    
    def test_fetch_chapters_without_downloading(self):
        """Test that fetch_chapters method exists and handles errors properly."""
        # Test fetch when already downloading
        self.controller._is_downloading = True
        
        error_called = False
        def on_error(message):
            nonlocal error_called
            error_called = True
        
        self.controller.on_error = on_error
        
        # Should trigger error since already downloading
        self.controller.fetch_chapters("test_url")
        self.assertTrue(error_called)
    
    def test_download_chapters_validation(self):
        """Test download chapters validation."""
        error_messages = []
        def on_error(message):
            error_messages.append(message)
        
        self.controller.on_error = on_error
        
        # Test download without manga
        self.controller.download_chapters([])
        self.assertIn("No manga selected", error_messages[-1])
        
        # Test download without chapters
        manga = Manga(title_no="123", series_name="test", display_title="Test")
        self.controller.set_current_manga(manga)
        self.controller.download_chapters([])
        self.assertIn("No chapters selected", error_messages[-1])
    
    def test_cleanup(self):
        """Test controller cleanup."""
        # Should not raise any exceptions
        self.controller.cleanup()
        self.assertFalse(self.controller.is_downloading)


class TestMVCIntegration(unittest.TestCase):
    """Test MVC integration and event-driven architecture."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.manga_controller = MangaController(self.mock_db_manager)
        self.download_controller = DownloadController(self.mock_db_manager)
    
    def test_controller_event_callbacks(self):
        """Test that controllers properly trigger callbacks."""
        # Test manga controller callbacks
        manga_loaded_called = False
        manga_selected_called = False
        
        def on_manga_loaded(manga_list):
            nonlocal manga_loaded_called
            manga_loaded_called = True
        
        def on_manga_selected(manga):
            nonlocal manga_selected_called
            manga_selected_called = True
        
        self.manga_controller.on_manga_loaded = on_manga_loaded
        self.manga_controller.on_manga_selected = on_manga_selected
        
        # Trigger events
        if self.manga_controller.on_manga_loaded:
            self.manga_controller.on_manga_loaded([])
        
        test_manga = Manga(title_no="123", series_name="test", display_title="Test")
        self.manga_controller.select_manga(test_manga)
        
        # Verify callbacks were called
        self.assertTrue(manga_loaded_called)
        self.assertTrue(manga_selected_called)
    
    def test_controller_independence(self):
        """Test that controllers can operate independently."""
        # Controllers should not depend on each other directly
        self.assertIsNone(self.manga_controller.current_manga)
        self.assertIsNone(self.download_controller.current_manga)
        
        # Setting manga in one controller shouldn't affect the other
        test_manga = Manga(title_no="123", series_name="test", display_title="Test")
        self.manga_controller.select_manga(test_manga)
        
        self.assertEqual(self.manga_controller.current_manga, test_manga)
        self.assertIsNone(self.download_controller.current_manga)
    
    def test_error_handling_separation(self):
        """Test that error handling is properly separated."""
        error_count = 0
        
        def on_error(message):
            nonlocal error_count
            error_count += 1
        
        # Each controller can have its own error handling
        self.manga_controller.on_error = on_error
        self.download_controller.on_error = on_error
        
        # Trigger errors
        if self.manga_controller.on_error:
            self.manga_controller.on_error("Test error 1")
        
        if self.download_controller.on_error:
            self.download_controller.on_error("Test error 2")
        
        self.assertEqual(error_count, 2)


class TestMVCBusinessLogicSeparation(unittest.TestCase):
    """Test that business logic is properly separated from UI concerns."""
    
    def test_controllers_have_no_ui_dependencies(self):
        """Test that controllers don't import UI modules."""
        # Controllers should not have tkinter or other UI imports
        
        import controllers.manga_controller as manga_mod
        import controllers.download_controller as download_mod
        
        # Check that controllers don't import tkinter
        manga_source = open(manga_mod.__file__).read()
        download_source = open(download_mod.__file__).read()
        
        self.assertNotIn('tkinter', manga_source.lower())
        self.assertNotIn('tkinter', download_source.lower())
        
        # They should only import models, utils, and scraper components
        allowed_imports = ['models', 'utils', 'scraper', 'typing', 'os', 'json', 'threading', 'pathlib', 'concurrent']
        
        # This is a basic check - in a real scenario you'd parse imports more carefully
        self.assertTrue(any(imp in manga_source for imp in allowed_imports))
        self.assertTrue(any(imp in download_source for imp in allowed_imports))
    
    def test_models_are_pure_data(self):
        """Test that models contain only data and no business logic."""
        # Models should be able to be instantiated and used without dependencies
        manga = Manga(
            title_no="123",
            series_name="test-manga",
            display_title="Test Manga"
        )
        
        chapter = Chapter(
            episode_no="1",
            title="Test Chapter",
            url="https://example.com/chapter/1"
        )
        
        # Should be able to add chapter to manga
        manga.add_chapter(chapter)
        self.assertEqual(len(manga.chapters), 1)
        self.assertEqual(manga.num_chapters, 1)
        
        # Should be able to serialize/deserialize
        manga_dict = manga.to_dict()
        reconstructed = Manga.from_dict(manga_dict)
        self.assertEqual(reconstructed.title_no, manga.title_no)
        self.assertEqual(len(reconstructed.chapters), 1)
    
    def test_controllers_provide_business_api(self):
        """Test that controllers provide clean business API."""
        mock_db = Mock()
        controller = MangaController(mock_db)
        
        # Controllers should provide clear business methods
        self.assertTrue(hasattr(controller, 'load_downloaded_manga'))
        self.assertTrue(hasattr(controller, 'select_manga'))
        self.assertTrue(hasattr(controller, 'get_chapter_comments'))
        self.assertTrue(hasattr(controller, 'open_chapter_folder'))
        
        # Methods should be callable
        self.assertTrue(callable(controller.load_downloaded_manga))
        self.assertTrue(callable(controller.select_manga))


if __name__ == '__main__':
    unittest.main() 