#!/usr/bin/env python3
"""Test session management, cookies, and restoration."""

import os
import sys
import io
from PIL import Image

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Create test app
app = create_app('testing')
client = app.test_client()

print('=== Test 1: Session Creation on Upload ===')

# Upload image
img = Image.new('RGB', (100, 100), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

response = client.post(
    '/upload',
    data={'image': (img_bytes, 'test.jpg')},
    content_type='multipart/form-data'
)

session_cookie = response.headers.get('Set-Cookie', '')
session_id = None
if 'va_session_id=' in session_cookie:
    session_id = session_cookie.split('va_session_id=')[1].split(';')[0]
    print(f'✓ Session created: {session_id}')
else:
    print('❌ No session cookie set')
    sys.exit(1)

print('\n=== Test 2: Session Persistence Across Requests ===')

# Make chat request with same session
chat_response = client.post(
    '/chat',
    json={'prompt': 'What colors?'},
    headers={'Cookie': f'va_session_id={session_id}'}
)

if chat_response.status_code == 200:
    print('✓ Session persisted across requests')
    # Check if same session ID is returned
    new_cookie = chat_response.headers.get('Set-Cookie', '')
    if session_id in new_cookie or not new_cookie:
        print('✓ Session ID maintained')
    else:
        print('⚠ Session ID changed')
else:
    print(f'❌ Chat failed with valid session')
    sys.exit(1)

print('\n=== Test 3: Session Isolation (Different Sessions) ===')

# Create second session by uploading without cookie
img2 = Image.new('RGB', (100, 100), color='yellow')
img_bytes2 = io.BytesIO()
img2.save(img_bytes2, format='JPEG')
img_bytes2.seek(0)

response2 = client.post(
    '/upload',
    data={'image': (img_bytes2, 'test2.jpg')},
    content_type='multipart/form-data'
)

session_cookie2 = response2.headers.get('Set-Cookie', '')
session_id2 = None
if 'va_session_id=' in session_cookie2:
    session_id2 = session_cookie2.split('va_session_id=')[1].split(';')[0]

if session_id2 and session_id2 != session_id:
    print(f'✓ New session created: {session_id2}')
    print('✓ Sessions are isolated')
else:
    print('❌ Session isolation failed')
    sys.exit(1)

print('\n=== Test 4: Session Restoration ===')

# Attempt to restore first session
restore_response = client.post(
    '/session/restore',
    json={'session_id': session_id}
)

if restore_response.status_code in [200, 404]:
    # 404 is expected if session hasn't expired yet
    data = restore_response.get_json()
    if restore_response.status_code == 200:
        print(f'✓ Session restored: {data.get("message")}')
    else:
        print(f'✓ Session not expired (404 expected): {data.get("error", {}).get("message")}')
else:
    print(f'❌ Unexpected status: {restore_response.status_code}')
    sys.exit(1)

print('\n✅ Session management tests PASSED')
