#!/usr/bin/env python3

import os
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from decimal import Decimal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

# Import routers
from routers.trading import router as trading_router
from routers.market_data import router as market_data_router
from routers.portfolio import router as portfolio_router
from routers.competitions import router as competitions_router
from routers.education import router as education_router

# Background task for updating market data
async def update_market_data_periodically():
    """Background task to update market data every 15 minutes for free tier"""
    while True:
        try:
            # This would be implemented in market_data router
            print(f"⏰ Updating market data at {datetime.now()}")
            # await update_all_market_data()
        except Exception as e:
            print(f"❌ Error updating market data: {e}")
        
        # Wait 15 minutes (free tier delay)
        await asyncio.sleep(900)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_database()
    # Start background tasks for market data updates
    task = asyncio.create_task(update_market_data_periodically())
    yield
    # Shutdown
    task.cancel()

app = FastAPI(
    title="ActiveLog Paper Trading Platform",
    description="Comprehensive paper trading platform with real market data and competitions",
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
app.include_router(trading_router, prefix="/api/trading", tags=["trading"])
app.include_router(market_data_router, prefix="/api/market-data", tags=["market-data"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(competitions_router, prefix="/api/competitions", tags=["competitions"])
app.include_router(education_router, prefix="/api/education", tags=["education"])

# Database initialization
def init_database():
    """Initialize SQLite database with all required tables"""
    conn = sqlite3.connect('paper_trading.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age_group TEXT DEFAULT 'adult',
            experience_level TEXT DEFAULT 'beginner',
            starting_capital REAL DEFAULT 100000.0,
            current_cash REAL DEFAULT 100000.0,
            total_portfolio_value REAL DEFAULT 100000.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_premium BOOLEAN DEFAULT FALSE,
            cc_balance REAL DEFAULT 0.0
        )
    ''')
    
    # Portfolios table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            portfolio_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            starting_capital REAL NOT NULL,
            current_cash REAL NOT NULL,
            total_value REAL NOT NULL,
            day_change REAL DEFAULT 0.0,
            day_change_percent REAL DEFAULT 0.0,
            total_return REAL DEFAULT 0.0,
            total_return_percent REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Holdings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            holding_id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            asset_type TEXT NOT NULL, -- stock, crypto, forex, option, future, commodity, etf
            quantity REAL NOT NULL,
            average_cost REAL NOT NULL,
            current_price REAL DEFAULT 0.0,
            market_value REAL DEFAULT 0.0,
            day_change REAL DEFAULT 0.0,
            day_change_percent REAL DEFAULT 0.0,
            total_return REAL DEFAULT 0.0,
            total_return_percent REAL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios (portfolio_id)
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            action TEXT NOT NULL, -- buy, sell, short, cover
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            commission REAL DEFAULT 0.0,
            total_amount REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            order_type TEXT DEFAULT 'market', -- market, limit, stop
            notes TEXT,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios (portfolio_id)
        )
    ''')
    
    # Market data cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            symbol TEXT PRIMARY KEY,
            asset_type TEXT NOT NULL,
            current_price REAL NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            volume INTEGER,
            market_cap REAL,
            day_change REAL,
            day_change_percent REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_source TEXT
        )
    ''')
    
    # Competitions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitions (
            competition_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            competition_type TEXT NOT NULL, -- daily, weekly, monthly, tournament
            age_group TEXT DEFAULT 'all',
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            entry_fee_cc REAL DEFAULT 0.0,
            prize_pool_cc REAL DEFAULT 0.0,
            max_participants INTEGER,
            current_participants INTEGER DEFAULT 0,
            starting_capital REAL DEFAULT 100000.0,
            status TEXT DEFAULT 'upcoming', -- upcoming, active, completed, cancelled
            rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Competition entries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS competition_entries (
            entry_id TEXT PRIMARY KEY,
            competition_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            portfolio_id TEXT NOT NULL,
            entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            starting_value REAL NOT NULL,
            current_value REAL DEFAULT 0.0,
            current_rank INTEGER DEFAULT 0,
            final_rank INTEGER,
            prize_won_cc REAL DEFAULT 0.0,
            FOREIGN KEY (competition_id) REFERENCES competitions (competition_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (portfolio_id) REFERENCES portfolios (portfolio_id)
        )
    ''')
    
    # Achievements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            achievement_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL, -- trading, portfolio, competition, education
            icon TEXT,
            points INTEGER DEFAULT 0,
            requirements TEXT, -- JSON string with requirements
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # User achievements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id TEXT NOT NULL,
            achievement_id TEXT NOT NULL,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, achievement_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (achievement_id) REFERENCES achievements (achievement_id)
        )
    ''')
    
    # Educational content table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS educational_content (
            content_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL, -- article, video, quiz, simulation
            category TEXT NOT NULL, -- stocks, crypto, forex, options, basics
            difficulty TEXT DEFAULT 'beginner',
            content TEXT,
            video_url TEXT,
            quiz_questions TEXT, -- JSON string
            estimated_time INTEGER, -- minutes
            points_reward INTEGER DEFAULT 0,
            prerequisites TEXT, -- JSON array of required content_ids
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # User progress table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id TEXT NOT NULL,
            content_id TEXT NOT NULL,
            status TEXT DEFAULT 'not_started', -- not_started, in_progress, completed
            completion_date TIMESTAMP,
            score INTEGER, -- for quizzes
            time_spent INTEGER DEFAULT 0, -- minutes
            PRIMARY KEY (user_id, content_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (content_id) REFERENCES educational_content (content_id)
        )
    ''')
    
    # ActiveLog ecosystem companies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activelog_companies (
            company_id TEXT PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            sector TEXT,
            market_cap REAL DEFAULT 0.0,
            shares_outstanding INTEGER DEFAULT 1000000,
            current_price REAL DEFAULT 1.00,
            founding_date TIMESTAMP,
            description TEXT,
            ceo TEXT,
            headquarters TEXT,
            employees INTEGER DEFAULT 1,
            revenue REAL DEFAULT 0.0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample ActiveLog ecosystem companies
    activelog_companies = [
        ('ALOG', 'ActiveLog Core', 'Technology', 'AI-powered business analytics platform', 'San Francisco, CA'),
        ('FUND', 'ActiveLog Fundraising', 'Financial Services', 'Equity crowdfunding platform', 'New York, NY'),
        ('TRADE', 'ActiveLog Trading', 'Financial Services', 'Equity trading and investment platform', 'Chicago, IL'),
        ('PAPER', 'ActiveLog Paper Trading', 'Education', 'Investment education and simulation', 'Austin, TX'),
        ('REAL', 'ActiveLog Real Estate', 'Real Estate', 'Real estate investment platform', 'Los Angeles, CA'),
        ('GAME', 'ActiveLog Gaming', 'Entertainment', 'Gaming and entertainment platform', 'Seattle, WA'),
        ('HEALTH', 'ActiveLog Health', 'Healthcare', 'Digital health and wellness platform', 'Boston, MA'),
        ('GREEN', 'ActiveLog Green Energy', 'Energy', 'Renewable energy solutions', 'Denver, CO'),
        ('SPACE', 'ActiveLog Space', 'Aerospace', 'Commercial space technology', 'Houston, TX'),
        ('FOOD', 'ActiveLog Food Tech', 'Food Technology', 'Food technology and delivery', 'Portland, OR')
    ]
    
    for symbol, name, sector, description, hq in activelog_companies:
        cursor.execute('''
            INSERT OR IGNORE INTO activelog_companies 
            (company_id, symbol, name, sector, description, headquarters, current_price, market_cap)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, symbol, name, sector, description, hq, 1.00, 1000000.0))
    
    # Insert sample educational content
    educational_content = [
        ('basics_001', 'Introduction to Stock Trading', 'article', 'basics', 'beginner', 
         'Learn the fundamentals of stock trading including market orders, limit orders, and basic terminology.', 15),
        ('basics_002', 'Understanding Market Analysis', 'article', 'basics', 'beginner',
         'Introduction to technical and fundamental analysis techniques for evaluating investments.', 20),
        ('crypto_001', 'Cryptocurrency Basics', 'article', 'crypto', 'beginner',
         'Understanding blockchain technology, Bitcoin, Ethereum, and other major cryptocurrencies.', 25),
        ('options_001', 'Options Trading Fundamentals', 'article', 'options', 'intermediate',
         'Learn about call options, put options, and basic options strategies.', 30),
        ('forex_001', 'Foreign Exchange Trading', 'article', 'forex', 'intermediate',
         'Understanding currency pairs, pips, leverage, and forex market dynamics.', 25),
    ]
    
    for content_id, title, content_type, category, difficulty, content, time in educational_content:
        cursor.execute('''
            INSERT OR IGNORE INTO educational_content 
            (content_id, title, content_type, category, difficulty, content, estimated_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (content_id, title, content_type, category, difficulty, content, time))
    
    # Insert sample achievements
    achievements = [
        ('first_trade', 'First Trade', 'Complete your first paper trade', 'trading', '🎯', 10),
        ('profitable_week', 'Profitable Week', 'End a week with positive returns', 'trading', '📈', 25),
        ('diversified_portfolio', 'Diversified Portfolio', 'Hold stocks from 5 different sectors', 'portfolio', '🎨', 20),
        ('competition_winner', 'Competition Winner', 'Win a trading competition', 'competition', '🏆', 100),
        ('education_seeker', 'Education Seeker', 'Complete 10 educational modules', 'education', '📚', 50),
        ('risk_manager', 'Risk Manager', 'Keep portfolio volatility under 15%', 'portfolio', '🛡️', 30),
        ('dividend_collector', 'Dividend Collector', 'Collect $1000 in dividends', 'trading', '💰', 40),
        ('options_trader', 'Options Trader', 'Execute 10 options trades', 'trading', '⚡', 60),
        ('crypto_pioneer', 'Crypto Pioneer', 'Trade 5 different cryptocurrencies', 'trading', '₿', 35),
        ('marathon_trader', 'Marathon Trader', 'Trade consistently for 30 days', 'trading', '🏃', 75)
    ]
    
    for achievement_id, name, description, category, icon, points in achievements:
        cursor.execute('''
            INSERT OR IGNORE INTO achievements 
            (achievement_id, name, description, category, icon, points)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (achievement_id, name, description, category, icon, points))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "ActiveLog Paper Trading Platform",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Real-time market data",
            "Multiple asset classes",
            "Portfolio simulation",
            "Trading competitions",
            "Educational content",
            "Achievement system"
        ],
        "supported_assets": [
            "stocks",
            "cryptocurrency", 
            "forex",
            "options",
            "futures",
            "commodities",
            "etfs",
            "activelog_ecosystem"
        ]
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "database": "connected",
        "market_data": "updating"
    }

# Dashboard HTML endpoint
@app.get("/dashboard-ui", response_class=HTMLResponse)
async def dashboard_ui(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Dashboard endpoint
@app.get("/dashboard")
async def get_dashboard_data():
    """Get overall platform statistics for dashboard"""
    conn = sqlite3.connect('paper_trading.db')
    cursor = conn.cursor()
    
    # Get basic statistics
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM portfolios WHERE is_active = 1')
    active_portfolios = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM competitions WHERE status = "active"')
    active_competitions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM transactions WHERE timestamp > datetime("now", "-24 hours")')
    daily_trades = cursor.fetchone()[0]
    
    # Get top performers
    cursor.execute('''
        SELECT u.username, p.total_return_percent 
        FROM portfolios p 
        JOIN users u ON p.user_id = u.user_id 
        WHERE p.is_active = 1 
        ORDER BY p.total_return_percent DESC 
        LIMIT 5
    ''')
    top_performers = cursor.fetchall()
    
    conn.close()
    
    return {
        "platform_stats": {
            "total_users": total_users,
            "active_portfolios": active_portfolios,
            "active_competitions": active_competitions,
            "daily_trades": daily_trades
        },
        "top_performers": [
            {"username": username, "return": return_pct}
            for username, return_pct in top_performers
        ],
        "market_status": "open",  # This would be dynamic based on market hours
        "featured_competition": "Weekly Stock Challenge",
        "education_spotlight": "Options Trading Basics"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8413))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )