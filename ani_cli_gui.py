import customtkinter as ctk
import subprocess
import threading
import tkinter.messagebox as messagebox
import os
import requests
import json
try:
    from PIL import Image, ImageTk
except ImportError:
    print("PIL/Pillow not found. Install with: pip install Pillow")
    Image = None
    ImageTk = None
from io import BytesIO
from typing import List, Dict, Optional
import webbrowser
import urllib.parse

class AnimeSearchAPI:
    """Class to handle anime search using MAL-Sync and Jikan APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AniCliGUI/1.0'
        })
    
    def search_anime_jikan(self, query: str, limit: int = 10) -> List[Dict]:
        """Search anime using Jikan API (MyAnimeList unofficial API)"""
        try:
            url = "https://api.jikan.moe/v4/anime"
            params = {
                'q': query,
                'limit': limit,
                'type': 'tv',
                'order_by': 'popularity',
                'sort': 'asc'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('data', []):
                anime_info = {
                    'title': item.get('title', ''),
                    'title_english': item.get('title_english', ''),
                    'episodes': item.get('episodes'),
                    'score': item.get('score'),
                    'year': item.get('year'),
                    'type': item.get('type', ''),
                    'genres': [genre['name'] for genre in item.get('genres', [])[:3]],  # Only first 3 genres
                    'image_url': item.get('images', {}).get('jpg', {}).get('image_url', ''),
                    'synopsis': item.get('synopsis', '')[:200] + "..." if item.get('synopsis') and len(item.get('synopsis', '')) > 200 else item.get('synopsis', '')
                }
                results.append(anime_info)
                
            return results
            
        except Exception as e:
            print(f"Error searching anime: {e}")
            return []
    
    def load_image_from_url(self, url: str, size: tuple = (80, 120)):
        """Load and resize image from URL"""
        try:
            if not url or not Image or not ImageTk:
                return None
                
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            image = image.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
            
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

class MALSyncIntegration:
    """Class to handle MAL-Sync integration for updating anime status"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AniCliGUI-MALSync/1.0'
        })
        
        # MAL API endpoints
        self.mal_api_base = "https://api.myanimelist.net/v2"
        self.mal_auth_url = "https://myanimelist.net/v1/oauth2/authorize"
        self.mal_token_url = "https://myanimelist.net/v1/oauth2/token"
        
        # AniList API
        self.anilist_api = "https://graphql.anilist.co"
        
        # Client ID for MAL (you would need to register an app)
        self.mal_client_id = "your_mal_client_id"  # Replace with actual client ID
        
        # Storage for tokens
        self.mal_token = None
        self.anilist_token = None
        
        # Load saved tokens
        self.load_tokens()
    
    def load_tokens(self):
        """Load saved authentication tokens from file"""
        try:
            if os.path.exists('mal_tokens.json'):
                with open('mal_tokens.json', 'r') as f:
                    data = json.load(f)
                    self.mal_token = data.get('mal_token')
                    self.anilist_token = data.get('anilist_token')
        except Exception as e:
            print(f"Error loading tokens: {e}")
    
    def save_tokens(self):
        """Save authentication tokens to file"""
        try:
            data = {
                'mal_token': self.mal_token,
                'anilist_token': self.anilist_token
            }
            with open('mal_tokens.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving tokens: {e}")
    
    def authenticate_mal(self):
        """Start MAL OAuth authentication process"""
        # Generate auth URL
        params = {
            'response_type': 'code',
            'client_id': self.mal_client_id,
            'redirect_uri': 'http://localhost:8080/auth/callback',
            'state': 'malsync_auth',
            'code_challenge_method': 'plain',
            'code_challenge': 'malsync_challenge'
        }
        
        auth_url = f"{self.mal_auth_url}?{urllib.parse.urlencode(params)}"
        webbrowser.open(auth_url)
        
        return "Please complete authentication in your browser"
    
    def authenticate_anilist(self):
        """Start AniList OAuth authentication process"""
        params = {
            'client_id': '12345',  # AniList client ID
            'response_type': 'token'
        }
        
        auth_url = f"https://anilist.co/api/v2/oauth/authorize?{urllib.parse.urlencode(params)}"
        webbrowser.open(auth_url)
        
        return "Please complete authentication in your browser"
    
    def update_anime_status(self, anime_id: int, episode: int, status: str = "watching", platform: str = "mal"):
        """Update anime episode progress and status"""
        try:
            if platform == "mal" and self.mal_token:
                return self._update_mal_anime(anime_id, episode, status)
            elif platform == "anilist" and self.anilist_token:
                return self._update_anilist_anime(anime_id, episode, status)
            else:
                return {"error": f"Not authenticated with {platform}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _update_mal_anime(self, anime_id: int, episode: int, status: str):
        """Update anime on MyAnimeList"""
        url = f"{self.mal_api_base}/anime/{anime_id}/my_list_status"
        headers = {
            'Authorization': f'Bearer {self.mal_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'status': status,
            'num_watched_episodes': episode,
        }
        
        # Auto-complete if watched all episodes
        if status == "completed":
            data['finish_date'] = self._get_current_date()
        elif status == "watching" and episode == 1:
            data['start_date'] = self._get_current_date()
        
        response = self.session.put(url, headers=headers, data=data)
        
        if response.status_code == 200:
            return {"success": True, "message": f"Updated episode {episode} on MAL"}
        else:
            return {"error": f"MAL API error: {response.status_code}"}
    
    def _update_anilist_anime(self, anime_id: int, episode: int, status: str):
        """Update anime on AniList"""
        query = """
        mutation ($id: Int, $progress: Int, $status: MediaListStatus) {
            SaveMediaListEntry(mediaId: $id, progress: $progress, status: $status) {
                id
                progress
                status
            }
        }
        """
        
        variables = {
            'id': anime_id,
            'progress': episode,
            'status': status.upper()
        }
        
        headers = {
            'Authorization': f'Bearer {self.anilist_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = self.session.post(
            self.anilist_api,
            json={'query': query, 'variables': variables},
            headers=headers
        )
        
        if response.status_code == 200:
            return {"success": True, "message": f"Updated episode {episode} on AniList"}
        else:
            return {"error": f"AniList API error: {response.status_code}"}
    
    def _get_current_date(self):
        """Get current date in YYYY-MM-DD format"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")
    
    def search_anime_ids(self, anime_title: str):
        """Search for anime IDs on both MAL and AniList"""
        results = {}
        
        # Search MAL
        try:
            mal_id = self._search_mal_id(anime_title)
            if mal_id:
                results['mal_id'] = mal_id
        except Exception as e:
            print(f"MAL search error: {e}")
        
        # Search AniList
        try:
            anilist_id = self._search_anilist_id(anime_title)
            if anilist_id:
                results['anilist_id'] = anilist_id
        except Exception as e:
            print(f"AniList search error: {e}")
        
        return results
    
    def _search_mal_id(self, anime_title: str):
        """Search for anime ID on MAL"""
        if not self.mal_token:
            return None
        
        url = f"{self.mal_api_base}/anime"
        headers = {'Authorization': f'Bearer {self.mal_token}'}
        params = {'q': anime_title, 'limit': 1}
        
        response = self.session.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                return data['data'][0]['node']['id']
        return None
    
    def _search_anilist_id(self, anime_title: str):
        """Search for anime ID on AniList"""
        query = """
        query ($search: String) {
            Media (search: $search, type: ANIME) {
                id
                idMal
            }
        }
        """
        
        variables = {'search': anime_title}
        
        response = self.session.post(
            self.anilist_api,
            json={'query': query, 'variables': variables}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data', {}).get('Media'):
                return data['data']['Media']['id']
        return None

class AniCliGUI:
    def __init__(self):
        # Set the appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create the main window
        self.root = ctk.CTk()
        self.root.title("Ani-CLI GUI with MAL-Sync")
        self.root.geometry("1200x800")
        self.root.minsize(900, 700)
        
        # Git Bash path
        self.git_bash_path = r"C:\Program Files\Git\bin\bash.exe"
        
        # Variables
        self.current_process = None
        self.anime_search_api = AnimeSearchAPI()
        self.mal_sync = MALSyncIntegration()
        self.selected_anime = None
        self.current_episode = 1
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="Ani-CLI GUI with MAL-Sync", font=("Arial", 24, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Create tabview for main content and MAL-Sync
        self.tabview = ctk.CTkTabview(main_frame, width=1000, height=600)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Main anime tab
        self.tabview.add("Anime Search & Play")
        anime_tab = self.tabview.tab("Anime Search & Play")
        
        # MAL-Sync tab
        self.tabview.add("MAL-Sync")
        malsync_tab = self.tabview.tab("MAL-Sync")
        
        # Setup anime search interface
        self.setup_anime_interface(anime_tab)
        
        # Setup MAL-Sync interface
        self.setup_malsync_interface(malsync_tab)
        
        # Status bar (outside tabs)
        self.status_label = ctk.CTkLabel(main_frame, text="Ready", font=("Arial", 12))
        self.status_label.pack(fill="x", padx=10, pady=(5, 5))
    
    def setup_anime_interface(self, parent):
        """Setup the main anime search and play interface"""
        # Single anime input section
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", padx=10, pady=(10, 10))
        
        input_label = ctk.CTkLabel(input_frame, text="Search or Enter Anime Name:", font=("Arial", 14))
        input_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Search input frame with buttons
        search_input_frame = ctk.CTkFrame(input_frame)
        search_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.anime_entry = ctk.CTkEntry(search_input_frame, placeholder_text="Enter anime name...")
        self.anime_entry.pack(side="left", fill="x", expand=True, padx=(5, 10), pady=5)
        self.anime_entry.bind("<Return>", lambda event: self.search_anime())
        
        search_button = ctk.CTkButton(search_input_frame, text="Search", command=self.search_anime, width=80)
        search_button.pack(side="right", padx=(0, 5), pady=5)
        
        # Search results frame
        results_frame = ctk.CTkFrame(parent)
        results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        results_label = ctk.CTkLabel(results_frame, text="Search Results:", font=("Arial", 14))
        results_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Create scrollable frame for results
        self.results_scrollable = ctk.CTkScrollableFrame(results_frame, height=200)
        self.results_scrollable.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Options section
        self.setup_options_section(parent)
        
        # Buttons section
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        play_selected_button = ctk.CTkButton(button_frame, text="Play Selected", command=self.play_selected_anime)
        play_selected_button.pack(side="left", padx=5, pady=10)
        
        play_direct_button = ctk.CTkButton(button_frame, text="Play Direct", command=self.play_anime)
        play_direct_button.pack(side="left", padx=5, pady=10)
        
        test_button = ctk.CTkButton(button_frame, text="Test ani-cli", command=self.test_ani_cli)
        test_button.pack(side="left", padx=5, pady=10)
        
        stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_process, fg_color="red")
        stop_button.pack(side="right", padx=5, pady=10)
    
    def setup_malsync_interface(self, parent):
        """Setup the MAL-Sync interface similar to browser extension"""
        # MAL-Sync title
        malsync_title = ctk.CTkLabel(parent, text="MAL-Sync Integration", font=("Arial", 20, "bold"))
        malsync_title.pack(pady=(10, 20))
        
        # Authentication section
        auth_frame = ctk.CTkFrame(parent)
        auth_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        auth_label = ctk.CTkLabel(auth_frame, text="Authentication:", font=("Arial", 16, "bold"))
        auth_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        auth_buttons_frame = ctk.CTkFrame(auth_frame)
        auth_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        mal_auth_btn = ctk.CTkButton(auth_buttons_frame, text="Connect MyAnimeList", command=self.authenticate_mal)
        mal_auth_btn.pack(side="left", padx=5, pady=5)
        
        anilist_auth_btn = ctk.CTkButton(auth_buttons_frame, text="Connect AniList", command=self.authenticate_anilist)
        anilist_auth_btn.pack(side="left", padx=5, pady=5)
        
        # Current anime status section
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        status_label = ctk.CTkLabel(status_frame, text="Current Anime Status:", font=("Arial", 16, "bold"))
        status_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Anime info display
        self.anime_info_frame = ctk.CTkFrame(status_frame)
        self.anime_info_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.current_anime_label = ctk.CTkLabel(self.anime_info_frame, text="No anime selected", font=("Arial", 14))
        self.current_anime_label.pack(anchor="w", padx=10, pady=5)
        
        # Episode controls
        episode_frame = ctk.CTkFrame(status_frame)
        episode_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        episode_label = ctk.CTkLabel(episode_frame, text="Episode:", font=("Arial", 12))
        episode_label.pack(side="left", padx=5, pady=5)
        
        self.episode_var = ctk.StringVar(value="1")
        self.episode_entry = ctk.CTkEntry(episode_frame, textvariable=self.episode_var, width=80)
        self.episode_entry.pack(side="left", padx=5, pady=5)
        
        # Status dropdown
        status_label = ctk.CTkLabel(episode_frame, text="Status:", font=("Arial", 12))
        status_label.pack(side="left", padx=(20, 5), pady=5)
        
        self.status_var = ctk.StringVar(value="watching")
        self.status_dropdown = ctk.CTkOptionMenu(
            episode_frame, 
            variable=self.status_var,
            values=["watching", "completed", "on_hold", "dropped", "plan_to_watch"]
        )
        self.status_dropdown.pack(side="left", padx=5, pady=5)
        
        # Platform selection
        platform_label = ctk.CTkLabel(episode_frame, text="Platform:", font=("Arial", 12))
        platform_label.pack(side="left", padx=(20, 5), pady=5)
        
        self.platform_var = ctk.StringVar(value="mal")
        self.platform_dropdown = ctk.CTkOptionMenu(
            episode_frame,
            variable=self.platform_var,
            values=["mal", "anilist"]
        )
        self.platform_dropdown.pack(side="left", padx=5, pady=5)
        
        # Update buttons
        update_frame = ctk.CTkFrame(status_frame)
        update_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        update_episode_btn = ctk.CTkButton(update_frame, text="Update Episode", command=self.update_episode_status)
        update_episode_btn.pack(side="left", padx=5, pady=5)
        
        mark_completed_btn = ctk.CTkButton(update_frame, text="Mark as Completed", command=self.mark_as_completed)
        mark_completed_btn.pack(side="left", padx=5, pady=5)
        
        auto_update_btn = ctk.CTkButton(update_frame, text="Auto-Update on Play", command=self.toggle_auto_update)
        auto_update_btn.pack(side="left", padx=5, pady=5)
        
        # Quick actions like browser extension
        quick_frame = ctk.CTkFrame(parent)
        quick_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        quick_label = ctk.CTkLabel(quick_frame, text="Quick Actions:", font=("Arial", 16, "bold"))
        quick_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        quick_buttons_frame = ctk.CTkFrame(quick_frame)
        quick_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        plus_one_btn = ctk.CTkButton(quick_buttons_frame, text="+1 Episode", command=lambda: self.quick_update_episode(1))
        plus_one_btn.pack(side="left", padx=5, pady=5)
        
        minus_one_btn = ctk.CTkButton(quick_buttons_frame, text="-1 Episode", command=lambda: self.quick_update_episode(-1))
        minus_one_btn.pack(side="left", padx=5, pady=5)
        
        set_watching_btn = ctk.CTkButton(quick_buttons_frame, text="Set Watching", command=lambda: self.quick_set_status("watching"))
        set_watching_btn.pack(side="left", padx=5, pady=5)
        
        # Log/Output area
        log_frame = ctk.CTkFrame(parent)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        log_label = ctk.CTkLabel(log_frame, text="MAL-Sync Log:", font=("Arial", 14, "bold"))
        log_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.malsync_log = ctk.CTkTextbox(log_frame, height=150)
        self.malsync_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def setup_options_section(self, parent):
        """Setup the options section (common for both tabs)"""
        options_label = ctk.CTkLabel(parent, text="Options:", font=("Arial", 14))
        options_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Episode selection
        episode_frame = ctk.CTkFrame(parent)
        episode_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        episode_label = ctk.CTkLabel(episode_frame, text="Episode(s):")
        episode_label.pack(side="left", padx=5)
        
        self.episode_entry = ctk.CTkEntry(episode_frame, placeholder_text="e.g., 1 or 1-5")
        self.episode_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Checkboxes for options
        checkbox_frame = ctk.CTkFrame(parent)
        checkbox_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.download_var = ctk.BooleanVar()
        download_check = ctk.CTkCheckBox(checkbox_frame, text="Download", variable=self.download_var)
        download_check.pack(side="left", padx=5)
        
        self.vlc_var = ctk.BooleanVar()
        vlc_check = ctk.CTkCheckBox(checkbox_frame, text="Use VLC", variable=self.vlc_var)
        vlc_check.pack(side="left", padx=5)
        
        self.continue_var = ctk.BooleanVar()
        continue_check = ctk.CTkCheckBox(checkbox_frame, text="Continue from History", variable=self.continue_var)
        continue_check.pack(side="left", padx=5)
    
    def play_anime(self):
        """Play anime directly using ani-cli"""
        anime_name = self.anime_entry.get().strip()
        
        if not anime_name:
            messagebox.showwarning("Warning", "Please enter an anime name!")
            return
        
        # Build and run ani-cli command
        cmd = self.build_command(anime_name)
        
        self.update_status("Starting anime...")
        
        # Run command in a separate thread
        thread = threading.Thread(target=self.run_ani_cli_command, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def search_anime(self):
        """Search for anime in the database"""
        query = self.anime_entry.get().strip()
        
        if not query:
            messagebox.showwarning("Warning", "Please enter an anime name to search!")
            return
        
        self.update_status("Searching anime database...")
        self.clear_results()
        
        # Run search in a separate thread
        thread = threading.Thread(target=self._search_anime_thread, args=(query,))
        thread.daemon = True
        thread.start()
    
    def _search_anime_thread(self, query):
        """Thread function to search anime"""
        try:
            results = self.anime_search_api.search_anime_jikan(query, limit=12)
            
            # Update UI in main thread
            self.root.after(0, self._update_search_results, results)
            
        except Exception as e:
            self.root.after(0, self.update_status, "Search failed")
    
    def _update_search_results(self, results):
        """Update the search results display"""
        self.clear_results()
        
        if not results:
            self.update_status("No results found")
            no_results_label = ctk.CTkLabel(self.results_scrollable, text="No anime found for your search.")
            no_results_label.pack(pady=20)
            return
        
        self.update_status(f"Found {len(results)} results")
        
        for anime in results:
            self._create_anime_result_widget(anime)
    
    def _create_anime_result_widget(self, anime):
        """Create a widget for displaying anime search result with image"""
        # Main container for this result
        result_frame = ctk.CTkFrame(self.results_scrollable)
        result_frame.pack(fill="x", padx=5, pady=5)
        
        # Make it clickable
        def select_anime(event=None):
            self.selected_anime = anime
            self._highlight_selected_result(result_frame)
            self.update_status(f"Selected: {anime['title']}")
            # Update MAL-Sync info when anime is selected
            self.update_selected_anime_info()
        
        result_frame.bind("<Button-1>", select_anime)
        
        # Main content frame
        content_frame = ctk.CTkFrame(result_frame)
        content_frame.pack(fill="x", padx=10, pady=10)
        content_frame.bind("<Button-1>", select_anime)
        
        # Image and info container
        info_container = ctk.CTkFrame(content_frame)
        info_container.pack(fill="x", padx=5, pady=5)
        info_container.bind("<Button-1>", select_anime)
        
        # Load and display image in a separate thread
        def load_image():
            try:
                image = self.anime_search_api.load_image_from_url(anime.get('image_url', ''), (80, 120))
                if image:
                    self.root.after(0, lambda: self._display_image(info_container, image, select_anime))
            except:
                pass  # Ignore image loading errors
        
        if anime.get('image_url'):
            img_thread = threading.Thread(target=load_image)
            img_thread.daemon = True
            img_thread.start()
        
        # Text info frame (right side)
        text_frame = ctk.CTkFrame(info_container)
        text_frame.pack(side="left", fill="both", expand=True, padx=(90, 5), pady=5)
        text_frame.bind("<Button-1>", select_anime)
        
        # Title
        title = anime.get('title', 'Unknown Title')
        if anime.get('title_english') and anime['title_english'] != title:
            title += f" ({anime['title_english']})"
        
        title_label = ctk.CTkLabel(text_frame, text=title, font=("Arial", 14, "bold"), wraplength=400)
        title_label.pack(anchor="w", padx=5, pady=(5, 0))
        title_label.bind("<Button-1>", select_anime)
        
        # Details
        details = []
        if anime.get('year'):
            details.append(f"Year: {anime['year']}")
        if anime.get('episodes'):
            details.append(f"Episodes: {anime['episodes']}")
        if anime.get('score'):
            details.append(f"Score: {anime['score']}/10")
        if anime.get('type'):
            details.append(f"Type: {anime['type']}")
        
        if details:
            details_text = " | ".join(details)
            details_label = ctk.CTkLabel(text_frame, text=details_text, font=("Arial", 11))
            details_label.pack(anchor="w", padx=5, pady=(2, 0))
            details_label.bind("<Button-1>", select_anime)
        
        # Genres
        if anime.get('genres'):
            genres_text = f"Genres: {', '.join(anime['genres'])}"
            genres_label = ctk.CTkLabel(text_frame, text=genres_text, font=("Arial", 10))
            genres_label.pack(anchor="w", padx=5, pady=(2, 0))
            genres_label.bind("<Button-1>", select_anime)
        
        # Synopsis (if available)
        if anime.get('synopsis'):
            synopsis_label = ctk.CTkLabel(text_frame, text=anime['synopsis'], font=("Arial", 9), 
                                        wraplength=400, justify="left")
            synopsis_label.pack(anchor="w", padx=5, pady=(2, 5))
            synopsis_label.bind("<Button-1>", select_anime)
    
    def _display_image(self, parent, image, click_callback):
        """Display the loaded image in the parent frame"""
        try:
            image_label = ctk.CTkLabel(parent, image=image, text="")
            image_label.place(x=5, y=5)
            image_label.bind("<Button-1>", click_callback)
        except:
            pass  # Ignore display errors
    
    def _highlight_selected_result(self, selected_frame):
        """Highlight the selected anime result"""
        # Simple highlighting by changing corner radius
        for widget in self.results_scrollable.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.configure(corner_radius=6)
        
        # Highlight selected frame
        selected_frame.configure(corner_radius=12)
    
    def play_selected_anime(self):
        """Play the selected anime using ani-cli"""
        if not self.selected_anime:
            messagebox.showwarning("Warning", "Please search and select an anime first!")
            return
        
        # Use the selected anime title for ani-cli search
        anime_title = self.selected_anime['title']
        
        # Build and run ani-cli command
        cmd = self.build_command(anime_title)
        
        self.update_status("Starting selected anime...")
        
        # Run command in a separate thread
        thread = threading.Thread(target=self.run_ani_cli_command, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def clear_results(self):
        """Clear the search results display"""
        for widget in self.results_scrollable.winfo_children():
            widget.destroy()
        self.selected_anime = None
    
    def build_command(self, anime_name=None):
        """Build the ani-cli command based on user inputs"""
        cmd = ["ani-cli"]
        
        # Add auto-select first result to avoid interactive menu
        cmd.extend(["-S", "1"])
        
        # Use best quality available automatically
        cmd.extend(["-q", "best"])
        
        # Add episode option
        if self.episode_entry.get().strip():
            cmd.extend(["-e", self.episode_entry.get().strip()])
        
        # Add checkbox options
        if self.download_var.get():
            cmd.append("-d")
        
        if self.vlc_var.get():
            cmd.append("-v")
        
        if self.continue_var.get():
            cmd.append("-c")
        
        # Add anime name if provided
        if anime_name:
            cmd.append(anime_name)
        
        return cmd
        
    def run_ani_cli_command(self, cmd):
        """Run ani-cli command in Git Bash"""
        try:
            # Check if Git Bash exists
            if not os.path.exists(self.git_bash_path):
                self.update_status("Git Bash not found")
                return
            
            # Convert command list to string for bash
            cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
            
            # Run the command through Git Bash
            process = subprocess.Popen(
                [self.git_bash_path, "-c", cmd_str],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            self.current_process = process
            
            # Read output in real-time
            if process.stdout:
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
            
            # Get any remaining output
            stdout, stderr = process.communicate()
                
            return_code = process.returncode
            
            if return_code == 0:
                self.update_status("Completed")
            else:
                self.update_status("Failed")
                
        except FileNotFoundError:
            self.update_status("Git Bash not found")
        except Exception as e:
            self.update_status("Error occurred")
        finally:
            self.current_process = None
    
    def test_ani_cli(self):
        """Test if ani-cli is working"""
        self.update_status("Testing ani-cli...")
        
        # Test version command
        cmd = ["ani-cli", "--version"]
        
        # Run test in a separate thread
        thread = threading.Thread(target=self.run_ani_cli_command, args=(cmd,))
        thread.daemon = True
        thread.start()
            
    def stop_process(self):
        """Stop the current ani-cli process"""
        if self.current_process:
            try:
                self.current_process.terminate()
                self.update_status("Process stopped")
            except Exception as e:
                self.update_status("Error stopping process")
        else:
            pass  # No process running to stop
            
    def update_status(self, message):
        """Update the status bar"""
        self.status_label.configure(text=message)
        
    def run(self):
        """Start the GUI application"""
        # Check if Git Bash is available
        if not os.path.exists(self.git_bash_path):
            messagebox.showerror("Error", f"Git Bash not found at: {self.git_bash_path}")
            return
            
        # Check if ani-cli is accessible
        try:
            test_process = subprocess.run(
                [self.git_bash_path, "-c", "ani-cli --version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if test_process.returncode != 0:
                messagebox.showwarning("Warning", "ani-cli may not be properly installed or accessible.")
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not verify ani-cli installation: {str(e)}")
            
        self.root.mainloop()
    
    # MAL-Sync Integration Methods
    def authenticate_mal(self):
        """Authenticate with MyAnimeList"""
        result = self.mal_sync.authenticate_mal()
        self.log_malsync(f"MAL Auth: {result}")
        self.update_status("MAL authentication started - check browser")
    
    def authenticate_anilist(self):
        """Authenticate with AniList"""
        result = self.mal_sync.authenticate_anilist()
        self.log_malsync(f"AniList Auth: {result}")
        self.update_status("AniList authentication started - check browser")
    
    def update_episode_status(self):
        """Update episode status on selected platform"""
        if not self.selected_anime:
            messagebox.showwarning("Warning", "Please select an anime first!")
            return
        
        try:
            episode = int(self.episode_var.get())
            status = self.status_var.get()
            platform = self.platform_var.get()
            
            # Get anime ID for the platform
            anime_title = self.selected_anime['title']
            ids = self.mal_sync.search_anime_ids(anime_title)
            
            if platform == "mal" and 'mal_id' in ids:
                result = self.mal_sync.update_anime_status(ids['mal_id'], episode, status, "mal")
            elif platform == "anilist" and 'anilist_id' in ids:
                result = self.mal_sync.update_anime_status(ids['anilist_id'], episode, status, "anilist")
            else:
                result = {"error": f"Could not find anime ID for {platform}"}
            
            if result.get('success'):
                self.log_malsync(f"✅ {result['message']}")
                self.update_status(f"Updated {anime_title} episode {episode}")
            else:
                self.log_malsync(f"❌ Error: {result.get('error', 'Unknown error')}")
                self.update_status("Update failed")
                
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid episode number!")
        except Exception as e:
            self.log_malsync(f"❌ Error: {str(e)}")
            self.update_status("Update failed")
    
    def mark_as_completed(self):
        """Mark anime as completed"""
        if not self.selected_anime:
            messagebox.showwarning("Warning", "Please select an anime first!")
            return
        
        # Set status to completed and episode to total episodes if available
        self.status_var.set("completed")
        if self.selected_anime.get('episodes'):
            self.episode_var.set(str(self.selected_anime['episodes']))
        
        self.update_episode_status()
    
    def quick_update_episode(self, change):
        """Quick update episode by +/- 1"""
        try:
            current = int(self.episode_var.get())
            new_episode = max(1, current + change)
            self.episode_var.set(str(new_episode))
            
            if self.selected_anime:
                self.update_episode_status()
            
        except ValueError:
            self.episode_var.set("1")
    
    def quick_set_status(self, status):
        """Quick set status"""
        self.status_var.set(status)
        if self.selected_anime:
            self.update_episode_status()
    
    def toggle_auto_update(self):
        """Toggle auto-update on play"""
        # This would be implemented to automatically update MAL when playing episodes
        self.log_malsync("Auto-update feature - Coming soon!")
        self.update_status("Auto-update feature in development")
    
    def log_malsync(self, message):
        """Log message to MAL-Sync log area"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}\n"
            
            self.malsync_log.insert("end", formatted_message)
            self.malsync_log.see("end")
        except:
            print(f"MAL-Sync: {message}")
    
    def update_selected_anime_info(self):
        """Update the current anime info in MAL-Sync tab"""
        if self.selected_anime:
            anime_info = f"Selected: {self.selected_anime['title']}"
            if self.selected_anime.get('episodes'):
                anime_info += f" ({self.selected_anime['episodes']} episodes)"
            if self.selected_anime.get('year'):
                anime_info += f" - {self.selected_anime['year']}"
            
            self.current_anime_label.configure(text=anime_info)
            
            # Auto-populate episode 1 if not set
            if self.episode_var.get() == "1" and not hasattr(self, '_episode_set'):
                self.episode_var.set("1")
                self._episode_set = True

def main():
    app = AniCliGUI()
    app.run()

if __name__ == "__main__":
    main()
