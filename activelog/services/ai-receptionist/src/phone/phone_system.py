"""
Phone Answering System
"""

import uuid
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..database import (
    Conversation, ConversationMessage, VoiceLog, CallRouting,
    BusinessHours, ConversationType, ConversationStatus, CallRoutingType
)
from ..voice.speech_processor import SpeechProcessor
from ..memory.memory_manager import MemoryManager
from ..escalation.escalation_manager import EscalationManager
from ..sentiment.sentiment_analyzer import SentimentAnalyzer


class PhoneSystem:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.speech_processor = SpeechProcessor()
        self.memory_manager = MemoryManager(db_session)
        self.escalation_manager = EscalationManager(db_session)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.active_calls = {}
        self.call_handlers = {}
        
    async def incoming_call(
        self,
        phone_number: str,
        caller_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle incoming phone call"""
        
        call_id = str(uuid.uuid4())
        
        # Check business hours
        is_business_hours = await self._check_business_hours()
        
        if not is_business_hours:
            return await self._handle_after_hours_call(call_id, phone_number, caller_id)
        
        # Create conversation record
        conversation = Conversation(
            session_id=call_id,
            conversation_type=ConversationType.PHONE,
            status=ConversationStatus.ACTIVE,
            phone_number=phone_number,
            caller_name=caller_id,
            metadata=metadata or {}
        )
        
        self.db.add(conversation)
        await self.db.commit()
        
        # Load caller memory
        caller_memory = await self.memory_manager.load_caller_memory(phone_number)
        
        # Generate greeting
        greeting = await self._generate_phone_greeting(caller_memory)
        
        # Start call session
        self.active_calls[call_id] = {
            "conversation_id": conversation.id,
            "phone_number": phone_number,
            "started_at": datetime.utcnow(),
            "language": "en_us",
            "routing_category": None,
            "memory_context": caller_memory
        }
        
        return {
            "call_id": call_id,
            "conversation_id": str(conversation.id),
            "greeting": greeting,
            "status": "connected",
            "next_action": "play_greeting_and_listen"
        }
    
    async def process_speech_input(
        self,
        call_id: str,
        audio_data: bytes,
        audio_format: str = "wav"
    ) -> Dict[str, Any]:
        """Process incoming speech from caller"""
        
        call_info = self.active_calls.get(call_id)
        if not call_info:
            raise ValueError("Call not found or ended")
        
        # Convert speech to text
        transcription_result = await self.speech_processor.speech_to_text(
            audio_data,
            language=call_info["language"],
            audio_format=audio_format
        )
        
        if not transcription_result["success"]:
            return {
                "response": "I'm sorry, I didn't catch that. Could you please repeat?",
                "audio_response": await self.speech_processor.text_to_speech(
                    "I'm sorry, I didn't catch that. Could you please repeat?",
                    language=call_info["language"]
                )
            }
        
        transcription = transcription_result["text"]
        confidence = transcription_result["confidence"]
        
        # Log voice input
        await self._log_voice_input(
            call_info["conversation_id"],
            transcription,
            confidence,
            audio_data,
            audio_format
        )
        
        # Analyze sentiment
        sentiment = await self.sentiment_analyzer.analyze_text(transcription)
        
        # Check for escalation triggers
        escalation_triggered = await self.escalation_manager.check_triggers(
            call_info["conversation_id"],
            transcription,
            sentiment
        )
        
        if escalation_triggered:
            return await self._handle_escalation(call_id, transcription)
        
        # Detect intent and route call if needed
        if not call_info["routing_category"]:
            routing_result = await self._detect_call_routing(transcription)
            if routing_result:
                call_info["routing_category"] = routing_result["category"]
                return await self._route_call(call_id, routing_result)
        
        # Generate response
        response = await self._generate_phone_response(
            call_id,
            transcription,
            sentiment,
            call_info
        )
        
        # Convert response to speech
        audio_response = await self.speech_processor.text_to_speech(
            response["text"],
            language=call_info["language"],
            voice_settings={"speed": 1.0, "pitch": 1.0}
        )
        
        # Log assistant response
        await self._log_voice_response(
            call_info["conversation_id"],
            response["text"],
            audio_response
        )
        
        # Update call memory
        await self.memory_manager.update_call_memory(
            call_info["conversation_id"],
            call_info["phone_number"],
            transcription,
            response["text"]
        )
        
        return {
            "response": response["text"],
            "audio_response": audio_response,
            "confidence": confidence,
            "intent": response.get("intent"),
            "routing_category": call_info["routing_category"],
            "next_action": response.get("next_action", "listen")
        }
    
    async def transfer_call(
        self,
        call_id: str,
        destination: str,
        reason: str = None
    ) -> Dict[str, Any]:
        """Transfer call to human agent or department"""
        
        call_info = self.active_calls.get(call_id)
        if not call_info:
            raise ValueError("Call not found")
        
        # Update conversation status
        stmt = update(Conversation).where(
            Conversation.id == call_info["conversation_id"]
        ).values(
            status=ConversationStatus.TRANSFERRED,
            metadata=Conversation.metadata.op('||')({
                "transferred_to": destination,
                "transfer_reason": reason,
                "transferred_at": datetime.utcnow().isoformat()
            })
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Generate transfer message
        transfer_message = f"Please hold while I transfer you to {destination}."
        audio_response = await self.speech_processor.text_to_speech(
            transfer_message,
            language=call_info["language"]
        )
        
        # Remove from active calls
        self.active_calls.pop(call_id, None)
        
        return {
            "transfer_message": transfer_message,
            "audio_response": audio_response,
            "destination": destination,
            "status": "transferred"
        }
    
    async def end_call(
        self,
        call_id: str,
        reason: str = "completed"
    ) -> Dict[str, Any]:
        """End phone call"""
        
        call_info = self.active_calls.get(call_id)
        if not call_info:
            return {"status": "call_not_found"}
        
        # Calculate call duration
        duration = (datetime.utcnow() - call_info["started_at"]).total_seconds()
        
        # Update conversation
        stmt = update(Conversation).where(
            Conversation.id == call_info["conversation_id"]
        ).values(
            status=ConversationStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            duration_seconds=int(duration),
            metadata=Conversation.metadata.op('||')({
                "end_reason": reason,
                "final_routing_category": call_info["routing_category"]
            })
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Remove from active calls
        self.active_calls.pop(call_id, None)
        
        return {
            "call_duration": duration,
            "status": "ended",
            "reason": reason,
            "conversation_id": str(call_info["conversation_id"])
        }
    
    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Get current call status"""
        
        call_info = self.active_calls.get(call_id)
        if not call_info:
            return {"status": "not_found"}
        
        return {
            "status": "active",
            "duration": (datetime.utcnow() - call_info["started_at"]).total_seconds(),
            "phone_number": call_info["phone_number"],
            "routing_category": call_info["routing_category"],
            "language": call_info["language"]
        }
    
    async def update_call_routing_rules(
        self,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update call routing rules"""
        
        for rule in rules:
            # Check if rule exists
            stmt = select(CallRouting).where(
                CallRouting.routing_rule == rule["name"]
            )
            result = await self.db.execute(stmt)
            existing_rule = result.scalar_one_or_none()
            
            if existing_rule:
                # Update existing rule
                stmt = update(CallRouting).where(
                    CallRouting.id == existing_rule.id
                ).values(
                    category=rule["category"],
                    keywords=rule["keywords"],
                    conditions=rule.get("conditions", {}),
                    destination=rule["destination"],
                    priority=rule.get("priority", 1),
                    business_hours_only=rule.get("business_hours_only", True),
                    is_active=rule.get("is_active", True)
                )
                await self.db.execute(stmt)
            else:
                # Create new rule
                new_rule = CallRouting(
                    routing_rule=rule["name"],
                    category=rule["category"],
                    keywords=rule["keywords"],
                    conditions=rule.get("conditions", {}),
                    destination=rule["destination"],
                    priority=rule.get("priority", 1),
                    business_hours_only=rule.get("business_hours_only", True),
                    is_active=rule.get("is_active", True)
                )
                self.db.add(new_rule)
        
        await self.db.commit()
        return {"status": "updated", "rules_count": len(rules)}
    
    # Private methods
    async def _check_business_hours(self) -> bool:
        """Check if current time is within business hours"""
        
        current_time = datetime.utcnow()
        day_of_week = current_time.weekday()  # 0=Monday, 6=Sunday
        current_hour_minute = current_time.strftime("%H:%M")
        
        stmt = select(BusinessHours).where(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_active == True,
            BusinessHours.is_holiday == False
        )
        result = await self.db.execute(stmt)
        business_hours = result.scalar_one_or_none()
        
        if not business_hours:
            return False
        
        return (business_hours.open_time <= current_hour_minute <= business_hours.close_time)
    
    async def _handle_after_hours_call(
        self,
        call_id: str,
        phone_number: str,
        caller_id: str
    ) -> Dict[str, Any]:
        """Handle calls received outside business hours"""
        
        # Create conversation record
        conversation = Conversation(
            session_id=call_id,
            conversation_type=ConversationType.PHONE,
            status=ConversationStatus.COMPLETED,
            phone_number=phone_number,
            caller_name=caller_id,
            metadata={"after_hours_call": True}
        )
        
        self.db.add(conversation)
        await self.db.commit()
        
        after_hours_message = (
            "Thank you for calling. Our office is currently closed. "
            "Our business hours are Monday through Friday, 9 AM to 5 PM. "
            "Please call back during business hours or leave a message after the tone."
        )
        
        audio_response = await self.speech_processor.text_to_speech(
            after_hours_message,
            language="en_us"
        )
        
        return {
            "call_id": call_id,
            "conversation_id": str(conversation.id),
            "message": after_hours_message,
            "audio_response": audio_response,
            "status": "after_hours",
            "next_action": "voicemail"
        }
    
    async def _generate_phone_greeting(
        self,
        caller_memory: Dict[str, Any]
    ) -> str:
        """Generate personalized phone greeting"""
        
        if caller_memory and caller_memory.get("returning_caller"):
            return f"Hello, welcome back to our company! How can I assist you today?"
        
        return (
            "Hello, thank you for calling our company. "
            "I'm your AI assistant. How may I help you today?"
        )
    
    async def _log_voice_input(
        self,
        conversation_id: uuid.UUID,
        transcription: str,
        confidence: float,
        audio_data: bytes,
        audio_format: str
    ):
        """Log voice input to database"""
        
        voice_log = VoiceLog(
            conversation_id=conversation_id,
            transcription=transcription,
            transcription_confidence=confidence,
            speaker_id="user",
            audio_quality_score=confidence,
            duration_seconds=len(audio_data) / 16000.0  # Approximate duration
        )
        
        self.db.add(voice_log)
        
        # Also log as conversation message
        message = ConversationMessage(
            conversation_id=conversation_id,
            message_type="user",
            content=transcription,
            confidence_score=confidence
        )
        self.db.add(message)
    
    async def _log_voice_response(
        self,
        conversation_id: uuid.UUID,
        response_text: str,
        audio_data: bytes
    ):
        """Log voice response to database"""
        
        voice_log = VoiceLog(
            conversation_id=conversation_id,
            transcription=response_text,
            transcription_confidence=1.0,
            speaker_id="assistant",
            duration_seconds=len(audio_data) / 16000.0
        )
        
        self.db.add(voice_log)
        
        # Also log as conversation message
        message = ConversationMessage(
            conversation_id=conversation_id,
            message_type="assistant",
            content=response_text,
            confidence_score=1.0
        )
        self.db.add(message)
    
    async def _detect_call_routing(self, transcription: str) -> Optional[Dict[str, Any]]:
        """Detect which department/category this call should be routed to"""
        
        # Get all routing rules
        stmt = select(CallRouting).where(
            CallRouting.is_active == True
        ).order_by(CallRouting.priority)
        result = await self.db.execute(stmt)
        routing_rules = result.scalars().all()
        
        transcription_lower = transcription.lower()
        
        for rule in routing_rules:
            # Check if any keywords match
            for keyword in rule.keywords:
                if keyword.lower() in transcription_lower:
                    return {
                        "category": rule.category,
                        "destination": rule.destination,
                        "rule_name": rule.routing_rule,
                        "matched_keyword": keyword
                    }
        
        return None
    
    async def _route_call(
        self,
        call_id: str,
        routing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route call to appropriate destination"""
        
        category = routing_result["category"]
        destination = routing_result["destination"]
        
        routing_messages = {
            CallRoutingType.SALES: "I'll connect you with our sales team.",
            CallRoutingType.SUPPORT: "Let me transfer you to our technical support team.",
            CallRoutingType.BILLING: "I'll connect you with our billing department.",
            CallRoutingType.TECHNICAL: "Transferring you to our technical specialists.",
            CallRoutingType.APPOINTMENT: "I can help you schedule an appointment. What type of appointment do you need?",
            CallRoutingType.EMERGENCY: "This sounds urgent. Let me connect you with someone immediately.",
            CallRoutingType.GENERAL: "I'll help you with your inquiry."
        }
        
        message = routing_messages.get(
            category, 
            f"I'll connect you with the right department."
        )
        
        # For appointments, don't transfer - handle internally
        if category == CallRoutingType.APPOINTMENT:
            audio_response = await self.speech_processor.text_to_speech(message)
            return {
                "response": message,
                "audio_response": audio_response,
                "routing_category": category.value,
                "next_action": "handle_appointment"
            }
        
        # For other categories, initiate transfer
        return await self.transfer_call(call_id, destination, f"Routed to {category.value}")
    
    async def _generate_phone_response(
        self,
        call_id: str,
        transcription: str,
        sentiment: Dict[str, Any],
        call_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate contextual phone response"""
        
        # Check if this is appointment-related
        if call_info["routing_category"] == CallRoutingType.APPOINTMENT:
            return await self._handle_appointment_request(transcription)
        
        # Default response generation
        response_templates = {
            "greeting": "Hello! How can I assist you today?",
            "confirmation": "I understand. Let me help you with that.",
            "clarification": "Could you please provide more details about that?",
            "hold": "Please hold while I look that up for you.",
            "thanks": "Thank you for that information."
        }
        
        # Simple intent detection for phone
        if any(word in transcription.lower() for word in ["hello", "hi", "calling"]):
            intent = "greeting"
        elif any(word in transcription.lower() for word in ["yes", "correct", "right"]):
            intent = "confirmation"
        elif "?" in transcription:
            intent = "clarification"
        else:
            intent = "confirmation"
        
        response_text = response_templates.get(intent, response_templates["confirmation"])
        
        return {
            "text": response_text,
            "intent": intent,
            "next_action": "listen"
        }
    
    async def _handle_appointment_request(self, transcription: str) -> Dict[str, Any]:
        """Handle appointment scheduling request"""
        
        # This would integrate with the scheduling system
        return {
            "text": "I'd be happy to help you schedule an appointment. What type of service are you interested in?",
            "intent": "appointment_inquiry",
            "next_action": "collect_appointment_details"
        }
    
    async def _handle_escalation(
        self,
        call_id: str,
        transcription: str
    ) -> Dict[str, Any]:
        """Handle call escalation to human agent"""
        
        escalation_message = (
            "I understand your concern and want to make sure you get the help you need. "
            "Let me connect you with one of our specialists who can better assist you."
        )
        
        return await self.transfer_call(
            call_id,
            "human_agent",
            "Escalated due to sentiment analysis"
        )