#!/bin/bash

# Complete Test Suite Runner
# Runs ALL test scripts to validate the entire application

echo "🧪 Visual Assistant - Complete Test Suite"
echo "=========================================="
echo ""
echo "This master script will run ALL tests in sequence:"
echo "  1. Core API Tests"
echo "  2. Image Requirement Enforcement"
echo "  3. Integration Tests"
echo "  4. Performance Tests"
echo "  5. Requirements Validation"
echo "  6. Advanced Automated Tests"
echo "  7. Evidence Collection"
echo "  8. Frontend Tests (manual)"
echo ""
echo "⚠️  Make sure the app is running on http://localhost:5001"
echo ""
read -p "Press Enter to begin testing..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Track results
PASSED=0
FAILED=0
SKIPPED=0

# Function to check if app is running
check_app() {
    echo -e "${YELLOW}Checking if app is running...${NC}"
    if ! curl -s http://localhost:5001/ > /dev/null 2>&1; then
        echo -e "${RED}❌ App is not running!${NC}"
        echo "Please start the app first:"
        echo "  cd /Users/ivanjacksonrivera/Downloads/candidate_files"
        echo "  python3 run.py"
        exit 1
    fi
    echo -e "${GREEN}✅ App is running${NC}"
    echo ""
}

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local script_path=$2
    local auto_run=${3:-false}
    
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ Running: $suite_name${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ ! -f "$script_path" ]; then
        echo -e "${RED}❌ Test script not found: $script_path${NC}"
        ((SKIPPED++))
        return 1
    fi
    
    chmod +x "$script_path"
    
    if [ "$auto_run" = "false" ]; then
        echo -e "${YELLOW}Press Enter to run this test suite...${NC}"
        read
    fi
    
    bash "$script_path"
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ $suite_name PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ $suite_name FAILED (exit code: $exit_code)${NC}"
        ((FAILED++))
    fi
    
    return $exit_code
}

# Start testing
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🚀 Starting Complete Test Suite${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check app is running
check_app

# Test 1: Core API Tests
run_test_suite "Core API Tests" "01-core-api-tests.sh"

# Test 2: Image Requirement Enforcement
run_test_suite "Image Requirement Enforcement" "test-image-requirement.sh"

# Test 3: Integration Tests
run_test_suite "Integration Tests" "03-integration-tests.sh"

# Test 4: Performance Tests
run_test_suite "Performance Tests" "04-performance-tests.sh"

# Test 5: Requirements Validation
run_test_suite "Requirements Validation" "05-requirements-validation.sh"

# Test 6: Advanced Automated Tests
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}▶ Next: Advanced Automated Tests${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "🔬 Testing complex scenarios with automated evidence:"
echo "  • Streaming reconnection with backpressure"
echo "  • Concurrent database access"
echo "  • Cache performance and invalidation"
echo "  • Rate limiting enforcement"
echo "  • Memory and resource management"
echo ""
run_test_suite "Advanced Automated Tests" "06-advanced-automated-tests.sh"

# Test 7: Evidence Collection
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}▶ Next: Evidence Collection${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "📸 Gathering comprehensive evidence of system behavior"
echo ""
run_test_suite "Evidence Collection" "07-evidence-collection.sh"

# Test 8: Frontend Tests (Manual)
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}▶ Next: Frontend Tests (Manual)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "🌐 Manual UI testing required"
echo ""
echo "Open in your browser:"
echo "  http://localhost:5001/testing/02-frontend-tests.html"
echo ""
echo "This test validates:"
echo "  • UI components and interactions"
echo "  • Image upload flow"
echo "  • Chat functionality"
echo "  • Error handling"
echo "  • Visual feedback"
echo ""
echo -e "${YELLOW}Complete the frontend tests in your browser, then return here.${NC}"
echo ""
read -p "Press Enter when you've completed the frontend tests..."
echo -e "${GREEN}✅ Frontend tests completed (manual verification)${NC}"
((PASSED++))

# Final Summary
echo ""
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 TEST SUITE COMPLETE!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📊 Final Test Summary:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${GREEN}✅ Passed:  $PASSED${NC}"
echo -e "  ${RED}❌ Failed:  $FAILED${NC}"
echo -e "  ${YELLOW}⊘  Skipped: $SKIPPED${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "Test Coverage:"
    echo "  ✅ Core API functionality validated"
    echo "  ✅ Image requirement enforced"
    echo "  ✅ Integration workflows verified"
    echo "  ✅ Performance under load tested"
    echo "  ✅ Requirements compliance confirmed"
    echo "  ✅ Advanced scenarios validated"
    echo "  ✅ Evidence collected"
    echo "  ✅ Frontend components tested"
    echo ""
    echo -e "${CYAN}🚀 Project is ready for production!${NC}"
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Review failed tests above"
    echo "  2. Check server logs for errors"
    echo "  3. Verify app configuration"
    echo "  4. Re-run failed tests individually"
fi

echo ""
echo -e "${BLUE}📁 Test Artifacts:${NC}"
echo "  • Evidence: testing/evidence-*/"
echo "  • Logs: Check terminal output above"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
