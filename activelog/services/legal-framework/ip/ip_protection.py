#!/usr/bin/env python3
"""
Intellectual Property Protection Manager
Provides comprehensive IP protection, registration, and management services
"""

import json
import uuid
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import sqlite3
from enum import Enum

logger = logging.getLogger(__name__)


class IPAssetType(Enum):
    COPYRIGHT = "copyright"
    TRADEMARK = "trademark"
    PATENT = "patent"
    TRADE_SECRET = "trade_secret"
    SOFTWARE = "software"
    BRAND = "brand"
    DOMAIN = "domain"
    DESIGN = "design"


class IPStatus(Enum):
    DRAFT = "draft"
    REGISTERED = "registered"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ABANDONED = "abandoned"


@dataclass
class IPAsset:
    """Intellectual property asset"""
    id: str
    name: str
    asset_type: IPAssetType
    description: str
    owner: str
    status: IPStatus
    created_at: str
    registration_date: Optional[str] = None
    expiration_date: Optional[str] = None
    registration_number: Optional[str] = None
    jurisdiction: str = "US"
    classification: Optional[str] = None
    priority_date: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if isinstance(self.asset_type, str):
            self.asset_type = IPAssetType(self.asset_type)
        if isinstance(self.status, str):
            self.status = IPStatus(self.status)
        if self.metadata is None:
            self.metadata = {}


@dataclass
class IPProtectionPlan:
    """IP protection strategy plan"""
    id: str
    asset_id: str
    protection_type: str
    strategy: List[str]
    timeline: Dict[str, str]
    cost_estimate: float
    priority: int
    created_at: str
    status: str = "draft"


@dataclass
class IPLicense:
    """IP licensing agreement"""
    id: str
    asset_id: str
    licensee: str
    license_type: str  # exclusive, non-exclusive, sole
    territory: str
    duration: int  # months
    royalty_rate: float
    minimum_guarantee: float
    created_at: str
    signed_at: Optional[str] = None
    status: str = "draft"


