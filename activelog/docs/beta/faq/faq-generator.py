#!/usr/bin/env python3

"""
Interactive FAQ Generator for ActiveLog Beta
Generates dynamic FAQ responses using knowledge base and AI assistance
"""

import os
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3

@dataclass
class FAQEntry:
    id: str
    question: str
    answer: str
    category: str
    keywords: List[str]
    popularity: int = 0
    last_accessed: str = None
    helpful_votes: int = 0
    unhelpful_votes: int = 0

@dataclass
class SearchResult:
    entry: FAQEntry
    relevance_score: float
    matched_keywords: List[str]

class FAQGenerator:
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or "/home/activeloguser/activelog/docs/beta/faq/data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "faq.db"
        self.knowledge_base = self._load_knowledge_base()
        
        self._init_database()
        self._populate_initial_data()

    def _init_database(self):
        """Initialize SQLite database for FAQ storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faq_entries (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT NOT NULL,
                keywords TEXT,
                popularity INTEGER DEFAULT 0,
                last_accessed TEXT,
                helpful_votes INTEGER DEFAULT 0,
                unhelpful_votes INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faq_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                results_found INTEGER,
                user_selected TEXT,
                satisfaction_rating INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faq_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                comment TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES faq_entries (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def _load_knowledge_base(self) -> Dict:
        """Load knowledge base with predefined FAQ entries"""
        return {
            "categories": {
                "account": {
                    "name": "Account & Login",
                    "keywords": ["login", "password", "account", "authentication", "signin", "register"]
                },
                "beta": {
                    "name": "Beta Program", 
                    "keywords": ["beta", "testing", "nda", "invitation", "program", "access"]
                },
                "features": {
                    "name": "Features & Usage",
                    "keywords": ["features", "how to", "usage", "functionality", "tools"]
                },
                "technical": {
                    "name": "Technical Issues",
                    "keywords": ["error", "bug", "problem", "issue", "broken", "slow", "performance"]
                },
                "api": {
                    "name": "API & Development",
                    "keywords": ["api", "development", "sdk", "programming", "integration", "webhook"]
                },
                "billing": {
                    "name": "Billing & Plans",
                    "keywords": ["billing", "pricing", "payment", "plan", "subscription", "cost"]
                },
                "privacy": {
                    "name": "Privacy & Security",
                    "keywords": ["privacy", "security", "data", "gdpr", "encryption", "protection"]
                }
            },
            "common_responses": {
                "contact_support": "For additional help, contact beta-support@activelog.dev or use the in-app chat feature.",
                "beta_specific": "This is a beta-specific feature that may change before general availability.",
                "documentation_link": "For detailed information, see our documentation at docs.activelog.dev/beta",
                "video_tutorial": "Check out our video tutorials for step-by-step guidance."
            }
        }

    def _populate_initial_data(self):
        """Populate database with initial FAQ entries"""
        initial_faqs = [
            {
                "id": "login_issues",
                "question": "Why can't I log in to ActiveLog?",
                "answer": """Common login issues and solutions:

**Account Locked:** Wait 15 minutes after 5 failed attempts
**Browser Issues:** Try incognito/private mode or clear browser cache  
**Beta Access:** Ensure your beta invitation hasn't expired
**NDA Required:** Make sure you've signed the NDA agreement
**Caps Lock:** Check if Caps Lock is accidentally enabled

**Beta-specific:** Use the beta login URL: https://beta.activelog.dev/login

Still having issues? Contact beta-support@activelog.dev""",
                "category": "account",
                "keywords": ["login", "password", "signin", "access", "authentication"]
            },
            {
                "id": "beta_program_info",
                "question": "What is the ActiveLog beta program?",
                "answer": """The ActiveLog beta program gives selected users early access to new features:

**Duration:** 6-month program (subject to extension)
**Participants:** 100 selected beta testers
**Access:** All core features plus experimental features
**Requirements:** Signed NDA, active feedback participation

**Benefits:**
- Early access to new features
- Direct influence on product development  
- Priority support from our team
- Extended API limits and advanced features

