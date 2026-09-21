"""
AI-powered video summary generation using multiple approaches
"""

import asyncio
import cv2
import numpy as np
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import hashlib
import re
from collections import Counter

from ..core.config import settings
from ..core.database import DatabaseManager
from ..models.video_models import VideoFile, ProcessingJob

ai_logger = logging.getLogger('ai_processing')

class VideoSummarizer:
    """AI-powered video summarization using multiple data sources"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # AI model configurations
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.use_local_model = os.getenv('USE_LOCAL_AI_MODEL', 'false').lower() == 'true'
        self.local_model_url = os.getenv('LOCAL_AI_MODEL_URL', 'http://localhost:11434')
        
        # Summary configurations
        self.max_tokens = 2000
        self.temperature = 0.3
        self.max_keyframes_for_analysis = 20
        
    async def generate_video_summary(self, job_id: str, video_path: str,
                                   summary_types: List[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive video summaries using multiple AI approaches
        
        Args:
            job_id: Processing job ID
            video_path: Path to video file
            summary_types: List of summary types to generate
            
        Returns:
            Dictionary containing all generated summaries and metadata
        """
        if summary_types is None:
            summary_types = ['comprehensive', 'scene_based', 'text_based', 'visual_based']
        
        try:
            ai_logger.info(f"Starting AI summary generation for job {job_id}: {video_path}")
            
            # Update job status
            await self.db_manager.update_job_status(job_id, 'processing', 
                                                  {'stage': 'ai_summary_generation'})
            
            # Gather all available data for the video
            video_data = await self._gather_video_data(job_id, video_path)
            
            # Generate different types of summaries
            summaries = {}
            
            for i, summary_type in enumerate(summary_types):
                try:
                    ai_logger.info(f"Generating {summary_type} summary...")
                    
                    if summary_type == 'comprehensive':
                        summary = await self._generate_comprehensive_summary(video_data)
                    elif summary_type == 'scene_based':
                        summary = await self._generate_scene_based_summary(video_data)
                    elif summary_type == 'text_based':
                        summary = await self._generate_text_based_summary(video_data)
                    elif summary_type == 'visual_based':
                        summary = await self._generate_visual_based_summary(video_data)
                    else:
                        continue
                    
                    summaries[summary_type] = summary
                    
                    # Save individual summary to database
                    await self._save_summary_to_db(job_id, summary_type, summary)
                    
                    # Update progress
                    progress = ((i + 1) / len(summary_types)) * 100
                    await self.db_manager.update_job_progress(job_id, progress)
                    
                except Exception as e:
                    ai_logger.warning(f"Failed to generate {summary_type} summary: {str(e)}")
                    summaries[summary_type] = {'error': str(e)}
            
            # Create final result
            result = {
                'job_id': job_id,
                'video_path': video_path,
                'processing_time': datetime.utcnow().isoformat(),
                'summaries': summaries,
                'statistics': await self._calculate_summary_statistics(summaries),
                'data_sources': self._get_data_source_info(video_data)
            }
            
            # Update job status
            await self.db_manager.update_job_status(job_id, 'completed', result)
            
            ai_logger.info(f"AI summary generation completed for job {job_id}")
            return result
            
        except Exception as e:
            ai_logger.error(f"AI summary generation failed for job {job_id}: {str(e)}")
            await self.db_manager.update_job_status(job_id, 'failed', {'error': str(e)})
            raise
    
    async def _gather_video_data(self, job_id: str, video_path: str) -> Dict[str, Any]:
        """Gather all available video processing data for analysis"""
        
        video_data = {
            'job_id': job_id,
            'video_path': video_path,
            'metadata': {},
            'keyframes': [],
            'scenes': [],
            'ocr_results': [],
            'text_timeline': []
        }
        
        try:
            # Get basic video metadata
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = total_frames / fps if fps > 0 else 0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                video_data['metadata'] = {
                    'duration': duration,
                    'fps': fps,
                    'total_frames': total_frames,
                    'width': width,
                    'height': height,
                    'aspect_ratio': width / height if height > 0 else 1.0
                }
                cap.release()
            
            # Get keyframes data
            keyframes = await self.db_manager.get_job_keyframes(job_id)
            video_data['keyframes'] = keyframes[:self.max_keyframes_for_analysis]
            
            # Get scenes data
            scenes = await self.db_manager.get_job_scenes(job_id)
            video_data['scenes'] = scenes
            
            # Get OCR results
            ocr_results = await self.db_manager.get_job_ocr_results(job_id)
            video_data['ocr_results'] = ocr_results
            
            # Get text timeline (if available from OCR processor)
            try:
                text_timeline = await self.db_manager.fetch_all("""
                    SELECT timestamp, text_content, confidence 
                    FROM video_text_timeline 
                    WHERE job_id = $1 
                    ORDER BY timestamp
                """, job_id)
                video_data['text_timeline'] = [dict(row) for row in text_timeline]
            except:
                pass
            
            ai_logger.info(f"Gathered data: {len(keyframes)} keyframes, {len(scenes)} scenes, {len(ocr_results)} OCR results")
            
        except Exception as e:
            ai_logger.warning(f"Error gathering video data: {str(e)}")
        
        return video_data
    
    async def _generate_comprehensive_summary(self, video_data: Dict) -> Dict[str, Any]:
        """Generate a comprehensive summary using all available data"""
        
        # Prepare context from all sources
        context = self._build_comprehensive_context(video_data)
        
        prompt = f"""
        Analyze this video and provide a comprehensive summary based on the following data:

        VIDEO METADATA:
        - Duration: {video_data['metadata'].get('duration', 0):.1f} seconds
        - Resolution: {video_data['metadata'].get('width', 0)}x{video_data['metadata'].get('height', 0)}
        - Total scenes detected: {len(video_data.get('scenes', []))}

        {context}

        Please provide a comprehensive summary that includes:
        1. Overall video content and purpose
        2. Key topics and themes discussed
        3. Important visual elements or scenes
        4. Main text content or messages shown
        5. Estimated target audience
        6. Notable features or highlights

        Keep the summary concise but informative (max 500 words).
        """
        
        summary_text = await self._call_ai_model(prompt)
        
        # Extract key topics and sentiment
        topics = await self._extract_key_topics(summary_text, video_data)
        sentiment = await self._analyze_sentiment(summary_text)
        
        return {
            'text': summary_text,
            'key_topics': topics,
            'sentiment_score': sentiment,
            'confidence': 0.85,
            'word_count': len(summary_text.split()),
            'data_sources_used': ['metadata', 'scenes', 'ocr', 'keyframes']
        }
    
    async def _generate_scene_based_summary(self, video_data: Dict) -> Dict[str, Any]:
        """Generate summary based on scene analysis"""
        
        scenes = video_data.get('scenes', [])
        if not scenes:
            return {
                'text': 'No scene data available for analysis.',
                'key_topics': [],
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'word_count': 0
            }
        
        # Build scene context
        scene_descriptions = []
        for i, scene in enumerate(scenes[:10]):  # Limit to top 10 scenes
            start_time = scene.get('start_time_seconds', 0)
            end_time = scene.get('end_time_seconds', 0)
            duration = scene.get('duration_seconds', 0)
            confidence = scene.get('confidence_score', 0)
            
            scene_desc = f"Scene {i+1} ({start_time:.1f}s - {end_time:.1f}s, {duration:.1f}s duration, {confidence:.2f} confidence)"
            if scene.get('description'):
                scene_desc += f": {scene['description']}"
            
            scene_descriptions.append(scene_desc)
        
        prompt = f"""
        Analyze this video based on the following scene breakdown:

        SCENES DETECTED:
        {chr(10).join(scene_descriptions)}

        VIDEO DURATION: {video_data['metadata'].get('duration', 0):.1f} seconds
        TOTAL SCENES: {len(scenes)}

        Based on this scene analysis, provide a summary that:
        1. Describes the video's structure and flow
        2. Identifies the main segments or parts
        3. Notes any significant scene transitions
        4. Estimates the video's pacing and style
        
        Keep the summary focused on the video's structure and content flow (max 300 words).
        """
        
        summary_text = await self._call_ai_model(prompt)
        topics = await self._extract_key_topics(summary_text, video_data)
        
        return {
            'text': summary_text,
            'key_topics': topics,
            'sentiment_score': 0.0,  # Neutral for structural analysis
            'confidence': 0.8,
            'word_count': len(summary_text.split()),
            'scenes_analyzed': len(scenes)
        }
    
    async def _generate_text_based_summary(self, video_data: Dict) -> Dict[str, Any]:
        """Generate summary based on extracted text content"""
        
        text_timeline = video_data.get('text_timeline', [])
        ocr_results = video_data.get('ocr_results', [])
        
        if not text_timeline and not ocr_results:
            return {
                'text': 'No text content detected in the video.',
                'key_topics': [],
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'word_count': 0
            }
        
        # Combine and analyze all text
        all_text = []
        
        for item in text_timeline:
            if item.get('confidence', 0) >= 50:  # Only high confidence text
                all_text.append(f"[{item.get('timestamp', 0):.1f}s] {item.get('text_content', '')}")
        
        # Get unique text content and word frequencies
        text_content = ' '.join([item.get('text_content', '') for item in text_timeline])
        words = re.findall(r'\b\w+\b', text_content.lower())
        word_freq = Counter(words)
        common_words = [word for word, count in word_freq.most_common(20) if len(word) > 3]
        
        prompt = f"""
        Analyze this video based on the text content that appears in it:

        TEXT CONTENT TIMELINE:
        {chr(10).join(all_text[:50])}  # Limit to prevent too long prompts
        
        MOST COMMON WORDS: {', '.join(common_words[:15])}
        TOTAL TEXT INSTANCES: {len(text_timeline)}

        Based on this text analysis, provide a summary that:
        1. Identifies the main topics or subjects discussed
        2. Notes any important information or messages shown
        3. Describes what type of content this appears to be
        4. Highlights key terms or concepts
        
        Focus on what the text content reveals about the video's purpose and message (max 300 words).
        """
        
        summary_text = await self._call_ai_model(prompt)
        topics = common_words[:10]  # Use common words as topics
        sentiment = await self._analyze_text_sentiment(text_content)
        
        return {
            'text': summary_text,
            'key_topics': topics,
            'sentiment_score': sentiment,
            'confidence': 0.9 if text_timeline else 0.3,
            'word_count': len(summary_text.split()),
            'text_instances_analyzed': len(text_timeline)
        }
    
    async def _generate_visual_based_summary(self, video_data: Dict) -> Dict[str, Any]:
        """Generate summary based on visual analysis of keyframes"""
        
        keyframes = video_data.get('keyframes', [])
        if not keyframes:
            return {
                'text': 'No keyframes available for visual analysis.',
                'key_topics': [],
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'word_count': 0
            }
        
        # Analyze keyframe features
        visual_features = []
        timestamps = []
        
        for kf in keyframes[:15]:  # Analyze top 15 keyframes
            timestamp = kf.get('timestamp_seconds', 0)
            confidence = kf.get('confidence_score', 0)
            features = kf.get('features', {})
            
            timestamps.append(timestamp)
            
            feature_desc = f"Frame at {timestamp:.1f}s (confidence: {confidence:.2f})"
            if features:
                if 'dominant_colors' in features:
                    feature_desc += f" - Colors: {features.get('dominant_colors', [])[:3]}"
                if 'brightness' in features:
                    feature_desc += f" - Brightness: {features.get('brightness', 0):.2f}"
            
            visual_features.append(feature_desc)
        
        # Calculate video visual characteristics
        duration = video_data['metadata'].get('duration', 0)
        frame_density = len(keyframes) / duration if duration > 0 else 0
        
        prompt = f"""
        Analyze this video based on visual keyframe analysis:

        KEYFRAMES ANALYZED:
        {chr(10).join(visual_features)}
        
        VISUAL CHARACTERISTICS:
        - Video duration: {duration:.1f} seconds
        - Keyframes extracted: {len(keyframes)}
        - Frame density: {frame_density:.2f} keyframes/second
        - Resolution: {video_data['metadata'].get('width', 0)}x{video_data['metadata'].get('height', 0)}

        Based on this visual analysis, provide a summary that:
        1. Describes the overall visual style and quality
        2. Notes any patterns in the visual content
        3. Identifies the likely video type (presentation, tutorial, entertainment, etc.)
        4. Comments on production quality and visual characteristics
        
        Focus on visual aspects and production qualities (max 250 words).
        """
        
        summary_text = await self._call_ai_model(prompt)
        
        # Extract visual topics
        visual_topics = ['visual_content', 'keyframes', 'video_quality']
        if frame_density > 0.5:
            visual_topics.append('high_activity')
        elif frame_density < 0.1:
            visual_topics.append('static_content')
        
        return {
            'text': summary_text,
            'key_topics': visual_topics,
            'sentiment_score': 0.0,  # Neutral for visual analysis
            'confidence': 0.7,
            'word_count': len(summary_text.split()),
            'keyframes_analyzed': len(keyframes)
        }
    
    def _build_comprehensive_context(self, video_data: Dict) -> str:
        """Build comprehensive context from all video data"""
        
        context_parts = []
        
        # Scene information
        scenes = video_data.get('scenes', [])
        if scenes:
            scene_info = f"SCENES ({len(scenes)} detected):\n"
            for i, scene in enumerate(scenes[:5]):
                start = scene.get('start_time_seconds', 0)
                end = scene.get('end_time_seconds', 0)
                scene_info += f"- Scene {i+1}: {start:.1f}s - {end:.1f}s\n"
            context_parts.append(scene_info)
        
        # Text content
        text_timeline = video_data.get('text_timeline', [])
        if text_timeline:
            high_conf_text = [item for item in text_timeline if item.get('confidence', 0) >= 60]
            if high_conf_text:
                text_info = f"TEXT CONTENT (high confidence):\n"
                for item in high_conf_text[:10]:
                    timestamp = item.get('timestamp', 0)
                    text = item.get('text_content', '')
                    text_info += f"- [{timestamp:.1f}s] {text}\n"
                context_parts.append(text_info)
        
        # Keyframe information
        keyframes = video_data.get('keyframes', [])
        if keyframes:
            kf_info = f"KEYFRAMES ({len(keyframes)} extracted):\n"
            kf_info += f"- Sampling from {keyframes[0].get('timestamp_seconds', 0):.1f}s to {keyframes[-1].get('timestamp_seconds', 0):.1f}s\n"
            context_parts.append(kf_info)
        
        return '\n'.join(context_parts)
    
    async def _call_ai_model(self, prompt: str) -> str:
        """Call AI model for text generation"""
        
        try:
            if self.use_local_model:
                return await self._call_local_model(prompt)
            elif self.openai_api_key:
                return await self._call_openai(prompt)
            elif self.anthropic_api_key:
                return await self._call_anthropic(prompt)
            else:
                # Fallback to rule-based summary
                return await self._generate_rule_based_summary(prompt)
                
        except Exception as e:
            ai_logger.warning(f"AI model call failed: {str(e)}")
            return await self._generate_rule_based_summary(prompt)
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI GPT model"""
        
        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.max_tokens,
            'temperature': self.temperature
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
                    return result['choices'][0]['message']['content']
                else:
                    raise Exception(f"OpenAI API error: {response.status}")
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude model"""
        
        headers = {
            'x-api-key': self.anthropic_api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        data = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
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
                    return result['content'][0]['text']
                else:
                    raise Exception(f"Anthropic API error: {response.status}")
    
    async def _call_local_model(self, prompt: str) -> str:
        """Call local AI model (e.g., Ollama)"""
        
        data = {
            'model': 'llama2',
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': self.temperature,
                'num_predict': self.max_tokens
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.local_model_url}/api/generate',
                json=data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['response']
                else:
                    raise Exception(f"Local model API error: {response.status}")
    
    async def _generate_rule_based_summary(self, prompt: str) -> str:
        """Generate basic rule-based summary when AI models are unavailable"""
        
        # Extract key information from prompt
        lines = prompt.split('\n')
        
        summary_parts = []
        
        # Look for duration
        for line in lines:
            if 'Duration:' in line:
                summary_parts.append(f"This video has a duration of {line.split('Duration:')[1].strip()}.")
                break
        
        # Look for scene information
        scene_count = 0
        for line in lines:
            if 'Total scenes detected:' in line:
                try:
                    scene_count = int(line.split(':')[1].strip())
                    summary_parts.append(f"The video contains {scene_count} distinct scenes or segments.")
                except:
                    pass
                break
        
        # Look for text content
        if 'TEXT CONTENT' in prompt:
            summary_parts.append("The video contains visible text content that may include titles, captions, or on-screen information.")
        
        # Look for keyframes
        if 'KEYFRAMES' in prompt:
            summary_parts.append("Visual analysis shows multiple keyframes extracted for content analysis.")
        
        # Default summary if nothing specific found
        if not summary_parts:
            summary_parts.append("This appears to be a video file that has been processed for analysis.")
        
        return ' '.join(summary_parts)
    
    async def _extract_key_topics(self, summary_text: str, video_data: Dict) -> List[str]:
        """Extract key topics from summary and video data"""
        
        topics = []
        
        # Extract from summary text
        summary_words = re.findall(r'\b[A-Za-z]{4,}\b', summary_text.lower())
        word_freq = Counter(summary_words)
        
        # Common video-related terms to prioritize
        video_terms = {'video', 'content', 'scene', 'visual', 'audio', 'text', 'tutorial', 
                      'presentation', 'educational', 'entertainment', 'documentary', 'review'}
        
        for word, freq in word_freq.most_common(20):
            if word in video_terms or freq > 2:
                topics.append(word)
        
        # Add topics from OCR text if available
        text_timeline = video_data.get('text_timeline', [])
        if text_timeline:
            all_text = ' '.join([item.get('text_content', '') for item in text_timeline])
            text_words = re.findall(r'\b[A-Za-z]{4,}\b', all_text.lower())
            text_freq = Counter(text_words)
            
            for word, freq in text_freq.most_common(10):
                if freq > 2 and word not in topics:
                    topics.append(word)
        
        return topics[:15]  # Limit to top 15 topics
    
    async def _analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis (returns score between -1.0 and 1.0)"""
        
        positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 
                         'positive', 'helpful', 'useful', 'informative', 'clear', 'professional'}
        negative_words = {'bad', 'terrible', 'awful', 'poor', 'negative', 'confusing', 
                         'unclear', 'difficult', 'problem', 'error', 'fail', 'wrong'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        if positive_count + negative_count == 0:
            return 0.0
        
        return (positive_count - negative_count) / (positive_count + negative_count)
    
    async def _analyze_text_sentiment(self, text: str) -> float:
        """Analyze sentiment of extracted text content"""
        return await self._analyze_sentiment(text)
    
    async def _save_summary_to_db(self, job_id: str, summary_type: str, summary: Dict):
        """Save individual summary to database"""
        
        try:
            await self.db_manager.save_video_summary(
                job_id=job_id,
                summary_type=summary_type,
                summary_text=summary['text'],
                confidence=summary.get('confidence', 0.5),
                key_topics=summary.get('key_topics', []),
                sentiment=summary.get('sentiment_score', 0.0),
                language='en'
            )
            
            ai_logger.info(f"Saved {summary_type} summary to database for job {job_id}")
            
        except Exception as e:
            ai_logger.error(f"Failed to save {summary_type} summary: {str(e)}")
    
    async def _calculate_summary_statistics(self, summaries: Dict) -> Dict[str, Any]:
        """Calculate statistics across all summaries"""
        
        total_summaries = len([s for s in summaries.values() if isinstance(s, dict) and 'text' in s])
        total_words = sum([s.get('word_count', 0) for s in summaries.values() if isinstance(s, dict)])
        
        avg_confidence = 0
        confidence_values = [s.get('confidence', 0) for s in summaries.values() if isinstance(s, dict)]
        if confidence_values:
            avg_confidence = sum(confidence_values) / len(confidence_values)
        
        # Aggregate topics
        all_topics = []
        for summary in summaries.values():
            if isinstance(summary, dict) and 'key_topics' in summary:
                all_topics.extend(summary['key_topics'])
        
        topic_freq = Counter(all_topics)
        top_topics = [topic for topic, count in topic_freq.most_common(10)]
        
        return {
            'total_summaries_generated': total_summaries,
            'total_word_count': total_words,
            'average_confidence': avg_confidence,
            'top_topics': top_topics,
            'summary_types': list(summaries.keys())
        }
    
    def _get_data_source_info(self, video_data: Dict) -> Dict[str, Any]:
        """Get information about data sources used"""
        
        return {
            'keyframes_available': len(video_data.get('keyframes', [])),
            'scenes_available': len(video_data.get('scenes', [])),
            'ocr_results_available': len(video_data.get('ocr_results', [])),
            'text_timeline_available': len(video_data.get('text_timeline', [])),
            'metadata_available': bool(video_data.get('metadata'))
        }
    
    async def get_video_summaries(self, job_id: str) -> List[Dict]:
        """Get all summaries for a video"""
        
        try:
            summaries = await self.db_manager.fetch_all("""
                SELECT summary_type, summary_text, confidence_score, 
                       key_topics, sentiment_score, word_count, created_at
                FROM video_summaries
                WHERE job_id = $1
                ORDER BY created_at DESC
            """, job_id)
            
            return [dict(row) for row in summaries]
            
        except Exception as e:
            ai_logger.error(f"Failed to get summaries for job {job_id}: {str(e)}")
            return []
    
    async def search_videos_by_summary(self, query: str, limit: int = 20) -> List[Dict]:
        """Search videos by summary content"""
        
        try:
            results = await self.db_manager.fetch_all("""
                SELECT 
                    vs.job_id,
                    vpj.original_filename,
                    vs.summary_type,
                    vs.summary_text,
                    vs.confidence_score,
                    vs.key_topics,
                    vs.created_at
                FROM video_summaries vs
                JOIN video_processing_jobs vpj ON vs.job_id = vpj.job_id
                WHERE 
                    vs.summary_text ILIKE $1 
                    OR $1 = ANY(vs.key_topics)
                ORDER BY vs.confidence_score DESC, vs.created_at DESC
                LIMIT $2
            """, f"%{query}%", limit)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            ai_logger.error(f"Summary search failed: {str(e)}")
            return []