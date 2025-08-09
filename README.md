# Ani-CLI GUI

A Python GUI application that provides a user-friendly interface for ani-cli, with integrated anime database search using MAL-Sync compatible APIs. Search for anime with detailed information and play them directly from your desktop.

## ✨ Features

### 🔍 Enhanced Anime Search
- **Database Search**: Search anime using Jikan API (MyAnimeList) and AniList GraphQL API
- **Detailed Information**: View anime titles, episodes, scores, genres, and descriptions
- **Smart Selection**: Click on search results to select and play anime
- **Multiple Title Support**: Choose between original and English titles
- **Rich Metadata**: See release years, episode counts, ratings, and more

### ▶️ Direct Play (Original Features)
- **Quick Access**: Direct anime name input for immediate search and play
- **Quality Selection**: Choose video quality (480p, 720p, 1080p, best, worst)
- **Episode Selection**: Specify individual episodes or ranges (e.g., "1" or "1-5")
- **Download Option**: Download videos instead of streaming
- **Dubbed Content**: Option to play dubbed versions
- **VLC Support**: Use VLC player for video playback
- **Continue Watching**: Resume from your viewing history

### 🎛️ Common Features
- **Real-time Output**: See ani-cli output in real-time
- **Process Control**: Stop running processes
- **Tabbed Interface**: Clean separation between search and direct play
- **Dark Theme**: Modern dark interface using CustomTkinter

## Requirements

- Python 3.7 or higher
- Git Bash (with ani-cli installed)
- Internet connection (for anime database search)
- customtkinter
- requests

## Installation

1. Make sure ani-cli is installed in your Git Bash environment
2. The Python virtual environment is already set up in this directory
3. All required packages are installed

## Usage

### Method 1: Using the Batch File (Recommended)
Double-click `run_gui.bat` to start the application.

### Method 2: Using PowerShell
```powershell
# Navigate to the project directory
cd "C:\Users\DrAnimo\Documents\anime"

# Activate virtual environment and run
.venv\Scripts\Activate.ps1; python ani_cli_gui.py
```

### Method 3: Using Command Prompt
```cmd
# Navigate to the project directory
cd "C:\Users\DrAnimo\Documents\anime"

# Activate virtual environment and run
.venv\Scripts\activate.bat
python ani_cli_gui.py
```

## How to Use the GUI

### 🔍 Search Tab (Recommended)

1. **Search for Anime**:
   - Enter the anime name in the search box
   - Click "Search" or press Enter
   - Browse through the search results with detailed information

2. **Select and Play**:
   - Click on any search result to select it
   - The selected anime will be highlighted in blue
   - Configure quality, episodes, and other options
   - Click "Play Selected Anime"

3. **Title Selection**:
   - If both original and English titles are available, you'll be prompted to choose
   - This ensures the best match with ani-cli's database

### ▶️ Direct Play Tab

1. **Quick Search**:
   - Enter the anime name directly
   - Select your preferred quality and options
   - Click "Search & Play" for immediate access

2. **Continue Watching**:
   - Click "Continue from History" to resume from your last watched episode
   - Or check the "Continue from History" checkbox before searching

### 🎛️ Options (Both Tabs)

- **Quality**: Choose video resolution
- **Episode(s)**: Enter episode number (e.g., "1") or range (e.g., "1-5")
- **Download**: Download the video instead of streaming
- **Dubbed**: Play dubbed version if available
- **Use VLC**: Use VLC media player for playback
- **Continue from History**: Resume from your viewing history

### 📊 Monitor Progress

- The output area shows real-time information from ani-cli
- The status bar shows the current operation status
- Use the "Stop" button to cancel any running operation

## Examples

### Using Search Tab:
1. Search for "attack on titan"
2. Browse results and select "Shingeki no Kyojin (Attack on Titan)"
3. Set quality to "1080p", episodes to "1-5"
4. Click "Play Selected Anime"

### Using Direct Play Tab:
- **Watch One Piece episode 1 in 720p**: 
  - Search: "one piece"
  - Quality: "720p"
  - Episode: "1"

- **Download Attack on Titan episodes 1-5 in 1080p**:
  - Search: "attack on titan"
  - Quality: "1080p" 
  - Episode: "1-5"
  - Check "Download"

## API Information

The application uses multiple anime databases:

- **Jikan API**: Unofficial MyAnimeList API for comprehensive anime information
- **AniList GraphQL API**: Alternative source for anime data and metadata
- **Automatic Fallback**: If one API fails, the app tries the other for best results

All API calls are made respectfully with appropriate rate limiting and error handling.

## Troubleshooting

1. **"Git Bash not found" error**:
   - Make sure Git is installed and accessible at `C:\Program Files\Git\bin\bash.exe`
   
2. **"ani-cli may not be properly installed" warning**:
   - Make sure ani-cli is installed in your Git Bash environment
   - Test by running `ani-cli --version` in Git Bash

3. **Search not working**:
   - Check your internet connection
   - APIs may be temporarily unavailable, try again later
   - Use the Direct Play tab as an alternative

4. **GUI doesn't start**:
   - Make sure the virtual environment is activated
   - Run `pip install customtkinter requests` if needed

5. **No video plays**:
   - Make sure you have a compatible video player installed (mpv, VLC, etc.)
   - Check if the anime name is spelled correctly
   - Try using different title variations from search results

## File Structure

```
anime/
├── ani_cli_gui.py      # Main GUI application with search functionality
├── run_gui.bat         # Easy launcher script
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── .venv/             # Python virtual environment
```

## Notes

- The application integrates anime database search with ani-cli playback
- Search results provide rich metadata to help you find the right anime
- The tabbed interface allows both database search and quick direct access
- All ani-cli features are supported through the enhanced interface
- Search APIs are accessed respectfully with proper error handling

Enjoy discovering and watching anime with this enhanced GUI interface!
