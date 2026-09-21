"""
Database models for AI Receptionist Service
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


# Enums
class ConversationType(str, Enum):
    PHONE = "phone"
    CHAT = "chat"
    EMAIL = "email"
    VOICE = "voice"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    TRANSFERRED = "transferred"
    ABANDONED = "abandoned"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    URGENT = "urgent"


class LanguageCode(str, Enum):
    EN_US = "en_us"
    ES_ES = "es_es"
    FR_FR = "fr_fr"
    DE_DE = "de_de"
    IT_IT = "it_it"
    PT_BR = "pt_br"
    ZH_CN = "zh_cn"
    JA_JP = "ja_jp"
    KO_KR = "ko_kr"
    RU_RU = "ru_ru"


class CallRoutingType(str, Enum):
    SALES = "sales"
    SUPPORT = "support"
    BILLING = "billing"
    TECHNICAL = "technical"
    APPOINTMENT = "appointment"
    GENERAL = "general"
    EMERGENCY = "emergency"


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class EscalationLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Core Models
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, nullable=False, index=True)
    conversation_type = Column(SQLEnum(ConversationType), nullable=False)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    language = Column(SQLEnum(LanguageCode), default=LanguageCode.EN_US)
    phone_number = Column(String, nullable=True)
    caller_name = Column(String, nullable=True)
    caller_email = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    routing_category = Column(SQLEnum(CallRoutingType), nullable=True)
    duration_seconds = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="conversation")
    voice_logs = relationship("VoiceLog", back_populates="conversation")
    sentiment_analysis = relationship("SentimentAnalysis", back_populates="conversation")
    escalations = relationship("EscalationTrigger", back_populates="conversation")
    appointments = relationship("Appointment", back_populates="conversation")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_type = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=True)
    intent = Column(String, nullable=True)
    entities = Column(JSON, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class VoiceLog(Base):
    __tablename__ = "voice_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audio_file_path = Column(String, nullable=True)
    transcription = Column(Text, nullable=False)
    transcription_confidence = Column(Float, nullable=True)
    speaker_id = Column(String, nullable=True)  # user, assistant
    duration_seconds = Column(Float, nullable=True)
    audio_quality_score = Column(Float, nullable=True)
    language_detected = Column(SQLEnum(LanguageCode), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="voice_logs")


class ConversationMemory(Base):
    __tablename__ = "conversation_memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_type = Column(String, nullable=False)  # preference, context, history
    category = Column(String, nullable=False)     # customer_info, product_interest, issue_type
    key = Column(String, nullable=False)          # specific memory key
    value = Column(JSON, nullable=False)          # memory data
    strength = Column(Float, default=1.0)        # memory importance/frequency
    last_accessed = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    phone_number = Column(String, nullable=True, index=True)
    caller_email = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TrainingData(Base):
    __tablename__ = "training_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_type = Column(String, nullable=False)
    user_input = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    user_feedback = Column(String, nullable=True)  # positive, negative, neutral
    feedback_score = Column(Float, nullable=True)  # 1-5 rating
    context = Column(JSON, nullable=True)
    intent_labels = Column(JSON, nullable=True)
    entity_labels = Column(JSON, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)


class AdminGuidance(Base):
    __tablename__ = "admin_guidance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)  # greeting, escalation, routing, etc.
    guidance_text = Column(Text, nullable=False)
    examples = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)    # When to use this guidance
    priority = Column(Integer, default=1)      # 1=highest, 10=lowest
    is_active = Column(Boolean, default=True)
    language = Column(SQLEnum(LanguageCode), default=LanguageCode.EN_US)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)


class LanguageTranslation(Base):
    __tablename__ = "language_translations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_language = Column(SQLEnum(LanguageCode), nullable=False)
    target_language = Column(SQLEnum(LanguageCode), nullable=False)
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=True)
    context_category = Column(String, nullable=True)
    is_validated = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class CallRouting(Base):
    __tablename__ = "call_routing"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    routing_rule = Column(String, nullable=False)
    category = Column(SQLEnum(CallRoutingType), nullable=False)
    keywords = Column(JSON, nullable=False)       # Keywords that trigger this routing
    conditions = Column(JSON, nullable=True)     # Additional conditions
    destination = Column(String, nullable=False) # Phone number, extension, or department
    priority = Column(Integer, default=1)
    business_hours_only = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    success_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    scheduled_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    attendee_name = Column(String, nullable=False)
    attendee_phone = Column(String, nullable=True)
    attendee_email = Column(String, nullable=True)
    staff_member = Column(String, nullable=True)
    location = Column(String, nullable=True)
    appointment_type = Column(String, nullable=False)
    reminder_sent = Column(Boolean, default=False)
    confirmation_sent = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="appointments")


class FAQ(Base):
    __tablename__ = "faqs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    keywords = Column(JSON, nullable=True)
    language = Column(SQLEnum(LanguageCode), default=LanguageCode.EN_US)
    usage_count = Column(Integer, default=0)
    effectiveness_score = Column(Float, default=0.0)
    is_auto_generated = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    source_conversations = Column(JSON, nullable=True)  # IDs of conversations that generated this FAQ
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analysis"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sentiment_type = Column(SQLEnum(SentimentType), nullable=False)
    confidence_score = Column(Float, nullable=False)
    emotional_indicators = Column(JSON, nullable=True)  # frustration, satisfaction, urgency markers
    tone_analysis = Column(JSON, nullable=True)         # formal, casual, aggressive, polite
    message_content = Column(Text, nullable=True)
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="sentiment_analysis")


class EscalationTrigger(Base):
    __tablename__ = "escalation_triggers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_type = Column(String, nullable=False)  # sentiment, keywords, duration, repeated_issue
    escalation_level = Column(SQLEnum(EscalationLevel), nullable=False)
    trigger_conditions = Column(JSON, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    escalation_reason = Column(Text, nullable=True)
    escalated_to = Column(String, nullable=True)    # Department or person
    resolution_time_minutes = Column(Integer, nullable=True)
    was_resolved = Column(Boolean, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="escalations")


class BusinessHours(Base):
    __tablename__ = "business_hours"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    open_time = Column(String, nullable=False)     # "09:00"
    close_time = Column(String, nullable=False)    # "17:00"
    timezone = Column(String, default="UTC")
    is_holiday = Column(Boolean, default=False)
    holiday_name = Column(String, nullable=True)
    special_message = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String, unique=True, nullable=False)
    setting_value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)  # phone, chat, voice, general
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(String, nullable=True)


# Database configuration
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/ai_receptionist"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()