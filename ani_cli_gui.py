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

class AniCliGUI:
    def __init__(self):
        # Set the appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create the main window
        self.root = ctk.CTk()
        self.root.title("Ani-CLI GUI")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Git Bash path
        self.git_bash_path = r"C:\Program Files\Git\bin\bash.exe"
        
        # Variables
        self.current_process = None
        self.anime_search_api = AnimeSearchAPI()
        self.selected_anime = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="Ani-CLI GUI", font=("Arial", 24, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Single anime input section
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
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
        results_frame = ctk.CTkFrame(main_frame)
        results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        results_label = ctk.CTkLabel(results_frame, text="Search Results:", font=("Arial", 14))
        results_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Create scrollable frame for results
        self.results_scrollable = ctk.CTkScrollableFrame(results_frame, height=200)
        self.results_scrollable.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Options section
        self.setup_options_section(main_frame)
        
        # Buttons section
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        play_selected_button = ctk.CTkButton(button_frame, text="Play Selected", command=self.play_selected_anime)
        play_selected_button.pack(side="left", padx=5, pady=10)
        
        play_direct_button = ctk.CTkButton(button_frame, text="Play Direct", command=self.play_anime)
        play_direct_button.pack(side="left", padx=5, pady=10)
        
        test_button = ctk.CTkButton(button_frame, text="Test ani-cli", command=self.test_ani_cli)
        test_button.pack(side="left", padx=5, pady=10)
        
        stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_process, fg_color="red")
        stop_button.pack(side="right", padx=5, pady=10)
        
        # Status bar
        self.status_label = ctk.CTkLabel(main_frame, text="Ready", font=("Arial", 12))
        self.status_label.pack(fill="x", padx=10, pady=(0, 5))
    
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

def main():
    app = AniCliGUI()
    app.run()

if __name__ == "__main__":
    main()
