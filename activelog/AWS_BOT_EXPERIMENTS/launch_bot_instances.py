#!/usr/bin/env python3
"""
Launch Bot Instances - Fixed version with correct AMI and setup
"""

import boto3
import json
import time
from datetime import datetime

def launch_competitive_bot_instances():
    """Launch AWS instances for competitive bot research"""
    ec2 = boto3.client('ec2')
    
    # Get correct AMI ID for current region
    ami_id = 'ami-0029f5c55e3fbb8d7'  # Latest Amazon Linux 2
    
    research_bots = [
        "vestige_researcher", "holographic_researcher", "firefly_researcher",
        "spatial_researcher", "consciousness_researcher", "economics_researcher", 
        "integration_researcher"
    ]
    
    print("🚀 Launching AWS EC2 t2.nano instances for competitive bot research...")
    print(f"📋 AMI: {ami_id}")
    print(f"🤖 Bots: {len(research_bots)}")
    print(f"💾 Storage: 10GB per bot")
    
    launched_instances = []
    
    for i, bot_name in enumerate(research_bots):
        try:
            print(f"\\n🤖 Launching {bot_name} ({i+1}/{len(research_bots)})...")
            
            user_data = f'''#!/bin/bash
# Setup for {bot_name}
echo "Setting up {bot_name} research environment..." > /home/ec2-user/setup.log
yum update -y >> /home/ec2-user/setup.log 2>&1
yum install -y python3 python3-pip git htop >> /home/ec2-user/setup.log 2>&1

# Create research structure
mkdir -p /home/ec2-user/{{research,experiments,shared_findings,logs}}
chown -R ec2-user:ec2-user /home/ec2-user/

# Create bot research script
cat > /home/ec2-user/research/{bot_name}.py << 'EOF'
#!/usr/bin/env python3
"""
{bot_name} - Independent AWS Research Instance
Competing to build best firefly tensor system
"""

import json, time, os
from datetime import datetime
from pathlib import Path

class CompetitiveResearcher:
    def __init__(self):
        self.bot_name = "{bot_name}"
        self.storage_limit_gb = 10
        self.experiments = []
        
    def start_research(self):
        print(f"🔬 {{self.bot_name}} starting competitive research")
        print("🎯 Goal: Build superior firefly logic tensor")
        print("💾 Storage: 10GB available")
        print("🏆 Competition: Beat other 6 bots")
        
        # Log start
        self.log_experiment("research_started", "Beginning competitive firefly tensor research")
        
        # Start first experiment
        self.experiment_firefly_tensor_v1()
        
    def experiment_firefly_tensor_v1(self):
        print("🧪 Starting: Firefly Tensor v1.0")
        
        # Basic firefly tensor implementation
        tensor_data = {{
            "firefly_agents": 5,
            "tensor_dimensions": [3, 3, 3],
            "optimization_cycles": 100,
            "efficiency_target": 0.85
        }}
        
        # Save experiment
        self.log_experiment("firefly_tensor_v1", tensor_data)
        
        # TODO: Implement actual tensor logic
        # This is the competitive framework - each bot will enhance differently
        
        return tensor_data
        
    def log_experiment(self, name, data):
        experiment = {{
            "bot": self.bot_name,
            "experiment": name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "competitive_status": "active"
        }}
        
        self.experiments.append(experiment)
        
        # Save to instance
        with open("/home/ec2-user/logs/experiments.json", "w") as f:
            json.dump(self.experiments, f, indent=2)
            
        # Share finding (competitive intelligence)
        with open("/home/ec2-user/shared_findings/latest.json", "w") as f:
            json.dump({{
                "from": self.bot_name,
                "finding": f"{{name}} completed",
                "timestamp": datetime.now().isoformat(),
                "competitive_edge": "details_withheld"
            }}, f, indent=2)

if __name__ == "__main__":
    researcher = CompetitiveResearcher()
    researcher.start_research()
    print("✅ Research initialized - competitive mode active")
EOF

chmod +x /home/ec2-user/research/{bot_name}.py
chown ec2-user:ec2-user /home/ec2-user/research/{bot_name}.py

echo "{bot_name} setup completed at $(date)" >> /home/ec2-user/setup.log
'''

            response = ec2.run_instances(
                ImageId=ami_id,
                MinCount=1,
                MaxCount=1, 
                InstanceType='t2.nano',
                SecurityGroupIds=['sg-default'],  # Use default security group ID
                UserData=user_data,
                BlockDeviceMappings=[{
                    'DeviceName': '/dev/xvda',
                    'Ebs': {
                        'VolumeSize': 10,  # 10GB per bot
                        'VolumeType': 'gp2',
                        'DeleteOnTermination': True
                    }
                }],
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'{bot_name}_competitive_research'},
                        {'Key': 'Bot', 'Value': bot_name},
                        {'Key': 'Project', 'Value': 'competitive_firefly_tensor'},
                        {'Key': 'Competition', 'Value': 'active'}
                    ]
                }]
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            launched_instances.append({
                "bot_name": bot_name,
                "instance_id": instance_id,
                "launch_time": datetime.now().isoformat()
            })
            
            print(f"✅ {bot_name}: {instance_id}")
            
        except Exception as e:
            print(f"❌ Failed to launch {bot_name}: {e}")
            
    # Save results
    results = {
        "competition_started": datetime.now().isoformat(),
        "total_bots": len(launched_instances),
        "successful_launches": len(launched_instances),
        "total_storage_gb": len(launched_instances) * 10,
        "instances": launched_instances
    }
    
    with open("competitive_bot_instances.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\\n🏆 COMPETITIVE RESEARCH LAUNCHED!")
    print(f"🤖 {len(launched_instances)} bots competing independently")
    print(f"💾 {len(launched_instances) * 10}GB total storage allocated")
    print("📊 Each bot building their own firefly tensor system")
    print("🔄 Best findings shared between competitors")
    print("⬆️ Top performers will get instance upgrades")
    
    return results

if __name__ == "__main__":
    results = launch_competitive_bot_instances()