"""
1099 Form Generation System
Generate 1099-MISC and 1099-NEC forms for creator payments
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, date
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class Form1099Type(str, Enum):
    MISC = "1099_misc"
    NEC = "1099_nec"

class Form1099Data(BaseModel):
    id: str
    entity_id: str
    tax_year: int
    form_type: Form1099Type
    
    # Payer information (us)
    payer_name: str = "ActiveLog Platform"
    payer_address: str = "123 Business Ave, Tech City, TX 75001"
    payer_tin: str = "12-3456789"
    
    # Payee information (creator)
    payee_name: str
    payee_address: str
    payee_tin: str
    payee_account_number: Optional[str] = None
    
    # Payment details
    total_payments: Decimal = Decimal('0')
    federal_tax_withheld: Decimal = Decimal('0')
    
    # Box-specific amounts (1099-MISC)
    rents: Decimal = Decimal('0')                    # Box 1
    royalties: Decimal = Decimal('0')               # Box 2
    other_income: Decimal = Decimal('0')            # Box 3
    federal_income_tax: Decimal = Decimal('0')      # Box 4
    fishing_boat_proceeds: Decimal = Decimal('0')   # Box 5
    medical_payments: Decimal = Decimal('0')        # Box 6
    substitute_payments: Decimal = Decimal('0')     # Box 8
    direct_sales: Decimal = Decimal('0')           # Box 9
    crop_insurance: Decimal = Decimal('0')         # Box 10
    gross_proceeds_attorney: Decimal = Decimal('0') # Box 11
    section_409a_deferrals: Decimal = Decimal('0') # Box 12
    
    # 1099-NEC specific
    nonemployee_compensation: Decimal = Decimal('0') # Box 1 NEC
    
    # State information
    state_tax_withheld: Decimal = Decimal('0')
    state: str = "TX"
    state_income: Decimal = Decimal('0')
    
    # Metadata
    generated_at: datetime
    filing_required: bool = True  # True if >= $600

class Form1099Summary(BaseModel):
    entity_id: str
    tax_year: int
    
    # Summary totals
    total_1099_misc: Decimal = Decimal('0')
    total_1099_nec: Decimal = Decimal('0')
    total_recipients: int = 0
    
    # Breakdown by form type
    misc_recipients: int = 0
    nec_recipients: int = 0
    
    # Filing requirements
    forms_requiring_filing: int = 0  # >= $600
    
    generated_at: datetime

class Form1099Generator:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db"
        self.filing_threshold = Decimal('600.00')  # $600 filing threshold
        
        # Default payer information
        self.payer_info = {
            "name": "ActiveLog Platform Inc",
            "address": "123 Innovation Drive\nTech City, TX 75001",
            "tin": "12-3456789",
            "contact": "tax@activelog.com"
        }
    
    async def generate_1099(self, entity_id: str, tax_year: int, 
                           form_type: str = "1099_misc") -> Dict[str, Any]:
        """Generate 1099 form for entity"""
        
        # Get entity information
        entity = await self._get_entity_info(entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        # Get relevant transactions for the year
        transactions = await self._get_1099_transactions(entity_id, tax_year)
        
        # Calculate totals based on transaction categories
        if form_type == "1099_nec":
            form_data = await self._generate_1099_nec(entity, transactions, tax_year)
        else:
            form_data = await self._generate_1099_misc(entity, transactions, tax_year)
        
        # Store generated form
        await self._store_1099_form(form_data)
        
        return {
            "form_id": form_data.id,
            "entity_id": entity_id,
            "tax_year": tax_year,
            "form_type": form_data.form_type.value,
            "payee_name": form_data.payee_name,
            "total_payments": float(form_data.total_payments),
            "filing_required": form_data.filing_required,
            "form_data": form_data.model_dump(),
            "generated_at": form_data.generated_at.isoformat()
        }
    
    async def _generate_1099_misc(self, entity: Dict[str, Any], 
                                transactions: List[Dict[str, Any]], 
                                tax_year: int) -> Form1099Data:
        """Generate 1099-MISC form"""
        
        form_id = f"1099MISC_{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate amounts by category
        rents = Decimal('0')
        royalties = Decimal('0') 
        other_income = Decimal('0')
        
        total_payments = Decimal('0')
        
        for txn in transactions:
            amount = Decimal(str(txn["amount"]))
            total_payments += amount
            
            # Categorize based on revenue category
            if txn.get("revenue_category") == "royalties":
                royalties += amount
            elif txn.get("revenue_category") == "licensing":
                royalties += amount
            elif txn.get("revenue_category") in ["service_revenue", "consulting"]:
                other_income += amount
            else:
                other_income += amount
        
        form_data = Form1099Data(
            id=form_id,
            entity_id=entity["id"],
            tax_year=tax_year,
            form_type=Form1099Type.MISC,
            payee_name=entity["name"],
            payee_address=self._format_address(entity.get("address", {})),
            payee_tin=entity["tax_id"],
            total_payments=total_payments,
            rents=rents,
            royalties=royalties,
            other_income=other_income,
            filing_required=total_payments >= self.filing_threshold,
            generated_at=datetime.now()
        )
        
        return form_data
    
    async def _generate_1099_nec(self, entity: Dict[str, Any], 
                               transactions: List[Dict[str, Any]], 
                               tax_year: int) -> Form1099Data:
        """Generate 1099-NEC form for non-employee compensation"""
        
        form_id = f"1099NEC_{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate non-employee compensation
        nonemployee_compensation = Decimal('0')
        
        for txn in transactions:
            amount = Decimal(str(txn["amount"]))
            
            # NEC is for payments to non-employees for services
            if txn.get("revenue_category") in ["service_revenue", "consulting"]:
                nonemployee_compensation += amount
        
        form_data = Form1099Data(
            id=form_id,
            entity_id=entity["id"],
            tax_year=tax_year,
            form_type=Form1099Type.NEC,
            payee_name=entity["name"],
            payee_address=self._format_address(entity.get("address", {})),
            payee_tin=entity["tax_id"],
            total_payments=nonemployee_compensation,
            nonemployee_compensation=nonemployee_compensation,
            filing_required=nonemployee_compensation >= self.filing_threshold,
            generated_at=datetime.now()
        )
        
        return form_data
    
    async def get_1099_summary(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Get 1099 summary for entity and tax year"""
        
        # Get all 1099-eligible transactions
        transactions = await self._get_1099_transactions(entity_id, tax_year)
        
        # Calculate totals by category
        misc_total = Decimal('0')
        nec_total = Decimal('0')
        
        for txn in transactions:
            amount = Decimal(str(txn["amount"]))
            
            if txn.get("revenue_category") in ["service_revenue", "consulting"]:
                nec_total += amount
            else:
                misc_total += amount
        
        # Determine filing requirements
        misc_filing_required = misc_total >= self.filing_threshold
        nec_filing_required = nec_total >= self.filing_threshold
        
        summary = {
            "entity_id": entity_id,
            "tax_year": tax_year,
            "totals": {
                "1099_misc": float(misc_total),
                "1099_nec": float(nec_total),
                "combined": float(misc_total + nec_total)
            },
            "filing_requirements": {
                "1099_misc_required": misc_filing_required,
                "1099_nec_required": nec_filing_required,
                "any_filing_required": misc_filing_required or nec_filing_required
            },
            "transaction_count": len(transactions),
            "threshold": float(self.filing_threshold),
            "generated_at": datetime.now().isoformat()
        }
        
        return summary
    
    async def generate_batch_1099s(self, tax_year: int, 
                                 min_amount: Decimal = None) -> Dict[str, Any]:
        """Generate 1099s for all eligible entities"""
        
        if min_amount is None:
            min_amount = self.filing_threshold
        
        # Get all entities with payments >= threshold
        entities = await self._get_entities_for_1099_generation(tax_year, min_amount)
        
        generated_forms = []
        total_forms = 0
        total_amount = Decimal('0')
        
        for entity in entities:
            try:
                # Determine appropriate form type
                transactions = await self._get_1099_transactions(entity["id"], tax_year)
                
                # Generate both MISC and NEC if needed
                misc_amount = self._calculate_misc_amount(transactions)
                nec_amount = self._calculate_nec_amount(transactions)
                
                if misc_amount >= self.filing_threshold:
                    misc_form = await self.generate_1099(entity["id"], tax_year, "1099_misc")
                    generated_forms.append(misc_form)
                    total_forms += 1
                    total_amount += misc_amount
                
                if nec_amount >= self.filing_threshold:
                    nec_form = await self.generate_1099(entity["id"], tax_year, "1099_nec")
                    generated_forms.append(nec_form)
                    total_forms += 1
                    total_amount += nec_amount
                
            except Exception as e:
                logger.error(f"Failed to generate 1099 for entity {entity['id']}: {e}")
        
        return {
            "tax_year": tax_year,
            "forms_generated": total_forms,
            "entities_processed": len(entities),
            "total_amount_reported": float(total_amount),
            "forms": generated_forms,
            "generated_at": datetime.now().isoformat()
        }
    
    def _calculate_misc_amount(self, transactions: List[Dict[str, Any]]) -> Decimal:
        """Calculate 1099-MISC reportable amount"""
        
        total = Decimal('0')
        for txn in transactions:
            if txn.get("revenue_category") in ["royalties", "licensing", "product_sales"]:
                total += Decimal(str(txn["amount"]))
        
        return total
    
    def _calculate_nec_amount(self, transactions: List[Dict[str, Any]]) -> Decimal:
        """Calculate 1099-NEC reportable amount"""
        
        total = Decimal('0')
        for txn in transactions:
            if txn.get("revenue_category") in ["service_revenue", "consulting"]:
                total += Decimal(str(txn["amount"]))
        
        return total
    
    async def _get_entity_info(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity information from database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM tax_entities
            WHERE id = ?
        ''', (entity_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    async def _get_1099_transactions(self, entity_id: str, tax_year: int) -> List[Dict[str, Any]]:
        """Get transactions eligible for 1099 reporting"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'revenue'
            AND taxable = TRUE
            ORDER BY transaction_date
        ''', (entity_id, str(tax_year)))
        
        results = cursor.fetchall()
        conn.close()
        
        transactions = []
        for result in results:
            transaction_data = json.loads(result[0])
            transactions.append(transaction_data)
        
        return transactions
    
    async def _get_entities_for_1099_generation(self, tax_year: int, 
                                              min_amount: Decimal) -> List[Dict[str, Any]]:
        """Get entities that need 1099s generated"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT te.data
            FROM tax_entities te
            JOIN (
                SELECT entity_id, SUM(amount) as total_amount
                FROM tax_transactions
                WHERE strftime('%Y', transaction_date) = ?
                AND transaction_type = 'revenue'
                AND taxable = TRUE
                GROUP BY entity_id
                HAVING total_amount >= ?
            ) tt ON te.id = tt.entity_id
        ''', (str(tax_year), float(min_amount)))
        
        results = cursor.fetchall()
        conn.close()
        
        entities = []
        for result in results:
            entity_data = json.loads(result[0])
            entities.append(entity_data)
        
        return entities
    
    def _format_address(self, address: Dict[str, str]) -> str:
        """Format address for 1099 form"""
        
        if not address:
            return "Address not provided"
        
        lines = []
        if address.get("street"):
            lines.append(address["street"])
        if address.get("city") and address.get("state") and address.get("zip"):
            lines.append(f"{address['city']}, {address['state']} {address['zip']}")
        
        return "\n".join(lines) if lines else "Address not provided"
    
    async def _store_1099_form(self, form_data: Form1099Data):
        """Store generated 1099 form in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tax_forms 
            (id, entity_id, form_type, tax_year, form_data, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            form_data.id,
            form_data.entity_id,
            form_data.form_type.value,
            form_data.tax_year,
            form_data.model_dump_json(),
            form_data.generated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def get_generated_1099s(self, tax_year: int, 
                                form_type: str = None) -> List[Dict[str, Any]]:
        """Get all generated 1099 forms for a tax year"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT form_data FROM tax_forms
            WHERE tax_year = ?
            AND form_type LIKE '1099%'
        '''
        params = [tax_year]
        
        if form_type:
            query += " AND form_type = ?"
            params.append(form_type)
        
        query += " ORDER BY generated_at DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        forms = []
        for result in results:
            form_data = json.loads(result[0])
            forms.append(form_data)
        
        return forms

# Global instance
form_1099_generator = Form1099Generator()