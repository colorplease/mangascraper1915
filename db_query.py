#!/usr/bin/env python3
"""
Database Query CLI for Webtoon Scraper

This module provides a comprehensive command-line interface for querying
and managing the manga database with advanced search capabilities.
"""

import argparse
import sys
import json
from typing import List, Dict, Any, Optional

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

from datetime import datetime

from utils.db_manager import DatabaseManager
from models.manga import Manga
from models.chapter import Chapter


class DatabaseQueryCLI:
    """Command-line interface for database queries."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def format_manga_table(self, manga_list: List[Manga], detailed: bool = False) -> str:
        """Format manga list as a table."""
        if not manga_list:
            return "No manga found."
        
        if detailed:
            headers = ["ID", "Title", "Author", "Genre", "Chapters", "Grade", "Views", "Subscribers", "Day", "Last Updated"]
            data = []
            for manga in manga_list:
                data.append([
                    manga.id or "N/A",
                    (manga.display_title or manga.series_name)[:40] + ("..." if len(manga.display_title or manga.series_name or "") > 40 else ""),
                    (manga.author or "Unknown")[:25] + ("..." if len(manga.author or "") > 25 else ""),
                    manga.genre or "Unknown",
                    manga.num_chapters or 0,
                    f"{manga.grade:.1f}" if manga.grade else "N/A",
                    manga.views or "N/A",
                    manga.subscribers or "N/A",
                    manga.day_info or "N/A",
                    manga.last_updated.strftime("%Y-%m-%d") if manga.last_updated else "N/A"
                ])
        else:
            headers = ["ID", "Title", "Author", "Genre", "Chapters"]
            data = []
            for manga in manga_list:
                data.append([
                    manga.id or "N/A",
                    (manga.display_title or manga.series_name)[:50] + ("..." if len(manga.display_title or manga.series_name or "") > 50 else ""),
                    (manga.author or "Unknown")[:30] + ("..." if len(manga.author or "") > 30 else ""),
                    manga.genre or "Unknown",
                    manga.num_chapters or 0
                ])
        
        if TABULATE_AVAILABLE:
            return tabulate(data, headers=headers, tablefmt="grid")
        else:
            # Fallback simple table format
            result = " | ".join(headers) + "\n"
            result += "-" * len(result) + "\n"
            for row in data:
                result += " | ".join(str(cell) for cell in row) + "\n"
            return result
    
    def format_manga_json(self, manga_list: List[Manga]) -> str:
        """Format manga list as JSON."""
        data = []
        for manga in manga_list:
            manga_dict = {
                "id": manga.id,
                "title_no": manga.title_no,
                "series_name": manga.series_name,
                "display_title": manga.display_title,
                "author": manga.author,
                "genre": manga.genre,
                "num_chapters": manga.num_chapters,
                "url": manga.url,
                "grade": manga.grade,
                "views": manga.views,
                "subscribers": manga.subscribers,
                "day_info": manga.day_info,
                "last_updated": manga.last_updated.isoformat() if manga.last_updated else None
            }
            if hasattr(manga, 'chapters') and manga.chapters:
                manga_dict["chapters"] = [
                    {
                        "episode_no": ch.episode_no,
                        "title": ch.title,
                        "url": ch.url
                    } for ch in manga.chapters
                ]
            data.append(manga_dict)
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def search_by_title(self, title: str, detailed: bool = False, output_format: str = "table") -> str:
        """Search manga by title."""
        results = self.db_manager.search_manga_by_title(title)
        
        if output_format == "json":
            return self.format_manga_json(results)
        else:
            result_str = f"Found {len(results)} manga with title containing '{title}':\n\n"
            result_str += self.format_manga_table(results, detailed)
            return result_str
    
    def search_by_author(self, author: str, detailed: bool = False, output_format: str = "table") -> str:
        """Search manga by author."""
        results = self.db_manager.search_manga_by_author(author)
        
        if output_format == "json":
            return self.format_manga_json(results)
        else:
            result_str = f"Found {len(results)} manga by authors containing '{author}':\n\n"
            result_str += self.format_manga_table(results, detailed)
            return result_str
    
    def search_by_genre(self, genre: str, detailed: bool = False, output_format: str = "table") -> str:
        """Search manga by genre."""
        results = self.db_manager.search_manga_by_genre(genre)
        
        if output_format == "json":
            return self.format_manga_json(results)
        else:
            result_str = f"Found {len(results)} manga with genre containing '{genre}':\n\n"
            result_str += self.format_manga_table(results, detailed)
            return result_str
    
    def search_by_min_chapters(self, min_chapters: int, detailed: bool = False, output_format: str = "table") -> str:
        """Search manga by minimum chapters."""
        results = self.db_manager.search_manga_by_min_chapters(min_chapters)
        
        if output_format == "json":
            return self.format_manga_json(results)
        else:
            result_str = f"Found {len(results)} manga with {min_chapters}+ chapters:\n\n"
            result_str += self.format_manga_table(results, detailed)
            return result_str
    
    def get_all_manga(self, detailed: bool = False, output_format: str = "table") -> str:
        """Get all manga from database."""
        results = self.db_manager.get_all_manga()
        
        if output_format == "json":
            return self.format_manga_json(results)
        else:
            result_str = f"All {len(results)} manga in database:\n\n"
            result_str += self.format_manga_table(results, detailed)
            return result_str
    
    def get_manga_by_id(self, manga_id: int, output_format: str = "table") -> str:
        """Get detailed manga information by ID."""
        manga = self.db_manager.get_manga_by_id(manga_id)
        
        if not manga:
            return f"No manga found with ID {manga_id}"
        
        if output_format == "json":
            return self.format_manga_json([manga])
        
        # Detailed view
        info = f"Manga Details (ID: {manga.id}):\n"
        info += "=" * 50 + "\n"
        info += f"Title: {manga.display_title or manga.series_name}\n"
        info += f"Series Name: {manga.series_name}\n"
        info += f"Title No: {manga.title_no}\n"
        info += f"Author: {manga.author or 'Unknown'}\n"
        info += f"Genre: {manga.genre or 'Unknown'}\n"
        info += f"Total Chapters: {manga.num_chapters or 0}\n"
        info += f"Grade: {manga.grade if manga.grade else 'N/A'}\n"
        info += f"Views: {manga.views or 'N/A'}\n"
        info += f"Subscribers: {manga.subscribers or 'N/A'}\n"
        info += f"Day Info: {manga.day_info or 'N/A'}\n"
        info += f"URL: {manga.url or 'N/A'}\n"
        info += f"Last Updated: {manga.last_updated.strftime('%Y-%m-%d %H:%M:%S') if manga.last_updated else 'N/A'}\n"
        
        if hasattr(manga, 'chapters') and manga.chapters:
            info += f"\nChapters ({len(manga.chapters)}):\n"
            info += "-" * 30 + "\n"
            for chapter in manga.chapters[:10]:  # Show first 10 chapters
                info += f"Episode {chapter.episode_no}: {chapter.title}\n"
            if len(manga.chapters) > 10:
                info += f"... and {len(manga.chapters) - 10} more chapters\n"
        
        return info
    
    def get_statistics(self) -> str:
        """Get database statistics."""
        stats = self.db_manager.get_download_statistics()
        
        # Get additional statistics
        all_manga = self.db_manager.get_all_manga()
        
        # Genre distribution
        genre_count = {}
        author_count = {}
        for manga in all_manga:
            genre = manga.genre or "Unknown"
            author = (manga.author or "Unknown").split(',')[0].strip()  # First author
            
            genre_count[genre] = genre_count.get(genre, 0) + 1
            author_count[author] = author_count.get(author, 0) + 1
        
        # Top genres and authors
        top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5]
        top_authors = sorted(author_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        result = "Database Statistics:\n"
        result += "=" * 30 + "\n"
        result += f"Total Manga: {stats['total_manga']}\n"
        result += f"Total Chapters: {stats['total_chapters']}\n"
        result += f"Average Chapters per Manga: {stats['average_chapters']}\n\n"
        
        result += "Top Genres:\n"
        result += "-" * 15 + "\n"
        for genre, count in top_genres:
            result += f"{genre}: {count} manga\n"
        
        result += "\nTop Authors:\n"
        result += "-" * 15 + "\n"
        for author, count in top_authors:
            result += f"{author[:30]}: {count} manga\n"
        
        return result
    
    def advanced_search(self, title: str = None, author: str = None, genre: str = None, 
                       min_chapters: int = None, max_chapters: int = None,
                       min_grade: float = None, detailed: bool = False, 
                       output_format: str = "table") -> str:
        """Advanced search with multiple criteria."""
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
        
        if output_format == "json":
            return self.format_manga_json(results)
        else:
            criteria = []
            if title: criteria.append(f"title contains '{title}'")
            if author: criteria.append(f"author contains '{author}'")
            if genre: criteria.append(f"genre contains '{genre}'")
            if min_chapters: criteria.append(f"chapters >= {min_chapters}")
            if max_chapters: criteria.append(f"chapters <= {max_chapters}")
            if min_grade: criteria.append(f"grade >= {min_grade}")
            
            criteria_str = " AND ".join(criteria) if criteria else "no filters"
            result_str = f"Advanced search ({criteria_str}):\n"
            result_str += f"Found {len(results)} matching manga:\n\n"
            result_str += self.format_manga_table(results, detailed)
            return result_str
    
    def scan_downloaded_manga(self) -> str:
        """Scan downloaded manga folders and update database."""
        try:
            count = self.db_manager.scan_downloaded_manga("")
            return f"Successfully scanned and added {count} manga to the database."
        except Exception as e:
            return f"Error scanning downloaded manga: {e}"
    
    def verify_database(self) -> str:
        """Verify database against downloaded manga and remove entries for deleted manga."""
        try:
            results = self.db_manager.verify_and_cleanup_database()
            
            output = "Database Verification Results:\n"
            output += "=" * 40 + "\n\n"
            output += f"Total manga checked: {results['total_checked']}\n"
            output += f"Verified (folder exists): {results['verified_count']}\n"
            output += f"Deleted (missing folders): {results['deleted_count']}\n\n"
            
            if results['missing_folders']:
                output += "Removed from database (missing folders):\n"
                output += "-" * 40 + "\n"
                for item in results['missing_folders']:
                    manga = item['manga']
                    output += f"- {manga.display_title or manga.series_name}\n"
                    output += f"  Expected folder: {item['expected_folder']}\n"
            else:
                output += "All manga folders verified successfully!\n"
            
            return output
            
        except Exception as e:
            return f"Error verifying database: {e}"
    
    def sync_database(self) -> str:
        """Complete database synchronization: verify existing and scan for new manga."""
        try:
            results = self.db_manager.sync_database_with_downloads()
            
            cleanup = results['cleanup_results']
            new_count = results['new_manga_added']
            stats = results['final_stats']
            
            output = "Complete Database Synchronization Results:\n"
            output += "=" * 50 + "\n\n"
            
            output += "CLEANUP PHASE:\n"
            output += f"- Total manga checked: {cleanup['total_checked']}\n"
            output += f"- Verified (folders exist): {cleanup['verified_count']}\n"
            output += f"- Deleted (missing folders): {cleanup['deleted_count']}\n\n"
            
            output += "SCAN PHASE:\n"
            output += f"- New manga added: {new_count}\n\n"
            
            output += "FINAL DATABASE STATS:\n"
            output += f"- Total manga: {stats['total_manga']}\n"
            output += f"- Total chapters: {stats['total_chapters']}\n"
            output += f"- Average chapters per manga: {stats['average_chapters']}\n\n"
            
            if cleanup['missing_folders']:
                output += "Removed manga (missing folders):\n"
                output += "-" * 30 + "\n"
                for item in cleanup['missing_folders']:
                    manga = item['manga']
                    output += f"- {manga.display_title or manga.series_name}\n"
            
            return output
            
        except Exception as e:
            return f"Error synchronizing database: {e}"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Query and manage the webtoon manga database')
    
    # Output options
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                       help='Output format (default: table)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed information')
    
    # Search commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search by title
    title_parser = subparsers.add_parser('title', help='Search by title')
    title_parser.add_argument('query', help='Title to search for')
    
    # Search by author
    author_parser = subparsers.add_parser('author', help='Search by author')
    author_parser.add_argument('query', help='Author to search for')
    
    # Search by genre
    genre_parser = subparsers.add_parser('genre', help='Search by genre')
    genre_parser.add_argument('query', help='Genre to search for')
    
    # Search by minimum chapters
    chapters_parser = subparsers.add_parser('chapters', help='Search by minimum chapters')
    chapters_parser.add_argument('min_count', type=int, help='Minimum chapter count')
    
    # Get all manga
    subparsers.add_parser('all', help='Show all manga')
    
    # Get manga by ID
    id_parser = subparsers.add_parser('id', help='Get manga by ID')
    id_parser.add_argument('manga_id', type=int, help='Manga ID')
    
    # Statistics
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Advanced search
    advanced_parser = subparsers.add_parser('search', help='Advanced search with multiple criteria')
    advanced_parser.add_argument('--title', help='Title contains')
    advanced_parser.add_argument('--author', help='Author contains')
    advanced_parser.add_argument('--genre', help='Genre contains')
    advanced_parser.add_argument('--min-chapters', type=int, help='Minimum chapters')
    advanced_parser.add_argument('--max-chapters', type=int, help='Maximum chapters')
    advanced_parser.add_argument('--min-grade', type=float, help='Minimum grade')
    
    # Scan downloaded manga
    subparsers.add_parser('scan', help='Scan downloaded manga folders and update database')
    
    # Verify database
    subparsers.add_parser('verify', help='Verify database against downloaded manga and remove entries for deleted manga')
    
    # Sync database
    subparsers.add_parser('sync', help='Complete database synchronization (verify + scan)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = DatabaseQueryCLI()
    
    try:
        if args.command == 'title':
            result = cli.search_by_title(args.query, args.detailed, args.format)
        elif args.command == 'author':
            result = cli.search_by_author(args.query, args.detailed, args.format)
        elif args.command == 'genre':
            result = cli.search_by_genre(args.query, args.detailed, args.format)
        elif args.command == 'chapters':
            result = cli.search_by_min_chapters(args.min_count, args.detailed, args.format)
        elif args.command == 'all':
            result = cli.get_all_manga(args.detailed, args.format)
        elif args.command == 'id':
            result = cli.get_manga_by_id(args.manga_id, args.format)
        elif args.command == 'stats':
            result = cli.get_statistics()
        elif args.command == 'search':
            result = cli.advanced_search(
                title=args.title,
                author=args.author,
                genre=args.genre,
                min_chapters=args.min_chapters,
                max_chapters=args.max_chapters,
                min_grade=args.min_grade,
                detailed=args.detailed,
                output_format=args.format
            )
        elif args.command == 'scan':
            result = cli.scan_downloaded_manga()
        elif args.command == 'verify':
            result = cli.verify_database()
        elif args.command == 'sync':
            result = cli.sync_database()
        else:
            result = "Unknown command"
        
        print(result)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main() 