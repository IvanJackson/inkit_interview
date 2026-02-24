#!/bin/bash

# Core API Tests - Step 1
# Tests fundamental API functionality

echo "🧪 Core API Tests"
echo "=================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: Health Check
echo -e "\n${YELLOW}Test 1: Health Check${NC}"
curl -s "http://localhost:5001/" | grep -q "Visual Assistant" && \
    echo -e "${GREEN}✅ Health endpoint working${NC}" || \
    echo -e "${RED}❌ Health endpoint failed${NC}"

# Test 2: Image Upload
echo -e "\n${YELLOW}Test 2: Image Upload${NC}"
# Create a test image
python3 << 'PYTHON_EOF'
import requests
from PIL import Image
import io

# Create a simple test image
img = Image.new('RGB', (100, 100), color='blue')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code == 200:
    data = upload_resp.json()
    print(f' Upload successful: {data["image_id"]}')
else:
    print(f' Upload failed: {upload_resp.status_code}')
PYTHON_EOF

# Test 3: Chat Without Image (Should Fail)
echo -e "\n${YELLOW}Test 3: Chat Without Image${NC}"
response=$(curl -s -w "%{http_code}" -o /dev/null \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello"}' \
    "http://localhost:5001/chat/stream")

if [ "$response" = "400" ]; then
    echo -e "${GREEN}✅ Correctly rejected chat without image${NC}"
else
    echo -e "${RED}❌ Should have rejected chat without image (got $response)${NC}"
fi

# Test 4: Chat With Image
echo -e "\n${YELLOW}Test 4: Chat With Image${NC}"
# First upload an image to get image_id
IMAGE_ID=$(python3 << 'PYTHON_EOF'
import requests
from PIL import Image
import io

img = Image.new('RGB', (50, 50), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
response = requests.post('http://localhost:5001/upload', files=files)
if response.status_code == 200:
    print(response.json()['image_id'])
else:
    print('ERROR')
PYTHON_EOF
)

if [ "$IMAGE_ID" != "ERROR" ]; then
    # Test streaming chat with image
    response=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"What do you see?\", \"image_id\": \"$IMAGE_ID\"}" \
        "http://localhost:5001/chat/stream")
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✅ Chat with image working${NC}"
    else
        echo -e "${RED}❌ Chat with image failed (got $response)${NC}"
    fi
else
    echo -e "${RED} Failed to upload test image${NC}"
fi

# Test 5: OpenAI Format Check
echo -e "\n${YELLOW}Test 5: OpenAI Format Compliance${NC}"
# Test streaming response format
python3 << 'PYTHON_EOF'
import requests
import json
from PIL import Image
import io

# Upload image first
img = Image.new('RGB', (50, 50), color='green')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code == 200:
    image_id = upload_resp.json()['image_id']
    
    # Test streaming chat
    resp = requests.post(
        'http://localhost:5001/chat/stream',
        json={'prompt': 'Format test', 'image_id': image_id},
        stream=True,
        timeout=10
    )
    
    if resp.status_code == 200:
        # Read first few chunks and validate format
        chunk_count = 0
        format_valid = True
        openai_compliant = 0
        
        for line in resp.iter_lines():
            if line:
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                if line_str.startswith('data: '):
                    chunk_count += 1
                    payload = line_str[6:].strip()
                    if payload and payload != '[DONE]':
                        try:
                            chunk = json.loads(payload)
                            
                            # Validate required OpenAI fields
                            required_fields = ['id', 'object', 'created', 'model', 'choices']
                            for field in required_fields:
                                if field not in chunk:
                                    format_valid = False
                                    print(f'Missing field: {field}')
                            
                            # Validate object field
                            if chunk.get('object') != 'chat.completion.chunk':
                                format_valid = False
                                print(f'Invalid object: {chunk.get("object")}')
                            
                            # Validate choices structure
                            if 'choices' not in chunk or not chunk['choices']:
                                format_valid = False
                                print('Missing or invalid choices')
                            
                            # Count compliant chunks
                            if format_valid:
                                openai_compliant += 1
                            
                            if chunk_count <= 3:  # Check first 3 chunks
                                print(f'Chunk {chunk_count}: {json.dumps(chunk, indent=2)[:150]}...')
                        
                        except:
                            pass
        
        compliance_rate = (openai_compliant / chunk_count) * 100 if chunk_count > 0 else 0
        print(f'OpenAI Compliance Rate: {compliance_rate:.1f}% ({openai_compliant}/{chunk_count} chunks)')
        
        if format_valid and compliance_rate >= 90:
            print(' Streaming format fully compliant')
        else:
            print(' OpenAI format issues detected')
    else:
        print(' Streaming test failed')
PYTHON_EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN} OpenAI format test completed${NC}"
else
    echo -e "${RED} OpenAI format test failed${NC}"
fi

echo -e "\n${GREEN}Core API tests completed!${NC}"
