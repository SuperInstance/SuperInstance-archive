from fastapi import APIRouter, HTTPException
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
class EducationalContent(BaseModel):
    content_id: str
    title: str
    content_type: str  # article, video, quiz, simulation
    category: str      # stocks, crypto, forex, options, basics
    difficulty: str    # beginner, intermediate, advanced
    content: Optional[str]
    video_url: Optional[str]
    quiz_questions: Optional[List[Dict[str, Any]]]
    estimated_time: int  # minutes
    points_reward: int
    prerequisites: List[str]
    created_at: datetime
    is_active: bool

class UserProgress(BaseModel):
    user_id: str
    content_id: str
    status: str  # not_started, in_progress, completed
    completion_date: Optional[datetime]
    score: Optional[int]
    time_spent: int  # minutes

class LearningPath(BaseModel):
    path_id: str
    name: str
    description: str
    difficulty: str
    estimated_time: int
    content_modules: List[EducationalContent]
    completion_percentage: float
    
class Quiz(BaseModel):
    quiz_id: str
    title: str
    questions: List[Dict[str, Any]]
    time_limit: int  # minutes
    passing_score: int  # percentage
    points_reward: int

class Simulation(BaseModel):
    simulation_id: str
    name: str
    description: str
    scenario_type: str  # market_crash, bull_market, sector_rotation, etc.
    starting_capital: float
    market_conditions: Dict[str, Any]
    learning_objectives: List[str]

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('paper_trading.db')

