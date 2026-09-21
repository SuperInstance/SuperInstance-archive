from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sqlite3
import uuid
import json
import hashlib
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

router = APIRouter()

# Pydantic models
class Course(BaseModel):
    course_id: str
    title: str
    description: str
    difficulty_level: str  # beginner, intermediate, advanced
    estimated_hours: float
    cpe_credits: float
    prerequisites: List[str]
    learning_objectives: List[str]
    course_modules: List[Dict[str, Any]]
    is_active: bool

class Certification(BaseModel):
    certification_id: str
    user_id: str
    course_id: str
    course_name: str
    completion_date: datetime
    final_score: int
    passing_score: int
    total_time_minutes: int
    certificate_url: str
    cpe_credits: float
    is_valid: bool
    expiry_date: Optional[datetime]

class SkillAssessment(BaseModel):
    assessment_id: str
    user_id: str
    skill_category: str  # technical_analysis, fundamental_analysis, risk_management, etc.
    current_level: str   # novice, beginner, intermediate, advanced, expert
    score: int
    max_score: int
    strengths: List[str]
    improvement_areas: List[str]
    recommended_courses: List[str]

class TeacherDashboard(BaseModel):
    teacher_id: str
    school_name: str
    students: List[Dict[str, Any]]
    class_performance: Dict[str, Any]
    curriculum_progress: Dict[str, Any]
    assignments: List[Dict[str, Any]]

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('trading_legal.db')

def generate_certificate(user_name: str, course_name: str, completion_date: datetime, score: int) -> str:
    """Generate a certificate image and return base64 encoded string"""
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(11, 8.5))  # Letter size
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Certificate border
    border = plt.Rectangle((0.5, 0.5), 9, 9, linewidth=3, edgecolor='gold', facecolor='white')
    ax.add_patch(border)
    
    # Inner border
    inner_border = plt.Rectangle((0.8, 0.8), 8.4, 8.4, linewidth=1, edgecolor='navy', facecolor='none')
    ax.add_patch(inner_border)
    
    # Title
    ax.text(5, 8.5, 'CERTIFICATE OF COMPLETION', fontsize=20, fontweight='bold', 
            ha='center', va='center', color='navy')
    
    # Subtitle
    ax.text(5, 7.8, 'ActiveLog Paper Trading Platform', fontsize=14, 
            ha='center', va='center', color='darkblue')
    
    # Main text
    ax.text(5, 6.8, 'This is to certify that', fontsize=12, 
            ha='center', va='center', color='black')
    
    # User name
    ax.text(5, 6.2, user_name, fontsize=18, fontweight='bold', 
            ha='center', va='center', color='darkgreen')
    
    # Course completion text
    ax.text(5, 5.6, 'has successfully completed the course', fontsize=12, 
            ha='center', va='center', color='black')
    
    # Course name
    ax.text(5, 5.0, course_name, fontsize=16, fontweight='bold', 
            ha='center', va='center', color='darkblue')
    
    # Score
    ax.text(5, 4.4, f'Final Score: {score}%', fontsize=14, 
            ha='center', va='center', color='darkgreen')
    
    # Date
    ax.text(5, 3.8, f'Date of Completion: {completion_date.strftime("%B %d, %Y")}', fontsize=12, 
            ha='center', va='center', color='black')
    
    # Signature line
    ax.text(2.5, 2.5, 'Course Instructor', fontsize=10, 
            ha='center', va='center', color='black')
    ax.plot([1.5, 3.5], [2.3, 2.3], 'k-', linewidth=1)
    
    # Date line
    ax.text(7.5, 2.5, 'Date', fontsize=10, 
            ha='center', va='center', color='black')
    ax.plot([6.5, 8.5], [2.3, 2.3], 'k-', linewidth=1)
    
    # Certificate ID
    cert_id = hashlib.md5(f"{user_name}{course_name}{completion_date}".encode()).hexdigest()[:8]
    ax.text(5, 1.5, f'Certificate ID: {cert_id.upper()}', fontsize=8, 
            ha='center', va='center', color='gray')
    
    # Save to BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    buffer.seek(0)
    
    # Convert to base64
    img_data = buffer.getvalue()
    img_base64 = base64.b64encode(img_data).decode('utf-8')
    
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"

