#!/usr/bin/env python3
import argparse
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, urljoin
import threading
import db_utils
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from datetime import datetime

def extract_webtoon_info(url):
    """Extract title_no and series title from the webtoon URL"""
    parsed_url = urlparse(url)
    
    # Extract title_no from URL parameters
    query_params = parse_qs(parsed_url.query)
    title_no = query_params.get('title_no', [''])[0]
    
    # Extract series name from path
    path_segments = parsed_url.path.strip('/').split('/')
    if len(path_segments) >= 3:
        series_name = path_segments[2]  # Usually the third segment is the series name
    else:
        series_name = "unknown"
    
    return title_no, series_name

def get_page_count(soup):
    """Extract the total number of pages from the pagination element"""
    paginate_div = soup.find('div', class_='paginate')
    if not paginate_div:
        return 1  # No pagination found, assume it's just one page
    
    # Find all page links
    page_links = paginate_div.find_all('a')
    if not page_links:
        return 1
    
    # Find the highest page number
    max_page = 1
    for link in page_links:
        span = link.find('span')
        if span and span.text.isdigit():
            page_num = int(span.text)
            max_page = max(max_page, page_num)
    
    return max_page

def scrape_chapter_links_from_page(soup):
    """Extract chapter links from the current page's soup object"""
    chapter_links = []
    
    # Method 1: Look for links where the class attribute starts with "NPI=a:list"
    for link in soup.find_all('a'):
        class_attr = link.get('class')
        href = link.get('href')
        
        # Check if class attribute exists and starts with NPI=a:list
        if class_attr and any(c.startswith('NPI=a:list') for c in class_attr):
            if href and 'episode' in href and 'viewer' in href:
                # Clean up the URL (remove amp; if present)
                clean_url = href.replace('&amp;', '&')
                chapter_links.append(clean_url)
        # Alternative check: if the class is stored as a string and starts with NPI=a:list
        elif isinstance(class_attr, str) and class_attr.startswith('NPI=a:list'):
            if href and 'episode' in href and 'viewer' in href:
                clean_url = href.replace('&amp;', '&')
                chapter_links.append(clean_url)
    
    # If no links found with the first method, try an alternative approach
    if not chapter_links:
        # Method 2: Look for any links that match the episode pattern
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and 'episode' in href and 'viewer' in href and 'title_no' in href:
                clean_url = href.replace('&amp;', '&')
                chapter_links.append(clean_url)
    
    return chapter_links

