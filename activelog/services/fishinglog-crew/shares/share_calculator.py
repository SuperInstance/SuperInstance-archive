"""
Crew Share Calculator System
Comprehensive calculation of crew shares, bonuses, and deductions for fishing trips
"""

import uuid
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import json

from ..roles.permissions import CrewRole, Permission, PermissionManager
from ..crew.crew_management import CrewManager

logger = logging.getLogger(__name__)


class ShareType(Enum):
    """Types of crew share systems"""
    EQUAL_SHARES = "equal_shares"  # All crew get equal shares
    ROLE_BASED = "role_based"      # Shares based on role hierarchy
    PERFORMANCE = "performance"    # Shares based on performance metrics
    HYBRID = "hybrid"             # Combination of role and performance
    CUSTOM = "custom"             # Custom allocation per trip


class DeductionType(Enum):
    """Types of deductions from crew shares"""
    FUEL = "fuel"
    ICE = "ice" 
    BAIT = "bait"
    FOOD = "food"
    GEAR_REPLACEMENT = "gear_replacement"
    REPAIRS = "repairs"
    INSURANCE = "insurance"
    HARBOR_FEES = "harbor_fees"
    MAINTENANCE = "maintenance"
    ADVANCE_PAYMENT = "advance_payment"
    TAXES = "taxes"
    UNION_DUES = "union_dues"
    SAFETY_EQUIPMENT = "safety_equipment"
    OTHER = "other"


class BonusType(Enum):
    """Types of bonuses for crew"""
    SAFETY_RECORD = "safety_record"
    FISH_HANDLING = "fish_handling"
    EQUIPMENT_CARE = "equipment_care"
    OVERTIME = "overtime"
    HAZARD_PAY = "hazard_pay"
    PERFORMANCE = "performance"
    LOYALTY = "loyalty"
    TRIP_LENGTH = "trip_length"
    WEATHER_CONDITIONS = "weather_conditions"
    CAPTAIN_DISCRETION = "captain_discretion"
    OTHER = "other"


class ExpenseCategory(Enum):
    """Categories of trip expenses"""
    OPERATIONAL = "operational"    # Direct operating costs
    MAINTENANCE = "maintenance"    # Vessel maintenance
    SAFETY = "safety"             # Safety equipment
    ADMINISTRATIVE = "administrative"  # Admin costs
    CREW_WELFARE = "crew_welfare"  # Crew food, accommodation


@dataclass
class TripEarnings:
    """Trip earnings breakdown"""
    trip_id: str
    vessel_id: str
    total_revenue: Decimal
    fish_sales: Decimal
    other_income: Decimal = Decimal('0')
    
    # Fish breakdown
    species_breakdown: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)  # species -> {weight, price, total}
    
    # Trip details
    trip_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trip_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    days_at_sea: int = 0
    
    # Market information
    market_prices: Dict[str, Decimal] = field(default_factory=dict)  # species -> price per unit
    buyer_information: Optional[str] = None


@dataclass
class CrewShare:
    """Individual crew member share configuration"""
    crew_member_id: str
    role: CrewRole
    share_percentage: Decimal
    base_share: Decimal  # Base share amount before bonuses/deductions
    bonuses: Dict[BonusType, Decimal] = field(default_factory=dict)
    deductions: Dict[DeductionType, Decimal] = field(default_factory=dict)
    performance_multiplier: Decimal = Decimal('1.0')
    days_worked: int = 0
    overtime_hours: Decimal = Decimal('0')
    notes: List[str] = field(default_factory=list)


@dataclass
class ShareScheme:
    """Crew share scheme definition"""
    scheme_id: str
    name: str
    share_type: ShareType
    vessel_id: str
    
    # Share allocations by role
    role_shares: Dict[CrewRole, Decimal] = field(default_factory=dict)  # percentage of total shares
    
    # Deduction rules
    automatic_deductions: Dict[DeductionType, Decimal] = field(default_factory=dict)  # percentage or fixed amount
    deduction_order: List[DeductionType] = field(default_factory=list)  # order to apply deductions
    
    # Bonus rules
    bonus_rules: Dict[BonusType, Dict[str, Any]] = field(default_factory=dict)  # bonus calculation rules
    
    # General settings
    captain_share_percentage: Decimal = Decimal('20')  # Captain's share of net income
    crew_share_percentage: Decimal = Decimal('50')     # Total crew share percentage
    vessel_share_percentage: Decimal = Decimal('30')   # Vessel/owner share percentage
    
    minimum_share_amount: Decimal = Decimal('0')       # Minimum guaranteed share
    advance_percentage: Decimal = Decimal('25')        # Percentage of expected share as advance
    
    # Configuration
    calculate_overtime: bool = True
    overtime_rate_multiplier: Decimal = Decimal('1.5')
    include_captain_in_crew: bool = False
    prorate_partial_trips: bool = True
    
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True