@router.get("/courses", response_model=List[Course])
async def get_available_courses(difficulty: Optional[str] = None, cpe_eligible: Optional[bool] = None):
    """Get list of available educational courses"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with filters
    where_conditions = ["is_active = 1"]
    params = []
    
    if difficulty:
        where_conditions.append("difficulty_level = ?")
        params.append(difficulty)
    
    if cpe_eligible:
        where_conditions.append("cpe_credits > 0")
    
    where_clause = " AND ".join(where_conditions)
    
    query = f'''
        SELECT course_id, title, description, difficulty_level, estimated_hours, 
               cpe_credits, prerequisites, learning_objectives, course_content
        FROM courses
        WHERE {where_clause}
        ORDER BY difficulty_level, estimated_hours
    '''
    
    cursor.execute(query, params)
    courses_data = cursor.fetchall()
    
    conn.close()
    
    courses = []
    for course_data in courses_data:
        course_id, title, description, difficulty, hours, cpe_credits, prereqs, objectives, content = course_data
        
        # Parse JSON fields
        try:
            prerequisites = json.loads(prereqs) if prereqs else []
            learning_objectives = json.loads(objectives) if objectives else []
            course_content = json.loads(content) if content else []
        except:
            prerequisites = []
            learning_objectives = []
            course_content = []
        
        courses.append(Course(
            course_id=course_id,
            title=title,
            description=description,
            difficulty_level=difficulty,
            estimated_hours=hours,
            cpe_credits=cpe_credits,
            prerequisites=prerequisites,
            learning_objectives=learning_objectives,
            course_modules=course_content,
            is_active=True
        ))
    
    return courses

@router.get("/course/{course_id}")
async def get_course_details(course_id: str):
    """Get detailed course information including curriculum"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT course_id, title, description, difficulty_level, estimated_hours, 
               cpe_credits, prerequisites, learning_objectives, course_content
        FROM courses
        WHERE course_id = ? AND is_active = 1
    ''', (course_id,))
    
    course_data = cursor.fetchone()
    
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course_id, title, description, difficulty, hours, cpe_credits, prereqs, objectives, content = course_data
    
    # Parse JSON fields
    try:
        prerequisites = json.loads(prereqs) if prereqs else []
        learning_objectives = json.loads(objectives) if objectives else []
        course_modules = json.loads(content) if content else []
    except:
        prerequisites = []
        learning_objectives = []
        course_modules = []
    
    # Add detailed curriculum if not present
    if not course_modules:
        course_modules = _get_default_curriculum(course_id)
    
    # Get enrollment statistics
    cursor.execute('''
        SELECT COUNT(*) as total_enrolled,
               AVG(final_score) as avg_score,
               COUNT(CASE WHEN final_score >= passing_score THEN 1 END) as passed
        FROM certifications
        WHERE course_id = ?
    ''', (course_id,))
    
    stats = cursor.fetchone()
    total_enrolled, avg_score, passed = stats if stats else (0, 0, 0)
    
    conn.close()
    
    return {
        "course_id": course_id,
        "title": title,
        "description": description,
        "difficulty_level": difficulty,
        "estimated_hours": hours,
        "cpe_credits": cpe_credits,
        "prerequisites": prerequisites,
        "learning_objectives": learning_objectives,
        "course_modules": course_modules,
        "enrollment_stats": {
            "total_enrolled": total_enrolled,
            "average_score": avg_score,
            "pass_rate": (passed / total_enrolled * 100) if total_enrolled > 0 else 0
        },
        "instructor": "ActiveLog Education Team",
        "format": "Self-paced online",
        "certification_available": True
    }

def _get_default_curriculum(course_id: str) -> List[Dict[str, Any]]:
    """Generate default curriculum based on course ID"""
    
    curricula = {
        "trading_basics_101": [
            {
                "module_id": 1,
                "title": "Introduction to Financial Markets",
                "duration_minutes": 45,
                "content_type": "video_lecture",
                "learning_objectives": ["Understand market structure", "Learn key terminology"],
                "assessment": True
            },
            {
                "module_id": 2,
                "title": "Order Types and Execution",
                "duration_minutes": 60,
                "content_type": "interactive_tutorial",
                "learning_objectives": ["Master order types", "Practice order placement"],
                "assessment": True
            },
            {
                "module_id": 3,
                "title": "Risk Management Fundamentals",
                "duration_minutes": 90,
                "content_type": "case_study",
                "learning_objectives": ["Learn position sizing", "Understand stop losses"],
                "assessment": True
            },
            {
                "module_id": 4,
                "title": "Final Assessment",
                "duration_minutes": 60,
                "content_type": "comprehensive_exam",
                "learning_objectives": ["Demonstrate mastery of all concepts"],
                "assessment": True
            }
        ],
        "options_mastery": [
            {
                "module_id": 1,
                "title": "Options Basics and Terminology",
                "duration_minutes": 90,
                "content_type": "video_lecture",
                "learning_objectives": ["Understand calls and puts", "Learn options terminology"],
                "assessment": True
            },
            {
                "module_id": 2,
                "title": "Options Pricing and Greeks",
                "duration_minutes": 120,
                "content_type": "interactive_simulation",
                "learning_objectives": ["Master options pricing", "Understand delta, gamma, theta, vega"],
                "assessment": True
            },
            {
                "module_id": 3,
                "title": "Basic Options Strategies",
                "duration_minutes": 150,
                "content_type": "strategy_workshop",
                "learning_objectives": ["Learn covered calls", "Master protective puts", "Understand spreads"],
                "assessment": True
            },
            {
                "module_id": 4,
                "title": "Advanced Options Strategies",
                "duration_minutes": 180,
                "content_type": "advanced_simulation",
                "learning_objectives": ["Complex spreads", "Multi-leg strategies", "Risk management"],
                "assessment": True
            }
        ]
    }
    
    return curricula.get(course_id, [])

@router.post("/enroll-course")
async def enroll_in_course(user_id: str, course_id: str):
    """Enroll user in a course"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if course exists
    cursor.execute('SELECT title FROM courses WHERE course_id = ? AND is_active = 1', (course_id,))
    course = cursor.fetchone()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if already enrolled
    cursor.execute('''
        SELECT certification_id FROM certifications 
        WHERE user_id = ? AND course_id = ?
    ''', (user_id, course_id))
    
    existing_enrollment = cursor.fetchone()
    
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    
    # Create enrollment record (simplified - in production this would be separate from certifications)
    enrollment_id = str(uuid.uuid4())
    
    conn.close()
    
    return {
        "enrollment_id": enrollment_id,
        "user_id": user_id,
        "course_id": course_id,
        "course_title": course[0],
        "enrollment_date": datetime.now(),
        "status": "enrolled",
        "message": "Successfully enrolled in course"
    }

@router.post("/complete-course")
async def complete_course(
    user_id: str,
    course_id: str,
    final_score: int,
    total_time_minutes: int,
    user_name: str = "Student"
):
    """Complete a course and generate certification"""
    
    if final_score < 0 or final_score > 100:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get course details
    cursor.execute('''
        SELECT title, cpe_credits FROM courses 
        WHERE course_id = ? AND is_active = 1
    ''', (course_id,))
    
    course = cursor.fetchone()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course_name, cpe_credits = course
    passing_score = 70  # Standard passing score
    
    # Generate certificate if passed
    if final_score >= passing_score:
        completion_date = datetime.now()
        certificate_data = generate_certificate(user_name, course_name, completion_date, final_score)
        
        # Store certification
        certification_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO certifications
            (certification_id, user_id, course_id, course_name, final_score, 
             passing_score, total_time_minutes, certificate_url, cpe_credits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (certification_id, user_id, course_id, course_name, final_score,
              passing_score, total_time_minutes, certificate_data, cpe_credits))
        
        conn.commit()
        conn.close()
        
        return Certification(
            certification_id=certification_id,
            user_id=user_id,
            course_id=course_id,
            course_name=course_name,
            completion_date=completion_date,
            final_score=final_score,
            passing_score=passing_score,
            total_time_minutes=total_time_minutes,
            certificate_url=certificate_data,
            cpe_credits=cpe_credits,
            is_valid=True,
            expiry_date=completion_date + timedelta(days=365*3) if cpe_credits > 0 else None
        )
    
    else:
        conn.close()
        return {
            "message": "Course completed but did not meet passing requirements",
            "final_score": final_score,
            "passing_score": passing_score,
            "can_retake": True
        }

@router.get("/user-certifications/{user_id}")
async def get_user_certifications(user_id: str):
    """Get all certifications for a user"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT certification_id, course_id, course_name, completion_date, 
               final_score, passing_score, total_time_minutes, certificate_url, 
               cpe_credits, is_valid, expiry_date
        FROM certifications
        WHERE user_id = ?
        ORDER BY completion_date DESC
    ''', (user_id,))
    
    certifications_data = cursor.fetchall()
    
    # Calculate total CPE credits
    cursor.execute('''
        SELECT SUM(cpe_credits) FROM certifications 
        WHERE user_id = ? AND is_valid = 1
    ''', (user_id,))
    
    total_cpe = cursor.fetchone()[0] or 0
    
    conn.close()
    
    certifications = []
    for cert_data in certifications_data:
        cert_id, course_id, course_name, completion_date, final_score, passing_score, total_time, cert_url, cpe_credits, is_valid, expiry_date = cert_data
        
        certifications.append({
            "certification_id": cert_id,
            "course_id": course_id,
            "course_name": course_name,
            "completion_date": completion_date,
            "final_score": final_score,
            "passing_score": passing_score,
            "total_time_minutes": total_time,
            "certificate_url": cert_url,
            "cpe_credits": cpe_credits,
            "is_valid": is_valid,
            "expiry_date": expiry_date,
            "status": "valid" if is_valid else "expired"
        })
    
    return {
        "user_id": user_id,
        "total_certifications": len(certifications),
        "total_cpe_credits": total_cpe,
        "certifications": certifications
    }

