#!/bin/bash

# Integration Tests - Step 3
# Tests end-to-end workflows and system integration

echo "🔗 Integration Tests"
echo "==================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: Complete Conversation Workflow
echo -e "\n${YELLOW}Test 1: Complete Conversation Workflow${NC}"
echo "Testing: Upload → Chat → History → New Conversation"

# Step 1: Upload image and chat
echo "Step 1: Uploading image and starting conversation..."
FIRST_IMAGE_ID=$(python3 << 'PYTHON_EOF'
import requests
import json
from PIL import Image
import io

img = Image.new('RGB', (100, 100), color='purple')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)
if upload_resp.status_code == 200:
    image_id = upload_resp.json()['image_id']
    print(image_id)
else:
    print('ERROR')
PYTHON_EOF
)

if [ "$FIRST_IMAGE_ID" != "ERROR" ]; then
    echo -e "${GREEN}✅ First image uploaded: $FIRST_IMAGE_ID${NC}"
    
    # Step 2: Send chat message
    echo "Step 2: Sending chat message..."
    CHAT_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"What do you see in this image?\", \"image_id\": \"$FIRST_IMAGE_ID\"}" \
        "http://localhost:5001/chat")
    
    if echo "$CHAT_RESPONSE" | grep -q "choices"; then
        echo -e "${GREEN}✅ Chat response received${NC}"
    else
        echo -e "${RED}❌ Chat response failed${NC}"
    fi
    
    # Step 3: Check history
    echo "Step 3: Checking conversation history..."
    HISTORY_CHECK=$(curl -s "http://localhost:5001/chat/history?image_id=$FIRST_IMAGE_ID")
    
    if echo "$HISTORY_CHECK" | grep -q '"messages"'; then
        MESSAGE_COUNT=$(echo "$HISTORY_CHECK" | python3 -c "
import sys, json
data = json.load(sys.stdin)
conv = data.get('conversations', [{}])[0]
print(len(conv.get('messages', [])))
")
        echo -e "${GREEN}✅ History shows $MESSAGE_COUNT messages${NC}"
    else
        echo -e "${RED}❌ History check failed${NC}"
    fi
    
    # Step 4: Upload second image (new conversation)
    echo "Step 4: Uploading second image (should start new conversation)..."
    SECOND_IMAGE_ID=$(python3 << 'PYTHON_EOF'
import requests
from PIL import Image
import io

img = Image.new('RGB', (80, 80), color='orange')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)
if upload_resp.status_code == 200:
    image_id = upload_resp.json()['image_id']
    print(image_id)
else:
    print('ERROR')
PYTHON_EOF
)
    
    if [ "$SECOND_IMAGE_ID" != "ERROR" ]; then
        echo -e "${GREEN}✅ Second image uploaded: $SECOND_IMAGE_ID${NC}"
        
        # Step 5: Verify two separate conversations exist
        echo "Step 5: Verifying separate conversations..."
        TOTAL_HISTORY=$(curl -s "http://localhost:5001/chat/history?limit=100")
        
        CONV_COUNT=$(echo "$TOTAL_HISTORY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data.get('conversations', [])))
")
        
        if [ "$CONV_COUNT" -ge 2 ]; then
            echo -e "${GREEN}✅ Two separate conversations exist${NC}"
        else
            echo -e "${RED}❌ Expected 2 conversations, found $CONV_COUNT${NC}"
        fi
    else
        echo -e "${RED}❌ Second image upload failed${NC}"
    fi
else
    echo -e "${RED}❌ First image upload failed${NC}"
fi

# Test 2: Session Persistence
echo -e "\n${YELLOW}Test 2: Session Persistence${NC}"
echo "Testing: Session survives app restart and conversation continuity"

# Create a session with conversation
SESSION_ID=$(python3 << 'PYTHON_EOF'
import requests
from PIL import Image
import io

img = Image.new('RGB', (60, 60), color='cyan')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)
if upload_resp.status_code == 200:
    session_id = upload_resp.cookies.get('va_session_id', '')
    if session_id:
        print(session_id)
    else:
        print('ERROR')
else:
    print('ERROR')
PYTHON_EOF
)

if [ "$SESSION_ID" != "ERROR" ]; then
    echo -e "${GREEN}✅ Session created: $SESSION_ID${NC}"
    
    # Send a message to create history (must include image_id)
    IMAGE_FOR_SESSION=$(python3 << 'PYTHON_EOF'
import requests
from PIL import Image
import io

img = Image.new('RGB', (50, 50), color='magenta')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)
if upload_resp.status_code == 200:
    print(upload_resp.json()['image_id'])
else:
    print('ERROR')
PYTHON_EOF
)
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"Session test message\", \"image_id\": \"$IMAGE_FOR_SESSION\"}" \
        "http://localhost:5001/chat" > /dev/null
    
    # Check history with session filter
    SESSION_HISTORY=$(curl -s "http://localhost:5001/chat/history?session_id=$SESSION_ID")
    
    if echo "$SESSION_HISTORY" | grep -q "$SESSION_ID"; then
        echo -e "${GREEN}✅ Session persistence working${NC}"
    else
        echo -e "${RED}❌ Session persistence failed${NC}"
    fi
else
    echo -e "${RED}❌ Session creation failed${NC}"
fi

# Test 3: Error Handling
echo -e "\n${YELLOW}Test 3: Error Handling${NC}"
echo "Testing: Invalid requests and edge cases"

# Test invalid image upload (send text data as image)
echo "Testing invalid image upload..."
echo "not an image" > /tmp/fake_image.jpg
INVALID_UPLOAD=$(curl -s -w "%{http_code}" -o /dev/null \
    -F "image=@/tmp/fake_image.jpg" \
    "http://localhost:5001/upload")

if [ "$INVALID_UPLOAD" = "400" ] || [ "$INVALID_UPLOAD" = "415" ]; then
    echo -e "${GREEN}✅ Invalid image correctly rejected ($INVALID_UPLOAD)${NC}"
else
    echo -e "${RED}❌ Should reject invalid image (got $INVALID_UPLOAD)${NC}"
fi

# Test chat without image (should be rejected)
echo "Testing chat without image..."
NO_IMAGE_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
    -H "Content-Type: application/json" \
    -d '{"prompt": "test without image"}' \
    "http://localhost:5001/chat")

if [ "$NO_IMAGE_RESPONSE" = "400" ]; then
    echo -e "${GREEN}✅ Chat without image correctly rejected (400)${NC}"
else
    echo -e "${RED}❌ Should reject chat without image (got $NO_IMAGE_RESPONSE)${NC}"
fi

# Test rate limiting
echo "Testing rate limiting..."
for i in {1..3}; do
    RATE_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "Content-Type: application/json" \
        -d '{"prompt": "Rate limit test '$i'"}' \
        "http://localhost:5001/chat")
    
    echo "Request $i: $RATE_RESPONSE"
    sleep 0.1
done

echo -e "\n${GREEN}Integration tests completed!${NC}"
echo "📊 Check the results above to validate system functionality"
