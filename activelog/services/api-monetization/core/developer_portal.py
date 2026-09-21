import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models.monetization_models import *

class DeveloperPortalManager:
    def __init__(self):
        self.developers = {}
        self.developer_sessions = {}
        self.api_subscriptions = {}
        self.support_tickets = {}
        self.notifications = {}
        
    async def register_developer(self, request: DeveloperPortalRequest) -> DeveloperPortalResponse:
        developer_id = str(uuid.uuid4())
        
        developer_data = {
            "developer_id": developer_id,
            "company_name": request.company_name,
            "email": request.email,
            "phone": request.phone,
            "billing_address": request.billing_address,
            "created_at": datetime.now(),
            "status": "active",
            "verification_status": "pending",
            "tier": PricingTier.FREE,
            "total_apis": 0,
            "monthly_spend": 0.0
        }
        
        self.developers[developer_id] = developer_data
        
        return DeveloperPortalResponse(
            developer_id=developer_id,
            company_name=request.company_name,
            email=request.email,
            api_keys=[],
            current_usage={},
            billing_history=[],
            tier=PricingTier.FREE,
            created_at=developer_data["created_at"]
        )
    
    async def get_developer_dashboard(self, developer_id: str) -> Dict:
        if developer_id not in self.developers:
            raise ValueError("Developer not found")
        
        developer = self.developers[developer_id]
        
        from core.api_key_management import api_key_manager
        from core.usage_metering import usage_metering_manager
        
        api_keys = await api_key_manager.get_developer_keys(developer_id)
        
        current_usage = {}
        total_requests = 0
        total_cost = 0.0
        
        for api_key_response in api_keys:
            usage_stats = await api_key_manager.get_key_usage_stats(api_key_response.api_key)
            if usage_stats:
                total_requests += usage_stats.get("total_requests", 0)
                current_usage[api_key_response.api_key] = usage_stats
        
        recent_activity = await self._get_recent_activity(developer_id)
        upcoming_bills = await self._get_upcoming_bills(developer_id)
        notifications = await self._get_developer_notifications(developer_id)
        
        return {
            "developer_info": developer,
            "api_keys": api_keys,
            "usage_summary": {
                "total_requests": total_requests,
                "total_apis": len(api_keys),
                "active_apis": len([k for k in api_keys if k.status == APIKeyStatus.ACTIVE]),
                "current_month_cost": total_cost
            },
            "current_usage": current_usage,
            "recent_activity": recent_activity,
            "upcoming_bills": upcoming_bills,
            "notifications": notifications
        }
    
    async def update_developer_profile(self, developer_id: str, updates: Dict) -> Dict:
        if developer_id not in self.developers:
            raise ValueError("Developer not found")
        
        allowed_fields = ["company_name", "email", "phone", "billing_address"]
        
        for field, value in updates.items():
            if field in allowed_fields:
                self.developers[developer_id][field] = value
        
        self.developers[developer_id]["updated_at"] = datetime.now()
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "updated_fields": list(updates.keys()),
            "updated_at": datetime.now()
        }
    
    async def upgrade_developer_tier(self, developer_id: str, new_tier: PricingTier) -> Dict:
        if developer_id not in self.developers:
            raise ValueError("Developer not found")
        
        old_tier = self.developers[developer_id]["tier"]
        self.developers[developer_id]["tier"] = new_tier
        
        from core.api_key_management import api_key_manager
        api_keys = await api_key_manager.get_developer_keys(developer_id)
        
        for api_key_response in api_keys:
            await api_key_manager.update_api_key_tier(api_key_response.api_key, new_tier)
        
        await self._create_notification(
            developer_id,
            "tier_upgrade",
            f"Your account has been upgraded from {old_tier} to {new_tier}",
            {"old_tier": old_tier, "new_tier": new_tier}
        )
        
        return {
            "success": True,
            "message": f"Developer tier upgraded from {old_tier} to {new_tier}",
            "old_tier": old_tier,
            "new_tier": new_tier,
            "affected_api_keys": len(api_keys),
            "upgraded_at": datetime.now()
        }
    
    async def create_support_ticket(self, developer_id: str, subject: str, 
                                   description: str, priority: str = "medium") -> Dict:
        ticket_id = str(uuid.uuid4())
        
        ticket = {
            "ticket_id": ticket_id,
            "developer_id": developer_id,
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "messages": [
                {
                    "message_id": str(uuid.uuid4()),
                    "sender": "developer",
                    "content": description,
                    "timestamp": datetime.now()
                }
            ]
        }
        
        self.support_tickets[ticket_id] = ticket
        
        await self._create_notification(
            developer_id,
            "support_ticket_created",
            f"Support ticket created: {subject}",
            {"ticket_id": ticket_id, "subject": subject}
        )
        
        return {
            "ticket_id": ticket_id,
            "status": "created",
            "estimated_response_time": "24 hours",
            "created_at": datetime.now()
        }
    
    async def get_support_tickets(self, developer_id: str) -> List[Dict]:
        tickets = [
            ticket for ticket in self.support_tickets.values()
            if ticket["developer_id"] == developer_id
        ]
        
        return sorted(tickets, key=lambda x: x["created_at"], reverse=True)
    
    async def add_ticket_message(self, ticket_id: str, sender: str, content: str) -> Dict:
        if ticket_id not in self.support_tickets:
            raise ValueError("Ticket not found")
        
        message = {
            "message_id": str(uuid.uuid4()),
            "sender": sender,
            "content": content,
            "timestamp": datetime.now()
        }
        
        self.support_tickets[ticket_id]["messages"].append(message)
        self.support_tickets[ticket_id]["updated_at"] = datetime.now()
        
        if sender == "support":
            developer_id = self.support_tickets[ticket_id]["developer_id"]
            await self._create_notification(
                developer_id,
                "support_response",
                f"New response on ticket: {self.support_tickets[ticket_id]['subject']}",
                {"ticket_id": ticket_id}
            )
        
        return {
            "message_id": message["message_id"],
            "added_at": message["timestamp"]
        }
    
    async def subscribe_to_api(self, developer_id: str, api_id: str, tier: PricingTier) -> Dict:
        subscription_id = str(uuid.uuid4())
        
        subscription = {
            "subscription_id": subscription_id,
            "developer_id": developer_id,
            "api_id": api_id,
            "tier": tier,
            "status": "active",
            "subscribed_at": datetime.now(),
            "billing_cycle": BillingCycle.MONTHLY
        }
        
        if developer_id not in self.api_subscriptions:
            self.api_subscriptions[developer_id] = []
        
        self.api_subscriptions[developer_id].append(subscription)
        
        await self._create_notification(
            developer_id,
            "api_subscription",
            f"Successfully subscribed to API: {api_id}",
            {"api_id": api_id, "tier": tier, "subscription_id": subscription_id}
        )
        
        return {
            "subscription_id": subscription_id,
            "status": "active",
            "message": "Successfully subscribed to API",
            "subscribed_at": datetime.now()
        }
    
    async def get_api_documentation(self, api_id: str) -> Dict:
        return {
            "api_id": api_id,
            "documentation": {
                "overview": "API documentation and usage examples",
                "authentication": "Use your API key in the Authorization header",
                "endpoints": [
                    {
                        "path": "/api/v1/data",
                        "method": "GET",
                        "description": "Retrieve data",
                        "parameters": ["limit", "offset"],
                        "example": "curl -H 'Authorization: Bearer YOUR_API_KEY' https://api.example.com/v1/data"
                    }
                ],
                "rate_limits": "Varies by tier",
                "error_codes": {
                    "401": "Unauthorized - Invalid API key",
                    "429": "Rate limit exceeded",
                    "500": "Internal server error"
                }
            },
            "code_examples": {
                "python": "import requests\nresponse = requests.get('https://api.example.com/v1/data', headers={'Authorization': 'Bearer YOUR_API_KEY'})",
                "javascript": "fetch('https://api.example.com/v1/data', { headers: { 'Authorization': 'Bearer YOUR_API_KEY' } })",
                "curl": "curl -H 'Authorization: Bearer YOUR_API_KEY' https://api.example.com/v1/data"
            }
        }
    
    async def _get_recent_activity(self, developer_id: str) -> List[Dict]:
        return [
            {
                "activity_id": str(uuid.uuid4()),
                "type": "api_key_created",
                "description": "New API key generated for Weather API",
                "timestamp": datetime.now() - timedelta(hours=2)
            },
            {
                "activity_id": str(uuid.uuid4()),
                "type": "usage_spike",
                "description": "High usage detected on Financial API",
                "timestamp": datetime.now() - timedelta(hours=6)
            }
        ]
    
    async def _get_upcoming_bills(self, developer_id: str) -> List[Dict]:
        return [
            {
                "billing_id": str(uuid.uuid4()),
                "amount": 29.99,
                "due_date": datetime.now() + timedelta(days=15),
                "description": "Monthly subscription - Basic tier"
            }
        ]
    
    async def _get_developer_notifications(self, developer_id: str) -> List[Dict]:
        if developer_id not in self.notifications:
            return []
        
        return sorted(
            self.notifications[developer_id],
            key=lambda x: x["created_at"],
            reverse=True
        )[:10]
    
    async def _create_notification(self, developer_id: str, notification_type: str, 
                                 message: str, metadata: Dict = None):
        if developer_id not in self.notifications:
            self.notifications[developer_id] = []
        
        notification = {
            "notification_id": str(uuid.uuid4()),
            "type": notification_type,
            "message": message,
            "metadata": metadata or {},
            "created_at": datetime.now(),
            "read": False
        }
        
        self.notifications[developer_id].append(notification)
        
        if len(self.notifications[developer_id]) > 100:
            self.notifications[developer_id] = self.notifications[developer_id][-100:]

developer_portal_manager = DeveloperPortalManager()