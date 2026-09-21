#!/usr/bin/env python3
"""
Fundraising Platform for ActiveLog
Enables app owners to raise funds through equity crowdfunding
Port: 8412
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import sqlite3
import json
import os
import uuid
from datetime import datetime, timedelta
import hashlib

# Initialize FastAPI app
app = FastAPI(
    title="ActiveLog Fundraising Platform",
    description="Equity crowdfunding platform for app developers",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database setup
DATABASE_PATH = "fundraising_platform.db"

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # App listings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_listings (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            app_name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            equity_percentage REAL,
            target_amount REAL,
            current_amount REAL DEFAULT 0,
            minimum_investment REAL DEFAULT 100,
            maximum_investment REAL,
            pitch_deck_url TEXT,
            video_url TEXT,
            team_info TEXT,
            roadmap TEXT,
            use_of_funds TEXT,
            investment_terms TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT,
            end_date TEXT,
            milestones TEXT
        )
    ''')
    
    # Financial projections table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_projections (
            id TEXT PRIMARY KEY,
            listing_id TEXT,
            year INTEGER,
            revenue REAL,
            expenses REAL,
            profit REAL,
            users INTEGER,
            growth_rate REAL,
            FOREIGN KEY (listing_id) REFERENCES app_listings (id)
        )
    ''')
    
    # Investments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id TEXT PRIMARY KEY,
            listing_id TEXT,
            investor_id TEXT,
            amount REAL,
            equity_percentage REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            milestone_releases TEXT,
            FOREIGN KEY (listing_id) REFERENCES app_listings (id)
        )
    ''')
    
    # Due diligence data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS due_diligence (
            id TEXT PRIMARY KEY,
            listing_id TEXT,
            revenue_verified BOOLEAN DEFAULT 0,
            user_growth_data TEXT,
            code_quality_score REAL,
            security_score REAL,
            legal_structure TEXT,
            competitive_analysis TEXT,
            market_size REAL,
            risk_disclosures TEXT,
            last_updated TEXT,
            FOREIGN KEY (listing_id) REFERENCES app_listings (id)
        )
    ''')
    
    # Educational content
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS educational_content (
            id TEXT PRIMARY KEY,
            title TEXT,
            content_type TEXT,
            content TEXT,
            category TEXT,
            difficulty_level TEXT,
            created_at TEXT
        )
    ''')
    
    # Investor updates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investor_updates (
            id TEXT PRIMARY KEY,
            listing_id TEXT,
            title TEXT,
            content TEXT,
            milestone_achieved TEXT,
            financial_update TEXT,
            created_at TEXT,
            FOREIGN KEY (listing_id) REFERENCES app_listings (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

# Pydantic models
class AppListing(BaseModel):
    app_name: str
    description: str
    category: str
    equity_percentage: float
    target_amount: float
    minimum_investment: float = 100
    maximum_investment: Optional[float] = None
    team_info: str
    roadmap: str
    use_of_funds: str
    investment_terms: str
    end_date: str

class FinancialProjection(BaseModel):
    year: int
    revenue: float
    expenses: float
    profit: float
    users: int
    growth_rate: float

class Investment(BaseModel):
    listing_id: str
    amount: float

class DueDiligence(BaseModel):
    revenue_verified: bool
    user_growth_data: str
    code_quality_score: float
    security_score: float
    legal_structure: str
    competitive_analysis: str
    market_size: float
    risk_disclosures: str

class EducationalContent(BaseModel):
    title: str
    content_type: str
    content: str
    category: str
    difficulty_level: str

class InvestorUpdate(BaseModel):
    title: str
    content: str
    milestone_achieved: Optional[str] = None
    financial_update: Optional[str] = None

# Helper functions
def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

def generate_id():
    return str(uuid.uuid4())

# Import routers
from routers import due_diligence, investments, education

# Include routers
app.include_router(due_diligence.router)
app.include_router(investments.router)
app.include_router(education.router)

# Routes

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Fundraising platform dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ActiveLog Fundraising Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .section { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .button { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            .button:hover { background: #2980b9; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .metric { text-align: center; padding: 15px; background: #ecf0f1; border-radius: 4px; }
            .metric h3 { margin: 0; color: #2c3e50; }
            .metric p { font-size: 24px; font-weight: bold; margin: 10px 0 0 0; color: #27ae60; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 ActiveLog Fundraising Platform</h1>
            <p>Equity crowdfunding for innovative app developers</p>
        </div>
        
        <div class="grid">
            <div class="section">
                <h3>📊 Platform Metrics</h3>
                <div class="grid">
                    <div class="metric">
                        <h3>Active Listings</h3>
                        <p id="active-listings">0</p>
                    </div>
                    <div class="metric">
                        <h3>Total Raised</h3>
                        <p id="total-raised">$0</p>
                    </div>
                    <div class="metric">
                        <h3>Investors</h3>
                        <p id="total-investors">0</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h3>🏢 For App Owners</h3>
                <p>List your app for equity crowdfunding</p>
                <button class="button" onclick="window.location.href='/docs#/Listings/create_listing_listings_post'">Create Listing</button>
                <button class="button" onclick="window.location.href='/docs#/Due%20Diligence'">Add Due Diligence</button>
                <button class="button" onclick="window.location.href='/docs#/Education/pitch_guide_education_pitch_guide_get'">Pitch Guide</button>
            </div>
            
            <div class="section">
                <h3>💰 For Investors</h3>
                <p>Discover and invest in promising apps</p>
                <button class="button" onclick="window.location.href='/docs#/Listings/get_listings_listings_get'">Browse Listings</button>
                <button class="button" onclick="window.location.href='/docs#/Education/valuation_calculator_education_valuation_calculator_get'">Valuation Calculator</button>
                <button class="button" onclick="window.location.href='/docs#/Investments/make_investment_investments_post'">Make Investment</button>
            </div>
        </div>
        
        <div class="section">
            <h3>📚 Educational Resources</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                <button class="button" onclick="window.location.href='/docs#/Education/pitch_guide_education_pitch_guide_get'">How to Pitch</button>
                <button class="button" onclick="window.location.href='/docs#/Education/valuation_calculator_education_valuation_calculator_get'">Valuation Calculator</button>
                <button class="button" onclick="window.location.href='/docs#/Education/term_sheet_generator_education_term_sheet_generator_get'">Term Sheet Generator</button>
                <button class="button" onclick="window.location.href='/docs#/Education/success_stories_education_success_stories_get'">Success Stories</button>
                <button class="button" onclick="window.location.href='/docs#/Education/ai_pitch_practice_education_ai_pitch_practice_post'">AI Pitch Practice</button>
            </div>
        </div>
        
        <div class="section">
            <h3>🔧 API Documentation</h3>
            <p>Complete API documentation for developers</p>
            <button class="button" onclick="window.location.href='/docs'">View API Docs</button>
            <button class="button" onclick="window.location.href='/health'">Health Check</button>
        </div>

        <script>
            // Load metrics
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('active-listings').textContent = data.active_listings || 0;
                    document.getElementById('total-raised').textContent = '$' + (data.total_raised || 0).toLocaleString();
                    document.getElementById('total-investors').textContent = data.total_investors || 0;
                })
                .catch(err => console.log('Metrics loading...'));
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fundraising-platform", "port": 8412}

@app.get("/api/metrics")
async def get_metrics():
    """Get platform metrics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Active listings
    cursor.execute("SELECT COUNT(*) FROM app_listings WHERE status = 'active'")
    active_listings = cursor.fetchone()[0]
    
    # Total raised
    cursor.execute("SELECT COALESCE(SUM(current_amount), 0) FROM app_listings")
    total_raised = cursor.fetchone()[0]
    
    # Total investors
    cursor.execute("SELECT COUNT(DISTINCT investor_id) FROM investments WHERE status = 'confirmed'")
    total_investors = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "active_listings": active_listings,
        "total_raised": total_raised,
        "total_investors": total_investors
    }

