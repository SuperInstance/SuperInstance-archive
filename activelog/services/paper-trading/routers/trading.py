from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import sqlite3
import uuid
import json
import random

router = APIRouter()

# Pydantic models
class TradeOrder(BaseModel):
    symbol: str
    asset_type: str  # stock, crypto, forex, option, future, commodity, etf
    action: str  # buy, sell, short, cover
    quantity: float
    order_type: str = "market"  # market, limit, stop, stop_limit
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"  # day, gtc, ioc, fok
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    order_id: str
    status: str
    executed_price: float
    executed_quantity: float
    commission: float
    total_cost: float
    timestamp: datetime

class PositionInfo(BaseModel):
    symbol: str
    asset_type: str
    quantity: float
    average_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    day_change: float
    day_change_percent: float

class TradingAccount(BaseModel):
    account_id: str
    cash_balance: float
    buying_power: float
    portfolio_value: float
    day_change: float
    day_change_percent: float
    positions: List[PositionInfo]

# Commission structure
COMMISSION_STRUCTURE = {
    "stock": 0.0,  # Commission-free stocks
    "etf": 0.0,    # Commission-free ETFs
    "option": 0.65,  # Per contract
    "crypto": 0.005,  # 0.5% of trade value
    "forex": 0.0001,  # 1 pip spread
    "future": 2.25,   # Per contract
    "commodity": 2.50  # Per contract
}

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('paper_trading.db')

def calculate_commission(asset_type: str, quantity: float, price: float) -> float:
    """Calculate trading commission based on asset type"""
    if asset_type in ["stock", "etf"]:
        return 0.0  # Commission-free
    elif asset_type == "option":
        return COMMISSION_STRUCTURE["option"] * quantity
    elif asset_type == "crypto":
        return price * quantity * COMMISSION_STRUCTURE["crypto"]
    elif asset_type in ["forex", "future", "commodity"]:
        return COMMISSION_STRUCTURE.get(asset_type, 0.0) * quantity
    else:
        return 0.0

def simulate_slippage(price: float, order_type: str, action: str, quantity: float) -> float:
    """Simulate realistic price slippage for market orders"""
    if order_type != "market":
        return price
    
    # Base slippage: 0.01% to 0.05% depending on order size
    base_slippage = 0.0001 + (min(quantity, 10000) / 10000) * 0.0004
    
    # Add random component
    slippage_factor = 1 + random.uniform(-base_slippage, base_slippage)
    
    # Apply directional slippage (worse for trader)
    if action in ["buy", "cover"]:
        slippage_factor = max(slippage_factor, 1.0)  # Price goes up
    else:  # sell, short
        slippage_factor = min(slippage_factor, 1.0)  # Price goes down
    
    return price * slippage_factor

