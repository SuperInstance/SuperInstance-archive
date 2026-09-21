#!/usr/bin/env python3
"""
Equity Management System
Comprehensive cap table and equity management platform

Features:
- Cap table management and modeling
- Equity grant tracking and vesting schedules
- Share class and preference stack management
- Waterfall analysis and distribution modeling
- Employee stock option pool management
- Convertible instrument tracking (SAFEs, convertible notes)
- Dilution analysis and scenario planning
- 409A valuation integration
- Transfer and secondary transaction management
- Board resolution and consent management
- Investor rights and information tracking
- Exit scenario modeling
- Tax optimization and planning
- Compliance and regulatory reporting
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
import asyncio
import logging
from pathlib import Path
import statistics
import random
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class SecurityType(str, Enum):
    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    STOCK_OPTION = "stock_option"
    RESTRICTED_STOCK = "restricted_stock"
    RSU = "rsu"
    WARRANT = "warrant"
    CONVERTIBLE_NOTE = "convertible_note"
    SAFE = "safe"

class VestingType(str, Enum):
    TIME_BASED = "time_based"
    MILESTONE_BASED = "milestone_based"
    PERFORMANCE_BASED = "performance_based"
    HYBRID = "hybrid"

class TransactionType(str, Enum):
    ISSUANCE = "issuance"
    EXERCISE = "exercise"
    TRANSFER = "transfer"
    CANCELLATION = "cancellation"
    CONVERSION = "conversion"
    REPURCHASE = "repurchase"

class LiquidationPreference(str, Enum):
    NON_PARTICIPATING = "non_participating"
    PARTICIPATING = "participating"
    PARTICIPATING_CAPPED = "participating_capped"

class ShareClass(BaseModel):
    id: str
    company_id: str
    class_name: str
    
    # Basic properties
    authorized_shares: int
    issued_shares: int = 0
    outstanding_shares: int = 0
    
    # Economic terms
    liquidation_preference: LiquidationPreference = LiquidationPreference.NON_PARTICIPATING
    liquidation_multiple: float = 1.0
    dividend_rate: float = 0.0  # Annual percentage
    participating_cap: Optional[float] = None  # Multiple of liquidation preference
    
    # Control and voting
    voting_rights_per_share: float = 1.0
    board_seats: int = 0
    protective_provisions: List[str] = []
    
    # Anti-dilution
    anti_dilution_protection: str = "none"  # none, weighted_average, full_ratchet
    
    # Conversion
    is_convertible: bool = False
    conversion_ratio: float = 1.0
    automatic_conversion_triggers: List[str] = []
    
    # Transfer restrictions
    right_of_first_refusal: bool = False
    co_sale_rights: bool = False
    drag_along_rights: bool = False
    tag_along_rights: bool = False
    
    created_at: datetime
    updated_at: datetime

class Stakeholder(BaseModel):
    id: str
    company_id: str
    
    # Identity
    name: str
    email: Optional[str] = None
    stakeholder_type: str  # founder, employee, investor, advisor, other
    
    # Employment/relationship
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    
    # Contact and address
    address: Dict[str, str] = {}
    tax_id: Optional[str] = None
    
    # Accreditation (for investors)
    is_accredited: bool = False
    accreditation_date: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime

class EquityGrant(BaseModel):
    id: str
    company_id: str
    stakeholder_id: str
    share_class_id: str
    
    # Grant details
    security_type: SecurityType
    granted_shares: int
    exercise_price: float = 0.0  # For options/warrants
    
    # Vesting
    vesting_type: VestingType = VestingType.TIME_BASED
    vesting_start_date: datetime
    vesting_cliff_months: int = 12
    vesting_duration_months: int = 48
    vested_shares: int = 0
    
    # Performance/milestone vesting (if applicable)
    performance_criteria: List[Dict[str, Any]] = []
    milestones: List[Dict[str, Any]] = []
    
    # Terms
    expiration_date: Optional[datetime] = None
    early_exercise_allowed: bool = False
    
    # Status
    is_active: bool = True
    fully_vested_date: Optional[datetime] = None
    
    # Documentation
    grant_agreement_url: Optional[str] = None
    board_approval_date: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime

class Transaction(BaseModel):
    id: str
    company_id: str
    
    # Transaction details
    transaction_type: TransactionType
    transaction_date: datetime
    shares: int
    price_per_share: float
    total_value: float
    
    # Parties involved
    from_stakeholder_id: Optional[str] = None
    to_stakeholder_id: str
    share_class_id: str
    equity_grant_id: Optional[str] = None  # If related to grant
    
    # Documentation
    transaction_documents: List[str] = []
    board_approval_required: bool = False
    board_approval_date: Optional[datetime] = None
    
    # Tax implications
    fair_market_value: Optional[float] = None
    tax_withholding: float = 0.0
    
    # Notes and context
    notes: str = ""
    
    created_at: datetime
    updated_at: datetime

class ConvertibleInstrument(BaseModel):
    id: str
    company_id: str
    stakeholder_id: str
    
    # Instrument details
    instrument_type: str  # safe, convertible_note, warrant
    principal_amount: float
    interest_rate: float = 0.0  # For convertible notes
    
    # Conversion terms
    valuation_cap: Optional[float] = None
    discount_rate: Optional[float] = None  # 0.20 = 20% discount
    conversion_trigger: str = "qualified_financing"
    
    # Timing
    issue_date: datetime
    maturity_date: Optional[datetime] = None
    
    # Status
    is_converted: bool = False
    conversion_date: Optional[datetime] = None
    converted_shares: int = 0
    converted_share_class_id: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

class CapTable(BaseModel):
    id: str
    company_id: str
    snapshot_date: datetime
    
    # Share class summaries
    share_classes: List[Dict[str, Any]] = []
    
    # Stakeholder holdings
    stakeholder_holdings: List[Dict[str, Any]] = []
    
    # Summary metrics
    total_outstanding_shares: int = 0
    total_authorized_shares: int = 0
    fully_diluted_shares: int = 0  # Including all options, convertibles
    
    # Option pool
    option_pool_size: int = 0
    option_pool_available: int = 0
    option_pool_percentage: float = 0.0
    
    # Valuation context
    company_valuation: Optional[float] = None
    price_per_share: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime

class WaterfallAnalysis(BaseModel):
    id: str
    company_id: str
    scenario_name: str
    
    # Exit assumptions
    exit_valuation: float
    exit_date: datetime
    
    # Distribution waterfall
    liquidation_waterfall: List[Dict[str, Any]] = []
    
    # Results by stakeholder
    distribution_results: List[Dict[str, Any]] = []
    
    # Summary metrics
    total_proceeds: float = 0
    investor_returns: Dict[str, float] = {}  # investor_id -> return multiple
    employee_payout: float = 0
    
    created_at: datetime

class EquityManagementSystem:
    def __init__(self):
        self.share_classes: Dict[str, ShareClass] = {}
        self.stakeholders: Dict[str, Stakeholder] = {}
        self.equity_grants: Dict[str, EquityGrant] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.convertible_instruments: Dict[str, ConvertibleInstrument] = {}
        self.cap_tables: Dict[str, CapTable] = {}
        self.waterfall_analyses: Dict[str, WaterfallAnalysis] = {}
        
        # Initialize default share classes
        self._initialize_default_share_classes()
    
    def _initialize_default_share_classes(self):
        """Initialize default share classes for demo"""
        
        # Common stock
        common_id = str(uuid.uuid4())
        common_class = ShareClass(
            id=common_id,
            company_id="default_company",
            class_name="Common Stock",
            authorized_shares=10000000,
            issued_shares=0,
            outstanding_shares=0,
            voting_rights_per_share=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.share_classes[common_id] = common_class
    
    async def create_share_class(self, company_id: str, class_data: Dict[str, Any]) -> ShareClass:
        """Create a new share class"""
        class_id = str(uuid.uuid4())
        
        share_class = ShareClass(
            id=class_id,
            company_id=company_id,
            class_name=class_data["class_name"],
            authorized_shares=class_data["authorized_shares"],
            liquidation_preference=LiquidationPreference(class_data.get("liquidation_preference", "non_participating")),
            liquidation_multiple=class_data.get("liquidation_multiple", 1.0),
            dividend_rate=class_data.get("dividend_rate", 0.0),
            participating_cap=class_data.get("participating_cap"),
            voting_rights_per_share=class_data.get("voting_rights_per_share", 1.0),
            board_seats=class_data.get("board_seats", 0),
            protective_provisions=class_data.get("protective_provisions", []),
            anti_dilution_protection=class_data.get("anti_dilution_protection", "none"),
            is_convertible=class_data.get("is_convertible", False),
            conversion_ratio=class_data.get("conversion_ratio", 1.0),
            automatic_conversion_triggers=class_data.get("automatic_conversion_triggers", []),
            right_of_first_refusal=class_data.get("right_of_first_refusal", False),
            co_sale_rights=class_data.get("co_sale_rights", False),
            drag_along_rights=class_data.get("drag_along_rights", False),
            tag_along_rights=class_data.get("tag_along_rights", False),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.share_classes[class_id] = share_class
        return share_class
    
    async def create_stakeholder(self, company_id: str, stakeholder_data: Dict[str, Any]) -> Stakeholder:
        """Create a new stakeholder"""
        stakeholder_id = str(uuid.uuid4())
        
        stakeholder = Stakeholder(
            id=stakeholder_id,
            company_id=company_id,
            name=stakeholder_data["name"],
            email=stakeholder_data.get("email"),
            stakeholder_type=stakeholder_data.get("stakeholder_type", "employee"),
            title=stakeholder_data.get("title"),
            start_date=stakeholder_data.get("start_date"),
            end_date=stakeholder_data.get("end_date"),
            is_active=stakeholder_data.get("is_active", True),
            address=stakeholder_data.get("address", {}),
            tax_id=stakeholder_data.get("tax_id"),
            is_accredited=stakeholder_data.get("is_accredited", False),
            accreditation_date=stakeholder_data.get("accreditation_date"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.stakeholders[stakeholder_id] = stakeholder
        return stakeholder
    
    async def create_equity_grant(self, grant_data: Dict[str, Any]) -> EquityGrant:
        """Create a new equity grant"""
        grant_id = str(uuid.uuid4())
        
        grant = EquityGrant(
            id=grant_id,
            company_id=grant_data["company_id"],
            stakeholder_id=grant_data["stakeholder_id"],
            share_class_id=grant_data["share_class_id"],
            security_type=SecurityType(grant_data["security_type"]),
            granted_shares=grant_data["granted_shares"],
            exercise_price=grant_data.get("exercise_price", 0.0),
            vesting_type=VestingType(grant_data.get("vesting_type", "time_based")),
            vesting_start_date=grant_data["vesting_start_date"],
            vesting_cliff_months=grant_data.get("vesting_cliff_months", 12),
            vesting_duration_months=grant_data.get("vesting_duration_months", 48),
            performance_criteria=grant_data.get("performance_criteria", []),
            milestones=grant_data.get("milestones", []),
            expiration_date=grant_data.get("expiration_date"),
            early_exercise_allowed=grant_data.get("early_exercise_allowed", False),
            grant_agreement_url=grant_data.get("grant_agreement_url"),
            board_approval_date=grant_data.get("board_approval_date"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.equity_grants[grant_id] = grant
        
        # If this is an immediate issuance (like founder stock), create transaction
        if grant.security_type in [SecurityType.COMMON_STOCK, SecurityType.PREFERRED_STOCK]:
            await self._create_issuance_transaction(grant)
        
        return grant
    
    async def _create_issuance_transaction(self, grant: EquityGrant):
        """Create issuance transaction for equity grant"""
        transaction_id = str(uuid.uuid4())
        
        transaction = Transaction(
            id=transaction_id,
            company_id=grant.company_id,
            transaction_type=TransactionType.ISSUANCE,
            transaction_date=datetime.now(),
            shares=grant.granted_shares,
            price_per_share=grant.exercise_price,
            total_value=grant.granted_shares * grant.exercise_price,
            to_stakeholder_id=grant.stakeholder_id,
            share_class_id=grant.share_class_id,
            equity_grant_id=grant.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.transactions[transaction_id] = transaction
        
        # Update share class outstanding shares
        share_class = self.share_classes.get(grant.share_class_id)
        if share_class:
            share_class.issued_shares += grant.granted_shares
            share_class.outstanding_shares += grant.granted_shares
            share_class.updated_at = datetime.now()
    
    async def calculate_vested_shares(self, grant_id: str, as_of_date: Optional[datetime] = None) -> int:
        """Calculate vested shares for an equity grant"""
        grant = self.equity_grants.get(grant_id)
        if not grant:
            return 0
        
        if as_of_date is None:
            as_of_date = datetime.now()
        
        if grant.vesting_type == VestingType.TIME_BASED:
            return await self._calculate_time_based_vesting(grant, as_of_date)
        elif grant.vesting_type == VestingType.MILESTONE_BASED:
            return await self._calculate_milestone_vesting(grant, as_of_date)
        elif grant.vesting_type == VestingType.PERFORMANCE_BASED:
            return await self._calculate_performance_vesting(grant, as_of_date)
        else:
            return grant.vested_shares  # Return current vested amount for other types
    
    async def _calculate_time_based_vesting(self, grant: EquityGrant, as_of_date: datetime) -> int:
        """Calculate time-based vesting"""
        
        # Check if we're before cliff
        cliff_date = grant.vesting_start_date + timedelta(days=30.44 * grant.vesting_cliff_months)  # 30.44 days per month average
        if as_of_date < cliff_date:
            return 0
        
        # Check if fully vested
        full_vest_date = grant.vesting_start_date + timedelta(days=30.44 * grant.vesting_duration_months)
        if as_of_date >= full_vest_date:
            return grant.granted_shares
        
        # Calculate proportional vesting
        days_from_start = (as_of_date - grant.vesting_start_date).days
        total_vesting_days = grant.vesting_duration_months * 30.44
        
        vesting_percentage = days_from_start / total_vesting_days
        vested_shares = int(grant.granted_shares * vesting_percentage)
        
        return min(vested_shares, grant.granted_shares)
    
    async def _calculate_milestone_vesting(self, grant: EquityGrant, as_of_date: datetime) -> int:
        """Calculate milestone-based vesting"""
        vested_shares = 0
        
        for milestone in grant.milestones:
            if milestone.get("completion_date") and milestone["completion_date"] <= as_of_date:
                vested_shares += milestone.get("shares", 0)
        
        return min(vested_shares, grant.granted_shares)
    
    async def _calculate_performance_vesting(self, grant: EquityGrant, as_of_date: datetime) -> int:
        """Calculate performance-based vesting"""
        # Simplified performance vesting calculation
        # In production, would evaluate actual performance criteria
        
        achieved_percentage = 0.0
        total_weight = 0.0
        
        for criterion in grant.performance_criteria:
            weight = criterion.get("weight", 1.0)
            achievement = criterion.get("achievement_percentage", 0.0)  # 0-1
            
            achieved_percentage += achievement * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_achievement = achieved_percentage / total_weight
            return int(grant.granted_shares * overall_achievement)
        
        return 0
    
    async def exercise_options(
        self, 
        grant_id: str, 
        shares_to_exercise: int, 
        exercise_data: Dict[str, Any]
    ) -> Transaction:
        """Exercise stock options"""
        
        grant = self.equity_grants.get(grant_id)
        if not grant:
            raise ValueError("Grant not found")
        
        if grant.security_type not in [SecurityType.STOCK_OPTION, SecurityType.WARRANT]:
            raise ValueError("Grant is not exercisable")
        
        # Check if shares are vested
        vested_shares = await self.calculate_vested_shares(grant_id)
        if shares_to_exercise > vested_shares:
            raise ValueError(f"Cannot exercise {shares_to_exercise} shares, only {vested_shares} are vested")
        
        # Create exercise transaction
        transaction_id = str(uuid.uuid4())
        
        transaction = Transaction(
            id=transaction_id,
            company_id=grant.company_id,
            transaction_type=TransactionType.EXERCISE,
            transaction_date=exercise_data.get("exercise_date", datetime.now()),
            shares=shares_to_exercise,
            price_per_share=grant.exercise_price,
            total_value=shares_to_exercise * grant.exercise_price,
            to_stakeholder_id=grant.stakeholder_id,
            share_class_id=grant.share_class_id,
            equity_grant_id=grant_id,
            fair_market_value=exercise_data.get("fair_market_value"),
            tax_withholding=exercise_data.get("tax_withholding", 0.0),
            notes=exercise_data.get("notes", ""),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.transactions[transaction_id] = transaction
        
        # Update share class outstanding shares
        share_class = self.share_classes.get(grant.share_class_id)
        if share_class:
            share_class.outstanding_shares += shares_to_exercise
            share_class.updated_at = datetime.now()
        
        # Update grant to reflect exercised shares
        grant.vested_shares = max(0, grant.vested_shares - shares_to_exercise)
        grant.updated_at = datetime.now()
        
        return transaction
    
    async def create_convertible_instrument(self, instrument_data: Dict[str, Any]) -> ConvertibleInstrument:
        """Create a new convertible instrument (SAFE, convertible note)"""
        instrument_id = str(uuid.uuid4())
        
        instrument = ConvertibleInstrument(
            id=instrument_id,
            company_id=instrument_data["company_id"],
            stakeholder_id=instrument_data["stakeholder_id"],
            instrument_type=instrument_data["instrument_type"],
            principal_amount=instrument_data["principal_amount"],
            interest_rate=instrument_data.get("interest_rate", 0.0),
            valuation_cap=instrument_data.get("valuation_cap"),
            discount_rate=instrument_data.get("discount_rate"),
            conversion_trigger=instrument_data.get("conversion_trigger", "qualified_financing"),
            issue_date=instrument_data.get("issue_date", datetime.now()),
            maturity_date=instrument_data.get("maturity_date"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.convertible_instruments[instrument_id] = instrument
        return instrument
    
    async def convert_instrument(
        self, 
        instrument_id: str, 
        conversion_data: Dict[str, Any]
    ) -> Transaction:
        """Convert a convertible instrument to equity"""
        
        instrument = self.convertible_instruments.get(instrument_id)
        if not instrument:
            raise ValueError("Instrument not found")
        
        if instrument.is_converted:
            raise ValueError("Instrument already converted")
        
        # Calculate conversion terms
        conversion_price = await self._calculate_conversion_price(instrument, conversion_data)
        shares_issued = int(instrument.principal_amount / conversion_price)
        
        # Create conversion transaction
        transaction_id = str(uuid.uuid4())
        
        transaction = Transaction(
            id=transaction_id,
            company_id=instrument.company_id,
            transaction_type=TransactionType.CONVERSION,
            transaction_date=conversion_data.get("conversion_date", datetime.now()),
            shares=shares_issued,
            price_per_share=conversion_price,
            total_value=instrument.principal_amount,
            to_stakeholder_id=instrument.stakeholder_id,
            share_class_id=conversion_data["target_share_class_id"],
            notes=f"Conversion of {instrument.instrument_type} - Principal: ${instrument.principal_amount:,.2f}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.transactions[transaction_id] = transaction
        
        # Update instrument status
        instrument.is_converted = True
        instrument.conversion_date = transaction.transaction_date
        instrument.converted_shares = shares_issued
        instrument.converted_share_class_id = conversion_data["target_share_class_id"]
        instrument.updated_at = datetime.now()
        
        # Update share class
        share_class = self.share_classes.get(conversion_data["target_share_class_id"])
        if share_class:
            share_class.issued_shares += shares_issued
            share_class.outstanding_shares += shares_issued
            share_class.updated_at = datetime.now()
        
        return transaction
    
    async def _calculate_conversion_price(
        self, 
        instrument: ConvertibleInstrument, 
        conversion_data: Dict[str, Any]
    ) -> float:
        """Calculate conversion price for convertible instrument"""
        
        financing_valuation = conversion_data.get("financing_valuation", 0)
        financing_price_per_share = conversion_data.get("financing_price_per_share", 0)
        
        if not financing_price_per_share:
            return 0
        
        conversion_price = financing_price_per_share
        
        # Apply valuation cap
        if instrument.valuation_cap and financing_valuation > instrument.valuation_cap:
            # Convert at valuation cap
            cap_price = instrument.valuation_cap / conversion_data.get("pre_money_shares", 1)
            conversion_price = min(conversion_price, cap_price)
        
        # Apply discount
        if instrument.discount_rate:
            discount_price = financing_price_per_share * (1 - instrument.discount_rate)
            conversion_price = min(conversion_price, discount_price)
        
        return max(conversion_price, 0.01)  # Minimum price protection
    
    async def generate_cap_table(self, company_id: str, as_of_date: Optional[datetime] = None) -> CapTable:
        """Generate current cap table"""
        
        if as_of_date is None:
            as_of_date = datetime.now()
        
        cap_table_id = str(uuid.uuid4())
        
        # Get all share classes for company
        company_share_classes = [sc for sc in self.share_classes.values() if sc.company_id == company_id]
        
        # Get all stakeholders for company
        company_stakeholders = [s for s in self.stakeholders.values() if s.company_id == company_id]
        
        # Calculate holdings for each stakeholder
        stakeholder_holdings = []
        
        for stakeholder in company_stakeholders:
            holdings = await self._calculate_stakeholder_holdings(stakeholder.id, as_of_date)
            if any(holding["shares"] > 0 for holding in holdings):
                stakeholder_holdings.append({
                    "stakeholder_id": stakeholder.id,
                    "stakeholder_name": stakeholder.name,
                    "stakeholder_type": stakeholder.stakeholder_type,
                    "holdings": holdings,
                    "total_shares": sum(holding["shares"] for holding in holdings),
                    "total_value": sum(holding["value"] for holding in holdings)
                })
        
        # Calculate totals
        total_outstanding = sum(sc.outstanding_shares for sc in company_share_classes)
        total_authorized = sum(sc.authorized_shares for sc in company_share_classes)
        
        # Calculate fully diluted (including options and convertibles)
        fully_diluted = total_outstanding
        
        # Add unexercised options
        company_grants = [g for g in self.equity_grants.values() if g.company_id == company_id and g.is_active]
        for grant in company_grants:
            if grant.security_type in [SecurityType.STOCK_OPTION, SecurityType.WARRANT]:
                vested_shares = await self.calculate_vested_shares(grant.id, as_of_date)
                fully_diluted += vested_shares
        
        # Add convertible instruments
        company_convertibles = [c for c in self.convertible_instruments.values() if c.company_id == company_id and not c.is_converted]
        for convertible in company_convertibles:
            # Estimate conversion shares (simplified)
            estimated_price = 1.00  # Would use latest 409A or financing price
            estimated_shares = int(convertible.principal_amount / estimated_price)
            fully_diluted += estimated_shares
        
        # Calculate option pool metrics
        option_grants = [g for g in company_grants if g.security_type == SecurityType.STOCK_OPTION]
        option_pool_allocated = sum(g.granted_shares for g in option_grants)
        option_pool_size = int(fully_diluted * 0.15)  # Assume 15% option pool
        option_pool_available = max(0, option_pool_size - option_pool_allocated)
        
        cap_table = CapTable(
            id=cap_table_id,
            company_id=company_id,
            snapshot_date=as_of_date,
            share_classes=[{
                "class_id": sc.id,
                "class_name": sc.class_name,
                "authorized": sc.authorized_shares,
                "issued": sc.issued_shares,
                "outstanding": sc.outstanding_shares
            } for sc in company_share_classes],
            stakeholder_holdings=stakeholder_holdings,
            total_outstanding_shares=total_outstanding,
            total_authorized_shares=total_authorized,
            fully_diluted_shares=fully_diluted,
            option_pool_size=option_pool_size,
            option_pool_available=option_pool_available,
            option_pool_percentage=(option_pool_size / fully_diluted * 100) if fully_diluted > 0 else 0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.cap_tables[cap_table_id] = cap_table
        return cap_table
    
    async def _calculate_stakeholder_holdings(self, stakeholder_id: str, as_of_date: datetime) -> List[Dict[str, Any]]:
        """Calculate holdings for a specific stakeholder"""
        holdings = []
        
        # Get all grants for stakeholder
        stakeholder_grants = [g for g in self.equity_grants.values() if g.stakeholder_id == stakeholder_id and g.is_active]
        
        for grant in stakeholder_grants:
            shares = 0
            
            if grant.security_type in [SecurityType.COMMON_STOCK, SecurityType.PREFERRED_STOCK]:
                # For direct stock grants, use granted shares
                shares = grant.granted_shares
            elif grant.security_type in [SecurityType.STOCK_OPTION, SecurityType.WARRANT]:
                # For options, use vested but not exercised shares
                vested_shares = await self.calculate_vested_shares(grant.id, as_of_date)
                
                # Subtract already exercised shares
                exercised_shares = sum(
                    t.shares for t in self.transactions.values()
                    if t.equity_grant_id == grant.id and t.transaction_type == TransactionType.EXERCISE
                )
                
                shares = max(0, vested_shares - exercised_shares)
            
            if shares > 0:
                holdings.append({
                    "grant_id": grant.id,
                    "security_type": grant.security_type.value,
                    "share_class_id": grant.share_class_id,
                    "shares": shares,
                    "exercise_price": grant.exercise_price,
                    "value": shares * 1.00  # Would use actual valuation
                })
        
        # Add shares from direct transactions (not related to grants)
        stakeholder_transactions = [
            t for t in self.transactions.values() 
            if t.to_stakeholder_id == stakeholder_id and t.equity_grant_id is None
        ]
        
        for transaction in stakeholder_transactions:
            if transaction.transaction_type in [TransactionType.ISSUANCE, TransactionType.TRANSFER]:
                holdings.append({
                    "transaction_id": transaction.id,
                    "security_type": "direct_purchase",
                    "share_class_id": transaction.share_class_id,
                    "shares": transaction.shares,
                    "exercise_price": 0,
                    "value": transaction.shares * 1.00
                })
        
        return holdings
    
    async def model_dilution_scenario(
        self, 
        company_id: str, 
        scenario_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Model dilution impact of new financing"""
        
        # Generate current cap table
        current_cap_table = await self.generate_cap_table(company_id)
        
        # Extract scenario parameters
        new_investment_amount = scenario_data["investment_amount"]
        pre_money_valuation = scenario_data["pre_money_valuation"]
        option_pool_increase = scenario_data.get("option_pool_increase", 0)
        
        # Calculate new shares to be issued
        post_money_valuation = pre_money_valuation + new_investment_amount
        price_per_share = pre_money_valuation / current_cap_table.fully_diluted_shares
        new_shares = int(new_investment_amount / price_per_share)
        
        # Calculate new fully diluted share count
        new_fully_diluted = current_cap_table.fully_diluted_shares + new_shares + option_pool_increase
        
        # Calculate dilution for each stakeholder
        dilution_analysis = []
        
        for holding in current_cap_table.stakeholder_holdings:
            current_shares = holding["total_shares"]
            current_ownership = (current_shares / current_cap_table.fully_diluted_shares) * 100
            new_ownership = (current_shares / new_fully_diluted) * 100
            dilution = current_ownership - new_ownership
            
            dilution_analysis.append({
                "stakeholder_name": holding["stakeholder_name"],
                "stakeholder_type": holding["stakeholder_type"],
                "current_shares": current_shares,
                "current_ownership": round(current_ownership, 2),
                "new_ownership": round(new_ownership, 2),
                "dilution_percentage": round(dilution, 2),
                "current_value": current_shares * price_per_share,
                "new_value": current_shares * (post_money_valuation / new_fully_diluted)
            })
        
        return {
            "scenario_name": scenario_data.get("name", "New Financing Scenario"),
            "investment_amount": new_investment_amount,
            "pre_money_valuation": pre_money_valuation,
            "post_money_valuation": post_money_valuation,
            "price_per_share": price_per_share,
            "new_shares_issued": new_shares,
            "current_fully_diluted": current_cap_table.fully_diluted_shares,
            "new_fully_diluted": new_fully_diluted,
            "dilution_analysis": dilution_analysis,
            "summary": {
                "total_dilution": round(((new_shares + option_pool_increase) / new_fully_diluted) * 100, 2),
                "investor_ownership": round((new_shares / new_fully_diluted) * 100, 2),
                "option_pool_impact": round((option_pool_increase / new_fully_diluted) * 100, 2)
            }
        }
    
    async def generate_waterfall_analysis(
        self, 
        company_id: str, 
        exit_valuation: float, 
        scenario_name: str = "Exit Scenario"
    ) -> WaterfallAnalysis:
        """Generate liquidation waterfall analysis"""
        
        analysis_id = str(uuid.uuid4())
        
        # Get current cap table
        cap_table = await self.generate_cap_table(company_id)
        
        # Get share classes sorted by liquidation preference
        company_share_classes = [sc for sc in self.share_classes.values() if sc.company_id == company_id]
        
        # Sort by liquidation preference (preferred first, then common)
        preferred_classes = [sc for sc in company_share_classes if sc.class_name.lower().startswith("preferred")]
        common_classes = [sc for sc in company_share_classes if sc.class_name.lower().startswith("common")]
        
        # Simple waterfall calculation
        remaining_proceeds = exit_valuation
        waterfall_steps = []
        distribution_results = []
        
        # Step 1: Liquidation preferences for preferred stock
        for share_class in preferred_classes:
            class_shares = share_class.outstanding_shares
            liquidation_amount = class_shares * share_class.liquidation_multiple * 1.00  # Assume $1 original price
            
            if remaining_proceeds >= liquidation_amount:
                waterfall_steps.append({
                    "step": f"{share_class.class_name} Liquidation Preference",
                    "amount": liquidation_amount,
                    "recipients": share_class.class_name
                })
                remaining_proceeds -= liquidation_amount
            else:
                waterfall_steps.append({
                    "step": f"{share_class.class_name} Liquidation Preference (Partial)",
                    "amount": remaining_proceeds,
                    "recipients": share_class.class_name
                })
                remaining_proceeds = 0
                break
        
        # Step 2: Distribute remaining proceeds pro-rata (if participating preferred)
        if remaining_proceeds > 0:
            total_participating_shares = sum(sc.outstanding_shares for sc in company_share_classes)
            
            waterfall_steps.append({
                "step": "Pro-rata distribution",
                "amount": remaining_proceeds,
                "recipients": "All shareholders pro-rata"
            })
        
        # Calculate distribution by stakeholder
        for holding in cap_table.stakeholder_holdings:
            stakeholder_payout = 0
            
            # Simplified calculation - would be more complex in practice
            total_shares = holding["total_shares"]
            pro_rata_share = (total_shares / cap_table.total_outstanding_shares) if cap_table.total_outstanding_shares > 0 else 0
            stakeholder_payout = exit_valuation * pro_rata_share
            
            distribution_results.append({
                "stakeholder_name": holding["stakeholder_name"],
                "stakeholder_type": holding["stakeholder_type"],
                "shares": total_shares,
                "ownership_percentage": (total_shares / cap_table.fully_diluted_shares) * 100,
                "payout": stakeholder_payout,
                "return_multiple": (stakeholder_payout / holding["total_value"]) if holding["total_value"] > 0 else 0
            })
        
        # Calculate summary metrics
        investor_returns = {}
        employee_payout = sum(
            result["payout"] for result in distribution_results 
            if result["stakeholder_type"] in ["employee", "founder"]
        )
        
        waterfall_analysis = WaterfallAnalysis(
            id=analysis_id,
            company_id=company_id,
            scenario_name=scenario_name,
            exit_valuation=exit_valuation,
            exit_date=datetime.now(),
            liquidation_waterfall=waterfall_steps,
            distribution_results=distribution_results,
            total_proceeds=exit_valuation,
            investor_returns=investor_returns,
            employee_payout=employee_payout,
            created_at=datetime.now()
        )
        
        self.waterfall_analyses[analysis_id] = waterfall_analysis
        return waterfall_analysis
    
    async def get_equity_dashboard(self, company_id: str) -> Dict[str, Any]:
        """Get comprehensive equity management dashboard"""
        
        # Generate current cap table
        cap_table = await self.generate_cap_table(company_id)
        
        # Get key metrics
        company_stakeholders = [s for s in self.stakeholders.values() if s.company_id == company_id]
        company_grants = [g for g in self.equity_grants.values() if g.company_id == company_id and g.is_active]
        
        # Vesting analysis
        total_unvested_options = 0
        vesting_schedule = []
        
        for grant in company_grants:
            if grant.security_type in [SecurityType.STOCK_OPTION]:
                vested = await self.calculate_vested_shares(grant.id)
                unvested = grant.granted_shares - vested
                total_unvested_options += unvested
                
                if unvested > 0:
                    # Calculate next vesting date (simplified)
                    next_vest_date = datetime.now() + timedelta(days=30)
                    monthly_vest = grant.granted_shares / grant.vesting_duration_months
                    
                    vesting_schedule.append({
                        "stakeholder_name": self.stakeholders.get(grant.stakeholder_id, {}).get("name", "Unknown"),
                        "next_vest_date": next_vest_date.isoformat(),
                        "shares_vesting": int(monthly_vest),
                        "remaining_unvested": unvested
                    })
        
        # Recent transactions
        recent_transactions = sorted(
            [t for t in self.transactions.values() if t.company_id == company_id],
            key=lambda x: x.created_at,
            reverse=True
        )[:10]
        
        transaction_summary = []
        for txn in recent_transactions:
            stakeholder_name = "Unknown"
            if txn.to_stakeholder_id:
                stakeholder = self.stakeholders.get(txn.to_stakeholder_id)
                if stakeholder:
                    stakeholder_name = stakeholder.name
            
            transaction_summary.append({
                "date": txn.transaction_date.isoformat(),
                "type": txn.transaction_type.value,
                "stakeholder": stakeholder_name,
                "shares": txn.shares,
                "value": txn.total_value
            })
        
        return {
            "company_id": company_id,
            "cap_table_summary": {
                "total_outstanding_shares": cap_table.total_outstanding_shares,
                "fully_diluted_shares": cap_table.fully_diluted_shares,
                "option_pool_percentage": cap_table.option_pool_percentage,
                "option_pool_available": cap_table.option_pool_available
            },
            "stakeholder_summary": {
                "total_stakeholders": len(company_stakeholders),
                "founders": len([s for s in company_stakeholders if s.stakeholder_type == "founder"]),
                "employees": len([s for s in company_stakeholders if s.stakeholder_type == "employee"]),
                "investors": len([s for s in company_stakeholders if s.stakeholder_type == "investor"]),
                "advisors": len([s for s in company_stakeholders if s.stakeholder_type == "advisor"])
            },
            "equity_grants": {
                "total_grants": len(company_grants),
                "active_options": len([g for g in company_grants if g.security_type == SecurityType.STOCK_OPTION]),
                "total_unvested_options": total_unvested_options
            },
            "ownership_breakdown": [
                {
                    "stakeholder_name": holding["stakeholder_name"],
                    "stakeholder_type": holding["stakeholder_type"],
                    "ownership_percentage": round((holding["total_shares"] / cap_table.fully_diluted_shares) * 100, 2),
                    "shares": holding["total_shares"]
                }
                for holding in cap_table.stakeholder_holdings
            ],
            "vesting_schedule": sorted(vesting_schedule, key=lambda x: x["next_vest_date"])[:10],
            "recent_transactions": transaction_summary,
            "generated_at": datetime.now().isoformat()
        }

# Global instance
equity_management_system = EquityManagementSystem()