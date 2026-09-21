import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import random

from .models import (Order, OrderSide, OrderType, MarketSymbol, LiquidityPool, 
                    MarketMakerConfig, CircuitBreaker, OrderStatus)
from .order_book import MatchingEngine

logger = logging.getLogger(__name__)

class AutomatedMarketMaker:
    """Automated Market Maker using constant product formula (x * y = k)"""
    
    def __init__(self):
        self.liquidity_pools: Dict[MarketSymbol, LiquidityPool] = {}
        self.fee_collector = Decimal('0')  # Accumulated fees
        
    def create_pool(self, symbol: MarketSymbol, base_amount: Decimal, 
                   quote_amount: Decimal) -> LiquidityPool:
        """Create a new liquidity pool for a trading pair"""
        pool = LiquidityPool(
            symbol=symbol,
            base_reserve=base_amount,    # CC reserves
            quote_reserve=quote_amount,  # Asset reserves
            total_liquidity=base_amount * quote_amount
        )
        
        self.liquidity_pools[symbol] = pool
        logger.info(f"Created liquidity pool for {symbol} with {base_amount} CC and {quote_amount} assets")
        return pool
    
    def add_liquidity(self, symbol: MarketSymbol, base_amount: Decimal, 
                     quote_amount: Decimal) -> Decimal:
        """Add liquidity to existing pool"""
        pool = self.liquidity_pools.get(symbol)
        if not pool:
            return self.create_pool(symbol, base_amount, quote_amount).total_liquidity
        
        # Calculate liquidity tokens to mint
        base_ratio = base_amount / pool.base_reserve
        quote_ratio = quote_amount / pool.quote_reserve
        
        # Use minimum ratio to prevent arbitrage
        liquidity_ratio = min(base_ratio, quote_ratio)
        liquidity_tokens = pool.total_liquidity * liquidity_ratio
        
        # Update pool reserves
        pool.base_reserve += base_amount
        pool.quote_reserve += quote_amount
        pool.total_liquidity += liquidity_tokens
        pool.k_constant = pool.base_reserve * pool.quote_reserve
        
        return liquidity_tokens
    
    def remove_liquidity(self, symbol: MarketSymbol, liquidity_tokens: Decimal) -> Tuple[Decimal, Decimal]:
        """Remove liquidity from pool"""
        pool = self.liquidity_pools.get(symbol)
        if not pool:
            raise ValueError("Pool not found")
        
        if liquidity_tokens > pool.total_liquidity:
            raise ValueError("Insufficient liquidity")
        
        # Calculate proportional withdrawal
        withdrawal_ratio = liquidity_tokens / pool.total_liquidity
        base_withdrawal = pool.base_reserve * withdrawal_ratio
        quote_withdrawal = pool.quote_reserve * withdrawal_ratio
        
        # Update pool
        pool.base_reserve -= base_withdrawal
        pool.quote_reserve -= quote_withdrawal
        pool.total_liquidity -= liquidity_tokens
        pool.k_constant = pool.base_reserve * pool.quote_reserve
        
        return base_withdrawal, quote_withdrawal
    
    def get_swap_quote(self, symbol: MarketSymbol, input_amount: Decimal, 
                      is_base_to_quote: bool = True) -> Dict:
        """Get quote for swapping tokens using AMM"""
        pool = self.liquidity_pools.get(symbol)
        if not pool:
            return {'error': 'Pool not found'}
        
        if is_base_to_quote:
            # Swapping CC (base) for assets (quote)
            input_reserve = pool.base_reserve
            output_reserve = pool.quote_reserve
        else:
            # Swapping assets (quote) for CC (base)
            input_reserve = pool.quote_reserve
            output_reserve = pool.base_reserve
        
        # Apply fee
        input_amount_after_fee = input_amount * (Decimal('1') - pool.fee_rate)
        
        # Calculate output using constant product formula
        # (x + Δx)(y - Δy) = k
        # Δy = (y * Δx) / (x + Δx)
        output_amount = (output_reserve * input_amount_after_fee) / (input_reserve + input_amount_after_fee)
        
        # Calculate price impact
        price_before = output_reserve / input_reserve
        new_input_reserve = input_reserve + input_amount_after_fee
        new_output_reserve = output_reserve - output_amount
        price_after = new_output_reserve / new_input_reserve
        price_impact = abs(price_after - price_before) / price_before * 100
        
        # Calculate fee
        fee_amount = input_amount * pool.fee_rate
        
        return {
            'input_amount': float(input_amount),
            'output_amount': float(output_amount),
            'price_impact': float(price_impact),
            'fee': float(fee_amount),
            'effective_price': float(input_amount / output_amount) if output_amount > 0 else 0,
            'minimum_output': float(output_amount * Decimal('0.995'))  # 0.5% slippage tolerance
        }
    
    def execute_swap(self, symbol: MarketSymbol, input_amount: Decimal, 
                    is_base_to_quote: bool = True, min_output: Optional[Decimal] = None) -> Dict:
        """Execute token swap through AMM"""
        pool = self.liquidity_pools.get(symbol)
        if not pool:
            return {'error': 'Pool not found'}
        
        quote = self.get_swap_quote(symbol, input_amount, is_base_to_quote)
        if 'error' in quote:
            return quote
        
        output_amount = Decimal(str(quote['output_amount']))
        
        # Check minimum output (slippage protection)
        if min_output and output_amount < min_output:
            return {'error': 'Output below minimum threshold (slippage protection)'}
        
        # Execute swap
        fee_amount = input_amount * pool.fee_rate
        input_amount_after_fee = input_amount - fee_amount
        
        if is_base_to_quote:
            pool.base_reserve += input_amount_after_fee
            pool.quote_reserve -= output_amount
        else:
            pool.quote_reserve += input_amount_after_fee
            pool.base_reserve -= output_amount
        
        # Update k constant (should remain the same)
        pool.k_constant = pool.base_reserve * pool.quote_reserve
        
        # Collect fees
        self.fee_collector += fee_amount
        
        return {
            'success': True,
            'input_amount': float(input_amount),
            'output_amount': float(output_amount),
            'fee_paid': float(fee_amount),
            'new_base_reserve': float(pool.base_reserve),
            'new_quote_reserve': float(pool.quote_reserve)
        }
    
    def get_pool_info(self, symbol: MarketSymbol) -> Dict:
        """Get liquidity pool information"""
        pool = self.liquidity_pools.get(symbol)
        if not pool:
            return {'error': 'Pool not found'}
        
        current_price = pool.base_reserve / pool.quote_reserve if pool.quote_reserve > 0 else Decimal('0')
        
        return {
            'symbol': symbol.value,
            'base_reserve': float(pool.base_reserve),
            'quote_reserve': float(pool.quote_reserve),
            'k_constant': float(pool.k_constant),
            'total_liquidity': float(pool.total_liquidity),
            'current_price': float(current_price),
            'fee_rate': float(pool.fee_rate),
            'created_at': pool.created_at.isoformat()
        }

