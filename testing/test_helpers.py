#!/usr/bin/env python3
"""Helper functions for test scripts to avoid bash quote escaping issues."""

import requests
import sys
from PIL import Image
import io


def upload_test_image(color='green'):
    """Upload a test image and return the image_id."""
    try:
        img = Image.new('RGB', (50, 50), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
        resp = requests.post('http://localhost:5001/upload', files=files, timeout=10)
        
        if resp.status_code == 200:
            return resp.json().get('image_id', 'ERROR')
        else:
            return 'ERROR'
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 'ERROR'


def test_chat_with_image(image_id, prompt='What do you see?'):
    """Test chat endpoint with an image."""
    try:
        resp = requests.post(
            'http://localhost:5001/chat',
            json={'prompt': prompt, 'image_id': image_id},
            timeout=10
        )
        return resp.status_code
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: test_helpers.py <command> [args]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'upload':
        color = sys.argv[2] if len(sys.argv) > 2 else 'green'
        image_id = upload_test_image(color)
        print(image_id)
    
    elif command == 'chat':
        if len(sys.argv) < 3:
            print("ERROR: image_id required", file=sys.stderr)
            sys.exit(1)
        image_id = sys.argv[2]
        prompt = sys.argv[3] if len(sys.argv) > 3 else 'What do you see?'
        status = test_chat_with_image(image_id, prompt)
        print(status)
    
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
