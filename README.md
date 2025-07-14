# opencode to OpenAI Chat Completion API

A Python HTTP server that converts [opencode](https://github.com/sst/opencode) commands to OpenAI-compatible chat completion API.

Use your **unlimited GPT-4.1 access** from GitHub Copilot in any app that supports OpenAI's API.

## How It Works

This server translates between OpenAI API format and the `opencode` command:

1. Takes OpenAI requests
2. Calls `opencode` with `github-copilot/gpt-4.1`
3. Returns properly formatted responses
4. Supports streaming

Related: [gpt-4.1.sh](https://gist.github.com/CJHwong/10e73d4d744a0775f4c01cafdb4852ec) - turns opencode into a system agent.

## Features

- OpenAI-compatible `/v1/chat/completions` endpoint
- Streaming and non-streaming responses
- Text-only chat completions
- Built with FastAPI for high performance

## Installation

1. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

2. Make sure you have `opencode` installed and available in your PATH.

## Usage

### Start the server

```bash
python server.py
```

The server will start on `http://0.0.0.0:4141` (accessible via `http://localhost:4141`)

### Test with curl

**Non-streaming request:**

```bash
curl http://localhost:4141/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy-key" \
  -d '{
    "model": "gpt-4.1",
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ]
  }'
```

**Streaming request:**

```bash
curl http://localhost:4141/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy-key" \
  -d '{
    "model": "gpt-4.1",
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ],
    "stream": true
  }'
```

### API Endpoints

- `POST /v1/chat/completions` - Chat completions endpoint
- `GET /v1/models` - List available models
- `GET /health` - Health check

## Request Format

The server accepts OpenAI-compatible chat completion requests with the following supported fields:

**Fields sent to opencode:**

- `model`: The model to use (maps to `github-copilot/gpt-4.1`)
- `messages`: Array of message objects with `role` and `content` (supports multimodal content arrays)

**Fields handled by server:**

- `stream`: Boolean to enable streaming responses

**Fields accepted but ignored:**

- `temperature`, `max_tokens`, `max_completion_tokens`, `top_p`, `n`, `stop`, `presence_penalty`, `frequency_penalty`, `logit_bias`, `user`, `logprobs`, `top_logprobs`, `seed`, `tools`, `tool_choice`, `stream_options`

## Response Format

Responses follow OpenAI's chat completion format:

**Non-streaming:**

```json
{
  "id": "chatcmpl-12345678",
  "object": "chat.completion",
  "created": 1694268190,
  "model": "gpt-4.1",
  "system_fingerprint": "fp_opencode",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

**Streaming:**

```plaintext
data: {"id":"chatcmpl-12345678","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4.1","system_fingerprint":"fp_opencode","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-12345678","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4.1","system_fingerprint":"fp_opencode","choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-12345678","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4.1","system_fingerprint":"fp_opencode","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}

data: [DONE]
```

## Notes

- The server uses the `opencode` command internally with model `github-copilot/gpt-4.1`
- Authorization headers are accepted but not validated
