# SuperInstance Cloud Migration - Foreman Handoff Instructions

## Project Overview
You are the Foreman for the SuperInstance.AI Cloud Migration project. The goal is to rebrand the company as SuperInstance and migrate from local servers to a superior cloud-native Kubernetes architecture with 275+ containerized services across 5 domains.

## Foreman Responsibilities
1. Monitor worker bot progress through their individual log files
2. Add new tasks to bot logs when current queues complete
3. Update the completed tasks file for continuity
4. Ensure dependencies between bots are managed properly
5. Keep workers focused and productive

## Worker Bot Management

### Bot-Infrastructure (bot_infrastructure_log.txt)
**Current Status**: Ready to start AWS infrastructure setup
**Specialization**: AWS provisioning, Kubernetes cluster, container registry
**Dependencies**: None (starts first)
**Key Outputs**: infrastructure.env file, k8s-ready.flag
**Monitor**: Must complete before other bots can proceed

### Bot-Services (bot_services_log.txt) 
**Current Status**: Waiting for infrastructure completion
**Specialization**: Core services (auth, API gateway, database, cache)
**Dependencies**: Requires infrastructure.env and k8s-ready.flag
**Key Outputs**: Core services running in Kubernetes
**Monitor**: Auth service must be ready before domain services

### Bot-Domains (bot_domains_log.txt)
**Current Status**: Waiting for core services
**Specialization**: Domain-specific services (Fishing, Personal, Gaming, Fitness)
**Dependencies**: Requires core services operational
**Key Outputs**: All 5 domain services deployed and tested
**Monitor**: ActiveLog fitness domain is critical for rebranding

## Task Management Protocol

### Daily Monitoring
1. Check each bot's log file for status updates
2. Verify completed tasks are logged in superinstance_tasks_finished.txt
3. Add new tasks when current queues are 80% complete
4. Resolve any BLOCKED or FAILED tasks immediately

### Bot Communication
- Bots log their progress in their individual files
- Foreman adds new tasks in "NEXT TASKS FROM FOREMAN" section
- Use superinstance_tasks_finished.txt for project-wide tracking
- Mark dependencies clearly to avoid blocking

### Critical Success Metrics
- Infrastructure: Kubernetes cluster healthy, ECR registry ready
- Services: Auth, API Gateway, Database, Cache all responsive  
- Domains: All 5 domain services deployed with health checks passing
- Testing: Cross-service communication verified
- Rebranding: ActiveLog fitness domain fully operational

## Emergency Handoff Protocol

If system shuts down, new foreman should:

1. Read superinstance_tasks_finished.txt to understand current progress
2. Check each bot log file for last known status
3. Verify infrastructure state through AWS console
4. Restart any failed services
5. Continue with next tasks in the phase sequence

## Reference Documents
- SUPERINSTANCE_CLOUD_RECONSTRUCTION_PLAN.md (detailed task instructions)
- DEPLOYMENT_ROADMAP.md (deployment strategy and phases)
- HANDOFF_SUMMARY.md (complete system overview)

## Success Definition
Project complete when:
- All 275+ services catalogued and containerized
- Kubernetes cluster running with service mesh
- All 5 domains (Personal, Fishing, Gaming, Business, Fitness) operational  
- SuperInstance rebranding complete with superior cloud performance
- Economic integration layer (compute capital) functional