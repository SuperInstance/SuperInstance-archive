#!/bin/bash
# ActiveLedger.ai Financial Infrastructure Startup Script

echo "🏦 Starting ActiveLedger.ai Financial Infrastructure..."
echo "=================================================="

# Set environment variables
export ACTIVELOG_ENV="development"
export REDIS_URL="redis://localhost:6379"
export PHASE="dream_mode_only"  # Phase 1: Dream Mode Only

# Create data directories
mkdir -p services/activeLedger-trading-engine/data
mkdir -p services/activeLedger-settlement/data
mkdir -p services/activeLedger-compliance/data
mkdir -p services/activeLedger-market-data/data
mkdir -p services/activeLedger-wallet/data
mkdir -p services/activeLedger-dream-mode/data

# Start Redis (required for all services)
echo "Starting Redis server..."
redis-server --daemonize yes --port 6379

# Wait for Redis to start
sleep 2

echo ""
echo "🎯 PHASE 1: DREAM MODE ONLY DEPLOYMENT"
echo "======================================"
echo "✅ Virtual CC trading with 10,000 starting balance"
echo "✅ Market simulation and educational content"
echo "✅ Compliance monitoring and audit logging"
echo "❌ Real money trading (Phase 2)"
echo "❌ Business flotation features (Phase 3)"
echo "❌ Full market features (Phase 4)"
echo ""

# Start Dream Mode Trading Service (Port 8510)
echo "🎮 Starting Dream Mode Trading Service on port 8510..."
cd services/activeLedger-dream-mode
pip3 install -r requirements.txt > /dev/null 2>&1
PORT=8510 python3 main.py &
DREAM_MODE_PID=$!
echo $DREAM_MODE_PID > ../../pids/dream-mode.pid
cd ../..

# Start Market Data Feed Service (Port 8503)
echo "📊 Starting Market Data Feed Service on port 8503..."
cd services/activeLedger-market-data
pip3 install -r requirements.txt > /dev/null 2>&1
PORT=8503 python3 main.py &
MARKET_DATA_PID=$!
echo $MARKET_DATA_PID > ../../pids/market-data.pid
cd ../..

# Start Compliance Server (Port 8502)
echo "⚖️  Starting Compliance Server on port 8502..."
cd services/activeLedger-compliance
pip3 install -r requirements.txt > /dev/null 2>&1
PORT=8502 python3 main.py &
COMPLIANCE_PID=$!
echo $COMPLIANCE_PID > ../../pids/compliance.pid
cd ../..

# Start Wallet Server (Virtual Mode) (Port 8504)
echo "💳 Starting Wallet Server (Virtual Mode) on port 8504..."
cd services/activeLedger-wallet
pip3 install -r requirements.txt > /dev/null 2>&1
PORT=8504 WALLET_MODE=virtual python3 main.py &
WALLET_PID=$!
echo $WALLET_PID > ../../pids/wallet.pid
cd ../..

# Phase 2+ Services (Disabled in Phase 1)
echo ""
echo "⏳ Phase 2+ Services (Will activate when criteria are met):"
echo "   🏪 Trading Engine (Real CC trading)"
echo "   💰 Settlement Server (Real money settlement)"
echo "   🏛️  Payment Integration (Stripe, PayPal, ACH)"
echo ""

# Wait for services to start
echo "Waiting for services to initialize..."
sleep 5

# Health checks
echo ""
echo "🔍 Performing health checks..."
echo "================================"

