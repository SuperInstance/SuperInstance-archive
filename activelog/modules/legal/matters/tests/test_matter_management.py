import pytest
from datetime import datetime, timedelta
from modules.legal.matters.src.matter_management import (
    Matter, MatterParticipant, MatterDocument, MatterTask, MatterEvent, BillingEntry,
    MatterStatus, MatterType, ParticipantRole, DocumentType, TaskPriority, TaskStatus,
    MatterManager, DocumentVersionControl, ConflictChecker, MatterTimelineGenerator,
    MatterReportGenerator, MatterDashboard
)


class TestMatter:
    def test_matter_creation(self):
        matter = Matter(
            matter_id="MTR-001",
            title="Contract Dispute Case",
            description="Dispute over software licensing agreement",
            matter_type=MatterType.LITIGATION,
            client="Tech Corp Inc",
            created_by="attorney@firm.com",
            created_date=datetime.now()
        )
        
        assert matter.matter_id == "MTR-001"
        assert matter.title == "Contract Dispute Case"
        assert matter.matter_type == MatterType.LITIGATION
        assert matter.status == MatterStatus.ACTIVE
        assert len(matter.participants) == 0
        assert len(matter.documents) == 0
        assert len(matter.tasks) == 0

    def test_matter_participant_creation(self):
        participant = MatterParticipant(
            participant_id="PART-001",
            name="John Doe",
            role=ParticipantRole.PLAINTIFF,
            organization="Tech Corp Inc",
            contact_email="john.doe@techcorp.com",
            contact_phone="555-0123"
        )
        
        assert participant.participant_id == "PART-001"
        assert participant.name == "John Doe"
        assert participant.role == ParticipantRole.PLAINTIFF
        assert participant.active is True

    def test_matter_document_creation(self):
        document = MatterDocument(
            document_id="DOC-001",
            title="Software License Agreement",
            document_type=DocumentType.CONTRACT,
            file_path="/documents/license_agreement.pdf",
            created_date=datetime.now(),
            author="legal@firm.com",
            confidential=True
        )
        
        assert document.document_id == "DOC-001"
        assert document.title == "Software License Agreement"
        assert document.document_type == DocumentType.CONTRACT
        assert document.confidential is True
        assert document.version == "1.0"

    def test_matter_task_creation(self):
        task = MatterTask(
            task_id="TASK-001",
            title="Review contract terms",
            description="Review software licensing terms for compliance",
            assigned_to="attorney@firm.com",
            created_by="paralegal@firm.com",
            created_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=7),
            priority=TaskPriority.HIGH
        )
        
        assert task.task_id == "TASK-001"
        assert task.title == "Review contract terms"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.NOT_STARTED


