#!/usr/bin/env python3
"""
Document Summarization Module
Generates summaries using various LLM approaches
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import uuid
from datetime import datetime
import asyncio

# NLP and summarization
import spacy
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from textblob import TextBlob
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# HTTP client for AI orchestrator
import requests
import aiohttp

# Text processing
import pandas as pd

# Utilities
import warnings
warnings.filterwarnings('ignore')

class DocumentSummarizer:
    """Document summarization using multiple approaches"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './output/summaries')
        self.ai_orchestrator_url = self.config.get('ai_orchestrator_url', 'http://localhost:8003')
        self.max_chunk_size = self.config.get('max_chunk_size', 4000)
        self.summary_ratio = self.config.get('summary_ratio', 0.3)
        
        # Summary types
        self.summary_types = {
            'extractive': 'Extract key sentences from the document',
            'abstractive': 'Generate new sentences that capture key information',
            'key_points': 'Extract main bullet points and key insights',
            'executive': 'Executive summary for business documents',
            'technical': 'Technical summary focusing on methods and results',
            'structured': 'Structured summary with sections'
        }
        
        # Initialize models
        self.spacy_model = None
        self.summarization_pipeline = None
        self.tokenizer = None
        self.nltk_ready = False
        
        # Setup directories
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize NLP models for summarization"""
        
        try:
            # Load spaCy model
            try:
                self.spacy_model = spacy.load("en_core_web_sm")
                self.logger.info("spaCy model loaded successfully")
            except OSError:
                self.logger.warning("spaCy English model not found")
                self.spacy_model = None
            
            # Load summarization pipeline
            try:
                self.summarization_pipeline = pipeline(
                    "summarization",
                    model="facebook/bart-large-cnn",
                    device=-1  # Use CPU
                )
                self.logger.info("BART summarization model loaded successfully")
            except Exception as e:
                self.logger.warning(f"Could not load BART model: {str(e)}")
                try:
                    # Fallback to smaller model
                    self.summarization_pipeline = pipeline(
                        "summarization",
                        model="sshleifer/distilbart-cnn-12-6",
                        device=-1
                    )
                    self.logger.info("DistilBART summarization model loaded successfully")
                except Exception as e2:
                    self.logger.warning(f"Could not load DistilBART model: {str(e2)}")
                    self.summarization_pipeline = None
            
            # Initialize NLTK
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                self.nltk_ready = True
                self.logger.info("NLTK components loaded successfully")
            except Exception as e:
                self.logger.warning(f"NLTK initialization failed: {str(e)}")
                self.nltk_ready = False
                
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
    
    async def summarize_document(self, text: str, metadata: Dict = None, options: Dict = None) -> Dict:
        """
        Generate document summary using multiple approaches
        """
        session_id = str(uuid.uuid4())
        options = options or {}
        metadata = metadata or {}
        
        try:
            self.logger.info(f"Summarizing document (session: {session_id})")
            
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'original_length': len(text),
                'processed_length': len(processed_text),
                'summaries': {},
                'metadata': metadata
            }
            
            # Document analysis
            analysis = self._analyze_document_structure(processed_text)
            result['document_analysis'] = analysis
            
            # Generate different types of summaries
            summary_types = options.get('summary_types', ['extractive', 'abstractive', 'key_points'])
            
            for summary_type in summary_types:
                try:
                    if summary_type == 'extractive':
                        summary = await self._generate_extractive_summary(processed_text, options)
                    elif summary_type == 'abstractive':
                        summary = await self._generate_abstractive_summary(processed_text, options)
                    elif summary_type == 'key_points':
                        summary = await self._generate_key_points_summary(processed_text, options)
                    elif summary_type == 'executive':
                        summary = await self._generate_executive_summary(processed_text, metadata, options)
                    elif summary_type == 'technical':
                        summary = await self._generate_technical_summary(processed_text, options)
                    elif summary_type == 'structured':
                        summary = await self._generate_structured_summary(processed_text, analysis, options)
                    else:
                        continue
                    
                    result['summaries'][summary_type] = summary
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate {summary_type} summary: {str(e)}")
                    result['summaries'][summary_type] = {
                        'error': str(e),
                        'success': False
                    }
            
            # Generate unified summary
            if len(result['summaries']) > 1:
                unified_summary = await self._generate_unified_summary(result['summaries'], options)
                result['unified_summary'] = unified_summary
            
            # Calculate summary statistics
            result['statistics'] = self._calculate_summary_statistics(result, processed_text)
            
            # Save results
            self._save_summary_results(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Document summarization failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for summarization"""
        
        # Basic cleaning
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\n+', '\n', text)  # Normalize line breaks
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{3,}', '---', text)
        
        # Clean up common OCR artifacts
        text = re.sub(r'\b[A-Z]{1}[a-z]{1,2}\b', '', text)  # Remove single/double letters
        text = re.sub(r'\b\d{1,2}\b(?=\s|$)', '', text)  # Remove standalone small numbers
        
        return text.strip()
    
    def _analyze_document_structure(self, text: str) -> Dict:
        """Analyze document structure for better summarization"""
        
        analysis = {}
        
        # Basic text statistics
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        analysis['text_stats'] = {
            'total_sentences': len(sentences),
            'total_words': len(words),
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,
            'estimated_reading_time': len(words) / 200  # Assuming 200 WPM
        }
        
        # Document structure detection
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        analysis['structure'] = {
            'paragraph_count': len(paragraphs),
            'has_headers': self._detect_headers(text),
            'has_lists': self._detect_lists(text),
            'has_tables': self._detect_tables(text),
            'sections': self._detect_sections(text)
        }
        
        # Content type indicators
        analysis['content_indicators'] = {
            'has_dates': bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)),
            'has_numbers': bool(re.search(r'\b\d+(?:\.\d+)?(?:[%$]|\s+(?:percent|dollars?))\b', text)),
            'has_citations': bool(re.search(r'\[\d+\]|\(\d{4}\)', text)),
            'formality_level': self._assess_formality(text),
            'technical_level': self._assess_technical_level(text)
        }
        
        # Identify key topics
        analysis['topics'] = self._extract_key_topics(text)
        
        return analysis
    
    def _detect_headers(self, text: str) -> bool:
        """Detect if text has headers"""
        # Look for lines in all caps or with specific formatting
        lines = text.split('\n')
        header_count = 0
        
        for line in lines:
            line = line.strip()
            if line and (line.isupper() or re.match(r'^\d+\.?\s+[A-Z]', line)):
                header_count += 1
        
        return header_count >= 2
    
    def _detect_lists(self, text: str) -> bool:
        """Detect if text has bullet points or numbered lists"""
        return bool(re.search(r'^\s*[•\-\*]\s+|\d+[\.\)]\s+', text, re.MULTILINE))
    
    def _detect_tables(self, text: str) -> bool:
        """Detect if text might contain tables"""
        # Look for multiple consecutive lines with similar patterns
        lines = text.split('\n')
        table_like_lines = 0
        
        for line in lines:
            if re.search(r'\s+\|\s+|\s{3,}', line) or line.count('\t') > 1:
                table_like_lines += 1
        
        return table_like_lines >= 3
    
    def _detect_sections(self, text: str) -> List[Dict]:
        """Detect document sections"""
        sections = []
        lines = text.split('\n')
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check if line looks like a header
            if line and (
                line.isupper() or 
                re.match(r'^\d+\.?\s+[A-Z]', line) or
                (len(line) < 50 and line.istitle())
            ):
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    'title': line,
                    'start_line': i,
                    'content': ''
                }
            elif current_section:
                current_section['content'] += line + '\n'
        
        if current_section:
            sections.append(current_section)
        
        return sections[:10]  # Limit to 10 sections
    
    def _assess_formality(self, text: str) -> str:
        """Assess the formality level of the text"""
        
        formal_indicators = ['whereas', 'hereby', 'pursuant', 'aforementioned', 'shall', 'therefore']
        informal_indicators = ["don't", "can't", "won't", "it's", "that's", "we're"]
        
        formal_count = sum(1 for word in formal_indicators if word in text.lower())
        informal_count = sum(1 for word in informal_indicators if word in text.lower())
        
        if formal_count > informal_count * 2:
            return 'formal'
        elif informal_count > formal_count:
            return 'informal'
        else:
            return 'neutral'
    
    def _assess_technical_level(self, text: str) -> str:
        """Assess the technical complexity of the text"""
        
        technical_indicators = [
            'methodology', 'analysis', 'algorithm', 'implementation', 'framework',
            'protocol', 'specification', 'configuration', 'architecture', 'database'
        ]
        
        technical_count = sum(1 for word in technical_indicators if word in text.lower())
        word_count = len(text.split())
        
        technical_ratio = technical_count / word_count if word_count > 0 else 0
        
        if technical_ratio > 0.01:
            return 'high'
        elif technical_ratio > 0.005:
            return 'medium'
        else:
            return 'low'
    
    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics using TF-IDF"""
        
        try:
            if not self.nltk_ready:
                return []
            
            # Tokenize into sentences
            sentences = sent_tokenize(text)
            if len(sentences) < 3:
                return []
            
            # Create TF-IDF vectorizer
            stop_words = stopwords.words('english')
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words=stop_words,
                ngram_range=(1, 2),
                min_df=1
            )
            
            # Fit vectorizer
            tfidf_matrix = vectorizer.fit_transform(sentences)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get top terms
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            top_indices = np.argsort(mean_scores)[-10:]
            
            top_topics = [feature_names[i] for i in top_indices]
            return list(reversed(top_topics))
            
        except Exception as e:
            self.logger.warning(f"Topic extraction failed: {str(e)}")
            return []
    
    async def _generate_extractive_summary(self, text: str, options: Dict) -> Dict:
        """Generate extractive summary by selecting key sentences"""
        
        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= 3:
                return {
                    'summary': text,
                    'method': 'extractive',
                    'sentence_count': len(sentences),
                    'compression_ratio': 1.0,
                    'confidence': 0.9
                }
            
            # Calculate sentence scores using TF-IDF
            if not self.nltk_ready:
                # Fallback to simple approach
                target_sentences = max(1, int(len(sentences) * self.summary_ratio))
                selected_sentences = sentences[:target_sentences]
            else:
                selected_sentences = self._select_key_sentences(sentences, options)
            
            summary_text = ' '.join(selected_sentences)
            
            return {
                'summary': summary_text,
                'method': 'extractive',
                'selected_sentences': len(selected_sentences),
                'total_sentences': len(sentences),
                'compression_ratio': len(selected_sentences) / len(sentences),
                'confidence': 0.8,
                'key_sentences': [
                    {
                        'text': sent,
                        'position': sentences.index(sent) if sent in sentences else -1
                    }
                    for sent in selected_sentences
                ]
            }
            
        except Exception as e:
            self.logger.warning(f"Extractive summarization failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'extractive',
                'success': False
            }
    
    def _select_key_sentences(self, sentences: List[str], options: Dict) -> List[str]:
        """Select key sentences using TF-IDF scoring"""
        
        try:
            # Remove stop words for scoring
            stop_words = stopwords.words('english')
            
            # Create TF-IDF matrix
            vectorizer = TfidfVectorizer(stop_words=stop_words)
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # Calculate sentence scores
            sentence_scores = np.sum(tfidf_matrix.toarray(), axis=1)
            
            # Get target number of sentences
            target_count = options.get('target_sentences', max(1, int(len(sentences) * self.summary_ratio)))
            target_count = min(target_count, len(sentences))
            
            # Select top sentences
            top_indices = np.argsort(sentence_scores)[-target_count:]
            top_indices = sorted(top_indices)  # Maintain order
            
            return [sentences[i] for i in top_indices]
            
        except Exception as e:
            self.logger.warning(f"Sentence selection failed: {str(e)}")
            # Fallback to first N sentences
            target_count = max(1, int(len(sentences) * self.summary_ratio))
            return sentences[:target_count]
    
    async def _generate_abstractive_summary(self, text: str, options: Dict) -> Dict:
        """Generate abstractive summary using transformer models"""
        
        try:
            # Use local model if available
            if self.summarization_pipeline:
                summary = await self._generate_local_abstractive_summary(text, options)
                if summary['success']:
                    return summary
            
            # Fallback to AI orchestrator
            summary = await self._generate_ai_orchestrator_summary(text, options)
            return summary
            
        except Exception as e:
            self.logger.warning(f"Abstractive summarization failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'abstractive',
                'success': False
            }
    
    async def _generate_local_abstractive_summary(self, text: str, options: Dict) -> Dict:
        """Generate summary using local transformer model"""
        
        try:
            # Chunk text if too long
            max_length = 1024
            min_length = options.get('min_length', 30)
            max_summary_length = options.get('max_length', 150)
            
            if len(text) > max_length:
                # Split into chunks and summarize each
                chunks = self._split_text_into_chunks(text, max_length)
                chunk_summaries = []
                
                for chunk in chunks:
                    if len(chunk.strip()) > 50:  # Skip very short chunks
                        summary = self.summarization_pipeline(
                            chunk,
                            max_length=max_summary_length,
                            min_length=min_length,
                            do_sample=False
                        )
                        chunk_summaries.append(summary[0]['summary_text'])
                
                # Combine chunk summaries
                combined_summary = ' '.join(chunk_summaries)
                
                # Summarize the combined summary if still too long
                if len(combined_summary) > max_length:
                    final_summary = self.summarization_pipeline(
                        combined_summary,
                        max_length=max_summary_length,
                        min_length=min_length,
                        do_sample=False
                    )
                    summary_text = final_summary[0]['summary_text']
                else:
                    summary_text = combined_summary
            else:
                # Summarize directly
                summary = self.summarization_pipeline(
                    text,
                    max_length=max_summary_length,
                    min_length=min_length,
                    do_sample=False
                )
                summary_text = summary[0]['summary_text']
            
            return {
                'summary': summary_text,
                'method': 'abstractive_local',
                'model': 'transformer',
                'original_length': len(text),
                'summary_length': len(summary_text),
                'compression_ratio': len(summary_text) / len(text),
                'confidence': 0.8,
                'success': True
            }
            
        except Exception as e:
            self.logger.warning(f"Local abstractive summarization failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'abstractive_local',
                'success': False
            }
    
    async def _generate_ai_orchestrator_summary(self, text: str, options: Dict) -> Dict:
        """Generate summary using AI orchestrator"""
        
        try:
            # Prepare prompt for summarization
            prompt = self._build_summarization_prompt(text, options)
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    'provider': options.get('ai_provider', 'openai'),
                    'model': options.get('ai_model', 'gpt-3.5-turbo'),
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': options.get('max_tokens', 500),
                    'temperature': options.get('temperature', 0.3)
                }
                
                async with session.post(
                    f'{self.ai_orchestrator_url}/process',
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        summary_text = result['choices'][0]['message']['content']
                        
                        return {
                            'summary': summary_text,
                            'method': 'abstractive_ai',
                            'provider': payload['provider'],
                            'model': payload['model'],
                            'original_length': len(text),
                            'summary_length': len(summary_text),
                            'compression_ratio': len(summary_text) / len(text),
                            'confidence': 0.85,
                            'success': True
                        }
                    else:
                        raise Exception(f"AI service returned status {response.status}")
        
        except Exception as e:
            self.logger.warning(f"AI orchestrator summarization failed: {str(e)}")
            
            # Fallback to simple extractive summary
            extractive_result = await self._generate_extractive_summary(text, options)
            extractive_result['method'] = 'abstractive_fallback'
            extractive_result['note'] = 'Fell back to extractive due to AI service unavailability'
            return extractive_result
    
    def _build_summarization_prompt(self, text: str, options: Dict) -> str:
        """Build prompt for AI-based summarization"""
        
        summary_type = options.get('summary_style', 'general')
        max_words = options.get('max_words', 150)
        
        # Truncate text if too long
        if len(text) > 3000:
            text = text[:3000] + "..."
        
        if summary_type == 'executive':
            prompt = f"""Please provide an executive summary of the following document. Focus on key business decisions, outcomes, and actionable insights. Keep it to approximately {max_words} words:

{text}

Executive Summary:"""
        
        elif summary_type == 'technical':
            prompt = f"""Please provide a technical summary of the following document. Focus on methods, processes, technical details, and results. Keep it to approximately {max_words} words:

{text}

Technical Summary:"""
        
        elif summary_type == 'key_points':
            prompt = f"""Please extract the key points from the following document as a bulleted list. Focus on the most important information and insights:

{text}

Key Points:"""
        
        else:
            prompt = f"""Please provide a concise summary of the following document. Capture the main ideas, important details, and key conclusions. Keep it to approximately {max_words} words:

{text}

Summary:"""
        
        return prompt
    
    async def _generate_key_points_summary(self, text: str, options: Dict) -> Dict:
        """Generate key points summary"""
        
        try:
            # Use AI orchestrator for key points extraction
            prompt = f"""Extract the most important key points from the following text. Present them as a numbered list. Focus on actionable insights, important facts, and main conclusions:

{text[:3000]}

Key Points:"""
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    'provider': options.get('ai_provider', 'openai'),
                    'model': options.get('ai_model', 'gpt-3.5-turbo'),
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 400,
                    'temperature': 0.3
                }
                
                async with session.post(
                    f'{self.ai_orchestrator_url}/process',
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        key_points_text = result['choices'][0]['message']['content']
                        
                        # Parse key points
                        key_points = self._parse_key_points(key_points_text)
                        
                        return {
                            'summary': key_points_text,
                            'key_points': key_points,
                            'method': 'key_points_ai',
                            'point_count': len(key_points),
                            'confidence': 0.8,
                            'success': True
                        }
        
        except Exception as e:
            self.logger.warning(f"AI key points extraction failed: {str(e)}")
        
        # Fallback to extractive approach
        return self._generate_fallback_key_points(text, options)
    
    def _parse_key_points(self, text: str) -> List[str]:
        """Parse key points from AI response"""
        
        # Look for numbered or bulleted lists
        lines = text.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.?\s+', line) or re.match(r'^[•\-\*]\s+', line):
                # Remove numbering/bullets
                clean_point = re.sub(r'^\d+\.?\s+|^[•\-\*]\s+', '', line)
                if clean_point:
                    key_points.append(clean_point)
            elif line and len(line) > 10 and not line.endswith(':'):
                # Standalone important sentence
                key_points.append(line)
        
        return key_points[:10]  # Limit to 10 key points
    
    def _generate_fallback_key_points(self, text: str, options: Dict) -> Dict:
        """Generate key points using extractive methods"""
        
        try:
            sentences = sent_tokenize(text)
            
            # Simple scoring based on sentence position and length
            scored_sentences = []
            
            for i, sentence in enumerate(sentences):
                score = 0
                
                # Position scoring (beginning and end are important)
                if i < len(sentences) * 0.2:  # First 20%
                    score += 2
                elif i > len(sentences) * 0.8:  # Last 20%
                    score += 1
                
                # Length scoring (not too short, not too long)
                word_count = len(sentence.split())
                if 10 <= word_count <= 30:
                    score += 2
                elif 5 <= word_count <= 50:
                    score += 1
                
                # Keyword scoring
                keywords = ['important', 'key', 'main', 'significant', 'critical', 'essential']
                for keyword in keywords:
                    if keyword in sentence.lower():
                        score += 1
                
                scored_sentences.append((sentence, score))
            
            # Select top sentences
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            top_sentences = [sent for sent, score in scored_sentences[:8]]
            
            return {
                'summary': '\n'.join([f"• {sent}" for sent in top_sentences]),
                'key_points': top_sentences,
                'method': 'key_points_extractive',
                'point_count': len(top_sentences),
                'confidence': 0.6,
                'success': True
            }
            
        except Exception as e:
            self.logger.warning(f"Fallback key points generation failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'key_points_extractive',
                'success': False
            }
    
    async def _generate_executive_summary(self, text: str, metadata: Dict, options: Dict) -> Dict:
        """Generate executive summary for business documents"""
        
        try:
            # Build context-aware prompt
            doc_type = metadata.get('document_type', 'document')
            
            prompt = f"""Create an executive summary for this {doc_type}. Focus on:
