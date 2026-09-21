"""
Revenue Categorization System
Automatically categorize revenue streams for tax reporting
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal
import re
import logging
import sqlite3

logger = logging.getLogger(__name__)

class RevenueCategorizer:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db"
        
        # Revenue categories with keywords and rules
        self.revenue_categories = {
            "service_revenue": {
                "keywords": ["consulting", "service", "hourly", "retainer", "professional"],
                "tax_treatment": "ordinary_income",
                "1099_required": True,
                "description": "Professional services and consulting"
            },
            "product_sales": {
                "keywords": ["sale", "product", "goods", "merchandise", "inventory"],
                "tax_treatment": "ordinary_income", 
                "1099_required": False,
                "description": "Product and goods sales"
            },
            "royalties": {
                "keywords": ["royalty", "license", "patent", "copyright", "intellectual"],
                "tax_treatment": "royalty_income",
                "1099_required": True,
                "description": "Royalties and licensing fees"
            },
            "rental_income": {
                "keywords": ["rent", "rental", "lease", "property", "real estate"],
                "tax_treatment": "rental_income",
                "1099_required": False,
                "description": "Rental and lease income"
            },
            "investment_income": {
                "keywords": ["dividend", "interest", "investment", "capital gain", "securities"],
                "tax_treatment": "investment_income",
                "1099_required": True,
                "description": "Investment income and capital gains"
            },
            "digital_revenue": {
                "keywords": ["software", "app", "digital", "subscription", "saas", "platform"],
                "tax_treatment": "ordinary_income",
                "1099_required": True,
                "description": "Digital products and services"
            },
            "affiliate_commissions": {
                "keywords": ["affiliate", "commission", "referral", "partner", "marketing"],
                "tax_treatment": "ordinary_income",
                "1099_required": True,
                "description": "Affiliate and referral commissions"
            },
            "cryptocurrency": {
                "keywords": ["crypto", "bitcoin", "ethereum", "blockchain", "mining", "ccc"],
                "tax_treatment": "capital_gain",
                "1099_required": False,
                "description": "Cryptocurrency transactions"
            },
            "grants_awards": {
                "keywords": ["grant", "award", "prize", "scholarship", "fellowship"],
                "tax_treatment": "other_income",
                "1099_required": True,
                "description": "Grants and awards"
            },
            "other_income": {
                "keywords": ["misc", "other", "miscellaneous", "various"],
                "tax_treatment": "other_income",
                "1099_required": False,
                "description": "Other miscellaneous income"
            }
        }
    
    async def categorize_revenue(self, transaction_id: str) -> Dict[str, Any]:
        """Categorize a specific revenue transaction"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get transaction details
        cursor.execute('''
            SELECT description, amount, transaction_date, payer_info
            FROM tax_transactions
            WHERE id = ? AND transaction_type = 'income'
        ''', (transaction_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError(f"Transaction {transaction_id} not found or not income")
        
        description, amount, transaction_date, payer_info = result
        
        # Perform categorization
        category_info = self._classify_revenue(description, amount, payer_info)
        
        # Update transaction with categorization
        await self._update_transaction_category(transaction_id, category_info)
        
        return {
            "transaction_id": transaction_id,
            "amount": float(Decimal(str(amount))),
            "description": description,
            "category": category_info["category"],
            "subcategory": category_info["subcategory"],
            "confidence_score": category_info["confidence"],
            "tax_treatment": category_info["tax_treatment"],
            "requires_1099": category_info["requires_1099"],
            "categorized_at": datetime.now().isoformat()
        }
    
    def _classify_revenue(self, description: str, amount: float, 
                         payer_info: str = None) -> Dict[str, Any]:
        """Classify revenue based on description and context"""
        
        text_to_analyze = f"{description} {payer_info or ''}".lower()
        
        scores = {}
        
        # Score each category based on keyword matches
        for category, config in self.revenue_categories.items():
            score = 0
            matched_keywords = []
            
            for keyword in config["keywords"]:
                if keyword in text_to_analyze:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                scores[category] = {
                    "score": score,
                    "keywords": matched_keywords,
                    "config": config
                }
        
        # Determine best category
        if not scores:
            # Default to other_income if no matches
            best_category = "other_income"
            confidence = 0.3
        else:
            # Get category with highest score
            best_category = max(scores.keys(), key=lambda x: scores[x]["score"])
            max_score = scores[best_category]["score"]
            confidence = min(0.9, max_score / len(self.revenue_categories[best_category]["keywords"]))
        
        # Determine subcategory based on amount and other factors
        subcategory = self._determine_subcategory(best_category, amount, text_to_analyze)
        
        config = self.revenue_categories[best_category]
        
        return {
            "category": best_category,
            "subcategory": subcategory,
            "confidence": confidence,
            "tax_treatment": config["tax_treatment"],
            "requires_1099": config["1099_required"],
            "matched_keywords": scores.get(best_category, {}).get("keywords", [])
        }
    
    def _determine_subcategory(self, category: str, amount: float, text: str) -> str:
        """Determine subcategory based on category and context"""
        
        subcategories = {
            "service_revenue": {
                "consulting": ["consult", "advisory", "strategy"],
                "development": ["develop", "coding", "programming", "software"],
                "design": ["design", "creative", "graphics", "ui", "ux"],
                "marketing": ["marketing", "advertising", "promotion", "seo"],
                "training": ["training", "education", "workshop", "seminar"]
            },
            "digital_revenue": {
                "software_sales": ["software", "app", "application"],
                "subscriptions": ["subscription", "monthly", "annual", "recurring"],
                "digital_products": ["ebook", "course", "template", "digital"],
                "platform_fees": ["platform", "marketplace", "commission"]
            },
            "investment_income": {
                "dividends": ["dividend"],
                "interest": ["interest"],
                "capital_gains": ["capital", "gain", "sale", "stock"],
                "crypto_gains": ["crypto", "bitcoin", "ethereum", "ccc"]
            }
        }
        
        if category in subcategories:
            for subcategory, keywords in subcategories[category].items():
                if any(keyword in text for keyword in keywords):
                    return subcategory
        
        # Amount-based subcategorization
        if amount >= 10000:
            return "large_transaction"
        elif amount >= 1000:
            return "medium_transaction"
        else:
            return "small_transaction"
    
    async def _update_transaction_category(self, transaction_id: str, 
                                         category_info: Dict[str, Any]) -> None:
        """Update transaction with categorization info"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tax_transactions
            SET 
                income_category = ?,
                tax_treatment = ?,
                categorization_confidence = ?,
                updated_at = ?
            WHERE id = ?
        ''', (
            f"{category_info['category']}/{category_info['subcategory']}",
            category_info['tax_treatment'],
            category_info['confidence'],
            datetime.now().isoformat(),
            transaction_id
        ))
        
        conn.commit()
        conn.close()
    
    async def get_revenue_summary(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Get revenue summary by category"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                income_category,
                tax_treatment,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count,
                AVG(categorization_confidence) as avg_confidence
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'income'
            AND income_category IS NOT NULL
            GROUP BY income_category, tax_treatment
            ORDER BY total_amount DESC
        ''', (entity_id, str(tax_year)))
        
        results = cursor.fetchall()
        conn.close()
        
        categories = {}
        total_revenue = Decimal('0')
        
        for result in results:
            category, tax_treatment, amount, count, confidence = result
            amount_decimal = Decimal(str(amount))
            
            categories[category] = {
                "amount": float(amount_decimal),
                "transaction_count": count,
                "tax_treatment": tax_treatment,
                "confidence": confidence or 0.5,
                "percentage": 0  # Will be calculated after total
            }
            
            total_revenue += amount_decimal
        
        # Calculate percentages
        for category_data in categories.values():
            if total_revenue > 0:
                category_data["percentage"] = (category_data["amount"] / float(total_revenue)) * 100
        
        return {
            "entity_id": entity_id,
            "tax_year": tax_year,
            "total_revenue": float(total_revenue),
            "categories": categories,
            "category_count": len(categories),
            "generated_at": datetime.now().isoformat()
        }
    
    async def bulk_categorize(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Bulk categorize all uncategorized revenue for entity/year"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get uncategorized income transactions
        cursor.execute('''
            SELECT id
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'income'
            AND (income_category IS NULL OR income_category = '')
        ''', (entity_id, str(tax_year)))
        
        transaction_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        categorized_count = 0
        for transaction_id in transaction_ids:
            try:
                await self.categorize_revenue(transaction_id)
                categorized_count += 1
            except Exception as e:
                logger.error(f"Failed to categorize transaction {transaction_id}: {e}")
        
        return {
            "entity_id": entity_id,
            "tax_year": tax_year,
            "total_transactions": len(transaction_ids),
            "categorized_count": categorized_count,
            "failed_count": len(transaction_ids) - categorized_count,
            "processed_at": datetime.now().isoformat()
        }

# Global instance
revenue_categorizer = RevenueCategorizer()