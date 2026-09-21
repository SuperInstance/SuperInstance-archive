from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union, Any
from enum import Enum
import json
import hashlib
import re
from pathlib import Path


class MatterStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    ON_HOLD = "on_hold"
    ARCHIVED = "archived"


class MatterType(Enum):
    LITIGATION = "litigation"
    REGULATORY = "regulatory"
    COMPLIANCE = "compliance"
    TRANSACTION = "transaction"
    EMPLOYMENT = "employment"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    INVESTIGATION = "investigation"
    CONTRACT_DISPUTE = "contract_dispute"
    MERGER_ACQUISITION = "merger_acquisition"
    BANKRUPTCY = "bankruptcy"


class ParticipantRole(Enum):
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    COUNSEL = "counsel"
    WITNESS = "witness"
    EXPERT = "expert"
    THIRD_PARTY = "third_party"
    REGULATORY_BODY = "regulatory_body"
    COUNTERPARTY = "counterparty"


class DocumentType(Enum):
    PLEADING = "pleading"
    MOTION = "motion"
    BRIEF = "brief"
    CONTRACT = "contract"
    CORRESPONDENCE = "correspondence"
    DISCOVERY = "discovery"
    EVIDENCE = "evidence"
    EXPERT_REPORT = "expert_report"
    DEPOSITION = "deposition"
    SETTLEMENT = "settlement"


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


@dataclass
class MatterParticipant:
    participant_id: str
    name: str
    role: ParticipantRole
    organization: str
    contact_email: str
    contact_phone: str = ""
    address: str = ""
    attorney: Optional[str] = None
    notes: str = ""
    active: bool = True


@dataclass
class MatterDocument:
    document_id: str
    title: str
    document_type: DocumentType
    file_path: str
    created_date: datetime
    author: str
    description: str = ""
    version: str = "1.0"
    confidential: bool = False
    privileged: bool = False
    work_product: bool = False
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash_value: str = ""


@dataclass
class MatterTask:
    task_id: str
    title: str
    description: str
    assigned_to: str
    created_by: str
    created_date: datetime
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.NOT_STARTED
    completion_date: Optional[datetime] = None
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class MatterEvent:
    event_id: str
    title: str
    description: str
    event_date: datetime
    event_type: str
    location: str = ""
    participants: List[str] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)
    recurring: bool = False
    reminder_minutes: int = 30
    calendar_link: str = ""


@dataclass
class BillingEntry:
    entry_id: str
    matter_id: str
    attorney: str
    date: datetime
    hours: float
    rate: float
    description: str
    task_code: str = ""
    billable: bool = True
    client_matter_number: str = ""


@dataclass
class Matter:
    matter_id: str
    title: str
    description: str
    matter_type: MatterType
    client: str
    created_by: str
    created_date: datetime
    status: MatterStatus = MatterStatus.ACTIVE
    open_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    statute_of_limitations: Optional[datetime] = None
    participants: List[MatterParticipant] = field(default_factory=list)
    documents: List[MatterDocument] = field(default_factory=list)
    tasks: List[MatterTask] = field(default_factory=list)
    events: List[MatterEvent] = field(default_factory=list)
    billing_entries: List[BillingEntry] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    conflicts_checked: bool = False
    budget_amount: float = 0.0
    actual_cost: float = 0.0
    outside_counsel: List[str] = field(default_factory=list)
    related_matters: List[str] = field(default_factory=list)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)


