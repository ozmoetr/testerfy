#!/bin/bash
set -e  # Exit on error
cd "$(dirname "$0")"

# Testerfy Linux Installation Script

echo "🔍 Checking for Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.7 or newer."
    exit 1
fi

# Create virtual environment if it doesn't exist
echo "📦 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created."
else
    echo "✅ Virtual environment already exists."
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "✅ Installation complete. You can now run ./run.sh" 