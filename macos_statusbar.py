#!/usr/bin/env python3
"""
macOS Status Bar Add-on for OpenCode to OpenAI API Converter

Status bar app that automatically starts the OpenCode server and monitors it:
- ⚡ Server online
- 🔴 Server offline
- ⚠️ Server error

Usage:
    python3 macos_statusbar.py [--port PORT] [--host HOST]
"""

import argparse
import os
import subprocess
import sys
import threading
import time

import requests
import rumps


class OpenCodeStatusBar(rumps.App):
    def __init__(self, host='localhost', port=4141):
        super().__init__('🔄')  # Starting icon
        self.host = host
        self.port = port
        self.base_url = f'http://{host}:{port}'
        self.status = 'Starting'
        self.server_process = None

        # Start the server first
        self.start_server()

        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_server, daemon=True)
        self.monitor_thread.start()

    def start_server(self):
        """Start the OpenCode API server"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            server_script = os.path.join(script_dir, 'server.py')

            if not os.path.exists(server_script):
                print(f'Error: server.py not found at {server_script}')
                self.status = 'Error'
                self.title = '⚠️'
                return

            # Start the server process
            self.server_process = subprocess.Popen(
                [sys.executable, server_script],
                cwd=script_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            print(f'Started server with PID: {self.server_process.pid}')

        except Exception as e:
            print(f'Failed to start server: {e}')
            self.status = 'Error'
            self.title = '⚠️'

    def monitor_server(self):
        """Background thread to monitor server status"""
        # Wait a bit for server to start
        time.sleep(3)

        while self.monitoring:
            try:
                response = requests.get(f'{self.base_url}/health', timeout=5)
                if response.status_code == 200:
                    self.status = 'Online'
                    self.title = '⚡'  # Green lightning when online
                else:
                    self.status = 'Error'
                    self.title = '⚠️'  # Warning when error
            except requests.exceptions.RequestException:
                self.status = 'Offline'
                self.title = '🔴'  # Red circle when offline

                # Try to restart server if it's offline
                if self.server_process and self.server_process.poll() is not None:
                    print('Server process died, restarting...')
                    self.start_server()

            # Status is shown via icon only
            time.sleep(10)  # Check every 10 seconds

    @rumps.clicked('Quit')
    def quit_clicked(self, sender):
        """Handle quit menu click"""
        self.cleanup_and_quit()

    def cleanup_and_quit(self):
        """Clean up server and quit application"""
        self.monitoring = False

        # Stop the server process
        if self.server_process:
            try:
                print(f'Stopping server process {self.server_process.pid}')
                self.server_process.terminate()

                # Wait a bit for graceful shutdown
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop gracefully
                    self.server_process.kill()

                print('Server stopped')
            except Exception as e:
                print(f'Error stopping server: {e}')

        # Quit the application
        rumps.quit_application()


def main():
    """Main entry point with command line argument support"""
    parser = argparse.ArgumentParser(description='macOS Status Bar for OpenCode API Server')
    parser.add_argument('--host', default='localhost', help='API server host (default: localhost)')
    parser.add_argument('--port', type=int, default=4141, help='API server port (default: 4141)')

    args = parser.parse_args()

    # Create and run the status bar app
    app = OpenCodeStatusBar(host=args.host, port=args.port)

    # Hide the quit button in the menu bar
    app.quit_button = None
    app.run()


if __name__ == '__main__':
    main()
