#!/bin/bash
# Deploy script for PythonAnywhere
# Run this from PythonAnywhere Bash console

set -e

echo "=== Deploying IdeaScheduler Bot ==="

# Navigate to project directory
cd ~/idea_scheduler_bot

# Pull latest changes
echo "Pulling latest changes..."
git pull origin main

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --user

# Download spaCy model for smart parsing
echo "Downloading spaCy model..."
python -m spacy download en_core_web_sm --user

# Touch WSGI file to reload (PythonAnywhere specific)
echo "Reloading web app..."
touch /var/www/vasylkhmarenko_pythonanywhere_com_wsgi.py

echo "=== Deployment complete ==="
echo "Check your bot at: https://t.me/your_bot_username"
