#!/usr/bin/env python3
"""
Simple GUI launcher for the Webtoon Scraper.

This script handles the import issues and launches the GUI application.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    """Launch the GUI application."""
    try:
        # Import required modules
        import tkinter as tk
        from tkinter import messagebox, ttk
        
        # Import our modules
        from utils.config import Config
        from utils.db_manager import DatabaseManager
        from models.manga import Manga
        
        # Create a simple launcher window first
        print("Starting Webtoon Scraper GUI...")
        
        # Import and create the main application
        from ui.manga_view import MangaViewPanel
        from ui.download_panel import DownloadPanel  
        from ui.database_panel import DatabasePanel
        
        class WebtoonScraperApp(tk.Tk):
            """Main application window for the Webtoon Scraper."""
            
            def __init__(self):
                super().__init__()
                self.title("Webtoon Scraper")
                self.geometry("1000x800")
                self.configure(bg=Config.UI_COLORS['BLACK'])
                
                # Initialize database
                self.db_manager = DatabaseManager()
                
                # Create UI
                self.create_widgets()
                
                # Set up protocol for window closing
                self.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            def create_widgets(self):
                """Create the main UI widgets."""
                # App title
                title_label = tk.Label(
                    self,
                    text="Webtoon Scraper",
                    font=("Helvetica", 22, "bold"),
                    fg=Config.UI_COLORS['BLACK'],
                    bg=Config.UI_COLORS['HIGHLIGHT'],
                    pady=10
                )
                title_label.pack(fill=tk.X, pady=(0, 10))
                
                # Create notebook for tabs
                self.notebook = ttk.Notebook(self)
                self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
                
                # Create tabs with actual panels
                try:
                    self.manga_view_panel = MangaViewPanel(self.notebook, self.db_manager)
                    self.notebook.add(self.manga_view_panel, text="Downloaded Manga")
                except Exception as e:
                    print(f"Error creating manga view panel: {e}")
                    # Create placeholder
                    placeholder = tk.Frame(self.notebook, bg=Config.UI_COLORS['BLACK'])
                    tk.Label(placeholder, text=f"Manga View Error: {e}", 
                            fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).pack(expand=True)
                    self.notebook.add(placeholder, text="Downloaded Manga")
                
                try:
                    self.download_panel = DownloadPanel(self.notebook, self.db_manager)
                    self.notebook.add(self.download_panel, text="Fetch Manga")
                except Exception as e:
                    print(f"Error creating download panel: {e}")
                    # Create placeholder
                    placeholder = tk.Frame(self.notebook, bg=Config.UI_COLORS['BLACK'])
                    tk.Label(placeholder, text=f"Download Panel Error: {e}",
                            fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).pack(expand=True)
                    self.notebook.add(placeholder, text="Fetch Manga")
                
                try:
                    self.database_panel = DatabasePanel(self.notebook, self.db_manager)
                    self.notebook.add(self.database_panel, text="Database")
                except Exception as e:
                    print(f"Error creating database panel: {e}")
                    # Create placeholder
                    placeholder = tk.Frame(self.notebook, bg=Config.UI_COLORS['BLACK'])
                    tk.Label(placeholder, text=f"Database Panel Error: {e}",
                            fg=Config.UI_COLORS['WHITE'], bg=Config.UI_COLORS['BLACK']).pack(expand=True)
                    self.notebook.add(placeholder, text="Database")
            
            def on_closing(self):
                """Handle application closing."""
                try:
                    # Clean up database connection
                    if hasattr(self, 'db_manager'):
                        pass  # DatabaseManager uses context managers
                except Exception as e:
                    print(f"Error during cleanup: {e}")
                finally:
                    self.destroy()
        
        # Create and run application
        app = WebtoonScraperApp()
        app.mainloop()
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 