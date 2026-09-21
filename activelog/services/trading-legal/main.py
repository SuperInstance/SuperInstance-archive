#!/usr/bin/env python3

import os
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from contextlib import asynccontextmanager
import hashlib
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
import uvicorn

# Import routers
from routers.compliance import router as compliance_router
from routers.education import router as education_router
from routers.scaling import router as scaling_router
from routers.transition import router as transition_router

# Background tasks and database initialization
def init_database():
    """Initialize SQLite database with all required tables"""
    conn = sqlite3.connect('trading_legal.db')
    cursor = conn.cursor()
    
    # Legal compliance tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS legal_acceptances (
            acceptance_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            document_version TEXT NOT NULL,
            accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            is_valid BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Age verification
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS age_verifications (
            verification_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            date_of_birth DATE,
            verification_method TEXT NOT NULL,
            parent_consent BOOLEAN DEFAULT FALSE,
            parent_email TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verification_status TEXT DEFAULT 'pending',
            compliance_notes TEXT
        )
    ''')
    
    # Educational certifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certifications (
            certification_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            course_id TEXT NOT NULL,
            course_name TEXT NOT NULL,
            completion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            final_score INTEGER NOT NULL,
            passing_score INTEGER NOT NULL,
            total_time_minutes INTEGER,
            certificate_url TEXT,
            cpe_credits REAL DEFAULT 0,
            is_valid BOOLEAN DEFAULT TRUE,
            expiry_date TIMESTAMP
        )
    ''')
    
    # Educational courses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            course_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            difficulty_level TEXT NOT NULL,
            estimated_hours REAL NOT NULL,
            cpe_credits REAL DEFAULT 0,
            prerequisites TEXT, -- JSON array
            learning_objectives TEXT, -- JSON array
            course_content TEXT, -- JSON course structure
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Scaling metrics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scaling_metrics (
            metric_id TEXT PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metric_type TEXT NOT NULL,
            region TEXT,
            value REAL NOT NULL,
            metadata TEXT -- JSON additional data
        )
    ''')
    
    # Transition tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transition_readiness (
            user_id TEXT PRIMARY KEY,
            overall_score INTEGER DEFAULT 0,
            risk_assessment_score INTEGER DEFAULT 0,
            knowledge_assessment_score INTEGER DEFAULT 0,
            experience_level TEXT DEFAULT 'beginner',
            recommended_brokers TEXT, -- JSON array
            warnings TEXT, -- JSON array
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Broker integrations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broker_integrations (
            broker_id TEXT PRIMARY KEY,
            broker_name TEXT NOT NULL,
            api_status TEXT DEFAULT 'inactive',
            supported_regions TEXT, -- JSON array
            minimum_balance REAL DEFAULT 0,
            commission_structure TEXT, -- JSON
            features TEXT, -- JSON array
            integration_guide TEXT,
            is_recommended BOOLEAN DEFAULT FALSE,
            risk_level TEXT DEFAULT 'medium'
        )
    ''')
    
    # Insert sample courses
    sample_courses = [
        {
            'course_id': 'trading_basics_101',
            'title': 'Trading Fundamentals 101',
            'description': 'Complete introduction to stock market basics, order types, and market mechanics',
            'difficulty': 'beginner',
            'hours': 8.0,
            'cpe': 8.0,
            'objectives': ['Understand market structure', 'Learn order types', 'Risk management basics']
        },
        {
            'course_id': 'options_mastery',
            'title': 'Options Trading Mastery',
            'description': 'Advanced options strategies, Greeks, and risk management',
            'difficulty': 'advanced',
            'hours': 12.0,
            'cpe': 12.0,
            'objectives': ['Master options pricing', 'Advanced strategies', 'Risk management']
        },
        {
            'course_id': 'crypto_trading_cert',
            'title': 'Cryptocurrency Trading Certification',
            'description': 'Comprehensive guide to cryptocurrency markets and DeFi',
            'difficulty': 'intermediate',
            'hours': 6.0,
            'cpe': 6.0,
            'objectives': ['Blockchain fundamentals', 'Crypto trading', 'DeFi protocols']
        }
    ]
    
    for course in sample_courses:
        cursor.execute('''
            INSERT OR IGNORE INTO courses 
            (course_id, title, description, difficulty_level, estimated_hours, cpe_credits, learning_objectives)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (course['course_id'], course['title'], course['description'], 
              course['difficulty'], course['hours'], course['cpe'], 
              json.dumps(course['objectives'])))
    
    # Insert sample broker data
    sample_brokers = [
        {
            'broker_id': 'td_ameritrade',
            'name': 'TD Ameritrade',
            'regions': ['US'],
            'min_balance': 0.0,
            'features': ['Commission-free stocks', 'Advanced platform', 'Research tools'],
            'recommended': True,
            'risk': 'low'
        },
        {
            'broker_id': 'interactive_brokers',
            'name': 'Interactive Brokers',
            'regions': ['US', 'EU', 'APAC'],
            'min_balance': 0.0,
            'features': ['Global markets', 'Low costs', 'Professional tools'],
            'recommended': True,
            'risk': 'low'
        },
        {
            'broker_id': 'robinhood',
            'name': 'Robinhood',
            'regions': ['US'],
            'min_balance': 0.0,
            'features': ['Mobile-first', 'Commission-free', 'Crypto trading'],
            'recommended': False,
            'risk': 'medium'
        }
    ]
    
    for broker in sample_brokers:
        cursor.execute('''
            INSERT OR IGNORE INTO broker_integrations
            (broker_id, broker_name, supported_regions, minimum_balance, features, is_recommended, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (broker['broker_id'], broker['name'], json.dumps(broker['regions']),
              broker['min_balance'], json.dumps(broker['features']), 
              broker['recommended'], broker['risk']))
    
    conn.commit()
    conn.close()
    print("✅ Trading legal database initialized successfully")

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_database()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="ActiveLog Trading Legal & Scaling Infrastructure",
    description="Compliance, educational certification, and scaling infrastructure for paper trading platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(compliance_router, prefix="/api/compliance", tags=["compliance"])
app.include_router(education_router, prefix="/api/education", tags=["education"])
app.include_router(scaling_router, prefix="/api/scaling", tags=["scaling"])
app.include_router(transition_router, prefix="/api/transition", tags=["transition"])

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('trading_legal.db')

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "ActiveLog Trading Legal & Scaling Infrastructure",
        "version": "1.0.0",
        "status": "operational",
        "components": [
            "Legal compliance framework",
            "Educational certification system", 
            "Scaling infrastructure",
            "Real trading transition tools"
        ],
        "compliance_features": [
            "Age verification (COPPA compliant)",
            "Terms of service management",
            "Paper trading disclaimers",
            "Data privacy protection",
            "International law compliance"
        ],
        "scaling_features": [
            "Microservices architecture",
            "Regional data centers",
            "CDN integration",
            "Database sharding",
            "Load balancing"
        ]
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "database": "connected",
        "compliance_status": "active"
    }

