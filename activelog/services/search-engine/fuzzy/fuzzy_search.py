#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Fuzzy & Phonetic Search
Advanced fuzzy matching and phonetic search capabilities
"""

import re
import logging
import time
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import difflib
import soundex
import metaphone

logger = logging.getLogger(__name__)

@dataclass
class FuzzyMatch:
    """Fuzzy match result"""
    original_term: str
    matched_term: str
    similarity_score: float
    match_type: str  # 'edit_distance', 'phonetic', 'ngram', 'wildcard'
    position: int = 0

class EditDistance:
    """Advanced edit distance calculations"""
    
    @staticmethod
    def levenshtein(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance"""
        if len(s1) < len(s2):
            return EditDistance.levenshtein(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def damerau_levenshtein(s1: str, s2: str) -> int:
        """Calculate Damerau-Levenshtein distance (includes transpositions)"""
        len1, len2 = len(s1), len(s2)
        big_int = max(len1, len2)
        
        # Create dictionary for character positions
        da = defaultdict(int)
        
        # Create matrix
        h = [[big_int for _ in range(len2 + 2)] for _ in range(len1 + 2)]
        h[0][0] = big_int
        
        for i in range(0, len1 + 1):
            h[i + 1][0] = big_int
            h[i + 1][1] = i
        
        for j in range(0, len2 + 1):
            h[0][j + 1] = big_int
            h[1][j + 1] = j
        
        for i in range(1, len1 + 1):
            db = 0
            for j in range(1, len2 + 1):
                i1 = da[s2[j - 1]]
                j1 = db
                cost = 1
                if s1[i - 1] == s2[j - 1]:
                    cost = 0
                    db = j
                
                h[i + 1][j + 1] = min(
                    h[i][j] + cost,  # substitution
                    h[i + 1][j] + 1,  # insertion
                    h[i][j + 1] + 1,  # deletion
                    h[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1)  # transposition
                )
            
            da[s1[i - 1]] = i
        
        return h[len1 + 1][len2 + 1]
    
    @staticmethod
    def jaro_winkler(s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity"""
        # Jaro similarity
        jaro = EditDistance._jaro(s1, s2)
        
        # Winkler modification
        prefix = 0
        for i in range(min(len(s1), len(s2), 4)):
            if s1[i] == s2[i]:
                prefix += 1
            else:
                break
        
        return jaro + (0.1 * prefix * (1 - jaro))
    
    @staticmethod
    def _jaro(s1: str, s2: str) -> float:
        """Calculate Jaro similarity"""
        if not s1 or not s2:
            return 0.0
        
        if s1 == s2:
            return 1.0
        
        len1, len2 = len(s1), len(s2)
        match_window = max(len1, len2) // 2 - 1
        match_window = max(0, match_window)
        
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        
        matches = 0
        transpositions = 0
        
        # Find matches
        for i in range(len1):
            start = max(0, i - match_window)
            end = min(i + match_window + 1, len2)
            
            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = s2_matches[j] = True
                matches += 1
                break
        
        if matches == 0:
            return 0.0
        
        # Find transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
        
        jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3
        return jaro

class PhoneticMatcher:
    """Phonetic matching algorithms"""
    
    def __init__(self):
        # Initialize phonetic algorithms
        self.soundex = soundex.Soundex()
        self.metaphone = metaphone.Metaphone()
    
    def soundex_match(self, word1: str, word2: str) -> bool:
        """Check if words match using Soundex"""
        try:
            return self.soundex(word1) == self.soundex(word2)
        except:
            return False
    
    def metaphone_match(self, word1: str, word2: str) -> bool:
        """Check if words match using Metaphone"""
        try:
            return self.metaphone(word1) == self.metaphone(word2)
        except:
            return False
    
    def double_metaphone_match(self, word1: str, word2: str) -> bool:
        """Check if words match using Double Metaphone"""
        try:
            dm1 = self.metaphone.double_metaphone(word1)
            dm2 = self.metaphone.double_metaphone(word2)
            
            # Check if any of the codes match
            return (dm1[0] == dm2[0] or dm1[0] == dm2[1] or 
                   dm1[1] == dm2[0] or dm1[1] == dm2[1])
        except:
            return False
    
    def phonetic_similarity(self, word1: str, word2: str) -> float:
        """Calculate phonetic similarity score"""
        score = 0.0
        
        if self.soundex_match(word1, word2):
            score += 0.4
        
        if self.metaphone_match(word1, word2):
            score += 0.3
        
        if self.double_metaphone_match(word1, word2):
            score += 0.3
        
        return min(score, 1.0)

class NGramMatcher:
    """N-gram based fuzzy matching"""
    
    def __init__(self, n: int = 2):
        self.n = n
    
    def get_ngrams(self, text: str) -> Set[str]:
        """Extract n-grams from text"""
        text = text.lower()
        ngrams = set()
        
        # Add padding for edge cases
        padded_text = ' ' * (self.n - 1) + text + ' ' * (self.n - 1)
        
        for i in range(len(padded_text) - self.n + 1):
            ngrams.add(padded_text[i:i + self.n])
        
        return ngrams
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate n-gram similarity"""
        ngrams1 = self.get_ngrams(text1)
        ngrams2 = self.get_ngrams(text2)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        return intersection / union if union > 0 else 0.0

class WildcardMatcher:
    """Wildcard pattern matching"""
    
    @staticmethod
    def compile_pattern(pattern: str) -> str:
        """Convert wildcard pattern to regex"""
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)
        
        # Convert wildcards to regex
        regex_pattern = escaped.replace(r'\*', '.*').replace(r'\?', '.')
        
        return f"^{regex_pattern}$"
    
    @staticmethod
    def match(pattern: str, text: str) -> bool:
        """Check if text matches wildcard pattern"""
        try:
            regex = WildcardMatcher.compile_pattern(pattern)
            return bool(re.match(regex, text, re.IGNORECASE))
        except re.error:
            return False
    
    @staticmethod
    def find_matches(pattern: str, candidates: List[str]) -> List[str]:
        """Find all candidates matching wildcard pattern"""
        try:
            regex = WildcardMatcher.compile_pattern(pattern)
            compiled_regex = re.compile(regex, re.IGNORECASE)
            
            return [candidate for candidate in candidates 
                   if compiled_regex.match(candidate)]
        except re.error:
            return []

class FuzzySearchIndex:
    """Fuzzy search index for fast approximate matching"""
    
    def __init__(self, db_path: str = "fuzzy_index.db"):
        self.terms: Dict[str, Set[str]] = defaultdict(set)  # term -> document_ids
        self.ngram_index: Dict[str, Set[str]] = defaultdict(set)  # ngram -> terms
        self.phonetic_index: Dict[str, Set[str]] = defaultdict(set)  # phonetic_code -> terms
        
        # Matchers
        self.phonetic_matcher = PhoneticMatcher()
        self.ngram_matcher = NGramMatcher(2)
        self.edit_distance = EditDistance()
        
        # Database persistence
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database for fuzzy index"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Terms table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fuzzy_terms (
                    term TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    soundex_code TEXT,
                    metaphone_code TEXT,
                    PRIMARY KEY(term, document_id),
                    INDEX(term),
                    INDEX(soundex_code),
                    INDEX(metaphone_code)
                )
            """)
            
            # N-grams table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS term_ngrams (
                    ngram TEXT NOT NULL,
                    term TEXT NOT NULL,
                    PRIMARY KEY(ngram, term),
                    INDEX(ngram)
                )
            """)
            
            conn.commit()
            conn.close()
    
    def add_document_terms(self, document_id: str, terms: List[str]):
        """Add document terms to fuzzy index"""
        for term in terms:
            term_lower = term.lower()
            
            # Add to term index
            self.terms[term_lower].add(document_id)
            
            # Add n-grams
            ngrams = self.ngram_matcher.get_ngrams(term_lower)
            for ngram in ngrams:
                self.ngram_index[ngram].add(term_lower)
            
            # Add phonetic codes
            try:
                soundex_code = self.phonetic_matcher.soundex(term_lower)
                if soundex_code:
                    self.phonetic_index[soundex_code].add(term_lower)
            except:
                pass
            
            # Persist to database
            self._persist_term(term_lower, document_id)
    
    def _persist_term(self, term: str, document_id: str):
        """Persist term to database"""
        def _db_insert():
            try:
                soundex_code = self.phonetic_matcher.soundex(term)
                metaphone_code = self.phonetic_matcher.metaphone(term)
            except:
                soundex_code = None
                metaphone_code = None
            
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                
                # Insert term
                conn.execute("""
                    INSERT OR IGNORE INTO fuzzy_terms 
                    (term, document_id, soundex_code, metaphone_code)
                    VALUES (?, ?, ?, ?)
                """, (term, document_id, soundex_code, metaphone_code))
                
                # Insert n-grams
                ngrams = self.ngram_matcher.get_ngrams(term)
                for ngram in ngrams:
                    conn.execute("""
                        INSERT OR IGNORE INTO term_ngrams (ngram, term)
                        VALUES (?, ?)
                    """, (ngram, term))
                
                conn.commit()
                conn.close()
        
        # Run in background
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(_db_insert)
    
    def find_fuzzy_matches(self, query_term: str, max_edit_distance: int = 2,
                          min_similarity: float = 0.6) -> List[FuzzyMatch]:
        """Find fuzzy matches for a query term"""
        matches = []
        query_lower = query_term.lower()
        
        # 1. Exact match
        if query_lower in self.terms:
            matches.append(FuzzyMatch(
                original_term=query_term,
                matched_term=query_lower,
                similarity_score=1.0,
                match_type='exact'
            ))
        
        # 2. Edit distance matches
        for term in self.terms.keys():
            if abs(len(term) - len(query_lower)) > max_edit_distance:
                continue
            
            edit_dist = self.edit_distance.levenshtein(query_lower, term)
            if edit_dist <= max_edit_distance:
                similarity = 1.0 - (edit_dist / max(len(query_lower), len(term)))
                if similarity >= min_similarity:
                    matches.append(FuzzyMatch(
                        original_term=query_term,
                        matched_term=term,
                        similarity_score=similarity,
                        match_type='edit_distance'
                    ))
        
        # 3. Phonetic matches
        phonetic_candidates = set()
        try:
            soundex_code = self.phonetic_matcher.soundex(query_lower)
            if soundex_code in self.phonetic_index:
                phonetic_candidates.update(self.phonetic_index[soundex_code])
        except:
            pass
        
        for candidate in phonetic_candidates:
            if candidate not in [m.matched_term for m in matches]:
                phonetic_sim = self.phonetic_matcher.phonetic_similarity(query_lower, candidate)
                if phonetic_sim >= min_similarity:
                    matches.append(FuzzyMatch(
                        original_term=query_term,
                        matched_term=candidate,
                        similarity_score=phonetic_sim,
                        match_type='phonetic'
                    ))
        
        # 4. N-gram matches
        query_ngrams = self.ngram_matcher.get_ngrams(query_lower)
        ngram_candidates = set()
        
        for ngram in query_ngrams:
            if ngram in self.ngram_index:
                ngram_candidates.update(self.ngram_index[ngram])
        
        for candidate in ngram_candidates:
            if candidate not in [m.matched_term for m in matches]:
                ngram_sim = self.ngram_matcher.similarity(query_lower, candidate)
                if ngram_sim >= min_similarity:
                    matches.append(FuzzyMatch(
                        original_term=query_term,
                        matched_term=candidate,
                        similarity_score=ngram_sim,
                        match_type='ngram'
                    ))
        
        # Sort by similarity score
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return matches[:10]  # Limit results

