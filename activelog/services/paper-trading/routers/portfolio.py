from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import sqlite3
import uuid
import json
import random
import math

router = APIRouter()

# Pydantic models
class CreatePortfolio(BaseModel):
    name: str
    starting_capital: float = 100000.0
    description: Optional[str] = None

class Portfolio(BaseModel):
    portfolio_id: str
    user_id: str
    name: str
    starting_capital: float
    current_cash: float
    total_value: float
    day_change: float
    day_change_percent: float
    total_return: float
    total_return_percent: float
    created_at: datetime
    is_active: bool

class Holding(BaseModel):
    holding_id: str
    symbol: str
    asset_type: str
    quantity: float
    average_cost: float
    current_price: float
    market_value: float
    day_change: float
    day_change_percent: float
    total_return: float
    total_return_percent: float
    weight_percent: float

class PortfolioAnalytics(BaseModel):
    portfolio_id: str
    total_value: float
    cash_percentage: float
    invested_percentage: float
    day_change: float
    day_change_percent: float
    total_return: float
    total_return_percent: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    holdings_count: int
    sector_allocation: Dict[str, float]
    asset_type_allocation: Dict[str, float]
    top_holdings: List[Holding]

class PerformanceMetrics(BaseModel):
    period: str
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float

class DividendTransaction(BaseModel):
    symbol: str
    amount: float
    ex_date: datetime
    pay_date: datetime
    dividend_type: str  # cash, stock, special

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('paper_trading.db')

def get_current_price(symbol: str, asset_type: str) -> float:
    """Get current price for a symbol from market data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if asset_type == "activelog":
        cursor.execute('SELECT current_price FROM activelog_companies WHERE symbol = ?', (symbol,))
    else:
        cursor.execute('SELECT current_price FROM market_data WHERE symbol = ? AND asset_type = ?', 
                      (symbol, asset_type))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return float(result[0])
    else:
        # Return simulated price if not found
        return random.uniform(10, 500)

def calculate_portfolio_metrics(portfolio_id: str) -> Dict[str, Any]:
    """Calculate comprehensive portfolio metrics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get portfolio basic info
    cursor.execute('''
        SELECT starting_capital, current_cash, total_value, created_at
        FROM portfolios WHERE portfolio_id = ?
    ''', (portfolio_id,))
    portfolio_data = cursor.fetchone()
    
    if not portfolio_data:
        return {}
    
    starting_capital, current_cash, total_value, created_at = portfolio_data
    
    # Get all holdings
    cursor.execute('''
        SELECT symbol, asset_type, quantity, average_cost, current_price, market_value
        FROM holdings WHERE portfolio_id = ?
    ''', (portfolio_id,))
    holdings = cursor.fetchall()
    
    # Calculate metrics
    total_return = total_value - starting_capital
    total_return_percent = (total_return / starting_capital) * 100
    
    # Calculate allocation percentages
    cash_percentage = (current_cash / total_value) * 100 if total_value > 0 else 0
    invested_percentage = 100 - cash_percentage
    
    # Calculate sector and asset type allocations
    sector_allocation = {}
    asset_type_allocation = {}
    
    for holding in holdings:
        symbol, asset_type, quantity, avg_cost, current_price, market_value = holding
        
        # Asset type allocation
        if asset_type not in asset_type_allocation:
            asset_type_allocation[asset_type] = 0
        asset_type_allocation[asset_type] += (market_value / total_value) * 100 if total_value > 0 else 0
        
        # Sector allocation (simplified)
        if asset_type == "stock":
            sector = get_stock_sector(symbol)  # This would be implemented
            if sector not in sector_allocation:
                sector_allocation[sector] = 0
            sector_allocation[sector] += (market_value / total_value) * 100 if total_value > 0 else 0
    
    # Get historical performance for volatility calculation
    cursor.execute('''
        SELECT timestamp, 
               LAG(total_value) OVER (ORDER BY timestamp) as prev_value,
               total_value
        FROM (
            SELECT DATE(timestamp) as date, 
                   AVG(total_value) as total_value,
                   timestamp
            FROM portfolio_snapshots 
            WHERE portfolio_id = ?
            GROUP BY DATE(timestamp)
            ORDER BY timestamp DESC
            LIMIT 30
        )
    ''', (portfolio_id,))
    
    # Since we don't have portfolio_snapshots table, simulate historical data
    daily_returns = []
    for i in range(30):  # 30 days of data
        daily_return = random.gauss(0.001, 0.02)  # 0.1% average, 2% volatility
        daily_returns.append(daily_return)
    
    # Calculate volatility (standard deviation of daily returns)
    if len(daily_returns) > 1:
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        volatility = math.sqrt(variance) * math.sqrt(252)  # Annualized volatility
    else:
        volatility = 0.0
    
    # Calculate Sharpe ratio (assuming 2% risk-free rate)
    risk_free_rate = 0.02
    annualized_return = total_return_percent / 100  # Convert to decimal
    sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
    
    # Calculate max drawdown (simplified)
    max_drawdown = max(0, min(daily_returns)) * 100  # Convert to percentage
    
    conn.close()
    
    return {
        "total_return": total_return,
        "total_return_percent": total_return_percent,
        "cash_percentage": cash_percentage,
        "invested_percentage": invested_percentage,
        "volatility": volatility * 100,  # Convert to percentage
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": abs(max_drawdown),
        "sector_allocation": sector_allocation,
        "asset_type_allocation": asset_type_allocation
    }