def extract_manga_metadata(soup):
    # Try to extract title, author, genre, grade, views, subscribers, day_info from the soup
    title = None
    author = None
    genre = None
    grade = None
    views = None
    subscribers = None
    day_info = None
    banner_bg_url = None
    banner_fg_url = None
    
    # Try to extract banner images (background and foreground)
    try:
        # Background image - typically in a div with style
        detail_bg = soup.find('div', class_='detail_bg')
        if detail_bg:
            style = detail_bg.get('style', '')
            # Try multiple regex patterns to extract URL from background
            bg_patterns = [
                r"background:url\('([^']+)'\)",  # Single quotes
                r'background:url\("([^"]+)"\)',  # Double quotes
                r"background:url\(([^)]+)\)",     # No quotes
                r"background-image:url\('([^']+)'\)",  # With image prefix, single quotes
                r'background-image:url\("([^"]+)"\)',  # With image prefix, double quotes
                r"background-image:url\(([^)]+)\)",     # With image prefix, no quotes
            ]
            
            for pattern in bg_patterns:
                bg_match = re.search(pattern, style)
                if bg_match:
                    banner_bg_url = bg_match.group(1).strip()
                    # Remove any quotes that might have been captured
                    banner_bg_url = banner_bg_url.strip("'\"")
                    print(f"Found banner background in detail_bg: {banner_bg_url}")
                    break
        
        # Look for background images in any div if not found
        if not banner_bg_url:
            for div in soup.find_all('div'):
                style = div.get('style', '')
                if 'background' in style and 'url' in style:
                    # Try the same patterns
                    for pattern in bg_patterns:
                        bg_match = re.search(pattern, style)
                        if bg_match:
                            banner_bg_url = bg_match.group(1).strip()
                            # Remove any quotes that might have been captured
                            banner_bg_url = banner_bg_url.strip("'\"")
                            print(f"Found banner background in div style: {banner_bg_url}")
                            break
                    if banner_bg_url:
                        break
        
        # Foreground image - typically an img tag with specific filename patterns
        fg_patterns = [
            'desktop_fg.png',
            'landingpage_desktop_fg',
            'episodelist_pc_fg',
            'landingpage_fg',
            '_fg.png',
            '_fg.jpg'
        ]
        
        # Look for foreground image based on filename patterns
        for pattern in fg_patterns:
            fg_img = soup.find('img', src=lambda src: src and pattern in src.lower())
            if fg_img:
                banner_fg_url = fg_img.get('src')
                print(f"Found banner foreground with pattern '{pattern}': {banner_fg_url}")
                break
        
        # If foreground not found, look for any image near the background div
        if not banner_fg_url and detail_bg:
            # Try to find images in parent or sibling elements
            parent = detail_bg.parent
            if parent:
                fg_img = parent.find('img')
                if fg_img and fg_img.get('src'):
                    banner_fg_url = fg_img.get('src')
                    print(f"Found potential banner foreground in parent: {banner_fg_url}")
        
        # Look for any character/title images if foreground still not found
        if not banner_fg_url:
            # Look for images with naming patterns related to characters or titles
            char_patterns = ['character.png', 'title.png', 'logo.png', 'front.png']
            for pattern in char_patterns:
                fg_img = soup.find('img', src=lambda src: src and pattern in src.lower())
                if fg_img:
                    banner_fg_url = fg_img.get('src')
                    print(f"Found character/title image: {banner_fg_url}")
                    break
        
        # Ensure URLs are absolute
        for url_var in ['banner_bg_url', 'banner_fg_url']:
            url = locals()[url_var]
            if url:
                # Clean up the URL - remove any extraneous quotes
                url = url.strip("'\"")
                
                # Make the URL absolute
                if not url.startswith(('http://', 'https://')):
                    url = 'https:' + url if url.startswith('//') else 'https://www.webtoons.com' + url
                
                # Update the variable
                locals()[url_var] = url
                print(f"Final {url_var}: {url}")
                
        # If we only have one of the banner images, use it for both (allows fallback)
        if banner_bg_url and not banner_fg_url:
            print("Using background image as fallback for foreground")
            banner_fg_url = None  # Keep as None to indicate we don't have a true foreground
        elif banner_fg_url and not banner_bg_url:
            print("Using foreground image as fallback for background")
            banner_bg_url = banner_fg_url
            
    except Exception as e:
        print(f"Error extracting banner images: {e}")
    
    # Title: try h1, meta, or title tag
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
    if not title:
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            title = meta_title.get('content', None)
    if not title:
        title = soup.title.string.strip() if soup.title else None
    
    # Author: look for <div class="author_area">
    author_area = soup.find('div', class_='author_area')
    if author_area:
        for btn in author_area.find_all('button'):
            btn.extract()
        author = author_area.get_text(strip=True)
    if not author:
        author_tag = soup.find(class_=lambda c: c and 'author' in c.lower())
        if author_tag:
            author = author_tag.get_text(strip=True)
    # Genre: look for <h2 class="genre ...">
    genre_h2 = soup.find('h2', class_=lambda c: c and 'genre' in c)
    if genre_h2:
        genre = genre_h2.get_text(strip=True)
    if not genre:
        genre_tag = soup.find(class_=lambda c: c and 'genre' in c.lower())
        if genre_tag:
            genre = genre_tag.get_text(strip=True)
    # Grade, views, subscribers: from <ul class="grade_area">
    grade_area = soup.find('ul', class_='grade_area')
    if grade_area:
        for li in grade_area.find_all('li'):
            span = li.find('span')
            em = li.find('em', class_='cnt')
            if not span or not em:
                continue
            if 'ico_view' in span.get('class', []):
                views = em.get_text(strip=True)
            elif 'ico_subscribe' in span.get('class', []):
                subscribers = em.get_text(strip=True)
            elif 'ico_grade5' in span.get('class', []):
                try:
                    grade = float(em.get_text(strip=True))
                except Exception:
                    grade = None
    # Day info: from <p class="day_info">
    day_p = soup.find('p', class_='day_info')
    if day_p:
        # Remove any span (like UP icon)
        for sp in day_p.find_all('span'):
            sp.extract()
        day_info = day_p.get_text(strip=True)
    return title, author, genre, grade, views, subscribers, day_info, banner_bg_url, banner_fg_url