@router.post("/skill-assessment")
async def conduct_skill_assessment(
    user_id: str,
    skill_category: str,
    assessment_data: Dict[str, Any]
):
    """Conduct skill assessment and provide recommendations"""
    
    # Mock assessment scoring based on category
    assessment_scores = {
        "technical_analysis": {
            "max_score": 100,
            "questions": ["Chart patterns", "Indicators", "Trend analysis", "Support/resistance"],
            "weight_distribution": [0.3, 0.3, 0.2, 0.2]
        },
        "fundamental_analysis": {
            "max_score": 100,
            "questions": ["Financial statements", "Ratios", "Industry analysis", "Economic factors"],
            "weight_distribution": [0.4, 0.3, 0.2, 0.1]
        },
        "risk_management": {
            "max_score": 100,
            "questions": ["Position sizing", "Stop losses", "Portfolio theory", "Risk metrics"],
            "weight_distribution": [0.3, 0.3, 0.2, 0.2]
        },
        "options_trading": {
            "max_score": 100,
            "questions": ["Options basics", "Greeks", "Strategies", "Risk management"],
            "weight_distribution": [0.2, 0.3, 0.3, 0.2]
        }
    }
    
    if skill_category not in assessment_scores:
        raise HTTPException(status_code=400, detail="Invalid skill category")
    
    # Calculate score (simplified)
    assessment_config = assessment_scores[skill_category]
    
    # Mock scoring logic
    answers = assessment_data.get("answers", [70, 65, 80, 75])  # Mock answers out of 100 each
    weights = assessment_config["weight_distribution"]
    
    final_score = sum(answer * weight for answer, weight in zip(answers, weights))
    
    # Determine skill level
    if final_score >= 90:
        skill_level = "expert"
    elif final_score >= 80:
        skill_level = "advanced"
    elif final_score >= 65:
        skill_level = "intermediate"
    elif final_score >= 50:
        skill_level = "beginner"
    else:
        skill_level = "novice"
    
    # Generate strengths and improvement areas
    question_areas = assessment_config["questions"]
    strengths = [area for i, area in enumerate(question_areas) if answers[i] >= 75]
    improvement_areas = [area for i, area in enumerate(question_areas) if answers[i] < 65]
    
    # Recommend courses based on skill level and improvement areas
    course_recommendations = {
        "technical_analysis": ["trading_basics_101"] if skill_level in ["novice", "beginner"] else ["advanced_technical_analysis"],
        "fundamental_analysis": ["fundamental_analysis_101"] if skill_level in ["novice", "beginner"] else ["advanced_fundamental_analysis"],
        "risk_management": ["risk_management_fundamentals"] if skill_level in ["novice", "beginner"] else ["advanced_portfolio_management"],
        "options_trading": ["options_basics"] if skill_level in ["novice", "beginner"] else ["options_mastery"]
    }
    
    recommended_courses = course_recommendations.get(skill_category, [])
    
    assessment_id = str(uuid.uuid4())
    
    return SkillAssessment(
        assessment_id=assessment_id,
        user_id=user_id,
        skill_category=skill_category,
        current_level=skill_level,
        score=int(final_score),
        max_score=assessment_config["max_score"],
        strengths=strengths,
        improvement_areas=improvement_areas,
        recommended_courses=recommended_courses
    )

