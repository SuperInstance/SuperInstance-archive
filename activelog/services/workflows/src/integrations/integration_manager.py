"""
Integration Manager for External Services

Handles:
- Service authentication (OAuth, API keys, etc.)
- Service-specific API clients
- Rate limiting per service
- Integration health monitoring
- Configuration management
- Credential encryption
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib
import hmac
import base64

import httpx
from cryptography.fernet import Fernet

from core.database import db_manager, IntegrationStatus
from core.config import settings

logger = logging.getLogger(__name__)

class AuthType(Enum):
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    WEBHOOK = "webhook"

@dataclass
class ServiceConfig:
    """Configuration for an external service integration"""
    service_name: str
    display_name: str
    description: str
    auth_type: AuthType
    base_url: str
    api_version: Optional[str] = None
    rate_limits: Dict[str, int] = field(default_factory=dict)
    required_scopes: List[str] = field(default_factory=list)
    webhook_support: bool = False
    supports_pagination: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30

class BaseIntegration(ABC):
    """Base class for all service integrations"""
    
    def __init__(self, service_name: str, config: Dict[str, Any], auth_data: Dict[str, Any] = None):
        self.service_name = service_name
        self.config = config
        self.auth_data = auth_data or {}
        self.client: Optional[httpx.AsyncClient] = None
        self.rate_limiter = None
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the service"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to service"""
        pass
    
    @abstractmethod
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Get OAuth authorization URL (if applicable)"""
        pass
    
    async def initialize(self) -> bool:
        """Initialize the integration"""
        try:
            await self.authenticate()
            return await self.test_connection()
        except Exception as e:
            logger.error(f"Error initializing {self.service_name} integration: {e}")
            return False
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to service API"""
        if not self.client:
            await self._create_client()
        
        url = f"{self.config.get('base_url', '')}/{endpoint.lstrip('/')}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {"text": response.text}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"{self.service_name} API error: {e}")
            raise
        except Exception as e:
            logger.error(f"{self.service_name} request error: {e}")
            raise
    
    async def _create_client(self):
        """Create HTTP client with authentication"""
        headers = await self._get_auth_headers()
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=self.config.get('timeout_seconds', 30)
        )
    
    @abstractmethod
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        pass
    
    async def cleanup(self):
        """Clean up integration resources"""
        if self.client:
            await self.client.aclose()

class SlackIntegration(BaseIntegration):
    """Slack service integration"""
    
    def __init__(self, config: Dict[str, Any], auth_data: Dict[str, Any] = None):
        super().__init__("slack", config, auth_data)
        self.webhook_url = config.get("webhook_url")
        self.bot_token = auth_data.get("bot_token")
    
    async def authenticate(self) -> bool:
        """Authenticate with Slack"""
        if self.webhook_url or self.bot_token:
            return True
        return False
    
    async def test_connection(self) -> bool:
        """Test Slack connection"""
        try:
            if self.bot_token:
                # Test bot token with auth.test
                response = await self.make_request("POST", "auth.test")
                return response.get("ok", False)
            elif self.webhook_url:
                # Test webhook with a simple message
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.webhook_url, json={
                        "text": "Test connection from ActiveLog Workflows"
                    })
                    return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False
        
        return False
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Get Slack OAuth URL"""
        client_id = self.config.get("client_id")
        scopes = ",".join(self.config.get("scopes", ["chat:write", "channels:read"]))
        
        return f"https://slack.com/oauth/v2/authorize?client_id={client_id}&scope={scopes}&redirect_uri={redirect_uri}"
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get Slack auth headers"""
        headers = {"Content-Type": "application/json"}
        
        if self.bot_token:
            headers["Authorization"] = f"Bearer {self.bot_token}"
        
        return headers
    
    async def send_message(self, channel: str, text: str, **kwargs) -> Dict[str, Any]:
        """Send message to Slack channel"""
        if self.webhook_url:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json={
                    "channel": channel,
                    "text": text,
                    **kwargs
                })
                return {"ok": response.status_code == 200}
        elif self.bot_token:
            return await self.make_request("POST", "chat.postMessage", json={
                "channel": channel,
                "text": text,
                **kwargs
            })
        
        raise Exception("No authentication method available")

