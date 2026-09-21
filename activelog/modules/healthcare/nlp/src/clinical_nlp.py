"""
Clinical Notes NLP Processing Module
Natural language processing for clinical documentation and medical text analysis.
"""
import re
import datetime
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json


class NoteType(Enum):
    """Types of clinical notes"""
    PROGRESS_NOTE = "progress_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    HISTORY_PHYSICAL = "history_physical"
    CONSULTATION = "consultation"
    OPERATIVE_REPORT = "operative_report"
    RADIOLOGY_REPORT = "radiology_report"
    PATHOLOGY_REPORT = "pathology_report"
    NURSING_NOTE = "nursing_note"
    EMERGENCY_NOTE = "emergency_note"


class EntityType(Enum):
    """Types of medical entities"""
    MEDICATION = "medication"
    DOSAGE = "dosage"
    CONDITION = "condition"
    SYMPTOM = "symptom"
    PROCEDURE = "procedure"
    ANATOMY = "anatomy"
    LAB_VALUE = "lab_value"
    VITAL_SIGN = "vital_sign"
    DATE = "date"
    PERSON = "person"
    ORGANIZATION = "organization"


class Sentiment(Enum):
    """Sentiment analysis results"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNCERTAIN = "uncertain"


@dataclass
class MedicalEntity:
    """Medical entity extracted from text"""
    text: str
    entity_type: EntityType
    start_pos: int
    end_pos: int
    confidence: float
    normalized_form: Optional[str] = None
    concept_id: Optional[str] = None  # UMLS CUI or similar
    attributes: Optional[Dict[str, Any]] = None


@dataclass
class ClinicalConcept:
    """Clinical concept with relationships"""
    concept_id: str
    preferred_term: str
    synonyms: List[str]
    semantic_type: str
    definition: Optional[str] = None
    relationships: Optional[Dict[str, List[str]]] = None


@dataclass
class NLPResult:
    """Complete NLP analysis result"""
    text: str
    entities: List[MedicalEntity]
    concepts: List[ClinicalConcept]
    sentiment: Sentiment
    confidence_score: float
    processed_at: datetime.datetime
    metadata: Optional[Dict[str, Any]] = None


class MedicalTerminologyMatcher:
    """Matches medical terms to standardized vocabularies"""
    
    def __init__(self):
        # Simplified medical terminology - in production would use UMLS, SNOMED, etc.
        self.medications = {
            'aspirin': {'cui': 'C0004057', 'preferred': 'Aspirin'},
            'ibuprofen': {'cui': 'C0020740', 'preferred': 'Ibuprofen'},
            'acetaminophen': {'cui': 'C0000970', 'preferred': 'Acetaminophen'},
            'paracetamol': {'cui': 'C0000970', 'preferred': 'Acetaminophen'},
            'tylenol': {'cui': 'C0000970', 'preferred': 'Acetaminophen'},
            'metformin': {'cui': 'C0025598', 'preferred': 'Metformin'},
            'insulin': {'cui': 'C0021641', 'preferred': 'Insulin'},
            'lisinopril': {'cui': 'C0065374', 'preferred': 'Lisinopril'},
            'atorvastatin': {'cui': 'C0286651', 'preferred': 'Atorvastatin'},
            'lipitor': {'cui': 'C0286651', 'preferred': 'Atorvastatin'}
        }
        
        self.conditions = {
            'diabetes': {'cui': 'C0011847', 'preferred': 'Diabetes Mellitus'},
            'hypertension': {'cui': 'C0020538', 'preferred': 'Hypertension'},
            'high blood pressure': {'cui': 'C0020538', 'preferred': 'Hypertension'},
            'heart disease': {'cui': 'C0018799', 'preferred': 'Heart Disease'},
            'pneumonia': {'cui': 'C0032285', 'preferred': 'Pneumonia'},
            'asthma': {'cui': 'C0004096', 'preferred': 'Asthma'},
            'copd': {'cui': 'C0024117', 'preferred': 'Chronic Obstructive Pulmonary Disease'},
            'depression': {'cui': 'C0011570', 'preferred': 'Depression'},
            'anxiety': {'cui': 'C0003467', 'preferred': 'Anxiety'},
            'migraine': {'cui': 'C0149931', 'preferred': 'Migraine'},
            'arthritis': {'cui': 'C0003864', 'preferred': 'Arthritis'}
        }
        
        self.procedures = {
            'surgery': {'cui': 'C0543467', 'preferred': 'Surgery'},
            'biopsy': {'cui': 'C0005558', 'preferred': 'Biopsy'},
            'x-ray': {'cui': 'C0034571', 'preferred': 'Radiography'},
            'ct scan': {'cui': 'C0040405', 'preferred': 'Computed Tomography'},
            'mri': {'cui': 'C0024485', 'preferred': 'Magnetic Resonance Imaging'},
            'endoscopy': {'cui': 'C0014245', 'preferred': 'Endoscopy'},
            'colonoscopy': {'cui': 'C0009378', 'preferred': 'Colonoscopy'},
            'ecg': {'cui': 'C1623258', 'preferred': 'Electrocardiography'},
            'ekg': {'cui': 'C1623258', 'preferred': 'Electrocardiography'},
            'blood test': {'cui': 'C0018941', 'preferred': 'Blood Test'}
        }
        
        self.vital_signs = {
            'blood pressure': {'cui': 'C0005823', 'preferred': 'Blood Pressure'},
            'heart rate': {'cui': 'C0018810', 'preferred': 'Heart Rate'},
            'pulse': {'cui': 'C0391850', 'preferred': 'Pulse'},
            'temperature': {'cui': 'C0005903', 'preferred': 'Body Temperature'},
            'weight': {'cui': 'C0005910', 'preferred': 'Body Weight'},
            'oxygen saturation': {'cui': 'C0523807', 'preferred': 'Oxygen Saturation'},
            'respiratory rate': {'cui': 'C0231832', 'preferred': 'Respiratory Rate'}
        }
    
    def match_term(self, term: str) -> Optional[Dict[str, str]]:
        """Match a term to medical vocabulary"""
        term_lower = term.lower().strip()
        
        # Check medications
        if term_lower in self.medications:
            return {**self.medications[term_lower], 'semantic_type': 'medication'}
        
        # Check conditions
        if term_lower in self.conditions:
            return {**self.conditions[term_lower], 'semantic_type': 'condition'}
        
        # Check procedures
        if term_lower in self.procedures:
            return {**self.procedures[term_lower], 'semantic_type': 'procedure'}
        
        # Check vital signs
        if term_lower in self.vital_signs:
            return {**self.vital_signs[term_lower], 'semantic_type': 'vital_sign'}
        
        return None


class ClinicalEntityExtractor:
    """Extract medical entities from clinical text"""
    
    def __init__(self):
        self.terminology_matcher = MedicalTerminologyMatcher()
        
        # Regex patterns for different entity types
        self.patterns = {
            EntityType.MEDICATION: [
                r'\b(?:aspirin|ibuprofen|acetaminophen|paracetamol|tylenol|metformin|insulin|lisinopril|atorvastatin|lipitor)\b',
                r'\b\w+(?:mycin|cillin|pril|statin|olol)\b',  # Common drug suffixes
                r'\b\d+\s*mg\s+\w+\b',  # Dosage with medication
            ],
            EntityType.CONDITION: [
                r'\b(?:diabetes|hypertension|pneumonia|asthma|copd|depression|anxiety|migraine|arthritis)\b',
                r'\bhigh blood pressure\b',
                r'\bheart disease\b',
                r'\b\w+(?:itis|osis|pathy|emia)\b',  # Common condition suffixes
            ],
            EntityType.PROCEDURE: [
                r'\b(?:surgery|biopsy|x-ray|ct scan|mri|endoscopy|colonoscopy|ecg|ekg|blood test)\b',
                r'\b\w+(?:scopy|graphy|tomy|ectomy)\b',  # Common procedure suffixes
            ],
            EntityType.VITAL_SIGN: [
                r'\b(?:blood pressure|heart rate|pulse|temperature|weight|oxygen saturation|respiratory rate)\b',
                r'\b(?:bp|hr|temp|wt|o2 sat|rr)\b',  # Abbreviations
            ],
            EntityType.LAB_VALUE: [
                r'\b(?:glucose|cholesterol|hemoglobin|hematocrit|creatinine|bun|sodium|potassium)\b',
                r'\b\d+\.?\d*\s*(?:mg/dl|mmol/l|g/dl|%|mEq/l)\b',  # Lab values with units
            ],
            EntityType.DOSAGE: [
                r'\b\d+\.?\d*\s*(?:mg|g|ml|units?|tablets?|capsules?)\b',
                r'\b(?:once|twice|three times?|four times?)\s+(?:daily|per day|a day)\b',
                r'\bq\d+h\b',  # Every X hours
            ],
            EntityType.DATE: [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b(?:today|yesterday|tomorrow)\b',
                r'\b\d{1,2}\s+(?:days?|weeks?|months?|years?)\s+ago\b',
            ]
        }
    
    def extract_entities(self, text: str) -> List[MedicalEntity]:
        """Extract medical entities from text"""
        entities = []
        text_lower = text.lower()
        
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                
                for match in matches:
                    matched_text = match.group()
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # Get original case text
                    original_text = text[start_pos:end_pos]
                    
                    # Try to match to terminology
                    term_info = self.terminology_matcher.match_term(matched_text)
                    
                    entity = MedicalEntity(
                        text=original_text,
                        entity_type=entity_type,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        confidence=0.8,  # Base confidence
                        normalized_form=term_info['preferred'] if term_info else None,
                        concept_id=term_info['cui'] if term_info else None
                    )
                    
                    # Adjust confidence based on terminology match
                    if term_info:
                        entity.confidence = 0.95
                    
                    entities.append(entity)
        
        # Remove overlapping entities (keep highest confidence)
        entities = self._remove_overlapping_entities(entities)
        
        return entities
    
    def _remove_overlapping_entities(self, entities: List[MedicalEntity]) -> List[MedicalEntity]:
        """Remove overlapping entities, keeping the one with highest confidence"""
        if not entities:
            return entities
        
        # Sort by start position
        entities.sort(key=lambda e: e.start_pos)
        
        filtered_entities = []
        
        for entity in entities:
            # Check if this entity overlaps with any already added entity
            overlaps = False
            
            for existing in filtered_entities:
                if (entity.start_pos < existing.end_pos and 
                    entity.end_pos > existing.start_pos):
                    # There's overlap - keep the one with higher confidence
                    if entity.confidence > existing.confidence:
                        filtered_entities.remove(existing)
                    else:
                        overlaps = True
                    break
            
            if not overlaps:
                filtered_entities.append(entity)
        
        return filtered_entities


class ClinicalSentimentAnalyzer:
    """Analyze sentiment and uncertainty in clinical text"""
    
    def __init__(self):
        self.positive_indicators = {
            'improved', 'better', 'stable', 'normal', 'good', 'excellent',
            'resolved', 'healing', 'recovered', 'responding', 'effective'
        }
        
        self.negative_indicators = {
            'worse', 'deteriorated', 'severe', 'acute', 'chronic', 'pain',
            'infected', 'abnormal', 'concerning', 'critical', 'failed'
        }
        
        self.uncertainty_indicators = {
            'possible', 'probable', 'likely', 'suggest', 'consider',
            'rule out', 'differential', 'uncertain', 'unclear', 'maybe'
        }
        
        self.negation_patterns = [
            r'\b(?:no|not|never|without|absence of|denies)\s+\w*\s*',
            r'\bnon-\w+',
            r'\bun\w+',
        ]
    
    def analyze_sentiment(self, text: str, entities: List[MedicalEntity]) -> Tuple[Sentiment, float]:
        """Analyze sentiment of clinical text"""
        text_lower = text.lower()
        
        # Check for uncertainty indicators
        uncertainty_score = sum(1 for indicator in self.uncertainty_indicators 
                              if indicator in text_lower)
        
        if uncertainty_score > 0:
            return Sentiment.UNCERTAIN, min(0.7 + uncertainty_score * 0.1, 0.95)
        
        # Count positive and negative indicators
        positive_score = sum(1 for indicator in self.positive_indicators 
                           if indicator in text_lower)
        negative_score = sum(1 for indicator in self.negative_indicators 
                           if indicator in text_lower)
        
        # Check for negation patterns
        negation_score = sum(1 for pattern in self.negation_patterns 
                           if re.search(pattern, text_lower))
        
        # Adjust scores based on negation
        if negation_score > 0:
            # Negation can flip sentiment
            positive_score, negative_score = negative_score, positive_score
        
        # Determine overall sentiment
        if positive_score > negative_score:
            confidence = min(0.6 + (positive_score - negative_score) * 0.1, 0.9)
            return Sentiment.POSITIVE, confidence
        elif negative_score > positive_score:
            confidence = min(0.6 + (negative_score - positive_score) * 0.1, 0.9)
            return Sentiment.NEGATIVE, confidence
        else:
            return Sentiment.NEUTRAL, 0.5


class ClinicalNLPProcessor:
    """Main clinical NLP processing pipeline"""
    
    def __init__(self):
        self.entity_extractor = ClinicalEntityExtractor()
        self.sentiment_analyzer = ClinicalSentimentAnalyzer()
        self.processing_stats = {
            'documents_processed': 0,
            'entities_extracted': 0,
            'last_processed': None
        }
    
    def process_clinical_note(self, text: str, note_type: NoteType = NoteType.PROGRESS_NOTE,
                            patient_id: Optional[str] = None) -> NLPResult:
        """Process a clinical note with full NLP analysis"""
        try:
            # Extract entities
            entities = self.entity_extractor.extract_entities(text)
            
            # Analyze sentiment
            sentiment, sentiment_confidence = self.sentiment_analyzer.analyze_sentiment(text, entities)
            
            # Extract clinical concepts
            concepts = self._extract_clinical_concepts(entities)
            
            # Calculate overall confidence
            entity_confidences = [e.confidence for e in entities] if entities else [0.5]
            overall_confidence = (sum(entity_confidences) / len(entity_confidences) + sentiment_confidence) / 2
            
            # Create result
            result = NLPResult(
                text=text,
                entities=entities,
                concepts=concepts,
                sentiment=sentiment,
                confidence_score=overall_confidence,
                processed_at=datetime.datetime.utcnow(),
                metadata={
                    'note_type': note_type.value,
                    'patient_id': patient_id,
                    'text_length': len(text),
                    'entity_count': len(entities),
                    'concept_count': len(concepts)
                }
            )
            
            # Update stats
            self.processing_stats['documents_processed'] += 1
            self.processing_stats['entities_extracted'] += len(entities)
            self.processing_stats['last_processed'] = datetime.datetime.utcnow()
            
            return result
            
        except Exception as e:
            logging.error(f"Error processing clinical note: {e}")
            raise
    
    def _extract_clinical_concepts(self, entities: List[MedicalEntity]) -> List[ClinicalConcept]:
        """Extract clinical concepts from entities"""
        concepts = []
        seen_concepts = set()
        
        for entity in entities:
            if entity.concept_id and entity.concept_id not in seen_concepts:
                concept = ClinicalConcept(
                    concept_id=entity.concept_id,
                    preferred_term=entity.normalized_form or entity.text,
                    synonyms=[entity.text] if entity.text != entity.normalized_form else [],
                    semantic_type=self._get_semantic_type(entity.entity_type)
                )
                
                concepts.append(concept)
                seen_concepts.add(entity.concept_id)
        
        return concepts
    
    def _get_semantic_type(self, entity_type: EntityType) -> str:
        """Map entity type to semantic type"""
        mapping = {
            EntityType.MEDICATION: 'Pharmacologic Substance',
            EntityType.CONDITION: 'Disease or Syndrome',
            EntityType.PROCEDURE: 'Therapeutic or Preventive Procedure',
            EntityType.ANATOMY: 'Body Part, Organ, or Organ Component',
            EntityType.SYMPTOM: 'Sign or Symptom',
            EntityType.LAB_VALUE: 'Laboratory Result',
            EntityType.VITAL_SIGN: 'Clinical Attribute'
        }
        
        return mapping.get(entity_type, 'Entity')
    
    def batch_process_notes(self, notes: List[Dict[str, Any]]) -> List[NLPResult]:
        """Process multiple clinical notes in batch"""
        results = []
        
        for note_data in notes:
            try:
                text = note_data.get('text', '')
                note_type = NoteType(note_data.get('note_type', 'progress_note'))
                patient_id = note_data.get('patient_id')
                
                result = self.process_clinical_note(text, note_type, patient_id)
                results.append(result)
                
            except Exception as e:
                logging.error(f"Error processing note {note_data.get('id', 'unknown')}: {e}")
                continue
        
        return results
    
    def generate_summary_report(self, results: List[NLPResult]) -> Dict[str, Any]:
        """Generate summary report from NLP results"""
        if not results:
            return {'error': 'No results to analyze'}
        
        # Aggregate statistics
        total_entities = sum(len(r.entities) for r in results)
        total_concepts = sum(len(r.concepts) for r in results)
        
        # Entity type distribution
        entity_types = {}
        for result in results:
            for entity in result.entities:
                entity_type = entity.entity_type.value
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # Sentiment distribution
        sentiments = {}
        for result in results:
            sentiment = result.sentiment.value
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        
        # Most common entities
        entity_texts = {}
        for result in results:
            for entity in result.entities:
                normalized = entity.normalized_form or entity.text.lower()
                entity_texts[normalized] = entity_texts.get(normalized, 0) + 1
        
        most_common_entities = sorted(entity_texts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'summary': {
                'documents_processed': len(results),
                'total_entities': total_entities,
                'total_concepts': total_concepts,
                'avg_entities_per_doc': total_entities / len(results),
                'avg_confidence': sum(r.confidence_score for r in results) / len(results)
            },
            'entity_distribution': entity_types,
            'sentiment_distribution': sentiments,
            'most_common_entities': most_common_entities,
            'generated_at': datetime.datetime.utcnow().isoformat()
        }
    
    def search_entities_by_type(self, results: List[NLPResult], 
                               entity_type: EntityType) -> List[MedicalEntity]:
        """Search for entities of specific type across all results"""
        matching_entities = []
        
        for result in results:
            for entity in result.entities:
                if entity.entity_type == entity_type:
                    matching_entities.append(entity)
        
        return matching_entities
    
    def extract_medication_regimen(self, results: List[NLPResult]) -> Dict[str, List[Dict]]:
        """Extract medication regimens from NLP results"""
        medications = {}
        
        for result in results:
            for entity in result.entities:
                if entity.entity_type == EntityType.MEDICATION:
                    med_name = entity.normalized_form or entity.text
                    
                    if med_name not in medications:
                        medications[med_name] = []
                    
                    # Look for dosage information near the medication
                    dosage_entities = [e for e in result.entities 
                                     if e.entity_type == EntityType.DOSAGE 
                                     and abs(e.start_pos - entity.start_pos) < 50]
                    
                    medication_info = {
                        'text': entity.text,
                        'confidence': entity.confidence,
                        'concept_id': entity.concept_id,
                        'dosages': [d.text for d in dosage_entities],
                        'document_date': result.processed_at.isoformat()
                    }
                    
                    medications[med_name].append(medication_info)
        
        return medications
    
    def identify_clinical_trends(self, results: List[NLPResult]) -> Dict[str, Any]:
        """Identify clinical trends across multiple notes"""
        # Sort results by processing date
        sorted_results = sorted(results, key=lambda r: r.processed_at)
        
        trends = {
            'sentiment_trend': [],
            'entity_count_trend': [],
            'medication_changes': [],
            'condition_mentions': {}
        }
        
        # Track sentiment over time
        for result in sorted_results:
            trends['sentiment_trend'].append({
                'date': result.processed_at.isoformat(),
                'sentiment': result.sentiment.value,
                'confidence': result.confidence_score
            })
            
            trends['entity_count_trend'].append({
                'date': result.processed_at.isoformat(),
                'entity_count': len(result.entities)
            })
        
        # Track condition mentions over time
        for result in sorted_results:
            for entity in result.entities:
                if entity.entity_type == EntityType.CONDITION:
                    condition = entity.normalized_form or entity.text.lower()
                    
                    if condition not in trends['condition_mentions']:
                        trends['condition_mentions'][condition] = []
                    
                    trends['condition_mentions'][condition].append({
                        'date': result.processed_at.isoformat(),
                        'text': entity.text,
                        'confidence': entity.confidence
                    })
        
        return trends
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.processing_stats,
            'last_processed': self.processing_stats['last_processed'].isoformat() 
                            if self.processing_stats['last_processed'] else None
        }