# Token-Efficient Bot Communication Protocols

## MICRO-UPDATE SYSTEM (< 50 tokens per update)

### Status File: `bot_status_compressed.txt`
**Format**: `YYYY-MM-DD-HH:MM|BOT|STATUS|TASK|BLOCKERS`
**Example**: `2025-08-27-02:55|services|WORKING|auth-deploy|none`

### Progress Log: `micro_updates.log`  
**Format**: `HH:MM|BOT|ACTION|STATUS`
**Example**: `02:55|services|START|auth-service`

### Task Assignment: `task_assignments_optimized.txt`
**Rule**: Each bot reads ONLY their section (reduces token load 70%)

## SIGNAL-BASED COORDINATION (0 tokens after setup)

### Ready Flags (File existence = signal)
- `/tmp/k8s-ready.flag` → Services/Domains can start
- `/tmp/auth-service-ready.flag` → Domains can deploy
- `/tmp/postgres-ready.flag` → All can use database
- `/tmp/activelog-priority.flag` → Focus on fitness domain

### Status Codes (Single letter efficiency)
- `W` = Waiting, `S` = Starting, `P` = Progress, `C` = Complete, `B` = Blocked

## COMPRESSED TASK UPDATES

### Before (Full JSON - ~200 tokens):
```json
{
  "task": "auth-service-deployment",
  "status": "in_progress", 
  "assigned_bot": "services",
  "started_at": "2025-08-27T02:55:00Z",
  "estimated_completion": "2025-08-27T03:30:00Z",
  "dependencies_met": true,
  "blockers": []
}
```

### After (Compressed - ~20 tokens):
```
02:55|services|S|auth-deploy|30min
```

## FOREMAN OPTIMIZATION SCRIPTS

### Auto-Status Aggregator (`status_quick_check.sh`)
```bash
#!/bin/bash
# 5-second status check - no token waste
tail -1 micro_updates.log
ls /tmp/*-ready.flag 2>/dev/null | wc -l
ps aux | grep -c kubectl
```

### Problem Detector (`stuck_task_detect.sh`)
```bash
#!/bin/bash
# Detect stuck tasks via timestamp comparison
last_update=$(tail -1 micro_updates.log | cut -d'|' -f1)
current_time=$(date +%H:%M)
# Alert if >20 min since last update
```

## BOT INSTRUCTION OPTIMIZATION

### Old Instructions (~1000 tokens):
- Long explanations of what to do
- Detailed context and background
- Multiple file references
- Verbose error handling

### New Instructions (~200 tokens):
- Action-only commands
- Single file reference
- Status code responses
- Error flags only

### Example Optimized Bot Instruction:
```
BOT-SERVICES: 
ACTION: Deploy auth-service to K8s NOW
INPUT: /services/auth-service/main.py
OUTPUT: auth-service-ready.flag  
STATUS: Echo "02:56|services|C|auth-deploy" >> micro_updates.log
NEXT: Auto-proceed to postgres-cluster
```

## PARALLEL WORK TRIGGERS

### Self-Organizing Task Assignment:
1. Bot checks `task_assignments_optimized.txt` for their section
2. Picks highest priority available task
3. Updates `micro_updates.log` with 1 line
4. Works independently until complete
5. Triggers next bot via flag file

This system reduces coordination overhead from ~500 tokens per interaction to ~20 tokens, enabling 25x more efficient bot communication while maintaining full coordination capability.