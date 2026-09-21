"""
Chain of Custody Tracking System
Comprehensive system for tracking legal evidence and document custody with forensic integrity.
"""
import datetime
import hashlib
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import base64
from pathlib import Path


class CustodyAction(Enum):
    """Types of custody actions"""
    CREATED = "created"
    ACCESSED = "accessed"
    MODIFIED = "modified"
    COPIED = "copied"
    TRANSFERRED = "transferred"
    RECEIVED = "received"
    STORED = "stored"
    RETRIEVED = "retrieved"
    ANALYZED = "analyzed"
    EXPORTED = "exported"
    DESTROYED = "destroyed"
    SEALED = "sealed"
    UNSEALED = "unsealed"
    VERIFIED = "verified"


class EvidenceType(Enum):
    """Types of legal evidence"""
    DOCUMENT = "document"
    EMAIL = "email"
    DATABASE = "database"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SYSTEM_LOG = "system_log"
    METADATA = "metadata"
    COMMUNICATION = "communication"
    FINANCIAL_RECORD = "financial_record"
    SOCIAL_MEDIA = "social_media"
    WEB_CONTENT = "web_content"
    MOBILE_DEVICE = "mobile_device"
    CLOUD_DATA = "cloud_data"


class CustodyLevel(Enum):
    """Levels of custody protection"""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    FORENSIC = "forensic"
    MAXIMUM = "maximum"


class VerificationStatus(Enum):
    """Status of evidence verification"""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CORRUPTED = "corrupted"
    TAMPERED = "tampered"
    MISSING = "missing"


@dataclass
class CustodyParticipant:
    """Individual or system involved in custody chain"""
    id: str
    name: str
    role: str
    organization: str
    credentials: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None
    digital_signature: Optional[str] = None
    authorization_level: Optional[str] = None


@dataclass
class EvidenceItem:
    """Individual piece of evidence"""
    item_id: str
    evidence_type: EvidenceType
    description: str
    original_filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    hash_md5: Optional[str] = None
    hash_sha256: Optional[str] = None
    hash_sha512: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    modified_at: Optional[datetime.datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[Set[str]] = None
    classification: Optional[str] = None


@dataclass
class CustodyEvent:
    """Single event in chain of custody"""
    event_id: str
    timestamp: datetime.datetime
    action: CustodyAction
    participant: CustodyParticipant
    evidence_items: List[str]  # Evidence item IDs
    location: str
    purpose: str
    method: Optional[str] = None
    verification_hash: Optional[str] = None
    digital_signature: Optional[str] = None
    witness: Optional[CustodyParticipant] = None
    notes: Optional[str] = None
    system_info: Optional[Dict[str, Any]] = None
    environmental_conditions: Optional[Dict[str, Any]] = None


@dataclass
class CustodyChain:
    """Complete chain of custody for evidence"""
    chain_id: str
    case_number: str
    evidence_items: Dict[str, EvidenceItem]
    custody_events: List[CustodyEvent]
    current_custodian: CustodyParticipant
    custody_level: CustodyLevel
    created_at: datetime.datetime
    last_verified: Optional[datetime.datetime] = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    sealed: bool = False
    sealed_by: Optional[CustodyParticipant] = None
    sealed_at: Optional[datetime.datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class HashCalculator:
    """Calculate various hash types for evidence integrity"""
    
    @staticmethod
    def calculate_file_hashes(file_path: str) -> Dict[str, str]:
        """Calculate MD5, SHA-256, and SHA-512 hashes for a file"""
        hashes = {
            'md5': hashlib.md5(),
            'sha256': hashlib.sha256(),
            'sha512': hashlib.sha512()
        }
        
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                while chunk := f.read(8192):
                    for hash_obj in hashes.values():
                        hash_obj.update(chunk)
            
            return {
                'md5': hashes['md5'].hexdigest(),
                'sha256': hashes['sha256'].hexdigest(),
                'sha512': hashes['sha512'].hexdigest()
            }
        
        except Exception as e:
            logging.error(f"Error calculating hashes for {file_path}: {e}")
            raise
    
    @staticmethod
    def calculate_string_hashes(content: str) -> Dict[str, str]:
        """Calculate hashes for string content"""
        content_bytes = content.encode('utf-8')
        
        return {
            'md5': hashlib.md5(content_bytes).hexdigest(),
            'sha256': hashlib.sha256(content_bytes).hexdigest(),
            'sha512': hashlib.sha512(content_bytes).hexdigest()
        }
    
    @staticmethod
    def verify_file_integrity(file_path: str, expected_hashes: Dict[str, str]) -> Dict[str, bool]:
        """Verify file integrity against expected hashes"""
        current_hashes = HashCalculator.calculate_file_hashes(file_path)
        
        verification_results = {}
        for hash_type, expected_hash in expected_hashes.items():
            current_hash = current_hashes.get(hash_type)
            verification_results[hash_type] = (current_hash == expected_hash)
        
        return verification_results


class DigitalSignature:
    """Handle digital signatures for custody events"""
    
    def __init__(self, private_key: Optional[str] = None):
        self.private_key = private_key
    
    def sign_event(self, event: CustodyEvent) -> str:
        """Create digital signature for custody event"""
        # Simplified signature - in production would use proper cryptographic signing
        event_data = {
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'action': event.action.value,
            'participant_id': event.participant.id,
            'evidence_items': sorted(event.evidence_items),
            'verification_hash': event.verification_hash
        }
        
        event_json = json.dumps(event_data, sort_keys=True)
        signature_input = f"{event_json}{self.private_key or 'default_key'}"
        
        signature_hash = hashlib.sha256(signature_input.encode()).hexdigest()
        return base64.urlsafe_b64encode(signature_hash.encode()).decode()
    
    def verify_signature(self, event: CustodyEvent, signature: str) -> bool:
        """Verify digital signature of custody event"""
        expected_signature = self.sign_event(event)
        return signature == expected_signature


class CustodyTracker:
    """Main chain of custody tracking system"""
    
    def __init__(self, storage_backend: Optional[Any] = None):
        self.storage = storage_backend or {}
        self.custody_chains: Dict[str, CustodyChain] = {}
        self.digital_signer = DigitalSignature()
        self.hash_calculator = HashCalculator()
    
    def create_custody_chain(self, case_number: str, initial_custodian: CustodyParticipant,
                           custody_level: CustodyLevel = CustodyLevel.STANDARD) -> str:
        """Create new chain of custody"""
        chain_id = str(uuid.uuid4())
        
        custody_chain = CustodyChain(
            chain_id=chain_id,
            case_number=case_number,
            evidence_items={},
            custody_events=[],
            current_custodian=initial_custodian,
            custody_level=custody_level,
            created_at=datetime.datetime.utcnow(),
            verification_status=VerificationStatus.VERIFIED
        )
        
        self.custody_chains[chain_id] = custody_chain
        
        # Create initial custody event
        initial_event = self._create_custody_event(
            action=CustodyAction.CREATED,
            participant=initial_custodian,
            evidence_items=[],
            location="Evidence Management System",
            purpose="Chain of custody creation"
        )
        
        self._add_event_to_chain(chain_id, initial_event)
        
        logging.info(f"Created custody chain {chain_id} for case {case_number}")
        return chain_id
    
    def add_evidence_item(self, chain_id: str, evidence_type: EvidenceType,
                         description: str, file_path: Optional[str] = None,
                         custodian: Optional[CustodyParticipant] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add evidence item to custody chain"""
        if chain_id not in self.custody_chains:
            raise ValueError(f"Custody chain {chain_id} not found")
        
        chain = self.custody_chains[chain_id]
        
        if chain.sealed:
            raise ValueError(f"Cannot add evidence to sealed chain {chain_id}")
        
        item_id = str(uuid.uuid4())
        
        # Calculate hashes if file path provided
        hashes = {}
        file_info = {}
        
        if file_path:
            try:
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    hashes = self.hash_calculator.calculate_file_hashes(file_path)
                    file_info = {
                        'original_filename': file_path_obj.name,
                        'file_path': str(file_path_obj.absolute()),
                        'file_size': file_path_obj.stat().st_size,
                        'created_at': datetime.datetime.fromtimestamp(file_path_obj.stat().st_ctime),
                        'modified_at': datetime.datetime.fromtimestamp(file_path_obj.stat().st_mtime)
                    }
            except Exception as e:
                logging.warning(f"Could not process file {file_path}: {e}")
        
        # Create evidence item
        evidence_item = EvidenceItem(
            item_id=item_id,
            evidence_type=evidence_type,
            description=description,
            hash_md5=hashes.get('md5'),
            hash_sha256=hashes.get('sha256'),
            hash_sha512=hashes.get('sha512'),
            metadata=metadata,
            tags=set(),
            **file_info
        )
        
        chain.evidence_items[item_id] = evidence_item
        
        # Create custody event
        custodian = custodian or chain.current_custodian
        event = self._create_custody_event(
            action=CustodyAction.CREATED,
            participant=custodian,
            evidence_items=[item_id],
            location="Evidence Management System",
            purpose=f"Evidence item creation: {description}",
            verification_hash=hashes.get('sha256')
        )
        
        self._add_event_to_chain(chain_id, event)
        
        logging.info(f"Added evidence item {item_id} to chain {chain_id}")
        return item_id
    
    def transfer_custody(self, chain_id: str, from_custodian: CustodyParticipant,
                        to_custodian: CustodyParticipant, evidence_item_ids: Optional[List[str]] = None,
                        location: str = "Unknown", purpose: str = "Custody transfer",
                        witness: Optional[CustodyParticipant] = None) -> str:
        """Transfer custody of evidence items"""
        if chain_id not in self.custody_chains:
            raise ValueError(f"Custody chain {chain_id} not found")
        
        chain = self.custody_chains[chain_id]
        
        if chain.sealed:
            raise ValueError(f"Cannot transfer custody of sealed chain {chain_id}")
        
        # If no specific items specified, transfer all
        if evidence_item_ids is None:
            evidence_item_ids = list(chain.evidence_items.keys())
        
        # Validate evidence items exist
        for item_id in evidence_item_ids:
            if item_id not in chain.evidence_items:
                raise ValueError(f"Evidence item {item_id} not found in chain {chain_id}")
        
        # Create transfer event
        transfer_event = self._create_custody_event(
            action=CustodyAction.TRANSFERRED,
            participant=from_custodian,
            evidence_items=evidence_item_ids,
            location=location,
            purpose=purpose,
            witness=witness
        )
        
        # Create received event
        received_event = self._create_custody_event(
            action=CustodyAction.RECEIVED,
            participant=to_custodian,
            evidence_items=evidence_item_ids,
            location=location,
            purpose=purpose,
            witness=witness
        )
        
        # Add both events to chain
        transfer_event_id = self._add_event_to_chain(chain_id, transfer_event)
        received_event_id = self._add_event_to_chain(chain_id, received_event)
        
        # Update current custodian
        chain.current_custodian = to_custodian
        
        logging.info(f"Transferred custody in chain {chain_id} from {from_custodian.id} to {to_custodian.id}")
        return received_event_id
    
    def access_evidence(self, chain_id: str, evidence_item_ids: List[str],
                       accessor: CustodyParticipant, purpose: str,
                       location: str = "Unknown") -> str:
        """Record evidence access event"""
        if chain_id not in self.custody_chains:
            raise ValueError(f"Custody chain {chain_id} not found")
        
        chain = self.custody_chains[chain_id]
        
        # Validate evidence items exist
        for item_id in evidence_item_ids:
            if item_id not in chain.evidence_items:
                raise ValueError(f"Evidence item {item_id} not found in chain {chain_id}")
        
        # Create access event
        access_event = self._create_custody_event(
            action=CustodyAction.ACCESSED,
            participant=accessor,
            evidence_items=evidence_item_ids,
            location=location,
            purpose=purpose
        )
        
        event_id = self._add_event_to_chain(chain_id, access_event)
        
        logging.info(f"Recorded access to evidence items {evidence_item_ids} in chain {chain_id}")
        return event_id
    
    def verify_evidence_integrity(self, chain_id: str, 
                                evidence_item_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Verify integrity of evidence items"""
        if chain_id not in self.custody_chains:
            raise ValueError(f"Custody chain {chain_id} not found")
        
        chain = self.custody_chains[chain_id]
        
        if evidence_item_ids is None:
            evidence_item_ids = list(chain.evidence_items.keys())
        
        verification_results = {}
        
        for item_id in evidence_item_ids:
            if item_id not in chain.evidence_items:
                verification_results[item_id] = {
                    'status': VerificationStatus.MISSING,
                    'details': 'Evidence item not found'
                }
                continue
            
            evidence_item = chain.evidence_items[item_id]
            
            if not evidence_item.file_path or not Path(evidence_item.file_path).exists():
                verification_results[item_id] = {
                    'status': VerificationStatus.MISSING,
                    'details': 'File not found'
                }
                continue
            
            # Verify hashes
            expected_hashes = {}
            if evidence_item.hash_md5:
                expected_hashes['md5'] = evidence_item.hash_md5
            if evidence_item.hash_sha256:
                expected_hashes['sha256'] = evidence_item.hash_sha256
            if evidence_item.hash_sha512:
                expected_hashes['sha512'] = evidence_item.hash_sha512
            
            if not expected_hashes:
                verification_results[item_id] = {
                    'status': VerificationStatus.UNVERIFIED,
                    'details': 'No original hashes available'
                }
                continue
            
            try:
                hash_verification = self.hash_calculator.verify_file_integrity(
                    evidence_item.file_path, expected_hashes
                )
                
                if all(hash_verification.values()):
                    status = VerificationStatus.VERIFIED
                    details = 'All hashes match'
                else:
                    status = VerificationStatus.CORRUPTED
                    failed_hashes = [h for h, result in hash_verification.items() if not result]
                    details = f'Hash mismatch: {failed_hashes}'
                
                verification_results[item_id] = {
                    'status': status,
                    'details': details,
                    'hash_verification': hash_verification
                }
                
            except Exception as e:
                verification_results[item_id] = {
                    'status': VerificationStatus.CORRUPTED,
                    'details': f'Verification error: {str(e)}'
                }
        
        # Update chain verification status
        all_verified = all(r['status'] == VerificationStatus.VERIFIED for r in verification_results.values())
        if all_verified:
            chain.verification_status = VerificationStatus.VERIFIED
        else:
            chain.verification_status = VerificationStatus.CORRUPTED
        
        chain.last_verified = datetime.datetime.utcnow()
        
        return verification_results
    
    def seal_custody_chain(self, chain_id: str, sealing_authority: CustodyParticipant,
                          reason: str = "Legal proceedings completed") -> str:
        """Seal custody chain to prevent further modifications"""
        if chain_id not in self.custody_chains:
            raise ValueError(f"Custody chain {chain_id} not found")
        
        chain = self.custody_chains[chain_id]
        
        if chain.sealed:
            raise ValueError(f"Chain {chain_id} is already sealed")
        
        # Create sealing event
        seal_event = self._create_custody_event(
            action=CustodyAction.SEALED,
            participant=sealing_authority,
            evidence_items=list(chain.evidence_items.keys()),
            location="Evidence Management System",
            purpose=f"Chain sealed: {reason}"
        )
        
        event_id = self._add_event_to_chain(chain_id, seal_event)
        
        # Mark chain as sealed
        chain.sealed = True
        chain.sealed_by = sealing_authority
        chain.sealed_at = datetime.datetime.utcnow()
        
        logging.info(f"Sealed custody chain {chain_id}")
        return event_id
    
    def generate_custody_report(self, chain_id: str) -> Dict[str, Any]:
        """Generate comprehensive custody report"""
        if chain_id not in self.custody_chains:
            raise ValueError(f"Custody chain {chain_id} not found")
        
        chain = self.custody_chains[chain_id]
        
        # Verify current integrity
        verification_results = self.verify_evidence_integrity(chain_id)
        
        # Analyze custody events
        event_analysis = self._analyze_custody_events(chain.custody_events)
        
        report = {
            'chain_summary': {
                'chain_id': chain.chain_id,
                'case_number': chain.case_number,
                'created_at': chain.created_at.isoformat(),
                'custody_level': chain.custody_level.value,
                'current_custodian': asdict(chain.current_custodian),
                'sealed': chain.sealed,
                'sealed_at': chain.sealed_at.isoformat() if chain.sealed_at else None,
                'verification_status': chain.verification_status.value,
                'last_verified': chain.last_verified.isoformat() if chain.last_verified else None
            },
            'evidence_items': {
                item_id: {
                    **asdict(item),
                    'tags': list(item.tags) if item.tags else [],
                    'created_at': item.created_at.isoformat() if item.created_at else None,
                    'modified_at': item.modified_at.isoformat() if item.modified_at else None
                }
                for item_id, item in chain.evidence_items.items()
            },
            'custody_events': [
                {
                    **asdict(event),
                    'timestamp': event.timestamp.isoformat(),
                    'action': event.action.value
                }
                for event in chain.custody_events
            ],
            'verification_results': {
                item_id: {
                    **result,
                    'status': result['status'].value if isinstance(result['status'], VerificationStatus) else result['status']
                }
                for item_id, result in verification_results.items()
            },
            'event_analysis': event_analysis,
            'report_generated_at': datetime.datetime.utcnow().isoformat()
        }
        
        return report
    
    def export_custody_chain(self, chain_id: str, format: str = 'json') -> str:
        """Export custody chain in specified format"""
        report = self.generate_custody_report(chain_id)
        
        if format.lower() == 'json':
            return json.dumps(report, indent=2)
        
        elif format.lower() == 'csv':
            # Simplified CSV export for events
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow([
                'Event ID', 'Timestamp', 'Action', 'Participant', 'Evidence Items',
                'Location', 'Purpose', 'Verification Hash'
            ])
            
            # Write events
            for event in report['custody_events']:
                writer.writerow([
                    event['event_id'],
                    event['timestamp'],
                    event['action'],
                    event['participant']['name'],
                    '; '.join(event['evidence_items']),
                    event['location'],
                    event['purpose'],
                    event.get('verification_hash', '')
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _create_custody_event(self, action: CustodyAction, participant: CustodyParticipant,
                            evidence_items: List[str], location: str, purpose: str,
                            method: Optional[str] = None, witness: Optional[CustodyParticipant] = None,
                            verification_hash: Optional[str] = None) -> CustodyEvent:
        """Create a custody event with proper verification"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow()
        
        # Collect system information
        system_info = {
            'hostname': 'evidence_system',  # Would get actual hostname
            'user_agent': 'Chain of Custody System v1.0',
            'ip_address': '127.0.0.1'  # Would get actual IP
        }
        
        event = CustodyEvent(
            event_id=event_id,
            timestamp=timestamp,
            action=action,
            participant=participant,
            evidence_items=evidence_items,
            location=location,
            purpose=purpose,
            method=method,
            verification_hash=verification_hash,
            witness=witness,
            system_info=system_info
        )
        
        # Create digital signature
        event.digital_signature = self.digital_signer.sign_event(event)
        
        return event
    
    def _add_event_to_chain(self, chain_id: str, event: CustodyEvent) -> str:
        """Add event to custody chain with validation"""
        if chain_id not in self.custody_chains:
            raise ValueError(f"Custody chain {chain_id} not found")
        
        chain = self.custody_chains[chain_id]
        
        # Verify digital signature
        if not self.digital_signer.verify_signature(event, event.digital_signature):
            raise ValueError("Invalid digital signature on custody event")
        
        chain.custody_events.append(event)
        
        return event.event_id
    
    def _analyze_custody_events(self, events: List[CustodyEvent]) -> Dict[str, Any]:
        """Analyze custody events for reporting"""
        analysis = {
            'total_events': len(events),
            'events_by_action': {},
            'unique_participants': set(),
            'custody_transfers': 0,
            'access_events': 0,
            'verification_events': 0,
            'timeline_summary': {
                'first_event': None,
                'last_event': None,
                'duration_days': 0
            }
        }
        
        if not events:
            return analysis
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        analysis['timeline_summary']['first_event'] = sorted_events[0].timestamp.isoformat()
        analysis['timeline_summary']['last_event'] = sorted_events[-1].timestamp.isoformat()
        analysis['timeline_summary']['duration_days'] = (
            sorted_events[-1].timestamp - sorted_events[0].timestamp
        ).days
        
        for event in events:
            # Count by action
            action = event.action.value
            analysis['events_by_action'][action] = analysis['events_by_action'].get(action, 0) + 1
            
            # Track participants
            analysis['unique_participants'].add(event.participant.id)
            
            # Special event counting
            if event.action == CustodyAction.TRANSFERRED:
                analysis['custody_transfers'] += 1
            elif event.action == CustodyAction.ACCESSED:
                analysis['access_events'] += 1
            elif event.action == CustodyAction.VERIFIED:
                analysis['verification_events'] += 1
        
        # Convert set to list for JSON serialization
        analysis['unique_participants'] = len(analysis['unique_participants'])
        
        return analysis
    
    def get_custody_chain(self, chain_id: str) -> Optional[CustodyChain]:
        """Get custody chain by ID"""
        return self.custody_chains.get(chain_id)
    
    def list_custody_chains(self, case_number: Optional[str] = None) -> List[str]:
        """List all custody chain IDs, optionally filtered by case number"""
        if case_number:
            return [
                chain_id for chain_id, chain in self.custody_chains.items()
                if chain.case_number == case_number
            ]
        else:
            return list(self.custody_chains.keys())
    
    def search_evidence(self, query: str, chain_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for evidence items across custody chains"""
        results = []
        
        search_chains = chain_ids or list(self.custody_chains.keys())
        query_lower = query.lower()
        
        for chain_id in search_chains:
            chain = self.custody_chains.get(chain_id)
            if not chain:
                continue
            
            for item_id, evidence_item in chain.evidence_items.items():
                # Search in description, filename, and tags
                searchable_text = [
                    evidence_item.description.lower(),
                    evidence_item.original_filename.lower() if evidence_item.original_filename else "",
                    " ".join(evidence_item.tags).lower() if evidence_item.tags else ""
                ]
                
                if any(query_lower in text for text in searchable_text):
                    results.append({
                        'chain_id': chain_id,
                        'case_number': chain.case_number,
                        'item_id': item_id,
                        'evidence_item': asdict(evidence_item)
                    })
        
        return results