#!/bin/bash
# Quick Launch DMLog Gaming Platform
# One-command deployment of the full gaming infrastructure

set -e

echo "🎲 DMLog SuperInstance Quick Deploy"
echo "===================================="
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "🔧 Deployment Options:"
echo "1. Deploy Full Infrastructure (New deployment)"
echo "2. Start Existing Cluster (Instances already deployed)"
echo "3. Stop Running Cluster (Save costs)"
echo "4. Check Cluster Status"
echo ""
read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo "🚀 Starting full DMLog SuperInstance deployment..."
        echo "⚠️  This will take 15-20 minutes and cost ~$6-12/hour when running"
        read -p "Continue? (y/N): " confirm
        
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo "🏗️  Deploying infrastructure..."
            ./deploy-dmlog-superinstance.sh
            
            echo ""
            echo "🎉 Deployment Complete!"
            echo "✅ 3 × DMLog SuperInstance ready"
            echo "✅ Load balancer configured" 
            echo "✅ All instances STOPPED (cost: $0/hour)"
            echo ""
            echo "To start gaming:"
            echo "  ./launch-dmlog-gaming.sh"
            echo "  Choose option 2 (Start Existing Cluster)"
        fi
        ;;
        
    2)
        echo "🎮 Starting DMLog Gaming Cluster..."
        echo ""
        echo "How many instances to start?"
        echo "1. Light Gaming (1 instance, ~$2/hour)"
        echo "2. Balanced Gaming (2 instances, ~$4/hour)"  
        echo "3. Heavy Gaming (3 instances, ~$6/hour)"
        read -p "Choose (1-3): " instances
        
        case $instances in
            1) target=1 ;;
            2) target=2 ;;
            3) target=3 ;;
            *) target=1 ;;
        esac
        
        echo "🚀 Starting $target instance(s)..."
        python3 dmlog-cluster-manager.py start $target
        
        # Get cluster status
        echo ""
        echo "📊 Cluster Status:"
        python3 dmlog-cluster-manager.py metrics
        ;;
        
    3)
        echo "⏸️  Stopping DMLog Cluster..."
        python3 dmlog-cluster-manager.py stop
        echo "💰 Cluster stopped - costs now $0/hour"
        ;;
        
    4)
        echo "📊 DMLog Cluster Status:"
        python3 dmlog-cluster-manager.py status
        echo ""
        echo "🎮 Gaming Metrics:"
        python3 dmlog-cluster-manager.py metrics
        ;;
        
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "🎯 Quick Commands:"
echo "  Start gaming:  ./launch-dmlog-gaming.sh (option 2)"
echo "  Stop cluster:  ./launch-dmlog-gaming.sh (option 3)" 
echo "  Check status:  ./launch-dmlog-gaming.sh (option 4)"
echo "  Auto-scale:    python3 dmlog-cluster-manager.py scale --execute"
echo ""
echo "🎮 When running, access gaming at your load balancer URL"
echo "🎤 Voice gaming enabled - click 'Enable Voice' in interface"
echo "🤖 AI storytelling powered by LLM cluster"