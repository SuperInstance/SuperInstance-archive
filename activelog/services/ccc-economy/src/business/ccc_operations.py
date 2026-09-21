from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from ..database import (
    Business, BusinessRevenue, CCCTransaction, User,
    BusinessType, CCCWallet, CCCTransactionType
)
from ..wallet.wallet_manager import CCCWalletManager
from ..earnings.sales_manager import CCCEarningsManager

logger = logging.getLogger(__name__)

class CCCBusinessManager:
    """Manage business operations entirely in CCC without fiat currency"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_manager = CCCWalletManager(db)
        self.earnings_manager = CCCEarningsManager(db)
        
    async def register_business(
        self,
        owner_id: uuid.UUID,
        business_name: str,
        description: str,
        business_type: BusinessType = BusinessType.STARTUP,
        initial_valuation_ccc: Decimal = Decimal('10000'),
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Register a new CCC-native business"""
        
        try:
            # Verify owner has a wallet
            owner_wallet = await self.wallet_manager.get_wallet_balance(user_id=owner_id)
            if "error" in owner_wallet:
                # Create wallet for business owner
                wallet_result = await self.wallet_manager.create_wallet(
                    user_id=owner_id,
                    initial_balance=Decimal('100')  # Welcome bonus
                )
                if not wallet_result["created"]:
                    return {"success": False, "error": "Failed to create owner wallet"}
            
            # Create business
            business = Business(
                owner_id=owner_id,
                name=business_name,
                description=description,
                business_type=business_type,
                valuation_ccc=initial_valuation_ccc,
                dividend_rate=Decimal('0.1'),  # 10% default dividend rate
                metadata={
                    "registration_date": datetime.utcnow().isoformat(),
                    "currency_type": "CCC_NATIVE",
                    "fiat_free": True,
                    **(metadata or {})
                }
            )
            
            self.db.add(business)
            await self.db.commit()
            await self.db.refresh(business)
            
            # Initialize business revenue tracking
            await self._initialize_business_revenue_tracking(business.id)
            
            return {
                "success": True,
                "business_id": str(business.id),
                "business_name": business.name,
                "owner_id": str(owner_id),
                "business_type": business_type.value,
                "initial_valuation_ccc": float(initial_valuation_ccc),
                "dividend_rate": float(business.dividend_rate),
                "registration_date": business.created_at.isoformat(),
                "ccc_native": True
            }
            
        except Exception as e:
            logger.error(f"Failed to register business: {e}")
            raise
    
    async def operate_business_transaction(
        self,
        business_id: uuid.UUID,
        transaction_type: str,  # "expense", "revenue", "investment", "payroll"
        amount_ccc: Decimal,
        counterparty_id: Optional[uuid.UUID] = None,
        description: str = "",
        category: str = "general",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process any business transaction entirely in CCC"""
        
        try:
            # Get business info
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"success": False, "error": "Business not found"}
            
            # Get business owner wallet
            owner_wallet = await self.wallet_manager.get_wallet_balance(user_id=business.owner_id)
            if "error" in owner_wallet:
                return {"success": False, "error": "Business owner wallet not found"}
            
            owner_wallet_id = uuid.UUID(owner_wallet["wallet_id"])
            
            # Process different transaction types
            if transaction_type == "expense":
                return await self._process_business_expense(
                    business_id, owner_wallet_id, amount_ccc, 
                    counterparty_id, description, category, metadata
                )
            elif transaction_type == "revenue":
                return await self._process_business_revenue(
                    business_id, owner_wallet_id, amount_ccc,
                    counterparty_id, description, category, metadata
                )
            elif transaction_type == "payroll":
                return await self._process_payroll_payment(
                    business_id, owner_wallet_id, amount_ccc,
                    counterparty_id, description, metadata
                )
            elif transaction_type == "investment":
                return await self._process_business_investment(
                    business_id, owner_wallet_id, amount_ccc,
                    description, metadata
                )
            else:
                return {"success": False, "error": f"Unknown transaction type: {transaction_type}"}
                
        except Exception as e:
            logger.error(f"Failed to process business transaction: {e}")
            raise
    
    async def get_business_financials(
        self,
        business_id: uuid.UUID,
        period_months: int = 12
    ) -> Dict[str, Any]:
        """Get comprehensive financial overview for CCC-native business"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_months * 30)
            
            # Get business info
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"error": "Business not found"}
            
            # Get all business transactions
            owner_wallet = await self.wallet_manager.get_wallet_balance(user_id=business.owner_id)
            if "error" in owner_wallet:
                return {"error": "Business wallet not found"}
            
            result = await self.db.execute(
                select(CCCTransaction).where(
                    and_(
                        CCCTransaction.wallet_id == uuid.UUID(owner_wallet["wallet_id"]),
                        CCCTransaction.business_id == business_id,
                        CCCTransaction.created_at >= start_date
                    )
                ).order_by(CCCTransaction.created_at.desc())
            )
            transactions = result.scalars().all()
            
            # Analyze transactions
            total_revenue = Decimal('0')
            total_expenses = Decimal('0')
            payroll_expenses = Decimal('0')
            investment_received = Decimal('0')
            
            revenue_by_month = {}
            expense_by_category = {}
            cash_flow_by_month = {}
            
            for tx in transactions:
                tx_month = tx.created_at.strftime('%Y-%m')
                metadata = tx.metadata or {}
                
                if tx.transaction_type == CCCTransactionType.EARN:
                    total_revenue += tx.amount
                    if tx_month not in revenue_by_month:
                        revenue_by_month[tx_month] = Decimal('0')
                    revenue_by_month[tx_month] += tx.amount
                
                elif tx.transaction_type == CCCTransactionType.SPEND:
                    total_expenses += abs(tx.amount)
                    
                    # Categorize expenses
                    category = metadata.get('category', 'general')
                    if category not in expense_by_category:
                        expense_by_category[category] = Decimal('0')
                    expense_by_category[category] += abs(tx.amount)
                    
                    # Track payroll separately
                    if category == 'payroll':
                        payroll_expenses += abs(tx.amount)
                
                elif tx.transaction_type == CCCTransactionType.INVEST and tx.amount > 0:
                    investment_received += tx.amount
                
                # Monthly cash flow
                if tx_month not in cash_flow_by_month:
                    cash_flow_by_month[tx_month] = Decimal('0')
                cash_flow_by_month[tx_month] += tx.amount
            
            # Calculate financial metrics
            net_profit = total_revenue - total_expenses
            profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Get current cash position
            current_balance = Decimal(str(owner_wallet["available_balance"]))
            
            # Calculate runway (months of operation at current burn rate)
            monthly_expenses = total_expenses / period_months if period_months > 0 else Decimal('0')
            runway_months = float(current_balance / monthly_expenses) if monthly_expenses > 0 else float('inf')
            
            # Convert decimals for JSON serialization
            revenue_by_month_serialized = {month: float(amount) for month, amount in revenue_by_month.items()}
            expense_by_category_serialized = {cat: float(amount) for cat, amount in expense_by_category.items()}
            cash_flow_by_month_serialized = {month: float(amount) for month, amount in cash_flow_by_month.items()}
            
            return {
                "business_id": str(business_id),
                "business_name": business.name,
                "business_type": business.business_type.value,
                "analysis_period_months": period_months,
                "financial_summary": {
                    "total_revenue_ccc": float(total_revenue),
                    "total_expenses_ccc": float(total_expenses),
                    "net_profit_ccc": float(net_profit),
                    "profit_margin_percentage": float(profit_margin),
                    "current_cash_balance_ccc": float(current_balance),
                    "runway_months": runway_months if runway_months != float('inf') else None,
                    "investment_received_ccc": float(investment_received),
                    "payroll_expenses_ccc": float(payroll_expenses)
                },
                "revenue_breakdown": {
                    "monthly_revenue": revenue_by_month_serialized,
                    "average_monthly_revenue": float(total_revenue / period_months) if period_months > 0 else 0
                },
                "expense_breakdown": {
                    "by_category": expense_by_category_serialized,
                    "average_monthly_expenses": float(total_expenses / period_months) if period_months > 0 else 0
                },
                "cash_flow": {
                    "monthly_cash_flow": cash_flow_by_month_serialized,
                    "cash_flow_trend": await self._analyze_cash_flow_trend(cash_flow_by_month)
                },
                "business_health": await self._assess_business_health(
                    net_profit, current_balance, runway_months, total_revenue
                ),
                "ccc_native_metrics": {
                    "fiat_dependency": 0.0,  # 100% CCC operations
                    "currency_stability_score": 9.5,  # High score for CCC stability
                    "transaction_cost_efficiency": 9.8  # Low/no transaction costs in CCC
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get business financials: {e}")
            raise
    
    async def setup_business_payroll(
        self,
        business_id: uuid.UUID,
        employees: List[Dict[str, Any]],
        payment_schedule: str = "monthly"  # monthly, bi_weekly, weekly
    ) -> Dict[str, Any]:
        """Setup CCC-based payroll system for business"""
        
        try:
            # Validate business
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"success": False, "error": "Business not found"}
            
            # Validate employee wallets exist
            payroll_setup = {
                "business_id": str(business_id),
                "payment_schedule": payment_schedule,
                "employees": [],
                "total_monthly_payroll_ccc": Decimal('0'),
                "setup_errors": []
            }
            
            for employee in employees:
                employee_id = uuid.UUID(employee["user_id"])
                salary_ccc = Decimal(str(employee["salary_ccc"]))
                
                # Check employee wallet
                employee_wallet = await self.wallet_manager.get_wallet_balance(user_id=employee_id)
                if "error" in employee_wallet:
                    # Create wallet for employee
                    wallet_result = await self.wallet_manager.create_wallet(user_id=employee_id)
                    if not wallet_result["created"]:
                        payroll_setup["setup_errors"].append(f"Failed to create wallet for employee {employee_id}")
                        continue
                    employee_wallet = await self.wallet_manager.get_wallet_balance(user_id=employee_id)
                
                payroll_setup["employees"].append({
                    "user_id": str(employee_id),
                    "name": employee.get("name", "Unknown"),
                    "position": employee.get("position", "Employee"),
                    "salary_ccc": float(salary_ccc),
                    "wallet_id": employee_wallet["wallet_id"],
                    "wallet_address": employee_wallet["wallet_address"]
                })
                
                payroll_setup["total_monthly_payroll_ccc"] += salary_ccc
            
            # Store payroll configuration in business metadata
            business_metadata = business.metadata or {}
            business_metadata["payroll"] = {
                "schedule": payment_schedule,
                "employees": payroll_setup["employees"],
                "total_monthly": float(payroll_setup["total_monthly_payroll_ccc"]),
                "setup_date": datetime.utcnow().isoformat()
            }
            business.metadata = business_metadata
            await self.db.commit()
            
            return {
                "success": True,
                **payroll_setup,
                "total_monthly_payroll_ccc": float(payroll_setup["total_monthly_payroll_ccc"])
            }
            
        except Exception as e:
            logger.error(f"Failed to setup business payroll: {e}")
            raise
    
    async def process_payroll_payments(
        self,
        business_id: uuid.UUID,
        pay_period_start: datetime,
        pay_period_end: datetime,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process payroll payments for all employees"""
        
        try:
            # Get business and payroll info
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"success": False, "error": "Business not found"}
            
            payroll_info = business.metadata.get("payroll") if business.metadata else None
            if not payroll_info:
                return {"success": False, "error": "Payroll not configured for this business"}
            
            # Get business owner wallet
            owner_wallet = await self.wallet_manager.get_wallet_balance(user_id=business.owner_id)
            if "error" in owner_wallet:
                return {"success": False, "error": "Business wallet not found"}
            
            owner_wallet_id = uuid.UUID(owner_wallet["wallet_id"])
            
            # Calculate total payroll needed
            total_payroll = Decimal('0')
            for employee in payroll_info["employees"]:
                total_payroll += Decimal(str(employee["salary_ccc"]))
            
            # Check business has sufficient funds
            if owner_wallet["available_balance"] < float(total_payroll):
                return {
                    "success": False,
                    "error": "Insufficient funds for payroll",
                    "required": float(total_payroll),
                    "available": owner_wallet["available_balance"]
                }
            
            # Process payments to each employee
            payment_results = []
            successful_payments = 0
            total_paid = Decimal('0')
            
            for employee in payroll_info["employees"]:
                employee_id = uuid.UUID(employee["user_id"])
                salary = Decimal(str(employee["salary_ccc"]))
                
                try:
                    # Transfer payment from business to employee
                    transfer_result = await self.wallet_manager.transfer_ccc(
                        sender_wallet_id=owner_wallet_id,
                        recipient_wallet_id=uuid.UUID(employee["wallet_id"]),
                        amount=salary,
                        description=f"Payroll: {employee['name']} - {pay_period_start.strftime('%Y-%m')}",
                        metadata={
                            "payroll_payment": True,
                            "employee_id": str(employee_id),
                            "employee_name": employee["name"],
                            "employee_position": employee["position"],
                            "pay_period_start": pay_period_start.isoformat(),
                            "pay_period_end": pay_period_end.isoformat(),
                            **(metadata or {})
                        }
                    )
                    
                    if transfer_result["success"]:
                        successful_payments += 1
                        total_paid += salary
                        
                        payment_results.append({
                            "employee_id": str(employee_id),
                            "employee_name": employee["name"],
                            "amount_paid": float(salary),
                            "status": "success",
                            "transaction_id": transfer_result["sender_transaction_id"]
                        })
                    else:
                        payment_results.append({
                            "employee_id": str(employee_id),
                            "employee_name": employee["name"],
                            "amount_paid": 0,
                            "status": "failed",
                            "error": transfer_result.get("error", "Unknown error")
                        })
                        
                except Exception as e:
                    payment_results.append({
                        "employee_id": str(employee_id),
                        "employee_name": employee["name"],
                        "amount_paid": 0,
                        "status": "error",
                        "error": str(e)
                    })
            
            # Record payroll expense in business records
            if total_paid > 0:
                await self.operate_business_transaction(
                    business_id=business_id,
                    transaction_type="payroll",
                    amount_ccc=total_paid,
                    description=f"Payroll payments for {pay_period_start.strftime('%Y-%m')}",
                    category="payroll",
                    metadata={
                        "pay_period_start": pay_period_start.isoformat(),
                        "pay_period_end": pay_period_end.isoformat(),
                        "employees_paid": successful_payments,
                        "total_employees": len(payroll_info["employees"])
                    }
                )
            
            return {
                "success": successful_payments > 0,
                "payroll_summary": {
                    "total_employees": len(payroll_info["employees"]),
                    "successful_payments": successful_payments,
                    "failed_payments": len(payroll_info["employees"]) - successful_payments,
                    "total_amount_paid_ccc": float(total_paid),
                    "pay_period": f"{pay_period_start.strftime('%Y-%m-%d')} to {pay_period_end.strftime('%Y-%m-%d')}"
                },
                "payment_details": payment_results,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process payroll payments: {e}")
            raise
    
    async def create_business_budget(
        self,
        business_id: uuid.UUID,
        budget_period_months: int,
        budget_categories: Dict[str, Decimal],
        revenue_projections: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """Create a CCC-based budget for business operations"""
        
        try:
            # Get business
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"success": False, "error": "Business not found"}
            
            # Calculate budget totals
            total_budgeted_expenses = sum(budget_categories.values())
            total_projected_revenue = sum(revenue_projections.values())
            projected_net_income = total_projected_revenue - total_budgeted_expenses
            
            # Create budget record
            budget = {
                "budget_id": str(uuid.uuid4()),
                "business_id": str(business_id),
                "period_months": budget_period_months,
                "created_date": datetime.utcnow().isoformat(),
                "budget_categories": {cat: float(amount) for cat, amount in budget_categories.items()},
                "revenue_projections": {cat: float(amount) for cat, amount in revenue_projections.items()},
                "totals": {
                    "total_budgeted_expenses_ccc": float(total_budgeted_expenses),
                    "total_projected_revenue_ccc": float(total_projected_revenue),
                    "projected_net_income_ccc": float(projected_net_income),
                    "break_even_required": float(total_budgeted_expenses)
                },
                "budget_health": {
                    "is_profitable": projected_net_income > 0,
                    "profit_margin_projected": float((projected_net_income / total_projected_revenue) * 100) if total_projected_revenue > 0 else 0,
                    "expense_ratio": float((total_budgeted_expenses / total_projected_revenue) * 100) if total_projected_revenue > 0 else 100
                }
            }
            
            # Store budget in business metadata
            business_metadata = business.metadata or {}
            if "budgets" not in business_metadata:
                business_metadata["budgets"] = []
            business_metadata["budgets"].append(budget)
            business.metadata = business_metadata
            await self.db.commit()
            
            return {
                "success": True,
                **budget
            }
            
        except Exception as e:
            logger.error(f"Failed to create business budget: {e}")
            raise
    
    async def _process_business_expense(
        self,
        business_id: uuid.UUID,
        owner_wallet_id: uuid.UUID,
        amount_ccc: Decimal,
        counterparty_id: Optional[uuid.UUID],
        description: str,
        category: str,
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Process a business expense"""
        
        # Spend CCC from business wallet
        spend_result = await self.wallet_manager.spend_ccc(
            wallet_id=owner_wallet_id,
            amount=amount_ccc,
            purpose=f"Business Expense: {description}",
            business_id=business_id,
            metadata={
                "expense_category": category,
                "counterparty_id": str(counterparty_id) if counterparty_id else None,
                **(metadata or {})
            }
        )
        
        if not spend_result["success"]:
            return spend_result
        
        # If counterparty specified, transfer to their wallet
        if counterparty_id:
            counterparty_wallet = await self.wallet_manager.get_wallet_balance(user_id=counterparty_id)
            if "error" not in counterparty_wallet:
                await self.wallet_manager.add_ccc_earnings(
                    wallet_id=uuid.UUID(counterparty_wallet["wallet_id"]),
                    amount=amount_ccc,
                    source=f"Payment from business: {description}",
                    metadata={"business_payment": True, "business_id": str(business_id)}
                )
        
        return {
            "success": True,
            "transaction_type": "expense",
            "amount_ccc": float(amount_ccc),
            "category": category,
            "description": description,
            "transaction_id": spend_result["transaction_id"]
        }
    
    async def _process_business_revenue(
        self,
        business_id: uuid.UUID,
        owner_wallet_id: uuid.UUID,
        amount_ccc: Decimal,
        counterparty_id: Optional[uuid.UUID],
        description: str,
        category: str,
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Process business revenue"""
        
        earnings_result = await self.wallet_manager.add_ccc_earnings(
            wallet_id=owner_wallet_id,
            amount=amount_ccc,
            source=f"Business Revenue: {description}",
            business_id=business_id,
            metadata={
                "revenue_category": category,
                "counterparty_id": str(counterparty_id) if counterparty_id else None,
                **(metadata or {})
            }
        )
        
        return {
            "success": earnings_result["success"],
            "transaction_type": "revenue",
            "amount_ccc": float(amount_ccc),
            "category": category,
            "description": description,
            "transaction_id": earnings_result["transaction_id"]
        }
    
    async def _process_payroll_payment(
        self,
        business_id: uuid.UUID,
        owner_wallet_id: uuid.UUID,
        amount_ccc: Decimal,
        employee_id: uuid.UUID,
        description: str,
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Process a single payroll payment"""
        
        if not employee_id:
            return {"success": False, "error": "Employee ID required for payroll"}
        
        employee_wallet = await self.wallet_manager.get_wallet_balance(user_id=employee_id)
        if "error" in employee_wallet:
            return {"success": False, "error": "Employee wallet not found"}
        
        # Transfer from business to employee
        transfer_result = await self.wallet_manager.transfer_ccc(
            sender_wallet_id=owner_wallet_id,
            recipient_wallet_id=uuid.UUID(employee_wallet["wallet_id"]),
            amount=amount_ccc,
            description=f"Payroll: {description}",
            metadata={
                "payroll_payment": True,
                "employee_id": str(employee_id),
                **(metadata or {})
            }
        )
        
        return {
            "success": transfer_result["success"],
            "transaction_type": "payroll",
            "amount_ccc": float(amount_ccc),
            "employee_id": str(employee_id),
            "description": description,
            "transaction_id": transfer_result.get("sender_transaction_id")
        }
    
    async def _process_business_investment(
        self,
        business_id: uuid.UUID,
        owner_wallet_id: uuid.UUID,
        amount_ccc: Decimal,
        description: str,
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Process business investment (capital expenditure)"""
        
        spend_result = await self.wallet_manager.spend_ccc(
            wallet_id=owner_wallet_id,
            amount=amount_ccc,
            purpose=f"Business Investment: {description}",
            business_id=business_id,
            metadata={
                "investment_transaction": True,
                "investment_type": "business_capex",
                **(metadata or {})
            }
        )
        
        return {
            "success": spend_result["success"],
            "transaction_type": "investment",
            "amount_ccc": float(amount_ccc),
            "description": description,
            "transaction_id": spend_result["transaction_id"]
        }
    
    async def _initialize_business_revenue_tracking(self, business_id: uuid.UUID) -> None:
        """Initialize revenue tracking for new business"""
        
        # Create initial revenue record for current month
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
        
        revenue_record = BusinessRevenue(
            business_id=business_id,
            revenue_period_start=period_start,
            revenue_period_end=period_end,
            total_revenue_ccc=Decimal('0'),
            net_profit_ccc=Decimal('0'),
            revenue_sources={}
        )
        
        self.db.add(revenue_record)
        await self.db.commit()
    
    async def _analyze_cash_flow_trend(self, cash_flow_by_month: Dict[str, Decimal]) -> str:
        """Analyze cash flow trend over time"""
        
        if len(cash_flow_by_month) < 2:
            return "insufficient_data"
        
        values = list(cash_flow_by_month.values())
        recent_avg = sum(values[-3:]) / len(values[-3:])  # Last 3 months
        older_avg = sum(values[:-3]) / len(values[:-3]) if len(values) > 3 else values[0]
        
        if recent_avg > older_avg * Decimal('1.1'):
            return "improving"
        elif recent_avg < older_avg * Decimal('0.9'):
            return "declining"
        else:
            return "stable"
    
    async def _assess_business_health(
        self,
        net_profit: Decimal,
        current_balance: Decimal,
        runway_months: float,
        total_revenue: Decimal
    ) -> Dict[str, Any]:
        """Assess overall business health"""
        
        health_score = 5.0  # Base score out of 10
        
        # Profitability impact
        if net_profit > 0:
            health_score += 2.0
        elif net_profit < total_revenue * Decimal('-0.2'):  # Losing more than 20%
            health_score -= 2.0
        
        # Cash position impact
        if current_balance > total_revenue * Decimal('0.5'):  # 6+ months expenses
            health_score += 1.5
        elif current_balance < total_revenue * Decimal('0.1'):  # Less than 1 month
            health_score -= 1.5
        
        # Runway impact
        if runway_months and runway_months > 12:
            health_score += 1.0
        elif runway_months and runway_months < 3:
            health_score -= 2.0
        
        health_score = max(0.0, min(10.0, health_score))  # Cap between 0-10
        
        # Health assessment
        if health_score >= 8:
            assessment = "excellent"
        elif health_score >= 6:
            assessment = "good"
        elif health_score >= 4:
            assessment = "fair"
        else:
            assessment = "poor"
        
        return {
            "health_score": round(health_score, 1),
            "assessment": assessment,
            "is_profitable": net_profit > 0,
            "runway_adequate": runway_months is None or runway_months > 6,
            "cash_position": "strong" if current_balance > total_revenue * Decimal('0.3') else "weak"
        }