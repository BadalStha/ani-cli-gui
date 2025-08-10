import customtkinter as ctk
import subprocess
import os
import threading
import requests
from PIL import Image
from tkinter import messagebox
from typing import List, Dict

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AnimeSearchAPI:
    def __init__(self):
        self.base_url = "https://api.jikan.moe/v4"
        self.anilist_url = "https://graphql.anilist.co"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AniCLI-GUI/1.0'
        })

    def get_anilist_episode_count(self, mal_id: int) -> int:
        """Get episode count from AniList API using MAL ID"""
        try:
            # GraphQL query to get anime by MAL ID
            query = """
            query ($malId: Int) {
                Media (idMal: $malId, type: ANIME) {
                    id
                    episodes
                    status
                    nextAiringEpisode {
                        episode
                        airingAt
                    }
                    title {
                        romaji
                        english
                    }
                    airingSchedule(page: 1, perPage: 50, notYetAired: false) {
                        edges {
                            node {
                                episode
                                airingAt
                            }
                        }
                    }
                }
            }
            """
            
            variables = {'malId': mal_id}
            
            response = self.session.post(
                self.anilist_url,
                json={'query': query, 'variables': variables},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            media = data.get('data', {}).get('Media')
            
            if not media:
                return 0
            
            episodes = media.get('episodes')
            next_airing = media.get('nextAiringEpisode')
            status = media.get('status')
            title = media.get('title', {}).get('romaji', 'Unknown')
            airing_schedule = media.get('airingSchedule', {}).get('edges', [])
            
            print(f"AniList data - Title: {title}, Status: {status}, Total Episodes: {episodes}")
            
            # For currently airing anime, determine actual available episodes
            if status in ['RELEASING', 'AIRING']:
                # Method 1: Use nextAiringEpisode (most reliable)
                if next_airing and next_airing.get('episode'):
                    current_episode = next_airing.get('episode') - 1
                    print(f"Next airing episode: {next_airing.get('episode')}, so current available: {current_episode}")
                    return max(0, current_episode)
                
                # Method 2: Count aired episodes from schedule
                elif airing_schedule:
                    import time
                    current_time = int(time.time())
                    aired_episodes = 0
                    
                    for edge in airing_schedule:
                        node = edge.get('node', {})
                        airing_at = node.get('airingAt', 0)
                        if airing_at <= current_time:  # Episode has already aired
                            aired_episodes = max(aired_episodes, node.get('episode', 0))
                    
                    if aired_episodes > 0:
                        print(f"From airing schedule: {aired_episodes} episodes have aired")
                        return aired_episodes
                
                # Method 3: Conservative estimate for new airing anime
                print("Using conservative estimate for new airing anime")
                return 6  # Conservative default
            
            # For completed anime, return total episodes
            elif episodes:
                print(f"Completed anime with {episodes} total episodes")
                return episodes
            else:
                return 0
                
        except Exception as e:
            print(f"Error fetching from AniList: {e}")
            return 0

    def get_kitsu_episode_count(self, title: str) -> int:
        """Get episode count from Kitsu API as backup"""
        try:
            # Search for anime on Kitsu
            url = "https://kitsu.io/api/edge/anime"
            params = {
                'filter[text]': title,
                'page[limit]': 1
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            anime_list = data.get('data', [])
            
            if anime_list:
                anime = anime_list[0]
                attributes = anime.get('attributes', {})
                episode_count = attributes.get('episodeCount')
                status = attributes.get('status')
                
                print(f"Kitsu data - Episodes: {episode_count}, Status: {status}")
                return episode_count if episode_count else 0
            
            return 0
            
        except Exception as e:
            print(f"Error fetching from Kitsu: {e}")
            return 0

    def search_anime_jikan(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for anime using Jikan API (MyAnimeList)"""
        try:
            url = f"{self.base_url}/anime"
            params = {
                'q': query,
                'limit': limit,
                'type': 'tv'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            anime_list = []
            
            for anime in data.get('data', []):
                anime_info = {
                    'title': anime.get('title', 'Unknown'),
                    'episodes': anime.get('episodes', 0),
                    'score': anime.get('score', 0),
                    'year': anime.get('year'),
                    'image_url': anime.get('images', {}).get('jpg', {}).get('image_url'),
                    'mal_id': anime.get('mal_id')
                }
                anime_list.append(anime_info)
            
            return anime_list
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return []
        except Exception as e:
            print(f"Error parsing API response: {e}")
            return []

    def get_episodes_from_malsync(self, mal_id: int) -> List[Dict]:
        """Get episode details from MAL-Sync API"""
        try:
            # MAL-Sync API endpoint
            url = f"https://api.malsync.moe/mal/anime/{mal_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            episodes = []
            
            # Extract episodes from the response
            if 'Sites' in data:
                # Look for available episodes from streaming sites
                available_episodes = set()
                
                for site, site_data in data['Sites'].items():
                    if isinstance(site_data, dict) and 'episodes' in site_data:
                        # Only count episodes that have actual URLs (meaning they're available)
                        for ep_num, ep_data in site_data['episodes'].items():
                            if ep_data.get('url'):  # Only include episodes with actual streaming URLs
                                available_episodes.add(int(ep_num))
                
                # Create episode list only for available episodes
                for ep_num in sorted(available_episodes):
                    episode_info = {
                        'number': ep_num,
                        'title': f'Episode {ep_num}',
                        'url': '',
                        'site': 'malsync'
                    }
                    episodes.append(episode_info)
            
            # Sort episodes by number
            episodes.sort(key=lambda x: x['number'])
            return episodes
            
        except Exception as e:
            print(f"Error fetching episodes from MAL-Sync: {e}")
            return []

    def get_actual_episode_count(self, mal_id: int) -> int:
        """Get the actual number of released episodes using multiple APIs for accuracy"""
        try:
            # Use Jikan API to get basic episode information
            url = f"https://api.jikan.moe/v4/anime/{mal_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            anime_data = data.get('data', {})
            
            status = anime_data.get('status', '')
            aired_episodes = anime_data.get('episodes')
            title = anime_data.get('title', 'Unknown')
            
            print(f"Jikan data - Title: {title}, Episodes: {aired_episodes}, Status: {status}")
            
            # Special handling for long-running series
            if mal_id == 21:  # One Piece
                return 1100  # Current approximate count
            elif mal_id == 1535:  # Death Note
                return 37
            elif mal_id == 20:  # Naruto
                return 720  # Including Shippuden
            
            # For currently airing anime, use multiple sources for accuracy
            if status == 'Currently Airing':
                # Try AniList API first (often more up-to-date for current episodes)
                anilist_count = self.get_anilist_episode_count(mal_id)
                
                # Try Jikan episodes endpoint for actual released episodes
                jikan_episode_count = self._get_current_episode_count_from_jikan(mal_id)
                
                # Try Kitsu as backup
                kitsu_count = self.get_kitsu_episode_count(title) if title != 'Unknown' else 0
                
                print(f"Episode counts - AniList: {anilist_count}, Jikan: {jikan_episode_count}, Kitsu: {kitsu_count}, Planned: {aired_episodes}")
                
                # For currently airing anime, prioritize actual available episodes over planned total
                # AniList is most reliable for current episode count of airing anime
                if anilist_count > 0:
                    print(f"Using AniList count: {anilist_count} (most reliable for airing anime)")
                    return anilist_count
                
                # If AniList fails, use other sources but prefer smaller counts (actual available)
                episode_counts = [count for count in [jikan_episode_count, kitsu_count] if count > 0]
                
                if episode_counts:
                    # For airing anime, use the minimum reliable count (actual available episodes)
                    # Don't use max() as it might give total planned instead of current available
                    min_count = min(episode_counts)
                    print(f"Using minimum count from backup sources: {min_count}")
                    return min_count
                else:
                    # Last resort: use a conservative estimate
                    print("No reliable episode count found, using conservative estimate")
                    return 6  # Conservative default for new airing anime
            else:
                # For completed anime, return the total episodes
                return aired_episodes if aired_episodes else 0
                
        except Exception as e:
            print(f"Error getting episode count: {e}")
            return 0

    def _get_current_episode_count_from_jikan(self, mal_id: int) -> int:
        """Get current episode count for airing anime"""
        try:
            # For One Piece specifically, we know it has 1000+ episodes
            # Use a different approach since the episodes endpoint is paginated
            if mal_id == 21:  # One Piece MAL ID
                # Get the main anime data and check broadcast info
                url = f"https://api.jikan.moe/v4/anime/{mal_id}"
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                anime_data = data.get('data', {})
                
                # One Piece is ongoing, return a reasonable current count
                # This should be updated based on current releases
                return 1100  # Current approximate episode count (as of 2024)
            
            # For other anime, try to get all episodes with pagination
            all_episodes = []
            page = 1
            
            while page <= 10:  # Limit to 10 pages to prevent infinite loops
                url = f"https://api.jikan.moe/v4/anime/{mal_id}/episodes?page={page}"
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                episodes = data.get('data', [])
                
                if not episodes:  # No more episodes
                    break
                    
                all_episodes.extend(episodes)
                
                # Check if there are more pages
                pagination = data.get('pagination', {})
                if not pagination.get('has_next_page', False):
                    break
                    
                page += 1
            
            return len(all_episodes) if all_episodes else 0
            
        except Exception as e:
            print(f"Error getting current episode count: {e}")
            return 0

    def load_image_from_url(self, url: str, size: tuple = (80, 120)):
        """Load image from URL and return PIL Image"""
        try:
            if not url:
                return None
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            from io import BytesIO
            image = Image.open(BytesIO(response.content))
            image = image.resize(size, Image.Resampling.LANCZOS)
            return image
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

class EpisodeWindow:
    def __init__(self, parent, anime_data, api):
        self.parent = parent
        self.anime_data = anime_data
        self.api = api
        self.selected_episode = None
        
        # Create new window
        self.window = ctk.CTkToplevel(parent.root)
        self.window.title(f"Episodes - {anime_data.get('title', 'Unknown')}")
        self.window.geometry("600x500")
        self.window.grab_set()  # Make window modal
        
        self.setup_ui()
        self.load_episodes()
    
    def setup_ui(self):
        """Setup the episode selection UI"""
        # Main frame
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="Episodes", font=("Arial", 20, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Episode range selector
        self.range_frame = ctk.CTkFrame(main_frame)
        self.range_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Range controls (001-006 style from your image)
        self.range_label = ctk.CTkLabel(self.range_frame, text="Loading episodes...", font=("Arial", 14))
        self.range_label.pack(pady=10)
        
        # Episodes scrollable frame
        self.episodes_frame = ctk.CTkScrollableFrame(main_frame, height=250)
        self.episodes_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        play_button = ctk.CTkButton(buttons_frame, text="Play Episode", command=self.play_selected_episode)
        play_button.pack(side="left", padx=5, pady=10)
        
        close_button = ctk.CTkButton(buttons_frame, text="Close", command=self.window.destroy)
        close_button.pack(side="right", padx=5, pady=10)
    
    def load_episodes(self):
        """Load episodes from MAL-Sync API"""
        mal_id = self.anime_data.get('mal_id')
        if not mal_id:
            # Fallback: create basic episode list if no MAL ID
            total_episodes = self.anime_data.get('episodes', 12)
            self.create_basic_episode_list(total_episodes)
            return
        
        # Load episodes in background thread
        threading.Thread(target=self._load_episodes_thread, args=(mal_id,), daemon=True).start()
    
    def _load_episodes_thread(self, mal_id):
        """Load episodes in separate thread"""
        print(f"\n=== Loading episodes for MAL ID: {mal_id} ===")
        
        # Get basic anime info first
        try:
            url = f"https://api.jikan.moe/v4/anime/{mal_id}"
            response = self.api.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            anime_data = data.get('data', {})
            title = anime_data.get('title', 'Unknown')
            status = anime_data.get('status', 'Unknown')
            total_planned = anime_data.get('episodes')
            
            print(f"Anime: {title}")
            print(f"Status: {status}")
            print(f"Planned Episodes: {total_planned}")
        except Exception as e:
            print(f"Error getting anime info: {e}")
            title = "Unknown"
            status = "Unknown"
        
        # Get actual episode count using our improved multi-API method
        actual_episode_count = self.api.get_actual_episode_count(mal_id)
        print(f"=== Final episode count determined: {actual_episode_count} ===\n")
        
        # Try to get episode details from MAL-Sync for titles (optional)
        episodes_from_malsync = self.api.get_episodes_from_malsync(mal_id)
        print(f"Episodes from MAL-Sync: {len(episodes_from_malsync) if episodes_from_malsync else 0}")
        
        # Use the episode count to create pagination, not a full episode list
        if actual_episode_count > 0:
            self.window.after(0, lambda: self.create_basic_episode_list(actual_episode_count))
        else:
            # Fallback to default
            print("Using fallback episode count")
            self.window.after(0, lambda: self.create_basic_episode_list(12))

    def create_basic_episode_list(self, total_episodes):
        """Create basic episode list when MAL-Sync data is not available"""
        if total_episodes == 0 or total_episodes is None:
            total_episodes = 12  # Default
        
        # Always use pagination for better performance
        self.total_episodes = total_episodes
        self.episodes_per_page = 25  # Smaller pages for better performance
        self.current_page = 1
        
        self.setup_pagination_controls()
        self.load_current_page()
    
    def setup_pagination_controls(self):
        """Setup pagination navigation controls"""
        # Clear existing controls
        for widget in self.range_frame.winfo_children():
            if widget != self.range_label:
                widget.destroy()
        
        # Create navigation frame
        nav_frame = ctk.CTkFrame(self.range_frame)
        nav_frame.pack(fill="x", padx=10, pady=5)
        
        # Page navigation
        page_frame = ctk.CTkFrame(nav_frame)
        page_frame.pack(side="left", padx=5)
        
        # Previous page button
        prev_btn = ctk.CTkButton(page_frame, text="◀", width=30, height=25,
                                command=self.prev_page)
        prev_btn.pack(side="left", padx=2)
        
        # Page info
        total_pages = (self.total_episodes - 1) // self.episodes_per_page + 1
        self.page_label = ctk.CTkLabel(page_frame, text=f"Page {self.current_page}/{total_pages}")
        self.page_label.pack(side="left", padx=10)
        
        # Next page button
        next_btn = ctk.CTkButton(page_frame, text="▶", width=30, height=25,
                                command=self.next_page)
        next_btn.pack(side="left", padx=2)
        
        # Jump to page
        jump_frame = ctk.CTkFrame(nav_frame)
        jump_frame.pack(side="left", padx=20)
        
        ctk.CTkLabel(jump_frame, text="Go to:").pack(side="left", padx=5)
        
        self.page_entry = ctk.CTkEntry(jump_frame, width=60, height=25)
        self.page_entry.pack(side="left", padx=5)
        self.page_entry.bind('<Return>', lambda e: self.jump_to_page())
        
        jump_btn = ctk.CTkButton(jump_frame, text="Go", width=40, height=25,
                                command=self.jump_to_page)
        jump_btn.pack(side="left", padx=2)
        
        # Episode range input
        range_frame = ctk.CTkFrame(nav_frame)
        range_frame.pack(side="right", padx=5)
        
        ctk.CTkLabel(range_frame, text="Episodes:").pack(side="left", padx=5)
        
        self.range_entry = ctk.CTkEntry(range_frame, width=80, height=25, 
                                       placeholder_text="1-25 or 500+")
        self.range_entry.pack(side="left", padx=5)
        self.range_entry.bind('<Return>', lambda e: self.load_custom_range())
        
        range_btn = ctk.CTkButton(range_frame, text="Load", width=50, height=25,
                                 command=self.load_custom_range)
        range_btn.pack(side="left", padx=2)
        
        # Add One Piece arc shortcuts if applicable
        if "one piece" in self.anime_data.get('title', '').lower():
            self.add_arc_shortcuts(nav_frame)
    
    def add_arc_shortcuts(self, parent):
        """Add One Piece arc shortcuts"""
        arc_frame = ctk.CTkFrame(parent)
        arc_frame.pack(fill="x", padx=5, pady=5)
        
        arcs = [
            ("East Blue", 1, 61),
            ("Alabasta", 62, 135),
            ("Skypeia", 136, 206),
            ("Water 7", 207, 325),
            ("Thriller Bark", 326, 384),
            ("Summit War", 385, 516),
            ("Fishman Island", 517, 574),
            ("Dressrosa", 575, 746),
            ("Wano", 878, 1085),
            ("Recent", 1086, self.total_episodes)
        ]
        
        ctk.CTkLabel(arc_frame, text="Quick Jump:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        for arc_name, start, end in arcs[:6]:  # Show first 6 arcs
            if start <= self.total_episodes:  # Only show arcs that exist
                btn = ctk.CTkButton(arc_frame, text=arc_name, width=80, height=25,
                                   command=lambda s=start, e=end: self.load_episode_range_by_numbers(s, e))
                btn.pack(side="left", padx=2)
    
    def load_current_page(self):
        """Load episodes for current page"""
        # Clear episodes
        for widget in self.episodes_frame.winfo_children():
            widget.destroy()
        
        # Calculate episode range for current page
        start_ep = (self.current_page - 1) * self.episodes_per_page + 1
        end_ep = min(self.current_page * self.episodes_per_page, self.total_episodes)
        
        # Update range label
        self.range_label.configure(text=f"{start_ep:03d}-{end_ep:03d}")
        
        # Load episodes for this page only
        for i in range(start_ep, end_ep + 1):
            episode_data = {
                'number': i,
                'title': f"Episode {i}",
                'url': '',
                'site': 'basic'
            }
            self.create_episode_widget(episode_data)
        
        # Update page label
        total_pages = (self.total_episodes - 1) // self.episodes_per_page + 1
        if hasattr(self, 'page_label'):
            self.page_label.configure(text=f"Page {self.current_page}/{total_pages}")
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_current_page()
    
    def next_page(self):
        """Go to next page"""
        total_pages = (self.total_episodes - 1) // self.episodes_per_page + 1
        if self.current_page < total_pages:
            self.current_page += 1
            self.load_current_page()
    
    def jump_to_page(self):
        """Jump to specific page"""
        try:
            page = int(self.page_entry.get())
            total_pages = (self.total_episodes - 1) // self.episodes_per_page + 1
            
            if 1 <= page <= total_pages:
                self.current_page = page
                self.load_current_page()
                self.page_entry.delete(0, 'end')
            else:
                messagebox.showwarning("Warning", f"Page must be between 1 and {total_pages}")
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid page number")
    
    def load_custom_range(self):
        """Load custom episode range"""
        try:
            range_str = self.range_entry.get().strip()
            if not range_str:
                return
            
            start_ep, end_ep = self.parse_episode_range(range_str)
            self.load_episode_range_by_numbers(start_ep, end_ep)
            
        except Exception as e:
            messagebox.showerror("Error", f"Invalid range format: {str(e)}")
    
    def parse_episode_range(self, range_str):
        """Parse episode range string"""
        if '+' in range_str:
            start_ep = int(range_str.replace('+', ''))
            end_ep = min(start_ep + self.episodes_per_page - 1, self.total_episodes)
        elif '-' in range_str:
            parts = range_str.split('-')
            start_ep = int(parts[0])
            end_ep = int(parts[1])
        else:
            start_ep = int(range_str)
            end_ep = min(start_ep + self.episodes_per_page - 1, self.total_episodes)
        
        # Validate range
        if start_ep < 1 or start_ep > self.total_episodes:
            raise ValueError(f"Start episode must be between 1 and {self.total_episodes}")
        if end_ep < start_ep or end_ep > self.total_episodes:
            end_ep = min(start_ep + self.episodes_per_page - 1, self.total_episodes)
        
        return start_ep, end_ep
    
    def load_episode_range_by_numbers(self, start_ep, end_ep):
        """Load specific episode range by numbers"""
        # Clear episodes
        for widget in self.episodes_frame.winfo_children():
            widget.destroy()
        
        # Update range label
        self.range_label.configure(text=f"{start_ep:03d}-{end_ep:03d}")
        
        # Load episodes in range
        for i in range(start_ep, end_ep + 1):
            episode_data = {
                'number': i,
                'title': f"Episode {i}",
                'url': '',
                'site': 'custom'
            }
            self.create_episode_widget(episode_data)
        
        # Update current page to match the range
        self.current_page = (start_ep - 1) // self.episodes_per_page + 1
        total_pages = (self.total_episodes - 1) // self.episodes_per_page + 1
        if hasattr(self, 'page_label'):
            self.page_label.configure(text=f"Custom Range (Page {self.current_page}/{total_pages})")
        
        # Clear range entry
        if hasattr(self, 'range_entry'):
            self.range_entry.delete(0, 'end')

    def create_episode_widget(self, episode_data):
        """Create a widget for an episode"""
        episode_frame = ctk.CTkFrame(self.episodes_frame)
        episode_frame.pack(fill="x", padx=10, pady=2)
        
        # Episode number and title
        episode_text = f"{episode_data['number']}. {episode_data['title']}"
        episode_label = ctk.CTkLabel(episode_frame, text=episode_text, font=("Arial", 12), anchor="w")
        episode_label.pack(fill="x", padx=15, pady=8)
        
        # Make clickable
        def on_episode_click():
            self.select_episode(episode_frame, episode_data)
        
        def on_episode_double_click():
            self.select_episode(episode_frame, episode_data)
            self.play_selected_episode()
        
        episode_frame.bind("<Button-1>", lambda e: on_episode_click())
        episode_label.bind("<Button-1>", lambda e: on_episode_click())
        episode_frame.bind("<Double-Button-1>", lambda e: on_episode_double_click())
        episode_label.bind("<Double-Button-1>", lambda e: on_episode_double_click())
        episode_frame.configure(cursor="hand2")
        episode_label.configure(cursor="hand2")
    
    def select_episode(self, episode_frame, episode_data):
        """Select an episode"""
        # Remove highlight from all frames
        for widget in self.episodes_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.configure(fg_color=("gray86", "gray17"))  # Default color
        
        # Highlight selected frame
        episode_frame.configure(fg_color=("orange", "darkorange"))
        
        # Store selected episode
        self.selected_episode = episode_data
    
    def play_selected_episode(self):
        """Play the selected episode"""
        if not self.selected_episode:
            messagebox.showwarning("Warning", "Please select an episode first")
            return
        
        # Close episode window and play episode in main window
        episode_number = self.selected_episode['number']
        self.parent.episode_entry.delete(0, 'end')
        self.parent.episode_entry.insert(0, str(episode_number))
        self.window.destroy()
        
        # Play the episode
        self.parent.play_selected_anime()

class AniCliGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Ani-CLI GUI")
        self.root.geometry("1000x700")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Initialize variables
        self.selected_anime = None
        self.current_process = None
        self.git_bash_path = r"C:\Program Files\Git\bin\bash.exe"
        
        # Initialize API
        self.api = AnimeSearchAPI()
        
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        # Main container
        self.main_frame = ctk.CTkScrollableFrame(self.root, corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Search section
        search_label = ctk.CTkLabel(self.main_frame, text="Search Anime:", font=("Arial", 14))
        search_label.pack(anchor="w", padx=20, pady=(0, 5))
        
        # Search input
        search_input_frame = ctk.CTkFrame(self.main_frame)
        search_input_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.search_entry = ctk.CTkEntry(search_input_frame, placeholder_text="Enter anime name...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.search_entry.bind('<Return>', lambda event: self.search_anime())
        
        search_button = ctk.CTkButton(search_input_frame, text="Search", command=self.search_anime)
        search_button.pack(side="right", padx=10, pady=10)
        
        # Search results
        self.results_scrollable = ctk.CTkScrollableFrame(self.main_frame, height=200)
        self.results_scrollable.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Options section
        self.setup_options_section(self.main_frame)

        # Button frame for actions
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        play_selected_button = ctk.CTkButton(button_frame, text="Play Selected", command=self.play_selected_anime)
        play_selected_button.pack(side="left", padx=5, pady=10)
        
        play_direct_button = ctk.CTkButton(button_frame, text="Play Direct", command=self.play_anime)
        play_direct_button.pack(side="left", padx=5, pady=10)
        
        stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_process, fg_color="red")
        stop_button.pack(side="right", padx=5, pady=10)
        
        # Status bar
        self.status_label = ctk.CTkLabel(self.main_frame, text="Starting selected anime", anchor="w")
        self.status_label.pack(fill="x", padx=20, pady=(10, 0))

    def setup_options_section(self, parent):
        """Set up the options section"""
        options_frame = ctk.CTkFrame(parent)
        options_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        options_label = ctk.CTkLabel(options_frame, text="Options:", font=("Arial", 16, "bold"))
        options_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Episode selection
        episode_frame = ctk.CTkFrame(options_frame)
        episode_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        episode_label = ctk.CTkLabel(episode_frame, text="Episode(s):")
        episode_label.pack(side="left", padx=(20, 10), pady=10)
        
        self.episode_entry = ctk.CTkEntry(episode_frame, placeholder_text="1", width=100)
        self.episode_entry.pack(side="left", padx=(0, 10), pady=10)
        
        # Download checkbox
        self.download_var = ctk.BooleanVar()
        download_checkbox = ctk.CTkCheckBox(episode_frame, text="Download", variable=self.download_var)
        download_checkbox.pack(side="left", padx=20, pady=10)

    def play_anime(self):
        """Play anime directly using the search term"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter an anime name")
            return
        
        episode = self.episode_entry.get().strip() or "1"
        
        if self.current_process:
            messagebox.showinfo("Info", "Another process is already running. Please stop it first.")
            return
        
        self.update_status(f"Starting {query}...")
        
        # Build and run command
        cmd = self.build_command(query)
        self.run_ani_cli_command(cmd)

    def search_anime(self):
        """Search for anime using the API"""
        query = self.search_entry.get().strip()
        if not query:
            return
        
        # Clear previous results
        for widget in self.results_scrollable.winfo_children():
            widget.destroy()
        self.selected_anime = None
        
        # Update status
        self.update_status("Searching...")
        
        # Run search in separate thread
        threading.Thread(target=self._search_anime_thread, args=(query,), daemon=True).start()

    def _search_anime_thread(self, query):
        """Search for anime in a separate thread"""
        results = self.api.search_anime_jikan(query)
        # Update UI from main thread
        self.root.after(0, self._update_search_results, results)

    def _update_search_results(self, results):
        """Update search results in the UI"""
        if not results:
            no_results_label = ctk.CTkLabel(self.results_scrollable, text="No anime found. Try a different search term.")
            no_results_label.pack(pady=20)
            self.update_status("No results found")
            return
        
        for anime in results:
            self._create_anime_result_widget(anime)
        
        self.update_status(f"Found {len(results)} results")

    def _create_anime_result_widget(self, anime):
        """Create a widget for an anime search result"""
        # Main frame for this result
        result_frame = ctk.CTkFrame(self.results_scrollable)
        result_frame.pack(fill="x", padx=10, pady=5)
        
        # Content frame
        content_frame = ctk.CTkFrame(result_frame)
        content_frame.pack(fill="x", padx=10, pady=10)
        
        # Image frame (left side)
        image_frame = ctk.CTkFrame(content_frame)
        image_frame.pack(side="left", padx=(0, 15), pady=10)
        
        # Load and display image
        def load_image():
            image = self.api.load_image_from_url(anime.get('image_url'))
            if image:
                self.root.after(0, lambda: self._display_image(image_frame, image, 
                                lambda: self._highlight_selected_result(result_frame, anime),
                                lambda: (self._highlight_selected_result(result_frame, anime), 
                                        self.open_episode_window(anime))))
        
        # Start image loading in thread
        threading.Thread(target=load_image, daemon=True).start()
        
        # Info frame (right side)
        info_frame = ctk.CTkFrame(content_frame)
        info_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        
        # Title
        title = anime.get('title', 'Unknown')
        title_label = ctk.CTkLabel(info_frame, text=title, font=("Arial", 14, "bold"), wraplength=400)
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Essential details only
        year = anime.get('year', 'Unknown')
        episodes = anime.get('episodes', 'Unknown')
        score = anime.get('score', 'N/A')
        
        details = f"Year: {year} | Episodes: {episodes} | Score: {score}/10"
        details_label = ctk.CTkLabel(info_frame, text=details, font=("Arial", 11))
        details_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Make the result clickable
        def on_click():
            self._highlight_selected_result(result_frame, anime)
        
        def on_double_click():
            self._highlight_selected_result(result_frame, anime)
            self.open_episode_window(anime)
        
        for widget in [result_frame, content_frame, info_frame]:
            widget.bind("<Button-1>", lambda e: on_click())
            widget.bind("<Double-Button-1>", lambda e: on_double_click())
            widget.configure(cursor="hand2")

    def _display_image(self, parent, image, click_callback, double_click_callback=None):
        """Display an image in the parent widget"""
        try:
            # Convert PIL image to CTkImage
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
            image_label = ctk.CTkLabel(parent, image=ctk_image, text="", cursor="hand2")
            image_label.pack(padx=5, pady=5)
            image_label.bind("<Button-1>", lambda e: click_callback())
            if double_click_callback:
                image_label.bind("<Double-Button-1>", lambda e: double_click_callback())
        except Exception as e:
            print(f"Error displaying image: {e}")
            # Fallback to text label if image fails
            placeholder_label = ctk.CTkLabel(parent, text="[Image]", cursor="hand2", width=80, height=120)
            placeholder_label.pack(padx=5, pady=5)
            placeholder_label.bind("<Button-1>", lambda e: click_callback())
            if double_click_callback:
                placeholder_label.bind("<Double-Button-1>", lambda e: double_click_callback())

    def _highlight_selected_result(self, selected_frame, anime):
        """Highlight the selected result and store the selection"""
        # Remove highlight from all frames
        for widget in self.results_scrollable.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.configure(border_width=0)
        
        # Highlight selected frame
        selected_frame.configure(border_width=2, border_color="blue")
        
        # Store selected anime
        self.selected_anime = anime
        self.update_status(f"Selected: {anime.get('title', 'Unknown')}")

    def play_selected_anime(self):
        """Play the selected anime"""
        if not self.selected_anime:
            messagebox.showwarning("Warning", "Please select an anime first")
            return
        
        if self.current_process:
            messagebox.showinfo("Info", "Another process is already running. Please stop it first.")
            return
        
        anime_title = self.selected_anime.get('title', 'Unknown')
        episode = self.episode_entry.get().strip() or "1"
        
        self.update_status(f"Starting {anime_title} episode {episode}...")
        
        # Build and run command
        cmd = self.build_command(anime_title)
        self.run_ani_cli_command(cmd)

    def open_episode_window(self, anime_data):
        """Open the episode selection window"""
        EpisodeWindow(self, anime_data, self.api)

    def build_command(self, anime_name=None):
        """Build the ani-cli command"""
        if not anime_name:
            anime_name = self.search_entry.get().strip()
        
        episode = self.episode_entry.get().strip() or "1"
        
        # Base command with automatic VLC and best quality
        cmd_parts = [
            'export PATH="$PATH:/c/Program Files/VideoLAN/VLC";',
            'ani-cli',
            '-S', '1',  # Use first provider (fastest)
            '-q', 'best',  # Always use best quality
            '-e', episode,
            '-v',  # Use VLC player
            f'"{anime_name}"'
        ]
        
        # Add download option if selected
        if self.download_var.get():
            cmd_parts.insert(-1, '-d')
        
        return ' '.join(cmd_parts)

    def run_ani_cli_command(self, cmd):
        """Run ani-cli command in a separate thread"""
        def run_command():
            try:
                self.update_status("Running command...")
                print(f"Running command: {cmd}")
                
                self.current_process = subprocess.Popen(
                    [self.git_bash_path, "-c", cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Wait for process to complete
                stdout, stderr = self.current_process.communicate()
                
                if stdout:
                    print(f"Output: {stdout}")
                if stderr:
                    print(f"Error: {stderr}")
                
                if self.current_process.returncode == 0:
                    self.root.after(0, lambda: self.update_status("Playback completed"))
                else:
                    self.root.after(0, lambda: self.update_status("Command failed"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Error: {str(e)}"))
                print(f"Exception: {e}")
            finally:
                self.current_process = None
        
        # Run in separate thread
        threading.Thread(target=run_command, daemon=True).start()
            
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
            
        self.root.mainloop()

def main():
    app = AniCliGUI()
    app.run()

if __name__ == "__main__":
    main()
