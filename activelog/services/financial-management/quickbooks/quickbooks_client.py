#!/usr/bin/env python3
"""
QuickBooks Online API Integration Client
Provides comprehensive integration with QuickBooks Online API for ActiveLog
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import aiohttp
from dataclasses import dataclass, asdict
import base64
import hashlib
import hmac
from urllib.parse import urlencode, parse_qs, urlparse
import jwt
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class QBOAuth:
    """QuickBooks OAuth credentials"""
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    realm_id: Optional[str] = None  # Company ID
    scope: str = "com.intuit.quickbooks.accounting"

@dataclass
class QBOCustomer:
    """QuickBooks Customer entity"""
    id: Optional[str] = None
    name: str = ""
    email: str = ""
    phone: str = ""
    billing_address: Dict[str, str] = None
    shipping_address: Dict[str, str] = None
    payment_terms: str = "Net 30"
    tax_exempt: bool = False
    currency_ref: str = "USD"
    active: bool = True

@dataclass
class QBOItem:
    """QuickBooks Item entity"""
    id: Optional[str] = None
    name: str = ""
    description: str = ""
    unit_price: float = 0.0
    type: str = "Service"  # Service, Inventory, Non-inventory
    income_account_ref: str = ""
    expense_account_ref: str = ""
    asset_account_ref: str = ""
    taxable: bool = True
    active: bool = True

@dataclass
class QBOInvoice:
    """QuickBooks Invoice entity"""
    id: Optional[str] = None
    doc_number: str = ""
    txn_date: str = ""
    due_date: str = ""
    customer_ref: Dict[str, str] = None
    line_items: List[Dict[str, Any]] = None
    currency_ref: str = "USD"
    total_amt: float = 0.0
    balance: float = 0.0
    email_status: str = "NotSet"
    print_status: str = "NotSet"
    payment_ref_num: str = ""
    custom_fields: Dict[str, Any] = None

@dataclass
class QBOPayment:
    """QuickBooks Payment entity"""
    id: Optional[str] = None
    txn_date: str = ""
    customer_ref: Dict[str, str] = None
    total_amt: float = 0.0
    payment_method_ref: Dict[str, str] = None
    payment_ref_num: str = ""
    deposit_to_account_ref: Dict[str, str] = None
    line_items: List[Dict[str, Any]] = None

@dataclass
class QBOEmployee:
    """QuickBooks Employee entity"""
    id: Optional[str] = None
    name: str = ""
    employee_number: str = ""
    ssn: str = ""
    primary_addr: Dict[str, str] = None
    primary_phone: Dict[str, str] = None
    primary_email_addr: Dict[str, str] = None
    employee_type: str = "Regular"
    status: str = "Active"
    hire_date: str = ""
    release_date: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None

class QuickBooksClient:
    """Main QuickBooks Online API client"""
    
    SANDBOX_BASE_URL = "https://sandbox-quickbooks.api.intuit.com"
    PRODUCTION_BASE_URL = "https://quickbooks.api.intuit.com"
    DISCOVERY_DOCUMENT_URL = "https://appcenter.intuit.com/api/v1/connection/oauth2"
    
    def __init__(self, auth: QBOAuth, sandbox: bool = True):
        self.auth = auth
        self.base_url = self.SANDBOX_BASE_URL if sandbox else self.PRODUCTION_BASE_URL
        self.api_version = "v3"
        self.session = None
        self.rate_limiter = AsyncRateLimiter(calls_per_minute=450)  # QBO limit is 500/min
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'Authorization': f'Bearer {self.auth.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _build_url(self, endpoint: str) -> str:
        """Build complete API URL"""
        return f"{self.base_url}/{self.api_version}/company/{self.auth.realm_id}/{endpoint}"
    
    async def _make_request(self, method: str, endpoint: str, 
                          data: Optional[Dict] = None,
                          params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API request with rate limiting"""
        await self.rate_limiter.acquire()
        
        url = self._build_url(endpoint)
        headers = self._get_headers()
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            ) as response:
                
                if response.status == 401:
                    # Token expired, try to refresh
                    await self.refresh_token()
                    headers = self._get_headers()
                    
                    # Retry the request
                    async with self.session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                        params=params
                    ) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.json()
                
                response.raise_for_status()
                return await response.json()
                
        except Exception as e:
            logger.error(f"QuickBooks API request failed: {e}")
            raise
    
    async def refresh_token(self):
        """Refresh OAuth access token"""
        if not self.auth.refresh_token:
            raise ValueError("No refresh token available")
        
        token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.auth.refresh_token
        }
        
        auth_string = base64.b64encode(
            f"{self.auth.client_id}:{self.auth.client_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth_string}',
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        async with self.session.post(token_url, data=data, headers=headers) as response:
            response.raise_for_status()
            token_data = await response.json()
            
            self.auth.access_token = token_data['access_token']
            self.auth.refresh_token = token_data.get('refresh_token', self.auth.refresh_token)
            expires_in = token_data.get('expires_in', 3600)
            self.auth.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("QuickBooks token refreshed successfully")
    
    # Customer Management
    async def create_customer(self, customer: QBOCustomer) -> Dict[str, Any]:
        """Create a new customer in QuickBooks"""
        customer_data = {
            'Name': customer.name,
            'CompanyName': customer.name,
            'Active': customer.active,
            'Taxable': not customer.tax_exempt,
            'CurrencyRef': {'value': customer.currency_ref}
        }
        
        if customer.email:
            customer_data['PrimaryEmailAddr'] = {'Address': customer.email}
        
        if customer.phone:
            customer_data['PrimaryPhone'] = {'FreeFormNumber': customer.phone}
        
        if customer.billing_address:
            customer_data['BillAddr'] = customer.billing_address
        
        if customer.shipping_address:
            customer_data['ShipAddr'] = customer.shipping_address
        
        result = await self._make_request('POST', 'customers', {'Customer': customer_data})
        return result['QueryResponse']['Customer'][0]
    
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer by ID"""
        result = await self._make_request('GET', f'customers/{customer_id}')
        return result['QueryResponse']['Customer'][0]
    
    async def update_customer(self, customer: QBOCustomer) -> Dict[str, Any]:
        """Update existing customer"""
        if not customer.id:
            raise ValueError("Customer ID is required for update")
        
        # Get current customer data for sync token
        current_customer = await self.get_customer(customer.id)
        sync_token = current_customer['SyncToken']
        
        customer_data = {
            'Id': customer.id,
            'SyncToken': sync_token,
            'Name': customer.name,
            'CompanyName': customer.name,
            'Active': customer.active,
            'Taxable': not customer.tax_exempt
        }
        
        if customer.email:
            customer_data['PrimaryEmailAddr'] = {'Address': customer.email}
        
        result = await self._make_request('POST', 'customers', {'Customer': customer_data})
        return result['QueryResponse']['Customer'][0]
    
    async def list_customers(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all customers"""
        query = "SELECT * FROM Customer"
        if active_only:
            query += " WHERE Active = true"
        
        result = await self._make_request('GET', 'query', params={'query': query})
        return result.get('QueryResponse', {}).get('Customer', [])
    
    # Item Management
    async def create_item(self, item: QBOItem) -> Dict[str, Any]:
        """Create a new item in QuickBooks"""
        item_data = {
            'Name': item.name,
            'Description': item.description,
            'Active': item.active,
            'Type': item.type,
            'Taxable': item.taxable,
            'UnitPrice': item.unit_price
        }
        
        if item.income_account_ref:
            item_data['IncomeAccountRef'] = {'value': item.income_account_ref}
        
        result = await self._make_request('POST', 'items', {'Item': item_data})
        return result['QueryResponse']['Item'][0]
    
    async def list_items(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all items"""
        query = "SELECT * FROM Item"
        if active_only:
            query += " WHERE Active = true"
        
        result = await self._make_request('GET', 'query', params={'query': query})
        return result.get('QueryResponse', {}).get('Item', [])
    
    # Invoice Management
    async def create_invoice(self, invoice: QBOInvoice) -> Dict[str, Any]:
        """Create a new invoice in QuickBooks"""
        invoice_data = {
            'TxnDate': invoice.txn_date,
            'DueDate': invoice.due_date,
            'CustomerRef': invoice.customer_ref,
            'Line': invoice.line_items or [],
            'CurrencyRef': {'value': invoice.currency_ref}
        }
        
        if invoice.doc_number:
            invoice_data['DocNumber'] = invoice.doc_number
        
        if invoice.custom_fields:
            invoice_data['CustomField'] = [
                {'Name': key, 'StringValue': str(value)}
                for key, value in invoice.custom_fields.items()
            ]
        
        result = await self._make_request('POST', 'invoices', {'Invoice': invoice_data})
        return result['QueryResponse']['Invoice'][0]
    
    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice by ID"""
        result = await self._make_request('GET', f'invoices/{invoice_id}')
        return result['QueryResponse']['Invoice'][0]
    
    async def send_invoice_email(self, invoice_id: str, email_address: str) -> bool:
        """Send invoice via email"""
        try:
            await self._make_request('POST', f'invoices/{invoice_id}/send', 
                                   params={'sendTo': email_address})
            return True
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False
    
    async def list_invoices(self, start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """List invoices with optional date filter"""
        query = "SELECT * FROM Invoice"
        
        if start_date and end_date:
            query += f" WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'"
        elif start_date:
            query += f" WHERE TxnDate >= '{start_date}'"
        elif end_date:
            query += f" WHERE TxnDate <= '{end_date}'"
        
        result = await self._make_request('GET', 'query', params={'query': query})
        return result.get('QueryResponse', {}).get('Invoice', [])
    
    # Payment Management
    async def create_payment(self, payment: QBOPayment) -> Dict[str, Any]:
        """Create a new payment in QuickBooks"""
        payment_data = {
            'TxnDate': payment.txn_date,
            'CustomerRef': payment.customer_ref,
            'TotalAmt': payment.total_amt,
            'Line': payment.line_items or []
        }
        
        if payment.payment_method_ref:
            payment_data['PaymentMethodRef'] = payment.payment_method_ref
        
        if payment.deposit_to_account_ref:
            payment_data['DepositToAccountRef'] = payment.deposit_to_account_ref
        
        if payment.payment_ref_num:
            payment_data['PaymentRefNum'] = payment.payment_ref_num
        
        result = await self._make_request('POST', 'payments', {'Payment': payment_data})
        return result['QueryResponse']['Payment'][0]
    
    async def list_payments(self, customer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List payments with optional customer filter"""
        query = "SELECT * FROM Payment"
        
        if customer_id:
            query += f" WHERE CustomerRef = '{customer_id}'"
        
        result = await self._make_request('GET', 'query', params={'query': query})
        return result.get('QueryResponse', {}).get('Payment', [])
    
    # Employee Management
    async def create_employee(self, employee: QBOEmployee) -> Dict[str, Any]:
        """Create a new employee in QuickBooks"""
        employee_data = {
            'Name': employee.name,
            'EmployeeNumber': employee.employee_number,
            'EmployeeType': employee.employee_type,
            'Status': employee.status,
            'HiredDate': employee.hire_date
        }
        
        if employee.ssn:
            employee_data['SSN'] = employee.ssn
        
        if employee.primary_addr:
            employee_data['PrimaryAddr'] = employee.primary_addr
        
        if employee.primary_phone:
            employee_data['PrimaryPhone'] = employee.primary_phone
        
        if employee.primary_email_addr:
            employee_data['PrimaryEmailAddr'] = employee.primary_email_addr
        
        if employee.birth_date:
            employee_data['BirthDate'] = employee.birth_date
        
        if employee.gender:
            employee_data['Gender'] = employee.gender
        
        result = await self._make_request('POST', 'employees', {'Employee': employee_data})
        return result['QueryResponse']['Employee'][0]
    
    async def list_employees(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all employees"""
        query = "SELECT * FROM Employee"
        if active_only:
            query += " WHERE Status = 'Active'"
        
        result = await self._make_request('GET', 'query', params={'query': query})
        return result.get('QueryResponse', {}).get('Employee', [])
    
    # Account Management
    async def list_accounts(self, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List chart of accounts"""
        query = "SELECT * FROM Account"
        if account_type:
            query += f" WHERE AccountType = '{account_type}'"
        
        result = await self._make_request('GET', 'query', params={'query': query})
        return result.get('QueryResponse', {}).get('Account', [])
    
    # Tax Management
    async def list_tax_codes(self) -> List[Dict[str, Any]]:
        """List available tax codes"""
        result = await self._make_request('GET', 'query', 
                                        params={'query': 'SELECT * FROM TaxCode'})
        return result.get('QueryResponse', {}).get('TaxCode', [])
    
    async def list_tax_rates(self) -> List[Dict[str, Any]]:
        """List tax rates"""
        result = await self._make_request('GET', 'query', 
                                        params={'query': 'SELECT * FROM TaxRate'})
        return result.get('QueryResponse', {}).get('TaxRate', [])
    
    # Reports
    async def get_profit_loss_report(self, start_date: str, end_date: str,
                                   detail_level: str = 'Summary') -> Dict[str, Any]:
        """Get Profit & Loss report"""
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'detail_level': detail_level
        }
        
        result = await self._make_request('GET', 'reports/ProfitAndLoss', params=params)
        return result
    
    async def get_balance_sheet_report(self, report_date: str,
                                     detail_level: str = 'Summary') -> Dict[str, Any]:
        """Get Balance Sheet report"""
        params = {
            'report_date': report_date,
            'detail_level': detail_level
        }
        
        result = await self._make_request('GET', 'reports/BalanceSheet', params=params)
        return result
    
    async def get_cash_flow_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get Cash Flow report"""
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        result = await self._make_request('GET', 'reports/CashFlow', params=params)
        return result
    
    # Utility Methods
    async def get_company_info(self) -> Dict[str, Any]:
        """Get company information"""
        result = await self._make_request('GET', 'companyinfo/1')
        return result['QueryResponse']['CompanyInfo'][0]
    
    async def get_preferences(self) -> Dict[str, Any]:
        """Get company preferences"""
        result = await self._make_request('GET', 'preferences')
        return result['QueryResponse']['Preferences'][0]

class AsyncRateLimiter:
    """Async rate limiter for API calls"""
    
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make an API call"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_call
            
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                await asyncio.sleep(sleep_time)
            
            self.last_call = time.time()

class QuickBooksWebhookHandler:
    """Handle QuickBooks webhooks for real-time updates"""
    
    def __init__(self, webhook_token: str):
        self.webhook_token = webhook_token
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature"""
        expected_signature = base64.b64encode(
            hmac.new(
                self.webhook_token.encode(),
                payload.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def parse_webhook_payload(self, payload: str) -> Dict[str, Any]:
        """Parse webhook payload"""
        try:
            data = json.loads(payload)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            return {}
    
    async def handle_webhook(self, payload: str, signature: str) -> Dict[str, Any]:
        """Handle incoming webhook"""
        if not self.verify_webhook_signature(payload, signature):
            raise ValueError("Invalid webhook signature")
        
        data = self.parse_webhook_payload(payload)
        
        # Process different entity types
        for entity_data in data.get('eventNotifications', []):
            realm_id = entity_data.get('realmId')
            
            for entity in entity_data.get('dataChangeEvent', {}).get('entities', []):
                entity_name = entity.get('name')
                entity_id = entity.get('id')
                operation = entity.get('operation')
                
                logger.info(f"QuickBooks webhook: {operation} {entity_name} {entity_id} in realm {realm_id}")
                
                # You can add custom logic here to handle different entity changes
                await self.process_entity_change(entity_name, entity_id, operation, realm_id)
        
        return {'status': 'processed'}
    
    async def process_entity_change(self, entity_name: str, entity_id: str, 
                                  operation: str, realm_id: str):
        """Process individual entity changes"""
        # Override this method to add custom logic
        logger.info(f"Processing {operation} for {entity_name} {entity_id}")

def main():
    """Example usage"""
    async def example_usage():
        # Initialize auth
        auth = QBOAuth(
            client_id=os.getenv('QB_CLIENT_ID'),
            client_secret=os.getenv('QB_CLIENT_SECRET'),
            access_token=os.getenv('QB_ACCESS_TOKEN'),
            refresh_token=os.getenv('QB_REFRESH_TOKEN'),
            realm_id=os.getenv('QB_REALM_ID')
        )
        
        async with QuickBooksClient(auth, sandbox=True) as qb_client:
            # Get company info
            company_info = await qb_client.get_company_info()
            print(f"Company: {company_info['CompanyName']}")
            
            # List customers
            customers = await qb_client.list_customers()
            print(f"Found {len(customers)} customers")
            
            # Create a sample customer
            customer = QBOCustomer(
                name="ActiveLog Test Customer",
                email="test@activelog.com",
                phone="555-123-4567"
            )
            
            created_customer = await qb_client.create_customer(customer)
            print(f"Created customer: {created_customer['Id']}")
    
    asyncio.run(example_usage())

if __name__ == '__main__':
    main()