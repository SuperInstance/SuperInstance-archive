from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sqlite3
import aiohttp
import asyncio
import json
import os
from decimal import Decimal
import random

router = APIRouter()

# API Configuration
API_CONFIG = {
    "yahoo_finance": {
        "base_url": "https://query1.finance.yahoo.com/v8/finance/chart/",
        "rate_limit": 2000,  # requests per hour
        "free": True
    },
    "alpha_vantage": {
        "base_url": "https://www.alphavantage.co/query",
        "api_key": os.getenv("ALPHA_VANTAGE_API_KEY", "demo"),
        "rate_limit": 5,     # requests per minute for free tier
        "free": True
    },
    "iex_cloud": {
        "base_url": "https://cloud.iexapis.com/stable",
        "api_key": os.getenv("IEX_CLOUD_API_KEY", "pk_test123"),
        "rate_limit": 100,   # requests per second for paid tier
        "free": False
    },
    "polygon": {
        "base_url": "https://api.polygon.io",
        "api_key": os.getenv("POLYGON_API_KEY", ""),
        "rate_limit": 5,     # requests per minute for free tier
        "free": True
    },
    "coinapi": {
        "base_url": "https://rest.coinapi.io/v1",
        "api_key": os.getenv("COINAPI_KEY", ""),
        "rate_limit": 100,   # requests per day for free tier
        "free": True
    }
}

# Pydantic models
class MarketQuote(BaseModel):
    symbol: str
    asset_type: str
    current_price: float
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    previous_close: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    day_change: Optional[float] = None
    day_change_percent: Optional[float] = None
    last_updated: datetime
    data_source: str

class HistoricalData(BaseModel):
    symbol: str
    asset_type: str
    timeframe: str  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
    data_points: List[Dict[str, Any]]
    last_updated: datetime

class MarketScreener(BaseModel):
    filters: Dict[str, Any]
    results: List[MarketQuote]
    total_results: int

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('paper_trading.db')

class MarketDataProvider:
    """Unified market data provider with multiple API sources"""
    
    def __init__(self):
        self.session = None
        self.rate_limits = {}
        self.last_request_times = {}
    
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    def should_rate_limit(self, source: str) -> bool:
        """Check if we should rate limit requests to a source"""
        config = API_CONFIG.get(source, {})
        rate_limit = config.get("rate_limit", 60)
        
        now = datetime.now()
        if source not in self.last_request_times:
            self.last_request_times[source] = now
            return False
        
        time_diff = (now - self.last_request_times[source]).total_seconds()
        min_interval = 60.0 / rate_limit  # seconds between requests
        
        if time_diff < min_interval:
            return True
        
        self.last_request_times[source] = now
        return False
    
    async def get_yahoo_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get quote from Yahoo Finance (free, reliable)"""
        if self.should_rate_limit("yahoo_finance"):
            await asyncio.sleep(0.1)
        
        try:
            session = await self.get_session()
            url = f"{API_CONFIG['yahoo_finance']['base_url']}{symbol}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get("chart", {}).get("result", [])
                    
                    if result:
                        quote = result[0]
                        meta = quote.get("meta", {})
                        
                        return MarketQuote(
                            symbol=symbol,
                            asset_type="stock",
                            current_price=meta.get("regularMarketPrice", 0),
                            open_price=meta.get("regularMarketOpen"),
                            high_price=meta.get("regularMarketDayHigh"),
                            low_price=meta.get("regularMarketDayLow"),
                            previous_close=meta.get("previousClose"),
                            volume=meta.get("regularMarketVolume"),
                            day_change=meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0),
                            day_change_percent=((meta.get("regularMarketPrice", 0) - meta.get("previousClose", 1)) / meta.get("previousClose", 1)) * 100,
                            last_updated=datetime.now(),
                            data_source="yahoo_finance"
                        )
        except Exception as e:
            print(f"Yahoo Finance API error for {symbol}: {e}")
        
        return None
    
    async def get_alpha_vantage_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get quote from Alpha Vantage"""
        if self.should_rate_limit("alpha_vantage"):
            await asyncio.sleep(12)  # 5 per minute limit
        
        try:
            session = await self.get_session()
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": API_CONFIG["alpha_vantage"]["api_key"]
            }
            
            async with session.get(API_CONFIG["alpha_vantage"]["base_url"], params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    quote = data.get("Global Quote", {})
                    
                    if quote:
                        price = float(quote.get("05. price", 0))
                        previous_close = float(quote.get("08. previous close", 0))
                        
                        return MarketQuote(
                            symbol=symbol,
                            asset_type="stock",
                            current_price=price,
                            open_price=float(quote.get("02. open", 0)),
                            high_price=float(quote.get("03. high", 0)),
                            low_price=float(quote.get("04. low", 0)),
                            previous_close=previous_close,
                            volume=int(quote.get("06. volume", 0)),
                            day_change=price - previous_close,
                            day_change_percent=float(quote.get("10. change percent", "0%").replace("%", "")),
                            last_updated=datetime.now(),
                            data_source="alpha_vantage"
                        )
        except Exception as e:
            print(f"Alpha Vantage API error for {symbol}: {e}")
        
        return None
    
    async def get_crypto_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get cryptocurrency quote (simulated for now)"""
        try:
            # This would integrate with actual crypto APIs like CoinGecko, CoinAPI, etc.
            # For now, we'll simulate realistic crypto data
            
            base_prices = {
                "BTC": 45000, "ETH": 3000, "ADA": 0.5, "DOT": 20, "LINK": 15,
                "XRP": 0.6, "LTC": 150, "BCH": 300, "XLM": 0.2, "UNI": 10
            }
            
            base_price = base_prices.get(symbol, random.uniform(1, 100))
            
            # Add some realistic volatility
            volatility = random.uniform(-0.1, 0.1)  # ±10%
            current_price = base_price * (1 + volatility)
            
            day_change = current_price - base_price
            day_change_percent = (day_change / base_price) * 100
            
            return MarketQuote(
                symbol=symbol,
                asset_type="crypto",
                current_price=current_price,
                open_price=base_price,
                high_price=current_price * 1.05,
                low_price=current_price * 0.95,
                previous_close=base_price,
                volume=random.randint(1000000, 100000000),
                day_change=day_change,
                day_change_percent=day_change_percent,
                last_updated=datetime.now(),
                data_source="simulated"
            )
        except Exception as e:
            print(f"Crypto quote error for {symbol}: {e}")
        
        return None
    
    async def get_forex_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get forex quote (simulated)"""
        try:
            # Common forex pairs with approximate rates
            base_rates = {
                "EURUSD": 1.08, "GBPUSD": 1.25, "USDJPY": 150, "USDCHF": 0.92,
                "AUDUSD": 0.65, "USDCAD": 1.35, "NZDUSD": 0.60, "EURGBP": 0.86
            }
            
            base_rate = base_rates.get(symbol, 1.0)
            volatility = random.uniform(-0.005, 0.005)  # ±0.5% typical daily forex volatility
            current_rate = base_rate * (1 + volatility)
            
            return MarketQuote(
                symbol=symbol,
                asset_type="forex",
                current_price=current_rate,
                open_price=base_rate,
                high_price=current_rate * 1.002,
                low_price=current_rate * 0.998,
                previous_close=base_rate,
                volume=random.randint(10000000, 1000000000),
                day_change=current_rate - base_rate,
                day_change_percent=((current_rate - base_rate) / base_rate) * 100,
                last_updated=datetime.now(),
                data_source="simulated"
            )
        except Exception as e:
            print(f"Forex quote error for {symbol}: {e}")
        
        return None

# Global market data provider instance
market_provider = MarketDataProvider()

@router.get("/quote/{symbol}", response_model=MarketQuote)
async def get_quote(symbol: str, asset_type: str = "stock"):
    """Get real-time quote for a symbol"""
    
    # Check if it's an ActiveLog ecosystem company first
    if asset_type == "activelog":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT current_price, name, market_cap FROM activelog_companies WHERE symbol = ?', (symbol,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            price, name, market_cap = result
            # Add some realistic daily movement
            daily_volatility = random.uniform(-0.05, 0.05)  # ±5%
            current_price = price * (1 + daily_volatility)
            
            return MarketQuote(
                symbol=symbol,
                asset_type="activelog",
                current_price=current_price,
                open_price=price,
                high_price=current_price * 1.02,
                low_price=current_price * 0.98,
                previous_close=price,
                market_cap=market_cap,
                day_change=current_price - price,
                day_change_percent=daily_volatility * 100,
                last_updated=datetime.now(),
                data_source="activelog"
            )
    
    # Try to get from cache first
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT current_price, open_price, high_price, low_price, volume, market_cap,
               day_change, day_change_percent, last_updated, data_source
        FROM market_data 
        WHERE symbol = ? AND asset_type = ? AND last_updated > datetime("now", "-15 minutes")
    ''', (symbol, asset_type))
    
    cached_data = cursor.fetchone()
    
    if cached_data:
        conn.close()
        return MarketQuote(
            symbol=symbol,
            asset_type=asset_type,
            current_price=cached_data[0],
            open_price=cached_data[1],
            high_price=cached_data[2],
            low_price=cached_data[3],
            volume=cached_data[4],
            market_cap=cached_data[5],
            day_change=cached_data[6],
            day_change_percent=cached_data[7],
            last_updated=datetime.fromisoformat(cached_data[8]),
            data_source=cached_data[9]
        )
    
    conn.close()
    
    # Fetch fresh data based on asset type
    quote = None
    
    if asset_type == "stock":
        # Try Yahoo Finance first (free and reliable)
        quote = await market_provider.get_yahoo_quote(symbol)
        if not quote:
            quote = await market_provider.get_alpha_vantage_quote(symbol)
    
    elif asset_type == "crypto":
        quote = await market_provider.get_crypto_quote(symbol)
    
    elif asset_type == "forex":
        quote = await market_provider.get_forex_quote(symbol)
    
    else:
        # For other asset types, use simulated data
        quote = MarketQuote(
            symbol=symbol,
            asset_type=asset_type,
            current_price=random.uniform(10, 500),
            last_updated=datetime.now(),
            data_source="simulated"
        )
    
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")
    
    # Cache the data
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO market_data 
        (symbol, asset_type, current_price, open_price, high_price, low_price, volume, 
         market_cap, day_change, day_change_percent, data_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (quote.symbol, quote.asset_type, quote.current_price, quote.open_price,
          quote.high_price, quote.low_price, quote.volume, quote.market_cap,
          quote.day_change, quote.day_change_percent, quote.data_source))
    conn.commit()
    conn.close()
    
    return quote

@router.get("/quotes")
async def get_multiple_quotes(symbols: str, asset_type: str = "stock"):
    """Get quotes for multiple symbols (comma-separated)"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    quotes = []
    
    for symbol in symbol_list:
        try:
            quote = await get_quote(symbol, asset_type)
            quotes.append(quote)
        except HTTPException:
            # Skip symbols that can't be found
            continue
    
    return {"quotes": quotes}

@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    asset_type: str = "stock",
    timeframe: str = "1mo",
    interval: str = "1d"
):
    """Get historical price data"""
    
    # For demo purposes, generate simulated historical data
    end_date = datetime.now()
    
    if timeframe == "1d":
        start_date = end_date - timedelta(days=1)
        data_points = 24  # hourly data
        time_delta = timedelta(hours=1)
    elif timeframe == "5d":
        start_date = end_date - timedelta(days=5)
        data_points = 5
        time_delta = timedelta(days=1)
    elif timeframe == "1mo":
        start_date = end_date - timedelta(days=30)
        data_points = 30
        time_delta = timedelta(days=1)
    elif timeframe == "3mo":
        start_date = end_date - timedelta(days=90)
        data_points = 90
        time_delta = timedelta(days=1)
    elif timeframe == "1y":
        start_date = end_date - timedelta(days=365)
        data_points = 52  # weekly data
        time_delta = timedelta(weeks=1)
    else:
        start_date = end_date - timedelta(days=365)
        data_points = 52
        time_delta = timedelta(weeks=1)
    
    # Get current price as starting point
    try:
        current_quote = await get_quote(symbol, asset_type)
        base_price = current_quote.current_price
    except:
        base_price = 100.0  # Default price
    
    # Generate historical data points
    historical_points = []
    current_time = start_date
    current_price = base_price * 0.9  # Start 10% lower for trend
    
    for i in range(data_points):
        # Add some realistic price movement
        daily_return = random.gauss(0.001, 0.02)  # 0.1% average daily return, 2% volatility
        current_price = current_price * (1 + daily_return)
        
        # Ensure prices don't go negative
        current_price = max(current_price, 0.01)
        
        open_price = current_price * random.uniform(0.98, 1.02)
        high_price = max(current_price, open_price) * random.uniform(1.0, 1.05)
        low_price = min(current_price, open_price) * random.uniform(0.95, 1.0)
        volume = random.randint(100000, 10000000)
        
        historical_points.append({
            "timestamp": current_time.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(current_price, 2),
            "volume": volume
        })
        
        current_time += time_delta
    
    return HistoricalData(
        symbol=symbol,
        asset_type=asset_type,
        timeframe=timeframe,
        data_points=historical_points,
        last_updated=datetime.now()
    )

@router.get("/market-overview")
async def get_market_overview():
    """Get overall market overview and major indices"""
    
    # Major market indices (simulated)
    indices = {
        "SPY": {"name": "S&P 500", "price": 450.0, "change": 2.5, "change_pct": 0.56},
        "QQQ": {"name": "NASDAQ 100", "price": 380.0, "change": -1.2, "change_pct": -0.31},
        "DIA": {"name": "Dow Jones", "price": 350.0, "change": 5.8, "change_pct": 1.68},
        "IWM": {"name": "Russell 2000", "price": 200.0, "change": 1.1, "change_pct": 0.55}
    }
    
    # Top movers
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT symbol, current_price, day_change_percent 
        FROM market_data 
        WHERE day_change_percent IS NOT NULL 
        ORDER BY day_change_percent DESC 
        LIMIT 10
    ''')
    top_gainers = cursor.fetchall()
    
    cursor.execute('''
        SELECT symbol, current_price, day_change_percent 
        FROM market_data 
        WHERE day_change_percent IS NOT NULL 
        ORDER BY day_change_percent ASC 
        LIMIT 10
    ''')
    top_losers = cursor.fetchall()
    
    cursor.execute('''
        SELECT symbol, volume 
        FROM market_data 
        WHERE volume IS NOT NULL 
        ORDER BY volume DESC 
        LIMIT 10
    ''')
    most_active = cursor.fetchall()
    
    conn.close()
    
    # Market sentiment (simulated)
    sentiment_score = random.uniform(0.3, 0.7)  # 0 = very bearish, 1 = very bullish
    
    if sentiment_score > 0.6:
        sentiment = "bullish"
    elif sentiment_score < 0.4:
        sentiment = "bearish"
    else:
        sentiment = "neutral"
    
    return {
        "indices": indices,
        "top_gainers": [{"symbol": t[0], "price": t[1], "change_pct": t[2]} for t in top_gainers],
        "top_losers": [{"symbol": t[0], "price": t[1], "change_pct": t[2]} for t in top_losers],
        "most_active": [{"symbol": t[0], "volume": t[1]} for t in most_active],
        "market_sentiment": {
            "score": sentiment_score,
            "label": sentiment,
            "fear_greed_index": int(sentiment_score * 100)
        },
        "market_hours": {
            "is_open": datetime.now().weekday() < 5 and 9 <= datetime.now().hour < 16,
            "next_open": "9:30 AM EST",
            "next_close": "4:00 PM EST"
        }
    }

@router.get("/screener")
async def stock_screener(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_market_cap: Optional[float] = None,
    max_market_cap: Optional[float] = None,
    min_volume: Optional[int] = None,
    sector: Optional[str] = None,
    asset_type: str = "stock",
    limit: int = 50
):
    """Screen stocks based on various criteria"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query based on filters
    where_conditions = ["asset_type = ?"]
    params = [asset_type]
    
    if min_price is not None:
        where_conditions.append("current_price >= ?")
        params.append(min_price)
    
    if max_price is not None:
        where_conditions.append("current_price <= ?")
        params.append(max_price)
    
    if min_market_cap is not None:
        where_conditions.append("market_cap >= ?")
        params.append(min_market_cap)
    
    if max_market_cap is not None:
        where_conditions.append("market_cap <= ?")
        params.append(max_market_cap)
    
    if min_volume is not None:
        where_conditions.append("volume >= ?")
        params.append(min_volume)
    
    where_clause = " AND ".join(where_conditions)
    
    query = f'''
        SELECT symbol, current_price, market_cap, volume, day_change_percent
        FROM market_data
        WHERE {where_clause}
        ORDER BY market_cap DESC
        LIMIT ?
    '''
    params.append(limit)
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Get total count
    count_query = f'SELECT COUNT(*) FROM market_data WHERE {where_clause}'
    cursor.execute(count_query, params[:-1])  # Exclude limit parameter
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    screener_results = []
    for result in results:
        symbol, price, market_cap, volume, day_change_pct = result
        screener_results.append(MarketQuote(
            symbol=symbol,
            asset_type=asset_type,
            current_price=price,
            market_cap=market_cap,
            volume=volume,
            day_change_percent=day_change_pct,
            last_updated=datetime.now(),
            data_source="database"
        ))
    
    return MarketScreener(
        filters={
            "min_price": min_price,
            "max_price": max_price,
            "min_market_cap": min_market_cap,
            "max_market_cap": max_market_cap,
            "min_volume": min_volume,
            "asset_type": asset_type
        },
        results=screener_results,
        total_results=total_count
    )

@router.post("/update-market-data")
async def update_market_data(background_tasks: BackgroundTasks):
    """Manually trigger market data update"""
    
    async def update_data():
        """Background task to update all market data"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all symbols that need updates
        cursor.execute('SELECT DISTINCT symbol, asset_type FROM market_data')
        symbols = cursor.fetchall()
        
        updated_count = 0
        for symbol, asset_type in symbols:
            try:
                quote = await get_quote(symbol, asset_type)
                updated_count += 1
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Failed to update {symbol}: {e}")
                continue
        
        conn.close()
        print(f"✅ Updated {updated_count} market data entries")
    
    background_tasks.add_task(update_data)
    
    return {"message": "Market data update started in background"}

@router.get("/watchlist/{user_id}")
async def get_user_watchlist(user_id: str):
    """Get user's watchlist with current quotes"""
    # This would integrate with user preferences
    # For now, return a sample watchlist
    
    sample_watchlist = ["AAPL", "GOOGL", "MSFT", "TSLA", "ALOG", "FUND"]
    quotes = []
    
    for symbol in sample_watchlist:
        try:
            asset_type = "activelog" if symbol in ["ALOG", "FUND", "TRADE", "PAPER"] else "stock"
            quote = await get_quote(symbol, asset_type)
            quotes.append(quote)
        except:
            continue
    
    return {
        "user_id": user_id,
        "watchlist": quotes,
        "last_updated": datetime.now()
    }