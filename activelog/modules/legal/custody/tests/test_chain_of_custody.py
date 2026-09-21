"""
Tests for Chain of Custody Tracking System
"""
import unittest
import datetime
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from ..src.chain_of_custody import (
    CustodyTracker, HashCalculator, DigitalSignature,
    CustodyParticipant, EvidenceItem, CustodyEvent, CustodyChain,
    CustodyAction, EvidenceType, CustodyLevel, VerificationStatus
)


class TestHashCalculator(unittest.TestCase):
    
    def setUp(self):
        self.calculator = HashCalculator()
    
    def test_calculate_string_hashes(self):
        """Test hash calculation for string content"""
        test_content = "This is test content for hashing"
        
        hashes = self.calculator.calculate_string_hashes(test_content)
        
        self.assertIn('md5', hashes)
        self.assertIn('sha256', hashes)
        self.assertIn('sha512', hashes)
        
        # Verify hash lengths
        self.assertEqual(len(hashes['md5']), 32)
        self.assertEqual(len(hashes['sha256']), 64)
        self.assertEqual(len(hashes['sha512']), 128)
        
        # Verify consistency
        hashes2 = self.calculator.calculate_string_hashes(test_content)
        self.assertEqual(hashes, hashes2)
    
    def test_calculate_file_hashes(self):
        """Test hash calculation for file content"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Test file content for hash calculation")
            temp_file_path = temp_file.name
        
        try:
            hashes = self.calculator.calculate_file_hashes(temp_file_path)
            
            self.assertIn('md5', hashes)
            self.assertIn('sha256', hashes)
            self.assertIn('sha512', hashes)
            
            # Verify hash lengths
            self.assertEqual(len(hashes['md5']), 32)
            self.assertEqual(len(hashes['sha256']), 64)
            self.assertEqual(len(hashes['sha512']), 128)
            
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    def test_verify_file_integrity(self):
        """Test file integrity verification"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Test content for integrity check")
            temp_file_path = temp_file.name
        
        try:
            # Calculate original hashes
            original_hashes = self.calculator.calculate_file_hashes(temp_file_path)
            
            # Verify integrity with correct hashes
            verification = self.calculator.verify_file_integrity(temp_file_path, original_hashes)
            
            self.assertTrue(all(verification.values()))
            
            # Test with incorrect hash
            wrong_hashes = original_hashes.copy()
            wrong_hashes['sha256'] = 'wrong_hash'
            
            verification = self.calculator.verify_file_integrity(temp_file_path, wrong_hashes)
            
            self.assertTrue(verification['md5'])
            self.assertFalse(verification['sha256'])
            self.assertTrue(verification['sha512'])
            
        finally:
            os.unlink(temp_file_path)


class TestDigitalSignature(unittest.TestCase):
    
    def setUp(self):
        self.signer = DigitalSignature("test_private_key")
    
    def create_test_event(self) -> CustodyEvent:
        """Create test custody event"""
        participant = CustodyParticipant(
            id="test_user",
            name="Test User",
            role="Evidence Custodian",
            organization="Test Org"
        )
        
        return CustodyEvent(
            event_id="test_event_1",
            timestamp=datetime.datetime.utcnow(),
            action=CustodyAction.CREATED,
            participant=participant,
            evidence_items=["item1", "item2"],
            location="Test Location",
            purpose="Testing",
            verification_hash="test_hash"
        )
    
    def test_sign_event(self):
        """Test digital signature creation"""
        event = self.create_test_event()
        
        signature = self.signer.sign_event(event)
        
        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)
        
        # Verify signature is consistent
        signature2 = self.signer.sign_event(event)
        self.assertEqual(signature, signature2)
    
    def test_verify_signature(self):
        """Test digital signature verification"""
        event = self.create_test_event()
        
        # Create and verify correct signature
        signature = self.signer.sign_event(event)
        is_valid = self.signer.verify_signature(event, signature)
        
        self.assertTrue(is_valid)
        
        # Test with incorrect signature
        wrong_signature = "wrong_signature"
        is_valid = self.signer.verify_signature(event, wrong_signature)
        
        self.assertFalse(is_valid)
    
    def test_signature_changes_with_event_modification(self):
        """Test that signature changes when event is modified"""
        event1 = self.create_test_event()
        event2 = self.create_test_event()
        event2.purpose = "Modified purpose"
        
        signature1 = self.signer.sign_event(event1)
        signature2 = self.signer.sign_event(event2)
        
        self.assertNotEqual(signature1, signature2)


