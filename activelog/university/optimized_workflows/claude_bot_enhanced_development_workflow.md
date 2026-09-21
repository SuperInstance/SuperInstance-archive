# 🚀 CLAUDE BOT ENHANCED DEVELOPMENT WORKFLOW
**SuperInstance.AI - 300% Productivity Enhancement Guide**

## ⚡ CORE PRINCIPLE
**Always analyze before you code.** Use coder bots to understand systems instantly, then apply your strategic thinking for solutions.

---

## 📋 STANDARD DEVELOPMENT WORKFLOW (5 Steps)

### **Step 1: Service Analysis (30 seconds)**
```bash
# Before touching ANY service, always run
cd /home/activeloguser/activelog/dev-tools/coder-bots
./bots/code-analyzer/analyze-service.py --service [SERVICE_NAME]
```

**What this gives you:**
- ✅ Health Score (0-10) - tells you service quality
- ✅ Complexity Score - shows how hard changes will be  
- ✅ Architecture Patterns - FastAPI, async, validation, etc.
- ✅ Dependencies - what libraries are used
- ✅ API Endpoints - automatically discovered routes
- ✅ Optimization Suggestions - specific improvements

**Decision Tree:**
- Health Score 8-10: Focus on performance optimization
- Health Score 6-8: Solid base, add features carefully
- Health Score <6: Consider refactoring before major changes

### **Step 2: Performance Baseline (15 seconds)**
```bash
# Quick performance check for any service
python3 << EOF
import requests, time
def check(name, port):
    try:
        start = time.time()
        r = requests.get(f"http://localhost:{port}/health", timeout=2)
        ms = (time.time() - start) * 1000
        print(f"🔍 {name}: {ms:.1f}ms - {'✅ Excellent' if ms < 50 else '⚠️ Optimize' if ms < 200 else '❌ Slow'}")
    except: print(f"❌ {name}: Service offline")

# Check your target service
check("auth", 8001)
check("api-gateway", 8088)
# Add your service here
EOF
```

### **Step 3: Code Changes with Pattern Awareness**
```bash
# Apply insights from analysis to your changes
# Example patterns to follow:

# ✅ FastAPI + Pydantic (if service uses this pattern)
from pydantic import BaseModel
class RequestModel(BaseModel):
    field: str

@app.post("/endpoint")
async def handler(data: RequestModel):
    # Your logic here
    pass

# ✅ Error handling (if service has this pattern)
try:
    # Your code
except Exception as e:
    logger.error(f"Error in operation: {e}")
    raise HTTPException(status_code=500, detail="Internal error")
```

### **Step 4: Quality Gates (Automated)**
```bash
# Run after making changes - these are your quality gates
./bots/code-analyzer/analyze-service.py --service [SERVICE_NAME]  # Health check
python -m flake8 services/[SERVICE_NAME]/                         # Code style
python -m pytest tests/[SERVICE_NAME]/                           # Unit tests
```

**Quality Standards:**
- Health Score should not decrease
- Complexity Score should not increase significantly  
- All tests must pass
- No new linting errors

### **Step 5: Performance Verification**
```bash
# Verify your changes didn't hurt performance
# Repeat Step 2 performance check
# Response times should be similar or better
```

---

## 🎯 SPECIALIZED WORKFLOWS BY TASK TYPE

### **🐛 Bug Fixing Workflow**
1. **Analyze** → Understand service architecture
2. **Profile** → Identify performance impact
3. **Test** → Create reproducer test first
4. **Fix** → Apply minimal change
5. **Verify** → Confirm fix + no regression

### **✨ Feature Addition Workflow**  
1. **Analyze** → Study existing patterns
2. **Design** → Follow service conventions
3. **Test** → Write tests before implementation
4. **Build** → Implement following patterns
5. **Optimize** → Use performance profiling

### **🔧 Optimization Workflow**
1. **Profile** → Baseline performance metrics
2. **Analyze** → Get specific optimization suggestions
3. **Apply** → Implement coder bot recommendations
4. **Measure** → Verify improvements
5. **Document** → Record performance gains

---

## 🏗️ ARCHITECTURE PATTERN RECOGNITION

