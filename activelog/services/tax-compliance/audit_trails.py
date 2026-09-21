"""
Tax Audit Trail Generation System
Generate comprehensive audit trails for tax compliance
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal
import uuid
import json
import logging
import sqlite3
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AuditEvent:
    event_id: str
    entity_id: str
    event_type: str
    description: str
    transaction_id: Optional[str]
    old_value: Optional[Any]
    new_value: Optional[Any]
    user_id: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]

class AuditTrailGenerator:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db"
    
    async def generate_audit_trail(self, entity_id: str, tax_year: int, 
                                 trail_type: str = "comprehensive") -> Dict[str, Any]:
        """Generate audit trail for tax year"""
        
        trail_id = f"AUDIT_{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all transactions for the year
        cursor.execute('''
            SELECT *
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            ORDER BY transaction_date, created_at
        ''', (entity_id, str(tax_year)))
        
        transactions = cursor.fetchall()
        
        # Get column names for proper mapping
        cursor.execute("PRAGMA table_info(tax_transactions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        conn.close()
        
        # Process transactions into audit trail
        audit_entries = []
        running_totals = {
            "income": Decimal('0'),
            "expenses": Decimal('0'),
            "tax_payments": Decimal('0')
        }
        
        for transaction in transactions:
            transaction_dict = dict(zip(columns, transaction))
            
            # Create audit entry
            entry = self._create_audit_entry(transaction_dict, running_totals)
            audit_entries.append(entry)
            
            # Update running totals
            amount = Decimal(str(transaction_dict.get('amount', 0)))
            transaction_type = transaction_dict.get('transaction_type', '')
            
            if transaction_type == 'income':
                running_totals['income'] += amount
            elif transaction_type == 'expense':
                running_totals['expenses'] += amount
            elif transaction_type == 'tax_payment':
                running_totals['tax_payments'] += amount
        
        # Generate summary
        summary = {
            "total_income": float(running_totals['income']),
            "total_expenses": float(running_totals['expenses']),
            "net_income": float(running_totals['income'] - running_totals['expenses']),
            "total_tax_payments": float(running_totals['tax_payments']),
            "transaction_count": len(transactions),
            "audit_entry_count": len(audit_entries)
        }
        
        return {
            "audit_trail_id": trail_id,
            "entity_id": entity_id,
            "tax_year": tax_year,
            "trail_type": trail_type,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "audit_entries": audit_entries[:100],  # Limit for API response
            "total_entries": len(audit_entries),
            "compliance_status": self._assess_compliance(summary, audit_entries)
        }
    
    def _create_audit_entry(self, transaction: Dict[str, Any], 
                          running_totals: Dict[str, Decimal]) -> Dict[str, Any]:
        """Create individual audit entry from transaction"""
        
        return {
            "entry_id": f"ENTRY_{uuid.uuid4().hex[:6].upper()}",
            "transaction_id": transaction.get('id'),
            "date": transaction.get('transaction_date'),
            "type": transaction.get('transaction_type'),
            "description": transaction.get('description', ''),
            "amount": transaction.get('amount'),
            "category": transaction.get('expense_category') or transaction.get('income_category'),
            "deductible": transaction.get('deductible'),
            "supporting_documents": transaction.get('receipt_url', '').split(',') if transaction.get('receipt_url') else [],
            "running_income": float(running_totals['income']),
            "running_expenses": float(running_totals['expenses']),
            "running_net": float(running_totals['income'] - running_totals['expenses']),
            "created_at": transaction.get('created_at'),
            "metadata": {
                "ccc_amount": transaction.get('ccc_amount'),
                "tax_rate": transaction.get('tax_rate'),
                "withholding_amount": transaction.get('withholding_amount')
            }
        }
    
    def _assess_compliance(self, summary: Dict[str, Any], 
                          audit_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess compliance status based on audit trail"""
        
        issues = []
        warnings = []
        
        # Check for missing documentation
        missing_docs = 0
        high_value_no_docs = 0
        
        for entry in audit_entries:
            if not entry.get('supporting_documents'):
                missing_docs += 1
                if entry.get('amount', 0) > 500:  # High value transactions
                    high_value_no_docs += 1
        
        if missing_docs > 0:
            warnings.append(f"{missing_docs} transactions missing supporting documentation")
        
        if high_value_no_docs > 0:
            issues.append(f"{high_value_no_docs} high-value transactions (>$500) without documentation")
        
        # Check for unusual patterns
        if summary['net_income'] < 0:
            warnings.append("Negative net income for tax year")
        
        # Determine overall status
        if len(issues) == 0:
            status = "compliant" if len(warnings) == 0 else "compliant_with_warnings"
        else:
            status = "non_compliant"
        
        return {
            "status": status,
            "score": max(0, 100 - (len(issues) * 20) - (len(warnings) * 5)),
            "issues": issues,
            "warnings": warnings,
            "recommendations": self._generate_recommendations(issues, warnings)
        }
    
    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """Generate compliance recommendations"""
        
        recommendations = []
        
        if any("documentation" in issue.lower() for issue in issues):
            recommendations.append("Implement document retention policy for all transactions over $500")
        
        if any("documentation" in warning.lower() for warning in warnings):
            recommendations.append("Digitize and organize supporting documents for all business transactions")
        
        if any("negative net income" in warning.lower() for warning in warnings):
            recommendations.append("Review expense categorization and ensure proper business purpose documentation")
        
        if not recommendations:
            recommendations.append("Maintain current documentation and record-keeping practices")
        
        return recommendations
    
    async def export_audit_trail(self, audit_trail_id: str, format_type: str = "json") -> Dict[str, Any]:
        """Export audit trail in specified format"""
        
        # In a real implementation, this would retrieve the stored audit trail
        # and format it for export (JSON, CSV, PDF, etc.)
        
        return {
            "audit_trail_id": audit_trail_id,
            "export_format": format_type,
            "export_url": f"/exports/audit_trail_{audit_trail_id}.{format_type}",
            "exported_at": datetime.now().isoformat(),
            "expires_at": datetime.now().replace(hour=23, minute=59, second=59).isoformat()
        }
    
    async def log_audit_event(self, event: AuditEvent) -> Dict[str, Any]:
        """Log audit event for future trail generation"""
        
        # In a real implementation, this would store the event in a database
        logger.info(f"Audit event logged: {event.event_type} for entity {event.entity_id}")
        
        return {
            "event_id": event.event_id,
            "logged_at": datetime.now().isoformat(),
            "status": "logged"
        }

# Global instance
audit_trail_generator = AuditTrailGenerator()