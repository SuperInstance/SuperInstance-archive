"""
Legal Citation Detection System
Comprehensive detection and parsing of legal citations in documents.
"""
import re
import datetime
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json


class CitationType(Enum):
    """Types of legal citations"""
    CASE_LAW = "case_law"
    STATUTE = "statute"
    REGULATION = "regulation"
    CONSTITUTIONAL = "constitutional"
    RULE = "rule"
    TREATY = "treaty"
    LAW_REVIEW = "law_review"
    SECONDARY_SOURCE = "secondary_source"
    COURT_FILING = "court_filing"
    UNKNOWN = "unknown"


class Jurisdiction(Enum):
    """Legal jurisdictions"""
    FEDERAL = "federal"
    STATE = "state"
    INTERNATIONAL = "international"
    LOCAL = "local"
    TRIBAL = "tribal"
    UNKNOWN = "unknown"


class CourtLevel(Enum):
    """Court hierarchy levels"""
    SUPREME_COURT = "supreme_court"
    APPELLATE_COURT = "appellate_court"
    DISTRICT_COURT = "district_court"
    TRIAL_COURT = "trial_court"
    SPECIALTY_COURT = "specialty_court"
    ADMINISTRATIVE = "administrative"
    UNKNOWN = "unknown"


@dataclass
class LegalCitation:
    """Individual legal citation"""
    raw_text: str
    citation_type: CitationType
    start_position: int
    end_position: int
    confidence: float
    case_name: Optional[str] = None
    volume: Optional[str] = None
    reporter: Optional[str] = None
    page: Optional[str] = None
    year: Optional[int] = None
    court: Optional[str] = None
    jurisdiction: Optional[Jurisdiction] = None
    court_level: Optional[CourtLevel] = None
    statute_title: Optional[str] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    parallel_citations: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CitationContext:
    """Context surrounding a citation"""
    citation: LegalCitation
    preceding_text: str
    following_text: str
    paragraph_text: str
    context_relevance: float
    authority_type: str  # "primary", "secondary", "persuasive", "binding"
    citation_purpose: str  # "support", "distinguish", "overrule", "cite"


