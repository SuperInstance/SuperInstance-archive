#!/bin/bash
# Start script for Content Studio V2 (API-based)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Loopless Content Studio V2           ║${NC}"
echo -e "${GREEN}║  Multi-Agent Parallel System           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Virtual environment not found!${NC}"
    echo "  Run: python3 -m venv venv"
    echo "  Then: ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}→ Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Run the system (handles .env check and first-run setup)
python run_studio.py

# Deactivate on exit
deactivate
