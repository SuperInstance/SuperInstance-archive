import pytest
from datetime import datetime, timedelta
from modules.legal.holds.src.legal_hold import (
    LegalHold, Custodian, PreservationRule, HoldNotification, ComplianceCheck,
    HoldStatus, CustodianStatus, NotificationType, HoldScope,
    LegalHoldManager, NotificationTemplateManager, HoldComplianceMonitor,
    HoldMetricsCalculator
)


class TestLegalHold:
    def test_legal_hold_creation(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Employee Termination Investigation",
            description="Investigation regarding employee termination",
            created_by="legal@company.com",
            created_date=datetime.now()
        )
        
        assert hold.hold_id == "HOLD-001"
        assert hold.matter_id == "MATTER-001"
        assert hold.title == "Employee Termination Investigation"
        assert hold.status == HoldStatus.DRAFT
        assert len(hold.custodians) == 0
        assert len(hold.preservation_rules) == 0
        assert len(hold.audit_trail) == 0

    def test_custodian_creation(self):
        custodian = Custodian(
            custodian_id="CUST-001",
            name="John Doe",
            email="john.doe@company.com",
            department="Engineering",
            role="Software Engineer"
        )
        
        assert custodian.custodian_id == "CUST-001"
        assert custodian.name == "John Doe"
        assert custodian.status == CustodianStatus.NOTIFIED
        assert custodian.compliance_score == 0.0
        assert custodian.escalation_count == 0

    def test_preservation_rule_creation(self):
        rule = PreservationRule(
            rule_id="RULE-001",
            scope=HoldScope.EMAIL,
            description="All emails related to project X",
            keywords=["project x", "termination", "performance"],
            file_types=["eml", "msg", "pst"]
        )
        
        assert rule.rule_id == "RULE-001"
        assert rule.scope == HoldScope.EMAIL
        assert "project x" in rule.keywords
        assert "eml" in rule.file_types


