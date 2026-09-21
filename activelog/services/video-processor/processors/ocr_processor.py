"""
OCR processor for extracting text from video frames using Tesseract
"""

import asyncio
import cv2
import numpy as np
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import pytesseract
import json
import hashlib
from PIL import Image, ImageEnhance, ImageFilter
import re
from concurrent.futures import ThreadPoolExecutor
import logging

from ..core.config import settings
from ..core.database import DatabaseManager
from ..models.video_models import VideoFile, ProcessingJob

ocr_logger = logging.getLogger('ocr')

class OCRProcessor:
    """OCR processor for extracting text from video frames"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)
        
        # OCR configuration
        self.tesseract_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,!?-:;()[]{}@#$%^&*+=<>/\|_'
        
        # Text detection thresholds
        self.min_confidence = 30
        self.min_text_length = 3
        self.max_text_length = 500
        
    async def process_video_ocr(self, job_id: str, video_path: str, 
                               frame_interval: float = 2.0,
                               confidence_threshold: int = 30,
                               languages: str = 'eng') -> Dict[str, Any]:
        """
        Extract text from video frames using OCR
        
        Args:
            job_id: Processing job ID
            video_path: Path to video file
            frame_interval: Interval between frames to process (seconds)
            confidence_threshold: Minimum OCR confidence score
            languages: Tesseract language codes (e.g., 'eng', 'eng+spa')
            
        Returns:
            Dictionary containing OCR results and metadata
        """
        try:
            ocr_logger.info(f"Starting OCR processing for job {job_id}: {video_path}")
            
            # Update job status
            await self.db_manager.update_job_status(job_id, 'processing', 
                                                  {'stage': 'ocr_extraction'})
            
            # Open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            
            # Calculate frame indices to process
            frame_step = int(fps * frame_interval)
            frame_indices = list(range(0, total_frames, frame_step))
            
            ocr_logger.info(f"Processing {len(frame_indices)} frames at {frame_interval}s intervals")
            
            # Process frames for text extraction
            ocr_results = []
            text_timeline = []
            unique_texts = set()
            
            for i, frame_idx in enumerate(frame_indices):
                try:
                    # Set frame position
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    
                    if not ret:
                        continue
                    
                    timestamp = frame_idx / fps
                    
                    # Extract text from frame
                    frame_text = await self._extract_text_from_frame(
                        frame, timestamp, confidence_threshold, languages
                    )
                    
                    if frame_text:
                        ocr_results.extend(frame_text)
                        
                        # Add to timeline
                        for text_data in frame_text:
                            text_timeline.append({
                                'timestamp': timestamp,
                                'text': text_data['text'],
                                'confidence': text_data['confidence'],
                                'bbox': text_data['bbox']
                            })
                            unique_texts.add(text_data['text'].strip().lower())
                    
                    # Update progress
                    progress = (i + 1) / len(frame_indices) * 100
                    if i % 10 == 0:
                        await self.db_manager.update_job_progress(job_id, progress)
                        ocr_logger.info(f"OCR progress: {progress:.1f}%")
                        
                except Exception as e:
                    ocr_logger.warning(f"Error processing frame {frame_idx}: {str(e)}")
                    continue
            
            cap.release()
            
            # Generate text analytics
            analytics = await self._analyze_extracted_text(ocr_results, duration)
            
            # Create final result
            result = {
                'job_id': job_id,
                'video_path': video_path,
                'processing_time': datetime.utcnow().isoformat(),
                'settings': {
                    'frame_interval': frame_interval,
                    'confidence_threshold': confidence_threshold,
                    'languages': languages
                },
                'statistics': {
                    'total_frames_processed': len(frame_indices),
                    'text_instances_found': len(ocr_results),
                    'unique_texts': len(unique_texts),
                    'video_duration': duration
                },
                'ocr_results': ocr_results,
                'text_timeline': text_timeline,
                'analytics': analytics,
                'unique_texts': list(unique_texts)
            }
            
            # Save results to database
            await self._save_ocr_results(job_id, result)
            
            # Update job status
            await self.db_manager.update_job_status(job_id, 'completed', result)
            
            ocr_logger.info(f"OCR processing completed for job {job_id}")
            return result
            
        except Exception as e:
            ocr_logger.error(f"OCR processing failed for job {job_id}: {str(e)}")
            await self.db_manager.update_job_status(job_id, 'failed', {'error': str(e)})
            raise
    
    async def _extract_text_from_frame(self, frame: np.ndarray, timestamp: float,
                                     confidence_threshold: int, languages: str) -> List[Dict]:
        """Extract text from a single frame using multiple preprocessing methods"""
        
        # Try multiple preprocessing approaches
        preprocessing_methods = [
            self._preprocess_basic,
            self._preprocess_high_contrast,
            self._preprocess_denoised,
            self._preprocess_edges
        ]
        
        all_texts = []
        
        for method in preprocessing_methods:
            try:
                # Preprocess frame
                processed_frame = method(frame)
                
                # Run OCR in thread pool
                loop = asyncio.get_event_loop()
                texts = await loop.run_in_executor(
                    self.executor,
                    self._run_tesseract_ocr,
                    processed_frame,
                    confidence_threshold,
                    languages
                )
                
                # Add method info to results
                for text_data in texts:
                    text_data.update({
                        'timestamp': timestamp,
                        'preprocessing_method': method.__name__
                    })
                
                all_texts.extend(texts)
                
            except Exception as e:
                ocr_logger.warning(f"OCR preprocessing method {method.__name__} failed: {str(e)}")
                continue
        
        # Remove duplicates and filter results
        return self._filter_and_deduplicate_texts(all_texts)
    
    def _preprocess_basic(self, frame: np.ndarray) -> np.ndarray:
        """Basic preprocessing: grayscale and slight blur"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (3, 3), 0)
    
    def _preprocess_high_contrast(self, frame: np.ndarray) -> np.ndarray:
        """High contrast preprocessing for better text visibility"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # CLAHE for adaptive histogram equalization
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Morphological operations to clean up text
        kernel = np.ones((2, 2), np.uint8)
        enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
        
        return enhanced
    
    def _preprocess_denoised(self, frame: np.ndarray) -> np.ndarray:
        """Denoised preprocessing for cleaner text extraction"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Non-local means denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Bilateral filter for edge preservation
        filtered = cv2.bilateralFilter(denoised, 9, 75, 75)
        
        return filtered
    
    def _preprocess_edges(self, frame: np.ndarray) -> np.ndarray:
        """Edge-based preprocessing to highlight text regions"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def _run_tesseract_ocr(self, image: np.ndarray, confidence_threshold: int, 
                          languages: str) -> List[Dict]:
        """Run Tesseract OCR on preprocessed image"""
        
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image)
            
            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                pil_image, 
                lang=languages,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )
            
            texts = []
            
            # Process OCR results
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                # Filter based on confidence and text quality
                if (confidence >= confidence_threshold and 
                    len(text) >= self.min_text_length and
                    len(text) <= self.max_text_length and
                    self._is_valid_text(text)):
                    
                    texts.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': {
                            'x': int(ocr_data['left'][i]),
                            'y': int(ocr_data['top'][i]),
                            'width': int(ocr_data['width'][i]),
                            'height': int(ocr_data['height'][i])
                        },
                        'word_num': int(ocr_data['word_num'][i]),
                        'line_num': int(ocr_data['line_num'][i]),
                        'par_num': int(ocr_data['par_num'][i])
                    })
            
            return texts
            
        except Exception as e:
            ocr_logger.warning(f"Tesseract OCR failed: {str(e)}")
            return []
    
    def _is_valid_text(self, text: str) -> bool:
        """Validate if extracted text is meaningful"""
        
        # Remove common OCR artifacts
        if not text or text.isspace():
            return False
        
        # Check for minimum alphabetic content
        alpha_count = sum(c.isalpha() for c in text)
        if alpha_count == 0:
            return False
        
        # Filter out single characters (unless numbers)
        if len(text) == 1 and not text.isdigit():
            return False
        
        # Filter out common OCR noise patterns
        noise_patterns = [
            r'^[^\w\s]+$',  # Only special characters
            r'^[\s\-_\.]+$',  # Only whitespace and basic punctuation
            r'^[IL1l\|]+$',  # Common OCR confusion characters
        ]
        
        for pattern in noise_patterns:
            if re.match(pattern, text):
                return False
        
        return True
    
    def _filter_and_deduplicate_texts(self, texts: List[Dict]) -> List[Dict]:
        """Filter and remove duplicate text extractions"""
        
        if not texts:
            return []
        
        # Group by text content and keep highest confidence
        text_groups = {}
        
        for text_data in texts:
            text_key = text_data['text'].strip().lower()
            
            if text_key not in text_groups:
                text_groups[text_key] = text_data
            else:
                # Keep the one with higher confidence
                if text_data['confidence'] > text_groups[text_key]['confidence']:
                    text_groups[text_key] = text_data
        
        # Sort by confidence (descending)
        filtered_texts = sorted(
            text_groups.values(), 
            key=lambda x: x['confidence'], 
            reverse=True
        )
        
        return filtered_texts
    
    async def _analyze_extracted_text(self, ocr_results: List[Dict], 
                                    video_duration: float) -> Dict[str, Any]:
        """Analyze extracted text for patterns and insights"""
        
        if not ocr_results:
            return {'text_density': 0, 'common_words': [], 'text_regions': []}
        
        # Text density analysis
        text_density = len(ocr_results) / video_duration if video_duration > 0 else 0
        
        # Word frequency analysis
        word_freq = {}
        all_words = []
        
        for result in ocr_results:
            words = re.findall(r'\b\w+\b', result['text'].lower())
            all_words.extend(words)
            
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get most common words (excluding short words)
        common_words = [
            {'word': word, 'count': count} 
            for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
            if len(word) > 3
        ]
        
        # Text region analysis (clustering by location)
        text_regions = self._analyze_text_regions(ocr_results)
        
        # Confidence distribution
        confidences = [result['confidence'] for result in ocr_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'text_density': text_density,
            'total_words': len(all_words),
            'unique_words': len(word_freq),
            'common_words': common_words,
            'text_regions': text_regions,
            'average_confidence': avg_confidence,
            'confidence_distribution': {
                'high_confidence': len([c for c in confidences if c >= 80]),
                'medium_confidence': len([c for c in confidences if 50 <= c < 80]),
                'low_confidence': len([c for c in confidences if c < 50])
            }
        }
    
    def _analyze_text_regions(self, ocr_results: List[Dict]) -> List[Dict]:
        """Analyze common text regions in video frames"""
        
        regions = {}
        
        for result in ocr_results:
            bbox = result['bbox']
            
            # Create region key based on approximate position
            region_x = (bbox['x'] // 100) * 100  # Group by 100px regions
            region_y = (bbox['y'] // 100) * 100
            region_key = f"{region_x}_{region_y}"
            
            if region_key not in regions:
                regions[region_key] = {
                    'x_range': [region_x, region_x + 100],
                    'y_range': [region_y, region_y + 100],
                    'text_count': 0,
                    'avg_confidence': 0,
                    'sample_texts': []
                }
            
            region = regions[region_key]
            region['text_count'] += 1
            region['avg_confidence'] = (region['avg_confidence'] * (region['text_count'] - 1) + 
                                      result['confidence']) / region['text_count']
            
            if len(region['sample_texts']) < 5:
                region['sample_texts'].append(result['text'])
        
        # Sort regions by text frequency
        return sorted(regions.values(), key=lambda x: x['text_count'], reverse=True)[:10]
    
    async def _save_ocr_results(self, job_id: str, results: Dict[str, Any]):
        """Save OCR results to database"""
        
        try:
            # Save main results
            await self.db_manager.execute_query("""
                INSERT INTO ocr_results (
                    job_id, video_path, total_frames_processed, 
                    text_instances_found, unique_texts_count,
                    average_confidence, processing_settings, results_json
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (job_id) DO UPDATE SET
                    total_frames_processed = EXCLUDED.total_frames_processed,
                    text_instances_found = EXCLUDED.text_instances_found,
                    unique_texts_count = EXCLUDED.unique_texts_count,
                    average_confidence = EXCLUDED.average_confidence,
                    processing_settings = EXCLUDED.processing_settings,
                    results_json = EXCLUDED.results_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                job_id,
                results['video_path'],
                results['statistics']['total_frames_processed'],
                results['statistics']['text_instances_found'],
                results['statistics']['unique_texts'],
                results['analytics']['average_confidence'],
                json.dumps(results['settings']),
                json.dumps(results)
            ))
            
            # Save individual text extractions for searchability
            for text_item in results['text_timeline']:
                await self.db_manager.execute_query("""
                    INSERT INTO video_text_timeline (
                        job_id, timestamp, text_content, confidence,
                        bbox_x, bbox_y, bbox_width, bbox_height
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (job_id, timestamp, text_content) DO NOTHING
                """, (
                    job_id,
                    text_item['timestamp'],
                    text_item['text'],
                    text_item['confidence'],
                    text_item['bbox']['x'],
                    text_item['bbox']['y'],
                    text_item['bbox']['width'],
                    text_item['bbox']['height']
                ))
            
            ocr_logger.info(f"OCR results saved to database for job {job_id}")
            
        except Exception as e:
            ocr_logger.error(f"Failed to save OCR results for job {job_id}: {str(e)}")
            raise
    
    async def search_video_text(self, query: str, confidence_threshold: int = 50,
                               limit: int = 100) -> List[Dict]:
        """Search for text content across all processed videos"""
        
        try:
            results = await self.db_manager.fetch_all("""
                SELECT 
                    vtt.job_id,
                    vf.filename,
                    vtt.timestamp,
                    vtt.text_content,
                    vtt.confidence,
                    vtt.bbox_x, vtt.bbox_y, vtt.bbox_width, vtt.bbox_height
                FROM video_text_timeline vtt
                JOIN processing_jobs pj ON vtt.job_id = pj.id
                JOIN video_files vf ON pj.video_file_id = vf.id
                WHERE 
                    vtt.text_content ILIKE $1
                    AND vtt.confidence >= $2
                    AND pj.status = 'completed'
                ORDER BY vtt.confidence DESC, vtt.timestamp ASC
                LIMIT $3
            """, (f"%{query}%", confidence_threshold, limit))
            
            return [dict(row) for row in results]
            
        except Exception as e:
            ocr_logger.error(f"Text search failed: {str(e)}")
            return []
    
    async def get_video_text_timeline(self, job_id: str) -> List[Dict]:
        """Get complete text timeline for a video"""
        
        try:
            results = await self.db_manager.fetch_all("""
                SELECT 
                    timestamp, text_content, confidence,
                    bbox_x, bbox_y, bbox_width, bbox_height
                FROM video_text_timeline
                WHERE job_id = $1
                ORDER BY timestamp ASC
            """, (job_id,))
            
            return [dict(row) for row in results]
            
        except Exception as e:
            ocr_logger.error(f"Failed to get text timeline for job {job_id}: {str(e)}")
            return []