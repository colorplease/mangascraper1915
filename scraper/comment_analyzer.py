"""
Comment analysis module for webtoon chapter comments.

This module handles extracting, analyzing, and summarizing comments
from webtoon chapter pages with comprehensive HTML parsing.
"""

import re
import os
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from collections import Counter

from models.chapter import Chapter


def extract_comments(soup: BeautifulSoup, chapter_url: str) -> List[Dict[str, Any]]:
    """Extract comments from a chapter page using comprehensive parsing."""
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
    
    # Still nothing? Try looking for the most specific class names
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


def summarize_comments(comments: List[Dict[str, Any]]) -> str:
    """Generate a comprehensive summary of the comments for an episode."""
    if not comments:
        return "No comments available for this episode."
    
    try:
        print("Generating comment summary...")
        # Try to use NLTK if available, but fall back to simple analysis
        try:
            import nltk
            from nltk.tokenize import word_tokenize
            from nltk.corpus import stopwords
            from nltk.sentiment import SentimentIntensityAnalyzer
            
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
            
            # Test if we can use NLTK components
            _ = word_tokenize("Test sentence")
            _ = stopwords.words('english')
            _ = SentimentIntensityAnalyzer().polarity_scores("Test sentence")
            print("NLTK components working correctly")
            
            return _generate_nltk_summary(comments)
        except Exception as e:
            print(f"NLTK not available or has issues: {e}")
            print("Using simplified comment analysis")
            return _generate_simple_summary(comments)
    except Exception as e:
        print(f"Error generating comment summary: {str(e)}")
        return _generate_simple_summary(comments)


def _generate_nltk_summary(comments: List[Dict[str, Any]]) -> str:
    """Generate summary using NLTK for advanced analysis."""
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.sentiment import SentimentIntensityAnalyzer
    
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


def _generate_simple_summary(comments: List[Dict[str, Any]]) -> str:
    """Generate a simplified summary without NLTK dependencies."""
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


def save_comments_to_file(comments: List[Dict[str, Any]], folder: str, episode_no: str) -> None:
    """Save scraped comments to a text file with summary."""
    if not comments:
        return
    
    # Ensure the directory exists
    os.makedirs(folder, exist_ok=True)
    
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


