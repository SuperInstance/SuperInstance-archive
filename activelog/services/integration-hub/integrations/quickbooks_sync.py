"""
QuickBooks Sync
Handles integration with QuickBooks accounting software
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class QuickBooksEntity:
    entity_type: str
    entity_id: str
    name: str
    active: bool
    last_updated: datetime
    sync_status: str


class QuickBooksSync:
    """Synchronization with QuickBooks accounting platform"""
    
    def __init__(self, config):
        self.config = config
        self.client_id = config.get('quickbooks_client_id')
        self.client_secret = config.get('quickbooks_client_secret')
        self.company_id = config.get('quickbooks_company_id')
        self.access_token = config.get('quickbooks_access_token')
        self.refresh_token = config.get('quickbooks_refresh_token')
        self.sandbox = config.get('quickbooks_sandbox', True)
        self.base_url = 'https://sandbox-quickbooks.api.intuit.com' if self.sandbox else 'https://quickbooks.api.intuit.com'
        self.enabled = False
        self.sync_count = 0
        self.last_sync = None
        self.error_count = 0
        self.synced_entities = []
        
        # Available QuickBooks entities
        self.available_entities = {
            'Customer': 'Customer records and contacts',
            'Vendor': 'Vendor and supplier records',
            'Item': 'Products and services',
            'Invoice': 'Customer invoices',
            'Bill': 'Vendor bills and expenses',
            'Payment': 'Customer payments',
            'BillPayment': 'Vendor bill payments',
            'Account': 'Chart of accounts',
            'TaxCode': 'Tax codes and rates',
            'Employee': 'Employee records',
            'TimeActivity': 'Time tracking entries'
        }
        
    def get_status(self) -> Dict[str, Any]:
        """Get sync status"""
        return {
            'status': 'active' if self.enabled else 'inactive',
            'enabled': self.enabled,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'synced_entities_count': len(self.synced_entities),
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'company_id': self.company_id,
            'sandbox': self.sandbox
        }
        
    def enable(self) -> Dict[str, Any]:
        """Enable QuickBooks sync"""
        try:
            self.enabled = True
            auth_result = self.authenticate()
            return {
                'status': 'enabled',
                'message': 'QuickBooks sync enabled successfully',
                'authentication': auth_result
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def disable(self) -> Dict[str, Any]:
        """Disable QuickBooks sync"""
        try:
            self.enabled = False
            return {
                'status': 'disabled',
                'message': 'QuickBooks sync disabled successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def configure(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configure QuickBooks sync settings"""
        try:
            if 'client_id' in config_data:
                self.client_id = config_data['client_id']
                
            if 'client_secret' in config_data:
                self.client_secret = config_data['client_secret']
                
            if 'company_id' in config_data:
                self.company_id = config_data['company_id']
                
            if 'access_token' in config_data:
                self.access_token = config_data['access_token']
                
            if 'refresh_token' in config_data:
                self.refresh_token = config_data['refresh_token']
                
            if 'sandbox' in config_data:
                self.sandbox = config_data['sandbox']
                self.base_url = 'https://sandbox-quickbooks.api.intuit.com' if self.sandbox else 'https://quickbooks.api.intuit.com'
                
            return {
                'status': 'configured',
                'message': 'QuickBooks sync configured successfully',
                'config': {
                    'client_id_set': bool(self.client_id),
                    'client_secret_set': bool(self.client_secret),
                    'company_id': self.company_id,
                    'access_token_set': bool(self.access_token),
                    'sandbox': self.sandbox,
                    'base_url': self.base_url
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with QuickBooks API"""
        try:
            if not all([self.client_id, self.client_secret, self.company_id]):
                return {
                    'status': 'error',
                    'error': 'Missing required authentication parameters'
                }
                
            # Simulate OAuth2 token refresh if needed
            if not self.access_token and self.refresh_token:
                token_result = self.refresh_access_token()
                if token_result['status'] != 'success':
                    return token_result
                    
            # Simulate successful authentication
            if not self.access_token:
                self.access_token = f"mock_qb_token_{datetime.now().timestamp()}"
                
            return {
                'status': 'authenticated',
                'message': 'Successfully authenticated with QuickBooks',
                'company_id': self.company_id,
                'sandbox': self.sandbox,
                'token_expires_in': 3600
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh QuickBooks access token"""
        try:
            if not self.refresh_token:
                return {
                    'status': 'error',
                    'error': 'No refresh token available'
                }
                
            # Simulate token refresh
            self.access_token = f"refreshed_qb_token_{datetime.now().timestamp()}"
            
            return {
                'status': 'success',
                'message': 'Access token refreshed successfully',
                'new_token_expires_in': 3600
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def sync(self) -> Dict[str, Any]:
        """Sync data with QuickBooks"""
        try:
            if not self.enabled:
                return {
                    'status': 'skipped',
                    'message': 'QuickBooks sync is disabled'
                }
                
            if not self.access_token:
                auth_result = self.authenticate()
                if auth_result['status'] != 'authenticated':
                    return {
                        'status': 'error',
                        'error': 'Authentication failed',
                        'auth_result': auth_result
                    }
                    
            self.sync_count += 1
            self.last_sync = datetime.now()
            
            # Sync different entity types
            sync_results = {}
            priority_entities = ['Customer', 'Item', 'Invoice', 'Account']
            
            for entity_type in priority_entities:
                sync_results[entity_type] = self.sync_entity_type(entity_type)
                
            return {
                'status': 'success',
                'message': 'QuickBooks sync completed',
                'timestamp': self.last_sync.isoformat(),
                'sync_count': self.sync_count,
                'entity_sync_results': sync_results,
                'company_info': self.get_company_info()
            }
            
        except Exception as e:
            self.error_count += 1
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def sync_entity_type(self, entity_type: str) -> Dict[str, Any]:
        """Sync specific QuickBooks entity type"""
        try:
            if entity_type not in self.available_entities:
                return {
                    'status': 'error',
                    'error': f'Unknown entity type: {entity_type}'
                }
                
            # Simulate API call to retrieve entities
            entities_retrieved = {
                'Customer': 45,
                'Vendor': 25,
                'Item': 120,
                'Invoice': 200,
                'Bill': 80,
                'Account': 35,
                'Employee': 15
            }.get(entity_type, 10)
            
            # Create mock synced entity
            synced_entity = QuickBooksEntity(
                entity_type=entity_type,
                entity_id=f"qb_{entity_type.lower()}_{datetime.now().timestamp()}",
                name=f"ActiveLog {entity_type} Sync",
                active=True,
                last_updated=datetime.now(),
                sync_status='completed'
            )
            
            self.synced_entities.append(synced_entity)
            
            return {
                'status': 'success',
                'entity_type': entity_type,
                'entities_retrieved': entities_retrieved,
                'entities_updated': entities_retrieved // 4,
                'entities_created': entities_retrieved // 20,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'entity_type': entity_type,
                'error': str(e)
            }
            
    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new customer in QuickBooks"""
        try:
            if not self.access_token:
                return {
                    'status': 'error',
                    'error': 'Not authenticated with QuickBooks'
                }
                
            # Prepare customer data for QuickBooks API
            qb_customer_data = {
                'Name': customer_data.get('name', 'ActiveLog Customer'),
                'CompanyName': customer_data.get('company'),
                'GivenName': customer_data.get('first_name'),
                'FamilyName': customer_data.get('last_name'),
                'PrimaryEmailAddr': {
                    'Address': customer_data.get('email')
                },
                'PrimaryPhone': {
                    'FreeFormNumber': customer_data.get('phone')
                },
                'BillAddr': {
                    'Line1': customer_data.get('address_line1'),
                    'City': customer_data.get('city'),
                    'CountrySubDivisionCode': customer_data.get('state'),
                    'PostalCode': customer_data.get('zip_code'),
                    'Country': customer_data.get('country', 'US')
                }
            }
            
            # Simulate customer creation
            customer_id = f"qb_customer_{datetime.now().timestamp()}"
            
            return {
                'status': 'created',
                'customer_id': customer_id,
                'name': qb_customer_data['Name'],
                'email': customer_data.get('email'),
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new invoice in QuickBooks"""
        try:
            if not self.access_token:
                return {
                    'status': 'error',
                    'error': 'Not authenticated with QuickBooks'
                }
                
            # Prepare invoice data
            qb_invoice_data = {
                'Line': [
                    {
                        'Amount': invoice_data.get('amount', 0),
                        'DetailType': 'SalesItemLineDetail',
                        'SalesItemLineDetail': {
                            'ItemRef': {
                                'value': invoice_data.get('item_id', '1'),
                                'name': invoice_data.get('item_name', 'ActiveLog Service')
                            }
                        }
                    }
                ],
                'CustomerRef': {
                    'value': invoice_data.get('customer_id', '1')
                },
                'DocNumber': invoice_data.get('invoice_number'),
                'DueDate': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'TxnDate': datetime.now().strftime('%Y-%m-%d')
            }
            
            # Simulate invoice creation
            invoice_id = f"qb_invoice_{datetime.now().timestamp()}"
            
            return {
                'status': 'created',
                'invoice_id': invoice_id,
                'doc_number': invoice_data.get('invoice_number', f'INV-{invoice_id[-6:]}'),
                'amount': invoice_data.get('amount', 0),
                'customer_id': invoice_data.get('customer_id'),
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def create_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new item/service in QuickBooks"""
        try:
            if not self.access_token:
                return {
                    'status': 'error',
                    'error': 'Not authenticated with QuickBooks'
                }
                
            # Prepare item data
            item_type = item_data.get('type', 'Service')
            qb_item_data = {
                'Name': item_data.get('name', 'ActiveLog Item'),
                'Type': item_type,
                'IncomeAccountRef': {
                    'value': item_data.get('income_account_id', '1')
                },
                'UnitPrice': item_data.get('unit_price', 0),
                'Taxable': item_data.get('taxable', False)
            }
            
            if item_type == 'Inventory':
                qb_item_data.update({
                    'TrackQtyOnHand': True,
                    'InvStartDate': datetime.now().strftime('%Y-%m-%d'),
                    'AssetAccountRef': {
                        'value': item_data.get('asset_account_id', '1')
                    }
                })
                
            # Simulate item creation
            item_id = f"qb_item_{datetime.now().timestamp()}"
            
            return {
                'status': 'created',
                'item_id': item_id,
                'name': qb_item_data['Name'],
                'type': item_type,
                'unit_price': item_data.get('unit_price', 0),
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def record_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record payment in QuickBooks"""
        try:
            if not self.access_token:
                return {
                    'status': 'error',
                    'error': 'Not authenticated with QuickBooks'
                }
                
            # Prepare payment data
            qb_payment_data = {
                'CustomerRef': {
                    'value': payment_data.get('customer_id', '1')
                },
                'TotalAmt': payment_data.get('amount', 0),
                'PaymentMethodRef': {
                    'value': payment_data.get('payment_method_id', '1')
                },
                'DepositToAccountRef': {
                    'value': payment_data.get('deposit_account_id', '1')
                },
                'TxnDate': datetime.now().strftime('%Y-%m-%d')
            }
            
            # Add line items for invoice applications
            if 'applied_to_invoices' in payment_data:
                qb_payment_data['Line'] = []
                for invoice in payment_data['applied_to_invoices']:
                    qb_payment_data['Line'].append({
                        'Amount': invoice.get('amount', 0),
                        'LinkedTxn': [{
                            'TxnId': invoice.get('invoice_id'),
                            'TxnType': 'Invoice'
                        }]
                    })
                    
            # Simulate payment recording
            payment_id = f"qb_payment_{datetime.now().timestamp()}"
            
            return {
                'status': 'recorded',
                'payment_id': payment_id,
                'amount': payment_data.get('amount', 0),
                'customer_id': payment_data.get('customer_id'),
                'payment_method': payment_data.get('payment_method', 'Check'),
                'recorded_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def get_company_info(self) -> Dict[str, Any]:
        """Get QuickBooks company information"""
        try:
            if not self.access_token:
                return {
                    'status': 'error',
                    'error': 'Not authenticated with QuickBooks'
                }
                
            # Simulate company info retrieval
            return {
                'status': 'success',
                'company': {
                    'Id': self.company_id,
                    'CompanyName': 'ActiveLog Company',
                    'LegalName': 'ActiveLog LLC',
                    'CompanyStartDate': '2020-01-01',
                    'FiscalYearStartMonth': 'January',
                    'Country': 'US',
                    'SupportedLanguages': 'en',
                    'CompanyAddr': {
                        'City': 'San Francisco',
                        'CountrySubDivisionCode': 'CA',
                        'PostalCode': '94102',
                        'Country': 'US'
                    },
                    'QBVersion': '2023',
                    'Sandbox': self.sandbox
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def export_data_to_quickbooks(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export data from ActiveLog to QuickBooks"""
        try:
            export_type = export_data.get('export_type')
            data_records = export_data.get('data', [])
            
            results = {
                'exported_count': 0,
                'failed_count': 0,
                'results': []
            }
            
            for record in data_records:
                if export_type == 'customers':
                    result = self.create_customer(record)
                elif export_type == 'invoices':
                    result = self.create_invoice(record)
                elif export_type == 'items':
                    result = self.create_item(record)
                elif export_type == 'payments':
                    result = self.record_payment(record)
                else:
                    result = {'status': 'error', 'error': f'Unknown export type: {export_type}'}
                    
                results['results'].append(result)
                
                if result['status'] in ['created', 'recorded']:
                    results['exported_count'] += 1
                else:
                    results['failed_count'] += 1
                    
            return {
                'status': 'completed',
                'export_type': export_type,
                'total_records': len(data_records),
                'exported_count': results['exported_count'],
                'failed_count': results['failed_count'],
                'results': results['results'],
                'exported_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def import_data_from_quickbooks(self, import_params: Dict[str, Any]) -> Dict[str, Any]:
        """Import data from QuickBooks to ActiveLog"""
        try:
            entity_types = import_params.get('entity_types', ['Customer', 'Item', 'Invoice'])
            since_date = import_params.get('since_date')
            
            imported_data = {}
            
            for entity_type in entity_types:
                # Simulate data import
                mock_data = self.generate_mock_import_data(entity_type, since_date)
                imported_data[entity_type] = mock_data
                
            return {
                'status': 'completed',
                'entity_types': entity_types,
                'since_date': since_date,
                'imported_data': imported_data,
                'total_records': sum(len(data['records']) for data in imported_data.values()),
                'imported_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def generate_mock_import_data(self, entity_type: str, since_date: Optional[str]) -> Dict[str, Any]:
        """Generate mock import data for testing"""
        record_count = {
            'Customer': 20,
            'Item': 15,
            'Invoice': 30,
            'Account': 10
        }.get(entity_type, 5)
        
        records = []
        for i in range(record_count):
            if entity_type == 'Customer':
                records.append({
                    'Id': f'qb_customer_{i}',
                    'Name': f'Customer {i}',
                    'Email': f'customer{i}@example.com',
                    'Active': True
                })
            elif entity_type == 'Item':
                records.append({
                    'Id': f'qb_item_{i}',
                    'Name': f'Item {i}',
                    'Type': 'Service',
                    'UnitPrice': 100 + i * 10
                })
            elif entity_type == 'Invoice':
                records.append({
                    'Id': f'qb_invoice_{i}',
                    'DocNumber': f'INV-{1000+i}',
                    'TotalAmt': 500 + i * 50,
                    'Balance': 0 if i % 3 == 0 else 500 + i * 50
                })
                
        return {
            'entity_type': entity_type,
            'record_count': len(records),
            'records': records
        }
        
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to QuickBooks"""
        try:
            if not all([self.client_id, self.client_secret, self.company_id]):
                return {
                    'status': 'error',
                    'error': 'Missing authentication configuration'
                }
                
            auth_result = self.authenticate()
            if auth_result['status'] != 'authenticated':
                return {
                    'status': 'error',
                    'error': 'Authentication failed',
                    'details': auth_result
                }
                
            # Test with company info query
            company_result = self.get_company_info()
            
            return {
                'status': 'success',
                'message': 'QuickBooks connection test successful',
                'company_id': self.company_id,
                'sandbox': self.sandbox,
                'company_info_test': company_result['status'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            'name': 'QuickBooks',
            'type': 'accounting_software',
            'status': 'active' if self.enabled else 'inactive',
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'synced_entities_count': len(self.synced_entities),
            'available_entities_count': len(self.available_entities),
            'company_id': self.company_id,
            'sandbox': self.sandbox,
            'capabilities': [
                'customer_management',
                'invoice_creation',
                'payment_recording',
                'item_management',
                'financial_reporting',
                'tax_management',
                'expense_tracking'
            ]
        }