For more information about beta responsibilities, see our Beta Program Guide.""",
                "category": "beta",
                "keywords": ["beta", "program", "testing", "features", "access"]
            },
            {
                "id": "file_upload_slow",
                "question": "Why are file uploads slow or failing?",
                "answer": """File upload troubleshooting steps:

**Check file size:** Max 1GB per file in beta
**Verify file type:** Ensure it's a supported format
**Test connection:** Try uploading a small test file
**Clear browser cache:** May resolve upload issues
**Try different browser:** Switch to Chrome/Firefox

**Network Issues:**
- Check internet connection stability
- Disable VPN temporarily
- Try uploading from different device

**Beta limits:** 1GB per file, 10GB total storage

Contact beta-support@activelog.dev if issues persist.""",
                "category": "technical",
                "keywords": ["upload", "file", "slow", "failing", "problem", "sync"]
            },
            {
                "id": "api_access",
                "question": "How do I get API access for the beta?",
                "answer": """Beta users get enhanced API access:

1. Go to Settings → API Keys
2. Click "Generate New Key"
3. Choose scopes (read, write, admin)
4. Copy and store your API key securely

**Beta API limits:**
- 10,000 requests/hour (vs 1,000 for regular users)
- Higher file upload limits
- Access to experimental endpoints

**Base URL:** `https://beta-api.activelog.dev/v1`
**Documentation:** See our API Reference guide