1. Key business decisions and outcomes
2. Financial implications (if any)
3. Strategic importance
4. Actionable recommendations
5. Risk factors or considerations

Keep the summary concise but comprehensive, suitable for executive leadership.

Document content:
{text[:3000]}

Executive Summary:"""
            
            return await self._call_ai_for_summary(prompt, 'executive_ai', options)
            
        except Exception as e:
            self.logger.warning(f"Executive summary generation failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'executive',
                'success': False
            }
    
    async def _generate_technical_summary(self, text: str, options: Dict) -> Dict:
        """Generate technical summary focusing on methods and implementation"""
        
        try:
            prompt = f"""Create a technical summary of this document. Focus on:
1. Technical methods and approaches used
2. Implementation details
3. Technical results and findings
4. Technical challenges and solutions
5. Technical recommendations

Present the information in a structured, technical format.

Document content:
{text[:3000]}

Technical Summary:"""
            
            return await self._call_ai_for_summary(prompt, 'technical_ai', options)
            
        except Exception as e:
            self.logger.warning(f"Technical summary generation failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'technical',
                'success': False
            }
    
    async def _generate_structured_summary(self, text: str, analysis: Dict, options: Dict) -> Dict:
        """Generate structured summary with sections"""
        
        try:
            sections = analysis.get('structure', {}).get('sections', [])
            
            if sections:
                # Generate section-wise summaries
                section_summaries = []
                
                for section in sections[:5]:  # Limit to 5 sections
                    if len(section.get('content', '').strip()) > 100:
                        section_summary = await self._summarize_section(
                            section['title'], 
                            section['content'], 
                            options
                        )
                        section_summaries.append(section_summary)
                
                return {
                    'summary': '\n\n'.join([f"**{s['title']}**\n{s['summary']}" for s in section_summaries]),
                    'sections': section_summaries,
                    'method': 'structured',
                    'section_count': len(section_summaries),
                    'confidence': 0.8,
                    'success': True
                }
            else:
                # Fallback to general structured format
                prompt = f"""Create a structured summary with the following sections:
