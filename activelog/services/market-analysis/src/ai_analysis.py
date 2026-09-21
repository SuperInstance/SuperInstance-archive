"""
AI-Powered Analysis Module for Market Analysis Platform
Provides sentiment analysis, earnings analysis, prediction models, risk assessment, and optimization
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import json
import re

import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
# import tensorflow as tf
# from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import requests
from textblob import TextBlob
import nltk
from newsapi import NewsApiClient
import finnhub

from .models import (
    SecurityData, SentimentAnalysis, PricePrediction, RiskMetrics,
    PortfolioOptimization, MarketRegime, CorrelationAnalysis, EarningsData,
    AssetType, RiskLevel, RecommendationType
)

# Initialize NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

from nltk.sentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

class AIAnalysisEngine:
    """Main AI analysis engine coordinating all AI-powered features"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.earnings_analyzer = EarningsAnalyzer()
        self.prediction_engine = PredictionEngine()
        self.risk_analyzer = RiskAnalyzer()
        self.portfolio_optimizer = PortfolioOptimizer()
        self.market_regime_detector = MarketRegimeDetector()
        
    async def perform_comprehensive_analysis(self, symbol: str) -> Dict[str, Any]:
        """Perform comprehensive AI analysis on a security"""
        try:
            # Run all analyses in parallel
            tasks = [
                self.sentiment_analyzer.analyze_sentiment(symbol),
                self.earnings_analyzer.analyze_earnings_transcripts(symbol),
                self.prediction_engine.generate_predictions(symbol),
                self.risk_analyzer.assess_risk(symbol),
                self.market_regime_detector.detect_current_regime()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return {
                "sentiment_analysis": results[0] if not isinstance(results[0], Exception) else None,
                "earnings_analysis": results[1] if not isinstance(results[1], Exception) else None,
                "price_predictions": results[2] if not isinstance(results[2], Exception) else None,
                "risk_assessment": results[3] if not isinstance(results[3], Exception) else None,
                "market_regime": results[4] if not isinstance(results[4], Exception) else None,
                "analysis_timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis for {symbol}: {e}")
            return {"error": str(e)}

class SentimentAnalyzer:
    """Advanced sentiment analysis using multiple sources and models"""
    
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.finbert = None
        self.news_client = None
        self.finnhub_client = None
        
        # Initialize FinBERT for financial sentiment
        # try:
        #     self.finbert = pipeline("sentiment-analysis", 
        #                           model="ProsusAI/finbert", 
        #                           tokenizer="ProsusAI/finbert")
        # except Exception as e:
        #     logger.warning(f"FinBERT not available: {e}")
            
        # Initialize news API clients
        try:
            self.news_client = NewsApiClient(api_key="demo_key")
        except Exception as e:
            logger.warning(f"NewsAPI not available: {e}")
            
        try:
            self.finnhub_client = finnhub.Client(api_key="demo_key")
        except Exception as e:
            logger.warning(f"Finnhub not available: {e}")
    
    async def analyze_sentiment(self, symbol: str) -> SentimentAnalysis:
        """Comprehensive sentiment analysis from multiple sources"""
        try:
            # Get news sentiment
            news_sentiment = await self._analyze_news_sentiment(symbol)
            
            # Get social media sentiment
            social_sentiment = await self._analyze_social_sentiment(symbol)
            
            # Get analyst sentiment
            analyst_sentiment = await self._analyze_analyst_sentiment(symbol)
            
            # Combine all sentiments
            sentiments = [s for s in [news_sentiment, social_sentiment, analyst_sentiment] if s is not None]
            
            if not sentiments:
                overall_sentiment = Decimal('0.0')
                sentiment_label = "Neutral"
            else:
                overall_sentiment = Decimal(str(sum(sentiments) / len(sentiments)))
                sentiment_label = self._get_sentiment_label(float(overall_sentiment))
            
            return SentimentAnalysis(
                symbol=symbol,
                sentiment_score=overall_sentiment,
                sentiment_label=sentiment_label,
                news_sentiment=Decimal(str(news_sentiment)) if news_sentiment else None,
                social_sentiment=Decimal(str(social_sentiment)) if social_sentiment else None,
                analyst_sentiment=Decimal(str(analyst_sentiment)) if analyst_sentiment else None,
                sources_analyzed=len([s for s in [news_sentiment, social_sentiment, analyst_sentiment] if s is not None])
            )
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis for {symbol}: {e}")
            return SentimentAnalysis(
                symbol=symbol,
                sentiment_score=Decimal('0.0'),
                sentiment_label="Neutral",
                sources_analyzed=0
            )
    
    async def _analyze_news_sentiment(self, symbol: str) -> Optional[float]:
        """Analyze sentiment from financial news"""
        try:
            if not self.news_client:
                return None
                
            # Get recent news
            articles = self.news_client.get_everything(
                q=symbol,
                language='en',
                sort_by='relevancy',
                page_size=20,
                from_param=(datetime.now() - timedelta(days=7)).isoformat()
            )
            
            if not articles['articles']:
                return None
            
            sentiments = []
            for article in articles['articles'][:10]:  # Analyze top 10 articles
                text = f"{article['title']} {article['description'] or ''}"
                
                # Use FinBERT if available, otherwise VADER
                if self.finbert:
                    result = self.finbert(text)[0]
                    score = result['score'] if result['label'] == 'positive' else -result['score']
                    sentiments.append(score)
                else:
                    scores = self.vader_analyzer.polarity_scores(text)
                    sentiments.append(scores['compound'])
            
            return sum(sentiments) / len(sentiments) if sentiments else 0.0
            
        except Exception as e:
            logger.error(f"Error analyzing news sentiment for {symbol}: {e}")
            return None
    
    async def _analyze_social_sentiment(self, symbol: str) -> Optional[float]:
        """Analyze sentiment from social media (simplified version)"""
        try:
            # In a real implementation, this would connect to Twitter API, Reddit API, etc.
            # For now, return a placeholder based on stock performance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if len(hist) < 2:
                return None
                
            price_change = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]
            
            # Simple heuristic: positive price movement correlates with positive sentiment
            sentiment_score = float(np.tanh(price_change * 5))  # Scale and bound between -1 and 1
            
            return sentiment_score
            
        except Exception as e:
            logger.error(f"Error analyzing social sentiment for {symbol}: {e}")
            return None
    
    async def _analyze_analyst_sentiment(self, symbol: str) -> Optional[float]:
        """Analyze sentiment from analyst ratings"""
        try:
            if not self.finnhub_client:
                return None
                
            # Get analyst recommendations
            recommendations = self.finnhub_client.recommendation_trends(symbol)
            
            if not recommendations:
                return None
            
            latest = recommendations[0]
            
            # Calculate weighted sentiment score
            total_ratings = (latest['strongBuy'] + latest['buy'] + 
                           latest['hold'] + latest['sell'] + latest['strongSell'])
            
            if total_ratings == 0:
                return None
            
            sentiment_score = (
                (latest['strongBuy'] * 1.0 + latest['buy'] * 0.5 + 
                 latest['hold'] * 0.0 + latest['sell'] * -0.5 + 
                 latest['strongSell'] * -1.0) / total_ratings
            )
            
            return sentiment_score
            
        except Exception as e:
            logger.error(f"Error analyzing analyst sentiment for {symbol}: {e}")
            return None
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= 0.6:
            return "Very Positive"
        elif score >= 0.2:
            return "Positive"
        elif score > -0.2:
            return "Neutral"
        elif score > -0.6:
            return "Negative"
        else:
            return "Very Negative"

class EarningsAnalyzer:
    """Analyze earnings calls and financial reports using NLP"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.financial_keywords = {
            'positive': ['growth', 'increase', 'strong', 'beat', 'exceeded', 'optimistic', 
                        'expansion', 'improvement', 'solid', 'robust', 'record'],
            'negative': ['decline', 'decrease', 'weak', 'miss', 'below', 'concerns',
                        'challenges', 'headwinds', 'pressure', 'volatility', 'uncertainty']
        }
    
    async def analyze_earnings_transcripts(self, symbol: str) -> Dict[str, Any]:
        """Analyze earnings call transcripts for insights"""
        try:
            # In a real implementation, this would fetch actual transcripts
            # For now, we'll simulate with basic earnings data analysis
            
            ticker = yf.Ticker(symbol)
            earnings = ticker.earnings_dates
            
            if earnings is None or len(earnings) == 0:
                return {"error": "No earnings data available"}
            
            # Get recent earnings surprise data
            recent_earnings = earnings.head(4)  # Last 4 quarters
            
            analysis = {
                "earnings_surprises": [],
                "sentiment_trend": "neutral",
                "key_themes": [],
                "management_confidence": "medium",
                "forward_guidance": "neutral"
            }
            
            # Analyze earnings surprises
            for date, row in recent_earnings.iterrows():
                if pd.notna(row.get('EPS Estimate')) and pd.notna(row.get('Reported EPS')):
                    surprise = float(row['Reported EPS']) - float(row['EPS Estimate'])
                    surprise_percent = (surprise / float(row['EPS Estimate'])) * 100
                    
                    analysis["earnings_surprises"].append({
                        "date": date.strftime("%Y-%m-%d"),
                        "surprise": surprise,
                        "surprise_percent": round(surprise_percent, 2)
                    })
            
            # Determine overall sentiment trend
            if len(analysis["earnings_surprises"]) > 0:
                avg_surprise = sum(e["surprise_percent"] for e in analysis["earnings_surprises"]) / len(analysis["earnings_surprises"])
                if avg_surprise > 5:
                    analysis["sentiment_trend"] = "positive"
                elif avg_surprise < -5:
                    analysis["sentiment_trend"] = "negative"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing earnings for {symbol}: {e}")
            return {"error": str(e)}

class PredictionEngine:
    """Advanced ML models for price prediction"""
    
    def __init__(self):
        self.models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boost': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'neural_network': None  # Will be initialized when needed
        }
        self.scaler = StandardScaler()
    
    async def generate_predictions(self, symbol: str) -> List[PricePrediction]:
        """Generate price predictions using multiple models"""
        try:
            # Get historical data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="2y")
            
            if len(data) < 50:
                return []
            
            # Prepare features
            features = self._prepare_features(data)
            
            # Generate predictions for different horizons
            horizons = [1, 7, 30, 90]  # 1 day, 1 week, 1 month, 3 months
            predictions = []
            
            for horizon in horizons:
                pred = await self._predict_price(symbol, data, features, horizon)
                if pred:
                    predictions.append(pred)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error generating predictions for {symbol}: {e}")
            return []
    
    def _prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML models"""
        df = data.copy()
        
        # Technical indicators as features
        df['sma_5'] = df['Close'].rolling(5).mean()
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['sma_50'] = df['Close'].rolling(50).mean()
        
        # Price ratios
        df['price_sma5_ratio'] = df['Close'] / df['sma_5']
        df['price_sma20_ratio'] = df['Close'] / df['sma_20']
        
        # Volatility
        df['volatility'] = df['Close'].rolling(20).std()
        df['high_low_ratio'] = df['High'] / df['Low']
        
        # Volume indicators
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']
        
        # Returns
        df['return_1d'] = df['Close'].pct_change()
        df['return_5d'] = df['Close'].pct_change(5)
        df['return_20d'] = df['Close'].pct_change(20)
        
        # Drop NaN values
        df = df.dropna()
        
        return df
    
    async def _predict_price(self, symbol: str, data: pd.DataFrame, features: pd.DataFrame, horizon: int) -> Optional[PricePrediction]:
        """Generate prediction for specific horizon"""
        try:
            if len(features) < 100:  # Need minimum data
                return None
            
            # Prepare target variable (future price)
            target = features['Close'].shift(-horizon).dropna()
            feature_cols = ['sma_5', 'sma_20', 'sma_50', 'price_sma5_ratio', 'price_sma20_ratio',
                          'volatility', 'high_low_ratio', 'volume_ratio', 'return_1d', 'return_5d', 'return_20d']
            
            X = features[feature_cols].iloc[:-horizon]
            y = target
            
            # Align X and y
            min_len = min(len(X), len(y))
            X = X.iloc[:min_len]
            y = y.iloc[:min_len]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model (using Random Forest as primary)
            model = self.models['random_forest']
            model.fit(X_train_scaled, y_train)
            
            # Make prediction
            current_features = X.iloc[-1:].values
            current_features_scaled = self.scaler.transform(current_features)
            
            predicted_price = model.predict(current_features_scaled)[0]
            current_price = float(features['Close'].iloc[-1])
            
            # Calculate confidence intervals (simplified)
            y_pred_test = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred_test)
            std_error = np.sqrt(mse)
            
            confidence_lower = predicted_price - (1.96 * std_error)
            confidence_upper = predicted_price + (1.96 * std_error)
            
            # Calculate probabilities
            prob_up = 0.6 if predicted_price > current_price else 0.4
            prob_down = 1.0 - prob_up
            
            return PricePrediction(
                symbol=symbol,
                model_name="Random Forest",
                prediction_horizon=horizon,
                predicted_price=Decimal(str(round(predicted_price, 2))),
                confidence_interval_lower=Decimal(str(round(confidence_lower, 2))),
                confidence_interval_upper=Decimal(str(round(confidence_upper, 2))),
                probability_up=Decimal(str(round(prob_up, 3))),
                probability_down=Decimal(str(round(prob_down, 3))),
                key_factors=["Technical indicators", "Price momentum", "Volume patterns"],
                model_accuracy=Decimal(str(round(1 - (mse / np.var(y_test)), 3)))
            )
            
        except Exception as e:
            logger.error(f"Error predicting price for {symbol} horizon {horizon}: {e}")
            return None

