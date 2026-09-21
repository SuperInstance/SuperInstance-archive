"""
Compute Credit (CC) System Implementation
Multi-currency support with automatic conversion
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.database import User, Transaction, CurrencyExchangeRate, TransactionType, TransactionStatus
from ...config.settings import settings
from ..exchange.currency_converter import CurrencyConverter

logger = logging.getLogger(__name__)

class ComputeCreditSystem:
    """Core Compute Credit (CC) system for financial operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.currency_converter = CurrencyConverter()
        self.base_currency = settings.compute_credits.base_currency
        self.cc_to_usd_rate = settings.compute_credits.cc_to_usd_rate
        
    async def get_user_balance(self, user_id: str) -> Decimal:
        """Get user's current CC balance"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        return user.cc_balance or Decimal("0")
    
    async def add_credits(
        self,
        user_id: str,
        amount_cc: Decimal,
        transaction_type: TransactionType = TransactionType.CREDIT,
        description: str = "Credit added",
        external_transaction_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Transaction:
        """Add CC credits to user account"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate amount
        if amount_cc <= 0:
            raise ValueError("Credit amount must be positive")
        
        # Check maximum balance limit
        new_balance = user.cc_balance + amount_cc
        if new_balance > settings.compute_credits.maximum_balance:
            raise ValueError(f"Credit would exceed maximum balance of {settings.compute_credits.maximum_balance} CC")
        
        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=transaction_type,
            status=TransactionStatus.PENDING,
            amount_cc=amount_cc,
            description=description,
            external_transaction_id=external_transaction_id,
            metadata=metadata or {}
        )
        
        try:
            # Update user balance
            user.cc_balance = new_balance
            
            # Complete transaction
            transaction.status = TransactionStatus.COMPLETED
            transaction.processed_at = datetime.utcnow()
            
            self.db.add(transaction)
            self.db.commit()
            
            logger.info(f"Added {amount_cc} CC to user {user_id}. New balance: {new_balance} CC")
            
            return transaction
            
        except Exception as e:
            self.db.rollback()
            transaction.status = TransactionStatus.FAILED
            self.db.add(transaction)
            self.db.commit()
            
            logger.error(f"Failed to add credits to user {user_id}: {str(e)}")
            raise
    
    async def deduct_credits(
        self,
        user_id: str,
        amount_cc: Decimal,
        transaction_type: TransactionType = TransactionType.DEBIT,
        description: str = "Credit deducted",
        allow_negative: bool = False,
        metadata: Optional[Dict] = None
    ) -> Transaction:
        """Deduct CC credits from user account"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate amount
        if amount_cc <= 0:
            raise ValueError("Debit amount must be positive")
        
        # Check sufficient balance
        if not allow_negative and user.cc_balance < amount_cc:
            raise ValueError(f"Insufficient balance. Current: {user.cc_balance} CC, Required: {amount_cc} CC")
        
        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=transaction_type,
            status=TransactionStatus.PENDING,
            amount_cc=-amount_cc,  # Negative for debit
            description=description,
            metadata=metadata or {}
        )
        
        try:
            # Update user balance
            new_balance = user.cc_balance - amount_cc
            user.cc_balance = new_balance
            
            # Complete transaction
            transaction.status = TransactionStatus.COMPLETED
            transaction.processed_at = datetime.utcnow()
            
            self.db.add(transaction)
            self.db.commit()
            
            logger.info(f"Deducted {amount_cc} CC from user {user_id}. New balance: {new_balance} CC")
            
            return transaction
            
        except Exception as e:
            self.db.rollback()
            transaction.status = TransactionStatus.FAILED
            self.db.add(transaction)
            self.db.commit()
            
            logger.error(f"Failed to deduct credits from user {user_id}: {str(e)}")
            raise
    
    async def transfer_credits(
        self,
        from_user_id: str,
        to_user_id: str,
        amount_cc: Decimal,
        description: str = "Credit transfer",
        metadata: Optional[Dict] = None
    ) -> Tuple[Transaction, Transaction]:
        """Transfer CC credits between users"""
        
        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer credits to the same user")
        
        # Validate users exist
        from_user = self.db.query(User).filter(User.id == from_user_id).first()
        to_user = self.db.query(User).filter(User.id == to_user_id).first()
        
        if not from_user:
            raise ValueError(f"From user {from_user_id} not found")
        if not to_user:
            raise ValueError(f"To user {to_user_id} not found")
        
        # Validate amount
        if amount_cc <= 0:
            raise ValueError("Transfer amount must be positive")
        
        # Check sufficient balance
        if from_user.cc_balance < amount_cc:
            raise ValueError(f"Insufficient balance for transfer. Current: {from_user.cc_balance} CC, Required: {amount_cc} CC")
        
        # Check maximum balance for recipient
        if to_user.cc_balance + amount_cc > settings.compute_credits.maximum_balance:
            raise ValueError(f"Transfer would exceed maximum balance for recipient")
        
        transfer_metadata = metadata or {}
        transfer_metadata.update({
            "transfer_from": from_user_id,
            "transfer_to": to_user_id,
            "transfer_amount": str(amount_cc)
        })
        
        try:
            # Deduct from sender
            debit_transaction = await self.deduct_credits(
                from_user_id,
                amount_cc,
                TransactionType.TRANSFER,
                f"Transfer to {to_user.username}: {description}",
                metadata=transfer_metadata
            )
            
            # Add to recipient
            credit_transaction = await self.add_credits(
                to_user_id,
                amount_cc,
                TransactionType.TRANSFER,
                f"Transfer from {from_user.username}: {description}",
                metadata=transfer_metadata
            )
            
            logger.info(f"Transferred {amount_cc} CC from {from_user_id} to {to_user_id}")
            
            return debit_transaction, credit_transaction
            
        except Exception as e:
            logger.error(f"Failed to transfer credits: {str(e)}")
            raise
    
    async def convert_to_cc(
        self,
        amount: Decimal,
        from_currency: str,
        user_id: Optional[str] = None
    ) -> Decimal:
        """Convert currency amount to CC"""
        
        if from_currency == "CC":
            return amount
        
        # Get exchange rate to USD first
        if from_currency != "USD":
            usd_amount = await self.currency_converter.convert(
                amount, from_currency, "USD"
            )
        else:
            usd_amount = amount
        
        # Convert USD to CC
        cc_amount = usd_amount / self.cc_to_usd_rate
        
        # Round to 8 decimal places
        cc_amount = cc_amount.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        
        logger.info(f"Converted {amount} {from_currency} to {cc_amount} CC (via {usd_amount} USD)")
        
        return cc_amount
    
    async def convert_from_cc(
        self,
        amount_cc: Decimal,
        to_currency: str,
        user_id: Optional[str] = None
    ) -> Decimal:
        """Convert CC amount to currency"""
        
        if to_currency == "CC":
            return amount_cc
        
        # Convert CC to USD first
        usd_amount = amount_cc * self.cc_to_usd_rate
        
        # Convert USD to target currency
        if to_currency != "USD":
            converted_amount = await self.currency_converter.convert(
                usd_amount, "USD", to_currency
            )
        else:
            converted_amount = usd_amount
        
        logger.info(f"Converted {amount_cc} CC to {converted_amount} {to_currency} (via {usd_amount} USD)")
        
        return converted_amount
    
    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """Get user's transaction history"""
        
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if transaction_type:
            query = query.filter(Transaction.type == transaction_type)
        
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)
        
        transactions = (
            query.order_by(desc(Transaction.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return transactions
    
    async def get_balance_summary(self, user_id: str) -> Dict:
        """Get comprehensive balance summary for user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get transaction summaries for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_transactions = (
            self.db.query(
                Transaction.type,
                func.sum(Transaction.amount_cc).label("total_amount"),
                func.count(Transaction.id).label("transaction_count")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= thirty_days_ago,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            )
            .group_by(Transaction.type)
            .all()
        )
        
        # Calculate totals
        total_credits = Decimal("0")
        total_debits = Decimal("0")
        
        transaction_summary = {}
        for trans_type, total_amount, count in recent_transactions:
            transaction_summary[trans_type.value] = {
                "total_amount": total_amount,
                "transaction_count": count
            }
            
            if total_amount > 0:
                total_credits += total_amount
            else:
                total_debits += abs(total_amount)
        
        # Convert balance to user's preferred currency
        balance_in_preferred_currency = await self.convert_from_cc(
            user.cc_balance, user.preferred_currency
        )
        
        return {
            "user_id": user_id,
            "cc_balance": user.cc_balance,
            "preferred_currency": user.preferred_currency,
            "balance_in_preferred_currency": balance_in_preferred_currency,
            "minimum_balance": settings.compute_credits.minimum_balance,
            "maximum_balance": settings.compute_credits.maximum_balance,
            "last_30_days": {
                "total_credits": total_credits,
                "total_debits": total_debits,
                "net_change": total_credits - total_debits,
                "transaction_summary": transaction_summary
            }
        }
    
    async def award_signup_bonus(self, user_id: str) -> Transaction:
        """Award free credits to new users"""
        
        # Check if user already received signup bonus
        existing_bonus = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.REWARD,
                    Transaction.description.contains("signup bonus")
                )
            )
            .first()
        )
        
        if existing_bonus:
            raise ValueError("User has already received signup bonus")
        
        return await self.add_credits(
            user_id,
            settings.compute_credits.free_tier_credits,
            TransactionType.REWARD,
            "Welcome signup bonus",
            metadata={"bonus_type": "signup", "amount": str(settings.compute_credits.free_tier_credits)}
        )
    
    async def process_pending_transactions(self) -> int:
        """Process pending transactions (cleanup job)"""
        
        # Find old pending transactions (older than 1 hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        pending_transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.status == TransactionStatus.PENDING,
                    Transaction.created_at < one_hour_ago
                )
            )
            .all()
        )
        
        processed_count = 0
        
        for transaction in pending_transactions:
            try:
                # Mark as failed after timeout
                transaction.status = TransactionStatus.FAILED
                transaction.processed_at = datetime.utcnow()
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process pending transaction {transaction.id}: {str(e)}")
        
        self.db.commit()
        
        logger.info(f"Processed {processed_count} pending transactions")
        return processed_count
    
    async def validate_transaction(self, transaction_id: str) -> bool:
        """Validate transaction integrity"""
        
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            return False
        
        user = self.db.query(User).filter(User.id == transaction.user_id).first()
        if not user:
            return False
        
        # Additional validation logic here
        # Check for double-spending, balance consistency, etc.
        
        return True