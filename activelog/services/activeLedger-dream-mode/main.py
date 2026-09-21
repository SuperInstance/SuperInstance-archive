#!/usr/bin/env python3
"""
ActiveLedger Dream Mode Trading
Virtual CC trading system for practice and learning
Safe environment before real trading
"""

import asyncio
import json
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
import os
from datetime import datetime, timedelta

app = FastAPI(title="ActiveLedger Dream Mode Trading", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class DreamModeUser:
    user_id: str
    virtual_cc_balance: Decimal
    dream_trades_count: int
    total_pnl: Decimal
    best_trade: Decimal
    worst_trade: Decimal
    trading_streak: int
    created_timestamp: float
    last_trade_timestamp: Optional[float] = None
    graduation_eligible: bool = False
    real_trading_enabled: bool = False

@dataclass
class DreamTrade:
    id: str
    user_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: Decimal
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    status: str = 'open'  # 'open', 'closed'
    entry_timestamp: float = 0
    exit_timestamp: Optional[float] = None
    lessons_learned: Optional[str] = None

@dataclass
class MarketSimulation:
    symbol: str
    current_price: Decimal
    price_history: List[Dict[str, Any]]
    volatility: float
    trend_direction: str  # 'up', 'down', 'sideways'
    last_update: float

class DreamModeTrading:
    def __init__(self):
        self.virtual_cc_starting_amount = Decimal('10000')  # Start with 10,000 virtual CC
        self.graduation_requirements = {
            'min_trades': 100,
            'min_pnl': Decimal('1000'),  # Must make at least 1,000 virtual CC profit
            'min_win_rate': 0.6,  # 60% win rate
            'max_drawdown': Decimal('2000')  # Max loss of 2,000 virtual CC
        }
        self.db_path = "data/dream_mode.db"
        self.market_data: Dict[str, MarketSimulation] = {}
        self._init_database()
        self._init_market_simulation()
    
    def _init_database(self):
        """Initialize SQLite database for dream mode data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Dream mode users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dream_users (
                user_id TEXT PRIMARY KEY,
                virtual_cc_balance TEXT NOT NULL,
                dream_trades_count INTEGER NOT NULL DEFAULT 0,
                total_pnl TEXT NOT NULL DEFAULT '0',
                best_trade TEXT NOT NULL DEFAULT '0',
                worst_trade TEXT NOT NULL DEFAULT '0',
                trading_streak INTEGER NOT NULL DEFAULT 0,
                created_timestamp REAL NOT NULL,
                last_trade_timestamp REAL,
                graduation_eligible BOOLEAN NOT NULL DEFAULT 0,
                real_trading_enabled BOOLEAN NOT NULL DEFAULT 0
            )
        ''')
        
        # Dream trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dream_trades (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity TEXT NOT NULL,
                entry_price TEXT NOT NULL,
                exit_price TEXT,
                pnl TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                entry_timestamp REAL NOT NULL,
                exit_timestamp REAL,
                lessons_learned TEXT
            )
        ''')
        
        # Learning progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_progress (
                user_id TEXT NOT NULL,
                lesson_id TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                completion_timestamp REAL,
                score INTEGER,
                PRIMARY KEY (user_id, lesson_id)
            )
        ''')
        
        # Achievement table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                achievement_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                earned_timestamp REAL NOT NULL,
                reward_cc INTEGER NOT NULL DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_market_simulation(self):
        """Initialize simulated market data"""
        symbols = ['ACTIVELEDGER', 'COMPUTECAPITAL', 'DREAMSHARES', 'INNOVATEFUND', 'TECHVENTURE']
        
        for symbol in symbols:
            self.market_data[symbol] = MarketSimulation(
                symbol=symbol,
                current_price=Decimal('100.00'),
                price_history=[],
                volatility=0.02,  # 2% volatility
                trend_direction='sideways',
                last_update=time.time()
            )
        
        # Start market simulation
        asyncio.create_task(self._simulate_market_data())
    
    async def _simulate_market_data(self):
        """Simulate realistic market price movements"""
        import random
        import math
        
        while True:
            current_time = time.time()
            
            for symbol, market in self.market_data.items():
                # Generate realistic price movement
                dt = current_time - market.last_update
                if dt < 1:  # Update every second
                    continue
                
                # Random walk with trend and mean reversion
                random_factor = random.gauss(0, market.volatility)
                trend_factor = {
                    'up': 0.0001,
                    'down': -0.0001,
                    'sideways': 0
                }.get(market.trend_direction, 0)
                
                # Mean reversion (prices tend to return to 100)
                mean_reversion = (Decimal('100.00') - market.current_price) * Decimal('0.0001')
                
                price_change = market.current_price * (Decimal(str(random_factor)) + Decimal(str(trend_factor))) + mean_reversion
                new_price = market.current_price + price_change
                
                # Ensure price stays positive and reasonable
                new_price = max(new_price, Decimal('1.00'))
                new_price = min(new_price, Decimal('1000.00'))
                
                market.current_price = new_price
                market.last_update = current_time
                
                # Store price history
                market.price_history.append({
                    'timestamp': current_time,
                    'price': float(new_price),
                    'volume': random.randint(1000, 10000)
                })
                
                # Keep only last 1000 price points
                if len(market.price_history) > 1000:
                    market.price_history = market.price_history[-1000:]
                
                # Occasionally change trend
                if random.random() < 0.001:  # 0.1% chance per update
                    market.trend_direction = random.choice(['up', 'down', 'sideways'])
            
            await asyncio.sleep(1)  # Update every second
    
    def get_or_create_user(self, user_id: str) -> DreamModeUser:
        """Get existing dream mode user or create new one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM dream_users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            columns = ['user_id', 'virtual_cc_balance', 'dream_trades_count', 'total_pnl',
                      'best_trade', 'worst_trade', 'trading_streak', 'created_timestamp',
                      'last_trade_timestamp', 'graduation_eligible', 'real_trading_enabled']
            user_data = dict(zip(columns, row))
            
            user = DreamModeUser(
                user_id=user_data['user_id'],
                virtual_cc_balance=Decimal(user_data['virtual_cc_balance']),
                dream_trades_count=user_data['dream_trades_count'],
                total_pnl=Decimal(user_data['total_pnl']),
                best_trade=Decimal(user_data['best_trade']),
                worst_trade=Decimal(user_data['worst_trade']),
                trading_streak=user_data['trading_streak'],
                created_timestamp=user_data['created_timestamp'],
                last_trade_timestamp=user_data['last_trade_timestamp'],
                graduation_eligible=bool(user_data['graduation_eligible']),
                real_trading_enabled=bool(user_data['real_trading_enabled'])
            )
        else:
            user = DreamModeUser(
                user_id=user_id,
                virtual_cc_balance=self.virtual_cc_starting_amount,
                dream_trades_count=0,
                total_pnl=Decimal('0'),
                best_trade=Decimal('0'),
                worst_trade=Decimal('0'),
                trading_streak=0,
                created_timestamp=time.time()
            )
            self._store_user(user)
        
        conn.close()
        return user
    
    def _store_user(self, user: DreamModeUser):
        """Store dream mode user in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO dream_users
            (user_id, virtual_cc_balance, dream_trades_count, total_pnl, best_trade, 
             worst_trade, trading_streak, created_timestamp, last_trade_timestamp, 
             graduation_eligible, real_trading_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.user_id,
            str(user.virtual_cc_balance),
            user.dream_trades_count,
            str(user.total_pnl),
            str(user.best_trade),
            str(user.worst_trade),
            user.trading_streak,
            user.created_timestamp,
            user.last_trade_timestamp,
            user.graduation_eligible,
            user.real_trading_enabled
        ))
        
        conn.commit()
        conn.close()
    
    def place_dream_trade(self, user_id: str, symbol: str, side: str, quantity: Decimal) -> DreamTrade:
        """Place a dream mode trade"""
        user = self.get_or_create_user(user_id)
        
        if symbol not in self.market_data:
            raise ValueError(f"Symbol {symbol} not available")
        
        current_price = self.market_data[symbol].current_price
        trade_value = quantity * current_price
        
        # Check if user has sufficient virtual CC for buy orders
        if side == 'buy' and user.virtual_cc_balance < trade_value:
            raise ValueError(f"Insufficient virtual CC balance: {user.virtual_cc_balance} < {trade_value}")
        
        # Create dream trade
        dream_trade = DreamTrade(
            id=str(uuid.uuid4()),
            user_id=user_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=current_price,
            entry_timestamp=time.time()
        )
        
        # Update user's virtual balance
        if side == 'buy':
            user.virtual_cc_balance -= trade_value
        else:  # sell
            user.virtual_cc_balance += trade_value
        
        user.dream_trades_count += 1
        user.last_trade_timestamp = time.time()
        
        # Store trade and update user
        self._store_dream_trade(dream_trade)
        self._store_user(user)
        
        # Award achievement for first trade
        if user.dream_trades_count == 1:
            self._award_achievement(user_id, "first_trade", "First Dream Trade", 
                                  "Congratulations on your first dream trade!", 100)
        
        return dream_trade
    
    def close_dream_trade(self, user_id: str, trade_id: str, lessons_learned: str = None) -> DreamTrade:
        """Close an open dream trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM dream_trades WHERE id = ? AND user_id = ?', (trade_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise ValueError("Trade not found")
        
        if row[8] == 'closed':  # status column
            conn.close()
            raise ValueError("Trade already closed")
        
        # Get current market price
        symbol = row[2]
        current_price = self.market_data[symbol].current_price
        
        # Calculate P&L
        entry_price = Decimal(row[5])
        quantity = Decimal(row[4])
        side = row[3]
        
        if side == 'buy':
            pnl = (current_price - entry_price) * quantity
        else:  # sell
            pnl = (entry_price - current_price) * quantity
        
        # Update trade
        cursor.execute('''
            UPDATE dream_trades 
            SET exit_price = ?, pnl = ?, status = 'closed', 
                exit_timestamp = ?, lessons_learned = ?
            WHERE id = ?
        ''', (str(current_price), str(pnl), time.time(), lessons_learned, trade_id))
        
        conn.commit()
        conn.close()
        
        # Update user statistics
        user = self.get_or_create_user(user_id)
        user.virtual_cc_balance += pnl  # Add/subtract P&L
        user.total_pnl += pnl
        
        if pnl > user.best_trade:
            user.best_trade = pnl
        if pnl < user.worst_trade:
            user.worst_trade = pnl
        
        # Update trading streak
        if pnl > 0:
            user.trading_streak += 1
        else:
            user.trading_streak = 0
        
        # Check graduation eligibility
        user.graduation_eligible = self._check_graduation_eligibility(user)
        
        self._store_user(user)
        
        # Award achievements
        if pnl > Decimal('500'):
            self._award_achievement(user_id, "big_winner", "Big Winner", 
                                  f"Made a profit of {pnl} CC on a single trade!", 200)
        
        if user.trading_streak >= 5:
            self._award_achievement(user_id, "streak_5", "5-Trade Streak", 
                                  "Won 5 trades in a row!", 300)
        
        # Create updated trade object
        dream_trade = DreamTrade(
            id=trade_id,
            user_id=user_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=current_price,
            pnl=pnl,
            status='closed',
            entry_timestamp=float(row[9]),
            exit_timestamp=time.time(),
            lessons_learned=lessons_learned
        )
        
        return dream_trade
    
    def _store_dream_trade(self, trade: DreamTrade):
        """Store dream trade in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dream_trades
            (id, user_id, symbol, side, quantity, entry_price, exit_price, pnl, 
             status, entry_timestamp, exit_timestamp, lessons_learned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.id,
            trade.user_id,
            trade.symbol,
            trade.side,
            str(trade.quantity),
            str(trade.entry_price),
            str(trade.exit_price) if trade.exit_price else None,
            str(trade.pnl) if trade.pnl else None,
            trade.status,
            trade.entry_timestamp,
            trade.exit_timestamp,
            trade.lessons_learned
        ))
        
        conn.commit()
        conn.close()
    
    def _check_graduation_eligibility(self, user: DreamModeUser) -> bool:
        """Check if user is eligible to graduate to real trading"""
        if user.dream_trades_count < self.graduation_requirements['min_trades']:
            return False
        
        if user.total_pnl < self.graduation_requirements['min_pnl']:
            return False
        
        # Check win rate
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN CAST(pnl AS REAL) > 0 THEN 1 ELSE 0 END) as wins
            FROM dream_trades 
            WHERE user_id = ? AND status = 'closed'
        ''', (user.user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row[0] == 0:  # No closed trades
            return False
        
        win_rate = row[1] / row[0]
        if win_rate < self.graduation_requirements['min_win_rate']:
            return False
        
        # Check max drawdown (simplified check)
        if user.worst_trade < -self.graduation_requirements['max_drawdown']:
            return False
        
        return True
    
    def graduate_to_real_trading(self, user_id: str) -> bool:
        """Graduate user from dream mode to real trading"""
        user = self.get_or_create_user(user_id)
        
        if not user.graduation_eligible:
            return False
        
        user.real_trading_enabled = True
        self._store_user(user)
        
        # Award graduation achievement
        self._award_achievement(user_id, "graduation", "Graduated to Real Trading", 
                              "Successfully completed dream mode training!", 1000)
        
        return True
    
    def _award_achievement(self, user_id: str, achievement_type: str, title: str, 
                          description: str, reward_cc: int):
        """Award achievement to user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if achievement already exists
        cursor.execute('''
            SELECT id FROM achievements 
            WHERE user_id = ? AND achievement_type = ?
        ''', (user_id, achievement_type))
        
        if cursor.fetchone():
            conn.close()
            return  # Achievement already awarded
        
        # Create achievement
        achievement_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO achievements
            (id, user_id, achievement_type, title, description, earned_timestamp, reward_cc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (achievement_id, user_id, achievement_type, title, description, time.time(), reward_cc))
        
        # Add reward CC to user's balance
        if reward_cc > 0:
            user = self.get_or_create_user(user_id)
            user.virtual_cc_balance += Decimal(str(reward_cc))
            self._store_user(user)
        
        conn.commit()
        conn.close()

# Initialize dream mode trading
dream_mode = DreamModeTrading()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dream-mode-trading"}

@app.get("/api/dream/user/{user_id}")
async def get_dream_user(user_id: str):
    """Get dream mode user profile"""
    user = dream_mode.get_or_create_user(user_id)
    return {"success": True, "user": asdict(user)}

@app.get("/api/dream/market/{symbol}")
async def get_market_data(symbol: str):
    """Get simulated market data"""
    if symbol not in dream_mode.market_data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    market = dream_mode.market_data[symbol]
    return {
        "success": True,
        "market_data": {
            "symbol": market.symbol,
            "current_price": float(market.current_price),
            "price_history": market.price_history[-100:],  # Last 100 points
            "volatility": market.volatility,
            "trend_direction": market.trend_direction
        }
    }

@app.get("/api/dream/markets")
async def get_all_markets():
    """Get all available markets"""
    markets = {}
    for symbol, market in dream_mode.market_data.items():
        markets[symbol] = {
            "current_price": float(market.current_price),
            "trend_direction": market.trend_direction,
            "volatility": market.volatility
        }
    
    return {"success": True, "markets": markets}

@app.post("/api/dream/trade")
async def place_dream_trade(trade_data: dict):
    """Place a dream mode trade"""
    try:
        dream_trade = dream_mode.place_dream_trade(
            user_id=trade_data['user_id'],
            symbol=trade_data['symbol'],
            side=trade_data['side'],
            quantity=Decimal(str(trade_data['quantity']))
        )
        return {"success": True, "trade": asdict(dream_trade)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/dream/trade/{trade_id}/close")
async def close_dream_trade(trade_id: str, close_data: dict):
    """Close a dream mode trade"""
    try:
        dream_trade = dream_mode.close_dream_trade(
            user_id=close_data['user_id'],
            trade_id=trade_id,
            lessons_learned=close_data.get('lessons_learned')
        )
        return {"success": True, "trade": asdict(dream_trade)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/dream/trades/{user_id}")
async def get_user_trades(user_id: str, status: str = None, limit: int = 50):
    """Get user's dream trades"""
    conn = sqlite3.connect(dream_mode.db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM dream_trades WHERE user_id = ?"
    params = [user_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY entry_timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    columns = ['id', 'user_id', 'symbol', 'side', 'quantity', 'entry_price', 
              'exit_price', 'pnl', 'status', 'entry_timestamp', 'exit_timestamp', 
              'lessons_learned']
    
    trades = []
    for row in rows:
        trade_data = dict(zip(columns, row))
        trades.append(trade_data)
    
    return {"success": True, "trades": trades}

@app.post("/api/dream/graduate")
async def graduate_user(user_data: dict):
    """Graduate user to real trading"""
    user_id = user_data['user_id']
    success = dream_mode.graduate_to_real_trading(user_id)
    
    if success:
        return {"success": True, "message": "Congratulations! You've graduated to real trading."}
    else:
        return {"success": False, "message": "Graduation requirements not met."}

@app.get("/api/dream/achievements/{user_id}")
async def get_achievements(user_id: str):
    """Get user's achievements"""
    conn = sqlite3.connect(dream_mode.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM achievements 
        WHERE user_id = ? 
        ORDER BY earned_timestamp DESC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    columns = ['id', 'user_id', 'achievement_type', 'title', 'description', 
              'earned_timestamp', 'reward_cc']
    
    achievements = []
    for row in rows:
        achievement_data = dict(zip(columns, row))
        achievements.append(achievement_data)
    
    return {"success": True, "achievements": achievements}

@app.get("/api/dream/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get dream mode leaderboard"""
    conn = sqlite3.connect(dream_mode.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, total_pnl, dream_trades_count, trading_streak, graduation_eligible
        FROM dream_users 
        ORDER BY CAST(total_pnl AS REAL) DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    leaderboard = []
    for i, row in enumerate(rows, 1):
        leaderboard.append({
            "rank": i,
            "user_id": row[0],
            "total_pnl": row[1],
            "trades_count": row[2],
            "trading_streak": row[3],
            "graduation_eligible": bool(row[4])
        })
    
    return {"success": True, "leaderboard": leaderboard}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8510))
    uvicorn.run(app, host="0.0.0.0", port=port)