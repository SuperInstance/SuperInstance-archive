#!/usr/bin/env python3
"""
Dynamic Bot Language Evolution System
The core language system that Dissertation Bot Dr. LinguaBot is monitoring for graduate research.
Creates evolving communication protocols that optimize token usage and concept transfer between bots.
"""

import asyncio
import json
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from pathlib import Path
import re
import aiohttp
from fastapi import FastAPI, HTTPException
import uvicorn
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dynamic Bot Language Evolution", version="1.0.0")

@dataclass
class LanguageToken:
    """Represents a compressed language token"""
    token: str  # Short representation (e.g., "A1", "B2")
    concept: str  # Full concept (e.g., "initialize_service_connection")
    usage_frequency: int
    domains: List[str]  # Which bot domains use this token
    creation_date: datetime
    last_used: datetime
    compression_ratio: float  # How much space this saves
    complexity_level: int  # 1-10, how complex the concept is

@dataclass
class ConceptPattern:
    """Pattern of frequently used concept sequences"""
    pattern_id: str
    sequence: List[str]  # List of concepts in sequence
    frequency: int
    efficiency_gain: float  # Token savings from using this pattern
    contexts: List[str]  # Where this pattern is used

@dataclass
class BotLanguageProfile:
    """Language profile for a specific bot type"""
    bot_type: str  # "image_generation", "code_generation", etc.
    vocabulary: Dict[str, str]  # token -> concept mapping
    specialized_tokens: Dict[str, str]  # domain-specific tokens
    communication_patterns: List[str]
    efficiency_metrics: Dict[str, float]

class DynamicLanguageSystem:
    """Core dynamic language evolution system"""
    
    def __init__(self):
        self.port = int(os.getenv("PORT", 8485))
        self.database_path = "/home/activeloguser/activelog/services/dynamic-bot-language/language_evolution.db"
        self.vocab_path = "/home/activeloguser/activelog/services/dynamic-bot-language/master_vocabulary"
        self.profiles_path = "/home/activeloguser/activelog/services/dynamic-bot-language/bot_profiles"
        
        # Core language state
        self.master_vocabulary: Dict[str, LanguageToken] = {}
        self.concept_patterns: Dict[str, ConceptPattern] = {}
        self.bot_profiles: Dict[str, BotLanguageProfile] = {}
        
        # Token generation
        self.next_token_id = 1
        self.token_categories = {
            "A": "actions",           # A1, A2, A3...
            "B": "objects",          # B1, B2, B3...  
            "C": "conditions",       # C1, C2, C3...
            "D": "data_structures",  # D1, D2, D3...
            "E": "errors",           # E1, E2, E3...
            "F": "functions",        # F1, F2, F3...
            "G": "generators",       # G1, G2, G3...
            "H": "handlers",         # H1, H2, H3...
            "I": "interfaces",       # I1, I2, I3...
            "J": "jobs",             # J1, J2, J3...
            "K": "keys",             # K1, K2, K3...
            "L": "learning",         # L1, L2, L3...
            "M": "models",           # M1, M2, M3...
            "N": "networks",         # N1, N2, N3...
            "O": "operations",       # O1, O2, O3...
            "P": "patterns",         # P1, P2, P3...
            "Q": "queries",          # Q1, Q2, Q3...
            "R": "resources",        # R1, R2, R3...
            "S": "systems",          # S1, S2, S3...
            "T": "tasks",            # T1, T2, T3...
            "U": "users",            # U1, U2, U3...
            "V": "values",           # V1, V2, V3...
            "W": "workflows",        # W1, W2, W3...
            "X": "extensions",       # X1, X2, X3...
            "Y": "yielding",         # Y1, Y2, Y3...
            "Z": "zones"             # Z1, Z2, Z3...
        }
        
        # Research integration
        self.dissertation_bot_url = "http://localhost:8495"
        self.research_metrics = {}
        
        # Statistics
        self.total_tokens_created = 0
        self.total_compression_achieved = 0.0
        self.communication_efficiency = {}
        
        self._setup_directories()
        self._initialize_database()
        self._load_existing_vocabulary()
        
    def _setup_directories(self):
        """Setup directory structure"""
        dirs = [self.vocab_path, self.profiles_path]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def _initialize_database(self):
        """Initialize language evolution database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Vocabulary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vocabulary (
                token TEXT PRIMARY KEY,
                concept TEXT,
                usage_frequency INTEGER,
                domains TEXT,
                creation_date TEXT,
                last_used TEXT,
                compression_ratio REAL,
                complexity_level INTEGER
            )
        ''')
        
        # Patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                pattern_id TEXT PRIMARY KEY,
                sequence TEXT,
                frequency INTEGER,
                efficiency_gain REAL,
                contexts TEXT,
                created_date TEXT
            )
        ''')
        
        # Bot profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_profiles (
                bot_type TEXT PRIMARY KEY,
                vocabulary TEXT,
                specialized_tokens TEXT,
                communication_patterns TEXT,
                efficiency_metrics TEXT,
                last_updated TEXT
            )
        ''')
        
        # Usage analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_analytics (
                timestamp TEXT,
                bot_id TEXT,
                token TEXT,
                context TEXT,
                efficiency_gained REAL
            )
        ''')
        
        # Research metrics for Dissertation Bot
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS research_metrics (
                timestamp TEXT,
                metric_type TEXT,
                metric_value REAL,
                bot_population INTEGER,
                vocabulary_size INTEGER,
                avg_compression_ratio REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("📚 Language evolution database initialized")
    
    def _load_existing_vocabulary(self):
        """Load existing vocabulary from database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM vocabulary')
        rows = cursor.fetchall()
        
        for row in rows:
            token, concept, freq, domains_json, created, last_used, comp_ratio, complexity = row
            domains = json.loads(domains_json)
            
            self.master_vocabulary[token] = LanguageToken(
                token=token,
                concept=concept,
                usage_frequency=freq,
                domains=domains,
                creation_date=datetime.fromisoformat(created),
                last_used=datetime.fromisoformat(last_used),
                compression_ratio=comp_ratio,
                complexity_level=complexity
            )
        
        conn.close()
        
        if self.master_vocabulary:
            # Update token counter
            token_numbers = []
            for token in self.master_vocabulary.keys():
                if len(token) >= 2 and token[1:].isdigit():
                    token_numbers.append(int(token[1:]))
            
            if token_numbers:
                self.next_token_id = max(token_numbers) + 1
        
        logger.info(f"📖 Loaded {len(self.master_vocabulary)} existing tokens")
    
    def _categorize_concept(self, concept: str) -> str:
        """Categorize a concept to determine token prefix"""
        concept_lower = concept.lower()
        
        # Action words
        if any(word in concept_lower for word in ['execute', 'run', 'start', 'stop', 'create', 'delete', 'update', 'process']):
            return "A"
        
        # Object/Entity words
        elif any(word in concept_lower for word in ['service', 'bot', 'user', 'file', 'data', 'image', 'audio']):
            return "B"
        
        # Condition words
        elif any(word in concept_lower for word in ['if', 'when', 'check', 'validate', 'verify', 'condition']):
            return "C"
        
        # Data structure words
        elif any(word in concept_lower for word in ['list', 'dict', 'array', 'database', 'table', 'record']):
            return "D"
        
        # Error/Exception words
        elif any(word in concept_lower for word in ['error', 'exception', 'fail', 'timeout', 'invalid']):
            return "E"
        
        # Function words
        elif any(word in concept_lower for word in ['function', 'method', 'calculate', 'compute', 'algorithm']):
            return "F"
        
        # Generation words
        elif any(word in concept_lower for word in ['generate', 'create', 'build', 'construct', 'synthesize']):
            return "G"
        
        # Handler words
        elif any(word in concept_lower for word in ['handle', 'manage', 'coordinate', 'orchestrate']):
            return "H"
        
        # Interface words
        elif any(word in concept_lower for word in ['api', 'interface', 'endpoint', 'connection', 'protocol']):
            return "I"
        
        # Job/Task words
        elif any(word in concept_lower for word in ['job', 'task', 'work', 'assignment', 'operation']):
            return "J"
        
        # Learning/ML words
        elif any(word in concept_lower for word in ['learn', 'train', 'model', 'predict', 'classify', 'ml', 'ai']):
            return "L"
        
        # Model words
        elif any(word in concept_lower for word in ['model', 'neural', 'network', 'transformer', 'gpt', 'claude']):
            return "M"
        
        # Network words
        elif any(word in concept_lower for word in ['network', 'cluster', 'distributed', 'mesh', 'topology']):
            return "N"
        
        # Pattern words  
        elif any(word in concept_lower for word in ['pattern', 'template', 'format', 'structure', 'schema']):
            return "P"
        
        # Resource words
        elif any(word in concept_lower for word in ['resource', 'memory', 'cpu', 'storage', 'bandwidth']):
            return "R"
        
        # System words
        elif any(word in concept_lower for word in ['system', 'platform', 'infrastructure', 'architecture']):
            return "S"
        
        # User words
        elif any(word in concept_lower for word in ['user', 'human', 'client', 'customer', 'person']):
            return "U"
        
        # Workflow words
        elif any(word in concept_lower for word in ['workflow', 'pipeline', 'sequence', 'chain', 'flow']):
            return "W"
        
        # Default to "O" for operations
        else:
            return "O"
    
    def create_token(self, concept: str, domain: str = "general", complexity: int = 5) -> str:
        """Create a new compressed token for a concept"""
        
        # Check if concept already has a token
        for token, lang_token in self.master_vocabulary.items():
            if lang_token.concept == concept:
                # Update usage and domain
                if domain not in lang_token.domains:
                    lang_token.domains.append(domain)
                lang_token.usage_frequency += 1
                lang_token.last_used = datetime.now()
                self._save_token_to_db(lang_token)
                return token
        
        # Create new token
        category = self._categorize_concept(concept)
        token = f"{category}{self.next_token_id}"
        self.next_token_id += 1
        
        # Calculate compression ratio
        original_length = len(concept)
        compressed_length = len(token)
        compression_ratio = (original_length - compressed_length) / original_length
        
        lang_token = LanguageToken(
            token=token,
            concept=concept,
            usage_frequency=1,
            domains=[domain],
            creation_date=datetime.now(),
            last_used=datetime.now(),
            compression_ratio=compression_ratio,
            complexity_level=complexity
        )
        
        self.master_vocabulary[token] = lang_token
        self._save_token_to_db(lang_token)
        
        self.total_tokens_created += 1
        self.total_compression_achieved += compression_ratio
        
        logger.info(f"🆕 Created token {token} for '{concept}' (compression: {compression_ratio:.2%})")
        
        # Notify Dissertation Bot of new token creation
        asyncio.create_task(self._notify_research_progress("token_created", {
            "token": token,
            "concept": concept,
            "compression_ratio": compression_ratio,
            "total_vocabulary_size": len(self.master_vocabulary)
        }))
        
        return token
    
    def _save_token_to_db(self, token: LanguageToken):
        """Save token to database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO vocabulary VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            token.token, token.concept, token.usage_frequency,
            json.dumps(token.domains), token.creation_date.isoformat(),
            token.last_used.isoformat(), token.compression_ratio, token.complexity_level
        ))
        
        conn.commit()
        conn.close()
    
    async def analyze_communication_patterns(self, messages: List[str], bot_id: str) -> Dict[str, Any]:
        """Analyze communication patterns to identify tokenization opportunities"""
        
        # Extract concept sequences
        concepts = []
        for message in messages:
            # Simple concept extraction (in production, would use more sophisticated NLP)
            words = re.findall(r'\b\w+\b', message.lower())
            concepts.extend(words)
        
        # Find frequent sequences
        sequence_counts = Counter()
        for i in range(len(concepts) - 1):
            sequence = tuple(concepts[i:i+2])
            sequence_counts[sequence] += 1
        
        # Find sequences worth tokenizing (frequency > 3)
        tokenization_candidates = []
        for sequence, count in sequence_counts.most_common():
            if count >= 3:
                concept = "_".join(sequence)
                potential_compression = self._calculate_potential_compression(concept)
                if potential_compression > 0.3:  # 30% compression threshold
                    tokenization_candidates.append({
                        "concept": concept,
                        "frequency": count,
                        "compression_potential": potential_compression
                    })
        
        # Create tokens for top candidates
        new_tokens = []
        for candidate in tokenization_candidates[:10]:  # Top 10
            token = self.create_token(candidate["concept"], bot_id, complexity=6)
            new_tokens.append(token)
        
        return {
            "bot_id": bot_id,
            "messages_analyzed": len(messages),
            "concepts_extracted": len(concepts),
            "tokenization_candidates": len(tokenization_candidates),
            "new_tokens_created": new_tokens,
            "efficiency_improvement": self._calculate_efficiency_improvement(new_tokens)
        }
    
    def _calculate_potential_compression(self, concept: str) -> float:
        """Calculate potential compression ratio for a concept"""
        category = self._categorize_concept(concept)
        potential_token = f"{category}{self.next_token_id}"
        
        original_length = len(concept)
        compressed_length = len(potential_token)
        
        return (original_length - compressed_length) / original_length if original_length > 0 else 0
    
    def _calculate_efficiency_improvement(self, tokens: List[str]) -> float:
        """Calculate efficiency improvement from new tokens"""
        if not tokens:
            return 0.0
        
        total_improvement = 0.0
        for token in tokens:
            if token in self.master_vocabulary:
                lang_token = self.master_vocabulary[token]
                # Efficiency = compression_ratio * usage_frequency
                efficiency = lang_token.compression_ratio * lang_token.usage_frequency
                total_improvement += efficiency
        
        return total_improvement
    
    async def get_optimized_vocabulary(self, bot_type: str = "general") -> Dict[str, str]:
        """Get optimized vocabulary for a specific bot type"""
        
        if bot_type in self.bot_profiles:
            profile = self.bot_profiles[bot_type]
            return profile.vocabulary
        
        # Create specialized vocabulary
        specialized_vocab = {}
        
        for token, lang_token in self.master_vocabulary.items():
            # Include if:
            # 1. Used in this bot type domain
            # 2. High frequency general tokens
            # 3. High compression ratio tokens
            
            if (bot_type in lang_token.domains or 
                lang_token.usage_frequency >= 10 or 
                lang_token.compression_ratio >= 0.5):
                
                specialized_vocab[token] = lang_token.concept
        
        # Save profile
        profile = BotLanguageProfile(
            bot_type=bot_type,
            vocabulary=specialized_vocab,
            specialized_tokens={},
            communication_patterns=[],
            efficiency_metrics={}
        )
        
        self.bot_profiles[bot_type] = profile
        self._save_bot_profile(profile)
        
        return specialized_vocab
    
    def _save_bot_profile(self, profile: BotLanguageProfile):
        """Save bot profile to database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO bot_profiles VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            profile.bot_type,
            json.dumps(profile.vocabulary),
            json.dumps(profile.specialized_tokens),
            json.dumps(profile.communication_patterns),
            json.dumps(profile.efficiency_metrics),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def translate_message(self, message: str, source_vocab: Dict[str, str], 
                              target_vocab: Dict[str, str]) -> str:
        """Translate message between different bot vocabularies"""
        
        translated = message
        
        # Replace tokens from source to concepts
        for token, concept in source_vocab.items():
            translated = translated.replace(token, concept)
        
        # Replace concepts to target tokens
        for token, concept in target_vocab.items():
            translated = translated.replace(concept, token)
        
        return translated
    
    async def _notify_research_progress(self, event_type: str, data: Dict[str, Any]):
        """Notify Dissertation Bot of research progress"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "title": f"Language Evolution: {event_type}",
                    "content": f"Event: {event_type}\nData: {json.dumps(data, indent=2)}",
                    "importance": 7
                }
                
                async with session.post(
                    f"{self.dissertation_bot_url}/record-observation",
                    params=payload,
                    timeout=2
                ) as response:
                    if response.status == 200:
                        logger.info(f"📊 Notified Dissertation Bot of {event_type}")
                    
        except Exception as e:
            logger.debug(f"Could not notify Dissertation Bot: {e}")
    
    async def generate_research_metrics(self) -> Dict[str, Any]:
        """Generate comprehensive research metrics for Dissertation Bot"""
        
        total_vocab_size = len(self.master_vocabulary)
        avg_compression = sum(t.compression_ratio for t in self.master_vocabulary.values()) / total_vocab_size if total_vocab_size > 0 else 0
        
        # Usage distribution
        usage_stats = [t.usage_frequency for t in self.master_vocabulary.values()]
        avg_usage = sum(usage_stats) / len(usage_stats) if usage_stats else 0
        
        # Domain distribution
        domain_distribution = defaultdict(int)
        for token in self.master_vocabulary.values():
            for domain in token.domains:
                domain_distribution[domain] += 1
        
        # Efficiency metrics
        total_characters_saved = 0
        for token in self.master_vocabulary.values():
            original_length = len(token.concept)
            compressed_length = len(token.token)
            characters_saved = (original_length - compressed_length) * token.usage_frequency
            total_characters_saved += characters_saved
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "vocabulary_size": total_vocab_size,
            "avg_compression_ratio": avg_compression,
            "total_tokens_created": self.total_tokens_created,
            "avg_usage_frequency": avg_usage,
            "total_characters_saved": total_characters_saved,
            "domain_distribution": dict(domain_distribution),
            "efficiency_score": total_characters_saved / total_vocab_size if total_vocab_size > 0 else 0,
            "categories_in_use": len(set(token.token[0] for token in self.master_vocabulary.values())),
            "bot_profiles_created": len(self.bot_profiles)
        }
        
        # Save metrics for research
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO research_metrics VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            metrics["timestamp"],
            "comprehensive_analysis",
            metrics["efficiency_score"],
            metrics["bot_profiles_created"],
            metrics["vocabulary_size"],
            metrics["avg_compression_ratio"]
        ))
        
        conn.commit()
        conn.close()
        
        return metrics

# Initialize the language system
language_system = DynamicLanguageSystem()

@app.on_event("startup")
async def startup_event():
    """Initialize language system on startup"""
    logger.info("🚀 Starting Dynamic Bot Language Evolution System")
    logger.info(f"📚 Loaded {len(language_system.master_vocabulary)} tokens")
    
    # Create some initial foundational tokens
    foundational_concepts = [
        ("initialize_service", "system"),
        ("process_request", "general"), 
        ("generate_response", "general"),
        ("error_handling", "system"),
        ("user_interaction", "interface"),
        ("data_processing", "data"),
        ("model_inference", "ai"),
        ("system_health_check", "monitoring"),
        ("resource_allocation", "system"),
        ("task_completion", "workflow")
    ]
    
    for concept, domain in foundational_concepts:
        token = language_system.create_token(concept, domain, complexity=7)
        logger.info(f"🔧 Foundation token: {token} -> {concept}")
    
    # Notify Dissertation Bot of system initialization
    await language_system._notify_research_progress("system_initialized", {
        "vocabulary_size": len(language_system.master_vocabulary),
        "foundation_tokens": len(foundational_concepts),
        "categories_available": len(language_system.token_categories)
    })

@app.get("/")
async def root():
    """Language system status"""
    return {
        "service": "Dynamic Bot Language Evolution System",
        "status": "evolving",
        "vocabulary_size": len(language_system.master_vocabulary),
        "total_tokens_created": language_system.total_tokens_created,
        "compression_achieved": f"{language_system.total_compression_achieved:.2%}",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/create-token")
async def create_token(concept: str, domain: str = "general", complexity: int = 5):
    """Create a new language token"""
    token = language_system.create_token(concept, domain, complexity)
    return {
        "token": token,
        "concept": concept,
        "domain": domain,
        "vocabulary_size": len(language_system.master_vocabulary)
    }

@app.post("/analyze-communication")
async def analyze_communication(messages: List[str], bot_id: str):
    """Analyze communication patterns and create optimized tokens"""
    analysis = await language_system.analyze_communication_patterns(messages, bot_id)
    return analysis

@app.get("/vocabulary/{bot_type}")
async def get_vocabulary(bot_type: str = "general"):
    """Get optimized vocabulary for a bot type"""
    vocabulary = await language_system.get_optimized_vocabulary(bot_type)
    return {
        "bot_type": bot_type,
        "vocabulary": vocabulary,
        "size": len(vocabulary)
    }

@app.post("/translate")
async def translate_message(message: str, source_bot: str, target_bot: str):
    """Translate message between bot vocabularies"""
    source_vocab = await language_system.get_optimized_vocabulary(source_bot)
    target_vocab = await language_system.get_optimized_vocabulary(target_bot)
    
    translated = await language_system.translate_message(message, source_vocab, target_vocab)
    
    return {
        "original_message": message,
        "translated_message": translated,
        "source_bot": source_bot,
        "target_bot": target_bot
    }

@app.get("/research-metrics")
async def get_research_metrics():
    """Get comprehensive research metrics for Dissertation Bot"""
    metrics = await language_system.generate_research_metrics()
    return metrics

@app.get("/token/{token}")
async def get_token_info(token: str):
    """Get information about a specific token"""
    if token not in language_system.master_vocabulary:
        raise HTTPException(status_code=404, detail="Token not found")
    
    lang_token = language_system.master_vocabulary[token]
    return asdict(lang_token)

@app.get("/patterns")
async def get_communication_patterns():
    """Get identified communication patterns"""
    return {
        "patterns": language_system.concept_patterns,
        "total_patterns": len(language_system.concept_patterns)
    }

@app.get("/health")
async def health_check():
    """Health check for language system"""
    return {
        "status": "evolving_language",
        "vocabulary_health": "optimal",
        "evolution_active": True,
        "research_mode": "dissertation_monitoring",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=language_system.port,
        log_level="info",
        reload=True
    )