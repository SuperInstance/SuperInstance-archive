"""
API Routes for Quick Analysis Portal
Comprehensive API endpoints for third-party integrations
"""

from flask import request, jsonify, render_template_string
from functools import wraps
import time
import jwt
from typing import Dict, List, Any, Optional

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                "error": "API key required",
                "message": "Include X-API-Key header or api_key parameter"
            }), 401
        
        # Get user session by API key
        user_session = user_manager.get_user_by_api_key(api_key)
        if not user_session:
            return jsonify({
                "error": "Invalid API key",
                "message": "API key not found or expired"
            }), 401
        
        # Check API rate limits
        if not user_manager.check_api_rate_limit(user_session):
            return jsonify({
                "error": "Rate limit exceeded",
                "message": "API rate limit exceeded for your tier"
            }), 429
        
        # Add user session to request context
        request.user_session = user_session
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/api/docs')
def api_docs():
    """API documentation page"""
    return render_template_string(API_DOCS_TEMPLATE)

@app.route('/api/v1/quote/<symbol>')
@require_api_key
def api_get_quote(symbol):
    """Get stock quote via API"""
    try:
        user_session = request.user_session
        
        # Log API usage
        user_manager.log_api_usage(user_session.user_id, '/api/v1/quote')
        
        # Get quote data
        quote_data = analysis_engine.get_stock_quote(symbol.upper())
        
        if quote_data.get('error'):
            return jsonify(quote_data), 404
        
        return jsonify({
            "success": True,
            "data": quote_data,
            "meta": {
                "symbol": symbol.upper(),
                "timestamp": time.time(),
                "tier": user_session.tier.value,
                "rate_limit": user_manager.get_rate_limit_info(user_session)
            }
        })
        
    except Exception as e:
        logger.error(f"API quote error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/api/v1/ratios/<symbol>')
@require_api_key
def api_get_ratios(symbol):
    """Get financial ratios via API"""
    try:
        user_session = request.user_session
        user_manager.log_api_usage(user_session.user_id, '/api/v1/ratios')
        
        ratios_data = analysis_engine.get_key_ratios(symbol.upper())
        
        if ratios_data.get('error'):
            return jsonify(ratios_data), 404
        
        return jsonify({
            "success": True,
            "data": ratios_data,
            "meta": {
                "symbol": symbol.upper(),
                "timestamp": time.time(),
                "tier": user_session.tier.value
            }
        })
        
    except Exception as e:
        logger.error(f"API ratios error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/v1/chart/<symbol>')
@require_api_key
def api_get_chart(symbol):
    """Get chart data via API"""
    try:
        user_session = request.user_session
        user_manager.log_api_usage(user_session.user_id, '/api/v1/chart')
        
        period = request.args.get('period', '1mo')
        chart_data = analysis_engine.get_chart_data(symbol.upper(), period)
        
        if chart_data.get('error'):
            return jsonify(chart_data), 404
        
        return jsonify({
            "success": True,
            "data": chart_data,
            "meta": {
                "symbol": symbol.upper(),
                "period": period,
                "timestamp": time.time(),
                "tier": user_session.tier.value
            }
        })
        
    except Exception as e:
        logger.error(f"API chart error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/v1/news/<symbol>')
@require_api_key
def api_get_news(symbol):
    """Get news via API"""
    try:
        user_session = request.user_session
        user_manager.log_api_usage(user_session.user_id, '/api/v1/news')
        
        limit = min(int(request.args.get('limit', 5)), 20)  # Max 20 articles
        news_data = analysis_engine.get_recent_news(symbol.upper(), limit)
        
        if news_data.get('error'):
            return jsonify(news_data), 404
        
        return jsonify({
            "success": True,
            "data": news_data,
            "meta": {
                "symbol": symbol.upper(),
                "limit": limit,
                "timestamp": time.time(),
                "tier": user_session.tier.value
            }
        })
        
    except Exception as e:
        logger.error(f"API news error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/v1/analysis/<symbol>')
@require_api_key
def api_get_full_analysis(symbol):
    """Get comprehensive analysis via API"""
    try:
        user_session = request.user_session
        user_manager.log_api_usage(user_session.user_id, '/api/v1/analysis')
        
        # Get all analysis data
        analysis_data = {
            "symbol": symbol.upper(),
            "quote": analysis_engine.get_stock_quote(symbol.upper()),
            "ratios": analysis_engine.get_key_ratios(symbol.upper()),
            "news": analysis_engine.get_recent_news(symbol.upper()),
            "analyst": analysis_engine.get_analyst_consensus(symbol.upper())
        }
        
        # Remove errors from successful calls
        for key, data in analysis_data.items():
            if isinstance(data, dict) and data.get('error'):
                analysis_data[key] = {"error": data.get('error')}
        
        return jsonify({
            "success": True,
            "data": analysis_data,
            "meta": {
                "symbol": symbol.upper(),
                "timestamp": time.time(),
                "tier": user_session.tier.value,
                "comprehensive": True
            }
        })
        
    except Exception as e:
        logger.error(f"API analysis error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/v1/batch', methods=['POST'])
@require_api_key
def api_batch_analysis():
    """Batch analysis for multiple symbols"""
    try:
        user_session = request.user_session
        
        # Premium feature check
        if user_session.tier == UserTier.FREE:
            return jsonify({
                "error": "Premium feature",
                "message": "Batch analysis requires Premium subscription"
            }), 403
        
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols or len(symbols) > 10:
            return jsonify({
                "error": "Invalid request",
                "message": "Provide 1-10 symbols in the 'symbols' array"
            }), 400
        
        user_manager.log_api_usage(user_session.user_id, '/api/v1/batch')
        
        results = {}
        for symbol in symbols:
            symbol = symbol.upper()
            results[symbol] = {
                "quote": analysis_engine.get_stock_quote(symbol),
                "ratios": analysis_engine.get_key_ratios(symbol)
            }
        
        return jsonify({
            "success": True,
            "data": results,
            "meta": {
                "symbols": symbols,
                "count": len(symbols),
                "timestamp": time.time(),
                "tier": user_session.tier.value
            }
        })
        
    except Exception as e:
        logger.error(f"API batch error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/v1/alerts', methods=['POST'])
@require_api_key
def api_create_alert():
    """Create price alert (Premium feature)"""
    try:
        user_session = request.user_session
        
        if user_session.tier == UserTier.FREE:
            return jsonify({
                "error": "Premium feature",
                "message": "Price alerts require Premium subscription"
            }), 403
        
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        alert_type = data.get('type', 'price')  # price, volume, etc.
        condition = data.get('condition', 'above')  # above, below
        value = data.get('value')
        
        if not symbol or not value:
            return jsonify({
                "error": "Invalid request",
                "message": "Symbol and value are required"
            }), 400
        
        # Store alert (simplified implementation)
        alert_id = str(uuid.uuid4())
        alert_data = {
            "id": alert_id,
            "user_id": user_session.user_id,
            "symbol": symbol,
            "type": alert_type,
            "condition": condition,
            "value": value,
            "created_at": time.time(),
            "active": True
        }
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO user_alerts (id, user_id, symbol, alert_type, condition_type, value, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (alert_id, user_session.user_id, symbol, alert_type, condition, value, datetime.now()))
        conn.commit()
        conn.close()
        
        user_manager.log_api_usage(user_session.user_id, '/api/v1/alerts')
        
        return jsonify({
            "success": True,
            "data": {
                "alert_id": alert_id,
                "message": f"Alert created for {symbol} when price goes {condition} ${value}"
            }
        })
        
    except Exception as e:
        logger.error(f"API alert error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/v1/user/usage')
@require_api_key
def api_user_usage():
    """Get user API usage statistics"""
    try:
        user_session = request.user_session
        
        # Get usage stats from database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Today's usage
        c.execute('''SELECT COUNT(*) FROM api_usage 
                     WHERE user_id = ? AND DATE(timestamp) = DATE('now')''',
                  (user_session.user_id,))
        today_usage = c.fetchone()[0]
        
        # Monthly usage
        c.execute('''SELECT COUNT(*) FROM api_usage 
                     WHERE user_id = ? AND DATE(timestamp) >= DATE('now', 'start of month')''',
                  (user_session.user_id,))
        monthly_usage = c.fetchone()[0]
        
        # Popular endpoints
        c.execute('''SELECT endpoint, COUNT(*) as count FROM api_usage 
                     WHERE user_id = ? AND DATE(timestamp) >= DATE('now', '-7 days')
                     GROUP BY endpoint ORDER BY count DESC LIMIT 5''',
                  (user_session.user_id,))
        popular_endpoints = [{"endpoint": row[0], "count": row[1]} for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "user_id": user_session.user_id,
                "tier": user_session.tier.value,
                "usage": {
                    "today": today_usage,
                    "this_month": monthly_usage,
                    "searches_today": user_session.searches_today
                },
                "limits": {
                    "daily_searches": 5 if user_session.tier == UserTier.FREE else "unlimited",
                    "api_calls_per_hour": user_manager.get_api_rate_limit(user_session.tier)
                },
                "popular_endpoints": popular_endpoints
            }
        })
        
    except Exception as e:
        logger.error(f"API usage error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/mobile-widget')
def mobile_widget():
    """Mobile widget page"""
    return render_template_string(MOBILE_WIDGET_TEMPLATE)

@app.route('/extension')
def extension_page():
    """Browser extension download page"""
    return render_template_string(EXTENSION_PAGE_TEMPLATE)

# Enhanced UserManager methods
def get_user_by_api_key(self, api_key: str) -> Optional[UserSession]:
    """Get user session by API key"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE api_key = ?', (api_key,))
    result = c.fetchone()
    conn.close()
    
    if result:
        columns = ['id', 'email', 'tier', 'api_key', 'searches_today', 
                  'searches_reset_date', 'premium_expires', 'created_at', 'last_login']
        user_data = dict(zip(columns, result))
        
        return UserSession(
            user_id=user_data['id'],
            tier=UserTier(user_data['tier']),
            searches_today=user_data['searches_today'],
            api_key=user_data['api_key'],
            premium_expires=datetime.fromisoformat(user_data['premium_expires']) if user_data['premium_expires'] else None
        )
    return None

def check_api_rate_limit(self, user_session: UserSession) -> bool:
    """Check API rate limit based on user tier"""
    if user_session.tier == UserTier.FREE:
        limit = 100  # 100 calls per hour
    elif user_session.tier == UserTier.PREMIUM:
        limit = 1000  # 1000 calls per hour
    else:
        limit = 10000  # 10000 calls per hour for enterprise
    
    # Check current hour usage
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM api_usage 
                 WHERE user_id = ? AND timestamp >= datetime('now', '-1 hour')''',
              (user_session.user_id,))
    current_usage = c.fetchone()[0]
    conn.close()
    
    return current_usage < limit

def log_api_usage(self, user_id: str, endpoint: str):
    """Log API usage"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO api_usage (user_id, endpoint) VALUES (?, ?)',
              (user_id, endpoint))
    conn.commit()
    conn.close()

def get_api_rate_limit(self, tier: UserTier) -> int:
    """Get API rate limit for tier"""
    limits = {
        UserTier.FREE: 100,
        UserTier.PREMIUM: 1000,
        UserTier.ENTERPRISE: 10000
    }
    return limits.get(tier, 100)

def get_rate_limit_info(self, user_session: UserSession) -> Dict[str, Any]:
    """Get rate limit information for user"""
    limit = self.get_api_rate_limit(user_session.tier)
    
    # Get current usage
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM api_usage 
                 WHERE user_id = ? AND timestamp >= datetime('now', '-1 hour')''',
              (user_session.user_id,))
    current_usage = c.fetchone()[0]
    conn.close()
    
    return {
        "limit": limit,
        "used": current_usage,
        "remaining": max(0, limit - current_usage),
        "reset_time": time.time() + 3600  # Next hour
    }

# Add methods to UserManager class
UserManager.get_user_by_api_key = get_user_by_api_key
UserManager.check_api_rate_limit = check_api_rate_limit
UserManager.log_api_usage = log_api_usage
UserManager.get_api_rate_limit = get_api_rate_limit
UserManager.get_rate_limit_info = get_rate_limit_info

# API Documentation Template
API_DOCS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quick Analysis Portal API Documentation</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f8fafc; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #1e40af; margin-bottom: 10px; }
        h2 { color: #1e40af; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 40px; }
        h3 { color: #374151; margin-top: 30px; }
        .endpoint { background: #f8fafc; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #1e40af; }
        .method { background: #1e40af; color: white; padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: 600; }
        .url { font-family: monospace; background: #e5e7eb; padding: 8px 12px; border-radius: 4px; margin: 10px 0; }
        .code { background: #1f2937; color: #f9fafb; padding: 20px; border-radius: 8px; overflow-x: auto; font-family: monospace; font-size: 14px; }
        .param { background: #fef3c7; padding: 15px; border-radius: 6px; margin: 10px 0; }
        .response { background: #d1fae5; padding: 15px; border-radius: 6px; margin: 10px 0; }
        .tier-badge { padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .free { background: #d1fae5; color: #065f46; }
        .premium { background: #dbeafe; color: #1e40af; }
        .enterprise { background: #f3e8ff; color: #7c3aed; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Quick Analysis Portal API</h1>
        <p>Integrate real-time financial analysis into your applications with our comprehensive API.</p>
        
        <h2>Authentication</h2>
        <p>All API requests require an API key. Include your key in the request header:</p>
        <div class="code">X-API-Key: YOUR_API_KEY</div>
        <p>Or as a query parameter:</p>
        <div class="code">?api_key=YOUR_API_KEY</div>
        
        <h2>Base URL</h2>
        <div class="url">https://analysis.activeledger.ai/api/v1</div>
        
        <h2>Rate Limits</h2>
        <ul>
            <li><span class="tier-badge free">Free</span> 100 calls/hour, 5 searches/day</li>
            <li><span class="tier-badge premium">Premium</span> 1,000 calls/hour, unlimited searches</li>
            <li><span class="tier-badge enterprise">Enterprise</span> 10,000 calls/hour, unlimited searches</li>
        </ul>
        
        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /quote/{symbol}</h3>
            <p>Get real-time stock quote for a symbol</p>
            <div class="param">
                <strong>Parameters:</strong><br>
                • <code>symbol</code> (path) - Stock symbol (e.g., AAPL, TSLA)
            </div>
            <div class="response">
                <strong>Response:</strong>
                <div class="code">{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "company_name": "Apple Inc.",
    "current_price": 150.25,
    "change": 2.15,
    "change_percent": 1.45,
    "volume": 45231890,
    "market_cap": 2456789000000,
    "pe_ratio": 24.5,
    "52_week_high": 180.95,
    "52_week_low": 124.17
  },
  "meta": {
    "timestamp": 1635789600,
    "tier": "premium"
  }
}</div>
            </div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /ratios/{symbol}</h3>
            <p>Get comprehensive financial ratios</p>
            <div class="response">
                <strong>Response includes:</strong> P/E ratio, P/B ratio, ROE, ROA, profit margin, debt-to-equity, etc.
            </div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /chart/{symbol}</h3>
            <p>Get historical price data for charting</p>
            <div class="param">
                <strong>Query Parameters:</strong><br>
                • <code>period</code> (optional) - Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            </div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /news/{symbol}</h3>
            <p>Get recent news articles for a symbol</p>
            <div class="param">
                <strong>Query Parameters:</strong><br>
                • <code>limit</code> (optional) - Number of articles (max 20)
            </div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /analysis/{symbol}</h3>
            <p>Get comprehensive analysis (quote + ratios + news + analyst consensus)</p>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">POST</span> /batch <span class="tier-badge premium">Premium</span></h3>
            <p>Analyze multiple symbols in one request</p>
            <div class="param">
                <strong>Request Body:</strong>
                <div class="code">{
  "symbols": ["AAPL", "TSLA", "MSFT"]
}</div>
            </div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">POST</span> /alerts <span class="tier-badge premium">Premium</span></h3>
            <p>Create price alerts</p>
            <div class="param">
                <strong>Request Body:</strong>
                <div class="code">{
  "symbol": "AAPL",
  "type": "price",
  "condition": "above",
  "value": 160.00
}</div>
            </div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /user/usage</h3>
            <p>Get your API usage statistics</p>
        </div>
        
        <h2>Example Integration</h2>
        <h3>JavaScript/Node.js</h3>
        <div class="code">const response = await fetch('https://analysis.activeledger.ai/api/v1/quote/AAPL', {
  headers: {
    'X-API-Key': 'your-api-key-here'
  }
});

const data = await response.json();
console.log(data.data.current_price);</div>
        
        <h3>Python</h3>
        <div class="code">import requests

headers = {'X-API-Key': 'your-api-key-here'}
response = requests.get('https://analysis.activeledger.ai/api/v1/quote/AAPL', headers=headers)
data = response.json()
print(data['data']['current_price'])</div>
        
        <h3>curl</h3>
        <div class="code">curl -H "X-API-Key: your-api-key-here" \\
     "https://analysis.activeledger.ai/api/v1/quote/AAPL"</div>
        
        <h2>Error Handling</h2>
        <p>The API returns appropriate HTTP status codes:</p>
        <ul>
            <li><strong>200</strong> - Success</li>
            <li><strong>401</strong> - Authentication required</li>
            <li><strong>403</strong> - Premium feature required</li>
            <li><strong>404</strong> - Symbol not found</li>
            <li><strong>429</strong> - Rate limit exceeded</li>
            <li><strong>500</strong> - Server error</li>
        </ul>
        
        <h2>Get API Key</h2>
        <p>To get your API key and start using the API:</p>
        <ol>
            <li><a href="/premium" style="color: #1e40af;">Upgrade to Premium</a></li>
            <li>Your API key will be generated automatically</li>
            <li>Start making API calls immediately</li>
        </ol>
        
        <div style="margin-top: 40px; padding: 20px; background: #f8fafc; border-radius: 8px; text-align: center;">
            <h3>Need Help?</h3>
            <p>Check out our <a href="/" style="color: #1e40af;">main portal</a> or contact support for integration assistance.</p>
        </div>
    </div>
</body>
</html>
"""

# Mobile Widget Template
MOBILE_WIDGET_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobile Widget - Quick Analysis Portal</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
        .container { max-width: 400px; margin: 0 auto; }
        .widget { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .header { text-align: center; margin-bottom: 20px; }
        .search-input { width: 100%; padding: 12px; border: 2px solid #e5e7eb; border-radius: 8px; font-size: 16px; outline: none; box-sizing: border-box; }
        .search-btn { width: 100%; padding: 12px; background: #1e40af; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 10px; }
        .quick-buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .quick-btn { padding: 10px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 6px; cursor: pointer; text-align: center; }
        .install-prompt { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; padding: 20px; text-align: center; }
        .install-btn { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; padding: 10px 20px; cursor: pointer; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="install-prompt">
            <h2>📱 Mobile Widget</h2>
            <p>Add Quick Analysis to your home screen for instant access</p>
            <button onclick="showInstallInstructions()" class="install-btn">
                Add to Home Screen
            </button>
        </div>
        
        <div class="widget">
            <div class="header">
                <h3>🚀 Quick Stock Analysis</h3>
            </div>
            
            <input type="text" 
                   id="symbolInput" 
                   class="search-input" 
                   placeholder="Enter stock symbol (e.g., AAPL)"
                   autocomplete="off">
            <button onclick="analyzeStock()" class="search-btn">Get Analysis</button>
            
            <div class="quick-buttons">
                <div onclick="quickAnalyze('AAPL')" class="quick-btn">AAPL</div>
                <div onclick="quickAnalyze('TSLA')" class="quick-btn">TSLA</div>
                <div onclick="quickAnalyze('MSFT')" class="quick-btn">MSFT</div>
                <div onclick="quickAnalyze('GOOGL')" class="quick-btn">GOOGL</div>
            </div>
        </div>
        
        <div class="widget" id="results" style="display: none;">
            <div id="resultsContent"></div>
        </div>
        
        <div class="widget">
            <h4>Widget Features</h4>
            <ul>
                <li>✅ Instant stock quotes</li>
                <li>✅ Real-time price changes</li>
                <li>✅ Key financial ratios</li>
                <li>✅ Recent news headlines</li>
                <li>✅ Works offline (cached data)</li>
                <li>✅ Fast, mobile-optimized</li>
            </ul>
        </div>
    </div>

    <script>
        function quickAnalyze(symbol) {
            document.getElementById('symbolInput').value = symbol;
            analyzeStock();
        }

        async function analyzeStock() {
            const symbol = document.getElementById('symbolInput').value.trim().toUpperCase();
            if (!symbol) return;

            const results = document.getElementById('results');
            const content = document.getElementById('resultsContent');
            
            results.style.display = 'block';
            content.innerHTML = '<div style="text-align: center; padding: 20px;">Loading...</div>';

            try {
                const response = await fetch('/api/quick-analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol: symbol })
                });

                const data = await response.json();
                
                if (data.error) {
                    content.innerHTML = `<div style="color: #ef4444; text-align: center;">${data.error}</div>`;
                    return;
                }

                const quote = data.quote;
                const changeClass = quote.change >= 0 ? 'positive' : 'negative';
                const changeColor = quote.change >= 0 ? '#10b981' : '#ef4444';
                const changeSymbol = quote.change >= 0 ? '+' : '';

                content.innerHTML = `
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h3 style="margin: 0 0 10px 0;">${quote.symbol}</h3>
                        <div style="font-size: 24px; font-weight: bold; color: #1e40af;">$${quote.current_price}</div>
                        <div style="color: ${changeColor}; font-weight: 600;">
                            ${changeSymbol}${quote.change} (${changeSymbol}${quote.change_percent.toFixed(2)}%)
                        </div>
                        <div style="color: #666; font-size: 14px; margin-top: 5px;">${quote.company_name}</div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; font-size: 14px;">
                        <div>
                            <div style="color: #666;">Volume</div>
                            <div style="font-weight: 600;">${quote.volume ? quote.volume.toLocaleString() : 'N/A'}</div>
                        </div>
                        <div>
                            <div style="color: #666;">P/E Ratio</div>
                            <div style="font-weight: 600;">${quote.pe_ratio || 'N/A'}</div>
                        </div>
                        <div>
                            <div style="color: #666;">Market Cap</div>
                            <div style="font-weight: 600;">${quote.market_cap ? '$' + (quote.market_cap/1e9).toFixed(1) + 'B' : 'N/A'}</div>
                        </div>
                        <div>
                            <div style="color: #666;">52W Range</div>
                            <div style="font-weight: 600;">$${quote['52_week_low']} - $${quote['52_week_high']}</div>
                        </div>
                    </div>
                `;
                
            } catch (error) {
                content.innerHTML = '<div style="color: #ef4444; text-align: center;">Failed to fetch data</div>';
            }
        }

        function showInstallInstructions() {
            const instructions = `
To add this widget to your home screen:

iOS Safari:
1. Tap the Share button
2. Tap "Add to Home Screen"
3. Tap "Add"

Android Chrome:
1. Tap the menu (⋮)
2. Tap "Add to Home screen"
3. Tap "Add"

The widget will work like a native app!
            `;
            alert(instructions);
        }

        // Auto-focus search input
        document.getElementById('symbolInput').focus();
        
        // Handle Enter key
        document.getElementById('symbolInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                analyzeStock();
            }
        });
    </script>
</body>
</html>
"""

# Extension Page Template
EXTENSION_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Browser Extension - Quick Analysis Portal</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #1e40af; text-align: center; }
        .feature { display: flex; align-items: center; margin: 20px 0; padding: 20px; background: #f8fafc; border-radius: 8px; }
        .feature-icon { font-size: 2rem; margin-right: 20px; }
        .download-btn { background: #1e40af; color: white; padding: 15px 30px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; margin: 10px; }
        .screenshot { width: 100%; border-radius: 8px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Quick Analysis Browser Extension</h1>
        <p style="text-align: center; font-size: 18px; color: #666;">Analyze any stock symbol with a simple right-click</p>
        
        <div class="feature">
            <div class="feature-icon">🖱️</div>
            <div>
                <h3>Right-Click Analysis</h3>
                <p>Select any stock symbol on any webpage and right-click for instant analysis</p>
            </div>
        </div>
        
        <div class="feature">
            <div class="feature-icon">⚡</div>
            <div>
                <h3>Instant Results</h3>
                <p>Get real-time quotes, price changes, and key metrics in a beautiful overlay</p>
            </div>
        </div>
        
        <div class="feature">
            <div class="feature-icon">🎯</div>
            <div>
                <h3>Smart Detection</h3>
                <p>Automatically enhances financial websites with quick analysis buttons</p>
            </div>
        </div>
        
        <div class="feature">
            <div class="feature-icon">⌨️</div>
            <div>
                <h3>Keyboard Shortcuts</h3>
                <p>Ctrl+Shift+A to open portal, Ctrl+Shift+S for quick search</p>
            </div>
        </div>
        
        <div style="text-align: center; margin: 40px 0;">
            <h2>Download Extension</h2>
            <a href="/static/extension/quick-analysis-extension.zip" class="download-btn" download>
                📥 Download for Chrome
            </a>
            <a href="/static/extension/quick-analysis-extension.zip" class="download-btn" download>
                📥 Download for Firefox
            </a>
        </div>
        
        <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>Installation Instructions</h3>
            <ol>
                <li>Download the extension file</li>
                <li>Open Chrome and go to chrome://extensions/</li>
                <li>Enable "Developer mode" in the top right</li>
                <li>Click "Load unpacked" and select the extracted folder</li>
                <li>The extension is now installed and ready to use!</li>
            </ol>
        </div>
        
        <div style="text-align: center; margin-top: 40px;">
            <h3>Try it now!</h3>
            <p>Select this text: <strong>AAPL</strong> and right-click to see the extension in action</p>
        </div>
    </div>
</body>
</html>
"""