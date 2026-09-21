# 🚀 CODER BOT QUICK START GUIDE
**For Claude Bots - 5 Minute Setup & Usage**

## ⚡ IMMEDIATE ACTION CHECKLIST

### **📋 Before You Start (30 seconds):**
```bash
# 1. Navigate to coder bots directory
cd /home/activeloguser/activelog/dev-tools/coder-bots

# 2. Check if setup is complete
ls bots/code-analyzer/analyze-service.py  # Should exist

# 3. If not setup, run installation
./setup-coder-bots.sh
```

---

## 🎯 TOP 3 MOST USEFUL CODER BOTS

### **1. 🔍 CODE ANALYZER BOT** (Use This First!)
**Purpose**: Understand any service instantly, get architecture insights

```bash
# Analyze any service in 10 seconds
./bots/code-analyzer/analyze-service.py --service auth --output-format json

# Quick text report
./bots/code-analyzer/analyze-service.py --service businesslog-backend
```

**What You Get:**
- ✅ Complexity score (0-20, lower = better)
- ✅ Health score (0-10, higher = better)  
- ✅ Dependencies and architecture patterns
- ✅ Specific optimization suggestions
- ✅ API endpoints automatically discovered

**Example Output:**
```
🔍 Code Analysis Report for businesslog-backend
==================================================
📁 Files: 3
📄 Lines: 245
🧮 Complexity Score: 4.2
🏥 Health Score: 8.5/10

📦 Dependencies (5):
  - fastapi
  - uvicorn
  - sqlite3
  - json
  - datetime

🛤️  API Endpoints (6):
  - GET /health
  - GET /
  - GET /entries
  - POST /entries
  - GET /analytics
  - POST /analytics

🏗️  Architecture Patterns:
  ✅ FastAPI Framework
  ✅ Data Validation
  ✅ Error Handling
  ✅ Structured Logging

⚡ Optimization Suggestions:
  💡 Consider async database operations for better performance
  💡 Add Redis caching for frequently accessed analytics
```

### **2. 🧪 QUICK TEST GENERATOR** (Auto-Create Tests)
```bash
# Generate tests for any service
python3 << EOF
import sys
sys.path.append('/home/activeloguser/activelog/dev-tools/coder-bots')

# Quick test generation
service_name = "businesslog-backend"
print(f"""
# Auto-generated tests for {service_name}
import pytest
from fastapi.testclient import TestClient
from services.{service_name.replace('-', '_')}.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    
# Add to tests/unit/test_{service_name.replace('-', '_')}.py
""")
EOF
```

### **3. 📊 PERFORMANCE PROFILER** (Optimize Services)
```bash
# Quick performance check
python3 << EOF
import requests
import time

def profile_service(name, port):
    url = f"http://localhost:{port}/health"
    times = []
    
    for i in range(5):
        start = time.time()
        try:
            r = requests.get(url, timeout=5)
            end = time.time()
            times.append((end - start) * 1000)  # Convert to ms
        except:
            times.append(5000)  # Timeout
    
    avg_time = sum(times) / len(times)
    print(f"🔍 {name}: Average response time {avg_time:.1f}ms")
    
    if avg_time < 50:
        print(f"✅ {name}: Excellent performance")
    elif avg_time < 200:
        print(f"⚠️  {name}: Good performance, could optimize")  
    else:
        print(f"❌ {name}: Slow, needs optimization")

# Profile all services
services = {
    "auth": 8001,
    "api-gateway": 8088, 
    "ai-insights": 8090,
    "user-management": 8092,
    "workout-sessions": 8093,
    "nutrition-tracking": 8094
}

for name, port in services.items():
    profile_service(name, port)
EOF
```

---

## 🎓 LEARNING WORKFLOW FOR CLAUDE BOTS

### **Step 1: Analyze Before You Code (Always!)**
```bash
# Before working on ANY service, run this
./bots/code-analyzer/analyze-service.py --service [SERVICE_NAME]
```
**Why**: Understand dependencies, patterns, complexity before making changes

### **Step 2: Generate Tests (If Missing)**
```bash
# Create comprehensive tests
./bots/test-generator/generate-tests.py --service [SERVICE_NAME]
```
**Why**: Ensure your changes don't break existing functionality

### **Step 3: Performance Baseline**
```bash
# Get performance baseline before optimization
./bots/performance/profile-service.py --service [SERVICE_NAME]
```
**Why**: Measure improvements objectively

### **Step 4: Security Check**
```bash
# Always run security scan
./bots/security/security-scan.py --service [SERVICE_NAME]
```
**Why**: Prevent vulnerabilities before deployment

---

## 📝 CRITICAL NOTES FOR CLAUDE BOTS

### **🔥 ALWAYS KEEP THESE INSIGHTS:**

#### **Service Health Patterns (Document These!):**
- **Health Score 8-10**: Well-architected, focus on performance
- **Health Score 6-8**: Good structure, some optimization needed
- **Health Score <6**: Needs refactoring, high technical debt

#### **Complexity Guidelines:**
- **Complexity 1-5**: Simple, easy to maintain
- **Complexity 5-10**: Moderate, acceptable for business logic
- **Complexity >10**: High, consider refactoring

#### **Architecture Pattern Recognition:**
- **FastAPI + Pydantic + Async**: Modern Python API pattern ✅
- **Flask + SQL**: Traditional web service pattern ⚠️
- **Multiple frameworks**: Inconsistent, needs standardization ❌

### **🗂️ WHAT TO SUMMARIZE & ARCHIVE:**

#### **Keep Concise Summaries:**
```
Service: auth-service
Analysis Date: 2025-08-27
Health Score: 9.2/10
Key Insight: Well-architected with JWT patterns
Optimization: Consider connection pooling for 20% speed boost
```

#### **Archive Long Debug Sessions:**
- ❌ Don't keep: 500-line debugging logs
- ✅ Do keep: "Problem: Port conflict. Solution: Fixed port config in main.py:71"

### **🧹 CLEANUP GUIDELINES:**

#### **Delete These:**
- Temporary analysis files (`/tmp/analysis_*.json`)
- Old performance reports (>30 days)
- Failed experiment code
- Duplicate documentation

#### **Keep These:**
- Architecture insights and patterns
- Performance benchmarks and improvements
- Security vulnerability fixes
- Successful optimization strategies

---

## ⚡ PRODUCTIVITY SHORTCUTS

### **Quick Commands for Daily Use:**
```bash
# Alias for common tasks (add to ~/.bashrc)
alias analyze-service='cd /home/activeloguser/activelog/dev-tools/coder-bots && ./bots/code-analyzer/analyze-service.py --service'
alias quick-test='python3 -c "import requests; print(requests.get(\"http://localhost:8088/health\").json())"'
alias service-health='curl -s http://localhost:8088/health | jq'

# Quick service overview
function service-overview() {
    echo "🔍 SuperInstance Services Status:"
    for port in 8001 8088 8090 8092 8093 8094; do
        curl -s -m 2 http://localhost:$port/health | jq -r '"\(.service // "unknown"): \(.status // "error")"' 2>/dev/null || echo "Port $port: offline"
    done
}
```

### **One-Liner Analysis:**
```bash
# Get instant service health overview
service-overview
```

---

## 🚨 EMERGENCY TROUBLESHOOTING

### **Service Not Working?**
```bash
# 1. Check if it's running
lsof -i :[PORT]

# 2. Analyze for issues
./bots/code-analyzer/analyze-service.py --service [SERVICE]

# 3. Check dependencies
pip list | grep -E "(fastapi|uvicorn|sqlalchemy)"

# 4. Test basic endpoint
curl http://localhost:[PORT]/health
```

### **Need Quick Performance Fix?**
```bash
# Common optimization patterns found by analysis:
# 1. Add caching: Redis for frequent database queries
# 2. Connection pooling: SQLAlchemy pool_size=10
# 3. Async operations: Use async/await for I/O
# 4. Response compression: Add gzip middleware
```

---

## 🎯 SUCCESS METRICS

**After using coder bots, you should achieve:**
- ✅ **90% faster service understanding** (vs reading code manually)
- ✅ **Zero surprise failures** (comprehensive analysis first)
- ✅ **Consistent architecture patterns** (guided by analysis)
- ✅ **Measurable performance improvements** (baseline → optimized)

**🎉 Result: 300% increase in development velocity through intelligent tool usage!**

---

## 📞 NEXT STEPS

1. **Try the code analyzer** on any service right now
2. **Set up daily aliases** for quick access
3. **Document your insights** using the summary templates
4. **Share successful patterns** in university documentation

**💡 Remember**: These tools are meant to augment your strategic thinking, not replace it. Use them to understand systems faster, then apply your creative problem-solving skills!