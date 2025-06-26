"""
Database manager for the webtoon scraper application.

This module provides a high-level interface for database operations,
building on the existing db_utils functionality.
"""

import sqlite3
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime

# Import existing database utilities
import db_utils
from models.manga import Manga
from models.chapter import Chapter
from utils.config import Config


class DatabaseManager:
    """High-level database manager for manga and chapter operations."""
    
    def __init__(self, db_path: str = None):
        """Initialize the database manager."""
        self.db_path = db_path or str(Config.DB_PATH)
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize the database with required tables."""
        db_utils.init_db()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection context manager."""
        with db_utils.get_connection() as conn:
            yield conn
    
    def save_manga(self, manga: Manga) -> int:
        """Save or update a manga in the database."""
        manga_id = db_utils.insert_or_update_manga(
            title_no=manga.title_no,
            series_name=manga.series_name,
            display_title=manga.display_title,
            author=manga.author,
            genre=manga.genre,
            num_chapters=manga.num_chapters,
            url=manga.url,
            grade=manga.grade,
            views=manga.views,
            subscribers=manga.subscribers,
            day_info=manga.day_info
        )
        
        # Update the manga object with the database ID
        manga.id = manga_id
        
        # Save chapters if they exist
        if manga.chapters:
            self.save_chapters(manga_id, manga.chapters)
        
        return manga_id
    
    def save_chapters(self, manga_id: int, chapters: List[Chapter]) -> None:
        """Save chapters for a manga."""
        # Convert chapters to the format expected by db_utils
        chapters_data = []
        for chapter in chapters:
            chapters_data.append({
                'episode_no': chapter.episode_no,
                'chapter_title': chapter.title,
                'url': chapter.url
            })
            # Update chapter with manga_id
            chapter.manga_id = manga_id
        
        # Clear existing chapters for this manga first
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM chapters WHERE manga_id=?', (manga_id,))
            conn.commit()
        
        # Insert new chapters
        db_utils.insert_chapters(manga_id, chapters_data)
    
    def get_manga_by_id(self, manga_id: int) -> Optional[Manga]:
        """Get a manga by its database ID."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM manga WHERE id=?', (manga_id,))
            row = c.fetchone()
            
            if not row:
                return None
            
            manga = self._row_to_manga(row)
            
            # Load chapters
            c.execute('SELECT * FROM chapters WHERE manga_id=?', (manga_id,))
            chapter_rows = c.fetchall()
            
            for chapter_row in chapter_rows:
                chapter = self._chapter_row_to_chapter(chapter_row)
                manga.add_chapter(chapter)
            
            return manga
    
    def get_manga_by_title_no(self, title_no: str) -> Optional[Manga]:
        """Get a manga by its title number."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM manga WHERE title_no=?', (title_no,))
            row = c.fetchone()
            
            if not row:
                return None
            
            manga = self._row_to_manga(row)
            
            # Load chapters
            c.execute('SELECT * FROM chapters WHERE manga_id=?', (manga.id,))
            chapter_rows = c.fetchall()
            
            for chapter_row in chapter_rows:
                chapter = self._chapter_row_to_chapter(chapter_row)
                manga.add_chapter(chapter)
            
            return manga
    
    def get_all_manga(self) -> List[Manga]:
        """Get all manga from the database."""
        rows = db_utils.get_all_manga()
        manga_list = []
        
        for row in rows:
            manga = self._row_to_manga(row)
            manga_list.append(manga)
        
        return manga_list
    
    def search_manga_by_title(self, title: str) -> List[Manga]:
        """Search manga by title."""
        rows = db_utils.query_manga_by_title(title)
        return [self._row_to_manga(row) for row in rows]
    
    def search_manga_by_author(self, author: str) -> List[Manga]:
        """Search manga by author."""
        rows = db_utils.query_manga_by_author(author)
        return [self._row_to_manga(row) for row in rows]
    
    def search_manga_by_genre(self, genre: str) -> List[Manga]:
        """Search manga by genre."""
        rows = db_utils.query_manga_by_genre(genre)
        return [self._row_to_manga(row) for row in rows]
    
    def search_manga_by_min_chapters(self, min_chapters: int) -> List[Manga]:
        """Search manga with minimum number of chapters."""
        rows = db_utils.query_manga_by_min_chapters(min_chapters)
        return [self._row_to_manga(row) for row in rows]
    
    def search_manga_by_grade(self, min_grade: float) -> List[Manga]:
        """Search manga by minimum grade."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM manga WHERE grade >= ?', (min_grade,))
            rows = c.fetchall()
            return [self._row_to_manga(row) for row in rows]
    
    def get_top_rated_manga(self, limit: int = 10) -> List[Manga]:
        """Get top rated manga."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM manga WHERE grade IS NOT NULL ORDER BY grade DESC LIMIT ?', (limit,))
            rows = c.fetchall()
            return [self._row_to_manga(row) for row in rows]
    
    def get_most_viewed_manga(self, limit: int = 10) -> List[Manga]:
        """Get most viewed manga (requires parsing view counts)."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM manga WHERE views IS NOT NULL ORDER BY views DESC LIMIT ?', (limit,))
            rows = c.fetchall()
            return [self._row_to_manga(row) for row in rows]
    
    def get_recently_updated_manga(self, limit: int = 10) -> List[Manga]:
        """Get recently updated manga."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM manga WHERE last_updated IS NOT NULL ORDER BY last_updated DESC LIMIT ?', (limit,))
            rows = c.fetchall()
            return [self._row_to_manga(row) for row in rows]
    
    def get_manga_by_day(self, day: str) -> List[Manga]:
        """Get manga by publication day."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM manga WHERE day_info LIKE ?', (f'%{day}%',))
            rows = c.fetchall()
            return [self._row_to_manga(row) for row in rows]
    
    def get_genres(self) -> List[str]:
        """Get all unique genres."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT genre FROM manga WHERE genre IS NOT NULL')
            rows = c.fetchall()
            return [row[0] for row in rows if row[0]]
    
    def get_authors(self) -> List[str]:
        """Get all unique authors."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT author FROM manga WHERE author IS NOT NULL')
            rows = c.fetchall()
            # Split authors and clean up
            authors = set()
            for row in rows:
                if row[0]:
                    # Split by comma and clean each author
                    for author in row[0].split(','):
                        cleaned = author.strip()
                        if cleaned and cleaned != "Unknown":
                            authors.add(cleaned)
            return sorted(list(authors))
    
    def update_manga_download_status(self, manga_id: int, status: Dict[str, Any]) -> None:
        """Update download status for a manga."""
        # This could be extended to store JSON data in a separate column
        # For now, we can update the last_updated timestamp
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE manga SET last_updated=? WHERE id=?',
                (datetime.utcnow().isoformat(), manga_id)
            )
            conn.commit()
    
    def mark_chapter_downloaded(self, manga_id: int, episode_no: str, image_count: int = 0) -> None:
        """Mark a chapter as downloaded."""
        # Since the current schema doesn't have download tracking for chapters,
        # this is a placeholder for future enhancement
        pass
    
    def delete_manga(self, manga_id: int) -> bool:
        """Delete a manga and its chapters from the database."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                
                # Delete chapters first (foreign key constraint)
                c.execute('DELETE FROM chapters WHERE manga_id=?', (manga_id,))
                
                # Delete manga
                c.execute('DELETE FROM manga WHERE id=?', (manga_id,))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting manga {manga_id}: {e}")
            return False
    
    def delete_manga_by_series_name(self, series_name: str) -> bool:
        """Delete manga by series name."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                
                # Get manga ID first
                c.execute('SELECT id FROM manga WHERE series_name=?', (series_name,))
                row = c.fetchone()
                
                if row:
                    manga_id = row[0]
                    return self.delete_manga(manga_id)
                return False
        except Exception as e:
            print(f"Error deleting manga by series name {series_name}: {e}")
            return False
    
    def verify_and_cleanup_database(self) -> Dict[str, Any]:
        """Verify downloaded manga and remove database entries for deleted manga."""
        import os
        from pathlib import Path
        
        downloads_path = Config.get_downloads_dir()
        
        # Get all manga from database
        all_manga = self.get_all_manga()
        
        # Track verification results
        verified_count = 0
        deleted_count = 0
        missing_folders = []
        verified_manga = []
        
        print("Verifying manga folders against database...")
        
        for manga in all_manga:
            # Determine expected folder name
            expected_folder = None
            
            if manga.title_no and manga.series_name:
                expected_folder = f"webtoon_{manga.title_no}_{manga.series_name}"
            elif manga.series_name:
                expected_folder = f"webtoon_{manga.series_name}"
            
            folder_exists = False
            
            if expected_folder:
                folder_path = downloads_path / expected_folder
                
                # Check if folder exists and has episode directories
                if folder_path.exists() and folder_path.is_dir():
                    has_episodes = any(
                        (folder_path / sub).is_dir() and sub.lower().startswith("episode_")
                        for sub in os.listdir(folder_path)
                        if (folder_path / sub).is_dir()
                    )
                    if has_episodes:
                        folder_exists = True
                        verified_count += 1
                        verified_manga.append(manga)
            
            # If folder doesn't exist, mark for deletion
            if not folder_exists:
                print(f"Missing folder for manga: {manga.display_title or manga.series_name} (Expected: {expected_folder})")
                missing_folders.append({
                    'manga': manga,
                    'expected_folder': expected_folder
                })
        
        # Remove database entries for missing manga
        for item in missing_folders:
            manga = item['manga']
            if self.delete_manga(manga.id):
                deleted_count += 1
                print(f"Removed from database: {manga.display_title or manga.series_name}")
        
        return {
            'total_checked': len(all_manga),
            'verified_count': verified_count,
            'deleted_count': deleted_count,
            'verified_manga': verified_manga,
            'missing_folders': missing_folders
        }
    
    def sync_database_with_downloads(self) -> Dict[str, Any]:
        """Complete synchronization: scan new manga and cleanup deleted ones."""
        print("Starting complete database synchronization...")
        
        # First, verify and cleanup deleted manga
        cleanup_results = self.verify_and_cleanup_database()
        
        # Then, scan for new manga
        new_manga_count = self.scan_downloaded_manga("")
        
        # Get final statistics
        final_stats = self.get_download_statistics()
        
        return {
            'cleanup_results': cleanup_results,
            'new_manga_added': new_manga_count,
            'final_stats': final_stats
        }
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get download statistics."""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Total manga count
            c.execute('SELECT COUNT(*) FROM manga')
            total_manga = c.fetchone()[0]
            
            # Total chapters count
            c.execute('SELECT COUNT(*) FROM chapters')
            total_chapters = c.fetchone()[0]
            
            # Average chapters per manga
            avg_chapters = total_chapters / total_manga if total_manga > 0 else 0
            
            return {
                'total_manga': total_manga,
                'total_chapters': total_chapters,
                'average_chapters': round(avg_chapters, 2)
            }
    
    def _row_to_manga(self, row) -> Manga:
        """Convert database row to Manga object."""
        # Row format: (id, title_no, series_name, display_title, author, genre, 
        #              num_chapters, url, last_updated, grade, views, subscribers, day_info)
        
        last_updated = None
        if row[8]:  # last_updated column
            try:
                last_updated = datetime.fromisoformat(row[8])
            except (ValueError, TypeError):
                pass
        
        return Manga(
            id=row[0],
            title_no=row[1],
            series_name=row[2],
            display_title=row[3],
            author=row[4],
            genre=row[5],
            num_chapters=row[6],
            url=row[7],
            last_updated=last_updated,
            grade=row[9],
            views=row[10],
            subscribers=row[11],
            day_info=row[12]
        )
    
    def _chapter_row_to_chapter(self, row) -> Chapter:
        """Convert database row to Chapter object."""
        # Row format: (id, manga_id, episode_no, chapter_title, url)
        return Chapter(
            id=row[0],
            manga_id=row[1],
            episode_no=row[2],
            title=row[3],
            url=row[4]
        )
    
    def scan_downloaded_manga(self, downloads_dir: str) -> int:
        """Scan downloaded manga folders and update database."""
        import os
        import json
        from scraper.parsers import extract_webtoon_info, extract_chapter_info
        
        count = 0
        downloads_path = Config.get_downloads_dir()
        
        for folder_name in os.listdir(downloads_path):
            folder_path = downloads_path / folder_name
            
            if not folder_path.is_dir() or not folder_name.startswith("webtoon_"):
                continue
            
            # Check if folder has episode directories
            has_episodes = any(
                (folder_path / sub).is_dir() and sub.lower().startswith("episode_")
                for sub in os.listdir(folder_path)
            )
            
            if not has_episodes:
                continue
            
            # Try to get info from chapter_links.json
            chapter_json = folder_path / "chapter_links.json"
            manga_info_json = folder_path / "manga_info.json"
            
            title_no = series_name = display_title = url = None
            chapters = []
            
            if chapter_json.exists():
                try:
                    with open(chapter_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        title_no = data.get('title_no')
                        series_name = data.get('series_name')
                        url = data.get('chapters', [None])[0]
                        
                        for link in data.get('chapters', []):
                            ep, title = extract_chapter_info(link)
                            chapters.append(Chapter(
                                episode_no=ep,
                                title=title,
                                url=link
                            ))
                except Exception as e:
                    print(f"Error reading chapter_links.json: {e}")
            
            # Get display name from manga_info.json
            if manga_info_json.exists():
                try:
                    with open(manga_info_json, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                        display_title = info.get('display_name', folder_name)
                except Exception:
                    display_title = folder_name
            else:
                display_title = folder_name
            
            # Count episode folders if no chapter data
            if not chapters:
                episode_count = sum(
                    1 for sub in os.listdir(folder_path)
                    if (folder_path / sub).is_dir() and sub.lower().startswith("episode_")
                )
            else:
                episode_count = len(chapters)
            
            # Create manga object
            manga = Manga(
                title_no=title_no or "",
                series_name=series_name or folder_name,
                display_title=display_title,
                author="Unknown",
                genre="Unknown",
                num_chapters=episode_count,
                url=url or "",
                chapters=chapters
            )
            
            # Save to database
            self.save_manga(manga)
            count += 1
        
        return count 