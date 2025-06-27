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
        print("Starting Webtoon Scraper GUI...")
        
        # Import and use the new MVC application
        from ui.app import main as gui_main
        gui_main()
        
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