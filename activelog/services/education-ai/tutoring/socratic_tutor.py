"""
Socratic Tutoring System

Advanced AI-powered tutoring system that employs Socratic questioning methods
to guide students toward deeper understanding through dialogue, scaffolded
learning, and metacognitive development.
"""

import asyncio
import sqlite3
import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionType(Enum):
    CLARIFICATION = "clarification"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"
    PERSPECTIVE = "perspective"
    IMPLICATION = "implication"
    META = "meta"
    SCAFFOLDING = "scaffolding"

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class SessionState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

@dataclass
class SocraticQuestion:
    question_id: str
    question_type: QuestionType
    question_text: str
    topic: str
    difficulty: DifficultyLevel
    expected_concepts: List[str] = field(default_factory=list)
    follow_up_hints: List[str] = field(default_factory=list)
    learning_objective: str = ""

@dataclass
class StudentResponse:
    response_id: str
    session_id: str
    question_id: str
    response_text: str
    understanding_level: float = 0.0
    concepts_demonstrated: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    analysis: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TutoringSession:
    session_id: str
    student_id: str
    topic: str
    difficulty_level: DifficultyLevel
    learning_objectives: List[str] = field(default_factory=list)
    current_question_id: Optional[str] = None
    question_sequence: List[str] = field(default_factory=list)
    responses: List[str] = field(default_factory=list)
    understanding_progress: Dict[str, float] = field(default_factory=dict)
    session_state: SessionState = SessionState.ACTIVE
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConceptualFramework:
    concept_id: str
    concept_name: str
    definition: str
    prerequisite_concepts: List[str] = field(default_factory=list)
    key_questions: List[str] = field(default_factory=list)
    common_misconceptions: List[str] = field(default_factory=list)
    scaffolding_steps: List[str] = field(default_factory=list)

