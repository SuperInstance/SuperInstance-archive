#!/bin/bash
# AI Society Portal - EC2 Automated Setup Script
# Run this on a fresh Ubuntu EC2 instance

set -e

echo "🚀 AI Society Portal - Cloud Deployment Setup"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "Please do not run as root"
    exit 1
fi

echo -e "${BLUE}Step 1: Updating system...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "${BLUE}Step 2: Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

echo -e "${BLUE}Step 3: Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo apt install docker-compose -y
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

echo -e "${BLUE}Step 4: Setting up firewall...${NC}"
sudo ufw --force enable
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
echo -e "${GREEN}✓ Firewall configured${NC}"

echo -e "${BLUE}Step 5: Creating project directory...${NC}"
mkdir -p ~/ai_society_portal
cd ~/ai_society_portal

echo -e "${BLUE}Step 6: Setting up environment variables...${NC}"
if [ ! -f backend/.env ]; then
    mkdir -p backend
    echo "Creating .env file..."
    read -p "Enter your OpenAI API Key: " OPENAI_KEY
    read -p "Enter your Anthropic API Key: " ANTHROPIC_KEY
    
    cat > backend/.env << EOF
OPENAI_API_KEY=$OPENAI_KEY
ANTHROPIC_API_KEY=$ANTHROPIC_KEY
QDRANT_URL=qdrant:6333
HOST=0.0.0.0
PORT=8000
EOF
    echo -e "${GREEN}✓ Environment configured${NC}"
else
    echo -e "${GREEN}✓ Environment already configured${NC}"
fi

echo ""
echo -e "${GREEN}=============================================="
echo "✓ Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "1. Upload or git clone your ai_society_portal code to ~/ai_society_portal"
echo "2. Run: docker-compose up -d"
echo "3. Access your portal at: http://$(curl -s ifconfig.me)"
echo ""
echo "To check status: docker-compose ps"
echo "To view logs: docker-compose logs -f"
echo "To restart: docker-compose restart"
echo ""
echo "Note: You may need to log out and back in for Docker group to take effect"
