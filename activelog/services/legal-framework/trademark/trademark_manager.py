#!/usr/bin/env python3
"""
Trademark Manager for Legal Framework
Handles trademark registration, searches, and management
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
import json
import uuid

class TrademarkManager:
    """Trademark management system"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/trademarks.db'
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize trademark database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trademarks (
                    trademark_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    class_numbers TEXT NOT NULL,
                    status TEXT NOT NULL,
                    filing_date TEXT NOT NULL,
                    created_date TEXT NOT NULL
                )
            ''')
    
    def register_trademark(self, trademark_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register new trademark"""
        try:
            trademark_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO trademarks 
                    (trademark_id, name, class_numbers, status, filing_date, created_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    trademark_id,
                    trademark_data.get('name', ''),
                    json.dumps(trademark_data.get('class_numbers', [])),
                    'filed',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            return {
                'success': True,
                'trademark_id': trademark_id,
                'status': 'filed'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_trademarks(self, search_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search existing trademarks"""
        try:
            search_term = search_data.get('search_term', '')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM trademarks WHERE name LIKE ?
                ''', (f'%{search_term}%',))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'trademark_id': row[0],
                        'name': row[1],
                        'class_numbers': json.loads(row[2]),
                        'status': row[3]
                    })
            
            return {
                'success': True,
                'results': results,
                'total_found': len(results)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }