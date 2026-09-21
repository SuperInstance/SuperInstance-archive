"""
Quick Analysis Portal - Simple Version (OpenSSL compatible)
Direct URL: analysis.activeledger.ai
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from dataclasses import dataclass
from enum import Enum
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change in production
CORS(app)

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
    
    conn.commit()
    conn.close()

class SimpleAnalysisEngine:
    """Simplified analysis engine using basic requests"""
    
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get basic stock quote using a simple API or mock data"""
        try:
            # Mock data for demonstration (replace with real API)
            mock_data = {
                "AAPL": {"price": 150.25, "change": 2.15, "volume": 45231890, "pe": 24.5},
                "TSLA": {"price": 245.67, "change": -3.45, "volume": 32145670, "pe": 45.2},
                "MSFT": {"price": 378.92, "change": 1.85, "volume": 28456789, "pe": 28.9},
                "GOOGL": {"price": 135.48, "change": 0.95, "volume": 19876543, "pe": 25.1}
            }
            
            if symbol.upper() in mock_data:
                data = mock_data[symbol.upper()]
                change_percent = (data["change"] / (data["price"] - data["change"])) * 100
                
                return {
                    "symbol": symbol.upper(),
                    "company_name": f"{symbol.upper()} Corporation",
                    "current_price": data["price"],
                    "change": data["change"],
                    "change_percent": change_percent,
                    "volume": data["volume"],
                    "market_cap": data["price"] * 1000000000,  # Mock market cap
                    "pe_ratio": data["pe"],
                    "52_week_high": data["price"] * 1.2,
                    "52_week_low": data["price"] * 0.8,
                    "updated_at": datetime.now().isoformat()
                }
            else:
                return {"error": "Symbol not found"}
                
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {"error": f"Failed to fetch data for {symbol}"}
    
    def get_key_ratios(self, symbol: str) -> Dict[str, Any]:
        """Get mock key financial ratios"""
        try:
            # Mock ratio data
            return {
                "symbol": symbol.upper(),
                "pe_ratio": 24.5,
                "forward_pe": 22.1,
                "peg_ratio": 1.2,
                "price_to_book": 6.8,
                "price_to_sales": 7.2,
                "debt_to_equity": 1.8,
                "return_on_equity": 0.15,
                "return_on_assets": 0.08,
                "profit_margin": 0.25,
                "operating_margin": 0.30,
                "dividend_yield": 0.005,
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching ratios for {symbol}: {e}")
            return {"error": f"Failed to fetch ratios for {symbol}"}
    
    def get_recent_news(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Get mock recent news"""
        try:
            news_items = [
                {
                    "title": f"{symbol.upper()} Reports Strong Quarterly Earnings",
                    "publisher": "Financial News Today",
                    "link": "https://example.com/news1",
                    "publish_time": datetime.now().isoformat(),
                    "summary": f"Latest earnings report shows {symbol.upper()} beating analyst expectations..."
                },
                {
                    "title": f"Market Analysis: {symbol.upper()} Stock Outlook",
                    "publisher": "Market Watch",
                    "link": "https://example.com/news2", 
                    "publish_time": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "summary": f"Analysts remain bullish on {symbol.upper()} following recent developments..."
                }
            ]
            
            return {
                "symbol": symbol.upper(),
                "news": news_items[:limit],
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return {"error": f"Failed to fetch news for {symbol}"}
    
    def get_analyst_consensus(self, symbol: str) -> Dict[str, Any]:
        """Get mock analyst consensus data"""
        try:
            current_price = 150.0  # Mock current price
            return {
                "symbol": symbol.upper(),
                "target_mean_price": current_price * 1.15,
                "target_high_price": current_price * 1.30,
                "target_low_price": current_price * 1.05,
                "recommendation_mean": 2.1,
                "recommendation_key": "Buy",
                "number_of_analyst_opinions": 25,
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching analyst data for {symbol}: {e}")
            return {"error": f"Failed to fetch analyst data for {symbol}"}

class UserManager:
    """Manage user sessions and tiers"""
    
    def __init__(self):
        self.sessions = {}
    
    def get_or_create_user(self, session_id: str, email: str = None) -> UserSession:
        """Get existing user or create anonymous user"""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
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
            return user_session.searches_today < 5
        elif user_session.tier == UserTier.PREMIUM:
            return True  # Unlimited searches
        else:
            return True  # Enterprise
    
    def increment_search_count(self, user_session: UserSession):
        """Increment user's search count"""
        user_session.searches_today += 1
        self._update_search_count(user_session.user_id, user_session.searches_today)
    
    def _create_user(self, user_id: str, email: str = None):
        """Create new user in database"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO users (id, email, searches_reset_date) 
                     VALUES (?, ?, ?)''', 
                  (user_id, email, datetime.now().strftime('%Y-%m-%d')))
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
analysis_engine = SimpleAnalysisEngine()
user_manager = UserManager()

# HTML Template
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quick Analysis Portal - ActiveLedger.ai</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1e40af">
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
            cursor: pointer;
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
            <div class="access-card" onclick="alert('PWA: Add this page to your home screen!')">
                <h3>📱 Install PWA</h3>
                <p>Add to home screen for instant access</p>
            </div>
            <div class="access-card" onclick="alert('Extension: Coming soon!')">
                <h3>🔧 Browser Extension</h3>
                <p>Right-click any stock ticker for analysis</p>
            </div>
            <div class="access-card" onclick="window.open('/api-docs', '_blank')">
                <h3>🔌 API Access</h3>
                <p>Integrate with your apps and tools</p>
            </div>
            <div class="access-card" onclick="window.open('/mobile-widget', '_blank')">
                <h3>📲 Mobile Widget</h3>
                <p>Quick access from your mobile device</p>
            </div>
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
        });

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
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def home():
    """Main portal page"""
    searches_left = 5  # Default for demonstration
    return render_template_string(MAIN_TEMPLATE, searches_left=searches_left)

@app.route('/api/quick-analysis', methods=['POST'])
def quick_analysis():
    """Quick analysis endpoint"""
    data = request.get_json()
    symbol = data.get('symbol', '').strip().upper()
    
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    
    try:
        # Get analysis data
        results = {
            "symbol": symbol,
            "quote": analysis_engine.get_stock_quote(symbol),
            "ratios": analysis_engine.get_key_ratios(symbol),
            "news": analysis_engine.get_recent_news(symbol),
            "analyst": analysis_engine.get_analyst_consensus(symbol),
            "tier": "free",
            "searches_remaining": 4  # Mock remaining searches
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
                
                <button class="btn" onclick="alert('Payment integration coming soon!')">Upgrade Now</button>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/api-docs')
def api_docs():
    """Simple API documentation"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Documentation - Quick Analysis Portal</title>
        <style>
            body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f8fafc; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; }
            h1 { color: #1e40af; }
            .endpoint { background: #f8fafc; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #1e40af; }
            .method { background: #1e40af; color: white; padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: 600; }
            .code { background: #1f2937; color: #f9fafb; padding: 20px; border-radius: 8px; overflow-x: auto; font-family: monospace; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Quick Analysis Portal API</h1>
            <p>Simple API for financial analysis integration</p>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> /api/quick-analysis</h3>
                <p>Get comprehensive stock analysis</p>
                <div class="code">{
  "symbol": "AAPL"
}</div>
                <p><strong>Response:</strong> Complete analysis including quote, ratios, news, and analyst data</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /manifest.json</h3>
                <p>PWA manifest for mobile installation</p>
            </div>
            
            <p><strong>Note:</strong> Full API documentation with authentication will be available in the complete version.</p>
        </div>
    </body>
    </html>
    """)

@app.route('/mobile-widget')
def mobile_widget():
    """Simple mobile widget page"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mobile Widget - Quick Analysis Portal</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
            .widget { background: white; border-radius: 12px; padding: 20px; max-width: 400px; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .search-input { width: 100%; padding: 12px; border: 2px solid #e5e7eb; border-radius: 8px; font-size: 16px; outline: none; box-sizing: border-box; }
            .search-btn { width: 100%; padding: 12px; background: #1e40af; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="widget">
            <h2>📱 Mobile Quick Analysis</h2>
            <input type="text" class="search-input" placeholder="Enter stock symbol" id="mobileInput">
            <button class="search-btn" onclick="mobileSearch()">Analyze Stock</button>
            <div id="mobileResults" style="margin-top: 20px;"></div>
        </div>
        
        <script>
            async function mobileSearch() {
                const symbol = document.getElementById('mobileInput').value;
                if (!symbol) return;
                
                try {
                    const response = await fetch('/api/quick-analysis', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ symbol: symbol })
                    });
                    
                    const data = await response.json();
                    const results = document.getElementById('mobileResults');
                    
                    if (data.error) {
                        results.innerHTML = `<p style="color: red;">${data.error}</p>`;
                    } else {
                        const quote = data.quote;
                        results.innerHTML = `
                            <h3>${quote.symbol}</h3>
                            <p><strong>Price:</strong> $${quote.current_price}</p>
                            <p><strong>Change:</strong> ${quote.change} (${quote.change_percent.toFixed(2)}%)</p>
                            <p><strong>Volume:</strong> ${quote.volume.toLocaleString()}</p>
                        `;
                    }
                } catch (error) {
                    document.getElementById('mobileResults').innerHTML = '<p style="color: red;">Failed to fetch data</p>';
                }
            }
            
            document.getElementById('mobileInput').addEventListener('keydown', (e) => {
                if (e.key === 'Enter') mobileSearch();
            });
        </script>
    </body>
    </html>
    """)

@app.route('/extension')
def browser_extension():
    """Browser extension download page"""
    extension_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Browser Extension - Quick Analysis Portal</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 40px; }
            .extension-card { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 30px; margin-bottom: 20px; backdrop-filter: blur(10px); }
            .download-btn { display: inline-block; background: #4CAF50; color: white; padding: 15px 30px; border-radius: 25px; text-decoration: none; font-weight: bold; margin: 10px; transition: all 0.3s; }
            .download-btn:hover { background: #45a049; transform: translateY(-2px); }
            .instructions { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 20px; margin: 20px 0; }
            .step { margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧩 Browser Extension</h1>
                <p>Right-click any stock symbol for instant analysis</p>
            </div>
            
            <div class="extension-card">
                <h2>Download Extension</h2>
                <p>Add Quick Analysis Portal to your browser for easy access to financial analysis on any webpage.</p>
                
                <a href="/browser-extension/quick-analysis-chrome.zip" class="download-btn" download>
                    📥 Download for Chrome
                </a>
                
                <a href="/browser-extension/quick-analysis-firefox.zip" class="download-btn" download>
                    📥 Download for Firefox
                </a>
            </div>
            
            <div class="instructions">
                <h3>Installation Instructions</h3>
                
                <div class="step">
                    <h4>Chrome Installation:</h4>
                    <ol>
                        <li>Download the Chrome extension file</li>
                        <li>Open Chrome and go to chrome://extensions/</li>
                        <li>Enable "Developer mode" (toggle in top right)</li>
                        <li>Click "Load unpacked" and select the extracted folder</li>
                        <li>Extension is now ready!</li>
                    </ol>
                </div>
                
                <div class="step">
                    <h4>Firefox Installation:</h4>
                    <ol>
                        <li>Download the Firefox extension file</li>
                        <li>Open Firefox and go to about:debugging</li>
                        <li>Click "This Firefox"</li>
                        <li>Click "Load Temporary Add-on"</li>
                        <li>Select the manifest.json file</li>
                    </ol>
                </div>
                
                <div class="step">
                    <h4>How to Use:</h4>
                    <ul>
                        <li>Right-click any stock symbol (AAPL, TSLA, etc.) on any webpage</li>
                        <li>Select "Analyze with Quick Analysis Portal"</li>
                        <li>View instant stock analysis in a popup overlay</li>
                        <li>Use keyboard shortcut: Ctrl+Shift+A</li>
                    </ul>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="/" style="color: white; text-decoration: none;">← Back to Portal</a>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(extension_template)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "quick-analysis-portal-simple",
        "timestamp": datetime.now().isoformat(),
        "features": ["stock_analysis", "pwa", "mobile_widget", "api", "browser_extension"]
    })

if __name__ == '__main__':
    init_db()
    
    logger.info("🚀 Starting Quick Analysis Portal (Simple Version)")
    logger.info("📍 Access via: http://localhost:8420")
    logger.info("🔗 Direct URL: analysis.activeledger.ai")
    logger.info("")
    logger.info("✨ Features Available:")
    logger.info("  📊 Stock analysis (mock data)")
    logger.info("  📱 Progressive Web App (PWA)")
    logger.info("  📲 Mobile widget")
    logger.info("  🔌 Basic API endpoints")
    logger.info("  ⌨️  Keyboard shortcuts")
    logger.info("  💎 Free tier demonstration")
    logger.info("")
    logger.info("🔗 Quick Access Points:")
    logger.info("  • Main Portal: http://localhost:8420")
    logger.info("  • API Docs: http://localhost:8420/api-docs")
    logger.info("  • Mobile Widget: http://localhost:8420/mobile-widget")
    logger.info("  • Premium Info: http://localhost:8420/premium")
    logger.info("  • Health Check: http://localhost:8420/health")
    
    app.run(host='0.0.0.0', port=8420, debug=False)