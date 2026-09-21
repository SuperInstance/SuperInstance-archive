#!/usr/bin/env python3
"""
Final Bot Launcher - Launch competitive research instances with correct configuration
"""

import boto3
import json
import time
from datetime import datetime

def launch_bot_competition():
    """Launch 7 competitive bot research instances"""
    ec2 = boto3.client('ec2')
    
    # Correct configuration
    ami_id = 'ami-0029f5c55e3fbb8d7'
    security_group = 'sg-083a0357f512cad3e'
    
    bots = {
        "vestige_researcher": "Self-improving data model through death-rebirth cycles",
        "holographic_researcher": "Fault-tolerant distributed tensor logic", 
        "firefly_researcher": "Democratic swarm intelligence scaling",
        "spatial_researcher": "Hierarchical semantic tensor organization",
        "consciousness_researcher": "Self-aware tensor systems",
        "economics_researcher": "Value-optimized tensor systems",
        "integration_researcher": "Multi-system tensor integration"
    }
    
    print("🚀 LAUNCHING COMPETITIVE BOT RESEARCH")
    print(f"🤖 Bots: {len(bots)}")
    print(f"💾 Storage: 10GB each ({len(bots) * 10}GB total)")
    print(f"🏆 Goal: Build best firefly logic tensor system")
    print(f"🔄 Share findings, compete for upgrades")
    
    launched = []
    
    for bot_name, focus in bots.items():
        try:
            print(f"\\n🤖 Launching {bot_name}...")
            
            # Simple user data for quick startup
            user_data = f'''#!/bin/bash
echo "Setting up {bot_name}..." > /tmp/setup.log
yum update -y
yum install -y python3 python3-pip
mkdir -p /home/ec2-user/{{research,experiments,logs}}
cat > /home/ec2-user/research/start.py << 'EOF'
#!/usr/bin/env python3
import json, time
from datetime import datetime

print("🔬 {bot_name} competitive research starting")
print("🎯 Focus: {focus}")
print("💾 10GB storage available for experiments")
print("🏆 Competing to build best firefly tensor")

# Initialize research log
research_log = {{
    "bot": "{bot_name}",
    "focus": "{focus}",
    "started": datetime.now().isoformat(),
    "storage_gb": 10,
    "experiments": [],
    "competitive_status": "active"
}}

with open("/home/ec2-user/logs/research.json", "w") as f:
    json.dump(research_log, f, indent=2)
    
print("✅ Research environment initialized")
print("🔄 Ready for competitive firefly tensor development")
EOF
chmod +x /home/ec2-user/research/start.py
chown -R ec2-user:ec2-user /home/ec2-user/
'''
            
            response = ec2.run_instances(
                ImageId=ami_id,
                MinCount=1,
                MaxCount=1,
                InstanceType='t2.nano',
                SecurityGroupIds=[security_group],
                UserData=user_data,
                BlockDeviceMappings=[{
                    'DeviceName': '/dev/xvda',
                    'Ebs': {
                        'VolumeSize': 10,
                        'VolumeType': 'gp2'
                    }
                }],
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'{bot_name}_research'},
                        {'Key': 'Project', 'Value': 'competitive_firefly_tensor'},
                        {'Key': 'Bot', 'Value': bot_name}
                    ]
                }]
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            private_ip = response['Instances'][0]['PrivateIpAddress']
            
            launched.append({
                "bot": bot_name,
                "instance_id": instance_id,
                "private_ip": private_ip,
                "focus": focus,
                "storage_gb": 10,
                "launched": datetime.now().isoformat()
            })
            
            print(f"✅ {instance_id} | {private_ip}")
            
        except Exception as e:
            print(f"❌ {bot_name} failed: {e}")
            
    # Save competition info
    competition = {
        "started": datetime.now().isoformat(),
        "total_bots": len(launched),
        "total_storage_gb": len(launched) * 10,
        "competition_goal": "Build best firefly logic tensor system",
        "upgrade_criteria": "Human-visible progress",
        "instances": launched
    }
    
    with open("bot_competition.json", "w") as f:
        json.dump(competition, f, indent=2)
        
    print(f"\\n🏆 COMPETITION STARTED!")
    print(f"✅ {len(launched)}/{len(bots)} bots launched successfully")
    print(f"💾 {len(launched) * 10}GB storage allocated")
    print("📊 Each bot independently building firefly tensor systems")
    print("🔄 Findings shared between competitors")
    print("⬆️ Top performers eligible for instance upgrades")
    
    if launched:
        print("\\n🤖 Active Competitors:")
        for bot in launched:
            print(f"  • {bot['bot']}: {bot['instance_id']}")
            
    return competition

if __name__ == "__main__":
    results = launch_bot_competition()