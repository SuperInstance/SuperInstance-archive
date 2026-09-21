import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
import yfinance as yf
from scipy import signal
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import logging

from .models import TechnicalIndicator, PatternRecognition

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    def __init__(self):
        self.indicators = {}
        self.patterns = {}
        
    def get_price_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """Get historical price data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                raise ValueError(f"No data available for {symbol}")
            
            # Ensure we have the required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in data.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            return data
        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            raise
    
    def calculate_all_indicators(self, symbol: str, data: pd.DataFrame = None, 
                               timeframe: str = "1d") -> Dict[str, TechnicalIndicator]:
        """Calculate 100+ technical indicators"""
        if data is None:
            data = self.get_price_data(symbol)
        
        indicators = {}
        
        # Trend Indicators
        indicators.update(self._calculate_trend_indicators(symbol, data, timeframe))
        
        # Momentum Indicators
        indicators.update(self._calculate_momentum_indicators(symbol, data, timeframe))
        
        # Volatility Indicators
        indicators.update(self._calculate_volatility_indicators(symbol, data, timeframe))
        
        # Volume Indicators
        indicators.update(self._calculate_volume_indicators(symbol, data, timeframe))
        
        # Support/Resistance Indicators
        indicators.update(self._calculate_support_resistance(symbol, data, timeframe))
        
        # Custom Indicators
        indicators.update(self._calculate_custom_indicators(symbol, data, timeframe))
        
        return indicators
    
    def _calculate_trend_indicators(self, symbol: str, data: pd.DataFrame, 
                                  timeframe: str) -> Dict[str, TechnicalIndicator]:
        """Calculate trend-following indicators"""
        indicators = {}
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        try:
            # Moving Averages
            periods = [5, 10, 20, 50, 100, 200]
            for period in periods:
                if len(close) >= period:
                    sma = talib.SMA(close.values, timeperiod=period)
                    ema = talib.EMA(close.values, timeperiod=period)
                    wma = talib.WMA(close.values, timeperiod=period)
                    
                    indicators[f'SMA_{period}'] = TechnicalIndicator(
                        name=f'SMA_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(sma[-1])) if not np.isnan(sma[-1]) else Decimal('0'),
                        signal=self._ma_signal(close.iloc[-1], sma[-1])
                    )
                    
                    indicators[f'EMA_{period}'] = TechnicalIndicator(
                        name=f'EMA_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(ema[-1])) if not np.isnan(ema[-1]) else Decimal('0'),
                        signal=self._ma_signal(close.iloc[-1], ema[-1])
                    )
                    
                    indicators[f'WMA_{period}'] = TechnicalIndicator(
                        name=f'WMA_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(wma[-1])) if not np.isnan(wma[-1]) else Decimal('0'),
                        signal=self._ma_signal(close.iloc[-1], wma[-1])
                    )
            
            # MACD
            macd, macdsignal, macdhist = talib.MACD(close.values)
            indicators['MACD'] = TechnicalIndicator(
                name='MACD', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(macd[-1])) if not np.isnan(macd[-1]) else Decimal('0'),
                signal=self._macd_signal(macd[-1], macdsignal[-1]),
                parameters={'signal': float(macdsignal[-1]), 'histogram': float(macdhist[-1])}
            )
            
            # ADX (Average Directional Index)
            adx = talib.ADX(high.values, low.values, close.values, timeperiod=14)
            plus_di = talib.PLUS_DI(high.values, low.values, close.values, timeperiod=14)
            minus_di = talib.MINUS_DI(high.values, low.values, close.values, timeperiod=14)
            
            indicators['ADX'] = TechnicalIndicator(
                name='ADX', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(adx[-1])) if not np.isnan(adx[-1]) else Decimal('0'),
                signal=self._adx_signal(adx[-1], plus_di[-1], minus_di[-1]),
                parameters={'plus_di': float(plus_di[-1]), 'minus_di': float(minus_di[-1])}
            )
            
            # Aroon
            aroon_up, aroon_down = talib.AROON(high.values, low.values, timeperiod=14)
            indicators['AROON'] = TechnicalIndicator(
                name='AROON', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(aroon_up[-1] - aroon_down[-1])) if not np.isnan(aroon_up[-1]) else Decimal('0'),
                signal=self._aroon_signal(aroon_up[-1], aroon_down[-1]),
                parameters={'aroon_up': float(aroon_up[-1]), 'aroon_down': float(aroon_down[-1])}
            )
            
            # Parabolic SAR
            sar = talib.SAR(high.values, low.values)
            indicators['SAR'] = TechnicalIndicator(
                name='SAR', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(sar[-1])) if not np.isnan(sar[-1]) else Decimal('0'),
                signal=self._sar_signal(close.iloc[-1], sar[-1])
            )
            
        except Exception as e:
            logger.error(f"Error calculating trend indicators: {e}")
        
        return indicators
    
    def _calculate_momentum_indicators(self, symbol: str, data: pd.DataFrame,
                                     timeframe: str) -> Dict[str, TechnicalIndicator]:
        """Calculate momentum indicators"""
        indicators = {}
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        try:
            # RSI (Relative Strength Index)
            periods = [14, 21, 30]
            for period in periods:
                if len(close) >= period:
                    rsi = talib.RSI(close.values, timeperiod=period)
                    indicators[f'RSI_{period}'] = TechnicalIndicator(
                        name=f'RSI_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(rsi[-1])) if not np.isnan(rsi[-1]) else Decimal('0'),
                        signal=self._rsi_signal(rsi[-1])
                    )
            
            # Stochastic Oscillator
            slowk, slowd = talib.STOCH(high.values, low.values, close.values)
            indicators['STOCH_K'] = TechnicalIndicator(
                name='STOCH_K', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(slowk[-1])) if not np.isnan(slowk[-1]) else Decimal('0'),
                signal=self._stoch_signal(slowk[-1], slowd[-1]),
                parameters={'stoch_d': float(slowd[-1])}
            )
            
            # Williams %R
            willr = talib.WILLR(high.values, low.values, close.values)
            indicators['WILLR'] = TechnicalIndicator(
                name='WILLR', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(willr[-1])) if not np.isnan(willr[-1]) else Decimal('0'),
                signal=self._willr_signal(willr[-1])
            )
            
            # CCI (Commodity Channel Index)
            cci = talib.CCI(high.values, low.values, close.values)
            indicators['CCI'] = TechnicalIndicator(
                name='CCI', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(cci[-1])) if not np.isnan(cci[-1]) else Decimal('0'),
                signal=self._cci_signal(cci[-1])
            )
            
            # ROC (Rate of Change)
            roc_periods = [10, 20, 30]
            for period in roc_periods:
                if len(close) >= period:
                    roc = talib.ROC(close.values, timeperiod=period)
                    indicators[f'ROC_{period}'] = TechnicalIndicator(
                        name=f'ROC_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(roc[-1])) if not np.isnan(roc[-1]) else Decimal('0'),
                        signal=self._roc_signal(roc[-1])
                    )
            
            # Money Flow Index
            mfi = talib.MFI(high.values, low.values, close.values, volume.values)
            indicators['MFI'] = TechnicalIndicator(
                name='MFI', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(mfi[-1])) if not np.isnan(mfi[-1]) else Decimal('0'),
                signal=self._mfi_signal(mfi[-1])
            )
            
            # Ultimate Oscillator
            uo = talib.ULTOSC(high.values, low.values, close.values)
            indicators['UO'] = TechnicalIndicator(
                name='UO', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(uo[-1])) if not np.isnan(uo[-1]) else Decimal('0'),
                signal=self._uo_signal(uo[-1])
            )
            
        except Exception as e:
            logger.error(f"Error calculating momentum indicators: {e}")
        
        return indicators
    
    def _calculate_volatility_indicators(self, symbol: str, data: pd.DataFrame,
                                       timeframe: str) -> Dict[str, TechnicalIndicator]:
        """Calculate volatility indicators"""
        indicators = {}
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        try:
            # Bollinger Bands
            periods = [20, 50]
            for period in periods:
                if len(close) >= period:
                    upper, middle, lower = talib.BBANDS(close.values, timeperiod=period)
                    bb_width = (upper[-1] - lower[-1]) / middle[-1] * 100
                    bb_position = (close.iloc[-1] - lower[-1]) / (upper[-1] - lower[-1])
                    
                    indicators[f'BB_UPPER_{period}'] = TechnicalIndicator(
                        name=f'BB_UPPER_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(upper[-1])) if not np.isnan(upper[-1]) else Decimal('0'),
                        signal=self._bb_signal(close.iloc[-1], upper[-1], lower[-1]),
                        parameters={'bb_width': bb_width, 'bb_position': bb_position}
                    )
            
            # Average True Range
            atr_periods = [14, 20, 30]
            for period in atr_periods:
                if len(close) >= period:
                    atr = talib.ATR(high.values, low.values, close.values, timeperiod=period)
                    indicators[f'ATR_{period}'] = TechnicalIndicator(
                        name=f'ATR_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(atr[-1])) if not np.isnan(atr[-1]) else Decimal('0'),
                        signal=self._atr_signal(atr[-1], atr[-5:-1])  # Compare with recent values
                    )
            
            # Keltner Channels
            if len(close) >= 20:
                kc_upper, kc_middle, kc_lower = self._calculate_keltner_channels(high, low, close)
                indicators['KC_UPPER'] = TechnicalIndicator(
                    name='KC_UPPER', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(kc_upper[-1])),
                    signal=self._kc_signal(close.iloc[-1], kc_upper[-1], kc_lower[-1])
                )
            
            # Donchian Channels
            if len(close) >= 20:
                dc_upper = talib.MAX(high.values, timeperiod=20)
                dc_lower = talib.MIN(low.values, timeperiod=20)
                indicators['DC_UPPER'] = TechnicalIndicator(
                    name='DC_UPPER', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(dc_upper[-1])),
                    signal=self._dc_signal(close.iloc[-1], dc_upper[-1], dc_lower[-1])
                )
            
        except Exception as e:
            logger.error(f"Error calculating volatility indicators: {e}")
        
        return indicators
    
    def _calculate_volume_indicators(self, symbol: str, data: pd.DataFrame,
                                   timeframe: str) -> Dict[str, TechnicalIndicator]:
        """Calculate volume-based indicators"""
        indicators = {}
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        try:
            # Volume Moving Averages
            volume_ma_periods = [10, 20, 50]
            for period in volume_ma_periods:
                if len(volume) >= period:
                    vol_ma = talib.SMA(volume.values, timeperiod=period)
                    indicators[f'VOL_MA_{period}'] = TechnicalIndicator(
                        name=f'VOL_MA_{period}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(vol_ma[-1])),
                        signal=self._volume_signal(volume.iloc[-1], vol_ma[-1])
                    )
            
            # On-Balance Volume
            obv = talib.OBV(close.values, volume.values)
            indicators['OBV'] = TechnicalIndicator(
                name='OBV', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(obv[-1])),
                signal=self._obv_signal(obv[-5:])  # Trend over last 5 periods
            )
            
            # Accumulation/Distribution Line
            ad = talib.AD(high.values, low.values, close.values, volume.values)
            indicators['AD'] = TechnicalIndicator(
                name='AD', symbol=symbol, timeframe=timeframe,
                value=Decimal(str(ad[-1])),
                signal=self._ad_signal(ad[-5:])  # Trend over last 5 periods
            )
            
            # Chaikin Money Flow
            if len(close) >= 20:
                cmf = self._calculate_cmf(high, low, close, volume)
                indicators['CMF'] = TechnicalIndicator(
                    name='CMF', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(cmf[-1])),
                    signal=self._cmf_signal(cmf[-1])
                )
            
            # Volume Rate of Change
            if len(volume) >= 10:
                vroc = talib.ROC(volume.values, timeperiod=10)
                indicators['VROC'] = TechnicalIndicator(
                    name='VROC', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(vroc[-1])) if not np.isnan(vroc[-1]) else Decimal('0'),
                    signal=self._vroc_signal(vroc[-1])
                )
            
            # Price Volume Trend
            if len(close) >= 2:
                pvt = self._calculate_pvt(close, volume)
                indicators['PVT'] = TechnicalIndicator(
                    name='PVT', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(pvt[-1])),
                    signal=self._pvt_signal(pvt[-5:])  # Trend over last 5 periods
                )
            
        except Exception as e:
            logger.error(f"Error calculating volume indicators: {e}")
        
        return indicators
    
    def _calculate_support_resistance(self, symbol: str, data: pd.DataFrame,
                                    timeframe: str) -> Dict[str, TechnicalIndicator]:
        """Calculate support and resistance levels"""
        indicators = {}
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        try:
            # Pivot Points
            pivot_points = self._calculate_pivot_points(high, low, close)
            for level, value in pivot_points.items():
                indicators[f'PIVOT_{level}'] = TechnicalIndicator(
                    name=f'PIVOT_{level}', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(value)),
                    signal=self._pivot_signal(close.iloc[-1], value, level)
                )
            
            # Fibonacci Retracements
            if len(close) >= 50:
                fib_levels = self._calculate_fibonacci_levels(high, low)
                for level, value in fib_levels.items():
                    indicators[f'FIB_{level}'] = TechnicalIndicator(
                        name=f'FIB_{level}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(value)),
                        signal=self._fib_signal(close.iloc[-1], value)
                    )
            
            # Psychological Levels
            psych_levels = self._calculate_psychological_levels(close.iloc[-1])
            for i, level in enumerate(psych_levels):
                indicators[f'PSYCH_{i}'] = TechnicalIndicator(
                    name=f'PSYCH_{i}', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(level)),
                    signal=self._psych_signal(close.iloc[-1], level)
                )
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance levels: {e}")
        
        return indicators
    
    def _calculate_custom_indicators(self, symbol: str, data: pd.DataFrame,
                                   timeframe: str) -> Dict[str, TechnicalIndicator]:
        """Calculate custom and advanced indicators"""
        indicators = {}
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        try:
            # Ichimoku Cloud
            if len(close) >= 52:
                ichimoku = self._calculate_ichimoku(high, low, close)
                for component, value in ichimoku.items():
                    indicators[f'ICHIMOKU_{component}'] = TechnicalIndicator(
                        name=f'ICHIMOKU_{component}', symbol=symbol, timeframe=timeframe,
                        value=Decimal(str(value)),
                        signal=self._ichimoku_signal(close.iloc[-1], ichimoku)
                    )
            
            # Kaufman Adaptive Moving Average
            if len(close) >= 30:
                kama = talib.KAMA(close.values, timeperiod=30)
                indicators['KAMA'] = TechnicalIndicator(
                    name='KAMA', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(kama[-1])) if not np.isnan(kama[-1]) else Decimal('0'),
                    signal=self._kama_signal(close.iloc[-1], kama[-1])
                )
            
            # Vortex Indicator
            if len(close) >= 14:
                vi_plus, vi_minus = self._calculate_vortex_indicator(high, low, close)
                indicators['VI_PLUS'] = TechnicalIndicator(
                    name='VI_PLUS', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(vi_plus[-1])),
                    signal=self._vi_signal(vi_plus[-1], vi_minus[-1])
                )
            
            # Elder Ray Index
            if len(close) >= 13:
                bull_power, bear_power = self._calculate_elder_ray(high, low, close)
                indicators['BULL_POWER'] = TechnicalIndicator(
                    name='BULL_POWER', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(bull_power[-1])),
                    signal=self._elder_ray_signal(bull_power[-1], bear_power[-1])
                )
            
            # Coppock Curve
            if len(close) >= 24:
                coppock = self._calculate_coppock_curve(close)
                indicators['COPPOCK'] = TechnicalIndicator(
                    name='COPPOCK', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(coppock[-1])),
                    signal=self._coppock_signal(coppock[-5:])
                )
            
            # Know Sure Thing (KST)
            if len(close) >= 100:
                kst = self._calculate_kst(close)
                indicators['KST'] = TechnicalIndicator(
                    name='KST', symbol=symbol, timeframe=timeframe,
                    value=Decimal(str(kst[-1])),
                    signal=self._kst_signal(kst[-1])
                )
            
        except Exception as e:
            logger.error(f"Error calculating custom indicators: {e}")
        
        return indicators
    
    def detect_patterns(self, symbol: str, data: pd.DataFrame = None) -> List[PatternRecognition]:
        """Detect chart patterns"""
        if data is None:
            data = self.get_price_data(symbol)
        
        patterns = []
        
        try:
            # Candlestick patterns
            patterns.extend(self._detect_candlestick_patterns(symbol, data))
            
            # Chart patterns
            patterns.extend(self._detect_chart_patterns(symbol, data))
            
            # Volume patterns
            patterns.extend(self._detect_volume_patterns(symbol, data))
            
        except Exception as e:
            logger.error(f"Error detecting patterns for {symbol}: {e}")
        
        return patterns
    
    def _detect_candlestick_patterns(self, symbol: str, data: pd.DataFrame) -> List[PatternRecognition]:
        """Detect candlestick patterns using TAlib"""
        patterns = []
        open_prices = data['Open'].values
        high_prices = data['High'].values
        low_prices = data['Low'].values
        close_prices = data['Close'].values
        
        # Define candlestick pattern functions
        candlestick_patterns = {
            'DOJI': talib.CDLDOJI,
            'HAMMER': talib.CDLHAMMER,
            'HANGING_MAN': talib.CDLHANGINGMAN,
            'SHOOTING_STAR': talib.CDLSHOOTINGSTAR,
            'ENGULFING': talib.CDLENGULFING,
            'HARAMI': talib.CDLHARAMI,
            'MORNING_STAR': talib.CDLMORNINGSTAR,
            'EVENING_STAR': talib.CDLEVENINGSTAR,
            'THREE_BLACK_CROWS': talib.CDL3BLACKCROWS,
            'THREE_WHITE_SOLDIERS': talib.CDL3WHITESOLDIERS
        }
        
        for pattern_name, pattern_func in candlestick_patterns.items():
            try:
                pattern_result = pattern_func(open_prices, high_prices, low_prices, close_prices)
                
                # Find recent pattern occurrences
                recent_signals = pattern_result[-20:]  # Last 20 periods
                for i, signal in enumerate(recent_signals):
                    if signal != 0:  # Pattern detected
                        confidence = abs(signal) / 100.0  # Convert to 0-1 scale
                        signal_type = "BULLISH" if signal > 0 else "BEARISH"
                        
                        pattern = PatternRecognition(
                            symbol=symbol,
                            pattern_type=f"CANDLESTICK_{pattern_name}",
                            confidence=Decimal(str(confidence)),
                            start_date=data.index[-20+i],
                            pattern_status="completed"
                        )
                        patterns.append(pattern)
                        
            except Exception as e:
                logger.warning(f"Error detecting {pattern_name}: {e}")
        
        return patterns
    
    def _detect_chart_patterns(self, symbol: str, data: pd.DataFrame) -> List[PatternRecognition]:
        """Detect chart patterns like head and shoulders, triangles, etc."""
        patterns = []
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        try:
            # Head and Shoulders
            hs_pattern = self._detect_head_and_shoulders(high, low)
            if hs_pattern:
                patterns.append(PatternRecognition(
                    symbol=symbol,
                    pattern_type="HEAD_AND_SHOULDERS",
                    confidence=hs_pattern['confidence'],
                    start_date=hs_pattern['start_date'],
                    price_target=hs_pattern['price_target'],
                    key_levels=hs_pattern['key_levels']
                ))
            
            # Double Top/Bottom
            double_pattern = self._detect_double_top_bottom(high, low, close)
            if double_pattern:
                patterns.append(PatternRecognition(
                    symbol=symbol,
                    pattern_type=double_pattern['type'],
                    confidence=double_pattern['confidence'],
                    start_date=double_pattern['start_date'],
                    price_target=double_pattern['price_target']
                ))
            
            # Triangle patterns
            triangle_patterns = self._detect_triangles(high, low, close)
            for triangle in triangle_patterns:
                patterns.append(PatternRecognition(
                    symbol=symbol,
                    pattern_type=triangle['type'],
                    confidence=triangle['confidence'],
                    start_date=triangle['start_date'],
                    price_target=triangle.get('price_target')
                ))
            
            # Flag and Pennant
            flag_patterns = self._detect_flags_pennants(high, low, close, data['Volume'])
            for flag in flag_patterns:
                patterns.append(PatternRecognition(
                    symbol=symbol,
                    pattern_type=flag['type'],
                    confidence=flag['confidence'],
                    start_date=flag['start_date'],
                    price_target=flag.get('price_target')
                ))
            
        except Exception as e:
            logger.error(f"Error detecting chart patterns: {e}")
        
        return patterns
    
    # Helper methods for signal generation
    def _ma_signal(self, price: float, ma_value: float) -> str:
        """Generate moving average signal"""
        if pd.isna(ma_value):
            return "NEUTRAL"
        return "BUY" if price > ma_value else "SELL"
    
    def _macd_signal(self, macd: float, signal_line: float) -> str:
        """Generate MACD signal"""
        if pd.isna(macd) or pd.isna(signal_line):
            return "NEUTRAL"
        return "BUY" if macd > signal_line else "SELL"
    
    def _rsi_signal(self, rsi: float) -> str:
        """Generate RSI signal"""
        if pd.isna(rsi):
            return "NEUTRAL"
        if rsi > 70:
            return "SELL"
        elif rsi < 30:
            return "BUY"
        else:
            return "NEUTRAL"
    
    def _adx_signal(self, adx: float, plus_di: float, minus_di: float) -> str:
        """Generate ADX signal"""
        if pd.isna(adx) or pd.isna(plus_di) or pd.isna(minus_di):
            return "NEUTRAL"
        if adx > 25:  # Strong trend
            return "BUY" if plus_di > minus_di else "SELL"
        else:
            return "NEUTRAL"
    
    # Additional helper methods would be implemented here...
    # (For brevity, I'll include a few key ones)
    
    def _calculate_keltner_channels(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20):
        """Calculate Keltner Channels"""
        ema = close.ewm(span=period).mean()
        atr = talib.ATR(high.values, low.values, close.values, timeperiod=period)
        upper = ema + (2 * atr)
        lower = ema - (2 * atr)
        return upper, ema, lower
    
    def _calculate_pivot_points(self, high: pd.Series, low: pd.Series, close: pd.Series):
        """Calculate pivot points"""
        pivot = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1]) / 3
        r1 = 2 * pivot - low.iloc[-1]
        r2 = pivot + (high.iloc[-1] - low.iloc[-1])
        s1 = 2 * pivot - high.iloc[-1]
        s2 = pivot - (high.iloc[-1] - low.iloc[-1])
        
        return {
            'PP': pivot,
            'R1': r1,
            'R2': r2,
            'S1': s1,
            'S2': s2
        }
    
    def _calculate_fibonacci_levels(self, high: pd.Series, low: pd.Series, lookback: int = 50):
        """Calculate Fibonacci retracement levels"""
        recent_high = high.rolling(window=lookback).max().iloc[-1]
        recent_low = low.rolling(window=lookback).min().iloc[-1]
        diff = recent_high - recent_low
        
        return {
            '0.0': recent_high,
            '23.6': recent_high - diff * 0.236,
            '38.2': recent_high - diff * 0.382,
            '50.0': recent_high - diff * 0.500,
            '61.8': recent_high - diff * 0.618,
            '78.6': recent_high - diff * 0.786,
            '100.0': recent_low
        }
    
    def _detect_head_and_shoulders(self, high: pd.Series, low: pd.Series):
        """Detect head and shoulders pattern (simplified)"""
        # This is a simplified version - real implementation would be more sophisticated
        if len(high) < 50:
            return None
        
        # Look for three peaks pattern
        peaks = signal.find_peaks(high.values, distance=10)[0]
        if len(peaks) < 3:
            return None
        
        # Check if middle peak is highest (head)
        last_three_peaks = peaks[-3:]
        if len(last_three_peaks) == 3:
            left_shoulder = high.iloc[last_three_peaks[0]]
            head = high.iloc[last_three_peaks[1]]
            right_shoulder = high.iloc[last_three_peaks[2]]
            
            # Head should be higher than both shoulders
            if head > left_shoulder and head > right_shoulder:
                # Shoulders should be roughly equal (within 5%)
                shoulder_diff = abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder)
                if shoulder_diff < 0.05:
                    neckline = min(low.iloc[last_three_peaks[0]:last_three_peaks[1]].min(),
                                 low.iloc[last_three_peaks[1]:last_three_peaks[2]].min())
                    
                    return {
                        'confidence': Decimal(str(0.8 - shoulder_diff)),
                        'start_date': high.index[last_three_peaks[0]],
                        'price_target': Decimal(str(neckline - (head - neckline))),
                        'key_levels': [Decimal(str(head)), Decimal(str(neckline))]
                    }
        
        return None
    
    # More pattern detection methods would be implemented here...
    # (Truncated for brevity)
    
    # Signal generation helper methods
    def _aroon_signal(self, aroon_up: float, aroon_down: float) -> str:
        if pd.isna(aroon_up) or pd.isna(aroon_down):
            return "NEUTRAL"
        if aroon_up > 70 and aroon_down < 30:
            return "BUY"
        elif aroon_down > 70 and aroon_up < 30:
            return "SELL"
        else:
            return "NEUTRAL"
    
    def _sar_signal(self, price: float, sar: float) -> str:
        if pd.isna(sar):
            return "NEUTRAL"
        return "BUY" if price > sar else "SELL"
    
    def _stoch_signal(self, stoch_k: float, stoch_d: float) -> str:
        if pd.isna(stoch_k) or pd.isna(stoch_d):
            return "NEUTRAL"
        if stoch_k > 80 and stoch_d > 80:
            return "SELL"
        elif stoch_k < 20 and stoch_d < 20:
            return "BUY"
        else:
            return "NEUTRAL"
    
    # Additional signal methods...
    def _willr_signal(self, willr: float) -> str:
        if pd.isna(willr):
            return "NEUTRAL"
        if willr > -20:
            return "SELL"
        elif willr < -80:
            return "BUY"
        else:
            return "NEUTRAL"
    
    def _cci_signal(self, cci: float) -> str:
        if pd.isna(cci):
            return "NEUTRAL"
        if cci > 100:
            return "SELL"
        elif cci < -100:
            return "BUY"
        else:
            return "NEUTRAL"
    
    def _roc_signal(self, roc: float) -> str:
        if pd.isna(roc):
            return "NEUTRAL"
        return "BUY" if roc > 0 else "SELL"
    
    def _mfi_signal(self, mfi: float) -> str:
        if pd.isna(mfi):
            return "NEUTRAL"
        if mfi > 80:
            return "SELL"
        elif mfi < 20:
            return "BUY"
        else:
            return "NEUTRAL"
    
    def _uo_signal(self, uo: float) -> str:
        if pd.isna(uo):
            return "NEUTRAL"
        if uo > 70:
            return "SELL"
        elif uo < 30:
            return "BUY"
        else:
            return "NEUTRAL"
    
    # More helper methods would be implemented for completeness...