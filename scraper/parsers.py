"""
HTML parsing logic for extracting data from webtoon pages.

This module contains all the parsing functions for extracting chapter links,
metadata, images, and other information from webtoon HTML pages.
"""

import re
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urljoin

from models.manga import Manga
from models.chapter import Chapter


def _clean_text(text: str) -> str:
    """Clean text by removing extra whitespace, newlines, and tabs."""
    if not text:
        return text
    
    # Replace all whitespace (including \n, \t) with single spaces
    cleaned = re.sub(r'\s+', ' ', str(text).strip())
    
    # Clean up common separators and extra commas
    cleaned = re.sub(r',\s*,', ',', cleaned)  # Remove double commas
    cleaned = re.sub(r'^\s*,\s*|\s*,\s*$', '', cleaned)  # Remove leading/trailing commas
    
    return cleaned


def extract_webtoon_info(url: str) -> Tuple[str, str]:
    """Extract title_no and series name from webtoon URL."""
    parsed_url = urlparse(url)
    
    # Extract title_no from URL parameters
    query_params = parse_qs(parsed_url.query)
    title_no = query_params.get('title_no', [''])[0]
    
    # Extract series name from path
    path_segments = parsed_url.path.strip('/').split('/')
    if len(path_segments) >= 3:
        series_name = path_segments[2]  # Usually the third segment
    else:
        series_name = "unknown"
    
    return title_no, series_name


def extract_chapter_info(chapter_url: str) -> Tuple[str, str]:
    """Extract chapter number and title from URL."""
    parsed_url = urlparse(chapter_url)
    path_segments = parsed_url.path.strip('/').split('/')
    
    # Extract episode number from query parameters
    query_params = parse_qs(parsed_url.query)
    episode_no = query_params.get('episode_no', ['0'])[0]
    
    # Extract chapter title from path
    chapter_title = "Unknown"
    if len(path_segments) >= 4:
        chapter_title = path_segments[-2]  # Second-to-last segment
        # Clean up title
        chapter_title = chapter_title.replace('-', ' ').replace('_', ' ').title()
    
    return episode_no, chapter_title


def parse_chapter_links(soup: BeautifulSoup) -> List[str]:
    """Extract chapter links from a series list page."""
    chapter_links = []
    
    # Method 1: Look for links with NPI=a:list class (original method)
    for link in soup.find_all('a'):
        class_attr = link.get('class')
        href = link.get('href')
        
        # Check if class attribute starts with NPI=a:list
        if class_attr and any(c.startswith('NPI=a:list') for c in class_attr):
            if href and 'episode' in href and 'viewer' in href:
                clean_url = href.replace('&amp;', '&')
                chapter_links.append(clean_url)
        # Alternative check for string class
        elif isinstance(class_attr, str) and class_attr.startswith('NPI=a:list'):
            if href and 'episode' in href and 'viewer' in href:
                clean_url = href.replace('&amp;', '&')
                chapter_links.append(clean_url)
    
    # Method 2: Look for any episode viewer links
    if not chapter_links:
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and 'episode' in href and 'viewer' in href:
                if 'title_no' in href:
                    clean_url = href.replace('&amp;', '&')
                    chapter_links.append(clean_url)
    
    # Method 3: Modern structure - look for episode list items
    if not chapter_links:
        # Look for specific WEBTOON episode item classes
        episode_items = soup.find_all('li', class_='_episodeItem')
        
        for item in episode_items:
            links = item.find_all('a', href=True)
            for link in links:
                href = link['href']
                if 'episode' in href or 'viewer' in href:
                    # Convert to absolute URL if needed
                    if href.startswith('/'):
                        href = f"https://www.webtoons.com{href}"
                    clean_url = href.replace('&amp;', '&')
                    chapter_links.append(clean_url)
        
        # Also try the main episode list container
        if not chapter_links:
            episode_list = soup.find('ul', id='_listUl')
            if episode_list:
                list_items = episode_list.find_all('li')
                
                for li in list_items:
                    links = li.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if 'episode' in href or 'viewer' in href:
                            # Convert to absolute URL if needed
                            if href.startswith('/'):
                                href = f"https://www.webtoons.com{href}"
                            clean_url = href.replace('&amp;', '&')
                            chapter_links.append(clean_url)
        
        # Generic episode list containers as fallback
        if not chapter_links:
            episode_lists = soup.find_all('ul', id=lambda x: x and 'episode' in x.lower())
            if not episode_lists:
                episode_lists = soup.find_all('ul', class_=lambda x: x and 'episode' in str(x).lower())
            
            for episode_list in episode_lists:
                list_items = episode_list.find_all('li')
                
                for li in list_items:
                    links = li.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if 'episode' in href or 'viewer' in href:
                            # Convert to absolute URL if needed
                            if href.startswith('/'):
                                href = f"https://www.webtoons.com{href}"
                            clean_url = href.replace('&amp;', '&')
                            chapter_links.append(clean_url)
    
    # Method 4: Last resort - any link containing episode
    if not chapter_links:
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            if 'episode' in href:
                clean_url = href.replace('&amp;', '&')
                if clean_url.startswith('/'):
                    clean_url = f"https://www.webtoons.com{clean_url}"
                chapter_links.append(clean_url)
    
    return chapter_links


