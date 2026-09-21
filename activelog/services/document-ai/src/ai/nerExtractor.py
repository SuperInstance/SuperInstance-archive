#!/usr/bin/env python3
"""
Named Entity Recognition (NER) Module
Extracts entities like people, places, dates, amounts, organizations, etc.
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import uuid
from datetime import datetime
import dateparser

# NLP and NER
import spacy
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk
from nltk.tree import Tree

# Text processing
import pandas as pd
import numpy as np
from textblob import TextBlob

# Utilities
import warnings
warnings.filterwarnings('ignore')

class NERExtractor:
    """Named Entity Recognition using multiple NLP models"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './output/entities')
        self.models_dir = self.config.get('models_dir', './models')
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)
        
        # Entity types to extract
        self.entity_types = {
            'PERSON': 'People names',
            'ORG': 'Organizations',
            'GPE': 'Geopolitical entities (countries, cities, states)',
            'LOCATION': 'Locations',
            'DATE': 'Dates',
            'TIME': 'Times',
            'MONEY': 'Monetary amounts',
            'PERCENT': 'Percentages',
            'QUANTITY': 'Quantities',
            'ORDINAL': 'Ordinal numbers',
            'CARDINAL': 'Cardinal numbers',
            'EMAIL': 'Email addresses',
            'PHONE': 'Phone numbers',
            'URL': 'URLs',
            'SSN': 'Social Security Numbers',
            'CREDIT_CARD': 'Credit card numbers',
            'ACCOUNT_NUMBER': 'Account numbers',
            'LICENSE_PLATE': 'License plates',
            'ADDRESS': 'Physical addresses'
        }
        
        # Custom regex patterns for specific entities
        self.custom_patterns = {
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            'URL': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            'SSN': r'\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b',
            'CREDIT_CARD': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            'ZIP_CODE': r'\b\d{5}(?:-\d{4})?\b',
            'DATE_VARIOUS': r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b',
            'MONEY_AMOUNT': r'\$[\d,]+\.?\d*|\b\d+\.\d{2}\s*(?:USD|dollars?|cents?)\b',
            'PERCENTAGE': r'\b\d+(?:\.\d+)?%\b',
            'ACCOUNT_NUMBER': r'\b(?:account|acct)\.?\s*#?\s*(\d{6,})\b',
            'INVOICE_NUMBER': r'\b(?:invoice|inv)\.?\s*#?\s*([A-Z0-9-]+)\b',
            'CONTRACT_NUMBER': r'\b(?:contract|agreement)\.?\s*#?\s*([A-Z0-9-]+)\b'
        }
        
        # Initialize models
        self.spacy_model = None
        self.transformer_ner = None
        self.nltk_ready = False
        
        # Setup directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize NLP models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize NLP models for NER"""
        
        try:
            # Load spaCy model
            try:
                self.spacy_model = spacy.load("en_core_web_sm")
                self.logger.info("spaCy model loaded successfully")
            except OSError:
                self.logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                self.spacy_model = None
            
            # Load transformer-based NER model
            try:
                self.transformer_ner = pipeline(
                    "ner",
                    model="dbmdz/bert-large-cased-finetuned-conll03-english",
                    aggregation_strategy="simple",
                    device=-1  # Use CPU
                )
                self.logger.info("Transformer NER model loaded successfully")
            except Exception as e:
                self.logger.warning(f"Could not load transformer NER model: {str(e)}")
                self.transformer_ner = None
            
            # Initialize NLTK
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('averaged_perceptron_tagger', quiet=True)
                nltk.download('maxent_ne_chunker', quiet=True)
                nltk.download('words', quiet=True)
                self.nltk_ready = True
                self.logger.info("NLTK models loaded successfully")
            except Exception as e:
                self.logger.warning(f"NLTK initialization failed: {str(e)}")
                self.nltk_ready = False
                
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
    
    def extract_entities(self, text: str, options: Dict = None) -> Dict:
        """
        Extract named entities using multiple NER approaches
        """
        session_id = str(uuid.uuid4())
        options = options or {}
        
        try:
            self.logger.info(f"Extracting entities from text (session: {session_id})")
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'text_length': len(text),
                'extraction_methods': {},
                'entities': {}
            }
            
            # Method 1: Custom regex patterns
            regex_entities = self._extract_regex_entities(text)
            result['extraction_methods']['regex'] = regex_entities
            
            # Method 2: spaCy NER
            if self.spacy_model:
                spacy_entities = self._extract_spacy_entities(text)
                result['extraction_methods']['spacy'] = spacy_entities
            
            # Method 3: Transformer NER
            if self.transformer_ner:
                transformer_entities = self._extract_transformer_entities(text)
                result['extraction_methods']['transformer'] = transformer_entities
            
            # Method 4: NLTK NER
            if self.nltk_ready:
                nltk_entities = self._extract_nltk_entities(text)
                result['extraction_methods']['nltk'] = nltk_entities
            
            # Method 5: Document-specific entity extraction
            document_entities = self._extract_document_specific_entities(text, options)
            result['extraction_methods']['document_specific'] = document_entities
            
            # Consolidate and deduplicate entities
            consolidated_entities = self._consolidate_entities(result['extraction_methods'])
            result['entities'] = consolidated_entities
            
            # Add entity statistics
            result['statistics'] = self._calculate_entity_statistics(consolidated_entities)
            
            # Extract relationships between entities
            if options.get('extract_relationships', False):
                relationships = self._extract_entity_relationships(text, consolidated_entities)
                result['relationships'] = relationships
            
            # Save results
            self._save_ner_results(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False
            }
    
    def _extract_regex_entities(self, text: str) -> Dict:
        """Extract entities using custom regex patterns"""
        
        entities = {}
        
        for entity_type, pattern in self.custom_patterns.items():
            matches = []
            
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities_data = {
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 1.0,  # Regex matches are certain
                    'method': 'regex'
                }
                
                # Additional processing for specific types
                if entity_type == 'DATE_VARIOUS':
                    parsed_date = self._parse_date(match.group())
                    if parsed_date:
                        entities_data['parsed_date'] = parsed_date.isoformat()
                
                elif entity_type == 'MONEY_AMOUNT':
                    amount = self._parse_money_amount(match.group())
                    if amount:
                        entities_data['amount'] = amount
                
                elif entity_type == 'PHONE':
                    formatted_phone = self._format_phone_number(match.group())
                    entities_data['formatted'] = formatted_phone
                
                matches.append(entities_data)
            
            if matches:
                entities[entity_type] = matches
        
        return entities
    
    def _extract_spacy_entities(self, text: str) -> Dict:
        """Extract entities using spaCy NER"""
        
        entities = {}
        
        try:
            # Process text
            doc = self.spacy_model(text)
            
            # Extract entities
            for ent in doc.ents:
                entity_type = ent.label_
                
                if entity_type not in entities:
                    entities[entity_type] = []
                
                entity_data = {
                    'text': ent.text,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 1.0,  # spaCy doesn't provide confidence scores by default
                    'method': 'spacy',
                    'description': spacy.explain(entity_type) or entity_type
                }
                
                # Additional processing for dates and money
                if entity_type in ['DATE', 'TIME']:
                    parsed_date = self._parse_date(ent.text)
                    if parsed_date:
                        entity_data['parsed_date'] = parsed_date.isoformat()
                
                elif entity_type == 'MONEY':
                    amount = self._parse_money_amount(ent.text)
                    if amount:
                        entity_data['amount'] = amount
                
                entities[entity_type].append(entity_data)
        
        except Exception as e:
            self.logger.warning(f"spaCy entity extraction failed: {str(e)}")
        
        return entities
    
    def _extract_transformer_entities(self, text: str) -> Dict:
        """Extract entities using transformer model"""
        
        entities = {}
        
        try:
            # Split text into chunks if too long
            max_length = 512
            text_chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            
            for chunk_idx, chunk in enumerate(text_chunks):
                if not chunk.strip():
                    continue
                
                # Extract entities
                ner_results = self.transformer_ner(chunk)
                
                for entity in ner_results:
                    entity_type = entity['entity_group']
                    
                    if entity_type not in entities:
                        entities[entity_type] = []
                    
                    # Adjust positions for chunk offset
                    chunk_offset = chunk_idx * max_length
                    
                    entity_data = {
                        'text': entity['word'],
                        'start': entity['start'] + chunk_offset,
                        'end': entity['end'] + chunk_offset,
                        'confidence': entity['score'],
                        'method': 'transformer'
                    }
                    
                    entities[entity_type].append(entity_data)
        
        except Exception as e:
            self.logger.warning(f"Transformer entity extraction failed: {str(e)}")
        
        return entities
    
    def _extract_nltk_entities(self, text: str) -> Dict:
        """Extract entities using NLTK"""
        
        entities = {}
        
        try:
            # Tokenize and tag
            sentences = sent_tokenize(text)
            
            for sent in sentences:
                tokens = word_tokenize(sent)
                pos_tags = pos_tag(tokens)
                chunks = ne_chunk(pos_tags)
                
                current_chunk = []
                current_label = None
                char_position = text.find(sent)
                word_position = 0
                
                for chunk in chunks:
                    if isinstance(chunk, Tree):
                        # Named entity
                        entity_text = ' '.join([token for token, pos in chunk.leaves()])
                        entity_type = chunk.label()
                        
                        # Calculate character positions
                        start_pos = char_position + text[char_position:].find(entity_text)
                        end_pos = start_pos + len(entity_text)
                        
                        if entity_type not in entities:
                            entities[entity_type] = []
                        
                        entities[entity_type].append({
                            'text': entity_text,
                            'start': start_pos,
                            'end': end_pos,
                            'confidence': 0.8,  # NLTK doesn't provide confidence
                            'method': 'nltk'
                        })
                    else:
                        word_position += len(chunk[0]) + 1  # +1 for space
        
        except Exception as e:
            self.logger.warning(f"NLTK entity extraction failed: {str(e)}")
        
        return entities
    
    def _extract_document_specific_entities(self, text: str, options: Dict) -> Dict:
        """Extract document-specific entities based on context"""
        
        entities = {}
        doc_type = options.get('document_type', 'unknown')
        
        # Invoice-specific entities
        if doc_type == 'invoice':
            entities.update(self._extract_invoice_entities(text))
        
        # Contract-specific entities
        elif doc_type == 'contract':
            entities.update(self._extract_contract_entities(text))
        
        # Resume-specific entities
        elif doc_type == 'resume':
            entities.update(self._extract_resume_entities(text))
        
        # Financial report entities
        elif doc_type == 'financial_report':
            entities.update(self._extract_financial_entities(text))
        
        # Medical record entities
        elif doc_type == 'medical_record':
            entities.update(self._extract_medical_entities(text))
        
        # General business entities
        else:
            entities.update(self._extract_general_business_entities(text))
        
        return entities
    
    def _extract_invoice_entities(self, text: str) -> Dict:
        """Extract invoice-specific entities"""
        
        entities = {}
        
        # Invoice numbers
        invoice_patterns = [
            r'invoice\s*#?\s*([A-Z0-9-]+)',
            r'inv\.?\s*#?\s*([A-Z0-9-]+)',
            r'bill\s*#?\s*([A-Z0-9-]+)'
        ]
        
        invoice_numbers = []
        for pattern in invoice_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                invoice_numbers.append({
                    'text': match.group(),
                    'number': match.group(1),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9,
                    'method': 'document_specific'
                })
        
        if invoice_numbers:
            entities['INVOICE_NUMBER'] = invoice_numbers
        
        # Due dates
        due_date_patterns = [
            r'due\s+(?:date\s*:?\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'payment\s+due\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        due_dates = []
        for pattern in due_date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                parsed_date = self._parse_date(match.group(1))
                due_date_data = {
                    'text': match.group(),
                    'date': match.group(1),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9,
                    'method': 'document_specific'
                }
                if parsed_date:
                    due_date_data['parsed_date'] = parsed_date.isoformat()
                due_dates.append(due_date_data)
        
        if due_dates:
            entities['DUE_DATE'] = due_dates
        
        # Line items with amounts
        line_item_pattern = r'(.+?)\s+\$?([\d,]+\.?\d*)'
        line_items = []
        for match in re.finditer(line_item_pattern, text):
            item_text = match.group(1).strip()
            amount_text = match.group(2)
            
            # Filter out likely headers or totals
            if len(item_text) > 5 and not re.search(r'total|subtotal|tax|amount', item_text, re.IGNORECASE):
                line_items.append({
                    'text': match.group(),
                    'item': item_text,
                    'amount': amount_text,
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.7,
                    'method': 'document_specific'
                })
        
        if line_items:
            entities['LINE_ITEM'] = line_items[:10]  # Limit to first 10 items
        
        return entities
    
    def _extract_contract_entities(self, text: str) -> Dict:
        """Extract contract-specific entities"""
        
        entities = {}
        
        # Contract parties
        party_patterns = [
            r'party\s+of\s+the\s+first\s+part[,\s]+([^,\n]+)',
            r'party\s+of\s+the\s+second\s+part[,\s]+([^,\n]+)',
            r'between\s+([^,\n]+)\s+and\s+([^,\n]+)',
            r'contractor[:\s]+([^,\n]+)',
            r'client[:\s]+([^,\n]+)'
        ]
        
        parties = []
        for pattern in party_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                    party_name = match.group(i).strip()
                    if party_name and len(party_name) > 2:
                        parties.append({
                            'text': party_name,
                            'start': match.start(i),
                            'end': match.end(i),
                            'confidence': 0.8,
                            'method': 'document_specific',
                            'role': f'party_{i}'
                        })
        
        if parties:
            entities['CONTRACT_PARTY'] = parties
        
        # Effective dates
        effective_date_patterns = [
            r'effective\s+(?:date\s*:?\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'commencing\s+(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'beginning\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        effective_dates = []
        for pattern in effective_date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                parsed_date = self._parse_date(match.group(1))
                date_data = {
                    'text': match.group(),
                    'date': match.group(1),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9,
                    'method': 'document_specific'
                }
                if parsed_date:
                    date_data['parsed_date'] = parsed_date.isoformat()
                effective_dates.append(date_data)
        
        if effective_dates:
            entities['EFFECTIVE_DATE'] = effective_dates
        
        return entities
    
    def _extract_resume_entities(self, text: str) -> Dict:
        """Extract resume-specific entities"""
        
        entities = {}
        
        # Education institutions
        education_patterns = [
            r'(university\s+of\s+[^,\n]+)',
            r'([^,\n]+\s+university)',
            r'([^,\n]+\s+college)',
            r'([^,\n]+\s+institute)',
            r'([^,\n]+\s+school)'
        ]
        
        education = []
        for pattern in education_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                institution = match.group(1).strip()
                if len(institution) > 5:
                    education.append({
                        'text': institution,
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.8,
                        'method': 'document_specific'
                    })
        
        if education:
            entities['EDUCATION_INSTITUTION'] = education
        
        # Skills
        skill_patterns = [
            r'skills?\s*:?\s*([^,\n]+(?:,\s*[^,\n]+)*)',
            r'technical\s+skills?\s*:?\s*([^,\n]+(?:,\s*[^,\n]+)*)',
            r'proficient\s+in\s*:?\s*([^,\n]+(?:,\s*[^,\n]+)*)'
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill_text = match.group(1).strip()
                individual_skills = [s.strip() for s in skill_text.split(',')]
                for skill in individual_skills:
                    if len(skill) > 2:
                        skills.append({
                            'text': skill,
                            'start': match.start(),
                            'end': match.end(),
                            'confidence': 0.7,
                            'method': 'document_specific'
                        })
        
        if skills:
            entities['SKILL'] = skills[:15]  # Limit to first 15 skills
        
        return entities
    
    def _extract_financial_entities(self, text: str) -> Dict:
        """Extract financial report entities"""
        
        entities = {}
        
        # Financial metrics
        metric_patterns = [
            r'(revenue|income|profit|loss|earnings)\s*:?\s*\$?([\d,]+\.?\d*)',
            r'(assets|liabilities|equity)\s*:?\s*\$?([\d,]+\.?\d*)',
            r'(cash\s+flow)\s*:?\s*\$?([\d,]+\.?\d*)'
        ]
        
        metrics = []
        for pattern in metric_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                metric_name = match.group(1)
                amount = match.group(2)
                metrics.append({
                    'text': match.group(),
                    'metric': metric_name,
                    'amount': amount,
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.8,
                    'method': 'document_specific'
                })
        
        if metrics:
            entities['FINANCIAL_METRIC'] = metrics
        
        return entities
    
    def _extract_medical_entities(self, text: str) -> Dict:
        """Extract medical record entities"""
        
        entities = {}
        
        # Medical conditions
        condition_patterns = [
            r'diagnosis\s*:?\s*([^,\n]+)',
            r'condition\s*:?\s*([^,\n]+)',
            r'symptoms?\s*:?\s*([^,\n]+)'
        ]
        
        conditions = []
        for pattern in condition_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                condition = match.group(1).strip()
                if len(condition) > 3:
                    conditions.append({
                        'text': condition,
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.8,
                        'method': 'document_specific'
                    })
        
        if conditions:
            entities['MEDICAL_CONDITION'] = conditions
        
        return entities
    
    def _extract_general_business_entities(self, text: str) -> Dict:
        """Extract general business entities"""
        
        entities = {}
        
        # Company names (simple pattern)
        company_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|Corp|LLC|Ltd|Co)\.?',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Company|Corporation|Limited)'
        ]
        
        companies = []
        for pattern in company_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                company = match.group(1).strip()
                if len(company) > 3:
                    companies.append({
                        'text': match.group(),
                        'company': company,
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.7,
                        'method': 'document_specific'
                    })
        
        if companies:
            entities['COMPANY'] = companies
        
        return entities
    
    def _consolidate_entities(self, extraction_methods: Dict) -> Dict:
        """Consolidate entities from different extraction methods"""
        
        consolidated = {}
        
        # Collect all entities by type
        for method, entities in extraction_methods.items():
            for entity_type, entity_list in entities.items():
                if entity_type not in consolidated:
                    consolidated[entity_type] = []
                
                for entity in entity_list:
                    # Add method information if not present
                    if 'method' not in entity:
                        entity['method'] = method
                    
                    consolidated[entity_type].append(entity)
        
        # Deduplicate and merge similar entities
        for entity_type in consolidated:
            consolidated[entity_type] = self._deduplicate_entities(consolidated[entity_type])
        
        return consolidated
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities and merge similar ones"""
        
        if not entities:
            return entities
        
        # Sort by position
        entities.sort(key=lambda x: x.get('start', 0))
        
        # Group overlapping entities
        deduplicated = []
        current_group = [entities[0]]
        
        for entity in entities[1:]:
            # Check if entities overlap
            if self._entities_overlap(current_group[-1], entity):
                current_group.append(entity)
            else:
                # Process current group
                best_entity = self._select_best_entity(current_group)
                deduplicated.append(best_entity)
                current_group = [entity]
        
        # Process last group
        if current_group:
            best_entity = self._select_best_entity(current_group)
            deduplicated.append(best_entity)
        
        return deduplicated
    
    def _entities_overlap(self, entity1: Dict, entity2: Dict) -> bool:
        """Check if two entities overlap"""
        
        start1, end1 = entity1.get('start', 0), entity1.get('end', 0)
        start2, end2 = entity2.get('start', 0), entity2.get('end', 0)
        
        # Check for overlap
        return not (end1 <= start2 or end2 <= start1)
    
    def _select_best_entity(self, entities: List[Dict]) -> Dict:
        """Select the best entity from overlapping entities"""
        
        if len(entities) == 1:
            return entities[0]
        
        # Prefer entities with higher confidence
        best_entity = max(entities, key=lambda x: x.get('confidence', 0))
        
        # Merge information from other entities
        best_entity['alternative_extractions'] = [
            {
                'text': e.get('text'),
                'method': e.get('method'),
                'confidence': e.get('confidence')
            }
            for e in entities if e != best_entity
        ]
        
        return best_entity
    
    def _extract_entity_relationships(self, text: str, entities: Dict) -> Dict:
        """Extract relationships between entities"""
        
        relationships = []
        
        # Simple relationship extraction based on proximity
        all_entities = []
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                entity['type'] = entity_type
                all_entities.append(entity)
        
        # Sort by position
        all_entities.sort(key=lambda x: x.get('start', 0))
        
        # Find entities that are close to each other
        for i, entity1 in enumerate(all_entities):
            for j, entity2 in enumerate(all_entities[i+1:], i+1):
                # Check if entities are within reasonable distance
                distance = entity2.get('start', 0) - entity1.get('end', 0)
                if distance < 100:  # 100 characters distance
                    # Extract text between entities
                    between_text = text[entity1.get('end', 0):entity2.get('start', 0)]
                    
                    # Simple relationship detection
                    relationship_type = self._determine_relationship_type(
                        entity1, entity2, between_text
                    )
                    
                    if relationship_type:
                        relationships.append({
                            'entity1': {
                                'text': entity1.get('text'),
                                'type': entity1.get('type'),
                                'start': entity1.get('start')
                            },
                            'entity2': {
                                'text': entity2.get('text'),
                                'type': entity2.get('type'),
                                'start': entity2.get('start')
                            },
                            'relationship': relationship_type,
                            'context': between_text.strip(),
                            'confidence': 0.6
                        })
        
        return {'relationships': relationships}
    
    def _determine_relationship_type(self, entity1: Dict, entity2: Dict, between_text: str) -> Optional[str]:
        """Determine relationship type between two entities"""
        
        entity1_type = entity1.get('type', '')
        entity2_type = entity2.get('type', '')
        between_text = between_text.lower().strip()
        
        # Common relationship patterns
        if 'works at' in between_text or 'employed by' in between_text:
            if entity1_type == 'PERSON' and entity2_type == 'ORG':
                return 'EMPLOYED_BY'
        
        elif 'located in' in between_text or 'in' in between_text:
            if entity1_type == 'ORG' and entity2_type in ['GPE', 'LOCATION']:
                return 'LOCATED_IN'
        
        elif 'paid' in between_text or 'owes' in between_text:
            if entity1_type == 'PERSON' and entity2_type == 'MONEY':
                return 'OWES_AMOUNT'
        
        elif 'due' in between_text:
            if entity1_type == 'MONEY' and entity2_type == 'DATE':
                return 'DUE_ON'
        
        elif 'born' in between_text or 'graduated' in between_text:
            if entity1_type == 'PERSON' and entity2_type == 'DATE':
                return 'OCCURRED_ON'
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        
        try:
            return dateparser.parse(date_str)
        except:
            return None
    
    def _parse_money_amount(self, money_str: str) -> Optional[float]:
        """Parse money string to float amount"""
        
        try:
            # Remove currency symbols and commas
            amount_str = re.sub(r'[^\d\.]', '', money_str)
            return float(amount_str)
        except:
            return None
    
    def _format_phone_number(self, phone_str: str) -> str:
        """Format phone number consistently"""
        
        # Extract digits only
        digits = re.sub(r'\D', '', phone_str)
        
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone_str
    
    def _calculate_entity_statistics(self, entities: Dict) -> Dict:
        """Calculate statistics about extracted entities"""
        
        stats = {
            'total_entities': 0,
            'entity_types': {},
            'extraction_methods': {},
            'confidence_distribution': {
                'high': 0,    # > 0.8
                'medium': 0,  # 0.5 - 0.8
                'low': 0      # < 0.5
            }
        }
        
        for entity_type, entity_list in entities.items():
            stats['entity_types'][entity_type] = len(entity_list)
            stats['total_entities'] += len(entity_list)
            
            for entity in entity_list:
                # Count extraction methods
                method = entity.get('method', 'unknown')
                if method not in stats['extraction_methods']:
                    stats['extraction_methods'][method] = 0
                stats['extraction_methods'][method] += 1
                
                # Count confidence distribution
                confidence = entity.get('confidence', 0)
                if confidence > 0.8:
                    stats['confidence_distribution']['high'] += 1
                elif confidence > 0.5:
                    stats['confidence_distribution']['medium'] += 1
                else:
                    stats['confidence_distribution']['low'] += 1
        
        return stats
    
    def _save_ner_results(self, results: Dict):
        """Save NER results to file"""
        
        try:
            output_file = os.path.join(
                self.output_dir,
                f"ner_results_{results['session_id']}.json"
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"NER results saved to {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save NER results: {str(e)}")

def main():
    """Command line interface for NER extraction"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract named entities from text')
    parser.add_argument('text', help='Text to process or file path')
    parser.add_argument('--output-dir', default='./output/entities', help='Output directory')
    parser.add_argument('--document-type', help='Document type for specialized extraction')
    parser.add_argument('--extract-relationships', action='store_true', help='Extract entity relationships')
    parser.add_argument('--file', action='store_true', help='Input is a file path')
    parser.add_argument('--confidence-threshold', type=float, default=0.8, help='Confidence threshold')
    
    args = parser.parse_args()
    
    # Configure NER extractor
    config = {
        'output_dir': args.output_dir,
        'confidence_threshold': args.confidence_threshold
    }
    
    options = {
        'document_type': args.document_type,
        'extract_relationships': args.extract_relationships
    }
    
    # Get text
    if args.file:
        with open(args.text, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = args.text
    
    # Extract entities
    extractor = NERExtractor(config)
    result = extractor.extract_entities(text, options)
    
    # Print results
    if 'entities' in result:
        print(f"✓ Entity extraction completed")
        print(f"  Session ID: {result['session_id']}")
        print(f"  Total entities: {result['statistics']['total_entities']}")
        print(f"  Entity types:")
        
        for entity_type, count in result['statistics']['entity_types'].items():
            print(f"    {entity_type}: {count}")
        
        print(f"  Extraction methods:")
        for method, count in result['statistics']['extraction_methods'].items():
            print(f"    {method}: {count}")
        
        if result.get('relationships'):
            rel_count = len(result['relationships']['relationships'])
            print(f"  Relationships found: {rel_count}")
    else:
        print(f"✗ Entity extraction failed: {result.get('error', 'Unknown error')}")

if __name__ == '__main__':
    main()