def check_achievement_progress(user_id: str, action: str, value: Any = None):
    """Check and award achievements based on user actions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if action == "complete_education":
        # Check education seeker achievement
        cursor.execute('''
            SELECT COUNT(*) FROM user_progress 
            WHERE user_id = ? AND status = 'completed'
        ''', (user_id,))
        completed_count = cursor.fetchone()[0]
        
        if completed_count >= 10:
            # Award education seeker achievement
            cursor.execute('''
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
                VALUES (?, 'education_seeker')
            ''', (user_id,))
    
    conn.commit()
    conn.close()

@router.get("/content")
async def list_educational_content(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List available educational content with filters"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with filters
    where_conditions = ["is_active = 1"]
    params = []
    
    if category:
        where_conditions.append("category = ?")
        params.append(category)
    
    if difficulty:
        where_conditions.append("difficulty = ?")
        params.append(difficulty)
    
    if content_type:
        where_conditions.append("content_type = ?")
        params.append(content_type)
    
    where_clause = " AND ".join(where_conditions)
    
    query = f'''
        SELECT content_id, title, content_type, category, difficulty, content,
               video_url, quiz_questions, estimated_time, points_reward, 
               prerequisites, created_at, is_active
        FROM educational_content
        WHERE {where_clause}
        ORDER BY difficulty, estimated_time
        LIMIT ? OFFSET ?
    '''
    
    params.extend([limit, offset])
    cursor.execute(query, params)
    content_list = cursor.fetchall()
    
    # Get total count
    count_query = f'SELECT COUNT(*) FROM educational_content WHERE {where_clause}'
    cursor.execute(count_query, params[:-2])
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    educational_content = []
    for content_data in content_list:
        content_id, title, content_type, category, difficulty, content, video_url, quiz_questions, estimated_time, points_reward, prerequisites, created_at, is_active = content_data
        
        # Parse JSON fields
        try:
            quiz_data = json.loads(quiz_questions) if quiz_questions else None
            prereq_list = json.loads(prerequisites) if prerequisites else []
        except:
            quiz_data = None
            prereq_list = []
        
        educational_content.append(EducationalContent(
            content_id=content_id,
            title=title,
            content_type=content_type,
            category=category,
            difficulty=difficulty,
            content=content,
            video_url=video_url,
            quiz_questions=quiz_data,
            estimated_time=estimated_time,
            points_reward=points_reward,
            prerequisites=prereq_list,
            created_at=datetime.fromisoformat(created_at),
            is_active=bool(is_active)
        ))
    
    return {
        "content": educational_content,
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }

@router.get("/content/{content_id}", response_model=EducationalContent)
async def get_educational_content(content_id: str):
    """Get specific educational content by ID"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT content_id, title, content_type, category, difficulty, content,
               video_url, quiz_questions, estimated_time, points_reward, 
               prerequisites, created_at, is_active
        FROM educational_content
        WHERE content_id = ? AND is_active = 1
    ''', (content_id,))
    
    content_data = cursor.fetchone()
    conn.close()
    
    if not content_data:
        raise HTTPException(status_code=404, detail="Educational content not found")
    
    content_id, title, content_type, category, difficulty, content, video_url, quiz_questions, estimated_time, points_reward, prerequisites, created_at, is_active = content_data
    
    # Parse JSON fields
    try:
        quiz_data = json.loads(quiz_questions) if quiz_questions else None
        prereq_list = json.loads(prerequisites) if prerequisites else []
    except:
        quiz_data = None
        prereq_list = []
    
    return EducationalContent(
        content_id=content_id,
        title=title,
        content_type=content_type,
        category=category,
        difficulty=difficulty,
        content=content,
        video_url=video_url,
        quiz_questions=quiz_data,
        estimated_time=estimated_time,
        points_reward=points_reward,
        prerequisites=prereq_list,
        created_at=datetime.fromisoformat(created_at),
        is_active=bool(is_active)
    )

@router.post("/progress/{content_id}")
async def update_progress(
    content_id: str,
    user_id: str,
    status: str,
    time_spent: int = 0,
    score: Optional[int] = None
):
    """Update user progress on educational content"""
    
    if status not in ["not_started", "in_progress", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if content exists
    cursor.execute('SELECT points_reward FROM educational_content WHERE content_id = ?', 
                  (content_id,))
    content_result = cursor.fetchone()
    
    if not content_result:
        raise HTTPException(status_code=404, detail="Educational content not found")
    
    points_reward = content_result[0]
    
    # Update or insert progress
    completion_date = datetime.now() if status == "completed" else None
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_progress 
        (user_id, content_id, status, completion_date, score, time_spent)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, content_id, status, 
          completion_date.isoformat() if completion_date else None, 
          score, time_spent))
    
    # Award points if completed
    if status == "completed":
        cursor.execute('''
            UPDATE users 
            SET cc_balance = cc_balance + ?
            WHERE user_id = ?
        ''', (points_reward, user_id))
        
        # Check for achievements
        check_achievement_progress(user_id, "complete_education")
    
    conn.commit()
    conn.close()
    
    return {
        "message": "Progress updated successfully",
        "points_awarded": points_reward if status == "completed" else 0
    }

@router.get("/progress/{user_id}")
async def get_user_progress(user_id: str):
    """Get user's learning progress across all content"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT up.content_id, up.status, up.completion_date, up.score, up.time_spent,
               ec.title, ec.category, ec.difficulty, ec.points_reward
        FROM user_progress up
        JOIN educational_content ec ON up.content_id = ec.content_id
        WHERE up.user_id = ?
        ORDER BY up.completion_date DESC, ec.created_at DESC
    ''', (user_id,))
    
    progress_data = cursor.fetchall()
    
    # Get summary statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_started,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(time_spent) as total_time_spent,
            AVG(score) as average_score
        FROM user_progress 
        WHERE user_id = ?
    ''', (user_id,))
    
    summary = cursor.fetchone()
    total_started, completed, total_time_spent, average_score = summary
    
    # Get total points earned from education
    cursor.execute('''
        SELECT SUM(ec.points_reward)
        FROM user_progress up
        JOIN educational_content ec ON up.content_id = ec.content_id
        WHERE up.user_id = ? AND up.status = 'completed'
    ''', (user_id,))
    
    total_points = cursor.fetchone()[0] or 0
    
    conn.close()
    
    progress_list = []
    for progress_item in progress_data:
        content_id, status, completion_date, score, time_spent, title, category, difficulty, points_reward = progress_item
        
        progress_list.append({
            "content_id": content_id,
            "title": title,
            "category": category,
            "difficulty": difficulty,
            "status": status,
            "completion_date": completion_date,
            "score": score,
            "time_spent": time_spent,
            "points_reward": points_reward
        })
    
    completion_rate = (completed / total_started * 100) if total_started > 0 else 0
    
    return {
        "user_id": user_id,
        "summary": {
            "total_content_started": total_started,
            "completed_count": completed,
            "completion_rate": completion_rate,
            "total_time_spent": total_time_spent,
            "average_quiz_score": average_score,
            "total_points_earned": total_points
        },
        "progress": progress_list
    }

@router.get("/learning-paths")
async def get_learning_paths(difficulty: Optional[str] = None):
    """Get structured learning paths for different skill levels"""
    
    learning_paths = [
        {
            "path_id": "beginner_stocks",
            "name": "Stock Trading for Beginners",
            "description": "Learn the fundamentals of stock market investing from scratch",
            "difficulty": "beginner",
            "estimated_time": 120,  # minutes
            "modules": ["basics_001", "basics_002", "stocks_001", "stocks_002"],
            "skills_learned": ["Market basics", "Order types", "Company analysis", "Risk management"]
        },
        {
            "path_id": "crypto_fundamentals", 
            "name": "Cryptocurrency Trading Fundamentals",
            "description": "Understanding blockchain technology and crypto markets",
            "difficulty": "beginner",
            "estimated_time": 90,
            "modules": ["crypto_001", "crypto_002", "crypto_003"],
            "skills_learned": ["Blockchain basics", "Major cryptocurrencies", "Wallet security", "Trading strategies"]
        },
        {
            "path_id": "options_mastery",
            "name": "Options Trading Mastery", 
            "description": "Advanced options strategies and risk management",
            "difficulty": "advanced",
            "estimated_time": 180,
            "modules": ["options_001", "options_002", "options_003", "options_004"],
            "skills_learned": ["Options basics", "Spread strategies", "Greeks", "Risk management"]
        },
        {
            "path_id": "technical_analysis",
            "name": "Technical Analysis Bootcamp",
            "description": "Master chart patterns and technical indicators",
            "difficulty": "intermediate", 
            "estimated_time": 150,
            "modules": ["tech_001", "tech_002", "tech_003", "tech_004"],
            "skills_learned": ["Chart patterns", "Technical indicators", "Trend analysis", "Entry/exit timing"]
        },
        {
            "path_id": "portfolio_management",
            "name": "Portfolio Management Essentials",
            "description": "Build and manage diversified investment portfolios",
            "difficulty": "intermediate",
            "estimated_time": 135,
            "modules": ["portfolio_001", "portfolio_002", "portfolio_003"],
            "skills_learned": ["Asset allocation", "Diversification", "Risk assessment", "Rebalancing"]
        }
    ]
    
    if difficulty:
        learning_paths = [path for path in learning_paths if path["difficulty"] == difficulty]
    
    return {"learning_paths": learning_paths}

@router.get("/quizzes")
async def get_available_quizzes(category: Optional[str] = None):
    """Get available quizzes"""
    
    sample_quizzes = [
        {
            "quiz_id": "stocks_basics_quiz",
            "title": "Stock Market Basics Quiz",
            "category": "stocks",
            "difficulty": "beginner",
            "question_count": 10,
            "time_limit": 15,
            "passing_score": 70,
            "points_reward": 25,
            "description": "Test your knowledge of basic stock market concepts"
        },
        {
            "quiz_id": "crypto_fundamentals_quiz", 
            "title": "Cryptocurrency Fundamentals Quiz",
            "category": "crypto",
            "difficulty": "beginner", 
            "question_count": 12,
            "time_limit": 20,
            "passing_score": 75,
            "points_reward": 30,
            "description": "Assess your understanding of cryptocurrency basics"
        },
        {
            "quiz_id": "options_strategies_quiz",
            "title": "Options Strategies Quiz",
            "category": "options",
            "difficulty": "advanced",
            "question_count": 15,
            "time_limit": 25,
            "passing_score": 80,
            "points_reward": 50,
            "description": "Advanced quiz on options trading strategies"
        },
        {
            "quiz_id": "risk_management_quiz",
            "title": "Risk Management Quiz",
            "category": "basics",
            "difficulty": "intermediate",
            "question_count": 8,
            "time_limit": 12,
            "passing_score": 75,
            "points_reward": 20,
            "description": "Test your knowledge of investment risk management"
        }
    ]
    
    if category:
        sample_quizzes = [quiz for quiz in sample_quizzes if quiz["category"] == category]
    
    return {"quizzes": sample_quizzes}

@router.get("/quiz/{quiz_id}")
async def get_quiz_questions(quiz_id: str):
    """Get quiz questions for taking the quiz"""
    
    # Sample quiz questions - in production, these would be in the database
    sample_questions = {
        "stocks_basics_quiz": [
            {
                "question": "What does P/E ratio stand for?",
                "options": ["Price to Earnings", "Profit to Equity", "Price to Equity", "Profit to Earnings"],
                "correct_answer": 0,
                "explanation": "P/E ratio stands for Price-to-Earnings ratio, which compares a company's share price to its earnings per share."
            },
            {
                "question": "What type of order guarantees execution but not price?",
                "options": ["Limit order", "Market order", "Stop order", "Stop-limit order"],
                "correct_answer": 1,
                "explanation": "A market order guarantees execution at the best available price, but the exact price is not guaranteed."
            },
            {
                "question": "Which of these represents ownership in a company?",
                "options": ["Bonds", "Stocks", "Options", "Futures"],
                "correct_answer": 1,
                "explanation": "Stocks represent ownership shares in a company, while bonds are debt instruments."
            }
        ]
    }
    
    if quiz_id not in sample_questions:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return {
        "quiz_id": quiz_id,
        "questions": sample_questions[quiz_id],
        "time_limit": 15,
        "passing_score": 70
    }

@router.post("/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    user_id: str,
    answers: List[int],
    time_taken: int
):
    """Submit quiz answers and get results"""
    
    # Get correct answers (simplified - would be from database)
    correct_answers = {
        "stocks_basics_quiz": [0, 1, 1]  # Correct answer indices
    }
    
    if quiz_id not in correct_answers:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz_correct_answers = correct_answers[quiz_id]
    
    # Calculate score
    if len(answers) != len(quiz_correct_answers):
        raise HTTPException(status_code=400, detail="Invalid number of answers")
    
    correct_count = sum(1 for i, answer in enumerate(answers) if answer == quiz_correct_answers[i])
    score = int((correct_count / len(quiz_correct_answers)) * 100)
    passed = score >= 70  # 70% passing score
    
    # Award points if passed
    points_awarded = 25 if passed else 10  # Participation points
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update user CC balance
    cursor.execute('UPDATE users SET cc_balance = cc_balance + ? WHERE user_id = ?',
                  (points_awarded, user_id))
    
    # Record progress
    cursor.execute('''
        INSERT OR REPLACE INTO user_progress 
        (user_id, content_id, status, completion_date, score, time_spent)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, quiz_id, "completed", datetime.now().isoformat(), score, time_taken))
    
    conn.commit()
    conn.close()
    
    return {
        "quiz_id": quiz_id,
        "score": score,
        "correct_answers": correct_count,
        "total_questions": len(quiz_correct_answers),
        "passed": passed,
        "points_awarded": points_awarded,
        "time_taken": time_taken,
        "detailed_results": [
            {
                "question_number": i + 1,
                "your_answer": answers[i],
                "correct_answer": quiz_correct_answers[i],
                "correct": answers[i] == quiz_correct_answers[i]
            }
            for i in range(len(answers))
        ]
    }