def get_chapter_links(url):
    """Get all chapter links from a webtoon page, including pagination"""
    print(f"Fetching chapter links from: {url}")
    
    # Make sure we're using the list page, not a specific episode
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.strip('/').split('/')
    
    # If URL is an episode viewer, convert to list page
    if 'viewer' in path_segments:
        # Find position of language and genre in the path
        lang_idx = 0
        genre_idx = 1
        series_idx = 2
        
        if len(path_segments) >= 3:
            list_url = f"https://www.webtoons.com/{path_segments[lang_idx]}/{path_segments[genre_idx]}/{path_segments[series_idx]}/list"
            query_params = parse_qs(parsed_url.query)
            title_no = query_params.get('title_no', [''])[0]
            if title_no:
                list_url += f"?title_no={title_no}"
            url = list_url
            print(f"Converted to list page: {url}")
    
    # Send request with headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.webtoons.com/'
    }
    
    # First request to get the initial page and determine total pages
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webtoon page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract metadata and store in DB
    title, author, genre, grade, views, subscribers, day_info, banner_bg_url, banner_fg_url = extract_manga_metadata(soup)
    total_pages = get_page_count(soup)
    print(f"Found {total_pages} page(s) of chapters")
    
    # Extract chapter links from the first page
    all_chapter_links = scrape_chapter_links_from_page(soup)
    
    # If more than one page, scrape the rest
    if total_pages > 1:
        # Extract base URL and title_no for pagination
        base_url = url.split('?')[0]
        query_params = parse_qs(parsed_url.query)
        title_no = query_params.get('title_no', [''])[0]
        
        # Start from page 2 (we already have page 1)
        for page_num in range(2, total_pages + 1):
            page_url = f"{base_url}?title_no={title_no}&page={page_num}"
            print(f"Fetching chapter links from page {page_num}: {page_url}")
            
            try:
                response = requests.get(page_url, headers=headers)
                response.raise_for_status()
                page_soup = BeautifulSoup(response.text, 'html.parser')
                page_links = scrape_chapter_links_from_page(page_soup)
                print(f"Found {len(page_links)} chapter links on page {page_num}")
                all_chapter_links.extend(page_links)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching page {page_num}: {e}")
                continue
    
    print(f"Found a total of {len(all_chapter_links)} chapter links across all pages")
    
    # Extract series info
    title_no, series_name = extract_webtoon_info(url)
    
    # Store in DB
    db_utils.init_db()
    manga_id = db_utils.insert_or_update_manga(
        title_no, series_name, title or series_name, author, genre, len(all_chapter_links), url, grade, views, subscribers, day_info
    )
    
    # Store chapters
    chapters = []
    for link in all_chapter_links:
        episode_no, chapter_title = extract_chapter_info(link)
        chapters.append({'episode_no': episode_no, 'chapter_title': chapter_title, 'url': link})
    db_utils.insert_chapters(manga_id, chapters)
    
    # Save banner URLs if found
    if banner_bg_url or banner_fg_url:
        print(f"Banner images found - BG: {banner_bg_url}, FG: {banner_fg_url}")
        try:
            manga_dir = os.path.join(os.getcwd(), "webtoon_downloads", f"webtoon_{title_no}_{series_name}")
            os.makedirs(manga_dir, exist_ok=True)
            info_json = os.path.join(manga_dir, "manga_info.json")
            
            # Load existing info if available
            manga_info = {}
            if os.path.exists(info_json):
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        manga_info = json.load(f)
                except Exception as e:
                    print(f"Error loading manga info: {e}")
            
            # Update with banner URLs and metadata
            manga_info["display_name"] = manga_info.get("display_name", title or series_name)
            if banner_bg_url:
                manga_info["banner_bg_url"] = banner_bg_url
            if banner_fg_url:
                manga_info["banner_fg_url"] = banner_fg_url
                
            # Add additional metadata
            if author:
                manga_info["author"] = author
            if genre:
                manga_info["genre"] = genre
            if grade:
                manga_info["grade"] = grade
            if views:
                manga_info["views"] = views
            if subscribers:
                manga_info["subscribers"] = subscribers
            if day_info:
                manga_info["day_info"] = day_info
                
            # Add current timestamp as last_updated
            manga_info["last_updated"] = datetime.utcnow().isoformat()
            
            # Save updated info
            with open(info_json, "w", encoding="utf-8") as f:
                json.dump(manga_info, f, indent=2)
            
            # Try to download the banner images
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.webtoons.com/',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
            }
            
            # Download background banner
            if banner_bg_url:
                banner_bg_file = os.path.join(manga_dir, "banner_bg.jpg")
                try:
                    bg_response = requests.get(banner_bg_url, headers=headers)
                    if bg_response.status_code == 200:
                        with open(banner_bg_file, "wb") as f:
                            f.write(bg_response.content)
                        print(f"Banner background image downloaded to {banner_bg_file}")
                except Exception as e:
                    print(f"Error downloading background banner: {e}")
                    
            # Download foreground banner if available
            if banner_fg_url:
                banner_fg_file = os.path.join(manga_dir, "banner_fg.png")
                try:
                    fg_response = requests.get(banner_fg_url, headers=headers)
                    if fg_response.status_code == 200:
                        with open(banner_fg_file, "wb") as f:
                            f.write(fg_response.content)
                        print(f"Banner foreground image downloaded to {banner_fg_file}")
                except Exception as e:
                    print(f"Error downloading foreground banner: {e}")
                    
        except Exception as e:
            print(f"Error saving banner information: {e}")
    
    return all_chapter_links

def extract_chapter_info(chapter_url):
    """Extract chapter number and title from the URL"""
    parsed_url = urlparse(chapter_url)
    path_segments = parsed_url.path.strip('/').split('/')
    
    # Extract episode number from the query parameters
    query_params = parse_qs(parsed_url.query)
    episode_no = query_params.get('episode_no', ['0'])[0]
    
    # Extract chapter title from path
    chapter_title = "Unknown"
    if len(path_segments) >= 4:
        chapter_title = path_segments[-2]  # Usually the second-to-last segment is the episode title
    
    return episode_no, chapter_title