class CommentAnalyzer:
    """Analyzes and extracts comments from webtoon pages."""
    
    def __init__(self):
        self.nltk_available = self._check_nltk()
    
    def _check_nltk(self) -> bool:
        """Check if NLTK is available and properly configured."""
        try:
            import nltk
            from nltk.tokenize import word_tokenize
            from nltk.corpus import stopwords
            from nltk.sentiment import SentimentIntensityAnalyzer
            
            # Check if required data is available
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('corpora/stopwords')
                nltk.data.find('sentiment/vader_lexicon')
                return True
            except LookupError:
                print("NLTK data not found. Downloading required packages...")
                self._download_nltk_data()
                return True
                
        except ImportError:
            print("NLTK not installed. Comment analysis will use simplified methods.")
            return False
    
    def _download_nltk_data(self) -> None:
        """Download required NLTK data."""
        try:
            import nltk
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
        except Exception as e:
            print(f"Error downloading NLTK data: {e}")
    
    def extract_comments_from_soup(self, soup: BeautifulSoup, chapter_url: str) -> List[Dict[str, Any]]:
        """Extract comments from a chapter page's BeautifulSoup object."""
        print("Extracting comments from chapter page...")
        comments = []
        
        # Save debug HTML
        self._save_debug_html(soup)
        
        # Find comment containers
        comment_items = self._find_comment_elements(soup)
        print(f"Found {len(comment_items)} potential comment items")
        
        # Process each comment item
        for item in comment_items:
            try:
                comment_data = self._extract_comment_data(item)
                if comment_data and comment_data['text']:
                    comments.append(comment_data)
            except Exception as e:
                print(f"Error extracting comment: {e}")
                continue
        
        print(f"Successfully extracted {len(comments)} comments")
        return comments
    
    def _save_debug_html(self, soup: BeautifulSoup) -> None:
        """Save HTML for debugging purposes."""
        try:
            debug_file = "webtoon_page_debug.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(str(soup))
            print(f"Saved debug HTML to {debug_file}")
        except Exception as e:
            print(f"Could not save debug HTML: {e}")
    
    def _find_comment_elements(self, soup: BeautifulSoup) -> List:
        """Find comment elements in the soup."""
        all_comment_items = []
        
        # Method 1: Look for UL containers with comment lists
        comment_uls = soup.find_all('ul', class_=lambda c: c and any(
            cls in c for cls in ['commentList', 'CommentList', 'comment-list', 'wcc_CommentList']
        ))
        
        for ul in comment_uls:
            items = ul.find_all('li', class_=lambda c: c and any(
                cls in c for cls in ['wcc_CommentItem__root', 'CommentItem', 'comment-item']
            ))
            if items:
                all_comment_items.extend(items)
        
        # Method 2: Direct search for comment items
        if not all_comment_items:
            all_comment_items = soup.find_all('li', class_=lambda c: c and any(
                cls in c for cls in ['wcc_CommentItem', 'CommentItem', 'comment-item']
            ))
        
        # Method 3: Look for divs with comment inside class
        if not all_comment_items:
            inside_divs = soup.find_all('div', class_='wcc_CommentItem__inside')
            for div in inside_divs:
                parent = div.parent
                if parent and parent.name == 'li':
                    all_comment_items.append(parent)
                else:
                    all_comment_items.append(div)
        
        # Method 4: Find by content elements
        if not all_comment_items:
            content_els = soup.find_all('p', class_='wcc_TextContent__content')
            for content in content_els:
                parent = content
                for _ in range(5):  # Go up DOM tree
                    if parent is None:
                        break
                    parent = parent.parent
                    if parent and (parent.name == 'li' or 'CommentItem' in str(parent.get('class', []))):
                        all_comment_items.append(parent)
                        break
        
        return all_comment_items
    
    def _extract_comment_data(self, item) -> Optional[Dict[str, Any]]:
        """Extract comment data from a comment element."""
        # Find the comment container
        comment_container = item
        inside_div = item.find('div', class_='wcc_CommentItem__inside')
        if inside_div:
            comment_container = inside_div
        
        # Extract username
        username = self._extract_username(comment_container)
        
        # Extract date
        date = self._extract_date(comment_container)
        
        # Extract comment text
        comment_text = self._extract_comment_text(comment_container)
        
        # Extract likes
        likes = self._extract_likes(comment_container)
        
        if not comment_text:
            return None
        
        return {
            'username': username,
            'date': date,
            'text': comment_text,
            'likes': likes
        }
    
    def _extract_username(self, container) -> str:
        """Extract username from comment container."""
        selectors = [
            lambda: container.find('span', class_='wcc_CommentHeader__name'),
            lambda: container.find('a', class_='wcc_CommentHeader__name'),
            lambda: container.find(class_=lambda c: c and 'CommentHeader__name' in str(c))
        ]
        
        for selector in selectors:
            element = selector()
            if element:
                return element.text.strip()
        
        return "Unknown User"
    
    def _extract_date(self, container) -> str:
        """Extract date from comment container."""
        selectors = [
            lambda: container.find('time', class_='wcc_CommentHeader__createdAt'),
            lambda: container.find('time'),
            lambda: container.find(class_=lambda c: c and 'createdAt' in str(c))
        ]
        
        for selector in selectors:
            element = selector()
            if element:
                return element.text.strip()
        
        return "Unknown Date"
    
    def _extract_comment_text(self, container) -> Optional[str]:
        """Extract comment text from container."""
        selectors = [
            lambda: container.find('p', class_='wcc_TextContent__content'),
            lambda: container.find(class_=lambda c: c and 'TextContent__content' in str(c)),
            lambda: container.find('p')
        ]
        
        for selector in selectors:
            content_el = selector()
            if content_el:
                # Create a copy to modify
                content_copy = BeautifulSoup(str(content_el), 'html.parser')
                
                # Remove badge elements
                for badge in content_copy.find_all('span', class_=lambda c: c and (
                    'TopBadge' in str(c) or 'badge' in str(c).lower() or 'sr-only' in str(c)
                )):
                    badge.extract()
                
                # Get text from spans or directly
                spans = content_copy.find_all('span')
                if spans:
                    comment_text = ' '.join(span.text.strip() for span in spans)
                else:
                    comment_text = content_copy.get_text(strip=True)
                
                return comment_text if comment_text else None
        
        return None
    
    def _extract_likes(self, container) -> str:
        """Extract likes count from comment container."""
        reaction_div = container.find('div', class_='wcc_CommentReaction__root')
        if reaction_div:
            upvote_buttons = reaction_div.find_all('button', class_='wcc_CommentReaction__action')
            if upvote_buttons:
                upvote_button = upvote_buttons[0]  # First button is usually upvote
                upvote_span = upvote_button.find('span')
                if upvote_span:
                    return upvote_span.text.strip()
        
        return "0"
    
    def analyze_comments(self, comments: List[Dict[str, Any]]) -> str:
        """Generate a summary and analysis of comments."""
        if not comments:
            return "No comments available for this episode."
        
        if self.nltk_available:
            return self._analyze_with_nltk(comments)
        else:
            return self._analyze_simple(comments)
    
    def _analyze_with_nltk(self, comments: List[Dict[str, Any]]) -> str:
        """Analyze comments using NLTK."""
        try:
            from nltk.tokenize import word_tokenize
            from nltk.corpus import stopwords
            from nltk.sentiment import SentimentIntensityAnalyzer
            
            # Get stopwords
            stop_words = set(stopwords.words('english'))
            
            # Extract text from all comments
            all_text = " ".join([comment['text'] for comment in comments])
            
            # Tokenize and filter stopwords
            words = [word.lower() for word in word_tokenize(all_text) 
                    if word.isalnum() and word.lower() not in stop_words]
            
            # Get most common words
            common_words = [word for word, _ in Counter(words).most_common(10)] if words else []
            
            # Calculate average comment length
            avg_length = sum(len(comment['text'].split()) for comment in comments) / len(comments)
            
            # Analyze sentiment
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
            
            # Find most upvoted comment
            most_upvoted = max(comments, key=lambda x: int(x['likes'].replace(',', '')) 
                             if x['likes'].replace(',', '').isdigit() else 0)
            top_comment = most_upvoted['text']
            top_likes = most_upvoted['likes']
            
            # Generate summary
            summary = f"A total of {len(comments)} comments were analyzed for this episode. "
            summary += f"The overall sentiment is {sentiment_category} (score: {avg_sentiment:.2f}). "
            summary += f"The most discussed topics include: {', '.join(common_words[:5])}. "
            summary += f"The average comment contains {avg_length:.1f} words. "
            summary += f"Most upvoted comment ({top_likes} likes): \"{top_comment[:50]}{'...' if len(top_comment) > 50 else ''}\""
            
            return summary
            
        except Exception as e:
            print(f"Error in NLTK analysis: {e}")
            return self._analyze_simple(comments)
    
    def _analyze_simple(self, comments: List[Dict[str, Any]]) -> str:
        """Analyze comments using simple methods."""
        try:
            # Calculate average comment length
            comment_lengths = [len(comment['text'].split()) for comment in comments]
            avg_length = sum(comment_lengths) / len(comment_lengths)
            
            # Find common words using basic tokenization
            all_words = []
            for comment in comments:
                words = [w.lower() for w in comment['text'].split() if len(w) > 3]
                all_words.extend(words)
            
            # Count word frequencies
            word_counts = {}
            for word in all_words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # Get most common words
            sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            common_words = [word for word, _ in sorted_words[:5]]
            
            # Find most upvoted comment
            most_upvoted = max(comments, key=lambda x: int(x['likes'].replace(',', '')) 
                             if x['likes'].replace(',', '').isdigit() else 0)
            top_comment = most_upvoted['text']
            top_likes = most_upvoted['likes']
            
            # Generate summary
            summary = f"A total of {len(comments)} comments were analyzed for this episode. "
            if common_words:
                summary += f"Frequently mentioned words include: {', '.join(common_words)}. "
            summary += f"The average comment contains {avg_length:.1f} words. "
            summary += f"Most upvoted comment ({top_likes} likes): \"{top_comment[:50]}{'...' if len(top_comment) > 50 else ''}\""
            
            return summary
            
        except Exception as e:
            print(f"Error in simple analysis: {e}")
            return f"Summary generation failed. Raw data includes {len(comments)} comments."
    
    def save_comments_to_file(self, comments: List[Dict[str, Any]], 
                            chapter: Chapter, folder_path: str) -> None:
        """Save comments and analysis to a text file."""
        if not comments:
            return
        
        import os
        comment_file = os.path.join(folder_path, f"comments_episode_{chapter.episode_no}.txt")
        
        # Generate analysis
        summary = self.analyze_comments(comments)
        
        with open(comment_file, 'w', encoding='utf-8') as f:
            f.write(f"Comments for Episode {chapter.episode_no}\n")
            f.write(f"Total comments: {len(comments)}\n")
            f.write("-" * 50 + "\n\n")
            
            # Add summary
            f.write("SUMMARY:\n")
            f.write(summary + "\n\n")
            f.write("-" * 50 + "\n\n")
            
            # Add individual comments
            for i, comment in enumerate(comments, 1):
                f.write(f"#{i} | {comment['username']} | {comment['date']} | Likes: {comment['likes']}\n")
                f.write(f"{comment['text']}\n")
                f.write("-" * 50 + "\n\n")
        
        print(f"Saved {len(comments)} comments with analysis to {comment_file}")
        
        # Update chapter with comment data
        chapter.add_comments(comments, summary) 