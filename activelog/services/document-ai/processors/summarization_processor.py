"""
Document summarization processor using LLMs and extractive methods
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import json
from datetime import datetime
import hashlib

# NLP libraries for extractive summarization
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import spacy
    from spacy.lang.en import English
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from ..core.config import settings
from ..core.database import DatabaseManager
from ..models.document_models import DocumentSummary, SummaryType

nlp_logger = logging.getLogger('nlp')

class SummarizationProcessor:
    """Document summarization using multiple approaches"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Summarization models
        self.extractive_summarizer = None
        self.transformer_summarizer = None
        
        # AI model configurations
        self.openai_api_key = settings.ai_models.openai_api_key
        self.anthropic_api_key = settings.ai_models.anthropic_api_key
        self.use_local_llm = settings.ai_models.use_local_llm
        self.local_llm_url = settings.ai_models.local_llm_url
        
        # Initialize models
        asyncio.create_task(self._initialize_models())
    
    async def _initialize_models(self):
        """Initialize summarization models"""
        try:
            # Initialize extractive summarizer
            if SKLEARN_AVAILABLE and SPACY_AVAILABLE:
                self.extractive_summarizer = ExtractiveSummarizer()
                await self.extractive_summarizer.initialize()
            
            # Initialize transformer summarizer
            if TRANSFORMERS_AVAILABLE:
                self.transformer_summarizer = TransformerSummarizer()
                await self.transformer_summarizer.initialize()
            
            nlp_logger.info("Summarization processors initialized")
            
        except Exception as e:
            nlp_logger.warning(f"Failed to initialize some summarization models: {str(e)}")
    
    async def generate_summaries(self, job_id: str, text_content: str,
                               document_type: str = "other",
                               summary_types: List[SummaryType] = None) -> List[DocumentSummary]:
        """
        Generate document summaries using multiple methods
        
        Args:
            job_id: Processing job ID
            text_content: Full document text content
            document_type: Type of document for context-aware summarization
            summary_types: Types of summaries to generate
            
        Returns:
            List of generated summaries
        """
        if summary_types is None:
            summary_types = [SummaryType.EXTRACTIVE, SummaryType.KEY_POINTS]
        
        try:
            nlp_logger.info(f"Starting summarization for job {job_id}")
            
            # Clean and prepare text
            cleaned_text = self._clean_text_for_summarization(text_content)
            
            if len(cleaned_text.split()) < 50:
                nlp_logger.warning(f"Text too short for meaningful summarization: {len(cleaned_text.split())} words")
                return []
            
            # Generate summaries
            summaries = []
            
            for summary_type in summary_types:
                try:
                    if summary_type == SummaryType.EXTRACTIVE:
                        summary = await self._generate_extractive_summary(cleaned_text, document_type)
                    elif summary_type == SummaryType.ABSTRACTIVE:
                        summary = await self._generate_abstractive_summary(cleaned_text, document_type)
                    elif summary_type == SummaryType.KEY_POINTS:
                        summary = await self._generate_key_points_summary(cleaned_text, document_type)
                    elif summary_type == SummaryType.EXECUTIVE:
                        summary = await self._generate_executive_summary(cleaned_text, document_type)
                    else:
                        continue
                    
                    if summary:
                        summaries.append(summary)
                    
                except Exception as e:
                    nlp_logger.warning(f"Failed to generate {summary_type} summary: {str(e)}")
                    continue
            
            # Save summaries to database
            saved_summaries = []
            for summary_data in summaries:
                summary_id = await self.db_manager.save_document_summary(
                    job_id=job_id,
                    summary_type=summary_data['type'].value,
                    summary_text=summary_data['text'],
                    key_points=summary_data.get('key_points', []),
                    word_count=len(summary_data['text'].split()),
                    compression_ratio=summary_data.get('compression_ratio'),
                    model_used=summary_data.get('model_used')
                )
                
                summary = DocumentSummary(
                    summary_id=summary_id,
                    job_id=job_id,
                    summary_type=summary_data['type'],
                    summary_text=summary_data['text'],
                    key_points=summary_data.get('key_points', []),
                    word_count=len(summary_data['text'].split()),
                    compression_ratio=summary_data.get('compression_ratio'),
                    model_used=summary_data.get('model_used'),
                    created_at=datetime.utcnow()
                )
                saved_summaries.append(summary)
            
            nlp_logger.info(f"Summarization completed for job {job_id}: {len(saved_summaries)} summaries")
            return saved_summaries
            
        except Exception as e:
            nlp_logger.error(f"Summarization failed for job {job_id}: {str(e)}")
            raise
    
    def _clean_text_for_summarization(self, text: str) -> str:
        """Clean and prepare text for summarization"""
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove very short sentences (likely artifacts)
        sentences = cleaned.split('.')
        filtered_sentences = [s.strip() for s in sentences if len(s.strip().split()) >= 3]
        
        # Rejoin sentences
        cleaned = '. '.join(filtered_sentences)
        
        # Remove common PDF artifacts
        cleaned = re.sub(r'\f', ' ', cleaned)  # Form feed
        cleaned = re.sub(r'^\d+\s*$', '', cleaned, flags=re.MULTILINE)  # Page numbers
        
        return cleaned.strip()
    
    async def _generate_extractive_summary(self, text: str, document_type: str) -> Optional[Dict]:
        """Generate extractive summary using sentence ranking"""
        
        if self.extractive_summarizer:
            try:
                loop = asyncio.get_event_loop()
                summary = await loop.run_in_executor(
                    self.executor, 
                    self.extractive_summarizer.summarize, 
                    text, 
                    document_type
                )
                
                if summary:
                    return {
                        'type': SummaryType.EXTRACTIVE,
                        'text': summary['text'],
                        'key_points': summary.get('sentences', []),
                        'compression_ratio': summary.get('compression_ratio'),
                        'model_used': 'tfidf_extractive'
                    }
                
            except Exception as e:
                nlp_logger.warning(f"Extractive summarization failed: {str(e)}")
        
        # Fallback to simple extraction
        return await self._generate_simple_extractive_summary(text)
    
    async def _generate_simple_extractive_summary(self, text: str) -> Dict:
        """Simple extractive summary using first and last sentences"""
        
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
        
        if len(sentences) <= 3:
            summary_text = text
            selected_sentences = sentences
        else:
            # Take first sentence, middle sentence, and last sentence
            selected_sentences = [
                sentences[0],
                sentences[len(sentences) // 2],
                sentences[-1]
            ]
            summary_text = '. '.join(selected_sentences) + '.'
        
        original_words = len(text.split())
        summary_words = len(summary_text.split())
        compression_ratio = summary_words / original_words if original_words > 0 else 0
        
        return {
            'type': SummaryType.EXTRACTIVE,
            'text': summary_text,
            'key_points': selected_sentences,
            'compression_ratio': compression_ratio,
            'model_used': 'simple_extractive'
        }
    
    async def _generate_abstractive_summary(self, text: str, document_type: str) -> Optional[Dict]:
        """Generate abstractive summary using LLMs"""
        
        # Try different LLM providers
        summary_text = None
        model_used = None
        
        # Try OpenAI first
        if self.openai_api_key:
            try:
                summary_text = await self._summarize_with_openai(text, document_type)
                model_used = 'openai_gpt'
            except Exception as e:
                nlp_logger.warning(f"OpenAI summarization failed: {str(e)}")
        
        # Try Anthropic if OpenAI failed
        if not summary_text and self.anthropic_api_key:
            try:
                summary_text = await self._summarize_with_anthropic(text, document_type)
                model_used = 'anthropic_claude'
            except Exception as e:
                nlp_logger.warning(f"Anthropic summarization failed: {str(e)}")
        
        # Try local LLM if others failed
        if not summary_text and self.use_local_llm:
            try:
                summary_text = await self._summarize_with_local_llm(text, document_type)
                model_used = 'local_llm'
            except Exception as e:
                nlp_logger.warning(f"Local LLM summarization failed: {str(e)}")
        
        # Try transformer model as final fallback
        if not summary_text and self.transformer_summarizer:
            try:
                loop = asyncio.get_event_loop()
                summary_text = await loop.run_in_executor(
                    self.executor,
                    self.transformer_summarizer.summarize,
                    text
                )
                model_used = 'transformer_bart'
            except Exception as e:
                nlp_logger.warning(f"Transformer summarization failed: {str(e)}")
        
        if summary_text:
            original_words = len(text.split())
            summary_words = len(summary_text.split())
            compression_ratio = summary_words / original_words if original_words > 0 else 0
            
            return {
                'type': SummaryType.ABSTRACTIVE,
                'text': summary_text,
                'compression_ratio': compression_ratio,
                'model_used': model_used
            }
        
        return None
    
    async def _generate_key_points_summary(self, text: str, document_type: str) -> Optional[Dict]:
        """Generate key points summary"""
        
        prompt = f"""
        Extract the key points from this {document_type} document. 
        Present them as a bulleted list of the most important information.
        
        Text: {text[:3000]}...
        
        Key Points:
        """
        
        # Try to get key points from LLM
        key_points_text = None
        model_used = None
        
        if self.openai_api_key:
            try:
                key_points_text = await self._call_openai(prompt)
                model_used = 'openai_gpt'
            except Exception as e:
                nlp_logger.warning(f"OpenAI key points failed: {str(e)}")
        
        if not key_points_text and self.anthropic_api_key:
            try:
                key_points_text = await self._call_anthropic(prompt)
                model_used = 'anthropic_claude'
            except Exception as e:
                nlp_logger.warning(f"Anthropic key points failed: {str(e)}")
        
        if not key_points_text:
            # Fallback to extractive key points
            key_points_text, model_used = await self._generate_extractive_key_points(text)
        
        if key_points_text:
            # Parse key points from text
            key_points = self._parse_key_points(key_points_text)
            
            return {
                'type': SummaryType.KEY_POINTS,
                'text': key_points_text,
                'key_points': key_points,
                'model_used': model_used
            }
        
        return None
    
    async def _generate_executive_summary(self, text: str, document_type: str) -> Optional[Dict]:
        """Generate executive summary"""
        
        prompt = f"""
        Create a concise executive summary for this {document_type} document.
        Focus on the most critical information that decision-makers need to know.
        Keep it professional and under 200 words.
        
        Text: {text[:4000]}...
        
        Executive Summary:
        """
        
        summary_text = None
        model_used = None
        
        if self.openai_api_key:
            try:
                summary_text = await self._call_openai(prompt)
                model_used = 'openai_gpt'
            except Exception as e:
                nlp_logger.warning(f"OpenAI executive summary failed: {str(e)}")
        
        if not summary_text and self.anthropic_api_key:
            try:
                summary_text = await self._call_anthropic(prompt)
                model_used = 'anthropic_claude'
            except Exception as e:
                nlp_logger.warning(f"Anthropic executive summary failed: {str(e)}")
        
        if summary_text:
            original_words = len(text.split())
            summary_words = len(summary_text.split())
            compression_ratio = summary_words / original_words if original_words > 0 else 0
            
            return {
                'type': SummaryType.EXECUTIVE,
                'text': summary_text,
                'compression_ratio': compression_ratio,
                'model_used': model_used
            }
        
        return None
    
    async def _summarize_with_openai(self, text: str, document_type: str) -> str:
        """Summarize using OpenAI GPT"""
        
        prompt = f"""
        Summarize this {document_type} document concisely while preserving the key information.
        Focus on the main points, conclusions, and important details.
        
        Text: {text[:4000]}...
        
        Summary:
        """
        
        return await self._call_openai(prompt)
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        
        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 500,
            'temperature': 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")
    
    async def _summarize_with_anthropic(self, text: str, document_type: str) -> str:
        """Summarize using Anthropic Claude"""
        
        prompt = f"""
        Summarize this {document_type} document concisely while preserving the key information.
        Focus on the main points, conclusions, and important details.
        
        Text: {text[:4000]}...
        
        Summary:
        """
        
        return await self._call_anthropic(prompt)
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API"""
        
        headers = {
            'x-api-key': self.anthropic_api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        data = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 500,
            'temperature': 0.3,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['content'][0]['text'].strip()
                else:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error {response.status}: {error_text}")
    
    async def _summarize_with_local_llm(self, text: str, document_type: str) -> str:
        """Summarize using local LLM (e.g., Ollama)"""
        
        prompt = f"""
        Summarize this {document_type} document concisely:
        
        {text[:3000]}...
        
        Summary:
        """
        
        data = {
            'model': settings.ai_models.local_llm_model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.3,
                'num_predict': 200
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.local_llm_url}/api/generate',
                json=data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['response'].strip()
                else:
                    error_text = await response.text()
                    raise Exception(f"Local LLM error {response.status}: {error_text}")
    
    async def _generate_extractive_key_points(self, text: str) -> Tuple[str, str]:
        """Generate key points using extractive methods"""
        
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
        
        if len(sentences) <= 5:
            key_points = sentences
        else:
            # Take every nth sentence based on length
            step = len(sentences) // 5
            key_points = [sentences[i] for i in range(0, len(sentences), step)][:5]
        
        # Format as bullet points
        formatted_points = []
        for i, point in enumerate(key_points, 1):
            formatted_points.append(f"• {point.strip()}")
        
        key_points_text = '\n'.join(formatted_points)
        
        return key_points_text, 'extractive_key_points'
    
    def _parse_key_points(self, text: str) -> List[str]:
        """Parse key points from formatted text"""
        
        # Split by common bullet point indicators
        lines = text.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Remove bullet point indicators
                clean_line = re.sub(r'^[•\-\*\d+\.\)]\s*', '', line)
                if clean_line:
                    key_points.append(clean_line)
        
        return key_points[:10]  # Limit to 10 key points


class ExtractiveSummarizer:
    """Extractive summarization using TF-IDF and sentence ranking"""
    
    def __init__(self):
        self.vectorizer = None
        self.nlp = None
    
    async def initialize(self):
        """Initialize the extractive summarizer"""
        
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn not available for extractive summarization")
        
        if not SPACY_AVAILABLE:
            raise ImportError("spaCy not available for sentence processing")
        
        loop = asyncio.get_event_loop()
        
        try:
            # Load English model for sentence segmentation
            self.nlp = await loop.run_in_executor(None, spacy.load, "en_core_web_sm")
        except OSError:
            # Fallback to basic English
            self.nlp = await loop.run_in_executor(None, English)
        
        # Initialize TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def summarize(self, text: str, document_type: str = "document",
                 target_sentences: int = 3) -> Dict[str, Any]:
        """Generate extractive summary"""
        
        if not self.nlp or not self.vectorizer:
            raise RuntimeError("Extractive summarizer not initialized")
        
        # Process text with spaCy
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]
        
        if len(sentences) <= target_sentences:
            return {
                'text': ' '.join(sentences),
                'sentences': sentences,
                'compression_ratio': 1.0
            }
        
        # Create TF-IDF matrix
        try:
            tfidf_matrix = self.vectorizer.fit_transform(sentences)
        except ValueError:
            # Fallback if TF-IDF fails
            return {
                'text': ' '.join(sentences[:target_sentences]),
                'sentences': sentences[:target_sentences],
                'compression_ratio': target_sentences / len(sentences)
            }
        
        # Calculate sentence scores
        sentence_scores = np.mean(tfidf_matrix.toarray(), axis=1)
        
        # Get top sentences
        top_indices = np.argsort(sentence_scores)[-target_sentences:]
        top_indices = sorted(top_indices)  # Keep original order
        
        selected_sentences = [sentences[i] for i in top_indices]
        summary_text = ' '.join(selected_sentences)
        
        return {
            'text': summary_text,
            'sentences': selected_sentences,
            'compression_ratio': len(selected_sentences) / len(sentences)
        }


class TransformerSummarizer:
    """Transformer-based abstractive summarization"""
    
    def __init__(self):
        self.summarizer = None
    
    async def initialize(self):
        """Initialize transformer summarizer"""
        
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not available")
        
        try:
            loop = asyncio.get_event_loop()
            self.summarizer = await loop.run_in_executor(
                None,
                pipeline,
                "summarization",
                model="facebook/bart-large-cnn",
                tokenizer="facebook/bart-large-cnn"
            )
            nlp_logger.info("Loaded BART summarization model")
            
        except Exception as e:
            nlp_logger.warning(f"Failed to load BART model: {str(e)}")
            # Try smaller model as fallback
            try:
                self.summarizer = await loop.run_in_executor(
                    None,
                    pipeline,
                    "summarization",
                    model="sshleifer/distilbart-cnn-12-6"
                )
                nlp_logger.info("Loaded DistilBART summarization model")
            except Exception as e2:
                nlp_logger.error(f"Failed to load any transformer summarization model: {str(e2)}")
                self.summarizer = None
    
    def summarize(self, text: str, max_length: int = 150, min_length: int = 50) -> Optional[str]:
        """Generate abstractive summary using transformer"""
        
        if not self.summarizer:
            return None
        
        try:
            # Truncate text to model's maximum input length
            max_input_length = 1024
            if len(text.split()) > max_input_length:
                words = text.split()[:max_input_length]
                text = ' '.join(words)
            
            # Generate summary
            result = self.summarizer(
                text,
                max_length=max_length,
                min_length=min_length,
                do_sample=False
            )
            
            if result and len(result) > 0:
                return result[0]['summary_text']
            
        except Exception as e:
            nlp_logger.warning(f"Transformer summarization failed: {str(e)}")
        
        return None