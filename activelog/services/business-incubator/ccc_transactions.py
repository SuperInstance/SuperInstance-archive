"""
CCC-Only Business Transactions
Comprehensive system for CCC (Community Currency Credit) based business operations
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
import hashlib

class CCCTransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense" 
    INVESTMENT = "investment"
    LOAN = "loan"
    GRANT = "grant"
    TRANSFER = "transfer"
    EXCHANGE = "exchange"

class CCCTransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CCCAccountType(str, Enum):
    BUSINESS_OPERATING = "business_operating"
    BUSINESS_SAVINGS = "business_savings"
    BUSINESS_ESCROW = "business_escrow"
    CUSTOMER_ACCOUNT = "customer_account"
    SUPPLIER_ACCOUNT = "supplier_account"
    INVESTOR_ACCOUNT = "investor_account"

class CCCTransaction(BaseModel):
    """CCC transaction record"""
    id: str
    business_id: str
    type: CCCTransactionType
    amount: float
    description: str
    category: str
    
    # Accounts
    from_account: str
    to_account: str
    from_account_type: CCCAccountType
    to_account_type: CCCAccountType
    
    # Transaction details
    status: CCCTransactionStatus = CCCTransactionStatus.PENDING
    reference_id: Optional[str] = None
    invoice_number: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = []
    attachments: List[str] = []
    notes: str = ""
    
    # Exchange info (if applicable)
    exchange_rate: Optional[float] = None
    fiat_equivalent: Optional[float] = None
    fiat_currency: Optional[str] = None
    
    # Compliance
    requires_approval: bool = False
    approved_by: Optional[str] = None
    tax_category: Optional[str] = None

class CCCAccount(BaseModel):
    """CCC account for business operations"""
    id: str
    business_id: str
    account_type: CCCAccountType
    name: str
    description: str = ""
    
    # Balances
    current_balance: float = 0.0
    available_balance: float = 0.0  # After pending transactions
    reserved_balance: float = 0.0   # Reserved/escrow funds
    
    # Limits
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    minimum_balance: float = 0.0
    
    # Status
    is_active: bool = True
    is_frozen: bool = False
    
    # Timestamps
    created_at: datetime
    last_transaction_at: Optional[datetime] = None

class CCCExchangeRate(BaseModel):
    """Exchange rate for CCC to fiat conversions"""
    id: str
    base_currency: str = "CCC"
    target_currency: str
    rate: float
    
    # Rate metadata
    source: str  # market, manual, algorithm
    timestamp: datetime
    valid_until: datetime
    
    # Market data
    bid_rate: Optional[float] = None
    ask_rate: Optional[float] = None
    volume_24h: Optional[float] = None
    
class CCCSmartContract(BaseModel):
    """Smart contract for automated CCC transactions"""
    id: str
    business_id: str
    name: str
    description: str
    
    # Contract terms
    trigger_conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    
    # Status
    is_active: bool = True
    execution_count: int = 0
    last_executed: Optional[datetime] = None
    
    created_at: datetime

class CCCTransactionManager:
    """Manages CCC-only business transactions"""
    
    def __init__(self):
        self.transactions: Dict[str, CCCTransaction] = {}
        self.accounts: Dict[str, CCCAccount] = {}
        self.exchange_rates: Dict[str, CCCExchangeRate] = {}
        self.smart_contracts: Dict[str, CCCSmartContract] = {}
        self.transaction_history: Dict[str, List[str]] = {}
        
        # Initialize exchange rates
        self._initialize_exchange_rates()
    
    def _initialize_exchange_rates(self):
        """Initialize default exchange rates"""
        default_rates = [
            {"target_currency": "USD", "rate": 1.2},
            {"target_currency": "EUR", "rate": 1.0},
            {"target_currency": "GBP", "rate": 0.85},
            {"target_currency": "CAD", "rate": 1.6},
            {"target_currency": "AUD", "rate": 1.8}
        ]
        
        for rate_data in default_rates:
            rate_id = str(uuid.uuid4())
            exchange_rate = CCCExchangeRate(
                id=rate_id,
                target_currency=rate_data["target_currency"],
                rate=rate_data["rate"],
                source="system",
                timestamp=datetime.now(),
                valid_until=datetime.now() + timedelta(hours=24)
            )
            self.exchange_rates[rate_id] = exchange_rate
    
    def create_business_accounts(self, business_id: str) -> Dict[str, str]:
        """Create default accounts for a business"""
        
        account_templates = [
            {
                "type": CCCAccountType.BUSINESS_OPERATING,
                "name": "Operating Account",
                "description": "Main business operating account",
                "daily_limit": 10000.0,
                "monthly_limit": 100000.0
            },
            {
                "type": CCCAccountType.BUSINESS_SAVINGS,
                "name": "Savings Account", 
                "description": "Business savings and reserves",
                "daily_limit": 5000.0,
                "monthly_limit": 50000.0
            },
            {
                "type": CCCAccountType.BUSINESS_ESCROW,
                "name": "Escrow Account",
                "description": "Escrow for customer deposits and payments",
                "daily_limit": 20000.0,
                "minimum_balance": 1000.0
            }
        ]
        
        created_accounts = {}
        
        for template in account_templates:
            account_id = str(uuid.uuid4())
            
            account = CCCAccount(
                id=account_id,
                business_id=business_id,
                account_type=template["type"],
                name=template["name"],
                description=template["description"],
                daily_limit=template.get("daily_limit"),
                monthly_limit=template.get("monthly_limit"),
                minimum_balance=template.get("minimum_balance", 0.0),
                created_at=datetime.now()
            )
            
            self.accounts[account_id] = account
            created_accounts[template["type"].value] = account_id
        
        return created_accounts
    
    def create_transaction(self, business_id: str, transaction_type: CCCTransactionType,
                          amount: float, description: str, from_account: str,
                          to_account: str, category: str = "general",
                          reference_id: Optional[str] = None) -> str:
        """Create a new CCC transaction"""
        
        # Validate accounts
        if from_account not in self.accounts or to_account not in self.accounts:
            raise ValueError("Invalid account specified")
        
        from_account_obj = self.accounts[from_account]
        to_account_obj = self.accounts[to_account]
        
        # Validate business ownership
        if (from_account_obj.business_id != business_id and 
            to_account_obj.business_id != business_id):
            raise ValueError("Business does not own specified accounts")
        
        # Check account limits and balances
        validation_result = self._validate_transaction(from_account_obj, amount, transaction_type)
        if not validation_result["valid"]:
            raise ValueError(validation_result["error"])
        
        transaction_id = str(uuid.uuid4())
        
        transaction = CCCTransaction(
            id=transaction_id,
            business_id=business_id,
            type=transaction_type,
            amount=amount,
            description=description,
            category=category,
            from_account=from_account,
            to_account=to_account,
            from_account_type=from_account_obj.account_type,
            to_account_type=to_account_obj.account_type,
            reference_id=reference_id,
            created_at=datetime.now()
        )
        
        # Check if approval required
        transaction.requires_approval = self._requires_approval(transaction)
        
        self.transactions[transaction_id] = transaction
        
        # Add to business transaction history
        if business_id not in self.transaction_history:
            self.transaction_history[business_id] = []
        self.transaction_history[business_id].append(transaction_id)
        
        # Auto-confirm if no approval needed
        if not transaction.requires_approval:
            self._confirm_transaction(transaction_id)
        
        return transaction_id
    
    def _validate_transaction(self, from_account: CCCAccount, amount: float,
                             transaction_type: CCCTransactionType) -> Dict[str, Any]:
        """Validate transaction against account constraints"""
        
        result = {"valid": True, "error": ""}
        
        # Check account status
        if not from_account.is_active:
            return {"valid": False, "error": "Account is inactive"}
        
        if from_account.is_frozen:
            return {"valid": False, "error": "Account is frozen"}
        
        # Check balance
        if from_account.available_balance < amount:
            return {"valid": False, "error": "Insufficient balance"}
        
        # Check daily limits
        if from_account.daily_limit:
            daily_total = self._get_daily_transaction_total(from_account.id)
            if daily_total + amount > from_account.daily_limit:
                return {"valid": False, "error": "Daily limit exceeded"}
        
        # Check monthly limits
        if from_account.monthly_limit:
            monthly_total = self._get_monthly_transaction_total(from_account.id)
            if monthly_total + amount > from_account.monthly_limit:
                return {"valid": False, "error": "Monthly limit exceeded"}
        
        # Check minimum balance
        if (from_account.current_balance - amount) < from_account.minimum_balance:
            return {"valid": False, "error": "Would violate minimum balance requirement"}
        
        return result
    
    def _get_daily_transaction_total(self, account_id: str) -> float:
        """Get total transactions for account today"""
        today = datetime.now().date()
        total = 0.0
        
        for transaction in self.transactions.values():
            if (transaction.from_account == account_id and 
                transaction.status == CCCTransactionStatus.CONFIRMED and
                transaction.confirmed_at and
                transaction.confirmed_at.date() == today):
                total += transaction.amount
        
        return total
    
    def _get_monthly_transaction_total(self, account_id: str) -> float:
        """Get total transactions for account this month"""
        current_month = datetime.now().replace(day=1)
        total = 0.0
        
        for transaction in self.transactions.values():
            if (transaction.from_account == account_id and 
                transaction.status == CCCTransactionStatus.CONFIRMED and
                transaction.confirmed_at and
                transaction.confirmed_at >= current_month):
                total += transaction.amount
        
        return total
    
    def _requires_approval(self, transaction: CCCTransaction) -> bool:
        """Check if transaction requires approval"""
        
        # Large amounts require approval
        if transaction.amount > 5000.0:
            return True
        
        # Investment transactions require approval
        if transaction.type == CCCTransactionType.INVESTMENT:
            return True
        
        # Loans require approval
        if transaction.type == CCCTransactionType.LOAN:
            return True
        
        # Cross-business transfers require approval
        from_account = self.accounts[transaction.from_account]
        to_account = self.accounts[transaction.to_account]
        
        if from_account.business_id != to_account.business_id:
            return True
        
        return False
    
    def _confirm_transaction(self, transaction_id: str):
        """Confirm and execute transaction"""
        
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        
        if transaction.status != CCCTransactionStatus.PENDING:
            raise ValueError("Transaction already processed")
        
        # Update account balances
        from_account = self.accounts[transaction.from_account]
        to_account = self.accounts[transaction.to_account]
        
        from_account.current_balance -= transaction.amount
        from_account.available_balance -= transaction.amount
        from_account.last_transaction_at = datetime.now()
        
        to_account.current_balance += transaction.amount
        to_account.available_balance += transaction.amount
        to_account.last_transaction_at = datetime.now()
        
        # Update transaction status
        transaction.status = CCCTransactionStatus.CONFIRMED
        transaction.confirmed_at = datetime.now()
        
        # Execute any triggered smart contracts
        self._check_smart_contract_triggers(transaction)
    
    def approve_transaction(self, transaction_id: str, approved_by: str) -> bool:
        """Approve pending transaction"""
        
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        
        if not transaction.requires_approval:
            raise ValueError("Transaction does not require approval")
        
        if transaction.status != CCCTransactionStatus.PENDING:
            raise ValueError("Transaction already processed")
        
        transaction.approved_by = approved_by
        self._confirm_transaction(transaction_id)
        
        return True
    
    def cancel_transaction(self, transaction_id: str, reason: str = "") -> bool:
        """Cancel pending transaction"""
        
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        
        if transaction.status != CCCTransactionStatus.PENDING:
            raise ValueError("Cannot cancel processed transaction")
        
        transaction.status = CCCTransactionStatus.CANCELLED
        transaction.notes = f"Cancelled: {reason}"
        
        return True
    
    def get_account_balance(self, account_id: str) -> Dict[str, float]:
        """Get account balance information"""
        
        account = self.accounts.get(account_id)
        if not account:
            raise ValueError("Account not found")
        
        return {
            "current_balance": account.current_balance,
            "available_balance": account.available_balance,
            "reserved_balance": account.reserved_balance,
            "minimum_balance": account.minimum_balance
        }
    
    def get_business_accounts(self, business_id: str) -> List[Dict[str, Any]]:
        """Get all accounts for a business"""
        
        business_accounts = []
        
        for account in self.accounts.values():
            if account.business_id == business_id:
                business_accounts.append({
                    "id": account.id,
                    "type": account.account_type.value,
                    "name": account.name,
                    "description": account.description,
                    "current_balance": account.current_balance,
                    "available_balance": account.available_balance,
                    "is_active": account.is_active,
                    "is_frozen": account.is_frozen,
                    "daily_limit": account.daily_limit,
                    "monthly_limit": account.monthly_limit,
                    "last_transaction_at": account.last_transaction_at.isoformat() if account.last_transaction_at else None
                })
        
        return business_accounts
    
    def get_transaction_history(self, business_id: str, limit: int = 100,
                               account_id: Optional[str] = None,
                               transaction_type: Optional[CCCTransactionType] = None) -> List[Dict[str, Any]]:
        """Get transaction history for business"""
        
        transactions = []
        
        for transaction_id in self.transaction_history.get(business_id, []):
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                continue
            
            # Apply filters
            if account_id and transaction.from_account != account_id and transaction.to_account != account_id:
                continue
            
            if transaction_type and transaction.type != transaction_type:
                continue
            
            transactions.append({
                "id": transaction.id,
                "type": transaction.type.value,
                "amount": transaction.amount,
                "description": transaction.description,
                "category": transaction.category,
                "from_account": transaction.from_account,
                "to_account": transaction.to_account,
                "status": transaction.status.value,
                "created_at": transaction.created_at.isoformat(),
                "confirmed_at": transaction.confirmed_at.isoformat() if transaction.confirmed_at else None,
                "reference_id": transaction.reference_id,
                "tags": transaction.tags,
                "fiat_equivalent": transaction.fiat_equivalent,
                "fiat_currency": transaction.fiat_currency
            })
        
        # Sort by date descending
        transactions.sort(key=lambda t: t["created_at"], reverse=True)
        
        return transactions[:limit]
    
    def calculate_fiat_equivalent(self, ccc_amount: float, target_currency: str) -> Tuple[float, float]:
        """Calculate fiat equivalent for CCC amount"""
        
        # Find current exchange rate
        current_rate = None
        for rate in self.exchange_rates.values():
            if (rate.target_currency == target_currency and 
                rate.valid_until > datetime.now()):
                if current_rate is None or rate.timestamp > current_rate.timestamp:
                    current_rate = rate
        
        if not current_rate:
            raise ValueError(f"No exchange rate available for {target_currency}")
        
        fiat_amount = ccc_amount * current_rate.rate
        return fiat_amount, current_rate.rate
    
    def create_smart_contract(self, business_id: str, name: str, description: str,
                            trigger_conditions: List[Dict[str, Any]],
                            actions: List[Dict[str, Any]]) -> str:
        """Create smart contract for automated transactions"""
        
        contract_id = str(uuid.uuid4())
        
        contract = CCCSmartContract(
            id=contract_id,
            business_id=business_id,
            name=name,
            description=description,
            trigger_conditions=trigger_conditions,
            actions=actions,
            created_at=datetime.now()
        )
        
        self.smart_contracts[contract_id] = contract
        return contract_id
    
    def _check_smart_contract_triggers(self, transaction: CCCTransaction):
        """Check if transaction triggers any smart contracts"""
        
        for contract in self.smart_contracts.values():
            if not contract.is_active or contract.business_id != transaction.business_id:
                continue
            
            # Check trigger conditions
            triggered = self._evaluate_trigger_conditions(contract.trigger_conditions, transaction)
            
            if triggered:
                self._execute_smart_contract(contract, transaction)
    
    def _evaluate_trigger_conditions(self, conditions: List[Dict[str, Any]], 
                                   transaction: CCCTransaction) -> bool:
        """Evaluate smart contract trigger conditions"""
        
        for condition in conditions:
            condition_type = condition.get("type")
            
            if condition_type == "transaction_amount":
                operator = condition.get("operator", ">=")
                threshold = condition.get("value", 0)
                
                if operator == ">=" and transaction.amount >= threshold:
                    continue
                elif operator == ">" and transaction.amount > threshold:
                    continue
                elif operator == "<=" and transaction.amount <= threshold:
                    continue
                elif operator == "<" and transaction.amount < threshold:
                    continue
                elif operator == "==" and transaction.amount == threshold:
                    continue
                else:
                    return False
            
            elif condition_type == "transaction_type":
                required_type = condition.get("value")
                if transaction.type.value != required_type:
                    return False
            
            elif condition_type == "account_balance":
                account_id = condition.get("account_id")
                operator = condition.get("operator", ">=")
                threshold = condition.get("value", 0)
                
                if account_id not in self.accounts:
                    return False
                
                balance = self.accounts[account_id].current_balance
                
                if operator == ">=" and balance >= threshold:
                    continue
                elif operator == ">" and balance > threshold:
                    continue
                elif operator == "<=" and balance <= threshold:
                    continue
                elif operator == "<" and balance < threshold:
                    continue
                else:
                    return False
        
        return True
    
    def _execute_smart_contract(self, contract: CCCSmartContract, trigger_transaction: CCCTransaction):
        """Execute smart contract actions"""
        
        for action in contract.actions:
            action_type = action.get("type")
            
            if action_type == "create_transaction":
                # Create automated transaction
                try:
                    self.create_transaction(
                        business_id=contract.business_id,
                        transaction_type=CCCTransactionType(action.get("transaction_type", "transfer")),
                        amount=action.get("amount", 0),
                        description=f"Smart contract: {contract.name}",
                        from_account=action.get("from_account"),
                        to_account=action.get("to_account"),
                        category=action.get("category", "automated"),
                        reference_id=trigger_transaction.id
                    )
                except Exception as e:
                    # Log error but don't fail the original transaction
                    print(f"Smart contract execution error: {e}")
            
            elif action_type == "send_notification":
                # Would integrate with notification system
                pass
            
            elif action_type == "update_account_limit":
                account_id = action.get("account_id")
                limit_type = action.get("limit_type", "daily_limit")
                new_limit = action.get("new_limit", 0)
                
                if account_id in self.accounts:
                    setattr(self.accounts[account_id], limit_type, new_limit)
        
        # Update contract execution stats
        contract.execution_count += 1
        contract.last_executed = datetime.now()
    
    def get_ccc_analytics(self, business_id: str) -> Dict[str, Any]:
        """Get CCC transaction analytics for business"""
        
        business_transactions = [
            t for t in self.transactions.values() 
            if t.business_id == business_id and t.status == CCCTransactionStatus.CONFIRMED
        ]
        
        if not business_transactions:
            return {"message": "No confirmed transactions found"}
        
        # Calculate totals by type
        totals_by_type = {}
        for transaction in business_transactions:
            transaction_type = transaction.type.value
            if transaction_type not in totals_by_type:
                totals_by_type[transaction_type] = 0
            totals_by_type[transaction_type] += transaction.amount
        
        # Calculate monthly trends
        monthly_totals = {}
        for transaction in business_transactions:
            month_key = transaction.confirmed_at.strftime("%Y-%m")
            if month_key not in monthly_totals:
                monthly_totals[month_key] = {"income": 0, "expense": 0, "net": 0}
            
            if transaction.type == CCCTransactionType.INCOME:
                monthly_totals[month_key]["income"] += transaction.amount
                monthly_totals[month_key]["net"] += transaction.amount
            elif transaction.type == CCCTransactionType.EXPENSE:
                monthly_totals[month_key]["expense"] += transaction.amount
                monthly_totals[month_key]["net"] -= transaction.amount
        
        # Account balances
        accounts = self.get_business_accounts(business_id)
        total_balance = sum(account["current_balance"] for account in accounts)
        
        return {
            "total_ccc_balance": total_balance,
            "transaction_count": len(business_transactions),
            "totals_by_type": totals_by_type,
            "monthly_trends": monthly_totals,
            "accounts": accounts,
            "average_transaction_size": sum(t.amount for t in business_transactions) / len(business_transactions),
            "largest_transaction": max(business_transactions, key=lambda t: t.amount).amount,
            "most_recent_transaction": max(business_transactions, key=lambda t: t.confirmed_at).confirmed_at.isoformat()
        }