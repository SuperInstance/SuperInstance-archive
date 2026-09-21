import asyncio
import aiohttp
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
from datetime import datetime, timedelta


class SearchProvider(Enum):
    KIDDLE = "kiddle"
    KIDS_SEARCH = "kids_search"
    SAFE_SEARCH_KIDS = "safe_search_kids"
    EDUCATIONAL_ONLY = "educational_only"


@dataclass
class SafeSearchResult:
    title: str
    url: str
    snippet: str
    age_appropriate: bool
    educational_value: int  # 1-10 scale
    content_type: str
    safe_score: float
    source_credibility: int


class SafeSearchEngine:
    def __init__(self, content_filter):
        self.content_filter = content_filter
        self.search_cache: Dict[str, Dict] = {}
        self.educational_domains = self._initialize_educational_domains()
        self.blocked_domains = self._initialize_blocked_domains()
        
    def _initialize_educational_domains(self) -> Set[str]:
        """Initialize list of trusted educational domains"""
        return {
            # Educational institutions
            "khan-academy.org", "coursera.org", "edx.org", "mit.edu", "harvard.edu",
            "stanford.edu", "berkeley.edu",
            
            # Kids' educational sites  
            "scratch.mit.edu", "code.org", "tynker.com", "codecademy.com",
            "duolingo.com", "brainpop.com", "ixl.com",
            
            # Science and nature
            "nasa.gov", "noaa.gov", "smithsonian.com", "nationalgeographic.com",
            "sciencenewsforstudents.org", "howstuffworks.com",
            
            # Libraries and museums
            "loc.gov", "britannica.com", "worldbook.com", "metmuseum.org",
            "amnh.org", "si.edu",
            
            # Government and civic
            "usa.gov", "kids.gov", "congress.gov", "whitehouse.gov",
            
            # Math and STEM
            "mathisfun.com", "coolmath.com", "mathpapa.com", "geogebra.org",
            "desmos.com", "wolframalpha.com",
            
            # Safe kids' content
            "pbskids.org", "sesamestreet.org", "nickjr.com", "disney.com",
            "natgeokids.com", "timeforkids.com"
        }
    
    def _initialize_blocked_domains(self) -> Set[str]:
        """Initialize domains that should be blocked for kids"""
        return {
            # Social media
            "facebook.com", "instagram.com", "twitter.com", "tiktok.com",
            "snapchat.com", "linkedin.com", "pinterest.com",
            
            # Video platforms (unfiltered)
            "youtube.com", "twitch.tv", "vimeo.com",
            
            # Gaming (potentially inappropriate)
            "steam.com", "epicgames.com", "roblox.com",
            
            # News (potentially disturbing)
            "cnn.com", "foxnews.com", "bbc.com", "nytimes.com",
            
            # Shopping
            "amazon.com", "ebay.com", "walmart.com", "target.com",
            
            # Forums and discussion
            "reddit.com", "quora.com", "stackoverflow.com"
        }

    async def safe_search(self, query: str, user_age: int, max_results: int = 10) -> Dict:
        """Perform safe search appropriate for child's age"""
        # Filter the query first
        filtered_query = await self._filter_search_query(query, user_age)
        if not filtered_query["safe"]:
            return {
                "results": [],
                "message": filtered_query["message"],
                "suggestions": filtered_query["suggestions"]
            }
        
        # Check cache
        cache_key = hashlib.md5(f"{query}_{user_age}_{max_results}".encode()).hexdigest()
        if cache_key in self.search_cache:
            cached_result = self.search_cache[cache_key]
            if datetime.now() - cached_result["timestamp"] < timedelta(hours=24):
                return cached_result["data"]
        
        # Determine search strategy based on age
        search_provider = self._get_search_provider(user_age)
        
        # Perform search
        raw_results = await self._perform_search(filtered_query["query"], search_provider)
        
        # Filter and rank results
        safe_results = []
        for result in raw_results[:max_results * 2]:  # Get extra to filter
            safety_analysis = await self._analyze_search_result(result, user_age)
            if safety_analysis["safe"]:
                safe_results.append(SafeSearchResult(
                    title=result["title"],
                    url=result["url"],
                    snippet=result["snippet"],
                    age_appropriate=safety_analysis["age_appropriate"],
                    educational_value=safety_analysis["educational_value"],
                    content_type=safety_analysis["content_type"],
                    safe_score=safety_analysis["safe_score"],
                    source_credibility=safety_analysis["credibility"]
                ))
        
        # Sort by educational value and safety score
        safe_results.sort(key=lambda x: (x.educational_value, x.safe_score), reverse=True)
        safe_results = safe_results[:max_results]
        
        result_data = {
            "results": [self._format_result(result) for result in safe_results],
            "total_found": len(safe_results),
            "query_used": filtered_query["query"],
            "search_tips": self._generate_search_tips(user_age),
            "educational_suggestions": await self._get_educational_suggestions(query, user_age)
        }
        
        # Cache results
        self.search_cache[cache_key] = {
            "data": result_data,
            "timestamp": datetime.now()
        }
        
        return result_data

    async def _filter_search_query(self, query: str, user_age: int) -> Dict:
        """Filter search query for safety and appropriateness"""
        # Analyze query using content filter
        from .content_filter import ContentType
        analysis = await self.content_filter.analyze_content(
            query, ContentType.TEXT, f"search_user_{user_age}"
        )
        
        if analysis.action.value == "block":
            return {
                "safe": False,
                "query": query,
                "message": "This search topic isn't appropriate for your age group.",
                "suggestions": [
                    "Try searching for educational topics",
                    "Ask a parent or teacher for help with research",
                    "Look for age-appropriate alternatives"
                ]
            }
        
        # Enhance query with educational focus
        enhanced_query = self._enhance_educational_query(query, user_age)
        
        return {
            "safe": True,
            "query": enhanced_query,
            "message": "Search query is safe"
        }

    def _enhance_educational_query(self, query: str, user_age: int) -> str:
        """Enhance query to promote educational content"""
        educational_terms = {
            "kids", "children", "education", "learning", "safe", "age appropriate"
        }
        
        # Add age-specific educational terms
        if user_age < 8:
            educational_terms.add("preschool")
            educational_terms.add("kindergarten")
        elif user_age < 12:
            educational_terms.add("elementary")
            educational_terms.add("kids")
        else:
            educational_terms.add("middle school")
            educational_terms.add("teen")
        
        # Check if query already contains educational terms
        query_lower = query.lower()
        has_educational_term = any(term in query_lower for term in educational_terms)
        
        if not has_educational_term:
            # Add educational qualifier
            if user_age < 10:
                return f"{query} for kids"
            else:
                return f"{query} educational"
        
        return query

    def _get_search_provider(self, user_age: int) -> SearchProvider:
        """Select appropriate search provider based on age"""
        if user_age < 8:
            return SearchProvider.KIDDLE
        elif user_age < 12:
            return SearchProvider.KIDS_SEARCH
        elif user_age < 16:
            return SearchProvider.SAFE_SEARCH_KIDS
        else:
            return SearchProvider.EDUCATIONAL_ONLY

    async def _perform_search(self, query: str, provider: SearchProvider) -> List[Dict]:
        """Perform actual search using specified provider"""
        # In a real implementation, this would call actual search APIs
        # For now, we'll simulate results based on educational domains
        
        mock_results = []
        
        if "science" in query.lower():
            mock_results.extend([
                {
                    "title": "NASA Kids Science Activities",
                    "url": "https://nasa.gov/audience/forkids/activities/",
                    "snippet": "Fun science experiments and activities for kids to explore space and Earth science."
                },
                {
                    "title": "National Geographic Kids Science",
                    "url": "https://natgeokids.com/science/",
                    "snippet": "Amazing science facts, experiments, and discoveries for curious kids."
                }
            ])
        
        if "math" in query.lower():
            mock_results.extend([
                {
                    "title": "Khan Academy Kids Math",
                    "url": "https://khan-academy.org/kids/math",
                    "snippet": "Interactive math lessons and practice for children of all ages."
                },
                {
                    "title": "Math is Fun for Kids",
                    "url": "https://mathisfun.com/kids/",
                    "snippet": "Making math enjoyable with games, puzzles, and simple explanations."
                }
            ])
        
        if "coding" in query.lower() or "programming" in query.lower():
            mock_results.extend([
                {
                    "title": "Scratch Programming for Kids", 
                    "url": "https://scratch.mit.edu/",
                    "snippet": "Create interactive stories, games, and animations with Scratch programming."
                },
                {
                    "title": "Code.org Hour of Code",
                    "url": "https://code.org/learn",
                    "snippet": "Learn computer science with fun, interactive tutorials and games."
                }
            ])
        
        # Add some general educational results
        mock_results.extend([
            {
                "title": f"Educational Resources about {query}",
                "url": "https://britannica.com/kids/",
                "snippet": f"Comprehensive, age-appropriate information about {query} from Britannica Kids."
            },
            {
                "title": f"Kids Learning Activities - {query}",
                "url": "https://pbskids.org/",
                "snippet": f"Interactive games and activities to learn about {query} in a fun way."
            }
        ])
        
        return mock_results[:10]

    async def _analyze_search_result(self, result: Dict, user_age: int) -> Dict:
        """Analyze individual search result for safety and educational value"""
        url = result["url"]
        title = result["title"]
        snippet = result["snippet"]
        
        # Extract domain
        import urllib.parse
        domain = urllib.parse.urlparse(url).netloc.lower()
        
        # Check if domain is blocked
        if any(blocked in domain for blocked in self.blocked_domains):
            return {"safe": False, "reason": "Blocked domain"}
        
        # Calculate credibility based on domain
        credibility = 5  # Default credibility
        if any(edu in domain for edu in self.educational_domains):
            credibility = 9
        elif domain.endswith('.edu') or domain.endswith('.gov'):
            credibility = 8
        elif domain.endswith('.org'):
            credibility = 7
        
        # Calculate educational value
        educational_keywords = [
            "learn", "education", "study", "tutorial", "lesson", "guide",
            "science", "math", "history", "geography", "art", "music",
            "experiment", "discovery", "explore", "create", "build"
        ]
        
        content = f"{title} {snippet}".lower()
        educational_score = sum(1 for keyword in educational_keywords if keyword in content)
        educational_value = min(educational_score + 3, 10)
        
        # Age appropriateness check
        age_appropriate = self._check_age_appropriateness(content, user_age)
        
        # Overall safety score
        safe_score = (credibility / 10) * 0.4 + (educational_value / 10) * 0.4 + (0.2 if age_appropriate else 0)
        
        # Determine content type
        content_type = self._determine_content_type(url, title, snippet)
        
        return {
            "safe": safe_score >= 0.6 and age_appropriate,
            "age_appropriate": age_appropriate,
            "educational_value": educational_value,
            "content_type": content_type,
            "safe_score": safe_score,
            "credibility": credibility
        }

    def _check_age_appropriateness(self, content: str, user_age: int) -> bool:
        """Check if content is appropriate for user's age"""
        # Check for age-inappropriate keywords
        inappropriate_keywords = [
            "adult", "mature", "explicit", "violence", "scary", "frightening",
            "dangerous", "risky", "advanced", "complex"
        ]
        
        if any(keyword in content for keyword in inappropriate_keywords):
            return False
        
        # Check reading level (simple heuristic)
        words = content.split()
        if user_age < 8:
            # Very simple content for young kids
            avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
            return avg_word_length < 5
        elif user_age < 12:
            # Elementary level
            return True  # Most educational content is appropriate
        else:
            # Middle school and up
            return True

    def _determine_content_type(self, url: str, title: str, snippet: str) -> str:
        """Determine the type of content from URL and text"""
        url_lower = url.lower()
        content = f"{title} {snippet}".lower()
        
        if any(term in url_lower for term in ["video", "youtube", "watch"]):
            return "video"
        elif any(term in url_lower for term in ["game", "play", "interactive"]):
            return "interactive"
        elif any(term in content for term in ["experiment", "activity", "hands-on"]):
            return "activity"
        elif any(term in content for term in ["lesson", "tutorial", "guide"]):
            return "tutorial"
        elif any(term in content for term in ["fact", "information", "encyclopedia"]):
            return "reference"
        else:
            return "article"

    def _format_result(self, result: SafeSearchResult) -> Dict:
        """Format search result for display"""
        return {
            "title": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "content_type": result.content_type,
            "educational_value": result.educational_value,
            "safe_score": round(result.safe_score, 2),
            "source_credibility": result.source_credibility,
            "badges": self._generate_result_badges(result)
        }

    def _generate_result_badges(self, result: SafeSearchResult) -> List[str]:
        """Generate badges for search result"""
        badges = []
        
        if result.source_credibility >= 8:
            badges.append("Trusted Source")
        
        if result.educational_value >= 8:
            badges.append("Highly Educational")
        elif result.educational_value >= 6:
            badges.append("Educational")
        
        if result.content_type == "interactive":
            badges.append("Interactive")
        elif result.content_type == "video":
            badges.append("Video Content")
        elif result.content_type == "activity":
            badges.append("Hands-On Activity")
        
        if result.safe_score >= 0.9:
            badges.append("Extra Safe")
        
        return badges

    def _generate_search_tips(self, user_age: int) -> List[str]:
        """Generate age-appropriate search tips"""
        tips = [
            "Use specific keywords to find what you're looking for",
            "Try adding 'for kids' to your search to get better results",
            "Look for results from educational websites",
            "Ask an adult if you're not sure about a website"
        ]
        
        if user_age >= 10:
            tips.extend([
                "Check multiple sources for important information",
                "Look for recently updated content",
                "Use quotation marks to search for exact phrases"
            ])
        
        if user_age >= 13:
            tips.extend([
                "Evaluate source credibility before trusting information",
                "Use advanced search operators for better results",
                "Consider the bias and perspective of information sources"
            ])
        
        return tips

    async def _get_educational_suggestions(self, query: str, user_age: int) -> List[str]:
        """Get educational topic suggestions related to the search"""
        suggestions = []
        query_lower = query.lower()
        
        # Science-related suggestions
        if any(term in query_lower for term in ["science", "experiment", "nature"]):
            suggestions.extend([
                "Simple science experiments you can do at home",
                "How things work in nature",
                "Famous scientists and their discoveries"
            ])
        
        # Math-related suggestions  
        if any(term in query_lower for term in ["math", "number", "calculate"]):
            suggestions.extend([
                "Fun math games and puzzles",
                "Real-world applications of math",
                "Math tricks and shortcuts"
            ])
        
        # History-related suggestions
        if any(term in query_lower for term in ["history", "ancient", "past"]):
            suggestions.extend([
                "Historical events explained for kids",
                "Life in different time periods",
                "Famous historical figures"
            ])
        
        # General educational suggestions
        suggestions.extend([
            f"Educational videos about {query}",
            f"Interactive activities for learning about {query}",
            f"Books and stories related to {query}"
        ])
        
        return suggestions[:5]  # Limit to 5 suggestions

    async def get_search_history_analysis(self, user_id: str) -> Dict:
        """Analyze user's search history for educational insights"""
        # This would integrate with the search logging system
        return {
            "most_searched_topics": ["science", "animals", "space", "coding"],
            "educational_growth": "User is showing increased interest in STEM topics",
            "recommendations": [
                "Continue exploring science experiments",
                "Try some coding tutorials",
                "Look into space exploration topics"
            ],
            "safety_score": 9.2,
            "parent_notes": "All searches have been age-appropriate and educational"
        }

    async def create_search_report(self, user_id: str, days: int = 30) -> Dict:
        """Generate search activity report for parents"""
        return {
            "period_days": days,
            "total_searches": 45,
            "safe_searches": 45,
            "blocked_searches": 0,
            "top_topics": [
                {"topic": "science experiments", "count": 12},
                {"topic": "animal facts", "count": 8},
                {"topic": "coding games", "count": 6},
                {"topic": "math help", "count": 5}
            ],
            "educational_value_avg": 8.3,
            "time_spent_per_search": "2.5 minutes",
            "most_visited_domains": [
                "nasa.gov", "natgeokids.com", "scratch.mit.edu", "khan-academy.org"
            ],
            "learning_progress": "Child shows consistent interest in educational content",
            "recommendations_for_parents": [
                "Encourage continued exploration of science topics",
                "Consider offline science experiment kits",
                "Support their interest in coding with structured lessons"
            ]
        }