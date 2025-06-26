import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import os
import json
import re
import webtoon_scraper
import db_utils
import time
from PIL import Image, ImageTk
import requests
from io import BytesIO

HIGHLIGHT = "#fbdd00"
WHITE = "#ffffff"
BLACK = "#000000"
FONT = ("Helvetica", 11, "bold")
TITLE_FONT = ("Helvetica", 16, "bold")

class AnimatedProgressBar(ttk.Progressbar):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._percent_label = tk.Label(master, text="", font=FONT, fg=BLACK, bg=WHITE)
        self._percent_label.place(x=0, y=0)
        self._last_value = 0
        self._max = 100
        self._running = False
        self._update_label_position()

    def set_max(self, maxval):
        self._max = maxval
        self["maximum"] = maxval

    def set_value(self, value):
        self._last_value = value
        self["value"] = value
        self._update_label()
        self._update_label_position()

    def _update_label(self):
        percent = 0
        if self._max:
            percent = int((self._last_value / self._max) * 100)
        self._percent_label.config(text=f"{percent}%")

    def _update_label_position(self):
        # Place the label at the right end of the bar
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() - 40
        y = self.winfo_y() + 2
        self._percent_label.place(x=x, y=y)

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

    def destroy(self):
        self._percent_label.destroy()
        super().destroy()

class WebtoonScraperTabbedGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Webtoon Scraper")
        self.geometry("800x750")  # Increased height to accommodate banner
        self.configure(bg=BLACK)
        self.output_dir = os.path.join(os.getcwd(), "webtoon_downloads")
        self.manga_title = None
        self.manga_dir = None
        self.downloaded_chapters = set()
        self.fetch_chapter_links = []  # For fetch tab
        self.downloaded_chapter_links = []  # For downloaded tab
        self.manga_display_names = {}  # folder_name -> display_name
        self._animated_status_running = False
        self.banner_image = None  # Store reference to prevent garbage collection
        self.create_widgets()
        self.load_downloaded_manga()

    def create_widgets(self):
        # App Title
        tk.Label(self, text="Webtoon Scraper", font=("Helvetica", 22, "bold"), fg=BLACK, bg=HIGHLIGHT, pady=10).pack(fill=tk.X, pady=(0, 10))
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.downloaded_tab = tk.Frame(self.notebook, bg=BLACK)
        self.notebook.add(self.downloaded_tab, text="Downloaded Manga")
        self.fetch_tab = tk.Frame(self.notebook, bg=BLACK)
        self.notebook.add(self.fetch_tab, text="Fetch Manga")
        self.db_tab = tk.Frame(self.notebook, bg=BLACK)
        self.notebook.add(self.db_tab, text="Manga Database")
        self.create_downloaded_tab()
        self.create_fetch_tab()
        self.create_db_tab()

    def create_downloaded_tab(self):
        # Section Header
        tk.Label(self.downloaded_tab, text="Your Downloaded Manga", font=("Helvetica", 15, "bold"), fg=BLACK, bg=HIGHLIGHT, pady=5).pack(fill=tk.X, pady=(0, 8))
        
        # Banner container frame with a border to help visually define the banner area
        banner_container = tk.Frame(self.downloaded_tab, bg=BLACK, bd=2, relief=tk.GROOVE)
        banner_container.pack(fill=tk.X, padx=10, pady=5)
        
        # Banner display frame - use a fixed width and variable height
        self.banner_frame = tk.Frame(banner_container, bg=BLACK, height=180)
        self.banner_frame.pack(fill=tk.X, expand=True)
        self.banner_frame.pack_propagate(False)  # Prevent the frame from shrinking to fit content
        
        # Banner label inside a canvas for proper image display
        self.banner_label = tk.Label(self.banner_frame, bg=BLACK)
        self.banner_label.pack(fill=tk.BOTH, expand=True)
        
        # Banner controls
        banner_controls = tk.Frame(banner_container, bg=BLACK)
        banner_controls.pack(fill=tk.X, padx=5, pady=2)
        
        # Title label - will show the manga title below the banner
        self.banner_title_label = tk.Label(banner_controls, text="", font=TITLE_FONT, fg=HIGHLIGHT, bg=BLACK)
        self.banner_title_label.pack(side=tk.LEFT, pady=2)
        
        # Refresh button on the right
        tk.Button(banner_controls, text="Refresh Banner", font=("Helvetica", 8), bg=HIGHLIGHT, fg=BLACK, 
                 command=lambda: self.refresh_banner(self.manga_var.get())).pack(side=tk.RIGHT, padx=5, pady=2)
        
        # Manga info section
        manga_info_frame = tk.Frame(self.downloaded_tab, bg=BLACK, bd=2, relief=tk.GROOVE)
        manga_info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Info layout - using a grid for better alignment
        info_grid = tk.Frame(manga_info_frame, bg=BLACK)
        info_grid.pack(fill=tk.X, padx=10, pady=5)
        
        # Author info
        tk.Label(info_grid, text="Author:", font=FONT, fg=HIGHLIGHT, bg=BLACK).grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.manga_author_label = tk.Label(info_grid, text="", font=FONT, fg=WHITE, bg=BLACK)
        self.manga_author_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        # Rating info
        tk.Label(info_grid, text="Rating:", font=FONT, fg=HIGHLIGHT, bg=BLACK).grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.manga_rating_label = tk.Label(info_grid, text="", font=FONT, fg=WHITE, bg=BLACK)
        self.manga_rating_label.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        # Downloaded chapters info
        tk.Label(info_grid, text="Downloaded:", font=FONT, fg=HIGHLIGHT, bg=BLACK).grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.manga_downloaded_label = tk.Label(info_grid, text="", font=FONT, fg=WHITE, bg=BLACK)
        self.manga_downloaded_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        # Total chapters info
        tk.Label(info_grid, text="Total Chapters:", font=FONT, fg=HIGHLIGHT, bg=BLACK).grid(row=1, column=2, sticky="e", padx=5, pady=2)
        self.manga_total_label = tk.Label(info_grid, text="", font=FONT, fg=WHITE, bg=BLACK)
        self.manga_total_label.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        # Manga selection controls
        top_frame = tk.Frame(self.downloaded_tab, bg=BLACK)
        top_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(top_frame, text="Downloaded Manga:", font=FONT, fg=WHITE, bg=BLACK).pack(side=tk.LEFT)
        self.manga_var = tk.StringVar()
        self.manga_menu = tk.OptionMenu(top_frame, self.manga_var, "", command=self.on_manga_select)
        self.manga_menu.config(font=FONT, bg=WHITE, fg=BLACK, highlightbackground=HIGHLIGHT)
        self.manga_menu.pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Refresh List", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.load_downloaded_manga).pack(side=tk.LEFT, padx=5)
        
        # Listbox frame
        listbox_frame = tk.Frame(self.downloaded_tab, bg=BLACK)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        self.downloaded_listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE, font=FONT, bg=WHITE, fg=BLACK, activestyle='none', selectbackground=HIGHLIGHT, selectforeground=BLACK, height=15)
        self.downloaded_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.downloaded_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.downloaded_listbox.config(yscrollcommand=scrollbar.set)
        
        # Add comment summary display section
        comment_frame = tk.Frame(self.downloaded_tab, bg=BLACK, bd=2, relief=tk.GROOVE)
        comment_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(comment_frame, text="Comment Summary:", font=FONT, fg=HIGHLIGHT, bg=BLACK).pack(anchor=tk.W, padx=5, pady=(5,0))
        self.comment_summary_text = tk.Text(comment_frame, height=4, font=("Helvetica", 9), bg=WHITE, fg=BLACK, wrap=tk.WORD)
        self.comment_summary_text.pack(fill=tk.X, padx=5, pady=5)
        self.comment_summary_text.config(state=tk.DISABLED)
        
        # Bind selection event to display comment summary
        self.downloaded_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        
        # Buttons
        button_frame = tk.Frame(self.downloaded_tab, bg=BLACK)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Button(button_frame, text="Open Chapter Folder", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.open_selected_chapter_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="View Comments", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.view_chapter_comments).pack(side=tk.LEFT, padx=5)
        
        self.downloaded_status_var = tk.StringVar(value="Ready.")
        tk.Label(self.downloaded_tab, textvariable=self.downloaded_status_var, font=("Helvetica", 9), fg=WHITE, bg=BLACK).pack(fill=tk.X, pady=(0, 5))

    def create_fetch_tab(self):
        # Section Header
        tk.Label(self.fetch_tab, text="Fetch and Download Manga", font=("Helvetica", 15, "bold"), fg=BLACK, bg=HIGHLIGHT, pady=5).pack(fill=tk.X, pady=(0, 8))
        url_frame = tk.Frame(self.fetch_tab, bg=BLACK)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(url_frame, text="Webtoon URL:", font=FONT, fg=WHITE, bg=BLACK).pack(side=tk.LEFT)
        self.url_entry = tk.Entry(url_frame, font=FONT, width=50, bg=WHITE, fg=BLACK)
        self.url_entry.pack(side=tk.LEFT, padx=5)
        fetch_btn = tk.Button(url_frame, text="Fetch Chapters", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.fetch_chapters)
        fetch_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover_effect(fetch_btn)
        # Listbox frame
        listbox_frame = tk.Frame(self.fetch_tab, bg=BLACK)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        self.fetch_listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, font=FONT, bg=WHITE, fg=BLACK, activestyle='none', selectbackground=HIGHLIGHT, selectforeground=BLACK, height=15)
        self.fetch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.fetch_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fetch_listbox.config(yscrollcommand=scrollbar.set)
        # Output directory
        dir_frame = tk.Frame(self.fetch_tab, bg=BLACK)
        dir_frame.pack(fill=tk.X, padx=10, pady=5)
        choose_btn = tk.Button(dir_frame, text="Choose Output Folder", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.choose_directory)
        choose_btn.pack(side=tk.LEFT)
        self._add_hover_effect(choose_btn)
        self.dir_label = tk.Label(dir_frame, text=self.output_dir, font=("Helvetica", 9), fg=WHITE, bg=BLACK)
        self.dir_label.pack(side=tk.LEFT, padx=5)
        # Download buttons
        download_frame = tk.Frame(self.fetch_tab, bg=BLACK)
        download_frame.pack(pady=10)
        
        download_btn = tk.Button(download_frame, text="Download Selected Chapters", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.download_selected)
        download_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover_effect(download_btn)
        
        resume_btn = tk.Button(download_frame, text="Resume Downloads", font=FONT, bg="#ff9900", fg=BLACK, command=self.resume_downloads)
        resume_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover_effect(resume_btn, highlight_color="#ffaa33", normal_color="#ff9900")
        # Progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Yellow.Horizontal.TProgressbar", troughcolor=WHITE, bordercolor=BLACK, background=HIGHLIGHT, lightcolor=HIGHLIGHT, darkcolor=HIGHLIGHT)
        self.fetch_progress = AnimatedProgressBar(self.fetch_tab, orient="horizontal", length=400, mode="determinate", style="Yellow.Horizontal.TProgressbar")
        self.fetch_progress.pack(pady=(0, 10))
        self.fetch_status_var = tk.StringVar(value="Ready.")
        self.fetch_status_label = tk.Label(self.fetch_tab, textvariable=self.fetch_status_var, font=("Helvetica", 9), fg=WHITE, bg=BLACK)
        self.fetch_status_label.pack(fill=tk.X, pady=(0, 5))

    def _add_hover_effect(self, widget, highlight_color="#ffe066", normal_color=HIGHLIGHT):
        def on_enter(e):
            widget.config(bg=highlight_color)
        def on_leave(e):
            widget.config(bg=normal_color)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def fetch_chapters(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a Webtoon URL.")
            return
        self.fetch_status_var.set("Fetching chapters...")
        self.fetch_progress.start_marquee()
        self._start_animated_status("Fetching chapters")
        self.fetch_listbox.delete(0, tk.END)
        threading.Thread(target=self._fetch_chapters_thread, args=(url,), daemon=True).start()

    def _fetch_chapters_thread(self, url):
        try:
            links = webtoon_scraper.get_chapter_links(url)
            if not links:
                self.fetch_status_var.set("No chapters found.")
                self.fetch_progress.stop_marquee()
                self._stop_animated_status()
                return
            self.fetch_chapter_links = links
            title_no, series_name = webtoon_scraper.extract_webtoon_info(url)
            display_name = self.get_manga_display_name_from_url_or_links(url, links)
            manga_dir = os.path.join(self.output_dir, f"webtoon_{title_no}_{series_name}")
            os.makedirs(manga_dir, exist_ok=True)
            self.save_manga_info(manga_dir, display_name)
            self.load_downloaded_chapters_for_dir(manga_dir)
            self.fetch_listbox.delete(0, tk.END)
            for i, link in enumerate(links):
                ep, title = webtoon_scraper.extract_chapter_info(link)
                display = f"Episode {ep}: {title}"
                if ep in self.downloaded_chapters:
                    display += " (downloaded)"
                self.fetch_listbox.insert(tk.END, display)
            self.fetch_status_var.set(f"Found {len(links)} chapters.")
            self.fetch_progress.stop_marquee()
            self._stop_animated_status()
            self.save_chapter_links_json(manga_dir, links, title_no, series_name)
            self.current_fetch_url = url
            self.current_fetch_manga_dir = manga_dir
            self.load_downloaded_manga()
        except Exception as e:
            self.fetch_status_var.set(f"Error: {e}")
            self.fetch_progress.stop_marquee()
            self._stop_animated_status()

    def download_selected(self):
        selected_indices = self.fetch_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "No chapters selected.")
            return
        selected_links = []
        
        for i in selected_indices:
            ep, _ = webtoon_scraper.extract_chapter_info(self.fetch_chapter_links[i])
            if ep not in self.downloaded_chapters:
                selected_links.append(self.fetch_chapter_links[i])
        if not selected_links:
            messagebox.showinfo("Info", "All selected chapters are already downloaded.")
            return
        manga_dir = getattr(self, 'current_fetch_manga_dir', None)
        url = getattr(self, 'current_fetch_url', None)
        if not manga_dir or not url:
            if selected_links:
                title_no, series_name = webtoon_scraper.extract_webtoon_info(selected_links[0])
                manga_dir = os.path.join(self.output_dir, f"webtoon_{title_no}_{series_name}")
        
        # Save selected links to download queue file
        self._save_download_queue(manga_dir, selected_links)
        
        self.fetch_progress.set_max(len(selected_links))
        self.fetch_progress.set_value(0)
        self.fetch_progress.stop_marquee()
        self._start_animated_status("Downloading chapters")
        threading.Thread(target=self._download_multiple_chapters_thread, args=(selected_links, manga_dir), daemon=True).start()

    def resume_downloads(self):
        """Resume downloads from the queue file"""
        # Try to get manga directory from current fetch context
        manga_dir = getattr(self, 'current_fetch_manga_dir', None)
        
        if not manga_dir:
            # If no current context, ask user to select a manga first
            messagebox.showinfo("Info", "Please fetch chapters for a manga first, or select a downloaded manga from the 'Downloaded Manga' tab.")
            return
        
        # Load download queue
        queue_data = self._load_download_queue(manga_dir)
        if not queue_data:
            messagebox.showinfo("Info", "No pending downloads found for this manga.")
            return
        
        queued_links = queue_data.get("chapters", [])
        if not queued_links:
            messagebox.showinfo("Info", "Download queue is empty.")
            return
        
        # Filter out already downloaded chapters
        self.load_downloaded_chapters_for_dir(manga_dir)
        remaining_links = []
        for link in queued_links:
            ep, _ = webtoon_scraper.extract_chapter_info(link)
            if ep not in self.downloaded_chapters:
                remaining_links.append(link)
        
        if not remaining_links:
            # All chapters already downloaded, clear the queue
            self._clear_download_queue(manga_dir)
            messagebox.showinfo("Info", "All chapters from the queue have already been downloaded.")
            return
        
        # Confirm resume
        timestamp = queue_data.get("timestamp", 0)
        queue_time = time.ctime(timestamp) if timestamp else "Unknown"
        result = messagebox.askyesno("Resume Downloads", 
            f"Found {len(remaining_links)} chapters in download queue from {queue_time}.\n\nDo you want to resume downloading these chapters?")
        
        if result:
            self.fetch_progress.set_max(len(remaining_links))
            self.fetch_progress.set_value(0)
            self.fetch_progress.stop_marquee()
            self._start_animated_status("Resuming downloads")
            threading.Thread(target=self._download_multiple_chapters_thread, args=(remaining_links, manga_dir), daemon=True).start()

    def _download_multiple_chapters_thread(self, selected_links, manga_dir):
        self.load_downloaded_chapters_for_dir(manga_dir)
        self.fetch_status_var.set(f"Downloading {len(selected_links)} chapters in parallel...")
        self.fetch_progress.set_max(len(selected_links))
        self.fetch_progress.set_value(0)
        import webtoon_scraper
        results = {}
        def update_progress(i):
            self.fetch_progress.set_value(i)
            self.update_idletasks()
        def download_and_update(link, idx):
            count = webtoon_scraper.download_chapter_images(link, manga_dir, max_workers=20)
            update_progress(idx+1)
            return link, count
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_idx = {executor.submit(download_and_update, link, idx): (link, idx) for idx, link in enumerate(selected_links)}
            for i, future in enumerate(as_completed(future_to_idx)):
                link, count = future.result()
                ep, _ = webtoon_scraper.extract_chapter_info(link)
                self.downloaded_chapters.add(ep)
                results[link] = count
        self.save_downloaded_chapters_for_dir(manga_dir)
        title_no, series_name = webtoon_scraper.extract_webtoon_info(manga_dir)
        all_links = self._merge_chapter_links_json(manga_dir, self.fetch_chapter_links)
        self.save_chapter_links_json(manga_dir, all_links, title_no, series_name)
        
        # Check if all downloads completed successfully
        all_successful = self._check_download_success(results, selected_links)
        
        if all_successful:
            # All downloads successful - clear the download queue
            self._clear_download_queue(manga_dir)
            self.fetch_status_var.set(f"Download complete! Downloaded {sum(results.values())} images across {len(selected_links)} chapters.")
            messagebox.showinfo("Done", f"Downloaded {sum(results.values())} images to {manga_dir}")
        else:
            # Some downloads failed - keep queue for resuming
            failed_count = len([link for link, count in results.items() if count == 0])
            self.fetch_status_var.set(f"Download partially complete. {failed_count} chapters failed - download queue preserved for resuming.")
            messagebox.showwarning("Partial Success", f"Downloaded {sum(results.values())} images to {manga_dir}\n\n{failed_count} chapters failed to download completely.\nDownload queue preserved - you can resume later.")
        
        self.fetch_progress.set_value(len(selected_links))
        self._stop_animated_status()
        self._refresh_fetch_listbox()
        self._refresh_downloaded_listbox()

    def _start_animated_status(self, base_text):
        self._animated_status_running = True
        def animate():
            dots = 0
            while self._animated_status_running:
                self.fetch_status_var.set(base_text + "." * (dots % 4))
                dots += 1
                time.sleep(0.5)
        threading.Thread(target=animate, daemon=True).start()

    def _stop_animated_status(self):
        self._animated_status_running = False

    def _merge_chapter_links_json(self, manga_dir, new_links):
        chapter_json = os.path.join(manga_dir, "chapter_links.json")
        all_links = list(new_links)
        if os.path.exists(chapter_json):
            try:
                with open(chapter_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    old_links = data.get("chapters", [])
                    # Merge and deduplicate, preserving order
                    seen = set()
                    all_links = [x for x in old_links + new_links if not (x in seen or seen.add(x))]
            except Exception:
                pass
        return all_links

    def save_chapter_links_json(self, manga_dir, links, title_no, series_name):
        # Save chapter_links.json in the manga folder
        chapter_json = os.path.join(manga_dir, "chapter_links.json")
        data = {
            "title_no": title_no,
            "series_name": series_name,
            "total_chapters": len(links),
            "chapters": links
        }
        with open(chapter_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_manga_info(self, manga_dir, display_name):
        info_json = os.path.join(manga_dir, "manga_info.json")
        with open(info_json, "w", encoding="utf-8") as f:
            json.dump({"display_name": display_name}, f)

    def get_manga_display_name_from_url_or_links(self, url, links):
        # Try to get a nice display name from the URL or the first chapter link
        parsed = re.search(r"/([^/]+)/list", url)
        if parsed:
            return parsed.group(1).replace('-', ' ').title()
        if links:
            # Try to extract from the first link
            parsed2 = re.search(r"/([^/]+)/episode", links[0])
            if parsed2:
                return parsed2.group(1).replace('-', ' ').title()
        return url

    def load_downloaded_chapters_for_dir(self, manga_dir):
        self.downloaded_chapters = set()
        if manga_dir:
            record = os.path.join(manga_dir, "downloaded.json")
            if os.path.exists(record):
                try:
                    with open(record, "r", encoding="utf-8") as f:
                        self.downloaded_chapters = set(json.load(f))
                except Exception:
                    self.downloaded_chapters = set()

    def save_downloaded_chapters_for_dir(self, manga_dir):
        if manga_dir:
            record = os.path.join(manga_dir, "downloaded.json")
            with open(record, "w", encoding="utf-8") as f:
                json.dump(sorted(self.downloaded_chapters), f)

    def _save_download_queue(self, manga_dir, selected_links):
        """Save the list of chapters to download to a queue file"""
        if manga_dir:
            os.makedirs(manga_dir, exist_ok=True)
            queue_file = os.path.join(manga_dir, "download_queue.json")
            queue_data = {
                "timestamp": time.time(),
                "total_chapters": len(selected_links),
                "chapters": selected_links
            }
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(queue_data, f, indent=2)
            print(f"Saved download queue with {len(selected_links)} chapters to {queue_file}")

    def _clear_download_queue(self, manga_dir):
        """Clear the download queue file after successful completion"""
        if manga_dir:
            queue_file = os.path.join(manga_dir, "download_queue.json")
            if os.path.exists(queue_file):
                try:
                    os.remove(queue_file)
                    print(f"Cleared download queue: {queue_file}")
                except Exception as e:
                    print(f"Error clearing download queue: {e}")

    def _check_download_success(self, results, selected_links):
        """Check if all downloads completed successfully"""
        if len(results) != len(selected_links):
            return False  # Not all chapters were processed
        
        # Check if any chapter downloaded 0 images (indicating failure)
        for link, image_count in results.items():
            if image_count == 0:
                return False
        
        return True

    def _load_download_queue(self, manga_dir):
        """Load pending downloads from queue file"""
        if not manga_dir:
            return None
        
        queue_file = os.path.join(manga_dir, "download_queue.json")
        if not os.path.exists(queue_file):
            return None
        
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading download queue: {e}")
            return None

    def _refresh_fetch_listbox(self):
        self.fetch_listbox.delete(0, tk.END)
        for i, link in enumerate(self.fetch_chapter_links):
            ep, title = webtoon_scraper.extract_chapter_info(link)
            display = f"Episode {ep}: {title}"
            if ep in self.downloaded_chapters:
                display += " (downloaded)"
            self.fetch_listbox.insert(tk.END, display)

    def _refresh_downloaded_listbox(self):
        self.downloaded_listbox.delete(0, tk.END)
        for i, link in enumerate(self.downloaded_chapter_links):
            ep, title = webtoon_scraper.extract_chapter_info(link)
            display = f"Episode {ep}: {title}"
            if ep in self.downloaded_chapters:
                display += " (downloaded)"
            self.downloaded_listbox.insert(tk.END, display)

    def load_downloaded_manga(self):
        self.manga_var.set("")
        menu = self.manga_menu["menu"]
        menu.delete(0, "end")
        manga_folders = []
        self.manga_display_names = {}
        if os.path.exists(self.output_dir):
            for name in os.listdir(self.output_dir):
                path = os.path.join(self.output_dir, name)
                if os.path.isdir(path) and name.startswith("webtoon_"):
                    # Only include if at least one episode folder exists (case-insensitive)
                    has_episode = False
                    try:
                        for sub in os.listdir(path):
                            if os.path.isdir(os.path.join(path, sub)) and sub.lower().startswith("episode_"):
                                has_episode = True
                                break
                    except Exception:
                        continue
                    if has_episode:
                        # Try to get display name from manga_info.json
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
        # Always update the dropdown
        menu.delete(0, "end")
        for folder, display_name in manga_folders:
            menu.add_command(label=display_name, command=lambda f=folder: self.on_manga_select(f))
        if manga_folders:
            self.manga_var.set(manga_folders[0][0])
            self.on_manga_select(manga_folders[0][0])
        else:
            self.downloaded_listbox.delete(0, tk.END)
            self.manga_var.set("")
            # Remove all dropdown entries
            menu.delete(0, "end")

    def on_manga_select(self, folder):
        self.manga_var.set(folder)
        self.manga_dir = os.path.join(self.output_dir, folder)
        self.downloaded_chapter_links = []
        self.downloaded_chapters = set()
        self.downloaded_listbox.delete(0, tk.END)
        
        # Load banner image if available
        self.load_banner_image(folder)
        
        # Update banner title with display name
        display_name = self.manga_display_names.get(folder, folder)
        self.banner_title_label.config(text=display_name)
        
        # Load and display manga info
        self.load_manga_info(folder)
        
        chapter_json = os.path.join(self.manga_dir, "chapter_links.json")
        if os.path.exists(chapter_json):
            try:
                with open(chapter_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.downloaded_chapter_links = data.get("chapters", [])
            except Exception:
                self.downloaded_chapter_links = []
        else:
            self.downloaded_chapter_links = self.reconstruct_chapter_links_from_folders(self.manga_dir)
        self.load_downloaded_chapters_for_dir(self.manga_dir)
        self.downloaded_listbox.delete(0, tk.END)
        for i, link in enumerate(self.downloaded_chapter_links):
            ep, title = webtoon_scraper.extract_chapter_info(link)
            display = f"Episode {ep}: {title}"
            if ep in self.downloaded_chapters:
                display += " (downloaded)"
            self.downloaded_listbox.insert(tk.END, display)
        # Show the display name in the status bar
        display_name = self.manga_display_names.get(folder, folder)
        self.downloaded_status_var.set(f"Loaded {len(self.downloaded_chapter_links)} chapters from {display_name}.")
        
        # Update downloaded and total chapter counts
        downloaded_count = len(self.downloaded_chapters)
        total_count = len(self.downloaded_chapter_links)
        self.manga_downloaded_label.config(text=f"{downloaded_count} chapters")
        self.manga_total_label.config(text=f"{total_count} chapters")

    def load_manga_info(self, folder):
        """Load and display manga metadata"""
        if not folder:
            # Clear info if no folder selected
            self.manga_author_label.config(text="")
            self.manga_rating_label.config(text="")
            self.manga_downloaded_label.config(text="")
            self.manga_total_label.config(text="")
            return
            
        # Default values
        author = "Unknown"
        rating = "N/A"
        
        # Try to get manga info from database first
        match = re.match(r"webtoon_(\d+)_(.*)", folder)
        if match:
            title_no = match.group(1)
            series_name = match.group(2)
            
            # Query database for manga info
            try:
                import db_utils
                db_utils.init_db()
                with db_utils.get_connection() as conn:
                    c = conn.cursor()
                    c.execute('''SELECT author, grade FROM manga WHERE title_no=?''', (title_no,))
                    row = c.fetchone()
                    if row:
                        author, grade = row
                        if author:
                            author = author
                        if grade:
                            rating = f"{grade:.1f}/5.0"
            except Exception as e:
                print(f"Error querying database: {e}")
        
        # If database query failed or info is missing, try manga_info.json
        if author == "Unknown" or rating == "N/A":
            manga_dir = os.path.join(self.output_dir, folder)
            info_json = os.path.join(manga_dir, "manga_info.json")
            if os.path.exists(info_json):
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        if "author" in info and info["author"]:
                            author = info["author"]
                        if "grade" in info and info["grade"]:
                            rating = f"{float(info['grade']):.1f}/5.0"
                except Exception as e:
                    print(f"Error loading manga info: {e}")
        
        # Update the info labels
        self.manga_author_label.config(text=author)
        self.manga_rating_label.config(text=rating)
        
        # Count downloaded chapters
        downloaded_count = len(self.downloaded_chapters) if hasattr(self, 'downloaded_chapters') else 0
        total_count = len(self.downloaded_chapter_links) if hasattr(self, 'downloaded_chapter_links') else 0
        
        # Update chapter count labels
        self.manga_downloaded_label.config(text=f"{downloaded_count} chapters")
        self.manga_total_label.config(text=f"{total_count} chapters")

    def load_banner_image(self, folder):
        """Load and display the banner image for the selected manga"""
        # Clear current banner
        self.banner_label.config(image="")
        self.banner_image = None
        
        if not folder:
            return
            
        manga_dir = os.path.join(self.output_dir, folder)
        
        # Check for local banner files first
        banner_bg_file = os.path.join(manga_dir, "banner_bg.jpg")
        banner_fg_file = os.path.join(manga_dir, "banner_fg.png")
        
        # Flags to track what we found
        has_bg = os.path.exists(banner_bg_file)
        has_fg = os.path.exists(banner_fg_file)
        
        # If local files don't exist, check manga_info.json for URLs
        banner_bg_url = None
        banner_fg_url = None
        
        if not (has_bg and has_fg):
            info_json = os.path.join(manga_dir, "manga_info.json")
            if os.path.exists(info_json):
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        banner_bg_url = info.get("banner_bg_url")
                        banner_fg_url = info.get("banner_fg_url")
                        
                        # Legacy support for older versions
                        if not banner_bg_url and "banner_url" in info:
                            banner_bg_url = info.get("banner_url")
                except Exception:
                    pass
        
        try:
            # If we have local files, use them
            if has_bg or has_fg:
                self.display_layered_banner(banner_bg_file if has_bg else None, 
                                           banner_fg_file if has_fg else None)
            
            # If we don't have local files but have URLs, download and display
            elif banner_bg_url or banner_fg_url:
                self.downloaded_status_var.set(f"Downloading banner images...")
                threading.Thread(target=self._download_and_display_layered_banner, 
                               args=(banner_bg_url, banner_fg_url, banner_bg_file, banner_fg_file), 
                               daemon=True).start()
            else:
                # Show placeholder with manga name if no banner available
                display_name = self.manga_display_names.get(folder, folder)
                self.banner_label.config(text=f"{display_name}", font=TITLE_FONT, fg=WHITE)
        except Exception as e:
            print(f"Error loading banner: {e}")
            self.banner_label.config(text="Banner not available", font=FONT, fg=WHITE)

    def _download_and_display_layered_banner(self, bg_url, fg_url, bg_save_path, fg_save_path):
        """Download banner images in a separate thread and display them layered"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://www.webtoons.com/'
            }
            
            bg_img = None
            fg_img = None
            
            # Download background image if URL provided
            if bg_url:
                response = requests.get(bg_url, headers=headers)
                if response.status_code == 200:
                    # Save the image
                    with open(bg_save_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Load the image
                    bg_img = Image.open(BytesIO(response.content))
                    print(f"Downloaded background banner: {bg_url}")
            
            # Download foreground image if URL provided
            if fg_url:
                response = requests.get(fg_url, headers=headers)
                if response.status_code == 200:
                    # Save the image
                    with open(fg_save_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Load the image
                    fg_img = Image.open(BytesIO(response.content))
                    print(f"Downloaded foreground banner: {fg_url}")
            
            # Display the layered images
            self.after(100, lambda: self.display_layered_banner(bg_save_path if bg_img else None, 
                                                             fg_save_path if fg_img else None))
            
        except Exception as e:
            print(f"Error downloading banner: {e}")
            self.after(100, lambda: self.banner_label.config(text="Error loading banner", font=FONT, fg=WHITE))
        finally:
            self.after(100, lambda: self.downloaded_status_var.set("Ready."))

    def display_layered_banner(self, bg_path, fg_path):
        """Resize and display a layered banner with background and foreground images"""
        try:
            # Get frame size - use the full width of the window
            frame_width = self.winfo_width()
            
            # If frame width is too small (during startup), use a default
            if frame_width < 100:
                frame_width = 800
            
            # First load and process the background image if available
            if bg_path and os.path.exists(bg_path):
                bg_img = Image.open(bg_path)
                
                # For background banners, they're typically very wide
                # and we want to fit them to the width while maintaining a reasonable height
                width, height = bg_img.size
                
                # Calculate new dimensions for background
                if width > height * 3:  # Very wide banner
                    new_width = frame_width - 40  # Account for padding
                    new_height = min(180, int(new_width * 0.25))  # Height around 25% of width
                    
                    # Resize with LANCZOS for better quality
                    bg_resized = bg_img.resize((new_width, int((height / width) * new_width)), Image.LANCZOS)
                    
                    # Crop the center portion for height
                    if bg_resized.height > new_height:
                        top = (bg_resized.height - new_height) // 2
                        bg_final = bg_resized.crop((0, top, new_width, top + new_height))
                    else:
                        bg_final = bg_resized
                else:
                    # Standard banner/image (closer to square or standard proportions)
                    new_height = 180
                    new_width = int((width / height) * new_height)
                    
                    # Limit width to frame width
                    if new_width > frame_width - 40:
                        new_width = frame_width - 40
                        new_height = int((height / width) * new_width)
                    
                    bg_final = bg_img.resize((new_width, new_height), Image.LANCZOS)
                
                # Create the result image with RGBA to support transparency for foreground
                final_img = Image.new("RGBA", (bg_final.width, bg_final.height), (0, 0, 0, 0))
                
                # If background isn't already RGBA, convert it
                if bg_final.mode != "RGBA":
                    bg_final = bg_final.convert("RGBA")
                
                # Paste background image
                final_img.paste(bg_final, (0, 0))
                
                # Now handle foreground image if available
                if fg_path and os.path.exists(fg_path):
                    try:
                        fg_img = Image.open(fg_path)
                        
                        # If foreground isn't RGBA (transparent PNG), convert it
                        if fg_img.mode != "RGBA":
                            fg_img = fg_img.convert("RGBA")
                        
                        # Resize foreground to match background height but maintain aspect ratio
                        fg_width, fg_height = fg_img.size
                        fg_new_height = bg_final.height
                        fg_new_width = int((fg_width / fg_height) * fg_new_height)
                        
                        # If foreground would be larger than background, resize to fit
                        if fg_new_width > bg_final.width:
                            fg_new_width = bg_final.width
                            fg_new_height = int((fg_height / fg_width) * fg_new_width)
                        
                        fg_resized = fg_img.resize((fg_new_width, fg_new_height), Image.LANCZOS)
                        
                        # Calculate position to center foreground over background
                        # Usually foreground character images are placed right-aligned
                        fg_x = bg_final.width - fg_new_width
                        fg_y = 0
                        
                        # Paste foreground onto result (using alpha channel as mask)
                        final_img.paste(fg_resized, (fg_x, fg_y), fg_resized)
                    except Exception as e:
                        print(f"Error processing foreground image: {e}")
                
                # Convert to PhotoImage and display
                # Convert RGBA to RGB for PhotoImage (remove transparency)
                final_img_rgb = Image.new("RGB", final_img.size, (0, 0, 0))
                final_img_rgb.paste(final_img, mask=final_img.split()[3])  # Use alpha as mask
                
                photo = ImageTk.PhotoImage(final_img_rgb)
                self.banner_image = photo  # Keep a reference to prevent garbage collection
                
                # Update banner label and frame height
                self.banner_label.config(image=photo, text="")
                self.banner_frame.config(height=final_img.height)
                
                # After a short delay, update the frame height to fit the image
                self.after(100, lambda: self.banner_frame.config(height=final_img.height))
                self.after(100, lambda: self.banner_frame.pack_propagate(True))
                self.after(200, lambda: self.banner_frame.pack_propagate(False))
                
            elif bg_path is None and fg_path and os.path.exists(fg_path):
                # Only foreground image available, display it alone
                fg_img = Image.open(fg_path)
                self.display_banner(fg_img)
            elif bg_path and os.path.exists(bg_path) and fg_path is None:
                # Only background image available
                bg_img = Image.open(bg_path)
                self.display_banner(bg_img)
            else:
                self.banner_label.config(text="Banner images not found", font=FONT, fg=WHITE)
                
        except Exception as e:
            print(f"Error displaying layered banner: {e}")
            self.banner_label.config(text=f"Error displaying banner: {str(e)}", font=FONT, fg=WHITE)

    def display_banner(self, img):
        """Resize and display a banner image"""
        try:
            # Get frame size - use the full width of the window
            frame_width = self.winfo_width()
            
            # If frame width is too small (during startup), use a default
            if frame_width < 100:
                frame_width = 800
            
            # Calculate aspect ratio and resize image
            width, height = img.size
            
            # For background banners, they're typically very wide, so use width as priority
            # and adjust height to maintain a reasonable banner size
            if width > height * 3:  # Very wide banner (like a background banner)
                # For very wide banners, fit to width and crop height
                new_width = frame_width - 40  # Account for padding
                # Calculate appropriate height for a banner (typically 150-240px)
                new_height = min(180, int(new_width * 0.25))  # Height around 25% of width
                
                # Resize with LANCZOS for better quality
                # For wide banners, resize to fit width, then crop center portion for height
                img_resized = img.resize((new_width, int((height / width) * new_width)), Image.LANCZOS)
                
                # Crop the center portion for height
                if img_resized.height > new_height:
                    # Get center crop coordinates
                    top = (img_resized.height - new_height) // 2
                    img = img_resized.crop((0, top, new_width, top + new_height))
                else:
                    img = img_resized
            else:
                # Standard banner/image (closer to square or standard proportions)
                new_height = 180
                new_width = int((width / height) * new_height)
                
                # Limit width to frame width
                if new_width > frame_width - 40:  # Account for padding
                    new_width = frame_width - 40
                    new_height = int((height / width) * new_width)
                
                # Resize with LANCZOS for better quality
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage and display
            photo = ImageTk.PhotoImage(img)
            self.banner_image = photo  # Keep a reference to prevent garbage collection
            
            # Update banner label and frame height
            self.banner_label.config(image=photo, text="")
            self.banner_frame.config(height=img.height)
            
            # After a short delay, update the frame height to fit the image
            # (this helps with GUI rendering)
            self.after(100, lambda: self.banner_frame.config(height=img.height))
            self.after(100, lambda: self.banner_frame.pack_propagate(True))
            self.after(200, lambda: self.banner_frame.pack_propagate(False))
        except Exception as e:
            print(f"Error displaying banner: {e}")
            self.banner_label.config(text="Error displaying banner", font=FONT, fg=WHITE)

    def refresh_banner(self, folder):
        """Force refresh the banner by downloading it again"""
        if not folder:
            messagebox.showinfo("Info", "Please select a manga first.")
            return
            
        manga_dir = os.path.join(self.output_dir, folder)
        info_json = os.path.join(manga_dir, "manga_info.json")
        banner_bg_file = os.path.join(manga_dir, "banner_bg.jpg")
        banner_fg_file = os.path.join(manga_dir, "banner_fg.png")
        
        # Try to extract title_no and series_name from folder name
        match = re.match(r"webtoon_(\d+)_(.*)", folder)
        if match:
            title_no = match.group(1)
            series_name = match.group(2)
            
            # Construct URL for the webtoon
            url = f"https://www.webtoons.com/en/search?keyword={series_name.replace('_', '+')}"
            
            self.downloaded_status_var.set(f"Fetching banner for {series_name}...")
            
            # Run in a separate thread to avoid blocking the UI
            threading.Thread(target=self._fetch_banner_thread, args=(url, title_no, series_name, manga_dir), daemon=True).start()
        else:
            # If we can't extract from folder name, try to load from manga_info.json
            if os.path.exists(info_json):
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        banner_bg_url = info.get("banner_bg_url")
                        banner_fg_url = info.get("banner_fg_url")
                        
                        # Legacy support
                        if not banner_bg_url and "banner_url" in info:
                            banner_bg_url = info.get("banner_url")
                        
                    if banner_bg_url or banner_fg_url:
                        # If we have URLs, download them again
                        self.downloaded_status_var.set("Re-downloading banner images...")
                        threading.Thread(target=self._download_and_display_layered_banner, 
                                        args=(banner_bg_url, banner_fg_url, banner_bg_file, banner_fg_file), 
                                        daemon=True).start()
                    else:
                        messagebox.showinfo("Info", "No banner URLs found. Please try fetching chapters first.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to refresh banner: {e}")
            else:
                messagebox.showinfo("Info", "No manga info found. Please try fetching chapters first.")

    def _fetch_banner_thread(self, url, title_no, series_name, manga_dir):
        """Fetch the webtoon page and extract the banner in a separate thread"""
        try:
            # Fetch the chapter links to get the banner
            chapters = webtoon_scraper.get_chapter_links(url)
            
            # After getting chapters, check if banner files were created
            banner_bg_file = os.path.join(manga_dir, "banner_bg.jpg")
            banner_fg_file = os.path.join(manga_dir, "banner_fg.png")
            
            has_bg = os.path.exists(banner_bg_file)
            has_fg = os.path.exists(banner_fg_file)
            
            if has_bg or has_fg:
                # Success! Load and display the banner
                self.after(100, lambda: self.load_banner_image(f"webtoon_{title_no}_{series_name}"))
                self.after(100, lambda: self.downloaded_status_var.set("Banner refreshed successfully."))
            else:
                # If files don't exist, check manga_info.json for URLs
                info_json = os.path.join(manga_dir, "manga_info.json")
                if os.path.exists(info_json):
                    try:
                        with open(info_json, "r", encoding="utf-8") as f:
                            info = json.load(f)
                            banner_bg_url = info.get("banner_bg_url")
                            banner_fg_url = info.get("banner_fg_url")
                            
                            # Legacy support
                            if not banner_bg_url and "banner_url" in info:
                                banner_bg_url = info.get("banner_url")
                            
                        if banner_bg_url or banner_fg_url:
                            # If we have URLs but no files, download them
                            self._download_and_display_layered_banner(banner_bg_url, banner_fg_url, 
                                                                     banner_bg_file, banner_fg_file)
                        else:
                            self.after(100, lambda: messagebox.showinfo("Info", "No banner found for this manga."))
                            self.after(100, lambda: self.downloaded_status_var.set("Ready."))
                    except Exception:
                        self.after(100, lambda: messagebox.showinfo("Info", "Could not find banner for this manga."))
                        self.after(100, lambda: self.downloaded_status_var.set("Ready."))
                else:
                    self.after(100, lambda: messagebox.showinfo("Info", "Could not find banner for this manga."))
                    self.after(100, lambda: self.downloaded_status_var.set("Ready."))
        except Exception as e:
            self.after(100, lambda: messagebox.showerror("Error", f"Error fetching banner: {e}"))
            self.after(100, lambda: self.downloaded_status_var.set("Ready."))

    def reconstruct_chapter_links_from_folders(self, manga_dir):
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

    def open_selected_chapter_folder(self):
        selection = self.downloaded_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No chapter selected.")
            return
        idx = selection[0]
        if idx >= len(self.downloaded_chapter_links):
            messagebox.showerror("Error", "Invalid chapter selection.")
            return
        link = self.downloaded_chapter_links[idx]
        ep, title = webtoon_scraper.extract_chapter_info(link)
        # Find the folder for this episode
        # Folders are named like Episode_{ep}_{title}
        # We'll match on episode number
        found_folder = None
        for name in os.listdir(self.manga_dir):
            if name.lower().startswith(f"episode_{ep}") and os.path.isdir(os.path.join(self.manga_dir, name)):
                found_folder = os.path.join(self.manga_dir, name)
                break
        if not found_folder:
            messagebox.showerror("Error", f"Could not find folder for Episode {ep}.")
            return
        # Open the folder in the system file explorer
        import platform
        import subprocess
        try:
            if platform.system() == "Windows":
                os.startfile(found_folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", found_folder])
            else:
                subprocess.Popen(["xdg-open", found_folder])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def on_chapter_select(self, event):
        """Display comment summary when a chapter is selected"""
        selection = self.downloaded_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if idx >= len(self.downloaded_chapter_links):
            return
            
        link = self.downloaded_chapter_links[idx]
        ep, title = webtoon_scraper.extract_chapter_info(link)
        
        # Find the folder for this episode
        found_folder = None
        for name in os.listdir(self.manga_dir):
            if name.lower().startswith(f"episode_{ep}") and os.path.isdir(os.path.join(self.manga_dir, name)):
                found_folder = os.path.join(self.manga_dir, name)
                break
                
        if not found_folder:
            self.update_comment_summary("No comment summary available for this chapter.")
            return
            
        # Check if comments file exists
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
        """Update the comment summary text widget"""
        self.comment_summary_text.config(state=tk.NORMAL)
        self.comment_summary_text.delete(1.0, tk.END)
        self.comment_summary_text.insert(tk.END, text)
        self.comment_summary_text.config(state=tk.DISABLED)

    def view_chapter_comments(self):
        """Open the comments file for the selected chapter"""
        selection = self.downloaded_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No chapter selected.")
            return
            
        idx = selection[0]
        if idx >= len(self.downloaded_chapter_links):
            messagebox.showerror("Error", "Invalid chapter selection.")
            return
            
        link = self.downloaded_chapter_links[idx]
        ep, title = webtoon_scraper.extract_chapter_info(link)
        
        # Find the folder for this episode
        found_folder = None
        for name in os.listdir(self.manga_dir):
            if name.lower().startswith(f"episode_{ep}") and os.path.isdir(os.path.join(self.manga_dir, name)):
                found_folder = os.path.join(self.manga_dir, name)
                break
                
        if not found_folder:
            messagebox.showerror("Error", f"Could not find folder for Episode {ep}.")
            return
            
        # Check if comments file exists
        comments_file = os.path.join(found_folder, f"comments_episode_{ep}.txt")
        if not os.path.exists(comments_file):
            messagebox.showerror("Error", f"No comments file found for Episode {ep}.")
            return
            
        # Open the comments file in the default text editor
        import platform
        import subprocess
        try:
            if platform.system() == "Windows":
                os.startfile(comments_file)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", comments_file])
            else:
                subprocess.Popen(["xdg-open", comments_file])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open comments file: {e}")

    def query_by_genre(self):
        genre = self.db_genre_entry.get().strip()
        if not genre:
            self.db_status_var.set("Enter a genre.")
            return
        results = db_utils.query_manga_by_genre(genre)
        self.show_db_results(results)

    def query_by_author(self):
        author = self.db_author_entry.get().strip()
        if not author:
            self.db_status_var.set("Enter an author.")
            return
        results = db_utils.query_manga_by_author(author)
        self.show_db_results(results)

    def query_by_title(self):
        title = self.db_title_entry.get().strip()
        if not title:
            self.db_status_var.set("Enter a title.")
            return
        results = db_utils.query_manga_by_title(title)
        self.show_db_results(results)

    def query_by_min_chapters(self):
        try:
            min_chapters = int(self.db_min_chapters_entry.get().strip())
        except Exception:
            self.db_status_var.set("Enter a valid number.")
            return
        results = db_utils.query_manga_by_min_chapters(min_chapters)
        self.show_db_results(results)

    def query_all_manga(self):
        results = db_utils.get_all_manga()
        self.show_db_results(results)

    def show_db_results(self, results):
        self.db_tree.delete(*self.db_tree.get_children())
        for row in results:
            # row: (id, title_no, series_name, display_title, author, genre, num_chapters, url, last_updated, grade, views, subscribers, day_info)
            self.db_tree.insert("", tk.END, values=(
                row[3],  # Title
                row[4],  # Author
                row[5],  # Genre
                row[6],  # Chapters
                row[9],  # Grade
                row[10], # Views
                row[11], # Subscribers
                row[12], # Day Info
                row[8],  # Last Updated
                row[7],  # URL
            ))
        self.db_status_var.set(f"{len(results)} result(s) found.")

    def scan_downloaded_manga(self):
        # Scan all manga folders in the downloads directory and update the DB
        base_dir = self.output_dir
        count = 0
        for name in os.listdir(base_dir):
            path = os.path.join(base_dir, name)
            if os.path.isdir(path) and name.startswith("webtoon_"):
                # Try to get info from chapter_links.json and manga_info.json
                chapter_json = os.path.join(path, "chapter_links.json")
                info_json = os.path.join(path, "manga_info.json")
                title_no = series_name = display_title = author = genre = url = None
                num_chapters = 0
                chapters = []
                if os.path.exists(chapter_json):
                    try:
                        with open(chapter_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            title_no = data.get("title_no")
                            series_name = data.get("series_name")
                            url = data.get("chapters", [None])[0]
                            num_chapters = data.get("total_chapters", 0)
                            for link in data.get("chapters", []):
                                ep, ch_title = webtoon_scraper.extract_chapter_info(link)
                                chapters.append({'episode_no': ep, 'chapter_title': ch_title, 'url': link})
                    except Exception:
                        pass
                # Fallback: count episode folders
                if not num_chapters:
                    try:
                        num_chapters = len([d for d in os.listdir(path) if d.lower().startswith("episode_") and os.path.isdir(os.path.join(path, d))])
                    except Exception:
                        num_chapters = 0
                if os.path.exists(info_json):
                    try:
                        with open(info_json, "r", encoding="utf-8") as f:
                            info = json.load(f)
                            display_title = info.get("display_name", name)
                    except Exception:
                        display_title = name
                else:
                    display_title = name
                # Author/genre unknown for legacy downloads
                author = author or "Unknown"
                genre = genre or "Unknown"
                # Insert/update manga in DB
                db_utils.init_db()
                manga_id = db_utils.insert_or_update_manga(
                    title_no or "", series_name or name, display_title, author, genre, num_chapters, url or ""
                )
                if chapters:
                    db_utils.insert_chapters(manga_id, chapters)
                count += 1
        self.db_status_var.set(f"Scan complete. {count} manga processed.")
        self.query_all_manga()

    def choose_directory(self):
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            self.dir_label.config(text=directory)
            self.load_downloaded_manga()

    def create_db_tab(self):
        # Section Header
        tk.Label(self.db_tab, text="Manga Database", font=("Helvetica", 15, "bold"), fg=BLACK, bg=HIGHLIGHT, pady=5).pack(fill=tk.X, pady=(0, 8))
        # Query frame
        query_frame = tk.Frame(self.db_tab, bg=BLACK)
        query_frame.pack(fill=tk.X, padx=10, pady=5)
        # Genre
        tk.Label(query_frame, text="Genre:", font=FONT, fg=WHITE, bg=BLACK).grid(row=0, column=0, sticky="e")
        self.db_genre_entry = tk.Entry(query_frame, font=FONT, width=15, bg=WHITE, fg=BLACK)
        self.db_genre_entry.grid(row=0, column=1, padx=2)
        genre_btn = tk.Button(query_frame, text="Search", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.query_by_genre)
        genre_btn.grid(row=0, column=2, padx=2)
        self._add_hover_effect(genre_btn)
        # Author
        tk.Label(query_frame, text="Author:", font=FONT, fg=WHITE, bg=BLACK).grid(row=0, column=3, sticky="e")
        self.db_author_entry = tk.Entry(query_frame, font=FONT, width=15, bg=WHITE, fg=BLACK)
        self.db_author_entry.grid(row=0, column=4, padx=2)
        author_btn = tk.Button(query_frame, text="Search", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.query_by_author)
        author_btn.grid(row=0, column=5, padx=2)
        self._add_hover_effect(author_btn)
        # Title
        tk.Label(query_frame, text="Title:", font=FONT, fg=WHITE, bg=BLACK).grid(row=1, column=0, sticky="e")
        self.db_title_entry = tk.Entry(query_frame, font=FONT, width=15, bg=WHITE, fg=BLACK)
        self.db_title_entry.grid(row=1, column=1, padx=2)
        title_btn = tk.Button(query_frame, text="Search", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.query_by_title)
        title_btn.grid(row=1, column=2, padx=2)
        self._add_hover_effect(title_btn)
        # Min chapters
        tk.Label(query_frame, text="Min Chapters:", font=FONT, fg=WHITE, bg=BLACK).grid(row=1, column=3, sticky="e")
        self.db_min_chapters_entry = tk.Entry(query_frame, font=FONT, width=8, bg=WHITE, fg=BLACK)
        self.db_min_chapters_entry.grid(row=1, column=4, padx=2)
        min_ch_btn = tk.Button(query_frame, text="Search", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.query_by_min_chapters)
        min_ch_btn.grid(row=1, column=5, padx=2)
        self._add_hover_effect(min_ch_btn)
        # All manga
        all_btn = tk.Button(query_frame, text="Show All", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.query_all_manga)
        all_btn.grid(row=2, column=0, columnspan=2, pady=4)
        self._add_hover_effect(all_btn)
        # Scan button
        scan_btn = tk.Button(query_frame, text="Scan Downloaded Manga", font=FONT, bg=HIGHLIGHT, fg=BLACK, command=self.scan_downloaded_manga)
        scan_btn.grid(row=2, column=3, columnspan=3, pady=4)
        self._add_hover_effect(scan_btn)
        # Results Treeview
        columns = ("Title", "Author", "Genre", "Chapters", "Grade", "Views", "Subscribers", "Day Info", "Last Updated", "URL")
        self.db_tree = ttk.Treeview(self.db_tab, columns=columns, show="headings", height=15)
        for col in columns:
            self.db_tree.heading(col, text=col)
            self.db_tree.column(col, width=100, anchor="center")
        self.db_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        # Status bar
        self.db_status_var = tk.StringVar(value="Ready.")
        tk.Label(self.db_tab, textvariable=self.db_status_var, font=("Helvetica", 9), fg=WHITE, bg=BLACK).pack(fill=tk.X, pady=(0, 5))

if __name__ == "__main__":
    app = WebtoonScraperTabbedGUI()
    app.mainloop() 

    