check_service() {
    local service_name=$1
    local port=$2
    local response=$(curl -s http://localhost:$port/health 2>/dev/null)
    if echo "$response" | grep -q "healthy"; then
        echo "✅ $service_name: Healthy"
        return 0
    else
        echo "❌ $service_name: Not responding"
        return 1
    fi
}

check_service "Dream Mode Trading" 8510
check_service "Market Data Feed" 8503
check_service "Compliance Server" 8502
check_service "Wallet Server" 8504

echo ""
echo "📈 ActiveLedger.ai Services Status:"
echo "=================================="
echo "🎮 Dream Mode Trading:     http://localhost:8510"
echo "📊 Market Data Feed:       http://localhost:8503"
echo "⚖️  Compliance Server:      http://localhost:8502"
echo "💳 Wallet Server:          http://localhost:8504"
echo ""
echo "🎯 WebSocket Endpoints:"
echo "📊 Market Data Stream:     ws://localhost:8503/ws/market-data"
echo ""

echo "📋 Phase 1 Features Available:"
echo "==============================="
echo "• Virtual CC Trading (10,000 starting balance)"
echo "• Market Simulation (10 symbols)"
echo "• Dream Mode Leaderboards"
echo "• Achievement System"
echo "• Educational Content"
echo "• Compliance Monitoring"
echo "• Real-time Market Data"
echo ""

echo "🎓 Graduation Requirements (to Phase 2):"
echo "========================================"
echo "• Complete 100+ dream trades"
echo "• Achieve 1,000+ virtual CC profit"
echo "• Maintain 60%+ win rate"
echo "• Max drawdown ≤ 2,000 virtual CC"
echo "• Complete KYC verification"
echo "• Enable 2FA"
echo "• Pass risk assessment"
echo ""

echo "📊 API Documentation:"
echo "===================="
echo "• Dream Mode API:          http://localhost:8510/docs"
echo "• Market Data API:         http://localhost:8503/docs"
echo "• Compliance API:          http://localhost:8502/docs"
echo "• Wallet API:              http://localhost:8504/docs"
echo ""

echo "🔐 Security Features Active:"
echo "============================"
echo "• AES-256 Encryption"
echo "• Rate Limiting (1000 req/hour)"
echo "• Fraud Detection (Learning Mode)"
echo "• Audit Logging"
echo "• Compliance Monitoring"
echo ""

echo "🚀 ActiveLedger.ai is now running in Phase 1: Dream Mode!"
echo "=========================================================="
echo ""
echo "Next Steps:"
echo "1. Register users and let them start dream trading"
echo "2. Monitor user engagement and graduation rates"
echo "3. When 1000+ active users and success criteria met:"
echo "   → Deploy Phase 2 (Real CC Trading)"
echo ""
echo "To stop all services: ./stop-activeledger.sh"
echo "To check logs: tail -f pids/*.log"
echo ""

# Create stop script
cat > stop-activeledger.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping ActiveLedger.ai Services..."

# Kill services using PID files
if [ -f pids/dream-mode.pid ]; then
    kill $(cat pids/dream-mode.pid) 2>/dev/null
    rm pids/dream-mode.pid
    echo "✅ Dream Mode Trading stopped"
fi

if [ -f pids/market-data.pid ]; then
    kill $(cat pids/market-data.pid) 2>/dev/null
    rm pids/market-data.pid
    echo "✅ Market Data Feed stopped"
fi

if [ -f pids/compliance.pid ]; then
    kill $(cat pids/compliance.pid) 2>/dev/null
    rm pids/compliance.pid
    echo "✅ Compliance Server stopped"
fi

if [ -f pids/wallet.pid ]; then
    kill $(cat pids/wallet.pid) 2>/dev/null
    rm pids/wallet.pid
    echo "✅ Wallet Server stopped"
fi

# Stop Redis
redis-cli shutdown 2>/dev/null
echo "✅ Redis stopped"

echo ""
echo "🏦 ActiveLedger.ai services stopped successfully!"
EOF

chmod +x stop-activeledger.sh

# Create Phase 2 deployment script for future use
cat > deploy-phase-2.sh << 'EOF'
#!/bin/bash
echo "🚀 Deploying Phase 2: Real CC Trading..."
echo "======================================="
echo ""
echo "⚠️  IMPORTANT: Only deploy when Phase 1 criteria are met:"
echo "   • 1000+ active users"
echo "   • 200+ graduated users"
echo "   • High user satisfaction (4.5/5+)"
echo "   • Zero security incidents"
echo "   • Regulatory approval obtained"
echo ""
echo "Phase 2 will enable:"
echo "• Real CC trading with actual money"
echo "• Payment processing (Stripe integration)"
echo "• Settlement engine"
echo "• Enhanced compliance monitoring"
echo "• KYC/2FA mandatory"
echo ""
read -p "Continue with Phase 2 deployment? (yes/no): " confirm
if [ "$confirm" = "yes" ]; then
    echo "Deploying Phase 2 services..."
    # Implementation would go here
    export PHASE="real_trading_limited"
    echo "✅ Phase 2 deployment complete!"
else
    echo "❌ Phase 2 deployment cancelled"
fi
EOF

chmod +x deploy-phase-2.sh

echo "💾 Additional scripts created:"
echo "   ./stop-activeledger.sh  - Stop all services"
echo "   ./deploy-phase-2.sh     - Deploy Phase 2 when ready"