def extract_comments(soup, chapter_url):
    """Extract comments from a chapter page"""
    print("Scraping comments...")
    comments = []
    
    # Save the HTML for debugging
    try:
        debug_file = os.path.join(os.getcwd(), "webtoon_page_debug.html")
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(str(soup))
        print(f"Saved full HTML to {debug_file} for debugging")
    except Exception as e:
        print(f"Could not save debug HTML: {e}")
    
    # Look for UL elements containing comment items
    comment_uls = soup.find_all('ul', class_=lambda c: c and any(cls in c for cls in ['commentList', 'CommentList', 'comment-list', 'wcc_CommentList']))
    print(f"Found {len(comment_uls)} possible comment list containers")
    
    all_comment_items = []
    
    # Check for comments in UL containers first
    for ul in comment_uls:
        items = ul.find_all('li', class_=lambda c: c and any(cls in c for cls in ['wcc_CommentItem__root', 'CommentItem', 'comment-item']))
        if items:
            print(f"Found {len(items)} comment items in a UL container")
            all_comment_items.extend(items)
    
    # If no comments found in ULs, search the entire page
    if not all_comment_items:
        # Try more lenient class name matching for comment items
        all_comment_items = soup.find_all('li', class_=lambda c: c and any(cls in c for cls in ['wcc_CommentItem', 'CommentItem', 'comment-item']))
        print(f"Found {len(all_comment_items)} comment items using lenient class matching")
    
    # Still nothing? Try looking for the most specific class names from the example
    if not all_comment_items:
        # Look for divs with wcc_CommentItem__inside class - these are inside the li elements
        inside_divs = soup.find_all('div', class_='wcc_CommentItem__inside')
        print(f"Found {len(inside_divs)} divs with wcc_CommentItem__inside class")
        
        # For each inside div, try to find its parent li
        for div in inside_divs:
            parent = div.parent
            if parent and parent.name == 'li':
                all_comment_items.append(parent)
            else:
                # If can't find parent, just use the div
                all_comment_items.append(div)
    
    # Last resort: look for any element with CommentBody and TextContent elements inside
    if not all_comment_items:
        print("Trying last resort comment finding method...")
        content_els = soup.find_all('p', class_='wcc_TextContent__content')
        for content in content_els:
            # Try to find the comment container by going up the DOM
            parent = content
            for _ in range(5):  # Go up to 5 levels up
                if parent is None:
                    break
                parent = parent.parent
                if parent and parent.name == 'li':
                    all_comment_items.append(parent)
                    break
                if parent and 'CommentItem' in str(parent.get('class', [])):
                    all_comment_items.append(parent)
                    break
    
    print(f"Total potential comment items found: {len(all_comment_items)}")
    
    # Debug: print all class names found for the first few elements
    for i, item in enumerate(all_comment_items[:3]):
        print(f"Comment item {i+1} tag: {item.name}, classes: {item.get('class', [])}")
    
    # Process the comment items
    for item in all_comment_items:
        try:
            # Find the comment content - either directly or via wcc_CommentItem__inside
            comment_container = item
            
            # If this is a li, try to find the inside div
            inside_div = item.find('div', class_='wcc_CommentItem__inside')
            if inside_div:
                comment_container = inside_div
            
            # Try to find username using multiple approaches
            username_el = None
            for selector in [
                lambda: comment_container.find('span', class_='wcc_CommentHeader__name'),
                lambda: comment_container.find('a', class_='wcc_CommentHeader__name'),
                lambda: comment_container.find(class_=lambda c: c and 'CommentHeader__name' in str(c))
            ]:
                username_el = selector()
                if username_el:
                    break
            
            username = username_el.text.strip() if username_el else "Unknown User"
            
            # Extract date using multiple approaches
            date_el = None
            for selector in [
                lambda: comment_container.find('time', class_='wcc_CommentHeader__createdAt'),
                lambda: comment_container.find('time'),
                lambda: comment_container.find(class_=lambda c: c and 'createdAt' in str(c))
            ]:
                date_el = selector()
                if date_el:
                    break
            
            date = date_el.text.strip() if date_el else "Unknown Date"
            
            # Extract comment text - try multiple selectors
            content_el = None
            for selector in [
                lambda: comment_container.find('p', class_='wcc_TextContent__content'),
                lambda: comment_container.find(class_=lambda c: c and 'TextContent__content' in str(c)),
                lambda: comment_container.find('p')
            ]:
                content_el = selector()
                if content_el:
                    break
            
            if content_el:
                # Create a copy to modify without affecting the original
                content_copy = BeautifulSoup(str(content_el), 'html.parser')
                
                # Remove badge elements (TOP badge, etc.)
                for badge in content_copy.find_all('span', class_='wcc_TopBadge__root'):
                    badge.extract()
                
                # Remove any span with badge class
                for badge in content_copy.find_all('span', class_=lambda c: c and 'badge' in str(c).lower()):
                    badge.extract()
                
                # Remove span with sr-only class (screen reader text)
                for sr in content_copy.find_all('span', class_='sr-only'):
                    sr.extract()
                
                # Get text from all span children and combine
                spans = content_copy.find_all('span')
                if spans:
                    comment_text = ' '.join(span.text.strip() for span in spans)
                else:
                    # Get the text directly if no spans
                    comment_text = content_copy.get_text(strip=True)
                
                # Get likes/upvotes
                likes = "0"
                
                # First try to find the upvote button
                reaction_div = comment_container.find('div', class_='wcc_CommentReaction__root')
                if reaction_div:
                    upvote_buttons = reaction_div.find_all('button', class_='wcc_CommentReaction__action')
                    if upvote_buttons and len(upvote_buttons) > 0:
                        upvote_button = upvote_buttons[0]  # First button is usually upvote
                        upvote_span = upvote_button.find('span')
                        if upvote_span:
                            likes = upvote_span.text.strip()
                
                # Skip empty comments
                if not comment_text:
                    continue
                
                comments.append({
                    'username': username,
                    'date': date,
                    'text': comment_text,
                    'likes': likes
                })
                
                # Print the extracted comment
                if len(comments) <= 5:  # Print first 5 for debugging
                    print(f"Extracted comment from {username}: \"{comment_text}\" | Date: {date} | Likes: {likes}")
        except Exception as e:
            print(f"Error extracting a comment: {e}")
            continue
    
    print(f"Successfully scraped {len(comments)} comments")
    return comments

