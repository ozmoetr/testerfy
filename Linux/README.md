# Testerfy

A powerful Spotify automation and playlist manager with secure credential storage, user-specific settings, and robust keyboard shortcut handling.

## Features

- **Spotify Integration**: Full Spotify API integration with OAuth authentication
- **Secure Credential Storage**: Save and auto-fill Spotify credentials using system keyring
- **User-Specific Settings**: Playlists and keyboard shortcuts saved per Spotify user
- **Global Keyboard Shortcuts**: Like/dislike songs with customizable hotkeys
- **Playlist Management**: Select and manage your playlists with persistent selections
- **System Tray Integration**: Run in background with system tray access
- **Dark Theme**: Modern dark UI theme
- **Auto-Login**: Automatic authentication if credentials are saved

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Spotify Developer Account (for Client ID and Secret)

### Installation & Setup

**Option 1: One-Command Installation (Recommended)**

**Linux/macOS:**
```bash
git clone https://github.com/ozmoetr/testerfy.git
cd testerfy
./install.sh
```

**Windows:**
```cmd
git clone https://github.com/ozmoetr/testerfy.git
cd testerfy
install.bat
```

**Option 2: Manual Installation**

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ozmoetr/testerfy.git
   cd testerfy
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Get Spotify API credentials**:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new app
   - Note your Client ID and Client Secret
   - Add `http://localhost:8888/callback` as a Redirect URI

## Usage

### Running the Application

**Background Mode (Recommended):**
The application now runs in the background and doesn't require the terminal to stay open.

```bash
# Start in background (detaches from terminal)
python3 main.py

# Or use the daemon manager for better control
python3 testerfy_daemon.py start    # Start in background
python3 testerfy_daemon.py stop     # Stop the process
python3 testerfy_daemon.py status   # Check if running
python3 testerfy_daemon.py restart  # Restart the process

# Or use the simple start script
./start_testerfy.sh
```

**Foreground Mode (for debugging):**
```bash
# Quick Start:
./run.sh          # Linux/macOS
run.bat           # Windows

# Manual:
source venv/bin/activate  # Linux/macOS
python main.py
```

### First Time Setup

1. **Authentication Tab**: Enter your Spotify Client ID, Client Secret, and Redirect URI
2. **Optional**: Check "Save credentials" to store them securely for future use
3. **Click "Authenticate"** to connect to Spotify
4. **Playlists Tab**: Select which playlists you want to manage
5. **Keyboard Shortcuts Tab**: Set your preferred hotkeys for like/dislike actions

### Features

#### Authentication
- Secure OAuth flow with Spotify
- Optional credential saving using system keyring
- Auto-login if credentials are saved
- Sign out functionality to clear saved credentials

#### Playlist Management
- View all your editable playlists
- Select/deselect playlists for management
- Export playlist selections to JSON
- Persistent selections per user

#### Keyboard Shortcuts
- Global hotkeys for like/dislike actions
- Customizable shortcuts with validation
- No duplicate shortcuts allowed
- Instant hotkey updates

#### System Tray
- Minimize to system tray
- Right-click menu for quick actions
- Current song information in tooltip
- Easy window toggle

## Configuration

### Settings Files

The application creates several configuration files in your home directory:

- `~/.testerfy_settings.json` - Global keyboard shortcuts
- `~/.testerfy_user_settings.json` - User-specific settings (playlists, shortcuts)
- `~/.testerfy/testerfy.log` - Application logs
- `~/.testerfy/testerfy.pid` - Process ID file (for background mode)

### Background Process Management

When running in background mode, the application:

- Detaches from the terminal session
- Creates a PID file for process management
- Redirects all output to log files
- Runs as a daemon process

**Managing the background process:**
```bash
# Check if Testerfy is running
python3 testerfy_daemon.py status

# Start Testerfy in background
python3 testerfy_daemon.py start

# Stop Testerfy
python3 testerfy_daemon.py stop

# Restart Testerfy
python3 testerfy_daemon.py restart
```

**Logs and debugging:**
- Application logs: `~/.testerfy/testerfy.log`
- Process ID: `~/.testerfy/testerfy.pid`
- If the application fails to start, check the log file for errors

### Default Shortcuts

- **Like Song**: `Ctrl+Shift+F8`
- **Dislike Song**: `Ctrl+Shift+F9`

## Prefilling Spotify Authentication and Playlists via Config File

By default, Testerfy looks for a config file at `~/Documents/.testerfy_config.json`. You can override this location by setting the `TESTERFY_CONFIG_PATH` environment variable to your desired path.

### Example config file:
```json
{
  "client_id": "your_spotify_client_id",
  "client_secret": "your_spotify_client_secret",
  "redirect_uri": "http://127.0.0.1:9111/callback",
  "selected_playlists": [
    "37i9dQZF1DXcBWIGoYBM5M",  // Spotify playlist ID
    "My Favorite Playlist"      // or exact playlist name
  ]
}
```

- If this file exists and contains values, the authentication fields will be prefilled when you launch the app.
- If the file contains a `selected_playlists` list (IDs or exact names), those playlists will be pre-selected at the top of the Playlists tab (no duplicates).
- If the file does not exist or is blank, the authentication fields and playlist selection will be empty by default.

## Development

### Project Structure

- `main.py` - Main application file (all-in-one)
- `requirements.txt` - Python dependencies
- `LAUNCH_OPTIONS.md` - Detailed launch instructions

### Dependencies

- **PyQt5** - GUI framework
- **Flask** - OAuth callback server
- **spotipy** - Spotify API client
- **pynput** - Global keyboard monitoring
- **keyring** - Secure credential storage

## Troubleshooting

### Common Issues

1. **Authentication fails**: Verify your Client ID, Secret, and Redirect URI
2. **Shortcuts not working**: Check if another application is using the same hotkeys
3. **Playlists not loading**: Ensure you're authenticated and have editable playlists
4. **Permission errors**: Make sure you have write access to your home directory

### Logs

Check the log file at `~/.testerfy/testerfy.log` for detailed error information.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub Issues page.
