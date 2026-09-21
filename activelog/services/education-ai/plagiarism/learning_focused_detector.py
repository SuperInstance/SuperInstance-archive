"""
Learning-Focused Plagiarism Detection System

Educational plagiarism detection system that emphasizes learning and academic
integrity development rather than just detection. Provides constructive feedback,
citation guidance, and originality improvement suggestions.
"""

import asyncio
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import re
import difflib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimilarityType(Enum):
    EXACT_MATCH = "exact_match"
    PARAPHRASE = "paraphrase"
    STRUCTURAL = "structural"
    CITATION_MISSING = "citation_missing"
    SELF_PLAGIARISM = "self_plagiarism"

class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class LearningAction(Enum):
    CITATION_GUIDANCE = "citation_guidance"
    PARAPHRASING_HELP = "paraphrasing_help"
    ORIGINALITY_COACHING = "originality_coaching"
    ACADEMIC_INTEGRITY_EDUCATION = "academic_integrity_education"
    RESEARCH_SKILLS_DEVELOPMENT = "research_skills_development"

@dataclass
class SimilarityMatch:
    match_id: str
    student_submission_id: str
    source_text: str
    matched_text: str
    similarity_score: float
    similarity_type: SimilarityType
    severity_level: SeverityLevel
    start_position: int
    end_position: int
    source_info: Dict[str, str] = field(default_factory=dict)
    context_before: str = ""
    context_after: str = ""

@dataclass
class SubmissionAnalysis:
    submission_id: str
    student_id: str
    assignment_id: str
    submission_text: str
    total_similarity_score: float
    unique_matches: List[SimilarityMatch] = field(default_factory=list)
    originality_score: float = 0.0
    citation_quality_score: float = 0.0
    academic_writing_score: float = 0.0
    learning_recommendations: List[str] = field(default_factory=list)
    analysis_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class LearningRecommendation:
    recommendation_id: str
    student_id: str
    action_type: LearningAction
    priority: int
    description: str
    resources: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    completion_status: str = "pending"

@dataclass
class CitationPattern:
    pattern_id: str
    citation_style: str
    pattern_regex: str
    example: str
    description: str

@dataclass
class AcademicIntegrityProfile:
    student_id: str
    total_submissions: int = 0
    average_originality: float = 0.0
    citation_improvement_trend: float = 0.0
    integrity_violations: List[Dict] = field(default_factory=list)
    learning_progress: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

