"""
Privacy-Preserving Record Linkage
Advanced secure matching of records across datasets without revealing sensitive information
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from enum import Enum
import hashlib
import hmac
import secrets
import asyncio
from datetime import datetime
import numpy as np
from abc import ABC, abstractmethod

class LinkageMethod(Enum):
    PHONETIC_HASHING = "phonetic_hashing"
    BLOOM_FILTERS = "bloom_filters"  
    SECURE_HASH = "secure_hash"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"

class MatchingStrategy(Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    PROBABILISTIC = "probabilistic"
    THRESHOLD_BASED = "threshold_based"

class PrivacyLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"

@dataclass
class RecordIdentifier:
    """Unique identifier for a record in linkage process"""
    dataset_id: str
    record_id: str
    source_system: str

@dataclass
class LinkageField:
    """Field used for record linkage with privacy settings"""
    field_name: str
    field_value: str
    weight: float
    is_blocking_field: bool
    privacy_transform: Optional[str] = None

@dataclass
class PrivacyTransform:
    """Privacy transformation applied to linkage fields"""
    transform_type: str
    salt: str
    parameters: Dict[str, Any]
    noise_level: Optional[float] = None

@dataclass
class BloomFilterConfig:
    """Configuration for Bloom filter-based linkage"""
    filter_size: int
    hash_functions: int
    q_gram_size: int
    false_positive_rate: float

@dataclass
class LinkageMatch:
    """Result of record linkage matching"""
    record1: RecordIdentifier
    record2: RecordIdentifier
    confidence_score: float
    matching_fields: List[str]
    match_method: LinkageMethod
    privacy_preserved: bool

@dataclass
class LinkageResult:
    """Complete result of record linkage process"""
    matches: List[LinkageMatch]
    total_records_processed: int
    execution_time: float
    privacy_budget_used: Optional[float]
    quality_metrics: Dict[str, float]

class PhoneticHasher:
    """Phonetic hashing for approximate string matching"""
    
    def __init__(self):
        self.soundex_mapping = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }
    
    def soundex(self, name: str) -> str:
        """Generate Soundex code for phonetic matching"""
        if not name:
            return "0000"
        
        name = name.upper().strip()
        if not name:
            return "0000"
        
        # Keep first letter
        soundex = name[0]
        
        # Process remaining letters
        for char in name[1:]:
            if char in self.soundex_mapping:
                code = self.soundex_mapping[char]
                if soundex[-1] != code:  # Avoid consecutive duplicates
                    soundex += code
        
        # Pad with zeros or truncate to 4 characters
        soundex = soundex[:4].ljust(4, '0')
        return soundex
    
    def double_metaphone(self, word: str) -> Tuple[str, str]:
        """Generate Double Metaphone codes for better phonetic matching"""
        # Simplified Double Metaphone implementation
        word = word.upper().strip()
        if not word:
            return ("", "")
        
        primary = ""
        secondary = ""
        
        # Basic transformations
        transformations = [
            ('PH', 'F'), ('GH', 'F'), ('CK', 'K'),
            ('SCH', 'SK'), ('CH', 'K'), ('TH', 'T')
        ]
        
        for old, new in transformations:
            word = word.replace(old, new)
        
        # Generate metaphone codes (simplified)
        for char in word:
            if char.isalpha():
                primary += char
                secondary += char
        
        return (primary[:6], secondary[:6])

class BloomFilterLinkage:
    """Bloom filter-based privacy-preserving record linkage"""
    
    def __init__(self, config: BloomFilterConfig):
        self.config = config
        self.hash_seeds = [secrets.randbelow(2**32) for _ in range(config.hash_functions)]
    
    def create_bloom_filter(self, q_grams: Set[str]) -> np.ndarray:
        """Create Bloom filter from q-grams"""
        bloom_filter = np.zeros(self.config.filter_size, dtype=bool)
        
        for q_gram in q_grams:
            for seed in self.hash_seeds:
                hash_val = int(hashlib.sha256(f"{q_gram}{seed}".encode()).hexdigest(), 16)
                index = hash_val % self.config.filter_size
                bloom_filter[index] = True
        
        return bloom_filter
    
    def generate_q_grams(self, text: str, q: int) -> Set[str]:
        """Generate q-grams from text"""
        if len(text) < q:
            return {text}
        
        q_grams = set()
        for i in range(len(text) - q + 1):
            q_grams.add(text[i:i + q])
        
        return q_grams
    
    def calculate_similarity(self, filter1: np.ndarray, filter2: np.ndarray) -> float:
        """Calculate Dice coefficient between two Bloom filters"""
        intersection = np.sum(filter1 & filter2)
        union = np.sum(filter1) + np.sum(filter2)
        
        if union == 0:
            return 0.0
        
        return (2 * intersection) / union

class SecureHashLinkage:
    """Secure hash-based record linkage with salting"""
    
    def __init__(self, salt_length: int = 32):
        self.salt_length = salt_length
        self.global_salt = secrets.token_hex(salt_length)
    
    def create_secure_hash(self, value: str, field_salt: Optional[str] = None) -> str:
        """Create secure hash with salting"""
        salt = field_salt or self.global_salt
        combined = f"{value}{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def create_keyed_hash(self, value: str, key: str) -> str:
        """Create HMAC-based keyed hash"""
        return hmac.new(
            key.encode(),
            value.encode(),
            hashlib.sha256
        ).hexdigest()

class PrivacyPreservingRecordLinkage:
    """Main engine for privacy-preserving record linkage"""
    
    def __init__(self, privacy_level: PrivacyLevel = PrivacyLevel.HIGH):
        self.privacy_level = privacy_level
        self.phonetic_hasher = PhoneticHasher()
        self.secure_hasher = SecureHashLinkage()
        self.linkage_history: List[LinkageResult] = []
        self.privacy_budget_used = 0.0
        
        # Default Bloom filter configuration
        self.bloom_config = BloomFilterConfig(
            filter_size=1000,
            hash_functions=5,
            q_gram_size=2,
            false_positive_rate=0.01
        )
        self.bloom_linkage = BloomFilterLinkage(self.bloom_config)
    
    def _apply_privacy_transform(self, field: LinkageField, transform: PrivacyTransform) -> str:
        """Apply privacy transformation to a field"""
        if transform.transform_type == "hash":
            return self.secure_hasher.create_secure_hash(field.field_value, transform.salt)
        elif transform.transform_type == "keyed_hash":
            return self.secure_hasher.create_keyed_hash(field.field_value, transform.salt)
        elif transform.transform_type == "soundex":
            return self.phonetic_hasher.soundex(field.field_value)
        elif transform.transform_type == "metaphone":
            primary, _ = self.phonetic_hasher.double_metaphone(field.field_value)
            return primary
        elif transform.transform_type == "bloom_filter":
            q_grams = self.bloom_linkage.generate_q_grams(
                field.field_value, 
                transform.parameters.get("q_gram_size", 2)
            )
            bloom_filter = self.bloom_linkage.create_bloom_filter(q_grams)
            return bloom_filter.tobytes().hex()
        else:
            return field.field_value
    
    def _calculate_field_similarity(
        self, 
        field1: str, 
        field2: str, 
        method: LinkageMethod
    ) -> float:
        """Calculate similarity between two field values"""
        if method == LinkageMethod.SECURE_HASH:
            return 1.0 if field1 == field2 else 0.0
        elif method == LinkageMethod.PHONETIC_HASHING:
            return 1.0 if field1 == field2 else 0.0
        elif method == LinkageMethod.BLOOM_FILTERS:
            # Convert hex strings back to bloom filters
            try:
                filter1 = np.frombuffer(bytes.fromhex(field1), dtype=bool)
                filter2 = np.frombuffer(bytes.fromhex(field2), dtype=bool)
                return self.bloom_linkage.calculate_similarity(filter1, filter2)
            except:
                return 0.0
        else:
            # Simple string similarity for other methods
            if field1 == field2:
                return 1.0
            return 0.0
    
    def _calculate_record_similarity(
        self, 
        record1_fields: List[Tuple[LinkageField, str]], 
        record2_fields: List[Tuple[LinkageField, str]],
        method: LinkageMethod
    ) -> Tuple[float, List[str]]:
        """Calculate overall similarity between two records"""
        total_weight = 0.0
        weighted_score = 0.0
        matching_fields = []
        
        # Match fields by name
        field1_dict = {field.field_name: (field, transformed) for field, transformed in record1_fields}
        field2_dict = {field.field_name: (field, transformed) for field, transformed in record2_fields}
        
        for field_name in set(field1_dict.keys()) & set(field2_dict.keys()):
            field1, transformed1 = field1_dict[field_name]
            field2, transformed2 = field2_dict[field_name]
            
            similarity = self._calculate_field_similarity(transformed1, transformed2, method)
            weighted_score += similarity * field1.weight
            total_weight += field1.weight
            
            if similarity > 0.8:  # High similarity threshold
                matching_fields.append(field_name)
        
        if total_weight == 0:
            return 0.0, matching_fields
        
        return weighted_score / total_weight, matching_fields
    
    async def link_records(
        self,
        dataset1: Dict[RecordIdentifier, List[LinkageField]],
        dataset2: Dict[RecordIdentifier, List[LinkageField]],
        method: LinkageMethod = LinkageMethod.BLOOM_FILTERS,
        similarity_threshold: float = 0.8,
        privacy_transforms: Optional[Dict[str, PrivacyTransform]] = None
    ) -> LinkageResult:
        """Perform privacy-preserving record linkage"""
        start_time = datetime.now()
        matches = []
        privacy_transforms = privacy_transforms or {}
        
        # Transform all fields for privacy
        transformed_dataset1 = {}
        transformed_dataset2 = {}
        
        for record_id, fields in dataset1.items():
            transformed_fields = []
            for field in fields:
                if field.field_name in privacy_transforms:
                    transform = privacy_transforms[field.field_name]
                    transformed_value = self._apply_privacy_transform(field, transform)
                else:
                    # Apply default transformation based on method
                    if method == LinkageMethod.SECURE_HASH:
                        transformed_value = self.secure_hasher.create_secure_hash(field.field_value)
                    elif method == LinkageMethod.PHONETIC_HASHING:
                        transformed_value = self.phonetic_hasher.soundex(field.field_value)
                    elif method == LinkageMethod.BLOOM_FILTERS:
                        q_grams = self.bloom_linkage.generate_q_grams(field.field_value, 2)
                        bloom_filter = self.bloom_linkage.create_bloom_filter(q_grams)
                        transformed_value = bloom_filter.tobytes().hex()
                    else:
                        transformed_value = field.field_value
                
                transformed_fields.append((field, transformed_value))
            
            transformed_dataset1[record_id] = transformed_fields
        
        for record_id, fields in dataset2.items():
            transformed_fields = []
            for field in fields:
                if field.field_name in privacy_transforms:
                    transform = privacy_transforms[field.field_name]
                    transformed_value = self._apply_privacy_transform(field, transform)
                else:
                    # Apply default transformation based on method
                    if method == LinkageMethod.SECURE_HASH:
                        transformed_value = self.secure_hasher.create_secure_hash(field.field_value)
                    elif method == LinkageMethod.PHONETIC_HASHING:
                        transformed_value = self.phonetic_hasher.soundex(field.field_value)
                    elif method == LinkageMethod.BLOOM_FILTERS:
                        q_grams = self.bloom_linkage.generate_q_grams(field.field_value, 2)
                        bloom_filter = self.bloom_linkage.create_bloom_filter(q_grams)
                        transformed_value = bloom_filter.tobytes().hex()
                    else:
                        transformed_value = field.field_value
                
                transformed_fields.append((field, transformed_value))
            
            transformed_dataset2[record_id] = transformed_fields
        
        # Perform blocking if blocking fields are specified
        blocks1 = self._create_blocks(transformed_dataset1)
        blocks2 = self._create_blocks(transformed_dataset2)
        
        # Compare records within matching blocks
        for block_key in set(blocks1.keys()) & set(blocks2.keys()):
            block1_records = blocks1[block_key]
            block2_records = blocks2[block_key]
            
            for record1_id in block1_records:
                for record2_id in block2_records:
                    similarity, matching_fields = self._calculate_record_similarity(
                        transformed_dataset1[record1_id],
                        transformed_dataset2[record2_id],
                        method
                    )
                    
                    if similarity >= similarity_threshold:
                        match = LinkageMatch(
                            record1=record1_id,
                            record2=record2_id,
                            confidence_score=similarity,
                            matching_fields=matching_fields,
                            match_method=method,
                            privacy_preserved=True
                        )
                        matches.append(match)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        total_records = len(dataset1) + len(dataset2)
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(matches, total_records)
        
        result = LinkageResult(
            matches=matches,
            total_records_processed=total_records,
            execution_time=execution_time,
            privacy_budget_used=None,
            quality_metrics=quality_metrics
        )
        
        self.linkage_history.append(result)
        return result
    
    def _create_blocks(
        self, 
        transformed_dataset: Dict[RecordIdentifier, List[Tuple[LinkageField, str]]]
    ) -> Dict[str, List[RecordIdentifier]]:
        """Create blocking keys for efficient comparison"""
        blocks = {}
        
        for record_id, fields in transformed_dataset.items():
            # Use blocking fields to create block keys
            blocking_values = []
            for field, transformed in fields:
                if field.is_blocking_field:
                    blocking_values.append(transformed[:4])  # Use first 4 characters for blocking
            
            if blocking_values:
                block_key = "_".join(blocking_values)
            else:
                block_key = "default"
            
            if block_key not in blocks:
                blocks[block_key] = []
            blocks[block_key].append(record_id)
        
        return blocks
    
    def _calculate_quality_metrics(self, matches: List[LinkageMatch], total_records: int) -> Dict[str, float]:
        """Calculate quality metrics for linkage results"""
        if not matches:
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "match_rate": 0.0
            }
        
        # Basic quality metrics (would need ground truth for precision/recall)
        match_rate = len(matches) / total_records if total_records > 0 else 0.0
        avg_confidence = sum(match.confidence_score for match in matches) / len(matches)
        
        return {
            "match_rate": match_rate,
            "average_confidence": avg_confidence,
            "total_matches": len(matches),
            "unique_records_matched": len(set(match.record1.record_id for match in matches) | 
                                       set(match.record2.record_id for match in matches))
        }
    
    async def evaluate_linkage_quality(
        self, 
        result: LinkageResult,
        ground_truth: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, float]:
        """Evaluate quality of record linkage results"""
        metrics = result.quality_metrics.copy()
        
        if ground_truth:
            # Calculate precision, recall, F1 with ground truth
            true_matches = set(ground_truth)
            predicted_matches = set(
                (match.record1.record_id, match.record2.record_id) 
                for match in result.matches
            )
            
            true_positives = len(true_matches & predicted_matches)
            false_positives = len(predicted_matches - true_matches)
            false_negatives = len(true_matches - predicted_matches)
            
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
            f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            metrics.update({
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives
            })
        
        return metrics

def create_record_linkage_engine(
    privacy_level: PrivacyLevel = PrivacyLevel.HIGH,
    bloom_filter_size: int = 1000,
    hash_functions: int = 5
) -> PrivacyPreservingRecordLinkage:
    """Factory function to create a privacy-preserving record linkage engine"""
    engine = PrivacyPreservingRecordLinkage(privacy_level)
    
    # Configure Bloom filter settings
    engine.bloom_config = BloomFilterConfig(
        filter_size=bloom_filter_size,
        hash_functions=hash_functions,
        q_gram_size=2,
        false_positive_rate=0.01
    )
    engine.bloom_linkage = BloomFilterLinkage(engine.bloom_config)
    
    return engine

# Example usage
async def example_usage():
    """Example of using privacy-preserving record linkage"""
    
    # Create record linkage engine
    linkage_engine = create_record_linkage_engine(
        privacy_level=PrivacyLevel.HIGH,
        bloom_filter_size=2000,
        hash_functions=7
    )
    
    # Create sample datasets
    dataset1 = {
        RecordIdentifier("db1", "1", "system_a"): [
            LinkageField("first_name", "John", 0.3, True),
            LinkageField("last_name", "Smith", 0.4, True),
            LinkageField("birth_date", "1985-03-15", 0.3, False)
        ],
        RecordIdentifier("db1", "2", "system_a"): [
            LinkageField("first_name", "Jane", 0.3, True),
            LinkageField("last_name", "Doe", 0.4, True),
            LinkageField("birth_date", "1990-07-22", 0.3, False)
        ]
    }
    
    dataset2 = {
        RecordIdentifier("db2", "A", "system_b"): [
            LinkageField("first_name", "Jon", 0.3, True),  # Slight variation
            LinkageField("last_name", "Smith", 0.4, True),
            LinkageField("birth_date", "1985-03-15", 0.3, False)
        ],
        RecordIdentifier("db2", "B", "system_b"): [
            LinkageField("first_name", "Jane", 0.3, True),
            LinkageField("last_name", "Doe", 0.4, True),
            LinkageField("birth_date", "1990-07-22", 0.3, False)
        ]
    }
    
    # Define privacy transforms
    privacy_transforms = {
        "birth_date": PrivacyTransform("hash", secrets.token_hex(16), {}),
        "first_name": PrivacyTransform("soundex", "", {}),
        "last_name": PrivacyTransform("bloom_filter", "", {"q_gram_size": 2})
    }
    
    # Perform record linkage using Bloom filters
    result = await linkage_engine.link_records(
        dataset1,
        dataset2,
        method=LinkageMethod.BLOOM_FILTERS,
        similarity_threshold=0.7,
        privacy_transforms=privacy_transforms
    )
    
    print(f"Found {len(result.matches)} matches")
    for match in result.matches:
        print(f"Match: {match.record1.record_id} <-> {match.record2.record_id}")
        print(f"Confidence: {match.confidence_score:.3f}")
        print(f"Matching fields: {match.matching_fields}")
        print()
    
    # Evaluate quality
    quality_metrics = await linkage_engine.evaluate_linkage_quality(result)
    print("Quality Metrics:")
    for metric, value in quality_metrics.items():
        print(f"  {metric}: {value}")

if __name__ == "__main__":
    asyncio.run(example_usage())