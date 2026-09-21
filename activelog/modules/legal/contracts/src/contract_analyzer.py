"""
Contract Analysis and Extraction Tools
Advanced contract processing, clause identification, and legal term extraction.
"""
import re
import datetime
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class ContractType(Enum):
    """Types of legal contracts"""
    SERVICE_AGREEMENT = "service_agreement"
    EMPLOYMENT_CONTRACT = "employment_contract"
    NDA = "non_disclosure_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    PURCHASE_AGREEMENT = "purchase_agreement"
    LICENSING_AGREEMENT = "licensing_agreement"
    PARTNERSHIP_AGREEMENT = "partnership_agreement"
    VENDOR_AGREEMENT = "vendor_agreement"
    CONSULTING_AGREEMENT = "consulting_agreement"
    MASTER_SERVICE_AGREEMENT = "master_service_agreement"
    STATEMENT_OF_WORK = "statement_of_work"
    OTHER = "other"


class ClauseType(Enum):
    """Types of contract clauses"""
    TERMINATION = "termination"
    PAYMENT_TERMS = "payment_terms"
    LIABILITY_LIMITATION = "liability_limitation"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    CONFIDENTIALITY = "confidentiality"
    INDEMNIFICATION = "indemnification"
    DISPUTE_RESOLUTION = "dispute_resolution"
    GOVERNING_LAW = "governing_law"
    FORCE_MAJEURE = "force_majeure"
    ASSIGNMENT = "assignment"
    AMENDMENT = "amendment"
    ENTIRE_AGREEMENT = "entire_agreement"
    SEVERABILITY = "severability"
    WARRANTIES = "warranties"
    DELIVERABLES = "deliverables"
    SCOPE_OF_WORK = "scope_of_work"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ContractClause:
    """Individual contract clause"""
    clause_type: ClauseType
    text: str
    start_position: int
    end_position: int
    confidence: float
    risk_level: RiskLevel
    summary: Optional[str] = None
    key_terms: Optional[List[str]] = None
    obligations: Optional[List[str]] = None
    risks: Optional[List[str]] = None


@dataclass
class ContractParty:
    """Contract party information"""
    name: str
    role: str  # "client", "vendor", "licensor", etc.
    address: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None
    entity_type: Optional[str] = None  # "corporation", "individual", etc.
    jurisdiction: Optional[str] = None


@dataclass
class ContractTerm:
    """Important contract terms and dates"""
    term_type: str  # "effective_date", "expiration_date", "payment_due", etc.
    value: str
    date_value: Optional[datetime.date] = None
    amount_value: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ContractAnalysisResult:
    """Complete contract analysis results"""
    document_id: str
    contract_type: ContractType
    title: Optional[str]
    parties: List[ContractParty]
    clauses: List[ContractClause]
    terms: List[ContractTerm]
    key_dates: Dict[str, datetime.date]
    financial_terms: Dict[str, Any]
    overall_risk_score: float
    compliance_issues: List[str]
    recommendations: List[str]
    analyzed_at: datetime.datetime
    metadata: Optional[Dict[str, Any]] = None


class ContractClauseExtractor:
    """Extract and classify contract clauses"""
    
    def __init__(self):
        self.clause_patterns = {
            ClauseType.TERMINATION: [
                r'(?i)(?:termination|terminate|end|expire|dissolution).*?(?:agreement|contract|party|notice)',
                r'(?i)(?:either party|any party).*?(?:terminate|end).*?(?:agreement|contract)',
                r'(?i)(?:upon|after).*?(?:\d+\s*(?:days|months|years)).*?(?:notice|termination)',
                r'(?i)(?:breach|default|violation).*?(?:terminate|termination|end)',
            ],
            ClauseType.PAYMENT_TERMS: [
                r'(?i)(?:payment|pay|compensation|fee|amount).*?(?:due|payable|terms|schedule)',
                r'(?i)(?:\$[\d,]+\.?\d*|payment of).*?(?:within|by|on or before)',
                r'(?i)(?:invoice|billing|payment).*?(?:\d+\s*days|net \d+|terms)',
                r'(?i)(?:late fee|penalty|interest).*?(?:payment|overdue)',
            ],
            ClauseType.LIABILITY_LIMITATION: [
                r'(?i)(?:limit|limitation|exclude|exclusion).*?(?:liability|damages|loss)',
                r'(?i)(?:neither party|no party|company).*?(?:liable|responsible).*?(?:damages|loss)',
                r'(?i)(?:indirect|consequential|incidental|punitive).*?damages',
                r'(?i)(?:aggregate|total|maximum).*?liability.*?(?:limited to|shall not exceed)',
            ],
            ClauseType.INTELLECTUAL_PROPERTY: [
                r'(?i)(?:intellectual property|IP|patent|trademark|copyright|trade secret)',
                r'(?i)(?:proprietary|confidential).*?(?:information|materials|data)',
                r'(?i)(?:work product|deliverables|invention).*?(?:ownership|owned by|belong)',
                r'(?i)(?:license|licensed|grant).*?(?:rights|use|access)',
            ],
            ClauseType.CONFIDENTIALITY: [
                r'(?i)(?:confidential|confidentiality|non-disclosure|proprietary).*?(?:information|data|materials)',
                r'(?i)(?:disclose|disclosure|reveal).*?(?:confidential|proprietary)',
                r'(?i)(?:maintain|keep|hold).*?(?:confidence|confidential|secret)',
                r'(?i)(?:third party|third parties).*?(?:confidential|proprietary)',
            ],
            ClauseType.INDEMNIFICATION: [
                r'(?i)(?:indemnify|indemnification|hold harmless|defend).*?(?:against|from)',
                r'(?i)(?:claims|suits|actions|proceedings).*?(?:arising|resulting).*?(?:from|out of)',
                r'(?i)(?:losses|damages|costs|expenses).*?(?:incurred|suffered).*?(?:by|from)',
            ],
            ClauseType.DISPUTE_RESOLUTION: [
                r'(?i)(?:dispute|disagreement|controversy).*?(?:resolution|resolved|settle)',
                r'(?i)(?:arbitration|mediation|litigation|court).*?(?:binding|final|exclusive)',
                r'(?i)(?:good faith|meet and confer|negotiate).*?(?:dispute|resolution)',
            ],
            ClauseType.GOVERNING_LAW: [
                r'(?i)(?:governed by|governing law|laws of).*?(?:state|jurisdiction|country)',
                r'(?i)(?:subject to|accordance with).*?(?:laws|statutes|regulations)',
                r'(?i)(?:jurisdiction|venue|forum).*?(?:courts|state|federal)',
            ],
            ClauseType.FORCE_MAJEURE: [
                r'(?i)(?:force majeure|act of god|beyond.*?control|unforeseeable)',
                r'(?i)(?:war|terrorism|pandemic|natural disaster|government action)',
                r'(?i)(?:prevent|hinder|delay).*?(?:performance|obligations|duties)',
            ]
        }
        
        self.risk_indicators = {
            RiskLevel.CRITICAL: [
                'unlimited liability', 'personal guarantee', 'criminal liability',
                'gross negligence', 'willful misconduct', 'indemnify all claims'
            ],
            RiskLevel.HIGH: [
                'automatic renewal', 'exclusive rights', 'non-compete',
                'liquidated damages', 'specific performance', 'penalty'
            ],
            RiskLevel.MEDIUM: [
                'reasonable efforts', 'material breach', 'cure period',
                'consequential damages', 'third party claims'
            ],
            RiskLevel.LOW: [
                'best efforts', 'mutual consent', 'good faith',
                'standard terms', 'commercially reasonable'
            ]
        }
    
    def extract_clauses(self, contract_text: str) -> List[ContractClause]:
        """Extract and classify contract clauses"""
        clauses = []
        text_lower = contract_text.lower()
        
        for clause_type, patterns in self.clause_patterns.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, contract_text, re.IGNORECASE | re.DOTALL))
                
                for match in matches:
                    # Expand match to include more context
                    start_pos, end_pos = self._expand_clause_context(
                        contract_text, match.start(), match.end()
                    )
                    
                    clause_text = contract_text[start_pos:end_pos]
                    
                    # Assess risk level
                    risk_level = self._assess_clause_risk(clause_text)
                    
                    # Extract key terms
                    key_terms = self._extract_key_terms(clause_text, clause_type)
                    
                    # Generate summary
                    summary = self._generate_clause_summary(clause_text, clause_type)
                    
                    clause = ContractClause(
                        clause_type=clause_type,
                        text=clause_text.strip(),
                        start_position=start_pos,
                        end_position=end_pos,
                        confidence=0.8,  # Base confidence
                        risk_level=risk_level,
                        summary=summary,
                        key_terms=key_terms,
                        obligations=self._extract_obligations(clause_text),
                        risks=self._identify_risks(clause_text, clause_type)
                    )
                    
                    clauses.append(clause)
        
        # Remove duplicate and overlapping clauses
        return self._deduplicate_clauses(clauses)
    
    def _expand_clause_context(self, text: str, start: int, end: int, 
                              max_expansion: int = 500) -> Tuple[int, int]:
        """Expand clause boundaries to include full context"""
        # Find sentence boundaries
        expanded_start = max(0, start - max_expansion)
        expanded_end = min(len(text), end + max_expansion)
        
        # Look for paragraph breaks or section headers
        before_text = text[expanded_start:start]
        after_text = text[end:expanded_end]
        
        # Find last sentence start before match
        sentence_starts = list(re.finditer(r'[.!?]\s*[A-Z]', before_text))
        if sentence_starts:
            expanded_start = start - len(before_text) + sentence_starts[-1].end() - 1
        
        # Find next sentence end after match
        sentence_ends = list(re.finditer(r'[.!?]\s', after_text))
        if sentence_ends:
            expanded_end = end + sentence_ends[0].end()
        
        return expanded_start, expanded_end
    
    def _assess_clause_risk(self, clause_text: str) -> RiskLevel:
        """Assess risk level of a clause"""
        text_lower = clause_text.lower()
        
        # Count risk indicators
        for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            indicators = self.risk_indicators.get(risk_level, [])
            if any(indicator in text_lower for indicator in indicators):
                return risk_level
        
        return RiskLevel.MEDIUM  # Default
    
    def _extract_key_terms(self, clause_text: str, clause_type: ClauseType) -> List[str]:
        """Extract key terms from clause"""
        key_terms = []
        
        # Extract dates
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}\s+(?:days|months|years|weeks)',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, clause_text, re.IGNORECASE)
            key_terms.extend(matches)
        
        # Extract monetary amounts
        money_pattern = r'\$[\d,]+\.?\d*'
        money_matches = re.findall(money_pattern, clause_text)
        key_terms.extend(money_matches)
        
        # Extract percentages
        percent_pattern = r'\d+\.?\d*\s*%'
        percent_matches = re.findall(percent_pattern, clause_text)
        key_terms.extend(percent_matches)
        
        # Clause-specific extractions
        if clause_type == ClauseType.TERMINATION:
            termination_terms = re.findall(r'(?i)(?:\d+\s*(?:days|months|years))(?:\s*(?:notice|prior notice))?', clause_text)
            key_terms.extend(termination_terms)
        
        elif clause_type == ClauseType.PAYMENT_TERMS:
            payment_terms = re.findall(r'(?i)(?:net\s*\d+|within\s*\d+\s*days|payment\s*due)', clause_text)
            key_terms.extend(payment_terms)
        
        return list(set(key_terms))  # Remove duplicates
    
    def _generate_clause_summary(self, clause_text: str, clause_type: ClauseType) -> str:
        """Generate a summary of the clause"""
        # This is a simplified summary - in production would use NLP
        summaries = {
            ClauseType.TERMINATION: "Outlines conditions and procedures for contract termination",
            ClauseType.PAYMENT_TERMS: "Specifies payment amounts, timing, and procedures",
            ClauseType.LIABILITY_LIMITATION: "Limits liability exposure and damages",
            ClauseType.INTELLECTUAL_PROPERTY: "Defines IP ownership and usage rights",
            ClauseType.CONFIDENTIALITY: "Protects confidential information and trade secrets",
            ClauseType.INDEMNIFICATION: "Allocates responsibility for third-party claims",
            ClauseType.DISPUTE_RESOLUTION: "Establishes process for resolving disputes",
            ClauseType.GOVERNING_LAW: "Specifies applicable law and jurisdiction",
            ClauseType.FORCE_MAJEURE: "Addresses unforeseeable circumstances affecting performance"
        }
        
        return summaries.get(clause_type, "Contract provision requiring review")
    
    def _extract_obligations(self, clause_text: str) -> List[str]:
        """Extract obligations from clause text"""
        obligations = []
        
        # Look for obligation indicators
        obligation_patterns = [
            r'(?i)(?:shall|must|required to|obligated to|responsible for)\s+([^.]+)',
            r'(?i)(?:party|parties|company|client|vendor)\s+(?:shall|must|will)\s+([^.]+)',
            r'(?i)(?:agrees to|undertakes to|commits to)\s+([^.]+)'
        ]
        
        for pattern in obligation_patterns:
            matches = re.findall(pattern, clause_text)
            obligations.extend([match.strip() for match in matches])
        
        return obligations[:5]  # Limit to top 5
    
    def _identify_risks(self, clause_text: str, clause_type: ClauseType) -> List[str]:
        """Identify potential risks in clause"""
        risks = []
        text_lower = clause_text.lower()
        
        # General risk indicators
        if 'unlimited' in text_lower:
            risks.append("Unlimited liability exposure")
        
        if 'automatic' in text_lower and 'renewal' in text_lower:
            risks.append("Automatic contract renewal")
        
        if 'exclusive' in text_lower:
            risks.append("Exclusive rights granted")
        
        if 'penalty' in text_lower or 'liquidated damages' in text_lower:
            risks.append("Financial penalties specified")
        
        # Clause-specific risks
        if clause_type == ClauseType.TERMINATION:
            if 'convenience' not in text_lower:
                risks.append("Limited termination rights")
        
        elif clause_type == ClauseType.LIABILITY_LIMITATION:
            if 'gross negligence' in text_lower:
                risks.append("Liability exclusion may not apply to gross negligence")
        
        return risks
    
    def _deduplicate_clauses(self, clauses: List[ContractClause]) -> List[ContractClause]:
        """Remove duplicate and overlapping clauses"""
        if not clauses:
            return clauses
        
        # Sort by start position
        sorted_clauses = sorted(clauses, key=lambda c: c.start_position)
        
        deduplicated = []
        
        for clause in sorted_clauses:
            # Check for overlap with existing clauses
            overlaps = False
            
            for existing in deduplicated:
                overlap_start = max(clause.start_position, existing.start_position)
                overlap_end = min(clause.end_position, existing.end_position)
                
                if overlap_end > overlap_start:
                    overlap_ratio = (overlap_end - overlap_start) / min(
                        clause.end_position - clause.start_position,
                        existing.end_position - existing.start_position
                    )
                    
                    if overlap_ratio > 0.5:  # 50% overlap threshold
                        # Keep the one with higher confidence or more specific type
                        if clause.confidence > existing.confidence:
                            deduplicated.remove(existing)
                        else:
                            overlaps = True
                        break
            
            if not overlaps:
                deduplicated.append(clause)
        
        return deduplicated


class ContractEntityExtractor:
    """Extract entities like parties, dates, amounts from contracts"""
    
    def __init__(self):
        self.entity_patterns = {
            'company_names': [
                r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc\.?|LLC|Corp\.?|Corporation|Company|Co\.?|Ltd\.?)',
                r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+a\s+(?:Delaware|California|New York|Texas).*?(?:corporation|company)',
            ],
            'person_names': [
                r'(?i)(?:Mr\.?|Ms\.?|Mrs\.?|Dr\.?)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:,\s*(?:individually|personally))',
            ],
            'addresses': [
                r'\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln)[\s,]+[A-Za-z\s,]+\d{5}',
                r'[A-Za-z\s,]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?',
            ],
            'dates': [
                r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                r'(?i)(?:effective|execution|expiration|termination)\s+date[:\s]+([^,\n]+)',
            ],
            'monetary_amounts': [
                r'\$[\d,]+\.?\d*(?:\s*(?:million|thousand|billion|trillion))?',
                r'(?i)(?:dollars?|usd)\s*[\d,]+\.?\d*',
            ],
            'email_addresses': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            'phone_numbers': [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\+\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            ]
        }
    
    def extract_parties(self, contract_text: str) -> List[ContractParty]:
        """Extract contract parties"""
        parties = []
        
        # Extract company names
        company_names = set()
        for pattern in self.entity_patterns['company_names']:
            matches = re.findall(pattern, contract_text, re.IGNORECASE)
            company_names.update(matches)
        
        # Extract person names
        person_names = set()
        for pattern in self.entity_patterns['person_names']:
            matches = re.findall(pattern, contract_text, re.IGNORECASE)
            person_names.update(matches)
        
        # Extract addresses
        addresses = []
        for pattern in self.entity_patterns['addresses']:
            matches = re.findall(pattern, contract_text)
            addresses.extend(matches)
        
        # Extract contact info
        emails = []
        for pattern in self.entity_patterns['email_addresses']:
            matches = re.findall(pattern, contract_text)
            emails.extend(matches)
        
        phones = []
        for pattern in self.entity_patterns['phone_numbers']:
            matches = re.findall(pattern, contract_text)
            phones.extend(matches)
        
        # Create party objects
        for company in company_names:
            party = ContractParty(
                name=company,
                role=self._infer_party_role(contract_text, company),
                entity_type="corporation",
                address=addresses[0] if addresses else None,
                contact_info={
                    'email': emails[0] if emails else None,
                    'phone': phones[0] if phones else None
                }
            )
            parties.append(party)
        
        for person in person_names:
            party = ContractParty(
                name=person,
                role=self._infer_party_role(contract_text, person),
                entity_type="individual",
                contact_info={
                    'email': emails[0] if emails else None,
                    'phone': phones[0] if phones else None
                }
            )
            parties.append(party)
        
        return parties[:4]  # Limit to reasonable number
    
    def extract_terms(self, contract_text: str) -> List[ContractTerm]:
        """Extract important contract terms"""
        terms = []
        
        # Extract dates
        date_terms = self._extract_date_terms(contract_text)
        terms.extend(date_terms)
        
        # Extract monetary terms
        money_terms = self._extract_monetary_terms(contract_text)
        terms.extend(money_terms)
        
        # Extract duration terms
        duration_terms = self._extract_duration_terms(contract_text)
        terms.extend(duration_terms)
        
        return terms
    
    def _infer_party_role(self, contract_text: str, party_name: str) -> str:
        """Infer the role of a party in the contract"""
        text_lower = contract_text.lower()
        name_lower = party_name.lower()
        
        # Look for role indicators near the party name
        context_window = 200
        
        for match in re.finditer(re.escape(name_lower), text_lower):
            start = max(0, match.start() - context_window)
            end = min(len(text_lower), match.end() + context_window)
            context = text_lower[start:end]
            
            if any(term in context for term in ['client', 'customer', 'buyer', 'purchaser']):
                return 'client'
            elif any(term in context for term in ['vendor', 'supplier', 'seller', 'provider']):
                return 'vendor'
            elif any(term in context for term in ['contractor', 'consultant', 'service provider']):
                return 'contractor'
            elif any(term in context for term in ['licensor', 'grantor']):
                return 'licensor'
            elif any(term in context for term in ['licensee', 'grantee']):
                return 'licensee'
        
        return 'party'  # Default
    
    def _extract_date_terms(self, contract_text: str) -> List[ContractTerm]:
        """Extract date-related terms"""
        terms = []
        
        date_term_patterns = {
            'effective_date': r'(?i)(?:effective|commencement|start)\s*date[:\s]*([^,\n\.]+)',
            'expiration_date': r'(?i)(?:expiration|termination|end)\s*date[:\s]*([^,\n\.]+)',
            'execution_date': r'(?i)(?:execution|signing|executed)\s*date[:\s]*([^,\n\.]+)',
            'delivery_date': r'(?i)(?:delivery|completion|due)\s*date[:\s]*([^,\n\.]+)'
        }
        
        for term_type, pattern in date_term_patterns.items():
            matches = re.findall(pattern, contract_text)
            for match in matches:
                # Try to parse the date
                parsed_date = self._parse_date_string(match.strip())
                
                term = ContractTerm(
                    term_type=term_type,
                    value=match.strip(),
                    date_value=parsed_date,
                    description=f"Contract {term_type.replace('_', ' ')}"
                )
                terms.append(term)
        
        return terms
    
    def _extract_monetary_terms(self, contract_text: str) -> List[ContractTerm]:
        """Extract monetary terms"""
        terms = []
        
        # Find monetary amounts with context
        money_patterns = [
            r'(?i)(?:payment|fee|cost|price|amount).*?\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?).*?(?i)(?:per|monthly|annually|yearly)',
            r'(?i)(?:total|sum|aggregate).*?\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        for pattern in money_patterns:
            matches = re.finditer(pattern, contract_text)
            for match in matches:
                amount_str = match.group(1)
                amount_value = float(amount_str.replace(',', ''))
                
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(contract_text), match.end() + 50)
                context = contract_text[start:end]
                
                term = ContractTerm(
                    term_type='payment_amount',
                    value=f"${amount_str}",
                    amount_value=amount_value,
                    currency='USD',
                    description=f"Payment term: {context.strip()[:100]}..."
                )
                terms.append(term)
        
        return terms
    
    def _extract_duration_terms(self, contract_text: str) -> List[ContractTerm]:
        """Extract duration and time-related terms"""
        terms = []
        
        duration_patterns = [
            r'(?i)(?:term|period|duration).*?(\d+)\s*(years?|months?|days?|weeks?)',
            r'(?i)(\d+)\s*(year|month|day|week)\s*(?:term|period|contract)',
            r'(?i)(?:notice|notification).*?(\d+)\s*(days?|weeks?|months?)',
        ]
        
        for pattern in duration_patterns:
            matches = re.finditer(pattern, contract_text)
            for match in matches:
                number = int(match.group(1))
                unit = match.group(2).lower()
                
                term = ContractTerm(
                    term_type='duration',
                    value=f"{number} {unit}",
                    description=f"Contract duration or notice period"
                )
                terms.append(term)
        
        return terms
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime.date]:
        """Parse a date string into a datetime.date object"""
        date_str = date_str.strip()
        
        # Common date formats
        formats = [
            '%B %d, %Y',      # January 1, 2024
            '%b %d, %Y',      # Jan 1, 2024
            '%m/%d/%Y',       # 1/1/2024
            '%m-%d-%Y',       # 1-1-2024
            '%Y-%m-%d',       # 2024-1-1
            '%d/%m/%Y',       # 1/1/2024 (international)
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None


class ContractAnalyzer:
    """Main contract analysis system"""
    
    def __init__(self):
        self.clause_extractor = ContractClauseExtractor()
        self.entity_extractor = ContractEntityExtractor()
        self.contract_type_classifier = ContractTypeClassifier()
        self.analysis_cache = {}
    
    def analyze_contract(self, contract_text: str, document_id: str = None) -> ContractAnalysisResult:
        """Perform comprehensive contract analysis"""
        if not document_id:
            document_id = hashlib.md5(contract_text.encode()).hexdigest()
        
        # Check cache
        if document_id in self.analysis_cache:
            return self.analysis_cache[document_id]
        
        try:
            # Classify contract type
            contract_type = self.contract_type_classifier.classify_contract(contract_text)
            
            # Extract contract title
            title = self._extract_contract_title(contract_text)
            
            # Extract parties
            parties = self.entity_extractor.extract_parties(contract_text)
            
            # Extract clauses
            clauses = self.clause_extractor.extract_clauses(contract_text)
            
            # Extract terms
            terms = self.entity_extractor.extract_terms(contract_text)
            
            # Extract key dates
            key_dates = self._extract_key_dates(terms)
            
            # Extract financial terms
            financial_terms = self._extract_financial_terms(terms, clauses)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(clauses, terms)
            
            # Identify compliance issues
            compliance_issues = self._identify_compliance_issues(clauses, contract_type)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(clauses, risk_score, compliance_issues)
            
            # Create analysis result
            result = ContractAnalysisResult(
                document_id=document_id,
                contract_type=contract_type,
                title=title,
                parties=parties,
                clauses=clauses,
                terms=terms,
                key_dates=key_dates,
                financial_terms=financial_terms,
                overall_risk_score=risk_score,
                compliance_issues=compliance_issues,
                recommendations=recommendations,
                analyzed_at=datetime.datetime.utcnow(),
                metadata={
                    'text_length': len(contract_text),
                    'clause_count': len(clauses),
                    'party_count': len(parties),
                    'term_count': len(terms)
                }
            )
            
            # Cache result
            self.analysis_cache[document_id] = result
            
            return result
            
        except Exception as e:
            logging.error(f"Error analyzing contract {document_id}: {e}")
            raise
    
    def _extract_contract_title(self, contract_text: str) -> Optional[str]:
        """Extract contract title"""
        # Look for title patterns
        title_patterns = [
            r'^([A-Z][A-Z\s]+AGREEMENT)',
            r'^([A-Z][A-Z\s]+CONTRACT)',
            r'(?i)^((?:SERVICE|EMPLOYMENT|CONSULTING|LICENSING|PURCHASE)\s+AGREEMENT)',
            r'^([A-Z][^.]+)$'  # First line if all caps
        ]
        
        lines = contract_text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in title_patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(1).title()
        
        return None
    
    def _extract_key_dates(self, terms: List[ContractTerm]) -> Dict[str, datetime.date]:
        """Extract key dates from terms"""
        key_dates = {}
        
        for term in terms:
            if term.date_value and term.term_type in [
                'effective_date', 'expiration_date', 'execution_date', 'delivery_date'
            ]:
                key_dates[term.term_type] = term.date_value
        
        return key_dates
    
    def _extract_financial_terms(self, terms: List[ContractTerm], 
                                clauses: List[ContractClause]) -> Dict[str, Any]:
        """Extract financial terms"""
        financial_terms = {
            'total_value': None,
            'payment_schedule': [],
            'currency': 'USD',
            'payment_terms': None
        }
        
        # Find monetary amounts
        amounts = []
        for term in terms:
            if term.amount_value:
                amounts.append({
                    'amount': term.amount_value,
                    'currency': term.currency or 'USD',
                    'description': term.description
                })
        
        if amounts:
            financial_terms['total_value'] = max(amounts, key=lambda x: x['amount'])
            financial_terms['payment_schedule'] = amounts
        
        # Extract payment terms from clauses
        payment_clauses = [c for c in clauses if c.clause_type == ClauseType.PAYMENT_TERMS]
        if payment_clauses:
            financial_terms['payment_terms'] = payment_clauses[0].summary
        
        return financial_terms
    
    def _calculate_risk_score(self, clauses: List[ContractClause], 
                            terms: List[ContractTerm]) -> float:
        """Calculate overall contract risk score (0-100)"""
        if not clauses:
            return 50.0  # Medium risk if no clauses identified
        
        risk_weights = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 4,
            RiskLevel.CRITICAL: 8
        }
        
        total_weighted_risk = sum(risk_weights[clause.risk_level] for clause in clauses)
        max_possible_risk = len(clauses) * risk_weights[RiskLevel.CRITICAL]
        
        # Normalize to 0-100 scale
        risk_score = (total_weighted_risk / max_possible_risk) * 100
        
        # Adjust based on missing critical clauses
        critical_clause_types = {
            ClauseType.TERMINATION, ClauseType.LIABILITY_LIMITATION,
            ClauseType.INDEMNIFICATION, ClauseType.GOVERNING_LAW
        }
        
        existing_types = {clause.clause_type for clause in clauses}
        missing_critical = critical_clause_types - existing_types
        
        # Increase risk for each missing critical clause
        risk_score += len(missing_critical) * 10
        
        return min(risk_score, 100.0)
    
    def _identify_compliance_issues(self, clauses: List[ContractClause], 
                                  contract_type: ContractType) -> List[str]:
        """Identify potential compliance issues"""
        issues = []
        
        clause_types = {clause.clause_type for clause in clauses}
        
        # Check for required clauses by contract type
        required_clauses = {
            ContractType.EMPLOYMENT_CONTRACT: [
                ClauseType.TERMINATION, ClauseType.CONFIDENTIALITY
            ],
            ContractType.SERVICE_AGREEMENT: [
                ClauseType.TERMINATION, ClauseType.LIABILITY_LIMITATION,
                ClauseType.PAYMENT_TERMS
            ],
            ContractType.NDA: [
                ClauseType.CONFIDENTIALITY, ClauseType.GOVERNING_LAW
            ]
        }
        
        if contract_type in required_clauses:
            missing = set(required_clauses[contract_type]) - clause_types
            for missing_clause in missing:
                issues.append(f"Missing {missing_clause.value.replace('_', ' ')} clause")
        
        # Check for problematic clause combinations
        if ClauseType.LIABILITY_LIMITATION not in clause_types:
            issues.append("No liability limitation clause found - potential unlimited exposure")
        
        # Check for automatic renewal without termination rights
        auto_renewal_found = False
        termination_convenience = False
        
        for clause in clauses:
            if 'automatic' in clause.text.lower() and 'renewal' in clause.text.lower():
                auto_renewal_found = True
            if clause.clause_type == ClauseType.TERMINATION and 'convenience' in clause.text.lower():
                termination_convenience = True
        
        if auto_renewal_found and not termination_convenience:
            issues.append("Automatic renewal clause without termination for convenience")
        
        return issues
    
    def _generate_recommendations(self, clauses: List[ContractClause], 
                                risk_score: float, compliance_issues: List[str]) -> List[str]:
        """Generate recommendations for contract improvements"""
        recommendations = []
        
        if risk_score > 75:
            recommendations.append("High-risk contract - recommend comprehensive legal review")
        elif risk_score > 50:
            recommendations.append("Medium-risk contract - consider legal consultation")
        
        if compliance_issues:
            recommendations.append("Address identified compliance issues before execution")
        
        # Clause-specific recommendations
        clause_types = {clause.clause_type for clause in clauses}
        
        critical_risks = [c for c in clauses if c.risk_level == RiskLevel.CRITICAL]
        if critical_risks:
            recommendations.append("Review and negotiate critical risk clauses")
        
        if ClauseType.FORCE_MAJEURE not in clause_types:
            recommendations.append("Consider adding force majeure clause for risk protection")
        
        if ClauseType.DISPUTE_RESOLUTION not in clause_types:
            recommendations.append("Add dispute resolution clause to avoid litigation costs")
        
        # Payment terms recommendations
        payment_clauses = [c for c in clauses if c.clause_type == ClauseType.PAYMENT_TERMS]
        if not payment_clauses:
            recommendations.append("Clearly define payment terms and schedules")
        
        return recommendations


