# Testing Guide

## Quick Start

### Run All Tests (Recommended)
```bash
cd testing
./run-complete-test-suite.sh
```

This master script runs **all 8 test suites** in sequence:
1. ✅ Core API Tests
2. ✅ Image Requirement Enforcement
3. ✅ Integration Tests
4. ✅ Performance Tests
5. ✅ Requirements Validation
6. ✅ Advanced Automated Tests
7. ✅ Evidence Collection
8. ✅ Frontend Tests (manual)

---

## Individual Test Scripts

### Automated Tests

| Script | Purpose | Runtime |
|--------|---------|---------|
| `01-core-api-tests.sh` | Core API endpoints | ~30s |
| `test-image-requirement.sh` | Image requirement enforcement | ~10s |
| `03-integration-tests.sh` | End-to-end workflows | ~45s |
| `04-performance-tests.sh` | Load and stress testing | ~60s |
| `05-requirements-validation.sh` | Requirements compliance | ~40s |
| `06-advanced-automated-tests.sh` | Complex scenarios | ~90s |
| `07-evidence-collection.sh` | Evidence gathering | ~30s |

### Manual Tests

| Script | Purpose |
|--------|---------|
| `02-frontend-tests.html` | UI component testing (browser) |

---

## Running Individual Tests

```bash
cd testing

# Run a specific test
./01-core-api-tests.sh

# Run quick validation
./test-image-requirement.sh

# Run performance tests
./04-performance-tests.sh
```

---

## Alternative Test Runners

### Quick Start (Fast Setup)
```bash
./quick-start.sh
```
Sets up environment and runs core tests only.

### Direct Runner (No Pauses)
```bash
./run-tests-direct.sh
```
Runs tests without interactive pauses.

### Original Runner (Interactive)
```bash
./run-all-tests.sh
```
Original test runner with manual pauses between suites.

---

## Prerequisites

**Before running tests:**

1. **Start the app:**
   ```bash
   cd /Users/ivanjacksonrivera/Downloads/candidate_files
   python3 run.py
   ```

2. **Verify app is running:**
   ```bash
   curl http://localhost:5001/
   ```

3. **Install test dependencies (if needed):**
   ```bash
   cd testing
   ./install-deps.sh
   ```

---

## Test Output

### Success Indicators
- ✅ Green checkmarks for passed tests
- 📊 Summary with pass/fail counts
- 📁 Evidence collected in `evidence-*/` directories

### Failure Indicators
- ❌ Red X marks for failed tests
- Exit codes > 0
- Error messages in terminal

---

## Troubleshooting

### App Not Running
```bash
# Error: Connection refused
# Solution: Start the app first
cd /Users/ivanjacksonrivera/Downloads/candidate_files
python3 run.py
```

### Missing Dependencies
```bash
# Error: ImportError or command not found
# Solution: Install dependencies
cd testing
./install-deps.sh
```

### Permission Denied
```bash
# Error: Permission denied
# Solution: Make scripts executable
chmod +x *.sh
```

### Tests Hanging
- Press `Ctrl+C` to stop
- Check if app is responsive: `curl http://localhost:5001/`
- Restart app if needed

---

## Test Evidence

Evidence is automatically collected in timestamped directories:
```
testing/evidence-YYYYMMDD-HHMMSS/
├── streaming-test.log
├── concurrent-db-test.log
├── cache-performance.log
├── rate-limit-test.log
└── memory-usage.log
```

---

## CI/CD Integration

For automated testing in CI/CD pipelines:

```bash
# Non-interactive mode
cd testing
./run-tests-direct.sh

# Check exit code
if [ $? -eq 0 ]; then
    echo "All tests passed"
else
    echo "Tests failed"
    exit 1
fi
```

---

## Test Coverage

The complete test suite validates:

- ✅ **API Endpoints**: All REST endpoints functional
- ✅ **Image Upload**: File validation, size limits, format support
- ✅ **Chat**: Prompt validation, streaming, history
- ✅ **Requirements**: All FR-001 through FR-037 enforced
- ✅ **Performance**: Load handling, rate limiting, caching
- ✅ **Concurrency**: Thread safety, database integrity
- ✅ **Error Handling**: Graceful failures, clear messages
- ✅ **Frontend**: UI components, user interactions

---

## Quick Reference

```bash
# Run everything
./run-complete-test-suite.sh

# Run core tests only
./01-core-api-tests.sh

# Check image requirement
./test-image-requirement.sh

# Performance testing
./04-performance-tests.sh

# Collect evidence
./07-evidence-collection.sh

# Frontend testing
open http://localhost:5001/testing/02-frontend-tests.html
```

---

## Support

For issues or questions:
1. Check server logs
2. Review test output above failed tests
3. Verify app configuration in `config.py`
4. Check `testing/README.md` for detailed documentation
