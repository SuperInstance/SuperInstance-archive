#!/usr/bin/env python3
"""
Patent Manager for Legal Framework
Handles patent filing assistance and prior art searches
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
import json
import uuid

class PatentManager:
    """Patent management system"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/patents.db'
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize patent database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS patents (
                    patent_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    inventors TEXT NOT NULL,
                    status TEXT NOT NULL,
                    filing_date TEXT NOT NULL,
                    created_date TEXT NOT NULL
                )
            ''')
    
    def file_patent(self, patent_data: Dict[str, Any]) -> Dict[str, Any]:
        """File patent application"""
        try:
            patent_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO patents 
                    (patent_id, title, description, inventors, status, filing_date, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    patent_id,
                    patent_data.get('title', ''),
                    patent_data.get('description', ''),
                    json.dumps(patent_data.get('inventors', [])),
                    'filed',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            return {
                'success': True,
                'patent_id': patent_id,
                'status': 'filed'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_prior_art(self, search_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search prior art"""
        try:
            keywords = search_data.get('keywords', [])
            
            # Mock prior art search results
            results = [
                {
                    'patent_number': 'US10123456',
                    'title': 'System and Method for Data Processing',
                    'relevance_score': 0.85,
                    'publication_date': '2020-01-15'
                },
                {
                    'patent_number': 'US9876543',
                    'title': 'Advanced Computing Architecture',
                    'relevance_score': 0.72,
                    'publication_date': '2019-06-22'
                }
            ]
            
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