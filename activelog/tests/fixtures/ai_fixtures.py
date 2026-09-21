"""
AI-related test fixtures and data generators
"""

import uuid
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from faker import Faker

fake = Faker()


class AIFixtures:
    """Generate AI-related test data and fixtures"""
    
    @staticmethod
    def create_embedding(
        embedding_id: Optional[str] = None,
        file_id: Optional[str] = None,
        model: str = "text-embedding-ada-002",
        dimension: int = 1536,
        **kwargs
    ) -> Dict[str, Any]:
        """Create embedding fixture"""
        
        embedding_id = embedding_id or str(uuid.uuid4())
        file_id = file_id or str(uuid.uuid4())
        
        # Generate realistic embedding vector
        vector = np.random.normal(0, 0.1, dimension).tolist()
        # Normalize to unit vector (common in embeddings)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = (np.array(vector) / norm).tolist()
        
        chunk_text = fake.text(max_nb_chars=500)
        
        return {
            'id': embedding_id,
            'file_id': file_id,
            'chunk_id': str(uuid.uuid4()),
            'embedding_model': model,
            'model_version': random.choice(['v1', 'v2', 'v3']),
            'embedding_vector': vector,
            'dimension': dimension,
            'chunk_text': chunk_text,
            'chunk_index': random.randint(0, 100),
            'chunk_start': random.randint(0, 10000),
            'chunk_end': random.randint(100, 10500),
            'confidence_score': round(random.uniform(0.7, 1.0), 3),
            'created_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'processing_time_ms': random.randint(50, 2000),
            'metadata': {
                'language': random.choice(['en', 'es', 'fr', 'de', 'ja']),
                'text_length': len(chunk_text),
                'token_count': len(chunk_text.split()),
                'preprocessing_applied': random.sample([
                    'lowercase', 'remove_punctuation', 'stem', 'lemmatize'
                ], random.randint(0, 3)),
                'quality_score': round(random.uniform(0.5, 1.0), 2)
            },
            **kwargs
        }
    
    @staticmethod
    def create_semantic_search_result(
        query: str,
        file_id: str,
        similarity_score: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create semantic search result fixture"""
        
        similarity_score = similarity_score or round(random.uniform(0.6, 0.98), 3)
        
        return {
            'id': str(uuid.uuid4()),
            'query': query,
            'file_id': file_id,
            'similarity_score': similarity_score,
            'rank': random.randint(1, 100),
            'snippet': fake.text(max_nb_chars=200),
            'highlighted_snippet': fake.text(max_nb_chars=200),
            'match_type': random.choice(['exact', 'semantic', 'fuzzy', 'conceptual']),
            'matched_chunks': random.randint(1, 5),
            'total_chunks': random.randint(5, 50),
            'file_metadata': {
                'name': fake.file_name(),
                'type': random.choice(['document', 'image', 'video', 'audio']),
                'size': random.randint(1024, 10 * 1024 * 1024),
                'created_at': fake.date_time_between(start_date='-1y', end_date='now')
            },
            'search_metadata': {
                'query_tokens': len(query.split()),
                'processing_time_ms': random.randint(10, 500),
                'model_used': random.choice(['text-embedding-ada-002', 'text-embedding-3-small']),
                'search_timestamp': fake.date_time_between(start_date='-1h', end_date='now')
            },
            **kwargs
        }
    
    @staticmethod
    def create_ai_analysis(
        file_id: str,
        analysis_type: str = "content_analysis",
        **kwargs
    ) -> Dict[str, Any]:
        """Create AI analysis result fixture"""
        
        base_analysis = {
            'id': str(uuid.uuid4()),
            'file_id': file_id,
            'analysis_type': analysis_type,
            'status': random.choice(['completed', 'processing', 'failed', 'queued']),
            'created_at': fake.date_time_between(start_date='-7d', end_date='now'),
            'completed_at': fake.date_time_between(start_date='-6d', end_date='now') if random.random() > 0.3 else None,
            'processing_time_ms': random.randint(500, 30000),
            'model_used': random.choice(['gpt-4', 'gpt-3.5-turbo', 'claude-3', 'gemini-pro']),
            'confidence_score': round(random.uniform(0.6, 0.95), 3),
            'cost_estimate': round(random.uniform(0.001, 0.1), 4),
            **kwargs
        }
        
        # Add type-specific results
        if analysis_type == "content_analysis":
            base_analysis['results'] = AIFixtures._generate_content_analysis()
        elif analysis_type == "sentiment_analysis":
            base_analysis['results'] = AIFixtures._generate_sentiment_analysis()
        elif analysis_type == "entity_extraction":
            base_analysis['results'] = AIFixtures._generate_entity_extraction()
        elif analysis_type == "topic_modeling":
            base_analysis['results'] = AIFixtures._generate_topic_modeling()
        elif analysis_type == "summarization":
            base_analysis['results'] = AIFixtures._generate_summarization()
        elif analysis_type == "translation":
            base_analysis['results'] = AIFixtures._generate_translation()
        elif analysis_type == "question_answering":
            base_analysis['results'] = AIFixtures._generate_question_answering()
        
        return base_analysis
    
    @staticmethod
    def _generate_content_analysis() -> Dict[str, Any]:
        """Generate content analysis results"""
        return {
            'word_count': random.randint(100, 10000),
            'character_count': random.randint(500, 50000),
            'paragraph_count': random.randint(5, 100),
            'sentence_count': random.randint(10, 500),
            'readability_score': round(random.uniform(5.0, 15.0), 1),
            'reading_level': random.choice(['elementary', 'middle_school', 'high_school', 'college', 'graduate']),
            'language': random.choice(['en', 'es', 'fr', 'de', 'ja']),
            'language_confidence': round(random.uniform(0.8, 1.0), 3),
            'key_phrases': fake.words(nb=10),
            'content_type': random.choice(['article', 'report', 'email', 'presentation', 'manual']),
            'formality_level': random.choice(['casual', 'neutral', 'formal', 'academic']),
            'complexity_score': round(random.uniform(0.1, 1.0), 2)
        }
    
    @staticmethod
    def _generate_sentiment_analysis() -> Dict[str, Any]:
        """Generate sentiment analysis results"""
        return {
            'overall_sentiment': random.choice(['positive', 'negative', 'neutral', 'mixed']),
            'sentiment_score': round(random.uniform(-1.0, 1.0), 3),
            'confidence': round(random.uniform(0.6, 0.95), 3),
            'emotions': {
                'joy': round(random.uniform(0.0, 1.0), 3),
                'anger': round(random.uniform(0.0, 1.0), 3),
                'fear': round(random.uniform(0.0, 1.0), 3),
                'sadness': round(random.uniform(0.0, 1.0), 3),
                'surprise': round(random.uniform(0.0, 1.0), 3),
                'disgust': round(random.uniform(0.0, 1.0), 3)
            },
            'subjectivity': round(random.uniform(0.0, 1.0), 3),
            'intensity': random.choice(['low', 'medium', 'high']),
            'sentiment_by_sentence': [
                {
                    'sentence': fake.sentence(),
                    'sentiment': random.choice(['positive', 'negative', 'neutral']),
                    'score': round(random.uniform(-1.0, 1.0), 3)
                } for _ in range(random.randint(3, 10))
            ]
        }
    
    @staticmethod
    def _generate_entity_extraction() -> Dict[str, Any]:
        """Generate entity extraction results"""
        entities = []
        
        entity_types = ['PERSON', 'ORG', 'GPE', 'DATE', 'MONEY', 'PERCENT', 'TIME', 'PRODUCT']
        
        for _ in range(random.randint(5, 20)):
            entity_type = random.choice(entity_types)
            if entity_type == 'PERSON':
                text = fake.name()
            elif entity_type == 'ORG':
                text = fake.company()
            elif entity_type == 'GPE':
                text = fake.city()
            elif entity_type == 'DATE':
                text = fake.date()
            elif entity_type == 'MONEY':
                text = f"${random.randint(100, 100000)}"
            elif entity_type == 'PERCENT':
                text = f"{random.randint(1, 100)}%"
            elif entity_type == 'TIME':
                text = fake.time()
            else:
                text = fake.catch_phrase()
            
            entities.append({
                'text': text,
                'type': entity_type,
                'confidence': round(random.uniform(0.7, 0.99), 3),
                'start_char': random.randint(0, 1000),
                'end_char': random.randint(1001, 2000),
                'context': fake.sentence()
            })
        
        return {
            'entities': entities,
            'entity_count': len(entities),
            'entity_types': list(set(e['type'] for e in entities)),
            'confidence_avg': round(np.mean([e['confidence'] for e in entities]), 3) if entities else 0
        }
    
    @staticmethod
    def _generate_topic_modeling() -> Dict[str, Any]:
        """Generate topic modeling results"""
        topics = []
        
        for i in range(random.randint(3, 8)):
            topics.append({
                'topic_id': i,
                'topic_name': fake.catch_phrase(),
                'keywords': fake.words(nb=10),
                'probability': round(random.uniform(0.05, 0.4), 3),
                'coherence_score': round(random.uniform(0.3, 0.8), 3),
                'representative_sentences': [fake.sentence() for _ in range(3)]
            })
        
        return {
            'topics': topics,
            'topic_count': len(topics),
            'model_type': random.choice(['LDA', 'NMF', 'BERTopic']),
            'coherence_score': round(random.uniform(0.4, 0.7), 3),
            'perplexity': round(random.uniform(20, 100), 2)
        }
    
    @staticmethod
    def _generate_summarization() -> Dict[str, Any]:
        """Generate summarization results"""
        return {
            'summary': fake.text(max_nb_chars=300),
            'summary_type': random.choice(['extractive', 'abstractive', 'hybrid']),
            'compression_ratio': round(random.uniform(0.1, 0.3), 2),
            'key_points': [fake.sentence() for _ in range(random.randint(3, 7))],
            'summary_quality': round(random.uniform(0.6, 0.9), 2),
            'relevance_score': round(random.uniform(0.7, 0.95), 3),
            'factual_consistency': round(random.uniform(0.8, 0.99), 3),
            'fluency_score': round(random.uniform(0.7, 0.95), 3)
        }
    
    @staticmethod
    def _generate_translation() -> Dict[str, Any]:
        """Generate translation results"""
        source_lang = random.choice(['en', 'es', 'fr', 'de', 'ja', 'zh'])
        target_lang = random.choice([l for l in ['en', 'es', 'fr', 'de', 'ja', 'zh'] if l != source_lang])
        
        return {
            'source_language': source_lang,
            'target_language': target_lang,
            'translated_text': fake.text(max_nb_chars=500),
            'confidence_score': round(random.uniform(0.8, 0.99), 3),
            'translation_quality': random.choice(['high', 'medium', 'low']),
            'model_used': random.choice(['google-translate', 'deepl', 'azure-translator']),
            'detected_language': source_lang,
            'language_detection_confidence': round(random.uniform(0.9, 1.0), 3)
        }
    
    @staticmethod
    def _generate_question_answering() -> Dict[str, Any]:
        """Generate question answering results"""
        qa_pairs = []
        
        for _ in range(random.randint(3, 8)):
            qa_pairs.append({
                'question': fake.sentence().rstrip('.') + '?',
                'answer': fake.sentence(),
                'confidence': round(random.uniform(0.6, 0.95), 3),
                'answer_type': random.choice(['extractive', 'generative', 'boolean', 'numerical']),
                'source_location': {
                    'start_char': random.randint(0, 1000),
                    'end_char': random.randint(1001, 2000)
                }
            })
        
        return {
            'qa_pairs': qa_pairs,
            'total_questions': len(qa_pairs),
            'avg_confidence': round(np.mean([qa['confidence'] for qa in qa_pairs]), 3) if qa_pairs else 0,
            'model_type': random.choice(['extractive', 'generative', 'hybrid'])
        }
    
    @staticmethod
    def create_ai_model_config(
        model_name: str,
        model_type: str = "language_model",
        **kwargs
    ) -> Dict[str, Any]:
        """Create AI model configuration fixture"""
        
        return {
            'id': str(uuid.uuid4()),
            'name': model_name,
            'type': model_type,
            'version': random.choice(['v1.0', 'v1.1', 'v2.0', 'v2.1', 'v3.0']),
            'provider': random.choice(['openai', 'anthropic', 'google', 'huggingface', 'local']),
            'status': random.choice(['active', 'inactive', 'deprecated', 'beta']),
            'created_at': fake.date_time_between(start_date='-2y', end_date='-30d'),
            'updated_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'config': {
                'max_tokens': random.choice([1000, 2000, 4000, 8000, 16000]),
                'temperature': round(random.uniform(0.0, 1.0), 2),
                'top_p': round(random.uniform(0.1, 1.0), 2),
                'frequency_penalty': round(random.uniform(0.0, 2.0), 2),
                'presence_penalty': round(random.uniform(0.0, 2.0), 2)
            },
            'capabilities': random.sample([
                'text_generation', 'text_completion', 'chat', 'translation',
                'summarization', 'sentiment_analysis', 'entity_extraction',
                'question_answering', 'code_generation', 'image_analysis'
            ], random.randint(2, 6)),
            'limitations': {
                'max_input_length': random.randint(1000, 100000),
                'rate_limit_per_minute': random.randint(10, 1000),
                'supported_languages': random.sample([
                    'en', 'es', 'fr', 'de', 'ja', 'zh', 'ko', 'pt', 'it', 'ru'
                ], random.randint(3, 8))
            },
            'performance_metrics': {
                'avg_response_time_ms': random.randint(100, 5000),
                'throughput_requests_per_second': round(random.uniform(0.1, 50.0), 1),
                'success_rate': round(random.uniform(0.95, 0.99), 3),
                'quality_score': round(random.uniform(0.7, 0.95), 2)
            },
            'cost_info': {
                'cost_per_1k_tokens': round(random.uniform(0.0001, 0.1), 6),
                'monthly_usage_limit': random.randint(100000, 10000000),
                'current_usage': random.randint(0, 100000)
            },
            **kwargs
        }
    
    @staticmethod
    def create_ai_plugin_config(
        plugin_name: str,
        plugin_type: str = "ai_service",
        **kwargs
    ) -> Dict[str, Any]:
        """Create AI plugin configuration fixture"""
        
        return {
            'id': str(uuid.uuid4()),
            'name': plugin_name,
            'type': plugin_type,
            'version': fake.bothify('#.#.#'),
            'enabled': fake.boolean(chance_of_getting_true=80),
            'created_at': fake.date_time_between(start_date='-1y', end_date='-7d'),
            'updated_at': fake.date_time_between(start_date='-7d', end_date='now'),
            'config': {
                'api_endpoint': fake.url(),
                'api_key': fake.sha256(),
                'timeout_seconds': random.randint(10, 120),
                'retry_count': random.randint(1, 5),
                'batch_size': random.randint(1, 100)
            },
            'supported_operations': random.sample([
                'text_analysis', 'image_recognition', 'audio_transcription',
                'translation', 'summarization', 'sentiment_analysis'
            ], random.randint(2, 4)),
            'health_check': {
                'last_check': fake.date_time_between(start_date='-1h', end_date='now'),
                'status': random.choice(['healthy', 'degraded', 'unhealthy']),
                'response_time_ms': random.randint(50, 2000),
                'error_rate': round(random.uniform(0.0, 0.1), 3)
            },
            **kwargs
        }
    
    @staticmethod
    def create_training_data(
        dataset_name: str,
        task_type: str = "classification",
        **kwargs
    ) -> Dict[str, Any]:
        """Create training data fixture"""
        
        sample_count = random.randint(100, 10000)
        
        return {
            'id': str(uuid.uuid4()),
            'name': dataset_name,
            'task_type': task_type,
            'created_at': fake.date_time_between(start_date='-6m', end_date='-30d'),
            'updated_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'sample_count': sample_count,
            'validation_split': round(random.uniform(0.1, 0.3), 2),
            'test_split': round(random.uniform(0.1, 0.3), 2),
            'features': {
                'input_type': random.choice(['text', 'image', 'audio', 'multimodal']),
                'output_type': random.choice(['classification', 'regression', 'generation']),
                'feature_count': random.randint(10, 1000),
                'avg_input_length': random.randint(50, 2000)
            },
            'quality_metrics': {
                'completeness': round(random.uniform(0.8, 1.0), 3),
                'consistency': round(random.uniform(0.7, 0.95), 3),
                'diversity': round(random.uniform(0.6, 0.9), 3),
                'balance_score': round(random.uniform(0.5, 1.0), 3)
            },
            'preprocessing': {
                'steps_applied': random.sample([
                    'tokenization', 'normalization', 'deduplication',
                    'filtering', 'augmentation', 'balancing'
                ], random.randint(2, 5)),
                'processing_time_hours': round(random.uniform(0.1, 24.0), 1)
            },
            'labels': {
                'label_count': random.randint(2, 50),
                'label_distribution': {
                    f"label_{i}": random.randint(10, sample_count // 5)
                    for i in range(random.randint(2, 10))
                }
            },
            **kwargs
        }
    
    @staticmethod
    def create_ai_usage_stats(
        user_id: Optional[str] = None,
        time_period: str = "monthly",
        **kwargs
    ) -> Dict[str, Any]:
        """Create AI usage statistics fixture"""
        
        user_id = user_id or str(uuid.uuid4())
        
        return {
            'user_id': user_id,
            'period': time_period,
            'start_date': fake.date_time_between(start_date='-30d', end_date='-15d'),
            'end_date': fake.date_time_between(start_date='-15d', end_date='now'),
            'requests': {
                'total_requests': random.randint(100, 10000),
                'successful_requests': random.randint(90, 9900),
                'failed_requests': random.randint(0, 100),
                'avg_requests_per_day': round(random.uniform(1.0, 100.0), 1)
            },
            'usage_by_service': {
                'semantic_search': random.randint(10, 1000),
                'content_analysis': random.randint(5, 500),
                'summarization': random.randint(5, 200),
                'translation': random.randint(0, 100),
                'sentiment_analysis': random.randint(0, 300)
            },
            'tokens': {
                'input_tokens': random.randint(1000, 1000000),
                'output_tokens': random.randint(500, 500000),
                'total_tokens': random.randint(1500, 1500000)
            },
            'performance': {
                'avg_response_time_ms': random.randint(200, 3000),
                'p95_response_time_ms': random.randint(1000, 8000),
                'success_rate': round(random.uniform(0.9, 0.99), 3),
                'avg_quality_score': round(random.uniform(0.7, 0.95), 3)
            },
            'costs': {
                'total_cost': round(random.uniform(1.0, 100.0), 2),
                'cost_per_request': round(random.uniform(0.001, 0.1), 4),
                'cost_breakdown': {
                    'api_calls': round(random.uniform(0.5, 50.0), 2),
                    'compute': round(random.uniform(0.2, 30.0), 2),
                    'storage': round(random.uniform(0.1, 10.0), 2)
                }
            },
            **kwargs
        }


class AIFactory:
    """Factory for creating complex AI scenarios"""
    
    def __init__(self):
        self.embeddings = []
        self.analyses = []
        self.models = []
        self.plugins = []
    
    def create_document_processing_pipeline(
        self,
        file_ids: List[str],
        analysis_types: List[str] = None
    ) -> Dict[str, Any]:
        """Create complete document processing pipeline"""
        
        analysis_types = analysis_types or [
            'content_analysis', 'sentiment_analysis', 'entity_extraction', 'summarization'
        ]
        
        results = {
            'files': file_ids,
            'embeddings': [],
            'analyses': [],
            'processing_stats': {
                'total_files': len(file_ids),
                'total_analyses': len(analysis_types) * len(file_ids),
                'start_time': fake.date_time_between(start_date='-2d', end_date='-1d'),
                'estimated_completion': fake.date_time_between(start_date='+1h', end_date='+6h')
            }
        }
        
        for file_id in file_ids:
            # Create embeddings
            for chunk in range(random.randint(1, 10)):
                embedding = AIFixtures.create_embedding(file_id=file_id)
                results['embeddings'].append(embedding)
                self.embeddings.append(embedding)
            
            # Create analyses
            for analysis_type in analysis_types:
                analysis = AIFixtures.create_ai_analysis(file_id, analysis_type)
                results['analyses'].append(analysis)
                self.analyses.append(analysis)
        
        return results
    
    def create_semantic_search_scenario(
        self,
        queries: List[str],
        file_ids: List[str]
    ) -> Dict[str, Any]:
        """Create semantic search scenario with results"""
        
        search_results = []
        
        for query in queries:
            query_results = []
            
            # Create results for each query
            for file_id in random.sample(file_ids, random.randint(1, min(10, len(file_ids)))):
                result = AIFixtures.create_semantic_search_result(query, file_id)
                query_results.append(result)
            
            # Sort by similarity score
            query_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            search_results.append({
                'query': query,
                'results': query_results,
                'result_count': len(query_results),
                'search_time_ms': random.randint(50, 1000)
            })
        
        return {
            'searches': search_results,
            'total_queries': len(queries),
            'total_results': sum(len(sr['results']) for sr in search_results),
            'avg_similarity': np.mean([
                r['similarity_score'] 
                for sr in search_results 
                for r in sr['results']
            ]) if search_results else 0
        }