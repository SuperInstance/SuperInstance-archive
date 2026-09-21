"""
Crowdfunding Mechanics and Investment Management
Comprehensive investment platform with milestone-based releases and governance
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import sqlite3
import json
from datetime import datetime, timedelta
import uuid
from decimal import Decimal

router = APIRouter(prefix="/investments", tags=["Investments"])

DATABASE_PATH = "fundraising_platform.db"

def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

# Pydantic models
class Investment(BaseModel):
    listing_id: str
    amount: float
    investor_notes: Optional[str] = None

class InvestmentTerms(BaseModel):
    listing_id: str
    minimum_raise: float
    maximum_raise: float
    investment_period_days: int
    milestone_releases: List[Dict[str, Any]]
    voting_rights: Dict[str, Any]
    exit_strategies: List[str]
    refund_conditions: List[str]

class Milestone(BaseModel):
    title: str
    description: str
    target_date: str
    funding_percentage: float
    success_criteria: List[str]
    deliverables: List[str]

class VotingProposal(BaseModel):
    listing_id: str
    title: str
    description: str
    proposal_type: str  # milestone_approval, strategy_change, exit_vote
    voting_deadline: str
    required_majority: float = 0.5

class SecondaryMarketListing(BaseModel):
    investment_id: str
    asking_price: float
    shares_percentage: float
    reason_for_sale: str

class RefundRequest(BaseModel):
    investment_id: str
    reason: str
    supporting_documents: Optional[List[str]] = None

@router.post("/invest")
async def make_investment(investment: Investment, investor_id: str = "demo-investor"):
    """Make an investment in an app listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify listing exists and is active
    cursor.execute(
        "SELECT * FROM app_listings WHERE id = ? AND status = 'active'",
        (investment.listing_id,)
    )
    listing = cursor.fetchone()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Active listing not found")
    
    # Get listing details
    columns = [desc[0] for desc in cursor.description]
    listing_dict = dict(zip(columns, listing))
    
    # Validate investment amount
    min_investment = listing_dict['minimum_investment']
    max_investment = listing_dict.get('maximum_investment')
    current_amount = listing_dict['current_amount'] or 0
    target_amount = listing_dict['target_amount']
    
    if investment.amount < min_investment:
        raise HTTPException(
            status_code=400,
            detail=f"Investment amount must be at least ${min_investment}"
        )
    
    if max_investment and investment.amount > max_investment:
        raise HTTPException(
            status_code=400,
            detail=f"Investment amount cannot exceed ${max_investment}"
        )
    
    if current_amount + investment.amount > target_amount:
        raise HTTPException(
            status_code=400,
            detail="Investment would exceed target amount"
        )
    
    # Calculate equity percentage
    equity_percentage = (investment.amount / target_amount) * listing_dict['equity_percentage']
    
    # Create investment record
    investment_id = str(uuid.uuid4())
    
    cursor.execute('''
        INSERT INTO investments (
            id, listing_id, investor_id, amount, equity_percentage,
            status, created_at, milestone_releases
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        investment_id, investment.listing_id, investor_id, investment.amount,
        equity_percentage, 'pending', datetime.now().isoformat(),
        json.dumps([])  # Will be populated when milestones are set
    ))
    
    # Update listing current amount
    new_current_amount = current_amount + investment.amount
    cursor.execute(
        "UPDATE app_listings SET current_amount = ? WHERE id = ?",
        (new_current_amount, investment.listing_id)
    )
    
    # Check if funding goal reached
    if new_current_amount >= target_amount:
        cursor.execute(
            "UPDATE app_listings SET status = 'funded' WHERE id = ?",
            (investment.listing_id,)
        )
    
    conn.commit()
    conn.close()
    
    return {
        "investment_id": investment_id,
        "equity_percentage": equity_percentage,
        "status": "pending",
        "message": "Investment submitted successfully",
        "listing_funded": new_current_amount >= target_amount
    }

@router.get("/my-investments/{investor_id}")
async def get_investor_portfolio(investor_id: str):
    """Get all investments for an investor"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.*, al.app_name, al.category, al.status as listing_status
        FROM investments i
        JOIN app_listings al ON i.listing_id = al.id
        WHERE i.investor_id = ?
        ORDER BY i.created_at DESC
    ''', (investor_id,))
    
    investments = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    result = [dict(zip(columns, row)) for row in investments]
    
    # Calculate portfolio metrics
    total_invested = sum(inv['amount'] for inv in result)
    active_investments = len([inv for inv in result if inv['status'] in ['confirmed', 'active']])
    
    conn.close()
    
    return {
        "investments": result,
        "portfolio_summary": {
            "total_invested": total_invested,
            "active_investments": active_investments,
            "total_investments": len(result)
        }
    }