@router.get("/simulations")
async def get_market_simulations():
    """Get available market scenario simulations"""
    
    simulations = [
        {
            "simulation_id": "market_crash_2008",
            "name": "2008 Financial Crisis Simulation",
            "description": "Experience trading during the 2008 financial crisis and learn crisis management",
            "scenario_type": "market_crash",
            "starting_capital": 100000,
            "duration_days": 180,
            "difficulty": "advanced",
            "learning_objectives": [
                "Crisis portfolio management",
                "Defensive investing strategies", 
                "Market timing challenges",
                "Recovery positioning"
            ],
            "market_conditions": {
                "volatility": "extreme",
                "trend": "bearish",
                "sector_rotation": True,
                "correlation_breakdown": True
            }
        },
        {
            "simulation_id": "dot_com_boom",
            "name": "Dot-com Boom and Bust",
            "description": "Navigate the technology bubble of the late 1990s and early 2000s",
            "scenario_type": "bubble",
            "starting_capital": 50000,
            "duration_days": 365,
            "difficulty": "intermediate",
            "learning_objectives": [
                "Bubble identification",
                "Valuation analysis",
                "Risk management in euphoric markets",
                "Sector allocation"
            ],
            "market_conditions": {
                "volatility": "high",
                "trend": "parabolic_then_crash",
                "sector_focus": "technology",
                "irrational_exuberance": True
            }
        },
        {
            "simulation_id": "covid_crash_2020",
            "name": "COVID-19 Market Crash",
            "description": "Trade through the rapid market decline and recovery of 2020",
            "scenario_type": "black_swan",
            "starting_capital": 75000,
            "duration_days": 90,
            "difficulty": "intermediate",
            "learning_objectives": [
                "Black swan event response",
                "Sector rotation dynamics",
                "Fed policy impact",
                "Recovery trade identification"
            ],
            "market_conditions": {
                "volatility": "extreme",
                "trend": "V_shaped_recovery",
                "government_intervention": True,
                "sector_divergence": True
            }
        },
        {
            "simulation_id": "crypto_winter",
            "name": "Crypto Winter 2022",
            "description": "Navigate the cryptocurrency bear market and institutional collapse",
            "scenario_type": "crypto_bear",
            "starting_capital": 25000,
            "duration_days": 120,
            "difficulty": "advanced",
            "learning_objectives": [
                "Crypto market cycles",
                "Institutional risk",
                "Leverage dangers",
                "Alternative asset correlation"
            ],
            "market_conditions": {
                "volatility": "extreme",
                "trend": "bearish",
                "asset_class": "cryptocurrency",
                "counterparty_risk": True
            }
        }
    ]
    
    return {"simulations": simulations}

