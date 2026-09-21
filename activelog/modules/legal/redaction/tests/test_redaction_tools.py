"""
Tests for Legal Document Redaction Tools
"""
import unittest
from unittest.mock import Mock, patch
from ..src.redaction_tools import (
    RedactionEngine, SensitiveDataDetector, RedactionQualityAnalyzer,
    RedactionCategory, RedactionMethod, RedactionLevel,
    SensitiveMatch, RedactionRule, RedactionResult
)


class TestSensitiveDataDetector(unittest.TestCase):
    
    def setUp(self):
        self.detector = SensitiveDataDetector()
    
    def test_detect_ssn(self):
        """Test detection of Social Security Numbers"""
        text = "John's SSN is 123-45-6789 and he was born on 01/15/1980."
        
        matches = self.detector.detect_sensitive_content(text)
        
        ssn_matches = [m for m in matches if m.category == RedactionCategory.PERSONAL_IDENTIFIERS 
                      and 'SSN' in m.reason or '123-45-6789' in m.text]
        self.assertGreater(len(ssn_matches), 0)
        
        ssn_match = ssn_matches[0]
        self.assertIn('123-45-6789', ssn_match.text)
        self.assertGreaterEqual(ssn_match.confidence, 0.8)
    
    def test_detect_email(self):
        """Test detection of email addresses"""
        text = "Please contact john.doe@example.com for more information."
        
        matches = self.detector.detect_sensitive_content(text)
        
        email_matches = [m for m in matches if m.category == RedactionCategory.PERSONAL_IDENTIFIERS 
                        and '@' in m.text]
        self.assertGreater(len(email_matches), 0)
        
        email_match = email_matches[0]
        self.assertEqual(email_match.text, 'john.doe@example.com')
        self.assertGreaterEqual(email_match.confidence, 0.8)
    
    def test_detect_phone_number(self):
        """Test detection of phone numbers"""
        text = "Call me at (555) 123-4567 or 555.987.6543."
        
        matches = self.detector.detect_sensitive_content(text)
        
        phone_matches = [m for m in matches if m.category == RedactionCategory.PERSONAL_IDENTIFIERS 
                        and any(char.isdigit() for char in m.text) and len(m.text) >= 10]
        self.assertGreater(len(phone_matches), 0)
        
        # Should detect both phone number formats
        phone_texts = [m.text for m in phone_matches]
        self.assertTrue(any('555' in text for text in phone_texts))
    
    def test_detect_credit_card(self):
        """Test detection of credit card numbers"""
        text = "My credit card number is 4532-1234-5678-9012."
        
        matches = self.detector.detect_sensitive_content(text)
        
        cc_matches = [m for m in matches if m.category == RedactionCategory.FINANCIAL_INFO]
        self.assertGreater(len(cc_matches), 0)
        
        cc_match = cc_matches[0]
        self.assertIn('4532', cc_match.text)
    
    def test_detect_attorney_client_privilege(self):
        """Test detection of attorney-client privileged content"""
        text = "This attorney-client communication is privileged and confidential."
        
        matches = self.detector.detect_sensitive_content(text)
        
        privilege_matches = [m for m in matches if m.category == RedactionCategory.LEGAL_PRIVILEGED]
        self.assertGreater(len(privilege_matches), 0)
        
        privilege_match = privilege_matches[0]
        self.assertIn('attorney-client', privilege_match.text.lower())
        self.assertGreaterEqual(privilege_match.confidence, 0.8)
    
    def test_context_based_detection(self):
        """Test context-based detection accuracy"""
        # Medical context
        text = "The patient's medical record number is MRN123456."
        
        matches = self.detector.detect_sensitive_content(text)
        
        medical_matches = [m for m in matches if m.category == RedactionCategory.MEDICAL_INFO]
        self.assertGreater(len(medical_matches), 0)
    
    def test_luhn_algorithm_validation(self):
        """Test Luhn algorithm for credit card validation"""
        # Valid credit card number (passes Luhn check)
        valid_cc = "4532123456789012"
        self.assertTrue(self.detector._luhn_check(valid_cc))
        
        # Invalid credit card number (fails Luhn check)
        invalid_cc = "1234567890123456"
        self.assertFalse(self.detector._luhn_check(invalid_cc))
    
    def test_resolve_overlapping_matches(self):
        """Test resolution of overlapping matches"""
        match1 = SensitiveMatch(
            text="john.doe@example.com",
            category=RedactionCategory.PERSONAL_IDENTIFIERS,
            start_position=10,
            end_position=30,
            confidence=0.9,
            context="Contact john.doe@example.com",
            reason="Email Address"
        )
        
        match2 = SensitiveMatch(
            text="doe@example.com",
            category=RedactionCategory.PERSONAL_IDENTIFIERS,
            start_position=15,
            end_position=30,
            confidence=0.7,
            context="Contact john.doe@example.com",
            reason="Partial Email"
        )
        
        matches = [match1, match2]
        resolved = self.detector._resolve_overlaps(matches)
        
        # Should keep the higher confidence match
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].confidence, 0.9)
        self.assertEqual(resolved[0].text, "john.doe@example.com")
    
    def test_validate_match_confidence(self):
        """Test match confidence validation"""
        # Test SSN validation
        valid_ssn = "123-45-6789"
        confidence = self.detector._validate_match(
            valid_ssn, RedactionCategory.PERSONAL_IDENTIFIERS, "", 0.8
        )
        self.assertGreaterEqual(confidence, 0.8)
        
        # Test invalid SSN (starts with 000)
        invalid_ssn = "000-45-6789"
        confidence = self.detector._validate_match(
            invalid_ssn, RedactionCategory.PERSONAL_IDENTIFIERS, "", 0.8
        )
        self.assertLess(confidence, 0.8)