class TestMatterManager:
    def setup_method(self):
        self.manager = MatterManager()

    def test_create_matter(self):
        matter = self.manager.create_matter(
            matter_id="MTR-001",
            title="Employment Dispute",
            description="Wrongful termination case",
            matter_type=MatterType.EMPLOYMENT,
            client="Jane Smith",
            created_by="attorney@firm.com"
        )
        
        assert matter.matter_id == "MTR-001"
        assert matter.title == "Employment Dispute"
        assert matter.matter_type == MatterType.EMPLOYMENT
        assert len(matter.audit_trail) == 1
        assert matter.audit_trail[0]["action"] == "matter_created"

    def test_add_participant(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION, 
            "Client Inc", "attorney@firm.com"
        )
        
        participant = MatterParticipant(
            participant_id="PART-001",
            name="Witness One",
            role=ParticipantRole.WITNESS,
            organization="Company ABC",
            contact_email="witness@company.com"
        )
        
        result = self.manager.add_participant("MTR-001", participant)
        assert result is True
        assert len(matter.participants) == 1
        assert matter.participants[0].participant_id == "PART-001"
        
        # Test duplicate participant
        duplicate_result = self.manager.add_participant("MTR-001", participant)
        assert duplicate_result is False
        assert len(matter.participants) == 1

    def test_add_document(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION,
            "Client Inc", "attorney@firm.com"
        )
        
        document = MatterDocument(
            document_id="DOC-001",
            title="Initial Complaint",
            document_type=DocumentType.PLEADING,
            file_path="/docs/complaint.pdf",
            created_date=datetime.now(),
            author="attorney@firm.com"
        )
        
        result = self.manager.add_document("MTR-001", document)
        assert result is True
        assert len(matter.documents) == 1
        assert matter.documents[0].document_id == "DOC-001"

    def test_add_task(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION,
            "Client Inc", "attorney@firm.com"
        )
        
        task = MatterTask(
            task_id="TASK-001",
            title="Draft motion",
            description="Draft summary judgment motion",
            assigned_to="attorney@firm.com",
            created_by="paralegal@firm.com",
            created_date=datetime.now()
        )
        
        result = self.manager.add_task("MTR-001", task)
        assert result is True
        assert len(matter.tasks) == 1
        assert matter.tasks[0].task_id == "TASK-001"

    def test_update_task_status(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION,
            "Client Inc", "attorney@firm.com"
        )
        
        task = MatterTask(
            task_id="TASK-001",
            title="Review documents",
            description="Review discovery documents",
            assigned_to="attorney@firm.com",
            created_by="paralegal@firm.com",
            created_date=datetime.now()
        )
        
        self.manager.add_task("MTR-001", task)
        
        result = self.manager.update_task_status("MTR-001", "TASK-001", TaskStatus.COMPLETED)
        assert result is True
        assert task.status == TaskStatus.COMPLETED
        assert task.completion_date is not None

    def test_add_billing_entry(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION,
            "Client Inc", "attorney@firm.com"
        )
        
        billing_entry = BillingEntry(
            entry_id="BILL-001",
            matter_id="MTR-001",
            attorney="attorney@firm.com",
            date=datetime.now(),
            hours=3.5,
            rate=350.0,
            description="Client consultation and case strategy"
        )
        
        result = self.manager.add_billing_entry("MTR-001", billing_entry)
        assert result is True
        assert len(matter.billing_entries) == 1
        assert matter.actual_cost == 3.5 * 350.0

    def test_change_matter_status(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION,
            "Client Inc", "attorney@firm.com"
        )
        
        result = self.manager.change_matter_status("MTR-001", MatterStatus.CLOSED)
        assert result is True
        assert matter.status == MatterStatus.CLOSED
        assert matter.close_date is not None

    def test_search_matters(self):
        matter1 = self.manager.create_matter(
            "MTR-001", "Contract Dispute", "Software licensing dispute", 
            MatterType.LITIGATION, "Tech Corp", "attorney@firm.com"
        )
        
        matter2 = self.manager.create_matter(
            "MTR-002", "Employment Case", "Wrongful termination case",
            MatterType.EMPLOYMENT, "John Doe", "attorney@firm.com"
        )
        
        # Search by title
        results = self.manager.search_matters("contract")
        assert len(results) == 1
        assert results[0]["matter_id"] == "MTR-001"
        
        # Search by client
        results = self.manager.search_matters("john doe")
        assert len(results) == 1
        assert results[0]["matter_id"] == "MTR-002"

    def test_get_overdue_tasks(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION,
            "Client Inc", "attorney@firm.com"
        )
        
        # Create an overdue task
        overdue_task = MatterTask(
            task_id="TASK-001",
            title="Overdue task",
            description="This task is overdue",
            assigned_to="attorney@firm.com",
            created_by="paralegal@firm.com",
            created_date=datetime.now() - timedelta(days=10),
            due_date=datetime.now() - timedelta(days=5)
        )
        
        self.manager.add_task("MTR-001", overdue_task)
        
        overdue_tasks = self.manager.get_overdue_tasks()
        assert len(overdue_tasks) == 1
        assert overdue_tasks[0]["task_id"] == "TASK-001"
        assert overdue_tasks[0]["days_overdue"] == 5

    def test_export_matter_data(self):
        matter = self.manager.create_matter(
            "MTR-001", "Test Case", "Description", MatterType.LITIGATION,
            "Client Inc", "attorney@firm.com"
        )
        
        participant = MatterParticipant(
            participant_id="PART-001",
            name="Test Participant",
            role=ParticipantRole.WITNESS,
            organization="Company ABC",
            contact_email="test@company.com"
        )
        self.manager.add_participant("MTR-001", participant)
        
        export_data = self.manager.export_matter_data("MTR-001", "json")
        assert export_data != ""
        assert "MTR-001" in export_data
        assert "Test Case" in export_data
        assert "Test Participant" in export_data


class TestDocumentVersionControl:
    def setup_method(self):
        self.version_control = DocumentVersionControl()

    def test_add_document_version(self):
        document = MatterDocument(
            document_id="DOC-001_v1",
            title="Contract Draft v1",
            document_type=DocumentType.CONTRACT,
            file_path="/docs/contract_v1.pdf",
            created_date=datetime.now(),
            author="attorney@firm.com"
        )
        
        result = self.version_control.add_document_version(document)
        assert result is True
        assert "DOC-001" in self.version_control.versions

    def test_get_latest_version(self):
        doc_v1 = MatterDocument(
            document_id="DOC-001_v1",
            title="Contract v1",
            document_type=DocumentType.CONTRACT,
            file_path="/docs/contract_v1.pdf",
            created_date=datetime.now() - timedelta(hours=2),
            author="attorney@firm.com"
        )
        
        doc_v2 = MatterDocument(
            document_id="DOC-001_v2",
            title="Contract v2",
            document_type=DocumentType.CONTRACT,
            file_path="/docs/contract_v2.pdf",
            created_date=datetime.now(),
            author="attorney@firm.com"
        )
        
        self.version_control.add_document_version(doc_v1)
        self.version_control.add_document_version(doc_v2)
        
        latest = self.version_control.get_latest_version("DOC-001")
        assert latest is not None
        assert latest.document_id == "DOC-001_v2"

    def test_get_version_history(self):
        doc_v1 = MatterDocument(
            document_id="DOC-001_v1",
            title="Contract v1",
            document_type=DocumentType.CONTRACT,
            file_path="/docs/contract_v1.pdf",
            created_date=datetime.now() - timedelta(hours=2),
            author="attorney@firm.com"
        )
        
        doc_v2 = MatterDocument(
            document_id="DOC-001_v2",
            title="Contract v2",
            document_type=DocumentType.CONTRACT,
            file_path="/docs/contract_v2.pdf",
            created_date=datetime.now(),
            author="attorney@firm.com"
        )
        
        self.version_control.add_document_version(doc_v1)
        self.version_control.add_document_version(doc_v2)
        
        history = self.version_control.get_version_history("DOC-001")
        assert len(history) == 2
        assert history[0].document_id == "DOC-001_v2"  # Latest first
        assert history[1].document_id == "DOC-001_v1"


class TestConflictChecker:
    def setup_method(self):
        self.conflict_checker = ConflictChecker()

    def test_add_known_conflict(self):
        self.conflict_checker.add_known_conflict("ABC Corp", "Opposing party in previous litigation")
        assert "ABC Corp" in self.conflict_checker.known_conflicts
        assert len(self.conflict_checker.known_conflicts["ABC Corp"]) == 1

    def test_check_conflicts_with_known_conflict(self):
        # Add a known conflict
        self.conflict_checker.add_known_conflict("XYZ Inc", "Former client with opposing interests")
        
        matter = Matter(
            matter_id="MTR-001",
            title="Test Matter",
            description="Test description",
            matter_type=MatterType.LITIGATION,
            client="XYZ Inc",
            created_by="attorney@firm.com",
            created_date=datetime.now()
        )
        
        conflict_result = self.conflict_checker.check_conflicts(matter)
        assert len(conflict_result["conflicts_found"]) > 0
        assert conflict_result["requires_review"] is True

    def test_check_conflicts_no_conflicts(self):
        matter = Matter(
            matter_id="MTR-001",
            title="Test Matter",
            description="Test description",
            matter_type=MatterType.LITIGATION,
            client="Clean Client Corp",
            created_by="attorney@firm.com",
            created_date=datetime.now()
        )
        
        conflict_result = self.conflict_checker.check_conflicts(matter)
        assert len(conflict_result["conflicts_found"]) == 0
        assert conflict_result["requires_review"] is False


class TestMatterTimelineGenerator:
    def setup_method(self):
        self.timeline_generator = MatterTimelineGenerator()

    def test_generate_timeline(self):
        matter = Matter(
            matter_id="MTR-001",
            title="Test Matter",
            description="Test description",
            matter_type=MatterType.LITIGATION,
            client="Test Client",
            created_by="attorney@firm.com",
            created_date=datetime.now()
        )
        
        # Add a document
        document = MatterDocument(
            document_id="DOC-001",
            title="Initial Pleading",
            document_type=DocumentType.PLEADING,
            file_path="/docs/pleading.pdf",
            created_date=datetime.now() + timedelta(hours=1),
            author="attorney@firm.com"
        )
        matter.documents.append(document)
        
        # Add a task
        task = MatterTask(
            task_id="TASK-001",
            title="Review case law",
            description="Research relevant precedents",
            assigned_to="attorney@firm.com",
            created_by="paralegal@firm.com",
            created_date=datetime.now() + timedelta(hours=2),
            completion_date=datetime.now() + timedelta(hours=4)
        )
        matter.tasks.append(task)
        
        timeline = self.timeline_generator.generate_timeline(matter)
        assert len(timeline) >= 3  # Matter creation + document + task creation + task completion
        assert timeline[0]["type"] == "matter_created"
        assert any(event["type"] == "document_added" for event in timeline)
        assert any(event["type"] == "task_created" for event in timeline)


class TestMatterReportGenerator:
    def setup_method(self):
        self.report_generator = MatterReportGenerator()

    def test_generate_matter_summary(self):
        matter = Matter(
            matter_id="MTR-001",
            title="Test Matter",
            description="Test description",
            matter_type=MatterType.LITIGATION,
            client="Test Client",
            created_by="attorney@firm.com",
            created_date=datetime.now()
        )
        
        # Add participants
        participant = MatterParticipant(
            participant_id="PART-001",
            name="John Witness",
            role=ParticipantRole.WITNESS,
            organization="Company ABC",
            contact_email="witness@company.com"
        )
        matter.participants.append(participant)
        
        # Add documents
        document = MatterDocument(
            document_id="DOC-001",
            title="Contract",
            document_type=DocumentType.CONTRACT,
            file_path="/docs/contract.pdf",
            created_date=datetime.now(),
            author="attorney@firm.com",
            confidential=True
        )
        matter.documents.append(document)
        
        # Add tasks
        task = MatterTask(
            task_id="TASK-001",
            title="Review documents",
            description="Review case documents",
            assigned_to="attorney@firm.com",
            created_by="paralegal@firm.com",
            created_date=datetime.now(),
            status=TaskStatus.COMPLETED
        )
        matter.tasks.append(task)
        
        summary = self.report_generator.generate_matter_summary(matter)
        
        assert summary["matter_id"] == "MTR-001"
        assert summary["participants"]["total"] == 1
        assert summary["documents"]["total"] == 1
        assert summary["documents"]["confidential"] == 1
        assert summary["tasks"]["total"] == 1
        assert summary["tasks"]["completed"] == 1
        assert summary["tasks"]["completion_rate"] == 1.0

    def test_generate_financial_report(self):
        matter = Matter(
            matter_id="MTR-001",
            title="Test Matter",
            description="Test description",
            matter_type=MatterType.LITIGATION,
            client="Test Client",
            created_by="attorney@firm.com",
            created_date=datetime.now(),
            budget_amount=50000.0
        )
        
        # Add billing entries
        entry1 = BillingEntry(
            entry_id="BILL-001",
            matter_id="MTR-001",
            attorney="attorney1@firm.com",
            date=datetime.now(),
            hours=5.0,
            rate=400.0,
            description="Case research"
        )
        
        entry2 = BillingEntry(
            entry_id="BILL-002",
            matter_id="MTR-001",
            attorney="attorney2@firm.com",
            date=datetime.now(),
            hours=3.0,
            rate=350.0,
            description="Document review"
        )
        
        matter.billing_entries.extend([entry1, entry2])
        
        financial_report = self.report_generator.generate_financial_report(matter)
        
        assert financial_report["matter_id"] == "MTR-001"
        assert financial_report["total_billed"] == (5.0 * 400.0) + (3.0 * 350.0)
        assert "attorney1@firm.com" in financial_report["billing_by_attorney"]
        assert "attorney2@firm.com" in financial_report["billing_by_attorney"]
        assert financial_report["budget_amount"] == 50000.0


class TestMatterDashboard:
    def setup_method(self):
        self.manager = MatterManager()
        self.dashboard = MatterDashboard(self.manager)

    def test_get_dashboard_data_empty(self):
        dashboard_data = self.dashboard.get_dashboard_data()
        
        assert dashboard_data["total_matters"] == 0
        assert dashboard_data["total_overdue_tasks"] == 0
        assert dashboard_data["financial_summary"]["total_budget"] == 0

    def test_get_dashboard_data_with_matters(self):
        # Create test matters
        matter1 = self.manager.create_matter(
            "MTR-001", "Litigation Case", "Description", 
            MatterType.LITIGATION, "Client 1", "attorney@firm.com"
        )
        matter1.budget_amount = 25000.0
        matter1.actual_cost = 15000.0
        
        matter2 = self.manager.create_matter(
            "MTR-002", "Employment Case", "Description",
            MatterType.EMPLOYMENT, "Client 2", "attorney@firm.com"
        )
        matter2.budget_amount = 30000.0
        matter2.actual_cost = 20000.0
        
        dashboard_data = self.dashboard.get_dashboard_data()
        
        assert dashboard_data["total_matters"] == 2
        assert dashboard_data["matters_by_type"]["litigation"] == 1
        assert dashboard_data["matters_by_type"]["employment"] == 1
        assert dashboard_data["financial_summary"]["total_budget"] == 55000.0
        assert dashboard_data["financial_summary"]["total_actual"] == 35000.0


if __name__ == "__main__":
    pytest.main([__file__])