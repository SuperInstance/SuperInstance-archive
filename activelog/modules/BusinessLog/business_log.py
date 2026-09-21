"""
BusinessLog Module - Advanced business expense and payroll management.
Features: Receipt OCR, automatic tax categorization, payroll automation, compliance tracking.
"""

import asyncio
import json
import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re
import pytesseract
from PIL import Image

@dataclass
class Receipt:
    """Receipt data structure."""
    id: str
    merchant: str
    date: datetime
    total_amount: float
    currency: str
    items: List[Dict[str, Any]]
    tax_amount: Optional[float] = None
    category: Optional[str] = None
    confidence: float = 1.0
    image_path: Optional[str] = None
    raw_ocr_text: Optional[str] = None

@dataclass
class Employee:
    """Employee data structure."""
    id: str
    name: str
    position: str
    department: str
    salary: float
    hourly_rate: Optional[float] = None
    hire_date: datetime = None
    tax_info: Dict[str, Any] = None
    benefits: Dict[str, Any] = None

@dataclass
class PayrollRecord:
    """Payroll record for an employee."""
    id: str
    employee_id: str
    pay_period_start: datetime
    pay_period_end: datetime
    gross_pay: float
    deductions: Dict[str, float]
    net_pay: float
    hours_worked: Optional[float] = None
    overtime_hours: Optional[float] = None

@dataclass
class TaxCategory:
    """Tax category information."""
    category: str
    code: str
    deductible_percentage: float
    description: str
    requires_documentation: bool