# LISTING SYSTEM ENDPOINTS

@app.post("/listings")
async def create_listing(listing: AppListing, owner_id: str = "demo-user"):
    """Create a new app listing for fundraising"""
    listing_id = generate_id()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO app_listings (
            id, owner_id, app_name, description, category, equity_percentage,
            target_amount, minimum_investment, maximum_investment, team_info,
            roadmap, use_of_funds, investment_terms, created_at, end_date,
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        listing_id, owner_id, listing.app_name, listing.description,
        listing.category, listing.equity_percentage, listing.target_amount,
        listing.minimum_investment, listing.maximum_investment, listing.team_info,
        listing.roadmap, listing.use_of_funds, listing.investment_terms,
        datetime.now().isoformat(), listing.end_date, "draft"
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "listing_id": listing_id,
        "message": "Listing created successfully",
        "status": "draft"
    }

@app.get("/listings")
async def get_listings(status: str = "active", category: Optional[str] = None):
    """Get all active listings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM app_listings WHERE status = ?"
    params = [status]
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    cursor.execute(query, params)
    listings = cursor.fetchall()
    
    columns = [desc[0] for desc in cursor.description]
    result = [dict(zip(columns, row)) for row in listings]
    
    conn.close()
    return {"listings": result, "count": len(result)}

@app.get("/listings/{listing_id}")
async def get_listing_details(listing_id: str):
    """Get detailed information about a specific listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get listing details
    cursor.execute("SELECT * FROM app_listings WHERE id = ?", (listing_id,))
    listing = cursor.fetchone()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    columns = [desc[0] for desc in cursor.description]
    listing_dict = dict(zip(columns, listing))
    
    # Get financial projections
    cursor.execute("SELECT * FROM financial_projections WHERE listing_id = ?", (listing_id,))
    projections = cursor.fetchall()
    proj_columns = [desc[0] for desc in cursor.description]
    projections_dict = [dict(zip(proj_columns, proj)) for proj in projections]
    
    # Get due diligence data
    cursor.execute("SELECT * FROM due_diligence WHERE listing_id = ?", (listing_id,))
    dd_data = cursor.fetchone()
    dd_dict = None
    if dd_data:
        dd_columns = [desc[0] for desc in cursor.description]
        dd_dict = dict(zip(dd_columns, dd_data))
    
    conn.close()
    
    return {
        "listing": listing_dict,
        "financial_projections": projections_dict,
        "due_diligence": dd_dict
    }

