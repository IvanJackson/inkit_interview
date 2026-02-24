#!/bin/bash

# Direct Test Runner
# Executes tests immediately without delays

echo "🧪 Running Tests Directly"
echo "========================"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if app is running
echo -e "${YELLOW}Checking if app is running...${NC}"
if ! curl -s http://localhost:5001/ > /dev/null 2>&1; then
    echo -e "${RED}❌ App is not running! Please start it first:${NC}"
    echo "Run: python3 app.py (from candidate_files directory)"
    exit 1
fi

echo -e "${GREEN}✅ App is running on http://localhost:5001${NC}"

# Check if we're in a virtual environment and activate it if needed
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Creating virtual environment for testing...${NC}"
    python3 -m venv testing_env
    source testing_env/bin/activate
    echo -e "${GREEN}✅ Testing virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Using existing virtual environment: $VIRTUAL_ENV${NC}"
fi

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
python3 -c "
import sys
sys.path.insert(0, 'testing_env/lib/python3.12/site-packages')
try:
    import requests
    import psutil
    from PIL import Image
    print('✅ All dependencies available in virtual environment')
except ImportError as e:
    print(f'❌ Missing dependency in virtual environment: {e}')
    sys.exit(1)
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencies ready in virtual environment${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies in virtual environment${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🚀 Starting tests in 3 seconds...${NC}"

# Countdown
for i in 3 2 1; do
    echo -e "\r${YELLOW}Starting in: $i${NC}"
    sleep 1
done

echo ""
echo -e "${GREEN}🧪 Running tests now!${NC}"

# Run core tests first
echo -e "${YELLOW}Running: Core API Tests${NC}"
if [ -f "01-core-api-tests.sh" ]; then
    # Activate virtual environment for this test
    if [ -z "$VIRTUAL_ENV" ]; then
        source testing_env/bin/activate
    fi
    
    bash 01-core-api-tests.sh
    CORE_RESULT=$?
    if [ $CORE_RESULT -eq 0 ]; then
        echo -e "${GREEN}✅ Core API tests passed${NC}"
    else
        echo -e "${RED}❌ Core API tests failed${NC}"
    fi
else
    echo -e "${RED}❌ Core API test script not found${NC}"
fi

echo ""
echo -e "${YELLOW}Running: Requirements Validation${NC}"
if [ -f "05-requirements-validation.sh" ]; then
    # Activate virtual environment for this test
    if [ -z "$VIRTUAL_ENV" ]; then
        source testing_env/bin/activate
    fi
    
    bash 05-requirements-validation.sh
    REQ_RESULT=$?
    if [ $REQ_RESULT -eq 0 ]; then
        echo -e "${GREEN}✅ Requirements validation passed${NC}"
    else
        echo -e "${RED}❌ Requirements validation failed${NC}"
    fi
else
    echo -e "${RED}❌ Requirements validation script not found${NC}"
fi

echo ""
echo -e "${BLUE}📊 Test Summary:${NC}"
echo "Core API Tests: $([ $CORE_RESULT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo "Requirements Validation: $([ $REQ_RESULT -eq 0 ] && echo 'PASS' || echo 'FAIL')"

if [ "$CORE_RESULT" = "0" ] && [ "$REQ_RESULT" = "0" ]; then
    echo -e "${GREEN}🎉 All critical tests passed!${NC}"
    echo -e "${BLUE}✅ Project is ready for production!${NC}"
else
    echo -e "${RED}❌ Some tests failed - please review above${NC}"
fi
