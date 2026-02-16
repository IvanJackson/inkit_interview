#!/usr/bin/env python3
"""Test OpenAI API format compatibility.

Validates two distinct formats:
- Vision Analysis: OpenAI Responses API format (output array)
- Chat Completion: OpenAI Chat Completions API format (choices array)
"""

import os
import sys
import io
import json
from PIL import Image

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Create test app
app = create_app('testing')
client = app.test_client()


def validate_responses_api_format(response_data):
    """Validate OpenAI Responses API format (used for vision analysis)."""
    errors = []

    # Required top-level fields
    required_fields = ['id', 'object', 'created_at', 'model', 'output', 'usage']
    for field in required_fields:
        if field not in response_data:
            errors.append(f'Missing field: {field}')

    # Validate id format (resp_ prefix)
    if 'id' in response_data and not response_data['id'].startswith('resp_'):
        errors.append(f'Invalid ID format: {response_data["id"]} (expected resp_ prefix)')

    # Validate object type
    if response_data.get('object') != 'response':
        errors.append(f'Invalid object type: {response_data.get("object")} (expected "response")')

    # Validate output structure
    if 'output' in response_data:
        if not isinstance(response_data['output'], list):
            errors.append('Output must be a list')
        elif len(response_data['output']) > 0:
            msg = response_data['output'][0]
            if not msg.get('id', '').startswith('msg_'):
                errors.append(f'Message ID should start with msg_: {msg.get("id")}')
            if msg.get('type') != 'message':
                errors.append(f'Message type should be "message": {msg.get("type")}')
            if msg.get('role') != 'assistant':
                errors.append(f'Message role should be "assistant": {msg.get("role")}')
            if 'content' not in msg:
                errors.append('Message missing content array')
            elif len(msg['content']) > 0:
                block = msg['content'][0]
                if block.get('type') != 'output_text':
                    errors.append(f'Content block type should be "output_text": {block.get("type")}')
                if 'text' not in block:
                    errors.append('Content block missing text')
                if 'annotations' not in block:
                    errors.append('Content block missing annotations')

    # Validate usage (Responses API uses input_tokens/output_tokens)
    if 'usage' in response_data:
        usage_fields = ['input_tokens', 'output_tokens', 'total_tokens']
        for field in usage_fields:
            if field not in response_data['usage']:
                errors.append(f'Usage missing {field}')

    return errors


def validate_chat_completions_format(response_data):
    """Validate OpenAI Chat Completions API format (used for chat)."""
    errors = []

    # Required top-level fields
    required_fields = ['id', 'object', 'created', 'model', 'choices', 'usage']
    for field in required_fields:
        if field not in response_data:
            errors.append(f'Missing field: {field}')

    # Validate id format (chatcmpl- prefix)
    if 'id' in response_data and not response_data['id'].startswith('chatcmpl-'):
        errors.append(f'Invalid ID format: {response_data["id"]} (expected chatcmpl- prefix)')

    # Validate object type
    if response_data.get('object') != 'chat.completion':
        errors.append(f'Invalid object type: {response_data.get("object")} (expected "chat.completion")')

    # Validate choices structure
    if 'choices' in response_data:
        if not isinstance(response_data['choices'], list):
            errors.append('Choices must be a list')
        elif len(response_data['choices']) > 0:
            choice = response_data['choices'][0]
            if 'index' not in choice:
                errors.append('Choice missing index')
            if 'message' not in choice:
                errors.append('Choice missing message')
            elif 'role' not in choice['message'] or 'content' not in choice['message']:
                errors.append('Message missing role or content')
            if 'finish_reason' not in choice:
                errors.append('Choice missing finish_reason')
            if 'logprobs' not in choice:
                errors.append('Choice missing logprobs')

    # Validate optional fields exist
    if 'service_tier' not in response_data:
        errors.append('Missing optional field: service_tier')
    if 'system_fingerprint' not in response_data:
        errors.append('Missing optional field: system_fingerprint')

    # Validate usage (Chat Completions uses prompt_tokens/completion_tokens)
    if 'usage' in response_data:
        usage_fields = ['prompt_tokens', 'completion_tokens', 'total_tokens']
        for field in usage_fields:
            if field not in response_data['usage']:
                errors.append(f'Usage missing {field}')

    return errors


