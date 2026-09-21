#!/usr/bin/env python3
"""
Multi-Language Invoice System
Support for invoices in multiple languages with localization
"""

import json
import sqlite3
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class MultiLanguageInvoiceSystem:
    """Multi-language invoice support system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        self.default_language = 'en'
        
        # Supported languages
        self.supported_languages = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'ar': 'Arabic'
        }
    
    async def initialize(self):
        """Initialize multi-language system"""
        try:
            await self._setup_language_tables()
            await self._setup_default_translations()
            logger.info("Multi-language invoice system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize multi-language system: {e}")
            raise
    
    async def _setup_language_tables(self):
        """Setup language-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS language_templates (
                id TEXT PRIMARY KEY,
                language_code TEXT NOT NULL,
                template_type TEXT NOT NULL,
                translations TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_languages (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                preferred_language TEXT NOT NULL,
                currency_preference TEXT,
                date_format TEXT,
                number_format TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _setup_default_translations(self):
        """Setup default translations for supported languages"""
        default_translations = {
            'en': {
                'invoice': 'Invoice',
                'quote': 'Quote',
                'credit_note': 'Credit Note',
                'date': 'Date',
                'due_date': 'Due Date',
                'amount': 'Amount',
                'description': 'Description',
                'quantity': 'Quantity',
                'unit_price': 'Unit Price',
                'total': 'Total',
                'subtotal': 'Subtotal',
                'tax': 'Tax',
                'discount': 'Discount',
                'payment_terms': 'Payment Terms',
                'thank_you': 'Thank you for your business'
            },
            'es': {
                'invoice': 'Factura',
                'quote': 'Cotización',
                'credit_note': 'Nota de Crédito',
                'date': 'Fecha',
                'due_date': 'Fecha de Vencimiento',
                'amount': 'Importe',
                'description': 'Descripción',
                'quantity': 'Cantidad',
                'unit_price': 'Precio Unitario',
                'total': 'Total',
                'subtotal': 'Subtotal',
                'tax': 'Impuesto',
                'discount': 'Descuento',
                'payment_terms': 'Términos de Pago',
                'thank_you': 'Gracias por su negocio'
            },
            'fr': {
                'invoice': 'Facture',
                'quote': 'Devis',
                'credit_note': 'Note de Crédit',
                'date': 'Date',
                'due_date': 'Date d\'Échéance',
                'amount': 'Montant',
                'description': 'Description',
                'quantity': 'Quantité',
                'unit_price': 'Prix Unitaire',
                'total': 'Total',
                'subtotal': 'Sous-total',
                'tax': 'Taxe',
                'discount': 'Remise',
                'payment_terms': 'Conditions de Paiement',
                'thank_you': 'Merci pour votre confiance'
            }
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for lang_code, translations in default_translations.items():
            cursor.execute('''
                INSERT OR REPLACE INTO language_templates (
                    id, language_code, template_type, translations
                ) VALUES (?, ?, ?, ?)
            ''', (
                f"LANG_{lang_code.upper()}_{uuid.uuid4().hex[:6].upper()}",
                lang_code, 'invoice_default', json.dumps(translations)
            ))
        
        conn.commit()
        conn.close()
    
    async def add_language_template(self, language_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add custom language template"""
        try:
            template_id = f"LANG_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO language_templates (
                    id, language_code, template_type, translations
                ) VALUES (?, ?, ?, ?)
            ''', (
                template_id, language_data['language_code'],
                language_data.get('template_type', 'custom'),
                json.dumps(language_data['translations'])
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'template_id': template_id,
                'language_code': language_data['language_code']
            }
            
        except Exception as e:
            logger.error(f"Error adding language template: {e}")
            return {
                'success': False,
                'error': f"Language template error: {str(e)}"
            }
    
    async def set_customer_language(self, customer_id: str, language_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Set customer language preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if preferences exist
            cursor.execute('SELECT id FROM customer_languages WHERE customer_id = ?', (customer_id,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE customer_languages 
                    SET preferred_language = ?, currency_preference = ?,
                        date_format = ?, number_format = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = ?
                ''', (
                    language_preferences['preferred_language'],
                    language_preferences.get('currency_preference'),
                    language_preferences.get('date_format', 'YYYY-MM-DD'),
                    language_preferences.get('number_format', '1,000.00'),
                    customer_id
                ))
            else:
                pref_id = f"PREF_{uuid.uuid4().hex[:8].upper()}"
                cursor.execute('''
                    INSERT INTO customer_languages (
                        id, customer_id, preferred_language, currency_preference,
                        date_format, number_format
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    pref_id, customer_id, language_preferences['preferred_language'],
                    language_preferences.get('currency_preference'),
                    language_preferences.get('date_format', 'YYYY-MM-DD'),
                    language_preferences.get('number_format', '1,000.00')
                ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'customer_id': customer_id,
                'preferred_language': language_preferences['preferred_language']
            }
            
        except Exception as e:
            logger.error(f"Error setting customer language: {e}")
            return {
                'success': False,
                'error': f"Language preference error: {str(e)}"
            }
    
    async def get_translations(self, language_code: str) -> Dict[str, str]:
        """Get translations for specified language"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT translations FROM language_templates
                WHERE language_code = ? AND is_active = TRUE
                ORDER BY created_at DESC LIMIT 1
            ''', (language_code,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
            else:
                # Return English as fallback
                return await self.get_translations('en')
                
        except Exception as e:
            logger.error(f"Error getting translations: {e}")
            return {}
    
    async def list_languages(self) -> Dict[str, Any]:
        """List supported languages"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT language_code FROM language_templates
                WHERE is_active = TRUE
                ORDER BY language_code
            ''')
            
            available_languages = []
            for row in cursor.fetchall():
                lang_code = row[0]
                lang_name = self.supported_languages.get(lang_code, lang_code.upper())
                available_languages.append({
                    'code': lang_code,
                    'name': lang_name
                })
            
            conn.close()
            
            return {
                'success': True,
                'languages': available_languages,
                'default_language': self.default_language
            }
            
        except Exception as e:
            logger.error(f"Error listing languages: {e}")
            return {
                'success': False,
                'error': f"Language list error: {str(e)}"
            }

# Global instance
multilang_system = MultiLanguageInvoiceSystem()