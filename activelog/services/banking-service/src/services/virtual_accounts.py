import uuid
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class AccountType(Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money_market"
    CD = "certificate_deposit"
    BUSINESS_CHECKING = "business_checking"
    BUSINESS_SAVINGS = "business_savings"
    ESCROW = "escrow"
    TRUST = "trust"

class AccountStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
    CLOSED = "closed"
    RESTRICTED = "restricted"

class TransactionType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    FEE = "fee"
    INTEREST = "interest"
    ADJUSTMENT = "adjustment"

@dataclass
class VirtualAccount:
    account_id: str
    customer_id: str
    account_number: str
    routing_number: str
    account_type: AccountType
    account_name: str
    balance: Decimal
    available_balance: Decimal
    status: AccountStatus
    created_at: datetime
    updated_at: datetime
    interest_rate: Decimal
    minimum_balance: Decimal
    overdraft_limit: Decimal
    monthly_fee: Decimal
    metadata: Dict

@dataclass
class Transaction:
    transaction_id: str
    account_id: str
    transaction_type: TransactionType
    amount: Decimal
    balance_after: Decimal
    description: str
    reference_number: str
    timestamp: datetime
    status: str
    merchant_info: Optional[Dict]
    location: Optional[Dict]

class VirtualAccountService:
    def __init__(self):
        self.accounts = {}
        self.transactions = {}
        self.account_counter = 1000000
        self.routing_number = "123456789"  # Bank's routing number
    
    async def create_account(self, customer_id: str, account_type: str, account_name: str, 
                           initial_deposit: float = 0.0, metadata: Dict = None) -> Dict:
        """Create a new virtual account"""
        try:
            account_id = str(uuid.uuid4())
            account_number = self._generate_account_number()
            
            # Set account-specific parameters
            interest_rate, min_balance, overdraft_limit, monthly_fee = self._get_account_parameters(account_type)
            
            account = VirtualAccount(
                account_id=account_id,
                customer_id=customer_id,
                account_number=account_number,
                routing_number=self.routing_number,
                account_type=AccountType(account_type),
                account_name=account_name,
                balance=Decimal(str(initial_deposit)),
                available_balance=Decimal(str(initial_deposit)),
                status=AccountStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                interest_rate=Decimal(str(interest_rate)),
                minimum_balance=Decimal(str(min_balance)),
                overdraft_limit=Decimal(str(overdraft_limit)),
                monthly_fee=Decimal(str(monthly_fee)),
                metadata=metadata or {}
            )
            
            self.accounts[account_id] = account
            
            # Record initial deposit transaction if any
            if initial_deposit > 0:
                await self._record_transaction(
                    account_id=account_id,
                    transaction_type=TransactionType.CREDIT,
                    amount=Decimal(str(initial_deposit)),
                    description="Initial deposit",
                    reference_number=f"INIT_{account_id[:8]}"
                )
            
            logger.info(f"Created virtual account: {account_id} for customer: {customer_id}")
            
            return {
                'success': True,
                'account': {
                    'account_id': account_id,
                    'account_number': account_number,
                    'routing_number': self.routing_number,
                    'account_type': account_type,
                    'balance': float(account.balance),
                    'status': account.status.value
                }
            }
        
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_account(self, account_id: str) -> Dict:
        """Get account details"""
        try:
            if account_id not in self.accounts:
                return {'success': False, 'error': 'Account not found'}
            
            account = self.accounts[account_id]
            
            return {
                'success': True,
                'account': {
                    'account_id': account.account_id,
                    'customer_id': account.customer_id,
                    'account_number': account.account_number,
                    'routing_number': account.routing_number,
                    'account_type': account.account_type.value,
                    'account_name': account.account_name,
                    'balance': float(account.balance),
                    'available_balance': float(account.available_balance),
                    'status': account.status.value,
                    'interest_rate': float(account.interest_rate),
                    'minimum_balance': float(account.minimum_balance),
                    'overdraft_limit': float(account.overdraft_limit),
                    'monthly_fee': float(account.monthly_fee),
                    'created_at': account.created_at.isoformat(),
                    'updated_at': account.updated_at.isoformat()
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_customer_accounts(self, customer_id: str) -> List[Dict]:
        """Get all accounts for a customer"""
        try:
            customer_accounts = []
            
            for account in self.accounts.values():
                if account.customer_id == customer_id:
                    customer_accounts.append({
                        'account_id': account.account_id,
                        'account_number': account.account_number,
                        'account_type': account.account_type.value,
                        'account_name': account.account_name,
                        'balance': float(account.balance),
                        'available_balance': float(account.available_balance),
                        'status': account.status.value
                    })
            
            return customer_accounts
        
        except Exception as e:
            logger.error(f"Error getting customer accounts: {e}")
            return []
    
    async def update_balance(self, account_id: str, amount: Decimal, 
                           transaction_type: TransactionType, description: str,
                           reference_number: str = None) -> Dict:
        """Update account balance"""
        try:
            if account_id not in self.accounts:
                return {'success': False, 'error': 'Account not found'}
            
            account = self.accounts[account_id]
            
            if account.status != AccountStatus.ACTIVE:
                return {'success': False, 'error': 'Account is not active'}
            
            # Calculate new balance
            if transaction_type in [TransactionType.DEBIT, TransactionType.TRANSFER_OUT, TransactionType.FEE]:
                new_balance = account.balance - amount
                
                # Check for overdraft
                if new_balance < -account.overdraft_limit:
                    return {'success': False, 'error': 'Insufficient funds'}
            else:
                new_balance = account.balance + amount
            
            # Update account
            old_balance = account.balance
            account.balance = new_balance
            account.available_balance = new_balance  # Simplified - could factor in holds
            account.updated_at = datetime.now()
            
            # Record transaction
            await self._record_transaction(
                account_id=account_id,
                transaction_type=transaction_type,
                amount=amount,
                description=description,
                reference_number=reference_number or f"TXN_{uuid.uuid4().hex[:8].upper()}"
            )
            
            return {
                'success': True,
                'old_balance': float(old_balance),
                'new_balance': float(new_balance),
                'transaction_amount': float(amount)
            }
        
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return {'success': False, 'error': str(e)}
    
    async def freeze_account(self, account_id: str, reason: str) -> Dict:
        """Freeze an account"""
        try:
            if account_id not in self.accounts:
                return {'success': False, 'error': 'Account not found'}
            
            account = self.accounts[account_id]
            account.status = AccountStatus.FROZEN
            account.updated_at = datetime.now()
            account.metadata['freeze_reason'] = reason
            account.metadata['freeze_timestamp'] = datetime.now().isoformat()
            
            logger.warning(f"Account frozen: {account_id}, Reason: {reason}")
            
            return {
                'success': True,
                'account_id': account_id,
                'status': 'frozen',
                'reason': reason
            }
        
        except Exception as e:
            logger.error(f"Error freezing account: {e}")
            return {'success': False, 'error': str(e)}
    
    async def unfreeze_account(self, account_id: str) -> Dict:
        """Unfreeze an account"""
        try:
            if account_id not in self.accounts:
                return {'success': False, 'error': 'Account not found'}
            
            account = self.accounts[account_id]
            account.status = AccountStatus.ACTIVE
            account.updated_at = datetime.now()
            account.metadata['unfreeze_timestamp'] = datetime.now().isoformat()
            
            logger.info(f"Account unfrozen: {account_id}")
            
            return {
                'success': True,
                'account_id': account_id,
                'status': 'active'
            }
        
        except Exception as e:
            logger.error(f"Error unfreezing account: {e}")
            return {'success': False, 'error': str(e)}
    
    async def close_account(self, account_id: str, reason: str) -> Dict:
        """Close an account"""
        try:
            if account_id not in self.accounts:
                return {'success': False, 'error': 'Account not found'}
            
            account = self.accounts[account_id]
            
            # Check if account has positive balance
            if account.balance > Decimal('0'):
                return {'success': False, 'error': 'Cannot close account with positive balance'}
            
            account.status = AccountStatus.CLOSED
            account.updated_at = datetime.now()
            account.metadata['close_reason'] = reason
            account.metadata['close_timestamp'] = datetime.now().isoformat()
            
            logger.info(f"Account closed: {account_id}, Reason: {reason}")
            
            return {
                'success': True,
                'account_id': account_id,
                'status': 'closed',
                'reason': reason,
                'final_balance': float(account.balance)
            }
        
        except Exception as e:
            logger.error(f"Error closing account: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_transaction_history(self, account_id: str, 
                                    start_date: datetime = None,
                                    end_date: datetime = None,
                                    limit: int = 100) -> List[Dict]:
        """Get transaction history for an account"""
        try:
            if account_id not in self.accounts:
                return []
            
            account_transactions = []
            
            for transaction in self.transactions.get(account_id, []):
                if start_date and transaction.timestamp < start_date:
                    continue
                if end_date and transaction.timestamp > end_date:
                    continue
                
                account_transactions.append({
                    'transaction_id': transaction.transaction_id,
                    'transaction_type': transaction.transaction_type.value,
                    'amount': float(transaction.amount),
                    'balance_after': float(transaction.balance_after),
                    'description': transaction.description,
                    'reference_number': transaction.reference_number,
                    'timestamp': transaction.timestamp.isoformat(),
                    'status': transaction.status
                })
            
            # Sort by timestamp (newest first) and limit
            account_transactions.sort(key=lambda x: x['timestamp'], reverse=True)
            return account_transactions[:limit]
        
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []
    
    async def calculate_monthly_fees(self) -> Dict:
        """Calculate and apply monthly fees for all accounts"""
        try:
            fees_applied = []
            
            for account_id, account in self.accounts.items():
                if account.status == AccountStatus.ACTIVE and account.monthly_fee > 0:
                    # Check if minimum balance is maintained to waive fee
                    waive_fee = account.balance >= account.minimum_balance
                    
                    if not waive_fee:
                        fee_result = await self.update_balance(
                            account_id=account_id,
                            amount=account.monthly_fee,
                            transaction_type=TransactionType.FEE,
                            description="Monthly maintenance fee",
                            reference_number=f"FEE_{datetime.now().strftime('%Y%m')}"
                        )
                        
                        fees_applied.append({
                            'account_id': account_id,
                            'fee_amount': float(account.monthly_fee),
                            'applied': fee_result['success']
                        })
            
            return {
                'success': True,
                'fees_applied': fees_applied,
                'total_fees': sum(fee['fee_amount'] for fee in fees_applied if fee['applied'])
            }
        
        except Exception as e:
            logger.error(f"Error calculating monthly fees: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_account_number(self) -> str:
        """Generate a unique account number"""
        self.account_counter += 1
        return str(self.account_counter).zfill(10)
    
    def _get_account_parameters(self, account_type: str) -> Tuple[float, float, float, float]:
        """Get account-specific parameters (interest_rate, min_balance, overdraft_limit, monthly_fee)"""
        parameters = {
            'checking': (settings.CHECKING_INTEREST_RATE, 0.0, 500.0, 10.0),
            'savings': (settings.SAVINGS_INTEREST_RATE, 100.0, 0.0, 5.0),
            'money_market': (settings.SAVINGS_INTEREST_RATE * 1.2, 2500.0, 0.0, 15.0),
            'certificate_deposit': (settings.CD_INTEREST_RATE, 1000.0, 0.0, 0.0),
            'business_checking': (settings.CHECKING_INTEREST_RATE, 500.0, 2000.0, 25.0),
            'business_savings': (settings.SAVINGS_INTEREST_RATE, 500.0, 0.0, 10.0),
            'escrow': (settings.SAVINGS_INTEREST_RATE, 0.0, 0.0, 0.0),
            'trust': (settings.SAVINGS_INTEREST_RATE, 1000.0, 0.0, 20.0)
        }
        
        return parameters.get(account_type, (0.0, 0.0, 0.0, 0.0))
    
    async def _record_transaction(self, account_id: str, transaction_type: TransactionType,
                                 amount: Decimal, description: str, reference_number: str):
        """Record a transaction"""
        try:
            transaction_id = str(uuid.uuid4())
            account = self.accounts[account_id]
            
            transaction = Transaction(
                transaction_id=transaction_id,
                account_id=account_id,
                transaction_type=transaction_type,
                amount=amount,
                balance_after=account.balance,
                description=description,
                reference_number=reference_number,
                timestamp=datetime.now(),
                status="completed",
                merchant_info=None,
                location=None
            )
            
            if account_id not in self.transactions:
                self.transactions[account_id] = []
            
            self.transactions[account_id].append(transaction)
            
        except Exception as e:
            logger.error(f"Error recording transaction: {e}")
    
    async def generate_account_statement(self, account_id: str, 
                                       start_date: datetime, 
                                       end_date: datetime) -> Dict:
        """Generate account statement"""
        try:
            if account_id not in self.accounts:
                return {'success': False, 'error': 'Account not found'}
            
            account = self.accounts[account_id]
            transactions = await self.get_transaction_history(
                account_id, start_date, end_date
            )
            
            # Calculate statement summary
            total_credits = sum(
                t['amount'] for t in transactions 
                if t['transaction_type'] in ['credit', 'transfer_in', 'interest']
            )
            
            total_debits = sum(
                t['amount'] for t in transactions 
                if t['transaction_type'] in ['debit', 'transfer_out', 'fee']
            )
            
            statement = {
                'account_id': account_id,
                'account_number': account.account_number,
                'account_type': account.account_type.value,
                'statement_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'opening_balance': float(account.balance - Decimal(str(total_credits - total_debits))),
                'closing_balance': float(account.balance),
                'total_credits': total_credits,
                'total_debits': total_debits,
                'transaction_count': len(transactions),
                'transactions': transactions,
                'interest_earned': sum(
                    t['amount'] for t in transactions 
                    if t['transaction_type'] == 'interest'
                ),
                'fees_charged': sum(
                    t['amount'] for t in transactions 
                    if t['transaction_type'] == 'fee'
                )
            }
            
            return {
                'success': True,
                'statement': statement
            }
        
        except Exception as e:
            logger.error(f"Error generating statement: {e}")
            return {'success': False, 'error': str(e)}