class EmailIntegration(BaseIntegration):
    """Email service integration (SMTP)"""
    
    def __init__(self, config: Dict[str, Any], auth_data: Dict[str, Any] = None):
        super().__init__("email", config, auth_data)
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = auth_data.get("username")
        self.password = auth_data.get("password")
        self.use_tls = config.get("use_tls", True)
    
    async def authenticate(self) -> bool:
        """Authenticate with SMTP server"""
        return bool(self.username and self.password)
    
    async def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            import smtplib
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.quit()
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Email doesn't use OAuth"""
        return ""
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Email doesn't use HTTP headers for auth"""
        return {}
    
    async def send_email(self, to_email: str, subject: str, body: str, 
                        from_email: str = None, **kwargs) -> Dict[str, Any]:
        """Send email"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = from_email or self.username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            
            return {"success": True, "message": "Email sent successfully"}
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return {"success": False, "error": str(e)}

class GitHubIntegration(BaseIntegration):
    """GitHub service integration"""
    
    def __init__(self, config: Dict[str, Any], auth_data: Dict[str, Any] = None):
        super().__init__("github", config, auth_data)
        self.config["base_url"] = "https://api.github.com"
        self.access_token = auth_data.get("access_token")
    
    async def authenticate(self) -> bool:
        """Authenticate with GitHub"""
        return bool(self.access_token)
    
    async def test_connection(self) -> bool:
        """Test GitHub connection"""
        try:
            response = await self.make_request("GET", "user")
            return "login" in response
        except Exception as e:
            logger.error(f"GitHub connection test failed: {e}")
            return False
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Get GitHub OAuth URL"""
        client_id = self.config.get("client_id")
        scopes = ",".join(self.config.get("scopes", ["repo", "user"]))
        
        return f"https://github.com/login/oauth/authorize?client_id={client_id}&scope={scopes}&redirect_uri={redirect_uri}"
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get GitHub auth headers"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ActiveLog-Workflows/1.0"
        }
        
        if self.access_token:
            headers["Authorization"] = f"token {self.access_token}"
        
        return headers
    
    async def create_issue(self, repo: str, title: str, body: str = None, **kwargs) -> Dict[str, Any]:
        """Create GitHub issue"""
        return await self.make_request("POST", f"repos/{repo}/issues", json={
            "title": title,
            "body": body,
            **kwargs
        })
    
    async def get_repositories(self, username: str = None) -> List[Dict[str, Any]]:
        """Get user repositories"""
        if username:
            endpoint = f"users/{username}/repos"
        else:
            endpoint = "user/repos"
        
        response = await self.make_request("GET", endpoint)
        return response if isinstance(response, list) else []

class GoogleSheetsIntegration(BaseIntegration):
    """Google Sheets service integration"""
    
    def __init__(self, config: Dict[str, Any], auth_data: Dict[str, Any] = None):
        super().__init__("google_sheets", config, auth_data)
        self.config["base_url"] = "https://sheets.googleapis.com/v4"
        self.access_token = auth_data.get("access_token")
        self.refresh_token = auth_data.get("refresh_token")
    
    async def authenticate(self) -> bool:
        """Authenticate with Google Sheets"""
        return bool(self.access_token)
    
    async def test_connection(self) -> bool:
        """Test Google Sheets connection"""
        try:
            # Try to list spreadsheets (requires Drive API)
            response = await self.make_request("GET", "spreadsheets")
            return True
        except Exception as e:
            logger.error(f"Google Sheets connection test failed: {e}")
            return False
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Get Google OAuth URL"""
        client_id = self.config.get("client_id")
        scopes = "%20".join(self.config.get("scopes", [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]))
        
        return f"https://accounts.google.com/o/oauth2/auth?client_id={client_id}&scope={scopes}&redirect_uri={redirect_uri}&response_type=code&access_type=offline"
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get Google Sheets auth headers"""
        headers = {"Content-Type": "application/json"}
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        return headers
    
    async def read_sheet(self, spreadsheet_id: str, range_name: str) -> Dict[str, Any]:
        """Read data from Google Sheet"""
        return await self.make_request("GET", f"spreadsheets/{spreadsheet_id}/values/{range_name}")
    
    async def write_sheet(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> Dict[str, Any]:
        """Write data to Google Sheet"""
        return await self.make_request("PUT", f"spreadsheets/{spreadsheet_id}/values/{range_name}", json={
            "valueInputOption": "RAW",
            "values": values
        })

class IntegrationManager:
    """Manages all external service integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, BaseIntegration] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.encryption_key = self._get_or_create_encryption_key()
        
        self.stats = {
            "total_integrations": 0,
            "active_integrations": 0,
            "failed_integrations": 0,
            "api_requests_made": 0,
            "api_errors": 0
        }
    
    def _get_or_create_encryption_key(self) -> Fernet:
        """Get or create encryption key for credentials"""
        # In production, this should be stored securely
        key = settings.SECRET_KEY.encode()[:32]  # Use first 32 chars
        key = base64.urlsafe_b64encode(key.ljust(32)[:32])
        return Fernet(key)
    
    async def initialize(self):
        """Initialize integration manager"""
        
        # Register built-in service configurations
        await self._register_service_configs()
        
        # Load user integrations from database
        await self._load_user_integrations()
        
        logger.info(f"Integration manager initialized with {len(self.service_configs)} service types")
    
    async def _register_service_configs(self):
        """Register built-in service configurations"""
        
        # Slack
        self.service_configs["slack"] = ServiceConfig(
            service_name="slack",
            display_name="Slack",
            description="Team communication and collaboration",
            auth_type=AuthType.OAUTH2,
            base_url="https://slack.com/api",
            rate_limits={"requests_per_minute": 100},
            required_scopes=["chat:write", "channels:read"],
            webhook_support=True
        )
        
        # Email (SMTP)
        self.service_configs["email"] = ServiceConfig(
            service_name="email",
            display_name="Email",
            description="Send emails via SMTP",
            auth_type=AuthType.BASIC_AUTH,
            base_url="smtp://localhost:587",
            rate_limits={"emails_per_hour": 100}
        )
        
        # GitHub
        self.service_configs["github"] = ServiceConfig(
            service_name="github",
            display_name="GitHub",
            description="Version control and collaboration",
            auth_type=AuthType.OAUTH2,
            base_url="https://api.github.com",
            rate_limits={"requests_per_hour": 5000},
            required_scopes=["repo", "user"],
            webhook_support=True
        )
        
        # Google Sheets
        self.service_configs["google_sheets"] = ServiceConfig(
            service_name="google_sheets",
            display_name="Google Sheets",
            description="Spreadsheet management",
            auth_type=AuthType.OAUTH2,
            base_url="https://sheets.googleapis.com/v4",
            rate_limits={"requests_per_100_seconds": 300},
            required_scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        # Webhook (generic)
        self.service_configs["webhook"] = ServiceConfig(
            service_name="webhook",
            display_name="Generic Webhook",
            description="HTTP webhooks to any endpoint",
            auth_type=AuthType.API_KEY,
            base_url="",
            rate_limits={"requests_per_minute": 1000},
            webhook_support=True
        )
    
    async def _load_user_integrations(self):
        """Load user integrations from database"""
        try:
            query = """
            SELECT id, user_id, service_name, integration_name, status, config, auth_data, created_at
            FROM integrations
            WHERE status = :status
            """
            
            rows = await db_manager.database.fetch_all(query, {
                "status": IntegrationStatus.ACTIVE.value
            })
            
            for row in rows:
                try:
                    # Decrypt auth data
                    encrypted_auth = row["auth_data"]
                    if encrypted_auth:
                        decrypted_auth = self._decrypt_data(encrypted_auth)
                        auth_data = json.loads(decrypted_auth)
                    else:
                        auth_data = {}
                    
                    # Parse config
                    config = json.loads(row["config"]) if isinstance(row["config"], str) else row["config"]
                    
                    # Create integration instance
                    integration = await self._create_integration_instance(
                        row["service_name"], config, auth_data
                    )
                    
                    if integration and await integration.initialize():
                        integration_key = f"{row['user_id']}:{row['service_name']}:{row['integration_name']}"
                        self.integrations[integration_key] = integration
                        self.stats["active_integrations"] += 1
                    else:
                        self.stats["failed_integrations"] += 1
                        
                except Exception as e:
                    logger.error(f"Error loading integration {row['id']}: {e}")
                    self.stats["failed_integrations"] += 1
            
            self.stats["total_integrations"] = len(rows)
            
        except Exception as e:
            logger.error(f"Error loading user integrations: {e}")
    
    async def _create_integration_instance(self, service_name: str, config: Dict[str, Any], 
                                         auth_data: Dict[str, Any]) -> Optional[BaseIntegration]:
        """Create integration instance for service"""
        
        integration_classes = {
            "slack": SlackIntegration,
            "email": EmailIntegration,
            "github": GitHubIntegration,
            "google_sheets": GoogleSheetsIntegration
        }
        
        integration_class = integration_classes.get(service_name)
        if not integration_class:
            logger.warning(f"Unknown service type: {service_name}")
            return None
        
        try:
            return integration_class(config, auth_data)
        except Exception as e:
            logger.error(f"Error creating {service_name} integration: {e}")
            return None
    
    async def create_integration(self, user_id: str, service_name: str, integration_name: str,
                               config: Dict[str, Any], auth_data: Dict[str, Any] = None) -> str:
        """Create new integration for user"""
        
        if service_name not in self.service_configs:
            raise ValueError(f"Unknown service: {service_name}")
        
        try:
            # Create integration instance
            integration = await self._create_integration_instance(service_name, config, auth_data or {})
            if not integration:
                raise Exception(f"Failed to create {service_name} integration")
            
            # Test integration
            if not await integration.initialize():
                raise Exception(f"Integration test failed for {service_name}")
            
            # Encrypt auth data
            encrypted_auth = None
            if auth_data:
                encrypted_auth = self._encrypt_data(json.dumps(auth_data))
            
            # Save to database
            integration_id = str(uuid.uuid4())
            query = """
            INSERT INTO integrations (id, user_id, service_name, integration_name, status,
                                    config, auth_data, created_at)
            VALUES (:id, :user_id, :service_name, :integration_name, :status,
                    :config, :auth_data, :created_at)
            """
            
            values = {
                "id": integration_id,
                "user_id": user_id,
                "service_name": service_name,
                "integration_name": integration_name,
                "status": IntegrationStatus.ACTIVE.value,
                "config": json.dumps(config),
                "auth_data": encrypted_auth,
                "created_at": datetime.utcnow()
            }
            
            await db_manager.database.execute(query, values)
            
            # Store in memory
            integration_key = f"{user_id}:{service_name}:{integration_name}"
            self.integrations[integration_key] = integration
            
            self.stats["total_integrations"] += 1
            self.stats["active_integrations"] += 1
            
            logger.info(f"Created {service_name} integration for user {user_id}")
            return integration_id
            
        except Exception as e:
            logger.error(f"Error creating integration: {e}")
            raise
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.encryption_key.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.encryption_key.decrypt(encrypted_data.encode()).decode()
    
    async def get_integration(self, user_id: str, service_name: str, 
                            integration_name: str) -> Optional[BaseIntegration]:
        """Get user's integration for service"""
        integration_key = f"{user_id}:{service_name}:{integration_name}"
        return self.integrations.get(integration_key)
    
    async def list_user_integrations(self, user_id: str) -> List[Dict[str, Any]]:
        """List all integrations for user"""
        try:
            query = """
            SELECT id, service_name, integration_name, status, created_at, last_used_at
            FROM integrations
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            """
            
            rows = await db_manager.database.fetch_all(query, {"user_id": user_id})
            
            integrations = []
            for row in rows:
                service_config = self.service_configs.get(row["service_name"])
                
                integration_info = {
                    "id": row["id"],
                    "service_name": row["service_name"],
                    "service_display_name": service_config.display_name if service_config else row["service_name"],
                    "integration_name": row["integration_name"],
                    "status": row["status"],
                    "created_at": row["created_at"].isoformat(),
                    "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None
                }
                
                integrations.append(integration_info)
            
            return integrations
            
        except Exception as e:
            logger.error(f"Error listing user integrations: {e}")
            return []
    
    async def delete_integration(self, user_id: str, integration_id: str) -> bool:
        """Delete user integration"""
        try:
            # Get integration info
            query = """
            SELECT service_name, integration_name FROM integrations
            WHERE id = :integration_id AND user_id = :user_id
            """
            
            row = await db_manager.database.fetch_one(query, {
                "integration_id": integration_id,
                "user_id": user_id
            })
            
            if not row:
                return False
            
            # Remove from memory
            integration_key = f"{user_id}:{row['service_name']}:{row['integration_name']}"
            if integration_key in self.integrations:
                await self.integrations[integration_key].cleanup()
                del self.integrations[integration_key]
                self.stats["active_integrations"] -= 1
            
            # Update database
            update_query = """
            UPDATE integrations 
            SET status = :status, updated_at = :updated_at
            WHERE id = :integration_id AND user_id = :user_id
            """
            
            await db_manager.database.execute(update_query, {
                "status": IntegrationStatus.INACTIVE.value,
                "updated_at": datetime.utcnow(),
                "integration_id": integration_id,
                "user_id": user_id
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting integration: {e}")
            return False
    
    def get_service_configs(self) -> List[Dict[str, Any]]:
        """Get available service configurations"""
        configs = []
        
        for service_config in self.service_configs.values():
            config_info = {
                "service_name": service_config.service_name,
                "display_name": service_config.display_name,
                "description": service_config.description,
                "auth_type": service_config.auth_type.value,
                "webhook_support": service_config.webhook_support,
                "required_scopes": service_config.required_scopes,
                "rate_limits": service_config.rate_limits
            }
            configs.append(config_info)
        
        return configs
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get integration manager metrics"""
        return {
            "integration_manager": {
                "total_integrations": self.stats["total_integrations"],
                "active_integrations": self.stats["active_integrations"],
                "failed_integrations": self.stats["failed_integrations"],
                "available_services": len(self.service_configs),
                "api_requests_made": self.stats["api_requests_made"],
                "api_errors": self.stats["api_errors"],
                "success_rate": (
                    (self.stats["api_requests_made"] - self.stats["api_errors"]) / 
                    max(1, self.stats["api_requests_made"])
                ) * 100
            }
        }
    
    async def cleanup(self):
        """Clean up integration manager"""
        
        # Cleanup all integrations
        for integration in self.integrations.values():
            await integration.cleanup()
        
        self.integrations.clear()
        logger.info("Integration manager cleaned up")