class CaseLawCitationParser:
    """Parser for case law citations"""
    
    def __init__(self):
        # Federal court reporters
        self.federal_reporters = {
            'U.S.': {'name': 'United States Reports', 'court': 'Supreme Court'},
            'S. Ct.': {'name': 'Supreme Court Reporter', 'court': 'Supreme Court'},
            'L. Ed.': {'name': 'Lawyers Edition', 'court': 'Supreme Court'},
            'F.': {'name': 'Federal Reporter', 'court': 'Circuit Court'},
            'F.2d': {'name': 'Federal Reporter 2nd', 'court': 'Circuit Court'},
            'F.3d': {'name': 'Federal Reporter 3rd', 'court': 'Circuit Court'},
            'F.4th': {'name': 'Federal Reporter 4th', 'court': 'Circuit Court'},
            'F. Supp.': {'name': 'Federal Supplement', 'court': 'District Court'},
            'F. Supp. 2d': {'name': 'Federal Supplement 2nd', 'court': 'District Court'},
            'F. Supp. 3d': {'name': 'Federal Supplement 3rd', 'court': 'District Court'},
        }
        
        # State reporters
        self.state_reporters = {
            'Cal.': {'name': 'California Reports', 'jurisdiction': 'California'},
            'Cal. 2d': {'name': 'California Reports 2nd', 'jurisdiction': 'California'},
            'Cal. 3d': {'name': 'California Reports 3rd', 'jurisdiction': 'California'},
            'Cal. 4th': {'name': 'California Reports 4th', 'jurisdiction': 'California'},
            'Cal. 5th': {'name': 'California Reports 5th', 'jurisdiction': 'California'},
            'N.Y.': {'name': 'New York Reports', 'jurisdiction': 'New York'},
            'N.Y.2d': {'name': 'New York Reports 2nd', 'jurisdiction': 'New York'},
            'Tex.': {'name': 'Texas Reports', 'jurisdiction': 'Texas'},
            'Ill.': {'name': 'Illinois Reports', 'jurisdiction': 'Illinois'},
            'Pa.': {'name': 'Pennsylvania Reports', 'jurisdiction': 'Pennsylvania'},
        }
        
        # Regional reporters
        self.regional_reporters = {
            'A.': {'name': 'Atlantic Reporter', 'region': 'Atlantic'},
            'A.2d': {'name': 'Atlantic Reporter 2nd', 'region': 'Atlantic'},
            'A.3d': {'name': 'Atlantic Reporter 3rd', 'region': 'Atlantic'},
            'P.': {'name': 'Pacific Reporter', 'region': 'Pacific'},
            'P.2d': {'name': 'Pacific Reporter 2nd', 'region': 'Pacific'},
            'P.3d': {'name': 'Pacific Reporter 3rd', 'region': 'Pacific'},
            'N.E.': {'name': 'Northeastern Reporter', 'region': 'Northeastern'},
            'N.E.2d': {'name': 'Northeastern Reporter 2nd', 'region': 'Northeastern'},
            'N.E.3d': {'name': 'Northeastern Reporter 3rd', 'region': 'Northeastern'},
            'N.W.': {'name': 'Northwestern Reporter', 'region': 'Northwestern'},
            'N.W.2d': {'name': 'Northwestern Reporter 2nd', 'region': 'Northwestern'},
            'S.E.': {'name': 'Southeastern Reporter', 'region': 'Southeastern'},
            'S.E.2d': {'name': 'Southeastern Reporter 2nd', 'region': 'Southeastern'},
            'S.W.': {'name': 'Southwestern Reporter', 'region': 'Southwestern'},
            'S.W.2d': {'name': 'Southwestern Reporter 2nd', 'region': 'Southwestern'},
            'S.W.3d': {'name': 'Southwestern Reporter 3rd', 'region': 'Southwestern'},
            'So.': {'name': 'Southern Reporter', 'region': 'Southern'},
            'So. 2d': {'name': 'Southern Reporter 2nd', 'region': 'Southern'},
            'So. 3d': {'name': 'Southern Reporter 3rd', 'region': 'Southern'},
        }
        
        self.all_reporters = {
            **self.federal_reporters,
            **self.state_reporters,
            **self.regional_reporters
        }
        
        # Citation patterns
        self.case_citation_patterns = self._build_case_patterns()
    
    def _build_case_patterns(self) -> List[str]:
        """Build regex patterns for case citations"""
        # Create reporter pattern from all known reporters
        reporter_pattern = '|'.join(re.escape(r) for r in self.all_reporters.keys())
        
        patterns = [
            # Standard case citation: Volume Reporter Page (Year)
            rf'(\d+)\s+({reporter_pattern})\s+(\d+)(?:,\s*(\d+))?\s*\((\d{{4}})\)',
            
            # Case citation with case name
            rf'([A-Za-z][A-Za-z\s&.,-]+)\s*v\.\s*([A-Za-z][A-Za-z\s&.,-]+),\s*(\d+)\s+({reporter_pattern})\s+(\d+)(?:,\s*(\d+))?\s*\((\d{{4}})\)',
            
            # Parallel citation format
            rf'(\d+)\s+({reporter_pattern})\s+(\d+)(?:,\s*(\d+))?,\s*(\d+)\s+({reporter_pattern})\s+(\d+)(?:,\s*(\d+))?\s*\((\d{{4}})\)',
            
            # Short form citations
            rf'(\d+)\s+({reporter_pattern})\s+at\s+(\d+)',
            
            # Id. citations with pincites
            r'[Ii]d\.\s+at\s+(\d+)(?:-(\d+))?',
            
            # Supra citations
            r'([A-Za-z][A-Za-z\s&.,-]+),?\s+supra\s+note\s+(\d+)(?:,\s+at\s+(\d+))?'
        ]
        
        return patterns
    
    def parse_case_citation(self, text: str, start_pos: int = 0) -> List[LegalCitation]:
        """Parse case law citations from text"""
        citations = []
        
        for pattern in self.case_citation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                citation = self._create_case_citation(match, start_pos, text)
                if citation:
                    citations.append(citation)
        
        return self._deduplicate_citations(citations)
    
    def _create_case_citation(self, match: re.Match, start_pos: int, full_text: str) -> Optional[LegalCitation]:
        """Create citation object from regex match"""
        groups = match.groups()
        raw_text = match.group(0)
        
        # Determine citation format based on groups
        if len(groups) >= 5 and groups[1] in self.all_reporters:
            # Standard format: Volume Reporter Page (Year)
            volume = groups[0]
            reporter = groups[1]
            page = groups[2]
            year = int(groups[4]) if groups[4] else None
            
            jurisdiction = self._determine_jurisdiction(reporter)
            court_level = self._determine_court_level(reporter)
            
            return LegalCitation(
                raw_text=raw_text,
                citation_type=CitationType.CASE_LAW,
                start_position=start_pos + match.start(),
                end_position=start_pos + match.end(),
                confidence=0.9,
                volume=volume,
                reporter=reporter,
                page=page,
                year=year,
                jurisdiction=jurisdiction,
                court_level=court_level,
                metadata={'reporter_info': self.all_reporters.get(reporter, {})}
            )
        
        elif len(groups) >= 7 and groups[6] in self.all_reporters:
            # Format with case name
            plaintiff = groups[0]
            defendant = groups[1]
            volume = groups[2]
            reporter = groups[3]
            page = groups[4]
            year = int(groups[6]) if groups[6] else None
            
            case_name = f"{plaintiff.strip()} v. {defendant.strip()}"
            
            jurisdiction = self._determine_jurisdiction(reporter)
            court_level = self._determine_court_level(reporter)
            
            return LegalCitation(
                raw_text=raw_text,
                citation_type=CitationType.CASE_LAW,
                start_position=start_pos + match.start(),
                end_position=start_pos + match.end(),
                confidence=0.95,
                case_name=case_name,
                volume=volume,
                reporter=reporter,
                page=page,
                year=year,
                jurisdiction=jurisdiction,
                court_level=court_level,
                metadata={'reporter_info': self.all_reporters.get(reporter, {})}
            )
        
        return None
    
    def _determine_jurisdiction(self, reporter: str) -> Jurisdiction:
        """Determine jurisdiction from reporter"""
        if reporter in self.federal_reporters:
            return Jurisdiction.FEDERAL
        elif reporter in self.state_reporters:
            return Jurisdiction.STATE
        elif reporter in self.regional_reporters:
            return Jurisdiction.STATE  # Regional reporters cover state cases
        else:
            return Jurisdiction.UNKNOWN
    
    def _determine_court_level(self, reporter: str) -> CourtLevel:
        """Determine court level from reporter"""
        if reporter in ['U.S.', 'S. Ct.', 'L. Ed.']:
            return CourtLevel.SUPREME_COURT
        elif reporter.startswith('F.') and not 'Supp' in reporter:
            return CourtLevel.APPELLATE_COURT
        elif 'Supp' in reporter:
            return CourtLevel.DISTRICT_COURT
        else:
            return CourtLevel.UNKNOWN
    
    def _deduplicate_citations(self, citations: List[LegalCitation]) -> List[LegalCitation]:
        """Remove duplicate citations"""
        seen = set()
        unique_citations = []
        
        for citation in citations:
            # Create a key based on volume, reporter, page
            key = (citation.volume, citation.reporter, citation.page, citation.year)
            
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)
        
        return unique_citations