class ContractTypeClassifier:
    """Classify contract types based on content analysis"""
    
    def __init__(self):
        self.type_indicators = {
            ContractType.EMPLOYMENT_CONTRACT: [
                'employee', 'employer', 'employment', 'salary', 'wages',
                'benefits', 'vacation', 'termination of employment', 'job duties'
            ],
            ContractType.SERVICE_AGREEMENT: [
                'services', 'service provider', 'deliverables', 'statement of work',
                'professional services', 'consulting services', 'performance'
            ],
            ContractType.NDA: [
                'confidential information', 'non-disclosure', 'proprietary information',
                'trade secrets', 'confidentiality agreement', 'disclosure'
            ],
            ContractType.LEASE_AGREEMENT: [
                'lease', 'rent', 'tenant', 'landlord', 'premises',
                'monthly rent', 'security deposit', 'lease term'
            ],
            ContractType.PURCHASE_AGREEMENT: [
                'purchase', 'buyer', 'seller', 'goods', 'merchandise',
                'purchase price', 'delivery', 'title transfer'
            ],
            ContractType.LICENSING_AGREEMENT: [
                'license', 'licensor', 'licensee', 'intellectual property',
                'patent', 'trademark', 'royalty', 'license fee'
            ],
            ContractType.VENDOR_AGREEMENT: [
                'vendor', 'supplier', 'supply', 'procurement',
                'purchase order', 'vendor services', 'supplies'
            ]
        }
    
    def classify_contract(self, contract_text: str) -> ContractType:
        """Classify the type of contract"""
        text_lower = contract_text.lower()
        
        scores = {}
        
        for contract_type, indicators in self.type_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score > 0:
                scores[contract_type] = score
        
        if not scores:
            return ContractType.OTHER
        
        # Return the type with the highest score
        return max(scores.items(), key=lambda x: x[1])[0]