# Legal disclaimer endpoint
@app.get("/disclaimers")
async def get_legal_disclaimers():
    """Get all legal disclaimers and warnings"""
    return {
        "paper_trading_disclaimer": {
            "title": "PAPER TRADING SIMULATION ONLY",
            "content": "This platform provides simulated trading for educational purposes only. No real money is involved. Past performance does not guarantee future results.",
            "version": "1.0",
            "mandatory": True
        },
        "no_financial_advice": {
            "title": "NOT FINANCIAL ADVICE",
            "content": "Content provided is for educational purposes only and does not constitute investment advice. Consult with qualified financial professionals before making investment decisions.",
            "version": "1.0", 
            "mandatory": True
        },
        "risk_warning": {
            "title": "INVESTMENT RISKS",
            "content": "All investments carry risk of loss. You may lose some or all of your invested capital. Only invest money you can afford to lose.",
            "version": "1.0",
            "mandatory": True
        },
        "age_restriction": {
            "title": "AGE REQUIREMENTS",
            "content": "Users under 13 require parental consent. Users 13-17 require parental supervision. Educational use only for minors.",
            "version": "1.0",
            "mandatory": True
        },
        "data_privacy": {
            "title": "DATA PRIVACY NOTICE",
            "content": "We collect minimal data for educational purposes only. Financial data is simulated and not real. See privacy policy for details.",
            "version": "1.0",
            "mandatory": False
        }
    }

