"""
Slack Bot Integration
Natural language interface for swarm management via Slack
"""

from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
import os
import re


# Initialize Slack app
slack_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

handler = SlackRequestHandler(slack_app)


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@slack_app.command("/swarm-create")
def handle_create_swarm(ack, command, say):
    """
    Create swarm via Slack command
    Usage: /swarm-create name=my-swarm agents=10 type=WORKER
    """
    ack()

    # Parse command text
    text = command['text']
    params = parse_command_params(text)

    name = params.get('name', f"swarm-{command['user_id']}")
    agent_count = int(params.get('agents', 10))
    agent_type = params.get('type', 'WORKER')

    # Create swarm (call API)
    swarm = create_swarm(name, agent_count, agent_type)

    say({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Swarm Created!* :rocket:\n\nID: `{swarm['swarm_id']}`\nName: {name}\nAgents: {agent_count}\nStatus: {swarm['status']}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Status"},
                        "action_id": "view_swarm_status",
                        "value": swarm['swarm_id']
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Submit Task"},
                        "action_id": "submit_task",
                        "value": swarm['swarm_id']
                    }
                ]
            }
        ]
    })


@slack_app.command("/swarm-status")
def handle_swarm_status(ack, command, say):
    """
    Check swarm status
    Usage: /swarm-status swarm_abc123
    """
    ack()

    swarm_id = command['text'].strip()
    if not swarm_id:
        say("Please provide a swarm ID: `/swarm-status swarm_abc123`")
        return

    # Fetch swarm status
    swarm = get_swarm_status(swarm_id)

    if not swarm:
        say(f"Swarm `{swarm_id}` not found")
        return

    metrics = swarm.get('metrics', {})

    say({
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Swarm Status: {swarm['name']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*ID:*\n`{swarm['swarm_id']}`"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{swarm['status']}"},
                    {"type": "mrkdwn", "text": f"*Agents:*\n{swarm['agent_count']}"},
                    {"type": "mrkdwn", "text": f"*Type:*\n{swarm['agent_type']}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Metrics:*\nTasks: {metrics.get('tasks_completed', 0)} | Utilization: {metrics.get('agent_utilization', 0)*100:.1f}% | Errors: {metrics.get('error_rate', 0)*100:.1f}%"
                }
            }
        ]
    })


@slack_app.command("/swarm-task")
def handle_submit_task(ack, command, respond):
    """
    Submit task via Slack
    Usage: /swarm-task swarm_abc123 type=process payload={"data": "test"}
    """
    ack()

    parts = command['text'].split(maxsplit=1)
    if len(parts) < 2:
        respond("Usage: `/swarm-task <swarm_id> type=<type> payload=<json>`")
        return

    swarm_id = parts[0]
    params = parse_command_params(parts[1])

    task_type = params.get('type')
    payload = params.get('payload', '{}')

    if not task_type:
        respond("Please specify task type: `type=process`")
        return

    # Submit task
    task = submit_task(swarm_id, task_type, payload)

    respond({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Task Submitted* :white_check_mark:\n\nTask ID: `{task['task_id']}`\nType: {task_type}\nStatus: {task['status']}"
                }
            }
        ]
    })


# ============================================================================
# INTERACTIVE COMPONENTS
# ============================================================================

@slack_app.action("view_swarm_status")
def handle_view_status(ack, body, say):
    """Handle view status button click"""
    ack()
    swarm_id = body['actions'][0]['value']

    # Fetch and display status
    swarm = get_swarm_status(swarm_id)
    # Display status message
    say(f"Swarm {swarm_id} status: {swarm['status']}")


