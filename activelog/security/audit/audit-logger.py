#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import geoip2.database
import geoip2.errors
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import redis
import elasticsearch
from elasticsearch.helpers import bulk
import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class EventType(str, Enum):
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    PASSWORD_CHANGE = "password_change"
    API_ACCESS = "api_access"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    PERMISSION_CHANGE = "permission_change"
    ADMIN_ACTION = "admin_action"
    SECURITY_ALERT = "security_alert"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_ERROR = "system_error"
    COMPLIANCE_EVENT = "compliance_event"
    FINANCIAL_TRANSACTION = "financial_transaction"
    PII_ACCESS = "pii_access"
    GDPR_REQUEST = "gdpr_request"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceFramework(str, Enum):
    SOX = "sox"
    PCI = "pci"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"

@dataclass
class AuditEvent:
    event_id: str
    timestamp: datetime
    event_type: EventType
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    outcome: str  # success, failure, error
    risk_level: RiskLevel
    compliance_frameworks: List[ComplianceFramework]
    details: Dict[str, Any]
    context: Dict[str, Any]
    geolocation: Optional[Dict[str, str]] = None
    fingerprint: Optional[str] = None

class AuditEventRequest(BaseModel):
    event_type: EventType
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str
    outcome: str = "success"
    risk_level: RiskLevel = RiskLevel.LOW
    compliance_frameworks: List[ComplianceFramework] = []
    details: Dict[str, Any] = {}
    context: Dict[str, Any] = {}

    @validator('outcome')
    def validate_outcome(cls, v):
        if v not in ['success', 'failure', 'error']:
            raise ValueError('outcome must be success, failure, or error')
        return v

class ComplianceQuery(BaseModel):
    framework: ComplianceFramework
    start_date: datetime
    end_date: datetime
    user_id: Optional[str] = None
    event_types: Optional[List[EventType]] = None
    risk_levels: Optional[List[RiskLevel]] = None

