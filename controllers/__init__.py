"""
Controllers package for the manga scraper application.

This package contains controller classes that implement the business logic
and act as intermediaries between models and views, following the MVC pattern.
"""

from .manga_controller import MangaController
from .download_controller import DownloadController

__all__ = ['MangaController', 'DownloadController'] 