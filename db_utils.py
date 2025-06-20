import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.getcwd(), 'manga_collection.db')

MANGA_TABLE = '''
CREATE TABLE IF NOT EXISTS manga (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_no TEXT,
    series_name TEXT,
    display_title TEXT,
    author TEXT,
    genre TEXT,
    num_chapters INTEGER,
    url TEXT,
    last_updated TEXT,
    grade REAL,
    views TEXT,
    subscribers TEXT,
    day_info TEXT
);
'''

CHAPTER_TABLE = '''
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manga_id INTEGER,
    episode_no TEXT,
    chapter_title TEXT,
    url TEXT,
    FOREIGN KEY(manga_id) REFERENCES manga(id)
);
'''

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(MANGA_TABLE)
        c.execute(CHAPTER_TABLE)
        conn.commit()

def insert_or_update_manga(title_no, series_name, display_title, author, genre, num_chapters, url, grade=None, views=None, subscribers=None, day_info=None):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT id FROM manga WHERE title_no=? AND series_name=?''', (title_no, series_name))
        row = c.fetchone()
        now = datetime.utcnow().isoformat()
        if row:
            manga_id = row[0]
            c.execute('''UPDATE manga SET display_title=?, author=?, genre=?, num_chapters=?, url=?, last_updated=?, grade=?, views=?, subscribers=?, day_info=? WHERE id=?''',
                      (display_title, author, genre, num_chapters, url, now, grade, views, subscribers, day_info, manga_id))
        else:
            c.execute('''INSERT INTO manga (title_no, series_name, display_title, author, genre, num_chapters, url, last_updated, grade, views, subscribers, day_info) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (title_no, series_name, display_title, author, genre, num_chapters, url, now, grade, views, subscribers, day_info))
            manga_id = c.lastrowid
        conn.commit()
        return manga_id

def insert_chapters(manga_id, chapters):
    # chapters: list of dicts with episode_no, chapter_title, url
    with get_connection() as conn:
        c = conn.cursor()
        for ch in chapters:
            c.execute('''INSERT INTO chapters (manga_id, episode_no, chapter_title, url) VALUES (?, ?, ?, ?)''',
                      (manga_id, ch['episode_no'], ch['chapter_title'], ch['url']))
        conn.commit()

def get_all_manga():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM manga')
        return c.fetchall()

def query_manga_by_genre(genre):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM manga WHERE genre LIKE ?', (f'%{genre}%',))
        return c.fetchall()

def query_manga_by_author(author):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM manga WHERE author LIKE ?', (f'%{author}%',))
        return c.fetchall()

def query_manga_by_title(title):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM manga WHERE display_title LIKE ?', (f'%{title}%',))
        return c.fetchall()

def query_manga_by_min_chapters(min_chapters):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM manga WHERE num_chapters >= ?', (min_chapters,))
        return c.fetchall() 