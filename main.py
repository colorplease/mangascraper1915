#!/usr/bin/env python3
"""
Main entry point for the Webtoon Scraper application.

This module provides the main entry point that handles both CLI and GUI modes
with proper module path setup.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path to enable imports
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import argparse
from typing import Optional

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Webtoon Scraper - Download webtoons with advanced features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --gui                    # Launch GUI
  python main.py "WEBTOON_URL"            # CLI mode - fetch chapters
  python main.py "WEBTOON_URL" --download # CLI mode - download chapters
  
For more CLI options, use: python main.py --cli --help
        """
    )
    
    parser.add_argument('--gui', action='store_true', 
                       help='Launch the graphical user interface')
    parser.add_argument('--cli', action='store_true',
                       help='Use command-line interface with full options')
    parser.add_argument('url', nargs='?', 
                       help='Webtoon URL (for quick CLI access)')
    parser.add_argument('--download', action='store_true',
                       help='Download chapters (quick CLI mode)')
    
    args = parser.parse_args()
    
    # If --gui is specified or no arguments given, launch GUI
    if args.gui or (not args.cli and not args.url):
        launch_gui()
    elif args.cli:
        # Launch full CLI with all options
        launch_full_cli()
    else:
        # Quick CLI mode with basic options
        launch_quick_cli(args.url, args.download)

def launch_gui():
    """Launch the GUI application."""
    try:
        from ui.app import WebtoonScraperApp
        
        print("Starting Webtoon Scraper GUI...")
        app = WebtoonScraperApp()
        app.run()
        
    except ImportError as e:
        print(f"Error importing GUI components: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching GUI: {e}")
        sys.exit(1)

def launch_full_cli():
    """Launch the full CLI with all options."""
    try:
        # Import and run the full CLI
        from cli import main as cli_main
        cli_main()
        
    except ImportError as e:
        print(f"Error importing CLI components: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching CLI: {e}")
        sys.exit(1)

def launch_quick_cli(url: Optional[str], download: bool):
    """Launch quick CLI mode with basic options."""
    try:
        from cli import main as cli_main
        
        # Modify sys.argv to pass arguments to CLI
        original_argv = sys.argv.copy()
        sys.argv = ['cli.py']
        
        if url:
            sys.argv.append(url)
        if download:
            sys.argv.append('--download')
            
        try:
            cli_main()
        finally:
            # Restore original argv
            sys.argv = original_argv
            
    except ImportError as e:
        print(f"Error importing CLI components: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching CLI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 