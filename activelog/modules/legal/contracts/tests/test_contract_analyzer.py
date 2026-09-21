"""
Tests for Contract Analysis and Extraction Tools
"""
import unittest
import datetime
from unittest.mock import Mock, patch
from ..src.contract_analyzer import (
    ContractAnalyzer, ContractClauseExtractor, ContractEntityExtractor,
    ContractTypeClassifier, ContractType, ClauseType, RiskLevel,
    ContractClause, ContractParty, ContractTerm
)


class TestContractClauseExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = ContractClauseExtractor()
    
    def test_extract_termination_clause(self):
        """Test extraction of termination clauses"""
        text = """
        Either party may terminate this agreement upon thirty (30) days written notice.
        In case of material breach, this contract may be terminated immediately.
        """
        
        clauses = self.extractor.extract_clauses(text)
        
        termination_clauses = [c for c in clauses if c.clause_type == ClauseType.TERMINATION]
        self.assertGreater(len(termination_clauses), 0)
        
        clause = termination_clauses[0]
        self.assertIn('terminate', clause.text.lower())
        self.assertIsInstance(clause.risk_level, RiskLevel)
        self.assertIsNotNone(clause.summary)
    
    def test_extract_payment_terms_clause(self):
        """Test extraction of payment terms clauses"""
        text = """
        Payment of $50,000 is due within 30 days of invoice date.
        Late payments will incur a 1.5% monthly penalty fee.
        """
        
        clauses = self.extractor.extract_clauses(text)
        
        payment_clauses = [c for c in clauses if c.clause_type == ClauseType.PAYMENT_TERMS]
        self.assertGreater(len(payment_clauses), 0)
        
        clause = payment_clauses[0]
        self.assertIn('payment', clause.text.lower())
        self.assertGreater(len(clause.key_terms), 0)
    
    def test_extract_liability_limitation_clause(self):
        """Test extraction of liability limitation clauses"""
        text = """
        Company's total liability under this agreement shall not exceed $100,000.
        Neither party shall be liable for indirect or consequential damages.
        """
        
        clauses = self.extractor.extract_clauses(text)
        
        liability_clauses = [c for c in clauses if c.clause_type == ClauseType.LIABILITY_LIMITATION]
        self.assertGreater(len(liability_clauses), 0)
        
        clause = liability_clauses[0]
        self.assertIn('liabilit', clause.text.lower())
    
    def test_assess_clause_risk(self):
        """Test risk assessment of clauses"""
        high_risk_text = "Company shall indemnify all claims and unlimited liability applies"
        low_risk_text = "Parties will use best efforts and act in good faith"
        
        high_risk = self.extractor._assess_clause_risk(high_risk_text)
        low_risk = self.extractor._assess_clause_risk(low_risk_text)
        
        self.assertIn(high_risk, [RiskLevel.HIGH, RiskLevel.CRITICAL])
        self.assertEqual(low_risk, RiskLevel.LOW)
    
    def test_extract_key_terms(self):
        """Test key term extraction from clauses"""
        text = "Payment of $25,000 is due within 30 days, with 2% late fee applied monthly"
        
        key_terms = self.extractor._extract_key_terms(text, ClauseType.PAYMENT_TERMS)
        
        self.assertGreater(len(key_terms), 0)
        # Should extract monetary amount, days, and percentage
        self.assertTrue(any('$25,000' in term for term in key_terms))
        self.assertTrue(any('30' in term for term in key_terms))
        self.assertTrue(any('2%' in term for term in key_terms))
    
    def test_deduplicate_clauses(self):
        """Test removal of duplicate clauses"""
        clause1 = ContractClause(
            clause_type=ClauseType.TERMINATION,
            text="Either party may terminate",
            start_position=0,
            end_position=25,
            confidence=0.9,
            risk_level=RiskLevel.MEDIUM
        )
        
        clause2 = ContractClause(
            clause_type=ClauseType.TERMINATION,
            text="party may terminate this",
            start_position=7,
            end_position=30,
            confidence=0.7,
            risk_level=RiskLevel.MEDIUM
        )
        
        clauses = [clause1, clause2]
        deduplicated = self.extractor._deduplicate_clauses(clauses)
        
        # Should keep the higher confidence clause
        self.assertEqual(len(deduplicated), 1)
        self.assertEqual(deduplicated[0].confidence, 0.9)


class TestContractEntityExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = ContractEntityExtractor()
    
    def test_extract_parties_companies(self):
        """Test extraction of company parties"""
        text = """
        This agreement is between TechCorp Inc., a Delaware corporation,
        and ServiceProvider LLC, a California limited liability company.
        """
        
        parties = self.extractor.extract_parties(text)
        
        self.assertGreaterEqual(len(parties), 2)
        
        company_names = [p.name for p in parties]
        self.assertIn('TechCorp Inc.', company_names)
        self.assertIn('ServiceProvider LLC', company_names)
        
        # Check entity types
        corp_party = next(p for p in parties if 'TechCorp' in p.name)
        self.assertEqual(corp_party.entity_type, 'corporation')
    
    def test_extract_parties_individuals(self):
        """Test extraction of individual parties"""
        text = """
        This contract is between John Smith, individually, and 
        Dr. Jane Doe, acting in her professional capacity.
        """
        
        parties = self.extractor.extract_parties(text)
        
        self.assertGreaterEqual(len(parties), 1)
        
        names = [p.name for p in parties]
        self.assertTrue(any('John Smith' in name for name in names))
    
    def test_extract_date_terms(self):
        """Test extraction of date terms"""
        text = """
        Effective Date: January 1, 2024
        Expiration Date: December 31, 2024
        This agreement was executed on 3/15/2024.
        """
        
        terms = self.extractor._extract_date_terms(text)
        
        self.assertGreater(len(terms), 0)
        
        # Check for specific date types
        term_types = [t.term_type for t in terms]
        self.assertIn('effective_date', term_types)
        self.assertIn('expiration_date', term_types)
        
        # Check that dates were parsed
        parsed_dates = [t for t in terms if t.date_value is not None]
        self.assertGreater(len(parsed_dates), 0)
    
    def test_extract_monetary_terms(self):
        """Test extraction of monetary terms"""
        text = """
        The total payment amount is $100,000.
        Monthly fees of $5,000 are due on the first of each month.
        """
        
        terms = self.extractor._extract_monetary_terms(text)
        
        self.assertGreater(len(terms), 0)
        
        # Check for monetary values
        amounts = [t.amount_value for t in terms if t.amount_value]
        self.assertGreater(len(amounts), 0)
        self.assertIn(100000.0, amounts)
    
    def test_extract_duration_terms(self):
        """Test extraction of duration terms"""
        text = """
        The contract term is 2 years from the effective date.
        Either party may terminate with 30 days notice.
        """
        
        terms = self.extractor._extract_duration_terms(text)
        
        self.assertGreater(len(terms), 0)
        
        # Check for duration values
        durations = [t.value for t in terms]
        self.assertTrue(any('2 years' in duration for duration in durations))
        self.assertTrue(any('30 days' in duration for duration in durations))
    
    def test_infer_party_role(self):
        """Test inference of party roles"""
        text = """
        ABC Corp (the "Client") agrees to purchase services from
        XYZ Services LLC (the "Vendor") under this agreement.
        """
        
        client_role = self.extractor._infer_party_role(text, "ABC Corp")
        vendor_role = self.extractor._infer_party_role(text, "XYZ Services LLC")
        
        self.assertEqual(client_role, "client")
        self.assertEqual(vendor_role, "vendor")