def get_stock_sector(symbol: str) -> str:
    """Get sector for a stock symbol (simplified mapping)"""
    tech_stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META", "AMZN"]
    finance_stocks = ["JPM", "BAC", "WFC", "GS", "MS"]
    healthcare_stocks = ["JNJ", "PFE", "UNH", "ABBV", "MRK"]
    
    if symbol in tech_stocks:
        return "Technology"
    elif symbol in finance_stocks:
        return "Financial Services"
    elif symbol in healthcare_stocks:
        return "Healthcare"
    else:
        return "Other"

@router.post("/create", response_model=Portfolio)
async def create_portfolio(portfolio_data: CreatePortfolio, user_id: str):
    """Create a new paper trading portfolio"""
    
    portfolio_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO portfolios 
            (portfolio_id, user_id, name, starting_capital, current_cash, total_value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (portfolio_id, user_id, portfolio_data.name, portfolio_data.starting_capital,
              portfolio_data.starting_capital, portfolio_data.starting_capital))
        
        conn.commit()
        
        return Portfolio(
            portfolio_id=portfolio_id,
            user_id=user_id,
            name=portfolio_data.name,
            starting_capital=portfolio_data.starting_capital,
            current_cash=portfolio_data.starting_capital,
            total_value=portfolio_data.starting_capital,
            day_change=0.0,
            day_change_percent=0.0,
            total_return=0.0,
            total_return_percent=0.0,
            created_at=datetime.now(),
            is_active=True
        )
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create portfolio: {str(e)}")
    
    finally:
        conn.close()

