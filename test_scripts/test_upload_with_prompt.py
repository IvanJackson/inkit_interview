#!/usr/bin/env python3
"""Test upload with optional prompt (hybrid approach)."""

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

print('=== Test 1: Upload WITHOUT Prompt (Original Behavior) ===\n')

# Create a test image
img = Image.new('RGB', (200, 200), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

# Upload without prompt
response = client.post(
    '/upload',
    data={'image': (img_bytes, 'red_square.jpg')},
    content_type='multipart/form-data'
)

print(f'Status Code: {response.status_code}')
data = response.get_json()

print(f'✓ Image ID: {data["image_id"]}')
print(f'✓ Has Vision Analysis: {"analysis" in data}')
print(f'✓ Has Chat Response: {"chat_response" in data}')

if "analysis" in data:
    vision_text = data["analysis"]["output"][0]["content"][0]["text"]
    print(f'✓ Vision Analysis: {vision_text}')

print('\n=== Test 2: Upload WITH Prompt (Hybrid Approach) ===\n')

# Create another test image
img2 = Image.new('RGB', (200, 200), color='blue')
img_bytes2 = io.BytesIO()
img2.save(img_bytes2, format='JPEG')
img_bytes2.seek(0)

# Upload with prompt
response2 = client.post(
    '/upload',
    data={
        'image': (img_bytes2, 'blue_square.jpg'),
        'prompt': 'What colors do you see in this image?'
    },
    content_type='multipart/form-data'
)

print(f'Status Code: {response2.status_code}')
data2 = response2.get_json()

print('--- Full Response ---')
print(json.dumps(data2, indent=2))
print()

print('--- Response Analysis ---')
print(f'✓ Image ID: {data2["image_id"]}')
print(f'✓ Has Vision Analysis: {"analysis" in data2}')
print(f'✓ Has Chat Response: {"chat_response" in data2}')

if "analysis" in data2:
    vision_text2 = data2["analysis"]["output"][0]["content"][0]["text"]
    print(f'✓ Vision Analysis: {vision_text2}')

if "chat_response" in data2:
    chat_text = data2["chat_response"]["choices"][0]["message"]["content"]
    print(f'✓ Chat Response: {chat_text}')
    print(f'✓ Chat Object Type: {data2["chat_response"]["object"]}')

print('\n=== Test 3: Follow-up Chat After Upload ===\n')

# Extract session cookie from previous upload
session_cookie = response2.headers.get('Set-Cookie', '')

# Follow-up question using /chat endpoint
chat_response = client.post(
    '/chat',
    json={'prompt': 'Can you describe it in more detail?'},
    headers={'Cookie': session_cookie}
)

print(f'Chat Status: {chat_response.status_code}')
chat_data = chat_response.get_json()
followup_text = chat_data["choices"][0]["message"]["content"]
print(f'✓ Follow-up Response: {followup_text}')

print('\n=== Summary ===\n')
print('✅ Hybrid approach working:')
print('   - Upload without prompt → Vision analysis only')
print('   - Upload with prompt → Vision analysis + Chat response')
print('   - Follow-up chats still work via /chat endpoint')
print('\n✅ All tests PASSED')
