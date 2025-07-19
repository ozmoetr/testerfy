#!/usr/bin/env python3
import time
startup_times = []
def log_time(label):
    t = time.perf_counter()
    startup_times.append((label, t))
    try:
        print(f"[STARTUP TIMING] {label}: {t:.4f}s")
    except Exception:
        pass
print('Testerfy main_macos.py started')
import logging
import os
# macOS-specific logging path
log_dir = os.path.expanduser("~/.testerfy")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "testerfy_macos.log")
logging.basicConfig(filename=log_file, level=logging.INFO)
logging.info('Testerfy main_macos.py started (logging)')
import sys
import json
import os
import secrets
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, QListWidget, QListWidgetItem,
    QSystemTrayIcon, QMenu, QAction, QScrollArea, QMessageBox, QGroupBox, QFrame, QDialog, QDialogButtonBox
)
log_time('import PyQt5.QtWidgets')
from PyQt5.QtGui import QPalette, QColor, QIcon, QPixmap, QKeySequence, QFont, QPen, QPainter
log_time('import PyQt5.QtGui')
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex, QWaitCondition, QEvent
log_time('import PyQt5.QtCore')
import threading
import webbrowser

import time
from flask import Flask, request
import base64
import pathlib
import platform
import subprocess

# Place this after all imports, before any class or function definitions:
MODIFIER_MAP = {
    'ctrl': 'ctrl', 'control': 'ctrl',
    'shift': 'shift',
    'alt': 'alt', 'option': 'alt',
    'cmd': 'super', 'command': 'super', 'super': 'super', 'win': 'super', 'windows': 'super',
}
def map_modifier(key):
    k = key.lower()
    return MODIFIER_MAP.get(k, k)

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
try:
    from flask import Flask, request
except ImportError:
    Flask = None
    request = None
flask_app = Flask(__name__) if Flask else None
flask_server_thread = None
flask_server_running = False

oauth_result = {}
oauth_mutex = QMutex()

def run_flask_server(port, log_callback):
    global flask_server_running
    if not flask_app:
        log_callback("Flask is not available. OAuth server cannot be started.")
        return
    try:
        flask_server_running = True
        flask_app.run(port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        log_callback(f"Flask server error: {e}")
    finally:
        flask_server_running = False

SPOTIFY_GREEN = "#1DB954"

# Default keyboard shortcuts (macOS)
DEFAULT_SHORTCUTS = {
    "like": "ctrl+shift+9",
    "dislike": "ctrl+shift+0"
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
        import keyring
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
    logger.info("svg_to_pixmap called")
    from PyQt5.QtWidgets import QApplication
    if QApplication.instance() is None:
        logger.error("svg_to_pixmap called before QApplication exists!")
        raise RuntimeError("QApplication must be created before calling svg_to_pixmap")
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
    """Parse shortcut string into key components, handling shifted symbols and macOS cmd key, and normalize to base key."""
    shifted_symbol_map = {
        '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
        '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
        'cmd': 'super'
    }
    try:
        parts = shortcut_str.lower().replace('cmd', 'super').split('+')
        keys = set()
        for part in parts:
            part = part.strip()
            if part in ['ctrl', 'shift', 'alt', 'super']:
                keys.add(part)
            elif part in shifted_symbol_map:
                keys.add(normalize_key(shifted_symbol_map[part]))
                keys.add('shift')
            elif len(part) == 1:
                keys.add(normalize_key(part))
            elif part.startswith('f') and part[1:].isdigit():
                keys.add(part)
            else:
                keys.add(normalize_key(part))
        return keys
    except Exception as e:
        logger.error(f"Error parsing shortcut {shortcut_str}: {e}")
        return set()

# Map of shifted symbols to their base key
SHIFTED_SYMBOL_MAP = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
}
# Reverse map for normalization
BASE_TO_SHIFTED = {v: k for k, v in SHIFTED_SYMBOL_MAP.items()}

# Map all US keyboard symbol keys to their base (unshifted) key
US_KEYBOARD_SYMBOLS = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
    '~': '`'
}
# Add reverse mapping for base keys
for shifted, base in list(US_KEYBOARD_SYMBOLS.items()):
    US_KEYBOARD_SYMBOLS[base] = base

