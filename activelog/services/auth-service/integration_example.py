"""
Example: How to integrate ActiveLog Authentication into other services

This shows how to modify existing services like PersonalLog, FishingLog, DMLog, etc.
to use the centralized authentication system.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from middleware import AuthMiddleware, get_current_user, setup_auth_for_service
from client import AuthClient, create_auth_client
from typing import Dict, Any, Optional
import uvicorn

# Example: PersonalLog service with authentication
class PersonalLogWithAuth:
    """PersonalLog service integrated with authentication"""
    
    def __init__(self, auth_service_url: str = "http://localhost:8080"):
        self.auth_client = create_auth_client(auth_service_url)
        
    def create_app(self):
        """Create FastAPI app with authentication"""
        app = FastAPI(
            title="PersonalLog with Authentication",
            description="Personal journaling service with JWT authentication",
            version="1.0.0"
        )
        
        # Setup authentication for this service
        setup_auth_for_service(app, "personallog", self.auth_client.base_url)
        
        # Example protected endpoint
        @app.post("/api/entries")
        async def create_entry(
            entry_data: Dict[str, Any],
            request: Request
        ):
            """Create a new journal entry (requires authentication)"""
            # Get current user from request (added by middleware)
            user = getattr(request.state, 'current_user', None)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Add user ID to entry
            entry_data['user_id'] = user['id']
            entry_data['username'] = user['username']
            
            # Your existing entry creation logic here
            # For example:
            entry = {
                "id": "generated-entry-id",
                "title": entry_data.get("title", ""),
                "content": entry_data.get("content", ""),
                "user_id": user['id'],
                "created_at": "2025-08-26T13:22:00Z"
            }
            
            return {
                "success": True,
                "entry": entry,
                "message": f"Entry created for user {user['username']}"
            }
        
        @app.get("/api/entries")
        async def get_entries(
            request: Request,
            limit: int = 50
        ):
            """Get user's journal entries (requires authentication)"""
            user = getattr(request.state, 'current_user', None)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Your existing logic to fetch entries for this user
            entries = [
                {
                    "id": "entry-1",
                    "title": "My First Entry",
                    "content": "This is my first authenticated entry!",
                    "user_id": user['id'],
                    "created_at": "2025-08-26T13:22:00Z"
                }
            ]
            
            return {
                "entries": entries,
                "total": len(entries),
                "user": user['username']
            }
        
        @app.get("/api/profile")
        async def get_user_profile(request: Request):
            """Get current user profile"""
            user = getattr(request.state, 'current_user', None)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            return user
        
        # Public endpoint (no authentication required)
        @app.get("/api/public/info")
        async def get_public_info():
            """Public endpoint - no authentication required"""
            return {
                "service": "PersonalLog",
                "version": "1.0.0",
                "features": ["journaling", "authentication", "user-specific entries"]
            }
        
        return app

# Example: Using AuthClient directly in existing services
class ExistingServiceIntegration:
    """Shows how to add auth to existing services without middleware"""
    
    def __init__(self, auth_service_url: str = "http://localhost:8080"):
        self.auth_client = create_auth_client(auth_service_url)
    
    async def protected_function(self, token: str, data: Dict[str, Any]):
        """Example of a function that requires authentication"""
        
        # Validate token and get user
        user = await self.auth_client.validate_token(token)
        if not user:
            raise ValueError("Invalid or expired authentication token")
        
        # Check if user has access to this service
        if "fishinglog" not in user.get('services', []):
            raise ValueError("User does not have access to FishingLog service")
        
        # Add user context to data
        data['user_id'] = user['id']
        data['username'] = user['username']
        
        # Your existing business logic here
        result = {
            "message": f"Data processed for user {user['username']}",
            "data": data,
            "user_context": user
        }
        
        return result
    
    async def register_and_grant_access(self, email: str, password: str, username: str, full_name: str, service_name: str):
        """Register user and grant access to a service"""
        
        # Register user
        register_result = await self.auth_client.register_user(email, password, username, full_name)
        if not register_result:
            return None
        
        # Grant access to the service
        token = register_result['access_token']
        granted = await self.auth_client.grant_service_access(token, service_name)
        
        if granted:
            # Get updated user profile
            user = await self.auth_client.get_user_profile(token)
            register_result['user'] = user
        
        return register_result

