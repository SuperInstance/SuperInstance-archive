from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import sqlite3
import uuid
import json
import random

router = APIRouter()

# Pydantic models
class CreateCompetition(BaseModel):
    name: str
    description: Optional[str] = None
    competition_type: str  # daily, weekly, monthly, tournament
    age_group: str = "all"  # kids, teens, adults, all
    start_date: datetime
    end_date: datetime
    entry_fee_cc: float = 0.0
    prize_pool_cc: float = 0.0
    max_participants: Optional[int] = None
    starting_capital: float = 100000.0
    rules: Optional[str] = None

class Competition(BaseModel):
    competition_id: str
    name: str
    description: Optional[str]
    competition_type: str
    age_group: str
    start_date: datetime
    end_date: datetime
    entry_fee_cc: float
    prize_pool_cc: float
    max_participants: Optional[int]
    current_participants: int
    starting_capital: float
    status: str  # upcoming, active, completed, cancelled
    rules: Optional[str]
    created_at: datetime

class CompetitionEntry(BaseModel):
    entry_id: str
    competition_id: str
    user_id: str
    username: str
    portfolio_id: str
    entry_time: datetime
    starting_value: float
    current_value: float
    current_rank: int
    performance_percent: float

class Leaderboard(BaseModel):
    competition_id: str
    competition_name: str
    entries: List[CompetitionEntry]
    total_participants: int
    prize_distribution: List[Dict[str, Any]]

class TournamentBracket(BaseModel):
    tournament_id: str
    rounds: List[Dict[str, Any]]
    current_round: int
    bracket_type: str  # single_elimination, double_elimination, round_robin

class Achievement(BaseModel):
    achievement_id: str
    name: str
    description: str
    category: str
    icon: str
    points: int
    requirements: Dict[str, Any]

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('paper_trading.db')

def calculate_competition_rankings(competition_id: str):
    """Calculate and update competition rankings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all entries for this competition with current portfolio values
    cursor.execute('''
        SELECT ce.entry_id, ce.user_id, ce.starting_value, p.total_value
        FROM competition_entries ce
        JOIN portfolios p ON ce.portfolio_id = p.portfolio_id
        WHERE ce.competition_id = ?
        ORDER BY p.total_value DESC
    ''', (competition_id,))
    
    entries = cursor.fetchall()
    
    # Update rankings
    for rank, (entry_id, user_id, starting_value, current_value) in enumerate(entries, 1):
        cursor.execute('''
            UPDATE competition_entries 
            SET current_value = ?, current_rank = ?
            WHERE entry_id = ?
        ''', (current_value, rank, entry_id))
    
    conn.commit()
    conn.close()

def award_prizes(competition_id: str):
    """Award prizes to competition winners"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get competition details
    cursor.execute('SELECT prize_pool_cc, current_participants FROM competitions WHERE competition_id = ?', 
                  (competition_id,))
    result = cursor.fetchone()
    
    if not result:
        return
    
    prize_pool, participants = result
    
    if prize_pool <= 0:
        return
    
    # Get top performers
    cursor.execute('''
        SELECT entry_id, user_id, current_rank
        FROM competition_entries 
        WHERE competition_id = ?
        ORDER BY current_rank
        LIMIT 10
    ''', (competition_id,))
    
    top_entries = cursor.fetchall()
    
    # Prize distribution: 50% to 1st, 30% to 2nd, 20% to 3rd
    prize_distribution = [0.5, 0.3, 0.2]
    
    for i, (entry_id, user_id, rank) in enumerate(top_entries[:3]):
        if i < len(prize_distribution):
            prize_amount = prize_pool * prize_distribution[i]
            
            # Award prize
            cursor.execute('''
                UPDATE competition_entries 
                SET prize_won_cc = ?
                WHERE entry_id = ?
            ''', (prize_amount, entry_id))
            
            # Add to user's CC balance
            cursor.execute('''
                UPDATE users 
                SET cc_balance = cc_balance + ?
                WHERE user_id = ?
            ''', (prize_amount, user_id))
    
    conn.commit()
    conn.close()

