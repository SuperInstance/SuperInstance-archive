"""
Marketplace v2 - Assembler Wanted Boards
Community-driven marketplace for finding skilled assemblers and service providers
"""

import asyncio
import sqlite3
import json
import random
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SkillCategory(Enum):
    MARINE_ELECTRONICS = "marine_electronics"
    ENGINE_REPAIR = "engine_repair"
    BOAT_BUILDING = "boat_building"
    NAVIGATION_SYSTEMS = "navigation_systems"
    SAFETY_EQUIPMENT = "safety_equipment"
    FISHING_GEAR_SETUP = "fishing_gear_setup"
    WELDING_FABRICATION = "welding_fabrication"
    PLUMBING_SYSTEMS = "plumbing_systems"
    ELECTRICAL_WORK = "electrical_work"
    FIBERGLASS_REPAIR = "fiberglass_repair"
    RIGGING_WORK = "rigging_work"
    UPHOLSTERY_WORK = "upholstery_work"

class JobUrgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class JobStatus(Enum):
    POSTED = "posted"
    BIDS_RECEIVED = "bids_received"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"

class PaymentType(Enum):
    HOURLY = "hourly"
    FIXED_PRICE = "fixed_price"
    PER_ITEM = "per_item"
    MATERIALS_PLUS_LABOR = "materials_plus_labor"

class AssemblerLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"

@dataclass
class JobRequirement:
    requirement_id: str
    job_id: str
    requirement_type: str  # skill, tool, certification, experience
    description: str
    is_mandatory: bool
    verification_required: bool

@dataclass
class JobBid:
    bid_id: str
    job_id: str
    assembler_id: str
    amount: float
    estimated_hours: Optional[float]
    completion_time: int  # days
    message: str
    materials_included: bool
    warranty_offered: Optional[str]
    portfolio_items: List[str]  # references to previous work
    submitted_at: datetime
    status: str  # pending, accepted, declined, withdrawn

@dataclass
class AssemblerProfile:
    assembler_id: str
    user_id: str
    business_name: Optional[str]
    first_name: str
    last_name: str
    email: str
    phone: str
    location: Tuple[float, float]  # lat, lon
    location_name: str
    travel_radius: int  # kilometers
    skills: List[SkillCategory]
    skill_levels: Dict[str, AssemblerLevel]  # skill -> level
    certifications: List[str]
    years_experience: int
    hourly_rate_range: Tuple[float, float]
    availability_status: str  # available, busy, unavailable
    rating: float
    total_reviews: int
    completed_jobs: int
    bio: str
    portfolio_urls: List[str]
    tools_owned: List[str]
    insurance_verified: bool
    background_check: bool
    created_at: datetime
    last_active: datetime

@dataclass
class AssemblyJob:
    job_id: str
    client_id: str
    client_name: str
    title: str
    description: str
    category: SkillCategory
    subcategory: str
    location: Tuple[float, float]
    location_name: str
    budget_range: Tuple[float, float]
    payment_type: PaymentType
    urgency: JobUrgency
    estimated_duration: Optional[int]  # hours
    requirements: List[JobRequirement]
    materials_provided: bool
    materials_list: List[str]
    photos: List[str]
    status: JobStatus
    posted_at: datetime
    desired_completion: Optional[datetime]
    bids: List[JobBid]
    assigned_assembler: Optional[str]
    actual_start_date: Optional[datetime]
    actual_completion_date: Optional[datetime]
    client_review: Optional[Dict[str, Any]]
    assembler_review: Optional[Dict[str, Any]]

@dataclass
class AssemblerReview:
    review_id: str
    job_id: str
    assembler_id: str
    client_id: str
    rating: int  # 1-5 stars
    title: str
    content: str
    work_quality: int  # 1-5
    communication: int  # 1-5
    timeliness: int  # 1-5
    would_recommend: bool
    photos: List[str]
    created_at: datetime