@router.get("/listing-investments/{listing_id}")
async def get_listing_investments(listing_id: str):
    """Get all investments for a specific listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.*, al.app_name, al.target_amount
        FROM investments i
        JOIN app_listings al ON i.listing_id = al.id
        WHERE i.listing_id = ?
        ORDER BY i.created_at DESC
    ''', (listing_id,))
    
    investments = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    result = [dict(zip(columns, row)) for row in investments]
    
    # Calculate funding metrics
    total_raised = sum(inv['amount'] for inv in result if inv['status'] == 'confirmed')
    investor_count = len(set(inv['investor_id'] for inv in result))
    
    conn.close()
    
    return {
        "investments": result,
        "funding_summary": {
            "total_raised": total_raised,
            "investor_count": investor_count,
            "investment_count": len(result)
        }
    }

@router.post("/terms")
async def set_investment_terms(terms: InvestmentTerms):
    """Set investment terms for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (terms.listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Store terms in app_listings table
    terms_json = json.dumps({
        "minimum_raise": terms.minimum_raise,
        "maximum_raise": terms.maximum_raise,
        "investment_period_days": terms.investment_period_days,
        "milestone_releases": terms.milestone_releases,
        "voting_rights": terms.voting_rights,
        "exit_strategies": terms.exit_strategies,
        "refund_conditions": terms.refund_conditions
    })
    
    cursor.execute(
        "UPDATE app_listings SET investment_terms = ? WHERE id = ?",
        (terms_json, terms.listing_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Investment terms set successfully"}

@router.get("/terms/{listing_id}")
async def get_investment_terms(listing_id: str):
    """Get investment terms for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT investment_terms FROM app_listings WHERE id = ?", (listing_id,))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        raise HTTPException(status_code=404, detail="Investment terms not found")
    
    conn.close()
    
    try:
        terms = json.loads(result[0])
        return terms
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid terms data")

@router.post("/milestones")
async def create_milestone(listing_id: str, milestone: Milestone):
    """Create a milestone for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    milestone_id = str(uuid.uuid4())
    
    # Store milestone
    milestone_data = {
        "id": milestone_id,
        "title": milestone.title,
        "description": milestone.description,
        "target_date": milestone.target_date,
        "funding_percentage": milestone.funding_percentage,
        "success_criteria": milestone.success_criteria,
        "deliverables": milestone.deliverables,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    # Update listing milestones
    cursor.execute("SELECT milestones FROM app_listings WHERE id = ?", (listing_id,))
    existing_milestones = cursor.fetchone()[0] or "[]"
    
    try:
        milestones_list = json.loads(existing_milestones)
    except:
        milestones_list = []
    
    milestones_list.append(milestone_data)
    
    cursor.execute(
        "UPDATE app_listings SET milestones = ? WHERE id = ?",
        (json.dumps(milestones_list), listing_id)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "milestone_id": milestone_id,
        "message": "Milestone created successfully"
    }

@router.get("/milestones/{listing_id}")
async def get_milestones(listing_id: str):
    """Get all milestones for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT milestones FROM app_listings WHERE id = ?", (listing_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    conn.close()
    
    try:
        milestones = json.loads(result[0] or "[]")
        return {"milestones": milestones}
    except json.JSONDecodeError:
        return {"milestones": []}

@router.put("/milestones/{milestone_id}/complete")
async def complete_milestone(listing_id: str, milestone_id: str):
    """Mark a milestone as completed and trigger funding release"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current milestones
    cursor.execute("SELECT milestones FROM app_listings WHERE id = ?", (listing_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    try:
        milestones = json.loads(result[0] or "[]")
    except:
        milestones = []
    
    # Find and update milestone
    milestone_found = False
    for milestone in milestones:
        if milestone['id'] == milestone_id:
            milestone['status'] = 'completed'
            milestone['completed_at'] = datetime.now().isoformat()
            milestone_found = True
            break
    
    if not milestone_found:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Update milestones
    cursor.execute(
        "UPDATE app_listings SET milestones = ? WHERE id = ?",
        (json.dumps(milestones), listing_id)
    )
    
    # Calculate funding release
    completed_milestone = next(m for m in milestones if m['id'] == milestone_id)
    funding_percentage = completed_milestone['funding_percentage']
    
    # Get total raised for this listing
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM investments WHERE listing_id = ? AND status = 'confirmed'",
        (listing_id,)
    )
    total_raised = cursor.fetchone()[0]
    
    release_amount = total_raised * (funding_percentage / 100)
    
    conn.commit()
    conn.close()
    
    return {
        "message": "Milestone completed successfully",
        "funding_released": release_amount,
        "release_percentage": funding_percentage
    }

@router.post("/voting/proposal")
async def create_voting_proposal(proposal: VotingProposal):
    """Create a voting proposal for investors"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    proposal_id = str(uuid.uuid4())
    
    # Store proposal (you might want a separate table for this)
    proposal_data = {
        "id": proposal_id,
        "listing_id": proposal.listing_id,
        "title": proposal.title,
        "description": proposal.description,
        "proposal_type": proposal.proposal_type,
        "voting_deadline": proposal.voting_deadline,
        "required_majority": proposal.required_majority,
        "status": "active",
        "votes": [],
        "created_at": datetime.now().isoformat()
    }
    
    # For now, store in a simple way (you might want a dedicated table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voting_proposals (
            id TEXT PRIMARY KEY,
            listing_id TEXT,
            proposal_data TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute(
        "INSERT INTO voting_proposals (id, listing_id, proposal_data, created_at) VALUES (?, ?, ?, ?)",
        (proposal_id, proposal.listing_id, json.dumps(proposal_data), datetime.now().isoformat())
    )
    
    conn.commit()
    conn.close()
    
    return {
        "proposal_id": proposal_id,
        "message": "Voting proposal created successfully"
    }

@router.post("/voting/{proposal_id}/vote")
async def cast_vote(proposal_id: str, vote: bool, investor_id: str = "demo-investor"):
    """Cast a vote on a proposal"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get proposal
    cursor.execute("SELECT proposal_data FROM voting_proposals WHERE id = ?", (proposal_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    try:
        proposal_data = json.loads(result[0])
    except:
        raise HTTPException(status_code=500, detail="Invalid proposal data")
    
    # Check if voting is still active
    voting_deadline = datetime.fromisoformat(proposal_data['voting_deadline'])
    if datetime.now() > voting_deadline:
        raise HTTPException(status_code=400, detail="Voting period has ended")
    
    # Verify investor has stake in the listing
    cursor.execute(
        "SELECT equity_percentage FROM investments WHERE listing_id = ? AND investor_id = ? AND status = 'confirmed'",
        (proposal_data['listing_id'], investor_id)
    )
    investment = cursor.fetchone()
    
    if not investment:
        raise HTTPException(status_code=403, detail="Not authorized to vote on this proposal")
    
    voting_power = investment[0]  # Equity percentage determines voting power
    
    # Remove existing vote from same investor
    proposal_data['votes'] = [v for v in proposal_data['votes'] if v['investor_id'] != investor_id]
    
    # Add new vote
    proposal_data['votes'].append({
        "investor_id": investor_id,
        "vote": vote,
        "voting_power": voting_power,
        "timestamp": datetime.now().isoformat()
    })
    
    # Update proposal
    cursor.execute(
        "UPDATE voting_proposals SET proposal_data = ? WHERE id = ?",
        (json.dumps(proposal_data), proposal_id)
    )
    
    # Check if proposal can be concluded
    total_voting_power = sum(v['voting_power'] for v in proposal_data['votes'])
    yes_power = sum(v['voting_power'] for v in proposal_data['votes'] if v['vote'])
    
    if total_voting_power > 50:  # Quorum reached
        if yes_power / total_voting_power >= proposal_data['required_majority']:
            proposal_data['status'] = 'approved'
        else:
            proposal_data['status'] = 'rejected'
        
        cursor.execute(
            "UPDATE voting_proposals SET proposal_data = ? WHERE id = ?",
            (json.dumps(proposal_data), proposal_id)
        )
    
    conn.commit()
    conn.close()
    
    return {
        "message": "Vote cast successfully",
        "proposal_status": proposal_data['status'],
        "current_support": (yes_power / total_voting_power * 100) if total_voting_power > 0 else 0
    }

@router.post("/secondary-market/list")
async def list_on_secondary_market(listing: SecondaryMarketListing, seller_id: str = "demo-investor"):
    """List investment shares on secondary market"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify investor owns the investment
    cursor.execute(
        "SELECT * FROM investments WHERE id = ? AND investor_id = ?",
        (listing.investment_id, seller_id)
    )
    investment = cursor.fetchone()
    
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")
    
    # Create secondary market listing
    secondary_listing_id = str(uuid.uuid4())
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS secondary_market_listings (
            id TEXT PRIMARY KEY,
            investment_id TEXT,
            seller_id TEXT,
            asking_price REAL,
            shares_percentage REAL,
            reason_for_sale TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        INSERT INTO secondary_market_listings (
            id, investment_id, seller_id, asking_price, shares_percentage,
            reason_for_sale, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        secondary_listing_id, listing.investment_id, seller_id,
        listing.asking_price, listing.shares_percentage, listing.reason_for_sale,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "secondary_listing_id": secondary_listing_id,
        "message": "Investment listed on secondary market successfully"
    }

@router.get("/secondary-market")
async def get_secondary_market_listings():
    """Get all active secondary market listings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT sml.*, i.listing_id, al.app_name, al.category
            FROM secondary_market_listings sml
            JOIN investments i ON sml.investment_id = i.id
            JOIN app_listings al ON i.listing_id = al.id
            WHERE sml.status = 'active'
            ORDER BY sml.created_at DESC
        ''')
        
        listings = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in listings]
        
        conn.close()
        return {"secondary_listings": result}
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        conn.close()
        return {"secondary_listings": []}

@router.post("/refund-request")
async def request_refund(refund_request: RefundRequest, investor_id: str = "demo-investor"):
    """Request a refund for an investment"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify investment exists and belongs to investor
    cursor.execute(
        "SELECT * FROM investments WHERE id = ? AND investor_id = ?",
        (refund_request.investment_id, investor_id)
    )
    investment = cursor.fetchone()
    
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")
    
    # Check refund eligibility (based on investment terms)
    # This is a simplified version - you'd check the actual terms
    
    refund_request_id = str(uuid.uuid4())
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS refund_requests (
            id TEXT PRIMARY KEY,
            investment_id TEXT,
            investor_id TEXT,
            reason TEXT,
            supporting_documents TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        INSERT INTO refund_requests (
            id, investment_id, investor_id, reason, supporting_documents, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        refund_request_id, refund_request.investment_id, investor_id,
        refund_request.reason, json.dumps(refund_request.supporting_documents or []),
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "refund_request_id": refund_request_id,
        "message": "Refund request submitted successfully",
        "status": "pending"
    }

@router.get("/analytics/{listing_id}")
async def get_investment_analytics(listing_id: str):
    """Get investment analytics for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get investment summary
    cursor.execute('''
        SELECT 
            COUNT(*) as total_investors,
            SUM(amount) as total_raised,
            AVG(amount) as average_investment,
            MIN(amount) as minimum_investment,
            MAX(amount) as maximum_investment
        FROM investments 
        WHERE listing_id = ? AND status = 'confirmed'
    ''', (listing_id,))
    
    summary = cursor.fetchone()
    
    # Get investment timeline
    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as investments, SUM(amount) as daily_amount
        FROM investments 
        WHERE listing_id = ? AND status = 'confirmed'
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (listing_id,))
    
    timeline = cursor.fetchall()
    
    # Get investor distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN amount < 1000 THEN 'Small ($0-$999)'
                WHEN amount < 5000 THEN 'Medium ($1K-$4.9K)'
                WHEN amount < 10000 THEN 'Large ($5K-$9.9K)'
                ELSE 'Whale ($10K+)'
            END as investor_type,
            COUNT(*) as count,
            SUM(amount) as total_amount
        FROM investments 
        WHERE listing_id = ? AND status = 'confirmed'
        GROUP BY investor_type
    ''', (listing_id,))
    
    distribution = cursor.fetchall()
    
    conn.close()
    
    return {
        "summary": {
            "total_investors": summary[0] or 0,
            "total_raised": summary[1] or 0,
            "average_investment": summary[2] or 0,
            "minimum_investment": summary[3] or 0,
            "maximum_investment": summary[4] or 0
        },
        "timeline": [{"date": t[0], "investments": t[1], "amount": t[2]} for t in timeline],
        "distribution": [{"type": d[0], "count": d[1], "amount": d[2]} for d in distribution]
    }