@router.get("/teacher-dashboard/{teacher_id}")
async def get_teacher_dashboard(teacher_id: str, class_id: Optional[str] = None):
    """Get teacher dashboard with student progress and class management tools"""
    
    # Mock data for teacher dashboard
    students = [
        {
            "student_id": "student_001",
            "name": "Alice Johnson",
            "grade": "10th",
            "courses_enrolled": ["trading_basics_101"],
            "current_progress": 65,
            "last_activity": "2024-01-15",
            "performance_trend": "improving"
        },
        {
            "student_id": "student_002", 
            "name": "Bob Smith",
            "grade": "11th",
            "courses_enrolled": ["trading_basics_101", "crypto_trading_cert"],
            "current_progress": 80,
            "last_activity": "2024-01-16",
            "performance_trend": "stable"
        },
        {
            "student_id": "student_003",
            "name": "Carol Davis",
            "grade": "12th", 
            "courses_enrolled": ["options_mastery"],
            "current_progress": 45,
            "last_activity": "2024-01-10",
            "performance_trend": "needs_attention"
        }
    ]
    
    class_performance = {
        "average_completion_rate": 63.3,
        "average_score": 76.8,
        "active_students": 28,
        "total_enrolled": 32,
        "courses_in_progress": 3,
        "completion_trend": "+12% this month"
    }
    
    curriculum_progress = {
        "trading_basics_101": {
            "enrolled_students": 20,
            "average_progress": 70,
            "completion_rate": 65
        },
        "crypto_trading_cert": {
            "enrolled_students": 8,
            "average_progress": 55,
            "completion_rate": 40
        },
        "options_mastery": {
            "enrolled_students": 4,
            "average_progress": 30,
            "completion_rate": 25
        }
    }
    
    assignments = [
        {
            "assignment_id": "assign_001",
            "title": "Portfolio Diversification Exercise",
            "due_date": "2024-01-25",
            "submitted": 15,
            "total_students": 20,
            "average_score": 82
        },
        {
            "assignment_id": "assign_002",
            "title": "Risk Assessment Project", 
            "due_date": "2024-01-30",
            "submitted": 8,
            "total_students": 20,
            "average_score": 78
        }
    ]
    
    return TeacherDashboard(
        teacher_id=teacher_id,
        school_name="Lincoln High School",
        students=students,
        class_performance=class_performance,
        curriculum_progress=curriculum_progress,
        assignments=assignments
    )

