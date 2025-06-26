"""
Chapter data model representing an individual chapter/episode.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import os


@dataclass
class Chapter:
    """Data model for a manga chapter/episode."""
    
    # Core identifiers
    episode_no: str
    title: str
    url: str
    
    # Metadata
    manga_id: Optional[int] = None
    image_count: int = 0
    comment_count: int = 0
    
    # Download information
    is_downloaded: bool = False
    download_path: Optional[str] = None
    images_downloaded: int = 0
    download_timestamp: Optional[datetime] = None
    
    # Comment data
    comments: List[Dict[str, Any]] = field(default_factory=list)
    comment_summary: Optional[str] = None
    
    # Database fields
    id: Optional[int] = None
    
    @property
    def folder_name(self) -> str:
        """Generate folder name for this chapter."""
        # Sanitize title for filesystem
        sanitized_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '-' for c in self.title)
        sanitized_title = sanitized_title.replace(' ', '-').strip('-')
        return f"Episode_{self.episode_no}_{sanitized_title}"
    
    @property
    def download_complete(self) -> bool:
        """Check if download is complete."""
        return self.is_downloaded and self.images_downloaded > 0
    
    @property
    def has_comments(self) -> bool:
        """Check if chapter has comments."""
        return len(self.comments) > 0 or self.comment_count > 0
    
    def mark_downloaded(self, image_count: int = 0, download_path: str = None) -> None:
        """Mark chapter as downloaded."""
        self.is_downloaded = True
        self.images_downloaded = image_count
        self.image_count = max(self.image_count, image_count)
        self.download_timestamp = datetime.utcnow()
        if download_path:
            self.download_path = download_path
    
    def add_comments(self, comments: List[Dict[str, Any]], summary: str = None) -> None:
        """Add comments to this chapter."""
        self.comments = comments
        self.comment_count = len(comments)
        if summary:
            self.comment_summary = summary
    
    def get_download_folder(self, base_path: str) -> str:
        """Get the full download folder path."""
        return os.path.join(base_path, self.folder_name)
    
    def check_download_exists(self, base_path: str) -> bool:
        """Check if download folder exists and has images."""
        folder_path = self.get_download_folder(base_path)
        if not os.path.exists(folder_path):
            return False
        
        # Count image files in folder
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
        image_files = [f for f in os.listdir(folder_path) 
                      if os.path.splitext(f.lower())[1] in image_extensions]
        
        if image_files:
            self.images_downloaded = len(image_files)
            self.is_downloaded = True
            self.download_path = folder_path
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'manga_id': self.manga_id,
            'episode_no': self.episode_no,
            'title': self.title,
            'url': self.url,
            'image_count': self.image_count,
            'comment_count': self.comment_count,
            'is_downloaded': self.is_downloaded,
            'download_path': self.download_path,
            'images_downloaded': self.images_downloaded,
            'download_timestamp': self.download_timestamp.isoformat() if self.download_timestamp else None,
            'comments': self.comments,
            'comment_summary': self.comment_summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chapter':
        """Create instance from dictionary."""
        # Handle datetime conversion
        download_timestamp = None
        if data.get('download_timestamp'):
            download_timestamp = datetime.fromisoformat(data['download_timestamp'])
        
        return cls(
            id=data.get('id'),
            manga_id=data.get('manga_id'),
            episode_no=data['episode_no'],
            title=data['title'],
            url=data['url'],
            image_count=data.get('image_count', 0),
            comment_count=data.get('comment_count', 0),
            is_downloaded=data.get('is_downloaded', False),
            download_path=data.get('download_path'),
            images_downloaded=data.get('images_downloaded', 0),
            download_timestamp=download_timestamp,
            comments=data.get('comments', []),
            comment_summary=data.get('comment_summary')
        )
    
    @classmethod
    def from_url(cls, url: str, episode_no: str = None, title: str = None) -> 'Chapter':
        """Create chapter from URL, extracting info if needed."""
        from scraper.parsers import extract_chapter_info
        
        if not episode_no or not title:
            extracted_episode, extracted_title = extract_chapter_info(url)
            episode_no = episode_no or extracted_episode
            title = title or extracted_title
        
        return cls(
            episode_no=episode_no,
            title=title,
            url=url
        )
    
    def __str__(self) -> str:
        """String representation."""
        status = "Downloaded" if self.is_downloaded else "Not Downloaded"
        return f"Chapter(episode={self.episode_no}, title='{self.title}', status={status})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"Chapter(episode_no='{self.episode_no}', url='{self.url}')"
    
    def __eq__(self, other) -> bool:
        """Equality comparison based on episode number and URL."""
        if not isinstance(other, Chapter):
            return False
        return self.episode_no == other.episode_no and self.url == other.url
    
    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash((self.episode_no, self.url)) 