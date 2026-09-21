"""
AI-Powered Folder Structure Suggestion System

Uses machine learning to analyze user files and suggest optimal folder organizations:
- Content-based clustering using embeddings
- File type and metadata analysis
- Usage pattern recognition
- Semantic similarity grouping
- Personalized recommendations
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import pickle
import json
import os

# ML libraries
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from ..core.config import settings
from ..core.database import db_manager
from ..utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class FolderSuggester:
    """AI-powered folder structure suggestion engine"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.cache_manager = CacheManager()
        
        # Initialize NLTK components
        if ML_AVAILABLE:
            self._initialize_nltk()
        
        self.suggestion_stats = {
            "total_suggestions_generated": 0,
            "total_suggestions_accepted": 0,
            "average_confidence_score": 0.0,
            "model_load_time": 0.0
        }
        
    def _initialize_nltk(self):
        """Initialize NLTK components"""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words('english'))
        except Exception as e:
            logger.warning(f"Failed to initialize NLTK: {e}")
    
    async def initialize(self):
        """Initialize the folder suggester"""
        
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available - AI suggestions disabled")
            return
        
        if not settings.smart_folders.ai_suggestions_enabled:
            logger.info("AI suggestions disabled in configuration")
            return
        
        try:
            start_time = datetime.utcnow()
            
            # Load sentence transformer model
            model_name = settings.smart_folders.ai_model_name
            logger.info(f"Loading AI model: {model_name}")
            
            self.model = SentenceTransformer(model_name)
            
            load_time = (datetime.utcnow() - start_time).total_seconds()
            self.suggestion_stats["model_load_time"] = load_time
            
            logger.info(f"AI model loaded in {load_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Failed to initialize folder suggester: {e}")
            self.model = None
    
    async def generate_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate folder structure suggestions for a user"""
        
        if not self.model:
            return []
        
        try:
            # Collect user's file data
            file_data = await self._collect_user_file_data(user_id)
            
            if len(file_data) < 10:  # Need minimum files for meaningful suggestions
                return [{
                    "type": "insufficient_data",
                    "message": "Need at least 10 files to generate meaningful suggestions",
                    "confidence": 0.0
                }]
            
            # Generate different types of suggestions
            suggestions = []
            
            # Content-based suggestions
            content_suggestions = await self._generate_content_based_suggestions(file_data)
            suggestions.extend(content_suggestions)
            
            # Type-based suggestions
            type_suggestions = await self._generate_type_based_suggestions(file_data)
            suggestions.extend(type_suggestions)
            
            # Date-based suggestions
            date_suggestions = await self._generate_date_based_suggestions(file_data)
            suggestions.extend(date_suggestions)
            
            # Project-based suggestions
            project_suggestions = await self._generate_project_based_suggestions(file_data)
            suggestions.extend(project_suggestions)
            
            # Rank and filter suggestions
            ranked_suggestions = await self._rank_suggestions(suggestions, file_data)
            
            # Store suggestions in database
            for suggestion in ranked_suggestions[:5]:  # Store top 5
                await db_manager.create_ai_suggestion(
                    user_id=user_id,
                    suggestion=suggestion,
                    model_used=settings.smart_folders.ai_model_name,
                    confidence=suggestion["confidence"]
                )
            
            self.suggestion_stats["total_suggestions_generated"] += len(ranked_suggestions)
            
            return ranked_suggestions[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions for user {user_id}: {e}")
            return []
    
    async def _collect_user_file_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect and analyze user's file data"""
        
        # This would typically query a file index or database
        # For demo purposes, we'll simulate file data
        
        file_data = []
        
        try:
            # Simulate user file data
            # In production, this would query your file database
            sample_files = [
                {
                    "file_id": "1", "name": "project_proposal.docx", "type": "document",
                    "size": 45000, "created": "2024-01-15", "path": "/documents/work/",
                    "content": "project management software development proposal"
                },
                {
                    "file_id": "2", "name": "vacation_photo.jpg", "type": "image",
                    "size": 2500000, "created": "2024-02-20", "path": "/photos/",
                    "content": ""
                },
                {
                    "file_id": "3", "name": "meeting_notes.txt", "type": "text",
                    "size": 5000, "created": "2024-01-20", "path": "/documents/",
                    "content": "team meeting notes discussion project timeline"
                },
                {
                    "file_id": "4", "name": "budget_2024.xlsx", "type": "spreadsheet",
                    "size": 25000, "created": "2024-01-10", "path": "/documents/finance/",
                    "content": "annual budget financial planning expenses"
                },
                {
                    "file_id": "5", "name": "presentation_slides.pptx", "type": "presentation",
                    "size": 15000000, "created": "2024-01-25", "path": "/documents/work/",
                    "content": "quarterly review presentation business metrics"
                }
                # Add more sample files as needed
            ]
            
            for i in range(50):  # Generate more sample files
                file_types = ["document", "image", "video", "audio", "text", "spreadsheet"]
                categories = ["work", "personal", "photos", "music", "projects"]
                
                file_data.append({
                    "file_id": str(i + 100),
                    "name": f"sample_file_{i}.ext",
                    "type": np.random.choice(file_types),
                    "size": np.random.randint(1000, 50000000),
                    "created": f"2024-{np.random.randint(1, 12):02d}-{np.random.randint(1, 28):02d}",
                    "path": f"/{np.random.choice(categories)}/",
                    "content": f"sample content for {np.random.choice(categories)} file"
                })
            
            file_data.extend(sample_files)
            
            return file_data
            
        except Exception as e:
            logger.error(f"Error collecting user file data: {e}")
            return []
    
    async def _generate_content_based_suggestions(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions based on file content similarity"""
        
        suggestions = []
        
        try:
            # Extract text content from files
            text_files = [f for f in file_data if f.get("content")]
            
            if len(text_files) < 5:
                return []
            
            # Generate embeddings for file contents
            contents = [self._preprocess_text(f["content"]) for f in text_files]
            embeddings = self.model.encode(contents)
            
            # Cluster files based on content similarity
            n_clusters = min(5, len(text_files) // 3)  # Dynamic cluster count
            if n_clusters < 2:
                return []
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(embeddings)
            
            # Analyze clusters and generate folder suggestions
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                clusters[label].append(text_files[i])
            
            for cluster_id, cluster_files in clusters.items():
                if len(cluster_files) < 2:
                    continue
                
                # Analyze cluster content to determine theme
                all_content = " ".join([f["content"] for f in cluster_files])
                theme_keywords = self._extract_keywords(all_content)
                
                # Generate folder name based on theme
                folder_name = self._generate_theme_folder_name(theme_keywords)
                
                suggestion = {
                    "type": "content_based",
                    "name": folder_name,
                    "description": f"Files grouped by content similarity: {', '.join(theme_keywords[:3])}",
                    "structure": {
                        folder_name: {
                            "files": [f["name"] for f in cluster_files],
                            "rules": [
                                {
                                    "condition_field": "content",
                                    "operator": "contains",
                                    "value": keyword
                                } for keyword in theme_keywords[:2]
                            ]
                        }
                    },
                    "confidence": len(cluster_files) / len(text_files),
                    "files_count": len(cluster_files),
                    "reasoning": f"Files share similar content themes around: {', '.join(theme_keywords[:3])}"
                }
                
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating content-based suggestions: {e}")
        
        return suggestions
    
    async def _generate_type_based_suggestions(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions based on file types"""
        
        suggestions = []
        
        try:
            # Count file types
            type_counts = Counter([f["type"] for f in file_data])
            
            # Generate suggestions for file types with significant presence
            for file_type, count in type_counts.items():
                if count >= 3:  # At least 3 files of this type
                    
                    type_mapping = {
                        "image": "Photos & Images",
                        "video": "Videos",
                        "audio": "Music & Audio",
                        "document": "Documents",
                        "spreadsheet": "Spreadsheets",
                        "presentation": "Presentations",
                        "text": "Text Files"
                    }
                    
                    folder_name = type_mapping.get(file_type, file_type.title())
                    
                    suggestion = {
                        "type": "type_based",
                        "name": folder_name,
                        "description": f"Organize {count} {file_type} files",
                        "structure": {
                            folder_name: {
                                "rules": [
                                    {
                                        "condition_field": "file_type",
                                        "operator": "equals",
                                        "value": file_type
                                    }
                                ]
                            }
                        },
                        "confidence": min(count / len(file_data), 0.9),
                        "files_count": count,
                        "reasoning": f"You have {count} {file_type} files that could be organized together"
                    }
                    
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating type-based suggestions: {e}")
        
        return suggestions
    
    async def _generate_date_based_suggestions(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions based on file creation dates"""
        
        suggestions = []
        
        try:
            # Group files by month/year
            date_groups = defaultdict(list)
            
            for file_info in file_data:
                try:
                    date_str = file_info.get("created", "")
                    if date_str:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        month_key = date_obj.strftime("%Y-%m")
                        date_groups[month_key].append(file_info)
                except ValueError:
                    continue
            
            # Generate suggestions for months with significant file activity
            for month_key, files in date_groups.items():
                if len(files) >= 5:  # At least 5 files in this month
                    
                    date_obj = datetime.strptime(month_key, "%Y-%m")
                    folder_name = date_obj.strftime("%B %Y")
                    
                    suggestion = {
                        "type": "date_based",
                        "name": folder_name,
                        "description": f"Files from {folder_name}",
                        "structure": {
                            folder_name: {
                                "rules": [
                                    {
                                        "condition_field": "created_date",
                                        "operator": "between",
                                        "value": [
                                            f"{month_key}-01",
                                            f"{month_key}-31"
                                        ]
                                    }
                                ]
                            }
                        },
                        "confidence": min(len(files) / len(file_data), 0.8),
                        "files_count": len(files),
                        "reasoning": f"You created {len(files)} files in {folder_name}"
                    }
                    
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating date-based suggestions: {e}")
        
        return suggestions
    
    async def _generate_project_based_suggestions(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions based on project or path patterns"""
        
        suggestions = []
        
        try:
            # Analyze file paths for patterns
            path_groups = defaultdict(list)
            
            for file_info in file_data:
                path = file_info.get("path", "/")
                # Extract potential project names from paths
                path_parts = [p for p in path.split("/") if p]
                
                if len(path_parts) > 0:
                    project_name = path_parts[0]  # Use first directory as project name
                    path_groups[project_name].append(file_info)
            
            # Generate suggestions for paths with multiple files
            for project_name, files in path_groups.items():
                if len(files) >= 3 and project_name not in ["documents", "files"]:
                    
                    suggestion = {
                        "type": "project_based",
                        "name": f"{project_name.title()} Project",
                        "description": f"Files related to {project_name}",
                        "structure": {
                            f"{project_name.title()} Project": {
                                "rules": [
                                    {
                                        "condition_field": "path",
                                        "operator": "contains",
                                        "value": project_name
                                    }
                                ]
                            }
                        },
                        "confidence": min(len(files) / len(file_data), 0.7),
                        "files_count": len(files),
                        "reasoning": f"Multiple files appear to be related to {project_name}"
                    }
                    
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating project-based suggestions: {e}")
        
        return suggestions
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for NLP analysis"""
        
        if not ML_AVAILABLE or not hasattr(self, 'lemmatizer'):
            return text.lower()
        
        try:
            # Tokenize
            tokens = word_tokenize(text.lower())
            
            # Remove stopwords and lemmatize
            tokens = [
                self.lemmatizer.lemmatize(token) 
                for token in tokens 
                if token.isalnum() and token not in self.stop_words
            ]
            
            return " ".join(tokens)
            
        except Exception:
            return text.lower()
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract key terms from text"""
        
        try:
            # Simple keyword extraction based on frequency
            words = text.lower().split()
            
            # Filter out common words
            common_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
            words = [w for w in words if w not in common_words and len(w) > 2]
            
            # Count word frequency
            word_counts = Counter(words)
            
            # Return most common words
            keywords = [word for word, count in word_counts.most_common(max_keywords)]
            
            return keywords
            
        except Exception as e:
            logger.debug(f"Error extracting keywords: {e}")
            return []
    
    def _generate_theme_folder_name(self, keywords: List[str]) -> str:
        """Generate folder name from theme keywords"""
        
        if not keywords:
            return "Miscellaneous"
        
        # Map keywords to common folder names
        keyword_mapping = {
            "project": "Projects",
            "work": "Work",
            "meeting": "Meetings", 
            "report": "Reports",
            "budget": "Finance",
            "financial": "Finance",
            "photo": "Photos",
            "image": "Images",
            "music": "Music",
            "video": "Videos",
            "document": "Documents",
            "presentation": "Presentations"
        }
        
        for keyword in keywords:
            if keyword in keyword_mapping:
                return keyword_mapping[keyword]
        
        # If no mapping found, use first keyword
        return keywords[0].title()
    
    async def _rank_suggestions(self, suggestions: List[Dict[str, Any]], 
                              file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank suggestions by relevance and confidence"""
        
        if not suggestions:
            return []
        
        # Calculate ranking scores
        for suggestion in suggestions:
            score = 0.0
            
            # Base confidence score
            score += suggestion.get("confidence", 0.0) * 0.4
            
            # File count factor (more files = higher relevance)
            files_count = suggestion.get("files_count", 0)
            file_count_score = min(files_count / len(file_data), 1.0)
            score += file_count_score * 0.3
            
            # Type bonus (some types are more valuable)
            suggestion_type = suggestion.get("type", "")
            type_bonuses = {
                "content_based": 0.3,
                "project_based": 0.25,
                "type_based": 0.2,
                "date_based": 0.15
            }
            score += type_bonuses.get(suggestion_type, 0.1) * 0.3
            
            suggestion["ranking_score"] = score
        
        # Sort by ranking score
        suggestions.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
        
        return suggestions
    
    async def get_suggestion_feedback(self, suggestion_id: str, user_id: str, 
                                   feedback: Dict[str, Any]) -> bool:
        """Process user feedback on suggestions"""
        
        try:
            # Update suggestion status in database
            query = """
            UPDATE ai_folder_suggestions 
            SET status = :status, user_feedback = :feedback, applied_at = :applied_at
            WHERE id = :id AND user_id = :user_id
            """
            
            applied_at = datetime.utcnow() if feedback.get("accepted") else None
            
            await db_manager.database.execute(
                query,
                values={
                    "id": suggestion_id,
                    "user_id": user_id,
                    "status": "accepted" if feedback.get("accepted") else "rejected",
                    "feedback": json.dumps(feedback),
                    "applied_at": applied_at
                }
            )
            
            # Update statistics
            if feedback.get("accepted"):
                self.suggestion_stats["total_suggestions_accepted"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing suggestion feedback: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get AI suggester performance metrics"""
        
        stats = self.suggestion_stats.copy()
        
        # Calculate acceptance rate
        if stats["total_suggestions_generated"] > 0:
            stats["acceptance_rate"] = stats["total_suggestions_accepted"] / stats["total_suggestions_generated"]
        else:
            stats["acceptance_rate"] = 0.0
        
        stats["ml_available"] = ML_AVAILABLE
        stats["model_loaded"] = self.model is not None
        
        return stats
    
    async def cleanup(self):
        """Clean up resources"""
        self.model = None
        logger.info("Folder suggester cleaned up")