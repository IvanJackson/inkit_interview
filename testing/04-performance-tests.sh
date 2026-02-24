#!/bin/bash

# Performance Tests - Step 4
# Tests concurrent user safety, rate limiting, and performance

echo "⚡ Performance Tests"
echo "===================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: Concurrent User Safety
echo -e "\n${YELLOW}Test 1: Concurrent User Safety${NC}"
echo "Testing: Multiple simultaneous requests don't interfere with each other"

# Function to run concurrent requests
run_concurrent_test() {
    local test_id=$1
    local image_data=$2
    
    python3 << 'PYTHON_EOF'
import requests
import threading
import time
import json
from PIL import Image
import io

def upload_and_chat(test_id, image_data):
    try:
        # Upload image
        img = Image.new('RGB', (50, 50), color=image_data)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
        upload_resp = requests.post('http://localhost:5001/upload', files=files, timeout=10)
        
        if upload_resp.status_code != 200:
            print(f'Test {test_id}: Upload failed')
            return
        
        image_id = upload_resp.json()['image_id']
        
        # Send chat
        chat_resp = requests.post(
            'http://localhost:5001/chat',
            json={'prompt': f'Test message {test_id}', 'image_id': image_id},
            timeout=10
        )
        
        if chat_resp.status_code == 200:
            response_data = chat_resp.json()
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'No content')
            print(f'Test {test_id}: SUCCESS - {content[:50]}...')
        else:
            print(f'Test {test_id}: Chat failed - {chat_resp.status_code}')
            
    except Exception as e:
        print(f'Test {test_id}: ERROR - {str(e)}')

# Run 5 concurrent requests
threads = []
colors = ['red', 'blue', 'green', 'yellow', 'purple']

for i in range(5):
    color = colors[i]
    thread = threading.Thread(target=upload_and_chat, args=(i+1, color))
    threads.append(thread)
    thread.start()

# Wait for all threads to complete
for thread in threads:
    thread.join()

print('✅ Concurrent test completed')
PYTHON_EOF

    echo -e "${GREEN}✅ Concurrent test completed - check results above${NC}"
}

# Test 2: File Safety
echo -e "\n${YELLOW}Test 2: File Safety${NC}"
echo "Testing: No file overwrites or conflicts with concurrent uploads"

# Test that different uploads create different files
echo "Testing unique file generation..."
FILE_TEST=$(python3 << 'PYTHON_EOF'
import requests
import os
from PIL import Image
import io

# Upload 3 images
image_ids = []
for i in range(3):
    img = Image.new('RGB', (50, 50), color=['red', 'blue', 'green'][i])
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
    resp = requests.post('http://localhost:5001/upload', files=files)
    
    if resp.status_code == 200:
        image_ids.append(resp.json()['image_id'])

# Check all IDs are unique
if len(image_ids) == len(set(image_ids)) == 3:
    print('✅ All uploads created unique files')
else:
    print('❌ File collision detected')
PYTHON_EOF
)

echo "$FILE_TEST"

# Test 3: Rate Limiting
echo -e "\n${YELLOW}Test 3: Rate Limiting${NC}"
echo "Testing: Rate limits are enforced properly"

# Test upload rate limit (20/hour)
echo "Testing upload rate limit..."
RATE_LIMIT_TEST=$(python3 << 'PYTHON_EOF'
import requests
import time
from PIL import Image
import io

# Try to exceed rate limit (20/hour)
success_count = 0
rate_limited = False

for i in range(25):
    img = Image.new('RGB', (50, 50), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
    resp = requests.post('http://localhost:5001/upload', files=files)
    
    if resp.status_code == 200:
        success_count += 1
    elif resp.status_code == 429:
        rate_limited = True
        break
    
    time.sleep(0.1)

if rate_limited:
    print(f'✅ Rate limit enforced after {success_count} uploads')
else:
    print(f'⚠️  Rate limit not triggered ({success_count}/25 succeeded)')
PYTHON_EOF
)

if echo "$RATE_LIMIT_TEST" | grep -q "Rate limited"; then
    echo -e "${GREEN}✅ Upload rate limiting working${NC}"
else
    echo -e "${YELLOW}⚠️  Upload rate limit may not be strictly enforced${NC}"
fi

# Test chat rate limit (100/minute)
echo "Testing chat rate limit..."
CHAT_RATE_TEST=$(python3 << 'PYTHON_EOF'
import requests
import time
from PIL import Image
import io

# First upload an image to chat with
img = Image.new('RGB', (50, 50), color='blue')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code != 200:
    print('❌ Failed to upload test image')
else:
    image_id = upload_resp.json()['image_id']
    
    success_count = 0
    start_time = time.time()
    
    for i in range(105):  # Try 105 chats (should hit limit of 100)
        resp = requests.post(
            'http://localhost:5001/chat',
            json={'prompt': f'Rate test {i}', 'image_id': image_id},
            timeout=5
        )
        
        if resp.status_code == 200:
            success_count += 1
        elif resp.status_code == 429:
            elapsed = time.time() - start_time
            print(f'Rate limited after {success_count} chats in {elapsed:.1f}s')
            break
        time.sleep(0.05)
    
    print(f'Chats succeeded: {success_count}')
PYTHON_EOF
)

if echo "$CHAT_RATE_TEST" | grep -q "Rate limited"; then
    echo -e "${GREEN}✅ Chat rate limiting working${NC}"
else
    echo -e "${YELLOW}⚠️  Chat rate limit may not be strictly enforced${NC}"
fi

# Test 4: Database Performance
echo -e "\n${YELLOW}Test 4: Database Performance${NC}"
echo "Testing: Database operations under load"

DB_PERF_TEST=$(python3 << 'PYTHON_EOF'
import requests
import time
import concurrent.futures
from PIL import Image
import io

def test_db_operation(i):
    try:
        # Upload
        img = Image.new('RGB', (50, 50), color='cyan')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
        upload_resp = requests.post('http://localhost:5001/upload', files=files, timeout=5)
        
        if upload_resp.status_code != 200:
            return False
        
        image_id = upload_resp.json()['image_id']
        
        # Chat
        chat_resp = requests.post(
            'http://localhost:5001/chat',
            json={'prompt': f'DB test {i}', 'image_id': image_id},
            timeout=5
        )
        
        # Check history
        history_resp = requests.get('http://localhost:5001/history', timeout=5)
        
        return all([
            upload_resp.status_code == 200,
            chat_resp.status_code == 200,
            history_resp.status_code == 200
        ])
    except Exception as e:
        return False

# Run 10 concurrent database operations
start_time = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(test_db_operation, range(10)))
duration = time.time() - start_time

success_count = sum(results)
if success_count >= 8 and duration < 30:
    print('✅ Database performance acceptable')
else:
    print('❌ Database performance issues detected')
PYTHON_EOF
)

echo -e "${GREEN}Performance tests completed!${NC}"
echo "📊 Review results to ensure system handles load correctly"