def summarize_comments(comments):
    """Generate a summary of the comments for an episode"""
    if not comments:
        return "No comments available for this episode."
    
    try:
        print("Generating comment summary...")
        # Download necessary NLTK data (only first time)
        nltk_packages = ['punkt', 'stopwords', 'vader_lexicon']
        for package in nltk_packages:
            try:
                print(f"Checking for NLTK package: {package}")
                if package == 'punkt':
                    nltk.data.find(f'tokenizers/{package}')
                elif package == 'stopwords':
                    nltk.data.find(f'corpora/{package}')
                elif package == 'vader_lexicon':
                    nltk.data.find(f'sentiment/{package}')
                print(f"Package {package} already downloaded")
            except LookupError:
                print(f"Downloading NLTK package: {package}")
                nltk.download(package)
                print(f"Downloaded {package} successfully")
        
        # Use a simple approach if NLTK still has issues
        try:
            # Check if we can import and use these components
            from nltk.tokenize import word_tokenize
            from nltk.corpus import stopwords
            from nltk.sentiment import SentimentIntensityAnalyzer
            _ = word_tokenize("Test sentence")
            _ = stopwords.words('english')
            _ = SentimentIntensityAnalyzer().polarity_scores("Test sentence")
            print("NLTK components working correctly")
        except Exception as e:
            print(f"NLTK still has issues: {e}")
            print("Using simplified comment analysis due to NLTK data issues")
            return generate_simple_summary(comments)
        
        # Get English stopwords
        print("Processing stopwords...")
        stop_words = set(stopwords.words('english'))
        
        # Extract text from all comments
        print(f"Analyzing {len(comments)} comments...")
        all_text = " ".join([comment['text'] for comment in comments])
        
        # Tokenize and filter out stopwords
        print("Tokenizing text...")
        words = [word.lower() for word in word_tokenize(all_text) if word.isalnum() and word.lower() not in stop_words]
        
        # Get most common words (top 10)
        print("Finding most common words...")
        if not words:
            common_words = ["No common words found"]
        else:
            most_common = Counter(words).most_common(10)
            common_words = [word for word, _ in most_common] if most_common else ["No common words found"]
        
        # Calculate average comment length
        print("Calculating average comment length...")
        avg_length = sum(len(comment['text'].split()) for comment in comments) / len(comments)
        
        # Analyze sentiment
        print("Analyzing sentiment...")
        sia = SentimentIntensityAnalyzer()
        sentiments = [sia.polarity_scores(comment['text'])['compound'] for comment in comments]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        # Determine sentiment category
        if avg_sentiment > 0.2:
            sentiment_category = "positive"
        elif avg_sentiment < -0.2:
            sentiment_category = "negative"
        else:
            sentiment_category = "neutral"
        
        # Find the most upvoted comment
        print("Finding most upvoted comment...")
        try:
            most_upvoted = max(comments, key=lambda x: int(x['likes'].replace(',', '')) if x['likes'].replace(',', '').isdigit() else 0)
            top_comment = most_upvoted['text']
            top_likes = most_upvoted['likes']
        except Exception as e:
            print(f"Error finding most upvoted comment: {e}")
            top_comment = "No notable comments found"
            top_likes = "0"
        
        # Generate summary
        print("Generating final summary...")
        summary = f"A total of {len(comments)} comments were analyzed for this episode. "
        summary += f"The overall sentiment is {sentiment_category} (score: {avg_sentiment:.2f}). "
        summary += f"The most discussed topics include: {', '.join(common_words[:5])}. "
        summary += f"The average comment contains {avg_length:.1f} words. "
        summary += f"Most upvoted comment ({top_likes} likes): \"{top_comment[:50]}{'...' if len(top_comment) > 50 else ''}\""
        
        print("Summary generation complete!")
        return summary
    except Exception as e:
        print(f"Error generating comment summary: {str(e)}")
        import traceback
        traceback.print_exc()
        # Fall back to simple summary
        return generate_simple_summary(comments)

