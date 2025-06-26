"""
Manga data model representing a webtoon series.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Manga:
    """Data model for a manga/webtoon series."""
    
    # Core identifiers
    title_no: str
    series_name: str
    display_title: str
    
    # Metadata
    author: Optional[str] = None
    genre: Optional[str] = None
    grade: Optional[float] = None
    views: Optional[str] = None
    subscribers: Optional[str] = None
    day_info: Optional[str] = None
    
    # URLs and paths
    url: Optional[str] = None
    banner_bg_url: Optional[str] = None
    banner_fg_url: Optional[str] = None
    
    # Chapter information
    num_chapters: int = 0
    chapters: List['Chapter'] = field(default_factory=list)
    
    # Status tracking
    last_updated: Optional[datetime] = None
    download_status: Dict[str, Any] = field(default_factory=dict)
    
    # Database fields
    id: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
        
        # Ensure num_chapters matches actual chapters
        if self.chapters:
            self.num_chapters = len(self.chapters)
    
    @property
    def folder_name(self) -> str:
        """Generate folder name for this manga."""
        return f"webtoon_{self.title_no}_{self.series_name}"
    
    @property
    def is_complete(self) -> bool:
        """Check if all chapters are downloaded."""
        if not self.chapters:
            return False
        return all(chapter.is_downloaded for chapter in self.chapters)
    
    @property
    def downloaded_chapters_count(self) -> int:
        """Count of downloaded chapters."""
        return sum(1 for chapter in self.chapters if chapter.is_downloaded)
    
    def add_chapter(self, chapter: 'Chapter') -> None:
        """Add a chapter to this manga."""
        if chapter not in self.chapters:
            self.chapters.append(chapter)
            self.num_chapters = len(self.chapters)
    
    def get_chapter_by_episode(self, episode_no: str) -> Optional['Chapter']:
        """Get chapter by episode number."""
        for chapter in self.chapters:
            if chapter.episode_no == episode_no:
                return chapter
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title_no': self.title_no,
            'series_name': self.series_name,
            'display_title': self.display_title,
            'author': self.author,
            'genre': self.genre,
            'grade': self.grade,
            'views': self.views,
            'subscribers': self.subscribers,
            'day_info': self.day_info,
            'url': self.url,
            'banner_bg_url': self.banner_bg_url,
            'banner_fg_url': self.banner_fg_url,
            'num_chapters': self.num_chapters,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'download_status': self.download_status,
            'chapters': [chapter.to_dict() for chapter in self.chapters]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Manga':
        """Create instance from dictionary."""
        # Handle datetime conversion
        last_updated = None
        if data.get('last_updated'):
            last_updated = datetime.fromisoformat(data['last_updated'])
        
        # Extract chapters data
        chapters_data = data.pop('chapters', [])
        
        # Create manga instance
        manga = cls(
            id=data.get('id'),
            title_no=data['title_no'],
            series_name=data['series_name'],
            display_title=data['display_title'],
            author=data.get('author'),
            genre=data.get('genre'),
            grade=data.get('grade'),
            views=data.get('views'),
            subscribers=data.get('subscribers'),
            day_info=data.get('day_info'),
            url=data.get('url'),
            banner_bg_url=data.get('banner_bg_url'),
            banner_fg_url=data.get('banner_fg_url'),
            num_chapters=data.get('num_chapters', 0),
            last_updated=last_updated,
            download_status=data.get('download_status', {})
        )
        
        # Add chapters
        from .chapter import Chapter
        for chapter_data in chapters_data:
            chapter = Chapter.from_dict(chapter_data)
            manga.add_chapter(chapter)
        
        return manga
    
    def __str__(self) -> str:
        """String representation."""
        return f"Manga(title='{self.display_title}', chapters={self.num_chapters})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"Manga(title_no='{self.title_no}', series_name='{self.series_name}')" 