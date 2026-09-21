"""
Named Entity Recognition (NER) processor for extracting structured information
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import dateutil.parser
import phonenumbers
from email_validator import validate_email, EmailNotValidError

# NLP libraries
try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from ..core.config import settings, LANGUAGE_CONFIGS
from ..core.database import DatabaseManager
from ..models.document_models import NamedEntity, EntityType

nlp_logger = logging.getLogger('nlp')

class NERProcessor:
    """Named Entity Recognition processor with multiple approaches"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # NER models
        self.spacy_models = {}
        self.transformer_ner = None
        self.rule_based_ner = RuleBasedNER()
        
        # Initialize models
        asyncio.create_task(self._initialize_models())
    
    async def _initialize_models(self):
        """Initialize NER models in background"""
        try:
            # Initialize spaCy models for supported languages
            if SPACY_AVAILABLE:
                await self._load_spacy_models()
            
            # Initialize transformer-based NER
            if TRANSFORMERS_AVAILABLE:
                await self._load_transformer_ner()
            
            nlp_logger.info("NER processors initialized")
            
        except Exception as e:
            nlp_logger.warning(f"Failed to initialize some NER models: {str(e)}")
    
    async def _load_spacy_models(self):
        """Load spaCy models for different languages"""
        
        loop = asyncio.get_event_loop()
        
        # Load models for configured languages
        for lang_code, lang_config in LANGUAGE_CONFIGS.items():
            model_name = lang_config.get('spacy_model')
            if model_name:
                try:
                    model = await loop.run_in_executor(
                        None, spacy.load, model_name
                    )
                    self.spacy_models[lang_code] = model
                    nlp_logger.info(f"Loaded spaCy model for {lang_code}: {model_name}")
                except OSError:
                    nlp_logger.warning(f"spaCy model not found: {model_name}")
                except Exception as e:
                    nlp_logger.warning(f"Failed to load spaCy model {model_name}: {str(e)}")
        
        # Fallback to English if no models loaded
        if not self.spacy_models:
            try:
                model = await loop.run_in_executor(None, spacy.load, "en_core_web_sm")
                self.spacy_models['en'] = model
                nlp_logger.info("Loaded fallback English spaCy model")
            except Exception as e:
                nlp_logger.warning(f"Failed to load fallback spaCy model: {str(e)}")
    
    async def _load_transformer_ner(self):
        """Load transformer-based NER model"""
        
        try:
            loop = asyncio.get_event_loop()
            
            # Load pre-trained NER model
            self.transformer_ner = await loop.run_in_executor(
                None, 
                pipeline,
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple"
            )
            nlp_logger.info("Loaded transformer NER model")
            
        except Exception as e:
            nlp_logger.warning(f"Failed to load transformer NER: {str(e)}")
    
    async def extract_entities(self, job_id: str, text_content: str, 
                             page_texts: List[Dict] = None,
                             language: str = 'en') -> List[NamedEntity]:
        """
        Extract named entities from document text
        
        Args:
            job_id: Processing job ID
            text_content: Full document text
            page_texts: List of page-wise text data
            language: Primary language of the document
            
        Returns:
            List of extracted named entities
        """
        try:
            nlp_logger.info(f"Starting NER processing for job {job_id}")
            
            # Extract entities using different methods
            all_entities = []
            
            # Rule-based extraction
            rule_entities = await self._extract_with_rules(text_content, page_texts)
            all_entities.extend(rule_entities)
            
            # spaCy-based extraction
            if language in self.spacy_models:
                spacy_entities = await self._extract_with_spacy(
                    text_content, language, page_texts
                )
                all_entities.extend(spacy_entities)
            
            # Transformer-based extraction
            if self.transformer_ner:
                transformer_entities = await self._extract_with_transformer(
                    text_content, page_texts
                )
                all_entities.extend(transformer_entities)
            
            # Deduplicate and merge entities
            merged_entities = self._merge_entities(all_entities)
            
            # Save entities to database
            saved_entities = []
            for entity_data in merged_entities:
                entity_id = await self.db_manager.save_named_entity(
                    job_id=job_id,
                    entity_text=entity_data['text'],
                    entity_type=entity_data['label'],
                    start_pos=entity_data.get('start'),
                    end_pos=entity_data.get('end'),
                    confidence=entity_data.get('confidence'),
                    page_number=entity_data.get('page_number'),
                    context=entity_data.get('context'),
                    normalized_value=entity_data.get('normalized_value')
                )
                
                entity = NamedEntity(
                    entity_id=entity_id,
                    job_id=job_id,
                    entity_text=entity_data['text'],
                    entity_type=EntityType(entity_data['label']),
                    start_position=entity_data.get('start'),
                    end_position=entity_data.get('end'),
                    confidence_score=entity_data.get('confidence'),
                    page_number=entity_data.get('page_number'),
                    context_text=entity_data.get('context'),
                    normalized_value=entity_data.get('normalized_value'),
                    created_at=datetime.utcnow()
                )
                saved_entities.append(entity)
            
            nlp_logger.info(f"NER processing completed for job {job_id}: {len(saved_entities)} entities")
            return saved_entities
            
        except Exception as e:
            nlp_logger.error(f"NER processing failed for job {job_id}: {str(e)}")
            raise
    
    async def _extract_with_rules(self, text: str, page_texts: List[Dict] = None) -> List[Dict]:
        """Extract entities using rule-based patterns"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.rule_based_ner.extract_entities, text, page_texts
        )
    
    async def _extract_with_spacy(self, text: str, language: str, 
                                page_texts: List[Dict] = None) -> List[Dict]:
        """Extract entities using spaCy NER"""
        
        if language not in self.spacy_models:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._spacy_extract_sync, text, language, page_texts
        )
    
    def _spacy_extract_sync(self, text: str, language: str, 
                          page_texts: List[Dict] = None) -> List[Dict]:
        """Synchronous spaCy entity extraction"""
        
        try:
            nlp = self.spacy_models[language]
            
            # Process text in chunks to avoid memory issues
            max_length = 1000000  # 1MB limit for spaCy
            entities = []
            
            if len(text) <= max_length:
                doc = nlp(text)
                entities.extend(self._extract_spacy_entities(doc, 0))
            else:
                # Process in chunks
                chunk_size = max_length // 2
                overlap = 1000  # Overlap to catch entities at chunk boundaries
                
                for start in range(0, len(text), chunk_size - overlap):
                    end = min(start + chunk_size, len(text))
                    chunk = text[start:end]
                    
                    doc = nlp(chunk)
                    chunk_entities = self._extract_spacy_entities(doc, start)
                    entities.extend(chunk_entities)
            
            return entities
            
        except Exception as e:
            nlp_logger.warning(f"spaCy NER extraction failed: {str(e)}")
            return []
    
    def _extract_spacy_entities(self, doc, text_offset: int = 0) -> List[Dict]:
        """Extract entities from spaCy doc object"""
        
        entities = []
        
        for ent in doc.ents:
            # Map spaCy labels to our EntityType enum
            entity_type = self._map_spacy_label(ent.label_)
            if entity_type:
                # Get context (surrounding text)
                context_start = max(0, ent.start - 5)
                context_end = min(len(doc), ent.end + 5)
                context = doc[context_start:context_end].text
                
                # Normalize entity value
                normalized_value = self._normalize_entity_value(ent.text, entity_type)
                
                entities.append({
                    'text': ent.text,
                    'label': entity_type.value,
                    'start': ent.start_char + text_offset,
                    'end': ent.end_char + text_offset,
                    'confidence': 0.8,  # spaCy doesn't provide confidence scores
                    'source': 'spacy',
                    'context': context,
                    'normalized_value': normalized_value
                })
        
        return entities
    
    def _map_spacy_label(self, spacy_label: str) -> Optional[EntityType]:
        """Map spaCy entity labels to our EntityType enum"""
        
        mapping = {
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'GPE': EntityType.LOCATION,  # Geopolitical entity
            'LOC': EntityType.LOCATION,
            'DATE': EntityType.DATE,
            'TIME': EntityType.TIME,
            'MONEY': EntityType.MONEY,
            'PERCENT': EntityType.PERCENT,
            'CARDINAL': EntityType.CARDINAL,
            'ORDINAL': EntityType.ORDINAL,
        }
        
        return mapping.get(spacy_label)
    
    async def _extract_with_transformer(self, text: str, 
                                      page_texts: List[Dict] = None) -> List[Dict]:
        """Extract entities using transformer model"""
        
        if not self.transformer_ner:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._transformer_extract_sync, text
        )
    
    def _transformer_extract_sync(self, text: str) -> List[Dict]:
        """Synchronous transformer entity extraction"""
        
        try:
            # Process text in chunks due to token limits
            max_tokens = 512
            chunks = self._chunk_text_for_transformer(text, max_tokens)
            
            all_entities = []
            
            for chunk_start, chunk_text in chunks:
                try:
                    results = self.transformer_ner(chunk_text)
                    
                    for result in results:
                        # Map transformer labels to our EntityType
                        entity_type = self._map_transformer_label(result['entity_group'])
                        if entity_type:
                            all_entities.append({
                                'text': result['word'],
                                'label': entity_type.value,
                                'start': result['start'] + chunk_start,
                                'end': result['end'] + chunk_start,
                                'confidence': result['score'],
                                'source': 'transformer',
                                'normalized_value': self._normalize_entity_value(
                                    result['word'], entity_type
                                )
                            })
                
                except Exception as e:
                    nlp_logger.warning(f"Transformer NER failed for chunk: {str(e)}")
                    continue
            
            return all_entities
            
        except Exception as e:
            nlp_logger.warning(f"Transformer NER extraction failed: {str(e)}")
            return []
    
    def _chunk_text_for_transformer(self, text: str, max_tokens: int) -> List[Tuple[int, str]]:
        """Split text into chunks suitable for transformer processing"""
        
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        chunks = []
        
        if len(text) <= max_chars:
            return [(0, text)]
        
        # Split by sentences/paragraphs when possible
        sentences = re.split(r'[.!?]\s+', text)
        
        current_chunk = ""
        current_start = 0
        
        for sentence in sentences:
            if len(current_chunk + sentence) <= max_chars:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append((current_start, current_chunk.strip()))
                    current_start += len(current_chunk)
                
                # If single sentence is too long, split it
                if len(sentence) > max_chars:
                    for i in range(0, len(sentence), max_chars):
                        chunk = sentence[i:i + max_chars]
                        chunks.append((current_start + i, chunk))
                    current_start += len(sentence)
                    current_chunk = ""
                else:
                    current_chunk = sentence + ". "
        
        # Add final chunk
        if current_chunk:
            chunks.append((current_start, current_chunk.strip()))
        
        return chunks
    
    def _map_transformer_label(self, transformer_label: str) -> Optional[EntityType]:
        """Map transformer entity labels to our EntityType enum"""
        
        # Common BERT NER labels
        mapping = {
            'PER': EntityType.PERSON,
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'LOC': EntityType.LOCATION,
            'MISC': EntityType.CARDINAL,  # Miscellaneous -> Cardinal as fallback
        }
        
        return mapping.get(transformer_label)
    
    def _merge_entities(self, entities: List[Dict]) -> List[Dict]:
        """Merge and deduplicate entities from different sources"""
        
        if not entities:
            return []
        
        # Group entities by text and type
        entity_groups = {}
        
        for entity in entities:
            key = (entity['text'].lower().strip(), entity['label'])
            
            if key not in entity_groups:
                entity_groups[key] = []
            
            entity_groups[key].append(entity)
        
        # Merge entities in each group
        merged_entities = []
        
        for (text, label), group in entity_groups.items():
            # Sort by confidence (highest first)
            group.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Use the highest confidence entity as base
            best_entity = group[0].copy()
            
            # Collect sources
            sources = list(set(entity.get('source', 'unknown') for entity in group))
            best_entity['sources'] = sources
            
            # Average confidence if multiple sources
            if len(group) > 1:
                avg_confidence = sum(e.get('confidence', 0) for e in group) / len(group)
                best_entity['confidence'] = avg_confidence
            
            merged_entities.append(best_entity)
        
        # Sort by confidence
        merged_entities.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        return merged_entities
    
    def _normalize_entity_value(self, text: str, entity_type: EntityType) -> Optional[str]:
        """Normalize entity values for better matching and storage"""
        
        try:
            if entity_type == EntityType.DATE:
                return self._normalize_date(text)
            elif entity_type == EntityType.MONEY:
                return self._normalize_money(text)
            elif entity_type == EntityType.PERCENT:
                return self._normalize_percent(text)
            elif entity_type == EntityType.PHONE:
                return self._normalize_phone(text)
            elif entity_type == EntityType.EMAIL:
                return self._normalize_email(text)
            elif entity_type in [EntityType.PERSON, EntityType.ORGANIZATION]:
                return self._normalize_name(text)
            else:
                return text.strip()
        
        except Exception:
            return text.strip()
    
    def _normalize_date(self, text: str) -> str:
        """Normalize date strings to ISO format"""
        try:
            parsed_date = dateutil.parser.parse(text, fuzzy=True)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return text
    
    def _normalize_money(self, text: str) -> str:
        """Normalize monetary amounts"""
        # Extract numeric value and currency
        money_pattern = r'[\$£€¥]?([\d,]+\.?\d*)'
        match = re.search(money_pattern, text)
        if match:
            amount = match.group(1).replace(',', '')
            try:
                return f"{float(amount):.2f}"
            except:
                return text
        return text
    
    def _normalize_percent(self, text: str) -> str:
        """Normalize percentage values"""
        percent_pattern = r'([\d.]+)%?'
        match = re.search(percent_pattern, text)
        if match:
            try:
                return f"{float(match.group(1)):.2f}%"
            except:
                return text
        return text
    
    def _normalize_phone(self, text: str) -> str:
        """Normalize phone numbers"""
        try:
            parsed = phonenumbers.parse(text, None)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            pass
        return text
    
    def _normalize_email(self, text: str) -> str:
        """Normalize email addresses"""
        try:
            validated_email = validate_email(text)
            return validated_email.email.lower()
        except EmailNotValidError:
            return text
    
    def _normalize_name(self, text: str) -> str:
        """Normalize person and organization names"""
        # Basic normalization: title case and clean whitespace
        return re.sub(r'\s+', ' ', text.strip().title())


class RuleBasedNER:
    """Rule-based named entity recognition using regex patterns"""
    
    def __init__(self):
        # Compile regex patterns for different entity types
        self.patterns = {
            EntityType.EMAIL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            EntityType.PHONE: [
                r'\b(?:\+1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
                r'\b\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b'
            ],
            EntityType.MONEY: [
                r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
                r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|usd)\b',
                r'£\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
                r'€\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
            ],
            EntityType.PERCENT: [
                r'\b\d{1,3}(?:\.\d{1,2})?%',
                r'\b\d{1,3}(?:\.\d{1,2})?\s*percent\b'
            ],
            EntityType.DATE: [
                r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b',
                r'\b\d{4}[/.-]\d{1,2}[/.-]\d{1,2}\b',
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'
            ],
            EntityType.TIME: [
                r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)\b',
                r'\b\d{1,2}:\d{2}(?::\d{2})?\b'
            ],
            EntityType.URL: [
                r'https?://[^\s]+',
                r'www\.[^\s]+\.[a-z]{2,}'
            ]
        }
        
        # Compile patterns
        self.compiled_patterns = {}
        for entity_type, patterns in self.patterns.items():
            self.compiled_patterns[entity_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def extract_entities(self, text: str, page_texts: List[Dict] = None) -> List[Dict]:
        """Extract entities using rule-based patterns"""
        
        entities = []
        
        for entity_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity_text = match.group(0)
                    
                    # Get context
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text), match.end() + 50)
                    context = text[start_pos:end_pos]
                    
                    # Normalize value
                    normalized_value = self._normalize_by_type(entity_text, entity_type)
                    
                    entities.append({
                        'text': entity_text,
                        'label': entity_type.value,
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.9,  # High confidence for rule-based matches
                        'source': 'rules',
                        'context': context,
                        'normalized_value': normalized_value
                    })
        
        return entities
    
    def _normalize_by_type(self, text: str, entity_type: EntityType) -> str:
        """Simple normalization based on entity type"""
        
        if entity_type == EntityType.EMAIL:
            return text.lower().strip()
        elif entity_type == EntityType.PHONE:
            # Remove common formatting
            return re.sub(r'[^\d+]', '', text)
        elif entity_type == EntityType.MONEY:
            # Extract just the numeric part
            numeric = re.sub(r'[^\d.]', '', text)
            try:
                return f"{float(numeric):.2f}"
            except:
                return text
        elif entity_type == EntityType.PERCENT:
            # Extract numeric part
            numeric = re.sub(r'[^\d.]', '', text)
            try:
                return f"{float(numeric):.2f}%"
            except:
                return text
        else:
            return text.strip()