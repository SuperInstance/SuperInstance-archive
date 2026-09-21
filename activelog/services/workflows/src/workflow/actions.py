"""
Action system for IFTTT-style workflow automation

Supports various action types:
- HTTP requests
- Email sending
- Slack messaging
- Database operations
- File operations
- Webhooks
- Conditional logic
- Delays
- Custom actions
"""

import asyncio
import json
import logging
import smtplib
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin

import httpx
from jinja2 import Template

from core.database import ActionType
from .context import ExecutionContext

logger = logging.getLogger(__name__)

class ActionResult:
    """Result of action execution"""
    
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None, 
                 metadata: Dict[str, Any] = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

class BaseAction(ABC):
    """Base class for all actions"""
    
    def __init__(self, action_type: str):
        self.action_type = action_type
    
    @abstractmethod
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute the action"""
        pass
    
    def render_template(self, template_str: str, context: ExecutionContext) -> str:
        """Render template string with context variables"""
        try:
            template = Template(template_str)
            return template.render(**context.get_all_variables())
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return template_str
    
    def extract_config_values(self, config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Extract and render config values with context"""
        rendered_config = {}
        
        for key, value in config.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                rendered_config[key] = self.render_template(value, context)
            elif isinstance(value, dict):
                rendered_config[key] = self.extract_config_values(value, context)
            elif isinstance(value, list):
                rendered_config[key] = [
                    self.render_template(item, context) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                rendered_config[key] = value
        
        return rendered_config

class HTTPRequestAction(BaseAction):
    """HTTP request action"""
    
    def __init__(self):
        super().__init__(ActionType.HTTP_REQUEST.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute HTTP request"""
        
        try:
            # Extract and render configuration
            rendered_config = self.extract_config_values(config, context)
            
            url = rendered_config.get("url")
            method = rendered_config.get("method", "GET").upper()
            headers = rendered_config.get("headers", {})
            params = rendered_config.get("params", {})
            data = rendered_config.get("data")
            json_data = rendered_config.get("json")
            timeout = rendered_config.get("timeout", 30)
            
            if not url:
                return ActionResult(False, error="URL is required for HTTP request")
            
            # Make HTTP request
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data
                )
            
            # Parse response
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url)
            }
            
            try:
                response_data["json"] = response.json()
            except:
                response_data["text"] = response.text
            
            # Check if request was successful
            success = 200 <= response.status_code < 300
            
            return ActionResult(
                success=success,
                data=response_data,
                error=f"HTTP {response.status_code}" if not success else None,
                metadata={
                    "action_type": "http_request",
                    "method": method,
                    "url": url,
                    "status_code": response.status_code
                }
            )
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "http_request"}
            )

class EmailAction(BaseAction):
    """Email sending action"""
    
    def __init__(self):
        super().__init__(ActionType.EMAIL.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute email sending"""
        
        try:
            # Extract and render configuration
            rendered_config = self.extract_config_values(config, context)
            
            to_email = rendered_config.get("to")
            from_email = rendered_config.get("from")
            subject = rendered_config.get("subject", "")
            body = rendered_config.get("body", "")
            body_html = rendered_config.get("body_html")
            
            # SMTP configuration
            smtp_host = rendered_config.get("smtp_host", "localhost")
            smtp_port = rendered_config.get("smtp_port", 587)
            smtp_user = rendered_config.get("smtp_user")
            smtp_password = rendered_config.get("smtp_password")
            use_tls = rendered_config.get("use_tls", True)
            
            if not to_email or not from_email:
                return ActionResult(False, error="to and from email addresses are required")
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text part
            if body:
                text_part = MIMEText(body, 'plain')
                msg.attach(text_part)
            
            # Add HTML part
            if body_html:
                html_part = MIMEText(body_html, 'html')
                msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP(smtp_host, smtp_port)
            
            if use_tls:
                server.starttls()
            
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            return ActionResult(
                success=True,
                data={
                    "to": to_email,
                    "from": from_email,
                    "subject": subject,
                    "sent_at": datetime.utcnow().isoformat()
                },
                metadata={
                    "action_type": "email",
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port
                }
            )
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "email"}
            )

