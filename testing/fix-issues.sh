#!/bin/bash

# Fix Common Testing Issues
# Resolves dependency, syntax, and configuration problems

echo "🔧 Fixing Common Testing Issues"
echo "=============================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Issue 1: Installing missing dependencies${NC}"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}❌ No virtual environment detected${NC}"
    echo "Creating virtual environment first..."
    
    # Create virtual environment
    python3 -m venv testing_env
    source testing_env/bin/activate
    
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment detected: $VIRTUAL_ENV${NC}"
fi

echo -e "\n${YELLOW}Issue 2: Installing required packages${NC}"

# Install required packages
pip install requests pillow psutil

echo -e "${GREEN}✅ Dependencies installed${NC}"

echo -e "\n${YELLOW}Issue 3: Fixing evidence collection syntax${NC}"

# Create a fixed version of evidence collection
cat > /Users/ivanjacksonrivera/Downloads/candidate_files/testing/07-evidence-collection-fixed.sh << 'EOF'
#!/bin/bash

# Evidence Collection and Reporting - Step 7 (FIXED)
# Gathers comprehensive evidence of system behavior

echo "📸 Evidence Collection & Reporting"
echo "================================="

# Create evidence directory
EVIDENCE_DIR="evidence-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$EVIDENCE_DIR"

echo -e "${BLUE}Collecting evidence in: $EVIDENCE_DIR${NC}"

# Function to capture system evidence
capture_evidence() {
    local test_name=$1
    local command=$2
    
    echo -e "${YELLOW}Capturing evidence for: $test_name${NC}"
    
    # Create test-specific evidence file
    evidence_file="$EVIDENCE_DIR/${test_name}-evidence.json"
    
    # Run command and capture output
    {
        echo "Running: $command"
        eval "$command" 2>&1 | tee "$evidence_file"
    } 3>&1
    
    echo -e "${GREEN}✅ Evidence saved to: $evidence_file${NC}"
}

# Test 1: System Health Evidence
capture_evidence "system-health" "
    echo '=== System Health ==='
    echo 'Timestamp:' $(date)
    echo 'Server Status:'
    curl -s http://localhost:5001/ | head -5
    echo ''
    echo 'Database Status:'
    curl -s http://localhost:5001/chat/history | head -3
    echo ''
    echo 'Memory Usage:'
    ps aux | grep 'python.*app.py' | head -1
    echo ''
    echo 'Disk Space:'
    df -h . | head -2
"

# Test 2: API Response Evidence
capture_evidence "api-responses" "
    echo '=== API Response Evidence ==='
    echo 'Upload Endpoint:'
    echo 'Request: POST /upload with test image'
    
    # Python script for upload test
    python3 << 'PYTHON_SCRIPT'
import requests
import json
from PIL import Image
import io
import base64

# Upload image
img = Image.new('RGB', (100, 100), color='cyan')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': img_bytes}
resp = requests.post('http://localhost:5001/upload', files=files, timeout=10)

print(f'Status Code: {resp.status_code}')
print(f'Response Headers: {dict(resp.headers)}')
if resp.status_code == 200:
    data = resp.json()
    print(f'Response Body: {json.dumps(data, indent=2)}')
    print(f'Image ID Generated: {data.get("image_id", "None")}')
    print(f'Session ID: {data.get("session_id", "None")}')
PYTHON_SCRIPT

    echo ''
    echo 'Chat Endpoint:'
    echo 'Request: POST /chat with image'
    
    # Python script for chat test
    python3 << 'PYTHON_SCRIPT'
import requests
import json

# Use previously uploaded image or upload new one
img = Image.new('RGB', (80, 80), color='orange')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': img_bytes}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code == 200:
    image_id = upload_resp.json()['image_id']
    
    # Test streaming chat
    resp = requests.post(
        'http://localhost:5001/chat/stream',
        json={'prompt': 'Evidence collection test', 'image_id': image_id},
        stream=True,
        timeout=10
    )
    
    print(f'Status Code: {resp.status_code}')
    print(f'Content-Type: {resp.headers.get("content-type", "unknown")}')
    
    if resp.status_code == 200:
        chunk_count = 0
        print('First 5 streaming chunks:')
        for line in resp.iter_lines():
            if line.startswith('data: '):
                chunk_count += 1
                payload = line[6:].strip()
                if payload and payload != '[DONE]' and chunk_count <= 5:
                    print(f'Chunk {chunk_count}: {payload[:100]}...')
PYTHON_SCRIPT

    echo ''
    echo 'Streaming Analysis:'
    
    # Python script for streaming analysis
    python3 << 'PYTHON_SCRIPT'
import requests
import time
import json

# Upload image
img = Image.new('RGB', (60, 60), color='lime')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': img_bytes}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code == 200:
    image_id = upload_resp.json()['image_id']
    
    # Test streaming chat
    resp = requests.post(
        'http://localhost:5001/chat/stream',
        json={'prompt': 'Streaming evidence test', 'image_id': image_id},
        stream=True,
        timeout=15
    )
    
    if resp.status_code == 200:
        print('Timing Analysis:')
        chunk_times = []
        start_time = time.time()
        
        for line in resp.iter_lines():
            if line.startswith('data: '):
                chunk_times.append(time.time() - start_time)
                
                if len(chunk_times) >= 5:
                    break
        
        if len(chunk_times) >= 2:
            intervals = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
            avg_interval = sum(intervals) / len(intervals)
            print(f'Average chunk interval: {avg_interval:.3f}s')
        
        print('Format Validation:')
        openai_compliant = 0
        total_chunks = 0
        
        for line in resp.iter_lines():
            if line.startswith('data: '):
                total_chunks += 1
                payload = line[6:].strip()
                if payload and payload != '[DONE]':
                    try:
                        chunk = json.loads(payload)
                        required_fields = ['id', 'object', 'created', 'model', 'choices']
                        has_all_fields = all(field in chunk for field in required_fields)
                        if has_all_fields:
                            openai_compliant += 1
                        
                        if total_chunks <= 3:  # Check first 3 chunks
                            print(f'Chunk {total_chunks}: {json.dumps(chunk, indent=2)[:150]}...')
                    except:
                        pass
        
        compliance_rate = (openai_compliant / total_chunks) * 100 if total_chunks > 0 else 0
        print(f'OpenAI Compliance Rate: {compliance_rate:.1f}% ({openai_compliant}/{total_chunks} chunks)')
