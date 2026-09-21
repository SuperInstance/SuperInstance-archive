#!/usr/bin/env python3
"""
Enterprise App Store System
Curated application catalog with custom deployment, license management,
security scanning, and enterprise-specific configurations.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import tarfile
import zipfile
import tempfile
import os
import subprocess
import yaml
# import semver  # Would be used in production for semantic versioning

logger = logging.getLogger(__name__)

class AppStatus(str, Enum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    UPDATING = "updating"
    DEPRECATED = "deprecated"
    SECURITY_REVIEW = "security_review"
    REJECTED = "rejected"

class AppCategory(str, Enum):
    PRODUCTIVITY = "productivity"
    ANALYTICS = "analytics"
    SECURITY = "security"
    INTEGRATION = "integration"
    COMMUNICATION = "communication"
    DEVELOPMENT = "development"
    FINANCE = "finance"
    CUSTOM = "custom"

class LicenseType(str, Enum):
    FREE = "free"
    PAID = "paid"
    SUBSCRIPTION = "subscription"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class EnterpriseAppStoreSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/enterprise-custom/data/enterprise_custom.db"
        self.app_catalog = {}
        self.installed_apps = {}
        self.licenses = {}
        self.security_scanner = None
        self.app_storage_path = "/home/activeloguser/activelog/services/enterprise-custom/data/app_store"
        
    async def initialize(self):
        """Initialize the enterprise app store system"""
        try:
            await self._setup_database_tables()
            await self._setup_storage_directories()
            await self._load_app_catalog()
            await self._load_installed_apps()
            await self._initialize_security_scanner()
            await self._start_update_checker()
            logger.info("Enterprise app store system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize app store system: {e}")
            raise

    async def _setup_database_tables(self):
        """Setup database tables for app store"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # App catalog table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_catalog (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                version TEXT NOT NULL,
                description TEXT,
                publisher TEXT NOT NULL,
                license_type TEXT DEFAULT 'free',
                status TEXT DEFAULT 'available',
                security_scan_results TEXT,
                configuration_schema TEXT,
                installation_requirements TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Installed applications table (from main.py, extending it)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enterprise_application_configs (
                id TEXT PRIMARY KEY,
                app_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                custom_config TEXT,
                environment_variables TEXT,
                resource_limits TEXT,
                scaling_policy TEXT,
                monitoring_config TEXT,
                backup_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES app_catalog (id),
                FOREIGN KEY (organization_id) REFERENCES enterprise_organizations (id)
            )
        ''')
        
        # App licenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_licenses (
                id TEXT PRIMARY KEY,
                app_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                license_key TEXT,
                license_type TEXT NOT NULL,
                expires_at TIMESTAMP,
                max_users INTEGER,
                features TEXT,
                purchase_order TEXT,
                cost DECIMAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES app_catalog (id),
                FOREIGN KEY (organization_id) REFERENCES enterprise_organizations (id)
            )
        ''')
        
        # Security scan results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_security_scans (
                id TEXT PRIMARY KEY,
                app_id TEXT NOT NULL,
                app_version TEXT NOT NULL,
                scan_type TEXT NOT NULL,
                scan_results TEXT NOT NULL,
                vulnerabilities_found INTEGER DEFAULT 0,
                security_score INTEGER DEFAULT 0,
                scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scanner_version TEXT,
                FOREIGN KEY (app_id) REFERENCES app_catalog (id)
            )
        ''')
        
        # App reviews and ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_reviews (
                id TEXT PRIMARY KEY,
                app_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                review_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES app_catalog (id),
                FOREIGN KEY (organization_id) REFERENCES enterprise_organizations (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def _setup_storage_directories(self):
        """Setup storage directories for app store"""
        directories = [
            self.app_storage_path,
            f"{self.app_storage_path}/packages",
            f"{self.app_storage_path}/configs",
            f"{self.app_storage_path}/backups",
            f"{self.app_storage_path}/temp"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    async def _load_app_catalog(self):
        """Load application catalog"""
        # Load curated enterprise applications
        self.app_catalog = {
            "grafana": {
                "id": "grafana",
                "name": "Grafana",
                "category": AppCategory.ANALYTICS,
                "version": "10.2.0",
                "description": "Open source analytics and monitoring solution",
                "publisher": "Grafana Labs",
                "license_type": LicenseType.FREE,
                "status": AppStatus.AVAILABLE,
                "docker_image": "grafana/grafana:10.2.0",
                "ports": [3000],
                "environment_variables": [
                    "GF_SECURITY_ADMIN_PASSWORD",
                    "GF_USERS_ALLOW_SIGN_UP"
                ],
                "configuration_schema": {
                    "admin_password": {"type": "password", "required": True},
                    "allow_signup": {"type": "boolean", "default": False},
                    "smtp_host": {"type": "string", "required": False}
                },
                "security_score": 85,
                "enterprise_features": [
                    "SSO integration", "LDAP authentication", 
                    "Advanced permissions", "Audit logging"
                ]
            },
            "prometheus": {
                "id": "prometheus",
                "name": "Prometheus",
                "category": AppCategory.ANALYTICS,
                "version": "2.47.0",
                "description": "Systems monitoring and alerting toolkit",
                "publisher": "Prometheus",
                "license_type": LicenseType.FREE,
                "status": AppStatus.AVAILABLE,
                "docker_image": "prom/prometheus:v2.47.0",
                "ports": [9090],
                "configuration_schema": {
                    "retention_time": {"type": "string", "default": "15d"},
                    "scrape_interval": {"type": "string", "default": "15s"},
                    "external_url": {"type": "string", "required": False}
                },
                "security_score": 90
            },
            "elastic_stack": {
                "id": "elastic_stack",
                "name": "Elastic Stack (ELK)",
                "category": AppCategory.ANALYTICS,
                "version": "8.11.0",
                "description": "Search and analytics engine with Kibana and Logstash",
                "publisher": "Elastic",
                "license_type": LicenseType.FREE,
                "status": AppStatus.AVAILABLE,
                "components": ["elasticsearch", "kibana", "logstash"],
                "docker_compose": True,
                "configuration_schema": {
                    "cluster_name": {"type": "string", "default": "enterprise-cluster"},
                    "heap_size": {"type": "string", "default": "1g"},
                    "security_enabled": {"type": "boolean", "default": True}
                },
                "security_score": 88
            },
            "vault": {
                "id": "vault",
                "name": "HashiCorp Vault",
                "category": AppCategory.SECURITY,
                "version": "1.15.2",
                "description": "Secrets management and data protection",
                "publisher": "HashiCorp",
                "license_type": LicenseType.ENTERPRISE,
                "status": AppStatus.AVAILABLE,
                "docker_image": "vault:1.15.2",
                "ports": [8200],
                "configuration_schema": {
                    "storage_backend": {"type": "select", "options": ["file", "consul", "s3"], "default": "file"},
                    "seal_type": {"type": "select", "options": ["shamir", "auto"], "default": "shamir"},
                    "ui_enabled": {"type": "boolean", "default": True}
                },
                "security_score": 95,
                "enterprise_features": ["HSM support", "Multi-datacenter replication", "Disaster recovery"]
            },
            "jenkins": {
                "id": "jenkins",
                "name": "Jenkins",
                "category": AppCategory.DEVELOPMENT,
                "version": "2.426.1",
                "description": "Automation server for CI/CD pipelines",
                "publisher": "Jenkins",
                "license_type": LicenseType.FREE,
                "status": AppStatus.AVAILABLE,
                "docker_image": "jenkins/jenkins:2.426.1-lts",
                "ports": [8080, 50000],
                "configuration_schema": {
                    "admin_user": {"type": "string", "required": True},
                    "admin_password": {"type": "password", "required": True},
                    "jenkins_opts": {"type": "string", "required": False}
                },
                "security_score": 75
            },
            "sonarqube": {
                "id": "sonarqube",
                "name": "SonarQube",
                "category": AppCategory.DEVELOPMENT,
                "version": "10.3.0",
                "description": "Continuous code quality and security analysis",
                "publisher": "SonarSource",
                "license_type": LicenseType.PAID,
                "status": AppStatus.AVAILABLE,
                "docker_image": "sonarqube:10.3.0-community",
                "ports": [9000],
                "configuration_schema": {
                    "database_url": {"type": "string", "required": True},
                    "database_user": {"type": "string", "required": True},
                    "database_password": {"type": "password", "required": True}
                },
                "security_score": 92
            },
            "rocket_chat": {
                "id": "rocket_chat",
                "name": "Rocket.Chat",
                "category": AppCategory.COMMUNICATION,
                "version": "6.4.0",
                "description": "Team communication and collaboration platform",
                "publisher": "Rocket.Chat",
                "license_type": LicenseType.FREE,
                "status": AppStatus.AVAILABLE,
                "docker_image": "rocket.chat:6.4.0",
                "ports": [3000],
                "dependencies": ["mongodb"],
                "configuration_schema": {
                    "site_name": {"type": "string", "required": True},
                    "site_url": {"type": "string", "required": True},
                    "mongo_url": {"type": "string", "required": True}
                },
                "security_score": 80
            }
        }

        # Store catalog in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for app_id, app_data in self.app_catalog.items():
            cursor.execute('''
                INSERT OR REPLACE INTO app_catalog 
                (id, name, category, version, description, publisher, 
                 license_type, status, security_scan_results, 
                 configuration_schema, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                app_id, app_data["name"], app_data["category"], 
                app_data["version"], app_data["description"], 
                app_data["publisher"], app_data["license_type"], 
                app_data["status"], json.dumps({"score": app_data.get("security_score", 0)}),
                json.dumps(app_data.get("configuration_schema", {})),
                json.dumps(app_data)
            ))
        
        conn.commit()
        conn.close()

    async def _load_installed_apps(self):
        """Load installed applications from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, organization_id, data FROM enterprise_applications
            ''')
            
            apps = cursor.fetchall()
            for app_id, org_id, data_json in apps:
                app_data = json.loads(data_json)
                if org_id not in self.installed_apps:
                    self.installed_apps[org_id] = {}
                self.installed_apps[org_id][app_id] = app_data
                
            conn.close()
            logger.info(f"Loaded {len(apps)} installed applications")
        except Exception as e:
            logger.error(f"Failed to load installed apps: {e}")

    async def _initialize_security_scanner(self):
        """Initialize security scanning capabilities"""
        self.security_scanner = {
            "vulnerability_scanners": ["trivy", "clair", "snyk"],
            "compliance_checks": ["cis", "nist", "gdpr"],
            "code_analysis": ["sonarqube", "checkmarx"],
            "dependency_scanning": ["owasp", "retire.js"]
        }

    async def _start_update_checker(self):
        """Start background task to check for app updates"""
        asyncio.create_task(self._update_checker_loop())

    async def get_catalog(self, org_id: str, category: str = None) -> Dict[str, Any]:
        """Get application catalog for organization"""
        try:
            # Filter catalog based on organization requirements
            filtered_catalog = {}
            
            for app_id, app_data in self.app_catalog.items():
                # Apply category filter
                if category and app_data.get("category") != category:
                    continue
                
                # Check if app is already installed
                is_installed = (org_id in self.installed_apps and 
                               app_id in self.installed_apps[org_id])
                
                # Get license information
                license_info = await self._get_license_info(app_id, org_id)
                
                # Get security scan results
                security_info = await self._get_security_scan_results(app_id)
                
                # Get reviews and ratings
                reviews_info = await self._get_app_reviews(app_id)
                
                catalog_entry = {
                    **app_data,
                    "is_installed": is_installed,
                    "license_info": license_info,
                    "security_info": security_info,
                    "reviews": reviews_info,
                    "installation_size": self._estimate_installation_size(app_data),
                    "installation_time": self._estimate_installation_time(app_data)
                }
                
                filtered_catalog[app_id] = catalog_entry
            
            # Get categories for filtering
            categories = list(set(app["category"] for app in filtered_catalog.values()))
            
            return {
                "status": "success",
                "catalog": filtered_catalog,
                "categories": categories,
                "total_apps": len(filtered_catalog),
                "installed_count": sum(1 for app in filtered_catalog.values() if app["is_installed"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get catalog: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _get_license_info(self, app_id: str, org_id: str) -> Dict[str, Any]:
        """Get license information for app and organization"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT license_type, expires_at, max_users, features 
                FROM app_licenses 
                WHERE app_id = ? AND organization_id = ?
            ''', (app_id, org_id))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "has_license": True,
                    "license_type": result[0],
                    "expires_at": result[1],
                    "max_users": result[2],
                    "features": json.loads(result[3] or "[]")
                }
            else:
                app_data = self.app_catalog.get(app_id, {})
                return {
                    "has_license": False,
                    "required_license_type": app_data.get("license_type", "free"),
                    "estimated_cost": self._estimate_license_cost(app_data)
                }
                
        except Exception as e:
            logger.error(f"Failed to get license info: {e}")
            return {"has_license": False}

    async def _get_security_scan_results(self, app_id: str) -> Dict[str, Any]:
        """Get security scan results for app"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT scan_type, vulnerabilities_found, security_score, scan_date
                FROM app_security_scans 
                WHERE app_id = ? 
                ORDER BY scan_date DESC
                LIMIT 5
            ''', (app_id,))
            
            scans = cursor.fetchall()
            conn.close()
            
            if scans:
                latest_scan = scans[0]
                return {
                    "last_scan_date": latest_scan[3],
                    "security_score": latest_scan[2],
                    "vulnerabilities_found": latest_scan[1],
                    "scan_history": [
                        {
                            "scan_type": scan[0],
                            "vulnerabilities": scan[1],
                            "score": scan[2],
                            "date": scan[3]
                        }
                        for scan in scans
                    ]
                }
            else:
                # Return default security score from catalog
                app_data = self.app_catalog.get(app_id, {})
                return {
                    "security_score": app_data.get("security_score", 0),
                    "scan_required": True
                }
                
        except Exception as e:
            logger.error(f"Failed to get security scan results: {e}")
            return {"security_score": 0, "scan_required": True}

    async def _get_app_reviews(self, app_id: str) -> Dict[str, Any]:
        """Get reviews and ratings for app"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get average rating
            cursor.execute('''
                SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                FROM app_reviews 
                WHERE app_id = ?
            ''', (app_id,))
            
            rating_info = cursor.fetchone()
            
            # Get recent reviews
            cursor.execute('''
                SELECT rating, review_text, created_at
                FROM app_reviews 
                WHERE app_id = ? AND review_text IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5
            ''', (app_id,))
            
            recent_reviews = cursor.fetchall()
            conn.close()
            
            return {
                "average_rating": round(rating_info[0] or 0, 1),
                "total_reviews": rating_info[1] or 0,
                "recent_reviews": [
                    {
                        "rating": review[0],
                        "text": review[1],
                        "date": review[2]
                    }
                    for review in recent_reviews
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get app reviews: {e}")
            return {"average_rating": 0, "total_reviews": 0}

    def _estimate_installation_size(self, app_data: dict) -> str:
        """Estimate installation size for app"""
        # Simple estimation based on app type
        if app_data.get("docker_compose"):
            return "500MB - 2GB"
        elif "elastic" in app_data.get("name", "").lower():
            return "1GB - 5GB"
        elif app_data.get("category") == AppCategory.ANALYTICS:
            return "200MB - 1GB"
        else:
            return "100MB - 500MB"

    def _estimate_installation_time(self, app_data: dict) -> str:
        """Estimate installation time for app"""
        if app_data.get("docker_compose"):
            return "5-15 minutes"
        elif len(app_data.get("dependencies", [])) > 0:
            return "3-10 minutes"
        else:
            return "2-5 minutes"

    def _estimate_license_cost(self, app_data: dict) -> Optional[float]:
        """Estimate license cost for app"""
        license_type = app_data.get("license_type")
        
        if license_type == LicenseType.FREE:
            return 0.0
        elif license_type == LicenseType.PAID:
            return 99.0  # Monthly
        elif license_type == LicenseType.SUBSCRIPTION:
            return 49.0  # Per user per month
        elif license_type == LicenseType.ENTERPRISE:
            return 500.0  # Monthly
        else:
            return None

    async def install_application(self, installation_data: dict) -> Dict[str, Any]:
        """Install enterprise application"""
        try:
            app_id = installation_data["app_id"]
            org_id = installation_data["organization_id"]
            
            if app_id not in self.app_catalog:
                return {
                    "status": "error",
                    "message": "Application not found in catalog"
                }
            
            app_data = self.app_catalog[app_id]
            
            # Check if already installed
            if (org_id in self.installed_apps and 
                app_id in self.installed_apps[org_id]):
                return {
                    "status": "error",
                    "message": "Application already installed"
                }
            
            # Check license requirements
            license_check = await self._check_license_requirements(app_id, org_id)
            if not license_check["valid"]:
                return {
                    "status": "error",
                    "message": "License requirements not met",
                    "details": license_check
                }
            
            # Perform security scan if required
            if installation_data.get("require_security_scan", True):
                scan_result = await self._perform_security_scan(app_id)
                if scan_result["security_score"] < 70:
                    return {
                        "status": "error",
                        "message": "Application failed security requirements",
                        "security_scan": scan_result
                    }
            
            # Generate installation ID
            installation_id = f"INSTALL_{uuid.uuid4().hex[:12].upper()}"
            
            # Prepare installation configuration
            install_config = {
                "id": installation_id,
                "app_id": app_id,
                "organization_id": org_id,
                "app_name": app_data["name"],
                "app_type": app_data.get("category"),
                "version": app_data["version"],
                "installation_status": "installing",
                "configuration": installation_data.get("configuration", {}),
                "custom_config": installation_data.get("custom_config", {}),
                "environment_variables": installation_data.get("environment_variables", {}),
                "resource_limits": installation_data.get("resource_limits", {}),
                "networking": installation_data.get("networking", {}),
                "installed_at": datetime.now().isoformat(),
                "installed_by": installation_data.get("installed_by", "system")
            }
            
            # Perform installation
            installation_result = await self._perform_installation(install_config)
            
            if installation_result["success"]:
                # Store installation record
                await self._store_installation_record(install_config, installation_result)
                
                # Update local cache
                if org_id not in self.installed_apps:
                    self.installed_apps[org_id] = {}
                self.installed_apps[org_id][app_id] = install_config
                
                # Setup monitoring
                await self._setup_app_monitoring(installation_id, install_config)
                
                return {
                    "status": "success",
                    "installation_id": installation_id,
                    "app_name": app_data["name"],
                    "installation_details": installation_result,
                    "access_urls": installation_result.get("access_urls", {}),
                    "next_steps": [
                        "Configure application settings",
                        "Set up user access",
                        "Test application functionality",
                        "Configure monitoring and alerts"
                    ]
                }
            else:
                return {
                    "status": "error",
                    "message": "Installation failed",
                    "details": installation_result
                }
                
        except Exception as e:
            logger.error(f"Failed to install application: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _check_license_requirements(self, app_id: str, org_id: str) -> Dict[str, Any]:
        """Check if license requirements are met"""
        try:
            app_data = self.app_catalog[app_id]
            license_type = app_data.get("license_type")
            
            if license_type == LicenseType.FREE:
                return {"valid": True}
            
            # Check if organization has valid license
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT license_key, expires_at, max_users
                FROM app_licenses 
                WHERE app_id = ? AND organization_id = ?
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            ''', (app_id, org_id))
            
            license_record = cursor.fetchone()
            conn.close()
            
            if license_record:
                return {
                    "valid": True,
                    "license_key": license_record[0],
                    "expires_at": license_record[1],
                    "max_users": license_record[2]
                }
            else:
                return {
                    "valid": False,
                    "message": f"Valid {license_type} license required",
                    "required_license_type": license_type
                }
                
        except Exception as e:
            logger.error(f"Failed to check license requirements: {e}")
            return {"valid": False, "message": str(e)}

    async def _perform_security_scan(self, app_id: str) -> Dict[str, Any]:
        """Perform security scan on application"""
        try:
            app_data = self.app_catalog[app_id]
            
            # Simulate security scanning process
            await asyncio.sleep(2)  # Simulate scan time
            
            # Generate scan results
            vulnerabilities = []
            security_score = app_data.get("security_score", 85)
            
            # Add some simulated findings for demonstration
            if security_score < 90:
                vulnerabilities.append({
                    "severity": "medium",
                    "description": "Outdated dependency detected",
                    "recommendation": "Update to latest version"
                })
            
            if security_score < 80:
                vulnerabilities.append({
                    "severity": "high",
                    "description": "Insecure default configuration",
                    "recommendation": "Review security settings"
                })
            
            scan_results = {
                "scan_id": f"SCAN_{uuid.uuid4().hex[:8].upper()}",
                "security_score": security_score,
                "vulnerabilities_found": len(vulnerabilities),
                "vulnerabilities": vulnerabilities,
                "compliance_checks": {
                    "cis_benchmark": security_score >= 85,
                    "owasp_top_10": security_score >= 80,
                    "gdpr_compliant": security_score >= 90
                },
                "scan_date": datetime.now().isoformat()
            }
            
            # Store scan results
            await self._store_security_scan_results(app_id, scan_results)
            
            return scan_results
            
        except Exception as e:
            logger.error(f"Failed to perform security scan: {e}")
            return {
                "security_score": 0,
                "vulnerabilities_found": 999,
                "error": str(e)
            }

    async def _store_security_scan_results(self, app_id: str, scan_results: dict):
        """Store security scan results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO app_security_scans
                (id, app_id, app_version, scan_type, scan_results, 
                 vulnerabilities_found, security_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan_results["scan_id"], app_id, 
                self.app_catalog[app_id].get("version", "unknown"),
                "comprehensive", json.dumps(scan_results),
                scan_results["vulnerabilities_found"],
                scan_results["security_score"]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store security scan results: {e}")

    async def _perform_installation(self, install_config: dict) -> Dict[str, Any]:
        """Perform actual application installation"""
        try:
            app_id = install_config["app_id"]
            app_data = self.app_catalog[app_id]
            
            # Simulate installation process
            installation_steps = [
                "Downloading application package",
                "Validating package integrity",
                "Setting up environment",
                "Installing dependencies",
                "Configuring application",
                "Starting services",
                "Running health checks"
            ]
            
            for step in installation_steps:
                logger.info(f"Installation {install_config['id']}: {step}")
                await asyncio.sleep(0.5)  # Simulate processing time
            
            # Generate installation result
            installation_result = {
                "success": True,
                "installation_id": install_config["id"],
                "deployment_type": "containerized",
                "container_id": f"container_{uuid.uuid4().hex[:8]}",
                "access_urls": {
                    "primary": f"https://{app_id}-{install_config['organization_id']}.enterprise.local",
                    "admin": f"https://{app_id}-{install_config['organization_id']}.enterprise.local/admin"
                },
                "service_ports": app_data.get("ports", []),
                "resource_usage": {
                    "cpu": "500m",
                    "memory": "1Gi",
                    "storage": "5Gi"
                },
                "health_status": "healthy",
                "installation_log": installation_steps,
                "configuration_applied": install_config.get("configuration", {}),
                "environment_variables_set": len(install_config.get("environment_variables", {}))
            }
            
            return installation_result
            
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _store_installation_record(self, install_config: dict, installation_result: dict):
        """Store installation record in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store in enterprise_applications table
            cursor.execute('''
                INSERT INTO enterprise_applications
                (id, organization_id, app_name, app_type, version,
                 installation_status, configuration, permissions, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                install_config["id"],
                install_config["organization_id"],
                install_config["app_name"],
                install_config["app_type"],
                install_config["version"],
                "installed",
                json.dumps(install_config.get("configuration", {})),
                json.dumps(install_config.get("permissions", {})),
                json.dumps({**install_config, "installation_result": installation_result})
            ))
            
            # Store custom configuration
            cursor.execute('''
                INSERT INTO enterprise_application_configs
                (id, app_id, organization_id, custom_config, 
                 environment_variables, resource_limits)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                f"CONFIG_{install_config['id']}",
                install_config["app_id"],
                install_config["organization_id"],
                json.dumps(install_config.get("custom_config", {})),
                json.dumps(install_config.get("environment_variables", {})),
                json.dumps(install_config.get("resource_limits", {}))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store installation record: {e}")
            raise

    async def _setup_app_monitoring(self, installation_id: str, install_config: dict):
        """Setup monitoring for installed application"""
        try:
            monitoring_config = {
                "installation_id": installation_id,
                "app_id": install_config["app_id"],
                "organization_id": install_config["organization_id"],
                "health_checks": [
                    {
                        "name": "HTTP Health Check",
                        "type": "http",
                        "url": f"https://{install_config['app_id']}-{install_config['organization_id']}.enterprise.local/health",
                        "interval": 60
                    },
                    {
                        "name": "Resource Usage",
                        "type": "metrics",
                        "metrics": ["cpu", "memory", "disk"],
                        "interval": 30
                    }
                ],
                "alerts": [
                    {
                        "name": "High CPU Usage",
                        "condition": "cpu_usage > 80",
                        "severity": "warning"
                    },
                    {
                        "name": "Service Down",
                        "condition": "http_status != 200",
                        "severity": "critical"
                    }
                ]
            }
            
            # In a real implementation, this would integrate with the monitoring system
            logger.info(f"Monitoring configured for installation {installation_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring: {e}")

    async def get_installed_apps(self, org_id: str) -> Dict[str, Any]:
        """Get installed applications for organization"""
        try:
            if org_id not in self.installed_apps:
                return {
                    "status": "success",
                    "installed_apps": [],
                    "total_count": 0
                }
            
            org_apps = self.installed_apps[org_id]
            app_details = []
            
            for app_id, install_config in org_apps.items():
                app_data = self.app_catalog.get(app_id, {})
                
                # Get current status
                app_status = await self._get_app_status(install_config["id"])
                
                # Get usage statistics
                usage_stats = await self._get_app_usage_stats(install_config["id"])
                
                app_info = {
                    "installation_id": install_config["id"],
                    "app_id": app_id,
                    "app_name": app_data.get("name", install_config.get("app_name")),
                    "version": install_config.get("version"),
                    "category": app_data.get("category"),
                    "installed_at": install_config.get("installed_at"),
                    "status": app_status,
                    "usage_stats": usage_stats,
                    "access_urls": install_config.get("installation_result", {}).get("access_urls", {}),
                    "resource_usage": install_config.get("installation_result", {}).get("resource_usage", {}),
                    "last_updated": install_config.get("last_updated"),
                    "update_available": await self._check_update_available(app_id, install_config.get("version"))
                }
                
                app_details.append(app_info)
            
            return {
                "status": "success",
                "installed_apps": app_details,
                "total_count": len(app_details),
                "categories": list(set(app["category"] for app in app_details if app["category"])),
                "apps_needing_updates": sum(1 for app in app_details if app["update_available"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get installed apps: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _get_app_status(self, installation_id: str) -> Dict[str, Any]:
        """Get current status of installed application"""
        # Simulate status check
        statuses = ["running", "stopped", "error", "updating"]
        import random
        
        return {
            "status": random.choice(statuses[:2]),  # Mostly running/stopped
            "health": "healthy",
            "uptime": "5d 12h 30m",
            "last_check": datetime.now().isoformat()
        }

    async def _get_app_usage_stats(self, installation_id: str) -> Dict[str, Any]:
        """Get usage statistics for installed application"""
        # Simulate usage stats
        import random
        
        return {
            "cpu_usage": f"{random.randint(10, 80)}%",
            "memory_usage": f"{random.randint(20, 90)}%",
            "disk_usage": f"{random.randint(30, 70)}%",
            "network_io": f"{random.randint(1, 100)} MB/s",
            "requests_per_minute": random.randint(50, 500),
            "active_users": random.randint(5, 100)
        }

    async def _check_update_available(self, app_id: str, current_version: str) -> bool:
        """Check if update is available for application"""
        try:
            if app_id not in self.app_catalog:
                return False
            
            latest_version = self.app_catalog[app_id].get("version")
            if not latest_version or not current_version:
                return False
            
            # Simple version comparison (in production, use proper semver)
            return latest_version != current_version
            
        except Exception as e:
            logger.error(f"Failed to check update availability: {e}")
            return False

    async def _update_checker_loop(self):
        """Background task to check for application updates"""
        while True:
            try:
                # Check for updates every 24 hours
                await asyncio.sleep(24 * 3600)
                
                # Check each installed application for updates
                for org_id, org_apps in self.installed_apps.items():
                    for app_id, install_config in org_apps.items():
                        if await self._check_update_available(app_id, install_config.get("version")):
                            logger.info(f"Update available for {app_id} in organization {org_id}")
                            # In production, would send notifications
                
            except Exception as e:
                logger.error(f"Error in update checker loop: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour

# Global instance
enterprise_store_system = EnterpriseAppStoreSystem()