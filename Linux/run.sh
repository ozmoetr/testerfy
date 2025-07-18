#!/bin/bash
cd "$(dirname "$0")"

# Testerfy Quick Start Script
# This script activates the virtual environment and runs Testerfy

set -e  # Exit on any error

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run the installation first:"
    echo "  ./install.sh"
    exit 1
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found!"
    echo "Please make sure you're in the Testerfy directory."
    exit 1
fi

echo "🎵 Starting Testerfy..."
echo "======================="

# Activate virtual environment and run
source venv/bin/activate
python main.py 