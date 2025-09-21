# yt-dlp GUI

A simple, user-friendly graphical interface for [yt-dlp](https://github.com/yt-dlp/yt-dlp), allowing easy video and audio downloads from YouTube and many other sites.

## Features
- URL input with a dedicated "Paste from Clipboard" button
- Audio-only downloads (extracts MP3 via ffmpeg)
- Separate save locations for Video and Audio
- Optional per-download override: "Choose save location for each download"
- Authentication helpers:
  - Use cookies from browser (with optional profile)
  - Use cookies file (Netscape cookies.txt)
- Responsive UI with real-time yt-dlp output (runs work in a background thread)
- Persistent settings: window size, video directory, audio directory (stored in `yt_dlp_gui_config.json`)
- Check for updates: "Check for yt-dlp updates" button
- Helpful tooltips. Tip shown in-app: "Hover over items marked with '(i)' for more information."

## Requirements
- Python 3.9+
- ffmpeg available on PATH (required for muxing and audio extraction)
- yt-dlp installed (the app can invoke `yt-dlp` on PATH)

## Setup
Using uv (recommended):
```bash
uv pip install -r requirements.txt
```

Using pip:
```bash
python -m pip install -r requirements.txt
```

## Run
Using uv:
```bash
uv run python yt_dlp_gui.py
```

Or directly (with your venv activated):
```bash
python yt_dlp_gui.py
```

## Usage
1. Paste or enter a URL.
2. (Optional) Check "Audio only (extract as .mp3)" to download audio only.
3. Set default save locations for Video and Audio, or check "Choose save location for each download" to select a folder per download.
4. If the site requires login, use one of the cookies options:
   - Use cookies from browser: select your browser and optionally the profile name (e.g., Default, Profile 1). If the browser keeps its cookie database locked, fully close it first.
   - Use cookies file: provide a Netscape-format `cookies.txt` file.
     - How to create: install a cookies exporter extension in your browser; while logged in, open the site’s page and export cookies as Netscape `cookies.txt`.
5. Click Download. Status and yt-dlp output will stream in the log area.
6. Use "Check for yt-dlp updates" to see if a newer yt-dlp release is available, with suggested upgrade commands.

## Troubleshooting
- Missing ffmpeg: install it and ensure `ffmpeg` is on PATH.
- Login required: supply cookies (browser/profile or `cookies.txt`).
- Browser cookie DB locked: fully close the browser, or use the cookies file method.
- Authorization/403 or geo errors: these are site-specific; cookies or a different region may be required. Some protected/DRM content cannot be downloaded.

## Roadmap

### Core Features
- URL input and download
- Paste from clipboard
- Download directory selection (separate for video and audio)
- Per-download save location override
- Persistent settings (window size, download directories)
- Responsive UI with real-time status updates
- Cookies support (browser + profile, cookies.txt)
- Check for yt-dlp updates button
- Helpful tooltips with '(i)' markers

### Planned Enhancements
1. **Download Options**
    - Video quality selection (best, worst, 720p, etc.)
    - Custom output filename template
    - Subtitles download (with language selection)
2. **Batch Downloads**
    - Support for multiple URLs (one per line or from a file)
    - Show a queue and progress for each item
3. **Download Progress**
    - Progress bar for current download
    - Estimated time remaining, speed, etc.
4. **Download History**
    - List of previously downloaded items
    - Open file/folder buttons
5. **Error Handling & Logging**
    - Dedicated errors tab or area
    - Save logs to a file
6. **System Integration**
    - "Open download folder" button
    - Notifications on download complete
7. **Advanced yt-dlp Options**
    - Custom arguments field
    - Option to use a custom yt-dlp binary
8. **UI/UX Improvements**
    - Dark mode toggle
    - About/help dialog

---

Contributions and suggestions are welcome! Open an issue or PR with ideas or improvements.