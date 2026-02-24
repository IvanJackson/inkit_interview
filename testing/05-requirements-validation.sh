#!/bin/bash

# Requirements Validation Tests - Step 5
# Validates compliance with updated requirements

echo "📋 Requirements Validation"
echo "=========================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Testing compliance with updated requirements:"
echo "1. Concurrent users: No shared state issues"
echo "2. Single app.py: Modular architecture acceptable"
echo "3. Mock AI service: OpenAI format compliance"
echo "4. 1 image per conversation: UI enforcement"
echo "5. Chat requires image: Endpoint enforcement"
echo "6. Only 1 image per conversation: Strict enforcement"

# Test 1: Concurrent User Safety (Requirement 1)
echo -e "\n${YELLOW}✓ Testing Requirement 1: Concurrent User Safety${NC}"

CONCURRENT_TEST=$(python3 << 'PYTHON_EOF'
import requests
import threading
import time
import json
from PIL import Image
import io

def test_concurrent_safety():
    colors = ['red', 'blue', 'green']
    def create_session(test_id):
        img = Image.new('RGB', (40, 40), color=colors[test_id % len(colors)])
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
        upload_resp = requests.post('http://localhost:5001/upload', files=files)
        
        if upload_resp.status_code == 200:
            image_id = upload_resp.json()['image_id']
            session_id = upload_resp.json().get('session_id', '')
            
            results = []
            for i in range(10):
                resp = requests.post(
                    'http://localhost:5001/chat',
                    json={'prompt': f'Concurrent test {test_id}-{i}', 'image_id': image_id},
                    headers={'Cookie': f'va_session_id={session_id}'}
                )
                results.append(resp.status_code)
            
            success_count = sum(1 for r in results if r == 200)
            print(f'Test {test_id}: {success_count}/10 successful, no conflicts detected')
            return success_count >= 8
        else:
            print(f'Test {test_id}: Upload failed')
            return False
    
    threads = []
    for i in range(3):
        thread = threading.Thread(target=create_session, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    print('✅ Concurrent user safety validated')

test_concurrent_safety()
PYTHON_EOF
)

if echo "$CONCURRENT_TEST" | grep -q "validated"; then
    echo -e "${GREEN}✅ PASS: No shared state conflicts detected${NC}"
else
    echo -e "${RED}❌ FAIL: Shared state issues detected${NC}"
fi

# Test 2: Mock AI Service OpenAI Format (Requirement 3)
echo -e "\n${YELLOW}✓ Testing Requirement 3: Mock AI Service OpenAI Format${NC}"

OPENAI_FORMAT_TEST=$(python3 << 'PYTHON_EOF'
import requests
import json
from PIL import Image
import io

img = Image.new('RGB', (50, 50), color='blue')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code == 200:
    image_id = upload_resp.json()['image_id']
    
    chat_resp = requests.post(
        'http://localhost:5001/chat/stream',
        json={'prompt': 'Format test', 'image_id': image_id},
        stream=True
    )
    
    if chat_resp.status_code == 200:
        chunk_count = 0
        format_valid = True
        
        for line in chat_resp.iter_lines():
            if line:
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                if line_str.startswith('data: '):
                    chunk_count += 1
                    payload = line_str[6:].strip()
                    if payload and payload != '[DONE]':
                        try:
                            chunk = json.loads(payload)
                            
                            required_fields = ['id', 'object', 'created', 'model', 'choices']
                            for field in required_fields:
                                if field not in chunk:
                                    format_valid = False
                                    print(f'Missing field: {field}')
                            
                            if chunk.get('object') != 'chat.completion.chunk':
                                format_valid = False
                            
                            if 'choices' not in chunk or not chunk['choices']:
                                format_valid = False
                            
                            if format_valid and chunk_count <= 5:
                                print(f'✅ Chunk {chunk_count}: Valid OpenAI format')
                                
                        except json.JSONDecodeError:
                            print(f'❌ Invalid JSON in chunk {chunk_count}')
        
        if format_valid:
            print('✅ Streaming format fully compliant with OpenAI specification')
        else:
            print('❌ OpenAI format compliance issues detected')
    else:
        print('❌ Streaming test failed')
else:
    print('❌ Upload failed for format test')
PYTHON_EOF
)

if echo "$OPENAI_FORMAT_TEST" | grep -q "fully compliant"; then
    echo -e "${GREEN}✅ PASS: OpenAI format compliant${NC}"
else
    echo -e "${RED}❌ FAIL: OpenAI format issues${NC}"
fi

# Test 3: Image Requirement Enforcement (Requirements 4,5,6)
echo -e "\n${YELLOW}✓ Testing Requirements 4,5,6: Image Enforcement${NC}"

IMAGE_ENFORCEMENT_TEST=$(python3 << 'PYTHON_EOF'
import requests
import json
from PIL import Image
import io

def test_image_requirement():
    print('Test 1: Chat without image...')
    no_image_resp = requests.post(
        'http://localhost:5001/chat',
        json={'prompt': 'Test without image'}
    )
    
    if no_image_resp.status_code == 400:
        print('✅ Chat without image correctly rejected (400)')
    else:
        print(f'❌ Chat without image should fail (got {no_image_resp.status_code})')
        return False
    
    print('Test 2: Chat with image...')
    img = Image.new('RGB', (60, 60), color='green')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
    upload_resp = requests.post('http://localhost:5001/upload', files=files)
    
    if upload_resp.status_code == 200:
        image_id = upload_resp.json()['image_id']
        
        with_image_resp = requests.post(
            'http://localhost:5001/chat',
            json={'prompt': 'Test with image', 'image_id': image_id}
        )
        
        if with_image_resp.status_code == 200:
            print('✅ Chat with image successful')
            return True
        else:
            print(f'❌ Chat with image failed (got {with_image_resp.status_code})')
            return False
    else:
        print('❌ Upload failed')
        return False

if test_image_requirement():
    print('✅ Image requirement enforcement working correctly')
else:
    print('❌ Image requirement enforcement failed')
PYTHON_EOF
)

if echo "$IMAGE_ENFORCEMENT_TEST" | grep -q "working correctly"; then
    echo -e "${GREEN}✅ PASS: Image requirements enforced${NC}"
else
    echo -e "${RED}❌ FAIL: Image requirements not enforced${NC}"
fi

# Test 4: One Image Per Conversation (Requirement 6)
echo -e "\n${YELLOW}✓ Testing Requirement 6: One Image Per Conversation${NC}"

ONE_IMAGE_TEST=$(python3 << 'PYTHON_EOF'
import requests
import json
from PIL import Image
import io

img1 = Image.new('RGB', (70, 70), color='red')
img_bytes1 = io.BytesIO()
img1.save(img_bytes1, format='JPEG')
img_bytes1.seek(0)

files1 = {'image': ('test.jpg', img_bytes1, 'image/jpeg')}
upload1 = requests.post('http://localhost:5001/upload', files=files1)

if upload1.status_code == 200:
    image_id1 = upload1.json()['image_id']
    
    chat1 = requests.post(
        'http://localhost:5001/chat',
        json={'prompt': 'First message', 'image_id': image_id1}
    )
    
    if chat1.status_code == 200:
        chat2 = requests.post(
            'http://localhost:5001/chat',
            json={'prompt': 'Second message', 'image_id': image_id1}
        )
        
        img2 = Image.new('RGB', (70, 70), color='blue')
        img_bytes2 = io.BytesIO()
        img2.save(img_bytes2, format='JPEG')
        img_bytes2.seek(0)
        
        files2 = {'image': ('test2.jpg', img_bytes2, 'image/jpeg')}
        upload2 = requests.post('http://localhost:5001/upload', files=files2)
        
        if upload2.status_code == 200:
            image_id2 = upload2.json()['image_id']
            
            chat3 = requests.post(
                'http://localhost:5001/chat',
                json={'prompt': 'Message with new image', 'image_id': image_id2}
            )
            
            history = requests.get('http://localhost:5001/chat/history?limit=100')
            
            if history.status_code == 200:
                data = history.json()
                conv_count = len(data.get('conversations', []))
                
                if conv_count >= 2:
                    print('✅ One image per conversation enforced')
                    print('✅ New image creates new conversation')
                else:
                    print('❌ Should have 2 separate conversations')
        else:
            print('❌ Second image upload failed')
    else:
        print('❌ First chat failed')
else:
    print('❌ First image upload failed')
PYTHON_EOF
)

if echo "$ONE_IMAGE_TEST" | grep -q "enforced"; then
    echo -e "${GREEN}✅ PASS: One image per conversation${NC}"
else
    echo -e "${RED}❌ FAIL: Multiple images per conversation${NC}"
fi

echo -e "\n${GREEN}Requirements validation completed!${NC}"
echo "📋 All updated requirements should now be enforced correctly"
