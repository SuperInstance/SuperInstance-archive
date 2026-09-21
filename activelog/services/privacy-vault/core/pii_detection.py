import re
import hashlib
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from ..models.privacy_models import PIIType, PIIFinding, PIIDetectionResult, PIIMaskingResult, MaskingStrategy
import logging

logger = logging.getLogger(__name__)

class PIIDetectionEngine:
    def __init__(self):
        self.detection_patterns = {}
        self.custom_patterns = {}
        self.masking_functions = {}
        self.confidence_thresholds = {
            "strict": 0.9,
            "standard": 0.75,
            "permissive": 0.6
        }
        
        # Initialize detection patterns
        self._initialize_detection_patterns()
        self._initialize_masking_functions()
    
    def _initialize_detection_patterns(self):
        """Initialize PII detection patterns"""
        self.detection_patterns = {
            PIIType.EMAIL: {
                "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "confidence": 0.95,
                "validator": self._validate_email
            },
            PIIType.PHONE: {
                "pattern": r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                "confidence": 0.85,
                "validator": self._validate_phone
            },
            PIIType.SSN: {
                "pattern": r'\b\d{3}-?\d{2}-?\d{4}\b',
                "confidence": 0.9,
                "validator": self._validate_ssn
            },
            PIIType.CREDIT_CARD: {
                "pattern": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                "confidence": 0.85,
                "validator": self._validate_credit_card
            },
            PIIType.NAME: {
                "pattern": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
                "confidence": 0.7,
                "validator": self._validate_name
            },
            PIIType.ADDRESS: {
                "pattern": r'\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)',
                "confidence": 0.8,
                "validator": self._validate_address
            },
            PIIType.IP_ADDRESS: {
                "pattern": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                "confidence": 0.95,
                "validator": self._validate_ip_address
            },
            PIIType.DATE_OF_BIRTH: {
                "pattern": r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(?:\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
                "confidence": 0.8,
                "validator": self._validate_date_of_birth
            }
        }
    
    def _initialize_masking_functions(self):
        """Initialize masking functions"""
        self.masking_functions = {
            MaskingStrategy.FULL_MASK: self._full_mask,
            MaskingStrategy.PARTIAL_MASK: self._partial_mask,
            MaskingStrategy.TOKENIZATION: self._tokenize,
            MaskingStrategy.ENCRYPTION: self._encrypt,
            MaskingStrategy.REDACTION: self._redact,
            MaskingStrategy.PSEUDONYMIZATION: self._pseudonymize
        }
    
    async def detect_pii(
        self,
        data: Dict[str, Any],
        detection_level: str = "standard",
        custom_patterns: Optional[List[Dict[str, str]]] = None
    ) -> PIIDetectionResult:
        """Detect PII in provided data"""
        try:
            pii_findings = []
            total_fields_scanned = 0
            confidence_threshold = self.confidence_thresholds.get(detection_level, 0.75)
            
            # Add custom patterns if provided
            if custom_patterns:
                for pattern in custom_patterns:
                    self.custom_patterns[pattern["name"]] = {
                        "pattern": pattern["regex"],
                        "confidence": pattern.get("confidence", 0.8),
                        "validator": lambda x: True  # Default validator
                    }
            
            # Recursively scan data structure
            findings = await self._scan_data_recursive(data, "", confidence_threshold)
            pii_findings.extend(findings)
            total_fields_scanned = await self._count_fields_recursive(data)
            
            # Assess overall risk
            risk_assessment = await self._assess_risk(pii_findings)
            
            return PIIDetectionResult(
                pii_findings=pii_findings,
                scan_timestamp=datetime.utcnow(),
                total_fields_scanned=total_fields_scanned,
                pii_fields_detected=len(pii_findings),
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            raise
    
    async def _scan_data_recursive(
        self, data: Any, path: str, confidence_threshold: float
    ) -> List[PIIFinding]:
        """Recursively scan data structure for PII"""
        findings = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                findings.extend(await self._scan_data_recursive(value, current_path, confidence_threshold))
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                findings.extend(await self._scan_data_recursive(item, current_path, confidence_threshold))
        
        elif isinstance(data, str):
            # Scan string for PII patterns
            string_findings = await self._scan_string_for_pii(data, path, confidence_threshold)
            findings.extend(string_findings)
        
        return findings
    
    async def _scan_string_for_pii(
        self, text: str, field_path: str, confidence_threshold: float
    ) -> List[PIIFinding]:
        """Scan a string for PII patterns"""
        findings = []
        
        # Check all PII patterns
        all_patterns = {**self.detection_patterns, **self.custom_patterns}
        
        for pii_type_str, pattern_info in all_patterns.items():
            pattern = pattern_info["pattern"]
            base_confidence = pattern_info["confidence"]
            validator = pattern_info.get("validator", lambda x: True)
            
            # Find all matches
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                detected_value = match.group()
                
                # Validate the match
                if validator(detected_value):
                    # Adjust confidence based on context
                    confidence = await self._adjust_confidence(
                        detected_value, field_path, base_confidence, pii_type_str
                    )
                    
                    if confidence >= confidence_threshold:
                        # Convert string to PIIType if it's a custom pattern
                        if isinstance(pii_type_str, str) and pii_type_str not in [e.value for e in PIIType]:
                            pii_type = PIIType.CUSTOM
                        else:
                            pii_type = PIIType(pii_type_str) if isinstance(pii_type_str, str) else pii_type_str
                        
                        finding = PIIFinding(
                            field_path=field_path,
                            pii_type=pii_type,
                            confidence_score=confidence,
                            detected_value=detected_value[:50] + "..." if len(detected_value) > 50 else detected_value,
                            location={"start": match.start(), "end": match.end()},
                            suggestion=await self._generate_masking_suggestion(pii_type, detected_value)
                        )
                        findings.append(finding)
        
        return findings
    
    async def _adjust_confidence(
        self, value: str, field_path: str, base_confidence: float, pii_type: str
    ) -> float:
        """Adjust confidence based on context"""
        confidence = base_confidence
        
        # Field name context boost
        field_name_lower = field_path.lower()
        context_boosts = {
            PIIType.EMAIL: ["email", "mail", "contact"],
            PIIType.PHONE: ["phone", "tel", "mobile", "contact"],
            PIIType.NAME: ["name", "first", "last", "full"],
            PIIType.ADDRESS: ["address", "street", "location"],
            PIIType.SSN: ["ssn", "social", "security"],
            PIIType.CREDIT_CARD: ["card", "credit", "payment"]
        }
        
        pii_type_enum = PIIType(pii_type) if isinstance(pii_type, str) else pii_type
        if pii_type_enum in context_boosts:
            for keyword in context_boosts[pii_type_enum]:
                if keyword in field_name_lower:
                    confidence = min(1.0, confidence + 0.1)
                    break
        
        # Length and format validation
        confidence = await self._validate_format_confidence(value, pii_type_enum, confidence)
        
        return confidence
    
    async def _validate_format_confidence(self, value: str, pii_type: PIIType, confidence: float) -> float:
        """Validate format and adjust confidence"""
        if pii_type == PIIType.EMAIL:
            # Check for common email providers
            common_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
            if any(domain in value.lower() for domain in common_domains):
                confidence = min(1.0, confidence + 0.05)
        
        elif pii_type == PIIType.PHONE:
            # Check for proper phone number length
            digits_only = re.sub(r'\D', '', value)
            if len(digits_only) in [10, 11]:  # US phone numbers
                confidence = min(1.0, confidence + 0.05)
        
        elif pii_type == PIIType.SSN:
            # Check SSN format validity
            if re.match(r'^\d{3}-\d{2}-\d{4}$', value) or re.match(r'^\d{9}$', value):
                confidence = min(1.0, confidence + 0.1)
        
        return confidence
    
    async def _generate_masking_suggestion(self, pii_type: PIIType, value: str) -> str:
        """Generate masking suggestion for detected PII"""
        if pii_type == PIIType.EMAIL:
            return "Consider masking email domain or using tokenization"
        elif pii_type == PIIType.PHONE:
            return "Mask all but last 4 digits"
        elif pii_type == PIIType.SSN:
            return "Show only last 4 digits (XXX-XX-1234)"
        elif pii_type == PIIType.CREDIT_CARD:
            return "Show only last 4 digits (**** **** **** 1234)"
        elif pii_type == PIIType.NAME:
            return "Use initials or pseudonyms"
        else:
            return "Apply appropriate masking for this PII type"
    
    async def mask_pii(
        self,
        data: Dict[str, Any],
        masking_strategy: MaskingStrategy,
        preserve_format: bool = True,
        custom_masks: Optional[Dict[str, str]] = None
    ) -> PIIMaskingResult:
        """Mask PII in data using specified strategy"""
        try:
            # First detect PII
            detection_result = await self.detect_pii(data)
            
            # Apply masking
            masked_data = await self._apply_masking(
                data, detection_result.pii_findings, masking_strategy, 
                preserve_format, custom_masks
            )
            
            # Generate masking metadata
            masking_metadata = {
                "strategy": masking_strategy.value,
                "preserve_format": preserve_format,
                "pii_types_masked": list(set([finding.pii_type.value for finding in detection_result.pii_findings])),
                "total_fields_masked": len(detection_result.pii_findings),
                "custom_masks_applied": bool(custom_masks)
            }
            
            fields_masked = [finding.field_path for finding in detection_result.pii_findings]
            
            return PIIMaskingResult(
                masked_data=masked_data,
                masking_metadata=masking_metadata,
                fields_masked=fields_masked,
                masking_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"PII masking failed: {e}")
            raise
    
    async def _apply_masking(
        self,
        data: Dict[str, Any],
        findings: List[PIIFinding],
        strategy: MaskingStrategy,
        preserve_format: bool,
        custom_masks: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Apply masking to data based on findings"""
        masked_data = self._deep_copy(data)
        
        for finding in findings:
            # Get masking function
            mask_function = self.masking_functions.get(strategy, self._full_mask)
            
            # Check for custom mask
            if custom_masks and finding.pii_type.value in custom_masks:
                masked_value = custom_masks[finding.pii_type.value]
            else:
                # Apply standard masking
                original_value = self._get_value_by_path(masked_data, finding.field_path)
                masked_value = await mask_function(
                    original_value, finding.pii_type, preserve_format
                )
            
            # Set masked value
            self._set_value_by_path(masked_data, finding.field_path, masked_value)
        
        return masked_data
    
    # Masking Functions
    async def _full_mask(self, value: str, pii_type: PIIType, preserve_format: bool) -> str:
        """Fully mask the value"""
        if preserve_format:
            if pii_type == PIIType.EMAIL:
                local, domain = value.split('@')
                return f"{'*' * len(local)}@{'*' * len(domain.split('.')[0])}.{domain.split('.')[-1]}"
            elif pii_type == PIIType.PHONE:
                return re.sub(r'\d', '*', value)
            elif pii_type == PIIType.CREDIT_CARD:
                return re.sub(r'\d', '*', value)
            else:
                return '*' * len(value)
        else:
            return '[MASKED]'
    
    async def _partial_mask(self, value: str, pii_type: PIIType, preserve_format: bool) -> str:
        """Partially mask the value"""
        if pii_type == PIIType.EMAIL:
            local, domain = value.split('@')
            masked_local = local[:2] + '*' * (len(local) - 2)
            return f"{masked_local}@{domain}"
        elif pii_type == PIIType.PHONE:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                masked = '*' * (len(digits) - 4) + digits[-4:]
                return re.sub(r'\d+', masked, value, count=1)
        elif pii_type == PIIType.CREDIT_CARD:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                masked = '*' * (len(digits) - 4) + digits[-4:]
                return re.sub(r'\d+', masked, value, count=1)
        elif pii_type == PIIType.SSN:
            if '-' in value:
                return f"***-**-{value[-4:]}"
            else:
                return f"*****{value[-4:]}"
        else:
            return value[:2] + '*' * (len(value) - 4) + value[-2:] if len(value) > 4 else '*' * len(value)
        
        return value
    
    async def _tokenize(self, value: str, pii_type: PIIType, preserve_format: bool) -> str:
        """Create a token for the value"""
        # Create a deterministic token
        token_hash = hashlib.sha256(value.encode()).hexdigest()[:12]
        return f"TOKEN_{pii_type.value.upper()}_{token_hash}"
    
    async def _encrypt(self, value: str, pii_type: PIIType, preserve_format: bool) -> str:
        """Encrypt the value (simplified)"""
        encrypted_bytes = base64.b64encode(value.encode())
        return f"ENC_{encrypted_bytes.decode()[:16]}..."
    
    async def _redact(self, value: str, pii_type: PIIType, preserve_format: bool) -> str:
        """Redact the value completely"""
        return f"[REDACTED_{pii_type.value.upper()}]"
    
    async def _pseudonymize(self, value: str, pii_type: PIIType, preserve_format: bool) -> str:
        """Create a pseudonym for the value"""
        # Create a deterministic pseudonym
        pseudo_hash = hashlib.sha256(value.encode()).hexdigest()
        
        if pii_type == PIIType.NAME:
            # Generate fake name from hash
            first_names = ["Alex", "Jordan", "Casey", "Riley", "Morgan", "Taylor", "Blake", "Quinn"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
            first_idx = int(pseudo_hash[:2], 16) % len(first_names)
            last_idx = int(pseudo_hash[2:4], 16) % len(last_names)
            return f"{first_names[first_idx]} {last_names[last_idx]}"
        elif pii_type == PIIType.EMAIL:
            return f"user{pseudo_hash[:8]}@example.com"
        else:
            return f"PSEUDO_{pseudo_hash[:12]}"
    
    # Validation Functions
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        return '@' in email and '.' in email.split('@')[1]
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number"""
        digits = re.sub(r'\D', '', phone)
        return len(digits) >= 10
    
    def _validate_ssn(self, ssn: str) -> bool:
        """Validate SSN format"""
        digits = re.sub(r'\D', '', ssn)
        return len(digits) == 9
    
    def _validate_credit_card(self, cc: str) -> bool:
        """Validate credit card using Luhn algorithm"""
        digits = re.sub(r'\D', '', cc)
        if len(digits) < 13 or len(digits) > 19:
            return False
        
        # Luhn algorithm
        def luhn_check(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10 == 0
        
        return luhn_check(digits)
    
    def _validate_name(self, name: str) -> bool:
        """Validate name (basic check)"""
        parts = name.split()
        return len(parts) >= 2 and all(part.isalpha() for part in parts)
    
    def _validate_address(self, address: str) -> bool:
        """Validate address format"""
        return any(word in address.lower() for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd'])
    
    def _validate_ip_address(self, ip: str) -> bool:
        """Validate IP address"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    def _validate_date_of_birth(self, date_str: str) -> bool:
        """Validate date of birth"""
        # Basic date format validation
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
        ]
        return any(re.match(pattern, date_str) for pattern in date_patterns)
    
    # Utility Functions
    async def _count_fields_recursive(self, data: Any) -> int:
        """Count total fields in data structure"""
        if isinstance(data, dict):
            return sum(await self._count_fields_recursive(value) for value in data.values())
        elif isinstance(data, list):
            return sum(await self._count_fields_recursive(item) for item in data)
        else:
            return 1
    
    async def _assess_risk(self, findings: List[PIIFinding]) -> str:
        """Assess overall privacy risk"""
        if not findings:
            return "low"
        
        # Count high-risk PII types
        high_risk_types = {PIIType.SSN, PIIType.CREDIT_CARD, PIIType.BIOMETRIC}
        medium_risk_types = {PIIType.EMAIL, PIIType.PHONE, PIIType.ADDRESS, PIIType.DATE_OF_BIRTH}
        
        high_risk_count = sum(1 for f in findings if f.pii_type in high_risk_types)
        medium_risk_count = sum(1 for f in findings if f.pii_type in medium_risk_types)
        
        if high_risk_count > 0:
            return "high"
        elif medium_risk_count > 3:
            return "medium"
        elif len(findings) > 5:
            return "medium"
        else:
            return "low"
    
    def _deep_copy(self, obj):
        """Create a deep copy of the object"""
        if isinstance(obj, dict):
            return {key: self._deep_copy(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    
    def _get_value_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from data using dot notation path"""
        parts = path.split('.')
        current = data
        
        for part in parts:
            if '[' in part and ']' in part:
                # Handle array access
                key, index_part = part.split('[')
                index = int(index_part.rstrip(']'))
                current = current[key][index]
            else:
                current = current[part]
        
        return current
    
    def _set_value_by_path(self, data: Dict[str, Any], path: str, value: Any):
        """Set value in data using dot notation path"""
        parts = path.split('.')
        current = data
        
        for part in parts[:-1]:
            if '[' in part and ']' in part:
                # Handle array access
                key, index_part = part.split('[')
                index = int(index_part.rstrip(']'))
                current = current[key][index]
            else:
                current = current[part]
        
        # Set the final value
        final_part = parts[-1]
        if '[' in final_part and ']' in final_part:
            key, index_part = final_part.split('[')
            index = int(index_part.rstrip(']'))
            current[key][index] = value
        else:
            current[final_part] = value