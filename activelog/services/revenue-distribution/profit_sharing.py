"""
Profit Sharing Calculations
Calculate and distribute profit shares based on various models
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class ProfitShareModel(str, Enum):
    EQUAL = "equal"
    PROPORTIONAL = "proportional"
    PERFORMANCE = "performance"
    CUSTOM = "custom"

class ProfitShareCalculator:
    def __init__(self):
        self.distributions = {}
    
    async def calculate_distribution(self, profit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate profit sharing distribution"""
        
        distribution_id = f"DIST_{uuid.uuid4().hex[:8].upper()}"
        
        total_profit = Decimal(str(profit_data["total_profit"]))
        participants = profit_data["participants"]
        model = ProfitShareModel(profit_data.get("model", "equal"))
        
        distributions = []
        
        if model == ProfitShareModel.EQUAL:
            # Equal distribution
            share_per_participant = total_profit / len(participants)
            for participant in participants:
                distributions.append({
                    "participant_id": participant["id"],
                    "share_amount": float(share_per_participant),
                    "share_percentage": float(100 / len(participants))
                })
        
        elif model == ProfitShareModel.PROPORTIONAL:
            # Proportional to contribution
            total_contribution = sum(p.get("contribution", 1) for p in participants)
            for participant in participants:
                contribution = participant.get("contribution", 1)
                share_percentage = contribution / total_contribution * 100
                share_amount = total_profit * Decimal(str(contribution)) / Decimal(str(total_contribution))
                
                distributions.append({
                    "participant_id": participant["id"],
                    "share_amount": float(share_amount),
                    "share_percentage": float(share_percentage)
                })
        
        result = {
            "id": distribution_id,
            "total_profit": float(total_profit),
            "model": model.value,
            "participant_count": len(participants),
            "distributions": distributions,
            "calculated_at": datetime.now().isoformat()
        }
        
        self.distributions[distribution_id] = result
        
        logger.info(f"Calculated profit distribution {distribution_id}")
        return result
    
    async def get_distribution_history(self, entity_id: str, year: int) -> List[Dict[str, Any]]:
        """Get profit distribution history"""
        
        # Mock history data
        history = []
        for i in range(12):
            history.append({
                "month": i + 1,
                "profit_share": 1000.0 + (i * 50),
                "distribution_date": f"{year}-{i+1:02d}-01"
            })
        
        return {
            "entity_id": entity_id,
            "year": year,
            "monthly_distributions": history,
            "total_annual_share": sum(item["profit_share"] for item in history)
        }

# Global instance
profit_share_calculator = ProfitShareCalculator()