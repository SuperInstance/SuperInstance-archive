#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Natural Language Query Parser
Advanced NLP for parsing natural language search queries
"""

import re
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime, timedelta
import calendar

logger = logging.getLogger(__name__)

@dataclass
class ParsedQuery:
    """Parsed natural language query"""
    original_query: str
    processed_query: str
    intent: str
    entities: Dict[str, List[str]]
    filters: Dict[str, Any]
    temporal_info: Dict[str, Any]
    confidence: float
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []

@dataclass
class Entity:
    """Named entity in query"""
    text: str
    type: str  # person, organization, location, date, etc.
    start_pos: int
    end_pos: int
    confidence: float = 1.0

class TemporalParser:
    """Parse temporal expressions in queries"""
    
    def __init__(self):
        # Time patterns
        self.time_patterns = {
            # Relative time
            r'\b(?:today|this morning|this afternoon|this evening)\b': self._parse_today,
            r'\byesterday\b': self._parse_yesterday,
            r'\btomorrow\b': self._parse_tomorrow,
            r'\bthis week\b': self._parse_this_week,
            r'\blast week\b': self._parse_last_week,
            r'\bnext week\b': self._parse_next_week,
            r'\bthis month\b': self._parse_this_month,
            r'\blast month\b': self._parse_last_month,
            r'\bthis year\b': self._parse_this_year,
            r'\blast year\b': self._parse_last_year,
            
            # Specific dates
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b': self._parse_date_format,
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b': self._parse_iso_date,
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b': self._parse_month_day_year,
            
            # Relative periods
            r'\b(\d+)\s+(days?|weeks?|months?|years?)\s+ago\b': self._parse_relative_past,
            r'\bin\s+the\s+last\s+(\d+)\s+(days?|weeks?|months?|years?)\b': self._parse_last_period,
            r'\bsince\s+(\d{4})\b': self._parse_since_year,
            r'\bbefore\s+(\d{4})\b': self._parse_before_year,
            r'\bafter\s+(\d{4})\b': self._parse_after_year,
        }
    
    def parse_temporal_info(self, text: str) -> Dict[str, Any]:
        """Parse temporal information from text"""
        temporal_info = {}
        
        for pattern, parser in self.time_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    result = parser(match)
                    if result:
                        temporal_info.update(result)
                except Exception as e:
                    logger.warning(f"Temporal parsing error: {e}")
                    continue
        
        return temporal_info
    
    def _parse_today(self, match) -> Dict[str, Any]:
        """Parse 'today' references"""
        today = datetime.now().date()
        return {
            "date_from": today,
            "date_to": today,
            "temporal_type": "specific_day"
        }
    
    def _parse_yesterday(self, match) -> Dict[str, Any]:
        """Parse 'yesterday' references"""
        yesterday = (datetime.now() - timedelta(days=1)).date()
        return {
            "date_from": yesterday,
            "date_to": yesterday,
            "temporal_type": "specific_day"
        }
    
    def _parse_tomorrow(self, match) -> Dict[str, Any]:
        """Parse 'tomorrow' references"""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        return {
            "date_from": tomorrow,
            "date_to": tomorrow,
            "temporal_type": "specific_day"
        }
    
    def _parse_this_week(self, match) -> Dict[str, Any]:
        """Parse 'this week' references"""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        return {
            "date_from": start_of_week,
            "date_to": end_of_week,
            "temporal_type": "week"
        }
    
    def _parse_last_week(self, match) -> Dict[str, Any]:
        """Parse 'last week' references"""
        today = datetime.now().date()
        start_of_last_week = today - timedelta(days=today.weekday() + 7)
        end_of_last_week = start_of_last_week + timedelta(days=6)
        
        return {
            "date_from": start_of_last_week,
            "date_to": end_of_last_week,
            "temporal_type": "week"
        }
    
    def _parse_this_month(self, match) -> Dict[str, Any]:
        """Parse 'this month' references"""
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        _, last_day = calendar.monthrange(today.year, today.month)
        end_of_month = today.replace(day=last_day)
        
        return {
            "date_from": start_of_month,
            "date_to": end_of_month,
            "temporal_type": "month"
        }
    
    def _parse_last_month(self, match) -> Dict[str, Any]:
        """Parse 'last month' references"""
        today = datetime.now().date()
        if today.month == 1:
            last_month_year = today.year - 1
            last_month = 12
        else:
            last_month_year = today.year
            last_month = today.month - 1
        
        start_of_last_month = datetime(last_month_year, last_month, 1).date()
        _, last_day = calendar.monthrange(last_month_year, last_month)
        end_of_last_month = datetime(last_month_year, last_month, last_day).date()
        
        return {
            "date_from": start_of_last_month,
            "date_to": end_of_last_month,
            "temporal_type": "month"
        }
    
    def _parse_this_year(self, match) -> Dict[str, Any]:
        """Parse 'this year' references"""
        current_year = datetime.now().year
        start_of_year = datetime(current_year, 1, 1).date()
        end_of_year = datetime(current_year, 12, 31).date()
        
        return {
            "date_from": start_of_year,
            "date_to": end_of_year,
            "temporal_type": "year"
        }
    
    def _parse_last_year(self, match) -> Dict[str, Any]:
        """Parse 'last year' references"""
        last_year = datetime.now().year - 1
        start_of_last_year = datetime(last_year, 1, 1).date()
        end_of_last_year = datetime(last_year, 12, 31).date()
        
        return {
            "date_from": start_of_last_year,
            "date_to": end_of_last_year,
            "temporal_type": "year"
        }
    
    def _parse_date_format(self, match) -> Dict[str, Any]:
        """Parse MM/DD/YYYY format"""
        month, day, year = match.groups()
        try:
            date = datetime(int(year), int(month), int(day)).date()
            return {
                "date_from": date,
                "date_to": date,
                "temporal_type": "specific_date"
            }
        except ValueError:
            return {}
    
    def _parse_iso_date(self, match) -> Dict[str, Any]:
        """Parse YYYY-MM-DD format"""
        year, month, day = match.groups()
        try:
            date = datetime(int(year), int(month), int(day)).date()
            return {
                "date_from": date,
                "date_to": date,
                "temporal_type": "specific_date"
            }
        except ValueError:
            return {}
    
    def _parse_month_day_year(self, match) -> Dict[str, Any]:
        """Parse 'January 15, 2023' format"""
        month_name, day, year = match.groups()
        
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        month_num = months.get(month_name.lower())
        if month_num:
            try:
                date = datetime(int(year), month_num, int(day)).date()
                return {
                    "date_from": date,
                    "date_to": date,
                    "temporal_type": "specific_date"
                }
            except ValueError:
                return {}
        return {}
    
    def _parse_relative_past(self, match) -> Dict[str, Any]:
        """Parse 'X days/weeks/months/years ago'"""
        number, unit = match.groups()
        number = int(number)
        
        if 'day' in unit:
            days = number
        elif 'week' in unit:
            days = number * 7
        elif 'month' in unit:
            days = number * 30  # Approximate
        elif 'year' in unit:
            days = number * 365  # Approximate
        else:
            return {}
        
        target_date = (datetime.now() - timedelta(days=days)).date()
        
        return {
            "date_from": target_date,
            "date_to": target_date,
            "temporal_type": "relative_past"
        }
    
    def _parse_last_period(self, match) -> Dict[str, Any]:
        """Parse 'in the last X days/weeks/months/years'"""
        number, unit = match.groups()
        number = int(number)
        
        if 'day' in unit:
            days = number
        elif 'week' in unit:
            days = number * 7
        elif 'month' in unit:
            days = number * 30  # Approximate
        elif 'year' in unit:
            days = number * 365  # Approximate
        else:
            return {}
        
        start_date = (datetime.now() - timedelta(days=days)).date()
        end_date = datetime.now().date()
        
        return {
            "date_from": start_date,
            "date_to": end_date,
            "temporal_type": "period"
        }
    
    def _parse_since_year(self, match) -> Dict[str, Any]:
        """Parse 'since YYYY'"""
        year = int(match.group(1))
        start_date = datetime(year, 1, 1).date()
        end_date = datetime.now().date()
        
        return {
            "date_from": start_date,
            "date_to": end_date,
            "temporal_type": "since"
        }
    
    def _parse_before_year(self, match) -> Dict[str, Any]:
        """Parse 'before YYYY'"""
        year = int(match.group(1))
        end_date = datetime(year - 1, 12, 31).date()
        
        return {
            "date_to": end_date,
            "temporal_type": "before"
        }
    
    def _parse_after_year(self, match) -> Dict[str, Any]:
        """Parse 'after YYYY'"""
        year = int(match.group(1))
        start_date = datetime(year + 1, 1, 1).date()
        
        return {
            "date_from": start_date,
            "temporal_type": "after"
        }

class EntityExtractor:
    """Extract named entities from queries"""
    
    def __init__(self):
        # Simple patterns for entity recognition
        self.entity_patterns = {
            # Email addresses
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            
            # URLs
            'url': r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?',
            
            # File extensions
            'file_extension': r'\b\w+\.(pdf|doc|docx|txt|jpg|jpeg|png|gif|mp4|mp3|xlsx|ppt|zip)\b',
            
            # Service names (ActiveLog services)
            'service': r'\b(PersonalLog|BusinessLog|HealthLog|FinanceLog|TaskManager|NoteTaker|Calendar|Contacts)\b',
            
            # Content types
            'content_type': r'\b(document|image|audio|video|email|message|note|task|event|contact)\b',
            
            # User mentions
            'user_mention': r'@(\w+)',
            
            # Hashtags
            'hashtag': r'#(\w+)',
            
            # Numbers
            'number': r'\b\d+(?:\.\d+)?\b',
            
            # Quoted strings
            'quoted_string': r'"([^"]*)"',
        }
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                entity = Entity(
                    text=match.group(0),
                    type=entity_type,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9  # High confidence for regex patterns
                )
                entities.append(entity)
        
        return entities

class IntentClassifier:
    """Classify query intent"""
    
    def __init__(self):
        # Intent patterns
        self.intent_patterns = {
            'search': [
                r'\bfind\b', r'\bsearch\b', r'\blook for\b', r'\bwhere\b',
                r'\bshow me\b', r'\bget\b', r'\blist\b'
            ],
            'filter': [
                r'\bfrom\b', r'\bby\b', r'\btype:\w+\b', r'\btag:\w+\b',
                r'\bservice:\w+\b', r'\bwith\b', r'\bcontaining\b'
            ],
            'temporal': [
                r'\btoday\b', r'\byesterday\b', r'\blast week\b', r'\bthis month\b',
                r'\brecent\b', r'\bnew\b', r'\bold\b', r'\bsince\b', r'\bbefore\b'
            ],
            'aggregation': [
                r'\bcount\b', r'\bhow many\b', r'\btotal\b', r'\bsum\b',
                r'\baverage\b', r'\bmax\b', r'\bmin\b'
            ],
            'comparison': [
                r'\bcompare\b', r'\bvs\b', r'\bdifference\b', r'\bsimilar\b',
                r'\blike\b', r'\brelated\b'
            ],
            'export': [
                r'\bexport\b', r'\bdownload\b', r'\bsave as\b', r'\bgenerate report\b'
            ]
        }
    
    def classify_intent(self, query: str) -> Tuple[str, float]:
        """Classify query intent with confidence score"""
        intent_scores = defaultdict(float)
        
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, query_lower))
                if matches > 0:
                    intent_scores[intent] += matches * 0.5
        
        if not intent_scores:
            return 'search', 0.5  # Default intent
        
        # Get intent with highest score
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(intent_scores[best_intent], 1.0)
        
        return best_intent, confidence

class NaturalLanguageQueryParser:
    """Main natural language query parser"""
    
    def __init__(self):
        self.temporal_parser = TemporalParser()
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        
        # Query preprocessing patterns
        self.preprocessing_patterns = [
            # Remove common phrases
            (r'\bcan you\b', ''),
            (r'\bplease\b', ''),
            (r'\bi want to\b', ''),
            (r'\bi need to\b', ''),
            (r'\bhelp me\b', ''),
            
            # Normalize boolean operators
            (r'\band\b', 'AND'),
            (r'\bor\b', 'OR'),
            (r'\bnot\b', 'NOT'),
            
            # Normalize quotes
            (r'["""]', '"'),
        ]
        
        # Statistics
        self.stats = {
            "queries_parsed": 0,
            "avg_processing_time_ms": 0,
            "intent_distribution": defaultdict(int),
            "entities_extracted": defaultdict(int)
        }
    
    async def parse_query(self, query: str) -> ParsedQuery:
        """Parse natural language query"""
        start_time = time.time()
        
        try:
            # Preprocess query
            processed_query = self._preprocess_query(query)
            
            # Extract entities
            entities = self.entity_extractor.extract_entities(processed_query)
            
            # Parse temporal information
            temporal_info = self.temporal_parser.parse_temporal_info(processed_query)
            
            # Classify intent
            intent, confidence = self.intent_classifier.classify_intent(processed_query)
            
            # Extract filters from entities and patterns
            filters = self._extract_filters(entities, temporal_info)
            
            # Create entity dictionary
            entity_dict = defaultdict(list)
            for entity in entities:
                entity_dict[entity.type].append(entity.text)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(processed_query, intent, entities)
            
            # Create parsed query
            parsed_query = ParsedQuery(
                original_query=query,
                processed_query=processed_query,
                intent=intent,
                entities=dict(entity_dict),
                filters=filters,
                temporal_info=temporal_info,
                confidence=confidence,
                suggestions=suggestions
            )
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self.stats["queries_parsed"] += 1
            self.stats["intent_distribution"][intent] += 1
            
            for entity in entities:
                self.stats["entities_extracted"][entity.type] += 1
            
            # Update average processing time
            current_avg = self.stats["avg_processing_time_ms"]
            total_queries = self.stats["queries_parsed"]
            self.stats["avg_processing_time_ms"] = ((current_avg * (total_queries - 1)) + processing_time) / total_queries
            
            return parsed_query
            
        except Exception as e:
            logger.error(f"Query parsing error: {e}")
            
            # Return basic parsed query on error
            return ParsedQuery(
                original_query=query,
                processed_query=query,
                intent="search",
                entities={},
                filters={},
                temporal_info={},
                confidence=0.1
            )
    
    def _preprocess_query(self, query: str) -> str:
        """Preprocess query text"""
        processed = query.strip()
        
        # Apply preprocessing patterns
        for pattern, replacement in self.preprocessing_patterns:
            processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        processed = ' '.join(processed.split())
        
        return processed
    
    def _extract_filters(self, entities: List[Entity], temporal_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract search filters from entities and temporal info"""
        filters = {}
        
        # Add temporal filters
        if temporal_info:
            filters.update(temporal_info)
        
        # Add entity-based filters
        for entity in entities:
            if entity.type == 'service':
                filters.setdefault('services', []).append(entity.text)
            elif entity.type == 'content_type':
                filters.setdefault('content_types', []).append(entity.text)
            elif entity.type == 'file_extension':
                filters.setdefault('file_types', []).append(entity.text)
            elif entity.type == 'user_mention':
                # Remove @ symbol
                username = entity.text[1:] if entity.text.startswith('@') else entity.text
                filters.setdefault('users', []).append(username)
            elif entity.type == 'hashtag':
                # Remove # symbol
                tag = entity.text[1:] if entity.text.startswith('#') else entity.text
                filters.setdefault('tags', []).append(tag)
        
        return filters
    
    def _generate_suggestions(self, query: str, intent: str, entities: List[Entity]) -> List[str]:
        """Generate query suggestions"""
        suggestions = []
        
        # Intent-based suggestions
        if intent == 'search':
            suggestions.extend([
                f"Find recent {query}",
                f"Search for {query} in PersonalLog",
                f"Look for {query} today"
            ])
        elif intent == 'temporal':
            suggestions.extend([
                f"Show {query} from last week",
                f"Find {query} this month"
            ])
        
        # Entity-based suggestions
        service_entities = [e.text for e in entities if e.type == 'service']
        if service_entities:
            for service in service_entities[:2]:  # Limit suggestions
                suggestions.append(f"Search {query} in {service}")
        
        # Filter suggestions
        if not any(e.type == 'content_type' for e in entities):
            suggestions.extend([
                f"{query} type:document",
                f"{query} type:image",
                f"{query} type:email"
            ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            **self.stats,
            "intent_distribution": dict(self.stats["intent_distribution"]),
            "entities_extracted": dict(self.stats["entities_extracted"])
        }