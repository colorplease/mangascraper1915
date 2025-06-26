#!/usr/bin/env python3
"""
Command-line interface for the webtoon scraper.

This module provides a CLI that replicates all functionality from the original
webtoon_scraper.py with the new modular architecture.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional

from models.manga import Manga
from models.chapter import Chapter
from scraper.webtoon_client import WebtoonClient
from scraper.parsers import create_manga_from_page, create_chapters_from_links, parse_chapter_links
from scraper.downloader import DownloadManager, DownloadProgress
from scraper.comment_analyzer import CommentAnalyzer
from utils.config import Config
from utils.db_manager import DatabaseManager


def extract_webtoon_info(url: str) -> tuple[str, str]:
    """Extract title_no and series name from URL."""
    from urllib.parse import urlparse, parse_qs
    
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    title_no = query_params.get('title_no', [''])[0]
    
    path_segments = parsed_url.path.strip('/').split('/')
    if len(path_segments) >= 3:
        series_name = path_segments[2]
    else:
        series_name = "unknown"
    
    return title_no, series_name


def get_chapter_links(url: str, client: WebtoonClient) -> List[str]:
    """Get all chapter links from a webtoon page."""
    print(f"Fetching chapter links from: {url}")
    
    # Normalize URL to list page
    normalized_url = client.normalize_list_url(url)
    
    # Get initial page
    soup = client.get_page(normalized_url)
    if not soup:
        print("Failed to fetch the page")
        return []
    
    # Get all pages with pagination
    title_no, _ = extract_webtoon_info(normalized_url)
    all_pages = client.get_paginated_content(
        normalized_url.split('?')[0], title_no
    )
    
    # Collect all chapter links
    all_chapter_links = []
    for page_soup in all_pages:
        links = parse_chapter_links(page_soup)
        all_chapter_links.extend(links)
    
    print(f"Found {len(all_chapter_links)} chapter links")
    return all_chapter_links


def prompt_for_chapter_selection(chapters: List[Chapter]) -> List[Chapter]:
    """Prompt user to select which chapters to download."""
    print("\nAvailable chapters:")
    
    # Sort by episode number (newest first)
    sorted_chapters = sorted(chapters, key=lambda x: int(x.episode_no), reverse=True)
    
    # Display chapters
    for i, chapter in enumerate(sorted_chapters):
        print(f"{i+1}. Episode {chapter.episode_no}: {chapter.title}")
    
    print("\nSelect chapters to download:")
    print("Options:")
    print("  - Enter chapter numbers separated by commas (e.g., '1,3,5')")
    print("  - Enter a range (e.g., '1-5')")
    print("  - Enter 'all' to download all chapters")
    print("  - Enter 'q' to quit")
    
    selection = input("\nEnter your selection: ").strip().lower()
    
    if selection == 'q':
        return []
    
    if selection == 'all':
        return sorted_chapters
    
    selected_chapters = []
    
    # Process comma-separated values and ranges
    parts = selection.split(',')
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if 1 <= start <= len(sorted_chapters) and 1 <= end <= len(sorted_chapters):
                    for i in range(start, end + 1):
                        selected_chapters.append(sorted_chapters[i-1])
            except ValueError:
                print(f"Invalid range: {part}")
        else:
            try:
                idx = int(part)
                if 1 <= idx <= len(sorted_chapters):
                    selected_chapters.append(sorted_chapters[idx-1])
                else:
                    print(f"Chapter number {idx} is out of range")
            except ValueError:
                print(f"Invalid chapter number: {part}")
    
    return selected_chapters


def save_manga_data(manga: Manga, output_dir: str) -> str:
    """Save manga data to files."""
    manga_folder = Path(output_dir) / f"webtoon_{manga.title_no}_{manga.series_name}"
    manga_folder.mkdir(exist_ok=True)
    
    # Save manga info
    info_file = manga_folder / "manga_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        import json
        json.dump(manga.to_dict(), f, indent=2)
    
    # Save chapter links
    chapter_data = {
        "title_no": manga.title_no,
        "series_name": manga.series_name,
        "total_chapters": len(manga.chapters),
        "chapters": [chapter.url for chapter in manga.chapters]
    }
    chapter_file = manga_folder / "chapter_links.json"
    with open(chapter_file, 'w', encoding='utf-8') as f:
        import json
        json.dump(chapter_data, f, indent=2)
    
    print(f"Saved manga data to: {manga_folder}")
    return str(manga_folder)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Scrape chapter links and images from a Webtoon series')
    parser.add_argument('url', nargs='?', help='URL of the Webtoon series page')
    parser.add_argument('--download', action='store_true', help='Download chapter images')
    parser.add_argument('--output', '-o', default='webtoon_downloads', help='Output directory (default: webtoon_downloads)')
    parser.add_argument('--threads', '-t', type=int, default=20, help='Number of download threads (default: 20)')
    parser.add_argument('--no-selenium', action='store_true', help='Disable Selenium (faster but may miss comments)')
    parser.add_argument('--no-comments', action='store_true', help='Skip comment extraction')
    parser.add_argument('--gui', action='store_true', help='Launch GUI instead of CLI')
    parser.add_argument('--db-query', action='store_true', help='Launch database query interface')
    parser.add_argument('--db-stats', action='store_true', help='Show database statistics')
    
    args = parser.parse_args()
    
    # Launch GUI if requested
    if args.gui:
        try:
            from ui.app import WebtoonScraperApp
            app = WebtoonScraperApp()
            app.run()
        except ImportError as e:
            print(f"Error importing GUI: {e}")
            print("Make sure all dependencies are installed: pip install -r requirements.txt")
            sys.exit(1)
        return
    
    # Database query interface
    if args.db_query:
        try:
            from db_query import DatabaseQueryCLI
            cli = DatabaseQueryCLI()
            print("Database Query Interface")
            print("=" * 30)
            print("Available commands:")
            print("  stats     - Show database statistics")
            print("  all       - Show all manga")
            print("  search    - Search manga")
            print("  verify    - Verify database and remove deleted manga")
            print("  sync      - Full synchronization (verify + scan)")
            print("  help      - Show help")
            print("  quit      - Exit")
            print()
            
            while True:
                try:
                    command = input("db> ").strip().lower()
                    if command in ['quit', 'exit', 'q']:
                        break
                    elif command == 'stats':
                        print(cli.get_statistics())
                    elif command == 'all':
                        print(cli.get_all_manga())
                    elif command == 'verify':
                        print(cli.verify_database())
                    elif command == 'sync':
                        print(cli.sync_database())
                    elif command.startswith('search'):
                        parts = command.split()
                        if len(parts) >= 3:
                            search_type = parts[1]
                            query = ' '.join(parts[2:])
                            if search_type == 'title':
                                print(cli.search_by_title(query))
                            elif search_type == 'author':
                                print(cli.search_by_author(query))
                            elif search_type == 'genre':
                                print(cli.search_by_genre(query))
                            else:
                                print("Usage: search [title|author|genre] <query>")
                        else:
                            print("Usage: search [title|author|genre] <query>")
                    elif command == 'help':
                        print("Commands:")
                        print("  stats                    - Database statistics")
                        print("  all                      - Show all manga")
                        print("  search title <query>     - Search by title")
                        print("  search author <query>    - Search by author")
                        print("  search genre <query>     - Search by genre")
                        print("  verify                   - Verify database and remove deleted manga")
                        print("  sync                     - Full synchronization (verify + scan)")
                        print("  quit                     - Exit")
                    else:
                        print("Unknown command. Type 'help' for available commands.")
                    print()
                except (KeyboardInterrupt, EOFError):
                    break
            
            print("Goodbye!")
        except ImportError as e:
            print(f"Error importing database query: {e}")
            sys.exit(1)
        return
    
    # Show database statistics if requested
    if args.db_stats:
        try:
            from db_query import DatabaseQueryCLI
            cli = DatabaseQueryCLI()
            print(cli.get_statistics())
        except ImportError as e:
            print(f"Error importing database query: {e}")
            sys.exit(1)
        return
    
    # Get URL if not provided
    url = args.url
    if not url:
        url = input("Please enter the URL of the Webtoon series: ").strip()
        if not url:
            print("No URL provided. Exiting.")
            sys.exit(1)
    
    # Initialize components
    use_selenium = not args.no_selenium
    client = WebtoonClient(use_selenium=use_selenium)
    db_manager = DatabaseManager()
    
    try:
        # Get chapter links
        chapter_links = get_chapter_links(url, client)
        if not chapter_links:
            print("No chapter links found.")
            sys.exit(1)
        
        # Get initial page for manga metadata
        normalized_url = client.normalize_list_url(url)
        soup = client.get_page(normalized_url)
        
        # Create manga object
        manga = create_manga_from_page(soup, normalized_url)
        manga.chapters = create_chapters_from_links(chapter_links)
        manga.num_chapters = len(manga.chapters)
        
        # Save manga data
        output_dir = save_manga_data(manga, args.output)
        
        # Save to database
        db_manager.save_manga(manga)
        print(f"Saved manga '{manga.display_title}' to database")
        
        # Download if requested
        download_images = args.download
        if not download_images:
            choice = input("\nDo you want to download chapter images? (y/n): ").strip().lower()
            download_images = choice.startswith('y')
        
        if download_images:
            # Let user select chapters
            selected_chapters = prompt_for_chapter_selection(manga.chapters)
            
            if not selected_chapters:
                print("No chapters selected for download.")
                return
            
            print(f"\nDownloading {len(selected_chapters)} chapters...")
            
            # Initialize download manager
            extract_comments = not args.no_comments
            download_manager = DownloadManager(
                use_selenium=use_selenium,
                max_workers=args.threads,
                extract_comments=extract_comments
            )
            
            # Progress callback
            def progress_callback(progress: DownloadProgress):
                percent = (progress.completed_items / progress.total_items) * 100
                print(f"Progress: [{progress.completed_items}/{progress.total_items}] {percent:.1f}%")
            
            try:
                # Download chapters
                results = download_manager.download_manga_chapters(
                    manga, selected_chapters, output_dir, progress_callback
                )
                
                # Report results
                total_images = sum(results.values())
                failed_chapters = [url for url, count in results.items() if count == 0]
                
                print(f"\nDownload complete!")
                print(f"Downloaded {total_images} images across {len(selected_chapters)} chapters")
                
                if failed_chapters:
                    print(f"Failed to download {len(failed_chapters)} chapters")
                
                print(f"Files saved to: {output_dir}")
                
            finally:
                download_manager.close()
        
    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main() 