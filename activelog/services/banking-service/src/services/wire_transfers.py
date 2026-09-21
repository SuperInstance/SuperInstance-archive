import uuid
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class WireType(Enum):
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    BOOK_TRANSFER = "book_transfer"

class WireStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    RECALLED = "recalled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class WirePriority(Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class WireTransfer:
    wire_id: str
    originator_account_id: str
    originator_name: str
    originator_address: str
    beneficiary_name: str
    beneficiary_address: str
    beneficiary_account_number: str
    beneficiary_bank_name: str
    beneficiary_bank_swift: str
    beneficiary_bank_routing: Optional[str]
    intermediary_bank_name: Optional[str]
    intermediary_bank_swift: Optional[str]
    amount: Decimal
    currency: str
    wire_type: WireType
    priority: WirePriority
    purpose_code: str
    payment_details: str
    charges_instruction: str  # OUR, BEN, SHA
    status: WireStatus
    reference_number: str
    federal_reference: Optional[str]
    created_at: datetime
    value_date: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    fees: Dict[str, Decimal]
    compliance_status: str
    ofac_status: str

class WireTransferService:
    def __init__(self):
        self.wires = {}
        self.daily_limits = {}
        self.wire_counter = 1000000
        self.bank_swift_code = "ACTLUS33"
        self.bank_routing = "123456789"
        
        # Wire fees
        self.fees = {
            "domestic_outgoing": Decimal("25.00"),
            "domestic_incoming": Decimal("15.00"),
            "international_outgoing": Decimal("45.00"),
            "international_incoming": Decimal("15.00"),
            "urgent_surcharge": Decimal("20.00"),
            "recall_fee": Decimal("35.00")
        }
    
    async def initiate_wire_transfer(self, 
                                   originator_account_id: str,
                                   originator_name: str,
                                   originator_address: str,
                                   beneficiary_name: str,
                                   beneficiary_address: str,
                                   beneficiary_account_number: str,
                                   beneficiary_bank_name: str,
                                   beneficiary_bank_identifier: str,  # SWIFT or Routing
                                   amount: float,
                                   currency: str = "USD",
                                   payment_details: str = "",
                                   purpose_code: str = "SUPP",
                                   priority: str = "normal",
                                   charges_instruction: str = "OUR",
                                   value_date: datetime = None,
                                   intermediary_bank_name: str = None,
                                   intermediary_bank_swift: str = None) -> Dict:
        """Initiate a wire transfer"""
        try:
            # Validate amount
            if amount <= 0:
                return {'success': False, 'error': 'Amount must be positive'}
            
            if amount > settings.DAILY_WIRE_LIMIT:
                return {'success': False, 'error': f'Amount exceeds daily wire limit of ${settings.DAILY_WIRE_LIMIT:,.2f}'}
            
            # Check daily limits
            daily_limit_check = await self._check_daily_limits(originator_account_id, amount)
            if not daily_limit_check['allowed']:
                return {'success': False, 'error': daily_limit_check['reason']}
            
            # Determine wire type
            wire_type = self._determine_wire_type(beneficiary_bank_identifier, currency)
            
            # Validate based on wire type
            validation_result = await self._validate_wire_details(wire_type, beneficiary_bank_identifier, currency)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['error']}
            
            # Set value date
            if value_date is None:
                value_date = self._get_next_business_day()
            
            # Calculate fees
            wire_fees = await self._calculate_fees(wire_type, priority, amount)
            
            wire_id = str(uuid.uuid4())
            reference_number = self._generate_reference_number()
            
            # Determine bank identifiers based on type
            beneficiary_bank_swift = None
            beneficiary_bank_routing = None
            
            if wire_type == WireType.INTERNATIONAL:
                beneficiary_bank_swift = beneficiary_bank_identifier
            else:
                beneficiary_bank_routing = beneficiary_bank_identifier
                beneficiary_bank_swift = None
            
            wire = WireTransfer(
                wire_id=wire_id,
                originator_account_id=originator_account_id,
                originator_name=originator_name,
                originator_address=originator_address,
                beneficiary_name=beneficiary_name,
                beneficiary_address=beneficiary_address,
                beneficiary_account_number=beneficiary_account_number,
                beneficiary_bank_name=beneficiary_bank_name,
                beneficiary_bank_swift=beneficiary_bank_swift,
                beneficiary_bank_routing=beneficiary_bank_routing,
                intermediary_bank_name=intermediary_bank_name,
                intermediary_bank_swift=intermediary_bank_swift,
                amount=Decimal(str(amount)),
                currency=currency,
                wire_type=wire_type,
                priority=WirePriority(priority),
                purpose_code=purpose_code,
                payment_details=payment_details,
                charges_instruction=charges_instruction,
                status=WireStatus.PENDING,
                reference_number=reference_number,
                federal_reference=None,
                created_at=datetime.now(),
                value_date=value_date,
                processed_at=None,
                completed_at=None,
                fees=wire_fees,
                compliance_status="pending",
                ofac_status="pending"
            )
            
            self.wires[wire_id] = wire
            
            # Update daily limits
            await self._update_daily_limits(originator_account_id, amount)
            
            # Start compliance and OFAC checks
            asyncio.create_task(self._perform_compliance_checks(wire_id))
            
            logger.info(f"Wire transfer initiated: {wire_id} for ${amount} {currency}")
            
            return {
                'success': True,
                'wire_id': wire_id,
                'reference_number': reference_number,
                'value_date': value_date.isoformat(),
                'wire_type': wire_type.value,
                'total_fees': float(sum(wire_fees.values())),
                'status': 'pending',
                'estimated_completion': self._get_completion_time(wire_type, priority, value_date).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error initiating wire transfer: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_wire_status(self, wire_id: str) -> Dict:
        """Get wire transfer status"""
        try:
            if wire_id not in self.wires:
                return {'success': False, 'error': 'Wire transfer not found'}
            
            wire = self.wires[wire_id]
            
            return {
                'success': True,
                'wire_id': wire_id,
                'reference_number': wire.reference_number,
                'federal_reference': wire.federal_reference,
                'status': wire.status.value,
                'wire_type': wire.wire_type.value,
                'amount': float(wire.amount),
                'currency': wire.currency,
                'beneficiary_name': wire.beneficiary_name,
                'beneficiary_bank': wire.beneficiary_bank_name,
                'value_date': wire.value_date.isoformat(),
                'created_at': wire.created_at.isoformat(),
                'processed_at': wire.processed_at.isoformat() if wire.processed_at else None,
                'completed_at': wire.completed_at.isoformat() if wire.completed_at else None,
                'fees': {k: float(v) for k, v in wire.fees.items()},
                'compliance_status': wire.compliance_status,
                'ofac_status': wire.ofac_status
            }
        
        except Exception as e:
            logger.error(f"Error getting wire status: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cancel_wire(self, wire_id: str, reason: str) -> Dict:
        """Cancel a pending wire transfer"""
        try:
            if wire_id not in self.wires:
                return {'success': False, 'error': 'Wire transfer not found'}
            
            wire = self.wires[wire_id]
            
            if wire.status not in [WireStatus.PENDING, WireStatus.PROCESSING]:
                return {'success': False, 'error': f'Wire transfer cannot be cancelled - status: {wire.status.value}'}
            
            # Check if we're still before value date
            if datetime.now() >= wire.value_date and wire.status == WireStatus.PROCESSING:
                return {'success': False, 'error': 'Wire transfer cannot be cancelled - already processing'}
            
            wire.status = WireStatus.CANCELLED
            
            # Restore daily limits
            await self._restore_daily_limits(wire.originator_account_id, float(wire.amount))
            
            logger.info(f"Wire transfer cancelled: {wire_id}, Reason: {reason}")
            
            return {
                'success': True,
                'wire_id': wire_id,
                'status': 'cancelled',
                'reason': reason
            }
        
        except Exception as e:
            logger.error(f"Error cancelling wire: {e}")
            return {'success': False, 'error': str(e)}
    
    async def recall_wire(self, wire_id: str, reason: str) -> Dict:
        """Attempt to recall a sent wire transfer"""
        try:
            if wire_id not in self.wires:
                return {'success': False, 'error': 'Wire transfer not found'}
            
            wire = self.wires[wire_id]
            
            if wire.status != WireStatus.SENT:
                return {'success': False, 'error': f'Wire transfer cannot be recalled - status: {wire.status.value}'}
            
            # International wires are harder to recall
            if wire.wire_type == WireType.INTERNATIONAL:
                recall_success_rate = 0.3  # 30% success rate
            else:
                recall_success_rate = 0.7  # 70% success rate
            
            # Simulate recall attempt
            import random
            recall_successful = random.random() < recall_success_rate
            
            if recall_successful:
                wire.status = WireStatus.RECALLED
                # Add recall fee
                wire.fees['recall_fee'] = self.fees['recall_fee']
                
                # Restore funds to originator account
                await self._restore_daily_limits(wire.originator_account_id, -float(wire.amount))
                
                logger.info(f"Wire transfer recalled successfully: {wire_id}")
                
                return {
                    'success': True,
                    'wire_id': wire_id,
                    'status': 'recalled',
                    'recall_fee': float(self.fees['recall_fee']),
                    'reason': reason
                }
            else:
                logger.warning(f"Wire transfer recall failed: {wire_id}")
                
                return {
                    'success': False,
                    'error': 'Recall attempt unsuccessful - wire may have already been processed by beneficiary bank',
                    'recall_fee': float(self.fees['recall_fee'])
                }
        
        except Exception as e:
            logger.error(f"Error recalling wire: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_incoming_wire(self, 
                                  beneficiary_account_id: str,
                                  originator_name: str,
                                  originator_bank: str,
                                  amount: float,
                                  currency: str,
                                  reference_number: str,
                                  payment_details: str) -> Dict:
        """Process an incoming wire transfer"""
        try:
            wire_id = str(uuid.uuid4())
            
            # Determine wire type based on originator bank
            wire_type = WireType.INTERNATIONAL if len(originator_bank) > 9 else WireType.DOMESTIC
            
            # Calculate incoming fees
            fee_key = f"{wire_type.value}_incoming"
            incoming_fee = self.fees.get(fee_key, Decimal("15.00"))
            
            wire = WireTransfer(
                wire_id=wire_id,
                originator_account_id=None,  # External originator
                originator_name=originator_name,
                originator_address="",
                beneficiary_name="Account Holder",  # Would get from account
                beneficiary_address="",
                beneficiary_account_number=beneficiary_account_id,
                beneficiary_bank_name="ActiveLog Bank",
                beneficiary_bank_swift=self.bank_swift_code,
                beneficiary_bank_routing=self.bank_routing,
                intermediary_bank_name=None,
                intermediary_bank_swift=None,
                amount=Decimal(str(amount)),
                currency=currency,
                wire_type=wire_type,
                priority=WirePriority.NORMAL,
                purpose_code="SUPP",
                payment_details=payment_details,
                charges_instruction="BEN",
                status=WireStatus.PROCESSING,
                reference_number=reference_number,
                federal_reference=None,
                created_at=datetime.now(),
                value_date=datetime.now(),
                processed_at=datetime.now(),
                completed_at=None,
                fees={"incoming_fee": incoming_fee},
                compliance_status="approved",  # Assume pre-screened
                ofac_status="clear"
            )
            
            self.wires[wire_id] = wire
            
            # Complete the wire immediately for incoming
            await self._complete_wire(wire_id)
            
            logger.info(f"Incoming wire processed: {wire_id} for ${amount} {currency}")
            
            return {
                'success': True,
                'wire_id': wire_id,
                'reference_number': reference_number,
                'amount_received': float(amount) - float(incoming_fee),
                'incoming_fee': float(incoming_fee),
                'status': 'completed'
            }
        
        except Exception as e:
            logger.error(f"Error processing incoming wire: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_wire_history(self, account_id: str,
                             start_date: datetime = None,
                             end_date: datetime = None) -> List[Dict]:
        """Get wire transfer history for an account"""
        try:
            history = []
            
            for wire in self.wires.values():
                # Check if this wire involves the account (originator or beneficiary)
                if (wire.originator_account_id != account_id and 
                    wire.beneficiary_account_number != account_id):
                    continue
                
                if start_date and wire.created_at < start_date:
                    continue
                
                if end_date and wire.created_at > end_date:
                    continue
                
                # Determine direction
                direction = "outgoing" if wire.originator_account_id == account_id else "incoming"
                
                history.append({
                    'wire_id': wire.wire_id,
                    'reference_number': wire.reference_number,
                    'direction': direction,
                    'amount': float(wire.amount),
                    'currency': wire.currency,
                    'counterparty': wire.beneficiary_name if direction == "outgoing" else wire.originator_name,
                    'counterparty_bank': wire.beneficiary_bank_name if direction == "outgoing" else "External Bank",
                    'status': wire.status.value,
                    'wire_type': wire.wire_type.value,
                    'value_date': wire.value_date.isoformat(),
                    'created_at': wire.created_at.isoformat(),
                    'total_fees': float(sum(wire.fees.values()))
                })
            
            return sorted(history, key=lambda x: x['created_at'], reverse=True)
        
        except Exception as e:
            logger.error(f"Error getting wire history: {e}")
            return []
    
    def _determine_wire_type(self, bank_identifier: str, currency: str) -> WireType:
        """Determine wire type based on bank identifier and currency"""
        if currency != "USD":
            return WireType.INTERNATIONAL
        
        # SWIFT codes are typically 8-11 characters
        if len(bank_identifier) > 9 or not bank_identifier.isdigit():
            return WireType.INTERNATIONAL
        
        # US routing numbers are 9 digits
        if len(bank_identifier) == 9 and bank_identifier.isdigit():
            return WireType.DOMESTIC
        
        return WireType.INTERNATIONAL
    
    async def _validate_wire_details(self, wire_type: WireType, bank_identifier: str, currency: str) -> Dict:
        """Validate wire transfer details"""
        if wire_type == WireType.DOMESTIC:
            # Validate routing number
            if not self._validate_routing_number(bank_identifier):
                return {'valid': False, 'error': 'Invalid routing number'}
        
        elif wire_type == WireType.INTERNATIONAL:
            # Validate SWIFT code
            if not self._validate_swift_code(bank_identifier):
                return {'valid': False, 'error': 'Invalid SWIFT/BIC code'}
        
        # Validate currency
        if currency not in ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF']:
            return {'valid': False, 'error': 'Unsupported currency'}
        
        return {'valid': True}
    
    def _validate_routing_number(self, routing_number: str) -> bool:
        """Validate US routing number"""
        if len(routing_number) != 9 or not routing_number.isdigit():
            return False
        
        # Check digit validation
        weights = [3, 7, 1, 3, 7, 1, 3, 7]
        check_sum = sum(int(routing_number[i]) * weights[i] for i in range(8))
        check_digit = (10 - (check_sum % 10)) % 10
        
        return int(routing_number[8]) == check_digit
    
    def _validate_swift_code(self, swift_code: str) -> bool:
        """Validate SWIFT/BIC code"""
        if len(swift_code) < 8 or len(swift_code) > 11:
            return False
        
        # Basic format validation
        if not swift_code[:4].isalpha():  # Bank code
            return False
        
        if not swift_code[4:6].isalpha():  # Country code
            return False
        
        return True
    
    async def _calculate_fees(self, wire_type: WireType, priority: str, amount: float) -> Dict[str, Decimal]:
        """Calculate wire transfer fees"""
        fees = {}
        
        # Base wire fee
        if wire_type == WireType.DOMESTIC:
            fees['wire_fee'] = self.fees['domestic_outgoing']
        else:
            fees['wire_fee'] = self.fees['international_outgoing']
        
        # Priority surcharge
        if priority in ['high', 'urgent']:
            fees['priority_surcharge'] = self.fees['urgent_surcharge']
        
        return fees
    
    def _get_next_business_day(self) -> datetime:
        """Get next business day for value date"""
        next_day = datetime.now() + timedelta(days=1)
        
        while next_day.weekday() > 4:  # Skip weekends
            next_day += timedelta(days=1)
        
        return next_day.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _get_completion_time(self, wire_type: WireType, priority: str, value_date: datetime) -> datetime:
        """Estimate completion time"""
        base_delay = 2 if wire_type == WireType.DOMESTIC else 24  # hours
        
        if priority == 'urgent':
            base_delay = base_delay // 2
        
        return value_date + timedelta(hours=base_delay)
    
    def _generate_reference_number(self) -> str:
        """Generate unique wire reference number"""
        self.wire_counter += 1
        return f"WR{datetime.now().strftime('%y%m%d')}{self.wire_counter:06d}"
    
    async def _check_daily_limits(self, account_id: str, amount: float) -> Dict:
        """Check daily wire transfer limits"""
        today = datetime.now().date()
        
        if account_id not in self.daily_limits:
            self.daily_limits[account_id] = {}
        
        if today not in self.daily_limits[account_id]:
            self.daily_limits[account_id][today] = 0.0
        
        current_usage = self.daily_limits[account_id][today]
        
        if current_usage + amount > settings.DAILY_WIRE_LIMIT:
            return {
                'allowed': False,
                'reason': f'Daily wire limit exceeded. Current: ${current_usage:,.2f}, Limit: ${settings.DAILY_WIRE_LIMIT:,.2f}'
            }
        
        return {'allowed': True}
    
    async def _update_daily_limits(self, account_id: str, amount: float):
        """Update daily limits"""
        today = datetime.now().date()
        
        if account_id not in self.daily_limits:
            self.daily_limits[account_id] = {}
        
        if today not in self.daily_limits[account_id]:
            self.daily_limits[account_id][today] = 0.0
        
        self.daily_limits[account_id][today] += amount
    
    async def _restore_daily_limits(self, account_id: str, amount: float):
        """Restore daily limits after cancellation"""
        today = datetime.now().date()
        
        if account_id in self.daily_limits and today in self.daily_limits[account_id]:
            self.daily_limits[account_id][today] -= amount
    
    async def _perform_compliance_checks(self, wire_id: str):
        """Perform compliance and OFAC screening"""
        try:
            wire = self.wires[wire_id]
            
            # Simulate compliance checks delay
            await asyncio.sleep(2)
            
            # OFAC screening (simulate)
            ofac_hit = await self._check_ofac(wire.beneficiary_name, wire.beneficiary_address)
            
            if ofac_hit:
                wire.status = WireStatus.REJECTED
                wire.ofac_status = "blocked"
                wire.compliance_status = "rejected"
                logger.warning(f"Wire transfer blocked by OFAC: {wire_id}")
                return
            
            # BSA/AML checks
            if wire.amount >= Decimal(str(settings.BSA_REPORTING_THRESHOLD)):
                wire.compliance_status = "bsa_reporting_required"
                # Would generate BSA report here
            
            wire.ofac_status = "clear"
            wire.compliance_status = "approved"
            
            # Schedule processing
            asyncio.create_task(self._schedule_wire_processing(wire_id))
            
        except Exception as e:
            logger.error(f"Error in compliance checks for wire {wire_id}: {e}")
            wire = self.wires[wire_id]
            wire.status = WireStatus.FAILED
            wire.compliance_status = "error"
    
    async def _check_ofac(self, name: str, address: str) -> bool:
        """Check against OFAC sanctions list"""
        # Mock OFAC check - in production would check against actual OFAC list
        blocked_names = ['BLOCKED PERSON', 'SANCTIONED ENTITY']
        return any(blocked.lower() in name.lower() for blocked in blocked_names)
    
    async def _schedule_wire_processing(self, wire_id: str):
        """Schedule wire for processing"""
        try:
            wire = self.wires[wire_id]
            
            # Wait until value date
            delay = (wire.value_date - datetime.now()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
            
            wire.status = WireStatus.PROCESSING
            wire.processed_at = datetime.now()
            
            # Simulate processing time
            processing_delay = 300 if wire.wire_type == WireType.DOMESTIC else 3600  # 5 min vs 1 hour
            if wire.priority == WirePriority.URGENT:
                processing_delay //= 2
            
            await asyncio.sleep(processing_delay)
            
            # Send wire
            wire.status = WireStatus.SENT
            wire.federal_reference = f"FED{uuid.uuid4().hex[:8].upper()}"
            
            # Schedule completion
            completion_delay = 3600 if wire.wire_type == WireType.DOMESTIC else 86400  # 1 hour vs 1 day
            await asyncio.sleep(completion_delay)
            
            await self._complete_wire(wire_id)
            
        except Exception as e:
            logger.error(f"Error processing wire {wire_id}: {e}")
            wire = self.wires[wire_id]
            wire.status = WireStatus.FAILED
    
    async def _complete_wire(self, wire_id: str):
        """Complete wire transfer"""
        try:
            wire = self.wires[wire_id]
            wire.status = WireStatus.COMPLETED
            wire.completed_at = datetime.now()
            
            logger.info(f"Wire transfer completed: {wire_id}")
            
        except Exception as e:
            logger.error(f"Error completing wire {wire_id}: {e}")