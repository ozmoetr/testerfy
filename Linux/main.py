#!/usr/bin/env python3
print('Testerfy main.py started')
import logging
import os

# Create proper log directory in user's home
log_dir = os.path.expanduser("~/.testerfy")
os.makedirs(log_dir, exist_ok=True)
desktop_log_file = os.path.join(log_dir, "testerfy_desktop_debug.log")

# Configure initial logging
logging.basicConfig(filename=desktop_log_file, level=logging.INFO)
logging.info('Testerfy main.py started (logging)')
import sys
import json
import os
import secrets
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, QListWidget, QListWidgetItem,
    QSystemTrayIcon, QMenu, QAction, QScrollArea, QMessageBox, QGroupBox, QFrame, QDialog, QDialogButtonBox,
    QWidgetAction
)
from PyQt5.QtGui import QPalette, QColor, QIcon, QPixmap, QKeySequence, QFont, QPen, QPainter
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex, QWaitCondition, QEvent, QObject
import threading
import webbrowser
import time
from flask import Flask, request
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import base64
import pynput
from pynput import keyboard
import logging
import keyring
import pathlib
from pynput.keyboard import KeyCode

# Configure logging - redirect to file to avoid console output
import os
log_dir = os.path.expanduser("~/.testerfy")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "testerfy.log")

# Configure logging to file instead of console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.NullHandler()  # Suppress console output
    ]
)
logger = logging.getLogger(__name__)

def get_documents_path():
    return os.path.join(os.path.expanduser('~'), 'Documents')

# Flask app for OAuth redirect
flask_app = Flask(__name__)
flask_server_thread = None
flask_server_running = False

oauth_result = {}
oauth_mutex = QMutex()

