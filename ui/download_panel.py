"""
Download panel for fetching and downloading manga chapters.
"""

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Optional, List

from models.manga import Manga
from models.chapter import Chapter
from utils.config import Config


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
    
    def __init__(self, parent, download_controller):
        super().__init__(parent, bg=Config.UI_COLORS['BLACK'])
        
        # Validate controller type during initialization
        expected_methods = ['fetch_chapters', 'resume_downloads', 'download_chapters', 'get_downloaded_chapters']
        controller_type = type(download_controller)
        
        # Check if this is the expected controller type
        missing_methods = [method for method in expected_methods if not hasattr(download_controller, method)]
        if missing_methods:
            print(f"ERROR: Controller {controller_type} is missing methods: {missing_methods}")
            print("Expected a DownloadController but received a different object!")
            print(f"Available methods: {[attr for attr in dir(download_controller) if not attr.startswith('_')]}")
            
            # This is a critical error - wrong controller type passed
            raise TypeError(f"Expected DownloadController, got {controller_type}. Missing methods: {missing_methods}")
        
        self.download_controller = download_controller
        self.current_manga: Optional[Manga] = None
        self.chapter_links: List[str] = []
        self.downloaded_chapters: set = set()
        self.output_dir = str(Config.get_downloads_dir())
        self._animated_status_running = False
        
        # Set up controller event handlers
        self.setup_controller_events()
        
        self.setup_ui()
    
    def setup_controller_events(self):
        """Set up event handlers for the controller."""
        # Validate controller type before setting event handlers
        if not hasattr(self.download_controller, 'on_chapters_fetched'):
            print(f"WARNING: Controller {type(self.download_controller)} doesn't have expected event attributes!")
            print("This suggests the wrong object was passed as download_controller")
            return
            
        try:
            self.download_controller.on_chapters_fetched = self.on_chapters_fetched
            self.download_controller.on_download_progress = self.on_download_progress
            self.download_controller.on_download_complete = self.on_download_complete_internal
            self.download_controller.on_error = self.on_controller_error
            self.download_controller.on_status_update = self.on_status_update
        except Exception as e:
            print(f"Error setting up controller events: {e}")
            print(f"Controller type: {type(self.download_controller)}")
            import traceback
            traceback.print_exc()
        
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
                              fg=Config.UI_COLORS['BLACK'], command=self._safe_resume_downloads)
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
        
        self.progress_bar.start_marquee()
        self.chapter_listbox.delete(0, tk.END)
        
        # Delegate to controller
        self._safe_fetch_chapters(url)
    
    def _safe_fetch_chapters(self, url: str):
        """Safely call fetch_chapters with validation."""
        try:
            # Debug: Check what type of object we have
            controller_type = type(self.download_controller)
            print(f"DEBUG: download_controller type is {controller_type}")
            
            # Check if it has the method
            if not hasattr(self.download_controller, 'fetch_chapters'):
                print(f"ERROR: {controller_type} does not have fetch_chapters method!")
                print("Available methods:", [attr for attr in dir(self.download_controller) if not attr.startswith('_')])
                return
            
            # Call the method
            self.download_controller.fetch_chapters(url)
            
        except Exception as e:
            print(f"Error in _safe_fetch_chapters: {e}")
            import traceback
            traceback.print_exc()
    
    def download_selected(self):
        """Download selected chapters."""
        if not self.current_manga:
            messagebox.showerror("Error", "Please fetch chapters first.")
            return
        
        selected_indices = self.chapter_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "No chapters selected.")
            return
        
        # Get selected chapters
        selected_chapters = []
        for i in selected_indices:
            if i < len(self.current_manga.chapters):
                selected_chapters.append(self.current_manga.chapters[i])
        
        if not selected_chapters:
            messagebox.showinfo("Info", "No valid chapters selected.")
            return
        
        self.progress_bar.set_max(len(selected_chapters))
        self.progress_bar.set_value(0)
        self.progress_bar.stop_marquee()
        
        # Delegate to controller
        self.download_controller.download_chapters(selected_chapters)
    

    
    def choose_directory(self):
        """Choose output directory."""
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            self.dir_label.config(text=directory)
    
    # Controller event handlers
    def on_chapters_fetched(self, manga: Manga, chapters: List[Chapter]) -> None:
        """Handle chapters fetched from controller."""
        self.current_manga = manga
        self.chapter_links = [ch.url for ch in chapters]
        self.downloaded_chapters = self.download_controller.get_downloaded_chapters()
        
        # Update UI in main thread
        self.after(0, self._update_chapter_list)
        self.progress_bar.stop_marquee()
        
    def on_download_progress(self, progress) -> None:
        """Handle download progress from controller."""
        # Update progress bar
        if progress.total_chapters > 0:
            self.progress_bar.set_max(progress.total_chapters)
            self.progress_bar.set_value(progress.completed_chapters)
        
        # Update status
        if progress.current_chapter:
            self.status_var.set(f"Downloading: {progress.current_chapter}")
        
    def on_download_complete_internal(self, success: bool, message: str) -> None:
        """Handle download completion from controller."""
        self.progress_bar.stop_marquee()
        self.status_var.set(message)
        
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showwarning("Partial Success", message)
        
        # Refresh chapter list
        self.downloaded_chapters = self.download_controller.get_downloaded_chapters()
        self._update_chapter_list()
        
    def on_controller_error(self, error_message: str) -> None:
        """Handle errors from controller."""
        self.progress_bar.stop_marquee()
        self.status_var.set(f"Error: {error_message}")
        messagebox.showerror("Error", error_message)
        
    def on_status_update(self, message: str) -> None:
        """Handle status updates from controller."""
        self.status_var.set(message)
    

    
    def cleanup(self):
        """Clean up resources."""
        # Controller cleanup is handled by the main app
        pass 

    def _update_chapter_list(self):
        """Update the chapter list display with download status."""
        if not self.current_manga or not self.current_manga.chapters:
            return
            
        # Clear current list
        self.chapter_listbox.delete(0, tk.END)
        
        # Add chapters with download status
        for i, chapter in enumerate(self.current_manga.chapters):
            display_text = f"Episode {chapter.episode_no}: {chapter.title}"
            
            # Check if chapter is downloaded
            if chapter.episode_no in self.downloaded_chapters:
                display_text += " ✓ Downloaded"
            
            self.chapter_listbox.insert(tk.END, display_text)
            
            # Color downloaded chapters differently
            if chapter.episode_no in self.downloaded_chapters:
                self.chapter_listbox.itemconfig(i, {'fg': 'green'})

    def _safe_resume_downloads(self):
        """Safely call resume_downloads with validation."""
        try:
            # Debug: Check what type of object we have
            controller_type = type(self.download_controller)
            print(f"DEBUG: download_controller type is {controller_type}")
            
            # Check if it has the method
            if not hasattr(self.download_controller, 'resume_downloads'):
                print(f"ERROR: {controller_type} does not have resume_downloads method!")
                print("Available methods:", [attr for attr in dir(self.download_controller) if not attr.startswith('_')])
                return
            
            # Call the method
            self.download_controller.resume_downloads()
            
        except Exception as e:
            print(f"Error in _safe_resume_downloads: {e}")
            import traceback
            traceback.print_exc() 