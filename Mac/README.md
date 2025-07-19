# Testerfy for macOS

A Spotify integration app for macOS that allows you to like/dislike songs using global keyboard shortcuts.

## Features

- Global keyboard shortcuts for liking/disliking Spotify songs
- Dark-themed UI with Spotify green accent color
- System tray integration
- OAuth authentication with Spotify
- Playlist management
- Customizable keyboard shortcuts

## Prerequisites

- macOS 10.14 or later
- Python 3.8 or later
- Spotify account

## Installation & Build Instructions

### 1. Set Up Python Environment

```bash
# Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Test the App (Optional)

```bash
# Run the app directly to test it works
python main_macos.py
```

### 3. Build the App

```bash
# Build using PyInstaller with the spec file
pyinstaller Testerfy.spec
```

### 4. Install the App

After building, you'll find the app in `dist/Testerfy.app`. You can:
- Move it to `/Applications` for system-wide installation
- Run it from the `dist` folder
- Double-click to launch

## Configuration

### Spotify API Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add `http://localhost:8888/callback` as a redirect URI
4. Copy your Client ID and Client Secret
5. Open the app and enter these credentials in the Settings tab

### Permissions

The app requires accessibility permissions for global keyboard shortcuts:
1. Go to System Preferences > Security & Privacy > Privacy > Accessibility
2. Add Testerfy.app to the list of allowed apps

## Default Keyboard Shortcuts

- **Like song**: `Ctrl+Shift+9`
- **Dislike song**: `Ctrl+Shift+0`

You can customize these in the Keyboard Shortcuts tab of the app.

## File Structure

- `main_macos.py` - Main application code
- `Testerfy.spec` - PyInstaller build configuration
- `green_t.icns` - App icon
- `requirements.txt` - Python dependencies

## Troubleshooting

### Common Issues

1. **"App can't be opened"**: Right-click the app and select "Open" to bypass Gatekeeper
2. **Keyboard shortcuts not working**: Ensure accessibility permissions are granted
3. **Spotify authentication fails**: Check your Client ID/Secret and redirect URI

### Logs

Logs are stored in `~/.testerfy/testerfy_macos.log` for debugging.

## Development

To modify the app:
1. Edit `main_macos.py`
2. Test with `python main_macos.py`
3. Rebuild with `pyinstaller Testerfy.spec`

## License

See the main LICENSE file in the repository root. 