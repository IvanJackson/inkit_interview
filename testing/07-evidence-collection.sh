#!/bin/bash

# Evidence Collection and Reporting - Step 7
# Gathers comprehensive evidence of system behavior

echo "📸 Evidence Collection & Reporting"
echo "================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create evidence directory
EVIDENCE_DIR="evidence-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$EVIDENCE_DIR"

echo -e "${BLUE}Collecting evidence in: $EVIDENCE_DIR${NC}"

# Test 1: System Health Evidence
echo -e "\n${YELLOW}Capturing evidence for: system-health${NC}"
{
    echo '=== System Health ==='
    echo "Timestamp: $(date)"
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
} | tee "$EVIDENCE_DIR/system-health-evidence.json"
echo -e "${GREEN}✅ Evidence saved to: $EVIDENCE_DIR/system-health-evidence.json${NC}"

# Test 2: API Response Evidence
echo -e "\n${YELLOW}Capturing evidence for: api-responses${NC}"
python3 << 'PYTHON_EOF' | tee "$EVIDENCE_DIR/api-responses-evidence.json"
import requests
import json
from PIL import Image
import io

print('=== API Response Evidence ===')
print('Upload Endpoint:')
print('Request: POST /upload with test image')

img = Image.new('RGB', (100, 100), color='cyan')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
resp = requests.post('http://localhost:5001/upload', files=files, timeout=10)