print('=== Test 1: Upload Response - Vision Analysis (Responses API Format) ===\n')

# Upload image
img = Image.new('RGB', (150, 150), color='purple')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

response = client.post(
    '/upload',
    data={'image': (img_bytes, 'test.jpg')},
    content_type='multipart/form-data'
)

upload_data = response.get_json()
vision_analysis = upload_data.get('analysis', {})

# Show full vision analysis response
print('--- Full Vision Analysis Response (Responses API) ---')
print(json.dumps(vision_analysis, indent=2))
print()

# Extract text from Responses API format
vision_text = vision_analysis['output'][0]['content'][0]['text']
print('--- Extracted Vision Text ---')
print(f'Text: {vision_text}')
print()

errors = validate_responses_api_format(vision_analysis)
if errors:
    print('❌ Vision analysis format errors:')
    for error in errors:
        print(f'  - {error}')
    sys.exit(1)
else:
    print('✓ Vision analysis matches Responses API format')
    print(f'  - ID: {vision_analysis["id"]}')
    print(f'  - Object: {vision_analysis["object"]}')
    print(f'  - Model: {vision_analysis["model"]}')
    print(f'  - Message ID: {vision_analysis["output"][0]["id"]}')
    print(f'  - Content Type: {vision_analysis["output"][0]["content"][0]["type"]}')
    print(f'  - Tokens: {vision_analysis["usage"]["total_tokens"]}')

print('\n=== Test 2: Chat Response (Chat Completions API Format) ===\n')

session_cookie = response.headers.get('Set-Cookie', '')

chat_response = client.post(
    '/chat',
    json={'prompt': 'Describe this image'},
    headers={'Cookie': session_cookie}
)

chat_data = chat_response.get_json()

# Show full chat response
print('--- Full Chat Response (Chat Completions API) ---')
print(json.dumps(chat_data, indent=2))
print()

# Extract text from Chat Completions format
chat_text = chat_data['choices'][0]['message']['content']
print('--- Extracted Chat Text ---')
print(f'Text: {chat_text}')
print()

errors = validate_chat_completions_format(chat_data)
if errors:
    print('❌ Chat response format errors:')
    for error in errors:
        print(f'  - {error}')
    sys.exit(1)
else:
    print('✓ Chat response matches Chat Completions API format')
    print(f'  - ID: {chat_data["id"]}')
    print(f'  - Object: {chat_data["object"]}')
    print(f'  - Model: {chat_data["model"]}')
    print(f'  - Finish reason: {chat_data["choices"][0]["finish_reason"]}')
    print(f'  - Role: {chat_data["choices"][0]["message"]["role"]}')
    print(f'  - Logprobs: {chat_data["choices"][0]["logprobs"]}')
    print(f'  - Service tier: {chat_data.get("service_tier")}')
    print(f'  - System fingerprint: {chat_data.get("system_fingerprint")}')

print('\n=== Test 3: Formats Are Distinct ===\n')

# Vision should NOT have Chat Completions fields
if 'choices' in vision_analysis:
    print('❌ Vision analysis incorrectly has "choices" field')
    sys.exit(1)
if 'output' in chat_data:
    print('❌ Chat response incorrectly has "output" field')
    sys.exit(1)

print('✓ Vision uses Responses API (output array)')
print('✓ Chat uses Chat Completions API (choices array)')
print('✓ Formats are correctly distinct')

print('\n=== Test 4: Error Response Format ===\n')

error_response = client.post('/chat', json={})
error_data = error_response.get_json()

# Show full error response
print('--- Full Error Response ---')
print(json.dumps(error_data, indent=2))
print()

if 'error' not in error_data:
    print('❌ Error response missing "error" field')
    sys.exit(1)

error = error_data['error']
required_error_fields = ['message', 'type']
missing = [f for f in required_error_fields if f not in error]

if missing:
    print(f'❌ Error missing fields: {missing}')
    sys.exit(1)
else:
    print('✓ Error response matches OpenAI format')
    print(f'  - Type: {error["type"]}')
    print(f'  - Message: {error["message"]}')
    if 'code' in error:
        print(f'  - Code: {error["code"]}')
    if 'param' in error:
        print(f'  - Param: {error["param"]}')

print('\n✅ OpenAI format compatibility tests PASSED')