class DocumentVersionControl:
    def __init__(self):
        self.versions: Dict[str, List[MatterDocument]] = {}
    
    def add_document_version(self, document: MatterDocument) -> bool:
        base_id = document.document_id.split('_v')[0]
        
        if base_id not in self.versions:
            self.versions[base_id] = []
        
        # Calculate hash for integrity
        if document.file_path and Path(document.file_path).exists():
            document.hash_value = self._calculate_file_hash(document.file_path)
        
        self.versions[base_id].append(document)
        return True
    
    def get_latest_version(self, base_document_id: str) -> Optional[MatterDocument]:
        if base_document_id not in self.versions:
            return None
        
        versions = sorted(self.versions[base_document_id], 
                         key=lambda d: d.created_date, reverse=True)
        return versions[0] if versions else None
    
    def get_version_history(self, base_document_id: str) -> List[MatterDocument]:
        if base_document_id not in self.versions:
            return []
        
        return sorted(self.versions[base_document_id], 
                     key=lambda d: d.created_date, reverse=True)
    
    def compare_versions(self, doc_id1: str, doc_id2: str) -> Dict[str, Any]:
        doc1 = self._find_document_by_id(doc_id1)
        doc2 = self._find_document_by_id(doc_id2)
        
        if not doc1 or not doc2:
            return {}
        
        return {
            "document_1": {
                "id": doc1.document_id,
                "version": doc1.version,
                "created_date": doc1.created_date.isoformat(),
                "author": doc1.author,
                "hash": doc1.hash_value
            },
            "document_2": {
                "id": doc2.document_id,
                "version": doc2.version,
                "created_date": doc2.created_date.isoformat(),
                "author": doc2.author,
                "hash": doc2.hash_value
            },
            "hash_match": doc1.hash_value == doc2.hash_value,
            "same_author": doc1.author == doc2.author,
            "time_difference_hours": (doc2.created_date - doc1.created_date).total_seconds() / 3600
        }
    
    def _find_document_by_id(self, document_id: str) -> Optional[MatterDocument]:
        for versions_list in self.versions.values():
            for doc in versions_list:
                if doc.document_id == document_id:
                    return doc
        return None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""


class ConflictChecker:
    def __init__(self):
        self.known_conflicts: Dict[str, List[str]] = {}
        self.entities_database: Dict[str, Set[str]] = {}
    
    def check_conflicts(self, matter: Matter) -> Dict[str, Any]:
        conflicts_found = []
        potential_conflicts = []
        
        # Check client conflicts
        client_conflicts = self._check_client_conflicts(matter.client)
        conflicts_found.extend(client_conflicts)
        
        # Check participant conflicts
        for participant in matter.participants:
            participant_conflicts = self._check_participant_conflicts(participant)
            conflicts_found.extend(participant_conflicts)
        
        # Check matter type conflicts
        type_conflicts = self._check_matter_type_conflicts(matter.matter_type, matter.client)
        potential_conflicts.extend(type_conflicts)
        
        return {
            "matter_id": matter.matter_id,
            "conflicts_found": conflicts_found,
            "potential_conflicts": potential_conflicts,
            "check_date": datetime.now().isoformat(),
            "requires_review": len(conflicts_found) > 0 or len(potential_conflicts) > 0
        }
    
    def _check_client_conflicts(self, client: str) -> List[str]:
        conflicts = []
        
        if client in self.known_conflicts:
            for conflict in self.known_conflicts[client]:
                conflicts.append(f"Known conflict with client: {conflict}")
        
        return conflicts
    
    def _check_participant_conflicts(self, participant: MatterParticipant) -> List[str]:
        conflicts = []
        
        if participant.name in self.known_conflicts:
            for conflict in self.known_conflicts[participant.name]:
                conflicts.append(f"Known conflict with participant {participant.name}: {conflict}")
        
        if participant.organization in self.known_conflicts:
            for conflict in self.known_conflicts[participant.organization]:
                conflicts.append(f"Known conflict with organization {participant.organization}: {conflict}")
        
        return conflicts
    
    def _check_matter_type_conflicts(self, matter_type: MatterType, client: str) -> List[str]:
        potential_conflicts = []
        
        if matter_type == MatterType.LITIGATION:
            # Check for opposing counsel relationships
            if client in self.entities_database:
                related_entities = self.entities_database[client]
                for entity in related_entities:
                    potential_conflicts.append(f"Potential conflict: litigation involving related entity {entity}")
        
        return potential_conflicts
    
    def add_known_conflict(self, entity: str, conflict_description: str):
        if entity not in self.known_conflicts:
            self.known_conflicts[entity] = []
        self.known_conflicts[entity].append(conflict_description)
    
    def add_entity_relationship(self, entity1: str, entity2: str):
        if entity1 not in self.entities_database:
            self.entities_database[entity1] = set()
        if entity2 not in self.entities_database:
            self.entities_database[entity2] = set()
        
        self.entities_database[entity1].add(entity2)
        self.entities_database[entity2].add(entity1)


