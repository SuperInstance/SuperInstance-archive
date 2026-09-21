#!/usr/bin/env python3
"""
ActiveLedger Trading Engine
High-performance order matching and market making system
Instance: c5.xlarge
"""

import asyncio
import json
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import redis
import aioredis
from cryptography.fernet import Fernet
import hashlib
import hmac
import os

app = FastAPI(title="ActiveLedger Trading Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class Order:
    id: str
    user_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: Decimal
    price: Decimal
    order_type: str  # 'market' or 'limit'
    timestamp: float
    status: str = 'pending'
    filled_quantity: Decimal = Decimal('0')
    remaining_quantity: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity

@dataclass
class Trade:
    id: str
    buy_order_id: str
    sell_order_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    timestamp: float
    buyer_id: str
    seller_id: str

class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.buy_orders: List[Order] = []  # Sorted by price DESC
        self.sell_orders: List[Order] = []  # Sorted by price ASC
        self.trades: List[Trade] = []
    
    def add_order(self, order: Order) -> List[Trade]:
        trades = []
        
        if order.side == 'buy':
            trades = self._match_buy_order(order)
            if order.remaining_quantity > 0:
                self._insert_buy_order(order)
        else:
            trades = self._match_sell_order(order)
            if order.remaining_quantity > 0:
                self._insert_sell_order(order)
        
        return trades
    
    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        trades = []
        remaining = buy_order.remaining_quantity
        
        while remaining > 0 and self.sell_orders:
            best_sell = self.sell_orders[0]
            
            # Price matching logic
            if buy_order.order_type == 'market' or buy_order.price >= best_sell.price:
                trade_quantity = min(remaining, best_sell.remaining_quantity)
                trade_price = best_sell.price
                
                # Create trade
                trade = Trade(
                    id=str(uuid.uuid4()),
                    buy_order_id=buy_order.id,
                    sell_order_id=best_sell.id,
                    symbol=buy_order.symbol,
                    quantity=trade_quantity,
                    price=trade_price,
                    timestamp=time.time(),
                    buyer_id=buy_order.user_id,
                    seller_id=best_sell.user_id
                )
                
                trades.append(trade)
                self.trades.append(trade)
                
                # Update orders
                buy_order.filled_quantity += trade_quantity
                buy_order.remaining_quantity -= trade_quantity
                remaining -= trade_quantity
                
                best_sell.filled_quantity += trade_quantity
                best_sell.remaining_quantity -= trade_quantity
                
                # Remove filled orders
                if best_sell.remaining_quantity == 0:
                    best_sell.status = 'filled'
                    self.sell_orders.pop(0)
            else:
                break
        
        if buy_order.remaining_quantity == 0:
            buy_order.status = 'filled'
        elif buy_order.filled_quantity > 0:
            buy_order.status = 'partially_filled'
            
        return trades
    
    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        trades = []
        remaining = sell_order.remaining_quantity
        
        while remaining > 0 and self.buy_orders:
            best_buy = self.buy_orders[0]
            
            # Price matching logic
            if sell_order.order_type == 'market' or sell_order.price <= best_buy.price:
                trade_quantity = min(remaining, best_buy.remaining_quantity)
                trade_price = best_buy.price
                
                # Create trade
                trade = Trade(
                    id=str(uuid.uuid4()),
                    buy_order_id=best_buy.id,
                    sell_order_id=sell_order.id,
                    symbol=sell_order.symbol,
                    quantity=trade_quantity,
                    price=trade_price,
                    timestamp=time.time(),
                    buyer_id=best_buy.user_id,
                    seller_id=sell_order.user_id
                )
                
                trades.append(trade)
                self.trades.append(trade)
                
                # Update orders
                sell_order.filled_quantity += trade_quantity
                sell_order.remaining_quantity -= trade_quantity
                remaining -= trade_quantity
                
                best_buy.filled_quantity += trade_quantity
                best_buy.remaining_quantity -= trade_quantity
                
                # Remove filled orders
                if best_buy.remaining_quantity == 0:
                    best_buy.status = 'filled'
                    self.buy_orders.pop(0)
            else:
                break
        
        if sell_order.remaining_quantity == 0:
            sell_order.status = 'filled'
        elif sell_order.filled_quantity > 0:
            sell_order.status = 'partially_filled'
            
        return trades
    
    def _insert_buy_order(self, order: Order):
        # Insert in price-time priority (highest price first, then earliest time)
        for i, existing_order in enumerate(self.buy_orders):
            if order.price > existing_order.price or \
               (order.price == existing_order.price and order.timestamp < existing_order.timestamp):
                self.buy_orders.insert(i, order)
                return
        self.buy_orders.append(order)
    
    def _insert_sell_order(self, order: Order):
        # Insert in price-time priority (lowest price first, then earliest time)
        for i, existing_order in enumerate(self.sell_orders):
            if order.price < existing_order.price or \
               (order.price == existing_order.price and order.timestamp < existing_order.timestamp):
                self.sell_orders.insert(i, order)
                return
        self.sell_orders.append(order)

class TradingEngine:
    def __init__(self):
        self.order_books: Dict[str, OrderBook] = {}
        self.redis_client = None
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    async def initialize_redis(self):
        self.redis_client = await aioredis.from_url("redis://localhost:6379")
    
    def get_order_book(self, symbol: str) -> OrderBook:
        if symbol not in self.order_books:
            self.order_books[symbol] = OrderBook(symbol)
        return self.order_books[symbol]
    
    def validate_order(self, order_data: dict) -> bool:
        """Security validation for orders"""
        required_fields = ['user_id', 'symbol', 'side', 'quantity', 'price', 'order_type']
        
        for field in required_fields:
            if field not in order_data:
                return False
        
        # Validate order parameters
        if order_data['side'] not in ['buy', 'sell']:
            return False
            
        if order_data['order_type'] not in ['market', 'limit']:
            return False
            
        try:
            Decimal(str(order_data['quantity']))
            Decimal(str(order_data['price']))
        except:
            return False
            
        return True
    
    async def process_order(self, order_data: dict) -> dict:
        """Process order with security checks"""
        if not self.validate_order(order_data):
            raise HTTPException(status_code=400, detail="Invalid order data")
        
        # Rate limiting check (implement with Redis)
        user_id = order_data['user_id']
        rate_limit_key = f"rate_limit:{user_id}"
        
        if self.redis_client:
            current_count = await self.redis_client.get(rate_limit_key)
            if current_count and int(current_count) > 100:  # 100 orders per minute
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            await self.redis_client.incr(rate_limit_key)
            await self.redis_client.expire(rate_limit_key, 60)
        
        # Create order
        order = Order(
            id=str(uuid.uuid4()),
            user_id=order_data['user_id'],
            symbol=order_data['symbol'],
            side=order_data['side'],
            quantity=Decimal(str(order_data['quantity'])),
            price=Decimal(str(order_data['price'])),
            order_type=order_data['order_type'],
            timestamp=time.time()
        )
        
        # Process order in order book
        order_book = self.get_order_book(order.symbol)
        trades = order_book.add_order(order)
        
        # Store order and trades in Redis for persistence
        if self.redis_client:
            encrypted_order = self.cipher_suite.encrypt(json.dumps(asdict(order), default=str).encode())
            await self.redis_client.set(f"order:{order.id}", encrypted_order)
            
            for trade in trades:
                encrypted_trade = self.cipher_suite.encrypt(json.dumps(asdict(trade), default=str).encode())
                await self.redis_client.set(f"trade:{trade.id}", encrypted_trade)
        
        return {
            'order': asdict(order),
            'trades': [asdict(trade) for trade in trades]
        }

# Initialize trading engine
trading_engine = TradingEngine()

@app.on_event("startup")
async def startup_event():
    await trading_engine.initialize_redis()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "trading-engine"}

