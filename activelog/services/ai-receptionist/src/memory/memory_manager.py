"""
Conversation Memory System
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from ..database import ConversationMemory, Conversation, ConversationMessage


class MemoryManager:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.memory_types = {
            "preference": {"decay_rate": 0.95, "max_age_days": 90},
            "context": {"decay_rate": 0.90, "max_age_days": 30},
            "history": {"decay_rate": 0.85, "max_age_days": 180},
            "behavior": {"decay_rate": 0.92, "max_age_days": 60},
            "goal": {"decay_rate": 0.98, "max_age_days": 365}
        }
    
    async def load_visitor_memory(
        self,
        visitor_email: str = None,
        visitor_phone: str = None
    ) -> Dict[str, Any]:
        """Load memory context for website visitor"""
        
        if not visitor_email and not visitor_phone:
            return {"returning_visitor": False}
        
        # Find existing memories
        filters = []
        if visitor_email:
            filters.append(ConversationMemory.caller_email == visitor_email)
        if visitor_phone:
            filters.append(ConversationMemory.phone_number == visitor_phone)
        
        stmt = select(ConversationMemory).where(
            or_(*filters),
            ConversationMemory.expiry_date > datetime.utcnow()
        ).order_by(ConversationMemory.strength.desc())
        
        result = await self.db.execute(stmt)
        memories = result.scalars().all()
        
        if not memories:
            return {"returning_visitor": False}
        
        # Process memories into context
        context = {
            "returning_visitor": True,
            "preferences": {},
            "history": {},
            "interests": [],
            "last_contact": None,
            "interaction_count": 0
        }
        
        for memory in memories:
            if memory.memory_type == "preference":
                context["preferences"][memory.key] = memory.value
            elif memory.memory_type == "history":
                if not context["last_contact"] or memory.last_accessed > context["last_contact"]:
                    context["last_contact"] = memory.last_accessed
                    context["last_topic"] = memory.value.get("topic", "general inquiry")
            elif memory.memory_type == "behavior":
                if memory.key == "interaction_count":
                    context["interaction_count"] = memory.value.get("count", 0)
        
        return context
    
    async def load_caller_memory(self, phone_number: str) -> Dict[str, Any]:
        """Load memory context for phone caller"""
        
        return await self.load_visitor_memory(visitor_phone=phone_number)
    
    async def load_conversation_memory(
        self,
        conversation_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Load memory context for ongoing conversation"""
        
        # Get conversation details
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {}
        
        # Load memories for this contact
        contact_memory = await self.load_visitor_memory(
            conversation.caller_email,
            conversation.phone_number
        )
        
        # Get recent conversation messages for context
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.timestamp.desc()).limit(10)
        
        result = await self.db.execute(stmt)
        recent_messages = result.scalars().all()
        
        # Extract conversation context
        conversation_context = {
            "recent_topics": [],
            "detected_intents": [],
            "user_questions": [],
            "unresolved_issues": []
        }
        
        for message in recent_messages:
            if message.intent:
                conversation_context["detected_intents"].append(message.intent)
            
            if message.message_type == "user" and "?" in message.content:
                conversation_context["user_questions"].append(message.content)
        
        return {
            **contact_memory,
            "conversation_context": conversation_context
        }
    
    async def update_conversation_memory(
        self,
        conversation_id: uuid.UUID,
        user_message: str,
        assistant_response: str,
        visitor_info: Dict[str, Any] = None
    ):
        """Update memory based on conversation interaction"""
        
        # Get conversation details
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return
        
        # Extract entities and topics from messages
        entities = await self._extract_entities(user_message, assistant_response)
        topics = await self._extract_topics(user_message)
        
        # Update or create memories
        await self._update_preference_memory(
            conversation.caller_email,
            conversation.phone_number,
            entities["preferences"]
        )
        
        await self._update_context_memory(
            conversation.caller_email,
            conversation.phone_number,
            topics,
            entities["context"]
        )
        
        await self._update_behavior_memory(
            conversation.caller_email,
            conversation.phone_number,
            user_message,
            assistant_response
        )
        
        await self._update_interaction_count(
            conversation.caller_email,
            conversation.phone_number
        )
    
    async def update_call_memory(
        self,
        conversation_id: uuid.UUID,
        phone_number: str,
        transcription: str,
        response: str
    ):
        """Update memory based on phone call interaction"""
        
        return await self.update_conversation_memory(
            conversation_id,
            transcription,
            response,
            {"phone_number": phone_number}
        )
    
    async def store_explicit_memory(
        self,
        visitor_email: str = None,
        visitor_phone: str = None,
        memory_type: str = "preference",
        category: str = "general",
        key: str = "",
        value: Any = None,
        strength: float = 1.0
    ):
        """Store explicit memory entry"""
        
        if not visitor_email and not visitor_phone:
            raise ValueError("Either email or phone number required")
        
        # Check if memory already exists
        filters = [
            ConversationMemory.memory_type == memory_type,
            ConversationMemory.category == category,
            ConversationMemory.key == key
        ]
        
        if visitor_email:
            filters.append(ConversationMemory.caller_email == visitor_email)
        if visitor_phone:
            filters.append(ConversationMemory.phone_number == visitor_phone)
        
        stmt = select(ConversationMemory).where(and_(*filters))
        result = await self.db.execute(stmt)
        existing_memory = result.scalar_one_or_none()
        
        if existing_memory:
            # Update existing memory
            stmt = update(ConversationMemory).where(
                ConversationMemory.id == existing_memory.id
            ).values(
                value=value,
                strength=min(existing_memory.strength + 0.1, 2.0),
                last_accessed=datetime.utcnow()
            )
            await self.db.execute(stmt)
        else:
            # Create new memory
            memory_config = self.memory_types.get(memory_type, self.memory_types["preference"])
            expiry_date = datetime.utcnow() + timedelta(days=memory_config["max_age_days"])
            
            new_memory = ConversationMemory(
                memory_type=memory_type,
                category=category,
                key=key,
                value=value,
                strength=strength,
                expiry_date=expiry_date,
                caller_email=visitor_email,
                phone_number=visitor_phone
            )
            
            self.db.add(new_memory)
        
        await self.db.commit()
    
    async def forget_memory(
        self,
        visitor_email: str = None,
        visitor_phone: str = None,
        memory_type: str = None,
        category: str = None
    ):
        """Remove or decay specific memories"""
        
        filters = []
        
        if visitor_email:
            filters.append(ConversationMemory.caller_email == visitor_email)
        if visitor_phone:
            filters.append(ConversationMemory.phone_number == visitor_phone)
        if memory_type:
            filters.append(ConversationMemory.memory_type == memory_type)
        if category:
            filters.append(ConversationMemory.category == category)
        
        if not filters:
            raise ValueError("At least one filter criterion required")
        
        # Delete matching memories
        stmt = delete(ConversationMemory).where(and_(*filters))
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def decay_memories(self):
        """Decay old memories and remove expired ones"""
        
        current_time = datetime.utcnow()
        
        # Remove expired memories
        stmt = delete(ConversationMemory).where(
            ConversationMemory.expiry_date <= current_time
        )
        await self.db.execute(stmt)
        
        # Decay strength of old memories
        for memory_type, config in self.memory_types.items():
            cutoff_date = current_time - timedelta(days=7)  # Decay weekly
            
            stmt = update(ConversationMemory).where(
                and_(
                    ConversationMemory.memory_type == memory_type,
                    ConversationMemory.last_accessed <= cutoff_date
                )
            ).values(
                strength=ConversationMemory.strength * config["decay_rate"]
            )
            await self.db.execute(stmt)
        
        # Remove very weak memories
        stmt = delete(ConversationMemory).where(
            ConversationMemory.strength < 0.1
        )
        await self.db.execute(stmt)
        
        await self.db.commit()
    
    async def get_memory_summary(
        self,
        visitor_email: str = None,
        visitor_phone: str = None
    ) -> Dict[str, Any]:
        """Get summary of stored memories for contact"""
        
        filters = []
        if visitor_email:
            filters.append(ConversationMemory.caller_email == visitor_email)
        if visitor_phone:
            filters.append(ConversationMemory.phone_number == visitor_phone)
        
        if not filters:
            return {}
        
        stmt = select(ConversationMemory).where(or_(*filters))
        result = await self.db.execute(stmt)
        memories = result.scalars().all()
        
        summary = {
            "total_memories": len(memories),
            "memory_types": {},
            "categories": {},
            "strongest_memories": [],
            "recent_memories": []
        }
        
        for memory in memories:
            # Count by type
            summary["memory_types"][memory.memory_type] = (
                summary["memory_types"].get(memory.memory_type, 0) + 1
            )
            
            # Count by category
            summary["categories"][memory.category] = (
                summary["categories"].get(memory.category, 0) + 1
            )
        
        # Get strongest memories
        strongest = sorted(memories, key=lambda m: m.strength, reverse=True)[:5]
        summary["strongest_memories"] = [
            {
                "type": m.memory_type,
                "category": m.category,
                "key": m.key,
                "strength": m.strength
            } for m in strongest
        ]
        
        # Get recent memories
        recent = sorted(memories, key=lambda m: m.last_accessed, reverse=True)[:5]
        summary["recent_memories"] = [
            {
                "type": m.memory_type,
                "category": m.category,
                "key": m.key,
                "last_accessed": m.last_accessed
            } for m in recent
        ]
        
        return summary
    
    # Private methods
    async def _extract_entities(
        self,
        user_message: str,
        assistant_response: str
    ) -> Dict[str, Any]:
        """Extract entities and preferences from conversation"""
        
        # Simple keyword-based extraction (could be enhanced with NLP)
        preferences = {}
        context = {}
        
        message_lower = user_message.lower()
        
        # Extract preferences
        if "prefer" in message_lower or "like" in message_lower:
            if "email" in message_lower:
                preferences["contact_method"] = "email"
            elif "call" in message_lower or "phone" in message_lower:
                preferences["contact_method"] = "phone"
        
        if "morning" in message_lower:
            preferences["contact_time"] = "morning"
        elif "afternoon" in message_lower:
            preferences["contact_time"] = "afternoon"
        elif "evening" in message_lower:
            preferences["contact_time"] = "evening"
        
        # Extract context
        if "appointment" in message_lower:
            context["service_interest"] = "appointment"
        elif "support" in message_lower or "help" in message_lower:
            context["service_interest"] = "support"
        elif "billing" in message_lower or "payment" in message_lower:
            context["service_interest"] = "billing"
        
        return {
            "preferences": preferences,
            "context": context
        }
    
    async def _extract_topics(self, message: str) -> List[str]:
        """Extract main topics from message"""
        
        # Simple topic extraction
        topics = []
        message_lower = message.lower()
        
        topic_keywords = {
            "appointment": ["appointment", "schedule", "booking", "meeting"],
            "billing": ["bill", "payment", "charge", "invoice", "cost", "price"],
            "support": ["problem", "issue", "error", "help", "support", "trouble"],
            "product": ["product", "service", "feature", "plan", "package"],
            "account": ["account", "login", "password", "profile", "settings"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    async def _update_preference_memory(
        self,
        caller_email: str,
        phone_number: str,
        preferences: Dict[str, Any]
    ):
        """Update preference memories"""
        
        for key, value in preferences.items():
            await self.store_explicit_memory(
                visitor_email=caller_email,
                visitor_phone=phone_number,
                memory_type="preference",
                category="communication",
                key=key,
                value={"preference": value, "confidence": 0.8}
            )
    
    async def _update_context_memory(
        self,
        caller_email: str,
        phone_number: str,
        topics: List[str],
        context: Dict[str, Any]
    ):
        """Update contextual memories"""
        
        # Store topics
        for topic in topics:
            await self.store_explicit_memory(
                visitor_email=caller_email,
                visitor_phone=phone_number,
                memory_type="context",
                category="topic",
                key=topic,
                value={"discussed": True, "frequency": 1, "last_discussed": datetime.utcnow().isoformat()}
            )
        
        # Store context
        for key, value in context.items():
            await self.store_explicit_memory(
                visitor_email=caller_email,
                visitor_phone=phone_number,
                memory_type="context",
                category="service",
                key=key,
                value={"interest": value, "timestamp": datetime.utcnow().isoformat()}
            )
    
    async def _update_behavior_memory(
        self,
        caller_email: str,
        phone_number: str,
        user_message: str,
        assistant_response: str
    ):
        """Update behavioral memories"""
        
        # Analyze communication style
        message_length = len(user_message.split())
        is_direct = len(user_message) < 50
        asks_questions = "?" in user_message
        
        behavior_data = {
            "communication_style": "direct" if is_direct else "detailed",
            "avg_message_length": message_length,
            "asks_questions": asks_questions,
            "last_interaction": datetime.utcnow().isoformat()
        }
        
        await self.store_explicit_memory(
            visitor_email=caller_email,
            visitor_phone=phone_number,
            memory_type="behavior",
            category="communication_style",
            key="style_analysis",
            value=behavior_data
        )
    
    async def _update_interaction_count(
        self,
        caller_email: str,
        phone_number: str
    ):
        """Update interaction count memory"""
        
        # Get existing count
        filters = [
            ConversationMemory.memory_type == "behavior",
            ConversationMemory.category == "interaction_stats",
            ConversationMemory.key == "interaction_count"
        ]
        
        if caller_email:
            filters.append(ConversationMemory.caller_email == caller_email)
        if phone_number:
            filters.append(ConversationMemory.phone_number == phone_number)
        
        stmt = select(ConversationMemory).where(and_(*filters))
        result = await self.db.execute(stmt)
        existing_count = result.scalar_one_or_none()
        
        current_count = 1
        if existing_count:
            current_count = existing_count.value.get("count", 0) + 1
        
        await self.store_explicit_memory(
            visitor_email=caller_email,
            visitor_phone=phone_number,
            memory_type="behavior",
            category="interaction_stats",
            key="interaction_count",
            value={"count": current_count, "last_updated": datetime.utcnow().isoformat()}
        )