class RiskAnalyzer:
    """Advanced risk assessment and scoring"""
    
    async def assess_risk(self, symbol: str) -> RiskMetrics:
        """Comprehensive risk assessment"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="2y")
            
            if len(data) < 252:  # Need at least 1 year of data
                return RiskMetrics(symbol=symbol, risk_level=RiskLevel.MEDIUM)
            
            # Calculate returns
            returns = data['Close'].pct_change().dropna()
            
            # Beta calculation (using SPY as market proxy)
            spy_data = yf.download("SPY", period="2y")['Close']
            spy_returns = spy_data.pct_change().dropna()
            
            # Align returns
            aligned_returns = pd.concat([returns, spy_returns], axis=1, keys=[symbol, 'SPY']).dropna()
            
            if len(aligned_returns) < 100:
                beta = None
                alpha = None
            else:
                covariance = aligned_returns.cov().iloc[0, 1]
                market_variance = aligned_returns['SPY'].var()
                beta = covariance / market_variance
                
                # Alpha calculation
                risk_free_rate = 0.02 / 252  # Assume 2% annual risk-free rate
                alpha = aligned_returns[symbol].mean() - (risk_free_rate + beta * (aligned_returns['SPY'].mean() - risk_free_rate))
                alpha *= 252  # Annualize
            
            # Risk metrics
            volatility = returns.std() * np.sqrt(252)  # Annualized
            sharpe_ratio = (returns.mean() * 252 - 0.02) / volatility if volatility > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else volatility
            sortino_ratio = (returns.mean() * 252 - 0.02) / downside_deviation if downside_deviation > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = abs(drawdowns.min())
            
            # Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5) * np.sqrt(252)
            
            # Expected Shortfall (Conditional VaR)
            var_threshold = np.percentile(returns, 5)
            expected_shortfall = returns[returns <= var_threshold].mean() * np.sqrt(252)
            
            # Risk level classification
            risk_score = (
                (volatility * 0.4) + 
                (max_drawdown * 0.3) + 
                (abs(var_95) * 0.3)
            )
            
            if risk_score < 0.15:
                risk_level = RiskLevel.VERY_LOW
            elif risk_score < 0.25:
                risk_level = RiskLevel.LOW
            elif risk_score < 0.35:
                risk_level = RiskLevel.MEDIUM
            elif risk_score < 0.50:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.VERY_HIGH
            
            return RiskMetrics(
                symbol=symbol,
                beta=Decimal(str(round(beta, 3))) if beta is not None else None,
                alpha=Decimal(str(round(alpha, 3))) if alpha is not None else None,
                sharpe_ratio=Decimal(str(round(sharpe_ratio, 3))),
                sortino_ratio=Decimal(str(round(sortino_ratio, 3))),
                max_drawdown=Decimal(str(round(max_drawdown, 3))),
                volatility=Decimal(str(round(volatility, 3))),
                value_at_risk_95=Decimal(str(round(var_95, 3))),
                expected_shortfall=Decimal(str(round(expected_shortfall, 3))),
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error assessing risk for {symbol}: {e}")
            return RiskMetrics(symbol=symbol, risk_level=RiskLevel.MEDIUM)

class PortfolioOptimizer:
    """Modern portfolio optimization using various methods"""
    
    async def optimize_portfolio(self, symbols: List[str], method: str = "mean_variance") -> Optional[PortfolioOptimization]:
        """Optimize portfolio allocation"""
        try:
            if len(symbols) < 2:
                return None
            
            # Get price data
            data = {}
            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1y")
                if len(hist) > 100:
                    data[symbol] = hist['Close']
            
            if len(data) < 2:
                return None
            
            # Create returns matrix
            price_df = pd.DataFrame(data).dropna()
            returns = price_df.pct_change().dropna()
            
            if method == "mean_variance":
                weights = self._mean_variance_optimization(returns)
            elif method == "risk_parity":
                weights = self._risk_parity_optimization(returns)
            elif method == "equal_weight":
                weights = [Decimal('1.0') / len(symbols)] * len(symbols)
            else:
                weights = self._mean_variance_optimization(returns)
            
            # Calculate portfolio metrics
            portfolio_return = sum(w * returns[sym].mean() for w, sym in zip(weights, symbols)) * 252
            portfolio_variance = 0
            for i, sym1 in enumerate(symbols):
                for j, sym2 in enumerate(symbols):
                    portfolio_variance += weights[i] * weights[j] * returns[[sym1, sym2]].cov().iloc[0, 1] * 252
            
            portfolio_volatility = np.sqrt(portfolio_variance)
            sharpe_ratio = (portfolio_return - 0.02) / portfolio_volatility if portfolio_volatility > 0 else 0
            
            return PortfolioOptimization(
                securities=symbols,
                weights=[Decimal(str(round(w, 4))) for w in weights],
                expected_return=Decimal(str(round(portfolio_return, 4))),
                expected_volatility=Decimal(str(round(portfolio_volatility, 4))),
                sharpe_ratio=Decimal(str(round(sharpe_ratio, 3))),
                optimization_method=method
            )
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return None
    
    def _mean_variance_optimization(self, returns: pd.DataFrame) -> List[float]:
        """Mean-variance optimization (simplified)"""
        try:
            # Calculate mean returns and covariance matrix
            mean_returns = returns.mean() * 252
            cov_matrix = returns.cov() * 252
            
            # Simple optimization: inverse volatility weighting
            volatilities = np.sqrt(np.diag(cov_matrix))
            inv_vol_weights = 1 / volatilities
            weights = inv_vol_weights / inv_vol_weights.sum()
            
            return weights.tolist()
            
        except Exception as e:
            logger.error(f"Error in mean-variance optimization: {e}")
            n_assets = len(returns.columns)
            return [1.0 / n_assets] * n_assets
    
    def _risk_parity_optimization(self, returns: pd.DataFrame) -> List[float]:
        """Risk parity optimization"""
        try:
            # Simplified risk parity: equal risk contribution
            cov_matrix = returns.cov() * 252
            inv_vol = 1 / np.sqrt(np.diag(cov_matrix))
            weights = inv_vol / inv_vol.sum()
            
            return weights.tolist()
            
        except Exception as e:
            logger.error(f"Error in risk parity optimization: {e}")
            n_assets = len(returns.columns)
            return [1.0 / n_assets] * n_assets

class MarketRegimeDetector:
    """Detect current market regime using multiple indicators"""
    
    async def detect_current_regime(self) -> MarketRegime:
        """Detect current market regime"""
        try:
            # Get market data (S&P 500)
            spy = yf.download("SPY", period="1y")
            
            # Calculate indicators for regime detection
            spy['sma_50'] = spy['Close'].rolling(50).mean()
            spy['sma_200'] = spy['Close'].rolling(200).mean()
            spy['volatility'] = spy['Close'].rolling(20).std()
            
            current_price = spy['Close'].iloc[-1]
            sma_50 = spy['sma_50'].iloc[-1]
            sma_200 = spy['sma_200'].iloc[-1]
            recent_volatility = spy['volatility'].iloc[-20:].mean()
            
            # Regime classification
            if current_price > sma_50 > sma_200 and recent_volatility < spy['volatility'].quantile(0.33):
                regime_name = "Bull Market"
                probability = Decimal('0.8')
                sectors_favored = ["Technology", "Growth", "Consumer Discretionary"]
                sectors_unfavored = ["Utilities", "Consumer Staples"]
            elif current_price < sma_50 < sma_200 and recent_volatility > spy['volatility'].quantile(0.67):
                regime_name = "Bear Market"
                probability = Decimal('0.8')
                sectors_favored = ["Consumer Staples", "Utilities", "Healthcare"]
                sectors_unfavored = ["Technology", "Energy", "Financials"]
            elif recent_volatility > spy['volatility'].quantile(0.75):
                regime_name = "High Volatility"
                probability = Decimal('0.7')
                sectors_favored = ["Financials", "Energy"]
                sectors_unfavored = ["REITs", "Utilities"]
            else:
                regime_name = "Sideways Market"
                probability = Decimal('0.6')
                sectors_favored = ["Dividend Stocks", "Value"]
                sectors_unfavored = ["High Growth", "Speculative"]
            
            return MarketRegime(
                regime_name=regime_name,
                start_date=date.today() - timedelta(days=30),  # Approximate
                probability=probability,
                sectors_favored=sectors_favored,
                sectors_unfavored=sectors_unfavored,
                key_indicators=["Price vs Moving Averages", "Volatility", "Market Breadth"],
                characteristics={
                    "price_vs_sma50": "above" if current_price > sma_50 else "below",
                    "sma50_vs_sma200": "above" if sma_50 > sma_200 else "below",
                    "volatility_regime": "high" if recent_volatility > spy['volatility'].quantile(0.67) else "low"
                }
            )
            
        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return MarketRegime(
                regime_name="Unknown",
                start_date=date.today(),
                probability=Decimal('0.5'),
                key_indicators=["Error in analysis"]
            )

# Factory function for easy initialization
def create_ai_analysis_engine() -> AIAnalysisEngine:
    """Create and return configured AI analysis engine"""
    return AIAnalysisEngine()