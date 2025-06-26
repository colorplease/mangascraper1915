"""
Download panel for fetching and downloading manga chapters.
"""

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading
import os
import time
from typing import Optional, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.manga import Manga
from models.chapter import Chapter
from scraper.webtoon_client import WebtoonClient
from scraper.parsers import create_manga_from_page, create_chapters_from_links, parse_chapter_links
from scraper.downloader import DownloadManager, DownloadQueue
from scraper.comment_analyzer import CommentAnalyzer
from utils.config import Config
from utils.db_manager import DatabaseManager


class AnimatedProgressBar(ttk.Progressbar):
    """Progress bar with percentage display."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._percent_label = tk.Label(master, text="", font=Config.UI_FONTS['DEFAULT'])
        self._percent_label.place(x=0, y=0)
        self._last_value = 0
        self._max = 100
        self._running = False

    def set_max(self, maxval):
        self._max = maxval
        self["maximum"] = maxval

    def set_value(self, value):
        self._last_value = value
        self["value"] = value
        self._update_label()

    def _update_label(self):
        percent = 0
        if self._max:
            percent = int((self._last_value / self._max) * 100)
        self._percent_label.config(text=f"{percent}%")

    def start_marquee(self):
        self["mode"] = "indeterminate"
        self.start(10)
        self._percent_label.config(text="...")
        self._running = True

    def stop_marquee(self):
        self.stop()
        self["mode"] = "determinate"
        self._running = False
        self._update_label()


class DownloadPanel(tk.Frame):
    """Panel for downloading manga chapters."""
    
    def __init__(self, parent, db_manager: DatabaseManager):
        super().__init__(parent, bg=Config.UI_COLORS['BLACK'])
        self.db_manager = db_manager
        self.current_manga: Optional[Manga] = None
        self.chapter_links: List[str] = []
        self.downloaded_chapters: set = set()
        self.output_dir = str(Config.get_downloads_dir())
        self._animated_status_running = False
        self.on_download_complete: Optional[Callable] = None
        
        # Create clients
        self.webtoon_client = WebtoonClient(use_selenium=True)
        self.download_manager = DownloadManager(
            use_selenium=True,
            extract_comments=Config.EXTRACT_COMMENTS_DEFAULT
        )
        self.comment_analyzer = CommentAnalyzer()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        # Header
        header = tk.Label(
            self,
            text="Fetch and Download Manga",
            font=Config.UI_FONTS['TITLE'],
            fg=Config.UI_COLORS['BLACK'],
            bg=Config.UI_COLORS['HIGHLIGHT'],
            pady=5
        )
        header.pack(fill=tk.X, pady=(0, 8))
        
        # URL input
        self.setup_url_input()
        
        # Chapter list
        self.setup_chapter_list()
        
        # Output directory
        self.setup_output_dir()
        
        # Download controls
        self.setup_download_controls()
        
        # Progress bar
        self.setup_progress()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status_label = tk.Label(
            self,
            textvariable=self.status_var,
            font=Config.UI_FONTS['SMALL'],
            fg=Config.UI_COLORS['WHITE'],
            bg=Config.UI_COLORS['BLACK']
        )
        status_label.pack(fill=tk.X, pady=(0, 5))
    
    def setup_url_input(self):
        """Set up URL input section."""
        url_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(url_frame, text="Webtoon URL:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).pack(side=tk.LEFT)
        
        self.url_entry = tk.Entry(url_frame, font=Config.UI_FONTS['DEFAULT'], width=50, 
                                 bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
        self.url_entry.pack(side=tk.LEFT, padx=5)
        
        fetch_btn = tk.Button(url_frame, text="Fetch Chapters", font=Config.UI_FONTS['DEFAULT'], 
                             bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                             command=self.fetch_chapters)
        fetch_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_chapter_list(self):
        """Set up chapter list display."""
        listbox_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        
        self.chapter_listbox = tk.Listbox(
            listbox_frame, selectmode=tk.MULTIPLE, font=Config.UI_FONTS['DEFAULT'], 
            bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'], 
            activestyle='none', selectbackground=Config.UI_COLORS['HIGHLIGHT'], 
            selectforeground=Config.UI_COLORS['BLACK'], height=15
        )
        self.chapter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.chapter_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chapter_listbox.config(yscrollcommand=scrollbar.set)
    
    def setup_output_dir(self):
        """Set up output directory selection."""
        dir_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        dir_frame.pack(fill=tk.X, padx=10, pady=5)
        
        choose_btn = tk.Button(dir_frame, text="Choose Output Folder", font=Config.UI_FONTS['DEFAULT'], 
                              bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                              command=self.choose_directory)
        choose_btn.pack(side=tk.LEFT)
        
        self.dir_label = tk.Label(dir_frame, text=self.output_dir, font=Config.UI_FONTS['SMALL'], 
                                 fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK'])
        self.dir_label.pack(side=tk.LEFT, padx=5)
    
    def setup_download_controls(self):
        """Set up download control buttons."""
        download_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        download_frame.pack(pady=10)
        
        download_btn = tk.Button(download_frame, text="Download Selected Chapters", 
                                font=Config.UI_FONTS['DEFAULT'], bg=Config.UI_COLORS['HIGHLIGHT'], 
                                fg=Config.UI_COLORS['BLACK'], command=self.download_selected)
        download_btn.pack(side=tk.LEFT, padx=5)
        
        resume_btn = tk.Button(download_frame, text="Resume Downloads", 
                              font=Config.UI_FONTS['DEFAULT'], bg="#ff9900", 
                              fg=Config.UI_COLORS['BLACK'], command=self.resume_downloads)
        resume_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_progress(self):
        """Set up progress bar."""
        self.progress_bar = AnimatedProgressBar(
            self, orient="horizontal", length=400, mode="determinate"
        )
        self.progress_bar.pack(pady=(0, 10))
    
    def fetch_chapters(self):
        """Fetch chapters from URL."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a Webtoon URL.")
            return
        
        self.status_var.set("Fetching chapters...")
        self.progress_bar.start_marquee()
        self._start_animated_status("Fetching chapters")
        self.chapter_listbox.delete(0, tk.END)
        
        threading.Thread(target=self._fetch_chapters_thread, args=(url,), daemon=True).start()
    
    def _fetch_chapters_thread(self, url):
        """Fetch chapters in background thread."""
        try:
            # Normalize URL
            normalized_url = self.webtoon_client.normalize_list_url(url)
            
            # Get page content
            soup = self.webtoon_client.get_page(normalized_url)
            if not soup:
                self.status_var.set("Failed to fetch page.")
                self.progress_bar.stop_marquee()
                self._stop_animated_status()
                return
            
            # Create manga object from page
            manga = create_manga_from_page(soup, normalized_url)
            
            # Get all chapter links
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
            
            self.current_manga = manga
            self.chapter_links = chapter_links
            
            # Save manga info
            manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
            manga_folder.mkdir(exist_ok=True)
            
            # Save manga info to JSON
            info_data = manga.to_dict()
            info_file = manga_folder / "manga_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                import json
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
                import json
                json.dump(chapter_data, f, indent=2)
            
            # Save to database
            self.db_manager.save_manga(manga)
            
            # Load downloaded chapters
            self._load_downloaded_chapters(str(manga_folder))
            
            # Update UI
            self.after(0, self._update_chapter_list)
            
            self.status_var.set(f"Found {len(chapter_links)} chapters.")
            self.progress_bar.stop_marquee()
            self._stop_animated_status()
            
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.progress_bar.stop_marquee()
            self._stop_animated_status()
    
    def _update_chapter_list(self):
        """Update the chapter list display."""
        if not self.current_manga:
            return
        
        self.chapter_listbox.delete(0, tk.END)
        for chapter in self.current_manga.chapters:
            display_text = f"Episode {chapter.episode_no}: {chapter.title}"
            if chapter.episode_no in self.downloaded_chapters:
                display_text += " (downloaded)"
            self.chapter_listbox.insert(tk.END, display_text)
    
    def _load_downloaded_chapters(self, manga_dir: str):
        """Load downloaded chapters from file."""
        self.downloaded_chapters = set()
        downloaded_file = os.path.join(manga_dir, "downloaded.json")
        
        if os.path.exists(downloaded_file):
            try:
                import json
                with open(downloaded_file, 'r', encoding='utf-8') as f:
                    self.downloaded_chapters = set(json.load(f))
            except Exception:
                pass
    
    def download_selected(self):
        """Download selected chapters."""
        if not self.current_manga:
            messagebox.showerror("Error", "Please fetch chapters first.")
            return
        
        selected_indices = self.chapter_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "No chapters selected.")
            return
        
        # Get selected chapters that aren't downloaded
        selected_chapters = []
        for i in selected_indices:
            chapter = self.current_manga.chapters[i]
            if chapter.episode_no not in self.downloaded_chapters:
                selected_chapters.append(chapter)
        
        if not selected_chapters:
            messagebox.showinfo("Info", "All selected chapters are already downloaded.")
            return
        
        manga_folder = Config.get_manga_folder(self.current_manga.title_no, self.current_manga.series_name)
        
        self.progress_bar.set_max(len(selected_chapters))
        self.progress_bar.set_value(0)
        self.progress_bar.stop_marquee()
        self._start_animated_status("Downloading chapters")
        
        threading.Thread(target=self._download_chapters_thread, 
                        args=(selected_chapters, str(manga_folder)), daemon=True).start()
    
    def _download_chapters_thread(self, chapters: List[Chapter], manga_dir: str):
        """Download chapters in background thread."""
        try:
            # Create download progress callback
            def progress_callback(progress):
                self.after(0, lambda: self.progress_bar.set_value(progress.completed_items))
            
            # Download chapters
            results = self.download_manager.download_manga_chapters(
                self.current_manga, chapters, manga_dir, progress_callback
            )
            
            # Update downloaded chapters list
            for chapter in chapters:
                if results.get(chapter.url, 0) > 0:
                    self.downloaded_chapters.add(chapter.episode_no)
            
            # Save downloaded chapters
            self._save_downloaded_chapters(manga_dir)
            
            # Check success
            all_successful = all(count > 0 for count in results.values())
            total_images = sum(results.values())
            
            if all_successful:
                self.status_var.set(f"Download complete! Downloaded {total_images} images across {len(chapters)} chapters.")
                messagebox.showinfo("Success", f"Downloaded {total_images} images to {manga_dir}")
            else:
                failed_count = len([c for c in results.values() if c == 0])
                self.status_var.set(f"Partial download. {failed_count} chapters failed.")
                messagebox.showwarning("Partial Success", 
                    f"Downloaded {total_images} images.\n{failed_count} chapters failed.")
            
            self.progress_bar.set_value(len(chapters))
            self._stop_animated_status()
            
            # Update UI
            self.after(0, self._update_chapter_list)
            
            # Notify completion
            if self.on_download_complete:
                self.on_download_complete()
                
        except Exception as e:
            self.status_var.set(f"Download error: {e}")
            self.progress_bar.stop_marquee()
            self._stop_animated_status()
    
    def _save_downloaded_chapters(self, manga_dir: str):
        """Save downloaded chapters to file."""
        downloaded_file = os.path.join(manga_dir, "downloaded.json")
        import json
        with open(downloaded_file, 'w', encoding='utf-8') as f:
            json.dump(sorted(self.downloaded_chapters), f)
    
    def resume_downloads(self):
        """Resume downloads from queue."""
        if not self.current_manga:
            messagebox.showinfo("Info", "Please fetch chapters for a manga first.")
            return
        
        manga_folder = Config.get_manga_folder(self.current_manga.title_no, self.current_manga.series_name)
        queue = DownloadQueue(str(manga_folder))
        
        if not queue.exists():
            messagebox.showinfo("Info", "No pending downloads found.")
            return
        
        # Load queue and filter downloaded chapters
        queued_urls = queue.load_queue()
        if not queued_urls:
            messagebox.showinfo("Info", "Download queue is empty.")
            return
        
        remaining_chapters = []
        for url in queued_urls:
            for chapter in self.current_manga.chapters:
                if chapter.url == url and chapter.episode_no not in self.downloaded_chapters:
                    remaining_chapters.append(chapter)
                    break
        
        if not remaining_chapters:
            queue.clear_queue()
            messagebox.showinfo("Info", "All queued chapters are already downloaded.")
            return
        
        # Confirm resume
        result = messagebox.askyesno("Resume Downloads", 
            f"Found {len(remaining_chapters)} chapters in download queue.\n\nResume downloading?")
        
        if result:
            self.progress_bar.set_max(len(remaining_chapters))
            self.progress_bar.set_value(0)
            self.progress_bar.stop_marquee()
            self._start_animated_status("Resuming downloads")
            
            threading.Thread(target=self._download_chapters_thread, 
                            args=(remaining_chapters, str(manga_folder)), daemon=True).start()
    
    def choose_directory(self):
        """Choose output directory."""
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            self.dir_label.config(text=directory)
    
    def on_manga_selected(self, manga: Manga):
        """Handle manga selection from other panels."""
        self.current_manga = manga
        if manga:
            manga_folder = Config.get_manga_folder(manga.title_no, manga.series_name)
            self._load_downloaded_chapters(str(manga_folder))
            self._update_chapter_list()
    
    def _start_animated_status(self, base_text: str):
        """Start animated status text."""
        self._animated_status_running = True
        
        def animate():
            dots = 0
            while self._animated_status_running:
                self.status_var.set(base_text + "." * (dots % 4))
                dots += 1
                time.sleep(0.5)
                
        threading.Thread(target=animate, daemon=True).start()
    
    def _stop_animated_status(self):
        """Stop animated status text."""
        self._animated_status_running = False
    
    def cleanup(self):
        """Clean up resources."""
        self._animated_status_running = False
        if hasattr(self, 'webtoon_client'):
            self.webtoon_client.close()
        if hasattr(self, 'download_manager'):
            self.download_manager.close() 