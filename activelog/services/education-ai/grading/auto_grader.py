"""
Assignment Auto-Grading System with Detailed Feedback

Advanced AI-powered system for automatically grading various types of assignments
including multiple choice, short answer, essays, math problems, and coding assignments.
Provides detailed feedback, rubric-based scoring, and learning-focused suggestions.
"""

import asyncio
import sqlite3
import json
import re
import difflib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from enum import Enum
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssignmentType(Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    MATH_PROBLEM = "math_problem"
    CODING = "coding"
    FILL_IN_BLANK = "fill_in_blank"
    MATCHING = "matching"
    TRUE_FALSE = "true_false"

class FeedbackType(Enum):
    CORRECTNESS = "correctness"
    IMPROVEMENT = "improvement"
    ENCOURAGEMENT = "encouragement"
    CONCEPT_EXPLANATION = "concept_explanation"
    EXTENSION = "extension"

class RubricCriterion(Enum):
    CONTENT_ACCURACY = "content_accuracy"
    ORGANIZATION = "organization"
    CLARITY = "clarity"
    CREATIVITY = "creativity"
    MECHANICS = "mechanics"
    CRITICAL_THINKING = "critical_thinking"
    USE_OF_EVIDENCE = "use_of_evidence"

@dataclass
class Question:
    question_id: str
    question_text: str
    question_type: AssignmentType
    correct_answer: Union[str, List[str], Dict[str, Any]]
    points: float
    acceptable_answers: List[str] = field(default_factory=list)
    partial_credit_rules: Dict[str, float] = field(default_factory=dict)
    feedback_templates: Dict[str, str] = field(default_factory=dict)
    concept_tags: List[str] = field(default_factory=list)
    difficulty_level: int = 1

@dataclass
class StudentAnswer:
    question_id: str
    student_answer: Union[str, List[str], Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)
    attempt_number: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GradingResult:
    question_id: str
    student_id: str
    points_earned: float
    points_possible: float
    is_correct: bool
    correctness_percentage: float
    feedback: List[str] = field(default_factory=list)
    concept_feedback: Dict[str, str] = field(default_factory=dict)
    rubric_scores: Dict[str, float] = field(default_factory=dict)
    improvement_suggestions: List[str] = field(default_factory=list)
    grading_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Assignment:
    assignment_id: str
    title: str
    description: str
    assignment_type: AssignmentType
    questions: List[Question] = field(default_factory=list)
    total_points: float = 0.0
    rubric: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    due_date: Optional[datetime] = None
    instructions: str = ""
    learning_objectives: List[str] = field(default_factory=list)

@dataclass
class Submission:
    submission_id: str
    assignment_id: str
    student_id: str
    answers: List[StudentAnswer] = field(default_factory=list)
    submission_timestamp: datetime = field(default_factory=datetime.now)
    is_late: bool = False
    attempt_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AssignmentGrade:
    grade_id: str
    assignment_id: str
    student_id: str
    submission_id: str
    total_points_earned: float
    total_points_possible: float
    percentage_score: float
    letter_grade: str
    question_results: List[GradingResult] = field(default_factory=list)
    overall_feedback: str = ""
    strengths: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    graded_timestamp: datetime = field(default_factory=datetime.now)

class AutoGrader:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.grade_scale = {
            97: 'A+', 93: 'A', 90: 'A-',
            87: 'B+', 83: 'B', 80: 'B-',
            77: 'C+', 73: 'C', 70: 'C-',
            67: 'D+', 63: 'D', 60: 'D-',
            0: 'F'
        }
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for auto-grading system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                assignment_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                assignment_type TEXT,
                questions TEXT,
                total_points REAL,
                rubric TEXT,
                due_date TIMESTAMP,
                instructions TEXT,
                learning_objectives TEXT,
                created_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                assignment_id TEXT,
                student_id TEXT,
                answers TEXT,
                submission_timestamp TIMESTAMP,
                is_late BOOLEAN,
                attempt_count INTEGER,
                metadata TEXT,
                FOREIGN KEY (assignment_id) REFERENCES assignments (assignment_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignment_grades (
                grade_id TEXT PRIMARY KEY,
                assignment_id TEXT,
                student_id TEXT,
                submission_id TEXT,
                total_points_earned REAL,
                total_points_possible REAL,
                percentage_score REAL,
                letter_grade TEXT,
                question_results TEXT,
                overall_feedback TEXT,
                strengths TEXT,
                areas_for_improvement TEXT,
                next_steps TEXT,
                graded_timestamp TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES assignments (assignment_id),
                FOREIGN KEY (submission_id) REFERENCES submissions (submission_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grading_analytics (
                analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id TEXT,
                total_submissions INTEGER,
                average_score REAL,
                median_score REAL,
                score_distribution TEXT,
                common_mistakes TEXT,
                concept_mastery TEXT,
                grading_efficiency TEXT,
                analysis_date TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES assignments (assignment_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Auto-grading system database initialized")

    async def create_assignment(self, assignment_id: str, title: str, description: str,
                              assignment_type: AssignmentType, questions: List[Question],
                              due_date: Optional[datetime] = None,
                              learning_objectives: List[str] = None) -> Assignment:
        """
        Create a new assignment with questions and grading criteria
        
        Args:
            assignment_id: Unique assignment identifier
            title: Assignment title
            description: Assignment description
            assignment_type: Type of assignment
            questions: List of questions
            due_date: Assignment due date
            learning_objectives: Learning objectives
            
        Returns:
            Created assignment
        """
        total_points = sum(q.points for q in questions)
        
        # Generate rubric based on assignment type
        rubric = self._generate_default_rubric(assignment_type)
        
        assignment = Assignment(
            assignment_id=assignment_id,
            title=title,
            description=description,
            assignment_type=assignment_type,
            questions=questions,
            total_points=total_points,
            rubric=rubric,
            due_date=due_date,
            learning_objectives=learning_objectives or []
        )
        
        await self._save_assignment(assignment)
        logger.info(f"Created assignment {title} with {len(questions)} questions ({total_points} points)")
        return assignment

    async def grade_submission(self, submission: Submission) -> AssignmentGrade:
        """
        Automatically grade a student submission
        
        Args:
            submission: Student submission to grade
            
        Returns:
            Comprehensive assignment grade with feedback
        """
        assignment = await self.get_assignment(submission.assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {submission.assignment_id} not found")
        
        # Grade each question
        question_results = []
        for i, answer in enumerate(submission.answers):
            if i < len(assignment.questions):
                question = assignment.questions[i]
                result = await self._grade_question(question, answer, submission.student_id)
                question_results.append(result)
        
        # Calculate overall grade
        total_earned = sum(result.points_earned for result in question_results)
        total_possible = assignment.total_points
        percentage = (total_earned / total_possible * 100) if total_possible > 0 else 0
        letter_grade = self._calculate_letter_grade(percentage)
        
        # Generate comprehensive feedback
        overall_feedback = await self._generate_overall_feedback(question_results, assignment)
        strengths = await self._identify_strengths(question_results, assignment)
        improvements = await self._identify_improvements(question_results, assignment)
        next_steps = await self._generate_next_steps(question_results, assignment)
        
        grade_id = f"grade_{submission.assignment_id}_{submission.student_id}_{int(datetime.now().timestamp())}"
        
        grade = AssignmentGrade(
            grade_id=grade_id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            submission_id=submission.submission_id,
            total_points_earned=total_earned,
            total_points_possible=total_possible,
            percentage_score=percentage,
            letter_grade=letter_grade,
            question_results=question_results,
            overall_feedback=overall_feedback,
            strengths=strengths,
            areas_for_improvement=improvements,
            next_steps=next_steps
        )
        
        await self._save_grade(grade)
        await self._save_submission(submission)
        
        logger.info(f"Graded submission for student {submission.student_id}: {percentage:.1f}% ({letter_grade})")
        return grade

    async def _grade_question(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Grade individual question based on type"""
        if question.question_type == AssignmentType.MULTIPLE_CHOICE:
            return await self._grade_multiple_choice(question, answer, student_id)
        elif question.question_type == AssignmentType.SHORT_ANSWER:
            return await self._grade_short_answer(question, answer, student_id)
        elif question.question_type == AssignmentType.ESSAY:
            return await self._grade_essay(question, answer, student_id)
        elif question.question_type == AssignmentType.MATH_PROBLEM:
            return await self._grade_math_problem(question, answer, student_id)
        elif question.question_type == AssignmentType.TRUE_FALSE:
            return await self._grade_true_false(question, answer, student_id)
        elif question.question_type == AssignmentType.FILL_IN_BLANK:
            return await self._grade_fill_in_blank(question, answer, student_id)
        else:
            return await self._grade_generic(question, answer, student_id)

    async def _grade_multiple_choice(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Grade multiple choice question"""
        student_answer = str(answer.student_answer).strip().upper()
        correct_answer = str(question.correct_answer).strip().upper()
        
        is_correct = student_answer == correct_answer
        points_earned = question.points if is_correct else 0
        correctness = 100.0 if is_correct else 0.0
        
        feedback = []
        if is_correct:
            feedback.append("Correct! Well done.")
        else:
            feedback.append(f"Incorrect. The correct answer is {question.correct_answer}.")
            
            # Add concept explanation if available
            if question.concept_tags:
                concept = question.concept_tags[0]
                feedback.append(f"This question tests understanding of {concept}.")
        
        return GradingResult(
            question_id=question.question_id,
            student_id=student_id,
            points_earned=points_earned,
            points_possible=question.points,
            is_correct=is_correct,
            correctness_percentage=correctness,
            feedback=feedback
        )

    async def _grade_short_answer(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Grade short answer question with fuzzy matching"""
        student_answer = str(answer.student_answer).strip().lower()
        correct_answer = str(question.correct_answer).strip().lower()
        
        # Check for exact match first
        if student_answer == correct_answer:
            return GradingResult(
                question_id=question.question_id,
                student_id=student_id,
                points_earned=question.points,
                points_possible=question.points,
                is_correct=True,
                correctness_percentage=100.0,
                feedback=["Excellent! Your answer is completely correct."]
            )
        
        # Check acceptable alternatives
        for acceptable in question.acceptable_answers:
            if student_answer == acceptable.strip().lower():
                return GradingResult(
                    question_id=question.question_id,
                    student_id=student_id,
                    points_earned=question.points,
                    points_possible=question.points,
                    is_correct=True,
                    correctness_percentage=100.0,
                    feedback=["Correct! This is an acceptable alternative answer."]
                )
        
        # Fuzzy matching for partial credit
        similarity = difflib.SequenceMatcher(None, student_answer, correct_answer).ratio()
        
        if similarity >= 0.8:
            points_earned = question.points * 0.9
            correctness = 90.0
            feedback = ["Very close! Minor differences from the expected answer.", f"Expected: {question.correct_answer}"]
        elif similarity >= 0.6:
            points_earned = question.points * 0.7
            correctness = 70.0
            feedback = ["Partially correct but needs improvement.", f"Expected: {question.correct_answer}"]
        elif similarity >= 0.4:
            points_earned = question.points * 0.5
            correctness = 50.0
            feedback = ["Some correct elements but significant issues.", f"Expected: {question.correct_answer}"]
        else:
            points_earned = 0
            correctness = 0.0
            feedback = ["Incorrect answer.", f"Expected: {question.correct_answer}"]
        
        # Add improvement suggestions
        improvements = []
        if similarity < 0.8:
            improvements.append("Review the key concepts related to this topic")
            if question.concept_tags:
                improvements.append(f"Focus on understanding {', '.join(question.concept_tags)}")
        
        return GradingResult(
            question_id=question.question_id,
            student_id=student_id,
            points_earned=points_earned,
            points_possible=question.points,
            is_correct=similarity >= 0.8,
            correctness_percentage=correctness,
            feedback=feedback,
            improvement_suggestions=improvements
        )

    async def _grade_essay(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Grade essay question using rubric-based assessment"""
        student_essay = str(answer.student_answer).strip()
        
        if not student_essay:
            return GradingResult(
                question_id=question.question_id,
                student_id=student_id,
                points_earned=0,
                points_possible=question.points,
                is_correct=False,
                correctness_percentage=0.0,
                feedback=["No response provided."],
                improvement_suggestions=["Please provide a complete response to the essay question."]
            )
        
        # Analyze essay components
        word_count = len(student_essay.split())
        sentence_count = len([s for s in student_essay.split('.') if s.strip()])
        paragraph_count = len([p for p in student_essay.split('\n\n') if p.strip()])
        
        # Rubric-based scoring
        rubric_scores = {}
        
        # Content accuracy (40% of score)
        content_score = await self._assess_essay_content(student_essay, question)
        rubric_scores[RubricCriterion.CONTENT_ACCURACY.value] = content_score
        
        # Organization (20% of score)
        organization_score = self._assess_essay_organization(student_essay, paragraph_count)
        rubric_scores[RubricCriterion.ORGANIZATION.value] = organization_score
        
        # Clarity (20% of score)
        clarity_score = self._assess_essay_clarity(student_essay, word_count, sentence_count)
        rubric_scores[RubricCriterion.CLARITY.value] = clarity_score
        
        # Mechanics (20% of score)
        mechanics_score = self._assess_essay_mechanics(student_essay)
        rubric_scores[RubricCriterion.MECHANICS.value] = mechanics_score
        
        # Calculate overall score
        overall_score = (content_score * 0.4 + organization_score * 0.2 + 
                        clarity_score * 0.2 + mechanics_score * 0.2)
        
        points_earned = question.points * overall_score
        correctness = overall_score * 100
        
        # Generate detailed feedback
        feedback = []
        if overall_score >= 0.9:
            feedback.append("Excellent essay! Strong understanding demonstrated.")
        elif overall_score >= 0.8:
            feedback.append("Good essay with solid understanding.")
        elif overall_score >= 0.7:
            feedback.append("Satisfactory essay but room for improvement.")
        else:
            feedback.append("Essay needs significant improvement.")
        
        feedback.append(f"Word count: {word_count} words")
        feedback.append(f"Content accuracy: {content_score:.1%}")
        feedback.append(f"Organization: {organization_score:.1%}")
        feedback.append(f"Clarity: {clarity_score:.1%}")
        feedback.append(f"Mechanics: {mechanics_score:.1%}")
        
        # Generate improvement suggestions
        improvements = []
        if content_score < 0.8:
            improvements.append("Focus on addressing all parts of the question thoroughly")
        if organization_score < 0.8:
            improvements.append("Improve essay structure with clear introduction, body, and conclusion")
        if clarity_score < 0.8:
            improvements.append("Work on sentence variety and clear expression of ideas")
        if mechanics_score < 0.8:
            improvements.append("Proofread for grammar, spelling, and punctuation errors")
        
        return GradingResult(
            question_id=question.question_id,
            student_id=student_id,
            points_earned=points_earned,
            points_possible=question.points,
            is_correct=overall_score >= 0.7,
            correctness_percentage=correctness,
            feedback=feedback,
            rubric_scores=rubric_scores,
            improvement_suggestions=improvements
        )

    async def _grade_math_problem(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Grade math problem with step-by-step analysis"""
        student_answer = str(answer.student_answer).strip()
        
        # Extract final numerical answer
        final_answer = self._extract_numerical_answer(student_answer)
        correct_answer = self._extract_numerical_answer(str(question.correct_answer))
        
        is_correct = abs(final_answer - correct_answer) < 0.001 if final_answer is not None and correct_answer is not None else False
        
        # Check for partial credit based on work shown
        partial_credit = 0.0
        if not is_correct and student_answer:
            partial_credit = await self._assess_math_work(student_answer, question)
        
        points_earned = question.points if is_correct else question.points * partial_credit
        correctness = 100.0 if is_correct else partial_credit * 100
        
        feedback = []
        if is_correct:
            feedback.append("Correct answer! Well done.")
            if len(student_answer) > 10:  # Work was shown
                feedback.append("Good work showing your steps.")
        else:
            feedback.append(f"Incorrect. The correct answer is {question.correct_answer}")
            if partial_credit > 0:
                feedback.append(f"Partial credit awarded for correct methodology ({partial_credit:.0%})")
            else:
                feedback.append("Please show your work for partial credit consideration.")
        
        improvements = []
        if not is_correct:
            improvements.append("Double-check your calculations")
            improvements.append("Show all work steps clearly")
            if question.concept_tags:
                improvements.append(f"Review concepts: {', '.join(question.concept_tags)}")
        
        return GradingResult(
            question_id=question.question_id,
            student_id=student_id,
            points_earned=points_earned,
            points_possible=question.points,
            is_correct=is_correct,
            correctness_percentage=correctness,
            feedback=feedback,
            improvement_suggestions=improvements
        )

    async def _grade_true_false(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Grade true/false question"""
        student_answer = str(answer.student_answer).strip().lower()
        correct_answer = str(question.correct_answer).strip().lower()
        
        # Normalize answers
        true_variants = ['true', 't', 'yes', '1', 'correct']
        false_variants = ['false', 'f', 'no', '0', 'incorrect']
        
        if student_answer in true_variants:
            student_answer = 'true'
        elif student_answer in false_variants:
            student_answer = 'false'
        
        if correct_answer in true_variants:
            correct_answer = 'true'
        elif correct_answer in false_variants:
            correct_answer = 'false'
        
        is_correct = student_answer == correct_answer
        points_earned = question.points if is_correct else 0
        correctness = 100.0 if is_correct else 0.0
        
        feedback = []
        if is_correct:
            feedback.append("Correct!")
        else:
            feedback.append(f"Incorrect. The correct answer is {question.correct_answer}")
        
        return GradingResult(
            question_id=question.question_id,
            student_id=student_id,
            points_earned=points_earned,
            points_possible=question.points,
            is_correct=is_correct,
            correctness_percentage=correctness,
            feedback=feedback
        )

    async def _grade_fill_in_blank(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Grade fill-in-the-blank question"""
        if isinstance(answer.student_answer, list) and isinstance(question.correct_answer, list):
            # Multiple blanks
            correct_count = 0
            total_blanks = len(question.correct_answer)
            
            for i, (student_ans, correct_ans) in enumerate(zip(answer.student_answer, question.correct_answer)):
                student_ans = str(student_ans).strip().lower()
                correct_ans = str(correct_ans).strip().lower()
                
                if student_ans == correct_ans:
                    correct_count += 1
            
            correctness = (correct_count / total_blanks * 100) if total_blanks > 0 else 0
            points_earned = question.points * (correct_count / total_blanks)
            
            feedback = [f"Got {correct_count} out of {total_blanks} blanks correct"]
            
        else:
            # Single blank
            student_answer = str(answer.student_answer).strip().lower()
            correct_answer = str(question.correct_answer).strip().lower()
            
            is_correct = student_answer == correct_answer
            correctness = 100.0 if is_correct else 0.0
            points_earned = question.points if is_correct else 0
            
            feedback = ["Correct!" if is_correct else f"Incorrect. Expected: {question.correct_answer}"]
        
        return GradingResult(
            question_id=question.question_id,
            student_id=student_id,
            points_earned=points_earned,
            points_possible=question.points,
            is_correct=correctness >= 100,
            correctness_percentage=correctness,
            feedback=feedback
        )

    async def _grade_generic(self, question: Question, answer: StudentAnswer, student_id: str) -> GradingResult:
        """Generic grading for unsupported question types"""
        return GradingResult(
            question_id=question.question_id,
            student_id=student_id,
            points_earned=0,
            points_possible=question.points,
            is_correct=False,
            correctness_percentage=0.0,
            feedback=["Manual grading required for this question type"],
            improvement_suggestions=["Please see instructor for feedback"]
        )

    async def _assess_essay_content(self, essay: str, question: Question) -> float:
        """Assess content accuracy of essay"""
        essay_lower = essay.lower()
        
        # Check for key concepts
        concept_score = 0.0
        if question.concept_tags:
            concepts_found = sum(1 for concept in question.concept_tags 
                               if concept.lower() in essay_lower)
            concept_score = concepts_found / len(question.concept_tags)
        
        # Basic content indicators
        length_score = min(1.0, len(essay.split()) / 200)  # Assume 200 words minimum
        
        # Combine scores
        return (concept_score * 0.7 + length_score * 0.3)

    def _assess_essay_organization(self, essay: str, paragraph_count: int) -> float:
        """Assess essay organization"""
        if paragraph_count >= 3:  # Introduction, body, conclusion
            return 1.0
        elif paragraph_count == 2:
            return 0.7
        elif paragraph_count == 1:
            return 0.4
        else:
            return 0.0

    def _assess_essay_clarity(self, essay: str, word_count: int, sentence_count: int) -> float:
        """Assess essay clarity"""
        if sentence_count == 0:
            return 0.0
        
        avg_sentence_length = word_count / sentence_count
        
        # Optimal sentence length is 15-20 words
        if 15 <= avg_sentence_length <= 20:
            return 1.0
        elif 10 <= avg_sentence_length <= 25:
            return 0.8
        elif 8 <= avg_sentence_length <= 30:
            return 0.6
        else:
            return 0.4

    def _assess_essay_mechanics(self, essay: str) -> float:
        """Basic assessment of grammar and mechanics"""
        # Simple heuristics for mechanics
        punctuation_score = 1.0 if essay.count('.') + essay.count('!') + essay.count('?') > 0 else 0.5
        capitalization_score = 1.0 if essay[0].isupper() if essay else 0.0
        
        # Check for basic sentence structure
        sentences = [s.strip() for s in essay.split('.') if s.strip()]
        structure_score = sum(1 for s in sentences if len(s.split()) >= 4) / len(sentences) if sentences else 0
        
        return (punctuation_score * 0.3 + capitalization_score * 0.3 + structure_score * 0.4)

    def _extract_numerical_answer(self, text: str) -> Optional[float]:
        """Extract numerical answer from text"""
        if not text:
            return None
        
        # Look for numbers in the text
        numbers = re.findall(r'-?\d+\.?\d*', text)
        if numbers:
            try:
                # Return the last number found (usually the final answer)
                return float(numbers[-1])
            except ValueError:
                pass
        
        return None

    async def _assess_math_work(self, work: str, question: Question) -> float:
        """Assess mathematical work for partial credit"""
        if not work or len(work.strip()) < 10:
            return 0.0
        
        partial_credit = 0.0
        
        # Check for mathematical symbols/operations
        math_symbols = ['+', '-', '*', '/', '=', '(', ')', '^', '√']
        symbol_count = sum(1 for symbol in math_symbols if symbol in work)
        if symbol_count > 0:
            partial_credit += 0.2
        
        # Check for step-by-step work
        lines = [line.strip() for line in work.split('\n') if line.strip()]
        if len(lines) > 2:
            partial_credit += 0.3
        
        # Check for correct methodology keywords
        if question.concept_tags:
            for concept in question.concept_tags:
                if concept.lower() in work.lower():
                    partial_credit += 0.2
                    break
        
        # Check for equation setup
        if '=' in work:
            partial_credit += 0.3
        
        return min(partial_credit, 0.8)  # Cap at 80% for work without correct answer

    def _calculate_letter_grade(self, percentage: float) -> str:
        """Convert percentage to letter grade"""
        for threshold, grade in sorted(self.grade_scale.items(), reverse=True):
            if percentage >= threshold:
                return grade
        return 'F'

    def _generate_default_rubric(self, assignment_type: AssignmentType) -> Dict[str, Dict[str, Any]]:
        """Generate default rubric based on assignment type"""
        if assignment_type == AssignmentType.ESSAY:
            return {
                RubricCriterion.CONTENT_ACCURACY.value: {"weight": 40, "description": "Accuracy and completeness of content"},
                RubricCriterion.ORGANIZATION.value: {"weight": 20, "description": "Clear structure and logical flow"},
                RubricCriterion.CLARITY.value: {"weight": 20, "description": "Clear expression of ideas"},
                RubricCriterion.MECHANICS.value: {"weight": 20, "description": "Grammar, spelling, and punctuation"}
            }
        elif assignment_type == AssignmentType.MATH_PROBLEM:
            return {
                RubricCriterion.CONTENT_ACCURACY.value: {"weight": 60, "description": "Correct answer"},
                "methodology": {"weight": 30, "description": "Correct problem-solving approach"},
                "work_shown": {"weight": 10, "description": "Clear presentation of work"}
            }
        else:
            return {
                RubricCriterion.CONTENT_ACCURACY.value: {"weight": 100, "description": "Correctness of response"}
            }

    async def _generate_overall_feedback(self, results: List[GradingResult], assignment: Assignment) -> str:
        """Generate overall feedback for the assignment"""
        total_questions = len(results)
        correct_questions = sum(1 for r in results if r.is_correct)
        avg_score = np.mean([r.correctness_percentage for r in results])
        
        if avg_score >= 90:
            feedback = f"Excellent work! You answered {correct_questions} out of {total_questions} questions correctly."
        elif avg_score >= 80:
            feedback = f"Good job! You answered {correct_questions} out of {total_questions} questions correctly."
        elif avg_score >= 70:
            feedback = f"Satisfactory performance. You answered {correct_questions} out of {total_questions} questions correctly."
        else:
            feedback = f"This assignment needs improvement. You answered {correct_questions} out of {total_questions} questions correctly."
        
        if assignment.learning_objectives:
            feedback += f" This assignment assessed your understanding of: {', '.join(assignment.learning_objectives)}."
        
        return feedback

    async def _identify_strengths(self, results: List[GradingResult], assignment: Assignment) -> List[str]:
        """Identify student strengths based on performance"""
        strengths = []
        
        # High performing questions
        strong_areas = [r for r in results if r.correctness_percentage >= 85]
        if len(strong_areas) >= len(results) * 0.7:
            strengths.append("Demonstrates strong overall understanding of the material")
        
        # Concept-based strengths
        concept_scores = {}
        for result in results:
            question = next((q for q in assignment.questions if q.question_id == result.question_id), None)
            if question and question.concept_tags:
                for concept in question.concept_tags:
                    if concept not in concept_scores:
                        concept_scores[concept] = []
                    concept_scores[concept].append(result.correctness_percentage)
        
        for concept, scores in concept_scores.items():
            if np.mean(scores) >= 80:
                strengths.append(f"Strong grasp of {concept}")
        
        if not strengths:
            strengths.append("Shows effort and engagement with the material")
        
        return strengths

    async def _identify_improvements(self, results: List[GradingResult], assignment: Assignment) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        # Low performing questions
        weak_areas = [r for r in results if r.correctness_percentage < 70]
        if len(weak_areas) >= len(results) * 0.3:
            improvements.append("Review fundamental concepts covered in this assignment")
        
        # Concept-based improvements
        concept_scores = {}
        for result in results:
            question = next((q for q in assignment.questions if q.question_id == result.question_id), None)
            if question and question.concept_tags:
                for concept in question.concept_tags:
                    if concept not in concept_scores:
                        concept_scores[concept] = []
                    concept_scores[concept].append(result.correctness_percentage)
        
        for concept, scores in concept_scores.items():
            if np.mean(scores) < 70:
                improvements.append(f"Focus on improving understanding of {concept}")
        
        # Collect specific improvement suggestions
        for result in results:
            improvements.extend(result.improvement_suggestions)
        
        # Remove duplicates and limit
        unique_improvements = list(dict.fromkeys(improvements))
        return unique_improvements[:5]  # Top 5 improvements

    async def _generate_next_steps(self, results: List[GradingResult], assignment: Assignment) -> List[str]:
        """Generate recommended next steps"""
        avg_score = np.mean([r.correctness_percentage for r in results])
        next_steps = []
        
        if avg_score < 60:
            next_steps.extend([
                "Schedule a meeting with the instructor for additional support",
                "Review class notes and textbook materials",
                "Form a study group with classmates"
            ])
        elif avg_score < 80:
            next_steps.extend([
                "Review incorrect answers and seek clarification",
                "Practice similar problems for reinforcement"
            ])
        else:
            next_steps.extend([
                "Continue the excellent work!",
                "Consider helping classmates who are struggling"
            ])
        
        if assignment.learning_objectives:
            next_steps.append(f"Prepare for upcoming assessments on {assignment.learning_objectives[0]}")
        
        return next_steps

    async def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Get assignment by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT assignment_id, title, description, assignment_type, questions,
                   total_points, rubric, due_date, instructions, learning_objectives
            FROM assignments
            WHERE assignment_id = ?
        ''', (assignment_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Deserialize questions
        questions_data = json.loads(row[4]) if row[4] else []
        questions = []
        for q_data in questions_data:
            question = Question(
                question_id=q_data['question_id'],
                question_text=q_data['question_text'],
                question_type=AssignmentType(q_data['question_type']),
                correct_answer=q_data['correct_answer'],
                points=q_data['points'],
                acceptable_answers=q_data.get('acceptable_answers', []),
                partial_credit_rules=q_data.get('partial_credit_rules', {}),
                concept_tags=q_data.get('concept_tags', []),
                difficulty_level=q_data.get('difficulty_level', 1)
            )
            questions.append(question)
        
        return Assignment(
            assignment_id=row[0],
            title=row[1],
            description=row[2],
            assignment_type=AssignmentType(row[3]),
            questions=questions,
            total_points=row[5],
            rubric=json.loads(row[6]) if row[6] else {},
            due_date=datetime.fromisoformat(row[7]) if row[7] else None,
            instructions=row[8],
            learning_objectives=json.loads(row[9]) if row[9] else []
        )

    async def _save_assignment(self, assignment: Assignment):
        """Save assignment to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        questions_data = []
        for q in assignment.questions:
            q_data = {
                'question_id': q.question_id,
                'question_text': q.question_text,
                'question_type': q.question_type.value,
                'correct_answer': q.correct_answer,
                'points': q.points,
                'acceptable_answers': q.acceptable_answers,
                'partial_credit_rules': q.partial_credit_rules,
                'concept_tags': q.concept_tags,
                'difficulty_level': q.difficulty_level
            }
            questions_data.append(q_data)
        
        cursor.execute('''
            INSERT OR REPLACE INTO assignments
            (assignment_id, title, description, assignment_type, questions, total_points,
             rubric, due_date, instructions, learning_objectives, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (assignment.assignment_id, assignment.title, assignment.description,
              assignment.assignment_type.value, json.dumps(questions_data),
              assignment.total_points, json.dumps(assignment.rubric),
              assignment.due_date, assignment.instructions,
              json.dumps(assignment.learning_objectives), datetime.now()))
        
        conn.commit()
        conn.close()

    async def _save_submission(self, submission: Submission):
        """Save submission to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        answers_data = []
        for answer in submission.answers:
            answer_data = {
                'question_id': answer.question_id,
                'student_answer': answer.student_answer,
                'timestamp': answer.timestamp.isoformat(),
                'attempt_number': answer.attempt_number,
                'metadata': answer.metadata
            }
            answers_data.append(answer_data)
        
        cursor.execute('''
            INSERT OR REPLACE INTO submissions
            (submission_id, assignment_id, student_id, answers, submission_timestamp,
             is_late, attempt_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (submission.submission_id, submission.assignment_id, submission.student_id,
              json.dumps(answers_data), submission.submission_timestamp,
              submission.is_late, submission.attempt_count, json.dumps(submission.metadata)))
        
        conn.commit()
        conn.close()

    async def _save_grade(self, grade: AssignmentGrade):
        """Save grade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results_data = []
        for result in grade.question_results:
            result_data = {
                'question_id': result.question_id,
                'student_id': result.student_id,
                'points_earned': result.points_earned,
                'points_possible': result.points_possible,
                'is_correct': result.is_correct,
                'correctness_percentage': result.correctness_percentage,
                'feedback': result.feedback,
                'concept_feedback': result.concept_feedback,
                'rubric_scores': result.rubric_scores,
                'improvement_suggestions': result.improvement_suggestions,
                'grading_timestamp': result.grading_timestamp.isoformat()
            }
            results_data.append(result_data)
        
        cursor.execute('''
            INSERT OR REPLACE INTO assignment_grades
            (grade_id, assignment_id, student_id, submission_id, total_points_earned,
             total_points_possible, percentage_score, letter_grade, question_results,
             overall_feedback, strengths, areas_for_improvement, next_steps,
             graded_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (grade.grade_id, grade.assignment_id, grade.student_id, grade.submission_id,
              grade.total_points_earned, grade.total_points_possible, grade.percentage_score,
              grade.letter_grade, json.dumps(results_data), grade.overall_feedback,
              json.dumps(grade.strengths), json.dumps(grade.areas_for_improvement),
              json.dumps(grade.next_steps), grade.graded_timestamp))
        
        conn.commit()
        conn.close()

async def demo_auto_grading():
    """Demonstrate auto-grading system"""
    grader = AutoGrader()
    
    print("=== Assignment Auto-Grading System Demo ===")
    
    # Create sample questions
    questions = [
        Question(
            question_id="q1",
            question_text="What is the capital of France?",
            question_type=AssignmentType.SHORT_ANSWER,
            correct_answer="Paris",
            points=10,
            acceptable_answers=["paris", "Paris, France"],
            concept_tags=["geography", "european_capitals"]
        ),
        Question(
            question_id="q2",
            question_text="Which of the following is a mammal? A) Fish B) Bird C) Dog D) Reptile",
            question_type=AssignmentType.MULTIPLE_CHOICE,
            correct_answer="C",
            points=5,
            concept_tags=["biology", "animal_classification"]
        ),
        Question(
            question_id="q3",
            question_text="True or False: The Earth revolves around the Sun.",
            question_type=AssignmentType.TRUE_FALSE,
            correct_answer="True",
            points=5,
            concept_tags=["astronomy", "solar_system"]
        ),
        Question(
            question_id="q4",
            question_text="Solve for x: 2x + 5 = 13",
            question_type=AssignmentType.MATH_PROBLEM,
            correct_answer="4",
            points=15,
            concept_tags=["algebra", "linear_equations"]
        )
    ]
    
    # Create assignment
    assignment = await grader.create_assignment(
        assignment_id="assignment_001",
        title="General Knowledge Quiz",
        description="A mixed-format quiz covering various subjects",
        assignment_type=AssignmentType.MULTIPLE_CHOICE,  # Mixed but using one type for demo
        questions=questions,
        learning_objectives=["Basic knowledge application", "Problem-solving skills"]
    )
    
    print(f"Created assignment: {assignment.title}")
    print(f"Total points: {assignment.total_points}")
    print(f"Questions: {len(assignment.questions)}")
    
    # Create student answers
    student_answers = [
        StudentAnswer("q1", "Paris"),  # Correct
        StudentAnswer("q2", "C"),      # Correct
        StudentAnswer("q3", "True"),   # Correct
        StudentAnswer("q4", "2x + 5 = 13\n2x = 13 - 5\n2x = 8\nx = 4")  # Correct with work
    ]
    
    # Create submission
    submission = Submission(
        submission_id="sub_001",
        assignment_id="assignment_001",
        student_id="student_alex",
        answers=student_answers
    )
    
    print(f"\nGrading submission for student {submission.student_id}...")
    
    # Grade the submission
    grade = await grader.grade_submission(submission)
    
    print(f"\n=== GRADING RESULTS ===")
    print(f"Overall Grade: {grade.percentage_score:.1f}% ({grade.letter_grade})")
    print(f"Points: {grade.total_points_earned}/{grade.total_points_possible}")
    print(f"\nOverall Feedback: {grade.overall_feedback}")
    
    print(f"\nStrengths:")
    for strength in grade.strengths:
        print(f"  • {strength}")
    
    print(f"\nAreas for Improvement:")
    for improvement in grade.areas_for_improvement:
        print(f"  • {improvement}")
    
    print(f"\nNext Steps:")
    for step in grade.next_steps:
        print(f"  • {step}")
    
    print(f"\n=== QUESTION-BY-QUESTION RESULTS ===")
    for i, result in enumerate(grade.question_results, 1):
        print(f"\nQuestion {i}: {result.points_earned}/{result.points_possible} points ({result.correctness_percentage:.0f}%)")
        print(f"Correct: {'Yes' if result.is_correct else 'No'}")
        
        if result.feedback:
            print("Feedback:")
            for feedback in result.feedback:
                print(f"  • {feedback}")
        
        if result.improvement_suggestions:
            print("Suggestions:")
            for suggestion in result.improvement_suggestions:
                print(f"  • {suggestion}")

if __name__ == "__main__":
    asyncio.run(demo_auto_grading())