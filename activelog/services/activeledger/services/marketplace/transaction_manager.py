"""
Marketplace Transaction System
Manages secure transactions between makers and buyers with escrow, CC payments, and dispute resolution
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.database import (
    User, MarketplaceTransaction, MarketplaceListing, Transaction, MarketplaceTransactionStatus,
    MarketplaceTransactionType, MarketplaceDisputeStatus, TransactionType, TransactionStatus
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem

logger = logging.getLogger(__name__)

class EscrowStatus(Enum):
    """Escrow transaction statuses"""
    PENDING = "pending"
    FUNDED = "funded"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

class MarketplaceTransactionManager:
    """Manages secure marketplace transactions with escrow system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        self.platform_fee_rate = settings.marketplace.platform_fee_rate
        self.dispute_timeout_days = settings.marketplace.dispute_timeout_days
        self.auto_release_days = settings.marketplace.auto_release_days
    
    async def create_purchase_transaction(
        self,
        buyer_id: str,
        listing_id: str,
        quantity: int = 1,
        delivery_address: Optional[Dict] = None,
        special_instructions: Optional[str] = None
    ) -> MarketplaceTransaction:
        """Create a new purchase transaction with escrow"""
        
        # Verify buyer exists
        buyer = self.db.query(User).filter(User.id == buyer_id).first()
        if not buyer:
            raise ValueError(f"Buyer {buyer_id} not found")
        
        # Verify listing exists and is active
        listing = self.db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")
        
        if not listing.is_active:
            raise ValueError("Listing is not active")
        
        if listing.quantity < quantity:
            raise ValueError(f"Insufficient quantity available. Requested: {quantity}, Available: {listing.quantity}")
        
        # Prevent self-purchase
        if buyer_id == listing.seller_id:
            raise ValueError("Cannot purchase your own listing")
        
        # Calculate costs
        item_total_cc = listing.price_cc * quantity
        platform_fee_cc = item_total_cc * self.platform_fee_rate
        total_cost_cc = item_total_cc + platform_fee_cc
        
        # Check buyer balance
        buyer_balance = await self.cc_system.get_user_balance(buyer_id)
        if buyer_balance < total_cost_cc:
            raise ValueError(
                f"Insufficient balance. Required: {total_cost_cc} CC, Available: {buyer_balance} CC"
            )
        
        # Create marketplace transaction
        transaction = MarketplaceTransaction(
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            listing_id=listing_id,
            quantity=quantity,
            item_price_cc=listing.price_cc,
            item_total_cc=item_total_cc,
            platform_fee_cc=platform_fee_cc,
            total_cost_cc=total_cost_cc,
            status=MarketplaceTransactionStatus.PENDING,
            transaction_type=MarketplaceTransactionType.PURCHASE,
            delivery_address=delivery_address,
            special_instructions=special_instructions,
            escrow_funded_at=None,
            expected_delivery_date=datetime.utcnow() + timedelta(days=listing.estimated_delivery_days)
        )
        
        try:
            # Place funds in escrow (deduct from buyer balance)
            await self.cc_system.deduct_credits(
                buyer_id,
                total_cost_cc,
                TransactionType.ESCROW,
                f"Escrow payment for marketplace purchase: {listing.title}",
                metadata={
                    "marketplace_transaction_id": str(transaction.id),
                    "listing_id": listing_id,
                    "seller_id": listing.seller_id,
                    "quantity": quantity,
                    "item_price_cc": str(listing.price_cc),
                    "platform_fee_cc": str(platform_fee_cc),
                    "escrow_status": EscrowStatus.FUNDED.value
                }
            )
            
            # Update transaction status
            transaction.status = MarketplaceTransactionStatus.PAYMENT_RECEIVED
            transaction.escrow_funded_at = datetime.utcnow()
            
            # Reserve inventory
            listing.quantity -= quantity
            listing.sales_count += quantity
            
            self.db.add(transaction)
            self.db.commit()
            
            logger.info(
                f"Created marketplace transaction: buyer {buyer_id} purchased {quantity}x "
                f"{listing.title} for {total_cost_cc} CC (including {platform_fee_cc} CC platform fee)"
            )
            
            return transaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create marketplace transaction: {str(e)}")
            raise
    
    async def confirm_shipment(
        self,
        transaction_id: str,
        seller_id: str,
        tracking_number: Optional[str] = None,
        carrier: Optional[str] = None,
        shipment_notes: Optional[str] = None
    ) -> MarketplaceTransaction:
        """Confirm shipment of goods by seller"""
        
        transaction = (
            self.db.query(MarketplaceTransaction)
            .filter(
                and_(
                    MarketplaceTransaction.id == transaction_id,
                    MarketplaceTransaction.seller_id == seller_id
                )
            )
            .first()
        )
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found for seller {seller_id}")
        
        if transaction.status != MarketplaceTransactionStatus.PAYMENT_RECEIVED:
            raise ValueError(f"Transaction is in {transaction.status.value} status, cannot confirm shipment")
        
        # Update transaction with shipment details
        transaction.status = MarketplaceTransactionStatus.SHIPPED
        transaction.tracking_number = tracking_number
        transaction.carrier = carrier
        transaction.shipment_notes = shipment_notes
        transaction.shipped_at = datetime.utcnow()
        
        # Set auto-release date (funds will be released automatically if not disputed)
        transaction.auto_release_at = datetime.utcnow() + timedelta(days=self.auto_release_days)
        
        self.db.commit()
        
        logger.info(
            f"Confirmed shipment for transaction {transaction_id}: "
            f"tracking {tracking_number} via {carrier}"
        )
        
        return transaction
    
    async def confirm_delivery(
        self,
        transaction_id: str,
        buyer_id: str,
        delivery_rating: int = 5,
        delivery_notes: Optional[str] = None
    ) -> MarketplaceTransaction:
        """Confirm delivery and release escrow funds to seller"""
        
        transaction = (
            self.db.query(MarketplaceTransaction)
            .filter(
                and_(
                    MarketplaceTransaction.id == transaction_id,
                    MarketplaceTransaction.buyer_id == buyer_id
                )
            )
            .first()
        )
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found for buyer {buyer_id}")
        
        if transaction.status not in [MarketplaceTransactionStatus.SHIPPED, MarketplaceTransactionStatus.DELIVERED]:
            raise ValueError(f"Transaction is in {transaction.status.value} status, cannot confirm delivery")
        
        # Validate rating
        if not 1 <= delivery_rating <= 5:
            raise ValueError("Delivery rating must be between 1 and 5")
        
        try:
            # Release funds to seller (minus platform fee)
            seller_amount = transaction.item_total_cc
            
            await self.cc_system.add_credits(
                transaction.seller_id,
                seller_amount,
                TransactionType.MARKETPLACE_SALE,
                f"Marketplace sale payment: {transaction.listing.title}",
                metadata={
                    "marketplace_transaction_id": transaction_id,
                    "buyer_id": buyer_id,
                    "quantity": transaction.quantity,
                    "gross_amount_cc": str(transaction.total_cost_cc),
                    "platform_fee_cc": str(transaction.platform_fee_cc),
                    "net_amount_cc": str(seller_amount),
                    "escrow_release": True
                }
            )
            
            # Update transaction status
            transaction.status = MarketplaceTransactionStatus.COMPLETED
            transaction.delivered_at = datetime.utcnow()
            transaction.delivery_rating = delivery_rating
            transaction.delivery_notes = delivery_notes
            transaction.completed_at = datetime.utcnow()
            
            # Update seller stats
            seller = self.db.query(User).filter(User.id == transaction.seller_id).first()
            if seller:
                seller.marketplace_sales_count += 1
                seller.marketplace_total_earnings_cc += seller_amount
                
                # Update seller rating (simple average)
                if seller.marketplace_rating:
                    seller.marketplace_rating = (
                        (seller.marketplace_rating * (seller.marketplace_sales_count - 1) + delivery_rating)
                        / seller.marketplace_sales_count
                    )
                else:
                    seller.marketplace_rating = delivery_rating
            
            self.db.commit()
            
            logger.info(
                f"Completed marketplace transaction {transaction_id}: "
                f"released {seller_amount} CC to seller {transaction.seller_id}"
            )
            
            return transaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to complete marketplace transaction {transaction_id}: {str(e)}")
            raise
    
    async def initiate_dispute(
        self,
        transaction_id: str,
        initiator_id: str,
        dispute_reason: str,
        dispute_details: str,
        evidence_urls: Optional[List[str]] = None
    ) -> MarketplaceTransaction:
        """Initiate a dispute for a transaction"""
        
        transaction = (
            self.db.query(MarketplaceTransaction)
            .filter(MarketplaceTransaction.id == transaction_id)
            .first()
        )
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        # Verify initiator is buyer or seller
        if initiator_id not in [transaction.buyer_id, transaction.seller_id]:
            raise ValueError("Only buyer or seller can initiate disputes")
        
        if transaction.status in [MarketplaceTransactionStatus.COMPLETED, MarketplaceTransactionStatus.CANCELLED]:
            raise ValueError(f"Cannot dispute {transaction.status.value} transaction")
        
        # Check if dispute period has expired
        if transaction.shipped_at and datetime.utcnow() > transaction.shipped_at + timedelta(days=self.dispute_timeout_days):
            raise ValueError("Dispute period has expired")
        
        # Update transaction with dispute details
        transaction.status = MarketplaceTransactionStatus.DISPUTED
        transaction.dispute_initiated_at = datetime.utcnow()
        transaction.dispute_initiator_id = initiator_id
        transaction.dispute_reason = dispute_reason
        transaction.dispute_details = dispute_details
        transaction.dispute_evidence_urls = evidence_urls or []
        transaction.dispute_status = MarketplaceDisputeStatus.OPEN
        
        self.db.commit()
        
        logger.info(
            f"Dispute initiated for transaction {transaction_id} by user {initiator_id}: {dispute_reason}"
        )
        
        return transaction
    
    async def resolve_dispute(
        self,
        transaction_id: str,
        admin_id: str,
        resolution: str,
        refund_buyer_percentage: int = 0,
        resolution_notes: Optional[str] = None
    ) -> MarketplaceTransaction:
        """Resolve a dispute (admin action)"""
        
        transaction = (
            self.db.query(MarketplaceTransaction)
            .filter(MarketplaceTransaction.id == transaction_id)
            .first()
        )
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if transaction.status != MarketplaceTransactionStatus.DISPUTED:
            raise ValueError("Transaction is not in disputed status")
        
        # Validate refund percentage
        if not 0 <= refund_buyer_percentage <= 100:
            raise ValueError("Refund percentage must be between 0 and 100")
        
        try:
            # Calculate refund and seller amounts
            total_escrow = transaction.total_cost_cc
            platform_fee = transaction.platform_fee_cc
            item_total = transaction.item_total_cc
            
            buyer_refund = (item_total * refund_buyer_percentage / 100)
            seller_payment = item_total - buyer_refund
            
            # Process refund to buyer if any
            if buyer_refund > 0:
                await self.cc_system.add_credits(
                    transaction.buyer_id,
                    buyer_refund,
                    TransactionType.DISPUTE_REFUND,
                    f"Dispute resolution refund: {transaction.listing.title}",
                    metadata={
                        "marketplace_transaction_id": transaction_id,
                        "dispute_resolution": resolution,
                        "refund_percentage": refund_buyer_percentage,
                        "admin_id": admin_id
                    }
                )
            
            # Process payment to seller if any
            if seller_payment > 0:
                await self.cc_system.add_credits(
                    transaction.seller_id,
                    seller_payment,
                    TransactionType.DISPUTE_PAYMENT,
                    f"Dispute resolution payment: {transaction.listing.title}",
                    metadata={
                        "marketplace_transaction_id": transaction_id,
                        "dispute_resolution": resolution,
                        "payment_percentage": 100 - refund_buyer_percentage,
                        "admin_id": admin_id
                    }
                )
            
            # Platform keeps the fee regardless of dispute outcome
            
            # Update transaction status
            transaction.status = MarketplaceTransactionStatus.DISPUTE_RESOLVED
            transaction.dispute_status = MarketplaceDisputeStatus.RESOLVED
            transaction.dispute_resolved_at = datetime.utcnow()
            transaction.dispute_resolution = resolution
            transaction.dispute_admin_id = admin_id
            transaction.dispute_resolution_notes = resolution_notes
            transaction.buyer_refund_cc = buyer_refund
            transaction.seller_payment_cc = seller_payment
            
            self.db.commit()
            
            logger.info(
                f"Resolved dispute for transaction {transaction_id}: "
                f"{refund_buyer_percentage}% refund to buyer, "
                f"{100 - refund_buyer_percentage}% payment to seller"
            )
            
            return transaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to resolve dispute for transaction {transaction_id}: {str(e)}")
            raise
    
    async def cancel_transaction(
        self,
        transaction_id: str,
        user_id: str,
        cancellation_reason: str
    ) -> MarketplaceTransaction:
        """Cancel a transaction (before shipment)"""
        
        transaction = (
            self.db.query(MarketplaceTransaction)
            .filter(MarketplaceTransaction.id == transaction_id)
            .first()
        )
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        # Verify user can cancel
        if user_id not in [transaction.buyer_id, transaction.seller_id]:
            raise ValueError("Only buyer or seller can cancel transaction")
        
        if transaction.status not in [MarketplaceTransactionStatus.PENDING, MarketplaceTransactionStatus.PAYMENT_RECEIVED]:
            raise ValueError(f"Cannot cancel transaction in {transaction.status.value} status")
        
        try:
            # Refund full amount to buyer
            await self.cc_system.add_credits(
                transaction.buyer_id,
                transaction.total_cost_cc,
                TransactionType.CANCELLATION_REFUND,
                f"Transaction cancelled: {transaction.listing.title}",
                metadata={
                    "marketplace_transaction_id": transaction_id,
                    "cancelled_by": user_id,
                    "cancellation_reason": cancellation_reason,
                    "refund_amount_cc": str(transaction.total_cost_cc)
                }
            )
            
            # Restore inventory
            listing = transaction.listing
            listing.quantity += transaction.quantity
            listing.sales_count -= transaction.quantity
            
            # Update transaction status
            transaction.status = MarketplaceTransactionStatus.CANCELLED
            transaction.cancelled_at = datetime.utcnow()
            transaction.cancelled_by_id = user_id
            transaction.cancellation_reason = cancellation_reason
            
            self.db.commit()
            
            logger.info(
                f"Cancelled transaction {transaction_id} by user {user_id}: "
                f"refunded {transaction.total_cost_cc} CC to buyer"
            )
            
            return transaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cancel transaction {transaction_id}: {str(e)}")
            raise
    
    async def process_auto_releases(self) -> Dict[str, int]:
        """Process automatic escrow releases for delivered orders"""
        
        # Find transactions ready for auto-release
        cutoff_time = datetime.utcnow()
        
        auto_release_transactions = (
            self.db.query(MarketplaceTransaction)
            .filter(
                and_(
                    MarketplaceTransaction.status == MarketplaceTransactionStatus.SHIPPED,
                    MarketplaceTransaction.auto_release_at <= cutoff_time
                )
            )
            .all()
        )
        
        results = {"processed": 0, "failed": 0}
        
        for transaction in auto_release_transactions:
            try:
                # Auto-complete the transaction
                await self.confirm_delivery(
                    transaction.id,
                    transaction.buyer_id,
                    delivery_rating=5,  # Default rating for auto-releases
                    delivery_notes="Auto-released after delivery period"
                )
                
                results["processed"] += 1
                
            except Exception as e:
                logger.error(f"Failed to auto-release transaction {transaction.id}: {str(e)}")
                results["failed"] += 1
        
        logger.info(f"Auto-release processing completed: {results}")
        return results
    
    async def get_transaction_details(self, transaction_id: str, user_id: str) -> Dict:
        """Get detailed transaction information"""
        
        transaction = (
            self.db.query(MarketplaceTransaction)
            .filter(MarketplaceTransaction.id == transaction_id)
            .first()
        )
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        # Verify user access
        if user_id not in [transaction.buyer_id, transaction.seller_id]:
            raise ValueError("Access denied")
        
        return {
            "transaction_id": transaction.id,
            "buyer_id": transaction.buyer_id,
            "seller_id": transaction.seller_id,
            "listing": {
                "id": transaction.listing_id,
                "title": transaction.listing.title,
                "description": transaction.listing.description,
                "images": transaction.listing.images or []
            },
            "purchase_details": {
                "quantity": transaction.quantity,
                "item_price_cc": float(transaction.item_price_cc),
                "item_total_cc": float(transaction.item_total_cc),
                "platform_fee_cc": float(transaction.platform_fee_cc),
                "total_cost_cc": float(transaction.total_cost_cc)
            },
            "status": transaction.status.value,
            "transaction_type": transaction.transaction_type.value,
            "timeline": {
                "created_at": transaction.created_at.isoformat(),
                "escrow_funded_at": transaction.escrow_funded_at.isoformat() if transaction.escrow_funded_at else None,
                "shipped_at": transaction.shipped_at.isoformat() if transaction.shipped_at else None,
                "delivered_at": transaction.delivered_at.isoformat() if transaction.delivered_at else None,
                "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
                "cancelled_at": transaction.cancelled_at.isoformat() if transaction.cancelled_at else None
            },
            "shipping": {
                "tracking_number": transaction.tracking_number,
                "carrier": transaction.carrier,
                "shipment_notes": transaction.shipment_notes,
                "delivery_address": transaction.delivery_address,
                "expected_delivery_date": transaction.expected_delivery_date.isoformat() if transaction.expected_delivery_date else None
            },
            "ratings": {
                "delivery_rating": transaction.delivery_rating,
                "delivery_notes": transaction.delivery_notes
            },
            "dispute": {
                "status": transaction.dispute_status.value if transaction.dispute_status else None,
                "initiated_at": transaction.dispute_initiated_at.isoformat() if transaction.dispute_initiated_at else None,
                "initiator_id": transaction.dispute_initiator_id,
                "reason": transaction.dispute_reason,
                "details": transaction.dispute_details,
                "resolution": transaction.dispute_resolution,
                "resolved_at": transaction.dispute_resolved_at.isoformat() if transaction.dispute_resolved_at else None,
                "buyer_refund_cc": float(transaction.buyer_refund_cc) if transaction.buyer_refund_cc else 0,
                "seller_payment_cc": float(transaction.seller_payment_cc) if transaction.seller_payment_cc else 0
            }
        }
    
    async def get_user_transactions(
        self,
        user_id: str,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get user's marketplace transactions"""
        
        query = (
            self.db.query(MarketplaceTransaction)
            .filter(
                (MarketplaceTransaction.buyer_id == user_id) |
                (MarketplaceTransaction.seller_id == user_id)
            )
        )
        
        if transaction_type:
            if transaction_type == "purchases":
                query = query.filter(MarketplaceTransaction.buyer_id == user_id)
            elif transaction_type == "sales":
                query = query.filter(MarketplaceTransaction.seller_id == user_id)
        
        if status:
            query = query.filter(MarketplaceTransaction.status == status)
        
        transactions = (
            query.order_by(desc(MarketplaceTransaction.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        result = []
        for transaction in transactions:
            result.append({
                "transaction_id": transaction.id,
                "listing_title": transaction.listing.title,
                "quantity": transaction.quantity,
                "total_cost_cc": float(transaction.total_cost_cc),
                "status": transaction.status.value,
                "user_role": "buyer" if transaction.buyer_id == user_id else "seller",
                "counterparty_id": transaction.seller_id if transaction.buyer_id == user_id else transaction.buyer_id,
                "created_at": transaction.created_at.isoformat(),
                "expected_delivery_date": transaction.expected_delivery_date.isoformat() if transaction.expected_delivery_date else None,
                "tracking_number": transaction.tracking_number,
                "can_dispute": self._can_dispute_transaction(transaction, user_id),
                "can_cancel": self._can_cancel_transaction(transaction, user_id)
            })
        
        return result
    
    def _can_dispute_transaction(self, transaction: MarketplaceTransaction, user_id: str) -> bool:
        """Check if user can dispute a transaction"""
        
        if user_id not in [transaction.buyer_id, transaction.seller_id]:
            return False
        
        if transaction.status in [MarketplaceTransactionStatus.COMPLETED, MarketplaceTransactionStatus.CANCELLED]:
            return False
        
        if transaction.dispute_initiated_at:
            return False
        
        if transaction.shipped_at and datetime.utcnow() > transaction.shipped_at + timedelta(days=self.dispute_timeout_days):
            return False
        
        return True
    
    def _can_cancel_transaction(self, transaction: MarketplaceTransaction, user_id: str) -> bool:
        """Check if user can cancel a transaction"""
        
        if user_id not in [transaction.buyer_id, transaction.seller_id]:
            return False
        
        if transaction.status not in [MarketplaceTransactionStatus.PENDING, MarketplaceTransactionStatus.PAYMENT_RECEIVED]:
            return False
        
        return True
    
    async def get_marketplace_analytics(self, admin_id: str) -> Dict:
        """Get marketplace analytics for administrators"""
        
        # Total transactions summary
        total_stats = (
            self.db.query(
                func.count(MarketplaceTransaction.id).label("total_transactions"),
                func.sum(MarketplaceTransaction.total_cost_cc).label("total_volume_cc"),
                func.sum(MarketplaceTransaction.platform_fee_cc).label("total_platform_fees_cc")
            )
            .first()
        )
        
        # Status breakdown
        status_breakdown = (
            self.db.query(
                MarketplaceTransaction.status,
                func.count(MarketplaceTransaction.id).label("count"),
                func.sum(MarketplaceTransaction.total_cost_cc).label("volume_cc")
            )
            .group_by(MarketplaceTransaction.status)
            .all()
        )
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_stats = (
            self.db.query(
                func.count(MarketplaceTransaction.id).label("recent_transactions"),
                func.sum(MarketplaceTransaction.total_cost_cc).label("recent_volume_cc"),
                func.sum(MarketplaceTransaction.platform_fee_cc).label("recent_fees_cc")
            )
            .filter(MarketplaceTransaction.created_at >= thirty_days_ago)
            .first()
        )
        
        # Dispute statistics
        dispute_stats = (
            self.db.query(
                func.count(MarketplaceTransaction.id).label("total_disputes"),
                func.sum(
                    func.case(
                        (MarketplaceTransaction.dispute_status == MarketplaceDisputeStatus.RESOLVED, 1),
                        else_=0
                    )
                ).label("resolved_disputes")
            )
            .filter(MarketplaceTransaction.dispute_initiated_at.isnot(None))
            .first()
        )
        
        return {
            "overview": {
                "total_transactions": total_stats.total_transactions or 0,
                "total_volume_cc": float(total_stats.total_volume_cc or 0),
                "total_platform_fees_cc": float(total_stats.total_platform_fees_cc or 0),
                "average_transaction_cc": float(
                    (total_stats.total_volume_cc or 0) / (total_stats.total_transactions or 1)
                )
            },
            "recent_activity_30d": {
                "transactions": recent_stats.recent_transactions or 0,
                "volume_cc": float(recent_stats.recent_volume_cc or 0),
                "platform_fees_cc": float(recent_stats.recent_fees_cc or 0)
            },
            "status_breakdown": [
                {
                    "status": status.status.value,
                    "count": status.count,
                    "volume_cc": float(status.volume_cc or 0)
                }
                for status in status_breakdown
            ],
            "disputes": {
                "total_disputes": dispute_stats.total_disputes or 0,
                "resolved_disputes": dispute_stats.resolved_disputes or 0,
                "resolution_rate": (
                    float(dispute_stats.resolved_disputes or 0) / (dispute_stats.total_disputes or 1) * 100
                )
            },
            "settings": {
                "platform_fee_rate": float(self.platform_fee_rate * 100),
                "auto_release_days": self.auto_release_days,
                "dispute_timeout_days": self.dispute_timeout_days
            }
        }