class FuzzySearchEngine:
    """Main fuzzy search engine"""
    
    def __init__(self):
        self.fuzzy_index = FuzzySearchIndex()
        self.wildcard_matcher = WildcardMatcher()
        
        # Configuration
        self.config = {
            'max_edit_distance': 2,
            'min_similarity': 0.6,
            'enable_phonetic': True,
            'enable_ngram': True,
            'enable_wildcard': True
        }
        
        # Statistics
        self.stats = {
            'queries_processed': 0,
            'avg_processing_time_ms': 0,
            'fuzzy_matches_found': 0,
            'match_type_distribution': defaultdict(int)
        }
    
    async def search(self, query, limit: int = 50) -> List[Tuple[str, float]]:
        """Perform fuzzy search"""
        start_time = time.time()
        
        try:
            # Handle different query types
            if hasattr(query, 'query'):
                query_text = query.query
            else:
                query_text = str(query)
            
            # Tokenize query
            query_terms = self._tokenize(query_text)
            
            # Find fuzzy matches for each term
            all_document_scores = defaultdict(float)
            
            for term in query_terms:
                # Check for wildcards
                if '*' in term or '?' in term:
                    wildcard_matches = self._search_wildcard(term)
                    for doc_id, score in wildcard_matches:
                        all_document_scores[doc_id] += score
                    continue
                
                # Regular fuzzy matching
                fuzzy_matches = self.fuzzy_index.find_fuzzy_matches(
                    term, 
                    self.config['max_edit_distance'],
                    self.config['min_similarity']
                )
                
                # Aggregate document scores
                for match in fuzzy_matches:
                    matched_term = match.matched_term
                    similarity = match.similarity_score
                    
                    # Get documents containing the matched term
                    document_ids = self.fuzzy_index.terms.get(matched_term, set())
                    
                    for doc_id in document_ids:
                        all_document_scores[doc_id] += similarity
                    
                    self.stats['match_type_distribution'][match.match_type] += 1
                
                self.stats['fuzzy_matches_found'] += len(fuzzy_matches)
            
            # Normalize scores by number of query terms
            if query_terms:
                for doc_id in all_document_scores:
                    all_document_scores[doc_id] /= len(query_terms)
            
            # Sort results by score
            results = sorted(all_document_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self.stats['queries_processed'] += 1
            
            current_avg = self.stats['avg_processing_time_ms']
            total_queries = self.stats['queries_processed']
            self.stats['avg_processing_time_ms'] = ((current_avg * (total_queries - 1)) + processing_time) / total_queries
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Fuzzy search error: {e}")
            return []
    
    def _search_wildcard(self, pattern: str) -> List[Tuple[str, float]]:
        """Search using wildcard patterns"""
        matching_terms = []
        
        # Find terms matching the wildcard pattern
        all_terms = list(self.fuzzy_index.terms.keys())
        matching_terms = self.wildcard_matcher.find_matches(pattern, all_terms)
        
        # Collect document IDs and scores
        document_scores = defaultdict(float)
        
        for term in matching_terms:
            document_ids = self.fuzzy_index.terms.get(term, set())
            for doc_id in document_ids:
                document_scores[doc_id] += 0.8  # Wildcard match score
        
        return list(document_scores.items())
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for fuzzy search"""
        # Basic tokenization
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Remove very short tokens
        tokens = [token for token in tokens if len(token) > 2]
        
        return tokens
    
    def add_document(self, document_id: str, content: str, title: str = ""):
        """Add document to fuzzy search index"""
        # Combine title and content
        full_text = f"{title} {content}"
        
        # Tokenize
        terms = self._tokenize(full_text)
        
        # Add to index
        self.fuzzy_index.add_document_terms(document_id, terms)
    
    def remove_document(self, document_id: str):
        """Remove document from fuzzy index"""
        # Remove from term index
        terms_to_remove = []
        for term, doc_ids in self.fuzzy_index.terms.items():
            if document_id in doc_ids:
                doc_ids.remove(document_id)
                if not doc_ids:
                    terms_to_remove.append(term)
        
        # Clean up empty entries
        for term in terms_to_remove:
            del self.fuzzy_index.terms[term]
    
    def configure(self, **config):
        """Update fuzzy search configuration"""
        self.config.update(config)
    
    def get_similar_terms(self, term: str, limit: int = 10) -> List[FuzzyMatch]:
        """Get terms similar to the given term"""
        return self.fuzzy_index.find_fuzzy_matches(term)[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fuzzy search statistics"""
        return {
            **self.stats,
            'match_type_distribution': dict(self.stats['match_type_distribution']),
            'indexed_terms': len(self.fuzzy_index.terms),
            'configuration': self.config
        }