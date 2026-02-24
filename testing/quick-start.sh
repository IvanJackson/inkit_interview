#!/bin/bash

# Quick Test Start
# Simple entry point for comprehensive testing

echo "🧪 Visual Assistant Testing Suite"
echo "========================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if app is running
echo -e "${YELLOW}Checking if app is running...${NC}"
if curl -s http://localhost:5001/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ App is running on http://localhost:5001${NC}"
else
    echo -e "${RED}❌ App is not running! Please start it first:${NC}"
    echo "Run: python3 app.py (from candidate_files directory)"
    exit 1
fi

echo ""

# Install dependencies if needed
echo -e "${YELLOW}Checking dependencies...${NC}"

# Check if we're in a virtual environment and activate it if needed
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Creating virtual environment for testing...${NC}"
    python3 -m venv testing_env
    source testing_env/bin/activate
    echo -e "${GREEN}✅ Testing virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Using existing virtual environment: $VIRTUAL_ENV${NC}"
fi

# Install dependencies in the virtual environment
echo -e "${YELLOW}Installing testing dependencies...${NC}"
./install-deps.sh

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencies ready in virtual environment${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies in virtual environment${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🚀 Ready to run comprehensive tests!${NC}"
echo ""
echo -e "${BLUE}Available commands:${NC}"
echo "  ./run-all-tests.sh           # Run all test suites"
echo "  ./07-evidence-collection-fixed.sh  # Collect evidence (fixed)"
echo ""
echo -e "${YELLOW}Note: Use ./run-all-tests.sh for complete validation${NC}"
echo ""
echo -e "${GREEN}Starting tests in 3 seconds...${NC}"

# Countdown
for i in 3 2 1; do
    echo -e "\r${YELLOW}Starting in: $i${NC}"
    sleep 1
done

echo ""
echo -e "${GREEN}🧪 Running tests now!${NC}"
