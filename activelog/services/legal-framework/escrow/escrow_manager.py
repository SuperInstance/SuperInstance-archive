#!/usr/bin/env python3
"""
Escrow Manager for Legal Framework
Handles code escrow agreements and deposits
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
import json
import uuid
import hashlib

class EscrowManager:
    """Code escrow management system"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/escrow.db'
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize escrow database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS escrow_agreements (
                    escrow_id TEXT PRIMARY KEY,
                    parties TEXT NOT NULL,
                    software_description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_date TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS escrow_deposits (
                    deposit_id TEXT PRIMARY KEY,
                    escrow_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    deposit_date TEXT NOT NULL,
                    FOREIGN KEY(escrow_id) REFERENCES escrow_agreements(escrow_id)
                )
            ''')
    
    def create_escrow(self, escrow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create code escrow agreement"""
        try:
            escrow_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO escrow_agreements 
                    (escrow_id, parties, software_description, status, created_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    escrow_id,
                    json.dumps(escrow_data.get('parties', [])),
                    escrow_data.get('software_description', ''),
                    'active',
                    datetime.now().isoformat()
                ))
            
            return {
                'success': True,
                'escrow_id': escrow_id,
                'status': 'active'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def deposit_code(self, deposit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deposit code to escrow"""
        try:
            deposit_id = str(uuid.uuid4())
            escrow_id = deposit_data.get('escrow_id')
            code_content = deposit_data.get('code_content', '')
            
            # Calculate hash of deposited code
            file_hash = hashlib.sha256(code_content.encode()).hexdigest()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO escrow_deposits 
                    (deposit_id, escrow_id, version, file_hash, deposit_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    deposit_id,
                    escrow_id,
                    deposit_data.get('version', '1.0'),
                    file_hash,
                    datetime.now().isoformat()
                ))
            
            return {
                'success': True,
                'deposit_id': deposit_id,
                'file_hash': file_hash
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }