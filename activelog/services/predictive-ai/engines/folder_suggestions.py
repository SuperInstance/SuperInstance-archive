"""
Automatic Folder Suggestions Engine - Proactively suggests folders before users think about them.
Uses AI to predict organizational needs based on user behavior and content analysis.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from collections import defaultdict, Counter

class SuggestionTrigger(Enum):
    CONTENT_PATTERN = "content_pattern"
    TEMPORAL_PATTERN = "temporal_pattern"
    VOLUME_THRESHOLD = "volume_threshold"
    SEMANTIC_GROUPING = "semantic_grouping"
    USER_BEHAVIOR = "user_behavior"
    EXTERNAL_EVENT = "external_event"

class SuggestionConfidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class FolderSuggestion:
    """Suggested folder organization."""
    suggestion_id: str
    user_id: str
    folder_name: str
    folder_path: str
    description: str
    trigger: SuggestionTrigger
    confidence: SuggestionConfidence
    reasoning: str
    affected_files: List[str]
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any] = None

@dataclass
class ContentPattern:
    """Identified pattern in user content."""
    pattern_id: str
    pattern_type: str
    keywords: List[str]
    file_extensions: List[str]
    date_range: Tuple[datetime, datetime]
    frequency: int
    example_files: List[str]

class ContentAnalyzer:
    """Analyzes content patterns for folder suggestions."""
    
    def __init__(self):
        self.semantic_categories = self._load_semantic_categories()
        self.temporal_patterns = self._load_temporal_patterns()
    
    def _load_semantic_categories(self) -> Dict[str, List[str]]:
        """Load semantic category keywords."""
        return {
            "financial": [
                "invoice", "receipt", "tax", "expense", "budget", "payment",
                "billing", "statement", "transaction", "refund", "purchase"
            ],
            "health": [
                "medical", "doctor", "appointment", "prescription", "insurance",
                "health", "wellness", "lab", "test", "result", "therapy"
            ],
            "work": [
                "project", "meeting", "presentation", "report", "contract",
                "proposal", "client", "deadline", "task", "deliverable"
            ],
            "personal": [
                "family", "vacation", "holiday", "birthday", "anniversary",
                "personal", "home", "house", "car", "travel", "hobby"
            ],
            "education": [
                "course", "class", "assignment", "homework", "study", "exam",
                "grade", "school", "university", "learning", "research"
            ],
            "legal": [
                "contract", "agreement", "legal", "law", "court", "document",
                "license", "permit", "copyright", "trademark", "patent"
            ],
            "media": [
                "photo", "image", "video", "movie", "music", "audio",
                "song", "album", "picture", "recording", "media"
            ],
            "reference": [
                "manual", "guide", "documentation", "reference", "instruction",
                "tutorial", "help", "faq", "specification", "standard"
            ]
        }
    
    def _load_temporal_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load temporal pattern definitions."""
        return {
            "tax_season": {
                "months": [1, 2, 3, 4],  # January to April
                "keywords": ["tax", "w2", "1099", "deduction", "irs"],
                "folder_suggestions": ["Tax Documents {year}", "Tax Returns", "Receipts for Taxes"]
            },
            "holiday_season": {
                "months": [11, 12],  # November to December
                "keywords": ["gift", "holiday", "christmas", "thanksgiving"],
                "folder_suggestions": ["Holiday Planning {year}", "Gift Ideas", "Holiday Photos"]
            },
            "back_to_school": {
                "months": [8, 9],  # August to September
                "keywords": ["school", "class", "assignment", "textbook"],
                "folder_suggestions": ["School Year {year}", "Class Materials", "Assignments"]
            },
            "spring_cleaning": {
                "months": [3, 4, 5],  # March to May
                "keywords": ["clean", "organize", "declutter", "donate"],
                "folder_suggestions": ["Spring Cleaning {year}", "Items to Donate", "Organization Projects"]
            }
        }
    
    def analyze_content_patterns(self, files: List[Dict[str, Any]]) -> List[ContentPattern]:
        """Analyze files to identify content patterns."""
        if not files:
            return []
        
        patterns = []
        
        # Group files by various criteria
        semantic_groups = self._group_by_semantics(files)
        temporal_groups = self._group_by_time_periods(files)
        extension_groups = self._group_by_extensions(files)
        
        # Generate patterns from groups
        patterns.extend(self._create_semantic_patterns(semantic_groups))
        patterns.extend(self._create_temporal_patterns(temporal_groups))
        patterns.extend(self._create_extension_patterns(extension_groups))
        
        return patterns
    
    def _group_by_semantics(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group files by semantic categories."""
        groups = defaultdict(list)
        
        for file_info in files:
            filename = file_info.get("name", "").lower()
            content = file_info.get("content", "").lower()
            text_to_analyze = f"{filename} {content}"
            
            # Check each semantic category
            for category, keywords in self.semantic_categories.items():
                matches = sum(1 for keyword in keywords if keyword in text_to_analyze)
                if matches >= 2:  # At least 2 keyword matches
                    groups[category].append(file_info)
        
        # Filter groups with minimum file count
        return {category: files for category, files in groups.items() if len(files) >= 3}
    
    def _group_by_time_periods(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group files by time periods."""
        groups = defaultdict(list)
        current_date = datetime.now()
        
        for file_info in files:
            file_date = file_info.get("created_at")
            if isinstance(file_date, str):
                try:
                    file_date = datetime.fromisoformat(file_date)
                except:
                    continue
            elif not isinstance(file_date, datetime):
                continue
            
            # Group by month-year
            month_year = f"{file_date.year}-{file_date.month:02d}"
            groups[month_year].append(file_info)
            
            # Group by quarter
            quarter = (file_date.month - 1) // 3 + 1
            quarter_year = f"Q{quarter}-{file_date.year}"
            groups[quarter_year].append(file_info)
            
            # Check for temporal patterns
            for pattern_name, pattern_info in self.temporal_patterns.items():
                if file_date.month in pattern_info["months"]:
                    filename_content = f"{file_info.get('name', '')} {file_info.get('content', '')}".lower()
                    if any(keyword in filename_content for keyword in pattern_info["keywords"]):
                        groups[f"{pattern_name}_{file_date.year}"].append(file_info)
        
        return {period: files for period, files in groups.items() if len(files) >= 5}
    
    def _group_by_extensions(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group files by extensions and types."""
        groups = defaultdict(list)
        
        for file_info in files:
            filename = file_info.get("name", "")
            if "." in filename:
                extension = filename.split(".")[-1].lower()
                groups[extension].append(file_info)
            
            # Group by file type categories
            file_type = self._categorize_file_type(filename)
            if file_type:
                groups[f"type_{file_type}"].append(file_info)
        
        return {ext: files for ext, files in groups.items() if len(files) >= 4}
    
    def _categorize_file_type(self, filename: str) -> Optional[str]:
        """Categorize file by type."""
        filename = filename.lower()
        
        image_exts = ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"]
        document_exts = ["pdf", "doc", "docx", "txt", "rtf", "odt"]
        spreadsheet_exts = ["xls", "xlsx", "csv", "ods"]
        presentation_exts = ["ppt", "pptx", "odp"]
        audio_exts = ["mp3", "wav", "flac", "aac", "ogg"]
        video_exts = ["mp4", "avi", "mkv", "mov", "wmv", "flv"]
        
        extension = filename.split(".")[-1] if "." in filename else ""
        
        if extension in image_exts:
            return "images"
        elif extension in document_exts:
            return "documents"
        elif extension in spreadsheet_exts:
            return "spreadsheets"
        elif extension in presentation_exts:
            return "presentations"
        elif extension in audio_exts:
            return "audio"
        elif extension in video_exts:
            return "video"
        
        return None
    
    def _create_semantic_patterns(self, semantic_groups: Dict[str, List[Dict]]) -> List[ContentPattern]:
        """Create patterns from semantic groupings."""
        patterns = []
        
        for category, files in semantic_groups.items():
            if len(files) < 3:
                continue
            
            # Extract common keywords
            all_text = " ".join([
                f"{f.get('name', '')} {f.get('content', '')}"
                for f in files
            ]).lower()
            
            keywords = self.semantic_categories[category]
            found_keywords = [kw for kw in keywords if kw in all_text]
            
            # Extract file extensions
            extensions = []
            for f in files:
                filename = f.get("name", "")
                if "." in filename:
                    ext = filename.split(".")[-1].lower()
                    extensions.append(ext)
            
            # Date range
            dates = []
            for f in files:
                date = f.get("created_at")
                if isinstance(date, str):
                    try:
                        dates.append(datetime.fromisoformat(date))
                    except:
                        continue
                elif isinstance(date, datetime):
                    dates.append(date)
            
            date_range = (min(dates), max(dates)) if dates else (datetime.now(), datetime.now())
            
            pattern = ContentPattern(
                pattern_id=f"semantic_{category}_{len(patterns)}",
                pattern_type="semantic",
                keywords=found_keywords[:10],
                file_extensions=list(set(extensions)),
                date_range=date_range,
                frequency=len(files),
                example_files=[f.get("name", "") for f in files[:5]]
            )
            
            patterns.append(pattern)
        
        return patterns
    
    def _create_temporal_patterns(self, temporal_groups: Dict[str, List[Dict]]) -> List[ContentPattern]:
        """Create patterns from temporal groupings."""
        patterns = []
        
        for period, files in temporal_groups.items():
            if len(files) < 5:
                continue
            
            # Extract keywords from filenames and content
            all_text = " ".join([
                f"{f.get('name', '')} {f.get('content', '')}"
                for f in files
            ]).lower()
            
            # Simple keyword extraction (most common words)
            words = re.findall(r'\b\w{3,}\b', all_text)
            word_counts = Counter(words)
            keywords = [word for word, count in word_counts.most_common(10) if count >= 2]
            
            pattern = ContentPattern(
                pattern_id=f"temporal_{period}_{len(patterns)}",
                pattern_type="temporal",
                keywords=keywords,
                file_extensions=[],
                date_range=(datetime.now() - timedelta(days=30), datetime.now()),
                frequency=len(files),
                example_files=[f.get("name", "") for f in files[:5]]
            )
            
            patterns.append(pattern)
        
        return patterns
    
    def _create_extension_patterns(self, extension_groups: Dict[str, List[Dict]]) -> List[ContentPattern]:
        """Create patterns from file extension groupings."""
        patterns = []
        
        for ext_type, files in extension_groups.items():
            if len(files) < 4:
                continue
            
            pattern = ContentPattern(
                pattern_id=f"extension_{ext_type}_{len(patterns)}",
                pattern_type="file_type",
                keywords=[ext_type],
                file_extensions=[ext_type] if not ext_type.startswith("type_") else [],
                date_range=(datetime.now() - timedelta(days=30), datetime.now()),
                frequency=len(files),
                example_files=[f.get("name", "") for f in files[:5]]
            )
            
            patterns.append(pattern)
        
        return patterns

class ProactiveFolderEngine:
    """Engine that proactively suggests folders before users need them."""
    
    def __init__(self):
        self.content_analyzer = ContentAnalyzer()
        self.suggestion_templates = self._load_suggestion_templates()
        self.user_context_history = defaultdict(list)
        
    def _load_suggestion_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load folder suggestion templates."""
        return {
            "semantic_folders": {
                "financial": {
                    "templates": [
                        "Financial Documents",
                        "Receipts {year}",
                        "Tax Documents {year}",
                        "Budget Planning",
                        "Investment Records"
                    ],
                    "descriptions": [
                        "Organize your financial documents",
                        "Store receipts from {year}",
                        "Keep tax-related documents together",
                        "Track your budget and expenses",
                        "Maintain investment documentation"
                    ]
                },
                "work": {
                    "templates": [
                        "Work Projects",
                        "Client {client_name}",
                        "Meetings {month}",
                        "Reports {year}",
                        "Presentations"
                    ],
                    "descriptions": [
                        "Organize work-related projects",
                        "Documents for {client_name}",
                        "Meeting notes and agendas",
                        "Annual reports and summaries",
                        "Presentation files and slides"
                    ]
                },
                "personal": {
                    "templates": [
                        "Family Photos {year}",
                        "Travel {destination}",
                        "Hobby Projects",
                        "Home Maintenance",
                        "Personal Documents"
                    ],
                    "descriptions": [
                        "Family photos from {year}",
                        "Travel memories from {destination}",
                        "Projects related to your hobbies",
                        "Home improvement and maintenance",
                        "Important personal documents"
                    ]
                }
            },
            "temporal_folders": {
                "monthly": "Monthly Archive {month} {year}",
                "quarterly": "Q{quarter} {year} Documents",
                "yearly": "Year {year} Archive",
                "project_based": "Project {project_name}",
                "event_based": "{event_name} {year}"
            },
            "type_based_folders": {
                "images": "Images and Photos",
                "documents": "Document Archive",
                "spreadsheets": "Spreadsheets and Data",
                "presentations": "Presentations",
                "audio": "Audio Files",
                "video": "Video Archive"
            }
        }
    
    async def generate_proactive_suggestions(self, user_id: str, 
                                           current_files: List[Dict[str, Any]],
                                           user_context: Dict[str, Any] = None) -> List[FolderSuggestion]:
        """Generate proactive folder suggestions."""
        
        suggestions = []
        current_time = datetime.now()
        
        # Analyze current content patterns
        patterns = self.content_analyzer.analyze_content_patterns(current_files)
        
        # Generate suggestions based on patterns
        for pattern in patterns:
            pattern_suggestions = await self._generate_pattern_suggestions(
                user_id, pattern, current_files, user_context or {}
            )
            suggestions.extend(pattern_suggestions)
        
        # Generate temporal suggestions
        temporal_suggestions = await self._generate_temporal_suggestions(
            user_id, current_time, current_files
        )
        suggestions.extend(temporal_suggestions)
        
        # Generate behavioral suggestions
        behavioral_suggestions = await self._generate_behavioral_suggestions(
            user_id, current_files, user_context or {}
        )
        suggestions.extend(behavioral_suggestions)
        
        # Sort by confidence and relevance
        suggestions.sort(key=lambda s: (s.confidence.value, len(s.affected_files)), reverse=True)
        
        return suggestions[:10]  # Return top 10 suggestions
    
    async def _generate_pattern_suggestions(self, user_id: str, pattern: ContentPattern,
                                          current_files: List[Dict[str, Any]],
                                          user_context: Dict[str, Any]) -> List[FolderSuggestion]:
        """Generate suggestions based on content patterns."""
        suggestions = []
        
        if pattern.pattern_type == "semantic":
            category = self._identify_semantic_category(pattern.keywords)
            if category and category in self.suggestion_templates["semantic_folders"]:
                template_info = self.suggestion_templates["semantic_folders"][category]
                
                for i, template in enumerate(template_info["templates"]):
                    folder_name = self._populate_template(template, user_context, pattern)
                    description = self._populate_template(
                        template_info["descriptions"][i], user_context, pattern
                    )
                    
                    # Find affected files
                    affected_files = [
                        f.get("name", "") for f in current_files
                        if self._file_matches_pattern(f, pattern)
                    ]
                    
                    if len(affected_files) >= 3:  # Minimum threshold
                        suggestion = FolderSuggestion(
                            suggestion_id=f"semantic_{user_id}_{category}_{i}",
                            user_id=user_id,
                            folder_name=folder_name,
                            folder_path=f"/{folder_name}",
                            description=description,
                            trigger=SuggestionTrigger.CONTENT_PATTERN,
                            confidence=self._calculate_confidence(pattern, affected_files),
                            reasoning=f"You have {len(affected_files)} {category}-related files that could be organized together",
                            affected_files=affected_files,
                            created_at=datetime.now(),
                            expires_at=datetime.now() + timedelta(days=7),
                            metadata={"pattern_id": pattern.pattern_id, "category": category}
                        )
                        
                        suggestions.append(suggestion)
        
        elif pattern.pattern_type == "file_type":
            file_type = pattern.keywords[0] if pattern.keywords else "files"
            
            if file_type.startswith("type_"):
                file_type = file_type[5:]  # Remove "type_" prefix
            
            if file_type in self.suggestion_templates["type_based_folders"]:
                folder_name = self.suggestion_templates["type_based_folders"][file_type]
                
                affected_files = [
                    f.get("name", "") for f in current_files
                    if self._file_matches_pattern(f, pattern)
                ]
                
                if len(affected_files) >= 4:
                    suggestion = FolderSuggestion(
                        suggestion_id=f"filetype_{user_id}_{file_type}",
                        user_id=user_id,
                        folder_name=folder_name,
                        folder_path=f"/{folder_name}",
                        description=f"Organize your {file_type} files in one place",
                        trigger=SuggestionTrigger.CONTENT_PATTERN,
                        confidence=SuggestionConfidence.MEDIUM,
                        reasoning=f"You have {len(affected_files)} {file_type} files that could be organized together",
                        affected_files=affected_files,
                        created_at=datetime.now(),
                        expires_at=datetime.now() + timedelta(days=7),
                        metadata={"pattern_id": pattern.pattern_id, "file_type": file_type}
                    )
                    
                    suggestions.append(suggestion)
        
        return suggestions
    
    async def _generate_temporal_suggestions(self, user_id: str, current_time: datetime,
                                           current_files: List[Dict[str, Any]]) -> List[FolderSuggestion]:
        """Generate suggestions based on temporal patterns."""
        suggestions = []
        
        # Check for seasonal/temporal patterns
        current_month = current_time.month
        current_year = current_time.year
        
        for pattern_name, pattern_info in self.content_analyzer.temporal_patterns.items():
            if current_month in pattern_info["months"]:
                # Find files that might match this temporal pattern
                matching_files = []
                for file_info in current_files:
                    filename_content = f"{file_info.get('name', '')} {file_info.get('content', '')}".lower()
                    if any(keyword in filename_content for keyword in pattern_info["keywords"]):
                        matching_files.append(file_info.get("name", ""))
                
                if len(matching_files) >= 2:  # Lower threshold for temporal patterns
                    for folder_template in pattern_info["folder_suggestions"]:
                        folder_name = folder_template.format(year=current_year)
                        
                        suggestion = FolderSuggestion(
                            suggestion_id=f"temporal_{user_id}_{pattern_name}_{current_year}",
                            user_id=user_id,
                            folder_name=folder_name,
                            folder_path=f"/{folder_name}",
                            description=f"Organize files for {pattern_name.replace('_', ' ')} {current_year}",
                            trigger=SuggestionTrigger.TEMPORAL_PATTERN,
                            confidence=SuggestionConfidence.HIGH if len(matching_files) >= 5 else SuggestionConfidence.MEDIUM,
                            reasoning=f"It's {pattern_name.replace('_', ' ')} season and you have {len(matching_files)} related files",
                            affected_files=matching_files,
                            created_at=datetime.now(),
                            expires_at=datetime.now() + timedelta(days=30),  # Temporal suggestions last longer
                            metadata={"pattern_name": pattern_name, "season": current_month}
                        )
                        
                        suggestions.append(suggestion)
        
        return suggestions
    
    async def _generate_behavioral_suggestions(self, user_id: str, current_files: List[Dict[str, Any]],
                                             user_context: Dict[str, Any]) -> List[FolderSuggestion]:
        """Generate suggestions based on user behavior patterns."""
        suggestions = []
        
        # Check for volume-based suggestions
        if len(current_files) > 50:
            suggestions.append(FolderSuggestion(
                suggestion_id=f"volume_{user_id}_archive",
                user_id=user_id,
                folder_name="Archive - Old Files",
                folder_path="/Archive - Old Files",
                description="Archive older files to keep your main folder organized",
                trigger=SuggestionTrigger.VOLUME_THRESHOLD,
                confidence=SuggestionConfidence.MEDIUM,
                reasoning=f"You have {len(current_files)} files that could benefit from archiving",
                affected_files=[f.get("name", "") for f in current_files],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=14)
            ))
        
        # Check for recent activity patterns
        recent_files = [
            f for f in current_files
            if self._is_recent_file(f, days=7)
        ]
        
        if len(recent_files) >= 10:
            suggestions.append(FolderSuggestion(
                suggestion_id=f"recent_{user_id}_activity",
                user_id=user_id,
                folder_name="Recent Work",
                folder_path="/Recent Work",
                description="Keep your recent files easily accessible",
                trigger=SuggestionTrigger.USER_BEHAVIOR,
                confidence=SuggestionConfidence.MEDIUM,
                reasoning=f"You've been very active with {len(recent_files)} files this week",
                affected_files=[f.get("name", "") for f in recent_files],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7)
            ))
        
        return suggestions
    
    def _identify_semantic_category(self, keywords: List[str]) -> Optional[str]:
        """Identify which semantic category keywords belong to."""
        category_scores = {}
        
        for category, category_keywords in self.content_analyzer.semantic_categories.items():
            score = sum(1 for kw in keywords if kw in category_keywords)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _populate_template(self, template: str, user_context: Dict[str, Any], 
                          pattern: ContentPattern) -> str:
        """Populate template with context variables."""
        current_year = datetime.now().year
        current_month = datetime.now().strftime("%B")
        
        # Replace common template variables
        template = template.replace("{year}", str(current_year))
        template = template.replace("{month}", current_month)
        
        # Replace context variables
        for key, value in user_context.items():
            template = template.replace(f"{{{key}}}", str(value))
        
        return template
    
    def _file_matches_pattern(self, file_info: Dict[str, Any], pattern: ContentPattern) -> bool:
        """Check if a file matches a content pattern."""
        filename = file_info.get("name", "").lower()
        content = file_info.get("content", "").lower()
        text_to_check = f"{filename} {content}"
        
        # Check keywords
        keyword_matches = sum(1 for keyword in pattern.keywords if keyword in text_to_check)
        
        # Check file extensions
        extension_match = False
        if pattern.file_extensions and "." in filename:
            file_ext = filename.split(".")[-1].lower()
            extension_match = file_ext in pattern.file_extensions
        
        return keyword_matches >= 2 or extension_match
    
    def _calculate_confidence(self, pattern: ContentPattern, affected_files: List[str]) -> SuggestionConfidence:
        """Calculate confidence level for a suggestion."""
        file_count = len(affected_files)
        keyword_strength = len(pattern.keywords)
        
        if file_count >= 10 and keyword_strength >= 5:
            return SuggestionConfidence.HIGH
        elif file_count >= 6 and keyword_strength >= 3:
            return SuggestionConfidence.MEDIUM
        else:
            return SuggestionConfidence.LOW
    
    def _is_recent_file(self, file_info: Dict[str, Any], days: int = 7) -> bool:
        """Check if file was created recently."""
        created_at = file_info.get("created_at")
        if not created_at:
            return False
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                return False
        
        return (datetime.now() - created_at).days <= days

