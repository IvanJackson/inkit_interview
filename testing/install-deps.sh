#!/bin/bash

# Install Testing Dependencies
# Simple script to install required packages for testing

echo "📦 Installing Testing Dependencies"
echo "=============================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Installing: requests, pillow, psutil${NC}"

# Install packages
pip install requests pillow psutil

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All dependencies installed successfully${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Dependencies are ready!${NC}"
