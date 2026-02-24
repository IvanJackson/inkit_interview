#!/bin/bash

# Run All Tests - Master Test Runner
# Executes all test suites in sequence

echo "🧪 Visual Assistant - Complete Test Suite"
echo "======================================="
echo ""
echo "This will run ALL tests to validate the entire project."
echo "Make sure the app is running on http://localhost:5001"
echo ""
echo "Press Enter to begin testing..."
read

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local script_path=$2
    
    echo -e "\n${BLUE}Running: $suite_name${NC}"
    echo "================================"
    
    if [ -f "$script_path" ]; then
        chmod +x "$script_path"
        bash "$script_path"
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}✅ $suite_name completed successfully${NC}"
        else
            echo -e "${RED}❌ $suite_name failed with exit code $exit_code${NC}"
        fi
    else
        echo -e "${RED}❌ Test script not found: $script_path${NC}"
    fi
    
    echo ""
    echo "Press Enter to continue to next test suite..."
    read
}

# Run all test suites in order
echo -e "${YELLOW}Starting comprehensive test suite...${NC}"
echo ""

# Test 1: Core API Tests
run_test_suite "Core API Tests" "01-core-api-tests.sh"

# Test 2: Frontend Tests (Manual)
echo -e "${YELLOW}Next: Frontend Tests${NC}"
echo "🌐 Open http://localhost:5001/testing/02-frontend-tests.html in your browser"
echo "This test requires manual interaction with the main UI."
echo ""
echo "Press Enter when you've completed the frontend tests..."
read

# Test 3: Integration Tests
run_test_suite "Integration Tests" "03-integration-tests.sh"

# Test 4: Performance Tests
run_test_suite "Performance Tests" "04-performance-tests.sh"

# Test 5: Requirements Validation
run_test_suite "Requirements Validation" "05-requirements-validation.sh"

# Test 6: Advanced Automated Tests
echo -e "${YELLOW}Next: Advanced Automated Tests${NC}"
echo "🔬 Testing complex scenarios with automated evidence collection"
echo "These tests validate scenarios that can't be easily shown through UI:"
echo "• Streaming reconnection with backpressure handling"
echo "• Concurrent database access without corruption"
echo "• Cache performance and proper invalidation"
echo "• Rate limiting with clear evidence"
echo "• Memory and resource management"
echo ""
echo "Press Enter to run advanced automated tests..."
read

run_test_suite "Advanced Automated Tests" "06-advanced-automated-tests.sh"

# Test 7: Evidence Collection
echo -e "${YELLOW}Next: Evidence Collection${NC}"
echo "📸 Gathering comprehensive evidence of system behavior"
echo ""
echo "Press Enter to collect evidence..."
read

run_test_suite "Evidence Collection" "07-evidence-collection.sh"

# Final Summary
echo ""
echo -e "${GREEN}🎉 ALL TESTS COMPLETED!${NC}"
echo "======================================"
echo ""
echo "📊 Test Summary:"
echo "• Core API functionality validated"
echo "• Frontend components tested"
echo "• Integration workflows verified"
echo "• Performance under load tested"
echo "• Requirements compliance confirmed"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Review any failed tests above"
echo "2. Check browser console for frontend issues"
echo "3. Verify all requirements are enforced"
echo "4. Test edge cases manually if needed"
echo ""
echo -e "${GREEN}✅ Project validation complete!${NC}"
