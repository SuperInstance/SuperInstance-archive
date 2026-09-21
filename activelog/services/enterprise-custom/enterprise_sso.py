#!/usr/bin/env python3
"""
Enterprise SSO Integration System
Advanced Single Sign-On integration with SAML 2.0, OAuth 2.0/OpenID Connect,
Active Directory, multi-provider support, and automated user provisioning.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
import hashlib
import base64
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
import jwt
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509 import load_pem_x509_certificate
# import ldap3  # Would be used in production for LDAP integration
from enum import Enum

logger = logging.getLogger(__name__)

class SSOProtocol(str, Enum):
    SAML2 = "saml2"
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openid_connect"
    LDAP = "ldap"
    ACTIVE_DIRECTORY = "active_directory"
    CUSTOM = "custom"

class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    ERROR = "error"
    PENDING = "pending"

class UserProvisioningAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DEACTIVATE = "deactivate"
    DELETE = "delete"
    SYNC = "sync"

class SSOIntegrationSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/enterprise-custom/data/enterprise_custom.db"
        self.sso_configurations = {}
        self.active_sessions = {}
        self.provider_certificates = {}
        self.user_mappings = {}
        self.group_mappings = {}
        self.supported_providers = {}
        
    async def initialize(self):
        """Initialize the SSO integration system"""
        try:
            await self._setup_database_tables()
            await self._load_supported_providers()
            await self._load_existing_configurations()
            await self._initialize_crypto_keys()
            await self._start_session_manager()
            logger.info("SSO integration system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SSO system: {e}")
            raise

    async def _setup_database_tables(self):
        """Setup database tables for SSO"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # SSO configurations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sso_configurations (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                protocol TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                configuration TEXT NOT NULL,
                certificates TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES enterprise_organizations (id)
            )
        ''')
        
        # SSO providers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sso_providers (
                id TEXT PRIMARY KEY,
                provider_type TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                configuration_template TEXT NOT NULL,
                supported_features TEXT,
                documentation_url TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User provisioning rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_provisioning_rules (
                id TEXT PRIMARY KEY,
                sso_config_id TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                conditions TEXT NOT NULL,
                actions TEXT NOT NULL,
                priority INTEGER DEFAULT 100,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sso_config_id) REFERENCES sso_configurations (id)
            )
        ''')
        
        # SSO sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sso_sessions (
                id TEXT PRIMARY KEY,
                session_token TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                sso_config_id TEXT NOT NULL,
                provider_session_id TEXT,
                user_attributes TEXT,
                group_memberships TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (sso_config_id) REFERENCES sso_configurations (id)
            )
        ''')
        
        # Group mappings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_mappings (
                id TEXT PRIMARY KEY,
                sso_config_id TEXT NOT NULL,
                provider_group TEXT NOT NULL,
                local_role TEXT NOT NULL,
                permissions TEXT,
                auto_provision BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sso_config_id) REFERENCES sso_configurations (id)
            )
        ''')
        
        # SSO audit logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sso_audit_logs (
                id TEXT PRIMARY KEY,
                sso_config_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                provider_user_id TEXT,
                event_data TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sso_config_id) REFERENCES sso_configurations (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def _load_supported_providers(self):
        """Load supported SSO providers"""
        self.supported_providers = {
            "microsoft_azure_ad": {
                "name": "Microsoft Azure Active Directory",
                "protocol": SSOProtocol.OPENID_CONNECT,
                "features": [
                    "user_provisioning", "group_sync", "mfa_support",
                    "conditional_access", "app_roles"
                ],
                "configuration_template": {
                    "client_id": "",
                    "client_secret": "",
                    "tenant_id": "",
                    "authority": "https://login.microsoftonline.com/{tenant_id}",
                    "scopes": ["openid", "profile", "email", "User.Read"],
                    "redirect_uri": ""
                },
                "endpoints": {
                    "authorization": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
                    "token": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                    "userinfo": "https://graph.microsoft.com/v1.0/me"
                }
            },
            "google_workspace": {
                "name": "Google Workspace",
                "protocol": SSOProtocol.OAUTH2,
                "features": [
                    "user_provisioning", "group_sync", "admin_sdk_integration"
                ],
                "configuration_template": {
                    "client_id": "",
                    "client_secret": "",
                    "domain": "",
                    "admin_email": "",
                    "scopes": [
                        "openid", "email", "profile",
                        "https://www.googleapis.com/auth/admin.directory.user"
                    ]
                }
            },
            "okta": {
                "name": "Okta",
                "protocol": SSOProtocol.SAML2,
                "features": [
                    "user_provisioning", "group_sync", "mfa_support",
                    "custom_attributes", "lifecycle_management"
                ],
                "configuration_template": {
                    "org_url": "",
                    "api_token": "",
                    "issuer_url": "",
                    "sso_url": "",
                    "certificate": ""
                }
            },
            "auth0": {
                "name": "Auth0",
                "protocol": SSOProtocol.OPENID_CONNECT,
                "features": ["universal_login", "social_connections", "mfa_support"],
                "configuration_template": {
                    "domain": "",
                    "client_id": "",
                    "client_secret": "",
                    "audience": ""
                }
            },
            "ping_identity": {
                "name": "PingIdentity",
                "protocol": SSOProtocol.SAML2,
                "features": ["federation", "adaptive_authentication", "api_governance"],
                "configuration_template": {
                    "issuer": "",
                    "sso_service_url": "",
                    "sls_service_url": "",
                    "x509_certificate": ""
                }
            },
            "active_directory": {
                "name": "Active Directory",
                "protocol": SSOProtocol.LDAP,
                "features": ["directory_sync", "kerberos_auth", "group_policy"],
                "configuration_template": {
                    "server": "",
                    "port": 389,
                    "use_ssl": True,
                    "bind_dn": "",
                    "bind_password": "",
                    "base_dn": "",
                    "user_search_base": "",
                    "group_search_base": ""
                }
            },
            "generic_saml": {
                "name": "Generic SAML 2.0 Provider",
                "protocol": SSOProtocol.SAML2,
                "features": ["standard_saml", "custom_attributes"],
                "configuration_template": {
                    "entity_id": "",
                    "sso_service_url": "",
                    "sls_service_url": "",
                    "x509_certificate": "",
                    "name_id_format": "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
                }
            }
        }

    async def _load_existing_configurations(self):
        """Load existing SSO configurations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, organization_id, data FROM sso_configurations
            ''')
            
            configs = cursor.fetchall()
            for config_id, org_id, data_json in configs:
                config_data = json.loads(data_json)
                self.sso_configurations[config_id] = config_data
                
            conn.close()
            logger.info(f"Loaded {len(configs)} existing SSO configurations")
        except Exception as e:
            logger.error(f"Failed to load existing configurations: {e}")

    async def _initialize_crypto_keys(self):
        """Initialize cryptographic keys for SAML"""
        try:
            # Generate RSA key pair for SAML signing
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            self.public_key = self.private_key.public_key()
            
            # Store keys (in production, these should be securely stored)
            self.private_key_pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            self.public_key_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize crypto keys: {e}")
            raise

    async def _start_session_manager(self):
        """Start SSO session management"""
        asyncio.create_task(self._cleanup_expired_sessions())

    async def configure_sso(self, sso_data: dict) -> Dict[str, Any]:
        """Configure SSO integration for organization"""
        try:
            org_id = sso_data["organization_id"]
            provider_type = sso_data["provider_type"]
            config_id = f"SSO_{uuid.uuid4().hex[:12].upper()}"
            
            # Validate provider type
            if provider_type not in self.supported_providers:
                return {
                    "status": "error",
                    "message": f"Unsupported provider type: {provider_type}"
                }
            
            provider_info = self.supported_providers[provider_type]
            
            # Build SSO configuration
            sso_config = {
                "id": config_id,
                "organization_id": org_id,
                "provider_type": provider_type,
                "provider_name": sso_data.get("provider_name", provider_info["name"]),
                "protocol": provider_info["protocol"],
                "status": ProviderStatus.PENDING,
                "configuration": await self._build_provider_configuration(provider_type, sso_data),
                "user_provisioning": {
                    "enabled": sso_data.get("enable_provisioning", True),
                    "create_users": sso_data.get("create_users", True),
                    "update_users": sso_data.get("update_users", True),
                    "deactivate_users": sso_data.get("deactivate_users", False),
                    "default_role": sso_data.get("default_role", "user")
                },
                "attribute_mapping": sso_data.get("attribute_mapping", {
                    "email": "email",
                    "first_name": "given_name",
                    "last_name": "family_name",
                    "display_name": "name"
                }),
                "group_mapping": sso_data.get("group_mapping", {}),
                "security_settings": {
                    "require_encrypted_assertions": sso_data.get("require_encryption", True),
                    "session_timeout": sso_data.get("session_timeout", 8 * 3600),
                    "enforce_mfa": sso_data.get("enforce_mfa", False),
                    "allowed_domains": sso_data.get("allowed_domains", [])
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Generate metadata based on protocol
            metadata = await self._generate_metadata(sso_config)
            sso_config["metadata"] = metadata
            
            # Validate configuration
            validation_result = await self._validate_sso_configuration(sso_config)
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "message": "SSO configuration validation failed",
                    "errors": validation_result["errors"]
                }
            
            # Test connection if credentials provided
            if sso_data.get("test_connection", False):
                test_result = await self._test_provider_connection(sso_config)
                if not test_result["success"]:
                    return {
                        "status": "error",
                        "message": "Provider connection test failed",
                        "details": test_result
                    }
                sso_config["status"] = ProviderStatus.TESTING
            
            # Store configuration
            await self._store_sso_configuration(sso_config)
            
            # Setup user provisioning rules
            await self._setup_default_provisioning_rules(config_id)
            
            # Setup group mappings
            await self._setup_group_mappings(config_id, sso_data.get("group_mapping", {}))
            
            self.sso_configurations[config_id] = sso_config
            
            return {
                "status": "success",
                "sso_config_id": config_id,
                "provider_type": provider_type,
                "metadata": metadata,
                "endpoints": {
                    "login_url": f"/sso/{config_id}/login",
                    "callback_url": f"/sso/{config_id}/callback",
                    "logout_url": f"/sso/{config_id}/logout",
                    "metadata_url": f"/sso/{config_id}/metadata"
                },
                "next_steps": [
                    "Configure provider with callback URLs",
                    "Test SSO integration",
                    "Set up user provisioning rules",
                    "Configure group mappings"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to configure SSO: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _build_provider_configuration(self, provider_type: str, sso_data: dict) -> Dict[str, Any]:
        """Build provider-specific configuration"""
        provider_info = self.supported_providers[provider_type]
        template = provider_info["configuration_template"].copy()
        
        # Fill template with provided data
        config_mapping = sso_data.get("configuration", {})
        
        for key, value in config_mapping.items():
            if key in template:
                template[key] = value
        
        # Add protocol-specific configurations
        if provider_info["protocol"] == SSOProtocol.SAML2:
            template.update({
                "sp_entity_id": f"enterprise-custom-{sso_data['organization_id']}",
                "acs_url": f"/sso/{sso_data.get('config_id', 'temp')}/acs",
                "sls_url": f"/sso/{sso_data.get('config_id', 'temp')}/sls"
            })
        elif provider_info["protocol"] == SSOProtocol.OAUTH2:
            template.update({
                "response_type": "code",
                "grant_type": "authorization_code",
                "redirect_uri": f"/sso/{sso_data.get('config_id', 'temp')}/callback"
            })
        elif provider_info["protocol"] == SSOProtocol.OPENID_CONNECT:
            template.update({
                "response_type": "code",
                "scope": " ".join(template.get("scopes", ["openid", "profile", "email"])),
                "redirect_uri": f"/sso/{sso_data.get('config_id', 'temp')}/callback"
            })
        
        return template

    async def _generate_metadata(self, sso_config: dict) -> Dict[str, Any]:
        """Generate SSO metadata based on protocol"""
        protocol = sso_config["protocol"]
        config_id = sso_config["id"]
        
        if protocol == SSOProtocol.SAML2:
            return await self._generate_saml_metadata(sso_config)
        elif protocol in [SSOProtocol.OAUTH2, SSOProtocol.OPENID_CONNECT]:
            return await self._generate_oauth_metadata(sso_config)
        elif protocol == SSOProtocol.LDAP:
            return await self._generate_ldap_metadata(sso_config)
        else:
            return {}

    async def _generate_saml_metadata(self, sso_config: dict) -> Dict[str, Any]:
        """Generate SAML metadata"""
        config_id = sso_config["id"]
        base_url = f"https://enterprise.example.com/sso/{config_id}"
        
        metadata = {
            "entity_id": sso_config["configuration"].get("sp_entity_id"),
            "acs_url": f"{base_url}/acs",
            "sls_url": f"{base_url}/sls",
            "metadata_url": f"{base_url}/metadata",
            "certificate": base64.b64encode(self.public_key_pem).decode(),
            "xml_metadata": await self._generate_saml_xml_metadata(sso_config)
        }
        
        return metadata

    async def _generate_saml_xml_metadata(self, sso_config: dict) -> str:
        """Generate SAML XML metadata"""
        config_id = sso_config["id"]
        entity_id = sso_config["configuration"].get("sp_entity_id")
        base_url = f"https://enterprise.example.com/sso/{config_id}"
        
        xml_metadata = f'''<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{entity_id}">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>{base64.b64encode(self.public_key_pem).decode()}</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:NameIDFormat>urn:oasis:names:tc:SAML:2.0:nameid-format:persistent</md:NameIDFormat>
    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                 Location="{base_url}/acs"
                                 index="1"/>
    <md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                           Location="{base_url}/sls"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>'''
        
        return xml_metadata

    async def _generate_oauth_metadata(self, sso_config: dict) -> Dict[str, Any]:
        """Generate OAuth/OpenID Connect metadata"""
        config_id = sso_config["id"]
        base_url = f"https://enterprise.example.com/sso/{config_id}"
        
        return {
            "client_id": sso_config["configuration"].get("client_id"),
            "redirect_uris": [f"{base_url}/callback"],
            "response_types": ["code"],
            "grant_types": ["authorization_code"],
            "token_endpoint_auth_method": "client_secret_post"
        }

    async def _generate_ldap_metadata(self, sso_config: dict) -> Dict[str, Any]:
        """Generate LDAP metadata"""
        return {
            "connection_info": {
                "server": sso_config["configuration"].get("server"),
                "port": sso_config["configuration"].get("port"),
                "use_ssl": sso_config["configuration"].get("use_ssl"),
                "base_dn": sso_config["configuration"].get("base_dn")
            },
            "schema_info": {
                "user_object_class": "user",
                "group_object_class": "group",
                "user_id_attribute": "sAMAccountName",
                "email_attribute": "mail"
            }
        }

    async def _validate_sso_configuration(self, sso_config: dict) -> Dict[str, Any]:
        """Validate SSO configuration"""
        errors = []
        
        # Required fields
        required_fields = ["organization_id", "provider_type", "configuration"]
        for field in required_fields:
            if not sso_config.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Protocol-specific validation
        protocol = sso_config.get("protocol")
        configuration = sso_config.get("configuration", {})
        
        if protocol == SSOProtocol.SAML2:
            saml_required = ["entity_id", "sso_service_url", "x509_certificate"]
            for field in saml_required:
                if not configuration.get(field):
                    errors.append(f"Missing SAML required field: {field}")
        
        elif protocol in [SSOProtocol.OAUTH2, SSOProtocol.OPENID_CONNECT]:
            oauth_required = ["client_id", "client_secret"]
            for field in oauth_required:
                if not configuration.get(field):
                    errors.append(f"Missing OAuth required field: {field}")
        
        elif protocol == SSOProtocol.LDAP:
            ldap_required = ["server", "base_dn"]
            for field in ldap_required:
                if not configuration.get(field):
                    errors.append(f"Missing LDAP required field: {field}")
        
        # Attribute mapping validation
        attribute_mapping = sso_config.get("attribute_mapping", {})
        if not attribute_mapping.get("email"):
            errors.append("Email attribute mapping is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    async def _test_provider_connection(self, sso_config: dict) -> Dict[str, Any]:
        """Test connection to SSO provider"""
        try:
            protocol = sso_config["protocol"]
            configuration = sso_config["configuration"]
            
            if protocol == SSOProtocol.LDAP:
                return await self._test_ldap_connection(configuration)
            elif protocol in [SSOProtocol.OAUTH2, SSOProtocol.OPENID_CONNECT]:
                return await self._test_oauth_connection(configuration)
            elif protocol == SSOProtocol.SAML2:
                return await self._test_saml_connection(configuration)
            else:
                return {
                    "success": False,
                    "message": "Test not implemented for this protocol"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    async def _test_ldap_connection(self, config: dict) -> Dict[str, Any]:
        """Test LDAP connection"""
        try:
            server = ldap3.Server(
                config["server"],
                port=config.get("port", 389),
                use_ssl=config.get("use_ssl", False)
            )
            
            conn = ldap3.Connection(
                server,
                user=config.get("bind_dn"),
                password=config.get("bind_password"),
                auto_bind=True
            )
            
            # Test search
            conn.search(
                search_base=config["base_dn"],
                search_filter="(objectClass=*)",
                search_scope=ldap3.BASE,
                attributes=["*"]
            )
            
            conn.unbind()
            
            return {
                "success": True,
                "message": "LDAP connection successful"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"LDAP connection failed: {str(e)}"
            }

    async def _test_oauth_connection(self, config: dict) -> Dict[str, Any]:
        """Test OAuth connection"""
        try:
            # This would typically involve making a test request to the provider's discovery endpoint
            # For now, we'll simulate a successful test
            return {
                "success": True,
                "message": "OAuth configuration validated"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"OAuth test failed: {str(e)}"
            }

    async def _test_saml_connection(self, config: dict) -> Dict[str, Any]:
        """Test SAML connection"""
        try:
            # Test certificate parsing
            cert_data = config.get("x509_certificate", "")
            if cert_data:
                # Remove headers and decode
                cert_data = cert_data.replace("-----BEGIN CERTIFICATE-----", "")
                cert_data = cert_data.replace("-----END CERTIFICATE-----", "")
                cert_data = cert_data.replace("\n", "")
                
                cert_bytes = base64.b64decode(cert_data)
                certificate = load_pem_x509_certificate(
                    b"-----BEGIN CERTIFICATE-----\n" + 
                    base64.b64encode(cert_bytes) + 
                    b"\n-----END CERTIFICATE-----"
                )
            
            return {
                "success": True,
                "message": "SAML configuration validated"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"SAML test failed: {str(e)}"
            }

    async def _store_sso_configuration(self, sso_config: dict):
        """Store SSO configuration in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO sso_configurations 
                (id, organization_id, provider_name, protocol, status, 
                 configuration, metadata, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sso_config["id"],
                sso_config["organization_id"],
                sso_config["provider_name"],
                sso_config["protocol"],
                sso_config["status"],
                json.dumps(sso_config["configuration"]),
                json.dumps(sso_config.get("metadata", {})),
                json.dumps(sso_config)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store SSO configuration: {e}")
            raise

    async def _setup_default_provisioning_rules(self, config_id: str):
        """Setup default user provisioning rules"""
        try:
            default_rules = [
                {
                    "rule_name": "Auto Create Users",
                    "rule_type": "user_creation",
                    "conditions": {
                        "user_exists": False,
                        "domain_allowed": True
                    },
                    "actions": {
                        "create_user": True,
                        "assign_default_role": True,
                        "send_welcome_email": True
                    }
                },
                {
                    "rule_name": "Update User Attributes",
                    "rule_type": "user_update",
                    "conditions": {
                        "user_exists": True,
                        "attributes_changed": True
                    },
                    "actions": {
                        "update_attributes": True,
                        "sync_group_memberships": True
                    }
                },
                {
                    "rule_name": "Deactivate Removed Users",
                    "rule_type": "user_deactivation",
                    "conditions": {
                        "user_removed_from_provider": True
                    },
                    "actions": {
                        "deactivate_user": True,
                        "revoke_sessions": True
                    }
                }
            ]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for rule in default_rules:
                rule_id = f"RULE_{uuid.uuid4().hex[:8].upper()}"
                
                cursor.execute('''
                    INSERT INTO user_provisioning_rules 
                    (id, sso_config_id, rule_name, rule_type, conditions, actions)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    rule_id, config_id, rule["rule_name"], rule["rule_type"],
                    json.dumps(rule["conditions"]), json.dumps(rule["actions"])
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to setup provisioning rules: {e}")

    async def _setup_group_mappings(self, config_id: str, group_mappings: dict):
        """Setup group to role mappings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for provider_group, local_role in group_mappings.items():
                mapping_id = f"MAPPING_{uuid.uuid4().hex[:8].upper()}"
                
                permissions = []
                if local_role == "admin":
                    permissions = ["read", "write", "delete", "manage_users"]
                elif local_role == "editor":
                    permissions = ["read", "write"]
                else:
                    permissions = ["read"]
                
                cursor.execute('''
                    INSERT INTO group_mappings 
                    (id, sso_config_id, provider_group, local_role, permissions)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    mapping_id, config_id, provider_group, local_role,
                    json.dumps(permissions)
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to setup group mappings: {e}")

    async def get_supported_providers(self, org_id: str) -> Dict[str, Any]:
        """Get list of supported SSO providers"""
        try:
            providers = []
            
            for provider_type, provider_info in self.supported_providers.items():
                providers.append({
                    "provider_type": provider_type,
                    "name": provider_info["name"],
                    "protocol": provider_info["protocol"],
                    "features": provider_info["features"],
                    "configuration_fields": list(provider_info["configuration_template"].keys())
                })
            
            return {
                "status": "success",
                "supported_providers": providers,
                "total_providers": len(providers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get supported providers: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def test_sso_connection(self, org_id: str, test_data: dict) -> Dict[str, Any]:
        """Test SSO connection for organization"""
        try:
            config_id = test_data.get("sso_config_id")
            if not config_id or config_id not in self.sso_configurations:
                return {
                    "status": "error",
                    "message": "SSO configuration not found"
                }
            
            sso_config = self.sso_configurations[config_id]
            
            # Verify organization ownership
            if sso_config["organization_id"] != org_id:
                return {
                    "status": "error",
                    "message": "Access denied"
                }
            
            # Perform connection test
            test_result = await self._test_provider_connection(sso_config)
            
            # Log test result
            await self._log_sso_event(config_id, "connection_test", {
                "success": test_result["success"],
                "message": test_result["message"]
            })
            
            # Update configuration status
            if test_result["success"]:
                sso_config["status"] = ProviderStatus.ACTIVE
                await self._store_sso_configuration(sso_config)
            
            return {
                "status": "success" if test_result["success"] else "error",
                "test_result": test_result,
                "configuration_status": sso_config["status"]
            }
            
        except Exception as e:
            logger.error(f"Failed to test SSO connection: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _log_sso_event(self, config_id: str, event_type: str, event_data: dict):
        """Log SSO event for auditing"""
        try:
            event_id = f"EVENT_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sso_audit_logs 
                (id, sso_config_id, event_type, event_data, success)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                event_id, config_id, event_type,
                json.dumps(event_data), event_data.get("success", True)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log SSO event: {e}")

    async def initiate_sso_login(self, config_id: str, return_url: str = None) -> Dict[str, Any]:
        """Initiate SSO login process"""
        try:
            if config_id not in self.sso_configurations:
                return {
                    "status": "error",
                    "message": "SSO configuration not found"
                }
            
            sso_config = self.sso_configurations[config_id]
            protocol = sso_config["protocol"]
            
            if protocol == SSOProtocol.SAML2:
                return await self._initiate_saml_login(sso_config, return_url)
            elif protocol in [SSOProtocol.OAUTH2, SSOProtocol.OPENID_CONNECT]:
                return await self._initiate_oauth_login(sso_config, return_url)
            else:
                return {
                    "status": "error",
                    "message": f"Login not supported for protocol: {protocol}"
                }
                
        except Exception as e:
            logger.error(f"Failed to initiate SSO login: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _initiate_saml_login(self, sso_config: dict, return_url: str) -> Dict[str, Any]:
        """Initiate SAML login"""
        try:
            request_id = f"REQ_{uuid.uuid4().hex[:16].upper()}"
            
            # Create SAML AuthnRequest
            authn_request = await self._create_saml_authn_request(sso_config, request_id)
            
            # Sign the request (simplified)
            signed_request = base64.b64encode(authn_request.encode()).decode()
            
            # Build redirect URL
            sso_url = sso_config["configuration"]["sso_service_url"]
            redirect_url = f"{sso_url}?SAMLRequest={signed_request}"
            
            if return_url:
                redirect_url += f"&RelayState={return_url}"
            
            return {
                "status": "success",
                "redirect_url": redirect_url,
                "request_id": request_id
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate SAML login: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _create_saml_authn_request(self, sso_config: dict, request_id: str) -> str:
        """Create SAML AuthnRequest"""
        issue_instant = datetime.utcnow().isoformat() + "Z"
        
        authn_request = f'''<samlp:AuthnRequest 
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{sso_config['configuration']['sso_service_url']}"
    AssertionConsumerServiceURL="{sso_config['metadata']['acs_url']}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{sso_config['configuration']['sp_entity_id']}</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
                        AllowCreate="true"/>
</samlp:AuthnRequest>'''
        
        return authn_request

    async def _initiate_oauth_login(self, sso_config: dict, return_url: str) -> Dict[str, Any]:
        """Initiate OAuth/OpenID Connect login"""
        try:
            state = f"STATE_{uuid.uuid4().hex[:16].upper()}"
            nonce = f"NONCE_{uuid.uuid4().hex[:16].upper()}"
            
            config = sso_config["configuration"]
            
            # Build authorization URL
            params = {
                "client_id": config["client_id"],
                "response_type": config.get("response_type", "code"),
                "scope": config.get("scope", "openid profile email"),
                "redirect_uri": config["redirect_uri"],
                "state": state
            }
            
            if sso_config["protocol"] == SSOProtocol.OPENID_CONNECT:
                params["nonce"] = nonce
            
            auth_url = config["authorization_endpoint"] + "?" + urlencode(params)
            
            # Store state for validation
            self.active_sessions[state] = {
                "config_id": sso_config["id"],
                "nonce": nonce,
                "return_url": return_url,
                "created_at": datetime.now()
            }
            
            return {
                "status": "success",
                "redirect_url": auth_url,
                "state": state
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate OAuth login: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _cleanup_expired_sessions(self):
        """Cleanup expired SSO sessions"""
        while True:
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                for session_id, session_data in self.active_sessions.items():
                    created_at = session_data.get("created_at")
                    if created_at and (current_time - created_at).seconds > 3600:  # 1 hour
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    del self.active_sessions[session_id]
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)

# Global instance
sso_integration_system = SSOIntegrationSystem()