class SlackAction(BaseAction):
    """Slack messaging action"""
    
    def __init__(self):
        super().__init__(ActionType.SLACK.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute Slack message"""
        
        try:
            # Extract and render configuration
            rendered_config = self.extract_config_values(config, context)
            
            webhook_url = rendered_config.get("webhook_url")
            channel = rendered_config.get("channel")
            text = rendered_config.get("text", "")
            username = rendered_config.get("username", "Workflow Bot")
            icon_emoji = rendered_config.get("icon_emoji", ":robot_face:")
            
            if not webhook_url:
                return ActionResult(False, error="webhook_url is required for Slack action")
            
            # Prepare Slack payload
            payload = {
                "text": text,
                "username": username,
                "icon_emoji": icon_emoji
            }
            
            if channel:
                payload["channel"] = channel
            
            # Send to Slack
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
            
            success = response.status_code == 200
            
            return ActionResult(
                success=success,
                data={
                    "channel": channel,
                    "text": text,
                    "sent_at": datetime.utcnow().isoformat()
                },
                error="Failed to send Slack message" if not success else None,
                metadata={
                    "action_type": "slack",
                    "status_code": response.status_code
                }
            )
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "slack"}
            )

class DatabaseAction(BaseAction):
    """Database operation action"""
    
    def __init__(self):
        super().__init__(ActionType.DATABASE.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute database operation"""
        
        try:
            # Extract and render configuration
            rendered_config = self.extract_config_values(config, context)
            
            operation = rendered_config.get("operation", "select").lower()
            table = rendered_config.get("table")
            query = rendered_config.get("query")
            values = rendered_config.get("values", {})
            
            if not table and not query:
                return ActionResult(False, error="table or query is required for database action")
            
            from core.database import db_manager
            
            if query:
                # Execute custom query
                if operation in ["insert", "update", "delete"]:
                    result = await db_manager.database.execute(query, values)
                    return ActionResult(
                        success=True,
                        data={"rows_affected": result},
                        metadata={"action_type": "database", "operation": operation}
                    )
                else:
                    rows = await db_manager.database.fetch_all(query, values)
                    return ActionResult(
                        success=True,
                        data=[dict(row) for row in rows],
                        metadata={"action_type": "database", "operation": operation}
                    )
            else:
                # Simple table operations
                if operation == "select":
                    where_clause = rendered_config.get("where", "")
                    query = f"SELECT * FROM {table}"
                    if where_clause:
                        query += f" WHERE {where_clause}"
                    
                    rows = await db_manager.database.fetch_all(query, values)
                    return ActionResult(
                        success=True,
                        data=[dict(row) for row in rows],
                        metadata={"action_type": "database", "operation": "select"}
                    )
                
                elif operation == "insert":
                    columns = ", ".join(values.keys())
                    placeholders = ", ".join([f":{k}" for k in values.keys()])
                    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                    
                    result = await db_manager.database.execute(query, values)
                    return ActionResult(
                        success=True,
                        data={"rows_inserted": result},
                        metadata={"action_type": "database", "operation": "insert"}
                    )
                
                else:
                    return ActionResult(False, error=f"Unsupported database operation: {operation}")
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "database"}
            )

class FileOperationAction(BaseAction):
    """File operation action"""
    
    def __init__(self):
        super().__init__(ActionType.FILE_OPERATION.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute file operation"""
        
        try:
            # Extract and render configuration
            rendered_config = self.extract_config_values(config, context)
            
            operation = rendered_config.get("operation", "read").lower()
            file_path = rendered_config.get("file_path")
            content = rendered_config.get("content")
            encoding = rendered_config.get("encoding", "utf-8")
            
            if not file_path:
                return ActionResult(False, error="file_path is required for file operation")
            
            path = Path(file_path)
            
            if operation == "read":
                if not path.exists():
                    return ActionResult(False, error=f"File does not exist: {file_path}")
                
                file_content = path.read_text(encoding=encoding)
                
                return ActionResult(
                    success=True,
                    data={
                        "content": file_content,
                        "file_path": str(path),
                        "size": path.stat().st_size,
                        "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                    },
                    metadata={"action_type": "file_operation", "operation": "read"}
                )
            
            elif operation == "write":
                if content is None:
                    return ActionResult(False, error="content is required for file write operation")
                
                # Create parent directories if they don't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                
                path.write_text(content, encoding=encoding)
                
                return ActionResult(
                    success=True,
                    data={
                        "file_path": str(path),
                        "size": path.stat().st_size,
                        "written_at": datetime.utcnow().isoformat()
                    },
                    metadata={"action_type": "file_operation", "operation": "write"}
                )
            
            elif operation == "append":
                if content is None:
                    return ActionResult(False, error="content is required for file append operation")
                
                # Create parent directories if they don't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                
                with path.open('a', encoding=encoding) as f:
                    f.write(content)
                
                return ActionResult(
                    success=True,
                    data={
                        "file_path": str(path),
                        "size": path.stat().st_size,
                        "appended_at": datetime.utcnow().isoformat()
                    },
                    metadata={"action_type": "file_operation", "operation": "append"}
                )
            
            elif operation == "delete":
                if not path.exists():
                    return ActionResult(False, error=f"File does not exist: {file_path}")
                
                path.unlink()
                
                return ActionResult(
                    success=True,
                    data={
                        "file_path": str(path),
                        "deleted_at": datetime.utcnow().isoformat()
                    },
                    metadata={"action_type": "file_operation", "operation": "delete"}
                )
            
            else:
                return ActionResult(False, error=f"Unsupported file operation: {operation}")
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "file_operation"}
            )

class WebhookAction(BaseAction):
    """Webhook calling action"""
    
    def __init__(self):
        super().__init__(ActionType.WEBHOOK.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute webhook call"""
        
        try:
            # Extract and render configuration
            rendered_config = self.extract_config_values(config, context)
            
            url = rendered_config.get("url")
            method = rendered_config.get("method", "POST").upper()
            headers = rendered_config.get("headers", {})
            data = rendered_config.get("data")
            json_data = rendered_config.get("json")
            timeout = rendered_config.get("timeout", 30)
            
            if not url:
                return ActionResult(False, error="URL is required for webhook action")
            
            # Set default headers for webhook
            default_headers = {
                "User-Agent": "ActiveLog-Workflows/1.0",
                "Content-Type": "application/json"
            }
            headers = {**default_headers, **headers}
            
            # Make webhook request
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    json=json_data
                )
            
            # Parse response
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url)
            }
            
            try:
                response_data["json"] = response.json()
            except:
                response_data["text"] = response.text
            
            # Check if webhook was successful
            success = 200 <= response.status_code < 300
            
            return ActionResult(
                success=success,
                data=response_data,
                error=f"Webhook failed with status {response.status_code}" if not success else None,
                metadata={
                    "action_type": "webhook",
                    "method": method,
                    "url": url,
                    "status_code": response.status_code
                }
            )
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "webhook"}
            )