print(f'Status Code: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(f'Response Body: {json.dumps(data, indent=2)}')
    print(f'Image ID Generated: {data.get("image_id", "None")}')
    print(f'Session ID: {data.get("session_id", "None")}')

    print('')
    print('Chat Endpoint:')
    image_id = data['image_id']

    chat_resp = requests.post(
        'http://localhost:5001/chat/stream',
        json={'prompt': 'Evidence collection test', 'image_id': image_id},
        stream=True,
        timeout=10
    )

    print(f'Status Code: {chat_resp.status_code}')
    print(f'Content-Type: {chat_resp.headers.get("content-type", "unknown")}')

    if chat_resp.status_code == 200:
        chunk_count = 0
        print('First 5 streaming chunks:')
        for line in chat_resp.iter_lines():
            if line:
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                if line_str.startswith('data: '):
                    chunk_count += 1
                    payload = line_str[6:].strip()
                    if payload and payload != '[DONE]' and chunk_count <= 5:
                        print(f'Chunk {chunk_count}: {payload[:100]}...')
PYTHON_EOF
echo -e "${GREEN}✅ Evidence saved to: $EVIDENCE_DIR/api-responses-evidence.json${NC}"

# Test 3: Streaming Evidence
echo -e "\n${YELLOW}Capturing evidence for: streaming-behavior${NC}"
python3 << 'PYTHON_EOF' | tee "$EVIDENCE_DIR/streaming-behavior-evidence.json"
import requests
import time
import json
from PIL import Image
import io

print('=== Streaming Behavior Evidence ===')

img = Image.new('RGB', (60, 60), color='lime')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
upload_resp = requests.post('http://localhost:5001/upload', files=files)

if upload_resp.status_code == 200:
    image_id = upload_resp.json()['image_id']

    print('Streaming Analysis:')
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
        openai_compliant = 0
        total_chunks = 0

        for line in resp.iter_lines():
            if line:
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                if line_str.startswith('data: '):
                    total_chunks += 1
                    chunk_times.append(time.time() - start_time)
                    payload = line_str[6:].strip()
                    if payload and payload != '[DONE]':
                        try:
                            chunk = json.loads(payload)
                            required_fields = ['id', 'object', 'created', 'model', 'choices']
                            if all(field in chunk for field in required_fields):
                                openai_compliant += 1
                            if total_chunks <= 3:
                                print(f'Chunk {total_chunks}: {json.dumps(chunk, indent=2)[:150]}...')
                        except:
                            pass

        if len(chunk_times) >= 2:
            intervals = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
            avg_interval = sum(intervals) / len(intervals)
            print(f'Average chunk interval: {avg_interval:.3f}s')

        compliance_rate = (openai_compliant / total_chunks) * 100 if total_chunks > 0 else 0
        print(f'OpenAI Compliance Rate: {compliance_rate:.1f}% ({openai_compliant}/{total_chunks} chunks)')
else:
    print('Upload failed')
PYTHON_EOF
echo -e "${GREEN}✅ Evidence saved to: $EVIDENCE_DIR/streaming-behavior-evidence.json${NC}"

# Test 4: Concurrency Evidence
echo -e "\n${YELLOW}Capturing evidence for: concurrency-safety${NC}"
python3 << 'PYTHON_EOF' | tee "$EVIDENCE_DIR/concurrency-safety-evidence.json"
import requests
import threading
import time
import json
from PIL import Image
import io

print('=== Concurrency Safety Evidence ===')

def concurrent_test(test_id):
    colors = ['red', 'blue', 'green']
    img = Image.new('RGB', (40, 40), color=colors[test_id % len(colors)])
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
    upload_resp = requests.post('http://localhost:5001/upload', files=files, timeout=15)

    if upload_resp.status_code == 200:
        image_id = upload_resp.json()['image_id']
        session_id = upload_resp.json().get('session_id', '')

        results = []
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
            except Exception as e:
                results.append('EXCEPTION')
            time.sleep(0.1)

        success_count = results.count('SUCCESS')
        print(f'Test {test_id}: {success_count}/20 successful')

print('Running concurrent safety tests...')
threads = []
for i in range(3):
    thread = threading.Thread(target=concurrent_test, args=(i,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

print('✅ Concurrent safety evidence collected')
PYTHON_EOF
echo -e "${GREEN}✅ Evidence saved to: $EVIDENCE_DIR/concurrency-safety-evidence.json${NC}"

# Test 5: Performance Metrics
echo -e "\n${YELLOW}Capturing evidence for: performance-metrics${NC}"
python3 << 'PYTHON_EOF' | tee "$EVIDENCE_DIR/performance-metrics-evidence.json"
import time
import requests
import statistics
from PIL import Image
import io

print('=== Performance Metrics Evidence ===')
print('Collecting performance metrics...')

response_times = []
for i in range(10):
    start_time = time.time()
    img = Image.new('RGB', (50, 50), color='gray')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
    upload_resp = requests.post('http://localhost:5001/upload', files=files, timeout=10)

    if upload_resp.status_code == 200:
        response_times.append(time.time() - start_time)

if response_times:
    avg_response_time = statistics.mean(response_times)
    print(f'Response Time Statistics ({len(response_times)} uploads):')
    print(f'  Average: {avg_response_time:.3f}s')
    print(f'  Min: {min(response_times):.3f}s')
    print(f'  Max: {max(response_times):.3f}s')
    if len(response_times) > 1:
        print(f'  Std Dev: {statistics.stdev(response_times):.3f}s')

    if avg_response_time < 1.0:
        print('✅ Performance: Excellent (< 1s average)')
    elif avg_response_time < 2.0:
        print('✅ Performance: Good (< 2s average)')
    elif avg_response_time < 5.0:
        print('⚠️  Performance: Acceptable (< 5s average)')
    else:
        print('❌ Performance: Poor (> 5s average)')

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
PYTHON_EOF
echo -e "${GREEN}✅ Evidence saved to: $EVIDENCE_DIR/performance-metrics-evidence.json${NC}"

# Generate comprehensive report
echo -e "\n${GREEN}Evidence collection completed!${NC}"
echo "📁 Evidence saved in: $EVIDENCE_DIR"
echo ""
echo "📊 Available Evidence Files:"
ls -la "$EVIDENCE_DIR"

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Review evidence files for detailed analysis"
echo "2. Check for any performance bottlenecks"
echo "3. Validate all requirements compliance"
echo "4. Use evidence for debugging and optimization"
echo ""
echo -e "${GREEN}✅ Evidence collection complete!${NC}"