@router.post("/create", response_model=Competition)
async def create_competition(competition_data: CreateCompetition, creator_id: str):
    """Create a new trading competition"""
    
    competition_id = str(uuid.uuid4())
    
    # Validate dates
    if competition_data.start_date >= competition_data.end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    if competition_data.start_date <= datetime.now():
        raise HTTPException(status_code=400, detail="Start date must be in the future")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO competitions 
            (competition_id, name, description, competition_type, age_group, start_date, end_date,
             entry_fee_cc, prize_pool_cc, max_participants, starting_capital, status, rules)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (competition_id, competition_data.name, competition_data.description,
              competition_data.competition_type, competition_data.age_group,
              competition_data.start_date.isoformat(), competition_data.end_date.isoformat(),
              competition_data.entry_fee_cc, competition_data.prize_pool_cc,
              competition_data.max_participants, competition_data.starting_capital,
              "upcoming", competition_data.rules))
        
        conn.commit()
        
        return Competition(
            competition_id=competition_id,
            name=competition_data.name,
            description=competition_data.description,
            competition_type=competition_data.competition_type,
            age_group=competition_data.age_group,
            start_date=competition_data.start_date,
            end_date=competition_data.end_date,
            entry_fee_cc=competition_data.entry_fee_cc,
            prize_pool_cc=competition_data.prize_pool_cc,
            max_participants=competition_data.max_participants,
            current_participants=0,
            starting_capital=competition_data.starting_capital,
            status="upcoming",
            rules=competition_data.rules,
            created_at=datetime.now()
        )
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create competition: {str(e)}")
    
    finally:
        conn.close()

