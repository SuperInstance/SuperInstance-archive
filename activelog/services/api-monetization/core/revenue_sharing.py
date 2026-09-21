import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from models.monetization_models import *

class RevenueShareManager:
    def __init__(self):
        self.revenue_shares = {}
        self.provider_balances = {}
        self.payment_methods = {}
        self.payout_schedules = {}
        self.revenue_reports = {}
        self.fee_structures = {
            "platform_fee_percentage": Decimal("0.15"),  # 15% platform fee
            "payment_processing_fee": Decimal("0.029"),   # 2.9% payment processing
            "minimum_payout": Decimal("10.00"),           # Minimum $10 payout
            "currency_conversion_fee": Decimal("0.01")    # 1% for currency conversion
        }
        
    async def calculate_revenue_share(self, request: RevenueShareRequest) -> RevenueShareResponse:
        share_id = str(uuid.uuid4())
        
        platform_fee_percentage = self.fee_structures["platform_fee_percentage"]
        payment_processing_fee = self.fee_structures["payment_processing_fee"]
        
        gross_revenue = request.revenue_amount
        payment_processing_cost = gross_revenue * payment_processing_fee
        platform_fee = gross_revenue * platform_fee_percentage
        
        net_revenue = gross_revenue - payment_processing_cost
        provider_share = net_revenue - platform_fee
        
        share_record = {
            "share_id": share_id,
            "provider_id": request.provider_id,
            "api_id": request.api_id,
            "billing_period_start": request.billing_period_start,
            "billing_period_end": request.billing_period_end,
            "gross_revenue": gross_revenue,
            "payment_processing_fee": payment_processing_cost,
            "platform_fee": platform_fee,
            "provider_share": provider_share,
            "platform_fee_percentage": float(platform_fee_percentage * 100),
            "payment_status": "pending",
            "created_at": datetime.now(),
            "payment_date": None
        }
        
        self.revenue_shares[share_id] = share_record
        
        await self._update_provider_balance(request.provider_id, provider_share)
        
        return RevenueShareResponse(
            share_id=share_id,
            provider_id=request.provider_id,
            api_id=request.api_id,
            total_revenue=gross_revenue,
            platform_fee_percentage=float(platform_fee_percentage * 100),
            platform_fee=platform_fee,
            provider_share=provider_share,
            payment_status="pending",
            payment_date=None
        )
    
    async def process_payout(self, provider_id: str, amount: Decimal = None) -> Dict:
        if provider_id not in self.provider_balances:
            return {
                "success": False,
                "message": "Provider not found",
                "balance": Decimal("0.00")
            }
        
        current_balance = self.provider_balances[provider_id]["available_balance"]
        
        if current_balance < self.fee_structures["minimum_payout"]:
            return {
                "success": False,
                "message": f"Balance below minimum payout threshold of ${self.fee_structures['minimum_payout']}",
                "current_balance": current_balance,
                "minimum_required": self.fee_structures["minimum_payout"]
            }
        
        payout_amount = amount or current_balance
        
        if payout_amount > current_balance:
            return {
                "success": False,
                "message": "Insufficient balance",
                "requested_amount": payout_amount,
                "available_balance": current_balance
            }
        
        payout_id = str(uuid.uuid4())
        
        payout_record = {
            "payout_id": payout_id,
            "provider_id": provider_id,
            "amount": payout_amount,
            "status": "processing",
            "initiated_at": datetime.now(),
            "processed_at": None,
            "payment_method": await self._get_provider_payment_method(provider_id),
            "transaction_fee": Decimal("0.00")
        }
        
        self.provider_balances[provider_id]["available_balance"] -= payout_amount
        self.provider_balances[provider_id]["pending_payouts"] += payout_amount
        
        if "payout_history" not in self.provider_balances[provider_id]:
            self.provider_balances[provider_id]["payout_history"] = []
        
        self.provider_balances[provider_id]["payout_history"].append(payout_record)
        
        await self._initiate_payment_processing(payout_record)
        
        return {
            "success": True,
            "payout_id": payout_id,
            "amount": payout_amount,
            "status": "processing",
            "estimated_arrival": datetime.now() + timedelta(days=3),
            "remaining_balance": self.provider_balances[provider_id]["available_balance"]
        }
    
    async def get_provider_revenue_summary(self, provider_id: str, 
                                         start_date: datetime = None, 
                                         end_date: datetime = None) -> Dict:
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        provider_shares = [
            share for share in self.revenue_shares.values()
            if share["provider_id"] == provider_id
            and start_date <= share["created_at"] <= end_date
        ]
        
        total_gross_revenue = sum(share["gross_revenue"] for share in provider_shares)
        total_platform_fees = sum(share["platform_fee"] for share in provider_shares)
        total_provider_share = sum(share["provider_share"] for share in provider_shares)
        total_processing_fees = sum(share["payment_processing_fee"] for share in provider_shares)
        
        api_breakdown = {}
        for share in provider_shares:
            api_id = share["api_id"]
            if api_id not in api_breakdown:
                api_breakdown[api_id] = {
                    "gross_revenue": Decimal("0.00"),
                    "provider_share": Decimal("0.00"),
                    "transaction_count": 0
                }
            api_breakdown[api_id]["gross_revenue"] += share["gross_revenue"]
            api_breakdown[api_id]["provider_share"] += share["provider_share"]
            api_breakdown[api_id]["transaction_count"] += 1
        
        current_balance = self.provider_balances.get(provider_id, {}).get("available_balance", Decimal("0.00"))
        pending_payouts = self.provider_balances.get(provider_id, {}).get("pending_payouts", Decimal("0.00"))
        
        return {
            "provider_id": provider_id,
            "period": {"start": start_date, "end": end_date},
            "summary": {
                "total_gross_revenue": total_gross_revenue,
                "total_platform_fees": total_platform_fees,
                "total_processing_fees": total_processing_fees,
                "total_provider_share": total_provider_share,
                "effective_fee_rate": float((total_platform_fees + total_processing_fees) / total_gross_revenue * 100) if total_gross_revenue > 0 else 0
            },
            "current_balance": {
                "available": current_balance,
                "pending_payouts": pending_payouts,
                "total": current_balance + pending_payouts
            },
            "api_breakdown": api_breakdown,
            "transaction_count": len(provider_shares)
        }
    
    async def update_fee_structure(self, new_fees: Dict) -> Dict:
        allowed_fields = ["platform_fee_percentage", "payment_processing_fee", 
                         "minimum_payout", "currency_conversion_fee"]
        
        updated_fields = {}
        for field, value in new_fees.items():
            if field in allowed_fields:
                old_value = self.fee_structures[field]
                self.fee_structures[field] = Decimal(str(value))
                updated_fields[field] = {"old": float(old_value), "new": float(value)}
        
        return {
            "success": True,
            "message": "Fee structure updated",
            "updated_fields": updated_fields,
            "updated_at": datetime.now()
        }
    
    async def set_payout_schedule(self, provider_id: str, schedule_type: str, 
                                 schedule_config: Dict) -> Dict:
        
        schedule_types = ["weekly", "bi_weekly", "monthly", "manual"]
        
        if schedule_type not in schedule_types:
            return {
                "success": False,
                "message": f"Invalid schedule type. Must be one of: {schedule_types}"
            }
        
        schedule = {
            "provider_id": provider_id,
            "schedule_type": schedule_type,
            "config": schedule_config,
            "active": True,
            "created_at": datetime.now(),
            "next_payout_date": await self._calculate_next_payout_date(schedule_type, schedule_config)
        }
        
        self.payout_schedules[provider_id] = schedule
        
        return {
            "success": True,
            "message": f"Payout schedule set to {schedule_type}",
            "next_payout_date": schedule["next_payout_date"]
        }
    
    async def generate_revenue_report(self, provider_id: str = None, 
                                    start_date: datetime = None,
                                    end_date: datetime = None) -> Dict:
        
        if not start_date:
            start_date = datetime.now().replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)
        if not end_date:
            end_date = datetime.now()
        
        report_id = str(uuid.uuid4())
        
        if provider_id:
            filtered_shares = [
                share for share in self.revenue_shares.values()
                if share["provider_id"] == provider_id
                and start_date <= share["created_at"] <= end_date
            ]
        else:
            filtered_shares = [
                share for share in self.revenue_shares.values()
                if start_date <= share["created_at"] <= end_date
            ]
        
        total_transactions = len(filtered_shares)
        total_gross_revenue = sum(share["gross_revenue"] for share in filtered_shares)
        total_platform_fees = sum(share["platform_fee"] for share in filtered_shares)
        total_provider_payouts = sum(share["provider_share"] for share in filtered_shares)
        
        provider_breakdown = {}
        for share in filtered_shares:
            pid = share["provider_id"]
            if pid not in provider_breakdown:
                provider_breakdown[pid] = {
                    "revenue": Decimal("0.00"),
                    "transactions": 0,
                    "payout": Decimal("0.00")
                }
            provider_breakdown[pid]["revenue"] += share["gross_revenue"]
            provider_breakdown[pid]["transactions"] += 1
            provider_breakdown[pid]["payout"] += share["provider_share"]
        
        report = {
            "report_id": report_id,
            "generated_at": datetime.now(),
            "period": {"start": start_date, "end": end_date},
            "summary": {
                "total_transactions": total_transactions,
                "total_gross_revenue": total_gross_revenue,
                "total_platform_fees": total_platform_fees,
                "total_provider_payouts": total_provider_payouts,
                "average_transaction_value": total_gross_revenue / total_transactions if total_transactions > 0 else Decimal("0.00")
            },
            "provider_breakdown": provider_breakdown,
            "top_apis": await self._get_top_apis_by_revenue(filtered_shares)
        }
        
        self.revenue_reports[report_id] = report
        
        return report
    
    async def get_payment_history(self, provider_id: str, limit: int = 50) -> List[Dict]:
        if provider_id not in self.provider_balances:
            return []
        
        payout_history = self.provider_balances[provider_id].get("payout_history", [])
        
        return sorted(
            payout_history,
            key=lambda x: x["initiated_at"],
            reverse=True
        )[:limit]
    
    async def dispute_revenue_calculation(self, share_id: str, provider_id: str, 
                                        reason: str, evidence: Dict) -> Dict:
        
        if share_id not in self.revenue_shares:
            return {
                "success": False,
                "message": "Revenue share record not found"
            }
        
        share = self.revenue_shares[share_id]
        if share["provider_id"] != provider_id:
            return {
                "success": False,
                "message": "Unauthorized to dispute this revenue share"
            }
        
        dispute_id = str(uuid.uuid4())
        
        dispute = {
            "dispute_id": dispute_id,
            "share_id": share_id,
            "provider_id": provider_id,
            "reason": reason,
            "evidence": evidence,
            "status": "under_review",
            "created_at": datetime.now(),
            "resolution": None,
            "resolved_at": None
        }
        
        if "disputes" not in share:
            share["disputes"] = []
        share["disputes"].append(dispute)
        
        return {
            "success": True,
            "dispute_id": dispute_id,
            "status": "under_review",
            "estimated_resolution_time": "3-5 business days"
        }
    
    async def _update_provider_balance(self, provider_id: str, amount: Decimal):
        if provider_id not in self.provider_balances:
            self.provider_balances[provider_id] = {
                "available_balance": Decimal("0.00"),
                "pending_payouts": Decimal("0.00"),
                "total_earned": Decimal("0.00"),
                "last_updated": datetime.now()
            }
        
        self.provider_balances[provider_id]["available_balance"] += amount
        self.provider_balances[provider_id]["total_earned"] += amount
        self.provider_balances[provider_id]["last_updated"] = datetime.now()
    
    async def _get_provider_payment_method(self, provider_id: str) -> Dict:
        return self.payment_methods.get(provider_id, {
            "type": "bank_transfer",
            "account_ending": "****1234",
            "verified": True
        })
    
    async def _initiate_payment_processing(self, payout_record: Dict):
        await asyncio.sleep(0.1)
        payout_record["status"] = "completed"
        payout_record["processed_at"] = datetime.now() + timedelta(days=2)
    
    async def _calculate_next_payout_date(self, schedule_type: str, config: Dict) -> datetime:
        now = datetime.now()
        
        if schedule_type == "weekly":
            return now + timedelta(weeks=1)
        elif schedule_type == "bi_weekly":
            return now + timedelta(weeks=2)
        elif schedule_type == "monthly":
            next_month = now.replace(day=28) + timedelta(days=4)
            return next_month.replace(day=config.get("day_of_month", 1))
        else:
            return None
    
    async def _get_top_apis_by_revenue(self, shares: List[Dict], limit: int = 10) -> List[Dict]:
        api_revenue = {}
        
        for share in shares:
            api_id = share["api_id"]
            if api_id not in api_revenue:
                api_revenue[api_id] = Decimal("0.00")
            api_revenue[api_id] += share["gross_revenue"]
        
        return [
            {"api_id": api_id, "revenue": revenue}
            for api_id, revenue in sorted(
                api_revenue.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]
        ]

revenue_share_manager = RevenueShareManager()