class FolderSuggestionEngine:
    """Main folder suggestion engine orchestrator."""
    
    def __init__(self):
        self.proactive_engine = ProactiveFolderEngine()
        self.user_suggestions = defaultdict(list)
        self.suggestion_history = defaultdict(list)
        
        print("📁 Folder Suggestion Engine initialized")
    
    async def get_folder_suggestions(self, user_id: str, current_files: List[Dict[str, Any]],
                                   user_context: Dict[str, Any] = None) -> List[FolderSuggestion]:
        """Get proactive folder suggestions for a user."""
        
        # Generate new suggestions
        suggestions = await self.proactive_engine.generate_proactive_suggestions(
            user_id, current_files, user_context
        )
        
        # Filter out suggestions we've already made recently
        filtered_suggestions = []
        for suggestion in suggestions:
            if not self._suggestion_recently_made(user_id, suggestion):
                filtered_suggestions.append(suggestion)
        
        # Cache suggestions
        self.user_suggestions[user_id] = filtered_suggestions
        
        # Add to history
        for suggestion in filtered_suggestions:
            self.suggestion_history[user_id].append({
                "suggestion_id": suggestion.suggestion_id,
                "folder_name": suggestion.folder_name,
                "created_at": suggestion.created_at,
                "confidence": suggestion.confidence.value
            })
        
        # Keep only recent history
        if len(self.suggestion_history[user_id]) > 50:
            self.suggestion_history[user_id] = self.suggestion_history[user_id][-50:]
        
        return filtered_suggestions
    
    def _suggestion_recently_made(self, user_id: str, suggestion: FolderSuggestion) -> bool:
        """Check if similar suggestion was made recently."""
        recent_suggestions = [
            s for s in self.suggestion_history[user_id]
            if (datetime.now() - datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else datetime.now() - s["created_at"]).days <= 7
        ]
        
        for recent in recent_suggestions:
            if recent["folder_name"] == suggestion.folder_name:
                return True
        
        return False
    
    async def accept_suggestion(self, user_id: str, suggestion_id: str) -> Dict[str, Any]:
        """Mark a suggestion as accepted by the user."""
        user_suggestions = self.user_suggestions.get(user_id, [])
        
        for suggestion in user_suggestions:
            if suggestion.suggestion_id == suggestion_id:
                # In a real implementation, this would create the actual folder
                result = {
                    "success": True,
                    "folder_created": suggestion.folder_name,
                    "files_moved": len(suggestion.affected_files),
                    "suggestion_id": suggestion_id
                }
                
                # Remove from active suggestions
                self.user_suggestions[user_id] = [
                    s for s in user_suggestions if s.suggestion_id != suggestion_id
                ]
                
                print(f"✅ Accepted suggestion: {suggestion.folder_name} for {user_id}")
                return result
        
        return {"success": False, "error": "Suggestion not found"}
    
    async def dismiss_suggestion(self, user_id: str, suggestion_id: str) -> Dict[str, Any]:
        """Dismiss a suggestion."""
        user_suggestions = self.user_suggestions.get(user_id, [])
        
        for suggestion in user_suggestions:
            if suggestion.suggestion_id == suggestion_id:
                # Remove from active suggestions
                self.user_suggestions[user_id] = [
                    s for s in user_suggestions if s.suggestion_id != suggestion_id
                ]
                
                print(f"❌ Dismissed suggestion: {suggestion.folder_name} for {user_id}")
                return {"success": True, "suggestion_id": suggestion_id}
        
        return {"success": False, "error": "Suggestion not found"}
    
    async def get_suggestion_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics about folder suggestions for a user."""
        history = self.suggestion_history.get(user_id, [])
        current_suggestions = self.user_suggestions.get(user_id, [])
        
        if not history and not current_suggestions:
            return {"message": "No suggestion history available"}
        
        # Analyze suggestion history
        total_suggestions = len(history)
        confidence_distribution = Counter([s["confidence"] for s in history])
        
        # Recent suggestions
        recent_suggestions = [
            s for s in history
            if (datetime.now() - (datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"])).days <= 7
        ]
        
        return {
            "total_suggestions_made": total_suggestions,
            "current_active_suggestions": len(current_suggestions),
            "recent_suggestions_7_days": len(recent_suggestions),
            "confidence_distribution": dict(confidence_distribution),
            "most_common_triggers": [s.trigger.value for s in current_suggestions],
            "average_files_per_suggestion": sum(len(s.affected_files) for s in current_suggestions) / max(len(current_suggestions), 1)
        }

# CLI interface for testing
async def main():
    """CLI interface for Folder Suggestion Engine testing."""
    engine = FolderSuggestionEngine()
    
    print("📁 Folder Suggestion Engine Test Suite")
    print("=" * 50)
    
    # Test 1: Create mock file data
    print("\n1. Creating mock file data...")
    
    user_id = "test_user"
    current_date = datetime.now()
    
    mock_files = [
        # Financial files
        {"name": "receipt_grocery_2024.jpg", "content": "grocery receipt payment", "created_at": current_date - timedelta(days=5)},
        {"name": "tax_document_w2.pdf", "content": "w2 tax form 2024", "created_at": current_date - timedelta(days=10)},
        {"name": "invoice_client_abc.pdf", "content": "invoice payment due client", "created_at": current_date - timedelta(days=3)},
        {"name": "budget_planning.xlsx", "content": "budget expenses income", "created_at": current_date - timedelta(days=7)},
        
        # Work files
        {"name": "project_alpha_report.docx", "content": "project report meeting client", "created_at": current_date - timedelta(days=2)},
        {"name": "presentation_quarterly.pptx", "content": "quarterly presentation meeting", "created_at": current_date - timedelta(days=4)},
        {"name": "client_meeting_notes.txt", "content": "meeting notes project client", "created_at": current_date - timedelta(days=1)},
        
        # Personal files
        {"name": "vacation_photo1.jpg", "content": "vacation travel photo", "created_at": current_date - timedelta(days=15)},
        {"name": "vacation_photo2.jpg", "content": "vacation travel photo", "created_at": current_date - timedelta(days=15)},
        {"name": "family_birthday.jpg", "content": "family birthday celebration", "created_at": current_date - timedelta(days=8)},
        
        # Medical files
        {"name": "doctor_appointment.pdf", "content": "doctor appointment medical", "created_at": current_date - timedelta(days=6)},
        {"name": "lab_results.pdf", "content": "medical lab test results", "created_at": current_date - timedelta(days=12)},
        {"name": "insurance_card.jpg", "content": "health insurance medical", "created_at": current_date - timedelta(days=20)},
    ]
    
    print(f"✅ Created {len(mock_files)} mock files across multiple categories")
    
    # Test 2: Generate folder suggestions
    print("\n2. Generating folder suggestions...")
    
    user_context = {
        "current_month": current_date.strftime("%B"),
        "current_year": current_date.year,
        "recent_activity": "high",
        "primary_use": "business"
    }
    
    suggestions = await engine.get_folder_suggestions(user_id, mock_files, user_context)
    
    print(f"✅ Generated {len(suggestions)} folder suggestions:")
    for i, suggestion in enumerate(suggestions[:5], 1):
        print(f"   {i}. {suggestion.folder_name}")
        print(f"      Confidence: {suggestion.confidence.value}")
        print(f"      Reasoning: {suggestion.reasoning}")
        print(f"      Affected files: {len(suggestion.affected_files)}")
        print(f"      Trigger: {suggestion.trigger.value}")
    
    # Test 3: Accept a suggestion
    print("\n3. Testing suggestion acceptance...")
    
    if suggestions:
        suggestion_to_accept = suggestions[0]
        result = await engine.accept_suggestion(user_id, suggestion_to_accept.suggestion_id)
        
        if result["success"]:
            print(f"✅ Accepted suggestion: {result['folder_created']}")
            print(f"   Files that would be moved: {result['files_moved']}")
        else:
            print(f"❌ Failed to accept suggestion: {result['error']}")
    
    # Test 4: Dismiss a suggestion
    print("\n4. Testing suggestion dismissal...")
    
    remaining_suggestions = await engine.get_folder_suggestions(user_id, mock_files, user_context)
    if remaining_suggestions:
        suggestion_to_dismiss = remaining_suggestions[0]
        result = await engine.dismiss_suggestion(user_id, suggestion_to_dismiss.suggestion_id)
        
        if result["success"]:
            print(f"✅ Dismissed suggestion: {suggestion_to_dismiss.folder_name}")
        else:
            print(f"❌ Failed to dismiss suggestion: {result['error']}")
    
    # Test 5: Get analytics
    print("\n5. Getting suggestion analytics...")
    
    analytics = await engine.get_suggestion_analytics(user_id)
    if "message" not in analytics:
        print(f"✅ Suggestion analytics:")
        print(f"   Total suggestions made: {analytics['total_suggestions_made']}")
        print(f"   Current active suggestions: {analytics['current_active_suggestions']}")
        print(f"   Recent suggestions (7 days): {analytics['recent_suggestions_7_days']}")
        print(f"   Average files per suggestion: {analytics['average_files_per_suggestion']:.1f}")
    else:
        print(f"ℹ️ {analytics['message']}")
    
    # Test 6: Temporal suggestions (simulate tax season)
    print("\n6. Testing temporal suggestions (tax season simulation)...")
    
    # Add more tax-related files
    tax_files = mock_files + [
        {"name": "1099_form.pdf", "content": "1099 tax form irs", "created_at": datetime(2024, 3, 15)},
        {"name": "deduction_receipts.pdf", "content": "tax deduction receipts", "created_at": datetime(2024, 3, 20)},
        {"name": "tax_software.exe", "content": "tax preparation software", "created_at": datetime(2024, 3, 10)},
    ]
    
    # Simulate it's tax season (March)
    tax_context = {
        "current_month": "March",
        "current_year": 2024,
        "tax_season": True
    }
    
    tax_suggestions = await engine.get_folder_suggestions(user_id + "_tax", tax_files, tax_context)
    tax_season_suggestions = [s for s in tax_suggestions if "tax" in s.folder_name.lower()]
    
    print(f"✅ Tax season suggestions: {len(tax_season_suggestions)}")
    for suggestion in tax_season_suggestions[:2]:
        print(f"   - {suggestion.folder_name}: {suggestion.reasoning}")
    
    print("\n🎉 Folder Suggestion Engine tests completed!")

if __name__ == "__main__":
    asyncio.run(main())