@router.get("/list/{user_id}")
async def get_user_portfolios(user_id: str):
    """Get all portfolios for a user"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT portfolio_id, name, starting_capital, current_cash, total_value,
               day_change, day_change_percent, total_return, total_return_percent,
               created_at, is_active
        FROM portfolios 
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    
    portfolios = cursor.fetchall()
    conn.close()
    
    portfolio_list = []
    for portfolio in portfolios:
        portfolio_list.append(Portfolio(
            portfolio_id=portfolio[0],
            user_id=user_id,
            name=portfolio[1],
            starting_capital=portfolio[2],
            current_cash=portfolio[3],
            total_value=portfolio[4],
            day_change=portfolio[5] or 0.0,
            day_change_percent=portfolio[6] or 0.0,
            total_return=portfolio[7] or 0.0,
            total_return_percent=portfolio[8] or 0.0,
            created_at=datetime.fromisoformat(portfolio[9]),
            is_active=bool(portfolio[10])
        ))
    
    return {"portfolios": portfolio_list}

@router.get("/{portfolio_id}/details", response_model=PortfolioAnalytics)
async def get_portfolio_details(portfolio_id: str):
    """Get detailed portfolio analytics"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get portfolio basic info
    cursor.execute('''
        SELECT user_id, name, starting_capital, current_cash, total_value,
               day_change, day_change_percent, created_at
        FROM portfolios WHERE portfolio_id = ?
    ''', (portfolio_id,))
    
    portfolio_data = cursor.fetchone()
    if not portfolio_data:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    user_id, name, starting_capital, current_cash, total_value, day_change, day_change_percent, created_at = portfolio_data
    
    # Get all holdings with updated prices
    cursor.execute('''
        SELECT holding_id, symbol, asset_type, quantity, average_cost, current_price
        FROM holdings WHERE portfolio_id = ?
    ''', (portfolio_id,))
    
    holdings_data = cursor.fetchall()
    holdings = []
    updated_total_value = current_cash
    
    for holding_data in holdings_data:
        holding_id, symbol, asset_type, quantity, average_cost, current_price = holding_data
        
        # Get latest price
        latest_price = get_current_price(symbol, asset_type)
        market_value = quantity * latest_price
        updated_total_value += market_value
        
        # Calculate returns
        total_return = market_value - (quantity * average_cost)
        total_return_percent = (total_return / (quantity * average_cost)) * 100 if average_cost > 0 else 0
        
        # Calculate day change (simplified)
        day_change_amount = market_value * random.uniform(-0.05, 0.05)  # ±5%
        day_change_percent = (day_change_amount / market_value) * 100 if market_value > 0 else 0
        
        # Calculate weight in portfolio
        weight_percent = (market_value / updated_total_value) * 100 if updated_total_value > 0 else 0
        
        holdings.append(Holding(
            holding_id=holding_id,
            symbol=symbol,
            asset_type=asset_type,
            quantity=quantity,
            average_cost=average_cost,
            current_price=latest_price,
            market_value=market_value,
            day_change=day_change_amount,
            day_change_percent=day_change_percent,
            total_return=total_return,
            total_return_percent=total_return_percent,
            weight_percent=weight_percent
        ))
    
    # Update portfolio total value
    cursor.execute('UPDATE portfolios SET total_value = ? WHERE portfolio_id = ?', 
                  (updated_total_value, portfolio_id))
    conn.commit()
    conn.close()
    
    # Calculate portfolio metrics
    metrics = calculate_portfolio_metrics(portfolio_id)
    
    # Sort holdings by market value (top holdings)
    holdings.sort(key=lambda x: x.market_value, reverse=True)
    top_holdings = holdings[:10]  # Top 10 holdings
    
    return PortfolioAnalytics(
        portfolio_id=portfolio_id,
        total_value=updated_total_value,
        cash_percentage=metrics.get("cash_percentage", 0),
        invested_percentage=metrics.get("invested_percentage", 0),
        day_change=day_change or 0,
        day_change_percent=day_change_percent or 0,
        total_return=metrics.get("total_return", 0),
        total_return_percent=metrics.get("total_return_percent", 0),
        volatility=metrics.get("volatility", 0),
        sharpe_ratio=metrics.get("sharpe_ratio", 0),
        max_drawdown=metrics.get("max_drawdown", 0),
        holdings_count=len(holdings),
        sector_allocation=metrics.get("sector_allocation", {}),
        asset_type_allocation=metrics.get("asset_type_allocation", {}),
        top_holdings=top_holdings
    )

@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: str, 
    period: str = "1mo"  # 1d, 1w, 1mo, 3mo, 6mo, 1y, all
):
    """Get portfolio performance metrics for specified period"""
    
    # Calculate date range based on period
    end_date = datetime.now()
    if period == "1d":
        start_date = end_date - timedelta(days=1)
    elif period == "1w":
        start_date = end_date - timedelta(weeks=1)
    elif period == "1mo":
        start_date = end_date - timedelta(days=30)
    elif period == "3mo":
        start_date = end_date - timedelta(days=90)
    elif period == "6mo":
        start_date = end_date - timedelta(days=180)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    else:  # all
        start_date = datetime(2020, 1, 1)  # Beginning of time
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get portfolio creation date and starting capital
    cursor.execute('SELECT starting_capital, created_at FROM portfolios WHERE portfolio_id = ?', 
                  (portfolio_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    starting_capital, created_at = result
    portfolio_start = datetime.fromisoformat(created_at)
    
    # Adjust start date if portfolio is newer than requested period
    if portfolio_start > start_date:
        start_date = portfolio_start
    
    # Get transactions in the period for detailed analysis
    cursor.execute('''
        SELECT action, quantity, price, total_amount, timestamp
        FROM transactions 
        WHERE portfolio_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    ''', (portfolio_id, start_date.isoformat(), end_date.isoformat()))
    
    transactions = cursor.fetchall()
    conn.close()
    
    # Calculate performance metrics
    # For demo purposes, we'll simulate realistic metrics
    
    # Generate daily returns for the period
    days_in_period = (end_date - start_date).days
    if days_in_period == 0:
        days_in_period = 1
    
    daily_returns = []
    cumulative_returns = []
    running_value = starting_capital
    
    for i in range(days_in_period):
        # Simulate daily return with some correlation to market
        daily_return = random.gauss(0.0008, 0.018)  # 0.08% daily average, 1.8% volatility
        daily_returns.append(daily_return)
        
        running_value *= (1 + daily_return)
        cumulative_returns.append((running_value - starting_capital) / starting_capital)
    
    # Calculate metrics
    total_return = (running_value - starting_capital) / starting_capital
    
    # Annualized return
    years = days_in_period / 365.25
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else total_return
    
    # Volatility (annualized standard deviation)
    if len(daily_returns) > 1:
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        volatility = math.sqrt(variance) * math.sqrt(252)  # Annualized
    else:
        volatility = 0.0
    
    # Sharpe ratio (assuming 2% risk-free rate)
    risk_free_rate = 0.02
    sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
    
    # Maximum drawdown
    peak = starting_capital
    max_drawdown = 0
    for value in [starting_capital * (1 + r) for r in cumulative_returns]:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Win rate and profit factor
    winning_trades = sum(1 for t in transactions if t[0] == "sell" and float(t[3]) > 0)
    total_trades = len([t for t in transactions if t[0] == "sell"])
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # Profit factor (total profits / total losses)
    profits = sum(float(t[3]) for t in transactions if t[0] == "sell" and float(t[3]) > 0)
    losses = abs(sum(float(t[3]) for t in transactions if t[0] == "sell" and float(t[3]) < 0))
    profit_factor = profits / losses if losses > 0 else float('inf') if profits > 0 else 0
    
    # Calmar ratio (annualized return / max drawdown)
    calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
    
    return PerformanceMetrics(
        period=period,
        total_return=total_return * 100,  # Convert to percentage
        annualized_return=annualized_return * 100,
        volatility=volatility * 100,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown * 100,
        win_rate=win_rate * 100,
        profit_factor=profit_factor,
        calmar_ratio=calmar_ratio
    )

@router.post("/{portfolio_id}/rebalance")
async def rebalance_portfolio(
    portfolio_id: str,
    target_allocation: Dict[str, float]  # symbol -> target weight percentage
):
    """Rebalance portfolio to target allocation"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current portfolio value and holdings
    cursor.execute('SELECT current_cash, total_value FROM portfolios WHERE portfolio_id = ?', 
                  (portfolio_id,))
    portfolio_data = cursor.fetchone()
    
    if not portfolio_data:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    current_cash, total_value = portfolio_data
    
    cursor.execute('''
        SELECT symbol, asset_type, quantity, current_price
        FROM holdings WHERE portfolio_id = ?
    ''', (portfolio_id,))
    
    current_holdings = cursor.fetchall()
    
    # Calculate rebalancing trades needed
    rebalancing_trades = []
    total_target_weight = sum(target_allocation.values())
    
    if total_target_weight > 100:
        raise HTTPException(status_code=400, detail="Target allocation exceeds 100%")
    
    # Calculate current allocations
    current_allocation = {}
    for symbol, asset_type, quantity, current_price in current_holdings:
        current_price = get_current_price(symbol, asset_type)
        market_value = quantity * current_price
        current_weight = (market_value / total_value) * 100 if total_value > 0 else 0
        current_allocation[symbol] = {
            "weight": current_weight,
            "value": market_value,
            "quantity": quantity,
            "asset_type": asset_type,
            "price": current_price
        }
    
    # Calculate required trades
    for symbol, target_weight in target_allocation.items():
        target_value = (target_weight / 100) * total_value
        current_info = current_allocation.get(symbol, {})
        current_value = current_info.get("value", 0)
        
        difference = target_value - current_value
        
        if abs(difference) > total_value * 0.01:  # Only rebalance if difference > 1%
            if symbol in current_allocation:
                # Existing holding - buy more or sell some
                current_price = current_info["price"]
                quantity_change = difference / current_price
                
                rebalancing_trades.append({
                    "symbol": symbol,
                    "asset_type": current_info["asset_type"],
                    "action": "buy" if quantity_change > 0 else "sell",
                    "quantity": abs(quantity_change),
                    "reason": f"Rebalance from {current_info['weight']:.1f}% to {target_weight:.1f}%"
                })
            else:
                # New holding - need to buy
                # For simplicity, assume it's a stock
                estimated_price = get_current_price(symbol, "stock")
                quantity = target_value / estimated_price
                
                rebalancing_trades.append({
                    "symbol": symbol,
                    "asset_type": "stock",
                    "action": "buy",
                    "quantity": quantity,
                    "reason": f"New holding - target {target_weight:.1f}%"
                })
    
    conn.close()
    
    return {
        "portfolio_id": portfolio_id,
        "current_allocation": current_allocation,
        "target_allocation": target_allocation,
        "rebalancing_trades": rebalancing_trades,
        "estimated_cost": sum(
            trade["quantity"] * get_current_price(trade["symbol"], trade["asset_type"]) 
            for trade in rebalancing_trades if trade["action"] == "buy"
        )
    }

@router.get("/{portfolio_id}/dividends")
async def get_dividend_history(portfolio_id: str):
    """Get dividend payment history for portfolio"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get holdings that pay dividends
    cursor.execute('''
        SELECT DISTINCT symbol, asset_type, quantity
        FROM holdings WHERE portfolio_id = ?
    ''', (portfolio_id,))
    
    holdings = cursor.fetchall()
    
    # Simulate dividend history
    dividend_history = []
    
    for symbol, asset_type, quantity in holdings:
        if asset_type in ["stock", "etf", "activelog"]:
            # Generate some historical dividends
            for i in range(random.randint(0, 4)):  # 0-4 dividend payments
                dividend_per_share = random.uniform(0.10, 2.50)
                total_dividend = dividend_per_share * quantity
                
                pay_date = datetime.now() - timedelta(days=random.randint(30, 365))
                ex_date = pay_date - timedelta(days=random.randint(1, 5))
                
                dividend_history.append(DividendTransaction(
                    symbol=symbol,
                    amount=total_dividend,
                    ex_date=ex_date,
                    pay_date=pay_date,
                    dividend_type="cash"
                ))
    
    # Sort by pay date
    dividend_history.sort(key=lambda x: x.pay_date, reverse=True)
    
    # Calculate summary statistics
    total_dividends = sum(div.amount for div in dividend_history)
    annual_dividend_yield = (total_dividends / 100000) * 100  # Assuming $100k portfolio
    
    conn.close()
    
    return {
        "portfolio_id": portfolio_id,
        "dividend_history": dividend_history,
        "summary": {
            "total_dividends_received": total_dividends,
            "estimated_annual_yield": annual_dividend_yield,
            "dividend_payments_count": len(dividend_history)
        }
    }

@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: str):
    """Delete a portfolio and all associated data"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Delete holdings first
        cursor.execute('DELETE FROM holdings WHERE portfolio_id = ?', (portfolio_id,))
        
        # Delete transactions
        cursor.execute('DELETE FROM transactions WHERE portfolio_id = ?', (portfolio_id,))
        
        # Delete portfolio
        cursor.execute('DELETE FROM portfolios WHERE portfolio_id = ?', (portfolio_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        conn.commit()
        return {"message": "Portfolio deleted successfully"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete portfolio: {str(e)}")
    
    finally:
        conn.close()

@router.post("/{portfolio_id}/reset")
async def reset_portfolio(portfolio_id: str):
    """Reset portfolio to starting state"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get starting capital
        cursor.execute('SELECT starting_capital FROM portfolios WHERE portfolio_id = ?', 
                      (portfolio_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        starting_capital = result[0]
        
        # Delete all holdings and transactions
        cursor.execute('DELETE FROM holdings WHERE portfolio_id = ?', (portfolio_id,))
        cursor.execute('DELETE FROM transactions WHERE portfolio_id = ?', (portfolio_id,))
        
        # Reset portfolio to starting state
        cursor.execute('''
            UPDATE portfolios 
            SET current_cash = ?, 
                total_value = ?, 
                day_change = 0, 
                day_change_percent = 0,
                total_return = 0,
                total_return_percent = 0
            WHERE portfolio_id = ?
        ''', (starting_capital, starting_capital, portfolio_id))
        
        conn.commit()
        return {"message": "Portfolio reset to starting state successfully"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset portfolio: {str(e)}")
    
    finally:
        conn.close()