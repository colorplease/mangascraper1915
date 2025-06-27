"""
Manga Controller - Business logic for manga collection management.

This controller handles all manga-related operations including:
- Loading downloaded manga
- Managing manga metadata
- Chapter management
- Banner image handling
- Comment operations

Following the MVC pattern, this controller acts as an intermediary between
the manga models and the UI views.
"""

import os
import json
import threading
from typing import List, Optional, Callable, Dict, Any
from pathlib import Path

from models.manga import Manga
from models.chapter import Chapter
from utils.config import Config
from utils.db_manager import DatabaseManager
from scraper.parsers import extract_chapter_info
from scraper.comment_analyzer import CommentAnalyzer


class MangaController:
    """Controller for manga collection operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the manga controller."""
        self.db_manager = db_manager
        self.comment_analyzer = CommentAnalyzer()
        self._current_manga: Optional[Manga] = None
        self._downloaded_manga: List[Manga] = []
        self._manga_display_names: Dict[str, str] = {}
        
        # Event callbacks
        self.on_manga_loaded: Optional[Callable[[List[Manga]], None]] = None
        self.on_manga_selected: Optional[Callable[[Optional[Manga]], None]] = None
        self.on_chapters_loaded: Optional[Callable[[List[Chapter]], None]] = None
        self.on_banner_loaded: Optional[Callable[[str, str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    @property
    def current_manga(self) -> Optional[Manga]:
        """Get the currently selected manga."""
        return self._current_manga
    
    @property
    def downloaded_manga(self) -> List[Manga]:
        """Get the list of downloaded manga."""
        return self._downloaded_manga.copy()
    
    def load_downloaded_manga(self) -> None:
        """Load all downloaded manga from the filesystem and database."""
        try:
            downloads_dir = Config.get_downloads_dir()
            if not downloads_dir.exists():
                downloads_dir.mkdir(parents=True, exist_ok=True)
                self._downloaded_manga = []
                if self.on_manga_loaded:
                    self.on_manga_loaded(self._downloaded_manga)
                return
            
            manga_list = []
            manga_folders = [d for d in downloads_dir.iterdir() 
                           if d.is_dir() and d.name.startswith('webtoon_')]
            
            for manga_folder in manga_folders:
                try:
                    manga = self._load_manga_from_folder(manga_folder)
                    if manga:
                        manga_list.append(manga)
                        # Store display name mapping
                        self._manga_display_names[manga.folder_name] = manga.display_title
                except Exception as e:
                    print(f"Error loading manga from {manga_folder}: {e}")
                    continue
            
            # Sort by display title
            manga_list.sort(key=lambda m: m.display_title.lower())
            self._downloaded_manga = manga_list
            
            # Notify view
            if self.on_manga_loaded:
                self.on_manga_loaded(self._downloaded_manga)
            
            print(f"Loaded {len(manga_list)} manga and notified UI")
                
        except Exception as e:
            error_msg = f"Failed to load downloaded manga: {e}"
            if self.on_error:
                self.on_error(error_msg)
    
    def _load_manga_from_folder(self, manga_folder: Path) -> Optional[Manga]:
        """Load manga information from a folder."""
        # Try to load from manga_info.json first
        info_file = manga_folder / "manga_info.json"
        if info_file.exists():
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return Manga.from_dict(data)
            except Exception as e:
                print(f"Error loading manga info from {info_file}: {e}")
        
        # Fallback: extract from folder name and database
        try:
            folder_name = manga_folder.name
            if folder_name.startswith('webtoon_'):
                parts = folder_name.split('_', 2)
                if len(parts) >= 3:
                    title_no = parts[1]
                    series_name = parts[2]
                    
                    # Check database first
                    db_manga = self.db_manager.get_manga_by_title_no(title_no)
                    if db_manga:
                        return db_manga
                    
                    # Create basic manga object
                    display_name = self._get_display_name_from_folder(manga_folder)
                    manga = Manga(
                        title_no=title_no,
                        series_name=series_name,
                        display_title=display_name
                    )
                    
                    # Load chapters from folder
                    self._load_chapters_from_folder(manga, manga_folder)
                    
                    return manga
        except Exception as e:
            print(f"Error creating manga from folder {manga_folder}: {e}")
        
        return None
    
    def _get_display_name_from_folder(self, manga_folder: Path) -> str:
        """Get display name for manga from folder."""
        # Try manga_info.json first
        info_file = manga_folder / "manga_info.json"
        if info_file.exists():
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'display_name' in data:
                        return data['display_name']
                    if 'display_title' in data:
                        return data['display_title']
            except Exception:
                pass
        
        # Fallback: derive from folder name
        folder_name = manga_folder.name
        if folder_name.startswith('webtoon_'):
            parts = folder_name.split('_', 2)
            if len(parts) >= 3:
                series_name = parts[2]
                return series_name.replace('-', ' ').title()
        
        return folder_name
    
    def _load_chapters_from_folder(self, manga: Manga, manga_folder: Path) -> None:
        """Load chapters for a manga from its folder."""
        # Load from chapter_links.json if available
        chapter_links_file = manga_folder / "chapter_links.json"
        if chapter_links_file.exists():
            try:
                with open(chapter_links_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    chapter_urls = data.get('chapters', [])
                    
                    for url in chapter_urls:
                        episode_no, title = extract_chapter_info(url)
                        chapter = Chapter(
                            episode_no=episode_no,
                            title=title,
                            url=url,
                            manga_id=manga.id
                        )
                        manga.add_chapter(chapter)
            except Exception as e:
                print(f"Error loading chapter links: {e}")
        
        # Get downloaded episodes from multiple sources
        downloaded_episodes = set()
        
        # Check downloaded.json file
        downloaded_file = manga_folder / "downloaded.json"
        if downloaded_file.exists():
            try:
                with open(downloaded_file, 'r', encoding='utf-8') as f:
                    downloaded_data = json.load(f)
                    if isinstance(downloaded_data, list):
                        # Convert to integers for consistency
                        for ep in downloaded_data:
                            try:
                                downloaded_episodes.add(int(ep))
                            except (ValueError, TypeError):
                                pass
                    elif isinstance(downloaded_data, dict):
                        # Handle different formats of downloaded.json
                        for ep in downloaded_data.keys():
                            try:
                                downloaded_episodes.add(int(ep))
                            except (ValueError, TypeError):
                                pass
            except Exception as e:
                print(f"Error reading downloaded.json: {e}")
        
        # Also check for actual episode folders (primary source of truth)
        episode_folders = [d for d in manga_folder.iterdir() 
                          if d.is_dir() and d.name.startswith('Episode_')]
        
        for folder in episode_folders:
            try:
                # Extract episode number from folder name: Episode_9_Episode 9 -> 9
                parts = folder.name.split('_')
                if len(parts) >= 2 and parts[1].isdigit():
                    episode_no = int(parts[1])
                    downloaded_episodes.add(episode_no)
            except Exception:
                continue
        
        print(f"Found downloaded episodes: {sorted(downloaded_episodes)}")
        
        # Mark downloaded chapters based on actual folder existence
        for chapter in manga.chapters:
            try:
                episode_num = int(chapter.episode_no)
                if episode_num in downloaded_episodes:
                    chapter.is_downloaded = True
                    # Set folder path for easy access
                    chapter.folder_path = str(manga_folder)
                    print(f"Marked Episode {episode_num} as downloaded")
                else:
                    chapter.is_downloaded = False
            except ValueError:
                # Handle non-numeric episode numbers
                chapter.is_downloaded = False
    
    def select_manga(self, manga: Optional[Manga]) -> None:
        """Select a manga and load its details."""
        self._current_manga = manga
        
        if manga:
            # Load detailed chapter information
            manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
            if manga_folder.exists():
                self._load_chapters_from_folder(manga, manga_folder)
            
            # Load banner images if available
            self._load_banner_images(manga)
        
        # Notify view
        if self.on_manga_selected:
            self.on_manga_selected(manga)
        
        if manga and self.on_chapters_loaded:
            self.on_chapters_loaded(manga.chapters)
    
    def _load_banner_images(self, manga: Manga) -> None:
        """Load banner images for a manga."""
        manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
        bg_path = manga_folder / "banner_bg.jpg"
        fg_path = manga_folder / "banner_fg.png"
        
        bg_exists = bg_path.exists()
        fg_exists = fg_path.exists()
        
        if bg_exists or fg_exists:
            if self.on_banner_loaded:
                self.on_banner_loaded(
                    str(bg_path) if bg_exists else None,
                    str(fg_path) if fg_exists else None
                )
    
    def get_chapter_comments(self, chapter: Chapter) -> Optional[str]:
        """Get comments for a specific chapter."""
        if not self._current_manga:
            return None
        
        try:
            manga_folder = Config.get_manga_folder(
                self._current_manga.title_no, 
                self._current_manga.series_name
            )
            
            # Find the actual episode folder (don't rely on generated folder_name)
            episode_folder = self._find_episode_folder(manga_folder, chapter.episode_no)
            
            if not episode_folder or not episode_folder.exists():
                print(f"Episode folder not found for Episode {chapter.episode_no}")
                return None
            
            # Look for comments file
            comments_file = episode_folder / f"comments_episode_{chapter.episode_no}.txt"
            
            if comments_file.exists():
                with open(comments_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"Comments file not found: {comments_file}")
                return None
                
        except Exception as e:
            print(f"Error loading comments for chapter {chapter.episode_no}: {e}")
        
        return None
    
    def get_chapter_comment_summary(self, chapter: Chapter) -> Optional[str]:
        """Get comment summary for a chapter."""
        comments_text = self.get_chapter_comments(chapter)
        if not comments_text:
            return None
        
        try:
            # Use comment analyzer to generate summary
            analysis = self.comment_analyzer.analyze_comments_text(comments_text)
            return analysis.get('summary', '')
        except Exception as e:
            print(f"Error analyzing comments: {e}")
            return comments_text[:200] + "..." if len(comments_text) > 200 else comments_text
    
    def open_chapter_folder(self, chapter: Chapter) -> bool:
        """Open chapter folder in file explorer."""
        if not self._current_manga:
            return False
        
        try:
            manga_folder = Config.get_manga_folder(
                self._current_manga.title_no, 
                self._current_manga.series_name
            )
            
            # Find the actual episode folder (don't rely on generated folder_name)
            episode_folder = self._find_episode_folder(manga_folder, chapter.episode_no)
            
            if not episode_folder or not episode_folder.exists():
                error_msg = f"Chapter folder not found for Episode {chapter.episode_no}"
                if self.on_error:
                    self.on_error(error_msg)
                return False
            
            # Open folder based on OS
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", str(episode_folder)])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(episode_folder)])
            else:  # Linux
                subprocess.run(["xdg-open", str(episode_folder)])
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to open chapter folder: {e}"
            if self.on_error:
                self.on_error(error_msg)
            return False
    
    def refresh_manga_data(self) -> None:
        """Refresh manga data from filesystem."""
        current_selection = self._current_manga
        self.load_downloaded_manga()
        
        # Restore selection if possible
        if current_selection:
            for manga in self._downloaded_manga:
                if (manga.title_no == current_selection.title_no and 
                    manga.series_name == current_selection.series_name):
                    self.select_manga(manga)
                    break
    
    def get_manga_by_folder_name(self, folder_name: str) -> Optional[Manga]:
        """Get manga by its folder name."""
        for manga in self._downloaded_manga:
            if manga.folder_name == folder_name:
                return manga
        return None
    
    def get_display_names_mapping(self) -> Dict[str, str]:
        """Get mapping of folder names to display names."""
        return self._manga_display_names.copy()
    
    def _find_episode_folder(self, manga_folder: Path, episode_no: str) -> Optional[Path]:
        """Find the actual episode folder for a given episode number."""
        try:
            # Convert episode_no to int for comparison
            target_episode = int(episode_no)
            
            # Look for folders that start with Episode_{episode_no}_
            for folder in manga_folder.iterdir():
                if folder.is_dir() and folder.name.startswith(f'Episode_{target_episode}_'):
                    return folder
            
            # Fallback: look for any folder containing the episode number
            for folder in manga_folder.iterdir():
                if folder.is_dir() and folder.name.startswith('Episode_'):
                    try:
                        # Extract episode number from folder name
                        parts = folder.name.split('_')
                        if len(parts) >= 2 and parts[1].isdigit():
                            folder_episode = int(parts[1])
                            if folder_episode == target_episode:
                                return folder
                    except (ValueError, IndexError):
                        continue
            
            return None
            
        except Exception as e:
            print(f"Error finding episode folder for {episode_no}: {e}")
            return None 