class AuditLogger:
    def __init__(self):
        self.app = FastAPI(title="ActiveLog Audit Logger", version="1.0.0")
        self.db_pool = None
        self.redis_client = None
        self.es_client = None
        self.geoip_reader = None
        self.tracer = trace.get_tracer(__name__)
        
        self._setup_tracing()
        self._setup_database()
        self._setup_redis()
        self._setup_elasticsearch()
        self._setup_geoip()
        self._setup_routes()
        self._setup_middleware()

    def _setup_tracing(self):
        """Set up distributed tracing with Jaeger."""
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.set_tracer_provider(TracerProvider())
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        FastAPIInstrumentor.instrument_app(self.app)

    def _setup_database(self):
        """Set up PostgreSQL connection for audit log storage."""
        try:
            self.db_pool = psycopg2.pool.ThreadedConnectionPool(
                1, 20,
                host=os.getenv("POSTGRES_HOST", "localhost"),
                database=os.getenv("POSTGRES_DB", "activelog_audit"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "password"),
                port=int(os.getenv("POSTGRES_PORT", "5432"))
            )
            self._create_tables()
            logger.info("Database connection established")
        except Exception as e:
            logger.error("Database setup failed", error=str(e))

    def _setup_redis(self):
        """Set up Redis for caching and rate limiting."""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "3")),
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error("Redis setup failed", error=str(e))

    def _setup_elasticsearch(self):
        """Set up Elasticsearch for audit log indexing and search."""
        try:
            es_hosts = os.getenv("ELASTICSEARCH_HOSTS", "localhost:9200").split(",")
            self.es_client = elasticsearch.Elasticsearch(
                es_hosts,
                http_auth=(
                    os.getenv("ELASTICSEARCH_USERNAME"),
                    os.getenv("ELASTICSEARCH_PASSWORD")
                ) if os.getenv("ELASTICSEARCH_USERNAME") else None,
                verify_certs=False,
                ssl_show_warn=False
            )
            
            # Create audit log index if it doesn't exist
            self._create_elasticsearch_index()
            logger.info("Elasticsearch connection established")
        except Exception as e:
            logger.error("Elasticsearch setup failed", error=str(e))

    def _setup_geoip(self):
        """Set up GeoIP database for location tracking."""
        try:
            geoip_path = os.getenv("GEOIP_DB_PATH", "/usr/share/GeoIP/GeoLite2-City.mmdb")
            if os.path.exists(geoip_path):
                self.geoip_reader = geoip2.database.Reader(geoip_path)
                logger.info("GeoIP database loaded")
            else:
                logger.warning("GeoIP database not found", path=geoip_path)
        except Exception as e:
            logger.error("GeoIP setup failed", error=str(e))

    def _create_tables(self):
        """Create audit log tables in PostgreSQL."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id SERIAL PRIMARY KEY,
                        event_id UUID UNIQUE NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        event_type VARCHAR(100) NOT NULL,
                        user_id VARCHAR(255),
                        session_id VARCHAR(255),
                        ip_address INET,
                        user_agent TEXT,
                        resource_type VARCHAR(255),
                        resource_id VARCHAR(255),
                        action VARCHAR(255) NOT NULL,
                        outcome VARCHAR(50) NOT NULL,
                        risk_level VARCHAR(20) NOT NULL,
                        compliance_frameworks JSONB DEFAULT '[]',
                        details JSONB DEFAULT '{}',
                        context JSONB DEFAULT '{}',
                        geolocation JSONB,
                        fingerprint VARCHAR(64),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS compliance_reports (
                        id SERIAL PRIMARY KEY,
                        framework VARCHAR(50) NOT NULL,
                        report_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
                        report_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
                        total_events INTEGER NOT NULL,
                        high_risk_events INTEGER NOT NULL,
                        failed_events INTEGER NOT NULL,
                        report_data JSONB NOT NULL,
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        generated_by VARCHAR(255)
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS retention_policies (
                        id SERIAL PRIMARY KEY,
                        framework VARCHAR(50) UNIQUE NOT NULL,
                        retention_days INTEGER NOT NULL,
                        archive_after_days INTEGER,
                        encryption_required BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit_events(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_risk_level ON audit_events(risk_level)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_outcome ON audit_events(outcome)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_compliance ON audit_events USING GIN(compliance_frameworks)")
                
                # Insert default retention policies
                cursor.execute("""
                    INSERT INTO retention_policies (framework, retention_days, archive_after_days)
                    VALUES 
                        ('sox', 2555, 365),      -- 7 years for SOX
                        ('pci', 365, 90),        -- 1 year for PCI
                        ('gdpr', 2190, 730),     -- 6 years for GDPR
                        ('hipaa', 2190, 365),    -- 6 years for HIPAA
                        ('soc2', 1095, 365),     -- 3 years for SOC2
                        ('iso27001', 1095, 365)  -- 3 years for ISO27001
                    ON CONFLICT (framework) DO NOTHING
                """)
                
                conn.commit()
                logger.info("Database tables created/verified")
        finally:
            self.db_pool.putconn(conn)

    def _create_elasticsearch_index(self):
        """Create Elasticsearch index for audit logs."""
        if not self.es_client:
            return
            
        index_name = "activelog-audit-logs"
        
        if not self.es_client.indices.exists(index=index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "event_id": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "event_type": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "session_id": {"type": "keyword"},
                        "ip_address": {"type": "ip"},
                        "user_agent": {"type": "text"},
                        "resource_type": {"type": "keyword"},
                        "resource_id": {"type": "keyword"},
                        "action": {"type": "keyword"},
                        "outcome": {"type": "keyword"},
                        "risk_level": {"type": "keyword"},
                        "compliance_frameworks": {"type": "keyword"},
                        "details": {"type": "object", "enabled": False},
                        "context": {"type": "object", "enabled": False},
                        "geolocation": {
                            "properties": {
                                "country": {"type": "keyword"},
                                "city": {"type": "keyword"},
                                "latitude": {"type": "float"},
                                "longitude": {"type": "float"}
                            }
                        }
                    }
                },
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1
                }
            }
            
            self.es_client.indices.create(index=index_name, body=mapping)
            logger.info("Elasticsearch index created", index=index_name)

    def _get_geolocation(self, ip_address: str) -> Optional[Dict[str, str]]:
        """Get geolocation information for IP address."""
        if not self.geoip_reader or not ip_address:
            return None
            
        try:
            response = self.geoip_reader.city(ip_address)
            return {
                "country": response.country.name,
                "city": response.city.name,
                "latitude": str(response.location.latitude),
                "longitude": str(response.location.longitude)
            }
        except (geoip2.errors.AddressNotFoundError, Exception):
            return None

    def _generate_fingerprint(self, event: AuditEvent) -> str:
        """Generate a unique fingerprint for the audit event."""
        import hashlib
        
        fingerprint_data = f"{event.user_id}:{event.ip_address}:{event.user_agent}:{event.action}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

    async def log_audit_event(self, event_request: AuditEventRequest, 
                            request: Request) -> AuditEvent:
        """Log an audit event to all storage backends."""
        with self.tracer.start_as_current_span("log_audit_event") as span:
            event_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Extract request information
            ip_address = request.client.host
            user_agent = request.headers.get("User-Agent")
            
            # Get geolocation
            geolocation = self._get_geolocation(ip_address)
            
            # Create audit event
            audit_event = AuditEvent(
                event_id=event_id,
                timestamp=timestamp,
                event_type=event_request.event_type,
                user_id=event_request.user_id,
                session_id=event_request.session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                resource_type=event_request.resource_type,
                resource_id=event_request.resource_id,
                action=event_request.action,
                outcome=event_request.outcome,
                risk_level=event_request.risk_level,
                compliance_frameworks=event_request.compliance_frameworks,
                details=event_request.details,
                context=event_request.context,
                geolocation=geolocation
            )
            
            # Generate fingerprint
            audit_event.fingerprint = self._generate_fingerprint(audit_event)
            
            # Add span attributes
            span.set_attributes({
                "audit.event_id": event_id,
                "audit.event_type": event_request.event_type.value,
                "audit.user_id": event_request.user_id or "anonymous",
                "audit.risk_level": event_request.risk_level.value
            })
            
            # Store in PostgreSQL
            await self._store_in_postgres(audit_event)
            
            # Index in Elasticsearch
            await self._index_in_elasticsearch(audit_event)
            
            # Cache recent events in Redis
            await self._cache_in_redis(audit_event)
            
            # Trigger compliance checks
            await self._check_compliance_rules(audit_event)
            
            logger.info("Audit event logged", 
                       event_id=event_id, 
                       event_type=event_request.event_type.value,
                       user_id=event_request.user_id)
            
            return audit_event

    async def _store_in_postgres(self, event: AuditEvent):
        """Store audit event in PostgreSQL."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO audit_events 
                    (event_id, timestamp, event_type, user_id, session_id, ip_address,
                     user_agent, resource_type, resource_id, action, outcome, risk_level,
                     compliance_frameworks, details, context, geolocation, fingerprint)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event.event_id, event.timestamp, event.event_type.value,
                    event.user_id, event.session_id, event.ip_address,
                    event.user_agent, event.resource_type, event.resource_id,
                    event.action, event.outcome, event.risk_level.value,
                    json.dumps([f.value for f in event.compliance_frameworks]),
                    json.dumps(event.details), json.dumps(event.context),
                    json.dumps(event.geolocation) if event.geolocation else None,
                    event.fingerprint
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    async def _index_in_elasticsearch(self, event: AuditEvent):
        """Index audit event in Elasticsearch."""
        if not self.es_client:
            return
            
        try:
            doc = asdict(event)
            doc['timestamp'] = event.timestamp.isoformat()
            doc['event_type'] = event.event_type.value
            doc['risk_level'] = event.risk_level.value
            doc['compliance_frameworks'] = [f.value for f in event.compliance_frameworks]
            
            self.es_client.index(
                index="activelog-audit-logs",
                id=event.event_id,
                body=doc
            )
        except Exception as e:
            logger.error("Failed to index in Elasticsearch", error=str(e))

    async def _cache_in_redis(self, event: AuditEvent):
        """Cache recent audit event in Redis."""
        if not self.redis_client:
            return
            
        try:
            # Store recent events for quick access
            event_data = {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "action": event.action,
                "outcome": event.outcome,
                "risk_level": event.risk_level.value
            }
            
            # Store in sorted set by timestamp
            self.redis_client.zadd(
                f"recent_events:{event.user_id or 'anonymous'}",
                {json.dumps(event_data): event.timestamp.timestamp()}
            )
            
            # Keep only last 100 events per user
            self.redis_client.zremrangebyrank(
                f"recent_events:{event.user_id or 'anonymous'}",
                0, -101
            )
            
            # Set expiry on the key
            self.redis_client.expire(
                f"recent_events:{event.user_id or 'anonymous'}",
                86400  # 24 hours
            )
            
        except Exception as e:
            logger.error("Failed to cache in Redis", error=str(e))

    async def _check_compliance_rules(self, event: AuditEvent):
        """Check event against compliance rules and trigger alerts."""
        # SOX compliance checks
        if ComplianceFramework.SOX in event.compliance_frameworks:
            if event.event_type == EventType.FINANCIAL_TRANSACTION and event.outcome == "failure":
                await self._trigger_compliance_alert("SOX", event, "Failed financial transaction")
        
        # PCI compliance checks
        if ComplianceFramework.PCI in event.compliance_frameworks:
            if event.risk_level == RiskLevel.CRITICAL:
                await self._trigger_compliance_alert("PCI", event, "Critical security event")
        
        # GDPR compliance checks
        if ComplianceFramework.GDPR in event.compliance_frameworks:
            if event.event_type == EventType.PII_ACCESS and not event.user_id:
                await self._trigger_compliance_alert("GDPR", event, "Anonymous PII access")

    async def _trigger_compliance_alert(self, framework: str, event: AuditEvent, reason: str):
        """Trigger compliance alert for suspicious activity."""
        alert_data = {
            "framework": framework,
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "reason": reason,
            "event_type": event.event_type.value,
            "user_id": event.user_id,
            "risk_level": event.risk_level.value
        }
        
        # Store alert
        if self.redis_client:
            self.redis_client.lpush("compliance_alerts", json.dumps(alert_data))
            self.redis_client.expire("compliance_alerts", 86400)  # 24 hours
        
        logger.warning("Compliance alert triggered", **alert_data)

    def _setup_middleware(self):
        """Set up middleware for the FastAPI app."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:8088"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.post("/api/v1/audit/log")
        async def log_event(event_request: AuditEventRequest, request: Request):
            """Log an audit event."""
            audit_event = await self.log_audit_event(event_request, request)
            return {
                "event_id": audit_event.event_id,
                "timestamp": audit_event.timestamp.isoformat(),
                "status": "logged"
            }

        @self.app.get("/api/v1/audit/events/{event_id}")
        async def get_event(event_id: str):
            """Get a specific audit event."""
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM audit_events WHERE event_id = %s",
                        (event_id,)
                    )
                    event = cursor.fetchone()
                    if not event:
                        raise HTTPException(status_code=404, detail="Event not found")
                    return dict(event)
            finally:
                self.db_pool.putconn(conn)

        @self.app.get("/api/v1/audit/events")
        async def search_events(
            user_id: Optional[str] = None,
            event_type: Optional[EventType] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            limit: int = 100,
            offset: int = 0
        ):
            """Search audit events with filters."""
            conn = self.db_pool.getconn()
            try:
                query = "SELECT * FROM audit_events WHERE 1=1"
                params = []
                
                if user_id:
                    query += " AND user_id = %s"
                    params.append(user_id)
                
                if event_type:
                    query += " AND event_type = %s"
                    params.append(event_type.value)
                
                if start_date:
                    query += " AND timestamp >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= %s"
                    params.append(end_date)
                
                query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    events = cursor.fetchall()
                    return {"events": [dict(event) for event in events]}
            finally:
                self.db_pool.putconn(conn)

        @self.app.post("/api/v1/compliance/report")
        async def generate_compliance_report(query: ComplianceQuery):
            """Generate a compliance report."""
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Base query for compliance events
                    sql = """
                        SELECT event_type, risk_level, outcome, COUNT(*) as count
                        FROM audit_events 
                        WHERE %s = ANY(compliance_frameworks)
                        AND timestamp >= %s AND timestamp <= %s
                    """
                    params = [query.framework.value, query.start_date, query.end_date]
                    
                    if query.user_id:
                        sql += " AND user_id = %s"
                        params.append(query.user_id)
                    
                    if query.event_types:
                        sql += " AND event_type = ANY(%s)"
                        params.append([et.value for et in query.event_types])
                    
                    if query.risk_levels:
                        sql += " AND risk_level = ANY(%s)"
                        params.append([rl.value for rl in query.risk_levels])
                    
                    sql += " GROUP BY event_type, risk_level, outcome ORDER BY count DESC"
                    
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    
                    # Calculate summary statistics
                    total_events = sum(row['count'] for row in results)
                    high_risk_events = sum(row['count'] for row in results 
                                         if row['risk_level'] in ['high', 'critical'])
                    failed_events = sum(row['count'] for row in results 
                                      if row['outcome'] == 'failure')
                    
                    report_data = {
                        "framework": query.framework.value,
                        "period_start": query.start_date.isoformat(),
                        "period_end": query.end_date.isoformat(),
                        "total_events": total_events,
                        "high_risk_events": high_risk_events,
                        "failed_events": failed_events,
                        "event_breakdown": [dict(row) for row in results]
                    }
                    
                    # Store the report
                    cursor.execute("""
                        INSERT INTO compliance_reports 
                        (framework, report_period_start, report_period_end, 
                         total_events, high_risk_events, failed_events, report_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        query.framework.value, query.start_date, query.end_date,
                        total_events, high_risk_events, failed_events,
                        json.dumps(report_data)
                    ))
                    
                    report_id = cursor.fetchone()['id']
                    conn.commit()
                    
                    return {"report_id": report_id, "report": report_data}
            finally:
                self.db_pool.putconn(conn)

        @self.app.get("/api/v1/compliance/alerts")
        async def get_compliance_alerts():
            """Get recent compliance alerts."""
            if not self.redis_client:
                return {"alerts": []}
            
            try:
                alerts_raw = self.redis_client.lrange("compliance_alerts", 0, 50)
                alerts = [json.loads(alert) for alert in alerts_raw]
                return {"alerts": alerts}
            except Exception as e:
                logger.error("Failed to get compliance alerts", error=str(e))
                return {"alerts": [], "error": str(e)}

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": "healthy" if self.db_pool else "unhealthy",
                    "redis": "healthy" if self.redis_client else "unhealthy",
                    "elasticsearch": "healthy" if self.es_client else "unhealthy"
                }
            }
            
            overall_healthy = all(
                status == "healthy" 
                for status in health_status["services"].values()
            )
            
            if not overall_healthy:
                health_status["status"] = "degraded"
            
            return health_status

# Service instance
audit_logger = AuditLogger()

@audit_logger.app.on_event("startup")
async def startup_event():
    logger.info("Audit logger service started")

@audit_logger.app.on_event("shutdown") 
async def shutdown_event():
    if audit_logger.db_pool:
        audit_logger.db_pool.closeall()
    if audit_logger.geoip_reader:
        audit_logger.geoip_reader.close()
    logger.info("Audit logger service stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "audit-logger:audit_logger.app",
        host="0.0.0.0",
        port=8088,
        reload=False
    )