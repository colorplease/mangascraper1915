# Webtoon Chapter Scraper

A simple script to scrape all chapter links from a Webtoon series page.

## Installation

1. Make sure you have Python 3.6 or newer installed
2. Install the required libraries:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with a Webtoon series URL:

```bash
python webtoon_scraper.py "https://www.webtoons.com/en/graphic-novel/beneath-the-trees-where-nobody-sees/list?title_no=7680"
```

The script will:
1. Fetch the series page
2. Extract all chapter links
3. Save the links to a JSON file in a new directory named after the series

You can also provide a link to a specific episode, and the script will automatically convert it to the list page URL.

## Output

The script creates a directory named `webtoon_{title_no}_{series_name}` containing a `chapter_links.json` file with all chapter URLs.

Example output format:
```json
{
  "title_no": "7680",
  "series_name": "beneath-the-trees-where-nobody-sees",
  "total_chapters": 11,
  "chapters": [
    "https://www.webtoons.com/en/graphic-novel/beneath-the-trees-where-nobody-sees/episode-1/viewer?title_no=7680&episode_no=1",
    "https://www.webtoons.com/en/graphic-novel/beneath-the-trees-where-nobody-sees/episode-2/viewer?title_no=7680&episode_no=2",
    ...
  ]
}
``` 