@router.get("/parent-report/{student_id}")
async def generate_parent_report(student_id: str, report_period: str = "monthly"):
    """Generate progress report for parents"""
    
    # Mock student progress data
    return {
        "student_id": student_id,
        "student_name": "Alice Johnson",
        "report_period": report_period,
        "generated_date": datetime.now(),
        "overall_progress": {
            "courses_enrolled": 2,
            "courses_completed": 1,
            "total_time_spent_hours": 12.5,
            "overall_grade": "B+",
            "improvement_trend": "positive"
        },
        "course_details": [
            {
                "course_name": "Trading Fundamentals 101",
                "progress_percent": 85,
                "current_grade": "A-", 
                "time_spent_hours": 8.0,
                "strengths": ["Risk management concepts", "Market terminology"],
                "areas_for_improvement": ["Technical analysis", "Chart reading"],
                "teacher_notes": "Excellent progress in understanding basic concepts"
            }
        ],
        "safety_compliance": {
            "paper_trading_only": True,
            "age_appropriate_content": True,
            "parental_controls_active": True,
            "data_privacy_compliant": True
        },
        "recommendations": [
            "Continue with current pace of learning",
            "Consider enrolling in intermediate course next semester",
            "Practice more with chart analysis tools"
        ],
        "next_parent_conference": "2024-02-15"
    }

