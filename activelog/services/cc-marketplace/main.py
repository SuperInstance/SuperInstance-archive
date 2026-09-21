from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from src.models import (Order, Trade, OrderType, OrderSide, MarketSymbol, 
                       Portfolio, Position, MarketMakerConfig, LiquidityPool)
from src.order_book import MatchingEngine
from src.trading_interface import MarketDataProvider, ROICalculator
from src.market_maker import AutomatedMarketMaker, MarketMaker, CircuitBreakerManager, ArbitrageDetector
from src.portfolio_manager import PortfolioManager
from src.nonprofit_integration import NonProfitIntegrationSystem
from src.youth_investment import YouthInvestmentSystem
from src.yield_optimization import YieldOptimizationSystem
from src.exit_strategy import ExitStrategySystem
from src.competition_protection import CompetitionProtectionSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CC Marketplace",
    description="Advanced cryptocurrency marketplace with order book, AMM, and portfolio management",
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize core components
matching_engine = MatchingEngine()
market_data_provider = MarketDataProvider(matching_engine)
amm = AutomatedMarketMaker()
market_maker = MarketMaker(matching_engine)
circuit_breaker = CircuitBreakerManager()
arbitrage_detector = ArbitrageDetector(amm, matching_engine)
portfolio_manager = PortfolioManager(market_data_provider)

# Initialize advanced ecosystem components
nonprofit_system = NonProfitIntegrationSystem()
youth_system = YouthInvestmentSystem()
yield_optimizer = YieldOptimizationSystem(matching_engine, portfolio_manager, amm)
exit_strategy = ExitStrategySystem()
competition_protection = CompetitionProtectionSystem()

# WebSocket connections
websocket_connections: List[WebSocket] = []

# Request/Response Models
class OrderRequest(BaseModel):
    user_id: str
    symbol: MarketSymbol
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None

class LiquidityPoolRequest(BaseModel):
    symbol: MarketSymbol
    base_amount: Decimal
    quote_amount: Decimal

class SwapRequest(BaseModel):
    symbol: MarketSymbol
    input_amount: Decimal
    is_base_to_quote: bool = True
    min_output: Optional[Decimal] = None

# Initialize market data and liquidity pools for all symbols
async def initialize_markets():
    """Initialize markets with starting liquidity and market makers"""
    logger.info("Initializing markets...")
    
    # Initialize circuit breakers
    for symbol in MarketSymbol:
        circuit_breaker.initialize_symbol(symbol)
    
    # Create initial liquidity pools
    initial_pools = {
        MarketSymbol.ACTIVELOG_CC: (Decimal('10000'), Decimal('100000')),  # 1:10 ratio
        MarketSymbol.DMLOG_CC: (Decimal('5000'), Decimal('25000')),        # 1:5 ratio
        MarketSymbol.STUDYLOG_CC: (Decimal('8000'), Decimal('40000')),     # 1:5 ratio
        MarketSymbol.FISHINGLOG_CC: (Decimal('3000'), Decimal('9000')),    # 1:3 ratio
    }
    
    for symbol, (base_amount, quote_amount) in initial_pools.items():
        amm.create_pool(symbol, base_amount, quote_amount)
        logger.info(f"Created liquidity pool for {symbol}")
    
    # Configure market makers
    for symbol in MarketSymbol:
        config = MarketMakerConfig(
            symbol=symbol,
            spread_percentage=Decimal('0.005'),  # 0.5% spread
            max_order_size=Decimal('1000'),
            inventory_target=Decimal('5000'),
            risk_limit=Decimal('0.02')
        )
        market_maker.configure(symbol, config)
    
    # Start market maker
    asyncio.create_task(market_maker.start())
    
    logger.info("Markets initialized successfully")

@app.on_event("startup")
async def startup_event():
    await initialize_markets()

@app.on_event("shutdown")
async def shutdown_event():
    await market_maker.stop()

