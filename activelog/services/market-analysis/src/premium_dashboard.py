"""
Premium Dashboard - Interactive Visualizations and Real-time Alerts
Professional-grade dashboard with advanced visualizations, real-time streaming, and comprehensive analytics
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

logger = logging.getLogger(__name__)

class PremiumDashboardEngine:
    """Premium dashboard with real-time capabilities"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.alert_engine = RealTimeAlertEngine()
        self.visualization_engine = AdvancedVisualizationEngine()
        self.streaming_engine = StreamingDataEngine()
        self.portfolio_monitor = PortfolioMonitoringEngine()
        
    async def get_premium_dashboard_html(self) -> str:
        """Generate premium dashboard HTML with advanced features"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Market Analysis Pro - Premium Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.3.0"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: linear-gradient(135deg, #1e1e2e 0%, #27273f 100%);
                    color: #ffffff;
                    min-height: 100vh;
                    overflow-x: hidden;
                }
                
                .premium-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px 0;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    position: relative;
                    z-index: 1000;
                }
                
                .header-content {
                    max-width: 1600px;
                    margin: 0 auto;
                    padding: 0 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .premium-logo {
                    display: flex;
                    align-items: center;
                    font-size: 1.8em;
                    font-weight: 700;
                    color: #fff;
                }
                
                .premium-logo i {
                    margin-right: 12px;
                    font-size: 1.2em;
                    background: linear-gradient(45deg, #ffd700, #ffed4a);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
                
                .status-indicators {
                    display: flex;
                    gap: 20px;
                    align-items: center;
                }
                
                .status-indicator {
                    display: flex;
                    align-items: center;
                    background: rgba(255,255,255,0.1);
                    padding: 8px 16px;
                    border-radius: 25px;
                    font-size: 0.9em;
                    transition: all 0.3s ease;
                }
                
                .status-indicator:hover {
                    background: rgba(255,255,255,0.2);
                    transform: translateY(-2px);
                }
                
                .status-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    margin-right: 8px;
                    animation: pulse 2s infinite;
                }
                
                .status-live { background-color: #10b981; }
                .status-processing { background-color: #f59e0b; }
                .status-alert { background-color: #ef4444; }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                
                .dashboard-container {
                    max-width: 1600px;
                    margin: 0 auto;
                    padding: 30px 20px;
                    display: grid;
                    grid-template-columns: 1fr 350px;
                    gap: 30px;
                    min-height: calc(100vh - 100px);
                }
                
                .main-content {
                    display: grid;
                    gap: 25px;
                }
                
                .sidebar {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                
                .premium-card {
                    background: linear-gradient(135deg, #2a2a3e 0%, #3a3a54 100%);
                    border-radius: 16px;
                    padding: 25px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    border: 1px solid rgba(255,255,255,0.1);
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }
                
                .premium-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
                    background-size: 200% 100%;
                    animation: shimmer 3s ease-in-out infinite;
                }
                
                @keyframes shimmer {
                    0%, 100% { background-position: 200% 0; }
                    50% { background-position: -200% 0; }
                }
                
                .premium-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 12px 48px rgba(0,0,0,0.4);
                    border-color: rgba(255,255,255,0.2);
                }
                
                .card-header {
                    display: flex;
                    justify-content: between;
                    align-items: center;
                    margin-bottom: 20px;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                    padding-bottom: 15px;
                }
                
                .card-title {
                    font-size: 1.3em;
                    font-weight: 600;
                    color: #fff;
                    display: flex;
                    align-items: center;
                }
                
                .card-title i {
                    margin-right: 10px;
                    color: #667eea;
                }
                
                .card-actions {
                    display: flex;
                    gap: 8px;
                }
                
                .action-btn {
                    background: rgba(255,255,255,0.1);
                    border: none;
                    color: #fff;
                    padding: 6px 12px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 0.85em;
                    transition: all 0.2s ease;
                }
                
                .action-btn:hover {
                    background: rgba(255,255,255,0.2);
                    transform: scale(1.05);
                }
                
                .market-overview-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }
                
                .metric-card {
                    background: rgba(255,255,255,0.05);
                    padding: 20px;
                    border-radius: 12px;
                    text-align: center;
                    border: 1px solid rgba(255,255,255,0.1);
                    transition: all 0.3s ease;
                }
                
                .metric-card:hover {
                    background: rgba(255,255,255,0.1);
                    transform: scale(1.02);
                }
                
                .metric-value {
                    font-size: 2em;
                    font-weight: 700;
                    margin-bottom: 5px;
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
                
                .metric-label {
                    font-size: 0.9em;
                    color: #b3b3b3;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .metric-change {
                    font-size: 0.85em;
                    margin-top: 5px;
                    padding: 2px 8px;
                    border-radius: 12px;
                }
                
                .metric-change.positive {
                    background: rgba(16, 185, 129, 0.2);
                    color: #10b981;
                }
                
                .metric-change.negative {
                    background: rgba(239, 68, 68, 0.2);
                    color: #ef4444;
                }
                
                .chart-container {
                    height: 400px;
                    width: 100%;
                    margin-top: 20px;
                    background: rgba(255,255,255,0.02);
                    border-radius: 12px;
                    padding: 15px;
                }
                
                .heatmap-container {
                    display: grid;
                    grid-template-columns: repeat(5, 1fr);
                    gap: 8px;
                    margin-top: 20px;
                }
                
                .heatmap-cell {
                    aspect-ratio: 1;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.8em;
                    font-weight: 600;
                    color: #fff;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }
                
                .heatmap-cell:hover {
                    transform: scale(1.1);
                    z-index: 10;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
                }
                
                .alert-item {
                    display: flex;
                    align-items: center;
                    padding: 15px;
                    background: rgba(255,255,255,0.05);
                    border-radius: 10px;
                    margin-bottom: 10px;
                    border-left: 4px solid;
                    transition: all 0.3s ease;
                }
                
                .alert-item:hover {
                    background: rgba(255,255,255,0.1);
                    transform: translateX(5px);
                }
                
                .alert-critical { border-left-color: #ef4444; }
                .alert-warning { border-left-color: #f59e0b; }
                .alert-info { border-left-color: #3b82f6; }
                .alert-success { border-left-color: #10b981; }
                
                .alert-icon {
                    margin-right: 12px;
                    font-size: 1.2em;
                }
                
                .alert-content {
                    flex: 1;
                }
                
                .alert-title {
                    font-weight: 600;
                    margin-bottom: 4px;
                }
                
                .alert-time {
                    font-size: 0.8em;
                    color: #b3b3b3;
                }
                
                .portfolio-summary {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin-bottom: 20px;
                }
                
                .portfolio-metric {
                    text-align: center;
                    padding: 15px;
                    background: rgba(255,255,255,0.05);
                    border-radius: 10px;
                }
                
                .portfolio-value {
                    font-size: 1.5em;
                    font-weight: 700;
                    color: #10b981;
                }
                
                .watchlist-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 15px;
                    background: rgba(255,255,255,0.03);
                    border-radius: 8px;
                    margin-bottom: 8px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    border: 1px solid transparent;
                }
                
                .watchlist-item:hover {
                    background: rgba(255,255,255,0.08);
                    border-color: rgba(102, 126, 234, 0.5);
                    transform: scale(1.02);
                }
                
                .stock-symbol {
                    font-weight: 600;
                    font-size: 1.1em;
                }
                
                .stock-price {
                    font-weight: 600;
                }
                
                .stock-change {
                    font-size: 0.9em;
                    padding: 2px 6px;
                    border-radius: 4px;
                    margin-left: 8px;
                }
                
                .change-positive {
                    background: rgba(16, 185, 129, 0.2);
                    color: #10b981;
                }
                
                .change-negative {
                    background: rgba(239, 68, 68, 0.2);
                    color: #ef4444;
                }
                
                .floating-controls {
                    position: fixed;
                    bottom: 30px;
                    right: 30px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    z-index: 1000;
                }
                
                .floating-btn {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    border: none;
                    color: #fff;
                    font-size: 1.2em;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
                    transition: all 0.3s ease;
                }
                
                .floating-btn:hover {
                    transform: scale(1.1) rotate(5deg);
                    box-shadow: 0 6px 25px rgba(102, 126, 234, 0.6);
                }
                
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.8);
                    backdrop-filter: blur(10px);
                    display: none;
                    align-items: center;
                    justify-content: center;
                    z-index: 2000;
                }
                
                .modal-content {
                    background: linear-gradient(135deg, #2a2a3e 0%, #3a3a54 100%);
                    border-radius: 20px;
                    padding: 30px;
                    max-width: 600px;
                    width: 90%;
                    border: 1px solid rgba(255,255,255,0.2);
                    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
                }
                
                .loading-spinner {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid rgba(255,255,255,0.3);
                    border-radius: 50%;
                    border-top-color: #667eea;
                    animation: spin 1s ease-in-out infinite;
                }
                
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                
                .connection-status {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 8px 15px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 600;
                    z-index: 1001;
                    transition: all 0.3s ease;
                }
                
                .connected {
                    background: rgba(16, 185, 129, 0.2);
                    color: #10b981;
                    border: 1px solid rgba(16, 185, 129, 0.3);
                }
                
                .disconnected {
                    background: rgba(239, 68, 68, 0.2);
                    color: #ef4444;
                    border: 1px solid rgba(239, 68, 68, 0.3);
                }
                
                @media (max-width: 1200px) {
                    .dashboard-container {
                        grid-template-columns: 1fr;
                        gap: 20px;
                    }
                    
                    .sidebar {
                        order: -1;
                    }
                }
                
                @media (max-width: 768px) {
                    .header-content {
                        flex-direction: column;
                        gap: 15px;
                    }
                    
                    .status-indicators {
                        flex-wrap: wrap;
                        justify-content: center;
                    }
                    
                    .market-overview-grid {
                        grid-template-columns: 1fr 1fr;
                    }
                    
                    .floating-controls {
                        bottom: 20px;
                        right: 20px;
                    }
                }
                
                /* Additional animations and effects */
                .glow-effect {
                    position: relative;
                }
                
                .glow-effect::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: linear-gradient(45deg, transparent, rgba(102, 126, 234, 0.1), transparent);
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                    pointer-events: none;
                }
                
                .glow-effect:hover::after {
                    opacity: 1;
                }
            </style>
        </head>
        <body>
            <div class="connection-status connected" id="connectionStatus">
                <i class="fas fa-wifi"></i> Real-time Connected
            </div>
            
            <header class="premium-header">
                <div class="header-content">
                    <div class="premium-logo">
                        <i class="fas fa-crown"></i>
                        Market Analysis Pro
                    </div>
                    
                    <div class="status-indicators">
                        <div class="status-indicator">
                            <div class="status-dot status-live"></div>
                            Live Market Data
                        </div>
                        <div class="status-indicator">
                            <div class="status-dot status-processing"></div>
                            AI Processing
                        </div>
                        <div class="status-indicator">
                            <div class="status-dot status-alert"></div>
                            3 Active Alerts
                        </div>
                    </div>
                </div>
            </header>
            
            <div class="dashboard-container">
                <main class="main-content">
                    <!-- Market Overview -->
                    <div class="premium-card glow-effect">
                        <div class="card-header">
                            <h2 class="card-title">
                                <i class="fas fa-chart-line"></i>
                                Market Overview
                            </h2>
                            <div class="card-actions">
                                <button class="action-btn" onclick="refreshMarketData()">
                                    <i class="fas fa-sync-alt"></i>
                                </button>
                                <button class="action-btn" onclick="exportData()">
                                    <i class="fas fa-download"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="market-overview-grid">
                            <div class="metric-card">
                                <div class="metric-value">$175.25</div>
                                <div class="metric-label">AAPL</div>
                                <div class="metric-change positive">+2.4%</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">4,587</div>
                                <div class="metric-label">S&P 500</div>
                                <div class="metric-change positive">+0.8%</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">$2.8T</div>
                                <div class="metric-label">Market Cap</div>
                                <div class="metric-change positive">+1.2%</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">28.5</div>
                                <div class="metric-label">VIX</div>
                                <div class="metric-change negative">-3.2%</div>
                            </div>
                        </div>
                        
                        <div class="chart-container" id="marketChart">
                            <!-- Market chart will be rendered here -->
                        </div>
                    </div>
                    
                    <!-- Advanced Analytics -->
                    <div class="premium-card glow-effect">
                        <div class="card-header">
                            <h2 class="card-title">
                                <i class="fas fa-brain"></i>
                                AI Analysis Dashboard
                            </h2>
                            <div class="card-actions">
                                <button class="action-btn" onclick="runAIAnalysis()">
                                    <i class="fas fa-play"></i> Run Analysis
                                </button>
                                <button class="action-btn" onclick="viewDetails()">
                                    <i class="fas fa-expand"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="chart-container" id="aiAnalysisChart">
                            <!-- AI analysis visualization will be rendered here -->
                        </div>
                    </div>
                    
                    <!-- Sector Heat Map -->
                    <div class="premium-card glow-effect">
                        <div class="card-header">
                            <h2 class="card-title">
                                <i class="fas fa-fire"></i>
                                Sector Performance Heat Map
                            </h2>
                        </div>
                        
                        <div class="heatmap-container" id="sectorHeatmap">
                            <!-- Sector heatmap will be generated here -->
                        </div>
                    </div>
                </main>
                
                <aside class="sidebar">
                    <!-- Real-time Alerts -->
                    <div class="premium-card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-bell"></i>
                                Live Alerts
                            </h3>
                        </div>
                        
                        <div class="alerts-container" id="alertsContainer">
                            <div class="alert-item alert-critical">
                                <div class="alert-icon">
                                    <i class="fas fa-exclamation-triangle"></i>
                                </div>
                                <div class="alert-content">
                                    <div class="alert-title">Breakout Alert: AAPL</div>
                                    <div class="alert-time">2 minutes ago</div>
                                </div>
                            </div>
                            
                            <div class="alert-item alert-warning">
                                <div class="alert-icon">
                                    <i class="fas fa-chart-line"></i>
                                </div>
                                <div class="alert-content">
                                    <div class="alert-title">Volume Spike: MSFT</div>
                                    <div class="alert-time">5 minutes ago</div>
                                </div>
                            </div>
                            
                            <div class="alert-item alert-info">
                                <div class="alert-icon">
                                    <i class="fas fa-info-circle"></i>
                                </div>
                                <div class="alert-content">
                                    <div class="alert-title">Earnings Today: GOOGL</div>
                                    <div class="alert-time">8 minutes ago</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Portfolio Monitor -->
                    <div class="premium-card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-briefcase"></i>
                                Portfolio Monitor
                            </h3>
                        </div>
                        
                        <div class="portfolio-summary">
                            <div class="portfolio-metric">
                                <div class="portfolio-value">$1.2M</div>
                                <div class="metric-label">Total Value</div>
                            </div>
                            <div class="portfolio-metric">
                                <div class="portfolio-value change-positive">+12.8%</div>
                                <div class="metric-label">Today's P&L</div>
                            </div>
                        </div>
                        
                        <div class="chart-container" id="portfolioChart" style="height: 200px;">
                            <!-- Portfolio performance chart -->
                        </div>
                    </div>
                    
                    <!-- Watchlist -->
                    <div class="premium-card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-eye"></i>
                                Smart Watchlist
                            </h3>
                            <div class="card-actions">
                                <button class="action-btn" onclick="addToWatchlist()">
                                    <i class="fas fa-plus"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="watchlist-container" id="watchlistContainer">
                            <div class="watchlist-item" onclick="selectStock('AAPL')">
                                <div>
                                    <div class="stock-symbol">AAPL</div>
                                    <div class="stock-price">$175.25</div>
                                </div>
                                <div class="stock-change change-positive">+2.4%</div>
                            </div>
                            
                            <div class="watchlist-item" onclick="selectStock('MSFT')">
                                <div>
                                    <div class="stock-symbol">MSFT</div>
                                    <div class="stock-price">$420.50</div>
                                </div>
                                <div class="stock-change change-positive">+1.8%</div>
                            </div>
                            
                            <div class="watchlist-item" onclick="selectStock('GOOGL')">
                                <div>
                                    <div class="stock-symbol">GOOGL</div>
                                    <div class="stock-price">$142.85</div>
                                </div>
                                <div class="stock-change change-negative">-0.5%</div>
                            </div>
                        </div>
                    </div>
                </aside>
            </div>
            
            <!-- Floating Controls -->
            <div class="floating-controls">
                <button class="floating-btn" onclick="openScreener()" title="Stock Screener">
                    <i class="fas fa-filter"></i>
                </button>
                <button class="floating-btn" onclick="openBacktester()" title="Backtester">
                    <i class="fas fa-history"></i>
                </button>
                <button class="floating-btn" onclick="openSettings()" title="Settings">
                    <i class="fas fa-cog"></i>
                </button>
            </div>
            
            <!-- Modal Overlay -->
            <div class="modal-overlay" id="modalOverlay">
                <div class="modal-content">
                    <h2 id="modalTitle">Loading...</h2>
                    <div id="modalContent">
                        <div class="loading-spinner"></div>
                        <p>Please wait while we process your request...</p>
                    </div>
                </div>
            </div>
            
            <script>
                // WebSocket connection for real-time data
                let ws = null;
                let reconnectAttempts = 0;
                const maxReconnectAttempts = 5;
                
                function initWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws`;
                    
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function(event) {
                        console.log('WebSocket connected');
                        updateConnectionStatus(true);
                        reconnectAttempts = 0;
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        handleRealTimeUpdate(data);
                    };
                    
                    ws.onclose = function(event) {
                        console.log('WebSocket disconnected');
                        updateConnectionStatus(false);
                        
                        if (reconnectAttempts < maxReconnectAttempts) {
                            setTimeout(() => {
                                reconnectAttempts++;
                                initWebSocket();
                            }, 3000 * reconnectAttempts);
                        }
                    };
                    
                    ws.onerror = function(error) {
                        console.error('WebSocket error:', error);
                    };
                }
                
                function updateConnectionStatus(connected) {
                    const statusEl = document.getElementById('connectionStatus');
                    if (connected) {
                        statusEl.className = 'connection-status connected';
                        statusEl.innerHTML = '<i class="fas fa-wifi"></i> Real-time Connected';
                    } else {
                        statusEl.className = 'connection-status disconnected';
                        statusEl.innerHTML = '<i class="fas fa-wifi-slash"></i> Reconnecting...';
                    }
                }
                
                function handleRealTimeUpdate(data) {
                    switch(data.type) {
                        case 'price_update':
                            updatePriceData(data);
                            break;
                        case 'alert':
                            addAlert(data);
                            break;
                        case 'analysis_complete':
                            updateAnalysis(data);
                            break;
                        case 'market_data':
                            updateMarketOverview(data);
                            break;
                    }
                }
                
                function updatePriceData(data) {
                    // Update price displays in real-time
                    const elements = document.querySelectorAll(`[data-symbol="${data.symbol}"]`);
                    elements.forEach(el => {
                        el.textContent = `$${data.price.toFixed(2)}`;
                    });
                }
                
                function addAlert(data) {
                    const alertsContainer = document.getElementById('alertsContainer');
                    const alertEl = document.createElement('div');
                    alertEl.className = `alert-item alert-${data.severity}`;
                    alertEl.innerHTML = `
                        <div class="alert-icon">
                            <i class="fas fa-${data.icon}"></i>
                        </div>
                        <div class="alert-content">
                            <div class="alert-title">${data.title}</div>
                            <div class="alert-time">Just now</div>
                        </div>
                    `;
                    alertsContainer.insertBefore(alertEl, alertsContainer.firstChild);
                    
                    // Remove old alerts (keep only 5)
                    while (alertsContainer.children.length > 5) {
                        alertsContainer.removeChild(alertsContainer.lastChild);
                    }
                }
                
                // Chart initialization
                function initializeCharts() {
                    // Market Overview Chart
                    initMarketChart();
                    
                    // AI Analysis Chart
                    initAIAnalysisChart();
                    
                    // Portfolio Chart
                    initPortfolioChart();
                    
                    // Sector Heatmap
                    initSectorHeatmap();
                }
                
                function initMarketChart() {
                    const ctx = document.getElementById('marketChart');
                    
                    // Sample data for demonstration
                    const data = {
                        labels: ['9:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00'],
                        datasets: [{
                            label: 'AAPL Price',
                            data: [172.5, 173.2, 174.1, 173.8, 174.5, 175.2, 175.8, 175.3, 175.9, 175.1, 175.6, 175.25],
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }]
                    };
                    
                    // Use Plotly for advanced charting
                    const plotData = [{
                        x: data.labels,
                        y: data.datasets[0].data,
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: {color: '#667eea', width: 2},
                        marker: {color: '#667eea', size: 6},
                        fill: 'tonexty',
                        fillcolor: 'rgba(102, 126, 234, 0.1)'
                    }];
                    
                    const layout = {
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        font: {color: '#ffffff'},
                        xaxis: {color: '#ffffff', gridcolor: 'rgba(255,255,255,0.1)'},
                        yaxis: {color: '#ffffff', gridcolor: 'rgba(255,255,255,0.1)'},
                        margin: {l: 50, r: 20, t: 20, b: 40},
                        showlegend: false
                    };
                    
                    Plotly.newPlot('marketChart', plotData, layout, {responsive: true});
                }
                
                function initAIAnalysisChart() {
                    // Advanced AI analysis visualization
                    const data = {
                        technical: 85,
                        fundamental: 78,
                        sentiment: 82,
                        momentum: 76,
                        risk: 68
                    };
                    
                    const plotData = [{
                        type: 'scatterpolar',
                        r: Object.values(data),
                        theta: Object.keys(data).map(k => k.charAt(0).toUpperCase() + k.slice(1)),
                        fill: 'toself',
                        fillcolor: 'rgba(102, 126, 234, 0.3)',
                        line: {color: '#667eea', width: 2},
                        marker: {color: '#667eea', size: 8}
                    }];
                    
                    const layout = {
                        polar: {
                            radialaxis: {
                                visible: true,
                                range: [0, 100],
                                color: '#ffffff'
                            },
                            angularaxis: {
                                color: '#ffffff'
                            }
                        },
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        font: {color: '#ffffff'},
                        margin: {l: 50, r: 50, t: 50, b: 50},
                        showlegend: false
                    };
                    
                    Plotly.newPlot('aiAnalysisChart', plotData, layout, {responsive: true});
                }
                
                function initPortfolioChart() {
                    // Portfolio performance chart
                    const data = [100, 102, 105, 103, 108, 112, 110, 115, 118, 120];
                    const labels = Array.from({length: 10}, (_, i) => `Day ${i + 1}`);
                    
                    const plotData = [{
                        x: labels,
                        y: data,
                        type: 'scatter',
                        mode: 'lines',
                        line: {color: '#10b981', width: 2},
                        fill: 'tonexty',
                        fillcolor: 'rgba(16, 185, 129, 0.1)'
                    }];
                    
                    const layout = {
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        font: {color: '#ffffff', size: 10},
                        xaxis: {color: '#ffffff', gridcolor: 'rgba(255,255,255,0.1)', showticklabels: false},
                        yaxis: {color: '#ffffff', gridcolor: 'rgba(255,255,255,0.1)'},
                        margin: {l: 30, r: 10, t: 10, b: 20},
                        showlegend: false
                    };
                    
                    Plotly.newPlot('portfolioChart', plotData, layout, {responsive: true});
                }
                
                function initSectorHeatmap() {
                    const sectors = [
                        'Technology', 'Healthcare', 'Financials', 'Consumer Disc.', 'Communication',
                        'Industrials', 'Consumer Staples', 'Energy', 'Utilities', 'Real Estate',
                        'Materials', 'Aerospace', 'Biotechnology', 'Gaming', 'Renewable'
                    ];
                    
                    const performance = [2.4, 1.8, -0.5, 1.2, 0.8, 1.5, 0.3, -1.2, 0.5, 0.9, 1.1, 2.1, 3.2, -0.8, 4.5];
                    
                    const heatmapContainer = document.getElementById('sectorHeatmap');
                    heatmapContainer.innerHTML = '';
                    
                    sectors.forEach((sector, index) => {
                        const cell = document.createElement('div');
                        cell.className = 'heatmap-cell';
                        cell.textContent = `${sector.split(' ')[0]} ${performance[index]}%`;
                        cell.title = `${sector}: ${performance[index]}%`;
                        
                        const perf = performance[index];
                        if (perf > 2) {
                            cell.style.backgroundColor = '#10b981';
                        } else if (perf > 0) {
                            cell.style.backgroundColor = '#059669';
                        } else if (perf > -1) {
                            cell.style.backgroundColor = '#dc2626';
                        } else {
                            cell.style.backgroundColor = '#991b1b';
                        }
                        
                        heatmapContainer.appendChild(cell);
                    });
                }
                
                // Interactive Functions
                function refreshMarketData() {
                    const btn = event.target.closest('.action-btn');
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    
                    setTimeout(() => {
                        btn.innerHTML = '<i class="fas fa-sync-alt"></i>';
                        // Simulate data refresh
                        addAlert({
                            type: 'alert',
                            severity: 'info',
                            icon: 'sync-alt',
                            title: 'Market data refreshed',
                        });
                    }, 2000);
                }
                
                function runAIAnalysis() {
                    showModal('AI Analysis Running', 'Running comprehensive AI analysis...');
                    
                    setTimeout(() => {
                        hideModal();
                        addAlert({
                            type: 'alert',
                            severity: 'success',
                            icon: 'brain',
                            title: 'AI Analysis Complete',
                        });
                    }, 3000);
                }
                
                function selectStock(symbol) {
                    console.log(`Selected stock: ${symbol}`);
                    // Implement stock selection logic
                }
                
                function addToWatchlist() {
                    showModal('Add to Watchlist', 'Enter stock symbol to add to watchlist');
                }
                
                function openScreener() {
                    showModal('Stock Screener', 'Opening advanced stock screener...');
                }
                
                function openBacktester() {
                    showModal('Strategy Backtester', 'Loading backtesting interface...');
                }
                
                function openSettings() {
                    showModal('Settings', 'Configure your dashboard preferences...');
                }
                
                function showModal(title, content) {
                    document.getElementById('modalTitle').textContent = title;
                    document.getElementById('modalContent').innerHTML = `<p>${content}</p>`;
                    document.getElementById('modalOverlay').style.display = 'flex';
                }
                
                function hideModal() {
                    document.getElementById('modalOverlay').style.display = 'none';
                }
                
                // Close modal on overlay click
                document.getElementById('modalOverlay').addEventListener('click', function(e) {
                    if (e.target === this) {
                        hideModal();
                    }
                });
                
                // Initialize everything when page loads
                document.addEventListener('DOMContentLoaded', function() {
                    initializeCharts();
                    initWebSocket();
                    
                    // Simulate some real-time updates
                    setInterval(() => {
                        if (Math.random() > 0.7) {
                            const alerts = [
                                {severity: 'info', icon: 'chart-line', title: 'Price Alert: AAPL above $175'},
                                {severity: 'warning', icon: 'exclamation-triangle', title: 'Volume spike detected'},
                                {severity: 'success', icon: 'check-circle', title: 'Target reached: MSFT'},
                            ];
                            const randomAlert = alerts[Math.floor(Math.random() * alerts.length)];
                            addAlert(randomAlert);
                        }
                    }, 10000);
                });
            </script>
        </body>
        </html>
        """
    
    async def connect_websocket(self, websocket: WebSocket):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send initial data
        await websocket.send_json({
            "type": "connection_established",
            "message": "Welcome to Market Analysis Pro",
            "timestamp": datetime.now().isoformat()
        })
    
    async def disconnect_websocket(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if self.active_connections:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for conn in disconnected:
                await self.disconnect_websocket(conn)
    
    async def send_price_update(self, symbol: str, price: float, change: float):
        """Send real-time price update"""
        await self.broadcast_to_all({
            "type": "price_update",
            "symbol": symbol,
            "price": price,
            "change": change,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_alert(self, alert_type: str, severity: str, title: str, message: str):
        """Send real-time alert"""
        await self.broadcast_to_all({
            "type": "alert",
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "message": message,
            "icon": self._get_alert_icon(alert_type),
            "timestamp": datetime.now().isoformat()
        })
    
    def _get_alert_icon(self, alert_type: str) -> str:
        """Get appropriate icon for alert type"""
        icon_map = {
            "breakout": "chart-line-up",
            "volume": "volume-high",
            "earnings": "calendar-alt",
            "news": "newspaper",
            "technical": "chart-area",
            "fundamental": "building"
        }
        return icon_map.get(alert_type, "bell")

class RealTimeAlertEngine:
    """Real-time alert system with sophisticated triggering logic"""
    
    def __init__(self):
        self.alert_rules = []
        self.active_alerts = []
        
    async def add_alert_rule(self, rule: Dict[str, Any]):
        """Add a new alert rule"""
        self.alert_rules.append({
            "id": len(self.alert_rules) + 1,
            "rule": rule,
            "created": datetime.now(),
            "triggered_count": 0,
            "last_triggered": None
        })
    
    async def check_alerts(self, market_data: Dict[str, Any]):
        """Check all alert rules against current market data"""
        triggered_alerts = []
        
        for rule in self.alert_rules:
            if await self._evaluate_rule(rule["rule"], market_data):
                alert = {
                    "rule_id": rule["id"],
                    "type": rule["rule"]["type"],
                    "severity": rule["rule"]["severity"],
                    "title": rule["rule"]["title"],
                    "message": rule["rule"]["message"],
                    "symbol": rule["rule"].get("symbol"),
                    "triggered_at": datetime.now()
                }
                
                triggered_alerts.append(alert)
                rule["triggered_count"] += 1
                rule["last_triggered"] = datetime.now()
        
        return triggered_alerts
    
    async def _evaluate_rule(self, rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate if a rule should trigger an alert"""
        try:
            rule_type = rule["type"]
            
            if rule_type == "price_breakout":
                return await self._check_price_breakout(rule, data)
            elif rule_type == "volume_spike":
                return await self._check_volume_spike(rule, data)
            elif rule_type == "technical_signal":
                return await self._check_technical_signal(rule, data)
            elif rule_type == "news_sentiment":
                return await self._check_news_sentiment(rule, data)
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating alert rule: {e}")
            return False
    
    async def _check_price_breakout(self, rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Check for price breakout conditions"""
        symbol = rule["symbol"]
        threshold = rule["threshold"]
        direction = rule["direction"]  # "above" or "below"
        
        current_price = data.get("prices", {}).get(symbol, 0)
        
        if direction == "above":
            return current_price > threshold
        else:
            return current_price < threshold
    
    async def _check_volume_spike(self, rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Check for volume spike conditions"""
        symbol = rule["symbol"]
        multiplier = rule["multiplier"]
        
        current_volume = data.get("volumes", {}).get(symbol, 0)
        avg_volume = data.get("avg_volumes", {}).get(symbol, 0)
        
        return current_volume > (avg_volume * multiplier)
    
    async def _check_technical_signal(self, rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Check for technical analysis signals"""
        # Implement technical signal checking logic
        return False  # Simplified for now
    
    async def _check_news_sentiment(self, rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Check for news sentiment conditions"""
        # Implement news sentiment checking logic
        return False  # Simplified for now

class AdvancedVisualizationEngine:
    """Advanced visualization engine for complex financial data"""
    
    async def generate_advanced_chart_config(self, chart_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate advanced chart configurations"""
        try:
            if chart_type == "candlestick":
                return await self._generate_candlestick_config(data)
            elif chart_type == "heatmap":
                return await self._generate_heatmap_config(data)
            elif chart_type == "network":
                return await self._generate_network_config(data)
            elif chart_type == "3d_surface":
                return await self._generate_3d_surface_config(data)
            elif chart_type == "correlation_matrix":
                return await self._generate_correlation_matrix_config(data)
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error generating chart config: {e}")
            return {}
    
    async def _generate_candlestick_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate candlestick chart configuration"""
        return {
            "type": "candlestick",
            "data": {
                "x": data.get("timestamps", []),
                "open": data.get("open", []),
                "high": data.get("high", []),
                "low": data.get("low", []),
                "close": data.get("close", [])
            },
            "layout": {
                "title": "Price Action",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Price"},
                "plot_bgcolor": "rgba(0,0,0,0)",
                "paper_bgcolor": "rgba(0,0,0,0)"
            }
        }
    
    async def _generate_heatmap_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate heatmap configuration"""
        return {
            "type": "heatmap",
            "data": {
                "z": data.get("values", []),
                "x": data.get("x_labels", []),
                "y": data.get("y_labels", []),
                "colorscale": "RdYlGn"
            },
            "layout": {
                "title": "Performance Heatmap",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "paper_bgcolor": "rgba(0,0,0,0)"
            }
        }
    
    async def _generate_network_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate network visualization configuration"""
        return {
            "type": "network",
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
            "layout": {
                "title": "Market Network",
                "showlegend": False
            }
        }
    
    async def _generate_3d_surface_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate 3D surface plot configuration"""
        return {
            "type": "surface",
            "data": {
                "z": data.get("surface_data", []),
                "colorscale": "Viridis"
            },
            "layout": {
                "title": "Risk Surface",
                "scene": {
                    "xaxis": {"title": "Time"},
                    "yaxis": {"title": "Strike"},
                    "zaxis": {"title": "Implied Volatility"}
                }
            }
        }
    
    async def _generate_correlation_matrix_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate correlation matrix configuration"""
        return {
            "type": "heatmap",
            "data": {
                "z": data.get("correlation_matrix", []),
                "x": data.get("symbols", []),
                "y": data.get("symbols", []),
                "colorscale": "RdBu",
                "zmin": -1,
                "zmax": 1
            },
            "layout": {
                "title": "Asset Correlation Matrix",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "paper_bgcolor": "rgba(0,0,0,0)"
            }
        }

class StreamingDataEngine:
    """Real-time data streaming engine"""
    
    def __init__(self):
        self.data_streams = {}
        self.subscribers = {}
        
    async def start_data_stream(self, stream_id: str, data_source: str, update_interval: int = 1000):
        """Start a new data stream"""
        self.data_streams[stream_id] = {
            "source": data_source,
            "interval": update_interval,
            "active": True,
            "last_update": datetime.now()
        }
        
        # Start background task for data streaming
        asyncio.create_task(self._stream_data(stream_id))
    
    async def _stream_data(self, stream_id: str):
        """Background task for streaming data"""
        while self.data_streams.get(stream_id, {}).get("active", False):
            try:
                # Simulate data generation
                data = await self._generate_streaming_data(stream_id)
                
                # Send to subscribers
                if stream_id in self.subscribers:
                    for subscriber in self.subscribers[stream_id]:
                        await subscriber.send_json({
                            "stream_id": stream_id,
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        })
                
                # Wait for next update
                interval = self.data_streams[stream_id]["interval"] / 1000
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in data stream {stream_id}: {e}")
                await asyncio.sleep(1)
    
    async def _generate_streaming_data(self, stream_id: str) -> Dict[str, Any]:
        """Generate streaming data based on stream type"""
        import random
        
        if "price" in stream_id:
            return {
                "symbol": "AAPL",
                "price": 175.25 + random.uniform(-1, 1),
                "volume": random.randint(1000000, 5000000),
                "timestamp": datetime.now().isoformat()
            }
        elif "market" in stream_id:
            return {
                "spy": 458.7 + random.uniform(-2, 2),
                "qqq": 375.2 + random.uniform(-1.5, 1.5),
                "vix": 18.5 + random.uniform(-1, 1)
            }
        else:
            return {"value": random.uniform(0, 100)}
    
    async def subscribe_to_stream(self, stream_id: str, websocket):
        """Subscribe a WebSocket to a data stream"""
        if stream_id not in self.subscribers:
            self.subscribers[stream_id] = []
        
        self.subscribers[stream_id].append(websocket)
    
    async def unsubscribe_from_stream(self, stream_id: str, websocket):
        """Unsubscribe a WebSocket from a data stream"""
        if stream_id in self.subscribers:
            if websocket in self.subscribers[stream_id]:
                self.subscribers[stream_id].remove(websocket)

class PortfolioMonitoringEngine:
    """Advanced portfolio monitoring and analytics"""
    
    def __init__(self):
        self.portfolios = {}
        self.monitoring_active = {}
        
    async def add_portfolio(self, portfolio_id: str, holdings: Dict[str, float], initial_value: float):
        """Add a portfolio for monitoring"""
        self.portfolios[portfolio_id] = {
            "holdings": holdings,
            "initial_value": initial_value,
            "created": datetime.now(),
            "performance_history": [],
            "alerts": []
        }
        
        self.monitoring_active[portfolio_id] = True
        asyncio.create_task(self._monitor_portfolio(portfolio_id))
    
    async def _monitor_portfolio(self, portfolio_id: str):
        """Background task for portfolio monitoring"""
        while self.monitoring_active.get(portfolio_id, False):
            try:
                portfolio = self.portfolios[portfolio_id]
                
                # Calculate current portfolio value
                current_value = await self._calculate_portfolio_value(portfolio["holdings"])
                
                # Calculate performance metrics
                performance = await self._calculate_performance_metrics(
                    portfolio_id, 
                    current_value, 
                    portfolio["initial_value"]
                )
                
                # Store performance data
                portfolio["performance_history"].append({
                    "timestamp": datetime.now(),
                    "value": current_value,
                    "return": performance["total_return"],
                    "daily_return": performance["daily_return"]
                })
                
                # Check for alert conditions
                await self._check_portfolio_alerts(portfolio_id, performance)
                
                # Wait for next update (5 minutes)
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error monitoring portfolio {portfolio_id}: {e}")
                await asyncio.sleep(60)
    
    async def _calculate_portfolio_value(self, holdings: Dict[str, float]) -> float:
        """Calculate current portfolio value"""
        # Simulate portfolio value calculation
        import random
        base_value = sum(holdings.values()) * 100  # Assume $100 per share average
        return base_value * (1 + random.uniform(-0.05, 0.05))
    
    async def _calculate_performance_metrics(self, portfolio_id: str, current_value: float, initial_value: float) -> Dict[str, Any]:
        """Calculate portfolio performance metrics"""
        total_return = (current_value - initial_value) / initial_value
        
        # Get previous day value for daily return calculation
        portfolio = self.portfolios[portfolio_id]
        history = portfolio["performance_history"]
        
        if history:
            previous_value = history[-1]["value"]
            daily_return = (current_value - previous_value) / previous_value
        else:
            daily_return = 0
        
        return {
            "total_return": total_return,
            "daily_return": daily_return,
            "current_value": current_value,
            "unrealized_pnl": current_value - initial_value
        }
    
    async def _check_portfolio_alerts(self, portfolio_id: str, performance: Dict[str, Any]):
        """Check for portfolio alert conditions"""
        portfolio = self.portfolios[portfolio_id]
        
        # Check for significant moves
        if abs(performance["daily_return"]) > 0.05:  # 5% daily move
            alert = {
                "type": "large_move",
                "portfolio_id": portfolio_id,
                "daily_return": performance["daily_return"],
                "timestamp": datetime.now()
            }
            portfolio["alerts"].append(alert)

# Factory function
def create_premium_dashboard() -> PremiumDashboardEngine:
    """Create and return premium dashboard engine"""
    return PremiumDashboardEngine()