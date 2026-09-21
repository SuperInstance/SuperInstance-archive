#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Federated Search
Search across external sources and integrate results
"""

import asyncio
import json
import logging
import time
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict
from abc import ABC, abstractmethod
import urllib.parse
import re

logger = logging.getLogger(__name__)

@dataclass
class ExternalSource:
    """External search source configuration"""
    id: str
    name: str
    base_url: str
    api_key: Optional[str] = None
    search_endpoint: str = ""
    result_format: str = "json"  # "json", "xml", "html"
    rate_limit: int = 100  # requests per hour
    timeout: float = 5.0
    enabled: bool = True
    weight: float = 1.0  # Result weighting
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class FederatedResult:
    """Result from federated search"""
    source_id: str
    source_name: str
    title: str
    content: str
    url: str
    score: float
    metadata: Dict[str, Any] = None
    retrieved_at: float = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.retrieved_at == 0:
            self.retrieved_at = time.time()

class SearchAdapter(ABC):
    """Base class for search adapters"""
    
    def __init__(self, source: ExternalSource):
        self.source = source
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[FederatedResult]:
        """Perform search on external source"""
        pass
    
    def check_rate_limit(self) -> bool:
        """Check if request is within rate limit"""
        current_time = time.time()
        
        # Reset window if hour has passed
        if current_time - self.request_window_start >= 3600:
            self.request_count = 0
            self.request_window_start = current_time
        
        return self.request_count < self.source.rate_limit
    
    def record_request(self):
        """Record a request for rate limiting"""
        self.request_count += 1
        self.last_request_time = time.time()

class RESTSearchAdapter(SearchAdapter):
    """Generic REST API search adapter"""
    
    async def search(self, query: str, limit: int = 10) -> List[FederatedResult]:
        """Search REST API"""
        if not self.check_rate_limit():
            logger.warning(f"Rate limit exceeded for {self.source.name}")
            return []
        
        try:
            # Build query parameters
            params = {
                "q": query,
                "limit": limit,
                "format": "json"
            }
            
            if self.source.api_key:
                params["api_key"] = self.source.api_key
            
            # Make request
            url = f"{self.source.base_url}/{self.source.search_endpoint}".rstrip('/')
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.source.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Search request failed for {self.source.name}: {response.status}")
                        return []
                    
                    data = await response.json()
                    self.record_request()
                    
                    return self._parse_json_results(data, query)
        
        except asyncio.TimeoutError:
            logger.error(f"Search timeout for {self.source.name}")
            return []
        except Exception as e:
            logger.error(f"Search error for {self.source.name}: {e}")
            return []
    
    def _parse_json_results(self, data: Dict[str, Any], query: str) -> List[FederatedResult]:
        """Parse JSON response into FederatedResult objects"""
        results = []
        
        # Generic JSON parsing - adapt based on actual API responses
        items = data.get("results", data.get("items", data.get("data", [])))
        
        for item in items:
            try:
                result = FederatedResult(
                    source_id=self.source.id,
                    source_name=self.source.name,
                    title=item.get("title", item.get("name", "Untitled")),
                    content=item.get("content", item.get("description", item.get("summary", ""))),
                    url=item.get("url", item.get("link", "")),
                    score=item.get("score", item.get("relevance", 1.0)),
                    metadata={
                        "query": query,
                        "original_data": item
                    }
                )
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Failed to parse result item: {e}")
                continue
        
        return results

class WikipediaSearchAdapter(SearchAdapter):
    """Wikipedia search adapter"""
    
    async def search(self, query: str, limit: int = 10) -> List[FederatedResult]:
        """Search Wikipedia"""
        if not self.check_rate_limit():
            return []
        
        try:
            # Wikipedia API search
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
                "srprop": "snippet|titlesnippet"
            }
            
            url = "https://en.wikipedia.org/w/api.php"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.source.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    self.record_request()
                    
                    results = []
                    search_results = data.get("query", {}).get("search", [])
                    
                    for item in search_results:
                        # Clean HTML tags from snippet
                        snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                        
                        result = FederatedResult(
                            source_id=self.source.id,
                            source_name="Wikipedia",
                            title=item.get("title", ""),
                            content=snippet,
                            url=f"https://en.wikipedia.org/wiki/{urllib.parse.quote(item.get('title', ''))}",
                            score=1.0,  # Wikipedia doesn't provide relevance scores
                            metadata={
                                "query": query,
                                "page_id": item.get("pageid"),
                                "size": item.get("size", 0)
                            }
                        )
                        results.append(result)
                    
                    return results
        
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []

class GitHubSearchAdapter(SearchAdapter):
    """GitHub search adapter"""
    
    async def search(self, query: str, limit: int = 10) -> List[FederatedResult]:
        """Search GitHub repositories and code"""
        if not self.check_rate_limit():
            return []
        
        try:
            # GitHub API requires authentication for higher rate limits
            headers = {}
            if self.source.api_key:
                headers["Authorization"] = f"token {self.source.api_key}"
            
            params = {
                "q": query,
                "per_page": min(limit, 30),  # GitHub max per page
                "sort": "score",
                "order": "desc"
            }
            
            # Search repositories
            url = "https://api.github.com/search/repositories"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.source.timeout)) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"GitHub search failed: {response.status}")
                        return []
                    
                    data = await response.json()
                    self.record_request()
                    
                    results = []
                    items = data.get("items", [])
                    
                    for item in items:
                        result = FederatedResult(
                            source_id=self.source.id,
                            source_name="GitHub",
                            title=f"{item.get('full_name', '')} - {item.get('description', '')[:100]}",
                            content=item.get("description", ""),
                            url=item.get("html_url", ""),
                            score=item.get("score", 1.0),
                            metadata={
                                "query": query,
                                "language": item.get("language"),
                                "stars": item.get("stargazers_count", 0),
                                "forks": item.get("forks_count", 0),
                                "updated_at": item.get("updated_at")
                            }
                        )
                        results.append(result)
                    
                    return results
        
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []

class ArXivSearchAdapter(SearchAdapter):
    """arXiv academic paper search adapter"""
    
    async def search(self, query: str, limit: int = 10) -> List[FederatedResult]:
        """Search arXiv papers"""
        if not self.check_rate_limit():
            return []
        
        try:
            # arXiv API query
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": limit,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            url = "http://export.arxiv.org/api/query"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.source.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return []
                    
                    xml_data = await response.text()
                    self.record_request()
                    
                    return self._parse_arxiv_xml(xml_data, query)
        
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_data: str, query: str) -> List[FederatedResult]:
        """Parse arXiv XML response"""
        results = []
        
        try:
            root = ET.fromstring(xml_data)
            namespace = {"atom": "http://www.w3.org/2005/Atom"}
            
            entries = root.findall("atom:entry", namespace)
            
            for entry in entries:
                title = entry.find("atom:title", namespace)
                summary = entry.find("atom:summary", namespace)
                link = entry.find("atom:id", namespace)
                published = entry.find("atom:published", namespace)
                
                # Get authors
                authors = []
                for author in entry.findall("atom:author", namespace):
                    name = author.find("atom:name", namespace)
                    if name is not None:
                        authors.append(name.text)
                
                result = FederatedResult(
                    source_id=self.source.id,
                    source_name="arXiv",
                    title=title.text if title is not None else "",
                    content=summary.text[:500] if summary is not None else "",
                    url=link.text if link is not None else "",
                    score=1.0,
                    metadata={
                        "query": query,
                        "authors": authors,
                        "published": published.text if published is not None else "",
                        "source_type": "academic_paper"
                    }
                )
                results.append(result)
            
            return results
            
        except ET.ParseError as e:
            logger.error(f"arXiv XML parsing error: {e}")
            return []

class NewsAPIAdapter(SearchAdapter):
    """News API search adapter"""
    
    async def search(self, query: str, limit: int = 10) -> List[FederatedResult]:
        """Search news articles"""
        if not self.check_rate_limit() or not self.source.api_key:
            return []
        
        try:
            params = {
                "q": query,
                "pageSize": min(limit, 100),
                "sortBy": "relevancy",
                "apiKey": self.source.api_key,
                "language": "en"
            }
            
            url = "https://newsapi.org/v2/everything"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.source.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    self.record_request()
                    
                    results = []
                    articles = data.get("articles", [])
                    
                    for article in articles:
                        result = FederatedResult(
                            source_id=self.source.id,
                            source_name="News",
                            title=article.get("title", ""),
                            content=article.get("description", ""),
                            url=article.get("url", ""),
                            score=1.0,
                            metadata={
                                "query": query,
                                "author": article.get("author"),
                                "source": article.get("source", {}).get("name"),
                                "published_at": article.get("publishedAt"),
                                "image_url": article.get("urlToImage")
                            }
                        )
                        results.append(result)
                    
                    return results
        
        except Exception as e:
            logger.error(f"News API search error: {e}")
            return []

class FederatedSearchEngine:
    """Main federated search engine"""
    
    def __init__(self):
        # External sources configuration
        self.sources: Dict[str, ExternalSource] = {}
        self.adapters: Dict[str, SearchAdapter] = {}
        
        # Built-in sources
        self._register_builtin_sources()
        
        # Result aggregation settings
        self.result_merger = ResultMerger()
        
        # Statistics
        self.stats = {
            "searches_performed": 0,
            "sources_queried": defaultdict(int),
            "avg_response_time_ms": 0,
            "total_results_retrieved": 0,
            "failed_requests": defaultdict(int)
        }
    
    def _register_builtin_sources(self):
        """Register built-in search sources"""
        # Wikipedia
        wikipedia_source = ExternalSource(
            id="wikipedia",
            name="Wikipedia",
            base_url="https://en.wikipedia.org",
            search_endpoint="w/api.php",
            rate_limit=200,
            weight=0.8
        )
        self.register_source(wikipedia_source, WikipediaSearchAdapter)
        
        # arXiv
        arxiv_source = ExternalSource(
            id="arxiv",
            name="arXiv",
            base_url="http://export.arxiv.org",
            search_endpoint="api/query",
            result_format="xml",
            rate_limit=100,
            weight=0.9
        )
        self.register_source(arxiv_source, ArXivSearchAdapter)
    
    def register_source(self, source: ExternalSource, adapter_class: type):
        """Register external search source"""
        self.sources[source.id] = source
        self.adapters[source.id] = adapter_class(source)
        logger.info(f"Registered federated source: {source.name}")
    
    def configure_source(self, source_id: str, **config):
        """Configure existing source"""
        if source_id in self.sources:
            source = self.sources[source_id]
            for key, value in config.items():
                if hasattr(source, key):
                    setattr(source, key, value)
    
    async def search(self, query: str, sources: List[str] = None, limit_per_source: int = 10, 
                    total_limit: int = 50) -> List[FederatedResult]:
        """Perform federated search across sources"""
        start_time = time.time()
        
        # Determine sources to search
        search_sources = sources if sources else [s for s in self.sources.keys() if self.sources[s].enabled]
        
        if not search_sources:
            return []
        
        # Search all sources concurrently
        search_tasks = []
        for source_id in search_sources:
            if source_id in self.adapters:
                adapter = self.adapters[source_id]
                task = self._search_source(adapter, query, limit_per_source)
                search_tasks.append((source_id, task))
        
        # Wait for all searches to complete
        all_results = []
        for source_id, task in search_tasks:
            try:
                results = await task
                
                # Apply source weighting
                source_weight = self.sources[source_id].weight
                for result in results:
                    result.score *= source_weight
                
                all_results.extend(results)
                self.stats["sources_queried"][source_id] += 1
                self.stats["total_results_retrieved"] += len(results)
                
            except Exception as e:
                logger.error(f"Federated search failed for {source_id}: {e}")
                self.stats["failed_requests"][source_id] += 1
        
        # Merge and rank results
        merged_results = self.result_merger.merge_results(all_results)
        final_results = merged_results[:total_limit]
        
        # Update statistics
        search_time = (time.time() - start_time) * 1000
        self.stats["searches_performed"] += 1
        
        current_avg = self.stats["avg_response_time_ms"]
        total_searches = self.stats["searches_performed"]
        self.stats["avg_response_time_ms"] = ((current_avg * (total_searches - 1)) + search_time) / total_searches
        
        logger.info(f"Federated search completed: {len(final_results)} results in {search_time:.1f}ms")
        return final_results
    
    async def _search_source(self, adapter: SearchAdapter, query: str, limit: int) -> List[FederatedResult]:
        """Search a single source"""
        try:
            return await adapter.search(query, limit)
        except Exception as e:
            logger.error(f"Source search error: {e}")
            return []
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """Get list of available sources"""
        return [
            {
                "id": source.id,
                "name": source.name,
                "enabled": source.enabled,
                "weight": source.weight,
                "rate_limit": source.rate_limit,
                "metadata": source.metadata
            }
            for source in self.sources.values()
        ]
    
    def enable_source(self, source_id: str):
        """Enable a search source"""
        if source_id in self.sources:
            self.sources[source_id].enabled = True
    
    def disable_source(self, source_id: str):
        """Disable a search source"""
        if source_id in self.sources:
            self.sources[source_id].enabled = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get federated search statistics"""
        return {
            **self.stats,
            "sources_queried": dict(self.stats["sources_queried"]),
            "failed_requests": dict(self.stats["failed_requests"]),
            "registered_sources": len(self.sources),
            "enabled_sources": sum(1 for s in self.sources.values() if s.enabled)
        }

