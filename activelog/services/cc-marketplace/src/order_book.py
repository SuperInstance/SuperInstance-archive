import asyncio
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from decimal import Decimal
import heapq
import logging
from datetime import datetime

from .models import Order, Trade, OrderSide, OrderType, OrderStatus, MarketSymbol

logger = logging.getLogger(__name__)

class PriceLevel:
    def __init__(self, price: Decimal):
        self.price = price
        self.orders: deque[Order] = deque()
        self.total_quantity = Decimal('0')
        
    def add_order(self, order: Order):
        self.orders.append(order)
        self.total_quantity += order.remaining_quantity
        
    def remove_order(self, order: Order):
        try:
            self.orders.remove(order)
            self.total_quantity -= order.remaining_quantity
        except ValueError:
            pass
            
    def is_empty(self) -> bool:
        return len(self.orders) == 0

class OrderBook:
    def __init__(self, symbol: MarketSymbol):
        self.symbol = symbol
        self.buy_orders: Dict[Decimal, PriceLevel] = {}  # price -> PriceLevel
        self.sell_orders: Dict[Decimal, PriceLevel] = {}  # price -> PriceLevel
        self.buy_prices = []  # max heap (negative prices for max behavior)
        self.sell_prices = []  # min heap
        self.order_lookup: Dict[str, Order] = {}  # order_id -> Order
        self.last_trade_price = Decimal('0')
        self.total_volume = Decimal('0')
        self._lock = asyncio.Lock()
        
    async def add_order(self, order: Order) -> List[Trade]:
        async with self._lock:
            trades = []
            
            if order.order_type == OrderType.MARKET:
                trades = await self._execute_market_order(order)
            elif order.order_type == OrderType.LIMIT:
                trades = await self._execute_limit_order(order)
            elif order.order_type == OrderType.STOP_LOSS:
                await self._handle_stop_order(order)
            
            if order.remaining_quantity > 0 and order.status == OrderStatus.PENDING:
                self._add_to_book(order)
                
            return trades
    
    async def cancel_order(self, order_id: str) -> bool:
        async with self._lock:
            order = self.order_lookup.get(order_id)
            if not order:
                return False
                
            self._remove_from_book(order)
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            return True
    
    async def _execute_market_order(self, order: Order) -> List[Trade]:
        trades = []
        
        if order.side == OrderSide.BUY:
            # Buy market order: take from sell side (ask)
            while order.remaining_quantity > 0 and self.sell_prices:
                best_ask = self.sell_prices[0]
                if best_ask not in self.sell_orders:
                    heapq.heappop(self.sell_prices)
                    continue
                    
                price_level = self.sell_orders[best_ask]
                if price_level.is_empty():
                    del self.sell_orders[best_ask]
                    heapq.heappop(self.sell_prices)
                    continue
                
                counterparty = price_level.orders[0]
                trade = await self._execute_trade(order, counterparty, best_ask)
                trades.append(trade)
                
        else:  # SELL
            # Sell market order: take from buy side (bid)
            while order.remaining_quantity > 0 and self.buy_prices:
                best_bid = -self.buy_prices[0]  # Convert back from negative
                if best_bid not in self.buy_orders:
                    heapq.heappop(self.buy_prices)
                    continue
                    
                price_level = self.buy_orders[best_bid]
                if price_level.is_empty():
                    del self.buy_orders[best_bid]
                    heapq.heappop(self.buy_prices)
                    continue
                
                counterparty = price_level.orders[0]
                trade = await self._execute_trade(order, counterparty, best_bid)
                trades.append(trade)
        
        if order.remaining_quantity > 0:
            order.status = OrderStatus.PARTIALLY_FILLED if order.filled_quantity > 0 else OrderStatus.PENDING
        else:
            order.status = OrderStatus.FILLED
            
        return trades
    
    async def _execute_limit_order(self, order: Order) -> List[Trade]:
        trades = []
        
        if order.side == OrderSide.BUY:
            # Buy limit: can execute against sell orders at or below limit price
            while (order.remaining_quantity > 0 and self.sell_prices and 
                   self.sell_prices[0] <= order.price):
                
                best_ask = self.sell_prices[0]
                if best_ask not in self.sell_orders:
                    heapq.heappop(self.sell_prices)
                    continue
                    
                price_level = self.sell_orders[best_ask]
                if price_level.is_empty():
                    del self.sell_orders[best_ask]
                    heapq.heappop(self.sell_prices)
                    continue
                
                counterparty = price_level.orders[0]
                trade = await self._execute_trade(order, counterparty, best_ask)
                trades.append(trade)
                
        else:  # SELL
            # Sell limit: can execute against buy orders at or above limit price
            while (order.remaining_quantity > 0 and self.buy_prices and 
                   -self.buy_prices[0] >= order.price):
                
                best_bid = -self.buy_prices[0]
                if best_bid not in self.buy_orders:
                    heapq.heappop(self.buy_prices)
                    continue
                    
                price_level = self.buy_orders[best_bid]
                if price_level.is_empty():
                    del self.buy_orders[best_bid]
                    heapq.heappop(self.buy_prices)
                    continue
                
                counterparty = price_level.orders[0]
                trade = await self._execute_trade(order, counterparty, best_bid)
                trades.append(trade)
        
        if order.remaining_quantity > 0:
            order.status = OrderStatus.PARTIALLY_FILLED if order.filled_quantity > 0 else OrderStatus.PENDING
        else:
            order.status = OrderStatus.FILLED
            
        return trades
    
    async def _execute_trade(self, taker_order: Order, maker_order: Order, 
                           execution_price: Decimal) -> Trade:
        trade_quantity = min(taker_order.remaining_quantity, maker_order.remaining_quantity)
        
        # Create trade record
        if taker_order.side == OrderSide.BUY:
            trade = Trade(
                buyer_order_id=taker_order.order_id,
                seller_order_id=maker_order.order_id,
                buyer_id=taker_order.user_id,
                seller_id=maker_order.user_id,
                symbol=self.symbol,
                quantity=trade_quantity,
                price=execution_price
            )
        else:
            trade = Trade(
                buyer_order_id=maker_order.order_id,
                seller_order_id=taker_order.order_id,
                buyer_id=maker_order.user_id,
                seller_id=taker_order.user_id,
                symbol=self.symbol,
                quantity=trade_quantity,
                price=execution_price
            )
        
        # Update orders
        taker_order.filled_quantity += trade_quantity
        taker_order.remaining_quantity -= trade_quantity
        taker_order.updated_at = datetime.now()
        
        maker_order.filled_quantity += trade_quantity
        maker_order.remaining_quantity -= trade_quantity
        maker_order.updated_at = datetime.now()
        
        # Update order statuses
        if taker_order.remaining_quantity == 0:
            taker_order.status = OrderStatus.FILLED
        elif taker_order.filled_quantity > 0:
            taker_order.status = OrderStatus.PARTIALLY_FILLED
            
        if maker_order.remaining_quantity == 0:
            maker_order.status = OrderStatus.FILLED
            self._remove_from_book(maker_order)
        elif maker_order.filled_quantity > 0:
            maker_order.status = OrderStatus.PARTIALLY_FILLED
        
        # Update market data
        self.last_trade_price = execution_price
        self.total_volume += trade_quantity
        
        logger.info(f"Trade executed: {trade_quantity} {self.symbol} at {execution_price}")
        
        return trade
    
    def _add_to_book(self, order: Order):
        self.order_lookup[order.order_id] = order
        
        if order.side == OrderSide.BUY:
            if order.price not in self.buy_orders:
                self.buy_orders[order.price] = PriceLevel(order.price)
                heapq.heappush(self.buy_prices, -order.price)  # Negative for max heap
            self.buy_orders[order.price].add_order(order)
        else:
            if order.price not in self.sell_orders:
                self.sell_orders[order.price] = PriceLevel(order.price)
                heapq.heappush(self.sell_prices, order.price)  # Min heap
            self.sell_orders[order.price].add_order(order)
    
    def _remove_from_book(self, order: Order):
        if order.order_id in self.order_lookup:
            del self.order_lookup[order.order_id]
            
        if order.side == OrderSide.BUY and order.price in self.buy_orders:
            self.buy_orders[order.price].remove_order(order)
            if self.buy_orders[order.price].is_empty():
                del self.buy_orders[order.price]
        elif order.side == OrderSide.SELL and order.price in self.sell_orders:
            self.sell_orders[order.price].remove_order(order)
            if self.sell_orders[order.price].is_empty():
                del self.sell_orders[order.price]
    
    async def _handle_stop_order(self, order: Order):
        # For now, just add to book - stop logic would be handled by market data updates
        order.status = OrderStatus.PENDING
        self.order_lookup[order.order_id] = order
    
    def get_best_bid(self) -> Optional[Decimal]:
        if self.buy_prices:
            return -self.buy_prices[0]
        return None
    
    def get_best_ask(self) -> Optional[Decimal]:
        if self.sell_prices:
            return self.sell_prices[0]
        return None
    
    def get_spread(self) -> Optional[Decimal]:
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid and ask:
            return ask - bid
        return None
    
    def get_market_depth(self, levels: int = 10) -> Dict:
        buy_depth = []
        sell_depth = []
        
        # Get top buy levels (highest prices first)
        buy_prices_sorted = sorted(self.buy_orders.keys(), reverse=True)[:levels]
        for price in buy_prices_sorted:
            level = self.buy_orders[price]
            buy_depth.append({
                'price': price,
                'quantity': level.total_quantity,
                'orders': len(level.orders)
            })
        
        # Get top sell levels (lowest prices first)
        sell_prices_sorted = sorted(self.sell_orders.keys())[:levels]
        for price in sell_prices_sorted:
            level = self.sell_orders[price]
            sell_depth.append({
                'price': price,
                'quantity': level.total_quantity,
                'orders': len(level.orders)
            })
        
        return {
            'bids': buy_depth,
            'asks': sell_depth,
            'spread': self.get_spread(),
            'last_price': self.last_trade_price
        }

class MatchingEngine:
    def __init__(self):
        self.order_books: Dict[MarketSymbol, OrderBook] = {}
        self.trade_history: List[Trade] = []
        self.order_history: List[Order] = []
        
    def get_order_book(self, symbol: MarketSymbol) -> OrderBook:
        if symbol not in self.order_books:
            self.order_books[symbol] = OrderBook(symbol)
        return self.order_books[symbol]
    
    async def submit_order(self, order: Order) -> List[Trade]:
        order_book = self.get_order_book(order.symbol)
        trades = await order_book.add_order(order)
        
        # Store order and trades
        self.order_history.append(order)
        self.trade_history.extend(trades)
        
        return trades
    
    async def cancel_order(self, order_id: str, symbol: MarketSymbol) -> bool:
        order_book = self.get_order_book(symbol)
        return await order_book.cancel_order(order_id)
    
    def get_market_data(self, symbol: MarketSymbol) -> Dict:
        order_book = self.get_order_book(symbol)
        return order_book.get_market_depth()
    
    def get_recent_trades(self, symbol: MarketSymbol, limit: int = 100) -> List[Trade]:
        symbol_trades = [t for t in self.trade_history if t.symbol == symbol]
        return sorted(symbol_trades, key=lambda x: x.executed_at, reverse=True)[:limit]