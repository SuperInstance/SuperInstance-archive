"""
Quick Analysis Portal - Easy Access Financial Analysis Tools
Direct URL: analysis.activeledger.ai
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
import json
import time
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change in production
CORS(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

class UserTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class UserSession:
    user_id: str
    tier: UserTier
    searches_today: int
    api_key: Optional[str] = None
    premium_expires: Optional[datetime] = None

# Database setup
DB_PATH = 'quick_analysis.db'

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        tier TEXT DEFAULT 'free',
        api_key TEXT,
        searches_today INTEGER DEFAULT 0,
        searches_reset_date TEXT,
        premium_expires TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )''')
    
    # Search history table
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        symbol TEXT,
        search_type TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Analysis cache table
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        analysis_type TEXT,
        data TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )''')
    
    # API usage tracking
    c.execute('''CREATE TABLE IF NOT EXISTS api_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        endpoint TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

class QuickAnalysisEngine:
    """Core analysis engine for financial data"""
    
    def __init__(self):
        self.data_sources = {
            'yahoo': self._fetch_yahoo_data,
            'alpha_vantage': self._fetch_alpha_vantage_data
        }
    
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get basic stock quote"""
        try:
            stock = yf.Ticker(symbol.upper())
            info = stock.info
            hist = stock.history(period="1d")
            
            if hist.empty:
                return {"error": "Symbol not found"}
            
            current_price = hist['Close'].iloc[-1]
            previous_close = info.get('previousClose', current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close else 0
            
            return {
                "symbol": symbol.upper(),
                "company_name": info.get('longName', symbol.upper()),
                "current_price": round(current_price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get('volume'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "52_week_high": info.get('fiftyTwoWeekHigh'),
                "52_week_low": info.get('fiftyTwoWeekLow'),
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {"error": f"Failed to fetch data for {symbol}"}
    
    def get_key_ratios(self, symbol: str) -> Dict[str, Any]:
        """Get key financial ratios"""
        try:
            stock = yf.Ticker(symbol.upper())
            info = stock.info
            
            return {
                "symbol": symbol.upper(),
                "pe_ratio": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),
                "price_to_book": info.get('priceToBook'),
                "price_to_sales": info.get('priceToSalesTrailing12Months'),
                "debt_to_equity": info.get('debtToEquity'),
                "return_on_equity": info.get('returnOnEquity'),
                "return_on_assets": info.get('returnOnAssets'),
                "profit_margin": info.get('profitMargins'),
                "operating_margin": info.get('operatingMargins'),
                "dividend_yield": info.get('dividendYield'),
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching ratios for {symbol}: {e}")
            return {"error": f"Failed to fetch ratios for {symbol}"}
    
    def get_chart_data(self, symbol: str, period: str = "1mo") -> Dict[str, Any]:
        """Get chart data for visualization"""
        try:
            stock = yf.Ticker(symbol.upper())
            hist = stock.history(period=period)
            
            if hist.empty:
                return {"error": "No data available"}
            
            # Convert to format suitable for charting
            chart_data = []
            for date, row in hist.iterrows():
                chart_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(row['Open'], 2),
                    "high": round(row['High'], 2),
                    "low": round(row['Low'], 2),
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume'])
                })
            
            return {
                "symbol": symbol.upper(),
                "period": period,
                "data": chart_data,
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching chart data for {symbol}: {e}")
            return {"error": f"Failed to fetch chart data for {symbol}"}
    
    def get_recent_news(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Get recent news for a symbol"""
        try:
            stock = yf.Ticker(symbol.upper())
            news = stock.news[:limit] if stock.news else []
            
            formatted_news = []
            for article in news:
                formatted_news.append({
                    "title": article.get('title', ''),
                    "publisher": article.get('publisher', ''),
                    "link": article.get('link', ''),
                    "publish_time": datetime.fromtimestamp(
                        article.get('providerPublishTime', time.time())
                    ).isoformat() if article.get('providerPublishTime') else None,
                    "summary": article.get('summary', '')[:200] + '...' if len(article.get('summary', '')) > 200 else article.get('summary', '')
                })
            
            return {
                "symbol": symbol.upper(),
                "news": formatted_news,
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return {"error": f"Failed to fetch news for {symbol}"}
    
    def get_analyst_consensus(self, symbol: str) -> Dict[str, Any]:
        """Get analyst consensus data"""
        try:
            stock = yf.Ticker(symbol.upper())
            info = stock.info
            
            return {
                "symbol": symbol.upper(),
                "target_mean_price": info.get('targetMeanPrice'),
                "target_high_price": info.get('targetHighPrice'),
                "target_low_price": info.get('targetLowPrice'),
                "recommendation_mean": info.get('recommendationMean'),
                "recommendation_key": info.get('recommendationKey'),
                "number_of_analyst_opinions": info.get('numberOfAnalystOpinions'),
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching analyst data for {symbol}: {e}")
            return {"error": f"Failed to fetch analyst data for {symbol}"}
    
    def _fetch_yahoo_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from Yahoo Finance"""
        return self.get_stock_quote(symbol)
    
    def _fetch_alpha_vantage_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from Alpha Vantage API"""
        # Placeholder for Alpha Vantage integration
        return {"error": "Alpha Vantage integration not implemented"}

class UserManager:
    """Manage user sessions and tiers"""
    
    def __init__(self):
        self.sessions = {}
    
    def get_or_create_user(self, session_id: str, email: str = None) -> UserSession:
        """Get existing user or create anonymous user"""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Check if existing user in database
        if email:
            user_data = self._get_user_by_email(email)
            if user_data:
                user_session = UserSession(
                    user_id=user_data['id'],
                    tier=UserTier(user_data['tier']),
                    searches_today=user_data['searches_today'],
                    api_key=user_data['api_key'],
                    premium_expires=datetime.fromisoformat(user_data['premium_expires']) if user_data['premium_expires'] else None
                )
                self.sessions[session_id] = user_session
                return user_session
        
        # Create anonymous user
        user_id = str(uuid.uuid4())
        user_session = UserSession(
            user_id=user_id,
            tier=UserTier.FREE,
            searches_today=0
        )
        
        # Store in database
        self._create_user(user_id, email)
        self.sessions[session_id] = user_session
        return user_session
    
    def check_search_limit(self, user_session: UserSession) -> bool:
        """Check if user has reached search limit"""
        if user_session.tier == UserTier.FREE:
            # Reset daily searches if it's a new day
            if self._should_reset_searches(user_session.user_id):
                self._reset_daily_searches(user_session.user_id)
                user_session.searches_today = 0
            
            return user_session.searches_today < 5
        elif user_session.tier == UserTier.PREMIUM:
            return True  # Unlimited searches
        else:
            return True  # Enterprise
    
    def increment_search_count(self, user_session: UserSession):
        """Increment user's search count"""
        user_session.searches_today += 1
        self._update_search_count(user_session.user_id, user_session.searches_today)
    
    def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user data by email"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        result = c.fetchone()
        conn.close()
        
        if result:
            columns = ['id', 'email', 'tier', 'api_key', 'searches_today', 
                      'searches_reset_date', 'premium_expires', 'created_at', 'last_login']
            return dict(zip(columns, result))
        return None
    
    def _create_user(self, user_id: str, email: str = None):
        """Create new user in database"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO users (id, email, searches_reset_date) 
                     VALUES (?, ?, ?)''', 
                  (user_id, email, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
    
    def _should_reset_searches(self, user_id: str) -> bool:
        """Check if daily searches should be reset"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT searches_reset_date FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            reset_date = datetime.strptime(result[0], '%Y-%m-%d').date()
            return reset_date < datetime.now().date()
        return True
    
    def _reset_daily_searches(self, user_id: str):
        """Reset daily search count"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''UPDATE users SET searches_today = 0, searches_reset_date = ? 
                     WHERE id = ?''', 
                  (datetime.now().strftime('%Y-%m-%d'), user_id))
        conn.commit()
        conn.close()
    
    def _update_search_count(self, user_id: str, count: int):
        """Update user's search count"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET searches_today = ? WHERE id = ?', (count, user_id))
        conn.commit()
        conn.close()

# Initialize components
analysis_engine = QuickAnalysisEngine()
user_manager = UserManager()

# HTML Templates
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quick Analysis Portal - ActiveLedger.ai</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1e40af">
    <link rel="icon" type="image/x-icon" href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiByeD0iOCIgZmlsbD0iIzFlNDBhZiIvPgo8cGF0aCBkPSJNOCAxNmwxNiAwIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiLz4KPHBhdGggZD0ibTE2IDhsOCA4bC04IDgiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIvPgo8L3N2Zz4K">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .header h1 {
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .header p {
            color: rgba(255,255,255,0.8);
            font-size: 1.1rem;
        }
        .quick-access {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .search-container {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            align-items: stretch;
        }
        .search-input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 1.1rem;
            outline: none;
            transition: all 0.3s;
        }
        .search-input:focus {
            border-color: #1e40af;
            box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.1);
        }
        .search-btn {
            background: #1e40af;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 15px 30px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .search-btn:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
        }
        .tier-info {
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #10b981;
        }
        .results-container {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            display: none;
        }
        .loading {
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 4px solid #f3f4f6;
            border-top: 4px solid #1e40af;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .stock-card {
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .stock-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .stock-price {
            font-size: 2rem;
            font-weight: bold;
            color: #1e40af;
        }
        .price-change {
            padding: 5px 10px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
        }
        .positive { background: #10b981; }
        .negative { background: #ef4444; }
        .keyboard-shortcuts {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 8px;
            font-size: 0.8rem;
            display: none;
        }
        .access-points {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .access-card {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
            color: white;
            text-decoration: none;
            transition: all 0.3s;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .access-card:hover {
            transform: translateY(-2px);
            background: rgba(255,255,255,0.2);
            color: white;
            text-decoration: none;
        }
        @media (max-width: 768px) {
            .search-container { flex-direction: column; }
            .header h1 { font-size: 2rem; }
            .container { padding: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Quick Analysis Portal</h1>
            <p>Instant financial analysis at analysis.activeledger.ai</p>
        </div>
        
        <div class="access-points">
            <a href="#" class="access-card" onclick="installPWA()">
                <h3>📱 Install PWA</h3>
                <p>Add to home screen for instant access</p>
            </a>
            <a href="/extension" class="access-card">
                <h3>🔧 Browser Extension</h3>
                <p>Right-click any stock ticker for analysis</p>
            </a>
            <a href="/api-docs" class="access-card">
                <h3>🔌 API Access</h3>
                <p>Integrate with your apps and tools</p>
            </a>
            <a href="/mobile-widget" class="access-card">
                <h3>📲 Mobile Widget</h3>
                <p>Quick access from your mobile device</p>
            </a>
        </div>

        <div class="quick-access">
            <div class="tier-info">
                <strong>Free Tier:</strong> {{ searches_left }} searches remaining today
                <a href="/premium" style="margin-left: 15px; color: #1e40af; text-decoration: none; font-weight: 600;">Upgrade to Premium →</a>
            </div>
            
            <div class="search-container">
                <input type="text" 
                       id="symbolInput" 
                       class="search-input" 
                       placeholder="Enter stock symbol (e.g., AAPL, TSLA, MSFT)"
                       autocomplete="off">
                <button onclick="quickAnalysis()" class="search-btn">Quick Analysis</button>
            </div>
            
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button onclick="analyzeSymbol('AAPL')" style="padding: 8px 16px; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer;">AAPL</button>
                <button onclick="analyzeSymbol('TSLA')" style="padding: 8px 16px; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer;">TSLA</button>
                <button onclick="analyzeSymbol('MSFT')" style="padding: 8px 16px; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer;">MSFT</button>
                <button onclick="analyzeSymbol('GOOGL')" style="padding: 8px 16px; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer;">GOOGL</button>
            </div>
        </div>

        <div id="resultsContainer" class="results-container">
            <div id="loadingSpinner" class="loading">
                <div class="spinner"></div>
                <p>Analyzing stock data...</p>
            </div>
            <div id="resultsContent"></div>
        </div>

        <div class="keyboard-shortcuts" id="shortcuts">
            <div><kbd>Ctrl</kbd> + <kbd>/</kbd> - Focus search</div>
            <div><kbd>Enter</kbd> - Search</div>
            <div><kbd>Esc</kbd> - Close results</div>
        </div>
    </div>

    <script>
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === '/') {
                e.preventDefault();
                document.getElementById('symbolInput').focus();
            }
            if (e.key === 'Enter' && document.activeElement.id === 'symbolInput') {
                quickAnalysis();
            }
            if (e.key === 'Escape') {
                document.getElementById('resultsContainer').style.display = 'none';
            }
            if (e.key === '?') {
                toggleShortcuts();
            }
        });

        function toggleShortcuts() {
            const shortcuts = document.getElementById('shortcuts');
            shortcuts.style.display = shortcuts.style.display === 'none' ? 'block' : 'none';
        }

        function analyzeSymbol(symbol) {
            document.getElementById('symbolInput').value = symbol;
            quickAnalysis();
        }

        async function quickAnalysis() {
            const symbol = document.getElementById('symbolInput').value.trim();
            if (!symbol) return;

            const container = document.getElementById('resultsContainer');
            const content = document.getElementById('resultsContent');
            const loading = document.getElementById('loadingSpinner');
            
            container.style.display = 'block';
            loading.style.display = 'block';
            content.innerHTML = '';

            try {
                const response = await fetch('/api/quick-analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol: symbol.toUpperCase() })
                });

                const data = await response.json();
                
                loading.style.display = 'none';
                
                if (data.error) {
                    content.innerHTML = `<div style="color: #ef4444; font-weight: 600;">❌ ${data.error}</div>`;
                    return;
                }

                renderAnalysisResults(data);
                
            } catch (error) {
                loading.style.display = 'none';
                content.innerHTML = '<div style="color: #ef4444; font-weight: 600;">❌ Failed to fetch analysis</div>';
            }
        }

        function renderAnalysisResults(data) {
            const content = document.getElementById('resultsContent');
            const quote = data.quote;
            const ratios = data.ratios;
            const news = data.news;
            const analyst = data.analyst;

            const changeClass = quote.change >= 0 ? 'positive' : 'negative';
            const changeSymbol = quote.change >= 0 ? '+' : '';

            content.innerHTML = `
                <div class="stock-card">
                    <div class="stock-header">
                        <div>
                            <h2>${quote.symbol} - ${quote.company_name}</h2>
                        </div>
                        <div style="text-align: right;">
                            <div class="stock-price">$${quote.current_price}</div>
                            <div class="price-change ${changeClass}">
                                ${changeSymbol}${quote.change} (${changeSymbol}${quote.change_percent.toFixed(2)}%)
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px;">
                        <div>
                            <strong>Volume:</strong><br>${quote.volume ? quote.volume.toLocaleString() : 'N/A'}
                        </div>
                        <div>
                            <strong>Market Cap:</strong><br>${quote.market_cap ? '$' + (quote.market_cap/1e9).toFixed(1) + 'B' : 'N/A'}
                        </div>
                        <div>
                            <strong>P/E Ratio:</strong><br>${quote.pe_ratio || 'N/A'}
                        </div>
                        <div>
                            <strong>52W Range:</strong><br>$${quote['52_week_low']} - $${quote['52_week_high']}
                        </div>
                    </div>
                </div>

                ${ratios && !ratios.error ? `
                <div class="stock-card">
                    <h3>📊 Key Ratios</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px;">
                        <div><strong>P/E:</strong> ${ratios.pe_ratio || 'N/A'}</div>
                        <div><strong>P/B:</strong> ${ratios.price_to_book || 'N/A'}</div>
                        <div><strong>ROE:</strong> ${ratios.return_on_equity ? (ratios.return_on_equity * 100).toFixed(1) + '%' : 'N/A'}</div>
                        <div><strong>Profit Margin:</strong> ${ratios.profit_margin ? (ratios.profit_margin * 100).toFixed(1) + '%' : 'N/A'}</div>
                    </div>
                </div>
                ` : ''}

                ${analyst && !analyst.error ? `
                <div class="stock-card">
                    <h3>👥 Analyst Consensus</h3>
                    <div style="margin-top: 15px;">
                        <div><strong>Target Price:</strong> $${analyst.target_mean_price || 'N/A'}</div>
                        <div><strong>Recommendation:</strong> ${analyst.recommendation_key || 'N/A'}</div>
                        <div><strong>Analysts:</strong> ${analyst.number_of_analyst_opinions || 'N/A'}</div>
                    </div>
                </div>
                ` : ''}

                ${news && !news.error ? `
                <div class="stock-card">
                    <h3>📰 Recent News</h3>
                    <div style="margin-top: 15px;">
                        ${news.news.slice(0, 3).map(article => `
                            <div style="border-bottom: 1px solid #e5e7eb; padding: 10px 0;">
                                <a href="${article.link}" target="_blank" style="color: #1e40af; text-decoration: none; font-weight: 600;">
                                    ${article.title}
                                </a>
                                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">
                                    ${article.publisher} • ${new Date(article.publish_time).toLocaleDateString()}
                                </div>
                                ${article.summary ? `<p style="margin-top: 5px; color: #666; font-size: 0.95rem;">${article.summary}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9rem;">
                    Free tier • Upgrade for unlimited access and real-time data
                </div>
            `;
        }

        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {
            deferredPrompt = e;
        });

        function installPWA() {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('PWA installed');
                    }
                    deferredPrompt = null;
                });
            } else {
                alert('To install: Add this page to your bookmarks or home screen from your browser menu');
            }
        }

        // Show shortcuts hint
        setTimeout(() => {
            if (!localStorage.getItem('shortcutsShown')) {
                document.getElementById('shortcuts').style.display = 'block';
                setTimeout(() => {
                    document.getElementById('shortcuts').style.display = 'none';
                    localStorage.setItem('shortcutsShown', 'true');
                }, 3000);
            }
        }, 2000);
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def home():
    """Main portal page"""
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    
    user_session = user_manager.get_or_create_user(session_id)
    searches_left = max(0, 5 - user_session.searches_today) if user_session.tier == UserTier.FREE else "Unlimited"
    
    return render_template_string(MAIN_TEMPLATE, searches_left=searches_left)

@app.route('/api/quick-analysis', methods=['POST'])
@limiter.limit("30 per minute")
def quick_analysis():
    """Quick analysis endpoint"""
    data = request.get_json()
    symbol = data.get('symbol', '').strip().upper()
    
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    
    # Get user session
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({"error": "Invalid session"}), 401
    
    user_session = user_manager.get_or_create_user(session_id)
    
    # Check search limits for free tier
    if not user_manager.check_search_limit(user_session):
        return jsonify({
            "error": "Daily search limit reached. Upgrade to Premium for unlimited searches.",
            "upgrade_url": "/premium"
        }), 429
    
    # Increment search count
    user_manager.increment_search_count(user_session)
    
    # Log search
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO search_history (user_id, symbol, search_type) VALUES (?, ?, ?)',
              (user_session.user_id, symbol, 'quick_analysis'))
    conn.commit()
    conn.close()
    
    try:
        # Get analysis data
        results = {
            "symbol": symbol,
            "quote": analysis_engine.get_stock_quote(symbol),
            "ratios": analysis_engine.get_key_ratios(symbol),
            "news": analysis_engine.get_recent_news(symbol),
            "analyst": analysis_engine.get_analyst_consensus(symbol),
            "tier": user_session.tier.value,
            "searches_remaining": max(0, 5 - user_session.searches_today) if user_session.tier == UserTier.FREE else "unlimited"
        }
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({"error": "Analysis failed"}), 500

@app.route('/manifest.json')
def manifest():
    """PWA manifest"""
    return jsonify({
        "name": "Quick Analysis Portal",
        "short_name": "QuickAnalysis",
        "description": "Instant financial analysis and stock data",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1e40af",
        "icons": [
            {
                "src": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTkyIiBoZWlnaHQ9IjE5MiIgdmlld0JveD0iMCAwIDE5MiAxOTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxOTIiIGhlaWdodD0iMTkyIiByeD0iNDgiIGZpbGw9IiMxZTQwYWYiLz4KPHBhdGggZD0iTTQ4IDk2bDk2IDAiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMTIiLz4KPHBhdGggZD0ibTk2IDQ4bDQ4IDQ4bC00OCA0OCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIxMiIgZmlsbD0ibm9uZSIvPgo8L3N2Zz4K",
                "sizes": "192x192",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            }
        ],
        "categories": ["finance", "business", "productivity"],
        "shortcuts": [
            {
                "name": "Quick Search",
                "short_name": "Search",
                "description": "Quick stock analysis",
                "url": "/?shortcut=search",
                "icons": [{"src": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOTYiIGhlaWdodD0iOTYiIHZpZXdCb3g9IjAgMCA5NiA5NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iMjgiIHN0cm9rZT0iIzFlNDBhZiIgc3Ryb2tlLXdpZHRoPSI4IiBmaWxsPSJub25lIi8+CjxwYXRoIGQ9Im02MCA2MGwyMCAyMCIgc3Ryb2tlPSIjMWU0MGFmIiBzdHJva2Utd2lkdGg9IjgiLz4KPC9zdmc+Cg==", "sizes": "96x96"}]
            }
        ]
    })

@app.route('/premium')
def premium_page():
    """Premium tier information page"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upgrade to Premium - Quick Analysis Portal</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: white; border-radius: 12px; padding: 30px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #1e40af; margin-bottom: 10px; }
            .feature { padding: 10px 0; border-bottom: 1px solid #e5e7eb; }
            .feature:last-child { border-bottom: none; }
            .price { font-size: 2rem; font-weight: bold; color: #1e40af; margin: 20px 0; }
            .btn { background: #1e40af; color: white; padding: 15px 30px; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #1d4ed8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>🚀 Upgrade to Premium</h1>
                <p>Unlock unlimited analysis and advanced features</p>
                
                <div class="price">$9.99/month</div>
                
                <div class="feature">✅ Unlimited stock analysis</div>
                <div class="feature">✅ Real-time data</div>
                <div class="feature">✅ Advanced charts and indicators</div>
                <div class="feature">✅ Full financial reports</div>
                <div class="feature">✅ API access for integrations</div>
                <div class="feature">✅ No advertisements</div>
                <div class="feature">✅ Priority customer support</div>
                <div class="feature">✅ Custom alerts and notifications</div>
                <div class="feature">✅ Portfolio tracking</div>
                <div class="feature">✅ Historical data access</div>
                
                <button class="btn" onclick="alert('Payment integration coming soon!')">Upgrade Now</button>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666;">
                    <h3>Free Tier Limitations:</h3>
                    <ul>
                        <li>5 searches per day</li>
                        <li>Basic data only</li>
                        <li>Watermarked reports</li>
                        <li>Advertisement supported</li>
                        <li>No API access</li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "quick-analysis-portal",
        "timestamp": datetime.now().isoformat()
    })

# Add database schema updates
def update_db_schema():
    """Update database schema for new features"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Add API key column if not exists
    try:
        c.execute('ALTER TABLE users ADD COLUMN api_key TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add user alerts table
    c.execute('''CREATE TABLE IF NOT EXISTS user_alerts (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        symbol TEXT,
        alert_type TEXT,
        condition_type TEXT,
        value REAL,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

# Generate API key for premium users
def generate_api_key(user_id: str) -> str:
    """Generate unique API key for user"""
    import secrets
    api_key = f"qa_{secrets.token_urlsafe(32)}"
    
    # Store API key
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET api_key = ? WHERE id = ?', (api_key, user_id))
    conn.commit()
    conn.close()
    
    return api_key

# Import and add API routes
import importlib.util
import os

# Load API routes if file exists
api_routes_path = os.path.join(os.path.dirname(__file__), 'api_routes.py')
if os.path.exists(api_routes_path):
    spec = importlib.util.spec_from_file_location("api_routes", api_routes_path)
    api_routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_routes)

if __name__ == '__main__':
    init_db()
    update_db_schema()
    
    logger.info("🚀 Starting Quick Analysis Portal")
    logger.info("📍 Access via: http://localhost:8420")
    logger.info("🔗 Direct URL: analysis.activeledger.ai")
    logger.info("")
    logger.info("✨ Features Available:")
    logger.info("  📊 Real-time stock analysis")
    logger.info("  📱 Progressive Web App (PWA)")
    logger.info("  🔧 Browser extension support") 
    logger.info("  📲 Mobile widget")
    logger.info("  🔌 REST API endpoints")
    logger.info("  ⌨️  Keyboard shortcuts")
    logger.info("  💎 Free & Premium tiers")
    logger.info("  🎯 Easy bookmarking")
    logger.info("")
    logger.info("🔗 Quick Access Points:")
    logger.info("  • Main Portal: http://localhost:8420")
    logger.info("  • API Docs: http://localhost:8420/api/docs")
    logger.info("  • Mobile Widget: http://localhost:8420/mobile-widget")
    logger.info("  • Browser Extension: http://localhost:8420/extension")
    logger.info("  • Premium Upgrade: http://localhost:8420/premium")
    
    app.run(host='0.0.0.0', port=8420, debug=False)