class MatterTimelineGenerator:
    def generate_timeline(self, matter: Matter) -> List[Dict[str, Any]]:
        timeline_events = []
        
        # Add matter creation
        timeline_events.append({
            "date": matter.created_date,
            "type": "matter_created",
            "title": "Matter Created",
            "description": f"Matter '{matter.title}' created by {matter.created_by}",
            "details": {"matter_type": matter.matter_type.value}
        })
        
        # Add document events
        for doc in matter.documents:
            timeline_events.append({
                "date": doc.created_date,
                "type": "document_added",
                "title": f"Document Added: {doc.title}",
                "description": f"Document '{doc.title}' created by {doc.author}",
                "details": {
                    "document_id": doc.document_id,
                    "document_type": doc.document_type.value,
                    "confidential": doc.confidential,
                    "privileged": doc.privileged
                }
            })
        
        # Add task events
        for task in matter.tasks:
            timeline_events.append({
                "date": task.created_date,
                "type": "task_created",
                "title": f"Task Created: {task.title}",
                "description": f"Task assigned to {task.assigned_to}",
                "details": {
                    "task_id": task.task_id,
                    "priority": task.priority.value,
                    "status": task.status.value,
                    "due_date": task.due_date.isoformat() if task.due_date else None
                }
            })
            
            if task.completion_date:
                timeline_events.append({
                    "date": task.completion_date,
                    "type": "task_completed",
                    "title": f"Task Completed: {task.title}",
                    "description": f"Task completed by {task.assigned_to}",
                    "details": {
                        "task_id": task.task_id,
                        "actual_hours": task.actual_hours
                    }
                })
        
        # Add calendar events
        for event in matter.events:
            timeline_events.append({
                "date": event.event_date,
                "type": "calendar_event",
                "title": event.title,
                "description": event.description,
                "details": {
                    "event_id": event.event_id,
                    "location": event.location,
                    "participants": event.participants
                }
            })
        
        # Add status changes from audit trail
        for audit_entry in matter.audit_trail:
            if audit_entry.get("action") == "status_changed":
                timeline_events.append({
                    "date": datetime.fromisoformat(audit_entry["timestamp"]),
                    "type": "status_change",
                    "title": "Matter Status Changed",
                    "description": f"Status changed from {audit_entry['details'].get('old_status')} to {audit_entry['details'].get('new_status')}",
                    "details": audit_entry["details"]
                })
        
        # Sort by date
        timeline_events.sort(key=lambda x: x["date"])
        
        # Convert dates to ISO format for JSON serialization
        for event in timeline_events:
            event["date"] = event["date"].isoformat()
        
        return timeline_events


class MatterReportGenerator:
    def generate_matter_summary(self, matter: Matter) -> Dict[str, Any]:
        total_tasks = len(matter.tasks)
        completed_tasks = len([t for t in matter.tasks if t.status == TaskStatus.COMPLETED])
        overdue_tasks = len([t for t in matter.tasks if t.due_date and t.due_date < datetime.now() and t.status != TaskStatus.COMPLETED])
        
        total_hours = sum(entry.hours for entry in matter.billing_entries)
        total_billed = sum(entry.hours * entry.rate for entry in matter.billing_entries if entry.billable)
        
        return {
            "matter_id": matter.matter_id,
            "title": matter.title,
            "client": matter.client,
            "matter_type": matter.matter_type.value,
            "status": matter.status.value,
            "created_date": matter.created_date.isoformat(),
            "open_date": matter.open_date.isoformat() if matter.open_date else None,
            "close_date": matter.close_date.isoformat() if matter.close_date else None,
            "participants": {
                "total": len(matter.participants),
                "by_role": self._count_participants_by_role(matter.participants)
            },
            "documents": {
                "total": len(matter.documents),
                "by_type": self._count_documents_by_type(matter.documents),
                "confidential": len([d for d in matter.documents if d.confidential]),
                "privileged": len([d for d in matter.documents if d.privileged])
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
                "overdue": overdue_tasks
            },
            "billing": {
                "total_hours": total_hours,
                "total_billed": total_billed,
                "budget_amount": matter.budget_amount,
                "budget_utilization": (total_billed / matter.budget_amount) if matter.budget_amount > 0 else 0
            },
            "events": len(matter.events),
            "generated_date": datetime.now().isoformat()
        }
    
    def generate_financial_report(self, matter: Matter) -> Dict[str, Any]:
        billing_by_attorney = {}
        billing_by_month = {}
        
        for entry in matter.billing_entries:
            # Group by attorney
            if entry.attorney not in billing_by_attorney:
                billing_by_attorney[entry.attorney] = {"hours": 0, "amount": 0}
            billing_by_attorney[entry.attorney]["hours"] += entry.hours
            billing_by_attorney[entry.attorney]["amount"] += entry.hours * entry.rate
            
            # Group by month
            month_key = entry.date.strftime("%Y-%m")
            if month_key not in billing_by_month:
                billing_by_month[month_key] = {"hours": 0, "amount": 0}
            billing_by_month[month_key]["hours"] += entry.hours
            billing_by_month[month_key]["amount"] += entry.hours * entry.rate
        
        total_billed = sum(entry.hours * entry.rate for entry in matter.billing_entries if entry.billable)
        
        return {
            "matter_id": matter.matter_id,
            "billing_by_attorney": billing_by_attorney,
            "billing_by_month": billing_by_month,
            "total_billed": total_billed,
            "budget_amount": matter.budget_amount,
            "budget_remaining": matter.budget_amount - total_billed,
            "budget_utilization_percent": (total_billed / matter.budget_amount * 100) if matter.budget_amount > 0 else 0,
            "generated_date": datetime.now().isoformat()
        }
    
    def _count_participants_by_role(self, participants: List[MatterParticipant]) -> Dict[str, int]:
        role_counts = {}
        for participant in participants:
            role = participant.role.value
            role_counts[role] = role_counts.get(role, 0) + 1
        return role_counts
    
    def _count_documents_by_type(self, documents: List[MatterDocument]) -> Dict[str, int]:
        type_counts = {}
        for document in documents:
            doc_type = document.document_type.value
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        return type_counts


