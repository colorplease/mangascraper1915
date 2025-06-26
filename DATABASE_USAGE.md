# Database Query System Documentation

The Webtoon Scraper includes a comprehensive database system for storing and querying manga information. This document covers all available database functionality.

## Database Structure

The database stores manga and chapter information with the following schema:

### Manga Table
- `id` - Primary key
- `title_no` - Webtoon title number
- `series_name` - URL-friendly series name
- `display_title` - Human-readable title
- `author` - Author(s) information
- `genre` - Genre classification
- `num_chapters` - Total number of chapters
- `url` - Series URL
- `last_updated` - Last database update timestamp
- `grade` - User rating (if available)
- `views` - View count
- `subscribers` - Subscriber count
- `day_info` - Publication day information

### Chapters Table
- `id` - Primary key
- `manga_id` - Foreign key to manga table
- `episode_no` - Episode number
- `chapter_title` - Chapter title
- `url` - Chapter URL

## Command Line Tools

### 1. Dedicated Database Query Tool (`db_query.py`)

The main database query tool provides comprehensive search and analysis capabilities.

#### Basic Usage
```bash
python db_query.py <command> [options]
```

#### Available Commands

##### Show All Manga
```bash
python db_query.py all                    # Basic table view
python db_query.py all --detailed         # Detailed table view
python db_query.py --format json all      # JSON output
```

##### Search by Title
```bash
python db_query.py title "Hero"           # Search for manga with "Hero" in title
python db_query.py title "Mercenary" --detailed
```

##### Search by Author
```bash
python db_query.py author "SEOPASS"       # Search by author name
python db_query.py author "Kim" --format json
```

##### Search by Genre
```bash
python db_query.py genre "Action"         # Search by genre
python db_query.py genre "Fantasy" --detailed
```

##### Search by Chapter Count
```bash
python db_query.py chapters 30            # Manga with 30+ chapters
python db_query.py chapters 50 --detailed
```

##### Get Specific Manga Details
```bash
python db_query.py id 3                   # Get detailed info for manga ID 3
python db_query.py id 5 --format json     # JSON format
```

##### Advanced Multi-Criteria Search
```bash
# Search with multiple criteria
python db_query.py search --genre Action --min-chapters 30
python db_query.py search --title "Hero" --author "SEOPASS"
python db_query.py search --genre Fantasy --min-grade 8.0 --max-chapters 50
```

Available search criteria:
- `--title <text>` - Title contains text
- `--author <text>` - Author contains text  
- `--genre <text>` - Genre contains text
- `--min-chapters <num>` - Minimum chapter count
- `--max-chapters <num>` - Maximum chapter count
- `--min-grade <num>` - Minimum rating

##### Database Statistics
```bash
python db_query.py stats                  # Show database statistics
```

##### Scan Downloaded Manga
```bash
python db_query.py scan                   # Scan downloads folder and update DB
```

#### Output Formats

**Table Format (default):**
- Clean, formatted tables using tabulate library
- Automatically adjusts column widths
- Good for terminal viewing

**JSON Format:**
- Machine-readable JSON output
- Includes all available fields
- Perfect for scripting and data processing

```bash
# Examples
python db_query.py --format table all     # Table format
python db_query.py --format json all      # JSON format
```

### 2. Integrated CLI Commands

The main CLI includes integrated database functionality:

#### Quick Database Statistics
```bash
python cli.py --db-stats                  # Show database statistics
```

#### Interactive Database Query Interface
```bash
python cli.py --db-query                  # Launch interactive interface
```

Interactive commands:
- `stats` - Show database statistics
- `all` - Show all manga
- `search title <query>` - Search by title
- `search author <query>` - Search by author
- `search genre <query>` - Search by genre
- `help` - Show available commands
- `quit` - Exit interface

Example interactive session:
```
db> stats
Database Statistics:
==============================
Total Manga: 10
Total Chapters: 352
Average Chapters per Manga: 35.2

db> search genre Action
Found 4 manga with genre containing 'Action':
[Table output...]

db> quit
```

## Programming Interface

### DatabaseManager Class

For programmatic access, use the `DatabaseManager` class:

```python
from utils.db_manager import DatabaseManager

# Initialize database manager
db = DatabaseManager()

# Basic queries
all_manga = db.get_all_manga()
action_manga = db.search_manga_by_genre("Action")
hero_manga = db.search_manga_by_title("Hero")

# Advanced queries
top_rated = db.get_top_rated_manga(limit=5)
recent = db.get_recently_updated_manga(limit=10)
long_series = db.search_manga_by_min_chapters(50)

# Get specific manga with chapters
manga = db.get_manga_by_id(3)
manga_with_chapters = db.get_manga_by_title_no("1726")

# Statistics
stats = db.get_download_statistics()
genres = db.get_genres()
authors = db.get_authors()
```

