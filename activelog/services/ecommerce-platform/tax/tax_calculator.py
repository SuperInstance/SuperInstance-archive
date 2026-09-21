"""
Tax Calculator
Handles tax calculations, compliance, and multi-jurisdiction support
"""

import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class TaxType(Enum):
    SALES_TAX = "sales_tax"
    VAT = "vat"  # Value Added Tax
    GST = "gst"  # Goods and Services Tax
    EXCISE = "excise"
    DUTY = "duty"


class TaxExemptionType(Enum):
    RESELLER = "reseller"
    NON_PROFIT = "non_profit"
    GOVERNMENT = "government"
    MEDICAL = "medical"
    EDUCATION = "education"


@dataclass
class TaxRate:
    jurisdiction: str
    tax_type: TaxType
    rate: float
    name: str
    description: Optional[str] = None


@dataclass
class TaxLineItem:
    name: str
    amount: float
    rate: float
    jurisdiction: str
    tax_type: TaxType


class TaxCalculator:
    """Handles tax calculations and compliance"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Tax service configurations
        self.taxjar_config = config.get('taxjar', {})
        self.avalara_config = config.get('avalara', {})
        self.taxcloud_config = config.get('taxcloud', {})
        
        # Load tax tables
        self.tax_rates = self.load_tax_rates()
        self.exempt_categories = self.load_exempt_categories()
        
        # Enable/disable tax calculation
        self.tax_enabled = config.get('tax_enabled', True)
        self.tax_inclusive_pricing = config.get('tax_inclusive_pricing', False)
        
    def calculate_tax(self, tax_calculation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate tax for order"""
        try:
            if not self.tax_enabled:
                return {
                    'total_tax': 0.0,
                    'tax_lines': [],
                    'tax_breakdown': {},
                    'exempt': True,
                    'reason': 'Tax calculation disabled'
                }
                
            # Extract calculation parameters
            shipping_address = tax_calculation_data['shipping_address']
            billing_address = tax_calculation_data.get('billing_address', shipping_address)
            line_items = tax_calculation_data['line_items']
            shipping_amount = tax_calculation_data.get('shipping_amount', 0)
            customer_id = tax_calculation_data.get('customer_id')
            
            # Check for tax exemptions
            exemption_status = self.check_tax_exemption(customer_id, line_items)
            if exemption_status['exempt']:
                return {
                    'total_tax': 0.0,
                    'tax_lines': [],
                    'tax_breakdown': {},
                    'exempt': True,
                    'exemption_type': exemption_status['type'],
                    'reason': exemption_status['reason']
                }
                
            # Determine tax jurisdiction
            jurisdiction = self.determine_tax_jurisdiction(shipping_address, billing_address)
            
            # Calculate taxes using preferred service
            if self.taxjar_config.get('enabled', False):
                return self.calculate_tax_taxjar(jurisdiction, line_items, shipping_amount, shipping_address)
            elif self.avalara_config.get('enabled', False):
                return self.calculate_tax_avalara(jurisdiction, line_items, shipping_amount, shipping_address)
            else:
                return self.calculate_tax_builtin(jurisdiction, line_items, shipping_amount, shipping_address)
                
        except Exception as e:
            raise Exception(f"Error calculating tax: {e}")
            
    def calculate_tax_taxjar(self, jurisdiction: str, line_items: List[Dict], shipping: float, address: Dict) -> Dict[str, Any]:
        """Calculate tax using TaxJar API"""
        try:
            api_token = self.taxjar_config.get('api_token')
            if not api_token:
                raise ValueError("TaxJar API token not configured")
                
            # Prepare TaxJar request
            tax_request = {
                'to_country': address['country'],
                'to_state': address['state'],
                'to_zip': address['zip'],
                'to_city': address['city'],
                'to_street': address['address1'],
                'amount': sum(item['price'] * item['quantity'] for item in line_items),
                'shipping': shipping,
                'line_items': []
            }
            
            # Add line items
            for item in line_items:
                tax_request['line_items'].append({
                    'id': item['product_id'],
                    'quantity': item['quantity'],
                    'product_tax_code': item.get('tax_code', ''),
                    'unit_price': item['price'],
                    'discount': item.get('discount', 0)
                })
                
            # Make API request
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://api.taxjar.com/v2/taxes',
                json=tax_request,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                tax_data = response.json()['tax']
                
                return {
                    'total_tax': tax_data['amount_to_collect'],
                    'tax_lines': self.format_taxjar_response(tax_data),
                    'tax_breakdown': tax_data['breakdown'],
                    'exempt': False,
                    'provider': 'taxjar',
                    'jurisdiction': jurisdiction
                }
            else:
                # Fallback to builtin calculation
                return self.calculate_tax_builtin(jurisdiction, line_items, shipping, address)
                
        except Exception as e:
            print(f"TaxJar API error: {e}")
            # Fallback to builtin calculation
            return self.calculate_tax_builtin(jurisdiction, line_items, shipping, address)
            
    def calculate_tax_avalara(self, jurisdiction: str, line_items: List[Dict], shipping: float, address: Dict) -> Dict[str, Any]:
        """Calculate tax using Avalara AvaTax API"""
        try:
            username = self.avalara_config.get('username')
            password = self.avalara_config.get('password')
            environment = self.avalara_config.get('environment', 'sandbox')
            
            if not username or not password:
                raise ValueError("Avalara credentials not configured")
                
            # Prepare Avalara request
            base_url = 'https://sandbox-rest.avatax.com' if environment == 'sandbox' else 'https://rest.avatax.com'
            
            tax_request = {
                'companyCode': self.avalara_config.get('company_code', 'DEFAULT'),
                'type': 'SalesOrder',
                'customerCode': 'CUSTOMER',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'addresses': {
                    'shipTo': {
                        'line1': address['address1'],
                        'city': address['city'],
                        'region': address['state'],
                        'country': address['country'],
                        'postalCode': address['zip']
                    }
                },
                'lines': []
            }
            
            # Add line items
            for i, item in enumerate(line_items):
                tax_request['lines'].append({
                    'number': str(i + 1),
                    'quantity': item['quantity'],
                    'amount': item['price'] * item['quantity'],
                    'taxCode': item.get('tax_code', ''),
                    'description': item.get('title', f"Item {i + 1}"),
                    'itemCode': item['product_id']
                })
                
            # Add shipping line if applicable
            if shipping > 0:
                tax_request['lines'].append({
                    'number': str(len(line_items) + 1),
                    'quantity': 1,
                    'amount': shipping,
                    'taxCode': 'FR',  # Freight
                    'description': 'Shipping'
                })
                
            # Make API request
            auth = (username, password)
            response = requests.post(
                f'{base_url}/api/v2/transactions/create',
                json=tax_request,
                auth=auth,
                timeout=10
            )
            
            if response.status_code == 201:
                tax_data = response.json()
                
                return {
                    'total_tax': tax_data['totalTax'],
                    'tax_lines': self.format_avalara_response(tax_data),
                    'tax_breakdown': tax_data.get('summary', []),
                    'exempt': False,
                    'provider': 'avalara',
                    'jurisdiction': jurisdiction
                }
            else:
                # Fallback to builtin calculation
                return self.calculate_tax_builtin(jurisdiction, line_items, shipping, address)
                
        except Exception as e:
            print(f"Avalara API error: {e}")
            # Fallback to builtin calculation
            return self.calculate_tax_builtin(jurisdiction, line_items, shipping, address)
            
    def calculate_tax_builtin(self, jurisdiction: str, line_items: List[Dict], shipping: float, address: Dict) -> Dict[str, Any]:
        """Calculate tax using built-in tax tables"""
        try:
            tax_lines = []
            total_tax = 0.0
            tax_breakdown = {}
            
            # Get tax rates for jurisdiction
            applicable_rates = self.get_applicable_tax_rates(jurisdiction, address)
            
            if not applicable_rates:
                return {
                    'total_tax': 0.0,
                    'tax_lines': [],
                    'tax_breakdown': {},
                    'exempt': True,
                    'reason': 'No applicable tax rates found'
                }
                
            # Calculate tax on line items
            subtotal = sum(item['price'] * item['quantity'] for item in line_items)
            
            for rate in applicable_rates:
                # Check if rate applies to products
                if rate.tax_type == TaxType.SALES_TAX:
                    taxable_amount = self.get_taxable_amount(line_items, rate)
                    
                    if taxable_amount > 0:
                        tax_amount = taxable_amount * (rate.rate / 100)
                        total_tax += tax_amount
                        
                        tax_line = TaxLineItem(
                            name=rate.name,
                            amount=tax_amount,
                            rate=rate.rate,
                            jurisdiction=rate.jurisdiction,
                            tax_type=rate.tax_type
                        )
                        tax_lines.append(tax_line)
                        
                        if rate.jurisdiction not in tax_breakdown:
                            tax_breakdown[rate.jurisdiction] = 0
                        tax_breakdown[rate.jurisdiction] += tax_amount
                        
            # Calculate tax on shipping if applicable
            if shipping > 0 and self.is_shipping_taxable(jurisdiction):
                for rate in applicable_rates:
                    if rate.tax_type == TaxType.SALES_TAX:
                        shipping_tax = shipping * (rate.rate / 100)
                        total_tax += shipping_tax
                        
                        tax_line = TaxLineItem(
                            name=f"{rate.name} (Shipping)",
                            amount=shipping_tax,
                            rate=rate.rate,
                            jurisdiction=rate.jurisdiction,
                            tax_type=rate.tax_type
                        )
                        tax_lines.append(tax_line)
                        
                        if rate.jurisdiction not in tax_breakdown:
                            tax_breakdown[rate.jurisdiction] = 0
                        tax_breakdown[rate.jurisdiction] += shipping_tax
                        
            return {
                'total_tax': round(total_tax, 2),
                'tax_lines': [self.tax_line_to_dict(line) for line in tax_lines],
                'tax_breakdown': {k: round(v, 2) for k, v in tax_breakdown.items()},
                'exempt': False,
                'provider': 'builtin',
                'jurisdiction': jurisdiction
            }
            
        except Exception as e:
            raise Exception(f"Error in builtin tax calculation: {e}")
            
    def determine_tax_jurisdiction(self, shipping_address: Dict, billing_address: Dict) -> str:
        """Determine tax jurisdiction based on addresses"""
        try:
            # Use shipping address as primary jurisdiction
            primary_address = shipping_address
            
            # For digital goods, may use billing address
            if self.config.get('digital_goods_billing_address', False):
                primary_address = billing_address
                
            # Create jurisdiction identifier
            country = primary_address.get('country', 'US')
            state = primary_address.get('state', '')
            
            if country == 'US':
                return f"US-{state}"
            else:
                return country
                
        except Exception:
            return "US-CA"  # Default jurisdiction
            
    def get_applicable_tax_rates(self, jurisdiction: str, address: Dict) -> List[TaxRate]:
        """Get applicable tax rates for jurisdiction"""
        try:
            applicable_rates = []
            
            # Get rates from tax tables
            if jurisdiction in self.tax_rates:
                for rate_data in self.tax_rates[jurisdiction]:
                    rate = TaxRate(
                        jurisdiction=rate_data['jurisdiction'],
                        tax_type=TaxType(rate_data['tax_type']),
                        rate=rate_data['rate'],
                        name=rate_data['name'],
                        description=rate_data.get('description')
                    )
                    applicable_rates.append(rate)
                    
            return applicable_rates
            
        except Exception as e:
            print(f"Error getting tax rates: {e}")
            return []
            
    def get_taxable_amount(self, line_items: List[Dict], rate: TaxRate) -> float:
        """Calculate taxable amount for specific tax rate"""
        try:
            taxable_amount = 0.0
            
            for item in line_items:
                # Check if item is tax exempt
                if self.is_item_tax_exempt(item, rate):
                    continue
                    
                # Add to taxable amount
                item_total = item['price'] * item['quantity']
                discount = item.get('discount', 0)
                taxable_amount += max(0, item_total - discount)
                
            return taxable_amount
            
        except Exception:
            return 0.0
            
    def is_item_tax_exempt(self, item: Dict, rate: TaxRate) -> bool:
        """Check if item is exempt from specific tax"""
        try:
            # Check product tax code
            tax_code = item.get('tax_code', '')
            
            # Exempt categories (food, medicine, etc.)
            exempt_codes = self.exempt_categories.get(rate.jurisdiction, [])
            if tax_code in exempt_codes:
                return True
                
            # Check product category
            category = item.get('category', '')
            exempt_categories = ['food', 'medicine', 'books']
            if category.lower() in exempt_categories:
                return True
                
            return False
            
        except Exception:
            return False
            
    def is_shipping_taxable(self, jurisdiction: str) -> bool:
        """Check if shipping is taxable in jurisdiction"""
        try:
            # States where shipping is generally taxable
            taxable_shipping_states = [
                'CA', 'CT', 'DC', 'FL', 'GA', 'HI', 'IL', 'IN', 'KS', 'KY',
                'MI', 'MN', 'NE', 'NV', 'NJ', 'NM', 'NY', 'NC', 'OH', 'PA',
                'RI', 'SD', 'TN', 'TX', 'UT', 'VT', 'WA', 'WV', 'WI', 'WY'
            ]
            
            state = jurisdiction.split('-')[-1] if '-' in jurisdiction else ''
            return state in taxable_shipping_states
            
        except Exception:
            return True  # Default to taxable
            
    def check_tax_exemption(self, customer_id: Optional[str], line_items: List[Dict]) -> Dict[str, Any]:
        """Check if customer or order is tax exempt"""
        try:
            if not customer_id:
                return {'exempt': False}
                
            # Check customer tax exemption status
            customer = self.db.get_customer(customer_id)
            if customer and customer.get('tax_exempt'):
                exemption_type = customer.get('exemption_type', 'unknown')
                exemption_cert = customer.get('exemption_certificate')
                
                if exemption_cert and self.validate_exemption_certificate(exemption_cert):
                    return {
                        'exempt': True,
                        'type': exemption_type,
                        'reason': f'Customer tax exempt: {exemption_type}',
                        'certificate': exemption_cert
                    }
                    
            return {'exempt': False}
            
        except Exception:
            return {'exempt': False}
            
    def validate_exemption_certificate(self, certificate: Dict[str, Any]) -> bool:
        """Validate tax exemption certificate"""
        try:
            required_fields = ['certificate_number', 'issued_by', 'expiry_date']
            
            for field in required_fields:
                if field not in certificate:
                    return False
                    
            # Check expiry date
            expiry_date = datetime.strptime(certificate['expiry_date'], '%Y-%m-%d')
            if expiry_date < datetime.now():
                return False
                
            return True
            
        except Exception:
            return False
            
    def load_tax_rates(self) -> Dict[str, List[Dict]]:
        """Load tax rates from database or config"""
        try:
            # This would typically load from database
            # Using hardcoded rates for demo
            return {
                'US-CA': [
                    {
                        'jurisdiction': 'California',
                        'tax_type': 'sales_tax',
                        'rate': 7.25,
                        'name': 'California State Sales Tax',
                        'description': 'Base state sales tax rate'
                    }
                ],
                'US-NY': [
                    {
                        'jurisdiction': 'New York', 
                        'tax_type': 'sales_tax',
                        'rate': 8.00,
                        'name': 'New York State Sales Tax'
                    }
                ],
                'US-TX': [
                    {
                        'jurisdiction': 'Texas',
                        'tax_type': 'sales_tax', 
                        'rate': 6.25,
                        'name': 'Texas State Sales Tax'
                    }
                ],
                'US-FL': [
                    {
                        'jurisdiction': 'Florida',
                        'tax_type': 'sales_tax',
                        'rate': 6.00,
                        'name': 'Florida State Sales Tax'
                    }
                ]
            }
            
        except Exception:
            return {}
            
    def load_exempt_categories(self) -> Dict[str, List[str]]:
        """Load tax exempt categories by jurisdiction"""
        try:
            return {
                'US-CA': ['FOOD', 'MEDICINE', 'BOOKS'],
                'US-NY': ['FOOD', 'MEDICINE', 'CLOTHING'],
                'US-TX': ['FOOD', 'MEDICINE'],
                'US-FL': ['FOOD', 'MEDICINE', 'BOOKS']
            }
        except Exception:
            return {}
            
    def format_taxjar_response(self, tax_data: Dict) -> List[Dict]:
        """Format TaxJar response to standard format"""
        try:
            tax_lines = []
            
            breakdown = tax_data.get('breakdown', {})
            
            # State tax
            if breakdown.get('state_amount', 0) > 0:
                tax_lines.append({
                    'name': f"{breakdown.get('state_name', 'State')} Tax",
                    'amount': breakdown['state_amount'],
                    'rate': breakdown.get('state_rate', 0) * 100,
                    'jurisdiction': breakdown.get('state_name', 'State')
                })
                
            # County tax  
            if breakdown.get('county_amount', 0) > 0:
                tax_lines.append({
                    'name': f"{breakdown.get('county_name', 'County')} Tax",
                    'amount': breakdown['county_amount'],
                    'rate': breakdown.get('county_rate', 0) * 100,
                    'jurisdiction': breakdown.get('county_name', 'County')
                })
                
            # City tax
            if breakdown.get('city_amount', 0) > 0:
                tax_lines.append({
                    'name': f"{breakdown.get('city_name', 'City')} Tax",
                    'amount': breakdown['city_amount'],
                    'rate': breakdown.get('city_rate', 0) * 100,
                    'jurisdiction': breakdown.get('city_name', 'City')
                })
                
            return tax_lines
            
        except Exception:
            return []
            
    def format_avalara_response(self, tax_data: Dict) -> List[Dict]:
        """Format Avalara response to standard format"""
        try:
            tax_lines = []
            
            for line in tax_data.get('lines', []):
                for detail in line.get('details', []):
                    tax_lines.append({
                        'name': detail.get('taxName', 'Tax'),
                        'amount': detail.get('tax', 0),
                        'rate': detail.get('rate', 0) * 100,
                        'jurisdiction': detail.get('jurisdictionName', '')
                    })
                    
            return tax_lines
            
        except Exception:
            return []
            
    def tax_line_to_dict(self, tax_line: TaxLineItem) -> Dict[str, Any]:
        """Convert TaxLineItem to dictionary"""
        return {
            'name': tax_line.name,
            'amount': round(tax_line.amount, 2),
            'rate': tax_line.rate,
            'jurisdiction': tax_line.jurisdiction,
            'tax_type': tax_line.tax_type.value
        }
        
    def get_tax_summary(self, order_id: str) -> Dict[str, Any]:
        """Get tax summary for order"""
        try:
            # This would load from database
            order_tax = self.db.get_order_tax(order_id)
            
            if not order_tax:
                return {
                    'total_tax': 0.0,
                    'tax_lines': [],
                    'exempt': True
                }
                
            return order_tax
            
        except Exception as e:
            raise Exception(f"Error getting tax summary: {e}")
            
    def save_tax_calculation(self, order_id: str, tax_data: Dict[str, Any]) -> bool:
        """Save tax calculation for order"""
        try:
            tax_record = {
                'order_id': order_id,
                'total_tax': tax_data['total_tax'],
                'tax_lines': json.dumps(tax_data['tax_lines']),
                'tax_breakdown': json.dumps(tax_data.get('tax_breakdown', {})),
                'exempt': tax_data.get('exempt', False),
                'provider': tax_data.get('provider', 'builtin'),
                'jurisdiction': tax_data.get('jurisdiction', ''),
                'calculated_at': datetime.now().isoformat()
            }
            
            self.db.save_order_tax(tax_record)
            return True
            
        except Exception as e:
            print(f"Error saving tax calculation: {e}")
            return False
            
    def get_nexus_jurisdictions(self) -> List[Dict[str, Any]]:
        """Get jurisdictions where business has tax nexus"""
        try:
            return [
                {'jurisdiction': 'US-CA', 'name': 'California', 'nexus_type': 'physical'},
                {'jurisdiction': 'US-NY', 'name': 'New York', 'nexus_type': 'economic'},
                {'jurisdiction': 'US-TX', 'name': 'Texas', 'nexus_type': 'physical'},
                {'jurisdiction': 'US-FL', 'name': 'Florida', 'nexus_type': 'economic'}
            ]
        except Exception as e:
            raise Exception(f"Error getting nexus jurisdictions: {e}")
            
    def update_tax_rates(self) -> Dict[str, Any]:
        """Update tax rates from external sources"""
        try:
            updated_count = 0
            
            # This would fetch latest rates from tax services
            # For demo, just return success
            
            return {
                'success': True,
                'updated_count': updated_count,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error updating tax rates: {e}'
            }