@router.post("/simulation/{simulation_id}/start")
async def start_simulation(simulation_id: str, user_id: str):
    """Start a market scenario simulation"""
    
    # Create a special portfolio for the simulation
    portfolio_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get simulation details (simplified)
        simulation_data = {
            "market_crash_2008": {"name": "2008 Financial Crisis", "capital": 100000},
            "dot_com_boom": {"name": "Dot-com Boom", "capital": 50000},
            "covid_crash_2020": {"name": "COVID-19 Crash", "capital": 75000},
            "crypto_winter": {"name": "Crypto Winter", "capital": 25000}
        }
        
        if simulation_id not in simulation_data:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        sim_info = simulation_data[simulation_id]
        
        # Create simulation portfolio
        cursor.execute('''
            INSERT INTO portfolios 
            (portfolio_id, user_id, name, starting_capital, current_cash, total_value, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (portfolio_id, user_id, f"Simulation: {sim_info['name']}", 
              sim_info['capital'], sim_info['capital'], sim_info['capital'], True))
        
        conn.commit()
        
        return {
            "simulation_id": simulation_id,
            "portfolio_id": portfolio_id,
            "message": "Simulation started successfully",
            "starting_capital": sim_info['capital']
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {str(e)}")
    
    finally:
        conn.close()

@router.get("/glossary")
async def get_trading_glossary():
    """Get trading terms glossary"""
    
    glossary_terms = [
        {
            "term": "Bull Market",
            "definition": "A market condition characterized by rising prices and optimistic investor sentiment.",
            "category": "market_conditions"
        },
        {
            "term": "Bear Market", 
            "definition": "A market condition where prices are falling and investor sentiment is pessimistic, typically defined as a 20% decline from recent highs.",
            "category": "market_conditions"
        },
        {
            "term": "P/E Ratio",
            "definition": "Price-to-Earnings ratio, a valuation metric that compares a company's share price to its earnings per share.",
            "category": "valuation"
        },
        {
            "term": "Market Cap",
            "definition": "Market capitalization, the total value of a company's shares calculated by multiplying share price by number of outstanding shares.",
            "category": "valuation"
        },
        {
            "term": "Dividend Yield",
            "definition": "Annual dividend per share divided by the stock price, expressed as a percentage.",
            "category": "fundamentals"
        },
        {
            "term": "Volatility",
            "definition": "A measure of the degree of variation in a security's price over time.",
            "category": "risk"
        },
        {
            "term": "Beta",
            "definition": "A measure of a stock's volatility relative to the overall market. A beta of 1 means the stock moves with the market.",
            "category": "risk"
        },
        {
            "term": "Limit Order",
            "definition": "An order to buy or sell a security at a specific price or better.",
            "category": "order_types"
        },
        {
            "term": "Market Order",
            "definition": "An order to buy or sell a security immediately at the best available price.",
            "category": "order_types"
        },
        {
            "term": "Short Selling",
            "definition": "Selling borrowed securities with the expectation that the price will decline, allowing you to buy them back at a lower price.",
            "category": "strategies"
        }
    ]
    
    return {"glossary": glossary_terms}

@router.get("/market-insights")
async def get_daily_market_insights():
    """Get daily market insights and educational content"""
    
    insights = [
        {
            "date": datetime.now().date().isoformat(),
            "title": "Understanding Market Volatility During Earnings Season",
            "content": "Earnings season typically brings increased volatility as companies report quarterly results. Key points to remember: 1) Even good earnings can lead to stock declines if they don't meet high expectations, 2) Focus on forward guidance rather than just past performance, 3) Consider the broader market context when evaluating individual stock reactions.",
            "category": "market_analysis",
            "related_concepts": ["earnings", "volatility", "expectations"]
        },
        {
            "date": datetime.now().date().isoformat(), 
            "title": "The Importance of Position Sizing",
            "content": "Proper position sizing is crucial for long-term success. The 2% rule suggests never risking more than 2% of your portfolio on a single trade. This helps preserve capital during inevitable losing streaks and allows you to stay in the game long enough for your edge to play out.",
            "category": "risk_management",
            "related_concepts": ["position_sizing", "risk_management", "capital_preservation"]
        },
        {
            "date": datetime.now().date().isoformat(),
            "title": "Cryptocurrency Correlation with Traditional Markets",
            "content": "Bitcoin and other cryptocurrencies have shown increasing correlation with traditional risk assets during market stress. This challenges the narrative of crypto as a 'digital gold' hedge and highlights the importance of understanding correlation dynamics in portfolio construction.",
            "category": "crypto_education", 
            "related_concepts": ["correlation", "diversification", "alternative_assets"]
        }
    ]
    
    return {"insights": insights}

@router.get("/learning-stats/{user_id}")
async def get_learning_statistics(user_id: str):
    """Get comprehensive learning statistics for a user"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get learning activity by category
    cursor.execute('''
        SELECT ec.category, COUNT(*) as completed_count, 
               AVG(up.score) as avg_score, SUM(up.time_spent) as total_time
        FROM user_progress up
        JOIN educational_content ec ON up.content_id = ec.content_id
        WHERE up.user_id = ? AND up.status = 'completed'
        GROUP BY ec.category
    ''', (user_id,))
    
    category_stats = cursor.fetchall()
    
    # Get learning streak (consecutive days with activity)
    cursor.execute('''
        SELECT DATE(completion_date) as date
        FROM user_progress
        WHERE user_id = ? AND status = 'completed' AND completion_date IS NOT NULL
        ORDER BY completion_date DESC
        LIMIT 30
    ''', (user_id,))
    
    recent_activity = [row[0] for row in cursor.fetchall()]
    
    # Calculate current streak
    current_streak = 0
    if recent_activity:
        last_date = datetime.fromisoformat(recent_activity[0]).date()
        current_date = datetime.now().date()
        
        while current_date >= last_date and str(current_date) in recent_activity:
            current_streak += 1
            current_date -= timedelta(days=1)
    
    conn.close()
    
    return {
        "user_id": user_id,
        "category_progress": [
            {
                "category": category,
                "completed_modules": completed,
                "average_score": avg_score,
                "time_spent": total_time
            }
            for category, completed, avg_score, total_time in category_stats
        ],
        "current_learning_streak": current_streak,
        "recent_activity_dates": recent_activity[:7],  # Last 7 days
        "total_learning_time": sum(row[3] for row in category_stats),
        "overall_average_score": sum(row[2] * row[1] for row in category_stats) / sum(row[1] for row in category_stats) if category_stats else 0
    }