# FastAPI dependency approach (alternative to middleware)
class AuthDependencyExample:
    """Example using FastAPI dependencies instead of middleware"""
    
    def __init__(self, auth_service_url: str = "http://localhost:8080"):
        self.auth_client = create_auth_client(auth_service_url)
    
    async def get_current_user(self, request: Request) -> Dict[str, Any]:
        """FastAPI dependency to get current user"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        user = await self.auth_client.validate_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return user
    
    def create_app(self):
        """Create app using dependency injection"""
        app = FastAPI(title="Service with Auth Dependencies")
        
        @app.get("/api/protected")
        async def protected_endpoint(
            current_user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            return {
                "message": f"Hello {current_user['username']}",
                "user_id": current_user['id'],
                "services": current_user.get('services', [])
            }
        
        return app

# Example service modification for existing PersonalLog backend
def modify_personallog_backend():
    """
    Example of how to modify the existing PersonalLog backend
    to use authentication (pseudo-code)
    """
    
    # Add this to your existing main.py imports:
    # from auth_service.middleware import AuthMiddleware
    # from auth_service.client import create_auth_client
    
    # In your FastAPI app setup:
    # app.add_middleware(AuthMiddleware, auth_service_url="http://localhost:8080")
    
    # Modify your existing endpoints:
    """
    @app.post("/api/entries", response_model=JournalEntry)
    async def create_entry(entry: JournalEntry, request: Request):
        # Get authenticated user
        user = getattr(request.state, 'current_user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Associate entry with user
        entry.user_id = user['id']
        
        # Your existing entry creation logic
        return await backend.create_entry(entry)
    
    @app.get("/api/entries/{user_id}")
    async def get_entries(user_id: str, request: Request, limit: int = 50, offset: int = 0):
        # Get authenticated user
        user = getattr(request.state, 'current_user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Ensure user can only access their own entries
        if user['id'] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Your existing logic
        return await backend.get_entries(user_id, limit, offset)
    """

# Test the authentication integration
async def test_integration():
    """Test authentication integration"""
    
    # Create auth client
    auth_client = create_auth_client("http://localhost:8080")
    
    # Test service health
    healthy = await auth_client.health_check()
    print(f"Auth service healthy: {healthy}")
    
    if not healthy:
        print("⚠️  Authentication service is not available")
        return
    
    # Test user registration
    print("\n📝 Testing user registration...")
    user_data = await auth_client.register_user(
        email="testuser@example.com",
        password="TestPassword123!",
        username="testuser",
        full_name="Test User"
    )
    
    if user_data:
        print(f"✅ User registered: {user_data['user']['username']}")
        token = user_data['access_token']
        
        # Test token validation
        print("\n🔐 Testing token validation...")
        validated_user = await auth_client.validate_token(token)
        
        if validated_user:
            print(f"✅ Token valid for user: {validated_user['username']}")
            
            # Grant service access
            print("\n🎫 Granting service access...")
            granted = await auth_client.grant_service_access(token, "personallog")
            
            if granted:
                print("✅ Service access granted")
                
                # Get updated profile
                profile = await auth_client.get_user_profile(token)
                print(f"📊 User services: {profile.get('services', [])}")
            else:
                print("❌ Failed to grant service access")
        else:
            print("❌ Token validation failed")
    else:
        print("❌ User registration failed")

if __name__ == "__main__":
    import asyncio
    
    # Run integration test
    print("🧪 Testing ActiveLog Authentication Integration")
    print("=" * 50)
    
    asyncio.run(test_integration())
    
    # You can also run the example services:
    # 
    # personallog_service = PersonalLogWithAuth()
    # app = personallog_service.create_app()
    # uvicorn.run(app, host="0.0.0.0", port=8001)