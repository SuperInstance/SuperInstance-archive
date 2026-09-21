#!/usr/bin/env python3
"""
RFP/RFQ Management System
Comprehensive request for proposal and quotation management
"""

import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import re

logger = logging.getLogger(__name__)

class RFPStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    AWARDED = "awarded"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

class RFPType(Enum):
    RFP = "rfp"  # Request for Proposal
    RFQ = "rfq"  # Request for Quotation
    IFB = "ifb"  # Invitation for Bid
    RFI = "rfi"  # Request for Information
    SOURCES_SOUGHT = "sources_sought"

class ContractType(Enum):
    FIXED_PRICE = "fixed_price"
    COST_PLUS = "cost_plus"
    TIME_MATERIALS = "time_materials"
    INDEFINITE_DELIVERY = "indefinite_delivery"

class RFPManagementSystem:
    def __init__(self):
        self.db_path = "data/rfp_management.db"
        self.sam_api_key = None
        self.notification_settings = {}

    async def initialize(self):
        """Initialize RFP management system"""
        try:
            await self._create_database_schema()
            await self._setup_notification_settings()
            await self._load_agency_mappings()
            logger.info("RFP Management System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RFP Management System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for RFP management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # RFP opportunities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfp_opportunities (
                id TEXT PRIMARY KEY,
                rfp_number TEXT NOT NULL,
                title TEXT NOT NULL,
                agency TEXT NOT NULL,
                office TEXT,
                description TEXT,
                rfp_type TEXT NOT NULL,
                contract_type TEXT,
                naics_code TEXT,
                set_aside_type TEXT,
                place_of_performance TEXT,
                estimated_value_min REAL,
                estimated_value_max REAL,
                release_date TEXT,
                response_deadline TEXT,
                questions_deadline TEXT,
                contact_info TEXT,
                solicitation_url TEXT,
                attachments TEXT,
                requirements TEXT,
                evaluation_criteria TEXT,
                keywords TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # RFP responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfp_responses (
                id TEXT PRIMARY KEY,
                rfp_id TEXT NOT NULL,
                response_number TEXT,
                team_members TEXT,
                technical_approach TEXT,
                management_approach TEXT,
                past_performance TEXT,
                proposed_solution TEXT,
                cost_proposal_id TEXT,
                compliance_checklist TEXT,
                submission_method TEXT,
                submission_date TEXT,
                status TEXT NOT NULL,
                bid_decision TEXT,
                win_probability REAL DEFAULT 0.0,
                competitor_analysis TEXT,
                lessons_learned TEXT,
                files_submitted TEXT,
                audit_trail TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (rfp_id) REFERENCES rfp_opportunities (id)
            )
        """)
        
        # Proposal team table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proposal_teams (
                id TEXT PRIMARY KEY,
                rfp_response_id TEXT NOT NULL,
                team_lead TEXT NOT NULL,
                technical_lead TEXT,
                program_manager TEXT,
                contracts_lead TEXT,
                team_members TEXT,
                roles_responsibilities TEXT,
                experience_matrix TEXT,
                security_clearances TEXT,
                availability_matrix TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (rfp_response_id) REFERENCES rfp_responses (id)
            )
        """)
        
        # Competitor intelligence table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_intelligence (
                id TEXT PRIMARY KEY,
                rfp_id TEXT NOT NULL,
                competitor_name TEXT NOT NULL,
                strengths TEXT,
                weaknesses TEXT,
                past_performance TEXT,
                typical_pricing TEXT,
                win_rate REAL DEFAULT 0.0,
                relationship_with_customer TEXT,
                differentiators TEXT,
                intelligence_source TEXT,
                confidence_level TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (rfp_id) REFERENCES rfp_opportunities (id)
            )
        """)
        
        # Questions and clarifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfp_questions (
                id TEXT PRIMARY KEY,
                rfp_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT,
                submitted_date TEXT,
                response_received TEXT,
                government_response TEXT,
                impact_level TEXT,
                follow_up_required BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (rfp_id) REFERENCES rfp_opportunities (id)
            )
        """)
        
        # Past performance references table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS past_performance (
                id TEXT PRIMARY KEY,
                contract_number TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                contract_title TEXT,
                contract_value REAL,
                performance_period_start TEXT,
                performance_period_end TEXT,
                description_of_work TEXT,
                performance_rating TEXT,
                key_personnel TEXT,
                relevance_score REAL DEFAULT 0.0,
                reference_contact TEXT,
                lessons_learned TEXT,
                awards_recognition TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_notification_settings(self):
        """Setup notification settings for RFP tracking"""
        self.notification_settings = {
            "new_opportunities_keywords": ["software", "IT", "cybersecurity", "data", "analytics"],
            "deadline_alerts": {
                "questions_deadline": 5,  # days before
                "submission_deadline": 3,  # days before
                "follow_up": 7  # days after submission
            },
            "daily_scan_enabled": True,
            "email_notifications": True
        }

    async def _load_agency_mappings(self):
        """Load government agency mappings and contact information"""
        self.agency_mappings = {
            "DOD": {
                "name": "Department of Defense",
                "common_offices": ["Army", "Navy", "Air Force", "DLA", "DISA"],
                "typical_contract_types": ["FIXED_PRICE", "COST_PLUS"],
                "procurement_methods": ["SAM.gov", "eBuy", "Direct"]
            },
            "GSA": {
                "name": "General Services Administration", 
                "common_offices": ["FAS", "PBS", "OGP"],
                "typical_contract_types": ["FIXED_PRICE", "TIME_MATERIALS"],
                "procurement_methods": ["GSA Advantage", "eBuy", "RFQ"]
            },
            "DHS": {
                "name": "Department of Homeland Security",
                "common_offices": ["CBP", "ICE", "TSA", "USCIS"],
                "typical_contract_types": ["FIXED_PRICE", "COST_PLUS"],
                "procurement_methods": ["SAM.gov", "Direct"]
            }
        }

    async def scan_opportunities(self, keywords: List[str] = None, 
                               naics_codes: List[str] = None,
                               agencies: List[str] = None) -> Dict[str, Any]:
        """Scan for new RFP opportunities matching criteria"""
        try:
            # Simulate API call to SAM.gov or other sources
            opportunities = await self._fetch_opportunities_from_sources(keywords, naics_codes, agencies)
            
            # Process and store new opportunities
            new_count = 0
            updated_count = 0
            
            for opp in opportunities:
                existing = await self._check_existing_opportunity(opp['rfp_number'])
                if existing:
                    await self._update_opportunity(existing['id'], opp)
                    updated_count += 1
                else:
                    await self._store_new_opportunity(opp)
                    new_count += 1
            
            # Analyze opportunities for relevance
            relevant_opportunities = await self._analyze_opportunity_relevance(opportunities)
            
            result = {
                "scan_date": datetime.now().isoformat(),
                "total_found": len(opportunities),
                "new_opportunities": new_count,
                "updated_opportunities": updated_count,
                "relevant_opportunities": len(relevant_opportunities),
                "opportunities": relevant_opportunities[:10],  # Top 10 most relevant
                "keywords_used": keywords or self.notification_settings["new_opportunities_keywords"],
                "next_scan": (datetime.now() + timedelta(hours=6)).isoformat()
            }
            
            logger.info(f"Opportunity scan completed: {new_count} new, {updated_count} updated")
            return result
            
        except Exception as e:
            logger.error(f"Error scanning opportunities: {e}")
            return {"error": str(e)}

    async def _fetch_opportunities_from_sources(self, keywords: List[str], 
                                              naics_codes: List[str], 
                                              agencies: List[str]) -> List[Dict[str, Any]]:
        """Simulate fetching opportunities from various sources"""
        # In real implementation, this would call SAM.gov API, eBuy, etc.
        simulated_opportunities = [
            {
                "rfp_number": "W15QKN-24-R-0001",
                "title": "Enterprise Software Development Services",
                "agency": "DOD",
                "office": "Army",
                "description": "Multi-year IDIQ for custom software development",
                "rfp_type": RFPType.RFP.value,
                "contract_type": ContractType.TIME_MATERIALS.value,
                "naics_code": "541511",
                "set_aside_type": "Small Business",
                "estimated_value_min": 5000000,
                "estimated_value_max": 50000000,
                "release_date": "2024-02-01",
                "response_deadline": "2024-03-15",
                "questions_deadline": "2024-02-28"
            },
            {
                "rfp_number": "GS00Q-24-R-0002", 
                "title": "Cybersecurity Assessment Services",
                "agency": "GSA",
                "office": "FAS",
                "description": "NIST 800-171 compliance assessments",
                "rfp_type": RFPType.RFQ.value,
                "contract_type": ContractType.FIXED_PRICE.value,
                "naics_code": "541512",
                "set_aside_type": "None",
                "estimated_value_min": 1000000,
                "estimated_value_max": 10000000,
                "release_date": "2024-01-15",
                "response_deadline": "2024-02-29",
                "questions_deadline": "2024-02-15"
            }
        ]
        
        return simulated_opportunities

    async def _check_existing_opportunity(self, rfp_number: str) -> Optional[Dict[str, Any]]:
        """Check if opportunity already exists in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM rfp_opportunities WHERE rfp_number = ?", (rfp_number,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"id": row[0], "rfp_number": row[1]}
        return None

    async def _store_new_opportunity(self, opportunity: Dict[str, Any]):
        """Store new RFP opportunity in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        opp_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO rfp_opportunities (
                id, rfp_number, title, agency, office, description, rfp_type,
                contract_type, naics_code, set_aside_type, estimated_value_min,
                estimated_value_max, release_date, response_deadline, questions_deadline,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            opp_id, opportunity["rfp_number"], opportunity["title"],
            opportunity["agency"], opportunity["office"], opportunity["description"],
            opportunity["rfp_type"], opportunity["contract_type"], opportunity["naics_code"],
            opportunity["set_aside_type"], opportunity["estimated_value_min"],
            opportunity["estimated_value_max"], opportunity["release_date"],
            opportunity["response_deadline"], opportunity["questions_deadline"],
            now, now
        ))
        
        conn.commit()
        conn.close()

    async def _update_opportunity(self, opp_id: str, opportunity: Dict[str, Any]):
        """Update existing opportunity with new information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE rfp_opportunities 
            SET title = ?, description = ?, response_deadline = ?, 
                questions_deadline = ?, updated_at = ?
            WHERE id = ?
        """, (
            opportunity["title"], opportunity["description"],
            opportunity["response_deadline"], opportunity["questions_deadline"],
            datetime.now().isoformat(), opp_id
        ))
        
        conn.commit()
        conn.close()

    async def _analyze_opportunity_relevance(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze and score opportunities for relevance"""
        scored_opportunities = []
        
        for opp in opportunities:
            score = await self._calculate_relevance_score(opp)
            opp["relevance_score"] = score
            opp["analysis"] = await self._generate_opportunity_analysis(opp)
            scored_opportunities.append(opp)
        
        # Sort by relevance score descending
        return sorted(scored_opportunities, key=lambda x: x["relevance_score"], reverse=True)

    async def _calculate_relevance_score(self, opportunity: Dict[str, Any]) -> float:
        """Calculate relevance score for an opportunity"""
        score = 0.0
        
        # NAICS code relevance (40 points)
        relevant_naics = ["541511", "541512", "541513", "541519"]
        if opportunity.get("naics_code") in relevant_naics:
            score += 40
        
        # Contract value (25 points) - prefer mid-range contracts
        value_max = opportunity.get("estimated_value_max", 0)
        if 1000000 <= value_max <= 25000000:
            score += 25
        elif value_max < 1000000:
            score += 10
        
        # Set aside type (15 points)
        if opportunity.get("set_aside_type") == "Small Business":
            score += 15
        
        # Agency preference (10 points)
        preferred_agencies = ["DOD", "GSA", "DHS"]
        if opportunity.get("agency") in preferred_agencies:
            score += 10
        
        # Time to deadline (10 points)
        deadline = opportunity.get("response_deadline")
        if deadline:
            try:
                deadline_date = datetime.fromisoformat(deadline)
                days_to_deadline = (deadline_date - datetime.now()).days
                if 30 <= days_to_deadline <= 60:  # Sweet spot
                    score += 10
                elif days_to_deadline >= 15:
                    score += 5
            except:
                pass
        
        return min(score, 100.0)  # Cap at 100

    async def _generate_opportunity_analysis(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis for an opportunity"""
        return {
            "go_no_go_recommendation": "GO" if opportunity.get("relevance_score", 0) >= 60 else "NO-GO",
            "key_strengths": ["Technical expertise", "Past performance", "Security clearances"],
            "potential_challenges": ["Timeline constraints", "Resource availability"],
            "estimated_effort": "Medium",
            "win_probability": min(opportunity.get("relevance_score", 0) / 100 * 0.8, 0.8),
            "recommended_next_steps": [
                "Form proposal team",
                "Analyze requirements", 
                "Prepare questions",
                "Schedule kickoff meeting"
            ]
        }

    async def get_opportunities(self, agency: Optional[str] = None, 
                              naics_code: Optional[str] = None) -> Dict[str, Any]:
        """Get RFP opportunities with optional filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM rfp_opportunities WHERE status = 'active'"
            params = []
            
            if agency:
                query += " AND agency = ?"
                params.append(agency)
            
            if naics_code:
                query += " AND naics_code = ?"
                params.append(naics_code)
            
            query += " ORDER BY response_deadline ASC"
            
            cursor.execute(query, params)
            
            opportunities = []
            for row in cursor.fetchall():
                opportunities.append({
                    "id": row[0],
                    "rfp_number": row[1],
                    "title": row[2],
                    "agency": row[3],
                    "office": row[4],
                    "description": row[5],
                    "rfp_type": row[6],
                    "contract_type": row[7],
                    "naics_code": row[8],
                    "set_aside_type": row[9],
                    "estimated_value_min": row[10],
                    "estimated_value_max": row[11],
                    "release_date": row[12],
                    "response_deadline": row[13],
                    "questions_deadline": row[14],
                    "status": row[19]
                })
            
            conn.close()
            
            return {
                "total_opportunities": len(opportunities),
                "filter_applied": {"agency": agency, "naics_code": naics_code},
                "opportunities": opportunities
            }
            
        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return {"error": str(e)}

    async def submit_response(self, rfp_data: Dict[str, Any], 
                            submission_deadline: str,
                            requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Submit RFP response"""
        try:
            response_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Validate submission
            validation_result = await self._validate_submission(rfp_data, requirements)
            if not validation_result["is_valid"]:
                return {
                    "error": "Submission validation failed",
                    "validation_errors": validation_result["errors"]
                }
            
            # Store response
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO rfp_responses (
                    id, rfp_id, technical_approach, management_approach,
                    proposed_solution, compliance_checklist, submission_date,
                    status, audit_trail, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                response_id, rfp_data["rfp_id"], rfp_data.get("technical_approach"),
                rfp_data.get("management_approach"), rfp_data.get("proposed_solution"),
                json.dumps(validation_result["checklist"]), submission_deadline,
                RFPStatus.SUBMITTED.value, json.dumps([{
                    "action": "response_submitted",
                    "date": now,
                    "user": "system"
                }]), now, now
            ))
            
            conn.commit()
            conn.close()
            
            # Generate submission confirmation
            result = {
                "response_id": response_id,
                "rfp_id": rfp_data["rfp_id"],
                "submission_status": "SUCCESS",
                "submission_date": submission_deadline,
                "validation_score": validation_result["score"],
                "compliance_percentage": validation_result["compliance_percentage"],
                "next_steps": [
                    "Monitor for government questions",
                    "Prepare for oral presentation if required",
                    "Track evaluation timeline",
                    "Maintain proposal team availability"
                ]
            }
            
            logger.info(f"RFP response submitted successfully: {response_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error submitting RFP response: {e}")
            return {"error": str(e)}

    async def _validate_submission(self, rfp_data: Dict[str, Any], 
                                 requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate RFP submission against requirements"""
        errors = []
        checklist = []
        compliance_count = 0
        
        # Check required sections
        required_sections = ["technical_approach", "management_approach", "proposed_solution"]
        for section in required_sections:
            if not rfp_data.get(section):
                errors.append(f"Missing required section: {section}")
                checklist.append({"item": section, "status": "MISSING"})
            else:
                checklist.append({"item": section, "status": "COMPLETE"})
                compliance_count += 1
        
        # Check requirements compliance
        for req in requirements:
            req_id = req.get("id", "unknown")
            if req.get("mandatory", False):
                # Check if requirement is addressed
                addressed = self._check_requirement_addressed(rfp_data, req)
                if addressed:
                    checklist.append({"item": f"Requirement {req_id}", "status": "ADDRESSED"})
                    compliance_count += 1
                else:
                    errors.append(f"Mandatory requirement {req_id} not addressed")
                    checklist.append({"item": f"Requirement {req_id}", "status": "NOT_ADDRESSED"})
        
        total_items = len(checklist)
        compliance_percentage = (compliance_count / total_items * 100) if total_items > 0 else 0
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "checklist": checklist,
            "compliance_percentage": compliance_percentage,
            "score": max(0, 100 - len(errors) * 10)
        }

    def _check_requirement_addressed(self, rfp_data: Dict[str, Any], requirement: Dict[str, Any]) -> bool:
        """Check if a requirement is addressed in the submission"""
        # Simple keyword matching - in real implementation would be more sophisticated
        req_text = requirement.get("description", "").lower()
        keywords = req_text.split()
        
        # Search for keywords in all text sections
        text_sections = [
            rfp_data.get("technical_approach", ""),
            rfp_data.get("management_approach", ""), 
            rfp_data.get("proposed_solution", "")
        ]
        
        all_text = " ".join(text_sections).lower()
        return any(keyword in all_text for keyword in keywords[:3])  # Check first 3 keywords

    async def get_response_status(self, rfp_id: str) -> Dict[str, Any]:
        """Get status of RFP response"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.*, o.title, o.agency, o.response_deadline 
                FROM rfp_responses r
                JOIN rfp_opportunities o ON r.rfp_id = o.id
                WHERE r.rfp_id = ?
                ORDER BY r.created_at DESC
            """, (rfp_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {"error": "RFP response not found"}
            
            return {
                "response_id": row[0],
                "rfp_id": row[1],
                "rfp_title": row[15],
                "agency": row[16],
                "status": row[10],
                "submission_date": row[9],
                "response_deadline": row[17],
                "win_probability": row[11] or 0.0,
                "current_stage": self._determine_response_stage(row[10]),
                "days_since_submission": self._calculate_days_since_submission(row[9]),
                "next_milestone": self._determine_next_milestone(row[10])
            }
            
        except Exception as e:
            logger.error(f"Error getting response status: {e}")
            return {"error": str(e)}

    def _determine_response_stage(self, status: str) -> str:
        """Determine current stage of response"""
        stage_map = {
            RFPStatus.SUBMITTED.value: "Initial Review",
            RFPStatus.UNDER_REVIEW.value: "Technical Evaluation", 
            RFPStatus.SHORTLISTED.value: "Final Selection",
            RFPStatus.AWARDED.value: "Contract Award",
            RFPStatus.REJECTED.value: "Closed - Not Selected"
        }
        return stage_map.get(status, "Unknown")

    def _calculate_days_since_submission(self, submission_date: str) -> int:
        """Calculate days since submission"""
        try:
            submitted = datetime.fromisoformat(submission_date)
            return (datetime.now() - submitted).days
        except:
            return 0

    def _determine_next_milestone(self, status: str) -> str:
        """Determine next milestone in process"""
        milestone_map = {
            RFPStatus.SUBMITTED.value: "Government initial review (7-14 days)",
            RFPStatus.UNDER_REVIEW.value: "Technical evaluation completion (30-45 days)",
            RFPStatus.SHORTLISTED.value: "Final award decision (14-30 days)",
            RFPStatus.AWARDED.value: "Contract execution",
            RFPStatus.REJECTED.value: "Debrief available"
        }
        return milestone_map.get(status, "Unknown")

# Global instance
rfp_system = RFPManagementSystem()