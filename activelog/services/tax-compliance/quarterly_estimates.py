"""
Quarterly Tax Estimate Calculator
Calculate quarterly estimated tax payments
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal
import logging
import sqlite3

logger = logging.getLogger(__name__)

class QuarterlyEstimateCalculator:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db"
        
        # Tax rates (simplified - would normally be more complex)
        self.federal_rates = {
            "single": [
                (Decimal('0'), Decimal('10275'), Decimal('0.10')),
                (Decimal('10275'), Decimal('41775'), Decimal('0.12')),
                (Decimal('41775'), Decimal('89450'), Decimal('0.22')),
                (Decimal('89450'), Decimal('190750'), Decimal('0.24')),
                (Decimal('190750'), None, Decimal('0.32'))
            ]
        }
        
        self.self_employment_rate = Decimal('0.153')  # 15.3% SE tax
        self.safe_harbor_rate = Decimal('0.9')  # 90% safe harbor
    
    async def calculate_quarterly_estimate(self, entity_id: str, current_quarter: int, 
                                         current_year: int) -> Dict[str, Any]:
        """Calculate quarterly estimated tax payment"""
        
        # Get year-to-date income and expenses
        ytd_data = await self._get_ytd_financials(entity_id, current_year, current_quarter)
        
        # Project annual income
        projected_annual = self._project_annual_income(ytd_data, current_quarter)
        
        # Calculate estimated tax liability
        estimated_tax = self._calculate_annual_tax_liability(projected_annual)
        
        # Calculate quarterly payment
        quarterly_payment = estimated_tax / Decimal('4')
        
        # Apply safe harbor rules
        safe_harbor_payment = await self._calculate_safe_harbor(entity_id, current_year - 1)
        
        recommended_payment = max(quarterly_payment, safe_harbor_payment / Decimal('4'))
        
        return {
            "entity_id": entity_id,
            "quarter": current_quarter,
            "year": current_year,
            "projected_annual_income": float(projected_annual["gross_income"]),
            "projected_annual_expenses": float(projected_annual["total_expenses"]),
            "projected_net_income": float(projected_annual["net_income"]),
            "estimated_annual_tax": float(estimated_tax),
            "quarterly_payment": float(quarterly_payment),
            "safe_harbor_payment": float(safe_harbor_payment / Decimal('4')),
            "recommended_payment": float(recommended_payment),
            "due_date": self._get_quarter_due_date(current_quarter, current_year),
            "calculated_at": datetime.now().isoformat()
        }
    
    async def _get_ytd_financials(self, entity_id: str, year: int, quarter: int) -> Dict[str, Decimal]:
        """Get year-to-date financial data"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get income
        cursor.execute('''
            SELECT SUM(amount)
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'income'
            AND strftime('%m', transaction_date) <= ?
        ''', (entity_id, str(year), str(quarter * 3)))
        
        income_result = cursor.fetchone()
        gross_income = Decimal(str(income_result[0])) if income_result[0] else Decimal('0')
        
        # Get expenses
        cursor.execute('''
            SELECT SUM(amount)
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'expense'
            AND deductible = TRUE
            AND strftime('%m', transaction_date) <= ?
        ''', (entity_id, str(year), str(quarter * 3)))
        
        expense_result = cursor.fetchone()
        total_expenses = Decimal(str(expense_result[0])) if expense_result[0] else Decimal('0')
        
        conn.close()
        
        return {
            "gross_income": gross_income,
            "total_expenses": total_expenses,
            "net_income": gross_income - total_expenses
        }
    
    def _project_annual_income(self, ytd_data: Dict[str, Decimal], current_quarter: int) -> Dict[str, Decimal]:
        """Project annual income based on YTD data"""
        
        quarters_completed = current_quarter
        projection_multiplier = Decimal('4') / Decimal(str(quarters_completed))
        
        return {
            "gross_income": ytd_data["gross_income"] * projection_multiplier,
            "total_expenses": ytd_data["total_expenses"] * projection_multiplier,
            "net_income": ytd_data["net_income"] * projection_multiplier
        }
    
    def _calculate_annual_tax_liability(self, projected_income: Dict[str, Decimal]) -> Decimal:
        """Calculate estimated annual tax liability"""
        
        net_income = projected_income["net_income"]
        
        if net_income <= 0:
            return Decimal('0')
        
        # Federal income tax (simplified calculation)
        federal_tax = self._calculate_federal_tax(net_income)
        
        # Self-employment tax
        se_tax = net_income * self.self_employment_rate
        
        total_tax = federal_tax + se_tax
        
        return total_tax
    
    def _calculate_federal_tax(self, income: Decimal) -> Decimal:
        """Calculate federal income tax using tax brackets"""
        
        tax_owed = Decimal('0')
        remaining_income = income
        
        for bracket in self.federal_rates["single"]:
            bracket_start, bracket_end, rate = bracket
            
            if remaining_income <= 0:
                break
            
            if bracket_end is None:
                # Top bracket
                taxable_in_bracket = remaining_income
            else:
                # Regular bracket
                bracket_size = bracket_end - bracket_start
                taxable_in_bracket = min(remaining_income, bracket_size)
            
            tax_owed += taxable_in_bracket * rate
            remaining_income -= taxable_in_bracket
        
        return tax_owed
    
    async def _calculate_safe_harbor(self, entity_id: str, prior_year: int) -> Decimal:
        """Calculate safe harbor amount based on prior year"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get prior year tax liability (simplified)
        cursor.execute('''
            SELECT SUM(amount)
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'tax_payment'
        ''', (entity_id, str(prior_year)))
        
        result = cursor.fetchone()
        conn.close()
        
        prior_year_tax = Decimal(str(result[0])) if result and result[0] else Decimal('0')
        
        return prior_year_tax * self.safe_harbor_rate
    
    def _get_quarter_due_date(self, quarter: int, year: int) -> str:
        """Get due date for quarterly payment"""
        
        due_dates = {
            1: f"{year}-04-15",  # Q1 due April 15
            2: f"{year}-06-15",  # Q2 due June 15
            3: f"{year}-09-15",  # Q3 due September 15
            4: f"{year + 1}-01-15"  # Q4 due January 15 of next year
        }
        
        return due_dates.get(quarter, f"{year}-12-31")

# Global instance
quarterly_estimate_calculator = QuarterlyEstimateCalculator()