**SDKs available:** JavaScript, Python, PHP, and more""",
                "category": "api",
                "keywords": ["api", "access", "key", "development", "programming", "sdk"]
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for faq in initial_faqs:
            cursor.execute('SELECT id FROM faq_entries WHERE id = ?', (faq['id'],))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO faq_entries (id, question, answer, category, keywords)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    faq['id'],
                    faq['question'],
                    faq['answer'],
                    faq['category'],
                    json.dumps(faq['keywords'])
                ))
        
        conn.commit()
        conn.close()

    def search_faq(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search FAQ entries using keyword matching and relevance scoring"""
        query_lower = query.lower()
        query_words = re.findall(r'\w+', query_lower)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM faq_entries')
        entries = cursor.fetchall()
        
        results = []
        
        for entry_data in entries:
            entry = FAQEntry(
                id=entry_data[0],
                question=entry_data[1],
                answer=entry_data[2],
                category=entry_data[3],
                keywords=json.loads(entry_data[4]) if entry_data[4] else [],
                popularity=entry_data[5] or 0,
                last_accessed=entry_data[6],
                helpful_votes=entry_data[7] or 0,
                unhelpful_votes=entry_data[8] or 0
            )
            
            # Calculate relevance score
            score = 0
            matched_keywords = []
            
            # Check question match
            question_words = re.findall(r'\w+', entry.question.lower())
            question_matches = sum(1 for word in query_words if word in question_words)
            score += question_matches * 3
            
            # Check keyword match
            keyword_matches = sum(1 for word in query_words if word in [kw.lower() for kw in entry.keywords])
            score += keyword_matches * 2
            matched_keywords.extend([kw for kw in entry.keywords if kw.lower() in query_words])
            
            # Check answer match (less weight)
            answer_words = re.findall(r'\w+', entry.answer.lower())
            answer_matches = sum(1 for word in query_words if word in answer_words)
            score += answer_matches * 0.5
            
            # Boost popular entries slightly
            score += entry.popularity * 0.1
            
            # Boost entries with good votes
            if entry.helpful_votes + entry.unhelpful_votes > 0:
                vote_ratio = entry.helpful_votes / (entry.helpful_votes + entry.unhelpful_votes)
                score += vote_ratio
            
            if score > 0:
                results.append(SearchResult(
                    entry=entry,
                    relevance_score=score,
                    matched_keywords=matched_keywords
                ))
        
        # Sort by relevance score and limit results
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Log search
        cursor.execute('''
            INSERT INTO faq_searches (query, results_found)
            VALUES (?, ?)
        ''', (query, len(results[:limit])))
        
        conn.commit()
        conn.close()
        
        return results[:limit]

    def get_entry_by_id(self, entry_id: str) -> Optional[FAQEntry]:
        """Get specific FAQ entry by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM faq_entries WHERE id = ?', (entry_id,))
        entry_data = cursor.fetchone()
        
        if entry_data:
            # Update access count and timestamp
            cursor.execute('''
                UPDATE faq_entries 
                SET popularity = popularity + 1, last_accessed = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), entry_id))
            conn.commit()
            
            entry = FAQEntry(
                id=entry_data[0],
                question=entry_data[1],
                answer=entry_data[2],
                category=entry_data[3],
                keywords=json.loads(entry_data[4]) if entry_data[4] else [],
                popularity=entry_data[5] or 0,
                last_accessed=entry_data[6],
                helpful_votes=entry_data[7] or 0,
                unhelpful_votes=entry_data[8] or 0
            )
            
            conn.close()
            return entry
        
        conn.close()
        return None

    def add_faq_entry(self, question: str, answer: str, category: str, 
                     keywords: List[str] = None) -> str:
        """Add new FAQ entry"""
        # Generate ID from question
        entry_id = re.sub(r'[^a-z0-9]', '_', question.lower()[:50])
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO faq_entries (id, question, answer, category, keywords)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            entry_id,
            question,
            answer,
            category,
            json.dumps(keywords or [])
        ))
        
        conn.commit()
        conn.close()
        
        return entry_id

    def vote_on_entry(self, entry_id: str, helpful: bool):
        """Record vote on FAQ entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if helpful:
            cursor.execute('UPDATE faq_entries SET helpful_votes = helpful_votes + 1 WHERE id = ?', (entry_id,))
        else:
            cursor.execute('UPDATE faq_entries SET unhelpful_votes = unhelpful_votes + 1 WHERE id = ?', (entry_id,))
        
        conn.commit()
        conn.close()

    def add_feedback(self, entry_id: str, feedback_type: str, comment: str = None):
        """Add feedback for FAQ entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO faq_feedback (entry_id, feedback_type, comment)
            VALUES (?, ?, ?)
        ''', (entry_id, feedback_type, comment))
        
        conn.commit()
        conn.close()

    def get_popular_entries(self, limit: int = 10) -> List[FAQEntry]:
        """Get most popular FAQ entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM faq_entries 
            ORDER BY popularity DESC, helpful_votes DESC
            LIMIT ?
        ''', (limit,))
        
        entries = []
        for entry_data in cursor.fetchall():
            entries.append(FAQEntry(
                id=entry_data[0],
                question=entry_data[1],
                answer=entry_data[2],
                category=entry_data[3],
                keywords=json.loads(entry_data[4]) if entry_data[4] else [],
                popularity=entry_data[5] or 0,
                last_accessed=entry_data[6],
                helpful_votes=entry_data[7] or 0,
                unhelpful_votes=entry_data[8] or 0
            ))
        
        conn.close()
        return entries

    def generate_smart_answer(self, query: str) -> Dict:
        """Generate smart answer using search and context"""
        # Search existing FAQs
        results = self.search_faq(query, limit=3)
        
        if not results:
            return {
                "type": "no_results",
                "message": "I couldn't find a specific answer to your question.",
                "suggestions": [
                    "Try rephrasing your question",
                    "Contact beta-support@activelog.dev for personalized help",
                    "Check our video tutorials for visual guidance",
                    "Browse our documentation for detailed information"
                ]
            }
        
        best_result = results[0]
        
        if best_result.relevance_score > 3:
            # High confidence answer
            return {
                "type": "direct_answer",
                "entry": asdict(best_result.entry),
                "confidence": "high",
                "relevance_score": best_result.relevance_score,
                "matched_keywords": best_result.matched_keywords,
                "related_entries": [asdict(r.entry) for r in results[1:]]
            }
        else:
            # Multiple possible answers
            return {
                "type": "multiple_answers",
                "message": "I found several answers that might help:",
                "results": [
                    {
                        "entry": asdict(r.entry),
                        "relevance_score": r.relevance_score,
                        "matched_keywords": r.matched_keywords
                    }
                    for r in results
                ],
                "suggestion": "Select the most relevant answer or contact support for specific help."
            }

    def get_analytics(self) -> Dict:
        """Get FAQ analytics and statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Search statistics
        cursor.execute('SELECT COUNT(*) FROM faq_searches')
        total_searches = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(results_found) FROM faq_searches WHERE results_found > 0')
        avg_results = cursor.fetchone()[0] or 0
        
        # Popular queries
        cursor.execute('''
            SELECT query, COUNT(*) as count
            FROM faq_searches 
            GROUP BY query 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        popular_queries = [{"query": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Entry statistics
        cursor.execute('SELECT COUNT(*) FROM faq_entries')
        total_entries = cursor.fetchone()[0]
        
        cursor.execute('SELECT category, COUNT(*) FROM faq_entries GROUP BY category')
        category_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Satisfaction metrics
        cursor.execute('SELECT SUM(helpful_votes), SUM(unhelpful_votes) FROM faq_entries')
        votes = cursor.fetchone()
        helpful_total = votes[0] or 0
        unhelpful_total = votes[1] or 0
        
        satisfaction_rate = 0
        if helpful_total + unhelpful_total > 0:
            satisfaction_rate = helpful_total / (helpful_total + unhelpful_total) * 100
        
        conn.close()
        
        return {
            "searches": {
                "total": total_searches,
                "avg_results": round(avg_results, 2),
                "popular_queries": popular_queries
            },
            "content": {
                "total_entries": total_entries,
                "category_distribution": category_counts
            },
            "satisfaction": {
                "helpful_votes": helpful_total,
                "unhelpful_votes": unhelpful_total,
                "satisfaction_rate": round(satisfaction_rate, 1)
            }
        }

def main():
    parser = argparse.ArgumentParser(description='Interactive FAQ Generator')
    parser.add_argument('--action', choices=['search', 'add', 'popular', 'analytics'], 
                       default='search', help='Action to perform')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--question', help='Question for new FAQ entry')
    parser.add_argument('--answer', help='Answer for new FAQ entry')  
    parser.add_argument('--category', help='Category for new FAQ entry')
    parser.add_argument('--limit', type=int, default=5, help='Limit results')
    
    args = parser.parse_args()
    
    faq = FAQGenerator()
    
    if args.action == 'search':
        if not args.query:
            print("Please provide a search query with --query")
            return
        
        results = faq.search_faq(args.query, args.limit)
        
        if results:
            print(f"Found {len(results)} results for '{args.query}':\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.entry.question}")
                print(f"   Category: {result.entry.category}")
                print(f"   Relevance: {result.relevance_score:.1f}")
                print(f"   Keywords: {', '.join(result.matched_keywords)}")
                print()
                print(f"   {result.entry.answer[:200]}...")
                print("-" * 60)
        else:
            print(f"No results found for '{args.query}'")
    
    elif args.action == 'add':
        if not all([args.question, args.answer, args.category]):
            print("Please provide --question, --answer, and --category")
            return
        
        entry_id = faq.add_faq_entry(args.question, args.answer, args.category)
        print(f"Added FAQ entry: {entry_id}")
    
    elif args.action == 'popular':
        entries = faq.get_popular_entries(args.limit)
        print(f"Top {len(entries)} popular FAQ entries:\n")
        
        for entry in entries:
            print(f"• {entry.question}")
            print(f"  Category: {entry.category} | Views: {entry.popularity} | Votes: +{entry.helpful_votes}/-{entry.unhelpful_votes}")
            print()
    
    elif args.action == 'analytics':
        analytics = faq.get_analytics()
        print("FAQ Analytics:")
        print("=" * 50)
        print(f"Total Searches: {analytics['searches']['total']}")
        print(f"Average Results per Search: {analytics['searches']['avg_results']}")
        print(f"Total FAQ Entries: {analytics['content']['total_entries']}")
        print(f"Satisfaction Rate: {analytics['satisfaction']['satisfaction_rate']}%")
        print()
        
        print("Popular Queries:")
        for query in analytics['searches']['popular_queries'][:5]:
            print(f"  • '{query['query']}' ({query['count']} times)")
        print()
        
        print("Category Distribution:")
        for category, count in analytics['content']['category_distribution'].items():
            print(f"  • {category}: {count} entries")

if __name__ == '__main__':
    main()