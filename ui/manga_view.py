"""
Manga viewing panel for displaying downloaded manga with banners, info, and chapters.

This module implements the manga viewing functionality from the original GUI
with banner image display, manga info, chapter lists, and comment viewing.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import os
import json
import re
import time
import subprocess
import platform
from typing import Optional, Callable, List, Dict, Any
from PIL import Image, ImageTk
import requests
from io import BytesIO

from models.manga import Manga
from models.chapter import Chapter
from utils.config import Config
from utils.db_manager import DatabaseManager
from scraper.parsers import extract_chapter_info


class BannerDisplay:
    """Handles banner image loading and display."""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.banner_image = None  # Keep reference to prevent garbage collection
        self.setup_banner_ui()
    
    def setup_banner_ui(self):
        """Set up the banner display UI components."""
        # Banner container with border
        self.banner_container = tk.Frame(
            self.parent_frame, 
            bg=Config.UI_COLORS['BLACK'], 
            bd=2, 
            relief=tk.GROOVE
        )
        self.banner_container.pack(fill=tk.X, padx=10, pady=5)
        
        # Banner display frame with fixed height
        self.banner_frame = tk.Frame(
            self.banner_container, 
            bg=Config.UI_COLORS['BLACK'], 
            height=Config.UI_CONFIG['banner_height']
        )
        self.banner_frame.pack(fill=tk.X, expand=True)
        self.banner_frame.pack_propagate(False)
        
        # Banner label for image display
        self.banner_label = tk.Label(self.banner_frame, bg=Config.UI_COLORS['BLACK'])
        self.banner_label.pack(fill=tk.BOTH, expand=True)
        
        # Banner controls
        self.banner_controls = tk.Frame(self.banner_container, bg=Config.UI_COLORS['BLACK'])
        self.banner_controls.pack(fill=tk.X, padx=5, pady=2)
        
        # Title label
        self.banner_title_label = tk.Label(
            self.banner_controls,
            text="",
            font=Config.UI_FONTS['TITLE'],
            fg=Config.UI_COLORS['HIGHLIGHT'],
            bg=Config.UI_COLORS['BLACK']
        )
        self.banner_title_label.pack(side=tk.LEFT, pady=2)
        
        # Refresh button
        refresh_btn = tk.Button(
            self.banner_controls,
            text="Refresh Banner",
            font=Config.UI_FONTS['TINY'],
            bg=Config.UI_COLORS['HIGHLIGHT'],
            fg=Config.UI_COLORS['BLACK'],
            command=self.refresh_banner
        )
        refresh_btn.pack(side=tk.RIGHT, padx=5, pady=2)
        
        self.current_manga = None
    
    def load_banner(self, manga: Optional[Manga]):
        """Load and display banner for manga."""
        self.current_manga = manga
        
        if not manga:
            self.clear_banner()
            return
        
        # Update title
        self.banner_title_label.config(text=manga.display_title)
        
        # Load banner images
        banner_bg_path = Config.get_manga_folder(manga.title_no, manga.series_name) / "banner_bg.jpg"
        banner_fg_path = Config.get_manga_folder(manga.title_no, manga.series_name) / "banner_fg.png"
        
        has_bg = banner_bg_path.exists()
        has_fg = banner_fg_path.exists()
        
        if has_bg or has_fg:
            self.display_layered_banner(
                str(banner_bg_path) if has_bg else None,
                str(banner_fg_path) if has_fg else None
            )
        elif manga.banner_bg_url or manga.banner_fg_url:
            # Download banners if URLs available
            threading.Thread(
                target=self._download_and_display_banner,
                args=(manga.banner_bg_url, manga.banner_fg_url, str(banner_bg_path), str(banner_fg_path)),
                daemon=True
            ).start()
        else:
            # Show placeholder
            self.banner_label.config(
                text=manga.display_title,
                font=Config.UI_FONTS['TITLE'],
                fg=Config.UI_COLORS['WHITE'],
                image=""
            )
    
    def clear_banner(self):
        """Clear the banner display."""
        self.banner_label.config(image="", text="")
        self.banner_title_label.config(text="")
        self.banner_image = None
    
    def display_layered_banner(self, bg_path: Optional[str], fg_path: Optional[str]):
        """Display layered banner with background and foreground."""
        try:
            frame_width = self.banner_frame.winfo_width()
            if frame_width < 100:
                frame_width = 800
            
            final_img = None
            
            # Load background
            if bg_path and os.path.exists(bg_path):
                bg_img = Image.open(bg_path)
                width, height = bg_img.size
                
                # Resize background to fit frame
                if width > height * 3:  # Very wide banner
                    new_width = frame_width - 40
                    new_height = min(Config.UI_CONFIG['banner_height'], int(new_width * 0.25))
                    bg_resized = bg_img.resize((new_width, int((height / width) * new_width)), Image.LANCZOS)
                    
                    if bg_resized.height > new_height:
                        top = (bg_resized.height - new_height) // 2
                        final_img = bg_resized.crop((0, top, new_width, top + new_height))
                    else:
                        final_img = bg_resized
                else:
                    new_height = Config.UI_CONFIG['banner_height']
                    new_width = int((width / height) * new_height)
                    if new_width > frame_width - 40:
                        new_width = frame_width - 40
                        new_height = int((height / width) * new_width)
                    final_img = bg_img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to RGBA for layering
                final_img = final_img.convert("RGBA")
            
            # Load and layer foreground
            if fg_path and os.path.exists(fg_path) and final_img:
                try:
                    fg_img = Image.open(fg_path).convert("RGBA")
                    fg_width, fg_height = fg_img.size
                    
                    # Resize foreground to match background height
                    fg_new_height = final_img.height
                    fg_new_width = int((fg_width / fg_height) * fg_new_height)
                    
                    if fg_new_width > final_img.width:
                        fg_new_width = final_img.width
                        fg_new_height = int((fg_height / fg_width) * fg_new_width)
                    
                    fg_resized = fg_img.resize((fg_new_width, fg_new_height), Image.LANCZOS)
                    
                    # Position foreground (right-aligned)
                    fg_x = final_img.width - fg_new_width
                    fg_y = 0
                    
                    final_img.paste(fg_resized, (fg_x, fg_y), fg_resized)
                except Exception as e:
                    print(f"Error processing foreground: {e}")
            elif fg_path and os.path.exists(fg_path) and not final_img:
                # Only foreground available
                final_img = Image.open(fg_path)
                final_img = self._resize_single_image(final_img, frame_width)
            elif bg_path and os.path.exists(bg_path) and not final_img:
                # Only background available  
                final_img = Image.open(bg_path)
                final_img = self._resize_single_image(final_img, frame_width)
            
            if final_img:
                # Convert to RGB for display
                display_img = Image.new("RGB", final_img.size, Config.UI_COLORS['BLACK'])
                if final_img.mode == "RGBA":
                    display_img.paste(final_img, mask=final_img.split()[3])
                else:
                    display_img = final_img
                
                photo = ImageTk.PhotoImage(display_img)
                self.banner_image = photo
                self.banner_label.config(image=photo, text="")
                
                # Update frame height
                self.banner_frame.config(height=final_img.height)
                
        except Exception as e:
            print(f"Error displaying banner: {e}")
            self.banner_label.config(text="Error displaying banner", font=Config.UI_FONTS['DEFAULT'], fg=Config.UI_COLORS['WHITE'])
    
    def _resize_single_image(self, img: Image.Image, frame_width: int) -> Image.Image:
        """Resize a single image to fit the banner frame."""
        width, height = img.size
        
        if width > height * 3:  # Wide banner
            new_width = frame_width - 40
            new_height = min(Config.UI_CONFIG['banner_height'], int(new_width * 0.25))
            resized = img.resize((new_width, int((height / width) * new_width)), Image.LANCZOS)
            
            if resized.height > new_height:
                top = (resized.height - new_height) // 2
                return resized.crop((0, top, new_width, top + new_height))
            return resized
        else:
            new_height = Config.UI_CONFIG['banner_height']
            new_width = int((width / height) * new_height)
            if new_width > frame_width - 40:
                new_width = frame_width - 40
                new_height = int((height / width) * new_width)
            return img.resize((new_width, new_height), Image.LANCZOS)
    
    def _download_and_display_banner(self, bg_url: Optional[str], fg_url: Optional[str], 
                                   bg_save_path: str, fg_save_path: str):
        """Download banner images and display them."""
        try:
            headers = Config.IMAGE_HEADERS.copy()
            
            bg_downloaded = False
            fg_downloaded = False
            
            if bg_url:
                response = requests.get(bg_url, headers=headers)
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(bg_save_path), exist_ok=True)
                    with open(bg_save_path, 'wb') as f:
                        f.write(response.content)
                    bg_downloaded = True
            
            if fg_url:
                response = requests.get(fg_url, headers=headers)
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(fg_save_path), exist_ok=True)
                    with open(fg_save_path, 'wb') as f:
                        f.write(response.content)
                    fg_downloaded = True
            
            # Update display in main thread
            if bg_downloaded or fg_downloaded:
                self.banner_frame.after(100, lambda: self.display_layered_banner(
                    bg_save_path if bg_downloaded else None,
                    fg_save_path if fg_downloaded else None
                ))
        except Exception as e:
            print(f"Error downloading banner: {e}")
    
    def refresh_banner(self):
        """Refresh the banner for current manga."""
        if self.current_manga:
            # Force re-download banners
            manga_folder = Config.get_manga_folder(self.current_manga.title_no, self.current_manga.series_name)
            bg_path = manga_folder / "banner_bg.jpg"
            fg_path = manga_folder / "banner_fg.png"
            
            # Remove existing files
            if bg_path.exists():
                bg_path.unlink()
            if fg_path.exists():
                fg_path.unlink()
            
            # Reload banner
            self.load_banner(self.current_manga)


class MangaViewPanel(tk.Frame):
    """Panel for viewing downloaded manga with banners, info, and chapters."""
    
    def __init__(self, parent, db_manager: DatabaseManager):
        super().__init__(parent, bg=Config.UI_COLORS['BLACK'])
        self.db_manager = db_manager
        self.current_manga: Optional[Manga] = None
        self.on_manga_selected: Optional[Callable] = None
        self.banner_image = None
        self.current_manga_folder = None
        self.downloaded_chapters = set()
        self.manga_display_names = {}
        self.chapter_links = []
        
        self.setup_ui()
        self.load_downloaded_manga()
        
    def setup_ui(self):
        """Set up the UI components."""
        # Header
        header = tk.Label(
            self,
            text="Your Downloaded Manga",
            font=("Helvetica", 15, "bold"),
            fg=Config.UI_COLORS['BLACK'],
            bg=Config.UI_COLORS['HIGHLIGHT'],
            pady=5
        )
        header.pack(fill=tk.X, pady=(0, 8))
        
        # Banner display
        self.setup_banner()
        
        # Manga info
        self.setup_manga_info()
        
        # Manga selection
        self.setup_manga_selection()
        
        # Chapter list
        self.setup_chapter_list()
        
        # Comment section
        self.setup_comment_section()
        
        # Action buttons
        self.setup_action_buttons()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        self.downloaded_status_var = tk.StringVar(value="Ready.")
        status_label = tk.Label(
            self,
            textvariable=self.downloaded_status_var,
            font=("Helvetica", 9),
            fg=Config.UI_COLORS['WHITE'],
            bg=Config.UI_COLORS['BLACK']
        )
        status_label.pack(fill=tk.X, pady=(0, 5))
    
    def setup_banner(self):
        """Set up banner display."""
        banner_container = tk.Frame(self, bg=Config.UI_COLORS['BLACK'], bd=2, relief=tk.GROOVE)
        banner_container.pack(fill=tk.X, padx=10, pady=5)
        
        self.banner_frame = tk.Frame(banner_container, bg=Config.UI_COLORS['BLACK'], height=180)
        self.banner_frame.pack(fill=tk.X, expand=True)
        self.banner_frame.pack_propagate(False)
        
        self.banner_label = tk.Label(self.banner_frame, bg=Config.UI_COLORS['BLACK'])
        self.banner_label.pack(fill=tk.BOTH, expand=True)
        
        banner_controls = tk.Frame(banner_container, bg=Config.UI_COLORS['BLACK'])
        banner_controls.pack(fill=tk.X, padx=5, pady=2)
        
        TITLE_FONT = ("Helvetica", 16, "bold")
        self.banner_title_label = tk.Label(
            banner_controls, text="", font=TITLE_FONT,
            fg=Config.UI_COLORS['HIGHLIGHT'], bg=Config.UI_COLORS['BLACK']
        )
        self.banner_title_label.pack(side=tk.LEFT, pady=2)
        
        # Refresh banner button
        refresh_banner_btn = tk.Button(
            banner_controls,
            text="Refresh Banner",
            font=("Helvetica", 8),
            bg=Config.UI_COLORS['HIGHLIGHT'],
            fg=Config.UI_COLORS['BLACK'],
            command=self.refresh_banner
        )
        refresh_banner_btn.pack(side=tk.RIGHT, padx=5, pady=2)
    
    def setup_manga_info(self):
        """Set up manga info display with clean, uniform layout."""
        FONT = ("Helvetica", 11, "bold")
        
        # Main info container
        info_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'], bd=2, relief=tk.GROOVE)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create a centered container for the info grid
        info_container = tk.Frame(info_frame, bg=Config.UI_COLORS['BLACK'])
        info_container.pack(expand=True, padx=10, pady=8)
        
        # Create info items as horizontal pairs
        info_items = [
            ("Author:", "manga_author_label"),
            ("Rating:", "manga_rating_label"),
            ("Downloaded:", "manga_downloaded_label"), 
            ("Total Chapters:", "manga_total_label")
        ]
        
        # First row: Author and Rating
        row1_frame = tk.Frame(info_container, bg=Config.UI_COLORS['BLACK'])
        row1_frame.pack(pady=2)
        
        self._create_info_pair(row1_frame, "Author:", "manga_author_label", FONT, side='left')
        self._create_info_pair(row1_frame, "Rating:", "manga_rating_label", FONT, side='right')
        
        # Second row: Downloaded and Total Chapters  
        row2_frame = tk.Frame(info_container, bg=Config.UI_COLORS['BLACK'])
        row2_frame.pack(pady=2)
        
        self._create_info_pair(row2_frame, "Downloaded:", "manga_downloaded_label", FONT, side='left')
        self._create_info_pair(row2_frame, "Total Chapters:", "manga_total_label", FONT, side='right')
    
    def _create_info_pair(self, parent, label_text, value_attr_name, font, side='left'):
        """Create a label-value pair with consistent spacing."""
        pair_frame = tk.Frame(parent, bg=Config.UI_COLORS['BLACK'])
        
        if side == 'left':
            pair_frame.pack(side=tk.LEFT, padx=(0, 20))  # Space between left and right pairs
        else:
            pair_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        # Label
        label = tk.Label(pair_frame, text=label_text, font=font,
                        fg=Config.UI_COLORS['HIGHLIGHT'], bg=Config.UI_COLORS['BLACK'])
        label.pack(side=tk.LEFT)
        
        # Value
        value_label = tk.Label(pair_frame, text="", font=font,
                              fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK'])
        value_label.pack(side=tk.LEFT, padx=(5, 0))  # Small space between label and value
        
        # Store reference to the value label
        setattr(self, value_attr_name, value_label)
    
    def setup_manga_selection(self):
        """Set up manga selection controls."""
        FONT = ("Helvetica", 11, "bold")
        
        selection_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        selection_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Label(selection_frame, text="Downloaded Manga:", font=FONT, 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).pack(side=tk.LEFT)
        
        self.manga_var = tk.StringVar()
        self.manga_menu = tk.OptionMenu(selection_frame, self.manga_var, "", command=self.on_manga_select)
        self.manga_menu.config(font=FONT, bg=Config.UI_COLORS['WHITE'], 
                              fg=Config.UI_COLORS['BLACK'], highlightbackground=Config.UI_COLORS['HIGHLIGHT'])
        self.manga_menu.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = tk.Button(selection_frame, text="Refresh List", font=FONT, 
                               bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                               command=self.load_downloaded_manga)
        refresh_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_chapter_list(self):
        """Set up chapter list."""
        FONT = ("Helvetica", 11, "bold")
        
        listbox_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        
        self.downloaded_listbox = tk.Listbox(
            listbox_frame, selectmode=tk.SINGLE, font=FONT, 
            bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'], 
            activestyle='none', selectbackground=Config.UI_COLORS['HIGHLIGHT'], 
            selectforeground=Config.UI_COLORS['BLACK'], height=15
        )
        self.downloaded_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.downloaded_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.downloaded_listbox.config(yscrollcommand=scrollbar.set)
        
        self.downloaded_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
    
    def setup_comment_section(self):
        """Set up comment display."""
        FONT = ("Helvetica", 11, "bold")
        
        comment_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'], bd=2, relief=tk.GROOVE)
        comment_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(comment_frame, text="Comment Summary:", font=FONT, 
                fg=Config.UI_COLORS['HIGHLIGHT'], bg=Config.UI_COLORS['BLACK']).pack(
                anchor=tk.W, padx=5, pady=(5, 0))
        
        self.comment_summary_text = tk.Text(comment_frame, height=4, font=("Helvetica", 9), 
                                   bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'], 
                                   wrap=tk.WORD)
        self.comment_summary_text.pack(fill=tk.X, padx=5, pady=5)
        self.comment_summary_text.config(state=tk.DISABLED)
    
    def setup_action_buttons(self):
        """Set up action buttons."""
        FONT = ("Helvetica", 11, "bold")
        
        button_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        open_btn = tk.Button(button_frame, text="Open Chapter Folder", font=FONT, 
                            bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                            command=self.open_selected_chapter_folder)
        open_btn.pack(side=tk.LEFT, padx=5)
        
        view_btn = tk.Button(button_frame, text="View Comments", font=FONT, 
                            bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                            command=self.view_chapter_comments)
        view_btn.pack(side=tk.LEFT, padx=5)
    
    def load_downloaded_manga(self):
        """Load downloaded manga from filesystem."""
        self.manga_var.set("")
        menu = self.manga_menu["menu"]
        menu.delete(0, "end")
        
        manga_folders = []
        self.manga_display_names = {}
        
        output_dir = Config.DOWNLOAD_FOLDER
        
        if os.path.exists(output_dir):
            for name in os.listdir(output_dir):
                path = os.path.join(output_dir, name)
                if os.path.isdir(path) and name.startswith("webtoon_"):
                    # Check if manga has downloaded episodes
                    has_episode = False
                    try:
                        for sub in os.listdir(path):
                            if os.path.isdir(os.path.join(path, sub)) and sub.lower().startswith("episode_"):
                                has_episode = True
                                break
                    except Exception:
                        continue
                    
                    if has_episode:
                        # Get display name from manga_info.json
                        info_json = os.path.join(path, "manga_info.json")
                        display_name = name
                        if os.path.exists(info_json):
                            try:
                                with open(info_json, "r", encoding="utf-8") as f:
                                    info = json.load(f)
                                    display_name = info.get("display_name", name)
                            except Exception:
                                pass
                        
                        manga_folders.append((name, display_name))
                        self.manga_display_names[name] = display_name
        
        # Update dropdown menu
        for folder, display_name in manga_folders:
            menu.add_command(label=display_name, command=lambda f=folder: self.on_manga_select(f))
        
        if manga_folders:
            self.manga_var.set(manga_folders[0][0])
            self.on_manga_select(manga_folders[0][0])
        else:
            self.downloaded_listbox.delete(0, tk.END)
            self.manga_var.set("")
            self.clear_banner()
            self.clear_manga_info()
    
    def on_manga_select(self, folder):
        """Handle manga selection."""
        self.manga_var.set(folder)
        self.current_manga_folder = os.path.join(Config.DOWNLOAD_FOLDER, folder)
        self.chapter_links = []
        self.downloaded_chapters = set()
        self.downloaded_listbox.delete(0, tk.END)
        
        # Load banner image
        self.load_banner_image(folder)
        
        # Update banner title
        display_name = self.manga_display_names.get(folder, folder)
        self.banner_title_label.config(text=display_name)
        
        # Load manga info
        self.load_manga_info(folder)
        
        # Load chapter links
        chapter_json = os.path.join(self.current_manga_folder, "chapter_links.json")
        if os.path.exists(chapter_json):
            try:
                with open(chapter_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.chapter_links = data.get("chapters", [])
            except Exception:
                self.chapter_links = []
        else:
            self.chapter_links = self.reconstruct_chapter_links_from_folders(self.current_manga_folder)
        
        # Load downloaded chapters
        self.load_downloaded_chapters()
        
        # Populate chapter list
        for link in self.chapter_links:
            ep, title = extract_chapter_info(link)
            display = f"Episode {ep}: {title}"
            if ep in self.downloaded_chapters:
                display += " (downloaded)"
            self.downloaded_listbox.insert(tk.END, display)
        
        # Update status
        display_name = self.manga_display_names.get(folder, folder)
        self.downloaded_status_var.set(f"Loaded {len(self.chapter_links)} chapters from {display_name}.")
        
        # Update chapter counts
        downloaded_count = len(self.downloaded_chapters)
        total_count = len(self.chapter_links)
        self.manga_downloaded_label.config(text=f"{downloaded_count} chapters")
        self.manga_total_label.config(text=f"{total_count} chapters")
    
    def load_banner_image(self, folder):
        """Load and display banner image for selected manga."""
        # Clear current banner
        self.banner_label.config(image="", text="")
        self.banner_image = None
        
        if not folder:
            return
        
        manga_dir = os.path.join(Config.DOWNLOAD_FOLDER, folder)
        
        # Check for local banner files
        banner_bg_file = os.path.join(manga_dir, "banner_bg.jpg")
        banner_fg_file = os.path.join(manga_dir, "banner_fg.png")
        
        has_bg = os.path.exists(banner_bg_file)
        has_fg = os.path.exists(banner_fg_file)
        
        # If local files exist, display them
        if has_bg or has_fg:
            self.display_layered_banner(
                banner_bg_file if has_bg else None,
                banner_fg_file if has_fg else None
            )
        else:
            # Check for banner URLs in manga_info.json
            info_json = os.path.join(manga_dir, "manga_info.json")
            if os.path.exists(info_json):
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        banner_bg_url = info.get("banner_bg_url")
                        banner_fg_url = info.get("banner_fg_url")
                        
                        if banner_bg_url or banner_fg_url:
                            self.downloaded_status_var.set("Downloading banner images...")
                            threading.Thread(
                                target=self._download_and_display_banner,
                                args=(banner_bg_url, banner_fg_url, banner_bg_file, banner_fg_file),
                                daemon=True
                            ).start()
                            return
                except Exception:
                    pass
            
            # Show placeholder text
            display_name = self.manga_display_names.get(folder, folder)
            self.banner_label.config(
                text=display_name,
                font=("Helvetica", 16, "bold"),
                fg=Config.UI_COLORS['WHITE'],
                image=""
            )
    
    def display_layered_banner(self, bg_path, fg_path):
        """Display layered banner with background and foreground images."""
        try:
            frame_width = self.winfo_width()
            if frame_width < 100:
                frame_width = 800
            
            final_img = None
            
            # Load background image
            if bg_path and os.path.exists(bg_path):
                bg_img = Image.open(bg_path)
                width, height = bg_img.size
                
                # Resize background to fit frame
                if width > height * 3:  # Very wide banner
                    new_width = frame_width - 40
                    new_height = min(180, int(new_width * 0.25))
                    bg_resized = bg_img.resize((new_width, int((height / width) * new_width)), Image.LANCZOS)
                    
                    if bg_resized.height > new_height:
                        top = (bg_resized.height - new_height) // 2
                        final_img = bg_resized.crop((0, top, new_width, top + new_height))
                    else:
                        final_img = bg_resized
                else:
                    new_height = 180
                    new_width = int((width / height) * new_height)
                    if new_width > frame_width - 40:
                        new_width = frame_width - 40
                        new_height = int((height / width) * new_width)
                    final_img = bg_img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to RGBA for layering
                if final_img.mode != "RGBA":
                    final_img = final_img.convert("RGBA")
            
            # Load and layer foreground image
            if fg_path and os.path.exists(fg_path) and final_img:
                try:
                    fg_img = Image.open(fg_path)
                    if fg_img.mode != "RGBA":
                        fg_img = fg_img.convert("RGBA")
                    
                    fg_width, fg_height = fg_img.size
                    fg_new_height = final_img.height
                    fg_new_width = int((fg_width / fg_height) * fg_new_height)
                    
                    if fg_new_width > final_img.width:
                        fg_new_width = final_img.width
                        fg_new_height = int((fg_height / fg_width) * fg_new_width)
                    
                    fg_resized = fg_img.resize((fg_new_width, fg_new_height), Image.LANCZOS)
                    
                    # Position foreground (right-aligned)
                    fg_x = final_img.width - fg_new_width
                    fg_y = 0
                    
                    final_img.paste(fg_resized, (fg_x, fg_y), fg_resized)
                except Exception as e:
                    print(f"Error processing foreground image: {e}")
            elif fg_path and os.path.exists(fg_path) and not final_img:
                # Only foreground available
                final_img = Image.open(fg_path)
                final_img = self._resize_single_image(final_img, frame_width)
            elif bg_path and os.path.exists(bg_path) and not final_img:
                # Only background available
                final_img = Image.open(bg_path)
                final_img = self._resize_single_image(final_img, frame_width)
            
            if final_img:
                # Convert to RGB for display
                final_img_rgb = Image.new("RGB", final_img.size, (0, 0, 0))
                if final_img.mode == "RGBA":
                    final_img_rgb.paste(final_img, mask=final_img.split()[3])
                else:
                    final_img_rgb = final_img
                
                photo = ImageTk.PhotoImage(final_img_rgb)
                self.banner_image = photo  # Keep reference to prevent garbage collection
                
                self.banner_label.config(image=photo, text="")
                self.banner_frame.config(height=final_img.height)
                
                # Update frame height after a delay
                self.after(100, lambda: self.banner_frame.config(height=final_img.height))
                self.after(100, lambda: self.banner_frame.pack_propagate(True))
                self.after(200, lambda: self.banner_frame.pack_propagate(False))
            else:
                self.banner_label.config(text="Banner images not found", font=("Helvetica", 11, "bold"), fg=Config.UI_COLORS['WHITE'])
        
        except Exception as e:
            print(f"Error displaying layered banner: {e}")
            self.banner_label.config(text=f"Error displaying banner: {str(e)}", font=("Helvetica", 11, "bold"), fg=Config.UI_COLORS['WHITE'])
    
    def _resize_single_image(self, img, frame_width):
        """Resize a single image to fit banner frame."""
        width, height = img.size
        
        if width > height * 3:  # Wide banner
            new_width = frame_width - 40
            new_height = min(180, int(new_width * 0.25))
            resized = img.resize((new_width, int((height / width) * new_width)), Image.LANCZOS)
            
            if resized.height > new_height:
                top = (resized.height - new_height) // 2
                return resized.crop((0, top, new_width, top + new_height))
            return resized
        else:
            new_height = 180
            new_width = int((width / height) * new_height)
            if new_width > frame_width - 40:
                new_width = frame_width - 40
                new_height = int((height / width) * new_width)
            return img.resize((new_width, new_height), Image.LANCZOS)
    
    def _download_and_display_banner(self, bg_url, fg_url, bg_save_path, fg_save_path):
        """Download banner images and display them."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://www.webtoons.com/'
            }
            
            bg_downloaded = False
            fg_downloaded = False
            
            if bg_url:
                response = requests.get(bg_url, headers=headers)
                if response.status_code == 200:
                    with open(bg_save_path, 'wb') as f:
                        f.write(response.content)
                    bg_downloaded = True
                    print(f"Downloaded background banner: {bg_url}")
            
            if fg_url:
                response = requests.get(fg_url, headers=headers)
                if response.status_code == 200:
                    with open(fg_save_path, 'wb') as f:
                        f.write(response.content)
                    fg_downloaded = True
                    print(f"Downloaded foreground banner: {fg_url}")
            
            # Display banner in main thread
            if bg_downloaded or fg_downloaded:
                self.after(100, lambda: self.display_layered_banner(
                    bg_save_path if bg_downloaded else None,
                    fg_save_path if fg_downloaded else None
                ))
            
        except Exception as e:
            print(f"Error downloading banner: {e}")
            self.after(100, lambda: self.banner_label.config(text="Error loading banner", font=("Helvetica", 11, "bold"), fg=Config.UI_COLORS['WHITE']))
        finally:
            self.after(100, lambda: self.downloaded_status_var.set("Ready."))
    
    def load_manga_info(self, folder):
        """Load and display manga metadata."""
        if not folder:
            self.clear_manga_info()
            return
        
        # Default values
        author = "Unknown"
        rating = "N/A"
        
        # Try to get info from database first
        match = re.match(r"webtoon_(\d+)_(.*)", folder)
        if match:
            title_no = match.group(1)
            
            try:
                # Query database for manga info
                manga = self.db_manager.get_manga_by_title_no(title_no)
                if manga:
                    if manga.author:
                        author = self._clean_text(manga.author)
                    if manga.grade:
                        rating = f"{manga.grade:.1f}/5.0"
            except Exception as e:
                print(f"Error querying database: {e}")
        
        # If database query failed, try manga_info.json
        if author == "Unknown" or rating == "N/A":
            manga_dir = os.path.join(Config.DOWNLOAD_FOLDER, folder)
            info_json = os.path.join(manga_dir, "manga_info.json")
            if os.path.exists(info_json):
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        if "author" in info and info["author"]:
                            author = self._clean_text(info["author"])
                        if "grade" in info and info["grade"]:
                            rating = f"{float(info['grade']):.1f}/5.0"
                except Exception as e:
                    print(f"Error loading manga info: {e}")
        
        # Update info labels
        self.manga_author_label.config(text=author)
        self.manga_rating_label.config(text=rating)
    
    def _clean_text(self, text):
        """Clean text by removing extra whitespace, newlines, and tabs."""
        if not text:
            return text
        
        # Replace all whitespace (including \n, \t) with single spaces
        import re
        cleaned = re.sub(r'\s+', ' ', str(text).strip())
        
        # Clean up common author separators and extra commas
        cleaned = re.sub(r',\s*,', ',', cleaned)  # Remove double commas
        cleaned = re.sub(r'^\s*,\s*|\s*,\s*$', '', cleaned)  # Remove leading/trailing commas
        
        return cleaned
    
    def clear_manga_info(self):
        """Clear manga info display."""
        self.manga_author_label.config(text="")
        self.manga_rating_label.config(text="")
        self.manga_downloaded_label.config(text="")
        self.manga_total_label.config(text="")
    
    def clear_banner(self):
        """Clear banner display."""
        self.banner_label.config(image="", text="")
        self.banner_title_label.config(text="")
        self.banner_image = None
    
    def load_downloaded_chapters(self):
        """Load set of downloaded chapter numbers."""
        self.downloaded_chapters = set()
        if self.current_manga_folder:
            record = os.path.join(self.current_manga_folder, "downloaded.json")
            if os.path.exists(record):
                try:
                    with open(record, "r", encoding="utf-8") as f:
                        self.downloaded_chapters = set(json.load(f))
                except Exception:
                    self.downloaded_chapters = set()
    
    def reconstruct_chapter_links_from_folders(self, manga_dir):
        """Reconstruct chapter links from existing episode folders."""
        links = []
        if not os.path.exists(manga_dir):
            return links
        
        for name in os.listdir(manga_dir):
            if name.lower().startswith("episode_") and os.path.isdir(os.path.join(manga_dir, name)):
                m = re.match(r"Episode_(\d+)_([\w\- ]+)", name, re.IGNORECASE)
                if m:
                    ep = m.group(1)
                    title = m.group(2).replace('_', ' ')
                    links.append(f"episode-dummy-url?episode_no={ep}")
        return links
    
    def on_chapter_select(self, event):
        """Display comment summary when chapter is selected."""
        selection = self.downloaded_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if idx >= len(self.chapter_links):
            return
        
        link = self.chapter_links[idx]
        ep, title = extract_chapter_info(link)
        
        # Find episode folder
        found_folder = None
        for name in os.listdir(self.current_manga_folder):
            if name.lower().startswith(f"episode_{ep}") and os.path.isdir(os.path.join(self.current_manga_folder, name)):
                found_folder = os.path.join(self.current_manga_folder, name)
                break
        
        if not found_folder:
            self.update_comment_summary("No comment summary available for this chapter.")
            return
        
        # Check for comments file
        comments_file = os.path.join(found_folder, f"comments_episode_{ep}.txt")
        if not os.path.exists(comments_file):
            self.update_comment_summary("No comments have been downloaded for this chapter.")
            return
        
        # Extract summary from comments file
        try:
            with open(comments_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                summary = ""
                in_summary = False
                for line in lines:
                    if line.strip() == "SUMMARY:":
                        in_summary = True
                        continue
                    elif in_summary and line.strip() == "--------------------------------------------------":
                        break
                    elif in_summary:
                        summary += line
                
                if summary:
                    self.update_comment_summary(summary.strip())
                else:
                    self.update_comment_summary("Comment summary not found in file.")
        except Exception as e:
            self.update_comment_summary(f"Error reading comment file: {e}")
    
    def update_comment_summary(self, text):
        """Update comment summary text widget."""
        self.comment_summary_text.config(state=tk.NORMAL)
        self.comment_summary_text.delete(1.0, tk.END)
        self.comment_summary_text.insert(tk.END, text)
        self.comment_summary_text.config(state=tk.DISABLED)
    
    def open_selected_chapter_folder(self):
        """Open selected chapter folder in file explorer."""
        selection = self.downloaded_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No chapter selected.")
            return
        
        idx = selection[0]
        if idx >= len(self.chapter_links):
            messagebox.showerror("Error", "Invalid chapter selection.")
            return
        
        link = self.chapter_links[idx]
        ep, title = extract_chapter_info(link)
        
        # Find episode folder
        found_folder = None
        for name in os.listdir(self.current_manga_folder):
            if name.lower().startswith(f"episode_{ep}") and os.path.isdir(os.path.join(self.current_manga_folder, name)):
                found_folder = os.path.join(self.current_manga_folder, name)
                break
        
        if not found_folder:
            messagebox.showerror("Error", f"Could not find folder for Episode {ep}.")
            return
        
        # Open folder in system file explorer
        try:
            if platform.system() == "Windows":
                os.startfile(found_folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", found_folder])
            else:
                subprocess.Popen(["xdg-open", found_folder])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")
    
    def view_chapter_comments(self):
        """Open comments file for selected chapter."""
        selection = self.downloaded_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No chapter selected.")
            return
        
        idx = selection[0]
        if idx >= len(self.chapter_links):
            messagebox.showerror("Error", "Invalid chapter selection.")
            return
        
        link = self.chapter_links[idx]
        ep, title = extract_chapter_info(link)
        
        # Find episode folder
        found_folder = None
        for name in os.listdir(self.current_manga_folder):
            if name.lower().startswith(f"episode_{ep}") and os.path.isdir(os.path.join(self.current_manga_folder, name)):
                found_folder = os.path.join(self.current_manga_folder, name)
                break
        
        if not found_folder:
            messagebox.showerror("Error", f"Could not find folder for Episode {ep}.")
            return
        
        # Check for comments file
        comments_file = os.path.join(found_folder, f"comments_episode_{ep}.txt")
        if not os.path.exists(comments_file):
            messagebox.showerror("Error", f"No comments file found for Episode {ep}.")
            return
        
        # Open comments file in default text editor
        try:
            if platform.system() == "Windows":
                os.startfile(comments_file)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", comments_file])
            else:
                subprocess.Popen(["xdg-open", comments_file])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open comments file: {e}")
    
    def refresh_banner(self):
        """Refresh banner for current manga."""
        current_folder = self.manga_var.get()
        if not current_folder:
            messagebox.showinfo("Info", "Please select a manga first.")
            return
        
        # Remove existing banner files to force re-download
        manga_dir = os.path.join(Config.DOWNLOAD_FOLDER, current_folder)
        banner_bg_file = os.path.join(manga_dir, "banner_bg.jpg")
        banner_fg_file = os.path.join(manga_dir, "banner_fg.png")
        
        try:
            if os.path.exists(banner_bg_file):
                os.remove(banner_bg_file)
            if os.path.exists(banner_fg_file):
                os.remove(banner_fg_file)
        except Exception as e:
            print(f"Error removing banner files: {e}")
        
        # Reload banner
        self.load_banner_image(current_folder) 