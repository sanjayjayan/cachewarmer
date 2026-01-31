# CacheWarmer

CacheWarmer is a Windows application designed to automatically find and pre-cache torrents from Torrentio into a Real-Debrid account. It helps ensure that content is available in your cloud storage before you attempt to stream it.

## Features

- Scrapes Torrentio for movie and TV series streams.
- Filters by resolution, seeders, and file size.
- Supports IMDb list URLs for bulk caching.
- Supports individual IMDb IDs or titles for movies and series.
- Automatically handles TV series by fetching episode lists.
- Runs in the background with a system tray icon.
- Configurable run modes: One-shot, Loop, or Interval.
- Low process priority to minimize system impact.
- Local database (cache.db) to track previously processed items.

## Installation

### Binary
1. Download the latest release from the releases page.
2. Extract the files and run `CacheWarmer.exe`.

### From Source
1. Ensure Python 3.10+ is installed.
2. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run with:
   ```bash
   python main.py
   ```

## Configuration

The application uses a `config.json` file for settings. When using the GUI, these can be managed through the interface.

- **Real-Debrid API Key**: Required for communication with the Real-Debrid API.
- **Delay Between Items**: Time in seconds to wait between processing different titles.
- **Minimum Seeders**: Filters out torrents with low seeder counts.
- **Minimum Resolution**: Sets the minimum quality (720, 1080, 2160).
- **Max Per Quality**: Number of torrents to add per resolution.
- **Allow Pack Fallback**: If no single episode files are found, the app can attempt to cache a season pack instead.

## Usage

### Movies
Enter IMDb IDs (tt0133093) or movie titles in the Movies box. Enter one per line.

### TV Series
Enter IMDb IDs or series URLs. The app resolves the series and processes all seasons/episodes found.

### IMDb Lists
Paste URLs for public IMDb lists (e.g., https://www.imdb.com/list/ls.../). The app will parse the list and add all found titles to the queue.

### Tray Icon
Closing the main window will minimize the app to the tray. Right-click the tray icon to show the window, start/stop the service, or exit.

## Development

To build the executable yourself, run:
```cmd
build_exe.bat
```
This requires PyInstaller to be installed. The output will be located in the `dist` folder.

## Disclaimer
This tool is for personal use and educational purposes. It does not host or distribute content. Users are responsible for their own use of the software and compliance with local regulations.