def generate_simple_summary(comments):
    """Generate a simplified summary without NLTK dependencies"""
    try:
        print("Generating simplified summary...")
        # Find comment lengths
        comment_lengths = [len(comment['text'].split()) for comment in comments]
        avg_length = sum(comment_lengths) / len(comment_lengths)
        
        # Find most common words using basic python
        all_words = []
        for comment in comments:
            # Simple tokenization by splitting on spaces
            words = [w.lower() for w in comment['text'].split() if len(w) > 3]
            all_words.extend(words)
        
        # Get word frequencies
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        common_words = [word for word, _ in sorted_words[:5]]
        
        # Find most upvoted comment
        try:
            most_upvoted = max(comments, key=lambda x: int(x['likes'].replace(',', '')) if x['likes'].replace(',', '').isdigit() else 0)
            top_comment = most_upvoted['text']
            top_likes = most_upvoted['likes']
        except:
            top_comment = "No notable comments found"
            top_likes = "0"
        
        # Generate summary
        summary = f"A total of {len(comments)} comments were analyzed for this episode. "
        if common_words:
            summary += f"Frequently mentioned words include: {', '.join(common_words)}. "
        summary += f"The average comment contains {avg_length:.1f} words. "
        summary += f"Most upvoted comment ({top_likes} likes): \"{top_comment[:50]}{'...' if len(top_comment) > 50 else ''}\""
        
        return summary
    except Exception as e:
        print(f"Error generating simplified summary: {str(e)}")
        return f"Summary generation failed. Raw data includes {len(comments)} comments. Error: {str(e)}"

