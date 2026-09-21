"""
Employee Management System with Skill Tracking & Career Paths
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from ..models.hatchery_types import (
    Employee, EmployeeRole, EmployeeSkill, SkillLevel, AlertLevel
)

logger = logging.getLogger(__name__)

class TrainingType(Enum):
    CERTIFICATION = "certification"
    SKILL_DEVELOPMENT = "skill_development"
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    LEADERSHIP = "leadership"
    TECHNICAL = "technical"

class CareerTrack(Enum):
    OPERATIONS = "operations"
    MANAGEMENT = "management"
    TECHNICAL_SPECIALIST = "technical_specialist"
    COMPLIANCE = "compliance"
    RESEARCH = "research"

@dataclass
class TrainingModule:
    module_id: str
    name: str
    type: TrainingType
    duration_hours: int
    prerequisites: List[str]
    skills_taught: List[str]
    certification_awarded: Optional[str]
    cost: float
    provider: str
    description: str

@dataclass
class CareerPath:
    path_id: str
    track: CareerTrack
    current_role: EmployeeRole
    next_role: EmployeeRole
    required_skills: List[str]
    required_certifications: List[str]
    estimated_timeline_months: int
    training_modules: List[str]  # module_ids
    mentorship_required: bool

@dataclass
class PerformanceReview:
    review_id: str
    employee_id: str
    reviewer_id: str
    review_date: datetime
    period_start: datetime
    period_end: datetime
    overall_rating: float  # 1.0 - 5.0
    skill_ratings: Dict[str, float]
    goals_achieved: List[str]
    areas_for_improvement: List[str]
    development_plan: List[str]
    promotion_recommended: bool
    salary_adjustment: float
    notes: Optional[str] = None

@dataclass
class SkillAssessment:
    assessment_id: str
    employee_id: str
    skill_name: str
    assessor_id: str
    assessment_date: datetime
    method: str  # "practical", "written", "observation", "peer_review"
    score: float  # 1.0 - 5.0
    level_achieved: SkillLevel
    certification_earned: bool
    next_assessment_due: Optional[datetime]
    notes: Optional[str] = None

class EmployeeManager:
    def __init__(self):
        self.employees: Dict[str, Employee] = {}
        self.training_modules = self._initialize_training_modules()
        self.career_paths = self._initialize_career_paths()
        self.performance_reviews: Dict[str, List[PerformanceReview]] = {}
        self.skill_assessments: Dict[str, List[SkillAssessment]] = {}
        self.training_schedule: Dict[str, List[str]] = {}  # employee_id -> module_ids
        
    def _initialize_training_modules(self) -> Dict[str, TrainingModule]:
        """Initialize available training modules"""
        modules = [
            TrainingModule(
                module_id="TM_001",
                name="Fish Health Assessment Basics",
                type=TrainingType.TECHNICAL,
                duration_hours=16,
                prerequisites=[],
                skills_taught=["fish_health_assessment", "disease_recognition"],
                certification_awarded="Fish Health Technician Level 1",
                cost=350.0,
                provider="Pacific Aquaculture Institute",
                description="Introduction to fish health evaluation and disease identification"
            ),
            TrainingModule(
                module_id="TM_002", 
                name="Water Quality Management",
                type=TrainingType.TECHNICAL,
                duration_hours=24,
                prerequisites=[],
                skills_taught=["water_quality_testing", "system_maintenance"],
                certification_awarded="Water Quality Specialist",
                cost=450.0,
                provider="Aquaculture Training Center",
                description="Comprehensive water quality monitoring and management"
            ),
            TrainingModule(
                module_id="TM_003",
                name="Feed Management & Nutrition",
                type=TrainingType.TECHNICAL,
                duration_hours=20,
                prerequisites=["TM_001"],
                skills_taught=["feeding_protocols", "nutrition_analysis"],
                certification_awarded="Aquaculture Nutrition Specialist",
                cost=400.0,
                provider="Fish Nutrition Institute",
                description="Advanced feeding strategies and nutritional requirements"
            ),
            TrainingModule(
                module_id="TM_004",
                name="NSRAA/SSRAA Compliance",
                type=TrainingType.COMPLIANCE,
                duration_hours=12,
                prerequisites=[],
                skills_taught=["regulatory_compliance", "documentation"],
                certification_awarded="Aquaculture Compliance Officer",
                cost=300.0,
                provider="Regulatory Training Solutions",
                description="Comprehensive compliance training for aquaculture operations"
            ),
            TrainingModule(
                module_id="TM_005",
                name="Leadership in Aquaculture",
                type=TrainingType.LEADERSHIP,
                duration_hours=32,
                prerequisites=["TM_001", "TM_002"],
                skills_taught=["team_leadership", "project_management"],
                certification_awarded="Aquaculture Operations Manager",
                cost=650.0,
                provider="Leadership Development Institute",
                description="Management skills for aquaculture facility leadership"
            ),
            TrainingModule(
                module_id="TM_006",
                name="Emergency Response & Safety",
                type=TrainingType.SAFETY,
                duration_hours=8,
                prerequisites=[],
                skills_taught=["emergency_response", "workplace_safety"],
                certification_awarded="Aquaculture Safety Coordinator",
                cost=200.0,
                provider="Safety Training Corp",
                description="Emergency procedures and workplace safety protocols"
            ),
            TrainingModule(
                module_id="TM_007",
                name="Advanced Disease Diagnostics",
                type=TrainingType.TECHNICAL,
                duration_hours=40,
                prerequisites=["TM_001", "TM_002"],
                skills_taught=["disease_diagnostics", "pathology", "treatment_protocols"],
                certification_awarded="Fish Health Specialist",
                cost=850.0,
                provider="Veterinary Aquaculture College",
                description="Advanced diagnostics and treatment of aquatic diseases"
            ),
            TrainingModule(
                module_id="TM_008",
                name="Breeding & Genetics",
                type=TrainingType.TECHNICAL,
                duration_hours=36,
                prerequisites=["TM_001", "TM_003"],
                skills_taught=["selective_breeding", "genetics", "spawning_management"],
                certification_awarded="Aquaculture Geneticist",
                cost=750.0,
                provider="Genetics Research Institute",
                description="Breeding programs and genetic management in aquaculture"
            )
        ]
        
        return {module.module_id: module for module in modules}
    
    def _initialize_career_paths(self) -> Dict[str, CareerPath]:
        """Initialize career advancement paths"""
        paths = [
            # Operations Track
            CareerPath(
                path_id="CP_001",
                track=CareerTrack.OPERATIONS,
                current_role=EmployeeRole.FISH_CULTURIST,
                next_role=EmployeeRole.HATCHERY_MANAGER,
                required_skills=["team_leadership", "project_management", "fish_health_assessment"],
                required_certifications=["Fish Health Specialist", "Aquaculture Operations Manager"],
                estimated_timeline_months=18,
                training_modules=["TM_005", "TM_007"],
                mentorship_required=True
            ),
            CareerPath(
                path_id="CP_002",
                track=CareerTrack.TECHNICAL_SPECIALIST,
                current_role=EmployeeRole.FISH_CULTURIST,
                next_role=EmployeeRole.VETERINARIAN,
                required_skills=["disease_diagnostics", "pathology", "treatment_protocols"],
                required_certifications=["Fish Health Specialist", "Veterinary License"],
                estimated_timeline_months=36,
                training_modules=["TM_007", "VET_001"],  # VET_001 would be external veterinary training
                mentorship_required=True
            ),
            CareerPath(
                path_id="CP_003",
                track=CareerTrack.TECHNICAL_SPECIALIST,
                current_role=EmployeeRole.WATER_QUALITY_TECH,
                next_role=EmployeeRole.FEED_SPECIALIST,
                required_skills=["feeding_protocols", "nutrition_analysis"],
                required_certifications=["Aquaculture Nutrition Specialist"],
                estimated_timeline_months=12,
                training_modules=["TM_003"],
                mentorship_required=False
            ),
            CareerPath(
                path_id="CP_004",
                track=CareerTrack.COMPLIANCE,
                current_role=EmployeeRole.FISH_CULTURIST,
                next_role=EmployeeRole.COMPLIANCE_OFFICER,
                required_skills=["regulatory_compliance", "documentation", "quality_assurance"],
                required_certifications=["Aquaculture Compliance Officer"],
                estimated_timeline_months=9,
                training_modules=["TM_004"],
                mentorship_required=True
            )
        ]
        
        return {path.path_id: path for path in paths}
    
    async def add_employee(self, employee: Employee) -> bool:
        """Add new employee to system"""
        if employee.employee_id in self.employees:
            logger.warning(f"Employee {employee.employee_id} already exists")
            return False
        
        self.employees[employee.employee_id] = employee
        await self._initialize_employee_development_plan(employee.employee_id)
        
        logger.info(f"Added employee: {employee.name} ({employee.employee_id})")
        return True
    
    async def get_all_employees(self) -> Dict[str, Any]:
        """Get all employees with summary stats"""
        employees_data = []
        
        for emp_id, employee in self.employees.items():
            employee_summary = {
                "employee_id": emp_id,
                "name": employee.name,
                "role": employee.role.value,
                "hire_date": employee.hire_date.isoformat(),
                "performance_rating": employee.performance_rating,
                "skills_count": len(employee.skills),
                "certifications_count": len(employee.certifications),
                "is_active": employee.is_active,
                "next_review_due": await self._get_next_review_date(emp_id),
                "career_track": await self._get_current_career_track(emp_id)
            }
            employees_data.append(employee_summary)
        
        return {
            "employees": employees_data,
            "total_employees": len(self.employees),
            "active_employees": sum(1 for e in self.employees.values() if e.is_active),
            "average_performance": sum(e.performance_rating for e in self.employees.values()) / len(self.employees) if self.employees else 0
        }
    
    async def conduct_skill_assessment(self, employee_id: str, assessment_data: dict) -> Dict[str, Any]:
        """Conduct skill assessment for employee"""
        if employee_id not in self.employees:
            return {"error": "Employee not found"}
        
        employee = self.employees[employee_id]
        skill_name = assessment_data.get("skill_name")
        assessor_id = assessment_data.get("assessor_id")
        method = assessment_data.get("method", "observation")
        
        # Simulate assessment scoring
        base_score = assessment_data.get("score", 3.5)
        
        # Determine skill level based on score
        if base_score >= 4.5:
            level_achieved = SkillLevel.EXPERT
        elif base_score >= 3.5:
            level_achieved = SkillLevel.ADVANCED
        elif base_score >= 2.5:
            level_achieved = SkillLevel.INTERMEDIATE
        elif base_score >= 1.5:
            level_achieved = SkillLevel.BEGINNER
        else:
            level_achieved = SkillLevel.NOVICE
        
        # Check if certification threshold met
        certification_earned = base_score >= 3.5 and method in ["practical", "written"]
        
        # Create assessment record
        assessment = SkillAssessment(
            assessment_id=f"SA_{employee_id}_{skill_name}_{datetime.now().strftime('%Y%m%d')}",
            employee_id=employee_id,
            skill_name=skill_name,
            assessor_id=assessor_id,
            assessment_date=datetime.now(timezone.utc),
            method=method,
            score=base_score,
            level_achieved=level_achieved,
            certification_earned=certification_earned,
            next_assessment_due=datetime.now(timezone.utc) + timedelta(days=180),
            notes=assessment_data.get("notes")
        )
        
        # Store assessment
        if employee_id not in self.skill_assessments:
            self.skill_assessments[employee_id] = []
        self.skill_assessments[employee_id].append(assessment)
        
        # Update employee skill
        employee.add_skill(skill_name, level_achieved, certification_earned)
        
        # Check for career advancement opportunities
        advancement_opportunities = await self._check_advancement_eligibility(employee_id)
        
        logger.info(f"Skill assessment completed for {employee.name}: {skill_name} -> {level_achieved.name}")
        
        return {
            "assessment_id": assessment.assessment_id,
            "skill_name": skill_name,
            "level_achieved": level_achieved.name,
            "score": base_score,
            "certification_earned": certification_earned,
            "advancement_opportunities": advancement_opportunities,
            "next_assessment_due": assessment.next_assessment_due.isoformat()
        }
    
    async def _initialize_employee_development_plan(self, employee_id: str):
        """Create initial development plan for new employee"""
        employee = self.employees[employee_id]
        
        # Recommend basic training based on role
        recommended_modules = []
        
        if employee.role in [EmployeeRole.FISH_CULTURIST, EmployeeRole.HATCHERY_MANAGER]:
            recommended_modules.extend(["TM_001", "TM_002", "TM_006"])
        
        if employee.role == EmployeeRole.WATER_QUALITY_TECH:
            recommended_modules.extend(["TM_002", "TM_006"])
        
        if employee.role == EmployeeRole.FEED_SPECIALIST:
            recommended_modules.extend(["TM_003", "TM_006"])
        
        if employee.role == EmployeeRole.COMPLIANCE_OFFICER:
            recommended_modules.extend(["TM_004", "TM_006"])
        
        self.training_schedule[employee_id] = recommended_modules
        
        logger.info(f"Created development plan for {employee.name}: {len(recommended_modules)} modules")
    
    async def _get_next_review_date(self, employee_id: str) -> Optional[str]:
        """Calculate next performance review date"""
        if employee_id in self.performance_reviews and self.performance_reviews[employee_id]:
            last_review = max(self.performance_reviews[employee_id], key=lambda r: r.review_date)
            next_review = last_review.review_date + timedelta(days=365)
        else:
            # For new employees, first review after 90 days
            hire_date = self.employees[employee_id].hire_date
            next_review = hire_date + timedelta(days=90)
        
        return next_review.isoformat() if next_review > datetime.now(timezone.utc) else None
    
    async def _get_current_career_track(self, employee_id: str) -> Optional[str]:
        """Determine employee's current career track"""
        employee = self.employees[employee_id]
        
        # Find applicable career paths based on current role
        applicable_paths = [
            path for path in self.career_paths.values()
            if path.current_role == employee.role
        ]
        
        if not applicable_paths:
            return None
        
        # Return the track they're most qualified for based on skills
        best_match = None
        highest_skill_match = 0
        
        for path in applicable_paths:
            skill_matches = sum(
                1 for skill in path.required_skills
                if employee.get_skill_level(skill) is not None
            )
            
            if skill_matches > highest_skill_match:
                highest_skill_match = skill_matches
                best_match = path.track.value
        
        return best_match
    
    async def _check_advancement_eligibility(self, employee_id: str) -> List[Dict[str, Any]]:
        """Check if employee is eligible for advancement"""
        employee = self.employees[employee_id]
        opportunities = []
        
        for path_id, path in self.career_paths.items():
            if path.current_role != employee.role:
                continue
            
            # Check skill requirements
            skills_met = 0
            skills_needed = []
            
            for required_skill in path.required_skills:
                skill_level = employee.get_skill_level(required_skill)
                if skill_level and skill_level.value >= 3:  # At least intermediate
                    skills_met += 1
                else:
                    skills_needed.append(required_skill)
            
            # Check certifications
            certs_met = sum(
                1 for cert in path.required_certifications
                if cert in employee.certifications
            )
            
            # Calculate eligibility percentage
            total_requirements = len(path.required_skills) + len(path.required_certifications)
            met_requirements = skills_met + certs_met
            eligibility_percentage = (met_requirements / total_requirements) * 100 if total_requirements > 0 else 0
            
            opportunity = {
                "path_id": path_id,
                "target_role": path.next_role.value,
                "career_track": path.track.value,
                "eligibility_percentage": eligibility_percentage,
                "skills_needed": skills_needed,
                "certifications_needed": [
                    cert for cert in path.required_certifications
                    if cert not in employee.certifications
                ],
                "recommended_training": [
                    module_id for module_id in path.training_modules
                    if module_id in self.training_modules
                ],
                "estimated_timeline_months": path.estimated_timeline_months,
                "mentorship_required": path.mentorship_required
            }
            
            opportunities.append(opportunity)
        
        # Sort by eligibility percentage
        opportunities.sort(key=lambda x: x["eligibility_percentage"], reverse=True)
        
        return opportunities
    
    async def get_employee_development_plan(self, employee_id: str) -> Dict[str, Any]:
        """Get comprehensive development plan for employee"""
        if employee_id not in self.employees:
            return {"error": "Employee not found"}
        
        employee = self.employees[employee_id]
        
        # Get current skills assessment
        current_skills = [
            {
                "skill_name": skill.skill_name,
                "level": skill.level.name,
                "certified": skill.certified,
                "training_hours": skill.training_hours
            }
            for skill in employee.skills
        ]
        
        # Get advancement opportunities
        advancement_opportunities = await self._check_advancement_eligibility(employee_id)
        
        # Get recommended training
        scheduled_training = self.training_schedule.get(employee_id, [])
        training_details = [
            {
                "module_id": module_id,
                "name": self.training_modules[module_id].name,
                "duration_hours": self.training_modules[module_id].duration_hours,
                "cost": self.training_modules[module_id].cost,
                "skills_taught": self.training_modules[module_id].skills_taught
            }
            for module_id in scheduled_training
            if module_id in self.training_modules
        ]
        
        # Calculate development metrics
        total_training_hours = sum(module["duration_hours"] for module in training_details)
        total_training_cost = sum(module["cost"] for module in training_details)
        
        return {
            "employee": {
                "id": employee_id,
                "name": employee.name,
                "role": employee.role.value,
                "performance_rating": employee.performance_rating,
                "hire_date": employee.hire_date.isoformat()
            },
            "current_skills": current_skills,
            "advancement_opportunities": advancement_opportunities,
            "recommended_training": training_details,
            "development_metrics": {
                "total_training_hours": total_training_hours,
                "total_training_cost": total_training_cost,
                "skills_count": len(current_skills),
                "certifications_count": len(employee.certifications)
            },
            "next_review_date": await self._get_next_review_date(employee_id)
        }
    
    async def schedule_training(self, employee_id: str, module_ids: List[str]) -> Dict[str, Any]:
        """Schedule training modules for employee"""
        if employee_id not in self.employees:
            return {"error": "Employee not found"}
        
        invalid_modules = [mid for mid in module_ids if mid not in self.training_modules]
        if invalid_modules:
            return {"error": f"Invalid training modules: {invalid_modules}"}
        
        # Add to training schedule
        if employee_id not in self.training_schedule:
            self.training_schedule[employee_id] = []
        
        for module_id in module_ids:
            if module_id not in self.training_schedule[employee_id]:
                self.training_schedule[employee_id].append(module_id)
        
        # Calculate training summary
        total_hours = sum(
            self.training_modules[mid].duration_hours
            for mid in self.training_schedule[employee_id]
        )
        total_cost = sum(
            self.training_modules[mid].cost
            for mid in self.training_schedule[employee_id]
        )
        
        logger.info(f"Scheduled {len(module_ids)} training modules for employee {employee_id}")
        
        return {
            "employee_id": employee_id,
            "scheduled_modules": len(self.training_schedule[employee_id]),
            "total_training_hours": total_hours,
            "total_cost": total_cost,
            "estimated_completion_weeks": total_hours / 8  # Assuming 8 hours per week
        }