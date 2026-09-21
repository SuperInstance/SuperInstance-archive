"""
Document classification system using multiple approaches
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from collections import Counter
import pickle
import os

# NLP libraries
try:
    import spacy
    from spacy.lang.en import English
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.svm import SVC
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from ..core.config import settings, DOCUMENT_TYPES, LANGUAGE_CONFIGS
from ..core.database import DatabaseManager
from ..models.document_models import DocumentType, DocumentClassification

doc_logger = logging.getLogger('document_processing')

class DocumentClassifier:
    """Multi-method document classification system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Classification models
        self.rule_based_classifier = RuleBasedClassifier()
        self.ml_classifier = None
        self.transformer_classifier = None
        
        # Initialize models
        asyncio.create_task(self._initialize_models())
    
    async def _initialize_models(self):
        """Initialize ML models in background"""
        try:
            # Initialize ML classifier
            if SKLEARN_AVAILABLE:
                self.ml_classifier = MLClassifier()
                await self.ml_classifier.initialize()
            
            # Initialize transformer-based classifier
            if TRANSFORMERS_AVAILABLE and settings.ai_models.huggingface_api_key:
                self.transformer_classifier = TransformerClassifier()
                await self.transformer_classifier.initialize()
            
            doc_logger.info("Document classifiers initialized")
            
        except Exception as e:
            doc_logger.warning(f"Failed to initialize some classifiers: {str(e)}")
    
    async def classify_document(self, job_id: str, text_content: str, 
                              metadata: Dict[str, Any] = None) -> List[DocumentClassification]:
        """
        Classify document using multiple methods and return ranked results
        
        Args:
            job_id: Processing job ID
            text_content: Full document text content
            metadata: Additional metadata for classification
            
        Returns:
            List of classification results ranked by confidence
        """
        if metadata is None:
            metadata = {}
        
        try:
            doc_logger.info(f"Starting document classification for job {job_id}")
            
            # Prepare text for classification
            text_sample = self._prepare_text_sample(text_content)
            
            # Get classifications from different methods
            classifications = []
            
            # Rule-based classification
            rule_results = await self._classify_with_rules(text_sample, metadata)
            classifications.extend(rule_results)
            
            # ML-based classification
            if self.ml_classifier:
                try:
                    ml_results = await self._classify_with_ml(text_sample, metadata)
                    classifications.extend(ml_results)
                except Exception as e:
                    doc_logger.warning(f"ML classification failed: {str(e)}")
            
            # Transformer-based classification
            if self.transformer_classifier:
                try:
                    transformer_results = await self._classify_with_transformer(text_sample, metadata)
                    classifications.extend(transformer_results)
                except Exception as e:
                    doc_logger.warning(f"Transformer classification failed: {str(e)}")
            
            # Ensemble and rank results
            final_classifications = self._ensemble_classifications(classifications)
            
            # Save results to database
            saved_classifications = []
            for classification in final_classifications:
                classification_id = await self.db_manager.save_classification(
                    job_id=job_id,
                    document_type=classification['document_type'].value,
                    confidence=classification['confidence_score'],
                    method=classification['classification_method'],
                    features=classification['features_used'],
                    model_version=classification.get('model_version')
                )
                
                saved_classification = DocumentClassification(
                    classification_id=classification_id,
                    job_id=job_id,
                    document_type=classification['document_type'],
                    confidence_score=classification['confidence_score'],
                    classification_method=classification['classification_method'],
                    features_used=classification['features_used'],
                    model_version=classification.get('model_version'),
                    created_at=classification.get('created_at')
                )
                saved_classifications.append(saved_classification)
            
            doc_logger.info(f"Document classification completed for job {job_id}: {len(final_classifications)} classifications")
            return saved_classifications
            
        except Exception as e:
            doc_logger.error(f"Document classification failed for job {job_id}: {str(e)}")
            raise
    
    def _prepare_text_sample(self, text: str, max_length: int = 5000) -> str:
        """Prepare text sample for classification"""
        
        # Clean text
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Take beginning and end of document for better classification
        if len(cleaned) <= max_length:
            return cleaned
        
        # Take first 60% and last 40% of allowed length
        first_part_length = int(max_length * 0.6)
        last_part_length = max_length - first_part_length
        
        first_part = cleaned[:first_part_length]
        last_part = cleaned[-last_part_length:]
        
        return first_part + "\n...\n" + last_part
    
    async def _classify_with_rules(self, text: str, metadata: Dict) -> List[Dict]:
        """Classify using rule-based approach"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.rule_based_classifier.classify, text, metadata
        )
    
    async def _classify_with_ml(self, text: str, metadata: Dict) -> List[Dict]:
        """Classify using ML approach"""
        
        if not self.ml_classifier:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.ml_classifier.classify, text, metadata
        )
    
    async def _classify_with_transformer(self, text: str, metadata: Dict) -> List[Dict]:
        """Classify using transformer approach"""
        
        if not self.transformer_classifier:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.transformer_classifier.classify, text, metadata
        )
    
    def _ensemble_classifications(self, classifications: List[Dict]) -> List[Dict]:
        """Combine and rank classifications from different methods"""
        
        if not classifications:
            return [{
                'document_type': DocumentType.OTHER,
                'confidence_score': 0.5,
                'classification_method': 'fallback',
                'features_used': {},
                'model_version': '1.0'
            }]
        
        # Group by document type and combine scores
        type_scores = {}
        type_methods = {}
        type_features = {}
        
        for classification in classifications:
            doc_type = classification['document_type']
            confidence = classification['confidence_score']
            method = classification['classification_method']
            
            if doc_type not in type_scores:
                type_scores[doc_type] = []
                type_methods[doc_type] = []
                type_features[doc_type] = {}
            
            type_scores[doc_type].append(confidence)
            type_methods[doc_type].append(method)
            type_features[doc_type].update(classification.get('features_used', {}))
        
        # Calculate ensemble scores
        ensemble_results = []
        
        for doc_type, scores in type_scores.items():
            # Weighted average with higher weight for transformer models
            weighted_scores = []
            for i, score in enumerate(scores):
                method = type_methods[doc_type][i]
                if 'transformer' in method.lower():
                    weight = 0.5
                elif 'ml' in method.lower():
                    weight = 0.3
                else:  # rule-based
                    weight = 0.2
                
                weighted_scores.append(score * weight)
            
            ensemble_score = sum(weighted_scores) / len(weighted_scores)
            
            # Boost score if multiple methods agree
            agreement_bonus = (len(scores) - 1) * 0.1
            final_score = min(ensemble_score + agreement_bonus, 1.0)
            
            ensemble_results.append({
                'document_type': doc_type,
                'confidence_score': final_score,
                'classification_method': 'ensemble_' + '_'.join(set(type_methods[doc_type])),
                'features_used': type_features[doc_type],
                'model_version': '1.0',
                'contributing_methods': len(scores)
            })
        
        # Sort by confidence and return top 3
        ensemble_results.sort(key=lambda x: x['confidence_score'], reverse=True)
        return ensemble_results[:3]


class RuleBasedClassifier:
    """Rule-based document classifier using keywords and patterns"""
    
    def __init__(self):
        self.document_patterns = DOCUMENT_TYPES
    
    def classify(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Classify document using rules"""
        
        if metadata is None:
            metadata = {}
        
        text_lower = text.lower()
        results = []
        
        for doc_type, config in self.document_patterns.items():
            score = self._calculate_rule_score(text_lower, config)
            
            if score > 0.1:  # Minimum threshold
                results.append({
                    'document_type': DocumentType(doc_type),
                    'confidence_score': min(score, 0.95),  # Cap at 95% for rule-based
                    'classification_method': 'rule_based',
                    'features_used': {
                        'keyword_matches': self._get_keyword_matches(text_lower, config['keywords']),
                        'pattern_matches': self._get_pattern_matches(text, config['patterns'])
                    }
                })
        
        # Sort by confidence
        results.sort(key=lambda x: x['confidence_score'], reverse=True)
        return results[:5]  # Return top 5 candidates
    
    def _calculate_rule_score(self, text: str, config: Dict) -> float:
        """Calculate classification score based on rules"""
        
        score = 0.0
        
        # Keyword matching
        keywords = config.get('keywords', [])
        if keywords:
            keyword_matches = sum(1 for keyword in keywords if keyword in text)
            keyword_score = (keyword_matches / len(keywords)) * 0.6
            score += keyword_score
        
        # Pattern matching
        patterns = config.get('patterns', [])
        if patterns:
            pattern_matches = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
            pattern_score = (pattern_matches / len(patterns)) * 0.4
            score += pattern_score
        
        return score
    
    def _get_keyword_matches(self, text: str, keywords: List[str]) -> List[str]:
        """Get list of matched keywords"""
        return [keyword for keyword in keywords if keyword in text]
    
    def _get_pattern_matches(self, text: str, patterns: List[str]) -> List[str]:
        """Get list of matched patterns"""
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches


