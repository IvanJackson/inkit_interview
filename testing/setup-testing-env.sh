#!/bin/bash

# Setup Testing Environment
# Ensures all dependencies are installed for comprehensive testing

echo "🔧 Setting Up Testing Environment"
echo "==============================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d "testing_env" ]; then
    echo -e "${YELLOW}Creating testing virtual environment...${NC}"
    python3 -m venv testing_env
    source testing_env/bin/activate
    echo -e "${GREEN}✅ Testing environment created${NC}"
else
    echo -e "${GREEN}✅ Testing environment already exists${NC}"
fi

# Install required packages
echo -e "${YELLOW}Installing testing dependencies...${NC}"
pip install requests pillow psutil > /dev/null 2>&1

# Verify installations
echo -e "${YELLOW}Verifying installations...${NC}"

python3 -c "
import sys
try:
    import requests
    import psutil
    from PIL import Image
    print('✅ requests module available')
    print('✅ pillow module available') 
    print('✅ psutil module available')
    print('✅ All dependencies installed')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All testing dependencies ready${NC}"
else
    echo -e "${RED}❌ Dependency installation failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🧪 Testing environment is ready!${NC}"
echo ""
echo "You can now run the comprehensive test suite:"
echo "  ./fix-issues.sh          # Fix environment issues"
echo "  ./run-all-tests.sh         # Run all tests"
echo ""
echo -e "${BLUE}📋 Recommended testing order:${NC}"
echo "1. Setup environment (if needed)"
echo "2. Run core tests to verify basic functionality"
echo "3. Run requirements validation to check compliance"
echo "4. Run advanced tests for complex scenarios"
echo "5. Collect evidence for detailed analysis"