class ReceiptOCR:
    """Optical Character Recognition system for receipts."""
    
    def __init__(self):
        self.text_patterns = self._load_text_patterns()
        self.merchant_database = self._load_merchant_database()
        
    def _load_text_patterns(self) -> Dict[str, Any]:
        """Load regex patterns for extracting receipt information."""
        return {
            'total_patterns': [
                r'total[:\s]*\$?(\d+\.?\d*)',
                r'amount[:\s]*\$?(\d+\.?\d*)',
                r'grand total[:\s]*\$?(\d+\.?\d*)',
                r'\$(\d+\.\d{2})\s*$'
            ],
            'date_patterns': [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',
                r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}'
            ],
            'merchant_patterns': [
                r'^([A-Z\s]+)\n',
                r'([A-Z][A-Z\s]{5,})\n',
                r'store[:\s]*([A-Za-z\s]+)',
                r'merchant[:\s]*([A-Za-z\s]+)'
            ],
            'tax_patterns': [
                r'tax[:\s]*\$?(\d+\.?\d*)',
                r'hst[:\s]*\$?(\d+\.?\d*)',
                r'gst[:\s]*\$?(\d+\.?\d*)',
                r'pst[:\s]*\$?(\d+\.?\d*)'
            ],
            'item_patterns': [
                r'(\d+)\s+([A-Za-z\s]+)\s+\$?(\d+\.\d{2})',
                r'([A-Za-z\s]+)\s+\$?(\d+\.\d{2})\s*$'
            ]
        }
    
    def _load_merchant_database(self) -> Dict[str, Dict[str, str]]:
        """Load merchant database for categorization."""
        return {
            "WALMART": {"category": "office_supplies", "type": "retail"},
            "AMAZON": {"category": "office_supplies", "type": "online"},
            "STARBUCKS": {"category": "meals_entertainment", "type": "restaurant"},
            "SHELL": {"category": "vehicle_expenses", "type": "fuel"},
            "FEDEX": {"category": "shipping", "type": "logistics"},
            "STAPLES": {"category": "office_supplies", "type": "retail"},
            "HOME DEPOT": {"category": "equipment", "type": "retail"},
            "UBER": {"category": "travel", "type": "transportation"},
            "MARRIOTT": {"category": "travel", "type": "accommodation"}
        }
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from receipt image using OCR."""
        try:
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                return ""
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply image preprocessing
            processed = self._preprocess_receipt_image(gray)
            
            # Extract text using pytesseract
            text = pytesseract.image_to_string(processed, config='--psm 6')
            
            return text.strip()
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def _preprocess_receipt_image(self, gray_image: np.ndarray) -> np.ndarray:
        """Preprocess receipt image for better OCR accuracy."""
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray_image, (3, 3), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up the image
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def parse_receipt_text(self, text: str) -> Receipt:
        """Parse extracted text to create Receipt object."""
        lines = text.split('\n')
        
        # Extract merchant
        merchant = self._extract_merchant(lines)
        
        # Extract date
        date = self._extract_date(text)
        
        # Extract total amount
        total_amount = self._extract_total(text)
        
        # Extract tax amount
        tax_amount = self._extract_tax(text)
        
        # Extract items
        items = self._extract_items(lines)
        
        # Determine category
        category = self._categorize_receipt(merchant, items)
        
        receipt_id = f"RCP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return Receipt(
            id=receipt_id,
            merchant=merchant,
            date=date,
            total_amount=total_amount,
            currency="USD",
            items=items,
            tax_amount=tax_amount,
            category=category,
            confidence=0.85,  # Mock confidence
            raw_ocr_text=text
        )
    
    def _extract_merchant(self, lines: List[str]) -> str:
        """Extract merchant name from receipt lines."""
        for pattern in self.text_patterns['merchant_patterns']:
            for line in lines[:5]:  # Check first few lines
                match = re.search(pattern, line.upper())
                if match:
                    return match.group(1).strip()
        
        # Fallback: use first non-empty line
        for line in lines:
            if line.strip() and len(line.strip()) > 3:
                return line.strip()
        
        return "Unknown Merchant"
    
    def _extract_date(self, text: str) -> datetime:
        """Extract date from receipt text."""
        for pattern in self.text_patterns['date_patterns']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try different date formats
                    for fmt in ['%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except:
                            continue
                except:
                    continue
        
        return datetime.now()  # Fallback to current date
    
    def _extract_total(self, text: str) -> float:
        """Extract total amount from receipt text."""
        amounts = []
        for pattern in self.text_patterns['total_patterns']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match.replace('$', '').replace(',', ''))
                    amounts.append(amount)
                except:
                    continue
        
        # Return the largest amount found (likely the total)
        return max(amounts) if amounts else 0.0
    
    def _extract_tax(self, text: str) -> Optional[float]:
        """Extract tax amount from receipt text."""
        for pattern in self.text_patterns['tax_patterns']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace('$', '').replace(',', ''))
                except:
                    continue
        return None
    
    def _extract_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract line items from receipt."""
        items = []
        
        for line in lines:
            for pattern in self.text_patterns['item_patterns']:
                match = re.search(pattern, line)
                if match:
                    if len(match.groups()) == 3:
                        # Quantity, description, price pattern
                        items.append({
                            'quantity': int(match.group(1)),
                            'description': match.group(2).strip(),
                            'price': float(match.group(3))
                        })
                    elif len(match.groups()) == 2:
                        # Description, price pattern
                        items.append({
                            'quantity': 1,
                            'description': match.group(1).strip(),
                            'price': float(match.group(2))
                        })
        
        return items
    
    def _categorize_receipt(self, merchant: str, items: List[Dict[str, Any]]) -> str:
        """Automatically categorize receipt based on merchant and items."""
        merchant_upper = merchant.upper()
        
        # Check merchant database
        for known_merchant, info in self.merchant_database.items():
            if known_merchant in merchant_upper:
                return info['category']
        
        # Categorize by items/keywords
        item_text = ' '.join([item.get('description', '') for item in items]).upper()
        
        if any(keyword in item_text for keyword in ['FOOD', 'MEAL', 'COFFEE', 'LUNCH', 'DINNER']):
            return 'meals_entertainment'
        elif any(keyword in item_text for keyword in ['GAS', 'FUEL', 'PETROL']):
            return 'vehicle_expenses'
        elif any(keyword in item_text for keyword in ['OFFICE', 'SUPPLIES', 'PAPER', 'PEN']):
            return 'office_supplies'
        elif any(keyword in item_text for keyword in ['HOTEL', 'FLIGHT', 'TRAVEL']):
            return 'travel'
        else:
            return 'general_expense'

