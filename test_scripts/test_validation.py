#!/usr/bin/env python3
"""Test input validation and error handling."""

import os
import sys
import io

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Create test app
app = create_app('testing')
client = app.test_client()

print('=== Test 1: Missing File ===')
response = client.post('/upload', content_type='multipart/form-data')
print(f'Status: {response.status_code}')
if response.status_code == 400:
    print(f'✓ Error: {response.get_json()["error"]["message"]}')
else:
    print(f'❌ Expected 400')
    sys.exit(1)

print('\n=== Test 2: Empty Filename ===')
response = client.post(
    '/upload',
    data={'image': (io.BytesIO(b''), '')},
    content_type='multipart/form-data'
)
print(f'Status: {response.status_code}')
if response.status_code == 400:
    print(f'✓ Error: {response.get_json()["error"]["message"]}')
else:
    print(f'❌ Expected 400')
    sys.exit(1)

print('\n=== Test 3: Unsupported File Type ===')
pdf_content = b'%PDF-1.4\n%fake pdf content'
response = client.post(
    '/upload',
    data={'image': (io.BytesIO(pdf_content), 'test.pdf')},
    content_type='multipart/form-data'
)
print(f'Status: {response.status_code}')
if response.status_code == 415:
    print(f'✓ Error: {response.get_json()["error"]["message"]}')
else:
    print(f'❌ Expected 415, got {response.status_code}')
    sys.exit(1)

print('\n=== Test 4: Missing Chat Prompt ===')
response = client.post('/chat', json={})
print(f'Status: {response.status_code}')
if response.status_code == 400:
    print(f'✓ Error: {response.get_json()["error"]["message"]}')
else:
    print(f'❌ Expected 400')
    sys.exit(1)

print('\n=== Test 5: XSS Attempt in Prompt ===')
response = client.post('/chat', json={'prompt': '<script>alert("xss")</script>'})
print(f'Status: {response.status_code}')
if response.status_code == 400:
    error_msg = response.get_json()["error"]["message"]
    print(f'✓ Error: {error_msg}')
    if 'malicious' in error_msg.lower():
        print('✓ XSS detected and blocked')
    else:
        print('⚠ XSS blocked but different error message')
else:
    print(f'❌ Expected 400, got {response.status_code}')
    sys.exit(1)

print('\n✅ Validation tests PASSED')
