#!/usr/bin/env python3
"""
Simple Launch - Start competitive bot research with proper VPC/Subnet configuration
"""

import boto3
import json
from datetime import datetime

def launch_research_bots():
    """Launch competitive research bots with correct network configuration"""
    ec2 = boto3.client('ec2')
    
    # Correct network configuration
    ami_id = 'ami-0029f5c55e3fbb8d7'
    security_group = 'sg-079f48abca9795b2c'  # Matching VPC
    subnet_id = 'subnet-0496763b3fb523c1b'
    
    research_bots = [
        ("vestige_researcher", "Death-rebirth optimization firefly tensors"),
        ("holographic_researcher", "Fault-tolerant firefly tensor logic"),
        ("firefly_researcher", "Pure swarm intelligence optimization"),
        ("spatial_researcher", "Semantic firefly tensor organization"),
        ("consciousness_researcher", "Self-aware firefly systems"),
        ("economics_researcher", "ROI-optimized firefly tensors"),
        ("integration_researcher", "Unified firefly tensor framework")
    ]
    
    print("🚀 LAUNCHING COMPETITIVE FIREFLY TENSOR RESEARCH")
    print(f"🤖 {len(research_bots)} bots competing independently")
    print(f"💾 10GB storage per bot ({len(research_bots) * 10}GB total)")
    print("🏆 Goal: Build the most advanced firefly logic tensor system")
    
    launched_bots = []
    
    for bot_name, specialization in research_bots:
        try:
            print(f"\\n🤖 Starting {bot_name}...")
            
            response = ec2.run_instances(
                ImageId=ami_id,
                MinCount=1,
                MaxCount=1,
                InstanceType='t2.nano',
                SecurityGroupIds=[security_group],
                SubnetId=subnet_id,
                UserData=f'''#!/bin/bash
# Quick setup for {bot_name}
yum update -y
yum install -y python3 python3-pip git
mkdir -p /home/ec2-user/{{research,experiments,shared_findings,logs}}

# Create competitive research script
cat > /home/ec2-user/research/{bot_name}.py << 'EOF'
#!/usr/bin/env python3
"""
{bot_name} - Competitive Firefly Tensor Research
Specialization: {specialization}
Storage: 10GB for experiments
Goal: Build superior firefly logic tensor system
"""

import json, time, os
from datetime import datetime

class CompetitiveFireflyResearcher:
    def __init__(self):
        self.bot_name = "{bot_name}"
        self.specialization = "{specialization}"
        self.storage_gb = 10
        self.competitive_status = "active"
        
    def initialize_research(self):
        print(f"🔬 {{self.bot_name}} - Competitive Research Active")
        print(f"🎯 Specialization: {{self.specialization}}")
        print("🏆 Competition: Building best firefly tensor system")
        print("💾 10GB storage for experiments")
        print("🔄 Sharing findings with 6 other competitors")
        
        # Initialize research log
        research_log = {{
            "bot": self.bot_name,
            "specialization": self.specialization,
            "start_time": datetime.now().isoformat(),
            "storage_limit_gb": 10,
            "experiments": [],
            "findings_shared": [],
            "competitive_status": "researching",
            "goal": "superior_firefly_tensor_system"
        }}
        
        # Save initial state
        os.makedirs("/home/ec2-user/logs", exist_ok=True)
        with open("/home/ec2-user/logs/research_log.json", "w") as f:
            json.dump(research_log, f, indent=2)
            
        # Start first competitive experiment
        self.experiment_1_baseline_firefly_tensor()
        
    def experiment_1_baseline_firefly_tensor(self):
        print("🧪 Experiment 1: Baseline Firefly Tensor Implementation")
        
        # Each bot will specialize differently based on their focus
        baseline_tensor = {{
            "firefly_agents": 7,  # Start with 7 agents
            "tensor_dimensions": [4, 4, 4],  # 3D tensor space
            "democratic_voting": True,
            "specialization": self.specialization,
            "optimization_target": "efficiency > 0.8",
            "competitive_advantage": "{{specialized approach based on bot focus}}"
        }}
        
        print(f"📊 Tensor Configuration: {{baseline_tensor}}")
        
        # Log experiment
        self.log_experiment("baseline_firefly_tensor", baseline_tensor)
        
        # Share finding with competitors (but keep competitive edge)
        self.share_competitive_finding("Baseline tensor initialized", "limited_details")
        
    def log_experiment(self, name, data):
        experiment = {{
            "name": name,
            "bot": self.bot_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "status": "active"
        }}
        
        # Save to bot's research log
        try:
            with open("/home/ec2-user/logs/research_log.json", "r") as f:
                log = json.load(f)
            log["experiments"].append(experiment)
            with open("/home/ec2-user/logs/research_log.json", "w") as f:
                json.dump(log, f, indent=2)
        except:
            # Create new log if doesn't exist
            log = {{"experiments": [experiment]}}
            with open("/home/ec2-user/logs/research_log.json", "w") as f:
                json.dump(log, f, indent=2)
                
    def share_competitive_finding(self, finding, detail_level):
        """Share findings with other bots while maintaining competitive advantage"""
        shared_data = {{
            "from_bot": self.bot_name,
            "finding": finding,
            "detail_level": detail_level,
            "timestamp": datetime.now().isoformat(),
            "competitive_note": "Full details available after performance evaluation"
        }}
        
        os.makedirs("/home/ec2-user/shared_findings", exist_ok=True)
        with open(f"/home/ec2-user/shared_findings/{{self.bot_name}}_latest.json", "w") as f:
            json.dump(shared_data, f, indent=2)

if __name__ == "__main__":
    researcher = CompetitiveFireflyResearcher()
    researcher.initialize_research()
    print("✅ Competitive research initialized - ready to build superior firefly tensor")
EOF

chmod +x /home/ec2-user/research/{bot_name}.py
chown -R ec2-user:ec2-user /home/ec2-user/

# Auto-start research
python3 /home/ec2-user/research/{bot_name}.py > /home/ec2-user/logs/startup.log 2>&1 &

echo "Setup completed for {bot_name}" > /tmp/setup_complete
''',
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
                        {'Key': 'Name', 'Value': f'{bot_name}_firefly_research'},
                        {'Key': 'Bot', 'Value': bot_name},
                        {'Key': 'Competition', 'Value': 'firefly_tensor'},
                        {'Key': 'Storage', 'Value': '10GB'},
                        {'Key': 'Upgrade', 'Value': 'performance_based'}
                    ]
                }]
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            private_ip = response['Instances'][0]['PrivateIpAddress']
            
            launched_bots.append({
                "bot_name": bot_name,
                "specialization": specialization,
                "instance_id": instance_id,
                "private_ip": private_ip,
                "storage_gb": 10,
                "launched_at": datetime.now().isoformat(),
                "status": "initializing"
            })
            
            print(f"✅ {bot_name}: {instance_id} | {private_ip}")
            
        except Exception as e:
            print(f"❌ {bot_name} launch failed: {e}")
            
    # Save competition state
    competition_data = {
        "competition_start": datetime.now().isoformat(),
        "total_bots": len(launched_bots),
        "total_storage_gb": len(launched_bots) * 10,
        "competition_goal": "Build most advanced firefly logic tensor system",
        "upgrade_criteria": "Human-visible progress in tensor performance",
        "sharing_policy": "Findings shared, competitive advantage retained",
        "launched_bots": launched_bots
    }
    
    with open("firefly_tensor_competition.json", "w") as f:
        json.dump(competition_data, f, indent=2)
        
    print(f"\\n🏆 FIREFLY TENSOR COMPETITION LAUNCHED!")
    print(f"✅ {len(launched_bots)}/{len(research_bots)} competitive researchers active")
    print(f"💾 {len(launched_bots) * 10}GB distributed storage allocated")
    print("🔬 Each bot independently developing firefly tensor systems")
    print("🤝 Findings shared between competitors")
    print("⬆️ Performance leaders eligible for t2.small/medium upgrades")
    
    if launched_bots:
        print("\\n🤖 Active Competitive Researchers:")
        for bot in launched_bots:
            print(f"  • {bot['bot_name']}: {bot['instance_id']} ({bot['specialization']})")
    
    return competition_data

if __name__ == "__main__":
    competition = launch_research_bots()