#!/usr/bin/env python3
"""
Document Classification Module
Classifies documents into categories like invoice, contract, resume, etc.
"""

import os
import json
import logging
import pickle
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import uuid
from datetime import datetime

# NLP and ML
import spacy
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np

# Text processing
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from textblob import TextBlob

# Utilities
import warnings
warnings.filterwarnings('ignore')

class DocumentClassifier:
    """Document classification using multiple ML approaches"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './output/classified')
        self.models_dir = self.config.get('models_dir', './models')
        self.min_confidence = self.config.get('min_confidence', 0.7)
        
        # Document categories and their patterns
        self.document_categories = {
            'invoice': {
                'keywords': ['invoice', 'bill', 'payment', 'amount', 'total', 'due', 'tax', 'subtotal', 
                           'invoice number', 'bill to', 'payment terms', 'net', 'gross'],
                'patterns': [
                    r'invoice\s*#?\s*\d+',
                    r'amount\s*due',
                    r'payment\s*terms',
                    r'bill\s*to',
                    r'subtotal',
                    r'tax\s*amount',
                    r'total\s*amount'
                ]
            },
            'contract': {
                'keywords': ['agreement', 'contract', 'terms', 'conditions', 'party', 'whereas', 
                           'hereby', 'execution', 'binding', 'obligations', 'termination', 'effective date'],
                'patterns': [
                    r'this\s+agreement',
                    r'party\s+of\s+the\s+first\s+part',
                    r'whereas',
                    r'hereby\s+agree',
                    r'terms\s+and\s+conditions',
                    r'effective\s+date',
                    r'in\s+witness\s+whereof'
                ]
            },
            'resume': {
                'keywords': ['experience', 'education', 'skills', 'objective', 'summary', 'employment',
                           'university', 'degree', 'certification', 'achievements', 'responsibilities'],
                'patterns': [
                    r'work\s+experience',
                    r'education',
                    r'skills',
                    r'objective',
                    r'summary',
                    r'\d{4}\s*-\s*\d{4}',  # Year ranges
                    r'bachelor|master|phd|degree',
                    r'university|college'
                ]
            },
            'legal_document': {
                'keywords': ['plaintiff', 'defendant', 'court', 'jurisdiction', 'statute', 'whereas',
                           'motion', 'complaint', 'petition', 'affidavit', 'deposition'],
                'patterns': [
                    r'case\s+no',
                    r'plaintiff\s+v\s+defendant',
                    r'court\s+of',
                    r'jurisdiction',
                    r'motion\s+for',
                    r'comes\s+now',
                    r'respectfully\s+submitted'
                ]
            },
            'financial_report': {
                'keywords': ['revenue', 'profit', 'loss', 'assets', 'liabilities', 'equity', 'cash flow',
                           'balance sheet', 'income statement', 'financial', 'quarterly', 'annual'],
                'patterns': [
                    r'balance\s+sheet',
                    r'income\s+statement',
                    r'cash\s+flow',
                    r'profit\s+and\s+loss',
                    r'quarterly\s+report',
                    r'annual\s+report',
                    r'financial\s+statement'
                ]
            },
            'medical_record': {
                'keywords': ['patient', 'diagnosis', 'treatment', 'medication', 'symptoms', 'doctor',
                           'hospital', 'medical', 'prescription', 'dosage', 'allergies'],
                'patterns': [
                    r'patient\s+name',
                    r'date\s+of\s+birth',
                    r'diagnosis',
                    r'treatment\s+plan',
                    r'medications?',
                    r'allergies',
                    r'medical\s+history'
                ]
            },
            'academic_paper': {
                'keywords': ['abstract', 'introduction', 'methodology', 'results', 'conclusion',
                           'references', 'bibliography', 'hypothesis', 'experiment', 'analysis'],
                'patterns': [
                    r'abstract',
                    r'introduction',
                    r'methodology',
                    r'results\s+and\s+discussion',
                    r'conclusion',
                    r'references',
                    r'bibliography'
                ]
            },
            'manual': {
                'keywords': ['instructions', 'manual', 'guide', 'procedure', 'steps', 'operation',
                           'installation', 'configuration', 'troubleshooting', 'warranty'],
                'patterns': [
                    r'user\s+manual',
                    r'installation\s+guide',
                    r'operating\s+instructions',
                    r'step\s+\d+',
                    r'troubleshooting',
                    r'warranty\s+information'
                ]
            },
            'policy': {
                'keywords': ['policy', 'procedure', 'compliance', 'regulation', 'standard', 'guideline',
                           'requirement', 'mandatory', 'prohibited', 'authorized'],
                'patterns': [
                    r'policy\s+number',
                    r'effective\s+date',
                    r'compliance\s+with',
                    r'regulatory\s+requirements',
                    r'standard\s+operating\s+procedure',
                    r'guidelines?\s+for'
                ]
            },
            'other': {
                'keywords': [],
                'patterns': []
            }
        }
        
        # Initialize models
        self.tfidf_vectorizer = None
        self.sklearn_model = None
        self.transformer_model = None
        self.nlp = None
        
        # Setup directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize NLP models and classifiers"""
        try:
            # Load spaCy model
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp = None
            
            # Initialize transformer model for advanced classification
            try:
                self.transformer_model = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=-1  # Use CPU
                )
            except Exception as e:
                self.logger.warning(f"Could not load transformer model: {str(e)}")
                self.transformer_model = None
            
            # Download NLTK data
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
    
    def classify_document(self, text: str, metadata: Dict = None, options: Dict = None) -> Dict:
        """
        Classify document using multiple approaches
        """
        session_id = str(uuid.uuid4())
        options = options or {}
        
        try:
            self.logger.info(f"Classifying document (session: {session_id})")
            
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            # Multiple classification approaches
            results = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'text_length': len(text),
                'processed_text_length': len(processed_text),
                'classifications': {}
            }
            
            # Approach 1: Rule-based classification
            rule_based_result = self._classify_rule_based(processed_text)
            results['classifications']['rule_based'] = rule_based_result
            
            # Approach 2: Statistical features
            statistical_result = self._classify_statistical_features(processed_text)
            results['classifications']['statistical'] = statistical_result
            
            # Approach 3: Transformer-based (if available)
            if self.transformer_model:
                transformer_result = self._classify_transformer(processed_text)
                results['classifications']['transformer'] = transformer_result
            
            # Approach 4: TF-IDF + ML (if trained model exists)
            if self.sklearn_model and self.tfidf_vectorizer:
                ml_result = self._classify_sklearn(processed_text)
                results['classifications']['machine_learning'] = ml_result
            
            # Ensemble classification
            ensemble_result = self._ensemble_classification(results['classifications'])
            results['final_classification'] = ensemble_result
            
            # Extract document features
            features = self._extract_document_features(text, processed_text)
            results['features'] = features
            
            # Add metadata analysis
            if metadata:
                metadata_analysis = self._analyze_metadata(metadata)
                results['metadata_analysis'] = metadata_analysis
            
            # Save results
            self._save_classification_results(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Document classification failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for classification"""
        
        # Basic cleaning
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)]', '', text)  # Remove special chars
        text = text.lower()
        
        return text.strip()
    
    def _classify_rule_based(self, text: str) -> Dict:
        """Rule-based classification using keywords and patterns"""
        
        scores = {}
        matches = {}
        
        for category, rules in self.document_categories.items():
            if category == 'other':
                continue
                
            score = 0
            category_matches = {'keywords': [], 'patterns': []}
            
            # Keyword matching
            for keyword in rules['keywords']:
                keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                keyword_matches = len(re.findall(keyword_pattern, text))
                if keyword_matches > 0:
                    score += keyword_matches * 2  # Weight keywords higher
                    category_matches['keywords'].append({
                        'keyword': keyword,
                        'count': keyword_matches
                    })
            
            # Pattern matching
            for pattern in rules['patterns']:
                pattern_matches = len(re.findall(pattern, text, re.IGNORECASE))
                if pattern_matches > 0:
                    score += pattern_matches * 3  # Weight patterns even higher
                    category_matches['patterns'].append({
                        'pattern': pattern,
                        'count': pattern_matches
                    })
            
            scores[category] = score
            matches[category] = category_matches
        
        # Normalize scores
        total_score = sum(scores.values())
        if total_score > 0:
            normalized_scores = {cat: score / total_score for cat, score in scores.items()}
        else:
            normalized_scores = {cat: 0 for cat in scores.keys()}
        
        # Get top prediction
        top_category = max(normalized_scores.items(), key=lambda x: x[1])
        
        return {
            'predicted_category': top_category[0] if top_category[1] > 0 else 'other',
            'confidence': top_category[1],
            'scores': normalized_scores,
            'matches': matches,
            'method': 'rule_based'
        }
    
    def _classify_statistical_features(self, text: str) -> Dict:
        """Classification based on statistical text features"""
        
        # Calculate text statistics
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        # Basic statistics
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        
        # Document structure indicators
        has_date_patterns = bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text))
        has_currency = bool(re.search(r'\$[\d,]+\.?\d*', text))
        has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        has_phone = bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text))
        has_addresses = bool(re.search(r'\d+\s+\w+\s+(street|st|avenue|ave|road|rd|drive|dr)', text, re.IGNORECASE))
        
        # Calculate feature scores for each category
        feature_scores = {}
        
        # Invoice features
        invoice_score = 0
        if has_currency:
            invoice_score += 0.3
        if has_date_patterns:
            invoice_score += 0.2
        if re.search(r'total|subtotal|tax', text):
            invoice_score += 0.3
        if re.search(r'payment|bill|invoice', text):
            invoice_score += 0.2
        feature_scores['invoice'] = invoice_score
        
        # Contract features
        contract_score = 0
        if has_date_patterns:
            contract_score += 0.2
        if avg_sentence_length > 20:  # Legal documents tend to have long sentences
            contract_score += 0.3
        if re.search(r'agreement|contract|party|whereas', text):
            contract_score += 0.3
        if has_addresses:
            contract_score += 0.2
        feature_scores['contract'] = contract_score
        
        # Resume features
        resume_score = 0
        if re.search(r'experience|education|skills', text):
            resume_score += 0.4
        if re.search(r'\d{4}\s*-\s*\d{4}', text):  # Year ranges
            resume_score += 0.3
        if has_email or has_phone:
            resume_score += 0.3
        feature_scores['resume'] = resume_score
        
        # Financial report features
        financial_score = 0
        if has_currency:
            financial_score += 0.3
        if re.search(r'revenue|profit|loss|assets|liabilities', text):
            financial_score += 0.4
        if re.search(r'quarter|annual|fiscal', text):
            financial_score += 0.3
        feature_scores['financial_report'] = financial_score
        
        # Academic paper features
        academic_score = 0
        if re.search(r'abstract|methodology|results|conclusion', text):
            academic_score += 0.4
        if re.search(r'figure|table|equation|reference', text):
            academic_score += 0.3
        if avg_sentence_length > 15:  # Academic writing tends to be verbose
            academic_score += 0.3
        feature_scores['academic_paper'] = academic_score
        
        # Get top prediction
        if feature_scores:
            top_category = max(feature_scores.items(), key=lambda x: x[1])
            predicted_category = top_category[0] if top_category[1] > 0.3 else 'other'
            confidence = top_category[1]
        else:
            predicted_category = 'other'
            confidence = 0
        
        return {
            'predicted_category': predicted_category,
            'confidence': confidence,
            'feature_scores': feature_scores,
            'text_features': {
                'avg_sentence_length': avg_sentence_length,
                'avg_word_length': avg_word_length,
                'has_currency': has_currency,
                'has_dates': has_date_patterns,
                'has_email': has_email,
                'has_phone': has_phone,
                'has_addresses': has_addresses
            },
            'method': 'statistical_features'
        }
    
    def _classify_transformer(self, text: str) -> Dict:
        """Classification using transformer model"""
        
        try:
            # Truncate text if too long
            max_length = 1000
            if len(text) > max_length:
                text = text[:max_length]
            
            # Define candidate labels
            candidate_labels = [
                "invoice or bill",
                "legal contract or agreement", 
                "resume or CV",
                "legal document",
                "financial report",
                "medical record",
                "academic paper",
                "instruction manual",
                "policy document",
                "other document"
            ]
            
            # Classify
            result = self.transformer_model(text, candidate_labels)
            
            # Map labels back to categories
            label_mapping = {
                "invoice or bill": "invoice",
                "legal contract or agreement": "contract",
                "resume or CV": "resume",
                "legal document": "legal_document",
                "financial report": "financial_report",
                "medical record": "medical_record",
                "academic paper": "academic_paper",
                "instruction manual": "manual",
                "policy document": "policy",
                "other document": "other"
            }
            
            predicted_label = result['labels'][0]
            predicted_category = label_mapping.get(predicted_label, 'other')
            confidence = result['scores'][0]
            
            # Create scores dictionary
            scores = {}
            for label, score in zip(result['labels'], result['scores']):
                category = label_mapping.get(label, 'other')
                scores[category] = score
            
            return {
                'predicted_category': predicted_category,
                'confidence': confidence,
                'scores': scores,
                'method': 'transformer'
            }
            
        except Exception as e:
            self.logger.warning(f"Transformer classification failed: {str(e)}")
            return {
                'predicted_category': 'other',
                'confidence': 0,
                'error': str(e),
                'method': 'transformer'
            }
    
    def _classify_sklearn(self, text: str) -> Dict:
        """Classification using trained scikit-learn model"""
        
        try:
            # Vectorize text
            text_vector = self.tfidf_vectorizer.transform([text])
            
            # Predict
            prediction = self.sklearn_model.predict(text_vector)[0]
            probabilities = self.sklearn_model.predict_proba(text_vector)[0]
            
            # Get class labels
            classes = self.sklearn_model.classes_
            
            # Create scores dictionary
            scores = {class_name: prob for class_name, prob in zip(classes, probabilities)}
            
            confidence = max(probabilities)
            
            return {
                'predicted_category': prediction,
                'confidence': confidence,
                'scores': scores,
                'method': 'machine_learning'
            }
            
        except Exception as e:
            self.logger.warning(f"Sklearn classification failed: {str(e)}")
            return {
                'predicted_category': 'other',
                'confidence': 0,
                'error': str(e),
                'method': 'machine_learning'
            }
    
    def _ensemble_classification(self, classifications: Dict) -> Dict:
        """Combine multiple classification results"""
        
        # Collect all predictions and confidences
        predictions = []
        confidences = []
        
        for method, result in classifications.items():
            if 'predicted_category' in result and 'confidence' in result:
                predictions.append(result['predicted_category'])
                confidences.append(result['confidence'])
        
        if not predictions:
            return {
                'predicted_category': 'other',
                'confidence': 0,
                'method': 'ensemble',
                'component_results': classifications
            }
        
        # Weighted voting based on confidence
        category_votes = {}
        total_weight = 0
        
        for pred, conf in zip(predictions, confidences):
            if pred not in category_votes:
                category_votes[pred] = 0
            category_votes[pred] += conf
            total_weight += conf
        
        # Normalize votes
        if total_weight > 0:
            normalized_votes = {cat: vote / total_weight for cat, vote in category_votes.items()}
        else:
            normalized_votes = category_votes
        
        # Get final prediction
        if normalized_votes:
            final_category = max(normalized_votes.items(), key=lambda x: x[1])
            predicted_category = final_category[0]
            confidence = final_category[1]
        else:
            predicted_category = 'other'
            confidence = 0
        
        return {
            'predicted_category': predicted_category,
            'confidence': confidence,
            'category_votes': normalized_votes,
            'method': 'ensemble',
            'component_results': {
                method: {
                    'category': result.get('predicted_category'),
                    'confidence': result.get('confidence')
                } for method, result in classifications.items()
                if 'predicted_category' in result
            }
        }
    
    def _extract_document_features(self, original_text: str, processed_text: str) -> Dict:
        """Extract various document features"""
        
        features = {}
        
        # Text statistics
        features['text_stats'] = {
            'total_characters': len(original_text),
            'total_words': len(processed_text.split()),
            'total_sentences': len(sent_tokenize(original_text)),
            'avg_word_length': np.mean([len(word) for word in processed_text.split()]) if processed_text.split() else 0,
            'avg_sentence_length': len(processed_text.split()) / len(sent_tokenize(original_text)) if sent_tokenize(original_text) else 0
        }
        
        # Structural features
        features['structure'] = {
            'has_headers': bool(re.search(r'^[A-Z\s]+$', original_text, re.MULTILINE)),
            'has_bullet_points': bool(re.search(r'^\s*[•\-\*]\s+', original_text, re.MULTILINE)),
            'has_numbered_lists': bool(re.search(r'^\s*\d+[\.\)]\s+', original_text, re.MULTILINE)),
            'paragraph_count': len([p for p in original_text.split('\n\n') if p.strip()]),
            'line_count': len(original_text.split('\n'))
        }
        
        # Content features
        features['content'] = {
            'has_dates': bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', original_text)),
            'has_currency': bool(re.search(r'\$[\d,]+\.?\d*', original_text)),
            'has_percentages': bool(re.search(r'\d+%', original_text)),
            'has_emails': bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', original_text)),
            'has_phone_numbers': bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', original_text)),
            'has_urls': bool(re.search(r'https?://[^\s]+', original_text)),
            'has_addresses': bool(re.search(r'\d+\s+\w+\s+(street|st|avenue|ave|road|rd)', original_text, re.IGNORECASE))
        }
        
        # Language features
        try:
            blob = TextBlob(processed_text[:1000])  # Limit for performance
            features['language'] = {
                'sentiment_polarity': blob.sentiment.polarity,
                'sentiment_subjectivity': blob.sentiment.subjectivity,
                'readability_score': self._calculate_readability(processed_text)
            }
        except:
            features['language'] = {
                'sentiment_polarity': 0,
                'sentiment_subjectivity': 0,
                'readability_score': 0
            }
        
        return features
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate simple readability score (Flesch Reading Ease approximation)"""
        
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        if not sentences or not words:
            return 0
        
        avg_sentence_length = len(words) / len(sentences)
        syllable_count = sum(self._count_syllables(word) for word in words)
        avg_syllables_per_word = syllable_count / len(words)
        
        # Simplified Flesch Reading Ease formula
        reading_ease = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        return max(0, min(100, reading_ease))
    
    def _count_syllables(self, word: str) -> int:
        """Simple syllable counting"""
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            if char in vowels:
                if not prev_was_vowel:
                    syllable_count += 1
                prev_was_vowel = True
            else:
                prev_was_vowel = False
        
        # Handle silent 'e'
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    def _analyze_metadata(self, metadata: Dict) -> Dict:
        """Analyze document metadata for classification clues"""
        
        analysis = {}
        
        # File-based indicators
        if 'filename' in metadata:
            filename = metadata['filename'].lower()
            analysis['filename_indicators'] = {
                'suggests_invoice': any(term in filename for term in ['invoice', 'bill', 'receipt']),
                'suggests_contract': any(term in filename for term in ['contract', 'agreement', 'terms']),
                'suggests_resume': any(term in filename for term in ['resume', 'cv', 'curriculum']),
                'suggests_report': any(term in filename for term in ['report', 'analysis', 'summary'])
            }
        
        # Date-based indicators
        if 'creation_date' in metadata or 'modification_date' in metadata:
            analysis['date_indicators'] = {
                'has_creation_date': 'creation_date' in metadata,
                'has_modification_date': 'modification_date' in metadata
            }
        
        # Author/creator indicators
        if 'author' in metadata or 'creator' in metadata:
            analysis['authorship'] = {
                'has_author': 'author' in metadata,
                'has_creator': 'creator' in metadata
            }
        
        # Document properties
        if 'page_count' in metadata:
            page_count = metadata['page_count']
            analysis['document_properties'] = {
                'page_count': page_count,
                'is_short_document': page_count <= 2,
                'is_medium_document': 3 <= page_count <= 10,
                'is_long_document': page_count > 10
            }
        
        return analysis
    
    def _save_classification_results(self, results: Dict):
        """Save classification results to file"""
        
        try:
            output_file = os.path.join(
                self.output_dir,
                f"classification_{results['session_id']}.json"
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Classification results saved to {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save classification results: {str(e)}")
    
    def train_custom_model(self, training_data: List[Dict], model_name: str = 'custom_classifier'):
        """Train a custom classification model"""
        
        try:
            # Prepare training data
            texts = [item['text'] for item in training_data]
            labels = [item['category'] for item in training_data]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            # Vectorize text
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            X_train_tfidf = self.tfidf_vectorizer.fit_transform(X_train)
            X_test_tfidf = self.tfidf_vectorizer.transform(X_test)
            
            # Train model
            self.sklearn_model = LogisticRegression(random_state=42, max_iter=1000)
            self.sklearn_model.fit(X_train_tfidf, y_train)
            
            # Evaluate
            y_pred = self.sklearn_model.predict(X_test_tfidf)
            report = classification_report(y_test, y_pred, output_dict=True)
            
            # Save model
            model_path = os.path.join(self.models_dir, f'{model_name}.pkl')
            vectorizer_path = os.path.join(self.models_dir, f'{model_name}_vectorizer.pkl')
            
            with open(model_path, 'wb') as f:
                pickle.dump(self.sklearn_model, f)
            
            with open(vectorizer_path, 'wb') as f:
                pickle.dump(self.tfidf_vectorizer, f)
            
            self.logger.info(f"Model trained and saved: {model_path}")
            self.logger.info(f"Model accuracy: {report['accuracy']:.3f}")
            
            return {
                'success': True,
                'model_path': model_path,
                'accuracy': report['accuracy'],
                'classification_report': report
            }
            
        except Exception as e:
            self.logger.error(f"Model training failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_custom_model(self, model_name: str = 'custom_classifier'):
        """Load a trained custom model"""
        
        try:
            model_path = os.path.join(self.models_dir, f'{model_name}.pkl')
            vectorizer_path = os.path.join(self.models_dir, f'{model_name}_vectorizer.pkl')
            
            if os.path.exists(model_path) and os.path.exists(vectorizer_path):
                with open(model_path, 'rb') as f:
                    self.sklearn_model = pickle.load(f)
                
                with open(vectorizer_path, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
                
                self.logger.info(f"Model loaded: {model_path}")
                return True
            else:
                self.logger.warning(f"Model files not found: {model_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Model loading failed: {str(e)}")
            return False

def main():
    """Command line interface for document classification"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Classify documents')
    parser.add_argument('text', help='Text to classify or file path')
    parser.add_argument('--output-dir', default='./output/classified', help='Output directory')
    parser.add_argument('--min-confidence', type=float, default=0.7, help='Minimum confidence threshold')
    parser.add_argument('--file', action='store_true', help='Input is a file path')
    
    args = parser.parse_args()
    
    # Configure classifier
    config = {
        'output_dir': args.output_dir,
        'min_confidence': args.min_confidence
    }
    
    # Get text
    if args.file:
        with open(args.text, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = args.text
    
    # Classify
    classifier = DocumentClassifier(config)
    result = classifier.classify_document(text)
    
    # Print results
    if 'final_classification' in result:
        final = result['final_classification']
        print(f"✓ Document classified")
        print(f"  Category: {final['predicted_category']}")
        print(f"  Confidence: {final['confidence']:.3f}")
        print(f"  Session ID: {result['session_id']}")
        
        if 'component_results' in final:
            print(f"  Component results:")
            for method, comp_result in final['component_results'].items():
                print(f"    {method}: {comp_result['category']} ({comp_result['confidence']:.3f})")
    else:
        print(f"✗ Classification failed: {result.get('error', 'Unknown error')}")

if __name__ == '__main__':
    main()