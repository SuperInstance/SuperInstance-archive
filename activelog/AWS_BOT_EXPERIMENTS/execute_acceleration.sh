#!/bin/bash
# Experiment Acceleration Execution Script
# Upgrades instances to cut experiment time from 4 weeks to 3-5 days

echo "🚀 Starting experiment acceleration..."

# Phase 1: Upgrade delegation experiment bots (Day 1)
echo "⚡ Phase 1: Upgrading delegation experiment bots to c5.2xlarge"
aws ec2 run-instances \
    --image-id ami-0029f5c55e3fbb8d7 \
    --count 4 \
    --instance-type c5.2xlarge \
    --security-group-ids sg-079f48abca9795b2c \
    --subnet-id subnet-0496763b3fb523c1b \
    --user-data file://delegation_acceleration_userdata.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=delegation_accelerated},{Key=Experiment,Value=optimal_delegation}]'

# Phase 2: Launch GPU-accelerated ML training (Day 2)
echo "🧠 Phase 2: Launching GPU-accelerated ML training"
aws ec2 run-instances \
    --image-id ami-0029f5c55e3fbb8d7 \
    --count 1 \
    --instance-type p3.2xlarge \
    --security-group-ids sg-079f48abca9795b2c \
    --subnet-id subnet-0496763b3fb523c1b \
    --user-data file://gpu_ml_userdata.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=professor_gpu},{Key=Purpose,Value=ml_acceleration}]'

# Phase 3: Parallel fourth dimension testing
echo "🌐 Phase 3: Launching parallel fourth dimension testing"
aws ec2 run-instances \
    --image-id ami-0029f5c55e3fbb8d7 \
    --count 4 \
    --instance-type c5.xlarge \
    --security-group-ids sg-079f48abca9795b2c \
    --subnet-id subnet-0496763b3fb523c1b \
    --user-data file://fourth_dimension_userdata.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=fourth_dimension_accelerated}]'

echo "✅ Acceleration deployment complete!"
echo "📊 Expected results in 3-5 days vs 4 weeks"
echo "💰 Cost increase: +40% for 23-25 day time savings"

# Monitor acceleration progress
echo "🔍 Monitoring acceleration progress..."
watch -n 30 'aws ec2 describe-instances --filters "Name=tag:Experiment,Values=optimal_delegation" --query "Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType]" --output table'