def run_flask_server(port, log_callback):
    global flask_server_running
    try:
        flask_server_running = True
        flask_app.run(port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        log_callback(f"Flask server error: {e}")
    finally:
        flask_server_running = False

SPOTIFY_GREEN = "#1DB954"

# Default keyboard shortcuts
DEFAULT_SHORTCUTS = {
    "like": "ctrl+shift+f8",
    "dislike": "ctrl+shift+f9"
}

# Settings file path
SETTINGS_FILE = os.path.expanduser("~/.testerfy_settings.json")
# Config file path for prefilled credentials and selected playlists
def get_config_file_path():
    env_path = os.environ.get('TESTERFY_CONFIG_PATH')
    if env_path:
        return os.path.expanduser(env_path)
    docs = get_documents_path()
    return os.path.join(docs, '.testerfy_config.json')

CONFIG_FILE = get_config_file_path()

def load_settings():
    """Load settings from file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load settings: {e}")
    return DEFAULT_SHORTCUTS.copy()

def save_settings(settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Could not save settings: {e}")
        return False

def load_config():
    """Load config from file, supporting credentials and selected_playlists."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                import json
                return json.load(f)
    except Exception:
        pass
    return {}

def load_config_credentials():
    config = load_config()
    client_id = config.get('client_id', '')
    client_secret = config.get('client_secret', '')
    redirect_uri = config.get('redirect_uri', '')
    return client_id, client_secret, redirect_uri

def load_config_selected_playlists():
    config = load_config()
    config_playlists = config.get('selected_playlists', [])
    
    # Add local default playlists that should always be selected
    local_default_playlists = [
        "2axbjO6lDhdUf5YmoaXniB",
        "4yRrCWNhWOqWZx5lmFqZvt"
    ]
    
    # Combine config playlists with local defaults, avoiding duplicates
    all_playlists = list(set(config_playlists + local_default_playlists))
    
    return all_playlists

USER_SETTINGS_FILE = os.path.expanduser("~/.testerfy_user_settings.json")

def load_user_settings(user_id):
    try:
        if os.path.exists(USER_SETTINGS_FILE):
            with open(USER_SETTINGS_FILE, 'r') as f:
                all_settings = json.load(f)
                return all_settings.get(user_id, {})
    except Exception as e:
        logger.warning(f"Could not load user settings: {e}")
    return {}

def save_user_settings(user_id, user_settings):
    try:
        all_settings = {}
        if os.path.exists(USER_SETTINGS_FILE):
            with open(USER_SETTINGS_FILE, 'r') as f:
                all_settings = json.load(f)
        all_settings[user_id] = user_settings
        with open(USER_SETTINGS_FILE, 'w') as f:
            json.dump(all_settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Could not save user settings: {e}")
        return False

# Simple Spotify-green SVG icon as base64 (for demonstration)
SPOTIFY_SVG = '''
<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="16" cy="16" r="16" fill="#1DB954"/>
<path d="M23.5 22.5C19.5 20 12.5 20 8.5 22.5" stroke="black" stroke-width="2" stroke-linecap="round"/>
<path d="M22 18C18.5 16 13.5 16 10 18" stroke="black" stroke-width="2" stroke-linecap="round"/>
<path d="M20.5 14C17.5 12.5 14.5 12.5 11.5 14" stroke="black" stroke-width="2" stroke-linecap="round"/>
</svg>
'''

def svg_to_pixmap(svg):
    try:
        from PyQt5.QtSvg import QSvgRenderer
        from PyQt5.QtGui import QImage, QPainter
        image = QImage(32, 32, QImage.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(bytearray(svg, encoding='utf-8'))
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        return QPixmap.fromImage(image)
    except Exception as e:
        logger.warning(f"Could not create SVG pixmap: {e}")
        return QPixmap()

def parse_shortcut(shortcut_str):
    """Parse shortcut string into key components, handling shifted symbols."""
    # Map of shifted symbols to their base key and required shift
    shifted_symbol_map = {
        '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
        '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
    }
    try:
        parts = shortcut_str.lower().split('+')
        keys = set()
        for part in parts:
            part = part.strip()
            if part in ['ctrl', 'shift', 'alt', 'super']:
                keys.add(part)
            elif part in shifted_symbol_map:
                # Add the base key and ensure shift is present
                keys.add(shifted_symbol_map[part])
                keys.add('shift')
            elif len(part) == 1:
                keys.add(part)
            elif part.startswith('f') and part[1:].isdigit():
                # Function keys like f8, f9, etc.
                keys.add(part)
            else:
                keys.add(part)
        return keys
    except Exception as e:
        logger.error(f"Error parsing shortcut {shortcut_str}: {e}")
        return set()

# Map of shifted symbols to their base key and required shift
SHIFTED_SYMBOL_MAP = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
}
# Reverse map for normalization
BASE_TO_SHIFTED = {v: k for k, v in SHIFTED_SYMBOL_MAP.items()}


def normalize_keys_for_comparison(keys):
    """Normalize a set of keys so shifted symbols and base keys are treated as equivalent if shift is present."""
    keys = set(keys)
    if 'shift' in keys:
        normalized = set()
        for k in keys:
            if k in SHIFTED_SYMBOL_MAP:
                # If a shifted symbol is present, add its base key
                normalized.add(SHIFTED_SYMBOL_MAP[k])
            elif k in BASE_TO_SHIFTED:
                # If a base key is present, add its shifted symbol
                normalized.add(BASE_TO_SHIFTED[k])
            normalized.add(k)
        return normalized
    return keys


def is_shortcut_match(pressed_keys, shortcut_keys):
    """Check if pressed keys match the shortcut, treating shifted symbols and base keys as equivalent if shift is present."""
    try:
        pressed_set = normalize_keys_for_comparison(pressed_keys)
        shortcut_set = normalize_keys_for_comparison(shortcut_keys)
        return pressed_set == shortcut_set
    except Exception as e:
        logger.error(f"Error checking shortcut match: {e}")
        return False

class PlaylistLoaderThread(QThread):
    """Thread for loading playlists to avoid blocking UI"""
    playlists_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, spotify_client):
        super().__init__()
        self.spotify_client = spotify_client
    
    def run(self):
        try:
            # Get user's playlists
            results = self.spotify_client.current_user_playlists(limit=50)
            
            playlists = []
            user_id = self.spotify_client.current_user()['id']
            
            for playlist in results['items']:
                # Only include playlists the user can modify
                if playlist['owner']['id'] == user_id:
                    playlists.append({
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'tracks_total': playlist['tracks']['total']
                    })
            
            self.playlists_loaded.emit(playlists)
            
        except Exception as e:
            logger.error(f"Error loading playlists: {e}")
            self.error_occurred.emit(str(e))

class SettingsTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self._auto_auth_scheduled = False  # Guard flag to prevent double auto-auth
        layout = QVBoxLayout()
        
        # Setup instructions
        instructions_group = QGroupBox("📋 Setup Instructions")
        instructions_group.setStyleSheet(f"""
            QGroupBox {{
                color: white;
                font-weight: bold;
                border: 2px solid {SPOTIFY_GREEN};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        instructions_layout = QVBoxLayout()
        
        instructions_text = QTextEdit()
        instructions_text.setMaximumHeight(200)
        instructions_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 8px;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        instructions_text.setPlainText("""🔧 How to get your Spotify API credentials:

1. Go to https://developer.spotify.com/dashboard
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in the app details:
   • App name: "Testerfy" (or any name you prefer)
   • App description: "Personal music management app"
   • Website: Can be left blank or use your personal site
   • Redirect URIs: Add "http://127.0.0.1:9111/callback"
   • Category: Choose "Other"
5. Click "Save"
6. Copy your Client ID and Client Secret from the app dashboard
7. Paste them in the fields below

⚠️ Keep your Client Secret private and never share it publicly!""")
        instructions_text.setReadOnly(True)
        instructions_layout.addWidget(instructions_text)
        instructions_group.setLayout(instructions_layout)
        layout.addWidget(instructions_group)
        
        # Security notice
        security_label = QLabel("⚠️ SECURITY: Enter your own Spotify API credentials")
        security_label.setStyleSheet("color: #ff6b6b; font-weight: bold; font-size: 12px;")
        layout.addWidget(security_label)
        
        self.client_id_input = QLineEdit()
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.Password)
        self.redirect_uri_input = QLineEdit()
        self.save_credentials_checkbox = QCheckBox("Save credentials for future use (secure)")
        self.save_credentials_checkbox.setToolTip("If checked, your credentials will be stored securely using your system's keyring.")
        # Remove auto-login checkbox and logic
        # self.auto_login_checkbox = QCheckBox("Auto-login with saved credentials")
        # self.auto_login_checkbox.setToolTip("If checked, the app will automatically authenticate on launch if credentials are saved.")
        
        # Credential input fields (always visible)
        layout.addWidget(QLabel("Spotify Client ID:"))
        layout.addWidget(self.client_id_input)
        layout.addWidget(QLabel("Spotify Client Secret:"))
        layout.addWidget(self.client_secret_input)
        layout.addWidget(QLabel("Redirect URI:"))
        layout.addWidget(self.redirect_uri_input)
        # Checkboxes for save and auto-login
        layout.addWidget(self.save_credentials_checkbox)
        # Remove auto-login checkbox
        # layout.addWidget(self.auto_login_checkbox)
        self.auth_button = QPushButton("Authenticate")
        self.status_label = QLabel("")
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.status_label.setStyleSheet(f"color: {SPOTIFY_GREEN};")
        self.auth_button.clicked.connect(self.start_authentication)
        # Add Sign Out button
        self.sign_out_button = QPushButton("Sign Out")
        self.sign_out_button.clicked.connect(self.sign_out)
        layout.addWidget(self.auth_button)
        layout.addWidget(self.sign_out_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addStretch()
        self.setLayout(layout)
        self.sp_oauth = None
        self.token_info = None
        self.username = None
        self._registered_route = None
        # Prefill from config file if present (move this up)
        config_id, config_secret, config_uri = load_config_credentials()
        if config_id:
            self.client_id_input.setText(config_id)
        if config_secret:
            self.client_secret_input.setText(config_secret)
        if config_uri:
            self.redirect_uri_input.setText(config_uri)
        self._load_saved_credentials()
        # Only auto-authenticate if credentials are saved and all fields are filled (after all prefills)
        self._maybe_auto_authenticate()

    def _maybe_auto_authenticate(self):
        if not self._auto_auth_scheduled and self.save_credentials_checkbox.isChecked() and self.client_id_input.text() and self.client_secret_input.text() and self.redirect_uri_input.text():
            self._auto_auth_scheduled = True
            QTimer.singleShot(500, self.start_authentication)

    def log(self, msg):
        if self.main_window and hasattr(self.main_window, 'debug_log_tab'):
            self.main_window.debug_log_tab.log(msg)
        else:
            logger.info(msg)

    def _load_saved_credentials(self):
        try:
            client_id = keyring.get_password("testerfy_spotify", "client_id")
            client_secret = keyring.get_password("testerfy_spotify", "client_secret")
            redirect_uri = keyring.get_password("testerfy_spotify", "redirect_uri")
            if client_id:
                self.client_id_input.setText(client_id)
                self.save_credentials_checkbox.setChecked(True)
            if client_secret:
                self.client_secret_input.setText(client_secret)
            if redirect_uri:
                self.redirect_uri_input.setText(redirect_uri)
        except Exception as e:
            logger.warning(f"Could not load credentials from keyring: {e}")

    def start_authentication(self):
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        redirect_uri = self.redirect_uri_input.text().strip()
        
        if not client_id or not client_secret or not redirect_uri:
            self.error_label.setText("All fields are required.")
            return
            
        self.error_label.setText("")
        self.status_label.setText("Starting authentication...")
        self.log("Starting OAuth authentication...")
        
        # Register Flask route for the redirect URI path only if not already registered
        from urllib.parse import urlparse
        parsed = urlparse(redirect_uri)
        path = parsed.path or "/"
        global flask_app, flask_server_thread, flask_server_running
        
        if not hasattr(flask_app.view_functions, path):
            try:
                def dynamic_oauth_callback():
                    global oauth_result
                    code = request.args.get('code')
                    error = request.args.get('error')
                    if code:
                        oauth_mutex.lock()
                        oauth_result['code'] = code
                        oauth_mutex.unlock()
                        return '<h2 style="color:#1DB954">Authentication successful! Closing in 3 seconds...</h2><script>setTimeout(function(){window.close();}, 3000);</script>'
                    elif error:
                        oauth_mutex.lock()
                        oauth_result['error'] = error
                        oauth_mutex.unlock()
                        return f'<h2 style="color:red">Error: {error}</h2>'
                    else:
                        return '<h2 style="color:red">No code or error received.</h2>'
                        
                flask_app.add_url_rule(path, endpoint=path, view_func=dynamic_oauth_callback)
                self._registered_route = path
                self.log(f"Registered Flask route for {path}")
            except Exception as e:
                self.error_label.setText(f"Flask route error: {e}")
                self.log(f"Flask route error: {e}")
                return
                
        # Start Flask server in a thread if not already running
        port = parsed.port or 8080
        if not flask_server_running:
            try:
                flask_server_thread = threading.Thread(target=run_flask_server, args=(port, self.log), daemon=True)
                flask_server_thread.start()
                time.sleep(1)  # Give Flask a moment to start
                self.log(f"Started Flask server on port {port}")
            except Exception as e:
                self.error_label.setText(f"Flask server error: {e}")
                self.log(f"Flask server error: {e}")
                return
                
        # Set up Spotipy OAuth
        token_cache_path = os.path.expanduser("~/.testerfy_spotify_token_cache")
        self.sp_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-read-private playlist-read-private playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state user-library-modify",
            open_browser=False,
            cache_path=token_cache_path  # Persistent token cache
        )
        auth_url = self.sp_oauth.get_authorize_url()
        self.log(f"Opening browser to: {auth_url}")
        webbrowser.open(auth_url)
        self.status_label.setText("Waiting for authentication...")
        # Start thread to poll for token
        threading.Thread(target=self.poll_for_token, daemon=True).start()

        # Save credentials if checkbox is checked
        if self.save_credentials_checkbox.isChecked():
            try:
                keyring.set_password("testerfy_spotify", "client_id", client_id)
                keyring.set_password("testerfy_spotify", "client_secret", client_secret)
                keyring.set_password("testerfy_spotify", "redirect_uri", redirect_uri)
            except Exception as e:
                logger.warning(f"Could not save credentials to keyring: {e}")
        else:
            # Remove credentials if unchecked
            try:
                keyring.delete_password("testerfy_spotify", "client_id")
            except Exception:
                pass
            try:
                keyring.delete_password("testerfy_spotify", "client_secret")
            except Exception:
                pass
            try:
                keyring.delete_password("testerfy_spotify", "redirect_uri")
            except Exception:
                pass

    def poll_for_token(self):
        global oauth_result
        for _ in range(60):  # Wait up to 60 seconds
            oauth_mutex.lock()
            if oauth_result.get('code'):
                try:
                    code = oauth_result['code']
                    oauth_mutex.unlock()
                    
                    self.log(f"Received authorization code, attempting to exchange for token...")
                    
                    # Use get_cached_token instead of deprecated get_access_token
                    if self.sp_oauth:
                        token_info = self.sp_oauth.get_cached_token()
                        if not token_info:
                            self.log("No cached token found, exchanging code for token...")
                            try:
                                token_info = self.sp_oauth.get_access_token(code)
                                self.log("Token exchange successful")
                            except Exception as token_error:
                                self.log(f"Token exchange failed: {token_error}")
                                if "invalid_client" in str(token_error).lower():
                                    self.error_label.setText("Invalid client secret. Please check your Spotify API credentials.")
                                    self.log("ERROR: Invalid client secret - please verify your client secret in the Settings tab")
                                elif "invalid_client_id" in str(token_error).lower():
                                    self.error_label.setText("Invalid client ID. Please check your Spotify API credentials.")
                                    self.log("ERROR: Invalid client ID - please verify your client ID in the Settings tab")
                                else:
                                    self.error_label.setText(f"Authentication failed: {token_error}")
                                    self.log(f"ERROR: Authentication failed - {token_error}")
                                oauth_result = {}
                                return
                        
                        self.token_info = token_info
                        if token_info and 'access_token' in token_info:
                            self.log("Access token obtained successfully")
                            sp = spotipy.Spotify(auth=token_info['access_token'])
                        else:
                            raise Exception("Failed to get access token from token info")
                    else:
                        raise Exception("OAuth object not initialized")
                    
                    if sp:
                        self.log("Testing Spotify client connection...")
                        user = sp.current_user()
                        if user:
                            self.username = user.get('display_name') or user.get('id', 'Unknown')
                            self.log(f"Successfully connected to Spotify as: {self.username}")
                        else:
                            raise Exception("Failed to get user info from Spotify")
                    else:
                        raise Exception("Failed to create Spotify client")
                    self.status_label.setText(f"Authenticated as {self.username}")
                    self.log(f"Authentication successful! User: {self.username}")
                    self.error_label.setText("")
                    
                    # Load playlists after successful authentication
                    self.load_playlists_after_auth(sp)
                    
                except Exception as e:
                    self.error_label.setText(f"Authentication error: {e}")
                    self.log(f"Authentication error: {e}")
                    import traceback
                    self.log(f"Full error traceback: {traceback.format_exc()}")
                oauth_result = {}
                return
            elif oauth_result.get('error'):
                error = oauth_result['error']
                oauth_mutex.unlock()
                self.error_label.setText(f"OAuth error: {error}")
                self.log(f"OAuth error received: {error}")
                oauth_result = {}
                return
            oauth_mutex.unlock()
            time.sleep(1)
        self.error_label.setText("Authentication timed out.")
        self.log("Authentication timed out.")

    def load_playlists_after_auth(self, spotify_client):
        """Load playlists after successful authentication"""
        try:
            self.log("=== PLAYLIST LOADING DEBUG ===")
            self.log("load_playlists_after_auth called")
            
            # Set the Spotify client in the main window
            if self.main_window:
                self.log("Calling main_window.set_spotify_client...")
                self.main_window.set_spotify_client(spotify_client)
                self.log("set_spotify_client called successfully")
            else:
                self.log("Error: No main window reference")
        except Exception as e:
            self.log(f"Error loading playlists after auth: {e}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")

    def sign_out(self):
        # Remove credentials from keyring
        try:
            keyring.delete_password("testerfy_spotify", "client_id")
        except Exception:
            pass
        try:
            keyring.delete_password("testerfy_spotify", "client_secret")
        except Exception:
            pass
        try:
            keyring.delete_password("testerfy_spotify", "redirect_uri")
        except Exception:
            pass
        # Remove persistent token cache file
        try:
            token_cache_path = os.path.expanduser("~/.testerfy_spotify_token_cache")
            if os.path.exists(token_cache_path):
                os.remove(token_cache_path)
        except Exception as e:
            logger.warning(f"Could not remove token cache file: {e}")
        # Clear input fields and checkbox
        self.client_id_input.clear()
        self.client_secret_input.clear()
        self.redirect_uri_input.setText("http://127.0.0.1:9111/callback")
        self.save_credentials_checkbox.setChecked(False)
        # Remove: self.auto_login_checkbox.setChecked(False)
        self.status_label.setText("")
        self.error_label.setText("")
        self.username = None
        # Reset main window state if needed
        if self.main_window:
            self.main_window.set_spotify_client(None)
        QMessageBox.information(self, "Signed Out", "You have been signed out and credentials have been cleared.")

class PlaylistItemWidget(QWidget):
    """Custom widget for playlist items with proper layout"""
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Checkbox
        self.checkbox = QCheckBox()
        layout.addWidget(self.checkbox)
        
        # Playlist info in a frame for better styling
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #333;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(8, 4, 8, 4)
        
        # Playlist name
        name_label = QLabel(self.playlist['name'])
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Track count
        tracks_label = QLabel(f"{self.playlist['tracks_total']} tracks")
        tracks_label.setStyleSheet("color: #aaa; font-size: 11px;")
        info_layout.addWidget(tracks_label)
        
        info_frame.setLayout(info_layout)
        layout.addWidget(info_frame, 1)  # Expand to fill available space
        
        self.setLayout(layout)
        self.setMinimumHeight(50)

class PlaylistsTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Select playlists for liked songs workflow:")
        header_label.setStyleSheet(f"color: {SPOTIFY_GREEN}; font-weight: bold; font-size: 14px;")
        layout.addWidget(header_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Selected Playlists")
        self.deselect_button = QPushButton("Deselect All")
        self.refresh_button = QPushButton("Refresh Playlists")
        self.save_button.clicked.connect(self.save_selected_playlists)
        self.deselect_button.clicked.connect(self.deselect_all)
        self.refresh_button.clicked.connect(self.refresh_playlists)
        self.export_button = QPushButton("Export Playlists")
        self.export_button.clicked.connect(self.export_playlists)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.deselect_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Playlist list with improved styling
        self.playlist_list = QListWidget()
        self.playlist_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QListWidget::item {
                background-color: transparent;
                border-radius: 3px;
                margin: 2px;
                padding: 0px;
            }
            QListWidget::item:selected {
                background-color: #1DB954;
                color: black;
            }
            QListWidget::item:hover {
                background-color: #444;
            }
        """)
        layout.addWidget(self.playlist_list)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {SPOTIFY_GREEN};")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.playlists = []
        self.selected_playlists = set()
        self.playlist_loader_thread = None
        self.user_playlists = []
        self.user_id = None
        # No longer pre-load config selection here; do it after playlists are loaded

    def log(self, msg):
        if self.main_window and hasattr(self.main_window, 'debug_log_tab'):
            self.main_window.debug_log_tab.log(msg)
        else:
            logger.info(msg)

    def load_playlists(self, spotify_client):
        self.spotify_client = spotify_client
        self.playlist_loader_thread = PlaylistLoaderThread(spotify_client)
        self.playlist_loader_thread.playlists_loaded.connect(self.on_playlists_loaded)
        self.playlist_loader_thread.error_occurred.connect(self.on_playlist_error)
        self.playlist_loader_thread.start()

    def on_playlists_loaded(self, playlists):
        self.playlists = playlists
        # Pre-select playlists from config (by ID or exact name) every time playlists are loaded
        config_selected = set(load_config_selected_playlists())
        for p in playlists:
            if p['id'] in config_selected or p['name'] in config_selected:
                self.selected_playlists.add(p['id'])
        # Remove duplicates
        self.selected_playlists = set(self.selected_playlists)
        self.display_playlists()
        self.status_label.setText(f"Loaded {len(self.playlists)} playlists")

    def on_playlist_error(self, error_msg):
        """Handle playlist loading error"""
        self.log(f"Error loading playlists: {error_msg}")
        self.status_label.setText(f"Error loading playlists: {error_msg}")

    def refresh_playlists(self):
        """Refresh playlists manually"""
        if self.main_window and self.main_window.spotify_client:
            self.load_playlists(self.main_window.spotify_client)

    def display_playlists(self):
        """Display playlists in the list widget with custom widgets"""
        try:
            self.playlist_list.clear()
            
            for playlist in self.playlists:
                item = QListWidgetItem()
                widget = PlaylistItemWidget(playlist)
                
                # Connect checkbox to selection handler
                widget.checkbox.setChecked(playlist['id'] in self.selected_playlists)
                widget.checkbox.stateChanged.connect(
                    lambda state, pid=playlist['id']: self.on_playlist_toggled(pid, state)
                )
                
                item.setSizeHint(widget.sizeHint())
                self.playlist_list.addItem(item)
                self.playlist_list.setItemWidget(item, widget)
                
        except Exception as e:
            self.log(f"Error displaying playlists: {e}")

    def on_playlist_toggled(self, playlist_id, state):
        """Handle playlist checkbox toggle"""
        if state == Qt.CheckState.Checked:
            self.selected_playlists.add(playlist_id)
        else:
            self.selected_playlists.discard(playlist_id)
        
        self.log(f"Selected playlists: {len(self.selected_playlists)}")

    def save_selected_playlists(self):
        """Save the selected playlists"""
        try:
            # Store selected playlist IDs (you can save to file/database later)
            selected_names = [p['name'] for p in self.playlists if p['id'] in self.selected_playlists]
            
            self.log(f"Saved {len(self.selected_playlists)} playlists: {', '.join(selected_names)}")
            self.status_label.setText(f"Saved {len(self.selected_playlists)} playlists")
            
            # You can add persistence here (save to file, database, etc.)
            # For now, we'll just store in memory
            
        except Exception as e:
            self.log(f"Error saving playlists: {e}")
            self.status_label.setText(f"Error saving playlists: {e}")

    def deselect_all(self):
        """Deselect all playlists"""
        self.selected_playlists.clear()
        self.display_playlists()
        self.log("Deselected all playlists")
        self.status_label.setText("Deselected all playlists")

    def get_selected_playlist_ids(self):
        """Get list of selected playlist IDs"""
        return list(self.selected_playlists)

    def export_playlists(self):
        if self.main_window and hasattr(self.main_window, 'user_id') and self.main_window.user_id:
            user_id = self.main_window.user_id
            export_path = os.path.join(get_documents_path(), f".testerfy_playlists_{user_id}.json")
            try:
                with open(export_path, 'w') as f:
                    json.dump(list(self.selected_playlists), f, indent=2)
                self.status_label.setText(f"Exported playlists to {export_path}")
            except Exception as e:
                self.status_label.setText(f"Failed to export playlists: {e}")

    def set_user_settings(self, playlists):
        self.user_playlists = playlists
        self.selected_playlists = set(playlists)
        # Try to load from export file if it exists
        if self.main_window and hasattr(self.main_window, 'user_id') and self.main_window.user_id:
            user_id = self.main_window.user_id
            import_path = os.path.join(get_documents_path(), f".testerfy_playlists_{user_id}.json")
            if os.path.exists(import_path):
                try:
                    with open(import_path, 'r') as f:
                        file_playlists = set(json.load(f))
                        self.selected_playlists = file_playlists
                except Exception as e:
                    self.status_label.setText(f"Failed to import playlists: {e}")
        self.display_playlists()
        self.status_label.setText(f"Loaded {len(self.selected_playlists)} saved playlists")

class ShortcutCaptureDialog(QDialog):
    def __init__(self, parent=None, current_shortcut=None, other_shortcut=None, other_label=None):
        super().__init__(parent)
        self.setWindowTitle("Set New Shortcut")
        self.setModal(True)
        self.resize(350, 120)
        self.result_shortcut = None
        self.other_shortcut = other_shortcut
        self.other_label = other_label
        self.label = QLabel("Press your desired key combination... (1-3 keys, including modifiers)")
        self.label.setStyleSheet("font-size: 13px; color: #1DB954;")
        self.input_display = QLineEdit()
        self.input_display.setReadOnly(True)
        self.input_display.setStyleSheet("font-size: 15px; background: #222; color: #fff; border: 1px solid #444; padding: 6px;")
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = self.button_box.button(QDialogButtonBox.Save)
        if save_btn:
            save_btn.setEnabled(False)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input_display)
        layout.addWidget(self.button_box)
        self.setLayout(layout)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.installEventFilter(self)
        self._pressed_keys = set()
        self._last_valid_shortcut = None
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            key_str = self._key_to_str(key)
            if key_str:
                self._pressed_keys.add(key_str)
                self._update_display()
            return True
        elif event.type() == QEvent.Type.KeyRelease:
            key = event.key()
            key_str = self._key_to_str(key)
            if key_str and key_str in self._pressed_keys:
                self._pressed_keys.remove(key_str)
                self._update_display()
            return True
        return super().eventFilter(obj, event)
    def _key_to_str(self, key):
        keymap = {
            Qt.Key.Key_Control: 'ctrl',
            Qt.Key.Key_Shift: 'shift',
            Qt.Key.Key_Alt: 'alt',
            Qt.Key.Key_Meta: 'super',
        }
        if key in keymap:
            return keymap[key]
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            return f'f{key - Qt.Key.Key_F1 + 1}'
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return str(key - Qt.Key.Key_0)
        elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key).lower()
        # Add support for common symbol keys
        symbol_keys = {
            Qt.Key.Key_Exclam: '!', Qt.Key.Key_At: '@', Qt.Key.Key_NumberSign: '#', Qt.Key.Key_Dollar: '$',
            Qt.Key.Key_Percent: '%', Qt.Key.Key_AsciiCircum: '^', Qt.Key.Key_Ampersand: '&', Qt.Key.Key_Asterisk: '*',
            Qt.Key.Key_ParenLeft: '(', Qt.Key.Key_ParenRight: ')', Qt.Key.Key_Underscore: '_', Qt.Key.Key_Plus: '+',
            Qt.Key.Key_BraceLeft: '{', Qt.Key.Key_BraceRight: '}', Qt.Key.Key_Bar: '|', Qt.Key.Key_Colon: ':',
            Qt.Key.Key_QuoteDbl: '"', Qt.Key.Key_Less: '<', Qt.Key.Key_Greater: '>', Qt.Key.Key_Question: '?',
            Qt.Key.Key_Minus: '-', Qt.Key.Key_Equal: '=', Qt.Key.Key_BracketLeft: '[', Qt.Key.Key_BracketRight: ']',
            Qt.Key.Key_Backslash: '\\', Qt.Key.Key_Semicolon: ';', Qt.Key.Key_Apostrophe: "'", Qt.Key.Key_Comma: ',',
            Qt.Key.Key_Period: '.', Qt.Key.Key_Slash: '/'
        }
        if key in symbol_keys:
            return symbol_keys[key]
        return None
    def _update_display(self):
        mods = [k for k in self._pressed_keys if k in ['ctrl', 'shift', 'alt', 'super']]
        keys = [k for k in self._pressed_keys if k not in mods]
        save_btn = self.button_box.button(QDialogButtonBox.Save)
        shortcut = '+'.join(sorted(mods) + sorted(keys))
        # If a valid shortcut is currently pressed, update last valid
        if keys and 1 <= len(self._pressed_keys) <= 3:
            self._last_valid_shortcut = shortcut
            self.input_display.setText(shortcut)
            self.label.setText("Press your desired key combination... (1-3 keys, including modifiers)")
            if self.other_shortcut and shortcut == self.other_shortcut:
                self.label.setText(f"Cannot use same shortcut as {self.other_label}!")
                if save_btn:
                    save_btn.setEnabled(False)
                self.result_shortcut = None
                return
            if save_btn:
                save_btn.setEnabled(True)
            self.result_shortcut = shortcut
        else:
            # If no keys are pressed, keep showing the last valid shortcut
            if self._last_valid_shortcut:
                self.input_display.setText(self._last_valid_shortcut)
                self.label.setText("Press your desired key combination... (1-3 keys, including modifiers)")
                if self.other_shortcut and self._last_valid_shortcut == self.other_shortcut:
                    self.label.setText(f"Cannot use same shortcut as {self.other_label}!")
                    if save_btn:
                        save_btn.setEnabled(False)
                    self.result_shortcut = None
                    return
                if save_btn:
                    save_btn.setEnabled(True)
                self.result_shortcut = self._last_valid_shortcut
            else:
                self.input_display.setText("")
                self.label.setText("Press your desired key combination... (1-3 keys, including modifiers)")
                if save_btn:
                    save_btn.setEnabled(False)
                self.result_shortcut = None
    def get_shortcut(self):
        if self.exec_() == QDialog.Accepted and self.result_shortcut:
            return self.result_shortcut
        return None

class KeyboardShortcutsTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.settings = load_settings()
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Customizable Global Keyboard Shortcuts:")
        header_label.setStyleSheet(f"color: {SPOTIFY_GREEN}; font-weight: bold; font-size: 14px;")
        layout.addWidget(header_label)
        
        # Shortcuts configuration group
        shortcuts_group = QGroupBox("Shortcut Configuration")
        shortcuts_group.setStyleSheet(f"""
            QGroupBox {{
                color: white;
                font-weight: bold;
                border: 2px solid {SPOTIFY_GREEN};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        shortcuts_layout = QVBoxLayout()
        
        # Like shortcut
        like_layout = QHBoxLayout()
        like_layout.addWidget(QLabel("Like Song:"))
        self.like_shortcut_input = QLineEdit()
        self.like_shortcut_input.setText(self.settings.get("like", DEFAULT_SHORTCUTS["like"]))
        self.like_shortcut_input.setReadOnly(True)
        self.like_shortcut_input.setPlaceholderText("e.g., ctrl+shift+1")
        like_layout.addWidget(self.like_shortcut_input)
        self.like_set_button = QPushButton("Set New Command")
        self.like_set_button.clicked.connect(lambda: self.set_new_shortcut('like'))
        like_layout.addWidget(self.like_set_button)
        shortcuts_layout.addLayout(like_layout)
        
        # Dislike shortcut
        dislike_layout = QHBoxLayout()
        dislike_layout.addWidget(QLabel("Dislike Song:"))
        self.dislike_shortcut_input = QLineEdit()
        self.dislike_shortcut_input.setText(self.settings.get("dislike", DEFAULT_SHORTCUTS["dislike"]))
        self.dislike_shortcut_input.setReadOnly(True)
        self.dislike_shortcut_input.setPlaceholderText("e.g., ctrl+shift+3")
        dislike_layout.addWidget(self.dislike_shortcut_input)
        self.dislike_set_button = QPushButton("Set New Command")
        self.dislike_set_button.clicked.connect(lambda: self.set_new_shortcut('dislike'))
        dislike_layout.addWidget(self.dislike_set_button)
        shortcuts_layout.addLayout(dislike_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset to Defaults")
        self.save_button = QPushButton("Save Shortcuts")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        self.save_button.clicked.connect(self.save_shortcuts)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        shortcuts_layout.addLayout(button_layout)
        
        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)
        
        # Instructions
        instructions_text = """
        <h3>How to use:</h3>
        <ul>
            <li>Enter shortcuts in the format: <b>ctrl+shift+key</b></li>
            <li>Valid modifiers: <b>ctrl</b>, <b>shift</b>, <b>alt</b>, <b>super</b></li>
            <li>Examples: <b>ctrl+shift+1</b>, <b>ctrl+alt+l</b>, <b>super+shift+d</b></li>
            <li><b>Shifted symbols are supported!</b> For example, <b>ctrl+shift+!</b> is the same as <b>ctrl+shift+1</b>, <b>ctrl+shift+@</b> is <b>ctrl+shift+2</b>, <b>ctrl+shift+(</b> is <b>ctrl+shift+9</b>, etc.</li>
            <li>You can use any symbol or letter with modifiers. The program will automatically map shifted symbols to their base key and include shift.</li>
        </ul>
        <h3>Requirements:</h3>
        <ul>
            <li>You must be authenticated with Spotify</li>
            <li>Spotify must be playing a song</li>
            <li>Testerfy must be running (can be minimized to tray)</li>
        </ul>
        <h3>Note:</h3>
        <p>Shortcuts work globally (even when Testerfy is in the background). 
        Changes take effect immediately after saving.</p>
        """
        
        instructions_label = QLabel(instructions_text)
        instructions_label.setStyleSheet("color: white; font-size: 12px;")
        instructions_label.setWordWrap(True)
        
        # Make it scrollable
        scroll_area = QScrollArea()
        scroll_area.setWidget(instructions_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        
        layout.addWidget(scroll_area)
        layout.addStretch()
        self.setLayout(layout)

        # Add non-editable info for zoom shortcuts
        zoom_info = QLabel("<b>View Zoom:</b>  Ctrl+Shift+= (Zoom In),  Ctrl+Shift+- (Zoom Out)")
        zoom_info.setStyleSheet("color: #aaa; font-size: 12px; margin-top: 8px;")
        layout.addWidget(zoom_info)

    def reset_to_defaults(self):
        """Reset shortcuts to default values"""
        reply = QMessageBox.question(
            self, 
            "Reset Shortcuts", 
            "Are you sure you want to reset to default shortcuts?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.like_shortcut_input.setText(DEFAULT_SHORTCUTS["like"])
            self.dislike_shortcut_input.setText(DEFAULT_SHORTCUTS["dislike"])
            if self.main_window:
                self.main_window.debug_log_tab.log(f"Shortcuts reset to defaults")

    def save_shortcuts(self, update_only=False):
        """Save the current shortcuts"""
        try:
            like_shortcut = self.like_shortcut_input.text().strip().lower()
            dislike_shortcut = self.dislike_shortcut_input.text().strip().lower()
            
            # Validate shortcuts
            if not like_shortcut or not dislike_shortcut:
                if not update_only:
                    QMessageBox.warning(self, "Invalid Shortcuts", "Please enter both shortcuts.")
                return
            
            # Basic validation
            if like_shortcut == dislike_shortcut:
                if not update_only:
                    QMessageBox.warning(self, "Invalid Shortcuts", "Like and dislike shortcuts cannot be the same.")
                return
            
            # Conflict detection (normalized)
            like_keys = parse_shortcut(like_shortcut)
            dislike_keys = parse_shortcut(dislike_shortcut)
            if normalize_keys_for_comparison(like_keys) == normalize_keys_for_comparison(dislike_keys):
                if not update_only:
                    QMessageBox.warning(self, "Shortcut Conflict", "The like and dislike shortcuts are functionally identical. Please choose different shortcuts.")
                return
            
            # Update settings
            self.settings["like"] = like_shortcut
            self.settings["dislike"] = dislike_shortcut
            
            # Save to file
            if save_settings(self.settings) and not update_only:
                QMessageBox.information(self, "Success", "Shortcuts saved successfully!")
                
                # Update main window shortcuts
                if self.main_window:
                    self.main_window.update_shortcuts(self.settings)
                    self.main_window.debug_log_tab.log(f"Shortcuts updated: Like={like_shortcut}, Dislike={dislike_shortcut}")
            else:
                if not update_only:
                    QMessageBox.critical(self, "Error", "Failed to save shortcuts to file.")
                
        except Exception as e:
            if not update_only:
                QMessageBox.critical(self, "Error", f"Error saving shortcuts: {e}")

    def set_new_shortcut(self, which):
        # Pass the opposing shortcut for validation
        if which == 'like':
            other = self.dislike_shortcut_input.text().strip().lower()
            other_label = 'Dislike'
        else:
            other = self.like_shortcut_input.text().strip().lower()
            other_label = 'Like'
        dlg = ShortcutCaptureDialog(self, current_shortcut=self.settings.get(which), other_shortcut=other, other_label=other_label)
        shortcut = dlg.get_shortcut()
        if shortcut:
            if which == 'like':
                self.like_shortcut_input.setText(shortcut)
                self.settings['like'] = shortcut
            elif which == 'dislike':
                self.dislike_shortcut_input.setText(shortcut)
                self.settings['dislike'] = shortcut
            # Save immediately and update hotkeys/tray
            self.save_shortcuts(update_only=True)
            if self.main_window:
                self.main_window.update_shortcuts(self.settings)

    def set_user_settings(self, shortcuts):
        if shortcuts:
            self.settings.update(shortcuts)
            # Optionally update UI to reflect saved shortcuts

class DebugLogTab(QWidget):
    log_signal = pyqtSignal(str)
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Monospace", 9))
        layout.addWidget(QLabel("Debug / Log Output:"))
        layout.addWidget(self.log_area)
        # Add toggle button for keyboard debug logging
        self.keyboard_debug_button = QPushButton("Enable Keyboard Debug Logging")
        self.keyboard_debug_button.setCheckable(True)
        self.keyboard_debug_button.setChecked(False)
        self.keyboard_debug_button.clicked.connect(self.toggle_keyboard_debug)
        layout.addWidget(self.keyboard_debug_button)
        self.setLayout(layout)
        self.max_lines = 100
        self.log_file_path = os.path.expanduser("~/.testerfy/debug_log_tab.log")
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        self.log_signal.connect(self.log_area_prepend)

    def log_area_prepend(self, text):
        try:
            # Beautify log line with icons and color
            icon = ''
            color = None
            lower = text.lower()
            add_hr = False
            if 'dislike action completed' in lower:
                icon = '💩'
                add_hr = True
            elif 'like action completed' in lower:
                icon = '❤️'
                add_hr = True
            elif 'successfully removed from current playlist' in lower or 'successfully added to playlist' in lower:
                icon = '✅'
                add_hr = True
            elif 'action completed' in lower:
                icon = '✅'
                add_hr = True
            elif 'undo' in lower:
                icon = '↩️'
                add_hr = True
            elif 'skipped to next song' in lower or 'skip' in lower:
                icon = '⏭️'
            elif 'error' in lower or 'failed' in lower or 'cannot' in lower:
                icon = '❌'
                color = '#ff4444'
                add_hr = True
            elif 'authenticated as' in lower or 'access token obtained' in lower or 'authentication successful' in lower:
                icon = '✅'
                color = '#1DB954'
                add_hr = True
            elif 'warning' in lower:
                icon = '⚠️'
                color = '#ffaa00'
            elif 'info' in lower:
                icon = 'ℹ️'
                color = '#888888'
            # Compose HTML line
            html_line = f"<span>{icon} </span>" if icon else ""
            safe_text = text.replace('<', '&lt;').replace('>', '&gt;')
            if color:
                html_line += f'<span style="color:{color}">{safe_text}</span>'
            else:
                html_line += safe_text
            if add_hr:
                html_line += '<br><hr style="border:1px solid #444;margin:4px 0;">'
            else:
                html_line += '<br>'
            
            # Get current HTML content
            current_html = self.log_area.toHtml()
            
            # Extract body content
            if '<body>' in current_html:
                body_start = current_html.find('<body>') + 6
                body_end = current_html.find('</body>')
                if body_end == -1:
                    body_end = len(current_html)
                body_content = current_html[body_start:body_end]
            else:
                body_content = current_html
            
            # Split into lines and count actual log entries (not HTML tags)
            lines = body_content.split('<br>')
            # Filter out empty lines and HTML-only lines
            log_lines = [line for line in lines if line.strip() and not line.startswith('<')]
            
            # Add new line at the beginning
            new_lines = [html_line] + lines
            
            # Limit to max_lines by removing oldest lines from the end
            if len(new_lines) > self.max_lines:
                new_lines = new_lines[:self.max_lines]
            
            # Reconstruct HTML
            new_html = '<br>'.join(new_lines)
            
            # Set the new HTML content
            self.log_area.setHtml(new_html)
            
            # Move cursor to top to show newest logs
            cursor = self.log_area.textCursor()
            cursor.movePosition(cursor.Start)
            self.log_area.setTextCursor(cursor)
            
        except Exception as e:
            # Fallback: append plain text and log the error
            self.log_area.append(text)
            try:
                with open(self.log_file_path, 'a') as f:
                    f.write(f"[LOG_AREA_PREPEND ERROR] {e}\n{text}\n")
            except Exception:
                pass
        
        # Always write to persistent log file (plain text)
        try:
            with open(self.log_file_path, 'a') as f:
                f.write(text + '\n')
        except Exception:
            pass

    def log_area_append(self, text):
        # For compatibility: append to bottom (legacy)
        self.log_area.append(text)
        # Write to persistent log file
        try:
            with open(self.log_file_path, 'a') as f:
                f.write(text + '\n')
        except Exception:
            pass

    def log(self, text):
        # Always emit signal so log_area_prepend runs in main thread
        self.log_signal.emit(text)

    def toggle_keyboard_debug(self):
        if self.main_window:
            enabled = self.keyboard_debug_button.isChecked()
            self.main_window.keyboard_debug_enabled = enabled
            if enabled:
                self.keyboard_debug_button.setText("Disable Keyboard Debug Logging")
                self.log("Keyboard debug logging ENABLED.")
            else:
                self.keyboard_debug_button.setText("Enable Keyboard Debug Logging")
                self.log("Keyboard debug logging DISABLED.")

# Utility for key normalization
KEY_ALIASES = {
    'cmd': 'super',
    'command': 'super',
    'win': 'super',
    'windows': 'super',
    'super': 'super',
}

def normalize_key(key):
    k = key.lower()
    return KEY_ALIASES.get(k, k)

def generate_tray_icon_png(path):
    """Generate a simple PNG icon: green letter 'T' on transparent background."""
    try:
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(22)
        painter.setFont(font)
        painter.setPen(QColor('#1DB954'))  # Spotify green
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, 'T')
        painter.end()
        pixmap.save(path, 'PNG')
    except Exception as e:
        logger.error(f"Failed to generate tray icon PNG: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        self.keyboard_debug_enabled = False  # Defensive: set before anything else
        super().__init__()
        self.last_action = None  # Track last like/dislike action (must be set before any method uses it)
        self.setWindowTitle("Testerfy")
        # Set window icon to green T icon
        icon_path = os.path.join(os.path.expanduser('~'), '.testerfy_tray_icon.png')
        if not os.path.exists(icon_path):
            generate_tray_icon_png(icon_path)
        self.setWindowIcon(QIcon(icon_path))
        self.resize(600, 500)  # Increased size for better playlist display
        self.tabs = QTabWidget()
        self._font_size = 11  # Default font size for zoom
        
        # Create tabs with main window reference
        self.settings_tab = SettingsTab(self)
        self.playlists_tab = PlaylistsTab(self)
        self.keyboard_shortcuts_tab = KeyboardShortcutsTab(self)
        self.debug_log_tab = DebugLogTab(self)
        
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.playlists_tab, "Playlists")
        self.tabs.addTab(self.keyboard_shortcuts_tab, "Keyboard Shortcuts")
        self.tabs.addTab(self.debug_log_tab, "Debug/Log")
        
        self.setCentralWidget(self.tabs)
        self.apply_dark_theme()  # Start with authentication warning
        self.tray_icon = None
        self.is_hidden = False
        self.spotify_client = None
        
        # Load settings
        self.settings = load_settings()
        
        # Create tray icon after settings are loaded
        self.create_tray_icon()
        
        # Global hotkey listener
        self.hotkey_listener = None
        self.pressed_keys = set()
        self.setup_global_hotkeys()
        
        # Timer for updating now playing info in tray
        self.now_playing_timer = QTimer()
        self.now_playing_timer.timeout.connect(self.update_now_playing_tooltip)
        self.now_playing_timer.timeout.connect(self.update_tray_menu)
        self.now_playing_timer.start(5000)  # Update every 5 seconds
        
        # --- Action cooldown state ---
        self._action_cooldown = False
        self._last_action_time = 0
        self._action_cooldown_duration = 2.0  # 2 second cooldown between actions
        
        # --- Hotkey edge-trigger state ---
        self._shortcut_prev_state = {"like": False, "dislike": False}
        
        # Add keyboard state reset timer
        self.keyboard_reset_timer = QTimer()
        self.keyboard_reset_timer.timeout.connect(self.reset_keyboard_state)
        self.keyboard_reset_timer.start(30000)  # Reset every 30 seconds to prevent stuck keys

    def set_spotify_client(self, spotify_client):
        """Set the Spotify client and load playlists"""
        self.spotify_client = spotify_client
        if self.spotify_client:
            # Get user id
            try:
                user = self.spotify_client.current_user()
                user_id = user.get('id')
                self.user_id = user_id
                user_settings = load_user_settings(user_id)
                # Load playlists and shortcuts for this user
                self.playlists_tab.set_user_settings(user_settings.get('playlists', []))
                self.keyboard_shortcuts_tab.set_user_settings(user_settings.get('shortcuts', {}))
                # Ensure main window settings are updated for hotkeys
                if 'shortcuts' in user_settings:
                    self.settings.update(user_settings['shortcuts'])
            except Exception as e:
                logger.error(f"Could not load user-specific settings: {e}")
            self.playlists_tab.load_playlists(self.spotify_client)
            self.remove_authentication_warning()
        else:
            self.add_authentication_warning()
            self.user_id = None

    def update_shortcuts(self, new_settings):
        """Update shortcuts with new settings"""
        self.settings = new_settings
        self.debug_log_tab.log(f"Shortcuts updated in main window")
        # Update the tray menu to reflect new shortcuts
        self.update_tray_menu()
        # Re-setup global hotkeys
        self.setup_global_hotkeys()

    def setup_global_hotkeys(self):
        # Defensive: ensure attribute exists
        if not hasattr(self, 'keyboard_debug_enabled'):
            self.keyboard_debug_enabled = False
        
        # CRITICAL FIX: Stop existing listener before creating new one
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
                self.hotkey_listener = None
            except Exception as e:
                self.debug_log_tab.log(f"Error stopping old hotkey listener: {e}")
        
        # Clear pressed keys to prevent stuck keys
        self.pressed_keys.clear()
        self._shortcut_prev_state = {"like": False, "dislike": False}
        
        try:
            def on_press(key):
                try:
                    key_name = key_to_name(key)
                    if key_name:
                        self.pressed_keys.add(key_name)
                        # --- Handle zoom in/out (Ctrl+Shift+= or Ctrl+Shift+-) ---
                        if self._is_zoom_in_shortcut():
                            self.set_font_size(self._font_size + 1)
                            self.debug_log_tab.log("Zoomed in (font size increased)")
                            return
                        elif self._is_zoom_out_shortcut():
                            self.set_font_size(self._font_size - 1)
                            self.debug_log_tab.log("Zoomed out (font size decreased)")
                            return
                        if self.keyboard_debug_enabled:
                            self.debug_log_tab.log(f"Raw key event (press): {repr(key)}")
                            self.debug_log_tab.log(f"Key pressed: {key_name}, Current keys: {self.pressed_keys}")
                            self.debug_log_tab.log(f"Checking shortcuts - Pressed: {self.pressed_keys}, Like: {self.settings.get('like', DEFAULT_SHORTCUTS['like'])}, Dislike: {self.settings.get('dislike', DEFAULT_SHORTCUTS['dislike'])}")
                        self.check_shortcuts()
                    elif self.keyboard_debug_enabled:
                        # Log ignored keys for debugging
                        self.debug_log_tab.log(f"Ignored key press: {repr(key)}")
                except AttributeError as e:
                    if self.keyboard_debug_enabled:
                        self.debug_log_tab.log(f"AttributeError in on_press: {e}")
                except Exception as e:
                    if self.keyboard_debug_enabled:
                        self.debug_log_tab.log(f"Unexpected error in on_press: {e}")
            
            def on_release(key):
                try:
                    key_name = key_to_name(key)
                    if key_name:
                        self.pressed_keys.discard(key_name)
                    # Reset edge trigger state on any key release
                    self._shortcut_prev_state["like"] = False
                    self._shortcut_prev_state["dislike"] = False
                except AttributeError as e:
                    if self.keyboard_debug_enabled:
                        self.debug_log_tab.log(f"AttributeError in on_release: {e}")
                except Exception as e:
                    if self.keyboard_debug_enabled:
                        self.debug_log_tab.log(f"Unexpected error in on_release: {e}")
            
            # Create new listener with proper error handling
            self.hotkey_listener = keyboard.Listener(
                on_press=on_press, 
                on_release=on_release,
                suppress=False  # Don't suppress other applications
            )
            self.hotkey_listener.start()
            
            if self.keyboard_debug_enabled:
                self.debug_log_tab.log("Global hotkeys enabled (new listener created)")
                
        except Exception as e:
            self.debug_log_tab.log(f"Error setting up hotkeys: {e}")
            # Ensure listener is None if setup fails
            self.hotkey_listener = None

    def _is_zoom_in_shortcut(self):
        # Ctrl+Shift+= or Ctrl+Shift++
        return 'ctrl' in self.pressed_keys and 'shift' in self.pressed_keys and ('=' in self.pressed_keys or '+' in self.pressed_keys)

    def _is_zoom_out_shortcut(self):
        # Ctrl+Shift+-
        return 'ctrl' in self.pressed_keys and 'shift' in self.pressed_keys and ('-' in self.pressed_keys or '_' in self.pressed_keys)

    def check_shortcuts(self):
        """Edge-triggered: Only trigger action on transition from not-matched to matched."""
        try:
            like_keys = parse_shortcut(self.settings.get("like", DEFAULT_SHORTCUTS["like"]))
            dislike_keys = parse_shortcut(self.settings.get("dislike", DEFAULT_SHORTCUTS["dislike"]))
            if self.keyboard_debug_enabled:
                self.debug_log_tab.log(f"Checking shortcuts - Pressed: {self.pressed_keys}, Like: {like_keys}, Dislike: {dislike_keys}")
            # Like shortcut edge
            like_now = is_shortcut_match(self.pressed_keys, like_keys)
            if like_now and not self._shortcut_prev_state["like"]:
                self.debug_log_tab.log("Like shortcut matched (edge)!")
                self.like_current_song()
            self._shortcut_prev_state["like"] = like_now
            # Dislike shortcut edge
            dislike_now = is_shortcut_match(self.pressed_keys, dislike_keys)
            if dislike_now and not self._shortcut_prev_state["dislike"]:
                self.debug_log_tab.log("Dislike shortcut matched (edge)!")
                self.dislike_current_song()
            self._shortcut_prev_state["dislike"] = dislike_now
        except Exception as e:
            if self.keyboard_debug_enabled:
                self.debug_log_tab.log(f"Error checking shortcuts: {e}")

    def check_device_status(self):
        """Check if there's an active Spotify device and provide user feedback"""
        if not self.spotify_client:
            return False, "Not authenticated with Spotify"
            
        try:
            devices = self.spotify_client.devices()
            active_device = None
            
            for device in devices['devices']:
                if device['is_active']:
                    active_device = device
                    break
            
            if active_device:
                return True, f"Active device: {active_device['name']} ({active_device['type']})"
            else:
                # Check if there are any available devices
                if devices['devices']:
                    device_list = ", ".join([f"{d['name']} ({d['type']})" for d in devices['devices']])
                    return False, f"No active device. Available devices: {device_list}"
                else:
                    return False, "No devices found. Make sure Spotify is running on a device."
                    
        except Exception as e:
            return False, f"Error checking devices: {e}"

    def like_current_song(self):
        """Like the currently playing song - add to selected playlists, remove from current playlist, and skip"""
        # Check action cooldown
        current_time = time.time()
        if self._action_cooldown and (current_time - self._last_action_time) < self._action_cooldown_duration:
            self.debug_log_tab.log(f"Action cooldown active, ignoring like request (cooldown: {self._action_cooldown_duration}s)")
            return
        
        if not self.spotify_client:
            self.debug_log_tab.log("Not authenticated with Spotify")
            return
            
        try:
            # Get current playback
            current = self.spotify_client.current_playback()
            if not current or not current['is_playing']:
                self.debug_log_tab.log("No song currently playing")
                return
                
            track_id = current['item']['id']
            track_name = current['item']['name']
            artist_name = current['item']['artists'][0]['name']
            
            # 1. Add to selected playlists from the Playlists tab
            selected_playlist_ids = self.playlists_tab.get_selected_playlist_ids()
            if selected_playlist_ids:
                for playlist_id in selected_playlist_ids:
                    try:
                        self.spotify_client.playlist_add_items(playlist_id, [track_id])
                        self.debug_log_tab.log(f"Added to playlist {playlist_id}")
                    except Exception as e:
                        self.debug_log_tab.log(f"Error adding to playlist {playlist_id}: {e}")
            else:
                self.debug_log_tab.log("No playlists selected in Playlists tab")
            
            # 2. Remove from current playlist if playing from a playlist
            context_type = current.get('context', {}).get('type')
            self.debug_log_tab.log(f"Current playback context type: {context_type}")
            if context_type == 'playlist':
                context_uri = current.get('context', {}).get('uri', '')
                self.debug_log_tab.log(f"Context URI: {context_uri}")
                
                # Extract playlist ID from URI (format: spotify:playlist:playlist_id)
                if 'spotify:playlist:' in context_uri:
                    playlist_id = context_uri.split('spotify:playlist:')[-1]
                    self.debug_log_tab.log(f"Attempting to remove from current playlist: {playlist_id}")
                    
                    # Try multiple methods to remove the track
                    removal_success = False
                    
                    # Method 1: Remove all occurrences
                    try:
                        self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
                        self.debug_log_tab.log(f"Successfully removed from current playlist {playlist_id} (method 1)")
                        removal_success = True
                    except Exception as e:
                        self.debug_log_tab.log(f"Method 1 failed: {str(e)}")
                    
                    # Method 2: Try with positions if method 1 failed
                    if not removal_success:
                        try:
                            # Get current position in playlist
                            current_position = current.get('item', {}).get('position', None)
                            if current_position is not None:
                                self.spotify_client.playlist_remove_specific_occurrences_of_items(playlist_id, [{'uri': f'spotify:track:{track_id}', 'positions': [current_position]}])
                                self.debug_log_tab.log(f"Successfully removed from current playlist {playlist_id} (method 2)")
                                removal_success = True
                            else:
                                self.debug_log_tab.log("Could not determine track position in playlist")
                        except Exception as e:
                            self.debug_log_tab.log(f"Method 2 failed: {str(e)}")
                    
                    # Method 3: Try with track URI if other methods failed
                    if not removal_success:
                        try:
                            track_uri = f"spotify:track:{track_id}"
                            self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                            self.debug_log_tab.log(f"Successfully removed from current playlist {playlist_id} (method 3)")
                            removal_success = True
                        except Exception as e:
                            self.debug_log_tab.log(f"Method 3 failed: {str(e)}")
                    
                    if not removal_success:
                        self.debug_log_tab.log(f"All removal methods failed for playlist {playlist_id}")
                else:
                    self.debug_log_tab.log(f"Could not parse playlist ID from URI: {context_uri}")
            else:
                self.debug_log_tab.log("Not playing from a playlist - skipping removal")
            
            # 3. Skip to next song with better device management
            try:
                # Check if there's an active device
                devices = self.spotify_client.devices()
                active_device = None
                
                # Find an active device
                for device in devices['devices']:
                    if device['is_active']:
                        active_device = device['id']
                        break
                
                if active_device:
                    # Use the active device to skip
                    self.spotify_client.next_track(device_id=active_device)
                    self.debug_log_tab.log("Skipped to next song")
                else:
                    # Try without device_id (fallback)
                    self.spotify_client.next_track()
                    self.debug_log_tab.log("Skipped to next song (fallback)")
                    
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "Restriction violated" in error_msg:
                    self.debug_log_tab.log("Cannot skip track: No active device or Premium account required")
                elif "404" in error_msg:
                    self.debug_log_tab.log("Cannot skip track: No active device found")
                else:
                    self.debug_log_tab.log(f"Error skipping to next song: {error_msg}")
            
            self.debug_log_tab.log(f"Like action completed for: {track_name} by {artist_name}")
            
            # Set action cooldown
            self._action_cooldown = True
            self._last_action_time = current_time
            
            # Track last action for undo
            self.last_action = {
                'type': 'like',
                'track_id': track_id,
                'track_name': track_name,
                'artist_name': artist_name,
                'playlists': list(selected_playlist_ids)
            }
            self.update_tray_menu()
            
        except Exception as e:
            self.debug_log_tab.log(f"Error in like action: {e}")

    def dislike_current_song(self):
        """Dislike the currently playing song - remove from current playlist and skip"""
        # Check action cooldown
        current_time = time.time()
        if self._action_cooldown and (current_time - self._last_action_time) < self._action_cooldown_duration:
            self.debug_log_tab.log(f"Action cooldown active, ignoring dislike request (cooldown: {self._action_cooldown_duration}s)")
            return
        
        if not self.spotify_client:
            self.debug_log_tab.log("Not authenticated with Spotify")
            return
            
        try:
            # Get current playback
            current = self.spotify_client.current_playback()
            if not current or not current['is_playing']:
                self.debug_log_tab.log("No song currently playing")
                return
                
            track_id = current['item']['id']
            track_name = current['item']['name']
            artist_name = current['item']['artists'][0]['name']
            
            # 1. Remove from current playlist if playing from a playlist
            context_type = current.get('context', {}).get('type')
            self.debug_log_tab.log(f"Current playback context type: {context_type}")
            if context_type == 'playlist':
                context_uri = current.get('context', {}).get('uri', '')
                self.debug_log_tab.log(f"Context URI: {context_uri}")
                
                # Extract playlist ID from URI (format: spotify:playlist:playlist_id)
                if 'spotify:playlist:' in context_uri:
                    playlist_id = context_uri.split('spotify:playlist:')[-1]
                    self.debug_log_tab.log(f"Attempting to remove from current playlist: {playlist_id}")
                    
                    # Try multiple methods to remove the track
                    removal_success = False
                    
                    # Method 1: Remove all occurrences
                    try:
                        self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
                        self.debug_log_tab.log(f"Successfully removed from current playlist {playlist_id} (method 1)")
                        removal_success = True
                    except Exception as e:
                        self.debug_log_tab.log(f"Method 1 failed: {str(e)}")
                    
                    # Method 2: Try with positions if method 1 failed
                    if not removal_success:
                        try:
                            # Get current position in playlist
                            current_position = current.get('item', {}).get('position', None)
                            if current_position is not None:
                                self.spotify_client.playlist_remove_specific_occurrences_of_items(playlist_id, [{'uri': f'spotify:track:{track_id}', 'positions': [current_position]}])
                                self.debug_log_tab.log(f"Successfully removed from current playlist {playlist_id} (method 2)")
                                removal_success = True
                            else:
                                self.debug_log_tab.log("Could not determine track position in playlist")
                        except Exception as e:
                            self.debug_log_tab.log(f"Method 2 failed: {str(e)}")
                    
                    # Method 3: Try with track URI if other methods failed
                    if not removal_success:
                        try:
                            track_uri = f"spotify:track:{track_id}"
                            self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                            self.debug_log_tab.log(f"Successfully removed from current playlist {playlist_id} (method 3)")
                            removal_success = True
                        except Exception as e:
                            self.debug_log_tab.log(f"Method 3 failed: {str(e)}")
                    
                    if not removal_success:
                        self.debug_log_tab.log(f"All removal methods failed for playlist {playlist_id}")
                else:
                    self.debug_log_tab.log(f"Could not parse playlist ID from URI: {context_uri}")
            else:
                self.debug_log_tab.log("Not playing from a playlist, skipping playlist removal")
            
            # 2. Skip to next song with better device management
            try:
                # Check if there's an active device
                devices = self.spotify_client.devices()
                active_device = None
                
                # Find an active device
                for device in devices['devices']:
                    if device['is_active']:
                        active_device = device['id']
                        break
                
                if active_device:
                    # Use the active device to skip
                    self.spotify_client.next_track(device_id=active_device)
                    self.debug_log_tab.log("Skipped to next song")
                else:
                    # Try without device_id (fallback)
                    self.spotify_client.next_track()
                    self.debug_log_tab.log("Skipped to next song (fallback)")
                    
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "Restriction violated" in error_msg:
                    self.debug_log_tab.log("Cannot skip track: No active device or Premium account required")
                elif "404" in error_msg:
                    self.debug_log_tab.log("Cannot skip track: No active device found")
                else:
                    self.debug_log_tab.log(f"Error skipping to next song: {error_msg}")
            
            self.debug_log_tab.log(f"Dislike action completed for: {track_name} by {artist_name}")
            
            # Set action cooldown
            self._action_cooldown = True
            self._last_action_time = current_time
            
            # Track last action for undo
            self.last_action = {
                'type': 'dislike',
                'track_id': track_id,
                'track_name': track_name,
                'artist_name': artist_name,
                'playlists': []  # Not tracked for dislike
            }
            self.update_tray_menu()
            
        except Exception as e:
            self.debug_log_tab.log(f"Error in dislike action: {e}")

    def update_now_playing_tooltip(self):
        """Update the tray icon tooltip with now playing info"""
        if not self.spotify_client or not self.tray_icon:
            return
            
        try:
            current = self.spotify_client.current_playback()
            if current and current['is_playing']:
                track_name = current['item']['name']
                artist_name = current['item']['artists'][0]['name']
                album_name = current['item']['album']['name']
                tooltip = f"Testerfy\nNow Playing: {track_name}\nArtist: {artist_name}\nAlbum: {album_name}"
                self.tray_icon.setToolTip(tooltip)
            else:
                self.tray_icon.setToolTip("Testerfy\nNo song playing")
        except Exception:
            # Silently fail for tooltip updates
            pass

    def apply_dark_theme(self):
        """Apply dark theme with Spotify green accents"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(Qt.GlobalColor.white))
        palette.setColor(QPalette.Base, QColor(20, 20, 20))
        palette.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
        palette.setColor(QPalette.ToolTipBase, QColor(Qt.GlobalColor.white))
        palette.setColor(QPalette.ToolTipText, QColor(Qt.GlobalColor.white))
        palette.setColor(QPalette.Text, QColor(Qt.GlobalColor.white))
        palette.setColor(QPalette.Button, QColor(40, 40, 40))
        palette.setColor(QPalette.ButtonText, QColor(Qt.GlobalColor.white))
        palette.setColor(QPalette.BrightText, QColor(Qt.GlobalColor.red))
        palette.setColor(QPalette.Link, QColor(42, 42, 42))
        palette.setColor(QPalette.Highlight, QColor(42, 42, 42))
        palette.setColor(QPalette.HighlightedText, QColor(Qt.GlobalColor.white))
        self.setPalette(palette)
        
        # Apply stylesheet with Spotify green accents
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #1e1e1e;
                color: white;
            }}
            QTabWidget::pane {{
                border: 1px solid {SPOTIFY_GREEN};
                background-color: #1e1e1e;
            }}
            QTabBar::tab {{
                background-color: #2d2d2d;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {SPOTIFY_GREEN};
                color: black;
            }}
            QTabBar::tab:hover {{
                background-color: #3d3d3d;
            }}
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1ed760;
            }}
            QPushButton:pressed {{
                background-color: #1aa34a;
            }}
            QLineEdit {{
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #555;
                padding: 6px;
                border-radius: 4px;
            }}
            QLineEdit:focus {{
                border: 2px solid {SPOTIFY_GREEN};
            }}
            QTextEdit {{
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
            }}
            QScrollBar:vertical {{
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {SPOTIFY_GREEN};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #1ed760;
            }}
            QGroupBox {{
                color: white;
                font-weight: bold;
                border: 2px solid {SPOTIFY_GREEN};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QCheckBox {{
                color: white;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid #555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }}
            QCheckBox::indicator:checked {{
                background-color: {SPOTIFY_GREEN};
                border: 2px solid {SPOTIFY_GREEN};
            }}
            QCheckBox::indicator:checked::after {{
                content: "✓";
                color: black;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        
        # Add red authentication warning overlay
        self.add_authentication_warning()
    
    def add_authentication_warning(self):
        """Add red warning overlay when not authenticated"""
        if hasattr(self, 'auth_warning'):
            self.auth_warning.deleteLater()
        
        self.auth_warning = QLabel("⚠️ NOT AUTHENTICATED - Enter Spotify credentials in Settings tab", self)
        self.auth_warning.setStyleSheet("""
            QLabel {
                background-color: #ff4444;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #ff0000;
            }
        """)
        self.auth_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_warning.setGeometry(10, 10, self.width() - 20, 40)
        self.auth_warning.show()
        self.auth_warning.raise_()
    
    def remove_authentication_warning(self):
        """Remove the red warning overlay when authenticated"""
        if hasattr(self, 'auth_warning'):
            self.auth_warning.hide()
            self.auth_warning.deleteLater()
            delattr(self, 'auth_warning')

    def create_tray_icon(self):
        # Use PNG icon for tray, with error handling
        icon_path = os.path.join(os.path.expanduser('~'), '.testerfy_tray_icon.png')
        if not os.path.exists(icon_path):
            generate_tray_icon_png(icon_path)
        try:
            icon = QIcon(icon_path)
            if icon.isNull():
                raise ValueError("Loaded tray icon is null")
        except Exception as e:
            logger.error(f"Tray icon PNG load failed: {e}, falling back to solid color icon.")
            try:
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor('#1DB954'))
                icon = QIcon(pixmap)
            except Exception as e2:
                logger.error(f"Fallback tray icon creation failed: {e2}")
                icon = QIcon()
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Testerfy")
        # Restore full context menu
        menu = QMenu()
        # --- Remove now playing section ---
        # Like action with keyboard shortcut
        like_shortcut = self.settings.get("like", DEFAULT_SHORTCUTS["like"])
        self.like_action = QAction(f"❤️ Like Song ({like_shortcut})", self)
        self.like_action.triggered.connect(self.like_current_song)
        menu.addAction(self.like_action)
        # Dislike action with keyboard shortcut
        dislike_shortcut = self.settings.get("dislike", DEFAULT_SHORTCUTS["dislike"])
        self.dislike_action = QAction(f"💩 Dislike Song ({dislike_shortcut})", self)
        self.dislike_action.triggered.connect(self.dislike_current_song)
        menu.addAction(self.dislike_action)
        # Undo last action
        self.undo_action = QAction("↩️ Undo Last Action", self)
        self.undo_action.triggered.connect(self.undo_last_action)
        self.undo_action.setEnabled(self.last_action is not None)
        menu.addAction(self.undo_action)
        menu.addSeparator()
        # Show/Hide action
        show_action = QAction("Show/Hide Window", self)
        show_action.triggered.connect(self.toggle_window)
        menu.addAction(show_action)
        # Quit action
        quit_action = QAction("Quit Testerfy", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        # Update the menu immediately
        self.update_tray_menu()

    def update_tray_menu(self):
        """Update the tray context menu with current song information"""
        if not self.tray_icon or not self.spotify_client:
            return
        try:
            current = self.spotify_client.current_playback()
            if current and current['is_playing']:
                # Enable like/dislike actions
                self.like_action.setEnabled(True)
                self.dislike_action.setEnabled(True)
                # Update tooltip
                track_name = current['item']['name']
                artist_name = current['item']['artists'][0]['name']
                album_name = current['item']['album']['name']
                tooltip = f"Testerfy\nNow Playing: {track_name}\nArtist: {artist_name}\nAlbum: {album_name}"
                self.tray_icon.setToolTip(tooltip)
                if hasattr(self, 'undo_action'):
                    self.undo_action.setEnabled(self.last_action is not None)
            else:
                self.like_action.setEnabled(False)
                self.dislike_action.setEnabled(False)
                self.tray_icon.setToolTip("Testerfy\nNo song playing")
        except Exception as e:
            self.like_action.setEnabled(False)
            self.dislike_action.setEnabled(False)
            self.tray_icon.setToolTip("Testerfy\nError getting song info")

    def toggle_window(self):
        if self.isHidden() or self.is_hidden:
            self.showNormal()
            self.raise_()
            self.activateWindow()
            self.is_hidden = False
        else:
            self.hide()
            self.is_hidden = True

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window()

    def quit_app(self):
        # Proper cleanup of resources
        try:
            if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
                self.hotkey_listener.stop()
                self.hotkey_listener = None
                self.debug_log_tab.log("Hotkey listener stopped")
        except Exception as e:
            self.debug_log_tab.log(f"Error stopping hotkey listener: {e}")
        
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.hide()
                self.tray_icon = None
        except Exception as e:
            self.debug_log_tab.log(f"Error hiding tray icon: {e}")
        
        try:
            # Clean up PID file
            pid_file = os.path.expanduser("~/.testerfy/testerfy.pid")
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception as e:
            self.debug_log_tab.log(f"Error removing PID file: {e}")
        
        self.debug_log_tab.log("Testerfy shutting down...")
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.is_hidden = True

    def undo_last_action(self):
        if not self.last_action or not self.spotify_client:
            return
        action = self.last_action
        try:
            if action['type'] == 'like':
                # Remove from all playlists added to
                for playlist_id in action['playlists']:
                    try:
                        self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [action['track_id']])
                        self.debug_log_tab.log(f"Undo: Removed {action['track_name']} from playlist {playlist_id}")
                    except Exception as e:
                        self.debug_log_tab.log(f"Undo failed for playlist {playlist_id}: {e}")
                self.debug_log_tab.log(f"Undo: Like action undone for {action['track_name']} by {action['artist_name']}")
            elif action['type'] == 'dislike':
                # Can't reliably re-add to playlist, just log
                self.debug_log_tab.log("Undo: Dislike action cannot be fully undone (manual re-add may be needed)")
            self.last_action = None
            self.update_tray_menu()
        except Exception as e:
            self.debug_log_tab.log(f"Undo failed: {e}")

    def set_font_size(self, size):
        self._font_size = max(7, min(size, 32))
        font = QFont("Monospace", self._font_size)
        # Update all QTextEdit and QLabel widgets in tabs
        for tab in [self.settings_tab, self.playlists_tab, self.keyboard_shortcuts_tab, self.debug_log_tab]:
            self._set_widget_font(tab, font)
        self.update()

    def _set_widget_font(self, widget, font):
        # Recursively set font for QTextEdit and QLabel
        if isinstance(widget, (QTextEdit, QLabel)):
            widget.setFont(font)
        if hasattr(widget, 'children'):
            for child in widget.children():
                if isinstance(child, QWidget):
                    self._set_widget_font(child, font)

    def reset_keyboard_state(self):
        """Reset keyboard state to prevent stuck keys and memory issues"""
        try:
            # Clear pressed keys
            if hasattr(self, 'pressed_keys'):
                self.pressed_keys.clear()
            
            # Reset edge trigger state
            if hasattr(self, '_shortcut_prev_state'):
                self._shortcut_prev_state = {"like": False, "dislike": False}
            
            # Log reset for debugging
            if self.keyboard_debug_enabled:
                self.debug_log_tab.log("Keyboard state reset (preventive maintenance)")
                
        except Exception as e:
            if self.keyboard_debug_enabled:
                self.debug_log_tab.log(f"Error in keyboard state reset: {e}")

def key_to_name(key):
    # Robust mapping of pynput key event to a unique, human-readable name
    try:
        # Handle special keys with virtual key codes
        if hasattr(key, 'vk') and hasattr(key, 'char') and key.char is None:
            # Function keys (F1-F12)
            if 112 <= key.vk <= 123:
                return f'f{key.vk - 111}'
            # Numpad keys
            if 96 <= key.vk <= 105:
                return str(key.vk - 96)
            # Other special keys
            vk_map = {
                8: 'backspace', 9: 'tab', 13: 'enter', 16: 'shift', 17: 'ctrl', 18: 'alt',
                20: 'capslock', 27: 'esc', 32: 'space', 33: 'pageup', 34: 'pagedown', 35: 'end',
                36: 'home', 37: 'left', 38: 'up', 39: 'right', 40: 'down', 45: 'insert', 46: 'delete',
                91: 'super', 92: 'super', 93: 'menu', 144: 'numlock', 145: 'scrolllock',
                186: ';', 187: '=', 188: ',', 189: '-', 190: '.', 191: '/', 192: '`',
                219: '[', 220: '\\', 221: ']', 222: "'"
            }
            if key.vk in vk_map:
                return vk_map[key.vk]
        
        # Handle Key objects (pynput.keyboard.Key)
        if hasattr(key, 'name'):
            key_name = key.name.lower()
            # Normalize modifier keys
            if key_name in ['ctrl_l', 'ctrl_r', 'ctrl', 'shift_l', 'shift_r', 'shift', 'alt_l', 'alt_r', 'alt', 'super', 'cmd', 'cmd_l', 'cmd_r']:
                return normalize_key(key_name.replace('_l', '').replace('_r', ''))
            # Handle function keys
            if key_name.startswith('f') and key_name[1:].isdigit():
                return key_name
            # Handle other special keys
            special_keys = {
                'space': 'space', 'tab': 'tab', 'enter': 'enter', 'backspace': 'backspace',
                'delete': 'delete', 'insert': 'insert', 'home': 'home', 'end': 'end',
                'page_up': 'pageup', 'page_down': 'pagedown', 'up': 'up', 'down': 'down',
                'left': 'left', 'right': 'right', 'esc': 'esc', 'escape': 'esc'
            }
            if key_name in special_keys:
                return special_keys[key_name]
            return key_name
        
        # Handle alphanumeric and symbol keys (KeyCode objects)
        if hasattr(key, 'char') and key.char:
            c = key.char.lower()
            # Only return valid characters that we actually want to track
            if c.isalnum() or c in SHIFTED_SYMBOL_MAP or c in SHIFTED_SYMBOL_MAP.values():
                return c
        
        # Fallback: convert to string and clean up
        s = str(key).lower().replace('key.', '')
        # Filter out unwanted characters that might be generated by function keys
        if s in ['_', ':', '(', ')', ';', '"', '<', '>', '?', '{', '}', '|', '\\', '`', '~']:
            return None  # Ignore these characters
        if s in ['ctrl_l', 'ctrl_r', 'ctrl', 'shift_l', 'shift_r', 'shift', 'alt_l', 'alt_r', 'alt', 'super', 'cmd', 'cmd_l', 'cmd_r']:
            return normalize_key(s.replace('_l', '').replace('_r', ''))
        if s.startswith('f') and s[1:].isdigit():
            return s
        return s
    except Exception:
        return None  # Return None for any unhandled cases

def main():
    # Detach from terminal and run in background
    try:
        # Fork the process to detach from terminal
        pid = os.fork()
        if pid > 0:
            # Parent process - exit immediately
            print("Testerfy started in background. Check system tray for the application.")
            sys.exit(0)
        else:
            # Child process - continue running
            # Create new session to detach from terminal
            os.setsid()
            
            # Redirect standard file descriptors to /dev/null
            sys.stdout.flush()
            sys.stderr.flush()
            
            with open(os.devnull, 'r') as dev_null:
                os.dup2(dev_null.fileno(), sys.stdin.fileno())
            with open(os.devnull, 'a+') as dev_null:
                os.dup2(dev_null.fileno(), sys.stdout.fileno())
            with open(os.devnull, 'a+') as dev_null:
                os.dup2(dev_null.fileno(), sys.stderr.fileno())
            
            # Create PID file for process management
            pid_file = os.path.expanduser("~/.testerfy/testerfy.pid")
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            # Start the Qt application
            app = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            
            # Run the application
            sys.exit(app.exec_())
            
    except Exception as e:
        logger.error(f"Failed to start Testerfy in background: {e}")
        # Fallback to normal execution if daemonization fails
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())

if __name__ == "__main__":
    main() 