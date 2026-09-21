"""
Website Helpbot Integration
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .database import (
    Conversation, ConversationMessage, ConversationMemory, 
    FAQ, SentimentAnalysis, EscalationTrigger,
    ConversationType, ConversationStatus, SentimentType
)
from .sentiment.sentiment_analyzer import SentimentAnalyzer
from .escalation.escalation_manager import EscalationManager
from .memory.memory_manager import MemoryManager
from .language.translation_service import TranslationService


class WebsiteHelpbot:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.sentiment_analyzer = SentimentAnalyzer()
        self.escalation_manager = EscalationManager(db_session)
        self.memory_manager = MemoryManager(db_session)
        self.translation_service = TranslationService(db_session)
        
    async def start_chat_session(
        self,
        session_id: str,
        visitor_info: Dict[str, Any] = None,
        language: str = "en_us"
    ) -> Dict[str, Any]:
        """Start a new chat session"""
        
        conversation = Conversation(
            session_id=session_id,
            conversation_type=ConversationType.CHAT,
            status=ConversationStatus.ACTIVE,
            language=language,
            caller_email=visitor_info.get("email") if visitor_info else None,
            caller_name=visitor_info.get("name") if visitor_info else None,
            company_name=visitor_info.get("company") if visitor_info else None,
            metadata={
                "visitor_info": visitor_info,
                "page_url": visitor_info.get("page_url") if visitor_info else None,
                "referrer": visitor_info.get("referrer") if visitor_info else None,
                "user_agent": visitor_info.get("user_agent") if visitor_info else None
            }
        )
        
        self.db.add(conversation)
        await self.db.commit()
        
        # Load visitor memory if available
        memory_context = await self.memory_manager.load_visitor_memory(
            visitor_info.get("email") if visitor_info else None
        )
        
        welcome_message = await self._generate_welcome_message(language, memory_context)
        
        # Log welcome message
        await self._log_message(
            conversation.id,
            "assistant",
            welcome_message,
            intent="greeting"
        )
        
        return {
            "conversation_id": str(conversation.id),
            "session_id": session_id,
            "welcome_message": welcome_message,
            "memory_context": memory_context,
            "supported_languages": [
                "en_us", "es_es", "fr_fr", "de_de", "it_it",
                "pt_br", "zh_cn", "ja_jp", "ko_kr", "ru_ru"
            ]
        }
    
    async def process_chat_message(
        self,
        conversation_id: str,
        message: str,
        visitor_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process incoming chat message"""
        
        conversation = await self._get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        
        # Log user message
        await self._log_message(
            conversation.id,
            "user",
            message
        )
        
        # Analyze sentiment
        sentiment = await self.sentiment_analyzer.analyze_text(message)
        await self._log_sentiment(conversation.id, sentiment)
        
        # Check for escalation triggers
        escalation_triggered = await self.escalation_manager.check_triggers(
            conversation.id,
            message,
            sentiment
        )
        
        # Get conversation memory
        memory_context = await self.memory_manager.load_conversation_memory(
            conversation.id
        )
        
        # Generate response
        response = await self._generate_response(
            message,
            conversation,
            memory_context,
            sentiment,
            escalation_triggered
        )
        
        # Log assistant response
        await self._log_message(
            conversation.id,
            "assistant",
            response["text"],
            confidence_score=response.get("confidence"),
            intent=response.get("intent")
        )
        
        # Update conversation memory
        await self.memory_manager.update_conversation_memory(
            conversation.id,
            message,
            response["text"],
            visitor_info
        )
        
        # Update conversation stats
        await self._update_conversation_stats(conversation.id)
        
        return {
            "response": response["text"],
            "confidence": response.get("confidence", 0.8),
            "intent": response.get("intent"),
            "sentiment": sentiment,
            "escalation_triggered": escalation_triggered,
            "suggested_actions": response.get("suggested_actions", []),
            "requires_human": escalation_triggered,
            "conversation_status": conversation.status.value
        }
    
    async def search_faqs(
        self,
        query: str,
        language: str = "en_us",
        category: str = None
    ) -> List[Dict[str, Any]]:
        """Search FAQ database for relevant answers"""
        
        # Simple keyword-based search (could be enhanced with semantic search)
        query_lower = query.lower()
        
        stmt = select(FAQ).where(
            FAQ.language == language,
            FAQ.is_approved == True
        )
        
        if category:
            stmt = stmt.where(FAQ.category == category)
        
        result = await self.db.execute(stmt)
        faqs = result.scalars().all()
        
        # Score FAQs based on keyword matches
        scored_faqs = []
        for faq in faqs:
            score = 0
            question_lower = faq.question.lower()
            answer_lower = faq.answer.lower()
            
            # Check for keyword matches
            keywords = faq.keywords or []
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 2
            
            # Check for direct text matches
            query_words = query_lower.split()
            for word in query_words:
                if word in question_lower:
                    score += 3
                if word in answer_lower:
                    score += 1
            
            if score > 0:
                scored_faqs.append({
                    "faq_id": str(faq.id),
                    "question": faq.question,
                    "answer": faq.answer,
                    "category": faq.category,
                    "score": score,
                    "usage_count": faq.usage_count
                })
        
        # Sort by score and return top results
        scored_faqs.sort(key=lambda x: x["score"], reverse=True)
        return scored_faqs[:5]
    
    async def end_chat_session(
        self,
        conversation_id: str,
        feedback: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """End chat session and collect feedback"""
        
        conversation = await self._get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        
        # Update conversation status
        stmt = update(Conversation).where(
            Conversation.id == conversation.id
        ).values(
            status=ConversationStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )
        await self.db.execute(stmt)
        
        # Log feedback if provided
        if feedback:
            await self._log_message(
                conversation.id,
                "system",
                json.dumps(feedback),
                intent="feedback"
            )
        
        await self.db.commit()
        
        # Generate session summary
        summary = await self._generate_session_summary(conversation.id)
        
        return {
            "session_summary": summary,
            "total_duration": (datetime.utcnow() - conversation.started_at).total_seconds(),
            "message_count": conversation.total_messages,
            "satisfaction_score": feedback.get("rating") if feedback else None
        }
    
    async def get_widget_config(self, website_domain: str) -> Dict[str, Any]:
        """Get chat widget configuration for website"""
        
        return {
            "widget_settings": {
                "position": "bottom-right",
                "theme_color": "#007bff",
                "welcome_message": "Hi! How can I help you today?",
                "placeholder_text": "Type your message...",
                "show_typing_indicator": True,
                "enable_file_upload": False,
                "enable_emoji": True,
                "max_message_length": 500
            },
            "features": {
                "sentiment_analysis": True,
                "auto_escalation": True,
                "faq_suggestions": True,
                "multi_language": True,
                "conversation_memory": True
            },
            "branding": {
                "company_name": "AI Assistant",
                "logo_url": None,
                "custom_css": None
            },
            "integrations": {
                "google_analytics": False,
                "zendesk": False,
                "salesforce": False
            }
        }
    
    # Private methods
    async def _get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        stmt = select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _log_message(
        self,
        conversation_id: uuid.UUID,
        message_type: str,
        content: str,
        confidence_score: float = None,
        intent: str = None
    ):
        message = ConversationMessage(
            conversation_id=conversation_id,
            message_type=message_type,
            content=content,
            confidence_score=confidence_score,
            intent=intent
        )
        self.db.add(message)
    
    async def _log_sentiment(self, conversation_id: uuid.UUID, sentiment: Dict[str, Any]):
        sentiment_record = SentimentAnalysis(
            conversation_id=conversation_id,
            sentiment_type=sentiment["type"],
            confidence_score=sentiment["confidence"],
            emotional_indicators=sentiment.get("emotions", {}),
            tone_analysis=sentiment.get("tone", {})
        )
        self.db.add(sentiment_record)
    
    async def _generate_welcome_message(
        self,
        language: str,
        memory_context: Dict[str, Any]
    ) -> str:
        """Generate personalized welcome message"""
        
        base_messages = {
            "en_us": "Hello! I'm your AI assistant. How can I help you today?",
            "es_es": "¡Hola! Soy tu asistente de IA. ¿Cómo puedo ayudarte hoy?",
            "fr_fr": "Bonjour ! Je suis votre assistant IA. Comment puis-je vous aider aujourd'hui ?",
            "de_de": "Hallo! Ich bin Ihr KI-Assistent. Wie kann ich Ihnen heute helfen?",
            "it_it": "Ciao! Sono il tuo assistente IA. Come posso aiutarti oggi?",
            "pt_br": "Olá! Eu sou seu assistente de IA. Como posso ajudá-lo hoje?",
            "zh_cn": "您好！我是您的AI助手。今天我能为您做些什么？",
            "ja_jp": "こんにちは！私はあなたのAIアシスタントです。今日はどのようにお手伝いできますか？",
            "ko_kr": "안녕하세요! 저는 AI 어시스턴트입니다. 오늘 어떻게 도와드릴까요?",
            "ru_ru": "Привет! Я ваш ИИ-помощник. Чем могу помочь вам сегодня?"
        }
        
        base_message = base_messages.get(language, base_messages["en_us"])
        
        # Personalize based on memory
        if memory_context and memory_context.get("returning_visitor"):
            personalized_greetings = {
                "en_us": f"Welcome back! I remember you were interested in {memory_context.get('last_topic', 'our services')}. How can I help you today?",
                "es_es": f"¡Bienvenido de vuelta! Recuerdo que estabas interesado en {memory_context.get('last_topic', 'nuestros servicios')}. ¿Cómo puedo ayudarte hoy?"
            }
            return personalized_greetings.get(language, base_message)
        
        return base_message
    
    async def _generate_response(
        self,
        message: str,
        conversation: Conversation,
        memory_context: Dict[str, Any],
        sentiment: Dict[str, Any],
        escalation_triggered: bool
    ) -> Dict[str, Any]:
        """Generate contextual response to user message"""
        
        if escalation_triggered:
            return {
                "text": "I understand this might be frustrating. Let me connect you with a human agent who can better assist you.",
                "intent": "escalation",
                "confidence": 1.0,
                "suggested_actions": ["transfer_to_human"]
            }
        
        # Search FAQs first
        faq_results = await self.search_faqs(message, conversation.language.value)
        if faq_results and faq_results[0]["score"] > 5:
            best_faq = faq_results[0]
            return {
                "text": best_faq["answer"],
                "intent": "faq_response",
                "confidence": 0.9,
                "suggested_actions": ["mark_helpful", "need_more_help"]
            }
        
        # Detect intent from message
        intent = await self._detect_intent(message)
        
        # Generate contextual response based on intent
        response_templates = {
            "greeting": {
                "en_us": "Hello! How can I assist you today?",
                "es_es": "¡Hola! ¿Cómo puedo asistirte hoy?"
            },
            "appointment": {
                "en_us": "I'd be happy to help you schedule an appointment. What type of appointment are you looking for?",
                "es_es": "Estaré encantado de ayudarte a programar una cita. ¿Qué tipo de cita estás buscando?"
            },
            "support": {
                "en_us": "I'm here to help with your support request. Can you tell me more about the issue you're experiencing?",
                "es_es": "Estoy aquí para ayudarte con tu solicitud de soporte. ¿Puedes contarme más sobre el problema que estás experimentando?"
            },
            "billing": {
                "en_us": "I can help with billing questions. What specific information do you need?",
                "es_es": "Puedo ayudarte con preguntas de facturación. ¿Qué información específica necesitas?"
            },
            "general": {
                "en_us": "I understand you have a question. Could you provide more details so I can better assist you?",
                "es_es": "Entiendo que tienes una pregunta. ¿Podrías proporcionar más detalles para poder ayudarte mejor?"
            }
        }
        
        template = response_templates.get(intent, response_templates["general"])
        response_text = template.get(conversation.language.value, template["en_us"])
        
        return {
            "text": response_text,
            "intent": intent,
            "confidence": 0.7,
            "suggested_actions": ["provide_more_info", "schedule_callback"]
        }
    
    async def _detect_intent(self, message: str) -> str:
        """Basic intent detection from message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return "greeting"
        elif any(word in message_lower for word in ["appointment", "schedule", "book", "meeting"]):
            return "appointment"
        elif any(word in message_lower for word in ["problem", "issue", "error", "bug", "help", "support"]):
            return "support"
        elif any(word in message_lower for word in ["bill", "payment", "charge", "invoice", "cost", "price"]):
            return "billing"
        else:
            return "general"
    
    async def _update_conversation_stats(self, conversation_id: uuid.UUID):
        """Update conversation statistics"""
        stmt = update(Conversation).where(
            Conversation.id == conversation_id
        ).values(
            total_messages=Conversation.total_messages + 1
        )
        await self.db.execute(stmt)
    
    async def _generate_session_summary(self, conversation_id: uuid.UUID) -> Dict[str, Any]:
        """Generate summary of chat session"""
        
        # Get all messages
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.timestamp)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Get sentiment analysis
        stmt = select(SentimentAnalysis).where(
            SentimentAnalysis.conversation_id == conversation_id
        )
        result = await self.db.execute(stmt)
        sentiments = result.scalars().all()
        
        return {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m.message_type == "user"]),
            "assistant_messages": len([m for m in messages if m.message_type == "assistant"]),
            "primary_intents": list(set([m.intent for m in messages if m.intent])),
            "overall_sentiment": sentiments[-1].sentiment_type.value if sentiments else "neutral",
            "escalated": any(s.sentiment_type == SentimentType.FRUSTRATED for s in sentiments),
            "topics_discussed": []  # Could be enhanced with topic extraction
        }