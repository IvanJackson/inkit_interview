# Visual Assistant API Testing Suite

## Overview
Comprehensive testing suite to validate all project components step by step, with focus on **automated evidence collection** for complex scenarios that can't be easily validated through UI.

## Test Categories

### 1. Core API Tests (`01-core-api-tests.sh`)
- Health check endpoint
- Image upload functionality  
- Chat rejection without image
- Chat success with image
- OpenAI streaming format compliance

### 2. Frontend Tests (`02-frontend-tests.html`) 🌐
- **Manual UI tests** for:
  - Image upload interface
  - New conversation warnings
  - Chat without image rejection
  - Streaming text display
  - History panel functionality
- **Automated tests** for:
  - SSE format validation
  - Console logging verification

### 3. Integration Tests (`03-integration-tests.sh`)
- Complete conversation workflow
- Session persistence across requests
- Error handling for invalid inputs
- Rate limiting verification

### 4. Performance Tests (`04-performance-tests.sh`) ⚡
- **Concurrent user safety** - Multiple simultaneous requests
- **File safety** - No overwrites with UUID-based naming
- **Rate limiting** - Upload (20/hr) and chat (100/min) limits
- **Database performance** - Multiple concurrent conversations

### 5. Requirements Validation (`05-requirements-validation.sh`) 📋
- **Requirement 1**: No shared state issues
- **Requirement 3**: OpenAI format compliance  
- **Requirements 4,5,6**: Image enforcement rules
- **Requirement 6**: One image per conversation

### 6. Advanced Automated Tests (`06-advanced-automated-tests.sh`) 🔬
- **Streaming Reconnection**: Tests SSE reconnection with proper event ID handling
- **Concurrent Database Access**: Validates database consistency under concurrent load
- **Cache Performance**: Tests caching layer efficiency and invalidation
- **Rate Limiting Evidence**: Collects clear evidence of rate limiting behavior
- **Memory and Resource Management**: Monitors resource usage during operations

### 7. Evidence Collection (`07-evidence-collection-fixed.sh`) 📸
- **Comprehensive Evidence Gathering**: Collects detailed system behavior evidence
- **Performance Metrics**: Response times, throughput, statistics
- **Automated Reports**: JSON-formatted evidence files with timestamps
- **Timestamped Evidence**: All evidence saved with timestamps

## 🔧 Environment Setup

### Quick Start (`quick-start.sh`) 🚀
**Simple entry point that:**
- Checks if app is running
- Creates/activates virtual environment if needed
- Installs required dependencies (requests, pillow, psutil)
- Starts comprehensive test suite with countdown timer

### Dependency Installation (`install-deps.sh`) 📦
**Standalone dependency installer** for testing environment

## Usage

### Primary Method (Recommended):
```bash
cd testing
./quick-start.sh
```

### Alternative Methods:

#### If Environment Setup Issues:
```bash
./install-deps.sh          # Install dependencies only
./run-all-tests.sh         # Then run tests (if env ready)
```

#### Manual Test Execution:
```bash
./01-core-api-tests.sh       # Individual test suites
./02-frontend-tests.html     # Open in browser for manual UI tests
./03-integration-tests.sh
./04-performance-tests.sh
./05-requirements-validation.sh
./06-advanced-automated-tests.sh
./07-evidence-collection-fixed.sh
```

## Key Features

✅ **Automated Evidence Collection** - All tests generate JSON evidence files  
✅ **Performance Metrics** - Response times, throughput, memory usage  
✅ **Concurrency Testing** - Multiple simultaneous requests with data integrity checks  
✅ **Rate Limiting Proof** - Clear evidence of 429 responses and request patterns  
✅ **Requirements Compliance** - Validates all updated requirements with detailed logs  
✅ **Virtual Environment Support** - Automatic setup and dependency management  
✅ **Error Handling** - Graceful failure handling and clear error reporting  

## Notes

- **Focus on Complex Scenarios**: Advanced tests specifically target scenarios that cannot be easily validated through UI, providing ample evidence of system behavior.
- **Evidence-Based Validation**: All automated tests collect comprehensive evidence with timestamps and detailed metrics.
- **Environment Independence**: Testing framework works regardless of existing virtual environment setup.
- **Fixed Common Issues**: Resolved permission problems, dependency installation, and Python syntax errors.

## Test Execution Order

For comprehensive validation, run tests in this order:
1. **Environment Setup** (if needed)
2. **Core API Tests** (basic functionality)
3. **Requirements Validation** (compliance checking)
4. **Integration Tests** (workflow validation)
5. **Performance Tests** (load testing)
6. **Advanced Automated Tests** (complex scenarios)
7. **Evidence Collection** (detailed analysis)