class AssemblerWantedBoards:
    def __init__(self, db_path: str = "marketplace_v2_assemblers.db"):
        self.db_path = db_path
        self.jobs: Dict[str, AssemblyJob] = {}
        self.assemblers: Dict[str, AssemblerProfile] = {}
        self.reviews: Dict[str, AssemblerReview] = {}
        
        # Initialize database
        self._init_database()
        
        # Load sample data
        self._load_sample_data()
        
        # Start background matching
        self.matching_thread = threading.Thread(target=self._run_matching_engine, daemon=True)
        self.matching_thread.start()
    
    def _init_database(self):
        """Initialize SQLite database for assembler boards"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assembly_jobs (
                job_id TEXT PRIMARY KEY,
                client_id TEXT,
                client_name TEXT,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                subcategory TEXT,
                latitude REAL,
                longitude REAL,
                location_name TEXT,
                budget_min REAL,
                budget_max REAL,
                payment_type TEXT,
                urgency TEXT,
                estimated_duration INTEGER,
                materials_provided BOOLEAN,
                materials_list TEXT,
                photos TEXT,
                status TEXT,
                posted_at TIMESTAMP,
                desired_completion TIMESTAMP,
                assigned_assembler TEXT,
                actual_start_date TIMESTAMP,
                actual_completion_date TIMESTAMP
            )
        ''')
        
        # Job requirements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_requirements (
                requirement_id TEXT PRIMARY KEY,
                job_id TEXT,
                requirement_type TEXT,
                description TEXT,
                is_mandatory BOOLEAN,
                verification_required BOOLEAN,
                FOREIGN KEY (job_id) REFERENCES assembly_jobs (job_id)
            )
        ''')
        
        # Job bids table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_bids (
                bid_id TEXT PRIMARY KEY,
                job_id TEXT,
                assembler_id TEXT,
                amount REAL,
                estimated_hours REAL,
                completion_time INTEGER,
                message TEXT,
                materials_included BOOLEAN,
                warranty_offered TEXT,
                portfolio_items TEXT,
                submitted_at TIMESTAMP,
                status TEXT,
                FOREIGN KEY (job_id) REFERENCES assembly_jobs (job_id),
                FOREIGN KEY (assembler_id) REFERENCES assembler_profiles (assembler_id)
            )
        ''')
        
        # Assembler profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assembler_profiles (
                assembler_id TEXT PRIMARY KEY,
                user_id TEXT,
                business_name TEXT,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone TEXT,
                latitude REAL,
                longitude REAL,
                location_name TEXT,
                travel_radius INTEGER,
                skills TEXT,
                skill_levels TEXT,
                certifications TEXT,
                years_experience INTEGER,
                hourly_rate_min REAL,
                hourly_rate_max REAL,
                availability_status TEXT,
                rating REAL,
                total_reviews INTEGER,
                completed_jobs INTEGER,
                bio TEXT,
                portfolio_urls TEXT,
                tools_owned TEXT,
                insurance_verified BOOLEAN,
                background_check BOOLEAN,
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # Assembler reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assembler_reviews (
                review_id TEXT PRIMARY KEY,
                job_id TEXT,
                assembler_id TEXT,
                client_id TEXT,
                rating INTEGER,
                title TEXT,
                content TEXT,
                work_quality INTEGER,
                communication INTEGER,
                timeliness INTEGER,
                would_recommend BOOLEAN,
                photos TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES assembly_jobs (job_id),
                FOREIGN KEY (assembler_id) REFERENCES assembler_profiles (assembler_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_category ON assembly_jobs(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_location ON assembly_jobs(latitude, longitude)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON assembly_jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_assemblers_location ON assembler_profiles(latitude, longitude)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_assemblers_skills ON assembler_profiles(skills)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bids_job ON job_bids(job_id)')
        
        conn.commit()
        conn.close()
    
    def _load_sample_data(self):
        """Load sample assemblers and jobs"""
        
        # Sample assembler profiles
        sample_assemblers = [
            {
                "business_name": "Marine Electronics Pro",
                "first_name": "John",
                "last_name": "Martinez",
                "email": "john@marineelectronicspro.com",
                "location": (47.6062, -122.3321),  # Seattle
                "location_name": "Seattle, WA",
                "skills": [SkillCategory.MARINE_ELECTRONICS, SkillCategory.NAVIGATION_SYSTEMS],
                "skill_levels": {"marine_electronics": AssemblerLevel.EXPERT, "navigation_systems": AssemblerLevel.ADVANCED},
                "years_experience": 12,
                "hourly_rate_range": (75.0, 125.0),
                "certifications": ["NMEA 2000 Certified", "Furuno Certified Technician"],
                "bio": "Specialized marine electronics installation with over 12 years experience in commercial and recreational vessels."
            },
            {
                "business_name": "Coastal Engine Works",
                "first_name": "Sarah",
                "last_name": "Thompson",
                "email": "sarah@coastalengine.com",
                "location": (45.5152, -122.6784),  # Portland
                "location_name": "Portland, OR",
                "skills": [SkillCategory.ENGINE_REPAIR, SkillCategory.PLUMBING_SYSTEMS],
                "skill_levels": {"engine_repair": AssemblerLevel.MASTER, "plumbing_systems": AssemblerLevel.ADVANCED},
                "years_experience": 18,
                "hourly_rate_range": (85.0, 140.0),
                "certifications": ["Mercury Certified", "Yamaha Master Technician"],
                "bio": "Master marine engine technician specializing in outboard and inboard engine repair and installation."
            },
            {
                "business_name": None,
                "first_name": "Mike",
                "last_name": "Rodriguez",
                "email": "mike.rodriguez@email.com",
                "location": (42.3601, -71.0589),  # Boston
                "location_name": "Boston, MA",
                "skills": [SkillCategory.FIBERGLASS_REPAIR, SkillCategory.BOAT_BUILDING],
                "skill_levels": {"fiberglass_repair": AssemblerLevel.EXPERT, "boat_building": AssemblerLevel.INTERMEDIATE},
                "years_experience": 8,
                "hourly_rate_range": (55.0, 85.0),
                "certifications": ["Fiberglass Repair Certified"],
                "bio": "Experienced fiberglass repair specialist with background in custom boat building."
            },
            {
                "business_name": "Atlantic Rigging Solutions",
                "first_name": "Lisa",
                "last_name": "Chen",
                "email": "lisa@atlanticrigging.com",
                "location": (25.7617, -80.1918),  # Miami
                "location_name": "Miami, FL",
                "skills": [SkillCategory.RIGGING_WORK, SkillCategory.SAFETY_EQUIPMENT],
                "skill_levels": {"rigging_work": AssemblerLevel.EXPERT, "safety_equipment": AssemblerLevel.ADVANCED},
                "years_experience": 10,
                "hourly_rate_range": (65.0, 100.0),
                "certifications": ["ABYC Certified", "Professional Rigger"],
                "bio": "Professional rigger specializing in racing and cruising sailboat rigging installation and maintenance."
            },
            {
                "business_name": "Pacific Welding & Fab",
                "first_name": "David",
                "last_name": "Williams",
                "email": "david@pacificwelding.com",
                "location": (37.7749, -122.4194),  # San Francisco
                "location_name": "San Francisco, CA",
                "skills": [SkillCategory.WELDING_FABRICATION, SkillCategory.ELECTRICAL_WORK],
                "skill_levels": {"welding_fabrication": AssemblerLevel.MASTER, "electrical_work": AssemblerLevel.INTERMEDIATE},
                "years_experience": 15,
                "hourly_rate_range": (70.0, 110.0),
                "certifications": ["AWS Certified Welder", "Marine Electrical"],
                "bio": "Master welder and fabricator specializing in custom marine installations and repairs."
            }
        ]
        
        for i, assembler_data in enumerate(sample_assemblers):
            assembler_id = f"assembler_{i+1:03d}"
            
            assembler = AssemblerProfile(
                assembler_id=assembler_id,
                user_id=f"user_{assembler_id}",
                business_name=assembler_data["business_name"],
                first_name=assembler_data["first_name"],
                last_name=assembler_data["last_name"],
                email=assembler_data["email"],
                phone=f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                location=assembler_data["location"],
                location_name=assembler_data["location_name"],
                travel_radius=random.randint(50, 200),
                skills=assembler_data["skills"],
                skill_levels=assembler_data["skill_levels"],
                certifications=assembler_data["certifications"],
                years_experience=assembler_data["years_experience"],
                hourly_rate_range=assembler_data["hourly_rate_range"],
                availability_status="available",
                rating=random.uniform(4.2, 4.9),
                total_reviews=random.randint(15, 75),
                completed_jobs=random.randint(50, 200),
                bio=assembler_data["bio"],
                portfolio_urls=[f"https://portfolio.com/{assembler_id}/project{j}" for j in range(1, 4)],
                tools_owned=["multimeter", "drill", "impact_driver", "soldering_iron"],
                insurance_verified=True,
                background_check=True,
                created_at=datetime.now() - timedelta(days=random.randint(30, 365)),
                last_active=datetime.now() - timedelta(hours=random.randint(1, 48))
            )
            
            self.assemblers[assembler_id] = assembler
        
        # Sample assembly jobs
        sample_jobs = [
            {
                "title": "Install Furuno NavNet TZtouch3 Chartplotter",
                "category": SkillCategory.MARINE_ELECTRONICS,
                "subcategory": "Chartplotter Installation",
                "description": "Need professional installation of new Furuno NavNet TZtouch3 16-inch display on 45ft sportfisher. Includes NMEA 2000 network integration, radar connection, and sonar transducer wiring.",
                "location": (47.5480, -122.3390),  # Seattle area
                "location_name": "Shilshole Bay Marina, Seattle, WA",
                "budget_range": (1200.0, 1800.0),
                "urgency": JobUrgency.MEDIUM,
                "estimated_duration": 12,
                "requirements": [
                    ("skill", "NMEA 2000 network experience required", True, True),
                    ("certification", "Furuno certification preferred", False, True),
                    ("tool", "Multimeter and network tester", True, False)
                ]
            },
            {
                "title": "Yamaha F250 Outboard Service and Winterization",
                "category": SkillCategory.ENGINE_REPAIR,
                "subcategory": "Outboard Service",
                "description": "Annual service and winterization of twin Yamaha F250 outboards on 28ft center console. Includes oil change, lower unit service, fuel system treatment, and storage preparation.",
                "location": (42.3501, -70.9830),  # Boston area
                "location_name": "Constitution Marina, Boston, MA",
                "budget_range": (800.0, 1200.0),
                "urgency": JobUrgency.HIGH,
                "estimated_duration": 8,
                "requirements": [
                    ("certification", "Yamaha certified technician", True, True),
                    ("experience", "5+ years outboard service", True, False),
                    ("tool", "Complete service tools", True, False)
                ]
            },
            {
                "title": "Fiberglass Hull Repair - Gelcoat Damage",
                "category": SkillCategory.FIBERGLASS_REPAIR,
                "subcategory": "Hull Repair",
                "description": "Repair gelcoat damage on port side hull of 32ft sailboat. Approximately 2ft x 1ft area with minor delamination. Need color matching and professional finish.",
                "location": (25.7907, -80.1300),  # Miami area
                "location_name": "Miami Beach Marina, Miami, FL",
                "budget_range": (600.0, 900.0),
                "urgency": JobUrgency.LOW,
                "estimated_duration": 6,
                "requirements": [
                    ("skill", "Gelcoat repair and color matching", True, True),
                    ("experience", "Hull repair experience", True, False),
                    ("tool", "Spray equipment or hand tools", True, False)
                ]
            },
            {
                "title": "Standing Rigging Replacement - 38ft Sailboat",
                "category": SkillCategory.RIGGING_WORK,
                "subcategory": "Standing Rigging",
                "description": "Complete standing rigging replacement on 38ft cruising sailboat. Includes new shrouds, stays, turnbuckles, and hardware. Mast must be pulled and re-stepped.",
                "location": (37.8044, -122.4758),  # San Francisco Bay
                "location_name": "Sausalito Yacht Harbor, Sausalito, CA",
                "budget_range": (2500.0, 4000.0),
                "urgency": JobUrgency.MEDIUM,
                "estimated_duration": 24,
                "requirements": [
                    ("certification", "Professional rigger certification", True, True),
                    ("experience", "Mast stepping experience", True, True),
                    ("tool", "Rigging tools and crane access", True, False)
                ]
            },
            {
                "title": "Custom Aluminum Radar Arch Fabrication",
                "category": SkillCategory.WELDING_FABRICATION,
                "subcategory": "Custom Fabrication",
                "description": "Design and fabricate custom aluminum radar arch for 26ft fishing boat. Need to accommodate radar, navigation lights, and rod holders. Powder coating included.",
                "location": (45.5420, -122.7940),  # Portland area
                "location_name": "Portland Yacht Club, Portland, OR",
                "budget_range": (1800.0, 2800.0),
                "urgency": JobUrgency.LOW,
                "estimated_duration": 16,
                "requirements": [
                    ("skill", "Aluminum welding (TIG preferred)", True, True),
                    ("experience", "Marine fabrication experience", True, False),
                    ("tool", "TIG welder and fabrication tools", True, False)
                ]
            }
        ]
        
        for i, job_data in enumerate(sample_jobs):
            job_id = f"job_{i+1:03d}"
            
            # Create requirements
            requirements = [
                JobRequirement(
                    requirement_id=f"req_{job_id}_{j}",
                    job_id=job_id,
                    requirement_type=req[0],
                    description=req[1],
                    is_mandatory=req[2],
                    verification_required=req[3] if len(req) > 3 else False
                )
                for j, req in enumerate(job_data["requirements"])
            ]
            
            # Create some sample bids
            bids = []
            if random.random() > 0.3:  # 70% of jobs have bids
                num_bids = random.randint(1, 4)
                for bid_num in range(num_bids):
                    bid_id = f"bid_{job_id}_{bid_num+1}"
                    assembler_ids = list(self.assemblers.keys())
                    assembler_id = random.choice(assembler_ids)
                    
                    bid = JobBid(
                        bid_id=bid_id,
                        job_id=job_id,
                        assembler_id=assembler_id,
                        amount=random.uniform(job_data["budget_range"][0], job_data["budget_range"][1]),
                        estimated_hours=job_data["estimated_duration"] + random.randint(-2, 4),
                        completion_time=random.randint(3, 14),
                        message=f"I have extensive experience with this type of work. Can complete within {random.randint(3, 7)} days.",
                        materials_included=random.choice([True, False]),
                        warranty_offered=random.choice([None, "90 days", "6 months", "1 year"]),
                        portfolio_items=[f"project_{assembler_id}_{k}" for k in range(1, 3)],
                        submitted_at=datetime.now() - timedelta(hours=random.randint(1, 48)),
                        status="pending"
                    )
                    bids.append(bid)
            
            job = AssemblyJob(
                job_id=job_id,
                client_id=f"client_{random.randint(1000, 9999)}",
                client_name=f"Client {chr(65 + i)}",
                title=job_data["title"],
                description=job_data["description"],
                category=job_data["category"],
                subcategory=job_data["subcategory"],
                location=job_data["location"],
                location_name=job_data["location_name"],
                budget_range=job_data["budget_range"],
                payment_type=PaymentType.FIXED_PRICE,
                urgency=job_data["urgency"],
                estimated_duration=job_data["estimated_duration"],
                requirements=requirements,
                materials_provided=random.choice([True, False]),
                materials_list=["mounting hardware", "wiring", "connectors"] if random.choice([True, False]) else [],
                photos=[f"photo_{job_id}_{j}.jpg" for j in range(1, random.randint(2, 5))],
                status=JobStatus.POSTED if not bids else JobStatus.BIDS_RECEIVED,
                posted_at=datetime.now() - timedelta(days=random.randint(1, 14)),
                desired_completion=datetime.now() + timedelta(days=random.randint(7, 30)),
                bids=bids,
                assigned_assembler=None,
                actual_start_date=None,
                actual_completion_date=None,
                client_review=None,
                assembler_review=None
            )
            
            self.jobs[job_id] = job
        
        # Save to database
        self._save_data_to_db()
    
    def _save_data_to_db(self):
        """Save all data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save assembler profiles
        for assembler in self.assemblers.values():
            cursor.execute('''
                INSERT OR REPLACE INTO assembler_profiles 
                (assembler_id, user_id, business_name, first_name, last_name, email, phone,
                 latitude, longitude, location_name, travel_radius, skills, skill_levels,
                 certifications, years_experience, hourly_rate_min, hourly_rate_max,
                 availability_status, rating, total_reviews, completed_jobs, bio,
                 portfolio_urls, tools_owned, insurance_verified, background_check,
                 created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assembler.assembler_id, assembler.user_id, assembler.business_name,
                assembler.first_name, assembler.last_name, assembler.email, assembler.phone,
                assembler.location[0], assembler.location[1], assembler.location_name,
                assembler.travel_radius, json.dumps([skill.value for skill in assembler.skills]),
                json.dumps({k: v.value for k, v in assembler.skill_levels.items()}),
                json.dumps(assembler.certifications), assembler.years_experience,
                assembler.hourly_rate_range[0], assembler.hourly_rate_range[1],
                assembler.availability_status, assembler.rating, assembler.total_reviews,
                assembler.completed_jobs, assembler.bio, json.dumps(assembler.portfolio_urls),
                json.dumps(assembler.tools_owned), assembler.insurance_verified,
                assembler.background_check, assembler.created_at, assembler.last_active
            ))
        
        # Save jobs
        for job in self.jobs.values():
            cursor.execute('''
                INSERT OR REPLACE INTO assembly_jobs 
                (job_id, client_id, client_name, title, description, category, subcategory,
                 latitude, longitude, location_name, budget_min, budget_max, payment_type,
                 urgency, estimated_duration, materials_provided, materials_list, photos,
                 status, posted_at, desired_completion, assigned_assembler, actual_start_date,
                 actual_completion_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job.job_id, job.client_id, job.client_name, job.title, job.description,
                job.category.value, job.subcategory, job.location[0], job.location[1],
                job.location_name, job.budget_range[0], job.budget_range[1],
                job.payment_type.value, job.urgency.value, job.estimated_duration,
                job.materials_provided, json.dumps(job.materials_list),
                json.dumps(job.photos), job.status.value, job.posted_at,
                job.desired_completion, job.assigned_assembler, job.actual_start_date,
                job.actual_completion_date
            ))
            
            # Save job requirements
            for req in job.requirements:
                cursor.execute('''
                    INSERT OR REPLACE INTO job_requirements 
                    (requirement_id, job_id, requirement_type, description, is_mandatory, verification_required)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    req.requirement_id, req.job_id, req.requirement_type,
                    req.description, req.is_mandatory, req.verification_required
                ))
            
            # Save job bids
            for bid in job.bids:
                cursor.execute('''
                    INSERT OR REPLACE INTO job_bids 
                    (bid_id, job_id, assembler_id, amount, estimated_hours, completion_time,
                     message, materials_included, warranty_offered, portfolio_items,
                     submitted_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    bid.bid_id, bid.job_id, bid.assembler_id, bid.amount,
                    bid.estimated_hours, bid.completion_time, bid.message,
                    bid.materials_included, bid.warranty_offered,
                    json.dumps(bid.portfolio_items), bid.submitted_at, bid.status
                ))
        
        conn.commit()
        conn.close()
    
    async def post_job(self, client_id: str, job_data: Dict[str, Any]) -> str:
        """Post a new assembly job"""
        job_id = f"job_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Create requirements from job data
        requirements = []
        for i, req_data in enumerate(job_data.get("requirements", [])):
            requirement = JobRequirement(
                requirement_id=f"req_{job_id}_{i}",
                job_id=job_id,
                requirement_type=req_data.get("type", "skill"),
                description=req_data["description"],
                is_mandatory=req_data.get("mandatory", False),
                verification_required=req_data.get("verification_required", False)
            )
            requirements.append(requirement)
        
        job = AssemblyJob(
            job_id=job_id,
            client_id=client_id,
            client_name=job_data.get("client_name", "Anonymous Client"),
            title=job_data["title"],
            description=job_data["description"],
            category=SkillCategory(job_data["category"]),
            subcategory=job_data.get("subcategory", ""),
            location=tuple(job_data["location"]),
            location_name=job_data["location_name"],
            budget_range=tuple(job_data["budget_range"]),
            payment_type=PaymentType(job_data.get("payment_type", "fixed_price")),
            urgency=JobUrgency(job_data.get("urgency", "medium")),
            estimated_duration=job_data.get("estimated_duration"),
            requirements=requirements,
            materials_provided=job_data.get("materials_provided", False),
            materials_list=job_data.get("materials_list", []),
            photos=job_data.get("photos", []),
            status=JobStatus.POSTED,
            posted_at=datetime.now(),
            desired_completion=datetime.fromisoformat(job_data["desired_completion"]) if job_data.get("desired_completion") else None,
            bids=[],
            assigned_assembler=None,
            actual_start_date=None,
            actual_completion_date=None,
            client_review=None,
            assembler_review=None
        )
        
        self.jobs[job_id] = job
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO assembly_jobs 
            (job_id, client_id, client_name, title, description, category, subcategory,
             latitude, longitude, location_name, budget_min, budget_max, payment_type,
             urgency, estimated_duration, materials_provided, materials_list, photos,
             status, posted_at, desired_completion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.job_id, job.client_id, job.client_name, job.title, job.description,
            job.category.value, job.subcategory, job.location[0], job.location[1],
            job.location_name, job.budget_range[0], job.budget_range[1],
            job.payment_type.value, job.urgency.value, job.estimated_duration,
            job.materials_provided, json.dumps(job.materials_list),
            json.dumps(job.photos), job.status.value, job.posted_at,
            job.desired_completion
        ))
        conn.commit()
        conn.close()
        
        logger.info(f"Posted new job: {job.title} ({job_id})")
        
        # Trigger matching for new job
        await self._notify_matching_assemblers(job_id)
        
        return job_id
    
    async def submit_bid(self, job_id: str, assembler_id: str, bid_data: Dict[str, Any]) -> str:
        """Submit a bid for a job"""
        if job_id not in self.jobs or assembler_id not in self.assemblers:
            raise ValueError("Invalid job ID or assembler ID")
        
        bid_id = f"bid_{job_id}_{assembler_id}_{int(time.time())}"
        
        bid = JobBid(
            bid_id=bid_id,
            job_id=job_id,
            assembler_id=assembler_id,
            amount=bid_data["amount"],
            estimated_hours=bid_data.get("estimated_hours"),
            completion_time=bid_data["completion_time"],
            message=bid_data["message"],
            materials_included=bid_data.get("materials_included", False),
            warranty_offered=bid_data.get("warranty_offered"),
            portfolio_items=bid_data.get("portfolio_items", []),
            submitted_at=datetime.now(),
            status="pending"
        )
        
        # Add bid to job
        self.jobs[job_id].bids.append(bid)
        if self.jobs[job_id].status == JobStatus.POSTED:
            self.jobs[job_id].status = JobStatus.BIDS_RECEIVED
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO job_bids 
            (bid_id, job_id, assembler_id, amount, estimated_hours, completion_time,
             message, materials_included, warranty_offered, portfolio_items,
             submitted_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bid.bid_id, bid.job_id, bid.assembler_id, bid.amount,
            bid.estimated_hours, bid.completion_time, bid.message,
            bid.materials_included, bid.warranty_offered,
            json.dumps(bid.portfolio_items), bid.submitted_at, bid.status
        ))
        conn.commit()
        conn.close()
        
        logger.info(f"Bid submitted for job {job_id} by assembler {assembler_id}")
        return bid_id
    
    def search_jobs(self, filters: Dict[str, Any] = None, location: Tuple[float, float] = None, 
                   radius_km: int = 50) -> List[AssemblyJob]:
        """Search for assembly jobs"""
        jobs = list(self.jobs.values())
        
        # Filter by status (only show posted and bids_received jobs)
        jobs = [job for job in jobs if job.status in [JobStatus.POSTED, JobStatus.BIDS_RECEIVED]]
        
        if filters:
            # Filter by category
            if "category" in filters:
                jobs = [job for job in jobs if job.category == SkillCategory(filters["category"])]
            
            # Filter by budget range
            if "budget_min" in filters:
                jobs = [job for job in jobs if job.budget_range[1] >= filters["budget_min"]]
            if "budget_max" in filters:
                jobs = [job for job in jobs if job.budget_range[0] <= filters["budget_max"]]
            
            # Filter by urgency
            if "urgency" in filters:
                jobs = [job for job in jobs if job.urgency == JobUrgency(filters["urgency"])]
        
        # Filter by location if provided
        if location:
            lat, lon = location
            jobs = [
                job for job in jobs
                if self._calculate_distance(lat, lon, job.location[0], job.location[1]) <= radius_km
            ]
        
        # Sort by posted date (newest first) and urgency
        urgency_weight = {JobUrgency.URGENT: 4, JobUrgency.HIGH: 3, JobUrgency.MEDIUM: 2, JobUrgency.LOW: 1}
        jobs.sort(key=lambda j: (urgency_weight[j.urgency], j.posted_at), reverse=True)
        
        return jobs
    
    def search_assemblers(self, filters: Dict[str, Any] = None, location: Tuple[float, float] = None,
                         radius_km: int = 100) -> List[AssemblerProfile]:
        """Search for assemblers"""
        assemblers = list(self.assemblers.values())
        
        # Filter by availability
        assemblers = [a for a in assemblers if a.availability_status == "available"]
        
        if filters:
            # Filter by skills
            if "skills" in filters:
                required_skills = [SkillCategory(skill) for skill in filters["skills"]]
                assemblers = [
                    a for a in assemblers
                    if any(skill in a.skills for skill in required_skills)
                ]
            
            # Filter by minimum rating
            if "min_rating" in filters:
                assemblers = [a for a in assemblers if a.rating >= filters["min_rating"]]
            
            # Filter by experience
            if "min_experience" in filters:
                assemblers = [a for a in assemblers if a.years_experience >= filters["min_experience"]]
            
            # Filter by rate range
            if "max_rate" in filters:
                assemblers = [a for a in assemblers if a.hourly_rate_range[0] <= filters["max_rate"]]
        
        # Filter by location if provided
        if location:
            lat, lon = location
            assemblers = [
                a for a in assemblers
                if self._calculate_distance(lat, lon, a.location[0], a.location[1]) <= min(radius_km, a.travel_radius)
            ]
        
        # Sort by rating and experience
        assemblers.sort(key=lambda a: (a.rating, a.years_experience), reverse=True)
        
        return assemblers
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    async def _notify_matching_assemblers(self, job_id: str):
        """Notify assemblers who match the job requirements"""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        matching_assemblers = []
        
        for assembler in self.assemblers.values():
            # Check if assembler has required skills
            if job.category in assembler.skills:
                # Check location
                distance = self._calculate_distance(
                    job.location[0], job.location[1],
                    assembler.location[0], assembler.location[1]
                )
                
                if distance <= assembler.travel_radius:
                    # Check if assembler can meet budget expectations
                    if assembler.hourly_rate_range[0] <= job.budget_range[1] / max(1, job.estimated_duration or 8):
                        matching_assemblers.append(assembler)
        
        logger.info(f"Found {len(matching_assemblers)} matching assemblers for job {job_id}")
        
        # In a real system, would send notifications here
        for assembler in matching_assemblers:
            logger.info(f"Notified assembler {assembler.assembler_id} about job {job_id}")
    
    def get_job_details(self, job_id: str) -> Optional[AssemblyJob]:
        """Get detailed job information"""
        return self.jobs.get(job_id)
    
    def get_assembler_profile(self, assembler_id: str) -> Optional[AssemblerProfile]:
        """Get assembler profile"""
        return self.assemblers.get(assembler_id)
    
    def get_job_bids(self, job_id: str) -> List[JobBid]:
        """Get all bids for a job"""
        if job_id in self.jobs:
            return self.jobs[job_id].bids
        return []
    
    def get_assembler_jobs(self, assembler_id: str, status: Optional[JobStatus] = None) -> List[AssemblyJob]:
        """Get jobs assigned to or bid on by an assembler"""
        jobs = []
        
        for job in self.jobs.values():
            # Check if assigned to assembler
            if job.assigned_assembler == assembler_id:
                if not status or job.status == status:
                    jobs.append(job)
            # Check if assembler has bid on job
            elif any(bid.assembler_id == assembler_id for bid in job.bids):
                if not status or job.status == status:
                    jobs.append(job)
        
        return sorted(jobs, key=lambda j: j.posted_at, reverse=True)
    
    def _run_matching_engine(self):
        """Background matching engine"""
        while True:
            try:
                self._update_job_recommendations()
                time.sleep(1800)  # Run every 30 minutes
            except Exception as e:
                logger.error(f"Matching engine error: {e}")
    
    def _update_job_recommendations(self):
        """Update job recommendations for assemblers"""
        for assembler in self.assemblers.values():
            if assembler.availability_status == "available":
                # Find recommended jobs
                recommended_jobs = self.search_jobs(
                    filters={"category": assembler.skills[0].value} if assembler.skills else None,
                    location=assembler.location,
                    radius_km=assembler.travel_radius
                )
                
                # Store recommendations (in real system, would update database)
                if recommended_jobs:
                    logger.debug(f"Found {len(recommended_jobs)} recommended jobs for {assembler.assembler_id}")
    
    def get_board_analytics(self) -> Dict[str, Any]:
        """Get assembler board analytics"""
        total_jobs = len(self.jobs)
        active_jobs = len([j for j in self.jobs.values() if j.status in [JobStatus.POSTED, JobStatus.BIDS_RECEIVED]])
        total_assemblers = len(self.assemblers)
        available_assemblers = len([a for a in self.assemblers.values() if a.availability_status == "available"])
        
        # Job categories
        category_counts = {}
        for job in self.jobs.values():
            cat = job.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Average bid counts
        bid_counts = [len(job.bids) for job in self.jobs.values()]
        avg_bids_per_job = sum(bid_counts) / len(bid_counts) if bid_counts else 0
        
        # Budget ranges
        budgets = [(job.budget_range[0] + job.budget_range[1]) / 2 for job in self.jobs.values()]
        avg_budget = sum(budgets) / len(budgets) if budgets else 0
        
        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_assemblers": total_assemblers,
            "available_assemblers": available_assemblers,
            "category_distribution": category_counts,
            "average_bids_per_job": avg_bids_per_job,
            "average_job_budget": avg_budget,
            "job_statuses": {status.value: len([j for j in self.jobs.values() if j.status == status]) 
                           for status in JobStatus}
        }

