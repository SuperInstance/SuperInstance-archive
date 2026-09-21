"""
Context Window Optimizer - Minimal Token Usage with Maximum Understanding
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import json
import re

logger = logging.getLogger(__name__)

@dataclass
class OptimizationRequest:
    request_id: str
    task_description: str
    current_context: List[str]
    bot_capabilities: str  # simple, intermediate, advanced, expert
    max_tokens: int
    priority_concepts: List[str] = field(default_factory=list)
    excluded_concepts: List[str] = field(default_factory=list)
    compression_level: str = "high"  # low, medium, high, max
    
@dataclass
class OptimizedContext:
    optimization_id: str
    optimized_content: List[str]
    token_count: int
    token_savings: int
    techniques_used: List[str]
    concept_references: List[str]
    expansion_points: List[str]  # Places where context can be expanded
    confidence_score: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class ContextOptimizer:
    def __init__(self):
        self.optimization_cache: Dict[str, OptimizedContext] = {}
        self.token_patterns = self._load_token_patterns()
        self.compression_strategies = self._load_compression_strategies()
        
    def _load_token_patterns(self) -> Dict[str, int]:
        """Load patterns for token estimation"""
        return {
            "word": 1,          # Average word = 1 token
            "code_block": 1.5,  # Code tends to be more token-dense
            "json": 1.2,        # JSON structure adds tokens
            "url": 0.5,         # URLs often compress well
            "number": 0.3,      # Numbers are token-efficient
            "whitespace": 0.1   # Whitespace minimal tokens
        }
    
    def _load_compression_strategies(self) -> List[Dict[str, Any]]:
        """Load context compression strategies"""
        return [
            {
                "name": "concept_aliasing",
                "description": "Replace long concepts with short aliases",
                "token_reduction": 0.3,
                "quality_impact": 0.1
            },
            {
                "name": "reference_linking", 
                "description": "Use concept IDs instead of full explanations",
                "token_reduction": 0.5,
                "quality_impact": 0.0
            },
            {
                "name": "delta_encoding",
                "description": "Only describe differences from standard patterns",
                "token_reduction": 0.4,
                "quality_impact": 0.05
            },
            {
                "name": "progressive_disclosure",
                "description": "Start minimal, expand only as needed",
                "token_reduction": 0.6,
                "quality_impact": 0.0
            },
            {
                "name": "semantic_compression",
                "description": "Remove redundant information",
                "token_reduction": 0.25,
                "quality_impact": 0.15
            },
            {
                "name": "contextual_pruning",
                "description": "Remove information not relevant to task",
                "token_reduction": 0.35,
                "quality_impact": 0.1
            }
        ]
    
    async def optimize(
        self,
        request_id: str,
        task_description: str,
        current_context: List[str],
        bot_capabilities: str = "advanced",
        max_tokens: int = 4000,
        priority_concepts: List[str] = None
    ) -> Dict[str, Any]:
        """Optimize context for minimal token usage"""
        
        optimization_request = OptimizationRequest(
            request_id=request_id,
            task_description=task_description,
            current_context=current_context or [],
            bot_capabilities=bot_capabilities,
            max_tokens=max_tokens,
            priority_concepts=priority_concepts or []
        )
        
        try:
            # Analyze current context
            current_tokens = await self._estimate_tokens(current_context)
            
            # Determine optimization strategy based on bot capabilities
            strategies = await self._select_optimization_strategies(
                bot_capabilities, 
                current_tokens, 
                max_tokens
            )
            
            # Apply optimization strategies
            optimized_content = await self._apply_optimization_strategies(
                optimization_request,
                strategies
            )
            
            # Calculate savings and effectiveness
            optimized_tokens = await self._estimate_tokens(optimized_content)
            token_savings = current_tokens - optimized_tokens
            
            # Generate expansion points for future use
            expansion_points = await self._identify_expansion_points(
                optimized_content, 
                optimization_request
            )
            
            # Calculate confidence score
            confidence_score = await self._calculate_confidence_score(
                optimization_request,
                optimized_content,
                strategies
            )
            
            optimized_context = OptimizedContext(
                optimization_id=request_id,
                optimized_content=optimized_content,
                token_count=optimized_tokens,
                token_savings=token_savings,
                techniques_used=[s["name"] for s in strategies],
                concept_references=await self._extract_concept_references(optimized_content),
                expansion_points=expansion_points,
                confidence_score=confidence_score
            )
            
            # Cache the result
            self.optimization_cache[request_id] = optimized_context
            
            return {
                "optimization_id": request_id,
                "optimized_content": optimized_content,
                "original_tokens": current_tokens,
                "optimized_tokens": optimized_tokens,
                "token_savings": token_savings,
                "compression_ratio": token_savings / current_tokens if current_tokens > 0 else 0,
                "strategies_used": [s["name"] for s in strategies],
                "expansion_points": expansion_points,
                "confidence_score": confidence_score,
                "bot_optimized_for": bot_capabilities
            }
            
        except Exception as e:
            logger.error(f"Context optimization failed for {request_id}: {e}")
            return {
                "optimization_id": request_id,
                "error": str(e),
                "original_content": current_context
            }
    
    async def progressive_load(
        self,
        session: Dict[str, Any],
        new_requirement: str,
        max_new_tokens: int = 1000
    ) -> Dict[str, Any]:
        """Incrementally load context based on new requirements"""
        
        try:
            # Analyze new requirement
            required_concepts = await self._analyze_requirement_concepts(new_requirement)
            
            # Find concepts not yet loaded
            loaded_concepts = session.get("loaded_concepts", set())
            new_concepts = [c for c in required_concepts if c not in loaded_concepts]
            
            if not new_concepts:
                return {
                    "new_concepts": [],
                    "new_content": [],
                    "message": "No new concepts needed"
                }
            
            # Load new concepts optimized for bot type
            bot_type = session.get("bot_type", "advanced")
            new_content = await self._load_concepts_optimized(
                new_concepts,
                bot_type,
                max_new_tokens
            )
            
            # Estimate token usage
            new_tokens = await self._estimate_tokens(new_content)
            
            return {
                "new_concepts": new_concepts,
                "new_content": new_content,
                "token_count": new_tokens,
                "concepts_loaded": len(new_concepts),
                "remaining_token_budget": max_new_tokens - new_tokens
            }
            
        except Exception as e:
            logger.error(f"Progressive context loading failed: {e}")
            return {
                "error": str(e),
                "new_concepts": [],
                "new_content": []
            }
    
    async def _estimate_tokens(self, content: List[str]) -> int:
        """Estimate token count for content"""
        if not content:
            return 0
        
        total_tokens = 0
        full_text = " ".join(content)
        
        # Word-based estimation (rough approximation)
        words = len(full_text.split())
        total_tokens += words
        
        # Adjust for different content types
        # Code blocks tend to be more token-dense
        code_blocks = len(re.findall(r'```[\s\S]*?```', full_text))
        total_tokens += code_blocks * 50  # Rough estimate for code overhead
        
        # JSON structures
        json_blocks = len(re.findall(r'\{[\s\S]*?\}', full_text))
        total_tokens += json_blocks * 10
        
        # URLs are typically token-efficient
        urls = len(re.findall(r'https?://\S+', full_text))
        total_tokens -= urls * 5  # URLs compress well
        
        # Numbers are very token-efficient
        numbers = len(re.findall(r'\d+', full_text))
        total_tokens -= numbers * 0.5
        
        return max(int(total_tokens), 1)
    
    async def _select_optimization_strategies(
        self,
        bot_capabilities: str,
        current_tokens: int,
        max_tokens: int
    ) -> List[Dict[str, Any]]:
        """Select optimization strategies based on bot capabilities and token pressure"""
        
        token_pressure = current_tokens / max_tokens if max_tokens > 0 else 1.0
        strategies = []
        
        # Always use reference linking - no quality impact
        strategies.append(next(s for s in self.compression_strategies if s["name"] == "reference_linking"))
        
        # High token pressure - aggressive optimization
        if token_pressure > 1.5:
            strategies.extend([
                s for s in self.compression_strategies
                if s["name"] in ["progressive_disclosure", "contextual_pruning", "delta_encoding"]
            ])
        
        # Medium token pressure - balanced optimization
        elif token_pressure > 1.0:
            strategies.extend([
                s for s in self.compression_strategies
                if s["name"] in ["concept_aliasing", "semantic_compression"]
            ])
        
        # Bot capability adjustments
        if bot_capabilities == "simple":
            # Simple bots need more aggressive compression
            if not any(s["name"] == "progressive_disclosure" for s in strategies):
                strategies.append(next(s for s in self.compression_strategies if s["name"] == "progressive_disclosure"))
        
        elif bot_capabilities == "expert":
            # Expert bots can handle more complex references
            if not any(s["name"] == "delta_encoding" for s in strategies):
                strategies.append(next(s for s in self.compression_strategies if s["name"] == "delta_encoding"))
        
        return strategies
    
    async def _apply_optimization_strategies(
        self,
        request: OptimizationRequest,
        strategies: List[Dict[str, Any]]
    ) -> List[str]:
        """Apply selected optimization strategies to context"""
        
        optimized_content = request.current_context.copy()
        
        for strategy in strategies:
            if strategy["name"] == "concept_aliasing":
                optimized_content = await self._apply_concept_aliasing(optimized_content)
            
            elif strategy["name"] == "reference_linking":
                optimized_content = await self._apply_reference_linking(optimized_content)
            
            elif strategy["name"] == "delta_encoding":
                optimized_content = await self._apply_delta_encoding(optimized_content, request)
            
            elif strategy["name"] == "progressive_disclosure":
                optimized_content = await self._apply_progressive_disclosure(optimized_content, request)
            
            elif strategy["name"] == "semantic_compression":
                optimized_content = await self._apply_semantic_compression(optimized_content)
            
            elif strategy["name"] == "contextual_pruning":
                optimized_content = await self._apply_contextual_pruning(optimized_content, request)
        
        return optimized_content
    
    async def _apply_concept_aliasing(self, content: List[str]) -> List[str]:
        """Replace long concepts with short aliases"""
        aliases = {
            "authentication": "auth",
            "authorization": "authz",
            "configuration": "config",
            "database": "db",
            "application": "app",
            "ActiveLog Bot-Orchestrator": "BOT-ORCH",
            "LucidDreamer Core": "LUCID-CORE",
            "Business Platform": "BIZ-PLAT",
            "Municipal Platform": "MUNI-PLAT",
            "Project Memory System": "PROJ-MEM",
            "artificial intelligence": "AI",
            "machine learning": "ML",
            "natural language processing": "NLP"
        }
        
        optimized = []
        for item in content:
            optimized_item = item
            for full_term, alias in aliases.items():
                optimized_item = re.sub(
                    re.escape(full_term), 
                    alias, 
                    optimized_item, 
                    flags=re.IGNORECASE
                )
            optimized.append(optimized_item)
        
        return optimized
    
    async def _apply_reference_linking(self, content: List[str]) -> List[str]:
        """Use concept IDs instead of full explanations"""
        # Look for patterns that match concept references
        reference_patterns = [
            (r"For more information about ([^,\.]+), see", r"Ref: \1"),
            (r"As described in the ([^,\.]+) section", r"→\1"),
            (r"This is similar to ([^,\.]+)", r"~\1"),
            (r"See also: ([^,\.]+)", r"→\1")
        ]
        
        optimized = []
        for item in content:
            optimized_item = item
            for pattern, replacement in reference_patterns:
                optimized_item = re.sub(pattern, replacement, optimized_item, flags=re.IGNORECASE)
            optimized.append(optimized_item)
        
        return optimized
    
    async def _apply_delta_encoding(self, content: List[str], request: OptimizationRequest) -> List[str]:
        """Only describe differences from standard patterns"""
        # This would be more sophisticated in practice
        # For now, identify and compress standard patterns
        
        standard_patterns = {
            "FastAPI service with WebSocket support": "STD-API-WS",
            "PostgreSQL database with Redis caching": "STD-DB-CACHE", 
            "Docker containerization with health checks": "STD-DOCKER",
            "JWT authentication with role-based access": "STD-AUTH",
            "React frontend with TypeScript": "STD-REACT-TS"
        }
        
        optimized = []
        for item in content:
            optimized_item = item
            for pattern, encoding in standard_patterns.items():
                if pattern.lower() in item.lower():
                    optimized_item = optimized_item.replace(pattern, f"Uses {encoding}")
            optimized.append(optimized_item)
        
        return optimized
    
    async def _apply_progressive_disclosure(self, content: List[str], request: OptimizationRequest) -> List[str]:
        """Start minimal, mark expansion points"""
        if request.bot_capabilities == "simple":
            # For simple bots, provide only essential information
            essential = []
            for item in content:
                if len(item) > 200:  # Long content gets summarized
                    summary = item[:100] + "... [+expand]"
                    essential.append(summary)
                else:
                    essential.append(item)
            return essential
        
        # For other bots, mark expansion points but keep content
        enhanced = []
        for item in content:
            if len(item) > 300:
                # Add expansion markers
                enhanced_item = item + " [+details available]"
                enhanced.append(enhanced_item)
            else:
                enhanced.append(item)
        
        return enhanced
    
    async def _apply_semantic_compression(self, content: List[str]) -> List[str]:
        """Remove redundant information"""
        # Remove common redundant phrases
        redundant_phrases = [
            "it is important to note that",
            "please be aware that",
            "it should be mentioned that",
            "as you can see",
            "in other words",
            "that is to say",
            "in summary",
            "to summarize"
        ]
        
        optimized = []
        for item in content:
            compressed_item = item
            for phrase in redundant_phrases:
                compressed_item = re.sub(phrase, "", compressed_item, flags=re.IGNORECASE)
            
            # Clean up extra whitespace
            compressed_item = re.sub(r'\s+', ' ', compressed_item).strip()
            
            if compressed_item:  # Only add non-empty items
                optimized.append(compressed_item)
        
        return optimized
    
    async def _apply_contextual_pruning(self, content: List[str], request: OptimizationRequest) -> List[str]:
        """Remove information not relevant to task"""
        task_keywords = set(request.task_description.lower().split())
        
        # Define relevance based on keyword overlap
        relevant_content = []
        for item in content:
            item_keywords = set(item.lower().split())
            overlap = len(task_keywords.intersection(item_keywords))
            
            # Keep items with significant keyword overlap or priority concepts
            if overlap >= 2 or any(priority in item.lower() for priority in request.priority_concepts):
                relevant_content.append(item)
            elif len(item) < 100:  # Keep short items as they're likely important
                relevant_content.append(item)
        
        return relevant_content if relevant_content else content[:3]  # Keep at least 3 items
    
    async def _identify_expansion_points(
        self, 
        optimized_content: List[str], 
        request: OptimizationRequest
    ) -> List[str]:
        """Identify places where context can be expanded"""
        expansion_points = []
        
        for i, item in enumerate(optimized_content):
            # Look for expansion markers
            if "[+expand]" in item or "[+details available]" in item:
                expansion_points.append(f"Item {i}: Detailed explanation available")
            
            # Look for reference links that could be expanded
            if "→" in item or "Ref:" in item:
                expansion_points.append(f"Item {i}: Reference can be expanded inline")
            
            # Look for compressed concepts
            if any(alias in item for alias in ["STD-", "BOT-", "DREAM-", "BIZ-", "MKT-"]):
                expansion_points.append(f"Item {i}: Compressed concepts can be detailed")
        
        return expansion_points
    
    async def _extract_concept_references(self, content: List[str]) -> List[str]:
        """Extract concept references from optimized content"""
        references = []
        
        for item in content:
            # Look for concept ID patterns
            concept_ids = re.findall(r'\b[A-Z]+-\d{3}\b', item)
            references.extend(concept_ids)
            
            # Look for reference markers
            ref_matches = re.findall(r'Ref:\s*([^,\.\s]+)', item)
            references.extend(ref_matches)
            
            # Look for arrow references
            arrow_matches = re.findall(r'→([^,\.\s]+)', item)
            references.extend(arrow_matches)
        
        return list(set(references))  # Remove duplicates
    
    async def _calculate_confidence_score(
        self,
        request: OptimizationRequest,
        optimized_content: List[str],
        strategies: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for optimization"""
        confidence = 1.0
        
        # Reduce confidence based on quality impact of strategies
        for strategy in strategies:
            confidence -= strategy.get("quality_impact", 0)
        
        # Boost confidence if priority concepts are preserved
        priority_preserved = 0
        for priority in request.priority_concepts:
            if any(priority.lower() in item.lower() for item in optimized_content):
                priority_preserved += 1
        
        if request.priority_concepts:
            priority_ratio = priority_preserved / len(request.priority_concepts)
            confidence += priority_ratio * 0.2
        
        # Reduce confidence for aggressive compression
        original_size = sum(len(item) for item in request.current_context)
        optimized_size = sum(len(item) for item in optimized_content)
        
        if original_size > 0:
            compression_ratio = 1 - (optimized_size / original_size)
            if compression_ratio > 0.7:  # Very aggressive compression
                confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))
    
    async def _analyze_requirement_concepts(self, requirement: str) -> List[str]:
        """Analyze requirement to identify needed concepts"""
        concepts = []
        
        # Simple keyword-based concept identification
        concept_keywords = {
            "authentication": ["auth", "login", "token", "jwt", "security"],
            "database": ["db", "data", "storage", "query", "postgresql", "redis"],
            "api": ["api", "endpoint", "rest", "http", "request", "response"],
            "bot": ["bot", "ai", "llm", "claude", "model", "orchestrator"],
            "dream": ["dream", "simulation", "quantum", "lucid", "reality"],
            "business": ["business", "portfolio", "financial", "analytics"],
            "trading": ["trading", "market", "dividend", "investment", "portfolio"],
            "municipal": ["municipal", "government", "citizen", "public", "services"]
        }
        
        requirement_lower = requirement.lower()
        for concept, keywords in concept_keywords.items():
            if any(keyword in requirement_lower for keyword in keywords):
                concepts.append(concept)
        
        return concepts
    
    async def _load_concepts_optimized(
        self,
        concepts: List[str],
        bot_type: str,
        max_tokens: int
    ) -> List[str]:
        """Load concepts optimized for bot type and token budget"""
        loaded_content = []
        token_budget = max_tokens
        
        # Define concept content based on bot type
        concept_templates = {
            "simple": {
                "authentication": "AUTH: Login with username/password or token",
                "database": "DB: Store/retrieve data using PostgreSQL+Redis", 
                "api": "API: HTTP endpoints for service communication",
                "bot": "BOT: AI assistant that processes tasks",
                "dream": "DREAM: Simulation environment with variable speed",
                "business": "BIZ: Business analytics and management tools",
                "trading": "TRADE: Market simulation and portfolio management",
                "municipal": "GOVT: Government services and citizen portal"
            },
            "intermediate": {
                "authentication": "AUTH: JWT-based authentication with 30min access tokens, 7-day refresh. Role-based access control.",
                "database": "DB: PostgreSQL primary storage with Redis caching. Connection pooling and query optimization.",
                "api": "API: RESTful endpoints with WebSocket support. Rate limiting and error handling.",
                "bot": "BOT: Multi-LLM orchestration with Claude, Ollama, GPT4All. Task complexity routing.",
                "dream": "DREAM: Quantum-inspired simulation with 1x-100,000x speed. Reality anchoring system.",
                "business": "BIZ: Portfolio management with financial intelligence and market data integration.",
                "trading": "TRADE: Real-time market simulation with risk analytics and backtesting engine.",
                "municipal": "GOVT: Citizen services portal with public safety coordination and infrastructure monitoring."
            },
            "advanced": {
                "authentication": "AUTH: Comprehensive JWT authentication system with secure session management, role-based access control (admin/user/guest), encrypted HTTPS-only communications, and GDPR/SOC2 compliance ready.",
                "database": "DB: PostgreSQL 16 with connection pooling, automated backups, Redis caching layer for performance optimization, pub/sub messaging, and multi-tenant architecture support.",
                "api": "API: RESTful design with WebSocket real-time communication, comprehensive error handling, rate limiting, API versioning, OpenAPI documentation, and monitoring integration.",
                "bot": "BOT: Advanced bot orchestration with Claude Max 20x integration, intelligent multi-LLM routing (Ollama/GPT4All/Mistral), 5-hour session management, task complexity analysis, and automated failover mechanisms.",
                "dream": "DREAM: Quantum-inspired dream engine with superposition states, variable-speed simulation (1x to 100,000x), multi-scale instance coordination, React+Three.js 3D visualization, and collaborative features.",
                "business": "BIZ: Comprehensive business platform with multi-business portfolio management, financial analytics, market intelligence integration, automated decision support, and compliance tracking.",
                "trading": "TRADE: Advanced paper trading platform with real-time market data, portfolio management, risk analytics (VaR, Sharpe ratios), backtesting engine, and educational tools.",
                "municipal": "GOVT: Full-service municipal platform with citizen portal, public safety coordination, infrastructure monitoring, emergency response management, and regulatory compliance tracking."
            }
        }
        
        templates = concept_templates.get(bot_type, concept_templates["intermediate"])
        
        for concept in concepts:
            if concept in templates and token_budget > 0:
                content = templates[concept]
                content_tokens = await self._estimate_tokens([content])
                
                if content_tokens <= token_budget:
                    loaded_content.append(content)
                    token_budget -= content_tokens
                else:
                    # Truncate if over budget
                    truncated = content[:int(len(content) * (token_budget / content_tokens))]
                    loaded_content.append(truncated + "...")
                    break
        
        return loaded_content
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get context optimization analytics"""
        if not self.optimization_cache:
            return {"optimizations_performed": 0}
        
        total_original_tokens = 0
        total_optimized_tokens = 0
        strategy_usage = {}
        
        for opt in self.optimization_cache.values():
            original_tokens = opt.token_count + opt.token_savings
            total_original_tokens += original_tokens
            total_optimized_tokens += opt.token_count
            
            for strategy in opt.techniques_used:
                strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
        
        overall_compression = 1.0 - (total_optimized_tokens / total_original_tokens) if total_original_tokens > 0 else 0
        
        return {
            "optimizations_performed": len(self.optimization_cache),
            "total_token_savings": total_original_tokens - total_optimized_tokens,
            "overall_compression_ratio": overall_compression,
            "average_confidence": sum(opt.confidence_score for opt in self.optimization_cache.values()) / len(self.optimization_cache),
            "strategy_usage": strategy_usage,
            "cache_size": len(self.optimization_cache)
        }
    
    def is_operational(self) -> bool:
        """Check if context optimizer is operational"""
        return len(self.compression_strategies) > 0 and len(self.token_patterns) > 0