"""
Automated royalty distribution system
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import uuid
from ..models.base import RoyaltyRule, Order, Product

class RoyaltyType(Enum):
    PERCENTAGE = "percentage"
    FLAT_RATE = "flat_rate"
    TIERED = "tiered"
    REVENUE_SHARE = "revenue_share"

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"
    REFUNDED = "refunded"

class PayoutFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class RoyaltySystem:
    """Manages automated royalty distribution"""
    
    def __init__(self):
        self.royalty_rules: Dict[str, RoyaltyRule] = {}
        self.pending_payouts: Dict[str, Dict[str, Any]] = {}
        self.payout_history: Dict[str, List[Dict[str, Any]]] = {}
        self.revenue_shares: Dict[str, List[Dict[str, Any]]] = {}  # product_id -> collaborators
        self.payment_processors: Dict[str, Dict[str, Any]] = {}
        
        # Initialize system settings
        self._initialize_system_settings()
    
    def _initialize_system_settings(self):
        """Initialize royalty system settings"""
        
        self.system_settings = {
            "minimum_payout": Decimal("10.00"),  # Minimum amount for payout
            "platform_fee": Decimal("0.05"),    # 5% platform fee
            "payment_processing_fee": Decimal("0.029"),  # 2.9% processing fee
            "currency": "USD",
            "default_payout_frequency": PayoutFrequency.MONTHLY,
            "hold_period_days": 7,  # Days to hold funds before payout
            "dispute_period_days": 30  # Days customers can dispute
        }
        
        self.tier_structures = {
            "standard": [
                {"min_revenue": Decimal("0"), "max_revenue": Decimal("1000"), "rate": Decimal("0.70")},
                {"min_revenue": Decimal("1000"), "max_revenue": Decimal("5000"), "rate": Decimal("0.75")},
                {"min_revenue": Decimal("5000"), "max_revenue": Decimal("10000"), "rate": Decimal("0.80")},
                {"min_revenue": Decimal("10000"), "max_revenue": None, "rate": Decimal("0.85")}
            ],
            "premium": [
                {"min_revenue": Decimal("0"), "max_revenue": Decimal("1000"), "rate": Decimal("0.80")},
                {"min_revenue": Decimal("1000"), "max_revenue": Decimal("5000"), "rate": Decimal("0.85")},
                {"min_revenue": Decimal("5000"), "max_revenue": None, "rate": Decimal("0.90")}
            ]
        }
        
        # Initialize payment processors
        self._initialize_payment_processors()
    
    def _initialize_payment_processors(self):
        """Initialize payment processor configurations"""
        
        self.payment_processors = {
            "paypal": {
                "name": "PayPal",
                "fee_percentage": Decimal("0.029"),
                "fee_fixed": Decimal("0.30"),
                "minimum_payout": Decimal("1.00"),
                "supported_currencies": ["USD", "EUR", "GBP", "CAD"],
                "processing_time_days": 1
            },
            "stripe": {
                "name": "Stripe",
                "fee_percentage": Decimal("0.029"),
                "fee_fixed": Decimal("0.30"),
                "minimum_payout": Decimal("0.50"),
                "supported_currencies": ["USD", "EUR", "GBP", "CAD", "AUD"],
                "processing_time_days": 2
            },
            "bank_transfer": {
                "name": "Bank Transfer",
                "fee_percentage": Decimal("0.005"),
                "fee_fixed": Decimal("0.00"),
                "minimum_payout": Decimal("50.00"),
                "supported_currencies": ["USD"],
                "processing_time_days": 5
            }
        }
    
    def create_royalty_rule(
        self,
        creator_id: str,
        product_id: Optional[str] = None,  # None for global rule
        royalty_type: RoyaltyType = RoyaltyType.PERCENTAGE,
        rate: Optional[Decimal] = None,
        tier_structure: Optional[str] = None,
        minimum_threshold: Decimal = None,
        payout_frequency: PayoutFrequency = PayoutFrequency.MONTHLY,
        payment_method: str = "paypal",
        collaborators: List[Dict[str, Any]] = None
    ) -> RoyaltyRule:
        """Create royalty rule for creator or specific product"""
        
        if royalty_type == RoyaltyType.TIERED and not tier_structure:
            tier_structure = "standard"
        
        if royalty_type == RoyaltyType.PERCENTAGE and not rate:
            rate = Decimal("0.70")  # Default 70% to creator
        
        royalty_rule = RoyaltyRule(
            creator_id=creator_id,
            product_id=product_id,
            royalty_type=royalty_type.value,
            rate=rate,
            tier_structure=tier_structure,
            minimum_threshold=minimum_threshold or self.system_settings["minimum_payout"],
            payout_frequency=payout_frequency.value,
            payment_method=payment_method,
            collaborators=collaborators or [],
            is_active=True
        )
        
        self.royalty_rules[royalty_rule.id] = royalty_rule
        
        # Set up collaborator revenue sharing if specified
        if collaborators:
            self._setup_revenue_sharing(product_id or "global", collaborators)
        
        return royalty_rule
    
    def _setup_revenue_sharing(self, product_id: str, collaborators: List[Dict[str, Any]]):
        """Set up revenue sharing between collaborators"""
        
        if product_id not in self.revenue_shares:
            self.revenue_shares[product_id] = []
        
        # Validate that shares add up to 100%
        total_share = sum(Decimal(str(collab["share"])) for collab in collaborators)
        if total_share != Decimal("1.00"):
            raise ValueError(f"Collaborator shares must add up to 100%, got {total_share * 100}%")
        
        self.revenue_shares[product_id] = collaborators
    
    def calculate_royalty(self, order: Order, product: Product) -> Dict[str, Any]:
        """Calculate royalty amount for an order"""
        
        # Get applicable royalty rule
        royalty_rule = self._get_applicable_rule(product.creator_id, product.id)
        
        if not royalty_rule:
            # Use default rule
            royalty_rule = self._create_default_rule(product.creator_id)
        
        # Calculate base amount (order total minus fees)
        gross_amount = order.total_amount
        platform_fee = gross_amount * self.system_settings["platform_fee"]
        processing_fee = gross_amount * self.system_settings["payment_processing_fee"]
        
        net_amount = gross_amount - platform_fee - processing_fee
        
        # Calculate royalty based on rule type
        royalty_calculation = {
            "order_id": order.id,
            "product_id": product.id,
            "creator_id": product.creator_id,
            "gross_amount": gross_amount,
            "platform_fee": platform_fee,
            "processing_fee": processing_fee,
            "net_amount": net_amount,
            "royalty_rule_id": royalty_rule.id,
            "calculated_at": datetime.utcnow()
        }
        
        if royalty_rule.royalty_type == RoyaltyType.PERCENTAGE.value:
            creator_royalty = net_amount * royalty_rule.rate
            royalty_calculation["creator_royalty"] = creator_royalty
            royalty_calculation["royalty_rate"] = royalty_rule.rate
        
        elif royalty_rule.royalty_type == RoyaltyType.FLAT_RATE.value:
            creator_royalty = min(royalty_rule.rate, net_amount)
            royalty_calculation["creator_royalty"] = creator_royalty
            royalty_calculation["royalty_rate"] = "flat"
        
        elif royalty_rule.royalty_type == RoyaltyType.TIERED.value:
            creator_royalty = self._calculate_tiered_royalty(product.creator_id, net_amount, royalty_rule.tier_structure)
            royalty_calculation["creator_royalty"] = creator_royalty
            royalty_calculation["royalty_rate"] = "tiered"
        
        else:  # REVENUE_SHARE
            creator_royalty = net_amount  # Will be split among collaborators
            royalty_calculation["creator_royalty"] = creator_royalty
            royalty_calculation["royalty_rate"] = "revenue_share"
        
        # Handle revenue sharing with collaborators
        if product.id in self.revenue_shares or "global" in self.revenue_shares:
            collaborators = self.revenue_shares.get(product.id, self.revenue_shares.get("global", []))
            royalty_calculation["collaborator_splits"] = self._calculate_collaborator_splits(
                creator_royalty, collaborators
            )
        
        return royalty_calculation
    
    def _get_applicable_rule(self, creator_id: str, product_id: str) -> Optional[RoyaltyRule]:
        """Get the most applicable royalty rule"""
        
        # First check for product-specific rule
        for rule in self.royalty_rules.values():
            if rule.creator_id == creator_id and rule.product_id == product_id and rule.is_active:
                return rule
        
        # Then check for creator-wide rule
        for rule in self.royalty_rules.values():
            if rule.creator_id == creator_id and rule.product_id is None and rule.is_active:
                return rule
        
        return None
    
    def _create_default_rule(self, creator_id: str) -> RoyaltyRule:
        """Create default royalty rule for creator"""
        
        return RoyaltyRule(
            creator_id=creator_id,
            product_id=None,
            royalty_type=RoyaltyType.PERCENTAGE.value,
            rate=Decimal("0.70"),  # Default 70%
            minimum_threshold=self.system_settings["minimum_payout"],
            payout_frequency=self.system_settings["default_payout_frequency"].value,
            payment_method="paypal",
            collaborators=[],
            is_active=True
        )
    
    def _calculate_tiered_royalty(self, creator_id: str, net_amount: Decimal, tier_structure: str) -> Decimal:
        """Calculate royalty using tiered structure"""
        
        # Get creator's total revenue to date (simplified)
        total_revenue = self._get_creator_total_revenue(creator_id)
        
        tiers = self.tier_structures.get(tier_structure, self.tier_structures["standard"])
        
        # Find applicable tier
        applicable_rate = Decimal("0.70")  # Default
        
        for tier in tiers:
            if total_revenue >= tier["min_revenue"]:
                if tier["max_revenue"] is None or total_revenue <= tier["max_revenue"]:
                    applicable_rate = tier["rate"]
                    break
        
        return net_amount * applicable_rate
    
    def _get_creator_total_revenue(self, creator_id: str) -> Decimal:
        """Get creator's total revenue to date (simplified calculation)"""
        
        # In real implementation, this would query the database
        # For now, return a placeholder value
        return Decimal("2500.00")
    
    def _calculate_collaborator_splits(self, total_amount: Decimal, collaborators: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """Calculate revenue splits for collaborators"""
        
        splits = {}
        
        for collaborator in collaborators:
            user_id = collaborator["user_id"]
            share = Decimal(str(collaborator["share"]))
            splits[user_id] = (total_amount * share).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return splits
    
    def process_order_royalty(self, order: Order, product: Product) -> str:
        """Process royalty for completed order"""
        
        royalty_calculation = self.calculate_royalty(order, product)
        
        # Create payout entry
        payout_id = str(uuid.uuid4())
        
        payout_entry = {
            "id": payout_id,
            "order_id": order.id,
            "product_id": product.id,
            "creator_id": product.creator_id,
            "gross_amount": royalty_calculation["gross_amount"],
            "net_amount": royalty_calculation["net_amount"],
            "creator_royalty": royalty_calculation["creator_royalty"],
            "platform_fee": royalty_calculation["platform_fee"],
            "processing_fee": royalty_calculation["processing_fee"],
            "royalty_rule_id": royalty_calculation["royalty_rule_id"],
            "collaborator_splits": royalty_calculation.get("collaborator_splits", {}),
            "status": PaymentStatus.PENDING,
            "created_at": datetime.utcnow(),
            "hold_until": datetime.utcnow() + timedelta(days=self.system_settings["hold_period_days"]),
            "dispute_deadline": datetime.utcnow() + timedelta(days=self.system_settings["dispute_period_days"])
        }
        
        # Add to pending payouts
        if product.creator_id not in self.pending_payouts:
            self.pending_payouts[product.creator_id] = {}
        
        self.pending_payouts[product.creator_id][payout_id] = payout_entry
        
        return payout_id
    
    def process_scheduled_payouts(self, frequency: PayoutFrequency = PayoutFrequency.MONTHLY) -> Dict[str, Any]:
        """Process scheduled payouts for creators"""
        
        processed_payouts = []
        failed_payouts = []
        total_amount = Decimal("0.00")
        
        current_time = datetime.utcnow()
        
        for creator_id, creator_payouts in self.pending_payouts.items():
            # Get creator's royalty rule for payout settings
            royalty_rule = self._get_applicable_rule(creator_id, None)
            
            if not royalty_rule or royalty_rule.payout_frequency != frequency.value:
                continue
            
            # Aggregate eligible payouts
            eligible_payouts = []
            creator_total = Decimal("0.00")
            
            for payout_id, payout_entry in creator_payouts.items():
                if (payout_entry["status"] == PaymentStatus.PENDING and
                    payout_entry["hold_until"] <= current_time):
                    
                    eligible_payouts.append(payout_entry)
                    creator_total += payout_entry["creator_royalty"]
            
            # Check minimum threshold
            if creator_total < royalty_rule.minimum_threshold:
                continue
            
            # Process payout
            payout_result = self._execute_payout(creator_id, eligible_payouts, creator_total, royalty_rule.payment_method)
            
            if payout_result["success"]:
                processed_payouts.append({
                    "creator_id": creator_id,
                    "amount": creator_total,
                    "payout_count": len(eligible_payouts),
                    "payment_method": royalty_rule.payment_method,
                    "transaction_id": payout_result["transaction_id"]
                })
                total_amount += creator_total
                
                # Move to history and remove from pending
                self._move_to_history(creator_id, eligible_payouts)
            else:
                failed_payouts.append({
                    "creator_id": creator_id,
                    "amount": creator_total,
                    "error": payout_result["error"]
                })
        
        return {
            "processed_count": len(processed_payouts),
            "failed_count": len(failed_payouts),
            "total_amount": total_amount,
            "processed_payouts": processed_payouts,
            "failed_payouts": failed_payouts,
            "processed_at": current_time
        }
    
    def _execute_payout(self, creator_id: str, payouts: List[Dict[str, Any]], total_amount: Decimal, payment_method: str) -> Dict[str, Any]:
        """Execute payout to creator"""
        
        if payment_method not in self.payment_processors:
            return {"success": False, "error": f"Unsupported payment method: {payment_method}"}
        
        processor = self.payment_processors[payment_method]
        
        # Calculate fees
        processing_fee = (total_amount * processor["fee_percentage"] + processor["fee_fixed"]).quantize(Decimal('0.01'))
        net_payout = total_amount - processing_fee
        
        # Check minimum
        if net_payout < processor["minimum_payout"]:
            return {"success": False, "error": f"Amount below minimum for {payment_method}"}
        
        # Simulate payment processing
        transaction_id = f"txn_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{creator_id[:8]}"
        
        # In real implementation, this would call the actual payment processor API
        payout_success = self._simulate_payment_processing(creator_id, net_payout, payment_method)
        
        if payout_success:
            # Update payout entries
            for payout in payouts:
                payout["status"] = PaymentStatus.COMPLETED
                payout["transaction_id"] = transaction_id
                payout["net_payout"] = net_payout
                payout["processing_fee"] = processing_fee
                payout["processed_at"] = datetime.utcnow()
            
            return {"success": True, "transaction_id": transaction_id, "net_amount": net_payout}
        else:
            return {"success": False, "error": "Payment processor rejected transaction"}
    
    def _simulate_payment_processing(self, creator_id: str, amount: Decimal, payment_method: str) -> bool:
        """Simulate payment processing (replace with real API calls)"""
        
        # Simulate 95% success rate
        import random
        return random.random() < 0.95
    
    def _move_to_history(self, creator_id: str, payouts: List[Dict[str, Any]]):
        """Move completed payouts to history"""
        
        if creator_id not in self.payout_history:
            self.payout_history[creator_id] = []
        
        # Add to history
        for payout in payouts:
            self.payout_history[creator_id].append(payout)
        
        # Remove from pending
        for payout in payouts:
            if payout["id"] in self.pending_payouts.get(creator_id, {}):
                del self.pending_payouts[creator_id][payout["id"]]
    
    def get_creator_earnings_summary(self, creator_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Get creator's earnings summary"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get pending payouts
        pending_payouts = self.pending_payouts.get(creator_id, {})
        pending_total = sum(payout["creator_royalty"] for payout in pending_payouts.values())
        pending_count = len(pending_payouts)
        
        # Get completed payouts
        completed_payouts = self.payout_history.get(creator_id, [])
        recent_completed = [p for p in completed_payouts if p["processed_at"] >= cutoff_date]
        completed_total = sum(payout["creator_royalty"] for payout in recent_completed)
        completed_count = len(recent_completed)
        
        # Calculate total historical earnings
        all_completed = sum(payout["creator_royalty"] for payout in completed_payouts)
        
        return {
            "creator_id": creator_id,
            "period_days": period_days,
            "pending_earnings": {
                "amount": pending_total,
                "count": pending_count,
                "ready_for_payout": sum(
                    payout["creator_royalty"] for payout in pending_payouts.values()
                    if payout["hold_until"] <= datetime.utcnow()
                )
            },
            "recent_earnings": {
                "amount": completed_total,
                "count": completed_count,
                "period": f"Last {period_days} days"
            },
            "lifetime_earnings": {
                "total_paid": all_completed,
                "total_orders": len(completed_payouts)
            },
            "next_payout": self._calculate_next_payout_date(creator_id),
            "royalty_settings": self._get_applicable_rule(creator_id, None)
        }
    
    def _calculate_next_payout_date(self, creator_id: str) -> Optional[datetime]:
        """Calculate next payout date for creator"""
        
        royalty_rule = self._get_applicable_rule(creator_id, None)
        
        if not royalty_rule:
            return None
        
        frequency = royalty_rule.payout_frequency
        current_time = datetime.utcnow()
        
        if frequency == PayoutFrequency.WEEKLY.value:
            # Next Monday
            days_ahead = 7 - current_time.weekday()
            if days_ahead == 7:  # Today is Monday
                days_ahead = 7
            return current_time + timedelta(days=days_ahead)
        
        elif frequency == PayoutFrequency.MONTHLY.value:
            # First of next month
            if current_time.month == 12:
                return current_time.replace(year=current_time.year + 1, month=1, day=1)
            else:
                return current_time.replace(month=current_time.month + 1, day=1)
        
        elif frequency == PayoutFrequency.QUARTERLY.value:
            # Next quarter
            current_quarter = (current_time.month - 1) // 3
            next_quarter_month = (current_quarter + 1) * 3 + 1
            
            if next_quarter_month > 12:
                return current_time.replace(year=current_time.year + 1, month=1, day=1)
            else:
                return current_time.replace(month=next_quarter_month, day=1)
        
        return None
    
    def handle_dispute(self, order_id: str, dispute_reason: str, dispute_amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Handle order dispute that affects royalty"""
        
        # Find affected payouts
        affected_payouts = []
        
        for creator_id, creator_payouts in self.pending_payouts.items():
            for payout_id, payout_entry in creator_payouts.items():
                if payout_entry["order_id"] == order_id:
                    affected_payouts.append((creator_id, payout_id, payout_entry))
        
        # Also check history
        for creator_id, creator_history in self.payout_history.items():
            for payout_entry in creator_history:
                if payout_entry["order_id"] == order_id:
                    affected_payouts.append((creator_id, payout_entry["id"], payout_entry))
        
        if not affected_payouts:
            return {"success": False, "error": "No payouts found for order"}
        
        # Process dispute
        dispute_id = str(uuid.uuid4())
        dispute_record = {
            "id": dispute_id,
            "order_id": order_id,
            "dispute_reason": dispute_reason,
            "dispute_amount": dispute_amount,
            "affected_payouts": len(affected_payouts),
            "status": "under_review",
            "created_at": datetime.utcnow(),
            "resolution": None
        }
        
        # Update payout statuses
        for creator_id, payout_id, payout_entry in affected_payouts:
            payout_entry["status"] = PaymentStatus.DISPUTED
            payout_entry["dispute_id"] = dispute_id
        
        return {
            "success": True,
            "dispute_id": dispute_id,
            "affected_payouts": len(affected_payouts),
            "status": "Dispute created and payouts placed on hold"
        }
    
    def resolve_dispute(self, dispute_id: str, resolution: str, refund_amount: Decimal = Decimal("0.00")) -> Dict[str, Any]:
        """Resolve dispute and adjust royalties"""
        
        # Find disputed payouts
        affected_payouts = []
        
        for creator_id, creator_payouts in self.pending_payouts.items():
            for payout_id, payout_entry in creator_payouts.items():
                if payout_entry.get("dispute_id") == dispute_id:
                    affected_payouts.append((creator_id, payout_id, payout_entry))
        
        for creator_id, creator_history in self.payout_history.items():
            for payout_entry in creator_history:
                if payout_entry.get("dispute_id") == dispute_id:
                    affected_payouts.append((creator_id, payout_entry["id"], payout_entry))
        
        if not affected_payouts:
            return {"success": False, "error": "No disputed payouts found"}
        
        # Apply resolution
        for creator_id, payout_id, payout_entry in affected_payouts:
            if resolution == "refund_full":
                payout_entry["status"] = PaymentStatus.REFUNDED
                payout_entry["refund_amount"] = payout_entry["creator_royalty"]
                payout_entry["creator_royalty"] = Decimal("0.00")
            
            elif resolution == "refund_partial":
                payout_entry["status"] = PaymentStatus.COMPLETED
                payout_entry["refund_amount"] = refund_amount
                # Adjust creator royalty proportionally
                refund_ratio = refund_amount / payout_entry["gross_amount"]
                royalty_reduction = payout_entry["creator_royalty"] * refund_ratio
                payout_entry["creator_royalty"] -= royalty_reduction
            
            elif resolution == "no_refund":
                payout_entry["status"] = PaymentStatus.COMPLETED
                payout_entry["refund_amount"] = Decimal("0.00")
            
            payout_entry["dispute_resolved_at"] = datetime.utcnow()
            payout_entry["resolution"] = resolution
        
        return {
            "success": True,
            "resolution": resolution,
            "affected_payouts": len(affected_payouts),
            "total_refund": refund_amount
        }
    
    def generate_royalty_report(self, creator_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive royalty report for creator"""
        
        # Collect all payouts in date range
        all_payouts = []
        
        # Pending payouts
        pending_payouts = self.pending_payouts.get(creator_id, {})
        for payout in pending_payouts.values():
            if start_date <= payout["created_at"] <= end_date:
                all_payouts.append(payout)
        
        # Historical payouts
        history_payouts = self.payout_history.get(creator_id, [])
        for payout in history_payouts:
            if start_date <= payout["created_at"] <= end_date:
                all_payouts.append(payout)
        
        # Calculate summary statistics
        total_gross = sum(p["gross_amount"] for p in all_payouts)
        total_net = sum(p["net_amount"] for p in all_payouts)
        total_royalty = sum(p["creator_royalty"] for p in all_payouts)
        total_platform_fees = sum(p["platform_fee"] for p in all_payouts)
        total_processing_fees = sum(p["processing_fee"] for p in all_payouts)
        
        # Group by product
        product_breakdown = {}
        for payout in all_payouts:
            product_id = payout["product_id"]
            if product_id not in product_breakdown:
                product_breakdown[product_id] = {
                    "orders": 0,
                    "gross_revenue": Decimal("0.00"),
                    "net_revenue": Decimal("0.00"),
                    "royalty_earned": Decimal("0.00")
                }
            
            product_breakdown[product_id]["orders"] += 1
            product_breakdown[product_id]["gross_revenue"] += payout["gross_amount"]
            product_breakdown[product_id]["net_revenue"] += payout["net_amount"]
            product_breakdown[product_id]["royalty_earned"] += payout["creator_royalty"]
        
        # Group by status
        status_breakdown = {}
        for payout in all_payouts:
            status = payout["status"]
            if status not in status_breakdown:
                status_breakdown[status] = {"count": 0, "amount": Decimal("0.00")}
            
            status_breakdown[status]["count"] += 1
            status_breakdown[status]["amount"] += payout["creator_royalty"]
        
        return {
            "creator_id": creator_id,
            "report_period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": (end_date - start_date).days
            },
            "summary": {
                "total_orders": len(all_payouts),
                "gross_revenue": total_gross,
                "net_revenue": total_net,
                "total_fees": total_platform_fees + total_processing_fees,
                "platform_fees": total_platform_fees,
                "processing_fees": total_processing_fees,
                "royalty_earned": total_royalty,
                "effective_rate": (total_royalty / total_gross * 100) if total_gross > 0 else 0
            },
            "product_breakdown": product_breakdown,
            "status_breakdown": status_breakdown,
            "detailed_transactions": all_payouts,
            "generated_at": datetime.utcnow()
        }