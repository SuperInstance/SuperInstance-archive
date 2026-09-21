"""
Advanced video analysis using AI and computer vision
"""
import asyncio
import cv2
import json
import numpy as np
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple

import easyocr
import librosa
import torch
import whisper
from PIL import Image
from transformers import pipeline
import structlog

from config.settings import settings

logger = structlog.get_logger()


class VideoAnalysisService:
    """
    Comprehensive video analysis service using multiple AI models
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._models = {}
        self._init_models()
        
    def _init_models(self):
        """Initialize AI models"""
        try:
            # OCR model
            if settings.enable_ocr:
                self._models["ocr"] = easyocr.Reader(settings.ocr_languages)
                
            # Speech-to-text model
            if settings.enable_speech_to_text:
                self._models["whisper"] = whisper.load_model(settings.whisper_model)
                
            # Sentiment analysis
            if settings.enable_sentiment_analysis:
                self._models["sentiment"] = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    device=0 if self.device == "cuda" else -1
                )
                
            # Object detection (using YOLO if available)
            if settings.enable_object_detection:
                try:
                    # Try to load YOLOv5 model
                    self._models["yolo"] = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                    self._models["yolo"].to(self.device)
                except Exception as e:
                    logger.warning("Failed to load YOLO model", error=str(e))
                    
            logger.info("Analysis models initialized", 
                       device=self.device,
                       models=list(self._models.keys()))
                       
        except Exception as e:
            logger.error("Failed to initialize analysis models", error=str(e))

    async def analyze_video_comprehensive(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive video analysis including all enabled features
        """
        start_time = datetime.utcnow()
        analysis_results = {
            "video_path": video_path,
            "analysis_start": start_time.isoformat(),
            "scene_analysis": {},
            "object_detection": {},
            "face_detection": {},
            "ocr_results": {},
            "speech_analysis": {},
            "sentiment_analysis": {},
            "content_classification": {},
            "quality_assessment": {},
            "technical_analysis": {}
        }
        
        try:
            # Get video metadata
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            analysis_results["video_metadata"] = {
                "total_frames": total_frames,
                "fps": fps,
                "duration": duration,
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else 0,
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if cap.isOpened() else 0
            }
            
            # Run analysis tasks in parallel where possible
            analysis_tasks = []
            
            # Scene detection
            if settings.enable_scene_detection:
                analysis_tasks.append(
                    self._run_scene_analysis(video_path, progress_callback)
                )
                
            # Object detection
            if settings.enable_object_detection and "yolo" in self._models:
                analysis_tasks.append(
                    self._run_object_detection(video_path, progress_callback)
                )
                
            # Face detection
            if settings.enable_face_detection:
                analysis_tasks.append(
                    self._run_face_detection(video_path, progress_callback)
                )
                
            # OCR analysis
            if settings.enable_ocr and "ocr" in self._models:
                analysis_tasks.append(
                    self._run_ocr_analysis(video_path, progress_callback)
                )
                
            # Audio analysis (speech-to-text and sentiment)
            if settings.enable_speech_to_text or settings.enable_sentiment_analysis:
                analysis_tasks.append(
                    self._run_audio_analysis(video_path, progress_callback)
                )
                
            # Run all tasks
            if analysis_tasks:
                results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Analysis task {i} failed", error=str(result))
                    elif isinstance(result, dict):
                        # Merge results based on task type
                        if "scenes" in result:
                            analysis_results["scene_analysis"] = result
                        elif "objects" in result:
                            analysis_results["object_detection"] = result
                        elif "faces" in result:
                            analysis_results["face_detection"] = result
                        elif "text_segments" in result:
                            analysis_results["ocr_results"] = result
                        elif "transcripts" in result or "sentiment" in result:
                            analysis_results["speech_analysis"] = result
                            
            # Content classification
            analysis_results["content_classification"] = await self._classify_content(analysis_results)
            
            # Quality assessment
            analysis_results["quality_assessment"] = await self._assess_video_quality(video_path)
            
            # Technical analysis
            analysis_results["technical_analysis"] = await self._technical_analysis(video_path)
            
            # Generate summary
            analysis_results["summary"] = self._generate_analysis_summary(analysis_results)
            
            end_time = datetime.utcnow()
            analysis_results["analysis_end"] = end_time.isoformat()
            analysis_results["total_analysis_time"] = (end_time - start_time).total_seconds()
            
            logger.info("Comprehensive video analysis completed",
                       video_path=video_path,
                       analysis_time=(end_time - start_time).total_seconds())
            
            return analysis_results
            
        except Exception as e:
            logger.error("Comprehensive video analysis failed",
                        video_path=video_path,
                        error=str(e))
            analysis_results["error"] = str(e)
            return analysis_results

    async def _run_scene_analysis(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Detect and analyze scenes in video"""
        try:
            scenes = []
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {"scenes": []}
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            prev_frame = None
            scene_start = 0
            current_scene_frames = []
            
            frame_idx = 0
            threshold = settings.scene_detection_threshold
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Convert to grayscale for comparison
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate histogram difference
                    hist_diff = cv2.compareHist(
                        cv2.calcHist([prev_frame], [0], None, [256], [0, 256]),
                        cv2.calcHist([gray], [0], None, [256], [0, 256]),
                        cv2.HISTCMP_CORREL
                    )
                    
                    # Scene change detected
                    if hist_diff < threshold:
                        # Save previous scene
                        if current_scene_frames:
                            scene_end = frame_idx
                            scenes.append({
                                "scene_id": len(scenes),
                                "start_time": scene_start / fps,
                                "end_time": scene_end / fps,
                                "duration": (scene_end - scene_start) / fps,
                                "start_frame": scene_start,
                                "end_frame": scene_end,
                                "frame_count": len(current_scene_frames),
                                "avg_brightness": np.mean([f["brightness"] for f in current_scene_frames]),
                                "dominant_colors": self._extract_dominant_colors(current_scene_frames[-1]["frame"])
                            })
                            
                        scene_start = frame_idx
                        current_scene_frames = []
                        
                # Add current frame to scene
                current_scene_frames.append({
                    "frame_idx": frame_idx,
                    "brightness": np.mean(gray),
                    "frame": frame.copy()
                })
                
                prev_frame = gray
                frame_idx += 1
                
                # Progress callback
                if progress_callback and total_frames > 0:
                    progress = (frame_idx / total_frames) * 100
                    progress_callback("scene_analysis", progress)
                    
            # Add final scene
            if current_scene_frames:
                scenes.append({
                    "scene_id": len(scenes),
                    "start_time": scene_start / fps,
                    "end_time": frame_idx / fps,
                    "duration": (frame_idx - scene_start) / fps,
                    "start_frame": scene_start,
                    "end_frame": frame_idx,
                    "frame_count": len(current_scene_frames),
                    "avg_brightness": np.mean([f["brightness"] for f in current_scene_frames]),
                    "dominant_colors": self._extract_dominant_colors(current_scene_frames[-1]["frame"])
                })
                
            cap.release()
            
            return {
                "scenes": scenes,
                "total_scenes": len(scenes),
                "avg_scene_duration": np.mean([s["duration"] for s in scenes]) if scenes else 0,
                "scene_change_points": [s["start_time"] for s in scenes[1:]]
            }
            
        except Exception as e:
            logger.error("Scene analysis failed", video_path=video_path, error=str(e))
            return {"scenes": [], "error": str(e)}

    async def _run_object_detection(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Detect objects in video frames using YOLO"""
        try:
            if "yolo" not in self._models:
                return {"objects": [], "error": "YOLO model not available"}
                
            detected_objects = []
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {"objects": []}
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Process every Nth frame for efficiency
            frame_interval = max(1, int(fps))  # Process 1 frame per second
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_idx % frame_interval == 0:
                    # Run object detection
                    results = self._models["yolo"](frame)
                    
                    # Process detections
                    for detection in results.pandas().xyxy[0].itertuples():
                        if detection.confidence >= settings.object_detection_confidence:
                            detected_objects.append({
                                "timestamp": frame_idx / fps,
                                "frame_number": frame_idx,
                                "object_class": detection.name,
                                "confidence": float(detection.confidence),
                                "bbox": {
                                    "x1": float(detection.xmin),
                                    "y1": float(detection.ymin),
                                    "x2": float(detection.xmax),
                                    "y2": float(detection.ymax)
                                }
                            })
                            
                frame_idx += 1
                
                # Progress callback
                if progress_callback and total_frames > 0:
                    progress = (frame_idx / total_frames) * 100
                    progress_callback("object_detection", progress)
                    
            cap.release()
            
            # Analyze object patterns
            object_stats = {}
            for obj in detected_objects:
                class_name = obj["object_class"]
                if class_name not in object_stats:
                    object_stats[class_name] = {
                        "count": 0,
                        "avg_confidence": 0,
                        "first_seen": obj["timestamp"],
                        "last_seen": obj["timestamp"]
                    }
                    
                stats = object_stats[class_name]
                stats["count"] += 1
                stats["avg_confidence"] = (stats["avg_confidence"] * (stats["count"] - 1) + obj["confidence"]) / stats["count"]
                stats["last_seen"] = obj["timestamp"]
                
            return {
                "objects": detected_objects,
                "total_detections": len(detected_objects),
                "unique_classes": len(object_stats),
                "object_statistics": object_stats,
                "most_common_objects": sorted(
                    object_stats.items(), 
                    key=lambda x: x[1]["count"], 
                    reverse=True
                )[:10]
            }
            
        except Exception as e:
            logger.error("Object detection failed", video_path=video_path, error=str(e))
            return {"objects": [], "error": str(e)}

    async def _run_face_detection(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Detect faces in video frames"""
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            detected_faces = []
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"faces": []}
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Process every few frames
            frame_interval = max(1, int(fps * 2))  # Process every 2 seconds
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_idx % frame_interval == 0:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30)
                    )
                    
                    for (x, y, w, h) in faces:
                        # Calculate confidence based on size and position
                        confidence = min(1.0, (w * h) / (100 * 100))
                        
                        if confidence >= settings.face_detection_confidence:
                            detected_faces.append({
                                "timestamp": frame_idx / fps,
                                "frame_number": frame_idx,
                                "confidence": confidence,
                                "bbox": {
                                    "x": int(x),
                                    "y": int(y),
                                    "width": int(w),
                                    "height": int(h)
                                }
                            })
                            
                frame_idx += 1
                
                if progress_callback and total_frames > 0:
                    progress = (frame_idx / total_frames) * 100
                    progress_callback("face_detection", progress)
                    
            cap.release()
            
            return {
                "faces": detected_faces,
                "total_faces": len(detected_faces),
                "face_appearances": len(set(f["timestamp"] for f in detected_faces)),
                "avg_face_size": np.mean([f["bbox"]["width"] * f["bbox"]["height"] for f in detected_faces]) if detected_faces else 0
            }
            
        except Exception as e:
            logger.error("Face detection failed", video_path=video_path, error=str(e))
            return {"faces": [], "error": str(e)}

    async def _run_ocr_analysis(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Extract text from video frames using OCR"""
        try:
            if "ocr" not in self._models:
                return {"text_segments": [], "error": "OCR model not available"}
                
            text_segments = []
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {"text_segments": []}
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Process every few frames
            frame_interval = max(1, int(fps * 3))  # Process every 3 seconds
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_idx % frame_interval == 0:
                    # Run OCR on frame
                    results = self._models["ocr"].readtext(frame)
                    
                    for (bbox, text, confidence) in results:
                        if confidence >= settings.ocr_confidence_threshold:
                            text_segments.append({
                                "timestamp": frame_idx / fps,
                                "frame_number": frame_idx,
                                "text": text.strip(),
                                "confidence": float(confidence),
                                "bbox": {
                                    "points": [[int(p[0]), int(p[1])] for p in bbox]
                                }
                            })
                            
                frame_idx += 1
                
                if progress_callback and total_frames > 0:
                    progress = (frame_idx / total_frames) * 100
                    progress_callback("ocr_analysis", progress)
                    
            cap.release()
            
            # Process text segments
            all_text = " ".join([seg["text"] for seg in text_segments])
            unique_texts = list(set([seg["text"] for seg in text_segments]))
            
            return {
                "text_segments": text_segments,
                "total_text_detections": len(text_segments),
                "unique_texts": unique_texts,
                "all_text_combined": all_text,
                "avg_text_confidence": np.mean([seg["confidence"] for seg in text_segments]) if text_segments else 0
            }
            
        except Exception as e:
            logger.error("OCR analysis failed", video_path=video_path, error=str(e))
            return {"text_segments": [], "error": str(e)}

    async def _run_audio_analysis(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Analyze audio track for speech-to-text and sentiment"""
        try:
            # Extract audio from video
            temp_audio_file = tempfile.mktemp(suffix=".wav")
            
            # Use ffmpeg to extract audio
            os.system(f"ffmpeg -i '{video_path}' -vn -acodec pcm_s16le -ar 16000 '{temp_audio_file}' -y > /dev/null 2>&1")
            
            if not os.path.exists(temp_audio_file):
                return {"transcripts": [], "error": "Failed to extract audio"}
                
            results = {
                "transcripts": [],
                "sentiment": {},
                "audio_features": {}
            }
            
            # Speech-to-text
            if "whisper" in self._models and settings.enable_speech_to_text:
                if progress_callback:
                    progress_callback("audio_transcription", 25)
                    
                transcript_result = self._models["whisper"].transcribe(temp_audio_file)
                
                transcripts = []
                for segment in transcript_result["segments"]:
                    transcripts.append({
                        "start_time": segment["start"],
                        "end_time": segment["end"],
                        "duration": segment["end"] - segment["start"],
                        "text": segment["text"].strip(),
                        "confidence": segment.get("confidence", 1.0)
                    })
                    
                results["transcripts"] = transcripts
                results["full_transcript"] = transcript_result.get("text", "")
                results["detected_language"] = transcript_result.get("language", "unknown")
                
                # Sentiment analysis on transcript
                if "sentiment" in self._models and settings.enable_sentiment_analysis:
                    if progress_callback:
                        progress_callback("sentiment_analysis", 75)
                        
                    sentiment_results = []
                    full_text = results["full_transcript"]
                    
                    if full_text:
                        # Analyze full transcript
                        sentiment = self._models["sentiment"](full_text)[0]
                        results["sentiment"]["overall"] = {
                            "label": sentiment["label"],
                            "score": float(sentiment["score"])
                        }
                        
                        # Analyze individual segments
                        for transcript in transcripts:
                            if len(transcript["text"]) > 10:  # Only analyze substantial text
                                seg_sentiment = self._models["sentiment"](transcript["text"])[0]
                                sentiment_results.append({
                                    "start_time": transcript["start_time"],
                                    "end_time": transcript["end_time"],
                                    "text": transcript["text"],
                                    "sentiment": seg_sentiment["label"],
                                    "confidence": float(seg_sentiment["score"])
                                })
                                
                        results["sentiment"]["segments"] = sentiment_results
                        
            # Audio feature analysis
            try:
                if progress_callback:
                    progress_callback("audio_features", 90)
                    
                y, sr = librosa.load(temp_audio_file)
                
                # Extract audio features
                features = {
                    "duration": float(len(y) / sr),
                    "sample_rate": int(sr),
                    "rms_energy": float(np.mean(librosa.feature.rms(y=y))),
                    "spectral_centroid": float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))),
                    "zero_crossing_rate": float(np.mean(librosa.feature.zero_crossing_rate(y))),
                    "tempo": float(librosa.beat.tempo(y=y, sr=sr)[0])
                }
                
                results["audio_features"] = features
                
            except Exception as e:
                logger.warning("Audio feature extraction failed", error=str(e))
                
            # Cleanup
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
                
            if progress_callback:
                progress_callback("audio_analysis", 100)
                
            return results
            
        except Exception as e:
            logger.error("Audio analysis failed", video_path=video_path, error=str(e))
            return {"transcripts": [], "error": str(e)}

    async def _classify_content(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Classify content based on analysis results"""
        try:
            classification = {
                "content_type": "unknown",
                "category": "general",
                "complexity_score": 0.5,
                "engagement_indicators": [],
                "content_rating": "unrated"
            }
            
            # Analyze based on available data
            scenes = analysis_results.get("scene_analysis", {}).get("scenes", [])
            objects = analysis_results.get("object_detection", {}).get("objects", [])
            faces = analysis_results.get("face_detection", {}).get("faces", [])
            transcripts = analysis_results.get("speech_analysis", {}).get("transcripts", [])
            
            # Scene complexity
            if scenes:
                avg_scene_duration = np.mean([s["duration"] for s in scenes])
                scene_count = len(scenes)
                
                if avg_scene_duration < 5 and scene_count > 10:
                    classification["content_type"] = "fast_paced"
                    classification["complexity_score"] = 0.8
                elif avg_scene_duration > 30:
                    classification["content_type"] = "slow_paced"
                    classification["complexity_score"] = 0.3
                    
            # Object analysis
            if objects:
                object_stats = analysis_results.get("object_detection", {}).get("object_statistics", {})
                
                if "person" in object_stats and object_stats["person"]["count"] > 50:
                    classification["category"] = "people_focused"
                    
                if any(obj in object_stats for obj in ["car", "truck", "motorcycle"]):
                    classification["category"] = "transportation"
                    
                if any(obj in object_stats for obj in ["sports ball", "baseball bat", "tennis racket"]):
                    classification["category"] = "sports"
                    
            # Face analysis
            if faces:
                face_count = len(faces)
                if face_count > 100:
                    classification["engagement_indicators"].append("high_human_presence")
                    
            # Speech analysis
            if transcripts:
                total_speech_time = sum([t["duration"] for t in transcripts])
                video_duration = analysis_results.get("video_metadata", {}).get("duration", 0)
                
                if video_duration > 0:
                    speech_ratio = total_speech_time / video_duration
                    if speech_ratio > 0.7:
                        classification["content_type"] = "dialogue_heavy"
                        classification["engagement_indicators"].append("high_speech_content")
                    elif speech_ratio < 0.1:
                        classification["content_type"] = "visual_focused"
                        
            return classification
            
        except Exception as e:
            logger.error("Content classification failed", error=str(e))
            return {"content_type": "unknown", "error": str(e)}

    async def _assess_video_quality(self, video_path: str) -> Dict[str, Any]:
        """Assess technical video quality"""
        try:
            quality_metrics = {
                "overall_score": 0.0,
                "technical_quality": {},
                "visual_quality": {},
                "audio_quality": {},
                "issues": []
            }
            
            # Basic technical metrics
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                # Resolution score
                pixel_count = width * height
                if pixel_count >= 1920 * 1080:
                    res_score = 1.0
                elif pixel_count >= 1280 * 720:
                    res_score = 0.8
                elif pixel_count >= 854 * 480:
                    res_score = 0.6
                else:
                    res_score = 0.3
                    
                # Frame rate score
                if fps >= 60:
                    fps_score = 1.0
                elif fps >= 30:
                    fps_score = 0.8
                elif fps >= 24:
                    fps_score = 0.6
                else:
                    fps_score = 0.3
                    
                quality_metrics["technical_quality"] = {
                    "resolution_score": res_score,
                    "framerate_score": fps_score,
                    "width": width,
                    "height": height,
                    "fps": fps
                }
                
                # Sample frames for visual quality
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                sample_frames = min(10, frame_count // 10)
                
                brightness_values = []
                contrast_values = []
                
                for i in range(sample_frames):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i * (frame_count // sample_frames))
                    ret, frame = cap.read()
                    
                    if ret:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        brightness_values.append(np.mean(gray))
                        contrast_values.append(np.std(gray))
                        
                if brightness_values and contrast_values:
                    avg_brightness = np.mean(brightness_values)
                    avg_contrast = np.mean(contrast_values)
                    
                    # Quality scores based on brightness and contrast
                    brightness_score = 1.0 - abs(avg_brightness - 127.5) / 127.5
                    contrast_score = min(1.0, avg_contrast / 50.0)
                    
                    quality_metrics["visual_quality"] = {
                        "brightness_score": brightness_score,
                        "contrast_score": contrast_score,
                        "avg_brightness": avg_brightness,
                        "avg_contrast": avg_contrast
                    }
                    
                cap.release()
                
            # Overall quality score
            scores = []
            if "technical_quality" in quality_metrics:
                scores.extend([
                    quality_metrics["technical_quality"].get("resolution_score", 0),
                    quality_metrics["technical_quality"].get("framerate_score", 0)
                ])
            if "visual_quality" in quality_metrics:
                scores.extend([
                    quality_metrics["visual_quality"].get("brightness_score", 0),
                    quality_metrics["visual_quality"].get("contrast_score", 0)
                ])
                
            if scores:
                quality_metrics["overall_score"] = np.mean(scores)
                
            return quality_metrics
            
        except Exception as e:
            logger.error("Quality assessment failed", video_path=video_path, error=str(e))
            return {"overall_score": 0.0, "error": str(e)}

    async def _technical_analysis(self, video_path: str) -> Dict[str, Any]:
        """Perform technical analysis of video file"""
        try:
            import ffmpeg
            
            # Get detailed technical information
            probe = ffmpeg.probe(video_path)
            
            analysis = {
                "file_size": os.path.getsize(video_path),
                "container_format": probe["format"]["format_name"],
                "duration": float(probe["format"]["duration"]),
                "bit_rate": int(probe["format"]["bit_rate"]),
                "streams": []
            }
            
            for stream in probe["streams"]:
                stream_info = {
                    "codec_type": stream["codec_type"],
                    "codec_name": stream["codec_name"],
                    "profile": stream.get("profile"),
                    "level": stream.get("level")
                }
                
                if stream["codec_type"] == "video":
                    stream_info.update({
                        "width": stream["width"],
                        "height": stream["height"],
                        "fps": eval(stream["r_frame_rate"]),
                        "pixel_format": stream.get("pix_fmt"),
                        "bit_rate": stream.get("bit_rate")
                    })
                elif stream["codec_type"] == "audio":
                    stream_info.update({
                        "sample_rate": stream["sample_rate"],
                        "channels": stream["channels"],
                        "channel_layout": stream.get("channel_layout"),
                        "bit_rate": stream.get("bit_rate")
                    })
                    
                analysis["streams"].append(stream_info)
                
            return analysis
            
        except Exception as e:
            logger.error("Technical analysis failed", video_path=video_path, error=str(e))
            return {"error": str(e)}

    def _extract_dominant_colors(self, frame: np.ndarray, k: int = 3) -> List[List[int]]:
        """Extract dominant colors from frame using k-means clustering"""
        try:
            # Reshape frame
            data = frame.reshape((-1, 3))
            data = np.float32(data)
            
            # Apply k-means clustering
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            # Convert to int and return
            centers = np.uint8(centers)
            return centers.tolist()
            
        except:
            return [[0, 0, 0]]

    def _generate_analysis_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level summary of analysis results"""
        try:
            summary = {
                "content_highlights": [],
                "technical_summary": {},
                "engagement_factors": [],
                "quality_indicators": [],
                "recommendations": []
            }
            
            # Scene summary
            scenes = analysis_results.get("scene_analysis", {}).get("scenes", [])
            if scenes:
                summary["content_highlights"].append(f"{len(scenes)} distinct scenes detected")
                avg_duration = np.mean([s["duration"] for s in scenes])
                summary["content_highlights"].append(f"Average scene duration: {avg_duration:.1f} seconds")
                
            # Object summary
            objects = analysis_results.get("object_detection", {})
            if objects.get("objects"):
                unique_classes = objects.get("unique_classes", 0)
                summary["content_highlights"].append(f"{unique_classes} different object types detected")
                
                most_common = objects.get("most_common_objects", [])
                if most_common:
                    top_object = most_common[0][0]
                    summary["content_highlights"].append(f"Most common object: {top_object}")
                    
            # Speech summary
            speech = analysis_results.get("speech_analysis", {})
            if speech.get("transcripts"):
                total_speech = sum([t["duration"] for t in speech["transcripts"]])
                summary["content_highlights"].append(f"{total_speech:.1f} seconds of speech detected")
                
                if speech.get("sentiment", {}).get("overall"):
                    sentiment = speech["sentiment"]["overall"]["label"]
                    summary["content_highlights"].append(f"Overall sentiment: {sentiment}")
                    
            # Quality summary
            quality = analysis_results.get("quality_assessment", {})
            if quality.get("overall_score"):
                score = quality["overall_score"]
                if score > 0.8:
                    summary["quality_indicators"].append("High technical quality")
                elif score > 0.6:
                    summary["quality_indicators"].append("Good technical quality") 
                else:
                    summary["quality_indicators"].append("Quality improvements recommended")
                    
            return summary
            
        except Exception as e:
            logger.error("Summary generation failed", error=str(e))
            return {"error": str(e)}


# Global analysis service instance
analysis_service = VideoAnalysisService()