class MLClassifier:
    """Machine learning-based document classifier"""
    
    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self.model_path = os.path.join(settings.output_dir, 'ml_classifier.pkl')
        self.is_trained = False
    
    async def initialize(self):
        """Initialize ML classifier"""
        
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn not available for ML classification")
        
        # Try to load existing model
        if os.path.exists(self.model_path):
            try:
                await self._load_model()
                doc_logger.info("Loaded pre-trained ML classifier")
                return
            except Exception as e:
                doc_logger.warning(f"Failed to load ML model: {str(e)}")
        
        # Train new model with sample data
        await self._train_model()
    
    async def _load_model(self):
        """Load pre-trained model"""
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model_sync)
    
    def _load_model_sync(self):
        """Synchronous model loading"""
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
            self.vectorizer = model_data['vectorizer']
            self.classifier = model_data['classifier']
            self.is_trained = True
    
    async def _train_model(self):
        """Train ML model with sample data"""
        
        # Generate sample training data based on document type patterns
        training_data = self._generate_training_data()
        
        if len(training_data) < 10:
            doc_logger.warning("Insufficient training data for ML classifier")
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._train_model_sync, training_data)
    
    def _generate_training_data(self) -> List[Tuple[str, str]]:
        """Generate synthetic training data based on document patterns"""
        
        training_samples = []
        
        for doc_type, config in DOCUMENT_TYPES.items():
            keywords = config.get('keywords', [])
            
            if not keywords:
                continue
            
            # Generate sample texts for this document type
            for _ in range(5):  # 5 samples per type
                # Create text with keywords from this type
                sample_text = self._create_sample_text(keywords, doc_type)
                training_samples.append((sample_text, doc_type))
        
        return training_samples
    
    def _create_sample_text(self, keywords: List[str], doc_type: str) -> str:
        """Create sample text containing keywords for training"""
        
        # Base templates for different document types
        templates = {
            'invoice': "Invoice #{num} Date: {date} Amount: ${amount} {keywords}",
            'contract': "Agreement between parties {keywords} effective date {date}",
            'resume': "Professional experience and qualifications {keywords} education background",
            'report': "Executive summary and analysis {keywords} findings and recommendations",
            'letter': "Dear recipient {keywords} sincerely yours",
            'financial_statement': "Balance sheet assets liabilities {keywords} financial position",
            'legal_document': "Legal proceedings {keywords} court jurisdiction",
            'technical_manual': "Technical specifications and procedures {keywords} requirements",
            'academic_paper': "Research methodology and analysis {keywords} references bibliography"
        }
        
        template = templates.get(doc_type, "{keywords}")
        
        # Select random keywords
        import random
        selected_keywords = random.sample(keywords, min(3, len(keywords)))
        keyword_text = ' '.join(selected_keywords)
        
        # Fill template
        sample = template.format(
            keywords=keyword_text,
            num=random.randint(1000, 9999),
            date="2024-01-01",
            amount=random.randint(100, 10000)
        )
        
        return sample
    
    def _train_model_sync(self, training_data: List[Tuple[str, str]]):
        """Synchronous model training"""
        
        try:
            texts, labels = zip(*training_data)
            
            # Create TF-IDF vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            # Vectorize texts
            X = self.vectorizer.fit_transform(texts)
            y = list(labels)
            
            # Train classifier
            self.classifier = RandomForestClassifier(
                n_estimators=100,
                random_state=42
            )
            
            self.classifier.fit(X, y)
            self.is_trained = True
            
            # Save model
            model_data = {
                'vectorizer': self.vectorizer,
                'classifier': self.classifier
            }
            
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            doc_logger.info("ML classifier trained and saved")
            
        except Exception as e:
            doc_logger.error(f"ML model training failed: {str(e)}")
            raise
    
    def classify(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Classify document using ML model"""
        
        if not self.is_trained or not self.vectorizer or not self.classifier:
            return []
        
        try:
            # Vectorize text
            X = self.vectorizer.transform([text])
            
            # Get predictions and probabilities
            predictions = self.classifier.predict(X)
            probabilities = self.classifier.predict_proba(X)
            
            # Get class labels
            classes = self.classifier.classes_
            
            # Create results
            results = []
            for i, (class_name, prob) in enumerate(zip(classes, probabilities[0])):
                if prob > 0.1:  # Minimum confidence threshold
                    try:
                        doc_type = DocumentType(class_name)
                    except ValueError:
                        doc_type = DocumentType.OTHER
                    
                    results.append({
                        'document_type': doc_type,
                        'confidence_score': float(prob),
                        'classification_method': 'ml_random_forest',
                        'features_used': {
                            'tfidf_features': True,
                            'ngram_range': '1-2'
                        },
                        'model_version': '1.0'
                    })
            
            # Sort by confidence
            results.sort(key=lambda x: x['confidence_score'], reverse=True)
            return results[:3]
            
        except Exception as e:
            doc_logger.warning(f"ML classification failed: {str(e)}")
            return []


class TransformerClassifier:
    """Transformer-based document classifier using pre-trained models"""
    
    def __init__(self):
        self.classifier = None
        self.model_name = "microsoft/DialoGPT-medium"  # Fallback model
    
    async def initialize(self):
        """Initialize transformer classifier"""
        
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library not available")
        
        try:
            # Try to load a pre-trained classification model
            # Note: In production, you'd want to fine-tune on your specific document types
            self.classifier = pipeline(
                "text-classification",
                model="distilbert-base-uncased",
                return_all_scores=True
            )
            
            doc_logger.info("Transformer classifier initialized")
            
        except Exception as e:
            doc_logger.warning(f"Failed to initialize transformer classifier: {str(e)}")
            self.classifier = None
    
    def classify(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Classify document using transformer model"""
        
        if not self.classifier:
            return []
        
        try:
            # Truncate text to model's max length
            max_length = 512
            truncated_text = text[:max_length]
            
            # Get predictions
            results = self.classifier(truncated_text)
            
            # Map generic labels to document types (this is a simplified mapping)
            # In production, you'd fine-tune the model on your document types
            label_mapping = {
                'NEGATIVE': DocumentType.OTHER,
                'POSITIVE': DocumentType.REPORT,  # Assuming positive sentiment indicates reports
            }
            
            classifications = []
            for result in results:
                label = result['label']
                score = result['score']
                
                doc_type = label_mapping.get(label, DocumentType.OTHER)
                
                classifications.append({
                    'document_type': doc_type,
                    'confidence_score': float(score),
                    'classification_method': 'transformer_distilbert',
                    'features_used': {
                        'transformer_features': True,
                        'model': 'distilbert-base-uncased'
                    },
                    'model_version': '1.0'
                })
            
            return classifications[:2]  # Return top 2
            
        except Exception as e:
            doc_logger.warning(f"Transformer classification failed: {str(e)}")
            return []