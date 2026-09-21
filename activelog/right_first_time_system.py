#!/usr/bin/env python3
"""
Right-First-Time Quality System
Prevents common mistakes by injecting best practices before implementation
"""

import json
from pathlib import Path
from datetime import datetime

class RightFirstTimeSystem:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        self.quality_templates = self.create_quality_templates()
        
    def create_quality_templates(self):
        """Create templates for common implementation patterns"""
        return {
            "k8s_deployment": {
                "checklist": [
                    "Resource limits defined (CPU/memory)",
                    "Health check endpoints configured", 
                    "Environment variables documented",
                    "Service discovery labels applied",
                    "Network policies considered"
                ],
                "common_mistakes": [
                    "Missing resource limits (causes node instability)",
                    "No health checks (prevents proper scaling)",
                    "Hard-coded configurations (breaks portability)",
                    "Missing service labels (breaks discovery)"
                ],
                "template_file": "k8s_deployment_template.yaml",
                "validation_commands": [
                    "kubectl apply --dry-run=client -f deployment.yaml",
                    "kubectl describe deployment <name>",
                    "curl http://service:port/health"
                ]
            },
            
            "auth_integration": {
                "checklist": [
                    "JWT secret key configured consistently",
                    "Token expiry times set appropriately", 
                    "CORS headers configured for cross-origin",
                    "Error handling for invalid/expired tokens",
                    "Rate limiting on auth endpoints"
                ],
                "common_mistakes": [
                    "Inconsistent JWT secrets across services",
                    "Missing CORS configuration (breaks frontend)",
                    "No rate limiting (vulnerable to brute force)",
                    "Poor error messages (security risk)"
                ],
                "template_file": "jwt_middleware_template.py",
                "validation_commands": [
                    "curl -X POST /auth/login -d '{\"username\":\"test\"}'",
                    "curl -H 'Authorization: Bearer <token>' /auth/verify"
                ]
            },
            
            "database_setup": {
                "checklist": [
                    "Connection pooling configured",
                    "Database migrations planned",
                    "Indexes defined for performance",
                    "Backup strategy documented",
                    "Schema validation implemented"
                ],
                "common_mistakes": [
                    "No connection pooling (resource exhaustion)",
                    "Missing indexes (poor query performance)",
                    "No migration rollback plan (risky deployments)",
                    "No foreign key constraints (data integrity issues)"
                ],
                "template_file": "database_setup_template.sql",
                "validation_commands": [
                    "psql -c '\\dt' # List tables",
                    "psql -c '\\d+ table_name' # Check indexes",
                    "psql -c 'EXPLAIN ANALYZE SELECT...' # Query performance"
                ]
            },
            
            "service_communication": {
                "checklist": [
                    "Circuit breaker patterns implemented",
                    "Retry logic with exponential backoff",
                    "Timeout configurations appropriate",
                    "Service discovery mechanism working",
                    "Load balancing configured"
                ],
                "common_mistakes": [
                    "No timeout handling (hanging requests)",
                    "Linear retry (amplifies failures)",
                    "Hard-coded service URLs (breaks scalability)",
                    "No circuit breakers (cascade failures)"
                ],
                "template_file": "service_client_template.py",
                "validation_commands": [
                    "curl http://service1/api/test",
                    "kubectl logs deployment/service1",
                    "kubectl get endpoints service1"
                ]
            }
        }
    
    def detect_implementation_intent(self, recent_updates):
        """Detect what the bot is about to implement"""
        intents = []
        
        for update in recent_updates:
            update_lower = update.lower()
            
            if any(keyword in update_lower for keyword in ['k8s', 'kubernetes', 'deploy', 'manifest']):
                intents.append('k8s_deployment')
            
            if any(keyword in update_lower for keyword in ['auth', 'jwt', 'token', 'login']):
                intents.append('auth_integration')
                
            if any(keyword in update_lower for keyword in ['database', 'postgres', 'schema', 'migration']):
                intents.append('database_setup')
                
            if any(keyword in update_lower for keyword in ['service', 'api', 'client', 'communication']):
                intents.append('service_communication')
        
        return list(set(intents))  # Remove duplicates
    
    def generate_preemptive_guidance(self, intent):
        """Generate guidance before implementation starts"""
        if intent not in self.quality_templates:
            return None
        
        template = self.quality_templates[intent]
        
        guidance = f"""
## 🎯 RIGHT-FIRST-TIME GUIDANCE: {intent.replace('_', ' ').title()}

### PRE-IMPLEMENTATION CHECKLIST:
"""
        
        for item in template['checklist']:
            guidance += f"- [ ] {item}\n"
        
        guidance += "\n### COMMON MISTAKES TO AVOID:\n"
        for mistake in template['common_mistakes']:
            guidance += f"⚠️  {mistake}\n"
        
        if 'template_file' in template:
            guidance += f"\n### READY TEMPLATE: `{template['template_file']}`\n"
        
        guidance += "\n### VALIDATION COMMANDS:\n"
        for cmd in template['validation_commands']:
            guidance += f"```bash\n{cmd}\n```\n"
        
        return guidance
    
    def create_implementation_templates(self):
        """Create actual implementation templates"""
        templates_created = []
        
        # K8s Deployment Template
        k8s_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service_name}
  labels:
    app: {service_name}
    domain: {domain}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {service_name}
  template:
    metadata:
      labels:
        app: {service_name}
    spec:
      containers:
      - name: {service_name}
        image: {image}
        ports:
        - containerPort: {port}
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: PORT
          value: "{port}"
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
spec:
  selector:
    app: {service_name}
  ports:
  - port: {port}
    targetPort: {port}
