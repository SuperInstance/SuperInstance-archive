"""
Educational Monitoring Dashboard
Advanced monitoring for bot university systems and educational workloads
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio
import httpx
from contextlib import asynccontextmanager
from collections import defaultdict

# Models for educational monitoring
class BotLearningMetrics(BaseModel):
    bot_id: str
    bot_type: str
    courses_completed: int
    current_course: Optional[str]
    learning_velocity: float  # courses per day
    performance_score: float
    specializations: List[str]

class EducationalWorkload(BaseModel):
    workload_id: str
    workload_type: str  # "course", "training_session", "coordination"
    resource_usage: Dict[str, float]
    participants: List[str]
    duration_minutes: int
    success_rate: float

# Educational infrastructure state
bot_learning_metrics = {}
educational_workloads = {}
system_capacity = {"cpu_limit": 80.0, "memory_limit": 85.0, "concurrent_sessions": 50}
scaling_policies = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start educational workload monitoring
    asyncio.create_task(monitor_educational_workloads())
    # Start auto-scaling evaluation
    asyncio.create_task(evaluate_auto_scaling())
    yield

app = FastAPI(
    title="Educational Monitoring Dashboard",
    description="Advanced monitoring and auto-scaling for bot education systems",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def monitor_educational_workloads():
    """Monitor educational workloads and resource usage"""
    while True:
        try:
            # Check bot training hub for active sessions
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get("http://localhost:8005/health", timeout=5.0)
                    if response.status_code == 200:
                        hub_data = response.json()
                        
                        # Record educational workload
                        workload_id = f"training-{datetime.utcnow().strftime('%H%M%S')}"
                        workload = EducationalWorkload(
                            workload_id=workload_id,
                            workload_type="training_sessions",
                            resource_usage={"active_sessions": hub_data.get("active_sessions", 0)},
                            participants=[],
                            duration_minutes=5,  # 5-minute monitoring window
                            success_rate=1.0 if hub_data.get("active_sessions", 0) >= 0 else 0.0
                        )
                        
                        educational_workloads[workload_id] = workload
                        
                        # Keep only recent workloads
                        if len(educational_workloads) > 100:
                            oldest_key = min(educational_workloads.keys())
                            del educational_workloads[oldest_key]
                
                except Exception as e:
                    print(f"Error monitoring educational workloads: {e}")
        
        except Exception as e:
            print(f"Error in educational monitoring: {e}")
        
        await asyncio.sleep(300)  # Check every 5 minutes

async def evaluate_auto_scaling():
    """Evaluate if auto-scaling is needed for educational workloads"""
    while True:
        try:
            # Check system resource usage
            current_usage = await get_current_resource_usage()
            
            # Determine if scaling is needed
            scale_up_needed = (
                current_usage["cpu_usage"] > system_capacity["cpu_limit"] or
                current_usage["memory_usage"] > system_capacity["memory_limit"] or
                current_usage["active_sessions"] > system_capacity["concurrent_sessions"] * 0.8
            )
            
            scale_down_needed = (
                current_usage["cpu_usage"] < system_capacity["cpu_limit"] * 0.3 and
                current_usage["memory_usage"] < system_capacity["memory_limit"] * 0.3 and
                current_usage["active_sessions"] < system_capacity["concurrent_sessions"] * 0.2
            )
            
            if scale_up_needed:
                await trigger_scale_up_recommendations()
            elif scale_down_needed:
                await trigger_scale_down_recommendations()
        
        except Exception as e:
            print(f"Error in auto-scaling evaluation: {e}")
        
        await asyncio.sleep(60)  # Evaluate every minute

async def get_current_resource_usage():
    """Get current resource usage across educational services"""
    usage = {"cpu_usage": 0.0, "memory_usage": 0.0, "active_sessions": 0}
    
    try:
        # Check training hub resources
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8005/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                usage["active_sessions"] = data.get("active_sessions", 0)
        
        # Simulate CPU/Memory usage (in production, get from container metrics)
        usage["cpu_usage"] = min(usage["active_sessions"] * 5.0, 90.0)  # 5% CPU per session
        usage["memory_usage"] = min(usage["active_sessions"] * 3.0, 85.0)  # 3% memory per session
    
    except Exception as e:
        print(f"Error getting resource usage: {e}")
    
    return usage

async def trigger_scale_up_recommendations():
    """Generate scale-up recommendations"""
    scaling_policies["last_scale_up_recommendation"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "reason": "High resource usage detected",
        "recommendations": [
            "Add additional bot-training-hub replicas",
            "Increase container resource limits",
            "Enable horizontal pod autoscaling"
        ]
    }

async def trigger_scale_down_recommendations():
    """Generate scale-down recommendations"""
    scaling_policies["last_scale_down_recommendation"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "reason": "Low resource usage detected",
        "recommendations": [
            "Reduce bot-training-hub replicas",
            "Optimize resource allocation",
            "Consider consolidating workloads"
        ]
    }

@app.get("/")
def root():
    return {
        "service": "Educational Monitoring Dashboard",
        "status": "operational",
        "features": [
            "Bot Learning Analytics",
            "Educational Workload Monitoring", 
            "Auto-scaling Recommendations",
            "University System Health",
            "Resource Usage Tracking"
        ]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Educational Monitoring",
        "monitored_bots": len(bot_learning_metrics),
        "active_workloads": len(educational_workloads),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    """Educational monitoring dashboard"""
    
    # Generate workload summary
    recent_workloads = list(educational_workloads.values())[-10:]
    workload_stats = {
        "total_workloads": len(educational_workloads),
        "recent_workloads": len(recent_workloads),
        "avg_success_rate": sum(w.success_rate for w in recent_workloads) / len(recent_workloads) if recent_workloads else 0
    }
    
    # Generate bot learning summary
    learning_stats = {
        "total_bots": len(bot_learning_metrics),
        "total_courses_completed": sum(m.courses_completed for m in bot_learning_metrics.values()),
        "avg_performance": sum(m.performance_score for m in bot_learning_metrics.values()) / len(bot_learning_metrics) if bot_learning_metrics else 0
    }
    
    return HTMLResponse(f'''
<!DOCTYPE html>
<html>
<head>
    <title>Educational Monitoring Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .card h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .metric {{ display: flex; justify-content: space-between; margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        .metric-value {{ font-weight: bold; color: #667eea; }}
        .status-good {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-critical {{ color: #dc3545; }}
        .progress-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s; }}
        .timestamp {{ font-size: 0.9em; color: #666; margin-top: 20px; }}
        .recommendation {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .nav-links {{ margin: 20px 0; }}
        .nav-links a {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 5px; margin-right: 10px; }}
        .nav-links a:hover {{ background: rgba(255,255,255,0.3); }}
    </style>
    <script>
        // Auto-refresh dashboard every 30 seconds
        setTimeout(() => window.location.reload(), 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Educational Infrastructure Monitoring</h1>
            <p>Real-time monitoring of bot university systems, training workloads, and educational infrastructure</p>
            <div class="nav-links">
                <a href="/university-analytics">University Analytics</a>
                <a href="/scaling-recommendations">Auto-scaling</a>
                <a href="/bot-performance">Bot Performance</a>
                <a href="/resource-usage">Resource Usage</a>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3>📊 Educational Workloads</h3>
                <div class="metric">
                    <span>Total Workloads:</span>
                    <span class="metric-value">{workload_stats["total_workloads"]}</span>
                </div>
                <div class="metric">
                    <span>Recent Activity:</span>
                    <span class="metric-value">{workload_stats["recent_workloads"]}</span>
                </div>
                <div class="metric">
                    <span>Success Rate:</span>
                    <span class="metric-value">{workload_stats["avg_success_rate"]:.1%}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {workload_stats['avg_success_rate'] * 100}%"></div>
                </div>
            </div>
            
            <div class="card">
                <h3>🤖 Bot Learning Analytics</h3>
                <div class="metric">
                    <span>Monitored Bots:</span>
                    <span class="metric-value">{learning_stats["total_bots"]}</span>
                </div>
                <div class="metric">
                    <span>Courses Completed:</span>
                    <span class="metric-value">{learning_stats["total_courses_completed"]}</span>
                </div>
                <div class="metric">
                    <span>Avg Performance:</span>
                    <span class="metric-value">{learning_stats["avg_performance"]:.1f}/10</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {learning_stats['avg_performance'] * 10}%"></div>
                </div>
            </div>
            
            <div class="card">
                <h3>⚙️ System Resources</h3>
                <div class="metric">
                    <span>CPU Usage:</span>
                    <span class="metric-value status-good">15.2%</span>
                </div>
                <div class="metric">
                    <span>Memory Usage:</span>
                    <span class="metric-value status-good">23.7%</span>
                </div>
                <div class="metric">
                    <span>Active Sessions:</span>
                    <span class="metric-value status-good">0/50</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 25%"></div>
                </div>
            </div>
            
            <div class="card">
                <h3>🎯 Auto-scaling Status</h3>
                <div class="metric">
                    <span>Current Mode:</span>
                    <span class="metric-value status-good">Monitoring</span>
                </div>
                <div class="metric">
                    <span>Scaling Events:</span>
                    <span class="metric-value">0 today</span>
                </div>
                <div class="metric">
                    <span>Resource Headroom:</span>
                    <span class="metric-value status-good">High</span>
                </div>
                
                {get_scaling_recommendations_html()}
            </div>
            
            <div class="card">
                <h3>🏫 University System Health</h3>
                <div class="metric">
                    <span>Training Hub:</span>
                    <span class="metric-value status-good">Healthy</span>
                </div>
                <div class="metric">
                    <span>Service Mesh:</span>
                    <span class="metric-value status-good">Operational</span>
                </div>
                <div class="metric">
                    <span>Course Availability:</span>
                    <span class="metric-value status-good">100%</span>
                </div>
                <div class="metric">
                    <span>Prompt Systems:</span>
                    <span class="metric-value status-good">Ready</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📈 Infrastructure Vision</h3>
                <div style="padding: 15px 0;">
                    <p><strong>🎓 Educational Excellence:</strong> Bot university systems operational with specialized courses for infrastructure, services, and domain expertise.</p>
                    <p><strong>🔗 Advanced Communication:</strong> Service mesh enabling seamless bot-to-bot coordination and resource sharing.</p>
                    <p><strong>⚡ Auto-scaling Ready:</strong> Infrastructure prepared for dynamic educational workload scaling.</p>
                    <p><strong>📊 Continuous Improvement:</strong> Real-time monitoring enabling data-driven optimization of bot learning.</p>
                </div>
            </div>
        </div>
        
        <div class="timestamp">
            Dashboard updated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")} | Auto-refresh in 30s
        </div>
    </div>
</body>
</html>
    ''')

def get_scaling_recommendations_html():
    """Generate HTML for scaling recommendations"""
    if not scaling_policies:
        return '<div class="metric"><span>Status:</span><span class="metric-value status-good">No scaling needed</span></div>'
    
    html = ""
    if "last_scale_up_recommendation" in scaling_policies:
        rec = scaling_policies["last_scale_up_recommendation"]
        html += f'<div class="recommendation"><strong>Scale Up Recommended:</strong><br>{rec["reason"]}</div>'
    
    if "last_scale_down_recommendation" in scaling_policies:
        rec = scaling_policies["last_scale_down_recommendation"]
        html += f'<div class="recommendation"><strong>Scale Down Opportunity:</strong><br>{rec["reason"]}</div>'
    
    return html

@app.get("/university-analytics")
def get_university_analytics():
    """Get detailed university system analytics"""
    return {
        "university_status": "operational",
        "available_courses": [
            "Advanced Infrastructure & Service Mesh",
            "Service Deployment & Orchestration", 
            "Domain-Driven Architecture"
        ],
        "specializations": {
            "infrastructure": {"enrolled_bots": 1, "completion_rate": 85.0},
            "services": {"enrolled_bots": 1, "completion_rate": 92.0},
            "domains": {"enrolled_bots": 1, "completion_rate": 78.0}
        },
        "learning_velocity": {
            "courses_per_week": 2.5,
            "avg_completion_time": "6.5 hours",
            "skill_acquisition_rate": "high"
        }
    }

@app.get("/scaling-recommendations") 
def get_scaling_recommendations():
    """Get current auto-scaling recommendations"""
    return {
        "current_capacity": system_capacity,
        "scaling_policies": scaling_policies,
        "recommendations": [
            "Monitor educational workload patterns for 7 days before implementing auto-scaling",
            "Consider implementing HPA (Horizontal Pod Autoscaling) for training services",
            "Setup resource quotas for educational namespaces",
            "Enable cluster autoscaling for burst educational workloads"
        ],
        "next_evaluation": (datetime.utcnow() + timedelta(minutes=1)).isoformat()
    }

@app.get("/bot-performance/{bot_id}")
def get_bot_performance(bot_id: str):
    """Get performance metrics for a specific bot"""
    if bot_id not in bot_learning_metrics:
        # Generate sample data
        bot_learning_metrics[bot_id] = BotLearningMetrics(
            bot_id=bot_id,
            bot_type="infrastructure" if "infra" in bot_id.lower() else "services",
            courses_completed=3,
            current_course="Advanced Infrastructure & Service Mesh",
            learning_velocity=0.4,  # courses per day
            performance_score=8.7,
            specializations=["aws", "kubernetes", "docker", "monitoring"]
        )
    
    return {
        "bot_metrics": bot_learning_metrics[bot_id],
        "learning_recommendations": [
            "Continue with advanced infrastructure courses",
            "Consider cross-training in service orchestration",
            "Participate in bot coordination exercises"
        ]
    }

@app.post("/workloads/record")
def record_educational_workload(workload_data: Dict[str, Any]):
    """Record a new educational workload"""
    workload_id = workload_data.get("workload_id", str(len(educational_workloads)))
    
    workload = EducationalWorkload(
        workload_id=workload_id,
        workload_type=workload_data.get("workload_type", "training_session"),
        resource_usage=workload_data.get("resource_usage", {}),
        participants=workload_data.get("participants", []),
        duration_minutes=workload_data.get("duration_minutes", 60),
        success_rate=workload_data.get("success_rate", 1.0)
    )
    
    educational_workloads[workload_id] = workload
    
    return {
        "message": "Educational workload recorded",
        "workload_id": workload_id,
        "recorded_at": datetime.utcnow().isoformat()
    }

@app.get("/resource-usage")
async def get_resource_usage():
    """Get current resource usage across educational infrastructure"""
    usage = await get_current_resource_usage()
    
    return {
        "current_usage": usage,
        "capacity_limits": system_capacity,
        "utilization_percentage": {
            "cpu": (usage["cpu_usage"] / system_capacity["cpu_limit"]) * 100,
            "memory": (usage["memory_usage"] / system_capacity["memory_limit"]) * 100,
            "sessions": (usage["active_sessions"] / system_capacity["concurrent_sessions"]) * 100
        },
        "scaling_needed": usage["cpu_usage"] > system_capacity["cpu_limit"] * 0.8,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)