#!/usr/bin/env python3
"""
Compliance Customization System
Multi-framework compliance support (SOC2, HIPAA, GDPR, etc.) with
custom audit controls, policy management, and automated compliance checks.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import hashlib
import re

logger = logging.getLogger(__name__)

class ComplianceFramework(str, Enum):
    SOC2 = "soc2"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    FEDRAMP = "fedramp"
    NIST = "nist"
    CCPA = "ccpa"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    PENDING_REVIEW = "pending_review"
    NOT_ASSESSED = "not_assessed"

class AuditFrequency(str, Enum):
    CONTINUOUS = "continuous"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"

class ComplianceSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/enterprise-custom/data/enterprise_custom.db"
        self.compliance_frameworks = {}
        self.organization_compliance = {}
        self.audit_templates = {}
        self.policy_templates = {}
        
    async def initialize(self):
        """Initialize the compliance system"""
        try:
            await self._setup_database_tables()
            await self._load_compliance_frameworks()
            await self._load_audit_templates()
            await self._load_policy_templates()
            await self._load_organization_compliance()
            await self._start_compliance_monitor()
            logger.info("Compliance system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize compliance system: {e}")
            raise

    async def _setup_database_tables(self):
        """Setup database tables for compliance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Compliance configurations table (already exists from main.py)
        
        # Audit controls table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_controls (
                id TEXT PRIMARY KEY,
                compliance_config_id TEXT NOT NULL,
                control_id TEXT NOT NULL,
                control_name TEXT NOT NULL,
                control_description TEXT,
                framework TEXT NOT NULL,
                category TEXT,
                requirements TEXT,
                implementation_status TEXT DEFAULT 'not_implemented',
                evidence_required BOOLEAN DEFAULT TRUE,
                automated_check BOOLEAN DEFAULT FALSE,
                frequency TEXT DEFAULT 'monthly',
                last_assessment DATE,
                next_assessment DATE,
                responsible_party TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (compliance_config_id) REFERENCES compliance_configs (id)
            )
        ''')
        
        # Policy documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS policy_documents (
                id TEXT PRIMARY KEY,
                compliance_config_id TEXT NOT NULL,
                policy_name TEXT NOT NULL,
                policy_type TEXT NOT NULL,
                version TEXT DEFAULT '1.0',
                status TEXT DEFAULT 'draft',
                content TEXT NOT NULL,
                template_id TEXT,
                approved_by TEXT,
                approved_date DATE,
                effective_date DATE,
                review_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (compliance_config_id) REFERENCES compliance_configs (id)
            )
        ''')
        
        # Audit evidence table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_evidence (
                id TEXT PRIMARY KEY,
                control_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                evidence_data TEXT NOT NULL,
                file_path TEXT,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                collector TEXT,
                verification_status TEXT DEFAULT 'pending',
                verified_by TEXT,
                verified_at TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (control_id) REFERENCES audit_controls (id)
            )
        ''')
        
        # Risk assessments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id TEXT PRIMARY KEY,
                compliance_config_id TEXT NOT NULL,
                risk_name TEXT NOT NULL,
                risk_description TEXT,
                likelihood INTEGER CHECK (likelihood >= 1 AND likelihood <= 5),
                impact INTEGER CHECK (impact >= 1 AND impact <= 5),
                risk_score INTEGER,
                mitigation_plan TEXT,
                owner TEXT,
                status TEXT DEFAULT 'identified',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (compliance_config_id) REFERENCES compliance_configs (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def _load_compliance_frameworks(self):
        """Load compliance framework definitions"""
        self.compliance_frameworks = {
            ComplianceFramework.SOC2: {
                "name": "SOC 2 Type II",
                "description": "Service Organization Control 2 focusing on security, availability, processing integrity, confidentiality, and privacy",
                "trust_service_criteria": {
                    "CC": "Common Criteria",
                    "A": "Availability",
                    "P": "Processing Integrity", 
                    "C": "Confidentiality",
                    "PI": "Privacy"
                },
                "controls": {
                    "CC1.1": {
                        "name": "Control Environment",
                        "description": "The entity demonstrates a commitment to integrity and ethical values"
                    },
                    "CC2.1": {
                        "name": "Communication and Information",
                        "description": "The entity obtains or generates and uses relevant, quality information"
                    },
                    "A1.1": {
                        "name": "Availability Policy",
                        "description": "The entity maintains system availability policies"
                    }
                },
                "audit_frequency": AuditFrequency.ANNUALLY
            },
            ComplianceFramework.HIPAA: {
                "name": "Health Insurance Portability and Accountability Act",
                "description": "US healthcare data protection regulations",
                "safeguards": {
                    "administrative": "Administrative Safeguards",
                    "physical": "Physical Safeguards",
                    "technical": "Technical Safeguards"
                },
                "controls": {
                    "164.308": {
                        "name": "Administrative Safeguards",
                        "description": "Security Officer, Workforce Training, Access Management"
                    },
                    "164.310": {
                        "name": "Physical Safeguards",
                        "description": "Facility Controls, Workstation Use, Device Controls"
                    },
                    "164.312": {
                        "name": "Technical Safeguards",
                        "description": "Access Control, Audit Controls, Integrity, Transmission Security"
                    }
                },
                "audit_frequency": AuditFrequency.ANNUALLY
            },
            ComplianceFramework.GDPR: {
                "name": "General Data Protection Regulation",
                "description": "EU data protection and privacy regulation",
                "principles": {
                    "lawfulness": "Lawful, fair, and transparent processing",
                    "purpose_limitation": "Purpose limitation",
                    "data_minimization": "Data minimization",
                    "accuracy": "Accuracy",
                    "storage_limitation": "Storage limitation",
                    "integrity_confidentiality": "Integrity and confidentiality",
                    "accountability": "Accountability"
                },
                "controls": {
                    "Art7": {
                        "name": "Conditions for consent",
                        "description": "Clear consent mechanism for data processing"
                    },
                    "Art25": {
                        "name": "Data protection by design and by default",
                        "description": "Privacy by design implementation"
                    },
                    "Art32": {
                        "name": "Security of processing",
                        "description": "Appropriate technical and organizational measures"
                    }
                },
                "audit_frequency": AuditFrequency.CONTINUOUSLY
            }
        }

    async def _load_audit_templates(self):
        """Load audit checklist templates"""
        self.audit_templates = {
            "soc2_security": {
                "name": "SOC 2 Security Audit",
                "framework": ComplianceFramework.SOC2,
                "checklist": [
                    {
                        "control": "CC6.1",
                        "question": "Has the organization implemented logical access security controls?",
                        "evidence_required": ["access_control_policy", "user_access_logs", "privileged_access_review"]
                    },
                    {
                        "control": "CC6.2", 
                        "question": "Are authentication mechanisms properly configured?",
                        "evidence_required": ["authentication_policy", "multi_factor_auth_config", "password_policy"]
                    }
                ]
            },
            "hipaa_technical": {
                "name": "HIPAA Technical Safeguards",
                "framework": ComplianceFramework.HIPAA,
                "checklist": [
                    {
                        "control": "164.312(a)(1)",
                        "question": "Is access to PHI restricted to authorized users?",
                        "evidence_required": ["access_control_system", "user_access_matrix", "audit_logs"]
                    }
                ]
            }
        }

    async def _load_policy_templates(self):
        """Load policy document templates"""
        self.policy_templates = {
            "information_security": {
                "name": "Information Security Policy",
                "applicable_frameworks": [ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
                "template": """
# Information Security Policy

## Purpose
This policy establishes the framework for protecting organizational information assets.

## Scope
This policy applies to all employees, contractors, and third parties.

## Policy Statements
1. All information must be classified and protected according to its sensitivity
2. Access to information must be granted on a need-to-know basis
3. Security incidents must be reported immediately

## Roles and Responsibilities
- CISO: Overall security oversight
- IT Team: Technical implementation
- All Users: Compliance with security practices

## Review and Updates
This policy will be reviewed annually and updated as needed.
                """
            },
            "data_privacy": {
                "name": "Data Privacy Policy", 
                "applicable_frameworks": [ComplianceFramework.GDPR, ComplianceFramework.CCPA],
                "template": """
# Data Privacy Policy

## Purpose
This policy governs the collection, use, and protection of personal data.

## Data Collection Principles
1. Data shall be collected for specified, explicit, and legitimate purposes
2. Data collection shall be limited to what is necessary
3. Consent shall be obtained where required

## Individual Rights
- Right to access personal data
- Right to rectification
- Right to erasure
- Right to data portability

## Data Processing Lawful Basis
Processing is based on one or more of the following:
- Consent
- Contract performance
- Legal obligation
- Vital interests
- Public task
- Legitimate interests
                """
            }
        }

    async def _load_organization_compliance(self):
        """Load existing organization compliance configurations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, organization_id, data FROM compliance_configs
            ''')
            
            configs = cursor.fetchall()
            for config_id, org_id, data_json in configs:
                config_data = json.loads(data_json)
                if org_id not in self.organization_compliance:
                    self.organization_compliance[org_id] = {}
                self.organization_compliance[org_id][config_id] = config_data
                
            conn.close()
            logger.info(f"Loaded {len(configs)} compliance configurations")
        except Exception as e:
            logger.error(f"Failed to load compliance configurations: {e}")

    async def _start_compliance_monitor(self):
        """Start background compliance monitoring"""
        asyncio.create_task(self._compliance_monitoring_loop())

    async def initialize_compliance(self, org_id: str, frameworks: List[ComplianceFramework]):
        """Initialize compliance configuration for organization"""
        try:
            for framework in frameworks:
                if framework not in self.compliance_frameworks:
                    continue
                
                config_id = f"COMP_{uuid.uuid4().hex[:12].upper()}"
                
                compliance_config = {
                    "id": config_id,
                    "organization_id": org_id,
                    "framework": framework,
                    "framework_info": self.compliance_frameworks[framework],
                    "configuration": {
                        "enabled_controls": [],
                        "risk_tolerance": "medium",
                        "audit_frequency": self.compliance_frameworks[framework]["audit_frequency"],
                        "responsible_parties": {},
                        "compliance_contacts": []
                    },
                    "audit_schedule": {},
                    "last_audit_date": None,
                    "next_audit_date": None,
                    "compliance_status": ComplianceStatus.NOT_ASSESSED,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                # Generate default controls
                await self._generate_default_controls(config_id, framework)
                
                # Generate default policies
                await self._generate_default_policies(config_id, framework)
                
                # Store configuration
                await self._store_compliance_configuration(compliance_config)
                
                if org_id not in self.organization_compliance:
                    self.organization_compliance[org_id] = {}
                self.organization_compliance[org_id][config_id] = compliance_config
                
                logger.info(f"Initialized {framework} compliance for organization {org_id}")
                
        except Exception as e:
            logger.error(f"Failed to initialize compliance: {e}")
            raise

    async def _generate_default_controls(self, config_id: str, framework: ComplianceFramework):
        """Generate default audit controls for framework"""
        try:
            framework_info = self.compliance_frameworks[framework]
            controls = framework_info.get("controls", {})
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for control_id, control_info in controls.items():
                audit_control = {
                    "id": f"CTRL_{uuid.uuid4().hex[:8].upper()}",
                    "compliance_config_id": config_id,
                    "control_id": control_id,
                    "control_name": control_info["name"],
                    "control_description": control_info["description"],
                    "framework": framework,
                    "category": self._categorize_control(control_id, framework),
                    "requirements": self._get_control_requirements(control_id, framework),
                    "implementation_status": "not_implemented",
                    "evidence_required": True,
                    "automated_check": self._can_automate_control(control_id, framework),
                    "frequency": framework_info["audit_frequency"],
                    "next_assessment": self._calculate_next_assessment(framework_info["audit_frequency"]),
                    "created_at": datetime.now().isoformat()
                }
                
                cursor.execute('''
                    INSERT INTO audit_controls
                    (id, compliance_config_id, control_id, control_name, control_description,
                     framework, category, requirements, implementation_status, evidence_required,
                     automated_check, frequency, next_assessment, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    audit_control["id"], config_id, control_id,
                    audit_control["control_name"], audit_control["control_description"],
                    framework, audit_control["category"], json.dumps(audit_control["requirements"]),
                    audit_control["implementation_status"], audit_control["evidence_required"],
                    audit_control["automated_check"], audit_control["frequency"],
                    audit_control["next_assessment"], json.dumps(audit_control)
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to generate default controls: {e}")

    def _categorize_control(self, control_id: str, framework: ComplianceFramework) -> str:
        """Categorize control based on ID and framework"""
        if framework == ComplianceFramework.SOC2:
            if control_id.startswith("CC"):
                return "Common Criteria"
            elif control_id.startswith("A"):
                return "Availability"
            elif control_id.startswith("P"):
                return "Processing Integrity"
            elif control_id.startswith("C"):
                return "Confidentiality"
            elif control_id.startswith("PI"):
                return "Privacy"
        elif framework == ComplianceFramework.HIPAA:
            if "308" in control_id:
                return "Administrative Safeguards"
            elif "310" in control_id:
                return "Physical Safeguards"
            elif "312" in control_id:
                return "Technical Safeguards"
        
        return "General"

    def _get_control_requirements(self, control_id: str, framework: ComplianceFramework) -> List[str]:
        """Get implementation requirements for control"""
        requirements = []
        
        if framework == ComplianceFramework.SOC2:
            if "access" in control_id.lower():
                requirements = ["Access control policy", "User access reviews", "Privileged access management"]
            elif "monitoring" in control_id.lower():
                requirements = ["Monitoring system", "Log review procedures", "Alerting mechanisms"]
        elif framework == ComplianceFramework.HIPAA:
            if "access" in control_id:
                requirements = ["User access controls", "Authentication mechanisms", "Authorization procedures"]
            elif "audit" in control_id:
                requirements = ["Audit logging", "Log review", "Audit trail protection"]
        
        return requirements or ["Policy documentation", "Implementation evidence", "Testing results"]

    def _can_automate_control(self, control_id: str, framework: ComplianceFramework) -> bool:
        """Determine if control can be automated"""
        automated_controls = {
            ComplianceFramework.SOC2: ["CC6.1", "CC6.2", "CC7.1"],
            ComplianceFramework.HIPAA: ["164.312(b)", "164.312(c)", "164.312(d)"],
            ComplianceFramework.GDPR: ["Art32"]
        }
        
        return control_id in automated_controls.get(framework, [])

    def _calculate_next_assessment(self, frequency: AuditFrequency) -> str:
        """Calculate next assessment date"""
        now = datetime.now()
        
        if frequency == AuditFrequency.DAILY:
            next_date = now + timedelta(days=1)
        elif frequency == AuditFrequency.WEEKLY:
            next_date = now + timedelta(weeks=1)
        elif frequency == AuditFrequency.MONTHLY:
            next_date = now + timedelta(days=30)
        elif frequency == AuditFrequency.QUARTERLY:
            next_date = now + timedelta(days=90)
        elif frequency == AuditFrequency.ANNUALLY:
            next_date = now + timedelta(days=365)
        else:
            next_date = now + timedelta(days=30)  # Default to monthly
            
        return next_date.isoformat()

    async def _generate_default_policies(self, config_id: str, framework: ComplianceFramework):
        """Generate default policy documents for framework"""
        try:
            applicable_policies = []
            
            for policy_id, policy_info in self.policy_templates.items():
                if framework in policy_info.get("applicable_frameworks", []):
                    applicable_policies.append(policy_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for policy_id in applicable_policies:
                policy_info = self.policy_templates[policy_id]
                
                policy_doc = {
                    "id": f"POLICY_{uuid.uuid4().hex[:8].upper()}",
                    "compliance_config_id": config_id,
                    "policy_name": policy_info["name"],
                    "policy_type": policy_id,
                    "version": "1.0",
                    "status": "draft",
                    "content": policy_info["template"],
                    "template_id": policy_id,
                    "effective_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
                    "review_date": (datetime.now() + timedelta(days=365)).date().isoformat(),
                    "created_at": datetime.now().isoformat()
                }
                
                cursor.execute('''
                    INSERT INTO policy_documents
                    (id, compliance_config_id, policy_name, policy_type, version,
                     status, content, template_id, effective_date, review_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    policy_doc["id"], config_id, policy_doc["policy_name"],
                    policy_doc["policy_type"], policy_doc["version"],
                    policy_doc["status"], policy_doc["content"],
                    policy_doc["template_id"], policy_doc["effective_date"],
                    policy_doc["review_date"]
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to generate default policies: {e}")

    async def _store_compliance_configuration(self, compliance_config: dict):
        """Store compliance configuration in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO compliance_configs
                (id, organization_id, framework, configuration, audit_schedule,
                 last_audit_date, next_audit_date, compliance_status, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                compliance_config["id"],
                compliance_config["organization_id"],
                compliance_config["framework"],
                json.dumps(compliance_config["configuration"]),
                json.dumps(compliance_config.get("audit_schedule", {})),
                compliance_config.get("last_audit_date"),
                compliance_config.get("next_audit_date"),
                compliance_config["compliance_status"],
                json.dumps(compliance_config)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store compliance configuration: {e}")
            raise

    async def configure_framework(self, compliance_data: dict) -> Dict[str, Any]:
        """Configure compliance framework for organization"""
        try:
            org_id = compliance_data["organization_id"]
            framework = ComplianceFramework(compliance_data["framework"])
            
            if framework not in self.compliance_frameworks:
                return {
                    "status": "error",
                    "message": f"Unsupported framework: {framework}"
                }
            
            config_id = compliance_data.get("config_id")
            if not config_id:
                config_id = f"COMP_{uuid.uuid4().hex[:12].upper()}"
            
            # Build configuration
            compliance_config = {
                "id": config_id,
                "organization_id": org_id,
                "framework": framework,
                "configuration": {
                    "enabled_controls": compliance_data.get("enabled_controls", []),
                    "risk_tolerance": compliance_data.get("risk_tolerance", "medium"),
                    "audit_frequency": compliance_data.get("audit_frequency", "quarterly"),
                    "responsible_parties": compliance_data.get("responsible_parties", {}),
                    "compliance_contacts": compliance_data.get("compliance_contacts", []),
                    "custom_controls": compliance_data.get("custom_controls", [])
                },
                "reporting_requirements": compliance_data.get("reporting_requirements", {}),
                "compliance_status": ComplianceStatus.PENDING_REVIEW,
                "updated_at": datetime.now().isoformat()
            }
            
            # Update or create controls based on configuration
            await self._update_controls_configuration(config_id, compliance_config)
            
            # Store configuration
            await self._store_compliance_configuration(compliance_config)
            
            # Update local cache
            if org_id not in self.organization_compliance:
                self.organization_compliance[org_id] = {}
            self.organization_compliance[org_id][config_id] = compliance_config
            
            return {
                "status": "success",
                "config_id": config_id,
                "framework": framework,
                "controls_configured": len(compliance_config["configuration"]["enabled_controls"]),
                "next_steps": [
                    "Review and customize audit controls",
                    "Assign responsible parties",
                    "Schedule initial assessment",
                    "Begin evidence collection"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to configure framework: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _update_controls_configuration(self, config_id: str, compliance_config: dict):
        """Update controls based on configuration"""
        try:
            enabled_controls = compliance_config["configuration"]["enabled_controls"]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update implementation status for enabled controls
            if enabled_controls:
                placeholders = ",".join(["?" for _ in enabled_controls])
                cursor.execute(f'''
                    UPDATE audit_controls 
                    SET implementation_status = 'in_progress'
                    WHERE compliance_config_id = ? AND control_id IN ({placeholders})
                ''', [config_id] + enabled_controls)
            
            # Update responsible parties
            responsible_parties = compliance_config["configuration"]["responsible_parties"]
            for control_id, party in responsible_parties.items():
                cursor.execute('''
                    UPDATE audit_controls 
                    SET responsible_party = ?
                    WHERE compliance_config_id = ? AND control_id = ?
                ''', (party, config_id, control_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update controls configuration: {e}")

    async def get_compliance_status(self, org_id: str) -> Dict[str, Any]:
        """Get compliance status for organization"""
        try:
            if org_id not in self.organization_compliance:
                return {
                    "status": "success",
                    "compliance_status": "no_frameworks_configured",
                    "frameworks": []
                }
            
            org_compliance = self.organization_compliance[org_id]
            frameworks_status = []
            
            for config_id, config_data in org_compliance.items():
                # Get control compliance statistics
                control_stats = await self._get_control_statistics(config_id)
                
                # Get recent audit results
                recent_audits = await self._get_recent_audits(config_id)
                
                # Calculate overall compliance score
                compliance_score = await self._calculate_compliance_score(config_id)
                
                framework_status = {
                    "config_id": config_id,
                    "framework": config_data["framework"],
                    "framework_name": self.compliance_frameworks[config_data["framework"]]["name"],
                    "compliance_status": config_data.get("compliance_status", ComplianceStatus.NOT_ASSESSED),
                    "compliance_score": compliance_score,
                    "control_statistics": control_stats,
                    "recent_audits": recent_audits,
                    "last_assessment": config_data.get("last_audit_date"),
                    "next_assessment": config_data.get("next_audit_date"),
                    "risk_level": await self._assess_risk_level(config_id)
                }
                
                frameworks_status.append(framework_status)
            
            # Calculate overall organizational compliance
            overall_score = sum(fw["compliance_score"] for fw in frameworks_status) / len(frameworks_status)
            
            return {
                "status": "success",
                "organization_id": org_id,
                "overall_compliance_score": round(overall_score, 1),
                "frameworks": frameworks_status,
                "total_frameworks": len(frameworks_status),
                "compliant_frameworks": len([fw for fw in frameworks_status if fw["compliance_status"] == ComplianceStatus.COMPLIANT])
            }
            
        except Exception as e:
            logger.error(f"Failed to get compliance status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _get_control_statistics(self, config_id: str) -> Dict[str, Any]:
        """Get statistics for audit controls"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total controls
            cursor.execute('''
                SELECT COUNT(*) FROM audit_controls WHERE compliance_config_id = ?
            ''', (config_id,))
            total_controls = cursor.fetchone()[0]
            
            # Implemented controls
            cursor.execute('''
                SELECT COUNT(*) FROM audit_controls 
                WHERE compliance_config_id = ? AND implementation_status = 'implemented'
            ''', (config_id,))
            implemented_controls = cursor.fetchone()[0]
            
            # Controls by category
            cursor.execute('''
                SELECT category, COUNT(*) FROM audit_controls 
                WHERE compliance_config_id = ? GROUP BY category
            ''', (config_id,))
            category_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Controls requiring attention
            cursor.execute('''
                SELECT COUNT(*) FROM audit_controls 
                WHERE compliance_config_id = ? AND (
                    implementation_status = 'not_implemented' OR
                    next_assessment <= date('now')
                )
            ''', (config_id,))
            controls_needing_attention = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_controls": total_controls,
                "implemented_controls": implemented_controls,
                "implementation_rate": (implemented_controls / max(total_controls, 1)) * 100,
                "category_breakdown": category_stats,
                "controls_needing_attention": controls_needing_attention
            }
            
        except Exception as e:
            logger.error(f"Failed to get control statistics: {e}")
            return {}

    async def _get_recent_audits(self, config_id: str) -> List[Dict[str, Any]]:
        """Get recent audit activities"""
        # Simulate recent audit data
        return [
            {
                "audit_date": "2024-01-15",
                "audit_type": "internal",
                "findings": 3,
                "recommendations": 5,
                "status": "completed"
            },
            {
                "audit_date": "2023-10-20", 
                "audit_type": "external",
                "findings": 1,
                "recommendations": 2,
                "status": "completed"
            }
        ]

    async def _calculate_compliance_score(self, config_id: str) -> float:
        """Calculate overall compliance score"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN implementation_status = 'implemented' THEN 1 ELSE 0 END) as implemented,
                    SUM(CASE WHEN evidence_required AND implementation_status = 'implemented' THEN 1 ELSE 0 END) as with_evidence
                FROM audit_controls 
                WHERE compliance_config_id = ?
            ''', (config_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result or result[0] == 0:
                return 0.0
            
            total, implemented, with_evidence = result
            
            # Base score from implementation
            base_score = (implemented / total) * 70
            
            # Bonus for evidence collection
            evidence_bonus = (with_evidence / max(implemented, 1)) * 30
            
            return min(base_score + evidence_bonus, 100.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate compliance score: {e}")
            return 0.0

    async def _assess_risk_level(self, config_id: str) -> str:
        """Assess risk level based on compliance status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count high-risk controls not implemented
            cursor.execute('''
                SELECT COUNT(*) FROM audit_controls 
                WHERE compliance_config_id = ? AND implementation_status = 'not_implemented'
                AND (control_id LIKE '%security%' OR control_id LIKE '%access%')
            ''', (config_id,))
            
            high_risk_controls = cursor.fetchone()[0]
            
            # Check overdue assessments
            cursor.execute('''
                SELECT COUNT(*) FROM audit_controls 
                WHERE compliance_config_id = ? AND next_assessment <= date('now')
            ''', (config_id,))
            
            overdue_assessments = cursor.fetchone()[0]
            
            conn.close()
            
            if high_risk_controls > 5 or overdue_assessments > 10:
                return "high"
            elif high_risk_controls > 2 or overdue_assessments > 5:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"Failed to assess risk level: {e}")
            return "unknown"

    async def trigger_audit(self, org_id: str, audit_data: dict) -> Dict[str, Any]:
        """Trigger compliance audit"""
        try:
            config_id = audit_data.get("config_id")
            audit_type = audit_data.get("audit_type", "internal")
            audit_scope = audit_data.get("scope", "full")
            
            if not config_id or config_id not in self.organization_compliance.get(org_id, {}):
                return {
                    "status": "error",
                    "message": "Compliance configuration not found"
                }
            
            audit_id = f"AUDIT_{uuid.uuid4().hex[:12].upper()}"
            
            # Create audit record
            audit_record = {
                "id": audit_id,
                "config_id": config_id,
                "organization_id": org_id,
                "audit_type": audit_type,
                "audit_scope": audit_scope,
                "status": "in_progress",
                "started_at": datetime.now().isoformat(),
                "auditor": audit_data.get("auditor", "system"),
                "findings": [],
                "recommendations": []
            }
            
            # Perform audit checks
            audit_results = await self._perform_audit_checks(config_id, audit_scope)
            
            # Update audit record with results
            audit_record.update(audit_results)
            audit_record["completed_at"] = datetime.now().isoformat()
            audit_record["status"] = "completed"
            
            return {
                "status": "success",
                "audit_id": audit_id,
                "audit_results": audit_results,
                "findings_count": len(audit_results.get("findings", [])),
                "recommendations_count": len(audit_results.get("recommendations", [])),
                "overall_score": audit_results.get("overall_score", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger audit: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _perform_audit_checks(self, config_id: str, scope: str) -> Dict[str, Any]:
        """Perform automated audit checks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT control_id, control_name, implementation_status, automated_check
                FROM audit_controls 
                WHERE compliance_config_id = ?
            ''', (config_id,))
            
            controls = cursor.fetchall()
            conn.close()
            
            findings = []
            recommendations = []
            total_score = 0
            
            for control_id, control_name, impl_status, automated_check in controls:
                if impl_status == "not_implemented":
                    findings.append({
                        "control_id": control_id,
                        "control_name": control_name,
                        "severity": "high",
                        "finding": "Control not implemented",
                        "recommendation": f"Implement {control_name} control"
                    })
                elif impl_status == "in_progress":
                    findings.append({
                        "control_id": control_id,
                        "control_name": control_name,
                        "severity": "medium",
                        "finding": "Control implementation incomplete",
                        "recommendation": f"Complete implementation of {control_name}"
                    })
                elif impl_status == "implemented":
                    total_score += 1
                    
                    if automated_check and not await self._run_automated_check(control_id):
                        findings.append({
                            "control_id": control_id,
                            "control_name": control_name,
                            "severity": "medium",
                            "finding": "Automated check failed",
                            "recommendation": f"Review and fix {control_name} configuration"
                        })
            
            # Generate recommendations
            if len(findings) > 0:
                recommendations.extend([
                    "Prioritize implementation of high-severity findings",
                    "Establish regular review cycles for controls",
                    "Implement automated monitoring where possible"
                ])
            
            overall_score = (total_score / max(len(controls), 1)) * 100
            
            return {
                "findings": findings,
                "recommendations": recommendations,
                "overall_score": round(overall_score, 1),
                "controls_assessed": len(controls),
                "controls_compliant": total_score
            }
            
        except Exception as e:
            logger.error(f"Failed to perform audit checks: {e}")
            return {"findings": [], "recommendations": [], "overall_score": 0}

    async def _run_automated_check(self, control_id: str) -> bool:
        """Run automated compliance check for control"""
        # Simulate automated check
        import random
        return random.choice([True, True, False])  # 66% success rate

    async def _compliance_monitoring_loop(self):
        """Background compliance monitoring"""
        while True:
            try:
                # Check for overdue assessments
                await self._check_overdue_assessments()
                
                # Run automated compliance checks
                await self._run_periodic_compliance_checks()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in compliance monitoring loop: {e}")
                await asyncio.sleep(300)

    async def _check_overdue_assessments(self):
        """Check for overdue compliance assessments"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT compliance_config_id, control_id, control_name, next_assessment
                FROM audit_controls 
                WHERE next_assessment <= date('now')
            ''')
            
            overdue_controls = cursor.fetchall()
            conn.close()
            
            for config_id, control_id, control_name, next_assessment in overdue_controls:
                logger.warning(f"Control {control_id} ({control_name}) assessment overdue: {next_assessment}")
                # In production, would send notifications
                
        except Exception as e:
            logger.error(f"Failed to check overdue assessments: {e}")

    async def _run_periodic_compliance_checks(self):
        """Run periodic automated compliance checks"""
        try:
            for org_id, org_compliance in self.organization_compliance.items():
                for config_id, config_data in org_compliance.items():
                    if config_data.get("compliance_status") == ComplianceStatus.COMPLIANT:
                        # Run automated checks for compliant frameworks
                        await self._perform_audit_checks(config_id, "automated")
                        
        except Exception as e:
            logger.error(f"Failed to run periodic compliance checks: {e}")

# Global instance
compliance_system = ComplianceSystem()