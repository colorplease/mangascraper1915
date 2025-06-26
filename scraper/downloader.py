"""
Download management for webtoon images and chapters.

This module handles image downloading, download queues, progress tracking,
and parallel download coordination.
"""

import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from models.manga import Manga
from models.chapter import Chapter
from scraper.webtoon_client import WebtoonClient
from scraper.parsers import parse_chapter_images, extract_chapter_info
from scraper.comment_analyzer import extract_comments, save_comments_to_file
from utils.config import Config


class DownloadProgress:
    """Progress tracking for downloads."""
    
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.completed_items = 0
        self.failed_items = 0
        self.start_time = time.time()
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable) -> None:
        """Add a progress callback function."""
        self.callbacks.append(callback)
    
    def update(self, completed: int = None, failed: int = None) -> None:
        """Update progress counters."""
        if completed is not None:
            self.completed_items = completed
        if failed is not None:
            self.failed_items = failed
        
        # Call all callbacks
        for callback in self.callbacks:
            try:
                callback(self)
            except Exception as e:
                print(f"Error in progress callback: {e}")
    
    def increment_completed(self) -> None:
        """Increment completed count."""
        self.completed_items += 1
        self.update()
    
    def increment_failed(self) -> None:
        """Increment failed count."""
        self.failed_items += 1
        self.update()
    
    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if download is complete."""
        return (self.completed_items + self.failed_items) >= self.total_items
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time


class ImageDownloader:
    """Downloads individual images."""
    
    def __init__(self, client: WebtoonClient):
        self.client = client
        self.extract_comments = True  # Default to extracting comments
    
    def download_image(self, url: str, filepath: str, chapter_url: str = None) -> bool:
        """Download a single image."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Set up headers with proper referer
            headers = Config.IMAGE_HEADERS.copy()
            if chapter_url:
                headers['Referer'] = chapter_url
            
            return self.client.download_image(url, filepath, headers)
            
        except Exception as e:
            print(f"Error downloading image {url}: {e}")
            return False
    
    def download_chapter_images(self, chapter: Chapter, output_dir: str, 
                              progress: DownloadProgress = None,
                              max_workers: int = None) -> int:
        """Download all images for a chapter."""
        if max_workers is None:
            max_workers = Config.DEFAULT_MAX_WORKERS
        
        # Get chapter folder and ensure it exists
        chapter_folder = Config.get_chapter_folder(
            Path(output_dir), 
            chapter.episode_no, 
            chapter.title
        )
        
        # Create the chapter directory early to ensure it exists for comments
        os.makedirs(chapter_folder, exist_ok=True)
        
        # Get chapter page content with enhanced method for comments
        if self.client.use_selenium and self.extract_comments:
            print(f"Using Selenium to get chapter page with dynamic comments: {chapter.url}")
            soup = self.client.get_page(chapter.url)
        elif self.client.use_selenium:
            print(f"Using Selenium to get chapter page: {chapter.url}")
            soup = self.client.get_page(chapter.url)
        else:
            print(f"Using requests to get chapter page: {chapter.url}")
            if self.extract_comments:
                print("⚠ Warning: Comment extraction may be limited without Selenium")
            soup = self.client.get_page(chapter.url)
        
        if not soup:
            print(f"Failed to get chapter page: {chapter.url}")
            return 0
        
        # Extract image URLs
        image_urls = parse_chapter_images(soup, chapter.url)
        if not image_urls:
            print(f"No images found for chapter {chapter.episode_no}")
            return 0
        
        print(f"Found {len(image_urls)} images for chapter {chapter.episode_no}")
        
        # Extract and save comments if enabled
        if self.extract_comments:
            try:
                print(f"Extracting and summarizing comments for chapter {chapter.episode_no}...")
                comments = extract_comments(soup, chapter.url)
                if comments:
                    save_comments_to_file(comments, str(chapter_folder), chapter.episode_no)
                    print(f"✓ Successfully saved {len(comments)} comments with summary for chapter {chapter.episode_no}")
                else:
                    print(f"⚠ No comments found for chapter {chapter.episode_no}")
            except Exception as e:
                print(f"✗ Error extracting comments for chapter {chapter.episode_no}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"Comment extraction disabled for chapter {chapter.episode_no}")
        
        # Download images in parallel
        successful_downloads = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit download tasks
            futures = []
            for i, image_url in enumerate(image_urls):
                # Determine file extension
                ext = self._get_image_extension(image_url)
                filename = f"{i+1:03d}{ext}"
                filepath = str(chapter_folder / filename)
                
                future = executor.submit(
                    self.download_image, 
                    image_url, 
                    filepath, 
                    chapter.url
                )
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                if future.result():
                    successful_downloads += 1
                
                if progress:
                    progress.increment_completed()
        
        # Update chapter with download info
        if successful_downloads > 0:
            chapter.mark_downloaded(successful_downloads, str(chapter_folder))
        
        print(f"Downloaded {successful_downloads}/{len(image_urls)} images for chapter {chapter.episode_no}")
        return successful_downloads
    
    def _get_image_extension(self, url: str) -> str:
        """Get appropriate file extension from image URL."""
        url_lower = url.lower()
        if 'jpg' in url_lower or 'jpeg' in url_lower:
            return '.jpg'
        elif 'png' in url_lower:
            return '.png'
        elif 'webp' in url_lower:
            return '.webp'
        elif 'gif' in url_lower:
            return '.gif'
        else:
            return '.jpg'  # Default


class DownloadQueue:
    """Manages download queues for resuming failed downloads."""
    
    def __init__(self, manga_folder: str):
        self.manga_folder = manga_folder
        self.queue_file = os.path.join(manga_folder, "download_queue.json")
    
    def save_queue(self, chapters: List[Chapter]) -> None:
        """Save chapters to download queue."""
        os.makedirs(self.manga_folder, exist_ok=True)
        
        queue_data = {
            "timestamp": time.time(),
            "total_chapters": len(chapters),
            "chapters": [chapter.url for chapter in chapters]
        }
        
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            json.dump(queue_data, f, indent=2)
        
        print(f"Saved download queue with {len(chapters)} chapters")
    
    def load_queue(self) -> Optional[List[str]]:
        """Load chapters from download queue."""
        if not os.path.exists(self.queue_file):
            return None
        
        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('chapters', [])
        except Exception as e:
            print(f"Error loading download queue: {e}")
            return None
    
    def clear_queue(self) -> None:
        """Clear the download queue."""
        if os.path.exists(self.queue_file):
            try:
                os.remove(self.queue_file)
                print("Download queue cleared")
            except Exception as e:
                print(f"Error clearing download queue: {e}")
    
    def exists(self) -> bool:
        """Check if download queue exists."""
        return os.path.exists(self.queue_file)


class DownloadManager:
    """High-level download manager for coordinating manga downloads."""
    
    def __init__(self, use_selenium: bool = True, max_workers: int = None, extract_comments: bool = True):
        self.client = WebtoonClient(use_selenium=use_selenium)
        self.image_downloader = ImageDownloader(self.client)
        self.max_workers = max_workers or Config.DEFAULT_MAX_WORKERS
        self.chapter_workers = Config.DEFAULT_CHAPTER_WORKERS
        self.extract_comments = extract_comments
        
        # Pass comment extraction setting to image downloader
        self.image_downloader.extract_comments = extract_comments
    
    def download_manga_chapters(self, manga: Manga, chapters: List[Chapter],
                              output_dir: str = None,
                              progress_callback: Callable = None) -> Dict[str, int]:
        """Download multiple chapters for a manga."""
        if output_dir is None:
            output_dir = str(Config.get_manga_folder(manga.title_no, manga.series_name))
        
        # Set up download queue
        queue = DownloadQueue(output_dir)
        queue.save_queue(chapters)
        
        # Set up progress tracking
        progress = DownloadProgress(len(chapters))
        if progress_callback:
            progress.add_callback(progress_callback)
        
        results = {}
        
        # Download chapters in parallel
        with ThreadPoolExecutor(max_workers=self.chapter_workers) as executor:
            # Submit chapter download tasks
            future_to_chapter = {}
            for chapter in chapters:
                future = executor.submit(
                    self.image_downloader.download_chapter_images,
                    chapter,
                    output_dir,
                    None,  # Individual chapter progress not tracked here
                    self.max_workers
                )
                future_to_chapter[future] = chapter
            
            # Wait for completion
            for future in as_completed(future_to_chapter):
                chapter = future_to_chapter[future]
                try:
                    image_count = future.result()
                    results[chapter.url] = image_count
                    
                    if image_count > 0:
                        progress.increment_completed()
                    else:
                        progress.increment_failed()
                        
                except Exception as e:
                    print(f"Error downloading chapter {chapter.episode_no}: {e}")
                    results[chapter.url] = 0
                    progress.increment_failed()
        
        # Check if all downloads were successful
        all_successful = all(count > 0 for count in results.values())
        
        if all_successful:
            queue.clear_queue()
            print(f"All {len(chapters)} chapters downloaded successfully!")
        else:
            failed_count = sum(1 for count in results.values() if count == 0)
            print(f"Download partially complete. {failed_count} chapters failed.")
        
        return results
    
    def resume_downloads(self, manga: Manga, output_dir: str = None) -> Dict[str, int]:
        """Resume downloads from queue."""
        if output_dir is None:
            output_dir = str(Config.get_manga_folder(manga.title_no, manga.series_name))
        
        queue = DownloadQueue(output_dir)
        queued_urls = queue.load_queue()
        
        if not queued_urls:
            print("No download queue found")
            return {}
        
        # Convert URLs back to Chapter objects
        chapters = []
        for url in queued_urls:
            # Find matching chapter in manga
            chapter = None
            for ch in manga.chapters:
                if ch.url == url:
                    chapter = ch
                    break
            
            if chapter:
                # Check if already downloaded
                chapter_folder = Config.get_chapter_folder(
                    Path(output_dir), 
                    chapter.episode_no, 
                    chapter.title
                )
                if not chapter.check_download_exists(str(chapter_folder.parent)):
                    chapters.append(chapter)
        
        if not chapters:
            queue.clear_queue()
            print("All queued chapters already downloaded")
            return {}
        
        print(f"Resuming download of {len(chapters)} chapters")
        return self.download_manga_chapters(manga, chapters, output_dir)
    
    def get_download_status(self, manga: Manga, output_dir: str = None) -> Dict[str, Any]:
        """Get download status for a manga."""
        if output_dir is None:
            output_dir = str(Config.get_manga_folder(manga.title_no, manga.series_name))
        
        total_chapters = len(manga.chapters)
        downloaded_chapters = 0
        
        # Check each chapter
        for chapter in manga.chapters:
            chapter_folder = Config.get_chapter_folder(
                Path(output_dir), 
                chapter.episode_no, 
                chapter.title
            )
            if chapter.check_download_exists(str(chapter_folder.parent)):
                downloaded_chapters += 1
        
        # Check if download queue exists
        queue = DownloadQueue(output_dir)
        has_pending = queue.exists()
        
        return {
            'total_chapters': total_chapters,
            'downloaded_chapters': downloaded_chapters,
            'pending_downloads': has_pending,
            'completion_percentage': (downloaded_chapters / total_chapters * 100) if total_chapters > 0 else 0
        }
    
    def close(self) -> None:
        """Close the download manager."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 