class StatuteCitationParser:
    """Parser for statutory citations"""
    
    def __init__(self):
        # Federal code patterns
        self.federal_codes = {
            'U.S.C.': 'United States Code',
            'U.S.C.A.': 'United States Code Annotated',
            'U.S.C.S.': 'United States Code Service',
            'C.F.R.': 'Code of Federal Regulations',
            'Fed. Reg.': 'Federal Register',
            'Pub. L.': 'Public Law',
            'Stat.': 'United States Statutes at Large'
        }
        
        # State code patterns
        self.state_codes = {
            'Cal. Code': 'California Code',
            'Cal. Gov. Code': 'California Government Code',
            'Cal. Civ. Code': 'California Civil Code',
            'N.Y. Law': 'New York Law',
            'Tex. Code': 'Texas Code',
            'Fla. Stat.': 'Florida Statutes',
            'Ill. Comp. Stat.': 'Illinois Compiled Statutes'
        }
        
        self.all_codes = {**self.federal_codes, **self.state_codes}
        
        # Build patterns
        self.statute_patterns = self._build_statute_patterns()
    
    def _build_statute_patterns(self) -> List[str]:
        """Build regex patterns for statutory citations"""
        code_pattern = '|'.join(re.escape(c) for c in self.all_codes.keys())
        
        patterns = [
            # Standard format: Title Code § Section (Year)
            rf'(\d+)\s+({code_pattern})\s+§\s*(\d+(?:\.\d+)*(?:\([a-z]+\))*)\s*\((\d{{4}})\)',
            
            # Format without year
            rf'(\d+)\s+({code_pattern})\s+§\s*(\d+(?:\.\d+)*(?:\([a-z]+\))*)',
            
            # Section-first format: § Section of Title Code
            rf'§\s*(\d+(?:\.\d+)*(?:\([a-z]+\))*)\s+of\s+(\d+)\s+({code_pattern})',
            
            # Code section format: Code § Section
            rf'({code_pattern})\s+§\s*(\d+(?:\.\d+)*(?:\([a-z]+\))*)',
            
            # Regulation format: Title C.F.R. § Section
            rf'(\d+)\s+C\.F\.R\.\s+§\s*(\d+(?:\.\d+)*)',
            
            # Public Law format
            rf'Pub\.\s*L\.\s*No\.\s*(\d+-\d+),\s*(\d+)\s+Stat\.\s*(\d+)\s*\((\d{{4}})\)',
        ]
        
        return patterns
    
    def parse_statute_citation(self, text: str, start_pos: int = 0) -> List[LegalCitation]:
        """Parse statutory citations from text"""
        citations = []
        
        for pattern in self.statute_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                citation = self._create_statute_citation(match, start_pos)
                if citation:
                    citations.append(citation)
        
        return citations
    
    def _create_statute_citation(self, match: re.Match, start_pos: int) -> Optional[LegalCitation]:
        """Create statute citation from regex match"""
        groups = match.groups()
        raw_text = match.group(0)
        
        if len(groups) >= 3:
            # Standard format parsing
            if groups[1] in self.all_codes:
                title = groups[0]
                code = groups[1]
                section = groups[2]
                year = int(groups[3]) if len(groups) > 3 and groups[3] else None
                
                jurisdiction = Jurisdiction.FEDERAL if code in self.federal_codes else Jurisdiction.STATE
                
                return LegalCitation(
                    raw_text=raw_text,
                    citation_type=CitationType.STATUTE,
                    start_position=start_pos + match.start(),
                    end_position=start_pos + match.end(),
                    confidence=0.9,
                    statute_title=title,
                    section=section,
                    year=year,
                    jurisdiction=jurisdiction,
                    metadata={
                        'code': code,
                        'code_name': self.all_codes.get(code, ''),
                    }
                )
        
        return None


