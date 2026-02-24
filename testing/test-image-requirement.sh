#!/bin/bash

# Test Image Requirement Enforcement
# Verifies that chat without image is properly rejected

echo "🔍 Testing Image Requirement Enforcement"
echo "========================="

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Test 1: Try chat without image (should fail)
echo -e "\n${RED}Test 1: Chat without image (should fail)${NC}"
response=$(curl -s -w "%{http_code}" -o /dev/null \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello without image"}' \
    "http://localhost:5001/chat")

if [ "$response" = "400" ]; then
    echo -e "${GREEN}✅ Chat without image correctly rejected (400)${NC}"
else
    echo -e "${RED}❌ Chat without image should fail (got $response)${NC}"
fi

# Test 2: Try chat with image (should succeed)
echo -e "\n${GREEN}Test 2: Chat with image (should succeed)${NC}"

# First upload an image
IMAGE_ID=$(python3 << 'PYTHON_EOF'
import requests
from PIL import Image
import io

img = Image.new('RGB', (50, 50), color='green')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code == 200:
    print(upload_resp.json().get('image_id', 'ERROR'))
else:
    print('ERROR')
PYTHON_EOF
)

if [ "$IMAGE_ID" != "ERROR" ] && [ -n "$IMAGE_ID" ]; then
    # Try chat with the uploaded image
    CHAT_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"What do you see?\", \"image_id\": \"$IMAGE_ID\"}" \
        "http://localhost:5001/chat")
    
    if [ "$CHAT_RESPONSE" = "200" ]; then
        echo -e "${GREEN}✅ Chat with image succeeded (200)${NC}"
    else
        echo -e "${RED}❌ Chat with image failed (got $CHAT_RESPONSE)${NC}"
    fi
else
    echo -e "${RED}❌ Failed to upload test image${NC}"
    CHAT_RESPONSE="SKIP"
fi

echo ""
echo -e "${GREEN}Image Requirement Enforcement Test Results:${NC}"
echo "• Chat without image: $([ "$response" = "400" ] && echo 'PASS' || echo 'FAIL')"
echo "• Chat with image: $([ "$CHAT_RESPONSE" = "200" ] && echo 'PASS' || echo 'FAIL')"

if [ "$response" = "400" ] && [ "$CHAT_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ Image requirement is working correctly${NC}"
else
    echo -e "${RED}❌ Image requirement is NOT working correctly${NC}"
fi