def save_comments_to_file(comments, folder, episode_no):
    """Save scraped comments to a text file"""
    if not comments:
        return
    
    comment_file = os.path.join(folder, f"comments_episode_{episode_no}.txt")
    with open(comment_file, 'w', encoding='utf-8') as f:
        f.write(f"Comments for Episode {episode_no}\n")
        f.write(f"Total comments: {len(comments)}\n")
        f.write("-" * 50 + "\n\n")
        
        # Generate and add comment summary
        summary = summarize_comments(comments)
        f.write("SUMMARY:\n")
        f.write(summary + "\n\n")
        f.write("-" * 50 + "\n\n")
        
        for i, comment in enumerate(comments, 1):
            f.write(f"#{i} | {comment['username']} | {comment['date']} | Likes: {comment['likes']}\n")
            f.write(f"{comment['text']}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"Saved {len(comments)} comments with summary to {comment_file}")

def get_chapter_images_and_comments(chapter_url, use_selenium=False):
    """Scrape all image URLs and comments from a chapter"""
    print(f"Fetching images and comments from chapter: {chapter_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
    }
    
    # If using Selenium, get the page with a browser
    if use_selenium:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            
            print("Using Selenium to load the page with JavaScript...")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={headers['User-Agent']}")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(chapter_url)
            
            # Wait for comments to load - we'll look for comment elements
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "wcc_CommentItem__root"))
                )
                print("Comments loaded successfully!")
            except TimeoutException:
                print("Timed out waiting for comments to load - will still try to extract any available")
            
            # Get the page source after JavaScript has run
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Create a session to use for image downloads
            session = requests.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            
            driver.quit()
        except ImportError:
            print("Selenium not installed. Please install it with: pip install selenium")
            print("Falling back to requests-based scraping...")
            use_selenium = False
        except Exception as e:
            print(f"Error using Selenium: {e}")
            print("Falling back to requests-based scraping...")
            use_selenium = False
    
    # If not using Selenium or Selenium failed, use requests
    if not use_selenium:
        # First get cookies from the main site
        session = requests.Session()
        soup = None
        
        try:
            # Get cookies from the main site
            session.get('https://www.webtoons.com/', headers=headers)
            
            # Now get the chapter page with the cookies
            response = session.get(chapter_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching chapter: {e}")
            return [], session, None
    
    # Find the container for the webtoon images
    content_container = soup.find('div', id='_imageList')
    if not content_container:
        # Try alternative containers
        content_container = soup.find('div', id='content')
        if not content_container:
            content_container = soup.find('div', class_='viewer_lst')
        if not content_container:
            content_container = soup  # Fall back to entire page if specific containers not found
    
    # Find all images in the container
    images = content_container.find_all('img')
    image_urls = []
    
    for img in images:
        # Try different attributes for the image source
        src = img.get('data-url') or img.get('data-src') or img.get('src')
        
        if src:
            # Clean up the URL (sometimes URLs have escaped characters)
            src = src.replace('&amp;', '&')
            
            # Ensure absolute URL
            if not src.startswith('http'):
                src = urljoin(chapter_url, src)
            
            # Filter out small images, icons, etc.
            # Most content images have specific patterns in URLs or are larger
            if ('webtoon-phinf' in src or 'comic.naver' in src or 'daumcdn' in src) and not src.endswith('.gif'):
                image_urls.append(src)
    
    # If no images found with standard methods, try JavaScript extraction
    if not image_urls:
        print("Trying to extract image URLs from JavaScript...")
        # Look for JavaScript that might contain image URLs
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for image URLs in JavaScript arrays or JSON
                matches = re.findall(r'https?://[^\s\'"]+\.(jpg|jpeg|png|webp)', script.string)
                for match in matches:
                    image_urls.append(match[0])  # match[0] contains the full URL
    
    print(f"Found {len(image_urls)} images in chapter")
    return image_urls, session, soup

def download_image(url, folder, filename, session, headers):
    """Download an image from a URL using an established session"""
    try:
        # Use the session to maintain cookies
        response = session.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        # Check if we got an actual image
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith(('image/', 'application/octet-stream')):
            print(f"Warning: URL {url} returned content type {content_type}, which may not be an image")
            
            # Try to verify content length is reasonable for an image
            content_length = int(response.headers.get('Content-Length', 0))
            if content_length < 1000:  # Very small files are suspicious
                print(f"Warning: Content length {content_length} bytes is suspiciously small")
                # We'll continue anyway to see what we get
        
        file_path = os.path.join(folder, filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # Verify the file is an actual image
        file_size = os.path.getsize(file_path)
        if file_size < 1000:
            print(f"Warning: Downloaded file {filename} is only {file_size} bytes")
        
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def download_chapter_images(chapter_url, output_dir, max_workers=20, use_selenium=True):
    """Download all images from a chapter and extract comments"""
    # Extract chapter info
    episode_no, chapter_title = extract_chapter_info(chapter_url)
    sanitized_title = re.sub(r'[\\/*?:"<>|]', "-", chapter_title)  # Remove invalid filename characters
    
    # Create folder for this chapter
    chapter_folder = os.path.join(output_dir, f"Episode_{episode_no}_{sanitized_title}")
    os.makedirs(chapter_folder, exist_ok=True)
    
    # Get all image URLs for this chapter, the session, and the soup
    image_urls, session, soup = get_chapter_images_and_comments(chapter_url, use_selenium=use_selenium)
    
    if not image_urls:
        print(f"No images found for chapter {episode_no}")
        return 0
    
    # Scrape and save comments if soup is available
    if soup:
        comments = extract_comments(soup, chapter_url)
        save_comments_to_file(comments, chapter_folder, episode_no)
    
    # Prepare headers for download
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': chapter_url,
        'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    # Download images - use more workers for speed
    successful_downloads = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = []
        for i, url in enumerate(image_urls):
            parsed_url = urlparse(url)
            base_path = parsed_url.path
            _, extension = os.path.splitext(base_path)
            if not extension or len(extension) <= 1:
                if 'jpg' in url or 'jpeg' in url:
                    extension = '.jpg'
                elif 'png' in url:
                    extension = '.png'
                elif 'webp' in url:
                    extension = '.webp'
                else:
                    extension = '.jpg'
            filename = f"{i+1:03d}{extension}"
            tasks.append(executor.submit(download_image, url, chapter_folder, filename, session, headers))
        total_images = len(tasks)
        for i, future in enumerate(as_completed(tasks)):
            if future.result():
                successful_downloads += 1
            progress = (i + 1) / total_images * 100
            print(f"Progress: [{i+1}/{total_images}] {progress:.1f}% - Downloaded: {successful_downloads}", end='\r')
    print(f"\nDownloaded {successful_downloads}/{total_images} images for Episode {episode_no}")
    return successful_downloads

def prompt_for_chapter_selection(chapters):
    """Prompt the user to select which chapters to download"""
    print("\nAvailable chapters:")
    
    # Extract chapter information for display
    chapter_info = []
    for i, chapter_url in enumerate(chapters):
        episode_no, chapter_title = extract_chapter_info(chapter_url)
        chapter_info.append((i, episode_no, chapter_title, chapter_url))
    
    # Sort by episode number (newest first, typically)
    chapter_info.sort(key=lambda x: int(x[1]), reverse=True)
    
    # Display chapters
    for i, (idx, episode_no, title, _) in enumerate(chapter_info):
        print(f"{i+1}. Episode {episode_no}: {title}")
    
    # Get user selection
    print("\nSelect chapters to download:")
    print("Options:")
    print("  - Enter chapter numbers separated by commas (e.g., '1,3,5')")
    print("  - Enter a range (e.g., '1-5')")
    print("  - Enter 'all' to download all chapters")
    print("  - Enter 'q' to quit")
    
    selection = input("\nEnter your selection: ").strip().lower()
    
    if selection == 'q':
        return []
    
    if selection == 'all':
        return [info[3] for info in chapter_info]  # Return all chapter URLs
    
    selected_chapters = []
    
    # Process comma-separated values and ranges
    parts = selection.split(',')
    for part in parts:
        part = part.strip()
        
        # Check if it's a range (e.g., "1-5")
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                # Adjust for 1-based indexing that we showed to the user
                if 1 <= start <= len(chapter_info) and 1 <= end <= len(chapter_info):
                    for i in range(start, end + 1):
                        selected_chapters.append(chapter_info[i-1][3])  # Get the URL
            except ValueError:
                print(f"Invalid range: {part}")
        else:
            # Single chapter number
            try:
                idx = int(part)
                if 1 <= idx <= len(chapter_info):
                    selected_chapters.append(chapter_info[idx-1][3])  # Get the URL
                else:
                    print(f"Chapter number {idx} is out of range")
            except ValueError:
                print(f"Invalid chapter number: {part}")
    
    return selected_chapters

def save_links_to_file(links, title_no, series_name):
    """Save the chapter links to a JSON file"""
    output_dir = f"webtoon_{title_no}_{series_name}" if title_no else "webtoon_chapters"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "chapter_links.json")
    
    data = {
        "title_no": title_no,
        "series_name": series_name,
        "total_chapters": len(links),
        "chapters": links
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved {len(links)} chapter links to {output_file}")
    return output_file, output_dir

def download_multiple_chapters(chapter_links, output_dir, max_workers_chapters=4, max_workers_images=20, use_selenium=True):
    results = {}
    def download_one(link):
        return link, download_chapter_images(link, output_dir, max_workers=max_workers_images, use_selenium=use_selenium)
    with ThreadPoolExecutor(max_workers=max_workers_chapters) as executor:
        future_to_link = {executor.submit(download_one, link): link for link in chapter_links}
        for future in as_completed(future_to_link):
            link, count = future.result()
            results[link] = count
    return results

def main():
    # Set up argument parser with url as optional
    parser = argparse.ArgumentParser(description='Scrape chapter links and images from a Webtoon series')
    parser.add_argument('url', nargs='?', help='URL of the Webtoon series page')
    parser.add_argument('--download', action='store_true', help='Download chapter images')
    parser.add_argument('--threads', type=int, default=10, help='Number of download threads (default: 10)')
    parser.add_argument('--no-selenium', action='store_true', help='Disable Selenium for comment scraping (not recommended)')
    args = parser.parse_args()
    
    # If no URL provided via command line, ask for it
    url = args.url
    if not url:
        url = input("Please enter the URL of the Webtoon series: ").strip()
        
        # Check if URL was provided
        if not url:
            print("No URL provided. Exiting.")
            sys.exit(1)
    
    # Get chapter links
    chapter_links = get_chapter_links(url)
    
    if not chapter_links:
        print("No chapter links found.")
        sys.exit(1)
    
    # Extract series info
    title_no, series_name = extract_webtoon_info(url)
    
    # Save links to file
    output_file, output_dir = save_links_to_file(chapter_links, title_no, series_name)
    print(f"Chapter links saved to: {output_file}")
    
    # Prompt user for download
    download_images = args.download
    if not download_images:
        choice = input("\nDo you want to download chapter images? (y/n): ").strip().lower()
        download_images = choice.startswith('y')
    
    if download_images:
        # Let user select which chapters to download
        selected_chapters = prompt_for_chapter_selection(chapter_links)
        
        if not selected_chapters:
            print("No chapters selected for download.")
            sys.exit(0)
        
        print(f"\nDownloading {len(selected_chapters)} chapters...")
        
        # Determine whether to use Selenium
        use_selenium = not args.no_selenium
        if use_selenium:
            print("Using Selenium for improved comment scraping. Install with 'pip install selenium' if not installed.")
        else:
            print("Selenium disabled. Comments may not be scraped correctly.")
        
        # Download each selected chapter
        total_downloaded = 0
        for i, chapter_url in enumerate(selected_chapters):
            print(f"\nDownloading chapter {i+1}/{len(selected_chapters)}")
            images_downloaded = download_chapter_images(chapter_url, output_dir, max_workers=args.threads, use_selenium=use_selenium)
            total_downloaded += images_downloaded
        
        print(f"\nDownload complete! Downloaded {total_downloaded} images across {len(selected_chapters)} chapters.")
        print(f"Files saved to: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    main() 