class ConditionAction(BaseAction):
    """Conditional logic action"""
    
    def __init__(self):
        super().__init__(ActionType.CONDITION.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute conditional logic"""
        
        try:
            # Extract configuration
            condition = config.get("condition")
            if_true_actions = config.get("if_true", [])
            if_false_actions = config.get("if_false", [])
            
            if not condition:
                return ActionResult(False, error="condition is required for condition action")
            
            # Evaluate condition
            from .conditions import ConditionEvaluator
            evaluator = ConditionEvaluator(context)
            result = await evaluator.evaluate(condition)
            
            # Execute appropriate actions
            actions_to_execute = if_true_actions if result else if_false_actions
            
            return ActionResult(
                success=True,
                data={
                    "condition_result": result,
                    "actions_to_execute": len(actions_to_execute),
                    "branch_taken": "if_true" if result else "if_false"
                },
                metadata={
                    "action_type": "condition",
                    "condition_result": result
                }
            )
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "condition"}
            )

class DelayAction(BaseAction):
    """Delay/wait action"""
    
    def __init__(self):
        super().__init__(ActionType.DELAY.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute delay"""
        
        try:
            # Extract and render configuration
            rendered_config = self.extract_config_values(config, context)
            
            seconds = rendered_config.get("seconds", 1)
            
            if not isinstance(seconds, (int, float)) or seconds < 0:
                return ActionResult(False, error="seconds must be a positive number")
            
            # Execute delay
            start_time = time.time()
            await asyncio.sleep(seconds)
            actual_delay = time.time() - start_time
            
            return ActionResult(
                success=True,
                data={
                    "requested_delay_seconds": seconds,
                    "actual_delay_seconds": actual_delay,
                    "completed_at": datetime.utcnow().isoformat()
                },
                metadata={"action_type": "delay"}
            )
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "delay"}
            )

class CustomAction(BaseAction):
    """Custom action for user-defined logic"""
    
    def __init__(self):
        super().__init__(ActionType.CUSTOM.value)
    
    async def execute(self, config: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        """Execute custom action"""
        
        try:
            # Extract configuration
            script = config.get("script")
            language = config.get("language", "javascript")
            
            if not script:
                return ActionResult(False, error="script is required for custom action")
            
            # For now, we'll just return the script information
            # In a full implementation, you might execute the script in a sandbox
            
            return ActionResult(
                success=True,
                data={
                    "script": script,
                    "language": language,
                    "executed_at": datetime.utcnow().isoformat(),
                    "note": "Custom script execution not implemented in this demo"
                },
                metadata={
                    "action_type": "custom",
                    "language": language
                }
            )
            
        except Exception as e:
            return ActionResult(
                False,
                error=str(e),
                metadata={"action_type": "custom"}
            )

class ActionRegistry:
    """Registry for managing all action types"""
    
    def __init__(self):
        self.actions: Dict[str, BaseAction] = {}
    
    async def initialize(self):
        """Initialize action registry with built-in actions"""
        
        # Register built-in actions
        self.register_action("http_request", HTTPRequestAction())
        self.register_action("email", EmailAction())
        self.register_action("slack", SlackAction())
        self.register_action("database", DatabaseAction())
        self.register_action("file_operation", FileOperationAction())
        self.register_action("webhook", WebhookAction())
        self.register_action("condition", ConditionAction())
        self.register_action("delay", DelayAction())
        self.register_action("custom", CustomAction())
        
        logger.info(f"Action registry initialized with {len(self.actions)} action types")
    
    def register_action(self, action_type: str, action_instance: BaseAction):
        """Register a new action type"""
        self.actions[action_type] = action_instance
        logger.debug(f"Registered action type: {action_type}")
    
    def get_action(self, action_type: str) -> Optional[BaseAction]:
        """Get action instance by type"""
        return self.actions.get(action_type)
    
    def get_action_types(self) -> List[str]:
        """Get list of available action types"""
        return list(self.actions.keys())
    
    async def cleanup(self):
        """Clean up action registry"""
        self.actions.clear()
        logger.info("Action registry cleaned up")