class TaxCategorizer:
    """Automatic tax categorization system."""
    
    def __init__(self):
        self.tax_categories = self._load_tax_categories()
        self.categorization_rules = self._load_categorization_rules()
    
    def _load_tax_categories(self) -> Dict[str, TaxCategory]:
        """Load tax category definitions."""
        return {
            'office_supplies': TaxCategory(
                category='office_supplies',
                code='OFFICE',
                deductible_percentage=100.0,
                description='Office supplies and equipment',
                requires_documentation=True
            ),
            'meals_entertainment': TaxCategory(
                category='meals_entertainment',
                code='MEALS',
                deductible_percentage=50.0,
                description='Business meals and entertainment',
                requires_documentation=True
            ),
            'travel': TaxCategory(
                category='travel',
                code='TRAVEL',
                deductible_percentage=100.0,
                description='Business travel expenses',
                requires_documentation=True
            ),
            'vehicle_expenses': TaxCategory(
                category='vehicle_expenses',
                code='VEHICLE',
                deductible_percentage=100.0,
                description='Vehicle and transportation expenses',
                requires_documentation=True
            ),
            'professional_services': TaxCategory(
                category='professional_services',
                code='PROF',
                deductible_percentage=100.0,
                description='Professional and consulting services',
                requires_documentation=True
            ),
            'equipment': TaxCategory(
                category='equipment',
                code='EQUIP',
                deductible_percentage=100.0,
                description='Business equipment and tools',
                requires_documentation=True
            ),
            'utilities': TaxCategory(
                category='utilities',
                code='UTIL',
                deductible_percentage=100.0,
                description='Utilities and communications',
                requires_documentation=False
            ),
            'insurance': TaxCategory(
                category='insurance',
                code='INS',
                deductible_percentage=100.0,
                description='Business insurance premiums',
                requires_documentation=True
            )
        }
    
    def _load_categorization_rules(self) -> Dict[str, List[str]]:
        """Load rules for automatic categorization."""
        return {
            'office_supplies': ['staples', 'office depot', 'amazon', 'supplies', 'paper', 'ink'],
            'meals_entertainment': ['restaurant', 'starbucks', 'coffee', 'lunch', 'dinner', 'food'],
            'travel': ['airline', 'hotel', 'uber', 'taxi', 'rental car', 'marriott', 'hilton'],
            'vehicle_expenses': ['shell', 'exxon', 'gas', 'fuel', 'parking', 'toll'],
            'professional_services': ['consulting', 'legal', 'accounting', 'professional'],
            'equipment': ['computer', 'laptop', 'tools', 'equipment', 'home depot'],
            'utilities': ['phone', 'internet', 'electricity', 'water', 'utility'],
            'insurance': ['insurance', 'premium', 'coverage']
        }
    
    def categorize_expense(self, receipt: Receipt) -> Dict[str, Any]:
        """Categorize expense and calculate tax implications."""
        category = receipt.category or self._auto_categorize(receipt)
        
        if category not in self.tax_categories:
            category = 'general_expense'
        
        tax_category = self.tax_categories.get(category)
        if not tax_category:
            # Default category
            tax_category = TaxCategory(
                category='general_expense',
                code='GENERAL',
                deductible_percentage=0.0,
                description='General business expense',
                requires_documentation=True
            )
        
        deductible_amount = receipt.total_amount * (tax_category.deductible_percentage / 100)
        
        return {
            'receipt_id': receipt.id,
            'category': category,
            'tax_code': tax_category.code,
            'total_amount': receipt.total_amount,
            'deductible_amount': deductible_amount,
            'deductible_percentage': tax_category.deductible_percentage,
            'requires_documentation': tax_category.requires_documentation,
            'confidence': 0.90,
            'suggested_account': self._suggest_account_code(category)
        }
    
    def _auto_categorize(self, receipt: Receipt) -> str:
        """Automatically categorize based on receipt content."""
        text_content = f"{receipt.merchant} {receipt.raw_ocr_text or ''}".lower()
        
        scores = {}
        for category, keywords in self.categorization_rules.items():
            score = sum(1 for keyword in keywords if keyword in text_content)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return 'general_expense'
    
    def _suggest_account_code(self, category: str) -> str:
        """Suggest accounting account code for the category."""
        account_mapping = {
            'office_supplies': '6100',
            'meals_entertainment': '6200',
            'travel': '6300',
            'vehicle_expenses': '6400',
            'professional_services': '6500',
            'equipment': '1500',
            'utilities': '6600',
            'insurance': '6700',
            'general_expense': '6000'
        }
        return account_mapping.get(category, '6000')
    
    def generate_tax_summary(self, receipts: List[Receipt]) -> Dict[str, Any]:
        """Generate tax summary for a collection of receipts."""
        categorized_expenses = [self.categorize_expense(receipt) for receipt in receipts]
        
        category_totals = {}
        total_expenses = 0
        total_deductible = 0
        
        for expense in categorized_expenses:
            category = expense['category']
            amount = expense['total_amount']
            deductible = expense['deductible_amount']
            
            if category not in category_totals:
                category_totals[category] = {
                    'total': 0,
                    'deductible': 0,
                    'count': 0
                }
            
            category_totals[category]['total'] += amount
            category_totals[category]['deductible'] += deductible
            category_totals[category]['count'] += 1
            
            total_expenses += amount
            total_deductible += deductible
        
        return {
            'summary_period': datetime.now().strftime('%Y-%m'),
            'total_expenses': round(total_expenses, 2),
            'total_deductible': round(total_deductible, 2),
            'deductible_percentage': round((total_deductible / total_expenses * 100) if total_expenses > 0 else 0, 1),
            'category_breakdown': category_totals,
            'receipts_processed': len(receipts),
            'generated_at': datetime.now().isoformat()
        }