@router.get("/curriculum-alignment")
async def get_curriculum_alignment(
    education_level: str,  # high_school, college, professional
    region: str = "US"
):
    """Get curriculum alignment with educational standards"""
    
    alignments = {
        "high_school": {
            "standards": ["Common Core Math", "Personal Finance Standards", "Economics Standards"],
            "grade_levels": ["9th", "10th", "11th", "12th"],
            "learning_objectives": [
                "Understand basic economic principles",
                "Learn personal financial management",
                "Develop analytical thinking skills",
                "Practice mathematical applications"
            ],
            "assessment_methods": ["Quizzes", "Projects", "Simulations", "Peer reviews"],
            "time_allocation": {
                "semester_course": "18 weeks, 3 credits",
                "unit_course": "6 weeks, 1 credit",
                "elective": "Variable scheduling"
            }
        },
        "college": {
            "standards": ["Business Program Standards", "Finance Curriculum Guidelines"],
            "credit_hours": 3,
            "prerequisites": ["Intro to Economics", "Basic Mathematics"],
            "learning_outcomes": [
                "Analyze market structures and mechanisms",
                "Evaluate investment strategies",
                "Apply risk management principles",
                "Demonstrate quantitative analysis skills"
            ],
            "capstone_project": "Portfolio management simulation"
        },
        "professional": {
            "certifications": ["CFA Institute", "FRM", "Series 7 prep"],
            "cpe_credits": "Available for continuing education",
            "professional_standards": ["Ethical trading practices", "Regulatory compliance"],
            "career_relevance": [
                "Financial advisory",
                "Investment banking",
                "Risk management",
                "Portfolio management"
            ]
        }
    }
    
    if education_level not in alignments:
        raise HTTPException(status_code=400, detail="Invalid education level")
    
    return {
        "education_level": education_level,
        "region": region,
        "alignment_details": alignments[education_level],
        "implementation_guide": {
            "setup_instructions": "Contact education@activelog.ai for implementation support",
            "teacher_training": "Available online and in-person",
            "student_accounts": "Bulk registration available for educational institutions",
            "progress_tracking": "Comprehensive reporting for educators"
        }
    }