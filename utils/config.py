"""
Configuration management for the webtoon scraper application.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration settings for the webtoon scraper."""
    
    # Application info
    APP_NAME = "Webtoon Scraper"
    VERSION = "2.0.0"
    
    # HTTP Headers
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    HTTP_HEADERS = {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.webtoons.com/'
    }
    
    IMAGE_HEADERS = {
        'User-Agent': USER_AGENT,
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.webtoons.com/',
        'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    # UI Colors and Fonts
    UI_COLORS = {
        'HIGHLIGHT': "#fbdd00",
        'WHITE': "#ffffff",
        'BLACK': "#000000",
        'ORANGE': "#ff9900",
        'ORANGE_HOVER': "#ffaa33"
    }
    
    UI_FONTS = {
        'DEFAULT': ("Helvetica", 11, "bold"),
        'TITLE': ("Helvetica", 16, "bold"),
        'LARGE_TITLE': ("Helvetica", 22, "bold"),
        'SMALL': ("Helvetica", 9),
        'TINY': ("Helvetica", 8)
    }
    
    UI_CONFIG = {
        'window_size': (1000, 800),
        'banner_height': 180,
        'listbox_height': 15,
        'comment_height': 4
    }
    
    # Default values
    DEFAULT_MAX_WORKERS = 20
    DEFAULT_CHAPTER_WORKERS = 4
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_TIMEOUT = 30
    
    # Comment extraction settings
    EXTRACT_COMMENTS_DEFAULT = True
    COMMENT_SUMMARY_DEFAULT = True
    PREFER_SELENIUM_FOR_COMMENTS = True
    
    # Logging configuration
    LOGGING_CONFIG = {
        'level': logging.INFO,
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5,
        'log_to_file': True,
        'log_to_console': True
    }
    
    # File paths
    BASE_DIR = Path.cwd()
    DOWNLOADS_DIR = BASE_DIR / "webtoon_downloads"
    DOWNLOAD_FOLDER = str(DOWNLOADS_DIR)  # String version for compatibility
    DB_PATH = BASE_DIR / "manga_collection.db"
    LOGS_DIR = BASE_DIR / "logs"
    
    @classmethod
    def get_downloads_dir(cls) -> Path:
        """Get the downloads directory, creating it if necessary."""
        cls.DOWNLOADS_DIR.mkdir(exist_ok=True)
        return cls.DOWNLOADS_DIR
    
    @classmethod
    def get_logs_dir(cls) -> Path:
        """Get the logs directory, creating it if necessary."""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        return cls.LOGS_DIR
    
    @classmethod
    def get_manga_folder(cls, title_no: str, series_name: str) -> Path:
        """Get the folder path for a specific manga."""
        folder_name = f"webtoon_{title_no}_{series_name}"
        return cls.get_downloads_dir() / folder_name
    
    @classmethod
    def get_chapter_folder(cls, manga_folder: Path, episode_no: str, chapter_title: str) -> Path:
        """Get the folder path for a specific chapter."""
        # Sanitize the chapter title for filesystem use
        import re
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "-", chapter_title)
        chapter_folder_name = f"Episode_{episode_no}_{sanitized_title}"
        return manga_folder / chapter_folder_name
    
    @classmethod
    def setup_logging(cls) -> logging.Logger:
        """Set up application-wide logging configuration."""
        from utils.logger import setup_logging
        return setup_logging(
            name='manga_scraper',
            level=cls.LOGGING_CONFIG['level'],
            log_to_file=cls.LOGGING_CONFIG['log_to_file'],
            log_to_console=cls.LOGGING_CONFIG['log_to_console'],
            max_file_size=cls.LOGGING_CONFIG['max_file_size'],
            backup_count=cls.LOGGING_CONFIG['backup_count']
        )
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings."""
        try:
            # Ensure necessary directories can be created
            cls.get_downloads_dir()
            cls.get_logs_dir()
            
            # Set up logging
            logger = cls.setup_logging()
            logger.info(f"Configuration validated successfully for {cls.APP_NAME} v{cls.VERSION}")
            
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False 