# COLLABORATION PROTOCOLS - PROVEN PATTERNS

## MICRO UPDATE COMMUNICATION STANDARD
**Format**: `HH:MM|BOT|ACTION|TASK`
**Actions**: START, COMPLETE, BLOCKED, CRITICAL, ASSIST, HANDOFF, COORDINATE
**Log Location**: `/home/activeloguser/activelog/micro_updates.log`
**Rule**: Update immediately when starting/completing tasks

## SIGNAL FILE HANDOFF SYSTEM
**Pattern**: Create deployment-ready resources for other bots
```bash
# Infrastructure creates for Services
/tmp/infrastructure.env
/tmp/k8s-ready.flag
k8s_auth_service_manifest.yaml

# Services creates for Domains  
auth_api_endpoints.json
database_connection_ready.flag

# Domains creates for Integration
business_logic_schemas.sql
user_workflow_definitions.json
```

## DYNAMIC WORKLOAD MANAGEMENT
**Monitor**: Check `workload_distribution` in role adaptation system
**Threshold**: >3 task difference triggers rebalancing
**Response**: Cross-train and delegate, don't wait for permission
**Command**: `python3 dynamic_role_adaptation.py` for real-time analysis

## FALLBACK PREPARATION PROTOCOL
**Rule**: Always prepare Plan B before Plan A fails
**Examples**:
- Docker deployment ready when K8s setup
- Local registry when ECR permissions limited  
- Direct database when API unavailable
**Implementation**: Create fallback resources proactively

## SKILL SHARING ESCALATION
**Trigger**: Task blocked >10 minutes OR other bot has relevant skill level >7
**Process**:
1. Log BLOCKED in micro_updates.log
2. Check skill matrix for available teachers
3. Request cross-training or direct assistance
4. Share learning resources from bot_university/

## RESOURCE OPTIMIZATION CYCLE
**Frequency**: Every 50 micro updates OR when disk >80%
**Actions**: Run storage audit, summarize logs, consolidate duplicates
**Preserve**: Decision frameworks, schemas, coordination patterns
**Delete**: Regenerable artifacts, superseded information

**KEY INSIGHT**: Optimize for compound learning value across all future projects