class IPProtectionManager:
    """Manages intellectual property protection and registration"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = Path("/home/activeloguser/activelog/data/legal-framework/ip.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.assets = {}  # asset_id -> IPAsset
        self.protection_plans = {}  # plan_id -> IPProtectionPlan
        self.licenses = {}  # license_id -> IPLicense
        
        self._init_database()
        self._load_assets()
        
        logger.info("IP Protection Manager initialized")

    def protect_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Protect an intellectual property asset"""
        try:
            # Create IP asset
            asset_id = str(uuid.uuid4())
            
            asset = IPAsset(
                id=asset_id,
                name=asset_data['name'],
                asset_type=IPAssetType(asset_data['asset_type']),
                description=asset_data['description'],
                owner=asset_data['owner'],
                status=IPStatus.DRAFT,
                created_at=datetime.utcnow().isoformat(),
                jurisdiction=asset_data.get('jurisdiction', 'US'),
                classification=asset_data.get('classification'),
                metadata=asset_data.get('metadata', {})
            )
            
            # Store asset
            self.assets[asset_id] = asset
            self._save_asset(asset)
            
            # Generate protection plan
            protection_plan = self._generate_protection_plan(asset)
            
            logger.info(f"Protected IP asset {asset_id}: {asset.name}")
            
            return {
                'asset_id': asset_id,
                'asset': asdict(asset),
                'protection_plan': asdict(protection_plan),
                'next_steps': self._get_next_steps(asset),
                'estimated_timeline': self._estimate_timeline(asset),
                'cost_estimate': self._estimate_costs(asset)
            }
            
        except Exception as e:
            logger.error(f"Failed to protect asset: {e}")
            raise

    def register_asset(self, asset_id: str, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register IP asset with authorities"""
        try:
            asset = self.assets.get(asset_id)
            if not asset:
                raise ValueError(f"Asset {asset_id} not found")
            
            # Update registration information
            asset.status = IPStatus.PENDING
            asset.registration_number = registration_data.get('application_number')
            asset.priority_date = registration_data.get('priority_date')
            
            # Calculate expiration based on asset type
            if asset.asset_type == IPAssetType.COPYRIGHT:
                # Copyright lasts 70 years after author's death or 95 years for corporate
                expiration = datetime.utcnow() + timedelta(days=95*365)
            elif asset.asset_type == IPAssetType.TRADEMARK:
                # Trademark registration lasts 10 years, renewable
                expiration = datetime.utcnow() + timedelta(days=10*365)
            elif asset.asset_type == IPAssetType.PATENT:
                # Utility patents last 20 years from filing date
                expiration = datetime.utcnow() + timedelta(days=20*365)
            else:
                expiration = datetime.utcnow() + timedelta(days=10*365)
            
            asset.expiration_date = expiration.isoformat()
            
            self._save_asset(asset)
            
            # Create registration record
            registration = {
                'asset_id': asset_id,
                'registration_number': asset.registration_number,
                'filing_date': datetime.utcnow().isoformat(),
                'status': 'pending',
                'jurisdiction': asset.jurisdiction,
                'fees_paid': registration_data.get('fees', 0)
            }
            
            logger.info(f"Registered IP asset {asset_id} with number {asset.registration_number}")
            
            return {
                'success': True,
                'registration': registration,
                'next_review_date': (datetime.utcnow() + timedelta(days=90)).isoformat(),
                'maintenance_schedule': self._get_maintenance_schedule(asset)
            }
            
        except Exception as e:
            logger.error(f"Failed to register asset {asset_id}: {e}")
            raise

    def create_license(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create IP license agreement"""
        try:
            license_id = str(uuid.uuid4())
            
            # Validate asset exists
            asset_id = license_data['asset_id']
            if asset_id not in self.assets:
                raise ValueError(f"Asset {asset_id} not found")
            
            license_agreement = IPLicense(
                id=license_id,
                asset_id=asset_id,
                licensee=license_data['licensee'],
                license_type=license_data.get('license_type', 'non-exclusive'),
                territory=license_data.get('territory', 'worldwide'),
                duration=license_data.get('duration', 12),
                royalty_rate=license_data.get('royalty_rate', 0.05),
                minimum_guarantee=license_data.get('minimum_guarantee', 0),
                created_at=datetime.utcnow().isoformat()
            )
            
            self.licenses[license_id] = license_agreement
            self._save_license(license_agreement)
            
            # Generate license document
            license_document = self._generate_license_document(license_agreement)
            
            logger.info(f"Created IP license {license_id} for asset {asset_id}")
            
            return {
                'license_id': license_id,
                'license': asdict(license_agreement),
                'document': license_document,
                'terms': self._generate_license_terms(license_agreement)
            }
            
        except Exception as e:
            logger.error(f"Failed to create license: {e}")
            raise

    def search_prior_art(self, search_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for prior art and existing IP"""
        try:
            query = search_data.get('query', '')
            asset_type = search_data.get('asset_type', 'patent')
            jurisdiction = search_data.get('jurisdiction', 'US')
            
            # Search internal assets
            internal_results = self._search_internal_assets(query, asset_type)
            
            # Mock external search (in production would use patent databases)
            external_results = self._mock_external_search(query, asset_type, jurisdiction)
            
            # Analyze conflicts
            conflicts = self._analyze_conflicts(search_data, internal_results + external_results)
            
            return {
                'query': query,
                'total_results': len(internal_results) + len(external_results),
                'internal_results': internal_results,
                'external_results': external_results,
                'potential_conflicts': conflicts,
                'recommendations': self._get_prior_art_recommendations(conflicts),
                'search_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to search prior art: {e}")
            raise

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get IP asset details"""
        try:
            asset = self.assets.get(asset_id)
            if not asset:
                return None
            
            # Get related licenses
            related_licenses = [
                asdict(lic) for lic in self.licenses.values() 
                if lic.asset_id == asset_id
            ]
            
            # Get protection plan
            protection_plan = None
            for plan in self.protection_plans.values():
                if plan.asset_id == asset_id:
                    protection_plan = asdict(plan)
                    break
            
            # Calculate value metrics
            value_metrics = self._calculate_asset_value(asset)
            
            return {
                'asset': asdict(asset),
                'licenses': related_licenses,
                'protection_plan': protection_plan,
                'value_metrics': value_metrics,
                'maintenance_status': self._get_maintenance_status(asset),
                'renewal_dates': self._get_renewal_dates(asset)
            }
            
        except Exception as e:
            logger.error(f"Failed to get asset {asset_id}: {e}")
            return None

    def list_assets(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """List IP assets with optional filtering"""
        try:
            assets = []
            
            for asset in self.assets.values():
                # Apply filters
                if filters:
                    if 'asset_type' in filters and asset.asset_type.value != filters['asset_type']:
                        continue
                    if 'status' in filters and asset.status.value != filters['status']:
                        continue
                    if 'owner' in filters and asset.owner != filters['owner']:
                        continue
                
                asset_info = asdict(asset)
                
                # Add summary information
                asset_info['license_count'] = len([
                    lic for lic in self.licenses.values() 
                    if lic.asset_id == asset.id
                ])
                
                asset_info['revenue_generated'] = self._calculate_asset_revenue(asset.id)
                asset_info['days_until_renewal'] = self._days_until_renewal(asset)
                
                assets.append(asset_info)
            
            # Sort by creation date (newest first)
            assets.sort(key=lambda x: x['created_at'], reverse=True)
            
            return assets
            
        except Exception as e:
            logger.error(f"Failed to list assets: {e}")
            return []

    def get_portfolio_analytics(self) -> Dict[str, Any]:
        """Get IP portfolio analytics"""
        try:
            total_assets = len(self.assets)
            
            # Asset type distribution
            type_distribution = {}
            status_distribution = {}
            
            for asset in self.assets.values():
                asset_type = asset.asset_type.value
                type_distribution[asset_type] = type_distribution.get(asset_type, 0) + 1
                
                status = asset.status.value
                status_distribution[status] = status_distribution.get(status, 0) + 1
            
            # Calculate portfolio value
            total_value = sum(self._calculate_asset_value(asset)['estimated_value'] for asset in self.assets.values())
            
            # License analytics
            total_licenses = len(self.licenses)
            active_licenses = len([lic for lic in self.licenses.values() if lic.status == 'active'])
            
            # Upcoming renewals
            upcoming_renewals = []
            for asset in self.assets.values():
                days_until = self._days_until_renewal(asset)
                if 0 < days_until <= 90:  # Within 90 days
                    upcoming_renewals.append({
                        'asset_id': asset.id,
                        'name': asset.name,
                        'days_until_renewal': days_until,
                        'renewal_fee': self._estimate_renewal_fee(asset)
                    })
            
            return {
                'portfolio_summary': {
                    'total_assets': total_assets,
                    'total_value': total_value,
                    'total_licenses': total_licenses,
                    'active_licenses': active_licenses
                },
                'asset_distribution': {
                    'by_type': type_distribution,
                    'by_status': status_distribution
                },
                'upcoming_renewals': upcoming_renewals,
                'maintenance_costs': self._calculate_maintenance_costs(),
                'revenue_metrics': self._calculate_revenue_metrics()
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio analytics: {e}")
            return {}

    def _generate_protection_plan(self, asset: IPAsset) -> IPProtectionPlan:
        """Generate protection plan for IP asset"""
        plan_id = str(uuid.uuid4())
        
        # Determine strategy based on asset type
        if asset.asset_type == IPAssetType.SOFTWARE:
            strategy = [
                "File copyright registration",
                "Consider patent filing for novel algorithms",
                "Implement trade secret protection",
                "Register trademarks for product names"
            ]
            timeline = {
                "copyright_filing": "immediate",
                "patent_research": "30 days",
                "trade_secret_audit": "60 days",
                "trademark_search": "90 days"
            }
            cost_estimate = 15000
        elif asset.asset_type == IPAssetType.TRADEMARK:
            strategy = [
                "Conduct comprehensive trademark search",
                "File trademark application",
                "Monitor for infringement",
                "Consider international registration"
            ]
            timeline = {
                "trademark_search": "7 days",
                "application_filing": "30 days",
                "monitoring_setup": "60 days",
                "international_filing": "180 days"
            }
            cost_estimate = 5000
        elif asset.asset_type == IPAssetType.PATENT:
            strategy = [
                "Conduct prior art search",
                "Prepare patent application",
                "File patent application",
                "Prosecute application"
            ]
            timeline = {
                "prior_art_search": "14 days",
                "application_prep": "60 days",
                "filing": "90 days",
                "prosecution": "24 months"
            }
            cost_estimate = 25000
        else:
            strategy = ["Assess protection options", "Implement basic protection measures"]
            timeline = {"assessment": "30 days", "implementation": "60 days"}
            cost_estimate = 5000
        
        plan = IPProtectionPlan(
            id=plan_id,
            asset_id=asset.id,
            protection_type=asset.asset_type.value,
            strategy=strategy,
            timeline=timeline,
            cost_estimate=cost_estimate,
            priority=self._calculate_priority(asset),
            created_at=datetime.utcnow().isoformat()
        )
        
        self.protection_plans[plan_id] = plan
        self._save_protection_plan(plan)
        
        return plan

    def _calculate_priority(self, asset: IPAsset) -> int:
        """Calculate protection priority (1-10, 10 being highest)"""
        priority = 5  # Base priority
        
        # Increase priority for revenue-generating assets
        if asset.metadata.get('revenue_potential', 0) > 100000:
            priority += 2
        
        # Increase priority for core business assets
        if asset.metadata.get('business_critical', False):
            priority += 3
        
        # Increase priority for novel innovations
        if asset.asset_type == IPAssetType.PATENT:
            priority += 1
        
        return min(priority, 10)

    def _get_next_steps(self, asset: IPAsset) -> List[str]:
        """Get next steps for IP protection"""
        steps = []
        
        if asset.status == IPStatus.DRAFT:
            if asset.asset_type == IPAssetType.TRADEMARK:
                steps.extend([
                    "Conduct trademark search",
                    "Prepare trademark application",
                    "File with USPTO"
                ])
            elif asset.asset_type == IPAssetType.PATENT:
                steps.extend([
                    "Complete prior art search",
                    "Draft patent specification",
                    "File provisional or full application"
                ])
            elif asset.asset_type == IPAssetType.COPYRIGHT:
                steps.extend([
                    "Complete copyright registration forms",
                    "Submit deposit copies",
                    "Pay registration fee"
                ])
        
        return steps

    def _estimate_timeline(self, asset: IPAsset) -> Dict[str, str]:
        """Estimate protection timeline"""
        timelines = {
            IPAssetType.COPYRIGHT: {
                "registration": "3-6 months",
                "effective_date": "upon creation",
                "duration": "70+ years"
            },
            IPAssetType.TRADEMARK: {
                "search": "1-2 weeks",
                "application": "12-18 months",
                "registration": "18-24 months",
                "duration": "10 years (renewable)"
            },
            IPAssetType.PATENT: {
                "search": "2-4 weeks",
                "application": "2-4 months",
                "examination": "18-36 months",
                "grant": "24-48 months",
                "duration": "20 years"
            }
        }
        
        return timelines.get(asset.asset_type, {"protection": "varies"})

    def _estimate_costs(self, asset: IPAsset) -> Dict[str, float]:
        """Estimate protection costs"""
        cost_estimates = {
            IPAssetType.COPYRIGHT: {
                "registration_fee": 85,
                "attorney_fees": 1500,
                "total": 1585
            },
            IPAssetType.TRADEMARK: {
                "search": 500,
                "filing_fee": 350,
                "attorney_fees": 2500,
                "total": 3350
            },
            IPAssetType.PATENT: {
                "search": 2000,
                "filing_fees": 1600,
                "attorney_fees": 15000,
                "prosecution": 8000,
                "total": 26600
            }
        }
        
        return cost_estimates.get(asset.asset_type, {"total": 5000})

    def _search_internal_assets(self, query: str, asset_type: str) -> List[Dict[str, Any]]:
        """Search internal IP assets"""
        results = []
        
        for asset in self.assets.values():
            if asset_type != 'all' and asset.asset_type.value != asset_type:
                continue
            
            # Simple text matching
            if (query.lower() in asset.name.lower() or 
                query.lower() in asset.description.lower()):
                results.append({
                    'id': asset.id,
                    'name': asset.name,
                    'type': asset.asset_type.value,
                    'description': asset.description,
                    'status': asset.status.value,
                    'registration_date': asset.registration_date,
                    'source': 'internal'
                })
        
        return results

    def _mock_external_search(self, query: str, asset_type: str, jurisdiction: str) -> List[Dict[str, Any]]:
        """Mock external patent/trademark database search"""
        # In production, this would integrate with actual databases
        mock_results = [
            {
                'id': 'US123456789',
                'name': f"Related {asset_type} for {query}",
                'type': asset_type,
                'description': f"External {asset_type} related to {query}",
                'status': 'active',
                'registration_date': '2020-01-15',
                'source': f'{jurisdiction} Patent Office'
            }
        ]
        
        return mock_results if len(query) > 3 else []

    def _analyze_conflicts(self, search_data: Dict[str, Any], results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze potential IP conflicts"""
        conflicts = []
        
        for result in results:
            # Mock conflict analysis
            similarity_score = 0.3 if 'similar' in result['name'].lower() else 0.1
            
            if similarity_score > 0.2:
                conflicts.append({
                    'conflicting_asset': result,
                    'similarity_score': similarity_score,
                    'conflict_type': 'potential_infringement',
                    'severity': 'medium' if similarity_score > 0.5 else 'low',
                    'recommendation': 'Review for potential conflicts'
                })
        
        return conflicts

    def _get_prior_art_recommendations(self, conflicts: List[Dict[str, Any]]) -> List[str]:
        """Get recommendations based on prior art search"""
        recommendations = []
        
        if not conflicts:
            recommendations.append("No significant conflicts identified")
            recommendations.append("Proceed with filing application")
        else:
            recommendations.append("Review identified conflicts carefully")
            recommendations.append("Consider modifying claims to avoid conflicts")
            recommendations.append("Consult with IP attorney")
        
        return recommendations

    def _calculate_asset_value(self, asset: IPAsset) -> Dict[str, Any]:
        """Calculate estimated asset value"""
        base_value = 10000  # Base value
        
        # Adjust based on asset type
        type_multipliers = {
            IPAssetType.PATENT: 5.0,
            IPAssetType.TRADEMARK: 3.0,
            IPAssetType.COPYRIGHT: 2.0,
            IPAssetType.SOFTWARE: 4.0
        }
        
        multiplier = type_multipliers.get(asset.asset_type, 1.0)
        estimated_value = base_value * multiplier
        
        # Adjust for age and status
        if asset.status == IPStatus.REGISTERED:
            estimated_value *= 1.5
        
        return {
            'estimated_value': estimated_value,
            'valuation_method': 'cost_approach',
            'last_updated': datetime.utcnow().isoformat(),
            'factors': {
                'asset_type': asset.asset_type.value,
                'status': asset.status.value,
                'age': self._calculate_asset_age(asset)
            }
        }

    def _calculate_asset_age(self, asset: IPAsset) -> int:
        """Calculate asset age in days"""
        created = datetime.fromisoformat(asset.created_at.replace('Z', '+00:00'))
        return (datetime.utcnow() - created).days

    def _get_maintenance_status(self, asset: IPAsset) -> Dict[str, Any]:
        """Get maintenance status for asset"""
        return {
            'status': 'current',
            'next_maintenance_date': (datetime.utcnow() + timedelta(days=365)).isoformat(),
            'maintenance_fee': self._estimate_renewal_fee(asset),
            'requirements': self._get_maintenance_requirements(asset)
        }

    def _get_maintenance_requirements(self, asset: IPAsset) -> List[str]:
        """Get maintenance requirements for asset type"""
        requirements = {
            IPAssetType.PATENT: [
                "Pay maintenance fees at 3.5, 7.5, and 11.5 years",
                "Monitor for infringement",
                "Consider international filings"
            ],
            IPAssetType.TRADEMARK: [
                "File Declaration of Use between years 5-6",
                "Renew registration every 10 years",
                "Monitor for infringement"
            ],
            IPAssetType.COPYRIGHT: [
                "No maintenance required",
                "Monitor for infringement",
                "Maintain copyright notices"
            ]
        }
        
        return requirements.get(asset.asset_type, ["Monitor asset status"])

    def _get_renewal_dates(self, asset: IPAsset) -> Dict[str, str]:
        """Get important renewal dates"""
        renewal_dates = {}
        
        if asset.expiration_date:
            expiration = datetime.fromisoformat(asset.expiration_date.replace('Z', '+00:00'))
            
            if asset.asset_type == IPAssetType.PATENT:
                renewal_dates.update({
                    '3.5_year_fee': (expiration - timedelta(days=16.5*365)).isoformat(),
                    '7.5_year_fee': (expiration - timedelta(days=12.5*365)).isoformat(),
                    '11.5_year_fee': (expiration - timedelta(days=8.5*365)).isoformat()
                })
            elif asset.asset_type == IPAssetType.TRADEMARK:
                renewal_dates.update({
                    'section_8_filing': (expiration - timedelta(days=15*365)).isoformat(),
                    'renewal': expiration.isoformat()
                })
        
        return renewal_dates

    def _days_until_renewal(self, asset: IPAsset) -> int:
        """Calculate days until next renewal"""
        if not asset.expiration_date:
            return -1
        
        expiration = datetime.fromisoformat(asset.expiration_date.replace('Z', '+00:00'))
        return (expiration - datetime.utcnow()).days

    def _estimate_renewal_fee(self, asset: IPAsset) -> float:
        """Estimate renewal fee for asset"""
        renewal_fees = {
            IPAssetType.PATENT: 2000,
            IPAssetType.TRADEMARK: 500,
            IPAssetType.COPYRIGHT: 0
        }
        
        return renewal_fees.get(asset.asset_type, 500)

    def _calculate_asset_revenue(self, asset_id: str) -> float:
        """Calculate revenue generated by asset"""
        revenue = 0
        
        for license_agreement in self.licenses.values():
            if license_agreement.asset_id == asset_id and license_agreement.status == 'active':
                # Estimate based on royalty rate and minimum guarantee
                revenue += license_agreement.minimum_guarantee
        
        return revenue

    def _calculate_maintenance_costs(self) -> Dict[str, float]:
        """Calculate total maintenance costs"""
        total_cost = 0
        cost_breakdown = {}
        
        for asset in self.assets.values():
            fee = self._estimate_renewal_fee(asset)
            total_cost += fee
            
            asset_type = asset.asset_type.value
            cost_breakdown[asset_type] = cost_breakdown.get(asset_type, 0) + fee
        
        return {
            'total': total_cost,
            'breakdown': cost_breakdown
        }

    def _calculate_revenue_metrics(self) -> Dict[str, Any]:
        """Calculate revenue metrics for IP portfolio"""
        total_revenue = 0
        license_count = 0
        
        for license_agreement in self.licenses.values():
            if license_agreement.status == 'active':
                total_revenue += license_agreement.minimum_guarantee
                license_count += 1
        
        return {
            'total_revenue': total_revenue,
            'active_licenses': license_count,
            'average_per_license': total_revenue / max(license_count, 1),
            'roi': self._calculate_portfolio_roi()
        }

    def _calculate_portfolio_roi(self) -> float:
        """Calculate portfolio return on investment"""
        total_investment = sum(self._estimate_costs(asset)['total'] for asset in self.assets.values())
        total_revenue = sum(self._calculate_asset_revenue(asset.id) for asset in self.assets.values())
        
        return (total_revenue - total_investment) / max(total_investment, 1)

    def _generate_license_document(self, license_agreement: IPLicense) -> Dict[str, str]:
        """Generate license agreement document"""
        return {
            'title': f'IP License Agreement - {license_agreement.id}',
            'type': 'license_agreement',
            'format': 'legal_document',
            'sections': self._generate_license_terms(license_agreement)
        }

    def _generate_license_terms(self, license_agreement: IPLicense) -> Dict[str, str]:
        """Generate license terms and conditions"""
        asset = self.assets[license_agreement.asset_id]
        
        return {
            'parties': f"Licensor: {asset.owner}, Licensee: {license_agreement.licensee}",
            'grant': f"{license_agreement.license_type} license for {asset.name}",
            'territory': license_agreement.territory,
            'term': f"{license_agreement.duration} months",
            'royalty': f"{license_agreement.royalty_rate * 100}% royalty rate",
            'minimum_guarantee': f"${license_agreement.minimum_guarantee} minimum guarantee"
        }

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_assets (
                    id TEXT PRIMARY KEY,
                    asset_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS protection_plans (
                    id TEXT PRIMARY KEY,
                    plan_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_licenses (
                    id TEXT PRIMARY KEY,
                    license_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize IP database: {e}")
            raise

    def _load_assets(self):
        """Load assets from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Load assets
            cursor.execute("SELECT asset_data FROM ip_assets")
            for row in cursor.fetchall():
                asset_data = json.loads(row[0])
                asset = IPAsset(**asset_data)
                self.assets[asset.id] = asset
            
            # Load protection plans
            cursor.execute("SELECT plan_data FROM protection_plans")
            for row in cursor.fetchall():
                plan_data = json.loads(row[0])
                plan = IPProtectionPlan(**plan_data)
                self.protection_plans[plan.id] = plan
            
            # Load licenses
            cursor.execute("SELECT license_data FROM ip_licenses")
            for row in cursor.fetchall():
                license_data = json.loads(row[0])
                license_obj = IPLicense(**license_data)
                self.licenses[license_obj.id] = license_obj
            
            conn.close()
            logger.info(f"Loaded {len(self.assets)} IP assets from database")
            
        except Exception as e:
            logger.error(f"Failed to load IP assets: {e}")

    def _save_asset(self, asset: IPAsset):
        """Save asset to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO ip_assets 
                (id, asset_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                asset.id,
                json.dumps(asdict(asset)),
                asset.created_at,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save asset {asset.id}: {e}")

    def _save_protection_plan(self, plan: IPProtectionPlan):
        """Save protection plan to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO protection_plans 
                (id, plan_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                plan.id,
                json.dumps(asdict(plan)),
                plan.created_at,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save protection plan {plan.id}: {e}")

    def _save_license(self, license_obj: IPLicense):
        """Save license to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO ip_licenses 
                (id, license_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                license_obj.id,
                json.dumps(asdict(license_obj)),
                license_obj.created_at,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save license {license_obj.id}: {e}")