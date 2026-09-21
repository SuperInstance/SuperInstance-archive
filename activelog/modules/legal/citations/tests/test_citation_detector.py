"""
Tests for Legal Citation Detection System
"""
import unittest
from unittest.mock import Mock, patch
from ..src.citation_detector import (
    LegalCitationDetector, CaseLawCitationParser, StatuteCitationParser,
    RegulationCitationParser, ConstitutionalCitationParser,
    CitationType, Jurisdiction, CourtLevel, LegalCitation
)


class TestCaseLawCitationParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = CaseLawCitationParser()
    
    def test_parse_supreme_court_citation(self):
        """Test parsing Supreme Court citations"""
        text = "The Court held in Brown v. Board of Education, 347 U.S. 483 (1954) that separate educational facilities are inherently unequal."
        
        citations = self.parser.parse_case_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.citation_type, CitationType.CASE_LAW)
        self.assertEqual(citation.case_name, "Brown v. Board of Education")
        self.assertEqual(citation.volume, "347")
        self.assertEqual(citation.reporter, "U.S.")
        self.assertEqual(citation.page, "483")
        self.assertEqual(citation.year, 1954)
        self.assertEqual(citation.jurisdiction, Jurisdiction.FEDERAL)
        self.assertEqual(citation.court_level, CourtLevel.SUPREME_COURT)
    
    def test_parse_circuit_court_citation(self):
        """Test parsing Circuit Court citations"""
        text = "The circuit court decided in Smith v. Jones, 123 F.3d 456 (9th Cir. 2000)."
        
        citations = self.parser.parse_case_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.reporter, "F.3d")
        self.assertEqual(citation.jurisdiction, Jurisdiction.FEDERAL)
        self.assertEqual(citation.court_level, CourtLevel.APPELLATE_COURT)
    
    def test_parse_district_court_citation(self):
        """Test parsing District Court citations"""
        text = "As noted in Johnson v. Wilson, 789 F. Supp. 2d 123 (D.D.C. 2010)."
        
        citations = self.parser.parse_case_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.reporter, "F. Supp. 2d")
        self.assertEqual(citation.court_level, CourtLevel.DISTRICT_COURT)
    
    def test_parse_state_court_citation(self):
        """Test parsing state court citations"""
        text = "The California Supreme Court ruled in People v. Anderson, 6 Cal. 3d 628 (1972)."
        
        citations = self.parser.parse_case_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.reporter, "Cal. 3d")
        self.assertEqual(citation.jurisdiction, Jurisdiction.STATE)
    
    def test_parse_regional_reporter_citation(self):
        """Test parsing regional reporter citations"""
        text = "See State v. Davis, 456 P.2d 789 (Wash. 1995)."
        
        citations = self.parser.parse_case_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.reporter, "P.2d")
        self.assertEqual(citation.jurisdiction, Jurisdiction.STATE)
    
    def test_parse_multiple_citations(self):
        """Test parsing multiple citations in text"""
        text = """
        The Supreme Court in Miranda v. Arizona, 384 U.S. 436 (1966), established 
        important precedent. Later, in Dickerson v. United States, 530 U.S. 428 (2000),
        the Court reaffirmed this ruling.
        """
        
        citations = self.parser.parse_case_citation(text)
        
        self.assertEqual(len(citations), 2)
        
        # Check first citation
        self.assertIn("Miranda", citations[0].case_name)
        self.assertEqual(citations[0].year, 1966)
        
        # Check second citation
        self.assertIn("Dickerson", citations[1].case_name)
        self.assertEqual(citations[1].year, 2000)
    
    def test_deduplicate_citations(self):
        """Test deduplication of identical citations"""
        citation1 = LegalCitation(
            raw_text="123 U.S. 456 (1900)",
            citation_type=CitationType.CASE_LAW,
            start_position=0,
            end_position=20,
            confidence=0.9,
            volume="123",
            reporter="U.S.",
            page="456",
            year=1900
        )
        
        citation2 = LegalCitation(
            raw_text="123 U.S. 456 (1900)",
            citation_type=CitationType.CASE_LAW,
            start_position=50,
            end_position=70,
            confidence=0.9,
            volume="123",
            reporter="U.S.",
            page="456",
            year=1900
        )
        
        citations = [citation1, citation2]
        deduplicated = self.parser._deduplicate_citations(citations)
        
        self.assertEqual(len(deduplicated), 1)


class TestStatuteCitationParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = StatuteCitationParser()
    
    def test_parse_usc_citation(self):
        """Test parsing USC citations"""
        text = "Under 42 U.S.C. § 1983 (2018), civil rights violations may be actionable."
        
        citations = self.parser.parse_statute_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.citation_type, CitationType.STATUTE)
        self.assertEqual(citation.statute_title, "42")
        self.assertEqual(citation.section, "1983")
        self.assertEqual(citation.year, 2018)
        self.assertEqual(citation.jurisdiction, Jurisdiction.FEDERAL)
        self.assertIn("U.S.C.", citation.metadata['code'])
    
    def test_parse_cfr_citation(self):
        """Test parsing CFR citations"""
        text = "The regulation at 29 C.F.R. § 1630.2 defines disability."
        
        citations = self.parser.parse_statute_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.statute_title, "29")
        self.assertEqual(citation.section, "1630.2")
        self.assertIn("C.F.R.", citation.metadata['code'])
    
    def test_parse_state_code_citation(self):
        """Test parsing state code citations"""
        text = "California Civil Code § 1542 provides important protections."
        
        citations = self.parser.parse_statute_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.section, "1542")
        self.assertEqual(citation.jurisdiction, Jurisdiction.STATE)
        self.assertIn("Cal. Civ. Code", citation.metadata['code'])
    
    def test_parse_public_law_citation(self):
        """Test parsing Public Law citations"""
        text = "The ADA was enacted as Pub. L. No. 101-336, 104 Stat. 327 (1990)."
        
        citations = self.parser.parse_statute_citation(text)
        
        self.assertGreater(len(citations), 0)
        # Check if any citation captured the public law format
        pub_law_citations = [c for c in citations if 'Pub. L.' in c.raw_text]
        self.assertGreater(len(pub_law_citations), 0)


class TestRegulationCitationParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = RegulationCitationParser()
    
    def test_parse_cfr_regulation(self):
        """Test parsing CFR regulations"""
        text = "The rules are codified at 40 C.F.R. § 122.21."
        
        citations = self.parser.parse_regulation_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.citation_type, CitationType.REGULATION)
        self.assertEqual(citation.statute_title, "40")
        self.assertEqual(citation.section, "122.21")
        self.assertEqual(citation.jurisdiction, Jurisdiction.FEDERAL)
        self.assertEqual(citation.metadata['regulation_type'], 'CFR')
    
    def test_parse_federal_register(self):
        """Test parsing Federal Register citations"""
        text = "The proposed rule appears at 85 Fed. Reg. 12345, 12350 (Mar. 15, 2020)."
        
        citations = self.parser.parse_regulation_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.volume, "85")
        self.assertIn("12345", citation.page)
        self.assertEqual(citation.metadata['regulation_type'], 'Federal Register')
        self.assertIn("Mar. 15, 2020", citation.metadata.get('date', ''))


class TestConstitutionalCitationParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = ConstitutionalCitationParser()
    
    def test_parse_us_constitution_article(self):
        """Test parsing U.S. Constitution article citations"""
        text = "Article I, Section 8 of the Constitution, U.S. Const. art. I, § 8."
        
        citations = self.parser.parse_constitutional_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.citation_type, CitationType.CONSTITUTIONAL)
        self.assertEqual(citation.jurisdiction, Jurisdiction.FEDERAL)
        self.assertEqual(citation.metadata['article'], 'I')
        self.assertEqual(citation.metadata['section'], '8')
    
    def test_parse_us_constitution_amendment(self):
        """Test parsing U.S. Constitution amendment citations"""
        text = "The First Amendment, U.S. Const. amend. I, protects free speech."
        
        citations = self.parser.parse_constitutional_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.jurisdiction, Jurisdiction.FEDERAL)
        self.assertEqual(citation.metadata['amendment'], 'I')
    
    def test_parse_state_constitution(self):
        """Test parsing state constitution citations"""
        text = "Under the California Constitution, Cal. Const. art. IV, § 1."
        
        citations = self.parser.parse_constitutional_citation(text)
        
        self.assertEqual(len(citations), 1)
        citation = citations[0]
        
        self.assertEqual(citation.jurisdiction, Jurisdiction.STATE)
        self.assertIn('state', citation.metadata)