class TestCustodyTracker(unittest.TestCase):
    
    def setUp(self):
        self.tracker = CustodyTracker()
        self.test_custodian = CustodyParticipant(
            id="custodian_001",
            name="John Doe",
            role="Evidence Custodian",
            organization="Legal Department",
            credentials="Badge #12345"
        )
    
    def test_create_custody_chain(self):
        """Test custody chain creation"""
        case_number = "CASE-2024-001"
        
        chain_id = self.tracker.create_custody_chain(
            case_number=case_number,
            initial_custodian=self.test_custodian,
            custody_level=CustodyLevel.FORENSIC
        )
        
        self.assertIsNotNone(chain_id)
        self.assertIn(chain_id, self.tracker.custody_chains)
        
        chain = self.tracker.custody_chains[chain_id]
        self.assertEqual(chain.case_number, case_number)
        self.assertEqual(chain.current_custodian.id, self.test_custodian.id)
        self.assertEqual(chain.custody_level, CustodyLevel.FORENSIC)
        self.assertFalse(chain.sealed)
        
        # Should have initial creation event
        self.assertEqual(len(chain.custody_events), 1)
        self.assertEqual(chain.custody_events[0].action, CustodyAction.CREATED)
    
    def test_add_evidence_item(self):
        """Test adding evidence items to custody chain"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Test evidence content")
            temp_file_path = temp_file.name
        
        try:
            item_id = self.tracker.add_evidence_item(
                chain_id=chain_id,
                evidence_type=EvidenceType.DOCUMENT,
                description="Test document evidence",
                file_path=temp_file_path,
                metadata={"source": "test"}
            )
            
            self.assertIsNotNone(item_id)
            
            chain = self.tracker.custody_chains[chain_id]
            self.assertIn(item_id, chain.evidence_items)
            
            evidence_item = chain.evidence_items[item_id]
            self.assertEqual(evidence_item.evidence_type, EvidenceType.DOCUMENT)
            self.assertEqual(evidence_item.description, "Test document evidence")
            self.assertIsNotNone(evidence_item.hash_sha256)
            self.assertIsNotNone(evidence_item.file_size)
            
            # Should have creation event
            creation_events = [e for e in chain.custody_events if e.action == CustodyAction.CREATED and item_id in e.evidence_items]
            self.assertEqual(len(creation_events), 1)
            
        finally:
            os.unlink(temp_file_path)
    
    def test_transfer_custody(self):
        """Test custody transfer"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        # Add evidence item
        item_id = self.tracker.add_evidence_item(
            chain_id, EvidenceType.DOCUMENT, "Test document"
        )
        
        # Create second custodian
        second_custodian = CustodyParticipant(
            id="custodian_002",
            name="Jane Smith",
            role="Legal Analyst",
            organization="Legal Department"
        )
        
        # Create witness
        witness = CustodyParticipant(
            id="witness_001",
            name="Bob Wilson",
            role="Supervisor",
            organization="Legal Department"
        )
        
        # Transfer custody
        event_id = self.tracker.transfer_custody(
            chain_id=chain_id,
            from_custodian=self.test_custodian,
            to_custodian=second_custodian,
            evidence_item_ids=[item_id],
            location="Evidence Room A",
            purpose="Analysis required",
            witness=witness
        )
        
        self.assertIsNotNone(event_id)
        
        chain = self.tracker.custody_chains[chain_id]
        self.assertEqual(chain.current_custodian.id, second_custodian.id)
        
        # Should have transfer and received events
        transfer_events = [e for e in chain.custody_events if e.action == CustodyAction.TRANSFERRED]
        received_events = [e for e in chain.custody_events if e.action == CustodyAction.RECEIVED]
        
        self.assertEqual(len(transfer_events), 1)
        self.assertEqual(len(received_events), 1)
        
        # Check witness recorded
        self.assertEqual(transfer_events[0].witness.id, witness.id)
        self.assertEqual(received_events[0].witness.id, witness.id)
    
    def test_access_evidence(self):
        """Test evidence access recording"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        item_id = self.tracker.add_evidence_item(
            chain_id, EvidenceType.DOCUMENT, "Test document"
        )
        
        # Record access
        accessor = CustodyParticipant(
            id="analyst_001",
            name="Legal Analyst",
            role="Analyst",
            organization="Legal Department"
        )
        
        access_event_id = self.tracker.access_evidence(
            chain_id=chain_id,
            evidence_item_ids=[item_id],
            accessor=accessor,
            purpose="Document review",
            location="Review Room B"
        )
        
        self.assertIsNotNone(access_event_id)
        
        chain = self.tracker.custody_chains[chain_id]
        access_events = [e for e in chain.custody_events if e.action == CustodyAction.ACCESSED]
        
        self.assertEqual(len(access_events), 1)
        self.assertEqual(access_events[0].participant.id, accessor.id)
        self.assertEqual(access_events[0].purpose, "Document review")
    
    def test_verify_evidence_integrity(self):
        """Test evidence integrity verification"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Test evidence content")
            temp_file_path = temp_file.name
        
        try:
            item_id = self.tracker.add_evidence_item(
                chain_id, EvidenceType.DOCUMENT, "Test document", temp_file_path
            )
            
            # Verify integrity
            verification_results = self.tracker.verify_evidence_integrity(chain_id, [item_id])
            
            self.assertIn(item_id, verification_results)
            result = verification_results[item_id]
            
            self.assertEqual(result['status'], VerificationStatus.VERIFIED)
            self.assertIn('hash_verification', result)
            
            chain = self.tracker.custody_chains[chain_id]
            self.assertEqual(chain.verification_status, VerificationStatus.VERIFIED)
            self.assertIsNotNone(chain.last_verified)
            
        finally:
            os.unlink(temp_file_path)
    
    def test_verify_evidence_integrity_corrupted(self):
        """Test integrity verification with corrupted file"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Original content")
            temp_file_path = temp_file.name
        
        try:
            item_id = self.tracker.add_evidence_item(
                chain_id, EvidenceType.DOCUMENT, "Test document", temp_file_path
            )
            
            # Modify the file to simulate corruption
            with open(temp_file_path, 'w') as f:
                f.write("Modified content - file corrupted")
            
            # Verify integrity
            verification_results = self.tracker.verify_evidence_integrity(chain_id, [item_id])
            
            result = verification_results[item_id]
            self.assertEqual(result['status'], VerificationStatus.CORRUPTED)
            
            chain = self.tracker.custody_chains[chain_id]
            self.assertEqual(chain.verification_status, VerificationStatus.CORRUPTED)
            
        finally:
            os.unlink(temp_file_path)
    
    def test_seal_custody_chain(self):
        """Test sealing of custody chain"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        item_id = self.tracker.add_evidence_item(
            chain_id, EvidenceType.DOCUMENT, "Test document"
        )
        
        # Seal the chain
        sealing_authority = CustodyParticipant(
            id="judge_001",
            name="Judge Smith",
            role="Judge",
            organization="Court"
        )
        
        seal_event_id = self.tracker.seal_custody_chain(
            chain_id=chain_id,
            sealing_authority=sealing_authority,
            reason="Case closed"
        )
        
        self.assertIsNotNone(seal_event_id)
        
        chain = self.tracker.custody_chains[chain_id]
        self.assertTrue(chain.sealed)
        self.assertEqual(chain.sealed_by.id, sealing_authority.id)
        self.assertIsNotNone(chain.sealed_at)
        
        # Should have sealing event
        seal_events = [e for e in chain.custody_events if e.action == CustodyAction.SEALED]
        self.assertEqual(len(seal_events), 1)
        
        # Should not be able to add evidence to sealed chain
        with self.assertRaises(ValueError):
            self.tracker.add_evidence_item(chain_id, EvidenceType.DOCUMENT, "New document")
        
        # Should not be able to transfer custody of sealed chain
        with self.assertRaises(ValueError):
            self.tracker.transfer_custody(
                chain_id, self.test_custodian, sealing_authority, [item_id]
            )
    
    def test_generate_custody_report(self):
        """Test custody report generation"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        item_id = self.tracker.add_evidence_item(
            chain_id, EvidenceType.DOCUMENT, "Test document"
        )
        
        # Add some activity
        accessor = CustodyParticipant(
            id="analyst_001", name="Analyst", role="Analyst", organization="Legal"
        )
        self.tracker.access_evidence(chain_id, [item_id], accessor, "Review")
        
        # Generate report
        report = self.tracker.generate_custody_report(chain_id)
        
        self.assertIn('chain_summary', report)
        self.assertIn('evidence_items', report)
        self.assertIn('custody_events', report)
        self.assertIn('verification_results', report)
        self.assertIn('event_analysis', report)
        self.assertIn('report_generated_at', report)
        
        # Check chain summary
        chain_summary = report['chain_summary']
        self.assertEqual(chain_summary['chain_id'], chain_id)
        self.assertEqual(chain_summary['case_number'], "CASE-001")
        self.assertFalse(chain_summary['sealed'])
        
        # Check evidence items
        self.assertIn(item_id, report['evidence_items'])
        
        # Check event analysis
        event_analysis = report['event_analysis']
        self.assertGreater(event_analysis['total_events'], 0)
        self.assertEqual(event_analysis['access_events'], 1)
    
    def test_export_custody_chain_json(self):
        """Test JSON export of custody chain"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        self.tracker.add_evidence_item(
            chain_id, EvidenceType.DOCUMENT, "Test document"
        )
        
        # Export as JSON
        json_export = self.tracker.export_custody_chain(chain_id, 'json')
        
        self.assertIsInstance(json_export, str)
        
        # Verify it's valid JSON
        import json
        parsed_export = json.loads(json_export)
        
        self.assertIn('chain_summary', parsed_export)
        self.assertIn('evidence_items', parsed_export)
        self.assertIn('custody_events', parsed_export)
    
    def test_export_custody_chain_csv(self):
        """Test CSV export of custody chain"""
        chain_id = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        
        item_id = self.tracker.add_evidence_item(
            chain_id, EvidenceType.DOCUMENT, "Test document"
        )
        
        # Export as CSV
        csv_export = self.tracker.export_custody_chain(chain_id, 'csv')
        
        self.assertIsInstance(csv_export, str)
        self.assertIn('Event ID', csv_export)  # Header
        self.assertIn('CASE-001', csv_export)  # Should contain case number in participant field
        
        # Should have multiple lines (header + events)
        lines = csv_export.strip().split('\n')
        self.assertGreater(len(lines), 1)
    
    def test_search_evidence(self):
        """Test evidence search functionality"""
        # Create multiple chains with evidence
        chain1 = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        chain2 = self.tracker.create_custody_chain("CASE-002", self.test_custodian)
        
        item1 = self.tracker.add_evidence_item(
            chain1, EvidenceType.DOCUMENT, "Contract agreement document"
        )
        
        item2 = self.tracker.add_evidence_item(
            chain2, EvidenceType.EMAIL, "Email communication evidence"
        )
        
        item3 = self.tracker.add_evidence_item(
            chain1, EvidenceType.DOCUMENT, "Financial records spreadsheet"
        )
        
        # Search for contract-related evidence
        results = self.tracker.search_evidence("contract")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['item_id'], item1)
        self.assertEqual(results[0]['chain_id'], chain1)
        
        # Search for document evidence
        results = self.tracker.search_evidence("document")
        
        self.assertEqual(len(results), 2)  # Should find both documents
        
        # Search in specific chain
        results = self.tracker.search_evidence("document", [chain2])
        
        self.assertEqual(len(results), 0)  # No documents in chain2
    
    def test_list_custody_chains(self):
        """Test listing custody chains"""
        # Create multiple chains
        chain1 = self.tracker.create_custody_chain("CASE-001", self.test_custodian)
        chain2 = self.tracker.create_custody_chain("CASE-002", self.test_custodian)
        chain3 = self.tracker.create_custody_chain("CASE-001", self.test_custodian)  # Same case
        
        # List all chains
        all_chains = self.tracker.list_custody_chains()
        self.assertEqual(len(all_chains), 3)
        self.assertIn(chain1, all_chains)
        self.assertIn(chain2, all_chains)
        self.assertIn(chain3, all_chains)
        
        # List chains for specific case
        case_001_chains = self.tracker.list_custody_chains("CASE-001")
        self.assertEqual(len(case_001_chains), 2)
        self.assertIn(chain1, case_001_chains)
        self.assertIn(chain3, case_001_chains)
        self.assertNotIn(chain2, case_001_chains)
    
    def test_custody_chain_not_found(self):
        """Test error handling for non-existent custody chain"""
        with self.assertRaises(ValueError):
            self.tracker.add_evidence_item(
                "nonexistent_chain", EvidenceType.DOCUMENT, "Test"
            )
        
        with self.assertRaises(ValueError):
            self.tracker.verify_evidence_integrity("nonexistent_chain")
        
        with self.assertRaises(ValueError):
            self.tracker.generate_custody_report("nonexistent_chain")


if __name__ == '__main__':
    unittest.main()