# Webtoon Scraper

A powerful Python application for downloading webtoons from WEBTOONS with advanced features including comment analysis, banner extraction, download queue management, and database integration.

## ✨ Features

### Core Functionality
- **🎯 Smart Chapter Detection**: Automatically finds all chapters across paginated listings
- **📥 Batch Downloads**: Download multiple chapters with parallel processing
- **💾 Download Queue**: Resume interrupted downloads with queue management
- **📊 Progress Tracking**: Real-time progress with animated status indicators
- **🗃️ Database Integration**: SQLite database for manga metadata and search

### Advanced Features  
- **💬 Comment Analysis**: Extract and analyze reader comments with NLTK
- **🖼️ Banner Extraction**: Download layered banner images (background + foreground)
- **🔍 Smart Search**: Search by title, author, genre, or chapter count
- **📱 Dual Interface**: Both GUI and CLI interfaces available
- **🔄 Auto-Resume**: Failed downloads automatically preserved in queue
- **📋 Metadata Extraction**: Author, rating, views, subscribers, publication info

### Technical Features
- **🏗️ Modular Architecture**: Clean separation of concerns with organized packages
- **🚀 Selenium Integration**: Optional JavaScript rendering for complete comment extraction
- **⚡ Concurrent Downloads**: Multi-threaded image downloading
- **🛡️ Error Handling**: Robust error handling with retry mechanisms
- **📝 Comprehensive Logging**: Detailed logs for debugging and monitoring

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/webtoon-scraper.git
cd webtoon-scraper
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Optional: Install Selenium WebDriver** (for complete comment extraction):
```bash
# Chrome WebDriver (recommended)
pip install selenium
# Download ChromeDriver and add to PATH
```

### Basic Usage

#### GUI Interface (Recommended)
```bash
# Method 1: Simple GUI launcher
python run_gui.py

# Method 2: Main launcher with GUI option
python main.py --gui

# Method 3: Default (no arguments launches GUI)
python main.py
```

#### Command Line Interface
```bash
# Basic usage (main launcher)
python main.py "https://www.webtoons.com/en/romance/series-name/list?title_no=12345"

# Download with main launcher
python main.py "https://www.webtoons.com/en/romance/series-name/list?title_no=12345" --download

# Full CLI options
python main.py --cli --help
python cli.py "URL" --download --threads 30 --output my_downloads
```

## 📖 Detailed Usage Guide

### GUI Interface

The GUI provides three main tabs:

#### 1. Downloaded Manga Tab
- **📚 Manga Library**: Browse your downloaded manga collection
- **🖼️ Banner Display**: View layered banner images with automatic scaling
- **📊 Manga Info**: Author, rating, chapter counts, and metadata
- **💬 Comment Summaries**: Quick preview of comment analysis
- **📁 Quick Actions**: Open chapter folders and view full comments

#### 2. Fetch Manga Tab  
- **🔗 URL Input**: Enter webtoon series URLs
- **📋 Chapter Selection**: Multi-select chapters for download
- **⚙️ Download Controls**: Start downloads or resume from queue
- **📈 Progress Tracking**: Real-time download progress with percentage
- **🎯 Smart Filtering**: Hide already downloaded chapters

#### 3. Database Tab
- **🔍 Advanced Search**: Search by multiple criteria
- **📊 Manga Overview**: Sortable table with all manga metadata  
- **🔄 Sync Functions**: Scan downloaded folders to update database
- **📈 Statistics**: View your collection statistics

### CLI Interface

#### Basic Commands
```bash
# Show help
python main.py --help
python cli.py --help

# Launch GUI
python run_gui.py
python main.py --gui

# Fetch chapter list only
python main.py "WEBTOON_URL"

# Download all chapters  
python main.py "WEBTOON_URL" --download

# Download with custom settings
python cli.py "WEBTOON_URL" --download --threads 50 --output custom_folder
```

#### Advanced Options
```bash
# Disable Selenium (faster, may miss some comments)
python cli.py "WEBTOON_URL" --download --no-selenium

# Skip comment extraction entirely
python cli.py "WEBTOON_URL" --download --no-comments

# Custom thread count for downloads
python cli.py "WEBTOON_URL" --download --threads 30
```

## 🏗️ Architecture Overview

The application follows a clean modular architecture:

```
webtoon-scraper/
├── models/              # Data models
│   ├── manga.py        # Manga data model
│   └── chapter.py      # Chapter data model
├── scraper/            # Core scraping functionality
│   ├── webtoon_client.py    # HTTP client with session management
│   ├── parsers.py           # HTML parsing functions
│   ├── downloader.py        # Download management
│   └── comment_analyzer.py  # Comment extraction & analysis
├── ui/                 # User interface components
│   ├── app.py          # Main application
│   ├── manga_view.py   # Downloaded manga panel
│   ├── download_panel.py    # Download interface
│   └── database_panel.py    # Database management
├── utils/              # Utilities and configuration
│   ├── config.py       # Configuration management
│   └── db_manager.py   # Database operations
├── cli.py              # Command-line interface
└── requirements.txt    # Dependencies
```