@slack_app.action("submit_task")
def handle_submit_task_button(ack, body, client):
    """Handle submit task button - open modal"""
    ack()
    swarm_id = body['actions'][0]['value']

    # Open modal for task submission
    client.views_open(
        trigger_id=body['trigger_id'],
        view={
            "type": "modal",
            "callback_id": "submit_task_modal",
            "title": {"type": "plain_text", "text": "Submit Task"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "task_type",
                    "label": {"type": "plain_text", "text": "Task Type"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "task_type_input"
                    }
                },
                {
                    "type": "input",
                    "block_id": "task_payload",
                    "label": {"type": "plain_text", "text": "Payload (JSON)"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "payload_input",
                        "multiline": True
                    }
                }
            ],
            "private_metadata": swarm_id
        }
    )


# ============================================================================
# NATURAL LANGUAGE PROCESSING
# ============================================================================

@slack_app.event("app_mention")
def handle_mention(event, say):
    """
    Handle @bot mentions with natural language
    Examples:
    - "@swarmbot create a swarm with 20 workers"
    - "@swarmbot show me the status of swarm_abc123"
    - "@swarmbot submit an image generation task"
    """
    text = event['text'].lower()
    user = event['user']

    # Intent detection
    if 'create' in text and 'swarm' in text:
        # Extract parameters from natural language
        agent_count = extract_number(text) or 10
        say(f"<@{user}> Creating swarm with {agent_count} agents...")
        # Create swarm
        swarm = create_swarm(f"swarm-{user}", agent_count, "WORKER")
        say(f"Swarm created: `{swarm['swarm_id']}`")

    elif 'status' in text or 'show' in text:
        # Extract swarm ID
        swarm_id = extract_swarm_id(text)
        if swarm_id:
            swarm = get_swarm_status(swarm_id)
            say(f"Swarm {swarm_id} is {swarm['status']} with {swarm['agent_count']} agents")
        else:
            say("Please specify a swarm ID")

    elif 'task' in text or 'submit' in text:
        say(f"<@{user}> Please use `/swarm-task` command to submit tasks")

    else:
        say(f"Hi <@{user}>! I can help you manage swarms. Try:\n• Create a swarm\n• Check status\n• Submit tasks\n\nUse `/swarm-create`, `/swarm-status`, or `/swarm-task`")


# ============================================================================
# NOTIFICATIONS
# ============================================================================

async def send_task_completion_notification(channel_id: str, task: dict):
    """Send notification when task completes"""
    slack_app.client.chat_postMessage(
        channel=channel_id,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Task Completed* :tada:\n\nTask ID: `{task['task_id']}`\nType: {task['type']}\nResult: {task.get('result', 'N/A')}"
                }
            }
        ]
    )


async def send_swarm_error_notification(channel_id: str, error: dict):
    """Send notification when swarm encounters error"""
    slack_app.client.chat_postMessage(
        channel=channel_id,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Swarm Error* :warning:\n\nSwarm: `{error['swarm_id']}`\nError: {error['message']}"
                }
            }
        ]
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_command_params(text: str) -> dict:
    """Parse key=value pairs from command text"""
    params = {}
    pattern = r'(\w+)=([^\s]+)'
    matches = re.findall(pattern, text)
    for key, value in matches:
        params[key] = value
    return params


def extract_number(text: str) -> int:
    """Extract first number from text"""
    match = re.search(r'\d+', text)
    return int(match.group()) if match else None


def extract_swarm_id(text: str) -> str:
    """Extract swarm ID from text"""
    match = re.search(r'swarm_[a-z0-9]+', text)
    return match.group() if match else None


def create_swarm(name: str, agent_count: int, agent_type: str) -> dict:
    """Create swarm via API"""
    # Implementation: Call swarm API
    return {
        "swarm_id": "swarm_abc123",
        "name": name,
        "status": "INITIALIZING",
        "agent_count": agent_count,
        "agent_type": agent_type
    }


def get_swarm_status(swarm_id: str) -> dict:
    """Get swarm status from API"""
    # Implementation: Call swarm API
    return {}


def submit_task(swarm_id: str, task_type: str, payload: str) -> dict:
    """Submit task via API"""
    # Implementation: Call swarm API
    return {
        "task_id": "task_xyz789",
        "swarm_id": swarm_id,
        "type": task_type,
        "status": "QUEUED"
    }