class SocraticTutor:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.question_templates = {}
        self.conceptual_frameworks = {}
        self.init_database()
        self._load_question_templates()
        self._load_conceptual_frameworks()
        
    def init_database(self):
        """Initialize database tables for Socratic tutoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutoring_sessions (
                session_id TEXT PRIMARY KEY,
                student_id TEXT,
                topic TEXT,
                difficulty_level TEXT,
                learning_objectives TEXT,
                current_question_id TEXT,
                question_sequence TEXT,
                responses TEXT,
                understanding_progress TEXT,
                session_state TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS socratic_questions (
                question_id TEXT PRIMARY KEY,
                question_type TEXT,
                question_text TEXT,
                topic TEXT,
                difficulty TEXT,
                expected_concepts TEXT,
                follow_up_hints TEXT,
                learning_objective TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_responses (
                response_id TEXT PRIMARY KEY,
                session_id TEXT,
                question_id TEXT,
                response_text TEXT,
                understanding_level REAL,
                concepts_demonstrated TEXT,
                timestamp TIMESTAMP,
                analysis TEXT,
                FOREIGN KEY (session_id) REFERENCES tutoring_sessions (session_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conceptual_frameworks (
                concept_id TEXT PRIMARY KEY,
                concept_name TEXT,
                definition TEXT,
                prerequisite_concepts TEXT,
                key_questions TEXT,
                common_misconceptions TEXT,
                scaffolding_steps TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Socratic tutoring database initialized")

    def _load_question_templates(self):
        """Load question templates for different question types"""
        self.question_templates = {
            QuestionType.CLARIFICATION: [
                "What do you mean when you say '{concept}'?",
                "Can you give me an example of what you just described?",
                "How does this relate to what we discussed earlier?",
                "Could you rephrase that in your own words?",
                "What do you think is the main point here?"
            ],
            QuestionType.ASSUMPTION: [
                "What assumptions are you making here?",
                "What if we assumed the opposite? How would that change things?",
                "Do you think this assumption is always true?",
                "What evidence do we have for this assumption?",
                "How might someone who disagrees with you think about this?"
            ],
            QuestionType.EVIDENCE: [
                "What evidence supports your conclusion?",
                "How do you know this to be true?",
                "What might contradict this evidence?",
                "Is this evidence reliable? Why?",
                "What additional information would help verify this?"
            ],
            QuestionType.PERSPECTIVE: [
                "How might someone from a different background view this?",
                "What are the strengths and weaknesses of this approach?",
                "Are there alternative ways to look at this?",
                "What would the counterargument be?",
                "How does this perspective compare to others we've discussed?"
            ],
            QuestionType.IMPLICATION: [
                "What are the implications of what you're saying?",
                "If this is true, what follows?",
                "How does this affect our original problem?",
                "What might be the consequences of this approach?",
                "Does this lead us to any new questions?"
            ],
            QuestionType.META: [
                "How did you arrive at that conclusion?",
                "What thinking process did you use?",
                "How confident are you in this answer? Why?",
                "What would you do differently next time?",
                "What was the most challenging part of this problem?"
            ],
            QuestionType.SCAFFOLDING: [
                "Let's break this down into smaller parts. What's the first step?",
                "What do we know for certain about this situation?",
                "Can you think of a simpler, similar problem we've solved?",
                "What tools or methods might help us here?",
                "What would happen if we tried a different approach?"
            ]
        }

    def _load_conceptual_frameworks(self):
        """Load conceptual frameworks for different topics"""
        frameworks = [
            ConceptualFramework(
                "quadratic_equations",
                "Quadratic Equations",
                "Equations of the form ax² + bx + c = 0 where a ≠ 0",
                ["algebra_basics", "linear_equations"],
                [
                    "What makes this equation quadratic?",
                    "How many solutions can a quadratic equation have?",
                    "What does the graph of this equation look like?",
                    "How can we find the solutions?"
                ],
                [
                    "Thinking all quadratic equations have two real solutions",
                    "Confusing the coefficient 'a' with the variable",
                    "Forgetting to set the equation equal to zero"
                ],
                [
                    "Identify the standard form",
                    "Determine the coefficients a, b, and c",
                    "Choose appropriate solution method",
                    "Check solutions by substitution"
                ]
            ),
            ConceptualFramework(
                "photosynthesis",
                "Photosynthesis",
                "The process by which plants convert light energy into chemical energy",
                ["cellular_structure", "chemical_reactions"],
                [
                    "What are the inputs and outputs of photosynthesis?",
                    "Where in the plant does photosynthesis occur?",
                    "Why is photosynthesis important for life on Earth?",
                    "How does light intensity affect photosynthesis?"
                ],
                [
                    "Plants breathe in oxygen and out carbon dioxide",
                    "Photosynthesis happens in all plant cells",
                    "Plants only photosynthesize during the day"
                ],
                [
                    "Identify the reactants and products",
                    "Understand the role of chloroplasts",
                    "Distinguish light and dark reactions",
                    "Connect to energy flow in ecosystems"
                ]
            )
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for framework in frameworks:
            cursor.execute('''
                INSERT OR IGNORE INTO conceptual_frameworks
                (concept_id, concept_name, definition, prerequisite_concepts,
                 key_questions, common_misconceptions, scaffolding_steps)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (framework.concept_id, framework.concept_name, framework.definition,
                  json.dumps(framework.prerequisite_concepts),
                  json.dumps(framework.key_questions),
                  json.dumps(framework.common_misconceptions),
                  json.dumps(framework.scaffolding_steps)))
        
        conn.commit()
        conn.close()

    async def start_session(self, student_id: str, topic: str, 
                          difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
                          learning_objectives: List[str] = None) -> TutoringSession:
        """
        Start a new Socratic tutoring session
        
        Args:
            student_id: Student identifier
            topic: Topic to tutor
            difficulty: Difficulty level
            learning_objectives: Specific learning objectives
            
        Returns:
            New tutoring session
        """
        session_id = f"session_{student_id}_{topic}_{int(datetime.now().timestamp())}"
        
        session = TutoringSession(
            session_id=session_id,
            student_id=student_id,
            topic=topic,
            difficulty_level=difficulty,
            learning_objectives=learning_objectives or [],
            understanding_progress={obj: 0.0 for obj in (learning_objectives or [])}
        )
        
        # Generate initial question
        initial_question = await self._generate_opening_question(topic, difficulty)
        if initial_question:
            session.current_question_id = initial_question.question_id
            session.question_sequence = [initial_question.question_id]
            await self._save_question(initial_question)
        
        await self._save_session(session)
        
        logger.info(f"Started Socratic tutoring session {session_id} for student {student_id} on topic {topic}")
        return session

    async def process_response(self, session_id: str, response_text: str) -> Tuple[str, Optional[str]]:
        """
        Process student response and generate next question
        
        Args:
            session_id: Session identifier
            response_text: Student's response
            
        Returns:
            Tuple of (feedback, next_question_text)
        """
        session = await self.get_session(session_id)
        if not session or session.session_state != SessionState.ACTIVE:
            return "Session not found or not active.", None
        
        current_question = await self._get_question(session.current_question_id)
        if not current_question:
            return "Current question not found.", None
        
        # Analyze response
        response = await self._analyze_response(session, current_question, response_text)
        
        # Generate feedback
        feedback = await self._generate_feedback(current_question, response)
        
        # Update understanding progress
        await self._update_understanding_progress(session, response)
        
        # Generate next question
        next_question = await self._generate_next_question(session, current_question, response)
        
        if next_question:
            session.current_question_id = next_question.question_id
            session.question_sequence.append(next_question.question_id)
            session.responses.append(response.response_id)
            await self._save_question(next_question)
            await self._save_session(session)
            return feedback, next_question.question_text
        else:
            # End session if no more questions
            session.session_state = SessionState.COMPLETED
            session.end_time = datetime.now()
            await self._save_session(session)
            return feedback + " Great work! You've completed this tutoring session.", None

    async def _analyze_response(self, session: TutoringSession, 
                              question: SocraticQuestion, 
                              response_text: str) -> StudentResponse:
        """Analyze student response for understanding and concepts"""
        response_id = f"resp_{session.session_id}_{len(session.responses)}"
        
        # Simple understanding analysis (in real implementation, would use NLP)
        understanding_level = self._assess_understanding_level(response_text, question)
        concepts_demonstrated = self._extract_demonstrated_concepts(response_text, question)
        
        analysis = {
            "response_length": len(response_text),
            "contains_examples": "example" in response_text.lower() or "for instance" in response_text.lower(),
            "shows_reasoning": any(word in response_text.lower() for word in ["because", "since", "therefore", "so"]),
            "asks_questions": "?" in response_text,
            "confidence_indicators": self._detect_confidence_level(response_text)
        }
        
        response = StudentResponse(
            response_id=response_id,
            session_id=session.session_id,
            question_id=question.question_id,
            response_text=response_text,
            understanding_level=understanding_level,
            concepts_demonstrated=concepts_demonstrated,
            analysis=analysis
        )
        
        await self._save_response(response)
        return response

    def _assess_understanding_level(self, response_text: str, question: SocraticQuestion) -> float:
        """Assess understanding level from response (simplified implementation)"""
        score = 0.3  # Base score for attempting to answer
        
        # Check for key concepts
        response_lower = response_text.lower()
        for concept in question.expected_concepts:
            if concept.lower() in response_lower:
                score += 0.2
        
        # Check for reasoning indicators
        reasoning_words = ["because", "since", "therefore", "so", "thus", "hence"]
        if any(word in response_lower for word in reasoning_words):
            score += 0.1
        
        # Check for examples or elaboration
        if len(response_text.split()) > 10:
            score += 0.1
        
        if any(phrase in response_lower for phrase in ["for example", "such as", "like when"]):
            score += 0.1
        
        # Check for questions (shows thinking)
        if "?" in response_text:
            score += 0.1
        
        return min(1.0, score)

    def _extract_demonstrated_concepts(self, response_text: str, question: SocraticQuestion) -> List[str]:
        """Extract concepts demonstrated in the response"""
        demonstrated = []
        response_lower = response_text.lower()
        
        for concept in question.expected_concepts:
            if concept.lower() in response_lower:
                demonstrated.append(concept)
        
        # Add additional concept detection logic here
        return demonstrated

    def _detect_confidence_level(self, response_text: str) -> str:
        """Detect confidence indicators in response"""
        response_lower = response_text.lower()
        
        high_confidence = ["definitely", "certainly", "clearly", "obviously", "sure"]
        low_confidence = ["maybe", "perhaps", "might", "possibly", "i think", "probably"]
        uncertainty = ["not sure", "don't know", "confused", "unclear"]
        
        if any(word in response_lower for word in high_confidence):
            return "high"
        elif any(word in response_lower for word in uncertainty):
            return "very_low"
        elif any(phrase in response_lower for phrase in low_confidence):
            return "low"
        else:
            return "medium"

    async def _generate_feedback(self, question: SocraticQuestion, response: StudentResponse) -> str:
        """Generate feedback for student response"""
        feedback_templates = {
            "high_understanding": [
                "Excellent thinking! You've grasped the key concepts.",
                "Great insight! Your reasoning is sound.",
                "Well done! You're demonstrating deep understanding."
            ],
            "medium_understanding": [
                "Good start! Let's explore this idea further.",
                "You're on the right track. Can you elaborate?",
                "Interesting point! What else can you tell me about this?"
            ],
            "low_understanding": [
                "Let me help you think through this step by step.",
                "That's a common way to think about it. Let's examine it more closely.",
                "Good effort! Let's approach this from a different angle."
            ]
        }
        
        if response.understanding_level >= 0.7:
            category = "high_understanding"
        elif response.understanding_level >= 0.4:
            category = "medium_understanding"
        else:
            category = "low_understanding"
        
        base_feedback = random.choice(feedback_templates[category])
        
        # Add specific feedback based on response analysis
        if response.analysis.get("shows_reasoning"):
            base_feedback += " I appreciate how you explained your thinking."
        
        if response.analysis.get("asks_questions"):
            base_feedback += " Your questions show you're thinking critically about this."
        
        return base_feedback

    async def _generate_opening_question(self, topic: str, difficulty: DifficultyLevel) -> Optional[SocraticQuestion]:
        """Generate opening question for a tutoring session"""
        question_id = f"q_{topic}_opening_{int(datetime.now().timestamp())}"
        
        # Topic-specific opening questions
        opening_questions = {
            "quadratic_equations": {
                DifficultyLevel.BEGINNER: "What do you already know about equations with x²?",
                DifficultyLevel.INTERMEDIATE: "How would you describe what makes an equation 'quadratic'?",
                DifficultyLevel.ADVANCED: "What connections do you see between quadratic equations and parabolas?"
            },
            "photosynthesis": {
                DifficultyLevel.BEGINNER: "What do you think plants need to grow?",
                DifficultyLevel.INTERMEDIATE: "How do you think plants make their own food?",
                DifficultyLevel.ADVANCED: "What role does photosynthesis play in global energy flow?"
            }
        }
        
        if topic in opening_questions and difficulty in opening_questions[topic]:
            question_text = opening_questions[topic][difficulty]
            
            question = SocraticQuestion(
                question_id=question_id,
                question_type=QuestionType.CLARIFICATION,
                question_text=question_text,
                topic=topic,
                difficulty=difficulty,
                expected_concepts=self._get_topic_concepts(topic),
                learning_objective=f"Assess prior knowledge of {topic}"
            )
            
            return question
        
        return None

    async def _generate_next_question(self, session: TutoringSession, 
                                    current_question: SocraticQuestion,
                                    response: StudentResponse) -> Optional[SocraticQuestion]:
        """Generate the next appropriate question based on response"""
        question_id = f"q_{session.topic}_{len(session.question_sequence)}_{int(datetime.now().timestamp())}"
        
        # Determine next question type based on understanding level and current type
        next_type = self._select_next_question_type(current_question.question_type, response.understanding_level)
        
        # Generate question based on type and context
        question_text = await self._generate_question_text(
            next_type, session.topic, response, session.difficulty_level
        )
        
        if not question_text:
            return None
        
        next_question = SocraticQuestion(
            question_id=question_id,
            question_type=next_type,
            question_text=question_text,
            topic=session.topic,
            difficulty=session.difficulty_level,
            expected_concepts=self._get_topic_concepts(session.topic)
        )
        
        return next_question

    def _select_next_question_type(self, current_type: QuestionType, understanding_level: float) -> QuestionType:
        """Select appropriate next question type"""
        if understanding_level < 0.3:
            # Need scaffolding
            return QuestionType.SCAFFOLDING
        elif understanding_level < 0.5:
            # Need clarification
            return QuestionType.CLARIFICATION
        elif understanding_level < 0.7:
            # Explore deeper
            if current_type == QuestionType.CLARIFICATION:
                return QuestionType.EVIDENCE
            elif current_type == QuestionType.EVIDENCE:
                return QuestionType.PERSPECTIVE
            else:
                return QuestionType.IMPLICATION
        else:
            # High understanding - challenge further
            if current_type in [QuestionType.CLARIFICATION, QuestionType.EVIDENCE]:
                return QuestionType.PERSPECTIVE
            elif current_type == QuestionType.PERSPECTIVE:
                return QuestionType.IMPLICATION
            else:
                return QuestionType.META

    async def _generate_question_text(self, question_type: QuestionType, topic: str, 
                                    response: StudentResponse, difficulty: DifficultyLevel) -> Optional[str]:
        """Generate question text based on type and context"""
        templates = self.question_templates.get(question_type, [])
        if not templates:
            return None
        
        # Select template and customize based on context
        template = random.choice(templates)
        
        # Simple template customization (in real implementation, would be more sophisticated)
        if "{concept}" in template and response.concepts_demonstrated:
            concept = response.concepts_demonstrated[0]
            template = template.replace("{concept}", concept)
        
        return template

    def _get_topic_concepts(self, topic: str) -> List[str]:
        """Get key concepts for a topic"""
        concept_map = {
            "quadratic_equations": ["quadratic", "coefficient", "discriminant", "vertex", "roots"],
            "photosynthesis": ["chlorophyll", "glucose", "carbon dioxide", "oxygen", "energy"]
        }
        return concept_map.get(topic, [])

    async def _update_understanding_progress(self, session: TutoringSession, response: StudentResponse):
        """Update understanding progress tracking"""
        # Update progress for learning objectives
        for objective in session.learning_objectives:
            if objective in response.concepts_demonstrated:
                current_progress = session.understanding_progress.get(objective, 0.0)
                new_progress = min(1.0, current_progress + response.understanding_level * 0.1)
                session.understanding_progress[objective] = new_progress

    async def get_session(self, session_id: str) -> Optional[TutoringSession]:
        """Get tutoring session by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT session_id, student_id, topic, difficulty_level, learning_objectives,
                   current_question_id, question_sequence, responses, understanding_progress,
                   session_state, start_time, end_time, metadata
            FROM tutoring_sessions
            WHERE session_id = ?
        ''', (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return TutoringSession(
            session_id=row[0],
            student_id=row[1],
            topic=row[2],
            difficulty_level=DifficultyLevel(row[3]),
            learning_objectives=json.loads(row[4]) if row[4] else [],
            current_question_id=row[5],
            question_sequence=json.loads(row[6]) if row[6] else [],
            responses=json.loads(row[7]) if row[7] else [],
            understanding_progress=json.loads(row[8]) if row[8] else {},
            session_state=SessionState(row[9]),
            start_time=datetime.fromisoformat(row[10]),
            end_time=datetime.fromisoformat(row[11]) if row[11] else None,
            metadata=json.loads(row[12]) if row[12] else {}
        )

    async def _get_question(self, question_id: str) -> Optional[SocraticQuestion]:
        """Get question by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT question_id, question_type, question_text, topic, difficulty,
                   expected_concepts, follow_up_hints, learning_objective
            FROM socratic_questions
            WHERE question_id = ?
        ''', (question_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return SocraticQuestion(
            question_id=row[0],
            question_type=QuestionType(row[1]),
            question_text=row[2],
            topic=row[3],
            difficulty=DifficultyLevel(row[4]),
            expected_concepts=json.loads(row[5]) if row[5] else [],
            follow_up_hints=json.loads(row[6]) if row[6] else [],
            learning_objective=row[7]
        )

    async def _save_session(self, session: TutoringSession):
        """Save tutoring session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tutoring_sessions
            (session_id, student_id, topic, difficulty_level, learning_objectives,
             current_question_id, question_sequence, responses, understanding_progress,
             session_state, start_time, end_time, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session.session_id, session.student_id, session.topic,
              session.difficulty_level.value, json.dumps(session.learning_objectives),
              session.current_question_id, json.dumps(session.question_sequence),
              json.dumps(session.responses), json.dumps(session.understanding_progress),
              session.session_state.value, session.start_time,
              session.end_time, json.dumps(session.metadata)))
        
        conn.commit()
        conn.close()

    async def _save_question(self, question: SocraticQuestion):
        """Save question to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO socratic_questions
            (question_id, question_type, question_text, topic, difficulty,
             expected_concepts, follow_up_hints, learning_objective)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (question.question_id, question.question_type.value, question.question_text,
              question.topic, question.difficulty.value, json.dumps(question.expected_concepts),
              json.dumps(question.follow_up_hints), question.learning_objective))
        
        conn.commit()
        conn.close()

    async def _save_response(self, response: StudentResponse):
        """Save student response to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO student_responses
            (response_id, session_id, question_id, response_text, understanding_level,
             concepts_demonstrated, timestamp, analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (response.response_id, response.session_id, response.question_id,
              response.response_text, response.understanding_level,
              json.dumps(response.concepts_demonstrated), response.timestamp,
              json.dumps(response.analysis)))
        
        conn.commit()
        conn.close()

async def demo_socratic_tutoring():
    """Demonstrate Socratic tutoring system"""
    tutor = SocraticTutor()
    
    print("=== Socratic Tutoring Demo ===")
    
    # Start session
    session = await tutor.start_session(
        student_id="student_jamie",
        topic="quadratic_equations",
        difficulty=DifficultyLevel.INTERMEDIATE,
        learning_objectives=["understand_quadratic_form", "solve_quadratic_equations"]
    )
    
    print(f"\nStarted tutoring session: {session.session_id}")
    print(f"Topic: {session.topic}")
    print(f"Difficulty: {session.difficulty_level.value}")
    
    # Get first question
    first_question = await tutor._get_question(session.current_question_id)
    print(f"\nTutor: {first_question.question_text}")
    
    # Simulate student responses
    responses = [
        "I think quadratic equations have x squared in them.",
        "Well, they have a highest power of 2 for the variable, so the graph would be curved.",
        "The general form is ax² + bx + c = 0 where a can't be zero because then it wouldn't be quadratic.",
        "We can solve them using factoring, completing the square, or the quadratic formula."
    ]
    
    for i, student_response in enumerate(responses):
        print(f"\nStudent: {student_response}")
        
        feedback, next_question = await tutor.process_response(session.session_id, student_response)
        print(f"Tutor: {feedback}")
        
        if next_question:
            print(f"Tutor: {next_question}")
        else:
            print("Session completed!")
            break
    
    # Show session progress
    final_session = await tutor.get_session(session.session_id)
    print(f"\nSession Progress:")
    print(f"Questions asked: {len(final_session.question_sequence)}")
    print(f"Understanding progress: {final_session.understanding_progress}")
    print(f"Session state: {final_session.session_state.value}")

if __name__ == "__main__":
    asyncio.run(demo_socratic_tutoring())