class RegulationCitationParser:
    """Parser for regulatory citations"""
    
    def __init__(self):
        self.regulation_patterns = [
            # CFR citations: Title C.F.R. § Section
            r'(\d+)\s+C\.F\.R\.\s+§?\s*(\d+(?:\.\d+)*)',
            
            # Federal Register citations
            r'(\d+)\s+Fed\.\s+Reg\.\s+(\d+(?:,\s*\d+)*)\s*\(([A-Za-z]+\.?\s+\d+,\s+\d{4})\)',
            
            # Agency regulations
            r'(\d+)\s+([A-Z]{2,})\s+(\d+(?:\.\d+)*)',
        ]
    
    def parse_regulation_citation(self, text: str, start_pos: int = 0) -> List[LegalCitation]:
        """Parse regulatory citations from text"""
        citations = []
        
        for pattern in self.regulation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                groups = match.groups()
                raw_text = match.group(0)
                
                if 'C.F.R.' in raw_text:
                    title = groups[0]
                    section = groups[1]
                    
                    citation = LegalCitation(
                        raw_text=raw_text,
                        citation_type=CitationType.REGULATION,
                        start_position=start_pos + match.start(),
                        end_position=start_pos + match.end(),
                        confidence=0.85,
                        statute_title=title,
                        section=section,
                        jurisdiction=Jurisdiction.FEDERAL,
                        metadata={'regulation_type': 'CFR'}
                    )
                    citations.append(citation)
                
                elif 'Fed. Reg.' in raw_text:
                    volume = groups[0]
                    page = groups[1]
                    date = groups[2] if len(groups) > 2 else None
                    
                    citation = LegalCitation(
                        raw_text=raw_text,
                        citation_type=CitationType.REGULATION,
                        start_position=start_pos + match.start(),
                        end_position=start_pos + match.end(),
                        confidence=0.85,
                        volume=volume,
                        page=page,
                        jurisdiction=Jurisdiction.FEDERAL,
                        metadata={'regulation_type': 'Federal Register', 'date': date}
                    )
                    citations.append(citation)
        
        return citations


