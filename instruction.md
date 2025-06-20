# Manga Scraper Pro - Instructions

## Overview
Manga Scraper Pro allows you to download manga and webtoons from online sources with a user-friendly interface. This guide will help you set up and use the application effectively.

## Installation Instructions

### Prerequisites
- Windows/Mac/Linux computer
- Internet connection
- At least 1GB free disk space

### Step 1: Install Python
1. Visit [python.org](https://www.python.org/downloads/)
2. Download Python 3.8 or newer
3. Run the installer
   - **Important**: Check "Add Python to PATH" before installing
   - Click "Install Now"
4. Verify installation by opening Command Prompt (Windows) or Terminal (Mac/Linux) and typing:
   ```
   python --version
   ```
   You should see the Python version displayed.

### Step 2: Download the Application
1. Extract all files from the ZIP archive to a folder of your choice
2. Make sure all files are in the same folder

### Step 3: Install Required Libraries
1. Open Command Prompt (Windows) or Terminal (Mac/Linux)
2. Navigate to the application folder:
   ```
   cd path/to/application/folder
   ```
   Replace "path/to/application/folder" with the actual path where you extracted the files
3. Install required libraries:
   ```
   pip install -r requirements.txt
   ```
4. Wait for all libraries to install successfully

## Using the Application

### Starting the Application
1. Open Command Prompt (Windows) or Terminal (Mac/Linux)
2. Navigate to the application folder
3. Run the application:
   ```
   python manga_scraper_gui.py
   ```
4. The graphical interface should appear on your screen

### Downloading a Single Manga Series
1. Find the manga/webtoon URL you want to download 
   - Example URL format: https://www.webtoons.com/en/action/designated-bully/list?title_no=4866
2. Copy the URL
3. Paste it into the URL field in the application
4. Choose a download location:
   - Click the "Choose" button
   - Select the folder where you want to save the manga
5. Click "🚀 Start Download"
6. Monitor progress in the status bar and log window
7. Wait for the "Download Complete" message

### Downloading Multiple Series at Once
1. Click "Download All From Genres Page"
2. Read the warning carefully - this can take a lot of time and disk space
3. Confirm to proceed
4. Wait for the process to complete

### Canceling a Download
- Click the "⏹️ Stop" button at any time to cancel an ongoing download

## Understanding the Download Structure

After downloading, your manga will be organized as follows:
```
Downloads/
  ├── [Manga Title]/
  │    ├── info.json
  │    ├── cover.jpg
  │    ├── Episode_1_[Episode Title]/
  │    │    ├── 001.jpg
  │    │    ├── 002.jpg
  │    │    └── ...
  │    ├── Episode_2_[Episode Title]/
  │    └── ...
  └── [Another Manga Title]/
       └── ...
```

## Troubleshooting

### Application Won't Start
- Make sure Python is installed correctly
- Verify you installed the required libraries
- Try running as administrator/with elevated privileges

### Missing Library Error
- Run the installation command again:
  ```
  pip install requests beautifulsoup4 customtkinter rich art urllib3
  ```

### Download Fails or Stops
- Check your internet connection
- Try a different manga URL
- Ensure you have enough disk space
- Some sites may block automated downloads - try again later

### Images Not Downloading Correctly
- Check if the manga is accessible on the website normally
- Try a different manga to see if the issue persists
- The site structure may have changed, requiring an application update

## Advanced Tips

### Increasing Download Speed
- The application uses 30 parallel threads by default
- If you have a fast internet connection, you can modify this in the code:
  1. Open `manga_scraper_gui.py` in a text editor
  2. Find the line `self.max_workers = 30` in the MangaScraper class
  3. Change to a higher number (e.g., 40-50) if you have fast internet
  4. Save and restart the application

### Conserving Memory
- For computers with limited RAM, reduce the number of parallel threads:
  1. Find the line `self.max_workers = 30` in the code
  2. Change to a lower number (e.g., 10-15)
  3. Save and restart the application

## Legal Considerations

- This tool is for personal use only
- Only download content you have the right to access
- Respect copyright laws in your country
- Do not distribute downloaded content

## Need More Help?
If you encounter issues not covered in this guide, please contact support with:
- A description of the problem
- Steps to reproduce the issue
- Any error messages you see 