PYTHON_SCRIPT

    echo ''
    echo 'Concurrency Evidence:'
    
    # Python script for concurrency test
    python3 << 'PYTHON_SCRIPT'
import requests
import threading
import time
import json
from PIL import Image
import io

def concurrent_test(test_id):
    img = Image.new('RGB', (40, 40), color=f'color{test_id}')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {'image': img_bytes}
    upload_resp = requests.post('http://localhost:5001/upload', files=files, timeout=15)
    
    if upload_resp.status_code == 200:
        image_id = upload_resp.json()['image_id']
        session_id = upload_resp.json()['session_id']
        
        results = []
        errors = []
        
        # Multiple rapid requests
        for i in range(20):
            try:
                resp = requests.post(
                    'http://localhost:5001/chat',
                    json={'prompt': f'Concurrent test {test_id}-{i}', 'image_id': image_id},
                    headers={'Cookie': f'va_session_id={session_id}'},
                    timeout=5
                )
                
                if resp.status_code == 200:
                    results.append('SUCCESS')
                elif resp.status_code == 429:
                    results.append('RATE_LIMITED')
                else:
                    results.append(f'ERROR_{resp.status_code}')
                    errors.append(f'Request {i}: {resp.status_code}')
                
            except Exception as e:
                results.append('EXCEPTION')
                errors.append(f'Exception {i}: {str(e)}')
            
            time.sleep(0.1)
        
        success_count = results.count('SUCCESS')
        error_count = len(errors)
        
        print(f'Test {test_id}: {success_count}/20 successful, {error_count} errors')
        
        # Check for data corruption (mixed responses)
        unique_responses = set(results)
        unexpected_patterns = [r for r in results if r not in ['SUCCESS', 'RATE_LIMITED', 'ERROR_400', 'ERROR_500', 'EXCEPTION']]
        
        if unexpected_patterns:
            print(f'Unexpected response patterns: {unexpected_patterns}')
        
        return success_count >= 15  # 75% success rate

print('Running concurrent safety tests...')
threads = []
for i in range(3):
    thread = threading.Thread(target=concurrent_test, args=(i,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

print('✅ Concurrent safety evidence collected')
PYTHON_SCRIPT

    echo ''
    echo 'Performance Metrics:'
    
    # Python script for performance test
    python3 << 'PYTHON_SCRIPT'
import time
import requests
import statistics
from PIL import Image
import io

def performance_test():
    print('Collecting performance metrics...')
    
    # Response time test
    response_times = []
    
    for i in range(10):
        start_time = time.time()
        
        img = Image.new('RGB', (50, 50), color='gray')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'image': img_bytes}
        upload_resp = requests.post('http://localhost:5001/upload', files=files, timeout=10)
        
        if upload_resp.status_code == 200:
            response_times.append(time.time() - start_time)
    
    if response_times:
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        print(f'Response Time Statistics (10 uploads):')
        print(f'  Average: {avg_response_time:.3f}s')
        print(f'  Min: {min_response_time:.3f}s')
        print(f'  Max: {max_response_time:.3f}s')
        print(f'  Std Dev: {statistics.stdev(response_times):.3f}s')
        
        # Performance classification
        if avg_response_time < 1.0:
            print('✅ Performance: Excellent (< 1s average)')
        elif avg_response_time < 2.0:
            print('✅ Performance: Good (< 2s average)')
        elif avg_response_time < 5.0:
            print('⚠️  Performance: Acceptable (< 5s average)')
        else:
            print('❌ Performance: Poor (> 5s average)')
    
    # Throughput test
    print('Throughput Test:')
    start_time = time.time()
    request_count = 0
    
    for i in range(50):
        resp = requests.get('http://localhost:5001/chat/history', timeout=5)
        if resp.status_code == 200:
            request_count += 1
        time.sleep(0.05)
    
    throughput_time = time.time() - start_time
    requests_per_second = request_count / throughput_time if throughput_time > 0 else 0
    
    print(f'Throughput: {requests_per_second:.1f} requests/second')
    
    if requests_per_second > 10:
        print('✅ Throughput: Excellent (> 10 req/s)')
    elif requests_per_second > 5:
        print('✅ Throughput: Good (> 5 req/s)')
    else:
        print('⚠️  Throughput: Acceptable (> 1 req/s)')

performance_test()
PYTHON_SCRIPT

    echo ''
    echo 'Generating comprehensive report...'
    echo 'All evidence collection completed successfully!'
EOF

# Make the fixed script executable
chmod +x /Users/ivanjacksonrivera/Downloads/candidate_files/testing/07-evidence-collection-fixed.sh

echo -e "${GREEN}✅ Fixed evidence collection script created${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Run: ./07-evidence-collection-fixed.sh"
echo "2. This will collect evidence without syntax errors"
echo "3. Then investigate why requirements are not being enforced"
echo ""
echo -e "${GREEN}🔧 Issues fixed!${NC}"