class MarketMaker:
    """Market maker that provides liquidity through continuous buy/sell orders"""
    
    def __init__(self, matching_engine: MatchingEngine):
        self.matching_engine = matching_engine
        self.configs: Dict[MarketSymbol, MarketMakerConfig] = {}
        self.active_orders: Dict[str, Order] = {}
        self.inventory: Dict[MarketSymbol, Decimal] = {}
        self.is_running = False
        
    def configure(self, symbol: MarketSymbol, config: MarketMakerConfig):
        """Configure market maker for a symbol"""
        self.configs[symbol] = config
        self.inventory[symbol] = config.inventory_target
        logger.info(f"Configured market maker for {symbol}")
    
    async def start(self):
        """Start market making operations"""
        self.is_running = True
        await self._market_making_loop()
    
    async def stop(self):
        """Stop market making operations"""
        self.is_running = False
        await self._cancel_all_orders()
    
    async def _market_making_loop(self):
        """Main market making loop"""
        while self.is_running:
            for symbol, config in self.configs.items():
                if config.enabled:
                    await self._update_quotes(symbol)
            
            await asyncio.sleep(1)  # Update quotes every second
    
    async def _update_quotes(self, symbol: MarketSymbol):
        """Update buy/sell quotes for a symbol"""
        config = self.configs[symbol]
        order_book = self.matching_engine.get_order_book(symbol)
        
        # Get current market price (mid-price)
        best_bid = order_book.get_best_bid()
        best_ask = order_book.get_best_ask()
        
        if best_bid and best_ask:
            mid_price = (best_bid + best_ask) / 2
        elif best_bid:
            mid_price = best_bid
        elif best_ask:
            mid_price = best_ask
        else:
            mid_price = Decimal('100')  # Default starting price
        
        # Calculate spread
        half_spread = mid_price * config.spread_percentage / 2
        bid_price = mid_price - half_spread
        ask_price = mid_price + half_spread
        
        # Check inventory and adjust quotes
        current_inventory = self.inventory.get(symbol, Decimal('0'))
        inventory_imbalance = (current_inventory - config.inventory_target) / config.inventory_target
        
        # Adjust prices based on inventory (inventory risk management)
        if inventory_imbalance > config.rebalance_threshold:
            # Too much inventory, make selling more attractive
            bid_price *= (Decimal('1') - config.risk_limit)
            ask_price *= (Decimal('1') - config.risk_limit / 2)
        elif inventory_imbalance < -config.rebalance_threshold:
            # Too little inventory, make buying more attractive
            bid_price *= (Decimal('1') + config.risk_limit / 2)
            ask_price *= (Decimal('1') + config.risk_limit)
        
        # Cancel existing orders and place new ones
        await self._cancel_symbol_orders(symbol)
        await self._place_market_maker_orders(symbol, bid_price, ask_price, config.max_order_size)
    
    async def _place_market_maker_orders(self, symbol: MarketSymbol, bid_price: Decimal, 
                                       ask_price: Decimal, max_size: Decimal):
        """Place market maker buy and sell orders"""
        # Place buy order
        buy_order = Order(
            user_id="market_maker",
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=max_size,
            price=bid_price
        )
        
        # Place sell order
        sell_order = Order(
            user_id="market_maker",
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=max_size,
            price=ask_price
        )
        
        # Submit orders
        await self.matching_engine.submit_order(buy_order)
        await self.matching_engine.submit_order(sell_order)
        
        self.active_orders[buy_order.order_id] = buy_order
        self.active_orders[sell_order.order_id] = sell_order
        
        logger.debug(f"Placed MM orders for {symbol}: BID {bid_price} ASK {ask_price}")
    
    async def _cancel_symbol_orders(self, symbol: MarketSymbol):
        """Cancel all active orders for a symbol"""
        orders_to_cancel = [
            order for order in self.active_orders.values() 
            if order.symbol == symbol and order.status == OrderStatus.PENDING
        ]
        
        for order in orders_to_cancel:
            await self.matching_engine.cancel_order(order.order_id, symbol)
            if order.order_id in self.active_orders:
                del self.active_orders[order.order_id]
    
    async def _cancel_all_orders(self):
        """Cancel all active market maker orders"""
        for order in list(self.active_orders.values()):
            if order.status == OrderStatus.PENDING:
                await self.matching_engine.cancel_order(order.order_id, order.symbol)
        self.active_orders.clear()
    
    def update_inventory(self, symbol: MarketSymbol, quantity_change: Decimal):
        """Update inventory after a trade"""
        current = self.inventory.get(symbol, Decimal('0'))
        self.inventory[symbol] = current + quantity_change

