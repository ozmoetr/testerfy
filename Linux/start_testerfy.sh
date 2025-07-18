#!/bin/bash
cd "$(dirname "$0")"
# Simple script to start Testerfy in the background

echo "Starting Testerfy..."
python3 main.py
echo "Testerfy should now be running in the background. Check your system tray for the icon." 