"""
Market Analysis Platform - Demo Version (Simplified)
Basic version without heavy dependencies for demonstration
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from decimal import Decimal
import uvicorn
import json
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Market Analysis Platform - Demo",
    description="Simplified demo version of world-class financial analysis platform",
    version="1.0.0-demo"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo data models
class SecurityData(BaseModel):
    symbol: str
    name: str
    current_price: Decimal
    currency: str = "USD"
    market_cap: Optional[Decimal] = None
    sector: Optional[str] = None

class FundamentalAnalysisDemo(BaseModel):
    symbol: str
    pe_ratio: Optional[Decimal] = None
    pb_ratio: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    revenue_growth: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    analysis_summary: str

class TechnicalAnalysisDemo(BaseModel):
    symbol: str
    rsi: Optional[Decimal] = None
    macd_signal: str
    moving_avg_trend: str
    support_level: Optional[Decimal] = None
    resistance_level: Optional[Decimal] = None
    analysis_summary: str

class ComprehensiveAnalysisResponse(BaseModel):
    symbol: str
    security_data: Optional[SecurityData] = None
    fundamental_analysis: Optional[FundamentalAnalysisDemo] = None
    technical_analysis: Optional[TechnicalAnalysisDemo] = None
    overall_recommendation: str
    confidence_score: Decimal
    analysis_timestamp: datetime

# Demo data
DEMO_STOCKS = {
    "AAPL": {
        "name": "Apple Inc.",
        "price": 175.25,
        "market_cap": 2800000000000,
        "sector": "Technology",
        "pe_ratio": 28.5,
        "pb_ratio": 42.1,
        "revenue_growth": 8.2,
        "profit_margin": 23.4
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "price": 420.50,
        "market_cap": 3100000000000,
        "sector": "Technology",
        "pe_ratio": 32.1,
        "pb_ratio": 12.8,
        "revenue_growth": 12.1,
        "profit_margin": 36.2
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "price": 142.85,
        "market_cap": 1800000000000,
        "sector": "Technology",
        "pe_ratio": 26.3,
        "pb_ratio": 6.2,
        "revenue_growth": 6.8,
        "profit_margin": 21.1
    },
    "TSLA": {
        "name": "Tesla, Inc.",
        "price": 248.75,
        "market_cap": 790000000000,
        "sector": "Consumer Discretionary",
        "pe_ratio": 78.4,
        "pb_ratio": 9.8,
        "revenue_growth": 19.3,
        "profit_margin": 8.4
    }
}

def generate_demo_technical_analysis(symbol: str) -> TechnicalAnalysisDemo:
    """Generate demo technical analysis data"""
    import random
    random.seed(hash(symbol) % 1000)  # Consistent random data per symbol
    
    rsi = Decimal(str(round(30 + random.random() * 40, 1)))
    
    macd_signals = ["BUY", "SELL", "NEUTRAL"]
    macd_signal = random.choice(macd_signals)
    
    trends = ["BULLISH", "BEARISH", "SIDEWAYS"]
    trend = random.choice(trends)
    
    if symbol in DEMO_STOCKS:
        price = DEMO_STOCKS[symbol]["price"]
        support = Decimal(str(round(price * (0.9 + random.random() * 0.05), 2)))
        resistance = Decimal(str(round(price * (1.05 + random.random() * 0.05), 2)))
    else:
        support = Decimal("100.00")
        resistance = Decimal("120.00")
    
    # Generate analysis summary
    summary = f"Technical outlook for {symbol}: "
    if rsi < 30:
        summary += "RSI indicates oversold conditions. "
    elif rsi > 70:
        summary += "RSI indicates overbought conditions. "
    else:
        summary += "RSI in normal range. "
    
    summary += f"MACD shows {macd_signal} signal. "
    summary += f"Overall trend is {trend}. "
    summary += f"Key support at ${support}, resistance at ${resistance}."
    
    return TechnicalAnalysisDemo(
        symbol=symbol,
        rsi=rsi,
        macd_signal=macd_signal,
        moving_avg_trend=trend,
        support_level=support,
        resistance_level=resistance,
        analysis_summary=summary
    )

def generate_demo_fundamental_analysis(symbol: str) -> FundamentalAnalysisDemo:
    """Generate demo fundamental analysis data"""
    if symbol in DEMO_STOCKS:
        stock_data = DEMO_STOCKS[symbol]
        
        pe_ratio = Decimal(str(stock_data["pe_ratio"]))
        pb_ratio = Decimal(str(stock_data["pb_ratio"]))
        market_cap = Decimal(str(stock_data["market_cap"]))
        revenue_growth = Decimal(str(stock_data["revenue_growth"]))
        profit_margin = Decimal(str(stock_data["profit_margin"]))
        
        # Generate analysis summary
        summary = f"Fundamental analysis for {symbol}: "
        
        if pe_ratio < 20:
            summary += "Attractively valued with P/E below 20. "
        elif pe_ratio > 40:
            summary += "Premium valuation with high P/E ratio. "
        else:
            summary += "Fairly valued. "
        
        if revenue_growth > 10:
            summary += "Strong revenue growth. "
        elif revenue_growth < 5:
            summary += "Modest revenue growth. "
        else:
            summary += "Healthy revenue growth. "
        
        if profit_margin > 20:
            summary += "Excellent profit margins. "
        elif profit_margin < 10:
            summary += "Tight profit margins. "
        else:
            summary += "Solid profit margins. "
        
        return FundamentalAnalysisDemo(
            symbol=symbol,
            pe_ratio=pe_ratio,
            pb_ratio=pb_ratio,
            market_cap=market_cap,
            revenue_growth=revenue_growth,
            profit_margin=profit_margin,
            analysis_summary=summary
        )
    else:
        return FundamentalAnalysisDemo(
            symbol=symbol,
            analysis_summary=f"Demo data not available for {symbol}. In production, this would contain comprehensive fundamental metrics."
        )

def generate_demo_security_data(symbol: str) -> SecurityData:
    """Generate demo security data"""
    if symbol in DEMO_STOCKS:
        stock_data = DEMO_STOCKS[symbol]
        return SecurityData(
            symbol=symbol,
            name=stock_data["name"],
            current_price=Decimal(str(stock_data["price"])),
            market_cap=Decimal(str(stock_data["market_cap"])),
            sector=stock_data["sector"]
        )
    else:
        return SecurityData(
            symbol=symbol,
            name=f"{symbol} Corporation",
            current_price=Decimal("100.00")
        )

# Root endpoint with dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard for the market analysis platform demo"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Market Analysis Platform - Demo</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                font-weight: 300;
            }
            
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            
            .demo-badge {
                background: rgba(255,255,255,0.2);
                color: #fff;
                padding: 8px 15px;
                border-radius: 20px;
                display: inline-block;
                margin-top: 15px;
                font-size: 0.9em;
                font-weight: bold;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                padding: 40px;
            }
            
            .feature {
                background: #f8f9fa;
                padding: 30px;
                border-radius: 10px;
                border-left: 4px solid #667eea;
                transition: transform 0.3s ease;
            }
            
            .feature:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            }
            
            .feature h3 {
                color: #2c3e50;
                margin-bottom: 15px;
                font-size: 1.4em;
            }
            
            .feature p {
                color: #666;
                line-height: 1.6;
            }
            
            .demo-section {
                padding: 40px;
                background: #f8f9fa;
            }
            
            .demo-section h2 {
                text-align: center;
                margin-bottom: 30px;
                color: #2c3e50;
            }
            
            .demo-form {
                max-width: 600px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            .form-group input, .form-group select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e1e8ed;
                border-radius: 6px;
                font-size: 16px;
                transition: border-color 0.3s ease;
            }
            
            .form-group input:focus, .form-group select:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .analyze-btn {
                width: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.3s ease;
            }
            
            .analyze-btn:hover {
                transform: translateY(-2px);
            }
            
            .analyze-btn:disabled {
                opacity: 0.7;
                cursor: not-allowed;
                transform: none;
            }
            
            .results {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 6px;
                display: none;
            }
            
            .results h3 {
                color: #2c3e50;
                margin-bottom: 15px;
            }
            
            .analysis-card {
                background: white;
                padding: 20px;
                margin-bottom: 15px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            
            .analysis-card h4 {
                color: #1e3c72;
                margin-bottom: 10px;
            }
            
            .metric {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                padding: 4px 0;
                border-bottom: 1px solid #eee;
            }
            
            .metric:last-child {
                border-bottom: none;
            }
            
            .metric-label {
                font-weight: bold;
                color: #555;
            }
            
            .metric-value {
                color: #2c3e50;
            }
            
            .recommendation {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                margin-top: 15px;
            }
            
            .recommendation.sell {
                background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
            }
            
            .recommendation.hold {
                background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
            }
            
            .loading {
                text-align: center;
                padding: 20px;
                display: none;
            }
            
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 2s linear infinite;
                margin: 0 auto 20px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .sample-symbols {
                display: flex;
                gap: 10px;
                margin-top: 10px;
                flex-wrap: wrap;
            }
            
            .symbol-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 5px 12px;
                border-radius: 15px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.3s ease;
            }
            
            .symbol-btn:hover {
                background: #5a67d8;
            }
            
            .api-note {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin-top: 20px;
                border-radius: 4px;
            }
            
            .api-note h4 {
                color: #1976d2;
                margin-bottom: 8px;
            }
            
            .api-note p {
                color: #555;
                margin: 0;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Market Analysis Platform</h1>
                <p>World-class financial analysis with AI-powered insights</p>
                <div class="demo-badge">DEMO VERSION</div>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>📊 Fundamental Analysis</h3>
                    <p>Complete fundamental analysis including P/E ratios, growth metrics, profitability analysis, and financial health scoring. Covers valuation, growth, and quality factors.</p>
                </div>
                
                <div class="feature">
                    <h3>📈 Technical Analysis</h3>
                    <p>Advanced technical analysis with 100+ indicators, pattern recognition, support/resistance levels, and trend analysis. Includes momentum and volatility indicators.</p>
                </div>
                
                <div class="feature">
                    <h3>🤖 AI-Powered Insights</h3>
                    <p>Machine learning models for sentiment analysis, price predictions, risk assessment, and market regime detection. Advanced portfolio optimization algorithms.</p>
                </div>
                
                <div class="feature">
                    <h3>🏢 Company Deep Dive</h3>
                    <p>Comprehensive company analysis including business model evaluation, competitive positioning, ESG scoring, and strategic assessment.</p>
                </div>
            </div>
            
            <div class="demo-section">
                <h2>Try Live Demo Analysis</h2>
                <div class="demo-form">
                    <div class="form-group">
                        <label for="symbol">Stock Symbol</label>
                        <input type="text" id="symbol" placeholder="Enter stock symbol (e.g., AAPL)" value="AAPL">
                        <div class="sample-symbols">
                            <button class="symbol-btn" onclick="setSymbol('AAPL')">AAPL</button>
                            <button class="symbol-btn" onclick="setSymbol('MSFT')">MSFT</button>
                            <button class="symbol-btn" onclick="setSymbol('GOOGL')">GOOGL</button>
                            <button class="symbol-btn" onclick="setSymbol('TSLA')">TSLA</button>
                            <button class="symbol-btn" onclick="setSymbol('NVDA')">NVDA</button>
                        </div>
                    </div>
                    
                    <button class="analyze-btn" onclick="performAnalysis()" id="analyzeBtn">
                        Analyze Stock 🔍
                    </button>
                    
                    <div class="loading" id="loading">
                        <div class="spinner"></div>
                        <p>Analyzing... Please wait</p>
                    </div>
                    
                    <div class="results" id="results">
                        <h3>Analysis Results</h3>
                        <div id="analysisContent"></div>
                    </div>
                    
                    <div class="api-note">
                        <h4>🔗 API Access</h4>
                        <p>This demo shows sample data. The full production version includes real-time data integration with multiple financial APIs, comprehensive technical indicators, and AI-powered predictions.</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function setSymbol(symbol) {
                document.getElementById('symbol').value = symbol;
            }
            
            async function performAnalysis() {
                const symbol = document.getElementById('symbol').value.toUpperCase().trim();
                
                if (!symbol) {
                    alert('Please enter a stock symbol');
                    return;
                }
                
                const loadingDiv = document.getElementById('loading');
                const resultsDiv = document.getElementById('results');
                const analysisContent = document.getElementById('analysisContent');
                const analyzeBtn = document.getElementById('analyzeBtn');
                
                // Show loading
                loadingDiv.style.display = 'block';
                resultsDiv.style.display = 'none';
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = 'Analyzing...';
                
                try {
                    const response = await fetch(`/api/analyze/${symbol}`);
                    const data = await response.json();
                    
                    if (response.ok) {
                        displayAnalysis(data);
                    } else {
                        throw new Error(data.detail || 'Analysis failed');
                    }
                    
                } catch (error) {
                    analysisContent.innerHTML = `
                        <div class="analysis-card">
                            <h4 style="color: #dc3545;">❌ Error</h4>
                            <p>${error.message}</p>
                        </div>
                    `;
                }
                
                // Show results and hide loading
                resultsDiv.style.display = 'block';
                loadingDiv.style.display = 'none';
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = 'Analyze Stock 🔍';
            }
            
            function displayAnalysis(data) {
                const analysisContent = document.getElementById('analysisContent');
                
                let html = '';
                
                // Security Data
                if (data.security_data) {
                    const security = data.security_data;
                    html += `
                        <div class="analysis-card">
                            <h4>📊 Security Information</h4>
                            <div class="metric">
                                <span class="metric-label">Company:</span>
                                <span class="metric-value">${security.name}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Current Price:</span>
                                <span class="metric-value">$${parseFloat(security.current_price).toFixed(2)}</span>
                            </div>
                            ${security.market_cap ? `
                                <div class="metric">
                                    <span class="metric-label">Market Cap:</span>
                                    <span class="metric-value">$${(parseFloat(security.market_cap) / 1e9).toFixed(1)}B</span>
                                </div>
                            ` : ''}
                            ${security.sector ? `
                                <div class="metric">
                                    <span class="metric-label">Sector:</span>
                                    <span class="metric-value">${security.sector}</span>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }
                
                // Fundamental Analysis
                if (data.fundamental_analysis) {
                    const fundamental = data.fundamental_analysis;
                    html += `
                        <div class="analysis-card">
                            <h4>📈 Fundamental Analysis</h4>
                            ${fundamental.pe_ratio ? `
                                <div class="metric">
                                    <span class="metric-label">P/E Ratio:</span>
                                    <span class="metric-value">${parseFloat(fundamental.pe_ratio).toFixed(1)}</span>
                                </div>
                            ` : ''}
                            ${fundamental.pb_ratio ? `
                                <div class="metric">
                                    <span class="metric-label">P/B Ratio:</span>
                                    <span class="metric-value">${parseFloat(fundamental.pb_ratio).toFixed(1)}</span>
                                </div>
                            ` : ''}
                            ${fundamental.revenue_growth ? `
                                <div class="metric">
                                    <span class="metric-label">Revenue Growth:</span>
                                    <span class="metric-value">${parseFloat(fundamental.revenue_growth).toFixed(1)}%</span>
                                </div>
                            ` : ''}
                            ${fundamental.profit_margin ? `
                                <div class="metric">
                                    <span class="metric-label">Profit Margin:</span>
                                    <span class="metric-value">${parseFloat(fundamental.profit_margin).toFixed(1)}%</span>
                                </div>
                            ` : ''}
                            <p style="margin-top: 15px; font-style: italic; color: #666;">
                                ${fundamental.analysis_summary}
                            </p>
                        </div>
                    `;
                }
                
                // Technical Analysis
                if (data.technical_analysis) {
                    const technical = data.technical_analysis;
                    html += `
                        <div class="analysis-card">
                            <h4>📊 Technical Analysis</h4>
                            ${technical.rsi ? `
                                <div class="metric">
                                    <span class="metric-label">RSI:</span>
                                    <span class="metric-value">${parseFloat(technical.rsi).toFixed(1)}</span>
                                </div>
                            ` : ''}
                            <div class="metric">
                                <span class="metric-label">MACD Signal:</span>
                                <span class="metric-value">${technical.macd_signal}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Trend:</span>
                                <span class="metric-value">${technical.moving_avg_trend}</span>
                            </div>
                            ${technical.support_level ? `
                                <div class="metric">
                                    <span class="metric-label">Support Level:</span>
                                    <span class="metric-value">$${parseFloat(technical.support_level).toFixed(2)}</span>
                                </div>
                            ` : ''}
                            ${technical.resistance_level ? `
                                <div class="metric">
                                    <span class="metric-label">Resistance Level:</span>
                                    <span class="metric-value">$${parseFloat(technical.resistance_level).toFixed(2)}</span>
                                </div>
                            ` : ''}
                            <p style="margin-top: 15px; font-style: italic; color: #666;">
                                ${technical.analysis_summary}
                            </p>
                        </div>
                    `;
                }
                
                // Overall Recommendation
                if (data.overall_recommendation) {
                    const recClass = data.overall_recommendation.toLowerCase().includes('buy') ? 'buy' :
                                   data.overall_recommendation.toLowerCase().includes('sell') ? 'sell' : 'hold';
                    
                    html += `
                        <div class="recommendation ${recClass}">
                            <strong>Overall Recommendation: ${data.overall_recommendation}</strong>
                            ${data.confidence_score ? `
                                <br>Confidence Score: ${parseFloat(data.confidence_score).toFixed(1)}%
                            ` : ''}
                        </div>
                    `;
                }
                
                analysisContent.innerHTML = html;
            }
            
            // Allow Enter key to trigger analysis
            document.getElementById('symbol').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    performAnalysis();
                }
            });
        </script>
    </body>
    </html>
    """

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "demo", "timestamp": datetime.now()}

