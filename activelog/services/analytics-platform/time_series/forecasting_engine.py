"""
Time Series Analysis and Forecasting Engine
Advanced forecasting capabilities with multiple models
"""

import asyncio
import logging
import warnings
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Time series libraries
from prophet import Prophet
import pmdarima as pm
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class ForecastModel(str, Enum):
    PROPHET = "prophet"
    ARIMA = "arima"
    AUTO_ARIMA = "auto_arima"
    ETS = "ets"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LINEAR_TREND = "linear_trend"
    SEASONAL_NAIVE = "seasonal_naive"
    MOVING_AVERAGE = "moving_average"

class SeasonalityType(str, Enum):
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    AUTO = "auto"

class TrendType(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGISTIC = "logistic"
    FLAT = "flat"

@dataclass
class ForecastConfig:
    model_type: ForecastModel
    forecast_periods: int
    confidence_intervals: List[float] = field(default_factory=lambda: [0.8, 0.95])
    seasonality_type: SeasonalityType = SeasonalityType.AUTO
    trend_type: TrendType = TrendType.LINEAR
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation_split: float = 0.2
    cross_validation: bool = True

@dataclass
class ForecastResult:
    model_name: str
    forecast: pd.DataFrame
    confidence_intervals: Dict[str, pd.DataFrame]
    metrics: Dict[str, float]
    model_parameters: Dict[str, Any]
    decomposition: Optional[Dict[str, pd.Series]] = None
    residuals: Optional[pd.Series] = None
    validation_results: Optional[Dict[str, Any]] = None
    feature_importance: Optional[Dict[str, float]] = None

class TimeSeriesAnalyzer:
    """Advanced time series analysis and preprocessing"""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    async def analyze_time_series(self, data: pd.Series) -> Dict[str, Any]:
        """Comprehensive time series analysis"""
        analysis = {
            'basic_stats': await self._calculate_basic_stats(data),
            'stationarity': await self._test_stationarity(data),
            'seasonality': await self._detect_seasonality(data),
            'trend': await self._analyze_trend(data),
            'outliers': await self._detect_outliers(data),
            'autocorrelation': await self._analyze_autocorrelation(data),
            'decomposition': await self._decompose_series(data)
        }
        
        return analysis
    
    async def _calculate_basic_stats(self, data: pd.Series) -> Dict[str, Any]:
        """Calculate basic statistical measures"""
        return {
            'count': len(data),
            'mean': data.mean(),
            'median': data.median(),
            'std': data.std(),
            'variance': data.var(),
            'min': data.min(),
            'max': data.max(),
            'skewness': stats.skew(data.dropna()),
            'kurtosis': stats.kurtosis(data.dropna()),
            'missing_values': data.isnull().sum(),
            'missing_percentage': (data.isnull().sum() / len(data)) * 100
        }
    
    async def _test_stationarity(self, data: pd.Series) -> Dict[str, Any]:
        """Test for stationarity using ADF and KPSS tests"""
        # Augmented Dickey-Fuller test
        adf_result = adfuller(data.dropna())
        
        # KPSS test
        kpss_result = kpss(data.dropna(), regression='c', nlags="auto")
        
        return {
            'adf_test': {
                'statistic': adf_result[0],
                'p_value': adf_result[1],
                'critical_values': adf_result[4],
                'is_stationary': adf_result[1] < 0.05
            },
            'kpss_test': {
                'statistic': kpss_result[0],
                'p_value': kpss_result[1],
                'critical_values': kpss_result[3],
                'is_stationary': kpss_result[1] > 0.05
            },
            'recommendation': self._get_stationarity_recommendation(adf_result[1], kpss_result[1])
        }
    
    def _get_stationarity_recommendation(self, adf_p: float, kpss_p: float) -> str:
        """Get recommendation based on stationarity tests"""
        if adf_p < 0.05 and kpss_p > 0.05:
            return "Series is stationary"
        elif adf_p >= 0.05 and kpss_p <= 0.05:
            return "Series is non-stationary, consider differencing"
        elif adf_p >= 0.05 and kpss_p > 0.05:
            return "Series is trend stationary, consider detrending"
        else:
            return "Tests are inconclusive, manual inspection required"
    
    async def _detect_seasonality(self, data: pd.Series) -> Dict[str, Any]:
        """Detect seasonal patterns in the data"""
        # Try different seasonal periods
        seasonal_periods = [7, 12, 24, 30, 365]  # Daily, monthly, hourly, etc.
        seasonality_results = {}
        
        for period in seasonal_periods:
            if len(data) >= 2 * period:
                try:
                    decomposition = seasonal_decompose(
                        data.dropna(), 
                        model='additive', 
                        period=period,
                        extrapolate_trend='freq'
                    )
                    
                    # Calculate seasonal strength
                    seasonal_strength = 1 - (np.var(decomposition.resid.dropna()) / 
                                           np.var(decomposition.seasonal.dropna() + decomposition.resid.dropna()))
                    
                    seasonality_results[f'period_{period}'] = {
                        'seasonal_strength': max(0, seasonal_strength),
                        'seasonal_variance': np.var(decomposition.seasonal.dropna())
                    }
                except:
                    continue
        
        # Determine dominant seasonality
        if seasonality_results:
            dominant_period = max(seasonality_results.keys(), 
                                key=lambda x: seasonality_results[x]['seasonal_strength'])
            return {
                'has_seasonality': max(seasonality_results.values(), 
                                     key=lambda x: x['seasonal_strength'])['seasonal_strength'] > 0.1,
                'dominant_period': int(dominant_period.split('_')[1]),
                'seasonal_strength': seasonality_results[dominant_period]['seasonal_strength'],
                'all_periods': seasonality_results
            }
        
        return {'has_seasonality': False, 'dominant_period': None}
    
    async def _analyze_trend(self, data: pd.Series) -> Dict[str, Any]:
        """Analyze trend in the time series"""
        # Linear trend
        x = np.arange(len(data))
        y = data.values
        
        # Remove NaN values
        mask = ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return {'trend_type': 'insufficient_data', 'trend_strength': 0}
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
        
        # Determine trend type
        trend_type = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'flat'
        
        return {
            'trend_type': trend_type,
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'trend_strength': abs(r_value),
            'is_significant': p_value < 0.05
        }
    
    async def _detect_outliers(self, data: pd.Series) -> Dict[str, Any]:
        """Detect outliers using multiple methods"""
        clean_data = data.dropna()
        
        # IQR method
        q1 = clean_data.quantile(0.25)
        q3 = clean_data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        iqr_outliers = clean_data[(clean_data < lower_bound) | (clean_data > upper_bound)]
        
        # Z-score method
        z_scores = np.abs(stats.zscore(clean_data))
        z_outliers = clean_data[z_scores > 3]
        
        # Modified Z-score method
        median = np.median(clean_data)
        mad = np.median(np.abs(clean_data - median))
        modified_z_scores = 0.6745 * (clean_data - median) / mad
        modified_z_outliers = clean_data[np.abs(modified_z_scores) > 3.5]
        
        return {
            'iqr_outliers': len(iqr_outliers),
            'iqr_outlier_indices': iqr_outliers.index.tolist(),
            'z_score_outliers': len(z_outliers),
            'z_score_outlier_indices': z_outliers.index.tolist(),
            'modified_z_outliers': len(modified_z_outliers),
            'modified_z_outlier_indices': modified_z_outliers.index.tolist(),
            'outlier_percentage': (len(iqr_outliers) / len(clean_data)) * 100
        }
    
    async def _analyze_autocorrelation(self, data: pd.Series) -> Dict[str, Any]:
        """Analyze autocorrelation structure"""
        from statsmodels.tsa.stattools import acf, pacf
        
        clean_data = data.dropna()
        max_lags = min(40, len(clean_data) // 4)
        
        if max_lags < 1:
            return {'insufficient_data': True}
        
        # Autocorrelation function
        acf_values = acf(clean_data, nlags=max_lags, alpha=0.05)
        
        # Partial autocorrelation function
        pacf_values = pacf(clean_data, nlags=max_lags, alpha=0.05)
        
        return {
            'acf': acf_values[0].tolist(),
            'acf_confidence': acf_values[1].tolist() if len(acf_values) > 1 else None,
            'pacf': pacf_values[0].tolist(),
            'pacf_confidence': pacf_values[1].tolist() if len(pacf_values) > 1 else None,
            'significant_lags': self._find_significant_lags(acf_values[0], acf_values[1] if len(acf_values) > 1 else None)
        }
    
    def _find_significant_lags(self, acf_values: np.ndarray, confidence_intervals: Optional[np.ndarray]) -> List[int]:
        """Find statistically significant lags"""
        significant_lags = []
        
        if confidence_intervals is not None:
            for i, (acf_val, (lower, upper)) in enumerate(zip(acf_values[1:], confidence_intervals[1:])):
                if acf_val < lower or acf_val > upper:
                    significant_lags.append(i + 1)
        
        return significant_lags
    
    async def _decompose_series(self, data: pd.Series) -> Dict[str, Any]:
        """Decompose time series into trend, seasonal, and residual components"""
        if len(data) < 24:  # Need sufficient data for decomposition
            return {'error': 'Insufficient data for decomposition'}
        
        try:
            # Try additive decomposition
            decomposition_add = seasonal_decompose(
                data.dropna(), 
                model='additive',
                extrapolate_trend='freq'
            )
            
            # Try multiplicative decomposition
            decomposition_mult = seasonal_decompose(
                data.dropna(), 
                model='multiplicative',
                extrapolate_trend='freq'
            )
            
            return {
                'additive': {
                    'trend': decomposition_add.trend.dropna().to_dict(),
                    'seasonal': decomposition_add.seasonal.dropna().to_dict(),
                    'residual': decomposition_add.resid.dropna().to_dict()
                },
                'multiplicative': {
                    'trend': decomposition_mult.trend.dropna().to_dict(),
                    'seasonal': decomposition_mult.seasonal.dropna().to_dict(),
                    'residual': decomposition_mult.resid.dropna().to_dict()
                }
            }
        except Exception as e:
            return {'error': str(e)}

class ForecastingEngine:
    """Main forecasting engine with multiple models"""
    
    def __init__(self):
        self.models = {}
        self.fitted_models = {}
        self.analyzer = TimeSeriesAnalyzer()
    
    async def create_forecast(self, data: pd.Series, config: ForecastConfig) -> ForecastResult:
        """Create forecast using specified model"""
        logger.info(f"Creating forecast with {config.model_type} model")
        
        # Prepare data
        prepared_data = await self._prepare_data(data)
        
        # Split data for validation
        if config.validation_split > 0:
            split_point = int(len(prepared_data) * (1 - config.validation_split))
            train_data = prepared_data[:split_point]
            test_data = prepared_data[split_point:]
        else:
            train_data = prepared_data
            test_data = None
        
        # Select and fit model
        if config.model_type == ForecastModel.PROPHET:
            result = await self._forecast_prophet(train_data, config)
        elif config.model_type == ForecastModel.ARIMA:
            result = await self._forecast_arima(train_data, config)
        elif config.model_type == ForecastModel.AUTO_ARIMA:
            result = await self._forecast_auto_arima(train_data, config)
        elif config.model_type == ForecastModel.ETS:
            result = await self._forecast_ets(train_data, config)
        elif config.model_type == ForecastModel.EXPONENTIAL_SMOOTHING:
            result = await self._forecast_exponential_smoothing(train_data, config)
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
        
        # Validate model if test data available
        if test_data is not None and len(test_data) > 0:
            validation_results = await self._validate_forecast(result, test_data)
            result.validation_results = validation_results
        
        # Cross-validation
        if config.cross_validation and len(prepared_data) > 50:
            cv_results = await self._cross_validate_forecast(prepared_data, config)
            if result.validation_results is None:
                result.validation_results = {}
            result.validation_results['cross_validation'] = cv_results
        
        return result
    
    async def _prepare_data(self, data: pd.Series) -> pd.Series:
        """Prepare data for forecasting"""
        # Handle missing values
        if data.isnull().any():
            # Forward fill then backward fill
            data = data.fillna(method='ffill').fillna(method='bfill')
        
        # Ensure datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            if isinstance(data.index, pd.RangeIndex):
                # Create a synthetic datetime index
                data.index = pd.date_range(start='2020-01-01', periods=len(data), freq='D')
            else:
                data.index = pd.to_datetime(data.index)
        
        # Sort by index
        data = data.sort_index()
        
        return data
    
    async def _forecast_prophet(self, data: pd.Series, config: ForecastConfig) -> ForecastResult:
        """Prophet forecasting model"""
        # Prepare data for Prophet
        df = pd.DataFrame({
            'ds': data.index,
            'y': data.values
        })
        
        # Initialize Prophet model
        prophet_params = config.parameters.copy()
        
        # Set seasonality mode
        if config.seasonality_type == SeasonalityType.ADDITIVE:
            prophet_params['seasonality_mode'] = 'additive'
        elif config.seasonality_type == SeasonalityType.MULTIPLICATIVE:
            prophet_params['seasonality_mode'] = 'multiplicative'
        
        # Set growth
        if config.trend_type == TrendType.LINEAR:
            prophet_params['growth'] = 'linear'
        elif config.trend_type == TrendType.LOGISTIC:
            prophet_params['growth'] = 'logistic'
            # Need to set cap for logistic growth
            if 'cap' not in prophet_params:
                prophet_params['cap'] = data.max() * 1.2
        
        model = Prophet(**prophet_params)
        
        # Fit model
        model.fit(df)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=config.forecast_periods)
        if config.trend_type == TrendType.LOGISTIC and 'cap' in prophet_params:
            future['cap'] = prophet_params['cap']
        
        # Make forecast
        forecast = model.predict(future)
        
        # Extract forecast results
        forecast_df = forecast[['ds', 'yhat']].tail(config.forecast_periods)
        forecast_df.set_index('ds', inplace=True)
        forecast_df.columns = ['forecast']
        
        # Extract confidence intervals
        confidence_intervals = {}
        for interval in config.confidence_intervals:
            lower_col = f'yhat_lower_{interval}'
            upper_col = f'yhat_upper_{interval}'
            
            # Prophet uses 80% interval by default, adjust if needed
            if interval == 0.8:
                conf_df = forecast[['ds', 'yhat_lower', 'yhat_upper']].tail(config.forecast_periods)
                conf_df.set_index('ds', inplace=True)
                conf_df.columns = ['lower', 'upper']
            else:
                # Approximate other intervals
                forecast_std = (forecast['yhat_upper'] - forecast['yhat_lower']) / 2.576  # 99% interval
                z_score = stats.norm.ppf((1 + interval) / 2)
                
                conf_df = pd.DataFrame({
                    'lower': forecast['yhat'] - z_score * forecast_std,
                    'upper': forecast['yhat'] + z_score * forecast_std
                }, index=forecast['ds']).tail(config.forecast_periods)
            
            confidence_intervals[f'{interval}'] = conf_df
        
        # Calculate metrics on training data
        train_forecast = forecast[['ds', 'yhat']].iloc[:-config.forecast_periods]
        train_forecast.set_index('ds', inplace=True)
        
        metrics = await self._calculate_metrics(data, train_forecast['yhat'])
        
        # Get residuals
        residuals = data - train_forecast['yhat']
        
        return ForecastResult(
            model_name='Prophet',
            forecast=forecast_df,
            confidence_intervals=confidence_intervals,
            metrics=metrics,
            model_parameters=prophet_params,
            residuals=residuals
        )
    
    async def _forecast_arima(self, data: pd.Series, config: ForecastConfig) -> ForecastResult:
        """ARIMA forecasting model"""
        arima_params = config.parameters
        
        # Default ARIMA order if not specified
        order = arima_params.get('order', (1, 1, 1))
        seasonal_order = arima_params.get('seasonal_order', (0, 0, 0, 0))
        
        # Fit ARIMA model
        model = ARIMA(data, order=order, seasonal_order=seasonal_order)
        fitted_model = model.fit()
        
        # Make forecast
        forecast_result = fitted_model.forecast(steps=config.forecast_periods, alpha=1-config.confidence_intervals[0])
        
        # Create forecast dataframe
        last_date = data.index[-1]
        forecast_index = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=config.forecast_periods,
            freq=pd.infer_freq(data.index) or 'D'
        )
        
        forecast_df = pd.DataFrame({
            'forecast': forecast_result
        }, index=forecast_index)
        
        # Get prediction intervals
        pred_ci = fitted_model.get_prediction(start=len(data), end=len(data) + config.forecast_periods - 1).conf_int()
        
        confidence_intervals = {}
        for interval in config.confidence_intervals:
            # ARIMA confidence intervals
            alpha = 1 - interval
            pred_ci_interval = fitted_model.get_prediction(
                start=len(data), 
                end=len(data) + config.forecast_periods - 1,
                alpha=alpha
            ).conf_int()
            
            conf_df = pd.DataFrame({
                'lower': pred_ci_interval.iloc[:, 0],
                'upper': pred_ci_interval.iloc[:, 1]
            }, index=forecast_index)
            
            confidence_intervals[f'{interval}'] = conf_df
        
        # Calculate metrics
        fitted_values = fitted_model.fittedvalues
        metrics = await self._calculate_metrics(data, fitted_values)
        
        # Get residuals
        residuals = fitted_model.resid
        
        return ForecastResult(
            model_name='ARIMA',
            forecast=forecast_df,
            confidence_intervals=confidence_intervals,
            metrics=metrics,
            model_parameters={'order': order, 'seasonal_order': seasonal_order},
            residuals=residuals
        )
    
    async def _forecast_auto_arima(self, data: pd.Series, config: ForecastConfig) -> ForecastResult:
        """Auto ARIMA forecasting model"""
        auto_arima_params = config.parameters.copy()
        
        # Set default parameters
        auto_arima_params.setdefault('seasonal', True)
        auto_arima_params.setdefault('stepwise', True)
        auto_arima_params.setdefault('suppress_warnings', True)
        auto_arima_params.setdefault('error_action', 'ignore')
        
        # Fit Auto ARIMA
        model = pm.auto_arima(data, **auto_arima_params)
        
        # Make forecast
        forecast_result, conf_int = model.predict(n_periods=config.forecast_periods, return_conf_int=True)
        
        # Create forecast dataframe
        last_date = data.index[-1]
        forecast_index = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=config.forecast_periods,
            freq=pd.infer_freq(data.index) or 'D'
        )
        
        forecast_df = pd.DataFrame({
            'forecast': forecast_result
        }, index=forecast_index)
        
        # Confidence intervals
        confidence_intervals = {}
        for interval in config.confidence_intervals:
            conf_df = pd.DataFrame({
                'lower': conf_int[:, 0],
                'upper': conf_int[:, 1]
            }, index=forecast_index)
            
            confidence_intervals[f'{interval}'] = conf_df
        
        # Calculate metrics
        fitted_values = model.predict_in_sample()
        metrics = await self._calculate_metrics(data, fitted_values)
        
        # Get residuals
        residuals = data - fitted_values
        
        return ForecastResult(
            model_name='Auto-ARIMA',
            forecast=forecast_df,
            confidence_intervals=confidence_intervals,
            metrics=metrics,
            model_parameters={'order': model.order, 'seasonal_order': model.seasonal_order},
            residuals=residuals
        )
    
    async def _forecast_ets(self, data: pd.Series, config: ForecastConfig) -> ForecastResult:
        """ETS (Error, Trend, Seasonal) forecasting model"""
        ets_params = config.parameters.copy()
        
        # Fit ETS model
        model = ETSModel(
            data,
            error=ets_params.get('error', 'add'),
            trend=ets_params.get('trend', 'add'),
            seasonal=ets_params.get('seasonal', 'add')
        )
        
        fitted_model = model.fit()
        
        # Make forecast
        forecast_result = fitted_model.forecast(steps=config.forecast_periods)
        
        # Create forecast dataframe
        last_date = data.index[-1]
        forecast_index = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=config.forecast_periods,
            freq=pd.infer_freq(data.index) or 'D'
        )
        
        forecast_df = pd.DataFrame({
            'forecast': forecast_result
        }, index=forecast_index)
        
        # Confidence intervals (simplified)
        confidence_intervals = {}
        forecast_std = np.std(fitted_model.resid.dropna())
        
        for interval in config.confidence_intervals:
            z_score = stats.norm.ppf((1 + interval) / 2)
            conf_df = pd.DataFrame({
                'lower': forecast_result - z_score * forecast_std,
                'upper': forecast_result + z_score * forecast_std
            }, index=forecast_index)
            
            confidence_intervals[f'{interval}'] = conf_df
        
        # Calculate metrics
        fitted_values = fitted_model.fittedvalues
        metrics = await self._calculate_metrics(data, fitted_values)
        
        return ForecastResult(
            model_name='ETS',
            forecast=forecast_df,
            confidence_intervals=confidence_intervals,
            metrics=metrics,
            model_parameters=ets_params,
            residuals=fitted_model.resid
        )
    
    async def _forecast_exponential_smoothing(self, data: pd.Series, config: ForecastConfig) -> ForecastResult:
        """Exponential Smoothing forecasting model"""
        es_params = config.parameters.copy()
        
        # Set trend and seasonal parameters
        trend = es_params.get('trend', 'add')
        seasonal = es_params.get('seasonal', 'add')
        seasonal_periods = es_params.get('seasonal_periods', 12)
        
        # Fit Exponential Smoothing model
        model = ExponentialSmoothing(
            data,
            trend=trend,
            seasonal=seasonal,
            seasonal_periods=seasonal_periods
        )
        
        fitted_model = model.fit()
        
        # Make forecast
        forecast_result = fitted_model.forecast(steps=config.forecast_periods)
        
        # Create forecast dataframe
        last_date = data.index[-1]
        forecast_index = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=config.forecast_periods,
            freq=pd.infer_freq(data.index) or 'D'
        )
        
        forecast_df = pd.DataFrame({
            'forecast': forecast_result
        }, index=forecast_index)
        
        # Confidence intervals (simplified)
        confidence_intervals = {}
        forecast_std = np.std(fitted_model.resid.dropna())
        
        for interval in config.confidence_intervals:
            z_score = stats.norm.ppf((1 + interval) / 2)
            conf_df = pd.DataFrame({
                'lower': forecast_result - z_score * forecast_std,
                'upper': forecast_result + z_score * forecast_std
            }, index=forecast_index)
            
            confidence_intervals[f'{interval}'] = conf_df
        
        # Calculate metrics
        fitted_values = fitted_model.fittedvalues
        metrics = await self._calculate_metrics(data, fitted_values)
        
        return ForecastResult(
            model_name='Exponential Smoothing',
            forecast=forecast_df,
            confidence_intervals=confidence_intervals,
            metrics=metrics,
            model_parameters=es_params,
            residuals=fitted_model.resid
        )
    
    async def _calculate_metrics(self, actual: pd.Series, predicted: pd.Series) -> Dict[str, float]:
        """Calculate forecast accuracy metrics"""
        # Align series
        common_index = actual.index.intersection(predicted.index)
        actual_aligned = actual[common_index]
        predicted_aligned = predicted[common_index]
        
        if len(actual_aligned) == 0:
            return {}
        
        # Calculate metrics
        mae = mean_absolute_error(actual_aligned, predicted_aligned)
        mse = mean_squared_error(actual_aligned, predicted_aligned)
        rmse = np.sqrt(mse)
        
        # MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((actual_aligned - predicted_aligned) / actual_aligned)) * 100
        
        # R-squared
        r2 = r2_score(actual_aligned, predicted_aligned)
        
        return {
            'mae': mae,
            'mse': mse,
            'rmse': rmse,
            'mape': mape,
            'r2': r2
        }
    
    async def _validate_forecast(self, forecast_result: ForecastResult, test_data: pd.Series) -> Dict[str, Any]:
        """Validate forecast against test data"""
        forecast_values = forecast_result.forecast['forecast']
        
        # Align test data with forecast
        common_index = test_data.index.intersection(forecast_values.index)
        
        if len(common_index) == 0:
            return {'error': 'No overlapping dates between forecast and test data'}
        
        test_aligned = test_data[common_index]
        forecast_aligned = forecast_values[common_index]
        
        # Calculate validation metrics
        validation_metrics = await self._calculate_metrics(test_aligned, forecast_aligned)
        
        return {
            'validation_metrics': validation_metrics,
            'test_period_length': len(test_aligned),
            'forecast_coverage': len(common_index) / len(forecast_values)
        }
    
    async def _cross_validate_forecast(self, data: pd.Series, config: ForecastConfig) -> Dict[str, Any]:
        """Perform time series cross-validation"""
        tscv = TimeSeriesSplit(n_splits=5)
        cv_metrics = []
        
        for train_idx, test_idx in tscv.split(data):
            train_data = data.iloc[train_idx]
            test_data = data.iloc[test_idx]
            
            # Create temporary config for CV
            cv_config = ForecastConfig(
                model_type=config.model_type,
                forecast_periods=len(test_data),
                confidence_intervals=config.confidence_intervals,
                parameters=config.parameters,
                validation_split=0,  # Don't split during CV
                cross_validation=False  # Avoid recursive CV
            )
            
            try:
                cv_result = await self.create_forecast(train_data, cv_config)
                
                # Calculate metrics for this fold
                forecast_values = cv_result.forecast['forecast']
                common_index = test_data.index.intersection(forecast_values.index)
                
                if len(common_index) > 0:
                    test_aligned = test_data[common_index]
                    forecast_aligned = cv_result.forecast['forecast'][common_index]
                    metrics = await self._calculate_metrics(test_aligned, forecast_aligned)
                    cv_metrics.append(metrics)
                
            except Exception as e:
                logger.warning(f"CV fold failed: {e}")
                continue
        
        if cv_metrics:
            # Average metrics across folds
            avg_metrics = {}
            for metric in cv_metrics[0].keys():
                avg_metrics[f'avg_{metric}'] = np.mean([m[metric] for m in cv_metrics])
                avg_metrics[f'std_{metric}'] = np.std([m[metric] for m in cv_metrics])
            
            return {
                'cv_folds': len(cv_metrics),
                'avg_metrics': avg_metrics,
                'individual_folds': cv_metrics
            }
        
        return {'error': 'Cross-validation failed'}
    
    async def create_ensemble_forecast(self, data: pd.Series, 
                                     model_configs: List[ForecastConfig]) -> ForecastResult:
        """Create ensemble forecast from multiple models"""
        individual_forecasts = []
        
        # Create forecasts for each model
        for config in model_configs:
            try:
                forecast_result = await self.create_forecast(data, config)
                individual_forecasts.append(forecast_result)
            except Exception as e:
                logger.warning(f"Model {config.model_type} failed: {e}")
                continue
        
        if not individual_forecasts:
            raise ValueError("No successful forecasts to ensemble")
        
        # Combine forecasts (simple average)
        forecast_dfs = [f.forecast for f in individual_forecasts]
        ensemble_forecast = pd.concat(forecast_dfs, axis=1).mean(axis=1).to_frame('forecast')
        
        # Combine confidence intervals
        ensemble_intervals = {}
        for interval in model_configs[0].confidence_intervals:
            interval_dfs = []
            for forecast in individual_forecasts:
                if f'{interval}' in forecast.confidence_intervals:
                    interval_dfs.append(forecast.confidence_intervals[f'{interval}'])
            
            if interval_dfs:
                # Average the bounds
                combined_lower = pd.concat([df['lower'] for df in interval_dfs], axis=1).mean(axis=1)
                combined_upper = pd.concat([df['upper'] for df in interval_dfs], axis=1).mean(axis=1)
                
                ensemble_intervals[f'{interval}'] = pd.DataFrame({
                    'lower': combined_lower,
                    'upper': combined_upper
                })
        
        # Combine metrics (average)
        all_metrics = [f.metrics for f in individual_forecasts if f.metrics]
        if all_metrics:
            ensemble_metrics = {}
            for metric in all_metrics[0].keys():
                ensemble_metrics[metric] = np.mean([m[metric] for m in all_metrics])
        else:
            ensemble_metrics = {}
        
        return ForecastResult(
            model_name='Ensemble',
            forecast=ensemble_forecast,
            confidence_intervals=ensemble_intervals,
            metrics=ensemble_metrics,
            model_parameters={'models': [config.model_type for config in model_configs]},
            validation_results={'individual_models': len(individual_forecasts)}
        )
    
    async def generate_forecast_visualization(self, data: pd.Series, 
                                            forecast_result: ForecastResult) -> go.Figure:
        """Generate interactive forecast visualization"""
        fig = go.Figure()
        
        # Historical data
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data.values,
            mode='lines',
            name='Historical Data',
            line=dict(color='blue')
        ))
        
        # Forecast
        forecast_data = forecast_result.forecast['forecast']
        fig.add_trace(go.Scatter(
            x=forecast_data.index,
            y=forecast_data.values,
            mode='lines',
            name=f'{forecast_result.model_name} Forecast',
            line=dict(color='red', dash='dash')
        ))
        
        # Confidence intervals
        for interval_name, interval_df in forecast_result.confidence_intervals.items():
            fig.add_trace(go.Scatter(
                x=interval_df.index,
                y=interval_df['upper'],
                fill=None,
                mode='lines',
                line_color='rgba(0,0,0,0)',
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=interval_df.index,
                y=interval_df['lower'],
                fill='tonexty',
                mode='lines',
                line_color='rgba(0,0,0,0)',
                name=f'{float(interval_name)*100:.0f}% CI',
                fillcolor=f'rgba(255, 0, 0, {0.1 * float(interval_name)})'
            ))
        
        fig.update_layout(
            title=f'Time Series Forecast - {forecast_result.model_name}',
            xaxis_title='Date',
            yaxis_title='Value',
            hovermode='x unified'
        )
        
        return fig