class CircuitBreakerManager:
    """Manages circuit breakers to halt trading during extreme volatility"""
    
    def __init__(self):
        self.circuit_breakers: Dict[MarketSymbol, CircuitBreaker] = {}
        self.price_history: Dict[MarketSymbol, List[Tuple[datetime, Decimal]]] = {}
        
    def initialize_symbol(self, symbol: MarketSymbol):
        """Initialize circuit breaker for a symbol"""
        self.circuit_breakers[symbol] = CircuitBreaker(symbol=symbol)
        self.price_history[symbol] = []
    
    def check_price_movement(self, symbol: MarketSymbol, price: Decimal) -> bool:
        """Check if price movement triggers circuit breaker"""
        if symbol not in self.circuit_breakers:
            self.initialize_symbol(symbol)
        
        breaker = self.circuit_breakers[symbol]
        if breaker.trading_halted:
            # Check if halt period has expired
            if (breaker.halt_started_at and 
                datetime.now() - breaker.halt_started_at > timedelta(minutes=breaker.halt_duration_minutes)):
                breaker.trading_halted = False
                breaker.halt_started_at = None
                logger.info(f"Trading halt lifted for {symbol}")
                return False
            return True
        
        # Track price history
        now = datetime.now()
        price_history = self.price_history[symbol]
        price_history.append((now, price))
        
        # Keep only recent history (last hour)
        cutoff = now - timedelta(hours=1)
        price_history[:] = [(t, p) for t, p in price_history if t >= cutoff]
        
        if len(price_history) < 2:
            return False
        
        # Check for price change threshold breach
        earliest_price = price_history[0][1]
        price_change = abs(price - earliest_price) / earliest_price
        
        if price_change >= breaker.price_change_threshold:
            self._trigger_halt(symbol, f"Price change of {price_change:.2%} exceeds threshold")
            return True
        
        # Check for volume spike (simplified - in real implementation would track volume)
        return False
    
    def _trigger_halt(self, symbol: MarketSymbol, reason: str):
        """Trigger trading halt for a symbol"""
        breaker = self.circuit_breakers[symbol]
        breaker.trading_halted = True
        breaker.halt_started_at = datetime.now()
        
        logger.warning(f"Circuit breaker triggered for {symbol}: {reason}")
    
    def is_trading_halted(self, symbol: MarketSymbol) -> bool:
        """Check if trading is halted for a symbol"""
        breaker = self.circuit_breakers.get(symbol)
        return breaker.trading_halted if breaker else False
    
    def force_halt(self, symbol: MarketSymbol, duration_minutes: int = 15):
        """Manually halt trading for a symbol"""
        if symbol not in self.circuit_breakers:
            self.initialize_symbol(symbol)
        
        breaker = self.circuit_breakers[symbol]
        breaker.trading_halted = True
        breaker.halt_started_at = datetime.now()
        breaker.halt_duration_minutes = duration_minutes
        
        logger.info(f"Manual trading halt for {symbol} - duration: {duration_minutes} minutes")
    
    def lift_halt(self, symbol: MarketSymbol):
        """Manually lift trading halt"""
        breaker = self.circuit_breakers.get(symbol)
        if breaker:
            breaker.trading_halted = False
            breaker.halt_started_at = None
            logger.info(f"Manual lift of trading halt for {symbol}")

