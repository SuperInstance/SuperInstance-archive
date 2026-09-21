#!/usr/bin/env python3
"""
Revenue Sharing Manager for Legal Framework
Handles revenue sharing contracts and calculations
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
import json
import uuid

class RevenueSharingManager:
    """Revenue sharing contract management"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/revenue_sharing.db'
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize revenue sharing database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS revenue_contracts (
                    contract_id TEXT PRIMARY KEY,
                    parties TEXT NOT NULL,
                    revenue_model TEXT NOT NULL,
                    split_percentage TEXT NOT NULL,
                    created_date TEXT NOT NULL
                )
            ''')
    
    def create_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create revenue sharing contract"""
        try:
            contract_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO revenue_contracts 
                    (contract_id, parties, revenue_model, split_percentage, created_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    contract_id,
                    json.dumps(contract_data.get('parties', [])),
                    contract_data.get('revenue_model', 'percentage'),
                    json.dumps(contract_data.get('split_percentage', {})),
                    datetime.now().isoformat()
                ))
            
            return {
                'success': True,
                'contract_id': contract_id,
                'status': 'created'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_share(self, calculation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate revenue sharing"""
        try:
            total_revenue = calculation_data.get('total_revenue', 0)
            split_percentage = calculation_data.get('split_percentage', {})
            
            shares = {}
            for party, percentage in split_percentage.items():
                shares[party] = total_revenue * (percentage / 100)
            
            return {
                'success': True,
                'total_revenue': total_revenue,
                'shares': shares
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }