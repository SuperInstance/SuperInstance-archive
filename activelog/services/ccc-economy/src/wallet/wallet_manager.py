from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import hashlib
import secrets
from cryptography.fernet import Fernet
import base64

from ..database import (
    CCCWallet, CCCTransaction, User, CCCTransactionType,
    CCCConversion, TaxDeferredAccount
)

logger = logging.getLogger(__name__)

class CCCWalletManager:
    """Comprehensive CCC wallet management system"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption_key = self._get_encryption_key()
        self.min_balance = Decimal('0.00000001')  # Minimum CCC balance
        self.max_balance = Decimal('1000000000.0')  # Maximum CCC balance (1B CCC)
    
    async def create_wallet(
        self,
        user_id: uuid.UUID,
        initial_balance: Decimal = Decimal('0')
    ) -> Dict[str, Any]:
        """Create a new CCC wallet for a user"""
        
        try:
            # Check if user already has a wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.user_id == user_id)
            )
            existing_wallet = result.scalar_one_or_none()
            
            if existing_wallet:
                return {
                    "created": False,
                    "error": "User already has a CCC wallet",
                    "existing_wallet_id": str(existing_wallet.id)
                }
            
            # Generate wallet address and keys
            wallet_address = self._generate_wallet_address()
            private_key = self._generate_private_key()
            private_key_hash = self._encrypt_private_key(private_key)
            
            # Create wallet
            wallet = CCCWallet(
                user_id=user_id,
                balance=initial_balance,
                wallet_address=wallet_address,
                private_key_hash=private_key_hash
            )
            
            self.db.add(wallet)
            await self.db.commit()
            await self.db.refresh(wallet)
            
            # Create initial transaction if there's a balance
            if initial_balance > 0:
                await self._create_transaction(
                    wallet_id=wallet.id,
                    transaction_type=CCCTransactionType.EARN,
                    amount=initial_balance,
                    description="Initial wallet funding"
                )
            
            return {
                "created": True,
                "wallet_id": str(wallet.id),
                "wallet_address": wallet.wallet_address,
                "initial_balance": float(initial_balance),
                "created_at": wallet.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create wallet: {e}")
            raise
    
    async def get_wallet_balance(
        self,
        user_id: Optional[uuid.UUID] = None,
        wallet_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get wallet balance and details"""
        
        try:
            if wallet_id:
                result = await self.db.execute(
                    select(CCCWallet).where(CCCWallet.id == wallet_id)
                )
            elif user_id:
                result = await self.db.execute(
                    select(CCCWallet).where(CCCWallet.user_id == user_id)
                )
            else:
                raise ValueError("Either user_id or wallet_id must be provided")
            
            wallet = result.scalar_one_or_none()
            if not wallet:
                return {"error": "Wallet not found"}
            
            # Calculate available balance
            available_balance = wallet.balance - wallet.locked_balance
            
            return {
                "wallet_id": str(wallet.id),
                "wallet_address": wallet.wallet_address,
                "total_balance": float(wallet.balance),
                "available_balance": float(available_balance),
                "locked_balance": float(wallet.locked_balance),
                "tax_deferred_balance": float(wallet.tax_deferred_balance),
                "lifetime_earned": float(wallet.total_earned),
                "lifetime_invested": float(wallet.total_invested),
                "is_active": wallet.is_active,
                "last_updated": wallet.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet balance: {e}")
            raise
    
    async def transfer_ccc(
        self,
        sender_wallet_id: uuid.UUID,
        recipient_wallet_id: uuid.UUID,
        amount: Decimal,
        description: str = "CCC Transfer",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Transfer CCC between wallets"""
        
        try:
            # Validate amount
            if amount <= 0:
                return {"success": False, "error": "Transfer amount must be positive"}
            
            # Get sender wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == sender_wallet_id)
            )
            sender_wallet = result.scalar_one_or_none()
            if not sender_wallet:
                return {"success": False, "error": "Sender wallet not found"}
            
            # Get recipient wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == recipient_wallet_id)
            )
            recipient_wallet = result.scalar_one_or_none()
            if not recipient_wallet:
                return {"success": False, "error": "Recipient wallet not found"}
            
            # Check sufficient balance
            available_balance = sender_wallet.balance - sender_wallet.locked_balance
            if available_balance < amount:
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "available_balance": float(available_balance),
                    "requested_amount": float(amount)
                }
            
            # Perform transfer
            sender_wallet.balance -= amount
            recipient_wallet.balance += amount
            
            # Create transactions
            sender_tx_id = await self._create_transaction(
                wallet_id=sender_wallet.id,
                transaction_type=CCCTransactionType.TRANSFER,
                amount=-amount,  # Negative for outgoing
                counterparty_wallet_id=recipient_wallet.id,
                description=f"Transfer to {recipient_wallet.wallet_address[:12]}...",
                metadata=metadata
            )
            
            recipient_tx_id = await self._create_transaction(
                wallet_id=recipient_wallet.id,
                transaction_type=CCCTransactionType.TRANSFER,
                amount=amount,  # Positive for incoming
                counterparty_wallet_id=sender_wallet.id,
                description=f"Transfer from {sender_wallet.wallet_address[:12]}...",
                metadata=metadata
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "transfer_amount": float(amount),
                "sender_new_balance": float(sender_wallet.balance),
                "recipient_new_balance": float(recipient_wallet.balance),
                "sender_transaction_id": str(sender_tx_id),
                "recipient_transaction_id": str(recipient_tx_id),
                "transfer_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to transfer CCC: {e}")
            await self.db.rollback()
            raise
    
    async def lock_ccc_for_investment(
        self,
        wallet_id: uuid.UUID,
        amount: Decimal,
        investment_id: uuid.UUID,
        lock_reason: str = "Investment"
    ) -> Dict[str, Any]:
        """Lock CCC for investment purposes"""
        
        try:
            # Get wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == wallet_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                return {"success": False, "error": "Wallet not found"}
            
            # Check available balance
            available_balance = wallet.balance - wallet.locked_balance
            if available_balance < amount:
                return {
                    "success": False,
                    "error": "Insufficient available balance for lock",
                    "available_balance": float(available_balance)
                }
            
            # Lock the amount
            wallet.locked_balance += amount
            wallet.total_invested += amount
            
            # Create transaction record
            tx_id = await self._create_transaction(
                wallet_id=wallet.id,
                transaction_type=CCCTransactionType.INVEST,
                amount=-amount,  # Negative to show it's locked/invested
                investment_id=investment_id,
                description=f"Locked CCC for {lock_reason}",
                metadata={"lock_type": "investment", "investment_id": str(investment_id)}
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "locked_amount": float(amount),
                "new_locked_balance": float(wallet.locked_balance),
                "new_available_balance": float(wallet.balance - wallet.locked_balance),
                "transaction_id": str(tx_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to lock CCC: {e}")
            await self.db.rollback()
            raise
    
    async def unlock_ccc_from_investment(
        self,
        wallet_id: uuid.UUID,
        amount: Decimal,
        investment_id: uuid.UUID,
        unlock_reason: str = "Investment completed"
    ) -> Dict[str, Any]:
        """Unlock CCC from investment"""
        
        try:
            # Get wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == wallet_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                return {"success": False, "error": "Wallet not found"}
            
            # Check locked balance
            if wallet.locked_balance < amount:
                return {
                    "success": False,
                    "error": "Insufficient locked balance",
                    "locked_balance": float(wallet.locked_balance)
                }
            
            # Unlock the amount
            wallet.locked_balance -= amount
            
            # Create transaction record
            tx_id = await self._create_transaction(
                wallet_id=wallet.id,
                transaction_type=CCCTransactionType.INVEST,
                amount=amount,  # Positive to show it's unlocked
                investment_id=investment_id,
                description=f"Unlocked CCC: {unlock_reason}",
                metadata={"unlock_type": "investment", "investment_id": str(investment_id)}
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "unlocked_amount": float(amount),
                "new_locked_balance": float(wallet.locked_balance),
                "new_available_balance": float(wallet.balance - wallet.locked_balance),
                "transaction_id": str(tx_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to unlock CCC: {e}")
            await self.db.rollback()
            raise
    
    async def add_ccc_earnings(
        self,
        wallet_id: uuid.UUID,
        amount: Decimal,
        source: str,
        business_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Add CCC earnings to wallet"""
        
        try:
            # Get wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == wallet_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                return {"success": False, "error": "Wallet not found"}
            
            # Add to balance and lifetime earnings
            wallet.balance += amount
            wallet.total_earned += amount
            
            # Create transaction record
            tx_id = await self._create_transaction(
                wallet_id=wallet.id,
                transaction_type=CCCTransactionType.EARN,
                amount=amount,
                business_id=business_id,
                description=f"Earned CCC from {source}",
                metadata={
                    "earning_source": source,
                    "business_id": str(business_id) if business_id else None,
                    **(metadata or {})
                }
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "earned_amount": float(amount),
                "new_balance": float(wallet.balance),
                "lifetime_earned": float(wallet.total_earned),
                "transaction_id": str(tx_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to add CCC earnings: {e}")
            await self.db.rollback()
            raise
    
    async def spend_ccc(
        self,
        wallet_id: uuid.UUID,
        amount: Decimal,
        purpose: str,
        business_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Spend CCC from wallet"""
        
        try:
            # Get wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == wallet_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                return {"success": False, "error": "Wallet not found"}
            
            # Check available balance
            available_balance = wallet.balance - wallet.locked_balance
            if available_balance < amount:
                return {
                    "success": False,
                    "error": "Insufficient available balance",
                    "available_balance": float(available_balance)
                }
            
            # Deduct from balance
            wallet.balance -= amount
            
            # Create transaction record
            tx_id = await self._create_transaction(
                wallet_id=wallet.id,
                transaction_type=CCCTransactionType.SPEND,
                amount=-amount,  # Negative for spending
                business_id=business_id,
                description=f"Spent CCC on {purpose}",
                metadata={
                    "spending_purpose": purpose,
                    "business_id": str(business_id) if business_id else None,
                    **(metadata or {})
                }
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "spent_amount": float(amount),
                "new_balance": float(wallet.balance),
                "new_available_balance": float(wallet.balance - wallet.locked_balance),
                "transaction_id": str(tx_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to spend CCC: {e}")
            await self.db.rollback()
            raise
    
    async def get_transaction_history(
        self,
        wallet_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
        transaction_types: Optional[List[CCCTransactionType]] = None
    ) -> Dict[str, Any]:
        """Get transaction history for a wallet"""
        
        try:
            # Build query
            query = select(CCCTransaction).where(CCCTransaction.wallet_id == wallet_id)
            
            if transaction_types:
                query = query.where(CCCTransaction.transaction_type.in_(transaction_types))
            
            query = query.order_by(CCCTransaction.created_at.desc()).limit(limit).offset(offset)
            
            # Execute query
            result = await self.db.execute(query)
            transactions = result.scalars().all()
            
            # Format transactions
            transaction_list = []
            for tx in transactions:
                transaction_list.append({
                    "transaction_id": str(tx.id),
                    "type": tx.transaction_type.value,
                    "amount": float(tx.amount),
                    "description": tx.description,
                    "counterparty_wallet_id": str(tx.counterparty_wallet_id) if tx.counterparty_wallet_id else None,
                    "business_id": str(tx.business_id) if tx.business_id else None,
                    "is_confirmed": tx.is_confirmed,
                    "created_at": tx.created_at.isoformat(),
                    "metadata": tx.metadata
                })
            
            # Get total count
            count_query = select(func.count(CCCTransaction.id)).where(CCCTransaction.wallet_id == wallet_id)
            if transaction_types:
                count_query = count_query.where(CCCTransaction.transaction_type.in_(transaction_types))
            
            result = await self.db.execute(count_query)
            total_count = result.scalar()
            
            return {
                "wallet_id": str(wallet_id),
                "transactions": transaction_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_count": total_count,
                    "has_more": offset + limit < total_count
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            raise
    
    async def get_wallet_analytics(
        self,
        wallet_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics for a wallet"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == wallet_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                return {"error": "Wallet not found"}
            
            # Get transactions in period
            result = await self.db.execute(
                select(CCCTransaction).where(
                    and_(
                        CCCTransaction.wallet_id == wallet_id,
                        CCCTransaction.created_at >= start_date
                    )
                )
            )
            transactions = result.scalars().all()
            
            # Calculate analytics
            analytics = {
                "wallet_id": str(wallet_id),
                "period_days": period_days,
                "current_balance": float(wallet.balance),
                "available_balance": float(wallet.balance - wallet.locked_balance),
                "locked_balance": float(wallet.locked_balance)
            }
            
            if transactions:
                # Transaction volume by type
                volume_by_type = {}
                for tx in transactions:
                    tx_type = tx.transaction_type.value
                    if tx_type not in volume_by_type:
                        volume_by_type[tx_type] = {"count": 0, "total_amount": Decimal('0')}
                    volume_by_type[tx_type]["count"] += 1
                    volume_by_type[tx_type]["total_amount"] += abs(tx.amount)
                
                # Convert to serializable format
                for tx_type_data in volume_by_type.values():
                    tx_type_data["total_amount"] = float(tx_type_data["total_amount"])
                
                analytics.update({
                    "period_transaction_count": len(transactions),
                    "volume_by_type": volume_by_type,
                    "most_active_type": max(volume_by_type.items(), key=lambda x: x[1]["count"])[0] if volume_by_type else None,
                    "largest_transaction": float(max((abs(tx.amount) for tx in transactions), default=0))
                })
            else:
                analytics.update({
                    "period_transaction_count": 0,
                    "volume_by_type": {},
                    "most_active_type": None,
                    "largest_transaction": 0
                })
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get wallet analytics: {e}")
            raise
    
    async def validate_wallet_integrity(
        self,
        wallet_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Validate wallet integrity and balance consistency"""
        
        try:
            # Get wallet
            result = await self.db.execute(
                select(CCCWallet).where(CCCWallet.id == wallet_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                return {"valid": False, "error": "Wallet not found"}
            
            # Get all transactions
            result = await self.db.execute(
                select(CCCTransaction).where(CCCTransaction.wallet_id == wallet_id)
            )
            transactions = result.scalars().all()
            
            # Calculate expected balance
            calculated_balance = Decimal('0')
            for tx in transactions:
                calculated_balance += tx.amount
            
            # Check balance consistency
            balance_consistent = abs(calculated_balance - wallet.balance) < self.min_balance
            
            # Validation results
            validation = {
                "wallet_id": str(wallet_id),
                "is_valid": balance_consistent,
                "current_balance": float(wallet.balance),
                "calculated_balance": float(calculated_balance),
                "balance_difference": float(wallet.balance - calculated_balance),
                "total_transactions": len(transactions),
                "locked_balance": float(wallet.locked_balance),
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            if not balance_consistent:
                validation["integrity_issues"] = [
                    f"Balance mismatch: expected {calculated_balance}, actual {wallet.balance}"
                ]
            
            return validation
            
        except Exception as e:
            logger.error(f"Failed to validate wallet integrity: {e}")
            raise
    
    async def _create_transaction(
        self,
        wallet_id: uuid.UUID,
        transaction_type: CCCTransactionType,
        amount: Decimal,
        counterparty_wallet_id: Optional[uuid.UUID] = None,
        business_id: Optional[uuid.UUID] = None,
        investment_id: Optional[uuid.UUID] = None,
        description: str = "",
        metadata: Optional[Dict] = None
    ) -> uuid.UUID:
        """Create a transaction record"""
        
        transaction = CCCTransaction(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            amount=amount,
            counterparty_wallet_id=counterparty_wallet_id,
            business_id=business_id,
            investment_id=investment_id,
            description=description,
            metadata=metadata,
            is_confirmed=True  # For now, all transactions are immediately confirmed
        )
        
        self.db.add(transaction)
        await self.db.flush()  # Get the ID without committing
        
        return transaction.id
    
    def _generate_wallet_address(self) -> str:
        """Generate a unique wallet address"""
        # Generate a unique address (simplified - in production would use proper blockchain addressing)
        random_bytes = secrets.token_bytes(20)
        return "CCC" + base64.b32encode(random_bytes).decode('utf-8')[:32]
    
    def _generate_private_key(self) -> str:
        """Generate a private key"""
        # Generate a secure private key (simplified)
        return secrets.token_hex(32)
    
    def _encrypt_private_key(self, private_key: str) -> str:
        """Encrypt private key for storage"""
        fernet = Fernet(self.encryption_key)
        encrypted_key = fernet.encrypt(private_key.encode())
        return base64.b64encode(encrypted_key).decode('utf-8')
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for private keys"""
        # In production, this would be stored securely (HSM, key vault, etc.)
        key_material = "CCC_WALLET_ENCRYPTION_KEY_PLACEHOLDER"
        return base64.urlsafe_b64encode(hashlib.sha256(key_material.encode()).digest())
    
    async def get_all_wallet_balances(
        self,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get summary of all wallet balances (for admin/analytics)"""
        
        try:
            query = select(CCCWallet)
            if user_id:
                query = query.where(CCCWallet.user_id == user_id)
            
            result = await self.db.execute(query)
            wallets = result.scalars().all()
            
            total_balance = sum(w.balance for w in wallets)
            total_locked = sum(w.locked_balance for w in wallets)
            total_tax_deferred = sum(w.tax_deferred_balance for w in wallets)
            
            return {
                "total_wallets": len(wallets),
                "total_ccc_balance": float(total_balance),
                "total_locked_balance": float(total_locked),
                "total_tax_deferred_balance": float(total_tax_deferred),
                "total_available_balance": float(total_balance - total_locked),
                "active_wallets": len([w for w in wallets if w.is_active]),
                "summary_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet balances summary: {e}")
            raise