# Terms of service endpoint
@app.get("/terms-of-service", response_class=HTMLResponse)
async def terms_of_service(request: Request):
    """Display terms of service for paper trading"""
    return templates.TemplateResponse("terms-of-service.html", {"request": request})

# Privacy policy endpoint  
@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Display privacy policy"""
    return templates.TemplateResponse("privacy-policy.html", {"request": request})

# Age verification endpoint
@app.post("/verify-age")
async def verify_age(
    user_id: str,
    date_of_birth: str,
    verification_method: str = "self_reported",
    parent_email: Optional[str] = None,
    parent_consent: bool = False
):
    """Verify user age for COPPA compliance"""
    
    try:
        birth_date = datetime.strptime(date_of_birth, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Calculate age
    today = datetime.now()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    # Determine verification status
    if age < 13:
        if not parent_consent or not parent_email:
            verification_status = "requires_parent_consent"
        else:
            verification_status = "pending_parent_verification"
    elif age < 18:
        verification_status = "minor_verified"
    else:
        verification_status = "adult_verified"
    
    # Store verification
    conn = get_db_connection()
    cursor = conn.cursor()
    
    verification_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT OR REPLACE INTO age_verifications
        (verification_id, user_id, date_of_birth, verification_method, 
         parent_consent, parent_email, verification_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (verification_id, user_id, date_of_birth, verification_method,
          parent_consent, parent_email, verification_status))
    
    conn.commit()
    conn.close()
    
    return {
        "verification_id": verification_id,
        "user_age": age,
        "verification_status": verification_status,
        "requires_parent_consent": age < 13,
        "is_minor": age < 18,
        "educational_restrictions": {
            "real_trading_blocked": age < 18,
            "parental_supervision_required": age < 18,
            "paper_trading_only": age < 21  # Conservative approach
        }
    }

# Legal document acceptance
@app.post("/accept-legal-document")
async def accept_legal_document(
    user_id: str,
    document_type: str,
    document_version: str,
    request: Request
):
    """Record acceptance of legal documents"""
    
    # Get client info for audit trail
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    acceptance_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO legal_acceptances
        (acceptance_id, user_id, document_type, document_version, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (acceptance_id, user_id, document_type, document_version, client_ip, user_agent))
    
    conn.commit()
    conn.close()
    
    return {
        "acceptance_id": acceptance_id,
        "message": "Legal document acceptance recorded",
        "document_type": document_type,
        "version": document_version,
        "timestamp": datetime.now()
    }

# Compliance dashboard
@app.get("/compliance-dashboard")
async def compliance_dashboard():
    """Get compliance metrics and status"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get acceptance statistics
    cursor.execute('''
        SELECT document_type, COUNT(*) as acceptances
        FROM legal_acceptances 
        WHERE is_valid = 1
        GROUP BY document_type
    ''')
    acceptances = cursor.fetchall()
    
    # Get age verification stats
    cursor.execute('''
        SELECT verification_status, COUNT(*) as count
        FROM age_verifications
        GROUP BY verification_status  
    ''')
    age_stats = cursor.fetchall()
    
    # Get recent compliance events
    cursor.execute('''
        SELECT document_type, COUNT(*) as count
        FROM legal_acceptances
        WHERE accepted_at > datetime('now', '-24 hours')
        GROUP BY document_type
    ''')
    recent_events = cursor.fetchall()
    
    conn.close()
    
    return {
        "compliance_status": "operational",
        "document_acceptances": [
            {"document_type": doc_type, "total_acceptances": count}
            for doc_type, count in acceptances
        ],
        "age_verification_stats": [
            {"status": status, "count": count}
            for status, count in age_stats
        ],
        "recent_compliance_events": [
            {"document_type": doc_type, "last_24h_acceptances": count}
            for doc_type, count in recent_events
        ],
        "compliance_score": 95.5,  # Mock compliance score
        "last_audit": "2024-12-01",
        "next_review": "2025-03-01"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8415))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )