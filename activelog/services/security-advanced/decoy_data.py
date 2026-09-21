"""
Decoy Data Generation for Security
Generate realistic fake data to confuse attackers and protect real information
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
from enum import Enum
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
import json
import random
import numpy as np
from abc import ABC, abstractmethod
import string
import re

class DecoyType(Enum):
    HONEYPOT_RECORDS = "honeypot_records"
    SYNTHETIC_USERS = "synthetic_users"
    FAKE_DOCUMENTS = "fake_documents"
    CANARY_TOKENS = "canary_tokens"
    POISON_DATA = "poison_data"
    DECOY_DATABASES = "decoy_databases"
    FAKE_CREDENTIALS = "fake_credentials"

class DetectionMethod(Enum):
    ACCESS_PATTERN = "access_pattern"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    BEHAVIORAL_SIGNATURE = "behavioral_signature"
    CONTENT_FINGERPRINT = "content_fingerprint"

class DecoyStatus(Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    COMPROMISED = "compromised"
    DISABLED = "disabled"

class RealisticLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PERFECT = "perfect"

@dataclass
class DecoyMetadata:
    """Metadata for tracking decoy data"""
    decoy_id: str
    decoy_type: DecoyType
    creation_time: datetime
    last_accessed: Optional[datetime]
    access_count: int
    detection_methods: List[DetectionMethod]
    realistic_level: RealisticLevel
    source_dataset: Optional[str] = None

@dataclass
class DecoyDetection:
    """Detection event when decoy is accessed"""
    detection_id: str
    decoy_id: str
    detected_at: datetime
    accessor_info: Dict[str, Any]
    access_pattern: str
    detection_method: DetectionMethod
    confidence_score: float
    additional_context: Dict[str, Any]

@dataclass
class SyntheticProfile:
    """Synthetic user/entity profile"""
    profile_id: str
    name: str
    email: str
    attributes: Dict[str, Any]
    behavioral_patterns: Dict[str, Any]
    creation_metadata: Dict[str, Any]

@dataclass
class CanaryToken:
    """Unique token embedded in decoy data for tracking"""
    token_id: str
    token_value: str
    embedded_location: str
    callback_url: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class DecoyGenerationConfig:
    """Configuration for decoy data generation"""
    decoy_type: DecoyType
    realistic_level: RealisticLevel
    count: int
    source_patterns: Dict[str, Any]
    detection_methods: List[DetectionMethod]
    expiration_time: Optional[timedelta] = None

class DataPattern(ABC):
    """Abstract base for data pattern analysis"""
    
    @abstractmethod
    async def analyze_pattern(self, data: Any) -> Dict[str, Any]:
        """Analyze data pattern"""
        pass
    
    @abstractmethod
    async def generate_similar(self, pattern: Dict[str, Any], count: int) -> List[Any]:
        """Generate similar data based on pattern"""
        pass

class NameGenerator:
    """Generate realistic names for synthetic profiles"""
    
    def __init__(self):
        self.first_names = [
            "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
            "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
            "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
            "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"
        ]
    
    def generate_name(self) -> Tuple[str, str]:
        """Generate random first and last name"""
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        return first_name, last_name
    
    def generate_email(self, first_name: str, last_name: str) -> str:
        """Generate realistic email address"""
        domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com"]
        patterns = [
            f"{first_name.lower()}.{last_name.lower()}",
            f"{first_name.lower()}{last_name.lower()}",
            f"{first_name[0].lower()}{last_name.lower()}",
            f"{first_name.lower()}_{last_name.lower()}"
        ]
        
        username = random.choice(patterns)
        domain = random.choice(domains)
        return f"{username}@{domain}"

class TextPatternGenerator:
    """Generate realistic text patterns"""
    
    def __init__(self):
        self.common_words = [
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
            "it", "for", "not", "on", "with", "he", "as", "you", "do", "at"
        ]
        
        self.sentence_templates = [
            "The {noun} {verb} {object} in the {location}.",
            "{Subject} {verb} {object} with {tool}.",
            "This {noun} is {adjective} and {adjective2}.",
            "We need to {verb} the {noun} for {purpose}."
        ]
    
    def generate_sentence(self) -> str:
        """Generate realistic sentence"""
        template = random.choice(self.sentence_templates)
        
        replacements = {
            "noun": random.choice(["system", "process", "data", "file", "record"]),
            "verb": random.choice(["process", "analyze", "update", "modify", "create"]),
            "object": random.choice(["information", "data", "records", "files", "content"]),
            "location": random.choice(["database", "server", "system", "network", "cloud"]),
            "subject": random.choice(["We", "They", "The team", "Users", "The system"]),
            "tool": random.choice(["automation", "scripts", "algorithms", "procedures"]),
            "adjective": random.choice(["important", "critical", "secure", "reliable"]),
            "adjective2": random.choice(["efficient", "scalable", "robust", "flexible"]),
            "purpose": random.choice(["security", "compliance", "performance", "reliability"])
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(f"{{{key}}}", value)
        
        return result

class DecoyDataGenerator:
    """Main generator for various types of decoy data"""
    
    def __init__(self):
        self.name_generator = NameGenerator()
        self.text_generator = TextPatternGenerator()
        self.active_decoys: Dict[str, DecoyMetadata] = {}
        self.detection_events: List[DecoyDetection] = []
        self.canary_tokens: Dict[str, CanaryToken] = {}
    
    async def generate_synthetic_users(
        self,
        count: int,
        realistic_level: RealisticLevel = RealisticLevel.HIGH
    ) -> List[SyntheticProfile]:
        """Generate synthetic user profiles"""
        profiles = []
        
        for i in range(count):
            first_name, last_name = self.name_generator.generate_name()
            email = self.name_generator.generate_email(first_name, last_name)
            
            # Generate realistic attributes based on level
            if realistic_level == RealisticLevel.PERFECT:
                age = random.randint(22, 65)
                department = random.choice(["Engineering", "Marketing", "Sales", "HR", "Finance"])
                role = random.choice(["Manager", "Senior", "Lead", "Junior", "Director"])
                
                behavioral_patterns = {
                    "login_frequency": random.uniform(0.8, 1.2),  # Logins per day
                    "active_hours": random.choice(["morning", "afternoon", "evening"]),
                    "preferred_features": random.sample(["feature_a", "feature_b", "feature_c", "feature_d"], k=2),
                    "session_duration": random.uniform(30, 180)  # Minutes
                }
            else:
                age = random.randint(20, 70)
                department = random.choice(["Dept_A", "Dept_B", "Dept_C"])
                role = random.choice(["Role_1", "Role_2", "Role_3"])
                behavioral_patterns = {"basic": True}
            
            profile = SyntheticProfile(
                profile_id=f"synthetic_{secrets.token_hex(8)}",
                name=f"{first_name} {last_name}",
                email=email,
                attributes={
                    "age": age,
                    "department": department,
                    "role": role,
                    "join_date": (datetime.now() - timedelta(days=random.randint(30, 1095))).isoformat(),
                    "employee_id": f"EMP{random.randint(10000, 99999)}"
                },
                behavioral_patterns=behavioral_patterns,
                creation_metadata={
                    "generated_at": datetime.now().isoformat(),
                    "realistic_level": realistic_level.value,
                    "generator_version": "1.0"
                }
            )
            
            profiles.append(profile)
            
            # Track as decoy
            decoy_metadata = DecoyMetadata(
                decoy_id=profile.profile_id,
                decoy_type=DecoyType.SYNTHETIC_USERS,
                creation_time=datetime.now(),
                last_accessed=None,
                access_count=0,
                detection_methods=[DetectionMethod.ACCESS_PATTERN, DetectionMethod.BEHAVIORAL_SIGNATURE],
                realistic_level=realistic_level
            )
            self.active_decoys[profile.profile_id] = decoy_metadata
        
        return profiles
    
    async def generate_honeypot_records(
        self,
        source_schema: Dict[str, Any],
        count: int,
        realistic_level: RealisticLevel = RealisticLevel.HIGH
    ) -> List[Dict[str, Any]]:
        """Generate honeypot records that mimic real data"""
        records = []
        
        for i in range(count):
            record = {}
            
            for field_name, field_config in source_schema.items():
                field_type = field_config.get("type", "string")
                
                if field_type == "string":
                    if "name" in field_name.lower():
                        first_name, last_name = self.name_generator.generate_name()
                        record[field_name] = f"{first_name} {last_name}"
                    elif "email" in field_name.lower():
                        first_name, last_name = self.name_generator.generate_name()
                        record[field_name] = self.name_generator.generate_email(first_name, last_name)
                    else:
                        record[field_name] = self._generate_realistic_string(field_name, field_config)
                
                elif field_type == "integer":
                    min_val = field_config.get("min", 1)
                    max_val = field_config.get("max", 1000)
                    record[field_name] = random.randint(min_val, max_val)
                
                elif field_type == "float":
                    min_val = field_config.get("min", 0.0)
                    max_val = field_config.get("max", 100.0)
                    record[field_name] = round(random.uniform(min_val, max_val), 2)
                
                elif field_type == "date":
                    start_date = datetime.now() - timedelta(days=365)
                    end_date = datetime.now()
                    random_date = start_date + timedelta(
                        days=random.randint(0, (end_date - start_date).days)
                    )
                    record[field_name] = random_date.isoformat()
                
                elif field_type == "boolean":
                    record[field_name] = random.choice([True, False])
            
            # Add canary token
            canary_token = await self.create_canary_token(f"honeypot_record_{i}")
            record["_tracking_id"] = canary_token.token_value
            
            records.append(record)
            
            # Track as decoy
            decoy_id = f"honeypot_{secrets.token_hex(8)}"
            decoy_metadata = DecoyMetadata(
                decoy_id=decoy_id,
                decoy_type=DecoyType.HONEYPOT_RECORDS,
                creation_time=datetime.now(),
                last_accessed=None,
                access_count=0,
                detection_methods=[DetectionMethod.ACCESS_PATTERN, DetectionMethod.CONTENT_FINGERPRINT],
                realistic_level=realistic_level
            )
            self.active_decoys[decoy_id] = decoy_metadata
        
        return records
    
    def _generate_realistic_string(self, field_name: str, field_config: Dict[str, Any]) -> str:
        """Generate realistic string based on field context"""
        if "description" in field_name.lower():
            return self.text_generator.generate_sentence()
        elif "id" in field_name.lower():
            return f"ID_{random.randint(100000, 999999)}"
        elif "code" in field_name.lower():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        elif "phone" in field_name.lower():
            return f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"
        else:
            length = field_config.get("length", 20)
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    async def create_canary_token(self, context: str) -> CanaryToken:
        """Create a unique canary token for tracking"""
        token_value = f"canary_{hashlib.sha256(f'{context}{secrets.token_hex(16)}'.encode()).hexdigest()[:16]}"
        
        token = CanaryToken(
            token_id=f"token_{secrets.token_hex(8)}",
            token_value=token_value,
            embedded_location=context,
            callback_url=f"https://canary-detector.internal/callback/{token_value}",
            metadata={"context": context, "generated_at": datetime.now().isoformat()},
            created_at=datetime.now()
        )
        
        self.canary_tokens[token.token_id] = token
        return token
    
    async def generate_fake_documents(
        self,
        document_types: List[str],
        count: int,
        realistic_level: RealisticLevel = RealisticLevel.HIGH
    ) -> List[Dict[str, Any]]:
        """Generate fake documents with embedded tracking"""
        documents = []
        
        for doc_type in document_types:
            for i in range(count):
                if doc_type == "contract":
                    document = await self._generate_fake_contract()
                elif doc_type == "report":
                    document = await self._generate_fake_report()
                elif doc_type == "policy":
                    document = await self._generate_fake_policy()
                else:
                    document = await self._generate_generic_document(doc_type)
                
                # Add tracking metadata
                canary_token = await self.create_canary_token(f"{doc_type}_document_{i}")
                document["_canary_token"] = canary_token.token_value
                document["_document_id"] = f"doc_{secrets.token_hex(12)}"
                
                documents.append(document)
                
                # Track as decoy
                decoy_id = document["_document_id"]
                decoy_metadata = DecoyMetadata(
                    decoy_id=decoy_id,
                    decoy_type=DecoyType.FAKE_DOCUMENTS,
                    creation_time=datetime.now(),
                    last_accessed=None,
                    access_count=0,
                    detection_methods=[DetectionMethod.CONTENT_FINGERPRINT, DetectionMethod.ACCESS_PATTERN],
                    realistic_level=realistic_level
                )
                self.active_decoys[decoy_id] = decoy_metadata
        
        return documents
    
    async def _generate_fake_contract(self) -> Dict[str, Any]:
        """Generate fake contract document"""
        first_name, last_name = self.name_generator.generate_name()
        company_name = random.choice(["TechCorp", "DataSystems", "CloudServices", "InfoTech"])
        
        return {
            "type": "contract",
            "title": f"Service Agreement - {company_name}",
            "parties": [
                {"name": f"{first_name} {last_name}", "role": "Client"},
                {"name": company_name, "role": "Provider"}
            ],
            "amount": f"${random.randint(10000, 100000):,}",
            "duration": f"{random.randint(6, 36)} months",
            "content": self._generate_contract_content(),
            "created_date": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            "status": random.choice(["draft", "pending", "active"])
        }
    
    def _generate_contract_content(self) -> str:
        """Generate realistic contract content"""
        clauses = [
            "This agreement governs the provision of services between the parties.",
            "The provider shall deliver services according to the specifications.",
            "Payment terms are net 30 days from invoice date.",
            "Either party may terminate with 30 days written notice.",
            "Confidentiality provisions apply to all shared information."
        ]
        return " ".join(clauses)
    
    async def _generate_fake_report(self) -> Dict[str, Any]:
        """Generate fake report document"""
        return {
            "type": "report",
            "title": f"Quarterly Analysis Report Q{random.randint(1,4)}",
            "author": f"{self.name_generator.generate_name()[0]} {self.name_generator.generate_name()[1]}",
            "department": random.choice(["Finance", "Operations", "Marketing", "Engineering"]),
            "metrics": {
                "revenue": f"${random.randint(100000, 1000000):,}",
                "growth": f"{random.uniform(-10, 50):.1f}%",
                "efficiency": f"{random.uniform(60, 95):.1f}%"
            },
            "summary": self.text_generator.generate_sentence(),
            "created_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            "classification": random.choice(["public", "internal", "confidential"])
        }
    
    async def _generate_fake_policy(self) -> Dict[str, Any]:
        """Generate fake policy document"""
        return {
            "type": "policy",
            "title": f"Data {random.choice(['Security', 'Privacy', 'Retention', 'Access'])} Policy",
            "version": f"{random.randint(1,5)}.{random.randint(0,9)}",
            "effective_date": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
            "content": self._generate_policy_content(),
            "approval_status": "approved",
            "next_review": (datetime.now() + timedelta(days=365)).isoformat()
        }
    
    def _generate_policy_content(self) -> str:
        """Generate realistic policy content"""
        sections = [
            "1. Purpose and Scope",
            "2. Responsibilities and Accountability", 
            "3. Implementation Guidelines",
            "4. Compliance and Monitoring",
            "5. Review and Updates"
        ]
        return "\n".join(sections)
    
    async def _generate_generic_document(self, doc_type: str) -> Dict[str, Any]:
        """Generate generic document"""
        return {
            "type": doc_type,
            "title": f"{doc_type.title()} Document",
            "content": self.text_generator.generate_sentence(),
            "created_date": datetime.now().isoformat(),
            "metadata": {"generated": True, "type": doc_type}
        }
    
    async def detect_decoy_access(
        self,
        accessed_data: Any,
        accessor_info: Dict[str, Any]
    ) -> Optional[DecoyDetection]:
        """Detect when decoy data is accessed"""
        detection_methods = []
        confidence_score = 0.0
        
        # Check for canary token access
        if isinstance(accessed_data, dict):
            for key, value in accessed_data.items():
                if isinstance(value, str) and value.startswith("canary_"):
                    # Canary token detected
                    detection_methods.append(DetectionMethod.CONTENT_FINGERPRINT)
                    confidence_score += 0.8
                    
                    detection = DecoyDetection(
                        detection_id=f"detect_{secrets.token_hex(8)}",
                        decoy_id=value,
                        detected_at=datetime.now(),
                        accessor_info=accessor_info,
                        access_pattern="canary_token_access",
                        detection_method=DetectionMethod.CONTENT_FINGERPRINT,
                        confidence_score=confidence_score,
                        additional_context={"token_value": value, "access_type": "direct"}
                    )
                    
                    self.detection_events.append(detection)
                    return detection
        
        # Check access patterns
        access_time = datetime.now()
        unusual_patterns = self._analyze_access_patterns(accessor_info, access_time)
        
        if unusual_patterns:
            detection_methods.append(DetectionMethod.ACCESS_PATTERN)
            confidence_score += 0.6
        
        # Statistical anomaly detection
        if self._detect_statistical_anomaly(accessed_data):
            detection_methods.append(DetectionMethod.STATISTICAL_ANALYSIS)
            confidence_score += 0.4
        
        if confidence_score > 0.5:  # Threshold for detection
            detection = DecoyDetection(
                detection_id=f"detect_{secrets.token_hex(8)}",
                decoy_id="unknown",
                detected_at=access_time,
                accessor_info=accessor_info,
                access_pattern="suspicious_access",
                detection_method=detection_methods[0] if detection_methods else DetectionMethod.BEHAVIORAL_SIGNATURE,
                confidence_score=confidence_score,
                additional_context={"methods": [m.value for m in detection_methods]}
            )
            
            self.detection_events.append(detection)
            return detection
        
        return None
    
    def _analyze_access_patterns(self, accessor_info: Dict[str, Any], access_time: datetime) -> bool:
        """Analyze if access pattern is unusual"""
        # Check for off-hours access
        if access_time.hour < 6 or access_time.hour > 22:
            return True
        
        # Check for rapid sequential access
        user_id = accessor_info.get("user_id")
        if user_id:
            recent_accesses = [
                event for event in self.detection_events 
                if event.accessor_info.get("user_id") == user_id
                and (access_time - event.detected_at).seconds < 60
            ]
            if len(recent_accesses) > 10:  # More than 10 accesses per minute
                return True
        
        return False
    
    def _detect_statistical_anomaly(self, accessed_data: Any) -> bool:
        """Detect statistical anomalies in access patterns"""
        # Simple anomaly detection based on data characteristics
        if isinstance(accessed_data, dict):
            # Check for unusually structured data
            if len(accessed_data) > 50:  # Too many fields
                return True
            
            # Check for obviously fake patterns
            for value in accessed_data.values():
                if isinstance(value, str) and ("synthetic_" in value or "fake_" in value):
                    return True
        
        return False
    
    async def get_decoy_statistics(self) -> Dict[str, Any]:
        """Get statistics about decoy data and detections"""
        active_decoys = len([d for d in self.active_decoys.values() if d.decoy_id])
        total_detections = len(self.detection_events)
        
        detection_by_method = {}
        for detection in self.detection_events:
            method = detection.detection_method.value
            detection_by_method[method] = detection_by_method.get(method, 0) + 1
        
        decoy_by_type = {}
        for decoy in self.active_decoys.values():
            decoy_type = decoy.decoy_type.value
            decoy_by_type[decoy_type] = decoy_by_type.get(decoy_type, 0) + 1
        
        return {
            "active_decoys": active_decoys,
            "total_detections": total_detections,
            "detection_rate": total_detections / active_decoys if active_decoys > 0 else 0,
            "detections_by_method": detection_by_method,
            "decoys_by_type": decoy_by_type,
            "canary_tokens": len(self.canary_tokens),
            "last_detection": self.detection_events[-1].detected_at.isoformat() if self.detection_events else None
        }

def create_decoy_data_generator() -> DecoyDataGenerator:
    """Factory function to create decoy data generator"""
    return DecoyDataGenerator()

# Example usage
async def example_usage():
    """Example of using decoy data generation"""
    
    # Create decoy generator
    decoy_generator = create_decoy_data_generator()
    
    # Generate synthetic users
    synthetic_users = await decoy_generator.generate_synthetic_users(
        count=5,
        realistic_level=RealisticLevel.HIGH
    )
    
    print(f"Generated {len(synthetic_users)} synthetic users:")
    for user in synthetic_users[:2]:  # Show first 2
        print(f"  {user.name} ({user.email})")
        print(f"  Department: {user.attributes['department']}")
        print(f"  Role: {user.attributes['role']}")
        print()
    
    # Generate honeypot records
    schema = {
        "user_name": {"type": "string"},
        "email": {"type": "string"},
        "age": {"type": "integer", "min": 18, "max": 65},
        "salary": {"type": "float", "min": 30000.0, "max": 150000.0},
        "join_date": {"type": "date"},
        "is_active": {"type": "boolean"}
    }
    
    honeypot_records = await decoy_generator.generate_honeypot_records(
        source_schema=schema,
        count=3,
        realistic_level=RealisticLevel.HIGH
    )
    
    print(f"Generated {len(honeypot_records)} honeypot records:")
    for record in honeypot_records[:1]:  # Show first record
        print(f"  User: {record['user_name']}")
        print(f"  Email: {record['email']}")
        print(f"  Tracking ID: {record['_tracking_id']}")
        print()
    
    # Generate fake documents
    fake_documents = await decoy_generator.generate_fake_documents(
        document_types=["contract", "report"],
        count=2,
        realistic_level=RealisticLevel.HIGH
    )
    
    print(f"Generated {len(fake_documents)} fake documents:")
    for doc in fake_documents[:1]:  # Show first document
        print(f"  Type: {doc['type']}")
        print(f"  Title: {doc['title']}")
        print(f"  Document ID: {doc['_document_id']}")
        print()
    
    # Simulate decoy access detection
    print("Simulating decoy access...")
    accessed_data = honeypot_records[0]
    accessor_info = {
        "user_id": "attacker_123",
        "ip_address": "192.168.1.100",
        "user_agent": "suspicious_bot",
        "session_id": "session_xyz"
    }
    
    detection = await decoy_generator.detect_decoy_access(accessed_data, accessor_info)
    if detection:
        print(f"ALERT: Decoy access detected!")
        print(f"  Detection ID: {detection.detection_id}")
        print(f"  Method: {detection.detection_method.value}")
        print(f"  Confidence: {detection.confidence_score:.2f}")
        print(f"  Accessor: {detection.accessor_info['user_id']}")
        print()
    
    # Get statistics
    stats = await decoy_generator.get_decoy_statistics()
    print("Decoy Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(example_usage())