@app.post("/listings/{listing_id}/upload-pitch-deck")
async def upload_pitch_deck(listing_id: str, file: UploadFile = File(...)):
    """Upload pitch deck for a listing"""
    # Create uploads directory if it doesn't exist
    os.makedirs("static/uploads", exist_ok=True)
    
    file_path = f"static/uploads/{listing_id}_pitch_deck_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update database with file path
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE app_listings SET pitch_deck_url = ? WHERE id = ?",
        (file_path, listing_id)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "message": "Pitch deck uploaded successfully",
        "file_path": file_path
    }

@app.post("/listings/{listing_id}/financial-projections")
async def add_financial_projections(listing_id: str, projections: List[FinancialProjection]):
    """Add financial projections for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing projections
    cursor.execute("DELETE FROM financial_projections WHERE listing_id = ?", (listing_id,))
    
    # Add new projections
    for proj in projections:
        cursor.execute('''
            INSERT INTO financial_projections (id, listing_id, year, revenue, expenses, profit, users, growth_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            generate_id(), listing_id, proj.year, proj.revenue, proj.expenses,
            proj.profit, proj.users, proj.growth_rate
        ))
    
    conn.commit()
    conn.close()
    
    return {"message": "Financial projections added successfully"}

@app.post("/listings/{listing_id}/investor-updates")
async def create_investor_update(listing_id: str, update: InvestorUpdate):
    """Create an update for investors in a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    update_id = generate_id()
    
    cursor.execute('''
        INSERT INTO investor_updates (
            id, listing_id, title, content, milestone_achieved, 
            financial_update, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        update_id, listing_id, update.title, update.content,
        update.milestone_achieved, update.financial_update,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "update_id": update_id,
        "message": "Investor update created successfully"
    }

@app.get("/listings/{listing_id}/investor-updates")
async def get_investor_updates(listing_id: str):
    """Get all investor updates for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM investor_updates 
        WHERE listing_id = ? 
        ORDER BY created_at DESC
    ''', (listing_id,))
    
    updates = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    result = [dict(zip(columns, row)) for row in updates]
    
    conn.close()
    return {"updates": result}

@app.put("/listings/{listing_id}/status")
async def update_listing_status(listing_id: str, status: str):
    """Update listing status (draft, active, closed, funded)"""
    valid_statuses = ["draft", "active", "closed", "funded"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE app_listings SET status = ? WHERE id = ?",
        (status, listing_id)
    )
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    conn.commit()
    conn.close()
    
    return {"message": f"Listing status updated to {status}"}

if __name__ == "__main__":
    print("🚀 Starting ActiveLog Fundraising Platform on port 8412...")
    uvicorn.run(app, host="0.0.0.0", port=8412)