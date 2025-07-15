"""
OpenCode to OpenAI Chat Completion API Converter
A simple HTTP server that converts opencode commands to OpenAI-compatible chat completion API.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import asdict, dataclass
from typing import Any, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, validator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('opencode_completion_api.log')],
)
logger = logging.getLogger(__name__)


@dataclass
class ChatCompletionChoice:
    index: int
    message: Optional[dict[str, Any]] = None
    delta: Optional[dict[str, Any]] = None
    logprobs: Optional[dict[str, Any]] = None
    finish_reason: Optional[str] = None


@dataclass
class ChatCompletionChunk:
    id: str
    object: str
    created: int
    model: str
    system_fingerprint: str
    choices: list[ChatCompletionChoice]


@dataclass
class ChatCompletion:
    id: str
    object: str
    created: int
    model: str
    system_fingerprint: str
    choices: list[ChatCompletionChoice]
    usage: Optional[dict[str, int]] = None


class Message(BaseModel):
    role: str
    content: Union[str, list[dict[str, Any]]]

    @validator('content', pre=True)
    def process_content(cls, v):
        """Process content - convert array format to string"""
        if isinstance(v, list):
            # Extract text from multimodal content format
            text_parts = []
            for item in v:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
            return '\n'.join(text_parts)
        return v


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None  # Add OpenAI's newer field
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stop: Optional[list[str]] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[dict[str, float]] = None
    user: Optional[str] = None
    # Add other common OpenAI fields that might be sent
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    seed: Optional[int] = None
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    stream_options: Optional[dict[str, Any]] = None


app = FastAPI(title='OpenCode to OpenAI API', version='1.0.0')


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed information"""
    return JSONResponse(
        status_code=422,
        content={
            'error': {
                'message': f'Validation error: {exc}',
                'type': 'invalid_request_error',
                'details': exc.errors(),
            }
        },
    )


class OpenCodeExecutor:
    model = 'github-copilot/gpt-4.1'

    def __init__(self):
        # Try to find opencode executable
        self.opencode_path = self._find_opencode_executable()
        logger.debug(f'OpenCode executable found at: {self.opencode_path}')

    def _find_opencode_executable(self) -> str:
        """Find the opencode executable in various common locations"""
        # Log current environment
        logger.debug(f'Current PATH: {os.environ.get("PATH", "Not set")}')
        logger.debug(f'Current working directory: {os.getcwd()}')

        # First try using shutil.which (respects PATH)
        opencode_path = shutil.which('opencode')
        if opencode_path:
            logger.debug(f'Found opencode via PATH: {opencode_path}')
            return opencode_path

        # Common installation paths to check
        common_paths = [
            '/usr/local/bin/opencode',
            '/opt/homebrew/bin/opencode',
            '/usr/bin/opencode',
            os.path.expanduser('~/.opencode/bin/opencode'),  # OpenCode's default installation path
            os.path.expanduser('~/.local/bin/opencode'),
            os.path.expanduser('~/bin/opencode'),
        ]

        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                logger.debug(f'Found opencode at: {path}')
                return path

        logger.warning("Could not find opencode executable, falling back to 'opencode'")
        return 'opencode'

    async def execute_opencode(self, query: str) -> AsyncGenerator[str, None]:
        """Execute opencode command and yield output content in real-time"""
        logger.debug(f'Starting opencode execution with model: {self.model}')
        logger.debug(f'Query length: {len(query)} characters')

        wrapped_query = f"""{query}

IMPORTANT: Wrap your entire response in <opencode_output></opencode_output> tags. Put ALL your output content inside these tags."""

        command = f'"{self.opencode_path}" --model "{self.model}" run -'
        logger.debug(f'Executing command: {command}')

        # Set up environment with extended PATH for subprocess
        env = os.environ.copy()
        additional_paths = [
            '/usr/local/bin',
            '/opt/homebrew/bin',
            os.path.expanduser('~/.opencode/bin'),  # OpenCode's default installation path
            os.path.expanduser('~/.local/bin'),
            os.path.expanduser('~/bin'),
        ]
        current_path = env.get('PATH', '')
        extended_path = ':'.join(additional_paths + [current_path])
        env['PATH'] = extended_path
        logger.debug(f'Extended PATH for subprocess: {extended_path}')

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,  # Separate stderr for better debugging
                env=env,
            )
            logger.debug(f'Process created with PID: {process.pid}')
        except Exception as e:
            logger.error(f'Failed to create subprocess: {e}')
            raise

        if process.stdout is None or process.stdin is None or process.stderr is None:
            logger.error('Process stdin, stdout, or stderr is None')
            raise RuntimeError('Failed to start opencode process')

        # Send the wrapped query to stdin
        try:
            logger.debug('Sending query to opencode process')
            process.stdin.write(wrapped_query.encode())
            await process.stdin.drain()
            process.stdin.close()
            logger.debug('Query sent successfully, stdin closed')
        except Exception as e:
            logger.error(f'Failed to send query to process: {e}')
            raise

        inside_tags = False
        first_output_line = False
        line_buffer = ''
        byte_buffer = bytearray()
        total_chars_yielded = 0

        logger.debug('Starting to read output from opencode process')
        while True:
            # Read byte by byte and handle multi-byte UTF-8 characters
            byte_data = await process.stdout.read(1)
            if not byte_data:
                logger.debug('No more data from process stdout')
                break

            byte_buffer.extend(byte_data)

            # Try to decode the accumulated bytes
            try:
                char = byte_buffer.decode('utf-8')
                # Successfully decoded, clear buffer and use the character
                byte_buffer.clear()
            except UnicodeDecodeError:
                # Incomplete multi-byte character, continue reading
                continue

            line_buffer += char

            # Process complete lines
            if char == '\n':
                # Clean ANSI escape codes
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line_buffer.rstrip('\n\r'))

                # Check for start tag
                if '<opencode_output>' in clean_line:
                    inside_tags = True
                    line_buffer = ''
                    continue

                # Check for end tag
                if '</opencode_output>' in clean_line:
                    if inside_tags:
                        break

                # Stream content in real-time when inside tags
                if inside_tags:
                    # Skip model prefix line
                    if clean_line.startswith('@') and 'github-copilot' in clean_line:
                        line_buffer = ''
                        continue

                    # Skip empty lines only before the first non-empty line
                    if not clean_line and not first_output_line:
                        line_buffer = ''
                        continue
                    if clean_line:
                        first_output_line = True

                    # Stream each character from the completed line
                    for line_char in clean_line:
                        yield line_char
                        total_chars_yielded += 1

                    # Add newline after each line
                    yield '\n'
                    total_chars_yielded += 1

                line_buffer = ''

        return_code = await process.wait()
        logger.debug(f'Process completed with return code: {return_code}')
        logger.debug(f'Total characters yielded: {total_chars_yielded}')

        # Read any stderr output for debugging
        if process.stderr:
            stderr_output = await process.stderr.read()
            if stderr_output:
                stderr_text = stderr_output.decode('utf-8', errors='replace')
                logger.error(f'OpenCode stderr output: {stderr_text}')

        if return_code != 0:
            logger.error(f'OpenCode process failed with return code: {return_code}')
            if total_chars_yielded == 0:
                logger.error('No output was generated - this suggests opencode command failed to run')
                raise RuntimeError(f'OpenCode command failed with exit code {return_code}')

        if total_chars_yielded == 0:
            logger.warning('Process completed successfully but no output was generated')


