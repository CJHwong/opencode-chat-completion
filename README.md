# opencode to OpenAI Chat Completion API

A Python HTTP server that converts [opencode](https://github.com/sst/opencode) commands to OpenAI-compatible chat completion API.

Use your **unlimited GPT-4.1 access** from GitHub Copilot in any app that supports OpenAI's API.

## Features

- **OpenAI-compatible API**: `/v1/chat/completions` endpoint with streaming support
- **macOS Status Bar**: Optional auto-start and monitoring via menu bar
- **High Performance**: Built with FastAPI and async processing
- **Easy Setup**: One-command installation and background running

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Server

```bash
# Basic server
python server.py

# macOS with status bar (auto-starts server)
./setup_macos_statusbar.sh
```

### 3. Test API

```bash
curl http://localhost:4141/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## How It Works

This server translates between OpenAI API format and the `opencode` command:

1. Takes OpenAI requests
2. Calls `opencode` with `github-copilot/gpt-4.1`
3. Returns properly formatted responses
4. Supports streaming

Related: [gpt-4.1.sh](https://gist.github.com/CJHwong/10e73d4d744a0775f4c01cafdb4852ec) - turns opencode into a system agent.

## API Reference

### Endpoints

- `POST /v1/chat/completions` - Chat completions endpoint
- `GET /v1/models` - List available models
- `GET /health` - Health check

### Request Format

```json
{
  "model": "gpt-4.1",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 1.0
}
```

### Response Format

```json
{
  "id": "chatcmpl-12345678",
  "object": "chat.completion",
  "created": 1694268190,
  "model": "gpt-4.1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ]
}
```

## macOS Status Bar

The optional macOS status bar app provides:

- **Auto-start server**: Starts `server.py` when status bar launches
- **Visual monitoring**: 🔄 Starting, ⚡ Online, 🔴 Offline, ⚠️ Error
- **Process management**: Auto-restart if server crashes
- **Clean shutdown**: Stops server when quitting

### Installation

```bash
# Quick setup
./setup_macos_statusbar.sh

# Manual setup
pip install rumps requests
chmod +x macos_statusbar.py
cp com.opencode.statusbar.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.opencode.statusbar.plist
```

### Usage

```bash
# Start manually
python3 macos_statusbar.py

# Auto-starts on login after setup
# Use Quit from menu bar to stop
```

## Configuration

### Server Options

- **Host**: `0.0.0.0` (default, accepts external connections)
- **Port**: `4141` (default)
- **Model**: `github-copilot/gpt-4.1` (hardcoded)

### Status Bar Options

```bash
python3 macos_statusbar.py --host localhost --port 8080
```

## Uninstalling

### Remove Status Bar

```bash
# Quick removal
./uninstall_macos_statusbar.sh

# Manual removal
launchctl stop com.opencode.statusbar
launchctl unload ~/Library/LaunchAgents/com.opencode.statusbar.plist
rm ~/Library/LaunchAgents/com.opencode.statusbar.plist
pkill -f "server.py" || true
```

## Supported Fields

**Processed by opencode:**

- `model`, `messages`

**Handled by server:**

- `stream`

**Accepted but ignored:**

- `temperature`, `max_tokens`, `max_completion_tokens`, `top_p`, `n`, `stop`, `presence_penalty`, `frequency_penalty`, `logit_bias`, `user`, `logprobs`, `top_logprobs`, `seed`, `tools`, `tool_choice`, `stream_options`

## File Structure

```plaintext
opencode-chat-completion/
├── server.py                      # Main API server
├── macos_statusbar.py             # macOS status bar app
├── requirements.txt               # Python dependencies
├── setup_macos_statusbar.sh       # Install status bar
├── uninstall_macos_statusbar.sh   # Remove status bar
├── com.opencode.statusbar.plist   # Launch agent config
├── opencode_completion_api.log    # Debug log file (created at runtime)
└── README.md                      # This file
```

## Troubleshooting

### Server Issues

```bash
# Check if server is running
curl http://localhost:4141/health

# Check opencode installation
opencode --version

# View server logs
python server.py  # Run in foreground

# View detailed debug logs (includes opencode execution details)
tail -f opencode_completion_api.log
```

### Status Bar Issues

```bash
# Check if service is running
launchctl list | grep statusbar

# View logs
tail -f /tmp/opencode_statusbar.log
tail -f /tmp/opencode_statusbar.error.log

# Restart service
launchctl stop com.opencode.statusbar
launchctl start com.opencode.statusbar
```

## Requirements

- **Python 3.11+**
- **opencode CLI** installed (automatically detected in common paths: `~/.opencode/bin`, `/opt/homebrew/bin`, `/usr/local/bin`, etc.)
- **macOS** (for status bar features)
- **Dependencies**: `fastapi`, `uvicorn`, `pydantic`, `requests`, `rumps` (macOS only)

## Notes

- Server accepts but doesn't validate authorization headers
- Uses `github-copilot/gpt-4.1` model internally
- Streaming responses sent character-by-character for real-time feel
- Status bar app manages server lifecycle automatically
- Comprehensive debug logging available in `opencode_completion_api.log`
- Automatic opencode executable detection in common installation paths
