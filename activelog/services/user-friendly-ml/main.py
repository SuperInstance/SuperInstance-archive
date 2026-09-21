#!/usr/bin/env python3
"""
User-Friendly ML Interface
Makes machine learning accessible to non-technical users through natural language,
visual interfaces, and guided workflows
"""

import asyncio
import json
import logging
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dataclasses import dataclass
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="User-Friendly ML Interface", version="1.0.0")

# Static files and templates
static_path = Path(__file__).parent / "static"
templates_path = Path(__file__).parent / "templates"
static_path.mkdir(exist_ok=True)
templates_path.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
templates = Jinja2Templates(directory=str(templates_path))

class QueryType(str, Enum):
    PREDICTION = "prediction"
    ANALYSIS = "analysis"
    COMPARISON = "comparison"
    TREND = "trend"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"
    MODEL_BUILD = "model_build"
    WORKFLOW = "workflow"
    PLAYGROUND = "playground"
    VISUALIZATION = "visualization"

class DataType(str, Enum):
    TRADING = "trading"
    USERS = "users"
    REVENUE = "revenue"
    SYSTEM = "system"
    PERFORMANCE = "performance"

@dataclass
class UserQuery:
    query_id: str
    user_question: str
    query_type: QueryType
    data_type: DataType
    parameters: Dict[str, Any]
    created_at: datetime

@dataclass
class MLResponse:
    response_id: str
    query_id: str
    answer: str
    visualizations: List[Dict[str, Any]]
    confidence: float
    recommendations: List[str]
    technical_details: Optional[Dict[str, Any]]
    created_at: datetime

class NaturalLanguageQuery(BaseModel):
    question: str
    context: Optional[str] = None
    include_technical_details: bool = False

class UserFriendlyML:
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "user_friendly_ml.db"
        self.data_path = Path(__file__).parent / "data"
        
        # Create directories
        self.db_path.parent.mkdir(exist_ok=True)
        self.data_path.mkdir(exist_ok=True)
        
        self._init_database()
        self._init_templates()
        
        # Natural language patterns for different query types
        self.query_patterns = {
            QueryType.PREDICTION: [
                r"predict|forecast|expect|will.*be|future|next|estimate",
                r"how much|how many|what will|when will",
            ],
            QueryType.ANALYSIS: [
                r"analyze|analysis|examine|study|investigate|look at",
                r"what is|what are|how is|explain",
            ],
            QueryType.COMPARISON: [
                r"compare|comparison|versus|vs|difference|better|worse",
                r"which is|what's the difference",
            ],
            QueryType.TREND: [
                r"trend|trending|pattern|over time|growing|declining",
                r"increase|decrease|rise|fall|change",
            ],
            QueryType.ANOMALY: [
                r"anomaly|unusual|strange|outlier|abnormal|irregular",
                r"what's wrong|problem|issue|alert",
            ],
            QueryType.RECOMMENDATION: [
                r"recommend|suggestion|advice|should|what to do",
                r"how to improve|optimize|fix|enhance",
            ],
            QueryType.MODEL_BUILD: [
                r"train.*model|build.*model|create.*model|make.*model",
                r"ml.*model|machine learning|train.*algorithm|build.*predictor",
                r"automl|auto.*train|automatic.*model|easy.*model|simple.*model",
                r"teach.*computer|smart.*robot|ai.*helper|magic.*predictor",
            ],
            QueryType.PLAYGROUND: [
                r"experiment|try.*out|play.*with|test.*model|playground|fun.*ml",
                r"sample.*data|demo.*data|practice.*ml|learn.*ml|explore",
                r"game.*ml|fun.*data|kids.*ml|simple.*experiment|easy.*try",
            ]
        }
        
        self.data_patterns = {
            DataType.TRADING: [
                r"trading|trade|order|buy|sell|volume|price|profit|loss",
                r"btc|bitcoin|crypto|currency|market|exchange",
            ],
            DataType.USERS: [
                r"user|customer|account|registration|login|growth|retention",
                r"people|visitor|client|subscriber",
            ],
            DataType.REVENUE: [
                r"revenue|income|profit|money|earnings|financial|sales",
                r"cost|expense|budget|roi|return",
            ],
            DataType.SYSTEM: [
                r"system|server|cpu|memory|disk|network|performance|load",
                r"infrastructure|resource|capacity|utilization",
            ],
            DataType.PERFORMANCE: [
                r"performance|speed|latency|response|throughput|efficiency",
                r"fast|slow|optimize|improve|benchmark",
            ]
        }
        
        # Pre-built query templates
        self.query_templates = {
            "simple_prediction": {
                "title": "📈 Predict Future Values",
                "description": "Get predictions for trading, users, revenue, or system metrics",
                "examples": [
                    "What will our trading volume be next week?",
                    "How many new users will we get this month?",
                    "Predict revenue for the next quarter"
                ]
            },
            "trend_analysis": {
                "title": "📊 Analyze Trends",
                "description": "Understand patterns and trends in your data",
                "examples": [
                    "Show me the trend in user growth over the last 3 months",
                    "How is our trading performance changing over time?",
                    "What's the pattern in system resource usage?"
                ]
            },
            "anomaly_detection": {
                "title": "🚨 Find Anomalies",
                "description": "Detect unusual patterns or outliers in your data",
                "examples": [
                    "Are there any unusual trading patterns today?",
                    "Find anomalies in our system performance",
                    "What looks abnormal in our user behavior?"
                ]
            },
            "recommendations": {
                "title": "💡 Get Recommendations",
                "description": "Receive AI-powered suggestions and advice",
                "examples": [
                    "How can we improve our trading performance?",
                    "What should we do to reduce system costs?",
                    "Recommend ways to increase user retention"
                ]
            },
            "easy_model_training": {
                "title": "🎯 Train Models Easily",
                "description": "Create ML models with simple conversations",
                "examples": [
                    "I want to train a simple model to predict sales",
                    "Help me build an easy customer segmentation model",
                    "Can you automatically train a model for me?",
                    "Create a magic predictor for my business"
                ]
            },
            "fun_ml_playground": {
                "title": "🎮 Fun ML Playground",
                "description": "Explore machine learning with games and experiments",
                "examples": [
                    "Let me try ML with sample data",
                    "I want to play with machine learning",
                    "Show me a fun ML experiment",
                    "Can I explore AI in a simple way?"
                ]
            },
            "kids_ml_adventures": {
                "title": "🌟 ML Adventures for Kids",
                "description": "Learn ML through fun stories and simple experiments",
                "examples": [
                    "Teach me about smart robots",
                    "How do computers learn like humans?",
                    "Let's build an AI helper together",
                    "Show me magic with data"
                ]
            }
        }
        
    def _init_database(self):
        """Initialize SQLite database for user queries"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS user_queries (
                    query_id TEXT PRIMARY KEY,
                    user_question TEXT NOT NULL,
                    query_type TEXT,
                    data_type TEXT,
                    parameters JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_session TEXT
                );
                
                CREATE TABLE IF NOT EXISTS ml_responses (
                    response_id TEXT PRIMARY KEY,
                    query_id TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    visualizations JSON,
                    confidence REAL,
                    recommendations JSON,
                    technical_details JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES user_queries (query_id)
                );
                
                CREATE TABLE IF NOT EXISTS user_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    response_id TEXT NOT NULL,
                    rating INTEGER,
                    comments TEXT,
                    helpful BOOLEAN,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (response_id) REFERENCES ml_responses (response_id)
                );
                
                CREATE TABLE IF NOT EXISTS query_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_type TEXT,
                    data_type TEXT,
                    success_rate REAL,
                    avg_confidence REAL,
                    avg_response_time REAL,
                    usage_count INTEGER,
                    date DATE DEFAULT (date('now'))
                );
                
                CREATE TABLE IF NOT EXISTS user_models (
                    model_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    config JSON,
                    status TEXT DEFAULT 'training',
                    accuracy REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_trained DATETIME,
                    predictions_made INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    steps JSON,
                    current_step INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    config JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME
                );
                
                CREATE TABLE IF NOT EXISTS workflow_progress (
                    progress_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    step_number INTEGER,
                    step_name TEXT,
                    status TEXT DEFAULT 'pending',
                    data JSON,
                    completed_at DATETIME,
                    FOREIGN KEY (workflow_id) REFERENCES workflows (workflow_id)
                );
                
                CREATE TABLE IF NOT EXISTS ml_experiments (
                    experiment_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    dataset_config JSON,
                    model_config JSON,
                    results JSON,
                    visualizations JSON,
                    status TEXT DEFAULT 'running',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME
                );
                
                CREATE TABLE IF NOT EXISTS data_connections (
                    connection_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    config JSON,
                    schema_info JSON,
                    status TEXT DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME
                );
                
                CREATE TABLE IF NOT EXISTS model_comparisons (
                    comparison_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    model_ids JSON,
                    metrics JSON,
                    recommendations JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS collaboration_sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    participants JSON,
                    shared_resources JSON,
                    activity_log JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME
                );
            """)
            
    def _init_templates(self):
        """Initialize HTML templates for the web interface"""
        # Main dashboard template
        dashboard_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ActiveLog ML Assistant</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .main-content {
            padding: 40px;
        }
        
        .query-section {
            margin-bottom: 40px;
        }
        
        .query-input {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        #questionInput {
            flex: 1;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            transition: border-color 0.3s;
        }
        
        #questionInput:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .ask-btn {
            padding: 15px 30px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        
        .ask-btn:hover {
            transform: translateY(-2px);
        }
        
        .templates-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .template-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }
        
        .template-card:hover {
            transform: translateY(-5px);
            border-color: #667eea;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        
        .template-card h3 {
            color: #333;
            margin-bottom: 10px;
            font-size: 1.3rem;
        }
        
        .template-card p {
            color: #666;
            margin-bottom: 15px;
        }
        
        .example {
            background: #e9ecef;
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            font-style: italic;
            color: #495057;
            cursor: pointer;
        }
        
        .example:hover {
            background: #dee2e6;
        }
        
        .response-section {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 15px;
            display: none;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .answer {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }
        
        .recommendations {
            background: #e3f2fd;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .recommendations h4 {
            color: #1976d2;
            margin-bottom: 10px;
        }
        
        .recommendation-item {
            background: white;
            padding: 10px;
            margin: 8px 0;
            border-radius: 5px;
            border-left: 3px solid #2196f3;
        }
        
        .confidence-bar {
            background: #e0e0e0;
            height: 8px;
            border-radius: 4px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .confidence-fill {
            background: linear-gradient(45deg, #4caf50, #8bc34a);
            height: 100%;
            transition: width 0.5s ease;
        }
        
        .feedback-section {
            margin-top: 20px;
            text-align: center;
        }
        
        .feedback-btn {
            margin: 0 5px;
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .feedback-btn:hover {
            background: #f0f0f0;
        }
        
        .feedback-btn.positive {
            border-color: #4caf50;
            color: #4caf50;
        }
        
        .feedback-btn.negative {
            border-color: #f44336;
            color: #f44336;
        }
        
        .section {
            margin: 40px 0;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 15px;
            border: 1px solid #e9ecef;
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 10px;
            font-size: 1.8rem;
        }
        
        .section p {
            color: #666;
            margin-bottom: 20px;
            font-size: 1.1rem;
        }
        
        .model-template-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
            position: relative;
            overflow: hidden;
        }
        
        .model-template-card:hover {
            transform: translateY(-5px);
            border-color: #667eea;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        
        .model-template-card::before {
            content: attr(data-icon);
            font-size: 3rem;
            position: absolute;
            top: 15px;
            right: 20px;
            opacity: 0.1;
        }
        
        .workflow-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            padding: 25px;
            cursor: pointer;
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }
        
        .workflow-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 15px 35px rgba(102, 126, 234, 0.3);
        }
        
        .workflow-card .difficulty {
            background: rgba(255, 255, 255, 0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            display: inline-block;
            margin-bottom: 10px;
        }
        
        .workflow-card .time-estimate {
            background: rgba(255, 255, 255, 0.15);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            display: inline-block;
            margin-left: 8px;
        }
        
        .workflow-steps {
            margin-top: 15px;
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .workflow-steps li {
            margin: 5px 0;
        }
        
        .playground-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-top: 20px;
        }
        
        .dataset-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .dataset-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .dataset-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(240, 147, 251, 0.3);
        }
        
        .dataset-card h4 {
            margin-bottom: 8px;
            font-size: 1.2rem;
        }
        
        .dataset-card .dataset-stats {
            font-size: 0.9rem;
            opacity: 0.9;
            margin-top: 10px;
        }
        
        .playground-experiment {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-top: 25px;
            padding-top: 25px;
            border-top: 2px solid #e9ecef;
        }
        
        .experiment-controls, .experiment-results {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
        }
        
        .model-recommendations {
            margin-top: 15px;
        }
        
        .model-rec-card {
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .model-rec-card:hover {
            border-color: #667eea;
            transform: translateX(5px);
        }
        
        .model-rec-card.selected {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .confidence-badge {
            background: #4caf50;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            float: right;
        }
        
        .smart-recommendations {
            margin-top: 20px;
        }
        
        .recommendation-category {
            margin-bottom: 25px;
        }
        
        .recommendation-category h3 {
            margin-bottom: 15px;
            font-size: 1.3rem;
        }
        
        .recommendation-card {
            background: white;
            border-left: 4px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
            transition: all 0.3s;
        }
        
        .recommendation-card:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        .recommendation-card.urgent {
            border-left-color: #f44336;
            background: #fff5f5;
        }
        
        .recommendation-card.opportunity {
            border-left-color: #ff9800;
            background: #fff8f0;
        }
        
        .recommendation-card.insight {
            border-left-color: #4caf50;
            background: #f0fff4;
        }
        
        .recommendation-actions {
            margin-top: 15px;
        }
        
        .action-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            margin-right: 10px;
            font-size: 0.9rem;
            transition: all 0.3s;
        }
        
        .action-btn:hover {
            background: #5a67d8;
            transform: translateY(-1px);
        }
        
        .drop-zone {
            border: 3px dashed #ccc;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
            background: #fafafa;
        }
        
        .drop-zone:hover, .drop-zone.dragover {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .upload-icon {
            font-size: 3rem;
            margin-bottom: 15px;
        }
        
        .connected-data-list {
            margin-top: 25px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .data-connection-card {
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 15px;
            transition: all 0.3s;
        }
        
        .data-connection-card:hover {
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .connection-status {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-top: 10px;
        }
        
        .connection-status.connected {
            background: #4caf50;
            color: white;
        }
        
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .kpi-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #e9ecef;
        }
        
        .kpi-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .kpi-change {
            font-size: 0.9rem;
            margin-top: 5px;
        }
        
        .kpi-change.positive {
            color: #4caf50;
        }
        
        .kpi-change.negative {
            color: #f44336;
        }
        
        @media (max-width: 768px) {
            .query-input {
                flex-direction: column;
            }
            
            .templates-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .main-content {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ActiveLog ML Assistant</h1>
            <p>Ask questions about your data in plain English - no technical knowledge required!</p>
        </div>
        
        <div class="main-content">
            <div class="query-section">
                <div class="query-input">
                    <input type="text" id="questionInput" placeholder="Ask me anything about your trading, users, revenue, or system performance..." />
                    <button class="ask-btn" onclick="askQuestion()">Ask ML</button>
                </div>
                
                <div class="templates-grid">
                    {% for template_key, template in query_templates.items() %}
                    <div class="template-card" onclick="selectTemplate('{{ template_key }}')">
                        <h3>{{ template.title }}</h3>
                        <p>{{ template.description }}</p>
                        {% for example in template.examples %}
                        <div class="example" onclick="event.stopPropagation(); askSpecificQuestion('{{ example }}')">{{ example }}</div>
                        {% endfor %}
                    </div>
                    {% endfor %}
                </div>
                
                <!-- No-Code ML Tools Section -->
                <div class="section">
                    <h2>🛠️ No-Code ML Model Builder</h2>
                    <p>Create powerful machine learning models without writing code</p>
                    <div class="templates-grid" id="modelTemplatesGrid">
                        <!-- Model templates will be loaded dynamically -->
                    </div>
                </div>
                
                <!-- Guided Workflows Section -->
                <div class="section">
                    <h2>🎯 Guided ML Workflows</h2>
                    <p>Step-by-step guidance for common ML tasks</p>
                    <div class="templates-grid" id="workflowsGrid">
                        <!-- Workflows will be loaded dynamically -->
                    </div>
                </div>
                
                <!-- ML Playground Section -->
                <div class="section">
                    <h2>🧪 Interactive ML Playground</h2>
                    <p>Experiment with ML models using sample data - see results instantly!</p>
                    <div class="playground-container">
                        <div class="dataset-selector">
                            <h4>Choose Dataset:</h4>
                            <div id="datasetCards" class="dataset-cards">
                                <!-- Dataset cards will be loaded dynamically -->
                            </div>
                        </div>
                        <div id="playgroundExperiment" class="playground-experiment" style="display: none;">
                            <div class="experiment-controls">
                                <h4>🎛️ Model Configuration</h4>
                                <div id="modelRecommendations" class="model-recommendations">
                                    <!-- Smart model recommendations will appear here -->
                                </div>
                            </div>
                            <div class="experiment-results">
                                <h4>📊 Real-Time Results</h4>
                                <div id="playgroundVisualizations" class="playground-viz">
                                    <!-- Visualizations will appear here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Smart Recommendations Section -->
                <div class="section">
                    <h2>🧠 AI-Powered Recommendations</h2>
                    <p>Get intelligent suggestions to optimize your ML workflows</p>
                    <div id="smartRecommendations" class="smart-recommendations">
                        <!-- Smart recommendations will be loaded dynamically -->
                    </div>
                </div>
                
                <!-- Data Connections Section -->
                <div class="section">
                    <h2>🔗 Drag & Drop Data Connections</h2>
                    <p>Connect your data sources with simple drag and drop</p>
                    <div class="data-connections">
                        <div class="drop-zone" id="dataDropZone">
                            <div class="drop-zone-content">
                                <div class="upload-icon">📁</div>
                                <h3>Drop your data files here</h3>
                                <p>Or click to browse files</p>
                                <input type="file" id="fileInput" accept=".csv,.json,.xlsx" style="display: none;">
                            </div>
                        </div>
                        <div id="connectedData" class="connected-data-list">
                            <!-- Connected data sources will appear here -->
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="responseSection" class="response-section">
                <div id="loadingDiv" class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing your question and preparing insights...</p>
                </div>
                
                <div id="answerDiv" style="display: none;">
                    <div class="answer">
                        <h3>📊 Analysis Results</h3>
                        <div id="answerContent"></div>
                        <div class="confidence-bar">
                            <div id="confidenceFill" class="confidence-fill" style="width: 0%"></div>
                        </div>
                        <small id="confidenceText">Confidence: 0%</small>
                    </div>
                    
                    <div id="recommendationsDiv" class="recommendations" style="display: none;">
                        <h4>💡 Recommendations</h4>
                        <div id="recommendationsList"></div>
                    </div>
                    
                    <div class="feedback-section">
                        <p>Was this helpful?</p>
                        <button class="feedback-btn positive" onclick="giveFeedback(true)">👍 Yes</button>
                        <button class="feedback-btn negative" onclick="giveFeedback(false)">👎 No</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentResponseId = null;
        
        async function askQuestion() {
            const question = document.getElementById('questionInput').value.trim();
            if (!question) return;
            
            await processQuestion(question);
        }
        
        async function askSpecificQuestion(question) {
            document.getElementById('questionInput').value = question;
            await processQuestion(question);
        }
        
        async function processQuestion(question) {
            const responseSection = document.getElementById('responseSection');
            const loadingDiv = document.getElementById('loadingDiv');
            const answerDiv = document.getElementById('answerDiv');
            
            // Show loading
            responseSection.style.display = 'block';
            loadingDiv.style.display = 'block';
            answerDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        question: question,
                        include_technical_details: false
                    })
                });
                
                const result = await response.json();
                
                // Hide loading
                loadingDiv.style.display = 'none';
                answerDiv.style.display = 'block';
                
                // Display answer
                document.getElementById('answerContent').innerHTML = result.answer;
                
                // Update confidence
                const confidence = Math.round(result.confidence * 100);
                document.getElementById('confidenceFill').style.width = confidence + '%';
                document.getElementById('confidenceText').textContent = `Confidence: ${confidence}%`;
                
                // Show recommendations if available
                if (result.recommendations && result.recommendations.length > 0) {
                    const recommendationsDiv = document.getElementById('recommendationsDiv');
                    const recommendationsList = document.getElementById('recommendationsList');
                    
                    recommendationsList.innerHTML = result.recommendations
                        .map(rec => `<div class="recommendation-item">${rec}</div>`)
                        .join('');
                    
                    recommendationsDiv.style.display = 'block';
                }
                
                currentResponseId = result.response_id;
                
            } catch (error) {
                loadingDiv.style.display = 'none';
                answerDiv.style.display = 'block';
                document.getElementById('answerContent').innerHTML = 
                    '<p style="color: red;">Sorry, there was an error processing your question. Please try again.</p>';
            }
        }
        
        async function giveFeedback(isPositive) {
            if (!currentResponseId) return;
            
            try {
                await fetch('/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        response_id: currentResponseId,
                        helpful: isPositive,
                        rating: isPositive ? 5 : 2
                    })
                });
                
                alert(isPositive ? 'Thank you for your positive feedback!' : 'Thank you for your feedback. We\'ll work to improve!');
            } catch (error) {
                console.error('Feedback error:', error);
            }
        }
        
        async function loadModelTemplates() {
            try {
                const response = await fetch('/api/no-code/templates');
                const result = await response.json();
                const grid = document.getElementById('modelTemplatesGrid');
                
                grid.innerHTML = result.templates.map(template => `
                    <div class="model-template-card" data-icon="${template.icon}" onclick="selectModelTemplate('${template.id}')">
                        <h3>${template.icon} ${template.name}</h3>
                        <p>${template.description}</p>
                        <div style="margin-top: 15px; font-size: 0.9rem; color: #666;">
                            <strong>Use Cases:</strong><br>
                            ${template.use_cases.join(', ')}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading model templates:', error);
            }
        }
        
        async function loadWorkflows() {
            try {
                const response = await fetch('/api/workflows');
                const result = await response.json();
                const grid = document.getElementById('workflowsGrid');
                
                grid.innerHTML = result.workflows.map(workflow => `
                    <div class="workflow-card" onclick="startWorkflow('${workflow.id}')">
                        <div>
                            <span class="difficulty">${workflow.difficulty}</span>
                            <span class="time-estimate">${workflow.estimated_time}</span>
                        </div>
                        <h3>${workflow.icon} ${workflow.name}</h3>
                        <p>${workflow.description}</p>
                        <div class="workflow-steps">
                            <strong>Steps:</strong>
                            <ol>
                                ${workflow.steps.map(step => `<li>${step}</li>`).join('')}
                            </ol>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading workflows:', error);
            }
        }
        
        async function selectModelTemplate(templateId) {
            const modelName = prompt('What would you like to name your model?', 'My Prediction Model');
            if (!modelName) return;
            
            const description = prompt('Brief description of what this model will predict:', '');
            
            try {
                const response = await fetch('/api/no-code/model', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        template_id: templateId,
                        name: modelName,
                        description: description
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`✅ ${result.message}\\n\\nModel ID: ${result.model_id}\\nTraining Status: ${result.training_status}`);
                } else {
                    alert(`❌ Failed to create model: ${result.message}`);
                }
            } catch (error) {
                alert('Error creating model. Please try again.');
                console.error('Model creation error:', error);
            }
        }
        
        async function startWorkflow(workflowId) {
            if (confirm('Start this guided workflow? It will walk you through each step.')) {
                try {
                    const response = await fetch(`/api/workflows/${workflowId}/start`, {
                        method: 'POST'
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        alert(`🚀 ${result.message}\\n\\nWorkflow ID: ${result.workflow_id}\\nNext Step: ${result.next_step}`);
                    } else {
                        alert('Failed to start workflow. Please try again.');
                    }
                } catch (error) {
                    alert('Error starting workflow. Please try again.');
                    console.error('Workflow start error:', error);
                }
            }
        }
        
        async function loadPlaygroundDatasets() {
            try {
                const response = await fetch('/api/playground/datasets');
                const result = await response.json();
                const grid = document.getElementById('datasetCards');
                
                grid.innerHTML = Object.entries(result.datasets).map(([key, dataset]) => `
                    <div class="dataset-card" onclick="selectPlaygroundDataset('${key}')">
                        <h4>${dataset.name}</h4>
                        <p>${dataset.description}</p>
                        <div class="dataset-stats">
                            📊 ${dataset.size} • 🔧 ${dataset.features} features
                            <br><strong>Try:</strong> ${dataset.suggested_tasks.slice(0, 2).join(', ')}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading playground datasets:', error);
            }
        }
        
        async function loadSmartRecommendations() {
            try {
                const response = await fetch('/api/smart/recommendations');
                const result = await response.json();
                const container = document.getElementById('smartRecommendations');
                
                let html = '';
                
                // Urgent recommendations
                if (result.urgent && result.urgent.length > 0) {
                    html += '<div class="recommendation-category"><h3>🚨 Urgent Actions</h3>';
                    result.urgent.forEach(rec => {
                        html += `
                            <div class="recommendation-card urgent">
                                <h4>${rec.title}</h4>
                                <p>${rec.description}</p>
                                <div class="recommendation-actions">
                                    <button class="action-btn" onclick="handleRecommendationAction('${rec.action}')">
                                        ${rec.action} (${rec.estimated_time})
                                    </button>
                                </div>
                            </div>`;
                    });
                    html += '</div>';
                }
                
                // Opportunities
                if (result.opportunities && result.opportunities.length > 0) {
                    html += '<div class="recommendation-category"><h3>💡 Opportunities</h3>';
                    result.opportunities.forEach(rec => {
                        html += `
                            <div class="recommendation-card opportunity">
                                <h4>${rec.title}</h4>
                                <p>${rec.description}</p>
                                <div class="recommendation-actions">
                                    <button class="action-btn" onclick="handleRecommendationAction('${rec.action}')">
                                        ${rec.action}
                                        ${rec.estimated_value ? ` (${rec.estimated_value})` : ''}
                                    </button>
                                </div>
                            </div>`;
                    });
                    html += '</div>';
                }
                
                // Insights
                if (result.insights && result.insights.length > 0) {
                    html += '<div class="recommendation-category"><h3>📊 Insights</h3>';
                    result.insights.forEach(insight => {
                        html += `
                            <div class="recommendation-card insight">
                                <h4>${insight.title}</h4>
                                <p>${insight.description}</p>
                                <small><strong>Suggestion:</strong> ${insight.suggestion}</small>
                            </div>`;
                    });
                    html += '</div>';
                }
                
                container.innerHTML = html;
            } catch (error) {
                console.error('Error loading smart recommendations:', error);
            }
        }
        
        async function selectPlaygroundDataset(datasetKey) {
            // Show experiment section
            document.getElementById('playgroundExperiment').style.display = 'block';
            
            // Create experiment
            try {
                const response = await fetch('/api/playground/experiment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        dataset: datasetKey,
                        name: `${datasetKey} Experiment`,
                        goal: 'prediction'
                    })
                });
                
                const experiment = await response.json();
                
                // Load model recommendations
                const recContainer = document.getElementById('modelRecommendations');
                recContainer.innerHTML = experiment.suggested_models.map(model => `
                    <div class="model-rec-card" onclick="selectModel('${model.model}')">
                        <div class="confidence-badge">${Math.round(model.confidence * 100)}%</div>
                        <h5>${model.model}</h5>
                        <p><strong>Why this works:</strong> ${model.reason}</p>
                        <div style="margin-top: 10px; font-size: 0.9rem; color: #666;">
                            <strong>Expected:</strong> ${model.expected_accuracy} accuracy in ${model.training_time}
                        </div>
                    </div>
                `).join('');
                
                // Load visualizations
                loadExperimentVisualizations(datasetKey);
                
            } catch (error) {
                console.error('Error creating playground experiment:', error);
            }
        }
        
        async function loadExperimentVisualizations(datasetKey) {
            try {
                const response = await fetch(`/api/visualizations/${datasetKey}`);
                const vizConfig = await response.json();
                const vizContainer = document.getElementById('playgroundVisualizations');
                
                // Create KPI cards
                let html = '<div class="kpi-grid">';
                vizConfig.kpis.forEach(kpi => {
                    const changeClass = kpi.change.startsWith('+') ? 'positive' : 'negative';
                    html += `
                        <div class="kpi-card">
                            <div class="kpi-value">${kpi.value}</div>
                            <div>${kpi.name}</div>
                            <div class="kpi-change ${changeClass}">${kpi.change}</div>
                        </div>`;
                });
                html += '</div>';
                
                // Add chart placeholder
                html += `
                    <div style="background: white; padding: 20px; border-radius: 10px; margin-top: 15px;">
                        <h5>${vizConfig.primary_chart.title}</h5>
                        <div style="height: 200px; background: linear-gradient(45deg, #667eea, #764ba2); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white;">
                            📈 Interactive Chart: ${vizConfig.primary_chart.type.toUpperCase()}
                            <br><small>Real charts would appear here with Chart.js</small>
                        </div>
                    </div>`;
                
                vizContainer.innerHTML = html;
            } catch (error) {
                console.error('Error loading visualizations:', error);
            }
        }
        
        function selectModel(modelName) {
            // Visual feedback
            document.querySelectorAll('.model-rec-card').forEach(card => {
                card.classList.remove('selected');
            });
            event.target.closest('.model-rec-card').classList.add('selected');
            
            // Show training animation
            const vizContainer = document.getElementById('playgroundVisualizations');
            vizContainer.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <div class="spinner"></div>
                    <h4>🤖 Training ${modelName}...</h4>
                    <p>Your AI is learning from the data! This is so exciting! 🎉</p>
                    <div style="margin-top: 20px; background: #f0f4ff; padding: 15px; border-radius: 10px;">
                        <strong>What's happening:</strong><br>
                        1. ✅ Data loaded successfully<br>
                        2. 🔄 Training model with smart algorithms<br>
                        3. ⏳ Optimizing performance...<br>
                        4. 🎯 Almost ready!
                    </div>
                </div>`;
            
            // Simulate training completion
            setTimeout(() => {
                vizContainer.innerHTML = `
                    <div style="text-align: center; padding: 30px;">
                        <h3>🎉 Congratulations! Your ${modelName} is ready!</h3>
                        <div style="background: #e8f5e8; padding: 20px; border-radius: 15px; margin: 20px 0;">
                            <h4>📊 Training Results:</h4>
                            <div class="kpi-grid" style="margin-top: 15px;">
                                <div class="kpi-card">
                                    <div class="kpi-value">91%</div>
                                    <div>Accuracy</div>
                                    <div class="kpi-change positive">Excellent!</div>
                                </div>
                                <div class="kpi-card">
                                    <div class="kpi-value">2.4 min</div>
                                    <div>Training Time</div>
                                    <div class="kpi-change positive">Super Fast!</div>
                                </div>
                                <div class="kpi-card">
                                    <div class="kpi-value">Ready</div>
                                    <div>Status</div>
                                    <div class="kpi-change positive">Let's Go!</div>
                                </div>
                            </div>
                        </div>
                        <button class="action-btn" onclick="startPredictions()" style="font-size: 1.1rem; padding: 12px 24px;">
                            🚀 Start Making Predictions!
                        </button>
                    </div>`;
            }, 3000);
        }
        
        function startPredictions() {
            alert("🎉 Amazing! Your model is now ready to make predictions!\\n\\nIn the full version, you'd be able to:\\n• Input new data\\n• Get instant predictions\\n• See confidence scores\\n• Export results\\n\\nYou're becoming a real data scientist! 🧬");
        }
        
        function handleRecommendationAction(action) {
            alert(`🚀 Starting: ${action}\\n\\nThis would trigger the actual workflow in the full system!`);
        }
        
        // Enhanced drag and drop for data files
        function initializeDragDrop() {
            const dropZone = document.getElementById('dataDropZone');
            const fileInput = document.getElementById('fileInput');
            
            dropZone.addEventListener('click', () => fileInput.click());
            
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });
            
            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('dragover');
            });
            
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                handleFileUpload(e.dataTransfer.files);
            });
            
            fileInput.addEventListener('change', (e) => {
                handleFileUpload(e.target.files);
            });
        }
        
        async function handleFileUpload(files) {
            for (let file of files) {
                // Simulate file processing
                const connectionData = await createDataConnection({
                    name: file.name,
                    type: file.type.includes('csv') ? 'csv' : 'json',
                    columns: ['Column 1', 'Column 2', 'Column 3'],
                    row_count: Math.floor(Math.random() * 1000) + 100,
                    data_types: {'Column 1': 'text', 'Column 2': 'number', 'Column 3': 'date'}
                });
                
                addDataConnectionCard(connectionData);
            }
        }
        
        async function createDataConnection(config) {
            try {
                const response = await fetch('/api/data/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                return await response.json();
            } catch (error) {
                console.error('Error creating data connection:', error);
                return null;
            }
        }
        
        function addDataConnectionCard(connection) {
            const container = document.getElementById('connectedData');
            const card = document.createElement('div');
            card.className = 'data-connection-card';
            card.innerHTML = `
                <h4>📊 ${connection.name}</h4>
                <p>${connection.schema.row_count} rows • ${connection.schema.columns.length} columns</p>
                <div class="connection-status connected">Connected</div>
                <div style="margin-top: 10px; font-size: 0.9rem; color: #666;">
                    Click to use in ML experiments!
                </div>
            `;
            card.addEventListener('click', () => {
                alert(`🎯 Using ${connection.name} for ML!\\n\\nThis would open the model builder with your data pre-loaded.`);
            });
            container.appendChild(card);
        }
        
        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            loadModelTemplates();
            loadWorkflows();
            loadPlaygroundDatasets();
            loadSmartRecommendations();
            initializeDragDrop();
        });
        
        // Enter key support
        document.getElementById('questionInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                askQuestion();
            }
        });
    </script>