@app.post("/api/orders")
async def place_order(order_data: dict):
    """Place a new order"""
    try:
        result = await trading_engine.process_order(order_data)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/orderbook/{symbol}")
async def get_order_book(symbol: str):
    """Get current order book for a symbol"""
    order_book = trading_engine.get_order_book(symbol)
    return {
        "symbol": symbol,
        "buy_orders": [asdict(order) for order in order_book.buy_orders[:10]],
        "sell_orders": [asdict(order) for order in order_book.sell_orders[:10]],
        "last_trade": asdict(order_book.trades[-1]) if order_book.trades else None
    }

@app.get("/api/trades/{symbol}")
async def get_trades(symbol: str, limit: int = 50):
    """Get recent trades for a symbol"""
    order_book = trading_engine.get_order_book(symbol)
    trades = order_book.trades[-limit:] if len(order_book.trades) >= limit else order_book.trades
    return {"symbol": symbol, "trades": [asdict(trade) for trade in trades]}

# WebSocket for real-time market data
active_connections: List[WebSocket] = []

@app.websocket("/ws/market-data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_trade(trade: Trade):
    """Broadcast trade to all connected clients"""
    message = {
        "type": "trade",
        "data": asdict(trade)
    }
    
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        active_connections.remove(connection)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8500))
    uvicorn.run(app, host="0.0.0.0", port=port)