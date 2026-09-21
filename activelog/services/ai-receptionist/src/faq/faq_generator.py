"""
FAQ Auto-Generation System
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from ..database import FAQ, Conversation, ConversationMessage, LanguageCode


class FAQGenerator:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # Minimum frequency for auto-generating FAQ
        self.min_question_frequency = 3
        
        # Keywords for identifying questions
        self.question_indicators = [
            "what", "how", "when", "where", "why", "who", "which",
            "can", "could", "would", "should", "is", "are", "do", "does",
            "will", "may", "might", "?", "help", "explain", "tell me"
        ]
        
        # Categories for auto-classification
        self.category_keywords = {
            "billing": ["bill", "payment", "charge", "invoice", "refund", "subscription", "cost", "price"],
            "technical": ["error", "bug", "not working", "broken", "install", "setup", "configure"],
            "account": ["account", "profile", "login", "password", "settings", "personal"],
            "support": ["help", "support", "assistance", "problem", "issue", "trouble"],
            "general": ["hours", "location", "contact", "phone", "email", "address"],
            "features": ["feature", "function", "capability", "option", "setting"]
        }
    
    async def search_faqs(
        self,
        query: str,
        language: str = "en_us",
        category: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search FAQ database for relevant answers"""
        
        query_lower = query.lower()
        
        # Build query
        stmt = select(FAQ).where(
            FAQ.language == language,
            FAQ.is_approved == True
        )
        
        if category:
            stmt = stmt.where(FAQ.category == category)
        
        result = await self.db.execute(stmt)
        faqs = result.scalars().all()
        
        # Score FAQs based on relevance
        scored_faqs = []
        for faq in faqs:
            score = await self._calculate_faq_relevance(query_lower, faq)
            
            if score > 0:
                scored_faqs.append({
                    "faq_id": str(faq.id),
                    "question": faq.question,
                    "answer": faq.answer,
                    "category": faq.category,
                    "relevance_score": score,
                    "usage_count": faq.usage_count,
                    "effectiveness_score": faq.effectiveness_score,
                    "keywords": faq.keywords or []
                })
        
        # Sort by relevance and return top results
        scored_faqs.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_faqs = scored_faqs[:limit]
        
        # Update usage counts for returned FAQs
        for faq_result in top_faqs:
            await self._increment_faq_usage(faq_result["faq_id"])
        
        return top_faqs
    
    async def submit_faq(
        self,
        question: str,
        answer: str,
        category: str,
        language: str = "en_us",
        keywords: List[str] = None,
        is_auto_generated: bool = False
    ) -> Dict[str, Any]:
        """Submit new FAQ entry"""
        
        # Extract keywords if not provided
        if not keywords:
            keywords = await self._extract_keywords(question + " " + answer)
        
        # Check for duplicates
        existing_faq = await self._find_similar_faq(question, language, category)
        if existing_faq:
            return {
                "success": False,
                "error": "Similar FAQ already exists",
                "existing_faq_id": str(existing_faq.id),
                "existing_question": existing_faq.question
            }
        
        # Create new FAQ
        new_faq = FAQ(
            question=question,
            answer=answer,
            category=category,
            keywords=keywords,
            language=language,
            is_auto_generated=is_auto_generated,
            is_approved=not is_auto_generated,  # Auto-generated FAQs need manual approval
            usage_count=0,
            effectiveness_score=0.0
        )
        
        self.db.add(new_faq)
        await self.db.commit()
        
        return {
            "success": True,
            "faq_id": str(new_faq.id),
            "question": question,
            "category": category,
            "needs_approval": is_auto_generated,
            "keywords": keywords
        }
    
    async def auto_generate_faqs(
        self,
        conversation_threshold: int = 3,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Auto-generate FAQs from frequent conversation patterns"""
        
        # Get recent conversations
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        stmt = select(ConversationMessage).where(
            and_(
                ConversationMessage.timestamp >= cutoff_date,
                ConversationMessage.message_type == "user"
            )
        )
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Identify questions
        questions = []
        for message in messages:
            if await self._is_question(message.content):
                normalized_question = await self._normalize_question(message.content)
                questions.append({
                    "original": message.content,
                    "normalized": normalized_question,
                    "conversation_id": message.conversation_id,
                    "timestamp": message.timestamp
                })
        
        # Count question frequency
        question_counts = Counter(q["normalized"] for q in questions)
        frequent_questions = [
            (question, count) for question, count in question_counts.items()
            if count >= conversation_threshold
        ]
        
        # Generate FAQs for frequent questions
        generated_faqs = []
        for question, frequency in frequent_questions:
            # Find representative conversations
            sample_conversations = await self._get_sample_conversations_for_question(question)
            
            # Generate answer
            generated_answer = await self._generate_answer_from_conversations(
                question, sample_conversations
            )
            
            # Determine category
            category = await self._categorize_question(question)
            
            # Submit FAQ
            result = await self.submit_faq(
                question=question,
                answer=generated_answer,
                category=category,
                is_auto_generated=True
            )
            
            if result["success"]:
                generated_faqs.append({
                    "faq_id": result["faq_id"],
                    "question": question,
                    "frequency": frequency,
                    "category": category,
                    "sample_conversations": len(sample_conversations)
                })
        
        return {
            "total_questions_analyzed": len(questions),
            "frequent_questions_found": len(frequent_questions),
            "faqs_generated": len(generated_faqs),
            "generated_faqs": generated_faqs,
            "approval_required": True,
            "threshold_used": conversation_threshold
        }
    
    async def approve_faq(self, faq_id: str, approved_by: str = "admin") -> Dict[str, Any]:
        """Approve auto-generated FAQ"""
        
        stmt = update(FAQ).where(
            FAQ.id == uuid.UUID(faq_id)
        ).values(
            is_approved=True,
            updated_at=datetime.utcnow()
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        if result.rowcount == 0:
            return {"success": False, "error": "FAQ not found"}
        
        return {
            "success": True,
            "faq_id": faq_id,
            "approved_by": approved_by,
            "approved_at": datetime.utcnow().isoformat()
        }
    
    async def get_faq_analytics(self) -> Dict[str, Any]:
        """Get FAQ system analytics"""
        
        # Total FAQ counts
        total_stmt = select(func.count(FAQ.id))
        approved_stmt = select(func.count(FAQ.id)).where(FAQ.is_approved == True)
        auto_generated_stmt = select(func.count(FAQ.id)).where(FAQ.is_auto_generated == True)
        
        total_result = await self.db.execute(total_stmt)
        approved_result = await self.db.execute(approved_stmt)
        auto_generated_result = await self.db.execute(auto_generated_stmt)
        
        total_faqs = total_result.scalar() or 0
        approved_faqs = approved_result.scalar() or 0
        auto_generated_faqs = auto_generated_result.scalar() or 0
        
        # Usage statistics
        usage_stmt = select(
            func.sum(FAQ.usage_count).label('total_usage'),
            func.avg(FAQ.usage_count).label('avg_usage'),
            func.avg(FAQ.effectiveness_score).label('avg_effectiveness')
        ).where(FAQ.is_approved == True)
        
        usage_result = await self.db.execute(usage_stmt)
        usage_row = usage_result.fetchone()
        
        # Category distribution
        category_stmt = select(
            FAQ.category,
            func.count(FAQ.id).label('count')
        ).where(FAQ.is_approved == True).group_by(FAQ.category)
        
        category_result = await self.db.execute(category_stmt)
        category_rows = category_result.fetchall()
        
        category_distribution = {row.category: row.count for row in category_rows}
        
        # Top performing FAQs
        top_faqs_stmt = select(FAQ).where(
            FAQ.is_approved == True
        ).order_by(FAQ.usage_count.desc()).limit(10)
        
        top_faqs_result = await self.db.execute(top_faqs_stmt)
        top_faqs = top_faqs_result.scalars().all()
        
        top_faq_list = [
            {
                "question": faq.question,
                "category": faq.category,
                "usage_count": faq.usage_count,
                "effectiveness_score": faq.effectiveness_score
            }
            for faq in top_faqs
        ]
        
        return {
            "summary": {
                "total_faqs": total_faqs,
                "approved_faqs": approved_faqs,
                "auto_generated_faqs": auto_generated_faqs,
                "pending_approval": total_faqs - approved_faqs,
                "approval_rate": (approved_faqs / total_faqs) if total_faqs > 0 else 0
            },
            "usage_stats": {
                "total_usage": usage_row.total_usage or 0,
                "average_usage_per_faq": usage_row.avg_usage or 0,
                "average_effectiveness": usage_row.avg_effectiveness or 0
            },
            "category_distribution": category_distribution,
            "top_performing_faqs": top_faq_list,
            "recommendations": await self._get_faq_recommendations()
        }
    
    async def update_faq_effectiveness(
        self,
        faq_id: str,
        was_helpful: bool,
        user_feedback: str = None
    ) -> Dict[str, Any]:
        """Update FAQ effectiveness based on user feedback"""
        
        # Get current FAQ
        stmt = select(FAQ).where(FAQ.id == uuid.UUID(faq_id))
        result = await self.db.execute(stmt)
        faq = result.scalar_one_or_none()
        
        if not faq:
            return {"success": False, "error": "FAQ not found"}
        
        # Update effectiveness score
        # Simple algorithm: helpful = +0.1, not helpful = -0.1
        adjustment = 0.1 if was_helpful else -0.1
        new_effectiveness = max(0.0, min(1.0, faq.effectiveness_score + adjustment))
        
        stmt = update(FAQ).where(
            FAQ.id == uuid.UUID(faq_id)
        ).values(
            effectiveness_score=new_effectiveness,
            updated_at=datetime.utcnow()
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        return {
            "success": True,
            "faq_id": faq_id,
            "was_helpful": was_helpful,
            "new_effectiveness_score": new_effectiveness,
            "user_feedback": user_feedback
        }
    
    # Private helper methods
    async def _calculate_faq_relevance(self, query: str, faq: FAQ) -> float:
        """Calculate relevance score between query and FAQ"""
        
        score = 0.0
        query_words = set(query.lower().split())
        
        # Check question relevance
        question_words = set(faq.question.lower().split())
        question_overlap = len(query_words & question_words)
        if question_overlap > 0:
            score += (question_overlap / len(query_words)) * 3  # Weight question matches highly
        
        # Check answer relevance
        answer_words = set(faq.answer.lower().split())
        answer_overlap = len(query_words & answer_words)
        if answer_overlap > 0:
            score += (answer_overlap / len(query_words)) * 1
        
        # Check keyword relevance
        if faq.keywords:
            keyword_matches = sum(1 for keyword in faq.keywords if keyword.lower() in query)
            score += keyword_matches * 2
        
        # Boost based on effectiveness and usage
        score *= (1 + faq.effectiveness_score * 0.2)
        score *= (1 + min(faq.usage_count / 100, 0.5))  # Cap usage boost at 50%
        
        return score
    
    async def _increment_faq_usage(self, faq_id: str):
        """Increment FAQ usage count"""
        
        stmt = update(FAQ).where(
            FAQ.id == uuid.UUID(faq_id)
        ).values(
            usage_count=FAQ.usage_count + 1
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        
        # Simple keyword extraction (in production, use NLP libraries)
        words = text.lower().split()
        
        # Filter out common words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "is", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can"
        }
        
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Return top keywords by frequency
        word_counts = Counter(keywords)
        return [word for word, count in word_counts.most_common(10)]
    
    async def _find_similar_faq(
        self,
        question: str,
        language: str,
        category: str
    ) -> Optional[FAQ]:
        """Find similar existing FAQ"""
        
        stmt = select(FAQ).where(
            FAQ.language == language,
            FAQ.category == category,
            FAQ.is_approved == True
        )
        
        result = await self.db.execute(stmt)
        faqs = result.scalars().all()
        
        question_words = set(question.lower().split())
        
        for faq in faqs:
            faq_words = set(faq.question.lower().split())
            similarity = len(question_words & faq_words) / len(question_words | faq_words)
            
            if similarity > 0.7:  # 70% similarity threshold
                return faq
        
        return None
    
    async def _is_question(self, text: str) -> bool:
        """Check if text is a question"""
        
        text_lower = text.lower()
        
        # Check for question mark
        if "?" in text:
            return True
        
        # Check for question indicators
        for indicator in self.question_indicators:
            if text_lower.startswith(indicator + " "):
                return True
        
        return False
    
    async def _normalize_question(self, question: str) -> str:
        """Normalize question for deduplication"""
        
        # Remove punctuation and convert to lowercase
        normalized = question.lower().strip()
        normalized = normalized.replace("?", "").replace("!", "").replace(".", "")
        
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        
        return normalized
    
    async def _get_sample_conversations_for_question(
        self,
        question: str
    ) -> List[Dict[str, Any]]:
        """Get sample conversations that contain this question"""
        
        # Find messages similar to the question
        stmt = select(ConversationMessage).where(
            ConversationMessage.message_type == "user"
        ).limit(100)  # Limit for performance
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        similar_conversations = []
        question_words = set(question.lower().split())
        
        for message in messages:
            message_words = set(message.content.lower().split())
            similarity = len(question_words & message_words) / len(question_words | message_words)
            
            if similarity > 0.5:  # 50% similarity threshold
                similar_conversations.append({
                    "conversation_id": str(message.conversation_id),
                    "user_message": message.content,
                    "timestamp": message.timestamp,
                    "similarity": similarity
                })
        
        # Sort by similarity and return top matches
        similar_conversations.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_conversations[:5]
    
    async def _generate_answer_from_conversations(
        self,
        question: str,
        sample_conversations: List[Dict[str, Any]]
    ) -> str:
        """Generate answer based on sample conversations"""
        
        # Mock answer generation (in production, use ML/AI)
        if not sample_conversations:
            return "This is a frequently asked question. Please contact our support team for assistance."
        
        # Create a generic helpful answer
        category = await self._categorize_question(question)
        
        answer_templates = {
            "billing": "For billing-related questions, please check your account dashboard or contact our billing team at billing@company.com.",
            "technical": "For technical issues, please try clearing your cache and cookies first. If the problem persists, contact our technical support team.",
            "account": "For account-related questions, please log into your account dashboard where you can manage your profile and settings.",
            "support": "Our support team is available to help you. Please contact us through the chat widget or email support@company.com.",
            "general": "Thank you for your question. Please contact our customer service team for more information.",
            "features": "For questions about features and functionality, please refer to our documentation or contact our support team."
        }
        
        return answer_templates.get(category, answer_templates["general"])
    
    async def _categorize_question(self, question: str) -> str:
        """Automatically categorize a question"""
        
        question_lower = question.lower()
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return "general"
    
    async def _get_faq_recommendations(self) -> List[str]:
        """Get recommendations for improving FAQ system"""
        
        recommendations = []
        
        # Check for categories with low coverage
        category_stmt = select(
            FAQ.category,
            func.count(FAQ.id).label('count')
        ).where(FAQ.is_approved == True).group_by(FAQ.category)
        
        result = await self.db.execute(category_stmt)
        categories = {row.category: row.count for row in result.fetchall()}
        
        for expected_category in self.category_keywords.keys():
            if categories.get(expected_category, 0) < 5:
                recommendations.append(f"Add more FAQs for {expected_category} category")
        
        # Check for low-effectiveness FAQs
        low_effectiveness_stmt = select(func.count(FAQ.id)).where(
            and_(
                FAQ.is_approved == True,
                FAQ.effectiveness_score < 0.3
            )
        )
        
        result = await self.db.execute(low_effectiveness_stmt)
        low_effectiveness_count = result.scalar() or 0
        
        if low_effectiveness_count > 0:
            recommendations.append(f"Review and improve {low_effectiveness_count} low-effectiveness FAQs")
        
        # Check for unused FAQs
        unused_stmt = select(func.count(FAQ.id)).where(
            and_(
                FAQ.is_approved == True,
                FAQ.usage_count == 0
            )
        )
        
        result = await self.db.execute(unused_stmt)
        unused_count = result.scalar() or 0
        
        if unused_count > 0:
            recommendations.append(f"Promote or update {unused_count} unused FAQs")
        
        return recommendations or ["FAQ system is performing well"]