class TestContractTypeClassifier(unittest.TestCase):
    
    def setUp(self):
        self.classifier = ContractTypeClassifier()
    
    def test_classify_employment_contract(self):
        """Test classification of employment contracts"""
        text = """
        EMPLOYMENT AGREEMENT
        This agreement sets forth the terms of employment between Company and Employee.
        Employee will receive a salary of $75,000 annually plus benefits.
        """
        
        contract_type = self.classifier.classify_contract(text)
        
        self.assertEqual(contract_type, ContractType.EMPLOYMENT_CONTRACT)
    
    def test_classify_service_agreement(self):
        """Test classification of service agreements"""
        text = """
        SERVICE AGREEMENT
        Company engages Service Provider to perform professional consulting services
        as detailed in the attached statement of work and deliverables schedule.
        """
        
        contract_type = self.classifier.classify_contract(text)
        
        self.assertEqual(contract_type, ContractType.SERVICE_AGREEMENT)
    
    def test_classify_nda(self):
        """Test classification of NDAs"""
        text = """
        NON-DISCLOSURE AGREEMENT
        The parties agree to maintain confidentiality of proprietary information
        and trade secrets disclosed during the course of their business relationship.
        """
        
        contract_type = self.classifier.classify_contract(text)
        
        self.assertEqual(contract_type, ContractType.NDA)
    
    def test_classify_lease_agreement(self):
        """Test classification of lease agreements"""
        text = """
        LEASE AGREEMENT
        Landlord leases the premises to Tenant for monthly rent of $2,500.
        Tenant shall pay a security deposit equal to one month's rent.
        """
        
        contract_type = self.classifier.classify_contract(text)
        
        self.assertEqual(contract_type, ContractType.LEASE_AGREEMENT)
    
    def test_classify_unknown_type(self):
        """Test classification of unknown contract types"""
        text = """
        Some random text that doesn't match any specific contract patterns
        or contain recognizable legal terms and clauses.
        """
        
        contract_type = self.classifier.classify_contract(text)
        
        self.assertEqual(contract_type, ContractType.OTHER)


class TestContractAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = ContractAnalyzer()
    
    def test_analyze_complete_contract(self):
        """Test complete contract analysis"""
        contract_text = """
        SERVICE AGREEMENT
        
        This Service Agreement is entered into between TechCorp Inc. (Client) 
        and ConsultingFirm LLC (Service Provider) effective January 1, 2024.
        
        PAYMENT TERMS
        Client shall pay Service Provider $50,000 within 30 days of invoice.
        Late payments will incur a 1.5% monthly penalty.
        
        TERMINATION
        Either party may terminate this agreement with 30 days written notice.
        
        LIABILITY LIMITATION
        Service Provider's liability shall not exceed the fees paid under this agreement.
        
        GOVERNING LAW
        This agreement shall be governed by the laws of California.
        """
        
        result = self.analyzer.analyze_contract(contract_text, "test_contract_001")
        
        self.assertEqual(result.document_id, "test_contract_001")
        self.assertEqual(result.contract_type, ContractType.SERVICE_AGREEMENT)
        self.assertGreater(len(result.parties), 0)
        self.assertGreater(len(result.clauses), 0)
        self.assertGreater(len(result.terms), 0)
        self.assertIsInstance(result.overall_risk_score, float)
        self.assertIsInstance(result.compliance_issues, list)
        self.assertIsInstance(result.recommendations, list)
        
        # Check that key dates were extracted
        if result.key_dates:
            self.assertIsInstance(list(result.key_dates.values())[0], datetime.date)
        
        # Check financial terms
        self.assertIsInstance(result.financial_terms, dict)
        if result.financial_terms.get('total_value'):
            self.assertIsInstance(result.financial_terms['total_value']['amount'], float)
    
    def test_extract_contract_title(self):
        """Test contract title extraction"""
        contract_text = """
        MASTER SERVICE AGREEMENT
        
        This agreement governs the relationship between parties...
        """
        
        title = self.analyzer._extract_contract_title(contract_text)
        
        self.assertIsNotNone(title)
        self.assertIn("Master Service Agreement", title)
    
    def test_calculate_risk_score(self):
        """Test risk score calculation"""
        high_risk_clauses = [
            ContractClause(
                clause_type=ClauseType.LIABILITY_LIMITATION,
                text="Unlimited liability applies",
                start_position=0,
                end_position=25,
                confidence=0.9,
                risk_level=RiskLevel.CRITICAL
            )
        ]
        
        low_risk_clauses = [
            ContractClause(
                clause_type=ClauseType.GOVERNING_LAW,
                text="Governed by California law",
                start_position=0,
                end_position=27,
                confidence=0.9,
                risk_level=RiskLevel.LOW
            )
        ]
        
        high_risk_score = self.analyzer._calculate_risk_score(high_risk_clauses, [])
        low_risk_score = self.analyzer._calculate_risk_score(low_risk_clauses, [])
        
        self.assertGreater(high_risk_score, low_risk_score)
        self.assertGreaterEqual(high_risk_score, 50.0)  # Should be elevated due to critical risk
    
    def test_identify_compliance_issues(self):
        """Test compliance issue identification"""
        # Service agreement without required clauses
        clauses = [
            ContractClause(
                clause_type=ClauseType.GOVERNING_LAW,
                text="Governed by state law",
                start_position=0,
                end_position=20,
                confidence=0.8,
                risk_level=RiskLevel.LOW
            )
        ]
        
        issues = self.analyzer._identify_compliance_issues(clauses, ContractType.SERVICE_AGREEMENT)
        
        self.assertGreater(len(issues), 0)
        # Should identify missing required clauses
        self.assertTrue(any('termination' in issue.lower() for issue in issues))
    
    def test_generate_recommendations(self):
        """Test recommendation generation"""
        high_risk_clauses = [
            ContractClause(
                clause_type=ClauseType.LIABILITY_LIMITATION,
                text="Company accepts unlimited liability",
                start_position=0,
                end_position=35,
                confidence=0.9,
                risk_level=RiskLevel.CRITICAL
            )
        ]
        
        recommendations = self.analyzer._generate_recommendations(
            high_risk_clauses, 85.0, ["Missing termination clause"]
        )
        
        self.assertGreater(len(recommendations), 0)
        self.assertTrue(any('high-risk' in rec.lower() for rec in recommendations))
        self.assertTrue(any('compliance' in rec.lower() for rec in recommendations))
    
    def test_caching_functionality(self):
        """Test that analysis results are cached"""
        contract_text = "Simple contract for testing caching functionality."
        doc_id = "cache_test_001"
        
        # First analysis
        result1 = self.analyzer.analyze_contract(contract_text, doc_id)
        
        # Second analysis should return cached result
        result2 = self.analyzer.analyze_contract(contract_text, doc_id)
        
        self.assertIs(result1, result2)  # Same object reference indicates caching worked
    
    def test_extract_financial_terms(self):
        """Test financial terms extraction"""
        terms = [
            ContractTerm(
                term_type='payment_amount',
                value='$75,000',
                amount_value=75000.0,
                currency='USD',
                description='Annual payment'
            )
        ]
        
        clauses = [
            ContractClause(
                clause_type=ClauseType.PAYMENT_TERMS,
                text="Payment due within 30 days",
                start_position=0,
                end_position=25,
                confidence=0.8,
                risk_level=RiskLevel.LOW,
                summary="Payment terms clause"
            )
        ]
        
        financial_terms = self.analyzer._extract_financial_terms(terms, clauses)
        
        self.assertIn('total_value', financial_terms)
        self.assertIn('payment_schedule', financial_terms)
        self.assertIn('payment_terms', financial_terms)
        
        if financial_terms['total_value']:
            self.assertEqual(financial_terms['total_value']['amount'], 75000.0)


if __name__ == '__main__':
    unittest.main()