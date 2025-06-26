"""
Database panel for searching and managing manga database.
"""

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import List, Optional, Callable
import json
import threading

from models.manga import Manga
from utils.config import Config
from utils.db_manager import DatabaseManager


class DatabasePanel(tk.Frame):
    """Panel for database operations and search."""
    
    def __init__(self, parent, db_manager: DatabaseManager):
        super().__init__(parent, bg=Config.UI_COLORS['BLACK'])
        self.db_manager = db_manager
        self.on_manga_selected: Optional[Callable] = None
        self.current_results = []  # Store current search results
        
        self.setup_ui()
        
        # Bind F5 for manual refresh
        self.bind_all("<F5>", lambda event: self.refresh_data())
        self.focus_set()  # Make sure the panel can receive key events
        
    def setup_ui(self):
        """Set up the UI components."""
        # Header
        header = tk.Label(
            self,
            text="Manga Database",
            font=Config.UI_FONTS['TITLE'],
            fg=Config.UI_COLORS['BLACK'],
            bg=Config.UI_COLORS['HIGHLIGHT'],
            pady=5
        )
        header.pack(fill=tk.X, pady=(0, 8))
        
        # Search controls
        self.setup_search_controls()
        
        # Advanced search and tools
        self.setup_advanced_controls()
        
        # Results table
        self.setup_results_table()
        
        # Action buttons
        self.setup_action_buttons()
        
        # Status bar
        status_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.status_var = tk.StringVar(value="Ready.")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=Config.UI_FONTS['SMALL'],
            fg=Config.UI_COLORS['WHITE'],
            bg=Config.UI_COLORS['BLACK']
        )
        status_label.pack(side=tk.LEFT, padx=10)
        
        # F5 hint
        hint_label = tk.Label(
            status_frame, 
            text="Press F5 to force refresh database", 
            font=Config.UI_FONTS['SMALL'], 
            fg=Config.UI_COLORS['HIGHLIGHT'], 
            bg=Config.UI_COLORS['BLACK']
        )
        hint_label.pack(side=tk.RIGHT, padx=10)
    
    def setup_search_controls(self):
        """Set up search control panel."""
        query_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        query_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Genre search
        tk.Label(query_frame, text="Genre:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).grid(
                row=0, column=0, sticky="e")
        self.genre_entry = tk.Entry(query_frame, font=Config.UI_FONTS['DEFAULT'], width=15, 
                                   bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
        self.genre_entry.grid(row=0, column=1, padx=2)
        genre_btn = tk.Button(query_frame, text="Search", font=Config.UI_FONTS['DEFAULT'], 
                             bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                             command=self.search_by_genre)
        genre_btn.grid(row=0, column=2, padx=2)
        
        # Author search
        tk.Label(query_frame, text="Author:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).grid(
                row=0, column=3, sticky="e")
        self.author_entry = tk.Entry(query_frame, font=Config.UI_FONTS['DEFAULT'], width=15, 
                                    bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
        self.author_entry.grid(row=0, column=4, padx=2)
        author_btn = tk.Button(query_frame, text="Search", font=Config.UI_FONTS['DEFAULT'], 
                              bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                              command=self.search_by_author)
        author_btn.grid(row=0, column=5, padx=2)
        
        # Title search
        tk.Label(query_frame, text="Title:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).grid(
                row=1, column=0, sticky="e")
        self.title_entry = tk.Entry(query_frame, font=Config.UI_FONTS['DEFAULT'], width=15, 
                                   bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
        self.title_entry.grid(row=1, column=1, padx=2)
        title_btn = tk.Button(query_frame, text="Search", font=Config.UI_FONTS['DEFAULT'], 
                             bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                             command=self.search_by_title)
        title_btn.grid(row=1, column=2, padx=2)
        
        # Min chapters search
        tk.Label(query_frame, text="Min Chapters:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).grid(
                row=1, column=3, sticky="e")
        self.min_chapters_entry = tk.Entry(query_frame, font=Config.UI_FONTS['DEFAULT'], width=8, 
                                          bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
        self.min_chapters_entry.grid(row=1, column=4, padx=2)
        min_ch_btn = tk.Button(query_frame, text="Search", font=Config.UI_FONTS['DEFAULT'], 
                              bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                              command=self.search_by_min_chapters)
        min_ch_btn.grid(row=1, column=5, padx=2)
        
        # General buttons
        all_btn = tk.Button(query_frame, text="Show All", font=Config.UI_FONTS['DEFAULT'], 
                           bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                           command=self.show_all_manga)
        all_btn.grid(row=2, column=0, columnspan=2, pady=4)
        
        scan_btn = tk.Button(query_frame, text="Scan Downloads", font=Config.UI_FONTS['DEFAULT'], 
                            bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                            command=self.scan_downloaded_manga)
        scan_btn.grid(row=2, column=3, columnspan=3, pady=4)
        
        # Clear all fields button
        clear_btn = tk.Button(query_frame, text="Clear All", font=Config.UI_FONTS['DEFAULT'], 
                             bg=Config.UI_COLORS['HIGHLIGHT'], fg=Config.UI_COLORS['BLACK'], 
                             command=self.clear_search_fields)
        clear_btn.grid(row=2, column=2, pady=4)
    
    def setup_advanced_controls(self):
        """Set up advanced search and analysis controls."""
        advanced_frame = tk.LabelFrame(
            self, 
            text="Advanced Search & Analysis", 
            font=Config.UI_FONTS['DEFAULT'],
            fg=Config.UI_COLORS['WHITE'], 
            bg=Config.UI_COLORS['BLACK']
        )
        advanced_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Advanced search row 1
        row1_frame = tk.Frame(advanced_frame, bg=Config.UI_COLORS['BLACK'])
        row1_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Max chapters
        tk.Label(row1_frame, text="Max Chapters:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).grid(
                row=0, column=0, sticky="e", padx=2)
        self.max_chapters_entry = tk.Entry(row1_frame, font=Config.UI_FONTS['DEFAULT'], width=8, 
                                          bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
        self.max_chapters_entry.grid(row=0, column=1, padx=2)
        
        # Min grade
        tk.Label(row1_frame, text="Min Grade:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).grid(
                row=0, column=2, sticky="e", padx=2)
        self.min_grade_entry = tk.Entry(row1_frame, font=Config.UI_FONTS['DEFAULT'], width=8, 
                                       bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
        self.min_grade_entry.grid(row=0, column=3, padx=2)
        
        # Publication day
        tk.Label(row1_frame, text="Day:", font=Config.UI_FONTS['DEFAULT'], 
                fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).grid(
                row=0, column=4, sticky="e", padx=2)
        self.day_var = tk.StringVar()
        day_combo = ttk.Combobox(row1_frame, textvariable=self.day_var, width=12,
                                values=["", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", 
                                       "FRIDAY", "SATURDAY", "SUNDAY", "COMPLETED", "DAILY"])
        day_combo.grid(row=0, column=5, padx=2)
        
        # Advanced search button
        advanced_search_btn = tk.Button(row1_frame, text="Advanced Search", 
                                       font=Config.UI_FONTS['DEFAULT'], 
                                       bg=Config.UI_COLORS['HIGHLIGHT'], 
                                       fg=Config.UI_COLORS['BLACK'], 
                                       command=self.advanced_search)
        advanced_search_btn.grid(row=0, column=6, padx=5)
        
        # Analysis row 2
        row2_frame = tk.Frame(advanced_frame, bg=Config.UI_COLORS['BLACK'])
        row2_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Quick analysis buttons
        stats_btn = tk.Button(row2_frame, text="Show Statistics", 
                             font=Config.UI_FONTS['DEFAULT'], 
                             bg=Config.UI_COLORS['HIGHLIGHT'], 
                             fg=Config.UI_COLORS['BLACK'], 
                             command=self.show_statistics)
        stats_btn.grid(row=0, column=0, padx=2)
        
        top_rated_btn = tk.Button(row2_frame, text="Top Rated", 
                                 font=Config.UI_FONTS['DEFAULT'], 
                                 bg=Config.UI_COLORS['HIGHLIGHT'], 
                                 fg=Config.UI_COLORS['BLACK'], 
                                 command=self.show_top_rated)
        top_rated_btn.grid(row=0, column=1, padx=2)
        
        most_viewed_btn = tk.Button(row2_frame, text="Most Viewed", 
                                   font=Config.UI_FONTS['DEFAULT'], 
                                   bg=Config.UI_COLORS['HIGHLIGHT'], 
                                   fg=Config.UI_COLORS['BLACK'], 
                                   command=self.show_most_viewed)
        most_viewed_btn.grid(row=0, column=2, padx=2)
        
        recent_btn = tk.Button(row2_frame, text="Recently Updated", 
                              font=Config.UI_FONTS['DEFAULT'], 
                              bg=Config.UI_COLORS['HIGHLIGHT'], 
                              fg=Config.UI_COLORS['BLACK'], 
                              command=self.show_recently_updated)
        recent_btn.grid(row=0, column=3, padx=2)
        
        # Database maintenance buttons
        sync_btn = tk.Button(row2_frame, text="Full Sync", 
                            font=Config.UI_FONTS['DEFAULT'], 
                            bg=Config.UI_COLORS['HIGHLIGHT'], 
                            fg=Config.UI_COLORS['BLACK'], 
                            command=self.sync_database)
        sync_btn.grid(row=0, column=4, padx=2)
        
        # Separator
        separator = ttk.Separator(row2_frame, orient="vertical")
        separator.grid(row=0, column=5, sticky="ns", padx=10)
        
        # Genre/Author dropdowns
        genres_btn = tk.Button(row2_frame, text="Browse Genres", 
                              font=Config.UI_FONTS['DEFAULT'], 
                              bg=Config.UI_COLORS['HIGHLIGHT'], 
                              fg=Config.UI_COLORS['BLACK'], 
                              command=self.browse_genres)
        genres_btn.grid(row=0, column=6, padx=2)
        
        authors_btn = tk.Button(row2_frame, text="Browse Authors", 
                               font=Config.UI_FONTS['DEFAULT'], 
                               bg=Config.UI_COLORS['HIGHLIGHT'], 
                               fg=Config.UI_COLORS['BLACK'], 
                               command=self.browse_authors)
        authors_btn.grid(row=0, column=7, padx=2)
    
    def setup_action_buttons(self):
        """Set up action buttons for results."""
        action_frame = tk.Frame(self, bg=Config.UI_COLORS['BLACK'])
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Export button
        export_btn = tk.Button(action_frame, text="Export Results (JSON)", 
                              font=Config.UI_FONTS['DEFAULT'], 
                              bg=Config.UI_COLORS['HIGHLIGHT'], 
                              fg=Config.UI_COLORS['BLACK'], 
                              command=self.export_results)
        export_btn.pack(side=tk.LEFT, padx=2)
        
        # View details button
        details_btn = tk.Button(action_frame, text="View Details", 
                               font=Config.UI_FONTS['DEFAULT'], 
                               bg=Config.UI_COLORS['HIGHLIGHT'], 
                               fg=Config.UI_COLORS['BLACK'], 
                               command=self.view_selected_details)
        details_btn.pack(side=tk.LEFT, padx=2)
        
        # Refresh button
        refresh_btn = tk.Button(action_frame, text="Refresh", 
                               font=Config.UI_FONTS['DEFAULT'], 
                               bg=Config.UI_COLORS['HIGHLIGHT'], 
                               fg=Config.UI_COLORS['BLACK'], 
                               command=self.refresh_data)
        refresh_btn.pack(side=tk.LEFT, padx=2)
        
        # Results count label
        self.results_count_var = tk.StringVar(value="0 results")
        count_label = tk.Label(action_frame, textvariable=self.results_count_var,
                              font=Config.UI_FONTS['DEFAULT'],
                              fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK'])
        count_label.pack(side=tk.RIGHT, padx=10)
    
    def setup_results_table(self):
        """Set up the results table."""
        columns = ("Title", "Author", "Genre", "Chapters", "Grade", "Views", "Subscribers", "Day Info", "Last Updated", "URL")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Bind double-click
        self.tree.bind("<Double-1>", self.on_item_double_click)
    
    def search_by_genre(self):
        """Search manga by genre."""
        genre = self.genre_entry.get().strip()
        if not genre:
            self.status_var.set("Enter a genre.")
            return
        
        try:
            results = self.db_manager.search_manga_by_genre(genre)
            self.show_results(results)
            self.status_var.set(f"Found {len(results)} manga with genre containing '{genre}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
    
    def search_by_author(self):
        """Search manga by author."""
        author = self.author_entry.get().strip()
        if not author:
            self.status_var.set("Enter an author.")
            return
        
        try:
            results = self.db_manager.search_manga_by_author(author)
            self.show_results(results)
            self.status_var.set(f"Found {len(results)} manga by authors containing '{author}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
    
    def search_by_title(self):
        """Search manga by title."""
        title = self.title_entry.get().strip()
        if not title:
            self.status_var.set("Enter a title.")
            return
        
        try:
            results = self.db_manager.search_manga_by_title(title)
            self.show_results(results)
            self.status_var.set(f"Found {len(results)} manga with title containing '{title}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
    
    def search_by_min_chapters(self):
        """Search manga by minimum chapters."""
        try:
            min_chapters = int(self.min_chapters_entry.get().strip())
        except ValueError:
            self.status_var.set("Enter a valid number.")
            return
        
        try:
            results = self.db_manager.search_manga_by_min_chapters(min_chapters)
            self.show_results(results)
            self.status_var.set(f"Found {len(results)} manga with {min_chapters}+ chapters.")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
    
    def show_all_manga(self):
        """Show all manga in database."""
        try:
            results = self.db_manager.get_all_manga()
            self.show_results(results)
            self.status_var.set(f"Showing all {len(results)} manga in database.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load manga: {e}")
    
    def show_results(self, manga_list: List[Manga]):
        """Display search results in the table."""
        # Store current results
        self.current_results = manga_list
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add new items
        for manga in manga_list:
            # Clean author text
            author_text = manga.author or "Unknown"
            if author_text != "Unknown":
                author_text = self._clean_text(author_text)
            
            values = (
                manga.display_title or manga.series_name,
                author_text[:30] + "..." if len(author_text) > 30 else author_text,
                manga.genre or "Unknown", 
                manga.num_chapters or 0,
                f"{manga.grade:.1f}" if manga.grade else "N/A",
                manga.views or "N/A",
                manga.subscribers or "N/A",
                manga.day_info or "N/A",
                manga.last_updated.strftime("%Y-%m-%d") if manga.last_updated else "N/A",
                manga.url or "N/A"
            )
            self.tree.insert("", tk.END, values=values)
        
        # Update results count
        self.results_count_var.set(f"{len(manga_list)} results")
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing excessive whitespace and formatting."""
        import re
        if not text:
            return ""
        # Replace multiple whitespace characters with single spaces
        cleaned = re.sub(r'\s+', ' ', text.strip())
        return cleaned
    
    def clear_search_fields(self):
        """Clear all search fields."""
        self.genre_entry.delete(0, tk.END)
        self.author_entry.delete(0, tk.END)
        self.title_entry.delete(0, tk.END)
        self.min_chapters_entry.delete(0, tk.END)
        self.max_chapters_entry.delete(0, tk.END)
        self.min_grade_entry.delete(0, tk.END)
        self.day_var.set("")
        self.status_var.set("Search fields cleared.")
    
    def auto_verify_database(self, force=False):
        """Automatically verify and scan database when tab is opened."""
        # Check if we've scanned recently (within the last 3 seconds to prevent rapid-fire scanning)
        import time
        current_time = time.time()
        if not force and hasattr(self, 'last_scan_time'):
            if current_time - self.last_scan_time < 3:
                return  # Recently scanned, skip
        
        # Mark scan time
        self.last_scan_time = current_time
        
        def scan_and_verify_in_background():
            try:
                self.status_var.set("Scanning and updating database...")
                
                # Perform full synchronization (verify + scan)
                results = self.db_manager.sync_database_with_downloads()
                
                # Extract results
                cleanup = results['cleanup_results']
                new_count = results['new_manga_added']
                deleted_count = cleanup['deleted_count']
                verified_count = cleanup['verified_count']
                
                # Build status message
                status_parts = []
                if new_count > 0:
                    status_parts.append(f"Added {new_count} new manga")
                if deleted_count > 0:
                    status_parts.append(f"removed {deleted_count} missing")
                if verified_count > 0:
                    status_parts.append(f"verified {verified_count}")
                
                if status_parts:
                    status_msg = f"Database updated: {', '.join(status_parts)}."
                else:
                    status_msg = "Database up to date."
                
                # Show notification if there were significant changes
                if new_count > 0 or deleted_count > 0:
                    self.after(100, lambda: self._show_auto_sync_notification(results))
                
                self.status_var.set(status_msg)
                
                # Load all manga after sync
                self.after(200, self.show_all_manga)
                
            except Exception as e:
                self.status_var.set(f"Auto-sync failed: {e}")
                # Still load manga even if sync failed
                self.after(200, self.show_all_manga)
        
        # Run sync in background
        threading.Thread(target=scan_and_verify_in_background, daemon=True).start()
    
    def _show_auto_cleanup_notification(self, results):
        """Show a subtle notification about automatic cleanup."""
        if results['deleted_count'] > 0:
            # Create a small notification window
            notification = tk.Toplevel(self)
            notification.title("Database Cleanup")
            notification.geometry("400x200")
            notification.configure(bg=Config.UI_COLORS['BLACK'])
            notification.transient(self.master)  # Make it stay on top of main window
            
            # Center the notification
            notification.geometry("+{}+{}".format(
                self.winfo_rootx() + 100,
                self.winfo_rooty() + 100
            ))
            
            # Content
            tk.Label(
                notification,
                text="Database Cleanup Complete",
                font=Config.UI_FONTS['TITLE'],
                fg=Config.UI_COLORS['WHITE'],
                bg=Config.UI_COLORS['BLACK']
            ).pack(pady=10)
            
            cleanup_text = f"Removed {results['deleted_count']} manga entries\nwith missing download folders."
            tk.Label(
                notification,
                text=cleanup_text,
                font=Config.UI_FONTS['DEFAULT'],
                fg=Config.UI_COLORS['WHITE'],
                bg=Config.UI_COLORS['BLACK']
            ).pack(pady=5)
            
            tk.Label(
                notification,
                text="The database now reflects your actual downloads.",
                font=Config.UI_FONTS['SMALL'],
                fg=Config.UI_COLORS['WHITE'],
                bg=Config.UI_COLORS['BLACK']
            ).pack(pady=5)
            
            # OK button
            ok_btn = tk.Button(
                notification,
                text="OK",
                font=Config.UI_FONTS['DEFAULT'],
                bg=Config.UI_COLORS['HIGHLIGHT'],
                fg=Config.UI_COLORS['BLACK'],
                command=notification.destroy
            )
            ok_btn.pack(pady=10)
            
            # Auto-close after 5 seconds
            notification.after(5000, notification.destroy)
    
    def _show_auto_sync_notification(self, results):
        """Show a notification about automatic sync results."""
        cleanup = results['cleanup_results']
        new_count = results['new_manga_added']
        deleted_count = cleanup['deleted_count']
        
        if new_count > 0 or deleted_count > 0:
            # Create a notification window
            notification = tk.Toplevel(self)
            notification.title("Database Update")
            notification.geometry("450x250")
            notification.configure(bg=Config.UI_COLORS['BLACK'])
            notification.transient(self.master)  # Make it stay on top of main window
            
            # Center the notification
            notification.geometry("+{}+{}".format(
                self.winfo_rootx() + 100,
                self.winfo_rooty() + 100
            ))
            
            # Content
            tk.Label(
                notification,
                text="Database Update Complete",
                font=Config.UI_FONTS['TITLE'],
                fg=Config.UI_COLORS['WHITE'],
                bg=Config.UI_COLORS['BLACK']
            ).pack(pady=10)
            
            # Build update message
            update_parts = []
            if new_count > 0:
                update_parts.append(f"Added {new_count} new manga")
            if deleted_count > 0:
                update_parts.append(f"Removed {deleted_count} missing manga")
            
            update_text = "\n".join(update_parts)
            tk.Label(
                notification,
                text=update_text,
                font=Config.UI_FONTS['DEFAULT'],
                fg=Config.UI_COLORS['WHITE'],
                bg=Config.UI_COLORS['BLACK']
            ).pack(pady=5)
            
            tk.Label(
                notification,
                text="Your database is now synchronized with downloads.",
                font=Config.UI_FONTS['SMALL'],
                fg=Config.UI_COLORS['WHITE'],
                bg=Config.UI_COLORS['BLACK']
            ).pack(pady=5)
            
            # OK button
            ok_btn = tk.Button(
                notification,
                text="OK",
                font=Config.UI_FONTS['DEFAULT'],
                bg=Config.UI_COLORS['HIGHLIGHT'],
                fg=Config.UI_COLORS['BLACK'],
                command=notification.destroy
            )
            ok_btn.pack(pady=10)
            
            # Auto-close after 6 seconds (slightly longer for more info)
            notification.after(6000, notification.destroy)
    
    def advanced_search(self):
        """Perform advanced search with multiple criteria."""
        try:
            # Get all search criteria
            title = self.title_entry.get().strip() or None
            author = self.author_entry.get().strip() or None
            genre = self.genre_entry.get().strip() or None
            
            min_chapters = None
            if self.min_chapters_entry.get().strip():
                min_chapters = int(self.min_chapters_entry.get().strip())
            
            max_chapters = None
            if self.max_chapters_entry.get().strip():
                max_chapters = int(self.max_chapters_entry.get().strip())
            
            min_grade = None
            if self.min_grade_entry.get().strip():
                min_grade = float(self.min_grade_entry.get().strip())
            
            day = self.day_var.get().strip() or None
            
            # Start with all manga
            results = self.db_manager.get_all_manga()
            
            # Apply filters
            if title:
                results = [m for m in results if title.lower() in (m.display_title or m.series_name or "").lower()]
            
            if author:
                results = [m for m in results if author.lower() in (m.author or "").lower()]
            
            if genre:
                results = [m for m in results if genre.lower() in (m.genre or "").lower()]
            
            if min_chapters is not None:
                results = [m for m in results if (m.num_chapters or 0) >= min_chapters]
            
            if max_chapters is not None:
                results = [m for m in results if (m.num_chapters or 0) <= max_chapters]
            
            if min_grade is not None:
                results = [m for m in results if m.grade and m.grade >= min_grade]
            
            if day:
                results = [m for m in results if day.upper() in (m.day_info or "").upper()]
            
            self.show_results(results)
            
            # Build criteria description
            criteria = []
            if title: criteria.append(f"title contains '{title}'")
            if author: criteria.append(f"author contains '{author}'")
            if genre: criteria.append(f"genre contains '{genre}'")
            if min_chapters: criteria.append(f"chapters >= {min_chapters}")
            if max_chapters: criteria.append(f"chapters <= {max_chapters}")
            if min_grade: criteria.append(f"grade >= {min_grade}")
            if day: criteria.append(f"day contains '{day}'")
            
            criteria_str = " AND ".join(criteria) if criteria else "no filters"
            self.status_var.set(f"Advanced search ({criteria_str}): {len(results)} results")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid number format: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Advanced search failed: {e}")
    
    def show_statistics(self):
        """Show database statistics in a popup window."""
        try:
            stats = self.db_manager.get_download_statistics()
            all_manga = self.db_manager.get_all_manga()
            
            # Calculate additional statistics
            genre_count = {}
            author_count = {}
            for manga in all_manga:
                genre = manga.genre or "Unknown"
                author = (manga.author or "Unknown").split(',')[0].strip()
                
                genre_count[genre] = genre_count.get(genre, 0) + 1
                author_count[author] = author_count.get(author, 0) + 1
            
            top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5]
            top_authors = sorted(author_count.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Create statistics window
            stats_window = tk.Toplevel(self)
            stats_window.title("Database Statistics")
            stats_window.geometry("500x400")
            stats_window.configure(bg=Config.UI_COLORS['BLACK'])
            
            # Create scrollable text widget
            text_frame = tk.Frame(stats_window, bg=Config.UI_COLORS['BLACK'])
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, font=Config.UI_FONTS['DEFAULT'],
                                 bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'],
                                 wrap=tk.WORD, state=tk.DISABLED)
            scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Build statistics text
            stats_text = "Database Statistics\n"
            stats_text += "=" * 30 + "\n\n"
            stats_text += f"Total Manga: {stats['total_manga']}\n"
            stats_text += f"Total Chapters: {stats['total_chapters']}\n"
            stats_text += f"Average Chapters per Manga: {stats['average_chapters']}\n\n"
            
            stats_text += "Top Genres:\n"
            stats_text += "-" * 15 + "\n"
            for genre, count in top_genres:
                stats_text += f"{genre}: {count} manga\n"
            
            stats_text += "\nTop Authors:\n"
            stats_text += "-" * 15 + "\n"
            for author, count in top_authors:
                clean_author = self._clean_text(author)[:30]
                stats_text += f"{clean_author}: {count} manga\n"
            
            # Insert text
            text_widget.config(state=tk.NORMAL)
            text_widget.insert(tk.END, stats_text)
            text_widget.config(state=tk.DISABLED)
            
            self.status_var.set("Statistics displayed.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show statistics: {e}")
    
    def show_top_rated(self):
        """Show top rated manga."""
        try:
            results = self.db_manager.get_top_rated_manga(limit=20)
            self.show_results(results)
            self.status_var.set(f"Showing top {len(results)} rated manga.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get top rated manga: {e}")
    
    def show_most_viewed(self):
        """Show most viewed manga."""
        try:
            results = self.db_manager.get_most_viewed_manga(limit=20)
            self.show_results(results)
            self.status_var.set(f"Showing top {len(results)} most viewed manga.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get most viewed manga: {e}")
    
    def show_recently_updated(self):
        """Show recently updated manga."""
        try:
            results = self.db_manager.get_recently_updated_manga(limit=20)
            self.show_results(results)
            self.status_var.set(f"Showing {len(results)} recently updated manga.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get recently updated manga: {e}")
    
    def browse_genres(self):
        """Show genre browser popup."""
        try:
            genres = self.db_manager.get_genres()
            
            # Create genre browser window
            genre_window = tk.Toplevel(self)
            genre_window.title("Browse Genres")
            genre_window.geometry("300x400")
            genre_window.configure(bg=Config.UI_COLORS['BLACK'])
            
            # Create listbox with genres
            listbox_frame = tk.Frame(genre_window, bg=Config.UI_COLORS['BLACK'])
            listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tk.Label(listbox_frame, text="Select a genre:", font=Config.UI_FONTS['DEFAULT'],
                    fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).pack(pady=5)
            
            listbox = tk.Listbox(listbox_frame, font=Config.UI_FONTS['DEFAULT'],
                               bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
            scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            
            for genre in sorted(genres):
                listbox.insert(tk.END, genre)
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            def on_genre_select(event):
                selection = listbox.curselection()
                if selection:
                    selected_genre = listbox.get(selection[0])
                    self.genre_entry.delete(0, tk.END)
                    self.genre_entry.insert(0, selected_genre)
                    genre_window.destroy()
                    self.search_by_genre()
            
            listbox.bind("<Double-1>", on_genre_select)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to browse genres: {e}")
    
    def browse_authors(self):
        """Show author browser popup."""
        try:
            authors = self.db_manager.get_authors()
            
            # Create author browser window
            author_window = tk.Toplevel(self)
            author_window.title("Browse Authors")
            author_window.geometry("400x400")
            author_window.configure(bg=Config.UI_COLORS['BLACK'])
            
            # Create listbox with authors
            listbox_frame = tk.Frame(author_window, bg=Config.UI_COLORS['BLACK'])
            listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tk.Label(listbox_frame, text="Select an author:", font=Config.UI_FONTS['DEFAULT'],
                    fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).pack(pady=5)
            
            listbox = tk.Listbox(listbox_frame, font=Config.UI_FONTS['DEFAULT'],
                               bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'])
            scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            
            for author in sorted(authors):
                clean_author = self._clean_text(author)
                listbox.insert(tk.END, clean_author)
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            def on_author_select(event):
                selection = listbox.curselection()
                if selection:
                    selected_author = listbox.get(selection[0])
                    self.author_entry.delete(0, tk.END)
                    self.author_entry.insert(0, selected_author)
                    author_window.destroy()
                    self.search_by_author()
            
            listbox.bind("<Double-1>", on_author_select)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to browse authors: {e}")
    
    def export_results(self):
        """Export current results to JSON file."""
        if not self.current_results:
            messagebox.showwarning("Warning", "No results to export.")
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Results"
            )
            
            if filename:
                # Convert manga objects to dictionary format
                export_data = []
                for manga in self.current_results:
                    manga_dict = {
                        "id": manga.id,
                        "title_no": manga.title_no,
                        "series_name": manga.series_name,
                        "display_title": manga.display_title,
                        "author": self._clean_text(manga.author) if manga.author else None,
                        "genre": manga.genre,
                        "num_chapters": manga.num_chapters,
                        "url": manga.url,
                        "grade": manga.grade,
                        "views": manga.views,
                        "subscribers": manga.subscribers,
                        "day_info": manga.day_info,
                        "last_updated": manga.last_updated.isoformat() if manga.last_updated else None
                    }
                    export_data.append(manga_dict)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Success", f"Exported {len(export_data)} results to {filename}")
                self.status_var.set(f"Exported {len(export_data)} results to file.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
    
    def view_selected_details(self):
        """View detailed information for selected manga."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a manga to view details.")
            return
        
        try:
            # Get the selected item index
            item_index = self.tree.index(selection[0])
            if item_index < len(self.current_results):
                manga = self.current_results[item_index]
                
                # Get full manga details with chapters
                full_manga = self.db_manager.get_manga_by_id(manga.id)
                if full_manga:
                    self._show_manga_details(full_manga)
                else:
                    self._show_manga_details(manga)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view details: {e}")
    
    def _show_manga_details(self, manga: Manga):
        """Show detailed manga information in a popup window."""
        # Create details window
        details_window = tk.Toplevel(self)
        details_window.title(f"Manga Details - {manga.display_title or manga.series_name}")
        details_window.geometry("600x500")
        details_window.configure(bg=Config.UI_COLORS['BLACK'])
        
        # Create scrollable text widget
        text_frame = tk.Frame(details_window, bg=Config.UI_COLORS['BLACK'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=Config.UI_FONTS['DEFAULT'],
                             bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'],
                             wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Build details text
        details_text = f"Manga Details (ID: {manga.id})\n"
        details_text += "=" * 50 + "\n\n"
        details_text += f"Title: {manga.display_title or manga.series_name}\n"
        details_text += f"Series Name: {manga.series_name}\n"
        details_text += f"Title No: {manga.title_no}\n"
        details_text += f"Author: {self._clean_text(manga.author) if manga.author else 'Unknown'}\n"
        details_text += f"Genre: {manga.genre or 'Unknown'}\n"
        details_text += f"Total Chapters: {manga.num_chapters or 0}\n"
        details_text += f"Grade: {manga.grade if manga.grade else 'N/A'}\n"
        details_text += f"Views: {manga.views or 'N/A'}\n"
        details_text += f"Subscribers: {manga.subscribers or 'N/A'}\n"
        details_text += f"Day Info: {manga.day_info or 'N/A'}\n"
        details_text += f"URL: {manga.url or 'N/A'}\n"
        details_text += f"Last Updated: {manga.last_updated.strftime('%Y-%m-%d %H:%M:%S') if manga.last_updated else 'N/A'}\n"
        
        if hasattr(manga, 'chapters') and manga.chapters:
            details_text += f"\nChapters ({len(manga.chapters)}):\n"
            details_text += "-" * 30 + "\n"
            for chapter in manga.chapters[:20]:  # Show first 20 chapters
                details_text += f"Episode {chapter.episode_no}: {chapter.title}\n"
            if len(manga.chapters) > 20:
                details_text += f"... and {len(manga.chapters) - 20} more chapters\n"
        
        # Insert text
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, details_text)
        text_widget.config(state=tk.DISABLED)
    
    def refresh_data(self):
        """Refresh the current view."""
        try:
            # Force a database sync to pick up any changes
            self.auto_verify_database(force=True)
        except Exception as e:
            messagebox.showerror("Error", f"Refresh failed: {e}")
    
    def sync_database(self):
        """Complete database synchronization: verify existing and scan for new manga."""
        def sync_in_background():
            try:
                results = self.db_manager.sync_database_with_downloads()
                
                # Show results in a popup
                self.after(100, lambda: self._show_sync_results(results))
                
                # Update status
                cleanup = results['cleanup_results']
                new_count = results['new_manga_added']
                self.status_var.set(f"Sync complete. Added {new_count} new, removed {cleanup['deleted_count']} missing, verified {cleanup['verified_count']}.")
                
                # Refresh the current view
                self.after(200, self.refresh_data)
                
            except Exception as e:
                self.after(100, lambda: messagebox.showerror("Error", f"Sync failed: {e}"))
        
        self.status_var.set("Synchronizing database (verify + scan)...")
        threading.Thread(target=sync_in_background, daemon=True).start()
    
    def _show_verification_results(self, results):
        """Show verification results in a popup window."""
        # Create results window
        results_window = tk.Toplevel(self)
        results_window.title("Database Verification Results")
        results_window.geometry("600x400")
        results_window.configure(bg=Config.UI_COLORS['BLACK'])
        
        # Create scrollable text widget
        text_frame = tk.Frame(results_window, bg=Config.UI_COLORS['BLACK'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=Config.UI_FONTS['DEFAULT'],
                             bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'],
                             wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Build results text
        results_text = "Database Verification Results\n"
        results_text += "=" * 40 + "\n\n"
        results_text += f"Total manga checked: {results['total_checked']}\n"
        results_text += f"Verified (folder exists): {results['verified_count']}\n"
        results_text += f"Deleted (missing folders): {results['deleted_count']}\n\n"
        
        if results['missing_folders']:
            results_text += "Removed from database (missing folders):\n"
            results_text += "-" * 40 + "\n"
            for item in results['missing_folders']:
                manga = item['manga']
                results_text += f"• {manga.display_title or manga.series_name}\n"
                results_text += f"  Expected folder: {item['expected_folder']}\n\n"
        else:
            results_text += "✓ All manga folders verified successfully!\n"
            results_text += "No cleanup was necessary.\n"
        
        # Insert text
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, results_text)
        text_widget.config(state=tk.DISABLED)
    
    def _show_sync_results(self, results):
        """Show synchronization results in a popup window."""
        # Create results window
        results_window = tk.Toplevel(self)
        results_window.title("Database Synchronization Results")
        results_window.geometry("600x500")
        results_window.configure(bg=Config.UI_COLORS['BLACK'])
        
        # Create scrollable text widget
        text_frame = tk.Frame(results_window, bg=Config.UI_COLORS['BLACK'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=Config.UI_FONTS['DEFAULT'],
                             bg=Config.UI_COLORS['WHITE'], fg=Config.UI_COLORS['BLACK'],
                             wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Build results text
        cleanup = results['cleanup_results']
        new_count = results['new_manga_added']
        stats = results['final_stats']
        
        results_text = "Complete Database Synchronization Results\n"
        results_text += "=" * 50 + "\n\n"
        
        results_text += "CLEANUP PHASE:\n"
        results_text += f"• Total manga checked: {cleanup['total_checked']}\n"
        results_text += f"• Verified (folders exist): {cleanup['verified_count']}\n"
        results_text += f"• Deleted (missing folders): {cleanup['deleted_count']}\n\n"
        
        results_text += "SCAN PHASE:\n"
        results_text += f"• New manga added: {new_count}\n\n"
        
        results_text += "FINAL DATABASE STATS:\n"
        results_text += f"• Total manga: {stats['total_manga']}\n"
        results_text += f"• Total chapters: {stats['total_chapters']}\n"
        results_text += f"• Average chapters per manga: {stats['average_chapters']}\n\n"
        
        if cleanup['missing_folders']:
            results_text += "Removed manga (missing folders):\n"
            results_text += "-" * 30 + "\n"
            for item in cleanup['missing_folders']:
                manga = item['manga']
                results_text += f"• {manga.display_title or manga.series_name}\n"
        else:
            results_text += "✓ No missing folders found during cleanup.\n"
        
        # Insert text
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, results_text)
        text_widget.config(state=tk.DISABLED)
    
    def scan_downloaded_manga(self):
        """Scan downloaded manga folders and update database."""
        def scan_in_background():
            try:
                count = self.db_manager.scan_downloaded_manga("")
                self.status_var.set(f"Scan completed. Added {count} manga to database.")
                # Refresh the current view
                self.after(100, self.refresh_data)
            except Exception as e:
                self.after(100, lambda: messagebox.showerror("Error", f"Scan failed: {e}"))
        
        self.status_var.set("Scanning downloaded manga folders...")
        threading.Thread(target=scan_in_background, daemon=True).start()
    
    def on_item_double_click(self, event):
        """Handle double-click on table item."""
        self.view_selected_details() 