class ConstitutionalCitationParser:
    """Parser for constitutional citations"""
    
    def __init__(self):
        self.constitutional_patterns = [
            # U.S. Constitution
            r'U\.S\.\s+Const\.\s+art\.\s+([IVX]+),?\s*§\s*(\d+)',
            r'U\.S\.\s+Const\.\s+amend\.\s+([IVX]+|\d+)',
            
            # State constitutions
            r'([A-Za-z]+)\s+Const\.\s+art\.\s+([IVX]+),?\s*§\s*(\d+)',
            r'([A-Za-z]+)\s+Const\.\s+amend\.\s+([IVX]+|\d+)',
        ]
    
    def parse_constitutional_citation(self, text: str, start_pos: int = 0) -> List[LegalCitation]:
        """Parse constitutional citations from text"""
        citations = []
        
        for pattern in self.constitutional_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                groups = match.groups()
                raw_text = match.group(0)
                
                if raw_text.startswith('U.S.'):
                    jurisdiction = Jurisdiction.FEDERAL
                    if 'art.' in raw_text:
                        article = groups[0]
                        section = groups[1] if len(groups) > 1 else None
                        metadata = {'article': article, 'section': section}
                    else:
                        amendment = groups[0]
                        metadata = {'amendment': amendment}
                else:
                    jurisdiction = Jurisdiction.STATE
                    state = groups[0]
                    metadata = {'state': state}
                
                citation = LegalCitation(
                    raw_text=raw_text,
                    citation_type=CitationType.CONSTITUTIONAL,
                    start_position=start_pos + match.start(),
                    end_position=start_pos + match.end(),
                    confidence=0.9,
                    jurisdiction=jurisdiction,
                    metadata=metadata
                )
                citations.append(citation)
        
        return citations


