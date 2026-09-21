#!/usr/bin/env python3

"""
Feedback Aggregation System for ActiveLog Beta
Collects, analyzes, and manages user feedback with AI-powered insights
"""

import os
import json
import argparse
import logging
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@dataclass
class FeedbackItem:
    id: str
    user_id: str
    category: str
    subject: str
    message: str
    rating: int
    priority: str
    status: str
    created_at: str
    updated_at: str
    metadata: Dict = None
    sentiment: str = None
    tags: List[str] = None

@dataclass
class FeedbackSummary:
    total_feedback: int
    average_rating: float
    category_breakdown: Dict[str, int]
    sentiment_analysis: Dict[str, int]
    priority_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    top_issues: List[Dict]
    trending_topics: List[str]

class FeedbackAggregator:
    def __init__(self, environment: str = "beta", config_path: str = None):
        self.environment = environment
        self.data_dir = Path(f"/app/data/feedback/{environment}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / "feedback-aggregator.log"),
                logging.StreamHandler()
            ]
        )
        
        self.config = self._load_config(config_path)
        self._init_database()

    def _load_config(self, config_path: str = None) -> Dict:
        """Load feedback system configuration"""
        default_config = {
            "auto_categorization": True,
            "sentiment_analysis": True,
            "priority_assignment": True,
            "email_notifications": True,
            "slack_integration": False,
            "feedback_request_frequency": 7,  # days
            "min_rating_for_followup": 3,
            "categories": [
                "bug_report", "feature_request", "usability", "performance", 
                "documentation", "general", "compliment", "complaint"
            ],
            "priority_levels": ["low", "medium", "high", "critical"],
            "notification_emails": ["product@activelog.dev", "support@activelog.dev"]
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
            default_config.update(user_config)
        
        return default_config

    def _get_db_connection(self):
        """Get database connection"""
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", f"activelog_{self.environment}"),
            "user": os.getenv("DB_USER", "activelog_user"),
            "password": os.getenv("DB_PASSWORD", ""),
        }
        
        return psycopg2.connect(**db_config)

    def _init_database(self):
        """Initialize feedback system tables"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Extend existing feedback table
            cursor.execute('''
                ALTER TABLE feedback 
                ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'medium',
                ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50),
                ADD COLUMN IF NOT EXISTS tags TEXT[],
                ADD COLUMN IF NOT EXISTS assignee_id UUID REFERENCES users(id),
                ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS resolution_notes TEXT
            ''')
            
            # Feedback analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback_analytics (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    period_start TIMESTAMP NOT NULL,
                    period_end TIMESTAMP NOT NULL,
                    total_feedback INTEGER DEFAULT 0,
                    average_rating DECIMAL(3,2),
                    category_stats JSONB,
                    sentiment_stats JSONB,
                    priority_stats JSONB,
                    top_issues JSONB,
                    trends JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Feedback requests tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback_requests (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) NOT NULL,
                    request_type VARCHAR(100) NOT NULL,
                    feature_context VARCHAR(255),
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responded_at TIMESTAMP,
                    response_feedback_id UUID REFERENCES feedback(id)
                )
            ''')
            
            # Feedback templates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback_templates (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name VARCHAR(255) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    category VARCHAR(100),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to initialize feedback tables: {e}")
        finally:
            cursor.close()
            conn.close()

    def submit_feedback(self, user_id: str, category: str, subject: str, 
                       message: str, rating: int = None, metadata: Dict = None) -> str:
        """Submit new feedback"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Auto-assign priority based on content and rating
            priority = self._analyze_priority(message, rating, category)
            
            # Perform sentiment analysis if enabled
            sentiment = None
            if self.config["sentiment_analysis"]:
                sentiment = self._analyze_sentiment(message)
            
            # Auto-generate tags
            tags = self._extract_tags(message, category) if self.config["auto_categorization"] else []
            
            cursor.execute('''
                INSERT INTO feedback 
                (user_id, category, subject, message, rating, priority, 
                 sentiment, tags, metadata, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'open')
                RETURNING id
            ''', (
                user_id, category, subject, message, rating, priority,
                sentiment, tags, json.dumps(metadata) if metadata else None
            ))
            
            feedback_id = cursor.fetchone()[0]
            conn.commit()
            
            self.logger.info(f"New feedback submitted: {feedback_id} by {user_id}")
            
            # Send notifications if critical
            if priority == "critical":
                self._send_critical_feedback_alert(feedback_id, user_id, subject, message)
            
            # Auto-assign if applicable
            if priority in ["high", "critical"]:
                self._auto_assign_feedback(feedback_id, category, priority)
            
            return str(feedback_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to submit feedback: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _analyze_priority(self, message: str, rating: int, category: str) -> str:
        """Analyze feedback priority based on content and context"""
        if not self.config["priority_assignment"]:
            return "medium"
        
        priority_score = 0
        
        # Rating-based scoring
        if rating is not None:
            if rating <= 2:
                priority_score += 3
            elif rating == 3:
                priority_score += 1
        
        # Category-based scoring
        if category in ["bug_report", "performance"]:
            priority_score += 2
        elif category == "feature_request":
            priority_score += 1
        
        # Keyword-based scoring
        high_priority_keywords = [
            "critical", "urgent", "broken", "crash", "error", "bug", "issue",
            "not working", "failed", "cannot", "unable", "slow", "performance"
        ]
        
        critical_keywords = [
            "security", "data loss", "corruption", "vulnerability", "breach",
            "down", "outage", "completely broken"
        ]
        
        message_lower = message.lower()
        
        for keyword in critical_keywords:
            if keyword in message_lower:
                return "critical"
        
        for keyword in high_priority_keywords:
            if keyword in message_lower:
                priority_score += 2
        
        # Determine final priority
        if priority_score >= 5:
            return "critical"
        elif priority_score >= 3:
            return "high"
        elif priority_score >= 1:
            return "medium"
        else:
            return "low"

    def _analyze_sentiment(self, message: str) -> str:
        """Simple sentiment analysis (in production, use proper NLP library)"""
        positive_words = [
            "good", "great", "excellent", "amazing", "love", "like", "awesome",
            "fantastic", "wonderful", "perfect", "helpful", "easy", "simple"
        ]
        
        negative_words = [
            "bad", "terrible", "awful", "hate", "dislike", "broken", "useless",
            "frustrating", "annoying", "difficult", "hard", "confusing", "slow"
        ]
        
        neutral_words = [
            "suggest", "recommend", "would", "could", "should", "maybe", "perhaps"
        ]
        
        message_lower = message.lower()
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        neutral_count = sum(1 for word in neutral_words if word in message_lower)
        
        if positive_count > negative_count and positive_count > neutral_count:
            return "positive"
        elif negative_count > positive_count and negative_count > neutral_count:
            return "negative"
        else:
            return "neutral"

    def _extract_tags(self, message: str, category: str) -> List[str]:
        """Extract relevant tags from feedback content"""
        tags = []
        
        # Add category as tag
        tags.append(category)
        
        # Feature-based tags
        feature_keywords = {
            "dashboard": ["dashboard", "main page", "overview"],
            "search": ["search", "find", "lookup"],
            "upload": ["upload", "file", "attachment"],
            "export": ["export", "download", "save"],
            "mobile": ["mobile", "phone", "tablet", "responsive"],
            "api": ["api", "integration", "webhook"],
            "performance": ["slow", "fast", "speed", "performance"],
            "ui": ["interface", "design", "layout", "ui", "ux"],
            "auth": ["login", "password", "authentication", "signup"]
        }
        
        message_lower = message.lower()
        
        for tag, keywords in feature_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                tags.append(tag)
        
        return list(set(tags))  # Remove duplicates

    def get_feedback_summary(self, start_date: datetime = None, 
                           end_date: datetime = None) -> FeedbackSummary:
        """Get comprehensive feedback summary"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            # Get feedback within date range
            cursor.execute('''
                SELECT * FROM feedback 
                WHERE created_at BETWEEN %s AND %s
                ORDER BY created_at DESC
            ''', (start_date, end_date))
            
            feedback_items = cursor.fetchall()
            
            if not feedback_items:
                return FeedbackSummary(
                    total_feedback=0, average_rating=0.0,
                    category_breakdown={}, sentiment_analysis={},
                    priority_distribution={}, status_distribution={},
                    top_issues=[], trending_topics=[]
                )
            
            # Calculate statistics
            total_feedback = len(feedback_items)
            ratings = [item["rating"] for item in feedback_items if item["rating"]]
            average_rating = statistics.mean(ratings) if ratings else 0.0
            
            # Category breakdown
            category_breakdown = Counter(item["category"] for item in feedback_items)
            
            # Sentiment analysis
            sentiment_analysis = Counter(
                item["sentiment"] for item in feedback_items 
                if item["sentiment"]
            )
            
            # Priority distribution
            priority_distribution = Counter(
                item["priority"] for item in feedback_items 
                if item["priority"]
            )
            
            # Status distribution
            status_distribution = Counter(item["status"] for item in feedback_items)
            
            # Top issues (most common subjects/messages)
            issue_counter = Counter()
            for item in feedback_items:
                if item["priority"] in ["high", "critical"]:
                    issue_counter[item["subject"]] += 1
            
            top_issues = [
                {"issue": issue, "count": count, "priority": "high"}
                for issue, count in issue_counter.most_common(10)
            ]
            
            # Trending topics (from tags)
            all_tags = []
            for item in feedback_items:
                if item["tags"]:
                    all_tags.extend(item["tags"])
            
            trending_topics = [tag for tag, count in Counter(all_tags).most_common(10)]
            
            return FeedbackSummary(
                total_feedback=total_feedback,
                average_rating=round(average_rating, 2),
                category_breakdown=dict(category_breakdown),
                sentiment_analysis=dict(sentiment_analysis),
                priority_distribution=dict(priority_distribution),
                status_distribution=dict(status_distribution),
                top_issues=top_issues,
                trending_topics=trending_topics
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get feedback summary: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def generate_feedback_report(self, start_date: datetime = None, 
                               end_date: datetime = None) -> Dict:
        """Generate comprehensive feedback report"""
        summary = self.get_feedback_summary(start_date, end_date)
        
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            # Get user engagement metrics
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT user_id) as active_feedback_users,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as dissatisfied_count,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as satisfied_count
                FROM feedback 
                WHERE created_at BETWEEN %s AND %s
            ''', (start_date, end_date))
            
            engagement = cursor.fetchone()
            
            # Get resolution metrics
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_count,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_count,
                    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_count,
                    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600) as avg_resolution_hours
                FROM feedback 
                WHERE created_at BETWEEN %s AND %s
            ''', (start_date, end_date))
            
            resolution_metrics = cursor.fetchone()
            
            # Get most active feedback users
            cursor.execute('''
                SELECT 
                    u.email,
                    COUNT(f.id) as feedback_count,
                    AVG(f.rating) as avg_rating
                FROM feedback f
                JOIN users u ON f.user_id = u.id
                WHERE f.created_at BETWEEN %s AND %s
                GROUP BY u.id, u.email
                ORDER BY feedback_count DESC
                LIMIT 10
            ''', (start_date, end_date))
            
            top_contributors = [dict(row) for row in cursor.fetchall()]
            
            # Calculate satisfaction score (NPS-style)
            satisfied = engagement.get("satisfied_count", 0) or 0
            dissatisfied = engagement.get("dissatisfied_count", 0) or 0
            total_rated = satisfied + dissatisfied
            
            satisfaction_score = 0
            if total_rated > 0:
                satisfaction_score = round(((satisfied - dissatisfied) / total_rated) * 100, 1)
            
            report = {
                "report_metadata": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "generated_at": datetime.now().isoformat()
                },
                "summary": asdict(summary),
                "engagement_metrics": {
                    "active_feedback_users": engagement.get("active_feedback_users", 0),
                    "satisfaction_score": satisfaction_score,
                    "avg_rating": round(float(engagement.get("avg_rating", 0) or 0), 2)
                },
                "resolution_metrics": {
                    "resolved_count": resolution_metrics.get("resolved_count", 0),
                    "in_progress_count": resolution_metrics.get("in_progress_count", 0),
                    "open_count": resolution_metrics.get("open_count", 0),
                    "avg_resolution_hours": round(float(resolution_metrics.get("avg_resolution_hours", 0) or 0), 1)
                },
                "top_contributors": top_contributors,
                "insights": self._generate_insights(summary, engagement, resolution_metrics)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate feedback report: {e}")
            return {"error": str(e)}
        finally:
            cursor.close()
            conn.close()

    def _generate_insights(self, summary: FeedbackSummary, engagement: Dict, 
                          resolution: Dict) -> List[str]:
        """Generate actionable insights from feedback data"""
        insights = []
        
        # Rating insights
        if summary.average_rating < 3.0:
            insights.append(f"Average rating is low ({summary.average_rating}/5). Focus on critical issues.")
        elif summary.average_rating > 4.0:
            insights.append(f"High satisfaction ({summary.average_rating}/5). Consider expanding features.")
        
        # Category insights
        if summary.category_breakdown:
            top_category = max(summary.category_breakdown, key=summary.category_breakdown.get)
            insights.append(f"Most feedback in '{top_category}' category. Review this area.")
        
        # Priority insights
        if summary.priority_distribution.get("critical", 0) > 0:
            critical_count = summary.priority_distribution["critical"]
            insights.append(f"{critical_count} critical issues need immediate attention.")
        
        # Resolution insights
        open_count = resolution.get("open_count", 0)
        if open_count > summary.total_feedback * 0.5:
            insights.append(f"High backlog: {open_count} open feedback items. Consider increasing resources.")
        
        # Sentiment insights
        negative_sentiment = summary.sentiment_analysis.get("negative", 0)
        if negative_sentiment > summary.total_feedback * 0.4:
            insights.append("High negative sentiment. Address user pain points urgently.")
        
        # Trending insights
        if summary.trending_topics:
            top_trend = summary.trending_topics[0]
            insights.append(f"'{top_trend}' is trending in feedback. Consider feature improvements.")
        
        return insights

    def request_feedback(self, user_id: str, context: str = "general", 
                        feature_context: str = None) -> str:
        """Request feedback from specific user"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if we've requested feedback recently
            cursor.execute('''
                SELECT created_at FROM feedback_requests 
                WHERE user_id = %s 
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id,))
            
            last_request = cursor.fetchone()
            if last_request:
                days_since = (datetime.now() - last_request[0]).days
                if days_since < self.config["feedback_request_frequency"]:
                    raise ValueError(f"Feedback requested {days_since} days ago. Wait {self.config['feedback_request_frequency'] - days_since} more days.")
            
            # Create feedback request
            cursor.execute('''
                INSERT INTO feedback_requests (user_id, request_type, feature_context)
                VALUES (%s, %s, %s)
                RETURNING id
            ''', (user_id, context, feature_context))
            
            request_id = cursor.fetchone()[0]
            conn.commit()
            
            # Send feedback request email/notification
            self._send_feedback_request(user_id, context, feature_context)
            
            self.logger.info(f"Requested feedback from user {user_id}: {context}")
            return str(request_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to request feedback: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _send_feedback_request(self, user_id: str, context: str, feature_context: str = None):
        """Send feedback request to user"""
        # In production, implement email/in-app notification
        self.logger.info(f"Feedback request notification would be sent to user {user_id}")

    def _send_critical_feedback_alert(self, feedback_id: str, user_id: str, 
                                    subject: str, message: str):
        """Send alert for critical feedback"""
        if self.config["email_notifications"]:
            # In production, implement email alert to team
            self.logger.warning(f"CRITICAL FEEDBACK: {feedback_id} - {subject}")

    def _auto_assign_feedback(self, feedback_id: str, category: str, priority: str):
        """Auto-assign feedback based on category and priority"""
        # In production, implement assignment logic
        self.logger.info(f"Auto-assignment logic would run for feedback {feedback_id}")

    def update_feedback_status(self, feedback_id: str, status: str, 
                             assignee_id: str = None, resolution_notes: str = None) -> bool:
        """Update feedback status"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            update_fields = ["status = %s", "updated_at = %s"]
            values = [status, datetime.now()]
            
            if assignee_id:
                update_fields.append("assignee_id = %s")
                values.append(assignee_id)
            
            if status == "resolved":
                update_fields.append("resolved_at = %s")
                values.append(datetime.now())
                
                if resolution_notes:
                    update_fields.append("resolution_notes = %s")
                    values.append(resolution_notes)
            
            values.append(feedback_id)
            
            cursor.execute(f'''
                UPDATE feedback 
                SET {", ".join(update_fields)}
                WHERE id = %s
            ''', values)
            
            updated = cursor.rowcount > 0
            conn.commit()
            
            if updated:
                self.logger.info(f"Updated feedback {feedback_id} status to {status}")
            
            return updated
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to update feedback status: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def export_feedback(self, format: str = "json", start_date: datetime = None,
                       end_date: datetime = None, category: str = None) -> str:
        """Export feedback data"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            where_conditions = []
            params = []
            
            if start_date:
                where_conditions.append("created_at >= %s")
                params.append(start_date)
            
            if end_date:
                where_conditions.append("created_at <= %s")
                params.append(end_date)
            
            if category:
                where_conditions.append("category = %s")
                params.append(category)
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            cursor.execute(f'''
                SELECT f.*, u.email as user_email
                FROM feedback f
                LEFT JOIN users u ON f.user_id = u.id
                {where_clause}
                ORDER BY f.created_at DESC
            ''', params)
            
            feedback_data = [dict(row) for row in cursor.fetchall()]
            
            # Export based on format
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format.lower() == "json":
                export_file = self.data_dir / f"feedback_export_{timestamp}.json"
                with open(export_file, 'w') as f:
                    json.dump(feedback_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                import csv
                export_file = self.data_dir / f"feedback_export_{timestamp}.csv"
                
                if feedback_data:
                    with open(export_file, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=feedback_data[0].keys())
                        writer.writeheader()
                        writer.writerows(feedback_data)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported {len(feedback_data)} feedback items to {export_file}")
            return str(export_file)
            
        except Exception as e:
            self.logger.error(f"Failed to export feedback: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Feedback Aggregator')
    parser.add_argument('--environment', default='beta', help='Environment')
    parser.add_argument('--config', help='Configuration file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Submit feedback
    submit_parser = subparsers.add_parser('submit', help='Submit feedback')
    submit_parser.add_argument('--user-id', required=True, help='User ID')
    submit_parser.add_argument('--category', required=True, help='Feedback category')
    submit_parser.add_argument('--subject', required=True, help='Subject')
    submit_parser.add_argument('--message', required=True, help='Message')
    submit_parser.add_argument('--rating', type=int, help='Rating (1-5)')
    
    # Summary
    summary_parser = subparsers.add_parser('summary', help='Get feedback summary')
    summary_parser.add_argument('--days', type=int, default=30, help='Days to analyze')
    
    # Report
    report_parser = subparsers.add_parser('report', help='Generate feedback report')
    report_parser.add_argument('--days', type=int, default=30, help='Days to analyze')
    
    # Export
    export_parser = subparsers.add_parser('export', help='Export feedback data')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Export format')
    export_parser.add_argument('--days', type=int, default=30, help='Days to export')
    export_parser.add_argument('--category', help='Filter by category')
    
    # Update status
    update_parser = subparsers.add_parser('update', help='Update feedback status')
    update_parser.add_argument('--feedback-id', required=True, help='Feedback ID')
    update_parser.add_argument('--status', required=True, help='New status')
    update_parser.add_argument('--assignee', help='Assignee user ID')
    update_parser.add_argument('--notes', help='Resolution notes')
    
    args = parser.parse_args()
    
    aggregator = FeedbackAggregator(args.environment, args.config)
    
    if args.command == 'submit':
        feedback_id = aggregator.submit_feedback(
            args.user_id, args.category, args.subject, args.message, args.rating
        )
        print(f"Feedback submitted: {feedback_id}")
    
    elif args.command == 'summary':
        start_date = datetime.now() - timedelta(days=args.days)
        summary = aggregator.get_feedback_summary(start_date)
        print(json.dumps(asdict(summary), indent=2))
    
    elif args.command == 'report':
        start_date = datetime.now() - timedelta(days=args.days)
        report = aggregator.generate_feedback_report(start_date)
        print(json.dumps(report, indent=2, default=str))
    
    elif args.command == 'export':
        start_date = datetime.now() - timedelta(days=args.days)
        export_file = aggregator.export_feedback(args.format, start_date, category=args.category)
        print(f"Exported to: {export_file}")
    
    elif args.command == 'update':
        success = aggregator.update_feedback_status(
            args.feedback_id, args.status, args.assignee, args.notes
        )
        print("Status updated" if success else "Update failed")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()