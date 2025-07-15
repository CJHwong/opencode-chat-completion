#!/bin/bash

# Setup script for OpenCode macOS Status Bar
# This script installs and configures the status bar app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="com.opencode.statusbar.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "🚀 Setting up OpenCode macOS Status Bar..."

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is only for macOS"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install rumps requests
elif command -v pip &> /dev/null; then
    pip install rumps requests
else
    echo "❌ Python pip not found. Please install Python first."
    exit 1
fi

# Make the Python script executable
echo "🔧 Making status bar app executable..."
chmod +x "$SCRIPT_DIR/macos_statusbar.py"

# Update paths in plist file
echo "⚙️  Configuring launch agent..."
PYTHON_PATH=$(which python3)
SCRIPT_PATH="$SCRIPT_DIR/macos_statusbar.py"

# Create a temporary plist with correct paths
sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__PROJECT_DIR__|$SCRIPT_DIR|g; s|__HOME__|$HOME|g" "$SCRIPT_DIR/$PLIST_FILE" > "/tmp/$PLIST_FILE"

# Copy plist to LaunchAgents directory
echo "📁 Installing launch agent..."
mkdir -p "$LAUNCH_AGENTS_DIR"
cp "/tmp/$PLIST_FILE" "$LAUNCH_AGENTS_DIR/$PLIST_FILE"

# Load and start the launch agent
echo "🔄 Starting status bar app..."
if launchctl list | grep -q "com.opencode.statusbar"; then
    echo "⚠️  Service already running, restarting..."
    launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_FILE" 2>/dev/null || true
fi

launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_FILE"
launchctl start com.opencode.statusbar

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Status Bar Features:"
echo "   • ⚡ Green lightning: Server is online"
echo "   • 🔴 Red circle: Server is offline"
echo "   • ⚠️  Warning: Server has errors"
echo ""
echo "🎯 Menu Options:"
echo "   • Check Status: Manual health check"
echo "   • Open API Docs: Opens /docs in browser"
echo "   • Preferences: Change host:port settings"
echo ""
echo "🔧 Management Commands:"
echo "   • Check if running: launchctl list | grep statusbar"
echo "   • Stop service: launchctl stop com.opencode.statusbar"
echo "   • Restart: launchctl stop com.opencode.statusbar && launchctl start com.opencode.statusbar"
echo "   • Uninstall: launchctl unload ~/Library/LaunchAgents/$PLIST_FILE"
echo ""
echo "📝 Logs are available at:"
echo "   • Output: /tmp/opencode_statusbar.log"
echo "   • Errors: /tmp/opencode_statusbar.error.log"
echo "   • API Debug: opencode_completion_api.log (in project directory)"
echo ""
echo "The status bar app will now start automatically on login!"