class PayrollAutomation:
    """Automated payroll processing system."""
    
    def __init__(self):
        self.employees = {}
        self.payroll_history = []
        self.tax_tables = self._load_tax_tables()
    
    def _load_tax_tables(self) -> Dict[str, Any]:
        """Load federal and state tax tables."""
        return {
            'federal_tax_brackets': [
                {'min': 0, 'max': 10275, 'rate': 0.10},
                {'min': 10276, 'max': 41775, 'rate': 0.12},
                {'min': 41776, 'max': 89450, 'rate': 0.22},
                {'min': 89451, 'max': 190750, 'rate': 0.24},
                {'min': 190751, 'max': 364200, 'rate': 0.32},
                {'min': 364201, 'max': 462550, 'rate': 0.35},
                {'min': 462551, 'max': float('inf'), 'rate': 0.37}
            ],
            'social_security_rate': 0.062,
            'medicare_rate': 0.0145,
            'medicare_additional_rate': 0.009,  # for income > $200k
            'social_security_wage_base': 160200,
            'standard_deduction': 13850
        }
    
    def add_employee(self, employee: Employee) -> str:
        """Add new employee to payroll system."""
        self.employees[employee.id] = employee
        print(f"👤 Added employee: {employee.name} ({employee.id})")
        return employee.id
    
    def calculate_payroll(self, employee_id: str, pay_period_start: datetime, 
                         pay_period_end: datetime, hours_worked: Optional[float] = None) -> PayrollRecord:
        """Calculate payroll for an employee."""
        if employee_id not in self.employees:
            raise ValueError(f"Employee {employee_id} not found")
        
        employee = self.employees[employee_id]
        
        # Calculate gross pay
        if employee.hourly_rate and hours_worked:
            # Hourly employee
            regular_hours = min(hours_worked, 40)
            overtime_hours = max(0, hours_worked - 40)
            gross_pay = (regular_hours * employee.hourly_rate) + (overtime_hours * employee.hourly_rate * 1.5)
        else:
            # Salaried employee (bi-weekly)
            days_in_period = (pay_period_end - pay_period_start).days
            gross_pay = (employee.salary / 365) * days_in_period
        
        # Calculate deductions
        deductions = self._calculate_deductions(gross_pay, employee)
        
        # Calculate net pay
        net_pay = gross_pay - sum(deductions.values())
        
        payroll_id = f"PAY_{employee_id}_{pay_period_start.strftime('%Y%m%d')}"
        
        payroll_record = PayrollRecord(
            id=payroll_id,
            employee_id=employee_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            gross_pay=round(gross_pay, 2),
            deductions=deductions,
            net_pay=round(net_pay, 2),
            hours_worked=hours_worked,
            overtime_hours=max(0, hours_worked - 40) if hours_worked else None
        )
        
        self.payroll_history.append(payroll_record)
        return payroll_record
    
    def _calculate_deductions(self, gross_pay: float, employee: Employee) -> Dict[str, float]:
        """Calculate all payroll deductions."""
        deductions = {}
        
        # Federal income tax (simplified calculation)
        annual_income = gross_pay * 26  # Bi-weekly to annual
        federal_tax = self._calculate_federal_tax(annual_income) / 26
        deductions['federal_tax'] = round(federal_tax, 2)
        
        # Social Security tax
        ss_tax = min(gross_pay * self.tax_tables['social_security_rate'], 
                    self.tax_tables['social_security_wage_base'] / 26)
        deductions['social_security'] = round(ss_tax, 2)
        
        # Medicare tax
        medicare_tax = gross_pay * self.tax_tables['medicare_rate']
        if annual_income > 200000:
            medicare_tax += gross_pay * self.tax_tables['medicare_additional_rate']
        deductions['medicare'] = round(medicare_tax, 2)
        
        # State tax (simplified - 5% rate)
        state_tax = gross_pay * 0.05
        deductions['state_tax'] = round(state_tax, 2)
        
        # Benefits deductions
        if employee.benefits:
            if 'health_insurance' in employee.benefits:
                deductions['health_insurance'] = employee.benefits['health_insurance']
            if 'dental_insurance' in employee.benefits:
                deductions['dental_insurance'] = employee.benefits['dental_insurance']
            if '401k_contribution' in employee.benefits:
                deductions['401k_contribution'] = gross_pay * employee.benefits['401k_contribution']
        
        return deductions
    
    def _calculate_federal_tax(self, annual_income: float) -> float:
        """Calculate federal income tax using tax brackets."""
        tax_owed = 0
        remaining_income = annual_income - self.tax_tables['standard_deduction']
        
        if remaining_income <= 0:
            return 0
        
        for bracket in self.tax_tables['federal_tax_brackets']:
            if remaining_income <= 0:
                break
            
            taxable_in_bracket = min(remaining_income, bracket['max'] - bracket['min'])
            tax_owed += taxable_in_bracket * bracket['rate']
            remaining_income -= taxable_in_bracket
        
        return tax_owed
    
    def generate_paystub(self, payroll_record: PayrollRecord) -> Dict[str, Any]:
        """Generate detailed paystub."""
        employee = self.employees[payroll_record.employee_id]
        
        return {
            'paystub_id': f"STUB_{payroll_record.id}",
            'employee': {
                'name': employee.name,
                'id': employee.id,
                'position': employee.position,
                'department': employee.department
            },
            'pay_period': {
                'start': payroll_record.pay_period_start.strftime('%Y-%m-%d'),
                'end': payroll_record.pay_period_end.strftime('%Y-%m-%d')
            },
            'earnings': {
                'gross_pay': payroll_record.gross_pay,
                'hours_worked': payroll_record.hours_worked,
                'overtime_hours': payroll_record.overtime_hours,
                'hourly_rate': employee.hourly_rate
            },
            'deductions': payroll_record.deductions,
            'net_pay': payroll_record.net_pay,
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_payroll_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate payroll summary for a period."""
        period_payrolls = [
            p for p in self.payroll_history 
            if start_date <= p.pay_period_start <= end_date
        ]
        
        total_gross = sum(p.gross_pay for p in period_payrolls)
        total_net = sum(p.net_pay for p in period_payrolls)
        total_deductions = total_gross - total_net
        
        deduction_breakdown = {}
        for payroll in period_payrolls:
            for deduction_type, amount in payroll.deductions.items():
                deduction_breakdown[deduction_type] = deduction_breakdown.get(deduction_type, 0) + amount
        
        return {
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'summary': {
                'employees_paid': len(set(p.employee_id for p in period_payrolls)),
                'total_gross_pay': round(total_gross, 2),
                'total_deductions': round(total_deductions, 2),
                'total_net_pay': round(total_net, 2),
                'payroll_count': len(period_payrolls)
            },
            'deduction_breakdown': {k: round(v, 2) for k, v in deduction_breakdown.items()},
            'generated_at': datetime.now().isoformat()
        }

class BusinessLog:
    """Main BusinessLog module orchestrator."""
    
    def __init__(self):
        self.receipt_ocr = ReceiptOCR()
        self.tax_categorizer = TaxCategorizer()
        self.payroll = PayrollAutomation()
        self.receipts = []
        
        print("💼 BusinessLog module initialized")
    
    async def process_receipt_image(self, image_path: str) -> Dict[str, Any]:
        """Process receipt image with OCR and categorization."""
        try:
            # Extract text from image
            ocr_text = self.receipt_ocr.extract_text_from_image(image_path)
            
            if not ocr_text:
                return {"error": "Could not extract text from image"}
            
            # Parse receipt
            receipt = self.receipt_ocr.parse_receipt_text(ocr_text)
            receipt.image_path = image_path
            
            # Categorize for taxes
            tax_info = self.tax_categorizer.categorize_expense(receipt)
            
            # Store receipt
            self.receipts.append(receipt)
            
            print(f"📄 Processed receipt: {receipt.merchant} - ${receipt.total_amount}")
            
            return {
                "success": True,
                "receipt": asdict(receipt),
                "tax_categorization": tax_info,
                "ocr_confidence": receipt.confidence
            }
            
        except Exception as e:
            return {"error": f"Error processing receipt: {str(e)}"}
    
    async def add_employee(self, name: str, position: str, department: str, 
                          salary: Optional[float] = None, hourly_rate: Optional[float] = None) -> str:
        """Add new employee to payroll system."""
        employee_id = f"EMP_{len(self.payroll.employees) + 1:03d}"
        
        employee = Employee(
            id=employee_id,
            name=name,
            position=position,
            department=department,
            salary=salary or 0,
            hourly_rate=hourly_rate,
            hire_date=datetime.now(),
            benefits={
                'health_insurance': 200.0,
                'dental_insurance': 50.0,
                '401k_contribution': 0.06
            }
        )
        
        self.payroll.add_employee(employee)
        return employee_id
    
    async def process_payroll(self, employee_id: str, hours_worked: Optional[float] = None) -> Dict[str, Any]:
        """Process payroll for an employee."""
        try:
            # Calculate bi-weekly pay period
            today = datetime.now()
            pay_period_start = today - timedelta(days=14)
            pay_period_end = today
            
            payroll_record = self.payroll.calculate_payroll(
                employee_id, pay_period_start, pay_period_end, hours_worked
            )
            
            paystub = self.payroll.generate_paystub(payroll_record)
            
            print(f"💰 Processed payroll for {employee_id}: ${payroll_record.net_pay}")
            
            return {
                "success": True,
                "payroll_record": asdict(payroll_record),
                "paystub": paystub
            }
            
        except Exception as e:
            return {"error": f"Error processing payroll: {str(e)}"}
    
    async def generate_tax_report(self, year: Optional[int] = None) -> Dict[str, Any]:
        """Generate comprehensive tax report."""
        target_year = year or datetime.now().year
        
        # Filter receipts by year
        year_receipts = [
            r for r in self.receipts 
            if r.date.year == target_year
        ]
        
        if not year_receipts:
            return {"message": f"No receipts found for {target_year}"}
        
        tax_summary = self.tax_categorizer.generate_tax_summary(year_receipts)
        
        # Add payroll summary
        year_start = datetime(target_year, 1, 1)
        year_end = datetime(target_year, 12, 31)
        payroll_summary = self.payroll.generate_payroll_summary(year_start, year_end)
        
        return {
            "tax_year": target_year,
            "expense_summary": tax_summary,
            "payroll_summary": payroll_summary,
            "total_business_expenses": tax_summary['total_expenses'],
            "total_deductible_expenses": tax_summary['total_deductible'],
            "total_payroll_expenses": payroll_summary['summary']['total_gross_pay'],
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_business_analytics(self) -> Dict[str, Any]:
        """Get comprehensive business analytics."""
        if not self.receipts and not self.payroll.payroll_history:
            return {"message": "No business data available"}
        
        # Expense analytics
        total_expenses = sum(r.total_amount for r in self.receipts)
        avg_expense = total_expenses / len(self.receipts) if self.receipts else 0
        
        monthly_expenses = {}
        for receipt in self.receipts:
            month_key = receipt.date.strftime('%Y-%m')
            monthly_expenses[month_key] = monthly_expenses.get(month_key, 0) + receipt.total_amount
        
        # Category breakdown
        category_totals = {}
        for receipt in self.receipts:
            cat = receipt.category or 'uncategorized'
            category_totals[cat] = category_totals.get(cat, 0) + receipt.total_amount
        
        # Payroll analytics
        total_payroll = sum(p.gross_pay for p in self.payroll.payroll_history)
        avg_payroll = total_payroll / len(self.payroll.payroll_history) if self.payroll.payroll_history else 0
        
        return {
            "expense_analytics": {
                "total_expenses": round(total_expenses, 2),
                "average_expense": round(avg_expense, 2),
                "receipt_count": len(self.receipts),
                "monthly_breakdown": {k: round(v, 2) for k, v in monthly_expenses.items()},
                "category_breakdown": {k: round(v, 2) for k, v in category_totals.items()}
            },
            "payroll_analytics": {
                "total_payroll_paid": round(total_payroll, 2),
                "average_payroll": round(avg_payroll, 2),
                "employee_count": len(self.payroll.employees),
                "payroll_runs": len(self.payroll.payroll_history)
            },
            "generated_at": datetime.now().isoformat()
        }

# CLI interface for testing
async def main():
    """CLI interface for BusinessLog module."""
    business_log = BusinessLog()
    
    print("💼 BusinessLog Module Test Suite")
    print("=" * 40)
    
    # Test 1: Add employees
    print("\n1. Adding employees...")
    emp1 = await business_log.add_employee("John Smith", "Software Engineer", "Engineering", salary=75000)
    emp2 = await business_log.add_employee("Jane Doe", "Marketing Manager", "Marketing", hourly_rate=35.0)
    print(f"✅ Added employees: {emp1}, {emp2}")
    
    # Test 2: Process payroll
    print("\n2. Processing payroll...")
    payroll1 = await business_log.process_payroll(emp1)
    payroll2 = await business_log.process_payroll(emp2, hours_worked=45.0)
    print(f"✅ Payroll processed for {len([payroll1, payroll2])} employees")
    
    # Test 3: Mock receipt processing (since we don't have actual images)
    print("\n3. Processing mock receipts...")
    mock_receipts = [
        {"merchant": "STAPLES", "amount": 45.67, "category": "office_supplies"},
        {"merchant": "STARBUCKS", "amount": 12.50, "category": "meals_entertainment"},
        {"merchant": "SHELL", "amount": 65.00, "category": "vehicle_expenses"}
    ]
    
    for mock_receipt in mock_receipts:
        receipt = Receipt(
            id=f"RCP_{datetime.now().timestamp()}",
            merchant=mock_receipt["merchant"],
            date=datetime.now(),
            total_amount=mock_receipt["amount"],
            currency="USD",
            items=[],
            category=mock_receipt["category"]
        )
        business_log.receipts.append(receipt)
    
    print(f"✅ Added {len(mock_receipts)} mock receipts")
    
    # Test 4: Tax categorization
    print("\n4. Testing tax categorization...")
    tax_summary = business_log.tax_categorizer.generate_tax_summary(business_log.receipts)
    print(f"✅ Tax summary: ${tax_summary['total_deductible']} deductible of ${tax_summary['total_expenses']}")
    
    # Test 5: Generate tax report
    print("\n5. Generating tax report...")
    tax_report = await business_log.generate_tax_report()
    print(f"✅ Tax report generated for {tax_report['tax_year']}")
    
    # Test 6: Business analytics
    print("\n6. Getting business analytics...")
    analytics = await business_log.get_business_analytics()
    print(f"✅ Analytics: {analytics['expense_analytics']['receipt_count']} receipts, {analytics['payroll_analytics']['employee_count']} employees")
    
    # Test 7: OCR text parsing
    print("\n7. Testing OCR text parsing...")
    sample_receipt_text = """WALMART SUPERCENTER
Store #1234
123 MAIN ST
ANYTOWN, ST 12345

01/15/2024 14:30

OFFICE SUPPLIES    $25.99
PRINTER PAPER      $12.50
PENS SET           $8.49

SUBTOTAL          $46.98
TAX               $3.76
TOTAL             $50.74

THANK YOU!"""
    
    parsed_receipt = business_log.receipt_ocr.parse_receipt_text(sample_receipt_text)
    print(f"✅ OCR parsing: {parsed_receipt.merchant} - ${parsed_receipt.total_amount}")
    
    print("\n🎉 BusinessLog module tests completed!")

if __name__ == "__main__":
    asyncio.run(main())