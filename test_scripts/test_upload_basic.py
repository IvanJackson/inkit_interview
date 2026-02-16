#!/usr/bin/env python3
"""Test basic image upload functionality."""

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

print('=== Test: Upload Valid Image ===\n')

# Create a test image
img = Image.new('RGB', (200, 200), color='blue')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

# Test upload
response = client.post(
    '/upload',
    data={'image': (img_bytes, 'test.jpg')},
    content_type='multipart/form-data'
)

print(f'Status Code: {response.status_code}\n')

if response.status_code == 200:
    data = response.get_json()

    # Show full response structure
    print('--- Full Upload Response ---')
    print(json.dumps(data, indent=2))
    print()

    # Extract and show vision analysis
    vision_analysis = data.get('analysis', {})

    print('--- Vision Analysis (Responses API Format) ---')
    print(json.dumps(vision_analysis, indent=2))
    print()

    # Extract text from Responses API format
    vision_text = vision_analysis['output'][0]['content'][0]['text']

    print('--- Extracted Analysis Text ---')
    print(f'Text: {vision_text}')
    print()

    # Show metadata
    print('--- Upload Metadata ---')
    print(f'✓ Image ID: {data["image_id"]}')
    print(f'✓ Filename: {data["filename"]}')
    print(f'✓ Dimensions: {data["width"]}x{data["height"]}')
    print(f'✓ Format: {data["format"]}')
    print(f'✓ Analysis Object Type: {vision_analysis.get("object")}')
    print(f'✓ Analysis ID: {vision_analysis.get("id")}')
    print(f'✓ Total Tokens: {vision_analysis.get("usage", {}).get("total_tokens")}')

    print('\n✅ Upload test PASSED')
else:
    print(f'❌ Upload test FAILED: {response.get_json()}')
    sys.exit(1)
