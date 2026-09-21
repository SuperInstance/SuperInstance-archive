"""
Market Analysis Platform - Main FastAPI Application
World-class analysis platform with fundamental analysis, technical analysis, AI-powered predictions, and company deep dives
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Query, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Import our analysis modules
try:
    from src.fundamental_analysis import FundamentalAnalyzer, create_fundamental_analyzer
    fundamental_available = True
except ImportError as e:
    print(f"Warning: Fundamental analysis not available: {e}")
    fundamental_available = False

try:
    from src.technical_analysis import TechnicalAnalyzer, create_technical_analyzer
    technical_available = True
except ImportError as e:
    print(f"Warning: Technical analysis not available: {e}")
    technical_available = False

try:
    from src.ai_analysis import AIAnalysisEngine, create_ai_analysis_engine
    ai_available = True
except ImportError as e:
    print(f"Warning: AI analysis not available: {e}")
    ai_available = False

try:
    from src.company_analysis import CompanyDeepDiveAnalyzer, create_company_analyzer
    company_available = True
except ImportError as e:
    print(f"Warning: Company analysis not available: {e}")
    company_available = False
from src.models import (
    SecurityData, FundamentalMetrics, TechnicalIndicator, PatternRecognition,
    SentimentAnalysis, PricePrediction, RiskMetrics, CompanyProfile,
    ESGScoring, AnalystRating, EarningsData, SectorAnalysis,
    AssetType, AnalysisType, RecommendationType, RiskLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Market Analysis Platform",
    description="World-class financial analysis platform with fundamental analysis, technical analysis, AI-powered predictions, and company deep dives",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize analysis engines
fundamental_analyzer = create_fundamental_analyzer() if fundamental_available else None
technical_analyzer = create_technical_analyzer() if technical_available else None
ai_engine = create_ai_analysis_engine() if ai_available else None
company_analyzer = create_company_analyzer() if company_available else None

# Request/Response Models
class AnalysisRequest(BaseModel):
    symbol: str
    analysis_types: List[AnalysisType] = [AnalysisType.FUNDAMENTAL, AnalysisType.TECHNICAL]
    timeframe: Optional[str] = "1d"
    include_predictions: bool = True
    include_deep_dive: bool = False

class ComprehensiveAnalysisResponse(BaseModel):
    symbol: str
    security_data: Optional[SecurityData] = None
    fundamental_analysis: Optional[Dict[str, Any]] = None
    technical_analysis: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    company_analysis: Optional[Dict[str, Any]] = None
    analysis_timestamp: datetime
    errors: List[str] = []

class PortfolioOptimizationRequest(BaseModel):
    symbols: List[str]
    method: str = "mean_variance"
    risk_tolerance: str = "medium"
    constraints: Dict[str, Any] = {}

class SectorAnalysisRequest(BaseModel):
    sectors: List[str] = []
    timeframe: str = "1m"
    include_top_performers: bool = True

# Root endpoint with dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard for the market analysis platform"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Market Analysis Platform</title>
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
            
            .feature ul {
                list-style: none;
                color: #666;
            }
            
            .feature li {
                padding: 5px 0;
                position: relative;
                padding-left: 20px;
            }
            
            .feature li:before {
                content: '✓';
                position: absolute;
                left: 0;
                color: #27ae60;
                font-weight: bold;
            }
            
            .api-section {
                background: #2c3e50;
                color: white;
                padding: 40px;
            }
            
            .api-section h2 {
                margin-bottom: 20px;
                color: #ecf0f1;
            }
            
            .api-endpoints {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            
            .endpoint {
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.2);
            }
            
            .endpoint-method {
                background: #27ae60;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                font-weight: bold;
            }
            
            .endpoint-path {
                font-family: 'Courier New', monospace;
                margin: 10px 0;
                font-size: 0.9em;
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
            
            .results {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 6px;
                display: none;
            }
            
            .loading {
                text-align: center;
                padding: 40px;
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Market Analysis Platform</h1>
                <p>World-class financial analysis with AI-powered insights</p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>📊 Fundamental Analysis</h3>
                    <ul>
                        <li>P/E, P/B, PEG ratios</li>
                        <li>Cash flow analysis</li>
                        <li>Profitability metrics</li>
                        <li>Financial health scoring</li>
                        <li>Insider trading analysis</li>
                    </ul>
                </div>
                
                <div class="feature">
                    <h3>📈 Technical Analysis</h3>
                    <ul>
                        <li>100+ technical indicators</li>
                        <li>Pattern recognition</li>
                        <li>Support/resistance levels</li>
                        <li>Ichimoku Cloud analysis</li>
                        <li>Volume profile analysis</li>
                    </ul>
                </div>
                
                <div class="feature">
                    <h3>🤖 AI-Powered Analysis</h3>
                    <ul>
                        <li>Sentiment analysis</li>
                        <li>Price predictions</li>
                        <li>Risk assessment</li>
                        <li>Market regime detection</li>
                        <li>Portfolio optimization</li>
                    </ul>
                </div>
                
                <div class="feature">
                    <h3>🏢 Company Deep Dive</h3>
                    <ul>
                        <li>Business model analysis</li>
                        <li>Competitive positioning</li>
                        <li>ESG scoring</li>
                        <li>Governance analysis</li>
                        <li>Strategic assessment</li>
                    </ul>
                </div>
            </div>
            
            <div class="demo-section">
                <h2>Try Live Analysis</h2>
                <div class="demo-form">
                    <div class="form-group">
                        <label for="symbol">Stock Symbol</label>
                        <input type="text" id="symbol" placeholder="e.g., AAPL, MSFT, GOOGL" value="AAPL">
                    </div>
                    
                    <div class="form-group">
                        <label for="analysisType">Analysis Type</label>
                        <select id="analysisType">
                            <option value="comprehensive">Comprehensive Analysis</option>
                            <option value="fundamental">Fundamental Only</option>
                            <option value="technical">Technical Only</option>
                            <option value="ai">AI Analysis Only</option>
                            <option value="company">Company Deep Dive</option>
                        </select>
                    </div>
                    
                    <button class="analyze-btn" onclick="performAnalysis()">
                        Analyze Stock 🔍
                    </button>
                    
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Analyzing... Please wait</p>
                    </div>
                    
                    <div class="results" id="results">
                        <h3>Analysis Results</h3>
                        <pre id="resultsContent"></pre>
                    </div>
                </div>
            </div>
            
            <div class="api-section">
                <h2>API Endpoints</h2>
                <p>Integrate our powerful analysis into your applications</p>
                
                <div class="api-endpoints">
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <div class="endpoint-path">/api/analyze/{symbol}</div>
                        <p>Comprehensive stock analysis</p>
                    </div>
                    
                    <div class="endpoint">
                        <span class="endpoint-method">POST</span>
                        <div class="endpoint-path">/api/portfolio/optimize</div>
                        <p>Portfolio optimization</p>
                    </div>
                    
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <div class="endpoint-path">/api/sector/analysis</div>
                        <p>Sector performance analysis</p>
                    </div>
                    
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <div class="endpoint-path">/api/predictions/{symbol}</div>
                        <p>AI price predictions</p>
                    </div>
                    
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <div class="endpoint-path">/api/company/{symbol}/deep-dive</div>
                        <p>Company deep dive analysis</p>
                    </div>
                    
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <div class="endpoint-path">/api/technical/{symbol}</div>
                        <p>Technical analysis indicators</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            async function performAnalysis() {
                const symbol = document.getElementById('symbol').value.toUpperCase();
                const analysisType = document.getElementById('analysisType').value;
                
                if (!symbol) {
                    alert('Please enter a stock symbol');
                    return;
                }
                
                const loadingDiv = document.querySelector('.loading');
                const resultsDiv = document.getElementById('results');
                const resultsContent = document.getElementById('resultsContent');
                const analyzeBtn = document.querySelector('.analyze-btn');
                
                // Show loading
                loadingDiv.style.display = 'block';
                resultsDiv.style.display = 'none';
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = 'Analyzing...';
                
                try {
                    let url;
                    switch(analysisType) {
                        case 'fundamental':
                            url = `/api/fundamental/${symbol}`;
                            break;
                        case 'technical':
                            url = `/api/technical/${symbol}`;
                            break;
                        case 'ai':
                            url = `/api/ai/${symbol}`;
                            break;
                        case 'company':
                            url = `/api/company/${symbol}/deep-dive`;
                            break;
                        default:
                            url = `/api/analyze/${symbol}`;
                    }
                    
                    const response = await fetch(url);
                    const data = await response.json();
                    
                    // Show results
                    resultsContent.textContent = JSON.stringify(data, null, 2);
                    resultsDiv.style.display = 'block';
                    
                } catch (error) {
                    resultsContent.textContent = `Error: ${error.message}`;
                    resultsDiv.style.display = 'block';
                }
                
                // Hide loading
                loadingDiv.style.display = 'none';
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = 'Analyze Stock 🔍';
            }
        </script>
    </body>
    </html>
    """

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

# Comprehensive analysis endpoint
@app.get("/api/analyze/{symbol}")
async def analyze_symbol(
    symbol: str = Path(..., description="Stock symbol to analyze"),
    include_predictions: bool = Query(True, description="Include AI predictions"),
    include_deep_dive: bool = Query(False, description="Include company deep dive"),
    timeframe: str = Query("1d", description="Timeframe for technical analysis")
):
    """Comprehensive analysis of a stock symbol"""
    try:
        symbol = symbol.upper()
        errors = []
        
        # Run all analyses in parallel
        tasks = []
        
        # Fundamental analysis
        tasks.append(fundamental_analyzer.get_comprehensive_analysis(symbol))
        
        # Technical analysis
        tasks.append(technical_analyzer.get_comprehensive_analysis(symbol, timeframe))
        
        # AI analysis (if requested)
        if include_predictions:
            tasks.append(ai_engine.perform_comprehensive_analysis(symbol))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
        
        # Company deep dive (if requested)
        if include_deep_dive:
            tasks.append(company_analyzer.perform_deep_dive(symbol))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        fundamental_result = results[0] if not isinstance(results[0], Exception) else None
        technical_result = results[1] if not isinstance(results[1], Exception) else None
        ai_result = results[2] if not isinstance(results[2], Exception) else None
        company_result = results[3] if not isinstance(results[3], Exception) else None
        
        # Collect errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Analysis {i} error: {str(result)}")
        
        # Get basic security data
        security_data = None
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            security_data = SecurityData(
                symbol=symbol,
                name=info.get('longName', symbol),
                asset_type=AssetType.STOCK,  # Assuming stock for now
                exchange=info.get('exchange', 'Unknown'),
                sector=info.get('sector'),
                industry=info.get('industry'),
                market_cap=Decimal(str(info.get('marketCap', 0))),
                current_price=Decimal(str(info.get('currentPrice', 0))),
                currency=info.get('currency', 'USD')
            )
        except Exception as e:
            errors.append(f"Security data error: {str(e)}")
        
        return ComprehensiveAnalysisResponse(
            symbol=symbol,
            security_data=security_data,
            fundamental_analysis=fundamental_result,
            technical_analysis=technical_result,
            ai_analysis=ai_result if include_predictions else None,
            company_analysis=company_result if include_deep_dive else None,
            analysis_timestamp=datetime.now(),
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Fundamental analysis endpoint
@app.get("/api/fundamental/{symbol}")
async def get_fundamental_analysis(symbol: str = Path(..., description="Stock symbol")):
    """Get fundamental analysis for a stock"""
    try:
        symbol = symbol.upper()
        result = await fundamental_analyzer.get_comprehensive_analysis(symbol)
        return result
    except Exception as e:
        logger.error(f"Error in fundamental analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Technical analysis endpoint
@app.get("/api/technical/{symbol}")
async def get_technical_analysis(
    symbol: str = Path(..., description="Stock symbol"),
    timeframe: str = Query("1d", description="Timeframe (1d, 1h, etc.)")
):
    """Get technical analysis for a stock"""
    try:
        symbol = symbol.upper()
        result = await technical_analyzer.get_comprehensive_analysis(symbol, timeframe)
        return result
    except Exception as e:
        logger.error(f"Error in technical analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI analysis endpoint
@app.get("/api/ai/{symbol}")
async def get_ai_analysis(symbol: str = Path(..., description="Stock symbol")):
    """Get AI-powered analysis for a stock"""
    try:
        symbol = symbol.upper()
        result = await ai_engine.perform_comprehensive_analysis(symbol)
        return result
    except Exception as e:
        logger.error(f"Error in AI analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Company deep dive endpoint
@app.get("/api/company/{symbol}/deep-dive")
async def get_company_analysis(symbol: str = Path(..., description="Stock symbol")):
    """Get comprehensive company deep dive analysis"""
    try:
        symbol = symbol.upper()
        result = await company_analyzer.perform_deep_dive(symbol)
        return result
    except Exception as e:
        logger.error(f"Error in company analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Price predictions endpoint
@app.get("/api/predictions/{symbol}")
async def get_price_predictions(symbol: str = Path(..., description="Stock symbol")):
    """Get AI price predictions for a stock"""
    try:
        symbol = symbol.upper()
        predictions = await ai_engine.prediction_engine.generate_predictions(symbol)
        return {"symbol": symbol, "predictions": predictions}
    except Exception as e:
        logger.error(f"Error getting predictions for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Portfolio optimization endpoint
@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: PortfolioOptimizationRequest):
    """Optimize portfolio allocation"""
    try:
        result = await ai_engine.portfolio_optimizer.optimize_portfolio(
            request.symbols, 
            request.method
        )
        return result
    except Exception as e:
        logger.error(f"Error optimizing portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Sector analysis endpoint
@app.get("/api/sector/analysis")
async def get_sector_analysis(
    sectors: List[str] = Query([], description="Sectors to analyze"),
    timeframe: str = Query("1m", description="Analysis timeframe")
):
    """Get sector performance analysis"""
    try:
        # If no sectors specified, use default major sectors
        if not sectors:
            sectors = [
                "Technology", "Healthcare", "Financials", "Consumer Discretionary",
                "Consumer Staples", "Energy", "Industrials", "Materials",
                "Real Estate", "Utilities", "Communication Services"
            ]
        
        # This would integrate with sector ETF data or aggregate individual stocks
        sector_analyses = []
        
        for sector in sectors:
            # Simplified sector analysis - in real implementation would use sector ETFs
            analysis = SectorAnalysis(
                sector=sector,
                performance_1d=Decimal('0.5'),
                performance_1w=Decimal('2.3'),
                performance_1m=Decimal('4.1'),
                performance_3m=Decimal('8.7'),
                performance_ytd=Decimal('12.4'),
                performance_1y=Decimal('15.6'),
                top_performers=["Symbol1", "Symbol2", "Symbol3"],
                worst_performers=["Symbol4", "Symbol5"]
            )
            sector_analyses.append(analysis)
        
        return {"sectors": sector_analyses, "analysis_timestamp": datetime.now()}
        
    except Exception as e:
        logger.error(f"Error in sector analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Risk metrics endpoint
@app.get("/api/risk/{symbol}")
async def get_risk_metrics(symbol: str = Path(..., description="Stock symbol")):
    """Get risk metrics for a stock"""
    try:
        symbol = symbol.upper()
        risk_metrics = await ai_engine.risk_analyzer.assess_risk(symbol)
        return risk_metrics
    except Exception as e:
        logger.error(f"Error getting risk metrics for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Market regime endpoint
@app.get("/api/market/regime")
async def get_market_regime():
    """Get current market regime analysis"""
    try:
        regime = await ai_engine.market_regime_detector.detect_current_regime()
        return regime
    except Exception as e:
        logger.error(f"Error detecting market regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Batch analysis endpoint
@app.post("/api/analyze/batch")
async def analyze_batch(symbols: List[str], analysis_types: List[AnalysisType] = None):
    """Analyze multiple symbols in batch"""
    try:
        if not symbols:
            raise HTTPException(status_code=400, detail="No symbols provided")
        
        if len(symbols) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 symbols per batch")
        
        # Default analysis types
        if not analysis_types:
            analysis_types = [AnalysisType.FUNDAMENTAL, AnalysisType.TECHNICAL]
        
        results = {}
        tasks = []
        
        for symbol in symbols:
            symbol = symbol.upper()
            if AnalysisType.FUNDAMENTAL in analysis_types:
                tasks.append((symbol, "fundamental", fundamental_analyzer.get_comprehensive_analysis(symbol)))
            if AnalysisType.TECHNICAL in analysis_types:
                tasks.append((symbol, "technical", technical_analyzer.get_comprehensive_analysis(symbol, "1d")))
        
        # Execute all tasks
        completed_tasks = await asyncio.gather(*[task[2] for task in tasks], return_exceptions=True)
        
        # Process results
        for i, (symbol, analysis_type, _) in enumerate(tasks):
            if symbol not in results:
                results[symbol] = {}
            
            result = completed_tasks[i]
            if isinstance(result, Exception):
                results[symbol][analysis_type] = {"error": str(result)}
            else:
                results[symbol][analysis_type] = result
        
        return {"results": results, "analysis_timestamp": datetime.now()}
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Watchlist endpoint
@app.post("/api/watchlist/analyze")
async def analyze_watchlist(symbols: List[str], background_tasks: BackgroundTasks):
    """Analyze a watchlist of symbols with background processing"""
    try:
        if not symbols or len(symbols) > 50:
            raise HTTPException(status_code=400, detail="Invalid watchlist size (1-50 symbols)")
        
        # Start background analysis
        analysis_id = f"watchlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async def process_watchlist():
            """Background task to process watchlist"""
            try:
                results = {}
                for symbol in symbols:
                    symbol = symbol.upper()
                    # Perform basic analysis for each symbol
                    fundamental_result = await fundamental_analyzer.get_comprehensive_analysis(symbol)
                    results[symbol] = fundamental_result
                
                # In a real implementation, you'd store results in a database or cache
                logger.info(f"Completed watchlist analysis {analysis_id} for {len(symbols)} symbols")
                
            except Exception as e:
                logger.error(f"Error in watchlist background processing: {e}")
        
        background_tasks.add_task(process_watchlist)
        
        return {
            "analysis_id": analysis_id,
            "status": "processing",
            "symbols_count": len(symbols),
            "estimated_completion": datetime.now() + timedelta(minutes=len(symbols) * 2)
        }
        
    except Exception as e:
        logger.error(f"Error starting watchlist analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Documentation endpoint
@app.get("/docs/features", response_class=HTMLResponse)
async def features_documentation():
    """Detailed features documentation"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Market Analysis Platform - Features</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
            .feature { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
            .feature h2 { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
            .feature ul { margin-top: 10px; }
            .feature li { margin-bottom: 5px; }
            .code { background: #f5f5f5; padding: 15px; border-radius: 4px; font-family: monospace; }
        </style>
    </head>
    <body>
        <h1>Market Analysis Platform - Features Overview</h1>
        
        <div class="feature">
            <h2>📊 Fundamental Analysis Suite</h2>
            <ul>
                <li><strong>Valuation Metrics:</strong> P/E, P/B, PEG, P/S ratios with peer comparisons</li>
                <li><strong>Growth Analysis:</strong> Revenue, earnings growth rates (1Y, 3Y)</li>
                <li><strong>Profitability:</strong> Margins, ROE, ROA, ROIC analysis</li>
                <li><strong>Financial Health:</strong> Debt ratios, liquidity analysis</li>
                <li><strong>Cash Flow:</strong> Operating CF, free cash flow analysis</li>
                <li><strong>Insider Activity:</strong> Insider buying/selling patterns</li>
            </ul>
            <div class="code">GET /api/fundamental/AAPL</div>
        </div>
        
        <div class="feature">
            <h2>📈 Technical Analysis (100+ Indicators)</h2>
            <ul>
                <li><strong>Trend Indicators:</strong> Moving averages, MACD, ADX, Parabolic SAR</li>
                <li><strong>Momentum:</strong> RSI, Stochastic, Williams %R, CCI</li>
                <li><strong>Volatility:</strong> Bollinger Bands, ATR, Keltner Channels</li>
                <li><strong>Volume:</strong> OBV, Volume Profile, Accumulation/Distribution</li>
                <li><strong>Pattern Recognition:</strong> Candlestick patterns, chart formations</li>
                <li><strong>Support/Resistance:</strong> Pivot points, Fibonacci retracements</li>
            </ul>
            <div class="code">GET /api/technical/AAPL?timeframe=1d</div>
        </div>
        
        <div class="feature">
            <h2>🤖 AI-Powered Analysis</h2>
            <ul>
                <li><strong>Sentiment Analysis:</strong> News, social media, analyst sentiment</li>
                <li><strong>Price Predictions:</strong> ML models for 1D, 1W, 1M, 3M forecasts</li>
                <li><strong>Risk Assessment:</strong> Beta, VaR, Sharpe ratio, drawdown analysis</li>
                <li><strong>Market Regime:</strong> Bull/bear/sideways market detection</li>
                <li><strong>Portfolio Optimization:</strong> Mean-variance, risk parity methods</li>
                <li><strong>Correlation Analysis:</strong> Stock and sector correlations</li>
            </ul>
            <div class="code">GET /api/ai/AAPL</div>
        </div>
        
        <div class="feature">
            <h2>🏢 Company Deep Dive</h2>
            <ul>
                <li><strong>Business Model:</strong> Revenue streams, cost structure analysis</li>
                <li><strong>Competitive Position:</strong> Market share, competitive advantages</li>
                <li><strong>ESG Scoring:</strong> Environmental, social, governance metrics</li>
                <li><strong>Strategic Analysis:</strong> Innovation, digital transformation</li>
                <li><strong>Financial Health:</strong> Liquidity, solvency, cash flow quality</li>
                <li><strong>Management Analysis:</strong> Leadership effectiveness, track record</li>
            </ul>
            <div class="code">GET /api/company/AAPL/deep-dive</div>
        </div>
        
        <h2>🚀 Getting Started</h2>
        <p>Try the comprehensive analysis endpoint:</p>
        <div class="code">
GET /api/analyze/AAPL?include_predictions=true&include_deep_dive=true
        </div>
        
        <p><a href="/">← Back to Dashboard</a></p>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8414,
        reload=True,
        log_level="info"
    )