class TestLegalHoldManager:
    def setup_method(self):
        self.manager = LegalHoldManager()

    def test_create_hold(self):
        hold = self.manager.create_hold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test Investigation",
            description="Test description",
            created_by="legal@test.com"
        )
        
        assert hold.hold_id == "HOLD-001"
        assert hold.matter_id == "MATTER-001"
        assert hold.status == HoldStatus.DRAFT
        assert len(hold.audit_trail) == 1
        assert hold.audit_trail[0]["action"] == "hold_created"

    def test_add_custodian(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Jane Smith",
            email="jane.smith@test.com",
            department="HR",
            role="Manager"
        )
        
        result = self.manager.add_custodian("HOLD-001", custodian)
        assert result is True
        assert len(hold.custodians) == 1
        assert hold.custodians[0].custodian_id == "CUST-001"
        
        # Test duplicate custodian
        duplicate_result = self.manager.add_custodian("HOLD-001", custodian)
        assert duplicate_result is False
        assert len(hold.custodians) == 1

    def test_add_preservation_rule(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        rule = PreservationRule(
            rule_id="RULE-001",
            scope=HoldScope.DOCUMENTS,
            description="All project documents",
            keywords=["project", "contract"],
            file_types=["docx", "pdf"]
        )
        
        result = self.manager.add_preservation_rule("HOLD-001", rule)
        assert result is True
        assert len(hold.preservation_rules) == 1
        assert hold.preservation_rules[0].rule_id == "RULE-001"

    def test_activate_hold(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        self.manager.add_custodian("HOLD-001", custodian)
        
        result = self.manager.activate_hold("HOLD-001")
        assert result is True
        assert hold.status == HoldStatus.ACTIVE
        assert hold.effective_date is not None
        assert len(hold.notifications) == 1
        assert hold.notifications[0].notification_type == NotificationType.INITIAL

    def test_release_hold(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        self.manager.add_custodian("HOLD-001", custodian)
        self.manager.activate_hold("HOLD-001")
        
        result = self.manager.release_hold("HOLD-001", "legal@test.com")
        assert result is True
        assert hold.status == HoldStatus.RELEASED
        assert hold.release_date is not None
        assert len(hold.notifications) == 2  # Initial + Release

    def test_acknowledge_hold(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        self.manager.add_custodian("HOLD-001", custodian)
        self.manager.activate_hold("HOLD-001")
        
        result = self.manager.acknowledge_hold("HOLD-001", "CUST-001")
        assert result is True
        assert custodian.status == CustodianStatus.ACKNOWLEDGED
        assert custodian.acknowledgment_date is not None
        assert custodian.compliance_score > 0

    def test_run_compliance_checks(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        self.manager.add_custodian("HOLD-001", custodian)
        self.manager.activate_hold("HOLD-001")
        
        checks = self.manager.run_compliance_checks("HOLD-001")
        assert len(checks) == 1
        assert checks[0].custodian_id == "CUST-001"
        assert checks[0].check_type == "custodian_compliance"

    def test_send_reminders(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        
        # Set notification date to 4 days ago to trigger reminder
        custodian.notification_date = datetime.now() - timedelta(days=4)
        custodian.status = CustodianStatus.NOTIFIED
        
        self.manager.add_custodian("HOLD-001", custodian)
        
        reminders_sent = self.manager.send_reminders("HOLD-001")
        assert reminders_sent == 1
        assert len(hold.notifications) == 1
        assert hold.notifications[0].notification_type == NotificationType.REMINDER

    def test_get_hold_status_report(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian1 = Custodian(
            custodian_id="CUST-001",
            name="User 1",
            email="user1@test.com",
            department="IT",
            role="Admin"
        )
        custodian1.status = CustodianStatus.ACKNOWLEDGED
        custodian1.compliance_score = 0.8
        
        custodian2 = Custodian(
            custodian_id="CUST-002",
            name="User 2",
            email="user2@test.com",
            department="HR",
            role="Manager"
        )
        custodian2.status = CustodianStatus.NON_RESPONSIVE
        custodian2.compliance_score = 0.3
        
        self.manager.add_custodian("HOLD-001", custodian1)
        self.manager.add_custodian("HOLD-001", custodian2)
        
        report = self.manager.get_hold_status_report("HOLD-001")
        
        assert report["hold_id"] == "HOLD-001"
        assert report["custodian_stats"]["total"] == 2
        assert report["custodian_stats"]["acknowledged"] == 1
        assert report["custodian_stats"]["non_responsive"] == 1
        assert report["average_compliance_score"] == 0.55

    def test_export_hold_data(self):
        hold = self.manager.create_hold(
            "HOLD-001", "MATTER-001", "Test", "Description", "legal@test.com"
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        self.manager.add_custodian("HOLD-001", custodian)
        
        export_data = self.manager.export_hold_data("HOLD-001", "json")
        assert export_data != ""
        assert "HOLD-001" in export_data
        assert "CUST-001" in export_data
        assert "Test User" in export_data


class TestNotificationTemplateManager:
    def setup_method(self):
        self.template_manager = NotificationTemplateManager()

    def test_get_initial_template(self):
        template = self.template_manager.get_template(NotificationType.INITIAL)
        assert template != ""
        assert "Legal Hold Notice" in template
        assert "{hold_title}" in template
        assert "{custodian_name}" in template

    def test_get_reminder_template(self):
        template = self.template_manager.get_template(NotificationType.REMINDER)
        assert template != ""
        assert "REMINDER" in template
        assert "{initial_notice_date}" in template

    def test_get_escalation_template(self):
        template = self.template_manager.get_template(NotificationType.ESCALATION)
        assert template != ""
        assert "ESCALATION" in template
        assert "{manager_name}" in template

    def test_get_release_template(self):
        template = self.template_manager.get_template(NotificationType.RELEASE)
        assert template != ""
        assert "Legal Hold Release" in template
        assert "{release_date}" in template

    def test_customize_template(self):
        template = "Hello {name}, your {item} is ready."
        variables = {"name": "John", "item": "order"}
        
        customized = self.template_manager.customize_template(template, variables)
        assert customized == "Hello John, your order is ready."


class TestHoldComplianceMonitor:
    def setup_method(self):
        self.monitor = HoldComplianceMonitor()

    def test_check_custodian_compliance_responsive(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        custodian.status = CustodianStatus.ACKNOWLEDGED
        custodian.notification_date = datetime.now() - timedelta(days=1)
        custodian.acknowledgment_date = datetime.now()
        custodian.compliance_score = 0.9
        
        check = self.monitor.check_custodian_compliance(custodian, hold)
        assert check.result == "COMPLIANT"
        assert len(check.issues_found) == 0

    def test_check_custodian_compliance_non_responsive(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        custodian.status = CustodianStatus.NON_RESPONSIVE
        custodian.notification_date = datetime.now() - timedelta(days=5)
        custodian.compliance_score = 0.2
        
        check = self.monitor.check_custodian_compliance(custodian, hold)
        assert check.result == "NON_COMPLIANT"
        assert len(check.issues_found) > 0
        assert "not acknowledged" in check.issues_found[0].lower()

    def test_scan_for_destruction_activities(self):
        activity_logs = [
            "User accessed file: report.docx",
            "User deleted file: old_contract.pdf",
            "User purged email folder",
            "User saved document: new_report.docx"
        ]
        
        suspicious = self.monitor.scan_for_destruction_activities("CUST-001", activity_logs)
        assert len(suspicious) == 2
        assert "deleted" in suspicious[0].lower()
        assert "purged" in suspicious[1].lower()

    def test_calculate_compliance_score_perfect(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        custodian.notification_date = datetime.now() - timedelta(hours=2)
        custodian.acknowledgment_date = datetime.now()
        custodian.status = CustodianStatus.ACKNOWLEDGED
        custodian.escalation_count = 0
        
        score = self.monitor.calculate_compliance_score(custodian, hold)
        assert score == 1.0

    def test_calculate_compliance_score_with_deductions(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian = Custodian(
            custodian_id="CUST-001",
            name="Test User",
            email="test@test.com",
            department="IT",
            role="Admin"
        )
        custodian.notification_date = datetime.now() - timedelta(days=5)
        custodian.acknowledgment_date = datetime.now()
        custodian.status = CustodianStatus.ACKNOWLEDGED
        custodian.escalation_count = 2
        
        score = self.monitor.calculate_compliance_score(custodian, hold)
        assert score < 1.0
        assert score > 0.0


class TestHoldMetricsCalculator:
    def test_calculate_acknowledgment_rate(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian1 = Custodian(
            custodian_id="CUST-001",
            name="User 1",
            email="user1@test.com",
            department="IT",
            role="Admin"
        )
        custodian1.status = CustodianStatus.ACKNOWLEDGED
        
        custodian2 = Custodian(
            custodian_id="CUST-002",
            name="User 2",
            email="user2@test.com",
            department="HR",
            role="Manager"
        )
        custodian2.status = CustodianStatus.NOTIFIED
        
        hold.custodians = [custodian1, custodian2]
        
        rate = HoldMetricsCalculator.calculate_acknowledgment_rate(hold)
        assert rate == 0.5

    def test_calculate_average_response_time(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian1 = Custodian(
            custodian_id="CUST-001",
            name="User 1",
            email="user1@test.com",
            department="IT",
            role="Admin"
        )
        custodian1.notification_date = datetime.now() - timedelta(hours=4)
        custodian1.acknowledgment_date = datetime.now()
        
        custodian2 = Custodian(
            custodian_id="CUST-002",
            name="User 2",
            email="user2@test.com",
            department="HR",
            role="Manager"
        )
        custodian2.notification_date = datetime.now() - timedelta(hours=2)
        custodian2.acknowledgment_date = datetime.now()
        
        hold.custodians = [custodian1, custodian2]
        
        avg_time = HoldMetricsCalculator.calculate_average_response_time(hold)
        assert avg_time == 3.0  # Average of 4 and 2 hours

    def test_identify_high_risk_custodians(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian1 = Custodian(
            custodian_id="CUST-001",
            name="User 1",
            email="user1@test.com",
            department="IT",
            role="Admin"
        )
        custodian1.compliance_score = 0.9
        
        custodian2 = Custodian(
            custodian_id="CUST-002",
            name="User 2",
            email="user2@test.com",
            department="HR",
            role="Manager"
        )
        custodian2.compliance_score = 0.3
        
        hold.custodians = [custodian1, custodian2]
        
        high_risk = HoldMetricsCalculator.identify_high_risk_custodians(hold, 0.5)
        assert len(high_risk) == 1
        assert high_risk[0].custodian_id == "CUST-002"

    def test_get_hold_effectiveness_score(self):
        hold = LegalHold(
            hold_id="HOLD-001",
            matter_id="MATTER-001",
            title="Test",
            description="Test",
            created_by="legal@test.com",
            created_date=datetime.now()
        )
        
        custodian1 = Custodian(
            custodian_id="CUST-001",
            name="User 1",
            email="user1@test.com",
            department="IT",
            role="Admin"
        )
        custodian1.status = CustodianStatus.ACKNOWLEDGED
        custodian1.compliance_score = 0.8
        
        custodian2 = Custodian(
            custodian_id="CUST-002",
            name="User 2",
            email="user2@test.com",
            department="HR",
            role="Manager"
        )
        custodian2.status = CustodianStatus.ACKNOWLEDGED
        custodian2.compliance_score = 0.6
        
        hold.custodians = [custodian1, custodian2]
        
        effectiveness = HoldMetricsCalculator.get_hold_effectiveness_score(hold)
        # Acknowledgment rate: 1.0, Avg compliance: 0.7
        # Score: (1.0 * 0.4) + (0.7 * 0.6) = 0.4 + 0.42 = 0.82
        assert effectiveness == 0.82


if __name__ == "__main__":
    pytest.main([__file__])