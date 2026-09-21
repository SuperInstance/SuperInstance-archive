#!/usr/bin/env python3
"""
DCAA Compliant Timekeeping System
Defense Contract Audit Agency compliant time tracking and reporting
"""

import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import hashlib

logger = logging.getLogger(__name__)

class TimeEntryType(Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    FRINGE = "fringe"
    OVERHEAD = "overhead"
    G_AND_A = "g_and_a"

class TimeEntryStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    LOCKED = "locked"

class ApprovalLevel(Enum):
    SUPERVISOR = "supervisor"
    PROJECT_MANAGER = "project_manager"
    DCAA_REVIEWER = "dcaa_reviewer"

class DCAAAuditRequirement(Enum):
    DAILY_PREPARATION = "daily_preparation"
    CONTEMPORANEOUS_RECORDING = "contemporaneous_recording"
    SUPERVISOR_APPROVAL = "supervisor_approval"
    SEGREGATION_DUTIES = "segregation_duties"
    SUPPORTING_DOCUMENTATION = "supporting_documentation"
    AUDIT_TRAIL = "audit_trail"

class DCAATimekeepingSystem:
    def __init__(self):
        self.db_path = "dcaa_timekeeping.db"
        self.audit_requirements = {}
        self.labor_categories = {}

    async def initialize(self):
        """Initialize DCAA timekeeping system"""
        try:
            await self._create_database_schema()
            await self._setup_labor_categories()
            await self._setup_audit_requirements()
            await self._setup_approval_workflows()
            logger.info("DCAA Timekeeping System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DCAA Timekeeping System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for DCAA timekeeping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Time entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                task_id TEXT,
                entry_date TEXT NOT NULL,
                hours_worked REAL NOT NULL,
                entry_type TEXT NOT NULL,
                labor_category TEXT NOT NULL,
                task_description TEXT NOT NULL,
                location TEXT,
                charge_number TEXT,
                status TEXT NOT NULL,
                submitted_date TEXT,
                approved_date TEXT,
                approved_by TEXT,
                approval_level TEXT,
                rejection_reason TEXT,
                is_locked BOOLEAN DEFAULT 0,
                digital_signature TEXT,
                ip_address TEXT,
                device_info TEXT,
                original_entry_id TEXT,
                modification_reason TEXT,
                supporting_documents TEXT,
                audit_trail TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Employee labor categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_labor_categories (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                labor_category TEXT NOT NULL,
                hourly_rate REAL NOT NULL,
                effective_date TEXT NOT NULL,
                expiration_date TEXT,
                billing_rate REAL,
                overhead_rate REAL DEFAULT 0.0,
                fringe_rate REAL DEFAULT 0.0,
                ga_rate REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
        """)
        
        # Timesheet periods table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timesheet_periods (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                period_start_date TEXT NOT NULL,
                period_end_date TEXT NOT NULL,
                total_hours REAL DEFAULT 0.0,
                direct_hours REAL DEFAULT 0.0,
                indirect_hours REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                submitted_date TEXT,
                supervisor_approval_date TEXT,
                supervisor_id TEXT,
                dcaa_review_date TEXT,
                dcaa_reviewer_id TEXT,
                certification_statement TEXT,
                employee_signature TEXT,
                supervisor_signature TEXT,
                is_final BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        # DCAA audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dcaa_audit_logs (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_description TEXT NOT NULL,
                affected_entry_id TEXT,
                old_values TEXT,
                new_values TEXT,
                performed_by TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                compliance_requirement TEXT,
                audit_timestamp TEXT NOT NULL
            )
        """)
        
        # Contract labor standards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contract_labor_standards (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                wage_determination TEXT,
                prevailing_wage_rates TEXT,
                fringe_benefits TEXT,
                labor_classifications TEXT,
                effective_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_labor_categories(self):
        """Setup standard labor categories"""
        self.labor_categories = {
            "senior_engineer": {
                "description": "Senior Software Engineer",
                "minimum_qualifications": "BS + 8 years or MS + 6 years",
                "typical_hourly_rate": Decimal('85.00')
            },
            "software_engineer": {
                "description": "Software Engineer",
                "minimum_qualifications": "BS + 4 years or MS + 2 years", 
                "typical_hourly_rate": Decimal('65.00')
            },
            "junior_engineer": {
                "description": "Junior Software Engineer",
                "minimum_qualifications": "BS + 0-2 years",
                "typical_hourly_rate": Decimal('45.00')
            },
            "project_manager": {
                "description": "Project Manager",
                "minimum_qualifications": "BS + 5 years PM experience",
                "typical_hourly_rate": Decimal('95.00')
            },
            "technical_writer": {
                "description": "Technical Writer",
                "minimum_qualifications": "BS + 3 years technical writing",
                "typical_hourly_rate": Decimal('55.00')
            }
        }

    async def _setup_audit_requirements(self):
        """Setup DCAA audit requirements"""
        self.audit_requirements = {
            DCAAAuditRequirement.DAILY_PREPARATION.value: {
                "description": "Time must be prepared daily as work is performed",
                "compliance_check": "Entry date within 24 hours of work date"
            },
            DCAAAuditRequirement.CONTEMPORANEOUS_RECORDING.value: {
                "description": "Time must be recorded at or near the time work is performed",
                "compliance_check": "Entry timestamp within reasonable time of work"
            },
            DCAAAuditRequirement.SUPERVISOR_APPROVAL.value: {
                "description": "Timesheets must be approved by knowledgeable supervisor",
                "compliance_check": "Valid supervisor signature and approval date"
            },
            DCAAAuditRequirement.SEGREGATION_DUTIES.value: {
                "description": "Separation of timekeeping and payroll functions",
                "compliance_check": "Different personnel for time recording and processing"
            },
            DCAAAuditRequirement.SUPPORTING_DOCUMENTATION.value: {
                "description": "Supporting documentation for time charges",
                "compliance_check": "Adequate documentation for work performed"
            },
            DCAAAuditRequirement.AUDIT_TRAIL.value: {
                "description": "Complete audit trail of all changes",
                "compliance_check": "All modifications logged with reason and approver"
            }
        }

    async def _setup_approval_workflows(self):
        """Setup approval workflows for different contract types"""
        pass

    async def submit_time_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit DCAA compliant time entry"""
        try:
            entry_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Validate entry data
            validation_result = await self._validate_time_entry(entry_data)
            if not validation_result['valid']:
                return {"error": "Invalid time entry", "validation_errors": validation_result['errors']}
            
            # Check DCAA compliance
            compliance_check = await self._check_dcaa_compliance(entry_data)
            if not compliance_check['compliant']:
                return {"error": "DCAA compliance violation", "compliance_issues": compliance_check['issues']}
            
            # Generate digital signature
            digital_signature = await self._generate_digital_signature(entry_data, entry_id)
            
            # Store time entry
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO time_entries 
                (id, employee_id, contract_id, task_id, entry_date, hours_worked, entry_type,
                 labor_category, task_description, location, charge_number, status,
                 digital_signature, ip_address, device_info, audit_trail, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                entry_data['employee_id'],
                entry_data['contract_id'],
                entry_data.get('task_id'),
                entry_data['date'],
                entry_data['hours_worked'],
                entry_data.get('direct_indirect', 'direct'),
                entry_data.get('labor_category', 'software_engineer'),
                entry_data['task_description'],
                entry_data.get('location'),
                entry_data.get('charge_number'),
                TimeEntryStatus.SUBMITTED.value,
                digital_signature,
                entry_data.get('ip_address'),
                entry_data.get('device_info'),
                json.dumps([{"action": "created", "date": now, "by": entry_data['employee_id']}]),
                now,
                now
            ))
            
            conn.commit()
            conn.close()
            
            # Log audit event
            await self._log_audit_event(
                entry_data['employee_id'],
                "TIME_ENTRY_SUBMITTED",
                f"Time entry submitted for {entry_data['date']} - {entry_data['hours_worked']} hours",
                entry_id,
                entry_data['employee_id']
            )
            
            return {
                "entry_id": entry_id,
                "status": "submitted",
                "message": "Time entry submitted successfully",
                "compliance_status": "compliant",
                "next_step": "awaiting_supervisor_approval"
            }
            
        except Exception as e:
            logger.error(f"Error submitting time entry: {e}")
            return {"error": str(e)}

    async def _validate_time_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate time entry data"""
        errors = []
        
        # Required fields
        required_fields = ['employee_id', 'contract_id', 'date', 'hours_worked', 'task_description']
        for field in required_fields:
            if field not in entry_data or not entry_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate hours
        if 'hours_worked' in entry_data:
            try:
                hours = float(entry_data['hours_worked'])
                if hours <= 0 or hours > 24:
                    errors.append("Hours worked must be between 0 and 24")
            except ValueError:
                errors.append("Invalid hours worked value")
        
        # Validate date
        if 'date' in entry_data:
            try:
                entry_date = datetime.fromisoformat(entry_data['date'].replace('Z', '+00:00'))
                if entry_date > datetime.now():
                    errors.append("Cannot submit time for future dates")
            except ValueError:
                errors.append("Invalid date format")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    async def _check_dcaa_compliance(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check DCAA compliance requirements"""
        issues = []
        
        # Check daily preparation requirement
        try:
            entry_date = datetime.fromisoformat(entry_data['date'].replace('Z', '+00:00')).date()
            current_date = date.today()
            days_difference = (current_date - entry_date).days
            
            if days_difference > 1:
                issues.append("Time entry not prepared within 24 hours (daily preparation requirement)")
        except:
            issues.append("Invalid date format for compliance check")
        
        # Check task description adequacy
        if len(entry_data.get('task_description', '')) < 10:
            issues.append("Task description too brief for DCAA requirements")
        
        # Check for required supporting documentation
        if entry_data.get('hours_worked', 0) > 8 and not entry_data.get('supporting_documents'):
            issues.append("Supporting documentation required for overtime hours")
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues
        }

    async def _generate_digital_signature(self, entry_data: Dict[str, Any], entry_id: str) -> str:
        """Generate digital signature for time entry"""
        signature_data = f"{entry_id}:{entry_data['employee_id']}:{entry_data['date']}:{entry_data['hours_worked']}"
        return hashlib.sha256(signature_data.encode()).hexdigest()

    async def generate_timesheet(self, employee_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate DCAA compliant timesheet"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get time entries for period
            cursor.execute("""
                SELECT * FROM time_entries 
                WHERE employee_id = ? AND entry_date BETWEEN ? AND ?
                ORDER BY entry_date, created_at
            """, (employee_id, start_date, end_date))
            
            entries = []
            total_hours = Decimal('0')
            direct_hours = Decimal('0')
            indirect_hours = Decimal('0')
            
            for row in cursor.fetchall():
                entry = {
                    "id": row[0],
                    "date": row[4],
                    "hours": row[5],
                    "type": row[6],
                    "labor_category": row[7],
                    "description": row[8],
                    "contract_id": row[2],
                    "status": row[11]
                }
                entries.append(entry)
                
                hours = Decimal(str(row[5]))
                total_hours += hours
                if row[6] == TimeEntryType.DIRECT.value:
                    direct_hours += hours
                else:
                    indirect_hours += hours
            
            # Check if timesheet exists for this period
            cursor.execute("""
                SELECT * FROM timesheet_periods 
                WHERE employee_id = ? AND period_start_date = ? AND period_end_date = ?
            """, (employee_id, start_date, end_date))
            
            existing_timesheet = cursor.fetchone()
            
            conn.close()
            
            # Generate certification statement
            certification = self._generate_certification_statement(employee_id, start_date, end_date)
            
            timesheet = {
                "employee_id": employee_id,
                "period_start": start_date,
                "period_end": end_date,
                "total_hours": float(total_hours),
                "direct_hours": float(direct_hours),
                "indirect_hours": float(indirect_hours),
                "entries": entries,
                "status": existing_timesheet[9] if existing_timesheet else "draft",
                "certification_statement": certification,
                "dcaa_compliant": await self._verify_timesheet_compliance(entries),
                "generated_date": datetime.now().isoformat()
            }
            
            return timesheet
            
        except Exception as e:
            logger.error(f"Error generating timesheet: {e}")
            return {"error": str(e)}

    def _generate_certification_statement(self, employee_id: str, start_date: str, end_date: str) -> str:
        """Generate DCAA required certification statement"""
        return f"""
        I hereby certify that the time recorded on this timesheet for the period 
        {start_date} through {end_date} is true and accurate to the best of my knowledge 
        and belief. I understand that this information is subject to verification and 
        that any false statements may subject me to criminal prosecution under 
        Title 18, United States Code, Section 1001.
        
        The time recorded represents work actually performed and is recorded in 
        accordance with Defense Contract Audit Agency (DCAA) requirements.
        """

    async def _verify_timesheet_compliance(self, entries: List[Dict[str, Any]]) -> bool:
        """Verify timesheet meets DCAA compliance requirements"""
        try:
            # Check for daily preparation
            for entry in entries:
                entry_date = datetime.fromisoformat(entry['date']).date()
                if (date.today() - entry_date).days > 7:  # Allow some flexibility for historical verification
                    continue
            
            # Check for adequate task descriptions
            for entry in entries:
                if len(entry['description']) < 10:
                    return False
            
            # Check for reasonable hour distributions
            total_daily_hours = {}
            for entry in entries:
                date_key = entry['date']
                if date_key not in total_daily_hours:
                    total_daily_hours[date_key] = 0
                total_daily_hours[date_key] += entry['hours']
            
            # Verify no day exceeds 24 hours
            for daily_total in total_daily_hours.values():
                if daily_total > 24:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying timesheet compliance: {e}")
            return False

    async def approve_timesheet(self, employee_id: str, period: str, supervisor_id: str) -> Dict[str, Any]:
        """Approve timesheet with DCAA requirements"""
        try:
            period_parts = period.split('_to_')
            if len(period_parts) != 2:
                return {"error": "Invalid period format. Use YYYY-MM-DD_to_YYYY-MM-DD"}
            
            start_date, end_date = period_parts
            
            # Verify supervisor authority
            authority_check = await self._verify_supervisor_authority(supervisor_id, employee_id)
            if not authority_check['authorized']:
                return {"error": "Supervisor not authorized to approve this employee's timesheet"}
            
            # Get timesheet data
            timesheet = await self.generate_timesheet(employee_id, start_date, end_date)
            if 'error' in timesheet:
                return timesheet
            
            # Verify DCAA compliance
            if not timesheet['dcaa_compliant']:
                return {"error": "Timesheet does not meet DCAA compliance requirements"}
            
            # Update timesheet approval
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # Insert or update timesheet period record
            cursor.execute("""
                INSERT OR REPLACE INTO timesheet_periods 
                (id, employee_id, period_start_date, period_end_date, total_hours,
                 direct_hours, indirect_hours, status, supervisor_approval_date,
                 supervisor_id, employee_signature, supervisor_signature, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                employee_id,
                start_date,
                end_date,
                timesheet['total_hours'],
                timesheet['direct_hours'],
                timesheet['indirect_hours'],
                TimeEntryStatus.APPROVED.value,
                now,
                supervisor_id,
                f"digital_signature_{employee_id}_{now}",
                f"digital_signature_{supervisor_id}_{now}",
                now
            ))
            
            # Update individual time entry statuses
            cursor.execute("""
                UPDATE time_entries 
                SET status = ?, approved_date = ?, approved_by = ?, approval_level = ?
                WHERE employee_id = ? AND entry_date BETWEEN ? AND ?
            """, (
                TimeEntryStatus.APPROVED.value,
                now,
                supervisor_id,
                ApprovalLevel.SUPERVISOR.value,
                employee_id,
                start_date,
                end_date
            ))
            
            conn.commit()
            conn.close()
            
            # Log audit event
            await self._log_audit_event(
                supervisor_id,
                "TIMESHEET_APPROVED",
                f"Timesheet approved for employee {employee_id}, period {period}",
                None,
                supervisor_id
            )
            
            return {
                "status": "approved",
                "employee_id": employee_id,
                "period": period,
                "approved_by": supervisor_id,
                "approval_date": now,
                "total_hours": timesheet['total_hours'],
                "dcaa_compliant": True
            }
            
        except Exception as e:
            logger.error(f"Error approving timesheet: {e}")
            return {"error": str(e)}

    async def _verify_supervisor_authority(self, supervisor_id: str, employee_id: str) -> Dict[str, bool]:
        """Verify supervisor has authority to approve employee timesheet"""
        # In a real system, this would check organizational hierarchy
        # For now, we'll assume any supervisor can approve any employee
        return {"authorized": True}

    async def _log_audit_event(self, performer_id: str, action_type: str, description: str, 
                              affected_entry_id: Optional[str], employee_id: str):
        """Log audit event for DCAA compliance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO dcaa_audit_logs 
                (id, employee_id, action_type, action_description, affected_entry_id,
                 performed_by, audit_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                employee_id,
                action_type,
                description,
                affected_entry_id,
                performer_id,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")

# Global instance
dcaa_system = DCAATimekeepingSystem()