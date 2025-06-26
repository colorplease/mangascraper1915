#!/usr/bin/env python3
"""
Tests for database functionality.
Tests DatabaseManager, db_utils, and all database operations.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sqlite3
from datetime import datetime

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from utils.db_manager import DatabaseManager
from models.manga import Manga
from models.chapter import Chapter
import db_utils


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager."""
    
    def setUp(self):
        """Set up test fixtures with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Ensure we start with a fresh database
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except:
                pass
        
        # Patch db_utils.DB_PATH to use our temporary database
        self.original_db_path = getattr(db_utils, 'DB_PATH', None)
        db_utils.DB_PATH = self.db_path
        
        # Also patch the DB_PATH in utils.config if it exists
        try:
            from utils.config import Config
            if hasattr(Config, 'DB_PATH'):
                self.original_config_db_path = Config.DB_PATH
                Config.DB_PATH = self.db_path
        except ImportError:
            self.original_config_db_path = None
        
        self.db_manager = DatabaseManager(self.db_path)
        
        # Sample manga for testing
        self.sample_manga = Manga(
            title_no="123",
            series_name="test-series",  # Use hyphen format to match extraction logic
            display_title="Test Series",
            author="Test Author",
            genre="Drama",
            num_chapters=5,
            url="https://example.com/test_series"
        )
        
        # Sample chapters
        self.sample_chapters = [
            Chapter(episode_no="1", title="Chapter 1", url="https://example.com/ch1"),
            Chapter(episode_no="2", title="Chapter 2", url="https://example.com/ch2")
        ]
        self.sample_manga.chapters = self.sample_chapters
    
    def tearDown(self):
        """Clean up after tests."""
        # Close any connections first
        try:
            if hasattr(self, 'db_manager'):
                self.db_manager = None
        except:
            pass
        
        # Restore original DB_PATH
        if hasattr(self, 'original_db_path') and self.original_db_path:
            db_utils.DB_PATH = self.original_db_path
        
        # Restore original config DB_PATH if we patched it
        if hasattr(self, 'original_config_db_path') and self.original_config_db_path:
            try:
                from utils.config import Config
                Config.DB_PATH = self.original_config_db_path
            except ImportError:
                pass
        
        # Clean up database file
        try:
            if hasattr(self, 'db_path') and os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except:
            pass
    
    def test_init_database(self):
        """Test database initialization."""
        # Force database initialization
        self.db_manager.init_database()
        
        # Check if tables exist
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall()]
            
        self.assertIn('manga', tables)
        self.assertIn('chapters', tables)
    
    def test_save_manga(self):
        """Test saving manga to database."""
        manga_id = self.db_manager.save_manga(self.sample_manga)
        
        self.assertIsInstance(manga_id, int)
        self.assertGreater(manga_id, 0)
        self.assertEqual(self.sample_manga.id, manga_id)
    
    def test_get_manga_by_id(self):
        """Test retrieving manga by ID."""
        # Save manga first
        manga_id = self.db_manager.save_manga(self.sample_manga)
        
        # Retrieve manga
        retrieved_manga = self.db_manager.get_manga_by_id(manga_id)
        
        self.assertIsNotNone(retrieved_manga)
        self.assertEqual(retrieved_manga.title_no, "123")
        self.assertEqual(retrieved_manga.display_title, "Test Series")
        self.assertEqual(len(retrieved_manga.chapters), 2)
    
    def test_get_manga_by_title_no(self):
        """Test retrieving manga by title number."""
        self.db_manager.save_manga(self.sample_manga)
        
        retrieved_manga = self.db_manager.get_manga_by_title_no("123")
        
        self.assertIsNotNone(retrieved_manga)
        self.assertEqual(retrieved_manga.series_name, "test-series")  # Expect hyphen format
    
    def test_get_all_manga(self):
        """Test retrieving all manga."""
        # Save multiple manga
        manga1 = self.sample_manga
        manga2 = Manga(
            title_no="456",
            series_name="another_series", 
            display_title="Another Series"
        )
        
        self.db_manager.save_manga(manga1)
        self.db_manager.save_manga(manga2)
        
        all_manga = self.db_manager.get_all_manga()
        
        self.assertEqual(len(all_manga), 2)
        titles = [m.display_title for m in all_manga]
        self.assertIn("Test Series", titles)
        self.assertIn("Another Series", titles)
    
    def test_search_manga_by_title(self):
        """Test searching manga by title."""
        self.db_manager.save_manga(self.sample_manga)
        
        results = self.db_manager.search_manga_by_title("Test")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].display_title, "Test Series")
    
    def test_search_manga_by_author(self):
        """Test searching manga by author."""
        self.db_manager.save_manga(self.sample_manga)
        
        results = self.db_manager.search_manga_by_author("Test Author")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].author, "Test Author")
    
    def test_search_manga_by_genre(self):
        """Test searching manga by genre."""
        self.db_manager.save_manga(self.sample_manga)
        
        results = self.db_manager.search_manga_by_genre("Drama")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].genre, "Drama")
    
    def test_delete_manga(self):
        """Test deleting manga from database."""
        manga_id = self.db_manager.save_manga(self.sample_manga)
        
        # Delete manga
        success = self.db_manager.delete_manga(manga_id)
        
        self.assertTrue(success)
        
        # Verify deletion
        retrieved_manga = self.db_manager.get_manga_by_id(manga_id)
        self.assertIsNone(retrieved_manga)
    
    def test_save_chapters(self):
        """Test saving chapters for manga."""
        manga_id = self.db_manager.save_manga(self.sample_manga)
        
        # Additional chapters
        new_chapters = [
            Chapter(episode_no="3", title="Chapter 3", url="https://example.com/ch3")
        ]
        
        self.db_manager.save_chapters(manga_id, new_chapters)
        
        # Verify chapters were saved
        retrieved_manga = self.db_manager.get_manga_by_id(manga_id)
        self.assertEqual(len(retrieved_manga.chapters), 1)  # Only new chapters saved
    
    def test_get_download_statistics(self):
        """Test getting download statistics."""
        self.db_manager.save_manga(self.sample_manga)
        
        stats = self.db_manager.get_download_statistics()
        
        self.assertIn('total_manga', stats)
        self.assertIn('total_chapters', stats)
        self.assertIn('average_chapters', stats)
        self.assertEqual(stats['total_manga'], 1)
        self.assertEqual(stats['total_chapters'], 2)


class TestDatabaseUtils(unittest.TestCase):
    """Test cases for db_utils module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Patch the DB_PATH to use our temporary database
        self.original_db_path = getattr(db_utils, 'DB_PATH', None)
        db_utils.DB_PATH = self.temp_db.name
        
        # Initialize database
        try:
            db_utils.init_db()
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    def tearDown(self):
        """Clean up after tests."""
        # Restore original DB_PATH
        if self.original_db_path:
            db_utils.DB_PATH = self.original_db_path
        
        try:
            if hasattr(self, 'temp_db') and os.path.exists(self.temp_db.name):
                os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_init_db(self):
        """Test database initialization via db_utils."""
        # Database should be initialized in setUp
        with sqlite3.connect(self.temp_db.name) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall()]
            
        self.assertIn('manga', tables)
        self.assertIn('chapters', tables)
    
    @patch('db_utils.get_connection')
    def test_insert_or_update_manga(self, mock_get_connection):
        """Test manga insert/update via db_utils."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No existing manga
        mock_cursor.lastrowid = 1
        mock_get_connection.return_value.__enter__.return_value = mock_conn
        
        manga_id = db_utils.insert_or_update_manga(
            title_no="123",
            series_name="test_series",
            display_title="Test Series",
            author="Test Author",
            genre="Drama",
            num_chapters=5,
            url="https://example.com/test"
        )
        
        self.assertEqual(manga_id, 1)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_full_manga_lifecycle(self):
        """Test complete manga lifecycle: create, read, update, delete."""
        # Create
        manga = Manga(
            title_no="999",
            series_name="lifecycle_test",
            display_title="Lifecycle Test Manga",
            author="Test Author",
            genre="Action"
        )
        
        # Add chapters
        chapters = [
            Chapter(episode_no="1", title="First Chapter", url="https://example.com/1"),
            Chapter(episode_no="2", title="Second Chapter", url="https://example.com/2")
        ]
        manga.chapters = chapters
        
        # Save (Create)
        manga_id = self.db_manager.save_manga(manga)
        self.assertGreater(manga_id, 0)
        
        # Read
        retrieved = self.db_manager.get_manga_by_id(manga_id)
        self.assertEqual(retrieved.display_title, "Lifecycle Test Manga")
        self.assertEqual(len(retrieved.chapters), 2)
        
        # Update - modify and save again
        retrieved.display_title = "Updated Manga Title"
        updated_id = self.db_manager.save_manga(retrieved)
        self.assertEqual(updated_id, manga_id)  # Should be same ID
        
        # Verify update
        re_retrieved = self.db_manager.get_manga_by_id(manga_id)
        self.assertEqual(re_retrieved.display_title, "Updated Manga Title")
        
        # Delete
        success = self.db_manager.delete_manga(manga_id)
        self.assertTrue(success)
        
        # Verify deletion
        deleted = self.db_manager.get_manga_by_id(manga_id)
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main() 