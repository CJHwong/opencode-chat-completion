#!/bin/bash

# Uninstall script for OpenCode macOS Status Bar
# This script completely removes the status bar app and auto-launch configuration

set -e

PLIST_FILE="com.opencode.statusbar.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_FILE"

echo "🗑️  Uninstalling OpenCode macOS Status Bar..."

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is only for macOS"
    exit 1
fi

# Step 1: Stop the service if running
echo "🛑 Stopping status bar service..."
if launchctl list | grep -q "com.opencode.statusbar"; then
    launchctl stop com.opencode.statusbar 2>/dev/null || true
    echo "   ✅ Service stopped"
else
    echo "   ℹ️  Service was not running"
fi

# Step 2: Unload the launch agent
echo "📤 Unloading launch agent..."
if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo "   ✅ Launch agent unloaded"
else
    echo "   ℹ️  Launch agent file not found"
fi

# Step 3: Remove the plist file
echo "🗂️  Removing launch agent file..."
if [ -f "$PLIST_PATH" ]; then
    rm "$PLIST_PATH"
    echo "   ✅ Removed $PLIST_PATH"
else
    echo "   ℹ️  Launch agent file already removed"
fi

# Step 4: Kill any remaining processes
echo "🔍 Checking for running processes..."
if pgrep -f "macos_statusbar.py" > /dev/null; then
    echo "   🛑 Stopping status bar processes..."
    pkill -f "macos_statusbar.py" || true
    echo "   ✅ Status bar processes stopped"
else
    echo "   ℹ️  No status bar processes found"
fi

# Also stop any server processes managed by the status bar
echo "🔍 Checking for managed server processes..."
if pgrep -f "server.py" > /dev/null; then
    echo "   🛑 Stopping server processes..."
    pkill -f "server.py" || true
    echo "   ✅ Server processes stopped"
else
    echo "   ℹ️  No server processes found"
fi

# Step 5: Clean up log files
echo "🧹 Cleaning up log files..."
LOG_FILES=(
    "/tmp/opencode_statusbar.log"
    "/tmp/opencode_statusbar.error.log"
)

for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        rm "$log_file"
        echo "   ✅ Removed $log_file"
    fi
done

# Step 6: Verification
echo "🔍 Verifying removal..."
ISSUES=0

# Check launchctl
if launchctl list | grep -q "com.opencode.statusbar"; then
    echo "   ⚠️  Warning: Service still appears in launchctl list"
    ISSUES=$((ISSUES + 1))
fi

# Check plist file
if [ -f "$PLIST_PATH" ]; then
    echo "   ⚠️  Warning: Launch agent file still exists"
    ISSUES=$((ISSUES + 1))
fi

# Check running processes
if pgrep -f "macos_statusbar.py" > /dev/null; then
    echo "   ⚠️  Warning: Status bar processes still running"
    ISSUES=$((ISSUES + 1))
fi

# Check server processes
if pgrep -f "server.py" > /dev/null; then
    echo "   ⚠️  Warning: Server processes still running"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo "   ✅ Verification successful - all components removed"
else
    echo "   ⚠️  Found $ISSUES issue(s) during verification"
    echo ""
    echo "🔧 Manual cleanup may be required. See README.md for troubleshooting."
fi

echo ""
echo "✅ Uninstall complete!"
echo ""
echo "📊 Status after removal:"
echo "   • No status bar icon in menu bar"
echo "   • No auto-start on login"
echo "   • No background processes"
echo "   • No managed server processes"
echo "   • Launch agent removed"
echo ""
echo "💡 To reinstall later, run: ./setup_macos_statusbar.sh"
echo "📚 For troubleshooting, see: README.md"