@router.get("/list")
async def list_competitions(
    status: Optional[str] = None,
    age_group: Optional[str] = None,
    competition_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List available competitions with filters"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with filters
    where_conditions = []
    params = []
    
    if status:
        where_conditions.append("status = ?")
        params.append(status)
    
    if age_group and age_group != "all":
        where_conditions.append("(age_group = ? OR age_group = 'all')")
        params.append(age_group)
    
    if competition_type:
        where_conditions.append("competition_type = ?")
        params.append(competition_type)
    
    where_clause = " AND ".join(where_conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause
    
    query = f'''
        SELECT competition_id, name, description, competition_type, age_group,
               start_date, end_date, entry_fee_cc, prize_pool_cc, max_participants,
               current_participants, starting_capital, status, rules, created_at
        FROM competitions 
        {where_clause}
        ORDER BY start_date DESC
        LIMIT ? OFFSET ?
    '''
    
    params.extend([limit, offset])
    cursor.execute(query, params)
    competitions = cursor.fetchall()
    
    # Get total count
    count_query = f'SELECT COUNT(*) FROM competitions {where_clause}'
    cursor.execute(count_query, params[:-2])  # Exclude limit and offset
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    competition_list = []
    for comp in competitions:
        competition_list.append(Competition(
            competition_id=comp[0],
            name=comp[1],
            description=comp[2],
            competition_type=comp[3],
            age_group=comp[4],
            start_date=datetime.fromisoformat(comp[5]),
            end_date=datetime.fromisoformat(comp[6]),
            entry_fee_cc=comp[7],
            prize_pool_cc=comp[8],
            max_participants=comp[9],
            current_participants=comp[10],
            starting_capital=comp[11],
            status=comp[12],
            rules=comp[13],
            created_at=datetime.fromisoformat(comp[14])
        ))
    
    return {
        "competitions": competition_list,
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }

@router.post("/join/{competition_id}")
async def join_competition(competition_id: str, user_id: str, username: str):
    """Join a trading competition"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get competition details
    cursor.execute('''
        SELECT name, competition_type, start_date, end_date, entry_fee_cc, 
               max_participants, current_participants, starting_capital, status
        FROM competitions WHERE competition_id = ?
    ''', (competition_id,))
    
    competition = cursor.fetchone()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    name, comp_type, start_date, end_date, entry_fee, max_participants, current_participants, starting_capital, status = competition
    
    # Check if competition is open for registration
    if status != "upcoming":
        raise HTTPException(status_code=400, detail="Competition is not open for registration")
    
    # Check if competition is full
    if max_participants and current_participants >= max_participants:
        raise HTTPException(status_code=400, detail="Competition is full")
    
    # Check if user already joined
    cursor.execute('SELECT entry_id FROM competition_entries WHERE competition_id = ? AND user_id = ?',
                  (competition_id, user_id))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Already joined this competition")
    
    # Check user's CC balance for entry fee
    cursor.execute('SELECT cc_balance FROM users WHERE user_id = ?', (user_id,))
    user_result = cursor.fetchone()
    if not user_result:
        raise HTTPException(status_code=404, detail="User not found")
    
    cc_balance = user_result[0]
    if cc_balance < entry_fee:
        raise HTTPException(status_code=400, detail="Insufficient CC balance for entry fee")
    
    try:
        # Create a new portfolio for the competition
        portfolio_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO portfolios 
            (portfolio_id, user_id, name, starting_capital, current_cash, total_value, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (portfolio_id, user_id, f"{name} - {username}", starting_capital,
              starting_capital, starting_capital, True))
        
        # Create competition entry
        entry_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO competition_entries 
            (entry_id, competition_id, user_id, portfolio_id, starting_value, current_value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (entry_id, competition_id, user_id, portfolio_id, starting_capital, starting_capital))
        
        # Deduct entry fee from user's CC balance
        cursor.execute('UPDATE users SET cc_balance = cc_balance - ? WHERE user_id = ?',
                      (entry_fee, user_id))
        
        # Update competition participant count
        cursor.execute('UPDATE competitions SET current_participants = current_participants + 1 WHERE competition_id = ?',
                      (competition_id,))
        
        conn.commit()
        
        return {
            "entry_id": entry_id,
            "portfolio_id": portfolio_id,
            "message": "Successfully joined competition"
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to join competition: {str(e)}")
    
    finally:
        conn.close()

@router.get("/leaderboard/{competition_id}", response_model=Leaderboard)
async def get_competition_leaderboard(competition_id: str, limit: int = 50):
    """Get competition leaderboard"""
    
    # Update rankings first
    calculate_competition_rankings(competition_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get competition info
    cursor.execute('SELECT name, prize_pool_cc FROM competitions WHERE competition_id = ?', 
                  (competition_id,))
    comp_result = cursor.fetchone()
    
    if not comp_result:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    competition_name, prize_pool = comp_result
    
    # Get leaderboard entries
    cursor.execute('''
        SELECT ce.entry_id, ce.competition_id, ce.user_id, u.username, ce.portfolio_id,
               ce.entry_time, ce.starting_value, ce.current_value, ce.current_rank
        FROM competition_entries ce
        JOIN users u ON ce.user_id = u.user_id
        WHERE ce.competition_id = ?
        ORDER BY ce.current_rank
        LIMIT ?
    ''', (competition_id, limit))
    
    entries_data = cursor.fetchall()
    
    # Get total participants
    cursor.execute('SELECT COUNT(*) FROM competition_entries WHERE competition_id = ?', 
                  (competition_id,))
    total_participants = cursor.fetchone()[0]
    
    conn.close()
    
    # Build entries list
    entries = []
    for entry_data in entries_data:
        entry_id, comp_id, user_id, username, portfolio_id, entry_time, starting_value, current_value, current_rank = entry_data
        
        performance_percent = ((current_value - starting_value) / starting_value) * 100 if starting_value > 0 else 0
        
        entries.append(CompetitionEntry(
            entry_id=entry_id,
            competition_id=comp_id,
            user_id=user_id,
            username=username,
            portfolio_id=portfolio_id,
            entry_time=datetime.fromisoformat(entry_time),
            starting_value=starting_value,
            current_value=current_value,
            current_rank=current_rank,
            performance_percent=performance_percent
        ))
    
    # Prize distribution
    prize_distribution = []
    if prize_pool > 0:
        prize_distribution = [
            {"rank": 1, "percentage": 50, "amount": prize_pool * 0.5},
            {"rank": 2, "percentage": 30, "amount": prize_pool * 0.3},
            {"rank": 3, "percentage": 20, "amount": prize_pool * 0.2}
        ]
    
    return Leaderboard(
        competition_id=competition_id,
        competition_name=competition_name,
        entries=entries,
        total_participants=total_participants,
        prize_distribution=prize_distribution
    )

@router.get("/my-competitions/{user_id}")
async def get_user_competitions(user_id: str):
    """Get competitions user has joined"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.competition_id, c.name, c.competition_type, c.status,
               ce.entry_id, ce.current_rank, ce.current_value, ce.starting_value,
               ce.prize_won_cc, c.end_date
        FROM competition_entries ce
        JOIN competitions c ON ce.competition_id = c.competition_id
        WHERE ce.user_id = ?
        ORDER BY c.end_date DESC
    ''', (user_id,))
    
    competitions = cursor.fetchall()
    conn.close()
    
    user_competitions = []
    for comp in competitions:
        comp_id, name, comp_type, status, entry_id, rank, current_value, starting_value, prize_won, end_date = comp
        
        performance = ((current_value - starting_value) / starting_value) * 100 if starting_value > 0 else 0
        
        user_competitions.append({
            "competition_id": comp_id,
            "name": name,
            "competition_type": comp_type,
            "status": status,
            "entry_id": entry_id,
            "current_rank": rank,
            "performance_percent": performance,
            "prize_won_cc": prize_won,
            "end_date": end_date
        })
    
    return {"competitions": user_competitions}

@router.post("/create-league")
async def create_private_league(
    name: str,
    description: str,
    creator_id: str,
    max_participants: int = 20,
    entry_fee_cc: float = 0.0,
    duration_days: int = 30
):
    """Create a private league for schools or groups"""
    
    league_id = str(uuid.uuid4())
    start_date = datetime.now() + timedelta(days=1)  # Start tomorrow
    end_date = start_date + timedelta(days=duration_days)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO competitions 
            (competition_id, name, description, competition_type, age_group, start_date, end_date,
             entry_fee_cc, prize_pool_cc, max_participants, starting_capital, status, rules)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (league_id, name, description, "private_league", "all",
              start_date.isoformat(), end_date.isoformat(),
              entry_fee_cc, entry_fee_cc * max_participants * 0.9,  # 90% goes to prizes
              max_participants, 100000.0, "upcoming",
              "Private league - invitation only"))
        
        conn.commit()
        
        return {
            "league_id": league_id,
            "invite_code": league_id[:8].upper(),  # Short invite code
            "message": "Private league created successfully"
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create league: {str(e)}")
    
    finally:
        conn.close()

@router.post("/join-league/{invite_code}")
async def join_private_league(invite_code: str, user_id: str, username: str):
    """Join a private league using invite code"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find league by invite code (first 8 characters of competition_id)
    cursor.execute('''
        SELECT competition_id FROM competitions 
        WHERE competition_type = 'private_league' 
        AND competition_id LIKE ? 
        AND status = 'upcoming'
    ''', (invite_code.lower() + '%',))
    
    result = cursor.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Invalid invite code or league not found")
    
    competition_id = result[0]
    conn.close()
    
    # Use the regular join competition function
    return await join_competition(competition_id, user_id, username)

@router.get("/tournaments")
async def list_tournaments():
    """List available tournaments with bracket information"""
    
    tournaments = [
        {
            "tournament_id": "weekly_knockout",
            "name": "Weekly Knockout Tournament",
            "description": "Single elimination tournament - one bad week and you're out!",
            "bracket_type": "single_elimination",
            "entry_fee_cc": 10.0,
            "prize_pool_cc": 1000.0,
            "max_participants": 64,
            "current_participants": 32,
            "status": "upcoming",
            "start_date": datetime.now() + timedelta(days=3),
            "rounds": [
                {"round": 1, "participants": 64, "duration_days": 7},
                {"round": 2, "participants": 32, "duration_days": 7},
                {"round": 3, "participants": 16, "duration_days": 7},
                {"round": 4, "participants": 8, "duration_days": 7},
                {"round": 5, "participants": 4, "duration_days": 7},
                {"round": 6, "participants": 2, "duration_days": 7}
            ]
        },
        {
            "tournament_id": "championship_series",
            "name": "Monthly Championship Series",
            "description": "Round-robin followed by playoffs for the best traders",
            "bracket_type": "round_robin",
            "entry_fee_cc": 25.0,
            "prize_pool_cc": 5000.0,
            "max_participants": 32,
            "current_participants": 28,
            "status": "active",
            "start_date": datetime.now() - timedelta(days=5),
            "current_round": 2
        }
    ]
    
    return {"tournaments": tournaments}

@router.get("/achievements")
async def list_achievements():
    """List all available achievements"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT achievement_id, name, description, category, icon, points, requirements
        FROM achievements WHERE is_active = 1
        ORDER BY category, points
    ''')
    
    achievements_data = cursor.fetchall()
    conn.close()
    
    achievements = []
    for achievement_data in achievements_data:
        achievement_id, name, description, category, icon, points, requirements = achievement_data
        
        # Parse requirements JSON
        try:
            requirements_dict = json.loads(requirements) if requirements else {}
        except:
            requirements_dict = {}
        
        achievements.append(Achievement(
            achievement_id=achievement_id,
            name=name,
            description=description,
            category=category,
            icon=icon,
            points=points,
            requirements=requirements_dict
        ))
    
    return {"achievements": achievements}

@router.get("/user-achievements/{user_id}")
async def get_user_achievements(user_id: str):
    """Get achievements earned by a user"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT a.achievement_id, a.name, a.description, a.category, a.icon, 
               a.points, ua.earned_at
        FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.achievement_id
        WHERE ua.user_id = ?
        ORDER BY ua.earned_at DESC
    ''', (user_id,))
    
    earned_achievements = cursor.fetchall()
    
    # Get total points
    cursor.execute('''
        SELECT SUM(a.points) as total_points
        FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.achievement_id
        WHERE ua.user_id = ?
    ''', (user_id,))
    
    total_points_result = cursor.fetchone()
    total_points = total_points_result[0] if total_points_result[0] else 0
    
    conn.close()
    
    achievements = []
    for achievement_data in earned_achievements:
        achievement_id, name, description, category, icon, points, earned_at = achievement_data
        
        achievements.append({
            "achievement_id": achievement_id,
            "name": name,
            "description": description,
            "category": category,
            "icon": icon,
            "points": points,
            "earned_at": earned_at
        })
    
    return {
        "user_id": user_id,
        "total_points": total_points,
        "achievements_count": len(achievements),
        "achievements": achievements
    }

@router.post("/end-competition/{competition_id}")
async def end_competition(competition_id: str, background_tasks: BackgroundTasks):
    """End a competition and award prizes"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if competition exists and can be ended
    cursor.execute('SELECT status, end_date FROM competitions WHERE competition_id = ?', 
                  (competition_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    status, end_date = result
    
    if status == "completed":
        raise HTTPException(status_code=400, detail="Competition already completed")
    
    # Update final rankings
    calculate_competition_rankings(competition_id)
    
    # Update competition status
    cursor.execute('UPDATE competitions SET status = ? WHERE competition_id = ?', 
                  ("completed", competition_id))
    
    conn.commit()
    conn.close()
    
    # Award prizes in background
    background_tasks.add_task(award_prizes, competition_id)
    
    return {"message": "Competition ended successfully, prizes will be awarded shortly"}

@router.get("/competition-stats")
async def get_competition_statistics():
    """Get overall competition platform statistics"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute('SELECT COUNT(*) FROM competitions')
    total_competitions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM competitions WHERE status = "active"')
    active_competitions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM competition_entries')
    total_entries = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(prize_pool_cc) FROM competitions WHERE status = "completed"')
    total_prizes_awarded = cursor.fetchone()[0] or 0
    
    # Get most popular competition types
    cursor.execute('''
        SELECT competition_type, COUNT(*) as count
        FROM competitions
        GROUP BY competition_type
        ORDER BY count DESC
        LIMIT 5
    ''')
    popular_types = cursor.fetchall()
    
    # Get top competitors
    cursor.execute('''
        SELECT u.username, COUNT(ce.entry_id) as competitions_joined,
               AVG(ce.current_rank) as avg_rank,
               SUM(ce.prize_won_cc) as total_prizes
        FROM competition_entries ce
        JOIN users u ON ce.user_id = u.user_id
        GROUP BY ce.user_id, u.username
        HAVING competitions_joined >= 3
        ORDER BY total_prizes DESC, avg_rank ASC
        LIMIT 10
    ''')
    top_competitors = cursor.fetchall()
    
    conn.close()
    
    return {
        "platform_stats": {
            "total_competitions": total_competitions,
            "active_competitions": active_competitions,
            "total_entries": total_entries,
            "total_prizes_awarded_cc": total_prizes_awarded
        },
        "popular_competition_types": [
            {"type": comp_type, "count": count} 
            for comp_type, count in popular_types
        ],
        "top_competitors": [
            {
                "username": username,
                "competitions_joined": joined,
                "average_rank": avg_rank,
                "total_prizes_cc": prizes
            }
            for username, joined, avg_rank, prizes in top_competitors
        ]
    }