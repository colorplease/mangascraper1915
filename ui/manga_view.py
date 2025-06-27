"""
Manga View Panel - UI component for viewing downloaded manga.

This panel displays downloaded manga with banners, chapter lists, and metadata.
It uses the MangaController for all business logic operations.
"""

import os
import tkinter as tk
import platform
import subprocess
from tkinter import messagebox, ttk
from typing import List, Optional
from PIL import Image, ImageTk
import requests

from models.manga import Manga
from models.chapter import Chapter
from utils.config import Config
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
    
    def __init__(self, parent, manga_controller):
        super().__init__(parent, bg=Config.UI_COLORS['BLACK'])
        
        # Validate controller type during initialization
        expected_methods = ['load_downloaded_manga', 'select_manga', 'get_manga_by_folder_name', 'refresh_manga_data']
        controller_type = type(manga_controller)
        
        # Check if this is the expected controller type
        missing_methods = [method for method in expected_methods if not hasattr(manga_controller, method)]
        if missing_methods:
            print(f"ERROR: Controller {controller_type} is missing methods: {missing_methods}")
            print("Expected a MangaController but received a different object!")
            print(f"Available methods: {[attr for attr in dir(manga_controller) if not attr.startswith('_')]}")
            
            # This is a critical error - wrong controller type passed
            raise TypeError(f"Expected MangaController, got {controller_type}")
        
        self.manga_controller = manga_controller
        self.current_manga: Optional[Manga] = None
        self.current_chapters: List[Chapter] = []  # Initialize chapter list
        self.banner_image = None
        
        # Set up controller event handlers
        self.setup_controller_events()
        
        self.setup_ui()
    
    def setup_controller_events(self):
        """Set up event handlers for the controller."""
        # Connect controller callbacks to UI update methods
        self.manga_controller.on_manga_loaded = self.on_manga_loaded
        self.manga_controller.on_manga_selected = self.on_manga_selected_internal
        self.manga_controller.on_chapters_loaded = self.on_chapters_loaded
        self.manga_controller.on_banner_loaded = self.on_banner_loaded
        self.manga_controller.on_error = self.on_controller_error
        
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
    
    # Controller event handlers
    def on_manga_loaded(self, manga_list: List[Manga]) -> None:
        """Handle manga list loaded from controller."""
        # Update dropdown menu
        menu = self.manga_menu['menu']
        menu.delete(0, 'end')
        
        if not manga_list:
            self.manga_var.set("")
            self.clear_manga_display()
            return
        
        # Add manga options
        for manga in manga_list:
            menu.add_command(
                label=manga.display_title,
                command=lambda m=manga: self.on_manga_select_from_menu(m)
            )
        
        # Set first manga as default if none selected
        if manga_list and not self.current_manga:
            self.manga_var.set(manga_list[0].display_title)
            self.manga_controller.select_manga(manga_list[0])
    
    def on_manga_selected_internal(self, manga: Optional[Manga]) -> None:
        """Handle manga selection from controller."""
        self.current_manga = manga
        if manga:
            self.manga_var.set(manga.display_title)
            self.update_manga_info(manga)
        else:
            self.clear_manga_display()
    
    def on_chapters_loaded(self, chapters: List[Chapter]) -> None:
        """Handle chapters loaded from controller."""
        self.downloaded_listbox.delete(0, tk.END)
        
        # Store chapters for later use (folder opening, etc.)
        self.current_chapters = chapters
        
        for chapter in chapters:
            display_text = f"Episode {chapter.episode_no}: {chapter.title}"
            if chapter.is_downloaded:
                display_text += " ✓ Downloaded"
            self.downloaded_listbox.insert(tk.END, display_text)
    
    def on_banner_loaded(self, bg_path: Optional[str], fg_path: Optional[str]) -> None:
        """Handle banner loaded from controller."""
        if bg_path or fg_path:
            self.display_layered_banner(bg_path, fg_path)
        else:
            # No banner files exist - show helpful message
            if self.current_manga:
                self.banner_label.config(
                    text=f"No banner available for {self.current_manga.display_title}\nBanners are downloaded when fetching new manga", 
                    font=("Helvetica", 10, "bold"), 
                    fg=Config.UI_COLORS['WHITE'],
                    justify=tk.CENTER
                )
            else:
                self.banner_label.config(
                    text="No banner available", 
                    font=("Helvetica", 11, "bold"), 
                    fg=Config.UI_COLORS['WHITE']
                )
    
    def on_controller_error(self, error_message: str) -> None:
        """Handle errors from controller."""
        self.downloaded_status_var.set(f"Error: {error_message}")
    
    # UI event handlers
    def on_manga_select_from_menu(self, manga: Manga) -> None:
        """Handle manga selection from dropdown menu."""
        self.manga_controller.select_manga(manga)
    
    def on_manga_select_legacy(self, folder_name: str) -> None:
        """Handle manga selection (legacy method for compatibility)."""
        manga = self.manga_controller.get_manga_by_folder_name(folder_name)
        if manga:
            self.manga_controller.select_manga(manga)
    
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
                               command=self._safe_load_downloaded_manga)
        refresh_btn.pack(side=tk.LEFT, padx=5)
    
    def _safe_load_downloaded_manga(self):
        """Safely call load_downloaded_manga with validation."""
        try:
            # Debug: Check what type of object we have
            controller_type = type(self.manga_controller)
            print(f"DEBUG: manga_controller type is {controller_type}")
            
            # Check if it has the method
            if not hasattr(self.manga_controller, 'load_downloaded_manga'):
                print(f"ERROR: {controller_type} does not have load_downloaded_manga method!")
                print("Available methods:", [attr for attr in dir(self.manga_controller) if not attr.startswith('_')])
                return
            
            # Call the method
            self.manga_controller.load_downloaded_manga()
            
        except Exception as e:
            print(f"Error in _safe_load_downloaded_manga: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    def on_manga_select(self, selected_display_title):
        """Handle manga selection from dropdown menu."""
        if not selected_display_title:
            return
            
        # Find manga by display title and delegate to controller
        for manga in self.manga_controller.downloaded_manga:
            if manga.display_title == selected_display_title:
                self.manga_controller.select_manga(manga)
                return
        
        # If not found, clear display
        self.clear_manga_display()
    
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
    
    def on_chapter_select(self, event):
        """Handle chapter selection to show comment summary."""
        selection = self.downloaded_listbox.curselection()
        if not selection or not self.current_manga:
            self.update_comment_summary("")
            return
        
        try:
            chapter_index = selection[0]
            chapter = self.current_manga.chapters[chapter_index]
            
            # Get comment summary from controller
            summary = self.manga_controller.get_chapter_comment_summary(chapter)
            if summary:
                self.update_comment_summary(summary)
            else:
                self.update_comment_summary("No comments available for this chapter.")
                
        except (IndexError, AttributeError):
            self.update_comment_summary("Error loading chapter comments.")
    
    def update_comment_summary(self, text):
        """Update comment summary text widget."""
        self.comment_summary_text.config(state=tk.NORMAL)
        self.comment_summary_text.delete(1.0, tk.END)
        self.comment_summary_text.insert(tk.END, text)
        self.comment_summary_text.config(state=tk.DISABLED)
    
    def update_manga_info(self, manga: Manga) -> None:
        """Update manga info display."""
        # Update manga info labels
        self.manga_author_label.config(text=manga.author or "Unknown")
        self.manga_rating_label.config(text=f"{manga.grade:.1f}" if manga.grade else "N/A")
        self.manga_downloaded_label.config(text=str(manga.downloaded_chapters_count))
        self.manga_total_label.config(text=str(manga.num_chapters))
        
        # Update banner title
        self.banner_title_label.config(text=manga.display_title)
    
    def clear_manga_display(self) -> None:
        """Clear all manga display elements."""
        self.manga_author_label.config(text="")
        self.manga_rating_label.config(text="")
        self.manga_downloaded_label.config(text="")
        self.manga_total_label.config(text="")
        self.banner_title_label.config(text="")
        self.downloaded_listbox.delete(0, tk.END)
        self.update_comment_summary("")
        self.clear_banner()
    
    def open_selected_chapter_folder(self):
        """Open selected chapter folder in file explorer."""
        selection = self.downloaded_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No chapter selected.")
            return
        
        if not self.current_manga:
            messagebox.showerror("Error", "No manga selected.")
            return
            
        if not hasattr(self, 'current_chapters') or not self.current_chapters:
            messagebox.showerror("Error", "No chapters loaded.")
            return
        
        try:
            chapter_index = selection[0]
            if chapter_index >= len(self.current_chapters):
                messagebox.showerror("Error", "Invalid chapter selection.")
                return
                
            chapter = self.current_chapters[chapter_index]
            
            # Check if chapter is actually downloaded
            if not chapter.is_downloaded:
                messagebox.showwarning(
                    "Chapter Not Downloaded", 
                    f"Episode {chapter.episode_no} has not been downloaded yet.\n\n"
                    f"You can only open folders for episodes that have been downloaded. "
                    f"Download this episode first using the Download Manga tab."
                )
                return
            
            # Use controller to open chapter folder
            if self.manga_controller.open_chapter_folder(chapter):
                self.downloaded_status_var.set(f"Opened folder for Episode {chapter.episode_no}")
            else:
                messagebox.showerror("Error", f"Could not open folder for Episode {chapter.episode_no}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open chapter folder: {e}")
    
    def view_chapter_comments(self):
        """View comments for selected chapter."""
        selection = self.downloaded_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No chapter selected.")
            return
        
        if not self.current_manga:
            messagebox.showerror("Error", "No manga selected.")
            return
            
        if not hasattr(self, 'current_chapters') or not self.current_chapters:
            messagebox.showerror("Error", "No chapters loaded.")
            return
        
        try:
            chapter_index = selection[0]
            if chapter_index >= len(self.current_chapters):
                messagebox.showerror("Error", "Invalid chapter selection.")
                return
                
            chapter = self.current_chapters[chapter_index]
            
            # Check if chapter is actually downloaded
            if not chapter.is_downloaded:
                messagebox.showwarning(
                    "Chapter Not Downloaded", 
                    f"Episode {chapter.episode_no} has not been downloaded yet.\n\n"
                    f"Comments are only available for episodes that have been downloaded. "
                    f"Download this episode first using the Download Manga tab."
                )
                return
            
            # Get comments from controller
            comments = self.manga_controller.get_chapter_comments(chapter)
            if not comments:
                messagebox.showinfo("No Comments", f"No comments found for Episode {chapter.episode_no}")
                return
            
            # Create comments display window
            comments_window = tk.Toplevel(self)
            comments_window.title(f"Comments - Episode {chapter.episode_no}: {chapter.title}")
            comments_window.geometry("600x400")
            comments_window.configure(bg=Config.UI_COLORS['BLACK'])
            
            # Create text widget with scrollbar
            text_frame = tk.Frame(comments_window, bg=Config.UI_COLORS['BLACK'])
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, font=Config.UI_FONTS['DEFAULT'],
                                 bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'],
                                 wrap=tk.WORD)
            scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Insert comments
            text_widget.insert(tk.END, comments)
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load comments: {e}")
    
    def refresh_banner(self):
        """Refresh banner for current manga."""
        if not self.current_manga:
            messagebox.showinfo("Info", "Please select a manga first.")
            return
        
        # Remove existing banner files to force re-download
        manga_folder = Config.get_manga_folder(self.current_manga.title_no, self.current_manga.series_name)
        bg_path = manga_folder / "banner_bg.jpg"
        fg_path = manga_folder / "banner_fg.png"
        
        try:
            if bg_path.exists():
                bg_path.unlink()
            if fg_path.exists():
                fg_path.unlink()
        except Exception as e:
            print(f"Error removing banner files: {e}")
        
        # Trigger controller to reload banner
        self.manga_controller.select_manga(self.current_manga) 