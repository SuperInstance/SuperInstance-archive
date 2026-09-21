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

class ACHTransactionCode(Enum):
    PPD_DEBIT = "27"  # Prearranged Payment and Deposit - Debit
    PPD_CREDIT = "22"  # Prearranged Payment and Deposit - Credit
    CCD_DEBIT = "27"  # Cash Concentration or Disbursement - Debit
    CCD_CREDIT = "22"  # Cash Concentration or Disbursement - Credit
    WEB_DEBIT = "27"  # Internet Initiated - Debit
    WEB_CREDIT = "22"  # Internet Initiated - Credit
    TEL_DEBIT = "27"  # Telephone Initiated - Debit
    TEL_CREDIT = "22"  # Telephone Initiated - Credit

class ACHStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETURNED = "returned"
    CANCELLED = "cancelled"

class ACHReturnCode(Enum):
    R01 = "R01"  # Insufficient Funds
    R02 = "R02"  # Account Closed
    R03 = "R03"  # No Account/Unable to Locate Account
    R04 = "R04"  # Invalid Account Number
    R05 = "R05"  # Unauthorized Debit to Consumer Account
    R07 = "R07"  # Authorization Revoked by Customer
    R08 = "R08"  # Payment Stopped
    R09 = "R09"  # Uncollected Funds
    R10 = "R10"  # Customer Advises Not Authorized

@dataclass
class ACHTransfer:
    transfer_id: str
    originator_account_id: str
    receiver_account_id: str
    receiver_routing_number: str
    receiver_account_number: str
    amount: Decimal
    transaction_code: ACHTransactionCode
    company_name: str
    company_id: str
    effective_date: datetime
    description: str
    status: ACHStatus
    created_at: datetime
    processed_at: Optional[datetime]
    return_code: Optional[ACHReturnCode]
    return_reason: Optional[str]
    trace_number: str
    batch_id: str

