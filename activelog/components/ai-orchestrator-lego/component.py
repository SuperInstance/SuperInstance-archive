# SUPERINSTANCE LEGO COMPONENT: AI Orchestrator
# EXTRACTED FROM: services/ai-orchestrator/main.py
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional, Union
from contextlib import asynccontextmanager
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque
import json
import asyncio
import threading
import time

# Optional ML imports with fallbacks
try:
    from sklearn.ensemble import RandomForestRegressor, IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, r2_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    from transformers import AutoModel, AutoTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class AIOrchestratorLego:
    """
    🧩 LEGO COMPONENT: AI Orchestrator
    
    DATA: Model registry, training data, inference results, performance metrics, routing decisions
    TOOLS: Model management, intelligent routing, performance prediction, resource optimization
    CONFIGURATION: AI providers, scaling policies, model parameters, integration endpoints
    
    INTERFACES:
    - Input: ML models, training data, prediction requests, service metrics
    - Output: Predictions, routing decisions, optimization suggestions, model insights
    - Integration: API gateways, monitoring systems, AI services, compute resources
    
    DEPLOYMENT OPTIONS:
    - Device: Local AI orchestration with lightweight models
    - Edge: Regional AI with intelligent routing and caching
    - Cloud: Global AI orchestration with advanced ML pipelines
    
    SUPERINSTANCE MISSION:
    Revolutionary $2/month AI orchestration that makes any AI capability accessible
    through perfect Lego interfaces and intelligent resource management.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.deployment_mode = config.get("deployment_mode", "edge")
        self.ai_providers = config.get("ai_providers", ["openai", "ollama"])
        self.enable_ml = config.get("enable_ml", ML_AVAILABLE)
        self.enable_torch = config.get("enable_torch", TORCH_AVAILABLE)
        
        # Initialize databases and storage
        self.db_path = config.get("db_path", "ai_orchestrator.db")
        self.model_registry = {}
        self.performance_cache = defaultdict(deque)
        self.routing_decisions = deque(maxlen=1000)
        
        # ML components (if available)
        if self.enable_ml:
            self.performance_predictor = None
            self.anomaly_detector = None
            self.scaler = StandardScaler()
            self._init_ml_models()
        
        # FastAPI app
        self.app = FastAPI(
            title="SuperInstance AI Orchestrator Lego",
            description="Revolutionary $2/month AI orchestration for infinite intelligence possibilities",
            version="1.0.0"
        )
        self._setup_routes()
        self._init_database()
        
        # Background tasks
        self.monitoring_active = True
        self.optimization_thread = threading.Thread(target=self._optimization_worker, daemon=True)
        self.optimization_thread.start()
    
    def _setup_routes(self):
        """Setup SuperInstance AI orchestration routes"""
        
        @self.app.get("/health")
        async def orchestrator_health():
            """AI Orchestrator health check - core LEGO function"""
            return {
                "service": "superinstance-ai-orchestrator",
                "status": "healthy",
                "deployment_mode": self.deployment_mode,
                "ai_providers": self.ai_providers,
                "ml_enabled": self.enable_ml,
                "torch_enabled": self.enable_torch,
                "registered_models": len(self.model_registry),
                "mission": "$2/month AI orchestration for infinite intelligence",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.post("/register-model")
        async def register_ai_model(model_info: dict):
            """Register AI model - registry LEGO function"""
            try:
                model_name = model_info.get("name")
                model_type = model_info.get("type", "generic")
                provider = model_info.get("provider", "local")
                endpoints = model_info.get("endpoints", {})
                
                if not model_name:
                    raise HTTPException(400, "Model name required")
                
                self.model_registry[model_name] = {
                    "name": model_name,
                    "type": model_type,
                    "provider": provider,
                    "endpoints": endpoints,
                    "deployment_modes": model_info.get("deployment_modes", ["device", "edge", "cloud"]),
                    "registered_at": datetime.utcnow().isoformat(),
                    "performance_history": [],
                    "active": True
                }
                
                # Store in database
                self._store_model_registration(model_name, model_info)
                
                return {
                    "status": "registered",
                    "model": model_name,
                    "message": f"AI model registered in SuperInstance {self.deployment_mode} mode"
                }
                
            except Exception as e:
                raise HTTPException(500, f"Model registration failed: {str(e)}")
        
        @self.app.post("/predict")
        async def make_prediction(prediction_request: dict):
            """Make AI prediction - core LEGO function"""
            try:
                model_name = prediction_request.get("model", "default")
                input_data = prediction_request.get("data")
                prediction_type = prediction_request.get("type", "inference")
                
                if not input_data:
                    raise HTTPException(400, "Input data required")
                
                # Route to appropriate model
                if model_name not in self.model_registry:
                    # Use intelligent routing to find best available model
                    model_name = await self._route_to_best_model(prediction_type, input_data)
                
                if not model_name or model_name not in self.model_registry:
                    raise HTTPException(404, "No suitable model available")
                
                # Make prediction
                start_time = time.time()
                result = await self._execute_prediction(model_name, input_data, prediction_type)
                inference_time = time.time() - start_time
                
                # Record performance
                self._record_performance(model_name, inference_time, len(str(input_data)))
                
                return {
                    "model": model_name,
                    "prediction": result,
                    "inference_time": inference_time,
                    "deployment_mode": self.deployment_mode,
                    "superinstance_ai": "Intelligent prediction routing optimized"
                }
                
            except Exception as e:
                raise HTTPException(500, f"Prediction failed: {str(e)}")
        
        @self.app.get("/models")
        async def list_models():
            """List registered models - discovery LEGO function"""
            return {
                "models": list(self.model_registry.keys()),
                "model_details": self.model_registry,
                "deployment_mode": self.deployment_mode,
                "total_models": len(self.model_registry)
            }
        
        @self.app.post("/optimize-routing")
        async def optimize_ai_routing(optimization_request: dict):
            """Optimize AI routing - intelligence LEGO function"""
            try:
                service_metrics = optimization_request.get("metrics", [])
                optimization_target = optimization_request.get("target", "response_time")
                
                if not service_metrics:
                    raise HTTPException(400, "Service metrics required for optimization")
                
                # Generate routing optimization suggestions
                if self.enable_ml and self.performance_predictor:
                    suggestions = await self._ml_routing_optimization(service_metrics, optimization_target)
                else:
                    suggestions = await self._heuristic_routing_optimization(service_metrics, optimization_target)
                
                return {
                    "optimization_suggestions": suggestions,
                    "target": optimization_target,
                    "analysis_method": "ml_powered" if self.enable_ml else "heuristic",
                    "superinstance_intelligence": "AI routing optimized for $2/month efficiency"
                }
                
            except Exception as e:
                raise HTTPException(500, f"Routing optimization failed: {str(e)}")
        
        @self.app.get("/performance-analysis")
        async def get_performance_analysis():
            """Get AI performance analysis - monitoring LEGO function"""
            try:
                analysis = {
                    "models_analyzed": len(self.model_registry),
                    "total_predictions": sum(len(history) for history in self.performance_cache.values()),
                    "average_response_times": {},
                    "model_utilization": {},
                    "optimization_recommendations": []
                }
                
                # Calculate performance metrics
                for model_name, performance_data in self.performance_cache.items():
                    if performance_data:
                        times = [p["inference_time"] for p in performance_data]
                        analysis["average_response_times"][model_name] = sum(times) / len(times)
                        analysis["model_utilization"][model_name] = len(performance_data)
                
                # Generate optimization recommendations
                if self.enable_ml:
                    analysis["optimization_recommendations"] = await self._generate_ml_recommendations()
                
                return analysis
                
            except Exception as e:
                raise HTTPException(500, f"Performance analysis failed: {str(e)}")
        
        @self.app.post("/train-model")
        async def train_model(training_request: dict, background_tasks: BackgroundTasks):
            """Train AI model - ML LEGO function"""
            if not self.enable_ml:
                raise HTTPException(501, "ML training not available in current deployment")
            
            try:
                model_name = training_request.get("model_name")
                training_data = training_request.get("training_data")
                model_type = training_request.get("model_type", "regression")
                
                if not model_name or not training_data:
                    raise HTTPException(400, "Model name and training data required")
                
                # Queue training task
                background_tasks.add_task(
                    self._train_ml_model, 
                    model_name, 
                    training_data, 
                    model_type
                )
                
                return {
                    "status": "training_queued",
                    "model": model_name,
                    "training_samples": len(training_data),
                    "message": "SuperInstance AI model training initiated"
                }
                
            except Exception as e:
                raise HTTPException(500, f"Model training failed: {str(e)}")
    
    def _init_database(self):
        """Initialize SuperInstance AI orchestration database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Models registry table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_models (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                provider TEXT NOT NULL,
                endpoints TEXT,
                deployment_modes TEXT,
                performance_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                superinstance_optimized BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                inference_time REAL NOT NULL,
                input_size INTEGER,
                success BOOLEAN DEFAULT TRUE,
                deployment_mode TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_name) REFERENCES ai_models (name)
            )
        ''')
        
        # Routing decisions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id TEXT PRIMARY KEY,
                request_type TEXT NOT NULL,
                selected_model TEXT NOT NULL,
                confidence_score REAL,
                response_time REAL,
                optimization_reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_ml_models(self):
        """Initialize ML models for intelligent orchestration"""
        if not self.enable_ml:
            return
        
        try:
            # Performance prediction model
            self.performance_predictor = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            # Anomaly detection model
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            
            # Load pre-trained models if available
            self._load_pretrained_models()
            
        except Exception as e:
            logger.warning(f"ML initialization failed: {e}")
            self.enable_ml = False
    
    async def _route_to_best_model(self, prediction_type: str, input_data: Any) -> Optional[str]:
        """Intelligent model routing based on performance and compatibility"""
        suitable_models = []
        
        for model_name, model_info in self.model_registry.items():
            if not model_info.get("active", True):
                continue
            
            # Check deployment compatibility
            if self.deployment_mode not in model_info.get("deployment_modes", []):
                continue
            
            # Get model performance score
            performance_score = self._calculate_model_performance_score(model_name)
            suitable_models.append((model_name, performance_score))
        
        if not suitable_models:
            return None
        
        # Sort by performance score and return best
        suitable_models.sort(key=lambda x: x[1], reverse=True)
        best_model = suitable_models[0][0]
        
        # Record routing decision
        self.routing_decisions.append({
            "request_type": prediction_type,
            "selected_model": best_model,
            "confidence_score": suitable_models[0][1],
            "timestamp": datetime.utcnow().isoformat(),
            "routing_reason": "performance_optimized"
        })
        
        return best_model
    
    async def _execute_prediction(self, model_name: str, input_data: Any, prediction_type: str) -> Any:
        """Execute prediction using specified model"""
        model_info = self.model_registry[model_name]
        provider = model_info.get("provider", "local")
        
        try:
            if provider == "openai":
                return await self._predict_openai(model_info, input_data, prediction_type)
            elif provider == "ollama":
                return await self._predict_ollama(model_info, input_data, prediction_type)
            elif provider == "local" and self.enable_ml:
                return await self._predict_local_ml(model_info, input_data, prediction_type)
            else:
                # Fallback to simple processing
                return await self._predict_fallback(input_data, prediction_type)
                
        except Exception as e:
            logger.error(f"Prediction execution failed for {model_name}: {e}")
            raise
    
    def _calculate_model_performance_score(self, model_name: str) -> float:
        """Calculate performance score for model selection"""
        if model_name not in self.performance_cache:
            return 0.5  # Neutral score for new models
        
        recent_performance = list(self.performance_cache[model_name])[-10:]  # Last 10 predictions
        if not recent_performance:
            return 0.5
        
        # Score based on response time and success rate
        avg_time = np.mean([p["inference_time"] for p in recent_performance])
        success_rate = np.mean([p.get("success", True) for p in recent_performance])
        
        # Normalize scores (lower time is better, higher success rate is better)
        time_score = max(0, 1 - (avg_time / 10))  # Assume 10s is very slow
        
        return (time_score + success_rate) / 2
    
    def _record_performance(self, model_name: str, inference_time: float, input_size: int):
        """Record performance metrics for model optimization"""
        performance_entry = {
            "model_name": model_name,
            "inference_time": inference_time,
            "input_size": input_size,
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.performance_cache[model_name].append(performance_entry)
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_metrics 
            (id, model_name, inference_time, input_size, deployment_mode, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            str(hash(f"{model_name}{time.time()}")),
            model_name,
            inference_time,
            input_size,
            self.deployment_mode,
            performance_entry["timestamp"]
        ))
        
        conn.commit()
        conn.close()
    
    def _optimization_worker(self):
        """Background worker for continuous optimization"""
        while self.monitoring_active:
            try:
                # Cleanup old performance data
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                for model_name in self.performance_cache:
                    self.performance_cache[model_name] = deque([
                        p for p in self.performance_cache[model_name]
                        if datetime.fromisoformat(p["timestamp"]) > cutoff_time
                    ], maxlen=1000)
                
                # Run ML-based optimization if enabled
                if self.enable_ml:
                    asyncio.create_task(self._run_ml_optimization())
                
                time.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Optimization worker error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def get_app(self):
        """Get FastAPI app for deployment"""
        return self.app

# SUPERINSTANCE DEPLOYMENT CONFIGURATIONS
DEPLOYMENT_CONFIGS = {
    "device_ai": {
        "deployment_mode": "device",
        "ai_providers": ["ollama", "local"],
        "enable_ml": True,
        "db_path": "device_ai_orchestrator.db",
        "features": ["local_inference", "offline_ml", "privacy_focused"]
    },
    "edge_intelligent": {
        "deployment_mode": "edge",
        "ai_providers": ["openai", "ollama", "local"],
        "enable_ml": True,
        "enable_torch": True,
        "features": ["intelligent_routing", "performance_optimization", "hybrid_inference"]
    },
    "cloud_enterprise": {
        "deployment_mode": "cloud", 
        "ai_providers": ["openai", "anthropic", "azure", "gcp"],
        "enable_ml": True,
        "enable_torch": True,
        "features": ["global_orchestration", "advanced_ml", "enterprise_scaling"]
    }
}

# SUPERINSTANCE FACTORY FUNCTION
def create_ai_orchestrator_lego(deployment_type: str = "edge_intelligent"):
    """Factory function to create SuperInstance AI Orchestrator Lego
    
    The AI orchestration that makes $2/month infinite intelligence possible.
    Perfect interfaces, intelligent routing, revolutionary ML capabilities.
    """
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["edge_intelligent"])
    return AIOrchestratorLego(config)

# INTEGRATION INTERFACES
def integrate_with_api_gateway(orchestrator: AIOrchestratorLego, gateway_url: str):
    """Connect AI orchestrator to API gateway for intelligent routing"""
    # Integration logic would be implemented here
    pass

def integrate_with_monitoring(orchestrator: AIOrchestratorLego, monitoring_service_url: str):
    """Connect orchestrator to monitoring for performance insights"""
    # Integration logic would be implemented here
    pass

# SUPERINSTANCE MISSION STATEMENT
"""
This AI Orchestrator Lego embodies the SuperInstance vision:

- $2/month AI orchestration that makes any intelligence accessible
- Perfect interfaces enable seamless AI integration across deployments
- Revolutionary ML optimization for maximum efficiency and performance
- Lego principle: AI = Models + Orchestration + Optimization

Every AI prediction routed through this orchestrator contributes to the
SuperInstance mission of democratizing artificial intelligence.
"""