class MatterManager:
    def __init__(self):
        self.matters: Dict[str, Matter] = {}
        self.document_version_control = DocumentVersionControl()
        self.conflict_checker = ConflictChecker()
        self.timeline_generator = MatterTimelineGenerator()
        self.report_generator = MatterReportGenerator()
    
    def create_matter(self, matter_id: str, title: str, description: str, 
                     matter_type: MatterType, client: str, created_by: str) -> Matter:
        matter = Matter(
            matter_id=matter_id,
            title=title,
            description=description,
            matter_type=matter_type,
            client=client,
            created_by=created_by,
            created_date=datetime.now()
        )
        
        self.matters[matter_id] = matter
        self._add_audit_entry(matter, "matter_created", {"created_by": created_by})
        return matter
    
    def add_participant(self, matter_id: str, participant: MatterParticipant) -> bool:
        if matter_id not in self.matters:
            return False
        
        matter = self.matters[matter_id]
        
        # Check for duplicate participant
        existing_ids = {p.participant_id for p in matter.participants}
        if participant.participant_id in existing_ids:
            return False
        
        matter.participants.append(participant)
        self._add_audit_entry(matter, "participant_added", {"participant_id": participant.participant_id})
        return True
    
    def add_document(self, matter_id: str, document: MatterDocument) -> bool:
        if matter_id not in self.matters:
            return False
        
        matter = self.matters[matter_id]
        matter.documents.append(document)
        
        # Add to version control
        self.document_version_control.add_document_version(document)
        
        self._add_audit_entry(matter, "document_added", {
            "document_id": document.document_id,
            "document_type": document.document_type.value
        })
        return True
    
    def add_task(self, matter_id: str, task: MatterTask) -> bool:
        if matter_id not in self.matters:
            return False
        
        matter = self.matters[matter_id]
        matter.tasks.append(task)
        
        self._add_audit_entry(matter, "task_added", {
            "task_id": task.task_id,
            "assigned_to": task.assigned_to
        })
        return True
    
    def update_task_status(self, matter_id: str, task_id: str, new_status: TaskStatus) -> bool:
        if matter_id not in self.matters:
            return False
        
        matter = self.matters[matter_id]
        task = self._find_task(matter, task_id)
        
        if not task:
            return False
        
        old_status = task.status
        task.status = new_status
        
        if new_status == TaskStatus.COMPLETED:
            task.completion_date = datetime.now()
        
        self._add_audit_entry(matter, "task_status_updated", {
            "task_id": task_id,
            "old_status": old_status.value,
            "new_status": new_status.value
        })
        return True
    
    def add_billing_entry(self, matter_id: str, billing_entry: BillingEntry) -> bool:
        if matter_id not in self.matters:
            return False
        
        matter = self.matters[matter_id]
        billing_entry.matter_id = matter_id
        matter.billing_entries.append(billing_entry)
        
        # Update actual cost
        matter.actual_cost = sum(entry.hours * entry.rate for entry in matter.billing_entries)
        
        self._add_audit_entry(matter, "billing_entry_added", {
            "entry_id": billing_entry.entry_id,
            "hours": billing_entry.hours,
            "amount": billing_entry.hours * billing_entry.rate
        })
        return True
    
    def change_matter_status(self, matter_id: str, new_status: MatterStatus) -> bool:
        if matter_id not in self.matters:
            return False
        
        matter = self.matters[matter_id]
        old_status = matter.status
        matter.status = new_status
        
        if new_status == MatterStatus.ACTIVE and not matter.open_date:
            matter.open_date = datetime.now()
        elif new_status == MatterStatus.CLOSED:
            matter.close_date = datetime.now()
        
        self._add_audit_entry(matter, "status_changed", {
            "old_status": old_status.value,
            "new_status": new_status.value
        })
        return True
    
    def run_conflict_check(self, matter_id: str) -> Dict[str, Any]:
        if matter_id not in self.matters:
            return {}
        
        matter = self.matters[matter_id]
        conflict_result = self.conflict_checker.check_conflicts(matter)
        
        matter.conflicts_checked = True
        self._add_audit_entry(matter, "conflict_check_performed", conflict_result)
        
        return conflict_result
    
    def generate_matter_timeline(self, matter_id: str) -> List[Dict[str, Any]]:
        if matter_id not in self.matters:
            return []
        
        matter = self.matters[matter_id]
        return self.timeline_generator.generate_timeline(matter)
    
    def generate_matter_summary(self, matter_id: str) -> Dict[str, Any]:
        if matter_id not in self.matters:
            return {}
        
        matter = self.matters[matter_id]
        return self.report_generator.generate_matter_summary(matter)
    
    def generate_financial_report(self, matter_id: str) -> Dict[str, Any]:
        if matter_id not in self.matters:
            return {}
        
        matter = self.matters[matter_id]
        return self.report_generator.generate_financial_report(matter)
    
    def search_matters(self, query: str, search_fields: List[str] = None) -> List[Dict[str, Any]]:
        if search_fields is None:
            search_fields = ["title", "description", "client", "tags"]
        
        results = []
        query_lower = query.lower()
        
        for matter in self.matters.values():
            match_found = False
            
            for field in search_fields:
                if field == "title" and query_lower in matter.title.lower():
                    match_found = True
                elif field == "description" and query_lower in matter.description.lower():
                    match_found = True
                elif field == "client" and query_lower in matter.client.lower():
                    match_found = True
                elif field == "tags" and any(query_lower in tag.lower() for tag in matter.tags):
                    match_found = True
            
            if match_found:
                results.append({
                    "matter_id": matter.matter_id,
                    "title": matter.title,
                    "client": matter.client,
                    "matter_type": matter.matter_type.value,
                    "status": matter.status.value,
                    "created_date": matter.created_date.isoformat()
                })
        
        return results
    
    def get_matters_by_status(self, status: MatterStatus) -> List[Matter]:
        return [matter for matter in self.matters.values() if matter.status == status]
    
    def get_overdue_tasks(self, matter_id: Optional[str] = None) -> List[Dict[str, Any]]:
        overdue_tasks = []
        matters_to_check = [self.matters[matter_id]] if matter_id and matter_id in self.matters else self.matters.values()
        
        for matter in matters_to_check:
            for task in matter.tasks:
                if (task.due_date and task.due_date < datetime.now() and 
                    task.status != TaskStatus.COMPLETED and task.status != TaskStatus.CANCELLED):
                    overdue_tasks.append({
                        "matter_id": matter.matter_id,
                        "matter_title": matter.title,
                        "task_id": task.task_id,
                        "task_title": task.title,
                        "assigned_to": task.assigned_to,
                        "due_date": task.due_date.isoformat(),
                        "days_overdue": (datetime.now() - task.due_date).days,
                        "priority": task.priority.value
                    })
        
        return sorted(overdue_tasks, key=lambda x: x["days_overdue"], reverse=True)
    
    def export_matter_data(self, matter_id: str, format_type: str = "json") -> str:
        if matter_id not in self.matters:
            return ""
        
        matter = self.matters[matter_id]
        
        if format_type == "json":
            return self._export_to_json(matter)
        else:
            return ""
    
    def _export_to_json(self, matter: Matter) -> str:
        export_data = {
            "matter_id": matter.matter_id,
            "title": matter.title,
            "description": matter.description,
            "matter_type": matter.matter_type.value,
            "client": matter.client,
            "created_by": matter.created_by,
            "created_date": matter.created_date.isoformat(),
            "status": matter.status.value,
            "open_date": matter.open_date.isoformat() if matter.open_date else None,
            "close_date": matter.close_date.isoformat() if matter.close_date else None,
            "participants": [
                {
                    "participant_id": p.participant_id,
                    "name": p.name,
                    "role": p.role.value,
                    "organization": p.organization,
                    "contact_email": p.contact_email
                } for p in matter.participants
            ],
            "documents": [
                {
                    "document_id": d.document_id,
                    "title": d.title,
                    "document_type": d.document_type.value,
                    "created_date": d.created_date.isoformat(),
                    "author": d.author,
                    "confidential": d.confidential,
                    "privileged": d.privileged
                } for d in matter.documents
            ],
            "tasks": [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "assigned_to": t.assigned_to,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "due_date": t.due_date.isoformat() if t.due_date else None
                } for t in matter.tasks
            ],
            "billing_summary": {
                "total_hours": sum(e.hours for e in matter.billing_entries),
                "total_amount": sum(e.hours * e.rate for e in matter.billing_entries),
                "budget_amount": matter.budget_amount
            },
            "metadata": matter.metadata,
            "audit_trail_count": len(matter.audit_trail)
        }
        
        return json.dumps(export_data, indent=2)
    
    def _find_task(self, matter: Matter, task_id: str) -> Optional[MatterTask]:
        for task in matter.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def _add_audit_entry(self, matter: Matter, action: str, details: Dict[str, Any]):
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "matter_id": matter.matter_id
        }
        matter.audit_trail.append(audit_entry)