class LegalCitationDetector:
    """Main legal citation detection system"""
    
    def __init__(self):
        self.case_parser = CaseLawCitationParser()
        self.statute_parser = StatuteCitationParser()
        self.regulation_parser = RegulationCitationParser()
        self.constitutional_parser = ConstitutionalCitationParser()
        
        # Secondary source patterns
        self.secondary_patterns = [
            # Law review articles
            r'([A-Za-z][A-Za-z\s&.,-]+),\s+([A-Za-z][A-Za-z\s&.,-]+),\s+(\d+)\s+([A-Za-z.]+\s+L\.\s+Rev\.)\s+(\d+)\s*\((\d{4})\)',
            
            # Legal treatises
            r'(\d+[A-Za-z]*)\s+([A-Za-z][A-Za-z\s&.,-]+)\s+§\s*(\d+(?:\.\d+)*)\s*\((\d+)(?:st|nd|rd|th)?\s+ed\.\s+(\d{4})\)',
            
            # Legal encyclopedias
            r'(\d+[A-Za-z]*)\s+(Am\.\s+Jur\.\s+2d|C\.J\.S\.)\s+([A-Za-z\s]+)\s+§\s*(\d+)\s*\((\d{4})\)',
        ]
    
    def detect_citations(self, text: str, include_context: bool = True) -> List[LegalCitation]:
        """Detect all types of legal citations in text"""
        all_citations = []
        
        # Parse each type of citation
        case_citations = self.case_parser.parse_case_citation(text)
        statute_citations = self.statute_parser.parse_statute_citation(text)
        regulation_citations = self.regulation_parser.parse_regulation_citation(text)
        constitutional_citations = self.constitutional_parser.parse_constitutional_citation(text)
        secondary_citations = self._parse_secondary_sources(text)
        
        all_citations.extend(case_citations)
        all_citations.extend(statute_citations)
        all_citations.extend(regulation_citations)
        all_citations.extend(constitutional_citations)
        all_citations.extend(secondary_citations)
        
        # Sort by position in text
        all_citations.sort(key=lambda c: c.start_position)
        
        # Remove overlapping citations (keep highest confidence)
        deduplicated = self._remove_overlapping_citations(all_citations)
        
        if include_context:
            return [self._add_citation_context(citation, text) for citation in deduplicated]
        
        return deduplicated
    
    def _parse_secondary_sources(self, text: str) -> List[LegalCitation]:
        """Parse secondary source citations"""
        citations = []
        
        for pattern in self.secondary_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                raw_text = match.group(0)
                groups = match.groups()
                
                # Determine citation type based on pattern
                if 'L. Rev.' in raw_text or 'Law Review' in raw_text:
                    citation_type = CitationType.LAW_REVIEW
                    confidence = 0.9
                else:
                    citation_type = CitationType.SECONDARY_SOURCE
                    confidence = 0.8
                
                citation = LegalCitation(
                    raw_text=raw_text,
                    citation_type=citation_type,
                    start_position=match.start(),
                    end_position=match.end(),
                    confidence=confidence,
                    metadata={'parsed_groups': groups}
                )
                citations.append(citation)
        
        return citations
    
    def _remove_overlapping_citations(self, citations: List[LegalCitation]) -> List[LegalCitation]:
        """Remove overlapping citations, keeping highest confidence"""
        if not citations:
            return citations
        
        # Sort by start position
        sorted_citations = sorted(citations, key=lambda c: c.start_position)
        
        filtered = []
        
        for citation in sorted_citations:
            # Check for overlap with existing citations
            overlaps = False
            
            for existing in filtered:
                if (citation.start_position < existing.end_position and 
                    citation.end_position > existing.start_position):
                    # There's overlap
                    if citation.confidence > existing.confidence:
                        filtered.remove(existing)
                    else:
                        overlaps = True
                    break
            
            if not overlaps:
                filtered.append(citation)
        
        return filtered
    
    def _add_citation_context(self, citation: LegalCitation, full_text: str) -> CitationContext:
        """Add context information to citation"""
        # Extract surrounding text
        context_window = 200
        start = max(0, citation.start_position - context_window)
        end = min(len(full_text), citation.end_position + context_window)
        
        preceding_text = full_text[start:citation.start_position]
        following_text = full_text[citation.end_position:end]
        
        # Find paragraph boundaries
        para_start = full_text.rfind('\n\n', 0, citation.start_position)
        para_end = full_text.find('\n\n', citation.end_position)
        
        if para_start == -1:
            para_start = 0
        else:
            para_start += 2
        
        if para_end == -1:
            para_end = len(full_text)
        
        paragraph_text = full_text[para_start:para_end]
        
        # Analyze context
        authority_type = self._determine_authority_type(citation, preceding_text, following_text)
        citation_purpose = self._determine_citation_purpose(preceding_text, following_text)
        relevance = self._calculate_context_relevance(citation, paragraph_text)
        
        return CitationContext(
            citation=citation,
            preceding_text=preceding_text,
            following_text=following_text,
            paragraph_text=paragraph_text,
            context_relevance=relevance,
            authority_type=authority_type,
            citation_purpose=citation_purpose
        )
    
    def _determine_authority_type(self, citation: LegalCitation, 
                                 preceding: str, following: str) -> str:
        """Determine if citation is binding, persuasive, primary, or secondary authority"""
        if citation.citation_type in [CitationType.CASE_LAW, CitationType.STATUTE, 
                                     CitationType.CONSTITUTIONAL, CitationType.REGULATION]:
            # Primary authority - check if binding or persuasive
            if citation.jurisdiction == Jurisdiction.FEDERAL:
                return "binding" if citation.court_level == CourtLevel.SUPREME_COURT else "primary"
            else:
                return "primary"
        else:
            return "secondary"
    
    def _determine_citation_purpose(self, preceding: str, following: str) -> str:
        """Determine the purpose of the citation in context"""
        context = (preceding + " " + following).lower()
        
        if any(phrase in context for phrase in ['see', 'see also', 'accord']):
            return "support"
        elif any(phrase in context for phrase in ['but see', 'contra', 'compare']):
            return "distinguish"
        elif any(phrase in context for phrase in ['overruled', 'reversed', 'abrogated']):
            return "overrule"
        else:
            return "cite"
    
    def _calculate_context_relevance(self, citation: LegalCitation, paragraph: str) -> float:
        """Calculate how relevant the citation is to its context"""
        # Simple relevance scoring based on context indicators
        relevance_indicators = [
            'holding', 'ruled', 'decided', 'established', 'precedent',
            'statute', 'law', 'regulation', 'constitutional', 'court'
        ]
        
        para_lower = paragraph.lower()
        relevance_score = sum(1 for indicator in relevance_indicators if indicator in para_lower)
        
        # Normalize to 0-1 scale
        max_score = len(relevance_indicators)
        return min(relevance_score / max_score, 1.0)
    
    def analyze_citation_network(self, citations: List[LegalCitation]) -> Dict[str, Any]:
        """Analyze the network of citations in a document"""
        analysis = {
            'total_citations': len(citations),
            'by_type': {},
            'by_jurisdiction': {},
            'by_court_level': {},
            'by_decade': {},
            'most_cited_sources': {},
            'authority_distribution': {},
        }
        
        for citation in citations:
            # Count by type
            citation_type = citation.citation_type.value
            analysis['by_type'][citation_type] = analysis['by_type'].get(citation_type, 0) + 1
            
            # Count by jurisdiction
            if citation.jurisdiction:
                jurisdiction = citation.jurisdiction.value
                analysis['by_jurisdiction'][jurisdiction] = analysis['by_jurisdiction'].get(jurisdiction, 0) + 1
            
            # Count by court level
            if citation.court_level:
                court_level = citation.court_level.value
                analysis['by_court_level'][court_level] = analysis['by_court_level'].get(court_level, 0) + 1
            
            # Count by decade
            if citation.year:
                decade = (citation.year // 10) * 10
                analysis['by_decade'][str(decade)] = analysis['by_decade'].get(str(decade), 0) + 1
            
            # Track most cited sources (simplified)
            if citation.reporter:
                analysis['most_cited_sources'][citation.reporter] = analysis['most_cited_sources'].get(citation.reporter, 0) + 1
        
        return analysis
    
    def validate_citations(self, citations: List[LegalCitation]) -> List[Dict[str, Any]]:
        """Validate citation format and completeness"""
        validation_results = []
        
        for citation in citations:
            issues = []
            
            # Check for required components based on citation type
            if citation.citation_type == CitationType.CASE_LAW:
                if not citation.volume:
                    issues.append("Missing volume number")
                if not citation.reporter:
                    issues.append("Missing reporter")
                if not citation.page:
                    issues.append("Missing page number")
                if not citation.year:
                    issues.append("Missing year")
            
            elif citation.citation_type == CitationType.STATUTE:
                if not citation.statute_title:
                    issues.append("Missing title")
                if not citation.section:
                    issues.append("Missing section")
            
            # Check citation format
            if citation.confidence < 0.7:
                issues.append("Low confidence in citation parsing")
            
            validation_results.append({
                'citation': citation,
                'issues': issues,
                'is_valid': len(issues) == 0
            })
        
        return validation_results
    
    def generate_citation_report(self, text: str) -> Dict[str, Any]:
        """Generate comprehensive citation analysis report"""
        citations = self.detect_citations(text, include_context=True)
        
        # Extract just the citations for network analysis
        citation_objects = [ctx.citation for ctx in citations]
        
        network_analysis = self.analyze_citation_network(citation_objects)
        validation_results = self.validate_citations(citation_objects)
        
        return {
            'document_summary': {
                'total_citations': len(citations),
                'valid_citations': sum(1 for r in validation_results if r['is_valid']),
                'citation_density': len(citations) / max(len(text.split()), 1),  # citations per word
            },
            'citations': [asdict(ctx) for ctx in citations],
            'network_analysis': network_analysis,
            'validation_summary': {
                'total_validated': len(validation_results),
                'valid_count': sum(1 for r in validation_results if r['is_valid']),
                'invalid_count': sum(1 for r in validation_results if not r['is_valid']),
                'common_issues': self._get_common_issues(validation_results)
            },
            'generated_at': datetime.datetime.utcnow().isoformat()
        }
    
    def _get_common_issues(self, validation_results: List[Dict[str, Any]]) -> List[str]:
        """Get most common citation validation issues"""
        issue_counts = {}
        
        for result in validation_results:
            for issue in result['issues']:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Return top 5 most common issues
        return sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]