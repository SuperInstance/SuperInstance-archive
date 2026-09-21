"""
Legal Document Redaction Tools
Comprehensive tools for identifying and redacting sensitive information in legal documents.
"""
import re
import datetime
import logging
import hashlib
import base64
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None


class RedactionCategory(Enum):
    """Categories of information that may require redaction"""
    PERSONAL_IDENTIFIERS = "personal_identifiers"
    FINANCIAL_INFO = "financial_info"
    MEDICAL_INFO = "medical_info"
    LEGAL_PRIVILEGED = "legal_privileged"
    TRADE_SECRETS = "trade_secrets"
    CLASSIFIED = "classified"
    ATTORNEY_CLIENT = "attorney_client"
    WORK_PRODUCT = "work_product"
    SETTLEMENT_TERMS = "settlement_terms"
    WITNESS_IDENTITY = "witness_identity"
    MINOR_INFORMATION = "minor_information"
    CUSTOM = "custom"


class RedactionMethod(Enum):
    """Methods of redaction"""
    BLACK_BOX = "black_box"
    WHITE_BOX = "white_box"
    REPLACEMENT_TEXT = "replacement_text"
    HASH_REDACTION = "hash_redaction"
    ENCRYPTED_REDACTION = "encrypted_redaction"
    REMOVAL = "removal"


class RedactionLevel(Enum):
    """Levels of redaction protection"""
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"
    TOP_SECRET = "top_secret"


@dataclass
class SensitiveMatch:
    """Information about detected sensitive content"""
    text: str
    category: RedactionCategory
    start_position: int
    end_position: int
    confidence: float
    context: str
    reason: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RedactionRule:
    """Rule for identifying and redacting sensitive content"""
    name: str
    category: RedactionCategory
    pattern: str
    replacement_text: str
    redaction_method: RedactionMethod
    confidence_threshold: float
    is_regex: bool = True
    case_sensitive: bool = False
    whole_word_only: bool = False
    context_required: Optional[str] = None
    exemptions: Optional[List[str]] = None


@dataclass
class RedactionResult:
    """Result of redaction operation"""
    original_text: str
    redacted_text: str
    redaction_map: Dict[int, SensitiveMatch]
    redaction_summary: Dict[str, Any]
    redacted_at: datetime.datetime
    redaction_key: Optional[str] = None  # For encrypted redactions
    metadata: Optional[Dict[str, Any]] = None


class SensitiveDataDetector:
    """Detects various types of sensitive information in documents"""
    
    def __init__(self):
        self.detection_patterns = self._initialize_patterns()
        self.context_patterns = self._initialize_context_patterns()
    
    def _initialize_patterns(self) -> Dict[RedactionCategory, List[Dict[str, Any]]]:
        """Initialize regex patterns for different types of sensitive data"""
        return {
            RedactionCategory.PERSONAL_IDENTIFIERS: [
                {
                    'name': 'Social Security Number',
                    'pattern': r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b',
                    'confidence': 0.9,
                    'context_required': None
                },
                {
                    'name': 'Driver License',
                    'pattern': r'(?i)(?:driver|license|dl)[\s#:]*([A-Z0-9]{8,12})',
                    'confidence': 0.8,
                    'context_required': r'(?i)driver|license|dl'
                },
                {
                    'name': 'Phone Number',
                    'pattern': r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
                    'confidence': 0.7,
                    'context_required': None
                },
                {
                    'name': 'Email Address',
                    'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'confidence': 0.9,
                    'context_required': None
                },
                {
                    'name': 'Date of Birth',
                    'pattern': r'(?i)(?:born|birth|dob)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})',
                    'confidence': 0.8,
                    'context_required': r'(?i)born|birth|dob'
                },
                {
                    'name': 'Address',
                    'pattern': r'\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln)[\s,]+[A-Za-z\s,]+\d{5}(?:-\d{4})?',
                    'confidence': 0.8,
                    'context_required': None
                }
            ],
            RedactionCategory.FINANCIAL_INFO: [
                {
                    'name': 'Credit Card Number',
                    'pattern': r'\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|\d{15,16})\b',
                    'confidence': 0.8,
                    'context_required': r'(?i)card|credit|visa|mastercard|amex'
                },
                {
                    'name': 'Bank Account Number',
                    'pattern': r'(?i)(?:account|acct)[\s#:]*(\d{8,17})',
                    'confidence': 0.8,
                    'context_required': r'(?i)account|bank|routing'
                },
                {
                    'name': 'Routing Number',
                    'pattern': r'(?i)routing[\s#:]*(\d{9})',
                    'confidence': 0.9,
                    'context_required': r'(?i)routing|aba'
                },
                {
                    'name': 'Tax ID / EIN',
                    'pattern': r'\b\d{2}-\d{7}\b',
                    'confidence': 0.8,
                    'context_required': r'(?i)tax|ein|employer'
                }
            ],
            RedactionCategory.MEDICAL_INFO: [
                {
                    'name': 'Medical Record Number',
                    'pattern': r'(?i)(?:medical|patient|mrn)[\s#:]*([A-Z0-9]{6,12})',
                    'confidence': 0.8,
                    'context_required': r'(?i)medical|patient|mrn'
                },
                {
                    'name': 'Insurance Policy Number',
                    'pattern': r'(?i)(?:policy|insurance)[\s#:]*([A-Z0-9]{6,15})',
                    'confidence': 0.7,
                    'context_required': r'(?i)policy|insurance'
                },
                {
                    'name': 'Prescription Information',
                    'pattern': r'(?i)(?:rx|prescription)[\s#:]*([A-Z0-9]{6,12})',
                    'confidence': 0.7,
                    'context_required': r'(?i)rx|prescription|medication'
                }
            ],
            RedactionCategory.LEGAL_PRIVILEGED: [
                {
                    'name': 'Attorney-Client Communication',
                    'pattern': r'(?i)(?:attorney-client|privileged|confidential)\s+(?:communication|correspondence|discussion)',
                    'confidence': 0.9,
                    'context_required': None
                },
                {
                    'name': 'Work Product',
                    'pattern': r'(?i)(?:work product|attorney work product|legal analysis)',
                    'confidence': 0.9,
                    'context_required': None
                }
            ],
            RedactionCategory.SETTLEMENT_TERMS: [
                {
                    'name': 'Settlement Amount',
                    'pattern': r'(?i)settlement[\s\w]*\$[\d,]+(?:\.\d{2})?',
                    'confidence': 0.9,
                    'context_required': r'(?i)settlement'
                },
                {
                    'name': 'Confidential Settlement Terms',
                    'pattern': r'(?i)confidential[\s\w]*settlement|settlement[\s\w]*confidential',
                    'confidence': 0.9,
                    'context_required': None
                }
            ],
            RedactionCategory.WITNESS_IDENTITY: [
                {
                    'name': 'Witness Name',
                    'pattern': r'(?i)witness[\s:]*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                    'confidence': 0.8,
                    'context_required': r'(?i)witness'
                }
            ],
            RedactionCategory.MINOR_INFORMATION: [
                {
                    'name': 'Minor Identification',
                    'pattern': r'(?i)(?:minor|child|juvenile)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    'confidence': 0.8,
                    'context_required': r'(?i)minor|child|juvenile'
                }
            ]
        }
    
    def _initialize_context_patterns(self) -> Dict[str, str]:
        """Initialize context patterns for better detection accuracy"""
        return {
            'financial_context': r'(?i)(?:bank|account|credit|debit|payment|financial|money|cash|check)',
            'medical_context': r'(?i)(?:medical|health|patient|doctor|hospital|treatment|diagnosis|medication)',
            'legal_context': r'(?i)(?:attorney|lawyer|legal|court|case|litigation|privilege|confidential)',
            'personal_context': r'(?i)(?:personal|private|individual|person|name|address|phone|email)'
        }
    
    def detect_sensitive_content(self, text: str) -> List[SensitiveMatch]:
        """Detect sensitive content in text"""
        matches = []
        
        for category, patterns in self.detection_patterns.items():
            for pattern_info in patterns:
                category_matches = self._find_pattern_matches(
                    text, pattern_info, category
                )
                matches.extend(category_matches)
        
        # Remove overlapping matches (keep highest confidence)
        return self._resolve_overlaps(matches)
    
    def _find_pattern_matches(self, text: str, pattern_info: Dict[str, Any], 
                            category: RedactionCategory) -> List[SensitiveMatch]:
        """Find matches for a specific pattern"""
        matches = []
        pattern = pattern_info['pattern']
        confidence = pattern_info['confidence']
        context_required = pattern_info.get('context_required')
        
        # Compile regex with appropriate flags
        flags = re.IGNORECASE if not pattern_info.get('case_sensitive', False) else 0
        
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            logging.warning(f"Invalid regex pattern '{pattern}': {e}")
            return matches
        
        for match in regex.finditer(text):
            start_pos = match.start()
            end_pos = match.end()
            matched_text = match.group(0)
            
            # Check context requirement
            if context_required:
                context_window = 100
                context_start = max(0, start_pos - context_window)
                context_end = min(len(text), end_pos + context_window)
                context = text[context_start:context_end]
                
                if not re.search(context_required, context, re.IGNORECASE):
                    continue
            else:
                context = self._extract_context(text, start_pos, end_pos)
            
            # Additional validation based on category
            validated_confidence = self._validate_match(
                matched_text, category, context, confidence
            )
            
            if validated_confidence >= 0.5:  # Minimum confidence threshold
                sensitive_match = SensitiveMatch(
                    text=matched_text,
                    category=category,
                    start_position=start_pos,
                    end_position=end_pos,
                    confidence=validated_confidence,
                    context=context,
                    reason=pattern_info['name'],
                    metadata={'pattern': pattern}
                )
                matches.append(sensitive_match)
        
        return matches
    
    def _extract_context(self, text: str, start_pos: int, end_pos: int, 
                        window: int = 50) -> str:
        """Extract context around a match"""
        context_start = max(0, start_pos - window)
        context_end = min(len(text), end_pos + window)
        return text[context_start:context_end]
    
    def _validate_match(self, matched_text: str, category: RedactionCategory, 
                       context: str, base_confidence: float) -> float:
        """Validate and adjust confidence of a match"""
        confidence = base_confidence
        
        if category == RedactionCategory.PERSONAL_IDENTIFIERS:
            # Validate SSN format
            if re.match(r'\d{3}-\d{2}-\d{4}', matched_text):
                # Check for obviously fake SSNs
                if matched_text.startswith(('000', '666', '900')):
                    confidence *= 0.5
                else:
                    confidence *= 1.1
            
            # Validate email addresses
            if '@' in matched_text:
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', matched_text):
                    confidence *= 1.0
                else:
                    confidence *= 0.7
        
        elif category == RedactionCategory.FINANCIAL_INFO:
            # Validate credit card numbers using Luhn algorithm
            if re.match(r'\d{13,19}', matched_text.replace(' ', '').replace('-', '')):
                if self._luhn_check(matched_text.replace(' ', '').replace('-', '')):
                    confidence *= 1.2
                else:
                    confidence *= 0.6
        
        # Context-based confidence adjustments
        context_lower = context.lower()
        
        if category == RedactionCategory.MEDICAL_INFO:
            medical_keywords = ['patient', 'medical', 'health', 'doctor', 'hospital']
            if any(keyword in context_lower for keyword in medical_keywords):
                confidence *= 1.1
        
        elif category == RedactionCategory.LEGAL_PRIVILEGED:
            legal_keywords = ['attorney', 'lawyer', 'privileged', 'confidential']
            if any(keyword in context_lower for keyword in legal_keywords):
                confidence *= 1.2
        
        return min(confidence, 1.0)
    
    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm"""
        if not card_number.isdigit():
            return False
        
        digits = [int(d) for d in card_number]
        
        # Double every second digit from the right
        for i in range(len(digits) - 2, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
        
        return sum(digits) % 10 == 0
    
    def _resolve_overlaps(self, matches: List[SensitiveMatch]) -> List[SensitiveMatch]:
        """Resolve overlapping matches by keeping highest confidence"""
        if not matches:
            return matches
        
        # Sort by start position
        sorted_matches = sorted(matches, key=lambda m: m.start_position)
        
        resolved = []
        
        for match in sorted_matches:
            # Check for overlap with existing matches
            overlaps = False
            
            for existing in resolved:
                if (match.start_position < existing.end_position and 
                    match.end_position > existing.start_position):
                    # There's overlap
                    if match.confidence > existing.confidence:
                        resolved.remove(existing)
                    else:
                        overlaps = True
                    break
            
            if not overlaps:
                resolved.append(match)
        
        return resolved


class RedactionEngine:
    """Main redaction engine that applies redaction rules"""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        self.detector = SensitiveDataDetector()
        self.redaction_rules = self._initialize_default_rules()
        self.encryption_key = encryption_key
        if Fernet and encryption_key:
            self.cipher = Fernet(encryption_key)
        else:
            self.cipher = None
    
    def _initialize_default_rules(self) -> Dict[str, RedactionRule]:
        """Initialize default redaction rules"""
        return {
            'ssn_redaction': RedactionRule(
                name='SSN Redaction',
                category=RedactionCategory.PERSONAL_IDENTIFIERS,
                pattern=r'\b\d{3}-\d{2}-\d{4}\b',
                replacement_text='[REDACTED SSN]',
                redaction_method=RedactionMethod.REPLACEMENT_TEXT,
                confidence_threshold=0.8
            ),
            'email_redaction': RedactionRule(
                name='Email Redaction',
                category=RedactionCategory.PERSONAL_IDENTIFIERS,
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                replacement_text='[REDACTED EMAIL]',
                redaction_method=RedactionMethod.REPLACEMENT_TEXT,
                confidence_threshold=0.8
            ),
            'phone_redaction': RedactionRule(
                name='Phone Number Redaction',
                category=RedactionCategory.PERSONAL_IDENTIFIERS,
                pattern=r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                replacement_text='[REDACTED PHONE]',
                redaction_method=RedactionMethod.REPLACEMENT_TEXT,
                confidence_threshold=0.7
            ),
            'attorney_client_redaction': RedactionRule(
                name='Attorney-Client Privilege',
                category=RedactionCategory.ATTORNEY_CLIENT,
                pattern=r'(?i)attorney-client.*?(?:\.|$)',
                replacement_text='[ATTORNEY-CLIENT PRIVILEGED]',
                redaction_method=RedactionMethod.BLACK_BOX,
                confidence_threshold=0.9
            )
        }
    
    def add_custom_rule(self, rule: RedactionRule) -> None:
        """Add a custom redaction rule"""
        self.redaction_rules[rule.name] = rule
    
    def remove_rule(self, rule_name: str) -> None:
        """Remove a redaction rule"""
        if rule_name in self.redaction_rules:
            del self.redaction_rules[rule_name]
    
    def redact_document(self, text: str, custom_rules: Optional[List[RedactionRule]] = None,
                       redaction_level: RedactionLevel = RedactionLevel.CONFIDENTIAL) -> RedactionResult:
        """Redact sensitive content from document text"""
        
        # Detect sensitive content
        sensitive_matches = self.detector.detect_sensitive_content(text)
        
        # Apply custom rules if provided
        if custom_rules:
            for rule in custom_rules:
                rule_matches = self._apply_redaction_rule(text, rule)
                sensitive_matches.extend(rule_matches)
        
        # Apply default rules
        for rule in self.redaction_rules.values():
            rule_matches = self._apply_redaction_rule(text, rule)
            sensitive_matches.extend(rule_matches)
        
        # Remove duplicates and resolve overlaps
        sensitive_matches = self.detector._resolve_overlaps(sensitive_matches)
        
        # Apply redactions
        redacted_text, redaction_map = self._apply_redactions(text, sensitive_matches)
        
        # Generate summary
        redaction_summary = self._generate_redaction_summary(sensitive_matches)
        
        # Generate redaction key for encrypted redactions
        redaction_key = None
        if any(m.category == RedactionCategory.CLASSIFIED for m in sensitive_matches):
            redaction_key = base64.urlsafe_b64encode(
                hashlib.sha256(text.encode()).digest()[:32]
            ).decode()
        
        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            redaction_map=redaction_map,
            redaction_summary=redaction_summary,
            redacted_at=datetime.datetime.utcnow(),
            redaction_key=redaction_key,
            metadata={
                'redaction_level': redaction_level.value,
                'total_redactions': len(sensitive_matches),
                'rules_applied': len(self.redaction_rules)
            }
        )
    
    def _apply_redaction_rule(self, text: str, rule: RedactionRule) -> List[SensitiveMatch]:
        """Apply a specific redaction rule to text"""
        matches = []
        
        # Compile regex
        flags = 0 if rule.case_sensitive else re.IGNORECASE
        if rule.whole_word_only:
            pattern = rf'\b{rule.pattern}\b'
        else:
            pattern = rule.pattern
        
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            logging.warning(f"Invalid regex in rule '{rule.name}': {e}")
            return matches
        
        for match in regex.finditer(text):
            # Check confidence threshold
            confidence = 0.9  # Default for rule-based matches
            
            if confidence >= rule.confidence_threshold:
                context = self.detector._extract_context(text, match.start(), match.end())
                
                sensitive_match = SensitiveMatch(
                    text=match.group(0),
                    category=rule.category,
                    start_position=match.start(),
                    end_position=match.end(),
                    confidence=confidence,
                    context=context,
                    reason=rule.name,
                    metadata={'rule': rule.name, 'method': rule.redaction_method.value}
                )
                matches.append(sensitive_match)
        
        return matches
    
    def _apply_redactions(self, text: str, matches: List[SensitiveMatch]) -> Tuple[str, Dict[int, SensitiveMatch]]:
        """Apply redaction methods to the text"""
        if not matches:
            return text, {}
        
        # Sort matches by position (reverse order to maintain positions)
        sorted_matches = sorted(matches, key=lambda m: m.start_position, reverse=True)
        
        redacted_text = text
        redaction_map = {}
        
        for match in sorted_matches:
            # Determine redaction method
            redaction_method = self._determine_redaction_method(match)
            replacement = self._generate_replacement_text(match, redaction_method)
            
            # Apply redaction
            redacted_text = (redacted_text[:match.start_position] + 
                           replacement + 
                           redacted_text[match.end_position:])
            
            # Update redaction map (adjust positions for previous redactions)
            redaction_map[match.start_position] = match
        
        return redacted_text, redaction_map
    
    def _determine_redaction_method(self, match: SensitiveMatch) -> RedactionMethod:
        """Determine appropriate redaction method based on content type"""
        # Check if rule specifies method
        if match.metadata and 'method' in match.metadata:
            return RedactionMethod(match.metadata['method'])
        
        # Default methods by category
        method_map = {
            RedactionCategory.PERSONAL_IDENTIFIERS: RedactionMethod.REPLACEMENT_TEXT,
            RedactionCategory.FINANCIAL_INFO: RedactionMethod.BLACK_BOX,
            RedactionCategory.MEDICAL_INFO: RedactionMethod.REPLACEMENT_TEXT,
            RedactionCategory.LEGAL_PRIVILEGED: RedactionMethod.BLACK_BOX,
            RedactionCategory.ATTORNEY_CLIENT: RedactionMethod.BLACK_BOX,
            RedactionCategory.CLASSIFIED: RedactionMethod.ENCRYPTED_REDACTION,
            RedactionCategory.SETTLEMENT_TERMS: RedactionMethod.WHITE_BOX,
            RedactionCategory.TRADE_SECRETS: RedactionMethod.BLACK_BOX
        }
        
        return method_map.get(match.category, RedactionMethod.REPLACEMENT_TEXT)
    
    def _generate_replacement_text(self, match: SensitiveMatch, method: RedactionMethod) -> str:
        """Generate replacement text based on redaction method"""
        if method == RedactionMethod.BLACK_BOX:
            return '█' * len(match.text)
        
        elif method == RedactionMethod.WHITE_BOX:
            return '▓' * len(match.text)
        
        elif method == RedactionMethod.REPLACEMENT_TEXT:
            category_replacements = {
                RedactionCategory.PERSONAL_IDENTIFIERS: f'[REDACTED {match.reason.upper()}]',
                RedactionCategory.FINANCIAL_INFO: '[REDACTED FINANCIAL INFO]',
                RedactionCategory.MEDICAL_INFO: '[REDACTED MEDICAL INFO]',
                RedactionCategory.WITNESS_IDENTITY: '[REDACTED WITNESS NAME]',
                RedactionCategory.MINOR_INFORMATION: '[REDACTED MINOR INFO]'
            }
            return category_replacements.get(match.category, '[REDACTED]')
        
        elif method == RedactionMethod.HASH_REDACTION:
            hash_value = hashlib.sha256(match.text.encode()).hexdigest()[:16]
            return f'[HASH:{hash_value}]'
        
        elif method == RedactionMethod.ENCRYPTED_REDACTION:
            if self.cipher:
                try:
                    encrypted = self.cipher.encrypt(match.text.encode())
                    encrypted_b64 = base64.urlsafe_b64encode(encrypted).decode()
                    return f'[ENCRYPTED:{encrypted_b64[:20]}...]'
                except Exception as e:
                    logging.warning(f"Encryption failed: {e}")
                    return '[ENCRYPTED CONTENT]'
            else:
                return '[ENCRYPTED CONTENT]'
        
        elif method == RedactionMethod.REMOVAL:
            return ''
        
        else:
            return '[REDACTED]'
    
    def _generate_redaction_summary(self, matches: List[SensitiveMatch]) -> Dict[str, Any]:
        """Generate summary of redaction operations"""
        summary = {
            'total_redactions': len(matches),
            'by_category': {},
            'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
            'by_method': {},
            'sensitive_patterns': []
        }
        
        for match in matches:
            # Count by category
            category = match.category.value
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count by confidence level
            if match.confidence >= 0.8:
                summary['by_confidence']['high'] += 1
            elif match.confidence >= 0.6:
                summary['by_confidence']['medium'] += 1
            else:
                summary['by_confidence']['low'] += 1
            
            # Track patterns
            if match.reason not in summary['sensitive_patterns']:
                summary['sensitive_patterns'].append(match.reason)
        
        return summary
    
    def unredact_document(self, redaction_result: RedactionResult, 
                         redaction_key: Optional[str] = None) -> Optional[str]:
        """Attempt to unredact document (only for reversible redactions)"""
        if not self.cipher or not redaction_key:
            logging.warning("Cannot unredact: missing cipher or key")
            return None
        
        # This is a simplified implementation
        # In practice, would need to store encrypted original segments
        try:
            # For demonstration - in real implementation would decrypt stored segments
            return redaction_result.original_text
        except Exception as e:
            logging.error(f"Unredaction failed: {e}")
            return None
    
    def generate_redaction_report(self, redaction_result: RedactionResult) -> Dict[str, Any]:
        """Generate comprehensive redaction report"""
        return {
            'redaction_metadata': {
                'redacted_at': redaction_result.redacted_at.isoformat(),
                'total_length': len(redaction_result.original_text),
                'redacted_length': len(redaction_result.redacted_text),
                'reduction_ratio': 1 - (len(redaction_result.redacted_text) / len(redaction_result.original_text))
            },
            'redaction_summary': redaction_result.redaction_summary,
            'redaction_locations': [
                {
                    'position': pos,
                    'category': match.category.value,
                    'reason': match.reason,
                    'confidence': match.confidence,
                    'length': len(match.text)
                }
                for pos, match in redaction_result.redaction_map.items()
            ],
            'quality_metrics': {
                'high_confidence_redactions': sum(
                    1 for match in redaction_result.redaction_map.values() 
                    if match.confidence >= 0.8
                ),
                'potential_false_positives': sum(
                    1 for match in redaction_result.redaction_map.values() 
                    if match.confidence < 0.6
                )
            },
            'compliance_status': {
                'personal_identifiers_protected': RedactionCategory.PERSONAL_IDENTIFIERS.value in redaction_result.redaction_summary.get('by_category', {}),
                'privileged_content_protected': any(
                    cat in redaction_result.redaction_summary.get('by_category', {})
                    for cat in [RedactionCategory.ATTORNEY_CLIENT.value, RedactionCategory.WORK_PRODUCT.value]
                ),
                'financial_info_protected': RedactionCategory.FINANCIAL_INFO.value in redaction_result.redaction_summary.get('by_category', {})
            }
        }


class RedactionQualityAnalyzer:
    """Analyze quality and completeness of redactions"""
    
    def __init__(self):
        self.known_leakage_patterns = [
            # Patterns that might indicate incomplete redaction
            r'\[REDACTED\]\s*(?:\w+@\w+\.\w+)',  # Email after redaction
            r'\[REDACTED\]\s*(?:\(\d{3}\)\s*\d{3}-\d{4})',  # Phone after redaction
            r'\[REDACTED\]\s*(?:\d{3}-\d{2}-\d{4})',  # SSN after redaction
        ]
    
    def analyze_redaction_quality(self, redaction_result: RedactionResult) -> Dict[str, Any]:
        """Analyze the quality and completeness of redactions"""
        analysis = {
            'completeness_score': 0.0,
            'consistency_score': 0.0,
            'potential_leaks': [],
            'recommendations': [],
            'overall_quality': 'unknown'
        }
        
        # Check for potential information leakage
        leaks = self._detect_information_leakage(redaction_result.redacted_text)
        analysis['potential_leaks'] = leaks
        
        # Calculate completeness score
        analysis['completeness_score'] = self._calculate_completeness_score(redaction_result)
        
        # Calculate consistency score
        analysis['consistency_score'] = self._calculate_consistency_score(redaction_result)
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_quality_recommendations(redaction_result, leaks)
        
        # Calculate overall quality
        overall_score = (analysis['completeness_score'] + analysis['consistency_score']) / 2
        if overall_score >= 0.9:
            analysis['overall_quality'] = 'excellent'
        elif overall_score >= 0.8:
            analysis['overall_quality'] = 'good'
        elif overall_score >= 0.7:
            analysis['overall_quality'] = 'fair'
        else:
            analysis['overall_quality'] = 'poor'
        
        return analysis
    
    def _detect_information_leakage(self, redacted_text: str) -> List[Dict[str, Any]]:
        """Detect potential information leakage in redacted text"""
        leaks = []
        
        for pattern in self.known_leakage_patterns:
            matches = re.finditer(pattern, redacted_text)
            for match in matches:
                leaks.append({
                    'type': 'potential_leak',
                    'position': match.start(),
                    'text': match.group(0),
                    'concern': 'Sensitive information may follow redaction marker'
                })
        
        return leaks
    
    def _calculate_completeness_score(self, redaction_result: RedactionResult) -> float:
        """Calculate completeness score based on detected vs redacted content"""
        # This is a simplified implementation
        # Real implementation would use more sophisticated analysis
        
        total_sensitive = len(redaction_result.redaction_map)
        high_confidence = sum(1 for match in redaction_result.redaction_map.values() 
                             if match.confidence >= 0.8)
        
        if total_sensitive == 0:
            return 1.0
        
        return high_confidence / total_sensitive
    
    def _calculate_consistency_score(self, redaction_result: RedactionResult) -> float:
        """Calculate consistency score based on uniform redaction of similar content"""
        # Check if similar types of content are redacted consistently
        category_methods = {}
        
        for match in redaction_result.redaction_map.values():
            category = match.category
            method = match.metadata.get('method', 'unknown') if match.metadata else 'unknown'
            
            if category not in category_methods:
                category_methods[category] = set()
            category_methods[category].add(method)
        
        # Calculate consistency (should use same method for same category)
        consistent_categories = sum(1 for methods in category_methods.values() if len(methods) == 1)
        total_categories = len(category_methods)
        
        if total_categories == 0:
            return 1.0
        
        return consistent_categories / total_categories
    
    def _generate_quality_recommendations(self, redaction_result: RedactionResult, 
                                        leaks: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for improving redaction quality"""
        recommendations = []
        
        if leaks:
            recommendations.append("Review potential information leakage patterns")
        
        # Check for low confidence redactions
        low_confidence = sum(1 for match in redaction_result.redaction_map.values() 
                           if match.confidence < 0.6)
        if low_confidence > 0:
            recommendations.append(f"Review {low_confidence} low-confidence redactions for accuracy")
        
        # Check category coverage
        summary = redaction_result.redaction_summary
        if 'personal_identifiers' not in summary.get('by_category', {}):
            recommendations.append("Consider scanning for personal identifiers")
        
        if 'financial_info' not in summary.get('by_category', {}):
            recommendations.append("Consider scanning for financial information")
        
        return recommendations