def parse_manga_metadata(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract manga metadata from series page."""
    metadata = {
        'title': None,
        'author': None,
        'genre': None,
        'grade': None,
        'views': None,
        'subscribers': None,
        'day_info': None,
        'banner_bg_url': None,
        'banner_fg_url': None
    }
    
    # Extract title
    h1 = soup.find('h1')
    if h1:
        metadata['title'] = h1.get_text(strip=True)
    if not metadata['title']:
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            metadata['title'] = meta_title.get('content')
    if not metadata['title'] and soup.title:
        metadata['title'] = soup.title.string.strip()
    
    # Extract author
    author_area = soup.find('div', class_='author_area')
    if author_area:
        # Remove button elements
        for btn in author_area.find_all('button'):
            btn.extract()
        metadata['author'] = _clean_text(author_area.get_text(strip=True))
    
    if not metadata['author']:
        author_tag = soup.find(class_=lambda c: c and 'author' in c.lower())
        if author_tag:
            metadata['author'] = _clean_text(author_tag.get_text(strip=True))
    
    # Extract genre
    genre_h2 = soup.find('h2', class_=lambda c: c and 'genre' in c)
    if genre_h2:
        metadata['genre'] = genre_h2.get_text(strip=True)
    
    if not metadata['genre']:
        genre_tag = soup.find(class_=lambda c: c and 'genre' in c.lower())
        if genre_tag:
            metadata['genre'] = genre_tag.get_text(strip=True)
    
    # Extract grade, views, subscribers
    grade_area = soup.find('ul', class_='grade_area')
    if grade_area:
        for li in grade_area.find_all('li'):
            span = li.find('span')
            em = li.find('em', class_='cnt')
            if not span or not em:
                continue
            
            span_classes = span.get('class', [])
            if 'ico_view' in span_classes:
                metadata['views'] = em.get_text(strip=True)
            elif 'ico_subscribe' in span_classes:
                metadata['subscribers'] = em.get_text(strip=True)
            elif 'ico_grade5' in span_classes:
                try:
                    metadata['grade'] = float(em.get_text(strip=True))
                except (ValueError, TypeError):
                    pass
    
    # Extract day info
    day_p = soup.find('p', class_='day_info')
    if day_p:
        # Remove span elements (like UP icon)
        for sp in day_p.find_all('span'):
            sp.extract()
        metadata['day_info'] = day_p.get_text(strip=True)
    
    # Extract banner images
    metadata.update(_extract_banner_urls(soup))
    
    return metadata


def _extract_banner_urls(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract banner background and foreground URLs."""
    banner_bg_url = None
    banner_fg_url = None
    
    try:
        # Background image - look in detail_bg div
        detail_bg = soup.find('div', class_='detail_bg')
        if detail_bg:
            style = detail_bg.get('style', '')
            bg_patterns = [
                r"background:url\('([^']+)'\)",
                r'background:url\("([^"]+)"\)',
                r"background:url\(([^)]+)\)",
                r"background-image:url\('([^']+)'\)",
                r'background-image:url\("([^"]+)"\)',
                r"background-image:url\(([^)]+)\)"
            ]
            
            for pattern in bg_patterns:
                bg_match = re.search(pattern, style)
                if bg_match:
                    banner_bg_url = bg_match.group(1).strip("'\"")
                    break
        
        # If not found in detail_bg, search all divs
        if not banner_bg_url:
            for div in soup.find_all('div'):
                style = div.get('style', '')
                if 'background' in style and 'url' in style:
                    for pattern in bg_patterns:
                        bg_match = re.search(pattern, style)
                        if bg_match:
                            banner_bg_url = bg_match.group(1).strip("'\"")
                            break
                    if banner_bg_url:
                        break
        
        # Foreground image - look for specific patterns
        fg_patterns = [
            'desktop_fg.png',
            'landingpage_desktop_fg',
            'episodelist_pc_fg',
            'landingpage_fg',
            '_fg.png',
            '_fg.jpg',
            'character.png',
            'pc_character',
            'title.png',
            'logo.png',
            'front.png'
        ]
        
        for pattern in fg_patterns:
            fg_img = soup.find('img', src=lambda src: src and pattern in src.lower())
            if fg_img:
                banner_fg_url = fg_img.get('src')
                break
        
        # Make URLs absolute
        if banner_bg_url and not banner_bg_url.startswith(('http://', 'https://')):
            banner_bg_url = 'https:' + banner_bg_url if banner_bg_url.startswith('//') else 'https://www.webtoons.com' + banner_bg_url
        
        if banner_fg_url and not banner_fg_url.startswith(('http://', 'https://')):
            banner_fg_url = 'https:' + banner_fg_url if banner_fg_url.startswith('//') else 'https://www.webtoons.com' + banner_fg_url
    
    except Exception as e:
        print(f"Error extracting banner URLs: {e}")
    
    return {
        'banner_bg_url': banner_bg_url,
        'banner_fg_url': banner_fg_url
    }


def parse_chapter_images(soup: BeautifulSoup, chapter_url: str) -> List[str]:
    """Extract image URLs from a chapter page."""
    image_urls = []
    
    # Find the container for webtoon images
    content_container = soup.find('div', id='_imageList')
    if not content_container:
        content_container = soup.find('div', id='content')
    if not content_container:
        content_container = soup.find('div', class_='viewer_lst')
    if not content_container:
        content_container = soup  # Fallback to entire page
    
    # Find all images in the container
    images = content_container.find_all('img')
    
    for img in images:
        # Try different attributes for image source
        src = img.get('data-url') or img.get('data-src') or img.get('src')
        
        if src:
            # Clean up URL
            src = src.replace('&amp;', '&')
            
            # Make absolute URL
            if not src.startswith('http'):
                src = urljoin(chapter_url, src)
            
            # Filter content images (avoid small icons, etc.)
            if ('webtoon-phinf' in src or 'comic.naver' in src or 'daumcdn' in src) and not src.endswith('.gif'):
                image_urls.append(src)
    
    # If no images found, try extracting from JavaScript
    if not image_urls:
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for image URLs in JavaScript
                matches = re.findall(r'https?://[^\s\'"]+\.(jpg|jpeg|png|webp)', script.string)
                for match in matches:
                    image_urls.append(match[0])
    
    return image_urls


def create_manga_from_page(soup: BeautifulSoup, url: str) -> Manga:
    """Create a Manga object from a parsed series page."""
    # Extract basic info
    title_no, series_name = extract_webtoon_info(url)
    metadata = parse_manga_metadata(soup)
    
    # Create manga object
    manga = Manga(
        title_no=title_no,
        series_name=series_name,
        display_title=metadata['title'] or series_name,
        author=metadata['author'],
        genre=metadata['genre'],
        grade=metadata['grade'],
        views=metadata['views'],
        subscribers=metadata['subscribers'],
        day_info=metadata['day_info'],
        url=url,
        banner_bg_url=metadata['banner_bg_url'],
        banner_fg_url=metadata['banner_fg_url']
    )
    
    return manga


def create_chapters_from_links(chapter_links: List[str]) -> List[Chapter]:
    """Create Chapter objects from a list of chapter URLs."""
    chapters = []
    
    for link in chapter_links:
        episode_no, title = extract_chapter_info(link)
        chapter = Chapter(
            episode_no=episode_no,
            title=title,
            url=link
        )
        chapters.append(chapter)
    
    return chapters 