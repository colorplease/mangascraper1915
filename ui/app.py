"""
Main application class for the webtoon scraper GUI.

This module coordinates all UI components and manages the application lifecycle.
"""

import tkinter as tk
from tkinter import messagebox

from .manga_view import MangaViewPanel
from .download_panel import DownloadPanel
from .database_panel import DatabasePanel
from utils.config import Config
from utils.db_manager import DatabaseManager
from controllers.manga_controller import MangaController
from controllers.download_controller import DownloadController


class WebtoonScraperApp(tk.Tk):
    """Main application window for the webtoon scraper."""
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        
        # Application setup
        self.title(Config.APP_NAME)
        self.geometry(f"{Config.UI_CONFIG['window_size'][0]}x{Config.UI_CONFIG['window_size'][1]}")
        self.configure(bg=Config.UI_COLORS['BLACK'])
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        
        # Initialize controllers (MVC pattern)
        self.manga_controller = MangaController(self.db_manager)
        self.download_controller = DownloadController(self.db_manager)
        
        # Validate controller types before proceeding
        if not hasattr(self.manga_controller, 'load_downloaded_manga'):
            raise TypeError(f"manga_controller is wrong type: {type(self.manga_controller)}")
        if not hasattr(self.download_controller, 'fetch_chapters'):
            raise TypeError(f"download_controller is wrong type: {type(self.download_controller)}")
        
        # Initialize UI components
        self.setup_ui()
        
        # Load initial data
        self.load_initial_data()
    
    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Create main title
        title_label = tk.Label(
            self,
            text=Config.APP_NAME,
            font=Config.UI_FONTS['LARGE_TITLE'],
            fg=Config.UI_COLORS['BLACK'],
            bg=Config.UI_COLORS['HIGHLIGHT'],
            pady=10
        )
        title_label.pack(fill=tk.X, pady=(0, 10))
        
        # Create notebook for tabs
        from tkinter import ttk
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create manga view panel (pass controller)
        self.manga_view = MangaViewPanel(self.notebook, self.manga_controller)
        self.notebook.add(self.manga_view, text="Downloaded Manga")
        
        # Create download panel (pass controller)
        self.download_panel = DownloadPanel(self.notebook, self.download_controller)
        self.notebook.add(self.download_panel, text="Download Manga")
        
        # Create database panel
        self.database_panel = DatabasePanel(self.notebook, self.db_manager)
        self.notebook.add(self.database_panel, text="Database")
        
        # Set up event bindings
        self.setup_event_bindings()
        
        # Bind tab selection events
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    

    
    def setup_event_bindings(self) -> None:
        """Set up event bindings between components using controllers."""
        # Create a wrapper function that calls both callbacks when manga is selected
        def on_manga_selected_wrapper(manga):
            """Wrapper to handle manga selection for both download controller and UI."""
            # Update download controller context
            if hasattr(self.download_controller, 'set_current_manga'):
                self.download_controller.set_current_manga(manga)
            
            # Update manga view UI (this was being overwritten before!)
            if hasattr(self.manga_view, 'on_manga_selected_internal'):
                self.manga_view.on_manga_selected_internal(manga)
        
        # Set the wrapper as the callback
        self.manga_controller.on_manga_selected = on_manga_selected_wrapper
        
        # When download completes, refresh manga data
        self.download_controller.on_download_complete = lambda success, msg: self.manga_controller.refresh_manga_data()
    
    def on_tab_changed(self, event) -> None:
        """Handle tab change events."""
        try:
            # Get the currently selected tab
            selected_tab = self.notebook.select()
            tab_text = self.notebook.tab(selected_tab, "text")
            
            # If database tab is selected, trigger auto-sync (verify + scan)
            if tab_text == "Database":
                # Use after() to ensure the tab is fully loaded
                self.after(100, self.database_panel.auto_verify_database)
                
        except Exception as e:
            print(f"Error handling tab change: {e}")
    
    def load_initial_data(self) -> None:
        """Load initial data for the application."""
        try:
            # Load manga data using controller
            self.manga_controller.load_downloaded_manga()
            
            # Show all manga in database panel
            self.database_panel.show_all_manga()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load initial data: {e}")
    
    def run(self) -> None:
        """Run the application."""
        try:
            self.mainloop()
        except KeyboardInterrupt:
            self.quit()
        except Exception as e:
            messagebox.showerror("Error", f"Application error: {e}")
            self.quit()
    
    def quit(self) -> None:
        """Quit the application."""
        try:
            # Clean up controllers
            if hasattr(self, 'download_controller'):
                self.download_controller.cleanup()
            
            # Clean up UI components
            if hasattr(self, 'download_panel'):
                self.download_panel.cleanup()
            
            # Close database connection
            if hasattr(self, 'db_manager'):
                # Database manager doesn't need explicit cleanup with context managers
                pass
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            self.destroy()


def main():
    """Main entry point for the GUI application."""
    try:
        # Validate configuration
        if not Config.validate_config():
            print("Configuration validation failed. Please check your settings.")
            return
        
        # Create and run the application
        app = WebtoonScraperApp()
        app.run()
        
    except Exception as e:
        print(f"Failed to start application: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 