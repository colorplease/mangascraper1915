"""
WebtoonClient handles all network requests to Webtoons.com.

This module is responsible for making HTTP requests, handling sessions,
cookies, and providing a clean interface for web interactions.
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
import time
from urllib.parse import urlparse, parse_qs, urljoin
import os

from utils.config import Config


class WebtoonClient:
    """Client for making requests to Webtoons.com."""
    
    def __init__(self, use_selenium: bool = False):
        """Initialize the client."""
        self.session = requests.Session()
        self.use_selenium = use_selenium
        self.selenium_driver = None
        
        # Set up default headers
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.webtoons.com/',
            'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Initialize session with cookies
        self._initialize_session()
    
    def _initialize_session(self) -> None:
        """Initialize session by getting cookies from main site."""
        try:
            self.session.get('https://www.webtoons.com/')
        except Exception as e:
            print(f"Warning: Could not initialize session: {e}")
    
    def get_page(self, url: str, retry_count: int = 3) -> Optional[BeautifulSoup]:
        """Get a web page and return BeautifulSoup object."""
        for attempt in range(retry_count):
            try:
                if self.use_selenium:
                    return self._get_page_selenium(url)
                else:
                    return self._get_page_requests(url)
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"Failed to get page after {retry_count} attempts: {url}")
                    return None
    
    def _get_page_requests(self, url: str) -> BeautifulSoup:
        """Get page using requests library."""
        response = self.session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    
    def _get_page_selenium(self, url: str) -> BeautifulSoup:
        """Get page using Selenium (for dynamic content)."""
        if not self.selenium_driver:
            self._setup_selenium()
        
        self.selenium_driver.get(url)
        
        # Wait for comments to load if this is a chapter page
        if 'viewer' in url:
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                WebDriverWait(self.selenium_driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "wcc_CommentItem__root"))
                )
            except Exception:
                pass  # Comments might not be available
        
        html = self.selenium_driver.page_source
        return BeautifulSoup(html, 'html.parser')
    
    def _setup_selenium(self) -> None:
        """Set up Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={Config.USER_AGENT}")
            
            self.selenium_driver = webdriver.Chrome(options=chrome_options)
        except ImportError:
            raise ImportError("Selenium not installed. Install with: pip install selenium")
        except Exception as e:
            raise Exception(f"Failed to setup Selenium: {e}")
    
    def get_paginated_content(self, base_url: str, title_no: str, max_pages: int = None) -> List[BeautifulSoup]:
        """Get content from all pages of a paginated series."""
        pages = []
        
        # Get first page to determine total pages - construct proper URL with title_no
        first_page_url = f"{base_url}?title_no={title_no}"
        first_page = self.get_page(first_page_url)
        if not first_page:
            return []
        
        pages.append(first_page)
        
        # Determine total pages
        total_pages = self._get_page_count(first_page)
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"Found {total_pages} page(s) of chapters")
        
        # Get remaining pages
        for page_num in range(2, total_pages + 1):
            page_url = f"{base_url}?title_no={title_no}&page={page_num}"
            print(f"Fetching page {page_num}: {page_url}")
            
            page_soup = self.get_page(page_url)
            if page_soup:
                pages.append(page_soup)
            else:
                print(f"Failed to get page {page_num}")
        
        return pages
    
    def _get_page_count(self, soup: BeautifulSoup) -> int:
        """Extract total number of pages from pagination."""
        paginate_div = soup.find('div', class_='paginate')
        if not paginate_div:
            return 1
        
        page_links = paginate_div.find_all('a')
        if not page_links:
            return 1
        
        max_page = 1
        for link in page_links:
            span = link.find('span')
            if span and span.text.isdigit():
                page_num = int(span.text)
                max_page = max(max_page, page_num)
        
        return max_page
    
    def download_image(self, url: str, filepath: str, headers: Dict[str, str] = None) -> bool:
        """Download an image from URL to filepath."""
        try:
            # Use image-specific headers
            img_headers = {
                'User-Agent': Config.USER_AGENT,
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
            
            if headers:
                img_headers.update(headers)
            
            response = self.session.get(url, headers=img_headers, stream=True)
            response.raise_for_status()
            
            # Check if we got an actual image
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith(('image/', 'application/octet-stream')):
                print(f"Warning: URL {url} returned content type {content_type}")
                return False
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file size
            if os.path.getsize(filepath) < 1000:
                print(f"Warning: Downloaded file {filepath} is very small")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    
    def normalize_list_url(self, url: str) -> str:
        """Convert any webtoon URL to a list page URL."""
        parsed_url = urlparse(url)
        path_segments = parsed_url.path.strip('/').split('/')
        
        # If URL is an episode viewer, convert to list page
        if 'viewer' in path_segments:
            # Find position of language, genre, and series in the path
            if len(path_segments) >= 3:
                lang_idx = 0
                genre_idx = 1
                series_idx = 2
                
                list_url = f"https://www.webtoons.com/{path_segments[lang_idx]}/{path_segments[genre_idx]}/{path_segments[series_idx]}/list"
                query_params = parse_qs(parsed_url.query)
                title_no = query_params.get('title_no', [''])[0]
                if title_no:
                    list_url += f"?title_no={title_no}"
                print(f"Converted viewer URL to list page: {list_url}")
                return list_url
        
        return url
    
    def close(self) -> None:
        """Close the client and clean up resources."""
        if self.selenium_driver:
            self.selenium_driver.quit()
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 