class TestLegalCitationDetector(unittest.TestCase):
    
    def setUp(self):
        self.detector = LegalCitationDetector()
    
    def test_detect_mixed_citations(self):
        """Test detecting various types of citations in single text"""
        text = """
        The Supreme Court in Brown v. Board, 347 U.S. 483 (1954), relied on 
        the Equal Protection Clause, U.S. Const. amend. XIV. Congress later 
        enacted 42 U.S.C. § 2000d to address discrimination. The implementing 
        regulations are found at 34 C.F.R. § 100.3.
        """
        
        citations = self.detector.detect_citations(text, include_context=False)
        
        # Should find case law, constitutional, statute, and regulation citations
        self.assertGreater(len(citations), 3)
        
        citation_types = {c.citation_type for c in citations}
        self.assertIn(CitationType.CASE_LAW, citation_types)
        self.assertIn(CitationType.CONSTITUTIONAL, citation_types)
        self.assertIn(CitationType.STATUTE, citation_types)
        self.assertIn(CitationType.REGULATION, citation_types)
    
    def test_detect_with_context(self):
        """Test citation detection with context analysis"""
        text = """
        The landmark decision in Miranda v. Arizona, 384 U.S. 436 (1966), 
        established the requirement for police to inform suspects of their rights. 
        This holding has been consistently upheld by subsequent courts.
        """
        
        contexts = self.detector.detect_citations(text, include_context=True)
        
        self.assertEqual(len(contexts), 1)
        context = contexts[0]
        
        self.assertIsNotNone(context.preceding_text)
        self.assertIsNotNone(context.following_text)
        self.assertIsNotNone(context.paragraph_text)
        self.assertIn(context.authority_type, ['primary', 'binding'])
        self.assertIn(context.citation_purpose, ['cite', 'support'])
    
    def test_remove_overlapping_citations(self):
        """Test removal of overlapping citations"""
        citation1 = LegalCitation(
            raw_text="Brown v. Board, 347 U.S. 483",
            citation_type=CitationType.CASE_LAW,
            start_position=10,
            end_position=35,
            confidence=0.9
        )
        
        citation2 = LegalCitation(
            raw_text="347 U.S. 483 (1954)",
            citation_type=CitationType.CASE_LAW,
            start_position=25,
            end_position=44,
            confidence=0.8
        )
        
        citations = [citation1, citation2]
        filtered = self.detector._remove_overlapping_citations(citations)
        
        # Should keep the higher confidence citation
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].confidence, 0.9)
    
    def test_analyze_citation_network(self):
        """Test citation network analysis"""
        citations = [
            LegalCitation(
                raw_text="347 U.S. 483 (1954)",
                citation_type=CitationType.CASE_LAW,
                start_position=0, end_position=20,
                confidence=0.9,
                reporter="U.S.",
                year=1954,
                jurisdiction=Jurisdiction.FEDERAL,
                court_level=CourtLevel.SUPREME_COURT
            ),
            LegalCitation(
                raw_text="42 U.S.C. § 1983",
                citation_type=CitationType.STATUTE,
                start_position=30, end_position=46,
                confidence=0.9,
                jurisdiction=Jurisdiction.FEDERAL
            )
        ]
        
        analysis = self.detector.analyze_citation_network(citations)
        
        self.assertEqual(analysis['total_citations'], 2)
        self.assertIn('case_law', analysis['by_type'])
        self.assertIn('statute', analysis['by_type'])
        self.assertIn('federal', analysis['by_jurisdiction'])
        self.assertIn('1950', analysis['by_decade'])
    
    def test_validate_citations(self):
        """Test citation validation"""
        valid_citation = LegalCitation(
            raw_text="347 U.S. 483 (1954)",
            citation_type=CitationType.CASE_LAW,
            start_position=0, end_position=20,
            confidence=0.9,
            volume="347",
            reporter="U.S.",
            page="483",
            year=1954
        )
        
        invalid_citation = LegalCitation(
            raw_text="Some citation",
            citation_type=CitationType.CASE_LAW,
            start_position=0, end_position=13,
            confidence=0.5,
            # Missing required fields
        )
        
        results = self.detector.validate_citations([valid_citation, invalid_citation])
        
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]['is_valid'])
        self.assertFalse(results[1]['is_valid'])
        self.assertGreater(len(results[1]['issues']), 0)
    
    def test_generate_citation_report(self):
        """Test comprehensive citation report generation"""
        text = """
        In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court 
        held that separate educational facilities violate the Equal Protection 
        Clause, U.S. Const. amend. XIV. Congress responded with the Civil Rights 
        Act, codified at 42 U.S.C. § 2000d et seq.
        """
        
        report = self.detector.generate_citation_report(text)
        
        self.assertIn('document_summary', report)
        self.assertIn('citations', report)
        self.assertIn('network_analysis', report)
        self.assertIn('validation_summary', report)
        self.assertIn('generated_at', report)
        
        # Check document summary
        summary = report['document_summary']
        self.assertGreater(summary['total_citations'], 0)
        self.assertGreaterEqual(summary['valid_citations'], 0)
        self.assertIsInstance(summary['citation_density'], float)
    
    def test_determine_authority_type(self):
        """Test authority type determination"""
        # Supreme Court case should be binding
        supreme_court_citation = LegalCitation(
            raw_text="347 U.S. 483",
            citation_type=CitationType.CASE_LAW,
            start_position=0, end_position=13,
            confidence=0.9,
            jurisdiction=Jurisdiction.FEDERAL,
            court_level=CourtLevel.SUPREME_COURT
        )
        
        authority_type = self.detector._determine_authority_type(
            supreme_court_citation, "", ""
        )
        
        self.assertEqual(authority_type, "binding")
        
        # Statute should be primary
        statute_citation = LegalCitation(
            raw_text="42 U.S.C. § 1983",
            citation_type=CitationType.STATUTE,
            start_position=0, end_position=16,
            confidence=0.9,
            jurisdiction=Jurisdiction.FEDERAL
        )
        
        authority_type = self.detector._determine_authority_type(
            statute_citation, "", ""
        )
        
        self.assertEqual(authority_type, "primary")
    
    def test_determine_citation_purpose(self):
        """Test citation purpose determination"""
        # Test support citation
        preceding = "The court noted, see "
        following = " for similar reasoning."
        purpose = self.detector._determine_citation_purpose(preceding, following)
        self.assertEqual(purpose, "support")
        
        # Test distinguishing citation
        preceding = "But see "
        following = " for contrary view."
        purpose = self.detector._determine_citation_purpose(preceding, following)
        self.assertEqual(purpose, "distinguish")


if __name__ == '__main__':
    unittest.main()