import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
from collections import deque

from .models import MarketSymbol, Trade, MarketData
from .order_book import MatchingEngine

class TechnicalIndicators:
    @staticmethod
    def calculate_sma(prices: List[Decimal], period: int) -> List[Optional[Decimal]]:
        """Simple Moving Average"""
        if len(prices) < period:
            return [None] * len(prices)
        
        sma_values = []
        for i in range(len(prices)):
            if i < period - 1:
                sma_values.append(None)
            else:
                window = prices[i - period + 1:i + 1]
                sma_values.append(sum(window) / len(window))
        return sma_values
    
    @staticmethod
    def calculate_ema(prices: List[Decimal], period: int) -> List[Optional[Decimal]]:
        """Exponential Moving Average"""
        if len(prices) == 0:
            return []
        
        alpha = Decimal(2) / (period + 1)
        ema_values = [None] * (period - 1)
        ema_values.append(prices[period - 1])  # First EMA is just the price
        
        for i in range(period, len(prices)):
            ema = alpha * prices[i] + (1 - alpha) * ema_values[i - 1]
            ema_values.append(ema)
        
        return ema_values
    
    @staticmethod
    def calculate_rsi(prices: List[Decimal], period: int = 14) -> List[Optional[Decimal]]:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(Decimal('0'))
            else:
                gains.append(Decimal('0'))
                losses.append(abs(change))
        
        rsi_values = [None] * period
        
        # Calculate initial RS
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            rsi_values.append(Decimal('100'))
        else:
            rs = avg_gain / avg_loss
            rsi = Decimal('100') - (Decimal('100') / (Decimal('1') + rs))
            rsi_values.append(rsi)
        
        # Calculate subsequent RSI values
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_values.append(Decimal('100'))
            else:
                rs = avg_gain / avg_loss
                rsi = Decimal('100') - (Decimal('100') / (Decimal('1') + rs))
                rsi_values.append(rsi)
        
        return rsi_values

class CandlestickData:
    def __init__(self, timestamp: datetime, open_price: Decimal, high: Decimal, 
                 low: Decimal, close: Decimal, volume: Decimal):
        self.timestamp = timestamp
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

class PriceChart:
    def __init__(self, symbol: MarketSymbol):
        self.symbol = symbol
        self.trades: deque[Trade] = deque(maxlen=10000)  # Store recent trades
        self.candlesticks: Dict[str, List[CandlestickData]] = {
            '1m': [],
            '5m': [],
            '15m': [],
            '1h': [],
            '4h': [],
            '1d': []
        }
        self.current_price = Decimal('0')
        self.volume_24h = Decimal('0')
        self.price_change_24h = Decimal('0')
        
    def add_trade(self, trade: Trade):
        self.trades.append(trade)
        self.current_price = trade.price
        self._update_candlesticks(trade)
        self._update_24h_stats()
    
    def _update_candlesticks(self, trade: Trade):
        intervals = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        
        for interval, seconds in intervals.items():
            self._update_candlestick_interval(trade, interval, seconds)
    
    def _update_candlestick_interval(self, trade: Trade, interval: str, seconds: int):
        timestamp = trade.executed_at
        candle_start = timestamp.replace(
            second=0, microsecond=0
        ) - timedelta(seconds=timestamp.second % seconds)
        
        if interval == '1h':
            candle_start = candle_start.replace(minute=0)
        elif interval == '4h':
            candle_start = candle_start.replace(minute=0, hour=(candle_start.hour // 4) * 4)
        elif interval == '1d':
            candle_start = candle_start.replace(minute=0, hour=0)
        
        candlesticks = self.candlesticks[interval]
        
        # Find or create candlestick for this period
        current_candle = None
        if candlesticks and candlesticks[-1].timestamp == candle_start:
            current_candle = candlesticks[-1]
        else:
            current_candle = CandlestickData(
                timestamp=candle_start,
                open_price=trade.price,
                high=trade.price,
                low=trade.price,
                close=trade.price,
                volume=Decimal('0')
            )
            candlesticks.append(current_candle)
        
        # Update OHLCV
        current_candle.close = trade.price
        current_candle.high = max(current_candle.high, trade.price)
        current_candle.low = min(current_candle.low, trade.price)
        current_candle.volume += trade.quantity
    
    def _update_24h_stats(self):
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        
        recent_trades = [t for t in self.trades if t.executed_at >= day_ago]
        
        if recent_trades:
            self.volume_24h = sum(t.quantity for t in recent_trades)
            oldest_price = recent_trades[0].price
            self.price_change_24h = self.current_price - oldest_price
    
    def get_chart_data(self, interval: str = '1h', limit: int = 100) -> List[Dict]:
        candlesticks = self.candlesticks.get(interval, [])
        limited_sticks = candlesticks[-limit:] if len(candlesticks) > limit else candlesticks
        
        return [
            {
                'timestamp': c.timestamp.isoformat(),
                'open': float(c.open),
                'high': float(c.high),
                'low': float(c.low),
                'close': float(c.close),
                'volume': float(c.volume)
            } for c in limited_sticks
        ]
    
    def get_price_history(self, hours: int = 24) -> List[Decimal]:
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_trades = [t for t in self.trades if t.executed_at >= cutoff]
        return [t.price for t in recent_trades]

class MarketDataProvider:
    def __init__(self, matching_engine: MatchingEngine):
        self.matching_engine = matching_engine
        self.charts: Dict[MarketSymbol, PriceChart] = {}
        self.market_data: Dict[MarketSymbol, MarketData] = {}
        self.subscribers: List[Any] = []  # WebSocket connections
        
        # Initialize charts for all symbols
        for symbol in MarketSymbol:
            self.charts[symbol] = PriceChart(symbol)
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                last_price=Decimal('100'),  # Starting price
            )
    
    async def update_with_trade(self, trade: Trade):
        """Update market data with new trade"""
        chart = self.charts[trade.symbol]
        chart.add_trade(trade)
        
        # Update market data
        market_data = self.market_data[trade.symbol]
        market_data.last_price = trade.price
        market_data.volume_24h = chart.volume_24h
        market_data.price_change_24h = chart.price_change_24h
        market_data.timestamp = trade.executed_at
        
        # Update bid/ask from order book
        order_book = self.matching_engine.get_order_book(trade.symbol)
        market_data.bid_price = order_book.get_best_bid()
        market_data.ask_price = order_book.get_best_ask()
        
        # Calculate 24h high/low
        price_history = chart.get_price_history(24)
        if price_history:
            market_data.high_24h = max(price_history)
            market_data.low_24h = min(price_history)
        
        # Notify subscribers
        await self._broadcast_market_update(trade.symbol)
    
    async def _broadcast_market_update(self, symbol: MarketSymbol):
        """Broadcast market data updates to WebSocket subscribers"""
        update_data = {
            'type': 'market_update',
            'symbol': symbol.value,
            'data': self.get_market_summary(symbol)
        }
        
        # Send to all connected clients
        for subscriber in self.subscribers:
            try:
                await subscriber.send_text(json.dumps(update_data))
            except:
                # Remove disconnected subscribers
                self.subscribers.remove(subscriber)
    
    def subscribe(self, websocket):
        """Subscribe to market data updates"""
        self.subscribers.append(websocket)
    
    def unsubscribe(self, websocket):
        """Unsubscribe from market data updates"""
        if websocket in self.subscribers:
            self.subscribers.remove(websocket)
    
    def get_market_summary(self, symbol: MarketSymbol) -> Dict:
        market_data = self.market_data[symbol]
        order_book = self.matching_engine.get_order_book(symbol)
        
        return {
            'symbol': symbol.value,
            'last_price': float(market_data.last_price),
            'bid': float(market_data.bid_price) if market_data.bid_price else None,
            'ask': float(market_data.ask_price) if market_data.ask_price else None,
            'spread': float(order_book.get_spread()) if order_book.get_spread() else None,
            'volume_24h': float(market_data.volume_24h),
            'change_24h': float(market_data.price_change_24h),
            'change_percent_24h': float(market_data.price_change_percent_24h),
            'high_24h': float(market_data.high_24h) if market_data.high_24h else None,
            'low_24h': float(market_data.low_24h) if market_data.low_24h else None,
            'timestamp': market_data.timestamp.isoformat() if market_data.timestamp else None
        }
    
    def get_technical_analysis(self, symbol: MarketSymbol) -> Dict:
        chart = self.charts[symbol]
        price_history = chart.get_price_history(100)  # Last 100 trades
        
        if len(price_history) < 20:
            return {'error': 'Insufficient data for technical analysis'}
        
        # Calculate technical indicators
        sma_20 = TechnicalIndicators.calculate_sma(price_history, 20)
        sma_50 = TechnicalIndicators.calculate_sma(price_history, 50)
        ema_12 = TechnicalIndicators.calculate_ema(price_history, 12)
        ema_26 = TechnicalIndicators.calculate_ema(price_history, 26)
        rsi = TechnicalIndicators.calculate_rsi(price_history)
        
        current_price = price_history[-1] if price_history else Decimal('0')
        
        return {
            'current_price': float(current_price),
            'sma_20': float(sma_20[-1]) if sma_20[-1] else None,
            'sma_50': float(sma_50[-1]) if sma_50[-1] else None,
            'ema_12': float(ema_12[-1]) if ema_12[-1] else None,
            'ema_26': float(ema_26[-1]) if ema_26[-1] else None,
            'rsi': float(rsi[-1]) if rsi[-1] else None,
            'trend': self._analyze_trend(sma_20, sma_50, current_price),
            'momentum': self._analyze_momentum(rsi[-1] if rsi[-1] else None)
        }
    
    def _analyze_trend(self, sma_20: List, sma_50: List, current_price: Decimal) -> str:
        if not sma_20 or not sma_50 or not sma_20[-1] or not sma_50[-1]:
            return 'NEUTRAL'
        
        if current_price > sma_20[-1] > sma_50[-1]:
            return 'BULLISH'
        elif current_price < sma_20[-1] < sma_50[-1]:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
    
    def _analyze_momentum(self, rsi: Optional[Decimal]) -> str:
        if not rsi:
            return 'NEUTRAL'
        
        if rsi > 70:
            return 'OVERBOUGHT'
        elif rsi < 30:
            return 'OVERSOLD'
        else:
            return 'NEUTRAL'

class ROICalculator:
    @staticmethod
    def calculate_roi(initial_investment: Decimal, current_value: Decimal) -> Dict:
        """Calculate return on investment metrics"""
        if initial_investment <= 0:
            return {'error': 'Invalid initial investment'}
        
        absolute_return = current_value - initial_investment
        roi_percentage = (absolute_return / initial_investment) * 100
        
        return {
            'initial_investment': float(initial_investment),
            'current_value': float(current_value),
            'absolute_return': float(absolute_return),
            'roi_percentage': float(roi_percentage),
            'multiple': float(current_value / initial_investment)
        }
    
    @staticmethod
    def calculate_pe_ratio(market_price: Decimal, earnings_per_share: Decimal) -> Optional[Decimal]:
        """Calculate Price-to-Earnings ratio"""
        if earnings_per_share <= 0:
            return None
        return market_price / earnings_per_share
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[Decimal], risk_free_rate: Decimal = Decimal('0.02')) -> Optional[Decimal]:
        """Calculate Sharpe ratio for risk-adjusted returns"""
        if len(returns) < 2:
            return None
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** Decimal('0.5')
        
        if std_dev == 0:
            return None
        
        return (mean_return - risk_free_rate) / std_dev