@app.get("/api/analyze/{symbol}")
async def analyze_symbol(symbol: str = Path(..., description="Stock symbol to analyze")):
    """Comprehensive analysis of a stock symbol (demo version)"""
    try:
        symbol = symbol.upper()
        
        # Simulate processing time
        await asyncio.sleep(1)
        
        # Generate demo data
        security_data = generate_demo_security_data(symbol)
        fundamental_analysis = generate_demo_fundamental_analysis(symbol)
        technical_analysis = generate_demo_technical_analysis(symbol)
        
        # Generate overall recommendation
        import random
        random.seed(hash(symbol) % 1000)
        
        recommendations = ["Strong Buy", "Buy", "Hold", "Sell"]
        weights = [0.2, 0.3, 0.4, 0.1]  # Bias toward hold/buy
        overall_recommendation = random.choices(recommendations, weights=weights)[0]
        
        confidence_score = Decimal(str(round(70 + random.random() * 25, 1)))
        
        return ComprehensiveAnalysisResponse(
            symbol=symbol,
            security_data=security_data,
            fundamental_analysis=fundamental_analysis,
            technical_analysis=technical_analysis,
            overall_recommendation=overall_recommendation,
            confidence_score=confidence_score,
            analysis_timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error in demo analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fundamental/{symbol}")
async def get_fundamental_analysis(symbol: str = Path(..., description="Stock symbol")):
    """Get fundamental analysis for a stock (demo version)"""
    try:
        symbol = symbol.upper()
        await asyncio.sleep(0.5)
        result = generate_demo_fundamental_analysis(symbol)
        return result
    except Exception as e:
        logger.error(f"Error in demo fundamental analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/technical/{symbol}")
async def get_technical_analysis(symbol: str = Path(..., description="Stock symbol")):
    """Get technical analysis for a stock (demo version)"""
    try:
        symbol = symbol.upper()
        await asyncio.sleep(0.5)
        result = generate_demo_technical_analysis(symbol)
        return result
    except Exception as e:
        logger.error(f"Error in demo technical analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demo/features")
async def demo_features():
    """List demo features and limitations"""
    return {
        "demo_version": "1.0.0",
        "features": {
            "fundamental_analysis": "Basic P/E, P/B, growth metrics with demo data",
            "technical_analysis": "RSI, MACD, trend analysis with simulated indicators",
            "security_data": "Company information and pricing for select stocks",
            "recommendations": "Algorithm-generated buy/sell/hold recommendations"
        },
        "limitations": {
            "data_source": "Demo data only - not real-time market data",
            "coverage": "Limited to pre-configured demo stocks",
            "ai_features": "Simulated AI analysis - not actual machine learning",
            "indicators": "Simplified technical indicators"
        },
        "production_features": {
            "real_time_data": "Integration with multiple financial APIs",
            "comprehensive_analysis": "100+ technical indicators, full fundamental metrics",
            "ai_powered": "Actual machine learning models for predictions",
            "company_deep_dive": "Complete business analysis and ESG scoring",
            "portfolio_optimization": "Advanced portfolio management tools"
        },
        "demo_stocks": list(DEMO_STOCKS.keys())
    }

if __name__ == "__main__":
    print("🚀 Starting Market Analysis Platform Demo Server on port 8414")
    print("📊 Features: Demo fundamental & technical analysis")
    print("🌐 Dashboard: http://localhost:8414")
    print("📖 API Docs: http://localhost:8414/docs")
    
    uvicorn.run(
        "demo_main:app",
        host="0.0.0.0",
        port=8414,
        reload=False,
        log_level="info"
    )