class ArbitrageDetector:
    """Detects and prevents arbitrage opportunities"""
    
    def __init__(self, amm: AutomatedMarketMaker, matching_engine: MatchingEngine):
        self.amm = amm
        self.matching_engine = matching_engine
        self.price_tolerance = Decimal('0.01')  # 1% price tolerance
    
    async def check_arbitrage_opportunity(self, symbol: MarketSymbol) -> Optional[Dict]:
        """Check for arbitrage between AMM and order book"""
        # Get AMM price
        pool = self.amm.liquidity_pools.get(symbol)
        if not pool:
            return None
        
        amm_price = pool.base_reserve / pool.quote_reserve
        
        # Get order book price
        order_book = self.matching_engine.get_order_book(symbol)
        best_bid = order_book.get_best_bid()
        best_ask = order_book.get_best_ask()
        
        if not best_bid or not best_ask:
            return None
        
        ob_mid_price = (best_bid + best_ask) / 2
        
        # Check for significant price difference
        price_diff = abs(amm_price - ob_mid_price) / ob_mid_price
        
        if price_diff > self.price_tolerance:
            return {
                'symbol': symbol.value,
                'amm_price': float(amm_price),
                'orderbook_price': float(ob_mid_price),
                'price_difference': float(price_diff),
                'arbitrage_direction': 'buy_amm_sell_ob' if amm_price < ob_mid_price else 'buy_ob_sell_amm'
            }
        
        return None
    
    async def execute_arbitrage(self, arbitrage_info: Dict, amount: Decimal) -> Dict:
        """Execute arbitrage trade (for authorized arbitrageurs)"""
        symbol = MarketSymbol(arbitrage_info['symbol'])
        direction = arbitrage_info['arbitrage_direction']
        
        try:
            if direction == 'buy_amm_sell_ob':
                # Buy from AMM, sell on order book
                amm_result = self.amm.execute_swap(symbol, amount, is_base_to_quote=False)
                if not amm_result.get('success'):
                    return amm_result
                
                # Place sell order on order book
                sell_order = Order(
                    user_id="arbitrageur",
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=Decimal(str(amm_result['output_amount']))
                )
                
                trades = await self.matching_engine.submit_order(sell_order)
                
                return {
                    'success': True,
                    'amm_trade': amm_result,
                    'orderbook_trades': len(trades),
                    'total_profit': 'calculated_separately'  # Would calculate actual profit
                }
            
            else:
                # Buy from order book, sell to AMM
                buy_order = Order(
                    user_id="arbitrageur",
                    symbol=symbol,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=amount
                )
                
                trades = await self.matching_engine.submit_order(buy_order)
                
                if trades:
                    total_bought = sum(t.quantity for t in trades)
                    amm_result = self.amm.execute_swap(symbol, total_bought, is_base_to_quote=True)
                    
                    return {
                        'success': True,
                        'orderbook_trades': len(trades),
                        'amm_trade': amm_result,
                        'total_profit': 'calculated_separately'
                    }
                
                return {'error': 'No trades executed on order book'}
                
        except Exception as e:
            logger.error(f"Arbitrage execution failed: {e}")
            return {'error': str(e)}