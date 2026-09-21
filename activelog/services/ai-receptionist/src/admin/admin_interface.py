"""
Admin Guidance Interface
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from ..database import (
    AdminGuidance, SystemSettings, Conversation, EscalationTrigger, 
    TrainingData, FAQ, ConversationMessage, LanguageCode
)


class AdminInterface:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive admin dashboard data"""
        
        # Get current date for filtering
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Conversation metrics
        total_conversations = await self._get_conversation_count()
        active_conversations = await self._get_active_conversation_count()
        today_conversations = await self._get_conversation_count(since=today)
        week_conversations = await self._get_conversation_count(since=week_ago)
        
        # Escalation metrics
        total_escalations = await self._get_escalation_count()
        week_escalations = await self._get_escalation_count(since=week_ago)
        escalation_rate = week_escalations / week_conversations if week_conversations > 0 else 0
        
        # Training metrics
        training_samples = await self._get_training_sample_count()
        pending_approvals = await self._get_pending_training_count()
        
        # FAQ metrics
        faq_count = await self._get_faq_count()
        faq_usage = await self._get_faq_usage_stats()
        
        # Performance metrics
        avg_resolution_time = await self._get_average_resolution_time()
        satisfaction_score = await self._get_satisfaction_score()
        
        # Channel distribution
        channel_stats = await self._get_channel_distribution()
        
        # Language distribution
        language_stats = await self._get_language_distribution()
        
        return {
            "overview": {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "today_conversations": today_conversations,
                "week_conversations": week_conversations,
                "escalation_rate": escalation_rate,
                "avg_resolution_time_minutes": avg_resolution_time,
                "satisfaction_score": satisfaction_score
            },
            "escalations": {
                "total": total_escalations,
                "this_week": week_escalations,
                "rate": escalation_rate,
                "top_reasons": await self._get_top_escalation_reasons()
            },
            "training": {
                "total_samples": training_samples,
                "pending_approvals": pending_approvals,
                "accuracy_estimate": await self._get_model_accuracy_estimate()
            },
            "faqs": {
                "total_count": faq_count,
                "usage_stats": faq_usage,
                "top_searches": await self._get_top_faq_searches()
            },
            "channels": channel_stats,
            "languages": language_stats,
            "alerts": await self._get_system_alerts(),
            "recommendations": await self._get_admin_recommendations()
        }
    
    async def get_guidance(
        self,
        category: str = None,
        language: str = "en_us"
    ) -> List[Dict[str, Any]]:
        """Get admin guidance for agents"""
        
        stmt = select(AdminGuidance).where(
            AdminGuidance.is_active == True,
            AdminGuidance.language == language
        )
        
        if category:
            stmt = stmt.where(AdminGuidance.category == category)
        
        stmt = stmt.order_by(AdminGuidance.priority, AdminGuidance.created_at.desc())
        
        result = await self.db.execute(stmt)
        guidance_records = result.scalars().all()
        
        guidance_list = []
        for record in guidance_records:
            guidance_list.append({
                "id": str(record.id),
                "title": record.title,
                "category": record.category,
                "guidance_text": record.guidance_text,
                "examples": record.examples or [],
                "conditions": record.conditions or {},
                "priority": record.priority,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat()
            })
        
        return guidance_list
    
    async def create_guidance(
        self,
        title: str,
        category: str,
        guidance_text: str,
        examples: List[str] = None,
        conditions: Dict[str, Any] = None,
        language: str = "en_us",
        priority: int = 5,
        created_by: str = "admin"
    ) -> Dict[str, Any]:
        """Create new admin guidance"""
        
        guidance = AdminGuidance(
            title=title,
            category=category,
            guidance_text=guidance_text,
            examples=examples or [],
            conditions=conditions or {},
            priority=priority,
            language=language,
            created_by=created_by
        )
        
        self.db.add(guidance)
        await self.db.commit()
        
        return {
            "guidance_id": str(guidance.id),
            "title": title,
            "category": category,
            "status": "created",
            "created_by": created_by
        }
    
    async def update_guidance(
        self,
        guidance_id: str,
        title: str = None,
        guidance_text: str = None,
        examples: List[str] = None,
        conditions: Dict[str, Any] = None,
        priority: int = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """Update existing guidance"""
        
        update_values = {"updated_at": datetime.utcnow()}
        
        if title:
            update_values["title"] = title
        if guidance_text:
            update_values["guidance_text"] = guidance_text
        if examples is not None:
            update_values["examples"] = examples
        if conditions is not None:
            update_values["conditions"] = conditions
        if priority is not None:
            update_values["priority"] = priority
        if is_active is not None:
            update_values["is_active"] = is_active
        
        stmt = update(AdminGuidance).where(
            AdminGuidance.id == uuid.UUID(guidance_id)
        ).values(**update_values)
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        return {"status": "updated", "guidance_id": guidance_id}
    
    async def get_system_settings(self, category: str = None) -> Dict[str, Any]:
        """Get system settings"""
        
        stmt = select(SystemSettings).where(SystemSettings.is_active == True)
        
        if category:
            stmt = stmt.where(SystemSettings.category == category)
        
        result = await self.db.execute(stmt)
        settings = result.scalars().all()
        
        settings_dict = {}
        for setting in settings:
            settings_dict[setting.setting_key] = {
                "value": setting.setting_value,
                "description": setting.description,
                "category": setting.category,
                "updated_at": setting.updated_at.isoformat()
            }
        
        return settings_dict
    
    async def update_system_setting(
        self,
        setting_key: str,
        setting_value: Any,
        description: str = None,
        category: str = "general",
        updated_by: str = "admin"
    ) -> Dict[str, Any]:
        """Update system setting"""
        
        # Check if setting exists
        stmt = select(SystemSettings).where(SystemSettings.setting_key == setting_key)
        result = await self.db.execute(stmt)
        existing_setting = result.scalar_one_or_none()
        
        if existing_setting:
            # Update existing setting
            stmt = update(SystemSettings).where(
                SystemSettings.setting_key == setting_key
            ).values(
                setting_value=setting_value,
                description=description or existing_setting.description,
                updated_at=datetime.utcnow(),
                updated_by=updated_by
            )
            await self.db.execute(stmt)
            status = "updated"
        else:
            # Create new setting
            new_setting = SystemSettings(
                setting_key=setting_key,
                setting_value=setting_value,
                description=description,
                category=category,
                updated_by=updated_by
            )
            self.db.add(new_setting)
            status = "created"
        
        await self.db.commit()
        
        return {
            "status": status,
            "setting_key": setting_key,
            "new_value": setting_value,
            "updated_by": updated_by
        }
    
    async def get_performance_analytics(
        self,
        date_from: datetime = None,
        date_to: datetime = None
    ) -> Dict[str, Any]:
        """Get detailed performance analytics"""
        
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=30)
        if not date_to:
            date_to = datetime.utcnow()
        
        # Conversation performance
        conversation_metrics = await self._get_conversation_metrics(date_from, date_to)
        
        # Resolution analytics
        resolution_metrics = await self._get_resolution_metrics(date_from, date_to)
        
        # Channel performance
        channel_performance = await self._get_channel_performance(date_from, date_to)
        
        # Language performance
        language_performance = await self._get_language_performance(date_from, date_to)
        
        # Agent performance (AI vs Human)
        agent_performance = await self._get_agent_performance(date_from, date_to)
        
        # Trend analysis
        trends = await self._analyze_performance_trends(date_from, date_to)
        
        return {
            "date_range": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "conversation_metrics": conversation_metrics,
            "resolution_metrics": resolution_metrics,
            "channel_performance": channel_performance,
            "language_performance": language_performance,
            "agent_performance": agent_performance,
            "trends": trends,
            "insights": await self._generate_performance_insights(conversation_metrics, resolution_metrics)
        }
    
    async def get_training_management(self) -> Dict[str, Any]:
        """Get training management interface data"""
        
        # Pending approvals
        pending_training = await self._get_pending_training_data()
        
        # Recent feedback
        recent_feedback = await self._get_recent_training_feedback()
        
        # Training statistics
        training_stats = await self._get_training_statistics()
        
        # Model performance tracking
        model_performance = await self._get_model_performance_history()
        
        return {
            "pending_approvals": pending_training,
            "recent_feedback": recent_feedback,
            "statistics": training_stats,
            "model_performance": model_performance,
            "recommendations": await self._get_training_recommendations()
        }
    
    async def manage_escalations(self) -> Dict[str, Any]:
        """Get escalation management interface data"""
        
        # Active escalations
        active_escalations = await self._get_active_escalations()
        
        # Escalation trends
        escalation_trends = await self._get_escalation_trends()
        
        # Escalation rules
        escalation_rules = await self._get_escalation_rule_performance()
        
        return {
            "active_escalations": active_escalations,
            "trends": escalation_trends,
            "rule_performance": escalation_rules,
            "recommendations": await self._get_escalation_recommendations()
        }
    
    # Private helper methods
    async def _get_conversation_count(self, since: datetime = None) -> int:
        """Get conversation count"""
        stmt = select(func.count(Conversation.id))
        if since:
            stmt = stmt.where(Conversation.started_at >= since)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_active_conversation_count(self) -> int:
        """Get active conversation count"""
        stmt = select(func.count(Conversation.id)).where(
            Conversation.status.in_(["active"])
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_escalation_count(self, since: datetime = None) -> int:
        """Get escalation count"""
        stmt = select(func.count(EscalationTrigger.id))
        if since:
            stmt = stmt.where(EscalationTrigger.triggered_at >= since)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_training_sample_count(self) -> int:
        """Get training sample count"""
        stmt = select(func.count(TrainingData.id))
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_pending_training_count(self) -> int:
        """Get pending training approval count"""
        stmt = select(func.count(TrainingData.id)).where(
            TrainingData.is_approved == False
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_faq_count(self) -> int:
        """Get FAQ count"""
        stmt = select(func.count(FAQ.id)).where(FAQ.is_approved == True)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_faq_usage_stats(self) -> Dict[str, Any]:
        """Get FAQ usage statistics"""
        stmt = select(
            func.sum(FAQ.usage_count).label('total_usage'),
            func.avg(FAQ.effectiveness_score).label('avg_effectiveness')
        ).where(FAQ.is_approved == True)
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        return {
            "total_usage": row.total_usage or 0,
            "average_effectiveness": row.avg_effectiveness or 0
        }
    
    async def _get_average_resolution_time(self) -> float:
        """Get average resolution time in minutes"""
        stmt = select(func.avg(Conversation.duration_seconds)).where(
            Conversation.status == "completed",
            Conversation.duration_seconds.isnot(None)
        )
        
        result = await self.db.execute(stmt)
        avg_seconds = result.scalar()
        
        return (avg_seconds / 60) if avg_seconds else 0
    
    async def _get_satisfaction_score(self) -> float:
        """Get average satisfaction score"""
        # This would analyze feedback from conversations
        # For now, return a mock value
        return 4.2
    
    async def _get_channel_distribution(self) -> Dict[str, int]:
        """Get distribution by channel"""
        stmt = select(
            Conversation.conversation_type,
            func.count(Conversation.id).label('count')
        ).group_by(Conversation.conversation_type)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        return {row.conversation_type.value: row.count for row in rows}
    
    async def _get_language_distribution(self) -> Dict[str, int]:
        """Get distribution by language"""
        stmt = select(
            Conversation.language,
            func.count(Conversation.id).label('count')
        ).group_by(Conversation.language)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        return {row.language.value: row.count for row in rows}
    
    async def _get_top_escalation_reasons(self) -> List[Dict[str, Any]]:
        """Get top escalation reasons"""
        stmt = select(
            EscalationTrigger.trigger_type,
            func.count(EscalationTrigger.id).label('count')
        ).group_by(EscalationTrigger.trigger_type).order_by(func.count(EscalationTrigger.id).desc()).limit(5)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        return [{"reason": row.trigger_type, "count": row.count} for row in rows]
    
    async def _get_model_accuracy_estimate(self) -> float:
        """Get model accuracy estimate"""
        # Calculate based on positive feedback ratio
        stmt = select(
            func.count(TrainingData.id).filter(TrainingData.user_feedback == 'positive').label('positive'),
            func.count(TrainingData.id).label('total')
        ).where(TrainingData.user_feedback.isnot(None))
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        if row.total > 0:
            return row.positive / row.total
        return 0.5
    
    async def _get_top_faq_searches(self) -> List[Dict[str, Any]]:
        """Get top FAQ searches"""
        stmt = select(FAQ.question, FAQ.usage_count).where(
            FAQ.is_approved == True
        ).order_by(FAQ.usage_count.desc()).limit(10)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        return [{"question": row.question, "usage_count": row.usage_count} for row in rows]
    
    async def _get_system_alerts(self) -> List[Dict[str, Any]]:
        """Get system alerts"""
        alerts = []
        
        # Check for high escalation rate
        recent_escalations = await self._get_escalation_count(
            since=datetime.utcnow() - timedelta(hours=24)
        )
        recent_conversations = await self._get_conversation_count(
            since=datetime.utcnow() - timedelta(hours=24)
        )
        
        if recent_conversations > 0:
            escalation_rate = recent_escalations / recent_conversations
            if escalation_rate > 0.1:  # More than 10%
                alerts.append({
                    "type": "high_escalation_rate",
                    "severity": "warning",
                    "message": f"High escalation rate: {escalation_rate:.1%} in the last 24 hours",
                    "action": "Review escalation triggers and agent guidance"
                })
        
        # Check for pending training approvals
        pending_count = await self._get_pending_training_count()
        if pending_count > 50:
            alerts.append({
                "type": "pending_training_approvals",
                "severity": "info",
                "message": f"{pending_count} training samples pending approval",
                "action": "Review and approve training data"
            })
        
        return alerts
    
    async def _get_admin_recommendations(self) -> List[str]:
        """Get admin recommendations"""
        recommendations = []
        
        # Analyze recent performance and suggest improvements
        avg_resolution_time = await self._get_average_resolution_time()
        if avg_resolution_time > 15:
            recommendations.append("Consider reviewing FAQ content to improve resolution times")
        
        escalation_rate = await self._get_escalation_count(
            since=datetime.utcnow() - timedelta(days=7)
        ) / max(1, await self._get_conversation_count(
            since=datetime.utcnow() - timedelta(days=7)
        ))
        
        if escalation_rate > 0.08:
            recommendations.append("High escalation rate - review agent guidance and training")
        
        model_accuracy = await self._get_model_accuracy_estimate()
        if model_accuracy < 0.8:
            recommendations.append("Model accuracy below threshold - review training data")
        
        return recommendations or ["System performing well - continue monitoring"]
    
    async def _get_conversation_metrics(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Get conversation metrics for date range"""
        stmt = select(
            func.count(Conversation.id).label('total'),
            func.avg(Conversation.duration_seconds / 60).label('avg_duration_min'),
            func.count(Conversation.id).filter(Conversation.status == 'completed').label('completed'),
            func.count(Conversation.id).filter(Conversation.status == 'escalated').label('escalated')
        ).where(and_(
            Conversation.started_at >= date_from,
            Conversation.started_at <= date_to
        ))
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        return {
            "total_conversations": row.total or 0,
            "average_duration_minutes": row.avg_duration_min or 0,
            "completed_conversations": row.completed or 0,
            "escalated_conversations": row.escalated or 0,
            "completion_rate": (row.completed / row.total) if row.total > 0 else 0,
            "escalation_rate": (row.escalated / row.total) if row.total > 0 else 0
        }
    
    async def _get_resolution_metrics(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Get resolution metrics"""
        # Mock implementation for resolution metrics
        return {
            "first_contact_resolution_rate": 0.72,
            "average_resolution_steps": 3.4,
            "self_service_success_rate": 0.68,
            "human_handoff_success_rate": 0.94
        }
    
    async def _get_channel_performance(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Get channel performance metrics"""
        stmt = select(
            Conversation.conversation_type,
            func.count(Conversation.id).label('total'),
            func.avg(Conversation.duration_seconds / 60).label('avg_duration'),
            func.count(Conversation.id).filter(Conversation.status == 'escalated').label('escalated')
        ).where(and_(
            Conversation.started_at >= date_from,
            Conversation.started_at <= date_to
        )).group_by(Conversation.conversation_type)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        performance = {}
        for row in rows:
            performance[row.conversation_type.value] = {
                "total": row.total,
                "avg_duration_minutes": row.avg_duration or 0,
                "escalation_rate": (row.escalated / row.total) if row.total > 0 else 0
            }
        
        return performance
    
    async def _get_language_performance(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Get language performance metrics"""
        stmt = select(
            Conversation.language,
            func.count(Conversation.id).label('total'),
            func.count(Conversation.id).filter(Conversation.status == 'completed').label('completed')
        ).where(and_(
            Conversation.started_at >= date_from,
            Conversation.started_at <= date_to
        )).group_by(Conversation.language)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        performance = {}
        for row in rows:
            performance[row.language.value] = {
                "total": row.total,
                "success_rate": (row.completed / row.total) if row.total > 0 else 0
            }
        
        return performance
    
    async def _get_agent_performance(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Get AI vs Human agent performance"""
        # Mock implementation
        return {
            "ai_agent": {
                "conversations_handled": 1247,
                "average_resolution_time": 8.3,
                "success_rate": 0.76,
                "escalation_rate": 0.12
            },
            "human_agents": {
                "conversations_handled": 189,
                "average_resolution_time": 12.7,
                "success_rate": 0.94,
                "escalation_rate": 0.02
            }
        }
    
    async def _analyze_performance_trends(self, date_from: datetime, date_to: datetime) -> Dict[str, str]:
        """Analyze performance trends"""
        # Mock trend analysis
        return {
            "conversation_volume": "increasing",
            "resolution_time": "stable",
            "escalation_rate": "decreasing",
            "satisfaction_score": "improving"
        }
    
    async def _generate_performance_insights(
        self,
        conversation_metrics: Dict[str, Any],
        resolution_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate performance insights"""
        insights = []
        
        if conversation_metrics["escalation_rate"] > 0.1:
            insights.append("Escalation rate is above optimal threshold (>10%)")
        
        if resolution_metrics["first_contact_resolution_rate"] < 0.7:
            insights.append("First contact resolution rate could be improved")
        
        if conversation_metrics["completion_rate"] > 0.9:
            insights.append("Excellent conversation completion rate")
        
        return insights or ["Performance metrics are within expected ranges"]
    
    async def _get_pending_training_data(self) -> List[Dict[str, Any]]:
        """Get pending training data for approval"""
        stmt = select(TrainingData).where(
            TrainingData.is_approved == False
        ).order_by(TrainingData.created_at.desc()).limit(20)
        
        result = await self.db.execute(stmt)
        training_data = result.scalars().all()
        
        pending = []
        for data in training_data:
            pending.append({
                "id": str(data.id),
                "user_input": data.user_input,
                "assistant_response": data.assistant_response,
                "feedback_type": data.user_feedback,
                "feedback_score": data.feedback_score,
                "created_at": data.created_at.isoformat(),
                "suggestions": data.improvement_suggestions
            })
        
        return pending
    
    async def _get_recent_training_feedback(self) -> List[Dict[str, Any]]:
        """Get recent training feedback"""
        stmt = select(TrainingData).where(
            TrainingData.user_feedback.isnot(None)
        ).order_by(TrainingData.created_at.desc()).limit(10)
        
        result = await self.db.execute(stmt)
        feedback_data = result.scalars().all()
        
        feedback = []
        for data in feedback_data:
            feedback.append({
                "feedback_type": data.user_feedback,
                "feedback_score": data.feedback_score,
                "interaction_type": data.interaction_type,
                "created_at": data.created_at.isoformat()
            })
        
        return feedback
    
    async def _get_training_statistics(self) -> Dict[str, Any]:
        """Get training statistics"""
        total_stmt = select(func.count(TrainingData.id))
        approved_stmt = select(func.count(TrainingData.id)).where(TrainingData.is_approved == True)
        positive_stmt = select(func.count(TrainingData.id)).where(TrainingData.user_feedback == 'positive')
        
        total_result = await self.db.execute(total_stmt)
        approved_result = await self.db.execute(approved_stmt)
        positive_result = await self.db.execute(positive_stmt)
        
        total = total_result.scalar() or 0
        approved = approved_result.scalar() or 0
        positive = positive_result.scalar() or 0
        
        return {
            "total_samples": total,
            "approved_samples": approved,
            "positive_feedback": positive,
            "approval_rate": (approved / total) if total > 0 else 0,
            "positive_rate": (positive / total) if total > 0 else 0
        }
    
    async def _get_model_performance_history(self) -> List[Dict[str, Any]]:
        """Get model performance history"""
        # Mock performance history
        return [
            {"date": "2024-01-01", "accuracy": 0.78, "precision": 0.82, "recall": 0.75},
            {"date": "2024-01-02", "accuracy": 0.81, "precision": 0.83, "recall": 0.79},
            {"date": "2024-01-03", "accuracy": 0.79, "precision": 0.81, "recall": 0.77}
        ]
    
    async def _get_training_recommendations(self) -> List[str]:
        """Get training recommendations"""
        return [
            "Focus on improving negative feedback interactions",
            "Collect more training data for billing inquiries",
            "Review and approve pending training samples"
        ]
    
    async def _get_active_escalations(self) -> List[Dict[str, Any]]:
        """Get active escalations"""
        stmt = select(EscalationTrigger).where(
            EscalationTrigger.was_resolved.is_(None)
        ).order_by(EscalationTrigger.triggered_at.desc()).limit(20)
        
        result = await self.db.execute(stmt)
        escalations = result.scalars().all()
        
        active = []
        for escalation in escalations:
            active.append({
                "id": str(escalation.id),
                "trigger_type": escalation.trigger_type,
                "escalation_level": escalation.escalation_level.value,
                "reason": escalation.escalation_reason,
                "escalated_to": escalation.escalated_to,
                "triggered_at": escalation.triggered_at.isoformat(),
                "conversation_id": str(escalation.conversation_id)
            })
        
        return active
    
    async def _get_escalation_trends(self) -> Dict[str, Any]:
        """Get escalation trends"""
        # Mock escalation trends
        return {
            "weekly_trend": "stable",
            "top_triggers": ["sentiment_frustrated", "conversation_length"],
            "resolution_time_trend": "improving"
        }
    
    async def _get_escalation_rule_performance(self) -> List[Dict[str, Any]]:
        """Get escalation rule performance"""
        stmt = select(
            EscalationTrigger.trigger_type,
            func.count(EscalationTrigger.id).label('triggered_count'),
            func.count(EscalationTrigger.id).filter(EscalationTrigger.was_resolved == True).label('resolved_count')
        ).group_by(EscalationTrigger.trigger_type)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        performance = []
        for row in rows:
            success_rate = (row.resolved_count / row.triggered_count) if row.triggered_count > 0 else 0
            performance.append({
                "rule_type": row.trigger_type,
                "triggered_count": row.triggered_count,
                "success_rate": success_rate
            })
        
        return performance
    
    async def _get_escalation_recommendations(self) -> List[str]:
        """Get escalation recommendations"""
        return [
            "Review sentiment-based escalation thresholds",
            "Provide additional training for frustration handling",
            "Monitor conversation length patterns"
        ]