class ResultMerger:
    """Merge and deduplicate federated search results"""
    
    def __init__(self):
        self.similarity_threshold = 0.8  # Title similarity threshold for deduplication
    
    def merge_results(self, results: List[FederatedResult]) -> List[FederatedResult]:
        """Merge and deduplicate results"""
        if not results:
            return []
        
        # Group similar results
        merged_groups = self._group_similar_results(results)
        
        # Select best result from each group
        final_results = []
        for group in merged_groups:
            best_result = self._select_best_result(group)
            final_results.append(best_result)
        
        # Sort by score
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        return final_results
    
    def _group_similar_results(self, results: List[FederatedResult]) -> List[List[FederatedResult]]:
        """Group similar results together"""
        groups = []
        
        for result in results:
            # Find existing group with similar result
            assigned = False
            
            for group in groups:
                if self._are_similar(result, group[0]):
                    group.append(result)
                    assigned = True
                    break
            
            # Create new group if no similar results found
            if not assigned:
                groups.append([result])
        
        return groups
    
    def _are_similar(self, result1: FederatedResult, result2: FederatedResult) -> bool:
        """Check if two results are similar"""
        # Check title similarity
        title_similarity = self._text_similarity(result1.title, result2.title)
        
        # Check URL similarity
        url_similarity = 1.0 if result1.url == result2.url else 0.0
        
        # Combined similarity
        overall_similarity = max(title_similarity, url_similarity)
        
        return overall_similarity >= self.similarity_threshold
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple token overlap"""
        if not text1 or not text2:
            return 0.0
        
        # Tokenize and normalize
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def _select_best_result(self, group: List[FederatedResult]) -> FederatedResult:
        """Select best result from a group of similar results"""
        if len(group) == 1:
            return group[0]
        
        # Score results based on multiple factors
        scored_results = []
        
        for result in group:
            score = result.score
            
            # Boost score for trusted sources
            if result.source_name in ["Wikipedia", "arXiv"]:
                score *= 1.2
            
            # Boost score for results with more content
            if len(result.content) > 100:
                score *= 1.1
            
            # Boost score for results with URLs
            if result.url:
                score *= 1.05
            
            scored_results.append((result, score))
        
        # Return highest scoring result
        best_result = max(scored_results, key=lambda x: x[1])[0]
        
        # Merge metadata from all results in group
        all_metadata = {}
        for result in group:
            all_metadata.update(result.metadata)
        
        best_result.metadata["merged_sources"] = [r.source_name for r in group]
        best_result.metadata["source_count"] = len(group)
        best_result.metadata.update(all_metadata)
        
        return best_result