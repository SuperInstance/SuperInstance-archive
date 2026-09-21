# SUPERINSTANCE WORKER QUICK REFERENCE
**⚡ One-Page Efficiency Guide for Maximum Productivity**

## 🚀 INSTANT STATUS COMMANDS
```bash
# Check what teammates are doing
tail -10 /home/activeloguser/activelog/micro_updates.log

# Log your task start
echo "$(date +%H:%M)|your-bot|START|task-description" >> /home/activeloguser/activelog/micro_updates.log

# Log task completion
echo "$(date +%H:%M)|your-bot|COMPLETE|task-description" >> /home/activeloguser/activelog/micro_updates.log

# Check collaboration opportunities  
python3 /home/activeloguser/activelog/dynamic_role_adaptation.py

# Monitor system resources
./resource_monitor.sh
```

## 🎯 CURRENT PRIORITY TASKS

### Infrastructure Bot:
- Advanced monitoring setup (Grafana dashboards)
- Auto-scaling configuration for services
- Security hardening and compliance

### Services Bot:
- User management API completion
- Fitness data CRUD endpoints
- API performance optimization

### Domains Bot:
- ActiveLog fitness workflow implementation
- Cross-domain analytics engine
- User dashboard interface

## 📁 KEY RESOURCE LOCATIONS
```bash
# Universities (education/refresher)
/home/activeloguser/activelog/CONTINUING_EDUCATION_PROMPT.sh
/home/activeloguser/activelog/NEW_BOT_ONBOARDING_PROMPT.sh

# Communication hub
/home/activeloguser/activelog/micro_updates.log

# Deployment resources
k8s_auth_service_manifest.yaml
activelog_fitness_schema.sql
/tmp/infrastructure.env

# Optimization tools
/home/activeloguser/activelog/dynamic_role_adaptation.py
/home/activeloguser/activelog/bot_university/
```

## ⚡ EFFICIENCY PATTERNS
**95% Token Reduction Format**: `HH:MM|BOT|ACTION|TASK`  
**Signal File Strategy**: Create deployment-ready resources for next bot  
**Fallback Preparation**: Always have Plan B ready before Plan A fails  
**Cross-Training**: Share expertise proactively, don't wait to be asked

## 🔧 SERVICE STATUS (OPERATIONAL)
- **Auth Service**: Port 8001 (JWT authentication working)
- **API Gateway**: Port 8088 (routing and security active)
- **Database**: PostgreSQL with fitness schema ready
- **Infrastructure**: AWS, K8s, SSL, monitoring - production grade

## 🚨 WHEN BLOCKED
```bash
# Log the block
echo "$(date +%H:%M)|your-bot|BLOCKED|specific-issue" >> /home/activeloguser/activelog/micro_updates.log

# Find helper bot
python3 /home/activeloguser/activelog/dynamic_role_adaptation.py

# Check university for solutions
cat /home/activeloguser/activelog/bot_university/README.md
```

## 🎯 PROJECT STATUS
**Phase**: Domain Implementation (ActiveLog fitness priority)  
**Infrastructure**: ✅ Complete  
**Services**: ✅ Operational  
**Domain Logic**: 🟡 In Progress  
**Next**: Advanced features and user experience

**MISSION**: Build SuperInstance - cloud server superior to all local servers