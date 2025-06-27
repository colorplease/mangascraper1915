"""
Download Controller - Business logic for manga downloading operations.

This controller handles all download-related operations including:
- Fetching chapter lists from URLs
- Managing download queues
- Coordinating parallel downloads
- Progress tracking
- Resume functionality

Following the MVC pattern, this controller separates download logic from UI.
"""

import os
import json
import threading
import time
from typing import List, Optional, Callable, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.manga import Manga
from models.chapter import Chapter
from utils.config import Config
from utils.db_manager import DatabaseManager
from scraper.webtoon_client import WebtoonClient
from scraper.parsers import create_manga_from_page, create_chapters_from_links, parse_chapter_links
from scraper.downloader import DownloadManager, DownloadQueue
from scraper.comment_analyzer import CommentAnalyzer


class DownloadProgress:
    """Progress tracking for downloads."""
    
    def __init__(self, total_chapters: int):
        self.total_chapters = total_chapters
        self.completed_chapters = 0
        self.current_chapter = ""
        self.total_images = 0
        self.completed_images = 0
        self.is_complete = False
        self.error_message = ""
    
    @property
    def chapter_progress_percent(self) -> int:
        """Get chapter progress as percentage."""
        if self.total_chapters == 0:
            return 0
        return int((self.completed_chapters / self.total_chapters) * 100)
    
    @property
    def image_progress_percent(self) -> int:
        """Get image progress as percentage."""
        if self.total_images == 0:
            return 0
        return int((self.completed_images / self.total_images) * 100)


