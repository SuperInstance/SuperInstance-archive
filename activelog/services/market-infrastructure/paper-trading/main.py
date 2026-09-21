#!/usr/bin/env python3
"""
Paper Trading System
Port: 8445

Advanced paper trading platform with:
- Real-time market simulation
- Portfolio management
- Risk analytics
- Backtesting engine
- Educational tools
- Multi-asset support
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import random
import math

from ..models.market_types import (
    Asset, MarketData, TradingOrder, Position, Portfolio, Trade,
    TraderProfile, TradeType, OrderType, OrderStatus, AssetType,
    TechnicalIndicator, RiskMetrics, BacktestResult,
    create_sample_asset, create_sample_market_data, create_sample_trading_order,
    create_sample_portfolio, create_sample_trader_profile
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaperTradingSystem:
    def __init__(self, port: int = 8445):
        self.port = port
        self.app = FastAPI(title="Paper Trading System")
        self.traders: Dict[str, TraderProfile] = {}
        self.portfolios: Dict[str, Portfolio] = {}
        self.orders: Dict[str, TradingOrder] = {}
        self.trades: Dict[str, Trade] = {}
        self.assets: Dict[str, Asset] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.websocket_connections: List[WebSocket] = []
        self.market_session_active = True
        
        self._setup_routes()
        self._setup_middleware()
        self._initialize_market_data()
        
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _initialize_market_data(self):
        """Initialize market with sample assets and data"""
        # Initialize popular assets
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "SPY", "QQQ", "BTC"]
        base_prices = [150, 2500, 300, 130, 200, 450, 280, 400, 350, 45000]
        
        for symbol, base_price in zip(symbols, base_prices):
            asset = create_sample_asset(symbol)
            self.assets[symbol] = asset
            
            market_data = create_sample_market_data(symbol, base_price)
            self.market_data[symbol] = market_data
        
        logger.info(f"Initialized market data for {len(self.assets)} assets")
    
    def _setup_routes(self):
        
        @self.app.get("/")
        async def root():
            active_traders = len([t for t in self.traders.values() if t.is_active])
            total_portfolios = len(self.portfolios)
            total_trades_today = len([t for t in self.trades.values() 
                                   if t.timestamp.date() == datetime.now().date()])
            
            return {
                "system": "Paper Trading System",
                "version": "1.0.0",
                "market_session_active": self.market_session_active,
                "active_traders": active_traders,
                "total_portfolios": total_portfolios,
                "trades_today": total_trades_today,
                "available_assets": len(self.assets),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Trader Management Routes
        @self.app.post("/traders")
        async def register_trader(trader_data: dict):
            trader_id = await self._register_trader(trader_data)
            
            if trader_id:
                await self._broadcast_update("trader_registered", {
                    "trader_id": trader_id,
                    "username": trader_data.get("username")
                })
                return {"trader_id": trader_id, "status": "registered"}
            else:
                raise HTTPException(status_code=400, detail="Failed to register trader")
        
        @self.app.get("/traders/{trader_id}")
        async def get_trader_profile(trader_id: str):
            if trader_id not in self.traders:
                raise HTTPException(status_code=404, detail="Trader not found")
            
            trader = self.traders[trader_id]
            profile = {
                "trader_id": trader.trader_id,
                "username": trader.username,
                "email": trader.email,
                "registration_date": trader.registration_date.isoformat(),
                "experience_level": trader.experience_level,
                "trading_style": trader.trading_style,
                "total_trades": trader.total_trades,
                "win_rate": trader.win_rate,
                "best_trade": float(trader.best_trade) if trader.best_trade else None,
                "worst_trade": float(trader.worst_trade) if trader.worst_trade else None,
                "is_active": trader.is_active
            }
            
            return profile
        
        # Portfolio Management Routes
        @self.app.post("/portfolios")
        async def create_portfolio(portfolio_data: dict):
            portfolio_id = await self._create_portfolio(portfolio_data)
            
            if portfolio_id:
                return {"portfolio_id": portfolio_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create portfolio")
        
        @self.app.get("/portfolios/{portfolio_id}")
        async def get_portfolio(portfolio_id: str):
            if portfolio_id not in self.portfolios:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            portfolio = self.portfolios[portfolio_id]
            
            # Update positions with current market prices
            await self._update_portfolio_values(portfolio_id)
            
            portfolio_data = {
                "portfolio_id": portfolio.portfolio_id,
                "trader_id": portfolio.trader_id,
                "name": portfolio.name,
                "cash_balance": float(portfolio.cash_balance),
                "total_value": float(portfolio.total_value),
                "daily_pnl": float(portfolio.daily_pnl),
                "total_pnl": float(portfolio.total_pnl),
                "positions": {},
                "created_at": portfolio.created_at.isoformat(),
                "last_updated": portfolio.last_updated.isoformat()
            }
            
            # Include position details
            for symbol, position in portfolio.positions.items():
                portfolio_data["positions"][symbol] = {
                    "symbol": symbol,
                    "quantity": position.quantity,
                    "average_price": float(position.average_price),
                    "current_price": float(position.current_price),
                    "unrealized_pnl": float(position.unrealized_pnl),
                    "realized_pnl": float(position.realized_pnl),
                    "market_value": float(position.market_value)
                }
            
            return portfolio_data
        
        @self.app.get("/traders/{trader_id}/portfolios")
        async def get_trader_portfolios(trader_id: str):
            if trader_id not in self.traders:
                raise HTTPException(status_code=404, detail="Trader not found")
            
            trader_portfolios = [
                portfolio for portfolio in self.portfolios.values()
                if portfolio.trader_id == trader_id
            ]
            
            portfolios_data = []
            for portfolio in trader_portfolios:
                await self._update_portfolio_values(portfolio.portfolio_id)
                portfolios_data.append({
                    "portfolio_id": portfolio.portfolio_id,
                    "name": portfolio.name,
                    "cash_balance": float(portfolio.cash_balance),
                    "total_value": float(portfolio.total_value),
                    "daily_pnl": float(portfolio.daily_pnl),
                    "total_pnl": float(portfolio.total_pnl),
                    "positions_count": len(portfolio.positions)
                })
            
            return {"portfolios": portfolios_data}
        
        # Trading Routes
        @self.app.post("/orders")
        async def place_order(order_data: dict):
            order_id = await self._place_order(order_data)
            
            if order_id:
                await self._broadcast_update("order_placed", {
                    "order_id": order_id,
                    "symbol": order_data.get("symbol"),
                    "trade_type": order_data.get("trade_type"),
                    "quantity": order_data.get("quantity")
                })
                return {"order_id": order_id, "status": "placed"}
            else:
                raise HTTPException(status_code=400, detail="Failed to place order")
        
        @self.app.get("/orders/{order_id}")
        async def get_order_status(order_id: str):
            if order_id not in self.orders:
                raise HTTPException(status_code=404, detail="Order not found")
            
            order = self.orders[order_id]
            return {
                "order_id": order.order_id,
                "trader_id": order.trader_id,
                "symbol": order.symbol,
                "trade_type": order.trade_type.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": float(order.price) if order.price else None,
                "status": order.status.value,
                "created_at": order.created_at.isoformat(),
                "executed_at": order.executed_at.isoformat() if order.executed_at else None,
                "filled_quantity": order.filled_quantity,
                "average_fill_price": float(order.average_fill_price) if order.average_fill_price else None
            }
        
        @self.app.get("/traders/{trader_id}/orders")
        async def get_trader_orders(trader_id: str, status: Optional[str] = None):
            trader_orders = [
                order for order in self.orders.values()
                if order.trader_id == trader_id
            ]
            
            if status:
                trader_orders = [
                    order for order in trader_orders
                    if order.status.value == status
                ]
            
            orders_data = []
            for order in trader_orders:
                orders_data.append({
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "trade_type": order.trade_type.value,
                    "order_type": order.order_type.value,
                    "quantity": order.quantity,
                    "price": float(order.price) if order.price else None,
                    "status": order.status.value,
                    "created_at": order.created_at.isoformat()
                })
            
            return {"orders": orders_data}
        
        @self.app.delete("/orders/{order_id}")
        async def cancel_order(order_id: str):
            if order_id not in self.orders:
                raise HTTPException(status_code=404, detail="Order not found")
            
            order = self.orders[order_id]
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                raise HTTPException(status_code=400, detail="Cannot cancel filled or already cancelled order")
            
            order.status = OrderStatus.CANCELLED
            
            await self._broadcast_update("order_cancelled", {
                "order_id": order_id,
                "symbol": order.symbol
            })
            
            return {"status": "cancelled"}
        
        # Market Data Routes
        @self.app.get("/market/assets")
        async def get_assets():
            assets_data = []
            for symbol, asset in self.assets.items():
                current_data = self.market_data.get(symbol)
                assets_data.append({
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "asset_type": asset.asset_type.value,
                    "exchange": asset.exchange,
                    "sector": asset.sector,
                    "current_price": float(current_data.price) if current_data else None,
                    "change_percent": current_data.change_percent if current_data else None
                })
            
            return {"assets": assets_data}
        
        @self.app.get("/market/data/{symbol}")
        async def get_market_data(symbol: str):
            if symbol not in self.market_data:
                raise HTTPException(status_code=404, detail="Symbol not found")
            
            data = self.market_data[symbol]
            return {
                "symbol": data.symbol,
                "timestamp": data.timestamp.isoformat(),
                "price": float(data.price),
                "bid": float(data.bid) if data.bid else None,
                "ask": float(data.ask) if data.ask else None,
                "volume": data.volume,
                "high": float(data.high) if data.high else None,
                "low": float(data.low) if data.low else None,
                "open": float(data.open_price) if data.open_price else None,
                "previous_close": float(data.previous_close) if data.previous_close else None,
                "change": float(data.change) if data.change else None,
                "change_percent": data.change_percent
            }
        
        @self.app.get("/market/quotes")
        async def get_market_quotes(symbols: Optional[str] = None):
            if symbols:
                symbol_list = symbols.split(",")
                filtered_data = {k: v for k, v in self.market_data.items() if k in symbol_list}
            else:
                filtered_data = self.market_data
            
            quotes = {}
            for symbol, data in filtered_data.items():
                quotes[symbol] = {
                    "price": float(data.price),
                    "change_percent": data.change_percent,
                    "volume": data.volume,
                    "timestamp": data.timestamp.isoformat()
                }
            
            return {"quotes": quotes}
        
        # Analytics Routes
        @self.app.get("/analytics/portfolio/{portfolio_id}/risk")
        async def get_portfolio_risk_metrics(portfolio_id: str):
            if portfolio_id not in self.portfolios:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            risk_metrics = await self._calculate_risk_metrics(portfolio_id)
            return risk_metrics
        
        @self.app.get("/analytics/trader/{trader_id}/performance")
        async def get_trader_performance(trader_id: str):
            if trader_id not in self.traders:
                raise HTTPException(status_code=404, detail="Trader not found")
            
            performance = await self._calculate_trader_performance(trader_id)
            return performance
        
        # Backtesting Routes
        @self.app.post("/backtesting/run")
        async def run_backtest(backtest_data: dict, background_tasks: BackgroundTasks):
            backtest_id = f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(self._run_backtest, backtest_id, backtest_data)
            
            return {"backtest_id": backtest_id, "status": "initiated"}
        
        # WebSocket for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    logger.info(f"Received websocket message: {data}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.remove(websocket)
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "market_session_active": self.market_session_active,
                "traders": len(self.traders),
                "portfolios": len(self.portfolios),
                "active_orders": len([o for o in self.orders.values() 
                                   if o.status == OrderStatus.PENDING]),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _register_trader(self, trader_data: dict) -> Optional[str]:
        """Register new trader"""
        try:
            trader_id = f"trader_{len(self.traders)+1:06d}"
            
            trader = TraderProfile(
                trader_id=trader_id,
                username=trader_data["username"],
                email=trader_data["email"],
                experience_level=trader_data.get("experience_level", "beginner"),
                trading_style=trader_data.get("trading_style", "conservative"),
                preferred_assets=[AssetType(asset) for asset in trader_data.get("preferred_assets", ["stock"])],
                risk_management_rules=trader_data.get("risk_management_rules", {})
            )
            
            self.traders[trader_id] = trader
            
            # Create default portfolio
            portfolio_data = {
                "trader_id": trader_id,
                "name": "Main Portfolio",
                "initial_balance": trader_data.get("initial_balance", 100000)
            }
            await self._create_portfolio(portfolio_data)
            
            logger.info(f"Registered trader: {trader.username} ({trader_id})")
            return trader_id
            
        except Exception as e:
            logger.error(f"Failed to register trader: {e}")
            return None
    
    async def _create_portfolio(self, portfolio_data: dict) -> Optional[str]:
        """Create new portfolio"""
        try:
            trader_id = portfolio_data["trader_id"]
            portfolio_id = f"portfolio_{trader_id}_{len([p for p in self.portfolios.values() if p.trader_id == trader_id])+1}"
            
            initial_balance = Decimal(str(portfolio_data.get("initial_balance", 100000)))
            
            portfolio = Portfolio(
                portfolio_id=portfolio_id,
                trader_id=trader_id,
                name=portfolio_data.get("name", "Portfolio"),
                cash_balance=initial_balance,
                total_value=initial_balance
            )
            
            self.portfolios[portfolio_id] = portfolio
            
            logger.info(f"Created portfolio: {portfolio.name} ({portfolio_id}) with ${initial_balance}")
            return portfolio_id
            
        except Exception as e:
            logger.error(f"Failed to create portfolio: {e}")
            return None
    
    async def _place_order(self, order_data: dict) -> Optional[str]:
        """Place trading order"""
        try:
            trader_id = order_data["trader_id"]
            symbol = order_data["symbol"].upper()
            
            if trader_id not in self.traders:
                logger.error(f"Trader not found: {trader_id}")
                return None
            
            if symbol not in self.assets:
                logger.error(f"Asset not found: {symbol}")
                return None
            
            order_id = f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.orders)+1:04d}"
            
            order = TradingOrder(
                order_id=order_id,
                trader_id=trader_id,
                symbol=symbol,
                trade_type=TradeType(order_data["trade_type"]),
                order_type=OrderType(order_data.get("order_type", "market")),
                quantity=int(order_data["quantity"]),
                price=Decimal(str(order_data["price"])) if order_data.get("price") else None,
                stop_price=Decimal(str(order_data["stop_price"])) if order_data.get("stop_price") else None
            )
            
            self.orders[order_id] = order
            
            # Try to execute immediately if market order
            if order.order_type == OrderType.MARKET and self.market_session_active:
                await self._execute_order(order_id)
            
            logger.info(f"Placed order: {order.trade_type.value} {order.quantity} {symbol} for {trader_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
    
    async def _execute_order(self, order_id: str) -> bool:
        """Execute trading order"""
        try:
            order = self.orders[order_id]
            
            if order.status != OrderStatus.PENDING:
                return False
            
            symbol = order.symbol
            current_data = self.market_data.get(symbol)
            
            if not current_data:
                order.status = OrderStatus.REJECTED
                return False
            
            # Determine execution price
            if order.order_type == OrderType.MARKET:
                execution_price = current_data.price
            else:
                # For limit orders, check if price conditions are met
                if order.trade_type in [TradeType.BUY, TradeType.COVER]:
                    if order.price and current_data.price <= order.price:
                        execution_price = order.price
                    else:
                        return False  # Limit not met
                else:  # SELL or SHORT
                    if order.price and current_data.price >= order.price:
                        execution_price = order.price
                    else:
                        return False  # Limit not met
            
            # Find trader's portfolio (use first portfolio for simplicity)
            trader_portfolios = [p for p in self.portfolios.values() if p.trader_id == order.trader_id]
            if not trader_portfolios:
                order.status = OrderStatus.REJECTED
                return False
            
            portfolio = trader_portfolios[0]
            
            # Calculate total cost including commission
            commission = Decimal("9.99")  # Fixed commission for demo
            total_cost = execution_price * order.quantity + commission
            
            # Check if trader has sufficient funds for buy orders
            if order.trade_type in [TradeType.BUY, TradeType.COVER]:
                if portfolio.cash_balance < total_cost:
                    order.status = OrderStatus.REJECTED
                    return False
            
            # Execute the trade
            order.status = OrderStatus.FILLED
            order.executed_at = datetime.now(timezone.utc)
            order.filled_quantity = order.quantity
            order.average_fill_price = execution_price
            order.commission = commission
            
            # Create trade record
            trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.trades)+1:04d}"
            trade = Trade(
                trade_id=trade_id,
                order_id=order_id,
                trader_id=order.trader_id,
                symbol=symbol,
                trade_type=order.trade_type,
                quantity=order.quantity,
                price=execution_price,
                timestamp=datetime.now(timezone.utc),
                commission=commission,
                total_cost=total_cost,
                portfolio_id=portfolio.portfolio_id
            )
            
            self.trades[trade_id] = trade
            
            # Update portfolio
            await self._update_portfolio_from_trade(portfolio.portfolio_id, trade)
            
            # Update trader statistics
            trader = self.traders[order.trader_id]
            trader.total_trades += 1
            
            logger.info(f"Executed order: {order_id} - {order.trade_type.value} {order.quantity} {symbol} at ${execution_price}")
            
            await self._broadcast_update("order_executed", {
                "order_id": order_id,
                "trade_id": trade_id,
                "symbol": symbol,
                "price": float(execution_price),
                "quantity": order.quantity
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute order {order_id}: {e}")
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.REJECTED
            return False
    
    async def _update_portfolio_from_trade(self, portfolio_id: str, trade: Trade):
        """Update portfolio positions and balances from trade"""
        portfolio = self.portfolios[portfolio_id]
        symbol = trade.symbol
        
        # Update cash balance
        if trade.trade_type in [TradeType.BUY, TradeType.COVER]:
            portfolio.cash_balance -= trade.total_cost
        else:  # SELL or SHORT
            portfolio.cash_balance += trade.total_cost - trade.commission
        
        # Update position
        if symbol not in portfolio.positions:
            # Create new position
            portfolio.positions[symbol] = Position(
                position_id=f"pos_{portfolio_id}_{symbol}",
                trader_id=trade.trader_id,
                symbol=symbol,
                quantity=0,
                average_price=Decimal("0"),
                current_price=trade.price,
                unrealized_pnl=Decimal("0")
            )
        
        position = portfolio.positions[symbol]
        
        if trade.trade_type == TradeType.BUY:
            # Calculate new average price
            if position.quantity > 0:
                total_cost = position.average_price * position.quantity + trade.price * trade.quantity
                total_quantity = position.quantity + trade.quantity
                position.average_price = total_cost / total_quantity
            else:
                position.average_price = trade.price
            
            position.quantity += trade.quantity
            
        elif trade.trade_type == TradeType.SELL:
            if position.quantity >= trade.quantity:
                # Calculate realized P&L
                realized_pnl = (trade.price - position.average_price) * trade.quantity
                position.realized_pnl += realized_pnl
                position.quantity -= trade.quantity
                
                if position.quantity == 0:
                    position.average_price = Decimal("0")
            
        # Update market value and unrealized P&L
        position.current_price = trade.price
        position.market_value = position.current_price * position.quantity
        position.unrealized_pnl = (position.current_price - position.average_price) * position.quantity
        position.last_updated = datetime.now(timezone.utc)
        
        # Update portfolio totals
        await self._update_portfolio_values(portfolio_id)
    
    async def _update_portfolio_values(self, portfolio_id: str):
        """Update portfolio total values with current market prices"""
        portfolio = self.portfolios[portfolio_id]
        
        total_market_value = Decimal("0")
        total_unrealized_pnl = Decimal("0")
        total_realized_pnl = Decimal("0")
        
        for symbol, position in portfolio.positions.items():
            # Update position with current market price
            if symbol in self.market_data:
                current_price = self.market_data[symbol].price
                position.current_price = current_price
                position.market_value = current_price * position.quantity
                position.unrealized_pnl = (current_price - position.average_price) * position.quantity
                position.last_updated = datetime.now(timezone.utc)
            
            total_market_value += position.market_value
            total_unrealized_pnl += position.unrealized_pnl
            total_realized_pnl += position.realized_pnl
        
        portfolio.total_value = portfolio.cash_balance + total_market_value
        portfolio.total_pnl = total_unrealized_pnl + total_realized_pnl
        portfolio.last_updated = datetime.now(timezone.utc)
    
    async def _calculate_risk_metrics(self, portfolio_id: str) -> dict:
        """Calculate risk metrics for portfolio"""
        portfolio = self.portfolios[portfolio_id]
        
        # Simplified risk calculations for demo
        total_value = float(portfolio.total_value)
        
        # Portfolio concentration risk
        position_values = [float(pos.market_value) for pos in portfolio.positions.values()]
        max_position = max(position_values) if position_values else 0
        concentration_risk = (max_position / total_value) * 100 if total_value > 0 else 0
        
        # Simulated volatility and risk metrics
        portfolio_volatility = random.uniform(15, 25)  # Simulated annual volatility
        var_95 = total_value * 0.05 * (portfolio_volatility / 100) * math.sqrt(1/252)  # Daily VaR
        
        return {
            "portfolio_id": portfolio_id,
            "total_value": total_value,
            "portfolio_volatility": portfolio_volatility,
            "concentration_risk": concentration_risk,
            "var_95_daily": var_95,
            "positions_count": len(portfolio.positions),
            "cash_percentage": (float(portfolio.cash_balance) / total_value) * 100 if total_value > 0 else 100,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    async def _calculate_trader_performance(self, trader_id: str) -> dict:
        """Calculate trader performance metrics"""
        trader = self.traders[trader_id]
        
        # Get trader's trades
        trader_trades = [trade for trade in self.trades.values() if trade.trader_id == trader_id]
        
        if not trader_trades:
            return {"message": "No trades found for trader"}
        
        # Calculate basic metrics
        total_trades = len(trader_trades)
        
        # Get trader's portfolios
        trader_portfolios = [p for p in self.portfolios.values() if p.trader_id == trader_id]
        total_pnl = sum(float(p.total_pnl) for p in trader_portfolios)
        
        # Simulated additional metrics
        win_rate = random.uniform(40, 70)  # Simulated win rate
        avg_trade_size = sum(float(t.total_cost) for t in trader_trades) / total_trades if total_trades > 0 else 0
        
        return {
            "trader_id": trader_id,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "average_trade_size": avg_trade_size,
            "experience_level": trader.experience_level,
            "trading_style": trader.trading_style,
            "registration_date": trader.registration_date.isoformat(),
            "is_active": trader.is_active
        }
    
    async def _run_backtest(self, backtest_id: str, backtest_data: dict):
        """Run backtesting strategy (background task)"""
        try:
            logger.info(f"Starting backtest: {backtest_id}")
            
            # Simulate backtest execution
            await asyncio.sleep(5)  # Simulate processing time
            
            # Generate simulated results
            initial_capital = Decimal(str(backtest_data.get("initial_capital", 100000)))
            final_value = initial_capital * Decimal(str(random.uniform(0.8, 1.5)))  # Random performance
            total_return = float((final_value - initial_capital) / initial_capital * 100)
            
            backtest_result = BacktestResult(
                backtest_id=backtest_id,
                strategy_name=backtest_data.get("strategy_name", "Custom Strategy"),
                start_date=datetime.fromisoformat(backtest_data.get("start_date", "2023-01-01")),
                end_date=datetime.fromisoformat(backtest_data.get("end_date", "2024-01-01")),
                initial_capital=initial_capital,
                final_value=final_value,
                total_return=total_return,
                annualized_return=total_return,  # Simplified
                max_drawdown=random.uniform(5, 20),
                sharpe_ratio=random.uniform(0.5, 2.0),
                win_rate=random.uniform(45, 65),
                total_trades=random.randint(50, 200),
                profit_factor=random.uniform(1.1, 2.5)
            )
            
            await self._broadcast_update("backtest_completed", {
                "backtest_id": backtest_id,
                "total_return": total_return,
                "sharpe_ratio": backtest_result.sharpe_ratio
            })
            
            logger.info(f"Completed backtest: {backtest_id} with {total_return:.2f}% return")
            
        except Exception as e:
            logger.error(f"Backtest failed {backtest_id}: {e}")
    
    async def start_market_simulation(self):
        """Start market data simulation and order processing loops"""
        asyncio.create_task(self._market_data_simulation_loop())
        asyncio.create_task(self._order_processing_loop())
        asyncio.create_task(self._portfolio_update_loop())
        
        logger.info("Started paper trading simulation loops")
    
    async def _market_data_simulation_loop(self):
        """Simulate real-time market data updates"""
        while True:
            try:
                if self.market_session_active:
                    for symbol, data in self.market_data.items():
                        # Simulate price movement (random walk)
                        change_percent = random.uniform(-0.02, 0.02)  # ±2% max change
                        new_price = data.price * (Decimal("1") + Decimal(str(change_percent)))
                        
                        # Update market data
                        data.price = new_price.quantize(Decimal("0.01"))
                        data.timestamp = datetime.now(timezone.utc)
                        data.change = new_price - (data.previous_close or new_price)
                        data.change_percent = float(data.change / (data.previous_close or new_price) * 100) if data.previous_close else 0
                        data.volume += random.randint(1000, 10000)
                    
                    # Broadcast market update every 5 seconds
                    if len(self.websocket_connections) > 0:
                        sample_quotes = {
                            symbol: {"price": float(data.price), "change_percent": data.change_percent}
                            for symbol, data in list(self.market_data.items())[:5]
                        }
                        
                        await self._broadcast_update("market_data_update", {
                            "quotes": sample_quotes
                        })
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Market simulation error: {e}")
                await asyncio.sleep(10)
    
    async def _order_processing_loop(self):
        """Process pending orders"""
        while True:
            try:
                pending_orders = [
                    order for order in self.orders.values()
                    if order.status == OrderStatus.PENDING
                ]
                
                for order in pending_orders:
                    if order.order_type != OrderType.MARKET:  # Market orders are executed immediately
                        await self._execute_order(order.order_id)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Order processing error: {e}")
                await asyncio.sleep(5)
    
    async def _portfolio_update_loop(self):
        """Update portfolio values periodically"""
        while True:
            try:
                for portfolio_id in self.portfolios.keys():
                    await self._update_portfolio_values(portfolio_id)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Portfolio update error: {e}")
                await asyncio.sleep(60)
    
    async def _broadcast_update(self, event_type: str, data: dict):
        if not self.websocket_connections:
            return
        
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    def run(self):
        """Start the paper trading system"""
        logger.info(f"Starting Paper Trading System on port {self.port}")
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )

async def main():
    system = PaperTradingSystem()
    
    # Start market simulation
    await system.start_market_simulation()
    
    # This would typically be called by uvicorn
    # system.run()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        # Development mode with asyncio
        asyncio.run(main())
    else:
        # Production mode with uvicorn
        PaperTradingSystem().run()