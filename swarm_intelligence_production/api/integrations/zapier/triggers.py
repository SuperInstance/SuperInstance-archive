"""
Zapier Integration - Triggers
Triggers allow Zapier workflows to start when events occur in the swarm system
"""

from typing import Dict, List, Any


# ============================================================================
# TRIGGER DEFINITIONS
# ============================================================================

def task_completed_trigger(bundle: Dict[str, Any]) -> List[Dict]:
    """
    Trigger: Task Completed
    Fires when a task completes successfully

    Use cases:
    - Send Slack notification when render completes
    - Add row to Google Sheets with task results
    - Email customer when creative asset is ready
    """
    api_key = bundle['authData']['api_key']
    swarm_id = bundle['inputData'].get('swarm_id')

    # Fetch completed tasks from API
    # This is a polling trigger - Zapier will check periodically
    completed_tasks = fetch_completed_tasks(api_key, swarm_id)

    return completed_tasks


def swarm_error_trigger(bundle: Dict[str, Any]) -> List[Dict]:
    """
    Trigger: Swarm Error
    Fires when a swarm encounters an error

    Use cases:
    - Send PagerDuty alert
    - Log error to monitoring system
    - Notify team via Slack/Discord
    """
    api_key = bundle['authData']['api_key']

    errors = fetch_swarm_errors(api_key)
    return errors


def agent_failed_trigger(bundle: Dict[str, Any]) -> List[Dict]:
    """
    Trigger: Agent Failed
    Fires when an individual agent fails

    Use cases:
    - Track failure rates in analytics
    - Automatic retry logic
    - Alert system administrators
    """
    api_key = bundle['authData']['api_key']
    swarm_id = bundle['inputData'].get('swarm_id')

    failed_agents = fetch_failed_agents(api_key, swarm_id)
    return failed_agents


def metrics_threshold_trigger(bundle: Dict[str, Any]) -> List[Dict]:
    """
    Trigger: Metrics Threshold
    Fires when metrics exceed configured thresholds

    Use cases:
    - Alert when error rate > 5%
    - Notify when throughput drops
    - Scale swarm when utilization > 80%
    """
    api_key = bundle['authData']['api_key']
    swarm_id = bundle['inputData']['swarm_id']
    metric = bundle['inputData']['metric']
    threshold = float(bundle['inputData']['threshold'])
    condition = bundle['inputData'].get('condition', 'greater_than')

    current_metrics = fetch_metrics(api_key, swarm_id)

    # Check threshold
    metric_value = current_metrics.get(metric, 0)

    triggered = False
    if condition == 'greater_than' and metric_value > threshold:
        triggered = True
    elif condition == 'less_than' and metric_value < threshold:
        triggered = True

    if triggered:
        return [{
            'swarm_id': swarm_id,
            'metric': metric,
            'value': metric_value,
            'threshold': threshold,
            'condition': condition
        }]

    return []


def creative_output_ready_trigger(bundle: Dict[str, Any]) -> List[Dict]:
    """
    Trigger: Creative Output Ready
    Fires when creative content generation completes

    Use cases:
    - Download to Dropbox
    - Post to social media
    - Send to client for review
    """
    api_key = bundle['authData']['api_key']
    swarm_id = bundle['inputData'].get('swarm_id')
    creative_type = bundle['inputData'].get('creative_type')

    outputs = fetch_creative_outputs(api_key, swarm_id, creative_type)
    return outputs


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fetch_completed_tasks(api_key: str, swarm_id: str = None) -> List[Dict]:
    """Fetch recently completed tasks"""
    # Implementation: Call API to fetch completed tasks
    return []


def fetch_swarm_errors(api_key: str) -> List[Dict]:
    """Fetch recent swarm errors"""
    return []


def fetch_failed_agents(api_key: str, swarm_id: str = None) -> List[Dict]:
    """Fetch failed agents"""
    return []


def fetch_metrics(api_key: str, swarm_id: str) -> Dict:
    """Fetch current metrics"""
    return {}


def fetch_creative_outputs(api_key: str, swarm_id: str, creative_type: str = None) -> List[Dict]:
    """Fetch creative outputs"""
    return []


# ============================================================================
# ZAPIER TRIGGER DEFINITIONS (JSON)
# ============================================================================

TRIGGERS = {
    "task_completed": {
        "key": "task_completed",
        "noun": "Task",
        "display": {
            "label": "Task Completed",
            "description": "Triggers when a task completes successfully"
        },
        "operation": {
            "perform": task_completed_trigger,
            "inputFields": [
                {
                    "key": "swarm_id",
                    "label": "Swarm ID",
                    "type": "string",
                    "required": False,
                    "helpText": "Filter to specific swarm (optional)"
                }
            ],
            "sample": {
                "task_id": "task_abc123",
                "swarm_id": "swarm_xyz789",
                "type": "image_generation",
                "status": "COMPLETED",
                "result": {
                    "image_url": "https://example.com/image.png"
                }
            }
        }
    },
    "swarm_error": {
        "key": "swarm_error",
        "noun": "Error",
        "display": {
            "label": "Swarm Error",
            "description": "Triggers when a swarm encounters an error"
        },
        "operation": {
            "perform": swarm_error_trigger,
            "sample": {
                "swarm_id": "swarm_xyz789",
                "error_type": "AGENT_FAILURE",
                "message": "Agent coordination timeout",
                "timestamp": "2025-10-14T10:00:00Z"
            }
        }
    },
    "metrics_threshold": {
        "key": "metrics_threshold",
        "noun": "Metric",
        "display": {
            "label": "Metrics Threshold",
            "description": "Triggers when metrics exceed thresholds"
        },
        "operation": {
            "perform": metrics_threshold_trigger,
            "inputFields": [
                {
                    "key": "swarm_id",
                    "label": "Swarm ID",
                    "type": "string",
                    "required": True
                },
                {
                    "key": "metric",
                    "label": "Metric",
                    "type": "string",
                    "required": True,
                    "choices": [
                        "error_rate",
                        "agent_utilization",
                        "throughput_per_second",
                        "average_latency_ms"
                    ]
                },
                {
                    "key": "threshold",
                    "label": "Threshold Value",
                    "type": "number",
                    "required": True
                },
                {
                    "key": "condition",
                    "label": "Condition",
                    "type": "string",
                    "required": True,
                    "choices": [
                        "greater_than",
                        "less_than"
                    ]
                }
            ]
        }
    },
    "creative_output_ready": {
        "key": "creative_output_ready",
        "noun": "Creative Output",
        "display": {
            "label": "Creative Output Ready",
            "description": "Triggers when creative content is generated"
        },
        "operation": {
            "perform": creative_output_ready_trigger,
            "inputFields": [
                {
                    "key": "swarm_id",
                    "label": "Swarm ID",
                    "type": "string",
                    "required": False
                },
                {
                    "key": "creative_type",
                    "label": "Content Type",
                    "type": "string",
                    "required": False,
                    "choices": ["art", "music", "narrative", "video"]
                }
            ]
        }
    }
}