### Available Methods

#### Search Methods
- `get_all_manga()` - Get all manga
- `search_manga_by_title(title)` - Search by title
- `search_manga_by_author(author)` - Search by author
- `search_manga_by_genre(genre)` - Search by genre
- `search_manga_by_min_chapters(min_chapters)` - Search by chapter count
- `search_manga_by_grade(min_grade)` - Search by minimum rating

#### Retrieval Methods
- `get_manga_by_id(manga_id)` - Get manga by database ID
- `get_manga_by_title_no(title_no)` - Get manga by webtoon title number
- `get_top_rated_manga(limit)` - Get highest rated manga
- `get_most_viewed_manga(limit)` - Get most viewed manga
- `get_recently_updated_manga(limit)` - Get recently updated manga
- `get_manga_by_day(day)` - Get manga by publication day

#### Utility Methods
- `get_download_statistics()` - Get database statistics
- `get_genres()` - Get all unique genres
- `get_authors()` - Get all unique authors
- `scan_downloaded_manga(downloads_dir)` - Scan and update from downloads

#### Data Management
- `save_manga(manga)` - Save/update manga in database
- `save_chapters(manga_id, chapters)` - Save chapters for manga
- `update_manga_download_status(manga_id, status)` - Update download status

## GUI Integration

The database functionality is fully integrated into the GUI through the Database tab:

### Database Panel Features
- **Search Controls**: Multiple search criteria (genre, author, title, min chapters)
- **Results Table**: Sortable table with all manga information
- **Quick Actions**: Double-click to view details
- **Scan Function**: Scan downloaded folders to update database
- **Status Bar**: Shows search results and operation status

### Using the GUI Database Panel
1. Open the GUI: `python run_gui.py`
2. Click the "Database" tab
3. Use search controls to find manga
4. View results in the table
5. Double-click entries for detailed view

## Data Sources

The database is automatically populated from:

1. **Manual Downloads**: When you download manga through the CLI or GUI
2. **Folder Scanning**: Use scan functions to import existing downloads
3. **Webtoon Metadata**: Extracted from webtoon pages during scraping

### Automatic Population
Every time you download a manga, the system automatically:
- Extracts metadata from the webtoon page
- Saves manga information to the database
- Creates chapter entries for all available chapters
- Updates existing entries if manga already exists

### Manual Population
Use the scan function to populate from existing downloads:
```bash
python db_query.py scan                   # Scan downloads folder
```

## Advanced Usage Examples

### Find Long-Running Action Series
```bash
python db_query.py search --genre Action --min-chapters 50 --detailed
```

### Export All Manga Data
```bash
python db_query.py --format json all > manga_backup.json
```

### Find Recently Updated Fantasy Manga
```python
from utils.db_manager import DatabaseManager
db = DatabaseManager()

# Get fantasy manga updated in the last month
fantasy_manga = db.search_manga_by_genre("Fantasy")
recent_fantasy = [m for m in fantasy_manga 
                  if m.last_updated and 
                  (datetime.now() - m.last_updated).days < 30]
```

### Get Statistics by Genre
```python
from utils.db_manager import DatabaseManager
from collections import Counter

db = DatabaseManager()
all_manga = db.get_all_manga()

# Genre distribution
genres = [m.genre for m in all_manga if m.genre]
genre_stats = Counter(genres)

print("Manga by Genre:")
for genre, count in genre_stats.most_common():
    print(f"{genre}: {count}")
```

## Database Maintenance

### Regular Maintenance Tasks

1. **Scan Downloads**: Regularly scan your downloads folder to keep the database up-to-date
2. **Check Statistics**: Monitor database growth and identify any data issues
3. **Backup Data**: Export important data using JSON format

### Troubleshooting

**Database not found:**
- The database is automatically created on first use
- Check that you're running commands from the correct directory

**Missing manga:**
- Use the scan function to import existing downloads
- Verify that manga folders follow the expected naming convention

**Slow queries:**
- The database uses SQLite which is efficient for the expected data size
- Consider the number of manga in your collection if performance degrades

## Integration with Other Tools

The database system integrates seamlessly with:

- **Download System**: Automatically populates during downloads
- **GUI Interface**: Full search and browse capabilities
- **Comment System**: Links to comment files in chapter folders
- **Banner System**: Associates with banner images in manga folders

This comprehensive database system provides powerful ways to organize, search, and analyze your webtoon collection! 