### **FastAPI Services (Modern Pattern)**
```python
# ✅ Expected structure from analysis
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import asyncio

app = FastAPI()

# Always use Pydantic models
class DataModel(BaseModel):
    field: str

# Use async for better performance  
@app.post("/endpoint")
async def create_item(data: DataModel):
    try:
        # Async database operations
        result = await db_operation(data)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
```

### **Legacy Flask Services (Refactor Opportunity)**
```python
# ⚠️ If analysis shows Flask pattern
# Consider gradual migration to FastAPI for consistency
# But maintain existing patterns until refactor
```

---

## 📊 PERFORMANCE OPTIMIZATION PATTERNS

### **Database Optimization** (Common from analysis)
```python
# If analysis suggests async database operations
import asyncpg

# ✅ Connection pooling
pool = asyncpg.create_pool(database_url, min_size=5, max_size=20)

# ✅ Async operations
async def get_data(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM users WHERE id = $1", user_id)
```

### **Caching Patterns** (From optimization suggestions)
```python
# If analysis suggests Redis caching
import redis
cache = redis.Redis(host='localhost', port=6379)

@lru_cache(maxsize=128)  # Simple function caching
def expensive_computation(param: str):
    # Heavy computation
    return result
```

---

## 🔒 SECURITY PATTERNS (Always Check)

### **Authentication Integration**
```python
# Follow auth service pattern (port 8001)
import jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

### **Input Validation** (Pydantic Pattern)
```python
# Use Pydantic for all input validation
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    email: str
    age: int
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

---

## 📈 SUCCESS METRICS & MONITORING

### **Key Performance Indicators**
- **Development Speed**: 300% faster with coder bot analysis
- **Code Quality**: Health scores >8.0 for all services
- **Response Times**: <50ms for simple endpoints, <200ms complex
- **Error Rates**: <0.1% in production
- **Test Coverage**: >85% for critical paths

### **Continuous Monitoring Commands**
```bash
# Daily health check
for service in auth api-gateway ai-insights user-management; do
    ./bots/code-analyzer/analyze-service.py --service $service | grep "Health Score"
done

# Performance monitoring
curl -s http://localhost:8088/health | jq '.response_time_ms'
```

---

## 🎓 LEARNING & KNOWLEDGE MANAGEMENT

### **Document Your Insights**
```markdown
# Service: [service_name]
# Date: [YYYY-MM-DD]
# Health Score: [X.X]/10
# Key Insight: [One line summary]
# Optimization Applied: [Specific change]
# Performance Impact: [Before → After metrics]
```

### **Share Patterns**
- Add successful patterns to `/university/patterns/`
- Document optimization techniques that work
- Report coder bot suggestions that provided high impact

### **Clean Up Learning Data**
- ❌ Delete: Temporary analysis files, debug logs >1 day old
- ✅ Keep: Health scores, performance benchmarks, successful solutions
- 🔄 Summarize: Long debugging sessions into one-line solutions

---

## 🚨 EMERGENCY TROUBLESHOOTING

### **Service Down Checklist**
1. **Quick Status**: `curl http://localhost:[PORT]/health`
2. **Process Check**: `lsof -i:[PORT]`
3. **Log Analysis**: `docker logs [container]` or check service logs
4. **Coder Bot Analysis**: Analyze service for obvious issues
5. **Dependency Check**: Verify database/external service connections

### **Performance Emergency**
1. **Immediate Profile**: Run performance baseline
2. **Resource Check**: Monitor CPU/memory usage
3. **Database Analysis**: Check for slow queries
4. **Cache Status**: Verify Redis/cache performance
5. **Scale Response**: Add instances if needed

---

## ✅ CHECKLIST FOR EVERY TASK

**Before Starting Any Work:**
- [ ] Run code analysis on target service
- [ ] Check performance baseline
- [ ] Review existing tests
- [ ] Understand service dependencies

**During Development:**
- [ ] Follow detected architecture patterns
- [ ] Apply optimization suggestions from analysis
- [ ] Write tests for new functionality
- [ ] Maintain or improve health scores

**Before Completion:**
- [ ] Verify no performance regression
- [ ] Run quality gates (linting, tests)
- [ ] Document significant insights
- [ ] Clean up temporary files

**🎉 Result: Consistent, high-quality development with 300% productivity boost!**