### Key Components

#### Models (`models/`)
- **Manga**: Complete manga representation with metadata, chapters, and file system integration
- **Chapter**: Individual chapter with download tracking and comment storage

#### Scraper (`scraper/`)
- **WebtoonClient**: HTTP session management, cookie handling, Selenium integration
- **Parsers**: Specialized HTML parsing for different page types and content
- **Downloader**: Multi-threaded downloading with progress tracking and queue management
- **CommentAnalyzer**: NLTK-powered comment extraction with sentiment analysis

#### User Interface (`ui/`)
- **App**: Main application coordinator with tabbed interface
- **MangaView**: Downloaded manga browser with banner display
- **DownloadPanel**: URL fetching and download management
- **DatabasePanel**: Search and database management interface

#### Utils (`utils/`)
- **Config**: Centralized configuration with validation
- **DatabaseManager**: High-level database operations with ORM-like interface

## 📦 Dependencies

### Required
- `requests`: HTTP requests and session management
- `beautifulsoup4`: HTML parsing and content extraction
- `lxml`: Fast XML/HTML parser for BeautifulSoup
- `Pillow`: Image processing for banner display
- `nltk`: Natural language processing for comment analysis

### Optional
- `selenium`: Complete JavaScript rendering for comment extraction
- `webdriver-manager`: Automatic WebDriver management

### GUI Dependencies (Included in Python)
- `tkinter`: Cross-platform GUI framework
- `sqlite3`: Database functionality

## ⚙️ Configuration

### Settings File (`utils/config.py`)
- HTTP headers and user agents
- UI colors and fonts  
- Default worker thread counts
- File paths and directories
- Download settings

### Database (`manga_collection.db`)
- Automatic SQLite database creation
- Manga metadata storage
- Chapter tracking
- Search indexing

## 🔧 Advanced Features

### Download Queue Management
- **Automatic Queue Creation**: Selected chapters saved to queue on download start
- **Failure Preservation**: Queue preserved if downloads fail or are interrupted  
- **Resume Functionality**: One-click resume from where you left off
- **Smart Filtering**: Already downloaded chapters automatically excluded

### Comment Analysis
- **Multi-Strategy Parsing**: Multiple approaches to handle different comment formats
- **NLTK Integration**: Advanced text processing with fallback for missing components
- **Sentiment Analysis**: Automatic sentiment scoring of comment sections
- **Summary Generation**: AI-powered comment summarization
- **Export Support**: Comments saved in readable text format

### Banner Image Handling
- **Layered Extraction**: Separate background and foreground banner components
- **Auto-Download**: Banners automatically downloaded and cached locally
- **Smart Scaling**: Responsive banner display with aspect ratio preservation
- **Manual Refresh**: Force re-download of banner images

### Database Features
- **Full-Text Search**: Search across titles, authors, and descriptions
- **Advanced Filtering**: Filter by chapter count, rating, genre, etc.
- **Auto-Scanning**: Scan download folders to automatically update database
- **Bulk Operations**: Mass updates and data synchronization

## 🐛 Troubleshooting

### Common Issues

#### "No chapters found"
- Check if the URL is a series list page (should contain `/list`)
- Verify the series is publicly available
- Try with `--no-selenium` flag for faster testing

#### Download failures
- Check internet connection stability
- Reduce thread count with `--threads 10`
- Enable Selenium with full browser headers

#### Missing comments
- Install Selenium: `pip install selenium`
- Download ChromeDriver and add to PATH
- Remove `--no-selenium` flag

#### GUI not launching
- Ensure tkinter is installed: `python -m tkinter`
- Check Python version (3.7+ required)
- Install PIL: `pip install Pillow`

### Performance Optimization

#### For Speed
```bash
# Disable Selenium and comments for maximum speed
python cli.py "URL" --download --no-selenium --no-comments --threads 50
```

#### For Completeness  
```bash
# Enable all features for complete extraction
python cli.py "URL" --download --threads 20
```

#### For Large Series
```bash
# Use moderate settings for stability
python cli.py "URL" --download --threads 15
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect the terms of service of WEBTOONS and only download content you have permission to access. The authors are not responsible for any misuse of this software.

## 🙏 Acknowledgments

- WEBTOONS for providing excellent web comics
- The Python community for amazing libraries
- Contributors and users for feedback and improvements

---

**Happy reading! 📚✨** 