def get_current_price(symbol: str, asset_type: str) -> float:
    """Get current price for a symbol"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if it's an ActiveLog ecosystem company
    if asset_type == "activelog":
        cursor.execute('SELECT current_price FROM activelog_companies WHERE symbol = ?', (symbol,))
        result = cursor.fetchone()
        if result:
            conn.close()
            return float(result[0])
    
    # Check market data cache
    cursor.execute('SELECT current_price FROM market_data WHERE symbol = ? AND asset_type = ?', 
                  (symbol, asset_type))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return float(result[0])
    else:
        # Return a simulated price if not in cache
        # This would be replaced with actual API calls
        if asset_type == "crypto":
            return random.uniform(100, 50000)  # Crypto price range
        elif asset_type == "forex":
            return random.uniform(0.5, 2.0)    # Forex rate range
        else:
            return random.uniform(10, 500)     # Stock price range

@router.post("/place-order", response_model=OrderResponse)
async def place_order(order: TradeOrder, portfolio_id: str):
    """Place a paper trading order"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Validate portfolio exists and get current cash balance
        cursor.execute('SELECT current_cash FROM portfolios WHERE portfolio_id = ?', (portfolio_id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        current_cash = float(result[0])
        
        # Get current market price
        current_price = get_current_price(order.symbol, order.asset_type)
        
        # Determine execution price based on order type
        if order.order_type == "market":
            execution_price = simulate_slippage(current_price, "market", order.action, order.quantity)
        elif order.order_type == "limit":
            if order.limit_price is None:
                raise HTTPException(status_code=400, detail="Limit price required for limit orders")
            execution_price = order.limit_price
            
            # Check if limit order would execute immediately
            if order.action in ["buy", "cover"] and current_price > order.limit_price:
                raise HTTPException(status_code=400, detail="Limit order would not execute at current market price")
            if order.action in ["sell", "short"] and current_price < order.limit_price:
                raise HTTPException(status_code=400, detail="Limit order would not execute at current market price")
        else:
            # For stop orders, use current price for now (simplified)
            execution_price = current_price
        
        # Calculate commission
        commission = calculate_commission(order.asset_type, order.quantity, execution_price)
        
        # Calculate total cost/proceeds
        if order.action in ["buy", "cover"]:
            total_amount = (execution_price * order.quantity) + commission
            if total_amount > current_cash:
                raise HTTPException(status_code=400, detail="Insufficient buying power")
            new_cash = current_cash - total_amount
        else:  # sell, short
            total_amount = (execution_price * order.quantity) - commission
            new_cash = current_cash + total_amount
        
        # Create transaction record
        transaction_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (transaction_id, portfolio_id, symbol, asset_type, action, quantity, price, 
             commission, total_amount, order_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, portfolio_id, order.symbol, order.asset_type, order.action,
              order.quantity, execution_price, commission, total_amount, order.order_type, order.notes))
        
        # Update portfolio cash balance
        cursor.execute('UPDATE portfolios SET current_cash = ? WHERE portfolio_id = ?', 
                      (new_cash, portfolio_id))
        
        # Update or create holding
        if order.action in ["buy", "cover"]:
            # Check if holding exists
            cursor.execute('SELECT holding_id, quantity, average_cost FROM holdings WHERE portfolio_id = ? AND symbol = ? AND asset_type = ?',
                          (portfolio_id, order.symbol, order.asset_type))
            existing_holding = cursor.fetchone()
            
            if existing_holding:
                holding_id, existing_quantity, existing_avg_cost = existing_holding
                
                if order.action == "buy":
                    # Add to existing position
                    new_quantity = existing_quantity + order.quantity
                    new_avg_cost = ((existing_quantity * existing_avg_cost) + (order.quantity * execution_price)) / new_quantity
                else:  # cover short position
                    new_quantity = existing_quantity + order.quantity  # Should move toward zero
                    if new_quantity > 0:
                        new_avg_cost = execution_price  # Reset cost basis after covering
                    else:
                        new_avg_cost = existing_avg_cost
                
                cursor.execute('''
                    UPDATE holdings SET quantity = ?, average_cost = ?, current_price = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE holding_id = ?
                ''', (new_quantity, new_avg_cost, current_price, holding_id))
            else:
                # Create new holding
                holding_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO holdings 
                    (holding_id, portfolio_id, symbol, asset_type, quantity, average_cost, current_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (holding_id, portfolio_id, order.symbol, order.asset_type, order.quantity, execution_price, current_price))
        
        else:  # sell, short
            cursor.execute('SELECT holding_id, quantity, average_cost FROM holdings WHERE portfolio_id = ? AND symbol = ? AND asset_type = ?',
                          (portfolio_id, order.symbol, order.asset_type))
            existing_holding = cursor.fetchone()
            
            if existing_holding:
                holding_id, existing_quantity, existing_avg_cost = existing_holding
                new_quantity = existing_quantity - order.quantity
                
                if abs(new_quantity) < 0.0001:  # Position closed
                    cursor.execute('DELETE FROM holdings WHERE holding_id = ?', (holding_id,))
                else:
                    cursor.execute('''
                        UPDATE holdings SET quantity = ?, current_price = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE holding_id = ?
                    ''', (new_quantity, current_price, holding_id))
            else:
                # Create short position
                if order.action == "short":
                    holding_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO holdings 
                        (holding_id, portfolio_id, symbol, asset_type, quantity, average_cost, current_price)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (holding_id, portfolio_id, order.symbol, order.asset_type, -order.quantity, execution_price, current_price))
        
        conn.commit()
        
        return OrderResponse(
            order_id=transaction_id,
            status="filled",
            executed_price=execution_price,
            executed_quantity=order.quantity,
            commission=commission,
            total_cost=total_amount,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Order execution failed: {str(e)}")
    finally:
        conn.close()

@router.get("/account/{portfolio_id}", response_model=TradingAccount)
async def get_trading_account(portfolio_id: str):
    """Get trading account information including positions and cash balance"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get portfolio information
    cursor.execute('SELECT current_cash, total_value, day_change, day_change_percent FROM portfolios WHERE portfolio_id = ?', 
                  (portfolio_id,))
    portfolio_data = cursor.fetchone()
    if not portfolio_data:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    cash_balance, total_value, day_change, day_change_percent = portfolio_data
    
    # Get all holdings
    cursor.execute('''
        SELECT symbol, asset_type, quantity, average_cost, current_price, market_value, 
               total_return, total_return_percent, day_change, day_change_percent
        FROM holdings WHERE portfolio_id = ?
    ''', (portfolio_id,))
    holdings = cursor.fetchall()
    
    positions = []
    for holding in holdings:
        symbol, asset_type, quantity, avg_cost, current_price, market_value, total_return, total_return_pct, day_chg, day_chg_pct = holding
        
        # Update current price and recalculate values
        current_price = get_current_price(symbol, asset_type)
        market_value = quantity * current_price
        unrealized_pnl = market_value - (quantity * avg_cost)
        unrealized_pnl_percent = (unrealized_pnl / (quantity * avg_cost)) * 100 if avg_cost > 0 else 0
        
        positions.append(PositionInfo(
            symbol=symbol,
            asset_type=asset_type,
            quantity=quantity,
            average_cost=avg_cost,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_percent=unrealized_pnl_percent,
            day_change=day_chg or 0,
            day_change_percent=day_chg_pct or 0
        ))
    
    # Calculate buying power (simplified - cash + margin if enabled)
    buying_power = cash_balance * 2  # 2:1 margin for demonstration
    
    conn.close()
    
    return TradingAccount(
        account_id=portfolio_id,
        cash_balance=cash_balance,
        buying_power=buying_power,
        portfolio_value=total_value,
        day_change=day_change or 0,
        day_change_percent=day_change_percent or 0,
        positions=positions
    )

@router.get("/order-history/{portfolio_id}")
async def get_order_history(portfolio_id: str, limit: int = 50, offset: int = 0):
    """Get trading order history for a portfolio"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT transaction_id, symbol, asset_type, action, quantity, price, commission, 
               total_amount, timestamp, order_type, notes
        FROM transactions 
        WHERE portfolio_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
    ''', (portfolio_id, limit, offset))
    
    transactions = cursor.fetchall()
    
    # Get total count for pagination
    cursor.execute('SELECT COUNT(*) FROM transactions WHERE portfolio_id = ?', (portfolio_id,))
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "transactions": [
            {
                "transaction_id": tx[0],
                "symbol": tx[1],
                "asset_type": tx[2],
                "action": tx[3],
                "quantity": tx[4],
                "price": tx[5],
                "commission": tx[6],
                "total_amount": tx[7],
                "timestamp": tx[8],
                "order_type": tx[9],
                "notes": tx[10]
            }
            for tx in transactions
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }

@router.get("/supported-assets")
async def get_supported_assets():
    """Get list of all supported trading assets"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get ActiveLog ecosystem companies
    cursor.execute('SELECT symbol, name, sector FROM activelog_companies WHERE is_active = 1')
    activelog_companies = cursor.fetchall()
    
    # Get cached market data
    cursor.execute('SELECT DISTINCT symbol, asset_type FROM market_data ORDER BY symbol')
    market_assets = cursor.fetchall()
    
    conn.close()
    
    return {
        "activelog_ecosystem": [
            {"symbol": company[0], "name": company[1], "sector": company[2]}
            for company in activelog_companies
        ],
        "market_assets": [
            {"symbol": asset[0], "type": asset[1]}
            for asset in market_assets
        ],
        "asset_types": {
            "stock": "Individual stocks (NYSE, NASDAQ)",
            "etf": "Exchange-traded funds",
            "crypto": "Cryptocurrencies (BTC, ETH, etc.)",
            "forex": "Foreign exchange pairs",
            "option": "Stock and index options",
            "future": "Futures contracts",
            "commodity": "Commodity futures",
            "activelog": "ActiveLog ecosystem companies"
        },
        "commission_structure": COMMISSION_STRUCTURE
    }

@router.post("/simulate-trade")
async def simulate_trade(order: TradeOrder, portfolio_id: str):
    """Simulate a trade without executing it to show estimated costs and impact"""
    current_price = get_current_price(order.symbol, order.asset_type)
    
    # Simulate execution price
    if order.order_type == "market":
        execution_price = simulate_slippage(current_price, "market", order.action, order.quantity)
    elif order.order_type == "limit" and order.limit_price:
        execution_price = order.limit_price
    else:
        execution_price = current_price
    
    # Calculate costs
    commission = calculate_commission(order.asset_type, order.quantity, execution_price)
    
    if order.action in ["buy", "cover"]:
        total_cost = (execution_price * order.quantity) + commission
        impact = -total_cost  # Negative cash impact
    else:
        total_proceeds = (execution_price * order.quantity) - commission
        impact = total_proceeds  # Positive cash impact
    
    return {
        "symbol": order.symbol,
        "action": order.action,
        "quantity": order.quantity,
        "estimated_execution_price": execution_price,
        "current_market_price": current_price,
        "estimated_commission": commission,
        "estimated_total_cost": abs(impact),
        "cash_impact": impact,
        "slippage_estimate": abs(execution_price - current_price) / current_price * 100,
        "order_valid": True,
        "warnings": []
    }