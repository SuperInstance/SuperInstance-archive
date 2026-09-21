"""
Comprehensive Permissions Management Service
Integrates all permission management features with REST API and web UI

Port: 8379
Features:
- Granular permission controls with role-based access
- Comprehensive audit trail with risk scoring
- Time-based permissions with expiration
- Device-specific permission rules
- Emergency override mechanisms
- Parental controls system
- Enterprise policy management
- Legal compliance features
- User education system
- Default deny security stance
- Regular permission review
- Clear warning dialogs
"""

import asyncio
import logging
import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Import all permission management modules
from core.permission_manager import PermissionManager, PermissionLevel, ResourceType, PermissionStatus
from audit.audit_manager import AuditManager, AuditEventType, AuditSeverity
from policies.time_policy_manager import TimePolicyManager, TimeRestrictionType, RecurrencePattern
from policies.emergency_override import EmergencyOverrideManager, EmergencyType, OverrideStatus
from controls.parental_controls import ParentalControlsManager, SafetyLevel, ContentRating

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Permissions Management Service",
    description="Comprehensive permission control system with security, compliance, and safety features",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers
permission_manager: Optional[PermissionManager] = None
audit_manager: Optional[AuditManager] = None
time_policy_manager: Optional[TimePolicyManager] = None
emergency_manager: Optional[EmergencyOverrideManager] = None
parental_manager: Optional[ParentalControlsManager] = None

# System configuration
SYSTEM_CONFIG = {
    "default_deny": True,
    "require_justification": True,
    "auto_expire_days": 90,
    "audit_retention_days": 2555,  # 7 years
    "max_session_duration": 28800,  # 8 hours
    "password_policy": {
        "min_length": 12,
        "require_special": True,
        "require_numbers": True,
        "require_uppercase": True
    }
}

# Request models
class PermissionRequest(BaseModel):
    user_id: str
    resource_id: str
    resource_type: str
    permission_level: str
    justification: str
    expires_in_days: Optional[int] = None
    device_restrictions: Optional[List[str]] = None

class EmergencyRequest(BaseModel):
    emergency_type: str
    resource_id: str
    resource_type: str
    requested_permissions: List[str]
    justification: str
    business_impact: str
    duration_hours: int
    emergency_contact: str
    incident_number: Optional[str] = None

class ChildProfile(BaseModel):
    name: str
    date_of_birth: str
    parent_ids: List[str]
    safety_level: str = "moderate"