# WebSocket endpoint for real-time market data
@app.websocket("/ws/market-data")
async def market_data_websocket(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.append(websocket)
    market_data_provider.subscribe(websocket)
    
    try:
        while True:
            # Keep connection alive and handle ping/pong
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        market_data_provider.unsubscribe(websocket)

# Trading endpoints
@app.post("/api/orders/submit")
async def submit_order(order_request: OrderRequest, background_tasks: BackgroundTasks):
    """Submit a trading order"""
    try:
        # Check circuit breaker
        if circuit_breaker.is_trading_halted(order_request.symbol):
            raise HTTPException(status_code=403, detail="Trading halted for this symbol")
        
        # Create order
        order = Order(
            user_id=order_request.user_id,
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            price=order_request.price,
            stop_price=order_request.stop_price
        )
        
        # Submit to matching engine
        trades = await matching_engine.submit_order(order)
        
        # Process trades in background
        for trade in trades:
            background_tasks.add_task(process_trade, trade)
        
        return {
            "order_id": order.order_id,
            "status": order.status.value,
            "trades": len(trades),
            "filled_quantity": float(order.filled_quantity),
            "remaining_quantity": float(order.remaining_quantity)
        }
    
    except Exception as e:
        logger.error(f"Error submitting order: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/orders/{order_id}/cancel")
async def cancel_order(order_id: str, symbol: MarketSymbol):
    """Cancel a pending order"""
    success = await matching_engine.cancel_order(order_id, symbol)
    
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or already executed")
    
    return {"message": "Order cancelled successfully"}

@app.get("/api/market/{symbol}")
async def get_market_data(symbol: MarketSymbol):
    """Get current market data for a symbol"""
    try:
        market_summary = market_data_provider.get_market_summary(symbol)
        market_depth = matching_engine.get_market_data(symbol)
        technical_analysis = market_data_provider.get_technical_analysis(symbol)
        
        return {
            "symbol": symbol.value,
            "summary": market_summary,
            "depth": market_depth,
            "technical": technical_analysis
        }
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/{symbol}/chart")
async def get_chart_data(symbol: MarketSymbol, interval: str = "1h", limit: int = 100):
    """Get candlestick chart data"""
    chart = market_data_provider.charts.get(symbol)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart data not found")
    
    return chart.get_chart_data(interval, limit)

@app.get("/api/market/{symbol}/trades")
async def get_recent_trades(symbol: MarketSymbol, limit: int = 50):
    """Get recent trades for a symbol"""
    trades = matching_engine.get_recent_trades(symbol, limit)
    
    return [
        {
            "trade_id": trade.trade_id,
            "price": float(trade.price),
            "quantity": float(trade.quantity),
            "executed_at": trade.executed_at.isoformat(),
            "buyer_id": trade.buyer_id,
            "seller_id": trade.seller_id
        } for trade in trades
    ]

# AMM endpoints
@app.post("/api/amm/pools/create")
async def create_liquidity_pool(pool_request: LiquidityPoolRequest):
    """Create a new liquidity pool"""
    try:
        pool = amm.create_pool(
            pool_request.symbol,
            pool_request.base_amount,
            pool_request.quote_amount
        )
        return {
            "pool_id": pool.pool_id,
            "symbol": pool.symbol.value,
            "base_reserve": float(pool.base_reserve),
            "quote_reserve": float(pool.quote_reserve),
            "k_constant": float(pool.k_constant)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/amm/pools/{symbol}")
async def get_pool_info(symbol: MarketSymbol):
    """Get liquidity pool information"""
    pool_info = amm.get_pool_info(symbol)
    if 'error' in pool_info:
        raise HTTPException(status_code=404, detail=pool_info['error'])
    return pool_info

@app.post("/api/amm/swap/quote")
async def get_swap_quote(swap_request: SwapRequest):
    """Get quote for token swap"""
    quote = amm.get_swap_quote(
        swap_request.symbol,
        swap_request.input_amount,
        swap_request.is_base_to_quote
    )
    return quote

@app.post("/api/amm/swap/execute")
async def execute_swap(swap_request: SwapRequest):
    """Execute token swap"""
    result = amm.execute_swap(
        swap_request.symbol,
        swap_request.input_amount,
        swap_request.is_base_to_quote,
        swap_request.min_output
    )
    return result

# Portfolio endpoints
@app.post("/api/portfolio/create")
async def create_portfolio(user_id: str, initial_cash: Decimal = Decimal('10000')):
    """Create a new portfolio"""
    portfolio = portfolio_manager.create_portfolio(user_id, initial_cash)
    return {
        "user_id": portfolio.user_id,
        "cash_balance": float(portfolio.cash_balance),
        "total_value": float(portfolio.total_value_cc),
        "created": True
    }

@app.get("/api/portfolio/{user_id}")
async def get_portfolio_summary(user_id: str):
    """Get comprehensive portfolio summary"""
    summary = await portfolio_manager.get_portfolio_summary(user_id)
    if 'error' in summary:
        raise HTTPException(status_code=404, detail=summary['error'])
    return summary

@app.get("/api/portfolio/{user_id}/positions")
async def get_positions(user_id: str):
    """Get all positions for a user"""
    positions = portfolio_manager.get_positions(user_id)
    return [
        {
            "symbol": pos.symbol.value,
            "quantity": float(pos.quantity),
            "average_cost": float(pos.average_cost),
            "current_price": float(pos.current_price),
            "market_value": float(pos.market_value),
            "unrealized_pnl": float(pos.unrealized_pnl),
            "cost_basis": float(pos.cost_basis)
        } for pos in positions
    ]

@app.get("/api/portfolio/{user_id}/tax-report/{tax_year}")
async def get_tax_report(user_id: str, tax_year: int):
    """Get tax report for a specific year"""
    return portfolio_manager.get_tax_report(user_id, tax_year)

@app.post("/api/portfolio/{user_id}/rebalance")
async def get_rebalancing_suggestions(user_id: str, target_allocation: Dict[str, float]):
    """Get portfolio rebalancing suggestions"""
    suggestions = portfolio_manager.get_rebalancing_suggestions(user_id, target_allocation)
    return {"suggestions": suggestions}

# Risk management endpoints
@app.get("/api/risk/circuit-breakers")
async def get_circuit_breaker_status():
    """Get circuit breaker status for all symbols"""
    status = {}
    for symbol in MarketSymbol:
        breaker = circuit_breaker.circuit_breakers.get(symbol)
        if breaker:
            status[symbol.value] = {
                "trading_halted": breaker.trading_halted,
                "halt_started_at": breaker.halt_started_at.isoformat() if breaker.halt_started_at else None,
                "price_change_threshold": float(breaker.price_change_threshold)
            }
    return status

@app.post("/api/risk/circuit-breakers/{symbol}/halt")
async def force_trading_halt(symbol: MarketSymbol, duration_minutes: int = 15):
    """Manually halt trading for a symbol"""
    circuit_breaker.force_halt(symbol, duration_minutes)
    return {"message": f"Trading halted for {symbol.value} for {duration_minutes} minutes"}

@app.post("/api/risk/circuit-breakers/{symbol}/lift")
async def lift_trading_halt(symbol: MarketSymbol):
    """Manually lift trading halt"""
    circuit_breaker.lift_halt(symbol)
    return {"message": f"Trading halt lifted for {symbol.value}"}

# Arbitrage detection
@app.get("/api/arbitrage/opportunities")
async def get_arbitrage_opportunities():
    """Get current arbitrage opportunities"""
    opportunities = []
    for symbol in MarketSymbol:
        opportunity = await arbitrage_detector.check_arbitrage_opportunity(symbol)
        if opportunity:
            opportunities.append(opportunity)
    return {"opportunities": opportunities}

# Analytics endpoints
@app.get("/api/analytics/roi")
async def calculate_roi(initial_investment: Decimal, current_value: Decimal):
    """Calculate ROI metrics"""
    return ROICalculator.calculate_roi(initial_investment, current_value)

@app.get("/api/analytics/pe-ratio")
async def calculate_pe_ratio(market_price: Decimal, earnings_per_share: Decimal):
    """Calculate P/E ratio"""
    pe_ratio = ROICalculator.calculate_pe_ratio(market_price, earnings_per_share)
    return {"pe_ratio": float(pe_ratio) if pe_ratio else None}

# Market overview
@app.get("/api/market/overview")
async def get_market_overview():
    """Get overview of all markets"""
    overview = {}
    for symbol in MarketSymbol:
        try:
            market_summary = market_data_provider.get_market_summary(symbol)
            pool_info = amm.get_pool_info(symbol)
            
            overview[symbol.value] = {
                "market_data": market_summary,
                "amm_pool": pool_info if 'error' not in pool_info else None,
                "trading_halted": circuit_breaker.is_trading_halted(symbol)
            }
        except Exception as e:
            logger.error(f"Error getting overview for {symbol}: {e}")
            overview[symbol.value] = {"error": str(e)}
    
    return overview

# Non-Profit Integration endpoints
@app.post("/api/nonprofit/register")
async def register_nonprofit(organization_data: Dict):
    """Register a new non-profit organization"""
    try:
        account = nonprofit_system.register_nonprofit(organization_data)
        return {
            'account_id': account.account_id,
            'organization_name': account.organization_name,
            'verification_status': account.verification_status,
            'special_rate_eligible': account.special_rate_eligible
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/nonprofit/{account_id}/verify")
async def verify_nonprofit(account_id: str, verification_data: Dict):
    """Verify non-profit tax-exempt status"""
    success = nonprofit_system.verify_nonprofit_status(account_id, verification_data)
    return {'verified': success}

@app.post("/api/nonprofit/donate")
async def process_donation(donor_id: str, recipient_account_id: str, amount: Decimal, 
                          symbol: MarketSymbol, program_id: Optional[str] = None):
    """Process a donation with matching funds"""
    try:
        donation = nonprofit_system.process_donation(donor_id, recipient_account_id, amount, symbol, program_id)
        return {
            'donation_id': donation.donation_id,
            'amount': float(donation.amount),
            'matched_amount': float(donation.matched_amount),
            'total_amount': float(donation.total_amount),
            'tax_receipt_number': donation.tax_receipt_number
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/nonprofit/public-good-projects")
async def get_public_good_projects():
    """Get highlighted public good projects"""
    return {"projects": nonprofit_system.get_public_good_projects()}

@app.get("/api/nonprofit/{account_id}/dashboard")
async def get_nonprofit_dashboard(account_id: str):
    """Get comprehensive dashboard for non-profit"""
    dashboard = nonprofit_system.get_nonprofit_dashboard(account_id)
    if 'error' in dashboard:
        raise HTTPException(status_code=404, detail=dashboard['error'])
    return dashboard

# Youth Investment endpoints
@app.post("/api/youth/accounts/create")
async def create_youth_account(youth_data: Dict, parent_data: Optional[Dict] = None):
    """Create a new youth investment account"""
    try:
        account = youth_system.create_youth_account(youth_data, parent_data)
        return {
            'account_id': account.account_id,
            'youth_name': account.youth_name,
            'account_type': account.account_type.value,
            'real_money_enabled': account.real_money_enabled,
            'parent_guardian_id': account.parent_guardian_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/youth/{account_id}/goals")
async def create_investment_goal(account_id: str, goal_data: Dict):
    """Create investment goal for youth account"""
    try:
        goal = youth_system.create_investment_goal(account_id, goal_data)
        return {
            'goal_id': goal.goal_id,
            'title': goal.title,
            'target_amount': float(goal.target_amount),
            'target_date': goal.target_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/youth/{account_id}/dashboard")
async def get_youth_dashboard(account_id: str):
    """Get youth investment dashboard"""
    dashboard = youth_system.get_youth_dashboard(account_id)
    if 'error' in dashboard:
        raise HTTPException(status_code=404, detail=dashboard['error'])
    return dashboard

@app.post("/api/youth/mock-trading/create")
async def create_mock_trading_game(account_id: str, game_data: Dict):
    """Create mock trading game for education"""
    try:
        game = youth_system.create_mock_trading_game(account_id, game_data)
        return {
            'game_id': game.game_id,
            'starting_balance': float(game.starting_balance),
            'duration_days': game.duration_days,
            'end_date': game.end_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/youth/compound-interest-calculator")
async def compound_interest_calculator(principal: Decimal, monthly_contribution: Decimal,
                                     annual_rate: Decimal, years: int):
    """Educational compound interest calculator"""
    return youth_system.get_compound_interest_calculator(principal, monthly_contribution, annual_rate, years)

# Yield Optimization endpoints
@app.post("/api/yield/strategies/create")
async def create_investment_strategy(user_id: str, strategy_data: Dict):
    """Create auto-investment strategy"""
    try:
        strategy = yield_optimizer.create_investment_strategy(user_id, strategy_data)
        return {
            'strategy_id': strategy.strategy_id,
            'name': strategy.name,
            'strategy_type': strategy.strategy_type.value,
            'monthly_investment': float(strategy.monthly_investment),
            'next_execution': strategy.next_execution.isoformat() if strategy.next_execution else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/yield/staking/{pool_id}/stake")
async def stake_in_pool(user_id: str, pool_id: str, amount: Decimal):
    """Stake tokens in yield farming pool"""
    result = yield_optimizer.stake_in_yield_pool(user_id, pool_id, amount)
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/api/yield/opportunities/{user_id}")
async def get_yield_opportunities(user_id: str, risk_tolerance: str = "medium"):
    """Get available yield opportunities"""
    return {"opportunities": yield_optimizer.get_yield_opportunities(user_id, risk_tolerance)}

@app.post("/api/yield/referrals/create")
async def create_referral_program(referrer_id: str):
    """Create referral program"""
    program = yield_optimizer.create_referral_program(referrer_id)
    return {
        'program_id': program.program_id,
        'referral_code': program.referral_code,
        'commission_rate': float(program.commission_rate)
    }

@app.get("/api/yield/{user_id}/summary")
async def get_yield_summary(user_id: str):
    """Get user's yield optimization summary"""
    return yield_optimizer.get_user_yield_summary(user_id)

# Exit Strategy endpoints
@app.get("/api/exit-strategy/roadmap/{plan_id}")
async def get_transition_roadmap(plan_id: str):
    """Get detailed transition roadmap"""
    roadmap = exit_strategy.get_transition_roadmap(plan_id)
    if 'error' in roadmap:
        raise HTTPException(status_code=404, detail=roadmap['error'])
    return roadmap

@app.post("/api/exit-strategy/vesting/founder")
async def create_founder_vesting(plan_id: str, founder_id: str, total_shares: Decimal):
    """Create founder vesting schedule"""
    try:
        schedule = exit_strategy.create_founder_vesting_schedule(plan_id, founder_id, total_shares)
        return {
            'schedule_id': schedule.schedule_id,
            'total_shares': float(schedule.total_shares),
            'vesting_duration_months': schedule.vesting_duration_months,
            'cliff_duration_months': schedule.cliff_duration_months
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/exit-strategy/ownership-projection/{plan_id}")
async def get_ownership_projection(plan_id: str, target_date: str):
    """Get ownership distribution projection"""
    try:
        target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        projection = exit_strategy.get_ownership_distribution_projection(plan_id, target_date_obj)
        if 'error' in projection:
            raise HTTPException(status_code=404, detail=projection['error'])
        return projection
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@app.get("/api/exit-strategy/dashboard/{plan_id}")
async def get_exit_strategy_dashboard(plan_id: str):
    """Get comprehensive exit strategy dashboard"""
    dashboard = exit_strategy.get_exit_strategy_dashboard(plan_id)
    if 'error' in dashboard:
        raise HTTPException(status_code=404, detail=dashboard['error'])
    return dashboard

# Competition Protection endpoints
@app.post("/api/protection/ownership-incentives/create")
async def create_ownership_incentive(incentive_data: Dict):
    """Create broad ownership incentive program"""
    try:
        incentive = competition_protection.create_ownership_incentive(incentive_data)
        return {
            'incentive_id': incentive.incentive_id,
            'name': incentive.name,
            'target_audience': incentive.target_audience,
            'base_amount': float(incentive.base_amount),
            'budget_allocated': float(incentive.budget_allocated)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/protection/holding-bonus/create")
async def create_holding_bonus(holder_id: str, symbol: MarketSymbol, shares_held: Decimal, bonus_config: Dict):
    """Create long-term holding bonus"""
    bonus = competition_protection.create_long_term_holding_bonus(holder_id, symbol, shares_held, bonus_config)
    return {
        'bonus_id': bonus.bonus_id,
        'annual_bonus_rate': float(bonus.bonus_rate_annual * 100),
        'minimum_holding_months': bonus.minimum_holding_period_months
    }

@app.post("/api/protection/threat-assessment")
async def assess_threat(threat_data: Dict):
    """Assess competitive threat level"""
    assessment = competition_protection.assess_competitive_threat_level(threat_data)
    return assessment

@app.get("/api/protection/defense-status")
async def get_defense_status():
    """Get community defense status"""
    return competition_protection.get_community_defense_status()

@app.post("/api/protection/anti-takeover/{provision_id}/activate")
async def activate_anti_takeover(provision_id: str, trigger_event: Dict):
    """Activate anti-takeover provision"""
    result = competition_protection.activate_anti_takeover_provision(provision_id, trigger_event)
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# Trading interface
@app.get("/", response_class=HTMLResponse)
async def get_trading_interface():
    """Serve the main trading interface"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CC Marketplace</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a1a; color: #fff; }
            .container { max-width: 1400px; margin: 0 auto; }
            .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
            .card { background: #2d2d2d; border-radius: 8px; padding: 20px; }
            .card h3 { margin-top: 0; color: #4CAF50; }
            .market-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
            .metric { text-align: center; }
            .metric .label { font-size: 0.9em; color: #ccc; }
            .metric .value { font-size: 1.5em; font-weight: bold; }
            .positive { color: #4CAF50; }
            .negative { color: #f44336; }
            .order-form { display: grid; gap: 15px; }
            .order-form input, .order-form select, .order-form button { 
                padding: 10px; border: none; border-radius: 4px; 
                background: #3d3d3d; color: #fff;
            }
            .order-form button { background: #4CAF50; cursor: pointer; }
            .order-form button:hover { background: #45a049; }
            #chart { height: 400px; }
            .order-book { max-height: 300px; overflow-y: auto; }
            .order-book table { width: 100%; border-collapse: collapse; }
            .order-book th, .order-book td { padding: 8px; text-align: right; }
            .order-book .ask { color: #f44336; }
            .order-book .bid { color: #4CAF50; }
            .recent-trades { max-height: 300px; overflow-y: auto; }
            .trade { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #444; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>CC Marketplace</h1>
            
            <div class="grid">
                <div class="card">
                    <h3>Market Overview</h3>
                    <div id="market-overview" class="market-summary">
                        Loading...
                    </div>
                </div>
                
                <div class="card">
                    <h3>Place Order</h3>
                    <form class="order-form" onsubmit="submitOrder(event)">
                        <select id="symbol">
                            <option value="ALOG/CC">ActiveLog (ALOG/CC)</option>
                            <option value="DMLOG/CC">DMLog (DMLOG/CC)</option>
                            <option value="STUDY/CC">StudyLog (STUDY/CC)</option>
                            <option value="FISH/CC">FishingLog (FISH/CC)</option>
                        </select>
                        <select id="side">
                            <option value="buy">Buy</option>
                            <option value="sell">Sell</option>
                        </select>
                        <select id="order_type">
                            <option value="market">Market Order</option>
                            <option value="limit">Limit Order</option>
                        </select>
                        <input type="number" id="quantity" placeholder="Quantity" step="0.01" required>
                        <input type="number" id="price" placeholder="Price (for limit orders)" step="0.01">
                        <input type="text" id="user_id" placeholder="User ID" required>
                        <button type="submit">Submit Order</button>
                    </form>
                </div>
                
                <div class="card">
                    <h3>Portfolio</h3>
                    <div id="portfolio">
                        <input type="text" id="portfolio_user_id" placeholder="Enter User ID" style="margin-bottom: 10px; padding: 8px; width: 100%;">
                        <button onclick="loadPortfolio()" style="margin-bottom: 15px; padding: 8px 16px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">Load Portfolio</button>
                        <div id="portfolio-data">Enter User ID to view portfolio</div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 20px;" class="grid">
                <div class="card">
                    <h3>Price Chart</h3>
                    <div id="chart"></div>
                </div>
                
                <div class="card">
                    <h3>Order Book</h3>
                    <div id="order-book" class="order-book">
                        Loading...
                    </div>
                </div>
                
                <div class="card">
                    <h3>Recent Trades</h3>
                    <div id="recent-trades" class="recent-trades">
                        Loading...
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let currentSymbol = 'ALOG/CC';
            let ws;
            
            // Initialize WebSocket connection
            function initWebSocket() {
                const wsUrl = `ws://${window.location.host}/ws/market-data`;
                ws = new WebSocket(wsUrl);
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'market_update') {
                        updateMarketData(data.symbol, data.data);
                    }
                };
                
                ws.onclose = function() {
                    setTimeout(initWebSocket, 3000); // Reconnect after 3 seconds
                };
            }
            
            // Load initial data
            async function loadMarketOverview() {
                try {
                    const response = await fetch('/api/market/overview');
                    const data = await response.json();
                    
                    let html = '';
                    for (const [symbol, marketData] of Object.entries(data)) {
                        const market = marketData.market_data;
                        if (market) {
                            const changeClass = market.change_24h >= 0 ? 'positive' : 'negative';
                            html += `
                                <div class="metric">
                                    <div class="label">${symbol}</div>
                                    <div class="value">$${market.last_price?.toFixed(2) || '0.00'}</div>
                                    <div class="${changeClass}">${market.change_24h >= 0 ? '+' : ''}${(market.change_percent_24h || 0).toFixed(2)}%</div>
                                </div>
                            `;
                        }
                    }
                    document.getElementById('market-overview').innerHTML = html;
                } catch (error) {
                    console.error('Error loading market overview:', error);
                }
            }
            
            async function loadOrderBook() {
                try {
                    const response = await fetch(`/api/market/${currentSymbol}`);
                    const data = await response.json();
                    const depth = data.depth;
                    
                    let html = '<table><tr><th>Price</th><th>Size</th><th>Orders</th></tr>';
                    
                    // Asks (sell orders) - reverse order for better visualization
                    if (depth.asks) {
                        for (let i = Math.min(5, depth.asks.length) - 1; i >= 0; i--) {
                            const ask = depth.asks[i];
                            html += `<tr class="ask"><td>$${ask.price}</td><td>${ask.quantity}</td><td>${ask.orders}</td></tr>`;
                        }
                    }
                    
                    html += '<tr style="border-top: 2px solid #666;"><td colspan="3" style="text-align: center; color: #ccc;">SPREAD</td></tr>';
                    
                    // Bids (buy orders)
                    if (depth.bids) {
                        for (let i = 0; i < Math.min(5, depth.bids.length); i++) {
                            const bid = depth.bids[i];
                            html += `<tr class="bid"><td>$${bid.price}</td><td>${bid.quantity}</td><td>${bid.orders}</td></tr>`;
                        }
                    }
                    
                    html += '</table>';
                    document.getElementById('order-book').innerHTML = html;
                } catch (error) {
                    console.error('Error loading order book:', error);
                }
            }
            
            async function loadRecentTrades() {
                try {
                    const response = await fetch(`/api/market/${currentSymbol}/trades?limit=10`);
                    const trades = await response.json();
                    
                    let html = '';
                    trades.forEach(trade => {
                        const time = new Date(trade.executed_at).toLocaleTimeString();
                        html += `
                            <div class="trade">
                                <span>${time}</span>
                                <span>$${trade.price}</span>
                                <span>${trade.quantity}</span>
                            </div>
                        `;
                    });
                    
                    document.getElementById('recent-trades').innerHTML = html || 'No recent trades';
                } catch (error) {
                    console.error('Error loading recent trades:', error);
                }
            }
            
            async function loadChart() {
                try {
                    const response = await fetch(`/api/market/${currentSymbol}/chart?interval=1h&limit=24`);
                    const data = await response.json();
                    
                    if (data.length === 0) {
                        document.getElementById('chart').innerHTML = '<p>No chart data available</p>';
                        return;
                    }
                    
                    const trace = {
                        x: data.map(d => d.timestamp),
                        close: data.map(d => d.close),
                        high: data.map(d => d.high),
                        low: data.map(d => d.low),
                        open: data.map(d => d.open),
                        type: 'candlestick'
                    };
                    
                    const layout = {
                        title: `${currentSymbol} Price Chart`,
                        plot_bgcolor: '#2d2d2d',
                        paper_bgcolor: '#2d2d2d',
                        font: { color: '#fff' },
                        xaxis: { gridcolor: '#444' },
                        yaxis: { gridcolor: '#444' }
                    };
                    
                    Plotly.newPlot('chart', [trace], layout, {displayModeBar: false});
                } catch (error) {
                    console.error('Error loading chart:', error);
                    document.getElementById('chart').innerHTML = '<p>Error loading chart data</p>';
                }
            }
            
            async function loadPortfolio() {
                const userId = document.getElementById('portfolio_user_id').value;
                if (!userId) return;
                
                try {
                    const response = await fetch(`/api/portfolio/${userId}`);
                    
                    if (!response.ok) {
                        if (response.status === 404) {
                            // Create portfolio if it doesn't exist
                            const createResponse = await fetch(`/api/portfolio/create?user_id=${userId}`, { method: 'POST' });
                            if (createResponse.ok) {
                                loadPortfolio(); // Retry loading
                                return;
                            }
                        }
                        throw new Error(`HTTP ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    let html = `
                        <div class="metric">
                            <div class="label">Total Value</div>
                            <div class="value">$${data.total_value_cc.toFixed(2)}</div>
                        </div>
                        <div class="metric">
                            <div class="label">Cash</div>
                            <div class="value">$${data.cash_balance.toFixed(2)}</div>
                        </div>
                        <div class="metric">
                            <div class="label">P&L</div>
                            <div class="value ${data.total_pnl >= 0 ? 'positive' : 'negative'}">
                                ${data.total_pnl >= 0 ? '+' : ''}$${data.total_pnl.toFixed(2)}
                            </div>
                        </div>
                    `;
                    
                    if (data.positions && data.positions.length > 0) {
                        html += '<h4 style="margin-top: 20px; margin-bottom: 10px;">Positions</h4>';
                        data.positions.forEach(pos => {
                            const pnlClass = pos.unrealized_pnl >= 0 ? 'positive' : 'negative';
                            html += `
                                <div style="padding: 8px; margin: 5px 0; background: #3d3d3d; border-radius: 4px;">
                                    <div style="font-weight: bold;">${pos.symbol}</div>
                                    <div>Qty: ${pos.quantity} | Avg Cost: $${pos.average_cost.toFixed(2)}</div>
                                    <div class="${pnlClass}">P&L: ${pos.unrealized_pnl >= 0 ? '+' : ''}$${pos.unrealized_pnl.toFixed(2)}</div>
                                </div>
                            `;
                        });
                    }
                    
                    document.getElementById('portfolio-data').innerHTML = html;
                } catch (error) {
                    console.error('Error loading portfolio:', error);
                    document.getElementById('portfolio-data').innerHTML = `<p>Error loading portfolio: ${error.message}</p>`;
                }
            }
            
            async function submitOrder(event) {
                event.preventDefault();
                
                const orderData = {
                    user_id: document.getElementById('user_id').value,
                    symbol: document.getElementById('symbol').value,
                    side: document.getElementById('side').value,
                    order_type: document.getElementById('order_type').value,
                    quantity: parseFloat(document.getElementById('quantity').value)
                };
                
                const price = document.getElementById('price').value;
                if (price && orderData.order_type === 'limit') {
                    orderData.price = parseFloat(price);
                }
                
                try {
                    const response = await fetch('/api/orders/submit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(orderData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        alert(`Order submitted successfully! Order ID: ${result.order_id}`);
                        document.querySelector('.order-form').reset();
                        
                        // Refresh data
                        loadMarketOverview();
                        loadOrderBook();
                        loadRecentTrades();
                    } else {
                        alert(`Error: ${result.detail}`);
                    }
                } catch (error) {
                    alert(`Error submitting order: ${error.message}`);
                }
            }
            
            function updateMarketData(symbol, data) {
                // Update real-time market data display
                // Implementation would update relevant UI elements
            }
            
            // Initialize everything
            document.addEventListener('DOMContentLoaded', function() {
                loadMarketOverview();
                loadOrderBook();
                loadRecentTrades();
                loadChart();
                initWebSocket();
                
                // Update data every 30 seconds
                setInterval(() => {
                    loadMarketOverview();
                    loadOrderBook();
                    loadRecentTrades();
                }, 30000);
                
                // Update chart every 5 minutes
                setInterval(loadChart, 300000);
            });
        </script>
    </body>
    </html>
    """)

async def process_trade(trade: Trade):
    """Process trade in background - update market data and portfolios"""
    try:
        # Update market data
        await market_data_provider.update_with_trade(trade)
        
        # Process portfolios
        await portfolio_manager.process_trade(trade)
        
        # Check for circuit breaker triggers
        circuit_breaker.check_price_movement(trade.symbol, trade.price)
        
        logger.info(f"Processed trade: {trade.quantity} {trade.symbol} at {trade.price}")
        
    except Exception as e:
        logger.error(f"Error processing trade {trade.trade_id}: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8411)