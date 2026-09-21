"""
Expense Categorization System
Automatically categorize business expenses for tax deductions
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal
import re
import logging
import sqlite3

logger = logging.getLogger(__name__)

class ExpenseCategorizer:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db"
        
        # Expense categories with keywords, deductibility rules, and limits
        self.expense_categories = {
            "office_supplies": {
                "keywords": ["paper", "pen", "office", "supplies", "stationery", "printer"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Office supplies and materials"
            },
            "equipment": {
                "keywords": ["computer", "laptop", "equipment", "machinery", "tools", "hardware"],
                "deductible": True,
                "percentage": 100,
                "depreciation_required": True,
                "schedule": "Schedule C / Form 4562",
                "description": "Business equipment and machinery"
            },
            "software": {
                "keywords": ["software", "subscription", "saas", "license", "app", "cloud"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Software and digital subscriptions"
            },
            "professional_services": {
                "keywords": ["legal", "accounting", "consulting", "professional", "attorney", "cpa"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Professional and legal services"
            },
            "marketing_advertising": {
                "keywords": ["marketing", "advertising", "promotion", "seo", "ads", "campaign"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Marketing and advertising expenses"
            },
            "travel": {
                "keywords": ["travel", "flight", "hotel", "airfare", "lodging", "transportation"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Business travel expenses"
            },
            "meals_entertainment": {
                "keywords": ["meal", "restaurant", "food", "entertainment", "client", "business meal"],
                "deductible": True,
                "percentage": 50,  # Only 50% deductible for meals
                "schedule": "Schedule C",
                "description": "Business meals and entertainment"
            },
            "vehicle": {
                "keywords": ["gas", "fuel", "vehicle", "car", "auto", "mileage", "parking"],
                "deductible": True,
                "percentage": 100,
                "business_use_required": True,
                "schedule": "Schedule C / Form 4562",
                "description": "Vehicle and transportation expenses"
            },
            "home_office": {
                "keywords": ["rent", "utilities", "internet", "phone", "home office", "workspace"],
                "deductible": True,
                "percentage": 100,
                "business_use_required": True,
                "schedule": "Schedule C / Form 8829",
                "description": "Home office expenses"
            },
            "insurance": {
                "keywords": ["insurance", "liability", "professional", "health", "business"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Business insurance premiums"
            },
            "training_education": {
                "keywords": ["training", "course", "education", "seminar", "workshop", "certification"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Professional development and training"
            },
            "bank_fees": {
                "keywords": ["bank", "fee", "transaction", "merchant", "processing", "paypal"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Bank and payment processing fees"
            },
            "rent_utilities": {
                "keywords": ["rent", "lease", "utilities", "electricity", "water", "internet"],
                "deductible": True,
                "percentage": 100,
                "business_use_required": True,
                "schedule": "Schedule C",
                "description": "Office rent and utilities"
            },
            "personal": {
                "keywords": ["personal", "family", "non-business", "private"],
                "deductible": False,
                "percentage": 0,
                "schedule": "Not deductible",
                "description": "Personal expenses (not deductible)"
            },
            "other_business": {
                "keywords": ["misc", "other", "business", "miscellaneous"],
                "deductible": True,
                "percentage": 100,
                "schedule": "Schedule C",
                "description": "Other business expenses"
            }
        }
    
    async def categorize_expense(self, transaction_id: str) -> Dict[str, Any]:
        """Categorize a specific expense transaction"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get transaction details
        cursor.execute('''
            SELECT description, amount, transaction_date, payee_info, receipt_url
            FROM tax_transactions
            WHERE id = ? AND transaction_type = 'expense'
        ''', (transaction_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError(f"Transaction {transaction_id} not found or not expense")
        
        description, amount, transaction_date, payee_info, receipt_url = result
        
        # Perform categorization
        category_info = self._classify_expense(description, amount, payee_info)
        
        # Calculate deductible amount
        deductible_amount = self._calculate_deductible_amount(amount, category_info)
        
        # Update transaction with categorization
        await self._update_expense_category(transaction_id, category_info, deductible_amount)
        
        return {
            "transaction_id": transaction_id,
            "amount": float(Decimal(str(amount))),
            "description": description,
            "category": category_info["category"],
            "subcategory": category_info["subcategory"],
            "confidence_score": category_info["confidence"],
            "deductible": category_info["deductible"],
            "deductible_percentage": category_info["percentage"],
            "deductible_amount": float(deductible_amount),
            "tax_schedule": category_info["schedule"],
            "requires_documentation": self._requires_documentation(category_info["category"], amount),
            "categorized_at": datetime.now().isoformat()
        }
    
    def _classify_expense(self, description: str, amount: float, 
                         payee_info: str = None) -> Dict[str, Any]:
        """Classify expense based on description and context"""
        
        text_to_analyze = f"{description} {payee_info or ''}".lower()
        
        scores = {}
        
        # Score each category based on keyword matches
        for category, config in self.expense_categories.items():
            score = 0
            matched_keywords = []
            
            for keyword in config["keywords"]:
                if keyword in text_to_analyze:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Boost score for vendor-specific patterns
            if category == "software" and any(vendor in text_to_analyze for vendor in 
                ["microsoft", "google", "adobe", "slack", "zoom", "dropbox"]):
                score += 2
            
            if category == "marketing_advertising" and any(platform in text_to_analyze for platform in
                ["facebook", "google ads", "linkedin", "twitter"]):
                score += 2
            
            if score > 0:
                scores[category] = {
                    "score": score,
                    "keywords": matched_keywords,
                    "config": config
                }
        
        # Determine best category
        if not scores:
            # Check amount-based categorization
            if amount > 5000:
                best_category = "equipment"  # Large amounts often equipment
                confidence = 0.4
            else:
                best_category = "other_business"
                confidence = 0.3
        else:
            # Get category with highest score
            best_category = max(scores.keys(), key=lambda x: scores[x]["score"])
            max_score = scores[best_category]["score"]
            total_keywords = len(self.expense_categories[best_category]["keywords"])
            confidence = min(0.95, max_score / total_keywords)
        
        # Determine subcategory
        subcategory = self._determine_expense_subcategory(best_category, amount, text_to_analyze)
        
        config = self.expense_categories[best_category]
        
        return {
            "category": best_category,
            "subcategory": subcategory,
            "confidence": confidence,
            "deductible": config["deductible"],
            "percentage": config["percentage"],
            "schedule": config["schedule"],
            "matched_keywords": scores.get(best_category, {}).get("keywords", []),
            "requires_business_use": config.get("business_use_required", False),
            "depreciation_required": config.get("depreciation_required", False)
        }
    
    def _determine_expense_subcategory(self, category: str, amount: float, text: str) -> str:
        """Determine subcategory based on category and context"""
        
        subcategories = {
            "equipment": {
                "computers": ["computer", "laptop", "desktop", "mac", "pc"],
                "furniture": ["desk", "chair", "furniture", "table"],
                "machinery": ["printer", "scanner", "machinery", "equipment"],
                "tools": ["tools", "software", "development"]
            },
            "software": {
                "productivity": ["office", "microsoft", "google", "productivity"],
                "development": ["github", "development", "coding", "programming"],
                "design": ["adobe", "photoshop", "design", "creative"],
                "business": ["crm", "accounting", "business", "enterprise"]
            },
            "travel": {
                "airfare": ["flight", "airline", "airfare", "plane"],
                "lodging": ["hotel", "lodging", "accommodation", "airbnb"],
                "ground": ["taxi", "uber", "rental", "car", "transport"],
                "meals": ["meal", "food", "restaurant"]
            },
            "marketing_advertising": {
                "online_ads": ["google", "facebook", "linkedin", "ads", "ppc"],
                "content": ["content", "writing", "blog", "social"],
                "events": ["conference", "event", "trade show", "booth"],
                "materials": ["brochure", "business card", "flyer", "print"]
            }
        }
        
        if category in subcategories:
            for subcategory, keywords in subcategories[category].items():
                if any(keyword in text for keyword in keywords):
                    return subcategory
        
        # Amount-based subcategorization for equipment
        if category == "equipment":
            if amount >= 2500:
                return "major_equipment"
            elif amount >= 500:
                return "moderate_equipment"
            else:
                return "minor_equipment"
        
        return "standard"
    
    def _calculate_deductible_amount(self, amount: float, category_info: Dict[str, Any]) -> Decimal:
        """Calculate the deductible portion of the expense"""
        
        amount_decimal = Decimal(str(amount))
        
        if not category_info["deductible"]:
            return Decimal('0')
        
        percentage = Decimal(str(category_info["percentage"])) / Decimal('100')
        return amount_decimal * percentage
    
    def _requires_documentation(self, category: str, amount: float) -> bool:
        """Determine if expense requires special documentation"""
        
        # High-value items always require documentation
        if amount >= 500:
            return True
        
        # Certain categories always require documentation
        documentation_required = [
            "travel", "meals_entertainment", "vehicle", 
            "home_office", "equipment"
        ]
        
        return category in documentation_required
    
    async def _update_expense_category(self, transaction_id: str, 
                                     category_info: Dict[str, Any],
                                     deductible_amount: Decimal) -> None:
        """Update transaction with categorization info"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tax_transactions
            SET 
                expense_category = ?,
                deductible = ?,
                deductible_amount = ?,
                tax_schedule = ?,
                categorization_confidence = ?,
                updated_at = ?
            WHERE id = ?
        ''', (
            f"{category_info['category']}/{category_info['subcategory']}",
            category_info['deductible'],
            float(deductible_amount),
            category_info['schedule'],
            category_info['confidence'],
            datetime.now().isoformat(),
            transaction_id
        ))
        
        conn.commit()
        conn.close()
    
    async def get_expense_summary(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Get expense summary by category"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                expense_category,
                tax_schedule,
                SUM(amount) as total_amount,
                SUM(deductible_amount) as total_deductible,
                COUNT(*) as transaction_count,
                AVG(categorization_confidence) as avg_confidence
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'expense'
            AND expense_category IS NOT NULL
            GROUP BY expense_category, tax_schedule
            ORDER BY total_deductible DESC
        ''', (entity_id, str(tax_year)))
        
        results = cursor.fetchall()
        conn.close()
        
        categories = {}
        total_expenses = Decimal('0')
        total_deductible = Decimal('0')
        
        for result in results:
            category, schedule, amount, deductible, count, confidence = result
            amount_decimal = Decimal(str(amount))
            deductible_decimal = Decimal(str(deductible or 0))
            
            categories[category] = {
                "total_amount": float(amount_decimal),
                "deductible_amount": float(deductible_decimal),
                "transaction_count": count,
                "tax_schedule": schedule,
                "confidence": confidence or 0.5,
                "deductible_percentage": float((deductible_decimal / amount_decimal * 100)) if amount_decimal > 0 else 0
            }
            
            total_expenses += amount_decimal
            total_deductible += deductible_decimal
        
        return {
            "entity_id": entity_id,
            "tax_year": tax_year,
            "total_expenses": float(total_expenses),
            "total_deductible": float(total_deductible),
            "deduction_rate": float((total_deductible / total_expenses * 100)) if total_expenses > 0 else 0,
            "categories": categories,
            "category_count": len(categories),
            "generated_at": datetime.now().isoformat()
        }
    
    async def bulk_categorize_expenses(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Bulk categorize all uncategorized expenses for entity/year"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get uncategorized expense transactions
        cursor.execute('''
            SELECT id
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'expense'
            AND (expense_category IS NULL OR expense_category = '')
        ''', (entity_id, str(tax_year)))
        
        transaction_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        categorized_count = 0
        total_deductible = Decimal('0')
        
        for transaction_id in transaction_ids:
            try:
                result = await self.categorize_expense(transaction_id)
                categorized_count += 1
                total_deductible += Decimal(str(result['deductible_amount']))
            except Exception as e:
                logger.error(f"Failed to categorize expense {transaction_id}: {e}")
        
        return {
            "entity_id": entity_id,
            "tax_year": tax_year,
            "total_transactions": len(transaction_ids),
            "categorized_count": categorized_count,
            "failed_count": len(transaction_ids) - categorized_count,
            "total_deductions_identified": float(total_deductible),
            "processed_at": datetime.now().isoformat()
        }

# Global instance
expense_categorizer = ExpenseCategorizer()