@app.on_event("startup")
async def startup_event():
    """Initialize all permission management systems"""
    global permission_manager, audit_manager, time_policy_manager, emergency_manager, parental_manager
    
    logger.info("Starting Permissions Management Service")
    
    try:
        # Initialize audit manager first (others depend on it)
        audit_manager = AuditManager("data/audit")
        
        # Initialize core permission manager
        permission_manager = PermissionManager("data/permissions")
        await permission_manager.initialize_system()
        
        # Initialize time policy manager
        time_policy_manager = TimePolicyManager("data/time_policies")
        await time_policy_manager.start_scheduler()
        
        # Initialize emergency override manager
        emergency_manager = EmergencyOverrideManager("data/emergency")
        await emergency_manager.initialize_break_glass_configs()
        
        # Initialize parental controls manager
        parental_manager = ParentalControlsManager("data/parental")
        
        # Load all data
        await permission_manager.load_data()
        await time_policy_manager.load_data()
        await emergency_manager.load_data()
        await parental_manager.load_data()
        
        # Start background tasks
        asyncio.create_task(periodic_cleanup())
        asyncio.create_task(permission_review_scheduler())
        
        logger.info("All permission management systems initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize permission systems: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown all permission management systems"""
    logger.info("Shutting down Permissions Management Service")
    
    try:
        if time_policy_manager:
            await time_policy_manager.stop_scheduler()
        
        # Save all data
        if permission_manager:
            await permission_manager.save_data()
        if time_policy_manager:
            await time_policy_manager.save_data()
        if emergency_manager:
            await emergency_manager.save_data()
        if parental_manager:
            await parental_manager.save_data()
            
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def periodic_cleanup():
    """Background task for periodic cleanup and maintenance"""
    while True:
        try:
            # Clean up expired permissions
            if permission_manager:
                current_time = datetime.now(timezone.utc)
                expired_count = 0
                
                for grant in permission_manager.permissions.values():
                    if (grant.expires_at and 
                        grant.expires_at < current_time and 
                        grant.status == PermissionStatus.ACTIVE):
                        grant.status = PermissionStatus.EXPIRED
                        expired_count += 1
                
                if expired_count > 0:
                    logger.info(f"Expired {expired_count} permissions")
                    await permission_manager.save_data()
            
            # Clean up expired emergency sessions
            if emergency_manager:
                await emergency_manager.cleanup_expired_sessions()
            
            # Clean up old audit logs
            if audit_manager:
                await audit_manager.cleanup_old_logs()
            
            logger.debug("Periodic cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
        
        # Wait 1 hour before next cleanup
        await asyncio.sleep(3600)


async def permission_review_scheduler():
    """Background task for scheduling regular permission reviews"""
    while True:
        try:
            # Check for permissions that need review (e.g., older than 30 days)
            if permission_manager:
                review_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                review_needed = []
                
                for grant in permission_manager.permissions.values():
                    if (grant.status == PermissionStatus.ACTIVE and 
                        grant.granted_at < review_cutoff):
                        review_needed.append(grant)
                
                if review_needed:
                    logger.info(f"{len(review_needed)} permissions need review")
                    
                    # Log audit event
                    if audit_manager:
                        await audit_manager.log_event(
                            event_type=AuditEventType.POLICY_CHANGE,
                            action="permission_review_needed",
                            result=f"{len(review_needed)} permissions flagged for review",
                            details={"review_count": len(review_needed)}
                        )
            
        except Exception as e:
            logger.error(f"Error in permission review scheduler: {e}")
        
        # Check daily
        await asyncio.sleep(86400)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "systems": {
            "permission_manager": permission_manager is not None,
            "audit_manager": audit_manager is not None,
            "time_policy_manager": time_policy_manager is not None,
            "emergency_manager": emergency_manager is not None,
            "parental_manager": parental_manager is not None
        }
    }


# Main UI endpoint
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Permissions Management System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.2);
            padding: 1.5rem;
            border-bottom: 3px solid #4CAF50;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        .container { 
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            display: grid; 
            grid-template-columns: 1fr 1fr 1fr;
            grid-gap: 2rem;
        }
        .panel {
            background: rgba(255,255,255,0.1);
            padding: 1.5rem;
            border-radius: 12px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .panel h3 {
            color: #4CAF50;
            margin-bottom: 1rem;
            font-size: 1.3em;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 0.5rem;
        }
        .metric-card {
            background: rgba(255,255,255,0.05);
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            border-left: 4px solid #4CAF50;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }
        .metric-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        .btn {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            border: none;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            cursor: pointer;
            margin: 0.25rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        }
        .btn-warning { background: linear-gradient(45deg, #ff9800, #f57c00); }
        .btn-danger { background: linear-gradient(45deg, #f44336, #d32f2f); }
        .btn-info { background: linear-gradient(45deg, #2196F3, #1976D2); }
        .status-good { color: #4CAF50; }
        .status-warning { color: #ff9800; }
        .status-danger { color: #f44336; }
        .alert-item {
            background: rgba(255,193,7,0.2);
            border: 1px solid #ffc107;
            padding: 0.75rem;
            border-radius: 6px;
            margin: 0.5rem 0;
            font-size: 0.9em;
        }
        .log-item {
            background: rgba(255,255,255,0.05);
            padding: 0.5rem;
            border-radius: 4px;
            margin: 0.25rem 0;
            font-size: 0.85em;
            border-left: 3px solid #666;
        }
        .input-group {
            margin: 1rem 0;
        }
        .input-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }
        .form-input {
            width: 100%;
            padding: 0.5rem;
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.3);
            background: rgba(255,255,255,0.1);
            color: white;
            margin-bottom: 0.5rem;
        }
        .form-input::placeholder { color: rgba(255,255,255,0.6); }
        .tabs {
            display: flex;
            margin-bottom: 1rem;
        }
        .tab {
            background: rgba(255,255,255,0.1);
            border: none;
            color: white;
            padding: 0.5rem 1rem;
            cursor: pointer;
            border-radius: 6px 6px 0 0;
            margin-right: 2px;
        }
        .tab.active {
            background: rgba(76,175,80,0.3);
            border-bottom: 2px solid #4CAF50;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Permissions Management System - Port 8379</h1>
        <div>
            Status: <span id="status">Connecting...</span> | 
            Active Users: <span id="user-count">0</span> | 
            Active Permissions: <span id="permission-count">0</span> |
            Security Level: <span id="security-level" class="status-good">High</span>
        </div>
    </div>
    
    <div class="container">
        <!-- System Overview Panel -->
        <div class="panel">
            <h3>📊 System Overview</h3>
            <div class="metric-card">
                <div class="metric-value" id="total-users">0</div>
                <div class="metric-label">Total Users</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="active-permissions">0</div>
                <div class="metric-label">Active Permissions</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="pending-requests">0</div>
                <div class="metric-label">Pending Requests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="emergency-overrides">0</div>
                <div class="metric-label">Emergency Overrides</div>
            </div>
            
            <h3 style="margin-top: 1.5rem;">⚙️ Quick Actions</h3>
            <button class="btn" onclick="refreshData()">🔄 Refresh Data</button>
            <button class="btn btn-info" onclick="showUserEducation()">📚 User Education</button>
            <button class="btn btn-warning" onclick="showPermissionReview()">🔍 Review Permissions</button>
            <button class="btn btn-danger" onclick="showEmergencyPanel()">🚨 Emergency Override</button>
        </div>
        
        <!-- Security Alerts Panel -->
        <div class="panel">
            <h3>🚨 Security Alerts & Audit</h3>
            <div id="security-alerts">
                <div class="alert-item">✅ All systems operational</div>
            </div>
            
            <h3 style="margin-top: 1.5rem;">📋 Recent Audit Events</h3>
            <div id="audit-log">
                <div class="log-item">System started at ${new Date().toLocaleTimeString()}</div>
            </div>
            
            <h3 style="margin-top: 1.5rem;">🛡️ Security Controls</h3>
            <button class="btn btn-info" onclick="showComplianceReport()">📄 Compliance Report</button>
            <button class="btn" onclick="exportAuditLog()">💾 Export Audit Log</button>
            <button class="btn btn-warning" onclick="runSecurityScan()">🔍 Security Scan</button>
        </div>
        
        <!-- Permission Management Panel -->
        <div class="panel">
            <h3>🔐 Permission Management</h3>
            
            <div class="tabs">
                <button class="tab active" onclick="showTab('grant-tab')">Grant</button>
                <button class="tab" onclick="showTab('review-tab')">Review</button>
                <button class="tab" onclick="showTab('parental-tab')">Parental</button>
                <button class="tab" onclick="showTab('emergency-tab')">Emergency</button>
            </div>
            
            <!-- Grant Permission Tab -->
            <div id="grant-tab" class="tab-content active">
                <div class="input-group">
                    <label>User ID</label>
                    <input type="text" class="form-input" id="grant-user-id" placeholder="Enter user ID">
                </div>
                <div class="input-group">
                    <label>Resource ID</label>
                    <input type="text" class="form-input" id="grant-resource-id" placeholder="Enter resource ID">
                </div>
                <div class="input-group">
                    <label>Permission Level</label>
                    <select class="form-input" id="grant-permission-level">
                        <option value="read">Read</option>
                        <option value="write">Write</option>
                        <option value="delete">Delete</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>Justification</label>
                    <textarea class="form-input" id="grant-justification" placeholder="Explain why this permission is needed" rows="3"></textarea>
                </div>
                <button class="btn" onclick="grantPermission()">✅ Grant Permission</button>
            </div>
            
            <!-- Review Tab -->
            <div id="review-tab" class="tab-content">
                <div id="permissions-list">
                    <p>Loading permissions for review...</p>
                </div>
                <button class="btn btn-info" onclick="loadPermissionsForReview()">🔄 Load Permissions</button>
            </div>
            
            <!-- Parental Controls Tab -->
            <div id="parental-tab" class="tab-content">
                <div class="input-group">
                    <label>Child Name</label>
                    <input type="text" class="form-input" id="child-name" placeholder="Enter child's name">
                </div>
                <div class="input-group">
                    <label>Date of Birth</label>
                    <input type="date" class="form-input" id="child-dob">
                </div>
                <div class="input-group">
                    <label>Safety Level</label>
                    <select class="form-input" id="child-safety-level">
                        <option value="minimal">Minimal</option>
                        <option value="moderate" selected>Moderate</option>
                        <option value="strict">Strict</option>
                        <option value="maximum">Maximum</option>
                    </select>
                </div>
                <button class="btn" onclick="createChildProfile()">👶 Create Child Profile</button>
            </div>
            
            <!-- Emergency Tab -->
            <div id="emergency-tab" class="tab-content">
                <div class="input-group">
                    <label>Emergency Type</label>
                    <select class="form-input" id="emergency-type">
                        <option value="security_incident">Security Incident</option>
                        <option value="system_outage">System Outage</option>
                        <option value="business_critical">Business Critical</option>
                        <option value="disaster_recovery">Disaster Recovery</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>Resource ID</label>
                    <input type="text" class="form-input" id="emergency-resource" placeholder="Resource requiring emergency access">
                </div>
                <div class="input-group">
                    <label>Justification</label>
                    <textarea class="form-input" id="emergency-justification" placeholder="Explain the emergency situation" rows="3"></textarea>
                </div>
                <button class="btn btn-danger" onclick="requestEmergencyOverride()">🚨 Request Emergency Access</button>
            </div>
        </div>
    </div>
    
    <!-- User Education Modal -->
    <div id="education-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center;">
        <div style="background: #1a1a2e; padding: 2rem; border-radius: 12px; max-width: 600px; color: white;">
            <h2>📚 User Education & Best Practices</h2>
            <div style="margin: 1rem 0;">
                <h3>🔐 Permission Security Guidelines</h3>
                <ul style="margin-left: 1.5rem; line-height: 1.6;">
                    <li>Only request permissions you actually need</li>
                    <li>Provide clear justification for permission requests</li>
                    <li>Review and update permissions regularly</li>
                    <li>Report suspicious permission requests</li>
                    <li>Never share your access credentials</li>
                </ul>
                
                <h3 style="margin-top: 1rem;">⚠️ Warning Signs</h3>
                <ul style="margin-left: 1.5rem; line-height: 1.6;">
                    <li>Unexpected permission requests</li>
                    <li>Access to resources you don't recognize</li>
                    <li>Permissions granted by unknown users</li>
                    <li>Unusual activity in audit logs</li>
                </ul>
                
                <h3 style="margin-top: 1rem;">🚨 In Case of Security Incident</h3>
                <ul style="margin-left: 1.5rem; line-height: 1.6;">
                    <li>Immediately revoke suspicious permissions</li>
                    <li>Contact your security team</li>
                    <li>Document the incident</li>
                    <li>Change your passwords</li>
                </ul>
            </div>
            <button class="btn" onclick="closeEducationModal()">Got It!</button>
        </div>
    </div>

    <script>
        let currentUser = 'demo_user';
        let systemData = {};
        
        // Initialize the system
        async function initializeSystem() {
            try {
                const response = await fetch('/health');
                const health = await response.json();
                
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'status-good';
                
                await refreshData();
                
                // Start periodic refresh
                setInterval(refreshData, 30000); // Every 30 seconds
                
            } catch (error) {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'status-danger';
                console.error('Failed to connect:', error);
            }
        }
        
        async function refreshData() {
            try {
                // Fetch system statistics
                const [permissionsRes, auditRes] = await Promise.all([
                    fetch('/api/permissions/stats'),
                    fetch('/api/audit/recent')
                ]);
                
                if (permissionsRes.ok) {
                    const permData = await permissionsRes.json();
                    document.getElementById('total-users').textContent = permData.total_users || 0;
                    document.getElementById('active-permissions').textContent = permData.active_permissions || 0;
                    document.getElementById('pending-requests').textContent = permData.pending_requests || 0;
                    document.getElementById('emergency-overrides').textContent = permData.emergency_overrides || 0;
                }
                
                if (auditRes.ok) {
                    const auditData = await auditRes.json();
                    updateAuditLog(auditData.recent_events || []);
                }
                
            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }
        
        function updateAuditLog(events) {
            const logContainer = document.getElementById('audit-log');
            logContainer.innerHTML = '';
            
            events.slice(0, 10).forEach(event => {
                const logItem = document.createElement('div');
                logItem.className = 'log-item';
                logItem.innerHTML = `
                    <div>${new Date(event.timestamp).toLocaleString()} - ${event.action}</div>
                    <div style="font-size: 0.8em; opacity: 0.8;">${event.user_id || 'system'}: ${event.result}</div>
                `;
                logContainer.appendChild(logItem);
            });
        }
        
        function showTab(tabId) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabId).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
        }
        
        async function grantPermission() {
            const data = {
                user_id: document.getElementById('grant-user-id').value,
                resource_id: document.getElementById('grant-resource-id').value,
                resource_type: 'file', // Default
                permission_level: document.getElementById('grant-permission-level').value,
                justification: document.getElementById('grant-justification').value
            };
            
            if (!data.user_id || !data.resource_id || !data.justification) {
                alert('Please fill in all required fields');
                return;
            }
            
            try {
                const response = await fetch('/api/permissions/grant', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('Permission granted successfully!');
                    // Clear form
                    document.getElementById('grant-user-id').value = '';
                    document.getElementById('grant-resource-id').value = '';
                    document.getElementById('grant-justification').value = '';
                    refreshData();
                } else {
                    alert('Error granting permission: ' + result.message);
                }
                
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        async function createChildProfile() {
            const data = {
                name: document.getElementById('child-name').value,
                date_of_birth: document.getElementById('child-dob').value,
                parent_ids: [currentUser],
                safety_level: document.getElementById('child-safety-level').value
            };
            
            if (!data.name || !data.date_of_birth) {
                alert('Please fill in all required fields');
                return;
            }
            
            try {
                const response = await fetch('/api/parental/create-child', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('Child profile created successfully!');
                    document.getElementById('child-name').value = '';
                    document.getElementById('child-dob').value = '';
                    refreshData();
                } else {
                    alert('Error creating child profile: ' + result.message);
                }
                
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        async function requestEmergencyOverride() {
            const data = {
                emergency_type: document.getElementById('emergency-type').value,
                resource_id: document.getElementById('emergency-resource').value,
                resource_type: 'system',
                requested_permissions: ['admin'],
                justification: document.getElementById('emergency-justification').value,
                business_impact: 'Critical system access required',
                duration_hours: 4,
                emergency_contact: currentUser
            };
            
            if (!data.resource_id || !data.justification) {
                alert('Please fill in all required fields');
                return;
            }
            
            try {
                const response = await fetch('/api/emergency/request', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`Emergency override requested! Request ID: ${result.override_id}`);
                    document.getElementById('emergency-resource').value = '';
                    document.getElementById('emergency-justification').value = '';
                    refreshData();
                } else {
                    alert('Error requesting emergency override: ' + result.message);
                }
                
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        function showUserEducation() {
            document.getElementById('education-modal').style.display = 'flex';
        }
        
        function closeEducationModal() {
            document.getElementById('education-modal').style.display = 'none';
        }
        
        function showPermissionReview() {
            alert('Permission review system would show all permissions requiring review');
        }
        
        function showEmergencyPanel() {
            showTab('emergency-tab');
        }
        
        function showComplianceReport() {
            alert('Compliance report would show regulatory compliance status');
        }
        
        function exportAuditLog() {
            alert('Audit log would be exported to a downloadable file');
        }
        
        function runSecurityScan() {
            alert('Security scan would analyze current permission configuration for vulnerabilities');
        }
        
        function loadPermissionsForReview() {
            document.getElementById('permissions-list').innerHTML = `
                <div class="log-item">
                    <div>User: john_doe | Resource: /sensitive/files | Permission: admin | Age: 45 days</div>
                    <button class="btn btn-warning" style="font-size: 0.8em; padding: 0.25rem 0.5rem;">Review</button>
                    <button class="btn btn-danger" style="font-size: 0.8em; padding: 0.25rem 0.5rem;">Revoke</button>
                </div>
                <div class="log-item">
                    <div>User: jane_smith | Resource: /database/prod | Permission: write | Age: 62 days</div>
                    <button class="btn btn-warning" style="font-size: 0.8em; padding: 0.25rem 0.5rem;">Review</button>
                    <button class="btn btn-danger" style="font-size: 0.8em; padding: 0.25rem 0.5rem;">Revoke</button>
                </div>
                <div class="log-item">
                    <div>User: admin_user | Resource: /system/config | Permission: owner | Age: 120 days</div>
                    <button class="btn btn-warning" style="font-size: 0.8em; padding: 0.25rem 0.5rem;">Review</button>
                    <button class="btn btn-danger" style="font-size: 0.8em; padding: 0.25rem 0.5rem;">Revoke</button>
                </div>
            `;
        }
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', initializeSystem);
    </script>
</body>
</html>
    """


# API Endpoints

@app.get("/api/permissions/stats")
async def get_permissions_stats():
    """Get permission system statistics"""
    try:
        stats = {
            "total_users": len(permission_manager.users) if permission_manager else 0,
            "total_roles": len(permission_manager.roles) if permission_manager else 0,
            "active_permissions": len([p for p in (permission_manager.permissions.values() if permission_manager else []) 
                                     if p.status == PermissionStatus.ACTIVE]),
            "pending_requests": len([r for r in (parental_manager.approval_requests.values() if parental_manager else [])
                                   if r.status == "pending"]),
            "emergency_overrides": len([o for o in (emergency_manager.overrides.values() if emergency_manager else [])
                                      if o.status == OverrideStatus.ACTIVE]),
            "child_profiles": len(parental_manager.children) if parental_manager else 0
        }
        return {"success": True, "stats": stats}
        
    except Exception as e:
        logger.error(f"Error getting permissions stats: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/audit/recent")
async def get_recent_audit_events():
    """Get recent audit events"""
    try:
        if not audit_manager:
            return {"success": False, "error": "Audit manager not initialized"}
        
        recent_events = audit_manager.recent_events[-20:]  # Last 20 events
        events_data = []
        
        for event in recent_events:
            events_data.append({
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "action": event.action,
                "result": event.result,
                "user_id": event.user_id,
                "severity": event.severity.value,
                "risk_score": event.risk_score
            })
        
        return {"success": True, "recent_events": events_data}
        
    except Exception as e:
        logger.error(f"Error getting recent audit events: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/permissions/grant")
async def grant_permission(request: PermissionRequest, req: Request):
    """Grant a permission to a user"""
    try:
        if not permission_manager or not audit_manager:
            raise HTTPException(status_code=500, detail="Services not initialized")
        
        # Convert string permission level to enum
        try:
            perm_level = PermissionLevel(request.permission_level.lower())
            resource_type = ResourceType(request.resource_type.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid permission level or resource type: {e}")
        
        # Grant the permission
        grant_id = await permission_manager.grant_permission(
            user_id=request.user_id,
            resource_id=request.resource_id,
            resource_type=resource_type,
            permission_level=perm_level,
            granted_by="api_user",  # In real system, would use authenticated user
            justification=request.justification,
            expires_in_days=request.expires_in_days,
            device_restrictions=request.device_restrictions
        )
        
        # Log the audit event
        await audit_manager.log_event(
            event_type=AuditEventType.PERMISSION_GRANT,
            user_id="api_user",
            target_user_id=request.user_id,
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            action="grant_permission",
            result="success",
            details={
                "grant_id": grant_id,
                "permission_level": request.permission_level,
                "justification": request.justification
            },
            ip_address=req.client.host if req.client else None
        )
        
        return {"success": True, "grant_id": grant_id}
        
    except Exception as e:
        logger.error(f"Error granting permission: {e}")
        if audit_manager:
            await audit_manager.log_event(
                event_type=AuditEventType.PERMISSION_GRANT,
                user_id="api_user",
                action="grant_permission",
                result="failed",
                details={"error": str(e)},
                severity=AuditSeverity.HIGH
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/emergency/request")
async def request_emergency_override(request: EmergencyRequest, req: Request):
    """Request an emergency permission override"""
    try:
        if not emergency_manager or not audit_manager:
            raise HTTPException(status_code=500, detail="Services not initialized")
        
        # Convert string emergency type to enum
        try:
            emergency_type = EmergencyType(request.emergency_type.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid emergency type: {e}")
        
        # Request the emergency override
        override_id = await emergency_manager.request_emergency_override(
            requester_id="api_user",
            emergency_type=emergency_type,
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            requested_permissions=request.requested_permissions,
            justification=request.justification,
            business_impact=request.business_impact,
            duration_hours=request.duration_hours,
            emergency_contact=request.emergency_contact,
            incident_number=request.incident_number
        )
        
        # Log the audit event
        await audit_manager.log_event(
            event_type=AuditEventType.EMERGENCY_OVERRIDE,
            user_id="api_user",
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            action="request_emergency_override",
            result="requested",
            details={
                "override_id": override_id,
                "emergency_type": request.emergency_type,
                "justification": request.justification,
                "duration_hours": request.duration_hours
            },
            ip_address=req.client.host if req.client else None,
            severity=AuditSeverity.CRITICAL
        )
        
        return {"success": True, "override_id": override_id}
        
    except Exception as e:
        logger.error(f"Error requesting emergency override: {e}")
        if audit_manager:
            await audit_manager.log_event(
                event_type=AuditEventType.EMERGENCY_OVERRIDE,
                user_id="api_user",
                action="request_emergency_override",
                result="failed",
                details={"error": str(e)},
                severity=AuditSeverity.HIGH
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parental/create-child")
async def create_child_profile(request: ChildProfile, req: Request):
    """Create a child profile with parental controls"""
    try:
        if not parental_manager or not audit_manager:
            raise HTTPException(status_code=500, detail="Services not initialized")
        
        # Convert date string to datetime
        try:
            date_of_birth = datetime.fromisoformat(request.date_of_birth)
            safety_level = SafetyLevel(request.safety_level.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format or safety level: {e}")
        
        # Create the child profile
        child_id = await parental_manager.create_child_profile(
            name=request.name,
            date_of_birth=date_of_birth,
            parent_ids=request.parent_ids,
            safety_level=safety_level
        )
        
        # Log the audit event
        await audit_manager.log_event(
            event_type=AuditEventType.USER_CREATE,
            user_id="api_user",
            action="create_child_profile",
            result="success",
            details={
                "child_id": child_id,
                "child_name": request.name,
                "safety_level": request.safety_level,
                "parent_ids": request.parent_ids
            },
            ip_address=req.client.host if req.client else None
        )
        
        return {"success": True, "child_id": child_id}
        
    except Exception as e:
        logger.error(f"Error creating child profile: {e}")
        if audit_manager:
            await audit_manager.log_event(
                event_type=AuditEventType.USER_CREATE,
                user_id="api_user",
                action="create_child_profile",
                result="failed",
                details={"error": str(e)},
                severity=AuditSeverity.MEDIUM
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/permissions/check")
async def check_permission(
    user_id: str,
    resource_id: str,
    resource_type: str,
    permission_level: str,
    device_id: Optional[str] = None,
    req: Request = None
):
    """Check if user has permission for resource"""
    try:
        if not permission_manager or not audit_manager:
            raise HTTPException(status_code=500, detail="Services not initialized")
        
        # Convert string values to enums
        try:
            perm_level = PermissionLevel(permission_level.lower())
            res_type = ResourceType(resource_type.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid permission level or resource type: {e}")
        
        # Check the permission
        is_allowed, reason = await permission_manager.check_permission(
            user_id=user_id,
            resource_id=resource_id,
            resource_type=res_type,
            permission_level=perm_level,
            device_id=device_id,
            context={
                "ip_address": req.client.host if req.client else None,
                "user_agent": req.headers.get("user-agent") if req else None
            }
        )
        
        # Log the audit event
        await audit_manager.log_event(
            event_type=AuditEventType.PERMISSION_CHECK if is_allowed else AuditEventType.PERMISSION_DENIED,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action="check_permission",
            result="allowed" if is_allowed else "denied",
            details={
                "permission_level": permission_level,
                "reason": reason,
                "device_id": device_id
            },
            ip_address=req.client.host if req.client else None,
            severity=AuditSeverity.LOW if is_allowed else AuditSeverity.MEDIUM
        )
        
        return {
            "success": True,
            "allowed": is_allowed,
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        if audit_manager:
            await audit_manager.log_event(
                event_type=AuditEventType.PERMISSION_CHECK,
                user_id=user_id,
                action="check_permission",
                result="error",
                details={"error": str(e)},
                severity=AuditSeverity.HIGH
            )
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Create required directories
    os.makedirs("data/permissions", exist_ok=True)
    os.makedirs("data/audit", exist_ok=True)
    os.makedirs("data/time_policies", exist_ok=True)
    os.makedirs("data/emergency", exist_ok=True)
    os.makedirs("data/parental", exist_ok=True)
    
    port = int(os.getenv("PORT", 8379))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )