#!/usr/bin/env python3
"""
ActiveLedger Market Data Feed
Real-time price streaming and market data distribution
Instance: c5.large
"""

import asyncio
import json
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import aioredis
import sqlite3
import os
from datetime import datetime, timedelta
import random
import math

app = FastAPI(title="ActiveLedger Market Data Feed", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class MarketTick:
    symbol: str
    price: Decimal
    volume: int
    timestamp: float
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    spread: Optional[Decimal] = None

@dataclass
class OHLCV:
    symbol: str
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    timestamp: float
    timeframe: str  # '1m', '5m', '1h', '1d'

@dataclass
class MarketDepth:
    symbol: str
    bids: List[Dict[str, Decimal]]  # [{'price': price, 'quantity': quantity}]
    asks: List[Dict[str, Decimal]]
    timestamp: float

@dataclass
class WebSocketClient:
    websocket: WebSocket
    client_id: str
    subscriptions: Set[str]
    connected_at: float

class MarketDataFeed:
    def __init__(self):
        self.redis_client = None
        self.db_path = "data/market_data.db"
        self.active_connections: Dict[str, WebSocketClient] = {}
        self.symbol_subscribers: Dict[str, Set[str]] = {}
        self.market_data: Dict[str, MarketTick] = {}
        self.market_depth: Dict[str, MarketDepth] = {}
        self.ohlcv_data: Dict[str, List[OHLCV]] = {}
        
        # Market simulation parameters
        self.symbols = [
            'ACTIVELEDGER', 'COMPUTECAPITAL', 'DREAMSHARES', 
            'INNOVATEFUND', 'TECHVENTURE', 'MARKETMAKER',
            'DATASTREAM', 'BLOCKCHAINTECH', 'AIVENTURES', 'CRYPTOFUND'
        ]
        
        self._init_database()
        self._init_market_data()
        
        # Start market data generation
        asyncio.create_task(self._generate_market_data())
        asyncio.create_task(self._generate_ohlcv_data())
        asyncio.create_task(self._cleanup_connections())
    
    def _init_database(self):
        """Initialize SQLite database for market data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Market ticks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_ticks (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                price TEXT NOT NULL,
                volume INTEGER NOT NULL,
                bid TEXT,
                ask TEXT,
                spread TEXT,
                timestamp REAL NOT NULL
            )
        ''')
        
        # OHLCV data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                open_price TEXT NOT NULL,
                high_price TEXT NOT NULL,
                low_price TEXT NOT NULL,
                close_price TEXT NOT NULL,
                volume INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                timeframe TEXT NOT NULL
            )
        ''')
        
        # Market depth snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_depth (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                bids TEXT NOT NULL,
                asks TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        ''')
        
        # Connection metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connection_metrics (
                client_id TEXT PRIMARY KEY,
                connected_at REAL NOT NULL,
                disconnected_at REAL,
                subscriptions TEXT,
                messages_sent INTEGER DEFAULT 0,
                data_transferred INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_market_data(self):
        """Initialize market data for all symbols"""
        for symbol in self.symbols:
            base_price = Decimal(str(random.uniform(50, 500)))
            spread_bps = Decimal(str(random.uniform(0.001, 0.01)))  # 0.1% to 1% spread
            
            bid = base_price * (1 - spread_bps)
            ask = base_price * (1 + spread_bps)
            spread = ask - bid
            
            self.market_data[symbol] = MarketTick(
                symbol=symbol,
                price=base_price,
                volume=random.randint(1000, 10000),
                timestamp=time.time(),
                bid=bid,
                ask=ask,
                spread=spread
            )
            
            # Initialize market depth
            bids = []
            asks = []
            
            for i in range(10):  # 10 levels of depth
                bid_price = bid - (Decimal(str(i)) * spread / Decimal('10'))
                ask_price = ask + (Decimal(str(i)) * spread / Decimal('10'))
                
                bids.append({
                    'price': bid_price,
                    'quantity': Decimal(str(random.randint(100, 5000)))
                })
                asks.append({
                    'price': ask_price,
                    'quantity': Decimal(str(random.randint(100, 5000)))
                })
            
            self.market_depth[symbol] = MarketDepth(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=time.time()
            )
            
            # Initialize OHLCV data
            self.ohlcv_data[symbol] = []
    
    async def initialize_redis(self):
        self.redis_client = await aioredis.from_url("redis://localhost:6379")
    
    async def _generate_market_data(self):
        """Generate realistic market data"""
        while True:
            current_time = time.time()
            
            for symbol in self.symbols:
                current_tick = self.market_data[symbol]
                
                # Generate realistic price movement
                volatility = random.uniform(0.001, 0.02)  # 0.1% to 2% volatility
                direction = random.choice([-1, 1])
                
                # Random walk with some momentum
                price_change_percent = random.gauss(0, volatility) * direction
                new_price = current_tick.price * (1 + Decimal(str(price_change_percent)))
                
                # Ensure price stays positive and within reasonable bounds
                new_price = max(new_price, Decimal('1.00'))
                new_price = min(new_price, Decimal('10000.00'))
                
                # Update bid/ask with new spread
                spread_bps = Decimal(str(random.uniform(0.001, 0.01)))
                bid = new_price * (1 - spread_bps)
                ask = new_price * (1 + spread_bps)
                spread = ask - bid
                
                new_tick = MarketTick(
                    symbol=symbol,
                    price=new_price,
                    volume=random.randint(100, 5000),
                    timestamp=current_time,
                    bid=bid,
                    ask=ask,
                    spread=spread
                )
                
                self.market_data[symbol] = new_tick
                
                # Store in database (sample storage, not every tick)
                if random.random() < 0.1:  # Store 10% of ticks
                    self._store_market_tick(new_tick)
                
                # Update market depth
                await self._update_market_depth(symbol, new_tick)
                
                # Broadcast to subscribers
                await self._broadcast_market_data(symbol, new_tick)
                
                # Publish to Redis for other services
                if self.redis_client:
                    await self.redis_client.publish(
                        f'market_data:{symbol}',
                        json.dumps(asdict(new_tick), default=str)
                    )
            
            # Sleep for a short interval (high frequency updates)
            await asyncio.sleep(0.1)  # 10 updates per second
    
    async def _update_market_depth(self, symbol: str, tick: MarketTick):
        """Update market depth based on new tick"""
        depth = self.market_depth[symbol]
        
        # Simulate depth changes based on price movement
        price_change = (tick.price - Decimal(str(depth.timestamp))) / Decimal(str(depth.timestamp)) if depth.timestamp > 0 else 0
        
        # Update bid/ask levels
        for i in range(len(depth.bids)):
            # Add some randomness to quantities
            quantity_change = Decimal(str(random.uniform(-0.1, 0.1)))
            depth.bids[i]['quantity'] = max(
                depth.bids[i]['quantity'] * (1 + quantity_change),
                Decimal('10')
            )
            
            # Update prices around current bid
            level_offset = Decimal(str(i)) * tick.spread / Decimal('10')
            depth.bids[i]['price'] = tick.bid - level_offset
        
        for i in range(len(depth.asks)):
            quantity_change = Decimal(str(random.uniform(-0.1, 0.1)))
            depth.asks[i]['quantity'] = max(
                depth.asks[i]['quantity'] * (1 + quantity_change),
                Decimal('10')
            )
            
            level_offset = Decimal(str(i)) * tick.spread / Decimal('10')
            depth.asks[i]['price'] = tick.ask + level_offset
        
        depth.timestamp = tick.timestamp
        
        # Broadcast depth update (less frequently)
        if random.random() < 0.2:  # 20% chance
            await self._broadcast_market_depth(symbol, depth)
    
    async def _generate_ohlcv_data(self):
        """Generate OHLCV data for different timeframes"""
        timeframes = {
            '1m': 60,      # 1 minute
            '5m': 300,     # 5 minutes  
            '15m': 900,    # 15 minutes
            '1h': 3600,    # 1 hour
            '4h': 14400,   # 4 hours
            '1d': 86400    # 1 day
        }
        
        while True:
            current_time = time.time()
            
            for symbol in self.symbols:
                current_tick = self.market_data[symbol]
                
                for timeframe, interval_seconds in timeframes.items():
                    # Check if we need to create a new OHLCV bar
                    interval_start = (int(current_time) // interval_seconds) * interval_seconds
                    
                    # Get or create OHLCV bar for this interval
                    ohlcv_bars = self.ohlcv_data[symbol]
                    
                    # Find existing bar for this interval
                    existing_bar = None
                    for bar in ohlcv_bars:
                        if (bar.timeframe == timeframe and 
                            abs(bar.timestamp - interval_start) < interval_seconds):
                            existing_bar = bar
                            break
                    
                    if existing_bar:
                        # Update existing bar
                        existing_bar.high_price = max(existing_bar.high_price, current_tick.price)
                        existing_bar.low_price = min(existing_bar.low_price, current_tick.price)
                        existing_bar.close_price = current_tick.price
                        existing_bar.volume += current_tick.volume
                    else:
                        # Create new bar
                        new_bar = OHLCV(
                            symbol=symbol,
                            open_price=current_tick.price,
                            high_price=current_tick.price,
                            low_price=current_tick.price,
                            close_price=current_tick.price,
                            volume=current_tick.volume,
                            timestamp=interval_start,
                            timeframe=timeframe
                        )
                        
                        ohlcv_bars.append(new_bar)
                        
                        # Keep only last 1000 bars per timeframe
                        if len(ohlcv_bars) > 1000:
                            # Remove old bars of same timeframe
                            ohlcv_bars[:] = [bar for bar in ohlcv_bars 
                                           if bar.timeframe != timeframe][-999:] + [new_bar]
                        
                        # Store in database
                        self._store_ohlcv_data(new_bar)
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    def _store_market_tick(self, tick: MarketTick):
        """Store market tick in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_ticks
            (id, symbol, price, volume, bid, ask, spread, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            tick.symbol,
            str(tick.price),
            tick.volume,
            str(tick.bid) if tick.bid else None,
            str(tick.ask) if tick.ask else None,
            str(tick.spread) if tick.spread else None,
            tick.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def _store_ohlcv_data(self, ohlcv: OHLCV):
        """Store OHLCV data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO ohlcv_data
            (id, symbol, open_price, high_price, low_price, close_price, volume, timestamp, timeframe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"{ohlcv.symbol}_{ohlcv.timeframe}_{int(ohlcv.timestamp)}",
            ohlcv.symbol,
            str(ohlcv.open_price),
            str(ohlcv.high_price),
            str(ohlcv.low_price),
            str(ohlcv.close_price),
            ohlcv.volume,
            ohlcv.timestamp,
            ohlcv.timeframe
        ))
        
        conn.commit()
        conn.close()
    
    async def _broadcast_market_data(self, symbol: str, tick: MarketTick):
        """Broadcast market data to WebSocket subscribers"""
        if symbol not in self.symbol_subscribers:
            return
        
        message = {
            'type': 'market_tick',
            'data': asdict(tick)
        }
        
        disconnected_clients = []
        
        for client_id in self.symbol_subscribers[symbol]:
            if client_id not in self.active_connections:
                disconnected_clients.append(client_id)
                continue
                
            client = self.active_connections[client_id]
            try:
                await client.websocket.send_json(message)
                # Update metrics
                await self._update_client_metrics(client_id, 1, len(json.dumps(message)))
            except:
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self._remove_client_subscription(client_id, symbol)
    
    async def _broadcast_market_depth(self, symbol: str, depth: MarketDepth):
        """Broadcast market depth to WebSocket subscribers"""
        if symbol not in self.symbol_subscribers:
            return
        
        # Convert Decimal to float for JSON serialization
        depth_data = asdict(depth)
        for bid in depth_data['bids']:
            bid['price'] = float(bid['price'])
            bid['quantity'] = float(bid['quantity'])
        for ask in depth_data['asks']:
            ask['price'] = float(ask['price'])
            ask['quantity'] = float(ask['quantity'])
        
        message = {
            'type': 'market_depth',
            'data': depth_data
        }
        
        disconnected_clients = []
        
        for client_id in self.symbol_subscribers[symbol]:
            if client_id not in self.active_connections:
                disconnected_clients.append(client_id)
                continue
                
            client = self.active_connections[client_id]
            try:
                await client.websocket.send_json(message)
            except:
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self._remove_client_subscription(client_id, symbol)
    
    async def _update_client_metrics(self, client_id: str, messages: int, bytes_sent: int):
        """Update client connection metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE connection_metrics 
            SET messages_sent = messages_sent + ?, data_transferred = data_transferred + ?
            WHERE client_id = ?
        ''', (messages, bytes_sent, client_id))
        
        conn.commit()
        conn.close()
    
    def _remove_client_subscription(self, client_id: str, symbol: str):
        """Remove client subscription"""
        if symbol in self.symbol_subscribers:
            self.symbol_subscribers[symbol].discard(client_id)
            if not self.symbol_subscribers[symbol]:
                del self.symbol_subscribers[symbol]
    
    async def _cleanup_connections(self):
        """Periodic cleanup of stale connections"""
        while True:
            await asyncio.sleep(60)  # Clean up every minute
            
            current_time = time.time()
            stale_clients = []
            
            for client_id, client in self.active_connections.items():
                # Check if connection is stale (no activity for 5 minutes)
                if current_time - client.connected_at > 300:
                    try:
                        await client.websocket.ping()
                    except:
                        stale_clients.append(client_id)
            
            # Remove stale clients
            for client_id in stale_clients:
                if client_id in self.active_connections:
                    client = self.active_connections[client_id]
                    # Remove from all subscriptions
                    for symbol in list(client.subscriptions):
                        self._remove_client_subscription(client_id, symbol)
                    
                    del self.active_connections[client_id]
                    
                    # Update database
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE connection_metrics 
                        SET disconnected_at = ?
                        WHERE client_id = ?
                    ''', (current_time, client_id))
                    conn.commit()
                    conn.close()

# Initialize market data feed
market_feed = MarketDataFeed()

@app.on_event("startup")
async def startup_event():
    await market_feed.initialize_redis()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "market-data-feed"}

@app.get("/api/market/symbols")
async def get_symbols():
    """Get all available trading symbols"""
    return {"success": True, "symbols": market_feed.symbols}

@app.get("/api/market/tick/{symbol}")
async def get_current_tick(symbol: str):
    """Get current market tick for symbol"""
    if symbol not in market_feed.market_data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    tick = market_feed.market_data[symbol]
    tick_data = asdict(tick)
    
    # Convert Decimal to float for JSON response
    for key, value in tick_data.items():
        if isinstance(value, Decimal):
            tick_data[key] = float(value)
    
    return {"success": True, "data": tick_data}

@app.get("/api/market/depth/{symbol}")
async def get_market_depth(symbol: str):
    """Get market depth for symbol"""
    if symbol not in market_feed.market_depth:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    depth = market_feed.market_depth[symbol]
    depth_data = asdict(depth)
    
    # Convert Decimal to float
    for bid in depth_data['bids']:
        bid['price'] = float(bid['price'])
        bid['quantity'] = float(bid['quantity'])
    for ask in depth_data['asks']:
        ask['price'] = float(ask['price'])
        ask['quantity'] = float(ask['quantity'])
    
    return {"success": True, "data": depth_data}

@app.get("/api/market/ohlcv/{symbol}")
async def get_ohlcv_data(symbol: str, timeframe: str = '1h', limit: int = 100):
    """Get OHLCV data for symbol"""
    if symbol not in market_feed.ohlcv_data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    # Filter by timeframe and limit
    ohlcv_bars = [
        bar for bar in market_feed.ohlcv_data[symbol]
        if bar.timeframe == timeframe
    ]
    
    # Sort by timestamp and limit
    ohlcv_bars = sorted(ohlcv_bars, key=lambda x: x.timestamp)[-limit:]
    
    # Convert to JSON-friendly format
    bars_data = []
    for bar in ohlcv_bars:
        bar_data = asdict(bar)
        for key, value in bar_data.items():
            if isinstance(value, Decimal):
                bar_data[key] = float(value)
        bars_data.append(bar_data)
    
    return {"success": True, "data": bars_data}

@app.websocket("/ws/market-data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    client_id = str(uuid.uuid4())
    client = WebSocketClient(
        websocket=websocket,
        client_id=client_id,
        subscriptions=set(),
        connected_at=time.time()
    )
    
    market_feed.active_connections[client_id] = client
    
    # Store connection in database
    conn = sqlite3.connect(market_feed.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO connection_metrics
        (client_id, connected_at, subscriptions)
        VALUES (?, ?, ?)
    ''', (client_id, client.connected_at, '[]'))
    conn.commit()
    conn.close()
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get('action')
            
            if action == 'subscribe':
                symbol = data.get('symbol')
                if symbol in market_feed.symbols:
                    if symbol not in market_feed.symbol_subscribers:
                        market_feed.symbol_subscribers[symbol] = set()
                    
                    market_feed.symbol_subscribers[symbol].add(client_id)
                    client.subscriptions.add(symbol)
                    
                    await websocket.send_json({
                        'type': 'subscription_confirmed',
                        'symbol': symbol
                    })
            
            elif action == 'unsubscribe':
                symbol = data.get('symbol')
                if symbol in client.subscriptions:
                    market_feed._remove_client_subscription(client_id, symbol)
                    client.subscriptions.discard(symbol)
                    
                    await websocket.send_json({
                        'type': 'unsubscription_confirmed',
                        'symbol': symbol
                    })
            
            elif action == 'ping':
                await websocket.send_json({'type': 'pong'})
                
    except WebSocketDisconnect:
        # Clean up client
        if client_id in market_feed.active_connections:
            for symbol in list(client.subscriptions):
                market_feed._remove_client_subscription(client_id, symbol)
            
            del market_feed.active_connections[client_id]
            
            # Update database
            conn = sqlite3.connect(market_feed.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE connection_metrics 
                SET disconnected_at = ?
                WHERE client_id = ?
            ''', (time.time(), client_id))
            conn.commit()
            conn.close()

@app.get("/api/market/stats")
async def get_market_stats():
    """Get market statistics"""
    stats = {
        'total_symbols': len(market_feed.symbols),
        'active_connections': len(market_feed.active_connections),
        'total_subscriptions': sum(len(subs) for subs in market_feed.symbol_subscribers.values()),
        'symbols_with_subscribers': len(market_feed.symbol_subscribers)
    }
    
    return {"success": True, "stats": stats}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8503))
    uvicorn.run(app, host="0.0.0.0", port=port)