"""
        
        template_file = self.base_path / "k8s_deployment_template.yaml"
        with open(template_file, 'w') as f:
            f.write(k8s_template)
        templates_created.append(template_file)
        
        # JWT Middleware Template
        jwt_template = '''
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_token(token: str = Depends(security)):
    """JWT token verification middleware"""
    try:
        payload = jwt.decode(
            token.credentials, 
            SECRET_KEY, 
            algorithms=["HS256"]
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail="Token expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=401, 
            detail="Invalid token"
        )

# Usage in endpoint:
# @app.get("/protected")
# async def protected_route(user_id: str = Depends(verify_token)):
#     return {"user_id": user_id, "message": "Access granted"}
'''
        
        jwt_file = self.base_path / "jwt_middleware_template.py"
        with open(jwt_file, 'w') as f:
            f.write(jwt_template)
        templates_created.append(jwt_file)
        
        # Database Setup Template
        db_template = '''-- Database Setup Best Practices Template

-- Connection pool configuration (SQLAlchemy)
-- engine = create_engine(
--     DATABASE_URL,
--     pool_size=10,
--     max_overflow=20,
--     pool_timeout=30,
--     pool_recycle=3600
-- )

-- Example table with proper constraints and indexes
CREATE TABLE example_table (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(name) > 0),
    email TEXT UNIQUE NOT NULL CHECK (email LIKE '%@%'),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_example_user_id ON example_table(user_id);
CREATE INDEX idx_example_status ON example_table(status) WHERE status = 'active';
CREATE INDEX idx_example_created ON example_table(created_at DESC);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_example_updated_at 
    BEFORE UPDATE ON example_table 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
'''
        
        db_file = self.base_path / "database_setup_template.sql"
        with open(db_file, 'w') as f:
            f.write(db_template)
        templates_created.append(db_file)
        
        return templates_created
    
    def inject_preemptive_guidance(self, bot_name, intent):
        """Inject right-first-time guidance into bot log"""
        guidance = self.generate_preemptive_guidance(intent)
        if not guidance:
            return False
        
        bot_log_file = self.base_path / f"bot_{bot_name}_log.txt"
        
        if not bot_log_file.exists():
            return False
        
        injection_content = f"""
## 🎯 RIGHT-FIRST-TIME SYSTEM ACTIVATED - {datetime.now().strftime('%H:%M')}

{guidance}

### SYSTEM NOTE: This guidance was injected proactively to prevent common issues
### TIMING: Before implementation begins (predictive quality assurance)
"""
        
        try:
            with open(bot_log_file, 'r') as f:
                lines = f.readlines()
            
            # Insert after "ACTIVE PUZZLES" section
            insert_index = -1
            for i, line in enumerate(lines):
                if "## ACTIVE PUZZLES:" in line:
                    insert_index = i + 1
                    break
            
            if insert_index > 0:
                lines.insert(insert_index, injection_content + "\n")
                
                with open(bot_log_file, 'w') as f:
                    f.writelines(lines)
                
                return True
        except Exception as e:
            print(f"Error injecting guidance to {bot_name}: {e}")
        
        return False

def main():
    """Run right-first-time quality system"""
    system = RightFirstTimeSystem()
    
    print("=== Right-First-Time Quality System ===")
    
    # Create implementation templates
    templates = system.create_implementation_templates()
    print(f"✅ Created {len(templates)} implementation templates")
    
    # Analyze recent updates for implementation intent
    try:
        with open("/home/activeloguser/activelog/micro_updates.log", 'r') as f:
            recent_updates = f.readlines()[-5:]  # Last 5 updates
        
        intents = system.detect_implementation_intent(recent_updates)
        print(f"🎯 Detected implementation intents: {intents}")
        
        # Example: inject guidance for detected intents
        guidance_injected = 0
        for intent in intents:
            # This would normally inject into appropriate bot logs
            print(f"   📋 Would inject {intent} guidance proactively")
            guidance_injected += 1
        
        print(f"✅ {guidance_injected} proactive guidance items ready for injection")
        
    except FileNotFoundError:
        print("ℹ️  No recent updates to analyze")
    
    return len(templates)

if __name__ == "__main__":
    main()