import asyncio
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from .models import Portfolio, Position, MarketSymbol, Trade, Order
from .trading_interface import MarketDataProvider

logger = logging.getLogger(__name__)

class TaxLot:
    """Represents a tax lot for tracking cost basis and holding period"""
    def __init__(self, symbol: MarketSymbol, quantity: Decimal, cost_per_share: Decimal, 
                 acquisition_date: datetime):
        self.symbol = symbol
        self.quantity = quantity
        self.cost_per_share = cost_per_share
        self.acquisition_date = acquisition_date
        self.cost_basis = quantity * cost_per_share
        self.remaining_quantity = quantity
    
    def sell_shares(self, quantity_to_sell: Decimal) -> Tuple[Decimal, Decimal]:
        """Sell shares from this lot and return realized gain/loss"""
        if quantity_to_sell > self.remaining_quantity:
            quantity_to_sell = self.remaining_quantity
        
        cost_basis_sold = quantity_to_sell * self.cost_per_share
        self.remaining_quantity -= quantity_to_sell
        
        return quantity_to_sell, cost_basis_sold
    
    def is_long_term(self) -> bool:
        """Check if position qualifies for long-term capital gains"""
        holding_period = datetime.now() - self.acquisition_date
        return holding_period.days > 365

class PortfolioManager:
    def __init__(self, market_data_provider: MarketDataProvider):
        self.market_data_provider = market_data_provider
        self.portfolios: Dict[str, Portfolio] = {}  # user_id -> Portfolio
        self.positions: Dict[str, Dict[MarketSymbol, Position]] = {}  # user_id -> symbol -> Position
        self.tax_lots: Dict[str, Dict[MarketSymbol, List[TaxLot]]] = {}  # user_id -> symbol -> [TaxLot]
        self.trade_history: Dict[str, List[Trade]] = {}  # user_id -> [Trade]
        self.performance_history: Dict[str, List[Tuple[datetime, Decimal]]] = {}  # user_id -> [(timestamp, value)]
    
    def create_portfolio(self, user_id: str, initial_cash: Decimal = Decimal('10000')) -> Portfolio:
        """Create a new portfolio for a user"""
        portfolio = Portfolio(
            user_id=user_id,
            cash_balance=initial_cash,
            holdings={},
            total_value_cc=initial_cash
        )
        
        self.portfolios[user_id] = portfolio
        self.positions[user_id] = {}
        self.tax_lots[user_id] = defaultdict(list)
        self.trade_history[user_id] = []
        self.performance_history[user_id] = [(datetime.now(), initial_cash)]
        
        logger.info(f"Created portfolio for user {user_id} with {initial_cash} CC")
        return portfolio
    
    def get_portfolio(self, user_id: str) -> Optional[Portfolio]:
        """Get portfolio for a user"""
        return self.portfolios.get(user_id)
    
    async def process_trade(self, trade: Trade):
        """Process a trade and update relevant portfolios"""
        # Update buyer's portfolio
        await self._update_portfolio_for_trade(trade.buyer_id, trade, is_buyer=True)
        
        # Update seller's portfolio
        await self._update_portfolio_for_trade(trade.seller_id, trade, is_buyer=False)
    
    async def _update_portfolio_for_trade(self, user_id: str, trade: Trade, is_buyer: bool):
        """Update a user's portfolio based on a trade"""
        portfolio = self.get_portfolio(user_id)
        if not portfolio:
            # Create portfolio if it doesn't exist
            portfolio = self.create_portfolio(user_id)
        
        # Add to trade history
        self.trade_history[user_id].append(trade)
        
        if is_buyer:
            # Buyer: decrease cash, increase holdings
            total_cost = trade.quantity * trade.price
            portfolio.cash_balance -= total_cost
            
            # Update holdings
            symbol_str = trade.symbol.value
            current_holding = portfolio.holdings.get(symbol_str, Decimal('0'))
            portfolio.holdings[symbol_str] = current_holding + trade.quantity
            
            # Create tax lot
            tax_lot = TaxLot(
                symbol=trade.symbol,
                quantity=trade.quantity,
                cost_per_share=trade.price,
                acquisition_date=trade.executed_at
            )
            self.tax_lots[user_id][trade.symbol].append(tax_lot)
            
        else:
            # Seller: increase cash, decrease holdings
            total_proceeds = trade.quantity * trade.price
            portfolio.cash_balance += total_proceeds
            
            # Update holdings
            symbol_str = trade.symbol.value
            current_holding = portfolio.holdings.get(symbol_str, Decimal('0'))
            portfolio.holdings[symbol_str] = current_holding - trade.quantity
            
            # Process tax lots (FIFO)
            realized_gain = await self._process_sale(user_id, trade)
            portfolio.total_pnl += realized_gain
        
        # Update position
        await self._update_position(user_id, trade.symbol)
        
        # Recalculate portfolio value
        await self._recalculate_portfolio_value(user_id)
        
        portfolio.last_updated = datetime.now()
    
    async def _process_sale(self, user_id: str, trade: Trade) -> Decimal:
        """Process sale using FIFO tax lot method"""
        symbol_lots = self.tax_lots[user_id][trade.symbol]
        quantity_to_sell = trade.quantity
        total_cost_basis = Decimal('0')
        
        # Process lots in FIFO order
        lots_to_remove = []
        for i, lot in enumerate(symbol_lots):
            if quantity_to_sell <= 0:
                break
            
            quantity_sold, cost_basis_sold = lot.sell_shares(quantity_to_sell)
            total_cost_basis += cost_basis_sold
            quantity_to_sell -= quantity_sold
            
            if lot.remaining_quantity == 0:
                lots_to_remove.append(i)
        
        # Remove empty lots
        for i in reversed(lots_to_remove):
            del symbol_lots[i]
        
        # Calculate realized gain/loss
        total_proceeds = trade.quantity * trade.price
        realized_gain = total_proceeds - total_cost_basis
        
        return realized_gain
    
    async def _update_position(self, user_id: str, symbol: MarketSymbol):
        """Update position for a symbol"""
        portfolio = self.get_portfolio(user_id)
        if not portfolio:
            return
        
        symbol_str = symbol.value
        quantity = portfolio.holdings.get(symbol_str, Decimal('0'))
        
        if quantity == 0:
            # Remove position if no holdings
            if user_id in self.positions and symbol in self.positions[user_id]:
                del self.positions[user_id][symbol]
            return
        
        # Calculate average cost from tax lots
        lots = self.tax_lots[user_id][symbol]
        total_cost_basis = sum(lot.remaining_quantity * lot.cost_per_share for lot in lots)
        average_cost = total_cost_basis / quantity if quantity > 0 else Decimal('0')
        
        # Get current market price
        market_data = self.market_data_provider.get_market_summary(symbol)
        current_price = Decimal(str(market_data.get('last_price', 0)))
        
        # Calculate position metrics
        market_value = quantity * current_price
        unrealized_pnl = market_value - total_cost_basis
        
        position = Position(
            user_id=user_id,
            symbol=symbol,
            quantity=quantity,
            average_cost=average_cost,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            cost_basis=total_cost_basis
        )
        
        if user_id not in self.positions:
            self.positions[user_id] = {}
        
        self.positions[user_id][symbol] = position
    
    async def _recalculate_portfolio_value(self, user_id: str):
        """Recalculate total portfolio value"""
        portfolio = self.get_portfolio(user_id)
        if not portfolio:
            return
        
        total_value = portfolio.cash_balance
        
        # Add value of all holdings
        for symbol_str, quantity in portfolio.holdings.items():
            if quantity > 0:
                try:
                    symbol = MarketSymbol(symbol_str)
                    market_data = self.market_data_provider.get_market_summary(symbol)
                    current_price = Decimal(str(market_data.get('last_price', 0)))
                    total_value += quantity * current_price
                except ValueError:
                    logger.warning(f"Invalid symbol in holdings: {symbol_str}")
        
        # Calculate daily P&L
        previous_value = portfolio.total_value_cc
        portfolio.daily_pnl = total_value - previous_value
        portfolio.total_value_cc = total_value
        
        # Update performance history
        self.performance_history[user_id].append((datetime.now(), total_value))
        
        # Keep only last 365 days of history
        cutoff_date = datetime.now() - timedelta(days=365)
        self.performance_history[user_id] = [
            (timestamp, value) for timestamp, value in self.performance_history[user_id]
            if timestamp >= cutoff_date
        ]
    
    def get_positions(self, user_id: str) -> List[Position]:
        """Get all positions for a user"""
        return list(self.positions.get(user_id, {}).values())
    
    async def get_portfolio_summary(self, user_id: str) -> Dict:
        """Get comprehensive portfolio summary"""
        portfolio = self.get_portfolio(user_id)
        if not portfolio:
            return {'error': 'Portfolio not found'}
        
        # Ensure portfolio is up to date
        await self._recalculate_portfolio_value(user_id)
        
        positions = self.get_positions(user_id)
        
        # Calculate diversification metrics
        diversification = self._calculate_diversification(positions)
        
        # Calculate risk metrics
        risk_metrics = await self._calculate_risk_metrics(user_id)
        
        # Get performance metrics
        performance_metrics = self._calculate_performance_metrics(user_id)
        
        return {
            'user_id': user_id,
            'cash_balance': float(portfolio.cash_balance),
            'total_value_cc': float(portfolio.total_value_cc),
            'total_value_usd': float(portfolio.total_value_usd),
            'daily_pnl': float(portfolio.daily_pnl),
            'total_pnl': float(portfolio.total_pnl),
            'positions': [
                {
                    'symbol': pos.symbol.value,
                    'quantity': float(pos.quantity),
                    'average_cost': float(pos.average_cost),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'unrealized_pnl': float(pos.unrealized_pnl),
                    'cost_basis': float(pos.cost_basis),
                    'weight': float(pos.market_value / portfolio.total_value_cc) if portfolio.total_value_cc > 0 else 0
                } for pos in positions
            ],
            'diversification': diversification,
            'risk_metrics': risk_metrics,
            'performance': performance_metrics,
            'last_updated': portfolio.last_updated.isoformat()
        }
    
    def _calculate_diversification(self, positions: List[Position]) -> Dict:
        """Calculate portfolio diversification metrics"""
        if not positions:
            return {'concentration': 0, 'herfindahl_index': 0, 'effective_positions': 0}
        
        total_value = sum(pos.market_value for pos in positions)
        if total_value == 0:
            return {'concentration': 0, 'herfindahl_index': 0, 'effective_positions': 0}
        
        weights = [pos.market_value / total_value for pos in positions]
        
        # Concentration (largest position weight)
        concentration = max(weights)
        
        # Herfindahl-Hirschman Index
        hhi = sum(w ** 2 for w in weights)
        
        # Effective number of positions
        effective_positions = 1 / hhi if hhi > 0 else 0
        
        return {
            'concentration': float(concentration),
            'herfindahl_index': float(hhi),
            'effective_positions': float(effective_positions),
            'number_of_positions': len(positions)
        }
    
    async def _calculate_risk_metrics(self, user_id: str) -> Dict:
        """Calculate portfolio risk metrics"""
        performance_history = self.performance_history.get(user_id, [])
        
        if len(performance_history) < 30:  # Need at least 30 days of data
            return {'volatility': None, 'max_drawdown': None, 'var_95': None}
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(performance_history)):
            prev_value = performance_history[i-1][1]
            curr_value = performance_history[i][1]
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(float(daily_return))
        
        if not returns:
            return {'volatility': None, 'max_drawdown': None, 'var_95': None}
        
        # Volatility (annualized)
        import statistics
        daily_volatility = statistics.stdev(returns) if len(returns) > 1 else 0
        annualized_volatility = daily_volatility * (365 ** 0.5)
        
        # Maximum Drawdown
        values = [float(v) for _, v in performance_history]
        peak = values[0]
        max_drawdown = 0
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        # Value at Risk (95th percentile)
        returns_sorted = sorted(returns)
        var_95 = returns_sorted[int(len(returns_sorted) * 0.05)] if returns else 0
        
        return {
            'volatility': annualized_volatility,
            'max_drawdown': max_drawdown,
            'var_95': var_95,
            'sharpe_ratio': self._calculate_sharpe_ratio(returns)
        }
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> Optional[float]:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return None
        
        import statistics
        mean_return = statistics.mean(returns)
        return_volatility = statistics.stdev(returns)
        
        if return_volatility == 0:
            return None
        
        # Annualize
        annualized_return = mean_return * 365
        annualized_volatility = return_volatility * (365 ** 0.5)
        
        return (annualized_return - risk_free_rate) / annualized_volatility
    
    def _calculate_performance_metrics(self, user_id: str) -> Dict:
        """Calculate performance metrics"""
        performance_history = self.performance_history.get(user_id, [])
        
        if len(performance_history) < 2:
            return {'total_return': 0, 'annualized_return': 0, 'best_day': 0, 'worst_day': 0}
        
        initial_value = float(performance_history[0][1])
        current_value = float(performance_history[-1][1])
        
        # Total return
        total_return = (current_value - initial_value) / initial_value if initial_value > 0 else 0
        
        # Annualized return
        days_elapsed = (performance_history[-1][0] - performance_history[0][0]).days
        if days_elapsed > 0:
            annualized_return = ((current_value / initial_value) ** (365 / days_elapsed)) - 1 if initial_value > 0 else 0
        else:
            annualized_return = 0
        
        # Best and worst days
        daily_changes = []
        for i in range(1, len(performance_history)):
            prev_value = float(performance_history[i-1][1])
            curr_value = float(performance_history[i][1])
            if prev_value > 0:
                change = (curr_value - prev_value) / prev_value
                daily_changes.append(change)
        
        best_day = max(daily_changes) if daily_changes else 0
        worst_day = min(daily_changes) if daily_changes else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'best_day': best_day,
            'worst_day': worst_day
        }
    
    def get_tax_report(self, user_id: str, tax_year: int) -> Dict:
        """Generate tax report for a specific year"""
        trades = self.trade_history.get(user_id, [])
        
        # Filter trades for tax year
        year_start = datetime(tax_year, 1, 1)
        year_end = datetime(tax_year, 12, 31, 23, 59, 59)
        year_trades = [t for t in trades if year_start <= t.executed_at <= year_end]
        
        short_term_gains = Decimal('0')
        long_term_gains = Decimal('0')
        total_proceeds = Decimal('0')
        total_cost_basis = Decimal('0')
        
        # Process sales for tax purposes
        for trade in year_trades:
            if trade.seller_id == user_id:
                # This was a sale
                proceeds = trade.quantity * trade.price
                total_proceeds += proceeds
                
                # Calculate cost basis and holding period
                # (Simplified - in practice would need to track specific lots)
                lots = self.tax_lots[user_id].get(trade.symbol, [])
                
                cost_basis = Decimal('0')
                is_long_term = False
                
                for lot in lots:
                    if lot.acquisition_date < trade.executed_at:
                        holding_period = trade.executed_at - lot.acquisition_date
                        if holding_period.days > 365:
                            is_long_term = True
                        
                        # Simplified cost basis calculation
                        cost_basis += lot.cost_per_share * trade.quantity
                        break
                
                total_cost_basis += cost_basis
                gain_loss = proceeds - cost_basis
                
                if is_long_term:
                    long_term_gains += gain_loss
                else:
                    short_term_gains += gain_loss
        
        return {
            'tax_year': tax_year,
            'short_term_gains': float(short_term_gains),
            'long_term_gains': float(long_term_gains),
            'total_gains': float(short_term_gains + long_term_gains),
            'total_proceeds': float(total_proceeds),
            'total_cost_basis': float(total_cost_basis),
            'number_of_transactions': len([t for t in year_trades if t.seller_id == user_id])
        }
    
    def get_rebalancing_suggestions(self, user_id: str, target_allocation: Dict[str, float]) -> List[Dict]:
        """Get portfolio rebalancing suggestions"""
        portfolio = self.get_portfolio(user_id)
        positions = self.get_positions(user_id)
        
        if not portfolio or not positions:
            return []
        
        current_allocation = {}
        for pos in positions:
            weight = float(pos.market_value / portfolio.total_value_cc) if portfolio.total_value_cc > 0 else 0
            current_allocation[pos.symbol.value] = weight
        
        suggestions = []
        for symbol, target_weight in target_allocation.items():
            current_weight = current_allocation.get(symbol, 0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > 0.05:  # 5% threshold
                target_value = portfolio.total_value_cc * Decimal(str(target_weight))
                current_value = portfolio.total_value_cc * Decimal(str(current_weight))
                trade_amount = target_value - current_value
                
                suggestions.append({
                    'symbol': symbol,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'weight_difference': weight_diff,
                    'action': 'buy' if weight_diff > 0 else 'sell',
                    'trade_amount_cc': float(abs(trade_amount))
                })
        
        return suggestions