# Example usage and testing
async def main():
    boards = AssemblerWantedBoards()
    
    print("=== Marketplace v2 - Assembler Wanted Boards ===")
    
    # Search for jobs
    print("\n=== Available Jobs ===")
    jobs = boards.search_jobs(location=(47.6062, -122.3321), radius_km=100)
    for job in jobs[:3]:
        print(f"- {job.title}")
        print(f"  Budget: ${job.budget_range[0]:.0f} - ${job.budget_range[1]:.0f}")
        print(f"  Location: {job.location_name}")
        print(f"  Bids: {len(job.bids)}")
    
    # Search for assemblers
    print("\n=== Available Assemblers ===")
    assemblers = boards.search_assemblers(
        filters={"skills": ["marine_electronics"]},
        location=(47.6062, -122.3321),
        radius_km=200
    )
    for assembler in assemblers[:3]:
        name = f"{assembler.first_name} {assembler.last_name}"
        if assembler.business_name:
            name = f"{assembler.business_name} ({name})"
        print(f"- {name}")
        print(f"  Rating: {assembler.rating:.1f}/5.0 ({assembler.total_reviews} reviews)")
        print(f"  Experience: {assembler.years_experience} years")
        print(f"  Rate: ${assembler.hourly_rate_range[0]:.0f}-${assembler.hourly_rate_range[1]:.0f}/hr")
    
    # Post a new job
    print("\n=== Posting New Job ===")
    new_job_data = {
        "title": "Install Garmin Chartplotter",
        "description": "Need installation of new Garmin chartplotter with NMEA integration",
        "category": "marine_electronics",
        "location": (47.6062, -122.3321),
        "location_name": "Seattle, WA",
        "budget_range": (800, 1200),
        "estimated_duration": 6,
        "materials_provided": True,
        "desired_completion": (datetime.now() + timedelta(days=14)).isoformat(),
        "requirements": [
            {"description": "NMEA 2000 experience", "mandatory": True, "type": "skill"}
        ]
    }
    
    job_id = await boards.post_job("client_12345", new_job_data)
    print(f"Posted new job: {job_id}")
    
    # Submit a bid
    if assemblers:
        assembler_id = assemblers[0].assembler_id
        bid_data = {
            "amount": 950.0,
            "estimated_hours": 6,
            "completion_time": 3,
            "message": "I have 12 years experience with marine electronics installation. Can complete this job within 3 days.",
            "materials_included": False,
            "warranty_offered": "90 days"
        }
        
        bid_id = await boards.submit_bid(job_id, assembler_id, bid_data)
        print(f"Submitted bid: {bid_id}")
    
    # Get analytics
    analytics = boards.get_board_analytics()
    print(f"\n=== Board Analytics ===")
    print(f"Active Jobs: {analytics['active_jobs']}")
    print(f"Available Assemblers: {analytics['available_assemblers']}")
    print(f"Average Bids per Job: {analytics['average_bids_per_job']:.1f}")
    print(f"Average Job Budget: ${analytics['average_job_budget']:.0f}")

if __name__ == "__main__":
    asyncio.run(main())