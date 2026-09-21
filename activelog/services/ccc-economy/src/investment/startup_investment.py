from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from ..database import (
    CCCInvestment, Business, User, CCCWallet, 
    InvestmentStatus, BusinessType, CCCTransaction, CCCTransactionType
)
from ..wallet.wallet_manager import CCCWalletManager

logger = logging.getLogger(__name__)

class CCCInvestmentManager:
    """Manage CCC-based startup investment system"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_manager = CCCWalletManager(db)
        self.min_investment_amount = Decimal('100.0')  # Minimum 100 CCC investment
        self.max_equity_per_investment = Decimal('49.99')  # Max 49.99% per single investment
        
    async def create_investment_opportunity(
        self,
        business_id: uuid.UUID,
        equity_percentage_offered: Decimal,
        valuation_ccc: Decimal,
        minimum_investment_ccc: Decimal,
        maximum_investment_ccc: Optional[Decimal] = None,
        investment_terms: Dict[str, Any] = None,
        requires_accredited: bool = False
    ) -> Dict[str, Any]:
        """Create an investment opportunity for a startup"""
        
        try:
            # Validate business exists and is eligible for investment
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"success": False, "error": "Business not found"}
            
            if equity_percentage_offered > self.max_equity_per_investment:
                return {
                    "success": False, 
                    "error": f"Cannot offer more than {self.max_equity_per_investment}% equity in single round"
                }
            
            # Calculate investment amount needed
            investment_amount_needed = (valuation_ccc * equity_percentage_offered) / 100
            
            # Update business for public investment
            business.is_public = True
            business.valuation_ccc = valuation_ccc
            business.requires_accredited_investors = requires_accredited
            
            # Store investment opportunity details in metadata
            investment_opportunity = {
                "equity_offered": float(equity_percentage_offered),
                "valuation_ccc": float(valuation_ccc),
                "investment_needed_ccc": float(investment_amount_needed),
                "minimum_investment_ccc": float(minimum_investment_ccc),
                "maximum_investment_ccc": float(maximum_investment_ccc) if maximum_investment_ccc else None,
                "requires_accredited": requires_accredited,
                "investment_terms": investment_terms or {},
                "opportunity_created": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            business_metadata = business.metadata or {}
            business_metadata["investment_opportunity"] = investment_opportunity
            business.metadata = business_metadata
            
            await self.db.commit()
            
            return {
                "success": True,
                "business_id": str(business_id),
                "business_name": business.name,
                "investment_opportunity": investment_opportunity,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create investment opportunity: {e}")
            raise
    
    async def make_investment(
        self,
        investor_id: uuid.UUID,
        business_id: uuid.UUID,
        investment_amount_ccc: Decimal,
        expected_return_percentage: Optional[Decimal] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process an investment in a startup"""
        
        try:
            # Validate investment amount
            if investment_amount_ccc < self.min_investment_amount:
                return {
                    "success": False,
                    "error": f"Minimum investment is {self.min_investment_amount} CCC"
                }
            
            # Get business and validate investment opportunity
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"success": False, "error": "Business not found"}
            
            if not business.is_public:
                return {"success": False, "error": "Business not accepting public investment"}
            
            # Get investment opportunity details
            investment_opp = business.metadata.get("investment_opportunity") if business.metadata else None
            if not investment_opp or investment_opp.get("status") != "active":
                return {"success": False, "error": "No active investment opportunity"}
            
            # Check investment limits
            min_investment = Decimal(str(investment_opp["minimum_investment_ccc"]))
            max_investment = Decimal(str(investment_opp["maximum_investment_ccc"])) if investment_opp.get("maximum_investment_ccc") else None
            
            if investment_amount_ccc < min_investment:
                return {
                    "success": False,
                    "error": f"Investment below minimum of {min_investment} CCC"
                }
            
            if max_investment and investment_amount_ccc > max_investment:
                return {
                    "success": False,
                    "error": f"Investment exceeds maximum of {max_investment} CCC"
                }
            
            # Check if accredited investor required
            if business.requires_accredited_investors:
                result = await self.db.execute(
                    select(User).where(User.id == investor_id)
                )
                investor = result.scalar_one_or_none()
                
                if not investor or not investor.is_accredited_investor:
                    return {
                        "success": False,
                        "error": "This investment requires accredited investor status"
                    }
            
            # Calculate equity percentage for this investment
            business_valuation = Decimal(str(investment_opp["valuation_ccc"]))
            equity_percentage = (investment_amount_ccc / business_valuation) * 100
            
            # Check total equity available
            current_equity_sold = await self._get_total_equity_sold(business_id)
            if current_equity_sold + equity_percentage > Decimal(str(investment_opp["equity_offered"])):
                return {
                    "success": False,
                    "error": f"Not enough equity available. Remaining: {float(Decimal(str(investment_opp['equity_offered'])) - current_equity_sold):.4f}%"
                }
            
            # Get investor wallet and check balance
            investor_wallet = await self.wallet_manager.get_wallet_balance(user_id=investor_id)
            if "error" in investor_wallet:
                return {"success": False, "error": "Investor wallet not found"}
            
            if investor_wallet["available_balance"] < float(investment_amount_ccc):
                return {
                    "success": False,
                    "error": "Insufficient CCC balance for investment",
                    "available_balance": investor_wallet["available_balance"],
                    "required_amount": float(investment_amount_ccc)
                }
            
            # Lock investor funds for investment
            lock_result = await self.wallet_manager.lock_ccc_for_investment(
                wallet_id=uuid.UUID(investor_wallet["wallet_id"]),
                amount=investment_amount_ccc,
                investment_id=uuid.uuid4(),  # Temporary ID, will update after creating investment
                lock_reason=f"Investment in {business.name}"
            )
            
            if not lock_result["success"]:
                return {"success": False, "error": "Failed to lock investment funds"}
            
            # Create investment record
            investment = CCCInvestment(
                investor_id=investor_id,
                business_id=business_id,
                investment_amount_ccc=investment_amount_ccc,
                equity_percentage=equity_percentage,
                status=InvestmentStatus.ACTIVE,
                expected_return_percentage=expected_return_percentage,
                lock_period_months=investment_opp.get("lock_period_months", 12),
                unlock_date=datetime.utcnow() + timedelta(days=investment_opp.get("lock_period_months", 12) * 30),
                metadata={
                    "investment_terms": investment_opp.get("investment_terms", {}),
                    "business_valuation_at_investment": float(business_valuation),
                    "investor_type": "accredited" if business.requires_accredited_investors else "retail",
                    **(metadata or {})
                }
            )
            
            self.db.add(investment)
            await self.db.commit()
            await self.db.refresh(investment)
            
            # Transfer funds to business owner
            business_owner_wallet = await self.wallet_manager.get_wallet_balance(user_id=business.owner_id)
            if "error" not in business_owner_wallet:
                # Unlock from investor and transfer to business
                await self.wallet_manager.unlock_ccc_from_investment(
                    wallet_id=uuid.UUID(investor_wallet["wallet_id"]),
                    amount=investment_amount_ccc,
                    investment_id=investment.id,
                    unlock_reason="Investment funds transferred to business"
                )
                
                # Transfer to business owner
                transfer_result = await self.wallet_manager.transfer_ccc(
                    sender_wallet_id=uuid.UUID(investor_wallet["wallet_id"]),
                    recipient_wallet_id=uuid.UUID(business_owner_wallet["wallet_id"]),
                    amount=investment_amount_ccc,
                    description=f"Investment in {business.name}",
                    metadata={
                        "investment_id": str(investment.id),
                        "equity_percentage": float(equity_percentage),
                        "business_valuation": float(business_valuation)
                    }
                )
                
                if not transfer_result["success"]:
                    # Rollback investment if transfer fails
                    investment.status = InvestmentStatus.FAILED
                    await self.db.commit()
                    return {"success": False, "error": "Failed to transfer investment funds"}
            
            # Update business total equity and valuation
            business.total_equity -= equity_percentage  # Reduce available equity
            await self.db.commit()
            
            # Generate investment certificate
            certificate = await self._generate_investment_certificate(investment)
            
            return {
                "success": True,
                "investment_id": str(investment.id),
                "investor_id": str(investor_id),
                "business_id": str(business_id),
                "business_name": business.name,
                "investment_amount_ccc": float(investment_amount_ccc),
                "equity_percentage": float(equity_percentage),
                "expected_return_percentage": float(expected_return_percentage) if expected_return_percentage else None,
                "lock_period_months": investment.lock_period_months,
                "unlock_date": investment.unlock_date.isoformat(),
                "investment_certificate": certificate,
                "investment_date": investment.investment_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process investment: {e}")
            raise
    
    async def get_investment_portfolio(
        self,
        investor_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get investment portfolio for an investor"""
        
        try:
            # Get all investments by investor
            result = await self.db.execute(
                select(CCCInvestment).where(
                    CCCInvestment.investor_id == investor_id
                ).order_by(CCCInvestment.investment_date.desc())
            )
            investments = result.scalars().all()
            
            if not investments:
                return {
                    "investor_id": str(investor_id),
                    "total_investments": 0,
                    "message": "No investments found"
                }
            
            # Calculate portfolio metrics
            total_invested = sum(inv.investment_amount_ccc for inv in investments)
            total_equity_owned = sum(inv.equity_percentage for inv in investments)
            active_investments = len([inv for inv in investments if inv.status == InvestmentStatus.ACTIVE])
            
            # Get business details for each investment
            portfolio_details = []
            current_portfolio_value = Decimal('0')
            
            for investment in investments:
                # Get business info
                result = await self.db.execute(
                    select(Business).where(Business.id == investment.business_id)
                )
                business = result.scalar_one_or_none()
                
                if business:
                    # Calculate current value based on business current valuation
                    current_investment_value = (business.valuation_ccc * investment.equity_percentage) / 100
                    current_portfolio_value += current_investment_value
                    
                    # Calculate return
                    return_amount = current_investment_value - investment.investment_amount_ccc
                    return_percentage = (return_amount / investment.investment_amount_ccc) * 100 if investment.investment_amount_ccc > 0 else 0
                    
                    portfolio_details.append({
                        "investment_id": str(investment.id),
                        "business_id": str(business.id),
                        "business_name": business.name,
                        "business_type": business.business_type.value,
                        "investment_amount_ccc": float(investment.investment_amount_ccc),
                        "equity_percentage": float(investment.equity_percentage),
                        "current_value_ccc": float(current_investment_value),
                        "return_amount_ccc": float(return_amount),
                        "return_percentage": float(return_percentage),
                        "investment_date": investment.investment_date.isoformat(),
                        "status": investment.status.value,
                        "is_dividend_eligible": investment.is_dividend_eligible,
                        "unlock_date": investment.unlock_date.isoformat() if investment.unlock_date else None
                    })
            
            # Calculate overall portfolio performance
            total_return = current_portfolio_value - total_invested
            total_return_percentage = (total_return / total_invested) * 100 if total_invested > 0 else 0
            
            # Diversification analysis
            business_types = {}
            for detail in portfolio_details:
                btype = detail["business_type"]
                if btype not in business_types:
                    business_types[btype] = {"count": 0, "invested_amount": 0}
                business_types[btype]["count"] += 1
                business_types[btype]["invested_amount"] += detail["investment_amount_ccc"]
            
            return {
                "investor_id": str(investor_id),
                "portfolio_summary": {
                    "total_investments": len(investments),
                    "active_investments": active_investments,
                    "total_invested_ccc": float(total_invested),
                    "current_portfolio_value_ccc": float(current_portfolio_value),
                    "total_return_ccc": float(total_return),
                    "total_return_percentage": float(total_return_percentage),
                    "total_equity_owned": float(total_equity_owned)
                },
                "investments": portfolio_details,
                "diversification": {
                    "business_types": business_types,
                    "diversification_score": len(business_types) / len(investments) if investments else 0
                },
                "performance_metrics": await self._calculate_performance_metrics(investments),
                "portfolio_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get investment portfolio: {e}")
            raise
    
    async def get_business_investors(
        self,
        business_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get all investors for a business"""
        
        try:
            # Get business info
            result = await self.db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                return {"error": "Business not found"}
            
            # Get all investments in this business
            result = await self.db.execute(
                select(CCCInvestment).where(
                    CCCInvestment.business_id == business_id
                ).order_by(CCCInvestment.investment_date.desc())
            )
            investments = result.scalars().all()
            
            if not investments:
                return {
                    "business_id": str(business_id),
                    "business_name": business.name,
                    "total_investors": 0,
                    "message": "No investors found"
                }
            
            # Aggregate investor information
            investors_summary = {}
            total_investment_received = Decimal('0')
            total_equity_sold = Decimal('0')
            
            for investment in investments:
                investor_id_str = str(investment.investor_id)
                
                if investor_id_str not in investors_summary:
                    # Get investor details
                    result = await self.db.execute(
                        select(User).where(User.id == investment.investor_id)
                    )
                    investor = result.scalar_one_or_none()
                    
                    investors_summary[investor_id_str] = {
                        "investor_id": investor_id_str,
                        "investor_name": investor.full_name if investor else "Unknown",
                        "investor_email": investor.email if investor else "Unknown",
                        "is_accredited": investor.is_accredited_investor if investor else False,
                        "total_invested_ccc": Decimal('0'),
                        "total_equity_percentage": Decimal('0'),
                        "investment_count": 0,
                        "first_investment_date": investment.investment_date,
                        "investments": []
                    }
                
                # Add investment to investor summary
                investor_summary = investors_summary[investor_id_str]
                investor_summary["total_invested_ccc"] += investment.investment_amount_ccc
                investor_summary["total_equity_percentage"] += investment.equity_percentage
                investor_summary["investment_count"] += 1
                
                if investment.investment_date < investor_summary["first_investment_date"]:
                    investor_summary["first_investment_date"] = investment.investment_date
                
                investor_summary["investments"].append({
                    "investment_id": str(investment.id),
                    "amount_ccc": float(investment.investment_amount_ccc),
                    "equity_percentage": float(investment.equity_percentage),
                    "investment_date": investment.investment_date.isoformat(),
                    "status": investment.status.value
                })
                
                total_investment_received += investment.investment_amount_ccc
                total_equity_sold += investment.equity_percentage
            
            # Convert to serializable format
            investors_list = []
            for investor_data in investors_summary.values():
                investors_list.append({
                    **investor_data,
                    "total_invested_ccc": float(investor_data["total_invested_ccc"]),
                    "total_equity_percentage": float(investor_data["total_equity_percentage"]),
                    "first_investment_date": investor_data["first_investment_date"].isoformat(),
                    "ownership_rank": 0  # Will be set after sorting
                })
            
            # Sort by equity percentage and set ranks
            investors_list.sort(key=lambda x: x["total_equity_percentage"], reverse=True)
            for i, investor in enumerate(investors_list):
                investor["ownership_rank"] = i + 1
            
            return {
                "business_id": str(business_id),
                "business_name": business.name,
                "business_type": business.business_type.value,
                "investment_summary": {
                    "total_investors": len(investors_summary),
                    "total_investment_received_ccc": float(total_investment_received),
                    "total_equity_sold_percentage": float(total_equity_sold),
                    "remaining_equity_percentage": float(business.total_equity),
                    "current_valuation_ccc": float(business.valuation_ccc)
                },
                "investors": investors_list,
                "investor_analysis": await self._analyze_investor_base(investors_list),
                "analysis_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get business investors: {e}")
            raise
    
    async def process_investment_exit(
        self,
        investment_id: uuid.UUID,
        exit_type: str,  # "sale", "buyback", "acquisition"
        exit_amount_ccc: Decimal,
        exit_reason: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process an investment exit/liquidation"""
        
        try:
            # Get investment
            result = await self.db.execute(
                select(CCCInvestment).where(CCCInvestment.id == investment_id)
            )
            investment = result.scalar_one_or_none()
            
            if not investment:
                return {"success": False, "error": "Investment not found"}
            
            if investment.status != InvestmentStatus.ACTIVE:
                return {"success": False, "error": "Investment is not active"}
            
            # Check if investment is locked
            if investment.unlock_date and datetime.utcnow() < investment.unlock_date:
                return {
                    "success": False,
                    "error": f"Investment locked until {investment.unlock_date.isoformat()}",
                    "unlock_date": investment.unlock_date.isoformat()
                }
            
            # Get investor wallet
            investor_wallet = await self.wallet_manager.get_wallet_balance(user_id=investment.investor_id)
            if "error" in investor_wallet:
                return {"success": False, "error": "Investor wallet not found"}
            
            # Calculate return
            return_amount = exit_amount_ccc - investment.investment_amount_ccc
            return_percentage = (return_amount / investment.investment_amount_ccc) * 100 if investment.investment_amount_ccc > 0 else 0
            
            # Process exit payment to investor
            exit_payment_result = await self.wallet_manager.add_ccc_earnings(
                wallet_id=uuid.UUID(investor_wallet["wallet_id"]),
                amount=exit_amount_ccc,
                source=f"Investment Exit: {exit_reason}",
                metadata={
                    "investment_exit": True,
                    "investment_id": str(investment_id),
                    "exit_type": exit_type,
                    "original_investment": float(investment.investment_amount_ccc),
                    "exit_amount": float(exit_amount_ccc),
                    "return_amount": float(return_amount),
                    "return_percentage": float(return_percentage),
                    **(metadata or {})
                }
            )
            
            if not exit_payment_result["success"]:
                return {"success": False, "error": "Failed to process exit payment"}
            
            # Update investment status
            investment.status = InvestmentStatus.COMPLETED
            investment.metadata = investment.metadata or {}
            investment.metadata.update({
                "exit_processed": True,
                "exit_date": datetime.utcnow().isoformat(),
                "exit_type": exit_type,
                "exit_amount_ccc": float(exit_amount_ccc),
                "exit_reason": exit_reason,
                "return_amount": float(return_amount),
                "return_percentage": float(return_percentage)
            })
            
            # Return equity to business
            result = await self.db.execute(
                select(Business).where(Business.id == investment.business_id)
            )
            business = result.scalar_one_or_none()
            
            if business:
                business.total_equity += investment.equity_percentage
                
            await self.db.commit()
            
            return {
                "success": True,
                "investment_id": str(investment_id),
                "exit_type": exit_type,
                "original_investment_ccc": float(investment.investment_amount_ccc),
                "exit_amount_ccc": float(exit_amount_ccc),
                "return_amount_ccc": float(return_amount),
                "return_percentage": float(return_percentage),
                "equity_percentage": float(investment.equity_percentage),
                "exit_date": datetime.utcnow().isoformat(),
                "transaction_id": exit_payment_result["transaction_id"]
            }
            
        except Exception as e:
            logger.error(f"Failed to process investment exit: {e}")
            raise
    
    async def _get_total_equity_sold(self, business_id: uuid.UUID) -> Decimal:
        """Get total equity sold for a business"""
        
        result = await self.db.execute(
            select(func.sum(CCCInvestment.equity_percentage)).where(
                and_(
                    CCCInvestment.business_id == business_id,
                    CCCInvestment.status == InvestmentStatus.ACTIVE
                )
            )
        )
        
        return result.scalar() or Decimal('0')
    
    async def _generate_investment_certificate(self, investment: CCCInvestment) -> Dict[str, Any]:
        """Generate investment certificate/documentation"""
        
        # Get business details
        result = await self.db.execute(
            select(Business).where(Business.id == investment.business_id)
        )
        business = result.scalar_one_or_none()
        
        certificate = {
            "certificate_id": str(uuid.uuid4()),
            "investment_id": str(investment.id),
            "investor_id": str(investment.investor_id),
            "business_name": business.name if business else "Unknown",
            "business_id": str(investment.business_id),
            "equity_percentage": float(investment.equity_percentage),
            "investment_amount_ccc": float(investment.investment_amount_ccc),
            "investment_date": investment.investment_date.isoformat(),
            "lock_period_months": investment.lock_period_months,
            "unlock_date": investment.unlock_date.isoformat() if investment.unlock_date else None,
            "dividend_eligible": investment.is_dividend_eligible,
            "certificate_issued": datetime.utcnow().isoformat(),
            "legal_text": "This certificate represents ownership in the above business as recorded in the CCC Economy blockchain.",
            "verification_hash": f"CCC-{str(investment.id)[:8]}-{str(investment.business_id)[:8]}"
        }
        
        return certificate
    
    async def _calculate_performance_metrics(self, investments: List[CCCInvestment]) -> Dict[str, Any]:
        """Calculate portfolio performance metrics"""
        
        if not investments:
            return {"no_data": True}
        
        # Calculate age-weighted returns
        total_weighted_return = Decimal('0')
        total_weight = Decimal('0')
        
        for investment in investments:
            age_days = (datetime.utcnow() - investment.investment_date).days
            weight = Decimal(str(age_days)) if age_days > 0 else Decimal('1')
            
            # Simplified return calculation (would need current business valuation for accurate calculation)
            estimated_return = Decimal('0.1') * (age_days / 365)  # 10% annual return estimate
            
            total_weighted_return += estimated_return * weight
            total_weight += weight
        
        avg_weighted_return = total_weighted_return / total_weight if total_weight > 0 else Decimal('0')
        
        # Risk metrics
        active_investments = [inv for inv in investments if inv.status == InvestmentStatus.ACTIVE]
        failed_investments = [inv for inv in investments if inv.status == InvestmentStatus.FAILED]
        
        success_rate = len(active_investments) / len(investments) * 100 if investments else 0
        
        return {
            "average_weighted_return": float(avg_weighted_return),
            "success_rate_percentage": success_rate,
            "active_investments": len(active_investments),
            "failed_investments": len(failed_investments),
            "portfolio_age_days": (datetime.utcnow() - min(inv.investment_date for inv in investments)).days if investments else 0
        }
    
    async def _analyze_investor_base(self, investors: List[Dict]) -> Dict[str, Any]:
        """Analyze the investor base composition"""
        
        if not investors:
            return {"no_data": True}
        
        # Analyze investor types
        accredited_count = len([inv for inv in investors if inv["is_accredited"]])
        retail_count = len(investors) - accredited_count
        
        # Analyze investment concentration
        total_invested = sum(inv["total_invested_ccc"] for inv in investors)
        largest_investor_percentage = max(inv["total_invested_ccc"] for inv in investors) / total_invested * 100 if total_invested > 0 else 0
        
        # Calculate equity distribution
        total_equity_sold = sum(inv["total_equity_percentage"] for inv in investors)
        largest_equity_holder = max(inv["total_equity_percentage"] for inv in investors) if investors else 0
        
        return {
            "investor_composition": {
                "accredited_investors": accredited_count,
                "retail_investors": retail_count,
                "accredited_percentage": (accredited_count / len(investors)) * 100
            },
            "concentration_metrics": {
                "total_investors": len(investors),
                "largest_investor_percentage": largest_investor_percentage,
                "largest_equity_holder_percentage": largest_equity_holder,
                "concentration_risk": "high" if largest_equity_holder > 25 else "moderate" if largest_equity_holder > 10 else "low"
            },
            "investment_distribution": {
                "total_equity_distributed": total_equity_sold,
                "average_equity_per_investor": total_equity_sold / len(investors) if investors else 0,
                "investment_diversity_score": len(investors) / max(1, largest_investor_percentage / 10)
            }
        }