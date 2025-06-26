"""
Data models for the webtoon scraper application.

This package contains the core data models representing manga, chapters,
and other domain objects.
"""

from .manga import Manga
from .chapter import Chapter

__all__ = ['Manga', 'Chapter'] 