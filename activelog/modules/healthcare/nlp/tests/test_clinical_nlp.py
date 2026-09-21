"""
Tests for Clinical Notes NLP Processing Module
"""
import unittest
import datetime
from ..src.clinical_nlp import (
    ClinicalNLPProcessor, ClinicalEntityExtractor, ClinicalSentimentAnalyzer,
    MedicalTerminologyMatcher, NoteType, EntityType, Sentiment,
    MedicalEntity, NLPResult
)


class TestMedicalTerminologyMatcher(unittest.TestCase):
    
    def setUp(self):
        self.matcher = MedicalTerminologyMatcher()
    
    def test_match_medication(self):
        """Test matching medication terms"""
        result = self.matcher.match_term('aspirin')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['preferred'], 'Aspirin')
        self.assertEqual(result['semantic_type'], 'medication')
        self.assertIn('cui', result)
    
    def test_match_condition(self):
        """Test matching condition terms"""
        result = self.matcher.match_term('diabetes')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['preferred'], 'Diabetes Mellitus')
        self.assertEqual(result['semantic_type'], 'condition')
        self.assertIn('cui', result)
    
    def test_match_synonym(self):
        """Test matching medication synonyms"""
        # Paracetamol should map to Acetaminophen
        result = self.matcher.match_term('paracetamol')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['preferred'], 'Acetaminophen')
    
    def test_match_case_insensitive(self):
        """Test case-insensitive matching"""
        result1 = self.matcher.match_term('ASPIRIN')
        result2 = self.matcher.match_term('aspirin')
        
        self.assertEqual(result1, result2)
    
    def test_no_match(self):
        """Test handling of unknown terms"""
        result = self.matcher.match_term('unknown_medication')
        
        self.assertIsNone(result)


class TestClinicalEntityExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = ClinicalEntityExtractor()
    
    def test_extract_medication_entities(self):
        """Test extracting medication entities"""
        text = "Patient was prescribed aspirin 81mg daily and ibuprofen 400mg as needed."
        
        entities = self.extractor.extract_entities(text)
        
        medication_entities = [e for e in entities if e.entity_type == EntityType.MEDICATION]
        self.assertGreaterEqual(len(medication_entities), 2)
        
        # Check for aspirin
        aspirin_entities = [e for e in medication_entities if 'aspirin' in e.text.lower()]
        self.assertGreater(len(aspirin_entities), 0)
        
        # Should have concept ID
        self.assertIsNotNone(aspirin_entities[0].concept_id)
    
    def test_extract_condition_entities(self):
        """Test extracting condition entities"""
        text = "Patient has diabetes and hypertension. History of pneumonia."
        
        entities = self.extractor.extract_entities(text)
        
        condition_entities = [e for e in entities if e.entity_type == EntityType.CONDITION]
        self.assertGreaterEqual(len(condition_entities), 3)
        
        condition_texts = [e.text.lower() for e in condition_entities]
        self.assertIn('diabetes', condition_texts)
        self.assertIn('hypertension', condition_texts)
        self.assertIn('pneumonia', condition_texts)
    
    def test_extract_vital_sign_entities(self):
        """Test extracting vital sign entities"""
        text = "Blood pressure 120/80, heart rate 72 bpm, temperature 98.6F."
        
        entities = self.extractor.extract_entities(text)
        
        vital_entities = [e for e in entities if e.entity_type == EntityType.VITAL_SIGN]
        self.assertGreater(len(vital_entities), 0)
        
        vital_texts = [e.text.lower() for e in vital_entities]
        self.assertTrue(any('blood pressure' in text for text in vital_texts))
    
    def test_extract_dosage_entities(self):
        """Test extracting dosage entities"""
        text = "Take 50mg twice daily. Apply 2 tablets every 8 hours."
        
        entities = self.extractor.extract_entities(text)
        
        dosage_entities = [e for e in entities if e.entity_type == EntityType.DOSAGE]
        self.assertGreater(len(dosage_entities), 0)
        
        dosage_texts = [e.text.lower() for e in dosage_entities]
        self.assertTrue(any('mg' in text for text in dosage_texts))
    
    def test_remove_overlapping_entities(self):
        """Test removal of overlapping entities"""
        # Create overlapping entities manually
        entity1 = MedicalEntity(
            text="blood pressure",
            entity_type=EntityType.VITAL_SIGN,
            start_pos=0,
            end_pos=14,
            confidence=0.9
        )
        
        entity2 = MedicalEntity(
            text="pressure",
            entity_type=EntityType.VITAL_SIGN,
            start_pos=6,
            end_pos=14,
            confidence=0.7
        )
        
        entities = [entity1, entity2]
        filtered = self.extractor._remove_overlapping_entities(entities)
        
        # Should keep the higher confidence entity
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].text, "blood pressure")


class TestClinicalSentimentAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = ClinicalSentimentAnalyzer()
    
    def test_positive_sentiment(self):
        """Test positive sentiment detection"""
        text = "Patient is feeling much better. Symptoms have improved significantly."
        
        sentiment, confidence = self.analyzer.analyze_sentiment(text, [])
        
        self.assertEqual(sentiment, Sentiment.POSITIVE)
        self.assertGreater(confidence, 0.5)
    
    def test_negative_sentiment(self):
        """Test negative sentiment detection"""
        text = "Patient condition has deteriorated. Severe pain and concerning symptoms."
        
        sentiment, confidence = self.analyzer.analyze_sentiment(text, [])
        
        self.assertEqual(sentiment, Sentiment.NEGATIVE)
        self.assertGreater(confidence, 0.5)
    
    def test_neutral_sentiment(self):
        """Test neutral sentiment detection"""
        text = "Patient presents for routine checkup. No significant changes."
        
        sentiment, confidence = self.analyzer.analyze_sentiment(text, [])
        
        self.assertEqual(sentiment, Sentiment.NEUTRAL)
    
    def test_uncertain_sentiment(self):
        """Test uncertain sentiment detection"""
        text = "Possible infection. Consider rule out pneumonia. Likely viral."
        
        sentiment, confidence = self.analyzer.analyze_sentiment(text, [])
        
        self.assertEqual(sentiment, Sentiment.UNCERTAIN)
        self.assertGreater(confidence, 0.5)
    
    def test_negation_handling(self):
        """Test handling of negation in sentiment"""
        text = "Patient is not feeling worse. No deterioration noted."
        
        sentiment, confidence = self.analyzer.analyze_sentiment(text, [])
        
        # Negation should affect sentiment analysis
        self.assertNotEqual(sentiment, Sentiment.NEGATIVE)