</body>
</html>
'''
        
        # Save the template
        with open(templates_path / "dashboard.html", "w") as f:
            f.write(dashboard_template)
            
    def parse_natural_language_query(self, question: str) -> Tuple[QueryType, DataType, Dict[str, Any]]:
        """Parse natural language question to determine intent and parameters"""
        question_lower = question.lower()
        
        # Determine query type
        query_type = QueryType.ANALYSIS  # default
        for qtype, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    query_type = qtype
                    break
            if query_type != QueryType.ANALYSIS:
                break
                
        # Determine data type
        data_type = DataType.SYSTEM  # default
        for dtype, patterns in self.data_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    data_type = dtype
                    break
            if data_type != DataType.SYSTEM:
                break
                
        # Extract time parameters
        parameters = {}
        
        # Time periods
        time_patterns = {
            'hour': r'hour|hourly',
            'day': r'day|daily|today|yesterday',
            'week': r'week|weekly',
            'month': r'month|monthly',
            'quarter': r'quarter|quarterly',
            'year': r'year|yearly|annual'
        }
        
        for period, pattern in time_patterns.items():
            if re.search(pattern, question_lower):
                parameters['time_period'] = period
                break
                
        # Numbers
        numbers = re.findall(r'\b(\d+)\b', question)
        if numbers:
            parameters['number_value'] = int(numbers[0])
            
        # Specific terms
        if 'next' in question_lower:
            parameters['direction'] = 'future'
        elif 'last' in question_lower or 'past' in question_lower:
            parameters['direction'] = 'past'
            
        if 'increase' in question_lower or 'grow' in question_lower:
            parameters['trend_direction'] = 'up'
        elif 'decrease' in question_lower or 'decline' in question_lower:
            parameters['trend_direction'] = 'down'
            
        return query_type, data_type, parameters
        
    async def process_user_query(self, query: NaturalLanguageQuery) -> MLResponse:
        """Process a user query and generate ML-powered response"""
        query_id = str(uuid.uuid4())
        
        # Parse the natural language query
        query_type, data_type, parameters = self.parse_natural_language_query(query.question)
        
        # Store the query
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_queries (query_id, user_question, query_type, data_type, parameters)
                VALUES (?, ?, ?, ?, ?)
            """, (query_id, query.question, query_type.value, data_type.value, json.dumps(parameters)))
            
        # Generate response based on query type
        try:
            if query_type == QueryType.PREDICTION:
                response = await self._handle_prediction_query(data_type, parameters, query.question)
            elif query_type == QueryType.TREND:
                response = await self._handle_trend_query(data_type, parameters, query.question)
            elif query_type == QueryType.ANOMALY:
                response = await self._handle_anomaly_query(data_type, parameters, query.question)
            elif query_type == QueryType.RECOMMENDATION:
                response = await self._handle_recommendation_query(data_type, parameters, query.question)
            elif query_type == QueryType.COMPARISON:
                response = await self._handle_comparison_query(data_type, parameters, query.question)
            elif query_type == QueryType.MODEL_BUILD:
                response = await self._handle_model_build_query(data_type, parameters, query.question)
            elif query_type == QueryType.PLAYGROUND:
                response = await self._handle_playground_query(data_type, parameters, query.question)
            else:
                response = await self._handle_analysis_query(data_type, parameters, query.question)
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            response = self._generate_error_response(query.question)
            
        # Create ML response
        ml_response = MLResponse(
            response_id=str(uuid.uuid4()),
            query_id=query_id,
            answer=response['answer'],
            visualizations=response.get('visualizations', []),
            confidence=response.get('confidence', 0.7),
            recommendations=response.get('recommendations', []),
            technical_details=response.get('technical_details') if query.include_technical_details else None,
            created_at=datetime.now()
        )
        
        # Store response
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ml_responses 
                (response_id, query_id, answer, visualizations, confidence, recommendations, technical_details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ml_response.response_id, ml_response.query_id, ml_response.answer,
                json.dumps(ml_response.visualizations), ml_response.confidence,
                json.dumps(ml_response.recommendations),
                json.dumps(ml_response.technical_details) if ml_response.technical_details else None
            ))
            
        return ml_response
        
    async def _handle_prediction_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle prediction-type queries"""
        try:
            # Call appropriate ML service for predictions
            if data_type == DataType.TRADING:
                endpoint = "http://localhost:8608/forecast"
                forecast_request = {
                    "forecast_type": "trading_volume",
                    "horizon": "daily",
                    "periods": parameters.get('number_value', 7),
                    "include_confidence": True
                }
            elif data_type == DataType.USERS:
                endpoint = "http://localhost:8608/forecast"
                forecast_request = {
                    "forecast_type": "user_growth",
                    "horizon": "daily",
                    "periods": parameters.get('number_value', 30),
                    "include_confidence": True
                }
            elif data_type == DataType.REVENUE:
                endpoint = "http://localhost:8608/forecast"
                forecast_request = {
                    "forecast_type": "revenue",
                    "horizon": "daily",
                    "periods": parameters.get('number_value', 30),
                    "include_confidence": True
                }
            else:
                endpoint = "http://localhost:8608/forecast"
                forecast_request = {
                    "forecast_type": "system_load",
                    "horizon": "hourly",
                    "periods": parameters.get('number_value', 24),
                    "include_confidence": True
                }
                
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=forecast_request) as response:
                    if response.status == 200:
                        forecast_data = await response.json()
                        return self._format_prediction_response(forecast_data, data_type, question)
        except:
            pass
            
        # Fallback to mock response
        return self._generate_mock_prediction_response(data_type, parameters, question)
        
    async def _handle_trend_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle trend analysis queries"""
        # Mock trend analysis
        if data_type == DataType.TRADING:
            trend_description = "📈 Your trading volume shows a <strong>strong upward trend</strong> over the past month, with a 23% increase. Peak activity occurs during 9-11 AM and 2-4 PM EST."
            recommendations = [
                "Consider increasing liquidity during peak hours (9-11 AM, 2-4 PM)",
                "Monitor system capacity to handle growing volume",
                "Implement dynamic pricing based on volume patterns"
            ]
        elif data_type == DataType.USERS:
            trend_description = "👥 User growth is <strong>accelerating</strong> with a 15% month-over-month increase. New registrations peak on weekends and show seasonal patterns."
            recommendations = [
                "Scale customer support for weekend peak registrations",
                "Prepare onboarding infrastructure for continued growth",
                "Launch targeted weekend marketing campaigns"
            ]
        elif data_type == DataType.REVENUE:
            trend_description = "💰 Revenue shows <strong>steady growth</strong> with a 12% increase this quarter. Growth is driven primarily by existing user expansion rather than new acquisitions."
            recommendations = [
                "Focus on user retention and expansion strategies",
                "Develop premium features to increase average revenue per user",
                "Investigate opportunities in underperforming segments"
            ]
        else:
            trend_description = "⚡ System performance trends show <strong>increasing resource usage</strong> with 18% growth in CPU utilization. Memory usage remains stable."
            recommendations = [
                "Consider horizontal scaling to distribute CPU load",
                "Implement performance monitoring for proactive scaling",
                "Optimize high-CPU processes identified in the analysis"
            ]
            
        return {
            'answer': trend_description,
            'confidence': 0.85,
            'recommendations': recommendations,
            'visualizations': [{'type': 'trend_chart', 'title': f'{data_type.value.title()} Trend Analysis'}]
        }
        
    async def _handle_anomaly_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle anomaly detection queries"""
        try:
            # Call anomaly detection service
            endpoint = f"http://localhost:8608/anomalies/{data_type.value}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        anomaly_data = await response.json()
                        if anomaly_data:
                            return self._format_anomaly_response(anomaly_data, data_type)
        except:
            pass
            
        # Mock anomaly response
        if data_type == DataType.TRADING:
            answer = "🚨 <strong>2 anomalies detected</strong> in trading data:<br>• Unusual volume spike at 2:30 PM (3.2x normal)<br>• Irregular price movement pattern detected"
            recommendations = [
                "Investigate the 2:30 PM volume spike for potential market events",
                "Review trading algorithms for the irregular price patterns",
                "Increase monitoring for the next 24 hours"
            ]
        else:
            answer = "✅ <strong>No significant anomalies</strong> detected in your recent data. All metrics are within normal ranges."
            recommendations = [
                "Continue regular monitoring",
                "Set up alerts for future anomaly detection",
                "Review thresholds monthly to ensure accuracy"
            ]
            
        return {
            'answer': answer,
            'confidence': 0.9,
            'recommendations': recommendations,
            'visualizations': [{'type': 'anomaly_plot', 'title': f'{data_type.value.title()} Anomaly Detection'}]
        }
        
    async def _handle_recommendation_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle recommendation queries"""
        if data_type == DataType.TRADING:
            answer = "🎯 Based on your trading patterns, here are <strong>AI-powered recommendations</strong> to improve performance:"
            recommendations = [
                "Increase position sizes during high-confidence signals (>80% accuracy)",
                "Implement dynamic stop-losses based on volatility (currently 15% improvement potential)",
                "Focus on momentum strategies during 10 AM - 2 PM window (highest success rate)",
                "Reduce exposure during low-volume periods (after 4 PM EST)",
                "Consider adding sentiment analysis to current technical indicators"
            ]
        elif data_type == DataType.USERS:
            answer = "👥 Here are <strong>data-driven recommendations</strong> to improve user growth and retention:"
            recommendations = [
                "Launch referral program - analysis shows 67% of users have strong social networks",
                "Improve onboarding flow - 23% drop-off at step 3 identified",
                "Target weekend marketing - 40% higher conversion rates detected",
                "Implement email re-engagement for inactive users (30-60 days)",
                "Add mobile app push notifications - 45% engagement increase potential"
            ]
        elif data_type == DataType.REVENUE:
            answer = "💰 <strong>Revenue optimization recommendations</strong> based on ML analysis of your financial data:"
            recommendations = [
                "Increase pricing for premium tier by 12% (price elasticity analysis supports this)",
                "Launch quarterly billing discount - reduces churn by 18%",
                "Focus sales efforts on enterprise segment (highest LTV identified)",
                "Implement usage-based pricing for power users",
                "Cross-sell complementary services to existing customers (32% acceptance rate predicted)"
            ]
        else:
            answer = "⚡ <strong>System optimization recommendations</strong> from performance analysis:"
            recommendations = [
                "Scale CPU resources during 9 AM - 5 PM peak hours (30% performance gain)",
                "Implement caching layer for frequently accessed data (25% response time improvement)",
                "Migrate high-I/O processes to SSD storage",
                "Set up automated scaling rules based on traffic patterns",
                "Optimize database queries - 5 slow queries identified for improvement"
            ]
            
        return {
            'answer': answer,
            'confidence': 0.88,
            'recommendations': recommendations,
            'visualizations': [{'type': 'recommendation_chart', 'title': f'{data_type.value.title()} Optimization Opportunities'}]
        }
        
    async def _handle_comparison_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle comparison queries"""
        if data_type == DataType.TRADING:
            answer = "📊 <strong>Trading Performance Comparison:</strong><br>• This month vs last month: <span style='color: green'>+18% improvement</span><br>• Your performance vs market average: <span style='color: green'>+12% better</span><br>• Manual vs automated trades: Automated performs <span style='color: green'>23% better</span>"
        elif data_type == DataType.USERS:
            answer = "👥 <strong>User Metrics Comparison:</strong><br>• Growth rate vs last quarter: <span style='color: green'>+15% increase</span><br>• Retention rate vs industry average: <span style='color: green'>8% above average</span><br>• Mobile vs web users: Mobile users are <span style='color: green'>35% more engaged</span>"
        else:
            answer = "⚡ <strong>Performance Comparison:</strong><br>• Current vs last month: <span style='color: orange'>5% increase in resource usage</span><br>• Peak vs average performance: <span style='color: red'>40% degradation during peaks</span><br>• Cost efficiency vs last quarter: <span style='color: green'>12% improvement</span>"
            
        return {
            'answer': answer,
            'confidence': 0.82,
            'recommendations': [
                "Continue focusing on strategies that are outperforming",
                "Investigate underperforming areas for optimization opportunities",
                "Set up automated alerts when performance deviates significantly"
            ],
            'visualizations': [{'type': 'comparison_chart', 'title': f'{data_type.value.title()} Performance Comparison'}]
        }
        
    async def _handle_analysis_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle general analysis queries"""
        if data_type == DataType.TRADING:
            answer = "📈 <strong>Trading Analysis Summary:</strong><br>Your trading performance shows strong fundamentals with consistent profitability. Key metrics: 68% win rate, 1.4 profit factor, and average return of 2.3% per trade."
        elif data_type == DataType.USERS:
            answer = "👥 <strong>User Analytics Summary:</strong><br>Your user base is healthy and growing. Current metrics: 15,847 active users, 82% retention rate, and 23% month-over-month growth."
        elif data_type == DataType.REVENUE:
            answer = "💰 <strong>Revenue Analysis Summary:</strong><br>Revenue trends are positive with diversified income streams. Current status: $127K monthly recurring revenue, 94% retention rate, and 18% quarterly growth."
        else:
            answer = "⚡ <strong>System Performance Analysis:</strong><br>Your system is performing well with room for optimization. Current metrics: 99.2% uptime, 45ms average response time, and 67% resource utilization."
            
        return {
            'answer': answer,
            'confidence': 0.8,
            'recommendations': [
                "Monitor key metrics regularly for early trend detection",
                "Set up automated alerts for important thresholds",
                "Review and adjust targets quarterly based on performance"
            ],
            'visualizations': [{'type': 'dashboard', 'title': f'{data_type.value.title()} Analytics Dashboard'}]
        }
        
    def _generate_mock_prediction_response(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Generate mock prediction response"""
        periods = parameters.get('number_value', 7)
        
        if data_type == DataType.TRADING:
            answer = f"📈 <strong>Trading Volume Prediction (Next {periods} days):</strong><br>Expected volume: <span style='color: green'>↗ 23% increase</span><br>Peak days: Wednesday & Friday<br>Confidence interval: ±12%"
            recommendations = [
                "Prepare for increased trading activity mid-week",
                "Ensure adequate liquidity for peak days",
                "Monitor system capacity during high-volume periods"
            ]
        elif data_type == DataType.USERS:
            answer = f"👥 <strong>User Growth Prediction (Next {periods} days):</strong><br>Expected new users: <span style='color: green'>+1,247 users</span><br>Growth rate: <span style='color: green'>15% increase</span><br>Confidence: 87%"
            recommendations = [
                "Scale customer support for new user onboarding",
                "Prepare welcome campaigns for incoming users",
                "Monitor conversion funnels during growth period"
            ]
        elif data_type == DataType.REVENUE:
            answer = f"💰 <strong>Revenue Forecast (Next {periods} days):</strong><br>Expected revenue: <span style='color: green'>$142,500</span><br>Growth vs last period: <span style='color: green'>+8.3%</span><br>Confidence: 91%"
            recommendations = [
                "Plan reinvestment strategies for increased revenue",
                "Monitor customer acquisition cost trends",
                "Prepare for higher transaction processing volume"
            ]
        else:
            answer = f"⚡ <strong>System Load Prediction (Next {periods} hours):</strong><br>Peak usage: <span style='color: orange'>78% CPU utilization</span><br>Expected at: 2:00 PM - 4:00 PM<br>Confidence: 84%"
            recommendations = [
                "Consider auto-scaling before peak hours",
                "Monitor memory usage during high CPU periods",
                "Review performance optimization opportunities"
            ]
            
        return {
            'answer': answer,
            'confidence': 0.87,
            'recommendations': recommendations,
            'visualizations': [{'type': 'forecast_chart', 'title': f'{data_type.value.title()} Prediction'}]
        }
        
    def _format_prediction_response(self, forecast_data: Dict, data_type: DataType, question: str) -> Dict[str, Any]:
        """Format prediction response from ML service"""
        predictions = forecast_data.get('predictions', [])
        if not predictions:
            return self._generate_mock_prediction_response(data_type, {}, question)
            
        avg_prediction = sum(predictions) / len(predictions)
        confidence = forecast_data.get('accuracy_metrics', {}).get('accuracy', 0.7)
        
        if data_type == DataType.TRADING:
            answer = f"📈 <strong>Trading Forecast:</strong><br>Average predicted volume: <span style='color: green'>{avg_prediction:,.0f}</span><br>Model confidence: {confidence*100:.1f}%"
        else:
            answer = f"📊 <strong>Prediction Results:</strong><br>Forecasted value: <span style='color: blue'>{avg_prediction:,.2f}</span><br>Model confidence: {confidence*100:.1f}%"
            
        return {
            'answer': answer,
            'confidence': confidence,
            'recommendations': [
                "Monitor actual values against predictions",
                "Adjust strategies based on forecast trends",
                "Set up alerts for significant deviations"
            ],
            'visualizations': [{'type': 'forecast_chart', 'title': 'ML Prediction Results'}]
        }
        
    def _format_anomaly_response(self, anomaly_data: List[Dict], data_type: DataType) -> Dict[str, Any]:
        """Format anomaly detection response"""
        if not anomaly_data:
            return {
                'answer': "✅ <strong>No anomalies detected</strong> - all metrics are within normal ranges.",
                'confidence': 0.95,
                'recommendations': ["Continue regular monitoring", "Review thresholds periodically"],
                'visualizations': [{'type': 'anomaly_chart', 'title': 'Anomaly Detection Results'}]
            }
            
        high_severity = [a for a in anomaly_data if a.get('severity') in ['high', 'critical']]
        
        if high_severity:
            answer = f"🚨 <strong>{len(high_severity)} high-severity anomalies</strong> detected requiring immediate attention."
            recommendations = [
                "Investigate high-severity anomalies immediately",
                "Check system logs for related events",
                "Consider temporary mitigation measures"
            ]
        else:
            answer = f"⚠️ <strong>{len(anomaly_data)} minor anomalies</strong> detected - monitoring recommended."
            recommendations = [
                "Monitor anomalies for pattern development",
                "Document anomalies for trend analysis",
                "Review if thresholds need adjustment"
            ]
            
        return {
            'answer': answer,
            'confidence': 0.9,
            'recommendations': recommendations,
            'visualizations': [{'type': 'anomaly_chart', 'title': 'Anomaly Detection Results'}]
        }
    
    async def _handle_model_build_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle model building queries with conversational guidance"""
        question_lower = question.lower()
        
        # Check if it's a kid-friendly request
        kid_friendly = any(word in question_lower for word in ['teach', 'smart robot', 'ai helper', 'magic', 'simple', 'easy'])
        
        if kid_friendly:
            return await self._handle_kids_model_building(data_type, parameters, question)
        
        # Determine model type based on question context
        if any(word in question_lower for word in ['predict', 'forecast', 'estimate']):
            model_type = 'prediction'
            suggested_algorithm = 'Random Forest'
        elif any(word in question_lower for word in ['segment', 'group', 'cluster']):
            model_type = 'clustering'
            suggested_algorithm = 'K-Means'
        elif any(word in question_lower for word in ['classify', 'category', 'label']):
            model_type = 'classification'
            suggested_algorithm = 'Gradient Boosting'
        else:
            model_type = 'automl'
            suggested_algorithm = 'AutoML'
        
        # Generate conversational model training response
        if model_type == 'prediction':
            answer = f"""🎯 <strong>Let's build your prediction model!</strong><br><br>
            I understand you want to predict {data_type.value} data. Here's how we'll make it super easy:<br><br>
            🔧 <strong>Recommended Model:</strong> {suggested_algorithm} (Perfect for beginners!)<br>
            ⏱️ <strong>Training Time:</strong> Just 2-3 minutes<br>
            🎯 <strong>Expected Accuracy:</strong> 85-92%<br><br>
            <strong>Next Steps:</strong><br>
            1. I'll automatically prepare your data<br>
            2. Train the model with smart settings<br>
            3. Show you easy-to-understand results<br>
            4. Give you predictions you can use right away!"""
            
        elif model_type == 'clustering':
            answer = f"""👥 <strong>Let's create your customer grouping model!</strong><br><br>
            I'll help you discover hidden patterns in your {data_type.value} data:<br><br>
            🔧 <strong>Smart Algorithm:</strong> K-Means Clustering<br>
            🎯 <strong>What you'll get:</strong> 3-5 meaningful customer groups<br>
            📊 <strong>Visual Results:</strong> Easy charts showing each group<br><br>
            <strong>Magic happens in 3 steps:</strong><br>
            1. I analyze your customer behavior automatically<br>
            2. Find natural groups based on patterns<br>
            3. Create actionable strategies for each group!"""
            
        else:  # automl
            answer = f"""🤖 <strong>AutoML to the rescue!</strong><br><br>
            Let me be your AI assistant and build the perfect model for you:<br><br>
            ✨ <strong>What I'll do:</strong> Test multiple algorithms automatically<br>
            🧠 <strong>Smart Selection:</strong> Pick the best one for your data<br>
            ⚡ <strong>No coding needed:</strong> Just tell me what you want to predict<br><br>
            <strong>Your model will be ready in 5-10 minutes with:</strong><br>
            • Optimized performance<br>
            • Easy explanations of results<br>
            • One-click predictions<br>
            • Beautiful visualizations"""
        
        recommendations = [
            "Click 'Start Training' and I'll guide you through each step",
            "You can modify settings anytime - I'll explain what each does",
            "Once trained, try predictions with your own data",
            "I'll help you understand and use the results"
        ]
        
        return {
            'answer': answer,
            'confidence': 0.95,
            'recommendations': recommendations,
            'visualizations': [{'type': 'model_builder', 'title': 'Interactive Model Builder'}],
            'next_action': 'start_model_training',
            'model_config': {
                'type': model_type,
                'algorithm': suggested_algorithm,
                'data_type': data_type.value,
                'difficulty': 'beginner'
            }
        }
    
    async def _handle_kids_model_building(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle ML model building for kids with fun explanations"""
        answer = """🌟 <strong>Let's build a smart robot together!</strong><br><br>
        Hi there! I'm going to help you create your very own AI helper! It's like teaching a computer to be super smart! 🤖<br><br>
        
        <strong>🎮 Here's our adventure plan:</strong><br>
        1. <strong>Choose your robot's job</strong> - What do you want it to learn?<br>
        2. <strong>Feed it some data</strong> - Like teaching with examples!<br>
        3. <strong>Watch it learn</strong> - See the magic happen!<br>
        4. <strong>Test your robot</strong> - Ask it questions and see how smart it got!<br><br>
        
        <strong>🎭 Fun fact:</strong> Your computer is like a student - the more examples you show it, the smarter it becomes!<br><br>
        
        Ready to start this amazing journey? Your AI robot is excited to learn from you! 🚀"""
        
        recommendations = [
            "🎯 Start with our 'Pet Classifier' - teach the computer to recognize cats and dogs!",
            "🎨 Try the 'Color Predictor' - predict what colors people like!",
            "🎲 Build a 'Game Winner' - predict who will win games!",
            "📚 Explore our 'Story Generator' - create fun stories with AI!"
        ]
        
        return {
            'answer': answer,
            'confidence': 0.98,
            'recommendations': recommendations,
            'visualizations': [{'type': 'kids_playground', 'title': 'Kids ML Adventure Playground'}],
            'kid_friendly': True
        }
    
    async def _handle_playground_query(self, data_type: DataType, parameters: Dict, question: str) -> Dict[str, Any]:
        """Handle ML playground and experimentation queries"""
        question_lower = question.lower()
        
        # Check if it's a kid-friendly request
        kid_friendly = any(word in question_lower for word in ['kids', 'fun', 'game', 'play', 'simple', 'easy', 'learn'])
        
        if kid_friendly:
            answer = """🎮 <strong>Welcome to the ML Playground!</strong><br><br>
            Get ready for some awesome machine learning adventures! Here's what we can explore together:<br><br>
            
            🎯 <strong>Fun Experiments:</strong><br>
            • <strong>Pet Detective</strong> - Train AI to recognize different animals<br>
            • <strong>Weather Wizard</strong> - Predict tomorrow's weather<br>
            • <strong>Treasure Hunter</strong> - Find patterns in mysterious data<br>
            • <strong>Future Teller</strong> - Make predictions about anything!<br><br>
            
            🌟 <strong>What makes this special:</strong><br>
            • No complicated stuff - just point and click!<br>
            • See results instantly with colorful charts<br>
            • Every step explained in simple words<br>
            • Safe sample data to play with<br><br>
            
            Ready to become a young data scientist? Let's explore the magic of AI together! ✨"""
        else:
            answer = """🧪 <strong>ML Playground is ready for you!</strong><br><br>
            Explore machine learning without any setup or coding. Perfect for learning and experimentation!<br><br>
            
            🎯 <strong>Available Experiments:</strong><br>
            • <strong>Sales Forecasting Demo</strong> - Try prediction models with sample retail data<br>
            • <strong>Customer Segmentation Lab</strong> - Explore clustering with sample customer data<br>
            • <strong>A/B Testing Simulator</strong> - Learn statistical significance with real scenarios<br>
            • <strong>Anomaly Detection Workshop</strong> - Practice finding outliers in sample datasets<br><br>
            
            🔧 <strong>Interactive Features:</strong><br>
            • Real-time parameter tuning with sliders<br>
            • Instant visualization of results<br>
            • Compare different algorithms side-by-side<br>
            • Export results and code snippets<br><br>
            
            Start experimenting immediately - no data preparation needed!"""
        
        recommendations = [
            "🎯 Start with the Sales Prediction experiment - great for beginners",
            "📊 Try adjusting model parameters and see results change instantly",
            "🔍 Use the 'Explain Results' feature to understand what happened",
            "💾 Save your favorite experiments for later reference"
        ]
        
        return {
            'answer': answer,
            'confidence': 0.92,
            'recommendations': recommendations,
            'visualizations': [{'type': 'playground_launcher', 'title': 'ML Playground Launcher'}],
            'kid_friendly': kid_friendly,
            'playground_ready': True
        }
        
    def _generate_error_response(self, question: str) -> Dict[str, Any]:
        """Generate error response for failed queries"""
        return {
            'answer': "I apologize, but I encountered an issue processing your question. Please try rephrasing it or contact support if the problem persists.",
            'confidence': 0.1,
            'recommendations': [
                "Try asking your question in a different way",
                "Check if the requested data is available",
                "Contact support for technical assistance"
            ],
            'visualizations': []
        }
    
    async def create_no_code_model(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a model using no-code configuration"""
        try:
            # Send model configuration to ML Orchestrator
            async with aiohttp.ClientSession() as session:
                endpoint = "http://localhost:8607/models/create"
                async with session.post(endpoint, json=model_config) as response:
                    if response.status == 200:
                        result = await response.json()
                        model_id = result.get('model_id')
                        
                        # Store model metadata in database
                        with sqlite3.connect(self.db_path) as conn:
                            conn.execute("""
                                INSERT INTO user_models (model_id, name, type, description, config, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                model_id,
                                model_config.get('name', 'Untitled Model'),
                                model_config.get('algorithm_type', 'regression'),
                                model_config.get('description', ''),
                                json.dumps(model_config),
                                datetime.now().isoformat()
                            ))
                            conn.commit()
                        
                        return {
                            'success': True,
                            'model_id': model_id,
                            'message': f"Successfully created {model_config.get('name', 'model')}!",
                            'training_status': 'started'
                        }
        except Exception as e:
            logger.error(f"Error creating no-code model: {e}")
        
        return {
            'success': False,
            'message': 'Failed to create model. Please check your configuration.',
            'error': 'Service unavailable'
        }
    
    def get_guided_workflows(self) -> List[Dict[str, Any]]:
        """Get available guided ML workflows"""
        return [
            {
                'id': 'sales_prediction',
                'name': 'Sales Forecasting',
                'description': 'Predict future sales trends and identify growth opportunities',
                'difficulty': 'Beginner',
                'estimated_time': '5-10 minutes',
                'icon': '📈',
                'steps': [
                    'Connect your sales data',
                    'Select forecasting period',
                    'Choose prediction model',
                    'Review and deploy',
                    'Get predictions and insights'
                ],
                'data_requirements': ['Historical sales data', 'Date information'],
                'outputs': ['Sales forecasts', 'Trend analysis', 'Seasonal patterns']
            },
            {
                'id': 'customer_segmentation',
                'name': 'Customer Segmentation',
                'description': 'Group customers based on behavior and characteristics',
                'difficulty': 'Intermediate',
                'estimated_time': '10-15 minutes',
                'icon': '👥',
                'steps': [
                    'Upload customer data',
                    'Select features to analyze',
                    'Choose number of segments',
                    'Run clustering analysis',
                    'Interpret segments and strategies'
                ],
                'data_requirements': ['Customer data', 'Behavioral metrics', 'Demographics'],
                'outputs': ['Customer segments', 'Segment profiles', 'Marketing strategies']
            },
            {
                'id': 'anomaly_detection',
                'name': 'Anomaly Detection',
                'description': 'Identify unusual patterns and outliers in your data',
                'difficulty': 'Beginner',
                'estimated_time': '5-8 minutes',
                'icon': '🚨',
                'steps': [
                    'Select data source',
                    'Configure detection sensitivity',
                    'Set alert thresholds',
                    'Test detection model',
                    'Monitor and get alerts'
                ],
                'data_requirements': ['Time series data', 'Baseline metrics'],
                'outputs': ['Anomaly alerts', 'Unusual pattern reports', 'Monitoring dashboard']
            },
            {
                'id': 'price_optimization',
                'name': 'Price Optimization',
                'description': 'Find optimal pricing strategies to maximize revenue',
                'difficulty': 'Advanced',
                'estimated_time': '15-20 minutes',
                'icon': '💰',
                'steps': [
                    'Import pricing and sales data',
                    'Define optimization goals',
                    'Set business constraints',
                    'Run optimization models',
                    'Review pricing recommendations'
                ],
                'data_requirements': ['Pricing history', 'Sales volume', 'Costs', 'Market data'],
                'outputs': ['Optimal prices', 'Revenue projections', 'A/B test recommendations']
            },
            {
                'id': 'risk_assessment',
                'name': 'Risk Assessment',
                'description': 'Evaluate and predict business risks using ML models',
                'difficulty': 'Intermediate',
                'estimated_time': '12-18 minutes',
                'icon': '⚠️',
                'steps': [
                    'Define risk factors',
                    'Connect relevant data sources',
                    'Configure risk models',
                    'Set risk thresholds',
                    'Deploy risk monitoring'
                ],
                'data_requirements': ['Financial data', 'Market indicators', 'Historical risks'],
                'outputs': ['Risk scores', 'Risk factors analysis', 'Mitigation strategies']
            }
        ]
    
    def create_ml_playground_experiment(self, experiment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create an interactive ML playground experiment"""
        experiment_id = str(uuid.uuid4())
        
        # Generate sample data for playground
        sample_datasets = {
            'sales_data': {
                'columns': ['date', 'product', 'sales_amount', 'customers'],
                'sample_rows': [
                    ['2024-01-01', 'Product A', 1200.50, 45],
                    ['2024-01-02', 'Product B', 850.75, 32],
                    ['2024-01-03', 'Product A', 1450.25, 52]
                ],
                'description': 'Sample sales data with dates, products, and amounts'
            },
            'customer_data': {
                'columns': ['customer_id', 'age', 'spend_amount', 'visits'],
                'sample_rows': [
                    ['CUST_001', 28, 1250.00, 12],
                    ['CUST_002', 34, 890.50, 8],
                    ['CUST_003', 45, 2100.75, 18]
                ],
                'description': 'Sample customer data with demographics and behavior'
            },
            'system_metrics': {
                'columns': ['timestamp', 'cpu_usage', 'memory_usage', 'requests'],
                'sample_rows': [
                    ['2024-01-01 10:00', 65.2, 78.5, 1250],
                    ['2024-01-01 11:00', 72.8, 81.2, 1385],
                    ['2024-01-01 12:00', 58.4, 75.9, 1180]
                ],
                'description': 'Sample system performance metrics'
            }
        }
        
        experiment_data = {
            'experiment_id': experiment_id,
            'name': experiment_config.get('name', 'ML Playground Experiment'),
            'selected_dataset': experiment_config.get('dataset', 'sales_data'),
            'available_datasets': sample_datasets,
            'suggested_models': self._get_smart_model_recommendations(experiment_config),
            'interactive_features': {
                'parameter_tuning': True,
                'real_time_results': True,
                'visualization_options': ['scatter_plot', 'line_chart', 'heatmap', 'distribution'],
                'export_options': ['json', 'csv', 'pdf_report']
            }
        }
        
        # Store experiment
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ml_experiments (experiment_id, name, description, dataset_config, model_config, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                experiment_id,
                experiment_data['name'],
                f"Interactive playground experiment with {experiment_data['selected_dataset']}",
                json.dumps(sample_datasets[experiment_data['selected_dataset']]),
                json.dumps(experiment_config),
                'ready'
            ))
            conn.commit()
        
        return experiment_data
    
    def _get_smart_model_recommendations(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate smart ML model recommendations based on data and goals"""
        dataset_type = config.get('dataset', 'sales_data')
        goal = config.get('goal', 'prediction')
        
        if dataset_type == 'sales_data' and goal == 'prediction':
            return [
                {
                    'model': 'Random Forest',
                    'confidence': 0.92,
                    'reason': 'Excellent for sales prediction with time-series patterns',
                    'expected_accuracy': '85-90%',
                    'training_time': '2-3 minutes',
                    'parameters': {
                        'n_estimators': 100,
                        'max_depth': 10,
                        'min_samples_split': 2
                    }
                },
                {
                    'model': 'Gradient Boosting',
                    'confidence': 0.88,
                    'reason': 'Great for capturing complex sales relationships',
                    'expected_accuracy': '82-88%',
                    'training_time': '3-5 minutes',
                    'parameters': {
                        'n_estimators': 100,
                        'learning_rate': 0.1,
                        'max_depth': 6
                    }
                }
            ]
        elif dataset_type == 'customer_data' and goal == 'segmentation':
            return [
                {
                    'model': 'K-Means Clustering',
                    'confidence': 0.90,
                    'reason': 'Perfect for customer segmentation based on behavior',
                    'expected_accuracy': '75-85% silhouette score',
                    'training_time': '1-2 minutes',
                    'parameters': {
                        'n_clusters': 4,
                        'random_state': 42
                    }
                }
            ]
        else:
            return [
                {
                    'model': 'AutoML Selection',
                    'confidence': 0.85,
                    'reason': 'Let AI choose the best model for your data',
                    'expected_accuracy': 'Optimized automatically',
                    'training_time': '5-10 minutes',
                    'parameters': {'auto_optimize': True}
                }
            ]
    
    def get_real_time_visualizations(self, data_type: str) -> Dict[str, Any]:
        """Generate real-time visualization configurations"""
        viz_configs = {
            'sales_data': {
                'primary_chart': {
                    'type': 'line',
                    'title': 'Sales Trend Over Time',
                    'x_axis': 'date',
                    'y_axis': 'sales_amount',
                    'color_scheme': ['#667eea', '#764ba2']
                },
                'secondary_charts': [
                    {
                        'type': 'bar',
                        'title': 'Sales by Product',
                        'x_axis': 'product',
                        'y_axis': 'sales_amount'
                    },
                    {
                        'type': 'scatter',
                        'title': 'Sales vs Customers',
                        'x_axis': 'customers',
                        'y_axis': 'sales_amount'
                    }
                ],
                'kpis': [
                    {'name': 'Total Sales', 'value': '$45,230', 'change': '+12.5%'},
                    {'name': 'Avg Deal Size', 'value': '$1,245', 'change': '+3.2%'},
                    {'name': 'Customer Count', 'value': '342', 'change': '+18.7%'}
                ]
            },
            'system_metrics': {
                'primary_chart': {
                    'type': 'area',
                    'title': 'System Performance Over Time',
                    'x_axis': 'timestamp',
                    'y_axis': 'cpu_usage',
                    'color_scheme': ['#ff7675', '#fdcb6e']
                },
                'secondary_charts': [
                    {
                        'type': 'gauge',
                        'title': 'CPU Usage',
                        'value': 72.5,
                        'max': 100
                    },
                    {
                        'type': 'gauge',
                        'title': 'Memory Usage',
                        'value': 81.2,
                        'max': 100
                    }
                ],
                'kpis': [
                    {'name': 'Uptime', 'value': '99.8%', 'change': '+0.1%'},
                    {'name': 'Avg Response', 'value': '125ms', 'change': '-5.2%'},
                    {'name': 'Error Rate', 'value': '0.02%', 'change': '-12.8%'}
                ]
            }
        }
        
        return viz_configs.get(data_type, viz_configs['sales_data'])

# Global user-friendly ML instance
user_ml = UserFriendlyML()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "query_templates": user_ml.query_templates
    })

@app.post("/api/ask")
async def ask_question(query: NaturalLanguageQuery):
    """Process natural language question"""
    response = await user_ml.process_user_query(query)
    
    return {
        "response_id": response.response_id,
        "answer": response.answer,
        "confidence": response.confidence,
        "recommendations": response.recommendations,
        "visualizations": response.visualizations,
        "technical_details": response.technical_details
    }

@app.post("/api/feedback")
async def submit_feedback(
    response_id: str = Form(...),
    helpful: bool = Form(...),
    rating: int = Form(...),
    comments: str = Form("")
):
    """Submit user feedback"""
    feedback_id = str(uuid.uuid4())
    
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.execute("""
            INSERT INTO user_feedback (feedback_id, response_id, rating, comments, helpful)
            VALUES (?, ?, ?, ?, ?)
        """, (feedback_id, response_id, rating, comments, helpful))
        
    return {"message": "Thank you for your feedback!"}

@app.get("/api/query-history")
async def get_query_history(limit: int = 20):
    """Get recent query history"""
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        queries = conn.execute("""
            SELECT q.*, r.answer, r.confidence, r.created_at as response_time
            FROM user_queries q
            LEFT JOIN ml_responses r ON q.query_id = r.query_id
            ORDER BY q.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        
    return [dict(query) for query in queries]

@app.get("/api/popular-queries")
async def get_popular_queries():
    """Get most popular query types"""
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        popular = conn.execute("""
            SELECT query_type, data_type, COUNT(*) as count
            FROM user_queries
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY query_type, data_type
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
    return [dict(row) for row in popular]

@app.get("/api/analytics")
async def get_usage_analytics():
    """Get usage analytics for the ML interface"""
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_queries,
                AVG(confidence) as avg_confidence,
                COUNT(CASE WHEN helpful = 1 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN helpful = 0 THEN 1 END) as negative_feedback
            FROM user_queries q
            LEFT JOIN ml_responses r ON q.query_id = r.query_id
            LEFT JOIN user_feedback f ON r.response_id = f.response_id
            WHERE q.created_at > datetime('now', '-30 days')
        """).fetchone()
        
        query_types = conn.execute("""
            SELECT query_type, COUNT(*) as count
            FROM user_queries
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY query_type
        """).fetchall()
        
    return {
        'summary': dict(stats) if stats else {},
        'query_types': [dict(row) for row in query_types]
    }

@app.get("/api/workflows")
async def get_workflows():
    """Get available guided ML workflows"""
    workflows = user_ml.get_guided_workflows()
    return {"workflows": workflows}

@app.post("/api/workflows/{workflow_id}/start")
async def start_workflow(workflow_id: str):
    """Start a guided ML workflow"""
    workflows = user_ml.get_guided_workflows()
    workflow = next((w for w in workflows if w['id'] == workflow_id), None)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Create workflow instance
    workflow_instance_id = str(uuid.uuid4())
    
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.execute("""
            INSERT INTO workflows (workflow_id, name, type, description, steps, current_step, config)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow_instance_id,
            workflow['name'],
            workflow_id,
            workflow['description'],
            json.dumps(workflow['steps']),
            0,
            json.dumps(workflow)
        ))
        
        # Create progress entries for each step
        for i, step in enumerate(workflow['steps']):
            conn.execute("""
                INSERT INTO workflow_progress (progress_id, workflow_id, step_number, step_name, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                workflow_instance_id,
                i,
                step,
                'current' if i == 0 else 'pending'
            ))
        conn.commit()
    
    return {
        "success": True,
        "workflow_id": workflow_instance_id,
        "current_step": 0,
        "next_step": workflow['steps'][0],
        "message": f"Started {workflow['name']} workflow"
    }

@app.get("/api/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get workflow progress status"""
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        workflow = conn.execute("""
            SELECT * FROM workflows WHERE workflow_id = ?
        """, (workflow_id,)).fetchone()
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        progress = conn.execute("""
            SELECT * FROM workflow_progress 
            WHERE workflow_id = ? 
            ORDER BY step_number
        """, (workflow_id,)).fetchall()
        
    return {
        "workflow": dict(workflow),
        "progress": [dict(p) for p in progress],
        "current_step": workflow['current_step'],
        "total_steps": len(progress)
    }

@app.post("/api/no-code/model")
async def create_no_code_model(model_request: Dict[str, Any]):
    """Create a model using no-code configuration"""
    result = await user_ml.create_no_code_model(model_request)
    return result

@app.get("/api/no-code/templates")
async def get_model_templates():
    """Get no-code model templates"""
    templates = [
        {
            'id': 'regression_template',
            'name': 'Prediction Model',
            'type': 'regression',
            'description': 'Predict numerical values like sales, revenue, or prices',
            'icon': '📈',
            'config': {
                'algorithm_type': 'random_forest',
                'parameters': {
                    'n_estimators': 100,
                    'max_depth': None
                },
                'features_required': ['numerical_features', 'time_features'],
                'target_type': 'continuous'
            },
            'use_cases': ['Sales forecasting', 'Price prediction', 'Demand planning']
        },
        {
            'id': 'classification_template',
            'name': 'Classification Model',
            'type': 'classification',
            'description': 'Categorize data into groups like customer segments or risk levels',
            'icon': '🎯',
            'config': {
                'algorithm_type': 'gradient_boosting',
                'parameters': {
                    'n_estimators': 100,
                    'learning_rate': 0.1
                },
                'features_required': ['categorical_features', 'numerical_features'],
                'target_type': 'categorical'
            },
            'use_cases': ['Customer segmentation', 'Risk classification', 'Quality assessment']
        },
        {
            'id': 'clustering_template',
            'name': 'Clustering Model',
            'type': 'clustering',
            'description': 'Find natural groups and patterns in your data',
            'icon': '👥',
            'config': {
                'algorithm_type': 'kmeans',
                'parameters': {
                    'n_clusters': 3,
                    'random_state': 42
                },
                'features_required': ['numerical_features'],
                'target_type': 'unsupervised'
            },
            'use_cases': ['Customer segmentation', 'Market analysis', 'Product grouping']
        },
        {
            'id': 'anomaly_template',
            'name': 'Anomaly Detection',
            'type': 'anomaly_detection',
            'description': 'Detect unusual patterns and outliers automatically',
            'icon': '🚨',
            'config': {
                'algorithm_type': 'isolation_forest',
                'parameters': {
                    'contamination': 0.1,
                    'random_state': 42
                },
                'features_required': ['time_series_features'],
                'target_type': 'anomaly_score'
            },
            'use_cases': ['Fraud detection', 'System monitoring', 'Quality control']
        }
    ]
    return {"templates": templates}

@app.get("/api/no-code/models")
async def get_user_models():
    """Get user's created models"""
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.row_factory = sqlite3.Row
        models = conn.execute("""
            SELECT * FROM user_models 
            ORDER BY created_at DESC
        """).fetchall()
    
    return {"models": [dict(model) for model in models]}

@app.post("/api/playground/experiment")
async def create_playground_experiment(experiment_config: Dict[str, Any]):
    """Create an interactive ML playground experiment"""
    experiment = user_ml.create_ml_playground_experiment(experiment_config)
    return experiment

@app.get("/api/playground/datasets")
async def get_playground_datasets():
    """Get available datasets for ML playground"""
    datasets = {
        'sales_data': {
            'name': '💰 Sales Data',
            'description': 'Historical sales data with products, amounts, and customers',
            'size': '1,250 records',
            'features': 4,
            'suggested_tasks': ['Sales Forecasting', 'Product Analysis', 'Customer Trends']
        },
        'customer_data': {
            'name': '👥 Customer Data',
            'description': 'Customer demographics and behavioral data',
            'size': '890 customers',
            'features': 4,
            'suggested_tasks': ['Customer Segmentation', 'Lifetime Value Prediction', 'Churn Analysis']
        },
        'system_metrics': {
            'name': '⚡ System Metrics',
            'description': 'System performance and monitoring data',
            'size': '2,100 data points',
            'features': 4,
            'suggested_tasks': ['Anomaly Detection', 'Performance Forecasting', 'Capacity Planning']
        }
    }
    return {"datasets": datasets}

@app.get("/api/visualizations/{data_type}")
async def get_real_time_visualizations(data_type: str):
    """Get real-time visualization configuration for data type"""
    viz_config = user_ml.get_real_time_visualizations(data_type)
    return viz_config

@app.post("/api/models/compare")
async def compare_models(comparison_request: Dict[str, Any]):
    """Compare multiple ML models side by side"""
    comparison_id = str(uuid.uuid4())
    model_ids = comparison_request.get('model_ids', [])
    
    # Mock comparison results - in reality this would call the ML Orchestrator
    comparison_results = {
        'comparison_id': comparison_id,
        'models_compared': len(model_ids),
        'metrics': {
            'accuracy': [0.87, 0.92, 0.85],
            'precision': [0.84, 0.89, 0.82],
            'recall': [0.89, 0.94, 0.87],
            'f1_score': [0.86, 0.91, 0.84]
        },
        'performance': {
            'training_time': ['2.3 min', '4.1 min', '1.8 min'],
            'inference_speed': ['15ms', '22ms', '12ms'],
            'memory_usage': ['245MB', '312MB', '198MB']
        },
        'recommendations': [
            "Model 2 (Random Forest) shows the best overall performance with 92% accuracy",
            "Model 3 is fastest for real-time predictions with 12ms inference time",
            "Model 1 provides good balance of accuracy and speed for production use"
        ]
    }
    
    # Store comparison
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.execute("""
            INSERT INTO model_comparisons (comparison_id, name, model_ids, metrics, recommendations)
            VALUES (?, ?, ?, ?, ?)
        """, (
            comparison_id,
            f"Model Comparison {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            json.dumps(model_ids),
            json.dumps(comparison_results['metrics']),
            json.dumps(comparison_results['recommendations'])
        ))
        conn.commit()
    
    return comparison_results

@app.post("/api/data/connect")
async def create_data_connection(connection_config: Dict[str, Any]):
    """Create a new data connection for drag-and-drop functionality"""
    connection_id = str(uuid.uuid4())
    
    connection_data = {
        'connection_id': connection_id,
        'name': connection_config.get('name', 'New Connection'),
        'type': connection_config.get('type', 'csv'),
        'status': 'connected',
        'schema': {
            'columns': connection_config.get('columns', []),
            'row_count': connection_config.get('row_count', 0),
            'data_types': connection_config.get('data_types', {})
        }
    }
    
    # Store connection
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.execute("""
            INSERT INTO data_connections (connection_id, name, type, config, schema_info)
            VALUES (?, ?, ?, ?, ?)
        """, (
            connection_id,
            connection_data['name'],
            connection_data['type'],
            json.dumps(connection_config),
            json.dumps(connection_data['schema'])
        ))
        conn.commit()
    
    return connection_data

@app.get("/api/data/connections")
async def get_data_connections():
    """Get all available data connections"""
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.row_factory = sqlite3.Row
        connections = conn.execute("""
            SELECT * FROM data_connections 
            WHERE status = 'active'
            ORDER BY last_used DESC, created_at DESC
        """).fetchall()
    
    return {"connections": [dict(conn) for conn in connections]}

@app.post("/api/collaboration/session")
async def create_collaboration_session(session_config: Dict[str, Any]):
    """Create a collaborative ML workspace session"""
    session_id = str(uuid.uuid4())
    
    session_data = {
        'session_id': session_id,
        'name': session_config.get('name', 'ML Collaboration Session'),
        'participants': session_config.get('participants', ['current_user']),
        'shared_resources': {
            'models': [],
            'datasets': [],
            'experiments': [],
            'workflows': []
        },
        'activity_feed': [
            {
                'timestamp': datetime.now().isoformat(),
                'user': 'current_user',
                'action': 'created_session',
                'details': f"Created collaboration session: {session_config.get('name', 'ML Collaboration Session')}"
            }
        ]
    }
    
    # Store session
    with sqlite3.connect(user_ml.db_path) as conn:
        conn.execute("""
            INSERT INTO collaboration_sessions (session_id, name, participants, shared_resources, activity_log)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            session_data['name'],
            json.dumps(session_data['participants']),
            json.dumps(session_data['shared_resources']),
            json.dumps(session_data['activity_feed'])
        ))
        conn.commit()
    
    return session_data

@app.get("/api/smart/recommendations")
async def get_smart_recommendations():
    """Get AI-powered recommendations for ML workflows and optimizations"""
    recommendations = {
        'urgent': [
            {
                'type': 'performance',
                'title': 'Model Performance Decline Detected',
                'description': 'Your sales prediction model accuracy has dropped to 78% (was 85%)',
                'action': 'Retrain model with recent data',
                'priority': 'high',
                'estimated_time': '15 minutes'
            }
        ],
        'opportunities': [
            {
                'type': 'new_model',
                'title': 'Customer Churn Prediction Opportunity',
                'description': 'Based on your data patterns, a churn prediction model could save $50k annually',
                'action': 'Start churn prediction workflow',
                'priority': 'medium',
                'estimated_value': '$50,000/year'
            },
            {
                'type': 'optimization',
                'title': 'Data Pipeline Optimization',
                'description': 'Your data processing could be 40% faster with feature caching',
                'action': 'Enable intelligent caching',
                'priority': 'low',
                'estimated_savings': '40% faster processing'
            }
        ],
        'insights': [
            {
                'type': 'trend',
                'title': 'Model Usage Pattern Insight',
                'description': 'Peak ML inference requests occur 2-4 PM daily',
                'suggestion': 'Consider auto-scaling during peak hours'
            },
            {
                'type': 'data_quality',
                'title': 'Data Quality Score: 92%',
                'description': 'Your data quality is excellent. Missing values: 2.1%',
                'suggestion': 'Continue current data preprocessing practices'
            }
        ]
    }
    
    return recommendations

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "user-friendly-ml",
        "query_templates": len(user_ml.query_templates),
        "supported_types": list(QueryType),
        "supported_data": list(DataType),
        "features": {
            "natural_language": True,
            "no_code_models": True,
            "guided_workflows": True,
            "visual_dashboard": True
        }
    }

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8610))
    uvicorn.run(app, host="0.0.0.0", port=port)