class DownloadController:
    """Controller for download operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the download controller."""
        self.db_manager = db_manager
        self.webtoon_client = WebtoonClient(use_selenium=True)
        self.download_manager = DownloadManager(
            use_selenium=True,
            extract_comments=Config.EXTRACT_COMMENTS_DEFAULT
        )
        self.comment_analyzer = CommentAnalyzer()
        
        # Current state
        self._current_manga: Optional[Manga] = None
        self._chapter_links: List[str] = []
        self._downloaded_chapters: set = set()
        self._is_downloading = False
        
        # Event callbacks
        self.on_chapters_fetched: Optional[Callable[[Manga, List[Chapter]], None]] = None
        self.on_download_progress: Optional[Callable[[DownloadProgress], None]] = None
        self.on_download_complete: Optional[Callable[[bool, str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_status_update: Optional[Callable[[str], None]] = None
    
    @property
    def current_manga(self) -> Optional[Manga]:
        """Get current manga being processed."""
        return self._current_manga
    
    @property
    def is_downloading(self) -> bool:
        """Check if currently downloading."""
        return self._is_downloading
    
    def fetch_chapters(self, url: str) -> None:
        """Fetch chapters from a webtoon URL."""
        if self._is_downloading:
            if self.on_error:
                self.on_error("Cannot fetch chapters while downloading.")
            return
        
        self._update_status("Fetching chapters...")
        
        # Start fetch in background thread
        threading.Thread(
            target=self._fetch_chapters_thread,
            args=(url,),
            daemon=True
        ).start()
    
    def _fetch_chapters_thread(self, url: str) -> None:
        """Fetch chapters in background thread."""
        try:
            # Normalize URL
            normalized_url = self.webtoon_client.normalize_list_url(url)
            
            # Get page content
            soup = self.webtoon_client.get_page(normalized_url)
            if not soup:
                self._handle_error("Failed to fetch page content.")
                return
            
            # Create manga object from page
            manga = create_manga_from_page(soup, normalized_url)
            
            # Download banner images if available
            self._download_banner_images(manga)
            
            # Get all chapter links from paginated content
            all_pages = self.webtoon_client.get_paginated_content(
                normalized_url.split('?')[0], manga.title_no
            )
            
            chapter_links = []
            for page_soup in all_pages:
                links = parse_chapter_links(page_soup)
                chapter_links.extend(links)
            
            # Create chapter objects
            chapters = create_chapters_from_links(chapter_links)
            manga.chapters = chapters
            manga.num_chapters = len(chapters)
            
            # Save manga data
            self._save_manga_data(manga, chapter_links)
            
            # Load downloaded chapters
            manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
            self._load_downloaded_chapters(str(manga_folder))
            
            # Update chapter download status
            for chapter in chapters:
                if chapter.episode_no in self._downloaded_chapters:
                    chapter.check_download_exists(str(manga_folder))
            
            # Store current state
            self._current_manga = manga
            self._chapter_links = chapter_links
            
            # Notify view
            if self.on_chapters_fetched:
                self.on_chapters_fetched(manga, chapters)
            
            self._update_status(f"Found {len(chapter_links)} chapters.")
            
        except Exception as e:
            self._handle_error(f"Error fetching chapters: {e}")
    
    def _save_manga_data(self, manga: Manga, chapter_links: List[str]) -> None:
        """Save manga data to filesystem and database."""
        manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
        manga_folder.mkdir(parents=True, exist_ok=True)
        
        # Save manga info to JSON
        info_data = manga.to_dict()
        info_file = manga_folder / "manga_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, indent=2)
        
        # Save chapter links
        chapter_data = {
            "title_no": manga.title_no,
            "series_name": manga.series_name,
            "total_chapters": len(chapter_links),
            "chapters": chapter_links
        }
        chapter_file = manga_folder / "chapter_links.json"
        with open(chapter_file, 'w', encoding='utf-8') as f:
            json.dump(chapter_data, f, indent=2)
        
        # Save to database
        try:
            self.db_manager.save_manga(manga)
        except Exception as e:
            print(f"Warning: Failed to save manga to database: {e}")
    
    def download_chapters(self, chapters: List[Chapter]) -> None:
        """Download selected chapters."""
        if self._is_downloading:
            if self.on_error:
                self.on_error("Download already in progress.")
            return
        
        if not self._current_manga:
            if self.on_error:
                self.on_error("No manga selected for download.")
            return
        
        if not chapters:
            if self.on_error:
                self.on_error("No chapters selected.")
            return
        
        # Filter out already downloaded chapters
        chapters_to_download = [
            ch for ch in chapters 
            if ch.episode_no not in self._downloaded_chapters
        ]
        
        if not chapters_to_download:
            if self.on_error:
                self.on_error("All selected chapters are already downloaded.")
            return
        
        # Save download queue
        manga_folder = Config.get_manga_folder(
            self._current_manga.title_no, 
            self._current_manga.series_name
        )
        self._save_download_queue(str(manga_folder), chapters_to_download)
        
        # Start download
        self._is_downloading = True
        self._update_status("Starting download...")
        
        threading.Thread(
            target=self._download_chapters_thread,
            args=(chapters_to_download, str(manga_folder)),
            daemon=True
        ).start()
    
    def _download_chapters_thread(self, chapters: List[Chapter], manga_dir: str) -> None:
        """Download chapters in background thread."""
        progress = DownloadProgress(len(chapters))
        
        try:
            # Create progress callback - fix signature to match downloader expectations
            def progress_callback(downloaded_images, total_images, failed_images, current_chapter):
                progress.completed_images = downloaded_images
                progress.total_images = total_images
                progress.current_chapter = current_chapter
                
                if self.on_download_progress:
                    self.on_download_progress(progress)
            
            # Download chapters
            results = self.download_manager.download_manga_chapters(
                self._current_manga, chapters, manga_dir, progress_callback
            )
            
            # Update progress and downloaded chapters
            successful_downloads = 0
            total_images = 0
            
            for chapter in chapters:
                image_count = results.get(chapter.url, 0)
                total_images += image_count
                
                if image_count > 0:
                    self._downloaded_chapters.add(chapter.episode_no)
                    chapter.mark_downloaded(image_count, 
                        os.path.join(manga_dir, chapter.folder_name))
                    successful_downloads += 1
                    progress.completed_chapters += 1
                    
                    if self.on_download_progress:
                        self.on_download_progress(progress)
            
            # Save downloaded chapters
            self._save_downloaded_chapters(manga_dir)
            
            # Update chapter links with any new chapters
            self._update_chapter_links_file(manga_dir)
            
            # Check if all downloads were successful
            all_successful = successful_downloads == len(chapters)
            failed_count = len(chapters) - successful_downloads
            
            # Clear download queue if all successful
            if all_successful:
                self._clear_download_queue(manga_dir)
                message = f"Download complete! Downloaded {total_images} images across {len(chapters)} chapters."
            else:
                message = f"Partial download complete. {successful_downloads} chapters succeeded, {failed_count} failed. Total images: {total_images}"
            
            progress.is_complete = True
            progress.completed_chapters = successful_downloads
            
            if self.on_download_progress:
                self.on_download_progress(progress)
            
            if self.on_download_complete:
                self.on_download_complete(all_successful, message)
            
            self._update_status(message)
            
        except Exception as e:
            error_msg = f"Download error: {e}"
            progress.error_message = error_msg
            
            if self.on_download_progress:
                self.on_download_progress(progress)
            
            self._handle_error(error_msg)
        
        finally:
            self._is_downloading = False
    
    def resume_downloads(self) -> None:
        """Resume downloads from queue."""
        if not self._current_manga:
            if self.on_error:
                self.on_error("No manga selected.")
            return
        
        manga_folder = Config.get_manga_folder(
            self._current_manga.title_no, 
            self._current_manga.series_name
        )
        
        # Load download queue
        queue_data = self._load_download_queue(str(manga_folder))
        if not queue_data:
            if self.on_error:
                self.on_error("No pending downloads found.")
            return
        
        queued_urls = queue_data.get("chapters", [])
        if not queued_urls:
            if self.on_error:
                self.on_error("Download queue is empty.")
            return
        
        # Find chapters for queued URLs
        remaining_chapters = []
        for url in queued_urls:
            for chapter in self._current_manga.chapters:
                if (chapter.url == url and 
                    chapter.episode_no not in self._downloaded_chapters):
                    remaining_chapters.append(chapter)
                    break
        
        if not remaining_chapters:
            self._clear_download_queue(str(manga_folder))
            if self.on_error:
                self.on_error("All queued chapters are already downloaded.")
            return
        
        # Start download
        self.download_chapters(remaining_chapters)
    
    def _load_downloaded_chapters(self, manga_dir: str) -> None:
        """Load downloaded chapters list."""
        self._downloaded_chapters = set()
        downloaded_file = os.path.join(manga_dir, "downloaded.json")
        
        if os.path.exists(downloaded_file):
            try:
                with open(downloaded_file, 'r', encoding='utf-8') as f:
                    self._downloaded_chapters = set(json.load(f))
            except Exception as e:
                print(f"Error loading downloaded chapters: {e}")
    
    def _save_downloaded_chapters(self, manga_dir: str) -> None:
        """Save downloaded chapters list."""
        downloaded_file = os.path.join(manga_dir, "downloaded.json")
        with open(downloaded_file, 'w', encoding='utf-8') as f:
            json.dump(sorted(self._downloaded_chapters), f)
    
    def _save_download_queue(self, manga_dir: str, chapters: List[Chapter]) -> None:
        """Save download queue to file."""
        queue_file = os.path.join(manga_dir, "download_queue.json")
        queue_data = {
            "timestamp": time.time(),
            "total_chapters": len(chapters),
            "chapters": [ch.url for ch in chapters]
        }
        
        os.makedirs(manga_dir, exist_ok=True)
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump(queue_data, f, indent=2)
    
    def _load_download_queue(self, manga_dir: str) -> Optional[Dict[str, Any]]:
        """Load download queue from file."""
        queue_file = os.path.join(manga_dir, "download_queue.json")
        if not os.path.exists(queue_file):
            return None
        
        try:
            with open(queue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading download queue: {e}")
            return None
    
    def _clear_download_queue(self, manga_dir: str) -> None:
        """Clear download queue file."""
        queue_file = os.path.join(manga_dir, "download_queue.json")
        if os.path.exists(queue_file):
            try:
                os.remove(queue_file)
            except Exception as e:
                print(f"Error clearing download queue: {e}")
    
    def _update_chapter_links_file(self, manga_dir: str) -> None:
        """Update chapter links file with current chapters."""
        if not self._current_manga:
            return
        
        chapter_file = os.path.join(manga_dir, "chapter_links.json")
        chapter_data = {
            "title_no": self._current_manga.title_no,
            "series_name": self._current_manga.series_name,
            "total_chapters": len(self._chapter_links),
            "chapters": self._chapter_links
        }
        
        with open(chapter_file, 'w', encoding='utf-8') as f:
            json.dump(chapter_data, f, indent=2)
    
    def _update_status(self, message: str) -> None:
        """Update status message."""
        if self.on_status_update:
            self.on_status_update(message)
    
    def _handle_error(self, error_message: str) -> None:
        """Handle error with cleanup."""
        self._is_downloading = False
        if self.on_error:
            self.on_error(error_message)
    
    def _download_banner_images(self, manga: Manga) -> None:
        """Download banner images for a manga."""
        if not manga.banner_bg_url and not manga.banner_fg_url:
            print("No banner URLs found for manga")
            return
            
        try:
            manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
            manga_folder.mkdir(parents=True, exist_ok=True)
            
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://www.webtoons.com/'
            }
            
            # Download background banner
            if manga.banner_bg_url:
                try:
                    bg_path = manga_folder / "banner_bg.jpg"
                    print(f"Downloading background banner: {manga.banner_bg_url}")
                    
                    response = requests.get(manga.banner_bg_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    with open(bg_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ Background banner saved: {bg_path}")
                    
                except Exception as e:
                    print(f"❌ Failed to download background banner: {e}")
            
            # Download foreground banner
            if manga.banner_fg_url:
                try:
                    fg_path = manga_folder / "banner_fg.png"
                    print(f"Downloading foreground banner: {manga.banner_fg_url}")
                    
                    response = requests.get(manga.banner_fg_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    with open(fg_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ Foreground banner saved: {fg_path}")
                    
                except Exception as e:
                    print(f"❌ Failed to download foreground banner: {e}")
                    
        except Exception as e:
            print(f"Error in banner download process: {e}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._is_downloading = False
        if hasattr(self, 'webtoon_client'):
            self.webtoon_client.close()
        if hasattr(self, 'download_manager'):
            self.download_manager.close()
    
    def set_current_manga(self, manga: Optional[Manga]) -> None:
        """Set the current manga context."""
        self._current_manga = manga
        if manga:
            manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
            self._load_downloaded_chapters(str(manga_folder))
    
    def get_downloaded_chapters(self) -> set:
        """Get the set of downloaded chapter episode numbers."""
        return self._downloaded_chapters.copy() 