class TestClinicalNLPProcessor(unittest.TestCase):
    
    def setUp(self):
        self.processor = ClinicalNLPProcessor()
    
    def test_process_clinical_note(self):
        """Test complete clinical note processing"""
        text = """
        Patient presents with diabetes and hypertension. 
        Currently taking metformin 500mg twice daily and lisinopril 10mg daily.
        Blood pressure 130/85, feeling better overall.
        """
        
        result = self.processor.process_clinical_note(text, NoteType.PROGRESS_NOTE, "patient123")
        
        self.assertIsInstance(result, NLPResult)
        self.assertEqual(result.text, text)
        self.assertGreater(len(result.entities), 0)
        self.assertGreater(len(result.concepts), 0)
        self.assertIsInstance(result.sentiment, Sentiment)
        self.assertGreater(result.confidence_score, 0)
        
        # Check metadata
        self.assertEqual(result.metadata['note_type'], 'progress_note')
        self.assertEqual(result.metadata['patient_id'], 'patient123')
    
    def test_extract_medication_regimen(self):
        """Test medication regimen extraction"""
        notes_data = [
            {
                'text': 'Started on aspirin 81mg daily and metformin 500mg twice daily.',
                'note_type': 'progress_note',
                'patient_id': 'patient123'
            }
        ]
        
        results = self.processor.batch_process_notes(notes_data)
        medications = self.processor.extract_medication_regimen(results)
        
        self.assertGreater(len(medications), 0)
        self.assertIn('Aspirin', medications.keys())
        
        aspirin_info = medications['Aspirin'][0]
        self.assertIn('dosages', aspirin_info)
        self.assertGreater(len(aspirin_info['dosages']), 0)
    
    def test_generate_summary_report(self):
        """Test summary report generation"""
        notes_data = [
            {
                'text': 'Patient has diabetes, taking metformin. Feeling better.',
                'note_type': 'progress_note'
            },
            {
                'text': 'Blood pressure elevated. Started on lisinopril.',
                'note_type': 'progress_note'
            }
        ]
        
        results = self.processor.batch_process_notes(notes_data)
        report = self.processor.generate_summary_report(results)
        
        self.assertIn('summary', report)
        self.assertEqual(report['summary']['documents_processed'], 2)
        self.assertGreater(report['summary']['total_entities'], 0)
        self.assertIn('entity_distribution', report)
        self.assertIn('sentiment_distribution', report)
    
    def test_search_entities_by_type(self):
        """Test searching entities by type"""
        text = "Patient taking aspirin and metformin for diabetes and hypertension."
        result = self.processor.process_clinical_note(text)
        
        medication_entities = self.processor.search_entities_by_type([result], EntityType.MEDICATION)
        condition_entities = self.processor.search_entities_by_type([result], EntityType.CONDITION)
        
        self.assertGreater(len(medication_entities), 0)
        self.assertGreater(len(condition_entities), 0)
        
        # All returned entities should be of the requested type
        self.assertTrue(all(e.entity_type == EntityType.MEDICATION for e in medication_entities))
        self.assertTrue(all(e.entity_type == EntityType.CONDITION for e in condition_entities))
    
    def test_identify_clinical_trends(self):
        """Test clinical trend identification"""
        # Create multiple notes with different timestamps
        notes_data = [
            {
                'text': 'Patient feeling worse, pain increased.',
                'note_type': 'progress_note'
            },
            {
                'text': 'Patient improving, pain decreased.',
                'note_type': 'progress_note'
            },
            {
                'text': 'Patient stable, no change in condition.',
                'note_type': 'progress_note'
            }
        ]
        
        results = self.processor.batch_process_notes(notes_data)
        
        # Manually set different timestamps for testing
        base_time = datetime.datetime.utcnow()
        for i, result in enumerate(results):
            result.processed_at = base_time + datetime.timedelta(days=i)
        
        trends = self.processor.identify_clinical_trends(results)
        
        self.assertIn('sentiment_trend', trends)
        self.assertIn('entity_count_trend', trends)
        self.assertEqual(len(trends['sentiment_trend']), 3)
    
    def test_batch_processing(self):
        """Test batch processing of multiple notes"""
        notes_data = [
            {
                'text': 'Patient has diabetes, started metformin.',
                'note_type': 'progress_note',
                'patient_id': 'patient1'
            },
            {
                'text': 'Blood pressure check, normal readings.',
                'note_type': 'progress_note',
                'patient_id': 'patient2'
            },
            {
                'text': 'Invalid note data',  # This might cause issues
                'note_type': 'invalid_type',  # Invalid type
                'patient_id': 'patient3'
            }
        ]
        
        results = self.processor.batch_process_notes(notes_data)
        
        # Should process the valid notes, skip or handle invalid ones
        self.assertGreaterEqual(len(results), 2)
        
        # Check that valid notes were processed correctly
        valid_results = [r for r in results if r.metadata['patient_id'] in ['patient1', 'patient2']]
        self.assertEqual(len(valid_results), 2)
    
    def test_processing_statistics(self):
        """Test processing statistics tracking"""
        initial_stats = self.processor.get_processing_statistics()
        
        text = "Patient taking aspirin for heart condition."
        self.processor.process_clinical_note(text)
        
        updated_stats = self.processor.get_processing_statistics()
        
        self.assertEqual(updated_stats['documents_processed'], 
                        initial_stats['documents_processed'] + 1)
        self.assertGreater(updated_stats['entities_extracted'], 
                          initial_stats['entities_extracted'])
        self.assertIsNotNone(updated_stats['last_processed'])


if __name__ == '__main__':
    unittest.main()