1. Overview
2. Key Points
3. Important Details
4. Conclusions/Recommendations

Document content:
{text[:3000]}

Structured Summary:"""
                
                return await self._call_ai_for_summary(prompt, 'structured_ai', options)
                
        except Exception as e:
            self.logger.warning(f"Structured summary generation failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'structured',
                'success': False
            }
    
    async def _summarize_section(self, title: str, content: str, options: Dict) -> Dict:
        """Summarize a specific section"""
        
        try:
            prompt = f"""Summarize this section titled "{title}". Keep it concise but capture the key information:

{content[:1000]}

Summary:"""
            
            result = await self._call_ai_for_summary(prompt, 'section', options)
            
            return {
                'title': title,
                'summary': result.get('summary', ''),
                'original_length': len(content),
                'summary_length': len(result.get('summary', ''))
            }
            
        except Exception as e:
            self.logger.warning(f"Section summarization failed: {str(e)}")
            return {
                'title': title,
                'summary': content[:200] + "..." if len(content) > 200 else content,
                'error': str(e)
            }
    
    async def _call_ai_for_summary(self, prompt: str, method: str, options: Dict) -> Dict:
        """Helper method to call AI service for summarization"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'provider': options.get('ai_provider', 'openai'),
                    'model': options.get('ai_model', 'gpt-3.5-turbo'),
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': options.get('max_tokens', 500),
                    'temperature': options.get('temperature', 0.3)
                }
                
                async with session.post(
                    f'{self.ai_orchestrator_url}/process',
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        summary_text = result['choices'][0]['message']['content']
                        
                        return {
                            'summary': summary_text,
                            'method': method,
                            'provider': payload['provider'],
                            'model': payload['model'],
                            'confidence': 0.85,
                            'success': True
                        }
                    else:
                        raise Exception(f"AI service returned status {response.status}")
        
        except Exception as e:
            raise Exception(f"AI service call failed: {str(e)}")
    
    async def _generate_unified_summary(self, summaries: Dict, options: Dict) -> Dict:
        """Generate unified summary from multiple summary types"""
        
        try:
            # Combine the best parts from different summaries
            summary_texts = []
            
            for summary_type, summary_data in summaries.items():
                if summary_data.get('success', True) and 'summary' in summary_data:
                    summary_texts.append(f"{summary_type.title()}: {summary_data['summary']}")
            
            if not summary_texts:
                return {
                    'error': 'No successful summaries to unify',
                    'success': False
                }
            
            combined_text = '\n\n'.join(summary_texts)
            
            # Use AI to create unified summary
            prompt = f"""Create a unified, coherent summary from these different summary approaches. Combine the best insights while avoiding redundancy:

{combined_text}

Unified Summary:"""
            
            return await self._call_ai_for_summary(prompt, 'unified', options)
            
        except Exception as e:
            self.logger.warning(f"Unified summary generation failed: {str(e)}")
            return {
                'error': str(e),
                'method': 'unified',
                'success': False
            }
    
    def _split_text_into_chunks(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks for processing"""
        
        # Split by sentences first
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence) <= max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _calculate_summary_statistics(self, result: Dict, original_text: str) -> Dict:
        """Calculate statistics about the summaries"""
        
        stats = {
            'original_stats': {
                'character_count': len(original_text),
                'word_count': len(original_text.split()),
                'sentence_count': len(sent_tokenize(original_text))
            },
            'summary_stats': {},
            'compression_ratios': {},
            'processing_info': {
                'total_summaries': len(result.get('summaries', {})),
                'successful_summaries': len([s for s in result.get('summaries', {}).values() if s.get('success', True)]),
                'methods_used': list(result.get('summaries', {}).keys())
            }
        }
        
        for summary_type, summary_data in result.get('summaries', {}).items():
            if 'summary' in summary_data:
                summary_text = summary_data['summary']
                stats['summary_stats'][summary_type] = {
                    'character_count': len(summary_text),
                    'word_count': len(summary_text.split()),
                    'sentence_count': len(sent_tokenize(summary_text))
                }
                
                # Calculate compression ratio
                original_words = len(original_text.split())
                summary_words = len(summary_text.split())
                stats['compression_ratios'][summary_type] = summary_words / original_words if original_words > 0 else 0
        
        return stats
    
    def _save_summary_results(self, results: Dict):
        """Save summarization results to file"""
        
        try:
            output_file = os.path.join(
                self.output_dir,
                f"summary_{results['session_id']}.json"
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Summary results saved to {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save summary results: {str(e)}")

def main():
    """Command line interface for document summarization"""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description='Summarize documents')
    parser.add_argument('text', help='Text to summarize or file path')
    parser.add_argument('--output-dir', default='./output/summaries', help='Output directory')
    parser.add_argument('--summary-types', nargs='+', default=['extractive', 'abstractive'], 
                       help='Types of summaries to generate')
    parser.add_argument('--ai-orchestrator-url', default='http://localhost:8003', 
                       help='AI orchestrator URL')
    parser.add_argument('--file', action='store_true', help='Input is a file path')
    parser.add_argument('--max-words', type=int, default=150, help='Maximum words in summary')
    
    args = parser.parse_args()
    
    # Configure summarizer
    config = {
        'output_dir': args.output_dir,
        'ai_orchestrator_url': args.ai_orchestrator_url
    }
    
    options = {
        'summary_types': args.summary_types,
        'max_words': args.max_words
    }
    
    # Get text
    if args.file:
        with open(args.text, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = args.text
    
    # Summarize
    async def run_summarization():
        summarizer = DocumentSummarizer(config)
        result = await summarizer.summarize_document(text, options=options)
        
        # Print results
        if 'summaries' in result:
            print(f"✓ Document summarization completed")
            print(f"  Session ID: {result['session_id']}")
            print(f"  Original length: {result['original_length']} characters")
            print(f"  Summaries generated: {len(result['summaries'])}")
            
            for summary_type, summary_data in result['summaries'].items():
                if summary_data.get('success', True):
                    print(f"\n{summary_type.title()} Summary:")
                    print(f"  {summary_data.get('summary', '')[:200]}...")
                    if 'compression_ratio' in summary_data:
                        print(f"  Compression ratio: {summary_data['compression_ratio']:.2f}")
                else:
                    print(f"\n{summary_type.title()} Summary: Failed - {summary_data.get('error', 'Unknown error')}")
        else:
            print(f"✗ Summarization failed: {result.get('error', 'Unknown error')}")
    
    asyncio.run(run_summarization())

if __name__ == '__main__':
    main()