class ACHTransferService:
    def __init__(self):
        self.transfers = {}
        self.batches = {}
        self.daily_limits = {}
        self.company_id = "1234567890"  # Bank's company ID
        self.trace_counter = 1
        
    async def initiate_ach_transfer(self, 
                                  originator_account_id: str,
                                  receiver_routing_number: str,
                                  receiver_account_number: str,
                                  amount: float,
                                  transaction_type: str,  # "debit" or "credit"
                                  description: str,
                                  effective_date: datetime = None,
                                  company_name: str = "ActiveLog Bank") -> Dict:
        """Initiate an ACH transfer"""
        try:
            # Validate amount
            if amount <= 0:
                return {'success': False, 'error': 'Amount must be positive'}
            
            if amount > settings.DAILY_ACH_LIMIT:
                return {'success': False, 'error': f'Amount exceeds daily ACH limit of ${settings.DAILY_ACH_LIMIT:,.2f}'}
            
            # Check daily limits
            daily_limit_check = await self._check_daily_limits(originator_account_id, amount)
            if not daily_limit_check['allowed']:
                return {'success': False, 'error': daily_limit_check['reason']}
            
            # Validate routing number
            if not self._validate_routing_number(receiver_routing_number):
                return {'success': False, 'error': 'Invalid routing number'}
            
            # Set effective date (next business day if not specified)
            if effective_date is None:
                effective_date = self._get_next_business_day()
            
            # Determine transaction code
            transaction_code = ACHTransactionCode.WEB_CREDIT if transaction_type == "credit" else ACHTransactionCode.WEB_DEBIT
            
            transfer_id = str(uuid.uuid4())
            trace_number = self._generate_trace_number()
            batch_id = self._get_or_create_batch(effective_date)
            
            transfer = ACHTransfer(
                transfer_id=transfer_id,
                originator_account_id=originator_account_id,
                receiver_account_id=None,  # External account
                receiver_routing_number=receiver_routing_number,
                receiver_account_number=receiver_account_number,
                amount=Decimal(str(amount)),
                transaction_code=transaction_code,
                company_name=company_name,
                company_id=self.company_id,
                effective_date=effective_date,
                description=description,
                status=ACHStatus.PENDING,
                created_at=datetime.now(),
                processed_at=None,
                return_code=None,
                return_reason=None,
                trace_number=trace_number,
                batch_id=batch_id
            )
            
            self.transfers[transfer_id] = transfer
            
            # Update daily limits
            await self._update_daily_limits(originator_account_id, amount)
            
            # Schedule processing
            asyncio.create_task(self._schedule_transfer_processing(transfer_id))
            
            logger.info(f"ACH transfer initiated: {transfer_id} for ${amount}")
            
            return {
                'success': True,
                'transfer_id': transfer_id,
                'trace_number': trace_number,
                'effective_date': effective_date.isoformat(),
                'status': 'pending',
                'estimated_completion': self._get_settlement_date(effective_date).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error initiating ACH transfer: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_transfer_status(self, transfer_id: str) -> Dict:
        """Get ACH transfer status"""
        try:
            if transfer_id not in self.transfers:
                return {'success': False, 'error': 'Transfer not found'}
            
            transfer = self.transfers[transfer_id]
            
            return {
                'success': True,
                'transfer_id': transfer_id,
                'status': transfer.status.value,
                'amount': float(transfer.amount),
                'effective_date': transfer.effective_date.isoformat(),
                'description': transfer.description,
                'trace_number': transfer.trace_number,
                'batch_id': transfer.batch_id,
                'created_at': transfer.created_at.isoformat(),
                'processed_at': transfer.processed_at.isoformat() if transfer.processed_at else None,
                'return_code': transfer.return_code.value if transfer.return_code else None,
                'return_reason': transfer.return_reason
            }
        
        except Exception as e:
            logger.error(f"Error getting transfer status: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cancel_transfer(self, transfer_id: str) -> Dict:
        """Cancel a pending ACH transfer"""
        try:
            if transfer_id not in self.transfers:
                return {'success': False, 'error': 'Transfer not found'}
            
            transfer = self.transfers[transfer_id]
            
            if transfer.status != ACHStatus.PENDING:
                return {'success': False, 'error': 'Transfer cannot be cancelled - already processing'}
            
            # Check if we're still before the effective date
            if datetime.now() >= transfer.effective_date:
                return {'success': False, 'error': 'Transfer cannot be cancelled - effective date has passed'}
            
            transfer.status = ACHStatus.CANCELLED
            
            # Restore daily limits
            await self._restore_daily_limits(transfer.originator_account_id, float(transfer.amount))
            
            logger.info(f"ACH transfer cancelled: {transfer_id}")
            
            return {
                'success': True,
                'transfer_id': transfer_id,
                'status': 'cancelled'
            }
        
        except Exception as e:
            logger.error(f"Error cancelling transfer: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_ach_returns(self, return_data: List[Dict]) -> Dict:
        """Process ACH returns from the network"""
        try:
            processed_returns = []
            
            for return_item in return_data:
                trace_number = return_item.get('trace_number')
                return_code = return_item.get('return_code')
                return_reason = return_item.get('return_reason', '')
                
                # Find transfer by trace number
                transfer = self._find_transfer_by_trace_number(trace_number)
                
                if transfer:
                    transfer.status = ACHStatus.RETURNED
                    transfer.return_code = ACHReturnCode(return_code)
                    transfer.return_reason = return_reason
                    transfer.processed_at = datetime.now()
                    
                    processed_returns.append({
                        'transfer_id': transfer.transfer_id,
                        'trace_number': trace_number,
                        'return_code': return_code,
                        'return_reason': return_reason,
                        'amount': float(transfer.amount)
                    })
                    
                    logger.warning(f"ACH return processed: {transfer.transfer_id}, Code: {return_code}")
            
            return {
                'success': True,
                'returns_processed': len(processed_returns),
                'returns': processed_returns
            }
        
        except Exception as e:
            logger.error(f"Error processing ACH returns: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_transfer_history(self, account_id: str, 
                                 start_date: datetime = None,
                                 end_date: datetime = None) -> List[Dict]:
        """Get ACH transfer history for an account"""
        try:
            history = []
            
            for transfer in self.transfers.values():
                if transfer.originator_account_id != account_id:
                    continue
                
                if start_date and transfer.created_at < start_date:
                    continue
                
                if end_date and transfer.created_at > end_date:
                    continue
                
                history.append({
                    'transfer_id': transfer.transfer_id,
                    'amount': float(transfer.amount),
                    'receiver_account': f"****{transfer.receiver_account_number[-4:]}",
                    'receiver_routing': transfer.receiver_routing_number,
                    'description': transfer.description,
                    'status': transfer.status.value,
                    'effective_date': transfer.effective_date.isoformat(),
                    'created_at': transfer.created_at.isoformat(),
                    'trace_number': transfer.trace_number
                })
            
            return sorted(history, key=lambda x: x['created_at'], reverse=True)
        
        except Exception as e:
            logger.error(f"Error getting transfer history: {e}")
            return []
    
    async def generate_nacha_file(self, batch_id: str) -> Dict:
        """Generate NACHA file for a batch of ACH transfers"""
        try:
            if batch_id not in self.batches:
                return {'success': False, 'error': 'Batch not found'}
            
            batch_transfers = [t for t in self.transfers.values() if t.batch_id == batch_id]
            
            if not batch_transfers:
                return {'success': False, 'error': 'No transfers found in batch'}
            
            # NACHA file header
            file_header = self._create_file_header()
            
            # Batch header
            batch_header = self._create_batch_header(batch_transfers[0].effective_date)
            
            # Entry detail records
            entry_details = []
            for transfer in batch_transfers:
                entry_details.append(self._create_entry_detail(transfer))
            
            # Batch control
            batch_control = self._create_batch_control(batch_transfers)
            
            # File control
            file_control = self._create_file_control(batch_transfers)
            
            nacha_content = "\n".join([
                file_header,
                batch_header,
                *entry_details,
                batch_control,
                file_control
            ])
            
            return {
                'success': True,
                'batch_id': batch_id,
                'nacha_content': nacha_content,
                'transfer_count': len(batch_transfers),
                'total_amount': sum(float(t.amount) for t in batch_transfers)
            }
        
        except Exception as e:
            logger.error(f"Error generating NACHA file: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_routing_number(self, routing_number: str) -> bool:
        """Validate routing number using check digit algorithm"""
        if len(routing_number) != 9 or not routing_number.isdigit():
            return False
        
        # Check digit validation
        weights = [3, 7, 1, 3, 7, 1, 3, 7]
        check_sum = sum(int(routing_number[i]) * weights[i] for i in range(8))
        check_digit = (10 - (check_sum % 10)) % 10
        
        return int(routing_number[8]) == check_digit
    
    def _get_next_business_day(self, days_ahead: int = 1) -> datetime:
        """Get next business day"""
        next_day = datetime.now() + timedelta(days=days_ahead)
        
        # Skip weekends
        while next_day.weekday() > 4:  # Monday = 0, Sunday = 6
            next_day += timedelta(days=1)
        
        return next_day.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _get_settlement_date(self, effective_date: datetime) -> datetime:
        """Get settlement date (typically 1-2 business days after effective date)"""
        return self._get_next_business_day((effective_date - datetime.now()).days + 2)
    
    def _generate_trace_number(self) -> str:
        """Generate unique trace number"""
        self.trace_counter += 1
        return f"123456789{self.trace_counter:07d}"  # Routing number + sequence
    
    def _get_or_create_batch(self, effective_date: datetime) -> str:
        """Get or create batch for effective date"""
        date_key = effective_date.strftime("%Y%m%d")
        
        if date_key not in self.batches:
            batch_id = f"BATCH_{date_key}_{uuid.uuid4().hex[:8].upper()}"
            self.batches[date_key] = {
                'batch_id': batch_id,
                'effective_date': effective_date,
                'created_at': datetime.now()
            }
        
        return self.batches[date_key]['batch_id']
    
    async def _check_daily_limits(self, account_id: str, amount: float) -> Dict:
        """Check daily ACH limits"""
        today = datetime.now().date()
        
        if account_id not in self.daily_limits:
            self.daily_limits[account_id] = {}
        
        if today not in self.daily_limits[account_id]:
            self.daily_limits[account_id][today] = 0.0
        
        current_usage = self.daily_limits[account_id][today]
        
        if current_usage + amount > settings.DAILY_ACH_LIMIT:
            return {
                'allowed': False,
                'reason': f'Daily ACH limit exceeded. Current: ${current_usage:,.2f}, Limit: ${settings.DAILY_ACH_LIMIT:,.2f}'
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
    
    def _find_transfer_by_trace_number(self, trace_number: str) -> Optional[ACHTransfer]:
        """Find transfer by trace number"""
        for transfer in self.transfers.values():
            if transfer.trace_number == trace_number:
                return transfer
        return None
    
    async def _schedule_transfer_processing(self, transfer_id: str):
        """Schedule transfer for processing on effective date"""
        transfer = self.transfers[transfer_id]
        
        # Calculate delay until effective date
        delay = (transfer.effective_date - datetime.now()).total_seconds()
        
        if delay > 0:
            await asyncio.sleep(delay)
        
        # Process the transfer
        await self._process_transfer(transfer_id)
    
    async def _process_transfer(self, transfer_id: str):
        """Process ACH transfer"""
        try:
            transfer = self.transfers[transfer_id]
            
            if transfer.status != ACHStatus.PENDING:
                return
            
            transfer.status = ACHStatus.PROCESSING
            transfer.processed_at = datetime.now()
            
            # Simulate processing delay
            await asyncio.sleep(2)
            
            # Simulate success/failure (90% success rate)
            import random
            if random.random() > 0.1:
                transfer.status = ACHStatus.COMPLETED
                logger.info(f"ACH transfer completed: {transfer_id}")
            else:
                transfer.status = ACHStatus.FAILED
                transfer.return_code = ACHReturnCode.R01
                transfer.return_reason = "Insufficient Funds"
                logger.warning(f"ACH transfer failed: {transfer_id}")
        
        except Exception as e:
            logger.error(f"Error processing transfer {transfer_id}: {e}")
            transfer.status = ACHStatus.FAILED
    
    def _create_file_header(self) -> str:
        """Create NACHA file header record"""
        return f"101 123456789 {self.company_id}{datetime.now().strftime('%y%m%d%H%M')}A094101ACTIVELOG BANK        ACTIVELOG BANK        12345678"
    
    def _create_batch_header(self, effective_date: datetime) -> str:
        """Create NACHA batch header record"""
        return f"5200ACTIVELOG BANK                      {self.company_id}PPDDEP    {effective_date.strftime('%y%m%d')}   1123456780000001"
    
    def _create_entry_detail(self, transfer: ACHTransfer) -> str:
        """Create NACHA entry detail record"""
        return f"6{transfer.transaction_code.value}{transfer.receiver_routing_number}{transfer.receiver_account_number.ljust(17)}{int(transfer.amount * 100):010d}{transfer.description[:10].ljust(10)}{transfer.trace_number}"
    
    def _create_batch_control(self, transfers: List[ACHTransfer]) -> str:
        """Create NACHA batch control record"""
        entry_count = len(transfers)
        total_debits = sum(int(t.amount * 100) for t in transfers if 'DEBIT' in t.transaction_code.name)
        total_credits = sum(int(t.amount * 100) for t in transfers if 'CREDIT' in t.transaction_code.name)
        
        return f"820000{entry_count:06d}123456780000000000{total_debits:012d}{total_credits:012d}{self.company_id}                         123456780000001"
    
    def _create_file_control(self, transfers: List[ACHTransfer]) -> str:
        """Create NACHA file control record"""
        batch_count = 1
        entry_count = len(transfers)
        total_debits = sum(int(t.amount * 100) for t in transfers if 'DEBIT' in t.transaction_code.name)
        total_credits = sum(int(t.amount * 100) for t in transfers if 'CREDIT' in t.transaction_code.name)
        
        return f"9000001{batch_count:06d}{entry_count:08d}123456780000000000{total_debits:012d}{total_credits:012d}                                       "