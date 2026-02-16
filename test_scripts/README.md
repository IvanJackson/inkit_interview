# Test Scripts

Manual test scripts for validating the Visual Assistant API implementation.

## Running Tests

All tests should be run from the project root directory:

```bash
# Make scripts executable
chmod +x test_scripts/*.py

# Run individual tests
python3 test_scripts/test_app_init.py
python3 test_scripts/test_upload_basic.py
python3 test_scripts/test_chat_workflow.py
python3 test_scripts/test_validation.py
python3 test_scripts/test_session_management.py
python3 test_scripts/test_openai_format.py
```

## Test Coverage

### test_app_init.py
- Flask app initialization
- Configuration loading
- Route registration
- Blueprint setup

### test_upload_basic.py
- Basic image upload
- File validation
- Vision analysis generation
- Response format

### test_chat_workflow.py
- Complete upload → chat flow
- Session-based image context
- Chat without explicit image IDs
- Chat with explicit image ID override
- Error handling for missing images

### test_validation.py
- Missing file validation
- Empty filename validation
- Unsupported file type (415)
- Missing prompt validation
- XSS/injection detection

### test_session_management.py
- Session creation on upload
- Session persistence across requests
- Session isolation (browser tabs)
- Session restoration
- Cookie management

### test_openai_format.py
- Vision analysis format compliance
- Chat completion format compliance
- Error response format compliance
- Required field validation
- OpenAI client library compatibility

## Quick Test All

Run all tests in sequence:

```bash
for script in test_scripts/test_*.py; do
    echo "Running $script..."
    python3 "$script" || exit 1
    echo "---"
done
echo "✅ All tests passed!"
```

## Notes

- Tests use the 'testing' config which disables delays
- Each test creates its own test client
- Tests are independent and can run in any order
- Exit code 0 = success, 1 = failure
