#!/usr/bin/env python3
"""
License Manager - Software licensing system with validation, tracking, and enforcement
Supports multiple license types, usage tracking, and compliance monitoring
"""

import json
import uuid
import hashlib
import hmac
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import sqlite3
from enum import Enum
import secrets
import cryptography
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    PERPETUAL = "perpetual"
    SUBSCRIPTION = "subscription"
    TRIAL = "trial"
    ACADEMIC = "academic"
    ENTERPRISE = "enterprise"
    DEVELOPER = "developer"
    OEM = "oem"
    OPEN_SOURCE = "open_source"


class LicenseStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"


@dataclass
class License:
    """Software license definition"""
    id: str
    license_key: str
    product_name: str
    license_type: LicenseType
    status: LicenseStatus
    customer_id: str
    customer_name: str
    customer_email: str
    features: List[str]
    max_users: int
    max_installations: int
    issued_date: str
    expiration_date: Optional[str] = None
    last_validated: Optional[str] = None
    usage_count: int = 0
    installation_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if isinstance(self.license_type, str):
            self.license_type = LicenseType(self.license_type)
        if isinstance(self.status, str):
            self.status = LicenseStatus(self.status)
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LicenseValidation:
    """License validation result"""
    valid: bool
    license_key: str
    product_name: str
    customer_id: str
    features: List[str]
    expires_at: Optional[str] = None
    usage_remaining: int = -1
    installations_remaining: int = -1
    status: str = "unknown"
    error_message: Optional[str] = None


@dataclass
class LicenseUsage:
    """License usage record"""
    id: str
    license_key: str
    customer_id: str
    product_name: str
    feature_used: str
    timestamp: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class LicenseTemplate:
    """License agreement template"""
    id: str
    name: str
    license_type: str
    template_text: str
    variables: List[str]
    created_at: str
    updated_at: str


class LicenseManager:
    """Manages software licensing with validation and tracking"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = Path("/home/activeloguser/activelog/data/legal-framework/licenses.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption key for license keys
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        self.licenses = {}  # license_key -> License
        self.usage_records = {}  # usage_id -> LicenseUsage
        self.templates = {}  # template_id -> LicenseTemplate
        
        self._init_database()
        self._load_licenses()
        self._init_templates()
        
        logger.info("License Manager initialized")

    def create_license(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new software license"""
        try:
            license_id = str(uuid.uuid4())
            license_key = self._generate_license_key(license_data)
            
            # Calculate expiration date
            expiration_date = None
            if license_data.get('license_type') == 'trial':
                days = license_data.get('trial_days', 30)
                expiration_date = (datetime.utcnow() + timedelta(days=days)).isoformat()
            elif license_data.get('license_type') == 'subscription':
                months = license_data.get('subscription_months', 12)
                expiration_date = (datetime.utcnow() + timedelta(days=months*30)).isoformat()
            
            license_obj = License(
                id=license_id,
                license_key=license_key,
                product_name=license_data['product_name'],
                license_type=LicenseType(license_data['license_type']),
                status=LicenseStatus.ACTIVE,
                customer_id=license_data['customer_id'],
                customer_name=license_data['customer_name'],
                customer_email=license_data['customer_email'],
                features=license_data.get('features', []),
                max_users=license_data.get('max_users', 1),
                max_installations=license_data.get('max_installations', 1),
                issued_date=datetime.utcnow().isoformat(),
                expiration_date=expiration_date,
                metadata=license_data.get('metadata', {})
            )
            
            # Store license
            self.licenses[license_key] = license_obj
            self._save_license(license_obj)
            
            # Generate license document
            license_document = self._generate_license_document(license_obj)
            
            logger.info(f"Created license {license_key} for {license_obj.customer_name}")
            
            return {
                'license_id': license_id,
                'license_key': license_key,
                'license': asdict(license_obj),
                'document': license_document,
                'installation_instructions': self._get_installation_instructions(license_obj),
                'download_links': self._get_download_links(license_obj)
            }
            
        except Exception as e:
            logger.error(f"Failed to create license: {e}")
            raise

    def validate_license(self, license_key: str, context: Dict[str, Any] = None) -> LicenseValidation:
        """Validate license key and return validation result"""
        try:
            license_obj = self.licenses.get(license_key)
            
            if not license_obj:
                return LicenseValidation(
                    valid=False,
                    license_key=license_key,
                    product_name="unknown",
                    customer_id="unknown",
                    features=[],
                    error_message="License key not found"
                )
            
            # Check license status
            if license_obj.status != LicenseStatus.ACTIVE:
                return LicenseValidation(
                    valid=False,
                    license_key=license_key,
                    product_name=license_obj.product_name,
                    customer_id=license_obj.customer_id,
                    features=license_obj.features,
                    status=license_obj.status.value,
                    error_message=f"License is {license_obj.status.value}"
                )
            
            # Check expiration
            if license_obj.expiration_date:
                expiration = datetime.fromisoformat(license_obj.expiration_date.replace('Z', '+00:00'))
                if datetime.utcnow() > expiration:
                    license_obj.status = LicenseStatus.EXPIRED
                    self._save_license(license_obj)
                    
                    return LicenseValidation(
                        valid=False,
                        license_key=license_key,
                        product_name=license_obj.product_name,
                        customer_id=license_obj.customer_id,
                        features=license_obj.features,
                        expires_at=license_obj.expiration_date,
                        status="expired",
                        error_message="License has expired"
                    )
            
            # Check installation limits
            installations_remaining = license_obj.max_installations - license_obj.installation_count
            if installations_remaining <= 0 and context and context.get('new_installation'):
                return LicenseValidation(
                    valid=False,
                    license_key=license_key,
                    product_name=license_obj.product_name,
                    customer_id=license_obj.customer_id,
                    features=license_obj.features,
                    installations_remaining=0,
                    error_message="Maximum installations exceeded"
                )
            
            # Update last validated timestamp
            license_obj.last_validated = datetime.utcnow().isoformat()
            self._save_license(license_obj)
            
            # Record usage
            if context:
                self._record_usage(license_obj, context)
            
            return LicenseValidation(
                valid=True,
                license_key=license_key,
                product_name=license_obj.product_name,
                customer_id=license_obj.customer_id,
                features=license_obj.features,
                expires_at=license_obj.expiration_date,
                usage_remaining=-1 if license_obj.max_users == -1 else license_obj.max_users - license_obj.usage_count,
                installations_remaining=installations_remaining,
                status=license_obj.status.value
            )
            
        except Exception as e:
            logger.error(f"Failed to validate license {license_key}: {e}")
            return LicenseValidation(
                valid=False,
                license_key=license_key,
                product_name="error",
                customer_id="error",
                features=[],
                error_message=str(e)
            )

    def activate_license(self, license_key: str, activation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Activate license for specific installation"""
        try:
            license_obj = self.licenses.get(license_key)
            if not license_obj:
                raise ValueError(f"License key {license_key} not found")
            
            # Validate license can be activated
            validation = self.validate_license(license_key, {'new_installation': True})
            if not validation.valid:
                raise ValueError(validation.error_message)
            
            # Record installation
            installation_id = str(uuid.uuid4())
            license_obj.installation_count += 1
            license_obj.metadata.setdefault('installations', []).append({
                'installation_id': installation_id,
                'machine_id': activation_data.get('machine_id'),
                'hostname': activation_data.get('hostname'),
                'os': activation_data.get('os'),
                'activated_at': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat()
            })
            
            self._save_license(license_obj)
            
            # Generate activation token
            activation_token = self._generate_activation_token(license_obj, installation_id)
            
            logger.info(f"Activated license {license_key} for installation {installation_id}")
            
            return {
                'activated': True,
                'installation_id': installation_id,
                'activation_token': activation_token,
                'license_info': asdict(validation),
                'installations_remaining': license_obj.max_installations - license_obj.installation_count
            }
            
        except Exception as e:
            logger.error(f"Failed to activate license {license_key}: {e}")
            raise

    def deactivate_license(self, license_key: str, installation_id: str) -> Dict[str, Any]:
        """Deactivate license for specific installation"""
        try:
            license_obj = self.licenses.get(license_key)
            if not license_obj:
                raise ValueError(f"License key {license_key} not found")
            
            # Find and remove installation
            installations = license_obj.metadata.get('installations', [])
            installation = None
            
            for i, inst in enumerate(installations):
                if inst.get('installation_id') == installation_id:
                    installation = installations.pop(i)
                    license_obj.installation_count -= 1
                    break
            
            if not installation:
                raise ValueError(f"Installation {installation_id} not found")
            
            self._save_license(license_obj)
            
            logger.info(f"Deactivated license {license_key} for installation {installation_id}")
            
            return {
                'deactivated': True,
                'installation_id': installation_id,
                'installations_remaining': license_obj.max_installations - license_obj.installation_count
            }
            
        except Exception as e:
            logger.error(f"Failed to deactivate license {license_key}: {e}")
            raise

    def renew_license(self, license_key: str, renewal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Renew expired or expiring license"""
        try:
            license_obj = self.licenses.get(license_key)
            if not license_obj:
                raise ValueError(f"License key {license_key} not found")
            
            # Calculate new expiration date
            if renewal_data.get('period_months'):
                months = renewal_data['period_months']
                if license_obj.expiration_date:
                    current_expiration = datetime.fromisoformat(license_obj.expiration_date.replace('Z', '+00:00'))
                    new_expiration = current_expiration + timedelta(days=months*30)
                else:
                    new_expiration = datetime.utcnow() + timedelta(days=months*30)
                
                license_obj.expiration_date = new_expiration.isoformat()
            
            # Update status if expired
            if license_obj.status == LicenseStatus.EXPIRED:
                license_obj.status = LicenseStatus.ACTIVE
            
            # Update features if provided
            if 'features' in renewal_data:
                license_obj.features = renewal_data['features']
            
            # Update limits if provided
            if 'max_users' in renewal_data:
                license_obj.max_users = renewal_data['max_users']
            
            if 'max_installations' in renewal_data:
                license_obj.max_installations = renewal_data['max_installations']
            
            self._save_license(license_obj)
            
            logger.info(f"Renewed license {license_key} until {license_obj.expiration_date}")
            
            return {
                'renewed': True,
                'license_key': license_key,
                'new_expiration': license_obj.expiration_date,
                'updated_features': license_obj.features,
                'renewal_document': self._generate_renewal_document(license_obj, renewal_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to renew license {license_key}: {e}")
            raise

    def revoke_license(self, license_key: str, reason: str = None) -> Dict[str, Any]:
        """Revoke license permanently"""
        try:
            license_obj = self.licenses.get(license_key)
            if not license_obj:
                raise ValueError(f"License key {license_key} not found")
            
            license_obj.status = LicenseStatus.REVOKED
            license_obj.metadata['revoked_at'] = datetime.utcnow().isoformat()
            license_obj.metadata['revocation_reason'] = reason or "Administrative action"
            
            self._save_license(license_obj)
            
            logger.info(f"Revoked license {license_key}: {reason}")
            
            return {
                'revoked': True,
                'license_key': license_key,
                'revoked_at': license_obj.metadata['revoked_at'],
                'reason': license_obj.metadata['revocation_reason']
            }
            
        except Exception as e:
            logger.error(f"Failed to revoke license {license_key}: {e}")
            raise

    def list_licenses(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """List licenses with optional filtering"""
        try:
            licenses = []
            
            for license_obj in self.licenses.values():
                # Apply filters
                if filters:
                    if 'customer_id' in filters and license_obj.customer_id != filters['customer_id']:
                        continue
                    if 'product_name' in filters and license_obj.product_name != filters['product_name']:
                        continue
                    if 'license_type' in filters and license_obj.license_type.value != filters['license_type']:
                        continue
                    if 'status' in filters and license_obj.status.value != filters['status']:
                        continue
                
                license_info = asdict(license_obj)
                
                # Add computed fields
                license_info['days_until_expiration'] = self._days_until_expiration(license_obj)
                license_info['usage_percentage'] = self._calculate_usage_percentage(license_obj)
                license_info['revenue_generated'] = self._calculate_license_revenue(license_obj)
                
                licenses.append(license_info)
            
            # Sort by issued date (newest first)
            licenses.sort(key=lambda x: x['issued_date'], reverse=True)
            
            return licenses
            
        except Exception as e:
            logger.error(f"Failed to list licenses: {e}")
            return []

    def get_license_analytics(self) -> Dict[str, Any]:
        """Get licensing analytics and metrics"""
        try:
            total_licenses = len(self.licenses)
            
            # Status distribution
            status_distribution = {}
            type_distribution = {}
            
            active_licenses = 0
            expired_licenses = 0
            trial_licenses = 0
            revenue_total = 0
            
            for license_obj in self.licenses.values():
                status = license_obj.status.value
                status_distribution[status] = status_distribution.get(status, 0) + 1
                
                license_type = license_obj.license_type.value
                type_distribution[license_type] = type_distribution.get(license_type, 0) + 1
                
                if license_obj.status == LicenseStatus.ACTIVE:
                    active_licenses += 1
                elif license_obj.status == LicenseStatus.EXPIRED:
                    expired_licenses += 1
                
                if license_obj.license_type == LicenseType.TRIAL:
                    trial_licenses += 1
                
                revenue_total += self._calculate_license_revenue(license_obj)
            
            # Expiration analysis
            expiring_soon = []
            for license_obj in self.licenses.values():
                days_until = self._days_until_expiration(license_obj)
                if 0 < days_until <= 30:  # Within 30 days
                    expiring_soon.append({
                        'license_key': license_obj.license_key,
                        'customer_name': license_obj.customer_name,
                        'product_name': license_obj.product_name,
                        'days_until_expiration': days_until
                    })
            
            return {
                'summary': {
                    'total_licenses': total_licenses,
                    'active_licenses': active_licenses,
                    'expired_licenses': expired_licenses,
                    'trial_licenses': trial_licenses,
                    'total_revenue': revenue_total
                },
                'distribution': {
                    'by_status': status_distribution,
                    'by_type': type_distribution
                },
                'expiring_soon': expiring_soon,
                'usage_metrics': self._get_usage_metrics(),
                'conversion_rates': self._calculate_conversion_rates()
            }
            
        except Exception as e:
            logger.error(f"Failed to get license analytics: {e}")
            return {}

    def create_license_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create license agreement template"""
        try:
            template_id = str(uuid.uuid4())
            
            template = LicenseTemplate(
                id=template_id,
                name=template_data['name'],
                license_type=template_data['license_type'],
                template_text=template_data['template_text'],
                variables=template_data.get('variables', []),
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
            self.templates[template_id] = template
            self._save_template(template)
            
            logger.info(f"Created license template {template_id}: {template.name}")
            
            return {
                'template_id': template_id,
                'template': asdict(template)
            }
            
        except Exception as e:
            logger.error(f"Failed to create license template: {e}")
            raise

    def generate_from_template(self, template_id: str, variables: Dict[str, str]) -> Dict[str, Any]:
        """Generate license document from template"""
        try:
            template = self.templates.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Replace variables in template
            license_text = template.template_text
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                license_text = license_text.replace(placeholder, var_value)
            
            return {
                'template_id': template_id,
                'generated_text': license_text,
                'variables_used': variables,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate from template {template_id}: {e}")
            raise

    def _generate_license_key(self, license_data: Dict[str, Any]) -> str:
        """Generate unique license key"""
        # Create unique identifier
        unique_data = f"{license_data['customer_id']}{license_data['product_name']}{datetime.utcnow().timestamp()}"
        hash_object = hashlib.sha256(unique_data.encode())
        hash_hex = hash_object.hexdigest()[:16].upper()
        
        # Format as license key (XXXX-XXXX-XXXX-XXXX)
        license_key = f"{hash_hex[:4]}-{hash_hex[4:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}"
        
        return license_key

    def _generate_activation_token(self, license_obj: License, installation_id: str) -> str:
        """Generate encrypted activation token"""
        token_data = {
            'license_key': license_obj.license_key,
            'installation_id': installation_id,
            'customer_id': license_obj.customer_id,
            'expires_at': license_obj.expiration_date,
            'issued_at': datetime.utcnow().isoformat()
        }
        
        token_json = json.dumps(token_data)
        encrypted_token = self.cipher.encrypt(token_json.encode())
        
        return base64.b64encode(encrypted_token).decode()

    def _record_usage(self, license_obj: License, context: Dict[str, Any]):
        """Record license usage"""
        try:
            usage_id = str(uuid.uuid4())
            
            usage = LicenseUsage(
                id=usage_id,
                license_key=license_obj.license_key,
                customer_id=license_obj.customer_id,
                product_name=license_obj.product_name,
                feature_used=context.get('feature', 'general'),
                timestamp=datetime.utcnow().isoformat(),
                ip_address=context.get('ip_address'),
                user_agent=context.get('user_agent'),
                session_id=context.get('session_id')
            )
            
            self.usage_records[usage_id] = usage
            self._save_usage_record(usage)
            
            # Update license usage count
            license_obj.usage_count += 1
            self._save_license(license_obj)
            
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")

    def _days_until_expiration(self, license_obj: License) -> int:
        """Calculate days until license expiration"""
        if not license_obj.expiration_date:
            return -1  # Perpetual license
        
        expiration = datetime.fromisoformat(license_obj.expiration_date.replace('Z', '+00:00'))
        days = (expiration - datetime.utcnow()).days
        
        return max(days, 0)

    def _calculate_usage_percentage(self, license_obj: License) -> float:
        """Calculate usage percentage"""
        if license_obj.max_users == -1:  # Unlimited
            return 0.0
        
        return (license_obj.usage_count / max(license_obj.max_users, 1)) * 100

    def _calculate_license_revenue(self, license_obj: License) -> float:
        """Calculate revenue from license"""
        # This would integrate with billing system
        base_prices = {
            LicenseType.TRIAL: 0,
            LicenseType.DEVELOPER: 99,
            LicenseType.ENTERPRISE: 999,
            LicenseType.ACADEMIC: 49
        }
        
        return base_prices.get(license_obj.license_type, 299)

    def _get_usage_metrics(self) -> Dict[str, Any]:
        """Get usage analytics"""
        total_usage = len(self.usage_records)
        
        # Feature usage distribution
        feature_usage = {}
        for usage in self.usage_records.values():
            feature = usage.feature_used
            feature_usage[feature] = feature_usage.get(feature, 0) + 1
        
        return {
            'total_usage_events': total_usage,
            'feature_usage_distribution': feature_usage,
            'average_usage_per_license': total_usage / max(len(self.licenses), 1)
        }

    def _calculate_conversion_rates(self) -> Dict[str, float]:
        """Calculate trial to paid conversion rates"""
        trial_count = 0
        converted_count = 0
        
        for license_obj in self.licenses.values():
            if license_obj.license_type == LicenseType.TRIAL:
                trial_count += 1
                # Check if customer has paid license
                customer_licenses = [
                    lic for lic in self.licenses.values()
                    if lic.customer_id == license_obj.customer_id and lic.license_type != LicenseType.TRIAL
                ]
                if customer_licenses:
                    converted_count += 1
        
        conversion_rate = (converted_count / max(trial_count, 1)) * 100
        
        return {
            'trial_to_paid_rate': conversion_rate,
            'trial_licenses': trial_count,
            'converted_licenses': converted_count
        }

    def _generate_license_document(self, license_obj: License) -> Dict[str, str]:
        """Generate license agreement document"""
        return {
            'title': f'Software License Agreement - {license_obj.product_name}',
            'license_key': license_obj.license_key,
            'customer': license_obj.customer_name,
            'type': license_obj.license_type.value,
            'issued_date': license_obj.issued_date,
            'expiration_date': license_obj.expiration_date,
            'features': ', '.join(license_obj.features),
            'terms': self._get_license_terms(license_obj)
        }

    def _get_license_terms(self, license_obj: License) -> str:
        """Get license terms based on license type"""
        terms_templates = {
            LicenseType.TRIAL: "This is a trial license valid for evaluation purposes only.",
            LicenseType.DEVELOPER: "This license is for development and testing purposes.",
            LicenseType.ENTERPRISE: "This license grants enterprise usage rights.",
            LicenseType.ACADEMIC: "This license is for academic and educational use only."
        }
        
        return terms_templates.get(license_obj.license_type, "Standard commercial license terms apply.")

    def _generate_renewal_document(self, license_obj: License, renewal_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate license renewal document"""
        return {
            'title': f'License Renewal - {license_obj.product_name}',
            'license_key': license_obj.license_key,
            'renewed_date': datetime.utcnow().isoformat(),
            'new_expiration': license_obj.expiration_date,
            'renewal_terms': renewal_data
        }

    def _get_installation_instructions(self, license_obj: License) -> List[str]:
        """Get installation instructions for license"""
        return [
            f"Download {license_obj.product_name} from the provided link",
            f"Run the installer and enter license key: {license_obj.license_key}",
            "Complete the activation process",
            "Begin using the software"
        ]

    def _get_download_links(self, license_obj: License) -> Dict[str, str]:
        """Get download links for licensed software"""
        return {
            'windows': f'https://downloads.activelog.com/{license_obj.product_name}/windows',
            'mac': f'https://downloads.activelog.com/{license_obj.product_name}/mac',
            'linux': f'https://downloads.activelog.com/{license_obj.product_name}/linux'
        }

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for license tokens"""
        key_file = Path("/home/activeloguser/activelog/data/legal-framework/license_key.key")
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            return key

    def _init_templates(self):
        """Initialize default license templates"""
        default_templates = [
            {
                'name': 'Standard Software License',
                'license_type': 'commercial',
                'template_text': '''SOFTWARE LICENSE AGREEMENT

This Software License Agreement ("Agreement") is entered into between {{licensor_name}} ("Licensor") and {{customer_name}} ("Licensee").

1. GRANT OF LICENSE
Licensor hereby grants to Licensee a {{license_type}} license to use {{product_name}}.

2. RESTRICTIONS
- Maximum {{max_users}} concurrent users
- Maximum {{max_installations}} installations
- Valid until {{expiration_date}}

3. SUPPORT AND MAINTENANCE
{{support_terms}}

By using this software, you agree to these terms.''',
                'variables': ['licensor_name', 'customer_name', 'license_type', 'product_name', 'max_users', 'max_installations', 'expiration_date', 'support_terms']
            }
        ]
        
        for template_data in default_templates:
            if not any(t.name == template_data['name'] for t in self.templates.values()):
                self.create_license_template(template_data)

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    license_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_records (
                    id TEXT PRIMARY KEY,
                    usage_data TEXT NOT NULL,
                    timestamp TEXT,
                    license_key TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS license_templates (
                    id TEXT PRIMARY KEY,
                    template_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_license ON usage_records(license_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize license database: {e}")
            raise

    def _load_licenses(self):
        """Load licenses from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Load licenses
            cursor.execute("SELECT license_data FROM licenses")
            for row in cursor.fetchall():
                license_data = json.loads(row[0])
                license_obj = License(**license_data)
                self.licenses[license_obj.license_key] = license_obj
            
            # Load usage records
            cursor.execute("SELECT usage_data FROM usage_records")
            for row in cursor.fetchall():
                usage_data = json.loads(row[0])
                usage = LicenseUsage(**usage_data)
                self.usage_records[usage.id] = usage
            
            # Load templates
            cursor.execute("SELECT template_data FROM license_templates")
            for row in cursor.fetchall():
                template_data = json.loads(row[0])
                template = LicenseTemplate(**template_data)
                self.templates[template.id] = template
            
            conn.close()
            logger.info(f"Loaded {len(self.licenses)} licenses from database")
            
        except Exception as e:
            logger.error(f"Failed to load licenses: {e}")

    def _save_license(self, license_obj: License):
        """Save license to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO licenses 
                (license_key, license_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                license_obj.license_key,
                json.dumps(asdict(license_obj)),
                license_obj.issued_date,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save license {license_obj.license_key}: {e}")

    def _save_usage_record(self, usage: LicenseUsage):
        """Save usage record to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO usage_records 
                (id, usage_data, timestamp, license_key)
                VALUES (?, ?, ?, ?)
            """, (
                usage.id,
                json.dumps(asdict(usage)),
                usage.timestamp,
                usage.license_key
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save usage record {usage.id}: {e}")

    def _save_template(self, template: LicenseTemplate):
        """Save template to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO license_templates 
                (id, template_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                template.id,
                json.dumps(asdict(template)),
                template.created_at,
                template.updated_at
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save template {template.id}: {e}")