class MatterDashboard:
    def __init__(self, matter_manager: MatterManager):
        self.matter_manager = matter_manager
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        all_matters = list(self.matter_manager.matters.values())
        
        if not all_matters:
            return self._empty_dashboard()
        
        status_counts = {}
        for status in MatterStatus:
            status_counts[status.value] = len([m for m in all_matters if m.status == status])
        
        type_counts = {}
        for matter_type in MatterType:
            type_counts[matter_type.value] = len([m for m in all_matters if m.matter_type == matter_type])
        
        overdue_tasks = self.matter_manager.get_overdue_tasks()
        
        total_budget = sum(m.budget_amount for m in all_matters)
        total_actual = sum(m.actual_cost for m in all_matters)
        
        return {
            "total_matters": len(all_matters),
            "matters_by_status": status_counts,
            "matters_by_type": type_counts,
            "total_overdue_tasks": len(overdue_tasks),
            "critical_overdue_tasks": len([t for t in overdue_tasks if t["priority"] == "critical"]),
            "financial_summary": {
                "total_budget": total_budget,
                "total_actual": total_actual,
                "budget_utilization": (total_actual / total_budget * 100) if total_budget > 0 else 0
            },
            "recent_activities": self._get_recent_activities(all_matters),
            "generated_at": datetime.now().isoformat()
        }
    
    def _empty_dashboard(self) -> Dict[str, Any]:
        return {
            "total_matters": 0,
            "matters_by_status": {status.value: 0 for status in MatterStatus},
            "matters_by_type": {matter_type.value: 0 for matter_type in MatterType},
            "total_overdue_tasks": 0,
            "critical_overdue_tasks": 0,
            "financial_summary": {"total_budget": 0, "total_actual": 0, "budget_utilization": 0},
            "recent_activities": [],
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_recent_activities(self, matters: List[Matter], limit: int = 10) -> List[Dict[str, Any]]:
        all_activities = []
        
        for matter in matters:
            for audit_entry in matter.audit_trail[-5:]:  # Get last 5 activities per matter
                all_activities.append({
                    "matter_id": matter.matter_id,
                    "matter_title": matter.title,
                    "timestamp": audit_entry["timestamp"],
                    "action": audit_entry["action"],
                    "details": audit_entry["details"]
                })
        
        # Sort by timestamp and limit
        all_activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_activities[:limit]