@dataclass
class ShareAllocation:
    """Final share allocation for a trip"""
    allocation_id: str
    trip_id: str
    scheme_id: str
    crew_member_id: str
    
    # Calculated amounts
    gross_share: Decimal
    total_deductions: Decimal
    total_bonuses: Decimal
    net_share: Decimal
    
    # Breakdown
    base_calculation: Dict[str, Decimal] = field(default_factory=dict)
    bonus_breakdown: Dict[BonusType, Decimal] = field(default_factory=dict)
    deduction_breakdown: Dict[DeductionType, Decimal] = field(default_factory=dict)
    
    # Payment tracking
    advance_paid: Decimal = Decimal('0')
    balance_due: Decimal = Decimal('0')
    payment_status: str = "pending"  # pending, partial, paid
    
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    calculated_by: str = ""
    notes: List[str] = field(default_factory=list)


@dataclass
class PaymentRecord:
    """Record of crew payment"""
    payment_id: str
    allocation_id: str
    crew_member_id: str
    trip_id: str
    
    amount: Decimal
    payment_type: str  # advance, final, bonus, adjustment
    payment_method: str  # cash, check, transfer
    payment_date: datetime
    
    processed_by: str
    notes: Optional[str] = None
    reference_number: Optional[str] = None


class ShareCalculator:
    """Main crew share calculation system"""
    
    def __init__(self, crew_manager: CrewManager, permission_manager: PermissionManager):
        self.crew_manager = crew_manager
        self.permission_manager = permission_manager
        
        # Storage
        self.share_schemes: Dict[str, ShareScheme] = {}
        self.trip_earnings: Dict[str, TripEarnings] = {}
        self.share_allocations: Dict[str, ShareAllocation] = {}
        self.payment_records: Dict[str, PaymentRecord] = {}
        
        # Indices
        self.allocations_by_trip: Dict[str, Set[str]] = {}
        self.allocations_by_crew: Dict[str, Set[str]] = {}
        self.payments_by_crew: Dict[str, List[str]] = {}
        
        # Default scheme
        self._create_default_scheme()
        
        logger.info("Share Calculator initialized")
    
    def _create_default_scheme(self) -> None:
        """Create default share scheme"""
        default_scheme = ShareScheme(
            scheme_id="default_fishing_shares",
            name="Standard Fishing Crew Shares",
            share_type=ShareType.ROLE_BASED,
            vessel_id="default",
            role_shares={
                CrewRole.CAPTAIN: Decimal('30'),      # 30% of crew shares
                CrewRole.FIRST_MATE: Decimal('25'),   # 25% of crew shares
                CrewRole.ENGINEER: Decimal('20'),     # 20% of crew shares
                CrewRole.COOK: Decimal('15'),         # 15% of crew shares
                CrewRole.DECK_HAND: Decimal('10')     # 10% of crew shares each
            },
            automatic_deductions={
                DeductionType.FUEL: Decimal('15'),    # 15% of gross
                DeductionType.ICE: Decimal('3'),      # 3% of gross
                DeductionType.FOOD: Decimal('5'),     # 5% of gross
                DeductionType.GEAR_REPLACEMENT: Decimal('2')  # 2% of gross
            },
            deduction_order=[
                DeductionType.FUEL,
                DeductionType.ICE,
                DeductionType.FOOD,
                DeductionType.GEAR_REPLACEMENT,
                DeductionType.ADVANCE_PAYMENT
            ],
            bonus_rules={
                BonusType.SAFETY_RECORD: {
                    'type': 'percentage',
                    'value': Decimal('5'),  # 5% bonus for perfect safety record
                    'condition': 'zero_incidents'
                },
                BonusType.OVERTIME: {
                    'type': 'hourly_rate',
                    'multiplier': Decimal('1.5')
                }
            }
        )
        
        self.share_schemes["default"] = default_scheme
    
    async def create_share_scheme(self, name: str, share_type: ShareType,
                                 vessel_id: str, created_by: str,
                                 role_shares: Optional[Dict[CrewRole, Decimal]] = None,
                                 **kwargs) -> Optional[str]:
        """Create a new share scheme"""
        try:
            # Verify creator permissions
            creator = await self.crew_manager.get_crew_member(created_by)
            if not creator:
                logger.error(f"Creator {created_by} not found")
                return None
            
            can_create = self.permission_manager.has_permission(
                creator.role, Permission.VIEW_FINANCIALS
            )
            if not can_create:
                logger.error(f"User {created_by} cannot create share schemes")
                return None
            
            scheme_id = str(uuid.uuid4())
            
            scheme = ShareScheme(
                scheme_id=scheme_id,
                name=name,
                share_type=share_type,
                vessel_id=vessel_id,
                created_by=created_by,
                role_shares=role_shares or {},
                **kwargs
            )
            
            # Validate share percentages add up correctly
            if role_shares:
                total_shares = sum(role_shares.values())
                if total_shares != Decimal('100'):
                    logger.warning(f"Role shares total {total_shares}%, adjusting to 100%")
                    # Normalize shares to 100%
                    for role in role_shares:
                        scheme.role_shares[role] = (role_shares[role] / total_shares) * Decimal('100')
            
            self.share_schemes[scheme_id] = scheme
            
            logger.info(f"Created share scheme {scheme_id}: {name}")
            return scheme_id
            
        except Exception as e:
            logger.error(f"Failed to create share scheme: {e}")
            return None
    
    async def record_trip_earnings(self, trip_id: str, vessel_id: str,
                                  total_revenue: Decimal, fish_sales: Decimal,
                                  species_breakdown: Dict[str, Dict[str, Decimal]],
                                  trip_start: datetime, trip_end: datetime,
                                  recorded_by: str,
                                  other_income: Decimal = Decimal('0')) -> bool:
        """Record trip earnings for share calculation"""
        try:
            # Verify recorder permissions
            recorder = await self.crew_manager.get_crew_member(recorded_by)
            if not recorder:
                return False
            
            can_record = self.permission_manager.has_permission(
                recorder.role, Permission.VIEW_FINANCIALS
            )
            if not can_record:
                logger.error(f"User {recorded_by} cannot record trip earnings")
                return False
            
            # Calculate days at sea
            days_at_sea = (trip_end - trip_start).days
            if days_at_sea == 0:
                days_at_sea = 1  # Minimum 1 day
            
            earnings = TripEarnings(
                trip_id=trip_id,
                vessel_id=vessel_id,
                total_revenue=total_revenue,
                fish_sales=fish_sales,
                other_income=other_income,
                species_breakdown=species_breakdown,
                trip_start=trip_start,
                trip_end=trip_end,
                days_at_sea=days_at_sea
            )
            
            self.trip_earnings[trip_id] = earnings
            
            logger.info(f"Recorded earnings for trip {trip_id}: ${total_revenue}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record trip earnings: {e}")
            return False
    
    async def calculate_crew_shares(self, trip_id: str, scheme_id: str,
                                   crew_assignments: List[Dict[str, Any]],
                                   calculated_by: str,
                                   trip_expenses: Optional[Dict[DeductionType, Decimal]] = None) -> List[str]:
        """Calculate crew shares for a trip"""
        try:
            # Verify calculator permissions
            calculator = await self.crew_manager.get_crew_member(calculated_by)
            if not calculator:
                return []
            
            can_calculate = self.permission_manager.has_permission(
                calculator.role, Permission.VIEW_FINANCIALS
            )
            if not can_calculate:
                logger.error(f"User {calculated_by} cannot calculate shares")
                return []
            
            # Get trip earnings and scheme
            earnings = self.trip_earnings.get(trip_id)
            scheme = self.share_schemes.get(scheme_id)
            
            if not earnings:
                logger.error(f"Trip earnings not found for {trip_id}")
                return []
            
            if not scheme:
                logger.error(f"Share scheme not found: {scheme_id}")
                return []
            
            allocation_ids = []
            
            # Calculate total deductions first
            total_deductions = Decimal('0')
            
            # Apply automatic deductions
            deduction_breakdown = {}
            for deduction_type, percentage in scheme.automatic_deductions.items():
                if percentage > Decimal('0'):
                    deduction_amount = earnings.total_revenue * (percentage / Decimal('100'))
                    deduction_breakdown[deduction_type] = deduction_amount
                    total_deductions += deduction_amount
            
            # Add trip-specific expenses
            if trip_expenses:
                for deduction_type, amount in trip_expenses.items():
                    if deduction_type not in deduction_breakdown:
                        deduction_breakdown[deduction_type] = amount
                    else:
                        deduction_breakdown[deduction_type] += amount
                    total_deductions += amount
            
            # Calculate net revenue after deductions
            net_revenue = earnings.total_revenue - total_deductions
            
            # Calculate total crew share pool
            crew_share_pool = net_revenue * (scheme.crew_share_percentage / Decimal('100'))
            
            # Calculate shares for each crew member
            total_share_units = Decimal('0')
            crew_share_units = {}
            
            # First pass: calculate share units for each crew member
            for assignment in crew_assignments:
                crew_id = assignment['crew_member_id']
                role = CrewRole(assignment['role'])
                days_worked = assignment.get('days_worked', earnings.days_at_sea)
                
                # Get base share percentage for role
                role_share_pct = scheme.role_shares.get(role, Decimal('10'))  # Default 10%
                
                # Calculate share units (can be modified by performance, days worked, etc.)
                share_units = role_share_pct
                
                # Prorate for partial trips if enabled
                if scheme.prorate_partial_trips and days_worked < earnings.days_at_sea:
                    prorate_factor = Decimal(str(days_worked)) / Decimal(str(earnings.days_at_sea))
                    share_units *= prorate_factor
                
                # Apply performance multiplier if specified
                performance_multiplier = assignment.get('performance_multiplier', Decimal('1.0'))
                share_units *= performance_multiplier
                
                crew_share_units[crew_id] = share_units
                total_share_units += share_units
            
            # Second pass: calculate actual share amounts
            for assignment in crew_assignments:
                crew_id = assignment['crew_member_id']
                role = CrewRole(assignment['role'])
                days_worked = assignment.get('days_worked', earnings.days_at_sea)
                overtime_hours = assignment.get('overtime_hours', Decimal('0'))
                
                # Calculate base share
                if total_share_units > 0:
                    share_percentage = crew_share_units[crew_id] / total_share_units
                    base_share = crew_share_pool * share_percentage
                else:
                    base_share = Decimal('0')
                
                # Calculate bonuses
                total_bonuses = Decimal('0')
                bonus_breakdown = {}
                
                # Safety record bonus
                if assignment.get('safety_incidents', 0) == 0 and BonusType.SAFETY_RECORD in scheme.bonus_rules:
                    safety_bonus_rule = scheme.bonus_rules[BonusType.SAFETY_RECORD]
                    if safety_bonus_rule['type'] == 'percentage':
                        safety_bonus = base_share * (safety_bonus_rule['value'] / Decimal('100'))
                        bonus_breakdown[BonusType.SAFETY_RECORD] = safety_bonus
                        total_bonuses += safety_bonus
                
                # Overtime bonus
                if overtime_hours > 0 and scheme.calculate_overtime:
                    # Calculate overtime based on daily rate
                    daily_rate = base_share / Decimal(str(days_worked)) if days_worked > 0 else Decimal('0')
                    hourly_rate = daily_rate / Decimal('8')  # Assume 8-hour standard day
                    overtime_rate = hourly_rate * scheme.overtime_rate_multiplier
                    overtime_bonus = overtime_rate * overtime_hours
                    bonus_breakdown[BonusType.OVERTIME] = overtime_bonus
                    total_bonuses += overtime_bonus
                
                # Apply any custom bonuses
                custom_bonuses = assignment.get('bonuses', {})
                for bonus_type_str, amount in custom_bonuses.items():
                    try:
                        bonus_type = BonusType(bonus_type_str)
                        bonus_breakdown[bonus_type] = Decimal(str(amount))
                        total_bonuses += Decimal(str(amount))
                    except (ValueError, TypeError):
                        continue
                
                # Calculate crew member's share of deductions
                crew_deduction_share = total_deductions * share_percentage
                crew_deduction_breakdown = {}
                for deduction_type, total_amount in deduction_breakdown.items():
                    crew_amount = total_amount * share_percentage
                    crew_deduction_breakdown[deduction_type] = crew_amount
                
                # Calculate final amounts
                gross_share = base_share + total_bonuses
                net_share = gross_share - crew_deduction_share
                
                # Apply minimum share guarantee
                if net_share < scheme.minimum_share_amount:
                    net_share = scheme.minimum_share_amount
                
                # Calculate balance due (considering any advances)
                advance_paid = assignment.get('advance_paid', Decimal('0'))
                balance_due = net_share - advance_paid
                
                # Create allocation record
                allocation_id = str(uuid.uuid4())
                allocation = ShareAllocation(
                    allocation_id=allocation_id,
                    trip_id=trip_id,
                    scheme_id=scheme_id,
                    crew_member_id=crew_id,
                    gross_share=gross_share,
                    total_deductions=crew_deduction_share,
                    total_bonuses=total_bonuses,
                    net_share=net_share,
                    base_calculation={
                        'base_share': base_share,
                        'share_percentage': float(share_percentage * 100),  # Convert to percentage
                        'share_units': float(crew_share_units[crew_id]),
                        'days_worked': days_worked,
                        'overtime_hours': float(overtime_hours)
                    },
                    bonus_breakdown=bonus_breakdown,
                    deduction_breakdown=crew_deduction_breakdown,
                    advance_paid=advance_paid,
                    balance_due=balance_due,
                    calculated_by=calculated_by
                )
                
                self.share_allocations[allocation_id] = allocation
                
                # Update indices
                self.allocations_by_trip.setdefault(trip_id, set()).add(allocation_id)
                self.allocations_by_crew.setdefault(crew_id, set()).add(allocation_id)
                
                allocation_ids.append(allocation_id)
            
            logger.info(f"Calculated shares for trip {trip_id}: {len(allocation_ids)} allocations")
            return allocation_ids
            
        except Exception as e:
            logger.error(f"Failed to calculate crew shares: {e}")
            return []
    
    async def record_payment(self, allocation_id: str, amount: Decimal,
                           payment_type: str, payment_method: str,
                           processed_by: str, notes: Optional[str] = None,
                           reference_number: Optional[str] = None) -> Optional[str]:
        """Record a payment to crew member"""
        try:
            allocation = self.share_allocations.get(allocation_id)
            if not allocation:
                logger.error(f"Allocation {allocation_id} not found")
                return None
            
            # Verify payment processor permissions
            processor = await self.crew_manager.get_crew_member(processed_by)
            if not processor:
                return None
            
            can_process = self.permission_manager.has_permission(
                processor.role, Permission.VIEW_FINANCIALS
            )
            if not can_process:
                logger.error(f"User {processed_by} cannot process payments")
                return None
            
            payment_id = str(uuid.uuid4())
            payment = PaymentRecord(
                payment_id=payment_id,
                allocation_id=allocation_id,
                crew_member_id=allocation.crew_member_id,
                trip_id=allocation.trip_id,
                amount=amount,
                payment_type=payment_type,
                payment_method=payment_method,
                payment_date=datetime.now(timezone.utc),
                processed_by=processed_by,
                notes=notes,
                reference_number=reference_number
            )
            
            self.payment_records[payment_id] = payment
            
            # Update allocation payment tracking
            if payment_type == "advance":
                allocation.advance_paid += amount
            
            allocation.balance_due = allocation.net_share - allocation.advance_paid
            
            # Update payment status
            if allocation.balance_due <= Decimal('0.01'):  # Allow small rounding differences
                allocation.payment_status = "paid"
            elif allocation.advance_paid > Decimal('0'):
                allocation.payment_status = "partial"
            else:
                allocation.payment_status = "pending"
            
            # Update indices
            self.payments_by_crew.setdefault(allocation.crew_member_id, []).append(payment_id)
            
            logger.info(f"Recorded payment {payment_id}: ${amount} to crew {allocation.crew_member_id}")
            return payment_id
            
        except Exception as e:
            logger.error(f"Failed to record payment: {e}")
            return None
    
    def get_crew_share_summary(self, crew_member_id: str,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get crew member's share summary"""
        allocation_ids = self.allocations_by_crew.get(crew_member_id, set())
        
        summary = {
            'crew_member_id': crew_member_id,
            'total_trips': 0,
            'total_gross_earnings': Decimal('0'),
            'total_net_earnings': Decimal('0'),
            'total_bonuses': Decimal('0'),
            'total_deductions': Decimal('0'),
            'total_paid': Decimal('0'),
            'balance_due': Decimal('0'),
            'trips': []
        }
        
        for allocation_id in allocation_ids:
            allocation = self.share_allocations.get(allocation_id)
            if not allocation:
                continue
            
            # Apply date filters if specified
            earnings = self.trip_earnings.get(allocation.trip_id)
            if earnings and start_date and earnings.trip_end < start_date:
                continue
            if earnings and end_date and earnings.trip_start > end_date:
                continue
            
            summary['total_trips'] += 1
            summary['total_gross_earnings'] += allocation.gross_share
            summary['total_net_earnings'] += allocation.net_share
            summary['total_bonuses'] += allocation.total_bonuses
            summary['total_deductions'] += allocation.total_deductions
            summary['total_paid'] += allocation.advance_paid
            summary['balance_due'] += allocation.balance_due
            
            trip_info = {
                'trip_id': allocation.trip_id,
                'gross_share': float(allocation.gross_share),
                'net_share': float(allocation.net_share),
                'bonuses': float(allocation.total_bonuses),
                'deductions': float(allocation.total_deductions),
                'payment_status': allocation.payment_status,
                'calculated_at': allocation.calculated_at.isoformat()
            }
            
            if earnings:
                trip_info.update({
                    'trip_start': earnings.trip_start.isoformat(),
                    'trip_end': earnings.trip_end.isoformat(),
                    'days_at_sea': earnings.days_at_sea
                })
            
            summary['trips'].append(trip_info)
        
        # Convert Decimal to float for JSON serialization
        summary['total_gross_earnings'] = float(summary['total_gross_earnings'])
        summary['total_net_earnings'] = float(summary['total_net_earnings'])
        summary['total_bonuses'] = float(summary['total_bonuses'])
        summary['total_deductions'] = float(summary['total_deductions'])
        summary['total_paid'] = float(summary['total_paid'])
        summary['balance_due'] = float(summary['balance_due'])
        
        return summary
    
    def get_trip_share_summary(self, trip_id: str) -> Dict[str, Any]:
        """Get complete share summary for a trip"""
        allocation_ids = self.allocations_by_trip.get(trip_id, set())
        earnings = self.trip_earnings.get(trip_id)
        
        summary = {
            'trip_id': trip_id,
            'total_crew': len(allocation_ids),
            'total_gross_shares': Decimal('0'),
            'total_net_shares': Decimal('0'),
            'total_bonuses': Decimal('0'),
            'total_deductions': Decimal('0'),
            'crew_allocations': []
        }
        
        if earnings:
            summary.update({
                'total_revenue': float(earnings.total_revenue),
                'fish_sales': float(earnings.fish_sales),
                'other_income': float(earnings.other_income),
                'trip_start': earnings.trip_start.isoformat(),
                'trip_end': earnings.trip_end.isoformat(),
                'days_at_sea': earnings.days_at_sea
            })
        
        for allocation_id in allocation_ids:
            allocation = self.share_allocations.get(allocation_id)
            if not allocation:
                continue
            
            summary['total_gross_shares'] += allocation.gross_share
            summary['total_net_shares'] += allocation.net_share
            summary['total_bonuses'] += allocation.total_bonuses
            summary['total_deductions'] += allocation.total_deductions
            
            crew_info = {
                'allocation_id': allocation.allocation_id,
                'crew_member_id': allocation.crew_member_id,
                'gross_share': float(allocation.gross_share),
                'net_share': float(allocation.net_share),
                'bonuses': float(allocation.total_bonuses),
                'deductions': float(allocation.total_deductions),
                'advance_paid': float(allocation.advance_paid),
                'balance_due': float(allocation.balance_due),
                'payment_status': allocation.payment_status,
                'base_calculation': allocation.base_calculation,
                'bonus_breakdown': {k.value: float(v) for k, v in allocation.bonus_breakdown.items()},
                'deduction_breakdown': {k.value: float(v) for k, v in allocation.deduction_breakdown.items()}
            }
            
            summary['crew_allocations'].append(crew_info)
        
        # Convert Decimal totals to float
        summary['total_gross_shares'] = float(summary['total_gross_shares'])
        summary['total_net_shares'] = float(summary['total_net_shares'])
        summary['total_bonuses'] = float(summary['total_bonuses'])
        summary['total_deductions'] = float(summary['total_deductions'])
        
        return summary
    
    def get_payment_history(self, crew_member_id: str) -> List[Dict[str, Any]]:
        """Get payment history for crew member"""
        payment_ids = self.payments_by_crew.get(crew_member_id, [])
        
        payments = []
        for payment_id in payment_ids:
            payment = self.payment_records.get(payment_id)
            if payment:
                payments.append({
                    'payment_id': payment.payment_id,
                    'trip_id': payment.trip_id,
                    'amount': float(payment.amount),
                    'payment_type': payment.payment_type,
                    'payment_method': payment.payment_method,
                    'payment_date': payment.payment_date.isoformat(),
                    'processed_by': payment.processed_by,
                    'notes': payment.notes,
                    'reference_number': payment.reference_number
                })
        
        # Sort by payment date (newest first)
        return sorted(payments, key=lambda x: x['payment_date'], reverse=True)