def create_chat_completion_chunk(
    chunk_id: str,
    model: str,
    index: int = 0,
    delta: Optional[dict[str, Any]] = None,
    finish_reason: Optional[str] = None,
) -> str:
    """Create a chat completion chunk in OpenAI format"""
    choice = ChatCompletionChoice(index=index, delta=delta or {}, logprobs=None, finish_reason=finish_reason)

    chunk = ChatCompletionChunk(
        id=chunk_id,
        object='chat.completion.chunk',
        created=int(time.time()),
        model=model,
        system_fingerprint='fp_opencode',
        choices=[choice],
    )

    # Convert to dict and remove None values
    chunk_dict = asdict(chunk)
    for choice_data in chunk_dict['choices']:
        if choice_data.get('message') is None:
            choice_data.pop('message', None)

    return f'data: {json.dumps(chunk_dict)}\n\n'


def create_chat_completion(completion_id: str, model: str, content: str, index: int = 0) -> dict[str, Any]:
    """Create a complete chat completion response"""
    completion = ChatCompletion(
        id=completion_id,
        object='chat.completion',
        created=int(time.time()),
        model=model,
        system_fingerprint='fp_opencode',
        choices=[
            ChatCompletionChoice(
                index=index,
                message={'role': 'assistant', 'content': content},
                logprobs=None,
                finish_reason='stop',
            )
        ],
        usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
    )
    return asdict(completion)


def build_prompt_from_messages(messages: list[Message]) -> str:
    """Convert OpenAI messages format to a single prompt"""
    prompt_parts = []

    for message in messages:
        if message.role == 'system' or message.role == 'developer':
            prompt_parts.append(f'System: {message.content}')
        elif message.role == 'user':
            prompt_parts.append(f'User: {message.content}')
        elif message.role == 'assistant':
            prompt_parts.append(f'Assistant: {message.content}')

    return '\n\n'.join(prompt_parts)


@app.post('/v1/chat/completions')
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint"""
    try:
        # Build prompt from messages
        prompt = build_prompt_from_messages(request.messages)

        # Generate unique ID for this completion
        completion_id = f'chatcmpl-{uuid.uuid4().hex[:8]}'

        executor = OpenCodeExecutor()

        if request.stream:
            # Streaming response
            async def generate_stream():
                # First chunk with role
                first_chunk = create_chat_completion_chunk(
                    completion_id,
                    request.model,
                    delta={'role': 'assistant', 'content': ''},
                )
                yield first_chunk

                # Stream content character by character
                async for char in executor.execute_opencode(prompt):
                    if char:
                        chunk = create_chat_completion_chunk(completion_id, request.model, delta={'content': char})
                        yield chunk

                # Send final chunk with finish_reason
                final_chunk = create_chat_completion_chunk(completion_id, request.model, finish_reason='stop')
                yield final_chunk
                yield 'data: [DONE]\n\n'

            return StreamingResponse(
                generate_stream(),
                media_type='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Content-Type': 'text/event-stream',
                },
            )
        else:
            # Non-streaming response - collect all content first
            content_parts = []
            async for char in executor.execute_opencode(prompt):
                content_parts.append(char)

            full_content = ''.join(content_parts)
            completion = create_chat_completion(completion_id, request.model, full_content)
            return completion

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error processing request: {str(e)}')


@app.get('/v1/models')
async def list_models():
    """List available models"""
    return {
        'object': 'list',
        'data': [
            {
                'id': OpenCodeExecutor.model,
                'object': 'model',
                'created': int(time.time()),
                'owned_by': 'opencode',
            }
        ],
    }


@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=4141)