class TestRedactionEngine(unittest.TestCase):
    
    def setUp(self):
        self.engine = RedactionEngine()
    
    def test_redact_ssn(self):
        """Test SSN redaction"""
        text = "John Smith's SSN is 123-45-6789."
        
        result = self.engine.redact_document(text)
        
        self.assertNotIn('123-45-6789', result.redacted_text)
        self.assertIn('[REDACTED', result.redacted_text)
        self.assertGreater(len(result.redaction_map), 0)
    
    def test_redact_email(self):
        """Test email redaction"""
        text = "Contact me at john.doe@example.com for details."
        
        result = self.engine.redact_document(text)
        
        self.assertNotIn('john.doe@example.com', result.redacted_text)
        self.assertIn('[REDACTED', result.redacted_text)
    
    def test_redact_phone_number(self):
        """Test phone number redaction"""
        text = "Call me at (555) 123-4567."
        
        result = self.engine.redact_document(text)
        
        self.assertNotIn('(555) 123-4567', result.redacted_text)
        self.assertIn('[REDACTED', result.redacted_text)
    
    def test_redact_attorney_client_content(self):
        """Test attorney-client privileged content redaction"""
        text = "This attorney-client communication contains sensitive legal advice."
        
        result = self.engine.redact_document(text)
        
        # Should use black box redaction for privileged content
        self.assertIn('█', result.redacted_text)
    
    def test_custom_redaction_rule(self):
        """Test adding and applying custom redaction rules"""
        custom_rule = RedactionRule(
            name='Custom Pattern',
            category=RedactionCategory.CUSTOM,
            pattern=r'CONFIDENTIAL-\d+',
            replacement_text='[CUSTOM REDACTED]',
            redaction_method=RedactionMethod.REPLACEMENT_TEXT,
            confidence_threshold=0.8
        )
        
        self.engine.add_custom_rule(custom_rule)
        
        text = "Document ID: CONFIDENTIAL-12345 is classified."
        result = self.engine.redact_document(text)
        
        self.assertNotIn('CONFIDENTIAL-12345', result.redacted_text)
        self.assertIn('[CUSTOM REDACTED]', result.redacted_text)
    
    def test_redaction_methods(self):
        """Test different redaction methods"""
        # Test black box method
        match = SensitiveMatch(
            text="sensitive",
            category=RedactionCategory.LEGAL_PRIVILEGED,
            start_position=0, end_position=9,
            confidence=0.9,
            context="", reason="test"
        )
        
        method = self.engine._determine_redaction_method(match)
        replacement = self.engine._generate_replacement_text(match, method)
        
        self.assertEqual(method, RedactionMethod.BLACK_BOX)
        self.assertTrue(all(c == '█' for c in replacement))
    
    def test_redaction_summary_generation(self):
        """Test redaction summary generation"""
        text = """
        John Smith (john.smith@example.com) lives at 123 Main St.
        His SSN is 123-45-6789 and phone is (555) 123-4567.
        This attorney-client communication is privileged.
        """
        
        result = self.engine.redact_document(text)
        
        summary = result.redaction_summary
        self.assertIn('total_redactions', summary)
        self.assertIn('by_category', summary)
        self.assertGreater(summary['total_redactions'], 0)
        
        # Should have personal identifiers and legal privileged content
        categories = summary['by_category']
        self.assertGreater(len(categories), 0)
    
    def test_redaction_with_different_levels(self):
        """Test redaction with different security levels"""
        text = "Classified document with SSN 123-45-6789."
        
        # Test confidential level
        result_conf = self.engine.redact_document(text, redaction_level=RedactionLevel.CONFIDENTIAL)
        
        # Test secret level  
        result_secret = self.engine.redact_document(text, redaction_level=RedactionLevel.SECRET)
        
        self.assertEqual(result_conf.metadata['redaction_level'], 'confidential')
        self.assertEqual(result_secret.metadata['redaction_level'], 'secret')
    
    def test_generate_redaction_report(self):
        """Test redaction report generation"""
        text = "John's email is john@example.com and SSN is 123-45-6789."
        
        result = self.engine.redact_document(text)
        report = self.engine.generate_redaction_report(result)
        
        self.assertIn('redaction_metadata', report)
        self.assertIn('redaction_summary', report)
        self.assertIn('redaction_locations', report)
        self.assertIn('quality_metrics', report)
        self.assertIn('compliance_status', report)
        
        # Check metadata
        metadata = report['redaction_metadata']
        self.assertIn('redacted_at', metadata)
        self.assertIn('total_length', metadata)
        self.assertIn('reduction_ratio', metadata)
    
    def test_redaction_rule_management(self):
        """Test adding and removing redaction rules"""
        # Add custom rule
        custom_rule = RedactionRule(
            name='Test Rule',
            category=RedactionCategory.CUSTOM,
            pattern=r'TEST-\d+',
            replacement_text='[TEST REDACTED]',
            redaction_method=RedactionMethod.REPLACEMENT_TEXT,
            confidence_threshold=0.8
        )
        
        initial_count = len(self.engine.redaction_rules)
        self.engine.add_custom_rule(custom_rule)
        
        self.assertEqual(len(self.engine.redaction_rules), initial_count + 1)
        self.assertIn('Test Rule', self.engine.redaction_rules)
        
        # Remove rule
        self.engine.remove_rule('Test Rule')
        self.assertEqual(len(self.engine.redaction_rules), initial_count)
        self.assertNotIn('Test Rule', self.engine.redaction_rules)
    
    @patch('modules.legal.redaction.src.redaction_tools.Fernet')
    def test_encrypted_redaction(self, mock_fernet):
        """Test encrypted redaction method"""
        # Mock Fernet encryption
        mock_cipher = Mock()
        mock_cipher.encrypt.return_value = b'encrypted_data'
        mock_fernet.return_value = mock_cipher
        
        engine = RedactionEngine(encryption_key=b'test_key_32_bytes_long_for_fernet!')
        
        match = SensitiveMatch(
            text="classified info",
            category=RedactionCategory.CLASSIFIED,
            start_position=0, end_position=15,
            confidence=0.9,
            context="", reason="test"
        )
        
        replacement = engine._generate_replacement_text(match, RedactionMethod.ENCRYPTED_REDACTION)
        
        self.assertIn('[ENCRYPTED:', replacement)


class TestRedactionQualityAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = RedactionQualityAnalyzer()
    
    def create_mock_redaction_result(self, redacted_text: str, matches: List[SensitiveMatch]) -> RedactionResult:
        """Create mock redaction result for testing"""
        redaction_map = {match.start_position: match for match in matches}
        
        summary = {
            'total_redactions': len(matches),
            'by_category': {},
            'by_confidence': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        for match in matches:
            category = match.category.value
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            if match.confidence >= 0.8:
                summary['by_confidence']['high'] += 1
            elif match.confidence >= 0.6:
                summary['by_confidence']['medium'] += 1
            else:
                summary['by_confidence']['low'] += 1
        
        return RedactionResult(
            original_text="Original text with sensitive data",
            redacted_text=redacted_text,
            redaction_map=redaction_map,
            redaction_summary=summary,
            redacted_at=datetime.datetime.utcnow()
        )
    
    def test_detect_information_leakage(self):
        """Test detection of potential information leakage"""
        # Text with potential leakage (sensitive info after redaction marker)
        redacted_text = "Contact [REDACTED] john.doe@example.com for details."
        
        leaks = self.analyzer._detect_information_leakage(redacted_text)
        
        self.assertGreater(len(leaks), 0)
        leak = leaks[0]
        self.assertEqual(leak['type'], 'potential_leak')
        self.assertIn('john.doe@example.com', leak['text'])
    
    def test_calculate_completeness_score(self):
        """Test completeness score calculation"""
        # High confidence matches
        high_confidence_matches = [
            SensitiveMatch("test1", RedactionCategory.PERSONAL_IDENTIFIERS, 0, 5, 0.9, "", "test"),
            SensitiveMatch("test2", RedactionCategory.PERSONAL_IDENTIFIERS, 10, 15, 0.95, "", "test")
        ]
        
        result = self.create_mock_redaction_result("redacted text", high_confidence_matches)
        score = self.analyzer._calculate_completeness_score(result)
        
        self.assertEqual(score, 1.0)  # All high confidence
        
        # Mixed confidence matches
        mixed_matches = [
            SensitiveMatch("test1", RedactionCategory.PERSONAL_IDENTIFIERS, 0, 5, 0.9, "", "test"),
            SensitiveMatch("test2", RedactionCategory.PERSONAL_IDENTIFIERS, 10, 15, 0.5, "", "test")
        ]
        
        result = self.create_mock_redaction_result("redacted text", mixed_matches)
        score = self.analyzer._calculate_completeness_score(result)
        
        self.assertEqual(score, 0.5)  # 50% high confidence
    
    def test_calculate_consistency_score(self):
        """Test consistency score calculation"""
        # Consistent redactions (same category, same method)
        consistent_matches = [
            SensitiveMatch("test1", RedactionCategory.PERSONAL_IDENTIFIERS, 0, 5, 0.9, "", "test", 
                         metadata={'method': 'replacement_text'}),
            SensitiveMatch("test2", RedactionCategory.PERSONAL_IDENTIFIERS, 10, 15, 0.9, "", "test",
                         metadata={'method': 'replacement_text'})
        ]
        
        result = self.create_mock_redaction_result("redacted text", consistent_matches)
        score = self.analyzer._calculate_consistency_score(result)
        
        self.assertEqual(score, 1.0)  # Perfect consistency
    
    def test_analyze_redaction_quality(self):
        """Test comprehensive redaction quality analysis"""
        matches = [
            SensitiveMatch("email@test.com", RedactionCategory.PERSONAL_IDENTIFIERS, 0, 14, 0.9, "", "Email"),
            SensitiveMatch("123-45-6789", RedactionCategory.PERSONAL_IDENTIFIERS, 20, 31, 0.85, "", "SSN")
        ]
        
        result = self.create_mock_redaction_result(
            "Contact [REDACTED EMAIL] at work. SSN: [REDACTED SSN].",
            matches
        )
        
        analysis = self.analyzer.analyze_redaction_quality(result)
        
        self.assertIn('completeness_score', analysis)
        self.assertIn('consistency_score', analysis)
        self.assertIn('potential_leaks', analysis)
        self.assertIn('recommendations', analysis)
        self.assertIn('overall_quality', analysis)
        
        # Should have good quality with high confidence matches
        self.assertGreaterEqual(analysis['completeness_score'], 0.8)
        self.assertIn(analysis['overall_quality'], ['good', 'excellent'])
    
    def test_generate_quality_recommendations(self):
        """Test generation of quality improvement recommendations"""
        # Create result with some issues
        low_confidence_matches = [
            SensitiveMatch("maybe sensitive", RedactionCategory.PERSONAL_IDENTIFIERS, 0, 15, 0.4, "", "Low confidence")
        ]
        
        result = self.create_mock_redaction_result("redacted text", low_confidence_matches)
        
        # Simulate some leaks
        leaks = [{'type': 'potential_leak', 'concern': 'test leak'}]
        
        recommendations = self.analyzer._generate_quality_recommendations(result, leaks)
        
        self.assertGreater(len(recommendations), 0)
        self.assertTrue(any('leakage' in rec.lower() for rec in recommendations))
        self.assertTrue(any('low-confidence' in rec.lower() for rec in recommendations))


if __name__ == '__main__':
    unittest.main()