def normalize_key(key):
    """Normalize a key to its base (unshifted) form for US keyboards."""
    key = key.lower()
    if key in US_KEYBOARD_SYMBOLS:
        return US_KEYBOARD_SYMBOLS[key]
    return key

def normalize_keys_for_comparison(keys):
    """Normalize a set of keys so shifted symbols and base keys are treated as equivalent if shift is present."""
    keys = set(keys)
    normalized = set()
    for k in keys:
        if k in SHIFTED_SYMBOL_MAP:
            normalized.add(SHIFTED_SYMBOL_MAP[k])
            normalized.add(k)
        elif k in BASE_TO_SHIFTED:
            normalized.add(BASE_TO_SHIFTED[k])
            normalized.add(k)
        else:
            normalized.add(k)
    # If shift is present, treat base and shifted as equivalent
    if 'shift' in keys:
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
        self._load_saved_credentials()
        # Only auto-authenticate if credentials are saved and all fields are filled
        if self.save_credentials_checkbox.isChecked() and self.client_id_input.text() and self.client_secret_input.text() and self.redirect_uri_input.text():
            QTimer.singleShot(500, self.start_authentication)
        # Prefill from config file if present
        config_id, config_secret, config_uri = load_config_credentials()
        if config_id:
            self.client_id_input.setText(config_id)
        if config_secret:
            self.client_secret_input.setText(config_secret)
        if config_uri:
            self.redirect_uri_input.setText(config_uri)

    def log(self, msg):
        if self.main_window and hasattr(self.main_window, 'debug_log_tab'):
            self.main_window.debug_log_tab.log_area.append(msg)
        else:
            logger.info(msg)

    def _load_saved_credentials(self):
        import keyring
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
        import keyring
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
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
        
        if not flask_app:
            self.error_label.setText("Flask is not available. OAuth cannot proceed.")
            self.log("Flask is not available. OAuth cannot proceed.")
            return
        
        if not hasattr(flask_app.view_functions, path):
            try:
                def dynamic_oauth_callback():
                    global oauth_result
                    if request is None:
                        return '<h2 style="color:red">Flask request object is not available.</h2>'
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
        self.sp_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-read-private playlist-read-private playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state user-library-modify",
            open_browser=False,
            cache_path=None
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
        import keyring
        import spotipy
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
        import keyring
        # Remove credentials from keyring
        try:
            keyring.delete_password("testerfy_spotify", "client_id")
        except Exception as e:
            logger.warning(f"Could not remove credentials from keyring: {e}")
        try:
            keyring.delete_password("testerfy_spotify", "client_secret")
        except Exception:
            pass
        try:
            keyring.delete_password("testerfy_spotify", "redirect_uri")
        except Exception:
            pass
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
            self.main_window.debug_log_tab.log_area.append(msg)
        else:
            logger.info(msg)

    def load_playlists(self, spotify_client):
        import spotipy
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
        try:
            if event.type() == QEvent.Type.KeyPress or event.type() == QEvent.Type.KeyRelease:
                key = event.key()
                mods = event.modifiers()
                key_name = None
                # Map Qt key codes to universal names
                if key in (Qt.Key.Key_Control, Qt.Key.Key_Meta):
                    key_name = 'ctrl' if key == Qt.Key.Key_Control else 'super'
                elif key == Qt.Key.Key_Shift:
                    key_name = 'shift'
                elif key == Qt.Key.Key_Alt:
                    key_name = 'alt'
                elif key == Qt.Key.Key_Option:
                    key_name = 'alt'
                else:
                    key_name = event.text().lower()
                if event.type() == QEvent.Type.KeyPress:
                    self._pressed_keys.add(key_name)
                else:
                    self._pressed_keys.discard(key_name)
                self._update_display()
                return True
            return super().eventFilter(obj, event)
        except Exception as e:
            logger.error(f"Exception in ShortcutCaptureDialog.eventFilter: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    def _update_display(self):
        mods = set()
        keys = set()
        for k in self._pressed_keys:
            mapped = map_modifier(k)
            if mapped in ['ctrl', 'shift', 'alt', 'super']:
                mods.add(mapped)
            elif mapped is not None:
                base = SHIFTED_SYMBOL_MAP.get(mapped, mapped)
                keys.add(normalize_key(base))
        if 'shift' in mods:
            keys = {SHIFTED_SYMBOL_MAP.get(k, k) for k in keys if k is not None}
        keys = {k for k in keys if k is not None}
        shortcut = '+'.join(sorted(mods) + sorted(keys))
        save_btn = self.button_box.button(QDialogButtonBox.Save)
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
        # Always load the current shortcuts from the main window's settings
        if self.main_window and hasattr(self.main_window, 'settings'):
            self.settings = dict(self.main_window.settings)
        else:
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
                self.main_window.debug_log_tab.log_area.append("Shortcuts reset to defaults")

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
            
            # Update settings
            self.settings["like"] = like_shortcut
            self.settings["dislike"] = dislike_shortcut
            
            # Save to file
            if save_settings(self.settings) and not update_only:
                QMessageBox.information(self, "Success", "Shortcuts saved successfully!")
                
                # Update main window shortcuts
                if self.main_window:
                    self.main_window.update_shortcuts(self.settings)
                    self.main_window.debug_log_tab.log_area.append(f"Shortcuts updated: Like={like_shortcut}, Dislike={dislike_shortcut}")
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

    def toggle_keyboard_debug(self):
        if self.main_window:
            enabled = self.keyboard_debug_button.isChecked()
            self.main_window.keyboard_debug_enabled = enabled
            if enabled:
                self.keyboard_debug_button.setText("Disable Keyboard Debug Logging")
                self.log_area.append("Keyboard debug logging ENABLED.")
            else:
                self.keyboard_debug_button.setText("Enable Keyboard Debug Logging")
                self.log_area.append("Keyboard debug logging DISABLED.")

# Utility for key normalization
KEY_ALIASES = {
    'cmd': 'super',
    'command': 'super',
    'win': 'super',
    'windows': 'super',
    'super': 'super',
}


def generate_tray_icon_png(path):
    logger.info("generate_tray_icon_png called")
    from PyQt5.QtWidgets import QApplication
    if QApplication.instance() is None:
        logger.error("generate_tray_icon_png called before QApplication exists!")
        raise RuntimeError("QApplication must be created before calling generate_tray_icon_png")
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

def check_accessibility_permissions():
    """Check if the app has accessibility permissions on macOS."""
    if platform.system() == "Darwin":
        try:
            import subprocess
            result = subprocess.run([
                "/usr/bin/osascript", "-e",
                'tell application "System Events" to return UI elements enabled'
            ], capture_output=True, text=True)
            return result.stdout.strip() == 'true'
        except Exception:
            return False
    return True

def get_app_icon():
    """Return the green 'T' QIcon for use as app and tray icon."""
    from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter
    from PyQt5.QtCore import Qt
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
    return QIcon(pixmap)

class MainWindow(QMainWindow):
    def __init__(self):
        logger.info("MainWindow.__init__ called")
        super().__init__()
        self.keyboard_debug_enabled = False
        self.listener_running = False
        self.pressed_keys = set()  # <-- Moved to the top to prevent attribute errors
        self.total_likes = 0
        self.total_dislikes = 0
        # Set the green 'T' icon for Cmd+Tab and window
        self.setWindowIcon(get_app_icon())
        self.setWindowTitle("Testerfy")
        self.resize(600, 500)
        self.tabs = QTabWidget()
        
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
        
        # Defer heavy operations until after window is shown
        QTimer.singleShot(0, self.post_init_deferred)

    def post_init_deferred(self):
        # Load settings
        self.settings = load_settings()
        # Create tray icon after settings are loaded
        self.create_tray_icon()
        # Start hotkey listener
        self.setup_global_hotkeys()
        # Start background tasks (playlist loading, OAuth, etc.)
        # (Add any other heavy startup logic here)
        # Timer for updating now playing info in tray
        self.now_playing_timer = QTimer()
        self.now_playing_timer.timeout.connect(self.update_now_playing_tooltip)
        self.now_playing_timer.timeout.connect(self.update_tray_menu)
        self.now_playing_timer.start(5000)
        if not check_accessibility_permissions():
            QMessageBox.warning(self, "Accessibility Required",
                "Testerfy needs Accessibility permissions to monitor global hotkeys.\n"
                "Go to System Preferences > Security & Privacy > Accessibility and add Python or your terminal app.")

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
        self.settings = dict(new_settings)
        # Re-parse shortcuts and restart hotkey listener
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None
            self.listener_running = False
        self.setup_global_hotkeys()
        self.debug_log_tab.log_area.append("Shortcuts updated in main window")
        self.update_tray_menu()
        logger.info("Shortcuts updated and hotkey listener restarted")

    def setup_global_hotkeys(self):
        from pynput import keyboard
        from pynput.keyboard import KeyCode
        if self.listener_running:
            logger.info("Hotkey listener already running, skipping setup")
            return
        try:
            like_keys = parse_shortcut(self.settings.get("like", DEFAULT_SHORTCUTS["like"]))
            dislike_keys = parse_shortcut(self.settings.get("dislike", DEFAULT_SHORTCUTS["dislike"]))
            if not like_keys or not dislike_keys:
                logger.error(f"Invalid shortcut(s): like={self.settings.get('like')}, dislike={self.settings.get('dislike')}")
                return
            def on_press(key):
                try:
                    key_str = None
                    if hasattr(key, 'char') and key.char:
                        key_str = normalize_key(key.char.lower())
                    elif hasattr(key, 'vk'):
                        try:
                            char = KeyCode.from_vk(key.vk).char
                            if char:
                                key_str = normalize_key(char.lower())
                        except Exception:
                            pass
                    if not key_str:
                        s = str(key).lower().replace('key.', '')
                        mapped = map_modifier(s)
                        if mapped in ['ctrl', 'shift', 'alt', 'super']:
                            key_str = mapped
                        elif s.startswith('f') and s[1:].isdigit():
                            key_str = normalize_key(s)
                    if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                        self.debug_log_tab.log_area.append(f"[on_press] Raw key: {repr(key)}, key_str: {key_str}, pressed_keys before: {self.pressed_keys}")
                    if key_str:
                        self.pressed_keys.add(key_str)
                        if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                            self.debug_log_tab.log_area.append(f"[on_press] Key pressed: {key_str}, Current keys: {self.pressed_keys}")
                            self.debug_log_tab.log_area.append(f"[on_press] Checking shortcuts - Pressed: {self.pressed_keys}, Like: {self.settings.get('like', DEFAULT_SHORTCUTS['like'])}, Dislike: {self.settings.get('dislike', DEFAULT_SHORTCUTS['dislike'])}")
                        self.check_shortcuts()
                except Exception as e:
                    logger.error(f"Error in on_press: {e}")
                    if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                        self.debug_log_tab.log_area.append(f"Error in on_press: {e}")
            def on_release(key):
                try:
                    key_str = None
                    if hasattr(key, 'char') and key.char:
                        key_str = normalize_key(key.char.lower())
                    elif hasattr(key, 'vk'):
                        try:
                            char = KeyCode.from_vk(key.vk).char
                            if char:
                                key_str = normalize_key(char.lower())
                        except Exception:
                            pass
                    if not key_str:
                        s = str(key).lower().replace('key.', '')
                        mapped = map_modifier(s)
                        if mapped in ['ctrl', 'shift', 'alt', 'super']:
                            key_str = mapped
                        elif s.startswith('f') and s[1:].isdigit():
                            key_str = normalize_key(s)
                    if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                        self.debug_log_tab.log_area.append(f"[on_release] Raw key: {repr(key)}, key_str: {key_str}, pressed_keys before: {self.pressed_keys}")
                    if key_str:
                        self.pressed_keys.discard(key_str)
                        if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                            self.debug_log_tab.log_area.append(f"[on_release] Key released: {key_str}, Current keys: {self.pressed_keys}")
                except Exception as e:
                    logger.error(f"Error in on_release: {e}")
                    if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                        self.debug_log_tab.log_area.append(f"Error in on_release: {e}")
            self.hotkey_listener = None
            try:
                self.hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
                self.hotkey_listener.start()
                self.listener_running = True  # Mark as running
                if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                    self.debug_log_tab.log_area.append("Global hotkeys enabled")
                logger.info("Hotkey listener started successfully")
            except Exception as e:
                logger.error(f"Error starting hotkey listener: {e}")
                if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                    self.debug_log_tab.log_area.append(f"Error starting hotkey listener: {e}")
        except Exception as e:
            logger.error(f"Error setting up hotkeys: {e}")
            if self.keyboard_debug_enabled and hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                self.debug_log_tab.log_area.append(f"Error setting up hotkeys: {e}")

    def check_shortcuts(self):
        """Check if any shortcuts are pressed"""
        try:
            like_keys = parse_shortcut(self.settings.get("like", DEFAULT_SHORTCUTS["like"]))
            dislike_keys = parse_shortcut(self.settings.get("dislike", DEFAULT_SHORTCUTS["dislike"]))
            # Only log shortcut check if debug is enabled
            if self.keyboard_debug_enabled:
                self.debug_log_tab.log_area.append(f"Checking shortcuts - Pressed: {self.pressed_keys}, Like: {like_keys}, Dislike: {dislike_keys}")
            if is_shortcut_match(self.pressed_keys, like_keys):
                self.debug_log_tab.log_area.append("Like shortcut matched!")
                self.like_current_song()
            elif is_shortcut_match(self.pressed_keys, dislike_keys):
                self.debug_log_tab.log_area.append("Dislike shortcut matched!")
                self.dislike_current_song()
        except Exception as e:
            if self.keyboard_debug_enabled:
                self.debug_log_tab.log_area.append(f"Error checking shortcuts: {e}")

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
        if not self.spotify_client:
            if hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                self.debug_log_tab.log_area.append("Not authenticated with Spotify")
            return
        try:
            # Get current playback
            current = self.spotify_client.current_playback()
            if not current or not current['is_playing']:
                self.debug_log_tab.log_area.append("No song currently playing")
                return
                
            track_id = current['item']['id']
            track_name = current['item']['name']
            artist_name = current['item']['artists'][0]['name']
            
            # 1. Add to selected playlists from the Playlists tab
            added_playlists = []
            selected_playlist_ids = self.playlists_tab.get_selected_playlist_ids()
            if selected_playlist_ids:
                for playlist_id in selected_playlist_ids:
                    try:
                        self.spotify_client.playlist_add_items(playlist_id, [track_id])
                        added_playlists.append(playlist_id)
                    except Exception as e:
                        if hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                            self.debug_log_tab.log_area.append(f"Error adding to playlist {playlist_id}: {e}")
            else:
                self.debug_log_tab.log_area.append("No playlists selected in Playlists tab")
            
            # 2. Remove from current playlist if playing from a playlist
            context_type = current.get('context', {}).get('type')
            self.debug_log_tab.log_area.append(f"Current playback context type: {context_type}")
            if context_type == 'playlist':
                context_uri = current.get('context', {}).get('uri', '')
                self.debug_log_tab.log_area.append(f"Context URI: {context_uri}")
                
                # Extract playlist ID from URI (format: spotify:playlist:playlist_id)
                if 'spotify:playlist:' in context_uri:
                    playlist_id = context_uri.split('spotify:playlist:')[-1]
                    self.debug_log_tab.log_area.append(f"Attempting to remove from current playlist: {playlist_id}")
                    
                    # Try multiple methods to remove the track
                    removal_success = False
                    
                    # Method 1: Remove all occurrences
                    try:
                        self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
                        self.debug_log_tab.log_area.append(f"Successfully removed from current playlist {playlist_id} (method 1)")
                        removal_success = True
                    except Exception as e:
                        self.debug_log_tab.log_area.append(f"Method 1 failed: {str(e)}")
                    
                    # Method 2: Try with positions if method 1 failed
                    if not removal_success:
                        try:
                            # Get current position in playlist
                            current_position = current.get('item', {}).get('position', None)
                            if current_position is not None:
                                self.spotify_client.playlist_remove_specific_occurrences_of_items(playlist_id, [{'uri': f'spotify:track:{track_id}', 'positions': [current_position]}])
                                self.debug_log_tab.log_area.append(f"Successfully removed from current playlist {playlist_id} (method 2)")
                                removal_success = True
                            else:
                                self.debug_log_tab.log_area.append("Could not determine track position in playlist")
                        except Exception as e:
                            self.debug_log_tab.log_area.append(f"Method 2 failed: {str(e)}")
                    
                    # Method 3: Try with track URI if other methods failed
                    if not removal_success:
                        try:
                            track_uri = f"spotify:track:{track_id}"
                            self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                            self.debug_log_tab.log_area.append(f"Successfully removed from current playlist {playlist_id} (method 3)")
                            removal_success = True
                        except Exception as e:
                            self.debug_log_tab.log_area.append(f"Method 3 failed: {str(e)}")
                    
                    if not removal_success:
                        self.debug_log_tab.log_area.append(f"All removal methods failed for playlist {playlist_id}")
                else:
                    self.debug_log_tab.log_area.append(f"Could not parse playlist ID from URI: {context_uri}")
            else:
                self.debug_log_tab.log_area.append("Not playing from a playlist - skipping removal")
            
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
                    self.debug_log_tab.log_area.append("Skipped to next song")
                else:
                    # Try without device_id (fallback)
                    self.spotify_client.next_track()
                    self.debug_log_tab.log_area.append("Skipped to next song (fallback)")
                    
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "Restriction violated" in error_msg:
                    self.debug_log_tab.log_area.append("Cannot skip track: No active device or Premium account required")
                elif "404" in error_msg:
                    self.debug_log_tab.log_area.append("Cannot skip track: No active device found")
                else:
                    self.debug_log_tab.log_area.append(f"Error skipping to next song: {error_msg}")
            
            self.debug_log_tab.log_area.append(f"Like action completed for: {track_name} by {artist_name}")
            self.total_likes += 1
            if hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                self.debug_log_tab.log_area.append(f"[LIKE] {track_name} by {artist_name} | Added to playlists: {added_playlists if added_playlists else 'None'} | Like count: {self.total_likes}")
            
        except Exception as e:
            if hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                self.debug_log_tab.log_area.append(f"Error in like action: {e}")

    def dislike_current_song(self):
        """Dislike the currently playing song - remove from current playlist and skip"""
        if not self.spotify_client:
            if hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                self.debug_log_tab.log_area.append("Not authenticated with Spotify")
            return
        try:
            # Get current playback
            current = self.spotify_client.current_playback()
            if not current or not current['is_playing']:
                self.debug_log_tab.log_area.append("No song currently playing")
                return
                
            track_id = current['item']['id']
            track_name = current['item']['name']
            artist_name = current['item']['artists'][0]['name']
            
            # 1. Remove from current playlist if playing from a playlist
            context_type = current.get('context', {}).get('type')
            self.debug_log_tab.log_area.append(f"Current playback context type: {context_type}")
            if context_type == 'playlist':
                context_uri = current.get('context', {}).get('uri', '')
                self.debug_log_tab.log_area.append(f"Context URI: {context_uri}")
                
                # Extract playlist ID from URI (format: spotify:playlist:playlist_id)
                if 'spotify:playlist:' in context_uri:
                    playlist_id = context_uri.split('spotify:playlist:')[-1]
                    self.debug_log_tab.log_area.append(f"Attempting to remove from current playlist: {playlist_id}")
                    
                    # Try multiple methods to remove the track
                    removal_success = False
                    
                    # Method 1: Remove all occurrences
                    try:
                        self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
                        self.debug_log_tab.log_area.append(f"Successfully removed from current playlist {playlist_id} (method 1)")
                        removal_success = True
                    except Exception as e:
                        self.debug_log_tab.log_area.append(f"Method 1 failed: {str(e)}")
                    
                    # Method 2: Try with positions if method 1 failed
                    if not removal_success:
                        try:
                            # Get current position in playlist
                            current_position = current.get('item', {}).get('position', None)
                            if current_position is not None:
                                self.spotify_client.playlist_remove_specific_occurrences_of_items(playlist_id, [{'uri': f'spotify:track:{track_id}', 'positions': [current_position]}])
                                self.debug_log_tab.log_area.append(f"Successfully removed from current playlist {playlist_id} (method 2)")
                                removal_success = True
                            else:
                                self.debug_log_tab.log_area.append("Could not determine track position in playlist")
                        except Exception as e:
                            self.debug_log_tab.log_area.append(f"Method 2 failed: {str(e)}")
                    
                    # Method 3: Try with track URI if other methods failed
                    if not removal_success:
                        try:
                            track_uri = f"spotify:track:{track_id}"
                            self.spotify_client.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                            self.debug_log_tab.log_area.append(f"Successfully removed from current playlist {playlist_id} (method 3)")
                            removal_success = True
                        except Exception as e:
                            self.debug_log_tab.log_area.append(f"Method 3 failed: {str(e)}")
                    
                    if not removal_success:
                        self.debug_log_tab.log_area.append(f"All removal methods failed for playlist {playlist_id}")
                else:
                    self.debug_log_tab.log_area.append(f"Could not parse playlist ID from URI: {context_uri}")
            else:
                self.debug_log_tab.log_area.append("Not playing from a playlist, skipping playlist removal")
            
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
                    self.debug_log_tab.log_area.append("Skipped to next song")
                else:
                    # Try without device_id (fallback)
                    self.spotify_client.next_track()
                    self.debug_log_tab.log_area.append("Skipped to next song (fallback)")
                    
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "Restriction violated" in error_msg:
                    self.debug_log_tab.log_area.append("Cannot skip track: No active device or Premium account required")
                elif "404" in error_msg:
                    self.debug_log_tab.log_area.append("Cannot skip track: No active device found")
                else:
                    self.debug_log_tab.log_area.append(f"Error skipping to next song: {error_msg}")
            
            self.debug_log_tab.log_area.append(f"Dislike action completed for: {track_name} by {artist_name}")
            self.total_dislikes += 1
            if hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                self.debug_log_tab.log_area.append(f"[DISLIKE] {track_name} by {artist_name} | Dislike count: {self.total_dislikes}")
            
        except Exception as e:
            if hasattr(self, 'debug_log_tab') and hasattr(self.debug_log_tab, 'log_area'):
                self.debug_log_tab.log_area.append(f"Error in dislike action: {e}")

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
        # Use the green 'T' icon for tray and window
        icon = get_app_icon()
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Testerfy")
        # Restore full context menu
        menu = QMenu()
        # Current song information section
        self.current_song_label = QAction("No song playing", self)
        self.current_song_label.setEnabled(False)  # Make it non-clickable
        menu.addAction(self.current_song_label)
        menu.addSeparator()
        # Like action with keyboard shortcut
        like_shortcut = self.settings.get("like", DEFAULT_SHORTCUTS["like"])
        self.like_action = QAction(f"❤️ Like Song ({like_shortcut})", self)
        self.like_action.triggered.connect(self.like_current_song)
        menu.addAction(self.like_action)
        # Dislike action with keyboard shortcut
        dislike_shortcut = self.settings.get("dislike", DEFAULT_SHORTCUTS["dislike"])
        self.dislike_action = QAction(f"👎 Dislike Song ({dislike_shortcut})", self)
        self.dislike_action.triggered.connect(self.dislike_current_song)
        menu.addAction(self.dislike_action)
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
                track_name = current['item']['name']
                artist_name = current['item']['artists'][0]['name']
                album_name = current['item']['album']['name']
                
                # Update the song information label
                song_text = f"🎵 {track_name}\n👤 {artist_name}\n💿 {album_name}"
                self.current_song_label.setText(song_text)
                
                # Enable like/dislike actions
                self.like_action.setEnabled(True)
                self.dislike_action.setEnabled(True)
                
                # Update tooltip
                tooltip = f"Testerfy\nNow Playing: {track_name}\nArtist: {artist_name}\nAlbum: {album_name}"
                self.tray_icon.setToolTip(tooltip)
            else:
                # No song playing
                self.current_song_label.setText("No song currently playing")
                self.like_action.setEnabled(False)
                self.dislike_action.setEnabled(False)
                self.tray_icon.setToolTip("Testerfy\nNo song playing")
                
        except Exception as e:
            # If there's an error, show a generic message
            self.current_song_label.setText("Unable to get song info")
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
        if getattr(self, '_quitting', False):
            return
        self._quitting = True
        # Stop hotkey listener
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None
        # Stop playlist loader thread if running
        if hasattr(self, 'playlists_tab') and hasattr(self.playlists_tab, 'playlist_loader_thread'):
            thread = self.playlists_tab.playlist_loader_thread
            if thread and thread.isRunning():
                try:
                    thread.quit()
                    thread.wait(2000)
                except Exception:
                    pass
        # Attempt to stop Flask server thread if running
        global flask_server_thread
        if flask_server_thread and flask_server_thread.is_alive():
            try:
                # No direct way to stop Flask thread, but set a flag if you have one
                pass
            except Exception:
                pass
        # Hide and delete tray icon
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()
            except Exception:
                pass
            self.tray_icon = None
        # Close main window if not already closed
        try:
            self.close()
        except Exception:
            pass
        # Exit the application
        QApplication.exit(0)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.is_hidden = True

def main():
    log_time('main() start')
    logger.info("main() started")
    try:
        # Create PID file for process management
        pid_file = os.path.expanduser("~/.testerfy/testerfy_macos.pid")
        os.makedirs(os.path.dirname(pid_file), exist_ok=True)
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info("About to create QApplication")
        app = QApplication(sys.argv)
        log_time('after QApplication')
        logger.info("QApplication created")
        # Set macOS-specific application properties
        app.setApplicationName("Testerfy")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Testerfy")
        # Set the green 'T' icon for Cmd+Tab switcher
        app.setWindowIcon(get_app_icon())
        logger.info("About to create MainWindow")
        window = MainWindow()
        log_time('after MainWindow')
        logger.info("MainWindow created")
        window.show()
        log_time('after window.show()')
        result = app.exec_()
        log_time('after app.exec_()')
        for label, t in startup_times:
            logger.info(f"[STARTUP SUMMARY] {label}: {t:.4f}s")
        sys.exit(result)
    except Exception as e:
        logger.error(f"Failed to start Testerfy on macOS: {e}")
        # Fallback to normal execution
        app = QApplication(sys.argv)
        app.setWindowIcon(get_app_icon())
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())

if __name__ == "__main__":
    main() 