class LearningFocusedPlagiarismDetector:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.citation_patterns = {}
        self.common_phrases = set()
        self.educational_resources = {}
        self.init_database()
        self._load_citation_patterns()
        self._load_common_phrases()
        self._load_educational_resources()
        
    def init_database(self):
        """Initialize database tables for plagiarism detection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                student_id TEXT,
                assignment_id TEXT,
                submission_text TEXT,
                submission_hash TEXT,
                submission_date TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS similarity_matches (
                match_id TEXT PRIMARY KEY,
                student_submission_id TEXT,
                source_text TEXT,
                matched_text TEXT,
                similarity_score REAL,
                similarity_type TEXT,
                severity_level TEXT,
                start_position INTEGER,
                end_position INTEGER,
                source_info TEXT,
                context_before TEXT,
                context_after TEXT,
                FOREIGN KEY (student_submission_id) REFERENCES submissions (submission_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submission_analyses (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id TEXT,
                student_id TEXT,
                assignment_id TEXT,
                total_similarity_score REAL,
                originality_score REAL,
                citation_quality_score REAL,
                academic_writing_score REAL,
                learning_recommendations TEXT,
                analysis_timestamp TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES submissions (submission_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_recommendations (
                recommendation_id TEXT PRIMARY KEY,
                student_id TEXT,
                action_type TEXT,
                priority INTEGER,
                description TEXT,
                resources TEXT,
                expected_outcome TEXT,
                completion_status TEXT,
                created_date TIMESTAMP,
                completed_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS academic_integrity_profiles (
                student_id TEXT PRIMARY KEY,
                total_submissions INTEGER,
                average_originality REAL,
                citation_improvement_trend REAL,
                integrity_violations TEXT,
                learning_progress TEXT,
                last_updated TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reference_corpus (
                document_id TEXT PRIMARY KEY,
                source_type TEXT,
                title TEXT,
                author TEXT,
                content_hash TEXT,
                content_text TEXT,
                metadata TEXT,
                indexed_date TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Learning-focused plagiarism detection database initialized")

    def _load_citation_patterns(self):
        """Load citation patterns for different academic styles"""
        patterns = [
            CitationPattern(
                "apa_author_date",
                "APA",
                r'\([A-Za-z]+,?\s+\d{4}\)',
                "(Smith, 2023)",
                "APA author-date citation format"
            ),
            CitationPattern(
                "mla_author_page",
                "MLA",
                r'\([A-Za-z]+\s+\d+\)',
                "(Smith 45)",
                "MLA author-page citation format"
            ),
            CitationPattern(
                "chicago_footnote",
                "Chicago",
                r'\^\d+|\[\d+\]',
                "[1] or ^1",
                "Chicago footnote citation format"
            ),
            CitationPattern(
                "ieee_numeric",
                "IEEE",
                r'\[\d+\]',
                "[1]",
                "IEEE numeric citation format"
            )
        ]
        
        self.citation_patterns = {p.pattern_id: p for p in patterns}

    def _load_common_phrases(self):
        """Load common academic phrases that shouldn't trigger plagiarism alerts"""
        common_phrases = [
            "according to",
            "in conclusion",
            "on the other hand",
            "it is important to note",
            "in recent years",
            "research has shown",
            "it can be argued that",
            "furthermore",
            "however",
            "therefore",
            "in addition",
            "as a result"
        ]
        
        self.common_phrases = set(phrase.lower() for phrase in common_phrases)

    def _load_educational_resources(self):
        """Load educational resources for different learning needs"""
        self.educational_resources = {
            LearningAction.CITATION_GUIDANCE: [
                "Citation Style Guide (APA, MLA, Chicago)",
                "Interactive Citation Builder",
                "Common Citation Mistakes and How to Avoid Them",
                "When and How to Cite Sources"
            ],
            LearningAction.PARAPHRASING_HELP: [
                "Effective Paraphrasing Techniques",
                "Paraphrasing vs. Summarizing",
                "Practice Exercises: Paraphrasing Academic Texts",
                "Avoiding Patchwork Plagiarism"
            ],
            LearningAction.ORIGINALITY_COACHING: [
                "Developing Your Academic Voice",
                "Synthesizing Multiple Sources",
                "Critical Analysis and Original Thinking",
                "Creative Approaches to Academic Writing"
            ],
            LearningAction.ACADEMIC_INTEGRITY_EDUCATION: [
                "Understanding Academic Integrity",
                "Types of Academic Misconduct",
                "Building Ethical Research Practices",
                "Campus Academic Integrity Policies"
            ],
            LearningAction.RESEARCH_SKILLS_DEVELOPMENT: [
                "Effective Research Strategies",
                "Evaluating Source Credibility",
                "Note-Taking for Research",
                "Research Planning and Organization"
            ]
        }

    async def analyze_submission(self, submission_id: str, student_id: str, 
                               assignment_id: str, submission_text: str,
                               comparison_corpus: List[str] = None) -> SubmissionAnalysis:
        """
        Comprehensive analysis of student submission for learning-focused feedback
        
        Args:
            submission_id: Unique submission identifier
            student_id: Student identifier
            assignment_id: Assignment identifier
            submission_text: Student's submission content
            comparison_corpus: Optional corpus for comparison
            
        Returns:
            Complete submission analysis with learning recommendations
        """
        logger.info(f"Analyzing submission {submission_id} for student {student_id}")
        
        # Store submission
        await self._store_submission(submission_id, student_id, assignment_id, submission_text)
        
        # Find similarity matches
        matches = await self._find_similarity_matches(submission_id, submission_text, comparison_corpus)
        
        # Calculate scores
        total_similarity = self._calculate_total_similarity(matches)
        originality_score = max(0.0, 1.0 - total_similarity)
        citation_quality = await self._assess_citation_quality(submission_text)
        academic_writing_score = self._assess_academic_writing(submission_text)
        
        # Generate learning recommendations
        recommendations = await self._generate_learning_recommendations(
            student_id, matches, originality_score, citation_quality, academic_writing_score
        )
        
        analysis = SubmissionAnalysis(
            submission_id=submission_id,
            student_id=student_id,
            assignment_id=assignment_id,
            submission_text=submission_text,
            total_similarity_score=total_similarity,
            unique_matches=matches,
            originality_score=originality_score,
            citation_quality_score=citation_quality,
            academic_writing_score=academic_writing_score,
            learning_recommendations=[rec.description for rec in recommendations]
        )
        
        await self._save_analysis(analysis)
        
        # Update student's academic integrity profile
        await self._update_integrity_profile(student_id, analysis)
        
        logger.info(f"Analysis complete - Originality: {originality_score:.2f}, Citation Quality: {citation_quality:.2f}")
        return analysis

    async def _find_similarity_matches(self, submission_id: str, text: str, 
                                     corpus: List[str] = None) -> List[SimilarityMatch]:
        """Find similarity matches with focus on learning opportunities"""
        matches = []
        
        # Compare against reference corpus
        if corpus:
            for i, reference_text in enumerate(corpus):
                match_results = self._compare_texts(text, reference_text)
                for match_info in match_results:
                    if match_info['similarity'] > 0.3:  # Significant similarity threshold
                        match = SimilarityMatch(
                            match_id=f"{submission_id}_match_{len(matches)}",
                            student_submission_id=submission_id,
                            source_text=match_info['source_segment'],
                            matched_text=match_info['student_segment'],
                            similarity_score=match_info['similarity'],
                            similarity_type=match_info['type'],
                            severity_level=self._determine_severity(match_info),
                            start_position=match_info['start'],
                            end_position=match_info['end'],
                            source_info={"corpus_index": str(i), "type": "reference_corpus"},
                            context_before=match_info.get('context_before', ''),
                            context_after=match_info.get('context_after', '')
                        )
                        matches.append(match)
                        await self._save_similarity_match(match)
        
        # Check against previous submissions (self-plagiarism)
        previous_submissions = await self._get_previous_submissions(submission_id)
        for prev_submission in previous_submissions:
            self_matches = self._compare_texts(text, prev_submission['text'])
            for match_info in self_matches:
                if match_info['similarity'] > 0.5:  # Higher threshold for self-plagiarism
                    match = SimilarityMatch(
                        match_id=f"{submission_id}_self_{len(matches)}",
                        student_submission_id=submission_id,
                        source_text=match_info['source_segment'],
                        matched_text=match_info['student_segment'],
                        similarity_score=match_info['similarity'],
                        similarity_type=SimilarityType.SELF_PLAGIARISM,
                        severity_level=SeverityLevel.MEDIUM,
                        start_position=match_info['start'],
                        end_position=match_info['end'],
                        source_info={
                            "previous_submission_id": prev_submission['id'],
                            "submission_date": prev_submission['date']
                        }
                    )
                    matches.append(match)
                    await self._save_similarity_match(match)
        
        return matches

    def _compare_texts(self, student_text: str, reference_text: str) -> List[Dict[str, Any]]:
        """Compare two texts and identify similar segments"""
        matches = []
        
        # Tokenize texts into sentences
        student_sentences = self._tokenize_sentences(student_text)
        reference_sentences = self._tokenize_sentences(reference_text)
        
        for i, student_sent in enumerate(student_sentences):
            for j, ref_sent in enumerate(reference_sentences):
                similarity = self._calculate_sentence_similarity(student_sent, ref_sent)
                
                if similarity > 0.3:
                    # Determine match type
                    match_type = self._classify_similarity(student_sent, ref_sent, similarity)
                    
                    # Skip common phrases
                    if not self._is_common_phrase(student_sent):
                        match_info = {
                            'student_segment': student_sent,
                            'source_segment': ref_sent,
                            'similarity': similarity,
                            'type': match_type,
                            'start': self._find_sentence_position(student_text, student_sent),
                            'end': self._find_sentence_position(student_text, student_sent) + len(student_sent)
                        }
                        matches.append(match_info)
        
        return matches

    def _tokenize_sentences(self, text: str) -> List[str]:
        """Simple sentence tokenization"""
        # Basic sentence splitting (could be enhanced with NLTK)
        sentences = re.split(r'[.!?]+', text)
        return [sent.strip() for sent in sentences if sent.strip() and len(sent.strip()) > 10]

    def _calculate_sentence_similarity(self, sent1: str, sent2: str) -> float:
        """Calculate similarity between two sentences"""
        # Use difflib for sequence matching
        matcher = difflib.SequenceMatcher(None, sent1.lower(), sent2.lower())
        return matcher.ratio()

    def _classify_similarity(self, student_sent: str, ref_sent: str, similarity: float) -> SimilarityType:
        """Classify the type of similarity found"""
        if similarity >= 0.95:
            return SimilarityType.EXACT_MATCH
        elif similarity >= 0.7:
            # Check if it's a paraphrase (similar structure, different words)
            student_words = set(student_sent.lower().split())
            ref_words = set(ref_sent.lower().split())
            word_overlap = len(student_words.intersection(ref_words)) / len(student_words.union(ref_words))
            
            if word_overlap < 0.5:
                return SimilarityType.PARAPHRASE
            else:
                return SimilarityType.STRUCTURAL
        elif similarity >= 0.4:
            return SimilarityType.STRUCTURAL
        else:
            return SimilarityType.CITATION_MISSING

    def _is_common_phrase(self, sentence: str) -> bool:
        """Check if sentence contains only common academic phrases"""
        sentence_lower = sentence.lower()
        for phrase in self.common_phrases:
            if phrase in sentence_lower and len(sentence) < 100:
                return True
        return False

    def _find_sentence_position(self, text: str, sentence: str) -> int:
        """Find the position of a sentence in the text"""
        return text.find(sentence)

    def _determine_severity(self, match_info: Dict[str, Any]) -> SeverityLevel:
        """Determine severity level of similarity match"""
        similarity = match_info['similarity']
        match_type = match_info['type']
        
        if match_type == SimilarityType.EXACT_MATCH and similarity >= 0.95:
            return SeverityLevel.CRITICAL
        elif similarity >= 0.8:
            return SeverityLevel.HIGH
        elif similarity >= 0.6:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW

    def _calculate_total_similarity(self, matches: List[SimilarityMatch]) -> float:
        """Calculate overall similarity score"""
        if not matches:
            return 0.0
        
        # Weight matches by severity
        severity_weights = {
            SeverityLevel.CRITICAL: 1.0,
            SeverityLevel.HIGH: 0.8,
            SeverityLevel.MEDIUM: 0.6,
            SeverityLevel.LOW: 0.3
        }
        
        total_weighted_similarity = sum(
            match.similarity_score * severity_weights[match.severity_level] 
            for match in matches
        )
        
        # Normalize by number of matches to avoid penalty for thoroughness
        return min(1.0, total_weighted_similarity / max(len(matches), 1))

    async def _assess_citation_quality(self, text: str) -> float:
        """Assess quality and completeness of citations"""
        score = 0.0
        
        # Count citations using different patterns
        total_citations = 0
        for pattern in self.citation_patterns.values():
            citations = re.findall(pattern.pattern_regex, text)
            total_citations += len(citations)
        
        if total_citations > 0:
            score += 0.4  # Base score for having citations
            
            # Bonus for appropriate citation frequency (roughly 1 per 200 words)
            word_count = len(text.split())
            expected_citations = max(1, word_count // 200)
            citation_ratio = min(1.0, total_citations / expected_citations)
            score += 0.3 * citation_ratio
            
            # Check for bibliography/references section
            if re.search(r'(references|bibliography|works cited)', text.lower()):
                score += 0.2
            
            # Check citation placement (not all at the end)
            text_thirds = len(text) // 3
            citations_in_body = 0
            for pattern in self.citation_patterns.values():
                body_citations = re.findall(pattern.pattern_regex, text[:text_thirds*2])
                citations_in_body += len(body_citations)
            
            if citations_in_body > 0:
                score += 0.1
        
        return min(1.0, score)

    def _assess_academic_writing(self, text: str) -> float:
        """Assess academic writing quality indicators"""
        score = 0.0
        
        # Word count appropriateness
        word_count = len(text.split())
        if word_count >= 300:  # Minimum for meaningful analysis
            score += 0.2
        
        # Sentence complexity
        sentences = self._tokenize_sentences(text)
        if sentences:
            avg_sentence_length = sum(len(sent.split()) for sent in sentences) / len(sentences)
            if 15 <= avg_sentence_length <= 25:  # Appropriate academic sentence length
                score += 0.2
        
        # Academic vocabulary
        academic_indicators = [
            'however', 'furthermore', 'therefore', 'nevertheless', 'consequently',
            'analysis', 'research', 'study', 'investigation', 'findings',
            'significant', 'indicates', 'suggests', 'demonstrates', 'evidence'
        ]
        
        text_lower = text.lower()
        academic_word_count = sum(1 for word in academic_indicators if word in text_lower)
        if academic_word_count >= 5:
            score += 0.2
        
        # Paragraph structure (basic check)
        paragraphs = text.split('\n\n')
        if len(paragraphs) >= 3:  # Multiple paragraphs
            score += 0.2
        
        # Coherence indicators (transition words)
        transitions = ['first', 'second', 'next', 'finally', 'in addition', 'moreover', 'on the other hand']
        transition_count = sum(1 for trans in transitions if trans in text_lower)
        if transition_count >= 2:
            score += 0.2
        
        return min(1.0, score)

    async def _generate_learning_recommendations(self, student_id: str, matches: List[SimilarityMatch],
                                               originality_score: float, citation_quality: float,
                                               academic_writing_score: float) -> List[LearningRecommendation]:
        """Generate personalized learning recommendations"""
        recommendations = []
        
        # Citation guidance
        if citation_quality < 0.5:
            rec = LearningRecommendation(
                recommendation_id=f"citation_{student_id}_{int(datetime.now().timestamp())}",
                student_id=student_id,
                action_type=LearningAction.CITATION_GUIDANCE,
                priority=1,
                description="Learn proper citation techniques and when to cite sources",
                resources=self.educational_resources[LearningAction.CITATION_GUIDANCE],
                expected_outcome="Improved citation accuracy and completeness"
            )
            recommendations.append(rec)
        
        # Paraphrasing help
        paraphrase_issues = sum(1 for match in matches if match.similarity_type == SimilarityType.PARAPHRASE)
        if paraphrase_issues > 2:
            rec = LearningRecommendation(
                recommendation_id=f"paraphrase_{student_id}_{int(datetime.now().timestamp())}",
                student_id=student_id,
                action_type=LearningAction.PARAPHRASING_HELP,
                priority=2,
                description="Practice effective paraphrasing techniques to express ideas in your own words",
                resources=self.educational_resources[LearningAction.PARAPHRASING_HELP],
                expected_outcome="Better ability to rephrase source material while maintaining meaning"
            )
            recommendations.append(rec)
        
        # Originality coaching
        if originality_score < 0.6:
            rec = LearningRecommendation(
                recommendation_id=f"originality_{student_id}_{int(datetime.now().timestamp())}",
                student_id=student_id,
                action_type=LearningAction.ORIGINALITY_COACHING,
                priority=1 if originality_score < 0.4 else 3,
                description="Develop your unique academic voice and original thinking skills",
                resources=self.educational_resources[LearningAction.ORIGINALITY_COACHING],
                expected_outcome="Increased originality and personal insight in academic work"
            )
            recommendations.append(rec)
        
        # Academic integrity education
        critical_matches = sum(1 for match in matches if match.severity_level == SeverityLevel.CRITICAL)
        if critical_matches > 0:
            rec = LearningRecommendation(
                recommendation_id=f"integrity_{student_id}_{int(datetime.now().timestamp())}",
                student_id=student_id,
                action_type=LearningAction.ACADEMIC_INTEGRITY_EDUCATION,
                priority=1,
                description="Understanding academic integrity principles and ethical research practices",
                resources=self.educational_resources[LearningAction.ACADEMIC_INTEGRITY_EDUCATION],
                expected_outcome="Clear understanding of academic integrity expectations"
            )
            recommendations.append(rec)
        
        # Research skills development
        if academic_writing_score < 0.5:
            rec = LearningRecommendation(
                recommendation_id=f"research_{student_id}_{int(datetime.now().timestamp())}",
                student_id=student_id,
                action_type=LearningAction.RESEARCH_SKILLS_DEVELOPMENT,
                priority=3,
                description="Enhance research and academic writing skills",
                resources=self.educational_resources[LearningAction.RESEARCH_SKILLS_DEVELOPMENT],
                expected_outcome="Improved research methodology and academic writing quality"
            )
            recommendations.append(rec)
        
        # Save recommendations
        for rec in recommendations:
            await self._save_learning_recommendation(rec)
        
        return recommendations

    def generate_feedback_report(self, analysis: SubmissionAnalysis) -> str:
        """Generate constructive feedback report for students"""
        report = []
        
        report.append("=== ACADEMIC INTEGRITY ANALYSIS REPORT ===\n")
        report.append(f"Submission ID: {analysis.submission_id}")
        report.append(f"Analysis Date: {analysis.analysis_timestamp.strftime('%Y-%m-%d %H:%M')}\n")
        
        # Overall scores
        report.append("=== OVERALL ASSESSMENT ===")
        report.append(f"Originality Score: {analysis.originality_score:.1%}")
        report.append(f"Citation Quality: {analysis.citation_quality_score:.1%}")
        report.append(f"Academic Writing Quality: {analysis.academic_writing_score:.1%}\n")
        
        # Similarity analysis
        if analysis.unique_matches:
            report.append("=== SIMILARITY ANALYSIS ===")
            report.append(f"Total Similarity Score: {analysis.total_similarity_score:.1%}")
            
            # Group matches by severity
            severity_groups = {}
            for match in analysis.unique_matches:
                severity = match.severity_level.value
                if severity not in severity_groups:
                    severity_groups[severity] = []
                severity_groups[severity].append(match)
            
            for severity in ['critical', 'high', 'medium', 'low']:
                if severity in severity_groups:
                    matches = severity_groups[severity]
                    report.append(f"\n{severity.upper()} Priority Matches ({len(matches)}):")
                    
                    for match in matches[:3]:  # Show top 3 matches per severity
                        report.append(f"  • {match.similarity_type.value.replace('_', ' ').title()}")
                        report.append(f"    Similarity: {match.similarity_score:.1%}")
                        report.append(f"    Text: \"{match.matched_text[:100]}...\"")
                        if match.source_info:
                            source_type = match.source_info.get('type', 'unknown')
                            report.append(f"    Source: {source_type}")
        
        # Learning recommendations
        if analysis.learning_recommendations:
            report.append("\n=== LEARNING RECOMMENDATIONS ===")
            for i, rec in enumerate(analysis.learning_recommendations, 1):
                report.append(f"{i}. {rec}")
        
        # Positive reinforcement
        report.append("\n=== STRENGTHS & ENCOURAGEMENT ===")
        if analysis.originality_score >= 0.8:
            report.append("• Excellent original thinking and personal insights")
        elif analysis.originality_score >= 0.6:
            report.append("• Good level of original content and analysis")
        
        if analysis.citation_quality_score >= 0.7:
            report.append("• Strong citation practices and source attribution")
        elif analysis.citation_quality_score >= 0.4:
            report.append("• Good effort in citing sources")
        
        if analysis.academic_writing_score >= 0.7:
            report.append("• Well-structured academic writing")
        
        report.append("\nRemember: The goal is continuous learning and improvement in academic integrity!")
        
        return "\n".join(report)

    async def get_student_integrity_profile(self, student_id: str) -> Optional[AcademicIntegrityProfile]:
        """Get comprehensive academic integrity profile for student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, total_submissions, average_originality, citation_improvement_trend,
                   integrity_violations, learning_progress, last_updated
            FROM academic_integrity_profiles
            WHERE student_id = ?
        ''', (student_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return AcademicIntegrityProfile(
            student_id=row[0],
            total_submissions=row[1],
            average_originality=row[2],
            citation_improvement_trend=row[3],
            integrity_violations=json.loads(row[4]) if row[4] else [],
            learning_progress=json.loads(row[5]) if row[5] else {},
            last_updated=datetime.fromisoformat(row[6])
        )

    async def _store_submission(self, submission_id: str, student_id: str, assignment_id: str, text: str):
        """Store submission in database"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO submissions
            (submission_id, student_id, assignment_id, submission_text, submission_hash, submission_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (submission_id, student_id, assignment_id, text, text_hash, datetime.now()))
        
        conn.commit()
        conn.close()

    async def _get_previous_submissions(self, current_submission_id: str) -> List[Dict[str, Any]]:
        """Get previous submissions for self-plagiarism check"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT submission_id, submission_text, submission_date
            FROM submissions
            WHERE submission_id != ?
            ORDER BY submission_date DESC
            LIMIT 50
        ''', (current_submission_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"id": row[0], "text": row[1], "date": row[2]}
            for row in rows
        ]

    async def _save_similarity_match(self, match: SimilarityMatch):
        """Save similarity match to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO similarity_matches
            (match_id, student_submission_id, source_text, matched_text, similarity_score,
             similarity_type, severity_level, start_position, end_position,
             source_info, context_before, context_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (match.match_id, match.student_submission_id, match.source_text,
              match.matched_text, match.similarity_score, match.similarity_type.value,
              match.severity_level.value, match.start_position, match.end_position,
              json.dumps(match.source_info), match.context_before, match.context_after))
        
        conn.commit()
        conn.close()

    async def _save_analysis(self, analysis: SubmissionAnalysis):
        """Save submission analysis to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO submission_analyses
            (submission_id, student_id, assignment_id, total_similarity_score,
             originality_score, citation_quality_score, academic_writing_score,
             learning_recommendations, analysis_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (analysis.submission_id, analysis.student_id, analysis.assignment_id,
              analysis.total_similarity_score, analysis.originality_score,
              analysis.citation_quality_score, analysis.academic_writing_score,
              json.dumps(analysis.learning_recommendations), analysis.analysis_timestamp))
        
        conn.commit()
        conn.close()

    async def _save_learning_recommendation(self, recommendation: LearningRecommendation):
        """Save learning recommendation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO learning_recommendations
            (recommendation_id, student_id, action_type, priority, description,
             resources, expected_outcome, completion_status, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (recommendation.recommendation_id, recommendation.student_id,
              recommendation.action_type.value, recommendation.priority,
              recommendation.description, json.dumps(recommendation.resources),
              recommendation.expected_outcome, recommendation.completion_status,
              datetime.now()))
        
        conn.commit()
        conn.close()

    async def _update_integrity_profile(self, student_id: str, analysis: SubmissionAnalysis):
        """Update student's academic integrity profile"""
        profile = await self.get_student_integrity_profile(student_id)
        
        if not profile:
            profile = AcademicIntegrityProfile(student_id=student_id)
        
        # Update statistics
        profile.total_submissions += 1
        profile.average_originality = (
            (profile.average_originality * (profile.total_submissions - 1) + analysis.originality_score) /
            profile.total_submissions
        )
        
        # Track violations
        if analysis.total_similarity_score > 0.7:
            violation = {
                "submission_id": analysis.submission_id,
                "date": analysis.analysis_timestamp.isoformat(),
                "similarity_score": analysis.total_similarity_score,
                "severity": "high" if analysis.total_similarity_score > 0.8 else "medium"
            }
            profile.integrity_violations.append(violation)
        
        profile.last_updated = datetime.now()
        
        # Save updated profile
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO academic_integrity_profiles
            (student_id, total_submissions, average_originality, citation_improvement_trend,
             integrity_violations, learning_progress, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (profile.student_id, profile.total_submissions, profile.average_originality,
              profile.citation_improvement_trend, json.dumps(profile.integrity_violations),
              json.dumps(profile.learning_progress), profile.last_updated))
        
        conn.commit()
        conn.close()

async def demo_plagiarism_detection():
    """Demonstrate learning-focused plagiarism detection"""
    detector = LearningFocusedPlagiarismDetector()
    
    print("=== Learning-Focused Plagiarism Detection Demo ===")
    
    # Sample student submission with various issues
    student_submission = """
    Climate change is one of the most pressing issues of our time. According to Smith (2023), 
    global temperatures have risen significantly over the past century. The greenhouse effect 
    is a natural process that warms the Earth's surface. When the Sun's energy reaches the 
    Earth's atmosphere, some of it is reflected back to space and the rest is absorbed and 
    re-radiated by greenhouse gases.
    
    Many scientists agree that human activities are the primary cause of climate change since 
    the mid-20th century. The burning of fossil fuels releases greenhouse gases into the 
    atmosphere, which trap heat and cause global warming. This is a major problem that requires 
    immediate attention.
    
    In conclusion, climate change is a serious issue that affects everyone. We must take action 
    to reduce our carbon footprint and protect the environment for future generations.
    """
    
    # Sample reference corpus
    reference_corpus = [
        "The greenhouse effect is a natural process that warms the Earth's surface. When the Sun's energy reaches the Earth's atmosphere, some of it is reflected back to space and the rest is absorbed and re-radiated by greenhouse gases.",
        "Human activities are the primary driver of climate change since the mid-20th century, mainly due to the burning of fossil fuels which increases heat-trapping greenhouse gases in Earth's atmosphere.",
        "Climate change represents one of the most significant environmental challenges of the 21st century, requiring urgent global action to mitigate its effects."
    ]
    
    # Analyze submission
    analysis = await detector.analyze_submission(
        submission_id="sub_001",
        student_id="student_jenny",
        assignment_id="climate_essay",
        submission_text=student_submission,
        comparison_corpus=reference_corpus
    )
    
    print(f"\nAnalysis Results:")
    print(f"Originality Score: {analysis.originality_score:.1%}")
    print(f"Citation Quality: {analysis.citation_quality_score:.1%}")
    print(f"Academic Writing Score: {analysis.academic_writing_score:.1%}")
    print(f"Total Similarity: {analysis.total_similarity_score:.1%}")
    print(f"Matches Found: {len(analysis.unique_matches)}")
    
    # Show similarity matches
    if analysis.unique_matches:
        print(f"\nSimilarity Matches:")
        for i, match in enumerate(analysis.unique_matches, 1):
            print(f"{i}. {match.similarity_type.value} - {match.severity_level.value}")
            print(f"   Similarity: {match.similarity_score:.1%}")
            print(f"   Text: \"{match.matched_text[:80]}...\"")
    
    # Generate feedback report
    feedback_report = detector.generate_feedback_report(analysis)
    print(f"\n{feedback_report}")
    
    # Show learning recommendations
    print(f"\nLearning Recommendations:")
    for rec in analysis.learning_recommendations:
        print(f"• {rec}")

if __name__ == "__main__":
    asyncio.run(demo_plagiarism_detection())