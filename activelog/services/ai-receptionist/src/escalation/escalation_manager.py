"""
Escalation Triggers and Management System
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from ..database import (
    EscalationTrigger, Conversation, ConversationMessage, SentimentAnalysis,
    EscalationLevel, ConversationStatus
)


class EscalationManager:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # Escalation trigger rules
        self.trigger_rules = {
            "sentiment_negative": {
                "threshold": 0.7,
                "level": EscalationLevel.MEDIUM,
                "description": "High negative sentiment detected"
            },
            "sentiment_frustrated": {
                "threshold": 0.6,
                "level": EscalationLevel.HIGH,
                "description": "Customer frustration detected"
            },
            "repeated_issue": {
                "threshold": 3,  # number of similar messages
                "level": EscalationLevel.MEDIUM,
                "description": "Customer repeating the same issue"
            },
            "conversation_length": {
                "threshold": 20,  # number of messages
                "level": EscalationLevel.LOW,
                "description": "Long conversation without resolution"
            },
            "urgency_keywords": {
                "keywords": ["emergency", "urgent", "critical", "asap", "immediately"],
                "level": EscalationLevel.HIGH,
                "description": "Urgent language detected"
            },
            "escalation_request": {
                "keywords": ["manager", "supervisor", "human", "person", "speak to someone"],
                "level": EscalationLevel.CRITICAL,
                "description": "Customer requesting human agent"
            },
            "aggressive_language": {
                "keywords": ["terrible", "awful", "horrible", "incompetent", "stupid", "pathetic"],
                "level": EscalationLevel.HIGH,
                "description": "Aggressive language detected"
            },
            "billing_dispute": {
                "keywords": ["overcharged", "wrong charge", "billing error", "refund", "dispute"],
                "level": EscalationLevel.HIGH,
                "description": "Billing dispute detected"
            },
            "multiple_channels": {
                "threshold": 2,  # contacted via multiple channels
                "level": EscalationLevel.MEDIUM,
                "description": "Customer contacted via multiple channels"
            },
            "callback_request": {
                "keywords": ["call me back", "callback", "phone call", "speak on phone"],
                "level": EscalationLevel.MEDIUM,
                "description": "Customer requesting callback"
            }
        }
        
        # Department routing rules
        self.escalation_routing = {
            EscalationLevel.LOW: "senior_agent",
            EscalationLevel.MEDIUM: "team_lead",
            EscalationLevel.HIGH: "manager",
            EscalationLevel.CRITICAL: "director"
        }
    
    async def check_triggers(
        self,
        conversation_id: uuid.UUID,
        message_text: str,
        sentiment_analysis: Dict[str, Any]
    ) -> bool:
        """Check if any escalation triggers are activated"""
        
        triggered_rules = []
        
        # Check sentiment-based triggers
        sentiment_triggers = await self._check_sentiment_triggers(sentiment_analysis)
        triggered_rules.extend(sentiment_triggers)
        
        # Check keyword-based triggers
        keyword_triggers = await self._check_keyword_triggers(message_text)
        triggered_rules.extend(keyword_triggers)
        
        # Check conversation pattern triggers
        pattern_triggers = await self._check_conversation_patterns(conversation_id, message_text)
        triggered_rules.extend(pattern_triggers)
        
        # Check historical triggers
        historical_triggers = await self._check_historical_patterns(conversation_id)
        triggered_rules.extend(historical_triggers)
        
        if triggered_rules:
            # Determine highest priority trigger
            highest_level = max(trigger["level"] for trigger in triggered_rules)
            primary_trigger = next(t for t in triggered_rules if t["level"] == highest_level)
            
            # Create escalation record
            await self._create_escalation_trigger(
                conversation_id,
                primary_trigger,
                triggered_rules
            )
            
            return True
        
        return False
    
    async def get_escalation_recommendations(
        self,
        conversation_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get escalation recommendations for conversation"""
        
        # Get conversation history
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.timestamp)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Get sentiment history
        stmt = select(SentimentAnalysis).where(
            SentimentAnalysis.conversation_id == conversation_id
        ).order_by(SentimentAnalysis.analysis_timestamp)
        result = await self.db.execute(stmt)
        sentiments = result.scalars().all()
        
        # Analyze patterns
        analysis = {
            "conversation_length": len(messages),
            "user_messages": len([m for m in messages if m.message_type == "user"]),
            "sentiment_trend": self._analyze_sentiment_trend(sentiments),
            "escalation_indicators": await self._get_escalation_indicators(conversation_id),
            "resolution_probability": await self._calculate_resolution_probability(conversation_id)
        }
        
        # Generate recommendations
        recommendations = await self._generate_escalation_recommendations(analysis)
        
        return {
            "should_escalate": recommendations["escalate"],
            "escalation_level": recommendations["level"],
            "reasoning": recommendations["reason"],
            "suggested_actions": recommendations["actions"],
            "department": self.escalation_routing.get(recommendations["level"], "general"),
            "priority": recommendations["priority"],
            "analysis": analysis
        }
    
    async def escalate_conversation(
        self,
        conversation_id: uuid.UUID,
        escalation_level: EscalationLevel,
        reason: str,
        escalated_by: str = "system",
        notes: str = None
    ) -> Dict[str, Any]:
        """Escalate conversation to human agent"""
        
        # Update conversation status
        stmt = update(Conversation).where(
            Conversation.id == conversation_id
        ).values(
            status=ConversationStatus.ESCALATED,
            metadata=Conversation.metadata.op('||')({
                "escalated_at": datetime.utcnow().isoformat(),
                "escalated_by": escalated_by,
                "escalation_level": escalation_level.value,
                "escalation_reason": reason
            })
        )
        await self.db.execute(stmt)
        
        # Create escalation trigger record
        escalation = EscalationTrigger(
            conversation_id=conversation_id,
            trigger_type="manual_escalation",
            escalation_level=escalation_level,
            trigger_conditions={"manual": True, "escalated_by": escalated_by},
            escalation_reason=reason,
            escalated_to=self.escalation_routing[escalation_level],
            resolution_notes=notes
        )
        
        self.db.add(escalation)
        await self.db.commit()
        
        # Generate handover information
        handover_info = await self._generate_handover_info(conversation_id)
        
        return {
            "escalation_id": str(escalation.id),
            "escalated_to": escalation.escalated_to,
            "escalation_level": escalation_level.value,
            "handover_info": handover_info,
            "priority": self._get_priority_from_level(escalation_level),
            "estimated_response_time": self._get_response_time_estimate(escalation_level)
        }
    
    async def resolve_escalation(
        self,
        escalation_id: str,
        resolution_notes: str,
        resolution_time_minutes: int = None
    ) -> Dict[str, Any]:
        """Mark escalation as resolved"""
        
        # Update escalation record
        stmt = update(EscalationTrigger).where(
            EscalationTrigger.id == uuid.UUID(escalation_id)
        ).values(
            was_resolved=True,
            resolution_notes=resolution_notes,
            resolution_time_minutes=resolution_time_minutes
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        return {
            "status": "resolved",
            "resolution_time": resolution_time_minutes,
            "notes": resolution_notes
        }
    
    async def get_escalation_analytics(
        self,
        date_from: datetime = None,
        date_to: datetime = None
    ) -> Dict[str, Any]:
        """Get escalation analytics and metrics"""
        
        # Default to last 30 days
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=30)
        if not date_to:
            date_to = datetime.utcnow()
        
        # Get escalations in date range
        stmt = select(EscalationTrigger).where(
            and_(
                EscalationTrigger.triggered_at >= date_from,
                EscalationTrigger.triggered_at <= date_to
            )
        )
        result = await self.db.execute(stmt)
        escalations = result.scalars().all()
        
        if not escalations:
            return {"total_escalations": 0}
        
        # Calculate metrics
        total_escalations = len(escalations)
        resolved_escalations = len([e for e in escalations if e.was_resolved])
        avg_resolution_time = None
        
        resolution_times = [e.resolution_time_minutes for e in escalations 
                          if e.resolution_time_minutes is not None]
        if resolution_times:
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        # Group by trigger type
        trigger_types = {}
        for escalation in escalations:
            trigger_type = escalation.trigger_type
            if trigger_type not in trigger_types:
                trigger_types[trigger_type] = 0
            trigger_types[trigger_type] += 1
        
        # Group by escalation level
        escalation_levels = {}
        for escalation in escalations:
            level = escalation.escalation_level.value
            if level not in escalation_levels:
                escalation_levels[level] = 0
            escalation_levels[level] += 1
        
        return {
            "total_escalations": total_escalations,
            "resolved_escalations": resolved_escalations,
            "resolution_rate": resolved_escalations / total_escalations if total_escalations > 0 else 0,
            "average_resolution_time_minutes": avg_resolution_time,
            "trigger_type_breakdown": trigger_types,
            "escalation_level_breakdown": escalation_levels,
            "escalation_trend": self._calculate_escalation_trend(escalations),
            "top_escalation_triggers": sorted(trigger_types.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    # Private methods
    async def _check_sentiment_triggers(self, sentiment_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check sentiment-based escalation triggers"""
        
        triggers = []
        
        # Check negative sentiment
        if (sentiment_analysis.get("type") == "negative" and 
            sentiment_analysis.get("confidence", 0) > self.trigger_rules["sentiment_negative"]["threshold"]):
            triggers.append({
                "rule": "sentiment_negative",
                "level": self.trigger_rules["sentiment_negative"]["level"],
                "description": self.trigger_rules["sentiment_negative"]["description"],
                "details": {"sentiment_score": sentiment_analysis.get("score", 0)}
            })
        
        # Check frustrated sentiment
        if (sentiment_analysis.get("frustration_level", 0) > self.trigger_rules["sentiment_frustrated"]["threshold"]):
            triggers.append({
                "rule": "sentiment_frustrated",
                "level": self.trigger_rules["sentiment_frustrated"]["level"],
                "description": self.trigger_rules["sentiment_frustrated"]["description"],
                "details": {"frustration_level": sentiment_analysis.get("frustration_level", 0)}
            })
        
        return triggers
    
    async def _check_keyword_triggers(self, message_text: str) -> List[Dict[str, Any]]:
        """Check keyword-based escalation triggers"""
        
        triggers = []
        message_lower = message_text.lower()
        
        # Check each keyword rule
        for rule_name in ["urgency_keywords", "escalation_request", "aggressive_language", 
                         "billing_dispute", "callback_request"]:
            rule = self.trigger_rules[rule_name]
            matched_keywords = [kw for kw in rule["keywords"] if kw in message_lower]
            
            if matched_keywords:
                triggers.append({
                    "rule": rule_name,
                    "level": rule["level"],
                    "description": rule["description"],
                    "details": {"matched_keywords": matched_keywords}
                })
        
        return triggers
    
    async def _check_conversation_patterns(
        self,
        conversation_id: uuid.UUID,
        current_message: str
    ) -> List[Dict[str, Any]]:
        """Check conversation pattern-based triggers"""
        
        triggers = []
        
        # Get conversation messages
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Check conversation length
        if len(messages) > self.trigger_rules["conversation_length"]["threshold"]:
            triggers.append({
                "rule": "conversation_length",
                "level": self.trigger_rules["conversation_length"]["level"],
                "description": self.trigger_rules["conversation_length"]["description"],
                "details": {"message_count": len(messages)}
            })
        
        # Check for repeated issues
        user_messages = [m.content.lower() for m in messages if m.message_type == "user"]
        repeated_count = self._count_similar_messages(user_messages, current_message.lower())
        
        if repeated_count >= self.trigger_rules["repeated_issue"]["threshold"]:
            triggers.append({
                "rule": "repeated_issue",
                "level": self.trigger_rules["repeated_issue"]["level"],
                "description": self.trigger_rules["repeated_issue"]["description"],
                "details": {"repetition_count": repeated_count}
            })
        
        return triggers
    
    async def _check_historical_patterns(self, conversation_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Check historical escalation patterns"""
        
        triggers = []
        
        # Get conversation info
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return triggers
        
        # Check for multiple channel usage (if customer contacted via different channels)
        if conversation.phone_number and conversation.caller_email:
            # Check if customer has recent conversations on different channels
            recent_conversations = await self._get_recent_conversations(
                conversation.caller_email,
                conversation.phone_number
            )
            
            if len(recent_conversations) >= self.trigger_rules["multiple_channels"]["threshold"]:
                triggers.append({
                    "rule": "multiple_channels",
                    "level": self.trigger_rules["multiple_channels"]["level"],
                    "description": self.trigger_rules["multiple_channels"]["description"],
                    "details": {"channel_count": len(recent_conversations)}
                })
        
        return triggers
    
    async def _create_escalation_trigger(
        self,
        conversation_id: uuid.UUID,
        primary_trigger: Dict[str, Any],
        all_triggers: List[Dict[str, Any]]
    ):
        """Create escalation trigger record"""
        
        escalation = EscalationTrigger(
            conversation_id=conversation_id,
            trigger_type=primary_trigger["rule"],
            escalation_level=primary_trigger["level"],
            trigger_conditions={
                "primary_trigger": primary_trigger,
                "all_triggers": all_triggers,
                "trigger_count": len(all_triggers)
            },
            escalation_reason=primary_trigger["description"],
            escalated_to=self.escalation_routing[primary_trigger["level"]]
        )
        
        self.db.add(escalation)
        await self.db.commit()
    
    def _count_similar_messages(self, messages: List[str], current_message: str) -> int:
        """Count how many similar messages were sent"""
        
        current_words = set(current_message.split())
        similar_count = 0
        
        for message in messages:
            message_words = set(message.split())
            # Calculate word overlap
            if len(current_words) > 0:
                overlap = len(current_words & message_words) / len(current_words)
                if overlap > 0.5:  # More than 50% word overlap
                    similar_count += 1
        
        return similar_count
    
    async def _get_recent_conversations(
        self,
        caller_email: str = None,
        phone_number: str = None
    ) -> List[Conversation]:
        """Get recent conversations for this contact"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        filters = [Conversation.started_at >= cutoff_date]
        
        if caller_email:
            filters.append(Conversation.caller_email == caller_email)
        if phone_number:
            filters.append(Conversation.phone_number == phone_number)
        
        if len(filters) == 1:  # Only date filter
            return []
        
        stmt = select(Conversation).where(and_(*filters))
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    def _analyze_sentiment_trend(self, sentiments: List[SentimentAnalysis]) -> str:
        """Analyze sentiment trend over conversation"""
        
        if len(sentiments) < 2:
            return "insufficient_data"
        
        recent_sentiments = sentiments[-3:]  # Last 3 sentiment analyses
        early_sentiments = sentiments[:3]    # First 3 sentiment analyses
        
        recent_avg = sum(1 if s.sentiment_type.value == "positive" else
                        -1 if s.sentiment_type.value == "negative" else 0
                        for s in recent_sentiments) / len(recent_sentiments)
        
        early_avg = sum(1 if s.sentiment_type.value == "positive" else
                       -1 if s.sentiment_type.value == "negative" else 0
                       for s in early_sentiments) / len(early_sentiments)
        
        if recent_avg < early_avg - 0.5:
            return "deteriorating"
        elif recent_avg > early_avg + 0.5:
            return "improving"
        else:
            return "stable"
    
    async def _get_escalation_indicators(self, conversation_id: uuid.UUID) -> List[str]:
        """Get escalation indicators for conversation"""
        
        # Get existing escalation triggers
        stmt = select(EscalationTrigger).where(
            EscalationTrigger.conversation_id == conversation_id
        )
        result = await self.db.execute(stmt)
        triggers = result.scalars().all()
        
        return [trigger.trigger_type for trigger in triggers]
    
    async def _calculate_resolution_probability(self, conversation_id: uuid.UUID) -> float:
        """Calculate probability of resolving without escalation"""
        
        # Get conversation length and sentiment
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Simple heuristic: shorter conversations and recent positive sentiment = higher probability
        message_count = len(messages)
        base_probability = max(0.1, 1.0 - (message_count / 30))  # Decreases with length
        
        # Get recent sentiment
        stmt = select(SentimentAnalysis).where(
            SentimentAnalysis.conversation_id == conversation_id
        ).order_by(SentimentAnalysis.analysis_timestamp.desc()).limit(1)
        result = await self.db.execute(stmt)
        recent_sentiment = result.scalar_one_or_none()
        
        if recent_sentiment:
            if recent_sentiment.sentiment_type.value == "positive":
                base_probability += 0.2
            elif recent_sentiment.sentiment_type.value == "negative":
                base_probability -= 0.2
            elif recent_sentiment.sentiment_type.value == "frustrated":
                base_probability -= 0.4
        
        return max(0.0, min(1.0, base_probability))
    
    async def _generate_escalation_recommendations(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate escalation recommendations based on analysis"""
        
        escalate = False
        level = EscalationLevel.LOW
        reason = "No escalation needed"
        actions = ["continue_conversation"]
        priority = "normal"
        
        # Decision logic
        if analysis["resolution_probability"] < 0.2:
            escalate = True
            level = EscalationLevel.MEDIUM
            reason = "Low probability of resolution"
            actions = ["escalate_to_human", "provide_callback_option"]
            priority = "medium"
        
        if analysis["conversation_length"] > 25:
            escalate = True
            level = EscalationLevel.HIGH
            reason = "Extended conversation without resolution"
            priority = "high"
        
        if analysis["sentiment_trend"] == "deteriorating":
            escalate = True
            level = EscalationLevel.HIGH
            reason = "Customer sentiment deteriorating"
            priority = "high"
        
        if len(analysis["escalation_indicators"]) > 2:
            escalate = True
            level = EscalationLevel.CRITICAL
            reason = "Multiple escalation indicators"
            actions = ["immediate_escalation", "manager_notification"]
            priority = "critical"
        
        return {
            "escalate": escalate,
            "level": level,
            "reason": reason,
            "actions": actions,
            "priority": priority
        }
    
    async def _generate_handover_info(self, conversation_id: uuid.UUID) -> Dict[str, Any]:
        """Generate handover information for human agent"""
        
        # Get conversation summary
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {}
        
        # Get messages
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.timestamp)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Get escalation triggers
        stmt = select(EscalationTrigger).where(
            EscalationTrigger.conversation_id == conversation_id
        ).order_by(EscalationTrigger.triggered_at.desc())
        result = await self.db.execute(stmt)
        triggers = result.scalars().all()
        
        return {
            "customer_info": {
                "name": conversation.caller_name,
                "phone": conversation.phone_number,
                "email": conversation.caller_email,
                "company": conversation.company_name
            },
            "conversation_summary": {
                "started_at": conversation.started_at.isoformat(),
                "duration_minutes": (datetime.utcnow() - conversation.started_at).total_seconds() / 60,
                "message_count": len(messages),
                "conversation_type": conversation.conversation_type.value,
                "routing_category": conversation.routing_category.value if conversation.routing_category else None
            },
            "escalation_reasons": [trigger.escalation_reason for trigger in triggers],
            "key_messages": [
                {"timestamp": msg.timestamp.isoformat(), "content": msg.content}
                for msg in messages[-5:] if msg.message_type == "user"  # Last 5 user messages
            ],
            "suggested_next_steps": self._get_suggested_next_steps(triggers),
            "priority": self._get_priority_from_triggers(triggers)
        }
    
    def _get_priority_from_level(self, level: EscalationLevel) -> str:
        """Get priority from escalation level"""
        return {
            EscalationLevel.LOW: "normal",
            EscalationLevel.MEDIUM: "medium",
            EscalationLevel.HIGH: "high",
            EscalationLevel.CRITICAL: "critical"
        }.get(level, "normal")
    
    def _get_response_time_estimate(self, level: EscalationLevel) -> str:
        """Get estimated response time"""
        return {
            EscalationLevel.LOW: "within 2 hours",
            EscalationLevel.MEDIUM: "within 1 hour",
            EscalationLevel.HIGH: "within 30 minutes",
            EscalationLevel.CRITICAL: "within 10 minutes"
        }.get(level, "within 2 hours")
    
    def _calculate_escalation_trend(self, escalations: List[EscalationTrigger]) -> str:
        """Calculate escalation trend over time"""
        
        if len(escalations) < 2:
            return "insufficient_data"
        
        # Group by week
        from collections import defaultdict
        weekly_counts = defaultdict(int)
        
        for escalation in escalations:
            week = escalation.triggered_at.strftime("%Y-W%U")
            weekly_counts[week] += 1
        
        weeks = sorted(weekly_counts.keys())
        if len(weeks) < 2:
            return "stable"
        
        recent_avg = sum(weekly_counts[week] for week in weeks[-2:]) / 2
        earlier_avg = sum(weekly_counts[week] for week in weeks[:-2]) / max(1, len(weeks) - 2)
        
        if recent_avg > earlier_avg * 1.2:
            return "increasing"
        elif recent_avg < earlier_avg * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    def _get_suggested_next_steps(self, triggers: List[EscalationTrigger]) -> List[str]:
        """Get suggested next steps based on triggers"""
        
        if not triggers:
            return ["continue_normal_support"]
        
        suggestions = set()
        
        for trigger in triggers:
            if trigger.trigger_type == "billing_dispute":
                suggestions.add("review_billing_history")
                suggestions.add("verify_charges")
            elif trigger.trigger_type == "escalation_request":
                suggestions.add("provide_direct_human_contact")
            elif trigger.trigger_type == "repeated_issue":
                suggestions.add("escalate_to_technical_team")
            elif trigger.trigger_type == "aggressive_language":
                suggestions.add("use_de_escalation_techniques")
                suggestions.add("remain_calm_and_professional")
            else:
                suggestions.add("address_primary_concern")
        
        return list(suggestions) if suggestions else ["provide_comprehensive_assistance"]
    
    def _get_priority_from_triggers(self, triggers: List[EscalationTrigger]) -> str:
        """Get priority based on triggers"""
        
        if not triggers:
            return "normal"
        
        highest_level = max(trigger.escalation_level for trigger in triggers)
        return self._get_priority_from_level(highest_level)