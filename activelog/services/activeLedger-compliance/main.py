#!/usr/bin/env python3
"""
ActiveLedger Compliance Server
Regulatory reporting and compliance monitoring system
Instance: t3.medium
"""

import asyncio
import json
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import aioredis
import sqlite3
import requests
import hashlib
import hmac
import os
from enum import Enum

app = FastAPI(title="ActiveLedger Compliance Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ComplianceRuleType(Enum):
    KYC = "kyc"
    AML = "aml"
    POSITION_LIMITS = "position_limits"
    TRANSACTION_LIMITS = "transaction_limits"
    MARKET_MANIPULATION = "market_manipulation"
    INSIDER_TRADING = "insider_trading"

class ViolationSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ComplianceRule:
    id: str
    rule_type: ComplianceRuleType
    name: str
    description: str
    parameters: Dict[str, Any]
    enabled: bool
    created_timestamp: float
    updated_timestamp: float

@dataclass
class ComplianceViolation:
    id: str
    user_id: str
    rule_id: str
    rule_type: ComplianceRuleType
    severity: ViolationSeverity
    description: str
    transaction_data: Dict[str, Any]
    timestamp: float
    resolved: bool = False
    resolution_notes: Optional[str] = None
    resolution_timestamp: Optional[float] = None

@dataclass
class RegulatoryReport:
    id: str
    report_type: str
    period_start: float
    period_end: float
    data: Dict[str, Any]
    generated_timestamp: float
    submitted: bool = False
    submission_timestamp: Optional[float] = None

class ComplianceEngine:
    def __init__(self):
        self.redis_client = None
        self.db_path = "data/compliance.db"
        self.rules: Dict[str, ComplianceRule] = {}
        self._init_database()
        self._load_default_rules()
        
    def _init_database(self):
        """Initialize SQLite database for compliance data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Compliance rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_rules (
                id TEXT PRIMARY KEY,
                rule_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                parameters TEXT NOT NULL,
                enabled BOOLEAN NOT NULL,
                created_timestamp REAL NOT NULL,
                updated_timestamp REAL NOT NULL
            )
        ''')
        
        # Compliance violations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_violations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                transaction_data TEXT NOT NULL,
                timestamp REAL NOT NULL,
                resolved BOOLEAN NOT NULL DEFAULT 0,
                resolution_notes TEXT,
                resolution_timestamp REAL
            )
        ''')
        
        # Regulatory reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regulatory_reports (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                period_start REAL NOT NULL,
                period_end REAL NOT NULL,
                data TEXT NOT NULL,
                generated_timestamp REAL NOT NULL,
                submitted BOOLEAN NOT NULL DEFAULT 0,
                submission_timestamp REAL
            )
        ''')
        
        # KYC data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kyc_data (
                user_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                nationality TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                document_type TEXT NOT NULL,
                document_number TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                verification_timestamp REAL,
                risk_score INTEGER NOT NULL DEFAULT 0,
                pep_status BOOLEAN NOT NULL DEFAULT 0,
                sanctions_check BOOLEAN NOT NULL DEFAULT 0
            )
        ''')
        
        # Transaction monitoring table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_monitoring (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                counterparty TEXT,
                timestamp REAL NOT NULL,
                risk_score INTEGER NOT NULL DEFAULT 0,
                flagged BOOLEAN NOT NULL DEFAULT 0,
                review_status TEXT DEFAULT 'pending'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_default_rules(self):
        """Load default compliance rules"""
        default_rules = [
            ComplianceRule(
                id="kyc_required",
                rule_type=ComplianceRuleType.KYC,
                name="KYC Required",
                description="Users must complete KYC verification before trading",
                parameters={"required": True, "max_unverified_amount": "1000"},
                enabled=True,
                created_timestamp=time.time(),
                updated_timestamp=time.time()
            ),
            ComplianceRule(
                id="daily_transaction_limit",
                rule_type=ComplianceRuleType.TRANSACTION_LIMITS,
                name="Daily Transaction Limit",
                description="Maximum daily transaction amount per user",
                parameters={"limit": "50000", "currency": "CC"},
                enabled=True,
                created_timestamp=time.time(),
                updated_timestamp=time.time()
            ),
            ComplianceRule(
                id="large_transaction_reporting",
                rule_type=ComplianceRuleType.AML,
                name="Large Transaction Reporting",
                description="Report transactions above threshold",
                parameters={"threshold": "10000", "currency": "CC"},
                enabled=True,
                created_timestamp=time.time(),
                updated_timestamp=time.time()
            ),
            ComplianceRule(
                id="position_concentration_limit",
                rule_type=ComplianceRuleType.POSITION_LIMITS,
                name="Position Concentration Limit",
                description="Maximum position size relative to total portfolio",
                parameters={"max_percentage": "20", "check_frequency": "daily"},
                enabled=True,
                created_timestamp=time.time(),
                updated_timestamp=time.time()
            ),
            ComplianceRule(
                id="suspicious_pattern_detection",
                rule_type=ComplianceRuleType.MARKET_MANIPULATION,
                name="Suspicious Pattern Detection",
                description="Detect potential market manipulation patterns",
                parameters={"wash_trading_threshold": "5", "layering_threshold": "10"},
                enabled=True,
                created_timestamp=time.time(),
                updated_timestamp=time.time()
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.id] = rule
            self._store_rule(rule)
    
    def _store_rule(self, rule: ComplianceRule):
        """Store compliance rule in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO compliance_rules
            (id, rule_type, name, description, parameters, enabled, created_timestamp, updated_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rule.id,
            rule.rule_type.value,
            rule.name,
            rule.description,
            json.dumps(rule.parameters),
            rule.enabled,
            rule.created_timestamp,
            rule.updated_timestamp
        ))
        
        conn.commit()
        conn.close()
    
    async def initialize_redis(self):
        self.redis_client = await aioredis.from_url("redis://localhost:6379")
    
    async def check_transaction_compliance(self, transaction_data: Dict[str, Any]) -> List[ComplianceViolation]:
        """Check transaction against all compliance rules"""
        violations = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
                
            violation = None
            
            if rule.rule_type == ComplianceRuleType.KYC:
                violation = await self._check_kyc_compliance(transaction_data, rule)
            elif rule.rule_type == ComplianceRuleType.TRANSACTION_LIMITS:
                violation = await self._check_transaction_limits(transaction_data, rule)
            elif rule.rule_type == ComplianceRuleType.AML:
                violation = await self._check_aml_compliance(transaction_data, rule)
            elif rule.rule_type == ComplianceRuleType.POSITION_LIMITS:
                violation = await self._check_position_limits(transaction_data, rule)
            elif rule.rule_type == ComplianceRuleType.MARKET_MANIPULATION:
                violation = await self._check_market_manipulation(transaction_data, rule)
            
            if violation:
                violations.append(violation)
                self._store_violation(violation)
        
        return violations
    
    async def _check_kyc_compliance(self, transaction_data: Dict[str, Any], rule: ComplianceRule) -> Optional[ComplianceViolation]:
        """Check KYC compliance"""
        user_id = transaction_data.get('user_id')
        if not user_id:
            return None
            
        # Check if user has completed KYC
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT verification_status FROM kyc_data WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or row[0] != 'verified':
            amount = Decimal(str(transaction_data.get('amount', 0)))
            max_unverified = Decimal(rule.parameters.get('max_unverified_amount', '1000'))
            
            if amount > max_unverified:
                return ComplianceViolation(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    rule_id=rule.id,
                    rule_type=rule.rule_type,
                    severity=ViolationSeverity.HIGH,
                    description=f"KYC verification required for transaction amount {amount}",
                    transaction_data=transaction_data,
                    timestamp=time.time()
                )
        
        return None
    
    async def _check_transaction_limits(self, transaction_data: Dict[str, Any], rule: ComplianceRule) -> Optional[ComplianceViolation]:
        """Check transaction limits"""
        user_id = transaction_data.get('user_id')
        amount = Decimal(str(transaction_data.get('amount', 0)))
        currency = transaction_data.get('currency', 'CC')
        
        if currency != rule.parameters.get('currency'):
            return None
        
        # Check daily limit
        daily_limit = Decimal(rule.parameters.get('limit', '50000'))
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(CAST(amount AS REAL)) FROM transaction_monitoring 
            WHERE user_id = ? AND currency = ? AND timestamp >= ?
        ''', (user_id, currency, today_start))
        
        row = cursor.fetchone()
        conn.close()
        
        daily_total = Decimal(str(row[0] or 0)) + amount
        
        if daily_total > daily_limit:
            return ComplianceViolation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                rule_id=rule.id,
                rule_type=rule.rule_type,
                severity=ViolationSeverity.MEDIUM,
                description=f"Daily transaction limit exceeded: {daily_total} > {daily_limit}",
                transaction_data=transaction_data,
                timestamp=time.time()
            )
        
        return None
    
    async def _check_aml_compliance(self, transaction_data: Dict[str, Any], rule: ComplianceRule) -> Optional[ComplianceViolation]:
        """Check AML compliance"""
        amount = Decimal(str(transaction_data.get('amount', 0)))
        threshold = Decimal(rule.parameters.get('threshold', '10000'))
        
        if amount >= threshold:
            # This would be reported to authorities
            return ComplianceViolation(
                id=str(uuid.uuid4()),
                user_id=transaction_data.get('user_id'),
                rule_id=rule.id,
                rule_type=rule.rule_type,
                severity=ViolationSeverity.MEDIUM,
                description=f"Large transaction requiring AML reporting: {amount}",
                transaction_data=transaction_data,
                timestamp=time.time()
            )
        
        return None
    
    async def _check_position_limits(self, transaction_data: Dict[str, Any], rule: ComplianceRule) -> Optional[ComplianceViolation]:
        """Check position limits"""
        # This would check against user's portfolio
        # Placeholder implementation
        return None
    
    async def _check_market_manipulation(self, transaction_data: Dict[str, Any], rule: ComplianceRule) -> Optional[ComplianceViolation]:
        """Check for market manipulation patterns"""
        # This would analyze trading patterns
        # Placeholder implementation
        return None
    
    def _store_violation(self, violation: ComplianceViolation):
        """Store compliance violation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO compliance_violations
            (id, user_id, rule_id, rule_type, severity, description, transaction_data, timestamp, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            violation.id,
            violation.user_id,
            violation.rule_id,
            violation.rule_type.value,
            violation.severity.value,
            violation.description,
            json.dumps(violation.transaction_data),
            violation.timestamp,
            violation.resolved
        ))
        
        conn.commit()
        conn.close()
    
    def record_transaction(self, transaction_data: Dict[str, Any]):
        """Record transaction for monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transaction_monitoring
            (id, user_id, transaction_id, transaction_type, amount, currency, counterparty, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            transaction_data.get('user_id'),
            transaction_data.get('transaction_id'),
            transaction_data.get('transaction_type'),
            str(transaction_data.get('amount', 0)),
            transaction_data.get('currency', 'CC'),
            transaction_data.get('counterparty'),
            time.time()
        ))
        
        conn.commit()
        conn.close()
    
    async def generate_regulatory_report(self, report_type: str, period_days: int = 30) -> RegulatoryReport:
        """Generate regulatory report"""
        period_end = time.time()
        period_start = period_end - (period_days * 24 * 60 * 60)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get transaction data for period
        cursor.execute('''
            SELECT transaction_type, currency, SUM(CAST(amount AS REAL)), COUNT(*)
            FROM transaction_monitoring 
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY transaction_type, currency
        ''', (period_start, period_end))
        
        transaction_summary = {}
        for row in cursor.fetchall():
            key = f"{row[0]}_{row[1]}"
            transaction_summary[key] = {
                'total_amount': row[2],
                'transaction_count': row[3]
            }
        
        # Get violations for period
        cursor.execute('''
            SELECT rule_type, severity, COUNT(*)
            FROM compliance_violations 
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY rule_type, severity
        ''', (period_start, period_end))
        
        violation_summary = {}
        for row in cursor.fetchall():
            key = f"{row[0]}_{row[1]}"
            violation_summary[key] = row[2]
        
        conn.close()
        
        report_data = {
            'period_start': period_start,
            'period_end': period_end,
            'transaction_summary': transaction_summary,
            'violation_summary': violation_summary,
            'total_users_active': len(set(transaction_summary.keys())),
            'compliance_score': self._calculate_compliance_score(violation_summary)
        }
        
        report = RegulatoryReport(
            id=str(uuid.uuid4()),
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            data=report_data,
            generated_timestamp=time.time()
        )
        
        self._store_report(report)
        return report
    
    def _calculate_compliance_score(self, violations: Dict[str, int]) -> float:
        """Calculate overall compliance score"""
        if not violations:
            return 100.0
        
        total_violations = sum(violations.values())
        weighted_score = 0
        
        for key, count in violations.items():
            severity = key.split('_')[-1]
            weight = {
                'low': 1,
                'medium': 2,
                'high': 4,
                'critical': 8
            }.get(severity, 1)
            weighted_score += count * weight
        
        # Calculate score (100 - penalty)
        penalty = min(weighted_score * 2, 95)  # Max penalty of 95
        return 100.0 - penalty
    
    def _store_report(self, report: RegulatoryReport):
        """Store regulatory report in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO regulatory_reports
            (id, report_type, period_start, period_end, data, generated_timestamp, submitted)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.id,
            report.report_type,
            report.period_start,
            report.period_end,
            json.dumps(report.data),
            report.generated_timestamp,
            report.submitted
        ))
        
        conn.commit()
        conn.close()

# Initialize compliance engine
compliance_engine = ComplianceEngine()

@app.on_event("startup")
async def startup_event():
    await compliance_engine.initialize_redis()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "compliance-server"}

@app.post("/api/compliance/check")
async def check_compliance(transaction_data: dict):
    """Check transaction compliance"""
    violations = await compliance_engine.check_transaction_compliance(transaction_data)
    
    # Record transaction for monitoring
    compliance_engine.record_transaction(transaction_data)
    
    return {
        "success": True,
        "compliant": len(violations) == 0,
        "violations": [asdict(v) for v in violations]
    }

@app.get("/api/compliance/violations")
async def get_violations(user_id: str = None, resolved: bool = None, limit: int = 50):
    """Get compliance violations"""
    conn = sqlite3.connect(compliance_engine.db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM compliance_violations WHERE 1=1"
    params = []
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    if resolved is not None:
        query += " AND resolved = ?"
        params.append(resolved)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    columns = ['id', 'user_id', 'rule_id', 'rule_type', 'severity', 'description', 
              'transaction_data', 'timestamp', 'resolved', 'resolution_notes', 'resolution_timestamp']
    
    violations = []
    for row in rows:
        violation_data = dict(zip(columns, row))
        violation_data['transaction_data'] = json.loads(violation_data['transaction_data'])
        violations.append(violation_data)
    
    return {"success": True, "violations": violations}

@app.post("/api/compliance/reports")
async def generate_report(report_type: str, period_days: int = 30):
    """Generate regulatory report"""
    report = await compliance_engine.generate_regulatory_report(report_type, period_days)
    return {"success": True, "report": asdict(report)}

@app.get("/api/compliance/reports")
async def get_reports(limit: int = 20):
    """Get regulatory reports"""
    conn = sqlite3.connect(compliance_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM regulatory_reports 
        ORDER BY generated_timestamp DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    columns = ['id', 'report_type', 'period_start', 'period_end', 'data', 
              'generated_timestamp', 'submitted', 'submission_timestamp']
    
    reports = []
    for row in rows:
        report_data = dict(zip(columns, row))
        report_data['data'] = json.loads(report_data['data'])
        reports.append(report_data)
    
    return {"success": True, "reports": reports}

@app.get("/api/compliance/dashboard")
async def compliance_dashboard():
    """Get compliance dashboard data"""
    conn = sqlite3.connect(compliance_engine.db_path)
    cursor = conn.cursor()
    
    # Get recent violations count
    week_ago = time.time() - (7 * 24 * 60 * 60)
    cursor.execute('''
        SELECT COUNT(*) FROM compliance_violations 
        WHERE timestamp >= ?
    ''', (week_ago,))
    recent_violations = cursor.fetchone()[0]
    
    # Get unresolved violations count
    cursor.execute('SELECT COUNT(*) FROM compliance_violations WHERE resolved = 0')
    unresolved_violations = cursor.fetchone()[0]
    
    # Get compliance score
    cursor.execute('''
        SELECT rule_type, severity, COUNT(*)
        FROM compliance_violations 
        WHERE timestamp >= ?
        GROUP BY rule_type, severity
    ''', (week_ago,))
    
    violation_summary = {}
    for row in cursor.fetchall():
        key = f"{row[0]}_{row[1]}"
        violation_summary[key] = row[2]
    
    compliance_score = compliance_engine._calculate_compliance_score(violation_summary)
    
    conn.close()
    
    return {
        "success": True,
        "dashboard": {
            "recent_violations": recent_violations,
            "unresolved_violations": unresolved_violations,
            "compliance_score": compliance_score,
            "status": "good" if compliance_score > 90 else "warning" if compliance_score > 70 else "critical"
        }
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8502))
    uvicorn.run(app, host="0.0.0.0", port=port)